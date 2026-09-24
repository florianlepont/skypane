"""deploy/tests/test_ci_secrets.py — no secret spliced into a run: script
(SEC-07, D-20), plus the offline systemd-analyze CI gate (SEC-06).

Deliberately no PyYAML dependency (stdlib-only, matching this project's
discipline): a small text scanner is enough to find every `run:` block in
ci.yml and check its content, without needing a full YAML parser.
"""

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

_RUN_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)run:[ \t]*(?P<rest>.*)$")


def _run_blocks(text):
    """Yield the text content of every `run:` step in the workflow file.

    Handles both the inline form (`run: some command`) and the block
    scalar form (`run: |` followed by indented lines) by tracking
    indentation: a block scalar's body is every subsequent line indented
    strictly more than the `run:` line itself, stopping at the first line
    (non-blank) that is not.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _RUN_LINE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group("indent").expandtabs())
        rest = m.group("rest").strip()
        if rest and rest not in ("|", "|-", "|+", ">", ">-", ">+"):
            # Inline form: the whole command is on this one line.
            yield rest
            i += 1
            continue
        # Block scalar form: collect indented continuation lines.
        body = []
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.strip() == "":
                body.append(line)
                i += 1
                continue
            line_indent = len(line[: len(line) - len(line.lstrip())].expandtabs())
            if line_indent <= indent:
                break
            body.append(line)
            i += 1
        yield "\n".join(body)


def _steps_by_name(text):
    """Yield (step_name, run_block_text_or_None) tuples, in file order."""
    lines = text.splitlines()
    name_re = re.compile(r"^\s*-\s*name:\s*(.+)$")
    names_and_positions = []
    for idx, line in enumerate(lines):
        m = name_re.match(line)
        if m:
            names_and_positions.append((idx, m.group(1).strip()))
    for pos, name in names_and_positions:
        # Find the next `run:` at or after this step's `- name:` line,
        # but before the next step's `- name:` line.
        next_pos = None
        for other_pos, _ in names_and_positions:
            if other_pos > pos:
                next_pos = other_pos
                break
        chunk = "\n".join(lines[pos : next_pos if next_pos else len(lines)])
        run_match = None
        for run_text in _run_blocks(chunk):
            run_match = run_text
            break
        yield name, run_match


def test_no_secrets_expression_inside_any_run_block():
    text = _CI_YML.read_text()
    offenders = []
    for name, run_text in _steps_by_name(text):
        if run_text is None:
            continue
        if "${{ secrets." in run_text:
            offenders.append(name)
    assert not offenders, "run: block(s) still interpolate a secret: %s" % offenders


def test_deploy_job_passes_host_key_and_target_through_env():
    text = _CI_YML.read_text()
    assert "DEPLOY_HOST_KEY: ${{ secrets.DEPLOY_HOST_KEY }}" in text
    assert "DEPLOY_SSH_TARGET: ${{ secrets.DEPLOY_SSH_TARGET }}" in text
    names_and_runs = dict(_steps_by_name(text))
    host_key_run = names_and_runs.get("Trust the production host key")
    assert host_key_run is not None
    assert '"$DEPLOY_HOST_KEY"' in host_key_run

    deploy_run = names_and_runs.get("Deploy")
    assert deploy_run is not None
    assert '"$DEPLOY_SSH_TARGET"' in deploy_run


def test_offline_systemd_analyze_gate_present_in_test_job():
    text = _CI_YML.read_text()
    assert "systemd-analyze security --offline=true --threshold=20" in text
    names_and_runs = dict(_steps_by_name(text))
    score_run = names_and_runs.get("Score systemd units (offline, fail above 2.0)")
    assert score_run is not None
    assert "systemd-analyze security --offline=true --threshold=20" in score_run


def test_webfactory_ssh_agent_with_input_unaffected():
    # The ssh-agent action's own `with:` input is not a run: script and is
    # deliberately left interpolating the secret directly - only run:
    # blocks are the injection-risk surface this test guards.
    text = _CI_YML.read_text()
    assert "ssh-private-key: ${{ secrets.DEPLOY_SSH_PRIVATE_KEY }}" in text
