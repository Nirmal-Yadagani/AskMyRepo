"""Code-aware chunking logic for RAG."""

from __future__ import annotations

import hashlib
from pathlib import Path

from askmyrepo.config import Settings, get_settings
from askmyrepo.models import CodeChunk, CodeNode, Language


class CodeChunker:
    """Create RAG chunks from parsed AST nodes and raw source files."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def chunk_from_nodes(self, nodes: list[CodeNode]) -> list[CodeChunk]:
        """Create chunks from AST nodes.

        Strategy: each function/class becomes its own chunk with full context.
        """
        chunks: list[CodeChunk] = []
        for node in nodes:
            chunks.extend(self._chunk_node(node))
        return chunks

    def _chunk_node(self, node: CodeNode) -> list[CodeChunk]:
        """Create one or more chunks from a single AST node."""
        chunks = []
        chunk_type = self._map_node_type(node.node_type)

        # Build rich text with context (imports, docstring, code)
        parts = []

        # Header with file location
        header = f"## File: {node.file_path}\n## Type: {chunk_type}\n"
        parts.append(header)

        # Add docstring if available
        if node.docstring:
            parts.append(f'"""{node.docstring}"""\n')

        # Build context around the definition
        context_lines = []
        if node.decorators:
            context_lines.extend(node.decorators)
        if node.base_classes:
            context_lines.append(f"extends: {', '.join(node.base_classes)}")
        if node.parameters:
            params_str = ", ".join(
                f"{p['name']}{f': {p['type']}' if p.get('type') else ''}"
                for p in node.parameters
            )
            context_lines.append(f"params: {params_str}")
        if node.return_type:
            context_lines.append(f"returns: {node.return_type}")

        if context_lines:
            parts.append(f"# {context_lines[0]}\n")

        chunks.append(CodeChunk(
            chunk_id=self._make_chunk_id(node),
            text="\n".join(parts),
            file_path=node.file_path,
            language=node.language,
            line_start=node.line_start,
            line_end=node.line_end,
            chunk_type=chunk_type,
            metadata={
                "node_type": node.node_type.value,
                "name": node.name,
                "module_path": node.module_path,
            },
        ))
        return chunks

    def chunk_raw_text(self, file_path: Path, repo_root: Path) -> list[CodeChunk]:
        """Create text-based chunks from raw file content (fallback layer).

        Uses sliding window over lines for comprehensive coverage.
        """
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        lines = source.splitlines()
        if not lines:
            return []

        chunks: list[CodeChunk] = []
        lang = self._detect_lang(str(file_path))
        rel_path = str(file_path.relative_to(repo_root)) if file_path.is_absolute() else str(file_path)
        chunk_size = self.settings.chunk_size_tokens

        # Rough line estimation: ~10 chars per token
        lines_per_chunk = max(chunk_size // 10, 10)
        overlap = self.settings.chunk_overlap_tokens // 10

        for start in range(0, len(lines), lines_per_chunk - overlap):
            end = min(start + lines_per_chunk, len(lines))
            chunk_text = "\n".join(lines[start:end])
            if not chunk_text.strip():
                continue

            chunks.append(CodeChunk(
                chunk_id=self._make_text_id(rel_path, start, end),
                text=chunk_text,
                file_path=rel_path,
                language=lang,
                line_start=start + 1,
                line_end=end,
                chunk_type="text_segment",
                metadata={"total_lines": len(lines)},
            ))

        return chunks

    def _chunk_type_name(self, node_type) -> str:
        """Map NodeType to chunk type name."""
        mapping = {
            "function_definition": "function",
            "method_definition": "method",
            "class_definition": "class",
            "import_statement": "import",
        }
        return mapping.get(str(node_type), "unknown")

    def _map_node_type(self, node_type) -> str:
        """Map AST node type to a descriptive chunk type."""
        if node_type.value in ("function_definition", "method_definition"):
            return "function"
        elif node_type.value == "class_definition":
            return "class"
        elif node_type.value == "import_statement":
            return "import"
        return "unknown"

    @staticmethod
    def _make_chunk_id(node: CodeNode) -> str:
        raw = f"{node.file_path}:{node.line_start}-{node.line_end}:{node.name}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @staticmethod
    def _make_text_id(file_path: str, start: int, end: int) -> str:
        raw = f"{file_path}:{start}-{end}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @staticmethod
    def _detect_lang(file_path: str) -> Language:
        from askmyrepo.parser.language_map import detect_language
        return detect_language(file_path)
