from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from app.services.chunking import Chunk


class VectorStore:
    """
    Persistent ChromaDB vector store for rulebook chunks.
    """

    COLLECTION_NAME = "rulebook_chunks"

    def __init__(self, persist_directory: str) -> None:
        self.persist_directory = Path(persist_directory)

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={
                "description": "Meridian University rulebook chunks",
            },
        )

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add chunks and their embeddings to ChromaDB.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks must match number of embeddings."
            )

        if not chunks:
            return

        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                self._build_metadata(chunk)
                for chunk in chunks
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 8,
    ) -> dict[str, Any]:
        """
        Search for the most relevant rulebook chunks
        using semantic vector similarity.
        """
        if not query_embedding:
            raise ValueError(
                "Query embedding cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    def keyword_search(
        self,
        keywords: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search stored rulebook chunks using keyword overlap.

        This complements semantic vector search, especially for
        structured rules stored in CSV tables where exact
        terminology and thresholds are important.
        """
        if not keywords:
            return []

        if limit <= 0:
            raise ValueError(
                "limit must be greater than 0."
            )

        all_results = self.collection.get(
            include=[
                "documents",
                "metadatas",
            ],
        )

        matches: list[dict[str, Any]] = []

        ids = all_results.get("ids", [])
        documents = all_results.get("documents", [])
        metadatas = all_results.get("metadatas", [])

        normalized_keywords = {
            keyword.lower().rstrip("s")
            for keyword in keywords
            if keyword.strip()
        }

        for chunk_id, document, metadata in zip(
            ids,
            documents,
            metadatas,
        ):
            text_lower = document.lower()

            matched_keywords = []

            for keyword in normalized_keywords:
                normalized_keyword = keyword.rstrip("s")

                if normalized_keyword in text_lower:
                    matched_keywords.append(keyword)

            if not matched_keywords:
                continue

            matches.append(
                {
                    "id": chunk_id,
                    "document": document,
                    "metadata": metadata,
                    "matched_keywords": matched_keywords,
                }
            )

        matches.sort(
            key=lambda item: len(
                item["matched_keywords"]
            ),
            reverse=True,
        )

        return matches[:limit]

    def count(self) -> int:
        """
        Return the number of stored chunks.
        """
        return self.collection.count()

    def reset(self) -> None:
        """
        Delete and recreate the rulebook collection.

        Useful when rebuilding the entire index.
        """
        self.client.delete_collection(
            name=self.COLLECTION_NAME,
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={
                "description": "Meridian University rulebook chunks",
            },
        )

    @staticmethod
    def _build_metadata(
        chunk: Chunk,
    ) -> dict[str, Any]:
        """
        Convert chunk metadata into Chroma-compatible metadata.
        """
        metadata: dict[str, Any] = {
            "document_id": chunk.document_id,
            "source_file": chunk.source_file,
            "file_type": chunk.file_type,
        }

        if chunk.section is not None:
            metadata["section"] = chunk.section

        if chunk.page is not None:
            metadata["page"] = chunk.page

        return metadata