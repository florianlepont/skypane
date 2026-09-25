# Phase 35 baseline

Measured with `server/.venv/bin/python scripts/check_comment_history.py ratio`
over every tracked file the tool has a comment syntax for (264 files), on top
of commit `83f4620cb784d39b2d8bab8e0c1f3b550ea923c3` plus this plan's own
uncommitted foundation additions at measurement time (the pending-list file,
and the CI guard step in `.github/workflows/ci.yml`, whose one new comment
carries no history reference). Interpreter: `server/.venv/bin/python`,
CPython 3.11.15 (production and CI run 3.14; the guard tool and its ratio
math are interpreter-version-independent stdlib).

Full per-file numbers: `ratio-before.tsv` (path, lines, comment_lines,
ratio, history_hits, bytes, gzip_bytes).

## Totals per directory group

Group numbers match `35-CONTEXT.md`'s PR-group list. Group 1 (foundation —
this plan) has no directory bucket of its own here: its new files land in
the groups their paths already belong to (`scripts/check_comment_history.py`
and `scripts/comment-history-pending.txt` in group 8,
`test-support/test_check_comment_history.py` in group 5).

| Group | Directories | Files | Lines | Comment lines | Ratio | History hits |
|---|---|---:|---:|---:|---:|---:|
| 2 | server/ | 36 | 30940 | 11511 | 37% | 1689 |
| 3 | stub-server/ | 6 | 2915 | 954 | 33% | 69 |
| 4 | companion production (Python) | 33 | 30353 | 19291 | 64% | 3620 |
| 5 | companion tests + test-support/ | 52 | 50312 | 12948 | 26% | 2605 |
| 6 | companion static JS | 17 | 6518 | 3738 | 57% | 340 |
| 7 | companion/static/style.css | 1 | 10689 | 6842 | 64% | 830 |
| 8 | deploy/ + scripts/ + .github/ + root config + adsb-test/ + hardware/ | 48 | 8325 | 1897 | 23% | 199 |
| 9 | firmware/ | 71 | 8472 | 2087 | 25% | 89 |
| **Total** | | **264** | **148524** | **59268** | **40%** | **9441** |

## style.css shipped size

`companion/static/style.css`:

- Raw: 512795 bytes (`wc -c`)
- Gzip -9: 170113 bytes (`gzip -9c | wc -c`)

## Pending list

`scripts/comment-history-pending.txt` lists all 208 files with at least one
history hit (of the 264 files the tool can scan) — 9441 hits total. The
guard's default `check` skips these paths until each group's closing plan
purges its files and shrinks the list; the last group deletes it.
