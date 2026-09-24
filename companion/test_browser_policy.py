"""Self-tests proving TST-11's missing-browser policy and loopback-only
browser guard (33-02-PLAN.md Task 3): a missing/unlaunchable Chromium
fails in CI / SKYPANE_REQUIRE_BROWSER=1 and is a visible skip locally, and
a browser context can never reach a non-loopback host.
"""
import os
import subprocess
import sys
import textwrap

import pytest

from skypane_test_support import REPO_ROOT, child_env

pytestmark = pytest.mark.browser


def test_page_opens_login_and_reads_password_field(page, app_server):
    """With a launchable Chromium, a @pytest.mark.browser test using
    `page` opens app_server's /login and reads its <title> or the
    password field.
    """
    page.goto(app_server.base_url() + "/login")
    assert "password" in page.content().lower()


def test_non_loopback_navigation_is_blocked_and_recorded(page, blocked_requests):
    """page.goto("http://example.invalid/") inside a test is aborted by
    the guard (raises a Playwright Error), and the blocked_requests list
    contains that URL.
    """
    from playwright.sync_api import Error as PlaywrightError

    with pytest.raises(PlaywrightError):
        page.goto("http://example.invalid/")
    assert any("example.invalid" in url for url in blocked_requests)
    blocked_requests.clear()


def test_non_loopback_navigation_blocked_in_extra_viewport_context(
        new_context, blocked_requests):
    """The same holds for a context made with
    new_context(viewport={"width": 360, "height": 844}).
    """
    from playwright.sync_api import Error as PlaywrightError

    ctx = new_context(viewport={"width": 360, "height": 844})
    page = ctx.new_page()
    with pytest.raises(PlaywrightError):
        page.goto("http://example.invalid/")
    assert any("example.invalid" in url for url in blocked_requests)
    blocked_requests.clear()
    ctx.close()


_PROBE_PYTEST_INI = "[pytest]\n"
_PROBE_CONFTEST = 'pytest_plugins = ["companion.conftest"]\n'
_PROBE_TEST = textwrap.dedent("""\
    import pytest

    @pytest.mark.browser
    def test_probe(page):
        pass
    """)


def _run_probe(tmp_path, *, require_browser):
    """Run a tiny standalone pytest project (pytest.ini + conftest.py +
    test_probe.py, all under tmp_path) that loads companion.conftest's
    real `browser` override, with PLAYWRIGHT_BROWSERS_PATH pointed at an
    empty directory so Chromium cannot launch. Returns (returncode,
    combined stdout+stderr).
    """
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    (probe_dir / "pytest.ini").write_text(_PROBE_PYTEST_INI)
    (probe_dir / "conftest.py").write_text(_PROBE_CONFTEST)
    (probe_dir / "test_probe.py").write_text(_PROBE_TEST)

    empty_browsers_dir = tmp_path / "empty-browsers"
    empty_browsers_dir.mkdir()

    env = child_env(dict(os.environ))
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        [REPO_ROOT] + ([existing_pythonpath] if existing_pythonpath else []))
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(empty_browsers_dir)
    if require_browser:
        env["CI"] = "true"
    else:
        env.pop("CI", None)
        env.pop("SKYPANE_REQUIRE_BROWSER", None)

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rs",
         str(probe_dir)],
        cwd=str(probe_dir), env=env, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout + proc.stderr


@pytest.mark.slow
def test_missing_browser_fails_in_ci(tmp_path):
    """In a subprocess pytest run over a tiny browser test, with
    PLAYWRIGHT_BROWSERS_PATH pointing at an empty tmp dir and CI=true,
    rc != 0 and the output contains "could not launch".
    """
    rc, output = _run_probe(tmp_path, require_browser=True)
    assert rc != 0
    assert "could not launch" in output


@pytest.mark.slow
def test_missing_browser_skips_locally(tmp_path):
    """With CI and SKYPANE_REQUIRE_BROWSER removed, rc == 0 and the
    output reports 1 skipped whose reason contains "could not launch".
    """
    rc, output = _run_probe(tmp_path, require_browser=False)
    assert rc == 0
    assert "1 skipped" in output
    assert "could not launch" in output
