from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_java as tsjava

_LANGUAGES = {
    ".py":   Language(tspython.language()),
    ".js":   Language(tsjavascript.language()),
    ".ts":   Language(tstypescript.language_typescript()),
    ".java": Language(tsjava.language()),
}

_NODE_TYPES = {
    ".py":   {"function": "function_definition",  "class": "class_definition",  "call": "call"},
    ".js":   {"function": "function_declaration", "class": "class_declaration", "call": "call_expression"},
    ".ts":   {"function": "function_declaration", "class": "class_declaration", "call": "call_expression"},
    ".java": {"function": "method_declaration",   "class": "class_declaration", "call": "method_invocation"},
}


def parse(source: str, ext: str):
    lang = _LANGUAGES.get(ext)
    if lang is None:
        raise ValueError(f"Unsupported file extension: {ext}")
    parser = Parser(lang)
    return parser.parse(bytes(source, "utf-8"))


def traverse(node, node_type: str) -> list:
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(traverse(child, node_type))
    return results


def node_text(node) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8")


def get_node_types(ext: str) -> dict:
    return _NODE_TYPES.get(ext, {})
