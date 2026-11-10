import os
from tree_sitter import Language, Parser
from dotenv import load_dotenv
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_java as tsjava

load_dotenv()

_AST_MAX_DEPTH = int(os.getenv("AST_MAX_DEPTH", 100))

_LANGUAGES = {
    ".py":   Language(tspython.language()),
    ".js":   Language(tsjavascript.language()),
    ".ts":   Language(tstypescript.language_typescript()),
    ".java": Language(tsjava.language()),
}

_NODE_TYPES = {
    ".py":   {"function": "function_definition",  "class": "class_definition",  "call": "call",             "constructor": None,                        "arrow": None},
    ".js":   {"function": "function_declaration", "class": "class_declaration", "call": "call_expression",  "constructor": None,                        "arrow": "variable_declarator"},
    ".ts":   {"function": "function_declaration", "class": "class_declaration", "call": "call_expression",  "constructor": None,                        "arrow": "variable_declarator"},
    ".java": {"function": "method_declaration",   "class": "class_declaration", "call": "method_invocation","constructor": "object_creation_expression", "arrow": None},
}

_PARSERS = {ext: Parser(lang) for ext, lang in _LANGUAGES.items()}

SUPPORTED_EXTENSIONS = set(_LANGUAGES.keys())


def parse(source: str, ext: str):
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"Unsupported file extension: {ext}")
    return parser.parse(bytes(source, "utf-8"))


def traverse(node, node_type: str) -> list:
    results = []
    stack = [(node, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > _AST_MAX_DEPTH:
            continue
        if current.type == node_type:
            results.append(current)
        for child in reversed(current.children):
            stack.append((child, depth + 1))
    return results


def node_text(node) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8")


def get_node_types(ext: str) -> dict:
    types = _NODE_TYPES.get(ext)
    if types is None:
        raise ValueError(f"No node types defined for extension: {ext}")
    return types
