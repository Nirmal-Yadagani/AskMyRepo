"""Tool registry for the agent. Manages tool definitions and execution."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from askmyrepo.models import SearchResult


class ToolRegistry:
    """Register and manage agent tools.

    Each tool has:
    - name: unique identifier (used by the LLM to call it)
    - description: what the tool does (sent as system prompt to the LLM)
    - parameters: JSON schema describing input args
    - func: callable that executes the tool
    """

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        func: Callable,
    ) -> None:
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def get_tools_def(self) -> list[dict[str, Any]]:
        """Return tool definitions in OpenAI-compatible format for the LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, tool_call_id: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name with given arguments.

        Returns:
            Tool result as a string (for the LLM to read).
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: unknown tool '{tool_name}'"
        result = tool["func"](**arguments)
        if isinstance(result, str):
            return result
        return json.dumps(result, default=str, ensure_ascii=False)

    def list_tools(self) -> list[str]:
        """Return list of registered tool names."""
        return list(self._tools.keys())


# Built-in tool implementations are in tools/*.py
# These are registered by the Agent class.

def _make_tool_response(content: str, tool_call_id: str = "") -> dict:
    """Format a tool result message for the agent loop."""
    return {
        "role": "tool",
        "content": content,
        "tool_call_id": tool_call_id,
    }
