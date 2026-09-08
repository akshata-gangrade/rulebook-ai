from __future__ import annotations

import csv
import re
from pathlib import Path

import pymupdf

from app.models.document import Document


class DocumentIngestor:
    """
    Reads supported rulebook files and converts them into normalized
    Document objects.

    Supported formats:
    - Markdown (.md)
    - PDF (.pdf)
    - CSV (.csv)
    """

    DOCUMENT_ID_MAP = {
        "university_rulebook_part1.md": "MU-RULEBOOK-2026",
        "university_rulebook_part2.md": "MU-RULEBOOK-2026-STUDENT",
        "university_rulebook_part3.pdf": "MU-RULEBOOK-2026-HOSTEL",
        "university_rulebook_part4.pdf": "MU-RULEBOOK-2026-FINANCE",
        "university_rulebook_part5.md": "MU-RULEBOOK-2026-OPERATIONS",
        "university_rulebook_part6.md": "MU-RULEBOOK-2026-WELFARE",
        "attendance_exceptions.csv": "ATTENDANCE-EXCEPTIONS-2026",
        "examination_rules.csv": "EXAMINATION-RULES-2026",
        "academic_requirements.csv": "ACADEMIC-REQUIREMENTS-2026",
    }

    SUPPORTED_EXTENSIONS = {".md", ".pdf", ".csv"}

    def __init__(self, data_root: str | Path) -> None:
        self.data_root = Path(data_root)

        if not self.data_root.exists():
            raise FileNotFoundError(
                f"Data directory does not exist: {self.data_root}"
            )

    def ingest(self) -> list[Document]:
        """
        Ingest every supported file under data/raw/.

        Returns:
            A list of normalized Document objects.
        """
        raw_root = self.data_root / "raw"

        if not raw_root.exists():
            raise FileNotFoundError(
                f"Raw data directory does not exist: {raw_root}"
            )

        documents: list[Document] = []

        for file_path in sorted(raw_root.rglob("*")):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            documents.extend(self.ingest_file(file_path))

        return documents

    def ingest_file(self, file_path: str | Path) -> list[Document]:
        """
        Ingest a single supported file.

        Args:
            file_path: Path to the source file.

        Returns:
            One or more normalized Document objects.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Source file does not exist: {path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {sorted(self.SUPPORTED_EXTENSIONS)}"
            )

        if extension == ".md":
            return self._ingest_markdown(path)

        if extension == ".pdf":
            return self._ingest_pdf(path)

        if extension == ".csv":
            return self._ingest_csv(path)

        raise ValueError(f"Unsupported file type: {extension}")

    def _ingest_markdown(self, file_path: Path) -> list[Document]:
        """
        Extract Markdown content.

        A Markdown file is initially represented as one Document.
        Section extraction will be handled more precisely during chunking.
        """
        text = file_path.read_text(encoding="utf-8")
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return []

        document_id = self._get_document_id(file_path)

        return [
            Document(
                document_id=document_id,
                source_file=str(file_path),
                file_type="markdown",
                text=normalized_text,
            )
        ]

    def _ingest_pdf(self, file_path: Path) -> list[Document]:
        """
        Extract PDF text page-by-page.

        Keeping pages separate preserves page-level citation metadata.
        """
        document_id = self._get_document_id(file_path)
        documents: list[Document] = []

        with pymupdf.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text")
                normalized_text = self._normalize_text(text)

                if not normalized_text:
                    continue

                documents.append(
                    Document(
                        document_id=document_id,
                        source_file=str(file_path),
                        file_type="pdf",
                        text=normalized_text,
                        page=page_number,
                    )
                )

        return documents

    def _ingest_csv(self, file_path: Path) -> list[Document]:
        """
        Convert each CSV row into a searchable Document.

        Column names are included in the generated text so that semantic
        retrieval can understand what each value represents.
        """
        document_id = self._get_document_id(file_path)
        documents: list[Document] = []

        with file_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                raise ValueError(f"CSV file has no header: {file_path}")

            for row_number, row in enumerate(reader, start=2):
                parts = []

                for column, value in row.items():
                    if value is None:
                        continue

                    cleaned_value = self._normalize_text(str(value))

                    if not cleaned_value:
                        continue

                    parts.append(f"{column}: {cleaned_value}")

                row_text = " | ".join(parts)
                row_text = self._normalize_text(row_text)

                if not row_text:
                    continue

                documents.append(
                    Document(
                        document_id=document_id,
                        source_file=str(file_path),
                        file_type="csv",
                        text=row_text,
                        section=f"row {row_number}",
                    )
                )

        return documents

    def _get_document_id(self, file_path: Path) -> str:
        """
        Return a stable document ID based on the source filename.
        """
        filename = file_path.name

        if filename in self.DOCUMENT_ID_MAP:
            return self.DOCUMENT_ID_MAP[filename]

        raise ValueError(
            f"No document ID mapping exists for source file: {filename}"
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize extracted text without changing its meaning.

        - Normalizes line endings.
        - Removes trailing whitespace.
        - Collapses excessive blank lines.
        - Collapses repeated spaces.
        """
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()