"""ChromaDB vector store wrapper for AskMe."""

from __future__ import annotations

from pathlib import Path

import chromadb

from askmyrepo.config import Settings, get_settings
from askmyrepo.models import CodeChunk, SearchResult


class VectorStore:
    """ChromaDB wrapper for storing and querying code chunks."""

    def __init__(self, db_path: str = "./data/chroma_db", collection_name: str = "code_chunks"):
        self.db_path = db_path
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(path=self.db_path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[CodeChunk], embeddings: list[list[float]] | None = None) -> int:
        """Add chunks to the vector store.

        Args:
            chunks: List of CodeChunk objects to store.
            embeddings: Pre-computed embeddings (if None, ChromaDB generates its own).

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [c.metadata for c in chunks]

        kwargs: dict = {"ids": ids, "documents": documents, "metadatas": metadatas}
        if embeddings is not None:
            kwargs["embeddings"] = embeddings

        self._collection.add(**kwargs)
        return len(chunks)

    def search(self, query_embedding: list[float], top_k: int = 8) -> list[SearchResult]:
        """Search for relevant chunks using a pre-computed query embedding.

        Args:
            query_embedding: Embedding vector for the query (must match collection embedding dim).
            top_k: Number of results to return.

        Returns:
            List of SearchResult objects ranked by relevance.
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "distances", "metadatas"],
        )

        search_results: list[SearchResult] = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0.0
            # ChromaDB returns cosine distance; convert to similarity score
            score = 1.0 - distance if distance <= 2.0 else 0.0

            search_results.append(SearchResult(
                chunk_id=doc_id,
                text=results["documents"][0][i],
                file_path=metadata.get("file_path", ""),
                language=metadata.get("language", "unknown"),
                line_start=metadata.get("line_start", 0),
                line_end=metadata.get("line_end", 0),
                score=score,
                metadata=metadata,
            ))

        return search_results

    def delete_collection(self) -> None:
        """Remove all chunks from the store."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Return the number of chunks in the store."""
        return self._collection.count()
