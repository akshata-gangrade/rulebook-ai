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
    Retrieves relevant rulebook chunks using hybrid search.

    Hybrid retrieval combines:
    1. Semantic search for meaning-based matches.
    2. Keyword search for exact rulebook terminology,
       thresholds, and structured table entries.
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
        Retrieve relevant chunks using semantic and keyword search.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        k = top_k or self.settings.top_k

        if k <= 0:
            raise ValueError("top_k must be greater than 0.")

        # ---------------------------------------------------------
        # 1. Semantic retrieval
        # ---------------------------------------------------------
        query_embedding = self.embedding_service.embed_query(question)

        semantic_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
        )

        semantic_chunks = self._parse_results(
            semantic_results
        )

        # ---------------------------------------------------------
        # 2. Keyword retrieval
        # ---------------------------------------------------------
        keywords = self._extract_keywords(question)

        keyword_results = self.vector_store.keyword_search(
            keywords=keywords,
            limit=k,
        )

        # ---------------------------------------------------------
        # 3. Merge results without duplicates
        # ---------------------------------------------------------
        merged: dict[str, RetrievedChunk] = {}

        for chunk in semantic_chunks:
            merged[chunk.chunk_id] = chunk

        for result in keyword_results:
            chunk_id = result["id"]

            if chunk_id in merged:
                continue

            metadata = result["metadata"]

            merged[chunk_id] = RetrievedChunk(
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

        candidates = list(merged.values())

        # ---------------------------------------------------------
        # 4. Keep a balance of semantic + keyword results
        # ---------------------------------------------------------
        semantic_count = max(1, k // 2)

        semantic_candidates = [
            chunk
            for chunk in candidates
            if chunk.distance != 1.0
        ]

        keyword_candidates = [
            chunk
            for chunk in candidates
            if chunk.distance == 1.0
        ]

        semantic_candidates.sort(
            key=lambda chunk: chunk.similarity,
            reverse=True,
        )

        selected = semantic_candidates[:semantic_count]

        selected_ids = {
            chunk.chunk_id
            for chunk in selected
        }

        remaining_slots = k - len(selected)

        remaining_candidates = [
            chunk
            for chunk in candidates
            if chunk.chunk_id not in selected_ids
        ]

        # Prefer keyword matches for the remaining slots.
        remaining_candidates.sort(
            key=lambda chunk: (
                chunk.distance != 1.0,
                -chunk.similarity,
            )
        )

        selected.extend(
            remaining_candidates[:remaining_slots]
        )

        return selected[:k]

    @staticmethod
    def _extract_keywords(
        question: str,
    ) -> list[str]:
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

        keywords: list[str] = []

        for word in words:
            if len(word) < 4:
                continue

            if word in stop_words:
                continue

            keywords.append(word)

            # Basic singular/plural normalization.
            if word.endswith("ies") and len(word) > 4:
                keywords.append(
                    word[:-3] + "y"
                )
            elif word.endswith("s") and len(word) > 4:
                keywords.append(
                    word[:-1]
                )

        return list(dict.fromkeys(keywords))

    @staticmethod
    def _parse_results(
        results: dict,
    ) -> list[RetrievedChunk]:
        """
        Convert ChromaDB results into application-level objects.
        """

        ids = results.get(
            "ids",
            [[]],
        )[0]

        documents = results.get(
            "documents",
            [[]],
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]],
        )[0]

        distances = results.get(
            "distances",
            [[]],
        )[0]

        retrieved: list[RetrievedChunk] = []

        for (
            chunk_id,
            text,
            metadata,
            distance,
        ) in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            similarity = max(
                0.0,
                min(
                    1.0,
                    1.0 - float(distance),
                ),
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
                    distance=float(distance),
                    similarity=similarity,
                )
            )

        return retrieved