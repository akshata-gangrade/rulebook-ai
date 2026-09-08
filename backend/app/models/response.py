from pydantic import BaseModel, Field


class EvidenceResponse(BaseModel):
    """
    Evidence returned to the frontend for citation display.
    """

    chunk_id: str
    text: str
    section: str | None = None
    page: int | None = None
    source_file: str
    similarity: float = Field(ge=0.0, le=1.0)


class AskResponse(BaseModel):
    """
    Final structured response from the /ask endpoint.
    """

    status: str
    answer: str | None = None
    reason: str | None = None
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )
    evidence: list[EvidenceResponse] = Field(
        default_factory=list,
    )