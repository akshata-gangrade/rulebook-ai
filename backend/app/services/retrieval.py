from __future__ import annotations

from dataclasses import dataclass
import re

from app.core.config import Settings
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    """
    Represents a rulebook chunk retrieved for a user question.
    """

    chunk_id: str
    text: str
    document_id: str
    source_file: str
    file_type: str
    section: str | None
    page: int | None
    distance: float
    similarity: float


class RetrievalService:
    """
    Retrieves relevant rulebook chunks using semantic and keyword search.
    """

    def __init__(
        self,
        settings: Settings,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ) -> None:
        self.settings = settings
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        question: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks using both semantic and keyword search.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        k = top_k or self.settings.top_k

        # Semantic retrieval.
        query_embedding = self.embedding_service.embed_query(question)

        semantic_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
        )

        retrieved = self._parse_results(semantic_results)

        # Keyword retrieval.
        keywords = self._extract_keywords(question)

        keyword_results = self.vector_store.keyword_search(
            keywords=keywords,
            limit=k,
        )

        existing_ids = {
            chunk.chunk_id
            for chunk in retrieved
        }

        for result in keyword_results:
            chunk_id = result["id"]

            if chunk_id in existing_ids:
                continue

            metadata = result["metadata"]

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=result["document"],
                    document_id=metadata["document_id"],
                    source_file=metadata["source_file"],
                    file_type=metadata["file_type"],
                    section=metadata.get("section"),
                    page=metadata.get("page"),
                    distance=1.0,
                    similarity=0.30,
                )
            )

        return retrieved[:k]

    @staticmethod
    def _extract_keywords(question: str) -> list[str]:
        """
        Extract meaningful keywords for lexical retrieval.
        """
        stop_words = {
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "how",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "for",
            "to",
            "of",
            "in",
            "on",
            "at",
            "can",
            "could",
            "would",
            "should",
            "does",
            "do",
            "and",
            "or",
            "with",
            "from",
            "this",
            "that",
            "these",
            "those",
            "student",
            "students",
        }

        words = re.findall(
            r"[a-zA-Z]+",
            question.lower(),
        )

        return [
            word
            for word in words
            if len(word) >= 4
            and word not in stop_words
        ]

    @staticmethod
    def _parse_results(
        results: dict,
    ) -> list[RetrievedChunk]:
        """
        Convert ChromaDB results into application-level objects.
        """
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved: list[RetrievedChunk] = []

        for chunk_id, text, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            similarity = max(
                0.0,
                min(1.0, 1.0 - distance),
            )

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    document_id=metadata["document_id"],
                    source_file=metadata["source_file"],
                    file_type=metadata["file_type"],
                    section=metadata.get("section"),
                    page=metadata.get("page"),
                    distance=distance,
                    similarity=similarity,
                )
            )

        return retrieved