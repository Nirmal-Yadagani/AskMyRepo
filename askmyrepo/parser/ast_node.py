"""AST node representation models."""

from __future__ import annotations

from pydantic import BaseModel

from askmyrepo.models import CodeNode, Language, NodeType


def _node_type_from_ts(node_type: str) -> NodeType:
    """Map tree-sitter node type strings to our NodeType enum."""
    mapping = {
        "function_definition": NodeType.FUNCTION_DEF,
        "class_definition": NodeType.CLASS_DEF,
        "import_statement": NodeType.IMPORT,
        "method_definition": NodeType.METHOD_DEF,
        "attribute_definition": NodeType.ATTRIBUTE_DEF,
        "call_expression": NodeType.CALL,
        "module": NodeType.MODULE,
    }
    return NodeType(mapping.get(node_type, node_type))


def node_name(node) -> str:
    """Extract the name of a tree-sitter node if it has one."""
    try:
        return node.children_by_field_name("name")[0].text.decode()
    except (AttributeError, IndexError):
        return ""


def node_params(node) -> list[dict[str, str]] | None:
    """Extract parameter info from a function/method node."""
    try:
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            return None
        params = []
        for child in params_node.children:
            param_name = ""
            param_type = ""
            if child.type == "identifier":
                param_name = child.text.decode()
            elif child.type == "parameter":
                name_node = child.children_by_field_name("name")
                if name_node:
                    param_name = name_node[0].text.decode()
            elif child.type == "type_annotation":
                param_name = child.children[0].text.decode()
            else:
                param_name = child.text.decode()
            params.append({"name": param_name, "type": param_type})
        return params if params else None
    except (AttributeError, IndexError):
        return None


def node_return_type(node) -> str | None:
    """Extract return type annotation from a function node."""
    try:
        for child in node.children:
            if child.type == "return_type":
                return child.text.decode()
            if child.type == "type_annotation":
                return child.text.decode()
        return None
    except (AttributeError, IndexError):
        return None


def node_base_classes(node) -> list[str]:
    """Extract base classes from a class definition node."""
    bases = []
    try:
        if hasattr(node, 'children_by_field_name'):
            bases_node = node.children_by_field_name("superclasses")
            if bases_node:
                for base in bases_node[0].children:
                    if hasattr(base, 'type') and base.type == "identifier":
                        bases.append(base.text.decode())
                    elif hasattr(base, 'text'):
                        bases.append(base.text.decode())
    except (AttributeError, IndexError):
        pass
    return bases


def node_docstring(node) -> str | None:
    """Extract docstring from a node if it exists."""
    try:
        for child in node.children:
            if child.type in ("block", "document"):
                # Look for string node as docstring
                for grandchild in child.children:
                    if hasattr(grandchild, 'type') and grandchild.type in ("string", "raw_string"):
                        text = grandchild.text.decode()
                        # Strip quotes
                        if text.startswith(('"""', "'''", '"""')):
                            return text[3:-3].strip()
                        return text.strip()
        return None
    except (AttributeError, IndexError):
        return None


def node_decorators(node) -> list[str]:
    """Extract decorators from a node."""
    decorators = []
    try:
        for child in node.children:
            if child.type == "decorator":
                # Get the text of the decorator
                text = child.text.decode().strip()
                if text.startswith("@"):
                    decorators.append(text)
                else:
                    decorators.append(f"@{text}")
    except (AttributeError, IndexError):
        pass
    return decorators


def get_node_text(node) -> str:
    """Get the full text of a tree-sitter node."""
    try:
        return node.text.decode()
    except (AttributeError, UnicodeDecodeError):
        return ""
