"""Main agent: orchestrates tool-calling with the LLM."""

from __future__ import annotations

import json
from pathlib import Path

from askmyrepo.config import Settings, get_settings
from askmyrepo.embedding.ollama_embedder import ChatProvider, Embedder
from askmyrepo.vectorstore.chroma_store import VectorStore

from .tool_registry import ToolRegistry, _make_tool_response


MAX_TOOL_CALLS = 5  # Prevent infinite loops


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
            "You are AskMyRepo, a code analysis agent. You help users understand any GitHub repository by "
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
            tools = self.registry.get_tools_def()
            response = self.chat_provider.chat(messages, tools=tools)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")

            # Also try to extract tool calls from JSON in content (for LLMs without native tool calling)
            if not tool_calls:
                tool_calls = self._parse_tool_calls_from_content(content)

            # If we already have results, stop only if LLM gives a REAL answer (not tool-call artifacts)
            if tool_usage and not tool_calls and content:
                # Reject tool-call artifacts as final answers
                if ("[Calling" in content or
                    '{"' in content or
                    '```json' in content or
                    '`json' in content):
                    continue  # LLM is still calling tools, keep going
                return {"answer": content, "tool_usage": tool_usage, "messages": messages}

            if tool_calls:
                # Execute tool calls
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

        # Safety: force answer by using a fresh message set
        safety_msgs = messages + [{
            "role": "user",
            "content": "STOP. You have enough information. Answer the user's question now with a direct text answer. Do NOT call any tools.",
        }]
        response = self.chat_provider.chat(safety_msgs)
        answer = response.get("content", "")
        # Check if the LLM is still trying to call tools (not a real answer)
        if answer and not (
            "[" in answer and "Calling" in answer
            or '{"' in answer or "```json" in answer
            or "command" in answer.lower() or "arguments" in answer.lower()
        ):
            return {"answer": answer, "tool_usage": tool_usage, "messages": messages}

        return {
            "answer": "Here's what I found:\n\n" + "\n".join(
                f"- **{tc['tool']}**: {tc['result_preview'][:150]}" for tc in tool_usage
            ),
            "tool_usage": tool_usage,
            "messages": messages,
        }

    @staticmethod
    def _parse_tool_calls_from_content(content: str) -> list[dict] | None:
        """Extract tool calls from LLM content when native tool calling isn't supported."""
        import re

        # Try single JSON object with "command" key
        json_match = re.search(r'\{[^{}]*"command"\s*:[^{}]*\}', content)
        if json_match:
            try:
                tool_call = json.loads(json_match.group())
                name = tool_call.get("command", tool_call.get("name", ""))
                args = tool_call.get("arguments", tool_call.get("args", {}))
                if name:
                    return [{"name": name, "arguments": args, "id": ""}]
            except json.JSONDecodeError:
                pass

        # Try JSON array of tool calls
        json_arr_match = re.search(r'\[[^\]]*\{[^{}]*"command"\s*:[^{}]*\}', content)
        if json_arr_match:
            try:
                arr = json.loads(json_arr_match.group())
                calls = []
                for item in arr:
                    name = item.get("command", item.get("name", ""))
                    args = item.get("arguments", item.get("args", {}))
                    if name:
                        calls.append({"name": name, "arguments": args, "id": ""})
                return calls if calls else None
            except json.JSONDecodeError:
                pass

        return None
