import asyncio
import logging
import time
import uuid

from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.db.vector import vector_store

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model %s...", settings.embedding_model_name)
        _model = SentenceTransformer(settings.embedding_model_name)
        logger.info("Embedding model loaded")
    return _model


def _embed_sync(text: str) -> list[float]:
    """Synchronous embedding — call via asyncio.to_thread()."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


async def embed(text: str) -> list[float]:
    """Async-safe embedding via thread pool."""
    return await asyncio.to_thread(_embed_sync, text)


def extract_facts(user_message: str, assistant_response: str) -> list[str]:
    """Extract memorable facts from an exchange.
    MVP: store the full exchange if long enough.
    Future: use an LLM to extract structured facts.
    """
    combined = f"User said: {user_message}\nAssistant replied: {assistant_response}"
    if len(combined) > settings.memory_min_fact_length:
        return [combined]
    return []


def _upsert_sync(vector_id: str, embedding: list[float], payload: dict):
    """Synchronous Qdrant upsert — call via asyncio.to_thread()."""
    vector_store.upsert(vector_id=vector_id, embedding=embedding, payload=payload)


def _search_sync(embedding: list[float], user_id: str, limit: int) -> list[dict]:
    """Synchronous Qdrant search — call via asyncio.to_thread()."""
    return vector_store.search(embedding=embedding, user_id=user_id, limit=limit)


async def remember(user_id: str, text: str, source_message_id: str) -> str:
    """Embed and store a fact. Returns the vector_id."""
    start = time.time()
    vector_id = str(uuid.uuid4())
    embedding = await embed(text)
    await asyncio.to_thread(
        _upsert_sync,
        vector_id,
        embedding,
        {
            "user_id": user_id,
            "text": text,
            "source_message_id": source_message_id,
        },
    )
    elapsed = (time.time() - start) * 1000
    logger.info("[user:%s] remember() took %.0fms", user_id[:8], elapsed)
    return vector_id


async def recall(user_id: str, query: str, limit: int | None = None) -> list[str]:
    """Retrieve top-k relevant memories for a user given a query."""
    if limit is None:
        limit = settings.memory_recall_limit
    start = time.time()
    embedding = await embed(query)
    results = await asyncio.to_thread(_search_sync, embedding, user_id, limit)
    elapsed = (time.time() - start) * 1000
    logger.info(
        "[user:%s] recall(%r) returned %d results in %.0fms",
        user_id[:8], query[:40], len(results), elapsed,
    )
    return [r["text"] for r in results]


async def recall_as_tool(user_id: str, query: str) -> str:
    """Recall memories formatted as a tool result string."""
    memories = await recall(user_id, query)
    if not memories:
        return "No relevant memories found."
    return "\n".join(f"- {m}" for m in memories)
