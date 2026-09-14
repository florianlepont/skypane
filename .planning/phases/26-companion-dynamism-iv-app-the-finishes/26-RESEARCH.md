# Phase 26 Research — Companion dynamism IV — "App": the finishes

**Phase goal (ROADMAP.md):** D23 (keyboard shortcuts and a ⌘K command palette),
D24 (guided first run and drawn empty states) and D15 (share the picture of the
day). D6 is already shipped except its manifest/theme-color half. D11 is partly
excluded (hashed filenames imply a build step). D12 is excluded entirely.

**Researched:** 2026-09-13
**Planned with no CONTEXT.md and no UI-SPEC** — the precedent Phases 23, 24 and
25 all set. Every decision that would otherwise have been a question to the
developer is recorded under "Open decisions" below, marked PROVISIONAL.

---

## 0. The one-paragraph answer

This phase is three P3 "finishes" and two leftovers, and the research finding
that shapes all of them is that **almost none of it needs new machinery**. The
palette is the only genuinely new component, and it is the only new script:
`<dialog>` + `showModal()` is already in the app and already provides the focus
trap, focus restoration and Escape handling a hand-rolled palette would have to
re-derive; the picture already sits in a lightbox that a script already opens;
`empty_state()` already has the two-part shape and a compact variant; the
first-run checklist's three signals are all already derivable from state the app
already holds, so it needs no new persistence, no dismissal flag and no
`localStorage` — which 23-RESEARCH.md predicted D23 and D24 would be the first
features in this codebase tempted to reach for. The phase therefore spends
**exactly one new static script**, the same budget Phase 25 set for its five
controls, and the two items most likely to blow it (D15's share, D24's checklist)
are shown below to cost zero.

---

## 1. The machine-enforced contracts this phase runs into

Every number here was read out of the code today, not carried forward from
another phase's prose.

| Contract | Where | Value today | What this phase does to it |
|---|---|---|---|
| CSP `script-src 'self'`, no `unsafe-inline`, no nonce | `companion/app.py:143` | — | unchanged; no inline script anywhere |
| Deferred-script count on the authenticated shell | `companion/test_companion_app.py:4398` (`_fourteen_deferred_scripts_before_closing_body`), assertion at `:4431` | **14** | Phase 25 plans 14 → 15. This phase moves it **once**, 15 → 16, re-derived by RUNNING |
| Per-script triple tax | `test_companion_app.py:3723` (`_static_script_public`), `test_i18n.py:31-37` (French catalogue for every `var ALL_CAPS = "literal"` / `\|\| "literal"`), route==src agreement | 16 `*_SCRIPT_SRC` / `*_SCRIPT_ROUTE` pairs in `layout.py:155-233` / `app.py:156-226` | paid once, in the palette plan |
| No catch-all `/static/` handler | `app.py` route table, one constant per file | — | the palette needs its own route constant and its own dispatch line |
| Exactly one `@supports selector(:has(*))` block | `test_config_page.py:4002`, `:4232` | 1 | unchanged — nothing here needs `:has()` |
| Zero stray comment terminators in `style.css` | `companion/test_status_pages.py` | — | every CSS comment this phase adds must close exactly once |
| No-JS floor (D-09) proven in a real browser | `test_browser_ux.py:930`, `:1377`, `:1584` | 3 blocked-script checks | this phase adds its own, for the palette's destinations and the first run |
| Sandbox baseline | `scripts/run-all-tests.sh` | exactly **5** failing checks (4 × WR-11 read-only, 1 × `anomaly_active()`) | verified by check **NAME**, never by failing-file count |
| Motion tokens | `--motion-fast` 180 ms / `--motion-slow` 2 s; `interpolate-size` and `calc-size(` banned (Chromium-only); global `prefers-reduced-motion` block | — | the palette reuses the existing `<dialog>` `@starting-style` entrance (`style.css:6283-6299`), inventing no third entrance |
| Minimum viewport | 360 px, no horizontal body scrollbar | — | the palette dialog and the first-run card both obey it |

**The `.js` gate already exists and is already load-bearing.**
`companion/static/nav-dropdown.js:31` does
`document.documentElement.className += " js"` **unconditionally**, as the first
script on the shell, and `style.css:1078` (`.js .mobile-nav`) already consumes
it. Used hide-by-default / reveal-under-`.js`, this is how a script-only
affordance avoids rendering as a dead control when scripts are blocked. This
phase depends on the **shipped** mechanism, not on Phase 25's restatement of it.

---

## 2. D23 — keyboard shortcuts and the ⌘K palette

### 2.1 What the audit asked for

> Keyboard shortcuts (`g h/d/v/c`, `/`, `Esc`) and a ⌘K command palette
> (`<dialog>`) searching flights, airlines and settings ("switch screen off",
> "red theme"); ~300 lines, no dependency. — 22-AUDIT.md D23

### 2.2 The cost, stated against Phase 25's precedent

Phase 25 spends **exactly one** new script for **five** controls, and 25-01 pays
the three taxes once so that no later plan in that phase moves the pin. The
instruction for this phase is right to flag the palette as "exactly the kind of
feature that quietly adds another script and another route" — so here is the
bill, itemised, before any design:

- **one** new file `companion/static/command-palette.js`
- **one** new route constant pair (`COMMAND_PALETTE_SCRIPT_ROUTE` in `app.py`,
  `COMMAND_PALETTE_SCRIPT_SRC` in `layout.py`) and **one** new dispatch line —
  there is no catch-all `/static/` handler, by deliberate design
- the deferred-script pin moves **15 → 16**, retargeted in place with a stated
  reason, exactly once in the phase
- a French catalogue entry for every user-visible literal in the new file
  (`test_i18n.py` Check 6)
- a public-route smoke check, an ES5/forbidden-sink scan, and route==src
  agreement — the existing per-file pattern

That is the whole cost, and it is **the phase's entire script budget**. §4 and
§5 below show why D15 and D24 add nothing to it.

### 2.3 The no-JS floor, made executable rather than promised

A palette and a keystroke are script-only by nature. That is acceptable **only**
if everything they reach is reachable without them — and the way to make that a
fact rather than a promise is to remove the possibility of a palette command
that points somewhere the site does not otherwise go.

**The mechanism: the palette has no command list of its own.** Its index is
server-rendered from the *same* `NAV_GROUPS`/`_nav_links()` iteration the sidebar
and the bottom tab bar already render from (`layout.py:80-100`, `:1399-1422`),
plus the page-section anchors each page already emits. A command that points
nowhere is then impossible by construction, not merely unlikely — the same
argument 22-14 used when the bottom tab bar became "a third nav rendering fed by
the ONE shared `_nav_links()` iteration".

Two executable checks follow, and neither is vacuous:

1. **Source-level:** the palette index is built by the shared nav iteration; a
   second hand-written list of destinations in a page module or in the script
   fails the check. *What would a wrong implementation do?* Hard-code an array
   of `{label, href}` in `command-palette.js` — which the check greps for and
   fails.
2. **Browser-level, scripts blocked:** for every destination the server put in
   the index, a `context.new_page(java_script_enabled=False)` check asserts the
   destination is reachable by ordinary navigation and returns 200. *What would a
   wrong implementation do?* Add a palette-only destination (a route that exists
   only to be palette-reached) — which fails on the blocked-script page because
   nothing links to it.

### 2.4 State-changing commands: the CSRF question, answered by not opening it

23-RESEARCH.md records the posture: **`SameSite=Strict` session cookie
(`auth.py:263`) and no CSRF token anywhere.** A state change reachable by GET
would have no CSRF defence at all.

The audit's example commands are "switch screen off" and "red theme" — both
state changes. Three ways to have them:

| Option | Mechanism | Cost |
|---|---|---|
| **A (recommended)** | The palette **navigates, it does not act**. "Switch screen off" becomes "Display → Screen". Every command is a destination. | zero new routes, zero new POST surface, no-JS floor trivially true |
| B | Hidden mirror `<form>`s in the shell that the palette submits | a hidden POST form on every page, in an app with no CSRF token; and two renderings of one control to keep in sync |
| C | Action commands appear only on the page that already renders that form | works, but a palette that can only switch the screen off while you are already looking at the screen switch is not worth its own code |

**Recommendation: A.** Grounds: Phase 25 has just built the real controls
(switches, dial, slider, carousel); the palette's job is to get you to them in
one keystroke, not to become a second way to mutate config that must be kept in
agreement with the first. Recorded as a **deliberate deviation from the audit's
wording**, not a silent substitution. PROVISIONAL — see Open decision 1.

### 2.5 Accessibility: the traps, planned rather than discovered

A command palette has four well-known failure modes. Three of them the platform
already solves, and the fourth is where phase 23 already paid tuition.

| Trap | Resolution | Evidence |
|---|---|---|
| Focus escapes the palette | Native `<dialog>` + `showModal()` traps focus in the top layer. **Do not hand-roll a focus trap.** | `panel-lookup.js:280` already relies on exactly this; its comment at `:316-318` records that `<dialog>` was chosen over a hand-rolled overlay `<div>` *because* it provides this |
| Focus is not restored on close | `showModal()` restores focus to the previously-focused element natively. Assert it in the browser harness rather than assuming it | `test_browser_ux.py` has the harness; the assertion is new |
| Results are not announced | `role="listbox"` + `aria-activedescendant` on the input, and a **count-only** `aria-live="polite"` region that changes only when the *number* of results changes | Phase 23 learned this with its three switches: a `role="status"` region re-announces identical text on every keystroke. The palette types on every keystroke, so it is the worst possible place to repeat that mistake |
| Escape does not work | The native `cancel` event closes the dialog. **Never `preventDefault()` it.** A check asserts Escape closes the palette from the input, from a result, and with an empty query | new browser check |

Two more that are specific to shortcuts rather than to palettes:

- **`/` and `g` must not fire while the user is typing.** The handler returns
  early when the event target is an `<input>`, `<textarea>`, `<select>` or a
  `contenteditable` element, or when a modifier other than the palette's own is
  held. *What would a wrong implementation do?* Open the palette when you type
  "g" into the Airlines filter box — which the check drives directly.
- **`g h` is a chord with a timeout.** Bounded (1200 ms suggested) and stated;
  the second key is ignored after the window closes. This is the one timer this
  phase introduces, and it lives in the new file, not in `panel-lookup.js`
  (whose docstring pins "never introduce … a timer").

### 2.6 360 px: the honest answer about touch

**Keyboard shortcuts reach nobody on a phone, and no touch equivalent should be
invented for them.** The touch equivalent for navigation already shipped: the
bottom tab bar (22-14, `layout.py:2024`), five cells, present on every
authenticated page below 960 px. That is the answer for `g h/d/v/c`, and it is a
better one than a palette.

The palette itself is a different question, and an invisible feature is a feature
nobody uses. **Recommendation: a visible trigger** in the page header — a search
control that is present at every width, so the palette is reachable by touch and
by click, and so the harness can open it at 360 px without synthesising a
keystroke. The dialog must then meet the same obligations every other surface in
this app meets: fits 360 px, no horizontal body scrollbar, hit areas ≥ 44 px in
both axes measured in a real browser. PROVISIONAL — see Open decision 2. The
alternative is desktop-only with no trigger, which is defensible for a P3
power-user feature but should be *chosen*, not defaulted into.

---

## 3. D24 — guided first run and drawn empty states

### 3.1 The checklist item that cannot fail

The audit asks for: "password set ✓, frame paired, first wake received,
countdown".

**"Password set ✓" is vacuous as written.** `companion/auth.py:153` fails
**closed** when no password is configured — a missing password means nobody can
log in at all. Anyone who can see the checklist has, by construction, a password
set. A right implementation and a wrong one both render ✓. It fails the vacuity
question before a line is written.

There is a real check hiding behind it. `deploy/skypane.env.example:56` ships
`SKYPANE_COMPANION_PASSWORD=replace-with-a-long-random-secret`. "The shared
password is not the example placeholder" has a real failure state, a real
remedy, and real security value. **Recommendation: replace the vacuous item with
this one.** PROVISIONAL — see Open decision 3. (Note for the plan: the comparison
must be constant-time against the configured value and must never render the
configured password or any prefix of it — `test_companion_app.py` already pins
that `AuthNotConfigured` never leaks the password value, and this new surface
must not become the first place that does.)

### 3.2 "Frame paired" does not exist; the signal that does

There is **no pairing concept in the companion** — provisioning is BLE, in the
firmware, and the companion never sees it. The real, already-held signals are:

| Checklist item | Signal | Source |
|---|---|---|
| The frame has been set up | the shared password is not the example placeholder | `auth.configured_password()` vs `deploy/skypane.env.example` |
| The frame has checked in | `frame_state.resolve_state()` is not `STATE_UNKNOWN` — its docstring at `frame_state.py:158` literally names this state "no check-in recorded yet" | `companion/frame_state.py`, fed by `companion/wake.py`'s re-export of `server.wake.next_wake_status()` |
| A picture has been rendered | the gallery is non-empty | the same source the Home hero figure and `/gallery/` already read |
| Countdown | already shipped | the next-wake countdown / `relative-time.js` |

All three are **derived live**. That has three consequences worth stating
plainly, because they are what make this item cheap:

1. **No new persistence.** No "first run complete" flag, no new state file, no
   schema. The project has no SQLite migration mechanism at all (24-RESEARCH.md
   established this), and this item does not need one.
2. **No dismissal control and no `localStorage`.** The checklist disappears by
   itself the moment its last item goes true, because it is a function of state
   rather than a record of having been seen. 23-RESEARCH.md flagged that D23's
   palette and D24's checklist would be the first features in this codebase
   tempted to add client-side storage — "a second source of truth beside the
   server, and this app's whole discipline is server-authoritative state". This
   design declines the temptation rather than arguing with it.
3. **Zero scripts.** Entirely server-rendered, so it is complete in the first
   response and works with scripts blocked. A no-JS browser check asserts the
   checklist renders and its "next action" links navigate.

The check that earns its keep here is the **disappearance**: with all three
signals true the checklist must be absent from the HTML, not merely hidden by
CSS. *What would a wrong implementation do?* Render it always and hide it with a
class — which the check catches by asserting on the response body.

### 3.3 Drawn empty states

`layout.empty_state(heading, body, compact=False)` at `layout.py:3589` is already
the two-part block, already has a compact variant, and its docstring records the
contract any new parameter must honour: **a falsy value returns markup
BYTE-IDENTICAL to what the function returned before the parameter existed**, the
same contract `stat_tile()`'s `caption_title` and `status_dot()`'s
`visually_hide_label` carry. Two new keyword-with-default parameters (an
illustration and a next-action link) must be added the same way, and the check is
the one 22-12 already proved works: render an existing call site and assert the
output is byte-identical to the pre-change bytes.

Existing call sites (all must keep working untouched): `home_page.py` × 2,
`history_page.py` × 1, `data_table()`'s own no-rows fallback, `health_page.py`'s
battery-card and registry-card.

**The illustration must go through Phase 24's `companion/draw.py`.** 24-01
lands the drawing contract and its executable guard: every drawing takes its
colour from a theme token through a CSS class (`currentColor` + token, the
`.sparkline*` idiom), and *a colour literal, an unpainted shape, or a class that
resolves to no selector each fails that guard* — "a drawing correct only in light
mode is a defect, not a polish item". A hand-rolled `<svg>` with a stroke colour
in the empty-state helper would fail 24-01's guard, or worse, quietly become the
second drawing path that 24-01 exists to prevent.

This is a **cross-phase dependency the ROADMAP entry does not currently declare**
(it says "Depends on: Phase 23"). Execution order is 23 → 24 → 25 → 26, so in
practice `draw.py` will exist. The plan handles it as an **executable
precondition** — assert `companion/draw.py` exists and exports the emitter, and
fail loudly if not — rather than forking a second drawing path as a fallback. A
loud failure is recoverable; a silent second drawing module is the drift phase 24
was created to prevent. PROVISIONAL — see Open decision 4.

---

## 4. D15 — share the picture of the day, and its privacy answer

### 4.1 Why this needs a privacy answer before a design

Every page is session-gated and every HTML response is `Cache-Control: no-store`
by a deliberate Phase 18 decision (`app.py:1246`, `:1270`, `:1295`, `:1320`).
`/gallery/<name>` sits behind `do_GET()`'s `require_session()` gate
(`app.py:2098-2105`, and the comment there says so explicitly). Authentication
is **one shared password**, no per-user accounts (`auth.py:4`), 12-hour session
TTL.

"Sharing" in the ordinary web sense means a URL that someone who is not signed in
can open. Against this posture that is not a small feature — so state exactly
what the picture discloses:

- the set of flights departing ORY at that moment, which is public information;
- the frame's configured theme and layout, which is not sensitive;
- **and, since Phase 16, whether a flight matched the operator's connected
  calendar.** `server/plane/calendar_rules.py` parses the operator's iCal feed
  and `match_calendar_theme()` resolves a `calendar_theme_id` that repaints the
  panel. The *colour of the picture* therefore encodes "a flight in my calendar
  is departing now". That is a statement about the operator's own travel, derived
  from their private calendar, and it is the thing that makes a public picture
  URL a real disclosure rather than a theoretical one.

### 4.2 The answer: share the bytes, never a URL

**Recommendation: no unauthenticated endpoint is created, and no public URL comes
into existence at any point.** Sharing is done by handing the viewer the image
*bytes* they are already authorised to see:

| Path | Mechanism | Public URL? | Works with scripts blocked? | Machine-verifiable? |
|---|---|---|---|---|
| **Floor** | a plain `<a download href="/gallery/….png">` on the picture | **no** — the anchor resolves through the caller's own session | **yes** | **yes** |
| **Enhancement** | `navigator.share({files:[File]})` on a phone, the File built from the already-rendered `<img>` | **no** — the bytes go to the OS share sheet | n/a (hidden without `.js`) | partly — see §4.4 |

Answering the three questions the instruction asks, precisely:

- **What becomes publicly reachable?** Nothing. No route is added, no route loses
  its `require_session()` gate, and `no-store` is untouched.
- **For how long?** Not applicable — there is nothing to expire.
- **How is it revoked?** Not applicable — there is nothing to revoke. This is the
  substantive advantage over every token/expiring-link design: a shared *link* to
  a session-gated app would need a new unauthenticated route, a token store, an
  expiry policy, a revocation path and a test for each, and would put a
  calendar-derived signal behind a URL that can be forwarded. Handing over a PNG
  has none of that, and the recipient gets exactly what the operator chose to
  send them.

**An executable check makes this a property rather than a promise:** a check that
enumerates the server's GET dispatch and asserts the set of routes reachable
without a session is **unchanged** by this phase. *What would a wrong
implementation do?* Add a `/share/<token>` route — which the check fails
immediately. This check is worth having permanently, independent of D15.

### 4.3 Zero new scripts, and the constraint that decides where the code goes

`panel-lookup.js` already owns a native `<dialog>` lightbox showing the rendered
panel, on both History and the Airlines gallery, with `showModal()` at `:280` and
Escape handled natively. D15's "full-screen `<dialog>`" therefore **already
exists** — the work is adding controls inside it, not building it.

But that file carries a pinned standing constraint, in its own docstring at
`panel-lookup.js:14-17`: it *"must never introduce a network call, a timer, or
any persistent state"*. That rules out the obvious implementation
(`fetch(url) → blob → File`), and it is the kind of pin that should be respected
rather than amended for convenience.

**The way through: build the File from the image that is already in the DOM.**
The `<img>` is same-origin and already decoded; `canvas.drawImage()` +
`canvas.toBlob()` produces the bytes with **no network call, no timer and no
persistent state** — all three pinned constraints survive intact, and the plan
asserts they still hold rather than assuming it. Note honestly in the plan that
`toBlob` re-encodes, so the shared PNG is visually identical but not
byte-identical to the served file; for a picture being sent to a person that is
immaterial, and it is the price of not opening a network call in that file.

(This is not in tension with 25-07's refusal of a client-side canvas for D19.
That refusal's stated ground is that a *second, differently-thresholded
measurement* drifting from `illustration_normalize.py` is the defect. Here the
canvas measures nothing — it re-encodes bytes.)

So D15's script cost is **zero**: the floor is a plain anchor with no script at
all, and the enhancement grows a file that is already on every page.

### 4.4 The part no machine in this repository can check, named as such

23-RESEARCH.md verified that **`navigator.share` is `undefined` in the harness
Chromium**, and desktop Firefox has no support at all. The share branch has no
machine verification path in this repository. Rather than leave it unverified,
pin it **by its absence**: a named check asserts that when `navigator.canShare`
is unavailable the share control does not render, while the download anchor
does. That is a real assertion about the capability gate — the branch a wrong
implementation gets wrong is exactly the one where a dead button ships to every
desktop browser. The share sheet itself stays a **manual, real-phone**
verification item, listed as such in the phase gate.

---

## 5. D6 — is the manifest half worth building at all?

**Recommendation: build the `<meta name="theme-color">` half. Do not build the
manifest.** The reasoning, in the order it actually decides the question:

1. **The manifest's only real payoff is installability, and installability's
   prompt depends on the thing this milestone excluded.** Chrome's install
   criteria have historically required a service worker with a fetch handler —
   and D12 (service worker) is excluded entirely, correctly, because a service
   worker would persist authenticated `no-store` pages past sign-out. Shipping a
   manifest to obtain an install prompt that the excluded component is what
   enables is building the half that does not work. (Confidence: MEDIUM on the
   current exact Chrome criteria, which have been relaxing; the rest of this
   argument does not depend on it.)
2. **There are no icons, and 22-13 declined to invent one.** A manifest needs
   192 px and 512 px icons. This project has no brand mark — 22-13 deliberately
   declined the audit's own "small brand mark" suggestion (22-UI-SPEC.md §3.2).
   A manifest would force that decision as a side effect of a P2 leftover, which
   is the wrong way to make it.
3. **`theme_color` per theme cannot come from a static file.** D6 asks for
   "theme_color per theme" and there are eighteen themes chosen at runtime. That
   needs a dynamic manifest route, which needs the manifest fetch to carry
   credentials (`crossorigin="use-credentials"`, a known sharp edge behind
   auth) — a new route, a new auth interaction and a new failure mode, for a
   colour.
4. **The installed icon would open on a login screen.** A 12-hour session TTL
   against an app launched from a home screen means the standalone window
   frequently starts at `/login`. That is a worse first impression than a
   bookmark.
5. **`<meta name="theme-color">` has none of those problems and most of the
   visible benefit.** One line in the shell, emitted from the already-resolved
   active theme's own token, tints the browser chrome on Android Chrome and iOS
   Safari. It needs no icons, no new route, no manifest, no service worker, and
   it tracks the user's chosen theme because it is rendered per response like
   everything else. Two `media`-qualified variants cover light and dark.

So: **the manifest half is not worth building, the theme-color half is** — and
the theme-color half is small enough to ride along in the finishing plan rather
than earn one of its own. PROVISIONAL — see Open decision 5.

---

## 6. D11 — what is left, and what is structurally dead

D11's hashed-filenames third is already excluded by the ROADMAP entry (a build
step, forbidden by this milestone's framework-free/build-free constraint). Of the
two the entry leaves open:

### 6.1 Prefetch-on-hover is defeated by a decision this project made on purpose

Every HTML response carries `Cache-Control: no-store` (Phase 18, deliberate).
A prefetched response marked `no-store` **is not stored and cannot be reused** —
the browser fetches it and throws it away. Prefetch-on-hover against this app
would therefore produce a duplicate request to a single-threaded stdlib server
and **no speedup at all**. It would also need a script to insert the `<link>` on
hover, and hover is unreachable by touch (CFG-28's own ground).

**Recommendation: do not build it, and record the reason** so it is not
re-proposed a fourth time. The remedy would be to weaken `no-store` on
authenticated pages, which is a much larger decision than a navigation
optimisation is worth and which Phase 18 already took the other way.

### 6.2 gzip is real, is one line, and is not in the Python server

`deploy/Caddyfile` has **no `encode` directive** in either site block — verified
today. `companion/app.py` has no `Content-Encoding` handling either. Meanwhile
`companion/static/style.css` is **417 KB** and the scripts total ~190 KB, and all
of them are served *before* `require_session()` (static is exempt, `app.py:1685`)
— so they are public bytes with no secret in them.

**Recommendation: add `encode` to the companion's Caddy site block, scoped to
static asset types, and leave the Python server alone.** Compression belongs at
the edge that already terminates TLS; putting it in the hand-rolled
`ThreadingHTTPServer` would mean buffering, `Accept-Encoding` negotiation and a
`Vary` header in a file whose whole virtue is that it is small and obvious.
Scoping to CSS/JS also keeps **BREACH structurally out of scope** — no HTML
response, and therefore no response containing session-derived content, is ever
compressed. Expected effect: ~417 KB → roughly 40 KB on first paint.

Honest caveat: the check harness launches `companion/app.py` directly and never
runs Caddy, so this cannot be verified end-to-end here. The available check is a
file-content assertion that the directive is present **in the companion site
block specifically** — non-vacuous (a wrong implementation omits it, or puts it
in the device-protocol block, and the check distinguishes those), but weaker than
this project's norm. Say so in the SUMMARY rather than implying a runtime proof.

---

## 7. D12 — excluded, and the reason restated so it is not reopened

A same-origin service worker would cache the page shell and the last Home
response. Every one of those responses is an authenticated page served
`no-store`. A service worker would **persist authenticated pages past sign-out**,
on a device protected by one shared password. Excluded entirely (Phase 23's
decision), and nothing in this phase weakens the ground for it. The manifest
recommendation in §5 deliberately does not create a reason to revisit it.

---

## 8. Script budget for the phase, totalled

| Item | New scripts | Why |
|---|---|---|
| D23 palette + shortcuts | **1** | shell-wide, keystroke-driven, needs an index and a chord timer |
| D24 first run | 0 | server-rendered; the signals are all derived live |
| D24 empty states | 0 | server-rendered SVG through Phase 24's `draw.py` |
| D15 download floor | 0 | a plain `<a download>` |
| D15 share enhancement | 0 | grows `panel-lookup.js`, which already owns the lightbox |
| D6 theme-color | 0 | one line in the shell |
| D11 gzip | 0 | a Caddy directive |
| **Total** | **1** | pin 15 → 16, moved once |

23-RESEARCH.md predicted "six to eight new files" across D14/D2/D12/D15/D23/D16/
D17/D18. Phase 25 delivered five controls for one script; this phase delivers
three finishes for one more. The prediction was wrong in a good direction, and
the reason is the same both times: **the shipped platform primitives (`<dialog>`,
`<details>`, native form controls, server-rendered SVG) do more than the audit's
framing assumed.**

---

## 9. Validation Architecture

*(Nyquist: what must be sampled, at what rate, to know this phase is actually
working — not merely that its code exists.)*

**Signals that must be observed, and the rate each must be sampled at:**

| Signal | Why it can only be caught by sampling | Sampling method | Rate |
|---|---|---|---|
| Palette destination reachable without script | A palette-only destination looks fine in every scripted test and is a dead end for a no-JS user | `context.new_page(java_script_enabled=False)`, one navigation **per destination in the index** | every destination, every run — not a spot check |
| Shortcut fires while typing | Only observable on a page that has a text input AND a shortcut key that is an ordinary letter | drive the Airlines filter box and the palette input with `g`, `/`, `h` | 3 inputs × 3 keys |
| Focus restored after the palette closes | Passes visually and fails for keyboard users | record `document.activeElement` before open and after close | open/close × 3 entry points (trigger, `⌘K`, `/`) |
| Escape always closes | Fails only in specific sub-states (empty query, result focused) | Escape from input, from a result, with empty query | 3 states |
| Empty-state byte-identity for existing callers | A regression here is invisible until a page renders differently in production | render each of the 6 existing call sites, compare to captured pre-change bytes | all 6 |
| First-run checklist disappears | The failure mode is "renders always, hidden by CSS" — invisible to a visual check | assert absence **from the response body** with all signals true | 2 states per signal (8 combinations; at minimum all-true and each-one-false) |
| No new unauthenticated route | A single added public route defeats the entire D15 privacy answer | enumerate GET dispatch, diff the public set against the recorded baseline | every run |
| Share control absent without `canShare` | The wrong implementation ships a dead button to every desktop browser | harness browser has no `navigator.share`; assert the control is absent and the download anchor present | every run |
| 360 px, no horizontal body scrollbar | Only observable at the minimum viewport, in a real browser | measure `scrollWidth` vs `clientWidth` on the palette dialog open and on the first-run card | 360 px and 1280 px |
| Dark mode | Phase 24's harness helpers added a theme switch because the harness had never once measured dark mode | every new drawn surface measured in both themes | 2 themes |

**Aliasing risks (what a too-slow sample would miss):**
- Checking *one* palette destination instead of all of them samples below the
  rate at which a broken destination can be introduced — one hand-added command
  is the whole failure mode.
- Checking the empty state on *one* caller misses the five others, and the
  byte-identity contract is precisely a statement about all of them.
- Checking only light mode aliases out every token/colour defect, which is why
  24-01 declares a light-only drawing a defect rather than a polish item.

**Baseline discipline:** `EXPECTED_CHECK_COUNT` is re-derived by **running**, never
by arithmetic. The sandbox baseline is exactly **5** failing checks, verified by
check **NAME** (4 × WR-11 read-only, 1 × `anomaly_active()`), never by counting
failing files. Every check added by this phase is mutation-tested: revert the
implementation, confirm **exactly one** additional failure, and confirm it is the
new check by name.

---

## 10. Open decisions — all PROVISIONAL, none asked of the developer

The developer was unavailable and this run was instructed not to ask. Each of
these is a real fork with a real cost; each has a recommendation and a stated
reversal cost.

**1. The palette navigates; it does not act.** (§2.4)
Options: A navigate-only (recommended) · B hidden mirror forms in the shell · C
page-scoped action commands.
Reversal cost: LOW while the index is nav-derived — adding action commands later
means adding a form-submission branch to one script and mirror forms to the
shell. Reversing the other way (removing shipped action commands) is a visible
feature retraction.

**2. The palette gets a visible trigger in the page header at every width.** (§2.6)
Options: A visible trigger (recommended) · B keyboard-only, desktop-only, no
trigger.
Reversal cost: LOW. Ground for A: an invisible P3 feature is a P3 feature nobody
finds, and the trigger is what makes the palette testable at 360 px without
synthesising a keystroke. Ground for B: it is honestly a power-user feature and
the bottom tab bar already serves touch navigation.

**3. "Password set ✓" is replaced by "the password is not the example
placeholder".** (§3.1)
Options: A replace (recommended) · B drop the item entirely and ship a
three-item checklist · C keep it as written.
C fails the vacuity question outright and should not ship. Between A and B, A
adds real security value; B is smaller. Reversal cost: LOW either way.

**4. D24's drawn empty states hard-depend on Phase 24's `companion/draw.py`,
enforced as an executable precondition rather than a fallback.** (§3.3)
Options: A precondition check that fails loudly (recommended) · B a local
fallback emitter when `draw.py` is absent.
B is the drift 24-01 exists to prevent. Consequence to record: **the ROADMAP's
"Depends on: Phase 23" for this phase understates the real dependency** — it is
Phase 23 **and** Phase 24. Reversal cost: LOW now, HIGH once a second drawing
path ships.

**5. Build `<meta name="theme-color">`; do not build `manifest.webmanifest`.** (§5)
Options: A theme-color only (recommended) · B both · C neither.
B forces an icon/brand decision 22-13 deliberately declined and delivers an
install prompt whose enabling component (D12) is excluded. Reversal cost: LOW —
a manifest can be added in one later plan if the developer decides installability
matters, and nothing in A blocks it.

**6. Prefetch-on-hover is not built.** (§6.1)
Ground: `no-store` responses are not stored and cannot be reused, so it buys a
duplicate request and zero speedup; hover is unreachable by touch. The only way
to make it work is to weaken `no-store` on authenticated pages. Reversal cost:
LOW (nothing is built); reversing the *ground* means reopening a Phase 18
security decision.

**7. gzip is added at Caddy, scoped to static asset types, and is verified only
by a file-content assertion.** (§6.2)
Options: A Caddy, static-only (recommended) · B Caddy, everything including HTML
· C in `companion/app.py`.
B puts session-derived HTML into a compressed channel (BREACH) for no benefit
this app needs. C adds negotiation and buffering to a deliberately small
hand-rolled server. Honest caveat: A's check is weaker than this project's norm
and must be reported as such.

**8. D15's share enhancement builds its File from the already-rendered `<img>`
via canvas, to preserve `panel-lookup.js`'s pinned "no network call" constraint.** (§4.3)
Options: A canvas re-encode (recommended) · B `fetch()` in `panel-lookup.js`,
amending its pinned docstring · C a new dedicated script (+1, taking the phase
to two).
Cost of A, stated: the shared PNG is visually identical but not byte-identical to
the served file. Reversal cost: LOW.

---

## 11. Risks and anti-patterns specific to this phase

| Risk | Why it is likely here | Defence |
|---|---|---|
| The palette becomes a second navigation source of truth | Every palette implementation on the internet ships a hand-written command array | The index is built by the shared `_nav_links()` iteration; a source-level check fails a hand-written list |
| A hand-rolled focus trap | Every palette tutorial hand-rolls one | `<dialog>` + `showModal()`; `panel-lookup.js:316-318` already records why |
| A `role="status"` region announcing on every keystroke | The palette types constantly; this is phase 23's exact lesson in its worst setting | `aria-activedescendant` + a **count-only** live region |
| `localStorage` creeping in | 23-RESEARCH.md predicted D23/D24 would be the first to reach for it | The checklist derives from server state; the palette holds no state between opens |
| An empty-state illustration with a colour literal | The fastest way to draw an icon is to type `#888` | 24-01's guard; a light-only drawing is a defect, not a polish item |
| A "share" that quietly becomes a public URL | It is the ordinary meaning of the word | A check that the set of routes reachable without a session is unchanged |
| Sticky day headers reappearing | Struck twice already | Not in scope; every flight row already carries its date |
| The overlay drawer reappearing | Refused three times, plus locked decision D-10 | The bottom tab bar is the shipped answer; the palette is a `<dialog>`, not a drawer |

---

## 12. Sources

- `companion/app.py`, `companion/layout.py`, `companion/auth.py`,
  `companion/frame_state.py`, `companion/screens.py` — read directly, 2026-09-13
- `companion/static/panel-lookup.js`, `nav-dropdown.js`, `copy-button.js`,
  `style.css` — read directly
- `companion/test_companion_app.py` (`:3723`, `:4398`, `:4431`),
  `test_browser_ux.py`, `test_i18n.py`, `test_status_pages.py`,
  `test_config_page.py` — the machine-enforced contracts, read directly
- `deploy/Caddyfile`, `deploy/skypane.env.example` — read directly
- `server/plane/calendar_rules.py`, `server/device_config.py` — the
  calendar-theme path that gives §4.1 its teeth
- `.planning/phases/22-…/22-AUDIT.md` — the D-item definitions (D6, D11, D12,
  D15, D23, D24)
- `.planning/phases/23-…/23-RESEARCH.md` — `navigator.share` undefined in the
  harness; the three-tax cost of a script; the localStorage warning; the CSRF
  posture
- `.planning/phases/24-…/24-RESEARCH.md`, `24-01-PLAN.md` — the drawing contract
  and its guard; the no-migration finding
- `.planning/phases/25-…/25-RESEARCH.md`, `25-01-PLAN.md` — the one-script
  budget, the `.js` gate vocabulary, the executable no-JS control contract
- `.claude/skills/sketch-findings-skypane/` — the design authority; the standing
  refusals (overlay drawer, sticky day headers)
