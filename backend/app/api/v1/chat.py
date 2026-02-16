import base64
import json
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
from app.orchestrator.guardian import Guardian
from app.orchestrator.router import Router, Intent
from app.orchestrator.jarvis import JarvisModule
from app.orchestrator.her import HerModule
from app.orchestrator.memory import recall, remember, extract_facts
from app.image.generator import image_generator

router = APIRouter(prefix="/chat", tags=["chat"])
guardian = Guardian()
intent_router = Router()
jarvis = JarvisModule()
her = HerModule()


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
    # Pre-filter
    filter_result = await guardian.pre_filter(body.content)
    if filter_result.blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=filter_result.reason or "Message blocked by content filter",
        )

    # Safe word check — toggle mode
    if user.safe_word and guardian.check_safe_word(body.content, user.safe_word):
        new_mode = "her" if user.current_mode == "jarvis" else "jarvis"
        user.current_mode = new_mode
        await db.commit()

        async def mode_switch_event():
            yield json.dumps({
                "event": "mode_switch",
                "mode": new_mode,
                "message": f"Mode switched to {new_mode}.",
            })

        return EventSourceResponse(mode_switch_event())

    # Exit keyword check (only in Her mode)
    if user.current_mode == "her" and guardian.check_exit_keyword(body.content):
        user.current_mode = "jarvis"
        await db.commit()

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

    # Get conversation history
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.created_at)
        .limit(50)
    )
    history = history_result.scalars().all()

    # Classify intent
    intent = await intent_router.classify(body.content)

    # Handle image requests
    if intent == Intent.IMAGE_REQUEST:
        assistant_msg_id = uuid.uuid4()
        try:
            image_bytes_list = await image_generator.generate(
                prompt=body.content, user=user
            )
            encoded = [
                base64.b64encode(img).decode("utf-8") for img in image_bytes_list
            ]

            async def image_generate():
                yield json.dumps({
                    "event": "image",
                    "images": encoded,
                    "session_id": str(session.id),
                    "msg_id": str(assistant_msg_id),
                    "mode": user.current_mode,
                })
                assistant_msg = Message(
                    id=assistant_msg_id,
                    session_id=session.id,
                    user_id=user.id,
                    role="assistant",
                    content=f"[Generated image for: {body.content}]",
                    mode=user.current_mode,
                )
                db.add(assistant_msg)
                session.message_count = (session.message_count or 0) + 2
                await db.commit()

            return EventSourceResponse(image_generate())
        except Exception:
            # Fall through to text response if image gen fails
            pass

    # Recall memories
    memories = await recall(user_id=str(user.id), query=body.content, limit=5)

    # Choose module based on mode
    module = her if user.current_mode == "her" else jarvis

    # Stream response
    assistant_msg_id = uuid.uuid4()

    async def generate():
        full_response = []
        async for token in module.stream(body.content, history, user, memories=memories):
            full_response.append(token)
            yield json.dumps({
                "token": token,
                "session_id": str(session.id),
                "msg_id": str(assistant_msg_id),
                "mode": user.current_mode,
            })

        # Save assistant message after streaming completes
        content = "".join(full_response)
        assistant_msg = Message(
            id=assistant_msg_id,
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content=content,
            mode=user.current_mode,
        )
        db.add(assistant_msg)
        session.message_count = (session.message_count or 0) + 2
        await db.commit()

        # Write memories
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
    limit: int = 50,
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
        .limit(20)
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
