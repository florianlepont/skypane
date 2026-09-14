---
phase: 25
slug: companion-dynamism-iii-controls-the-modern-controls-that-rep
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-13
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | This project's own hand-rolled harnesses — a module per surface, each a list of named checks with an `EXPECTED_CHECK_COUNT` pin. No pytest, no unittest. A check is a function returning `(bool, message)` registered with a human-readable NAME; **the name is the identity, never the index**. |
| **Config file** | none — `scripts/run_all_tests.py` holds the harness list, concurrency and per-harness timeout; `scripts/run-all-tests.sh` owns the stable `PYTHON` contract |
| **Quick run command** | `PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] \|\| PY=$(command -v python3); "$PY" companion/<the harness this task touches>.py` |
| **Full suite command** | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |
| **Estimated runtime** | single harness: seconds. Full suite: minutes — the browser harness drives a real Chromium at five viewports in two languages and is the only long pole. |

**Baseline (verify by NAME, never by failing-file count):** exactly **5** failing
checks in this sandbox — 4 × WR-11 (read-only filesystem) and 1 ×
`anomaly_active()`. A plan reporting a different count must name which check moved
and why. `EXPECTED_CHECK_COUNT` is re-derived by **running** the harness and
appended as a NEW last assignment citing the plan and task — never by arithmetic.

**The instrument that matters most in this phase:** `companion/test_browser_ux.py`.
Every claim this phase makes is about behaviour a string comparison cannot see —
does the control still save with scripts blocked, is it operable from the keyboard,
is its hit area real at 360 px. A `SKIP` line from that harness means **none** of
those contracts was checked, so a SKIP is a failed phase gate, not a caveat.

---

## Sampling Rate

- **After every task commit:** the touched harness, plus `ruff check .`
- **After every plan (all tasks):** `companion/test_companion_app.py`,
  `companion/test_config_page.py`, `companion/test_status_pages.py`,
  `companion/test_i18n.py` — the four that any companion change can move
- **After every wave:** full suite
- **Before `/gsd:verify-work`:** full suite green against the 5-check baseline, and
  the browser harness NOT skipping
- **Max feedback latency:** single harness < 60 s; the browser harness is sampled
  per plan, not per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | CFG-46 | T-25-01-A / T-25-01-B | a clamped value bounded by `device_config`; a new static route behaving exactly as the sixteen existing ones | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 25-01-02 | 01 | 1 | CFG-46 | — | a script-only affordance cannot render without script | unit (stylesheet scan) | `… companion/test_status_pages.py` | ✅ | ⬜ pending |
| 25-01-03 | 01 | 1 | CFG-49 | T-25-01-D | no lifetime claim beyond what observed history supports | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 25-01-04 | 01 | 1 | CFG-46 | — | the no-JS contract fails on a wrong control (two mutations) | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 25-02-01 | 02 | 1 | CFG-52 | — | the scripts-blocked proof is operate-submit-**persist** | browser (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-02-02 | 02 | 1 | CFG-52 | — | keyboard operability with zero pointer events; real hit-tested area | browser (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-02-03 | 02 | 1 | CFG-52 | T-25-02-A | the gate asserted in BOTH directions; themes via 24-02's switch | browser (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-03-01 | 03 | 2 | CFG-47 | T-25-03-B / T-25-03-D | registry text escaped; an unparseable designator degrades, never raises | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-03-02 | 03 | 2 | CFG-47 | — | every emitted class resolves; one feature query; no colour literal | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-03-03 | 03 | 2 | CFG-47, CFG-52 | T-25-03-A | the runway PERSISTS with scripts blocked; hit areas real at 360 px | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-04-01 | 04 | 3 | CFG-48 | T-25-04-C | the wrapping-midnight span, asserted AT the boundary | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-04-02 | 04 | 3 | CFG-48 | T-25-04-B | the arc renders server-side; B14's sibling byte-identical | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-04-03 | 04 | 3 | CFG-48, CFG-52 | T-25-04-A | handles announce via aria-valuetext; nothing is a live region | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-04-04 | 04 | 3 | CFG-48, CFG-52 | T-25-04-D | the window PERSISTS with scripts blocked; handles ≥44 px when close | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-05-01 | 05 | 4 | CFG-49 | T-25-05-C | the battery sentence never exceeds what `battery.py` supports | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-05-02 | 05 | 4 | CFG-49 | T-25-05-A / T-25-05-D | the range has no `name`; bounds read from `device_config` | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-05-03 | 05 | 4 | CFG-49, CFG-52 | T-25-05-B | the stored-below-floor case still submits the whole form | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-06-01 | 06 | 5 | CFG-50 | — | Display's page height recorded BEFORE any change | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-06-02 | 06 | 5 | CFG-50 | T-25-06-D | one chip renderer; ONE feature query; three grids untouched | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-06-03 | 06 | 5 | CFG-50 | T-25-06-B | one radio set (or a named, asserted sync); no `<dialog>`; no new script | unit | `… companion/test_config_page.py` | ✅ | ⬜ pending |
| 25-06-04 | 06 | 5 | CFG-50, CFG-52 | T-25-06-A | the theme PERSISTS with scripts blocked; the height reported honestly | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-07-01 | 07 | 6 | CFG-51 | T-25-07-E | both upload forms byte-identical; ids document-unique | unit | `… companion/test_status_pages.py` | ✅ | ⬜ pending |
| 25-07-02 | 07 | 6 | CFG-51 | T-25-07-A / T-25-07-B / T-25-07-D | no canvas API; the normaliser untouched; object URLs revoked | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 25-07-03 | 07 | 6 | CFG-51, CFG-52 | T-25-07-C | artwork uploads with scripts blocked; dropped ≡ picked | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 25-08-01 | 08 | 7 | CFG-46…52 | T-25-08-B | every recorded number read from the code at execution time | full suite | `bash scripts/run-all-tests.sh` | ✅ | ⬜ pending |
| 25-08-02 | 08 | 7 | CFG-46…52 | T-25-08-A | no requirement complete with an unaccounted clause | full suite | `bash scripts/run-all-tests.sh` | ✅ | ⬜ pending |
| 25-08-03 | 08 | 7 | CFG-46…52 | — | baseline by NAME; no SKIP; five named no-JS persistence checks | full suite + browser | `bash scripts/run-all-tests.sh && … companion/test_browser_ux.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Sampling adequacy — the Nyquist question

A check that only exercises a comfortable value is **vacuous** for most of the
states this app actually reaches. Every control must be asserted across these
axes, because each is a real state of this deployment:

| Axis | Values that must appear |
|---|---|
| Scripts | on **and** blocked (`_no_js_page()`) |
| Input modality | pointer **and** keyboard-only (zero pointer events) |
| Theme | light **and** dark (24-02's switch) |
| Viewport | 360 px (contract floor) and 390 px; 1280 px where layout differs |
| Language | English and French — French strings are longer and have overflowed before |

Plus, **per control**, the states that are not the happy path:

| Control | The states a happy-path check would miss |
|---|---|
| D16 runway map | no runway selected; `images_available=()`; a registry id that does not parse as a bearing; a fourth registry entry |
| D17 dial | a window that **wraps midnight** (the default, 23:00→07:00); equal start and end; a 24-hour window; an unparseable stored time; handles close enough to overlap at 360 px |
| D18 slider | `WAKE_INTERVAL_MIN_S` and `MAX_S` exactly; a **stored value below the floor** (real — `deploy/skypane.env.example` ships 30); a rejected save's raw echo; a battery history too thin for an absolute figure; a **rising** battery series |
| D5 carousel | eighteen chips at 360 px; the disclosure closed and open; the other three grids unchanged |
| D19 drop zone | a non-PNG; an oversized file; both copies of both forms on one page; a dropped file vs a picked file |

**The single most likely arithmetic defect in the phase** is the wrapping-midnight
window, because the default configuration uses one: an implementation computing
`end - start` renders an eight-hour window as sixteen hours and labels it
confidently. It is asserted **at** the boundary (23:00→07:00 = 480 min;
23:59→00:00 = 1 min), not near it.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements, with two cross-phase
dependencies that must be present before wave 1 completes:

- [x] `companion/test_browser_ux.py` `_no_js_page()` — **already exists** (23-02).
      Its own docstring names the five controls this phase builds.
- [ ] `companion/test_browser_ux.py` theme switch — **owned by 24-02**, not by this
      phase. 25-02 calls it. If it has not landed, 25-02 STOPS rather than building
      a second theme mechanism.
- [ ] `companion/draw.py` — **owned by 24-01**. 25-03 and 25-04 use its viewBox
      scale helper if present and keep geometry local if not, stating which.
- [ ] `companion/battery.py`'s CFG-39 extensions — **owned by 24-01**. 25-01 extends
      the same module; it must re-read rather than assume the 38-line shape.
- [ ] No framework install needed. Playwright 1.62.0 is already pinned in
      `server/requirements-dev.txt` and never reaches the VPS.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The dial's handles when the quiet window's two ends are close | CFG-48 | A real thumb on a real 360 px phone is the only instrument that settles whether two handles a few tens of pixels apart are separable. The harness can measure the boxes; it cannot tell you the control feels wrong. | On a real Android at 360 px, set a window of about 90 minutes and try to move each end independently, by thumb, in both themes |
| The battery gauge's wording | CFG-49 | The claim's honesty is a judgement, not a measurement. The harness proves no number appears without history; only the developer can say whether the sentence reads as an estimate or as a fact. | Read the sentence in both languages with a thin history and with a full one; decide whether to accept, soften, or drop the claim |
| Display's page height outcome | CFG-50 | X6 has now been attempted twice; the number is measured, but whether it is *enough* is the developer's call | Compare 25-06's before/after numbers against the audit's target and say whether the item is closed |
| The three clauses removed from D19 | CFG-51 | Each is a deliberate reduction of what the audit asked for; reversing any is the developer's decision | Review the SUMMARY's three grounds and accept or reverse each |
| Five controls judged together, real device | CFG-52 | 06.6.1-06's precedent: a real-device session found two confirmed CSS defects no harness had caught | A real phone at 360 px and a desktop, both themes, both languages, operating every control by touch and by keyboard |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a named cross-phase dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0's four cross-phase dependencies confirmed present before wave 2 begins
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s per harness
- [ ] The browser harness does not SKIP at the phase gate
- [ ] Five named no-JS persistence checks exist, one per control
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
