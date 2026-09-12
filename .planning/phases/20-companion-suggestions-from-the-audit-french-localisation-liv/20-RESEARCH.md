# Phase 20: Bilingual companion, Display regrouped, Home redesigned, live theme preview, notifications, simple mode - Research

**Researched:** 2026-09-11
**Domain:** Python stdlib HTTP service (`companion/`), server-rendered HTML, ES5 vanilla JS static assets, a new i18n layer, a new outbound-HTTP notification sender, a shared server-side wake-arithmetic module — no new external dependency in any of the six areas
**Confidence:** HIGH (every claim below is grounded in a direct `Read`/`Grep` of the live code and a live run of every affected test harness; no library/API research is needed anywhere in this phase — every mechanism is either already precedented in this codebase or a pure-stdlib addition)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Every decision below is locked (it comes from the PRD, which records the developer's own requests verbatim). The four items under "Assumptions flagged" are the orchestrator's readings of a short request; they are locked for this phase and one-line changes if the developer later prefers otherwise. Full text of every D-01..D-36 decision is in `20-CONTEXT.md` and is not repeated verbatim here — see that file for the complete wording; this section names only the letter-groups for cross-reference.

- **A. Bilingual companion — French and English** (D-01..D-09, S-01/CFG-13)
- **B. Display page regrouped** (D-10..D-15e, CFG-15) — Runway/Calendar/Flight-colours join Display; Calendar (D-14) and Flight colours (D-15) get a full UX/UI redesign.
- **C. Home redesigned** (D-16..D-21, CFG-14) — no quick actions on Home; hero row + recent flights; fixes the duplicated verdict and the past "Next wake" bug; a new `layout.status_row()` primitive.
- **D. Live theme preview** (D-22..D-24, S-03/CFG-16) — a live render above the existing chip grid, cached per (theme, event id).
- **E. Notifications** (D-25..D-28, S-05/CFG-17) — an ntfy-style push topic, configured on Device, sent from the poll loop on `battery_low_active`/frame-silent transitions only.
- **F. Simple mode** (D-29..D-31, S-06/CFG-18) — a per-browser cookie hiding the Advanced group and every advanced affordance.
- **G. Artwork editing made obvious** (D-36) — "Edit artwork" leaves Device; Airlines gets its own "Change pictures"/"Done" toggle.
- **H. Cross-cutting** (D-32..D-35) — no new inline scripts; test-file ownership per wave; the design-system skill updated; the audit dashboard closed out.

### Claude's Discretion
- Exact French wording of every string (within D-09's rules); the catalogue file layout.
- How `t()` learns the request language (`contextvars.ContextVar` expected; thread-local acceptable).
- Compact theme chip's exact dimensions, status-row's exact spacing, hero row's breakpoint — within the design-system skill's tokens.
- The `?live=1` preview cache key and its invalidation scheme.
- Notification body wording (both languages) and the exact "silent" multiplier if 3x proves too twitchy — must not go below Health's own warn threshold.
- Plan/wave split; test-file ownership per wave (no two plans in one wave may edit the same test file).

### Deferred Ideas (OUT OF SCOPE)
- A second, read-only password.
- Email/SMS notifications; a daily digest.
- Any change to frame firmware or the panel renderer's output.
- A third UI language.
- Per-screen state directories (the `screen_id` seam stays as-is).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-13 | Bilingual FR/EN, per browser, English source + French catalogue + completeness check | Section A below: `companion/i18n.py` design, `companion/app.py` cookie/route additions, the D-06 JS gap (narrower than assumed), D-08's completeness-harness mechanics |
| CFG-14 | Home redesign: hero row, one status card, recent flights, no quick actions | Section C below: `home_page.py` rebuild, the confirmed duplicated-verdict root cause, `layout.status_row()` |
| CFG-15 | Display carries every everyday setting; Calendar/Flight-colours redesign | Section B below: `screens.py` group moves, the HTML form-nesting conflict for D-19's instant switches, D-14c's calendar-connect scope hazard, D-15's rule-row rebuild |
| CFG-16 | Live theme preview from the last real flight | Section D below: `theme_preview.py`'s existing cache/signature scheme extended for a live event id |
| CFG-17 | Push notification on battery-low / frame-silent transitions | Section E below: `server/poll_loop.py`'s two `battery_low_active` sites, the new `server/wake.py` seam, `server/device_config.py`'s `notifications` group |
| CFG-18 | Simple mode hiding Advanced pages/affordances | Section F below: nav/health-dot/link gating points, all presentation-only |
</phase_requirements>

## Summary

This phase is six coordinated features layered onto one mature, well-commented, stdlib-only codebase — the real risk is not "unknown domain," it is **structural conflicts between a locked decision's literal wording and this codebase's own HTML/test constraints**, exactly the shape phase 19's research flagged twice (CSP vs. inline styles, `<fieldset>` vs. zero-fieldset pinned checks) and both times the resolution was "the decision's own text already offers the compatible alternative — use it, do not implement the literal reading." This phase has at least three of the same shape, found by direct code read, documented below with their resolutions:

1. **D-19's instant-switch placement is impossible as literally described.** "The Screen on/off group gets a `.quick-action` switch row at its top... They are their own forms" cannot be satisfied by nesting a `<form>` inside `<form id="settings-form">` (HTML forbids nested forms) — and `quiet_hours_group()`/`display_group()`'s own markup is emitted **inside** that form today (verified: `render()`'s returned string is `header + '<form ...>' + hidden_html + groups_html + ... + '</form>' + ...`, and `groups_html` is the concatenation of every group builder including these two). The already-shipped precedent for exactly this shape is `form="{SETTINGS_FORM_ID}"` on the dirty-bar's Save button (quick task 260901-re6) — an element outside the `<form>` tag that still submits into it. The fix: split `quiet_hours_group()`/`display_group()` into an outer, non-form wrapper rendered as a **sibling** of `<form id="settings-form">` (same slot pattern as `calendar_disconnect_section()`/`_rules_section_html()`), containing (a) the new quick-action mini-`<form>` and (b) the scheduled-setting controls carrying `form="settings-form"` so they still submit with the batched Save despite no longer being a DOM descendant of it.
2. **D-14c's "Connect posts immediately... the existing save path for the URL"** must NOT be implemented as a small form posting `scope=display` to the existing `/settings` route once D-11 lands, because `handle_post()`'s per-scope checkbox semantics ("group in scope + checkbox absent => explicitly turn OFF") would silently disable Quiet hours/Screen the moment Calendar joins the Display scope's `in_scope` set. The safe path is a **dedicated route** (mirroring `calendar_disconnect_section()`'s own already-shipped precedent) that calls `calendar_rules.save_calendar_url()` + `calendar_rules.refresh_calendar_registry()` directly — the same two functions `_handle_settings_post()` already calls — never through the generic scoped `handle_post()`.
3. **Home's duplicated verdict bug (D-17) has a confirmed, single-line root cause**, not a vague "repeats text" description: `home_page._status_tiles_html()` builds its own `frame_body` from `FRAME_STATE_TEXT[device_state]`, then appends `ctx["health_state"]["device_html"]` verbatim as a second paragraph — but `device_html` (built by `health_page._device_section()`) **already contains its own verdict paragraph** from `DEVICE_STATE_TEXT`, whose three values are byte-identical to `FRAME_STATE_TEXT`'s. The fix is a `device_html`-shaped value split into "verdict" and "detail-only" parts, or a new detail-only helper in `health_page.py` that `home_page.py` calls instead of reusing the whole tile fragment.

Beyond these three, the phase's JS work for D-06 is **narrower than the CONTEXT text implies**: `freshness.js`, `confirm-submit.js`, and `poll-cooldown.js` already read every visible string from server-rendered `data-*` attributes (confirmed by direct read of all three files) — they need zero JS changes for i18n, only their *server-side* callers wrapping the attribute values in `t()`. Only `copy-button.js`'s hardcoded `FEEDBACK_TEXT = "Copied"` and `dirty-state.js`'s hardcoded "changed"/"and"/"unsaved change(s)" connector words are genuine JS-side literals that need a `data-*` attribute added.

**Primary recommendation:** Treat Section A (i18n infrastructure) as Wave 0 — every other section's new/moved strings need `t()` to exist first. Treat the three structural conflicts above as their own reviewed decisions before Wave 1 starts on B/C, exactly as phase 19's plan-check process did for its own two conflicts.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Language selection, translation lookup, `<html lang>` | API/Backend (`companion/i18n.py`, `companion/app.py`, `companion/layout.py`) | — | Every string is server-rendered; there is no client-side templating framework in this app to localise separately |
| JS-carried strings (D-06) | API/Backend (server renders the text into `data-*`) | Browser (`companion/static/*.js` reads the attribute) | The browser scripts are dumb DOM-attachment code with zero literal English left after this phase, matching this app's "no client rendering framework" architecture |
| Display/Device settings persistence + validation | API/Backend (`companion/pages/config_page.py`, `server/device_config.py`) | Browser (`dirty-state.js` UX only) | Unchanged from phase 19's own map — server is sole source of truth |
| Home/Display presentation | API/Backend (server-rendered HTML) | Browser (`theme-preview.js`, `rule-form.js` new; existing scripts) | No client rendering framework; JS only attaches behaviour to already-rendered DOM |
| Live theme preview render + cache | API/Backend (`companion/theme_preview.py`, `server/plane/render.py`) | Database/Storage (`theme_previews` cache dir on disk, `server/history_db.py` for the "last event") | Rendering happens server-side through the existing Pillow pipeline; the cache is a filesystem artifact keyed by (theme, event) |
| Notifications | API/Backend (`server/poll_loop.py`, a new `server/notify.py`) | External service (the operator's ntfy topic URL) | The poll loop is a server-only cron-like process with no browser; delivery is a plain outbound POST, no new infra |
| Simple mode | API/Backend (server decides what to render) | Browser (nothing — presentation only, no client gating) | D-30's own text: "a presentation choice, not an access control" — the server renders less, it does not hide already-sent markup with CSS/JS |

## Standard Stack

No new library, framework, or package is introduced by this phase. Every decision is implemented with:
- Python 3 stdlib only: `contextvars` (i18n's per-request language, D-04's own Discretion note names this as the expected shape), `urllib.request`/`http.client` (the ntfy POST, D-25 — the codebase already makes outbound HTTPS calls this way in `server/plane/calendar_rules.fetch_ics()`, so the same primitive is the natural fit, not `requests`), `json`, `hashlib`, `time` — matching this codebase's existing, explicit stdlib-only discipline.
- Pillow (already a dependency, via `server/plane/render.py`'s `build_canvas()`) for the live theme-preview render — no new imaging call, the existing `theme_preview.preview_png_bytes()` pipeline is reused with a different flight/route argument.
- The project's existing hand-rolled ES5-safe vanilla-JS idiom for the two genuinely new/extended static scripts (`theme-preview.js`, and a small addition to `rule-form.js`/the existing rule-add markup for D-15b's placeholder-swap).

**Package Legitimacy Audit:** Not applicable — this phase installs zero external packages in any ecosystem. The Package Legitimacy Gate is skipped per its own "no external packages" exemption.

**Version verification:** Not applicable (no packages).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Outbound HTTPS POST to the ntfy topic | A hand-rolled socket/TLS client | `urllib.request.Request`/`urlopen` with a 5s `timeout=` (D-27's own number) | `calendar_rules.default_calendar_transport()`/`fetch_ics()` already establish this exact stdlib pattern for outbound HTTPS in this codebase, including the SSRF-safety gate shape (`_url_is_safe()`) — reuse the pattern, do not invent a second HTTP client shape |
| Per-request language state | A global mutable variable, or threading `lang` through every function signature | `contextvars.ContextVar` (or a `threading.local()` if the planner prefers — `ThreadingHTTPServer` is one thread per request so either is correct) | D-04's own Discretion note names this; it is also the only shape that cannot leak one request's language into a concurrently-handled second request under `ThreadingHTTPServer` |
| Translation catalogue lookup | A templating engine, `gettext`/`.po` files, a JSON i18n bundle loader | A plain `dict` keyed by the exact English string, in `companion/i18n_fr.py` | D-04 locks this shape explicitly; `gettext` would be the standard tool in a non-constrained project, but this codebase is deliberately stdlib-minimal and already has a "one Python dict registry" idiom for every other lookup table (`THEMES`, `RUNWAYS`, `RULE_KIND_LABELS`) |
| Live theme-preview cache invalidation | A TTL-based or LRU cache | A signature folded into the filename, exactly like `theme_preview.preview_signature()` already does for the static previews (theme registry + palette + crop box + version) — extended with the runway event's own row id | The existing scheme already solves "how do we know a cached file is stale" for the static 16(now 18)-theme grid; a live preview differs only in adding one more input (the event id) to the same signature, not in needing a different cache strategy |
| Simple-mode gating logic | A second copy of `NAV_GROUPS`/page-render logic, or a client-side CSS `display:none` | A single `ctx["simple_mode"]` boolean, read at each of D-30's five named render sites, following the exact pattern `ctx["edit_mode"]` already established for airlines_page's edit-only forms (a presentation-only flag, never consulted by a POST handler) | D-30's own text: "a presentation choice, not an access control" — the `edit_mode` precedent is the identical shape, already proven safe in this codebase |

**Key insight:** every mechanism this phase needs already has a close, working precedent somewhere in this codebase — the work is almost entirely "apply the established pattern to a new surface," not "invent a new pattern." The one place that temptation must be resisted hardest is the D-19 instant-switch placement (Pitfall 1 below), where the *visually* simplest-looking markup change is actually invalid HTML.

## Package Legitimacy Audit

Not applicable — zero external packages are installed by this phase in any ecosystem (confirmed: no new `pip install` target anywhere in the six decision areas; `urllib.request` and `contextvars` are stdlib).

## Architecture Patterns

### System Architecture Diagram

```
Browser (FR/EN cookie, theme cookie, simple-mode cookie)
   |
   |  GET/POST (Cookie: sp_ui_lang, sp_ui_theme, sp_ui_mode, session)
   v
companion/app.py  Handler.do_GET/do_POST
   |
   |-- page_context() ---------------------------> ctx["lang"], ctx["simple_mode"], ctx["ui_theme"], ...
   |                                                  (read once per request from cookies/Accept-Language)
   |
   |-- dispatch to companion/pages/*.py render(ctx) / handle_post(form, ctx)
   |        |
   |        |-- every user-visible string wrapped in companion.i18n.t(text)
   |        |     -> reads ContextVar set by page_context(), looks up companion/i18n_fr.py dict
   |        |     -> falls back to the English literal on any miss
   |        |
   |        |-- companion/layout.py: page_shell() writes <html lang="fr|en">,
   |        |     status_row() (new), local_clock_text()/relative_age_text() (now lang-aware)
   |        |
   |        |-- companion/theme_preview.py: cached_preview_bytes(theme_id, live_event=...)
   |        |     -> server/history_db.py: latest runway event
   |        |     -> server/plane/render.py: build_canvas() (existing Pillow pipeline)
   |        |     -> theme_previews/ cache dir, keyed by (theme, palette, crop, version, event_id)
   |        |
   |        |-- companion/static/*.js: dumb DOM attachment, reads data-* attributes
   |              (already-translated text baked in server-side; copy-button.js/dirty-state.js
   |               gain one new data-* each for D-06's two real JS-literal gaps)
   |
   v
server/device_config.py (device_config.json: + notifications{topic_url, battery_low, frame_silent, lang})
server/plane/colour_rules.py, calendar_rules.py (rules/calendar registries, unchanged shape)

---------------------------------------------------------------------------------

server/poll_loop.py  run_once()  <-- independent cron-like process, NO browser, NO companion import
   |
   |-- battery_low_active transition (two call sites, hold-branch + main-branch)
   |-- frame-silent transition: history_db.latest_device_health().ts vs. 3x
   |     server/wake.py (NEW - the arithmetic currently in companion/wake.py, moved
   |     server-side so poll_loop never imports companion/)
   |
   |-- on either transition: server/notify.py (NEW) -> urllib.request POST to the
   |     configured ntfy topic URL, Title header, plain-text body, 5s timeout, 1 attempt
   |
   |-- poll_state.json: + notifications{last_battery_sent, last_silent_sent} sub-dict
```

### Recommended Project Structure (new/changed files only)

```
companion/
├── i18n.py              # NEW - t(text), t_lang(text, lang), ContextVar, set_current_lang()
├── i18n_fr.py           # NEW - the FR catalogue dict, grouped by page with comments
├── app.py               # + /ui-lang, /ui-mode routes; page_context() gains lang/simple_mode
├── layout.py            # + status_row(), lang-aware local_clock_text()/relative_age_text(),
│                         #   nav footer gains the language + simple-mode switches
├── wake.py              # becomes a thin re-export of server/wake.py (existing pinned tests
│                         #   keep importing companion.wake unchanged)
├── theme_preview.py     # + live-event render path, cache key gains event id
├── pages/
│   ├── config_page.py   # Display/Device regroup, calendar/rules UX rebuild, instant switches
│   ├── home_page.py     # hero row + status card + recent-flights rebuild
│   └── airlines_page.py # "Change pictures"/"Done" button (D-36)
└── static/
    ├── theme-preview.js # NEW - swaps the live-preview <img src> on chip selection
    ├── copy-button.js   # + data-copied-text attribute read
    └── dirty-state.js   # + data-dirty-* connector-word attributes read

server/
├── wake.py              # NEW - effective_wake_interval_s()/device_staleness_thresholds()/
│                         #   next_wake_at_iso(), moved from companion/wake.py (stdlib +
│                         #   server.device_config only, so poll_loop.py can import it
│                         #   without ever importing companion/)
├── notify.py            # NEW - send_notification(topic_url, title, body, timeout=5) -> bool
├── device_config.py     # + "notifications" config group (topic_url, battery_low, frame_silent, lang)
└── poll_loop.py         # run_once(): both battery_low_active sites gain a transition-notify
                          #   call; a new frame-silent check; poll_state.json's new sub-dict
```

## Don't Hand-Roll (JS-specific addendum)

The new `theme-preview.js` and any addition to `dirty-state.js`/`copy-button.js` must follow the six-touch-point static-script contract established in `19-PATTERNS.md` ("Duplicated-not-imported static-route contract"): route+path constants in `companion/app.py`, a thin `_serve_*_script()` delegate, one `do_GET()` dispatch line, a matching `*_SCRIPT_SRC` constant in `companion/layout.py`, `page_shell()`'s script-tag list/tuple growing by one, and a cross-file "route equals src" test in `companion/test_companion_app.py`. Do not attempt to import a shared constant between `app.py` and `layout.py` — that cross-import is a deliberate, already-tested design choice in this codebase (an import cycle would result).

## Common Pitfalls

### Pitfall 1 (CRITICAL): D-19's instant switch cannot be nested inside `<form id="settings-form">`
**What goes wrong:** `companion/pages/config_page.py`'s `render()` returns `header + '<form ...>' + hidden_html + groups_html + '<button ...>Save settings</button>' + '</form>' + calendar_disconnect_html + rules_section_html + poll_section_html + dirty_bar_html` (verified, `config_page.py:2348-2369`). `groups_html` is the concatenation of every group builder in `scope_groups()`'s order, and `quiet_hours_group()` (`config_page.py:1221-1356`) and `display_group()` (`config_page.py:1451-1513`) are both builders in that dict — their entire returned markup is therefore a **descendant** of the `<form>` tag. HTML5 forbids a `<form>` element as a descendant of another `<form>` element; browsers silently break out the inner form to the top level on parse, producing structurally broken, unpredictable markup, not a rendering error you would notice by eye.
**Why it happens:** D-19's own text ("They are their own forms (D-13)") is correct about *what* is needed, but reads as if the mini-form can simply be prepended to the existing group's markup in place — which it cannot, because that markup's parent is already a `<form>`.
**How to avoid:** Reuse the exact precedent this codebase already shipped for the identical structural problem: `form="{SETTINGS_FORM_ID}"` on the dirty-bar's Save button (`config_page.py:2242`, quick task 260901-re6's own documented reasoning) — a form-associated element outside the `<form>` tag that still submits into it via the `form=` attribute. Concretely: split `quiet_hours_group()`/`display_group()` so their outer card wrapper (`<div class="theme-status">`, heading, caption) is emitted as a **sibling** of `<form id="settings-form">` — in the same slot `calendar_disconnect_section()`/`_rules_section_html()` already occupy, immediately after `</form>` closes — while every `<input>`/`<select>` inside that wrapper keeps a `form="settings-form"` attribute so it still submits with the batched Save. The new quick-action mini-`<form>` (posting to `/quick/display`/`/quick/quiet-hours`) renders as a true, separate `<form>` at the top of that same non-form wrapper. This is a real restructuring of two of the seven group builders and of `render()`'s own assembly order — flag it explicitly in the plan, do not let it be discovered mid-implementation.
**Warning signs:** Any plan task that describes inserting a `<form>` "inside" `quiet_hours_group()`'s or `display_group()`'s existing returned string without first moving that string outside `<form id="settings-form">` — this is the signal the conflict was not resolved.

### Pitfall 2 (CRITICAL): D-14c's calendar-connect mini-form must not reuse the generic scoped `/settings` handler once Calendar joins Display's scope
**What goes wrong:** `submitted_calendar_signal(form)` already gates on `screens.GROUP_CALENDAR in scope_groups(submitted_scope(form))` (`config_page.py:2606`) — so a minimal connect-only POST would need `scope=display` once D-11 moves `GROUP_CALENDAR` into `everyday_groups`. But `handle_post()`'s absent-checkbox semantics are keyed on the SAME `in_scope` set: `if screens.GROUP_QUIET_HOURS not in in_scope: quiet_hours_enabled = None; elif submitted_qh_enabled is None: quiet_hours_enabled = False` (`config_page.py:2913-2921`, same shape for `GROUP_DISPLAY`/`GROUP_LED`). Once Calendar, Quiet hours, Screen and Runway all share `scope=display`, a bare `calendar_url`-only POST with `scope=display` would submit `quiet_hours_enabled`/`display_enabled` as **absent**, and absent-when-in-scope means "explicitly OFF" — the calendar-connect mini-form would silently switch off Quiet hours and the screen.
**Why it happens:** D-14c's own text ("the existing save path for the URL, called with the URL only") describes the *low-level functions* to reuse (`calendar_rules.save_calendar_url()` + `refresh_calendar_registry()`, the same two `_handle_settings_post()` already calls at `app.py:2381-2402`), not literally "the existing `/settings` route with a minimal body" — but the two read as the same thing at a glance.
**How to avoid:** Give the calendar-connect mini-form its own dedicated route (e.g. `POST /settings/calendar/connect`), mirroring `calendar_disconnect_section()`'s/`_handle_calendar_disconnect_post()`'s own already-shipped precedent (`app.py:1986+`, `config_page.py:1690-1737`) — call `calendar_rules.save_calendar_url(state_dir, url)` then, on success, `calendar_rules.refresh_calendar_registry(state_dir, poll_loop.now_s(), min_interval_s=0)` under `_POLL_LOCK`, exactly like `_handle_settings_post()`'s own calendar-signal branch (`app.py:2390-2403`) — but never touching `handle_post()`'s scope/in_scope machinery at all.
**Warning signs:** Any plan task wiring the calendar "Connect" form's `action` to `SETTINGS_ROUTE` (`/settings`) rather than a new dedicated path.

### Pitfall 3: Home's duplicated verdict has one exact, confirmed cause — fix the right function
**What goes wrong:** `home_page._status_tiles_html()` (`home_page.py:173-177`) builds `frame_body` from its OWN `FRAME_STATE_TEXT[device_state]` dict, then appends `health["device_html"]` as a second `<p class="text-label widget-detail">` paragraph. `health["device_html"]` is produced by `health_page._device_section()` (`health_page.py:1718-1721`), which ALREADY prepends its own verdict paragraph from `DEVICE_STATE_TEXT` — and `DEVICE_STATE_TEXT`'s three values (`health_page.py:247-251`) are byte-identical strings to `FRAME_STATE_TEXT`'s (`home_page.py:99-103`): `"Checking in normally"` / `"Has not checked in for a while"` / `"Has not checked in for a long time"`. Home therefore always renders the identical sentence twice, once from each dict.
**Why it happens:** `device_html` was designed as a complete, self-contained Health-page tile fragment (verdict + timestamp); reusing it wholesale inside Home's OWN verdict-plus-detail tile shape double-renders the verdict half.
**How to avoid:** Add a detail-only variant to `health_page.py` (e.g. `_device_timestamp_only(device_health, now)`, returning just the `<p class="stat-tile__value">` timestamp line without the verdict paragraph) and have `home_page.py` call that instead of embedding the whole `device_html` string. Do NOT fix this by editing `FRAME_STATE_TEXT`'s wording to differ from `DEVICE_STATE_TEXT`'s — that would leave the structural double-render in place while merely hiding it from a byte-for-byte comparison, and the two dicts are legitimately meant to describe the same states identically elsewhere (Health's own tile already uses `DEVICE_STATE_TEXT` correctly, once).
**Warning signs:** A diff that only touches string constants in either dict, with no change to which HTML fragment `home_page.py` interpolates.

### Pitfall 4: D-06's JS gap is real but much smaller than it reads
**What goes wrong:** A plan that assumes all five named scripts (`copy-button.js`, `dirty-state.js`, `freshness.js`, `confirm-submit.js`, `poll-cooldown.js`) need a data-attribute externalization pass will spend effort on three files that are already fully compliant.
**Why it happens:** D-06's own text lists all five as if each carries a hardcoded English literal reaching the screen.
**How to avoid:** Direct read of all five confirms: `freshness.js` reads `data-pause-text`/`data-resume-text` off the button (`freshness.js:321-322`, already rendered by `health_page.py:2860`); `confirm-submit.js` reads the whole confirm question from `form.getAttribute("data-confirm")` (`confirm-submit.js:57`, already rendered by `calendar_disconnect_section()`); `poll-cooldown.js` reads its countdown template, token and pending text from `data-cooldown-template`/`data-cooldown-token`/`data-submit-pending` (`poll-cooldown.js:47-73`, already rendered by `config_page.py`'s `poll_trigger_section()`). **These three need zero JS changes** — only their Python callers need to wrap the interpolated text in `t()`. The two real gaps: `copy-button.js`'s `var FEEDBACK_TEXT = "Copied";` (`copy-button.js:35`, a hardcoded JS literal with no attribute at all) and `dirty-state.js`'s connector words `" changed"`, `" and "`, `", and "`, `"1 unsaved change"`, `"N unsaved changes"` built directly into `updateBar()`'s string concatenation (`dirty-state.js:233-249`) — both need a new `data-*` attribute (e.g. `data-copied-text` on the feedback span/button; `data-dirty-and-text`/`data-dirty-changed-suffix`/`data-dirty-unsaved-singular`/`data-dirty-unsaved-plural` on the dirty-bar element) rendered by the Python side, read once by the script.
**Warning signs:** A plan task titled "externalize copy-button.js/dirty-state.js/freshness.js/confirm-submit.js/poll-cooldown.js's literals" treating all five identically — the latter three need no code change, only their Python caller does.

### Pitfall 5: D-08's completeness harness needs a mechanical enumeration strategy, not a hand-kept list
**What goes wrong:** "Enumerates the page modules' user-visible constants" is easy to state and easy to implement wrong (a hand-maintained list drifts the moment a new string constant is added and nobody remembers to add it to the list).
**Why it happens:** There is no existing precedent in this codebase for "walk every module-level string constant automatically" — every other registry (`THEMES`, `RUNWAYS`, `RULE_KIND_LABELS`) is a small, deliberately-enumerated dict, not a scan target.
**How to avoid:** The mechanical, drift-proof approach is an AST scan (stdlib `ast` module) over each page module's source: walk top-level `Assign` nodes whose target is an ALL_CAPS name and whose value is a string literal (or a `%`-templated string literal — the D-04 catalogue key format), collecting the literal value. This mirrors the codebase's own convention of ALL_CAPS module constants for every user-visible string (`FRAME_STATE_TEXT`, `RULES_EMPTY_HEADING`, `CALENDAR_SECTION_HEADING`, etc. — confirmed: every string this research read is exactly this shape) and needs no per-string opt-in annotation. The harness then: (a) renders every named page (Home, Display, Device, Flights, Airlines, Health, login, 404, disconnect-confirm) in French against seeded state and asserts none of the scanned English literals appear verbatim in the response body (a miss falls back to English per D-04, so a truly-missing translation is invisible in the rendered HTML unless checked against the SOURCE catalogue directly — the more precise check is: for every scanned literal, assert it is a KEY in `companion/i18n_fr.py`'s dict, not merely absent from the rendered French page, since some English words are legitimately identical in French); (b) a second check asserts every KEY in `i18n_fr.py` was scanned from at least one page module (the "dead translation" check). Exclude non-page-module constants deliberately (route strings, CSS class names, flash keys) by scanning only `companion/pages/*.py` plus `companion/layout.py`'s nav-label/status-text dicts plus `companion/auth.py`'s error strings — the same module set D-05 names as in scope.
**Warning signs:** A completeness check that string-searches the rendered French page body for the ABSENCE of English text, rather than checking the catalogue's own key set — the former both false-passes on any English word that is also valid French (e.g. proper nouns, "OK") and false-fails on legitimate identifiers that must NOT be translated (ICAO codes, theme ids).

### Pitfall 6: the notifications config group's `lang` default (D-28) needs a save-time snapshot, not a live read
**What goes wrong:** "default from the last language used in the companion at save time" sounds like it wants the CURRENT request's language read at every render — but the poll loop has no request at all, so this value must be a **persisted** field the companion writes once, at Device-page save time, from `ctx["lang"]`.
**Why it happens:** Every other Device-page field in `handle_post()` is re-derived from the current submission on every save; `notifications.lang` is the one field whose value should come from the SESSION's resolved language, not from a form field the user explicitly set.
**How to avoid:** When `_handle_settings_post()` (or a new dedicated notifications-save handler, if D-26's "Send a test" button gets its own route) writes the `notifications` group, pass `ctx["lang"]` as the `lang` value — never a submitted form field for this one sub-key. `server/poll_loop.py`'s notification sender then reads this persisted value from `device_config.json`'s `notifications.lang`, defaulting to `"en"` for any device_config predating this phase (matching every other additive-default precedent in `load_device_config()`).
**Warning signs:** A `<select name="notifications_lang">` control on the Device page — D-26's own field list (topic URL, two checkboxes, "Send a test" button) does not include a language selector; the value is meant to travel silently.

### Pitfall 7: the live theme-preview cache key must include the event id, or every chip-selection swap serves a stale render forever
**What goes wrong:** `theme_preview.cache_path()` today builds its filename from `"%s-%s.png" % (theme_id, preview_signature(theme_id))` (`theme_preview.py:203`) — `preview_signature()` folds in the theme registry, palette, crop box and a manual version bump, but nothing about WHICH flight is rendered. A live variant that reuses this exact filename scheme with no additional discriminator would cache the very first live render forever, never picking up a newer runway event.
**Why it happens:** The existing scheme was deliberately designed around a FIXED, never-changing fictional scene (D-06 of the theme-preview mechanism's own docstring: "must never be wired to live flight data") — extending it to a live scene needs one more axis the original design explicitly excluded.
**How to avoid:** Fold the runway event's own row id (or its `ts`, whichever `history_db.recent_runway_events()` exposes as a stable identifier — confirmed: `SELECT * FROM runway_events ORDER BY ts DESC, id DESC`, so the autoincrement `id` column is the natural, stable discriminator) into both the cache filename and `preview_signature()`'s digest input, e.g. `"%s-%s-%s.png" % (theme_id, event_id or "sample", preview_signature(theme_id))`. A missing/no-event state (fresh install, nothing on the watched runway yet) falls back to the existing fixed-scene render — same function, `live_event=None` degrades to today's behaviour byte-for-byte, satisfying D-23's own "falling back to today's sample flight" clause.
**Warning signs:** A `?live=1` route that reads `history_db.recent_runway_events(conn, limit=1)` fresh on every request without ever appending anything derived from that row's identity to the cache key — this "works" visually on first load and silently stops updating on every subsequent real flight.

## Code Examples

### Pitfall 1's resolution: `form=` attribute keeps a sibling control submitting into the merged form
```python
# companion/pages/config_page.py — the EXISTING precedent (quick task 260901-re6)
dirty_bar_html = (
    '<div class="dirty-bar" data-dirty-bar hidden role="status">'
    "<span data-dirty-count>%s</span>"
    '<button type="submit" class="dirty-bar__save" form="%s">Save settings</button>'
    '<button type="button" class="dirty-bar__cancel" data-dirty-cancel>Cancel</button>'
    "</div>"
) % (escape_html(DIRTY_BAR_INITIAL_TEXT), SETTINGS_FORM_ID)
```
Source: `companion/pages/config_page.py:2239-2245`. Apply the identical `form="%s" % SETTINGS_FORM_ID` attribute to `quiet_hours_group()`'s checkbox/time inputs and `display_group()`'s checkbox once their outer wrapper is moved outside `<form id="settings-form">`.

### Pitfall 2's resolution: the calendar-disconnect route is the template for calendar-connect
```python
# companion/app.py:1986+ (_handle_calendar_disconnect_post, the shape to mirror for connect)
def _handle_calendar_disconnect_post(self):
    ...
    if calendar_rules.save_calendar_url(
            state_dir, calendar_rules.CLEAR_CALENDAR_URL):
        return self.redirect("%s?flash=%s" % (back, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
    ...
```
A new `_handle_calendar_connect_post()` follows the same shape, but on success additionally calls `calendar_rules.refresh_calendar_registry(state_dir, poll_loop.now_s(), min_interval_s=0)` under `_POLL_LOCK`, exactly like `_handle_settings_post()`'s own `CALENDAR_URL_SIGNAL_SET` branch (`app.py:2390-2403`) — never routing through `config_page.handle_post()`'s scope/in_scope machinery.

### Pitfall 3's resolution: split verdict from detail in `health_page.py`
```python
# companion/pages/health_page.py — current _device_section() (health_page.py:1718-1721)
verdict = '<p class="text-body widget-verdict">%s</p>' % escape_html(
    DEVICE_STATE_TEXT.get(state, DEVICE_STATE_TEXT["warn"]))
detail = layout.concise_timestamp_html(ts, now)
row = verdict + '<p class="stat-tile__value">%s</p>' % detail
return row, state
```
Add a sibling that returns `detail` alone (or thread a `detail_only=False` kwarg through `_device_section()`), and have `home_page._status_tiles_html()` call that instead of interpolating the full `device_html` a second time alongside its own `FRAME_STATE_TEXT` verdict.

### Pitfall 7's resolution: fold the event id into the cache key
```python
# companion/theme_preview.py — cache_path() today (theme_preview.py:188-204)
def cache_path(state_dir, theme_id):
    if not state_dir or theme_id not in device_config.THEMES:
        return None
    directory = cache_dir(state_dir)
    filename = "%s-%s.png" % (theme_id, preview_signature(theme_id))
    return os.path.join(directory, filename)
```
Extend both `cache_path()`/`cached_preview_bytes()` and `preview_signature()` with an optional `live_event=None` parameter (a small dict/row: `{"id": ..., "hex": ..., "callsign": ..., "airline": ..., "origin": ..., "destination": ..., "confirmed_state": ...}` or `None`), append `live_event["id"]` (or a fixed sentinel like `"sample"`) to both the filename and the signature's digest input, and — when `live_event` is not `None` — call `render.build_canvas(flight, state, route=route, theme_id=theme_id)` with `previous_flight=None, previous_route=None` (both are optional per `build_canvas()`'s own signature, `server/plane/render.py:2436-2440`) instead of the fixed `THEME_PREVIEW_FLIGHT`/`THEME_PREVIEW_ROUTE` fixtures.

### D-06's real gap: adding one `data-*` attribute to `copy-button.js`
```javascript
// companion/static/copy-button.js:35 (current)
var FEEDBACK_TEXT = "Copied";
```
```javascript
// after: read from the button/feedback span instead of a JS literal,
// matching freshness.js's own data-pause-text/data-resume-text idiom
var feedbackText = button.getAttribute("data-copied-text") || "Copied";
```
`companion/pages/history_page.py`'s `_copy_button_html()` gains a `data-copied-text="%s"` attribute rendered through `t("Copied")`, mirroring `health_page.py:2860`'s existing `data-pause-text`/`data-resume-text` pattern exactly.

## Runtime State Inventory

Not applicable — this phase is not a rename/refactor/migration. Confirmed: no decision renames an on-disk key, a database column, an env var, or a secrets-file key. Two additive-only schema changes: `device_config.json` gains a `notifications` sub-dict (D-26, degrades to a documented default for any file predating this phase, following the exact pattern `screen_id`'s own additive rollout used in phase 19); `poll_state.json` gains a `notifications` sub-dict (D-27, same additive-default pattern `load_poll_state()`'s own "missing key -> default" convention already uses throughout the file). Neither needs a migration script.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python stdlib `contextvars` | D-04 (per-request language) | Yes | bundled since 3.7, this project targets 3.12 | `threading.local()` (also stdlib, CONTEXT.md's own Discretion note accepts either) |
| Python stdlib `urllib.request` | D-25/D-27 (ntfy POST) | Yes | bundled | already used by `calendar_rules.default_calendar_transport()` for outbound HTTPS |
| An actual reachable ntfy topic URL (e.g. `ntfy.sh` or a self-hosted instance) | D-26's "Send a test" button, D-27's real delivery | Not verifiable from this environment (outbound network call to a third-party or self-hosted service, operator-supplied at runtime) | n/a | None needed for automated tests — the harness must inject a stub transport (mirroring `calendar_rules.fetch_ics(transport=...)`'s own test-injection seam) rather than hitting a real endpoint |

**Missing dependencies with no fallback:** none — every dependency above either exists in this environment or is test-doubled by an injected transport, following an existing precedent in this exact codebase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib-only, hand-rolled `check(name, fn)` harness convention — no pytest, no unittest runner |
| Config file | none — `scripts/run-all-tests.sh` -> `scripts/run_all_tests.py` is the canonical list |
| Quick run command | `PYTHON=/home/user/skypane/server/.venv/bin/python server/.venv/bin/python3 <file>.py` (each file is directly executable and self-reports `N/M checks pass`) |
| Full suite command | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |

**Current authoritative baseline (verified live, 2026-09-11):**

| Harness | Current pass/total | Notes |
|---|---|---|
| `companion/test_companion_app.py` | 219/221 | 2 pre-existing root-sandbox failures — do not "fix" |
| `companion/test_config_page.py` | 181/181 | clean |
| `companion/test_status_pages.py` | 190/191 | 1 pre-existing root-sandbox failure — do not "fix" |
| `companion/test_view_pages.py` | 85/85 | clean |
| `companion/test_contrast_check.py` | 36/36 | clean |
| `server/test_config_history.py` | 64/64 | clean |
| `server/test_runway_config.py` | 15/15 | clean |
| `server/test_poll_loop.py` | 81/81 | clean |
| `server/test_manual_resolutions.py` | fails in this sandbox (root-owned read-only dir case, ~2 checks) | pre-existing, do not "fix" |

Full-suite run confirms exactly 3 failing harnesses (`test_manual_resolutions.py`, `test_companion_app.py`, `test_status_pages.py`) totalling the documented "five checks fail in this root sandbox" — matches the prompt's own count.

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-13 | FR/EN switch changes every string; completeness harness passes | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` (new i18n suite likely its own file, e.g. `companion/test_i18n.py`) | New file needed |
| CFG-14 | Home hero row, one status card, no duplicated verdict, no quick actions | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_view_pages.py` (Home currently has no dedicated harness file — confirm during planning which file owns Home's checks; likely folded into `test_view_pages.py` or a new `test_home_page.py`) | Partially — confirm ownership |
| CFG-15 | Display carries all six groups; Calendar/Flight-colours redesigned | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py` | Yes |
| CFG-16 | Live preview follows selection, cached per (theme, event) | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py` or `companion/test_companion_app.py` (theme-preview route tests) | Yes |
| CFG-17 | Battery-low/frame-silent transitions each produce exactly one push | unit (injected transport) | `server/.venv/bin/python3 server/test_poll_loop.py` | Yes (extend) |
| CFG-18 | Simple mode hides Advanced group + named affordances, survives navigation | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` | Yes (extend) |

### Sampling Rate
- **Per task commit:** the single most relevant harness for the file(s) touched (e.g. touching `home_page.py` -> run whichever file owns Home's checks; touching `server/poll_loop.py` -> `server/test_poll_loop.py`)
- **Per wave merge:** `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` (full suite)
- **Phase gate:** full suite green (excluding the 3 pre-existing, documented root-sandbox harness failures / 5 checks) before `/gsd:verify-work`, plus `ruff check .` clean, plus the headless 1280/390px sweep (D-18) with no CSP violation

### Wave 0 Gaps
- [ ] `companion/i18n.py` + `companion/i18n_fr.py` (new files) — no test exists yet; needs `t()`/`t_lang()` round-trip checks, the missing-key-falls-back-to-English check, and the two D-08 completeness checks (AST-scanned constants all present as keys; no dead catalogue entries).
- [ ] `server/wake.py` (new file, moved from `companion/wake.py`) — every existing pinned test importing `companion.wake.effective_wake_interval_s`/`device_staleness_thresholds`/`next_wake_at_iso` must keep passing unmodified against the thin re-export; add the module's own test file at its new home if the planner decides `companion/wake.py`'s existing tests should move too, or keep them where they are if `companion/wake.py` stays a re-export shim (Discretion, but must be decided explicitly).
- [ ] `server/notify.py` (new file) — needs its own test file with an injected transport (never hitting a real ntfy endpoint), covering: successful POST, timeout, non-2xx response, malformed topic URL — all degrading to "logged, never raises" per D-27.
- [ ] `server/poll_loop.py`'s frame-silent check — no test exists today for "device check-in older than 3x effective wake interval triggers a notification exactly once, and clears exactly once." Add alongside the existing `battery_low_active` transition tests.
- [ ] `companion/static/theme-preview.js` (new file) — needs the standard three-check pattern every static script gets (public route, ES5-safe/no-HTML-write, route/src agreement).
- [ ] Home page's own test ownership — confirm during planning whether Home's checks live in `test_view_pages.py`, a new `test_home_page.py`, or elsewhere; the redesign (D-16..D-21) touches enough of Home's markup that this should be settled before Wave 1, not discovered mid-task.

## Security Domain

### Applicable ASVS Categories (Level 1, block on high — per `.planning/config.json`)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes (unchanged) | Existing HMAC session tokens; the new `/ui-lang`/`/ui-mode` routes must be gated by `require_session()`, mirroring `/ui-theme`'s own D-18-era gating (phase 19) — never left open like the pre-phase-19 `/ui-theme` was |
| V4 Access Control | Yes | The new calendar-connect route (Pitfall 2's resolution), the notifications "Send a test" route, and the rule-add-via-segmented-control route all need `require_session()` — same discipline every existing state-changing POST route in `do_POST()` already has |
| V5 Input Validation | Yes | The notifications topic URL needs the SAME SSRF-safety gate `calendar_rules._url_is_safe()`/`_address_is_public()`/`_host_is_safe()` already implement for the calendar feed URL (`calendar_rules.py:1526-1656`) — an ntfy topic is just as capable of being pointed at an internal address as a calendar feed is, and this codebase already has the exact private-IP/DNS-rebinding-safe primitive to reuse, not re-derive |
| V12 File and Resources | Yes | `notify.py`'s outbound POST must carry the same 5s `timeout=`/1-attempt/never-raise discipline `calendar_rules.fetch_ics()` already establishes (D-27's own text: "5 s timeout, one attempt") |
| V14 Configuration | Yes | The `/ui-lang`/`/ui-mode` cookies must mirror `auth.UI_THEME_COOKIE_NAME`'s exact flags (`HttpOnly`, `SameSite=Strict`, the same `Secure`-flag opt-out via `auth.secure_cookie_flag()`) — do not invent a second cookie-flag scheme |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via the notifications topic URL (an operator-controlled URL the server itself POSTs to on a schedule, from `server/poll_loop.py` — a process with no browser and no user to notice a hung/redirected request) | Tampering / Elevation of Privilege | Reuse `calendar_rules._url_is_safe()` (validates scheme, resolves the hostname, rejects private/loopback/link-local ranges) verbatim before ever calling `urllib.request` — do NOT skip this because "it's just a notification," the request still originates from the trusted server process and can be pointed at internal infrastructure exactly like the calendar-URL SSRF vector already mitigated |
| Un-gated new state-changing routes (`/ui-lang`, `/ui-mode`, calendar-connect, notifications-test, rule-add-via-segmented-control) | Elevation of Privilege | Every one gated by `require_session()` at its `do_POST()` dispatch line, matching the existing gate-then-dispatch shape for every sibling route (`app.py:2499-2526`'s own pattern) |
| The masked/write-only display convention drifting for the new notifications topic URL | Information Disclosure | D-26 says "shown masked like the calendar URL" — but the calendar URL is actually NEVER rendered at all (write-only: `calendar_group()`'s own docstring, `config_page.py:1563-1575`, "the field always renders with no value attribute... nothing derived from the stored URL"), not masked-with-partial-characters. Follow the calendar URL's real behaviour (write-only, empty on every load) rather than inventing a masking scheme (e.g. `ntfy***xyz`) that does not exist anywhere else in this codebase — flagged as an Assumption below since the CONTEXT text's "masked" wording does not match the actual precedent it points to |
| CSRF on the new dedicated calendar-connect/notifications-test routes | Tampering | Inherits the site-wide posture already accepted for every other state-changing route (SameSite=Strict, single-operator tool, no CSRF token) — consistent with phase 19's own resolution of the identical question for calendar-disconnect |
| Reflected/stored XSS via a translated string that happens to contain user-influenced data (e.g. the notification body's battery mV/percentage, a flight callsign in a "Recent:" chip) | Tampering | Unchanged site-wide discipline: every dynamic value routes through `escape_html()` with zero exceptions, INCLUDING the output of `t()` — `t()` returns plain text, never markup, so callers must escape its return value exactly as they escape any other string today; do not special-case translated strings as "already safe" |

## Decision Implementation Map

### A. Bilingual companion (D-01..D-09)

| Decision | Lands in | Existing pinned check(s) to retarget/add |
|---|---|---|
| D-01/D-04 `i18n.py`/`i18n_fr.py` | NEW `companion/i18n.py` (stdlib `contextvars.ContextVar`, `t(text)`, `t_lang(text, lang)`, `set_current_lang(lang)`), NEW `companion/i18n_fr.py` (plain dict) | New file, new tests — no existing check references either module today |
| D-02/D-03 language cookie + `Accept-Language` default | `companion/auth.py`: a new `UI_LANG_COOKIE_NAME` constant beside `UI_THEME_COOKIE_NAME` (`auth.py:58`); `companion/app.py`: new `LANG_ROUTE = "/ui-lang"` beside `THEME_ROUTE` (`app.py:203`), a `_handle_lang_post()` mirroring `_handle_theme_post()` exactly (`app.py:2479-2490`), gated in `do_POST()` the same way (`app.py:2523-2526`); `page_context()` resolves `ctx["lang"]` from the cookie, falling back to `Accept-Language` parsing (a new small helper, e.g. `_lang_from_accept_header(header)`, checking for an `fr` prefix before any other entry) when no cookie is set | `companion/test_companion_app.py`'s existing theme-cookie-round-trip tests (~line 764-771, 2483-2490 area) are the template to copy for the language cookie; no existing check to retarget, several new ones to add |
| D-03 `<html lang="...">` | `companion/layout.py`: `page_shell()`/`login_shell()` (`layout.py:1003-1022`, `940-966`) — the hardcoded `'<html lang="en" data-ui-theme="%s">'` (`layout.py:969`, `login_shell()`) becomes `'<html lang="%s" data-ui-theme="%s">'` reading `ctx["lang"]`/a new `lang=` parameter | Any existing check asserting the literal string `lang="en"` in a full-page render must retarget to assert the resolved language instead |
| D-05 every string through `t()` | Every `companion/pages/*.py` module's ALL_CAPS string constants, `companion/layout.py`'s nav labels (`NAV_GROUPS`, `layout.py:54-65`) and status-text dicts, `companion/auth.py`'s login-error strings | This is the highest-touch-count decision in the phase — every existing pinned check asserting an exact English literal (there are dozens across `test_config_page.py`/`test_status_pages.py`/`test_view_pages.py`) must be re-verified to still find that literal for an EN-language request (the default in every existing test call, since no test sets the lang cookie) — `t()` wrapping a constant at RENDER time (not mutating the constant itself, per D-04's own instruction) means every existing test that constructs its expected string from the SAME module constant (the codebase's own established "self-verifying" pattern, e.g. `test_view_pages.py`'s runway-label check deriving its expectation from `device_config.runway_label()` live rather than a hardcoded literal) keeps passing unmodified; only a test that hardcodes the literal text a second time, independently of the constant, is at risk |
| D-06 JS strings from the server | `companion/static/copy-button.js:35`, `companion/static/dirty-state.js:233-249` (see Pitfall 4 above for the full breakdown — `freshness.js`/`confirm-submit.js`/`poll-cooldown.js` need NO JS change) | New `data-copied-text` attribute on `history_page.py`'s `_copy_button_html()`; new `data-dirty-*` connector attributes on `config_page.py`'s dirty-bar markup (`config_page.py:2239-2245`) |
| D-07 lang-aware dates/numbers | `companion/layout.py`: `local_clock_text()` (`layout.py:651-670`), `relative_age_text()` (`layout.py:565-578`), `_MONTH_ABBR` (`layout.py:31-32`) | Every existing check asserting English relative-age text ("Xs ago"/"Xm ago"/etc.) or an English month abbreviation must be confirmed to run under the default (English) language — same self-verifying caveat as D-05 above; a NEW French-language check suite is needed for the FR-specific text ("il y a X", "à l'instant", "sept.") |
| D-08 completeness harness | NEW test file (e.g. `companion/test_i18n.py`) using the AST-scan approach (Pitfall 5 above) | New file, no retargeting |
| D-09 French copy quality | `companion/i18n_fr.py`'s own dict values — a manual-review concern, not a mechanical check, though the completeness harness's key-coverage check (D-08) does verify presence |

### B. Display page regrouped (D-10..D-15e)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-10 Runway to everyday | `companion/screens.py`: `SCREEN_TYPES[DEFAULT_SCREEN_ID]["everyday_groups"]`/`["advanced_groups"]` (`screens.py:50-52`) — move `GROUP_RUNWAY` from the second tuple to the first; the module-level `EVERYDAY_GROUPS`/`ADVANCED_GROUPS` constants (`screens.py:38-39`) are confirmed UNUSED anywhere in production code (grep-verified) — update them too for documentation honesty, but they gate nothing | No test references `screens.EVERYDAY_GROUPS`/`ADVANCED_GROUPS` by name (grep-confirmed) — only `scope_groups()`'s own behaviour (which reads the PER-SCREEN-TYPE `everyday_groups`/`advanced_groups` dict keys) is exercised by tests, e.g. `test_config_page.py`'s scope-rendering checks |
| D-11 Calendar + rules to Display | `companion/screens.py`: move `GROUP_CALENDAR` into `everyday_groups`; `companion/pages/config_page.py`: `render()`'s `show_rules`/`show_calendar_disconnect` flags (currently set ONLY in the `elif scope == SCOPE_DEVICE:` branch, `config_page.py:2313-2319`) move to the `if scope == SCOPE_DISPLAY:` branch instead; `calendar_disconnect_section()`'s `return_to` (via `_scope_fields_html(scope, layout.DISPLAY_ROUTE)`, currently `layout.DEVICE_ROUTE` at `config_page.py:2312`) becomes `layout.DISPLAY_ROUTE` | `test_config_page.py`'s Device-page checks asserting Calendar/rules render there must retarget to assert they render on Display instead; any check asserting Device's `show_rules`/`show_calendar_disconnect` are `False` on Display must invert |
| D-12 three headed sections | `companion/pages/config_page.py`: `render()`'s Display-scope assembly needs three new wrapping `<div class="page-section">` headers ("Look"/"What it watches"/"When it is on") around the existing group builders' output, in the new order (Theme, Flight colours, Calendar / Runway / Screen, Quiet hours) | New checks needed for the section headings' presence/order; every EXISTING check asserting Display's group render ORDER (theme before runway before quiet-hours, etc., following `scope_groups()`'s tuple order) must be re-verified against the NEW order this decision locks |
| D-13 one form stays one form | See Pitfall 1 above — `scope_groups()` itself needs no signature change, but `render()`'s assembly of `quiet_hours_group()`/`display_group()` output relative to `<form>` does | Every pinned check asserting these two groups' markup is a descendant of `<form id="settings-form">` (if any exist — likely implicit via a DOM-parse-based assertion rather than a named check) needs re-verification against the new sibling-wrapper structure |
| D-14a/b caption + status-row + disclosure | `companion/pages/config_page.py`: `calendar_group()` (`config_page.py:1515-1687`) — the two-sentence disclaimer moves into a NEW `<details>` element; the `status_html` three/four-branch logic (`calendar_group.py:1608-1624`) gets rebuilt on `layout.status_row()` (new, D-21) instead of a bare `<p class="calendar-status">` | `test_config_page.py`'s calendar-status-text checks (asserting `CALENDAR_STATUS_*` constants render inside `<p class="calendar-status">`) retarget to assert the new `status_row()` markup shape |
| D-14c Connect as its own immediate form | See Pitfall 2 above — a NEW dedicated route, NOT the existing `/settings` path | New checks needed; existing checks on the write-only `calendar_url` field's empty-value behaviour (`config_page.py:1649-1654`'s own T-16-SECRET contract) must be preserved on whatever new render path this decision adds |
| D-14d chip-based calendar theme | `companion/pages/config_page.py`: `calendar_group()`'s `<select name="calendar_theme_id">` (`config_page.py:1667-1672`) replaced with `_theme_chip_grid_html()` (`config_page.py:754-810`, ALREADY EXISTS as the main Theme group's own chip grid) called with a `"calendar_theme_id"` field name and a new `extra_class="theme-chip--compact"` variant | `test_config_page.py`'s calendar-theme `<select>` checks retarget to assert the chip grid's `role="radiogroup"` shape instead; the "No `<select>` for themes anywhere on Display" acceptance criterion needs its own new check |
| D-15a/b/c/d rename + segmented add form + row list + empty state | `companion/pages/config_page.py`: `RULES_SECTION_HEADING` ("Per-flight colour rules" -> "Flight colours"), `_rule_add_form_html()` (`config_page.py:1894-1956`, the `<select name="rule_kind">` becomes a segmented `role="radiogroup"` using `RULE_KIND_LABELS`' VALUES as the plain-language segment text — confirmed already exactly "Callsign"/"ICAO24 hex"/"Callsign prefix", needing renaming to "Flight"/"Aircraft"/"Airline" with the OLD text moved to a `title=` tooltip per D-15b), `_rules_table_html()`/`_rules_cards_html()`/`_rule_row_html()` (`config_page.py:1972-2060`, table rows -> `.rule-row` list rows, reusing `.theme-chip__swatches`) | `test_config_page.py`'s `<select name="rule_kind">` checks retarget to the segmented-control shape; `_rules_table_html()`'s `<table>`/`<thead>` structural checks retarget to the row-list shape; the heading-text checks ("Per-flight colour rules") retarget to "Flight colours" |
| D-15e recent-flights suggestion chips | NEW logic in `_rule_add_form_html()` or a sibling function, reading `history_db.recent_runway_events(conn, limit=5)` (already the exact function `home_page._recent_flights()` calls) | New checks needed; progressive-enhancement (no-JS renders plain text) needs its own check per the pattern every other JS-enhanced control in this codebase already tests for |

### C. Home redesigned (D-16..D-21)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-16 quick actions leave Home | `companion/pages/home_page.py`: DELETE `_quick_actions_html()`/`_toggle_form_html()`/`QUICK_ACTIONS_HEADING`/etc. (`home_page.py:47-82, 229-311`) and their call site in `render()` (`home_page.py:378`); the extracted markup MOVES to `companion/pages/config_page.py` (see B's D-19 entry / Pitfall 1) | Whatever existing check(s) assert Home's Quick-actions card exists must retarget to assert its ABSENCE; whatever asserts the Refresh button posts from Home must retarget to Device's "Manual refresh" section instead |
| D-17 hero row + recent flights | `companion/pages/home_page.py`: full rebuild of `render()` (`home_page.py:372-382`), `_status_tiles_html()` (rebuilt on `layout.status_row()`, three rows not three tiles — see D-21), `_now_showing_html()` (becomes the hero row's picture half, gains the one-line flight caption), `_recent_flights_html()` (gains the illustration thumbnail via `illustrations.normalise_airline_key(row.get("airline"))`, same resolver `airlines_page.py:657` uses — falsy key means no thumbnail, matching that function's own `if not key: return ""` gate) | Every existing check asserting the current `.dashboard-grid home-status-grid` three-`stat_tile()` shape retargets to the new `status_row()`-based hero card; every existing check asserting the current recent-flights row shape (no thumbnail) retargets to include the new `<img>` |
| — Next-wake "Expected since" (past-time fix, part of D-17) | `companion/pages/home_page.py`: `_status_tiles_html()`'s next-wake block (`home_page.py:184-192`) — currently always renders `"Next wake ≈ %s"` with no past-time check; needs an `is_past = next_wake_parsed < layout.parse_iso(now)` branch rendering `EXPECTED_SINCE_TEMPLATE % clock` in the warn colour instead | New check needed — none exists today for the past-time branch |
| — duplicated verdict fix (part of D-17) | See Pitfall 3 above | New check needed asserting the Frame tile/row's verdict text appears exactly once |
| D-18 visual quality | `companion/static/style.css` (hero-row layout, `.status-row` styling per D-21), the design-system skill (D-34) | Headless screenshot sweep at 1280/390px — see Validation Architecture |
| D-19 instant switches move to Display | See Pitfall 1 above — lands in `companion/pages/config_page.py`'s `quiet_hours_group()`/`display_group()`, NOT `home_page.py` | New checks needed for the two quick-action forms now rendering on Display; `test_config_page.py` gains coverage `test_companion_app.py`'s existing `/quick/display`/`/quick/quiet-hours` route tests already partially cover (those routes' `return_to` changes from Home to Display per D-16, so their redirect-target assertions retarget) |
| D-20 no new queries beyond the artwork lookup | `companion/pages/home_page.py`: the one new call is `illustrations.normalise_airline_key()` on the CURRENT flight's airline (from `ctx["last_checkin_ts"]`-adjacent state or the gallery/last-flight row already read) — a pure string function, no new DB query | N/A, no query added |
| D-21 `layout.status_row()` | NEW function in `companion/layout.py`, beside `stat_tile()` (`layout.py:1239+`) — `status_row(label, verdict, detail, state)` returning `<div class="status-row status-row--ok|warn|error">...` | New function, new tests; consumed by `home_page.py`'s hero card and `config_page.calendar_group()`'s D-14b status row — both call sites need their own checks |

### D. Live theme preview (D-22..D-24)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-22 keep the chip grid, add a live preview above it | `companion/pages/config_page.py`: `theme_fieldset()` (`config_page.py:811-1004`) gains a new `.theme-live-preview` block before the existing `_theme_chip_grid_html()` call | New markup, new checks — the existing chip-grid checks stay valid unmodified (the grid itself is unchanged) |
| D-23 `/theme-preview/{id}.png?live=1` cached per (theme, event id) | `companion/theme_preview.py`: `cache_path()`/`cached_preview_bytes()`/`preview_signature()` gain an optional `live_event=None` parameter (see Pitfall 7 / Code Examples above); `companion/app.py`: `_serve_theme_preview_image()` (`app.py` ~ the block right after `_handle_illustration_replace`, confirmed reading `theme_id not in device_config.THEMES` then `theme_preview.cached_preview_bytes()`) reads the `?live=1` query param and, when present, fetches `history_db.recent_runway_events(conn, limit=1)`'s single row (or `None`) and passes it through | Existing theme-preview-route tests (theme-id membership 404, cache-hit/miss) stay valid for the NON-live path; new tests needed for `?live=1`'s fallback-to-sample-flight and its cache-miss-on-new-event behaviour |
| D-24 preview follows selection via `theme-preview.js` | NEW `companion/static/theme-preview.js` (six-touch-point static-script contract, see Architecture Patterns above); `companion/pages/config_page.py`: each theme chip gains a `data-preview-src="/theme-preview/{id}.png?live=1"` attribute the script reads on `change`/`click` to swap the `.theme-live-preview img`'s `src` | New file, new checks per the standard static-script three-check pattern |

### E. Notifications (D-25..D-28)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-25 ntfy-style channel | NEW `server/notify.py`: `send_notification(topic_url, title, body, timeout=5)` using `urllib.request` (Don't Hand-Roll table above); SSRF-gated via `calendar_rules._url_is_safe()`/`_address_is_public()` reused, not re-derived | New file, new tests with an injected transport |
| D-26 Device "Notifications" group | `server/device_config.py`: new `notifications` key in `load_device_config()`/`save_device_config()` (`device_config.py:641-798`), following the exact validation/default/config-history pattern `screen_id` used in phase 19 (membership/type-check on write, degrade-to-default on read); `companion/pages/config_page.py`: NEW `notifications_group()` builder (topic URL write-only per the calendar-URL precedent — see Security Domain's masking note — two checkboxes, a "Send a test" button as its OWN small form outside `#settings-form`, matching `calendar_disconnect_section()`'s sibling-form shape); `companion/app.py`: NEW `POST /settings/notifications/test` route | `server/test_config_history.py`'s full-config-dict equality checks (the same ones D-23/`screen_id` touched in phase 19, `server/test_config_history.py` lines noted there) need a `"notifications": {...default...}` key added to every expected literal — the single highest-count mechanical retarget in this section, exactly the shape phase 19's own D-23 retarget was |
| D-27 sent from the poll loop, transitions only | `server/poll_loop.py`: BOTH `battery_low_active` sites (`poll_loop.py:846-849` inside the hold branch, `poll_loop.py:1011-1014` in the main branch) gain a call to a new small helper (e.g. `_notify_battery_transition(state_dir, was_battery_low, battery_low, battery_mv, device_cfg)`) when `battery_changed` is true; a NEW frame-silent check reads `history_db.latest_device_health()`'s `ts` and compares its age against `server.wake.device_staleness_thresholds(server.wake.effective_wake_interval_s(device_cfg))[0]` (the WARN threshold, i.e. 3x — already exactly D-27's own multiplier, confirmed: `MISSED_WAKES_WARN = 3` in the existing `companion/wake.py:38`) — moved to `server/wake.py` per the module-move below; `poll_state.json` gains a `notifications` sub-dict (`{"last_battery_sent": bool, "last_silent_sent": bool}` or similar) so a repeat cycle with no NEW transition sends nothing | `server/test_poll_loop.py`'s existing `battery_low_active` transition tests (81/81 baseline) stay valid; NEW tests needed for the notify-call injection point (mock/stub `server.notify.send_notification`) and the frame-silent transition |
| — server-side wake-arithmetic module (the seam D-27 explicitly names) | NEW `server/wake.py` — `effective_wake_interval_s(device_cfg)`, `device_staleness_thresholds(wake_interval_s)`, `next_wake_at_iso(last_checkin_ts, device_cfg)`, moved VERBATIM from `companion/wake.py` (`companion/wake.py:81-193`, already stdlib + `server.device_config`-only, confirmed by its own docstring's import boundary statement — the move requires zero logic changes, only a new home); `companion/wake.py` becomes a 3-line re-export shim (`from server.wake import *` or explicit named re-exports) so every existing `companion.wake.*` call site AND every existing pinned test importing `companion.wake` keeps working unmodified | No existing test breaks if the shim re-exports the same names; if a planner instead chooses to update every `companion/pages/*.py` import site to `from server import wake` directly and delete the shim, every one of those import lines (`home_page.py:24`, `config_page.py:20`) needs updating in the same commit — the shim approach is lower-risk and is the RECOMMENDED path here |
| D-28 notification language | `server/device_config.py`'s `notifications.lang` field — see Pitfall 6 above (a save-time snapshot of `ctx["lang"]`, never a submitted form field) | New validation gate in `save_device_config()` (membership test against `{"en", "fr"}`, degrading to `"en"` on read for any pre-phase-20 config) |

### F. Simple mode (D-29..D-31)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-29 the switch + cookie + route | `companion/auth.py`: new `UI_MODE_COOKIE_NAME`; `companion/app.py`: new `MODE_ROUTE = "/ui-mode"`, `_handle_mode_post()` mirroring `_handle_theme_post()`/`_handle_lang_post()` exactly, gated in `do_POST()`; `companion/layout.py`: `_mobile_nav_html()`/`sidebar_nav()`'s footer gains a third switch beside the theme picker and (once D-02 lands) the language picker | New checks mirroring the existing theme-cookie round-trip tests |
| D-30 what it hides | `companion/layout.py`: `_nav_groups()`/`sidebar_nav()`/`_mobile_nav_html()` (`layout.py:709-937`) gain a `simple_mode` parameter that skips the `ADVANCED_GROUP_LABEL` group entirely and suppresses the Health nav-dot markup unconditionally; `companion/pages/home_page.py`: the "See details on Health" link (`HEALTH_LINK_TEXT`, `home_page.py:89, 224`) gated on `not ctx.get("simple_mode")`; `companion/pages/config_page.py`: `_edit_artwork_link_html()`'s call site gated the same way (though D-36 relocates this link entirely — see G below, so this gate may end up living on Airlines' new button instead); `companion/pages/airlines_page.py`: the `?edit=1` lightbox forms already gate on `ctx["edit_mode"]` (`airlines_page.py:1217-1219`) — simple mode additionally suppresses the "Change pictures" button itself (D-36) so `edit_mode` can never even be reached via the UI (typing the URL by hand still works, per D-30's own "presentation choice, not access control" text); the `<details>` disclosures (D-14a/D-15a) collapse to one plain sentence when `simple_mode` is true | This is a new `ctx["simple_mode"]` key threaded through the SAME five/six render sites — following the EXACT precedent `ctx["edit_mode"]` already established (`companion/pages/__init__.py:137-151`'s own documented contract: presentation-only, never consulted by a POST handler) |
| D-31 what it keeps | No code change beyond D-30's gates — Home/Display/Flights/Airlines/switches/Sign out render exactly as today when `simple_mode` is true, minus the D-30 exclusions | N/A |

### G. Artwork editing made obvious (D-36)

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-36 | `companion/pages/config_page.py`: DELETE `_edit_artwork_link_html()`'s call site from Device's `action_html` slot (`config_page.py:2306-2311`) — the function/constants can stay as dead code removal or be deleted outright, planner's call; `companion/pages/airlines_page.py`: `render()`'s `layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)` call (`airlines_page.py:1981`) gains an `action_html=` argument building a toggle link — `"Change pictures"` linking to `?edit=1` when `not ctx.get("edit_mode")`, `"Done"` linking to `/airlines` (no query) when `ctx.get("edit_mode")` is true — plus one new sentence under the gallery heading, both gated off entirely when `ctx.get("simple_mode")` is true (D-30) | `test_config_page.py`'s Device-page "Edit artwork" link checks retarget to assert its ABSENCE; `test_view_pages.py`'s Airlines-page checks gain new assertions for the toggle link's two states |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-19's instant-switch placement requires restructuring `quiet_hours_group()`/`display_group()` to render outside `<form id="settings-form">` with a `form=` attribute bridging their inputs back in, rather than a simpler-looking in-place insertion | Pitfall 1 | If implemented as literally described (a `<form>` prepended inside the existing group markup), the result is invalid HTML with unpredictable browser auto-correction behaviour — a real, likely-undetected-by-casual-QA defect, since the page would still visually "look right" in most browsers' error-recovery parsing |
| A2 | D-14c's calendar-connect mini-form needs a NEW dedicated route rather than reusing `/settings` with `scope=display`, because once D-11 lands, `scope=display`'s `in_scope` set includes Quiet hours/Screen, whose absent-checkbox semantics mean "explicitly OFF" | Pitfall 2 | If assumed away, a user connecting their calendar would silently switch off Quiet hours and the screen in the same action — a severe, silent, hard-to-diagnose regression |
| A3 | Home's duplicated verdict (D-17's bug-fix clause) has the single root cause documented in Pitfall 3 — `home_page.py` embedding `health_state["device_html"]` wholesale, which already contains its own verdict paragraph — not a copy-paste duplicate string elsewhere | Pitfall 3 | Low risk if wrong (the fix would simply need retargeting to wherever the real duplicate lives), but the evidence (byte-identical `FRAME_STATE_TEXT`/`DEVICE_STATE_TEXT` dicts, confirmed by direct read) is strong |
| A4 | `freshness.js`, `confirm-submit.js`, and `poll-cooldown.js` need ZERO JavaScript changes for D-06 — only their Python callers need to wrap the already-externalized `data-*` attribute values in `t()` | Pitfall 4 | If a plan spends effort "fixing" these three files' JS, that effort is wasted; if a plan skips wrapping their Python-side callers in `t()` believing the JS fix already handles i18n, the attributes stay English-only — the risk is asymmetric, so this assumption should be explicitly confirmed at plan-check time |
| A5 | D-26's "shown masked like the calendar URL" should be read as "write-only, never rendered, exactly like the calendar URL actually behaves" (empty value on every load) rather than a partial-character masking scheme (`ntfy***xyz`) — because no such masking scheme exists anywhere in this codebase to model it on, and the calendar URL itself is NOT masked, it is write-only | Security Domain / Section E | If a masking scheme is invented from scratch, it introduces a new, unprecedented UI pattern this codebase has never needed elsewhere, and (worse) a naive masking implementation risks re-deriving/exposing partial secret bytes that the write-only convention was specifically designed to avoid (T-16-SECRET's own stated threat model) |
| A6 | The frame-silent notification threshold (D-27's "3x the effective wake interval") should reuse `wake.device_staleness_thresholds()`'s existing WARN threshold verbatim (which already uses `MISSED_WAKES_WARN = 3`), rather than a new, independently-tuned constant | Section E | If a separate constant is introduced and drifts from Health's own warn threshold, D-27's own text ("must not be lower than the Health page's own warn threshold") could silently be violated by a future edit to one constant without the other — reusing the same function/constant makes drift impossible by construction |
| A7 | `home_page.py`'s and `config_page.py`'s existing test coverage for Home/Display do not currently live in a file this research read in full (e.g. a possible `test_home_page.py` was not found by the file listing, `home_page` checks may be folded into `test_view_pages.py` or `test_status_pages.py`) | Validation Architecture / Wave 0 Gaps | If the planner assumes a dedicated Home test file exists and it does not, new checks land in the wrong file, mis-tracking `EXPECTED_CHECK_COUNT`; confirm test-file ownership for Home explicitly before Wave 1 |

## Open Questions

1. **Does `quiet_hours_group()`/`display_group()`'s restructuring (Pitfall 1's resolution) risk breaking any pinned check that currently asserts these groups render as a literal descendant of `<form id="settings-form">`?**
   - What we know: no check NAMED this constraint was found by direct grep of `test_config_page.py`; the constraint is implicit in how a browser would parse the current (valid) HTML.
   - What's unclear: whether any existing check does a DOM-parse-based assertion (rather than a substring check) that would notice the restructuring even without naming it explicitly.
   - Recommendation: run `test_config_page.py`'s full suite immediately after this restructuring lands, before writing any NEW check for it, and treat any newly-failing check as a genuine signal to investigate rather than a "pre-existing sandbox failure" to wave off.

2. **Where should Home's own test checks live once D-16..D-21 substantially rewrite `home_page.py`?**
   - What we know: no `companion/test_home_page.py` exists today; Home-page-specific assertions were not conclusively located inside the time available for this research (they may be split across `test_view_pages.py`/`test_status_pages.py`/`test_companion_app.py`, each of which does touch `GET /` in passing for unrelated reasons).
   - What's unclear: the exact current home-page check count and file, needed to set an accurate `EXPECTED_CHECK_COUNT` baseline before this phase's edits.
   - Recommendation: the planner's Wave 0 task should grep each of the four harness files for `GET /` / `home_page` references and either confirm an existing owner or create `companion/test_home_page.py` explicitly, before any Home-page code changes land.

3. **Should `companion/wake.py` become a pure re-export shim over `server/wake.py`, or should every import site be updated directly?**
   - What we know: the shim approach (Section E's D-27 entry) requires zero changes to any existing `companion/pages/*.py` import line or any existing pinned test; the direct-update approach is "more correct" architecturally (no indirection) but touches more files for no behavioural gain.
   - What's unclear: whether the project's own conventions (which favour explicit, traceable imports over re-export indirection elsewhere) would prefer the direct-update path despite the larger diff.
   - Recommendation: default to the shim (lower risk, this phase already has three other structural conflicts to resolve) unless the planner has a specific reason to prefer the direct-update path.

## Sources

### Primary (HIGH confidence — direct source read, 2026-09-11)
- `companion/app.py` (targeted: routing table, `page_context()`, theme-post handler, redirect/hardening headers, calendar-disconnect handler, `_handle_settings_post()`, illustration/theme-preview serving routes) — 2665 lines
- `companion/layout.py` (targeted: NAV_GROUPS, nav renderers, theme-form idiom, `local_clock_text()`/`relative_age_text()`, `page_shell()`/`login_shell()`) — 1511 lines
- `companion/pages/config_page.py` (near-full targeted read: `scope_groups()`, every group builder, calendar/rules sections, `render()`, `handle_post()`, `submitted_calendar_signal()`) — 2987 lines
- `companion/pages/home_page.py` (full read, 382 lines) — every constant and function
- `companion/pages/airlines_page.py` (targeted: illustration-key resolution, `?edit=1` gating, gallery header assembly) — 1988 lines
- `companion/screens.py` (full read, 87 lines)
- `companion/wake.py` (full read, 193 lines)
- `companion/theme_preview.py` (full read, 242 lines)
- `companion/auth.py` (targeted: cookie constants, `secure_cookie_flag()`)
- `companion/static/copy-button.js`, `dirty-state.js`, `freshness.js`, `confirm-submit.js`, `poll-cooldown.js` (targeted greps confirming which already read `data-*` attributes vs. hardcode literals)
- `server/device_config.py` (targeted: `load_device_config()`/`save_device_config()`, the registry/normalise pattern)
- `server/poll_loop.py` (targeted: both `battery_low_active` sites, `load_poll_state()`/`save_poll_state()`)
- `server/history_db.py` (targeted: `recent_runway_events()`, `record_device_health()`, `latest_device_health()`)
- `server/plane/colour_rules.py`, `server/plane/calendar_rules.py`, `server/plane/illustrations.py`, `server/plane/render.py` (targeted: `RULE_KINDS`/`RULE_KIND_LABELS`, `save_calendar_url()`/`refresh_calendar_registry()`/`_url_is_safe()`, `select_illustration()`/`normalise_airline_key()`, `build_canvas()`'s signature)
- Live harness execution, 2026-09-11: every harness in `scripts/run-all-tests.sh` — see Validation Architecture's baseline table
- `.planning/phases/20-.../20-CONTEXT.md`, `20-PRD.md` — every D-01..D-36 decision's exact wording
- `.planning/phases/19-.../19-RESEARCH.md`, `19-PATTERNS.md` — the static-script contract, the `EXPECTED_CHECK_COUNT` re-derivation discipline, the precedent-conflict-resolution pattern this research's three CRITICAL pitfalls follow
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the design-system contract (tokens, card/nav idioms, the existing `.quick-action`/`.theme-status`/`.data-table` conventions every new component must fit)
- `.planning/REQUIREMENTS.md`, `.planning/config.json` — CFG-13..18, workflow flags (`nyquist_validation: true`, `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`)

### Secondary (MEDIUM confidence)
- None — no external documentation, library, or API was consulted; this phase is entirely internal-codebase research plus stdlib-module knowledge (`contextvars`, `urllib.request`), both verified against Python's own standard library (no version-specific behaviour risk at 3.12).

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, verified by direct source read of every file this phase touches; stdlib module choices (`contextvars`, `urllib.request`) cross-checked against this codebase's own existing outbound-HTTP precedent (`calendar_rules.fetch_ics()`)
- Architecture: HIGH — every decision's landing site verified by file:line read, not inferred from summaries; three structural conflicts (Pitfalls 1-3) found by direct code trace, not by intuition
- Pitfalls: HIGH — every pitfall is grounded in a specific, quoted source line or a direct grep/run confirming its scope (e.g. "byte-identical dict values," "no test references EVERYDAY_GROUPS by name," live harness counts)

**Research date:** 2026-09-11
**Valid until:** This research is tied to the exact commit state read on 2026-09-11; re-verify file:line references and `EXPECTED_CHECK_COUNT` values if planning is delayed more than a few days past this date or if any other phase/quick-task touches the same files first.
