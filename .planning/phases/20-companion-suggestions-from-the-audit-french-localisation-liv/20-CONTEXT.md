# Phase 20: Companion suggestions from the audit — bilingual FR/EN, Display regrouped, Home redesigned, live theme preview, notifications, simple mode - Context

**Gathered:** 2026-09-11
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/phases/20-companion-suggestions-from-the-audit-french-localisation-liv/20-PRD.md` — written from the developer's own feedback after phase 19 and the four audit suggestions S-01/S-03/S-05/S-06 deferred from phase 19)

<domain>
## Phase Boundary

The companion web app (`companion/`) plus the two server seams the phase needs: `server/device_config.py` (a `notifications` config group) and `server/poll_loop.py` (transition-only push notifications, with the wake-interval arithmetic shared through a server-side module so the server never imports the companion). Six areas, all locked by the PRD:

1. **Bilingual FR/EN** with a per-browser switch in the nav footer; English stays the source language in code, French is a catalogue keyed by the English string; a completeness harness keeps the two in step (D-01..D-09).
2. **Display regrouped** — Runway, Calendar and Flight colours join Theme, Quiet hours and Screen on/off on Display, organised as Look / What it watches / When it is on; Calendar and Flight colours are redesigned for a non-technical user (D-10..D-15).
3. **Home redesigned** — no quick actions on Home (switches go to Display, refresh stays on Device); a hero row (picture + one status card headlined by the next update) and the recent flights with artwork thumbnails; the duplicated Frame verdict and the past "Next wake" are fixed (D-16..D-21).
4. **Live theme preview** rendered from the last real flight, following the chip selection (D-22..D-24).
5. **Push notifications** (ntfy-style topic) on battery-low and frame-silent transitions, configured on Device, sent from the poll loop (D-25..D-28).
6. **Simple mode** (per-browser switch) hiding the Advanced group and every advanced affordance (D-29..D-31), and the "Edit artwork" link replaced by a clear "Change pictures" button on Airlines (D-36).

The audience framing from phases 18–19 governs every change: a second household member with basic computer skills uses the everyday pages; a change that makes an everyday page more technical is the wrong change. The frame firmware, the panel renderer's output and the on-disk state layout (beyond the new `notifications` key and `poll_state` sub-dict) are out of bounds.

</domain>

<decisions>
## Implementation Decisions

Every decision below is locked (it comes from the PRD, which records the developer's own requests verbatim). The four items under "Assumptions flagged" are the orchestrator's readings of a short request; they are locked for this phase and one-line changes if the developer later prefers otherwise.

### A. Bilingual companion — French and English (S-01, CFG-13)

- **D-01 Two languages, never one.** The companion ships in French and English.
  English stays the source language in code (every existing string constant
  keeps its English value, so every pinned test keeps passing); French is a
  translation catalogue. No third language in this phase, but the catalogue
  mechanism must not hard-code "fr" anywhere except the catalogue itself.
- **D-02 Language switch in the nav footer**, next to the existing
  Auto/Light/Dark theme picker, as a two-segment control "FR · EN" using the
  same idiom (a `<form method="post">` per option, no JS required). It posts to
  a new `POST /ui-lang` route (session-gated like `/ui-theme`), which sets a
  cookie modelled on `auth.UI_THEME_COOKIE_NAME` (same flags, same `Secure`
  opt-out) and redirects back to the referring page. The cookie is per browser,
  which is what "each person in their own language" means with one shared
  password.
- **D-03 First visit defaults from the browser.** With no cookie, the language
  is the first supported entry in `Accept-Language` (`fr*` → French, anything
  else → English). The chosen language is written into `<html lang="…">` by
  `layout.page_shell()`.
- **D-04 Translation mechanism: a lookup keyed by the English string.** A new
  `companion/i18n.py` exposes `t(text)` (and a `t_lang(text, lang)` for tests)
  that returns the French text from a catalogue when the current request
  language is French, else `text` unchanged. The catalogue is a plain dict in
  `companion/i18n_fr.py` keyed by the exact English source string (templates
  keep their `%s`/`%d` placeholders in the key). Missing keys fall back to
  English — never raise. The current request language reaches the pages
  through `ctx["lang"]` (set by `app.page_context()`), and `t()` reads it from
  a per-request context set once by the handler, so page modules do not thread
  `lang` through every helper.
- **D-05 Every user-visible string on every page goes through `t()`** —
  headings, captions, tile labels, verdicts, button labels, flash messages,
  field errors, empty states, `alt`/`aria-label`/`title` attributes, the nav
  labels, the login page, the 404 page, the calendar-disconnect confirmation
  page, and the email-free notification texts. Strings that are identifiers
  (route names, CSS classes, flash keys, ICAO codes, airline names, theme ids)
  are not translated. Theme *names* shown to people are translated where a
  natural French name exists ("Blanc", "Nuit"…), the theme ids are not.
- **D-06 JavaScript strings come from the server.** The static scripts must not
  carry English literals that reach the screen: `copy-button.js`'s "Copied",
  `dirty-state.js`'s "N changed" sentences, `freshness.js`'s pause/resume
  labels, `confirm-submit.js`'s question, `poll-cooldown.js`'s countdown
  template. Each is read from a `data-*` attribute rendered (and translated)
  by the server on the element that owns it, the way `freshness.js` already
  reads `data-pause-text`/`data-resume-text`.
- **D-07 Dates and numbers follow the language.** `layout.local_clock_text()`
  and the relative-age text ("1d ago" → "il y a 1 j", "just now" → "à
  l'instant") are language-aware; month abbreviations are localised ("10 sept.
  11:53"). Times stay 24-hour Europe/Paris in both languages.
- **D-08 A completeness harness.** A new check in the companion test suite
  renders every page (Home, Display, Device, Flights, Airlines, Health, login,
  404, the disconnect confirmation page) in French against a seeded state and
  fails if any string from the page modules' catalogue of user-visible
  constants is missing from `i18n_fr.py`, listing the missing keys. A second
  check asserts no catalogue entry is unused (dead translations). This is what
  keeps the two languages in step as future phases add strings.
- **D-09 French copy quality.** Sentence case, typographic apostrophes and
  non-breaking spaces before `:` `;` `?` `!`, no anglicisms where a plain
  French word exists ("Piste", "Heures calmes", "Écran", "Vols", "Compagnies",
  "Accueil", "Affichage", "Appareil", "État"). The nav labels in French:
  Accueil, Affichage, Vols, Compagnies, Avancé (group), État (Health),
  Appareil (Device).

### B. Display page regrouped — everything everyday in one place (CFG-15)

- **D-10 Runway returns to Display.** `companion/screens.py`: `GROUP_RUNWAY`
  moves from the plane frame's `advanced_groups` to its `everyday_groups`.
  Device keeps Diagnostic LED, Wake interval, Notifications (D-26), Manual
  refresh and the screen selector seam; the Edit-artwork link goes (D-36).
- **D-11 Calendar and Flight colours move to Display too.** `GROUP_CALENDAR`
  becomes an everyday group, and the colour-rules section (`has_colour_rules`)
  renders on Display instead of Device. The calendar-disconnect form and the
  rules add/delete routes follow their groups (their `return_to` becomes
  Display).
- **D-12 Display is organised in three headed sections**, each a
  `.page-section` group with a short plain-language intro, in this order:
  1. **Look** — Theme (with the live preview, D-24), Flight colours (D-15),
     Calendar (D-14).
  2. **What it watches** — Runway.
  3. **When it is on** — Screen on/off and Quiet hours, each carrying its
     instant switch (D-19) above the scheduled settings.
  Device's intro sentence and the "Screen: Plane frame" caption stay as they
  are; Display's intro becomes "Everything about what the frame shows and
  when." (translated).
- **D-13 The one settings form stays one form.** Moving groups between pages
  changes `scope_groups()` only; `handle_post()`'s absent-checkbox carry-forward
  and the hidden `scope`/`return_to` fields keep working unchanged. The
  instant switches (D-19), the calendar connect/disconnect forms and the rule
  add/delete forms remain their own forms outside `#settings-form`, so the
  dirty-state bar never sees them.

#### Calendar — strongly improved UX/UI (D-14)

- **D-14a One-line purpose, no lecture.** Caption: "Flights from your calendar
  get their own colour on the frame." The two-sentence disclaimer about "does
  not track or announce anything" moves into a `<details>` "How it works"
  disclosure under the card, along with the "applies on the next poll" note.
- **D-14b A status row instead of a sentence.** A `.status-row` (dot + verdict
  + detail, the same primitive Home's status card uses, D-21) reads
  "Connected · 12 upcoming flights · checked 10 min ago" or "Not connected".
  Errors from the last fetch ("The feed could not be read") appear in the
  detail, never as a raw exception string.
- **D-14c Connect is its own action.** The feed-URL input and a "Connect"
  button are one small form that posts immediately (the existing save path
  for the URL, called with the URL only), shows a flash on success ("Calendar
  connected — 12 flights found") or a field-level error on failure, and never
  requires the page-wide Save. While connected, the URL input is hidden behind
  a "Replace the feed URL" disclosure; "Disconnect" keeps its confirmed form
  from phase 19 (D-08) and sits at the end of the card as a secondary button.
- **D-14d Theme picked with chips, not a select.** The calendar theme uses a
  compact chip row (`.theme-chip--compact`: the same rendered preview band,
  smaller) as a `role="radiogroup"`, inside `#settings-form` (it is a saved
  setting, unlike the URL). No `<select>` for themes anywhere on Display.

#### Flight colours (per-flight colour rules) — strongly improved UX/UI (D-15)

- **D-15a Rename.** Heading "Flight colours"; caption "Give one flight, one
  aircraft or one airline its own theme." The precedence rules and the
  "adding a key that's already in use replaces it" sentence move into a
  `<details>` "How rules combine" disclosure.
- **D-15b The add form becomes one line.** A segmented `role="radiogroup"`
  "Flight · Aircraft · Airline" (labels replace "Callsign / ICAO24 hex /
  Callsign prefix"; the technical term stays as the segment's `title`), a
  value input whose placeholder changes with the segment (`AFR1234` /
  `3944F2` / `AFR`) via a small external script, a compact theme chip row
  (D-14d's primitive) and an "Add" button. Validation errors render under the
  field (phase 19 D-07 idiom), keeping the typed value.
- **D-15c Rules are a list of rows, not a table.** Each existing rule is a
  `.rule-row`: a theme swatch (the theme's two palette dots, as
  `.theme-chip__swatches` already draws them), the key in `.mono`, a small
  kind badge ("Flight"/"Aircraft"/"Airline"), the theme name, and a "Remove"
  secondary button whose form carries `data-confirm` (phase 19's
  `confirm-submit.js`). Rows are ordered most-specific first (flight,
  aircraft, airline), then alphabetically.
- **D-15d Empty state in the muted sans voice**: "No flight colours yet." plus
  one sentence, `.text-label`, never a serif heading.
- **D-15e Suggested from recent flights.** Under the add form, up to five
  "Recent: AFR1380 · TVF7412 · …" chips (from the last runway events) fill the
  segment and value on click — the common case is "colour the flight I just
  saw". This is a progressive enhancement: with no JS the chips are plain
  text.

### C. Home redesigned — useful and pleasant at a glance (CFG-14)

- **D-16 Quick actions leave Home.** The "Quick actions" card is removed. The
  Screen on/off and Quiet hours instant switches move to Display (D-19); the
  Refresh-now button moves to Device's existing "Manual refresh" section (which
  already triggers the same route; the Home button is simply dropped). The
  `/quick/*` routes, their flash keys and their tests stay; only their
  `return_to` changes to Display.
- **D-17 Home layout.** Two rows:
  1. **Hero row**: the current picture on the left (portrait, inside
     `.preview-frame`, capped at 60vh on desktop, full width on phones, with
     the "Rendered HH:MM" caption and, when the flight is known, a one-line
     "AFR1380 · Air France · ORY → TLS" under it); on the right a single
     **status card** (D-21) with three `.status-row`s — Frame, Battery,
     Flight data — each one dot + one verdict + one detail on one line. The
     card's headline, above those rows and in the emphasis voice, is the next
     update: "Next update ≈ 22:25" (the developer asked for it to stand out),
     or, when that time is already past, "Expected since 12:03" in the warn
     colour (fixes the misleading past time from phase 19). No
     duplicated verdict text (today the Frame tile repeats "Has not checked in
     for a long time" twice — this is a bug to fix). The "See details on
     Health" link stays under the card and is hidden in simple mode (D-30).
  2. **Recent flights**: full width, the last five flights as rows with the
     airline's illustration thumbnail when artwork exists (`/illustration/…`,
     lazy-loaded, 40×40, rounded), callsign in `.mono`, airline · route ·
     direction, and the local time. "See all flights" stays.
- **D-18 Visual quality.** Follow the design contract in the
  `sketch-findings-skypane` skill: one 24px gap, `.page-section` cards with the
  hairline border, the 12px uppercase label voice for row labels, status
  colours only through the existing `--color-ok/warn/error` tokens with a
  text verdict beside every dot. The hero row stacks picture-first on phones.
  Dark theme must be checked. A headless screenshot at 1280 and 390 px is part
  of the phase's verification.
- **D-19 Instant switches on Display.** The Screen on/off group gets a
  `.quick-action` switch row at its top ("Screen · On · [Switch off]") that
  posts to `/quick/display` as today; the Quiet hours group gets the same for
  `/quick/quiet-hours`, above the presets and time inputs. They are their own
  forms (D-13). Their copy explains they apply on the next wake, in one short
  sentence shared by both.
- **D-20 Home is the landing page and stays fast.** No new queries beyond what
  Home already runs plus one lookup for the current flight's airline artwork
  key (reusing the Airlines page's resolver).
- **D-21 A shared status-row primitive.** `layout.status_row(label, verdict,
  detail, state)` renders `<div class="status-row status-row--ok|warn|error">`
  with the dot, the label in the label voice, the verdict in emphasis and the
  detail muted; Home's status card, the calendar status (D-14b) and, later,
  other pages use it. It is documented in the design-system skill.

### D. Live theme preview from the real last flight (S-03, CFG-16)

- **D-22 Keep the chip grid** (validated by the developer in 06.6.4.1.1); no
  carousel. Add a large live preview above it.
- **D-23 `/theme-preview/{id}.png?live=1`** renders the theme with the most
  recent runway event (callsign, airline, route, direction, artwork) when one
  exists, falling back to today's sample flight. It is cached per
  (theme, event id) in the existing `theme_previews` cache directory with the
  same signature scheme, so a page load never renders 16 panels.
- **D-24 The preview follows the selection.** Above the grid, a
  `.theme-live-preview` shows the currently selected theme's live render with
  the caption "Preview with your last flight: AFR1380" (or "Preview with a
  sample flight" when none). A small external script (`theme-preview.js`,
  wired through the static-script contract, no inline JS under the CSP)
  swaps the image `src` when a chip is selected; without JS the preview shows
  the saved theme. Image width 480px max, `loading="lazy"` for the chips,
  eager for the live preview.

### E. Notifications — battery low and frame silent (S-05, CFG-17)

- **D-25 Channel: an ntfy-style push topic.** Simplest thing that reaches a
  phone with no account on our side: the user pastes a topic URL (e.g.
  `https://ntfy.sh/skypane-xyz`, or a self-hosted ntfy) and the server POSTs a
  plain-text body with a `Title` header. Any URL that accepts such a POST
  works. No email/SMTP in this phase.
- **D-26 Configured on Device**, in a new "Notifications" group: topic URL
  (stored server-side, shown masked like the calendar URL), two checkboxes
  "Battery low" and "Frame silent", and a "Send a test" button (its own form,
  posts immediately, flashes the result). Persisted in the device config
  document (`server/device_config.py`) under a `notifications` key with
  validation and a config-history entry like every other field.
- **D-27 Sent from the poll loop, on transitions only.** In
  `server/poll_loop.run_once()`: when `battery_low_active` flips (the hysteresis
  decision already exists) send "Battery low — 3 480 mV (≈ 18 %)" / "Battery
  back to normal"; when the last device check-in becomes older than 3× the
  effective wake interval (reuse `companion.wake`'s thresholds; move the
  shared arithmetic to a server-side module so the server never imports the
  companion) send "The frame has not checked in for 2 h" / "The frame is back".
  A `notifications` sub-dict in `poll_state.json` remembers what was last
  sent so nothing repeats every cycle. Delivery failures are logged and never
  break the poll cycle (5 s timeout, one attempt).
- **D-28 Language of notifications** follows a `lang` field in the same
  config group (default from the last language used in the companion at save
  time), because the poll loop has no browser to read.

### F. Simple mode — one companion, two audiences (S-06, CFG-18)

- **D-29 A "Simple mode" switch** in the nav footer, under the language and
  theme pickers, per browser (cookie, same mechanism as D-02, route
  `POST /ui-mode`). No second password in this phase (a read-only account is
  a separate auth change; noted as deferred).
- **D-30 What simple mode hides**: the Advanced nav group (Health, Device),
  the "See details on Health" link on Home, the "Edit artwork" link, the
  `?edit=1` lightbox forms on Airlines, the "How it works"/"How rules combine"
  disclosures' technical wording (they collapse to one plain sentence), and
  the Health status dot in the nav. Advanced URLs typed by hand still work —
  simple mode is a presentation choice, not an access control.
- **D-31 What simple mode keeps**: Home, Display (all six groups), Flights,
  Airlines (view, resolve a gap), the language/theme/mode switches, Sign out.

### G. Artwork editing made obvious (developer feedback)

- **D-36 "Edit artwork" leaves Device.** The developer did not understand the
  "EDIT ARTWORK — Opens Airlines with the artwork-editing forms available"
  link. It is removed. Instead, the Airlines page gets a secondary button at
  the top of the gallery, "Change pictures" (FR "Modifier les images"), which
  links to `?edit=1` and, once in edit mode, reads "Done" and links back
  without the query. One short sentence under the gallery heading explains
  what edit mode allows ("Replace an airline's picture or add one for an
  airline that has none."). The button is hidden in simple mode (D-30). The
  `?edit=1` gating from phase 19 (D-22) stays exactly as is.

### H. Cross-cutting

- **D-32 No new inline scripts or handlers** (CSP from phase 19). New scripts
  (`theme-preview.js`, `rule-form.js`) follow the six-touch-point
  static-script contract in the phase 19 patterns.
- **D-33 Tests.** Every moved group gets its pinned checks retargeted; every
  new route and switch gets a harness check (happy path, rejection, no-JS);
  `EXPECTED_CHECK_COUNT` re-derived per file as in phase 19. The five checks
  that fail in a root sandbox stay untouched.
- **D-34 Design-system skill updated** (`sketch-findings-skypane`): the new
  status-row primitive, the compact theme chip, the Display section headers,
  the rule row, the language/mode switches, and the Home hero layout.
- **D-35 Dashboard and audit record.** S-01, S-03, S-05, S-06 marked shipped
  in `18-AUDIT.md` and in the audit dashboard's `findings.json` at the end of
  the phase.

### Assumptions flagged for the developer (locked for this phase)
1. Quick actions land on Display (switches) and Device (refresh) — "ailleurs"
   was not more specific.
2. Notifications use an ntfy-style push topic rather than email.
3. Simple mode is a per-browser switch, not a second login.
4. The Display page order (Look → What it watches → When it is on) and the
   renamed "Flight colours" heading are proposals; both are one-line changes
   if the developer prefers otherwise.

### Claude's Discretion
- The exact French wording of every string, within D-09's rules; the catalogue file layout (one dict, grouped by page with comments).
- How `t()` learns the request language (a `contextvars.ContextVar` set by the handler is the expected shape; a thread-local is acceptable since `ThreadingHTTPServer` is one thread per request).
- The compact theme chip's exact dimensions, the status-row's exact spacing, the hero row's breakpoint — all within the design-system skill's tokens.
- The `?live=1` preview cache key and its invalidation when a newer runway event arrives.
- The notification body wording (both languages) and the exact "silent" multiplier if 3× the wake interval proves too twitchy in tests — it must not be lower than the Health page's own warn threshold.
- Plan and wave split; test-file ownership per wave (no two plans in one wave may edit the same test file — the phase 19 wave-4 conflict is the cautionary tale).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase
- `.planning/phases/20-companion-suggestions-from-the-audit-french-localisation-liv/20-PRD.md` — the requirements document; every decision above is traceable to it
- `.planning/REQUIREMENTS.md` — CFG-13..CFG-18 (added by this phase's cadrage); CFG-09 (UI theme cookie, the model for the language and mode cookies)

### Design contract and prior phases
- `.claude/skills/sketch-findings-skypane/SKILL.md` (+ its reference files) — the companion's design system of record: tokens, label voice, card contract, selected-state wash, navigation; every new component must fit it and D-34 updates it
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` — S-01, S-03, S-05, S-06 (the suggestions this phase ships), plus the audience framing
- `.planning/phases/19-companion-audit-follow-through-fix-the-open-findings-from-18/19-CONTEXT.md` — D-02 (freshness fetch-and-swap), D-07 (field errors), D-08 (confirmed disconnect), D-12 (radiogroups), D-13 (next wake), D-18 (CSP: no inline scripts), D-22 (`?edit=1` gating), D-23 (`screen_id`)
- `.planning/phases/19-companion-audit-follow-through-fix-the-open-findings-from-18/19-PATTERNS.md` — the six-touch-point static-script contract every new script must follow
- `.planning/phases/19-companion-audit-follow-through-fix-the-open-findings-from-18/19-VERIFICATION.md` — the ten browser-only human checks still pending; this phase must not regress them

### Code seams named by the decisions
- `companion/screens.py` — the group registry D-10/D-11 change
- `companion/pages/config_page.py` — `scope_groups()`, `render(ctx, scope, errors, submitted)`, `calendar_group()`, the rules section, `theme_fieldset()`
- `companion/pages/home_page.py` — the page D-16/D-17 rebuild
- `companion/layout.py` — `page_shell()` (`<html lang>`), the nav footer (theme picker idiom for the language and mode switches), `local_clock_text()`/`relative_age_text()` (D-07), the new `status_row()` (D-21)
- `companion/app.py` — `/ui-theme` (model for `/ui-lang` and `/ui-mode`), `page_context()`, the static-script routes, `/theme-preview/`
- `companion/theme_preview.py` — the `?live=1` render and cache (D-23)
- `companion/wake.py` — the wake-interval arithmetic to share server-side (D-27)
- `server/poll_loop.py` — `run_once()`'s `battery_low_active` transition (D-27)
- `server/device_config.py` — the `notifications` group (D-26)
- `companion/static/*.js` — the scripts whose literals move to `data-*` attributes (D-06)

</canonical_refs>

<specifics>
## Specific Ideas

- The developer's exact words are quoted at the top of the PRD; "améliorer fortement leur UX et UI" for Calendar and Flight colours is what D-14/D-15 concretise, and "plus en avant" for the next wake is D-17's headline.
- French nav labels are fixed by D-09: Accueil, Affichage, Vols, Compagnies, Avancé, État, Appareil.
- The status-row primitive (D-21) is the one new visual primitive; it serves Home's status card and the calendar status and must be documented in the design-system skill.
- The completeness harness (D-08) is the phase's guard against English leaking into French later; it enumerates the page modules' user-visible constants rather than relying on a hand-kept list.

## Acceptance criteria (from the PRD)
- Switching FR/EN in the footer changes every visible string on every page,
  including flash messages, field errors, button labels and script-driven
  text, with no English leaking in French and vice versa; the completeness
  harness passes.
- Display shows Theme (with live preview), Flight colours, Calendar, Runway,
  Screen on/off (with switch), Quiet hours (with switch); Device shows LED,
  Wake interval, Notifications, Manual refresh, Edit artwork.
- Home shows the hero row and recent flights only; no quick-actions card; no
  duplicated verdict; a past next-wake reads "Expected since".
- The theme preview above the grid shows the last real flight and follows the
  selection.
- A battery-low transition and a silent-frame transition each produce exactly
  one push to the configured topic; "Send a test" reaches it.
- Simple mode hides the Advanced group and every advanced affordance listed in
  D-30 and survives navigation.
- Full suite green apart from the five root-sandbox checks; `ruff check .`
  clean; headless sweep at 1280/390 px with no overflow, no CSP violation.

</specifics>

<deferred>
## Deferred Ideas

- A second, read-only password (deferred; simple mode is cookie-based).
- Email or SMS notifications; a daily digest.
- Any change to the frame firmware or to the panel renderer's output.
- A third UI language.
- Per-screen state directories (the `screen_id` seam from phase 19 stays as
  is).

</deferred>

---

*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Context gathered: 2026-09-11 via PRD Express Path*
