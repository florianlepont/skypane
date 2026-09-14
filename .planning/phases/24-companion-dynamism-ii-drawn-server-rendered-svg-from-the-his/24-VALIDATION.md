---
phase: 24
slug: companion-dynamism-ii-drawn-server-rendered-svg-from-the-his
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-13
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | This project's own hand-rolled harnesses — a module per surface, each a list of named checks with an `EXPECTED_CHECK_COUNT` pin. No pytest, no unittest. A check is a function returning `(bool, message)` and is registered with a human-readable NAME; the name is the identity, never the index. |
| **Config file** | none — `scripts/run_all_tests.py` holds the harness list, concurrency and per-harness timeout; `scripts/run-all-tests.sh` owns the stable `PYTHON` contract CI and README both depend on |
| **Quick run command** | `PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] \|\| PY=$(command -v python3); "$PY" companion/<the harness this task touches>.py` |
| **Full suite command** | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |
| **Estimated runtime** | single harness: seconds. Full suite: minutes (the browser harness drives a real Chromium at five viewports in two languages). |

**Baseline (verify by NAME, never by failing-file count):** exactly **5** failing
checks in this sandbox — 4 × WR-11 (read-only filesystem) and 1 ×
`anomaly_active()`. A plan that reports a different count must name which check
moved and why. `EXPECTED_CHECK_COUNT` is re-derived by **running** the harness and
appended as a NEW last assignment citing the plan and task — never by arithmetic.

---

## Sampling Rate

- **After every task commit:** the touched harness, plus `ruff check .`
- **After every plan (all tasks):** `companion/test_companion_app.py`,
  `companion/test_status_pages.py`, `companion/test_view_pages.py`,
  `companion/test_i18n.py` — the four that every companion change can move
- **After every wave:** full suite
- **Before `/gsd:verify-work`:** full suite green against the 5-check baseline
- **Max feedback latency:** single harness < 60 s; browser harness is the only
  long pole and is sampled per plan, not per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | CFG-39 | — | estimator constants exist in exactly one module | unit | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 24-01-02 | 01 | 1 | CFG-39 | — | drawing primitives escape every interpolated value | unit | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 24-01-03 | 01 | 1 | CFG-39/45 | T-24-01 | no colour literal, no unpainted shape, every emitted class resolves | source scan | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 24-02-01 | 02 | 1 | CFG-45 | — | both-theme paint helper reports the real computed paint | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-02-02 | 02 | 1 | CFG-45 | — | 360 px body-overflow helper fails on a deliberately wide element | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-03-01 | 03 | 1 | CFG-43 | T-24-03 | gap reader uses ALL rows, not the battery-filtered subset | unit | `"$PY" server/test_config_history.py` + the new reader harness | ✅ | ⬜ pending |
| 24-03-02 | 03 | 1 | CFG-43 | — | gap verdicts reuse `wake.device_staleness_thresholds()` | unit | new reader harness | ✅ | ⬜ pending |
| 24-03-03 | 03 | 1 | CFG-43 | T-24-03 | epoch write is deduped and never runs on an unchanged interval | unit | `"$PY" server/test_poll_loop.py` | ✅ | ⬜ pending |
| 24-04-01 | 04 | 2 | CFG-40 | — | one ring emitter, two sizes, arc length tracks the fraction | unit | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 24-04-02 | 04 | 2 | CFG-40/45 | — | ring paints in both themes, fits 360 px, viewBox contains its label | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-05-01 | 05 | 3 | CFG-41 | — | area/threshold/last point derive from the SAME filtered pair list | unit | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 24-05-02 | 05 | 3 | CFG-41/45 | — | chart still fills its card at 360 px with no body scrollbar, keyboard path intact | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-06-01 | 06 | 4 | CFG-42 | — | timeline is a Paris day; collapsed ticks never inflate a count | unit | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 24-06-02 | 06 | 4 | CFG-42/45 | — | timeline renders with scripts blocked at 360 px | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-07-01 | 07 | 5 | CFG-43 | — | grid claims only observed regularity; caption carries the two caveats | unit | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 24-07-02 | 07 | 5 | CFG-43/45 | — | grid cells legible in both themes at 360 px; SVG text inside its viewBox | browser | `"$PY" companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 24-08-01 | 08 | 6 | CFG-44 | — | the hero calls the SAME emitters; mutating one changes the hero | unit | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 24-08-02 | 08 | 6 | CFG-44/45 | — | Home renders the Frame verdict exactly once, still | unit | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 24-09-01 | 09 | 7 | CFG-39..45 | — | design system updated in step; coverage ledger; full-suite gate | suite | `PYTHON=… bash scripts/run-all-tests.sh` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The five harnesses this
phase moves (`test_companion_app.py`, `test_status_pages.py`,
`test_view_pages.py`, `test_browser_ux.py`, `test_i18n.py`) all exist and all
already carry the idioms this phase needs. The one genuinely new surface —
server-side readers over `device_health` gaps — gets its checks in plan 24-03,
which is itself in wave 1.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The drawings look right, not merely correct | CFG-39..45 | "A ring gauge that reads as a battery" is a judgement no assertion makes | Plan 24-09's `<human-check>`: open Home and Health at 360 px and at 1280 px, in both themes and both languages, with scripts on and blocked, and confirm each drawing reads as what it claims |
| The gradient area does not muddy the line in dark mode | CFG-41 | Contrast of a translucent fill over a card background at a given opacity is a visual call | Same sweep; compare against the pre-phase chart |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references — n/a, none missing
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s per task harness
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
