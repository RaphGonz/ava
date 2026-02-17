import logging
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

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

    @staticmethod
    def check_safe_word(text: str, safe_word: str) -> bool:
        """Check if the message is exactly the safe word (plain text comparison)."""
        word_count = len(text.strip().split())
        if word_count > settings.safe_word_max_words:
            return False
        return text.strip().lower() == safe_word.strip().lower()

    @staticmethod
    def check_exit_keyword(text: str, exit_word: str | None = None) -> bool:
        """Check if the message matches the user's exit word, or falls back to global config."""
        normalized = text.lower().strip()
        if exit_word:
            return normalized == exit_word.strip().lower()
        return any(kw == normalized for kw in settings.her_exit_keywords)
