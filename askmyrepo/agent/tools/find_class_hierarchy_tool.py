"""find_class_hierarchy tool: get parent/child class chains."""

from pathlib import Path

from askmyrepo.config import Settings
from askmyrepo.parser.tree_sitter_parser import CodeParser


class FindClassHierarchyTool:
    """Find the inheritance hierarchy of a class."""

    name = "find_class_hierarchy"
    description = (
        "Find the inheritance chain of a class: what it extends and what extends it. "
        "Use when the user asks about class inheritance, parent classes, or subclasses."
    )
    parameters = {
        "type": "object",
        "properties": {
            "class_name": {
                "type": "string",
                "description": "The class name to look up (e.g., 'BaseAgent')",
            },
        },
        "required": ["class_name"],
    }

    def __init__(self, repo_path: Path, settings: Settings):
        self.repo_path = repo_path
        self.settings = settings

    def run(self, class_name: str) -> str:
        parser = CodeParser(self.settings)
        all_nodes = parser.parse_directory(self.repo_path)

        class_nodes = [
            n for n in all_nodes
            if n.node_type.value == "class_definition" and n.name == class_name
        ]

        if not class_nodes:
            return f"Class '{class_name}' not found in the codebase."

        cls = class_nodes[0]
        lines = [f"Class: {cls.name} in {cls.file_path}:{cls.line_start}"]

        if cls.base_classes:
            lines.append(f"  extends: {', '.join(cls.base_classes)}")
        else:
            lines.append("  extends: (none)")

        # Find subclasses
        subclasses = [
            n for n in all_nodes
            if n.node_type.value == "class_definition"
            and cls.name in n.base_classes
        ]
        if subclasses:
            lines.append(f"  subclass of: {cls.name}")
            for sub in subclasses:
                lines.append(f"    - {sub.name} in {sub.file_path}:{sub.line_start}")
        else:
            lines.append("  subclass of: (none found)")

        # Find all methods
        methods = [
            n for n in all_nodes
            if n.node_type.value == "method_definition"
            and n.name.startswith(f"{class_name}.")
        ]
        if methods:
            lines.append(f"  methods ({len(methods)}):")
            for m in methods:
                lines.append(f"    - {m.name} at {m.file_path}:{m.line_start}")

        return "\n".join(lines)
