# Requirements: SkyPane

**Defined:** 2026-08-04
**Core Value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Plane (Runway 3)

- [x] **PLANE-01**: User can see flight number, airline, and destination for the next plane departing from Orly runway 3
- [x] **PLANE-02**: User can see flight number, airline, and origin for the next plane landing on runway 3 (when the runway is in arrival configuration, wind-dependent)
- [x] **PLANE-03**: Plane view updates one flight at a time, as real aircraft use runway 3, detected via free public ADS-B aggregator APIs (adsb.fi, adsb.lol) geofenced to the runway's flight path — not a fixed timetable

### Device

- [x] **DEVICE-03**: Device wakes on a schedule, polls the server over HTTPS, downloads and displays a new image if available, then returns to deep sleep, with exponential backoff on failure
- [x] **DEVICE-04**: User can see a low-battery indicator on the frame when the battery is running low
- [x] **DEVICE-05**: Device runs on battery power only (no wall power, no solar) for v1

### Companion Configuration Web Interface

Promoted 2026-08-27 from the v2 backlog to Phase 6 (see ROADMAP.md) — selected by the user over four sibling seeds (AeroDataBox destination lookup, local RTL-SDR backup, presence-adaptive poll cadence, and the standalone device-local fault-icon fallback DEVICE-06, which stayed deferred in v2 below until quick task 260924-u7n shipped it on 2026-09-24). Originated 2026-08-26 (`/gsd-discuss-phase 3`) as an unscoped seed idea, then expanded across two 2026-08-27 explore sessions to also cover view switching, device health/battery status, airline-coverage monitoring, and a server-side fault icon — rather than three separate mechanisms (a button, a push channel, and manual log-grepping).

**Scope widened again during `/gsd-discuss-phase 6` (2026-08-27):** CFG-02 (view switching) was removed from this phase — there's still nothing to switch to until a second view exists, so it moved back to v2's "View Switching" section below. In its place, the user asked to add seven new capabilities to this same phase: a flight-history log, a manual poll trigger, airline-resolution statistics, a dark/light theme for the page itself, a live render preview, a gallery of recent renders, and runway selection (CFG-06 through CFG-12 below — CFG-12 was raised mid-discussion, after the rest of this section was already written). See `06-CONTEXT.md` for the full discussion record.

- [x] **CFG-01**: User can configure the frame's settings (background colors/style, tracked airport, other display preferences) via a web interface, instead of every visual choice being fixed at build time. For v1, background-color configuration is scoped to choosing among DEPARTING/ARRIVING theme variants validated on real glass during Phase 7 — see `06-CONTEXT.md`.
- [x] **CFG-03**: User can see the device's last-known health status (last successful poll time, battery voltage once wired per Phase 5's DEVICE-04) via the web interface — deliberately not a phone push notification, to avoid reintroducing a phone dependency for an ambient device
- [x] **CFG-04**: User can see which ADS-B callsign ICAO prefixes have gone unrecognized in production, backed directly by `enrich.py`'s unresolved-prefix registry (`poll_state.json`'s `unresolved_prefixes`, added 2026-08-27) — surfaces airline-coverage gaps from real traffic instead of requiring another manual research audit
- [x] **CFG-05**: When the server's ADS-B data source itself is failing (not the normal "no aircraft right now" Empty state), the next successfully-rendered image includes a small alert icon prompting the user to check the web interface (CFG-03) for details — full design rationale in `.planning/seeds/on-device-fault-icon.md`
- [x] **CFG-06**: User can see a log of recently detected flights (not just the current one), via the web interface
- [x] **CFG-07**: User can manually trigger an immediate detection/render cycle from the web interface, for debugging without waiting for the next scheduled cycle — rate-limited (short cooldown) to avoid abusing the free ADS-B aggregator APIs
- [x] **CFG-08**: User can see airline/route resolution statistics over time via the web interface, beyond CFG-04's raw unresolved-prefix registry
- [x] **CFG-09**: User can toggle a dark/light theme for the web interface itself, independent of the colors rendered on the physical frame
- [x] **CFG-10**: User can see a live preview of what the physical panel is currently displaying, via the web interface, without needing SSH access to the server
- [x] **CFG-11**: User can see a gallery of the most recently rendered panel images via the web interface, for quick visual QA without SSH
- [x] **CFG-12**: User can select which of Orly's three runways the device tracks (currently hardcoded to runway 3; the two neighboring runways, 06/24 and 02/20, already have corridor geometry in `server/plane/detect.py` — added by the runway3-false-positive fix, currently used only to *exclude* their traffic). Generalizes PLANE-01/02/03's runway-3-specific detection to be parameterized by the selected runway. One runway tracked at a time, applied on the device's next scheduled poll (same timing as CFG-01).
- [x] **CFG-13**: User can switch the companion between French and English from any page (per browser); every user-visible string, date and script-driven text follows the choice, with English as the source language and a completeness check keeping the French catalogue in step
- [x] **CFG-14**: Home is a glanceable page — the current picture, one status card (frame, battery, flight data, next wake) and the recent flights — with no quick-action widgets on it
- [x] **CFG-15**: Display carries every everyday setting (theme, flight colours, calendar, runway, screen on/off with an instant switch, quiet hours with an instant switch), with the calendar and flight-colour rules redesigned for a non-technical user; Device keeps only hardware, data and diagnostics
- [x] **CFG-16**: The theme picker shows a live preview of the selected theme rendered with the last real flight, following the selection
- [x] **CFG-17**: User can receive a push notification (ntfy-style topic) when the battery goes low or the frame stops checking in, and when each condition clears — sent once per transition from the poll loop
- [~] **CFG-18**: ~~User can enable a simple mode (per browser) that hides the Advanced pages and every advanced affordance while keeping the everyday pages fully usable~~ — delivered in phase 20, then withdrawn by the developer's feedback ("à quoi sert le toggle simple/complet ?"); superseded by CFG-23 (phase 21)
- [x] **CFG-19**: The two everyday frame controls (Screen on/off, Quiet hours) and the next update time sit in a "Frame" strip at the top of Home and of Display, with a state-only reminder in the nav; Home is the strip, the three separate tiles Frame / Battery / Flight data, then the frame picture and the recent flights side by side
- [x] **CFG-20**: One "Frame colours" view on Display replaces the four theme chip grids: live preview on the left, a four-row assignment list (Departures, Arrivals, Calendar flights, Per-flight rules) on the right, one chip grid for the selected row, "Same as departures" for arrivals and calendar, the rule list and add form under the rules row; still saveable without script
- [x] **CFG-21**: The Calendar card holds status and feed URL together; once connected, "Replace the feed URL" is a plain link and "Disconnect" a small grey secondary button that still confirms
- [x] **CFG-22**: The Flights table fits a 1280 px desktop with no horizontal scroll in either language, with the hex, ISO timestamp, runway and copy button moved to an expandable detail row
- [x] **CFG-23**: The simple/full mode switch, its route and cookie, every gate it drove, and the Health "Pause updates" button are removed
- [x] **CFG-24**: Naming an unrecognised airline on Airlines offers the picture upload again without the "Change pictures" toggle, which keeps only replace/delete of existing artwork
- [x] **CFG-25**: Every setting on Display can be saved from a browser with JavaScript on — the save bar appears whenever any field changes, the fallback Save stays reachable until it does, and a browser-level test harness exercises the interactions the string-comparison harnesses cannot see
- [x] **CFG-26**: The frame's state reads the same everywhere — one quiet-hours- and screen-off-aware "next wake" estimate feeds the strip, the status tiles and the settings captions, with a grace window before any warning, so a frame that is deliberately asleep is never reported as late
- [x] **CFG-27**: Each frame setting has one control and one stated delay — the Frame strip owns Screen on/off and Quiet hours on/off, the settings form keeps only the quiet-hours schedule, and one computed sentence says when a change reaches the frame
- [x] **CFG-28**: Every visible time is Paris local time, including the battery readout and its chart, every tooltip, and the airline resolve dialog; raw ISO appears only behind a copy control
- [x] **CFG-29**: No English leaks into the French interface — flash banners, page titles, plurals and attribute text are translated, and the completeness harness covers the places it currently cannot see
- [x] **CFG-30**: The everyday pages are visually correct and honest — the login card, the Frame strip cells, orphaned controls, the runway grid on a phone, the nav state reminder, the filter Clear, the French table overflow, the Device fields, the theme preview crop, and the Health cards that render empty or contradict themselves
- [x] **CFG-31**: The stylesheet and scripts hold the design contract — the serif boundary, the accent reservation, hover and focus states on every interactive element, and the verified defects (permanently suppressed leave-guard, Disconnect styled as the primary action, missing disclosure markers, non-sticky table headers, save bar overlapping page content)
- [x] **CFG-32**: Motion is budgeted, not sprinkled — every animation duration comes from one of two shared tokens, every animation has exactly one keyframes definition, no animation names a keyframes block that does not exist, and the whole budget is switched off by `prefers-reduced-motion: reduce` (including pseudo-elements the global `*` selector cannot reach)
- [x] **CFG-33**: Moving between pages is a transition, not a flash — native cross-document view transitions, with per-route transition-name uniqueness proven in a real browser, degrading to an ordinary navigation where unsupported
- [ ] **CFG-34**: Every relative age on screen is live — a `<time data-relative>` server convention, one script ticking them each second, visibility-aware, with the ages that deliberately stay static enumerated rather than forgotten
- [x] **CFG-35**: Home and the Frame strip refresh themselves without stealing the page — a per-page refresh registry that skips a swap when the user holds focus, when an action is pending, or when a form is dirty
- [x] **CFG-36**: Screen, Quiet hours and LED are real switches — flipped over `fetch` with optimistic state and rollback on error, the absent-field semantics fixed first so a partial write can never silently disable a setting, and the underlying form still works with scripts blocked
- [ ] **CFG-37**: The flights list is alive — a new detection arrives visibly, the detail row opens and closes with measured motion, and the filter count moves with its list
- [x] **CFG-38**: The browser harness can express this phase — a no-JS helper, a 360 px viewport constant, and a disclosure sweep that stays honest once the pages animate
- [ ] **CFG-39**: One battery estimate and one drawing contract sit behind every picture in this phase — the five drawings share a single battery estimator and a single SVG drawing module (scale, geometry, label placement, colour binding), and the chart contract is enforced by a machine rather than a reviewer: one scale places marks, ticks and labels together; every axis label names a value the drawing actually reaches; every drawn shape carries an explicit fill; no colour literal appears in emitted SVG; and where a `viewBox` exists it contains its own outermost labels
- [x] **CFG-40**: The battery reading is drawn, not only written — a ring gauge rendered server-side from the shared estimator, large on Health and small in Home's battery tile, emitted by ONE function called twice rather than two similar functions, legible in both themes and at 360 px
- [x] **CFG-41**: The battery chart earns its canvas — a filled area under the line, an explicitly marked last point, and a drawn low-battery threshold the latest reading is judged against, added without losing the existing no-`viewBox` percentage-coordinate scheme, the per-point keyboard path, or the daily-average/raw-readings fallback
- [ ] **CFG-42**: Home shows the day the device has had — a 24-hour timeline rendered server-side from `history.db` (check-ins, the held quiet-hours window, detections), readable with scripts blocked and at 360 px
- [x] **CFG-43**: Punctuality is reported only as far as the stored data can prove it — the grid is computed from observed check-in gaps judged against the cadence in force, states in its own caption what it measures and what it cannot know (a rotated-away log range is not a missed wake), and no plan assumes an expected-interval history that this project does not store
- [x] **CFG-44**: Home gains a hero the other drawings feed — one composition assembled from the same emitters this phase defines elsewhere, never a second copy of any of them
- [x] **CFG-45**: The phase's regression floor — every drawing renders with scripts blocked, fits 360 px with no horizontal scrollbar on the page body, takes every colour from the theme tokens so it reads in BOTH themes, spends only from the existing motion budget, and the design system is updated in step
- [x] **CFG-46**: The no-JS control contract is executable, not promised — the server renders every submitting control unconditionally, the enhancement writes into it and never holds the value, an affordance that cannot work without script does not render without script, and a machine fails the build when any of those is violated; the whole phase spends ONE new static script, whose three taxes (the deferred-script pin, the French catalogue, the route and forbidden-sink guard) are paid once
- [x] **CFG-47**: The runway is picked on one drawn map of Orly — the three strips are the same native radios, so selection, arrow-key navigation and saving all work with scripts blocked; the map's bearings derive from the designators already in the registry, so the drawing cannot contradict its own labels; every strip is a real touch target at 360 px, measured — **RETIRED (Phase 27, 2026-09-14).** Met as worded by 25-03 and ticked on that evidence; then WITHDRAWN as a product decision, which is a different fact from "not met" and must not be collapsed into one. The developer, reviewing the deployed app: *"Je comprends pas l'intérêt de ces cartes des pistes, elles représentent la même chose que mes schémas."* The drawn map is removed by Phase 27 (CFG-66); the three native radios return to being the control, and the three `runway-*.png` photographs stay served. The tick is left standing because the work it records really was done — what is retired is the REQUIREMENT, so that no ticked row points at deleted code.
- [x] **CFG-48**: Quiet hours are set on a 24-hour dial whose arc is drawn by the server, so the window is visible with scripts blocked and only the drag handles are withheld — the two native time fields stay visible and stay what the form posts, B14's visible 24 h sibling survives, the window that wraps midnight is measured as the short way round, and the handles announce through `aria-valuetext` rather than a live region that re-reads on every step
- [x] **CFG-49**: The wake interval is steered by a slider whose two gauges tell the truth — freshness stated as a bound ("at most N minutes"), battery life stated only as far as this device's own observed history supports, with a named "not enough history yet" state instead of a figure invented from a per-wake cost nobody has measured; the number input remains the only thing that posts, and its out-of-range guard still protects the whole Settings form
- [ ] **CFG-50**: The theme picker folds — a scroll-snap carousel over the one existing chip grid with the full set behind a native disclosure that opens with scripts blocked, judged by Display's MEASURED page height rather than by the carousel's existence, with the stylesheet's single `:has()` feature query still single and the compact chip still size-only
- [x] **CFG-51**: Artwork can be dropped onto the card, and dropping it is provably the same act as choosing it — the file input still posts, the server's normaliser is still the only thing that decides how an illustration is framed, and the preview shows the chosen file inside that frame rather than reimplementing the crop
- [ ] **CFG-52**: The phase's regression floor for controls — every control is proven by SAVING with scripts blocked rather than by rendering, is operable from the keyboard with no pointer event at all, meets its touch floor measured at 360 px, reads correctly in both themes, spends only from the existing motion budget, and the design system is updated in step
- [~] **CFG-53** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The command palette costs ONE new static script and cannot become a second navigation source of truth — its index is emitted from the same `_nav_links()`/`_nav_groups()` iteration the sidebar and the bottom tab bar already consume, so a command pointing at a destination the site does not otherwise have is impossible by construction; the palette navigates and never acts, adding no POST surface to an app whose CSRF posture is `SameSite=Strict` with no token; the shell's deferred-script pin moves once, re-derived by running; and the trigger is revealed under `.js`, never hidden by it
- [~] **CFG-54** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The palette is operable and announceable — focus is trapped and restored by the platform's own `<dialog>.showModal()` rather than by a hand-rolled trap, Escape always closes (from the input, from a highlighted result, and with an empty query), results are announced through `aria-activedescendant` plus a live region carrying only the result COUNT and never re-set to a value it already holds, results are written with `textContent` alone, and the whole thing fits 360 px in both themes reusing the existing `<dialog>` entrance
- [~] **CFG-55** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): Keyboard shortcuts never steal what the user is typing and never outlive their chord — one named guard covers input, textarea, select, contenteditable and modifier keys, the `g` chord expires on a named bounded window, destinations are resolved from the server-rendered index rather than typed into the script; every destination the palette offers is proven reachable with scripts blocked, per destination and every run; and the touch equivalent is named honestly as the bottom tab bar shipped in 22-14, with no second gesture mechanism invented
- [~] **CFG-56** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The guided first run reports three signals that can actually fail, derived live — the shared password is not `deploy/skypane.env.example`'s placeholder (compared in constant time, with neither the value nor any prefix of it ever rendered), the frame has checked in (`frame_state.resolve_state()` is not `STATE_UNKNOWN`, the one existing definition), and a picture has been rendered; it adds no script, no state file, no schema and no client storage, and it DISAPPEARS from the response body when complete rather than being hidden by CSS
- [~] **CFG-57** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): Every empty list is drawn, says one sentence, and names a next action that is a real destination — the illustrations are emitted through the one drawing module (`companion/draw.py`) so none carries a colour literal and every class resolves in both themes, each SVG carries its own size, `empty_state()`'s new parameters return byte-identical markup for all six existing callers, Health's two tiles keep the compact variant, and an action pointing at the page the reader already occupies renders as a span with no href
- [~] **CFG-58** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The picture of the day can be shared without anything becoming publicly reachable — no route is added, none loses its session gate, no HTML response stops being `no-store`, and the executable proof is that the set of routes reachable WITHOUT a session is unchanged; the floor is a plain `download` anchor resolving through the caller's own session and works with scripts blocked, the native share sheet is a capability-gated enhancement built from the already-rendered image with no network call, and the share control is absent wherever the capability is
- [~] **CFG-59** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The app tints the browser chrome to the frame's own theme via `<meta name="theme-color">` driven by the resolved theme's token, and the `manifest.webmanifest` half is deliberately NOT built, with its five grounds recorded in the code — the install prompt depends on the service worker D12 excluded, there are no icons and 22-13 declined a brand mark, `theme_color` cannot track eighteen runtime themes from a static file, a manifest behind auth needs `crossorigin="use-credentials"`, and an installed icon on a 12-hour session would frequently open on the login page
- [~] **CFG-60** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): Static assets are compressed at the edge and nothing session-derived is — the `encode` directive lands in the companion's Caddy site block only, scoped to public static asset types served before `require_session()`, so BREACH is structurally out of scope rather than argued away; and prefetch-on-hover is deliberately NOT built because `no-store` responses cannot be reused, making it a duplicate request with zero speedup, with hover unreachable by touch and the only fix being to weaken a Phase 18 decision
- [~] **CFG-61** (DROPPED 2026-09-23 — Phase 26 abandoned before execution, never built): The phase's instrumentation floor — focus restoration is observed rather than cited, an announcement is read back as text so a repeat is detectable, the unauthenticated-route set is enumerable so a new public route is detectable, a keystroke can be aimed at a named element with proof it landed there, and the destination sweep visits every destination rather than a sample; the helpers add zero net checks
- [x] **CFG-62**: The quiet-hours dial tells one story — the arc and the caption are functions of the PAIR of values, not of one value per handle, so that after a drag or a preset the fields, the handles, the arc and the caption all describe the same window; the server-rendered arc stays authoritative for the SAVED value so the picture is still correct with scripts blocked, script only ever overrides what is already right, and a caption that cannot state a true duration says NOTHING rather than a stale one
- [x] **CFG-63**: The settings pages have no save button — a change saves itself, confirmed by a transient "Sauvegarde…" → "Sauvegardé" and nothing else; the failure path reuses the app's ONE existing failure vocabulary (the optimistic rollback and the translated generic toast the `role="switch"` controls already use) rather than inventing a second, the three instant switches and the settings form end up under ONE stated save model rather than two, and the leave-guard and "Annuler" are retired only where they mean "discard a pending edit" and kept where they confirm a destructive act — **RETIRED (Phase 28, 2026-09-16).** Met as worded by 27-04 and ticked on that evidence; then WITHDRAWN as a product decision, which is a different fact from "not met" and must not be collapsed into one. The developer, after testing the deployed silent auto-save on real Safari (iPhone and Mac) and confirming via the network tab that saves DID succeed (204) even though nothing ever visibly confirmed it: *"Mais ce n'était pas le comportement d'enregistrement qu'on a choisi. Je veux garder la pop up qui apparait et qui propose d'enregistrer... la barre qui apparait quand un changement de paramètres à été effectué et qui propose de sauvegarder... le comportement d'avant."* Confirmed explicitly, when asked whether real Enregistrer/Annuler buttons should return: *"Oui, avec les boutons Enregistrer/Annuler comme avant."* The pre-27-04 dirty save bar (native form POST, section-naming, Cancel with live-preview refresh) is restored by the successor requirement. The tick is left standing because the work it records really was done — what is retired is the REQUIREMENT, so that no ticked row points at removed behavior.
- [x] **CFG-64**: The no-JS floor survives the save button's removal BY CONSTRUCTION — the native submit is emitted on every render with no condition of any kind on its presence, script only hides it, and the proof is a value read back OFF DISK after a real form submit with scripts blocked, in both shipped languages and at 360 px, never a check that the button rendered; B1/P0's superseded `[data-static-save-fallback]` visibility contract is amended in writing where it lives, not deleted — **AMENDED IN FRAMING (Phase 28, 2026-09-16), NOT retired.** Its substance is unaffected by CFG-63's retirement and remains fully true and load-bearing: the native submit is still emitted unconditionally on every render (proven at the AST level by 27-03), and the value is still provably read back off disk with scripts blocked. Only the framing sentence "survives the save button's removal" becomes historically odd once the save button returns — the successor requirement now additionally makes this SAME native submit the restored bar's own visible Save control (no second button, no CSS `.js`-hide rule any more), rather than a script-hidden fallback distinct from it.
- [ ] **CFG-65**: There is one title form on the settings pages — both shapes are inventoried by a machine and their counts stated BEFORE the choice is made, the chosen form is applied everywhere it applies, and the check asserts the losing form's count is ZERO rather than asserting the winner exists
- [x] **CFG-66**: The runway is picked with the three native radios again — D16's drawn map, its constants, its stylesheet rules and the standing checks that assert its classes and geometry are all removed and NAMED as removed; the three `runway-*.png` photographs, their route and their slot stay served; the radios' own scripts-blocked save-to-disk proof stays and still passes; and CFG-47 is retired in place with its reason rather than left ticked against deleted code
- [x] **CFG-67**: The explanatory text is cut without weakening a refusal — the wake-interval caption, its two gauges and the Quiet hours paragraph are shorter, measured as a character count against a recorded baseline, while the honesty contract they carry is unchanged: with a battery history that cannot support an absolute figure the card still prints NO figure, and shortness and refusal are asserted about the SAME rendering rather than separately
- [x] **CFG-68**: Every colour grid folds the same way — the carousel wraps the arrivals and calendar grids as well as departures, "Voir tous les thèmes" sits BELOW the strip in the one shared wrapper, each carousel carries its OWN strip id so no two elements share one and every pager drives its own strip, and Display's page height is reported at 390 px against a figure this phase STATED before it measured
- [x] **CFG-69**: The Frame strip's Quiet hours cell links to the schedule fields, written ONCE in the shared component so Home and Display both get it from the same write site and neither is forked
- [x] **CFG-70**: Two findings carried in from earlier phases are closed rather than re-deferred — the "Departures · Arrivals" legend stops naming two swatches that the registry never makes different (asserted as a relationship against the registry, so it self-corrects if a theme ever does differ), and `.copy-btn`'s 34×26 hit area meets the 44 px floor measured in its own container, together with `.row-toggle`, which reuses its values verbatim
- [x] **CFG-71**: The phase's instrumentation floor is its own lesson made executable — ASSERT RELATIONSHIPS, NOT JUST ENDPOINTS: where several rendered surfaces are functions of one underlying value, ONE check decodes every surface to one canonical value and asserts the set has exactly one member, that the member is what the interaction requested and that it differs from what was there before; every check is mutation-tested with its failure message quoted, every `EXPECTED_CHECK_COUNT` is re-derived by RUNNING, and the phase adds no new script and no new route so the deferred-script pin stays at 15
- [ ] **CFG-72**: A settings card's own title renders in ONE typographic form regardless of which settings page hosts it — Device's cards are wrapped in the same nested-supersection style Display's already are, measured by `getComputedStyle` (font-size, weight, family) on every such title across both pages and asserted equal, not by grepping markup for a shared class name
- [ ] **CFG-73**: The quiet-hours dial is correct THROUGHOUT an interaction, not only before and after it — (a) after a drag, a keyboard step, a typed field edit or a preset click, the caption states both endpoints as HH:MM and a correctly recomputed duration, byte-for-byte matching the format the server emits at load, proven by reading the caption's actual displayed text after each interaction kind rather than by the existence of a formatting function; (b) the handle stays on the dial's own ring for the FULL DURATION of a press or drag, proven by sampling its resolved position against the dial's centre and radius while held rather than only at rest — the collapse toward the centre is a CSS specificity collision (`button:active`'s generic depress transform beating the handle's own positioning transform, both class-level specificity, the generic rule winning by source order and animating there via the shared `transition: transform`) and not the angle/pointer math, so the fix gives the positioned handle's own active state precedence without touching the value it reports, and extends to the wake-interval slider's handle, which shares the same base class and is subject to the identical collision
- [ ] **CFG-74**: A settings save failure is never silent and never permanent — investigated live by the developer across iPhone Safari and Mac desktop Safari and CONFIRMED SEVERE: no setting on ANY settings page (Display or Device) currently saves via auto-save in real Safari, with no visible error and no way to retry — a regression from Phase 27's removal of the manual save button that a Chromium-only harness cannot see (its own `_click_control()` helper already documents that a real coordinate click doesn't land reliably on these controls). Thorough code review of `dirty-state.js`, the toast element and its CSS found no incompatibility, and the exact root cause could not be confirmed without a live WebKit debugger, unavailable in this project's development environment — **this requirement does not claim to have found and fixed that root cause.** It requires resilience regardless of cause: (a) the save status is visible independent of scroll position (fixed/sticky, not tied to page-header position); (b) any save failure — non-204 response, opaque redirect, thrown exception, or a save that never resolves within a bounded timeout — surfaces a real, actionable retry affordance that appears ONLY on genuine failure and is invisible otherwise, honoring the developer's standing "zero buttons" preference; (c) the runway radios' `form=`-attribute wiring is additionally proven by its own check against the same pass/fail contract every other control meets, closing a path Phase 27's checks did not specifically cover; and (d) if the executor's own live-Chromium testing while building (a) and (b) surfaces a genuine, reproducible defect in the save pipeline along the way, it is fixed and named as a real root-cause fix, not folded silently into "resilience" — **SUPERSEDED before implementation (2026-09-16), never built.** This requirement's own text names its own root cause: "a regression from Phase 27's removal of the manual save button." With that button restored (CFG-77/CFG-78), the resilience machinery this requirement specified — a fetch-timeout, distinguished async failure kinds, a conditional retry affordance — has no fetch left to wrap, since the settings form goes back to a real native POST whose success or failure is unambiguous by construction (a real page navigation, not an async call that can fail silently). Left unticked rather than retired-as-met, because nothing here was ever built: the real Chromium data captured while the developer WAS testing the silent auto-save (a genuine 204 success with zero visible confirmation) is what led directly to the reversal, and stands as this requirement's own evidence for why "resilience around a silent mechanism" was the wrong fix for the symptom it correctly diagnosed.
- [x] **CFG-75**: Every theme carousel's live preview follows the scroll position — while scrolling or swiping, the preview image updates to match whichever chip is currently centered in the strip, without changing the SELECTED theme (no radio state change, no persisted setting change) until an actual click or keyboard-select commits it; every carousel instance (departures, arrivals, calendar) tracks its own preview state independently, preserving 27-07's per-instance `strip_id` discipline, proven by asserting the preview `<img src>` actually matches the geometrically centered chip during a scroll rather than by a scroll listener merely being attached
- [x] **CFG-76**: The mobile nav toggle's icon matches what it opens — `#site-nav-toggle` renders a gear glyph instead of the hamburger, with its `aria-label` and the account/preferences panel it opens unchanged, and no other icon in `ICON_IDS` collides with the new gear symbol
- [x] **CFG-77**: The settings pages have exactly one save mechanism, restored to its pre-Phase-27 form at the developer's explicit, twice-confirmed request — a bar that appears when a settings field changes, names which section(s) changed (in document order, from the same `data-dirty-section` wrappers that survived Phase 27 unread), and offers real "Enregistrer"/"Annuler" actions; Enregistrer is a genuine native form submission (never a fetch), so its result is a real page navigation whose success or failure is unambiguous by construction; Annuler restores every field via `form.reset()`, re-triggers the quiet-hours dial's own click-delegated repaint and the theme carousel's `window.SkyPaneLivePreview.refresh()` so neither control keeps showing a discarded value, and does not disarm the leave-guard permanently; the leave-guard itself is kept exactly where CFG-63's own carve-out already put it — confirming a pending, uncommitted edit, not a destructive act
- [x] **CFG-78**: The restoration leaves exactly one save affordance in the DOM, never two — the already-existing, AST-provably-unconditional native submit CFG-64 depends on becomes the bar's own visible Save control rather than a second button living behind a `.js`-hide rule, so the no-JS floor and the restored bar are proven to be the SAME element under two rendering conditions, not two independent implementations that could drift; the runway radios' `form=`-attribute cross-tree wiring is proven under the restored bar by its own check (closing the path CFG-74(c) named before the reversal); and the phase's closing gate re-derives every check count by running, names the sandbox baseline by NAME, and states plainly which of CFG-74's original four clauses were genuinely built (none) versus superseded by this pair
- [x] **CFG-79**: The whole site meets one editorial floor, except Display's Aspect section (Phase 30's) — under a card title, one sentence of at most ~12 words with no mechanism clause and no reason clause; "applies at the next wake" is said in one place per page (the Frame strip / save bar) and never repeated under a card; anything longer lives in the existing "How it works" disclosure or is deleted; the runway card's stale schematic clause (describing the map CFG-66 removed) is gone in both languages (cut in quick task Lot A, re-asserted here); enforced by a harness check measuring RENDERED caption length on every authenticated route in both languages, mutation-proven against a deliberately long caption
- [x] **CFG-80**: Quiet hours is one visual object — Start and End on one line as one unit with the dial **at ≥480px only**; below that width the shipped fix falls back to the original stacked, two-full-width-line layout (native `<input type="time">`'s 144px min-width floor does not fit both fields plus the normalised twin at 360px/390px, this app's own two reference viewports — see 29-04-SUMMARY.md's Known Limitations for the arithmetic), so the one-line claim does not hold on either shipped phone width today; the normalised HH:MM twin beside each native `<input type="time">` is hidden at load when the native field already renders unambiguous 24 h and stays as the scripts-blocked / 12 h fallback (B14's ground preserved); the presets are a segmented control with short labels whose hours are spoken once, by the dial's caption; proven by the surfaces-agree check reading the caption, the fields and the dial after a preset click, and by a check that the twin is hidden in a 24 h browser and visible with scripts blocked
- [x] **CFG-81**: The illustration dialog owns its own actions — Replace picture (and Delete for a manually resolved entry) is rendered in the dialog on every open, with the page-wide `edit_mode` and the "Change pictures" / "Modifier les images" toggle removed; "Send a picture" for an airline without artwork is unchanged; the resolve-context block (prefix, first/last seen, count, example callsign) renders only in the resolve modes and never shows an empty field or the image caption on an art card (its CSS `[hidden]` guard and its caption binding are fixed in quick task Lot A, re-asserted here); proven by opening a known airline's dialog and asserting Replace present, context absent, in both languages, with and without scripts
- [x] **CFG-82**: Compagnies reads gallery-first and its tab label never truncates — the filter and the known-airline gallery sit directly under the page title, unidentified prefixes and any remaining editing affordance move to a clearly announced secondary section below; the mobile tab bar's `Compagnies` label renders whole at 360 px and 390 px (`.tab-bar__pill`'s horizontal margin from `var(--space-sm)` to `calc(var(--space-xs) / 2)`, the 2026-09-17 audit's own fix, replayed) without the tab's 78×56 px tap area shrinking, proven by measuring the label's `scrollWidth` against its box at both widths
- [x] **CFG-83**: Vols is paginated — the list shows 10 to 15 flights then a real "Afficher plus" / "Show more" that works with scripts blocked (server-side limit or a native reveal, the planner's choice with its ground), the filter stays immediately visible above the first card, and the summary card keeps one stable grid on a 390 px phone (the timestamp and the callsign never share a wrapping line); proven by the page's measured height at 390 px on the realistic 36-flight fixture dropping below half of the audit's 6 710 px, and by the reveal read back from the DOM in both languages
- [x] **CFG-84**: État's battery-trend heading is short — the `<h2>` reads in the form "Batterie · 3 mois" / "Battery · 3 months" and the "daily average" precision moves to the card's caption, proven by the heading's rendered text in both languages and the caption carrying the precision
- [x] **CFG-85**: Aspect is one tile — the "Frame colours" card and the separate "Calendar" card are replaced by ONE tile holding the live preview, three usage rows (Départs, Arrivées, Vols du calendrier) each showing ONE swatch and the theme name, a wrapping palette grid of the 18 themes drawn as their own shape without the aircraft under the open row (no strip, no scrollbar, no pagers, no dot row, no disclosure), the calendar's connection folded under its own row, and "Règles par vol" as a secondary row disclosing the existing list and add form; the direction (accordion vs. segments) is decided by the developer on two `/gsd-sketch` variants BEFORE planning; the no-JS control contract holds (native radios cross-submitting via `form="settings-form"`, server-rendered preview for the saved theme, every row open with scripts blocked), the CSP is untouched, no new script file, no new custom property, colour literal, family or size; proven by the value read back from disk after an operate-submit round trip with scripts blocked at 360 px in both languages, by the preview following hover/focus and the selected swatch following the live radio state, and by every retired carousel rule grepped for a surviving consumer before deletion
- [x] **CFG-86**: Display's page height at 390 px is measured by the registered instrument before and after Phase 30 and reported against X6's 2 600 px target with the delta stated — the target is never restated to fit the result

### Audit remediation (2026-09-23 code audit)

Added 2026-09-23. Whole-repository code audit; the developer asked for every finding, low severity included, to be remediated inside v1.0 (Phases 32–41). Full evidence (file:line) and decisions D-A1..D-A6 in `.planning/audits/2026-09-23-code-audit.md`; each requirement below is that ledger row's remediation.

- [x] **TST-01**: pytest + pytest-xdist + pytest-cov as dev deps in `server/requirements-dev.txt`; config in `pyproject.toml`; shared fixtures in `conftest.py`; coverage gate moves to pytest-cov; CLAUDE.md stack row and CONTRIBUTING updated
- [x] **TST-02**: Migrated to pytest; every old check mapped in a migration ledger (old check name → new test id, or deletion with a reason)
- [x] **TST-03**: Injectable fake provider fixture; a conftest guard fails any test that opens a non-loopback socket
- [x] **TST-04**: CI (and ruff `target-version`) on the production version
- [x] **TST-05**: Run them in `firmware.yml`
- [x] **TST-06**: Separate test and deploy concurrency groups; never cancel an in-flight deploy
- [x] **TST-07**: `--only-shell`, cache `~/.cache/ms-playwright`
- [x] **TST-08**: Hash-pinned lock files for runtime and dev deps
- [x] **TST-09**: Subprocess coverage (`patch = ["subprocess"]`), then raise `fail_under` to the measured floor
- [x] **TST-10**: Migrated to pytest; one app-server fixture replaces every copy
- [x] **TST-11**: pytest-playwright; a missing browser is a failure in CI; parallelised per test with xdist
- [x] **TST-12**: Each rewritten as a behaviour or parsed-DOM assertion, or deleted with a stated reason in the migration ledger. No test reads `.planning/` or asserts on comments
- [x] **TST-13**: Permission tests skip under euid 0; every path inside `tmp_path`
- [x] **TST-14**: `run_all_tests.py` and all check counts retired; pytest discovery; `scripts/run-all-tests.sh` becomes a thin pytest wrapper
- [x] **TST-15**: Closing parity: every one of the 2018 pre-migration checks accounted for in the ledger; coverage ≥ pre-migration figure
- [x] **FW-01**: Reset reason checked at boot → increment `FP_NVS_BACKOFF_N` and sleep; `epd_init` returns errors
- [x] **FW-02**: Whole-wake deadline (one-shot `esp_timer` → deep sleep with backoff) and a real WDT; comment corrected
- [x] **FW-03**: 401/403 clears `FP_NVS_DEVICE_TOKEN`; next wake re-enrols; distinct error code
- [x] **FW-04**: Cap at 86400 s; above → JSON error
- [x] **FW-05**: Checked and mapped to the right `step=`
- [x] **FW-06**: Response validation (hash, URL, `sleep_s`, `led_enabled`, token), size/SHA gate and the sleep decision extracted into pure helpers with host tests
- [x] **FW-07**: https-only in production builds; custom bundle with the ISRG roots only
- [x] **FW-08**: Per-device enrolment secret; byos refuses re-enrolment of a known MAC
- [x] **FW-09**: `CONFIG_LWIP_DHCP_RESTORE_LAST_IP`, no ARP check (or static IP); measured on hardware
- [x] **FW-10**: One keep-alive client for display + image; TLS session tickets in RTC memory; wake duration logged (diagnostic line, Log Line Contract untouched); overhead explained
- [x] **FW-11**: Read once before Wi-Fi, 8-sample average
- [x] **FW-12**: `CONFIG_SPIRAM_MEMTEST=n`; shorter row wait if the datasheet allows; timed light sleep during the spacing wait
- [x] **FW-13**: Use `fp_api_base_normalize` or delete; delete dead code; drop orphan symbols; rollback disabled until OTA exists
- [x] **FW-14**: One helper each
- [x] **FW-15**: Derived from `git describe`
- [x] **HYG-01**: Keep what the code does, the *why* and invariants; drop plan/ticket history
- [x] **HYG-02**: Same purge in CSS and JS
- [x] **HYG-03**: Same purge
- [x] **HYG-04**: English-only rule for code, comments, docs and commits in CLAUDE.md and CONTRIBUTING.md
- [x] **HYG-05**: Deleted
- [x] **HYG-06**: Lint guard in CI rejecting plan/ticket IDs in comments (e.g. `\d{2}-\d{2}-PLAN`, `D-\d+`, `WR-\d+`)
- [x] **INT-01**: `fcntl.flock` on `state/poll.lock` around `run_once`
- [x] **INT-02**: One `atomic_write(path, data)` with unique temp names
- [x] **INT-03**: Thread lock + flock
- [x] **INT-04**: `mkstemp`, pruning, bounded cache
- [x] **INT-05**: Content-addressed `state/img/<sha>.bin` (last N kept); 404 on unknown hash
- [x] **INT-06**: Validated length, `Handler.timeout`, typed input, `hmac.compare_digest`
- [x] **INT-07**: `TimeoutStartSec`; total deadline per HTTP call
- [x] **INT-08**: Miss only on 404/empty route; TTL (misses ~1 day, hits ~30 days); LRU
- [x] **INT-09**: Advance to last newline; errors caught
- [x] **INT-10**: Type-checked
- [x] **INT-11**: Full traceback
- [x] **INT-12**: Injected clock; lock released during fetch
- [x] **INT-13**: Updated
- [x] **INT-14**: Pin the resolved IP for the connection (or correct the claim)
- [x] **SEC-01**: Per-client-IP throttle (trusted `X-Forwarded-For` from loopback Caddy)
- [x] **SEC-02**: `Strict-Transport-Security`
- [x] **SEC-03**: `Origin`/`Sec-Fetch-Site` check on every POST
- [x] **SEC-04**: Nightly `sqlite3 .backup` + off-box copy; README corrected
- [x] **SEC-05**: Release dir + symlink swap (or timer stopped); post-deploy `systemctl is-active` + HTTP probes fail the job; units/Caddyfile deployed with `daemon-reload`
- [x] **SEC-06**: `CapabilityBoundingSet=`, `PrivateDevices`, `ProtectKernel*`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`, `UMask=0027`; byos `--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost`
- [x] **SEC-07**: Secret via env; env file `root:root 600`; secret passed through `env:`
- [x] **SEC-08**: `sshd_config.d/00-skypane.conf`, `PermitRootLogin no`, validated
- [x] **EFF-01**: `encode zstd gzip`; validators + 304; static bytes cached in memory
- [ ] **EFF-02**: Only the scripts each page uses (no build step)
- [ ] **EFF-03**: One connection per request/cycle; schema once per process; one transaction
- [ ] **EFF-04**: Lazy context; severity computed without markup; light freshness endpoint
- [ ] **EFF-05**: Saved once, only if changed, compact
- [ ] **EFF-06**: Providers queried in parallel, per-provider rate limit kept
- [ ] **ARC-01**: `load_cycle_context` / `decide_hold` / `advance_display_queue` / `render_and_publish` / `persist` / `record` over a `CycleContext` dataclass
- [ ] **ARC-02**: `server/state_store.py` owns `poll_state.json`; companion imports it
- [ ] **ARC-03**: `render/{layout,text,hold_screens,cli}`, `calendar/{ics,registry,match}`, `themes.py`, shared `net/safe_fetch.py`
- [ ] **ARC-04**: Explicit injection
- [ ] **ARC-05**: One shared module used by server, byos and companion
- [ ] **ARC-06**: Type hints on the pure core; mypy in CI
- [ ] **CMP-01**: Route table `(method, matcher, handler, auth_required)`
- [ ] **CMP-02**: One `{route: path}` allowlist
- [ ] **CMP-03**: Split by settings group / by responsibility
- [ ] **CMP-04**: Typed per-page context
- [ ] **CMP-05**: Named templates
- [ ] **CMP-06**: Broken down; `handle_post` per settings group
- [ ] **CMP-07**: Shared helpers
- [ ] **CMP-08**: Merged; colours → tokens
- [ ] **CMP-09**: Stable message IDs
- [ ] **DOC-01**: All docs aligned with the code as it stands after phases 32–40
- [ ] **DOC-02**: Log gzipped in the tree (no history rewrite, D-A6); unused asset removed from the deploy; completed v1.0 phases archived via `/gsd-cleanup` at milestone close
- [ ] **DOC-03**: Re-audit: every ID in this ledger verified against the code and marked closed

### Remote firmware update (Phase 42)

Promoted from `.planning/seeds/SEED-009-remote-firmware-update-ota.md` on 2026-09-25. Decisions in `.planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-CONTEXT.md` (D-01..D-19).

- [ ] **OTA-01**: `GET /device/v1/display` carries an optional firmware offer (version, URL, SHA-256, size) only when the operator has scheduled a release that differs from the device's reported `X-Fw-Version`, the release is at or above the version floor, and the battery-low alert is not active. Quiet hours and display off do not withhold it (D-01, D-06, D-11, D-12, D-13)
- [ ] **OTA-02**: The device downloads an offered image with `esp_https_ota` over the existing ISRG-only trust store into the inactive OTA slot, checks size and SHA-256 against the offer, and verifies the image signature before the boot partition is switched (D-09)
- [ ] **OTA-03**: App rollback is enabled. A new image marks itself valid only after one fully successful poll; a crash, watchdog reset or failed poll on a trial image boots the previous image; `factory` stays the last resort (D-09)
- [ ] **OTA-04**: Release images are signed with ESP-IDF signed-app verification without hardware secure boot; no eFuse is burned. CI signs with a key held as a GitHub Actions secret; generating the key and its encrypted offline backup is a documented human procedure (D-09, D-10)
- [ ] **OTA-05**: A software version floor: the server never offers, and the device never accepts, a release older than the first OTA-capable release (D-11)
- [ ] **OTA-06**: The device refuses to start an update below the battery-low level it measures itself. A failed download, hash, signature or trial boot counts as one attempt and toward normal backoff; after three attempts the release is marked failed and the offer withdrawn (D-12, D-15)
- [ ] **OTA-07**: The panel shows an "Updating…" screen for every update, including during quiet hours and with the display off; the next normal poll redraws what the current mode calls for (D-14)
- [ ] **OTA-08**: A companion **Update** page, third entry of the Advanced nav group, shows the running version, the update state with its timestamp, a rollback warning, and every published release with its date and generated notes. Install asks for confirmation (with and without JS), a scheduled install can be cancelled until the device starts downloading, and any published release at or above the floor can be installed (D-02..D-07)
- [ ] **OTA-09**: A push notification reports a successful update and a failed one (with the version the frame is back on), through `server/notify.py`, in English and French (D-08)
- [ ] **OTA-10**: A git tag creates a release: CI builds with the tag as `PROJECT_VER`, signs, records version, SHA-256, size, date and the `firmware/` commits since the previous release; the reviewer-gated deploy job copies it into the state directory's firmware store; every release is kept (D-16, D-17, D-18)
- [ ] **OTA-11**: A CI check that reaches the network fails when the production host's certificate chain no longer leads to a root in `firmware/main/certs` (D-19)
- [ ] **OTA-12**: One hardware session proves, on the real frame: a signed update installs, an unsigned or tampered image is refused, a forced crash on a trial image rolls back, and recovery from `factory` works; recorded in `hardware/BRINGUP-LOG.md`

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### RER (Orly-Ville)

Deferred 2026-08-11 — user-requested scope reduction so v1 ships single-view (plane-only). Was Phase 3; that phase was removed from ROADMAP.md (see git history) and its full RER context is recoverable there when v2 planning starts.

- **RER-01**: User can see line, destination, and minutes-until-departure for the next 2+ RER trains from Orly-Ville
- **RER-02**: User can see a "leave by" cue combining the next train's countdown with a fixed walk-time buffer
- **RER-03**: User can see a disruption banner on the RER view during a service disruption on the line

### View Switching

Deferred 2026-08-11 alongside RER — meaningless in v1 with only one view. Revisit once a second view (RER or otherwise) exists in v2.

Superseded 2026-08-27 (explore session): the frame is meant to stay wall-mounted, so a physical button is impractical for routine interaction. View switching moves to the companion web interface (see CFG-01/CFG-02 below) instead. The physical button — not yet wired to any hardware (`firmware/main/app_main.c`'s wake-reason switch has a "button" case solely to exercise the log contract; the comment there states plainly "No button is wired up in Phase 1") — is reserved for debug/maintenance functions only (e.g. forcing an immediate poll, resetting Wi-Fi provisioning), not user-facing view control.

- **DEVICE-01**: User can switch between the plane view and the RER view via the companion web interface (CFG-02) — not a physical button
- **DEVICE-02**: Switching views triggers a fresh data poll for the newly selected view, not a stale cached image
- **CFG-02**: User can switch between available views (plane/RER) via the web interface, superseding the physical-button view-switch concept in DEVICE-01. **Moved back here from v1 (2026-08-27, `/gsd-discuss-phase 6`)** — inert with nothing to switch to until a second view exists; revisit once RER (or another view) is actually built.

### Messaging

- **MSG-01**: User can send a short message from a companion phone app that appears on the frame, delivered via the frame's next poll — the device never accepts inbound pushes, matching the poll-only security model

### Personal Photo Background

Deferred 2026-08-26 (Phase 3 discuss-phase) — user confirmed via SenseCraft that this panel renders dithered/photographic content well, so this is technically viable, but the user chose to keep Phase 3's scope to the aircraft illustration only and defer the background itself to v2.

- **VIS-01**: User can set a personal photo (e.g. of the install location) as the plane view's background, rendered with dithering instead of the current full-bleed solid state-color field

### On-Device Fault Fallback

Seed idea, deferred 2026-08-27 (explore session) — the device-local half of the fault-icon idea explored alongside the Companion Configuration Web Interface (CFG-05, now promoted to Phase 6 — see v1 Requirements above). This half stays deferred: it's technically independent of the web interface (no dependency on CFG-03 existing) and covers the harder case where the device can't reach the server at all, so no server-rendered image can carry an alert. Full design rationale in `.planning/seeds/on-device-fault-icon.md`.

- [x] **DEVICE-06**: When the device has failed to reach the server for 2+ consecutive poll attempts (`backoff_n >= 2`), it renders a small local fallback screen (solid fill + pre-baked alert icon) directly in firmware via the existing `fp_panel_draw()` call, without needing a successful server round-trip — done in quick task 260924-u7n (2026-09-24): dithered-field NO CONNECTION hold screen + CFG-05 alert glyph, drawn by firmware; see `.planning/quick/260924-u7n-device-06-local-no-connection-fault-scre/`

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Solar charging | Deferred until real battery life and frame placement are known; indoor solar is unreliable without a well-lit window |
| Public flight-data/schedule API (e.g. AeroDataBox) as the plane-detection source | Reversed after scoping — the goal is "the specific plane using runway 3 right now," which schedule APIs don't expose; ADS-B aggregators detect real aircraft directly |
| Wall power | Battery-only for v1, to force realistic power-budget decisions early |
| Freshness timestamp / graceful stale-offline display state | Explicitly deferred by user for v1 despite research flagging it as a common pitfall; revisit if staleness becomes a real problem |
| Additional views beyond plane/RER (weather, other transit lines, etc.) | Stay two-view to preserve focus on the core value |
| Status LEDs, on-device settings/menu UI, gate/terminal/check-in fields, push notifications to phone, animated transitions | Anti-features that would make the frame read as a gadget rather than ambient art. Scoped 2026-08-27: this exclusion is about a permanently wall-visible indicator — the module's own built-in User LED, lit only during the multi-second active wake window and physically behind the frame as a bring-up/reflash aid (`firmware/main/led.c`, plan `260827-wo4`), falls outside it. See `.planning/seeds/bring-up-debug-led-remote-toggle.md`. |
| Local RTL-SDR ADS-B receiver | Originally the primary plan; Phase 1 plan 01-04 validated the free adsb.fi/airplanes.live aggregators clear the coverage bar (~92min real traffic, 38/37 distinct aircraft, 2/2 on-ground) with no dedicated hardware needed — no RTL-SDR ordered |
| ADS-B Exchange specifically (as opposed to adsb.fi/adsb.lol) | Considered as a possible aggregator but not the one validated/used — adsb.fi and adsb.lol are the two default providers in production |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLANE-01 | Phase 2 | Complete |
| PLANE-02 | Phase 2 | Complete |
| PLANE-03 | Phase 2 | Complete |
| DEVICE-03 | Phase 1 | Complete |
| DEVICE-04 | Phase 5 | Complete |
| DEVICE-05 | Phase 5 | Complete (05-01, all 3 tasks — MEASURED verdict 2026-09-15, 0.923 mAh/cycle, closed 2026-09-24 with physical post-mortem confirmation; see `hardware/BATTERY-RUN.md`) |
| CFG-01 | Phase 6 | Complete (06-07) |
| CFG-03 | Phase 6 | Complete (06-08, deployed 06-11) |
| CFG-04 | Phase 6 | Pending (not yet planned) |
| CFG-05 | Phase 6 | Pending (not yet planned) |
| CFG-06 | Phase 6 | Pending (not yet planned) |
| CFG-07 | Phase 6 | Complete (06-07) |
| CFG-08 | Phase 6 | Pending (not yet planned) |
| CFG-09 | Phase 6 | Pending (not yet planned) |
| CFG-10 | Phase 6 | Pending (not yet planned) |
| CFG-11 | Phase 6 | Pending (not yet planned) |
| CFG-12 | Phase 6 | Complete (06-07) |
| CFG-13 | Phase 20 | Complete (#63) |
| CFG-14 | Phase 20 | Complete (#63) |
| CFG-15 | Phase 20 | Complete (#63) |
| CFG-16 | Phase 20 | Complete (#63) |
| CFG-17 | Phase 20 | Complete (#63) |
| CFG-18 | Phase 20 | Withdrawn — superseded by CFG-23 |
| CFG-19 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-20 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-21 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-22 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-23 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-24 | Phase 21 | Complete (21-VERIFICATION.md 10/10) |
| CFG-25 | Phase 22 | Complete (22-01) — `grep -l CFG-25 *-PLAN.md` returns 22-01 alone. It landed B1 in full (the save bar appears whenever any field changes; the fallback Save stays reachable until the bar has actually been shown once, never on the mere presence of `.dirty-ready`) plus D-02's browser harness. The "Planned (22-01..22-16)" text this row carried until the closing sweep was stale: it described the phase's own span, not this requirement's, and contradicted its own already-ticked checkbox |
| CFG-26 | Phase 22 | Complete (22-02, 22-04, 22-07) |
| CFG-27 | Phase 22 | Complete (22-05) |
| CFG-28 | Phase 22 | **Un-ticked after 22-12 (was marked complete by 22-11).** 22-06 landed the battery/tooltip half and 22-11 the resolve-dialog half (B5/D-05) — the dialog's `data-first-seen`/`-last-seen` carry the no-JS path's own `layout.concise_timestamp_html()` output with its tags stripped, so the two paths are byte-identical by construction, and `panel-lookup.js` is pinned free of every date API. **One clause remains unmet**, raised by 22-12 and verified here: Health's page-header clock renders `title="<raw UTC ISO>"` (`companion/pages/health_page.py:3628`, fed by `history_db.utc_now_iso()`). A `title` IS a tooltip and this one is not behind a copy control, so it fails two of this requirement's clauses. 19-09 (D-02/A-20) put it there deliberately and `companion/test_status_pages.py` pins it by name, which is why 22-12 correctly left another plan's pin standing rather than editing it. The conversion pattern already exists and is proven: 22-06 converted `concise_timestamp_html()`'s title to a full local timestamp and asserts the raw ISO does not survive verbatim. **Complete after 22-16's closing sweep, which did exactly that.** The clock's `title` now carries the full Europe/Paris local timestamp via `health_page._full_local_timestamp_text()` — a fourth caller of the helper every battery `title`/`aria-label`/`data-when` on that page has used since 22-06, so no second date path was opened and the unparseable-value degrade is unchanged. 19-09's pin was RETARGETED IN PLACE, not deleted: the same named check now asserts the title equals the helper's own output and that the raw ISO does not survive verbatim, and it was mutation-tested by reverting the render (exactly one additional failure, this check). `data-loaded-at` still carries the machine-readable instant `freshness.js` actually reads — the `title` was only ever a human-facing tooltip. `status-pages` stays at 267/268, the count unchanged because the check was retargeted rather than added. Every clause of this requirement now holds: the battery readout and its chart (22-06), every tooltip (22-06 and 22-16), the airline resolve dialog (22-11), and raw ISO only behind a copy control |
| CFG-29 | Phase 22 | Complete — `grep -l CFG-29 *-PLAN.md` returns only 22-08, which landed the flash/title/attribute half and widened `test_i18n.py` to `app.py`, HTML attribute literals and JS fallbacks; the three plurals B16 names were each landed by the plan that owns their file (22-10 the Calendar status detail, 22-11 the airlines_page.py pair, 22-12 the Resolution-rate line "over the last %d days, %d event(s)" — the last one). B16's remaining items are also landed and pinned by name: the flash and `<title>` round-trips, `aria-label="Primary navigation"`, the Light/Dark segments, and the battery caption stating the real count rather than BATTERY_TREND_LIMIT |
| CFG-30 | Phase 22 | Complete — served by nine plans (D-07's B2-B18/X3-X9); 22-07 landed the Home half of B2, B18 and X4; 22-09 landed X5 in full and B11's Flights third (Airlines/Health adopt the same group in 22-11/22-12); 22-10 landed X6's density half, B6, B7, B8, B9, B14, B15 and B17 (X6's "fold the grid behind the big preview" half is D5/Phase 23; X6's page-height target is NOT met and cannot be by density alone — see 22-10-SUMMARY.md); 22-11 landed X7 in full and B11's Airlines third; 22-12 landed X8 in full, B12 (the French table overflow, closed by headless measurement) and B11's Health third, closing B11 across all three filtered pages; 22-13 landed X3 in full (the stacked card measured at 390px and 1280px, a programmatically associated error reusing `.field-error`, a gated error border that passed and shipped, a script-gated show-password toggle and a server-seeded lockout countdown that re-enables the form at zero — the audit's "small brand mark" suggestion deliberately declined per 22-UI-SPEC.md §3.2). **Complete after 22-14, the last of the nine plans (`grep -l CFG-30 *-PLAN.md` returns nothing beyond it; 22-15 and 22-16 carry CFG-31 only).** 22-14 landed X9 in full — the mechanism locked to a bottom tab bar by D-10, never the rejected overlay drawer: a third nav rendering fed by the ONE shared `_nav_links()` iteration, five cells with More as a native `<details>` that works with scripts blocked, absent from the login shell and the 404, `aria-current` on the one real link and the active pill on the More summary for an Advanced page, 78x56px cells clearing 44px directly in both axes, and the hamburger's push cut from ~420px to a MEASURED 189px by moving destinations out of the dropdown — plus B10 (two nowrap segments, one client rect each in French at both the 240px sidebar and 390px, and a Home reminder that is a `<span>` with no href, so it can no longer claim a destination the user already occupies). 22-13's own handover note listed "B3, B10 and B13" as remaining; re-checked against the code, only B10 was — **B3 landed in 22-03** (`resolution_stats()` counting every row with unknown sources bucketed as "Other", the empty section omitted outright, the 30-day window named) and **B13 in 22-04** (one `.frame-strip__cell` class, `align-items: stretch`, one three-row internal grid, the update line demoted to Emphasis). One caveat carried forward rather than hidden: 22-10 reported that X6's page-height pixel target is not met and cannot be by chip density alone — that is an audit measurement, not one of this requirement's own enumerated clauses, and the remaining half is D5/Phase 23 |
| CFG-31 | Phase 22 | In progress — 22-10 landed C1's legend half, C3, T10 and T12; 22-12 landed C1's compact `empty_state()` variant (with the default form proven byte-identical against a real existing caller) and C5's Health adoption, the last of the four monospace time treatments on that page. 22-14 landed T5 (the `transitionend` listener filtering on its own target AND on `max-height`, and a close with no transition applying `hidden` synchronously — decided by reading the computed style, never by a timer, which `nav-dropdown.js`'s header forbids), T7 (a `.dirty-ready`-scoped content clearance at both breakpoints at MEASURED values, and one `z-index: 30` across both breakpoints where the desktop rule had none — the superseded "No z-index, and why" paragraph amended in place with the stated reason its own escape clause asks for) and T11 (one open-state `max-height`, 320px, pinned against a measured 165px of reduced French content; both contradicting declarations gone, not re-tuned). **After 22-15 every one of T1-T15 is landed.** 22-15 closed the seven it owned: T2 (the DESTRUCTIVE Disconnect stopped rendering as the primary accent CTA — a bare class at (0,1,0) lost to `button[type="submit"]` at (0,1,1), so the whole grey rule block was dead code; fixed by element-qualifying to (0,1,1) and letting source order decide, never by weakening the primary rule, and the two `type="button"` call sites are why the defect was invisible on two of three consumers), T3 (an explicit `summary::before` chevron restoring the marker `display: flex` suppresses — reaching the tab bar's More summary too, but out of flow and with an inverted rotation, both decided deliberately — with the reduced-motion block count unchanged at two), T4 (the false sticky table-header claim removed outright, which also makes 260901-uzi's finding 5 candidate (b) MOOT rather than deferred), T6 (selection stops shifting layout: `box-sizing: border-box` does not hold the OUTER box of a `flex: 1 1 0` item, measured 98.67px against 96.66px at 390px — every selected-state border is now a constant 1px and the 2px signal moved to `box-shadow: inset`, across all THREE selectable surfaces and both dashed saved-state markers, with both `:has(input:checked):hover` restore rules reconciled in the same commit, and 22-10's stated border allowance in `test_browser_ux.py` DELETED so outer widths now assert plain equality in a real browser), T15 (a focus ring on a selected chip or card using the global floor's own values, inside the ONE feature-query block, plus `summary` added to that floor), T13 (`freshness.js` retries with a bounded exponential ladder starting AT the normal cadence behind a NEUTRAL `.dot--off` Paused/Reconnecting badge — `.dot--off`'s third consumer — with an in-flight guard and targeted swaps that skip unchanged regions and any region holding focus) and T14 (one shared `companion/static/submit-guard.js`, a delegated document-level listener registered once on the authenticated shell, disabling from a ZERO-DELAY TIMER because a submit button's name/value joins the form data set after the listeners return and the theme and language pickers are named submit buttons — no label change, no CSP change). T1/T8 landed in 22-01, T9 in 22-04, T10/T12 in 22-10, T5/T7/T11 in 22-14. T16 is OPTIONAL and none was taken. **Complete after 22-16, the last of the seven plans serving this requirement.** T1-T15 were all landed before it and T16 is optional (none taken); what 22-16 owed was D-08's own framing — the skill is the authority and must be updated in step — and it applied all twenty of 22-UI-SPEC.md §4's rows across the six `sketch-findings-skypane` files, plus the three UI-checker follow-up notes. Every supersession is marked IN PLACE with a stated reason and nothing was deleted, verified by diff. **Two reversals, both argued rather than assumed:** the recorded rejection of the icon-only pattern for `.row-toggle` (X5 removed the visible text that was the rejection's own stated ground) and `.dirty-bar`'s "No `z-index`, and why" paragraph with its matching "What to Avoid" entry (T7, used exactly as that paragraph's own escape clause was written). **Three stale load-bearing numbers corrected:** the `:has()` block count (ONE, verified against the live stylesheet — the line an earlier draft of this phase's own UI spec copied instead of checking the code, and the cause of a checker BLOCK), the floating-overlay shadow exception count (FOUR, already stale by one before this phase) and the compact-chip usage sentence. **Two §4 rows were found wrong against the code and corrected rather than applied mechanically:** T6 covers THREE selectable surfaces plus both dashed markers and needs `.theme-chip`'s `box-shadow: inherit` overlay, and `.dot--off` has FOUR consumers, not three. 22-16 also corrected the false premise in `style.css`'s own header comment (it claimed 06.6.4.1-04 had removed the Disconnect accent fill as a specificity bug fix; the fill was live until 22-15), leaving both harness-pinned phrases untouched. The two rejected nav verdicts stay UNCHANGED AND UNREVERSED, with a note recording why bottom tabs were chosen so neither had to be reopened |
| CFG-32 | Phase 23 | **Complete (23-01, 23-04, 23-05, 23-08, 23-09, 23-10).** `grep -l CFG-32 .planning/phases/23-*/23-*-PLAN.md` returns exactly those six plus 23-11, which is this closing plan; the SUMMARYs echoing the ID are 23-01, 23-04, 23-05, 23-08 and 23-09 (23-10 spends the budget without restating the ID, and its own criterion table records the counts). Every clause checked against the live stylesheet at close, not against the plans: **(1) two shared tokens** — `--motion-fast: 180ms`, `--motion-slow: 2s`, and all four `animation:` declarations take their duration from one of them; **(2) exactly one keyframes definition per animation** — four blocks (`skypane-pulse`, `skypane-fade-in`, `skypane-row-arrive`, `skypane-bar-arrive`), each name defined once, mutation-proven (a second `@keyframes skypane-pulse` fails with the duplicate named); **(3) no dangling reference** — mutation-proven (`animation: skypane-shimmer …` fails naming the missing block); **(4) switched off by `prefers-reduced-motion: reduce`, INCLUDING the pseudo-elements the global `*` selector cannot reach** — this is the clause that needed real work and got it. The global override matches `*, *::before, *::after`, which are element selectors; the `::view-transition` tree is outside them, and 23-04 closes that gap by wrapping the at-rule in `@media (prefers-reduced-motion: no-preference)` so the transition is never SET UP, proven in a real browser in both context modes from the at-rule's own `parentRule`. `::backdrop` is in the same blind spot and is handled by declaring no motion on it at all — verified live, `.lightbox::backdrop` carries a `background` and nothing else. The live reduce-block count is **2** and the no-preference count **1**, both pinned by named constants in `companion/test_companion_app.py` and mutation-proven. The whole budget is executable rather than prose: `_motion_budget_is_enforced_in_the_stylesheet()` strips comments before measuring and additionally bans `interpolate-size`/`calc-size(` by name. **Recorded against this row rather than hidden in it:** the token rule binds `animation` and not `transition` (26 `transition:` declarations predate the phase with bare literals; converting them is the stylesheet-wide refactor 22-CONTEXT.md's D-08/T16 forbids), and this phase deliberately broke the "zero new custom properties" achievement Phases 20, 21 and 22 each held — by exactly two, because a motion budget with no named durations is a budget in prose |
| CFG-33 | Phase 23 | **Complete (23-04, in full — nothing about D10 remained open beyond the human sweep).** `grep -l CFG-33 .planning/phases/23-*/23-*-PLAN.md` returns 23-04 and 23-11 alone, and 23-04 is the only SUMMARY claiming it. All three clauses: **(1) native cross-document view transitions** — one `@view-transition { navigation: auto; }`, zero script (`grep -c startViewTransition` across `style.css` and every static script is 0), zero markup change, three `view-transition-name` declarations; **(2) per-route uniqueness proven in a REAL browser** — not by a source scan, which can only prove a declaration appears once: the check reads `getComputedStyle(el).viewTransitionName` for every element on all six authenticated routes and asserts the declared set matches `VIEW_TRANSITION_NAMES`, that no name resolves to more than one element (over every name, including Chromium's own UA `root`), that each resolves to exactly one element on each route its entry lists, and to zero elsewhere. The last three clauses exist because "no name appears twice" is trivially satisfied by a page declaring no names; both halves are mutation-proven, and each mutation leaves every source-level scan green; **(3) degrading where unsupported** — an engine without the feature parses the at-rule into no rule and drops the three unknown properties at parse time, so a Firefox visitor gets exactly today's instant navigation; the mutation evidence doubles as the degradation evidence, since M1/M3/M4 each changed only whether the at-rule is set up and the app rendered and navigated normally with all pre-existing browser checks green throughout. A scripts-blocked visitor gets the cross-fade in full — the one enhancement in this phase that survives the no-JS floor intact. Firefox itself is not installed in the container and is the human sweep's job |
| CFG-34 | Phase 23 | **NOT ticked — three of four clauses hold and the first does not.** `grep -l CFG-34 .planning/phases/23-*/23-*-PLAN.md` returns 23-03, 23-05, 23-06 and 23-11. What landed: the **`<time data-relative>` server convention** (23-03 — the app's first `<time>` element ever; `layout.relative_time_html()`, with the `datetime` attribute carrying the instant converted onto Europe/Paris rather than the raw stored string, because D-05/B4's no-raw-ISO rule is page-wide and an attribute is not an exemption from it — mutation-proven, reverting to the raw string fails three checks); **one script ticking them each second** (23-05, `relative-time.js`, the thirteenth deferred script, carrying no language logic at all — nine complete wordings rendered onto `<body>` and translated server-side); **visibility-aware** (the interval is stopped on `visibilitychange` and the elements are repainted immediately on return, before it is re-armed; proven in a browser against a CONTROL phase showing the same age does move while visible, because "the text did not change while hidden" passes on a dead element). **The unmet clause is the first one: "Every relative age on screen is live."** Four visible ages do not tick, and they were not left static by decision — three of them were simply unowned, and one was explicitly routed to a plan that did not convert it. They are enumerated here and in `references/data-density.md` so this row is a statement of fact rather than an aspiration: **(a)** the Flights **desktop** table's When cell (`history_page._when_cell_html()` composes from `relative_age_text()` directly) — so on the same row the age is live below 960 px, where the phone card goes through `concise_timestamp_html()`, and frozen above it. **Correction of record:** 23-03's inventory routed this site to 23-08 while describing it as "the mobile card's relative-age secondary line"; it is the desktop cell, and it was not converted. **(b)** Display's Calendar status detail ("12 entries, refreshed 3m ago"). **(c)** Health's unresolved-prefix registry cells. Nothing blocks (a), (b) or (c) — each needs a plan that owns the file. **(d)** Health's battery `when` text, which **structurally cannot** become an element: `battery-trend.js` writes it into a `title` with `setAttribute`, markup in a `title` renders as literal angle brackets, and a shipped check pins that the script does no client-side date math — changing this means changing that script's transport first. **The decision this needs:** either a follow-up converts (a)-(c) and this row is ticked, or the requirement's first clause is amended to match the shipped scope and (d) is named in it as the permanent exception. Ticking it as written would repeat the CFG-28 error of Phase 22 exactly. **D22's own remainder, which this row also carries, IS complete** (23-05): the live indicator breathes only while the loop is genuinely listening (the class is DERIVED from `freshness.js`'s own interval handle AND its state badge — either half alone lets a paused page breathe — and is synced from the four functions that change that state), and Health's freshness line reports now instead of claiming a moment. D22's **orange** reconnecting state is deliberately not implemented as worded: 22-15 shipped it NEUTRAL on the argued ground that a browser which lost its connection is not a device fault, `grep -cE 'dot--warn\|dot--error\|status-warn'` over `freshness.js` is 0 and pinned, and this phase extended that decision rather than reverting it — **superseded by a shipped decision, not an omission** |
| CFG-35 | Phase 23 | **Complete (23-06; extended to a fourth page by 23-08 without a code path changing).** `grep -l CFG-35 .planning/phases/23-*/23-*-PLAN.md` returns 23-06 and 23-11 alone. **The per-page registry:** `layout.REFRESH_SWAP_SELECTORS_BY_PAGE`, one definition site, keyed by `nav_slug()`'s own values so the key space has one definition site too and a page cannot be given a key that disagrees with its route; the key is rendered on `<body>` by `page_shell()`; the two key sets (Python and `freshness.js`) are pinned EQUAL in **both** directions, and a registry selector that matches nothing on its own page is a check failure rather than a region that silently never refreshes. **All three named skips, each proven in a real browser with a control proving the opposite outcome:** focus (22-15's, re-asserted), pending (`[data-pending]` — new here, and the marker's only producer arrived in 23-07, so the rule was proven from the harness side first and against the shipped writer second), and dirty form (a whole-cycle stand-down — no fetch at all, asserted by COUNTING requests rather than by reading the DOM, because a page that fetched and then declined to swap is a different and worse behaviour). The gate requires `dirty-state.js`'s liveness marker AND the bar's current visibility: presence-without-liveness is 22-01/B1's defect of record, and a source clause asserting only `".hidden" in code` was found **vacuous by mutation after it had shipped in a commit**, then repaired in its own commit so the failure and the fix are both legible. A hidden tab issues zero requests. **"Without stealing the page" is the clause most at risk of being asserted vacuously and was not:** `isEqualNode` skips an unchanged region for reasons having nothing to do with focus or pending, so both node-identity checks **dirty the region first** and then run a second phase proving the same changed region IS replaced once the rule's condition is removed |
| CFG-36 | Phase 23 | **Complete (23-07).** `grep -l CFG-36 .planning/phases/23-*/23-*-PLAN.md` returns 23-07 and 23-11 alone. Every clause, and the order they landed in is itself part of the evidence: **the absent-field semantics were fixed in the commit BEFORE the control moved** (`9d5fd06` changes `handle_post()`'s resolution and touches no markup; `ab41dc5` removes the checkbox), so no commit in history has `led_enabled`'s control absent from the form while an absent field still means `False` — the reverse order would have left a commit where every unrelated settings save switched the physical LED off. 22-05's four-combination guard was **extended** to eight over three flags rather than duplicated, and went red with exactly one failure naming the regression. **Three real `role="switch"` controls** from one builder, `aria-checked` and the posted `state` always each other's inverse (a switch whose posted state did not invert would, with scripts blocked, re-assert the state it is already in). **Optimistic with rollback on error:** the flip lands before the request leaves (proven by holding a POST open from the harness, so "before the answer" is a real moment with no sleep), and **both** terminal branches roll back — a 500 and a network-level `route.abort()`, in both languages, each restoring `aria-checked`, clearing the pending marker, leaving the stored value alone and putting a translated generic sentence in a toast that is asserted VISIBLE (a live region nobody can see is half an announcement) and free of `500`, `http`, `/quick/` and `TypeError`. A 204 and nothing else confirms; a rejected state value is never answered with a 204, because the client reads 204 as confirmation and would leave a false flip standing. **The underlying form still works with scripts blocked**, proven by SAVING rather than by rendering: a `java_script_enabled=False` context at the 360 px floor, in both languages, for all three switches — the control renders, its `aria-checked` equals the value on disk, its box clears 44 px in both axes, it is clicked, a real navigation is awaited, and `device_config.load_device_config()` is read back **from disk**. The mutation that demotes the switch to `type="button"` — literally a control that renders and does nothing — fails it. **On D2's fourth switch:** this requirement names Screen, Quiet hours and LED and is satisfied by them; the notifications switch is D2's ask, not this row's, and is recorded in the phase coverage ledger below with its grounds |
| CFG-37 | Phase 23 | **NOT ticked — two of three clauses hold and the middle one is deliberately contradicted by a shipped accessibility decision.** `grep -l CFG-37 .planning/phases/23-*/23-*-PLAN.md` returns 23-08 and 23-11 alone. What holds: **"a new detection arrives visibly"** — a one-shot `--motion-slow` wash on rows whose identity is absent from the set known from the page as first rendered, keyed to `runway_events.id` and never to the loop index (which renumbers the instant a detection lands at the top), asserted as set EQUALITY in both directions because "a new row is highlighted" is satisfied by a script that highlights everything, and highlighting everything is both the likelier bug and the more damaging one — mutation-measured at 108 elements highlighted on a refresh that brought nothing new. **"the filter count moves with its list"** — the count's element animates, its number is never tweened, it fires only when the rendered sentence actually differs, and a swap is followed by the one `applyFilter()` re-run, because the server renders the list unfiltered and a refresh would otherwise hand back every row under a typed query. **The unmet clause is "the detail row opens and closes with measured motion."** It opens with measured motion — a real height through `grid-template-rows: 0fr → 1fr` with an `@starting-style` entry, deliberately not the Chromium-only `interpolate-size`/`calc-size()`. **It closes instantly, on purpose.** `display: none` stays the collapsed end state and `transition-behavior: allow-discrete` was considered and declined in writing, because for the whole of that transition — and on every browser without the property — a closed row's copy buttons and links are still in the tab order and still in the accessibility tree: measured, a row held present at zero height let **4 of its 4** controls take focus, so a keyboard user tabs into a row nobody can see. A row that shuts instantly is a smaller loss than a row that is secretly still there, and that trade is right. **The decision this needs is about the REQUIREMENT, not about the code:** amend this clause to "opens with measured motion and closes instantly, for the accessibility reason recorded in 23-08", or accept the cost and reopen `allow-discrete`. Ticking it as written would be the CFG-28 error of Phase 22 repeated — a requirement marked complete while one of its clauses is knowingly unmet. **Sticky day headers are NOT built and that is a settled decision, not a gap in this row**: see the coverage ledger below |
| CFG-38 | Phase 23 | **Complete (23-02, with one clause extended by 23-08 and the whole re-asserted by 23-11).** `grep -l CFG-38 .planning/phases/23-*/23-*-PLAN.md` returns 23-02 and 23-11 alone; 23-01's SUMMARY mentions the ID without claiming it, and 23-02 deliberately left the box unticked because it delivered only the harness-helpers third. All three clauses: **(1) a no-JS helper** — `_no_js_page(browser, base_url, route, viewport=None, sign_in=True)`, now the file's ONLY `java_script_enabled=False` call site (3 → 1), so a scripts-blocked proof that quietly ran with scripts enabled is unavailable rather than merely unlikely; it took a `sign_in` parameter because one of its three first callers must not sign in (the login card's subject is what `/login` renders to an unauthenticated visitor), and its `viewport` parameter was first exercised by 23-07 at the 360 px floor, exactly as planned. **(2) a 360 px viewport constant** — `VIEWPORT_MIN_SUPPORTED`/`VIEWPORT_PHONE`/`VIEWPORT_DESKTOP` plus two width ladders DERIVED from those dicts rather than restated, so every width this file measures at has one definition; the 320 px rung is kept as `VIEWPORT_WIDTH_NARROW` with SKILL.md's two non-licences quoted verbatim beside it so a later reader cannot tidy it away. **(3) a disclosure sweep that stays honest once the pages animate** — the general every-`<details>`-open sweep runs under `reduced_motion="reduce"`, making the final state the immediate state through the app's OWN global override rather than through a timeout, a sleep or an event listener (a timing wait across 47 disclosures × 6 routes × 2 languages × 3 widths is a flakiness generator, and an intermittently red check is worse than no check because it teaches people to ignore it). 23-02 recorded that its sibling check (quick task 260913-cz6, on Health) had the identical exposure and deliberately left it alone rather than widen its own scope silently; **23-08 closed it**, on the honest ground that its own animations provably could not reach that check today but the exposure is structural and the cost of the fix is one argument. The sweep was proven still to SEE its own defect: 260913-eab's mutation was reproduced in both its forms, and the failure message is byte-for-byte the numbers eab recorded before the reduced-motion context existed. The refactor was proven to be a refactor by AST-comparing every `check(...)` description against HEAD — 26 call sites both sides, descriptions identical — and by measuring runtime rather than arguing it (52.4/53.0 s before, 51.9/52.0 s after). Zero net checks. **This row also carries the phase's design-system-in-step clause**, which 23-11 discharges: five `sketch-findings-skypane` files updated with every value read live from the code, every supersession marked in place, and two findings recorded rather than smoothed over |
| CFG-39 | Phase 24 | **NOT ticked — six of seven clauses hold, one fails and one holds only vacuously.** Served by 24-01; every clause re-checked against the code at close, not against the plans. **Holds: (1) "the five drawings share a single battery estimator"** — `companion/battery.py` is the one, machine-enforced by a three-net scan (the constant names; a second `battery_percent`/`battery_fraction` definition; and the net a rename cannot evade — `4200` and `3300` appearing **together** in one module, `4200` alone being innocent because `health_page.SPARKLINE_Y_MAX_MV` is legitimately the same number). `server/poll_loop.py`'s private copy is allow-listed **by name with a written justification** rather than scoped away, because the server package may never import the web-app package (D-27); it is outside every picture path, and a **third** definition anywhere under `companion/` or `server/` fails. Two recorded nuances rather than hidden ones: the plan's premise that the constants live in exactly one module was **false and permanently so**, and three of the "five drawings" plot no battery at all, so they share the estimator only vacuously. **(4) "every axis label names a value the drawing actually reaches"** — the chart's two Y labels are the fixed domain endpoints the scale reaches by construction and are asserted **not** to rescale to an out-of-range reading; the band's are its own two ends; and the grid **reads its scale labels past the buckets it dropped**, which is the one place this clause could have gone wrong and was designed for. **(5) "every drawn shape carries an explicit fill"** and **(6) "no colour literal appears in emitted SVG"** — both machine-enforced over `companion/draw.py` **plus every `companion/pages/*.py` module**, scanned over string **literals** with comments and docstrings stripped first (load-bearing: `health_page.py`'s own docstrings contain `<line class="sparkline-` and three prose mentions of `<polyline>` with no class, so a raw scan would report three unpainted shapes that do not exist), each mutation-proven. **(7) "where a `viewBox` exists it contains its own outermost labels" — holds VACUOUSLY and that is recorded rather than claimed.** This phase emitted **no SVG `<text>` node anywhere**: every label is an HTML `<span>` outside the canvas, so no viewBox has an outermost label to contain. The obligation was discharged on the drawings' own **ink** instead — the ring's arc measured at both sizes with half the *resolved* stroke width added on every side in the open, and the grid's cells — which is a real measurement but not the one the clause names. **THE UNMET CLAUSE IS (2): "a single SVG drawing module (scale, geometry, label placement, colour binding)."** Four of the five drawings go through `companion/draw.py`; **the battery chart does not.** `health_page.battery_sparkline_svg()` keeps its own scale (`sparkline_point_y()`, promoted out of a closure by 24-05 but **not** onto `draw.percent_y()`), its own canvas emission, its own label grid (`.sparkline`/`.sparkline__y`/`.sparkline__x`) and its own class vocabulary — **17 `.sparkline*` selectors standing beside 22 `.drawing*` ones**, two parallel implementations of one coordinate scheme. Neither plan hid this: 24-01's `files_owned` forbade touching `companion/pages/*.py` and routed adoption to 24-05, and 24-05 owned the function but found `draw.py` offers no primitive fitting the nested area layer and did not rewire the rest. **What makes this worth un-ticking rather than rounding up is the second half: nothing pins the two together.** 24-01 measured `draw.percent_y()` reproducing the chart's arithmetic exactly on all five seeded points including out-of-range — but that was a **one-off measurement recorded in a SUMMARY, not a shipped check** (`grep -rn 'percent_y' companion/test_status_pages.py companion/test_view_pages.py companion/test_browser_ux.py` is empty, and no check in `test_companion_app.py` names `battery_sparkline_svg`). The two can now drift with nothing noticing, which is the exact failure mode this requirement exists to prevent. **The decision this needs:** either a follow-up rewires `battery_sparkline_svg()` onto `draw.percent_*` + `draw.label_grid()` and retires the parallel `.sparkline*` vocabulary, **or** the clause is amended to "one drawing module plus the chart it was generalised from" and a standing equivalence check is added so the two provably cannot drift. Ticking it as written would repeat Phase 22's CFG-28 error exactly |
| CFG-40 | Phase 24 | **Complete (24-04).** Every clause measured, none inferred. **"Rendered server-side from the shared estimator"** — the page makes **one** call, `battery.battery_percent(mv)`, and the ring draws that integer over 100; it deliberately does **not** call `battery_fraction()`, because that would be two calls into the estimator that agree only by rounding. Settled by mutation, not argument: sourcing the arc from the fraction makes it disagree with the text beside it by **0.0033** on a seeded 3690 mV reading and fails a 0.0005-tolerance check naming both (*the ring draws 0.4333 of its circumference while the readout beside it prints '≈ 43% · 3690 mV'*). The cost is a 1% quantisation — 3.6° of arc at 72px, about 0.6px of ink — and it buys the defect class being unreachable rather than unlikely. **"Large on Health and small in Home's battery tile, ONE function called twice rather than two similar functions"** — proven **behaviourally**, which is the only proof that counts here, since two files can both import an emitter and still draw two different pictures: a class constant replaced inside `companion/draw.py` moves **both** pages at their two different sizes in one observation, and a simulated fork (the ring's markup inlined into `home_page.py` with the real class strings) fails both a structural and a behavioural check. The geometry is **ratios of the box side** (`RING_STROKE_RATIO` 0.12, `RING_CLEARANCE_RATIO` 0.02), identical at 72px and 36px by construction, and a CSS-only "small variant" is made **structurally impossible** by emitting `stroke-width` as a presentation attribute — CSS of any specificity beats one, so a `stroke-width` in `.drawing-ring-*` would flatten both sizes to one thickness; a mutation pinning the stroke fails naming the proportions (Home 0.0556 against Health 0.1200). There is no `variant` parameter and the docstring says one must never be added. **"Legible in both themes and at 360 px"** — the value arc resolves `rgb(22, 163, 74)` / `rgb(74, 222, 128)` on both pages against a track of `rgb(223, 215, 200)` / `rgb(42, 48, 64)`, none the SVG default; a mutation painting the track with `currentColor` too fails because *the gauge reads as a plain circle with no reading in it*. Body overflow 360/360 on both pages, the arc's inked box inside its own viewBox at both sizes, and the whole of it re-measured through a scripts-blocked context in **dark** mode. **Three degenerate cases handled where both arc mechanisms fail:** fraction 0 emits no value arc at all (a zero-length dash renders as a *dot* under a round cap), fraction 1 emits a complete circle with no dash pattern (an arc `<path>` whose sweep is the whole circle draws *nothing*, so full would read as empty), and `stroke-linecap: butt` is declared explicitly because a round cap would draw ~12% of the circle for a 5% reading. **A device with no reading renders NO ring** — an empty ring reads as 0%, a false statement about a device that has simply not checked in — and that page is byte-identically the page it was before (three cases, 1210 chars each on Home) |
| CFG-41 | Phase 24 | **Complete (24-05) — and read this row's first sentence before assuming otherwise, because the roadmap's D8 wording and this requirement's wording differ on the one clause that matters.** This requirement asks for **"a filled area under the line"**; the roadmap's goal sentence asks for a **"gradient area"**. The area shipped **flat** — `fill: currentColor` at `fill-opacity: 0.14` — so this row is complete as worded and the roadmap's gradient clause is recorded as a deliberate non-build in the D-item ledger below. **The ground for refusing the gradient:** a `<linearGradient>` is only referenceable as `fill="url(#id)"`, and `battery_sparkline_svg()` carries a standing, directly-asserted guarantee that its return value contains no `url(` — a literal substring scan with no scheme analysis to appeal to. Shipping the gradient meant relaxing a security-shaped assertion for decoration; it was not relaxed, and the property the clause actually names (*derived from the line's own colour, so it is correct in dark mode by the same mechanism the line already is*) is fully delivered — the area, the line and the mark are **measured resolving to one identical ink in each theme**, and a mutation making the area `#808080` fails naming all three. **"A filled area under the line"** — a `<polygon>` inside a nested `<svg viewBox="0 0 100 100" preserveAspectRatio="none">`, reached by experiment after two candidates were ruled out **without building**: percentages are illegal in a `points` list or a `d` string (the same rule that already makes the trend line `n-1` `<line>` segments), and nothing but `<rect>` takes percentage geometry so a per-segment trapezoid was unavailable. It is emitted **first in document order** (SVG paints in document order, asserted by index comparison rather than by reading a comment) and closes at **the scale's own floor**, `sparkline_point_y(SPARKLINE_Y_MIN_MV)`, never the canvas edge — a mutation closing at the edge fails naming both corners, because the edge adds the vertical inset to every reading as a constant. Its visibility is measured as a **composite over the card's own background** run through the app's own `contrast_ratio()` — 1.3317:1 light, 1.4955:1 dark, against a 1.20:1 floor **located by sweeping alpha** (first missed between 0.08 and 0.09), because a resolved-paint reader is structurally blind to "painted but invisible" and would pass at `fill-opacity: 0.001`. **"An explicitly marked last point"** — the newest *plotted* point, from the final iteration of the existing loop: same element, one class and one radius different (5px against 3px), never a second circle appended afterwards, and `is_latest` feeds the mark **and** the roving `tabindex` so the marked point and the Tab stop are the same point by construction. It **survives the dense-day suppression rule**, which is the whole reason it is drawn, and carries its own class rather than a modifier on the suppressed one so "suppress the dots" and "keep the mark" cannot become one instruction. **"A drawn low-battery threshold the latest reading is judged against"** — a full-width `<rect>` in `var(--color-status-warn)` at `sparkline_point_y(battery.LOW_BATTERY_DISPLAY_MV)`; the value is **read from `companion/battery.py` and never re-typed** (a mutation typing `3480` beside the chart fails), and because one function places the threshold *and* the readings the comparison is geometric rather than asserted — a threshold with its own arithmetic drifts from the plotted line by exactly the vertical inset. The judgement is also stated in words: the readout's own `battery_status()` verdict already colours the ring beside it. Out of range, the threshold is suppressed **entirely — line and label** — rather than clamped, because a clamped threshold pins to the axis edge where it reads as a threshold AT the chart floor. **"Without losing"** the three things named: the outer canvas still carries **no `viewBox`**, the per-point keyboard path is intact (the radius pin became `r="3"`×4 / `r="5"`×1 / `r="8"`×5 — every hit target absolutely sized and none shrunk), and the daily-average/raw-readings fallback is untouched. **One clause was built differently from the plan's own reading and the reason is measured:** the threshold's label is a **legend in its own full-width grid row**, not a third Y-axis tick — `.sparkline__y` is `justify-content: space-between`, so a third label lands at 50% while the threshold sits at **59.25%**, and pinning it to its real level needs an inline `style` attribute the drawing vocabulary refuses by name. A legend claims no position, so it cannot claim a wrong one; its swatch carries the same token and the same 1px height as the drawn rect, asserted in a browser, and it is deliberately **not** `aria-hidden` unlike every axis label, because every point already announces its own value and nothing anywhere announces where "low" starts |
| CFG-42 | Phase 24 | **NOT ticked — the drawing is built and measured, and one item in the requirement's own parenthetical was deliberately never built.** Served by 24-06. **What holds:** a 24-hour band rendered **server-side** from `history.db`, bucketed by the **Europe/Paris** calendar day (a UTC bucket drops today's 00:30 check-in *and* picks up tomorrow's — the same count from the wrong rows, asserted in both directions at once) and placed by `draw.percent_time()`, this phase's only time-domain scale, which **rejects** an out-of-day instant rather than clamping it because clamping invents a check-in at an edge of the band. **The held quiet-hours window** shades as **two** spans when it crosses midnight, never one — one span from 22:00 back to 07:00 has a negative width, and the obvious repair (swap them) shades the whole day and leaves the night clear, which looks entirely plausible; a mutation producing the single inverted span fails naming exactly that. **Readable with scripts blocked and at 360 px** — measured through a scripts-blocked context: 1 frame, 2 spans, 5 marks, all still painting real dark-mode tokens; the canvas 278.00 × 24.00px with every mark and span inside it; body overflow clean in both languages. The band never claims a count it does not show: the emitter **returns the number of marks it collapsed** and the caption is asserted to admit a merge on a dense day **and not to on a sparse one** (a caption that always admits one tells the reader nothing and is untrue on every sparse day). A day with no check-ins renders an **empty band, not an absent section** — an absent section reads as an unbuilt feature and an empty band reads as no activity, and those are different statements. **THE UNMET CLAUSE IS "detections."** The requirement's own parenthetical is "(check-ins, the held quiet-hours window, detections)"; two of the three are drawn and the third is not. This is a **deliberate non-build with a recorded ground, not an oversight**: it was taken provisionally at planning as 24-RESEARCH.md's open decision 5 and honoured as scoped by 24-06, on the argument that a detection mark and a check-in mark on one band is **two mark vocabularies in a 278px canvas** — and the planning-time figure for that canvas was ~330px, so the real measurement makes the argument stronger rather than weaker. At the shipped `DAY_BAND_MIN_MARK_SPACING_PERCENT` of 1.5 the band resolves ~22-minute intervals at best and holds at most **67** marks; a second vocabulary would have to share that. **The decision this needs:** amend the clause to "(check-ins and the held quiet-hours window)" and record detections as a separate, later item with a design for telling two mark vocabularies apart — or schedule that work and keep the clause. What must not happen is the box being ticked with "detections" still in it |
| CFG-43 | Phase 24 | **Complete (24-03, the readers; 24-07, the grid) — and the wording was checked clause by clause against what was built rather than assumed to match, because this is the requirement most at risk of being ticked for a drawing that claims more than it can.** Note first what this row does **not** say: it does not ask for a punctuality *metric*, it asks that punctuality be **"reported only as far as the stored data can prove it"** — a constraint of honesty, which is exactly what shipped. (The roadmap's own goal sentence says "wake-punctuality grid"; that phrasing is superseded, with its ground, in the D-item ledger below.) **"Computed from observed check-in gaps"** — `history_db.check_in_gaps()` reads **every** `device_health` row, not the battery-filtered subset a chart legitimately uses (a missing `X-Battery-Mv` header is not a missed wake; the mutation adding that filter merges two 30-minute intervals into one 3600 s gap that renders as a missed wake the device never missed). The series is re-sorted by **ingest id, not by `ts`**, because `ts` is attacker-influenceable and `id` is the order Caddy appended the lines — under `ORDER BY ts` a hostile row sorts after every ISO timestamp, making two real check-ins adjacent and **manufacturing** a missed wake. An undatable or out-of-order bound makes its spans **unknown** rather than dropping the row, since dropping merges two real intervals into one false long one. **"Judged against the cadence in force"** — `wake.classify_check_in_gap()`, which derives its thresholds from the **same** `device_staleness_thresholds()` the Frame tile already uses, so the tile and the grid share one function rather than two consistent copies; that reuse is pinned by reading the **compiled** function's `co_names`/`co_consts` rather than its source text (a text scan failed against a *correct* implementation whose docstring explained the reuse, and the obvious "fix" would have paid for the check with the documentation). Both boundaries are asserted **exactly at** `warn_s` and `error_s`, and an unknowable gap reports **unknown, never on-cadence**. A day is judged by its **longest** observed gap — an average would hide the one six-hour hole a reader opens this page for. **"States in its own caption what it measures and what it cannot know (a rotated-away log range is not a missed wake)"** — three clauses, each **separately** asserted and each separately mutation-proven by removing it, and the third is verbatim the caveat this row names. The caption names the cadence it judged against, and names the **fallback staleness floors** rather than inventing a default when a deployment yields no cadence at all. The grid's **fourth state** is what makes the whole thing honest: a day the record says nothing about is **classified, not branched on** — `classify_check_in_gap(None, cadence)` already answers `unknown`, so there is **no branch anywhere on the page deciding a cell's colour**, and `cell_class()` falls to the no-observation class for anything unrecognised, never to on-cadence (which would report health from a value nobody recognised) and never to missing (which would accuse the device on the same). The two words this grid must never be renamed into are asserted **absent from the rendered page in both languages** by a check, not only by hand. **"No plan assumes an expected-interval history that this project does not store"** — held, and held twice over: the metric was changed rather than the schema grown (ledger below), and the forward-looking `wake_epochs` table 24-03 added is **read by nothing**, pinned by a check that fails the day any file under `companion/` so much as mentions it. **One caveat is deliberately not in the caption and that is recorded rather than hidden:** the reader's docstring names *two* things it cannot know, and the caption carries the first — the second ("no rows in this window" cannot be told from "the ingest did not run") is the same sentence from the server's side and would not change what a reader does |
| CFG-44 | Phase 24 | **Complete (24-08) — as WORDED, and the distinction matters, so read the last third of this row before concluding otherwise.** Every clause: **"one composition"** — `.home-overview`, a grouping container holding the shared Frame strip, the three status tiles carrying 24-04's ring, and 24-06's day band. It is expressed as **proximity and asserted as two numbers**, not left to the eye: the parts sit one `--space-md` (16px) apart *inside* it and it sits one `--space-lg` (24px) *above* what follows — bound tighter than it is separated — and both are asserted as **equalities**, which is what caught the real defect below. It deliberately has **no surface of its own**: two of its three parts are already cards and the third is a grid of three more, so a background and a border would be a card holding cards — and the way out (taking the band's own card away) **widens the band's canvas**, silently invalidating the 278px `draw.DAY_BAND_MIN_MARK_SPACING_PERCENT` was re-derived from. **"Assembled from the same emitters this phase defines elsewhere"** and **"never a second copy of any of them"** — proven **behaviourally** rather than by grepping for a call, because two files can both import an emitter and still draw two different pictures: replace a class constant inside `companion/draw.py` and **both the hero and the page the emitter was borrowed from** change (verified by hand — one edit, `drawing-ring-value` → `MUTATED-ring-value`, two pages, two different sizes, 36px and 72px). A simulated fork (the ring's markup inlined into `home_page.py` with the real class strings) fails **both** a structural check and the behavioural one, a second estimator copied into the page fails, and even importing the estimator **unqualified** fails, because a bare `from companion.battery import battery_percent` makes it read as the page's own. The structural scan reads **string literals with docstrings excluded**, after a first draft failed on the page's own prose — `draw.DRAWING_GRID_CLASS` is the single word "drawing". Also held: the frame verdict is still rendered **exactly once**, asserted in **both** languages, and the French half is not redundant coverage — a mutation duplicating the verdict *only when the catalogue translates it* left every English verdict check in the repository green. The DB-read count is unmoved at **3**. **THE CLAUSE THAT COULD NOT BE BUILT IS THE PLAN'S, NOT THIS REQUIREMENT'S, and it is recorded here so the distinction is visible rather than convenient.** 24-08-PLAN.md's own wording — *"the stack is a floor behaviour rather than the only behaviour"* — reads as a hero that becomes multi-column on the desktop. Measured, it cannot be: the hero is **880.00px at a 1280px viewport**, so a one-third column (880 less the rule's own 16px gap, ÷3) is **288px**, against the **310px** a band *card* needs to keep its canvas at 278 — the canvas would come out at **256px**, making the band **narrower inside a wide desktop hero than it is at the 360px floor**. That is the "fits by shrinking its parts" failure arriving through the desktop rather than the phone. So the hero is **one column at every width**, and the floor-vs-not-floor property is asserted of its **parts** instead (the three tiles take three rows at 360px and share one row at 1280px; the band's canvas goes 278px → 830px, more room as the viewport grows, never less). **This requirement as written contains no stacking clause at all** — it asks for one composition, the same emitters, and no second copy — so the tick is honest; the plan-level clause is carried in the D4 row of the ledger below as a plan assumption measurement refuted. *(A related figure was wrong in a first draft and is corrected of record: 928 was read off a mutation's failure message, where it is a child's **left edge**, not the container's width. A mutation's message is evidence about the clause that fired, not a measurement of anything else in the sentence.)* |
| CFG-45 | Phase 24 | **Complete (24-02 built the measurement half; every drawing plan asserted it; 24-09 closes it).** **"Every drawing renders with scripts blocked"** — measured through `_no_js_page()`, not inferred from "it is server-rendered": the ring on both pages, the chart's mark, the band's frame/2 spans/5 marks, the grid's cells and the hero's every child, each also read in **dark** mode, on the stated ground that dark + scripts-blocked is the combination most likely to be wrong. The phase added **no script at all** — the deferred-script pin is still **14**, its pre-phase value, which is the number server-rendered SVG was chosen to hold still. **"Fits 360 px with no horizontal scrollbar on the page body"** — one shared assertion (`_assert_no_page_overflow`) rather than five slightly different ones, measuring `documentElement` to match both pre-existing page-level checks; Home and Health both 360/360, in **both languages**; proven to fire (a 420px ring takes Health to `scrollWidth` 516 against 360) and proven **not** to fire on a deliberately-scrollable `.data-table-wrap`, so it cannot start disagreeing with the wrap-level check that owns that question. **"Takes every colour from the theme tokens so it reads in BOTH themes"** — this is the clause that had never been checkable before this phase: until 24-02, **no browser check in this project had ever switched theme**, so every dark-mode claim rested on reading CSS. Sixteen resolved paint values across the phase's drawings, none the SVG default, in both themes; the helper that produces them **refuses to return unless the two themes genuinely invert**, so the vacuous state (every "differs between themes" assertion comparing a value to itself while printing PASS) is unreachable rather than unlikely — and it caught a real defect in itself on its first run, before any caller existed. Translucent fills are measured as **composites over their own background** through the app's own `contrast_ratio()`, because a resolved-paint reader cannot see "painted but invisible". **"Spends only from the existing motion budget"** — it spends **nothing**: the `.drawing*` block declares no `transition` and no `animation`, and `@keyframes` is still 4, `reduce` blocks 2 and `no-preference` 1, exactly where Phase 23 left them. **"The design system is updated in step"** — discharged by this plan: four `sketch-findings-skypane` files, every number read live from `companion/draw.py`, `companion/battery.py`, `companion/static/style.css` and the harnesses at execution time, every supersession marked **in place** with its reason and nothing deleted (nine removed lines, each one an amended line, verified by diff). **Two things this row does not claim:** the human sweep is the developer's and has not been performed, and CFG-39's single-drawing-module clause is unmet — this row asks about theme, floor, script and motion, and those hold for the chart exactly as they do for the four drawings that go through the shared module |
| CFG-46 | Phase 25 | **Complete (25-01 built it; 25-03..25-07 each registered against it; 25-08 closes it).** `grep -l CFG-46 .planning/phases/25-*/25-*-PLAN.md` returns 25-01 and 25-08. Every clause, checked against the code at close rather than against the plans. **(1) "the server renders every submitting control unconditionally"** — `companion/test_companion_app.py`'s `_NO_JS_CONTROL_REGISTRY` carries **six rows for five controls** (D17 holds two values in two inputs, so it owns two rows) and asserts per row that the named field is present in the group builder's own returned string. **(2) "the enhancement writes into it and never holds the value"** — exactly **one** `.value =` assignment in `companion/static/value-controls.js`, and the pin was **strengthened rather than satisfied** when 25-05 added a mirror: funnelling two writes through one helper would have kept the count at one while reopening what it guards, so the check now pins the *shape* (the assignment lives in `writeValue()`; exactly one `writeValue(field, ...)`; exactly one `writeValue(mirrorFor(wrapper), ...)`; the second asserted to lie **inside `paint()`**, strictly downstream of a value read back off the field). The script also writes **nothing at load** — every control's initial position is server-rendered, which is what makes the scripts-blocked render correct rather than merely present. **(3) "an affordance that cannot work without script does not render without script"** — `.js-gate { display: none }` / `.js .js-gate { display: var(--js-gate-display, block) }`, with `display` (not `visibility`/`opacity`, which leave a focusable ghost), the direction (hidden by default) and the `var()` fallback each mutation-proven; the gate class sits on the **gated element itself**, never an ancestor, so the nesting mistake is removed rather than detected; and every gated wrapper is measured in a real browser in **both** directions — zero height and zero focusable descendants in a 24-step walk of the real tab order with scripts blocked, a real box with scripts on. **(4) "a machine fails the build when any of those is violated"** — the registry is **non-vacuous on the day it landed**, proven against four fixtures built from real group-builder output (one correct control it must accept, three it must reject) plus five mutations, two of which (D and E) disable the guard's *own* assertions and are caught. **(5) "the whole phase spends ONE new static script"** — `ls companion/static/*.js | wc -l` is **16 → 17**, verified by diff against the phase's base commit `f7d25d9`; D16 spent **zero**, D5 grew `theme-preview.js` (+71 lines) and D19 grew `panel-lookup.js` (+283), each because that file already owned the subject and each recording why in its own header. **(6) "whose three taxes are paid once"** — the deferred-script pin moved **14 → 15 exactly once**, in 25-01, retargeted in place (the shell's script list is a fixed-arity `%`-format template, not a loop, which is recorded); the route is pre-auth like its sixteen siblings and is asserted to **behave like** an existing static route (200, `text/javascript`, `max-age=300`, no session) rather than assumed, with the ES5/forbidden-sink guard covering the file. **One nuance stated rather than glossed, because the clause names three taxes and one of them cost nothing:** the French-catalogue tax was assessed once and came to **zero** — `companion/i18n_fr/common.py` was listed in 25-01's `files_modified` and was **not touched**, because the script produces no user-visible literal at all (`aria-valuetext` is filled from a server-rendered, already-translated template on the wrapper, and with no template **no** `aria-valuetext` is written rather than an English sentence invented in the script). That is a stronger outcome than paying it, not a skipped payment: every literal the file declares is a hyphenated attribute name, a custom property or a token with no letters, all excluded by `test_i18n.py` Check 6's own rule, and that harness is 24/24 unchanged across the whole phase. |
| CFG-47 | Phase 25 | **Complete (25-03) — as WORDED, and read this row's second half before concluding otherwise, because one word in the requirement describes a shape that is impossible in HTML.** `grep -l CFG-47 .planning/phases/25-*/25-*-PLAN.md` returns 25-03 and 25-08. **"the three strips are the same native radios, so selection, arrow-key navigation and saving all work with scripts blocked"** — the strongest clause and the one fully met: the three `<input type="radio" name="tracked_runway" class="visually-hidden" form="settings-form">` are **untouched**; the map is a drawing wrapped around them. Measured, at 360 px, in **both** shipped languages, with scripts blocked: `'3'` → `'06-24'` → `'3'`, operated natively, submitted through the real form and **read back off the state directory after a genuine second GET**. The nine maps and twenty-seven strips on that page are asserted **after** the save, so the rendering can never stand in for it — and the mutation that proves the check tests *saving* rather than rendering is M20 (the radios lose `form="settings-form"`: the map still draws perfectly and the check fails anyway). Keyboard: one ArrowDown moves the radiogroup to the registry's next entry and ArrowDown/ArrowDown/ArrowUp returns to it, with **zero pointer events** and the recorder proving itself alive. **"the map's bearings derive from the designators already in the registry, so the drawing cannot contradict its own labels"** — `runway_bearing_deg()` parses the **LABEL before the id**, because Orly's first entry is keyed `'3'` (an ADP number) and labelled `Runway 3 (07/25)`. The source order is pinned by a registry where the two sources genuinely **disagree** (id `31-13`, label `Runway 9 (07/25)`), which is the fixture the first draft lacked — swapping the two sources against the shipped registry changed no angle at all. A pair that is not reciprocal is refused rather than drawn, and the emitter decides **no colour in Python**. **"every strip is a real touch target at 360 px, measured"** — measured by real `elementFromPoint` hit-testing in the runway row, never inherited from a class: **90 × 201 / 89 × 197 / 88 × 197**, all three clearing the 44 px floor by a factor of two in one axis and four in the other. `references/control-density.md`'s **exempt-by-delegation** category keeps its precondition and needed no new entry. **The one word re-scoped, with its ground: "one drawn map" renders as one map drawn three times, once per card, and it could not have been otherwise.** An `<svg>` cannot contain a `<label>` or an `<input>`, so a single shared canvas with three labels floated over it was the only literal reading — and it would have put all three touch targets on absolutely-positioned overlays at 360 px, which is precisely the hit-area failure this requirement's own third clause exists to measure, engineered in deliberately. The alternative reading (each card draws only its own strip) keeps the control intact and answers none of the question, because three strips side by side still do not say where these runways *are* relative to each other. So **each `.runway-card` carries a complete map of all three runways with its own picked out**, and comparing cards compares highlights on one shared picture. The measured consequence is the opposite of a cost: the cards got **taller**, which is why the hit areas rose from 25-02's pre-map 88 × 138. `runway-map__strip--this` means *"this card's runway"* and is present on every card selected or not — a check proves `runway_fieldset(None)` renders a map with nothing claimed rather than defaulting to one, which is the same check that proves the class did not quietly become a selection marker. **Two further deviations from plan sentences, recorded rather than quietly adjusted:** the caption claims relative bearings and north-up and deliberately does **not** claim relative lengths, because `device_config.RUNWAYS` carries no length for any entry and inventing plausible ones would be the dishonest-state defect the sentence exists to prevent (every strip is drawn the same length); and the selected strip pays in **INK** (30 % → 55 % → solid `--color-text`), never in accent, so the stylesheet's accent-reservation list is unchanged by this plan. The three `runway-*.png` photographs keep their slot, their route and their files (Decision 2), measured serving at `naturalWidth` 1672 through the session-gated route. **RETIRED 2026-09-14 (Phase 27).** This row's verdict is unchanged and is not being rewritten: the requirement was met as worded. Phase 27 withdraws the requirement itself after the developer reviewed the deployed app and found the map taught him nothing his own schematics did not already. Met-then-withdrawn is recorded as its own outcome, distinct from "not met" and from "deleted". The successor is CFG-66, which removes the drawing, names every check that comes out with it, and keeps the radios' scripts-blocked save-to-disk proof. |
| CFG-48 | Phase 25 | **Complete (25-04).** Every clause measured, none inferred. `grep -l CFG-48 .planning/phases/25-*/25-*-PLAN.md` returns 25-04 and 25-08. **"a 24-hour dial whose arc is drawn by the server, so the window is visible with scripts blocked and only the drag handles are withheld"** — the ring is server-drawn from `quiet_hours_start`/`quiet_hours_end` and sits **outside** the gate; only `.quiet-dial__handles` is gated. Measured with scripts blocked at 360 px in both languages: the gated handle layer has **zero height and no keyboard can reach into it**, while the **arc, the readout, both time inputs, B14's two 24-hour siblings and the three presets are all present** — asserted after the save so none of them can stand in for it. The vacuity fix behind that clause is worth recording: the first version counted DOM elements with `locator.count()`, which passes against the arc **moved behind the gate** — the exact refactor the clause exists to notice — so it now measures the rendered box (M33). **"the two native time fields stay visible and stay what the form posts"** and **"B14's visible 24 h sibling survives"** — proven **byte-identical**, not asserted: `quiet_hours_group()` was loaded from `HEAD` under a second module name and rendered beside the new one, and the new output with only the two new fragments removed compared byte-for-byte across **five** argument shapes including the D-07 rejected-save path and the empty-window path (`ALL IDENTICAL: True`). The durable half is a named check exercised by M14 (the ring moved below the End field), which asserts the card's order by measured document positions. **"the window that wraps midnight is measured as the short way round"** — `quiet_window_span()` returns one triple and the **drawn sweep is derived from the returned minute count inside that one function**, so the picture and the printed duration cannot disagree (M2). 23:00 → 07:00 is **480 minutes forward through midnight** (`(end - start) % 1440`; an `abs()` implementation returns 960 and an `end - start` one returns −960). Equal ends are **0**, never a whole day, and a zero-length window draws **nothing** — a zero-length dash under a round cap is a DOT, so "no window" would read as a few minutes. Cross-file agreement is asserted by **reconstruction**: the span is rebuilt from what `server/device_config` has left at five shared instants on **both** sides of midnight, which is what makes the server's own wrap branch drifting (`days=1` → `days=2`) fail — it failed **nothing** until that vacuity was fixed. **"the handles announce through `aria-valuetext` rather than a live region that re-reads on every step"** — the readout is `aria-hidden` and `role="status"` on it is refused by name (M12); each handle is a real `<button type="slider">`-shaped control carrying `role="slider"` and the `aria-value*` set, with `aria-valuetext` the local **HH:MM** and never the raw minute count (M22). One real defect was found here and fixed: `paint()` announced on the **wrapper** rather than on the focusable handle, so a screen reader would have read the *saved* value on every step of a drag that had already moved somewhere else — measured as the handle announcing `23:00` while its own input held `12:00` (M30). **Four deliberate departures from plan sentences, each argued rather than smoothed over:** Page keys move **150 minutes** (ten steps of 15) and not the plan's 60, because the same plan's binding constraint says the model must match the native range one 25-05 would inherit and the two sentences cannot both hold — see CFG-49 for the correction of record that the native rule is a **percentage of the band**; there is **no minimum separation** between the handles, deliberately, because a zero-length window is a real defined state and refusing it here would make a state reachable by typing unreachable by dragging (z-order is document order, the END handle is emitted second and wins an overlapping pointer-down, and the start handle stays its own tab stop — measured focusable at 15 minutes' separation where its own centre hit-tests to the end handle); the dial is **176 px, not 128 px**, which is geometry rather than taste (two 46 px hit boxes need ~45 px between centres, so on a 128 px ring the handles cannot both clear the floor until the ends are ≈ 4 h 49 apart, against ≈ 3 h 12 at 176 px); and the registry took **two** rows rather than the anticipated one, because a row names one field and this control holds two. **One defect only a browser could have found, and it is the reason this requirement is ticked on measurement rather than on reading:** a preset that writes into the two fields was supposed to move the handles for free. It did not — assigning to `.value` from script fires **no event of any kind**, so `dirty-state.js`'s preset handler moved both inputs and left both handles where they were. The fix stayed inside the design (`value-controls.js` repaints on `change`/`input`/`click`, learning nothing about presets) and `dirty-state.js` is untouched. Measured after: a preset click moves both fractions. |
| CFG-49 | Phase 25 | **Complete (25-01 built the arithmetic in `companion/battery.py`; 25-05 built the slider and the two gauges; 25-08 closes it) — and the clause this requirement was most at risk on is the one it holds most strongly.** `grep -l CFG-49 .planning/phases/25-*/25-*-PLAN.md` returns 25-01, 25-05 and 25-08. **"the wake interval is steered by a slider"** — a real native `<input type="range">` inside the `.js` gate, `min`/`max` interpolated from `device_config` and asserted against the module rather than against literals (M14). Measured end to end in a real browser: a drag across 55 % of the track moved the number input `300 → 3060`; with the range-to-number write disabled the same drag leaves it at `600` and the check says so. **The script's job here is syncing, not steering** — all three gesture listeners **stand aside** for a wrapper declaring a native mirror, because `preventDefault()` on a `pointerdown` over a native range cancels the browser's own thumb drag and a prevented `keydown` steps the value twice per press. **"freshness stated as a bound ('at most N minutes')"** — the words *at most* are asserted to be in the **wording**, not merely in the docstring (M2), because a bound stated without them is a claim about typical behaviour and nothing in this project measures that. The minute conversion rounds **UP** (M1): a 90-second cadence bounds the wait at a minute and a half, and `90 // 60` prints "at most 1 min", which is false. Both gauges and the slider are fed by **one** `wake_gauge_interval_s()` call, so they cannot describe different values. **"battery life stated only as far as this device's own observed history supports, with a named 'not enough history yet' state instead of a figure invented from a per-wake cost nobody has measured"** — `battery_life_estimate()` returns **five NAMED states** (`no-reading`, `not-enough-history`, `rising`, `flat`, `falling`) and **only `falling` carries a number**, derived from this device's own observed daily-average discharge slope over a **14-day** window behind two floors (`LIFE_MIN_OBSERVED_SPAN_DAYS = 2`, because a one-day delta between two daily *averages* is inside this series' own noise; `LIFE_MIN_OBSERVED_DROP_MV = 10`, because a 1 mV fall over three days divides out to roughly five years, which a reader takes as a promise — and without it a flat series divides by zero). `rising` carries **no** number deliberately: a charged device has a positive slope, and dividing by it gives a negative or an infinite lifetime, both of which a reader would act on. **No per-wake energy cost is assumed anywhere.** The audit's own "≈ 38 days" was therefore **not computed**, and the figure the card does print wears the `≈` marker the battery percentage already wears (M7) and names its source. **And the honesty is STRUCTURAL rather than promised, which is the part worth carrying forward:** the absolute "≈ N days" sentence is rendered by the **server, outside every readout element**, and the script never touches it; what the script may rewrite is a `<span>` whose template names two cadences and contains **no days figure at all** (M18 refuses a readout handed the days wording). So "if the server said *not enough history*, the script keeps saying so" is not a policy a future editor has to remember — there is no template through which it could say anything else, and a check asserts exactly that. The live clause names **two cadences rather than a ratio**, which dissolved three problems at once (no decimal, therefore no locale-specific decimal mark travelling to the script; no rounding rule needing `Math.round` half-up and Python's `round` half-to-even to agree at a tie this control really reaches, 1260 s against 1200 s being exactly 1.05; and one wording instead of two). `relative_factor` is still consumed — as the **guard** deciding whether there is anything to say, not as the number. **"the number input remains the only thing that posts"** — the range carries **no `name`** (M11: it would post a second value for the same setting and whichever arrived last would win, silently), and `dirty-state.js`'s own snapshot skips nameless controls. The number input is **byte-identical** across six argument shapes (M10 fails on an added `inputmode`). **"its out-of-range guard still protects the whole Settings form"** — re-proven end to end in a real browser with **30 s on disk** (a state the supported paths cannot produce, so the check writes the config file's JSON directly and restores its exact previous bytes, and says so at the call site): the number input carries **no `value` attribute**, no range and no gauge render at all, and the whole Settings form still saves a corrected value. A submitted `"7"` likewise renders no gauge, because a gauge about seven seconds describes a cadence this device cannot be configured to use (M5). **Three things recorded rather than smoothed over.** (a) **`role="slider"` is refused by name** on the native range (M12) — it is already a slider with its own `aria-valuenow` and its own keyboard model, and a role on top is the classic double-role error. (b) **Correction of record, measured:** the native **Page** key moves **10 % of the band**, not ten steps — from 60, `PageUp` lands on **420** (six steps of 60 on a 3540-wide band), which coincides with "ten steps" only when a band is about 100 steps wide, as 25-04's dial's ~96-step band nearly is. No script Page handling was added, because that would mean preventing the default on a native control. (c) **A function NAME tripped an existing guard and the guard was right:** `wake_battery_life_text()` failed the battery one-home check by its name alone and was **renamed** (`wake_battery_observed_text()` — it does not compute a lifetime and should not claim to), **not allow-listed**, because an allow-list entry would have let a real second estimate in under that name later. **The developer still owns the WORDING**, which 25-05 named as the item most needing a human's eye, and **DEVICE-05's discharge run (closing 2026-09-23) supplies the measured mAh-per-cycle figure** that would let a later plan add a second, model-based branch inside the same module and print it through the same wording — **the gap is in the data, not in the presentation**, and nothing in this card has to change to accept it. See decision 3 in the ledger below. |
| CFG-50 | Phase 25 | **NOT ticked — three of five clauses hold outright, one is contradicted by a shape that is impossible in HTML, and the one the requirement names as its own judge returns a FAILURE.** Served by 25-06; `grep -l CFG-50 .planning/phases/25-*/25-*-PLAN.md` returns 25-06 and 25-08. **This row's own planning text is carried forward rather than replaced, because it turned out to be right:** this requirement is X6's deferred half, and 22-10 had already recorded that the page-height target "is NOT met and cannot be by density alone — folding the grid behind the big preview is D5". The folding was done; the target is still not met. **Holds: "a scroll-snap carousel over the one existing chip grid"** — `_theme_carousel_html()` wraps `_theme_chip_grid_html()`'s existing output and **emits no chip**; a source scan finds **exactly one** function in `config_page.py` emitting a chip `<label>` carrying `data-preview-src` (M13 forks a second and fails), and the arrivals, calendar and rule-add grids were captured before the change and diffed after — **three of three byte-identical**. Swipe is native (CSS scroll-snap) and keyboard selection is native (a radiogroup's own arrow keys): measured, one, six and seventeen ArrowDowns each landing on the registry's own next theme with **zero pointer events** and the recorder proving itself. **Holds: "the stylesheet's single `:has()` feature query still single"** — **1**, brace-anchored and comment-stripped, verified live at this phase's close against the base commit's own 1. This was the phase's single highest-risk assertion and it was **never even approached**: the disclosure reaches the strip through an adjacent-sibling combinator on its own `[open]` state, so no `:has()` is involved at all. (A bare `grep -c` returns **6** on this file — one block plus five comment paragraphs quoting the at-rule — which is `references/settings-page-patterns.md`'s own stale-number warning running in the other direction.) **Holds: "the compact chip still size-only"** — M8 adds a `:has(input:checked)` to a `.theme-chip--compact` rule and fails by name. **CONTRADICTED BY A SHIPPED DECISION: "with the full set behind a native disclosure that opens with scripts blocked".** The disclosure is native and does open with scripts blocked (measured: it opens on a click and turns one row into a real grid holding the same eighteen radios). But **nothing is behind it, at any time** — every theme is always in the strip, always reachable by arrow key, always selectable, always saveable. **The plan's own recommended shape is impossible as literally written**, and that is the ground rather than a preference: a closed `<details>` hides its own non-summary children, so a disclosure *containing* the grid would hide all eighteen themes whenever it was shut and there would be no strip at all — the exact opposite of what the same sentence asks for. The shipped mechanism is the opposite arrangement (`.theme-carousel__all[open] + .theme-chip-grid--strip { flex-wrap: wrap }`), **one** set of eighteen radios rather than two: two sets would put two `--selected` chips, two check glyphs and thirty-six chip images on a page for a setting with one value, and open a duplicate-id surface (T-25-06-B). The honest consequence is recorded at the markup site as well as here, in real translated text: **the disclosure changes a LAYOUT, not a VISIBILITY.** **FAILS, AND IT IS THE CLAUSE THIS REQUIREMENT NOMINATES AS ITS OWN JUDGE: "judged by Display's MEASURED page height rather than by the carousel's existence".** The judging was done properly — `_display_page_height()` is a registered instrument, built in Task 1 **before there was anything to like**, asserting no target at all and asserting four things about where its number came from (the measurement was taken at the width asked for; the document is the authenticated Display page, proved by its Frame colours heading **and** a full `THEME_IDS`-sized departures radiogroup rather than merely "a page rendered"; the document is taller than the viewport). Run before any markup change and again after, on the same tree: **390 px: 4276 → 3743 px (−533). 360 px: 4269 → 3752 px (−517).** **X6's phone target is ≤ 2600 px, so it is NOT MET — 3743 px is 1143 px over it — and D5's own audit row ("Display page drops below 1 500 px") is 2243 px away.** The carousel itself **costs** about 82 px (a 44 px `<summary>`, the dots row and the pager row) against the ~615 px the strip removes, and that cost is inside the −533 rather than hidden. Two things this number does not license: reading the before-figures as a regression (phases 23–25 added the runway map, the quiet-hours dial and other Display content between 22-10's own 3661 px and this measurement — the only comparison that means anything is before-vs-after **by the same instrument on the same tree**, which is exactly why the instrument exists), and moving the goalposts. 22-10 recorded its own shortfall; this records the second attempt's. **DECISIONS NEEDED, and there are two.** (a) **On the height:** accept 3743 px and amend or retire X6's 2600 px phone target; or schedule a further density pass against what is actually left (four more cards — Calendar, Runway, Quiet hours and the three other usage panels — plus the Frame strip above them), which is **not a grid** and has no win of the carousel's size available inside a control plan's scope; or re-word this clause to name the measurement rather than a target. The instrument survives either way and is reusable. (b) **On the disclosure:** amend the clause to say the disclosure changes a layout rather than hiding a set, or ask for something genuinely hidden — which would mean two sets of radios and the duplicate-setting surface 25-06 refused. **What must not happen is this box being ticked with either clause as written.** **Two further scope statements, so a future audit meets the reasoning rather than the idea:** the strip does **not** render beside the big live preview (moving the departures panel out of `.frame-colours__panels` would take it out of `theme-preview.js`'s four-panel collapse machinery, which is D-08's locked no-JS floor, for a horizontal adjacency that does not exist at either of the two viewports this criterion is measured at); and the arrivals, calendar and rule-add grids are deliberately not converted (already compact, already beside other controls, and none of them is the page-height problem X6 named — four carousels would have multiplied the `:has()` risk by four for no gain). |
| CFG-51 | Phase 25 | **Complete (25-07).** Every clause measured through a real Chromium, and the clause most likely to be faked is the one with three independent proofs. `grep -l CFG-51 .planning/phases/25-*/25-*-PLAN.md` returns 25-07 and 25-08. **"Artwork can be dropped onto the card"** — measured with a **genuinely trusted** drag: the handler refuses `evt.isTrusted === false` (compared against `false`, not negated, so a browser without the property does not refuse every real drag), and Chromium's DevTools protocol `Input.dispatchDragEvent` carries a real `files` list through the same input pipeline a pointer uses, so the same check measures the real gesture (`isTrusted: true`, `dataTransfer.files.length === 1`) **and** proves the synthetic one inert. The guard and the proof usually trade against each other; here they do not. **"dropping it is provably the same act as choosing it"** — proven three ways, and their **order of strength is recorded rather than assumed**: (1) the **static absence of every canvas API** in `panel-lookup.js` (`getContext`, `drawImage`, `toBlob`, `toDataURL`, `OffscreenCanvas`, `createImageBitmap`, comments included); (2) the file's **size in the input** on both paths (`1833 == 1833`); (3) a **byte comparison of what landed on disk**, with the stored file **deleted between the two uploads** or the comparison would have passed on the file left behind. The third is the *weakest* of the three and that was measured, not assumed: a deliberate one-byte client truncation did **not** trip it, because the server re-encodes every upload through Pillow, which absorbed it — the clause that bit was the in-input size, and byte equality was proven able to fire at all only by a harness-side mutation. The structural reason there is nothing to keep in sync: a drop constructs a `DataTransfer`, adds the `File` and **assigns it to the form's own `<input type="file">`**, so from that point it is the same multipart POST to the same route, the same cap enforced before the body is read, the same `parse_single_uploaded_file()` discarding the client-declared filename, the same validator reading the real PNG header. **One validator (`uploadRefusal`), exactly one definition, exactly two call sites**, asserted by source scan, with the refusal proven **textually to precede the assignment** and the cap **imported from `companion/app.py` at render time** rather than retyped. **"the file input still posts"** — both upload forms are pinned **byte-for-byte against retyped pre-25-07 literals** (never against whatever the builder currently emits, which would only restate itself): each rendering's `<input type="file" id name="image" accept="image/png" required>`, its single bare `<button type="submit">`, its hint paragraph, its `method`/`enctype`/`action` including the dialog copies' empty placeholder, and exactly one `<form>` each. **The one addition is an `id` on each form**, carrying the existing `id_suffix` where one exists, so the no-JS registry can *declare* this control's form association rather than guess it — that is the only attribute added to either form tag and it is recorded here because "byte-identical" was the criterion. Proven with scripts blocked at 360 px: a file chosen through the native input and submitted through the fallback panel's own form is **stored (read back off the real state directory, never off the page — a rejected upload redirects to a page that looks like success) and served back by the illustration route as an image at `ILLUSTRATION_TARGET_SIZE`**. **"the server's normaliser is still the only thing that decides how an illustration is framed"** — `companion/illustration_normalize.py` is **unchanged by one line across the whole phase**, verified by `git diff` against the phase's base commit `f7d25d9` (empty), as is `companion/app.py` against 25-07's own base. **"the preview shows the chosen file inside that frame rather than reimplementing the crop"** — the preview box reserves the module's own frame through an inline `--upload-preview-ratio`, read by `style.css` with **no fallback value** (a fallback would keep the box the right shape after the inline property stopped being rendered, masking the deletion of the live value rather than guarding it). Measured at 360 px, at rest, before any image exists: **3.4098:1** against the module's **3.4091:1**; after a drop the `<img>` decodes to the source's own 1200 × 300 with `object-fit: contain`. **The decision that mattered most, and the precedent it sets:** the preview is a `FileReader` **`data:` URL, not an object URL — and that was a MEASUREMENT, not a preference.** Run against the real app before the preview was written, Chromium answered *"Loading the image 'blob:…' violates the following Content Security Policy directive: `img-src 'self' data:`"*. So the plan's central mechanism would never have rendered — and the plan's own acceptance criterion (`createObjectURL` paired with `revokeObjectURL`, asserted by source scan) **would have passed against a broken preview**, because a pair of calls is a pair of calls whether or not the image ever loads. There were two ways out and only one is right for the one control on that page that accepts bytes from outside the app: **`companion/app.py` was not widened by one line for a thumbnail**, `data:` was already allowed for the inline favicon, and the object-URL leak the plan worried about does not exist to leak. The criterion was replaced by a **stronger** one — the file names `createObjectURL` nowhere at all, and the `<img>`'s `src` is **removed** (not merely hidden) on replacement, on refusal and on dialog close. **The one asymmetry, stated rather than hidden:** on the drop path the file is refused *before* anything is assigned; on the picker path the same validator runs and the same message appears but `input.files` is never touched — a drop is the script's own act, so declining to perform it is the script doing nothing, while a pick is the visitor's act through the browser's own control and silently discarding it would be the script undoing a person's input to spare them a server error it is not entitled to predict. The client check is a **courtesy** and says so in the file, refusing only what it positively knows is wrong and handing a browser reporting **no** MIME type to the server — failing open toward the real gate is the correct direction for a courtesy. **Three of the AUDIT's D19 clauses were deliberately not built** (the client-side canvas crop, the progress bar and the hover-only aircraft types) — none of them is a clause of this requirement, whose own wording positively requires the crop's **absence**, and all three are walked with their grounds and their reversal costs in the ledger below. |
| CFG-52 | Phase 25 | **NOT ticked — five of six clauses hold and are measured, and the sixth holds for FOUR of the five controls and is unmeasured for the fifth.** Served by 25-02 — the four browser-harness instruments this whole phase runs on (`_persist_without_js()` for operate-submit-**persist** under blocked scripts, `_operate_with_keyboard()` for keyboard-only operation with the pointer-free claim **measured** rather than promised, `_hit_area()`/`_assert_hit_target()` for real `elementFromPoint` measurement, and `_assert_js_gate()` for the two-direction gate assertion), added at **zero net checks** and each demonstrated against a live subject in both directions before any control existed — then asserted by every control plan, and closed by 25-08; `grep -l CFG-52 .planning/phases/25-*/25-*-PLAN.md` returns 25-02, 25-03, 25-04, 25-05, 25-06 and 25-08 (25-07 asserts the same floor for D19 and cites CFG-51 rather than this ID, which is why the one unmeasured clause below is D19's). This box is the phase's own regression floor, so it is held to the phase's own standard: **measured, not asserted.** **Holds: "every control is proven by SAVING with scripts blocked rather than by rendering"** — five named checks, one per control, all passing, all reading the value back **from disk** through the app's own loader after a real operate-submit round trip at 360 px (four of the five in **both** shipped languages; the fifth, the upload, in one). The three weaker sequences were each measured failing against a broken control before this shape was chosen, and the third is the trap: *"the reloaded page shows the value"* passes **on this app by design**, because `wake_interval_group()`'s own docstring records D-07 requiring a rejected submission's raw string be echoed back into the field. The five names are listed in 25-08-SUMMARY.md. **Holds: "meets its touch floor measured at 360 px"** — by real `elementFromPoint` hit-testing **in each control's own container**, never inherited from a class: runway labels **90 × 201 / 89 × 197 / 88 × 197**, both dial handles **45 × 45** (with the window's ends far apart *and* close together, plus the genuinely overlapping case answered rather than avoided), the range **279 × 45**, the strip's first and last chips **106 × 71**, both pagers **45 × 45**, the drop zone **241 × 154**. **Nothing was traded and no control landed below 44 px in either axis**; the register's four categories are unchanged and no fifth was needed. The clause earned itself three times over: the same `.control-hit-area` arithmetic resolved to **43 × 43** for the dial's handle (a rotate/translate pair landing it off the pixel grid — fixed by overriding the inset **upward** in that component alone) and to **30 × 45** for the Previous pager (the Next pager's own `::before` winning the hit test in an 8 px gap — fixed by the `--space-lg` gap, which is therefore a hit-target number and not a spacing one). **Holds: "reads correctly in both themes"** — measured, not read off the stylesheet, and **sampled only after the Web Animations `finished` promise** because the first attempts read interpolation frames twice in this phase (25-03 reported a theme that does not invert for a stylesheet that was entirely correct; 25-05 met the same defect on the global `input, select` transition). The map's eight settled values all differ between themes with three distinct paints inside each; the dial's day ring, arc, labels and grip all invert; the slider's `accent-color`, surface and canvas all invert; the carousel's chip name, chip surface, disclosure summary and pager chevron all differ; the drop zone's canvas, note, frame, surface and message all differ, with the refusal message at **5.73:1** light and **7.13:1** dark against the canvas. **Holds: "spends only from the existing motion budget"** — `@keyframes` **4**, `prefers-reduced-motion: reduce` blocks **2**, `no-preference` **1**, all comment-stripped and all identical to the phase's base commit. No new keyframes, no per-rule reduced-motion block, no `interpolate-size`, no `calc-size(`; the map's strip transition spends the existing `--motion-fast`. **Holds: "the design system is updated in step"** — 25-08 Task 1, across `SKILL.md` and four reference files, every number read from the code at execution time, every supersession marked in place and **zero deleted lines of recorded reasoning** (diff: 436 insertions, 11 deletions, every deletion verified to be a line re-stated in full and extended). **THE UNMET CLAUSE: "is operable from the keyboard with no pointer event at all" is measured for FOUR of the five controls and is unmeasured for the fifth.** Measured, with the pointer recorder proving itself alive on each: **D16** (one ArrowDown moves the radiogroup to the registry's next entry, `pointer_events: []`), **D17** (one ArrowRight `23:00 → 23:15`, `End → 23:59`, `Home → 00:00`, `pointer_events: []`), **D18** (one ArrowRight `3060 → 3120`, one 60 s step, `pointer_events: []`), **D5** (one, six and seventeen ArrowDowns each landing on the registry's own next theme, `pointer_events: []`, plus a scripts-blocked focus-and-arrow clause added because `HTMLElement.click()` works perfectly well on a `display: none` element and the prescribed mutation would otherwise have stayed green). **D19 has none.** Its control is the native `<input type="file">`, whose keyboard activation opens the platform's own file chooser; `_upload_without_js()` puts the file in through `page.set_input_files()` (CDP's `DOM.setFileInputFiles`, which bypasses the UI entirely) and **submits by clicking the real submit button** — a pointer. The drop zone itself is measured to add **zero focusable descendants** with scripts blocked, so nothing was taken away from a keyboard visitor; what is missing is the positive measurement this requirement asks for. **DECISION NEEDED:** either **amend the clause** to name what a headless harness can drive (and record the platform file chooser as the platform's, which is the honest reading — this app has no code between the keyboard and that input), or **schedule the measurement**, which may well be buildable: focus the input by Tab, press Enter inside `expect_file_chooser()`, and submit by pressing Enter on the focused submit button rather than clicking it. Until one of those lands, **this box stays unticked** — this is the standard Phases 23 and 24 held with CFG-34, CFG-37, CFG-39 and CFG-42, and the standard Phase 22 had to learn the hard way when CFG-28 was ticked and then un-ticked. |
| CFG-53 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-01 (the one new script with its three taxes paid once, the nav-derived command index, and the two executable structural contracts); asserted by 26-03 and 26-04, closed by 26-09 |
| CFG-54 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-03. Three of the four accessibility traps are closed by NOT writing code: `<dialog>.showModal()` supplies the focus trap, the top layer, Escape and focus restoration. The fourth (announcing on every keystroke) is Phase 23's own lesson from its three switches, and is answered with a count-only live region |
| CFG-55 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-04. There is deliberately NO touch equivalent for a keyboard shortcut: the bottom tab bar shipped in 22-14 already is the touch answer for navigation, and inventing a second gesture mechanism would duplicate it and brush against the overlay drawer's standing refusal |
| CFG-56 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-05. The audit's "password set ✓" item is NOT built as written: `auth.py:153` fails closed, so anyone who can see the checklist has a password by construction and the tick can never be absent. It is replaced by a comparison against `deploy/skypane.env.example`'s placeholder. "Frame paired" describes a concept this companion does not have (provisioning is BLE, in the firmware) and resolves to `frame_state`'s existing `STATE_UNKNOWN` |
| CFG-57 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-06 (the emitter, the byte-identity proof, and the `companion/draw.py` precondition) and 26-07 (adoption across all six call sites). This requirement is why Phase 26's real dependency is Phase 23 AND Phase 24, not Phase 23 alone |
| CFG-58 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-08. The privacy answer is that NO public URL is created: nothing expires because nothing is exposed, and nothing needs revoking because there is nothing to revoke. The picture is not neutral data — since Phase 16 a calendar match repaints the panel, so its colour can encode a private-calendar signal, which is what makes a shareable link a real disclosure rather than a theoretical one. The native share sheet is manual-only: `navigator.share` is undefined in the harness Chromium and absent from desktop Firefox |
| CFG-59 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-09. Half built, half refused in writing. D6's tab bar shipped in 22-14; only this leftover remained |
| CFG-60 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-09. Half built, half refused in writing. D11's hashed-filenames third was already excluded by the milestone's build-free constraint. The gzip check is a FILE-CONTENT assertion, weaker than this project's norm, because the harness never runs Caddy — reported honestly rather than implied to be a runtime proof |
| CFG-61 | Phase 26 | **DROPPED 2026-09-23 — Phase 26 abandoned at the developer\'s request before execution; never built.** Was planned — 26-02 (the harness helpers: focus restoration, announcement read-back, the unauthenticated-route enumerator, the targeted keystroke driver and the exhaustive destination sweep), then asserted by every later plan, closed by 26-09 |
| CFG-62 | Phase 27 | **Complete (27-02).** The pair is now the model: `value-controls.js` publishes a shared-ancestor fraction seam and derives the sweep `(end - start + 1) % 1`, so the arc, the handles and the caption decode to one canonical minute-of-day after a drag AND a preset, in both themes — proven by ONE check (`_the_arc_the_handles_and_the_caption_agree_after_an_interaction`), not one check per surface. The server-rendered arc's presentation attributes stay **byte-identical** — diffed, not assumed, across four windows including the wrap and the 1-minute floor, both at 27-02's own close and RE-VERIFIED at this phase's close (2026-09-15) after every later plan's own edits to `config_page.py` — still an exact match. The caption's duration BLANKS rather than lying (empty `data-value-readout-text`, both of `paintReadouts()`'s branches resolve to `""`) — PROVISIONAL per 27-02's own note, and the fallback (server-emitted per-unit templates, C2 in 27-RESEARCH.md) stays recorded for a reviewer who rejects the blanking. `QUIET_DIAL_RADIUS`'s stale comment ("64−7−3=54" beside a shipped 78) is corrected in the same commit (27-02, `2336074`). |
| CFG-63 | Phase 27 | **Complete (27-04), one clause RE-SCOPED by the developer's own binding decision, recorded rather than silently reconciled.** No save button anywhere on Settings; `change` (never `input`) drives the same optimistic-apply/fetch/exact-204-confirms model `quick-switch.js`'s switches already shipped, over the app's ONE existing failure vocabulary (the existing generic translated toast, never a new string) — mutation-tested (M-A/M-B/M-C, all three failing on the predicted clause). The status region's own text sequence is recorded via `MutationObserver`, never sampled only at rest, closing a real vacuity gap M-B found in the check's own first draft. **The leave-guard clause is RE-SCOPED**: the requirement's own wording anticipated retiring it "only where it means discard a pending edit"; the developer's explicit, binding decision (`.planning/ROADMAP.md`, 2026-09-15) instead keeps it alive IN FULL, because a keystroke that never fires `change` still needs the same protection the old bar guaranteed — proven still armed and disarming correctly at the right moment (`_leave_guard_arms_on_uncommitted_edit_and_disarms_on_change`). "Annuler" is gone outright (there is no more pending-edit state to cancel). |
| CFG-64 | Phase 27 | **Complete (27-03), re-verified UNCHANGED at this phase's close.** The native submit's emission is proven unconditional at the AST SOURCE level (one `return` statement, never inside an `ast.IfExp`, `STATIC_SAVE_FALLBACK_ATTR` a bare `Name`), not merely observed to render today. The fallback-hide CSS rule reverted to the plain `.js` gate; B1/P0's original two-marker visibility contract is SUPERSEDED IN WRITING (kept verbatim, a dated paragraph appended, no CSS selector literal quoted per D-30). The disk-and-submit proof (`_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies`) is confirmed **byte-identical** — same function body, same registration message — from the commit that created it (27-03, `b717aab`) straight through every later plan's own edits to the same file, verified by direct extraction and comparison at this phase's close (2026-09-15), and it PASSES in today's final full-suite run. |
| CFG-65 | Phase 27 | **Investigated (27-06), NO DEFECT FOUND — recorded as its own outcome, not as "fixed."** The executable inventory (`config_page.render()`, both scopes, counted against the rendered HTML) measured **7** card titles (form A, `[data-dirty-section] > h2`) and **3** supersection intros (form B, `layout.section_intro_html()`, shared byte-identical with `health_page.py`) plus 2 unclassified — confirming 27-01's own browser-driven 7/3/2, correcting 27-RESEARCH.md's provisional 8/3/2 (a grep hit at a call site neither settings route renders). The two forms are a genuine grammar distinction, not a duplicate: form B introduces MORE THAN ONE card ("Look" introduces both Frame colours and Calendar, which a card title naming exactly one card cannot do) and the two sizes (22px serif / 16px sans-semibold) are a developer-validated, three-round-trip heading ladder — reversing either direction means either editing `layout.section_intro_html()` away from a shape `health_page.py`'s own structural checks match literally, or undoing Phase 20's D-12 restructure, which this plan has no standing to reopen. **No markup was converted.** See the coverage ledger below for the full clause walk and the decision this leaves the developer. |
| CFG-66 | Phase 27 | **Complete (27-05).** `runway_map_svg()`/`runway_bearing_deg()`/nine `RUNWAY_MAP_*` constants and all seven `runway-map` CSS rules removed; every map-only check named and removed (3 per harness), two mixed checks mutated IN PLACE (map clause dropped, the still-live escaping/radiogroup/photograph proof kept), one new relationship check added asserting absence-of-map AND presence-of-control AND presence-of-photographs as one fact. The radios' own scripts-blocked save-to-disk proof (CFG-64's own check, never the map-era one) is confirmed unedited by `git diff`. Touch targets re-measured post-removal: 90×138/89×136/88×136, within a pixel of 25-02's pre-map baseline. CFG-47's three retirement records (the ticked row, the traceability row above, the D16 section) are RE-VERIFIED present, dated and consistent at this phase's close (2026-09-15) — `grep -c RETIRED .planning/REQUIREMENTS.md` is **3**, unchanged since 27-05, despite three later plans (27-06/27-07/27-08) editing `config_page.py`/`style.css` again. |
| CFG-67 | Phase 27 | **Complete (27-06), RE-VERIFIED on the current tree.** Wake-interval caption 220→137 chars, the two wake gauges 254→168, Quiet hours paragraph 188→121 — each check reads the region ONCE and asserts length + refusal-survival against that SAME read. The honesty contract (`wake_battery_observed_text()`'s own docstring, unedited by this plan) is re-confirmed unweakened at this phase's close: with an empty `battery_rows` series it still prints *"Not enough battery history yet to say how long a charge lasts."*, no figure, and the days-CLAIM-shaped forbidden pattern (`≈\s*\d+\s*(?:day\|days\|jour\|jours)\b` — scoped to the CLAIM, not to `≈` near any digit, which the wake-interval caption's own legitimate `(next wake ≈ 31 Jul 08:05)` would otherwise false-positive on) still does not match. |
| CFG-68 | Phase 27 | **Complete (27-07/27-09).** `_theme_carousel_html(grid_html, strip_id)` takes `strip_id` as a REQUIRED argument (no shared default — the duplicate-id/wrong-pager-target trap is closed structurally, mutation-tested against a simulated collision); arrivals and calendar fold in with their own scripts-blocked save proofs; the disclosure moves to render LAST (below the strip) via one shared-helper reorder, reached by a `.theme-carousel:has(.theme-carousel__all[open])` rule scoped per instance, inside the file's one existing `@supports selector(:has(*))` block. **Display's height, measured at this phase's close (27-09, 2026-09-15): 3524 px at 390 px** (scripted; 360 px identical) — against 25-06's 3743 px baseline and 27-07's own STATED prediction of ≈3446–3496 px (midpoint ≈3471 px). The measured figure sits **28 px above** the top of that predicted range — reported as a missed prediction, not silently widened; see the coverage ledger below for why. 2600 px is NOT reached, as 27-07 said it would not be. |
| CFG-69 | Phase 27 | **Complete (27-08).** `layout.frame_strip_html()`'s quiet cell appends a real `<a href>` to a COPY of the shared caption (never the shared variable the Screen cell also reads) — proven by ONE check rendering BOTH `home_page.render()` and `config_page.render(scope=SCOPE_DISPLAY)` and asserting the hrefs are byte-identical, mutation-tested against total removal and a simulated per-page fork (both fail on the correct clause). Clears the 44px floor via `inline-flex`/`min-height`, measured at 360px in both themes, no horizontal scroll added on either page. |
| CFG-70 | Phase 27 | **Complete (27-07/27-08).** The swatch legend ("Departures · Arrivals" → "Departures & arrivals"/"Départs et arrivées") is checked as a REGISTRY RELATIONSHIP (expected label count computed from `device_config.THEMES` at check time), never a literal — self-corrects if a future theme ever gives departures/arrivals different inks. `.copy-btn` in a Flights detail row: root-caused to container spacing (a ~4px gap to a trailing sibling crushing the downward reach; an `overflow: hidden` clip boundary crushing the leftward one) — NOT `.copy-btn`'s own declared values, which already resolved correctly everywhere else — fixed via `.flight-detail-row__grid`/`.flight-detail-row__reveal-inner`, closing 34×26 to a resolved 45×45. `.row-toggle` re-measured and mutation-proven independently (its own targeted mutation names `.row-toggle` alone, confirming it is not piggy-backing on `.copy-btn`'s pass, even though it shares those exact CSS values verbatim). |
| CFG-71 | Phase 27 | **Complete (27-01 through 27-09).** The pattern this whole phase runs on: `_assert_surfaces_agree()` decodes N rendered surfaces to one canonical value and asserts the set has exactly one member, that it equals what was requested, and that it differs from what was there before — three clauses, never one, applied to the dial (27-02), the auto-save model (27-04) and reused throughout. Re-derived by RUNNING at this phase's close (2026-09-15): every `EXPECTED_CHECK_COUNT` confirmed against its own harness; the 5 sandbox-baseline failures verified BY NAME (unchanged from the phase's start — see the phase gate below); `grep -c SKIP` over the whole suite is 0; zero new script (`ls companion/static/*.js` still 17, `dirty-state.js` REPURPOSED not replaced, the deferred-script pin still 15); zero new route (`git diff 839489a..HEAD -- companion/app.py` touches zero `require_session()` call sites and adds zero `_ROUTE` constants anywhere under `companion/`, confirmed by source diff, not by re-deriving the route list by hand). |
| CFG-72 | Phase 28 | **Complete (28-04).** `grep -l CFG-72 .planning/phases/28-*/28-*-PLAN.md` returns 28-04 alone. Device's four settings cards (Diagnostic LED, Wake interval, Notifications, Manual refresh) are wrapped in the same `theme-status--nested`/nested-supersection style Display's cards already use — grouped under two new Device supersections plus a third one-card supersection for Poll — proven not by a markup inventory (27-06's own miss, and the exact mistake this requirement's own wording warns against) but by a rendered cross-page probe (`_a_settings_card_title_renders_identically_on_both_settings_pages()`) that opens BOTH settings pages in one session, addresses every settings-card title by STRUCTURAL POSITION rather than by class name, reads `getComputedStyle` (font-size, font-weight, font-family) on each, and asserts the combined set across both pages has cardinality 1. ZERO CSS was edited (28-04 reused `.page-section--nested > h2` verbatim); the failure message names the offending page, the offending title's own text, and BOTH triples; both themes exercised at the 360px floor. |
| CFG-73 | Phase 28 | **Complete (28-02, 28-03) — two distinct bugs in the one control.** **Bug B** (28-02, the handle collapsing to the dial's centre during a held press): root-caused to `button:active { transform: translateY(1px) }`'s generic depress transform beating `.quiet-dial__handle`'s own ring-positioning transform at equal class-level specificity, animated visibly by the shared `transition: transform`; fixed by excluding `.value-control__handle` from the generic `:active` rule and dropping `transform` from the handle's own transition list; proven by `_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press()`, which SAMPLES the handle's resolved distance from the dial's own centre >=10 times across a held press of >=400ms rather than only before/after — mutation-proven, since an endpoint-only version of the identical check passes on the broken code. 28-02 also corrected a planning-time claim (this same requirement's own text, ROADMAP.md's Phase 28 entry) that the wake-interval slider shared this defect: measured live, `.value-control__handle` has exactly one consumer (the quiet-dial handles); the wake-interval slider is a native `<input type="range">` whose own pre-existing comment states it deliberately does not wear `.value-control`, so no wake-side edit was made or needed — the fix is scoped to the shared class, covering any future consumer by construction. **Bug A** (28-03, the readout regressing to raw unconverted minutes with a permanently blank duration after any interaction): fixed by handing the client the SAME translated wordings a ticker already uses (server-rendered `#`-marked duration-bucket attributes), never a second HH:MM converter or a second duration ladder in JavaScript; proven by `_the_dial_caption_keeps_its_form_after_every_interaction_kind()`, reading the caption's actual displayed text after each interaction kind (drag, keyboard, typed field, preset) and asserting it matches computed HH:MM plus duration byte-for-byte against the server-rendered form, in both languages. |
| CFG-74 | Phase 28 | **SUPERSEDED before implementation, never built — recorded here rather than ticked, retired-as-met, or marked "not met", because none of those is the fact.** The requirement's own text named its own root cause: "a regression from Phase 27's removal of the manual save button." With that button restored (CFG-77/CFG-78), the resilience machinery this requirement specified — a bounded fetch-timeout, distinguished async failure kinds, a conditional retry affordance — has no fetch left to wrap, since the settings form goes back to a real native POST whose success or failure is unambiguous by construction (a real page navigation, never an async call that can fail silently). The two plans that would have built it, 28-06 and 28-07, never executed; both are on disk with a superseding header note (`28-06-PLAN.md.superseded`, `28-07-PLAN.md.superseded`) rather than deleted, per this project's standing convention against erasing planning history. None of its four original clauses — (a) scroll-independent status, (b) a conditional retry affordance, (c) the runway `form=` regression check, (d) fixing any genuine defect found along the way — was built AS CFG-74's OWN machinery. Clause (c) carries forward with its value intact, unchanged in intent, and is what CFG-78/28-09's own runway regression check actually proves — but against the restored bar's real POST, never against CFG-74's own fetch-timeout framing, so it is evidence for CFG-78, not for this row. The real Chromium-era evidence that led to the reversal — the developer's own captured real-Safari Network tab showing `POST /settings` answering a genuine 204, every field present, the value genuinely persisted after reload, with zero visible confirmation — is CFG-74's own evidence for why "resilience around a silent mechanism" was the wrong fix for the symptom it correctly diagnosed. It worked; the model was rejected. See the Phase 28 coverage ledger below for the full account. |
| CFG-75 | Phase 28 | **Complete (28-05).** While scrolling or swiping any of the three theme carousel strips (departures, arrivals, calendar), the live preview `<img>` now follows whichever chip is geometrically centered, via a per-strip IntersectionObserver-assisted tracker reusing the carousel's own existing `applyPreviewSrc()` sink — no radio touched, no setting persisted from scroll alone. Proven by `_scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_selects_nothing()`, dispatching real scroll events across four real intermediate positions per strip (never a jump to the end), in both UI themes, asserting no radio's checked state moves during any of it, that the final scrolled-to chip is provably distinct from the already-selected theme, and that a reload with nothing clicked shows the SAVED theme, never the last scrolled-past one; all three carousels exercised, plus one cross-instance clause proving arrivals' own scroll never reaches departures' preview or strip state (27-07's `strip_id`-per-instance discipline, preserved). |
| CFG-76 | Phase 28 | **Complete (28-01).** `#site-nav-toggle` now renders `icon-gear` (a new, 23rd `ICON_IDS` member, its own `<symbol>` alongside `icon-power`/`icon-moon`) instead of `icon-hamburger`; `NAV_TOGGLE_LABEL` ("Account and preferences") and the panel's own contents (`_mobile_nav_html()`) are byte-identical (confirmed via `git diff`: the only changed line in that function is the icon id). Both hard-coded icon-sprite member-count checks (`_icon_sprite_integrity()`, `_page_shell_emits_sprite_once_no_inline_styles()`) retargeted from 22 to 23, mutation-tested; a new check proves the glyph, the translated EN/FR label, and the panel's still-navigation-free contents all agree. No other `ICON_IDS` entry collides with the new gear symbol (0 hits for "gear"/"settings-icon"/⚙ before this plan). |
| CFG-77 | Phase 28 | **Complete (28-08, 28-10, 28-11).** Every clause of this requirement's own wording now has named, mutation-tested evidence — see the Phase 28 coverage ledger below for the full clause-by-clause walk, including the leave-guard re-arm clause that had zero executable coverage anywhere in the phase until a plan review surfaced the gap (28-11) and the no-JS-floor evidence naming all four scripts-blocked facts a review caught before implementation (28-08). |
| CFG-78 | Phase 28 | **Complete (28-08, 28-09).** The already-existing, AST-provably-unconditional native submit CFG-64 depends on (27-03's own AST proof, re-verified unmoved) became the bar's own visible Save — relocated, never duplicated — proven by `_the_bar_s_save_button_is_the_same_static_fallback_element_relocated()` (28-08, a static/string-level relationship proof) and by 28-09's own browser-level single-affordance audit, which resolves every submit-shaped control's own `.form` property in a live browser and requires exactly one whose form id is `settings-form`, on both settings pages, in both languages, mutation-proven against a deliberately added second button. The runway radios' cross-tree `form=` path is proven end to end by 28-09's own regression check (closing the path CFG-74(c) named before the reversal). The phase's closing gate (28-09) re-derives every check count by running, names the sandbox baseline by NAME (the same five checks 28-04 first recorded, re-verified rather than carried forward), and states plainly which of CFG-74's four original clauses were genuinely built (none) versus superseded by this pair — see the Phase 28 coverage ledger below. |
| CFG-79 | Phase 29 | **Complete (29-05, 29-06).** The editorial floor — one sentence, ~12 words, no mechanism/reason clause, under a card title — landed across every settings/status page except Display's Aspect section (`ASPECT_CAPTION_EXEMPTIONS`, one definition site in 29-05, imported by 29-06, empties when Phase 30 rebuilds that section). The apply-timing sentence now renders once per page rather than repeated under each card. A render-level, bilingual harness check measures the RENDERED caption on all six authenticated routes; it independently caught and fixed three French-only translations that exceeded the floor even though their English source did not (29-05), plus two more in Health (29-06) — corroborated independently by the phase verifier, which wrote its own standalone word-count scanner and found zero violations. |
| CFG-80 | Phase 29 | **Complete (29-04).** Start and End render on one line only at **≥480px**; both of this app's own reference viewports (360px, 390px) still see the original stacked layout below that width — a disclosed, correctly-derived trade-off (native `<input type="time">`'s 144px min-width floor), not an oversight. See 29-04-SUMMARY.md's Known Limitations for the arithmetic (WR-02, 29-REVIEW.md). |
| CFG-81 | Phase 29 | **Complete (29-01).** Replace (and Delete, for a manually resolved entry) render in the illustration dialog unconditionally; the page-wide `edit_mode` query param and the "Modifier les images"/"Change pictures" toggle are deleted outright — `grep -rn edit_mode companion/` returns zero executable hits, only historical comments, independently re-confirmed by the phase verifier. `panel-lookup.js` needed a zero-line diff: its own `mode`-gated visibility logic (`replaceForm.hidden = (mode !== "art")`, `deleteForm.hidden = (manual === "")`) already did the whole job once the server started rendering unconditionally. |
| CFG-82 | Phase 29 | **Complete (29-02).** Compagnies' `render()` now returns header → filter → gallery grid → gap strip (unidentified prefixes), independently confirmed by reading the function's actual return statement. The mobile tab bar's `Compagnies` label no longer truncates: `.tab-bar__pill`'s margin moved from `var(--space-sm)` to `calc(var(--space-xs) / 2)`, replaying the 2026-09-17 audit's own fix (which had drifted out of the working tree, never committed, ahead of this phase) against the current Phase 28-era stylesheet. |
| CFG-83 | Phase 29 | **Complete (29-03).** Vols shows `flights_limit(ctx)` flights (clamped into `[FLIGHTS_PAGE_SIZE, HISTORY_ROW_LIMIT]`, total by construction — 15 adversarial inputs including bools, floats, hex and out-of-band integers all resolve inside the band with no raise, independently re-verified by the phase verifier) behind a real `?limit=` query param, chosen over a `<details>`-only reveal specifically because `freshness.js`'s ~45s background refresh re-fetches `window.location.href` — a query param survives that cycle, a client-only disclosure would not. The phone summary card's callsign/timestamp moved from a flex row to a two-track grid (2026-09-17 audit P1) so the two no longer renegotiate space at 390px. Code review (29-REVIEW.md, CR-01) caught the new Show-more link shipping with zero of its intended styling — `<a class="calendar-disconnect-btn">` matched no selector, since the only two existing rules were `button`-qualified or `.airline-card`-scoped — fixed with a genuine `a.calendar-disconnect-btn` rule plus a selector-vs-tag check (not a substring match), independently re-verified by the phase verifier via its own mutation of the fix. |
| CFG-84 | Phase 29 | **Complete (29-06).** État's battery-trend `<h2>` reads "Batterie · 3 mois"/"Battery · 3 months"; "moyenne quotidienne"/"daily average" moved to the card's own caption sibling — independently confirmed by the phase verifier calling `_battery_trend_section_html()` directly and reading the rendered markup. |
| CFG-85 | Phase 30 | Pending — phase added 2026-09-21; a `/gsd-sketch` round precedes planning. |
| CFG-86 | Phase 30 | Pending — phase added 2026-09-21, not yet planned. |
| TST-01 | Phase 32 | Complete |
| TST-02 | Phase 32 | Complete |
| TST-03 | Phase 32 | Complete |
| TST-04 | Phase 32 | Complete |
| TST-05 | Phase 32 | Complete |
| TST-06 | Phase 32 | Complete |
| TST-07 | Phase 32 | Complete |
| TST-08 | Phase 32 | Complete |
| TST-09 | Phase 32 | Complete |
| TST-10 | Phase 33 | Complete |
| TST-11 | Phase 33 | Complete |
| TST-12 | Phase 33 | Complete |
| TST-13 | Phase 33 | Complete |
| TST-14 | Phase 33 | Complete |
| TST-15 | Phase 33 | Complete |
| FW-01 | Phase 34 | Complete |
| FW-02 | Phase 34 | Complete |
| FW-03 | Phase 34 | Complete |
| FW-04 | Phase 34 | Complete |
| FW-05 | Phase 34 | Complete |
| FW-06 | Phase 34 | Complete |
| FW-07 | Phase 34 | Complete |
| FW-08 | Phase 34 | Complete |
| FW-09 | Phase 34 | Complete |
| FW-10 | Phase 34 | Complete |
| FW-11 | Phase 34 | Complete |
| FW-12 | Phase 34 | Complete |
| FW-13 | Phase 34 | Complete |
| FW-14 | Phase 34 | Complete |
| FW-15 | Phase 34 | Complete |
| HYG-01 | Phase 35 | Complete |
| HYG-02 | Phase 35 | Complete |
| HYG-03 | Phase 35 | Complete |
| HYG-04 | Phase 35 | Complete |
| HYG-05 | Phase 35 | Complete |
| HYG-06 | Phase 35 | Complete |
| INT-01 | Phase 36 | Complete |
| INT-02 | Phase 36 | Complete |
| INT-03 | Phase 36 | Complete |
| INT-04 | Phase 36 | Complete |
| INT-05 | Phase 36 | Complete |
| INT-06 | Phase 36 | Complete |
| INT-07 | Phase 36 | Complete |
| INT-08 | Phase 36 | Complete |
| INT-09 | Phase 36 | Complete |
| INT-10 | Phase 36 | Complete |
| INT-11 | Phase 36 | Complete |
| INT-12 | Phase 36 | Complete |
| INT-13 | Phase 36 | Complete |
| INT-14 | Phase 36 | Complete |
| SEC-01 | Phase 37 | Complete |
| SEC-02 | Phase 37 | Complete |
| SEC-03 | Phase 37 | Complete |
| SEC-04 | Phase 37 | Complete |
| SEC-05 | Phase 37 | Complete |
| SEC-06 | Phase 37 | Complete |
| SEC-07 | Phase 37 | Complete |
| SEC-08 | Phase 37 | Complete |
| EFF-01 | Phase 38 | Complete |
| EFF-02 | Phase 38 | Pending |
| EFF-03 | Phase 38 | Pending |
| EFF-04 | Phase 38 | Pending |
| EFF-05 | Phase 38 | Pending |
| EFF-06 | Phase 38 | Pending |
| ARC-01 | Phase 39 | Pending |
| ARC-02 | Phase 39 | Pending |
| ARC-03 | Phase 39 | Pending |
| ARC-04 | Phase 39 | Pending |
| ARC-05 | Phase 39 | Pending |
| ARC-06 | Phase 39 | Pending |
| CMP-01 | Phase 40 | Pending |
| CMP-02 | Phase 40 | Pending |
| CMP-03 | Phase 40 | Pending |
| CMP-04 | Phase 40 | Pending |
| CMP-05 | Phase 40 | Pending |
| CMP-06 | Phase 40 | Pending |
| CMP-07 | Phase 40 | Pending |
| CMP-08 | Phase 40 | Pending |
| CMP-09 | Phase 40 | Pending |
| DOC-01 | Phase 41 | Pending |
| DOC-02 | Phase 41 | Pending |
| DOC-03 | Phase 41 | Pending |
| OTA-01 | Phase 42 | Pending |
| OTA-02 | Phase 42 | Pending |
| OTA-03 | Phase 42 | Pending |
| OTA-04 | Phase 42 | Pending |
| OTA-05 | Phase 42 | Pending |
| OTA-06 | Phase 42 | Pending |
| OTA-07 | Phase 42 | Pending |
| OTA-08 | Phase 42 | Pending |
| OTA-09 | Phase 42 | Pending |
| OTA-10 | Phase 42 | Pending |
| OTA-11 | Phase 42 | Pending |
| OTA-12 | Phase 42 | Pending |

## Phase 23 coverage ledger (companion dynamism I — "Alive")

Written at the phase's close by 23-11, by walking all seven D-items against the ten
preceding SUMMARYs and against the code, not against the plans. It exists so the
developer can see in one place what shipped, what did not, and the three things that
need a decision rather than an implementation. **Status lines above carry the
per-requirement evidence; this section carries the per-D-item walk.**

### The seven D-items

| D-item | Served by | Verdict |
|---|---|---|
| **D3** — a motion budget honoured under `prefers-reduced-motion` | 23-01 (vocabulary + guard), 23-08 (detail row, chevron, new-row wash), 23-09 (save bar), 23-10 (selection, crossfade, dialogs, skeletons) | **Landed, minus two clauses.** The overlay-drawer clause was STRUCK before planning (below). The "detail row opens *and closes* with measured motion" clause is deliberately one-directional — see CFG-37 and finding 3. The plan's "skeleton shimmers with 23-01's keyframes" behaviour was declined in writing: the only placement where a pure-CSS skeleton auto-hides on load is the image's own `background-image`, and `skypane-pulse` cycles *opacity*, which belongs to the element — so an animation there would breathe the **decoded picture** forever on a page left open all day, which is the complaint a motion budget exists to prevent. Shipped as a static gradient; the file's four keyframes stayed four. |
| **D10** — native multi-page view transitions | 23-04 | **Landed in full.** Nothing remains open beyond the human sweep on three engines. |
| **D14** — one script ticking every `<time data-relative>` | 23-03 (convention + the ladder read forwards), 23-05 (the ticker), 23-06 (the countdown, and `static_text`) | **Landed as a mechanism; not yet universal as a fact.** Four visible ages still do not tick — enumerated on CFG-34's row. Three are convertible and unowned; one cannot be converted without changing `battery-trend.js`'s transport. |
| **D1** — Home and the Frame strip refreshing themselves | 23-06 (registry, page key, three skips, the picture fade), 23-08 (Flights joins by adding one key on each side) | **Landed, and exceeded its own scope**: four pages refresh, not two. 23-06 also fixed a no-JS regression 23-05 had recorded against itself — Health's freshness line renders the server's clock again and the ticker upgrades it, so neither reader is handed a frozen claim. |
| **D22** — an honest live/paused/reconnecting indicator | 23-05 (the breathing dot, the freshness line), on top of 22-15's shipped state machine | **Landed, with its "orange" clause superseded by a shipped decision** (finding below). The remaining 20% was the *honesty* half: the dot breathes only while the loop is genuinely listening, derived from the loop's own two state variables, and a harness check fails if the server ever renders it already breathing — a dot breathing on a page with no loop running is exactly the lie D22 exists to remove. |
| **D2** — real `role="switch"` controls over `fetch` | 23-07 | **Three of four switches.** Screen, Quiet hours and the Diagnostic LED are real switches; the fourth (notifications) is not built — finding 1. |
| **D7** — the live flights list | 23-08 | **Landed, minus sticky day headers** — finding 2. |

### The three findings that carry forward

Recorded here rather than in a SUMMARY nobody re-reads, because each is a question for
the developer rather than an omission.

**1. D2's fourth switch (notifications) is NOT built.** The mechanism is available and
nothing technical blocks it — `save_device_config()` takes `notifications` as a
whole-dict replacement, so a `/quick/notifications` route could read-modify-write it.
**What is missing is a decision.** The two checkboxes (`notifications_battery`,
`notifications_silent`) share one card with the `notifications_topic_url` text field,
which is saved through the settings form and governed by the save bar. Converting only
the checkboxes produces a card where two controls apply instantly and one waits for
Save — a pattern no locked source covers, and one
`references/settings-page-patterns.md`'s one-caption-per-section and save-bar contracts
do not anticipate. Converting the field too would mean an instant-apply text input,
which is precisely what the save bar exists to avoid. Leaving the checkboxes *and*
adding switches would be two controls for one setting — the X1/D-04 defect Phase 22
removed. 23-07 stopped rather than falling back to a rejected pattern, following D-10's
own precedent, and the developer recorded the same conclusion as **option A** on
ROADMAP.md's Phase 23 entry (2026-09-13). Verified untouched at close:
`notifications_group()` is unchanged and `grep -c 'quick/notifications' companion/app.py`
is **0**. The two notification checkboxes keep in-scope-absent-means-`False` **because
their checkboxes are still rendered** — which is exactly the condition that made that
resolution correct for `led_enabled` until this phase, and `handle_post()`'s docstring
now says so in those words. **Decision needed: split the card (topic URL in its own
Save-governed section, the two toggles as instant switches), or leave it as checkboxes
plus Save permanently and close the clause.**

**2. D7's sticky day headers are NOT built, and this one is already DECIDED — it is
carried forward so it is not re-proposed, not because it is open.** Phase 22's T4 had
removed the app's previous sticky claim on the structural ground that a
`position: sticky` `th` inside `.data-table-wrap` — a wrapper with `overflow-x: auto`
and no height — has no vertical scrollport to stick within, so the declaration was inert
from the day it shipped. That ground has not changed, and making it engage still means
giving the Flights table a bounded-height scroll region with a measured width and density
budget behind it. **But the deciding reason is better than that cost argument, and it was
found by rendering rather than by arguing:** both variants were put on the real page with
seeded data and scrolled to the same offset, and **every flight row already carries its
own date** (`1 août 21:41`), so a pinned title would repeat what is already on every
line — while the sticky variant shrinks the list to a ~7-row box inside a half-empty page
and leaves a clipped row peeking under the pinned header. Declined by the developer as
**option A** (2026-09-13). Verified at close: `grep -cE 'position: *sticky'
companion/static/style.css` is **3**, its pre-phase value, of which two occurrences are
prose. **Revisit condition, narrow and specific: only if the per-row date is ever
removed** — for phone density, say — which would make the title non-redundant. Recorded
in `references/data-density.md` in place, where the old forward pointer ("sticky day
headers are D7, Phase 23") is superseded by this outcome rather than left pointing at
work that is now declined.

**3. Two requirement clauses are knowingly contradicted by shipped decisions, and this is
the CFG-28 situation of Phase 22 repeating — caught before the tick this time, not
after.** In Phase 22, CFG-28 was marked complete and then had to be un-ticked when 22-12
found Health's clock rendering a raw UTC ISO in its `title`, failing the "every tooltip"
clause. The same shape exists here twice, and **both boxes are therefore left unticked**:
**(a) CFG-37's "the detail row opens *and closes* with measured motion"** — it opens with
measured motion and closes instantly, because `transition-behavior: allow-discrete` keeps
a closed row's controls in the tab order and the accessibility tree for the whole of its
exit (measured: 4 of 4 focusable). The code's trade is right; the requirement's wording is
what is wrong. **(b) CFG-34's "EVERY relative age on screen is live"** — four are not,
three of them convertible and simply unowned, one structurally blocked behind
`battery-trend.js`'s `title` transport. **Decision needed on each: amend the clause to
match the shipped decision, or schedule the work that would make the clause true.** What
must not happen is the box being ticked with the clause as written. The most visible half
of (b) is worth stating on its own, because it is a user-facing inconsistency rather than
a paperwork one: **on a Flights row the age ticks below 960 px and is frozen above it**,
since the phone card goes through `concise_timestamp_html()` and the desktop When cell
does not.

### One design-system finding from the closing sweep

**`companion/static/style.css`'s accent-reservation list is no longer exhaustive, and its
own header comment says it is.** Phase 23 added two genuine accent consumers without
extending it: `.switch[aria-checked="true"] .switch__track`'s fill (23-07 — not covered by
the existing "native `accent-color` of radios/checkboxes" entry, which is a native property
on a native control) and `@keyframes skypane-row-arrive`'s 22% accent wash (23-08 — not
covered by the selected-card wash entry, which signals SELECTION where this signals
ARRIVAL). A third occurrence, `.history-card__summary::before`, is a restatement of the
already-listed `<summary>` disclosure-marker use and is **not** a new consumer. Both new
uses look defensible on their merits; the defect is that a list whose stated purpose is to
let "a future reader tell an intended use from an accidental one" has quietly stopped
being able to — which is exactly how the Disconnect button's accidental accent fill
survived for a phase and a half. 23-11 writes documentation only and does not edit
`companion/`, so this is recorded in `sketch-findings-skypane`'s Colour entry and here,
and the repair belongs in that stylesheet's own header comment and in
`06.6.1-UI-SPEC.md`'s Color section. **For whichever plan next edits `style.css`.**

### The three items struck before planning, with their grounds

Recorded so a future audit meets the reasoning rather than the idea, and so none of the
three is re-proposed as unexamined.

- **D9 (server-sent events) — REJECTED, not deferred.** The events it would emit
  originate in `server/poll_loop.py`, which runs `Type=oneshot` under a 30-second timer
  (`deploy/skypane-poll.service`, `deploy/skypane-poll.timer`): **the process exits every
  cycle, so there is no hook to register**, and an SSE endpoint would have to poll the
  database itself — a polling client with extra steps. **The thread cost is NOT the
  reason and the original premise for it was wrong**: it was measured (0/5/20/50/200 held
  connections, ~29–46 KB RSS each, returning to baseline on disconnect), the ~1 s
  burst-latency tail is the `request_queue_size = 5` accept backlog and is present at
  N=0, and the research corrected the brief's assumption that streaming could starve the
  frame — the device's poll is served by a **separate** systemd unit
  (`stub-server/byos_server.py`, port 8642, its own Caddy block), so companion streaming
  could never touch it. `freshness.js` already implements a better polling client (retry
  ladder, in-flight guard, visibility gate, focus-preserving targeted swaps) and was
  extended instead — which is what Phase 23 did, four times over.

- **D12 (service worker / offline shell) — OUT OF SCOPE, on a verified security
  finding.** In the project's own harness Chromium, `cache.put()` stores a
  `Cache-Control: no-store` body **verbatim**. Every HTML response here is `no-store` by a
  deliberate Phase 18 decision precisely because every page is session-gated, so a service
  worker would persist authenticated content past sign-out. **Retirement is also not
  deletion — a 404 leaves the registration live** — so reopening this requires two things
  to land first: a **tested** de-registration path (the harness can do this; `127.0.0.1`
  is a secure context) and an explicit answer on caching authenticated content.

- **D3's overlay-drawer clause — STRUCK, on its third proposal.** It contradicts
  `22-CONTEXT.md`'s D-10 and three recorded rejections in `sketch-findings-skypane`, one
  of them established by real-device testing; `references/mobile-navigation.md` already
  warns that this exact reopening happened once before. It also targets a component
  Phase 22 retired — `.mobile-nav` is a preferences panel now and the bottom tab bar is
  the navigation, and the tab bar was chosen precisely so neither rejected verdict had to
  be reopened. The rest of D3 landed unchanged.

## Phase 24 coverage ledger (companion dynamism II — "Drawn")

Written at the phase's close by 24-09, by walking all five D-items against the eight
preceding SUMMARYs **and against the code**, not against the plans. It exists so the
developer can see in one place what shipped, what did not, and what is still theirs to
decide. **Status lines above carry the per-requirement evidence; this section carries
the per-D-item walk, the provisional decisions this phase ran on, and the findings that
must not evaporate.**

Two of seven requirement boxes are deliberately left unticked (CFG-39, CFG-42), each
with its unmet clause named above and the decision it needs stated. That is Phase 23's
standard held rather than Phase 22's CFG-28 error repeated.

### The five D-items, against the roadmap's own wording

| D-item / goal clause | Served by | Verdict |
|---|---|---|
| **the goal sentence's "sharing one battery estimator"** | 24-01 | **Landed, machine-enforced — and the premise it was written on was false.** There is one estimator, `companion/battery.py`, extended rather than replaced (it was already created by 19-01 for this exact problem). But the plan's claim that the millivolt constants live in exactly one module "in `companion/` or `server/`" is **false in this tree and cannot be made true**: `server/poll_loop.py` carries a deliberate private copy whose own comment explains it, because the server package may never import the web-app package (D-27). Three ways out were available and the two easy ones were rejected — deleting the copy breaks a standing architectural rule for a cosmetic win, and scoping the check to `companion/` silently stops watching the one place a *third* copy is most likely to appear. What shipped is an **allow-list of exactly two, each with its own written justification**, so the two that exist are visibly deliberate rather than merely tolerated. |
| **D21** — "battery ring gauge, reused small in Home's tile" | 24-04 | **Landed in full.** One emitter at 72px and 36px, proven one function behaviourally rather than by inspection. See CFG-40 above. |
| **D8** — "battery chart with **gradient** area, marked last point, low-battery threshold" | 24-05 | **Landed, minus the GRADIENT, and minus adoption of the shared module.** The marked last point and the low-battery threshold landed in full. The area landed **flat**, not gradient: a `<linearGradient>` is only referenceable as `url(#id)` and this chart's own no-external-reference guarantee forbids that substring outright, so the gradient could only have shipped by relaxing a security-shaped assertion for decoration. CFG-41's own wording asks for "a filled area", which is met — it is the **roadmap's** wording that is not, and it is recorded here rather than quietly reconciled. Separately, this is the one drawing that does **not** go through `companion/draw.py`, which is CFG-39's unmet clause. |
| **D13** — "Home's day timeline" | 24-06 | **Landed, minus detections.** The band, the Paris-day bucketing, the wrapping quiet-hours window as two spans and the honest collapse caption all shipped. **Detections are deliberately not plotted** — a provisional planning decision (below), honoured as scoped rather than quietly added. That is CFG-42's unmet clause. |
| **D20** — "**wake-punctuality** grid" | 24-03 (the readers), 24-07 (the grid) | **Landed with the METRIC and the NAME both changed, deliberately and on evidence — and the roadmap's own blocker is what settled it.** The roadmap entry itself flagged this: `device_health` records observed check-ins only, so "honoured-wake rate" needs historical expected intervals that are nowhere stored. The settlement is below under "three facts not to re-propose". What shipped is **observed check-in regularity**, four states including an honest "no observation", judged by one shared threshold function, under a three-clause caption each clause of which is separately asserted. A forward-looking `wake_epochs` table accrues true interval epochs and is **read by nothing**. |
| **D4** — "the Home hero the others feed" | 24-08 | **Landed. One plan-level clause was refuted by measurement and is recorded rather than smoothed.** The hero is one composition assembled from calls, with "fed by" turned from a claim into a property a check can lose. 24-08-PLAN.md's own wording — *"the stack is a floor behaviour rather than the only behaviour"* — reads as a desktop column split and **cannot be built**: the hero is 880px at 1280px, so a one-third column is 288px against the 310px a band card needs to keep its canvas at 278, leaving the canvas at **256px — narrower than it gets at the 360px floor**. The hero is one column at every width and the floor-vs-not-floor property is asserted of its **parts**. CFG-44 as written contains no stacking clause, so the tick is honest; this is a plan assumption, not a requirement clause. |

### The provisional decisions the developer still owns

This phase was planned **without `/gsd-discuss-phase` and with no CONTEXT.md**, so every
decision below would normally have been the developer's. Each is listed with its
alternative and what switching would actually cost — a plan proceeding on a
recommendation is not the same as a decision taken.

**1. D20's metric: the metric changed rather than the schema grown (24-RESEARCH.md
decision 1).** *Alternative:* grow the schema (Option A) and compute a rate of wakes the
device kept. *Switching cost, and the part that matters most:* **the grid would not
change even then.** Option A still cannot describe the **past** — a column added today
carries nothing about the weeks already recorded — and it still cannot support the
phrase this drawing refuses, because **a log rotation the ingest missed leaves a hole
indistinguishable from a missed wake and no schema change recovers it**. What Option A
would buy is only a better *future* upgrade path, and `wake_epochs` already buys that
without a migration. It would also cost this project its first SQLite migration
mechanism, in its most concurrency-sensitive file: there is no `PRAGMA user_version` and
no in-place table alteration anywhere in the tree, and a new **column** would need one
where a new **table** does not. *Nothing shipped would have to change.*

**2. The forward-looking `wake_epochs` table (decision 2).** *Alternative:* drop it. It
was scoped into 24-03 Task 3 specifically so it could be **cut whole**. *Switching
cost:* one table and one deduped write, and no drawing changes — a check currently fails
the day anything under `companion/` so much as mentions it, and that check would go with
it. Keeping it costs a row per interval change and buys a later phase the option of an
honest forward-looking metric.

**3. The grid's name: "Check-in regularity", not the roadmap's "wake punctuality"
(decision 3).** *Alternative:* the roadmap's name. *Switching cost:* the name is not
cosmetic — two checks assert the refused words absent from the new code **and from the
rendered page in both languages**, and a mutation restoring the roadmap's phrasing as
the heading fails **both**. Changing the name means either changing what the drawing
claims or knowingly labelling it as something it cannot prove. *Nothing else would
change.*

**4. D8's area geometry (decision 4).** Resolved **by experiment inside 24-05**, as
planned, and the honest outcome the plan permitted ("no area, keep the line") was not
needed: candidate (a), a nested `viewBox`'d `<svg>`, was reached and shipped. *No
developer input needed* — recorded here only so the decision is visibly closed rather
than open. **The gradient half is a separate question and is still open** (see finding 2
below).

**5. Detections on the day band (decision 5).** *Recommendation taken:* check-ins and
the quiet-hours span only. *Alternative:* plot detections too, which is what CFG-42's own
parenthetical asks for. *Switching cost:* a second mark vocabulary inside a **measured
278px** canvas that at the shipped minimum spacing resolves ~22-minute intervals and
holds at most 67 marks — so it needs a design for telling two vocabularies apart at that
density, not just a second class. *Nothing shipped would have to change*, but **CFG-42
cannot be ticked until this is decided either way.**

**6. Motion on the drawings: none (decision 6).** *Alternative:* animate. *Switching
cost:* every drawing sits on a page inside the refresh-swap registry, so motion here is
ambient motion on the app's busiest page — and it would reopen a budget that has not
moved since Phase 23 (4 keyframes, 2 reduce blocks, 1 no-preference block).

**7. The hero's geometry (decided during execution, not at planning).** One column at
every width, no surface of its own. *Alternative:* a desktop column split or a card
around the parts. *Switching cost:* both are **measured to break the day band** — a
column split leaves its canvas at 256px against 278 at the floor, and giving the hero a
surface means taking the band's card away, which widens the canvas and invalidates the
constant derived from it. 16px of padding inside the hero is already enough to trip the
band's own spacing floor, measured.

### Three facts a future audit would otherwise re-propose

Recorded with their grounds so the argument is met rather than the idea.

**1. Why the schema was not grown.** `device_health` rows turn out to be real per-wake
check-ins, so observed cadence **is** measurable — but the *expected* interval is not
merely unstored: `wake.effective_wake_interval_s()` switches to `DISPLAY_OFF_SLEEP_S`
whenever the screen is off, quiet hours hold the frame on top of that, and
`device_config.json` is a current-state file whose no-migration/no-rewrite contract is
pinned by three named checks. Decisively, a rotated-away log range and a missed wake are
**the same hole**, so even a new column could not support the claim. The project also has
no migration mechanism at all, and a new column would have had to invent one.

**2. Why the grid is not called punctuality.** Because it cannot prove punctuality — see
above — and because the honest name is the one thing standing between a reader and
reading a log-rotation hole as a device fault. The refused words are grep-pinned absent
from the new server code and from both rendered languages.

**3. Why detections are not on the day band.** Two mark vocabularies in a measured 278px
canvas is unreadable at the density this band already runs at. The planning-time estimate
for that canvas was ~330px; the real measurement makes the argument stronger, not weaker.

### Four findings that must carry forward

**1. Ceiling-only assertions let real defects through, three plans running — so assert
the FLOOR.** 24-06: a day of **1 440 check-ins collapsed to one mark at 0.00%**, the
frame rendering as dead since midnight, with four green checks, because all four were
ceilings. 24-07: whole-pixel cells leave the grid at **277px inside a 278px canvas** —
inside the box, so containment stayed green — and the HTML label row beneath, which sizes
itself from the card rather than from the emitter's arithmetic, then names a column one
pixel off. 24-08: `.home-overview > *` is (0,1,0), **ties** `.frame-strip`'s own margin
and loses on source order, so **two thirds of the composition were correct and one third
was not**, measured at 40.00px where 16 was declared — precisely the shape a ceiling or an
eyeball passes. Recorded as a standing testing convention in
`references/data-density.md`.

**2. Mutate every property you add — and expect either outcome.** Six-plus CSS
declarations shipped in this phase with confident load-bearing comments and measured
either **inert** (24-04's two `min-width: 0` and one `flex: none`; 24-05's swatch
`flex: none`; 24-07's `flex: none`, inert only because a sibling `flex-wrap` holds, and
`align-items: center`, inert only by a coincidence of two 12px values) or
**load-bearing-but-invisible** (24-05's `grid-column: 1 / -1`, whose absence drops the
canvas 229.97px → 109.00px while overflowing nothing; 24-06's
`--drawing-canvas-height`, whose absence makes the band **6.7× taller** while moving no
mark and changing no colour). Every inert one was deleted **with the measurement written
where it stood**; every invisible one got the assertion that can see it. **The backlog
this implies is real and is nobody's yet:** this discipline only ever ran over
declarations *this phase added*, the rest of `style.css` has never been swept, and both
failure classes are silent by construction. A sweep is worth a plan of its own.

**3. An infrastructure hazard every mutation run in this repository depends on.**
`git checkout-index -f --` can restore source **within the same second** the `.pyc`
recorded, and CPython validates cached bytecode by comparing source mtime for **equality
at one-second granularity** — so stale bytecode stays valid, the corrected source is
never recompiled, and a later run reports phantom failures with mutated markup still
being served. 24-08 lost a full browser run to this and the failures looked exactly like
a defect in its own work; a pristine `git archive` of the same commit ran clean, which is
what identified it. **Clear every `__pycache__` outside `.venv` after any sub-second
mutate/revert cycle.** Written into `references/data-density.md` so a future executor
meets it before paying for it. Its companion rule: **stage before you mutate and revert
with `git checkout-index -f --`, never `git checkout --`**, which restores from HEAD and
will delete an unstaged implementation outright (24-04 lost a whole mutation round
exactly that way).

**4. Plan assumptions that proved wrong and were recorded rather than smoothed over.**
The day band measures **278px, not the ~330px the plan stated twice** — every spacing
figure derived from the estimate was wrong with it, and
`DAY_BAND_MIN_MARK_SPACING_PERCENT` was re-derived 1.2 → **1.5**, rounded **up** because
it is a floor on legibility. `device_config.quiet_hours_status()` returns an **activity
status** (`seconds_remaining`, `end_hm`), not a window, so it cannot be the band's source
and its own derivation was reused one level down instead. The Paris/UTC boundary case a
plan named **cannot occur** — Europe/Paris is never *behind* UTC, so 23:30 Paris is the
same UTC date; the implemented case is the mirror (00:30 Paris is the previous UTC day)
and the check pins both directions at once. `.home-hero` is **unusable as a class name**:
two standing checks assert that phase-20 string never returns to Home, so the container
is `.home-overview`. Three plans also shipped with an incomplete `files_modified` list
(24-03, 24-07, 24-08); no ownership was violated in any case, but the lists were wrong and
are recorded as such.

### Folded in from `deferred-items.md`

Both entries were logged by 24-05 as out-of-scope discoveries, seen only in mutation runs
where a mutated stylesheet shifts frame timing. Neither was caused by the plan that
recorded them, and neither touches any drawing this phase shipped.

1. **`the live theme preview CROSSFADES…`** (D3/CFG-32, 23-10) — sampled two frames after
   selection and read `opacity 1` with the transition correctly declared, i.e. the sample
   landed before the transition painted. **Promoted from intermittent to a real fix during
   this phase gate:** it has since appeared in a clean CI run on `2520a21`
   (browser-ux 64/65), so it is a genuinely flaky check rather than a curiosity, and the
   **orchestrator** fixed that one check to wait for the `transitionrun` event
   instead of sampling at a guessed instant — landed as `7fa619f`, *"the crossfade check
   waits for the transition instead of guessing when to look"*, +60/-22 in
   `companion/test_browser_ux.py` alone. `EXPECTED_CHECK_COUNT` did not move (65 stays
   65, verified after the fact) — a method change to one existing check, not a new one.
   **The fix is the orchestrator's, not 24-09's**, and 24-09 did not edit
   `companion/test_browser_ux.py`. It did not fire in either of this gate's runs, both of
   which were measured on the tree **before** `7fa619f` landed; since that commit changes
   only how one already-passing check waits, the gate's numbers are unaffected, and this
   sequencing is recorded rather than glossed.

2. **`…the reminder stays within 48px…`** (B10/X9/D-04, 22-14) — failed once at
   **48.1875**, a 0.19px overshoot of a hard ceiling; a sub-pixel text-metric boundary
   rather than a layout change. **Still open and still nobody's.** It did not fire in
   either of this gate's runs. *Decision needed: widen the ceiling's tolerance to
   absorb sub-pixel text metrics, or accept an occasional red.*

## Phase 25 coverage ledger (companion dynamism III — "Controls")

Written at the phase's close by 25-08, by walking all five D-items against the seven
preceding SUMMARYs **and against the code**, not against the plans. It exists so the
developer can see in one place what shipped, what did not, and what is still theirs to
decide. **Status lines above carry the per-requirement evidence; this section carries
the per-D-item clause walk, the eight provisional decisions this phase ran on with
their reversal cost AS IT NOW STANDS, and the findings that must not evaporate.**

Two of seven requirement boxes are deliberately left unticked (**CFG-50**, **CFG-52**),
each with its unmet clause named above and the decision it needs stated. That is
Phases 23 and 24's standard held — four boxes left unticked between them — rather than
Phase 22's CFG-28 error repeated, where a box was marked complete and had to be
un-ticked a plan later when a raw UTC ISO turned up in a `title`.

**Every clause below carries one of three verdicts: BUILT, RE-SCOPED (with what the
audit said and what shipped), or NOT BUILT (with its ground and the decision it needs).
No clause is unaccounted for.**

### D16 — "Pick the runway on one SVG map of Orly" (CFG-47, served by 25-03)

**RETIRED 2026-09-14 by Phase 27 (CFG-66).** Everything recorded below remains a true account of what 25-03 built and measured; it is kept for that reason. What changed is the product decision, not the evidence: the map is removed, the three native radios return to being the control, and the three `runway-*.png` photographs stay served. See CFG-47's row above for the retirement and its ground.

| Audit clause | Verdict |
|---|---|
| "Pick the runway on **one** SVG map of Orly" | **RE-SCOPED — one map, drawn three times, once per card.** An `<svg>` cannot contain a `<label>` or an `<input>`, so one literal shared canvas needs three absolutely-positioned overlay labels — the exact hit-area failure this D-item's own second trap exists to measure. Each `.runway-card` therefore carries a complete map of all three runways with its own picked out, so comparing cards compares highlights on one shared picture. Cost: n² strips (9 today, 16 with a fourth runway) at ~120 bytes each. Measured consequence: the cards got **taller**, which is why the touch targets rose from 88 × 138 to 90 × 201. |
| "**reuse `runway-*.png` drawings**" | **RE-SCOPED — redrawn, not embedded, and the photographs are KEPT.** The three files are 338–371 KB photographs, not vectors, so "reuse" means redrawing Orly's three runways as SVG geometry in Python. Bearings are parsed from the **registry's own labels** (before the id, because Orly's first entry is keyed `'3'` and labelled `Runway 3 (07/25)`), so the drawing cannot contradict the text printed beside it. The three PNGs keep their slot, their route and their session gate (Decision 2) — measured still serving at `naturalWidth` 1672. |
| "tracked runway in **accent**" | **RE-SCOPED — it pays in INK, not accent.** The selected strip goes 30 % → 55 % → solid `--color-text`; the stylesheet's exhaustive accent-reservation list is unchanged by this plan. The live selected state joins the **one** existing `@supports selector(:has(*))` block rather than opening a second. |
| "tap to select" | **BUILT, and it was already native.** The three radios are untouched; selection, arrow-key navigation and saving are all the browser's. **D16 added ZERO scripts** and used none of the phase's `.js` gate. |
| "label animates below" | **BUILT** — a plain `transition` on the strip, spending the existing `--motion-fast`, covered by the global reduced-motion block for free. Proven live (a theme switch puts a running animation on every strip), not merely declared. |
| "one **300 px** object on phone" | **NOT BUILT as a number.** Each map renders at **53.33 px** inside its card's 53.33 px content box at 360 px — three small maps in a row, not one 300 px object, which follows directly from the first re-scope above. *Decision needed: accept the per-card map (the shape that makes all three cards 44 px targets), or ask for a single large map with overlay labels and re-open the hit-area question this clause's own sibling trap raised.* |
| *(trap)* "a `<label>` overlaying an SVG shape must still be ≥ 44 px in both axes, **measured**" | **BUILT and measured** — 90 × 201 / 89 × 197 / 88 × 197 by real hit-testing in the runway row. |
| *(trap)* "any diff introducing a second `@supports selector(:has(*))` fails two named checks" | **BUILT** — the count is 1, brace-anchored and comment-stripped, and M15 opens a second and fails both. |
| *(plan sentence)* "the caption claims relative bearings **and relative lengths**" | **NOT BUILT, deliberately.** `device_config.RUNWAYS` carries no length for any entry, so there is nothing to derive one from and inventing plausible lengths would be the dishonest-state defect the sentence is trying to prevent. Every strip is drawn the same length and the caption claims only relative bearings, north up, not to scale. |
| *(deliberate non-build)* a north marker inside the map | **NOT BUILT, recorded so it is a choice rather than an oversight.** A tick at the top of the ring with no letter beside it is ambiguous, and SVG `<text>` inside a viewBox scales with the box and owes `draw.py`'s contract rule 5. The caption carries "north up" instead, which is where text belongs. |

### D17 — "24 h dial for quiet hours" (CFG-48, served by 25-04)

| Audit clause | Verdict |
|---|---|
| "two draggable handles on a ring" | **BUILT** — two real `<button>`s inside the `.js` gate, each carrying `role="slider"` and the `aria-value*` set, each measured **45 × 45** with the window's ends far apart, close together, **and** genuinely overlapping. |
| "the quiet arc draws itself" | **BUILT, and server-side, which is the stronger reading.** The arc is rendered from the saved window and sits **outside** the gate, so a scripts-blocked reader sees a correct picture rather than an absence. |
| "'23:00 → 07:00 · 8 h'" | **BUILT** — printed through this app's **one** duration ladder (M13 refuses a second), derived from the same minute count the arc's sweep is derived from, inside one function, so the picture and the words cannot disagree. |
| "presets move the handles" | **BUILT — and it did not work for free, which only a browser check could have known.** Assigning to `.value` from script fires no event, so `dirty-state.js`'s preset handler moved both time inputs and left both handles where they were. Fixed inside the design (`value-controls.js` repaints on `change`/`input`/`click`, learning nothing about presets); `dirty-state.js` is untouched. |
| "**hidden** synced `<input type="time">` for submission and no-JS" | **RE-SCOPED, and this is the clause the phase deliberately refused.** The time inputs stay **visible** and stay the submitting controls: a native `<input type="time">` is the only control on this page a person can *type* into, and typing 23:00 is faster and more precise than dragging to it. It is the **dial** that lives inside the gate. Proven byte-identical across five argument shapes, including the D-07 rejected-save path. |
| "fixes B14" | **RE-SCOPED — B14 was already fixed (22-10) and this PRESERVES it.** `_normalised_time_html()`'s two visible 24-hour siblings survive byte-for-byte; a dial that removed them would have reopened a closed defect. |
| *(dossier)* "`ArrowLeft`/`Right` ± 15 min, `PageUp`/`PageDown` ± 60 min, `Home`/`End` to the day's ends" | **RE-SCOPED on the Page keys: ±150 minutes, not ±60.** The same plan's binding constraint says the model must match the native `<input type="range">` one 25-05 would inherit, and the two sentences cannot both hold; a per-control page size would have been a second keyboard model on a second settings page. See the correction of record under CFG-49: the native rule is a **percentage of the band**, which coincides with "ten steps" only on a ~100-step band — as the dial's ~96-step band nearly is. |
| *(dossier)* "the plan must state a **minimum handle separation** and what happens below it" | **NOT BUILT — answered `no`, deliberately.** A zero-length window is a real, defined state (`seconds_until_quiet_hours_end()`'s own docstring calls it never-active and means it), so refusing it here would make a state reachable by typing unreachable by dragging — a worse card, not a safer one. What replaces it: z-order is **document order** (no `z-index` anywhere, asserted), the END handle is emitted second and wins an overlapping pointer-down, and the start handle stays its own tab stop whatever it is painted under — measured focusable at 15 minutes' separation, where its own centre hit-tests to the end handle. *No decision needed unless the developer finds the overlap unusable on a real phone, which is exactly what the human sweep is for.* |
| *(dossier)* "the readout must **not** be a `role="status"` live region" | **BUILT** — it is `aria-hidden`, and `role="status"` on it is refused by name (M12). The handle's own `aria-valuetext` (local HH:MM, never the minute count) is the announcing path, and a real defect was fixed here: `paint()` had been announcing on the **wrapper** rather than on the focusable handle. |
| *(plan sentence)* "the dial is 128 px" | **RE-SCOPED to 176 px, on arithmetic rather than taste** — two 46 px hit boxes need ~45 px between centres, so on a 128 px ring the handles cannot both clear the floor until the ends are ≈ 4 h 49 apart, against ≈ 3 h 12 at 176 px. |

### D18 — "wake-interval slider with freshness and battery-life gauges" (CFG-49, served by 25-01 + 25-05)

| Audit clause | Verdict |
|---|---|
| "wake-interval **slider**" | **BUILT** — a real native `<input type="range">` with **no `name`**, inside the `.js` gate, whose only job is to steer the `<input type="number">` that already existed. Measured: a drag across 55 % of the track moved the number input 300 → 3060. |
| "1–60 min" | **BUILT, in the wire format** — `min`/`max` are 60 and 3600 **seconds**, interpolated from `device_config` rather than typed (M14), because the field is in seconds and the wire format must stay seconds. |
| freshness gauge: "a plane appears at most N min after passing" | **BUILT, as a BOUND** — the words *at most* are asserted in the wording and not only in the docstring, and the minute conversion rounds **up** (a 90-second cadence bounds the wait at a minute and a half; "at most 1 min" is false). |
| battery gauge: "estimated battery life **≈ 38 days**" | **RE-SCOPED to a narrower claim, and this is the phase's most consequential re-scope.** The figure does not exist in this codebase and **cannot be computed honestly today**: it needs a per-wake energy cost this project has never measured, and inventing one is the dishonest-state defect Phase 22 spent a phase removing. What shipped: five **named** estimator states, an absolute figure **only** from `LIFE_TREND_FALLING` — this device's own observed daily-average discharge slope over 14 days, behind a 2-day span floor and a 10 mV drop floor — wearing the `≈` marker and naming its source, plus an explicit "not enough history yet" state. The honesty is **structural**: the absolute sentence is rendered by the server outside every element the script can rewrite, so there is no template through which the script could invent one. *See decision 3 below. The developer's real question is the WORDING, and DEVICE-05 (closing 2026-09-23) is the input that would let a later plan add a model-based branch through the same wording.* |
| *(dossier)* "do **not** add `role="slider"` to the native range" | **BUILT as an absence, asserted** — M12 adds one and fails by name. |
| *(dossier)* "the gauges are **not** `aria-hidden` and **not** a live region" | **BUILT** — they are plain text the number input's own value does not announce, and they are not a live region, because they change on every slider step and would flood. |
| *(dossier)* "the number input is untouched and remains the poster" | **BUILT** — byte-identical across six argument shapes (M10 fails on an added `inputmode`), and the out-of-range guard re-proven end to end in a browser with 30 s on disk. |
| *(plan sentence)* the live clause states the effect as a **ratio** ("about twice as long as now") | **RE-SCOPED to naming two cadences.** A ratio needs a decimal, a decimal needs a locale-specific decimal mark travelling to a script whose whole contract is that it carries no copy, and a rounding rule that `Math.round` (half-up) and Python's `round` (half-to-even) agree on at a tie this control really reaches (1260 s against 1200 s is exactly 1.05) — plus two wordings for more-often/less-often. "every 51 min instead of every 5 min" needs none of that. `relative_factor` is still consumed, as the **guard** rather than the number. |
| *(plan sentence)* the shared `.value-control` class is worn by this control | **NOT ADOPTED, deliberately.** Its `position: relative` is the containing block for an absolutely-placed handle and this control has none; its `touch-action: none` is a position on a gesture a native range implements itself. Recorded in the stylesheet at the point a later reader will wonder. |

### D5 — "Theme picker as a carousel" (CFG-50, served by 25-06)

| Audit clause | Verdict |
|---|---|
| "a **carousel**, swipe and keyboard" | **BUILT, and both are native** — the same eighteen radios re-laid-out as a CSS scroll-snap strip, so swipe is the browser's and arrow-key selection is the radiogroup's. Measured keyboard-only with zero pointer events at one, six and seventeen steps. **Two defects had to be fixed to make the two agree**: focus lands on a 1 px visually-hidden radio, so the browser stopped scrolling the moment its chip's left edge appeared and left the selected chip **50 px outside** a 278 px strip (fixed by `scroll-padding-right` equal to one chip's own width, pinned equal in the harness); and a nowrap strip of eighteen chips put `documentElement.scrollWidth` at **2049 against a client width of 360** until two declarations closed it, **each measured alone and each alone leaving the whole blowout in place**. |
| "over the **one existing** chip grid" | **BUILT, and proven** — `_theme_carousel_html()` emits no chip; a source scan finds exactly one function emitting a chip `<label>` carrying `data-preview-src`, and the arrivals, calendar and rule-add grids are byte-identical (three of three). |
| "◀ ▶" pagers | **BUILT, gated, and they are the only part that needed a script.** `theme-preview.js` **grew**; no new file appeared. They register **click only** — no `keydown`/`keyup`/`keypress` and no `preventDefault` anywhere in the file, asserted — because a pager capturing `ArrowLeft` would take the native radiogroup selection away from the scripts-blocked path that depends on it. |
| "big live preview" beside the strip | **NOT BUILT as an adjacency, deliberately.** The departures grid stays inside `.frame-colours__usage-panel`, so the strip renders *under* the preview/assignment pair. Moving it would take it out of `theme-preview.js`'s four-panel collapse machinery, which is D-08's locked no-JS floor, for a horizontal adjacency **that does not exist at either of the two viewports this D-item's own criterion is measured at** — everything stacks below 960 px. *Decision needed only if the developer wants the adjacency at desktop widths, which costs re-opening D-08.* |
| "a row of **24 px** colour dots" | **RE-SCOPED — the dots row ships at the existing `.theme-chip__dot` size (12 px), `aria-hidden`, carrying each theme's own registry colour and NO selection state.** Without a script or a `:has()` chain a server-rendered active dot could only mark the *saved* theme and would be wrong the instant a chip was clicked. **And see finding 1 below: on this registry the dots are not saying what the legend beside them claims.** |
| "theme name" | **BUILT** — unchanged, from the one chip renderer. |
| "full grid behind 'See all themes' **in a dialog**" | **RE-SCOPED TWICE, and both are recorded rather than substituted silently.** (a) **`<details>`, never `<dialog>`** (Decision 4): `showModal()` is the only thing that opens a dialog, so eighteen themes behind one is eighteen themes behind a dead control with scripts blocked. (b) **Nothing is "behind" it at all**: a closed `<details>` hides its own children, so a disclosure *containing* the grid would hide all eighteen whenever shut and there would be no strip. The disclosure is a **sibling** and governs the grid's layout through `[open] +`. The honest consequence is in real translated text at the markup site: **it changes a LAYOUT, not a VISIBILITY.** *This is one of CFG-50's two unmet clauses; the decision is in that row.* |
| "Display page drops **below 1 500 px**" | **NOT MET, by a long way, and the number is the verdict rather than a caveat.** Measured by a registered instrument before and after, same tree: **390 px 4276 → 3743 px (−533); 360 px 4269 → 3752 px (−517).** X6's phone target of 2600 px is **1143 px** away and D5's own 1500 px is **2243 px** away. The carousel *costs* ~82 px against the ~615 px the strip removes, and that is inside the −533. What remains is four more cards plus the Frame strip, not a grid. *This is CFG-50's other unmet clause; the decision is in that row.* |
| *(trap)* "`.theme-chip--compact` must stay size-only" | **BUILT** — M8 adds a `:has(input:checked)` to a compact rule and fails by name. |
| *(trap)* "a new selectable-state rule joins the existing `:has()` block; it never opens a second" | **BUILT, and the block was never even approached** — the `[open] +` combinator needs no `:has()`, so the count is still exactly 1. |
| *(scope)* the arrivals, calendar and rule-add grids converted too | **NOT BUILT, with the reason in `_theme_chip_grid_html()`'s own docstring** — they are already compact, already sit beside other controls, and none of them is the page-height problem X6 named. Four carousels would have multiplied the `:has()` risk by four for no gain. |

### D19 — "Drag-and-drop artwork upload" (CFG-51, served by 25-07)

| Audit clause | Verdict |
|---|---|
| "drag-and-drop artwork upload" | **BUILT**, over two upload forms that did not change, with a genuinely **trusted** drag measured through Chromium's DevTools protocol — so the `isTrusted` refusal and the end-to-end proof did not have to trade against each other. |
| "instant preview" | **BUILT, through a `FileReader` `data:` URL rather than `createObjectURL()`** — measured, not preferred: this app's own `img-src 'self' data:` blocks a `blob:` image outright, and the plan's own acceptance criterion would have passed against a preview that never rendered. **`companion/app.py` was not widened by one line for a thumbnail.** |
| "client-side `<canvas>` crop matching `illustration_normalize.py`" | **NOT BUILT, and the ground is that module's own docstring** — it records that a *second, differently-thresholded measurement silently drifting from the first* is the debug session that created it, and that it "must never become a second implementation for that same measurement to drift against". A browser-side crop that "matches" it **is** that second implementation, in a language the server cannot check, on a machine it cannot trust. What shipped instead is a **framing preview**: a box reserving the module's own aspect ratio (measured 3.4098:1 against 3.4091:1) with `object-fit: contain`, labelled as a framing preview. **The absence is asserted**, not assumed: `panel-lookup.js` names no `getContext`, `drawImage`, `toBlob`, `toDataURL`, `OffscreenCanvas` or `createImageBitmap`, comments included, and `companion/illustration_normalize.py` is unchanged by one line across the whole phase. *Decision needed: accept the framing preview, or re-open the crop — which now also costs deleting the check that forbids it.* |
| "progress bar" | **NOT BUILT** — `companion/static/submit-guard.js` already disables a form's submitting control on submit, app-wide, and a ≤ 4 MB upload to a household server does not need `XMLHttpRequest.upload.onprogress`. **And the recommendation's OTHER half was not built either, which is recorded rather than glossed: there is no "Uploading…" label.** *Decision needed: add the translated label (a string plus a relabel on the shape `submit-guard.js`'s own contract already permits — both existing Save controls are nameless `<button type="submit">`, and the upload submit would need the same check), accept the bare disable, or ask for the bar.* |
| "two cards per row on phone" | **ALREADY SHIPPED, and not this phase's work** — the Airlines illustration grid has rendered exactly two cards per row at 390 px since Phase 22, with each row's two columns equal within 1 px, and the browser check that pins it (and names the one-per-row auto-fill collapse that made the page 5800 px tall) predates this phase and still passes. Recorded so a future audit does not read the clause as outstanding. |
| "aircraft types on **hover**" | **NOT BUILT — hover is unreachable by touch, which is the exact ground CFG-28 used when it moved this app's tooltips out from behind hover.** The drop zone's own drag state follows the same rule: it rides on `[data-upload-drop-active]`, and a harness clause fails if any `.upload-drop` rule uses `:hover` (M8). *Decision needed: render the aircraft types as visible card text on Airlines — the alternative the research named and never refused — or drop the clause. It is a separate, cheap piece of work either way.* |
| *(security posture)* "the drop zone changes the affordance, not the parser" | **BUILT, structurally.** A drop assigns to the form's own `<input type="file">` through a `DataTransfer`, so there is one path: same POST, same route, same 4 MB cap enforced before the body is read, same parser discarding the client-declared filename, same normaliser. **One validator, one definition, two call sites**, asserted by source scan, refusal proven textually to precede the assignment, cap imported from `app.py` rather than retyped. `companion/app.py` is unchanged by one line against 25-07's base. |

### The eight provisional decisions the developer still owns

This phase was planned **without `/gsd-discuss-phase`, with no CONTEXT.md and no
UI-SPEC**, so every decision below would normally have been the developer's. Each is
listed with its alternative and **what reversing it would cost TODAY** — a decision
that was cheap to reverse at planning time may not be after seven plans landed on it,
and the developer should be told which is which rather than discovering it.

**1. The phase's script budget: ONE new file (`value-controls.js`).** *Alternatives:*
two new files (one per control — clearer names, two sets of the three taxes, two copies
of one clamp/round/keyboard/codec model); or **zero** new files by growing
`dirty-state.js`, which already writes into these exact fields for the quiet-hours
presets. *Reversal cost today:* **higher than at planning, and in a way the planning
note could not have known.** The two controls the file serves turned out to differ in
**two** attributes rather than one (geometry *and* a value codec — a time input is not
a numeric input), and a third consumer uses the file mainly to make it **stand aside**,
so a second file would largely be a file full of guards. Folding into `dirty-state.js`
is now strictly worse than it looked: 25-01's chosen mechanism — dispatching a bubbling
`change` onto the input, which that file's own delegated document-level listener
already handles — needed **zero** change to it, and that is the cleanest boundary
available. *Nothing shipped has to change to keep this; reversing it is a re-write of
one 795-line file.*

**2. D16 keeps the three `runway-*.png` photographs served.** *Alternative:* delete the
route and the three 338–371 KB files, saving ~1 MB and one route. *Reversal cost today:*
**unchanged and still cheap either way** — the map is an addition *above* the
photographs, `/runway-image/{id}.png` is untouched and still session-gated, and a
browser check measures all three still serving. Deleting them is still one route and
three files, and still irreversible in a way the addition is not. **This is the
cheapest decision on this list and the one most obviously taken by looking at the page.**

**3. D18's battery gauge is relative-with-a-conditional-absolute, not a flat
"≈ 38 days".** *Alternatives:* (a) ship the absolute figure from an assumed per-wake
cost — rejected outright, it is the dishonest-state defect Phase 22 spent a phase
removing; (b) **drop the battery gauge entirely and ship freshness alone**, which is
honest, much cheaper, and a legitimate choice if the developer would rather wait for
real discharge data. *Reversal cost today:* (b) is **still cheap** — the battery half is
one server-rendered sentence plus one readout template; `battery_life_estimate()` is
honest arithmetic with its own tests and could stay or go with it. **What has changed
since planning is the risk, not the cost:** the estimate is now *structurally* unable to
invent a figure, because no template the script can reach contains the days wording, so
the failure mode alternative (b) was meant to avoid is already closed by construction.
**And DEVICE-05's discharge run closes 2026-09-23 with a measured mAh-per-cycle
figure** — the input that lets a later plan add a second, model-based branch inside
`companion/battery.py` and print it through the same wording, with **nothing in the card
changing to accept it**. *This is the phase's most consequential open question and
25-05 named it as the item most needing a human's eye. The real question is the
WORDING, not the mechanism.*

**4. D5's full grid goes behind a native `<details>`, not a `<dialog>`.**
*Alternative:* a `<dialog>` with the `<details>` as its own no-JS fallback.
*Reversal cost today:* **higher than at planning, and it now collides with CFG-46.** The
shipped mechanism is an adjacent-sibling `[open] +` **layout toggle** over **one** set
of eighteen radios. A dialog needs either a second rendering of the grid (two
`--selected` chips, two check glyphs, thirty-six chip images for a setting with one
value, and a duplicate-id surface — T-25-06-B) or a move of the one set into the dialog,
which removes the strip. And a `<dialog>` cannot be opened without script at all, so
reversing this reopens the phase's own no-JS floor. *Nothing shipped would have to
change to keep it.*

**5. D19 sheds three of the audit's clauses.** *Alternative:* build all three as
specified. *Reversal cost today, per clause — they are no longer one decision:*

- *The canvas crop:* **cost went UP.** `panel-lookup.js` now carries a standing
  assertion that it names **no canvas API at all**, comments included, so adding one
  means deleting a check first. The ground is unchanged and is the normaliser's own
  docstring.

- *The progress bar:* **unchanged and small.** `submit-guard.js` already disables the
  submitting control. **Note the half that was also not built: the recommended
  "Uploading…" label.** Adding it is a translated string and a relabel on exactly the
  shape `submit-guard.js`'s own contract permits.

- *Hover-only aircraft types:* **unchanged**, and the alternative the research named was
  never refused — render them as **visible card text** on Airlines, which is separate,
  cheap work and does not touch the drop zone at all.

**6. D5's success is measured as Display's page height at 390 px, before and after.**
*Alternative:* judge the item by the carousel's existence. *This is the decision whose
ANSWER has changed, and it is the one that most needs the developer:* the instrument was
built before there was anything to like, it asserts no target at all, and it returns
**3743 px against X6's 2600 px — 1143 px over, and 2243 px over D5's own 1500 px**.
*What the developer now owns is not how to measure it but what to do with the answer:*
accept the number and amend or retire X6's phone target; or schedule a further density
pass against what is genuinely left (four more Display cards plus the Frame strip —
**not** a grid, and with no win of the carousel's size available inside a control plan's
scope); or re-word CFG-50's clause to name the measurement rather than a target. **The
instrument survives and is reusable either way.**

**7. No CONTEXT.md — and the sequencing is part of the record, not folklore.** This
phase was planned without `/gsd-discuss-phase`, so every decision above would normally
have been the developer's. **`.planning/ROADMAP.md`'s Phase 25 entry carries the
developer's own standing instruction verbatim: "this phase must not be executed before
the developer has seen Phases 23 and 24 on screen."** That is why the human sweep this
phase's verification demands is not a formality — it is the first time any of this has
been looked at, and it is the phase's real gate. Phase 06.6.1-06 is the precedent: a
real-device session found two confirmed CSS defects no harness had caught.

**8. No UI-SPEC.md.** Plans proceeded against the `sketch-findings-skypane` skill plus
`22-UI-SPEC.md`'s existing rows for D16/D17/D18/D19 — the precedent Phases 23 and 24
both set — even though 23-RESEARCH.md observed that this was "the phase most likely to
need its own UI spec, as Phase 22 had". *Reversal cost today:* a spec written now would
document shipped code rather than constrain it; **the skill was updated in step instead**
(25-08 Task 1, across `SKILL.md` and four reference files), which is the same
information in the place this project actually reads it from. *If the developer wants a
spec for the NEXT controls work, `/gsd-ui-phase` before execution is still the cheap
moment to add one.*

### Findings that must carry forward, not evaporate

**1. VACUITY is this phase's recurring defect class, and MUTATION is the only thing
that finds it.** Not one of the offending checks looked wrong; every one was green
against an implementation it was written to refuse. 25-01 strengthened **four** before
committing, 25-03 found **four**, 25-04 **three**, 25-05 **two**, 25-06 **one**. The
*shapes* transfer even where the subjects do not, and they are now recorded as testing
conventions in `references/data-density.md`: a mutation that edits a **comment** proves
nothing while looking rigorous; a **substring rename** can pass a seam check
(`data-theme-pagerr` survived one, leaving both pagers inert); locating a subject by a
**bare id string** can match inside another attribute; comparing your element's width
against **another element** passes when yours has no width rule at all; `.click()` works
on a **`display: none`** element, so a click-based helper stays green on the mutation
that destroys focusability; and `locator.count()` passes against an element moved
**behind the gate** — the exact refactor the clause existed to notice. **The question to
ask of every new check: what would a WRONG implementation do here? If the answer is
"pass", the check is decoration.**

**2. Never sample at a guessed instant — now a THREE-phase finding.** 25-03 read an
interpolation frame and **wrongly reported a theme that does not invert** against a
stylesheet that was entirely correct (a strip's settled dark value is
`rgb(241, 243, 246)` and the sample read `rgb(41, 43, 49)`, about 8 % along; the
`color-mix` samples gave it away by changing colour *space*). 25-05 met the identical
defect on the global `input, select` transition. Phase 24 lost a check to the same
class, fixed with `transitionrun`. **The instrument is the browser's own signal, never a
timer:** the Web Animations `finished` promise (an element with nothing running resolves
at once, so it can neither hang nor flake) or `transitionrun` — and count
`getAnimations()` only after one `requestAnimationFrame`, because immediately after a
theme flip there are none yet.

**3. A synthetic event can drive a real control, and the guard and the proof need not
trade.** 25-04 measured `_operate_with_keyboard()`'s own pointer-recorder self-test — an
`el.dispatchEvent(new PointerEvent("pointerdown"))`, carrying `clientX/clientY` of
`(0, 0)` — **moving the user's saved quiet window from 23:15 to 22:30** while merely
proving the recorder was alive. Any script on the page could have done the same.
`value-controls.js` now refuses `evt.isTrusted === false` (compared against `false`, not
negated, so a browser without the property does not refuse every real drag). 25-07 then
showed the guard need not cost the measurement: **Chromium's `Input.dispatchDragEvent`
carries a real files list through the same input pipeline a pointer uses**, so the
handler sees `isTrusted: true` and one check measures the real gesture *and* proves the
fake one inert.

**4. A function NAME can trip an existing guard, and the guard may be right.** 25-05's
`wake_battery_life_text()` failed the battery one-home guard by its name alone. It was
**renamed** — the function does not compute a lifetime and should not claim to — **not
allow-listed**, because an allow-list entry would have let a real second estimate in
under that name later.

**5. Two mutate/revert accidents, and the infrastructure hazard beside them.** 25-04 and
25-07 **each lost an implementation** to a revert against an **unstaged** tree:
`git checkout-index -f --` restores from the index, so an unstaged implementation is
deleted outright. Nothing was lost permanently either time and both cost a full
re-write. **Stage before you mutate — every time, not the first time** — and clear every
`__pycache__` outside `.venv` after the revert, because CPython validates cached
bytecode by comparing source mtime at **one-second granularity**, so a sub-second
mutate/revert cycle leaves stale bytecode serving the mutated behaviour. Both are now
standing conventions in `references/data-density.md`.

**6. A mutation suite without a NULL CONTROL cannot tell a load-bearing property from
layout jitter.** 25-07 mutated twenty-nine CSS declarations and re-measured the rendered
result each time; a mutation editing only a **comment** in the same block reported **14
measurements moved**, every one sub-pixel-to-4-pixel geometry jitter. Without that
control every mutation in the sweep would have read RED for the wrong reason. The same
run found one genuinely inert declaration (moving the rendering by **0.00 px** where the
null control moved it 0.01) and kept a neighbouring one that moved it ~1.9 px — and the
stylesheet now carries **both** results in a comment.

**7. Three plan shapes proved impossible as written, and each was resolved rather than
fudged.** 25-06's `<details>` could not wrap the same grid it presents (a closed
`<details>` hides its own children); 25-07's `createObjectURL` preview was blocked by
this app's own CSP; 25-03's caption could not claim relative lengths because the
registry carries no length. **In all three cases the plan sentence is recorded as wrong
rather than quietly satisfied**, which is the only way the next reader meets the
argument instead of the idea.

**8. The stylesheet's accent-reservation list is STILL not exhaustive, and this is now a
two-phase-old gap.** Phase 23 added two genuine accent consumers without extending the
header list — `.switch[aria-checked="true"] .switch__track`'s fill and
`@keyframes skypane-row-arrive`'s 22 % wash — and recorded the repair as belonging to
"whichever plan next edits that stylesheet". Phase 24 edited it and did not; **Phase 25
edited it and extended the list by exactly one** (25-05's wake range, inheriting
`accent-color` from the global `input, select` declaration, recorded in place as "a
genuine broadening rather than a clarification"). So the mechanism demonstrably works
and the list is one entry longer and still two entries short. Verified live at this
phase's close: both Phase 23 consumers are still in the stylesheet and still unlisted.
**Decision needed: whichever plan next edits `companion/static/style.css` extends the
list by those two with Phase 23's reasoning — it is recorded here so it stops being
nobody's.**

### Two product findings, folded in from `deferred-items.md`

Both were logged by a plan that did not own the fix. Neither was caused by the plan that
found it, and both need a developer's decision rather than an implementation.

**1. Every shipped theme paints its "Departures" and "Arrivals" swatches the SAME
colour.** Found by 25-06 while mutation-testing the carousel's dots: painting each dot
with `arriving_index` instead of `departing_index` changed **not one byte of output**.
Measured over `server/device_config.THEMES`: **`departing_index == arriving_index` for
18 of 18 themes**, and the eighteen resolve to **seven** distinct palette hexes. So the
one-line legend 22-10 added under every chip grid — `"Departures · Arrivals"` /
`"Départs · Arrivées"`, copy 22-10 deliberately chose over the spec's wrong
`"Background · Ink"` **precisely because** the dots are the departing and arriving inks —
names a distinction nobody can see, and two identical squares beside a label naming two
different things reads as a rendering fault. The carousel did not cause it; it put the
same dots in a row where the repetition is obvious at a glance. **Decision needed:
either the registry is *supposed* to allow different departure/arrival inks and no
shipped theme currently uses that (in which case the dots and the legend are correct and
merely under-exercised), or it is not, and the chips should show one swatch with a
legend naming what it actually is.** The fix lives in `server/device_config.py` (which
decides what the *frame* paints) or in the one shared chip renderer — 25-06 owned
neither question. *The check was strengthened rather than left as-is: it now also
requires the dots row to carry more than one distinct colour, which catches the wrong
implementation that actually exists (a fixed palette index for every dot).*

**2. `.copy-btn`'s real hit area inside a Flights detail row is 34 × 26, not 44 × 44.**
Found by 25-02 while demonstrating its own hit-area instrument against a subject whose
answer was supposed to be already known. Measured on `/flights` at 1280 × 900 with the
row expanded and its `<tr>` hovered (so the desktop `pointer-events: none`-at-rest rule
is not the cause): visual box 22 × 22, **real hit area 34 × 26**, reaching 12 px left,
21 right, 23 up and 2 down from its own centre. The `::before` synthesis *is* reaching
the hit test — every axis exceeds the 22 px box — but neighbours inside
`.flight-detail-row__grid` cover 12 of the 22 px available on the left and 20 of the 22
below. **The same class measures 45 × 45 in the row toggle's position, so the rule is
fine and the PLACEMENT is what eats it.** It is pre-existing and outside every Phase 25
plan's files. **Decision needed: give the copy buttons room inside
`.flight-detail-row__grid`, or record the 34 × 26 honestly in the touch-target register
the way `.airline-card__chip`'s 20 px exception already is.** It now sits beside that
exception in `references/control-density.md` as the register's second open entry.

**No intermittent checks were carried into this phase's `deferred-items.md`**, and both
of Phase 24's own intermittents are that ledger's, not this one's — the entry that was
promoted to a real fix there (the theme-preview crossfade, now waiting on
`transitionrun`) passed in both of this gate's runs.

### The phase gate

Re-derived by **running**, at this phase's close, never trusted from a plan.

**The full suite: exactly the 5 documented sandbox baseline failures, verified BY NAME
and by no other measure** (`PYTHON=server/.venv/bin/python3 bash scripts/run-all-tests.sh`,
run **three times** — before this plan's edits, after the design-system commit, and
again on the final tree — with identical results every time, and exactly five `FAIL`
lines in the whole output on each:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … the state dir is read-only … (WR-11)` — `companion/test_companion_app.py`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)` — `companion/test_companion_app.py`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because the parent directory is read-only … (WR-11)` — `server/test_manual_resolutions.py`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)` — `server/test_manual_resolutions.py`
5. `anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely` — `companion/test_status_pages.py`

**No sixth.** These five fail only because this container runs as root; they pass in CI.

**`companion/test_browser_ux.py` did NOT skip, and the wall clock is the proof it ran.**
`grep -c SKIP` over the whole suite output is **0**, and over the harness's own standalone
output it is **0**. **81/81 checks pass, 0 FAIL, in 274.8 s inside the suite and in
270 s (4 m 30 s) standalone** on the final tree — a skipped harness returns in under a
second, and this phase is almost entirely interaction, so a SKIP would have meant every
control contract in it went unchecked. It is the slowest file in the suite by a factor
of nine, and it is the whole suite's critical path (total wall time 274.8 s at JOBS=4).

**Structural pins, re-verified from the code against the phase's base commit `f7d25d9`:**

| Pin | Base | Now |
|---|---|---|
| `@supports selector(:has(*)) {` blocks (comment-stripped, brace-anchored) | 1 | **1** |
| `@keyframes` (comment-stripped; `^@keyframes` agrees) | 4 | **4** |
| `@media (prefers-reduced-motion: reduce)` blocks (comment-stripped) | 2 | **2** |
| `prefers-reduced-motion: no-preference` blocks (comment-stripped) | 1 | **1** |
| `ls companion/static/*.js \| wc -l` | 16 | **17** (exactly one more) |
| deferred `<script src=` on the authenticated shell | 14 | **fifteen** (its own named check passes) |
| stray comment terminators in `style.css` | 0 | **0** |
| `companion/illustration_normalize.py` | — | **unchanged by one line** (`git diff` empty) |

*(A bare `grep -c '@supports selector(:has(\*))'` returns **6** and a bare
`grep -c '@keyframes'` returns **5** — both are prose in comments quoting the at-rule,
which is why every pin above is comment-stripped. The bare counts are recorded so the
next reader does not treat them as a regression.)*

**The five no-JS persistence checks — one per control, all passing, all reading the
value back from disk.** This is the phase's central claim and it is verifiable by
reading five names rather than by trusting a narrative:

1. *"the runway still SAVES with scripts blocked through the map, at 360px and in BOTH shipped languages … re-read FROM DISK after a fresh GET, and restored through the identical sequence …"* (D16, CFG-47)
2. *"the quiet window still SAVES with scripts blocked through the dial — both ends set natively … re-read FROM DISK after a fresh GET and restored the same way …"* (D17, CFG-48)
3. *"the wake interval still SAVES with scripts blocked beside the slider — typed natively … re-read FROM DISK after a fresh GET and restored the same way …"* (D18, CFG-49)
4. *"the theme still SAVES with scripts blocked through the carousel, at 360px and in BOTH shipped languages … re-read FROM DISK after a fresh GET and restored the same way …"* (D5, CFG-50)
5. *"with scripts blocked at 360px, an artwork file chosen through the native `<input type="file">` … is STORED (read back off the real state directory, never off the page …) and SERVED back by the illustration route …"* (D19, CFG-51)

**Final `EXPECTED_CHECK_COUNT` for every harness this phase moved**, each re-derived by
running:

| Harness | Pre-phase | Final | Passing here |
|---|---|---|---|
| `companion/test_browser_ux.py` | 65 | **81** | 81/81, 0 SKIP |
| `companion/test_companion_app.py` | 300 | **314** | 312/314 (the two WR-11) |
| `companion/test_config_page.py` | 240 | **259** | 259/259 |
| `companion/test_status_pages.py` | 302 | **305** | 304/305 (`anomaly_active()`) |
| `companion/test_i18n.py` | 24 | 24 | 24/24 |
| `companion/test_view_pages.py` | 164 | 164 | 164/164 |
| `companion/test_contrast_check.py` | 49 | 49 | 49/49 |

`ruff check .` — **All checks passed!**

**The two standing refusals stay refused and UNREVERSED, and this phase reopened
neither.** The **overlay drawer** (three recorded rejections plus locked decision D-10,
one of them from real-device testing) is absent: `grep -i drawer` over the
comment-stripped stylesheet returns **0**. **Sticky day headers** (struck twice; every
flight row already carries its own date) are absent: `position: sticky` appears **once**
comment-stripped, its pre-phase value, and that one is not a day header.

**What this gate does NOT cover, stated plainly: the human sweep.** All five controls
judged together on a real phone at 360 px and on a desktop, in both themes and both
languages, operated by touch **and** by keyboard — specifically the dial's handles when
the window's ends are close, the battery gauge's **wording**, Display's page height, and
whether the three clauses removed from D19 are accepted. That review is the developer's
and is not claimed here.

## Phase 27 coverage ledger (companion review feedback — the defects and the noise the developer found on the real app)

Written at the phase's close by 27-09, by walking the dial defect and all nine
corrections/findings against the eight preceding SUMMARYs **and against the
code, on the finished tree with every plan's changes applied** — not against
what the plans intended. It exists so the developer can see in one place what
shipped, what was investigated and found not to need shipping, and what is
still theirs to judge. **The traceability rows above carry the per-requirement
evidence; this section carries the clause-by-clause walk, the re-verification
of two things this phase itself warned would need care (CFG-68's height
prediction and CFG-47's retirement note), and the findings that must carry
forward.**

One of ten rows is deliberately left unticked (**CFG-65**) — investigated,
found not to be a defect, and recorded as that rather than rounded up to
"fixed". That is the standard Phases 23, 24 and 25 held, and the standard this
phase's own lesson demands most: a phase that exists because two correct
halves shipped a lying arc cannot itself round a finding up to make its own
ledger look cleaner.

### The dial defect (CFG-62) — the reason this phase exists, in its executable form

**D17 shipped with three individually correct, individually passing checks,
and the relationship between them was never asserted.** The arc was asserted
correct **server-side**, for the saved value. The handles were asserted **to
move**. The value was asserted **to persist to disk**. All three passed,
against a page on which the fields read `08:00`/`18:00`, both handles sat at
8 and 18, and the arc and the caption still drew `23:00 → 07:00`. Two correct
halves; the relationship between them unmeasured; an arc that lies is worse
than no arc.

**What closed it, and the check that now measures the relationship.**
`value-controls.js` now publishes a shared-ancestor fraction seam
(`data-value-pair`/`data-value-pair-property`) and derives the sweep as
`(end − start + 1) % 1` — the `+1` is load-bearing and was found by the check
itself: reusing the handle's own cosmetic `(value−min)/(max−min)` fraction
decoded 23:00 as minute 1381, not 1380. `_the_arc_the_handles_and_the_caption_
agree_after_an_interaction()` (`companion/test_browser_ux.py`, 27-02) decodes
all four surfaces — the two native `<input type="time">` fields, the two
handles' `aria-valuenow`, the arc's RESOLVED geometry (`stroke-dasharray` +
`transform`, real SVG user units, never `getBoundingClientRect`), and the
caption's text — to ONE canonical minute-of-day pair via 27-01's
`_assert_surfaces_agree()`, over a real pointer drag AND a preset press, in
both themes. Reverting the seam's three publication lines reproduces the
shipped defect **live, on this plan's own fix, on demand**:

> `_assert_surfaces_agree: drag path — the 4 surfaces describing this value
> DISAGREE ... the arc's resolved geometry -> (480, 1380) ... The interaction
> asked for (480, 1080)`

**The server-rendered arc stays authoritative, and this is re-verified at this
phase's close, not merely at 27-02's.** `quiet_dial_svg()`'s own output is
**byte-identical** before and after the WHOLE plan's diff, across four windows
including the wrap and the 1-minute floor — script only ever overrides what is
already correct, computed from the SAME custom properties the server also
renders inline at rest. Re-run today (2026-09-15), directly comparing the
phase's base commit (`839489a`) against HEAD, after five more plans (27-03
through 27-08) touched `config_page.py` again: **still an exact match, all
four windows.** The caption's duration BLANKS rather than showing a stale or
wrong number — an empty `data-value-readout-text` template, so both of
`paintReadouts()`'s branches resolve to `""` the instant the pair moves away
from what the server rendered. This is PROVISIONAL (27-02's own note): a
reviewer who finds the disappearing duration during a drag unacceptable has
C2 (server-emitted per-unit templates, 27-RESEARCH.md) as the recorded
fallback.

### Correction 1 — no save button, and the no-JS floor kept by construction (CFG-63, CFG-64)

**Both requirements complete.** CFG-64 landed FIRST (27-03, wave 3),
deliberately, so the no-JS floor was never momentarily made of the thing being
removed. The native settings-form submit's emission is proven unconditional
at the **AST source level** — one `return` statement, never nested under any
`scope` branch, `STATIC_SAVE_FALLBACK_ATTR` reached as a bare `Name` never
behind an `ast.IfExp` — not merely observed to render today, which is the
difference between "the floor holds" and "the floor happens to be up right
now." The CSS gate reverted to the simplest possible form, a plain `.js`
selector; B1/P0's original two-marker `[data-static-save-fallback]` visibility
contract is **superseded in writing**, not deleted — its comment block is kept
verbatim in `companion/static/style.css` and a dated paragraph is appended
after it, naming CFG-64/27-03-PLAN.md, with no CSS selector literal quoted
(D-30).

CFG-63 (27-04, wave 4) then retired the dirty save bar outright — no button,
no Cancel, no per-field count, no connector words — and rebuilt the settings
form's save behaviour on the exact optimistic-apply → fetch POST → exact-204-
confirms → otherwise-revert-and-toast model the three `role="switch"`
controls already shipped, reusing the app's ONE existing failure vocabulary
(the same generic translated toast, never a new string). The sole visible
affordance is one `role="status"` region, empty at rest, holding "Saving…"
then "Saved" (or their French siblings) — proven with a `MutationObserver`
recording the FULL text sequence, never sampled only at the settled state,
which is what caught a real vacuity gap in the check's own first draft
(mutation M-B: a status region that briefly claims "Saved" during a FAILED
save, then quietly self-corrects, passed a settled-state-only read).

**One clause is RE-SCOPED by the developer's own binding decision, and it is
recorded here rather than silently reconciled.** CFG-63's own wording
anticipated the leave-guard being "retired only where it means discard a
pending edit, and kept where it confirms a destructive act." What actually
shipped, per the developer's explicit instruction
(`.planning/ROADMAP.md`, "Developer decisions, taken 2026-09-15"): the
`beforeunload` leave-guard stays alive **in full**, not partially retired,
because a keystroke that never fires `change` (the event auto-save listens
for) still needs the exact protection the old dirty bar used to guarantee —
pasting a calendar URL and closing the tab without leaving the field must not
lose the edit silently. This is a genuine departure from the requirement's own
anticipated shape, directed by the developer and executed as directed; it is
recorded as a re-scope rather than absorbed into a plain "built as worded."
"Annuler" is gone outright — there is no more pending-edit state left for it
to cancel.

### Correction 2 — one title form (CFG-65) — INVESTIGATED, NO DEFECT FOUND, NOT TICKED

**This row is deliberately left unticked**, per the standard Phases 23-25
held: a requirement whose premise does not survive investigation is recorded
as unmet, not quietly rounded up.

The developer's report was "titles sit inside the tile on some cards and
above it on others." 27-06's executable inventory (`config_page.render()`,
both scopes, counted directly against the server-rendered HTML — no browser
needed) measured, of 12 total `text-heading` instances:

| Form | What it is | Count |
|---|---|---|
| A — `[data-dirty-section] > h2` | the first thing inside a bordered settings card | **7** |
| B — `.section-intro > h2` | `layout.section_intro_html()`, shared byte-identical with Health | **3** |
| unclassified | the Frame strip's own live-status heading; the Poll card's bare-section heading | **2** |

This reproduces 27-01's own browser-driven 7/3/2 exactly, and corrects
27-RESEARCH.md's provisional 8/3/2 — the eighth grep hit is a form-A call site
neither settings route actually renders.

**Is this a genuine inconsistency, or two legitimate forms? Investigated
structurally, not by impression.** Form B is not a second card-title form —
it introduces a SUPERSECTION, and at least one instance ("Look") introduces
**two** cards at once (Frame colours and Calendar), which a card title, naming
exactly one card, structurally cannot do. The two forms also render at
genuinely different sizes on purpose: nested cards under a supersection render
their own `<h2>` at 16px sans-semibold, un-nested cards and supersection
intros themselves at 22px serif regular — `style.css`'s own comment on that
rule states this is "the third and final state of a three-round
developer-reviewed decision... not a mistake to second-guess," shared verbatim
with `health_page.py`. Converting either direction costs reversing a validated
prior decision this plan has no standing to reopen (B→A) or editing
`layout.section_intro_html()` away from a shape Health's own structural checks
match literally (A→B). **No markup or CSS was converted.**

**Verdict: the developer's impression very likely traces to Display's three
supersection headings being visually present where Device has none at all —
a real, intentional structural difference between the two settings pages —
rather than to a per-card title inconsistency. This is a separate,
out-of-scope, developer-confirmed design decision (the heading-ladder's own
three-round-trip history), not a defect this phase can or should fix.**
Guarded going forward at the source level:
`_no_card_builder_function_ever_calls_section_intro_html()`
(`companion/test_config_page.py`, AST-based) asserts **zero** of the seven
settings-card builder functions ever call `layout.section_intro_html()` for
their own `<h2>` — mutation-tested (a spurious call inserted into
`led_group()` fails by name, naming the offending function).

**Decision this leaves the developer**: accept that there is no title-form
inconsistency to fix, and that what reads as one is Display's supersection
structure; or, if the impression persists after a fresh look, ask specifically
about the heading-ladder's third round-trip rather than about "the titles" —
that is where the actual visual difference lives.

### Correction 3 — D16's runway map removed, CFG-47 retired (CFG-66)

**Complete (27-05).** `runway_map_svg()`, `runway_bearing_deg()`, nine
`RUNWAY_MAP_*` constants and all seven `runway-map`/`runway-map__*` CSS rules
are gone. Every map-only check is named and removed (3 per harness — the
registry-following proof, the bearing-derivation math, the paint/feature-query
assertions on the browser side; the map-drawn-from-registry proof, the
bearing math and the paint/join proof on the markup side). Two pre-existing
checks that bundled a map-only assertion with a still-load-bearing
control/security assertion in the SAME function were mutated IN PLACE rather
than deleted or left broken — the map's own colour-literal ban and shape-paint
requirements dropped, `runway_fieldset()`'s own hostile-label escaping proof
(the only escaping check for runway labels anywhere in the suite) kept. One
new relationship check
(`_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor`)
asserts absence-of-map AND presence-of-the-control AND presence-of-the-
photographs as ONE fact, replacing three narrower ones — mutation-tested
twice (re-adding a map class; deleting a radio), each failing on the correct,
named clause.

**The radios' own scripts-blocked save-to-disk proof is CFG-64's check
(`_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies`),
never the map-era one** — its own docstring already states the distinction
("unlike 25-03's own check, which corroborates with the runway MAP's
presence, this one asserts the SUBMIT itself"), and `git diff` confirms zero
edits to its function body across the whole plan. Touch targets re-measured
now that the map strip no longer provides the box: **90×138 / 89×136 /
88×136** at 360px in both themes, within a pixel of 25-02's own pre-map
baseline (88×138) — the map's removal returns the card to substantially its
pre-map shape, not to empty space or a shrunk target.

**CFG-47's retirement is RE-VERIFIED intact at this phase's close, per the
standing instruction that several later plans touched the same files again.**
All three records are present, dated `2026-09-14`, and consistent with the
tree Phase 27 actually produced:

1. The ticked requirement row (`.planning/REQUIREMENTS.md`, CFG-47): `[x]`
   present, `**RETIRED (Phase 27, 2026-09-14).**`

2. The traceability row (CFG-47): the full clause-by-clause evidence from
   25-03, ending `**RETIRED 2026-09-14 (Phase 27).**`

3. The D16 coverage-ledger section (Phase 25's own ledger, above): `**RETIRED
   2026-09-14 by Phase 27 (CFG-66).**`

`grep -c RETIRED .planning/REQUIREMENTS.md` → **3**, re-run today
(2026-09-15) on the finished tree — unchanged from 27-05's own count, despite
27-06, 27-07 and 27-08 each editing `config_page.py` and/or `style.css` again
after 27-05 landed.

### Correction 4 — the explanatory text cut, honesty contract intact (CFG-67)

**Complete (27-06), and RE-VERIFIED on the current tree rather than trusted
from 27-06's own close.** Three regions shortened, each measured as a
character count against 27-01's own recorded baseline, each check reading the
region ONCE and asserting length + refusal-survival against that SAME
reading:

| Region | Route | Before | After |
|---|---|---|---|
| Wake-interval caption | `/device` | 220 | **137** |
| The two wake gauges (combined) | `/device` | 254 | **168** |
| Quiet hours paragraph | `/display` | 188 | **121** |

Every cut removes only a mechanism/reason clause; every honesty-contract or
live-computed-state clause survives verbatim in meaning — the "at most" bound
on the freshness gauge, the battery refusal sentence itself, and the Quiet
hours delay sentence (computed live from `frame_state`, asserted to survive in
the SAME check as the length cut).

**Re-verified today (2026-09-15), directly against the shipped
`wake_battery_observed_text()`:** its docstring is unedited since 27-06 —
*"an absolute figure ONLY when this frame's own observed history supports
one, and the named 'not enough history yet' sentence in every other case"* —
and calling it with an empty `battery_rows` series still returns *"Not enough
battery history yet to say how long a charge lasts."*, with zero match against
the days-CLAIM-shaped forbidden pattern
(`≈\s*\d+\s*(?:day|days|jour|jours)\b` — deliberately scoped to the CLAIM
shape rather than to `≈` near any digit, since the wake-interval caption's own
legitimate `(next wake ≈ 31 Jul 08:05)` text would otherwise false-positive
on a naive pattern, a trap 27-01 flagged before 27-06 ever wrote the check).

### Correction 5 — the carousel extended, the disclosure moved, the height measured (CFG-68)

**Complete.** `_theme_carousel_html(grid_html, strip_id)` takes `strip_id` as
a **required** argument — no shared default, so the duplicate-id/wrong-pager-
target trap (`THEME_CAROUSEL_STRIP_ID` used to be one module-level literal
read by both pagers' `aria-controls` builders) is closed **structurally**,
mutation-tested against a simulated collision (two copies of the departures
carousel's own output on one page fail by name, naming the exact id and the
exact hazard). Arrivals and calendar fold into the same scroll-snap mechanism
departures already had, each with its own id, its own scripts-blocked save
proof (seeded through the validated `save_device_config()` API for
`theme_arriving`, since its `None` state would otherwise defeat the shared
save-floor guard's own "stored is None" check), and its own per-instance
`:has()`-scoped toggle, proven independent in a real browser (opening one
carousel's disclosure leaves both siblings' strips `nowrap` while only the
opened one reads `wrap`). "Voir tous les thèmes"/"See all themes" now renders
LAST in the shared wrapper (grid, pagers, dots, disclosure) — a one-line
reorder of the ONE shared helper, correcting all three carousels at once. The
swatch legend ("Departures · Arrivals" → "Departures & arrivals"/"Départs et
arrivées") is checked as a REGISTRY RELATIONSHIP (the expected label count
computed from `device_config.THEMES` at check time), never a literal string —
closing the phase's first carried-in finding, see CFG-70 below.

**Display's page height, measured at THIS phase's close (27-09,
2026-09-15), against 27-07's own STATED prediction — the standard this row
holds itself to.** 27-07 predicted, before anyone measured: **≈3446–3496 px**
(midpoint ≈3471 px) at 390px, arithmetic stated in full (≈0 px from the
carousel extension itself, since `theme-preview.js` already collapses
non-selected panels at load; ≈−63 px from the runway-map removal; an
ESTIMATED −40 to −90 px, midpoint −65, from the text cuts; ≈−144 px from the
dead `.dirty-ready` padding-bottom removal), and stated plainly that **2600 px
is NOT expected to be reached.**

**Measured today, reproducing 25-06's own conditions exactly
(`_display_page_height()`, scripts enabled, authenticated, pointed at the real
Display page, both phone widths): 3524 px at 390px (and 360px — identical, as
25-06 also found).**

| | 25-06 baseline | 27-07's prediction | Measured (27-09) |
|---|---|---|---|
| Display height, 390px, scripted | 3743 px | ≈3446–3496 px (mid ≈3471) | **3524 px** |

**The measured figure sits 28 px ABOVE the top of the predicted range — a
missed prediction, reported as one, not silently widened to fit.** The
reduction that actually happened is **−219 px** (3743 → 3524), against a
predicted reduction of −247 to −297 px (midpoint −272). **Why, named rather
than left as an unexplained gap:** 27-07's own text-cut term (−40 to −90px,
midpoint −65) summed ALL 236 characters 27-06 cut across THREE regions — but
two of those three regions (the wake-interval caption, the two wake gauges)
render only on `/device`, never on `/display` at all
(`screens.GROUP_WAKE_INTERVAL` is Device-scope-only, per its own code
comment: "read only on a scope that actually renders this group... and never
on Display"). Only the Quiet hours paragraph's 67-of-236 characters actually
apply to Display's height — so the applicable text-cut term should have been
roughly a third of what was estimated, on the order of −11 to −25 px rather
than −40 to −90 px, an overestimate of roughly 40-50 px at the midpoint from
scope alone. A second, smaller contributor in the same direction: the
`.save-status` region that replaced the dirty bar's fixed `padding-bottom`
reservation is measured, in its own empty-at-rest state, at **0 px** of its
own box height (only its `margin-top: 8px` is real), so the `.dirty-ready`
padding removal (−144 px) is very nearly fully realized rather than partly
offset. Together these account for most of the 28 px the measurement missed
the range by. **The lesson, in the same voice 25-06 used**: what is left after
this phase is still four more Display cards plus the Frame strip, not a grid
— 2600 px is **924 px** away, and no further win is available inside a
correction-only phase's scope.

**The scripts-blocked (no-JS) height, measured for the first time at this
close: 5550 px at 390px (5581 px at 360px)** — roughly 2000 px taller than the
scripted page, confirming 27-07's own prediction that the carousel
extension's real saving is for a no-JS reader (all three grids render their
full, un-collapsed rows with scripts blocked) rather than for the default
scripted load (where `theme-preview.js` already collapsed the non-departures
grids before this phase ever touched them). **No horizontal body scroll at
360px, confirmed on every page this phase touched (`/display`, `/device`,
`/`, `/flights`), in both themes** — `scrollWidth` equals `clientWidth` (360)
in all eight measured combinations.

### Correction 6 — the Frame strip's Quiet hours link (CFG-69)

**Complete (27-08).** `config_page.QUIET_HOURS_GROUP_HEADING_ID` gives the
Quiet hours card's own `<h2>` a stable fragment target.
`layout.frame_strip_html()`'s quiet cell appends a real
`<a class="text-link frame-strip__schedule-link" href="/display#quiet-hours-group-heading">`
to a **copy** of the shared `delay_caption_html` (never the shared variable
itself, which the Screen cell's own caption also reads two lines earlier in
the same function) — one write site, unconditionally, so both Home and
Display get the identical markup from the identical call by construction, not
by two independently-maintained call sites that happen to agree today. Proven
by ONE check rendering both `home_page.render()` and
`config_page.render(scope=SCOPE_DISPLAY)` and asserting (a) both carry the
link and (b) the two hrefs are byte-identical — mutation-tested against total
removal (fails, naming both missing pages) and a simulated per-page fork
(fails, naming the two different hrefs it produced). The href targets
`layout.DISPLAY_ROUTE` directly, never `SETTINGS_ROUTE` (a legacy 303 redirect
that would add an unnecessary hop). Clears the 44px floor via `inline-flex` +
`min-height`, measured by real hit-testing at 360px in both themes; neither
page gains horizontal scroll from the addition.

### The two carried-in findings, closed rather than re-deferred (CFG-70)

**Both complete.** These were logged by earlier phases against the SAME
correction the developer's review independently surfaced work near, not new
findings from this review itself.

**The swatch legend** (found by 25-06: `departing_index == arriving_index`
for 18 of 18 shipped themes, so "Departures · Arrivals" named a distinction
nobody could ever see) — closed under CFG-68's own carousel-rewrapping plan
(27-07), properly this row's subject: the legend now reads "Departures &
arrivals"/"Départs et arrivées", checked as a registry relationship rather
than a literal.

**`.copy-btn`'s 34×26 hit area** in a Flights detail row (found by 25-02
while demonstrating its own hit-area instrument) — closed by 27-08, which
found the cause was a *container* problem, not a button problem: `.copy-btn`'s
own declared box/inset values are correct everywhere else, including
`.row-toggle`, which shares those exact values verbatim and already resolved
45×45. The hex button's real defect was a ~4px gap to a trailing sibling
crushing its downward reach to 2px (of an expected ~22px) and an
`overflow: hidden` clip boundary on its container crushing its leftward reach
to ~12px (of an expected ~22px) — both fixed with container spacing
(`.flight-detail-row__grid` `margin-bottom`, `.flight-detail-row__reveal-inner`
`padding-left`), closing to a resolved **45×45**, never by touching
`.copy-btn`'s own rule. `.row-toggle` is separately re-measured and
mutation-proven **independent** — a mutation that shrinks ONLY
`.row-toggle::before`'s own inset names `.row-toggle` alone in its failure
message, with no mention of `.copy-btn`, confirming the two controls are
measured as genuinely separate subjects even though they share one register
of values.

### The instrumentation floor (CFG-71)

**Complete, across the whole phase.** The pattern every later plan in this
phase registers against: `_assert_surfaces_agree()` (27-01) decodes N rendered
surfaces describing one logical value to a canonical form, builds the SET of
decoded values, and asserts three things, never one — the set has exactly one
member (the surfaces agree); that member equals what the interaction
requested (agreement on the wrong value is what a page frozen together looks
like from outside); and that member differs from what was there before (a
no-op is the cheapest way to make every surface on a page agree). Applied to
the dial (27-02, the phase's own defect), to auto-save's own settle sequence
via `MutationObserver` (27-04), and generalized in the "review-feedback
discipline" paragraph now recorded in `sketch-findings-skypane`. See the
phase gate below for the re-derived counts, the five baseline failures by
name, and the structural pins proven together, once, at the end.

### The phase gate

Re-derived by **running**, at this phase's close (2026-09-15), never trusted
from a plan.

**The full suite: exactly the 5 sandbox baseline failures, verified BY NAME.**
`PYTHON=/home/user/skypane/server/.venv/bin/python3 bash scripts/run-all-tests.sh`,
run to completion, total wall time **265.9s** at `JOBS=4`
(`companion/test_browser_ux.py` is the critical path at 265.9s inside the
suite; standalone it runs in **4m17.4s / 257.4s**). `grep -c '^FAIL'` over the
whole run's output is **5** (a bare `grep -c FAIL` returns 14 — it also
matches the run's own "FAILED harnesses (3)" summary lines and the per-file
timing table's "FAIL" column, neither of which is a check result; anchored to
the start of the line is what counts real per-check FAIL lines), and the five
are, by name, unchanged from the set every earlier plan in this phase
reported:

1. `POST /airlines/resolve redirects with the manual_save_failed flash key … the state dir is read-only … (WR-11)` — `companion/test_companion_app.py`
2. `POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key … (WR-11)` — `companion/test_companion_app.py`
3. `add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because the parent directory is read-only … (WR-11)` — `server/test_manual_resolutions.py`
4. `delete_entry() returns False (never raises) when the state dir goes read-only mid-write … (WR-11)` — `server/test_manual_resolutions.py`
5. `anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely` — `companion/test_status_pages.py`

**No sixth.** These five fail only because this container runs as root; they
pass in CI. `grep -c SKIP` over the whole run's output is **0** —
`companion/test_browser_ux.py` really ran, in full, both times it was run
today (once inside the suite, once standalone).

**Every scripts-blocked save-to-disk check named and confirmed PASSING** —
the phase's central claim is executable, not narrated:

1. *"the runway ... no-JS floor still SAVES TO DISK after the gate simplifies to the plain .js rule (CFG-64) — tracked_runway operated natively ... re-read FROM DISK after a fresh GET ..."* (27-03's floor proof, which SUPERSEDED 25-03's own map-corroborated check when 27-05 removed the map)
2. *"the quiet window still SAVES with scripts blocked through the dial — both ends set natively ... re-read FROM DISK after a fresh GET and restored the same way ..."* (25-04)
3. *"the wake interval still SAVES with scripts blocked beside the slider ... re-read FROM DISK after a fresh GET and restored the same way ..."* (25-05)
4. *"the theme still SAVES with scripts blocked through the carousel ... re-read FROM DISK after a fresh GET and restored the same way ..."* (25-06)
5. *"with scripts blocked at 360px, an artwork file chosen through the native `<input type="file">` ... is STORED (read back off the real state directory ...) and SERVED back by the illustration route ..."* (25-07)
6. *"the arrivals grid — the first grid this plan newly folds — still SAVES with scripts blocked through ITS OWN carousel ..."* (27-07)

`grep -c 'new_context(java_script_enabled' companion/test_browser_ux.py` →
**1** — exactly one scripts-blocked context, composed with, never duplicated.
**A criterion that did not evaluate as predicted, recorded rather than
silently adjusted**: this plan's own interfaces section asked for
`grep -n 'java_script_enabled' companion/test_browser_ux.py` to return exactly
one line; it returns **6** (five of them prose in comments), and 27-01 already
found and recorded this exact fact on the phase's base commit — the call-site
count above is the invariant that actually holds, and is what every plan
since 27-01 has pinned.

**Structural pins, proven TOGETHER, at the end, against the phase's own base
commit `839489a`:**

| Pin | Base | Now |
|---|---|---|
| `@supports selector(:has(*)) {` blocks (comment-stripped, brace-anchored) | 1 | **1** |
| `@keyframes` (comment-stripped, `^@keyframes\b`-anchored) | 4 | **4** |
| `ls companion/static/*.js \| wc -l` | 17 | **17** (`dirty-state.js` REPURPOSED, not replaced — the whole reason the count could hold) |
| deferred `<script src=` on the authenticated shell | 15 | **15** (`_fifteen_deferred_scripts_before_closing_body`, passing) |
| stray comment terminators in `style.css` (`/*` vs `*/` counts) | balanced | **486 / 486, balanced** |
| `interpolate-size`/`calc-size(` in `style.css` | 2 (both banned-property prose) | **2**, unchanged |
| the overlay drawer (`grep -i drawer`, comment-stripped) | 0 | **0** |
| `position: sticky` (comment-stripped) | 1, `.dashboard-sidebar` | **1**, same rule, not a day header |
| unauthenticated route set (GET + POST, `require_session()` gating) | 19 GET + 1 POST | **unchanged** — `git diff 839489a..HEAD -- companion/app.py` touches ZERO `require_session()` call sites and the whole diff is 63 lines (a 204-vs-303 response-shape refactor, `_settings_saved_redirect()`, on already-gated routes) |
| new `_ROUTE`/`*_ROUTE` constants anywhere under `companion/` | — | **0**, confirmed by `git diff 839489a..HEAD -- companion/` |

*(A bare `grep -c '@keyframes'` returns **6** and a bare
`grep -c '@supports selector(:has(\*))'` returns **9** — both are prose in
comments quoting the at-rule, growing across the phase as later plans'
comments themselves referenced these pins; both are comment-stripped above
for that reason, and the bare counts are recorded here so the next reader
does not mistake either for a regression.)*

**Both standing refusals stay refused, and this phase reopened neither** —
proven above by grep, not merely asserted: the **overlay drawer** (three
recorded rejections plus locked decision D-10) and **sticky day headers**
(struck twice; every flight row already carries its own date).

**Final `EXPECTED_CHECK_COUNT` for every harness this phase moved, each
re-derived by running:**

| Harness | Pre-phase | Final | Passing here |
|---|---|---|---|
| `companion/test_browser_ux.py` | 81 | **88** | 88/88, 0 SKIP |
| `companion/test_companion_app.py` | 314 | 314 | 312/314 (the two WR-11) |
| `companion/test_config_page.py` | 259 | **263** | 263/263 |
| `companion/test_status_pages.py` | 305 | **306** | 305/306 (`anomaly_active()`) |
| `companion/test_i18n.py` | 24 | 24 | 24/24 |
| `companion/test_view_pages.py` | 164 | 164 | 164/164 |
| `companion/test_contrast_check.py` | 49 | 49 | 49/49 |

`ruff check .` — **All checks passed!**

**One intermittent, flagged by 27-08, checked here for recurrence rather than
waved away as already known.** 27-08's own SUMMARY recorded a `test_browser_
ux.py` check (`SkyPaneDirtyState` timing on the `quiet_hours_start` field)
failing once under 4-way parallel load and passing clean in four separate
serial/standalone runs both before and after that plan's own changes. **It
did NOT recur in this closing plan's own final run** — today's full-suite run
(`JOBS=4`) and today's separate standalone `test_browser_ux.py` run were both
clean at 88/88 with exactly the five named baseline failures and no sixth.
Confirmed absent, not merely assumed absent — this is new information (a
non-recurrence), not a re-statement of what 27-08 already knew.

### `deferred-items.md`

Created for this phase (`.planning/phases/27-companion-review-feedback-the-
defects-and-the-noise-the-deve/deferred-items.md`) — no earlier plan in this
phase had started one. Carries: the "règles par vol" view (explicitly out of
scope for the whole phase, per the ROADMAP's own entry — "the brief is too
vague to plan against and needs a conversation first"); the rule-add form's
colour grid, left unwrapped by 27-07 for the identical reason (recorded
together with the view it is deferred alongside, so the two decisions are
findable in one place); and `DIRTY_SECTION_ATTR` (`data-dirty-section`), left
standing in `config_page.py`'s markup by 27-04, unread by any script since its
reader was deleted with the dirty bar, still marking the same visual grouping
a sighted reader already sees.

### What this gate does NOT cover — the human sweep, named and not claimed

**This is the phase's real gate and it is the developer's, not this agent's.**
On a real phone at 360px and on a desktop, in both themes and both languages:

- **Auto-save's two words** — does "Sauvegarde…"/"Sauvegardé" arrive
  reassuringly or invisibly on a real screen, at real reading speed?

- **The dial's handles and arc**, following both a drag and a preset,
  including when the window's two ends are close together or genuinely
  overlapping.

- **The runway card without its map** — does the simplified card read as
  complete, or as missing something, on a real screen?

- **The shortened wake-interval and battery wording** — is 137/168 characters
  still enough explanation, or too terse now?

- **The one title form** — does Display's supersection structure read
  clearly now that CFG-65's investigation found nothing to convert, or does
  the developer's original impression persist even having seen the
  evidence above?

- **All three colour strips and their pagers**, each carousel's own
  disclosure now below the strip.

- **The Quiet hours link**, tapped from both the Home and the Display Frame
  strip.

- **Whether the disappearing duration during a drag** (the dial's caption,
  PROVISIONAL per CFG-62) is acceptable, or whether the C2 fallback
  (server-emitted per-unit templates) should replace it.

That review is the developer's. This gate reports what a machine can see;
it does not claim the rest.

## Phase 28 coverage ledger (companion review feedback round 2 — five more findings from the deployed app, investigated before planning)

Written at the phase's close by 28-09, walking all six items (five original
findings plus the mid-phase reversal they produced) against the ten
preceding SUMMARYs (28-01 through 28-05, 28-08, 28-10, 28-11) and against
the code on the finished tree — not against what the plans intended. It
exists so the developer can see in one place what shipped, what was
superseded and why, and which requirement was deliberately left unticked
because nothing was built for it, matching the discipline Phases 23, 24, 25
and 27 each held.

One of the six items is deliberately left UNTICKED (**CFG-74**) —
superseded before implementation, never built, and recorded as exactly
that rather than rounded up to "fixed" or down to "not met". A phase that
runs on "assert relationships, not just endpoints" (CFG-71's own standing
contract, inherited from Phase 27) cannot itself round a superseded
requirement up to make its own ledger look cleaner.

### Correction 1 — one typographic form for a settings-card title (CFG-72)

**Complete (28-04).** The developer's report — *"Ok mais visuellement les
titres sont toujours incohérents !"* — landed after 27-06's own
investigation had found "no structural defect" by inventorying markup
rather than rendering it. 28-04 rendered both settings pages and read
`getComputedStyle` instead: Device's three `.theme-status` cards
(Diagnostic LED, Wake interval, Notifications) were never wrapped in the
nested-supersection style Display's cards already use, so they rendered at
22px/regular/serif (the shared `.text-heading` default) while Display's
nested cards rendered at 16px/semibold/sans
(`companion/static/style.css:5703-5705`) — two unrelated typographic
registers for the same semantic element, depending only on which page you
were on. The fix wraps Device's four settings cards (the three above, plus
the Poll card) in the existing `theme-status--nested`/`.page-section--nested`
style under two new Device supersections plus a third one-card supersection
for Poll — **reusing `_nested_wrapper_html()` verbatim, zero CSS edited.**
`_a_settings_card_title_renders_identically_on_both_settings_pages()`
renders BOTH pages in one session, addresses every settings-card title by
STRUCTURAL POSITION (never a class name — the exact 27-06-shaped mistake
this check is written to avoid), reads the (font-size, font-weight,
font-family) triple on each, and asserts the combined set across both
pages has cardinality 1; the failure message names the offending page, the
offending title's text, and both triples. Supersection intro headings
(`.section-intro > h2`) are excluded structurally and deliberately — a
different, generically-worded tier, not an inconsistency this check should
assert away.

### Correction 2 — the quiet-hours dial's two bugs (CFG-73)

**Complete (28-02, 28-03).** The developer's second report —
*"Le curseur des heures calmes fonctionne mieux mais est toujours
bugué"* — named two genuinely distinct defects in the one control, and a
follow-up escalated a second one the first report had not separated out.

**Bug B (28-02), the handle collapsing to the dial's centre during a held
press.** Root-caused by live measurement, not by re-deriving the
angle/pointer math (which was already correct in every scenario tried):
`.quiet-dial__handle` is a real `<button>`, and the global
`button:active { transform: translateY(1px); }` rule
(`companion/static/style.css:2624-2626`, class-level specificity) beat the
handle's own single-class ring-positioning rule
(`companion/static/style.css:1519-1526`, the same specificity family, but
losing on source order) while pressed, animated visibly by the shared
`transition: transform .15s ease` (the base `button` rule) — measured live:
78px from the dial's centre (correct, on the ring) at press, collapsing to
14-16px (the centre) by 90-150ms, recovering to 78px roughly 200ms after
release. Fixed by excluding `.value-control__handle` from the generic
`:active` rule and dropping `transform` from the handle's own transition
list. `_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press()`
SAMPLES the handle's resolved distance from the dial's own centre >=10
times across a held press of >=400ms, never only before/after — mutation-
proven: an endpoint-only version of the identical check passes on the
broken code, which is exactly the shape of assertion that let this defect
ship in the first place. **A planning-time claim was found wrong during
execution, and corrected rather than silently worked around**: the
requirement's own text (and ROADMAP.md's Phase 28 entry) asserted the
wake-interval slider shares this defect via the same base class. Measured
live: `.value-control__handle` has exactly one consumer in the codebase
(the quiet-dial handles, `companion/pages/config_page.py:2980`); the
wake-interval slider is a native `<input type="range">` whose own
pre-existing CSS comment states it deliberately does not wear
`.value-control`, so `button:active` cannot reach it at all. No wake-side
edit was made or needed; the fix is scoped to the shared class, covering
any future `.value-control__handle` consumer by construction rather than
by enumeration.

**Bug A (28-03), the readout regressing to raw minutes with a permanently
blank duration.** `quiet_dial_readout_html()`'s own format (HH:MM plus a
computed duration) held at initial server-rendered load but never
recovered after any interaction — 27-02's own documented "known
limitation" surfacing exactly as "still buggy." Fixed by handing the
client the SAME translated wordings a ticker already uses (server-rendered
`#`-marked duration-bucket attributes), never a second HH:MM converter or a
second duration ladder written in JavaScript.
`_the_dial_caption_keeps_its_form_after_every_interaction_kind()` reads the
caption's own displayed text after EACH interaction kind — a drag, a
keyboard step, a typed field edit, a preset click — and asserts it matches
computed HH:MM plus duration byte-for-byte against the server-rendered
form, in both languages.

### Correction 3 — every carousel's preview follows the scroll (CFG-75)

**Complete (28-05).** The developer's fourth report —
*"Change pictures ne s'affiche pas quand je scroll ce qui n'est pas dingue
d'un point de vue UX"* — was confirmed as coded, by design: the carousel's
dots carried no position state at all, and the live preview `<img>` only
ever changed on an actual click or keyboard-select. A product decision
(AskUserQuestion, 2026-09-15, "Aperçu suit le scroll") built a genuinely
new PREVIEW state, distinct from SELECTION: while scrolling or swiping any
of the three carousel strips (departures, arrivals, calendar), the live
preview now follows whichever chip is geometrically centered, via a
per-strip IntersectionObserver-assisted tracker reusing the carousel's own
existing `applyPreviewSrc()` sink — no radio touched, nothing persisted
from scroll alone.
`_scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_selects_nothing()`
dispatches real scroll events across four real intermediate positions per
strip (never a jump to the end), in both UI themes, and asserts: no
radio's checked state moves during any of it; the final scrolled-to chip
is provably distinct from the already-selected theme; and a reload with
nothing clicked shows the SAVED theme, never the last scrolled-past one.
All three carousels are exercised, plus one cross-instance clause proving
arrivals' own scroll never reaches departures' preview or strip state —
27-07's `strip_id`-per-instance discipline, preserved rather than
reinvented.

### Correction 4 — the mobile nav toggle's icon matches what it opens (CFG-76)

**Complete (28-01).** The developer's fifth report and proposed fix —
*"Sur mobile le hamburger est perturbant car cela ressemble à la
navigation. Remplacer par un engrenage ?"* — was confirmed exactly as
described: `#site-nav-toggle` rendered `icon-hamburger` with
`aria-label="Account and preferences"`, but the panel it opens
(`_mobile_nav_html()`) holds zero page-navigation links (real navigation
moved to the bottom tab bar in 22-14). Fixed by appending a new,
23rd `ICON_IDS` member (`icon-gear`, its own `<symbol>` at the same visual
weight as `icon-power`/`icon-moon`) and changing `#site-nav-toggle`'s single
`icon_html(...)` argument — `NAV_TOGGLE_LABEL` and every other line of
`_mobile_nav_html()` are byte-identical (`git diff` confirms the only
changed line in that function is the icon id). Both hard-coded icon-sprite
member-count checks (`_icon_sprite_integrity()`,
`_page_shell_emits_sprite_once_no_inline_styles()`) retargeted from 22 to
23, mutation-tested; a new check proves the glyph, the translated EN/FR
label, and the panel's still-navigation-free contents all agree. No other
`ICON_IDS` entry collides with the new gear symbol (0 hits for
"gear"/"settings-icon"/⚙ app-wide before this plan).

### Correction 5 — the save-reliability requirement, superseded before it was ever built (CFG-74)

**Not ticked. Nothing was built for it.** This is the item that most needs
saying plainly rather than glossed, so: **none of CFG-74's four original
clauses — (a) scroll-independent save status, (b) a conditional retry
affordance, (c) the runway `form=` regression check, (d) fixing any
genuine defect found along the way — was built as CFG-74's own machinery.**
The two plans that would have built it, `28-06-PLAN.md` and
`28-07-PLAN.md`, never executed; both survive on disk with a superseding
header note (`28-06-PLAN.md.superseded`, `28-07-PLAN.md.superseded`)
rather than being deleted, per this project's standing convention against
erasing planning history.

**The timeline, because the reason matters more than the fact.** The
developer's third report — *"Quand je fais un changement de paramètre
(comme la piste) je ne vois pas le bouton enregistrer apparaître"* — was
first investigated as a single-control question and not reproduced in
Chromium. A follow-up escalated it completely: on a real iPhone in Safari,
nothing saved at all, for anything, with no error shown; the same held on
Mac Safari for every setting tested. A dedicated deep-dive (`dirty-state.js`
end to end, the toast's CSS, script load order, every Safari-incompatible-
API class checked) found no incompatibility, no syntax error, no CSS
collision — and the exact root cause could not be confirmed without a live,
tethered WebKit debugger, unavailable in this project's development
environment. The decision taken with the developer on 2026-09-15 was to
build resilience around the confirmed-severe, root-cause-unconfirmed
failure rather than guess at a fix. That is what CFG-74's four clauses
specified, and what 28-06/28-07 were written to build.

**Then the picture changed, before either plan ran.** With 28-01 through
28-04 shipped, the developer got hold of a Mac and captured the real
Safari Network tab for a settings save: `POST /settings` -> a genuine
**204**, every field present, and confirmed after reload that the value
genuinely persisted. The auto-save mechanism was never broken — it worked
correctly the whole time; the only real defect was that nothing ever
visibly confirmed it, exactly the class of problem CFG-74's own resilience
work was built to paper over without knowing the cause. Having seen this,
the developer rejected the auto-save MODEL itself, not merely its missing
feedback: *"Mais ce n'était pas le comportement d'enregistrement qu'on a
choisi. Je veux garder la pop up qui apparait et qui propose
d'enregistrer... le comportement d'avant."* Confirmed explicitly when asked
directly: *"Oui, avec les boutons Enregistrer/Annuler comme avant."*

**Why CFG-74 is superseded rather than failed.** The requirement's own
text names its own root cause in its very first sentence: "a regression
from Phase 27's removal of the manual save button." With that button
restored (CFG-77/CFG-78, Correction 6 below), the resilience machinery
this requirement specified — a bounded fetch-timeout, distinguished async
failure kinds, a conditional retry affordance — has no fetch left to wrap,
since the settings form goes back to a real native POST whose success or
failure is unambiguous by construction (a real page navigation, never an
async call that can fail silently). Building CFG-74's own machinery around
a mechanism the developer was about to reject outright would have been
work spent proving the wrong thing resilient. Clause (c) — the runway
`form=` regression check — is the one exception with its value carried
forward intact: CFG-78/28-09's own runway regression check proves exactly
that path, but against the restored bar's real POST, not against CFG-74's
own fetch-timeout framing, so it is recorded as CFG-78's evidence, not
this row's.

**Nothing here claims a Safari defect was found or fixed.** It worked; the
model was rejected. This is the sentence CFG-78's own wording requires
this ledger to say plainly, and it is said here without hedging.

### Correction 6 — the pre-Phase-27 save bar, restored (CFG-77, CFG-78, across 28-08, 28-10, 28-11 and 28-09)

**Both complete.** The restoration that replaced CFG-74's entire scope.
Real Enregistrer/Annuler buttons over a native form POST, restored from
this project's own history (`6dea46a` and its predecessors), at the
developer's twice-confirmed request. Every clause of both requirements'
own wording is walked below with its own named evidence — a check
function, a measured figure, or a file and mechanism — never a plan's
stated intention.

**CFG-77's clauses:**

- *The bar appears on a field change.* 28-08's restored `dirty-state.js`
  (`updateBar()`, driven by the document-level `change`/`input`
  delegation) and 28-10's retargeted
  `_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves()`.

- *It names the changed section(s), in document order, from the
  surviving `data-dirty-section` wrappers.* 28-10's
  `_the_dirty_count_arrives_and_moves_only_when_the_word_does()` (the
  control-phase/changed-text-gate clauses) **plus 28-11's Task 1**,
  `_section_naming_reflects_the_fields_actually_changed_in_document_order()`
  — the actual document-order-vs-click-order proof against real changed
  fields (Runway then Quiet hours, and the reverse), in both languages,
  built entirely from the bar's own `data-dirty-*` attributes rather than
  a hardcoded literal.

- *Enregistrer is a genuine native form submission, never a fetch.*
  28-08's own AST-level proof that the native submit
  (`STATIC_SAVE_FALLBACK_ATTR`) is emitted unconditionally, plus 28-10's
  retargeted checks waiting on a real `page.expect_navigation()` rather
  than a same-page DOM update.

- *Annuler restores every field via `form.reset()`, re-triggers the
  quiet-hours dial's repaint and the theme carousel's
  `window.SkyPaneLivePreview.refresh()`.* **28-11's Task 2**,
  `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom()`
  — the only place in the phase this is proven by reading the RESULTING
  DOM after 28-08's own deferred `setTimeout(fn, 0)` tick, never by
  spying on `refresh()`/`repaintAll()` being called. This check's own
  mutation testing produced a genuine corroboration of 28-08's written
  design argument, not merely a fresh finding: removing only
  `repaintAll()` from the deferred tick left the dial's start handle
  reading the DISCARDED edit's value (`300`, i.e. `05:00`) rather than
  the pre-edit original (`1335`, `22:15`) — proving `value-controls.js`'s
  document-level click listener does fire on the Cancel button's own
  click and does repaint from the STALE, pre-reset values, exactly as
  28-08's own comment states.

- *Annuler does not disarm the leave-guard permanently — a new edit
  re-arms it.* **28-11's Task 3**,
  `_the_leave_guard_re_arms_after_a_new_edit_following_cancel()` — **the
  one CFG-77 clause that had ZERO executable coverage anywhere in the
  phase until a plan review surfaced the gap.** A ledger that records
  how a gap was found is worth more than one that only records that it
  is closed: the check proves fresh load (disarmed) -> edit (armed) ->
  Annuler (disarmed) -> a NEW edit (RE-ARMED) -> a second Annuler
  (disarmed again, closing the symmetric "re-arms only once" hole),
  mutation-proven against exactly the defect a Cancel handler that sets
  `suppressGuard = true` once and never clears it reproduces.

- *The leave-guard is kept exactly where CFG-63's own carve-out put it.*
  28-10's retargeted
  `_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit()`.

**The no-JS-floor evidence, named precisely because it was nearly
missed.** 28-08's scripts-blocked criteria proves all FOUR facts together:
the bar renders VISIBLE by default (the polarity inversion — there is no
second fallback button any more, so the bar's own server-rendered visible
state IS the floor); the Save reaches disk via a real native POST with
scripts blocked; the Cancel is a genuinely working native
`<button type="reset">`, not a `type="button"` that would be scripted-
enhancement-only; and `[data-dirty-count]` renders EMPTY at rest, seeding
no claim. **A plan review caught two consequences before implementation,
and this is the phase's most load-bearing no-regression claim, worth
naming rather than compressing into one word:** (1) had Cancel shipped as
the old `type="button"` (which relied entirely on script because the old
bar was `hidden` by default), it would have been a fully visible, fully
INERT control for every scripts-blocked visitor now that the polarity is
inverted; (2) had `[data-dirty-count]` shipped seeded with
`DIRTY_BAR_INITIAL_TEXT`'s literal "Unsaved changes" text, it would have
been a permanently-announced false claim on a `role="status"` region for
every scripts-blocked visitor on every fresh load. The shipped design
avoids both: the native `type="reset"` restores every field with zero
script, and the count span's own empty seed means a scripts-blocked
visitor never has anything false announced to them.

**CFG-78's clauses:**

- *The already-existing, AST-provably-unconditional native submit becomes
  the bar's own visible Save — one element under two rendering
  conditions, never two implementations.* 28-08's
  `_the_bar_s_save_button_is_the_same_static_fallback_element_relocated()`
  (the static/string-level relationship proof: the one
  `STATIC_SAVE_FALLBACK_ATTR` occurrence's index sits strictly inside
  `.dirty-bar`'s own span) **plus 28-09's browser-level single-affordance
  audit**,
  `_exactly_one_submit_shaped_control_resolves_to_the_settings_form()` —
  resolving every submit-shaped control's own `.form` property in a live
  browser (never a count of `<button` occurrences, never a hand-
  maintained allow-list), on both `/display` and `/device`, in both
  languages, requiring exactly one whose form id is `settings-form` and
  that it carries `data-static-save-fallback` inside `[data-dirty-bar]`.
  Mutation-proven against a deliberately added second submit button
  inside the settings form, which the check caught and named by tuple
  (`tagName[type=submit] form='settings-form' text='MUTATION second
  save'`).

- *The runway radios' `form=`-attribute cross-tree wiring is proven under
  the restored bar.* 28-09's
  `_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end()`
  — closing the path CFG-74(c) named before the reversal, now against the
  real POST instead of the retired fetch: selecting the runway radio
  (rendered outside `<form id="settings-form">`) reveals the bar naming
  exactly its own Runway/Piste label, a real Enregistrer navigation
  writes `tracked_runway` to disk, and a reload shows the radio
  reflecting the saved value, in both languages. Mutation-proven against
  the exact B1 defect this path exists to guard (narrowing
  `dirty-state.js`'s document-level delegation to the form element
  reproduces the original bug class, and the check fails with a timeout
  waiting for the bar).

- *The closing gate re-derives every check count by running, names the
  sandbox baseline by NAME, and states which of CFG-74's four clauses
  were genuinely built.* See this plan's own gate section, immediately
  below.

**28-09's own gate, re-derived by RUNNING, not carried forward from any
earlier SUMMARY:**

| Harness | Pre-plan | Final | Passing here |
|---|---|---|---|
| `companion/test_browser_ux.py` | 94 | **96** | 96/96 |
| `companion/test_config_page.py` | 265 | **266** | 266/266 |
| `companion/test_companion_app.py` | 316 | 316 (unchanged, explicitly re-checked) | 314/316 (the 2 named WR-11 below) |
| `companion/test_status_pages.py` | 306 | 306 | 305/306 (`anomaly_active()` below) |
| `companion/test_i18n.py` | 24 | 24 | 24/24 |
| `companion/test_contrast_check.py` | 49 | 49 | 49/49 |
| `companion/test_view_pages.py` | 164 | 164 | 164/164 |

`PYTHON=.../python3 bash scripts/run-all-tests.sh` (JOBS=4) exit status:
**1 (FAIL)** — three harnesses named, exactly the same class the phase's
own plans have recorded from 28-01 onward: `server/test_manual_
resolutions.py`, `companion/test_companion_app.py`,
`companion/test_status_pages.py`. **The sandbox baseline, RE-DERIVED by
running today (2026-09-19) rather than carried forward from 28-04's own
SUMMARY, is still exactly the five named failures 28-04 first recorded on
2026-09-15** — unchanged in count and unchanged in membership across five
intervening plans that all touched these same suites:

1. `companion/test_companion_app.py` — *"expected the manual_save_failed
   flash key when add_entry() fails to write, got
   '/airlines?resolve=FLD&flash=manual_resolved'"* (WR-11).

2. `companion/test_companion_app.py` — *"expected the manual_delete_failed
   flash key when delete_entry() fails to write, got '/airlines'"*
   (WR-11).

3. `server/test_manual_resolutions.py` — *"expected ADD_FAILED for an
   uncreatable state dir, got 'ok'"* (WR-11).

4. `server/test_manual_resolutions.py` — *"expected False (never raises)
   when the state dir is read-only, got True"* (WR-11).

5. `companion/test_status_pages.py` — *"expected False for a non-existent
   state_dir path"* (`anomaly_active()`).

All five are a root-owned-sandbox artifact (permission enforcement on a
directory made "read-only" is bypassed when the test process itself owns
root, so the read-only-simulation setup this suite relies on cannot
reproduce the condition it means to test) — none is attributable to
28-08, 28-10, 28-11 or this plan's own Task 1, and none is widened into or
absorbed by this ledger; `ruff check .` is clean across the whole
repository.

**Which of CFG-74's four clauses were genuinely built: none.** Clause (c)
carries forward as CFG-78's own runway regression check, proven above —
but that is CFG-78's evidence, earned by this restoration's own design,
not CFG-74's machinery surviving in any form. Clauses (a), (b) and (d)
have no successor anywhere in this phase, because the mechanism they would
have wrapped (a fetch that can fail silently) no longer exists.

RER-01/02/03 and DEVICE-01/02 moved to v2 Requirements (2026-08-11) — no longer mapped to a v1 phase. CFG-01/03/04/05 (and now CFG-06..11) moved the other direction: promoted from v2 Requirements to Phase 6 (2026-08-27, briefly Phase 7 for a few minutes before the Phase 6/7 renumbering). CFG-02 was promoted alongside them but moved back to v2 during `/gsd-discuss-phase 6` (2026-08-27) — still nothing to switch to. DEVICE-06 stays in v2 Requirements, not promoted — shipped from there by quick task 260924-u7n (2026-09-24) and verified on glass 2026-09-25.

**Coverage:**

- v1 requirements: 17 total
- Mapped to phases: 17 (Phase 1: 1, Phase 2: 3, Phase 5: 2, Phase 6: 11)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-04*
*Last updated: 2026-08-04 after roadmap creation*
