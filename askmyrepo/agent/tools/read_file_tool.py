"""read_file tool: read raw file content with line limits."""

from pathlib import Path


class ReadFileTool:
    """Read the raw text content of a file."""

    name = "read_file"
    description = (
        "Read the raw text content of a file in the repository. "
        "Use when the user wants to see actual code, not just metadata."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file relative to repo root",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to return (default 100). Use -1 for no limit.",
                "default": 100,
            },
        },
        "required": ["file_path"],
    }

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def run(self, file_path: str, max_lines: int = 100) -> str:
        full_path = self.repo_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return f"Error reading file: {e}"

        if max_lines > 0:
            lines = content.splitlines()[:max_lines]
            content = "\n".join(lines)
            if len(content.splitlines()) < max_lines:
                return content
            return content + f"\n... (truncated, show max_lines={max_lines})"
        return content
