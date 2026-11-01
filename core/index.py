import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core.ast_parser import parse

_cache: dict = {}
_lock = threading.Lock()


class _Invalidator(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            with _lock:
                _cache.pop(event.src_path, None)

    def on_deleted(self, event):
        if not event.is_directory:
            with _lock:
                _cache.pop(event.src_path, None)

    def on_moved(self, event):
        with _lock:
            _cache.pop(event.src_path, None)


def get_tree(path: str, source: str):
    with _lock:
        if path not in _cache:
            _cache[path] = parse(source)
        return _cache[path]


def invalidate(path: str):
    with _lock:
        _cache.pop(path, None)


def start_watcher(watch_path: str = "."):
    observer = Observer()
    observer.schedule(_Invalidator(), path=watch_path, recursive=True)
    observer.daemon = True
    observer.start()
