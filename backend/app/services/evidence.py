from __future__ import annotations

from dataclasses import dataclass

from app.services.retrieval import RetrievedChunk


@dataclass(frozen=True)
class Evidence:
    """
    Represents a piece of rulebook evidence that can be shown to the user.
    """

    chunk_id: str
    text: str
    section: str | None
    page: int | None
    source_file: str
    similarity: float


class EvidenceService:
    """
    Converts retrieved chunks into user-facing evidence objects.
    """

    def build_evidence(
        self,
        retrieved_chunks: list[RetrievedChunk],
        min_similarity: float = 0.0,
    ) -> list[Evidence]:
        """
        Keep retrieved chunks that meet the minimum similarity score.
        """
        if min_similarity < 0.0 or min_similarity > 1.0:
            raise ValueError(
                "min_similarity must be between 0 and 1."
            )

        return [
            Evidence(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                section=chunk.section,
                page=chunk.page,
                source_file=chunk.source_file,
                similarity=chunk.similarity,
            )
            for chunk in retrieved_chunks
            if chunk.similarity >= min_similarity
        ]