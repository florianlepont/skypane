---
phase: 19
slug: companion-audit-follow-through-fix-the-open-findings-from-18
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-11
updated: 2026-09-11
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib-only hand-rolled `check(name, fn)` harnesses — no pytest, no unittest runner. Every harness file is directly executable and self-reports `N/M checks pass`, exiting non-zero unless `passed == total == EXPECTED_CHECK_COUNT` |
| **Config file** | none — `scripts/run_all_tests.py`'s list is the canonical suite |
| **Quick run command** | `server/.venv/bin/python3 companion/test_<name>.py` (or `server/test_<name>.py`) |
| **Full suite command** | `scripts/run-all-tests.sh` |
| **Estimated runtime** | quick: 1-9 s per harness; full suite: ~100 s wall (parallel runner) |

### Live baselines (verified 2026-09-11, before any Phase 19 edit)

| Harness | Baseline | Notes |
|---|---|---|
| `companion/test_companion_app.py` | 190/192 | 2 pre-existing root-sandbox FAILs (read-only-state-dir resolve + manual-delete). Never "fix" by weakening |
| `companion/test_config_page.py` | 142/142 | clean |
| `companion/test_status_pages.py` | 162/163 | 1 pre-existing root-sandbox FAIL (`anomaly_active()` non-existent state dir) |
| `companion/test_view_pages.py` | 65/65 | clean |
| `companion/test_contrast_check.py` | 36/36 | clean |
| `server/test_config_history.py` | 60/60 | clean |
| `server/test_runway_config.py` | 14/14 | clean |

**`EXPECTED_CHECK_COUNT` rule (every task, no exceptions):** after editing a
harness, RUN it, read the printed `N/M checks pass`, and append a NEW last
`EXPECTED_CHECK_COUNT = M` assignment citing the plan. Never compute M by
arithmetic on an old comment; never edit an older assignment's narration.
`test_companion_app.py` and `test_config_page.py` each contain several historical
assignments and only the LAST one is live.

---

## Sampling Rate

- **After every task commit:** the harness(es) named in that task's `<verify><automated>`
- **After every plan wave:** `scripts/run-all-tests.sh`
- **Before `/gsd:verify-work`:** full suite green except the five documented
  pre-existing root-sandbox artifacts
- **Max feedback latency:** 9 s (slowest single companion harness)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | CFG-03 | T-19-13 | `battery_percent()` degrades (not raises) on non-numeric / non-positive input | unit | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-01-02 | 01 | 1 | CFG-03 | T-19-08 | every reading value crosses `escape_html()` | unit + render | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-01-03 | 01 | 1 | CFG-03 | T-19-08 | verdict text is a module constant, never request data | render | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-02-01 | 02 | 1 | CFG-01 | T-19-02 | a lockout window releases; 5 fresh failures needed to re-arm | unit | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-02-02 | 02 | 1 | CFG-01 | T-19-01 / T-19-07 / T-19-14 / T-19-15 | derived signing key; logout revokes; set prunes; lock guards | unit + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-02-03 | 02 | 1 | CFG-01 | T-19-03 | `Secure` fails closed for any value other than exactly `1` | unit | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-03-01 | 03 | 2 | CFG-06 | T-19-08 | the new `<tr title>` / scroller `aria-label` are escaped | render | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-03-02 | 03 | 2 | CFG-06 | T-19-10 / T-19-16 | no HTML-writing sink; no false success signal | source + render | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-03-03 | 03 | 2 | CFG-06 | T-19-10 | `textContent` on a leaf span only | source + render | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-04-01 | 04 | 2 | CFG-01 | T-19-06 | zero inline `<script>`; the static file is ES5-safe and sink-free | source + render | `server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-04-02 | 04 | 2 | CFG-01 | T-19-05 / T-19-17 / T-19-18 / T-19-19 | CSP on every response incl. redirects; `script-src` strict | real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-04-03 | 04 | 2 | CFG-01 | T-19-04 | `POST /ui-theme` and `POST /logout` require a session | real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-05-01 | 05 | 2 | CFG-03 | T-19-20 | pure threshold functions degrade on None / non-positive input | unit | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-05-02 | 05 | 2 | CFG-03 | T-19-22 | out-of-range `battery_mv` clamps, never escapes the canvas | unit | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-05-03 | 05 | 2 | CFG-03 | T-19-21 / T-19-23 | hostile on-disk interval normalised; registry failure degrades to "no gaps" | unit | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-06-01 | 06 | 3 | CFG-03 | T-19-08 | `caption_title` escaped; output byte-identical when unused | unit | `server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-06-02 | 06 | 3 | CFG-03 | T-19-08 | plain-language labels; technical term only in a `title` | render | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-06-03 | 06 | 3 | CFG-04 / CFG-08 | T-19-24 / T-19-25 | no `adsbdb` / `CFG-\d` in visible text; `#server-data` intact | render | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-07-01 | 07 | 3 | CFG-01 | T-19-27 | every new gate returns before any write (all-or-nothing) | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-07-02 | 07 | 3 | CFG-01 | T-19-26 / T-19-12 | repopulated values escaped; the write-only calendar URL never echoed | render | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-07-03 | 07 | 3 | CFG-01 | T-19-28 / T-19-29 | the re-rendered page is whitelist-selected; the route stays session-gated | real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-08-01 | 08 | 4 | CFG-04 | T-19-08 | strip heading/sentence escaped; already-safe markup not re-escaped | render | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-08-02 | 08 | 4 | CFG-04 | — | N/A (copy + href change) | render | `server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-08-03 | 08 | 4 | CFG-04 | T-19-30 / T-19-31 / T-19-32 | `?edit=` is an exact `"1"` test; the flag is never authorisation | render + real-HTTP | `server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-09-01 | 09 | 4 | CFG-03 | T-19-08 | new button/attribute values escaped; no new CSS | render | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| 19-09-02 | 09 | 4 | CFG-03 | T-19-10 / T-19-33 / T-19-34 / T-19-35 / T-19-36 | DOMParser not `innerHTML`; same-document fetch; non-OK swaps nothing; chart/filter excluded; nav dot swapped | source | inline `python3 -c` token audit of `companion/static/freshness.js` (see plan) | ✅ | ⬜ pending |
| 19-09-03 | 09 | 4 | CFG-03 | T-19-10 / T-19-33 / T-19-35 | the one reviewed sink exception is named and pinned; excluded selectors pinned absent | source | `server/.venv/bin/python3 companion/test_status_pages.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-10-01 | 10 | 4 | CFG-01 | T-19-39 | the fallback Save hides only after the bar is proven present | source + cross-file | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-10-02 | 10 | 4 | CFG-01 | T-19-40 | the unload guard is keyed on the real diff count | source | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-10-03 | 10 | 4 | CFG-01 | T-19-38 / T-19-10 | presets are client-only and still server-validated; no DOM sink | render + source | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-11-01 | 11 | 5 | CFG-01 | T-19-41 / T-19-09 / T-19-42 / T-19-43 | route session-gated; `confirm=yes` required server-side; resolver gates preserved | real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-11-02 | 11 | 5 | CFG-01 | T-19-10 | confirm script is a misclick guard only; no sink, no navigation | source | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-11-03 | 11 | 5 | CFG-01 | T-19-08 | zero `<fieldset>`; every aria id reference resolves | render | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |
| 19-12-01 | 12 | 6 | CFG-01 | T-19-11 / T-19-44 / T-19-45 | `screen_id` membership-tested both ways; no `server/`→`companion/` import; rejected write leaves the file byte-identical | unit | `server/.venv/bin/python3 server/test_config_history.py && server/.venv/bin/python3 server/test_runway_config.py && server/.venv/bin/python3 companion/test_view_pages.py` | ✅ | ⬜ pending |
| 19-12-02 | 12 | 6 | CFG-01 / CFG-04 | T-19-27 / T-19-08 | the `screen_id` gate returns before the single write; option values escaped | render + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py && server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| 19-12-03 | 12 | 6 | CFG-01 | T-19-46 | `next_wake_at_iso()` never raises; the figure is omitted when unknown | unit + render | `server/.venv/bin/python3 companion/test_view_pages.py && server/.venv/bin/python3 companion/test_config_page.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Nyquist compliance:** 36 of 36 tasks carry an `<automated>` verify. No three
consecutive tasks lack one. Task 19-09-02 is the only task whose automated check
is an inline token audit rather than a harness run — its harness coverage lands
in the very next task (19-09-03), which is in the same plan and the same wave.

---

## Wave 0 Requirements

Existing infrastructure covers every phase requirement — all seven harnesses
already exist and run. The five coverage gaps 19-RESEARCH.md identified are
closed by the plan that introduces the behaviour, not by a separate Wave 0:

- [x] lockout-window reset -> new checks in 19-02 Task 1
- [x] token revocation -> new checks in 19-02 Task 2
- [x] redirect carries hardening headers + CSP -> new checks in 19-04 Task 2
- [x] field-level-error 200-render path -> new checks in 19-07 Tasks 1-3
- [x] `poll-cooldown.js` pre-auth / ES5 / route-agreement -> new checks in 19-04 Task 1
- [x] (added by planning) `confirm-submit.js` same three checks -> 19-11 Task 2
- [x] (added by planning) `freshness.js` named sink guard -> 19-09 Task 3

---

## Manual-Only Verifications

`workflow.human_verify_mode` is `end-of-phase`, so these run once, together,
after wave 6 — never as mid-phase checkpoints.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live refresh keeps the chart, the filter, focus and open disclosures alive across an update | CFG-03 | only observable in a real browser over two update cycles; no harness can assert post-swap event-handler liveness | Open Health, wait 2 min: no navigation; "Updated HH:MM" advances; an open "More details" stays open; the sparkline still answers hover and arrow keys; a typed registry filter query survives; the nav Health dot matches the banner; Pause stops and Resume restarts; console shows no CSP violation |
| Theme swatches still render colour under the new CSP | CFG-01 | a blocked inline style attribute produces no error most users would see | Open Display; every theme chip shows its colour band and both swatch dots |
| Poll countdown and "Polling…" affordance survive externalisation | CFG-01 | requires a live cooldown window | During a cooldown, the countdown ticks and re-enables the button; at zero cooldown, clicking disables it and shows "Polling…" |
| Field-level save errors keep the rest of the form | CFG-01 | requires a real browser form round-trip | On Display, change the theme AND clear the quiet-hours Start, save: the new theme is still selected, an error sits under Start, no generic banner, nothing persisted |
| Quiet-hours presets and the unload guard | CFG-01 | native browser dialogs | Tap "Work day" (both times fill, bar appears); tap "Always on" (checkbox unticks, times stay); with unsaved edits click Trigger poll and confirm the browser asks; Save and confirm it does not |
| No-JS paths | CFG-01 | requires disabling JavaScript | With JS off: the bottom "Save settings" button is visible and works; Disconnect lands on a server-rendered confirmation page whose Cancel returns to Device |
| Calendar disconnect confirmation | CFG-01 | native `confirm()` dialog | Click Disconnect: declining changes nothing; accepting disconnects and flashes |
| Screen-reader group semantics | CFG-01 | requires an assistive technology | Theme chips and runway cards announce as named radio groups; each group's hint is read with its control |
| Flights table fit and copy feedback | CFG-06 | visual/interaction | At 1280px the table fits or scrolls with a visible focus ring when tabbed to; a copy click shows "Copied" for ~1.5 s and announces the row's callsign |
| Airlines strip, view-only lightbox, Edit artwork | CFG-04 | visual | `/airlines` shows the strip first with its sentence; a card's lightbox has no replace/upload/delete; `/airlines?edit=1` restores them; Device's "Edit artwork" link opens that view; a gap card's back link returns to Airlines |
| Runway labels and next wake | CFG-01 | visual, and depends on a real check-in history | Runway cards read "Runway 3 (07/25)" etc.; Home shows "Next wake ≈ HH:MM" in Paris time, and nothing at all when the frame has never checked in |
| Health reads in plain language | CFG-03 | editorial judgement | Read the whole page as a household member; no sentence should need the source code. Hovering each tile label reveals its technical term |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (closed in-plan, as tabulated above)
- [x] No watch-mode flags
- [x] Feedback latency < 19s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-11 (planner)
