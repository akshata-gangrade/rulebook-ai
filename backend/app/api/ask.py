from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.request import AskRequest
from app.models.response import AskResponse, EvidenceResponse
from app.services.answer_generator import AnswerGenerator
from app.services.conflict_detector import ConflictDetector
from app.services.coverage_detector import CoverageDetector
from app.services.embeddings import EmbeddingService
from app.services.evidence import EvidenceService
from app.services.llm import LLMService
from app.services.retrieval import RetrievalService
from app.services.vector_store import VectorStore


router = APIRouter()


def get_pipeline(
    settings: Settings = Depends(get_settings),
):
    """
    Build the services required by the /ask pipeline.
    """
    backend_root = Path(__file__).resolve().parents[2]

    chroma_path = backend_root / settings.chroma_persist_directory

    embedding_service = EmbeddingService()
    vector_store = VectorStore(str(chroma_path))

    retrieval_service = RetrievalService(
        settings=settings,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    evidence_service = EvidenceService()

    llm_service = LLMService(settings)

    coverage_detector = CoverageDetector(
        similarity_threshold=0.30,
    )

    conflict_detector = ConflictDetector(
        llm_service=llm_service,
        conflict_threshold=settings.conflict_threshold,
    )

    answer_generator = AnswerGenerator(
        llm_service=llm_service,
    )

    return (
        retrieval_service,
        evidence_service,
        coverage_detector,
        conflict_detector,
        answer_generator,
    )


@router.post(
    "/ask",
    response_model=AskResponse,
)
def ask_question(
    request: AskRequest,
    pipeline=Depends(get_pipeline),
) -> AskResponse:
    """
    Answer a question using the rulebook evidence pipeline.
    """
    (
        retrieval_service,
        evidence_service,
        coverage_detector,
        conflict_detector,
        answer_generator,
    ) = pipeline

    question = request.question.strip()

    # 1. Retrieve relevant chunks.
    retrieved_chunks = retrieval_service.retrieve(
        question,
        top_k=12,
    )

    # 2. Convert retrieved chunks into citation-ready evidence.
    evidence = evidence_service.build_evidence(
        retrieved_chunks,
        min_similarity=0.25,
    )

    # 3. Determine whether the rulebook covers the question.
    coverage = coverage_detector.detect(evidence)

    if not coverage.covered:
        return AskResponse(
            status="NOT_COVERED",
            answer=None,
            reason=(
                "The rulebook does not provide sufficient evidence "
                "to answer this question."
            ),
            confidence=coverage.confidence,
            evidence=[
                EvidenceResponse(
                    chunk_id=item.chunk_id,
                    text=item.text,
                    section=item.section,
                    page=item.page,
                    source_file=item.source_file,
                    similarity=item.similarity,
                )
                for item in evidence
            ],
        )

    # 4. Check covered questions for conflicting rules.
    conflict = conflict_detector.detect(
        question=question,
        evidence=evidence,
    )

    # 5. Determine the final status.
    if (
        conflict.conflict
        and conflict.confidence >= settings.conflict_threshold
    ):
        return AskResponse(
            status="CONFLICT",
            answer=None,
            reason=conflict.reason,
            confidence=conflict.confidence,
            evidence=[
                EvidenceResponse(
                    chunk_id=item.chunk_id,
                    text=item.text,
                    section=item.section,
                    page=item.page,
                    source_file=item.source_file,
                    similarity=item.similarity,
                )
                for item in evidence
            ],
        )

    # 6. Generate a grounded answer.
    answer = answer_generator.generate(
        question=question,
        evidence=evidence,
    )

    return AskResponse(
        status="ANSWERED",
        answer=answer,
        reason=None,
        confidence=coverage.confidence,
        evidence=[
            EvidenceResponse(
                chunk_id=item.chunk_id,
                text=item.text,
                section=item.section,
                page=item.page,
                source_file=item.source_file,
                similarity=item.similarity,
            )
            for item in evidence
        ],
    )