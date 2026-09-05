# Phase 12: Remote display on/off toggle - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The operator can turn the frame dark on demand from the companion Settings page, and bring it back, without touching hardware — the manual, immediate sibling of Phase 10's scheduled quiet hours. Quiet hours covers "dark every night between 23:00 and 07:00"; this covers "leaving for a week", "guest sleeping in the room", or simply not wanting the frame lit today.

Promoted from `.planning/seeds/SEED-004-remote-eink-display-power-toggle.md`.

</domain>

<decisions>
## Implementation Decisions

### Off-state device behaviour — the phase's central decision

- **D-01:** **"Off" means: check in on a fixed 300s cadence, skip the render.** While the display is off the device does **not** use its configured `wake_interval_s` — the served `sleep_s` is pinned to **300 seconds**, and the server produces no new flight panel. There is no window arithmetic and no open-ended bound: a single constant.

  *Why fixed rather than "keep the normal cadence" (developer's refinement, 2026-09-05).* Decoupling the off-state cadence from `wake_interval_s` is better on both axes at once, which is why it replaced the original simpler wording:
  - When `wake_interval_s` is short (its floor is 60s), 300s cuts the wake count ~5× during an off period — a real saving that "keep the normal cadence" would not have delivered.
  - When `wake_interval_s` is long (its ceiling is 3600s), 300s makes switching back on *faster*, not slower — a predictable "back within 5 minutes" instead of "up to an hour".

  300s sits inside `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` (60-3600), so this needs none of the ceiling-exceeding latitude `quiet_hours_sleep_s()` was granted.

  *Rationale, and the reframing that produced it.* The phase was originally scoped around a "bounded sleep" design, on the reasoning that `quiet_hours_sleep_s()`'s `max(base_sleep_s, remaining)` cannot be reused (it derives `remaining` from a window end time, and a manual toggle has no end time) and that an open-ended off state therefore needs its own bound. The developer challenged the framing directly — *"pas possible de juste faire ON/OFF ? on peut modifier le firmware si besoin"* — which surfaced two things:

  1. **The periodic wake is not a firmware limitation and cannot be removed by changing the firmware.** The device is poll-only and accepts no inbound connections (PROJECT.md: *"The device never accepts incoming connections — poll-only, no open ports"*), and it deep-sleeps between cycles. The server therefore cannot tell it to wake; the device must wake and ask. With no external wake source, the only lever is timer length — and the firmware already permits up to 86400s (`FP_MIN_REFRESH_SPACING_S`, `range 30 86400`), so nothing needed unlocking there.
  2. **But the trade-off it implied is much weaker than assumed.** On e-ink the panel refresh is typically the dominant per-cycle energy cost, and an off device does not refresh. So "normal cadence, no render" plausibly captures most of the available saving *while staying responsive* — collapsing the battery-versus-latency tension the phase was built around.

  **This is an explicitly un-measured assumption.** The real energy split is unknown because `DEVICE-05` (the multi-day discharge run) has never been executed — it remains the single open item on the v1 roadmap, and SEED-004's own trigger condition named that verdict. The developer chose to proceed on the simple design now rather than wait. See `<deferred>` for the refinement path if the assumption turns out wrong.

- **D-02:** **Turning the display back on takes effect within 300 seconds** — one off-state check-in. Predictable and independent of `wake_interval_s`, by construction of D-01. This latency is accepted, not a defect to design around, and the Settings UI should not imply the change is instantaneous; "within about 5 minutes" is an honest thing to tell the operator.

### Off-state panel appearance

- **D-03:** **A dedicated, sober off screen** — the same shape as Phase 10's quiet-hours state (`_build_quiet_hours_canvas()`), but **without any return-time promise**, since a manual toggle has no "Back at HH:MM" it can honestly make. A short heading plus one explanatory line indicating the frame was switched off from the interface.

  Rejected: **a blank field** — "off looks off" and suits the ambient object, but it is indistinguishable from a dead device or an outage, and the project already ships a source-fault icon (CFG-05) whose meaning that ambiguity would erode. Also rejected: **a blank field with a discreet corner mark** — a reasonable compromise, but it invents a new composition that would need its own on-glass validation for no decisive gain over D-03.

- **D-04:** Copy is **locked-English, defined once as module constants**, mirroring `QUIET_HOURS_HEADING_TEXT` / `QUIET_HOURS_BODY_TEMPLATE`. Exact wording is Claude's discretion (see below), but it must not promise a return time and must not read as an error state.

### Precedence against quiet hours

- **D-05 (derived, not user-stated — planner may revisit with reasoning):** **Precedence has two axes, and they resolve differently. Do not collapse them into one rule.**

  - **What the panel shows: the display toggle wins.** It is the explicit manual instruction; quiet hours is a standing schedule. The off screen (D-03) is what renders whenever the toggle is off, regardless of any window.
  - **How long the device sleeps: the longest value wins** — `max(300, quiet_hours_remaining)`, extending the existing `max(base_sleep_s, remaining)` idiom rather than replacing it.

  *Why the sleep axis must not follow the display axis.* A naive "off wins, always" would pin `sleep_s` to D-01's 300s even inside a quiet-hours window — making the device wake **more** often with the display off than quiet hours alone would have, which inverts the point of both features. Taking the max costs nothing in return: during a quiet window the panel stays dark either way, so a switch-back-on at 02:00 has no visible effect until the window ends at 07:00 whether the device checked in twelve times overnight or slept straight through. The operator sees the same thing; only the battery differs.

- **D-06 (derived):** **The display-off gate is evaluated first**, before the quiet-hours gate, and like it must sit **before** `detect.load_geofence()` / `detect.poll_current_aircraft()` in `run_once()`. This placement is load-bearing, not stylistic: `10-RESEARCH.md`'s Pitfall 4 records that the obvious-looking insertion point sits *after* detection has run, which would keep querying the free-tier ADS-B aggregators every cycle throughout an off period and discard every result. The same reasoning applies here with more force, since an off period can last indefinitely.

- **D-07 (derived):** **Moving between two hold states must not trigger an e-ink refresh.** If a quiet-hours window ends while the toggle is still off, the panel stays as it is rather than repainting from the quiet screen to the off screen — a refresh costs energy and produces a visible flash for no informational gain. Concretely: the latch pattern must distinguish "entering a hold state" (render once) from "already holding" (do nothing), across *both* mechanisms rather than per-mechanism. The existing `poll_state["quiet_hours_active"]` latch is the model but is single-purpose; generalising it is planning work.

### Config field

- **D-08:** A `display_enabled` boolean in `server/device_config.py`'s registry, following `normalise_led_enabled()`'s never-raising pattern exactly.

- **D-09:** **Defaults to `True` (display on).** Follows the `DEFAULT_LED_ENABLED` / `DEFAULT_QUIET_HOURS_ENABLED` precedent: an explicit boolean, never "empty field means off", so nothing changes for an installation already in service until someone opts in.

### Claude's Discretion

- Exact off-screen copy, within D-04's constraints (no return-time promise, must not read as an error).
- The Settings toggle's label and helper text, within the established `settings-checkbox` pattern.
- How the D-07 hold-state generalisation is factored — whether the existing `quiet_hours_active` latch is widened or a sibling latch is added alongside it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The phase this one is modelled on
- `.planning/phases/10-scheduled-quiet-hours/10-CONTEXT.md` — D-01/D-04/D-05/D-07, the decisions behind the gate and the render state this phase reuses
- `.planning/phases/10-scheduled-quiet-hours/10-RESEARCH.md` §Pitfall 4 — **why the gate must precede detection**; D-06 above depends on this
- `.planning/phases/11-web-configurable-wake-interval/11-CONTEXT.md` — D-02, the `wake_interval_s` bounds that D-02 above inherits as the on-latency ceiling

### Origin
- `.planning/seeds/SEED-004-remote-eink-display-power-toggle.md` — the seed this phase was promoted from, including its own scope reasoning and the sibling-seed relationships

### Project-level constraints
- `.planning/PROJECT.md` — the poll-only/no-inbound-connections architecture that makes D-01's periodic wake unavoidable; the battery-only v1 constraint
- `.claude/CLAUDE.md` — GSD workflow enforcement; the stdlib-only server constraint

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/plane/render.py` — `_build_quiet_hours_canvas()` (~line 1809) plus `QUIET_HOURS_HEADING_TEXT` / `QUIET_HOURS_BODY_TEMPLATE` (~line 304): the precedent for a dedicated hold-state canvas and for locked copy as module constants. D-03/D-04 follow this shape.
- `server/poll_loop.py` (~line 677-740) — the quiet-hours gate: a once-per-cycle decision computed from a single `device_cfg` read, an early return before detection, a `poll_state` latch, and the same three-line battery decision the main path computes. The structural model for D-06/D-07.
- `server/device_config.py` — `DEFAULT_LED_ENABLED` (line 56) and `normalise_led_enabled()` (line 371): the exact never-raising boolean pattern D-08/D-09 follow.
- `companion/pages/config_page.py` — `led_group()` (line 443) and `quiet_hours_group()` (line 501), plus the shared `settings-checkbox` label class introduced by quick task `260901-qif`. The UI pattern to mirror.

### Established Patterns
- **Single config read per cycle.** `run_once()` reads `device_cfg` once and derives every gate decision from it — never a second `load_device_config()`. The comment at `poll_loop.py:677` explains why: a mid-cycle save landing between two reads renders a panel half in one configuration and half in another.
- **`now_s()`, never `datetime.now()`** inside the poll loop — it is the module's harness-replaceable clock seam.
- **Served `sleep_s` may exceed the stored config bound.** `device_config.py:61-63` records that `quiet_hours_sleep_s()` is explicitly allowed to exceed `WAKE_INTERVAL_MAX_S`. **D-01 means this phase does not use that latitude** — but the planner should know it exists rather than rediscovering it as a blocker.
- **Vendored-file discipline** — `stub-server/byos_server.py` is vendored; every change there is recorded in its `VENDOR.md` local-modifications list, which already names the Phase 06.2 LED constant, the Phase 10 quiet-hours extension and the Phase 11 wake-interval read. **D-01 requires a fourth entry**: the served `sleep_s` chain is `read_wake_interval_s()` → `quiet_hours_sleep_s()`, and the 300s off-state pin composes into it per D-05's max rule. Add the `VENDOR.md` entry in the same commit as the code, matching the three existing precedents.

### Integration Points
- `server/poll_loop.py`'s `run_once()` — the new gate, ahead of the quiet-hours gate and both ahead of detection.
- `server/plane/render.py`'s canvas dispatch — a new hold state alongside the quiet-hours branch.
- `companion/pages/config_page.py` — a sixth Settings group (after theme, runway, LED, quiet hours, wake interval).
- `server/device_config.py`'s `load_device_config()` / `save_device_config()` — the eighth registry key.

</code_context>

<specifics>
## Specific Ideas

- The developer's framing challenge is the phase's most important artefact: *"pas possible de juste faire ON/OFF ? on peut modifier le firmware si besoin"*. From the operator's side this **is** just ON/OFF — a single checkbox — and the plan should keep it that way. Any design that surfaces the wake-cadence mechanics in the UI has drifted.
- Willingness to modify the firmware was offered explicitly. **D-01 means this phase needs no firmware change**, and the plan should not introduce one. Recorded because it widens the option space for the deferred refinement below.

</specifics>

<deferred>
## Deferred Ideas

- **A longer off-state sleep bound, if `DEVICE-05` shows the wake itself dominates.** D-01 assumes the panel refresh is the dominant per-cycle cost. If the multi-day discharge run later shows the wake/WiFi/HTTPS cycle dominates instead, "normal cadence, no render" will save far less than expected, and extending `sleep_s` during an off period becomes worthwhile — accepting the longer on-latency D-02 currently avoids. That refinement is deliberately out of scope here: it is a small, well-understood follow-up once real numbers exist, and building it now would be optimising against an unmeasured assumption.
- **Firmware-side changes** — offered by the developer, not needed under D-01. Would only come into play for the deferred refinement above, and even then the existing 86400s ceiling likely suffices without a firmware edit.
- **A physical off control** — not raised in this discussion, and view-switching hardware is already a v2 item (`DEVICE-01`/`CFG-02`). Noted only to mark it as out of scope for this phase.

</deferred>

---

*Phase: 12-remote-display-on-off-toggle*
*Context gathered: 2026-09-05*
