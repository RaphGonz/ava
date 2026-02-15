from enum import Enum

from openai import AsyncOpenAI

from app.core.config import settings


class Intent(str, Enum):
    SYSTEM_COMMAND = "system_command"
    EMOTIONAL_CHAT = "emotional_chat"
    IMAGE_REQUEST = "image_request"
    UNCLEAR = "unclear"


CLASSIFIER_PROMPT = """Classify the user's message into one of these categories:
- system_command: the user is asking for help with tasks, planning, reminders, information
- emotional_chat: the user wants to have a conversation, express feelings, chat casually
- image_request: the user is asking for an image, selfie, photo, or picture
- unclear: cannot determine

Respond with ONLY the category name, nothing else."""


class Router:
    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )

    async def classify(self, message: str) -> Intent:
        try:
            response = await self._client.chat.completions.create(
                model=settings.ollama_router_model,
                messages=[
                    {"role": "system", "content": CLASSIFIER_PROMPT},
                    {"role": "user", "content": message},
                ],
                temperature=0,
                max_tokens=20,
            )
            result = response.choices[0].message.content.strip().lower()
            for intent in Intent:
                if intent.value in result:
                    return intent
            return Intent.UNCLEAR
        except Exception:
            # If the router LLM is unavailable, default to chat
            return Intent.EMOTIONAL_CHAT
