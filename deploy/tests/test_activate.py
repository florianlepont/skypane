"""deploy/tests/test_activate.py -- deploy/activate.sh. Runs it as a real
bash subprocess against the fake-root fixtures in conftest.py
(systemctl/curl/caddy/runuser/journalctl/chown stubs on PATH), so the
atomic swap, verification probes, and automatic
rollback are exercised end to end with no VPS and no root. One test per
behavior line in the PLAN's <behavior> block, plus the shared-host
Caddy layout: SkyPane only ever writes its own site file under
/etc/caddy/sites/, never the host Caddyfile.
"""
import hashlib
import os
import shutil
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _sites_dir_names(fake_root):
    return {p.name for p in fake_root.sites_dir.iterdir()}


def _companion_unit_path(release_dir):
    return release_dir / "deploy" / "skypane-companion.service"


def _mark_release(release_dir, marker):
    """Append a unique comment to one unit file so two releases built
    from the same working tree are byte-distinguishable — needed to
    prove a rollback restores the *previous* release's unit file rather
    than coincidentally matching identical content.
    """
    with _companion_unit_path(release_dir).open("a") as f:
        f.write(f"\n# release-marker: {marker}\n")


def test_first_deploy_no_current(fake_root, fake_release, run_activate):
    fake_release("aaaaaaa")
    result = run_activate("aaaaaaa")
    assert result.returncode == 0, result.stderr

    assert fake_root.current_link.is_symlink()
    assert os.readlink(fake_root.current_link) == "releases/aaaaaaa"
    assert (fake_root.unit_dir / "skypane-companion.service").exists()

    log = fake_root.call_log.read_text()
    reload_idx = log.index("systemctl daemon-reload")
    restart_idx = log.index("systemctl restart skypane-byos.service")
    assert reload_idx < restart_idx, "daemon-reload must precede the first restart"

    site_text = fake_root.site_file.read_text()
    assert "pub.example.org {" in site_text
    assert "cfg.example.org {" in site_text
    assert "Strict-Transport-Security" in site_text
    assert (fake_root.site_file.stat().st_mode & 0o777) == 0o644
    assert fake_root.caddyfile.read_text() == fake_root.host_caddyfile_text

    assert (fake_root.backup_gate_dir / "backup_gate.py").exists()
    assert any(
        line.startswith("systemctl enable") and "skypane-backup.timer" in line
        for line in log.splitlines()
    )

    assert not fake_root.pwned_marker.exists()


def test_second_deploy_keeps_previous_release(fake_root, fake_release, run_activate):
    fake_release("1111111")
    r1 = run_activate("1111111")
    assert r1.returncode == 0, r1.stderr

    fake_release("2222222")
    r2 = run_activate("2222222")
    assert r2.returncode == 0, r2.stderr

    assert (fake_root.releases / "1111111").is_dir()
    assert os.readlink(fake_root.current_link) == "releases/2222222"


def test_rollback_on_inactive_unit(fake_root, fake_release, run_activate):
    rel1 = fake_release("3333333")
    _mark_release(rel1, "3333333")
    r1 = run_activate("3333333")
    assert r1.returncode == 0, r1.stderr

    rel2 = fake_release("4444444")
    _mark_release(rel2, "4444444")
    r2 = run_activate(
        "4444444", FAKE_INACTIVE="skypane-companion.service", PROBE_TIMEOUT_S="1"
    )
    assert r2.returncode != 0

    assert os.readlink(fake_root.current_link) == "releases/3333333"

    installed = (fake_root.unit_dir / "skypane-companion.service").read_text()
    assert "release-marker: 3333333" in installed
    assert "release-marker: 4444444" not in installed

    log = fake_root.call_log.read_text()
    assert any(
        line.startswith("journalctl") and "skypane-companion.service" in line
        for line in log.splitlines()
    )
    assert "unit:skypane-companion.service" in r2.stderr


def test_rollback_on_http_probe_failure_and_missing_hsts(fake_root, fake_release, run_activate):
    fake_release("5555555")
    assert run_activate("5555555").returncode == 0

    fake_release("6666666")
    r_http = run_activate(
        "6666666", FAKE_HTTP_CODES="companion_login=502", PROBE_TIMEOUT_S="1"
    )
    assert r_http.returncode != 0
    assert os.readlink(fake_root.current_link) == "releases/5555555"

    fake_release("7777777")
    r_hsts = run_activate("7777777", FAKE_NO_HSTS="1", PROBE_TIMEOUT_S="1")
    assert r_hsts.returncode != 0
    assert os.readlink(fake_root.current_link) == "releases/5555555"


def test_caddy_validate_failure_blocks_swap(fake_root, fake_release, run_activate):
    fake_release("8888888")
    r = run_activate("8888888", FAKE_CADDY_RC="1")
    assert r.returncode != 0
    assert not fake_root.current_link.exists()
    assert fake_root.caddyfile.read_text() == fake_root.host_caddyfile_text
    # No site file existed before, so the rejected one is removed, not kept.
    assert not fake_root.site_file.exists()
    assert _sites_dir_names(fake_root) <= {".skypane.caddy.prev"}
    assert "systemctl reload caddy" not in fake_root.call_log.read_text()


def test_smoke_check_failure_blocks_swap(fake_root, fake_release, run_activate):
    fake_release("9999999")
    r = run_activate("9999999", FAKE_SMOKE_RC="1")
    assert r.returncode != 0
    assert not fake_root.current_link.exists()


def test_failure_with_no_previous_release(fake_root, fake_release, run_activate):
    fake_release("aaaaaa1")
    r = run_activate(
        "aaaaaa1", FAKE_INACTIVE="skypane-companion.service", PROBE_TIMEOUT_S="1"
    )
    assert r.returncode != 0
    assert "no previous release" in r.stderr
    # The swap already happened before probing -- with no earlier release
    # to fall back to, there is nothing to swap back to, so `current`
    # legitimately still points at this first, failing release.
    assert os.readlink(fake_root.current_link) == "releases/aaaaaa1"


def test_prune_keeps_current_and_previous_and_removes_stale_incoming(
    fake_root, fake_release, run_activate
):
    fake_release("eee0001")
    assert run_activate("eee0001").returncode == 0

    old_shas = [f"dead00{i}" for i in range(7)]
    for i, sha in enumerate(old_shas):
        d = fake_root.releases / sha
        d.mkdir()
        (d / "marker").write_text(sha)
        ts = time.time() - (100 - i)
        os.utime(d, (ts, ts))

    stale_incoming = fake_root.releases / ".incoming-stalestale"
    stale_incoming.mkdir()

    fake_release("cafe001")
    r = run_activate("cafe001", KEEP_RELEASES="5")
    assert r.returncode == 0, r.stderr

    remaining = {
        p.name
        for p in fake_root.releases.iterdir()
        if p.is_dir() and not p.name.startswith(".incoming-")
    }
    assert len(remaining) == 5
    assert "cafe001" in remaining
    assert "eee0001" in remaining
    assert not stale_incoming.exists()


def test_redeploy_same_sha_restarts_and_probes_only(fake_root, fake_release, run_activate):
    fake_release("beef001")
    r1 = run_activate("beef001")
    assert r1.returncode == 0, r1.stderr

    log_before = fake_root.call_log.read_text()

    fake_release("beef001")
    r2 = run_activate("beef001")
    assert r2.returncode == 0, r2.stderr

    new_log = fake_root.call_log.read_text()[len(log_before):]
    assert "systemctl daemon-reload" not in new_log
    assert "systemctl enable" not in new_log
    assert "systemctl restart skypane-byos.service" in new_log
    assert os.readlink(fake_root.current_link) == "releases/beef001"


def test_invalid_host_or_port_fails_before_any_change(fake_root, fake_release, run_activate):
    fake_release("dead111")

    fake_root.env_file.write_text(
        "SKYPANE_PUBLIC_HOST=x;rm\n"
        "SKYPANE_COMPANION_HOST=cfg.example.org\n"
        "SKYPANE_BYOS_PORT=8642\n"
        "SKYPANE_COMPANION_PORT=8643\n"
    )
    r = run_activate("dead111")
    assert r.returncode != 0
    assert not fake_root.current_link.exists()
    assert not (fake_root.releases / "dead111").exists()

    fake_root.env_file.write_text(
        "SKYPANE_PUBLIC_HOST=pub.example.org\n"
        "SKYPANE_COMPANION_HOST=cfg.example.org\n"
        "SKYPANE_BYOS_PORT=notaport\n"
        "SKYPANE_COMPANION_PORT=8643\n"
    )
    r2 = run_activate("dead111")
    assert r2.returncode != 0
    assert not fake_root.current_link.exists()
    assert not (fake_root.releases / "dead111").exists()


def test_missing_prerequisites_fails_before_any_change(fake_root, fake_release, run_activate):
    fake_release("cafe111")

    missing_env = fake_root.path / "no-such-env"
    r = run_activate("cafe111", ENV_FILE=str(missing_env))
    assert r.returncode != 0
    assert "provision.sh" in r.stderr
    assert not fake_root.current_link.exists()
    assert not (fake_root.releases / "cafe111").exists()

    shutil.rmtree(fake_root.backup_root / "archives")
    r2 = run_activate("cafe111")
    assert r2.returncode != 0
    assert "provision.sh" in r2.stderr
    assert not fake_root.current_link.exists()
    assert not (fake_root.releases / "cafe111").exists()


def test_requirements_hash_gates_pip_install(fake_root, fake_release, run_activate):
    fake_release("face001")
    r = run_activate("face001")
    assert r.returncode == 0, r.stderr

    log = fake_root.call_log.read_text()
    assert log.count("pip install") == 1

    hash_file = fake_root.venv_dir / ".requirements.sha256"
    assert hash_file.exists()
    expected_hash = hashlib.sha256(
        (fake_root.releases / "face001" / "server" / "requirements.txt").read_bytes()
    ).hexdigest()
    assert hash_file.read_text().strip() == expected_hash

    fake_release("face002")
    r2 = run_activate("face002")
    assert r2.returncode == 0, r2.stderr

    log2 = fake_root.call_log.read_text()
    assert log2.count("pip install") == 1  # unchanged requirements content -> same hash -> not re-run


# --- Shared host Caddyfile: SkyPane owns only sites/skypane.caddy. ---


def test_host_caddyfile_byte_identical_after_deploy_and_rollback(
    fake_root, fake_release, run_activate
):
    host_bytes = fake_root.caddyfile.read_bytes()

    fake_release("a1a1a1a")
    assert run_activate("a1a1a1a").returncode == 0
    assert fake_root.caddyfile.read_bytes() == host_bytes
    first_site = fake_root.site_file.read_text()

    # Change the rendered output so the second deploy really replaces the
    # site file and the rollback has something to restore.
    fake_root.env_file.write_text(
        fake_root.env_file.read_text().replace("pub.example.org", "pub2.example.org")
    )
    fake_release("b2b2b2b")
    r = run_activate("b2b2b2b", FAKE_INACTIVE="skypane-byos.service", PROBE_TIMEOUT_S="1")
    assert r.returncode != 0
    assert os.readlink(fake_root.current_link) == "releases/a1a1a1a"

    assert fake_root.caddyfile.read_bytes() == host_bytes
    assert fake_root.site_file.read_text() == first_site
    log = fake_root.call_log.read_text().splitlines()
    assert sum(1 for ln in log if ln == "systemctl reload caddy") == 3


def test_validate_runs_against_the_host_caddyfile(fake_root, fake_release, run_activate):
    fake_release("c3c3c3c")
    assert run_activate("c3c3c3c").returncode == 0
    validate_lines = [
        ln for ln in fake_root.call_log.read_text().splitlines()
        if ln.startswith("caddy validate")
    ]
    assert validate_lines == [
        f"caddy validate --config {fake_root.caddyfile} --adapter caddyfile"
    ]


def test_missing_import_line_fails_before_any_change(fake_root, fake_release, run_activate):
    no_import = fake_root.host_caddyfile_text.replace("import sites/*.caddy\n", "")
    fake_root.caddyfile.write_text(no_import)
    fake_release("d4d4d4d")

    r = run_activate("d4d4d4d")
    assert r.returncode != 0
    assert "import sites/*.caddy" in r.stderr
    assert "deploy/README.md" in r.stderr
    assert not fake_root.current_link.exists()
    assert not (fake_root.releases / "d4d4d4d").exists()
    assert _sites_dir_names(fake_root) == set()
    assert fake_root.caddyfile.read_text() == no_import
    assert "caddy" not in fake_root.call_log.read_text()


def test_commented_or_indented_import_lines(fake_root, fake_release, run_activate):
    fake_release("d5d5d5d")
    fake_root.caddyfile.write_text("# import sites/*.caddy\n")
    assert run_activate("d5d5d5d").returncode != 0
    assert not (fake_root.releases / "d5d5d5d").exists()

    fake_root.caddyfile.write_text("x {\n}\n  import /etc/caddy/sites/*.caddy\n")
    assert run_activate("d5d5d5d").returncode == 0


def test_missing_host_caddyfile_or_sites_dir_fails_before_any_change(
    fake_root, fake_release, run_activate
):
    fake_release("d6d6d6d")
    r = run_activate("d6d6d6d", CADDYFILE=str(fake_root.caddy_dir / "absent"))
    assert r.returncode != 0
    assert "import sites/*.caddy" in r.stderr
    assert not (fake_root.releases / "d6d6d6d").exists()

    r2 = run_activate("d6d6d6d", CADDY_SITES_DIR=str(fake_root.caddy_dir / "no-sites"))
    assert r2.returncode != 0
    assert "provision.sh" in r2.stderr
    assert not (fake_root.releases / "d6d6d6d").exists()
    assert not (fake_root.caddy_dir / "no-sites").exists()


def test_validate_failure_restores_previous_site_file(fake_root, fake_release, run_activate):
    fake_release("e7e7e7e")
    assert run_activate("e7e7e7e").returncode == 0
    previous_site = fake_root.site_file.read_bytes()
    log_before = fake_root.call_log.read_text()

    fake_root.env_file.write_text(
        fake_root.env_file.read_text().replace("cfg.example.org", "cfg2.example.org")
    )
    fake_release("f8f8f8f")
    r = run_activate("f8f8f8f", FAKE_CADDY_RC="1")
    assert r.returncode != 0
    assert "validation failed" in r.stderr

    assert os.readlink(fake_root.current_link) == "releases/e7e7e7e"
    assert fake_root.site_file.read_bytes() == previous_site
    assert fake_root.caddyfile.read_text() == fake_root.host_caddyfile_text
    assert not (fake_root.sites_dir / ".skypane.caddy.new").exists()
    new_log = fake_root.call_log.read_text()[len(log_before):]
    assert "systemctl reload caddy" not in new_log
    assert "systemctl restart" not in new_log


def test_first_deploy_without_previous_site_file(fake_root, fake_release, run_activate):
    assert not fake_root.site_file.exists()
    fake_release("0a0a0a0")
    r = run_activate("0a0a0a0")
    assert r.returncode == 0, r.stderr

    assert fake_root.site_file.exists()
    # Nothing to back up on a first deploy; only the site file itself is
    # in the imported directory afterwards.
    assert _sites_dir_names(fake_root) == {"skypane.caddy"}
    assert "systemctl reload caddy" in fake_root.call_log.read_text()
    assert fake_root.caddyfile.read_text() == fake_root.host_caddyfile_text


def test_unchanged_site_file_skips_caddy_reload(fake_root, fake_release, run_activate):
    fake_release("1b1b1b1")
    assert run_activate("1b1b1b1").returncode == 0
    log_before = fake_root.call_log.read_text()

    fake_release("2c2c2c2")
    assert run_activate("2c2c2c2").returncode == 0
    new_log = fake_root.call_log.read_text()[len(log_before):]
    assert "systemctl reload caddy" not in new_log
    assert "caddy validate" not in new_log


def test_backup_and_staging_names_escape_the_import_glob(fake_root, fake_release, run_activate):
    fake_release("3d3d3d3")
    assert run_activate("3d3d3d3").returncode == 0
    fake_root.env_file.write_text(
        fake_root.env_file.read_text().replace("pub.example.org", "pub3.example.org")
    )
    fake_release("4e4e4e4")
    assert run_activate("4e4e4e4").returncode == 0

    assert fake_root.site_file_prev.exists()
    imported = {p.name for p in fake_root.sites_dir.glob("*.caddy")}
    assert imported == {"skypane.caddy"}
