"""Orchestrates the full indexing pipeline: clone -> parse -> chunk -> embed -> store."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Optional

from askmyrepo.chunking.chunker import CodeChunker
from askmyrepo.cloning.repo_cloner import RepoCloner
from askmyrepo.config import Settings, get_settings
from askmyrepo.embedding.ollama_embedder import Embedder
from askmyrepo.models import IndexingResult, IndexingStatus
from askmyrepo.parser.tree_sitter_parser import CodeParser
from askmyrepo.vectorstore.chroma_store import VectorStore


class Indexer:
    """End-to-end indexing pipeline for a repository."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.cloner = RepoCloner(self.settings)
        self.parser = CodeParser(self.settings)
        self.chunker = CodeChunker(self.settings)
        self._repo_root: Path | None = None
        self.embedder = Embedder(
            model=self.settings.embedding_model,
            base_url=self.settings.embedding_base_url,
        )
        self.vector_store = VectorStore(
            db_path=self.settings.chroma_db_path,
        )

    def index(
        self,
        source: str,
        callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> IndexingResult:
        """Run the full indexing pipeline on a repository.

        Args:
            source: GitHub URL or local file path.
            callback: Optional progress callback(status_message, current, total).

        Returns:
            IndexingResult with final status and stats.
        """
        result = IndexingResult(
            repo_path=source,
            start_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        try:
            # Step 1: Clone
            result.status = IndexingStatus.CLONING
            repo_path = self.cloner.clone_or_use(source)
            if callback:
                callback(f"Cloned to {repo_path}", 1, 6)

            # Step 2: Parse (AST extraction)
            result.status = IndexingStatus.PARSING
            if callback:
                callback("Parsing source files with tree-sitter...", 2, 6)
            all_nodes = self.parser.parse_directory(repo_path)
            result.total_nodes = len(all_nodes)
            result.total_files = len(set(n.file_path for n in all_nodes))
            if callback:
                callback(f"Parsed {result.total_files} files, {result.total_nodes} AST nodes", 3, 6)

            # Step 3: Chunk (code-aware + text fallback)
            result.status = IndexingStatus.CHUNKING
            if callback:
                callback("Creating chunks...", 3, 6)
            self._repo_root = repo_path
            chunker = CodeChunker(self.settings, repo_root=repo_path)
            code_chunks = chunker.chunk_from_nodes(all_nodes)
            text_chunks = self._chunk_raw_files(repo_path, all_nodes, code_chunks)
            all_chunks = code_chunks + text_chunks
            result.total_chunks = len(all_chunks)
            if callback:
                callback(f"Created {len(code_chunks)} code chunks + {len(text_chunks)} text chunks", 4, 6)

            # Step 4: Embed
            result.status = IndexingStatus.EMBEDDING
            if callback:
                callback("Generating embeddings...", 4, 6)
            texts = [c.text for c in all_chunks]
            embeddings = self.embedder.embed_batch(texts)
            if callback:
                callback(f"Embedded {len(embeddings)} chunks", 5, 6)

            # Step 5: Store in ChromaDB
            result.status = IndexingStatus.STORING
            for i, chunk in enumerate(all_chunks):
                chunk.metadata["embedding_dim"] = len(embeddings[i])
                chunk.metadata["file_path"] = chunk.file_path
            self.vector_store.add_chunks(all_chunks, embeddings=embeddings)
            result.status = IndexingStatus.COMPLETE
            result.end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if callback:
                callback(f"Indexed {result.total_chunks} chunks in ChromaDB", 6, 6)

        except Exception as e:
            result.status = IndexingStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return result

    def _chunk_raw_files(
        self,
        repo_root: Path,
        parsed_nodes: list,
        code_chunks: list = None,
    ) -> list:
        """Create text-based chunks for all Python files for comprehensive coverage."""
        if code_chunks is None:
            code_chunks = []
        text_chunks: list = []
        # Get set of files that already have AST chunks
        ast_covered = {n.file_path for n in parsed_nodes}
        seen: set[str] = set()
        # Walk the repo for ALL Python files
        for fp in repo_root.rglob("*.py"):
            if not fp.is_file():
                continue
            fp_str = str(fp)
            # Normalize: if path contains repo_root prefix, make it relative
            if fp_str in ast_covered:
                # File already has AST chunk — still add text for line-level coverage
                pass
            if fp_str in seen:
                continue
            seen.add(fp_str)
            text_chunks.extend(self.chunker.chunk_raw_text(fp, repo_root, repo_root))
        return text_chunks

    def get_vector_store(self) -> VectorStore:
        """Return the vector store for querying."""
        return self.vector_store
