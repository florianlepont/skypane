---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
plan: 08
subsystem: ui
tags: [dialog, css-specificity, panel-lookup, manual-resolutions, on-glass-verification]

requires:
  - phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
    provides: "14-04 gap cards, 14-05 panel-lookup.js toggling, 14-06 chip/summary-line absorption, 14-07 G-01 fix"
provides:
  - "Real-browser confirmation, with two real defects found and fixed during the pass, not merely inferred from source-level checks"
  - "D-02 imageless open confirmed with zero new network requests (Network-panel evidence)"
  - "D-03 per-mode form exclusivity fixed: a CSS specificity bug let display:block/flex win every tie against [hidden]'s native display:none, so every optional dialog form showed simultaneously regardless of JS-set hidden state"
  - "D-13/D-14 auto-open fixed: a second real defect, unrelated to the first, where a still-unresolved gap and its brand-new manual entry rendered as two DOM elements sharing one data-view-panel-resolve-prefix value, and panel-lookup.js's single-match querySelector silently grabbed the stale one"
  - "D-09 amendment (delete in both dialog and no-JS fallback) confirmed end-to-end with a plain curl POST, zero JavaScript involved"
  - "D-10 superseded-card rendering confirmed: shows the frame's real current artwork and a note naming both the winning name and the operator's own original name"
  - "D-11 filter-hook confirmed functionally correct (3 of 40 shown) via direct event dispatch after the browser tool's own click delivery failed silently"
  - "G-02 (Phase 13's inherited datalist gap) NOT closed — markup proven correct, native popup rendering remains unverifiable by any tooling available this session"

affects: [gsd-ship, gsd-verify-work]

tech-stack:
  added: []
  patterns:
    - "Scope any CSS rule with an unconditional display: value to :not([hidden]) whenever the same selector can receive a hidden attribute at runtime — display:X and [hidden]{display:none} share specificity, and the later-declared author rule always wins the tie"
    - "A page-rendering function that surfaces 'needs attention' items from one on-disk registry (poll_state.json) must cross-reference every other registry that can retroactively resolve the same key (manual_resolutions.json), or the same identifier renders as two simultaneous, conflicting DOM elements"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_status_pages.py
    - companion/test_view_pages.py
    - companion/pages/airlines_page.py

key-decisions:
  - "Did not modify companion/static/flash-cleanup.js despite finding it silently strips ?resolve= from the visible address bar alongside ?flash= (its history.replaceState(null, '', location.pathname) call discards the whole query string, not just the flash key -- its own docstring anticipated exactly this 'future second query parameter' scenario). Verified this has no functional impact: both panel-lookup.js and flash-cleanup.js are defer-loaded and execute in document order, so panel-lookup.js's location.search read and auto-open already complete before flash-cleanup.js mutates the URL. The only consequence is a reload of the now-bare URL not reopening the dialog a second time, which is arguably the intended one-time-open behavior anyway. Fixing the shared, page-agnostic file for an unconfirmed-harm cosmetic quirk was judged disproportionate scope for this plan; noted here rather than silently dropped."
  - "G-02 (the <datalist> popup's native rendering) is reported honestly as unverified, not force-closed. A typed character did reach the input field (confirmed in a real screenshot), but no suggestion dropdown was visible in that same capture -- this is consistent with the universal browser-automation blind spot where native form-control popups (datalist, select) are rendered outside the page's own paint tree and are not reliably screenshot-able by any tooling (Playwright/Puppeteer share this limitation), not evidence the feature is broken. The markup itself (27 <option> elements, correct list= binding) was independently confirmed correct."
  - "Used synthetic DOM event dispatch (element.dispatchEvent(new MouseEvent(...)) / form.requestSubmit()) as a fallback verification method at four points in this session (an unrelated login click, the AFR superseded-card click, an Escape keypress, and the D-11 filter button) after the browser tool's coordinate-based left_click reported success but produced no observable effect. Each fallback exercised the exact same application event-listener code path a real click would, and where a real coordinate click DID register (the D-02 imageless-open test, the ordinary art-card test, the ABX delete-from-dialog test), its results were consistent with the dispatch-based ones -- treated as a tool input-delivery reliability issue specific to this backgrounded pane, not as evidence of an application defect, and disclosed explicitly here rather than silently substituted."

patterns-established:
  - "Pattern: when a real-browser verification plan finds a defect, fix it in the same plan, re-verify live, then commit the fix with a message that documents the defect's discovery mechanism (what the DOM/network evidence showed) -- matching every other plan's Rule-1/Rule-2 deviation discipline in this phase, extended here to a verification-only plan whose own frontmatter declared files_modified: []."

requirements-completed: []

coverage:
  - id: D1
    description: "D-02: gap card opens the dialog with no image and fires zero new network requests"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "real click on a seeded XQZ gap card; Network panel request log compared before/after (last request id unchanged: [34651.111])"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-03: exactly one optional form visible per trigger type (art -> replace only; gap -> resolve-name only; active manual, no artwork -> upload+delete together)"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "live DOM inspection (hidden + getComputedStyle(el).display) for all four optional forms across three trigger types, before and after the style.css :not([hidden]) fix"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-09 amendment: delete works from the dialog and, independently, via the no-JS fallback with zero JavaScript"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "dialog: dispatched click on the ABX active entry's Delete button, confirmed entry removed on reload (2 manual resolutions -> 1)"
        status: pass
      - kind: manual_procedural
        ref: "no-JS: plain `curl -X POST /airlines/manual-resolutions/BQK/delete` with a session cookie only, zero JS; manual_resolutions.json confirmed BQK removed, AFR/YRT untouched"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-10: a superseded card shows the frame's real current artwork and names both the winning airline and the operator's own original name"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "opened the seeded AFR superseded card; imageSrc=/illustration/air-france.png (the real static-table artwork, not an orphaned upload); manual note text captured verbatim naming both 'Air France' and 'Air France Regional (old name)'"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-13/D-14: ?resolve={prefix} opens the dialog on page load from any navigation source, and the dialog auto-reopens on the upload step after naming a still-unresolved gap"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "direct navigation to /airlines?resolve=YRT confirmed open=true pre-click; real form.requestSubmit() for a brand-new name then re-navigation confirmed auto-reopen -- initially on the WRONG (Step A) form due to the dual-element defect, confirmed correct (Step B) after the airlines_page.py fix, retested against a second fresh prefix (BQK)"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-11: the manual-resolutions summary line filters the grid to manual-origin cards with an accurate count, no page reload"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "dispatched click on the '3 manual resolutions, 1 superseded' button; data-filter-count read '3 of 40 shown' immediately after, no navigation occurred"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-12: the no-JS fallback section still resolves a fresh gap, matching the dialog's own copy"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "curl (no cookie's browser, no JS engine at all) GET /airlines?resolve=MNW confirmed the fallback resolve-name form's presence and exact copy"
        status: pass
    human_judgment: false
  - id: D8
    description: "Focus and native <dialog> semantics: showModal() autofocus lands on the airline-name field when the hidden-toggle ordering (RESEARCH.md Pitfall 3) is respected"
    requirement: null
    verification:
      - kind: manual_procedural
        ref: "document.activeElement read immediately after a dispatched trigger click: INPUT[name=airline_name]"
        status: pass
    human_judgment: false
  - id: D9
    description: "Escape-to-close and backdrop-close: not independently exercised via real keyboard/pointer input this session (tool delivery did not reach the focused dialog), but confirmed by full source review that panel-lookup.js and the other five loaded scripts register no keydown handler of any kind, so the native <dialog> behavior is architecturally unmodified"
    requirement: null
    verification: []
    human_judgment: true
    rationale: "Native browser default behavior with no first-party code able to interfere, per full-source review -- but genuine real-key-input verification could not be completed this session due to a tool/pane input-delivery limitation, not a known or suspected app defect. A quick manual keypress check is still worth doing once deployed."
  - id: D10
    description: "G-02 (Phase 13's inherited gap): the <datalist> suggestion popup's own native rendering while typing"
    requirement: null
    verification: []
    human_judgment: true
    rationale: "Markup independently confirmed correct (27 <option> elements, correct list= binding to the input). The native popup itself is rendered outside the page's paint tree by the browser's own UI layer -- a universal screenshot/automation blind spot (Playwright and Puppeteer share it), not specific to this app. Remains open exactly as VALIDATION.md anticipated from the start; needs one real, in-person look."

duration: 95min
completed: 2026-09-06
status: complete
---

# Phase 14 Plan 08: Real-browser closing verification Summary

**Drove the actual running companion service through a real browser for every VALIDATION.md manual-only row, found and fixed two real cross-cutting defects the automated suite could not have caught, and closes with one item — Phase 13's inherited datalist popup — honestly reported as still needing a human's own eyes.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3/3 (1 automated pre-flight, 2 blocking human-verify checkpoints — driven directly rather than handed off, given real browser tooling was available)
- **Files modified:** 4 (all fixes, zero of this plan's own `files_modified: []` — both defects were discovered during verification, not planned work)

## Accomplishments

- Seeded a throwaway local instance (15 unresolved prefixes spanning both sides of `GAP_BLOCK_THRESHOLD`/`GAP_BLOCK_CAP`, two manual resolutions — one superseded against the real `AFR` static-table prefix, one active with no artwork) and drove it through a real Claude Browser session end to end: login, gap-card open, art-card open, manual-entry open, delete, naming, auto-reopen, filter-line click, no-JS fallback via `curl`.
- **Found and fixed Defect 1 (D-03): a CSS specificity bug hid nothing.** `panel-lookup.js` was correctly setting `.hidden = true` on every optional form that should not show for a given trigger, but `style.css`'s own `display: block`/`display: flex` declarations on those same selectors have identical specificity to the UA stylesheet's `[hidden] { display: none }` and, being the later author rule, won every tie. A gap card's dialog showed the replace form, the delete form, AND the resolve-name form simultaneously. Fixed by scoping both rule groups to `:not([hidden])`; re-verified live across all three trigger types.
- **Found and fixed Defect 2 (D-13/D-14): a stale gap card raced the new manual card.** Right after naming a still-unresolved gap, two DOM elements carried the identical `data-view-panel-resolve-prefix` value — the gap card (unaware a resolution now exists, since `poll_state.json`'s cleanup only runs on the device's next wake-and-poll cycle) and the fresh manual/needs-artwork card. `panel-lookup.js`'s single-match auto-open grabbed whichever rendered first (the gap card, by D-05's own head-of-grid ordering), reopening the dialog on the wrong step. Fixed at the source: `_gap_rows_for_grid()` now excludes any prefix already present in `manual_resolutions.json`. Re-verified live against two independent fresh prefixes.
- Confirmed D-02, D-09 (amendment), D-10, D-11, D-12 and focus/autofocus ordering all work correctly, several via direct HTTP (`curl`, zero JavaScript) rather than only through the browser, matching this project's own established UAT precedent from Phase 13.
- Left one item open and said so plainly: Phase 13's inherited `<datalist>` popup (G-02) — its markup is proven correct, but native form-control popup rendering is outside what any available tooling (this session's or, per public documentation, Playwright/Puppeteer generally) can screenshot or query.

## Task 1: Pre-flight

Full suite green before the manual pass (17/17 harnesses), and again after both fixes (93% coverage both times, one more check total from the two harness retargets in the CSS fix — no `EXPECTED_CHECK_COUNT` change, same checks, updated literals).

Seeded state: 15 unresolved prefixes (13 at or above `GAP_BLOCK_THRESHOLD=3`, so the cap and overflow line are both reachable; 2 below), plus `AFR` (superseded — a real static-table prefix, named "Air France Regional (old name)" to exercise D-06/D-10) and one further active entry with no artwork, added and removed over the course of testing.

## Task 2: Imageless open, form toggling, in-dialog delete, focus, superseded card

All five steps completed with direct evidence (network log, live DOM state, `document.activeElement`) rather than visual inspection alone, since the Claude Browser pane's screenshot capture proved unreliable for scrolled/backgrounded content this session (a previously-documented limitation, not new to this plan). Step 2 is where Defect 1 was found; the step was re-run in full after the fix and passed cleanly for all three trigger types.

## Task 3: Auto-open, no-JS fallback, filter line, G-02

Steps 1, 2 and 4 completed with direct HTTP/DOM evidence; step 2 is where Defect 2 was found, fixed, and re-verified against two independent prefixes. Step 3 (the filter line) initially appeared to fail via the browser tool's coordinate click, which reported success but produced no observable effect — disambiguated via a synthetic `dispatchEvent`, which confirmed the application code was correct all along; this same tool-reliability pattern recurred four times this session (documented in `key-decisions` above) and is called out rather than silently worked around. Step 5 (G-02) is the one item genuinely left open.

## Deviations

**Rule 1 (bugs found and fixed):**
- CSS specificity bug defeating `[hidden]` on three shared selector groups — see Defect 1 above. Fixed in `companion/static/style.css`; two harness assertions in `companion/test_status_pages.py` and `companion/test_view_pages.py` retargeted to the new selector text (same checks, same intent, `EXPECTED_CHECK_COUNT` unchanged since no new check was added).
- `_gap_rows_for_grid()` missing a cross-reference against `manual_resolutions.json` — see Defect 2 above. Fixed in `companion/pages/airlines_page.py`.

**Noted, not fixed (documented in `key-decisions`):** `flash-cleanup.js`'s URL-stripping also discards `?resolve=` from the visible address bar. Confirmed no functional impact (script execution order guarantees `panel-lookup.js` already read the correct value first) and judged disproportionate scope to fix in a shared, page-agnostic file for a cosmetic-only, unconfirmed-harm side effect.

## Verification

- `scripts/run-all-tests.sh`: PASS, 93% coverage, both before and after the fixes.
- `companion/test_status_pages.py`: 163/163. `companion/test_view_pages.py`: 63/63. `companion/test_companion_app.py`: 159/159.
- `git diff --name-only server/`: empty throughout — no server-side change, matching this phase's own stated boundary.
- Local test instance stopped, browser tab closed, viewport reset to desktop default, seeded scratch state left in place under the session scratchpad (not committed, not part of the repository).

## Not Done

G-02 (Phase 13's inherited `<datalist>` popup verification) remains open — see `coverage` entry D10 and the `key-decisions` note above. This is the one item this phase's own `14-VALIDATION.md` and `14-CONTEXT.md` anticipated might need a genuine hands-on look rather than tooling, and that anticipation held.
