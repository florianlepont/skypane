# Phase 29: Companion review feedback round 3 — Research

**Researched:** 2026-09-21
**Domain:** Internal codebase investigation (Python-rendered HTML/CSS/JS companion app) — no new external libraries, no new services. Pure "what does the existing code already do, and what is the cheapest conforming change" research.
**Confidence:** HIGH for everything traced directly to source (file:line cited below); MEDIUM/LOW flagged inline where a mechanism (CFG-80's 24h-detection, CFG-83's reveal choice) is genuinely undecided in this codebase and requires a planner judgment call.

## Summary

This phase touches six requirements (CFG-79 through CFG-84) across three files that overlap heavily: `companion/pages/config_page.py` (CFG-79, CFG-80), `companion/pages/airlines_page.py` (CFG-79, CFG-81, CFG-82), `companion/pages/history_page.py` (CFG-79, CFG-83), `companion/pages/health_page.py` (CFG-79, CFG-84), and `companion/static/style.css` (CFG-80, CFG-82). None of these requirements need a new package, a new script file, or a new route. CFG-81 is the largest in blast radius — `edit_mode` is threaded through `app.py`, `pages/__init__.py`, and roughly 30 call sites across `test_status_pages.py`/`test_view_pages.py` — removing it is a real, multi-file deletion, not a one-line fix. CFG-83 is the only requirement that is genuinely new UI (confirmed: `grep -ri paginat` across `companion/` returns nothing), and its central risk is that `companion/static/freshness.js`'s auto-refresh loop replaces the ENTIRE Flights list DOM every ~45s by fetching `window.location.href` — which is good news for a query-param-driven reveal (the URL, and therefore the reveal state, survives the swap for free) and bad news for a `<details>`-based reveal (a native `open` attribute on a swapped node is reset to the server's default, closed, on the very next background refresh).

**Primary recommendation:** For CFG-83, use a server-side `?limit=` query-param re-render (a plain `<a href="?limit=N">` link), not a `<details>` disclosure — it is the only one of the two candidates that survives `freshness.js`'s existing swap mechanism without any script change. For CFG-81, budget the removal as its own task: `edit_mode` has ~30 test call sites that assert its presence and must be deleted or rewritten, not just the two Python functions that gate on it.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Editorial floor (CFG-79) | Frontend Server (SSR, Python string constants) | — | All copy is server-rendered Python string constants; no client logic involved except the harness that measures rendered length in a browser |
| Quiet hours layout/24h detection (CFG-80) | Frontend Server (markup/CSS) | Browser (the 24h-detection script, if built) | The dial/labels/CSS are server-rendered; deciding whether to hide the normalised-time twin requires a client-side check of the browser's own time-rendering behaviour, which no server-side signal can determine |
| Illustration dialog actions (CFG-81) | Frontend Server (SSR) | Browser (`panel-lookup.js`, unchanged) | Removing `edit_mode` is a pure server-side markup change; the existing script already keys off attribute presence, not off `edit_mode` |
| Compagnies gallery-first + tab label (CFG-82) | Frontend Server (SSR + CSS) | — | Section reordering and CSS margin fix, no client logic |
| Flights pagination (CFG-83) | Frontend Server (SSR) | Browser (`freshness.js` interaction) | Whichever mechanism is chosen, the reveal state must be expressed in a form `freshness.js`'s existing `fetch(window.location.href)` call preserves across a background refresh |
| État title (CFG-84) | Frontend Server (SSR) | — | String constant + markup restructuring only |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

**Editorial floor (CFG-79)**
- One sentence under a card title, at most ~12 words, no mechanism clause, no reason clause.
- "Applies at the next wake" is said in exactly one place per page (the Frame strip / save bar), never repeated under each card.
- Anything longer moves into the existing "How it works" `<details>` disclosure, or is deleted outright.
- Scope is site-wide **except** Display's Aspect section — Phase 30 owns that card's copy, since it is being rebuilt from scratch there.
- Enforced by a harness check measuring RENDERED caption length on every authenticated route, in both languages, mutation-proven against a deliberately long caption.
- The runway card's stale schematic-map clause is already cut in Lot A (quick task 260921-n2n) — this requirement's own check must not re-fail on that already-fixed text; it asserts the FLOOR going forward, not a diff against Lot A.

**Quiet hours as one object (CFG-80)**
- Start and End render on one line as one visual unit with the dial, not as two separate stacked field groups.
- The normalised HH:MM twin beside each native `<input type="time">` (`_normalised_time_html()`, B14/22-10) is hidden at load when the native field already renders unambiguous 24h — kept alive as the scripts-blocked / forced-12h-browser fallback. B14's own ground for existing at all is unchanged; only its default visibility changes.
- Presets become a segmented control with short labels ("Nuit", "Journée") — the hours are already spoken by the dial's own caption, so the button labels don't need to repeat them.
- The uncommitted CSS fix sitting in the MAIN CHECKOUT (not this worktree) from the 2026-09-17 audit session — `_normalised_time_html()`'s sibling gaining a `field=` parameter so it can hide conditionally — is now MOOT: Phase 28 already fixed the dial's minute-vs-HHMM bug a different way (CFG-73, 28-03), and this requirement's own "hide the twin" mechanism is a fresh, independent implementation. Do NOT attempt to merge or replay that uncommitted diff; it predates Phase 28 and would conflict with CFG-73's shipped fix.

**The illustration dialog owns its own actions (CFG-81)**
- Replace picture (and Delete, for a manually resolved entry) render in the dialog on EVERY open, unconditionally — the page-wide `edit_mode` query param and the "Modifier les images" / "Change pictures" toggle are removed entirely.
- "Send a picture" for an airline with no artwork yet is unchanged — it was never gated by `edit_mode`.
- The resolve-context block's two bugs (empty-instead-of-hidden, caption-as-callsign) are already fixed in Lot A — this requirement is the SCOPE change (always-rendered actions), not a repeat of those two bug fixes.
- Removing `edit_mode` also removes the reason the resolve-context block was ever reachable from a page-wide toggle — no separate change needed there beyond what Lot A already shipped.

**Compagnies gallery-first (CFG-82)**
- Filter + known-airline gallery render directly under the page title.
- Unidentified prefixes and any remaining editing affordance move into a clearly announced secondary section below the gallery.
- The 2026-09-17 audit's own fix for the truncated "Compagnies" tab label — `.tab-bar__pill`'s horizontal margin from `var(--space-sm)` to `calc(var(--space-xs) / 2)` — sits uncommitted in the MAIN CHECKOUT's `style.css`, NOT in this worktree. **Do not attempt to pull or merge that diff.** Re-derive the same fix fresh in this worktree's `companion/static/style.css` and verify it against Phase 28's current tab-bar CSS, which has moved since that diff was written.

**Vols paginated (CFG-83)**
- Show 10–15 flights, then a real "Afficher plus" / "Show more" action that works with scripts blocked — either a server-side `?limit=` query param re-render, or a native `<details>`-style progressive reveal. Planner's choice; record the reasoning in the plan.
- The filter bar stays immediately visible above the first card at all times — pagination must not push it below the fold or hide it while collapsed.
- The summary card's grid stays stable on a 390px phone — the 2026-09-17 audit's P1 finding was the timestamp and callsign fighting for one line at this width; the fix must not regress once pagination is added.
- No existing pagination pattern exists anywhere in this codebase (verified: `grep -ri paginat` across `companion/` returns nothing) — this is genuinely new UI, closer to research territory than the other five requirements.

**État's title shortened (CFG-84)**
- The battery-trend `<h2>` reads "Batterie · 3 mois" / "Battery · 3 months"; "moyenne quotidienne" / "daily average" moves to the card's existing caption, not the heading.

### Claude's Discretion
- CFG-83's exact reveal mechanism (query-param re-render vs. `<details>`) — planner picks based on what's cheapest against the existing `history_page.py` structure and the no-JS floor this app holds everywhere else.
- Whether CFG-82's secondary section for unidentified prefixes reuses an existing disclosure pattern (`<details>`) or a plain lower page-section — planner's call, consistent with the rest of the page.
- Ordering of the six plans / waves — planner's call based on real file-ownership overlap (several of these touch `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, and `companion/static/style.css` and cannot safely run in parallel against the same file).

### Deferred Ideas (OUT OF SCOPE)
- The 2026-09-17 audit's 44px tap-target item (presets, Effacer, Envoyer un test, manual refresh) — explicitly not selected by the developer for this phase. Stays in that audit's own backlog.
- The Chrome "save password?" report from the developer's tour — investigated, no confirmed mechanism found, developer retracted it. No action needed.
- The maintainability debt of `config_page.py` and `style.css` (Mistral's one real contribution) — explicitly out of scope, "hors de cet arriéré d'interface, à traiter par opportunité". Not this phase.

</user_constraints>

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-79 | Editorial floor site-wide except Aspect | Concrete offender list below (12 constants over 12 words, file:line); existing `VIEW_TRANSITION_ROUTES` tuple in `test_browser_ux.py:994` is the ready-made "every authenticated route" iteration convention to reuse |
| CFG-80 | Quiet hours as one visual object | Exact current markup order and CSS class names identified in `config_page.py`'s `quiet_hours_group()`; no existing 24h-detection pattern found anywhere in this codebase — flagged as a genuine gap |
| CFG-81 | Illustration dialog owns its actions | Every `edit_mode` read site enumerated and classified below; ~30 test call sites found across `test_status_pages.py`/`test_view_pages.py` that assert its presence |
| CFG-82 | Compagnies gallery-first + tab label | Current `render()` section order extracted; `.tab-bar__pill` CSS confirmed unchanged since Phase 22 (2026-09-13), so the audit's described fix still applies verbatim |
| CFG-83 | Vols paginated | `freshness.js`'s swap mechanism traced to `fetch(window.location.href, ...)` — the decisive fact for choosing a reveal mechanism |
| CFG-84 | État title shortened | Exact current `<h2>` composition and both branches of its caption text found in `health_page.py` |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

The project's root `CLAUDE.md` documents the SkyPane hardware/firmware/server stack (ESP-IDF, AeroDataBox, PRIM, Hetzner). None of it is load-bearing for this phase: this phase touches only `companion/` (the Python stdlib-only web app) and its own design-system skill (`sketch-findings-skypane`). The one binding project-wide rule that applies here is the **GSD Workflow Enforcement** clause — file-changing work must go through a GSD command (`/gsd-execute-phase` for this planned phase), not direct edits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Every authenticated route" iteration for CFG-79's harness | A new route list | `companion/test_browser_ux.py:994`'s `VIEW_TRANSITION_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")` | Already the six-route tuple this exact codebase uses to prove a per-route property in a real browser (Phase 23's view-transition-name check) — reuse verbatim or duplicate its six literal routes, never invent a second route enumeration |
| A "collapsed extra content" pattern for CFG-79/CFG-82 | A new disclosure component | The existing `<details><summary>How it works</summary>...</details>` pattern (`config_page.py:2152`, `:4435`; `health_page.py:3051` `readings-disclosure`; `health_page.py:3648` `data-card__details`) | Multiple working, tested, no-JS-safe disclosure instances already exist; a new one duplicates a solved problem |
| A small, de-emphasised secondary-action button for any of these requirements | A new `.btn` class | `.calendar-disconnect-btn` (30px, 12px text, 6%/12% wash, 20% hairline) — already reused twice (`_view_panel_button_html()` in `history_page.py`, the per-card Replace control in `airlines_page.py`) | `references/control-density.md` names this class explicitly as "the pattern to reuse the next time this app needs a small, deliberately de-emphasized secondary action" |
| A live-region swap-survival mechanism for CFG-83 | A new swap-exclusion rule or a new "preserve state across refresh" script | Nothing — `freshness.js` already re-fetches `window.location.href`, so a query-param-encoded reveal state survives automatically | Building a preservation mechanism for a `<details>`-based reveal (e.g., re-opening it after a swap) is solving a problem the query-param approach doesn't have in the first place |

**Key insight:** every one of these six requirements is a markup/CSS/copy change inside an already-mature Python-rendered app with six standing design contracts (motion, colour-separation, spacing, drawings, controls, review-feedback discipline — see `sketch-findings-skypane` skill). The risk in this phase is not "what library to use" (there is none) but "which existing mechanism does this new requirement collide with" — CFG-80 collides with B14's normalised-time twin, CFG-81 collides with a ~30-site test contract, CFG-83 collides with the live-refresh swap loop.

## CFG-79 — Editorial floor: concrete offenders

**"Every authenticated route" convention already exists.** `companion/test_browser_ux.py:994`:
```python
VIEW_TRANSITION_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")
```
This is the exact six-route tuple Phase 23's `_page_carries_expected_view_transition_names()` iterates with a real browser to assert a per-route property from COMPUTED values (not a source scan). CFG-79's own harness check should reuse this tuple (or an equal, separately-named copy pinned equal to it) rather than invent a second route list — the same reasoning that keeps `_nav_links()` the one source of truth for the nav set.

**Cheapest check shape:** for each of the 6 routes × 2 languages, render the authenticated page, `querySelectorAll('.section-caption, .lightbox__note, [class$="__body"]')`-equivalent (the exact selector needs picking — every module composes `.section-caption` onto varying tag/class combinations, see the 41-site grep result below), and assert every element's rendered `.textContent.trim().split(/\s+/).length <= 12`. Mutation-proof it by temporarily lengthening one caption in a fixture and confirming the check fails.

**Word-count offenders found by direct measurement (module-level string constants rendered under a card title, English form; word counts computed by naive whitespace split — French renders separately and was not re-measured, but every English offender below has a French sibling in the matching `i18n_fr/*.py` module that must also be shortened in step, per CFG-79's "in both languages" requirement):**

| File:Line | Constant | Words | Text (truncated) |
|-----------|----------|-------|--------------------|
| `config_page.py:474` | `LED_SECTION_CAPTION` | 20 | "Lit only during the device's brief wake window, not visible from the wall side. Applies on the next scheduled poll." |
| `config_page.py:782` | `NOTIFICATIONS_URL_HINT` | 26 | "Paste your ntfy.sh topic URL (or a self-hosted one). Stored on the server and never shown back here — pasting a new one replaces the old." |
| `config_page.py:1205` | `CALENDAR_URL_HINT` | 22 | "Your calendar's private iCal link. Stored on the server and never shown back here — pasting a new one replaces the old." |
| `config_page.py:605` | `WAKE_INTERVAL_SECTION_CAPTION` | 19 | "Shorter means fresher info and more battery drain; longer means more battery life and staler info at a glance." |
| `config_page.py:772` | `NOTIFICATIONS_SECTION_CAPTION` | 15 | "Get a push alert when the battery runs low or the frame stops checking in." |
| `config_page.py:471` | `RUNWAY_SECTION_CAPTION` | 14 | "Which Orly runway the device watches. Applies on the next scheduled poll, not immediately." — **still repeats "applies on the next scheduled poll," which CFG-79 says must appear in exactly one place per page, not under each card** |
| `config_page.py:190` | `DEVICE_POLL_INTRO` | 14 | "— fetch a new picture right now instead of waiting for the next wake." |
| `config_page.py:148` | `DEVICE_PAGE_PURPOSE` | 14 | "Hardware, data and diagnostics for the frame. Nothing here needs changing day to day." |
| `config_page.py:491` | `POLL_SECTION_CAPTION` | 14 | "Manually trigger an immediate poll cycle instead of waiting for the next scheduled one." |
| `config_page.py:210` | `FRAME_COLOURS_CAPTION` | 13 | "Choose the colour theme for departures, arrivals, calendar flights and your own rules." |
| `config_page.py:160` | `DISPLAY_LOOK_INTRO` | 13 | "— the theme, flight colours and calendar that decide how the picture looks." |
| `airlines_page.py:92` | `EDIT_TOGGLE_CAPTION` | 13 | "Replace an airline's picture or add one for an airline that has none." — **moot once CFG-81 deletes the toggle it belongs to; do not fix this one in a CFG-79 task, delete it in the CFG-81 task instead** |
| `airlines_page.py:456` | `RESOLVE_CAPTION_TEMPLATE` | 15 | "Every flight using prefix %s will show as this airline once you save a name." |
| `airlines_page.py:478` | `STEP_B_CAPTION` | 15 | "Saved. This airline doesn't have artwork yet — add one below, or skip for now." |
| `airlines_page.py:473` | `NAME_HINT_TEXT` | 23 | "Start typing — pick a suggestion if the airline already has artwork, so this reuses it instead of asking for a new upload." |
| `airlines_page.py:306` | `UPLOAD_PREVIEW_CAPTION_TEXT` | 14 | "Framing preview — how it will be framed. The server does the final crop." |
| `airlines_page.py:543` | `MANUAL_DELETE_CAPTION` | 13 | "Deleting removes only this manual name — any uploaded artwork stays in place." |
| `airlines_page.py:547` | `MANUAL_SUPERSEDED_NOTE_TEMPLATE` | 36 | Long, multi-clause; renders as `.lightbox__manual-note`, not `.section-caption` — check whether this element is "a caption under a card title" in CFG-79's sense or a status/error message exempt from the floor (recommend: exempt, since it names a real conflict state rather than describing a control) |
| `health_page.py:595` | `CHECK_IN_CAPTION_CADENCE` | 22 | "Judged against the cadence configured now — a check-in every %s — not necessarily the cadence in force on an earlier day." |
| `health_page.py:602` | `CHECK_IN_CAPTION_CADENCE_FALLBACK` | 22 | Similar length, fallback wording |
| `health_page.py:611` | `CHECK_IN_CAPTION_NOT_PROOF` | 24 | "A day with no record is not proof the frame did not wake: a log rotation this server missed leaves exactly the same gap." |
| `health_page.py:616` | `CHECK_IN_CAPTION_EMPTY` | 18 | "No check-in intervals are recorded yet, so every day below is a day the record says nothing about." |
| `health_page.py:692` | `_READ_ONLY_NOTE` | 25 | "This list is read-only here — each row's Resolve link opens the Airlines page to name that airline (and add artwork, if it needs one)." |

**Note on `RUNWAY_SECTION_CAPTION`/`LED_SECTION_CAPTION`:** both already had their stale schematic-map clause cut in Lot A (confirmed at `config_page.py:460-470`'s own comment: "the two schematic-drawing clauses a prior revision added here ... had been describing a picture that no longer exists since CFG-66 shipped"). What remains is still over the 12-word floor and still repeats the "applies on the next scheduled poll" mechanism clause — CFG-79's rule says this sentence belongs in exactly one place per page (the Frame strip/save bar already carries it — see `layout.py`'s `frame_strip_html()`), so the fix here is deletion of that clause from BOTH captions, not merely trimming words elsewhere.

**Existing "How it works" disclosure homes for overflow content:** `CALENDAR_HOW_IT_WORKS_SUMMARY = "How it works"` (`config_page.py:1150`), the `theme-carousel__all` disclosure, and `<details><summary>%s</summary><p class="text-body">%s</p></details>` inline pattern at `config_page.py:2152`/`:4435`. Any clause cut from a caption that is genuinely useful reference material (e.g., the notification URL provenance sentence, the calendar URL storage sentence) should move into one of these, per CONTEXT.md's "anything longer moves into the existing 'How it works' disclosure, or is deleted outright."

## CFG-80 — Quiet hours as one object

**Current markup order** (`config_page.py`'s `quiet_hours_group()`, lines 3240-3442): `<h2>` heading → `<p class="section-caption">` (caption + delay sentence) → `dial_html` (`quiet_dial_html()`) → `readout_html` → `preset_row_html` (`.runway-row`, 3 buttons) → `<label>Start <input type="time"> + _normalised_time_html() sibling</label>` + error → `<label>End <input type="time"> + _normalised_time_html() sibling</label>` + error. The docstring is explicit that "10-UI-SPEC.md locks the order of the four CONTROLS — presets, then Start, then End, **each on its own full-width line**" (`config_page.py:3389-3391`) — this full-width-line rule is exactly what CFG-80 needs to relax for Start/End to render "on one line as one visual unit," so the plan must explicitly supersede that locked layout rule (not silently ignore it) and say so in the new function's docstring, matching this codebase's SUPERSEDED-in-place convention.

**CSS surface to change:** `.quiet-dial` block (`style.css:1312+`), and each `<label>` currently has no wrapping class of its own — a new wrapper class is needed to lay Start+End out side by side (or beneath the dial as one grid) instead of as two independent full-width `<label>` elements. `.field-inline-value` (`style.css:8238`) is the existing style for the normalised-time sibling span — reuse rather than reinvent.

**B14's own ground for existing at all** (`_normalised_time_html()` docstring, `config_page.py:2665-2694`): "A native time control formats itself from the browser's own locale, so a browser in en-US renders the stored '23:00' as '11:00 PM' ... The audit's fix is to SHOW the stored 24h text." This ground is UNCHANGED by CFG-80 — only the twin's default visibility changes (hidden when redundant, shown when needed), which the function's docstring should say explicitly to avoid a future reader thinking the whole element is being second-guessed.

**No existing 24h-detection pattern found.** Grepped `companion/static/*.js` and `test_browser_ux.py` for `hour12`, `resolvedOptions`, `12h`, `24h` — the only hits are comments/test names referencing the existing dial/B14 mechanism, not a detection routine. This is a genuine gap: **[ASSUMED]** the standard client-side approach is `new Intl.DateTimeFormat(navigator.language, {hour: "numeric"}).resolvedOptions().hour12 === false`, but this measures the BROWSER's locale-derived preference, not necessarily what a specific `<input type="time">` will actually paint (browsers are not contractually required to align the two, though in practice Chromium/Firefox/Safari all follow the OS locale for both). The `<input>`'s own `lang="{site_lang}"` attribute (set explicitly at `config_page.py:3435`/`:3439`) is a request to the control, not a guarantee it is honoured — B14's whole premise is that some browsers ignore it. Because no DOM API directly exposes "what did this specific `<input type="time">` just render," any detection is necessarily an approximation via `Intl.DateTimeFormat`. **This should be flagged to the developer as a low-confidence mechanism before locking a specific implementation** — recommend the planner add a `checkpoint:human-verify` or at minimum test on a real 12h-locale browser (e.g., a macOS/iOS device set to US region) before considering the hide-condition correct, since a false negative (hiding the twin when the native field is ACTUALLY ambiguous) directly reintroduces the defect B14 was built to fix.

**Presets:** currently three `type="button"` elements in a `.runway-row` flex/wrap container (`config_page.py:3346-3365`), with long labels via `QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE % (start, end)` (renders "Night (23:00-07:00)" per the ROADMAP's own quote). CFG-80 wants these shortened to bare "Nuit"/"Journée" (no hours) as a segmented control — this is a straightforward template change plus (optionally) a new `.segmented-control`-style CSS treatment, or reuse of the existing `.theme-form`/`.theme-option` segmented-button idiom already used for the language/theme footer switches (`layout.py`, "Both remaining `<form class="theme-form" method="post">`s still reuse the identical bordered-container-plus-borderless-segment idiom").

## CFG-81 — Illustration dialog owns its actions

**Every `edit_mode`-related site in `airlines_page.py`, classified:**

| Line(s) | Site | Classification |
|---------|------|-----------------|
| `938`, `968-976` | `_airline_card_html(..., edit_mode=False)` param + docstring | Must become unconditional — but see below, the per-card Replace button this gates is being REMOVED (Replace now lives only in the shared dialog per CFG-81's decision text), not made unconditional in place |
| `1188-1196` | `replace_control_html` — the per-card "Replace picture" `.calendar-disconnect-btn` | **Delete entirely.** CFG-81's decision is "Replace ... render in the dialog on EVERY open" — the per-card button was the "bouton pas au bon endroit" the developer complained about ("quand on est dans la liste d'avion on ne le voit plus"); it is not being made unconditional, it is being removed, because the dialog's own Replace form now suffices |
| `1223-1224`, `1256-1259`, `1273` | `_gallery_grid_html(..., edit_mode=False)` param, threaded to every card | Delete the parameter (no card-level affordance survives) |
| `1555`, `1648-1649` | `_lightbox_html(edit_mode=False)`; `replace_html`/`delete_html` gated `if edit_mode else ""` | Must become unconditional — `replace_html = _lightbox_replace_form_html()` and `delete_html = ...` always render. Note delete is currently rendered even when `edit_mode` is true regardless of whether the CURRENT airline is a manual entry — the existing `_manual_delete_form_html("")` call takes an empty action placeholder that `panel-lookup.js` overwrites per-click (mirroring the Replace form's own `action=""` placeholder mechanism) — so "Delete, for a manually resolved entry" is ALREADY handled by the JS setting/not-setting the action and (per `panel-lookup.js`'s own `if (form)`-style guards) presumably toggling visibility per open; confirm this at implementation time rather than assuming, since the docstring only documents the edit_mode gate, not per-open visibility logic |
| `2091`, `2213` | `_resolve_section_html(ctx, edit_mode=False)`; `delete_form = ... if edit_mode else ""` | Must become unconditional (same reasoning: an entry always eligible for delete should always show it, no page-wide toggle needed) |
| `2342-2379` | `_edit_toggle_html(ctx, edit_mode)` | **The toggle link itself — delete the whole function and its call site** |
| `2447`, `2455`, `2544`, `2575`, `2583` | `render()`'s own `edit_mode = bool(ctx.get("edit_mode"))` and threading | Delete the local variable and every keyword pass-through |

**Unrelated, leave alone:** nothing else in this module reads `edit_mode` — the resolve-flow's Step A/Step B branching (`_resolve_section_html`'s `entry is None` / artwork-exists checks) is independent of `edit_mode` and untouched.

**No other page depends on `?edit=1` surviving**, confirmed by grep: the only production readers are `companion/app.py:1621-1622` (`ctx["edit_mode"] = params.get(airlines_page.EDIT_QUERY_PARAM, [None])[0] == "1"`) and `companion/pages/__init__.py:36,147-150` (the doc-comment describing the same key). Both must be deleted along with `EDIT_QUERY_PARAM`/`CHANGE_PICTURES_TEXT`/`DONE_TEXT`/`EDITING_BADGE_TEXT`/`REPLACE_PICTURE_TEXT`/`REPLACE_PICTURE_ARIA_TEMPLATE` if they become unreferenced (confirm with a "grep the constant name" pass per constant before deleting, since some, e.g. `REPLACE_PICTURE_TEXT`, might read ambiguously close to a surviving one — verify exact identifier match).

**Test blast radius — this is the sizing risk for CFG-81's plan.** `grep -c edit_mode` across `companion/test_status_pages.py` and `companion/test_view_pages.py` finds roughly 30 call sites: dozens of `airlines_page.render(dict(_ctx(tmp), edit_mode=True))` calls, several dedicated checks that assert edit-mode-only behaviour (`_airlines_edit_mode_shows_a_badge_and_one_replace_control_per_card`, `_airlines_edit_mode_render_has_exactly_one_of_each_edit_only_form`, `_airlines_edit_mode_render_shows_done_toggle_with_no_query`, a browser-level check hitting `/airlines?edit=1` directly at `test_status_pages.py:15517`, `test_view_pages.py:8669`). Every one of these tests needs to be deleted, merged into the "everyday" render checks (since the affordance is now unconditional and there is no more edit-mode-vs-default distinction to test), or rewritten to assert the new "always present" behaviour. `EXPECTED_CHECK_COUNT` in both files must be re-derived by running, per this project's own convention — do not hand-compute the new total.

## CFG-82 — Compagnies gallery-first + tab label

**Current `render()` section order** (`airlines_page.py:2576-2586`):
```
page_header
+ edit_toggle_html      (deleted by CFG-81, upstream in the same phase)
+ gap_strip_html        (unidentified prefixes — "Unidentified airlines" strip)
+ filter_html           (filter bar + manual-resolutions summary)
+ gallery_grid_html     (known-airline gallery)
+ lightbox_html
+ resolve_html          (conditional, only when ?resolve= present)
```

**Target order per CFG-82:** `filter_html` + `gallery_grid_html` directly under `page_header`, with `gap_strip_html` (unidentified prefixes) moved to a secondary section BELOW the gallery. Since CFG-81 removes `edit_toggle_html` and any per-card editing affordance, there is no "remaining editing affordance" left to bundle into that secondary section except the already-existing manual-resolutions summary button (`_manual_summary_html()`, which lives inside the filter bar itself, not a separate editing section) — confirm with the planner whether CFG-82's "and any remaining editing affordance" clause is fully satisfied by CFG-81's removal (nothing left to move) or whether it refers to the resolve-flow's own delete/edit controls (which stay conditional on `?resolve=` and are arguably not "on this page's default view" at all). **Recommendation: land the CFG-81 plan before the CFG-82 plan in the same wave-ordering sense CONTEXT.md already flags ("several of these touch airlines_page.py ... cannot safely run in parallel"), since CFG-82's "any remaining editing affordance" is only fully knowable once CFG-81 has already deleted the toggle.**

**Filter/gallery must render even when `gap_shown` is empty and vice versa** — `render()`'s existing "no chrome with no data" gate (`total = len(gap_shown) + len(pairs)`; `filter_html = ... if (pairs or gap_shown) else ""`) already handles this; reordering must preserve, not rewrite, that gate.

**Secondary section framing — Claude's Discretion per CONTEXT.md.** The existing `<details>` pattern (`GAP_STRIP_HEADING`/`GAP_STRIP_BODY`, currently rendered via `_gap_strip_html()` as an always-visible `<section>`, not collapsed) is one candidate; a plain lower `.page-section` with a heading is the other. Given the gap strip already has its own explained heading/body pair (`GAP_STRIP_HEADING = "Unidentified airlines"`, `GAP_STRIP_BODY`), the cheapest change is likely just relocating the existing `_gap_strip_html()` output below the gallery rather than wrapping it in a NEW disclosure mechanism — the section is already "clearly announced" by its own heading; a `<details>` would additionally require deciding a default open/closed state, which the CONTEXT.md text does not ask for.

**Tab-bar label fix — confirmed still directly applicable, not drifted.** `git log -p -L10405,10416` on `style.css` shows `.tab-bar__pill`'s `margin: var(--space-xs) var(--space-sm)` rule has been unchanged since commit `8a3520c` (Phase 22, 2026-09-13) — before, not after, the 2026-09-17 audit. The tab bar's structure (4 direct destination cells + one `<details class="tab-bar__more">` fifth cell holding the "Advanced" group, `layout.py:2198-2317`) also dates to Phase 22 and has not changed since. **The audit's described fix is still exactly correct and directly re-appliable**: change `.tab-bar__pill`'s horizontal margin component from `var(--space-sm)` (8px) to `calc(var(--space-xs) / 2)` (2px), at `style.css:10413`. No other tab-bar CSS needs auditing for drift — Phase 28's only tab-bar-adjacent change was the icon swap (`icon-hamburger` → `icon-gear`, CFG-76), which does not touch `.tab-bar__pill`'s box model.

## CFG-83 — Vols paginated (the genuinely-new-UI requirement)

**Confirmed: no pagination/reveal-more pattern exists anywhere.** `grep -ri paginat` across `companion/` returns nothing; `history_page.py`'s `render()` (lines 1560-1653) fetches up to `HISTORY_ROW_LIMIT = 50` rows and renders ALL of them into both `_history_cards_html()` (mobile) and `_history_table_html()` (desktop) with no slicing of any kind today.

**The decisive fact: `freshness.js` replaces the Flights list wholesale on every background refresh, by re-fetching the CURRENT URL.**
- `layout.py:2189-2194`: `REFRESH_SWAP_SELECTORS_BY_PAGE[REFRESH_PAGE_FLIGHTS] = (".page-header__freshness", "ul.history-cards", ".data-table-wrap", "[data-filter-count]")` — the entire card list and the entire desktop table are swap targets, whole-node replacements, every ~45 seconds (`AUTO_REFRESH_INTERVAL_MS = 45000`, `freshness.js`).
- `freshness.js:885-886`: `fetch(window.location.href, { credentials: "same-origin", ... })` — the loop re-requests the page's OWN current URL, including its query string, not a hardcoded path.

This means:
- **Candidate A — server-side `?limit=` query-param re-render** ("Afficher plus" is a plain `<a href="?limit=30">` link, or a real GET form). After the visitor clicks it, `window.location.href` becomes `.../flights?limit=30`, and EVERY subsequent background refresh from that point on re-fetches `?limit=30` automatically, because `freshness.js` already re-fetches whatever URL the browser is currently on. **No script change is needed for the reveal state to survive a refresh** — this is a direct, free consequence of the existing mechanism. Risk: the server-rendered list at any moment only contains `min(limit, total)` rows, so `list-filter.js`'s client-side filter can only ever match within the currently-loaded subset — a visitor searching for a flight outside the first 15 (before clicking "Show more") gets a false "no matching flights." This is a real, disclosable product trade-off, not a bug, and should be named explicitly in the plan.
- **Candidate B — native `<details>` progressive reveal** (all 50 rows always render, rows past N sit inside a closed `<details>` so they contribute no layout height until opened). This preserves full-dataset client-side filtering (every row is always in the DOM). But: the `<details>`'s `open` state is a plain HTML attribute with no query-param encoding — the server always renders it closed by default, and when `freshness.js`'s `DOMParser`-based swap replaces `ul.history-cards`/`.data-table-wrap` wholesale, the freshly-parsed replacement node's `<details>` is closed, discarding whatever open/closed state the visitor had reached. This is exactly the risk the phase context calls out as "the single most important risk to resolve": **a visitor who opened "Show more," then waits out one 45-second refresh cycle, finds it silently collapsed again with no error and no explanation** — worse than not building the feature, because it looks like data loss. Mitigating this would require either (a) teaching `freshness.js` to read and re-apply the pre-swap `<details open>` state (a new, non-trivial script change, and a precedent for stateful-region handling this file does not currently have for any other element) or (b) adding this element to the loop's existing "unchanged region" skip check (`isEqualNode`) — which does not apply here, since the swap decision is made BEFORE the open-state divergence is even relevant (an open vs. closed `<details>` is a real DOM difference, so `isEqualNode` would already say "these differ, swap them").

**Recommendation: Candidate A (`?limit=` query param).** It is the only one of the two that requires zero changes to `freshness.js`, degrades correctly with scripts blocked (a plain link works with no JS at all — matching this app's no-JS floor exactly the way `?resolve=`/`?edit=1` used to, and the way the filter's own query-independent full-render already does), and its one real cost (filter only searches the loaded subset) is a disclosed, common, and arguably expected trade-off rather than a silent defect. Parse the `limit` query value defensively (the same `try: int(...) except (TypeError, ValueError)` pattern `wake_gauge_interval_s()` in `config_page.py:3471-3476` already uses for a different query/form value), clamp it to `[some minimum, HISTORY_ROW_LIMIT]`, and never trust the raw string past that point (ASVS V5 input-validation floor, see Security Domain below).

**Filter-bar-stays-visible requirement:** trivially satisfied by either candidate, since `_filter_bar_html()` already renders unconditionally before the list body in `render()`'s existing code path (`history_page.py:1648-1651`) and nothing about either pagination candidate needs to move it.

**Summary-card grid stability at 390px** (the timestamp/callsign collision) is an independent CSS fix inside `_history_cards_html()`'s card markup or its CSS grid-template — orthogonal to the reveal mechanism; measure the resolved box at 390px directly (per the "review-feedback discipline" standing contract: "a declared hit target/grid is not a resolved one ... measure the resolved box, in its own container, always").

## CFG-84 — État's title shortened

**Current shipped state, confirmed exact:** `health_page.py`'s `_battery_trend_section_html()` (lines 2858-2947) renders:
```html
<h2 class="text-heading">Battery trend<span class="text-label section-caption"> — {caption}</span></h2>
```
where `{caption}` is computed by `_battery_trend_caption()` (lines 935-956+) and is either:
1. `"Last 3 months, daily average"` (`i18n_fr`: "3 derniers mois, moyenne quotidienne") — when a real ≥2-day daily series exists, or
2. `"Latest %d readings"` (fallback, <2 daily buckets) — a DIFFERENT string, not the 3-month framing.

The audit's quoted string ("Tendance de la batterie — 3 derniers mois, moyenne quotidienne" / in English "Battery trend — Last 3 months, daily average") is branch 1 rendered as one combined `<h2>` with an inline `<span>`.

**CFG-84's target:** `<h2>` reads a fixed "Battery · 3 months" / "Batterie · 3 mois" (no longer conditional on which caption branch fires), with "daily average" (branch 1) or the reading-count fallback (branch 2) moved to the card's **existing caption** as a sibling element, not an inline `<span>` inside the `<h2>`. This is a genuine restructuring, not a string edit: today the "caption" IS the inline span inside the heading; CFG-84 wants a heading and a caption as two separate elements, matching the pattern the rest of the editorial-floor pass (CFG-79) is already establishing site-wide (`<h2>` title, then a sibling `<p class="section-caption">`). **Recommend doing CFG-84's restructuring using the same h2+sibling-caption shape CFG-79 uses elsewhere**, so the two requirements don't produce two different "how a card names itself" idioms in the same phase. `_battery_trend_caption()`'s own two-branch logic (real average vs. reading-count fallback) survives unchanged and simply feeds the new caption paragraph instead of the inline span — `BATTERY_TREND_WINDOW_DAYS` (already a constant, confirms "3 months" is a real, non-magic value to interpolate into the new fixed heading template, not a hardcoded "3").

## Common Pitfalls

### Pitfall 1: Treating CFG-81's removal as "delete two `if edit_mode` lines"
**What goes wrong:** a plan that only edits `_lightbox_html()` and `_resolve_section_html()` leaves `edit_mode` params on 3+ other functions, the `_edit_toggle_html()` function itself, the `app.py`/`__init__.py` query-param plumbing, and ~30 test call sites all dangling or silently no-op.
**Why it happens:** the two most-visible `if edit_mode` gates (the ones directly named in CFG-81's decision text) are easy to find by grep; the constant-threading and the test suite are not mentioned in the requirement text at all.
**How to avoid:** use the classification table above as the task checklist; grep `edit_mode` in `companion/` AND `companion/test_*.py` before declaring the task done, and expect the test file diff to be large.
**Warning signs:** `EXPECTED_CHECK_COUNT` in `test_status_pages.py`/`test_view_pages.py` not re-derived by running; any remaining `ctx.get("edit_mode")` or `EDIT_QUERY_PARAM` reference after the plan claims completion.

### Pitfall 2: Building CFG-83 as a `<details>` reveal without testing it against a real background refresh
**What goes wrong:** every unit-level render test can pass (the markup for a `<details>` reveal is simple and easy to get right in isolation) while the live-refresh interaction silently regresses the feature the moment `freshness.js`'s 45-second loop fires.
**Why it happens:** `test_view_pages.py`/`test_status_pages.py`'s render-level checks call `history_page.render(ctx)` directly and never simulate the swap loop; only `test_browser_ux.py`'s real-browser checks exercise `freshness.js` at all, and even those may not think to open the reveal, wait a refresh cycle, and re-check its state.
**How to avoid:** whichever mechanism is chosen, add a real-browser check that opens the reveal, forces (or waits for) one refresh cycle, and asserts the reveal state survives — matching this codebase's "review-feedback discipline" standing contract of asserting relationships (the reveal state before and after a refresh), not just endpoints (the reveal renders once, on first load).
**Warning signs:** a plan's acceptance criteria only test the reveal mechanism's FIRST render, never a second render simulating a refresh.

### Pitfall 3: Assuming the 2026-09-17 audit's tab-bar fix needs re-deriving because "the CSS has moved"
**What goes wrong:** spending a task re-measuring the tab bar's box model from scratch when the actual rule (`.tab-bar__pill`'s margin) has been byte-identical since Phase 22, predating the audit itself.
**Why it happens:** the phase context's own caution ("Phase 28's current tab-bar CSS ... has moved since that diff was written") is true in a general sense (Phase 28 did touch tab-bar-adjacent code, the icon swap) but does not apply to the specific rule the audit's fix targets.
**How to avoid:** `git log -p -L<line-range>:companion/static/style.css` on the specific rule before re-deriving a fix from scratch — as done in this research, confirming the exact pre-audit state is still live.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Hand-rolled Python harnesses (`unittest`-free, stdlib-only, each module a standalone script with its own `main()`/`check()` helper and an `EXPECTED_CHECK_COUNT` gate) |
| Config file | none — each `companion/test_*.py` is directly executable |
| Quick run command | `python3 companion/test_view_pages.py` / `python3 companion/test_status_pages.py` / `python3 companion/test_config_page.py` / `python3 companion/test_i18n.py` (each self-contained; some spin up a real `companion/app.py` instance and a headless browser for DOM-level checks) |
| Full suite command | Run every `companion/test_*.py` module in sequence (no single aggregating entrypoint found in this repo slice — confirm whether one exists elsewhere before assuming there is none) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-79 | Every `.section-caption`/disclosure caption ≤12 words, rendered, on every authenticated route, both languages | browser (real DOM measurement) | `python3 companion/test_browser_ux.py` (new check to add) | ✅ file exists, ❌ check does not exist yet |
| CFG-80 | Start/End render as one visual unit with the dial; the normalised twin hides only when the native field is unambiguous 24h | browser | `python3 companion/test_browser_ux.py` (extends the existing quiet-dial `_assert_surfaces_agree()`-style checks around line 11540-11900) | ✅ file/pattern exists, ❌ new assertion needed |
| CFG-81 | Dialog's Replace/Delete render unconditionally; `edit_mode`/`?edit=1` fully absent | unit + browser | `python3 companion/test_view_pages.py`, `python3 companion/test_status_pages.py` | ✅ existing edit-mode checks must be rewritten/removed |
| CFG-82 | Filter+gallery directly under title; tab label unellipsed at 360/390px | unit + browser | `python3 companion/test_view_pages.py` (section order), `python3 companion/test_browser_ux.py` (label `scrollWidth`) | ✅ |
| CFG-83 | Reveal works with scripts blocked; reveal state survives a background refresh; filter bar stays visible; summary grid stable at 390px | browser | `python3 companion/test_browser_ux.py` (new checks) | ❌ Wave 0 — no pagination test infra exists yet |
| CFG-84 | `<h2>` reads fixed "Battery · 3 months" form; caption carries the precision | unit | `python3 companion/test_status_pages.py` | ✅ |

### Sampling Rate
- **Per task commit:** the specific module's own test file (e.g. `python3 companion/test_config_page.py` after a `config_page.py` edit)
- **Per wave merge:** every touched module's test file, plus `python3 companion/test_i18n.py` (French-completeness is touched by every copy change in this phase) and `python3 companion/test_browser_ux.py` (the shared cross-page browser checks)
- **Phase gate:** full suite green before `/gsd-verify-work`, with every `EXPECTED_CHECK_COUNT` re-derived by running (this project's own standing convention, restated by every prior phase's closing gate)

### Wave 0 Gaps
- [ ] CFG-79's route×language×caption-length browser check — does not exist yet, needs the `VIEW_TRANSITION_ROUTES`-style route tuple plus a new caption-selector-and-word-count assertion in `test_browser_ux.py`
- [ ] CFG-83's reveal-survives-a-refresh browser check — genuinely new test infrastructure, no precedent in this codebase for "trigger the live-refresh loop and re-assert client state" (existing refresh-loop checks assert region content, not user-interaction-state persistence)
- [ ] Framework install: none — everything needed already exists in this repo

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged by this phase — every touched route is already session-gated |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged — CFG-81 removes a presentation-only toggle, not an authorization check (the routes the removed forms POST to were never gated by `edit_mode` server-side, per `pages/__init__.py`'s own doc comment: "no POST handler ever consults it") |
| V5 Input Validation | yes | CFG-83's new `?limit=` query param must be parsed defensively (`try: int(...) except (TypeError, ValueError)`, matching `config_page.py:3471-3476`'s existing pattern) and clamped to a safe range before use — never interpolated into a query or used to size an allocation without a ceiling |
| V6 Cryptography | no | unchanged |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded `?limit=` value (e.g. `?limit=999999999`) forcing an oversized render/DB read | Denial of Service | Clamp to `[minimum, HISTORY_ROW_LIMIT]` (50 is already the DB query cap — `?limit=` should never be allowed to request more rows than `history_rows()` ever fetches) |
| Non-integer `?limit=` value causing an unhandled exception | Denial of Service (crash-a-render) | `try/except (TypeError, ValueError)` degrading to the default limit, matching this codebase's "never raise, degrade to a documented fallback" discipline used throughout `history_page.py`/`config_page.py` |
| `edit_mode` removal accidentally leaving a POST route that assumed `?edit=1` gating | Elevation of Privilege | Not applicable here — confirmed via `pages/__init__.py`'s own doc comment that no POST handler ever reads `edit_mode`; it was presentation-only from the start. Still worth a final grep of `companion/app.py`'s POST dispatch for any stray `edit_mode`/`EDIT_QUERY_PARAM` reference before closing the CFG-81 plan |

## Sources

### Primary (HIGH confidence — direct source read in this worktree)
- `companion/pages/config_page.py` — `quiet_hours_group()`, `_normalised_time_html()`, caption constants (lines cited throughout)
- `companion/pages/airlines_page.py` — `render()`, `_lightbox_html()`, `_edit_toggle_html()`, `_resolve_section_html()`, `_airline_card_html()` (lines cited throughout)
- `companion/pages/history_page.py` — `render()`, `_filter_bar_html()`, `HISTORY_ROW_LIMIT`
- `companion/pages/health_page.py` — `_battery_trend_section_html()`, `_battery_trend_caption()`
- `companion/layout.py` — `REFRESH_SWAP_SELECTORS_BY_PAGE`, `_tab_bar_html()`
- `companion/static/style.css` — `.tab-bar__pill` and surrounding tab-bar rules, `.quiet-dial*`, `.field-inline-value`
- `companion/static/freshness.js` — the `fetch(window.location.href, ...)` swap mechanism
- `companion/test_browser_ux.py` — `VIEW_TRANSITION_ROUTES` convention
- `git log -p -L<range>` on `style.css` — confirmed no drift on the `.tab-bar__pill` rule since Phase 22
- `.planning/ROADMAP.md` Phase 29 entry — exhaustive prior investigation, file:line references, developer quotes
- `.planning/phases/29-.../29-CONTEXT.md` — locked decisions
- `.planning/ui-reviews/2026-09-17-companion-ui-ux-audit.md` — the measured audit behind CFG-82/83/84
- `.claude/skills/sketch-findings-skypane/SKILL.md` — design-system reference (save-bar mechanism, settings-page patterns, no-JS control contract, tab-bar/nav history)

### Secondary (MEDIUM confidence)
- `[ASSUMED]` `Intl.DateTimeFormat(...).resolvedOptions().hour12` as CFG-80's 24h-detection mechanism — plausible, standard, but not verified against this codebase's own conventions since no precedent exists here; flagged for developer confirmation

### Tertiary (LOW confidence)
- None — this research had no external-web component; everything is a direct codebase read

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Intl.DateTimeFormat(...).resolvedOptions().hour12` is the correct mechanism to detect whether a native `<input type="time">` will render unambiguous 24h | CFG-80 | A false negative (twin hidden when the field is actually ambiguous) silently reintroduces the exact defect B14 was built to fix — recommend a real-device check on a 12h-locale browser before shipping |
| A2 | CFG-82's "any remaining editing affordance" has nothing left to move once CFG-81 lands (no separate editing section survives) | CFG-82 | If wrong, the CFG-82 plan under-delivers by leaving an editing affordance in the wrong place; low risk since it is easily caught by rendering the page and looking |
| A3 | The `<details>` visibility divergence (open vs. closed) is sufflicient to make `freshness.js`'s existing `isEqualNode`-based "skip an unchanged region" check NOT protect an open `<details>` from being swapped closed | CFG-83 | If wrong (i.e., if the DOM's `isEqualNode` somehow treats an open/closed `<details>` as equal, which is not how the DOM spec defines node equality), the risk named for Candidate B would not materialize — but this would be surprising and should be verified empirically before relying on it, not assumed away |

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no external packages/libraries in scope for this phase
- Architecture (section order, CSS state, `edit_mode` blast radius): HIGH — every claim traced to a specific file:line in this worktree
- CFG-80's 24h-detection mechanism: LOW — genuine gap in this codebase, no precedent found, flagged as an assumption requiring confirmation
- CFG-83's swap-survival analysis: HIGH — traced directly to `freshness.js`'s own fetch call and `layout.py`'s own swap-target registry

**Research date:** 2026-09-21
**Valid until:** this phase's own execution — the findings are pinned to this worktree's exact current file contents (several git-blame checks were run to rule out drift since the 2026-09-17 audit); re-verify line numbers if this phase is replanned after other work lands on the same files.
