# Phase 33 follow-ups (orchestrator-tracked)

Items found while executing the migration plans that the closing plans
(33-32 guard tightening, 33-33 closing parity/verification) must resolve.

## F-01: text-level assertions over the served stylesheet

33-CONTEXT.md (TST-12) says CSS checks parse the served stylesheet
structurally, not with a regex over its text. Some migrated checks fetch
`style.css` over HTTP (no disk read, so guard G-rules pass) but then assert
with `re.search` / `str.index` / substring tests on the raw served text,
following 33-10's precedent. Known so far:

- `companion/test_config_page_02.py` (33-10), `companion/test_config_page_03.py`
  (33-11, ~9 large checks per its SUMMARY), `companion/test_view_pages_03.py`
  and `companion/test_companion_app_02.py` (substring/regex hits over served
  CSS/JS text).

Resolution in 33-32: sweep every migrated module for regex/index/substring
assertions over served CSS text; rewrite each over
`companion_markup.css_rules()` / `declarations_for()` / `rules_with_selector()`
(or a computed-style browser assertion). Anything that genuinely cannot be
expressed structurally is listed in the ledger with its reason. Then extend
`companion/test_suite_guards.py` with a rule that flags regex/index/substring
use on a value obtained from `served_stylesheet()`.

Served JS is different: without a JS engine, some contracts (e.g. "no
setTimeout", "ES5 only") are only expressible over the comment-stripped
served text; those stay, but must go through `strip_js_*` helpers, never raw
source on disk.

## F-02: gsd-sdk STATE.md mutations

Every `gsd-sdk query state.*` mutation resets frontmatter `percent` and can
rewrite the demoted historical block in STATE.md. Executors hand-correct it.
Not a phase-33 code issue; report upstream (get-shit-done-cc
`sdk/src/query/state-mutation.ts`).
