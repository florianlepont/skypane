# Phase 10: Scheduled quiet hours - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A configurable quiet-hours window (a curfew) that pauses the frame's wake/poll/display
cycle, set via the companion web interface, honored by the server on the device's
regular poll — promoted from `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md`
at the developer's direct request (2026-09-02/03), ahead of the seed's own original
trigger (Phase 5's real battery-discharge verdict, DEVICE-05, still in progress).

This phase covers: the quiet-hours config (enabled flag + one daily recurring
start/end window), the companion web-interface fields to set it, the server-side
mechanism that makes the device sleep through the window, and the dedicated
"quiet hours" screen shown once at window entry. It does not cover: a way to make an
edit apply faster than the device's next wake (explicitly rejected, see D-04), a
symmetric "waking up" screen at window exit (explicitly rejected, see D-07), or
day-specific/multiple windows (explicitly rejected, see D-05). It does not touch
Phase 11 (web-configurable wake interval) except that both phases modify the same
`stub-server/byos_server.py` `/display` response fields — see Integration Points below.

</domain>

<decisions>
## Implementation Decisions

### Pause mechanism
- **D-01:** Quiet hours pause the cycle by **extending `sleep_s`**, not by keeping the
  normal wake cadence and skipping the display refresh (the seed's original "option b").
  When a poll lands inside the configured window, the server computes a `sleep_s` that
  spans past the window's end instead of the normal interval — the device deep-sleeps
  through the entire window and does not wake, connect to Wi-Fi, or poll at all during
  it. This is the bigger battery win (skips the wake+Wi-Fi+HTTPS round-trip entirely,
  not just the e-ink refresh).
- **Correction of the seed's own premise, surfaced live during this discussion:**
  SEED-001 assumed this option needed "the firmware to compute an extended sleep_s...
  bigger change to state_machine.c/app_main.c's sleep-duration logic." That's wrong —
  `sleep_s` is already a fully server-controlled, per-response value
  (`stub-server/byos_server.py`'s `"sleep_s": self.args.sleep` in the `/display`
  handler; the firmware just deep-sleeps for whatever number the server sends, see
  `firmware/main/state_machine.c` line ~51 and `app_main.c` line ~172). Extending it
  during quiet hours needs **zero firmware changes** — it's the same "local
  modification" shape already used for `led_enabled` (`read_led_enabled()` in
  `byos_server.py`), just computed against the quiet-hours window instead of a fixed
  CLI value. The device does not need its own clock/time awareness for this — only the
  server's wall-clock matters, since `sleep_s` is a plain duration in seconds.

### Edit responsiveness
- **D-02:** A quiet-hours edit (change or disable) made on the companion page while the
  device is in its extended sleep is **not** picked up until the device's next natural
  wake — which, because of D-01, could now be hours away instead of the usual few
  minutes. This is accepted as-is, consistent with Phase 6's existing "config applies
  on next scheduled poll" rule (`06-CONTEXT.md` D-06/D-07). No new mechanism (e.g.
  reusing/extending the manual poll-trigger CFG-07) is in scope for this phase.

### Window shape
- **D-03:** **One daily recurring window** (a single start/end time applied every day),
  not day-specific/per-weekday windows. Matches the seed's simpler option and the
  typical curfew use case.
- **D-04:** **Separate enabled/disabled flag**, independent of the stored start/end
  times — same pattern as `led_enabled` (an explicit boolean, not "empty fields = off").
  Lets the developer temporarily disable a configured curfew (e.g. an exceptional late
  night) without losing the saved window, and re-enable it later without re-entering
  times.
- **Research note (not user-decided, flag for the phase researcher):** the window is
  inherently a **local wall-clock** concept (e.g. "23:00–07:00" Europe/Paris), but the
  codebase currently only reasons in UTC (`server/history_db.py`'s `datetime.now(timezone.utc)`
  is the only existing timestamp convention found). The server-side `sleep_s`
  computation (D-01) must account for Europe/Paris's DST shifts to stay correct
  year-round — Python's stdlib `zoneinfo` (`ZoneInfo("Europe/Paris")`, no new
  dependency, available since Python 3.9) is the natural fit given `server/requirements.txt`
  already stays minimal (Pillow + requests only, per `06-CONTEXT.md`). Left to
  research/planning to confirm and implement — not discussed live with the developer
  beyond flagging that it exists.

### Panel state at window entry
- **D-05:** A **dedicated "quiet hours" screen** is drawn once, at the poll that first
  detects the window has started — not a frozen last-content screen (the seed's other
  option). This is a deliberate, confirmed exception to the project's "no on-screen
  status text/indicators" convention (`PROJECT.md`'s Out of Scope table), in the same
  class as the low-battery icon's own confirmed exception
  (`05-CONTEXT.md` D-04's "a deliberate, confirmed exception to the project's
  established 'ambient art, not gadget' text-only visual language").
- **D-06:** The screen's copy is **English**, matching every other piece of panel text
  (`DEPARTING`/`ARRIVING` state labels, `ORY · RWY 3` tag) — not French, even though
  this discussion happened in French and the developer's own working example was in
  French ("Couvre-feu / Bonne nuit... Retour à..."). Wording direction: something in
  the shape of **"QUIET HOURS" / "Back at HH:MM"** — exact copy/typography/layout left
  to planning, following the same real-preview-before-committing discipline
  `05-CONTEXT.md` used for the battery icon.
- **D-07:** **No symmetric "waking up" screen** at window exit. The first normal poll
  after the device wakes renders the real, live departure/arrival board directly, same
  as any other poll — no intermediate "good morning" transition state. Consistent with
  the project's "no unnecessary refresh" ethos: no extra render exists just to mark the
  transition.

### Claude's Discretion
- Exact config field names in `device_config.py`'s registry (e.g. `quiet_hours_enabled`,
  `quiet_hours_start`, `quiet_hours_end`) — follow the existing `normalise_*()` +
  `load_device_config()`/`save_device_config()` pattern already used for
  `theme`/`tracked_runway`/`led_enabled`.
- Exact companion-page form layout for the two time fields + enabled checkbox — mirror
  the existing Settings page's fieldset pattern (`companion/pages/config_page.py`).
- Exact pixel layout/typography/color of the "QUIET HOURS / Back at HH:MM" screen —
  D-06 locks the copy direction and language, not the final visual design; validate
  against a real preview render before treating it as final (same discipline
  `05-CONTEXT.md`'s battery icon used).
- What happens if a single poll's normal `sleep_s` would already carry the device past
  the window on its own (e.g. a long wake interval overlapping a short window) — an
  edge case, not raised by the developer; a reasonable "still compute the
  window-spanning value, never make sleep_s shorter than it would otherwise be" rule
  is expected.
- Hysteresis/off-by-one handling at the exact window boundary (e.g. a poll landing
  within a few seconds of the configured end time) — not raised; standard defensive
  handling expected, no user-facing behavior implication.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase's own seed
- `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md` — the original seed
  this phase was promoted from; note its "option a needs bigger firmware changes"
  premise is corrected by this CONTEXT.md's pause-mechanism decision above

### Server-side mechanism (D-01)
- `stub-server/byos_server.py` — the `/display` handler's `"sleep_s": self.args.sleep`
  line (~254) is where the quiet-hours-aware computation replaces the static CLI value;
  `read_led_enabled()` (~85) is the exact "local modification" pattern to follow for
  reading `device_config.json`'s new quiet-hours fields
- `firmware/main/state_machine.c` (~line 51) and `firmware/main/app_main.c` (~line 172)
  — confirm `sleep_s` is consumed as-is from the server response with no firmware-side
  interpretation, ceiling, or clock awareness needed
- `firmware/main/state_machine.c` (~line 68) — the existing hash-skip logic
  (`FP_POLL_OK_UNCHANGED`), relevant context for why this project already has a
  "don't refresh needlessly" mechanism, even though this phase's chosen mechanism
  (D-01) doesn't rely on it

### Config registry pattern (D-03/D-04, Claude's Discretion)
- `server/device_config.py` — `THEMES`/`RUNWAYS` registries, `normalise_theme_id()`,
  `normalise_runway_id()`, `normalise_led_enabled()`, `load_device_config()`,
  `save_device_config()` (lines ~310-425) — the exact pattern new quiet-hours fields
  must follow, including the "never raise, degrade to a safe default" contract
- `companion/pages/config_page.py` — the existing Settings-page fieldset pattern
  (theme/runway/LED sections) a new quiet-hours fieldset should mirror

### Prior phase precedent (D-02, D-05, D-06)
- `.planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-CONTEXT.md`
  — D-06/D-07 (config applies on device's next scheduled poll, with an explicit
  "applies next wake" confirmation message — D-02 follows this rule); D-01/D-02
  (single shared password gates the whole site, including this new fieldset)
- `.planning/phases/05-low-battery-indicator/05-CONTEXT.md` — D-04 (the low-battery
  icon's own confirmed exception to the "no on-screen status text/indicators" rule —
  direct precedent for D-05/D-06's quiet-hours screen); the "real preview render
  before committing to visual decisions" discipline this phase's screen should reuse
- `.planning/PROJECT.md` — Out of Scope table ("Status LEDs, on-device settings/menu
  UI... anti-features that would make the frame read as a gadget rather than ambient
  art") and ("Freshness timestamp / graceful stale-offline handling on the display —
  explicitly deferred") — the two existing exclusions D-05/D-06 deliberately carve an
  exception into, same as the battery icon did

### Project planning docs
- `.planning/ROADMAP.md` — Phase 10 section
- `.planning/REQUIREMENTS.md` — no requirement ID mapping expected; this is an
  unmapped backlog phase, matching every prior `06.6.x` decimal phase's own precedent

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/device_config.py`'s registry pattern (`normalise_*()` + load/save with
  safe-default degradation) — direct template for the new quiet-hours fields
- `stub-server/byos_server.py`'s `read_led_enabled()` — direct template for a
  `read_quiet_hours()`-equivalent best-effort config read
- `05-CONTEXT.md`'s battery-icon precedent — direct template for how to design,
  preview, and lock a new panel visual element that's a deliberate exception to the
  "no status text" rule

### Established Patterns
- "Config changes apply on the device's next scheduled poll" (`06-CONTEXT.md` D-06/D-07)
  — governs D-02 directly
- "An element exists visually only when it has real information to show"
  (`03-CONTEXT.md` D-25, reused by `05-CONTEXT.md` D-06 for the battery icon) — the
  quiet-hours screen follows the same conditional-rendering discipline: it only ever
  appears during the one poll that enters the window
- `byos_server.py`'s "local modification" discipline (tracked in `stub-server/VENDOR.md`)
  — every prior deviation from the vendored reference server has been a small,
  documented, best-effort-degrading read of `device_config.json`; the quiet-hours
  `sleep_s` computation should follow the same shape, not a structural rewrite

### Integration Points
- `stub-server/byos_server.py`'s `/display` handler — where D-01's `sleep_s`
  computation and D-05's "serve the quiet screen's image this one poll" logic both
  hook in. **Shared touchpoint with Phase 11** (web-configurable wake interval, which
  also changes how `sleep_s` is computed) — whichever phase executes second should
  re-read the other's SUMMARY before assuming this handler's structure, same mutual-
  awareness discipline already used between e.g. 06.3/06.4/06.5
- `server/plane/render.py` — wherever the active-canvas builder composes the panel;
  the quiet-hours screen is a new, distinct render path (not a variant of the normal
  departure/arrival composition), most analogous to the Empty-state render already
  handled there
- `companion/pages/config_page.py` — the Settings page's existing fieldset-rendering
  and form-handling functions, where the new quiet-hours section/fields attach

</code_context>

<specifics>
## Specific Ideas

- The developer's own working example for the quiet screen's message was French
  ("Couvre-feu / Bonne nuit... Retour à...") — the *shape* of that message (a clear
  "we're in quiet hours" label plus a return time) is what's locked; D-06 translates it
  to English for panel-language consistency, not a rejection of the idea itself.
- The pause-mechanism decision (D-01) was reached only after a live correction of the
  seed's own assumption (that extending sleep needed firmware changes) — worth noting
  for future seed-enrichment sessions that a seed's "Behavior decision" bullets are a
  starting hypothesis, not verified fact, until checked against the actual code.

</specifics>

<deferred>
## Deferred Ideas

- **A faster way to apply a quiet-hours edit** (e.g. extending the manual poll-trigger
  CFG-07, or capping the sleep extension) — considered and explicitly rejected for this
  phase (D-02). Revisit only if the "hours-long edit lag" turns out to be a real
  annoyance in practice.
- **Day-specific/multiple quiet-hours windows** — considered and explicitly rejected
  (D-03) in favor of one daily recurring window. `SEED-001`'s own text already
  flagged this as a possible config shape; the developer chose the simpler one.
- **A symmetric "waking up" screen at window exit** — considered and explicitly
  rejected (D-07) in favor of a silent transition straight back to the live board.

### Reviewed Todos (not folded)
None — no pending todos matched this phase (`todo.match-phase 10` returned zero
matches).

</deferred>

---

*Phase: 10-scheduled-quiet-hours*
*Context gathered: 2026-09-03*
