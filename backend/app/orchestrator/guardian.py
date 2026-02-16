from dataclasses import dataclass

from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BLOCKED_KEYWORDS: list[str] = [
    # Add disallowed content categories here.
    # This is intentionally minimal for MVP — expand based on policy.
    "Child", "Loli", "Yiff", "Guro", "Scat", "Bestiality", "Incest"
]


@dataclass
class FilterResult:
    blocked: bool
    reason: str | None = None


class Guardian:
    async def pre_filter(self, text: str) -> FilterResult:
        normalized = text.lower().strip()
        for keyword in BLOCKED_KEYWORDS:
            if keyword in normalized:
                return FilterResult(blocked=True, reason="Content policy violation")
        return FilterResult(blocked=False)

    async def post_filter_text(self, text: str) -> FilterResult:
        return await self.pre_filter(text)

    @staticmethod
    def check_safe_word(text: str, safe_word_hash: str) -> bool:
        """Check if the message is exactly the safe word."""
        return pwd_context.verify(text.strip(), safe_word_hash)

    @staticmethod
    def hash_safe_word(safe_word: str) -> str:
        return pwd_context.hash(safe_word.strip())

    @staticmethod
    def check_exit_keyword(text: str) -> bool:
        """Check if the message contains an exit keyword for Her mode."""
        normalized = text.lower().strip()
        return any(kw in normalized for kw in settings.her_exit_keywords)
