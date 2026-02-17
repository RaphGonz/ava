import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.session import Message, Session
from app.models.user import User
from app.core.config import settings
from app.orchestrator.guardian import Guardian
from app.orchestrator.agent import run_agent
from app.orchestrator.memory import remember, extract_facts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
guardian = Guardian()


class ChatRequest(BaseModel):
    content: str
    session_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    mode: str
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/message")
async def send_message(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_short = str(user.id)[:8]

    # Pre-filter (always, cheap)
    filter_result = await guardian.pre_filter(body.content)
    if filter_result.blocked:
        logger.warning("[user:%s] message blocked by guardian", user_id_short)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=filter_result.reason or "Message blocked by content filter",
        )

    # Safe word check — toggle mode
    if user.safe_word and guardian.check_safe_word(body.content, user.safe_word):
        new_mode = "her" if user.current_mode == "jarvis" else "jarvis"
        user.current_mode = new_mode
        await db.commit()
        logger.info("[user:%s] mode switched to %s via safe word", user_id_short, new_mode)

        async def mode_switch_event():
            yield json.dumps({
                "event": "mode_switch",
                "mode": new_mode,
                "message": f"Mode switched to {new_mode}.",
            })

        return EventSourceResponse(mode_switch_event())

    # Exit keyword check (only in Her mode)
    if user.current_mode == "her" and guardian.check_exit_keyword(body.content, user.exit_word):
        user.current_mode = "jarvis"
        await db.commit()
        logger.info("[user:%s] exiting Her mode via keyword", user_id_short)

        async def exit_event():
            yield json.dumps({
                "event": "mode_switch",
                "mode": "jarvis",
                "message": "Returning to Jarvis mode.",
            })

        return EventSourceResponse(exit_event())

    # Age verification gate for Her mode
    if user.current_mode == "her" and not user.is_age_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Age verification required for intimate mode",
        )

    # Get or create session
    if body.session_id:
        result = await db.execute(
            select(Session).where(
                Session.id == body.session_id, Session.user_id == user.id
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = Session(user_id=user.id)
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Save user message
    user_msg = Message(
        session_id=session.id,
        user_id=user.id,
        role="user",
        content=body.content,
        mode=user.current_mode,
    )
    db.add(user_msg)
    await db.commit()

    # Get conversation history (only what we need)
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
        .limit(settings.agent_context_messages)
    )
    history = history_result.scalars().all()

    logger.info(
        "[user:%s] starting agent (mode=%s, history=%d msgs)",
        user_id_short, user.current_mode, len(history),
    )

    # Run the agent and stream response
    assistant_msg_id = uuid.uuid4()
    current_mode = user.current_mode

    async def generate():
        full_response = []

        async for event in run_agent(body.content, history, user, current_mode):
            if event["type"] == "token":
                full_response.append(event["content"])
                yield json.dumps({
                    "token": event["content"],
                    "session_id": str(session.id),
                    "msg_id": str(assistant_msg_id),
                    "mode": current_mode,
                })
            elif event["type"] == "image":
                yield json.dumps({
                    "event": "image",
                    "images": event["images"],
                    "session_id": str(session.id),
                    "msg_id": str(assistant_msg_id),
                    "mode": current_mode,
                })
            elif event["type"] == "tool_start":
                yield json.dumps({
                    "event": "tool_start",
                    "tool": event["tool"],
                    "session_id": str(session.id),
                    "mode": current_mode,
                })
            elif event["type"] == "tool_done":
                yield json.dumps({
                    "event": "tool_done",
                    "tool": event["tool"],
                    "session_id": str(session.id),
                    "mode": current_mode,
                })

        # Save assistant message after streaming completes
        content = "".join(full_response)
        assistant_msg = Message(
            id=assistant_msg_id,
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content=content,
            mode=current_mode,
        )
        db.add(assistant_msg)
        session.message_count = (session.message_count or 0) + 2
        await db.commit()

        # Write memories (background, after stream)
        facts = extract_facts(body.content, content)
        for fact in facts:
            vector_id = await remember(
                user_id=str(user.id),
                text=fact,
                source_message_id=str(assistant_msg_id),
            )
            assistant_msg.vector_id = vector_id
            await db.commit()

    return EventSourceResponse(generate())


@router.get("/history")
async def get_history(
    session_id: str | None = None,
    limit: int = settings.chat_history_default_limit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Message).where(Message.user_id == user.id)
    if session_id:
        query = query.where(Message.session_id == session_id)
    query = query.order_by(desc(Message.created_at)).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            mode=m.mode,
            created_at=m.created_at.isoformat(),
        )
        for m in reversed(messages)
    ]


@router.get("/sessions")
async def get_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user.id)
        .order_by(desc(Session.started_at))
        .limit(settings.chat_sessions_default_limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "started_at": s.started_at.isoformat(),
            "message_count": s.message_count,
        }
        for s in sessions
    ]
