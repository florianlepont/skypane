---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 02
subsystem: ui
tags: [companion-web, html, css, python-stdlib, health-page, accessibility]

# Dependency graph
requires:
  - phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp (plan 01)
    provides: server/plane/manual_resolutions.py registry storage contract (referenced by name only, not consumed)
provides:
  - "Health's _READ_ONLY_NOTE reworded to name Airlines as the resolution surface (D-10)"
  - "_SOURCE_ROWS gains a fifth 'manual' entry so operator-resolved prefixes are counted separately from the static prefix table's 'airline_only' (D-02)"
  - "Per-row Resolve deep link (/airlines?resolve={prefix}) on both the desktop registry table and the mobile card list, fully escaped and aria-labelled"
  - "RESOLVE_LINK_HREF_TEMPLATE / RESOLVE_LINK_ARIA_TEMPLATE / RESOLVE_LINK_TEXT / RESOLVE_CARD_LINK_TEXT module constants for downstream plans (13-04/13-06) to consume the same route contract"
  - ".data-card__action CSS class (inherits default link styling, no new accent use)"
affects: ["13-04 (airlines_page resolve-section render gate consumes /airlines?resolve={prefix})", "13-06 (POST handler for the resolve form)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deep-link-only affordance on a read-only page: a plain <a> navigating cross-page, never a <button>/<form>, to add an action without reopening a closed read-only decision (D-10)"
    - "Positional-header append discipline: _REGISTRY_HEADERS' new entry is appended, never inserted, because a sibling function (_registry_cards_html) addresses it by fixed index"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_status_pages.py

key-decisions:
  - "Reused escape_html(prefix) once per representation and interpolated the same escaped value into both href and aria-label, rather than calling escape_html() twice per representation as the plan's action text literally suggested — functionally identical (each interpolation point still passes through the escaping choke point exactly once) and avoids a redundant second call."
  - "Reformatted _READ_ONLY_NOTE's line-wrap so the substring the acceptance gate greps for ('each row's Resolve link opens the Airlines page') lives on a single physical line, since Python's implicit string concatenation across multiple string literals breaks a grep-per-line match at the wrap point."
  - "Fixed three pre-existing test_status_pages.py checks that compared against the raw _READ_ONLY_NOTE Python literal instead of its escaped rendered form — the reworded note contains two apostrophes, which escape_html()'s quote=True mode renders as &#x27;, so a raw-literal substring match against rendered HTML now fails."

requirements-completed: []

coverage:
  - id: D1
    description: "Health's read-only note is reworded to name Airlines as the resolution surface, no longer pointing at the retired manual runbook"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_read_only_note_reworded_to_point_at_airlines_not_the_runbook"
        status: pass
    human_judgment: false
  - id: D2
    description: "_SOURCE_ROWS gains a fifth 'manual' entry; resolution_stats() folds a seeded 'manual' route_source count into the total and a labelled row"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_source_rows_gains_fifth_manual_entry"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every registry row, in both the desktop table and the mobile card list, carries an escaped, aria-labelled Resolve deep link to /airlines?resolve={prefix}"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_registry_resolve_link_pairs_desktop_and_mobile_and_escapes_hostile_input"
        status: pass
    human_judgment: false
  - id: D4
    description: "Health gains no HTML form element and no submit control anywhere on the page (the D-11/D-12 read-only guarantee is not reopened)"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_health_still_has_no_form_and_exactly_one_button_literal"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 02: Health's read-only note reword and per-row Resolve deep link Summary

**Health's coverage-gap registry gains a per-row `/airlines?resolve={prefix}` deep link (desktop table + mobile card, both escaped and aria-labelled) and a fifth "Manual" resolution-source row, with zero new form/button/script — the entry point the whole phase exists to create.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-06T01:00Z (approx, after 13-01 plan closed)
- **Completed:** 2026-09-06T01:13Z
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments
- `_READ_ONLY_NOTE` reworded byte-for-byte to the UI-SPEC's approved copy, telling the operator where resolution happens (Airlines, via the new link) instead of pointing at a retired manual runbook — the module's "closed four-way enumeration" prose was swept for every place it needed correcting alongside this.
- `_SOURCE_ROWS` gained a fifth `("manual", "Manual", ...)` tuple so an operator-resolved prefix is never miscounted into `"airline_only"`'s static-prefix-table bucket (D-02).
- Both registry representations (the desktop `<tr>`'s new sixth `<td>` and the mobile `.data-card__action` block) now carry an identical, fully-escaped, `aria-label`led anchor to `/airlines?resolve={prefix}` — a plain navigation link, never a state-changing control.
- Health's read-only guarantee (D-11/D-12 of `06.6.4.1-04`) is proven machine-readably: zero `<form`, exactly one pre-existing `<button` docstring literal, zero new `<script`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reword `_READ_ONLY_NOTE` and append the fifth "manual" source row (D-02, D-10)** - `b45923c` (feat)
2. **Task 2: Add the per-row Resolve deep link to both registry representations (D-10)** - `376940e` (feat)

**Plan metadata:** (this commit) `docs(13-02): complete Health read-only-note-reword + Resolve-link plan`

## Files Created/Modified
- `companion/pages/health_page.py` - `_READ_ONLY_NOTE` reworded; `_SOURCE_ROWS` gains its fifth "manual" tuple; four new `RESOLVE_LINK_*`/`RESOLVE_CARD_LINK_TEXT` constants; `_REGISTRY_HEADERS` gains a sixth "Resolve" entry (appended); `_registry_row_html()`/`_registry_cards_html()` each emit an escaped, aria-labelled anchor to `/airlines?resolve={prefix}`.
- `companion/static/style.css` - one new `.data-card__action { margin-top: var(--space-xs); }` rule, inheriting default link styling (no new accent reservation).
- `companion/test_status_pages.py` - four new checks (note reword, fifth source row, deep-link pairing + hostile-prefix escaping, no-form/one-button-literal read-only guard); `EXPECTED_CHECK_COUNT` moved 136 → 138 → 140 across the two tasks, each re-derived by running the harness.

## Decisions Made
- Reused one `escape_html(prefix)` call per representation for both the `href` and `aria-label` interpolation points, rather than two separate calls as the plan's action prose literally described — every interpolation point still passes through the escaping choke point exactly once (T-13-05's mitigation requirement), and the resulting code is simpler.
- Rewrapped `_READ_ONLY_NOTE`'s Python string-concatenation line break so the acceptance gate's grepped substring ("each row's Resolve link opens the Airlines page") lives on one physical source line — the original wrap point (matching the plan's own action-block formatting) split that exact substring across two string literals, which is invisible to the rendered string but defeats a line-based `grep -c`.
- Fixed three pre-existing `test_status_pages.py` checks (the D-12 filter-bar-migration check, the quick-260902-gjj muted-caption check, and their shared `note_at = rendered.index(health_page._READ_ONLY_NOTE)` pattern) that compared the raw Python literal against rendered HTML. The reworded note's two apostrophes ("row's", "prefix's") are escaped by `escape_html()`'s `quote=True` mode into `&#x27;`, so a raw-literal match against the rendered page silently broke the moment the copy changed — these are pre-existing tests whose fixture assumption (no apostrophes in the note) the plan's own approved copy violated; classified as Rule 1 (auto-fix bug) since they were failing, not merely stylistically outdated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing `_READ_ONLY_NOTE` string-comparison checks broke against the new apostrophe-bearing copy**
- **Found during:** Task 1 (rewording `_READ_ONLY_NOTE`)
- **Issue:** Three existing checks in `test_status_pages.py` located the note in rendered HTML via `rendered.index(health_page._READ_ONLY_NOTE)` or `_READ_ONLY_NOTE not in rendered` — a raw-literal match. The UI-SPEC's approved new copy contains two apostrophes ("row's", "prefix's"); `escape_html()`'s `quote=True` renders these as `&#x27;`, so the raw literal no longer appears in rendered output verbatim.
- **Fix:** Updated all three call sites to compare against `layout.escape_html(health_page._READ_ONLY_NOTE)` instead of the raw constant.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` — 140/140.
- **Committed in:** `b45923c` (Task 1 commit)

**2. [Rule 1 - Bug] Line-wrap in `_READ_ONLY_NOTE` split the acceptance gate's grepped substring across two lines**
- **Found during:** Task 1, verifying `grep -c "each row's Resolve link opens the Airlines page" companion/pages/health_page.py` returns `1`
- **Issue:** The initial line wrap (breaking the string literal right after "the " and before "Airlines page") put half the required substring on each of two adjacent lines — invisible at runtime (Python concatenates the literals), but `grep` matches per physical line by default, so the acceptance check returned `0`.
- **Fix:** Rewrapped the string literal so the full substring "each row's Resolve link opens the Airlines page" sits on one physical line (84 chars, within this file's observed max line length of 111).
- **Files modified:** `companion/pages/health_page.py`
- **Verification:** `grep -c "each row's Resolve link opens the Airlines page" companion/pages/health_page.py` → `1`.
- **Committed in:** `b45923c` (Task 1 commit)

**3. [Rule 1 - Bug] New docstring text in `_registry_row_html()` accidentally added a second `<button>` literal**
- **Found during:** Task 2, verifying `grep -c '<button' companion/pages/health_page.py` returns `1`
- **Issue:** The new docstring explaining the Resolve link's non-state-changing nature originally said "never a `<button>`, never a form control" — adding a second occurrence of the literal string `<button` alongside the pre-existing D-16 docstring mention, which the acceptance gate treats as an exhaustive count.
- **Fix:** Reworded to "never a submit-type control" — same meaning, no literal `<button` substring.
- **Files modified:** `companion/pages/health_page.py`
- **Verification:** `grep -c '<button' companion/pages/health_page.py` → `1`.
- **Committed in:** `376940e` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs surfaced by the plan's own literal-string acceptance gates against the approved copy's actual characters)
**Impact on plan:** All three fixes were necessary for the plan's own stated acceptance criteria to pass; none changed scope, added functionality, or touched a locked decision.

## Issues Encountered
None beyond the three auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `/airlines?resolve={prefix}` is now a live outbound link from Health, ready for plan 13-04 to build the receiving `resolve_section_html` render gate on the Airlines page (D-11's server-side membership test) and for 13-06's POST handler.
- `RESOLVE_LINK_HREF_TEMPLATE`/`RESOLVE_LINK_ARIA_TEMPLATE`/`RESOLVE_LINK_TEXT`/`RESOLVE_CARD_LINK_TEXT` are available as the single source of truth for this route contract — downstream plans should reference these rather than re-deriving the URL shape.
- No blockers. `server/plane/illustrations.py` remains byte-for-byte unchanged (D-09 standing gate verified); full `scripts/run-all-tests.sh` (17/17 harnesses) passes with the coverage threshold intact.

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Completed: 2026-09-06*

## Self-Check: PASSED

All created/modified files found on disk; both task commits (`b45923c`, `376940e`) found in git history.
