---
phase: quick-260903-peo
plan: 260903-peo
subsystem: ui
tags: [companion, health-page, history-page, settings, css, javascript, accessibility]

requires:
  - phase: 06.6.4.1
    provides: "The page_header()/page_shell() shared component contract, the .refresh-pill/.data-table/.copy-btn component set, and the flash-banner PRG pattern this task builds on top of"
provides:
  - "404 page opens with the shared serif page_header(), and gates the Health nav dot on authentication"
  - "Health's pipeline tile gains a real second content line from META_LAST_DETECTION"
  - "Health's header gains a persistent server-rendered liveness note beside the existing hidden refresh pill"
  - "History's desktop copy buttons reveal on row hover/focus-within instead of always showing"
  - "A consumed ?flash= query param is stripped client-side after its banner renders"
affects: [companion-page-review, ui-polish]

tech-stack:
  added: []
  patterns:
    - "Client-side query-param cleanup via a dedicated no-build-step ES5-safe static script (flash-cleanup.js), guarded on two conditions (rendered banner + matching query string), mirroring the existing nav-dropdown.js/panel-lookup.js convention"
    - "opacity + pointer-events (never visibility/display) as the reveal mechanism for a hover/focus-triggered control, to keep it in the tab order and accessibility tree"

key-files:
  created:
    - companion/static/flash-cleanup.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/test_companion_app.py
    - companion/test_status_pages.py
    - companion/test_view_pages.py
    - companion/test_config_page.py

key-decisions:
  - "UIR-16's health-severity computation is gated on self._is_authenticated() (a pure, non-redirecting predicate) rather than threaded as a parameter through all eleven _not_found_page() call sites — keeps the two pre-auth static-asset paths from ever seeing health state."
  - "UIR-14's second line reuses .text-label/.section-caption (the file's existing 70% muted-colour tier) instead of .battery-readout__detail — the latter's class name literally contains the substring 'battery-readout', which would false-positive two pre-existing 'no battery readout element' regression guards since this tile renders unconditionally."
  - "UIR-14's absent-detection case renders the honest concise_timestamp_html() fallback ('no reading yet'), never an empty element — matching _device_section()'s own unconditional-render precedent."
  - "UIR-18's persistent note and the existing hidden pill are wrapped in one block-level <p class=\"page-header__freshness\"> so .page-header's children stay all block-level, preserving 260902-ep7's anonymous-block-box fix; the pill's own position:absolute rule (scoped to .page-header, not the wrapper) is unaffected."
  - "UIR-17 uses opacity:0 + pointer-events:none at rest (never visibility:hidden/display:none) so the copy buttons stay focusable and in the tab order — verified live via the keyboard hard gate."
  - "UIR-19's flash-cleanup.js guards on BOTH a rendered .banner--flash element AND location.search mentioning 'flash', so a future second query parameter is never silently discarded by an over-broad rewrite."

requirements-completed: [QUICK-260903-peo]

metrics:
  duration: 42min
  files_modified: 8
  files_created: 1

status: complete
---

# Quick Task 260903-peo: Five Minor UI Fixes from 06.6.4.1-UI-REVIEW Summary

**Closed UIR-16 (404 heading + Health nav-dot leak guard), UIR-14 (Health's near-empty pipeline tile), UIR-18 (Health's invisible auto-refresh cue), UIR-17 (History's desktop row clutter), and UIR-19 (Settings' replayable `?flash=saved`) — each verified in a real headless browser against seeded production-shaped state, with all sixteen harnesses green.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-09-03T17:32:11Z
- **Completed:** 2026-09-03T18:14:28Z (code + automated verification; Task 6 human checkpoint is a separate, deferred step — see below)
- **Tasks:** 5 of 6 (Tasks 1-5 complete; Task 6 is a `checkpoint:human-verify` gate left for the orchestrator to run with the developer)
- **Files modified:** 8 modified, 1 created

## Accomplishments

- UIR-16: `_not_found_page()` now opens with `layout.page_header()`'s shared 30px serif `.page-title` heading (was the 20px `.text-heading` section-heading role) and threads `health_alert` only on the `self._is_authenticated()` branch, closing the leak of Health severity state to the two pre-auth static-asset paths (`_serve_stylesheet()`, `_serve_script_file()`). Verified live: an authenticated 404 under a seeded error state shows `dot--error`; the identical unauthenticated request shows none.
- UIR-14: `_read_health_inputs()` grew from six reads to seven (`last_detection` joins `pipeline_ts` in the same atomic snapshot), and the pipeline tile now renders a real second line ("Last aircraft detected: …") sourced from `history_db.META_LAST_DETECTION`. `.dashboard-grid`'s `align-items: stretch` is byte-identical to before.
- UIR-18: Health's header now carries a persistent, server-rendered liveness note ("Live — refreshed HH:MM UTC (…)") beside the existing hidden `data-refresh-pill` span, both inside one block-level `<p class="page-header__freshness">` wrapper — preserving 260902-ep7's anonymous-block-box fix. `freshness.js` has zero diff.
- UIR-17: History's desktop `[data-copy-value]` copy buttons are `opacity: 0` / `pointer-events: none` at rest and reveal on `tr:hover`/`tr:focus-within`, inside the existing `min-width: 960px` block. The always-visible View-panel/eye trigger (same `.copy-btn` class, no `data-copy-value`) is unaffected. Mobile cards are untouched by construction.
- UIR-19: a new `companion/static/flash-cleanup.js` strips a consumed `?flash=` query param via `history.replaceState()` once its banner has rendered, guarded on both a present `.banner--flash` element and a matching `location.search`. The server-side PRG redirect (`POST /settings` → `?flash=saved`) is unchanged; wired through all seven mechanical touch points mirroring `panel-lookup.js`.
- All sixteen harnesses green across two full-suite runs (no flake); `ruff check .` clean.

## Task Commits

1. **Task 1: UIR-16 — 404 page uses page_header() and gates the Health nav dot on auth** - `002b178` (feat)
2. **Task 2: UIR-14 + UIR-18 — pipeline tile second line + persistent freshness note** - `41bd92f` (feat)
3. **Task 3: UIR-17 — History desktop copy buttons reveal on hover/focus-within** - `ce15860` (feat)
4. **Task 4: UIR-19 — flash-cleanup.js strips a consumed ?flash= param** - `9af8da4` (feat)
5. **Task 5: Full suite + real-browser before/after verification** - no source commit (verification only; results below)

**Plan metadata:** `8331557` (docs: plan five minor UI fixes) — pre-existing, committed before this execution began.

## Files Created/Modified

- `companion/app.py` — `_not_found_page()` rewrite (UIR-16); `NOT_FOUND_TITLE`/`NOT_FOUND_PURPOSE_TEXT` constants; `FLASH_CLEANUP_SCRIPT_ROUTE`, `_FLASH_CLEANUP_JS_PATH`, `_serve_flash_cleanup_script()`, and the pre-auth dispatch branch (UIR-19)
- `companion/layout.py` — `FLASH_CLEANUP_SCRIPT_SRC` constant and the seventh deferred `<script>` tag in `page_shell()` (UIR-19)
- `companion/pages/health_page.py` — `_read_health_inputs()` six→seven reads, `_pipeline_section()`'s new second line and `LAST_DETECTION_LABEL`/`PERSISTENT_FRESHNESS_PREFIX_TEXT` constants, `render()`'s new `.page-header__freshness` wrapper (UIR-14, UIR-18)
- `companion/static/style.css` — `.stat-tile__meta` (layout-only, UIR-14), `.page-header__freshness` (spacing-only, UIR-18), the desktop `[data-copy-value]` reveal rule pair inside the existing `min-width: 960px` block (UIR-17)
- `companion/static/flash-cleanup.js` — new file (UIR-19)
- `companion/test_companion_app.py` — 2 new UIR-16 checks (127 total, was 125); 3 new UIR-19 checks + in-place 6→7 script-tag-count retarget (130 total, was 127)
- `companion/test_status_pages.py` — 2 new UIR-14 checks + in-place six→seven `_read_health_inputs()` key-set retarget; 1 new UIR-18 structural check; the pre-existing `.dashboard-grid` align-items:stretch guard already fully covered UIR-14's "unedited" requirement (133 total, was 130)
- `companion/test_view_pages.py` — 2 new UIR-17 checks (54 total, was 52)
- `companion/test_config_page.py` — 1 new UIR-19 check (65 total, was 64)

## EXPECTED_CHECK_COUNT Before/After (re-derived from real runs, never arithmetic)

| File | Before | After |
|------|--------|-------|
| companion/test_companion_app.py | 125 | 130 |
| companion/test_status_pages.py | 130 | 133 |
| companion/test_view_pages.py | 52 | 54 |
| companion/test_config_page.py | 64 | 65 |

## Full Suite Verification

`scripts/run-all-tests.sh` run twice, both clean, no flake:

- Run 1: all 16 harnesses PASS, `Result: PASS`
- Run 2: all 16 harnesses PASS, `Result: PASS`
- Coverage: 92% (threshold met)
- `ruff check .`: All checks passed

`git diff --stat` (against the pre-plan HEAD, `8331557`) confirms edits confined to `companion/app.py`, `companion/layout.py`, `companion/pages/health_page.py`, `companion/static/style.css`, the new `companion/static/flash-cleanup.js`, and the four `companion/test_*.py` files — `companion/static/freshness.js`, `companion/static/copy-button.js`, `companion/static/panel-lookup.js`, `companion/static/dirty-state.js`, `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/pages/config_page.py`, `companion/auth.py` and everything under `server/` carry zero diff.

## Real-Browser Verification

**Method:** the cached Playwright Chromium at `~/Library/Caches/ms-playwright/chromium-1228` (`Google Chrome for Testing.app`), launched with legacy `--headless` (never `--headless=new`) plus `--remote-debugging-port=9333`, driven over raw CDP using Node's built-in `WebSocket`/`fetch` globals (no npm dependency). Authentication for each server was a real `POST /login` via `fetch`, with the server-issued `sp_session` cookie handed to the browser via CDP `Network.setCookie` — never a UI-driven form login.

**Environment:** two copies of `/tmp/skypane-prod-state` (never the original) in the session scratchpad, one served by the pre-edit tree (`git archive 83315578ded6ba2eb9886d97cf071b0f8e6218d5`, the plan's own recorded `BASE_SHA`) on port 8801, one served by this branch's current tree on port 8802. Both copies were seeded identically: a `META_LAST_DETECTION` meta row (~6 minutes old), a `META_LAST_PIPELINE_RUN` meta row, one `device_health` reading, two `runway_events` rows (callsign+hex on both, so both desktop copy buttons render), and one gallery PNG timestamped just before the newest row (so the View-panel/eye trigger renders too).

**Findings table** (BEFORE = pre-edit tree / port 8801, AFTER = this branch / port 8802):

| Finding | Measurement | BEFORE | AFTER |
|---|---|---|---|
| UIR-16 | Authenticated 404 `<h1>` class / font-size | `text-heading` / 20px | `page-title` / 30px (matches a real page's `<h1>`, confirmed against `/health` in the same run) |
| UIR-16 | Authenticated 404 under seeded error state: Health dot present | absent (pre-existing behaviour never threaded severity) | present (`dot--error`) |
| UIR-16 | **Leak guard** — identical unauthenticated 404 under the same seeded error state: dot present | absent | **absent** (confirmed after explicitly clearing the browser's cookie jar between scenarios — an earlier draft of this check had a false failure caused by CDP's browser-profile-scoped cookies leaking the prior authenticated session into the "unauthenticated" request; documented so a future re-run doesn't repeat the same test-methodology mistake) |
| UIR-14 | Pipeline tile line count / content | 2 lines: caption + "18:07 UTC (Nm ago)" | 3 lines: caption + pipeline timestamp + "Last aircraft detected: 17:56 UTC (Nm ago)" |
| UIR-14 | Pipeline tile `getBoundingClientRect().height` | 263.59px | 263.59px (unchanged — `.dashboard-grid`'s `align-items: stretch` means the row height is set by the tallest tile, Corroboration at 4 lines; the fix fills existing empty space rather than growing the tile) |
| UIR-14 | Corroboration tile height (must be unchanged) | 263.59px | 263.59px (unchanged) |
| UIR-18 | Persistent note visible on load, no interaction/wait | not present | `opacity: 1`, non-zero rect, text "Live — refreshed HH:MM UTC (0s ago)" |
| UIR-18 | Hidden `data-refresh-pill` span still present/hidden | present, `hidden` | present, `hidden` (byte-identical markup, confirmed via `outerHTML`) |
| UIR-18 | `<h1>`-bottom to `.page-header__purpose`-top gap, vs. Airlines (no freshness block) | Health 4px = Airlines 4px | Health 28.59px vs. Airlines 4px — **fully accounted for**: `.page-header__freshness`'s own rect height (20.59px, exactly one line at 14px/1.4 line-height) + its own 4px margin-bottom + the unchanged 4px `<h1>` margin-bottom = 28.59px. Confirmed the wrapper renders exactly one line box (`childElementCount: 2`, the note text plus the `position: absolute` pill, which contributes zero height) — this is the deliberate, accounted-for cost of one real visible line, not a reopening of 260902-ep7's phantom-anonymous-box bug (which was about *invisible* content consuming space) |
| UIR-17 | Desktop copy-button opacity at rest (pointer parked away) | `1` (always visible) | `0` (hidden, `pointer-events: none`) |
| UIR-17 | Desktop copy-button opacity on row hover | `1` | `1` (`pointer-events: auto`) |
| UIR-17 | View-panel/eye button opacity, both states | `1` / `1` | `1` / `1` (unaffected in both trees) |
| UIR-17 | **Hard gate** — Tab-focused copy button opacity, pointer never touched, transition settled | `1` (no reveal mechanism existed) | `1`, `pointer-events: auto`, `tr:focus-within` matches (measured after a 300ms settle past the rule's own 150ms transition — an earlier unsettled measurement caught the animation mid-flight at `opacity: 0.03` and would have been a false failure; documented so a future re-run measures post-transition, not mid-transition) |
| UIR-17 | Mobile (375px) card copy-button count/opacity | 3 buttons, all `opacity: 1` | 3 buttons, all `opacity: 1` (unchanged — desktop-only rule) |
| UIR-19 | URL after a real save, immediately | `.../settings?flash=saved` | `.../settings` (query stripped by the time the check ran — the deferred script executes essentially synchronously after DOM parse) |
| UIR-19 | Flash banner present after save | present | present (server-rendered from the redirect target, unaffected) |
| UIR-19 | URL + banner after a manual reload of the post-save URL | banner **reappears** (replayable) | banner **absent** (query already stripped, so the reload never carries `?flash=`) |
| UIR-19 | Server-side PRG redirect, read off the network layer | `303` to `?flash=saved` | `303` to `?flash=saved` (byte-identical, confirmed via a direct `fetch` with `redirect: 'manual'`) |

Screenshots captured at 1440px and 375px, light and dark themes (16 total: Health + History, before + after, 2 widths × 2 themes) — stored in the session scratchpad at `verify/{before,after}-{health,history}-{light,dark}-{1440,375}.png`, not committed to the repository.

**Note on computed-style assertions alone:** this project's own recorded lesson is that computed-style checks once missed a real mobile nav bug — the measurements above are all real-browser, real-render assertions (not harness-level string checks), but a developer's own visual/tactile pass on a real device is still the final sign-off, per Task 6 below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `.battery-readout__detail` reuse would have false-positived two pre-existing regression guards**
- **Found during:** Task 2, while implementing UIR-14's second line
- **Issue:** The plan's own must_haves named `.battery-readout__detail` as a candidate muted-text tier to reuse. Its class name literally contains the substring `battery-readout`, which collides with `BATTERY_READOUT_ID = "battery-readout"` — two pre-existing checks (`_single_reading_still_no_chart_no_readout_no_script`, `_empty_battery_history_stays_script_free`) assert that substring is absent from the page whenever there is no battery reading. Since the pipeline tile's new second line renders unconditionally, reusing that class would fire both guards as false positives on a fresh install with no battery data.
- **Fix:** Reused `.text-label`/`.section-caption` instead (the same file-wide 70% muted-colour strength, already composed this way by the battery heading's own trailing span and the Unresolved-prefixes read-only note per quick task 260902-gjj). Documented the rejection of `.battery-readout__detail` in both the CSS comment and the Python comment so a future editor doesn't reintroduce it.
- **Files modified:** `companion/pages/health_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`
- **Commit:** `41bd92f`

**2. [Rule 1 - Bug] My own new fallback-detection test check counted a page-wide substring instead of scoping to the pipeline tile**
- **Found during:** Task 2, while writing the "absent detection renders the honest fallback" check
- **Issue:** The first draft counted `"no reading yet"` occurrences page-wide and asserted exactly 1 — but the fixture (deliberately unseeded `device_health`) also leaves the Device tile's own `concise_timestamp_html()` call rendering the identical fallback text, so the real count was 2, not 1.
- **Fix:** Scoped the assertion to the pipeline tile's own second-line `<p>` element specifically, rather than a page-wide count.
- **Files modified:** `companion/test_status_pages.py`
- **Commit:** `41bd92f`

### Real-Browser Verification Methodology Corrections (not code bugs, documented for future re-runs)

**3. CDP cookies are browser-profile-scoped, not page-scoped** — the first UIR-16 unauthenticated-404 measurement showed a false `hasDot: true` because the prior authenticated scenario's `Network.setCookie` call persisted across a newly-created CDP target in the same Chrome instance. Fixed by calling `Network.clearBrowserCookies` before the unauthenticated scenario. See the findings table above.

**4. CSS transitions must be allowed to settle before measuring computed style** — the first UIR-17 keyboard hard-gate measurement caught the `opacity` transition mid-flight (`0.03`) because it measured immediately after `Input.dispatchKeyEvent` moved focus. Fixed by waiting 300ms (twice the rule's own 150ms transition) before the final measurement. See the findings table above.

Neither correction indicates a defect in the shipped code — both are documented here so a future automated re-run of this same technique doesn't reproduce the same false failures.

## Known Stubs

None — no hardcoded empty values, placeholder text, or unwired data sources were introduced by this task.

## Threat Flags

None — all five findings' new surface (the `[data-copy-value]` CSS selector, the `.page-header__freshness` wrapper, the pipeline tile's second line, the 404 page's auth-gated severity read, and `flash-cleanup.js`'s client-side `history.replaceState()` call) is already covered by this plan's own `<threat_model>` (T-peo-01 through T-peo-06), verified unchanged during implementation.

## Task 6: Human Checkpoint (Deferred)

Task 6 (`type="checkpoint:human-verify"`, `gate="blocking"`) is intentionally left open for the orchestrator to run with the developer — it cannot be completed by this executor, which has no way to interact with a real human or a real device. All automated verification (harnesses + real-browser measurements above) is complete and green; only the developer's own real-device visual/tactile sign-off remains.

**To reproduce the verification environment for a real-device pass**, from the repository root:

```bash
# Seed a scratch copy (never the original snapshot):
cp -R /tmp/skypane-prod-state /tmp/skypane-peo-verify
server/.venv/bin/python3 -c "
import datetime
from server import history_db
state_dir = '/tmp/skypane-peo-verify'
now = datetime.datetime.now(datetime.timezone.utc)
with history_db.open_db(state_dir) as conn:
    history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, (now - datetime.timedelta(seconds=20)).isoformat(timespec='seconds'))
    history_db.set_meta(conn, history_db.META_LAST_DETECTION, (now - datetime.timedelta(minutes=6)).isoformat(timespec='seconds'))
    history_db.record_runway_event(conn, ts=(now - datetime.timedelta(minutes=3)).isoformat(timespec='seconds'), hex='3944F0', callsign='AFR123')
"

# Start the companion service:
SKYPANE_COMPANION_PASSWORD=verify123 server/.venv/bin/python3 companion/app.py --port 8900 --state-dir /tmp/skypane-peo-verify

# Optional: a cloudflared tunnel for phone testing (as quick task 260903-etm did):
cloudflared tunnel --url http://127.0.0.1:8900
```

Then, per the plan's own checkpoint script:
1. Visit `/nope` (or any bad URL). The heading should read as the same large serif title every other page uses; if Health is warn/error the nav dot should be there. Sign out and try again — no dot should appear.
2. On Health: the "ADS-B pipeline last ran" tile should no longer read as mostly empty, and a small "live / refreshed at …" cue should sit near the page title on load, without waiting.
3. On History (desktop width): the two copy buttons per row should be invisible until you hover the row. Then, without touching the mouse, Tab through a row — each copy button must become visible when it receives focus. On a phone, the card disclosure should still show all three buttons.
4. On Settings: save something. You should see "Saved —" and a clean URL with no `?flash=saved`. Reload — the banner must not come back.

## Self-Check: PASSED

All 9 modified/created source files and this SUMMARY.md confirmed present on disk; all 5 referenced commit hashes (`002b178`, `41bd92f`, `ce15860`, `9af8da4`, `8331557`) confirmed present in `git log --oneline --all`. No missing items.
