import logging
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "orchestrator" / "prompts"
_SYSTEM_PROMPT = (_PROMPTS_DIR / "image_rewriter.txt").read_text(encoding="utf-8").strip()

_client = AsyncOpenAI(
    base_url=settings.ollama_base_url,
    api_key="ollama",
)


async def rewrite_prompt(
    intent: str,
    conversation_context: list[dict],
    has_reference_image: bool = False,
) -> str:
    """Rewrite a conversational image intent into an optimized Qwen diffusion prompt."""
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
    ]

    # Include recent conversation as context
    for msg in conversation_context[-6:]:
        messages.append({"role": msg["role"], "content": str(msg.get("content", ""))})

    messages.append({
        "role": "user",
        "content": f"Rewrite this image request into a Qwen diffusion prompt:\n\n{intent}",
    })

    response = await _client.chat.completions.create(
        model=settings.prompt_rewriter_model,
        messages=messages,
        max_tokens=settings.prompt_rewriter_max_tokens,
        stream=False,
    )

    rewritten = response.choices[0].message.content.strip()
    logger.info("Prompt rewritten: %.60s -> %.80s", intent, rewritten)
    return rewritten
