import threading
from pathlib import Path
from core.ast_parser import parse

_cache: dict = {}
_lock = threading.Lock()


def get_tree(path: str, source: str):
    ext = Path(path).suffix
    mtime = Path(path).stat().st_mtime if Path(path).exists() else None
    with _lock:
        if path in _cache:
            cached_mtime, tree = _cache[path]
            if cached_mtime == mtime:
                return tree
        tree = parse(source, ext)
        _cache[path] = (mtime, tree)
        return tree
