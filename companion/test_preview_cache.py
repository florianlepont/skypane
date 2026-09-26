"""Behaviour tests for companion/theme_preview.py's on-disk cache
(atomic writes, stale-signature pruning, a file-count bound) and for
companion/illustration_normalize.py's bounded in-memory cache.

Every fixture is `tmp_path`; no companion app server is started - these
are pure-function tests against the two cache modules directly, not an
HTTP round trip.
"""
import os
import threading

from companion import illustration_normalize, theme_preview


def _listing(directory):
    return os.listdir(directory)


def _pngs(directory):
    return [name for name in _listing(directory) if name.endswith(".png")]


def _tmp_leftovers(directory):
    return [name for name in _listing(directory) if name.endswith(".tmp")]


def test_concurrent_cold_preview_writes_one_file_no_tmp_leftover(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    barrier = threading.Barrier(2, timeout=5)
    fixed_bytes = b"fixed-preview-bytes"

    def fake_preview_png_bytes(theme_id, live_event=None):
        barrier.wait()
        return fixed_bytes

    monkeypatch.setattr(theme_preview, "preview_png_bytes", fake_preview_png_bytes)

    results = []
    errors = []

    def worker():
        try:
            results.append(theme_preview.cached_preview_bytes(state_dir, "white"))
        except Exception as exc:  # collected, never swallowed
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
        assert not t.is_alive()

    assert not errors, "worker exception(s): %r" % (errors,)
    assert results == [fixed_bytes, fixed_bytes]

    directory = theme_preview.cache_dir(state_dir)
    matching = [name for name in _pngs(directory) if name.startswith("white-sample-")]
    assert len(matching) == 1, "expected exactly one white-sample-*.png, got %r" % (matching,)
    assert _tmp_leftovers(directory) == []


def test_stale_signature_pruned_unrelated_files_kept(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    directory = theme_preview.cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)

    real_sig = theme_preview.preview_signature("white", None)
    stale_sig = "0" * 12 if real_sig != "0" * 12 else "1" * 12
    stale_name = "white-sample-%s.png" % stale_sig
    other_event_name = "white-5-%s.png" % theme_preview.preview_signature("white", 5)
    other_theme_name = "black-sample-%s.png" % theme_preview.preview_signature("black", None)

    for name in (stale_name, other_event_name, other_theme_name):
        with open(os.path.join(directory, name), "wb") as fh:
            fh.write(b"stale-or-unrelated")

    monkeypatch.setattr(theme_preview, "preview_png_bytes", lambda theme_id, live_event=None: b"new-render")
    result = theme_preview.cached_preview_bytes(state_dir, "white")

    assert result == b"new-render"
    remaining = set(_listing(directory))
    assert stale_name not in remaining, "stale same-theme-and-event file was not pruned"
    assert other_event_name in remaining, "a different live-event file was wrongly pruned"
    assert other_theme_name in remaining, "a different theme's file was wrongly pruned"
    real_path = theme_preview.cache_path(state_dir, "white")
    assert os.path.exists(real_path)


def test_cache_bound_evicts_oldest_first(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    directory = theme_preview.cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)

    prefill_count = theme_preview.THEME_PREVIEW_CACHE_MAX_FILES + 5
    prefill_names = []
    for i in range(prefill_count):
        name = "dummy-%04d.png" % i
        path = os.path.join(directory, name)
        with open(path, "wb") as fh:
            fh.write(b"dummy")
        # Strictly increasing mtimes, oldest first, one second apart so
        # filesystem mtime resolution can never tie two entries.
        os.utime(path, (1_700_000_000 + i, 1_700_000_000 + i))
        prefill_names.append(name)

    monkeypatch.setattr(theme_preview, "preview_png_bytes", lambda theme_id, live_event=None: b"new-render")
    theme_preview.cached_preview_bytes(state_dir, "white")

    remaining_pngs = _pngs(directory)
    assert len(remaining_pngs) == theme_preview.THEME_PREVIEW_CACHE_MAX_FILES

    overflow = prefill_count + 1 - theme_preview.THEME_PREVIEW_CACHE_MAX_FILES
    oldest_removed = prefill_names[:overflow]
    newest_kept = prefill_names[overflow:]
    remaining = set(remaining_pngs)
    for name in oldest_removed:
        assert name not in remaining, "expected the oldest file %r to be evicted" % (name,)
    for name in newest_kept:
        assert name in remaining, "did not expect the newer file %r to be evicted" % (name,)

    real_path = theme_preview.cache_path(state_dir, "white")
    assert os.path.basename(real_path) in remaining, "the file just written must survive its own prune"


def test_cache_hit_does_not_write_or_prune(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    directory = theme_preview.cache_dir(state_dir)
    os.makedirs(directory, exist_ok=True)

    real_path = theme_preview.cache_path(state_dir, "white")
    seeded_bytes = b"already-cached-bytes"
    with open(real_path, "wb") as fh:
        fh.write(seeded_bytes)

    # A stale file that stale-signature pruning would remove on a miss -
    # its survival is this test's proof that a hit never prunes.
    stale_sig = "0" * 12 if theme_preview.preview_signature("white", None) != "0" * 12 else "1" * 12
    stale_name = "white-sample-%s.png" % stale_sig
    with open(os.path.join(directory, stale_name), "wb") as fh:
        fh.write(b"would-be-pruned-on-a-miss")

    def fail_if_called(theme_id, live_event=None):
        raise AssertionError("preview_png_bytes() must not be called on a cache hit")

    monkeypatch.setattr(theme_preview, "preview_png_bytes", fail_if_called)
    result = theme_preview.cached_preview_bytes(state_dir, "white")

    assert result == seeded_bytes
    assert os.path.exists(os.path.join(directory, stale_name)), "a cache hit must not prune"


def test_normalized_png_cache_maxsize_is_128():
    assert illustration_normalize._cached_normalized_png_bytes.cache_info().maxsize == 128
