"""deploy/tests/conftest.py — fake-root fixtures for deploy/activate.sh and
deploy/deploy.sh (SEC-05, Plan 37-06). See 37-RESEARCH.md "Pattern:
fake-root shell testing": activate.sh reads every system path from an
overridable variable, so a tmp tree plus PATH-stubbed systemctl/curl/
caddy/runuser/journalctl/chown lets the whole atomic-swap/probe/rollback
flow run as a subprocess against fake state, with no VPS and no root.

Does not import or extend the repo-root conftest.py's fixtures (socket
guard, fake_providers) — those exist for server/companion HTTP tests, not
for exercising shell scripts as subprocesses, and none of the fixture
names below shadow them.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEPLOY_DIR = _REPO_ROOT / "deploy"

HOST_CADDYFILE = (
    "# host Caddyfile shared with another project\n"
    "cortege.example.net {\n"
    "    reverse_proxy 127.0.0.1:9000\n"
    "}\n"
    "\n"
    "import sites/*.caddy\n"
)


def _write_fake_smoke_script(path):
    """A minimal stand-in for companion/app.py, server/poll_loop.py and
    stub-server/byos_server.py inside a fake release: it only needs to
    accept `--help` (activate.sh's smoke check) and exit
    FAKE_SMOKE_RC (default 0) — the real files' own import-time
    dependencies are irrelevant to activate.sh's swap/probe logic, which
    is all this fixture set exists to exercise.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        'if "--help" in sys.argv[1:]:\n'
        '    sys.exit(int(os.environ.get("FAKE_SMOKE_RC", "0")))\n'
        "sys.exit(0)\n"
    )
    path.chmod(0o755)


def _write_stub(bindir, name, log_path, body):
    """Write an executable Python stub at bindir/name. Stubs are written
    in Python (not POSIX sh) so the same script logic can parse argv,
    env vars and URLs precisely — the shebang line is all that matters
    to whatever shell execs it, so this works equally under /bin/sh and
    bash.
    """
    script = bindir / name
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n"
        f"_LOG = {str(log_path)!r}\n"
        "_args = sys.argv[1:]\n"
        f"with open(_LOG, 'a') as _f:\n"
        f"    _f.write({name!r} + ' ' + ' '.join(_args) + chr(10))\n"
        + body
    )
    script.chmod(0o755)


@pytest.fixture
def fake_root(tmp_path):
    """A tmp tree standing in for the VPS filesystem, with every path
    deploy/activate.sh accepts as an override variable pre-created.
    """
    root = tmp_path / "root"
    skypane_root = root / "opt" / "skypane"
    releases = skypane_root / "releases"
    state_dir = skypane_root / "state"
    venv_dir = skypane_root / "venv"
    (venv_dir / "bin").mkdir(parents=True)
    releases.mkdir(parents=True)
    state_dir.mkdir(parents=True)

    unit_dir = root / "etc" / "systemd" / "system"
    unit_dir.mkdir(parents=True)

    caddy_dir = root / "etc" / "caddy"
    caddy_dir.mkdir(parents=True)
    caddyfile = caddy_dir / "Caddyfile"
    # The host Caddyfile is shared with another project on the real VPS:
    # an unrelated site block plus the one import line SkyPane relies on.
    # activate.sh must never write it, so tests compare it byte for byte
    # against this exact content.
    caddyfile.write_text(HOST_CADDYFILE)
    sites_dir = caddy_dir / "sites"
    sites_dir.mkdir()

    backup_gate_dir = root / "usr" / "local" / "lib" / "skypane"
    backup_gate_dir.mkdir(parents=True)

    backup_root = root / "var" / "lib" / "skypane-backup"
    (backup_root / "archives").mkdir(parents=True)
    (backup_root / "pulled").mkdir(parents=True)

    # venv/bin/python3 -> the real interpreter running pytest, so
    # `python3 -m compileall` and the fake release's `--help` smoke
    # scripts execute for real.
    python3 = venv_dir / "bin" / "python3"
    python3.symlink_to(sys.executable)

    call_log = root / "call.log"
    call_log.write_text("")

    # pip stub: logs the call and exits 0. activate.sh decides whether to
    # call it at all (hash comparison); this stub never touches a network
    # or a real venv.
    pip_stub = venv_dir / "bin" / "pip"
    pip_stub.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        f"_LOG = {str(call_log)!r}\n"
        "with open(_LOG, 'a') as f:\n"
        "    f.write('pip ' + ' '.join(sys.argv[1:]) + chr(10))\n"
        "sys.exit(0)\n"
    )
    pip_stub.chmod(0o755)

    pwned_marker = root / "pwned"
    env_file = skypane_root / "skypane.env"
    # The poison line proves activate.sh parses this file with a strict
    # line regex and never `source`s or `.`s it as root — if it were
    # sourced, `$(touch ...)` would run and create pwned_marker.
    env_file.write_text(
        "SKYPANE_PUBLIC_HOST=pub.example.org\n"
        "SKYPANE_COMPANION_HOST=cfg.example.org\n"
        "SKYPANE_BYOS_PORT=8642\n"
        "SKYPANE_COMPANION_PORT=8643\n"
        f"X=$(touch {pwned_marker})\n"
    )
    env_file.chmod(0o600)

    return SimpleNamespace(
        path=root,
        skypane_root=skypane_root,
        releases=releases,
        state_dir=state_dir,
        venv_dir=venv_dir,
        unit_dir=unit_dir,
        caddy_dir=caddy_dir,
        caddyfile=caddyfile,
        host_caddyfile_text=HOST_CADDYFILE,
        sites_dir=sites_dir,
        site_file=sites_dir / "skypane.caddy",
        site_file_prev=sites_dir / ".skypane.caddy.prev",
        backup_gate_dir=backup_gate_dir,
        backup_root=backup_root,
        env_file=env_file,
        pwned_marker=pwned_marker,
        call_log=call_log,
        current_link=skypane_root / "current",
    )


@pytest.fixture
def stub_bin(fake_root, tmp_path):
    """A tmp bin dir, meant to be prepended to PATH (never replacing it —
    activate.sh also needs real install/mv/ln/sed/tar/readlink/cmp),
    holding scripted stand-ins for the six commands whose real behaviour
    either needs root or would touch a real system: systemctl, curl,
    caddy, runuser, journalctl, chown.
    """
    bindir = tmp_path / "stubbin"
    bindir.mkdir()
    log = fake_root.call_log

    _write_stub(
        bindir,
        "systemctl",
        log,
        "if _args and _args[0] == 'is-active':\n"
        "    _inactive = set(os.environ.get('FAKE_INACTIVE', '').split())\n"
        "    _units = [a for a in _args[1:] if not a.startswith('-')]\n"
        "    sys.exit(1 if any(u in _inactive for u in _units) else 0)\n"
        "sys.exit(0)\n",
    )

    _write_stub(
        bindir,
        "curl",
        log,
        "from urllib.parse import urlsplit\n"
        "_url = None\n"
        "_dump_headers = False\n"
        "for _j, _a in enumerate(_args):\n"
        "    if _a.startswith('http://') or _a.startswith('https://'):\n"
        "        _url = _a\n"
        "    if _a == '-D' and _j + 1 < len(_args) and _args[_j + 1] == '-':\n"
        "        _dump_headers = True\n"
        "if _url is None:\n"
        "    sys.exit(0)\n"
        "_path = urlsplit(_url).path.rstrip('/')\n"
        "if _path.endswith('/display'):\n"
        "    _key, _default = 'byos_display', '401'\n"
        "elif _path.endswith('/login'):\n"
        "    _key, _default = 'companion_login', '200'\n"
        "else:\n"
        "    _key, _default = 'unknown_other', '200'\n"
        "_codes = {}\n"
        "for _pair in os.environ.get('FAKE_HTTP_CODES', '').replace(',', ' ').split():\n"
        "    if '=' in _pair:\n"
        "        _k, _v = _pair.split('=', 1)\n"
        "        _codes[_k] = _v\n"
        "_status = _codes.get(_key, _default)\n"
        "_out = ''\n"
        "if _dump_headers:\n"
        "    _out += 'HTTP/1.1 ' + _status + ' STUB\\r\\n'\n"
        "    if os.environ.get('FAKE_NO_HSTS') != '1':\n"
        "        _out += 'Strict-Transport-Security: max-age=31536000\\r\\n'\n"
        "    _out += '\\r\\n'\n"
        "_out += _status\n"
        "sys.stdout.write(_out)\n"
        "sys.exit(0)\n",
    )

    _write_stub(
        bindir,
        "caddy",
        log,
        "sys.exit(int(os.environ.get('FAKE_CADDY_RC', '0')))\n",
    )

    _write_stub(
        bindir,
        "runuser",
        log,
        "_rest = _args[_args.index('--') + 1:] if '--' in _args else _args\n"
        "if _rest:\n"
        "    os.execvp(_rest[0], _rest)\n"
        "sys.exit(0)\n",
    )

    _write_stub(
        bindir,
        "journalctl",
        log,
        "print('-- no journal entries (stub) --')\n"
        "sys.exit(0)\n",
    )

    _write_stub(
        bindir,
        "chown",
        log,
        "sys.exit(0)\n",
    )

    return bindir


@pytest.fixture
def fake_release(fake_root):
    """Factory fixture: fake_release(sha) -> Path to a populated
    releases/.incoming-<sha> directory, built from the *real* deploy/
    tree (so render_caddyfile.sh, the real units and backup_gate.py are
    exercised) plus minimal stand-ins for the three services and their
    requirements file, matching Phase 32's server/requirements.txt name
    (no TST-08 rename found in this checkout — re-verified before this
    plan's Task 1).
    """

    def _make(sha):
        incoming = fake_root.releases / f".incoming-{sha}"
        if incoming.exists():
            shutil.rmtree(incoming)
        shutil.copytree(
            _DEPLOY_DIR,
            incoming / "deploy",
            ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
        )
        _write_fake_smoke_script(incoming / "server" / "poll_loop.py")
        _write_fake_smoke_script(incoming / "companion" / "app.py")
        _write_fake_smoke_script(incoming / "stub-server" / "byos_server.py")
        (incoming / "server" / "requirements.txt").write_text("stubpkg==1.0.0\n")
        (incoming / "adsb-test").mkdir(parents=True, exist_ok=True)
        (incoming / "adsb-test" / "runway3.json").write_text("{}\n")
        return incoming

    return _make


@pytest.fixture
def run_activate(fake_root, stub_bin):
    """Factory fixture: run_activate(sha, incoming=None, **overrides) runs
    deploy/activate.sh as a real subprocess with every override variable
    pointed into fake_root, PATH prefixed with stub_bin (real commands —
    install/mv/ln/sed/tar/readlink/cmp/rm — stay reachable behind the
    stubs), and SKYPANE_ACTIVATE_ALLOW_NONROOT=1 so it runs unprivileged
    in CI. Returns the subprocess.CompletedProcess.
    """
    activate_sh = _DEPLOY_DIR / "activate.sh"

    def _run(sha, incoming=None, **overrides):
        incoming_dir = incoming or (fake_root.releases / f".incoming-{sha}")
        env = dict(os.environ)
        env["PATH"] = str(stub_bin) + os.pathsep + env.get("PATH", "")
        env.update(
            {
                "SKYPANE_ROOT": str(fake_root.skypane_root),
                "VENV": str(fake_root.venv_dir),
                "ENV_FILE": str(fake_root.env_file),
                "SYSTEMD_UNIT_DIR": str(fake_root.unit_dir),
                "CADDYFILE": str(fake_root.caddyfile),
                "CADDY_SITES_DIR": str(fake_root.sites_dir),
                "BACKUP_GATE_DIR": str(fake_root.backup_gate_dir),
                "BACKUP_ROOT": str(fake_root.backup_root),
                "KEEP_RELEASES": "5",
                "PROBE_TIMEOUT_S": "5",
                "SKYPANE_ACTIVATE_ALLOW_NONROOT": "1",
            }
        )
        env.update({k: str(v) for k, v in overrides.items()})
        return subprocess.run(
            ["bash", str(activate_sh), sha, str(incoming_dir)],
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )

    return _run
