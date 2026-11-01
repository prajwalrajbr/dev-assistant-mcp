from tree_sitter import Language, Parser
import tree_sitter_python as tspython

_PY_LANGUAGE = Language(tspython.language())


def parse(source: str):
    parser = Parser(_PY_LANGUAGE)
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
