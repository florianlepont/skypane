# Phase 22: Companion audit round 4 — Research

**Researched:** 2026-09-12
**Domain:** Stdlib-only Python HTTP companion service (hand-rolled routing, hand-written CSS, ES5 vanilla JS) — bug-fix/hardening pass against a fully-specified audit ledger, plus one new browser-level test harness.
**Confidence:** HIGH (the fix surface was read live, file:line, against the current tree; no unverified library claims are load-bearing except the one new dev dependency, Playwright, which is verified below)

## Summary

This phase is not exploratory — `22-AUDIT.md` and `22-CONTEXT.md` already name every defect, its file:line, and its locked fix direction. What a planner needs from research is: (1) the *exact* mechanism for the one blocker (B1) and confirmation it is structurally safe, (2) the concrete subprocess-harness pattern to clone for the new Playwright harness and how it plugs into `scripts/run_all_tests.py`, (3) where the single next-wake computation must live and what inputs it needs, (4) **two non-obvious regression traps that are NOT named explicitly in the audit but WILL ship a new, worse bug if missed** — both documented in detail below (display_enabled/quiet_hours_enabled absent-means-False on the settings POST, and a pinned SCOPE_ALL union test), and (5) a wave grouping that keeps the ~49 items from having two plans collide on the same file in the same wave.

**Primary recommendation:** Sequence B1+D-02 (the harness) first and alone, since every later plan's "prove it with the browser" checks depend on the harness existing; then split the remaining ~48 items by file-ownership into non-overlapping waves (grouping detailed in Question 7 below), landing the two silent-regression traps (X1/D-04's checkbox removal, D-03's quiet-hours-aware wake) as their own reviewed units rather than folding them into a larger CSS-focused plan.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dirty-state detection (B1) | Browser (JS) | — | `dirty-state.js` is pure client-side DOM diffing; no server change needed |
| Playwright harness (D-02) | Test tooling (dev-only) | — | Runs outside the request path; must never reach `server/requirements.txt` or a deployed unit |
| Next-wake computation (X2/D-03) | API/Backend (`server/wake.py`) | Frontend render (`layout.py`, page modules) | One computation, many render-time consumers — must not be duplicated per-page |
| Screen/quiet-hours on-off state (X1/D-04) | API/Backend (`server/device_config.py` write path) | Frontend (Frame strip forms, Settings form) | The strip's own dedicated `/quick/*` routes already own the write; the settings form must stop being a second writer |
| Time formatting (D-05) | Frontend render (`companion/layout.py`) | Frontend JS (reads server-rendered text only) | All JS files already read pre-formatted `data-when`/`data-*` text; no client-side date math exists or is needed |
| Daily battery bucketing (D-05) | Backend (`server/history_db.py`) | — | Requires moving day-bucketing from SQL `date()` (UTC-only) to Python (`ZoneInfo("Europe/Paris")`) |
| i18n completeness (D-06) | Backend/render (`companion/i18n.py`, page modules, `app.py`) | Test tooling (`test_i18n.py`'s AST scanner) | Flash/title copy must first *route through* `i18n.t()` before any scanner can see it |
| Visual/layout defects (D-07/D-08) | Frontend (CSS/markup) | — | `companion/static/style.css` + page-module markup only; no backend change |

## User Constraints (from CONTEXT.md)

<user_constraints>
### Locked Decisions

Every entry below is LOCKED: it comes from `22-AUDIT.md`, which the developer validated in full on 2026-09-12 ("Je valide l'ensemble des points remontés"). The audit's own "Fix / next step" column is the decision; the planner may choose mechanism, not outcome.

- **D-01 — The blocker is the first plan, and it ships with its own guard (B1, CFG-25).** `dirty-state.js` must detect changes to fields that are attached to `#settings-form` by the `form=` attribute while living outside the element. Delegate at document level and gate on `e.target.form === form`; keep `dirtySectionLabels()` working off `form.elements` intersected with each `[data-dirty-section]` wrapper's `contains()`. The fallback Save button must stay reachable until the bar has actually been shown once — hiding it on the mere presence of `.dirty-ready` is what turned a JS defect into "no way to save at all." This plan does not land without the harness in D-02.
- **D-02 — A minimal Playwright harness, dev-dependency only (CFG-25).** Covers, against a seeded temp state directory using the existing `Harness` subprocess pattern from `companion/test_companion_app.py`: (1) clicking a theme chip / a runway card / the Enable-display checkbox / a quiet-hours time makes the save bar visible, names the right section, and the save actually persists; (2) the same for Device scope; (3) the mobile nav opens/closes, leaving `hidden`/`aria-expanded` consistent (T5); (4) a Flights detail row expands/collapses; (5) Cancel restores the form AND the live theme preview (T8), and the leave-guard re-arms on the next edit (T1). Playwright is dev-only — never `server/requirements.txt`, never a deployed unit. Skips (not fails) with a clear message when the browser is unavailable.
- **D-03 — One next-wake truth, quiet-hours aware, with a grace window (X2, CFG-26).** `server/wake.py`'s next-wake computation becomes the single source consumed by the Frame strip headline, the Home/Health status tiles and every settings caption. Must account for an active quiet-hours window (device held until the window ends) and a screen switched off (`DISPLAY_OFF_SLEEP_S`). No warning state may be shown before a grace window of 2× the effective interval. Neutral copy while held ("Next wake around 07:05 · quiet hours"), never "Expected since." Strip and tile must not disagree. Live refresh (D1) is explicitly out of scope — a page load must simply be correct.
- **D-04 — One control per setting, one delay sentence (X1, CFG-27).** The Frame strip owns Screen on/off and Quiet hours on/off. `companion/screens.py` stops listing `GROUP_DISPLAY`/`GROUP_QUIET_HOURS`'s on/off controls as everyday form groups; the settings form keeps only the quiet-hours **schedule** (start, end, presets). One computed sentence states when a change reaches the frame, replacing all three of today's wordings. The "within about 5 minutes" claim (`config_page.py:444-448`) must be verified against `server/wake.py:114-115` and the firmware before reuse — the audit's reading is it holds only when the display is already off. Pressing a strip switch with unsaved form edits must not trigger the leave-page dialog. The nav reminder stays only if it links somewhere useful; its `aria-label` must not say "go to Home" when already on Home.
- **D-05 — Paris local time everywhere (B4, B5, CFG-28).** `layout.local_clock_text()` is the only formatter for visible times — covers `_battery_reading_parts()`, every sparkline tooltip/aria-label/`data-when`, `battery-trend.js`'s hover swap and raw-ISO fallback, `_axis_clock_label()`, and the airline resolve dialog's `data-first-seen`/`data-last-seen` (no-JS path already formats them — the two paths must agree). Daily battery buckets group by Europe/Paris calendar day, not UTC. Every `title` tooltip carries a local full timestamp; raw ISO survives only behind a copy control. `concise_timestamp_html()`'s stale docstring (still promises `"<HH:MM> UTC (<relative>)"`) is corrected.
- **D-06 — French completeness (B16, CFG-29).** Flash banners route through `i18n.t`. Page `<title>`s are translated, including login and 404. Plurals gain singular forms. `aria-label="Primary navigation"`, "Light"/"Dark" segments and CSS `content: "Current"` (must become a server-rendered `data-*` string — T10) are translated. The battery caption stops naming the constant when the real count differs. `test_i18n.py` widened to cover `app.py`, attribute literals, and JS-side fallbacks. Strings from `server/` are noted, not necessarily moved.
- **D-07 — The visible defects, as measured (B2–B18, X3–X9, CFG-30).** Each item locked to the audit's own fix direction; the "Pixel measurements" table in `22-AUDIT.md` is the acceptance target. (Full per-item list preserved verbatim in `22-CONTEXT.md`; not repeated here — see that file.)
- **D-08 — Design contract and code defects (C1–C6, T1–T16, CFG-31).** `sketch-findings-skypane` is the authority and must be updated in step with whatever this phase changes. (Full per-item list preserved verbatim in `22-CONTEXT.md`.)
- **D-09 — Regression floor.** Every existing harness keeps passing and counts move only where a plan's own change forces it. The no-JS floor holds. No new runtime dependency in `server/requirements.txt`; no vendored library; CSP stays `script-src 'self'` with no `unsafe-inline` and no nonce.

### Claude's Discretion

- Plan count, wave grouping and file-level sequencing.
- The exact mechanism for each fix where the audit names an outcome (e.g. whether X9 becomes bottom tabs or an overlay drawer; whether B9 uses fixed columns or a list).
- Which `T16` debt items ride along with a plan that already touches the code.
- Whether the shared next-wake code (D-03) lands in `server/wake.py` or a new module, as long as there is exactly one implementation.
- Test-harness file naming and how the browser-unavailable skip is reported.

### Deferred Ideas (OUT OF SCOPE)

- **All of D1–D24** — the dynamism half of the audit (SSE stream, fetch switches, motion budget, View Transitions, Home hero redesign, day timeline, runway map, quiet-hours dial, wake-interval slider, theme carousel, battery ring, punctuality grid, prefetch/gzip, offline shell, manifest, share, drag-and-drop upload, command palette, guided first run). Moved to Phase 23.
- **T16's stylesheet-wide debt** — gzip/hashed filenames, a `--color-text-muted` token, the 13 duplicated label-voice blocks, dead selectors, a shared `ui.js` helper module. Optional here, only where a plan already touches that code.
- **Real-device verification** — iPhone/Android rendering belongs to phase-level UAT, not to a plan.

**Boundary rule for the planner:** a fix that *happens* to add motion or a fetch call is out of scope unless the audit item itself requires it. Three named exceptions: X2 requires a shared next-wake computation (server-side only, no client polling — live refresh is Phase 23); X3 may add a show-password toggle and a live lockout countdown (both named in the audit's own fix column, local to the login card); T13 requires retry/backoff and a visible paused/reconnecting state in the *existing* `freshness.js` loop (repairing a loop that already exists, not adding a new one).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-25 | Every setting on Display can be saved from a browser with JS on — the save bar appears whenever any field changes, the fallback Save stays reachable until it does, and a browser-level test harness exercises the interactions string-comparison harnesses cannot see | Question 1 (B1 mechanism) and Question 2 (D-02 harness pattern) below give the exact edit and the exact subprocess/harness idiom to clone |
| CFG-26 | The frame's state reads the same everywhere — one quiet-hours- and screen-off-aware "next wake" estimate feeds the strip, the status tiles and the settings captions, with a grace window before any warning | Question 3 gives the current computation (`server/wake.py`), the three independent consumers that disagree today, and the exact formula (`quiet_hours_sleep_s(display_off_sleep_s(...))`) the fix must reproduce |
| CFG-27 | Each frame setting has one control and one stated delay — the Frame strip owns on/off, the settings form keeps only the schedule, one computed sentence states delay | Question 4 gives the `screens.py` registry mechanics AND the two absent-means-False write-path traps that must be fixed alongside the markup removal or the phase ships a worse regression |
| CFG-28 | Every visible time is Paris local time, including the battery readout/chart, every tooltip, and the airline resolve dialog; raw ISO only behind a copy control | Question 5 enumerates every formatter, confirms JS files do no client-side date math (fix is 100% server-side), and identifies the SQL→Python day-bucketing refactor `daily_battery_averages()` needs |
| CFG-29 | No English leaks into French; the completeness harness covers what it currently cannot see | Question 6 documents the AST-scanner's exact exclusion mechanics and what "widening to app.py/attributes/JS fallbacks" concretely requires |
| CFG-30 | The everyday pages are visually correct and honest (per audit's pixel table) | Question 7/8 — file-collision map and pitfall list (design-system contradiction for X9, touch-target register, `:has()` count pin) |
| CFG-31 | The stylesheet/scripts hold the design contract (serif boundary, accent reservation, hover/focus states, verified CSS/JS defects) | Question 8 — pitfall list; SKILL.md and its references are the authority and must be updated in the same plan that changes the contract |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

CLAUDE.md's own content is entirely about the *hardware/firmware/API* side of SkyPane (ESP-IDF, AeroDataBox, PRIM, Hetzner) and does not speak to the companion web app directly. Two directives are still load-bearing for this phase:
- **GSD Workflow Enforcement**: all edits must happen through a GSD command (`/gsd-execute-phase` etc.) — no direct repo edits outside the workflow.
- No conflicting stack guidance exists for `companion/` — this phase's actual authority is `sketch-findings-skypane` (design contract) plus the codebase's own established conventions (stdlib-only, ES5-only JS, no build step), both confirmed live below.

## Standard Stack

### Core

No new production dependency of any kind. Zero packages are added to `server/requirements.txt`. This phase is a bug-fix/hardening pass against an existing stdlib-only Python service, hand-written CSS, and ES5 vanilla JS.

### Supporting (dev-only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `playwright` | 1.62.0 (latest on PyPI at research time) | Browser automation for the new D-02 harness | Official Microsoft package; the de facto standard for headless-browser test automation in Python; matches CONTEXT.md D-02's explicit ask for a "minimal Playwright harness" |

**Installation (dev-only, mirrors the existing `server/requirements-dev.txt` convention — see Package Legitimacy Audit and Code Examples below):**
```bash
pip install playwright
python -m playwright install chromium   # downloads only the one browser needed
```

**Version verification:** `pip index versions playwright` confirms `1.62.0` is current on PyPI (verified live, 2026-09-12). Official docs confirm the two-step install (`pip install playwright` then `python -m playwright install`) at https://playwright.dev/python/docs/intro `[VERIFIED: PyPI registry + playwright.dev official docs]`.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright | Selenium | Selenium has no first-class async/sync dual API and a heavier driver-management story (webdriver-manager or manual chromedriver pinning); Playwright's `playwright install` step is simpler and is what CONTEXT.md D-02 already names by product name — not worth reopening |
| A real browser harness | Continue string-comparison-only testing | Rejected by the phase itself — B1 is precisely the class of defect (event delegation across a DOM boundary) that no string-comparison harness can ever catch, per `22-AUDIT.md`'s own finding |

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|--------------|-----------|-------------|
| `playwright` | PyPI | Years (Microsoft-maintained since ~2020) | Very high (millions/week class) | github.com/microsoft/playwright-python | [OK] (verified live via `slopcheck install playwright --ecosystem pypi`, 2026-09-12) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

No postinstall-script check applies (this is a Python/pip package, not npm); `pip show playwright` confirms no arbitrary install-time script execution beyond the standard wheel build. The one operationally-relevant follow-up step, `python -m playwright install chromium`, downloads a browser binary — this is a normal, documented, opt-in step (not a hidden postinstall hook) and must be a separate, visible CI step (see Environment Availability below), never silently bundled into `pip install`.

## Architecture Patterns

### System Architecture Diagram (the two structural fixes: B1 and X2/D-03)

```
B1 — dirty-state.js delegation fix
──────────────────────────────────
  User clicks a theme chip / runway card / display checkbox
  (physically rendered OUTSIDE <form id="settings-form">,
   but form="settings-form" makes it a member of form.elements)
        │
        │  change/input event fires on the FIELD itself,
        │  bubbles up through its own DOM ancestor chain —
        │  NOT through <form>, because the field is not a
        │  descendant of <form> in the DOM tree
        ▼
  document.addEventListener("change"/"input", handler)   <- NEW: was form.addEventListener
        │
        │  handler checks: e.target.form === form ?
        ▼
  updateBar() → countDifferences() (via form.elements, ALREADY correct —
                 form.elements is a live collection that includes
                 form="settings-form" fields regardless of DOM position)
        │
        ▼
  dirtySectionLabels() → form.elements ∩ wrapper.contains(el)  (ALREADY correct —
                 wrapper IS a real DOM ancestor of the field, just not
                 of <form> — contains() only needs a real DOM relationship)
        │
        ▼
  bar.hidden = false;  countEl.textContent = "<Section> changed"


X2/D-03 — one next-wake truth
──────────────────────────────
  last_checkin_ts (device_health) ──┐
  device_config (wake_interval_s,   │
    display_enabled,                ├──► server/wake.py: next_wake_at_iso()
    quiet_hours_enabled/start/end)  │      (extend: also apply the SAME
                                    │      max(effective_interval, quiet_remaining)
                                    │      extension byos_server.py's
                                    │      quiet_hours_sleep_s(display_off_sleep_s(...))
                                    │      already applies when the DEVICE decides
                                    │      how long to sleep — evaluated at
                                    │      last_checkin_ts, not render "now")
                                    │
                                    ▼
                          one (next_wake_iso, hold_reason) result
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                      ▼
      layout.frame_strip_html  health_page.py's       config_page.py's
      (strip headline, grace   staleness_status()/     _with_next_wake()
       window before "warn")   device_staleness_       caption suffixes
                                thresholds() tile
```

### Recommended Project Structure

No new files/folders beyond the harness. New/changed files stay inside the existing layout:
```
companion/
├── static/
│   ├── dirty-state.js        # B1/T1/T8 fix (document-level delegation, suppressGuard reset, Cancel dispatches a refresh)
│   ├── freshness.js          # T13 fix (retry/backoff, paused state, in-flight guard)
│   └── nav-dropdown.js       # T5 fix (transitionend target/property filter)
├── pages/
│   ├── config_page.py        # D-04 (drop on/off checkboxes), D-05 (time fmt), several D-07 items
│   ├── health_page.py        # B2/B3/B4/X8, daily bucket fix call site
│   ├── home_page.py          # B2/B18/X4(defects only)
│   └── airlines_page.py      # B5 (data-attr formatting), X7
├── i18n.py / i18n_fr/        # D-06
├── layout.py                 # D-03 consumer (frame_strip_html), D-05 (local_clock_text is already correct — fix callers)
├── screens.py                # D-04 (registry change)
└── app.py                    # D-04 (handle_post absent-means-unchanged fix), D-06 (flash/title i18n)
server/
├── wake.py                   # D-03 (the one computation)
├── device_config.py          # D-03 (reuse quiet_hours_status()), already has the primitives
└── history_db.py             # D-05 (daily_battery_averages Europe/Paris bucketing)
companion/
└── test_browser_ux.py        # NEW — D-02's Playwright harness (name is discretion; see Code Examples)
```

### Pattern 1: Document-level event delegation for cross-DOM `form=` fields (B1)

**What:** Replace `form.addEventListener("change"/"input", updateBar)` with `document.addEventListener` gated on `e.target.form === form`.
**When to use:** Any time a form-associated control (`form="x"` attribute) lives outside the `<form id="x">` element's own subtree — which this codebase does deliberately, for exactly the reason `config_page.py`'s own docstrings state repeatedly: the rules/calendar/runway/screen/quiet-hours cards each need their own `<form>`, which HTML forbids nesting inside `<form id="settings-form">`.
**Example:**
```javascript
// dirty-state.js — current (broken for form= fields outside <form>):
form.addEventListener("change", updateBar);
form.addEventListener("input", updateBar);

// Fixed — delegate at document level, filter to this form's own
// associated elements (form.elements is authoritative and ALREADY
// includes form="settings-form" fields regardless of DOM position —
// confirmed live: form.elements is a live HTMLFormControlsCollection
// per the WHATWG HTML spec, built from BOTH descendants and any
// element anywhere in the document carrying a matching form= attribute).
document.addEventListener("change", function (e) {
  if (e.target.form === form) { updateBar(); }
});
document.addEventListener("input", function (e) {
  if (e.target.form === form) { updateBar(); }
});
```
No other function in `dirty-state.js` needs to change for B1 itself: `countDifferences()`, `dirtySectionLabels()`, `snapshotValues()` already iterate `form.elements`, which was ALREADY correct — the bug is purely in the event-listener attachment point, confirmed by reading the file's full source (`companion/static/dirty-state.js:84-329`) and `config_page.py`'s own repeated docstring confirmation that every relocated group's controls carry `form="{SETTINGS_FORM_ID}"`.

**T1/T8 ride-along in the same file, same plan (both already named in D-08 and both touch the exact lines this fix touches):**
- T1: `suppressGuard = true` is set on Cancel click (`dirty-state.js:319-328`) and never reset — fix: reset it to `false` at the top of `updateBar()` whenever `countDifferences() > 0` (i.e., re-arm the moment a new edit is detected).
- T8: `cancelBtn` click calls `form.reset()`, which fires no `change` event, so `theme-preview.js`'s live preview and any expanded usage panel keep the discarded value. Fix: after `form.reset()`, either dispatch a synthetic `change` on the reset elements, or (simpler, since this file cannot easily construct synthetic events for `<input form=X>` elements cross-DOM) directly call whatever refresh function `theme-preview.js` exposes — confirm whether that file already exposes a reusable refresh hook or whether one needs adding as part of this same plan.

### Pattern 2: The fallback-Save-button visibility contract (B1's second half)

**What:** `.dirty-ready [data-static-save-fallback] { display: none; }` (`style.css:718-726`) hides the always-rendered bottom Save button once `dirty-state.js` sets `.dirty-ready` on `<html>` — but that class is set as soon as the script confirms `[data-dirty-bar]`/`[data-dirty-count]` exist (`dirty-state.js:164`), NOT once the bar has actually been shown/proven live. CONTEXT.md D-01 requires: "keep the fallback Save button reachable until the bar has actually been shown once."
**Current code (verified):** `document.documentElement.className += " dirty-ready";` runs unconditionally, right after the `if (!bar || !countEl) { return; }` guard — i.e., the instant the two DOM nodes are found, regardless of whether `updateBar()` has ever actually fired or whether the delegation fix even works. This is why B1 was worse than "no dirty bar" — it was "no dirty bar AND no fallback button," because the marker fires on element-presence, not on proven liveness.
**Fix direction (discretion on exact mechanism, but the shape is clear):** Move the `.dirty-ready` marker-setting to occur only after the FIRST successful `updateBar()` call that actually shows the bar (i.e., inside the `bar.hidden = false;` branch, not at script-init time) — OR keep init-time marking but change the CSS contract so the fallback button hides only once a section label has actually rendered. The simplest, most auditable fix: leave the marker where it is (proving script ran and the two elements exist is still a meaningful signal) but do NOT rely on it alone — add a second condition to the CSS selector, e.g. a class set only inside `updateBar()`'s dirty branch, so the fallback disappears only once the bar has genuinely displayed content at least once. Either way, this is a **two-file change** (`dirty-state.js` + `style.css`), and the planner should treat it as inseparable from the delegation fix (same root cause, same plan, same task).

### Pattern 3: The Playwright harness — clone the existing `Harness` class, not a new pattern

**What:** `companion/test_companion_app.py`'s `Harness` class (lines 565-660ish) is the exact subprocess-lifecycle pattern to reuse: a free port picked via `socket.bind(("127.0.0.1", 0))`, an isolated `tempfile.mkdtemp(prefix="skypane-companion-")` state dir, `subprocess.Popen([sys.executable, APP_PATH, "--port", ..., "--state-dir", ...], env=env)`, a readiness-polling loop (`socket.create_connection` retried until `STARTUP_DEADLINE_S`), and a `stop()` that `terminate()`s then `kill()`s on timeout.
**When to use:** For the new browser harness's own server-under-test — do not invent a second subprocess pattern.
**Example:**
```python
# companion/test_browser_ux.py (name is discretion) — sketch of the shape
"""Stdlib entry conventions: this file follows every other harness's
own check(name, fn) + EXPECTED_CHECK_COUNT contract from
companion/test_status_pages.py / server/test_poll_loop.py, so
scripts/run_all_tests.py's `coverage run` + exit-code convention
needs zero special-casing for this file.
"""
import sys

EXPECTED_CHECK_COUNT = 5  # one per D-02 interaction scenario; discretion on granularity

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP companion/test_browser_ux.py — playwright not installed "
              "(dev-only dependency; run `pip install playwright && "
              "python -m playwright install chromium` to enable this harness)")
        return 0  # SKIP, not FAIL — matches CONTEXT.md D-02's explicit contract

    try:
        with sync_playwright() as p:
            p.chromium.launch()
    except Exception as exc:
        # Browser binary itself missing (playwright installed, `playwright
        # install` never run) — same SKIP contract, different cause.
        print("SKIP companion/test_browser_ux.py — Chromium launch failed "
              "(%r); run `python -m playwright install chromium`" % (exc,))
        return 0

    # Reuse companion/test_companion_app.py's Harness class for the
    # subprocess-under-test, seeded exactly like 22-AUDIT.md's own
    # methodology section describes (36 runway events, wake interval
    # 300s, quiet hours 23:00-07:00, etc.) so the harness exercises the
    # SAME defect surface the audit itself observed.
    ...
    results = []
    def check(name, fn): ...  # identical shape to every other harness
    # 1. Display: click a theme chip -> bar visible, names "Theme", persists on save
    # 2. Device: same, proving the two scopes stay in step
    # 3. Mobile nav opens/closes, hidden/aria-expanded stay consistent
    # 4. A Flights detail row expands/collapses
    # 5. Cancel restores the form AND the live theme preview; leave-guard re-arms
    ...
    passed = sum(1 for _, ok in results if ok)
    return 0 if (passed == len(results) and len(results) == EXPECTED_CHECK_COUNT) else 1

if __name__ == "__main__":
    sys.exit(main())
```
**Registration:** Add the new filename to `HARNESSES` in `scripts/run_all_tests.py` (currently a flat 21-item list — despite the module docstring's stale "18 harnesses" comment, which is itself a small pre-existing debt item, not this phase's concern to fix). No other file needs to change for local runs; `scripts/run-all-tests.sh` and `run_all_tests.py`'s `coverage run <harness>` per-process model apply unmodified.
**CI wiring (a REAL required change, not optional):** `.github/workflows/ci.yml`'s "Create virtualenv and install dependencies" step currently only installs `server/requirements.txt` + `server/requirements-dev.txt`. A new step must be added — e.g. immediately after that step — running `server/.venv/bin/pip install playwright` and `server/.venv/bin/python -m playwright install --with-deps chromium`. `playwright` itself should be pinned in `server/requirements-dev.txt` (the file's own header comment already states its purpose: "CI-only tooling... Deliberately separate from requirements.txt so production installs never pull this in" — exactly the CONTEXT.md D-02 contract, this file is the correct, already-established home, no new file needed).

### Pattern 4: Quiet-hours-aware next wake — reproduce the DEVICE's own decision, not a new one

**What:** `stub-server/byos_server.py` (the device-facing reference server) ALREADY computes the correct effective sleep duration for every poll response: `quiet_hours_sleep_s(display_off_sleep_s(base_sleep_s, state_dir), state_dir, now)`, which resolves to `max(base_sleep_s_or_300_if_off, seconds_remaining_until_quiet_hours_end)`. `server/wake.py`'s `next_wake_at_iso()` only reproduces the `display_off` half (`effective_wake_interval_s()` returns `DISPLAY_OFF_SLEEP_S` when off) — it has **zero quiet-hours awareness at all**. This is the exact, sole root cause of X2's "every night the strip reads 'Expected since 23:0x'" defect.
**Correctness insight (load-bearing, verify before implementing differently):** the quiet-hours decision must be evaluated **at `last_checkin_ts`**, not at render "now." The device's own sleep_s was decided by the server at the moment of that last check-in — reproducing `device_config.quiet_hours_status(device_cfg, last_checkin_epoch)` (using the SAME epoch the `last_checkin_ts` string already carries, converted via `datetime.fromisoformat(...).timestamp()`) exactly mirrors what `byos_server.py` actually returned as `sleep_s` on that poll. Using "now" instead would be wrong in the common case (evaluating quiet-hours state at render time, not at decision time), and would silently disagree with what the device is actually doing.
**Example (sketch — exact function shape is discretion):**
```python
# server/wake.py — next_wake_at_iso() needs a genuinely new branch, not
# just a widened effective_wake_interval_s() call, because the existing
# function only returns a SECONDS value (extending it to accept a
# "now" reference and re-derive a remaining-seconds figure conflates
# two different questions). Recommended shape:
def next_wake_at_iso(last_checkin_ts, device_cfg):
    if not last_checkin_ts:
        return None
    try:
        parsed = datetime.fromisoformat(last_checkin_ts)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    base_interval_s = effective_wake_interval_s(device_cfg)  # unchanged; already
                                                                # handles display_off
    if base_interval_s is None:
        return None
    # NEW: reproduce byos_server.py's quiet_hours_sleep_s(display_off_sleep_s(...))
    # extension, evaluated AT last_checkin_ts (the moment the device's own
    # sleep_s was actually decided), not at render time.
    quiet_remaining, _end_hm = device_config.quiet_hours_status(
        device_cfg, parsed.timestamp())
    effective_interval_s = base_interval_s
    if quiet_remaining is not None:
        effective_interval_s = max(base_interval_s, quiet_remaining)
    return (parsed + timedelta(seconds=effective_interval_s)).isoformat()
```
`device_config.quiet_hours_status()` already exists (`server/device_config.py:1028`) and already has a "never raise" contract, so this is a pure composition of two already-tested primitives — no new arithmetic is invented, which materially lowers the risk of a new off-by-one/DST bug (the DST caveat is already accepted and documented at `device_config.py`'s `seconds_until_quiet_hours_end()` — reused, not reopened).
**Return-value shape, a real design decision for the planner:** the current function returns a bare ISO string. D-03 also needs the CALLER to know *why* the device is held (quiet hours vs. simply "not due yet") to choose between "Next update ≈ 17:54" and "Next wake around 07:05 · quiet hours" copy. Either (a) widen the return to a small tuple/namedtuple `(next_wake_iso, hold_reason)`, or (b) keep the function pure and give callers a second, cheap helper (`is_quiet_hours_at(ts, device_cfg)`) to derive the same fact independently. Every existing call site (`home_page.py:421`, `config_page.py:3109`, the new strip consumer) would need updating for option (a); option (b) risks the two computations drifting apart if not extremely careful to reuse the identical epoch. Recommend (a) for the single-source-of-truth guarantee CFG-26 explicitly asks for.
**Grace window:** `layout.frame_strip_html()`'s current warn trigger is `age = age_seconds(next_wake_iso, ctx.get("now")); is_past = age is not None and age >= 0` — i.e., zero grace, warns the instant the computed time passes. D-03 requires `is_past` to instead require `age >= 2 * effective_interval_s` (the grace window), which means the effective interval must also reach this call site — another argument for widening the return shape or exposing a small `(next_wake_iso, effective_interval_s, hold_reason)` result.

**Pinned test that WILL need retargeting (not a suggestion — a certainty):** `companion/test_view_pages.py`'s `_wake_next_wake_at_iso_contract()` (around line 4366) currently asserts, for a screen-ON config with NO quiet-hours keys set, `last_checkin + wake_interval_s` exactly. Since the test's fixture dicts (`{"wake_interval_s": 900, "display_enabled": True}`) carry no `quiet_hours_enabled` key, `quiet_hours_status()` will correctly return `(None, None)` for them (its own contract: "`config.get("quiet_hours_enabled")` is not literally `True`" → `(None, None)`), so this specific test should keep passing unmodified — but the planner must add NEW assertions for a quiet-hours-active config to prove the extension, and should re-read this test in full before editing `next_wake_at_iso()`'s signature, since a shape change (bare string → tuple) breaks every existing caller's assertion (`if got != "2026-08-27T12:10:00+00:00"`) even where the underlying VALUE is unchanged.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Browser automation for the new harness | A raw `subprocess` + screenshot-diffing scheme, or driving a browser via CDP directly | Playwright (`sync_playwright`) | This is exactly what CONTEXT.md D-02 names by product; Playwright's `page.click()`/`expect()` API is a fraction of the code a hand-rolled CDP client would need, and it already has first-class Python bindings with a documented, versioned install story |
| Quiet-hours-aware sleep arithmetic | A new formula "close enough" to what the device does | `device_config.quiet_hours_status()` composed the same way `stub-server/byos_server.py` already composes `quiet_hours_sleep_s(display_off_sleep_s(...))` | The device's actual behavior is defined by that exact composition; anything else can only ever be an approximation that occasionally disagrees with the real device |
| French-string discovery | A blind grep for quoted strings across `companion/` | The existing AST-based scanner in `test_i18n.py` (rules a/b/c + 8 named exclusion reasons) | The scanner already encodes non-trivial decisions (what counts as a CSS-class literal vs. prose, what's a route vs. a phrase) — a naive grep would produce a flood of false positives on the very first run |
| Cross-DOM form field diffing | A MutationObserver or a polling loop watching for field changes | `form.elements` (a live `HTMLFormControlsCollection` the browser itself keeps in sync with `form=` attributes, regardless of DOM position) | This already works correctly today — `dirtySectionLabels()`/`countDifferences()` are not the bug; only the event-listener attachment point is |

**Key insight:** every "Don't Hand-Roll" entry above resolves to *reusing a primitive that already exists in this codebase* (or, for Playwright, one canonical external library) — this phase has essentially zero net-new architecture to invent; the work is almost entirely "wire an existing correct primitive to the place it was wired incorrectly or not at all."

## Common Pitfalls

### Pitfall 1: `display_enabled`/`quiet_hours_enabled` absent-means-False will silently disable the frame on every settings save (X1/D-04) — NOT named explicitly in the audit, but a certain consequence of its fix direction

**What goes wrong:** `config_page.py`'s `handle_post()` (lines ~3906-4055) resolves three checkbox fields with an explicit **absent-in-scope-means-False** rule, documented in its own docstring as deliberate: "an *unchecked* checkbox is omitted from the POST body entirely, so `led_enabled`'s, `quiet_hours_enabled`'s and `display_enabled`'s absence must each resolve to `False`, never to 'leave unchanged.'" This is correct *today*, because today the checkbox is genuinely rendered on the page it's in scope for, and an unchecked box really does mean "the user just unchecked it." Once D-04 removes the `display_enabled`/`quiet_hours_enabled` **checkboxes** from the settings form's markup (their control moves to the Frame strip), the field is **structurally never present** in a real POST body again — but if the code path that resolves it still treats absence-while-in-scope as "user unchecked it," every single settings save (e.g. just changing the theme) will silently turn the display off and disable quiet hours.
**Why it happens:** the checkbox-removal (a markup change, D-07-adjacent) and the write-path semantics (`handle_post()`, a totally separate function ~1800 lines away in the same file) are not obviously coupled unless a reader traces the exact absent→False branch and asks "what happens when this field is NEVER rendered again, in ANY scope?"
**How to avoid — two DIFFERENT fixes are needed for the two fields, verified by direct code reading:**
- **`display_enabled` resolves for free, IF (and only if) `screens.GROUP_DISPLAY` is removed from BOTH `everyday_groups` in `screens.py` AND `scope_groups()`'s own hardcoded `SCOPE_ALL` tuple in `config_page.py` (currently lines 223-227, which still lists `screens.GROUP_DISPLAY` explicitly and independently of the registry).** `handle_post()`'s own gate is already `if screens.GROUP_DISPLAY not in in_scope: display_enabled = None` (leave unchanged) — so once `GROUP_DISPLAY` is structurally absent from every scope's group list, this resolves to `None` automatically, with zero code change inside `handle_post()` itself. But the `SCOPE_ALL` legacy tuple is a SEPARATE, hand-maintained list, not derived from the registry — miss it and a crafted/legacy POST with no scope field still resolves `display_enabled = False` on absence.
- **`quiet_hours_enabled` does NOT resolve for free**, because `GROUP_QUIET_HOURS` stays in scope (its Start/End/preset fields still render and save). Its resolution branch (`elif submitted_qh_enabled is None: quiet_hours_enabled = False`) must be edited directly — to `quiet_hours_enabled = None` (leave unchanged) — since the checkbox this branch used to read is being deliberately removed from the form while the surrounding group stays rendered.
**Warning signs a plan missed this:** any plan that deletes `display_group()`'s/`quiet_hours_group()`'s checkbox markup without ALSO touching `handle_post()`'s resolution branches and `scope_groups()`'s `SCOPE_ALL` tuple. The existing pinned test `companion/test_config_page.py`'s `_scope_groups_follow_the_screen_registry()` (~line 5680) asserts `scope_groups(SCOPE_ALL) == everyday | advanced` exactly — this test WILL FAIL the moment `GROUP_DISPLAY` is removed from the registry lists but not from the `SCOPE_ALL` literal tuple, which is a useful tripwire, but only if the planner runs the harness before considering the plan done, not just eyeballs the diff.

### Pitfall 2: The mobile-nav design-system contract explicitly REJECTS the two mechanisms X9's own fix column proposes

**What goes wrong:** `references/mobile-navigation.md`'s "What to Avoid" section states, as a locked design decision with real-device-testing history behind it: *"Full-screen overlay — still rejected"* and *"Slide-in drawer with a dimming backdrop — still rejected... adds more moving parts (a backdrop element, click-outside-to-close logic) than the header-dropdown needs."* But `22-AUDIT.md`'s own X9 fix column says: *"Bottom tab bar... or an overlay drawer with backdrop and 200ms transition."* An overlay drawer with a backdrop is exactly the mechanism the design-system doc calls "still rejected."
**Why it happens:** the mobile-navigation reference file predates this audit round and was never revisited against X9's specific finding (the in-flow push-down shoves the page ~420px down on a phone, which the earlier real-device testing that produced the "still rejected" verdict was not evaluating — that testing was about full-screen/backdrop *complexity*, not about push-down *page-shift*).
**How to avoid:** whichever mechanism the planner picks for X9 (bottom tabs avoid the contradiction entirely; an overlay drawer requires explicitly reversing the "still rejected" verdict), **D-08 requires updating `sketch-findings-skypane` in the same plan** — specifically `references/mobile-navigation.md`'s "What to Avoid" section must either gain a documented reversal (mirroring this file's own established pattern of marking prior guidance SUPERSEDED with a stated reason, e.g. "SUPERSEDED — X9 (22-AUDIT.md) found the in-flow push-down itself was the worse defect on a real 390px viewport") or the planner should choose bottom tabs specifically to avoid touching this locked verdict at all. Recommend bottom tabs as the lower-risk mechanism for exactly this reason — it doesn't require reversing prior real-device-validated guidance.
**Warning signs:** a plan that ships an overlay drawer without also editing `references/mobile-navigation.md` leaves the design-system skill contradicting the shipped code — the next phase's `sketch-findings-skypane` consumer will read stale "still rejected" guidance and could revert the very fix this phase ships.

### Pitfall 3: `daily_battery_averages()`'s UTC-day bucketing is done in SQL, not Python — the fix is a bigger refactor than it looks

**What goes wrong:** `server/history_db.py`'s `daily_battery_averages()` groups with `SELECT date(ts) AS day ... GROUP BY date(ts)` — SQLite's `date()` function converts an offset-aware ISO timestamp to UTC before taking the calendar day. There is no simple modifier fix: `date(ts, '+1 hours')` (or `'+2 hours'`) would be wrong across the CET/CEST DST boundary, and `date(ts, 'localtime')` would follow the **server's OS timezone** (a Hetzner VPS, almost certainly UTC), not a fixed Europe/Paris — so neither SQL-side fix is actually correct.
**Why it happens:** SQLite has no IANA-timezone-aware date function at all; "Europe/Paris calendar day" is inherently a Python-side (`zoneinfo`) computation, not something `date()` can express correctly across a DST transition.
**How to avoid:** move the day-bucketing from SQL `GROUP BY` to a Python-side aggregation: fetch rows with `battery_mv IS NOT NULL` (optionally still filtered by `ts >= ?` for the `since` cutoff, which stays a safe SQL-side comparison since it's a simple `>=` on the raw string, not a `date()` wrap — preserving the existing `idx_device_health_ts` index-usage comment already in the docstring), then in Python: `datetime.fromisoformat(row["ts"]).astimezone(ZoneInfo("Europe/Paris")).date()` per row, groupby that date, average `battery_mv`, count rows. This is the same DST-acceptance precedent `device_config.py`'s `seconds_until_quiet_hours_end()` already documents (PEP 495 `fold=0`, "bounds the worst case to one extra or one missing wake, twice a year") — reuse that same accepted-caveat framing rather than trying to engineer around it.
**Warning signs:** a plan that "fixes" this with a SQL-only change (a `date(ts, '+1 hours')` literal) will be wrong for roughly half the year (whichever of CET/CEST it wasn't tuned for) — this must be caught in review, not just tested against a single fixed-season seed.

### Pitfall 4: Count-shaped test assertions break mechanically on nearly every markup change — budget for it, don't be surprised by it

**What goes wrong:** every harness file in this codebase (`test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_companion_app.py`, `test_i18n.py`, `test_contrast_check.py`) pins an exact `EXPECTED_CHECK_COUNT` and fails outright if the real count of `check(...)` calls (or, in some files, DOM-node counts like `.theme-status` cards or `data-dirty-section` wrappers) diverges even by one. This is a **feature** of this codebase (catches silent check-loss), not a bug, but it means nearly every D-04/D-07 markup-shape change (removing a checkbox, changing a card count, reordering `data-dirty-section` wrappers) requires a corresponding `EXPECTED_CHECK_COUNT` bump with a `+N (reason)` comment, in the exact style every prior entry already uses.
**Why it happens:** the harness design intentionally makes "a check silently stopped running" impossible to miss.
**How to avoid:** when sequencing waves (Question 7 below), assume every plan touching `config_page.py`'s rendered markup shape, `screens.py`'s registry, or `layout.py`'s `frame_strip_html()`/nav functions will need count-bump edits in `test_config_page.py`/`test_view_pages.py`/`test_status_pages.py` — these are near-certain collision points if two plans touch the same file's markup in the same wave (see Question 7).
**Warning signs:** a plan whose task list has no "update EXPECTED_CHECK_COUNT" step but changes rendered markup shape in a file with a pinned harness is very likely to fail CI on the first run, not silently regress — this is a *loud* failure mode, not a subtle one, which is good, but it should be anticipated in the plan rather than discovered.

### Pitfall 5: The `@supports selector(:has(*))` block count is pinned at exactly 2 — don't add a third without checking

**What goes wrong:** `test_config_page.py` (~line 3737-3774) asserts the whole `style.css` file contains exactly two `@supports selector(:has(*)) { ... }` blocks (the Calendar card's visual-fusion rule, and the theme-chip/runway-card live-selection-state rule from quick task 260904-bbi). Nothing in this phase's own scope obviously needs a third `:has()` feature-query block, but B7/C3's hover-fix, T6's selection-border fix, and T15's focus-visible fix are all touching CSS immediately adjacent to that second block — worth a specific check before submitting a plan that edits this region.
**How to avoid:** if a plan's own fix genuinely needs `:has()`, either extend one of the two existing blocks (preferred, keeps the pinned count meaningful) or explicitly update the pinned count with a documented reason, mirroring every other count-bump in this codebase's own style.

### Pitfall 6: The frame's own design system must never leak into `style.css` — a boundary already stated, worth restating for D-07/D-08 plans

**What goes wrong (hypothetically, not observed):** a plan fixing a Display-page colour/theme-related defect (B6's crop, B7's hover) could be tempted to reference the frame's own `PALETTE_RGB` values or vendored e-ink fonts for "consistency."
**How to avoid:** `style.css`'s own header comment (per `sketch-findings-skypane` `SKILL.md`) states this boundary explicitly — the companion web app's visual identity is deliberately separate from the physical e-ink frame's. Every colour/font value this phase touches must come from `style.css`'s own existing token set (`--color-*`, `--font-*`), never a `server/plane/` constant.

## Code Examples

### Verified: `form.elements` includes `form=`-associated fields regardless of DOM position

This is the load-bearing fact behind B1's fix being *safe* (not a structural rewrite): `HTMLFormElement.elements` is defined by the WHATWG HTML spec as "a collection of all the form-associated elements... that are not image controls, whose form owner is this element" — form ownership is set by either (a) DOM nesting or (b) the `form=` content attribute, explicitly documented as working "even if that element is not a descendant of the form element." `dirty-state.js`'s own `snapshotValues()`, `countDifferences()`, and `dirtySectionLabels()` all already iterate `form.elements` — confirmed correct by direct code reading, not assumed — so B1's entire fix is scoped to the event-listener attachment point only.

### Verified: `quiet_hours_status()`'s existing never-raise contract (reusable primitive for D-03)

```python
# server/device_config.py:1028 — already exists, already tested, reused not reinvented
def quiet_hours_status(config, now_epoch):
    """Returns (seconds_remaining, end_hm), or (None, None) when config
    is not a dict, quiet_hours_enabled is not literally True, or the
    window computation returns None. Never raises for a hostile
    now_epoch (non-numeric, None, NaN, absurdly large)."""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| Three independent "next wake" computations (strip: zero-grace instant warn; tile: 3×/12×-interval thresholds; caption: bare `next_wake_at_iso()` with no quiet-hours awareness) | One `server/wake.py` computation, quiet-hours- and display-off-aware, with a 2×-interval grace window, consumed by all three render sites | This phase (D-03) | Every "next wake" figure on the site will agree with every other, and quiet-hours nights stop producing false warn/error states |
| Settings form as a second writer of `display_enabled`/`quiet_hours_enabled` alongside the Frame strip's `/quick/*` routes | Frame strip is the sole writer; settings form's `handle_post()` resolves both fields to `None` (leave unchanged) unconditionally | This phase (D-04) | Removes the "four controls for two settings" confusion AND removes a latent data-loss bug (see Pitfall 1) |
| String-comparison-only test harnesses (18, soon 19+ files) | + one browser-level harness proving real DOM/event behavior for the interactions no string comparison can see | This phase (D-02) | B1-class defects (event delegation across a DOM boundary) become mechanically detectable for the first time in this codebase's test history |

**Deprecated/outdated:** `references/mobile-navigation.md`'s blanket rejection of overlay-drawer/backdrop mechanisms for mobile nav is now in tension with X9's own fix direction — see Pitfall 2; must be explicitly reconciled (reversed with a stated reason, or avoided by choosing bottom tabs) in this phase, not left stale.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | `next_wake_at_iso()`'s correct quiet-hours evaluation point is `last_checkin_ts`, not render-time "now" | Pattern 4 | If wrong, the strip could show a subtly incorrect next-wake time that still looks plausible — low visible risk, but would silently diverge from the device's actual behavior. Verify by re-deriving `byos_server.py`'s own `quiet_hours_sleep_s(display_off_sleep_s(base_sleep_s, ...), ..., now)` call site and confirming `now` there is indeed "at the moment of this poll response," which is what `last_checkin_ts` represents for the NEXT computation |
| A2 | Widening `next_wake_at_iso()`'s return shape to a tuple (vs. adding a second helper function) is the lower-risk path to the single-source-of-truth guarantee CFG-26 asks for | Pattern 4 | If the planner instead keeps two separate functions and one drifts (e.g., a future edit updates the interval logic in one but not the other), the exact contradiction-window bug X2 describes could reappear in a new form. This is Claude's Discretion per CONTEXT.md, not a locked decision — flagging the tradeoff, not asserting the answer |
| A3 | Bottom tabs are the lower-risk X9 mechanism specifically because they avoid contradicting `references/mobile-navigation.md`'s existing "still rejected" verdict on overlay/backdrop drawers | Pitfall 2 | If the developer actually prefers the overlay-drawer aesthetic despite the prior real-device-testing verdict, this is not a blocker — CONTEXT.md explicitly leaves the X9 mechanism to Claude's Discretion — but the design-system doc update becomes mandatory rather than avoidable |

**If this table is empty:** N/A — three assumptions above need no user confirmation to proceed (both are reasoning about internal code mechanics already verified live), but are flagged because their opposite conclusions would materially change a plan's task list.

## Open Questions

1. **Does `theme-preview.js` already expose a reusable "refresh the live preview from current form state" function T8's fix can call after `form.reset()`?**
   - What we know: `theme-preview.js` is card-scoped (per SKILL.md's Phase 21 entry, "every lookup now scoped inside `.frame-colours`") and reacts to `change` events on the theme radios today.
   - What's unclear: whether calling its change-handling logic directly (vs. dispatching a synthetic event) is exposed as a named function, or whether it's an anonymous IIFE-internal closure with no external hook — this file was not read in full during this research pass (out of budget; `dirty-state.js`, `frame_strip_html`, `wake.py`, `screens.py`, `config_page.py`'s `handle_post`/`render`, `history_db.py`'s `daily_battery_averages`, `test_i18n.py`'s scanner, and the harness/CI files were prioritized per the research questions).
   - Recommendation: the plan implementing T8 should read `theme-preview.js` in full as its first task-step before committing to "dispatch a synthetic event" vs. "call an exposed refresh function."

2. **Exact granularity of the new Playwright harness's `EXPECTED_CHECK_COUNT`.**
   - What we know: CONTEXT.md D-02 names 5 scenario groups (Display bar, Device bar, mobile nav, Flights detail row, Cancel-restores-preview-and-re-arms-guard).
   - What's unclear: whether each scenario group is one `check()` (5 total) or decomposed into multiple finer-grained assertions per scenario (e.g., "bar visible" + "names the right section" + "save persists" as three separate checks for scenario 1 alone) — this is explicitly Claude's Discretion per CONTEXT.md ("Test-harness file naming and how the browser-unavailable skip is reported" implies broader harness-shape discretion too).
   - Recommendation: mirror this codebase's own dominant style (fine-grained, one `check()` per assertable fact, with a descriptive name) rather than 5 monolithic checks — every existing harness in this codebase uses the fine-grained style, and coarse checks would be the outlier.

3. **Whether `run_all_tests.py`'s stale "18 harnesses" docstring comment and `EXPECTED_SLOWEST` tuple need updating when the new harness is added.**
   - What we know: the module docstring says "Runs all 18 harnesses" but `HARNESSES` already has 21 entries (the docstring is already stale, predating this phase).
   - What's unclear: whether fixing this pre-existing staleness is in scope for this phase (it is adjacent to D-02's own file) or should be left alone as out-of-scope drift.
   - Recommendation: update the count in the same edit that adds the new harness's filename to the list (a one-line, zero-risk fix, consistent with "leave the file in a state at least as correct as you found it"), but do not treat fixing the stale count as a requirement if a plan is tight on scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python 3.12 | Entire companion service, test suite | Yes (existing, unrelated to this phase) | 3.12 | — |
| `playwright` (pip) | D-02's new harness | Not installed by default anywhere in this repo today | 1.62.0 (verified current on PyPI) | Harness SKIPs (exit 0, clear message) when import fails — per CONTEXT.md's explicit contract, this is not a blocking dependency for the rest of the suite |
| Chromium browser binary (`python -m playwright install chromium`) | D-02's new harness, at actual test-run time | Not installed by default; must be a separate, visible step (never silently bundled) | Whatever `playwright==1.62.0` bundles/targets | Harness SKIPs (exit 0, clear message) when browser launch fails — same contract as the import-failure case |
| GitHub Actions network access to download Chromium (~100-200MB) | CI's new install step | Available (GH-hosted runners have outbound internet) | — | None needed; this is a one-time-per-run cache-miss cost, could be mitigated later with `actions/cache` on the Playwright browser cache dir, but that's an optimization, not a correctness requirement for this phase |

**Missing dependencies with no fallback:** none — every new dependency has an explicit, CONTEXT.md-mandated skip path.

**Missing dependencies with fallback:** `playwright` (Python package) and the Chromium binary — both degrade to a SKIP, not a suite failure, when absent on a contributor's local machine; CI is expected to always have both (a required, not optional, CI step per D-02).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Stdlib-only hand-rolled harnesses (`check(name, fn)` + `EXPECTED_CHECK_COUNT` pattern), no pytest, no unittest. Orchestrated by `scripts/run_all_tests.py` under `coverage run` per file, in parallel (`ThreadPoolExecutor`), with a repo-wide `fail_under = 83` coverage gate from `pyproject.toml` |
| Config file | `pyproject.toml` (`[tool.coverage.run]`/`[tool.coverage.report]`); `scripts/run_all_tests.py`'s own `HARNESSES` list is the harness-discovery "config" |
| Quick run command | `server/.venv/bin/python3 companion/test_config_page.py` (or any single harness file directly — each is a self-contained `main()` with its own exit code) |
| Full suite command | `./scripts/run-all-tests.sh` (wraps `scripts/run_all_tests.py`; enforces the coverage threshold across the combined run) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| CFG-25 | Save bar appears on a `form=`-attached field's change; fallback stays reachable until proven live | browser | `python3 companion/test_browser_ux.py` (new name TBD) | ❌ Wave 0 — this phase creates it |
| CFG-25 | Existing string-comparison assertions for the dirty bar's copy/markup still hold | unit | `python3 companion/test_config_page.py` | ✅ |
| CFG-26 | `next_wake_at_iso()` quiet-hours extension, evaluated at `last_checkin_ts` | unit | `python3 companion/test_view_pages.py` (extend `_wake_next_wake_at_iso_contract`) | ✅ (extend) |
| CFG-26 | Strip/tile agreement, grace window before warn | unit | `python3 companion/test_status_pages.py` / `companion/test_view_pages.py` (new assertions against `frame_strip_html`) | ✅ (extend) |
| CFG-27 | `display_enabled`/`quiet_hours_enabled` resolve to "leave unchanged" on a settings-form save with no on/off field present | unit | `python3 companion/test_config_page.py` (new/extended `handle_post()` assertions) | ✅ (extend) |
| CFG-27 | `scope_groups(SCOPE_ALL)` union invariant still holds after registry change | unit | `python3 companion/test_config_page.py::_scope_groups_follow_the_screen_registry` (existing pinned test) | ✅ |
| CFG-27 | Strip switch does not trigger the leave-page dialog with unsaved form edits | browser | new Playwright scenario, or a targeted unit check on `dirty-state.js`'s `suppressGuard`/`beforeunload` logic if feasible without a real browser | ❌ Wave 0 (browser) / ✅ possible partial unit coverage |
| CFG-28 | Battery readout/chart/tooltips render Europe/Paris local time, not UTC | unit | `python3 companion/test_status_pages.py` (extend `_battery_reading_parts`/`_daily_reading_parts` assertions) | ✅ (extend) |
| CFG-28 | Daily battery buckets group by Europe/Paris calendar day across a DST boundary | unit | `python3 server/test_config_history.py` or a new/extended `history_db` test — needs a fixture with timestamps straddling a CEST/CET transition | ✅ (extend; DST fixture likely needs adding) |
| CFG-29 | Flash banners, titles, plurals, attribute literals translated; scanner sees `app.py` | unit | `python3 companion/test_i18n.py` (widen `_SCAN_RELATIVE_PATHS` and the Check 2 exception lists) | ✅ (extend) |
| CFG-30/31 | Pixel-measurement acceptance targets from `22-AUDIT.md`'s own table | manual/UAT + some automatable DOM-geometry assertions | Playwright can assert computed-style/geometry facts (e.g., "these three runway cards share a row at 390px") for a subset; the rest is human/UAT per the audit's own "Not verified" section | Partial — new Playwright checks can cover SOME (B9 column count, B13 cell height parity via `getBoundingClientRect`), most require eyeball verification against the pixel table |

### Sampling Rate

- **Per task commit:** the single most relevant harness for the file(s) touched (e.g., `companion/test_config_page.py` after a `config_page.py` edit) — fast, stdlib-only, typically sub-second to a few seconds per file.
- **Per wave merge:** `./scripts/run-all-tests.sh` (full suite, coverage-gated).
- **Phase gate:** full suite green, coverage ≥ 83%, plus the Playwright harness passing (not skipped) at least once in CI before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `companion/test_browser_ux.py` (name TBD) — the entire D-02 harness; does not exist yet.
- [ ] `server/requirements-dev.txt` — add a pinned `playwright==1.62.0` line.
- [ ] `.github/workflows/ci.yml` — add the `pip install playwright` + `playwright install chromium` step.
- [ ] A DST-straddling fixture for `daily_battery_averages()`'s Europe/Paris bucketing test (CFG-28) — no existing test currently exercises a CET/CEST boundary; one is needed to prove the Python-side rewrite is actually correct, not just "looks right against a seed that never crosses DST."
- [ ] New quiet-hours-active fixture(s) for `next_wake_at_iso()`'s extended contract (CFG-26) — the existing pinned test only covers screen-on/screen-off, never quiet-hours-active, cases.

*Machine-provable vs. eyeball-only, explicitly, per the output contract's requirement:*
- **Machine-provable (unit):** B1's underlying mechanism (form.elements/dirtySectionLabels already correct — provable without a browser by directly unit-testing the Python-rendered markup shape), X2/D-03's arithmetic, X1/D-04's write-path semantics, D-05's formatter call sites and DST bucketing, D-06's scanner coverage, the `SCOPE_ALL` union invariant.
- **Machine-provable (browser, new):** B1's actual browser behavior (the thing no unit test could ever prove — a real `change` event firing and a real DOM update happening), T5's mobile-nav `hidden`/`aria-expanded` consistency, T1/T8's Cancel-then-re-edit and Cancel-restores-preview behaviors, Flights row expand/collapse.
- **Eyeball-only (human/UAT):** essentially the entire "Pixel measurements" table in `22-AUDIT.md` (exact px/rem values, colour-on-hover legibility, "does this look right on a real phone") — Playwright CAN assert some of these mechanically (computed styles, `getBoundingClientRect()` geometry) but the audit's own methodology used a visual/screenshot review process this phase's harness is not asked to replicate wholesale; real-device verification (iPhone/Android rendering) is explicitly deferred to phase-level UAT per CONTEXT.md's Deferred Ideas.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | Yes (X3, login card) | `auth.py`'s existing `LoginThrottle` (lockout after `LOGIN_FAILURE_LIMIT`, 300s window) — the show-password toggle and live countdown are purely presentational over already-existing server state; no new auth logic is introduced |
| V3 Session Management | No change this phase | — |
| V4 Access Control | No change this phase | — |
| V5 Input Validation | Yes (already strong; no regression risk identified) | `escape_html()` at every interpolation point (existing, universal convention) continues to apply to every new/changed string this phase touches, including the reformatted `data-first-seen`/`data-last-seen` values (B5) and any new i18n-routed flash/title strings (D-06) |
| V6 Cryptography | No change this phase | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-------------------------|
| Reflected/stored XSS via an unescaped interpolation in a newly-touched render path (B5's `data-*` attribute reformat, D-06's newly-i18n-routed strings) | Tampering / Information Disclosure | This codebase's own universal discipline: every interpolated value crosses `escape_html()` at its interpolation site — confirmed already in force at every location this research touched (`config_page.py`, `layout.py`, `airlines_page.py`); no new sink is introduced by any fix in this phase, since every fix either reformats an existing already-escaped value (B5, D-05) or routes an existing string through `i18n.t()` before its existing escape call (D-06) |
| A crafted/legacy settings POST exploiting the `SCOPE_ALL` fallback to flip `display_enabled` off as a denial-of-service against the physical device | Denial of Service | This is exactly Pitfall 1 above — fixed by making `display_enabled`/`quiet_hours_enabled` resolve to "leave unchanged" whenever their owning group is out of scope (which, post-fix, is now true even for the legacy `SCOPE_ALL` submission path once its tuple is corrected) |
| A hostile Chromium page context in the new Playwright harness accidentally granted network access to production | Elevation of Privilege / Tampering | The harness must ONLY ever navigate to `Harness.base_url()` (the local subprocess-under-test's own `127.0.0.1:<port>`), matching every other harness's existing pattern — no external URL should ever be reachable or navigated to by the new test |

Given `security_asvs_level: 1` and `security_block_on: "high"` from `.planning/config.json`, and that this phase introduces no new authentication, session, or cryptographic surface, no HIGH-severity ASVS finding is anticipated from this phase's own scope — the one genuinely security-adjacent risk this research surfaced (Pitfall 1's silent display-disable) is a correctness/availability bug, not a classic injection/auth vulnerability, but is flagged here because its blast radius (bricking the physical device's display on every settings save) is severe enough to warrant the same rigor.

## Sources

### Primary (HIGH confidence — read live against the current tree, 2026-09-12)
- `companion/static/dirty-state.js` (full file) — B1/T1/T8 mechanism
- `companion/pages/config_page.py` (targeted: `scope_groups()`, `handle_post()`, `quiet_hours_group()`, `display_group()`, `_display_groups_html()`, `render()`'s next-wake block, DISPLAY_SECTION_CAPTION region)
- `companion/screens.py` (full file)
- `companion/layout.py` (targeted: `frame_strip_html()`, `parse_iso`/`age_seconds`/`local_clock_text`/`concise_timestamp_html`/`relative_age_text`)
- `server/wake.py` (full file), `server/device_config.py` (targeted: `quiet_hours_status`, `seconds_until_quiet_hours_end`, `DISPLAY_OFF_SLEEP_S`, `WAKE_INTERVAL_MIN_S/MAX_S`), `server/poll_loop.py` (targeted: hold_kind branch), `stub-server/byos_server.py` (targeted: `quiet_hours_sleep_s`/`display_off_sleep_s` and their composition site)
- `server/history_db.py` (targeted: `daily_battery_averages()`)
- `companion/pages/health_page.py` (targeted: `staleness_status`, `compute_health_state`, `_battery_reading_parts`, `_daily_reading_parts`)
- `companion/pages/airlines_page.py` (targeted: the `data-first-seen`/`data-last-seen` write sites)
- `companion/i18n.py` (full file), `companion/test_i18n.py` (targeted: the AST-scanner mechanics, `_SCAN_RELATIVE_PATHS`, exception lists)
- `companion/test_companion_app.py` (targeted: the `Harness` class)
- `scripts/run-all-tests.sh`, `scripts/run_all_tests.py` (full files), `.github/workflows/ci.yml` (full file)
- `companion/static/freshness.js` (targeted: `doRefresh`/`tick`/`startLoop`/`stopLoop`)
- `companion/static/battery-trend.js`, `companion/static/panel-lookup.js` (targeted: data-attribute read paths)
- `.claude/skills/sketch-findings-skypane/SKILL.md` (full file) and `references/control-density.md`, `references/settings-page-patterns.md`, `references/accessibility-contrast.md`, `references/mobile-navigation.md` (full files)
- `companion/test_config_page.py` (targeted: `EXPECTED_CHECK_COUNT` history, `_scope_groups_follow_the_screen_registry`, the `@supports selector(:has(*))` count pin)
- `.planning/phases/22-.../22-CONTEXT.md`, `.planning/phases/22-.../22-AUDIT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` (tail), `.planning/config.json`

### Secondary (MEDIUM confidence)
- `pip index versions playwright` + `pip show playwright` (live registry query, 2026-09-12) — version currency
- `slopcheck install playwright --ecosystem pypi` (live tool run, 2026-09-12) — [OK] verdict

### Tertiary (LOW confidence — none load-bearing)
- None. Every claim in this document that drives a concrete recommendation was verified against the live repository or an official package registry/docs page in this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — the only "stack" decision is one dev-only package (Playwright), verified via registry + official docs + slopcheck in this session.
- Architecture (B1, X1/D-04, X2/D-03): HIGH — every claim traced to specific file:line reads of the actual current source, not inferred from the audit's prose alone; the two non-obvious pitfalls (absent-means-False, SCOPE_ALL union) were discovered by direct code tracing, not stated in the audit.
- Pitfalls (D-05 DST bucketing, X9 design-system contradiction): HIGH — both confirmed by direct reading of `history_db.py`'s SQL and `mobile-navigation.md`'s own "What to Avoid" text respectively.
- Pixel-level D-07 items (B2-B18 individually): MEDIUM — file:line locations are taken from `22-AUDIT.md` itself (already validated by the developer) rather than independently re-verified line-by-line in this research pass, given the research budget was directed at the five deep-dive questions the task specified; the CSS/markup mechanism for each is well within this codebase's established idioms (documented throughout SKILL.md's references) and poses no unusual risk.

**Research date:** 2026-09-12
**Valid until:** ~30 days (stable, slow-moving internal codebase; the one external dependency, Playwright, is on a fast release cadence but pinning a specific version in `server/requirements-dev.txt` neutralizes drift risk)
