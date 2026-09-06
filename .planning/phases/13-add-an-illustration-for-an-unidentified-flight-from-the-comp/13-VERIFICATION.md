---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
verified: 2026-09-06T00:00:00Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 13: Add an illustration for an unidentified flight from the companion web interface — Verification Report

**Phase Goal:** From the two companion pages that already surface a coverage gap — Health's unresolved-prefix registry and the Airlines gallery — the operator can add the missing artwork for a flight the frame could not dress, with enough of that flight's own information in view to know what they are dressing.
**Verified:** 2026-09-06
**Status:** passed
**Re-verification:** No — initial verification (no prior `13-VERIFICATION.md` existed)

This phase carries no requirement IDs (unmapped, promoted from a seed — matches Phases 10/11/12 precedent, confirmed in every plan's `requirements: []`). The phase's real contract is `13-CONTEXT.md`'s 14 locked decisions (D-01..D-14), and the code review (`13-REVIEW.md`, 2 critical + 13 warnings). Verification below is goal-backward against that contract, not against SUMMARY.md narration.

## Goal Achievement

### Observable Truths (D-01..D-14 contract + review-blocker closure)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CR-01 fixed: an unwritable `state_dir` no longer raises out of `add_entry()`/`delete_entry()` | ✓ VERIFIED | Direct behavioral reproduction against the shipped module: `add_entry()` on a `chmod 0o500` parent and on a file-as-directory both return `"failed"` (`ADD_FAILED`), no exception. `delete_entry()` on a read-only parent returns `False`, no exception. `os.makedirs()` is now inside the `try:` block (commit `4df87de`) at `server/plane/manual_resolutions.py:376` (add) and delete's mirror. `server/test_manual_resolutions.py` now has 2 dedicated checks (`WR-11`) exercising exactly this; harness reports `23/23` (was 19/19 pre-review). |
| 2 | CR-02 fixed: after D-14 clears a resolved prefix from the gap registry, Step B (upload artwork) and D-07's delete-and-re-add path stay reachable | ✓ VERIFIED | `companion/pages/airlines_page.py`'s `_resolve_section_html()` (commit `ee9e353`) no longer dead-ends when `unresolved_row_for_prefix()` returns `None`: it re-validates `resolve_prefix` via `manual_resolutions.normalise_prefix()` (the same D-11 shape gate) and falls through to the manual-registry-driven Step A/B/already-done derivation. The management list gained a per-row "Add artwork" link (`ADD_ARTWORK_LINK_TEXT`, `_manual_add_artwork_link_html()`) into the identical `?resolve={prefix}` URL, rendered only for an active entry with no resolved artwork yet. `companion/test_status_pages.py` has dedicated CR-02 checks (`_manual_section_add_artwork_link_contract` and the "Step B must stay reachable once D-14 clears the live gap" check); harness reports `149/149`. **D-14 itself is untouched** — `git diff -- server/plane/enrich.py server/poll_loop.py` since `ee9e353` shows no change to `clear_resolved_unresolved_prefix()` or its call site; the fix lives entirely in the companion's render-state derivation, so D-14's cleanup was not weakened to achieve reachability. |
| 3 | D-09 standing gate: `select_illustration()` / `illustrations.py` never modified this phase | ✓ VERIFIED | `git diff 4a31a62..HEAD -- server/plane/illustrations.py` is empty (0 lines) — byte-for-byte unchanged since before phase 13 began. `server/test_illustrations.py` reports `58/58`, unchanged count. |
| 4 | D-10: Health stays read-only — no `<form>`, no state-changing `<button>` | ✓ VERIFIED | `grep -c '<form' companion/pages/health_page.py` → `0`. `grep -c '<button' companion/pages/health_page.py` → `1`, and that one hit is the pre-existing docstring reference to D-16 ("D-16 forbids a `<button>` element anywhere on the page"), not a rendered element. |
| 5 | Zero JavaScript, no new third-party dependency anywhere in the phase's diff | ✓ VERIFIED | `git diff 4a31a62..HEAD --stat -- '*.js'` empty. `git diff 4a31a62..HEAD -- server/requirements.txt server/requirements-dev.txt` empty. `.datalist` suggestion list is native HTML (D-13), confirmed no `<script>`/`onclick`/`onchange`/`onsubmit` added to `airlines_page.py` or `health_page.py` by per-plan acceptance-criteria greps, all of which pass in the current tree. |
| 6 | D-01/D-05: a manual resolution (prefix→airline name) survives a process restart via a state-dir JSON file, following `device_config.json`'s contract | ✓ VERIFIED | `server/plane/manual_resolutions.py` exists with `manual_resolutions_path()`, `os.replace()`-based atomic write (now inside `try:`, unique per-writer temp name — WR-02 fix), and round-trips through `load_manual_resolutions()`. `server/test_manual_resolutions.py`: `23/23`. |
| 7 | Malformed/hand-edited/oversized/unreadable registry degrades to `{}`, never raises in the poll cycle or a page render | ✓ VERIFIED | `load_manual_resolutions()` behavior confirmed by harness (non-JSON, non-dict, malformed entries, reserved-slug entries all dropped); bounded at `MANUAL_RESOLUTION_MAX_ENTRIES`. `server/test_poll_loop.py` (`64/64`) and `companion/test_companion_app.py` (`159/159`) both exercise this through real cycles/requests. |
| 8 | A name slugging to a reserved key (`generic-fallback`, `generic-<shape>`) is refused before persistence | ✓ VERIFIED | `add_entry(..., "Generic Fallback")` and `add_entry(..., "Generic A320")` both return `ADD_REJECTED_NAME_RESERVED`, proven live and by harness. `POST /airlines/resolve` rejection-mapping test (`companion/test_companion_app.py`) confirms the same through the real route (`flash=manual_name_reserved`). |
| 9 | Deleting a manual resolution leaves the uploaded override PNG on disk untouched (D-08) | ✓ VERIFIED | `server/test_manual_resolutions.py`'s D-08 proof (pinned to the real `illustrations.override_path_for_key()`) and `companion/test_companion_app.py`'s `_manual_resolution_delete_route_full_contract` — through the real HTTP route — both assert the override file survives a delete. Confirmed passing. |
| 10 | Registry cannot grow past `MANUAL_RESOLUTION_MAX_ENTRIES` even under a compromised authenticated session | ✓ VERIFIED | `companion/test_companion_app.py`'s D-03/rejection-mapping check fills the registry to the 200-entry cap and asserts a further `POST /airlines/resolve` returns `flash=manual_registry_full` and persists nothing. |
| 11 | D-06: static table wins over a manual entry on collision; a prefix present in both reports the static name and source; superseded entries are flagged in the UI, not silently dropped | ✓ VERIFIED | `enrich.airline_source_from_callsign()` consults `_ICAO_AIRLINE_PREFIXES` first and returns immediately on a hit (branch order, not comparison) — `server/test_enrich.py` check 3 proves this directly (`59/59` passing). `airlines_page._manual_resolution_rows()` sets `superseded` from `enrich.static_airline_name_for_prefix()`; the management list renders `SUPERSEDED_MARKER_TEXT` with an explanatory caption — `companion/test_status_pages.py`'s supersession-contract check confirms marker presence/absence and the caption's singular occurrence. |
| 12 | D-02: `resolve_route()` returns `"manual"` (never `"airline_only"`) when the runtime registry, not the static table, resolved the callsign | ✓ VERIFIED | `server/test_enrich.py` checks 4-5 prove `resolve_route()`'s manual-source branch and static/manual/adsbdb precedence together; `59/59` pass. Health's `_SOURCE_ROWS` gained a 5th `"manual"` tuple (`companion/test_status_pages.py`, `149/149`). |
| 13 | D-14: a resolved prefix leaves the gap registry on the poll loop's next cycle, independent of that cycle's `route_source`, so Health/`coverage_status()` stop reporting a closed gap | ✓ VERIFIED | `server/test_poll_loop.py` checks 3-4 prove cleanup fires even when the same cycle's `route_source` is `"fresh_hit"` (adsbdb answered) — the exact independence Pitfall 2 warned about. `64/64` pass. Cleanup call site verified positioned unconditionally, before `trim_unresolved_prefixes()` and the write-back (source read, not grep-only). |
| 14 | End-to-end operator loop closes: Health shows gap → deep link → name airline → artwork appears (already-vendored) or is uploaded (new name) → gap eventually stops being reported | ✓ VERIFIED | Full chain traced through real, passing HTTP-level tests: Health's per-row `/airlines?resolve={prefix}` deep link (`companion/test_status_pages.py`); `POST /airlines/resolve` persists the name after re-validating the prefix against the live registry (D-11, `companion/test_companion_app.py`); D-03 branch confirmed live — naming an airline with existing vendored artwork (e.g. "Air France") redirects **without** `resolve=`, no upload asked (`_manual_resolve_post_rejection_mapping_and_d03_branch`); a brand-new name redirects **with** `resolve=` into Step B, whose upload form posts unchanged to the existing `/illustration/{key}.png` route; D-14's poll-cycle cleanup (`server/test_poll_loop.py`) removes the gap on the next cycle that observes it. The one review-identified dead end in this loop (CR-02: Step B unreachable once D-14 clears the gap) is fixed and tested (see Truth 2). |

**Score:** 14/14 truths verified (0 present-but-behaviorally-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/plane/manual_resolutions.py` | Runtime prefix→name registry, D-05/D-08/D-13 contract | ✓ VERIFIED | Exists, all 10 documented functions + 7 `ADD_*` constants present; `23/23` harness checks pass including WR-02/WR-03/WR-11 fixes. |
| `server/test_manual_resolutions.py` | Contract harness | ✓ VERIFIED | `23/23` pass, registered in `scripts/run-all-tests.sh` (17-harness count confirmed live). |
| `server/plane/enrich.py` | `airline_source_from_callsign()`, `static_airline_name_for_prefix()`, `clear_resolved_unresolved_prefix()`, 5th `resolve_route()` source | ✓ VERIFIED | All three new functions present; `airline_from_callsign()` unchanged signature; `59/59` harness checks pass. |
| `server/poll_loop.py` | Per-cycle registry load + D-14 cleanup call site | ✓ VERIFIED | Both call sites confirmed inside `run_once()`, in correct order (setter beside `illustrations.set_override_state_dir()`; cleanup unconditional, before `trim_unresolved_prefixes()`). `64/64` pass. |
| `companion/pages/health_page.py` | Re-worded read-only note, per-row deep link, 5th source row | ✓ VERIFIED | No form/button added; deep link present in both desktop and mobile representations. |
| `companion/pages/airlines_page.py` | Resolve section (4+ states incl. CR-02's Step-B-without-live-gap state), management list with delete/superseded/add-artwork | ✓ VERIFIED | All states render correctly through real harness checks; zero `<script>`, zero inline handlers. |
| `companion/app.py` | Widened membership union, 2 new POST routes, 3 ctx keys, 8 flash keys | ✓ VERIFIED | `_illustration_filenames(state_dir)` is a per-request union; both routes gated by `require_session()` first; `159/159` companion-app checks pass. |
| `companion/pages/__init__.py` | ctx-key contract documentation | ✓ VERIFIED | `resolve_prefix` and `manual_resolutions` documented; harness asserts documented set matches actual returned keys. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `manual_resolutions.add_entry()` | filesystem write | `os.makedirs()` inside `try:` | ✓ WIRED (post-CR-01 fix) | Confirmed by direct reproduction: unwritable dir → `ADD_FAILED`, no raise. |
| `airline_from_callsign()` | `manual_resolutions.airline_name_for_prefix()` | static-table-first branch order | ✓ WIRED | `server/test_enrich.py` D-06 collision check passes; static table consulted and returns before the registry is ever read. |
| `poll_loop.run_once()` | `manual_resolutions.set_manual_registry_state_dir()` | consecutive line after `illustrations.set_override_state_dir()` | ✓ WIRED | Confirmed by source inspection and by `server/test_poll_loop.py`'s per-cycle-load check (`64/64`). |
| `airlines_page._resolve_section_html()` | `unresolved_row_for_prefix()` (render) and `companion/app.py`'s POST handler (write) | shared function, single normalization point (WR-04 fix) | ✓ WIRED | Both paths now normalize via `manual_resolutions.normalise_prefix()` inside `unresolved_row_for_prefix()` itself — no longer diverge (confirmed by source at `airlines_page.py:716-720`). |
| Health's `/airlines?resolve={prefix}` link | Airlines resolve section render | query param → `page_context()`'s `resolve_prefix` ctx key | ✓ WIRED | `companion/test_status_pages.py` and `companion/test_companion_app.py`'s ctx-contract check confirm. |
| `POST /illustration/{key}.png` | `_illustration_filenames(state_dir)` widened union | per-request read of `manual_resolutions.json`, never from current request | ✓ WIRED | T-v26-02-01 re-verified: Pitfall-3 executable check confirms a single-request upload of an unregistered key 404s and writes nothing. |
| Management list "Add artwork" link (CR-02) | `?resolve={prefix}` → Step B render | `_manual_resolution_rows()`'s `needs_artwork` flag | ✓ WIRED | `_manual_section_add_artwork_link_contract` check passes; link renders only for active, artwork-less entries. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `add_entry()` on unwritable parent dir | live `python3` repro against `server/plane/manual_resolutions.py` | returns `"failed"`, no exception raised | ✓ PASS |
| `add_entry()` when `state_dir` is a file (not a dir) | live `python3` repro | returns `"failed"`, no exception raised | ✓ PASS |
| `delete_entry()` on read-only parent dir mid-write | live `python3` repro | returns `False`, no exception raised | ✓ PASS |
| `server/plane/illustrations.py` byte-unchanged since pre-phase base | `git diff 4a31a62..HEAD -- server/plane/illustrations.py` | 0 lines | ✓ PASS |
| Zero-JS / no-new-dependency gate across whole phase | `git diff 4a31a62..HEAD --stat -- '*.js' server/requirements*.txt` | empty | ✓ PASS |
| Health has no form/state-changing button | `grep -c '<form\|<button' companion/pages/health_page.py` | `0` forms, `1` button (docstring-only mention) | ✓ PASS |

### Probe Execution

Not applicable — this phase declares no `scripts/*/tests/probe-*.sh` probes; verification instead runs the project's own harness suite (`scripts/run-all-tests.sh`), which is this phase's equivalent contract.

| Harness | Command | Result | Status |
|---------|---------|--------|--------|
| Full suite, 17 harnesses | `scripts/run-all-tests.sh` | All 17 harnesses green, coverage threshold met, `Result: PASS` | ✓ PASS |
| `server/test_manual_resolutions.py` | direct run | `23/23` | ✓ PASS |
| `server/test_enrich.py` | direct run | `59/59` | ✓ PASS |
| `server/test_poll_loop.py` | direct run | `64/64` | ✓ PASS |
| `companion/test_companion_app.py` | direct run | `159/159` | ✓ PASS |
| `companion/test_status_pages.py` | direct run | `149/149` | ✓ PASS |
| `companion/test_view_pages.py` | direct run | `54/54` | ✓ PASS |
| `companion/test_contrast_check.py` | direct run | `36/36` | ✓ PASS |
| `server/test_illustrations.py` (D-09 gate) | direct run | `58/58`, unchanged count | ✓ PASS |

Note: `deferred-items.md` documents an intermittent flake in a Health battery-chart check when the suite runs under parallel/coverage instrumentation, confirmed independent of phase 13's changes by the executor (reproduces identically with 13-04's own changes stashed). Per the task brief, this is a known pre-existing issue, not a phase-13 gap. It did not reproduce during this verification's full-suite run (all 17 harnesses green, `Result: PASS`).

### Requirements Coverage

Not applicable — this phase carries `requirements: []` in every plan, matching Phases 10/11/12's precedent for an unmapped phase promoted from a seed (`SEED-005`). No orphaned requirements found in `.planning/REQUIREMENTS.md` for Phase 13 (no "Phase 13" entries exist there to check against). Per the task brief, this is not a gap.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers found in any file this phase modified. `TODO`/`HACK`/`PLACEHOLDER` sweep: none found. The 11 remaining code-review warnings not fixed in this phase (WR-01, WR-05, WR-07 through WR-10, WR-12, WR-13) are documented, non-blocking, low/medium-severity items — none of them contradict a locked D-01..D-14 decision, none of them break a "never raises" contract that a shipped flash key depends on (that was CR-01, fixed), and none of them create a dead end in the operator's resolve flow (that was CR-02, fixed). They are follow-up hardening, not phase-goal blockers:

| File | Warning | Severity | Impact |
|------|---------|----------|--------|
| `server/plane/manual_resolutions.py` | WR-01: `state_dir=None` raises `TypeError` in three functions (latent — production always passes a string) | ⚠️ Warning | Not exercised by any real code path; two ad-hoc `if state_dir:` guards elsewhere already work around it. |
| `server/plane/manual_resolutions.py` | WR-03: a single load-time rejection can permanently drop legacy/over-cap entries on next write | ⚠️ Warning | Data-loss risk on a hand-edited or migrated file; not reachable through the normal UI flow this phase ships. |
| `companion/pages/airlines_page.py` / `style.css` | WR-07: `.resolve-upload-zone`'s DOM doesn't structurally match `.lightbox__replace-zone`, so the flex column/gap styling doesn't apply to the file input/button inside the nested form | ⚠️ Warning | Cosmetic layout drift in Step B's upload zone; does not block the upload functioning. |
| `companion/app.py` | WR-08: `ADD_REJECTED_PREFIX` maps to the "enter a name" flash instead of a stale/save-failed one | ⚠️ Warning | Documented-unreachable branch (prefix shape already proven upstream); message would be misleading if it ever fired. |
| `companion/app.py` | WR-10: concurrent uploads to the same key can collide on a shared temp path (pre-existing, widened reach) | ⚠️ Warning | Pre-existing defect from quick task 260902-v26; D-09 widens the reachable key space but doesn't introduce the race. |
| `companion/app.py` | WR-12: Step B's success flash says "Illustration replaced" for a first-ever upload | ⚠️ Warning | Minor copy inaccuracy, not a functional gap. |
| `server/plane/enrich.py` | WR-13: `static_airline_name_for_prefix()`'s "ASCII letters" claim isn't what `str.isalpha()` enforces | ⚠️ Warning | Currently correct by accident (non-ASCII letters would miss the static table anyway); a documentation/robustness gap, not a live bug. |

### Human Verification Required

None. All must-haves resolved to VERIFIED via direct code inspection, live behavioral reproduction against the shipped module, and passing automated harnesses (including tests added specifically to prove the two review-blocker fixes hold). No visual, real-time, or subjective-judgment items remain open for this phase.

### Gaps Summary

No gaps. Both code-review blockers (CR-01, CR-02) are genuinely fixed in the shipped code — not merely committed against — and proven by direct behavioral reproduction plus new harness coverage, not by re-reading the fix commit's message. The D-09 standing gate holds (`illustrations.py` byte-unchanged, 58/58). D-10 holds (Health has no form/button). Zero JavaScript and zero new dependencies were added anywhere in the phase's diff. The full 17-harness suite passes clean. The end-to-end operator loop — Health shows a gap, the operator names the airline, artwork either resolves immediately (vendored name, D-03) or is uploaded (new name, Step B), and the gap eventually clears from Health (D-14, next wake) — closes in the shipped code, including the CR-02 fix that keeps Step B and the delete-and-re-add correction path reachable after the gap entry disappears.

Eleven code-review warnings remain open (see Anti-Patterns table above); none blocks the phase goal and none contradicts a locked decision. They are reasonable candidates for a follow-up hardening pass but do not gate this phase's completion.

---

_Verified: 2026-09-06_
_Verifier: Claude (gsd-verifier)_
