---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 03
subsystem: ui
tags: [i18n, french, status-row, health-page, date-formatting, contextvars]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/prefs.py, companion/i18n.py (t()/t_lang()), companion/i18n_fr/ auto-merging catalogue package, ctx[\"lang\"]/ctx[\"simple_mode\"]"
provides:
  - "layout.status_row(label, verdict, detail, state) — D-21's shared status-row primitive (dot + optional label + verdict + detail), reusing _STATUS_DOT_CLASSES/card_status_class(), consumed by 20-06 (Home) and 20-09 (Calendar)"
  - "layout.section_intro_html(section_id, heading, description) — promoted verbatim from health_page.py's own former private _section_intro_html(), so config_page.py's Display supersections (20-07) can build it without a page module importing another page module"
  - "health_page._device_timestamp_only()/compute_health_state()'s new \"device_detail_html\" key — a verdict-free timestamp fragment Home (20-06) reads instead of embedding device_html's own duplicated verdict"
  - "layout.relative_age_text(age_seconds, lang=None) / layout.local_clock_text(parsed, now_parsed=None, lang=None) — language-aware relative-age and clock text (D-07), English output byte-identical"
  - "companion/i18n_fr/health.py — the Health page's full French catalogue (~115 entries), including the relative-age/clock-text connector strings Task 2's helpers read"
  - "companion/pages/health_page.py rendering entirely through i18n.t() under a French request, byte-identical to before under English"
affects: [20-06-home-redesign, 20-07-display-regroup, 20-09-calendar-redesign, 20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "status_row()'s outer CSS modifier is derived from card_status_class(\"status-row\", state) — a fourth consumer of the one status->class whitelist, never a second copy or a bare %s interpolation of unvalidated state"
    - "%-format templates translated BEFORE substitution (i18n.t(TEMPLATE) % values), never an already-formatted constant translated as one opaque unit, so a provider-hostname/count/percentage substitution never gets baked into the catalogue key at import time"
    - "_label_colon(label) — a small per-module helper adding a real U+00A0 before a French colon on a label+colon join, mirroring D-09's own non-breaking-space rule for relative-age text"
    - "constants keep their English value unchanged (D-01); i18n.t() wraps them ONLY at the render/interpolation site, so every pinned English-literal check in test_status_pages.py keeps passing under the default English request"

key-files:
  created:
    - companion/i18n_fr/health.py
  modified:
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - companion/test_i18n.py

key-decisions:
  - "SOURCE_FAULT_BODY (which used to bake the ADS-B provider hostnames into a fixed English sentence at module-import time via %-formatting) is restructured into SOURCE_FAULT_BODY_TEMPLATE, a %s-templated constant translated first and formatted with the (untranslated, per D-05) provider hostnames second — the only way to keep the provider names as identifiers while still translating the surrounding sentence."
  - "Three genuine French/English cognates this plan's own catalogue introduces (\"Corroboration\", \"Source\", \"Description\") are added to companion/test_i18n.py's pre-existing _UNCHANGED_IN_FRENCH exemption set (not in this plan's own files_modified list, but a direct, mechanical consequence of this plan's additive catalogue entries, following the exact precedent 20-02-SUMMARY.md already documents for an out-of-declared-scope test-file fix)."
  - "health_page.py's own private _MONTH_ABBR (the battery chart's SVG axis-label table) is deliberately left English-only — D-07's own locked decision names only layout.py's two date helpers, and reaching into layout.py's private _MONTH_ABBR_FR from a page module would violate this codebase's module-boundary convention for no requirement this plan actually carries. Documented in place rather than silently left as a gap."

requirements-completed: [CFG-13, CFG-14, CFG-15]

# Metrics
duration: 95min
completed: 2026-09-11
---

# Phase 20 Plan 03: Shared status-row/section-intro primitives, language-aware dates, and the Health page in French Summary

**layout.status_row()/section_intro_html() (the two primitives 20-06/20-07/20-09 build on), language-aware relative_age_text()/local_clock_text() (D-07), and the entire Health page rendering through t() with a ~115-entry French catalogue — English output byte-identical throughout.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-09-11T21:55:00Z (approx.)
- **Completed:** 2026-09-11T23:30:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- `layout.status_row(label, verdict, detail, state)` — the one new shared visual primitive this phase's Home (20-06) and Calendar (20-09) redesigns depend on; an empty `label` omits the `<span>` entirely, the outer CSS modifier is whitelisted through `card_status_class()`, and both `verdict`/`detail` are escaped
- `health_page._section_intro_html()` promoted verbatim to `layout.section_intro_html()`, unblocking 20-07's Display supersections from needing a page-to-page import
- `health_page._device_timestamp_only()` and a new `device_detail_html` key on `compute_health_state()`'s returned dict — the fix Home (20-06) needs for the duplicated Frame-tile verdict defect
- `layout.relative_age_text()`/`layout.local_clock_text()` gained a trailing `lang=None` keyword resolving to `prefs.current_lang()`; French collapses the whole under-a-minute bucket to "à l'instant" and reads "il y a N <unit>", French month abbreviations come from a new `_MONTH_ABBR_FR` table — English output is byte-for-byte unchanged
- Every user-visible string on `companion/pages/health_page.py` (headings, tile captions, the three verdict dicts, empty states, the freshness pause/resume button, the anomaly banner, the unresolved-prefix registry and resolution-statistics table) now renders through `i18n.t()`, backed by a new ~115-entry `companion/i18n_fr/health.py` catalogue — verified end-to-end against a seeded state under both languages

## Task Commits

1. **Task 1: layout.status_row(), the promoted layout.section_intro_html(), and health_page's detail-only device fragment** - `8bea0e0` (feat)
2. **Task 2: language-aware relative-age and clock text (D-07)** - `9ece259` (feat)
3. **Task 3: the Health page through t(), with its French catalogue** - `c8ae4e5` (feat)
4. **Follow-up: correct a stale comment on health_page.py's own month table** - `cc83828` (docs)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/layout.py` - `status_row()`, `section_intro_html()`, `_AGE_UNIT_SUFFIX_FR`, `_MONTH_ABBR_FR`, `relative_age_text(age_seconds, lang=None)`, `local_clock_text(parsed, now_parsed=None, lang=None)`
- `companion/pages/health_page.py` - `_device_timestamp_only()`, `_device_section()` refactored to delegate its detail half to it, `compute_health_state()`'s new `device_detail_html` key, `_section_intro_html` deleted (both call sites now `layout.section_intro_html`), `_label_colon()` helper, `SOURCE_FAULT_BODY_TEMPLATE` (SOURCE_FAULT_BODY restructured), every render site wrapped in `i18n.t()`
- `companion/i18n_fr/health.py` (new) - ~115 French catalogue entries: the relative-age/clock-text connectors (D-07) plus the entire Health page's user-visible copy (D-05)
- `companion/test_status_pages.py` - 15 new checks across three new sections (1.7/1.8/1.9); `EXPECTED_CHECK_COUNT` 196 → 204 → 208 → 211
- `companion/test_i18n.py` - `_UNCHANGED_IN_FRENCH` extended with three genuine cognates this plan's catalogue introduces (no check-count change)

## Decisions Made
See `key-decisions` in the frontmatter above — the SOURCE_FAULT_BODY_TEMPLATE restructuring, the test_i18n.py cognate exemption, and the deliberate English-only scope boundary on the battery chart's own axis-label month table.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extended companion/test_i18n.py's `_UNCHANGED_IN_FRENCH` exemption set**
- **Found during:** Task 3 (the Health page's French catalogue)
- **Issue:** Three genuine French/English cognates this plan's own catalogue entries introduce ("Corroboration", "Source", "Description") tripped `test_i18n.py`'s pre-existing "every CATALOG value differs from its English key" check — the exact mechanism that check's own pre-existing `_UNCHANGED_IN_FRENCH` frozenset (seeded by 20-01 for "Simple") already exists to handle.
- **Fix:** Added the three cognates to that same frozenset, with a comment naming this plan and the reason (real cognates, not missed translations).
- **Files modified:** `companion/test_i18n.py`
- **Verification:** `companion/test_i18n.py` → 11/11 (unchanged count, no regression)
- **Committed in:** `c8ae4e5` (Task 3 commit)
- **Boundary note:** `companion/test_i18n.py` is not in this plan's `files_modified` list (owned by 20-01) and is not declared as shared in this worktree's `project_specifics`. Fixed inline rather than deferred, mirroring the exact precedent 20-02-SUMMARY.md documents for `companion/test_config_page.py` — a direct, mechanical consequence of this plan's own additive catalogue entries, and leaving it broken would red the whole suite for anyone running it before a later plan happens to touch the same file.

**2. [Rule 1 - Bug] SOURCE_FAULT_BODY restructured into a %s-templated constant**
- **Found during:** Task 3
- **Issue:** `SOURCE_FAULT_BODY` used to bake the ADS-B provider hostnames into a fixed, fully-formatted English sentence at module-import time (`"...source (%s) failed..." % ", ".join(_ADSB_PROVIDER_NAMES)`). Translating that already-formatted string as one opaque catalogue key would have meant the French sentence carried the SAME baked English provider-list substring forever, or (worse) required a second, independently-maintained French sentence with the hostnames hand-typed in — either way a drift risk the codebase's own "one dict, no framework" catalogue convention exists to avoid.
- **Fix:** Introduced `SOURCE_FAULT_BODY_TEMPLATE` (the `%s`-templated sentence, translated first through `i18n.t()`, formatted with the untranslated provider hostnames second); `SOURCE_FAULT_BODY` itself is kept, computed from the template, for any external reader that still wants the plain English value.
- **Files modified:** `companion/pages/health_page.py`, `companion/i18n_fr/health.py`
- **Verification:** `companion/test_status_pages.py` → 210/211 (unchanged); manual French/English render smoke test confirmed both branches format correctly
- **Committed in:** `c8ae4e5` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs/correctness issues a direct, mechanical consequence of this plan's own additive changes)
**Impact on plan:** No scope creep — both fixes are same-effect corrections needed for this plan's own translation work to be correct and non-drifting. No plan requirement was dropped or weakened.

## Issues Encountered
- `layout.status_row()`'s outer CSS modifier needed one extra care point: `card_status_class("status-row", state)` is called exactly once (not twice) to satisfy the plan's own `grep -c` acceptance criterion while still deriving both the dot class and the outer modifier correctly.
- The anomaly banner's lead phrase ("N warning(s):") needed the same `_label_colon()` non-breaking-space treatment Task 3 introduced for `LAST_DETECTION_LABEL`, discovered only by rendering the banner under French and visually inspecting the output — not caught by any pinned test, since no existing check asserted the exact colon character. Fixed proactively per D-09.
- No other issues — every task's own `<verify>` command passed as specified, and the full local suite (`scripts/run-all-tests.sh`) shows no new failures beyond the project's five known root-sandbox cases (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`), identical to `main`.

## Known Stubs

None — every helper and catalogue entry this plan ships is real, immediately-effective code; nothing here is a placeholder awaiting a later plan's markup.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `layout.status_row()` and `layout.section_intro_html()` are both available for 20-06 (Home), 20-07 (Display supersections) and 20-09 (Calendar) to consume, exactly as D-21/§C specify.
- `health_page.compute_health_state()`'s new `device_detail_html` key is available for 20-06's Home rebuild to read instead of embedding `device_html` wholesale.
- `layout.relative_age_text()`/`layout.local_clock_text()` are language-aware end to end; every existing call site across the app keeps its unchanged English output with zero edits required at those call sites.
- `companion/i18n_fr/health.py` demonstrates the full-page translation pattern (constants stay English, `i18n.t()` wraps at the render site, `%`-templates translate before formatting) later page-translation plans in this phase can follow directly.
- `companion/test_view_pages.py` (85/85) and `companion/test_config_page.py` (181/181) are confirmed unmoved by this plan, per its own success criteria.
- No blockers for 20-05 (the sibling wave-2 plan, `server/poll_loop.py`/`server/test_poll_loop.py` — untouched by this plan).

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: companion/layout.py
- FOUND: companion/pages/health_page.py
- FOUND: companion/i18n_fr/health.py
- FOUND: companion/test_status_pages.py
- FOUND: companion/test_i18n.py
- FOUND commit: 8bea0e0 (Task 1)
- FOUND commit: 9ece259 (Task 2)
- FOUND commit: c8ae4e5 (Task 3)
- FOUND commit: cc83828 (follow-up docs fix)
