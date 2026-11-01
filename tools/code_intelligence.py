import subprocess
from pathlib import Path
from core.ast_parser import traverse, node_text
from core.index import get_tree


def _load(path: str):
    p = Path(path)
    if not p.exists():
        return None, None, f"File does not exist: {path}"
    source = p.read_text(encoding="utf-8")
    tree = get_tree(str(p), source)
    return tree, source, None


def find_symbol(path: str, name: str) -> dict:
    """Find where a function or class named `name` is defined in a file."""
    tree, source, err = _load(path)
    if err:
        return {"error": err}

    results = []
    for node_type in ("function_definition", "class_definition"):
        for node in traverse(tree.root_node, node_type):
            name_node = node.child_by_field_name("name")
            if node_text(name_node) == name:
                results.append({
                    "type": node_type.replace("_definition", ""),
                    "name": name,
                    "line": node.start_point[0] + 1,
                    "file": path,
                })

    return {"symbol": name, "results": results, "count": len(results)}


def get_references(directory: str, name: str) -> dict:
    """Find all call sites of `name` across all Python files in a directory."""
    p = Path(directory)
    if not p.exists():
        return {"error": f"Directory does not exist: {directory}"}

    references = []
    for file in p.rglob("*.py"):
        source = file.read_text(encoding="utf-8")
        tree = get_tree(str(file), source)

        for node in traverse(tree.root_node, "call"):
            func_node = node.child_by_field_name("function")
            if func_node:
                # handle both plain calls (foo) and attribute calls (obj.foo)
                func_name = node_text(func_node).split(".")[-1]
                if func_name == name:
                    references.append({
                        "file": str(file),
                        "line": node.start_point[0] + 1,
                        "call": node_text(func_node),
                    })

    return {"symbol": name, "references": references, "count": len(references)}


def get_imports(path: str) -> dict:
    """List all import statements in a Python file."""
    tree, source, err = _load(path)
    if err:
        return {"error": err}

    imports = []
    for node_type in ("import_statement", "import_from_statement"):
        for node in traverse(tree.root_node, node_type):
            imports.append({
                "type": node_type,
                "statement": node_text(node),
                "line": node.start_point[0] + 1,
            })

    imports.sort(key=lambda x: x["line"])
    return {"file": path, "imports": imports, "count": len(imports)}


def run_tests(path: str) -> dict:
    """Run pytest on a file or directory and return results."""
    p = Path(path)
    if not p.exists():
        return {"error": f"Path does not exist: {path}"}

    result = subprocess.run(
        ["python", "-m", "pytest", str(p), "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "path": str(p),
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "output": result.stdout,
        "errors": result.stderr,
    }


def get_lint_errors(path: str) -> dict:
    """Run flake8 on a file and return lint errors."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File does not exist: {path}"}

    result = subprocess.run(
        ["python", "-m", "flake8", str(p), "--format=%(row)d:%(col)d:%(code)s:%(text)s"],
        capture_output=True,
        text=True,
    )

    errors = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(":", 3)
        if len(parts) == 4:
            errors.append({
                "line": int(parts[0]),
                "col": int(parts[1]),
                "code": parts[2],
                "message": parts[3].strip(),
            })
        else:
            errors.append({"raw": line})

    return {"file": str(p), "errors": errors, "count": len(errors)}
