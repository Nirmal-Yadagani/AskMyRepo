"""Language detection and grammar mapping for tree-sitter."""

from askmyrepo.models import Language


LANGUAGE_GRAMMAR_MAP: dict[Language, str] = {
    Language.PYTHON: "python",
    Language.JAVASCRIPT: "javascript",
    Language.TYPESCRIPT: "typescript",
    Language.JAVA: "java",
    Language.GO: "go",
    Language.RUST: "rust",
    Language.C: "c",
    Language.CPP: "cpp",
    Language.RUBY: "ruby",
    Language.PHP: "php",
    Language.KOTLIN: "kotlin",
    Language.SWIFT: "swift",
}

EXTENSION_TO_LANGUAGE: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".c": Language.C,
    ".h": Language.C,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".kt": Language.KOTLIN,
    ".swift": Language.SWIFT,
}

SUPPORTED_EXTENSIONS: set[str] = set(EXTENSION_TO_LANGUAGE.keys())


def detect_language(file_path: str) -> Language:
    """Detect programming language from file extension."""
    import os
    _, ext = os.path.splitext(file_path)
    return EXTENSION_TO_LANGUAGE.get(ext, Language.UNKNOWN)
