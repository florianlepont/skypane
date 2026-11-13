"""Removal of private photo files, and the sweep that reconciles files with rows.

Ordering invariant: the database rows go first, inside the caller's
transaction; the files go after COMMIT. A crash or an unlink failure after the
commit leaves orphan files, never a row that points at nothing visible to a
user, and `sweep` removes those orphans. The sweep also drops rows whose file
is gone (a restore of fleet.db without the photo tree).

Security invariant: nothing here follows a symlink. Entries are inspected with
`lstat`/`scandir(follow_symlinks=False)` and a link is unlinked as a link, so
a planted link can never make a delete reach a file outside the photo tree.
Ids are shape-checked before they are joined onto a path.

Privacy invariant: results are integer counts only. Nothing here prints or
logs a photo id, a file name or a path, and no exception text escapes.

Leaf module: stdlib plus `server.fleet_db`, `server.photo_paths` and
`server.device_dirs`.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import sys
import time
from typing import NamedTuple

# Same repo-root sys.path bootstrap as server/photo_paths.py.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import device_dirs, fleet_db, photo_paths  # noqa: E402

DEFAULT_GRACE_SECONDS = 15 * 60


class PurgeResult(NamedTuple):
    """`purged`/`removed` counts what was deleted; `failed` counts unlinks that
    raised, so the caller can run `sweep` to finish the job."""
    purged: int
    failed: int


class SweepCounts(NamedTuple):
    orphan_dirs: int = 0
    orphan_files: int = 0
    stale_temps: int = 0
    missing_rows: int = 0
    links: int = 0
    refused: int = 0


class _Tally:
    def __init__(self) -> None:
        self.orphan_dirs = 0
        self.orphan_files = 0
        self.stale_temps = 0
        self.missing_rows = 0
        self.links = 0
        self.refused = 0

    def freeze(self) -> SweepCounts:
        return SweepCounts(
            self.orphan_dirs, self.orphan_files, self.stale_temps,
            self.missing_rows, self.links, self.refused)


def _remove_tree(path: str) -> tuple[int, int]:
    """Delete `path` and everything below it without following links.

    Returns (links removed, failures). A symlink at `path` itself is unlinked
    as a link.
    """
    links = failures = 0
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return 0, 0
    except OSError:
        return 0, 1
    if not stat.S_ISDIR(mode):
        try:
            os.unlink(path)
        except OSError:
            return 0, 1
        return (1 if stat.S_ISLNK(mode) else 0), 0
    try:
        with os.scandir(path) as it:
            children = [e.path for e in it]
    except OSError:
        return 0, 1
    for child in children:
        sub_links, sub_failures = _remove_tree(child)
        links += sub_links
        failures += sub_failures
    try:
        os.rmdir(path)
    except OSError:
        failures += 1
    return links, failures


def _photos_top(root: str) -> str:
    return os.path.join(root, photo_paths.PHOTOS_DIRNAME)


def _top_is_symlink(root: str) -> bool:
    return os.path.islink(_photos_top(root))


def remove_files(
    conn: sqlite3.Connection, root: str, refs: list[tuple[str, str]]
) -> PurgeResult:
    """Unlink the files of (device id, photo id) refs whose rows are gone.

    Call after the transaction that deleted the rows has committed: a ref
    whose row still exists (for instance after a rollback) is left alone. A
    missing file is fine, a malformed ref is skipped, and an emptied device
    directory is removed. Returns (files removed, unlink failures).
    """
    removed = failed = 0
    touched: set[str] = set()
    for device_id, photo_id in refs:
        if not (isinstance(device_id, str) and device_dirs.is_valid_device_id(device_id)
                and photo_paths.is_valid_photo_id(photo_id)):
            continue
        if fleet_db.get_photo_row(conn, device_id, photo_id) is not None:
            continue
        try:
            directory = photo_paths.photo_dir(root, device_id)
        except ValueError:
            continue  # symlinked parent: never follow it; the sweep unlinks the link
        path = os.path.join(directory, photo_id + photo_paths.PHOTO_SUFFIX)
        touched.add(directory)
        try:
            os.lstat(path)
        except FileNotFoundError:
            continue
        except OSError:
            failed += 1
            continue
        try:
            os.unlink(path)
            removed += 1
        except FileNotFoundError:
            pass
        except OSError:
            failed += 1
    for directory in touched:
        try:
            os.rmdir(directory)  # only succeeds when empty
        except OSError:
            pass
    return PurgeResult(removed, failed)


def purge_frame(conn: sqlite3.Connection, root: str, device_id: str) -> PurgeResult:
    """Delete every photo of a frame: rows in a transaction, then the files,
    then the whole device directory (temp files included).

    Returns (photos purged, failures); a second call purges 0. Raises
    ValueError for a malformed device id before touching anything.
    """
    if not isinstance(device_id, str) or not device_dirs.is_valid_device_id(device_id):
        raise ValueError("invalid device id")
    ids = fleet_db.delete_photo_rows(conn, device_id)
    result = remove_files(conn, root, [(device_id, pid) for pid in ids])
    failed = result.failed
    if not _top_is_symlink(root):
        _links, tree_failures = _remove_tree(os.path.join(_photos_top(root), device_id))
        failed += tree_failures
    return PurgeResult(len(ids), failed)


def _old_enough(path: str, now: float, grace_seconds: int) -> bool:
    try:
        return os.lstat(path).st_mtime <= now - grace_seconds
    except OSError:
        return False


def _device_ids(conn: sqlite3.Connection) -> set[str]:
    return {str(r["id"]) for r in conn.execute("SELECT id FROM devices")}


def _sweep_orphan_dirs(root: str, devices: set[str], tally: _Tally) -> list[str]:
    """Rule: directories of devices that no longer exist go, with no grace
    period; links are unlinked. Returns the device directories that stay."""
    keep: list[str] = []
    top = _photos_top(root)
    try:
        with os.scandir(top) as it:
            entries = [(e.name, e.path) for e in it]
    except OSError:
        return keep
    for name, path in entries:
        try:
            mode = os.lstat(path).st_mode
        except OSError:
            continue
        if stat.S_ISLNK(mode):
            if _remove_tree(path)[1] == 0:
                tally.links += 1
            continue
        if not stat.S_ISDIR(mode):
            if _remove_tree(path)[1] == 0:
                tally.orphan_files += 1
            continue
        if device_dirs.is_valid_device_id(name) and name in devices:
            keep.append(path)
            continue
        links, failures = _remove_tree(path)
        tally.links += links
        if failures == 0:
            tally.orphan_dirs += 1
    return keep


def _sweep_entry(
    path: str, name: str, mode: int, rows: set[str], now: float, grace: int,
    tally: _Tally,
) -> None:
    if stat.S_ISLNK(mode):
        if _remove_tree(path)[1] == 0:
            tally.links += 1
        return
    if stat.S_ISDIR(mode):
        links, failures = _remove_tree(path)
        tally.links += links
        if failures == 0:
            tally.orphan_dirs += 1
        return
    if name.startswith(photo_paths.TEMP_PREFIX):
        if _old_enough(path, now, grace) and _remove_tree(path)[1] == 0:
            tally.stale_temps += 1
        return
    stem, suffix = os.path.splitext(name)
    if suffix == photo_paths.PHOTO_SUFFIX and stem in rows:
        return
    if _old_enough(path, now, grace) and _remove_tree(path)[1] == 0:
        tally.orphan_files += 1


def _sweep_device_dir(
    directory: str, rows: set[str], now: float, grace: int, tally: _Tally
) -> None:
    """Rules for one live device directory: links, stale temp files, and
    unrowed files older than the grace period."""
    try:
        with os.scandir(directory) as it:
            entries = [(e.name, e.path) for e in it]
    except OSError:
        return
    for name, path in entries:
        try:
            mode = os.lstat(path).st_mode
        except OSError:
            continue
        _sweep_entry(path, name, mode, rows, now, grace, tally)


def _sweep_missing_rows(conn: sqlite3.Connection, root: str, tally: _Tally) -> None:
    """Rule: rows whose file is missing are deleted (restore without photos,
    partial failure). Runs after the file rules so a removed link counts as
    missing."""
    stale: list[tuple[str, str]] = []
    for device_id, photo_id in fleet_db.all_photo_refs(conn):
        try:
            path = photo_paths.photo_file(root, device_id, photo_id)
        except ValueError:
            stale.append((device_id, photo_id))
            continue
        try:
            os.lstat(path)
        except FileNotFoundError:
            stale.append((device_id, photo_id))
        except OSError:
            continue
    if not stale:
        return
    with fleet_db.transaction(conn):
        for device_id, photo_id in stale:
            if fleet_db.delete_photo_row(conn, device_id, photo_id):
                tally.missing_rows += 1


def sweep(
    conn: sqlite3.Connection,
    root: str,
    now: float | None = None,
    grace_seconds: int = DEFAULT_GRACE_SECONDS,
) -> SweepCounts:
    """Make the photo tree and the `device_photos` table agree.

    Removes directories of vanished devices, unrowed files and `.up-*` temp
    files older than `grace_seconds` (a young one may be an in-flight upload),
    symlinks, and rows whose file is missing. A `photos` directory that is
    itself a symlink is refused: nothing behind it is followed, deleted or
    reconciled. Returns integer counts only.
    """
    current = time.time() if now is None else now
    tally = _Tally()
    if _top_is_symlink(root):
        tally.refused = 1
        return tally.freeze()
    devices = _device_ids(conn)
    by_device: dict[str, set[str]] = {}
    for device_id, photo_id in fleet_db.all_photo_refs(conn):
        by_device.setdefault(device_id, set()).add(photo_id)
    for directory in _sweep_orphan_dirs(root, devices, tally):
        rows = by_device.get(os.path.basename(directory), set())
        _sweep_device_dir(directory, rows, current, grace_seconds, tally)
    _sweep_missing_rows(conn, root, tally)
    return tally.freeze()
