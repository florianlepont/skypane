#!/usr/bin/env python3
"""Merge the per-frame artwork directories into the fleet artwork directory.

Uploaded artwork used to live in each frame's own
`illustration_overrides/` directory. It now lives once, at the fleet root
(`<root>/illustration_overrides/<key>.png`, the live frame's directory). This
module folds every other frame's pictures into that directory. It is run by
`server.fleet_migrate` at deploy time and never at service start; renders
and page loads never write.

Invariants:
- Per-frame image directories are read, never written, renamed or deleted:
  a rollback to the release that still reads them loses nothing.
- A candidate is merged only when it is a regular file (never a symlink),
  named `<key>.png` with a key that the override path guard accepts, no
  larger than the upload cap, and accepted by
  `illustrations.validate_illustration_file` (PNG, dimensions, pixel cap,
  read from the header only). Anything else is skipped and reported, never
  merged and never deleted. Dot-files and `*.tmp` leftovers are ignored.
- A symlinked image directory, a symlinked or oddly named `devices/<id>`
  and a symlinked fleet directory are skipped and reported.
- Conflict rule per file name: when the fleet directory and one or more
  frames hold different bytes, the file with the latest modification time
  wins; a tie goes to the fleet file, then to the lowest device id. Copies
  keep the source's modification time, so the order is stable across runs.
  Identical bytes are not a conflict.
- Losers are never lost: every losing file (a replaced fleet file included)
  is first copied, with its modification time, under
  `illustration_conflicts/<device id or live>/`, never over an earlier
  archive of different bytes.
- At most `MAX_MERGED_FILES` files and `MAX_MERGED_BYTES` bytes are copied
  into the fleet directory in one run, latest modification time first; the
  rest stay pending for a later run.
- A marker in the root records the SHA-256 of every source already merged:
  an unchanged source is not merged again (so a picture removed fleet-wide
  since is not brought back) and a changed one is merged once more. The
  marker is written last; a write failure raises `OSError`.
- Output names counts, file names (airline keys), device ids, sizes and
  times only; never image content.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from server import atomic_io
from server.plane import fleet_registries, illustrations
from server.plane.fleet_registries import _merged_hashes

MARKER_FILENAME = "illustration_migration.json"
CONFLICTS_DIRNAME = "illustration_conflicts"
LIVE_LABEL = fleet_registries.LIVE_LABEL

# Equal to the companion upload cap (`companion.upload_form.MAX_UPLOAD_BYTES`);
# `server/` must not import `companion/`, a test keeps the two equal.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_MERGED_FILES = 1000
MAX_MERGED_BYTES = 256 * 1024 * 1024
MAX_SCANNED_PER_DIR = 5000
MAX_RECORDED_CONFLICTS = 50
MAX_ARCHIVE_SUFFIX = 1000

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.png$")
_REPORT = "artwork: "


@dataclass
class Cand:
    """One image file seen on one frame (`LIVE_LABEL` for the fleet directory)."""

    frame: str
    name: str
    path: str
    size: int
    mtime_ns: int
    atime_ns: int
    sha: str


@dataclass
class Op:
    """What one file name needs: the winner, whether it is copied, the losers
    to archive and the device sources this decision settles."""

    name: str
    winner: Cand
    root: Cand | None
    copy: bool
    losers: list[Cand] = field(default_factory=list)
    settled: list[Cand] = field(default_factory=list)


@dataclass
class ArtworkPlan:
    """What a merge would do, computed without writing anything."""

    root: str
    ops: list[Op] = field(default_factory=list)
    seen: int = 0
    pending: int = 0
    identical: int = 0
    new: int = 0
    replaced: int = 0
    conflicts: int = 0
    frames: int = 0
    details: list[str] = field(default_factory=list)
    marker: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_write(self) -> bool:
        return bool(self.marker)

    @property
    def fleet_dir(self) -> str:
        return os.path.join(self.root, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)


def _stamp(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, timezone.utc).isoformat(timespec="seconds")


def _describe(cand: Cand) -> str:
    return "[frame %s, %s, %d bytes]" % (cand.frame, _stamp(cand.mtime_ns), cand.size)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_marker(root: str) -> dict[str, Any]:
    try:
        with open(os.path.join(root, MARKER_FILENAME), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _candidate_problem(root: str, name: str, info: os.stat_result, path: str) -> str:
    """Why a regular, well-named file may not be merged, or `""`."""
    if not _NAME_RE.match(name):
        return "not a lowercase <key>.png name"
    if illustrations.override_path_for_key(name[:-4], root) is None:
        return "unsafe key"
    if info.st_size > MAX_UPLOAD_BYTES:
        return "over the %d-byte upload cap" % MAX_UPLOAD_BYTES
    problems = illustrations.validate_illustration_file(path)
    if problems:
        return "not a valid illustration: %s" % problems[0].split(":")[0][:80]
    return ""


def _entry_info(path: str) -> tuple[os.stat_result | None, str]:
    try:
        info = os.lstat(path)
    except OSError:
        return None, "unreadable"
    if stat.S_ISLNK(info.st_mode):
        return None, "symlink"
    if not stat.S_ISREG(info.st_mode):
        return None, "not a regular file"
    return info, ""


def _make_cand(frame: str, name: str, path: str, info: os.stat_result) -> Cand:
    return Cand(frame, name, path, info.st_size, info.st_mtime_ns, info.st_atime_ns, _sha256(path))


def _frame_image_dir(frame: str, directory: str, plan: ArtworkPlan) -> str | None:
    """The frame's image directory when it is a real directory, else `None`
    (a symlink is reported)."""
    path = os.path.join(directory, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME)
    try:
        info = os.lstat(path)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode):
        plan.details.append("skipped %s of frame %s: symlink" % (
            illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, frame))
        return None
    return path if stat.S_ISDIR(info.st_mode) else None


def _scan_frame(root: str, frame: str, directory: str, merged: dict[str, str],
                plan: ArtworkPlan) -> list[Cand]:
    """The valid pictures of one frame not yet merged at their current hash."""
    image_dir = _frame_image_dir(frame, directory, plan)
    if image_dir is None:
        return []
    try:
        with os.scandir(image_dir) as it:
            names = sorted(entry.name for _i, entry in zip(range(MAX_SCANNED_PER_DIR + 1), it))
    except OSError:
        plan.details.append("skipped %s of frame %s: unreadable" % (
            illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, frame))
        return []
    if len(names) > MAX_SCANNED_PER_DIR:
        names = names[:MAX_SCANNED_PER_DIR]
        plan.details.append("skipped frame %s beyond the first %d entries" % (frame, MAX_SCANNED_PER_DIR))
    pending: list[Cand] = []
    for name in names:
        path = os.path.join(image_dir, name)
        plan.seen += 1
        if name.startswith(".") or name.endswith(".tmp"):
            plan.details.append("skipped %s of frame %s: temporary or hidden file" % (name, frame))
            continue
        info, reason = _entry_info(path)
        if info is not None:
            reason = _candidate_problem(root, name, info, path)
        if info is None or reason:
            plan.details.append("skipped %s of frame %s: %s" % (name, frame, reason))
            continue
        cand = _make_cand(frame, name, path, info)
        if merged.get("%s/%s" % (frame, name)) != cand.sha:
            pending.append(cand)
    return pending


def _root_candidate(plan: ArtworkPlan, name: str) -> tuple[Cand | None, bool]:
    """`(fleet file or None, usable)`; unusable when the path exists but is
    not a plain regular file (it is then never replaced)."""
    path = os.path.join(plan.fleet_dir, name)
    if not os.path.lexists(path):
        return None, True
    info, reason = _entry_info(path)
    if info is None:
        plan.details.append("skipped %s: the fleet file is %s, left as is" % (name, reason))
        return None, False
    return _make_cand(LIVE_LABEL, name, path, info), True


def _rank(cand: Cand) -> tuple[int, int, str]:
    """Sort key: the first candidate in ascending order wins."""
    return (-cand.mtime_ns, 0 if cand.frame == LIVE_LABEL else 1, cand.frame)


def _decide(plan: ArtworkPlan, name: str, cands: list[Cand]) -> Op | None:
    root_cand, usable = _root_candidate(plan, name)
    if not usable:
        return None
    pool = ([root_cand] if root_cand else []) + cands
    ranked = sorted(pool, key=_rank)
    winner = ranked[0]
    losers: list[Cand] = []
    seen_shas = {winner.sha}
    for cand in ranked[1:]:
        if cand.sha in seen_shas:
            continue
        seen_shas.add(cand.sha)
        losers.append(cand)
    op = Op(name, winner, root_cand, winner.frame != LIVE_LABEL and (
        root_cand is None or root_cand.sha != winner.sha), losers, list(cands))
    for loser in losers:
        plan.details.append("conflict %s: keep %s over %s" % (name, _describe(winner), _describe(loser)))
    plan.conflicts += len(losers)
    return op


def _apply_caps(plan: ArtworkPlan, ops: list[Op]) -> list[Op]:
    """Keep the ops that fit the per-run caps, latest winner first."""
    ordered = sorted(ops, key=lambda o: (-o.winner.mtime_ns, o.name))
    kept: list[Op] = []
    files = total = 0
    deferred = 0
    for op in ordered:
        if op.copy:
            if files + 1 > MAX_MERGED_FILES or total + op.winner.size > MAX_MERGED_BYTES:
                deferred += 1
                continue
            files += 1
            total += op.winner.size
        kept.append(op)
    if deferred:
        plan.details.append(
            "not merged: %d file(s) beyond the per-run cap of %d files or %d bytes, they stay pending" % (
                deferred, MAX_MERGED_FILES, MAX_MERGED_BYTES))
    return kept


def plan_merge(root: str) -> ArtworkPlan:
    """Read the fleet directory, the marker and every frame's pictures and
    compute the merge. Writes nothing."""
    plan = ArtworkPlan(root)
    fleet_dir = plan.fleet_dir
    if os.path.islink(fleet_dir):
        plan.details.append("skipped %s: the fleet directory is a symlink" % (
            illustrations.ILLUSTRATION_OVERRIDE_DIRNAME))
        return plan
    marker = _read_marker(root)
    merged = _merged_hashes(marker)
    by_name: dict[str, list[Cand]] = {}
    frames = fleet_registries.frame_state_dirs(root)[1:]
    plan.frames = len(frames)
    for frame, directory in frames:
        for cand in _scan_frame(root, frame, directory, merged, plan):
            by_name.setdefault(cand.name, []).append(cand)
    ops: list[Op] = []
    for name in sorted(by_name):
        op = _decide(plan, name, by_name[name])
        if op is not None:
            ops.append(op)
    plan.ops = _apply_caps(plan, ops)
    plan.pending = sum(len(op.settled) for op in plan.ops)
    for op in plan.ops:
        if op.copy:
            if op.root is None:
                plan.new += 1
            else:
                plan.replaced += 1
        else:
            plan.identical += len(op.settled)
    if plan.pending:
        plan.marker = _next_marker(marker, merged, plan)
    return plan


def _next_marker(marker: dict[str, Any], merged: dict[str, str], plan: ArtworkPlan) -> dict[str, Any]:
    hashes = dict(merged)
    recorded = marker.get("conflicts")
    conflicts: list[dict[str, str]] = list(recorded) if isinstance(recorded, list) else []
    for op in plan.ops:
        for cand in op.settled:
            hashes["%s/%s" % (cand.frame, cand.name)] = cand.sha
        for loser in op.losers:
            if len(conflicts) < MAX_RECORDED_CONFLICTS:
                conflicts.append({
                    "name": op.name, "kept_frame": op.winner.frame, "kept": op.winner.sha,
                    "lost_frame": loser.frame, "lost": loser.sha})
    return {"merged": dict(sorted(hashes.items())), "conflicts": conflicts[:MAX_RECORDED_CONFLICTS]}


def report_lines(plan: ArtworkPlan, dry_run: bool) -> list[str]:
    """Human-readable lines; empty on an install with no per-frame pictures."""
    if not plan.seen and not plan.details:
        return []
    if not plan.pending:
        return [_REPORT + "nothing to do"] + [_REPORT + d for d in plan.details]
    verb = "would merge" if dry_run else "merged"
    lines = [
        "%s%s %d picture(s) from %d frame(s) into the fleet directory: %d new, %d replaced, "
        "%d identical, %d conflict(s)" % (
            _REPORT, verb, plan.pending, plan.frames, plan.new, plan.replaced,
            plan.identical, plan.conflicts)]
    lines.extend(_REPORT + d for d in plan.details)
    return lines


def _archive_target(root: str, frame: str, name: str, sha: str) -> str | None:
    """Where a loser goes, or `None` when the same bytes are archived already."""
    folder = os.path.join(root, CONFLICTS_DIRNAME, frame)
    for n in range(MAX_ARCHIVE_SUFFIX):
        candidate = os.path.join(folder, name if n == 0 else "%s.%d.png" % (name[:-4], n))
        if not os.path.lexists(candidate):
            return candidate
        if os.path.isfile(candidate) and not os.path.islink(candidate) and _sha256(candidate) == sha:
            return None
    raise OSError("too many archived versions of %s" % name)


def _copy_verified(src: Cand, dest: str) -> None:
    """Copy `src` to `dest` atomically when the file still has the planned
    bytes, then give the copy the source's times."""
    info, _reason = _entry_info(src.path)
    if info is None or _sha256(src.path) != src.sha:
        raise OSError("%s changed during the merge" % src.name)
    with open(src.path, "rb") as fh:
        data = fh.read(MAX_UPLOAD_BYTES + 1)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.islink(os.path.dirname(dest)):
        raise OSError("refusing to write through a symlinked directory")
    atomic_io.atomic_write(dest, data)
    os.utime(dest, ns=(src.atime_ns, src.mtime_ns))


def _apply_op(root: str, op: Op) -> None:
    for loser in op.losers:
        target = _archive_target(root, loser.frame, op.name, loser.sha)
        if target is not None:
            _copy_verified(loser, target)
    if op.copy:
        _copy_verified(op.winner, os.path.join(root, illustrations.ILLUSTRATION_OVERRIDE_DIRNAME, op.name))


def apply_merge(root: str, plan: ArtworkPlan, now: str | None = None) -> list[str]:
    """Archive the losers, copy the winners, then write the marker; returns
    the report lines. Never opens a per-frame file for writing. Raises
    `OSError` when a write fails."""
    for op in plan.ops:
        _apply_op(root, op)
    if plan.needs_write:
        stamp = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        atomic_io.atomic_write(
            os.path.join(root, MARKER_FILENAME),
            json.dumps(dict(plan.marker, merged_at=stamp), indent=1))
    return report_lines(plan, dry_run=False)

