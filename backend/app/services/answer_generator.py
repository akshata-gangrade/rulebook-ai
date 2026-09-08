from __future__ import annotations

from app.services.evidence import Evidence
from app.services.llm import LLMService


class AnswerGenerator:
    """
    Generates answers using only the retrieved rulebook evidence.
    """

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> str:
        """
        Generate a grounded answer from rulebook evidence.
        """
        if not question.strip():
            raise ValueError("Question cannot be empty.")

        if not evidence:
            raise ValueError(
                "Cannot generate an answer without evidence."
            )

        prompt = self._build_prompt(question, evidence)

        return self.llm_service.generate(
            prompt,
            temperature=0.0,
        ).strip()

    @staticmethod
    def _build_prompt(
        question: str,
        evidence: list[Evidence],
    ) -> str:
        """
        Build a grounded answer-generation prompt.
        """
        evidence_parts = []

        for index, item in enumerate(evidence, start=1):
            source = item.source_file

            if item.section:
                source += f", section: {item.section}"

            if item.page:
                source += f", page: {item.page}"

            evidence_parts.append(
                f"""
Evidence {index}
Source: {source}
Similarity: {item.similarity:.4f}

{item.text}
""".strip()
            )

        joined_evidence = "\n\n".join(evidence_parts)

        return f"""
You are the answer-generation component of a university
rulebook question-answering system.

Answer the user's question using ONLY the provided rulebook evidence.

Rules:
- Do not use outside knowledge.
- Do not invent policies or requirements.
- Do not make assumptions that are not supported by the evidence.
- Give a direct and concise answer.
- If the evidence contains conditions or exceptions, mention them.
- Do not mention that you are an AI.
- Do not mention the retrieval system.

User question:
{question}

Rulebook evidence:
{joined_evidence}

Write the final answer now.
""".strip()