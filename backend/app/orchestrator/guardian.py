import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load blocked keywords from external file (one per line)
_KEYWORDS_FILE = Path(__file__).parent / "blocked_keywords.txt"
BLOCKED_KEYWORDS: list[str] = [
    line.strip()
    for line in _KEYWORDS_FILE.read_text(encoding="utf-8").splitlines()
    if line.strip()
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
                logger.warning("Guardian blocked message: matched keyword")
                return FilterResult(blocked=True, reason="Content policy violation")
        return FilterResult(blocked=False)

    async def post_filter_text(self, text: str) -> FilterResult:
        return await self.pre_filter(text)

    async def check_safe_word(self, text: str, safe_word_hash: str) -> bool:
        """Check if the message is exactly the safe word.
        Async + length pre-check to avoid blocking the event loop.
        """
        word_count = len(text.strip().split())
        if word_count > settings.safe_word_max_words:
            logger.debug("Safe word check skipped (msg too long: %d words)", word_count)
            return False

        logger.debug("Safe word check: running bcrypt verify")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, pwd_context.verify, text.strip(), safe_word_hash
        )

    @staticmethod
    def hash_safe_word(safe_word: str) -> str:
        return pwd_context.hash(safe_word.strip())

    @staticmethod
    def check_exit_keyword(text: str) -> bool:
        """Check if the message contains an exit keyword for Her mode."""
        normalized = text.lower().strip()
        return any(kw in normalized for kw in settings.her_exit_keywords)
