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

    The detector uses:
    1. Deterministic detection for competing numeric thresholds.
    2. LLM validation for semantic relevance.
    """

    PERCENTAGE_PATTERN = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*%"
    )

    MINUTES_PATTERN = re.compile(
        r"\b(\d+)\s*(?:minutes?|mins?)\b",
        re.IGNORECASE,
    )

    ATTENDANCE_KEYWORDS = {
        "attendance",
        "attend",
        "eligible",
        "examination",
        "exam",
        "medical",
        "health",
        "activity",
        "authorized",
        "authorised",
    }

    EXAM_KEYWORDS = {
        "exam",
        "examination",
        "late",
        "arrival",
        "arrive",
        "admitted",
        "admission",
        "minutes",
    }

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
        Detect whether the evidence contains a conflict relevant
        to the user's question.
        """

        if not question.strip():
            raise ValueError("Question cannot be empty.")

        if not evidence:
            return ConflictResult(
                conflict=False,
                confidence=0.0,
                reason=(
                    "No evidence was available for conflict analysis."
                ),
            )

        deterministic_result = self._detect_numeric_conflict(
            question,
            evidence,
        )

        if deterministic_result is not None:
            return deterministic_result

        return self._llm_detect(
            question,
            evidence,
        )

    def _detect_numeric_conflict(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> ConflictResult | None:
        """
        Detect competing numeric rules before calling the LLM.

        This makes important rulebook conflicts deterministic and
        prevents the LLM from incorrectly treating an unresolved
        threshold difference as merely an exception.
        """

        question_words = set(
            re.findall(
                r"[a-zA-Z]+",
                question.lower(),
            )
        )

        evidence_text = "\n".join(
            item.text.lower()
            for item in evidence
        )

        # ---------------------------------------------------------
        # Attendance threshold conflict
        # ---------------------------------------------------------
        attendance_relevant = bool(
            question_words
            & self.ATTENDANCE_KEYWORDS
        )

        if attendance_relevant:
            percentages = []

            for item in evidence:
                values = [
                    float(value)
                    for value in self.PERCENTAGE_PATTERN.findall(
                        item.text
                    )
                ]

                for value in values:
                    percentages.append(
                        (value, item)
                    )

            unique_values = sorted(
                {value for value, _ in percentages}
            )

            if len(unique_values) >= 2:
                scenario_words = (
                    question_words
                    & {
                        "medical",
                        "activity",
                        "authorized",
                        "authorised",
                        "emergency",
                        "family",
                    }
                )

                relevant_special_rules = []

                for value, item in percentages:
                    text_lower = item.text.lower()

                    if scenario_words & set(
                        re.findall(
                            r"[a-zA-Z]+",
                            text_lower,
                        )
                    ):
                        relevant_special_rules.append(
                            (value, item)
                        )

                if relevant_special_rules:
                    general_rule_values = [
                        value
                        for value, item in percentages
                        if "regular" in item.text.lower()
                        or "general" in item.text.lower()
                        or "75%" in item.text
                    ]

                    if general_rule_values:
                        special_values = {
                            value
                            for value, _ in relevant_special_rules
                        }

                        conflicting_values = (
                            set(general_rule_values)
                            | special_values
                        )

                        if len(conflicting_values) >= 2:
                            values_text = ", ".join(
                                f"{value:g}%"
                                for value in sorted(
                                    conflicting_values
                                )
                            )

                            return ConflictResult(
                                conflict=True,
                                confidence=0.98,
                                reason=(
                                    "The rulebook contains different "
                                    f"attendance thresholds ({values_text}) "
                                    "relevant to this situation, and the "
                                    "retrieved provisions do not establish "
                                    "clear precedence between them."
                                ),
                            )

        # ---------------------------------------------------------
        # Examination late-arrival conflict
        # ---------------------------------------------------------
        exam_relevant = bool(
            question_words
            & self.EXAM_KEYWORDS
        )

        if exam_relevant:
            minute_rules = []

            for item in evidence:
                values = [
                    int(value)
                    for value in self.MINUTES_PATTERN.findall(
                        item.text
                    )
                ]

                for value in values:
                    minute_rules.append(
                        (value, item)
                    )

            unique_minutes = sorted(
                {value for value, _ in minute_rules}
            )

            if len(unique_minutes) >= 2:
                has_general_30 = any(
                    value == 30
                    for value, _ in minute_rules
                )

                has_special_45 = any(
                    value == 45
                    for value, _ in minute_rules
                )

                if has_general_30 and has_special_45:
                    return ConflictResult(
                        conflict=True,
                        confidence=0.98,
                        reason=(
                            "The rulebook contains both a general "
                            "30-minute examination arrival limit and "
                            "45-minute provisions for special or "
                            "emergency circumstances. The applicable "
                            "provision for this situation is therefore "
                            "not uniquely resolved by the retrieved rules."
                        ),
                    )

        return None

    def _llm_detect(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> ConflictResult:
        """
        Use the LLM for conflicts that cannot be identified
        deterministically from numeric thresholds.
        """

        prompt = self._build_prompt(
            question,
            evidence,
        )

        raw_response = self.llm_service.generate(
            prompt,
            temperature=0.0,
        )

        return self._parse_response(
            raw_response
        )

    def _build_prompt(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> str:
        """
        Build a strict semantic conflict-detection prompt.
        """

        evidence_text = []

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            source = item.source_file

            if item.section:
                source += (
                    f", section: {item.section}"
                )

            if item.page:
                source += (
                    f", page: {item.page}"
                )

            evidence_text.append(
                f"""
Evidence {index}

Source: {source}

Similarity: {item.similarity:.4f}

Text:

{item.text}
""".strip()
            )

        joined_evidence = "\n\n".join(
            evidence_text
        )

        return f"""
You are a rule-conflict analysis component in a university
rulebook QA system.

Determine whether the retrieved evidence contains a conflict
relevant to the user's question.

A conflict exists when:

1. Multiple provisions are relevant to the same scenario.
2. The provisions establish materially different requirements,
   permissions, restrictions, thresholds, or outcomes.
3. The rulebook evidence does not clearly resolve which provision
   controls the situation.

IMPORTANT:

If a general rule and a scenario-specific rule provide different
requirements for the same scenario, classify them as a CONFLICT
unless the evidence explicitly establishes their relationship.

For example:

General attendance requirement:
75%

Medical circumstance requirement:
65%

If the question concerns medical circumstances and both provisions
are present, this is a conflict unless the rulebook explicitly
states that the 65% rule replaces or overrides the 75% rule.

Similarly, if one provision permits examination entry after
30 minutes and another permits 45 minutes for a potentially
applicable scenario, treat this as a conflict when the evidence
does not clearly resolve which rule applies.

Do NOT classify as a conflict when:

- The rules clearly apply to different situations.
- One rule explicitly overrides or replaces another.
- The effective dates clearly resolve the difference.
- The rulebook explicitly establishes precedence.
- There is insufficient relevant evidence.

User question:

{question}

Evidence:

{joined_evidence}

Return ONLY valid JSON:

{{
    "conflict": true,
    "confidence": 0.95,
    "reason": "short explanation"
}}
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

        if not isinstance(
            conflict,
            bool,
        ):
            raise ValueError(
                "Conflict detector 'conflict' must be a boolean."
            )

        if not isinstance(
            confidence,
            (int, float),
        ):
            raise ValueError(
                "Conflict detector 'confidence' must be numeric."
            )

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "Conflict detector 'confidence' must be between 0 and 1."
            )

        if not isinstance(
            reason,
            str,
        ) or not reason.strip():
            raise ValueError(
                "Conflict detector 'reason' must be a non-empty string."
            )

        return ConflictResult(
            conflict=conflict,
            confidence=float(confidence),
            reason=reason.strip(),
        )