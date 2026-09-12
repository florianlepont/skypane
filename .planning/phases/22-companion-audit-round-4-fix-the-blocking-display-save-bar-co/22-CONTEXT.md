# Phase 22: Companion audit round 4 — Context

**Gathered:** 2026-09-12
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/phases/22-companion-audit-round-4-fix-the-blocking-display-save-bar-co/22-AUDIT.md`)

<domain>
## Phase Boundary

**In scope — the fix half of 22-AUDIT.md, enumerated, plus a browser test harness:**

- **B1** (P0), **B2–B18** — display bugs
- **X1–X9** — UX defects
- **C1–C6** — design-contract drift against `sketch-findings-skypane`
- **T1–T16** — verified CSS/JS defects and debt
- A minimal Playwright harness wired into `scripts/run-all-tests.sh`

**Explicitly out of scope — Phase 23:**

- Every dynamism suggestion **D1–D24** (SSE stream, fetch switches, motion budget, View Transitions, Home hero redesign, day timeline, runway map, quiet-hours dial, wake-interval slider, theme carousel, battery ring, punctuality grid, prefetch/gzip, offline shell, manifest, share, drag-and-drop upload, command palette, guided first run).
- The developer chose this split at planning (2026-09-12): Phase 22 must be a shippable correction pass where every item is individually verifiable; the dynamism work is a redesign and belongs in its own phase.

**Boundary rule for the planner:** a fix that *happens* to add motion or a fetch call is out of scope unless the audit item itself requires it. Three named exceptions where the audit's own fix direction is behavioural, not cosmetic:
- **X2** requires a shared next-wake computation (server-side, no client polling needed for the fix itself — the live refresh is D1, Phase 23).
- **X3** may add a show-password toggle and a live lockout countdown: both are named in the audit's fix column and are local to the login card.
- **T13** requires retry/backoff and a visible paused/reconnecting state in the existing `freshness.js` loop — repairing a loop that already exists, not adding a new one.

**Audience:** unchanged since Phase 18 — a second household member with basic computer skills must be able to use the everyday half without an explanation.
</domain>

<decisions>
## Implementation Decisions

Every entry below is LOCKED: it comes from `22-AUDIT.md`, which the developer validated in full on 2026-09-12 ("Je valide l'ensemble des points remontés"). The audit's own "Fix / next step" column is the decision; the planner may choose mechanism, not outcome.

### D-01 — The blocker is the first plan, and it ships with its own guard (B1, CFG-25)

`dirty-state.js` must detect changes to fields that are attached to `#settings-form` by the `form=` attribute while living outside the element. Delegate at document level and gate on `e.target.form === form`; keep `dirtySectionLabels()` working off `form.elements` intersected with each `[data-dirty-section]` wrapper's `contains()`. The fallback Save button must stay reachable until the bar has actually been shown once — hiding it on the mere presence of `.dirty-ready` is what turned a JS defect into "no way to save at all".

This plan does not land without the harness in D-02. The defect existed because every current harness compares HTML strings and none parses the DOM.

### D-02 — A minimal Playwright harness, dev-dependency only (CFG-25)

A new browser-level harness runs in `scripts/run-all-tests.sh` and covers the interactions string comparison cannot see. Minimum set, all against a seeded temp state directory using the existing `Harness` subprocess pattern from `companion/test_companion_app.py`:

1. Display: clicking a theme chip / a runway card / the Enable-display checkbox / a quiet-hours time makes the save bar visible, names the right section, and the save actually persists.
2. Device: the same, proving the two scopes stay in step.
3. The mobile nav opens and closes, leaving `hidden` and `aria-expanded` consistent (T5).
4. A Flights detail row expands and collapses (`aria-expanded`, `aria-controls`).
5. Cancel restores the form AND the live theme preview (T8), and the leave-guard is armed again on the next edit (T1).

Playwright is a **development dependency only** — it must not enter `server/requirements.txt` nor any deployed unit. The harness skips with a clear message (not a failure) when the browser is unavailable, the same way the suite already tolerates the documented macOS Pillow/FreeType digest mismatch. CI (`.github/workflows/ci.yml`) runs it; the `paths-ignore` docs filter stays as it is.

### D-03 — One next-wake truth, quiet-hours aware, with a grace window (X2, CFG-26)

`server/wake.py`'s next-wake computation becomes the single source consumed by the Frame strip headline, the Home/Health status tiles and every settings caption. It must account for:
- an active quiet-hours window (the device is held until the window ends — `poll_loop.py:1019-1027`), and
- a screen that is switched off (`DISPLAY_OFF_SLEEP_S`).

No warning state may be shown before a grace window of 2 × the effective interval. While the frame is legitimately held, the copy is neutral and says why ("Next wake around 07:05 · quiet hours"), never "Expected since". The strip and the tile must not be able to disagree: if the tile says "Checking in normally", the strip may not show a warning dot.

Deliberately NOT in this phase: making the strip refresh itself in the browser (D1, Phase 23). A page load must simply be correct.

### D-04 — One control per setting, one delay sentence (X1, CFG-27)

The Frame strip owns Screen on/off and Quiet hours on/off. `companion/screens.py` stops listing `GROUP_DISPLAY` and `GROUP_QUIET_HOURS`'s on/off controls as everyday form groups; the settings form keeps only the quiet-hours **schedule** (enable-by-schedule semantics, start, end, presets). One computed sentence states when a change reaches the frame, derived from D-03's estimate, replacing all three of today's wordings ("Applies the next time the frame wakes up", "Takes effect within about 5 minutes", "Applies on the next scheduled poll, which may now be hours away") and the flash variants.

The "within about 5 minutes" claim must be verified against `server/wake.py:114-115` and the firmware before being reused anywhere; the audit's reading is that it holds only when the display is *already* off. If it cannot be substantiated, it is replaced by the computed estimate, not restated.

Pressing a strip switch with unsaved form edits must no longer trigger the browser's "leave page?" dialog for a change the strip itself is about to apply (`dirty-state.js:297-317`).

The nav state reminder stays only if it links somewhere useful, and its `aria-label` must stop saying "go to Home" when already on Home.

### D-05 — Paris local time everywhere (B4, B5, CFG-28)

`layout.local_clock_text()` is the only formatter for visible times. This covers `_battery_reading_parts()` (which currently does `strftime("%H:%M")` on an unconverted datetime plus a literal " UTC"), every sparkline point's tooltip/`aria-label`/`data-when`, `battery-trend.js`'s hover swap and its raw-ISO fallback, `_axis_clock_label()`, and the airline resolve dialog's `data-first-seen`/`data-last-seen` (the no-JS path already formats them — the two paths must agree). Daily battery buckets group by **Europe/Paris** calendar day, not UTC. Every `title` tooltip carries a local full timestamp; raw ISO survives only behind a copy control.

`layout.concise_timestamp_html()`'s docstring, which still promises `"<HH:MM> UTC (<relative>)"`, is corrected — that stale doc is what the battery code copied.

### D-06 — French completeness (B16, CFG-29)

Flash banners route through `i18n.t` (today `_resolve_flash_text()` returns English and every FR catalogue lacks the keys). Page `<title>`s are translated, including the login shell and the 404. Plurals gain singular forms ("1 manual resolution", "%d upcoming flight(s)", "over the last %d days, %d events"). `aria-label="Primary navigation"`, the "Light"/"Dark" theme segments and the CSS `content: "Current"` (which must become a server-rendered `data-*` string — T10) are translated. The battery caption stops naming the constant (`BATTERY_TREND_LIMIT`) when the real count differs.

`companion/test_i18n.py` is widened to cover what it currently cannot see: `app.py`, attribute literals (`title`, `alt`, `aria-label`, `placeholder`), and JS-side fallbacks. Strings originating in `server/` are noted, not necessarily moved.

### D-07 — The visible defects, as measured (B2–B18, X3–X9, CFG-30)

Each item below is locked to the audit's own fix direction; the measurements in `22-AUDIT.md`'s "Pixel measurements" table are the acceptance target.

- **B2/B3** — Health: a real neutral "never ran / no detection yet" state (not warn); a verdict-free `pipeline_detail_html` for Home mirroring `device_detail_html`; the empty "How well we name flights" section is not rendered at all when empty; resolution stats count every row with unknown `route_source` bucketed as "other"; the empty copy names the 30-day window.
- **B6** — the theme-preview crop stops slicing the render's caption mid-glyph.
- **B7/C3** — an explicit `.theme-form .theme-option:hover` rule so a selected-and-hovered segment never takes the primary fill (accent text on accent ground today).
- **B8** — "Send a test" lives inside the Notifications card via `form=`, not orphaned between two cards.
- **B9** — three runway cards per row below 960 px, or a vertical list; no 2 + 1 orphan.
- **B10** — the nav state reminder never wraps mid-phrase.
- **B11** — the filter count and Clear stay on one line at 390 px on all three filtered pages.
- **B12** — the unresolved-prefix table fits 1280 px in French.
- **B13** — the Frame strip's cells share one height and one internal grid; the next-update line is a cell of the same style or the strip's subtitle, not a floating headline.
- **B14** — the normalised 24 h value is shown beside the native time fields.
- **B15** — "Connect calendar" is content-width, left-aligned.
- **B17** — Device fields share one left edge; the number input is sized for its content.
- **B18** — Home's recent-flight time is one line; airline names come from `display_airline_name()` so Home and Flights agree.
- **X3** — the login card: full-width field, primary below (or one same-height, same-radius group), a real error state (`aria-invalid`, `aria-describedby`, error styling), show-password, live lockout countdown, translated title.
- **X4** — Home's ordering and naming defects only (the hero redesign is D4, Phase 23).
- **X5** — Flights: day separators, whole-row disclosure rather than 50 grey buttons, a labelled picture control, a direct "name this airline" link, phone cards carrying airline and thumbnail.
- **X6** — one chip density across usages; the rules add-form left-aligned on one line; a legend for the swatches.
- **X7** — Airlines: normal-case "Change pictures", a visible editing affordance on each card, two cards per row on a phone.
- **X8** — one tile anatomy on Health; "Only one saw it" is neutral, not the same green as "Both agree"; the empty state is body-sized, not a 22 px serif heading inside a 12 px-captioned tile.
- **X9** — the mobile nav stops shoving the page down by a full screen. The mechanism is LOCKED to a **bottom tab bar** (Home, Display, Flights, Airlines, then More for the Advanced group) — see D-10. Keep a working nav without script.

### D-08 — Design contract and code defects (C1–C6, T1–T16, CFG-31)

`sketch-findings-skypane` is the authority and must be updated in step with whatever this phase changes:
- **C1** — label-voice legends leave the serif selector; a compact `empty_state()` variant for tiles.
- **C2** — the Frame strip stops stacking two filled primary buttons on an accent surface; accent returns to the page's single main action.
- **C4** — a stated composition rule: controls sharing a row share height and radius.
- **C5** — one "time value" role (sans, tabular numerals, muted relative age); monospace reserved for identifiers.
- **C6** — the next-update headline stops competing with section headings at the same size.
- **T1** — the leave-guard re-arms after Cancel.
- **T2** — Disconnect stops rendering as the primary accent CTA (specificity, not a new colour).
- **T3** — `<details>` regain an open/closed indicator.
- **T4** — sticky table headers either stick or stop claiming to.
- **T5** — the mobile-nav close path is deterministic.
- **T6** — selection stops shifting layout by 2 px.
- **T7** — the fixed save bar stops covering page content; it gets a `z-index` on desktop.
- **T8** — Cancel restores the live preview.
- **T9** — tile hover stops erasing the status rail; the strip stops lifting when a button inside it is hovered.
- **T11/T12/T15** — the contradicting `max-height`, the segmented-control margin, the invisible focus state on a selected card and `summary`'s missing `:focus-visible`.
- **T13** — `freshness.js` retries with backoff and shows a paused/reconnecting state instead of stopping silently; an in-flight guard.
- **T14** — one shared disable-on-submit helper for every form.
- **T16** — the debt items (gzip and hashed filenames, a muted-text token, dead selectors, a shared `ui.js`) are **optional** for this phase: take them only where a plan already touches that code. Do not open a stylesheet-wide refactor.

### D-09 — Regression floor

Every existing harness keeps passing and the counts move only where a plan's own change forces it. The no-JS floor holds: every page must still be usable and every setting still saveable with scripts blocked. No new runtime dependency in `server/requirements.txt`; no vendored library; the CSP stays `script-src 'self'` with no `unsafe-inline` and no nonce.

### D-10 — X9's mechanism is a bottom tab bar, not an overlay drawer (developer decision, 2026-09-12)

The audit's own fix column offered "bottom tab bar, or an overlay drawer with backdrop". That second option was a mistake in the audit: `sketch-findings-skypane`'s `references/mobile-navigation.md` carries a locked **rejected** verdict on the absolute-positioned overlay, established by real-device testing during 06.6.1-06 — the overlay could only cover content, never push it, which is why the shipped dropdown is in-flow via `flex-basis: 100%`.

The mechanism is therefore a bottom tab bar: the four everyday tabs (Home, Display, Flights, Airlines) plus a "More" entry for the Advanced group. It must not reintroduce a full-screen push, must keep a usable nav with scripts blocked, must respect the safe-area inset, and must not cover the pinned save bar on Display and Device (the two interact — plan them together or state the stacking order).

Do not implement an overlay drawer. If a plan finds bottom tabs unworkable for a reason this context does not anticipate, it must say so and stop rather than fall back to the rejected pattern.

### D-11 — Sequencing is by dependency wave, never by calendar (developer decision, 2026-09-12)

The audit originally sequenced this work as "Week 1", "Week 2", "Weeks 3–4" with S/M/L effort labels defined in days. Those durations were fabricated: nobody measured them, and this project's own history (Phases 20 and 21 both closed on 2026-09-12) shows the unit of work here is a plan, not a working week. The ledger's `## Sequencing` section now states waves ordered by dependency, and the D-table's third column is `Scope` (reach: one file / a few files / a redesign), explicitly not a duration.

**Planner: do not put durations, dates, week numbers or day estimates into any PLAN.md.** Order tasks by what must exist before what. The ledger's five waves are the intended grouping; deviate only with a stated reason.

### D-12 — Three findings the research added, all LOCKED (22-RESEARCH.md)

These were not in the audit. Each would have shipped a regression if a plan followed the audit alone.

1. **Removing the on/off checkboxes from the settings form silently disables both settings.** `handle_post()` resolves an absent checkbox to `False`. Once D-04 takes `display_enabled` and `quiet_hours_enabled` out of the form, every settings save would post neither field and switch the screen and quiet hours off. Both must be changed to resolve **absent → leave unchanged**, and a harness check must pin that: saving an unrelated field must not alter either flag.
2. **`scope_groups()`'s `SCOPE_ALL` tuple is hand-maintained, separate from the screen registry, and still lists `GROUP_DISPLAY`.** It must be edited in the same plan as D-04, or the already-pinned `_scope_groups_follow_the_screen_registry` check fails immediately.
3. **The Paris-day battery bucketing cannot be done in SQL.** `history_db.daily_battery_averages()` groups with SQLite's `date(ts)`, which is UTC-only, and no fixed-offset SQL modifier is DST-correct for Europe/Paris. The bucketing moves to Python with `ZoneInfo("Europe/Paris")`. A fixture straddling a DST boundary is part of the fix, not optional.

Two further research findings the planner should treat as the preferred mechanism rather than a locked one: X2's estimate should **reproduce** the device's own sleep decision (`stub-server/byos_server.py` already composes `quiet_hours_sleep_s(display_off_sleep_s(...))`, and `device_config.quiet_hours_status()` is already tested) rather than re-derive it, evaluated at the last check-in rather than at render time; and the new browser harness belongs in `server/requirements-dev.txt`, which is the repo's already-established home for dev-only pins, with a CI install step.

### Claude's Discretion

- Plan count, wave grouping and file-level sequencing.
- The exact mechanism for each fix where the audit names an outcome but not a means (e.g. whether B9 uses fixed columns or a vertical list). X9 is NOT discretionary — see D-10.
- Which `T16` debt items ride along with a plan that already touches the code.
- Whether the shared next-wake code (D-03) lands in `server/wake.py` or a new module, as long as there is exactly one implementation.
- Test-harness file naming and how the browser-unavailable skip is reported.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The audit being acted on
- `.planning/phases/22-companion-audit-round-4-fix-the-blocking-display-save-bar-co/22-AUDIT.md` — the full ledger: every finding with severity, file:line and its locked fix direction, the pixel-measurement table, and the sequencing. This is the phase's specification.
- https://claude.ai/code/artifact/af979b96-c02d-41bc-ad04-9623ff0d143a — the same findings with the evidence screenshots, developer-validated 2026-09-12.

### Design system (authority, must be updated in step)
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the live design contract: tokens, serif boundary, label voice, accent reservation, card treatment, control density, touch-target register, navigation.
- `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md` — the type ladder and its three-step history.
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — button geometry, wash strengths, the selected-card contract, the touch-target register.
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` — the WCAG floors and the executable colour-separation contract.
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` — the one-caption-per-section rule and the save-bar's four-iteration history.
- `.claude/skills/sketch-findings-skypane/references/data-density.md` — the Flights table's measured width budget.
- `companion/static/style.css` — its own header comment carries the accent-reservation list and the frame/companion boundary.

### Prior companion phases whose decisions this phase must not silently reverse
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` — the first audit ledger and the A-IDs this phase's regressions refer to (A-18 in particular).
- `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-PRD.md` and `21-UI-SPEC.md` — D-01..D-20, including the Frame strip's own contract (X1/D-04 revises it deliberately).
- `.planning/phases/20-companion-suggestions-from-the-audit-french-localisation-liv/` — the bilingual mechanism and its completeness harness.

### Code the fixes land in
- `companion/static/dirty-state.js`, `companion/static/theme-preview.js`, `companion/static/freshness.js`, `companion/static/nav-dropdown.js` — B1, T1, T5, T8, T13.
- `companion/pages/config_page.py`, `companion/pages/health_page.py`, `companion/pages/home_page.py`, `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, `companion/layout.py`, `companion/app.py`, `companion/screens.py` — the page-level fixes.
- `server/wake.py`, `server/poll_loop.py`, `server/device_config.py` — D-03's next-wake truth.
- `companion/i18n.py`, `companion/i18n_fr/`, `companion/test_i18n.py` — D-06.
- `scripts/run-all-tests.sh`, `.github/workflows/ci.yml`, `companion/test_companion_app.py` (its `Harness` subprocess pattern) — D-02.
</canonical_refs>

<specifics>
## Specific Ideas

- The audit was produced against a seeded state directory (36 runway events over 17 h, 40 days of battery readings, 3 gallery renders, 2 unresolved prefixes, 1 manual resolution, 2 colour rules, wake interval 300 s, quiet hours 23:00–07:00). Reproducing that seed is the cheapest way to see any of these defects; the seeding script pattern is worth keeping with the new harness.
- B1's root cause is structural and deliberate: `config_page.py` renders the theme/runway/screen/quiet-hours controls as siblings of `<form id="settings-form">` with `form="settings-form"`, because the rules and calendar forms cannot be nested inside it. The fix must preserve that structure, not undo it.
- X2's night-time behaviour was inferred from code (`server/wake.py:162-197` has no quiet-hours handling while `poll_loop.py:1019-1027` holds the device), not observed live. Confirming it against a real overnight run, or a unit test that pins it, is part of the fix.
- The "within about 5 minutes" screen-off claim (`config_page.py:444-448`) is the one copy statement the audit could not substantiate. Treat it as suspect until checked against `server/wake.py` and the firmware.
- Two regressions to name explicitly so they are not re-introduced: B11 is a regression of Phase 18's A-18, and B10/B13 are the Phase 21 Frame strip and nav reminder as shipped.
</specifics>

<deferred>
## Deferred Ideas

- **All of D1–D24** — the dynamism half of the audit. Moved to Phase 23 by the developer's own scope decision at planning (2026-09-12), so Phase 22 stays a shippable correction pass with individually verifiable items. Phase 23's roadmap entry already carries the full list.
- **T16's stylesheet-wide debt** — gzip and hashed filenames, a `--color-text-muted` token, the 13 duplicated label-voice blocks, the dead selectors, a shared `ui.js` helper module. Optional here, only where a plan already touches that code; the full cleanup is its own future task.
- **Real-device verification** — iPhone/Android rendering (system fonts, address bar, safe-area) is listed in the audit's "Not verified" section and belongs to phase-level UAT, not to a plan.
</deferred>

---

*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Context gathered: 2026-09-12 via PRD Express Path (22-AUDIT.md), scope narrowed by developer decision at planning*
