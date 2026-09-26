"""deploy/tests/test_caddyfile.py -- render_caddyfile.sh + HSTS.

Runs render_caddyfile.sh as a real subprocess (it is a shell script, not
Python) and parses the rendered text. No caddy binary is invoked (there is
none on the pytest runner) -- deploy/render_caddyfile.sh's own syntax is
checked separately with `bash -n`, and the real `caddy validate` only ever
runs on the VPS inside activate.sh.
"""

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "deploy" / "render_caddyfile.sh"
_TEMPLATE = _REPO_ROOT / "deploy" / "Caddyfile"


def _render(public_host, companion_host, template=None):
    return subprocess.run(
        ["bash", str(_SCRIPT), str(template or _TEMPLATE), public_host, companion_host],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _site_blocks(text):
    """Split rendered Caddyfile text into {site-address: block-body}.

    A site block opens with a line ending in " {" at column 0 (never
    indented — Caddyfile site addresses are always column 0) and closes at
    the matching column-0 "}", tracked by brace depth so a nested `log { }`
    block does not end the outer block early.
    """
    blocks = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(\S+) \{$", lines[i])
        if m:
            address = m.group(1)
            depth = 1
            body = []
            i += 1
            while i < len(lines) and depth > 0:
                if lines[i].rstrip().endswith("{"):
                    depth += 1
                elif lines[i].strip() == "}":
                    depth -= 1
                    if depth == 0:
                        break
                body.append(lines[i])
                i += 1
            blocks[address] = "\n".join(body)
        i += 1
    return blocks


def test_renders_both_hostnames_into_site_lines():
    result = _render("pub.example.org", "cfg.example.org")
    assert result.returncode == 0, result.stderr
    blocks = _site_blocks(result.stdout)
    assert "pub.example.org" in blocks
    assert "cfg.example.org" in blocks
    # The companion line must not be corrupted by the device substitution
    # (the device anchor is a substring of the companion anchor).
    assert "config-cfg.example.org" not in result.stdout
    assert "config-pub.example.org" not in result.stdout


def test_each_site_block_carries_hsts_no_preload_no_include_subdomains():
    result = _render("pub.example.org", "cfg.example.org")
    assert result.returncode == 0, result.stderr
    blocks = _site_blocks(result.stdout)
    assert len(blocks) == 2
    for address, body in blocks.items():
        assert 'header Strict-Transport-Security "max-age=31536000"' in body, address
    # Comments may explain the *absence* of preload/includeSubDomains
    # without that mention counting as the directive itself -- only
    # non-comment lines matter here.
    non_comment_lines = "\n".join(
        line for line in result.stdout.splitlines() if not line.strip().startswith("#")
    )
    assert "preload" not in non_comment_lines
    assert "includeSubDomains" not in non_comment_lines


def test_reverse_proxy_targets_unchanged():
    result = _render("pub.example.org", "cfg.example.org")
    blocks = _site_blocks(result.stdout)
    assert "reverse_proxy 127.0.0.1:8642" in blocks["pub.example.org"]
    assert "reverse_proxy 127.0.0.1:8643" in blocks["cfg.example.org"]


def test_rejects_hostname_with_space():
    result = _render("a b", "cfg.example.org")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_hostname_with_semicolon_injection():
    result = _render("x;rm -rf /", "cfg.example.org")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_hostname_with_command_substitution_dollar():
    result = _render("$(id)", "cfg.example.org")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_hostname_with_command_substitution_backtick():
    result = _render("`id`", "cfg.example.org")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_empty_public_host():
    result = _render("", "cfg.example.org")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_empty_companion_host():
    result = _render("pub.example.org", "")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rejects_bad_companion_host_even_when_public_host_is_valid():
    result = _render("pub.example.org", "x;rm -rf /")
    assert result.returncode != 0
    assert result.stdout == ""


def test_never_sources_or_reads_the_env_file():
    script_text = _SCRIPT.read_text()
    # No `source`/`. ` include of any file, and no literal reference to
    # the operator's env filename anywhere in the script.
    assert not re.search(r"(^|[^A-Za-z_])(source|\. )\s+\S*env", script_text, re.MULTILINE)
    assert "skypane.env" not in script_text


def test_script_is_executable():
    assert _SCRIPT.stat().st_mode & 0o111 == 0o111


def test_missing_template_fails_cleanly():
    result = _render("pub.example.org", "cfg.example.org", template=_REPO_ROOT / "deploy" / "does-not-exist")
    assert result.returncode != 0
    assert result.stdout == ""


def test_rendered_output_is_an_importable_site_snippet():
    # The output is imported into the shared host Caddyfile through
    # `import sites/*.caddy`; a global options block (a bare `{` opening
    # at column 0) is only legal at the top of the host file and would
    # break every site on the box, not just SkyPane's.
    r = _render("pub.example.org", "cfg.example.org")
    assert r.returncode == 0, r.stderr
    code_lines = [ln for ln in r.stdout.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert code_lines, "rendered snippet is empty"
    assert not any(ln.strip() == "{" for ln in code_lines if not ln.startswith((" ", "\t")))
    assert not any(ln.startswith("import ") for ln in code_lines)
    assert set(_site_blocks(r.stdout)) == {"pub.example.org", "cfg.example.org"}
