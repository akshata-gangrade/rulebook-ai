from __future__ import annotations

from dataclasses import dataclass

from app.services.evidence import Evidence


@dataclass(frozen=True)
class CoverageResult:
    """
    Represents whether the available evidence sufficiently covers a question.
    """

    covered: bool
    confidence: float
    evidence_count: int


class CoverageDetector:
    """
    Determines whether retrieved evidence is strong enough
    to consider a question covered by the rulebook.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.30,
        minimum_evidence: int = 1,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0 and 1."
            )

        if minimum_evidence <= 0:
            raise ValueError(
                "minimum_evidence must be greater than 0."
            )

        self.similarity_threshold = similarity_threshold
        self.minimum_evidence = minimum_evidence

    def detect(
        self,
        evidence: list[Evidence],
    ) -> CoverageResult:
        """
        Determine whether enough relevant evidence exists.
        """
        relevant_evidence = [
            item
            for item in evidence
            if item.similarity >= self.similarity_threshold
        ]

        if len(relevant_evidence) < self.minimum_evidence:
            return CoverageResult(
                covered=False,
                confidence=(
                    relevant_evidence[0].similarity
                    if relevant_evidence
                    else 0.0
                ),
                evidence_count=len(relevant_evidence),
            )

        confidence = max(
            item.similarity
            for item in relevant_evidence
        )

        return CoverageResult(
            covered=True,
            confidence=confidence,
            evidence_count=len(relevant_evidence),
        )