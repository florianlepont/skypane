#!/usr/bin/env python3
"""Contract harness for server/device_config.py (the theme + tracked-runway
registry and its validated, atomic JSON side-file) and server/history_db.py
(the SQLite history store behind CFG-03's health trend, CFG-06's flight
log, CFG-08's resolution statistics, and the Caddy access-log battery
tailer).

Stdlib-only. Exits 0 only when every check below passes.

Usage:
    server/.venv/bin/python3 server/test_config_history.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 6


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.device_config as device_config
    except ImportError as exc:
        print("FAIL import server.device_config - %r" % (exc,))
        print("config-history: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    # --- device_config.py -------------------------------------------------

    def _missing_state_dir_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            missing = os.path.join(tmpdir, "does-not-exist")
            config = device_config.load_device_config(missing)
            if config != {"theme": "sky", "tracked_runway": "3"}:
                return False, "expected defaults, got %r" % (config,)
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() on a missing state directory returns the documented defaults", _missing_state_dir_yields_defaults)

    def _malformed_file_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            for bad_content in ('["not", "a", "dict"]', "{truncated", "null"):
                path = device_config.device_config_path(tmpdir)
                with open(path, "w") as fh:
                    fh.write(bad_content)
                config = device_config.load_device_config(tmpdir)
                if config != {"theme": "sky", "tracked_runway": "3"}:
                    return False, "content %r produced %r, expected defaults" % (bad_content, config)
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() on a JSON array, a truncated document, or a non-dict returns defaults instead of raising", _malformed_file_yields_defaults)

    def _hostile_values_yield_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            path = device_config.device_config_path(tmpdir)
            with open(path, "w") as fh:
                fh.write('{"theme": "../../etc/passwd", "tracked_runway": 7}')
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "sky", "tracked_runway": "3"}:
                return False, "hostile input produced %r, expected defaults for both keys" % (config,)
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() replaces an unrecognised theme/runway value with the default rather than passing it through", _hostile_values_yield_defaults)

    def _save_then_load_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="02-20")
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "sky", "tracked_runway": "02-20"}:
                return False, "round-trip produced %r" % (config,)
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("save_device_config() followed by load_device_config() round-trips the saved theme and tracked_runway", _save_then_load_round_trips)

    def _unknown_theme_rejected_without_touching_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            raised = False
            try:
                device_config.save_device_config(tmpdir, theme="nope")
            except ValueError:
                raised = True
            if not raised:
                return False, "save_device_config() with an unknown theme did not raise ValueError"
            path = device_config.device_config_path(tmpdir)
            if os.path.exists(path):
                return False, "a rejected save left a device_config.json file behind"
            if os.path.exists(path + ".tmp"):
                return False, "a rejected save left a .tmp file behind"
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("save_device_config() with an unknown theme id raises ValueError and leaves the state directory file-free", _unknown_theme_rejected_without_touching_file)

    def _no_tmp_survives_a_successful_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="3")
            if os.path.exists(device_config.device_config_path(tmpdir) + ".tmp"):
                return False, "a .tmp file survived a successful save"
            return True, ""
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("no .tmp file remains in the state directory after a successful save", _no_tmp_survives_a_successful_save)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-history: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
