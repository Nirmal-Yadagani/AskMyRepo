"""CLI entry point for AskMe."""

import argparse
import sys
from pathlib import Path

import typer

from askmyrepo.config import get_settings
from askmyrepo.indexing.indexer import Indexer


def main():
    parser = argparse.ArgumentParser(prog="askmyrepo", description="Agentic RAG for GitHub repositories")
    subparsers = parser.add_subparsers(dest="command")

    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Clone a GitHub repo")
    clone_parser.add_argument("url", help="GitHub URL or local path")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index a repo for querying")
    index_parser.add_argument("source", help="GitHub URL or local path")

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question about an indexed repo")
    ask_parser.add_argument("source", help="GitHub URL or local path")
    ask_parser.add_argument("question", help="Your question")

    # List command
    list_parser = subparsers.add_parser("list", help="List cloned repos")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    settings = get_settings()

    if args.command == "clone":
        from askmyrepo.cloning.repo_cloner import RepoCloner
        cloner = RepoCloner(settings)
        path = cloner.clone_or_use(args.url)
        print(f"Cloned to: {path}")

    elif args.command == "index":
        indexer = Indexer(settings)

        def progress(msg, current, total):
            print(f"[{current}/{total}] {msg}")

        result = indexer.index(args.source, callback=progress)
        print(f"\nIndexing result: {result.status.value}")
        print(f"  Files: {result.total_files}")
        print(f"  AST Nodes: {result.total_nodes}")
        print(f"  Chunks: {result.total_chunks}")
        if result.error_message:
            print(f"  Error: {result.error_message}")

    elif args.command == "ask":
        from askmyrepo.agent.agent import AskMeAgent

        indexer = Indexer(settings)
        repo_path = indexer.cloner.clone_or_use(args.source)

        agent = AskMeAgent(repo_path, settings)
        answer = agent.ask(args.question)
        print(f"\nAnswer:\n{answer['answer']}")
        if answer.get("tool_usage"):
            print(f"\nTools used ({len(answer['tool_usage'])}):")
            for tc in answer["tool_usage"]:
                print(f"  {tc['tool']}: {tc['args']}")

    elif args.command == "list":
        from askmyrepo.cloning.repo_cloner import RepoCloner
        cloner = RepoCloner(settings)
        repos = cloner.list_repos()
        if repos:
            print("Cloned repos:")
            for r in repos:
                print(f"  {r}")
        else:
            print("No cloned repos. Use 'askme clone <url>' first.")


if __name__ == "__main__":
    main()
