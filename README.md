# AskMyRepo

Agentic RAG system for querying any GitHub repository. Clone any repo, ask natural language questions about its code, and get answers powered by a local LLM and semantic search.

## Architecture

```
Repo URL ──▶ Cloner ──▶ Tree-sitter Parser ──▶ CodeChunker ──▶ Embedder ──▶ ChromaDB
                                                                                   │
Question ──────────────────────────────────────────────────────────────────────────▶│──▶ Agent──▶ Answer
```

**Key differences from dumb RAG:**
- **Tree-sitter AST parsing** extracts functions, classes, imports, signatures, docstrings
- **Code-aware chunking** groups related code together (class + methods)
- **Custom tool-calling agent** decides which tool to use per question (parse, search, read_file, etc.)
- **LiteLLM-style provider abstraction** for chat and embeddings — swap providers by changing config

## Quick Start

### 1. Install dependencies
```bash
uv pip install -e .
```

### 2. Run Ollama locally
```bash
ollama pull qwen3.6          # Chat model
ollama pull nomic-embed-text # Embedding model (or any embedding model you prefer)
ollama serve                  # Start the server
```

### 3. Run the Streamlit app
```bash
streamlit run askmyrepo/ui/pages/1_repo_config.py
```

### 4. Or use the CLI
```bash
python -m askmyrepo clone https://github.com/username/repo
python -m askmyrepo index https://github.com/username/repo
python -m askmyrepo ask https://github.com/username/repo "Where is the database connection established?"
```

## Provider Configuration

All model providers are configurable in `askmyrepo/config.py`:

```python
Settings(
    chat_provider=ModelProvider.OLLAMA,      # or ModelProvider.LITELLM
    chat_model="qwen3.6",
    chat_base_url="http://localhost:11434",
    embedding_provider=ModelProvider.OLLAMA,
    embedding_model="nomic-embed-text",
    embedding_base_url="http://localhost:11434",
)
```

For LiteLLM, set the base URLs to your provider's endpoint and use the appropriate model name.

## Agent Tools

The agent has 6 tools it can call:

| Tool | Description |
|------|-------------|
| `parse_code` | Get AST metadata for a file (functions, classes, imports) |
| `read_file` | Read raw file content |
| `search_codebase` | Vector semantic search (finds code by meaning) |
| `search_imports` | Find all import statements for a function/class |
| `find_class_hierarchy` | Get class inheritance chain |
| `list_files` | Browse file structure |

## Project Structure

```
askmyrepo/
├── config.py              # Settings & provider config
├── models.py              # Pydantic data models
├── cloning/               # Repo cloner
├── parser/                # tree-sitter AST parsing
├── chunking/              # Code-aware chunking
├── embedding/             # Ollama embedding provider
├── vectorstore/           # ChromaDB storage
├── indexing/              # Pipeline orchestrator
├── agent/                 # Tool-calling agent
│   ├── agent.py
│   ├── tool_registry.py
│   └── tools/             # Individual tools
└── ui/                    # Streamlit pages
```

## Learning Path

This project is designed as a step-by-step exploration:

1. **Repo Cloning** — Git operations in Python
2. **Tree-sitter Parsing** — How compilers understand code structure
3. **Chunking** — Why what you chunk = what the agent sees
4. **Embeddings** — Turning code into vectors
5. **Vector Store** — Semantic search with ChromaDB
6. **Agent Loop** — The "AI" part: LLM decides tools, executes, synthesizes
7. **Streamlit UI** — Wrapping everything together
