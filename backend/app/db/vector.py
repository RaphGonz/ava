from qdrant_client import QdrantClient, models
from app.core.config import settings


class VectorStore:
    def __init__(self):
        self._client: QdrantClient | None = None

    def connect(self) -> None:
        """Called once during FastAPI lifespan startup."""
        self._client = QdrantClient(url=settings.qdrant_url)
        collections = [c.name for c in self._client.get_collections().collections]
        if settings.qdrant_collection_name not in collections:
            self._client.create_collection(
                collection_name=settings.qdrant_collection_name,
                vectors_config=models.VectorParams(
                    size=settings.embedding_vector_dim,
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
            collection_name=settings.qdrant_collection_name,
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
        limit: int | None = None,
    ) -> list[dict]:
        if limit is None:
            limit = settings.memory_recall_limit
        results = self._client.query_points(
            collection_name=settings.qdrant_collection_name,
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
