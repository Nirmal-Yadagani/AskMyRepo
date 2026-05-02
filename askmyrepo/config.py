"""Application settings."""

from dataclasses import dataclass, field
from enum import Enum


class ModelProvider(str, Enum):
    """Supported model providers for chat and embedding."""
    OLLAMA = "ollama"
    LITELLM = "litellm"


@dataclass(frozen=True)
class Settings:
    # --- Chat model ---
    chat_provider: ModelProvider = ModelProvider.OLLAMA
    chat_model: str = "qwen3.6"
    chat_base_url: str = "http://localhost:11434"  # used by Ollama provider

    # --- Embedding model ---
    embedding_provider: ModelProvider = ModelProvider.OLLAMA
    embedding_model: str = "nomic-embed-text"
    embedding_base_url: str = "http://localhost:11434"

    # --- Storage ---
    chroma_db_path: str = "./data/chroma_db"
    default_repo_path: str = "./data/repos"

    # --- Indexing ---
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 64
    top_k_results: int = 8
    max_file_size_bytes: int = 1_048_576  # 1 MB per file
    ignored_dirs: tuple[str, ...] = field(default=(
        "__pycache__", ".git", "node_modules", ".venv",
        "venv", "env", ".tox", "build", "dist", "target",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
        ".claude", ".vscode", ".idea", "vendor", "third_party",
    ))
    ignored_extensions: tuple[str, ...] = field(default=(
        ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
        ".pdf", ".zip", ".tar", ".gz", ".whl", ".egg",
        ".lock", ".sqlite", ".db",
    ))


def get_settings() -> Settings:
    return Settings()
