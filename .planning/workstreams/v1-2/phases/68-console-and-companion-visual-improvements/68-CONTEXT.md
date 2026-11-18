# Phase 68: Console and Companion Visual Improvements - Context

**Gathered:** 2026-11-16
**Status:** Ready for planning (list closed by the owner on 2026-11-18: 13 starting items, walk-through remarks R01-R36 and two route-source items; the owner's walk-through may add more)

<domain>
## Phase Boundary

Visual improvements to the administrator console and the companion pages for users, made in the existing design system (`sketch-findings-skypane`), so that Phase 66 (security audit) and Phase 67 (code cleanup) work on the final code. Requirement CON-01.

Only items on the owner's list are done. Nothing is added by Claude. No behaviour change beyond the list; the route x role x owner matrix is unchanged.

Not in this phase: photo mode screens, getting-started wizard, Wi-Fi setup (v1.3, v1.4); new features; Phases 66 and 67.

</domain>

<decisions>
## Implementation Decisions

### Scope and size
- **D-01:** Both the administrator console and the companion pages for users are in scope (owner, 2026-11-16).
- **D-02:** No cap on the list size (owner, 2026-11-16); the list is closed on 2026-11-18 (D-20). Claude's recommendation was a cap of 10; the owner chose none. The list still only grows by the owner's own remarks, each recorded with a screenshot. Phase 66 waits for this phase, so the owner closes the list explicitly before planning of execution waves is final.

### Starting list (all 12 selected by the owner, 2026-11-16)
High value:
- **D-03:** Home page: apply the approved mockup `68-HOME-MOCKUP.html` (online, sleeping, offline states).
- **D-04:** Fleet page: a retired frame is listed while the owner views another frame; make it clear which frame the page is about.
- **D-05:** Flight history: the search field drops under the title at some narrow widths; fix the header layout.
- **D-06:** "Back to Fleet" from a frame page must return to that frame, not the first one.

Medium value:
- **D-07:** Theme page: switching tab reloads all frame previews. Find whether it is a full navigation or changing preview URLs (previews carry a 5-minute cache in `companion/preview_images.py`) and fix.
- **D-08:** Naming: "Flights" (tab) versus "Flight history" (page), W6-08. Note: the French tab label "Compagnies" became "Airlines" on main (PR #453); the new label stays as it is unless the owner says otherwise. Naming choice goes through the owner, in English and French.
- **D-09:** More sheet width on a tablet (V6-10).
- **D-10:** Yellow Full/Soft-stripe contrast (1.12) on the panel; needs a real-device check.

- **D-15:** Airlines page: show the airlines known by name only (no artwork) as read-only rows, with the option to add artwork later. Raised 2026-11-17 after Phase 65; the owner decided to handle it in this phase. It touches companion files owned by Phase 64: say so before touching them. Mockup first. Details in `68-CANDIDATE-ITEMS.md`.

Low value:
- **D-11:** More sheet grab handle (A6-09).
- **D-12:** 44 px touch target for the quiet-hours link (V6-07).
- **D-13:** Tapping the active tab (W6-09).
- **D-14:** Hand-built `banner__pill` markup on a few pages: use the catalogue component.

### Walk-through remarks (owner, 2026-11-18)
- **D-20:** All remarks R01 to R35 of `68-WALKTHROUGH.md` are in the list (owner: "on fait tout"), including the ones marked "behaviour, outside list" (R02, R23, R26, R28, R29 filter, R30, R32). The owner's list defines the phase: those behaviour changes are asked for by the list, so they are not scope creep. They still need the access rules of Phases 54, 55 and 60, the golden hashes and `test_phase47_freeze.py` to stay green, and each one a test of the new behaviour.
- **D-21:** R35 (owner, administrator on another person's frame): a strong, unmissable marker (for example a top banner) on the personal view of a frame that is not the administrator's own. A marker exists today, too discreet. Mockup first.
- **D-22:** R26 includes a workflow question (how a new invited user signs in the first time without a password): research must establish how invitation and sign-in work today (Auth0) and propose options to the owner before any change. Other open points for the planner: the word "Marchand" in R29 (unclear, ask the owner), R10 (is the More sheet blur different in Safari: check), R34 label choice ("Mon compagnon" or "Mes cadres").
- **D-23:** Items R12 and R15 are the same as D-06 and D-04; R01-R34 supersede the ordering by value of the starting list: value order is decided at planning, the owner picks mockups one by one.

- **D-24:** R36 (owner, 2026-11-18): a re-activated retired frame keeps its retired screen until its next wake, up to 24 h (`RETIRED_SLEEP_S = 86400` s in `server/pairing_code.py`, used in `stub-server/byos_server.py::_pending_panel`); the server cannot wake a sleeping frame. Owner's decision: keep the 24 h wake interval (no battery or cadence change) and explain it clearly: a message at re-activation and on the pairing page saying when the frame will show its code and how to wake it by hand (reset button or power cycle: the planner must confirm the exact gesture per hardware type from `hardware/` docs). No change to `server/pairing_code.py` timings.
- **D-25:** R36 also covers the frame's own retired screen (owner, 2026-11-18): it must say that pressing the Reset button restarts the device so it can be paired again (wording short, English and French per the existing retired-screen convention). Owner confirmed on 2026-11-18 that every frame has a Reset button, known and used for a long time: the gesture is "press Reset", no longer an open question (the `hardware/` notes that say otherwise are stale or about an earlier kit). Only the button's place or label per hardware type is left to the owner's mockup review. It is rendered by `pairing_image.render_retired_image` and cached per frame as `retired.bin` (`stub-server/byos_server.py`): the planner must decide how already-retired frames pick up the new text (cache invalidation) and check which golden hashes or baselines cover this image. The retired screen of the live frame protocol and `test_phase47_freeze.py` must stay green. Mockup of the screen first, rendered for both hardware types, owner approves.

- **D-26:** Route sources "comparison" card (owner request of 2026-11-18, `68-CANDIDATE-ITEMS.md`): per aircraft, whether adsbdb and VRS give the same route, only one answers, or they differ. Needs the server to record which directory answered and the other directory's answer (a second request per new callsign): the planner must size the server and history-database change and offer the owner a choice before building. Mockup first.
- **D-27:** Route directories status (same source): reachable or not, time of the last answer, share of failed lookups and of lookups that found a route; needs new counters in the history database written by the poll cycle (a failed transient lookup is not recorded today). Both D-26 and D-27 touch the Health page, server history writes and companion files owned by Phase 64. Included because the owner asked for them; sizing and the exact scope are confirmed with the owner at planning. Mockup first.

### Owner decisions after the research (2026-11-18)
- **D-28:** R26 first sign-in: option B, an automatic invitation through the Auth0 Management API (a password-change ticket link), as in `SEED-012`. This adds a second secret and a security surface before Phase 66: the plan must keep the secret out of the repository and logs (environment file and systemd unit as for the existing secrets), limit the Management API scope to creating users and password-change tickets, keep the local invite as the access gate (an Auth0 account alone grants nothing), and record the threat model; Phase 66 audits it. The copy control becomes the real invitation link/message.
- **D-29:** R32: delete the Locations console routes (`POST /locations/add`, `/{id}/edit`, `/{id}/delete`) and their page, module, strings and tests; keep the `locations` table. The route table and access matrix change only by this removal; success criterion 5 reads "unchanged except the owner-requested removal".
- **D-30:** R34: the console bar label becomes "Mes cadres" in French and "My frames" in English.
- **D-31:** D-26 and D-27 (route sources) stay in the phase, but sized first: the plan has a sizing checkpoint (server and history-database cost, extra request per new callsign) and the owner decides before the build, with a mockup.
- **D-32:** Still to settle with the owner at the mockup stage: D-08 naming (EN and FR), the word "Marchand" in R29, the policy wording for R30, the frame list design for R13/R15, and whether R16 also retires the older standalone `/update` markup.

### Process
- **D-16:** Owner-guided page-by-page walk-through of the deployed console and companion (administrator and user views) still to be done, with a screenshot per remark. New remarks are added to the list only on the owner's say.
- **D-17:** Mockup approved by the owner before code for every visual change (as done for the active-mode card). The Home mockup is already approved. Any new pattern is added to `sketch-findings-skypane`.
- **D-18:** English and French both work, phone width works, browser tests cover each visual change (behaviour-over-source), accessibility checks keep passing.
- **D-19:** Owner validates on the deployed companion in English and French. Draft PRs only; production deploys are approved by the owner, never by Claude.

### Claude's Discretion
- Order of execution of the items and grouping into plans, by value then by shared files.
- Technical way to fix D-06 and D-07 (investigation first).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and requirement
- `.planning/workstreams/v1-2/ROADMAP.md` section "Phase 68"
- `.planning/workstreams/v1-2/REQUIREMENTS.md` CON-01
- `.planning/workstreams/v1-2/phases/68-console-and-companion-visual-improvements/68-CANDIDATE-ITEMS.md` (D-15)
- `.planning/seeds/SEED-020-console-visual-improvements.md` (items noted during the Phase 64 walk-through; the walk-through record calls it SEED-019 by mistake)

### Sources of the list
- `.planning/workstreams/v1-2/phases/64-second-hardware-in-production-build-release-deploy-and-parit/64-WALKTHROUGH.md` (remarks 4, 5, 6 and the retired-frame remark)
- `.planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-OWNER-VALIDATION.md` ("Left open on purpose", Round 31)
- `.planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-HANDOFF.md` (open items, "Not planned")

### Design
- `.claude/skills/sketch-findings-skypane/SKILL.md` and `references/component-catalogue.md`
- `.planning/workstreams/v1-2/phases/68-console-and-companion-visual-improvements/68-HOME-MOCKUP.html` (approved)

### Must not break
- Golden hashes of the legacy render; `stub-server/test_phase47_freeze.py`; access rules of Phases 54, 55, 60.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `companion/` pages, `companion/i18n_fr/` for French strings, shared app-server fixtures in `companion/conftest.py`.

### Established Patterns
- Behaviour-over-source tests enforced by `companion/test_suite_guards.py`; `companion/app.py` <= 1500 lines, JS files <= 1500 lines.

### Integration Points
- Phase 64 is changing companion files and Phase 65 detection: say so before touching a companion file Phase 64 changes.

</code_context>

<specifics>
## Specific Ideas

Owner's short answers in French, written artefacts in English.

</specifics>

<deferred>
## Deferred Ideas

- Real-frame check of the landscape hold caption legibility (not a companion item; Phase 64/65).
- Items set aside in Phase 61 and not selected: A5-15, A5-16, A5-20, A5-21, W5-12, W5-13, W5-17, W5-22, X13, P5-*, A6-11 (page-change frame drops under CPU throttle); not-planned items (canvas map markers, duplicated airport JSON, Airline editor weight, content-visibility).

</deferred>
