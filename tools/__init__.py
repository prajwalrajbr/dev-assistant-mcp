from pathlib import Path


def check_path(path: str, kind: str = "any") -> dict | None:
    """Return an error dict if path fails validation, else None.

    kind: "file" | "dir" | "any"
    """
    p = Path(path)
    if not p.exists():
        label = "File" if kind == "file" else "Directory" if kind == "dir" else "Path"
        return {"error": f"{label} does not exist: {path}"}
    if kind == "file" and not p.is_file():
        return {"error": f"Not a file: {path}"}
    if kind == "dir" and not p.is_dir():
        return {"error": f"Not a directory: {path}"}
    return None
