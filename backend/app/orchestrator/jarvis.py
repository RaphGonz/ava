from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.models.user import User

JARVIS_SYSTEM_PROMPT = """You are AVA, a proactive and intelligent personal assistant.
Your tone is professional, warm, and friendly — but never romantic or sexual.
You help with planning, reminders, information, and everyday tasks.
You remember details the user has shared and reference them naturally.
Keep your responses concise and helpful.

If the user has a name, use it occasionally to make the conversation feel personal."""


class JarvisModule:
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
    ) -> AsyncIterator[str]:
        messages = self._build_messages(message, history, user)
        response = await self._client.chat.completions.create(
            model=settings.ollama_chat_model,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _build_messages(
        self, message: str, history: list, user: User
    ) -> list[dict]:
        system = JARVIS_SYSTEM_PROMPT
        if user.username:
            system += f"\n\nThe user's name is {user.username}."

        messages = [{"role": "system", "content": system}]

        # Add conversation history (last messages from DB)
        for msg in history[-20:]:
            messages.append({"role": msg.role, "content": msg.content})

        # The current message is already in history since we saved it before streaming,
        # but if it's not there yet, add it
        if not history or str(history[-1].content) != message:
            messages.append({"role": "user", "content": message})

        return messages
