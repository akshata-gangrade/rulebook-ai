from __future__ import annotations

from dataclasses import dataclass
import json
import re

from app.services.evidence import Evidence
from app.services.llm import LLMService


@dataclass(frozen=True)
class ConflictResult:
    """
    Represents whether the retrieved evidence contains a conflict.
    """

    conflict: bool
    confidence: float
    reason: str


class ConflictDetector:
    """
    Detects conflicts in retrieved rulebook evidence.

    The detector combines:
    1. Deterministic threshold detection.
    2. LLM-based semantic validation.
    """

    PERCENTAGE_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*%"
    )

    MINUTES_PATTERN = re.compile(
        r"\b(\d+)\s*(?:minutes?|mins?)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        llm_service: LLMService,
        conflict_threshold: float = 0.75,
    ) -> None:
        if not 0.0 <= conflict_threshold <= 1.0:
            raise ValueError(
                "conflict_threshold must be between 0 and 1."
            )

        self.llm_service = llm_service
        self.conflict_threshold = conflict_threshold

    def detect(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> ConflictResult:
        """
        Analyze evidence for a semantic conflict.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        if not evidence:
            return ConflictResult(
                conflict=False,
                confidence=0.0,
                reason="No evidence was available for conflict analysis.",
            )

        threshold_summary = self._extract_thresholds(evidence)

        prompt = self._build_prompt(
            question,
            evidence,
            threshold_summary,
        )

        raw_response = self.llm_service.generate(
            prompt,
            temperature=0.0,
        )

        return self._parse_response(raw_response)

    def _extract_thresholds(
        self,
        evidence: list[Evidence],
    ) -> str:
        """
        Extract potentially conflicting numeric thresholds.

        This does not declare a conflict by itself.
        It gives the LLM explicit visibility into important thresholds.
        """
        percentages: list[str] = []
        minutes: list[str] = []

        for item in evidence:
            percentages.extend(
                self.PERCENTAGE_PATTERN.findall(item.text)
            )

            minutes.extend(
                self.MINUTES_PATTERN.findall(item.text)
            )

        parts: list[str] = []

        unique_percentages = sorted(
            set(percentages),
            key=float,
        )

        unique_minutes = sorted(
            set(minutes),
            key=int,
        )

        if unique_percentages:
            parts.append(
                "Percentage thresholds found: "
                + ", ".join(
                    f"{value}%"
                    for value in unique_percentages
                )
            )

        if unique_minutes:
            parts.append(
                "Time thresholds found: "
                + ", ".join(
                    f"{value} minutes"
                    for value in unique_minutes
                )
            )

        if not parts:
            return "No explicit percentage or time thresholds were detected."

        return "\n".join(parts)

    def _build_prompt(
        self,
        question: str,
        evidence: list[Evidence],
        threshold_summary: str,
    ) -> str:
        """
        Build a strict prompt for semantic conflict detection.
        """
        evidence_text = []

        for index, item in enumerate(evidence, start=1):
            source = item.source_file

            if item.section:
                source += f", section: {item.section}"

            if item.page:
                source += f", page: {item.page}"

            evidence_text.append(
                f"""
Evidence {index}
Source: {source}
Similarity: {item.similarity:.4f}
Text:
{item.text}
""".strip()
            )

        joined_evidence = "\n\n".join(evidence_text)

        return f"""
You are a rule-conflict analysis component in a university rulebook QA system.

Your task is ONLY to determine whether the provided evidence contains
a genuine conflict relevant to the user's question.

A conflict exists when:
1. Two or more rules apply to the same situation described by the question.
2. They establish materially different requirements, permissions,
   restrictions, thresholds, or outcomes.
3. The evidence does not clearly establish that one rule is a valid
   exception, has a different scope, has a different effective date,
   or has clear precedence.

IMPORTANT:
Different thresholds can represent a genuine conflict when they apply
to the same scenario.

For example:
- General attendance requirement: 75%
- Medical circumstance requirement: 65%

If the question specifically concerns medical circumstances and the
evidence provides both thresholds without clearly resolving their
relationship, this should be treated as a conflict.

Do NOT call something a conflict merely because:
- two numbers are different,
- two rules discuss completely different situations,
- one rule clearly defines an exception,
- the evidence does not contain enough information.

Relevant extracted thresholds:
{threshold_summary}

Return ONLY valid JSON using exactly this structure:

{{
    "conflict": true or false,
    "confidence": number between 0 and 1,
    "reason": "short explanation"
}}

User question:
{question}

Evidence:
{joined_evidence}
""".strip()

    @staticmethod
    def _parse_response(
        response: str,
    ) -> ConflictResult:
        """
        Parse and validate the LLM's JSON response.
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Conflict detector returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Conflict detector response must be a JSON object."
            )

        conflict = data.get("conflict")
        confidence = data.get("confidence")
        reason = data.get("reason")

        if not isinstance(conflict, bool):
            raise ValueError(
                "Conflict detector 'conflict' must be a boolean."
            )

        if not isinstance(confidence, (int, float)):
            raise ValueError(
                "Conflict detector 'confidence' must be numeric."
            )

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Conflict detector 'confidence' must be between 0 and 1."
            )

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                "Conflict detector 'reason' must be a non-empty string."
            )

        return ConflictResult(
            conflict=conflict,
            confidence=float(confidence),
            reason=reason.strip(),
        )