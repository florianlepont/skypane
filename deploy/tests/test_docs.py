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
    assert "cortege.algernon.is" in text


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


def _auth0_section():
    text = _text()
    start = text.index("## Sign-in (Auth0)")
    return text[start:text.index("## Verifying the deployment", start)]


def test_documents_auth0_sign_in():
    section = _auth0_section()
    for name in (
        "SKYPANE_AUTH0_DOMAIN",
        "SKYPANE_AUTH0_CLIENT_ID",
        "SKYPANE_AUTH0_CLIENT_SECRET",
        "https://<companion host>/callback",
        "https://<companion host>/login",
        "unlink-identity",
        "wrong `code_verifier`",
        "refuses a v2 file as too new",
        "sessions",
    ):
        assert name in section, name


def test_auth0_section_has_placeholders_only():
    section = _auth0_section()
    assert "<auth0-client-secret>" in section
    assert ".auth0.com" not in section.replace("<your-tenant>.eu.auth0.com", "")


def test_retired_password_variables_appear_only_in_the_upgrade_note():
    text = _text()
    start = text.index("**Upgrade note:**")
    end = text.index("\n\n", start)
    rest = text[:start] + text[end:]
    assert "Upgrade note" in text[start:end]
    for name in ("SKYPANE_COMPANION_PASSWORD", "SKYPANE_LEGACY_PASSWORD_LOGIN"):
        assert name in text[start:end]
        assert name not in rest


def _typed_release_section():
    text = _text()
    start = text.index("### Per-hardware-type releases")
    return text[start:text.index("## Backups", start)]


def test_deploy_readme_documents_typed_release_layout_and_switch():
    section = _typed_release_section()
    for name in (
        "release-<key>.json",
        "skypane-<key>-<tag>.bin",
        "SKYPANE_ENABLE_SECOND_HARDWARE",
        "exactly `1`",
        "skipped <tag> [<key>]: hardware type not available here",
    ):
        assert name in section, name


def test_deploy_readme_lift_runbook_is_owner_only_and_ends_in_a_deploy():
    section = _typed_release_section()
    start = section.index("#### Lifting the second-hardware switch")
    runbook = section[start:]
    assert runbook.count("SKYPANE_ENABLE_SECOND_HARDWARE") >= 2
    for phrase in (
        "only by the owner",
        "written confirmation",
        "workflow_dispatch",
        "`deploy.yml`",
        "no agent",
    ):
        assert phrase in runbook, phrase


def test_deploy_readme_claims_no_published_typed_release():
    section = _typed_release_section()
    assert "not yet published" in section
    assert "switch is closed" in section


def _signing_text():
    return (_REPO_ROOT / "firmware" / "SIGNING.md").read_text()


def test_signing_md_has_per_type_release_section():
    text = _signing_text()
    start = text.index("## Per-type releases")
    section = text[start:text.index("\n## ", start + 5)]
    for name in (
        "skypane-<key>-<tag>.bin",
        "release-<key>.json",
        "one RSA signing key",
        "build-ee02",
        "build-second",
        "check_production_config.sh built",
        "firmware-release.yml",
    ):
        assert name in section, name


def test_signing_md_documents_mac_signing():
    text = _signing_text()
    assert "fw_publish_signed.py" in text
    assert "--dry-run" in text
    assert "## Releasing (signing on the Mac)" in text
    assert "gh secret set FW_SIGNING_KEY" not in text
    assert "firmware-signing" not in text


def test_firmware_releases_section_describes_the_manual_path():
    text = _text()
    start = text.index("## Firmware releases (OTA)")
    section = text[start:text.index("\n## ", start + 5)]
    assert "fw_publish_signed.py" in section
    assert "deploy.yml" in section
    assert "reviewer approval" not in section
    assert "gh workflow run ci.yml" not in text
    assert "gh secret set FW_SIGNING_KEY" not in text


def test_documents_private_repository_setup():
    text = _text()
    start = text.index("## Private repository (GitHub Free plan)")
    assert start < text.index("## Secrets discipline")
    end = text.index("\n## ", start + 1)
    section = text[start:end]
    for needle in (
        "deploy.yml",
        "fw_publish_signed.py",
        "CI_RUNS_ON",
        "branch protection",
        "environments",
    ):
        assert needle in section, needle
    assert "reviewer approval" not in section.lower()


def test_ci_paths_section_states_what_skips_and_what_never_does():
    text = _text()
    assert "Which commits start CI" in text
    assert "hardware/cad" in text
    assert "ci_sha" in text
    assert "Lint, test, coverage, attribution" in text
    assert "docs-only tip" not in text
