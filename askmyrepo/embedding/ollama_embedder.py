"""Ollama embedding provider with LiteLLM abstraction for chat."""

from __future__ import annotations

from typing import Any

import ollama


class Embedder:
    """Generate embeddings using Ollama's embedding API."""

    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        client = ollama.Client(host=self.base_url)
        embeddings: list[list[float]] = []
        for text in texts:
            response = client.embeddings(model=self.model, prompt=text)
            embeddings.append(response["embedding"])
        return embeddings

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts in batches (ChromaDB expects batched inputs)."""
        return self.embed(texts)


class ChatProvider:
    """Chat model provider with LiteLLM-style abstraction.

    Currently supports Ollama backend. The config-driven design
    means we can swap in litellm later by just changing Settings.chat_provider.
    """

    def __init__(self, model: str = "qwen3.6", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict[str, str]], tools: list[dict] | None = None) -> dict[str, Any]:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions for tool-calling.

        Returns:
            Response dict with 'content' and optionally 'tool_calls'.
        """
        client = ollama.Client(host=self.base_url)
        response = client.chat(model=self.model, messages=messages, tools=tools)
        message = response["message"]

        result: dict[str, Any] = {"content": message.get("content", "")}
        if message.get("tool_calls"):
            result["tool_calls"] = [
                {
                    "id": tc.get("id", ""),
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                }
                for tc in message["tool_calls"]
            ]
        return result
