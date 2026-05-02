"""Pydantic data models for AskMe."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    UNKNOWN = "unknown"


class NodeType(str, Enum):
    FUNCTION_DEF = "function_definition"
    CLASS_DEF = "class_definition"
    IMPORT = "import_statement"
    METHOD_DEF = "method_definition"
    ATTRIBUTE_DEF = "attribute_definition"
    CALL = "call_expression"
    MODULE = "module"


class CodeNode(BaseModel):
    """A single AST node extracted from the code."""
    node_type: NodeType
    name: str
    language: Language
    file_path: str
    line_start: int
    line_end: int
    parameters: Optional[list[dict[str, str]]] = None
    return_type: Optional[str] = None
    decorators: list[str] = Field(default_factory=list)
    base_classes: list[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    module_path: str = ""
    child_nodes: list[CodeNode] = Field(default_factory=list)
    parent_node: Optional[CodeNode] = None


class CodeChunk(BaseModel):
    """A chunk ready for embedding."""
    chunk_id: str
    text: str
    file_path: str
    language: Language
    line_start: int
    line_end: int
    chunk_type: str  # "function", "class", "import", "docstring", "module_header"
    metadata: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A single result from ChromaDB retrieval."""
    chunk_id: str
    text: str
    file_path: str
    language: Language
    line_start: int
    line_end: int
    score: float
    metadata: dict = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """Message in the agent conversation."""
    role: str  # "user", "assistant", or "tool"
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


class IndexingStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETE = "complete"
    FAILED = "failed"


class IndexingResult(BaseModel):
    repo_path: str
    status: IndexingStatus = IndexingStatus.PENDING
    total_files: int = 0
    total_nodes: int = 0
    total_chunks: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_message: Optional[str] = None
