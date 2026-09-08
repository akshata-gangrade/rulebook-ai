from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.services.chunking import Chunk


class EmbeddingService:
    """
    Generates vector embeddings locally using Sentence Transformers.

    No external API is required for embedding generation.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[list[float]]:
        """
        Generate embeddings for all chunks.
        """
        texts = [chunk.text for chunk in chunks]
        return self.embed_texts(texts)

    def embed_query(self, query: str) -> list[float]:
        """
        Generate an embedding for a user's question.
        """
        if not query.strip():
            raise ValueError("Query cannot be empty.")

        embeddings = self.embed_texts([query])
        return embeddings[0]