from pathlib import Path

from app.core.config import get_settings
from app.services.chunking import DocumentChunker
from app.services.embeddings import EmbeddingService
from app.services.ingestion import DocumentIngestor
from app.services.vector_store import VectorStore


def main() -> None:
    """
    Ingest the rulebook corpus, generate local embeddings,
    and store the chunks in ChromaDB.
    """
    backend_root = Path(__file__).resolve().parent.parent
    project_root = backend_root.parent

    data_root = project_root / "data"
    settings = get_settings()

    print("Starting rulebook indexing...")

    # 1. Ingest source documents.
    ingestor = DocumentIngestor(data_root)
    documents = ingestor.ingest()

    print(f"Documents ingested: {len(documents)}")

    # 2. Create searchable chunks.
    chunker = DocumentChunker(
        max_chars=1200,
        overlap_chars=150,
    )
    chunks = chunker.chunk_documents(documents)

    print(f"Chunks created: {len(chunks)}")

    # 3. Generate embeddings locally.
    embedding_service = EmbeddingService()
    embeddings = embedding_service.embed_chunks(chunks)

    print(f"Embeddings generated: {len(embeddings)}")

    # 4. Store everything in ChromaDB.
    chroma_path = backend_root / settings.chroma_persist_directory

    vector_store = VectorStore(str(chroma_path))
    vector_store.add_chunks(chunks, embeddings)

    print(f"Chunks stored in ChromaDB: {vector_store.count()}")
    print("Indexing completed successfully.")


if __name__ == "__main__":
    main()