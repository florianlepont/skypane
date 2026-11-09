"""A per-process cache of what the history pages derive from `history.db`.

Flights, the Airlines collection and the Airline editor each fold the whole
stored history (repeated passes, airline keys) on every request, which costs
more than the page itself once the history is long. The folded result only
changes when `history.db` changes, so it is kept per database file and
recomputed when the file's signature moves: the modification time and size of
the database file together with the row count and highest id of
`runway_events`. Events are only ever inserted (or removed), and a commit in
WAL mode lands in the log before the main file moves, so the count and the
highest id are what notice a new flight at once.

The cached value is shared between requests: a caller must treat it as read
only.
"""
import os
import threading

_MAX_ENTRIES = 6
_LOCK = threading.Lock()
_CACHE = {}


def _database_file(conn):
    """The path of `conn`'s main database file, or None for an in-memory one."""
    for _seq, name, path in conn.execute("PRAGMA database_list").fetchall():
        if name == "main":
            return path or None
    return None


def _file_state(path):
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _signature(conn, path):
    count, newest = conn.execute("SELECT COUNT(*), MAX(id) FROM runway_events").fetchone()
    return (_file_state(path), count, newest)


def cached(conn, name, loader):
    """`loader()`'s result for `name` (any hashable), reused while the
    database behind `conn` has not changed. Without a database file the
    loader simply runs."""
    path = _database_file(conn)
    if path is None:
        return loader()
    signature = _signature(conn, path)
    key = (path, name)
    with _LOCK:
        hit = _CACHE.get(key)
    if hit is not None and hit[0] == signature:
        return hit[1]
    value = loader()
    with _LOCK:
        _CACHE.pop(key, None)
        _CACHE[key] = (signature, value)
        while len(_CACHE) > _MAX_ENTRIES:
            _CACHE.pop(next(iter(_CACHE)))
    return value


def clear():
    """Forget everything (a test, or after the file was replaced)."""
    with _LOCK:
        _CACHE.clear()
