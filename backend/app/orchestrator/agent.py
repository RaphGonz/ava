import base64
import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import settings
from app.image.generator import image_generator
from app.image.prompt_rewriter import rewrite_prompt
from app.models.user import User
from app.orchestrator.memory import recall, recall_as_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SENTINEL_IMAGE_REQUEST = "__IMAGE_REQUEST__"
_ERROR_RESPONSE = "I'm having trouble responding right now. Please try again."
_OLLAMA_API_KEY = "ollama"  # dummy key required by OpenAI SDK for local Ollama

# ---------------------------------------------------------------------------
# System prompts — loaded from txt files for easy editing
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


JARVIS_SYSTEM_PROMPT = _load_prompt("jarvis")
HER_SYSTEM_PROMPT = _load_prompt("her")
HER_SUPERVISOR_PROMPT = _load_prompt("supervisor")
IMAGE_CONTEXT_PROMPT = _load_prompt("image_context")

# ---------------------------------------------------------------------------
# Tool definitions — loaded from JSON files
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parent / "tools"


def _load_tool(name: str) -> dict:
    return json.loads((_TOOLS_DIR / f"{name}.json").read_text(encoding="utf-8"))


TOOL_RECALL_MEMORIES = _load_tool("recall_memories")
TOOL_GENERATE_IMAGE = _load_tool("generate_image")
ALL_TOOLS = [TOOL_RECALL_MEMORIES, TOOL_GENERATE_IMAGE]

# Tool name constants (match the JSON files)
_TOOL_NAME_RECALL = TOOL_RECALL_MEMORIES["function"]["name"]
_TOOL_NAME_IMAGE = TOOL_GENERATE_IMAGE["function"]["name"]

# ---------------------------------------------------------------------------
# OpenAI client (pointed at Ollama)
# ---------------------------------------------------------------------------

_client = AsyncOpenAI(
    base_url=settings.ollama_base_url,
    api_key=_OLLAMA_API_KEY,
)

# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------


async def _dispatch_tool(
    tool_name: str, arguments: dict, user: User
) -> str:
    """Execute a tool call and return the result as a string."""
    start = time.time()

    if tool_name == _TOOL_NAME_RECALL:
        query = arguments.get("query", "")
        result = await recall_as_tool(user_id=str(user.id), query=query)
    elif tool_name == _TOOL_NAME_IMAGE:
        result = _SENTINEL_IMAGE_REQUEST
    else:
        result = f"Unknown tool: {tool_name}"

    elapsed = (time.time() - start) * 1000
    logger.info(
        "[user:%s] tool_call: %s(%s) took %.0fms",
        str(user.id)[:8], tool_name, json.dumps(arguments)[:80], elapsed,
    )
    return result


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_system_prompt(
    user: User, mode: str, memories: list[str] | None = None
) -> str:
    system = JARVIS_SYSTEM_PROMPT if mode == "jarvis" else HER_SYSTEM_PROMPT

    if user.username:
        system += f"\n\nThe user's name is {user.username}."

    if memories:
        system += "\n\nRelevant context from past conversations:\n"
        for mem in memories:
            system += f"- {mem}\n"

    return system


def _build_messages(
    system_prompt: str, history: list, message: str, context_limit: int | None = None
) -> list[dict]:
    if context_limit is None:
        context_limit = settings.agent_context_messages
    messages = [{"role": "system", "content": system_prompt}]

    for msg in history[-context_limit:]:
        messages.append({"role": msg.role, "content": msg.content})

    if not history or str(history[-1].content) != message:
        messages.append({"role": "user", "content": message})

    return messages


# ---------------------------------------------------------------------------
# Image generation helper
# ---------------------------------------------------------------------------


async def _handle_image_generation(
    intent: str,
    user: User,
    user_id_short: str,
    conversation_context: list[dict],
) -> tuple[list[str] | None, str]:
    """Rewrite intent into a Qwen prompt, then generate. Returns (encoded_images, tool_result_text)."""
    try:
        has_ref = bool(user.avatar_config and user.avatar_config.get("reference_images"))

        # Step 1: rewrite conversational intent into optimized diffusion prompt
        optimized_prompt = await rewrite_prompt(
            intent=intent,
            conversation_context=conversation_context,
            has_reference_image=has_ref,
        )
        logger.info("[user:%s] rewritten prompt: %.100s", user_id_short, optimized_prompt)

        # Step 2: generate image with rewritten prompt
        results = await image_generator.generate(prompt=optimized_prompt, user=user)
        encoded = [base64.b64encode(r["bytes"]).decode("utf-8") for r in results]
        logger.info("[user:%s] image generated successfully", user_id_short)
        return encoded, f"Image generated successfully for: {intent}"
    except Exception as e:
        logger.warning("[user:%s] image generation failed: %s", user_id_short, e)
        return None, f"Image generation failed: {e}. Respond with text instead."


# ---------------------------------------------------------------------------
# Tool detection phase (shared by Her and Jarvis modes)
# ---------------------------------------------------------------------------


async def _run_tool_phase(
    message: str,
    history: list,
    user: User,
) -> tuple[list[str] | None, list[str] | None]:
    """Single supervisor call to detect and execute tool calls.

    Returns (image_result, memories) — either can be None.
    """
    user_id_short = str(user.id)[:8]
    supervisor_model = settings.ollama_supervisor_model

    sup_messages = [{"role": "system", "content": HER_SUPERVISOR_PROMPT}]
    for msg in history[-settings.supervisor_context_messages:]:
        sup_messages.append({"role": msg.role, "content": msg.content})
    if not history or str(history[-1].content) != message:
        sup_messages.append({"role": "user", "content": message})

    logger.info(
        "[user:%s] supervisor: analyzing with %s", user_id_short, supervisor_model
    )

    image_result = None
    memories = None

    try:
        response = await _client.chat.completions.create(
            model=supervisor_model,
            messages=sup_messages,
            tools=ALL_TOOLS,
            stream=False,
        )
    except Exception as e:
        logger.error("[user:%s] supervisor LLM failed: %s", user_id_short, e)
        return image_result, memories

    msg = response.choices[0].message

    if not msg.tool_calls:
        logger.info("[user:%s] supervisor: no tool calls needed", user_id_short)
        return image_result, memories

    for tc in msg.tool_calls:
        tool_name = tc.function.name
        try:
            arguments = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            arguments = {}

        result = await _dispatch_tool(tool_name, arguments, user)

        if result == _SENTINEL_IMAGE_REQUEST:
            prompt = arguments.get("prompt", message)
            context = [{"role": m.role, "content": m.content} for m in history[-6:]]
            encoded, _ = await _handle_image_generation(
                prompt, user, user_id_short, context
            )
            if encoded:
                image_result = encoded

        if tool_name == _TOOL_NAME_RECALL and result != "No relevant memories found.":
            memories = result.split("\n")
            logger.info(
                "[user:%s] supervisor: recalled %d memories",
                user_id_short, len(memories),
            )

    return image_result, memories


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


async def run_agent(
    message: str,
    history: list,
    user: User,
    mode: str,
) -> AsyncIterator[dict]:
    """Run the agent pipeline. Yields dicts:
    - {"type": "token", "content": str}        — streaming text token
    - {"type": "image", "images": list[str]}   — base64 images
    - {"type": "tool_start", "tool": str}       — tool progress indicator
    - {"type": "tool_done", "tool": str}        — tool done indicator
    """
    user_id_short = str(user.id)[:8]
    responder_model = settings.ollama_her_model if mode == "her" else settings.ollama_chat_model

    logger.info(
        "[user:%s] mode=%s, supervisor=%s, responder=%s",
        user_id_short, mode, settings.ollama_supervisor_model, responder_model,
    )

    # Step 1: supervisor — single LLM call for tool detection
    yield {"type": "tool_start", "tool": "analyzing"}
    image_result, raw_memories = await _run_tool_phase(message, history, user)
    yield {"type": "tool_done", "tool": "analyzing"}

    memories = None
    if raw_memories:
        memories = [m.lstrip("- ").strip() for m in raw_memories if m.strip()]
        logger.info("[user:%s] recalled %d memories", user_id_short, len(memories))

    if image_result:
        yield {"type": "image", "images": image_result}

    # Step 2: responder — stream the text reply
    system_prompt = _build_system_prompt(user, mode, memories)
    if image_result:
        system_prompt += f"\n\n{IMAGE_CONTEXT_PROMPT}"
    messages = _build_messages(system_prompt, history, message)

    logger.info("[user:%s] streaming response (model=%s)", user_id_short, responder_model)
    try:
        stream = await _client.chat.completions.create(
            model=responder_model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"type": "token", "content": chunk.choices[0].delta.content}
    except Exception as e:
        logger.error("[user:%s] streaming failed: %s", user_id_short, e)
        yield {"type": "token", "content": _ERROR_RESPONSE}
