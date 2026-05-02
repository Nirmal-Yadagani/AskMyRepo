"""Main agent: orchestrates tool-calling with the LLM."""

from __future__ import annotations

import json
from pathlib import Path

from askmyrepo.config import Settings, get_settings
from askmyrepo.embedding.ollama_embedder import ChatProvider, Embedder
from askmyrepo.vectorstore.chroma_store import VectorStore

from .tool_registry import ToolRegistry, _make_tool_response


MAX_TOOL_CALLS = 10  # Prevent infinite loops


class AskMeAgent:
    """Agentic RAG agent with custom tool-calling.

    The agent loop:
    1. User asks a question
    2. Agent sends messages + tool definitions to the LLM
    3. LLM decides which tool to call (or gives a final answer)
    4. Agent executes the tool, feeds result back to LLM
    5. Repeat until LLM gives a final answer
    """

    def __init__(
        self,
        repo_path: Path,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.repo_path = repo_path
        self.vector_store = VectorStore(db_path=self.settings.chroma_db_path)
        self.chat_provider = ChatProvider(
            model=self.settings.chat_model,
            base_url=self.settings.chat_base_url,
        )
        self.registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all available tools."""
        from .tools.parse_code_tool import ParseCodeTool
        from .tools.read_file_tool import ReadFileTool
        from .tools.search_codebase_tool import SearchCodebaseTool
        from .tools.search_imports_tool import SearchImportsTool
        from .tools.find_class_hierarchy_tool import FindClassHierarchyTool
        from .tools.list_files_tool import ListFilesTool
        from askmyrepo.config import get_settings

        s = get_settings()

        self.registry.register(
            ParseCodeTool.name,
            ParseCodeTool.description,
            ParseCodeTool.parameters,
            ParseCodeTool(self.repo_path, s).run,
        )
        self.registry.register(
            ReadFileTool.name,
            ReadFileTool.description,
            ReadFileTool.parameters,
            ReadFileTool(self.repo_path).run,
        )
        self.registry.register(
            SearchCodebaseTool.name,
            SearchCodebaseTool.description,
            SearchCodebaseTool.parameters,
            SearchCodebaseTool(self.vector_store, Embedder(), s).run,
        )
        self.registry.register(
            SearchImportsTool.name,
            SearchImportsTool.description,
            SearchImportsTool.parameters,
            SearchImportsTool(self.repo_path, s).run,
        )
        self.registry.register(
            FindClassHierarchyTool.name,
            FindClassHierarchyTool.description,
            FindClassHierarchyTool.parameters,
            FindClassHierarchyTool(self.repo_path, s).run,
        )
        self.registry.register(
            ListFilesTool.name,
            ListFilesTool.description,
            ListFilesTool.parameters,
            ListFilesTool(self.repo_path, s).run,
        )

    def ask(self, question: str) -> dict:
        """Ask a question and get an answer (possibly using tools).

        Args:
            question: The user's question about the codebase.

        Returns:
            Dict with 'answer', 'tool_usage', 'messages'.
        """
        system_prompt = (
            "You are AskMe, a code analysis agent. You help users understand any GitHub repository by "
            "analyzing its code. Use the available tools to gather information before answering.\n\n"
            f"Available tools: {self.registry.list_tools()}\n\n"
            "Tool usage rules:\n"
            "1. If the user asks about file structure, use 'list_files'.\n"
            "2. If the user asks about what a file contains, use 'parse_code'.\n"
            "3. If the user wants to see actual code, use 'read_file'.\n"
            "4. If the user asks 'where is X implemented' or 'how does X work', use 'search_codebase'.\n"
            "5. If the user asks where a function/class is imported, use 'search_imports'.\n"
            "6. If the user asks about class inheritance, use 'find_class_hierarchy'.\n"
            "7. When you have enough information, give a comprehensive answer using your knowledge.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        tool_usage: list[dict] = []

        for _ in range(MAX_TOOL_CALLS):
            tools = self.registry.get_tools_def() if tool_usage else []
            response = self.chat_provider.chat(messages, tools=tools if tools else None)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")

            if tool_calls:
                # Execute the first tool call
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"] if isinstance(tc["arguments"], dict) else {}
                    tool_call_id = tc.get("id", "")

                    if not tool_args:
                        # Try to parse as JSON string
                        try:
                            tool_args = json.loads(str(tc.get("arguments", "{}")))
                        except (json.JSONDecodeError, TypeError):
                            tool_args = {}

                    tool_result = self.registry.execute(tool_name, tool_call_id, tool_args)
                    tool_usage.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result_preview": tool_result[:200],
                    })

                    messages.append({
                        "role": "assistant",
                        "content": f"[Calling {tool_name}...]",
                    })
                    messages.append(_make_tool_response(tool_result, tool_call_id))
            elif content:
                # Final answer from the LLM
                return {
                    "answer": content,
                    "tool_usage": tool_usage,
                    "messages": messages,
                }

        # Safety: if we exceeded tool calls, give best-effort answer
        messages.append({
            "role": "user",
            "content": "You've used too many tool calls. Please synthesize what you've found so far into an answer.",
        })
        response = self.chat_provider.chat(messages)
        return {
            "answer": response.get("content", "No answer generated."),
            "tool_usage": tool_usage,
            "messages": messages,
        }
