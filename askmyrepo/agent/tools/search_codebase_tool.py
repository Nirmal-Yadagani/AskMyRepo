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

        # Build enriched queries for better semantic coverage
        enriched_queries = self._enrich_query(query)

        # Search with all queries, merge results by file_path+line_range
        best_results: dict[str, tuple] = {}
        for q in enriched_queries:
            emb = self.embedder.embed([q])[0]
            results = self.vector_store.search(emb, top_k=min(top_k * 2, self.settings.top_k_results))
            for r in results:
                key = f"{r.file_path}:{r.line_start}-{r.line_end}"
                if key not in best_results or r.score > best_results[key][1]:
                    best_results[key] = (r, r.score)

        if not best_results:
            return f"No results found for query: {query}"

        # Sort by score and take top_k
        sorted_results = sorted(best_results.values(), key=lambda x: x[1], reverse=True)[:top_k]

        lines = []
        for i, (r, score) in enumerate(sorted_results, 1):
            lines.append(f"\n=== Result {i} (score: {score:.3f}) ===")
            lines.append(f"File: {r.file_path}:{r.line_start}-{r.line_end}")
            # Show first 300 chars of the chunk
            preview = r.text[:300].replace("\n", " ").strip()
            lines.append(f"Content: {preview}")
            if len(r.text) > 300:
                lines.append("... (truncated)")

        return "\n".join(lines)

    @staticmethod
    def _enrich_query(query: str) -> list[str]:
        """Generate enriched queries for better search coverage."""
        queries = [query]
        q_lower = query.lower()

        # Add context keywords based on query patterns
        if any(w in q_lower for w in ("class", "what is", "what's", "what does")):
            queries.append(f"{query} class definition")
        if any(w in q_lower for w in ("function", "method", "how does", "how is")):
            queries.append(f"{query} function implementation")
        if any(w in q_lower for w in ("import", "where", "used by")):
            queries.append(f"{query} import usage")
        if "repo" in q_lower and any(w in q_lower for w in ("clone", "download", "fetch")):
            queries.append(f"{query} cloning repository github")

        return queries
