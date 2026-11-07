import re
from pathlib import Path
from tools import check_path


def list_directory(path: str) -> dict:
    """List contents of a directory."""
    if err := check_path(path, "dir"):
        return err

    p = Path(path)
    items = [
        {"name": item.name, "type": "directory" if item.is_dir() else "file", "path": str(item)}
        for item in sorted(p.iterdir())
    ]
    return {"path": str(p), "items": items, "count": len(items)}


def read_file(path: str) -> dict:
    """Read the full contents of a file."""
    if err := check_path(path, "file"):
        return err

    p = Path(path)
    content = p.read_text(encoding="utf-8", errors="replace")
    return {"path": str(p), "content": content, "lines": content.count("\n") + 1}


def write_file(path: str, content: str) -> dict:
    """Write content to a file, creating parent directories if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}


def search_files(directory: str, pattern: str) -> dict:
    """Search for a regex pattern across all files in a directory."""
    if err := check_path(directory, "dir"):
        return err

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return {"error": f"Invalid regex pattern: {e}"}

    p = Path(directory)
    matches = []
    for file in p.rglob("*"):
        if not file.is_file():
            continue
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    matches.append({"file": str(file), "line": i, "content": line.strip()})
        except Exception:
            continue

    return {"pattern": pattern, "matches": matches, "count": len(matches)}
