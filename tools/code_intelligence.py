import subprocess
from pathlib import Path
from core.ast_parser import traverse, node_text, get_node_types
from core.index import get_tree

_SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java"}


def _load(path: str):
    p = Path(path)
    if not p.exists():
        return None, None, None, f"File does not exist: {path}"
    if p.suffix not in _SUPPORTED_EXTENSIONS:
        return None, None, None, f"Unsupported file type: {p.suffix}"
    source = p.read_text(encoding="utf-8")
    tree = get_tree(str(p), source)
    return tree, source, p.suffix, None


def find_symbol(path: str, name: str) -> dict:
    """Find where a function or class named `name` is defined in a file."""
    tree, source, ext, err = _load(path)
    if err:
        return {"error": err}

    node_types = get_node_types(ext)
    results = []
    for kind, node_type in [("function", node_types["function"]), ("class", node_types["class"])]:
        for node in traverse(tree.root_node, node_type):
            name_node = node.child_by_field_name("name")
            if node_text(name_node) == name:
                results.append({
                    "type": kind,
                    "name": name,
                    "line": node.start_point[0] + 1,
                    "file": path,
                })

    return {"symbol": name, "results": results, "count": len(results)}


def get_references(directory: str, name: str) -> dict:
    """Find all call sites of `name` across all supported files in a directory."""
    p = Path(directory)
    if not p.exists():
        return {"error": f"Directory does not exist: {directory}"}

    references = []
    for ext in _SUPPORTED_EXTENSIONS:
        for file in p.rglob(f"*{ext}"):
            source = file.read_text(encoding="utf-8")
            tree = get_tree(str(file), source)
            node_types = get_node_types(ext)
            call_type = node_types.get("call", "call")

            for node in traverse(tree.root_node, call_type):
                func_node = node.child_by_field_name("function") or node.child_by_field_name("name")
                if func_node:
                    func_name = node_text(func_node).split(".")[-1]
                    if func_name == name:
                        references.append({
                            "file": str(file),
                            "line": node.start_point[0] + 1,
                            "call": node_text(func_node),
                        })

    return {"symbol": name, "references": references, "count": len(references)}


def get_imports(path: str) -> dict:
    """List all import statements in a file."""
    tree, source, ext, err = _load(path)
    if err:
        return {"error": err}

    if ext == ".py":
        import_types = ("import_statement", "import_from_statement")
    elif ext in (".js", ".ts"):
        import_types = ("import_statement",)
    elif ext == ".java":
        import_types = ("import_declaration",)
    else:
        import_types = ()

    imports = []
    for node_type in import_types:
        for node in traverse(tree.root_node, node_type):
            imports.append({
                "type": node_type,
                "statement": node_text(node),
                "line": node.start_point[0] + 1,
            })

    imports.sort(key=lambda x: x["line"])
    return {"file": path, "imports": imports, "count": len(imports)}


def run_tests(path: str) -> dict:
    """Run tests for a file or directory using the appropriate test runner."""
    p = Path(path)
    if not p.exists():
        return {"error": f"Path does not exist: {path}"}

    ext = p.suffix if p.is_file() else None

    if ext in (".js", ".ts") or (p.is_dir() and (p / "package.json").exists()):
        cmd = ["npx", "jest", str(p), "--verbose"]
    elif ext == ".java" or (p.is_dir() and (p / "pom.xml").exists()):
        cmd = ["mvn", "test", "-f", str(p / "pom.xml") if p.is_dir() else str(p.parent / "pom.xml")]
    elif p.is_dir() and (p / "build.gradle").exists():
        cmd = ["./gradlew", "test", "--project-dir", str(p)]
    else:
        cmd = ["python", "-m", "pytest", str(p), "-v", "--tb=short"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return {
        "path": str(p),
        "runner": cmd[0],
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "output": result.stdout,
        "errors": result.stderr,
    }


def get_lint_errors(path: str) -> dict:
    """Run flake8 on a Python file and return lint errors."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File does not exist: {path}"}
    if p.suffix != ".py":
        return {"error": "flake8 only supports Python files"}

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
