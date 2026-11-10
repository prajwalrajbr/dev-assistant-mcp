import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tools import check_path

load_dotenv()

_TRASH_DIR = (Path(__file__).parent.parent / os.getenv("TRASH_DIR", ".trash")).resolve()

_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", "target", ".trash",
}


def _is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return b"\x00" in f.read(512)
    except Exception:
        return True


def list_directory(path: str) -> dict:
    """List all files and subdirectories inside a directory, sorted alphabetically."""
    if err := check_path(path, "dir"):
        return err

    p = Path(path)
    items = [
        {"name": item.name, "type": "directory" if item.is_dir() else "file", "path": str(item)}
        for item in sorted(p.iterdir())
    ]
    return {"path": str(p), "items": items, "count": len(items)}


def read_file(path: str) -> dict:
    """Read the full text content of a file. Returns content and line count."""
    if err := check_path(path, "file"):
        return err

    p = Path(path)
    content = p.read_text(encoding="utf-8", errors="replace")
    return {"path": str(p), "content": content, "lines": content.count("\n") + 1}


def write_file(path: str, content: str) -> dict:
    """Write content to a file, creating parent directories if needed. Overwrites if the file already exists."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "bytes_written": len(content.encode("utf-8"))}


def delete_file(path: str) -> dict:
    """Soft-delete a file by moving it to the trash folder (TRASH_DIR) instead of permanently removing it. Appends a timestamp to the filename if a collision occurs in the trash."""
    if err := check_path(path, "file"):
        return err

    p = Path(path)
    trash = Path(_TRASH_DIR)

    dest = trash / p.name
    try:
        trash.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = trash / f"{p.stem}_{timestamp}{p.suffix}"
        shutil.move(str(p), dest)
    except Exception as e:
        return {"error": f"Could not move file to trash: {e}"}
    return {"original": str(p), "moved_to": str(dest), "trash_dir": str(trash)}


def move_file(src: str, dst: str) -> dict:
    """Move or rename a file. Creates destination parent directories if needed. Fails if the destination already exists."""
    if err := check_path(src, "file"):
        return err

    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        return {"error": f"Destination already exists: {dst}"}

    shutil.move(str(src_path), dst_path)
    return {"src": str(src_path), "dst": str(dst_path)}


def search_files(directory: str, pattern: str, extensions: list[str] | None = None) -> dict:
    """Search for a regex pattern across all text files in a directory tree. Skips binaries and noise directories (.git, node_modules, __pycache__, .venv, dist, build, target, .trash). Optionally filter by file extension."""
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
        if any(part in _SKIP_DIRS for part in file.parts):
            continue
        if _is_binary(file):
            continue
        if extensions and file.suffix.lower() not in extensions:
            continue
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if regex.search(line):
                    matches.append({"file": str(file), "line": i, "content": line.strip()})
        except Exception:
            continue

    return {"pattern": pattern, "matches": matches, "count": len(matches)}
