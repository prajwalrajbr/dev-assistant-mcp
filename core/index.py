import threading
from pathlib import Path
from core.ast_parser import parse

_cache: dict = {}
_lock = threading.Lock()


def get_tree(path: str, source: str):
    p = Path(path)
    ext = p.suffix
    with _lock:
        mtime = p.stat().st_mtime if p.exists() else None
        if path in _cache:
            cached_mtime, tree = _cache[path]
            if cached_mtime == mtime:
                return tree
        tree = parse(source, ext)
        _cache[path] = (mtime, tree)
        return tree
