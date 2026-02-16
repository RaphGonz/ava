import uuid

from sentence_transformers import SentenceTransformer

from app.db.vector import vector_store

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(text: str) -> list[float]:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def extract_facts(user_message: str, assistant_response: str) -> list[str]:
    """Extract memorable facts from an exchange.
    MVP: store the full exchange if long enough.
    Future: use an LLM to extract structured facts.
    """
    combined = f"User said: {user_message}\nAssistant replied: {assistant_response}"
    if len(combined) > 40:
        return [combined]
    return []


async def remember(user_id: str, text: str, source_message_id: str) -> str:
    """Embed and store a fact. Returns the vector_id."""
    vector_id = str(uuid.uuid4())
    embedding = embed(text)
    vector_store.upsert(
        vector_id=vector_id,
        embedding=embedding,
        payload={
            "user_id": user_id,
            "text": text,
            "source_message_id": source_message_id,
        },
    )
    return vector_id


async def recall(user_id: str, query: str, limit: int = 5) -> list[str]:
    """Retrieve top-k relevant memories for a user given a query."""
    embedding = embed(query)
    results = vector_store.search(
        embedding=embedding,
        user_id=user_id,
        limit=limit,
    )
    return [r["text"] for r in results]
