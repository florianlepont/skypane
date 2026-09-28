---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 13
subsystem: i18n
tags: [i18n, translation, python, stdlib]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: companion.i18n.Message/msg()/REGISTRY, companion.i18n_fr.BY_ID, test-support/i18n_ids.py (40-12)
provides:
  - Home, Flights, Airlines and Health pages fully migrated onto companion.i18n.Message stable ids
  - companion/i18n_fr/home.py, flights.py, airlines.py and health.py fully converted to id-keyed MESSAGES (zero residual CATALOG)
  - companion/i18n_fr/registry.py partially converted (the three runway-label entries only; theme names and the screen label stay legacy CATALOG, documented below for 40-14)
  - Cross-area ids this plan assigned for strings whose French still lives in a 40-14-owned catalogue (display.py, rules.py), so 40-14's own migration derives the identical id
affects: [40-14, 40-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "An AST-span replacement codemod (parse the legacy CATALOG dict, replace only each key node's exact source span with its computed id, byte-offset-aware for UTF-8 multi-byte characters) converts a large hand-written catalogue module to MESSAGES while preserving every comment and the exact French text byte-for-byte — used for health.py's 130-entry catalogue, verified against the pre-migration values programmatically rather than by eye"
    - "A catalogue module may convert only part of its CATALOG to MESSAGES when some entries have no in-scope module to declare their Message yet (registry.py: runway labels convert now since history_page.py is in-scope; theme names and the screen label stay CATALOG since only the not-yet-migrated config_page.py/settings/*.py read them)"

key-files:
  created: []
  modified:
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/pages/health_page.py
    - companion/health_signals.py
    - companion/battery_chart.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/flights.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/registry.py
    - companion/i18n_fr/health.py
    - companion/test_i18n.py
    - companion/test_view_pages_02.py
    - companion/test_view_pages_03.py
    - companion/test_view_pages_04.py
    - companion/test_status_pages_04.py
    - companion/test_status_pages_05b.py

key-decisions:
  - "registry.py converts only the three runway-label entries to MESSAGES this plan (history_page.py declares their Message); the eighteen theme-name entries and the one screen-label entry stay legacy CATALOG, since their only reader (config_page.py, companion/settings/*.py, companion/screens.py) is 40-14/40-15 territory untouched here — acceptance criteria explicitly allow this residual, documented in the module's own docstring"
  - "Several strings are shared across areas via the pre-existing flat CATALOG namespace (e.g. 'Departing'/'Arriving' used by both Home and Flights, owned by home.py; 'Corroboration'/'Prefix'/'First seen'/'Last seen'/'Example callsign' used by Flights/Airlines/Health, owned by health.py; 'Flight'/'Aircraft' used by Flights, owned by rules.py; 'Runway'/'Callsign'/'Delete' used by Flights/Airlines, owned by display.py). Each is declared with the id its owning catalogue's own migration will independently derive via the shared slug_for() rule — msg() is idempotent on a repeat (id, English) pair, so declaring the same id from two source modules (e.g. history_page.py and airlines_page.py both declaring 'health.close'... a similar id) never conflicts"
  - "Two constants that were never actual catalogue entries (history_page.py's CHECK_IN_CELL_TITLE_NONE analogue does not exist here, but health_page.py's own bare '%s — %s' join) stay plain str, un-migrated: they never carried translatable words of their own"
  - "test_i18n.py's two plain-str/legacy-fallback fixtures ('Status'/home.py and 'Screen'/health.py) broke once this plan fully migrated their owning catalogues — moved to 'Cancel'/'Settings' (both still-legacy display.py entries, 40-14 territory), matching 40-12's own precedent for keeping these tests dependency-free of any particular page module's import order"

patterns-established:
  - "AST key-span replacement for large catalogue conversions: parse the CATALOG dict, compute each key's byte-offset span (col_offset is UTF-8 byte offset, not codepoint offset — must work in bytes, not str, when the source has any non-ASCII character), replace only that span with the new quoted id, verify byte-for-byte value equality against the pre-migration dict programmatically before trusting the result"

requirements-completed: [CMP-09]

# Metrics
duration: unknown (long single session)
completed: 2026-09-27
---

# Phase 40 Plan 13: Stable message IDs (i18n, part 2 of 4) Summary

**Migrated the Home, Flights, Airlines and Health page modules (including the battery chart and health-signals modules) onto `companion.i18n.Message` stable ids, fully converting four of the five owned French catalogues (home/flights/airlines/health, 241 entries total) to ID-keyed `MESSAGES` and partially converting the fifth (registry.py's three runway labels), with every rendered page verified byte-identical to the pre-migration baseline.**

## Performance

- **Duration:** unknown — long single session, no reliable start timestamp
- **Completed:** 2026-09-27
- **Tasks:** 2/2
- **Files modified:** 17 (11 in Task 1, 8 in Task 2, 2 overlapping test files touched in neither task's own file list but required by the migration — see Deviations)

## Accomplishments
- `companion/pages/home_page.py`, `history_page.py` and `airlines_page.py` fully converted: every module constant and every inline `i18n.t("literal")` call site hoisted to a named `i18n.msg(id, english)` Message
- `companion/i18n_fr/home.py` (33 entries), `flights.py` (36), `airlines.py` (42) fully converted from `CATALOG` to `MESSAGES`, every French value verified byte-for-byte identical to the pre-migration catalogue via a scripted comparison (not by eye)
- `companion/i18n_fr/registry.py`'s three runway-label entries converted to `MESSAGES` (history_page.py declares their Message); its eighteen theme-name entries and one screen-label entry stay legacy `CATALOG`, since config_page.py/settings/*.py/screens.py (40-14/later territory) are the only readers and are untouched this plan
- `companion/pages/health_page.py`, `health_signals.py` and `battery_chart.py` fully converted: 79 + 11 + 4 call sites, including four dict-valued state-text tables (`DEVICE_STATE_TEXT`, `PIPELINE_STATE_TEXT`, `CORROBORATION_STATE_TEXT`, `CHECK_IN_STATE_TEXT`) and two multi-field tuples (`_CORROBORATION_ROWS`, `_SOURCE_ROWS`)
- `companion/i18n_fr/health.py` (130 entries) fully converted from `CATALOG` to `MESSAGES` via an AST key-span replacement codemod that preserves every comment and every French value byte-for-byte, verified programmatically
- Every cross-area string (an English text owned by one catalogue but consumed by a page this plan converts) declared with the id that catalogue's own future migration will independently derive — the same idempotent-`msg()` pattern 40-12 established
- Full test suite green: 3213 passed (one pre-existing, unrelated browser-test failure logged in `deferred-items.md`, confirmed to reproduce identically before this plan's own changes); `test_render_baseline.py` (byte-identical HTML in both languages, all pages) passes

## Task Commits

1. **Task 1: Home and Flights/Airlines pages with the home, flights, airlines and registry catalogues** - `f7d501e` (refactor)
2. **Task 2: Health page, chart and signals with the health catalogue** - `512c936` (refactor)

**Plan metadata:** _pending — this commit_

## Files Created/Modified

- `companion/pages/home_page.py` - every constant/inline literal hoisted to `i18n.msg()`, including cross-area reuses (`nav.home`, `flights.today`, `flights.no_reading_yet`, four `health.*` state-text ids)
- `companion/pages/history_page.py` - every constant/inline literal hoisted, including a local `_RUNWAY_LABEL_MESSAGES` dict wrapping `device_config.runway_label()`'s three known return values, and cross-area declarations for `rules.flight`, `health.corroboration`, `home.departing`/`home.arriving`, `display.runway`/`display.callsign`
- `companion/pages/airlines_page.py` - every constant/inline literal hoisted, including cross-area declarations for `home.illustration`, `display.delete`, `health.*` resolve-context labels, `nav.airlines`
- `companion/pages/health_page.py` - every constant/inline literal hoisted across ~1700 lines, including the four state-text dicts, `_CORROBORATION_ROWS`/`_SOURCE_ROWS` tuples, and `_REGISTRY_HEADERS`
- `companion/health_signals.py` - the ten anomaly/caption strings hoisted to module constants
- `companion/battery_chart.py` - the four battery-readout templates hoisted to module constants
- `companion/i18n_fr/home.py` - fully migrated to `MESSAGES` (33 entries); three entries needed their lost non-breaking space (U+00A0 before `;`/`:`) restored after the initial rewrite (see Deviations)
- `companion/i18n_fr/flights.py` - fully migrated to `MESSAGES` (36 entries)
- `companion/i18n_fr/airlines.py` - fully migrated to `MESSAGES` (42 entries)
- `companion/i18n_fr/registry.py` - partially migrated: three runway-label entries to `MESSAGES`, eighteen theme names plus the screen label stay `CATALOG`
- `companion/i18n_fr/health.py` - fully migrated to `MESSAGES` (130 entries) via the AST-span codemod
- `companion/test_i18n.py` - two fixtures moved off "Status"/"Screen" (now migrated) onto "Cancel"/"Settings" (still legacy `display.py`); the `_UNCHANGED_IN_FRENCH` cognate allowlist updated for three health.py ids that replaced their English-keyed predecessors
- `companion/test_view_pages_02.py`, `test_view_pages_03.py`, `test_view_pages_04.py` - three catalogue-completeness tests and one full-render test reached into `i18n_fr.<module>.CATALOG` directly; guarded with `getattr(..., "CATALOG", {})` plus a `MESSAGES`/`BY_ID` counterpart, matching 40-12's own fix for `nav.py`
- `companion/test_status_pages_04.py`, `test_status_pages_05b.py` - same `CATALOG`-reaches-directly pattern for health.py, fixed the same way

## Decisions Made

- **registry.py's residual CATALOG is intentional and matches the plan's own acceptance criteria** ("or the SUMMARY lists each residual English-keyed entry and the module that alone uses it"). The eighteen theme names (White/Black/.../Band Red Field) and "Plane frame" have no in-scope declaring module this plan — `device_config.theme_label()` is read only by `companion/settings/calendar.py`/`rules.py`/`theme.py`, and `screens.py`'s screen label only by `config_page.py`, all 40-14 territory. They will convert when 40-14 migrates those readers.
- **Cross-area ids declared this plan for 40-14-owned catalogues** (using `test-support/i18n_ids.slug_for()`, so 40-14's own migration derives the identical id — see table below).
- **AST byte-span codemod for health.py's 130-entry catalogue**, rather than hand-retyping: `ast.col_offset`/`end_col_offset` are UTF-8 *byte* offsets, not codepoint offsets, so the replacement script worked on the raw file bytes (not the decoded str) to stay correct across the catalogue's many multi-byte French/typographic characters (’, —, ≈, U+00A0). Verified every resulting French value byte-for-byte equal to the pre-migration `CATALOG` dict programmatically before trusting the output.
- **A handful of test files outside this plan's own file list needed fixing** (`test_i18n.py`, `test_view_pages_02/03/04.py`, `test_status_pages_04.py`, `test_status_pages_05b.py`) because they reached into `i18n_fr.<module>.CATALOG` by attribute access — a direct consequence of this plan's own catalogue migration, so treated as Rule 1 bugs (see Deviations), not scope creep.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lost non-breaking space in three re-typed home.py French values**
- **Found during:** Task 1's own verify step (`test_render_baseline.py`)
- **Issue:** Manually rewriting `companion/i18n_fr/home.py` as a fresh `Write` (rather than an AST-span codemod, used only for health.py) dropped the U+00A0 non-breaking space before `;`/`:` in three entries ("Le serveur conserve une copie... cadre ; la plus récente...", "Certaines marques sont fusionnées : ...", "Zone grisée : heures calmes...") — a plain ASCII space was typed instead, invisible in the diff at a glance.
- **Fix:** Restored the ` ` escape at all three sites; verified every one of home.py's 33 entries byte-for-byte against the pre-migration catalogue programmatically, and confirmed with `test_render_baseline.py`.
- **Files modified:** companion/i18n_fr/home.py
- **Verification:** `test_render_baseline.py` passes; scripted byte-equality sweep over all four Task-1 catalogues reports 0 mismatches
- **Committed in:** f7d501e (Task 1 commit)

**2. [Rule 1 - Bug] Three catalogue-completeness tests reached `i18n_fr.<module>.CATALOG` directly**
- **Found during:** Task 1's own verify step, after converting home/flights/airlines fully to `MESSAGES`
- **Issue:** `test_airlines_catalog_keys_all_present_in_merged_catalog`, `test_flights_catalog_keys_all_present_in_merged_catalog`, `test_home_catalog_keys_all_present_in_merged_catalog` (one per page's own test file) and `test_airlines_full_seeded_render_french_end_to_end`'s one needle all accessed `i18n_fr_<module>.CATALOG`, which no longer exists once each module exports only `MESSAGES`.
- **Fix:** Guarded each completeness check with `getattr(..., "CATALOG", {})` plus a parallel `MESSAGES`/`BY_ID` check (matching 40-12's own fix for `nav.py`); the render-test needle switched to `i18n_fr_airlines.MESSAGES[airlines_page.GAP_STRIP_BODY.msg_id]`.
- **Files modified:** companion/test_view_pages_02.py, companion/test_view_pages_03.py, companion/test_view_pages_04.py
- **Verification:** full Task 1 verify suite green (224 passed)
- **Committed in:** f7d501e (Task 1 commit)

**3. [Rule 1 - Bug] Two test_i18n.py fixtures broke once home.py/health.py fully migrated**
- **Found during:** Task 1 and Task 2's own verify steps
- **Issue:** `test_t_lang_fr_translates_a_known_key`/`test_t_lang_en_returns_the_english_source`/`test_t_follows_set_request_prefs_and_back` used the plain string "Status" (home.py, previously legacy) as a dependency-free translatable fixture; `test_t_lang_message_with_no_by_id_entry_falls_back_to_legacy_catalog` used "Screen" (health.py) for the same reason. Both catalogues fully migrated this plan, so both fixtures now require some other module's import to have registered the id first — exactly the dependency test_i18n.py's own minimal import set is designed to avoid (per 40-12's precedent comment).
- **Fix:** Moved both fixtures to "Cancel"/"Settings" (companion/i18n_fr/display.py, still fully legacy since display.py is 40-14 territory) — no import-order dependency, matching the original test's own intent.
- **Files modified:** companion/test_i18n.py
- **Verification:** full suite green after each fix
- **Committed in:** f7d501e (Task 1), 512c936 (Task 2, `_UNCHANGED_IN_FRENCH` allowlist update)

**4. [Rule 1 - Bug] Two health.py catalogue-completeness tests reached CATALOG directly**
- **Found during:** Task 2's own verify step
- **Issue:** `test_health_catalog_every_key_and_value_is_a_nonempty_str` (test_status_pages_05b.py) and `test_registry_table_fits_by_stacked_cells_and_short_french_headers`'s three health.py CATALOG lookups (test_status_pages_04.py) broke once health.py exported only `MESSAGES`.
- **Fix:** Same `getattr(..., "CATALOG", {})` guard plus a `MESSAGES` counterpart for the first; the second switched its three lookups to `i18n_fr_health.MESSAGES.get("health.first_seen")`/`"health.last_seen"`/`.values()`. The fourth assertion in that test (`health_page._REGISTRY_HEADERS[2:4] == ("First seen", "Last seen")`) needed no change: `Message` subclasses `str`, so the tuple equality still holds against plain-string operands.
- **Files modified:** companion/test_status_pages_05b.py, companion/test_status_pages_04.py
- **Verification:** both tests pass; full suite green (3213 passed)
- **Committed in:** 512c936 (Task 2 commit)

**5. [Rule 1 - Bug] `test_every_catalog_value_is_str_and_differs_from_its_english_key`'s cognate allowlist was keyed by English text**
- **Found during:** Task 2's own verify step, after fully migrating health.py
- **Issue:** `_UNCHANGED_IN_FRENCH` listed `{"Corroboration", "Source", "Description", ...}` — legitimate French/English cognates. Once health.py migrated, the sweep's identifier for these entries became their stable id (`health.corroboration`, `health.source`, `health.description`), no longer matching the English-keyed allowlist entries.
- **Fix:** Replaced the three English-keyed entries with their new ids in the frozenset, per the test's own already-anticipating docstring.
- **Files modified:** companion/test_i18n.py
- **Verification:** `test_every_catalog_value_is_str_and_differs_from_its_english_key` passes
- **Committed in:** 512c936 (Task 2 commit)

---

**Total deviations:** 5 auto-fixed (all Rule 1 — bugs directly caused by this plan's own catalogue migration, none out of scope)
**Impact on plan:** All five were necessary to keep the test suite green through the migration and to restore exact French text; none changed rendered output or scope beyond fixing what the migration itself broke.

## Issues Encountered

- One pre-existing, unrelated browser-test failure was found during the full-suite run:
  `test_cfg34_live_age_ticks_at_each_converted_site[chromium-health-registry]` fails with
  `AttributeError: module 'server.poll_loop' has no attribute 'save_poll_state'`. Confirmed (by
  running the same test against this plan's own starting commit, before any change) that this
  failure pre-dates this plan entirely. `server/poll_loop.py` is Phase 39's file scope (server/),
  not this plan's — logged in `.planning/phases/40-.../deferred-items.md` per the SCOPE BOUNDARY
  rule rather than fixed here.

## Known Cross-Area IDs (for plan 40-14)

These ids were assigned this plan, at a page module's Message declaration site, but their owning
`i18n_fr` catalogue module (display.py or rules.py, both 40-14 territory) stays legacy `CATALOG`
until 40-14's own migration runs. Each resolves correctly today via the Message-with-no-`BY_ID`-
entry legacy fallback. 40-14 must derive the SAME ids for these English strings (`slug_for()` is
deterministic) — never declare a second, different id for the same English text.

| ID | English | Owning catalogue (unmigrated) | Declared in |
|----|---------|-------------------------------|-------------|
| `display.delete` | "Delete" | display.py | airlines_page.py |
| `display.runway` | "Runway" | display.py | history_page.py |
| `display.callsign` | "Callsign" | display.py | history_page.py |
| `rules.flight` | "Flight" | rules.py | history_page.py |
| `rules.aircraft` | "Aircraft" | rules.py | history_page.py |

Additionally, `companion/i18n_fr/registry.py` still exports a legacy `CATALOG` for its eighteen
theme-name entries (White/Black/Grey/.../Band Red Field) and its one screen-label entry ("Plane
frame"). Plan 40-14 (or 40-15, since registry.py is not itself in 40-14's own catalogue list) must
declare their Messages in `config_page.py`/`companion/settings/*.py`/`companion/screens.py` and
finish converting `registry.py` to `MESSAGES` only.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 40-14 can migrate `config_page.py`/`companion/settings/*` and the `display`/
  `calendar_group`/`notifications`/`rules` catalogues, using `test-support/i18n_ids.slug_for()` for
  every new id — the cross-area table above tells it exactly which ids a page module already
  assumed for its catalogue's entries, and the registry.py residual CATALOG needs its own
  declaring modules.
- Plan 40-15 removes both legacy fallbacks (plain str → TypeError; Message-with-no-BY_ID → fails
  the completeness test) once every catalogue module is migrated — not before 40-14 lands.
- No blockers. One pre-existing, out-of-scope test failure logged in `deferred-items.md` for
  whichever session owns `server/poll_loop.py`.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 17 files listed under Files Created/Modified (plus deferred-items.md) confirmed present on
disk; both task commits (f7d501e, 512c936) confirmed in `git log`.
