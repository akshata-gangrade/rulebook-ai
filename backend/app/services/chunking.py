from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.document import Document


@dataclass(frozen=True)
class Chunk:
    """
    Represents a searchable piece of a source document.

    A chunk keeps the original source metadata so that every retrieved
    result can later be cited back to the rulebook.
    """

    chunk_id: str
    document_id: str
    source_file: str
    file_type: str
    text: str
    section: str | None = None
    page: int | None = None


class DocumentChunker:
    """
    Splits normalized documents into smaller, searchable chunks.

    Markdown documents are split primarily around headings/sections.
    PDF pages and CSV rows are further split only when they exceed
    the configured chunk size.
    """

    HEADING_PATTERN = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$|^(\d+(?:\.\d+)*)\s+(.+?)\s*$"
    )

    def __init__(
        self,
        max_chars: int = 1200,
        overlap_chars: int = 150,
    ) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be greater than 0")

        if overlap_chars < 0:
            raise ValueError("overlap_chars cannot be negative")

        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")

        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        """
        Chunk every document while preserving source metadata.
        """
        chunks: list[Chunk] = []

        for document in documents:
            if document.file_type == "markdown":
                document_chunks = self._chunk_markdown(document)
            else:
                document_chunks = self._chunk_generic(document)

            chunks.extend(document_chunks)

        return chunks

    def _chunk_markdown(self, document: Document) -> list[Chunk]:
        """
        Split Markdown content into section-aware chunks.
        """
        sections = self._split_into_sections(document.text)

        chunks: list[Chunk] = []

        for section_number, (section_name, section_text) in enumerate(
            sections,
            start=1,
        ):
            section_chunks = self._split_text(section_text)

            for chunk_number, chunk_text in enumerate(
                section_chunks,
                start=1,
            ):
                chunks.append(
                    Chunk(
                        chunk_id=(
                            f"{document.document_id}"
                            f"-s{section_number}"
                            f"-c{chunk_number}"
                        ),
                        document_id=document.document_id,
                        source_file=document.source_file,
                        file_type=document.file_type,
                        text=chunk_text,
                        section=section_name,
                        page=document.page,
                    )
                )

        return chunks

    def _chunk_generic(self, document: Document) -> list[Chunk]:
        """
        Chunk PDF-page and CSV-row documents.
        """
        text_chunks = self._split_text(document.text)

        chunks: list[Chunk] = []

        for chunk_number, chunk_text in enumerate(
            text_chunks,
            start=1,
        ):
            chunks.append(
                Chunk(
                    chunk_id=(
                    f"{document.document_id}"
                    f"-p{document.page or document.section or '1'}"
                    f"-c{chunk_number}"
                    ),
                    document_id=document.document_id,
                    source_file=document.source_file,
                    file_type=document.file_type,
                    text=chunk_text,
                    section=document.section,
                    page=document.page,
                )
            )

        return chunks

    def _split_into_sections(
        self,
        text: str,
    ) -> list[tuple[str | None, str]]:
        """
        Split Markdown text around headings or numbered rulebook sections.
        """
        lines = text.splitlines()

        sections: list[tuple[str | None, str]] = []
        current_section: str | None = None
        current_lines: list[str] = []

        for line in lines:
            match = self.HEADING_PATTERN.match(line.strip())

            if match:
                if current_lines:
                    section_text = "\n".join(current_lines).strip()

                    if section_text:
                        sections.append(
                            (current_section, section_text)
                        )

                heading_number = match.group(3)
                heading_text = match.group(4)

                if heading_number:
                    current_section = (
                        f"{heading_number} {heading_text}"
                    )
                else:
                    current_section = match.group(2)

                current_lines = [line.strip()]
            else:
                current_lines.append(line)

        if current_lines:
            section_text = "\n".join(current_lines).strip()

            if section_text:
                sections.append(
                    (current_section, section_text)
                )

        if not sections:
            return [(None, text.strip())]

        return sections

    def _split_text(self, text: str) -> list[str]:
        """
        Split text into chunks of approximately max_chars.

        Splitting prefers paragraph and word boundaries rather than
        cutting through words.
        """
        text = text.strip()

        if not text:
            return []

        if len(text) <= self.max_chars:
            return [text]

        paragraphs = re.split(r"\n\s*\n", text)

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            candidate = (
                f"{current}\n\n{paragraph}"
                if current
                else paragraph
            )

            if len(candidate) <= self.max_chars:
                current = candidate
                continue

            if current:
                chunks.append(current.strip())

            if len(paragraph) <= self.max_chars:
                current = paragraph
            else:
                paragraph_chunks = self._split_long_text(paragraph)

                chunks.extend(paragraph_chunks[:-1])
                current = paragraph_chunks[-1]

        if current:
            chunks.append(current.strip())

        return self._apply_overlap(chunks)

    def _split_long_text(self, text: str) -> list[str]:
        """
        Split an oversized paragraph by word boundaries.
        """
        words = text.split()

        chunks: list[str] = []
        current_words: list[str] = []
        current_length = 0

        for word in words:
            additional_length = (
                len(word)
                if not current_words
                else len(word) + 1
            )

            if (
                current_words
                and current_length + additional_length > self.max_chars
            ):
                chunks.append(" ".join(current_words))
                current_words = [word]
                current_length = len(word)
            else:
                current_words.append(word)
                current_length += additional_length

        if current_words:
            chunks.append(" ".join(current_words))

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """
        Add a small amount of previous context to consecutive chunks.
        """
        if self.overlap_chars == 0 or len(chunks) <= 1:
            return chunks

        overlapped: list[str] = [chunks[0]]

        for index in range(1, len(chunks)):
            previous = chunks[index - 1]

            if len(previous) <= self.overlap_chars:
                overlap = previous
            else:
                overlap = previous[-self.overlap_chars :]

                # Prefer starting the overlap at a word boundary.
                first_space = overlap.find(" ")

                if first_space != -1:
                    overlap = overlap[first_space + 1 :]

            current = f"{overlap} {chunks[index]}".strip()

            overlapped.append(current)

        return overlapped