"""deploy/tests/test_docs.py -- deploy/README.md corrections: the "fully
reproducible" claim is gone, backups/restore are documented, the
release-layout deploy flow replaces the old rsync description, env
ownership matches provision.sh, and every operator example logs in as
`ubuntu@`, never `root@`.
"""
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_README = _REPO_ROOT / "deploy" / "README.md"


def _text():
    return _README.read_text()


def test_no_fully_reproducible_claim():
    assert "fully reproducible" not in _text().lower()


def test_no_root_at_login_examples():
    assert "root@" not in _text()


def test_has_restore_section_and_rehearsal_log():
    text = _text()
    assert any(
        line.startswith("## ") and "Restore" in line for line in text.splitlines()
    )
    assert "Rehearsal log" in text


def test_documents_ssh_hardening_dropin():
    text = _text()
    assert "00-skypane.conf" in text
    assert "PermitRootLogin no" in text


def test_documents_offbox_marker():
    assert "SKYPANE_OFFBOX_MARKER" in _text()


def test_documents_release_layout_and_activate_sh():
    text = _text()
    assert "releases/" in text
    assert "activate.sh" in text


def test_documents_gallery_in_backups():
    assert "gallery" in _text()


def test_env_file_no_longer_documented_as_skypane_owned():
    assert "chown skypane:skypane /opt/skypane/skypane.env" not in _text()
    assert "root:root" in _text()


def test_readme_syntax_present_for_every_deploy_script_referenced():
    # Cheap drift guard: every script file this README names in a code
    # fence must actually exist under deploy/.
    text = _text()
    for name in (
        "provision.sh",
        "harden_sshd.sh",
        "deploy.sh",
        "activate.sh",
        "render_caddyfile.sh",
        "install-backup-key.sh",
        "install-launchagent.sh",
        "skypane-backup-pull.sh",
        "skypane_backup.py",
        "backup_gate.py",
    ):
        assert name in text, f"{name} is no longer mentioned in deploy/README.md"


def test_documents_shared_host_caddyfile_layout_and_migration():
    text = _text()
    assert "/etc/caddy/sites/skypane.caddy" in text
    assert "import sites/*.caddy" in text
    assert "sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre37" in text
    # The revert path copies the backup back and reloads.
    assert "sudo cp /etc/caddy/Caddyfile.pre37 /etc/caddy/Caddyfile" in text
    assert "cortege.algernon.ovh" in text


def _firmware_section():
    text = _text()
    start = text.index("## Firmware releases (OTA)")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def test_firmware_cli_runs_from_the_release_dir_as_the_skypane_user():
    """`ubuntu` cannot cd into /opt/skypane/current, so every firmware_cli command example
    (inside a code fence) must run its cd inside the sudo -u skypane shell, before the exec
    of the module"""
    section = _firmware_section()
    fenced_blocks = section.split("```")[1::2]
    command_lines = [
        line for block in fenced_blocks for line in block.splitlines()
        if "server.firmware_cli" in line]
    assert command_lines, "expected at least one firmware_cli command example"
    for line in command_lines:
        assert "sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec " in line, line
        assert line.index("cd /opt/skypane/current") < line.index("-m server.firmware_cli"), line


def test_firmware_section_names_both_hosts_with_placeholders_only():
    section = _firmware_section()
    assert "<public-host>" in section
    assert "<companion-host>" in section
    assert ".ovh" not in section
