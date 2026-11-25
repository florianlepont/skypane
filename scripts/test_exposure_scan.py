"""Tests for scripts/exposure_scan.py on throwaway git repositories.

Every secret-looking value is assembled from fragments at test time so that
nothing resembling a credential is committed to this repository.
"""
import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exposure_scan.py")

AWS_BODY = "ABCDEFGHIJKLMNOP"
GITHUB_BODY = "a1B2" * 10
SLACK_BODY = "1234567890-abcdefghij"
SK_BODY = "Zy9Xw8Vu7Ts6Rq5Po4Nm3"
BEARER_BODY = "abcdEFGH1234ijklMNOP5678"
ASSIGNED_BODY = "Qw3rTy8UiOp2AsDf"
EMAIL_LOCAL = "jane.doe"
IP_TEXT = ".".join(["93", "184", "216", "34"])

# class -> (secret body that must never be printed, line content)
SAMPLES = {
    "pem-private-key": ("PRIVATE", "-----BEGIN " + "RSA PRIVATE KEY-----"),
    "aws-access-key": (AWS_BODY, "key = AK" + "IA" + AWS_BODY),
    "github-token": (GITHUB_BODY, "tok " + "gh" + "p_" + GITHUB_BODY),
    "slack-token": (SLACK_BODY, "hook " + "xo" + "xb-" + SLACK_BODY),
    "api-key-sk": (SK_BODY, "use " + "s" + "k-" + SK_BODY),
    "bearer-literal": (BEARER_BODY, "Authorization: Bear" + "er " + BEARER_BODY),
    "assigned-secret": (ASSIGNED_BODY, "api_key = " + '"' + ASSIGNED_BODY + '"'),
    "email-non-noreply": (EMAIL_LOCAL, "contact " + EMAIL_LOCAL + "@corp-mail.fr"),
    "ipv4-public": (IP_TEXT, "host " + IP_TEXT),
}

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_COMMITTER_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@users.noreply.github.com",
    "GIT_COMMITTER_EMAIL": "t@users.noreply.github.com",
}


def git(repo, *args):
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        check=True, env=ENV,
    )
    return out.stdout.strip()


def make_repo(tmp_path, name="repo"):
    repo = tmp_path / name
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    return repo


def commit_file(repo, relpath, content, message="c"):
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    git(repo, "add", relpath)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "--short", "HEAD")


def scan(repo, mode, *extra):
    return subprocess.run(
        [sys.executable, SCRIPT, mode, "--repo", str(repo), *extra],
        capture_output=True, text=True, env=ENV,
    )


@pytest.mark.parametrize("cls", sorted(SAMPLES))
def test_tree_mode_detects_each_class(tmp_path, cls):
    repo = make_repo(tmp_path)
    commit_file(repo, "src/app.txt", SAMPLES[cls][1] + "\n")
    result = scan(repo, "tree")
    assert result.returncode == 0
    assert f"type={cls} file=src/app.txt commit=tree lines=1" in result.stdout.splitlines()


@pytest.mark.parametrize("cls", sorted(SAMPLES))
def test_history_mode_detects_each_class_with_commit(tmp_path, cls):
    repo = make_repo(tmp_path)
    short = commit_file(repo, "src/app.txt", SAMPLES[cls][1] + "\n")
    result = scan(repo, "history")
    assert f"type={cls} file=src/app.txt commit={short} lines=1" in result.stdout.splitlines()


def test_history_reports_a_value_removed_in_a_later_commit(tmp_path):
    repo = make_repo(tmp_path)
    short = commit_file(repo, "conf.txt", SAMPLES["github-token"][1] + "\n")
    commit_file(repo, "conf.txt", "clean\n")
    assert "github-token" not in scan(repo, "tree").stdout
    history = scan(repo, "history").stdout.splitlines()
    assert f"type=github-token file=conf.txt commit={short} lines=1" in history


def test_ignored_addresses_are_not_reported(tmp_path):
    repo = make_repo(tmp_path)
    lines = [
        "a 10.0.0.5", "b 127.0.0.1", "c 192.168.1.20", "d 169.254.1.1",
        "e 192.0.2.7", "f 198.51.100.9", "g 203.0.113.4", "h 172.16.0.3",
        "i 1.2.3.4.5", "j 999.1.1.1",
        "k 12345+bot@users.noreply.github.com", "l me@example.com",
        "m me@example.org", "n me@example.net", "o noreply@vendor.fr",
        "p icon@2x.png",
    ]
    commit_file(repo, "notes.txt", "\n".join(lines) + "\n")
    assert scan(repo, "tree").stdout == ""
    assert scan(repo, "history").stdout == ""


def test_output_never_contains_the_matched_text(tmp_path):
    repo = make_repo(tmp_path)
    body = "\n".join(sample for _, sample in SAMPLES.values()) + "\n"
    commit_file(repo, "all.txt", body)
    forbidden = [value for value, _ in SAMPLES.values() if value != "PRIVATE"]
    forbidden += ["BEGIN", "corp-mail"]
    for mode in ("tree", "history"):
        for fmt in ("text", "tsv"):
            result = scan(repo, mode, "--format", fmt)
            combined = result.stdout + result.stderr
            assert combined.strip(), "expected rows"
            for fragment in forbidden:
                assert fragment not in combined


def test_tsv_rows_are_type_file_commit_count(tmp_path):
    repo = make_repo(tmp_path)
    short = commit_file(repo, "x.txt", SAMPLES["api-key-sk"][1] + "\n")
    rows = scan(repo, "history", "--format", "tsv").stdout.splitlines()
    assert rows == [f"api-key-sk\tx.txt\t{short}\t1"]


def test_shallow_clone_prints_the_warning(tmp_path):
    origin = make_repo(tmp_path, "origin")
    commit_file(origin, "a.txt", "one\n")
    commit_file(origin, "a.txt", "two\n")
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.as_uri(), str(shallow)],
        check=True, capture_output=True, env=ENV,
    )
    result = scan(shallow, "history")
    assert "warning=shallow-clone history-incomplete" in result.stdout.splitlines()
    full = scan(origin, "history")
    assert "warning=" not in full.stdout


def test_fail_on_find_exit_codes(tmp_path):
    repo = make_repo(tmp_path)
    commit_file(repo, "clean.txt", "nothing here\n")
    assert scan(repo, "tree", "--fail-on-find").returncode == 0
    commit_file(repo, "leak.txt", SAMPLES["aws-access-key"][1] + "\n")
    assert scan(repo, "tree").returncode == 0
    assert scan(repo, "tree", "--fail-on-find").returncode == 1
    assert scan(repo, "history", "--fail-on-find").returncode == 1


def test_scan_script_and_its_tests_are_excluded(tmp_path):
    repo = make_repo(tmp_path)
    body = SAMPLES["api-key-sk"][1] + "\n"
    commit_file(repo, "scripts/exposure_scan.py", body)
    commit_file(repo, "scripts/test_exposure_scan.py", body)
    assert scan(repo, "tree").stdout == ""
    assert scan(repo, "history").stdout == ""


def test_max_rows_truncates_and_says_so(tmp_path):
    repo = make_repo(tmp_path)
    for index in range(3):
        commit_file(repo, f"f{index}.txt", SAMPLES["api-key-sk"][1] + "\n")
    lines = scan(repo, "tree", "--max-rows", "2").stdout.splitlines()
    assert sum(line.startswith("type=") for line in lines) == 2
    assert "warning=truncated rows=3" in lines


def test_every_output_line_is_a_type_or_warning_row(tmp_path):
    repo = make_repo(tmp_path)
    commit_file(repo, "a.txt", "\n".join(s for _, s in SAMPLES.values()) + "\n")
    for mode in ("tree", "history"):
        for line in scan(repo, mode).stdout.splitlines():
            assert line.startswith(("type=", "warning="))
