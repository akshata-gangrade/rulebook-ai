from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    Represents a normalized piece of source content before chunking.

    A Document corresponds to content extracted from one source file.
    The ingestion layer produces these objects, and later stages consume them.
    """

    document_id: str = Field(
        min_length=1,
        description="Stable identifier for the source document.",
    )

    source_file: str = Field(
        min_length=1,
        description="Original source file path or filename.",
    )

    file_type: str = Field(
        min_length=1,
        description="Source format such as markdown, pdf, or csv.",
    )

    text: str = Field(
        min_length=1,
        description="Extracted and normalized source text.",
    )

    section: str | None = Field(
        default=None,
        description="Section identifier or heading when available.",
    )

    page: int | None = Field(
        default=None,
        ge=1,
        description="1-based PDF page number when applicable.",
    )