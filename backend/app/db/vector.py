from qdrant_client import QdrantClient, models
from app.core.config import settings

COLLECTION_NAME = "ava_memories"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 output dimension


class VectorStore:
    def __init__(self):
        self._client: QdrantClient | None = None

    def connect(self) -> None:
        """Called once during FastAPI lifespan startup."""
        self._client = QdrantClient(url=settings.qdrant_url)
        collections = [c.name for c in self._client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIM,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert(
        self,
        vector_id: str,
        embedding: list[float],
        payload: dict,
    ) -> None:
        self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    def search(
        self,
        embedding: list[float],
        user_id: str,
        limit: int = 5,
    ) -> list[dict]:
        results = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=embedding,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            ),
            limit=limit,
        )
        return [
            {"text": point.payload.get("text", ""), "score": point.score}
            for point in results.points
        ]

    def close(self) -> None:
        if self._client:
            self._client.close()


vector_store = VectorStore()
