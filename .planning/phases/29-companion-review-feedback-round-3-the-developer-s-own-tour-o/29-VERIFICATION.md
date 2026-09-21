---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
verified: 2026-09-21T23:51:29Z
status: human_needed
score: 9/9 must-haves verified (code-level); 3 items present-but-behavior-unverified (client-side/real-browser)
behavior_unverified: 1
overrides_applied: 0
human_verification:
  - test: "On a real device with the OS region forced to a 12h locale (e.g. macOS/iOS set to United States), open /display and observe whether each quiet-hours time field's 24h twin (data-normalised-time) stays visible."
    expected: "The twin must NOT be hidden — value-controls.js's load-time pass only hides it on a strict Intl.DateTimeFormat(...).resolvedOptions().hour12 === false. Any other value (including a real 12h browser resolving something other than strict false) must leave it visible."
    why_human: "This is a client-side state transition (a script hiding a DOM element based on a runtime Intl determination). Playwright is not installed in this sandbox (test_browser_ux.py reports SKIP, confirmed by direct run), so the assertion added to it (comparing the twin's live .hidden property to the browser's resolved hour12 after a preset click) has never executed anywhere. This is exactly the false-negative risk 29-RESEARCH.md's own A1 caveat names, and 29-04-SUMMARY.md discloses it as an outstanding follow-up rather than claiming it closed."
  - test: "On Compagnies, open a known airline's illustration dialog with no query string in the URL; confirm Replace renders and the resolve-context block (prefix/first-seen/last-seen/count/example callsign) does not. Repeat for a manually-resolved entry to confirm Delete also appears."
    expected: "Replace (and Delete for manual entries) present; resolve-context block absent on an ordinary art card, in both languages, with and without scripts."
    why_human: "The visibility split is decided client-side by panel-lookup.js's existing mode/manual attribute reads at click time; a Python harness can only prove both forms are always present in the served markup, not that the script toggles them correctly per real click (29-01-SUMMARY.md Human Follow-ups)."
  - test: "On 360px and 390px viewports, in French and English, confirm the mobile tab bar renders 'Compagnies' whole with no ellipsis (console: [...document.querySelectorAll('.tab-bar__label')].map(e => [e.textContent, e.scrollWidth, e.clientWidth]), no label may have scrollWidth > clientWidth), and that Compagnies' filter + first gallery row are visible without scrolling past the unidentified-prefix list."
    expected: "No truncation at either reference width; gallery reachable without scrolling past secondary content."
    why_human: "No playwright in this sandbox — the audit's original P1 evidence was a real-browser scrollWidth measurement, which 29-02's own check reproduces only arithmetically from the stylesheet's declared tokens, not by rendering (29-02-SUMMARY.md Human Follow-ups)."
  - test: "On a 390px viewport with the realistic 36-flight fixture, re-measure Vols' rendered page height and report it against 3,355px (half of the 2026-09-17 audit's 6,710px baseline); separately, open 'Afficher plus', wait one 45-second freshness.js refresh cycle, and confirm the list stays expanded with the link now offering the next page; and with JavaScript disabled, confirm the Show-more link still reveals more flights."
    expected: "Measured height materially below the audit's baseline; expanded state survives the live refresh cycle; reveal works with scripts off."
    why_human: "No browser/playwright available in this sandbox to execute the actual fetch()/DOMParser swap cycle or measure a rendered page's real height; 29-03's own checks prove the structural half only (byte-identical re-render at a fixed URL, the declared swap region, the anchor's markup) — the live half is a named, undischarged follow-up in 29-03-SUMMARY.md."
gaps: []
deferred: []
---

# Phase 29: Companion Review Feedback Round 3 Verification Report

**Phase Goal:** Ship the remaining six cases from the developer's 2026-09-21 tour (CFG-79 through CFG-84), folding in three leftover 2026-09-17-audit items the developer selected — Compagnies label truncation + gallery order, Vols paginated, État's title — with the 44px tap-target item explicitly out of scope.
**Verified:** 2026-09-21T23:51:29Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CFG-81: illustration dialog owns its own actions — Replace/Delete render unconditionally in the dialog; page-wide `edit_mode`/toggle removed entirely | ✓ VERIFIED | `grep -rn "edit_mode\|EDIT_QUERY_PARAM" companion/` returns zero executable hits (only historical comments); `_lightbox_html()`'s Replace/Delete forms confirmed unconditional in `companion/pages/airlines_page.py`; full suite green (`test_view_pages.py` 169/169, `test_status_pages.py` 316/316) |
| 2 | CFG-82: Compagnies reads gallery-first; mobile tab label never truncates | ✓ VERIFIED | `.tab-bar__pill` margin confirmed at `calc(var(--space-xs) / 2)` (style.css:10542, with dated comment); `render()` order confirmed via passing section-order relationship check in `test_view_pages.py` |
| 3 | CFG-83: Vols paginated to 15, real no-JS Show-more, filter always above the list, stable phone grid, hostile `?limit=` cannot raise or over-fetch | ✓ VERIFIED (code level) | Read `flights_limit()` directly — total function, clamps into `[15,50]`, never raises; confirmed `render()` slices `visible_rows` at line 1771 *before* the per-row enrichment loop (line 1779) and both card list and table consume the same sliced list; `.flights-more` mirrored identically in `layout.py` and `freshness.js` (both greps show one hit each) |
| 4 | CFG-80: Quiet hours is one visual object at ≥480px; 24h twin hidden only on a strict positive determination, visible otherwise; four surfaces still agree | ✓ VERIFIED (layout/markup); ⚠️ twin's runtime hide/show is PRESENT_BEHAVIOR_UNVERIFIED | `@media (max-width: 479.98px)` fallback confirmed present in style.css:3040-3044, matching REQUIREMENTS.md's own qualified claim exactly; the JS hide mechanism (`value-controls.js`) is a real state transition never exercised by any executable test in this sandbox — see Human Verification |
| 5 | CFG-84: État's battery-trend heading is short and fixed; precision moves to a sibling caption | ✓ VERIFIED | Live-rendered `_battery_trend_section_html()` directly: produces `<h2 class="text-heading">Battery · 3 months</h2><p class="text-label section-caption">Latest 5 readings</p>` — confirmed by direct interpreter call, not by trusting the SUMMARY |
| 6 | CFG-79: whole site (except Display's Aspect, Phase 30's) meets a 12-word editorial floor; apply-timing sentence confined to the Frame strip | ✓ VERIFIED | Independent script scanning every `*CAPTION*` constant in `config_page.py` against the exemption tuple found zero violations >12 words; full site-wide check (`test_companion_app.py`) passes at 317/317, confirmed by direct run |
| 7 | CR-01 (review fix): Show-more anchor now has a real CSS rule matching its emitted `<a>` tag, not merely a class-string substring | ✓ VERIFIED | Read `_show_more_html()` (history_page.py:1698, emits `<a class="calendar-disconnect-btn">`) and the corresponding `a.calendar-disconnect-btn` rule (style.css:9788-9803) side by side — a real tag-matching selector, not the old `button.`-qualified one; independently re-ran the mutation (deleted the `a.calendar-disconnect-btn` block, reran `test_view_pages.py`, watched it drop to 168/169 with the exact expected failure, then restored the file with a clean `git diff`) |
| 8 | WR-01 (review fix): orphaned `.airline-card .calendar-disconnect-btn` rule + stale comment removed | ✓ VERIFIED | `grep -n calendar-disconnect-btn companion/static/style.css` shows no `.airline-card .calendar-disconnect-btn` selector anywhere; only a historical comment recording its removal remains |
| 9 | WR-02 (review fix): CFG-80's REQUIREMENTS.md row states its real ≥480px threshold rather than reading as unconditionally delivered | ✓ VERIFIED | REQUIREMENTS.md:257's row text ("Start and End render on one line only at ≥480px... a disclosed, correctly-derived trade-off") matches the actual `@media (max-width: 479.98px)` breakpoint in style.css exactly |

**Score:** 9/9 code-level truths verified; 1 of them (CFG-80's twin) carries a present-but-behavior-unverified runtime component; 3 additional truths (CFG-81, CFG-82, CFG-83) have real-browser/live-device confirmation still outstanding per their own SUMMARYs, honestly disclosed there rather than claimed closed.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `companion/pages/airlines_page.py` | toggle/badge/replace-control/EDIT_QUERY_PARAM deleted; render() reordered | ✓ VERIFIED | grep-confirmed zero `edit_mode`/`EDIT_QUERY_PARAM` occurrences; order check passes |
| `companion/app.py`, `companion/pages/__init__.py` | `edit_mode` ctx key removed | ✓ VERIFIED | zero occurrences outside comments |
| `companion/static/style.css` | `.tab-bar__pill` margin halved; `.quiet-times-row` two-col grid with 480px fallback; `a.calendar-disconnect-btn` added; orphaned `.airline-card .calendar-disconnect-btn` removed | ✓ VERIFIED | all four changes read directly from the file |
| `companion/pages/history_page.py` | `FLIGHTS_PAGE_SIZE`, `flights_limit()`, `_show_more_html()`, pre-loop slicing | ✓ VERIFIED | read directly; clamp function is total; slicing precedes enrichment loop |
| `companion/layout.py`, `companion/static/freshness.js` | `.flights-more` added to both swap-registry mirrors | ✓ VERIFIED | one hit each, byte-identical selector string |
| `companion/pages/config_page.py` | segmented presets, `.quiet-times-row`, `ASPECT_CAPTION_EXEMPTIONS`, shortened captions | ✓ VERIFIED | `ASPECT_CAPTION_EXEMPTIONS` present; independent word-count scan of all `*CAPTION*` constants found 0 violations |
| `companion/pages/health_page.py` | `BATTERY_SECTION_HEADING_TEMPLATE`, heading+sibling-caption composition | ✓ VERIFIED | live-rendered and inspected directly |
| `companion/static/value-controls.js` | strict `hour12 === false` gate for the twin | ✓ VERIFIED (static); ⚠️ runtime path unexercised | code inspected; no test in this sandbox can run it |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `history_page._show_more_html()` | `style.css` | class `calendar-disconnect-btn` on an `<a>` | ✓ WIRED | `a.calendar-disconnect-btn` selector genuinely matches the rendered tag (verified by direct read + independent mutation) |
| `layout.REFRESH_SWAP_SELECTORS_BY_PAGE` | `freshness.js SWAP_SELECTORS_BY_PAGE` | `.flights-more` mirror entry | ✓ WIRED | both files carry the identical literal |
| `config_page.ASPECT_CAPTION_EXEMPTIONS` | `test_companion_app.CAPTION_FLOOR_EXEMPTIONS` | direct import, not re-listed | ✓ WIRED | confirmed via source read (`CAPTION_FLOOR_EXEMPTIONS = config_page.ASPECT_CAPTION_EXEMPTIONS`) |
| `value-controls.js` load-time pass | `.field-inline-value[data-normalised-time]` | `hidden` attribute toggle on strict `hour12 === false` | ⚠️ WIRED, runtime unverified | code path is present and internally consistent; no browser available in this sandbox to observe it fire |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CR-01's selector-vs-tag check is non-vacuous | Deleted `a.calendar-disconnect-btn` block from style.css, reran `test_view_pages.py`, restored the file | 168/169 (exact expected failure message), then 169/169 after restore, `git diff` clean | ✓ PASS |
| `edit_mode`/`EDIT_QUERY_PARAM` genuinely have zero surviving references | `grep -rn` across `companion/` | 0 executable hits (comments only) | ✓ PASS |
| Orphaned `.airline-card .calendar-disconnect-btn` genuinely removed | `grep -n calendar-disconnect-btn companion/static/style.css` | no such selector present | ✓ PASS |
| CFG-84 heading/caption split renders as claimed | Direct interpreter call to `health_page._battery_trend_section_html()` | `<h2>Battery · 3 months</h2><p class="section-caption">Latest 5 readings</p>` | ✓ PASS |
| CFG-79 editorial floor holds independent of the harness's own counting rule | Standalone word-count scan of every `*CAPTION*` constant in `config_page.py` against `ASPECT_CAPTION_EXEMPTIONS` | 0 violations found | ✓ PASS |
| CFG-83 pagination clamp is total | Read `flights_limit()` source; traced all branches | No branch can raise; every path returns an int in `[15,50]` | ✓ PASS |
| Full test suite, run once, this session | `PYTHON=server/.venv/bin/python3 scripts/run-all-tests.sh` | `Result: PASS` — all 22 harnesses green, including `companion-app: 317/317`, `view-pages: 169/169`, `status-pages: 316/316`, `config-page: 274/274`; `test_browser_ux.py` reports SKIP (playwright absent), never counted as a pass | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CFG-79 | 29-05, 29-06 | Site-wide 12-word editorial floor, apply-timing confined to Frame strip | ✓ SATISFIED | Verified live; REQUIREMENTS.md checklist row (line 105) marked `[x]` |
| CFG-80 | 29-04 | Quiet hours as one object at ≥480px, twin hidden on strict 24h determination | ✓ SATISFIED (code); twin's runtime behavior human-needed | REQUIREMENTS.md row (line 106/257) accurately qualified post-WR-02 |
| CFG-81 | 29-01 | Illustration dialog owns its actions, `edit_mode` removed | ✓ SATISFIED | REQUIREMENTS.md checklist row (line 107) marked `[x]`; code verified directly |
| CFG-82 | 29-02 | Compagnies gallery-first, tab label never truncates | ✓ SATISFIED (code); real-browser confirmation outstanding | REQUIREMENTS.md checklist row (line 108) marked `[x]`; code verified directly |
| CFG-83 | 29-03 | Vols paginated, no-JS Show-more, stable phone grid | ✓ SATISFIED (code); live refresh-cycle/height confirmation outstanding | REQUIREMENTS.md checklist row (line 109) marked `[x]`; code verified directly |
| CFG-84 | 29-06 | État's battery-trend heading short, precision in sibling caption | ✓ SATISFIED | REQUIREMENTS.md checklist row (line 110) marked `[x]`; verified via direct render |

**Documentation gap found (not a code defect):** REQUIREMENTS.md's "Requirements Coverage" traceability table (the second table, further down the file) still reads "Pending — phase added 2026-09-21... not yet planned" for CFG-79, CFG-81, CFG-82, CFG-83 and CFG-84 (lines 256, 258-261) — directly contradicting the checklist immediately above it (lines 105-110), which is correctly marked `[x]` complete with detailed, accurate descriptions for all six items. Only CFG-80's traceability row (line 257) was updated, by the review-fix pass's WR-02 fix, which was scoped to that one item. The checklist (the item this project's own convention treats as the authoritative per-requirement record) is accurate; the second table simply was never refreshed for the other five items across any of the six plans' closing commits. This does not affect the shipped functionality — the six CFG items are all genuinely implemented and tested — but it is a real staleness gap a future reader cross-referencing only the traceability table would be misled by. Recommend a follow-up doc-only commit updating REQUIREMENTS.md lines 256/258/259/260/261 to match the checklist.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX` markers in any of the 15 files this phase touched. No `TODO`/`HACK`/`PLACEHOLDER` hits beyond legitimate HTML `placeholder` attribute constants (`WAKE_INTERVAL_PLACEHOLDER_TEXT`, `RULE_VALUE_PLACEHOLDER`) that predate and are unrelated to this phase. No stub returns, no hardcoded-empty props feeding rendering.

### Code Review Findings (29-REVIEW.md / 29-REVIEW-FIX.md) — Re-Verified

| Finding | Fix Commit | Re-Verification |
|---------|-----------|------------------|
| CR-01 (Critical): Show-more anchor rendered with no button styling — `button.calendar-disconnect-btn` selector element-type-qualified, never matches an `<a>` | `7d48aec` | ✓ Confirmed fixed — `a.calendar-disconnect-btn` rule genuinely matches the emitted tag; independently mutation-tested this session |
| WR-01 (Warning): orphaned `.airline-card .calendar-disconnect-btn` CSS + stale 15-line comment | `772fb11` | ✓ Confirmed fixed — no such selector remains, only a historical removal note |
| WR-02 (Warning): CFG-80's REQUIREMENTS.md row read as unconditionally delivered when the fix only holds ≥480px | `b140c33` | ✓ Confirmed fixed — the row's stated threshold matches the actual CSS breakpoint exactly |
| IN-01 (Info, skipped by design): no standing check verifies a reused CSS class paints the element type it's applied to | Skipped, explicitly out of scope (`fix_scope: critical_warning`) | Correctly recorded as skipped, not silently dropped |

### Human Verification Required

See frontmatter `human_verification` for the structured list. Summary:

1. **CFG-80's 24h-twin hide/show mechanism** — a genuine client-side state transition (`Intl.DateTimeFormat(...).resolvedOptions().hour12 === false` gate) that no test in this sandbox can execute (playwright absent, `test_browser_ux.py` SKIPs). This is a present-but-behavior-unverified item, not merely a "nice to confirm" — a false negative here would reopen the exact defect B14 was built to prevent.
2. **CFG-81's dialog click behavior in a real browser** — the Replace/Delete visibility split is decided client-side by `panel-lookup.js` at click time; only the served-markup half (both forms always present) is proven here.
3. **CFG-82's tab-bar fit at 360px/390px in a real browser** — proven arithmetically from stylesheet tokens and the audit's own measured advance factor, not by an actual `scrollWidth` measurement (no playwright).
4. **CFG-83's live page height and 45-second refresh-survival** — proven structurally (byte-identical re-render at a fixed URL, the declared swap region, a real HTTP round trip against a running service) but the actual browser fetch()/DOMParser swap cycle and the real rendered height at 390px are undischarged.

### Gaps Summary

No functional gaps found. All six requirements (CFG-79 through CFG-84) are genuinely implemented, wired, and covered by a passing automated suite (re-run in full this session: `PASS`, 22/22 harnesses green). The three code-review findings from 29-REVIEW.md were independently re-verified as correctly fixed, including one independent mutation test reproducing CR-01's non-vacuity proof from scratch. The only gaps are: (a) a documentation staleness issue in REQUIREMENTS.md's traceability table (five rows never refreshed, contradicting the accurate checklist above them — non-blocking, doc-only), and (b) a cluster of human-verification items that every relevant SUMMARY already disclosed honestly as outstanding rather than claiming closed (real-device 12h-locale confirmation, live-browser click/visual confirmations, live page-height/refresh-cycle measurement) — none of which is silently hidden, all of which route here as required.

---

_Verified: 2026-09-21T23:51:29Z_
_Verifier: Claude (gsd-verifier)_
