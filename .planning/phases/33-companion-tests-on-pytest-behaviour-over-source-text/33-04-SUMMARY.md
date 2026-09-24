---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 04
subsystem: testing
tags: [pytest, css-tokens, i18n, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/module_app_server_factory/app_server_in_process fixtures and companion_app_server.py's http_request/login/served_stylesheet/served_asset"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's custom_properties()/declarations_for() CSS parser, companion/test_suite_guards.py's TST-10/12/13/14 guard, and the disk-derived legacy companion harness set"
provides:
  - "companion/test_contrast_check.py: native pytest module, all 49 WCAG contrast / signal-separation checks measured against colour tokens fetched from a running server (custom_properties() over served_stylesheet()), never a hard-coded copy of style.css's :root values"
  - "companion/test_i18n.py: native pytest module, catalogue self-consistency (non-empty values, %s/%d/{...} placeholder parity, a full t_lang() round trip) plus real French renders of every authenticated page, login, 404 and the calendar-disconnect confirm page over a local InProcessAppServer fixture — no longer imports companion.test_companion_app"
  - "first proof, in a real commit, that the whole Phase 33 workflow (shared fixtures, markup toolkit, guard, ledger) holds end to end for a real harness migration"
affects: [33-05, 33-06, 33-07, 33-08, 33-09, 33-10, 33-11, 33-12, 33-13, 33-14, 33-15, 33-16, 33-17, 33-18, 33-32, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A migrated CSS-token test module fetches its colours from served_stylesheet() + custom_properties(css, ':root', at_rules=...) once per module (a module-scoped fixture built on module_app_server_factory), then asserts contrast/separation math over the live values — a future accidental token edit fails the test directly, instead of being silently re-validated against its own new hard-coded copy"
    - "A CSS color-mix(in srgb, var(X) N%, transparent) declaration used as a text colour is reproduced in a test as a plain per-channel alpha blend (N% of X over the opaque background beneath it) — mixing toward transparent leaves the RGB channels of X unchanged and only lowers the resulting alpha, which the browser then composites over whatever is actually behind the text"
    - "An ast/regex source-text completeness scan (i18n catalogue vs. page-module strings) with no observable runtime consequence is deleted outright (reason S), not rewritten — its guarantee is replaced by catalogue self-consistency checks (non-empty, placeholder parity, a full round trip) plus real rendered-page assertions, which are the direct behavioural proof of what a user actually sees"
    - "An 'X never imports Y' source-boundary check becomes a fresh-interpreter subprocess (child_env() + sys.modules inspection) instead of grepping the checked module's own source lines for a forbidden import string"

key-files:
  created: []
  modified:
    - companion/test_contrast_check.py
    - companion/test_i18n.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_contrast_check.md
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_i18n.md

key-decisions:
  - "test_contrast_check.py's Section 2 'muted detail text' pair (a color-mix() composite, not a raw custom property) is computed from live tokens via a local alpha-blend helper rather than kept as a pinned literal — ties the check to both the real declared CSS (the color-mix percentage is read via declarations_for()) and the real tokens, with no hard-coded hex duplicating either"
  - "test_i18n.py's D-08 Checks 1/2/5/6 (ast/regex completeness, dead-translation, attribute-literal and JS-fallback scans of production .py/.js source) are deleted rather than rewritten: each has no way to observe 'every user-visible string is translated' without reading source text, which is exactly what TST-12 retires. Replaced by 3 new catalogue-shape tests (non-empty values, placeholder parity, a full t_lang() round trip) plus the already-existing real French page renders"
  - "test_i18n.py's French-render checks get their own local module-scoped InProcessAppServer fixture (built with tmp_path_factory, mirroring companion/conftest.py's own app_server_in_process implementation) rather than a function-scoped fixture per check — all 9 render checks are read-only GETs (the one POST, to /settings/calendar/disconnect, is the two-step confirmation page and never mutates state on a bare POST), so sharing one server across the module is safe and avoids 9 server startups for what is effectively one behavioural contract"

patterns-established:
  - "Every later CSS-token migration plan (any check currently pinning a hex literal that duplicates a --color-* custom property) can reuse this plan's served_css/theme_tokens fixture pattern verbatim rather than inventing its own"

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-09-24
---

# Phase 33 Plan 04: Contrast-Check and i18n on Pytest, Behaviour Over Source Text Summary

**Rewrote the two smallest companion harnesses (73 checks total) as native pytest modules: WCAG contrast/signal-separation now measured against colour tokens fetched from a running server instead of hard-coded hex literals, and the i18n catalogue's completeness proven by catalogue self-consistency plus real French page renders instead of four ast/regex scans over production source.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-24T09:46:00Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T10:10:46Z
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 test modules rewritten in place, 2 ledger fragments filled)

## Accomplishments

- `companion/test_contrast_check.py` (524 legacy lines → a native pytest module): all 49 baseline checks ported. Formula-fidelity fixtures (8 hand-verified historical contrast numbers, plus the hue-wrap-around proof) stay hard-coded literals on purpose — they test the arithmetic, not today's stylesheet. Every live token pair (15 text-on-surface contrast checks, 12 accent/status signal-separation checks, 2 hue-separation checks, 4 superseded-colour discrimination guards, 2 UI-component-contrast sweeps, 2 login-field-border checks — 37 checks total) now reads its colour from `served_stylesheet(module_app_server_factory())` parsed with `custom_properties()`, via a module-scoped `theme_tokens` fixture, instead of a hard-coded hex literal copied from `style.css`. The one composite value (`.battery-readout__detail`'s `color-mix()` muted text) is reconstructed with a small alpha-blend helper fed the real `color-mix()` percentage read via `declarations_for()`, verified to reproduce the exact previously-pinned hex (`#5D5E62` light, `#AFB2B6` dark) bit for bit. 0 checks deleted — every one had a direct live-token equivalent. `EXPECTED_CHECK_COUNT`/`check()`/`main()` are gone; 0 `style.css` string literals remain outside route strings.
- `companion/test_i18n.py` (1289 legacy lines → a native pytest module): 20 of 24 baseline checks ported (round-trip/fallback behaviour, catalogue completeness against `common.py`/`nav.py`, value-shape, the two D-09 typographic rules, all 9 real French page/login/404/calendar-disconnect-confirm renders). The 4 ast/regex source-text completeness scans (D-08 Checks 1, 2, 5, 6 — page-module string completeness, dead-translation, attribute-literal completeness, JS-fallback-literal completeness) are deleted with reason S: none has an observable runtime consequence a behaviour test can prove without reading production source text, which is exactly what this phase retires. Their guarantee is replaced by 3 new tests — every catalogue value non-empty, every value's `%s`/`%d`/`{name}` placeholder set matching its English key's, and `t_lang()` round-tripping every one of the ~300 catalogue keys — plus the already-ported real French renders, which are the direct behavioural proof of what a user actually sees. The import-boundary check (`i18n.py`/`prefs.py` never import `companion.pages`/`server`) is rewritten as a fresh-interpreter subprocess inspecting `sys.modules`, replacing a line-by-line grep of the checked modules' own source. `companion.test_companion_app` is no longer imported anywhere in this file — the French-render checks use a module-scoped `InProcessAppServer` fixture built locally.
- Both ledger fragments filled (49/49 and 24/24, zero pending), both `LEDGER` runs exit 0 without `--allow-pending`, both files dropped out of `skypane_test_support.LEGACY_COMPANION_HARNESSES` automatically (derived from disk), the guard's per-file test passes for both (`companion/test_suite_guards.py -k "test_i18n or test_contrast_check"` → 2 passed), `ruff check` clean on both, and the full `companion test-support server stub-server` suite (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium) is unchanged at 908 passed / 2 known-and-documented root-sandbox failures (`test_companion_app`/`test_status_pages`'s legacy-harness `os.chmod`/`anomaly_active("/nonexistent/...")` checks, `33-BASELINE/INDEX.md`) / 3 skipped.

## Task Commits

1. **Task 1: rewrite test_contrast_check.py as pytest over served CSS tokens** - `7b6e0ea` (test)
2. **Task 2: rewrite test_i18n.py as pytest, catalogue behaviour over source scans** - `948c11f` (test)
3. **Task 3: guard/legacy-set/full-suite verification** - no code changes needed; verified only (see below)

## Files Created/Modified

- `companion/test_contrast_check.py` - rewritten in place as native pytest, live-token-sourced
- `companion/test_i18n.py` - rewritten in place as native pytest, catalogue-behaviour-sourced
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_contrast_check.md` - filled, 49/49 ported
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_i18n.md` - filled, 20 ported / 4 deleted

## Decisions Made

See `key-decisions` in the frontmatter above: the muted-text color-mix reconstruction, the decision to delete rather than rewrite the 4 ast/regex source-scan checks, and the module-scoped `InProcessAppServer` fixture for the French-render checks.

## Deviations from Plan

None — plan executed exactly as written. Task 3 required no code changes: the guard, the disk-derived legacy set and the shim's consistency test all already worked correctly against the two newly-migrated modules without any edit, because 33-03 built them to derive their scope from disk rather than a hand list.

## Issues Encountered

One test-writing mistake caught by the test itself, not left in a commit: the calendar-disconnect-confirm French render check initially used a plain space before `?` in its needle (`"Déconnecter le calendrier ?"`); the actual catalogue value uses U+00A0 per the D-09 non-breaking-space-before-punctuation rule this same file's own Check 4 enforces. Caught by running the test (it failed with a clear diff), fixed to `"Déconnecter le calendrier ?"`, re-verified against the original legacy file's own byte sequence (`git show HEAD~1:companion/test_i18n.py | cat -A`) to confirm exact parity before re-running green.

## User Setup Required

None.

## Next Phase Readiness

- This is the first harness migration to land end to end in this phase, proving the fixture/markup-toolkit/guard/ledger workflow from 33-01/33-02/33-03 holds for a real check-by-check port: both modules are green, both ledger fragments close with zero pending, the guard scans both without any exemption, and the legacy set shrank automatically with no hand-list edit.
- The `served_css`/`theme_tokens` module-scoped fixture pattern in `test_contrast_check.py` is directly reusable by any later plan that needs to assert on a live CSS custom property instead of a hard-coded hex literal.
- No blockers for 33-05 onward. `companion/test_companion_app.py` (33-05 through 33-18's chain) is untouched by this plan and still legacy.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk (`companion/test_contrast_check.py`,
`companion/test_i18n.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_contrast_check.md`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_i18n.md`,
this summary), and both commit hashes (`7b6e0ea`, `948c11f`) found in
`git log --oneline --all`.
