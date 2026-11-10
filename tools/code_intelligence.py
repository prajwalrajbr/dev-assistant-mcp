import os
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv
from core.ast_parser import traverse, node_text, get_node_types
from core.index import get_tree
from tools import check_path

load_dotenv()

_TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", 60))

_SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".java"}


def _load(path: str):
    p = Path(path)
    if err := check_path(path, "file"):
        return None, None, None, err["error"]
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

    # regular function and class definitions
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

    # JS/TS arrow functions: const foo = () => {}
    arrow_node_type = node_types.get("arrow")
    if arrow_node_type:
        for node in traverse(tree.root_node, arrow_node_type):
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if value_node and value_node.type == "arrow_function" and node_text(name_node) == name:
                results.append({
                    "type": "arrow_function",
                    "name": name,
                    "line": node.start_point[0] + 1,
                    "file": path,
                })

    return {"symbol": name, "results": results, "count": len(results)}


def get_symbols(path: str) -> dict:
    """List all functions, classes, and arrow functions defined in a file."""
    tree, source, ext, err = _load(path)
    if err:
        return {"error": err}

    node_types = get_node_types(ext)
    symbols = []

    for kind, node_type in [("function", node_types["function"]), ("class", node_types["class"])]:
        for node in traverse(tree.root_node, node_type):
            name_node = node.child_by_field_name("name")
            symbol_name = node_text(name_node)
            if symbol_name:
                symbols.append({
                    "type": kind,
                    "name": symbol_name,
                    "line": node.start_point[0] + 1,
                })

    arrow_node_type = node_types.get("arrow")
    if arrow_node_type:
        for node in traverse(tree.root_node, arrow_node_type):
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            if value_node and value_node.type == "arrow_function":
                symbol_name = node_text(name_node)
                if symbol_name:
                    symbols.append({
                        "type": "arrow_function",
                        "name": symbol_name,
                        "line": node.start_point[0] + 1,
                    })

    symbols.sort(key=lambda x: x["line"])
    return {"file": path, "symbols": symbols, "count": len(symbols)}


def get_references(directory: str, name: str) -> dict:
    """Find all call sites of `name` across all supported files in a directory."""
    if err := check_path(directory, "dir"):
        return err

    p = Path(directory)
    references = []
    for ext in _SUPPORTED_EXTENSIONS:
        for file in p.rglob(f"*{ext}"):
            try:
                source = file.read_text(encoding="utf-8")
                tree = get_tree(str(file), source)
                node_types = get_node_types(ext)
                call_type = node_types.get("call", "call")
                constructor_type = node_types.get("constructor")

                # collect both method calls and constructor calls (Java: new Foo())
                call_nodes = traverse(tree.root_node, call_type)
                if constructor_type:
                    call_nodes += traverse(tree.root_node, constructor_type)

                for node in call_nodes:
                    # method calls use "function"/"name"; constructors use "type"
                    func_node = (
                        node.child_by_field_name("function")
                        or node.child_by_field_name("name")
                        or node.child_by_field_name("type")
                    )
                    if func_node:
                        func_name = node_text(func_node).split(".")[-1]
                        if func_name == name:
                                references.append({
                                    "file": str(file),
                                    "line": node.start_point[0] + 1,
                                    "call": node_text(func_node),
                                })
            except Exception:
                continue

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
    if err := check_path(path):
        return err

    p = Path(path)
    ext = p.suffix if p.is_file() else None

    if ext in (".js", ".ts") or (p.is_dir() and (p / "package.json").exists()):
        cmd = ["npx", "jest", str(p), "--verbose"]
    elif ext == ".java" or (p.is_dir() and (p / "pom.xml").exists()):
        cmd = ["mvn", "test", "-f", str(p / "pom.xml") if p.is_dir() else str(p.parent / "pom.xml")]
    elif p.is_dir() and (p / "build.gradle").exists():
        cmd = ["./gradlew", "test", "--project-dir", str(p)]
    else:
        cmd = ["python", "-m", "pytest", str(p), "-v", "--tb=short"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_TEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {
            "path": str(p),
            "runner": cmd[0],
            "passed": False,
            "exit_code": None,
            "output": "",
            "errors": f"Tests timed out after {_TEST_TIMEOUT}s",
        }
    return {
        "path": str(p),
        "runner": cmd[0],
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "output": result.stdout,
        "errors": result.stderr,
    }


def get_lint_errors(path: str) -> dict:
    """Run a linter on a file and return lint errors."""
    if err := check_path(path, "file"):
        return err

    p = Path(path)
    if p.suffix == ".py":
        return _lint_python(p)
    elif p.suffix in (".js", ".ts"):
        return _lint_js_ts(p)
    elif p.suffix == ".java":
        return _lint_java(p)
    else:
        return {"error": f"No linter available for {p.suffix} files"}


def _lint_python(p: Path) -> dict:
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
    return {"file": str(p), "linter": "flake8", "errors": errors, "count": len(errors)}


def _lint_js_ts(p: Path) -> dict:
    result = subprocess.run(
        ["npx", "eslint", str(p), "--format", "json"],
        capture_output=True,
        text=True,
    )
    errors = []
    try:
        data = json.loads(result.stdout)
        for file_result in data:
            for msg in file_result.get("messages", []):
                errors.append({
                    "line": msg.get("line"),
                    "col": msg.get("column"),
                    "code": msg.get("ruleId", "unknown"),
                    "message": msg.get("message"),
                    "severity": "error" if msg.get("severity") == 2 else "warning",
                })
    except (json.JSONDecodeError, KeyError):
        errors.append({"raw": result.stdout})
    return {"file": str(p), "linter": "eslint", "errors": errors, "count": len(errors)}


def _lint_java(p: Path) -> dict:
    result = subprocess.run(
        ["checkstyle", "-c", "/google_checks.xml", str(p)],
        capture_output=True,
        text=True,
    )
    errors = []
    for line in result.stdout.strip().splitlines():
        if line.startswith("[ERROR]") or line.startswith("[WARN]"):
            try:
                severity = "error" if line.startswith("[ERROR]") else "warning"
                rest = line.split("] ", 1)[1]
                location, message = rest.split(": ", 1)
                parts = location.split(":")
                errors.append({
                    "line": int(parts[1]) if len(parts) > 1 else None,
                    "col": int(parts[2]) if len(parts) > 2 else None,
                    "message": message.strip(),
                    "severity": severity,
                })
            except (IndexError, ValueError):
                errors.append({"raw": line})
    return {"file": str(p), "linter": "checkstyle", "errors": errors, "count": len(errors)}
