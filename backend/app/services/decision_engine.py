from __future__ import annotations

from dataclasses import dataclass

from app.services.conflict_detector import ConflictResult
from app.services.coverage_detector import CoverageResult


@dataclass(frozen=True)
class DecisionResult:
    """
    Represents the final classification of a user question.
    """

    status: str
    reason: str


class DecisionEngine:
    """
    Converts coverage and conflict analysis into a final decision.

    Possible statuses:
    - ANSWERED
    - NOT_COVERED
    - CONFLICT
    """

    ANSWERED = "ANSWERED"
    NOT_COVERED = "NOT_COVERED"
    CONFLICT = "CONFLICT"

    def decide(
        self,
        coverage: CoverageResult,
        conflict: ConflictResult,
    ) -> DecisionResult:
        """
        Determine the final response status.
        """

        if not coverage.covered:
            return DecisionResult(
                status=self.NOT_COVERED,
                reason="The rulebook does not provide sufficient evidence "
                "to answer this question.",
            )

        if (
            conflict.conflict
            and conflict.confidence >= 0.75
        ):
            return DecisionResult(
                status=self.CONFLICT,
                reason=conflict.reason,
            )

        return DecisionResult(
            status=self.ANSWERED,
            reason="Sufficient rulebook evidence was found "
            "without a confirmed conflict.",
        )