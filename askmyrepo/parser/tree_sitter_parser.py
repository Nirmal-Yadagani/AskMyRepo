"""Core tree-sitter AST parser for code-aware extraction."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import tree_sitter
import tree_sitter_python

from askmyrepo.config import get_settings, Settings
from askmyrepo.models import CodeNode, Language, NodeType

from .ast_node import (
    get_node_text,
    node_base_classes,
    node_decorators,
    node_docstring,
    node_name,
    node_params,
    node_return_type,
    _node_type_from_ts,
)
from .language_map import detect_language, SUPPORTED_EXTENSIONS


class CodeParser:
    """Parse source files using tree-sitter and extract semantic metadata."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._parsers: dict[str, tree_sitter.Parser] = {}

    def _get_parser(self, lang: Language) -> tree_sitter.Parser:
        """Get or create a tree-sitter parser for the given language."""
        if lang not in self._parsers:
            if lang == Language.PYTHON:
                lang_module = tree_sitter_python.language()
            else:
                # Default to Python parser for unsupported languages
                # In a full implementation, register other grammar packages
                lang_module = tree_sitter_python.language()
            self._parsers[lang] = tree_sitter.Parser(lang_module)
        return self._parsers[lang]

    def parse_file(self, file_path: Path) -> list[CodeNode]:
        """Parse a single file and extract AST nodes.

        Args:
            file_path: Path to the source file.

        Returns:
            List of CodeNode objects extracted from the file.
        """
        lang = detect_language(str(file_path))
        if lang == Language.UNKNOWN or lang not in SUPPORTED_EXTENSIONS:
            return []

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return []

        if len(source) > self.settings.max_file_size_bytes:
            return []

        parser = self._get_parser(lang)
        tree = parser.parse_bytes(source.encode("utf-8"))
        root_node = tree.root_node

        # Walk the tree and extract nodes
        nodes = []
        for child in root_node.children:
            node = self._extract_node(child, file_path, lang, source)
            if node:
                nodes.append(node)

        return nodes

    def _extract_node(self, node, file_path: Path, lang: Language, source: str) -> CodeNode | None:
        """Extract a CodeNode from a tree-sitter node."""
        nt = _node_type_from_ts(node.type)

        # Only extract definition-type nodes (not raw calls)
        if nt not in (NodeType.FUNCTION_DEF, NodeType.CLASS_DEF, NodeType.IMPORT):
            return None

        name = node_name(node) or f"<{node.type}>"
        params = node_params(node) if nt in (NodeType.FUNCTION_DEF, NodeType.METHOD_DEF) else None
        return_type = node_return_type(node) if nt in (NodeType.FUNCTION_DEF, NodeType.METHOD_DEF) else None
        base_classes = node_base_classes(node) if nt == NodeType.CLASS_DEF else []
        docstring = node_docstring(node)
        decorators = node_decorators(node)

        file_str = str(file_path.relative_to(file_path.anchor)) if file_path.is_absolute() else str(file_path)
        module_path = str(file_path.parent)

        return CodeNode(
            node_type=nt,
            name=name,
            language=lang,
            file_path=file_str,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            parameters=params,
            return_type=return_type,
            decorators=decorators,
            base_classes=base_classes,
            docstring=docstring,
            module_path=module_path,
        )

    def parse_directory(self, repo_root: Path) -> list[CodeNode]:
        """Walk repo_root, parse all supported files, return flat list of nodes.

        Args:
            repo_root: Path to the repository root directory.

        Returns:
            Flat list of all CodeNode objects across all files.
        """
        all_nodes: list[CodeNode] = []
        seen_files: set[str] = set()

        for root, dirs, files in os.walk(repo_root):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.settings.ignored_dirs]
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                _, ext = os.path.splitext(filename)
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if ext in self.settings.ignored_extensions:
                    continue

                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(repo_root))
                if rel_path in seen_files:
                    continue
                seen_files.add(rel_path)

                nodes = self.parse_file(file_path)
                all_nodes.extend(nodes)

        return all_nodes

    def get_function_code(self, file_path: Path, line_start: int, line_end: int) -> str:
        """Extract the source code for a specific node range."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            lines = source.splitlines()
            start = max(0, line_start - 1)
            end = min(len(lines), line_end)
            return "\n".join(lines[start:end])
        except OSError:
            return ""
