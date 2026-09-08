from __future__ import annotations

from dataclasses import dataclass

from app.services.evidence import Evidence


@dataclass(frozen=True)
class CoverageResult:
    """
    Represents whether the rulebook contains enough evidence
    to answer the user's question.
    """

    covered: bool
    confidence: float
    evidence_count: int


class CoverageDetector:
    """
    Determines whether a question is sufficiently covered by
    retrieved rulebook evidence.

    Confidence is an evidence-based heuristic. It is intentionally
    separate from raw vector similarity because similarity is not
    equivalent to answer correctness.
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

        evidence_count = len(
            relevant_evidence
        )

        if evidence_count < self.minimum_evidence:
            return CoverageResult(
                covered=False,
                confidence=self._not_covered_confidence(
                    evidence
                ),
                evidence_count=evidence_count,
            )

        confidence = self._covered_confidence(
            relevant_evidence
        )

        return CoverageResult(
            covered=True,
            confidence=confidence,
            evidence_count=evidence_count,
        )

    def _covered_confidence(
        self,
        evidence: list[Evidence],
    ) -> float:
        """
        Calculate confidence for a covered question.

        Factors:
        - strength of the best retrieved evidence
        - number of supporting evidence items

        The result represents confidence in evidence coverage,
        not a mathematical probability of answer correctness.
        """

        if not evidence:
            return 0.0

        similarities = sorted(
            (
                item.similarity
                for item in evidence
            ),
            reverse=True,
        )

        top_score = similarities[0]

        # Normalize the top similarity around the useful
        # retrieval range of the current embedding model.
        strength = min(
            top_score / 0.50,
            1.0,
        )

        # Multiple independent pieces of evidence increase
        # confidence, but with diminishing returns.
        support = min(
            len(evidence) / 3.0,
            1.0,
        )

        confidence = (
            0.75
            + (0.15 * strength)
            + (0.10 * support)
        )

        return round(
            min(confidence, 0.99),
            2,
        )

    def _not_covered_confidence(
        self,
        evidence: list[Evidence],
    ) -> float:
        """
        Estimate confidence that the rulebook does not cover
        the question.

        A larger gap between the best retrieved similarity and
        the coverage threshold gives higher confidence that
        relevant evidence was not found.
        """

        if not evidence:
            return 0.99

        top_score = max(
            item.similarity
            for item in evidence
        )

        if top_score >= self.similarity_threshold:
            return 0.70

        gap = (
            self.similarity_threshold
            - top_score
        )

        normalized_gap = (
            gap / self.similarity_threshold
        )

        confidence = (
            0.94
            + (0.05 * normalized_gap)
        )

        return round(
            min(confidence, 0.99),
            2,
        )