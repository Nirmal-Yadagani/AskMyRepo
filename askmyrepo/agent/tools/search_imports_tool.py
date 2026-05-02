"""search_imports tool: find all imports of a function/class."""

from pathlib import Path

from askmyrepo.config import Settings
from askmyrepo.parser.tree_sitter_parser import CodeParser


class SearchImportsTool:
    """Find all files that import a specific function or class."""

    name = "search_imports"
    description = (
        "Find all import statements for a function or class across the codebase. "
        "Use when the user asks 'where is X imported' or 'who uses X'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "The function or class name to search for (e.g., 'RepoCloner')",
            },
        },
        "required": ["symbol"],
    }

    def __init__(self, repo_path: Path, settings: Settings):
        self.repo_path = repo_path
        self.settings = settings

    def run(self, symbol: str) -> str:
        parser = CodeParser(self.settings)
        all_nodes = parser.parse_directory(self.repo_path)

        imports = [
            n for n in all_nodes
            if n.node_type.value == "import_statement" and symbol in n.name
        ]

        if not imports:
            return f"No imports found for '{symbol}'."

        lines = [f"Found {len(imports)} import(s) for '{symbol}':\n"]
        for imp in imports:
            lines.append(f"- {imp.name} in {imp.file_path} (lines {imp.line_start}-{imp.line_end})")
        return "\n".join(lines)
