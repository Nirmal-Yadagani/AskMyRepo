"""parse_code tool: get AST metadata for a file or function."""

from pathlib import Path

from askmyrepo.config import Settings
from askmyrepo.parser.tree_sitter_parser import CodeParser


class ParseCodeTool:
    """Parse source code and return structured metadata."""

    name = "parse_code"
    description = (
        "Parse a source file and return AST metadata (functions, classes, imports). "
        "Use when the user asks about what a file contains, its structure, or the definitions in it."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the source file relative to repo root (e.g., 'src/askme/parser/tree_sitter_parser.py')",
            },
        },
        "required": ["file_path"],
    }

    def __init__(self, repo_path: Path, settings: Settings):
        self.repo_path = repo_path
        self.settings = settings

    def run(self, file_path: str) -> str:
        parser = CodeParser(self.settings)
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        nodes = parser.parse_file(full_path)
        if not nodes:
            return f"No AST nodes found in {file_path} (file may not be a supported language)."

        lines = []
        for n in nodes:
            lines.append(f"- {n.node_type.value}: '{n.name}' at lines {n.line_start}-{n.line_end}")
            if n.parameters:
                params = ", ".join(p["name"] for p in n.parameters)
                lines.append(f"  params: [{params}]")
            if n.return_type:
                lines.append(f"  returns: {n.return_type}")
            if n.base_classes:
                lines.append(f"  extends: {', '.join(n.base_classes)}")
            if n.decorators:
                lines.append(f"  decorators: {', '.join(n.decorators)}")
            if n.docstring:
                lines.append(f"  docstring: {n.docstring[:200]}")

        return f"Found {len(nodes)} definitions in {file_path}:\n" + "\n".join(lines)
