"""list_files tool: list files matching a pattern in the repository."""

from pathlib import Path

from askmyrepo.config import Settings


class ListFilesTool:
    """List files in the repository matching a glob pattern."""

    name = "list_files"
    description = (
        "List files in the repository matching a glob pattern. "
        "Use when the user wants to browse the file structure, find files by name/pattern."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match (e.g., '*.py', 'src/**/*.ts', 'test_*')",
                "default": "*",
            },
        },
        "required": ["pattern"],
    }

    def __init__(self, repo_path: Path, settings: Settings):
        self.repo_path = repo_path
        self.settings = settings

    def run(self, pattern: str = "*") -> str:
        from askmyrepo.parser.language_map import SUPPORTED_EXTENSIONS

        try:
            matches = list(self.repo_path.rglob(pattern))
        except ValueError:
            return f"Invalid pattern: {pattern}"

        relevant = [m for m in matches if m.is_file() and m.suffix in SUPPORTED_EXTENSIONS]
        if not relevant:
            return f"No files found matching '{pattern}'."

        # Show directory-like structure
        lines = [f"Found {len(relevant)} file(s) matching '{pattern}':\n"]
        for f in sorted(relevant)[:50]:  # Limit display
            rel = str(f.relative_to(self.repo_path))
            lines.append(f"  {rel}")
        if len(relevant) > 50:
            lines.append(f"  ... and {len(relevant) - 50} more")
        return "\n".join(lines)
