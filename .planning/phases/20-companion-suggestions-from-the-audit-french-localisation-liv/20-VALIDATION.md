---
phase: 20
slug: companion-suggestions-from-the-audit-french-localisation-liv
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-11
updated: 2026-09-11
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib-only, hand-rolled `check(name, fn)` harnesses — no pytest, no unittest runner; every harness file is directly executable and self-reports `N/M checks pass` |
| **Config file** | none — `scripts/run_all_tests.py` is the canonical harness list |
| **Quick run command** | `PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] \|\| PY=$(command -v python3); "$PY" <harness>.py` |
| **Full suite command** | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |
| **Estimated runtime** | single harness 1–20 s; full suite ~3 min |

**Worktree note:** plans execute in per-wave worktrees that carry no `server/.venv`.
Every `<automated>` command in this phase therefore resolves the interpreter as
`PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] || PY=$(command -v python3)`.
Both interpreters are adequate — every harness in this project is stdlib-only.

**Pre-existing failures that must NOT be "fixed"** (root-sandbox, read-only-directory
cases, five checks across three harnesses): `companion/test_companion_app.py` (2),
`companion/test_status_pages.py` (1), `server/test_manual_resolutions.py` (~2).

**Live baselines at plan time (2026-09-11):** `test_view_pages.py`=85,
`test_config_page.py`=181, `test_companion_app.py`=221, `test_status_pages.py`=191,
`test_contrast_check.py`=36, `server/test_config_history.py`=64,
`server/test_poll_loop.py`=81. Every task re-derives its file's
`EXPECTED_CHECK_COUNT` by running the harness and appending a NEW last assignment
citing its plan — never by arithmetic on an older comment (D-33).

---

## Sampling Rate

- **After every task commit:** run the harness(es) named in that task's `<automated>` block
- **After every plan wave:** `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh`
- **Before `/gsd:verify-work`:** full suite green apart from the five documented root-sandbox checks, `ruff check .` clean, and 20-12's FR/EN sweep recorded
- **Max feedback latency:** 20 s (single harness)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | CFG-13 | T-20-03 | translated text is data: `t()` returns plain text, never pre-escaped markup | unit | `"$PY" companion/test_i18n.py` | ✅ created in-task | ⬜ pending |
| 20-01-02 | 01 | 1 | CFG-13, CFG-18 | T-20-01 / T-20-02 / T-20-04 | both cookie routes session-gated; cookie flags via `secure_cookie_flag()`; only whitelisted lang ids reach `<html lang>` | integration (real HTTP) | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-01-03 | 01 | 1 | CFG-13, CFG-18 | T-20-16 | simple mode omits nav markup only; advanced routes stay gated and reachable | unit + render | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-02-01 | 02 | 1 | CFG-17 | — | the server still imports nothing from `companion/` | unit | `"$PY" companion/test_view_pages.py && "$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-02-02 | 02 | 1 | CFG-17 | T-20-05 / T-20-06 | SSRF gate reused verbatim; failure logging never carries the URL | unit (injected transport) | `"$PY" server/test_notify.py` | ✅ created in-task | ⬜ pending |
| 20-02-03 | 02 | 1 | CFG-17 | T-20-07 / T-20-12 | degrade on read, raise on write; history never records the topic URL | unit | `"$PY" server/test_config_history.py` | ✅ | ⬜ pending |
| 20-03-01 | 03 | 2 | CFG-13, CFG-14, CFG-15 | T-20-03 / T-20-18 | `status_row()` escapes its slots; an unrecognised state cannot reach a class attribute | unit | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-03-02 | 03 | 2 | CFG-13 | T-20-19 | both date helpers still degrade rather than raise | unit | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-03-03 | 03 | 2 | CFG-13 | T-20-03 | every `t()` result stays inside `escape_html()` | render | `"$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-04-01 | 04 | 2 | CFG-14, CFG-15 | T-20-20 / T-20-15 | no new colour literal, no external reference, no inline-style dependency | static + contrast | `"$PY" companion/test_contrast_check.py && "$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-04-02 | 04 | 2 | CFG-15, CFG-16 | T-20-20 | additive rules only; `:has()` degradation documented | static | `"$PY" companion/test_contrast_check.py` | ✅ | ⬜ pending |
| 20-04-03 | 04 | 2 | CFG-14 | T-20-21 | warn-on-card contrast proven at 4.5 in both themes, threshold unweakened | unit | `"$PY" companion/test_contrast_check.py` | ✅ | ⬜ pending |
| 20-05-01 | 05 | 2 | CFG-17 | T-20-17 / T-20-22 / T-20-23 | one push per transition; a raising sender never propagates | unit (injected sender) | `"$PY" server/test_poll_loop.py` | ✅ | ⬜ pending |
| 20-05-02 | 05 | 2 | CFG-17 | T-20-17 / T-20-22 | silence threshold is the shared WARN value, never re-tuned | unit (injected sender) | `"$PY" server/test_poll_loop.py` | ✅ | ⬜ pending |
| 20-06-01 | 06 | 3 | CFG-14, CFG-18 | T-20-03 / T-20-25 | the frame verdict renders exactly once; no quick-action markup remains | render | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 20-06-02 | 06 | 3 | CFG-14 | T-20-24 | the illustration key comes from the existing resolver; a falsy key renders no `<img>` | render | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 20-06-03 | 06 | 3 | CFG-13 | T-20-03 | French render escapes identically to English | render | `"$PY" companion/test_view_pages.py && "$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-07-01 | 07 | 3 | CFG-15 | — | every moved form returns to Display | render | `"$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-07-02 | 07 | 3 | CFG-15 | T-20-27 / T-20-26 | no `<form>` nested in a `<form>`; a same-field POST saves the same config | render + round-trip | `"$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-07-03 | 07 | 3 | CFG-13, CFG-18 | T-20-03 | translated settings copy stays escaped; Device loses the artwork link | render | `"$PY" companion/test_config_page.py && "$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-08-01 | 08 | 3 | CFG-16 | T-20-14 | only an int event id reaches a cache filename | unit | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-08-02 | 08 | 3 | CFG-16 | T-20-14 / T-20-29 | membership test stays first; every failure degrades to 404 or the sample scene | integration (real HTTP) | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-08-03 | 08 | 3 | CFG-16 | T-20-15 | script served from its own route; no inline script; route equals src | integration + static | `"$PY" companion/test_companion_app.py && "$PY" companion/test_status_pages.py` | ✅ | ⬜ pending |
| 20-09-01 | 09 | 4 | CFG-15, CFG-18 | T-20-12 / T-20-30 | write-only URL field; failures render mapped sentences, never exception text | render | `"$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-09-02 | 09 | 4 | CFG-15 | T-20-10 / T-20-11 | connect is session-gated and provably leaves Quiet hours and the screen ON | integration (real HTTP) | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-09-03 | 09 | 4 | CFG-13, CFG-15, CFG-18 | T-20-03 | rule keys, callsigns and `data-*` values all escaped | render | `"$PY" companion/test_config_page.py && "$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-10-01 | 10 | 4 | CFG-18 | T-20-16 / T-20-31 | the button hides in simple mode; the `?edit=1` route still works | render | `"$PY" companion/test_view_pages.py` | ✅ | ⬜ pending |
| 20-10-02 | 10 | 4 | CFG-13 | T-20-03 | airline names and codes unchanged in both languages | render | `"$PY" companion/test_view_pages.py && "$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-10-03 | 10 | 4 | CFG-13 | T-20-03 | flight data unchanged in both languages | render | `"$PY" companion/test_view_pages.py && "$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-11-01 | 11 | 5 | CFG-17 | T-20-13 / T-20-12 | the test route reads the URL from config only; no part of it is ever rendered | render + integration | `"$PY" companion/test_config_page.py && "$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-11-02 | 11 | 5 | CFG-16 | T-20-14 / T-20-15 | preview srcs built from the route prefix and a registry key; no inline script | render | `"$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-11-03 | 11 | 5 | CFG-13 | T-20-03 / T-20-15 | `data-*` text escaped; scripts write text, never `innerHTML` | static + render | `"$PY" companion/test_companion_app.py && "$PY" companion/test_view_pages.py && "$PY" companion/test_config_page.py` | ✅ | ⬜ pending |
| 20-12-01 | 12 | 6 | CFG-13 | T-20-33 | the scanner parses source and never imports a page module | unit (AST) | `"$PY" companion/test_i18n.py` | ✅ | ⬜ pending |
| 20-12-02 | 12 | 6 | CFG-18 | T-20-16 / T-20-32 | simple mode is presentation only; sweep artefacts stay out of the repo | integration (real HTTP) + headless sweep | `"$PY" companion/test_companion_app.py` | ✅ | ⬜ pending |
| 20-12-03 | 12 | 6 | CFG-13, CFG-18 | — | documentation only; no runtime surface | static | `"$PY" companion/test_contrast_check.py && grep -c "fixed (phase 20)" .planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No separate Wave 0 is needed: every harness this phase touches already exists,
and the two new ones are created inside the wave-1 task that first needs them,
before any code depends on them.

- [x] `companion/test_i18n.py` — created by 20-01 Task 1 (round-trip, fallback,
      merge and boundary checks), extended by 20-12 Task 1 with D-08's
      completeness and dead-translation checks
- [x] `server/test_notify.py` — created by 20-02 Task 2 (injected transport:
      success, non-2xx, timeout, exception, four SSRF refusals)
- [x] Harness registration — 20-02 Task 2 adds both new files to
      `scripts/run_all_tests.py`'s canonical list (that plan owns the runner file
      so the two wave-1 plans never edit it together; it therefore does not run
      the full suite as its own gate)
- [x] Home's test ownership — resolved before planning (20-RESEARCH.md Open
      Question 2): `companion/test_view_pages.py` owns all 13 `home_page.`
      references; no `test_home_page.py` is created

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A push actually arrives on a phone for a battery-low transition, a frame-silent transition and the "Send a test" button | CFG-17 | Delivery requires a real ntfy topic and a real device; every automated check uses an injected transport and must never contact a live endpoint | Configure a real topic on Device → Notifications, press "Send a test", then let the frame miss three wake intervals and come back |
| The native `confirm()` dialog appears before disconnecting a calendar and before removing a flight-colour rule | CFG-15 | Browser-native dialog, not observable from a server-side render | Click Disconnect and Remove in a real browser with JS enabled |
| A screen reader announces the three nav-footer switch groups by their `aria-label`s | CFG-13, CFG-18 | Requires assistive technology | Navigate the footer with VoiceOver/NVDA |
| Chip selection swaps the live preview with no page reload and no CSP error | CFG-16 | Requires a real browser console | Select several chips on Display and watch the console |
| FR/EN layout sweep at 1280 and 390 px, light and dark, across six pages | CFG-13, CFG-14, CFG-15 | Automated in 20-12 Task 2 via the Playwright CLI where it can drive a browser; falls back to a human check if it cannot, and the summary must say which happened | 24 screenshots; assert no horizontal overflow and no CSP console message |
| The ten browser-only checks recorded in 19-VERIFICATION.md still pass | CFG-01, CFG-03 | Carried over from phase 19; browser-only by nature | Re-run that list after this phase merges |

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify command; none depends on a missing file
- [x] Sampling continuity: every task runs at least one harness — no three consecutive tasks without automated verification
- [x] Wave 0 covers all MISSING references (both new harnesses are created in the wave-1 task that introduces their subject)
- [x] No watch-mode flags
- [x] Feedback latency < 20 s per task
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-09-11
</content>
