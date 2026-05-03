# AskMyRepo

Agentic RAG system for querying any GitHub repository. Clone any repo, ask natural language questions about its code, and get answers powered by a local LLM and semantic search.

## Architecture

```
Repo URL ──▶ Cloner ──▶ Tree-sitter Parser ──▶ CodeChunker ──▶ Embedder ──▶ ChromaDB
         >                               >                     >           >
Question ────────────────────────────────────────────────────────────────▶│──▶ Agent──▶ Answer
```

**Key design choices:**
- **Tree-sitter AST parsing** extracts functions, classes, imports, signatures, docstrings
- **Code-aware chunking** groups related code together (class + methods) instead of dumb text splitting
- **Custom tool-calling agent** — the LLM decides which tool to use per question, we execute it, and synthesize an answer
- **LiteLLM-style provider abstraction** — swap LLM/embedding providers by changing config

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally ([install](https://ollama.ai))
- **uv** package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))

### Models

```bash
ollama pull qwen3.6          # Chat model
ollama pull nomic-embed-text # Embedding model (default)
ollama serve
```

## Installation

```bash
git clone https://github.com/Nirmal-Yadagani/AskMyRepo.git
cd AskMyRepo
uv pip install -e .
```

## Usage

### Streamlit Web UI (recommended)

```bash
streamlit run askmyrepo/ui/pages/1_repo_config.py
```

This launches a 3-page app:
1. **Config** — set Ollama URL, chat/embedding models
2. **Indexing** — index a GitHub repo or local path with progress tracking
3. **Chat** — ask questions about the indexed code

### CLI

```bash
# Clone a repo
uv run python -m askmyrepo clone https://github.com/username/repo

# Index it (parse, chunk, embed, store in ChromaDB)
uv run python -m askmyrepo index https://github.com/username/repo

# Ask a question
uv run python -m askmyrepo ask https://github.com/Nirmal-Yadagani/AskMyRepo "Where is RepoCloner defined?"
```

### Python API

```python
from askmyrepo.indexing.indexer import Indexer
from askmyrepo.agent.agent import AskMeAgent
from pathlib import Path

# Index a repo
indexer = Indexer()
result = indexer.index("./data/repos/MyRepo")

# Query
agent = AskMeAgent(Path("./data/repos/MyRepo"))
answer = agent.ask("How does the ChromaDB search work?")
print(answer["answer"])
```

## Agent Tools

The agent has 6 tools it can call:

| Tool | Description |
|------|------|
| `parse_code` | Get AST metadata for a file (functions, classes, imports) |
| `read_file` | Read raw file content |
| `search_codebase` | Vector semantic search (finds code by meaning) |
| `search_imports` | Find all import statements for a function/class |
| `find_class_hierarchy` | Get class inheritance chain |
| `list_files` | Browse file structure |

## Configuration

All settings are in `askmyrepo/config.py`:

```python
Settings(
    chat_provider=ModelProvider.OLLAMA,
    chat_model="qwen3.6",
    chat_base_url="http://localhost:11434",
    embedding_provider=ModelProvider.OLLAMA,
    embedding_model="nomic-embed-text",
    embedding_base_url="http://localhost:11434",
    chroma_db_path="./data/chroma_db",
    default_repo_path="./data/repos",
    chunk_size_tokens=512,
    chunk_overlap_tokens=64,
    top_k_results=8,
    ignored_dirs=["__pycache__", ".git", "node_modules"],
    ignored_extensions=[".pyc", ".so", ".dll"],
    max_file_size_bytes=1_000_000,
)
```

## Project Structure

```
askmyrepo/
├── config.py              # Settings & provider config
├── models.py              # Pydantic data models
├── cloning/               # Step 1: clone repos
├── parser/                # Step 2: AST parsing (tree-sitter)
├── chunking/              # Step 3: code-aware chunking
├── embedding/             # Step 4: Ollama embeddings
├── vectorstore/           # Step 5: ChromaDB storage/query
├── indexing/              # Orchestrates steps 1-5
├── agent/                 # Step 6: tool-calling agent
│   ├── agent.py
│   ├── tool_registry.py
│   └── tools/
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

## Troubleshooting

- **`No module named 'pydantic'`** — Run `uv pip install -e .` to install dependencies
- **Ollama connection refused** — Ensure `ollama serve` is running (default: `localhost:11434`)
- **Embedding dimension mismatch** — Delete `./data/chroma_db/` and re-index the repo. ChromaDB's internal model (384-dim) and Ollama embeddings (768-dim) don't mix.
- **Agent gives wrong answers** — Re-index the repo. Search quality depends on chunk text quality.
- **Model not found** — Run `ollama list` to check available models, then update `chat_model` / `embedding_model` in config.
