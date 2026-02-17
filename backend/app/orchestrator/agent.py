import base64
import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import settings
from app.image.generator import image_generator
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
    prompt: str, user: User, user_id_short: str
) -> tuple[list[str] | None, str]:
    """Attempt image generation. Returns (encoded_images, tool_result_text)."""
    try:
        image_bytes_list = await image_generator.generate(prompt=prompt, user=user)
        encoded = [base64.b64encode(img).decode("utf-8") for img in image_bytes_list]
        logger.info("[user:%s] image generated successfully", user_id_short)
        return encoded, f"Image generated successfully for: {prompt}"
    except Exception as e:
        logger.warning("[user:%s] image generation failed: %s", user_id_short, e)
        return None, f"Image generation failed: {e}. Respond with text instead."


# ---------------------------------------------------------------------------
# Supervisor: tool-calling phase (Her mode)
# ---------------------------------------------------------------------------


async def _run_tool_phase(
    message: str,
    history: list,
    user: User,
) -> tuple[list[str] | None, list[str] | None]:
    """Run the supervisor (mistral) to decide tool calls for Her mode.
    Returns (image_result, memories) — either can be None.
    """
    user_id_short = str(user.id)[:8]
    supervisor_model = settings.ollama_chat_model

    sup_messages = [{"role": "system", "content": HER_SUPERVISOR_PROMPT}]
    for msg in history[-settings.supervisor_context_messages:]:
        sup_messages.append({"role": msg.role, "content": msg.content})
    if not history or str(history[-1].content) != message:
        sup_messages.append({"role": "user", "content": message})

    logger.info(
        "[user:%s] her supervisor: analyzing with %s", user_id_short, supervisor_model
    )

    image_result = None
    memories = None

    for iteration in range(settings.agent_max_tool_iterations):
        try:
            response = await _client.chat.completions.create(
                model=supervisor_model,
                messages=sup_messages,
                tools=ALL_TOOLS,
                stream=False,
            )
        except Exception as e:
            logger.error("[user:%s] supervisor LLM failed: %s", user_id_short, e)
            break

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            logger.info(
                "[user:%s] supervisor: no tool calls at iteration %d",
                user_id_short, iteration,
            )
            break

        sup_messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            result = await _dispatch_tool(tool_name, arguments, user)

            if result == _SENTINEL_IMAGE_REQUEST:
                prompt = arguments.get("prompt", message)
                encoded, result = await _handle_image_generation(
                    prompt, user, user_id_short
                )
                if encoded:
                    image_result = encoded

            if tool_name == _TOOL_NAME_RECALL and result != "No relevant memories found.":
                memories = result.split("\n")
                logger.info(
                    "[user:%s] supervisor: recalled %d memories",
                    user_id_short, len(memories),
                )

            sup_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

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
    """Run the agentic loop. Yields dicts:
    - {"type": "token", "content": str}        — streaming text token
    - {"type": "image", "images": list[str]}   — base64 images
    - {"type": "tool_start", "tool": str}       — tool progress indicator
    - {"type": "tool_done", "tool": str}        — tool done indicator
    """
    user_id_short = str(user.id)[:8]

    if mode == "her":
        # --- Two-model pipeline for Her mode ---
        responder_model = settings.ollama_her_model

        logger.info(
            "[user:%s] mode=her, supervisor=%s, responder=%s",
            user_id_short, settings.ollama_chat_model, responder_model,
        )

        yield {"type": "tool_start", "tool": "analyzing"}
        image_result, supervisor_memories = await _run_tool_phase(
            message, history, user
        )
        yield {"type": "tool_done", "tool": "analyzing"}

        memories = None
        if supervisor_memories:
            memories = [m.lstrip("- ").strip() for m in supervisor_memories if m.strip()]
            logger.info(
                "[user:%s] supervisor recalled %d memories",
                user_id_short, len(memories),
            )

        if image_result:
            yield {"type": "image", "images": image_result}

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
            logger.error("[user:%s] her streaming failed: %s", user_id_short, e)
            yield {"type": "token", "content": _ERROR_RESPONSE}

    else:
        # --- Single-model pipeline for Jarvis mode ---
        model = settings.ollama_chat_model
        tools = ALL_TOOLS

        logger.info(
            "[user:%s] mode=jarvis, model=%s, tools=%s",
            user_id_short, model, [t["function"]["name"] for t in tools],
        )

        system_prompt = _build_system_prompt(user, mode)
        messages = _build_messages(system_prompt, history, message)

        image_result = None

        for iteration in range(settings.agent_max_tool_iterations):
            try:
                response = await _client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    stream=False,
                )
            except Exception as e:
                logger.error("[user:%s] LLM call failed: %s", user_id_short, e)
                yield {"type": "token", "content": _ERROR_RESPONSE}
                return

            choice = response.choices[0]
            msg = choice.message

            if not msg.tool_calls:
                logger.info(
                    "[user:%s] no tool calls at iteration %d, proceeding to stream",
                    user_id_short, iteration,
                )
                break

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                yield {"type": "tool_start", "tool": tool_name}

                result = await _dispatch_tool(tool_name, arguments, user)

                if result == _SENTINEL_IMAGE_REQUEST:
                    prompt = arguments.get("prompt", message)
                    encoded, result = await _handle_image_generation(
                        prompt, user, user_id_short
                    )
                    if encoded:
                        image_result = encoded

                yield {"type": "tool_done", "tool": tool_name}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            logger.warning(
                "[user:%s] max tool iterations (%d) reached",
                user_id_short, settings.agent_max_tool_iterations,
            )

        if image_result:
            yield {"type": "image", "images": image_result}

        logger.info("[user:%s] streaming final response (model=%s)", user_id_short, model)
        try:
            stream = await _client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {"type": "token", "content": chunk.choices[0].delta.content}
        except Exception as e:
            logger.error("[user:%s] streaming failed: %s", user_id_short, e)
            yield {"type": "token", "content": _ERROR_RESPONSE}
