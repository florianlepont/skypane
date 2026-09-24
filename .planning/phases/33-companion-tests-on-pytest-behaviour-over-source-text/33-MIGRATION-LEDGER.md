# Phase 33 Migration Ledger

## Purpose

Every pre-migration check of the 9 companion harnesses ends up in this ledger mapped to a real
pytest node id (`ported`), or `deleted` with a stated reason. Together with Phase 32's 769
server-side checks, this covers all 2018 pre-migration checks the 2026-09-23 audit measured
(`.planning/audits/2026-09-23-code-audit.md`, TST-15). The live baseline capture measured 1250,
not the audit's own 2018 − 769 = 1249 arithmetic — `33-BASELINE/INDEX.md`'s Notes section
traces the +1 to a specific commit (`17d5bc7`, plan 32-11) that landed a new check after the
audit's baseline was taken.

Nothing in this file is hand-edited above the `<!-- fragments -->` marker below by anyone other
than 33-01 (this scaffold) — everything from the marker down is regenerated verbatim by
`33-ledger-check.py --assemble` (run once, by 33-33), which also refreshes the Summary table
and grand totals from the 9 fragments' current state.

## Format

Each fragment lives at `33-ledger/<key>.md`, one per harness, with the header
`# Ledger: <harness>`, a `Baseline:` line naming the transcript and its check count, then a
table:

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |

Disposition is one of `ported`, `deleted`, `pending`. A `|` inside a label is escaped as `\|`.
A `ported` target is the full pytest node id (`companion/test_status_pages_03.py::test_x`, or
`...::test_y[id]` for a parametrised test — browser node ids carry pytest-playwright's
`[chromium]` suffix exactly as `pytest --collect-only -q` prints it). A `deleted` target is the
reason, in the form `<rubric code>: <why there is no behaviour / what covers it now>`.

## Staged-migration rule

The 9 companion harnesses migrate across 28 plans (33-04..33-31), several plans per large
harness. The legacy harness stays on disk, still detected by
`test-support/skypane_test_support.py` (one of the 9 `ORIGINAL_COMPANION_HARNESSES`, still
containing a line starting `EXPECTED_CHECK_COUNT`), until its chain's LAST plan deletes it. A
fragment's `pending` row count must always equal that shrunk legacy harness's own single
authoritative `EXPECTED_CHECK_COUNT = <remaining>` line — every check is always accounted for
as either still-legacy (`pending`) or already-ported/deleted, never both, never neither.
`33-ledger-check.py <harness> --allow-pending` enforces this; the chain's final plan drops
`--allow-pending` once the legacy file is `git rm`'d and every row is `ported` or `deleted`.

## TST-12 classification rubric

Every check migrated out of a legacy harness gets exactly ONE of these codes (full detail:
`33-MIGRATION-RULES.md` section 3):

| Code | What the legacy check does | Disposition |
|------|---------------------------|-------------|
| B | Calls a production function or makes an HTTP request, and asserts on its output | `ported`: only the plumbing changes |
| D | Regex or substring test over rendered HTML | `ported`: parsed-DOM assertion, or a plain substring test for user-visible rendered text |
| C | Opens `companion/static/style.css` (or any CSS) from disk, or slices CSS text | `ported`: fetch via `served_stylesheet(server)` and assert on `css_rules`/`declarations_for`, or a browser computed-style assertion. A check on a CSS COMMENT is `deleted` |
| J | Opens a served JS asset as text | `ported`: fetch over HTTP, `strip_js_comments_and_strings`, assert the delivery contract. A check on a JS COMMENT is `deleted` |
| S | Opens a production `.py`/`.html` source file, or introspects production code via `inspect`/`ast`/`tokenize` | Rewrite as an observable-consequence behaviour test where one exists; otherwise `deleted` |
| P | Opens `.planning/...` or a UI-SPEC file | Rewrite against a literal copied into the test when the spec pins user-visible copy; otherwise `deleted` |
| R | Self-referential: opens the test file itself (e.g. `_ASPECT_REPIN_LEDGER`) | `deleted`: plan-history bookkeeping, no behaviour |
| S/T | Root-unsafe (`os.chmod`, or a literal host path production code may `mkdir`) | `ported` with `@requires_non_root` and/or a `tmp_path` absent path |

## Status table

| Harness | Baseline (pre-migration) | Owning plans |
| --- | ---: | --- |
| `companion/test_contrast_check.py` | 49 | 33-04 |
| `companion/test_i18n.py` | 24 | 33-04 |
| `companion/test_view_pages.py` | 169 | 33-05..33-08 |
| `companion/test_config_page.py` | 276 | 33-09..33-13 |
| `companion/test_companion_app.py` | 320 | 33-14..33-18 |
| `companion/test_browser_ux_health_drawings.py` | 11 | 33-19 |
| `companion/test_browser_ux_quiet_wake.py` | 9 | 33-20 |
| `companion/test_browser_ux.py` | 75 | 33-21..33-24 |
| `companion/test_status_pages.py` | 317 | 33-25..33-31 |

Grand total: 1250 pre-migration checks across 9 harnesses (`33-BASELINE/INDEX.md`).

## Verification

```bash
server/.venv/bin/python3 .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger-check.py --allow-pending --all
```

Every plan from 33-04 onward runs this (or the single-harness form) after flipping its slice's
rows, and the chain's final plan for each harness runs it without `--allow-pending`. 33-33 runs
`33-ledger-check.py --assemble` once every fragment has zero pending rows, which requires this
same command to exit 0 with zero pending rows across all 9 harnesses first.

<!-- fragments -->

## Closing parity

_Filled in by `33-ledger-check.py --assemble`, run once by 33-33 once all 9 harnesses have
finished migrating (zero pending rows in every fragment)._
