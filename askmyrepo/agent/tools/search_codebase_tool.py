"""search_codebase tool: vector semantic search across the indexed codebase."""

from askmyrepo.config import Settings
from askmyrepo.embedding.ollama_embedder import Embedder
from askmyrepo.vectorstore.chroma_store import VectorStore


class SearchCodebaseTool:
    """Search the indexed codebase semantically using vector embeddings."""

    name = "search_codebase"
    description = (
        "Search the indexed codebase for semantically relevant code chunks. "
        "Use when the user asks 'where is X implemented', 'how does X work', or 'what is X' about code. "
        "This searches by meaning, not by keyword."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query in natural language (e.g., 'how is the database connection established')",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, vector_store: VectorStore, embedder: Embedder, settings: Settings):
        self.vector_store = vector_store
        self.embedder = embedder
        self.settings = settings

    def run(self, query: str, top_k: int = 5) -> str:
        if self.vector_store.count() == 0:
            return "No chunks indexed yet. Run the indexing pipeline first."

        embeddings = self.embedder.embed([query])
        results = self.vector_store.search(embeddings[0], top_k=min(top_k, self.settings.top_k_results))

        if not results:
            return f"No results found for query: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"\n=== Result {i} (score: {r.score:.3f}) ===")
            lines.append(f"File: {r.file_path}:{r.line_start}-{r.line_end}")
            # Show first 300 chars of the chunk
            preview = r.text[:300].replace("\n", " ").strip()
            lines.append(f"Content: {preview}")
            if len(r.text) > 300:
                lines.append("... (truncated)")

        return "\n".join(lines)
