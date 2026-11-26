"""deploy/tests/test_runner_loop.py -- deploy/runner/skypane-runner-loop.sh run
as a real subprocess with `security`, `curl`, `limactl` and `sleep` replaced
by recording shims on PATH. No network, no VM, no Keychain.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "deploy" / "runner" / "skypane-runner-loop.sh"

# Built at test time so no token-shaped literal sits in the source.
_TOKEN = "tok" + "-" + "x" * 8 + "-secret"
_JIT = "ENCODED" + "JIT" + "CONFIG"

_RECORDER = """#!{python}
import json, os, sys
tool = os.path.basename(sys.argv[0])
state = os.environ["SHIM_STATE"]
stdin = "" if sys.stdin.isatty() else sys.stdin.read()
with open(os.path.join(state, "calls.jsonl"), "a") as f:
    f.write(json.dumps({{"tool": tool, "argv": sys.argv[1:], "env": dict(os.environ), "stdin": stdin}}) + "\\n")
{body}
"""

_BODIES = {
    "security": f"print({_TOKEN!r})",
    "sleep": "pass",
    "limactl": "pass",
    "curl": """
counter = os.path.join(state, "curl-count")
n = int(open(counter).read()) if os.path.exists(counter) else 0
open(counter, "w").write(str(n + 1))
if n < int(os.environ.get("SHIM_CURL_FAILURES", "0")):
    sys.stderr.write("curl: (22) The requested URL returned error: 503\\n")
    sys.stdout.write("RESPONSE-BODY-MUST-NOT-BE-LOGGED")
    sys.exit(22)
print(json.dumps({"runner": {"id": 1}, "encoded_jit_config": os.environ["SHIM_JIT"]}))
""",
}


@pytest.fixture
def shims(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    for tool, body in _BODIES.items():
        path = bindir / tool
        path.write_text(_RECORDER.format(python=sys.executable, body=body))
        path.chmod(0o755)
    return bindir, state


def _run(shims, index="1", curl_failures=0, **extra):
    bindir, state = shims
    env = dict(os.environ)
    env.update(
        PATH=f"{bindir}{os.pathsep}{env['PATH']}",
        SHIM_STATE=str(state),
        SHIM_JIT=_JIT,
        SHIM_CURL_FAILURES=str(curl_failures),
        SKYPANE_RUNNER_REPO="owner/repo",
        SKYPANE_RUNNER_INDEX=index,
        SKYPANE_RUNNER_ONCE="1",
    )
    env.update(extra)
    return subprocess.run(["bash", str(_SCRIPT)], env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


def _calls(shims, tool):
    path = shims[1] / "calls.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return [r for r in rows if r["tool"] == tool]


def _runner_name(shims):
    body = next(a for a in _calls(shims, "curl")[0]["argv"] if a.startswith("{"))
    return json.loads(body)["name"]


def test_token_never_reaches_a_command_line_or_the_vm(shims):
    result = _run(shims)
    assert result.returncode == 0, result.stderr
    for call in _calls(shims, "curl") + _calls(shims, "limactl"):
        assert _TOKEN not in " ".join(call["argv"])
        assert _TOKEN not in json.dumps(call["env"])
    assert _TOKEN not in result.stdout + result.stderr
    # The token does reach curl, but only through its standard input.
    assert _TOKEN in _calls(shims, "curl")[0]["stdin"]
    assert "--config" in _calls(shims, "curl")[0]["argv"]


def test_one_runner_process_per_iteration_with_the_jit_config(shims):
    assert _run(shims).returncode == 0
    starts = [c for c in _calls(shims, "limactl") if "--jitconfig" in c["argv"]]
    assert len(starts) == 1
    argv = starts[0]["argv"]
    assert argv[argv.index("--jitconfig") + 1] == _JIT
    assert argv[:2] == ["shell", "skypane-ci"]
    assert any(a.endswith("/run.sh") for a in argv)


def test_jit_request_names_the_labels(shims):
    assert _run(shims).returncode == 0
    argv = _calls(shims, "curl")[0]["argv"]
    body = json.loads(next(a for a in argv if a.startswith("{")))
    assert body["labels"] == ["self-hosted", "skypane-ci"]
    assert body["runner_group_id"] == 1
    assert argv[-1] == "https://api.github.com/repos/owner/repo/actions/runners/generate-jitconfig"


def test_different_indexes_get_different_runner_names(shims, tmp_path):
    assert _run(shims, index="1").returncode == 0
    other = tmp_path / "other"
    other.mkdir()
    (other / "state").mkdir()
    bindir = shims[0]
    assert _run((bindir, other / "state"), index="2").returncode == 0
    first, second = _runner_name(shims), _runner_name((bindir, other / "state"))
    assert first != second
    assert "-1-" in first and "-2-" in second


def test_api_failure_retries_without_printing_the_response_body(shims):
    result = _run(shims, curl_failures=1)
    assert result.returncode == 0, result.stderr
    assert len(_calls(shims, "curl")) == 2
    assert len(_calls(shims, "sleep")) == 1
    assert "RESPONSE-BODY-MUST-NOT-BE-LOGGED" not in result.stdout + result.stderr
    assert len([c for c in _calls(shims, "limactl") if "--jitconfig" in c["argv"]]) == 1


def test_work_folder_is_wiped_after_the_job(shims):
    assert _run(shims).returncode == 0
    argvs = [c["argv"] for c in _calls(shims, "limactl")]
    start = next(i for i, a in enumerate(argvs) if "--jitconfig" in a)
    wipes = [i for i, a in enumerate(argvs) if "find" in a and "-delete" in a]
    assert wipes and min(wipes) > start
    assert any("/_work" in arg for arg in argvs[wipes[0]])


def test_runner_temporary_directory_is_wiped_after_the_job(shims):
    assert _run(shims).returncode == 0
    argvs = [c["argv"] for c in _calls(shims, "limactl")]
    start = next(i for i, a in enumerate(argvs) if "--jitconfig" in a)
    wipes = [i for i, a in enumerate(argvs)
             if "find" in a and "-delete" in a and "/home/runner/tmp" in a]
    assert wipes and min(wipes) > start


def test_missing_repository_is_refused(shims):
    result = _run(shims, SKYPANE_RUNNER_REPO="")
    assert result.returncode == 2
    assert not _calls(shims, "curl")
