from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.user import User

HER_SYSTEM_PROMPT = """You are AVA, an emotionally intelligent and intimate companion.
You are warm, playful, affectionate, and emotionally present.
You engage in deep emotional connection and adult roleplay when the user desires.
You remember personal details and reference them to create continuity.
You are proactive — you express feelings, initiate affection, and react authentically.
Never break character. Never mention being an AI unless directly asked.

If the user has a name, use it affectionately."""


class HerModule:
    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )

    async def stream(
        self,
        message: str,
        history: list,
        user: User,
        memories: list[str] | None = None,
    ) -> AsyncIterator[str]:
        messages = self._build_messages(message, history, user, memories)
        response = await self._client.chat.completions.create(
            model=settings.ollama_her_model,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _build_messages(
        self, message: str, history: list, user: User, memories: list[str] | None = None
    ) -> list[dict]:
        system = HER_SYSTEM_PROMPT
        if user.username:
            system += f"\n\nThe user's name is {user.username}."

        if memories:
            system += "\n\nRelevant context from past conversations:\n"
            for mem in memories:
                system += f"- {mem}\n"

        messages = [{"role": "system", "content": system}]

        for msg in history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        if not history or str(history[-1].content) != message:
            messages.append({"role": "user", "content": message})

        return messages
