"""Lists secret-looking strings, e-mail addresses and public IPv4 literals in a
git repository, in the working tree or in the full history. Stdlib only.

The output never contains the matched text: every row carries only the class
of match, the file, the short commit (or "tree") and the number of matching
lines. That makes the report safe to paste into a chat, a ticket or a log.

Subcommands:
  tree     scan the files tracked at HEAD
  history  scan every line ever added on any ref (`git log --all -p --text`)

Row shape (text format):
  type=<class> file=<path> commit=<short hash or tree> lines=<n>

Scanning a full mirror, which also covers deleted branches and pull request
heads (a shallow or single-branch clone cannot see those):
  git clone --mirror <url> skypane-mirror.git
  cd skypane-mirror.git
  git fetch origin '+refs/pull/*:refs/pull/*'
  python3 scripts/exposure_scan.py history --repo . --format tsv > scan.tsv

A shallow clone is detected and reported as the line
`warning=shallow-clone history-incomplete`.

Exit status is 0 for a completed run, or 1 with --fail-on-find when at least
one row was found.
"""
import argparse
import ipaddress
import re
import subprocess
import sys
from collections import Counter

# The scan and its tests build their patterns from fragments and would
# otherwise report themselves.
SELF_PATHS = frozenset({"scripts/exposure_scan.py", "scripts/test_exposure_scan.py"})

SHALLOW_WARNING = "warning=shallow-clone history-incomplete"

_EMAIL_IGNORED_DOMAINS = (
    "users.noreply.github.com", "example.com", "example.org", "example.net",
)
_EMAIL_IGNORED_LOCALS = frozenset({"noreply", "no-reply"})
# "icon@2x.png" and similar asset names look like addresses.
_FILE_EXTENSION_TLDS = frozenset({
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "css", "js",
    "html", "json", "py", "md", "txt",
})


def _valid_email(text):
    local, _, domain = text.rpartition("@")
    domain = domain.lower()
    if local.lower() in _EMAIL_IGNORED_LOCALS:
        return False
    if domain.rsplit(".", 1)[-1] in _FILE_EXTENSION_TLDS:
        return False
    return not any(
        domain == d or domain.endswith("." + d) for d in _EMAIL_IGNORED_DOMAINS
    )


def _valid_public_ipv4(text):
    try:
        return ipaddress.IPv4Address(text).is_global
    except ValueError:
        return False


# Ordered (class, compiled pattern, optional validator on the matched text).
PATTERNS = [
    ("pem-private-key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"), None),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), None),
    ("github-token", re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{50,}\b"), None),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), None),
    ("api-key-sk", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), None),
    ("bearer-literal", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"), None),
    ("assigned-secret", re.compile(
        r"(?i)\b(?:secret|password|passwd|token|api[_-]?key)\w*\s*[:=]\s*"
        r"[\"'][A-Za-z0-9/+_=.-]{12,}[\"']"), None),
    ("email-non-noreply", re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
        _valid_email),
    ("ipv4-public", re.compile(
        r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d]|\.\d)"), _valid_public_ipv4),
]


def classify_line(line):
    """Return the set of classes that match one line of text."""
    found = set()
    for name, regex, validator in PATTERNS:
        for match in regex.finditer(line):
            if validator is None or validator(match.group(0)):
                found.add(name)
                break
    return found


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, check=True,
    ).stdout


def is_shallow(repo):
    out = _git(repo, "rev-parse", "--is-shallow-repository")
    return out.strip() == b"true"


def scan_tree(repo):
    """Counter of (class, file, "tree") -> matching line count."""
    counts = Counter()
    listing = _git(repo, "ls-files", "-z").split(b"\0")
    for raw_path in listing:
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", "replace")
        if path in SELF_PATHS:
            continue
        try:
            with open(f"{repo}/{path}", "rb") as handle:
                data = handle.read()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        for line in data.decode("utf-8", "replace").splitlines():
            for name in classify_line(line):
                counts[(name, path, "tree")] += 1
    return counts


def scan_history(repo):
    """Counter of (class, file, short commit) -> added line count."""
    counts = Counter()
    proc = subprocess.Popen(
        ["git", "-C", repo, "log", "--all", "--text", "-p", "--no-color",
         "--format=%x00%h"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    commit = "unknown"
    path = None
    in_hunk = False
    for raw in proc.stdout:
        line = raw.rstrip(b"\n").decode("utf-8", "replace")
        if line.startswith("\0"):
            commit, path, in_hunk = line[1:].strip(), None, False
        elif line.startswith("diff --git "):
            path, in_hunk = None, False
        elif in_hunk:
            if line.startswith("+") and path and path not in SELF_PATHS:
                for name in classify_line(line[1:]):
                    counts[(name, path, commit)] += 1
        elif line.startswith("+++ "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else None
        elif line.startswith("@@"):
            in_hunk = True
    proc.stdout.close()
    stderr = proc.stderr.read()
    proc.stderr.close()
    if proc.wait() != 0:
        raise RuntimeError("git log failed: " + stderr.decode("utf-8", "replace")[:200])
    return counts


def _clean(text):
    return re.sub(r"[\t\r\n]", "?", text)


def format_rows(counts, fmt, max_rows):
    """Return (rows, truncated) as printable strings, sorted for stability."""
    items = sorted(counts.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))
    truncated = max_rows is not None and len(items) > max_rows
    if max_rows is not None:
        items = items[:max_rows]
    rows = []
    for (name, path, commit), count in items:
        path, commit = _clean(path), _clean(commit)
        if fmt == "tsv":
            rows.append(f"{name}\t{path}\t{commit}\t{count}")
        else:
            rows.append(f"type={name} file={path} commit={commit} lines={count}")
    return rows, truncated


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode, helptext in (("tree", "scan tracked files"),
                           ("history", "scan all added lines in history")):
        p = sub.add_parser(mode, help=helptext)
        p.add_argument("--repo", default=".", help="repository or mirror directory")
        p.add_argument("--format", choices=("text", "tsv"), default="text")
        p.add_argument("--fail-on-find", action="store_true",
                       help="exit 1 when at least one row is found")
        p.add_argument("--max-rows", type=int, default=None,
                       help="print at most N rows")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    # In tsv mode warnings go to stderr so the table stays machine-readable.
    warn_out = sys.stderr if args.format == "tsv" else sys.stdout
    try:
        if args.mode == "history" and is_shallow(args.repo):
            print(SHALLOW_WARNING, file=warn_out)
        counts = scan_tree(args.repo) if args.mode == "tree" else scan_history(args.repo)
    except (subprocess.CalledProcessError, RuntimeError, OSError):
        print("error=scan-failed", file=sys.stderr)
        return 2
    rows, truncated = format_rows(counts, args.format, args.max_rows)
    for row in rows:
        print(row)
    if truncated:
        print(f"warning=truncated rows={len(counts)}", file=warn_out)
    return 1 if (args.fail_on_find and counts) else 0


if __name__ == "__main__":
    sys.exit(main())
