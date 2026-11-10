"""The photo render path stays separate from the plane renderer and the
companion; checked by importing fresh in a child interpreter."""
import json
import subprocess
import sys

from skypane_test_support import REPO_ROOT, child_env


def _unloaded_after_importing(module):
    script = (
        "import json, sys\n"
        "import %s\n"
        "print(json.dumps([m for m in ('server.plane.render', 'companion')"
        " if m in sys.modules]))\n"
    ) % module
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_photo_render_import_leaves_plane_render_and_companion_unloaded():
    assert _unloaded_after_importing("server.photo.render") == []


def test_photo_store_import_leaves_plane_render_and_companion_unloaded():
    assert _unloaded_after_importing("server.photo_store") == []
