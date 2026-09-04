# Phase 11: Web-configurable wake interval - Context

**Gathered:** 2026-09-04
**Status:** Ready for planning
**Source:** `/gsd-discuss-phase 11 --auto` — fully autonomous pass (mode: yolo). Every decision below is Claude's recommended choice, not a developer-confirmed one. Review before treating any of it as final; nothing here has been shown to the developer yet.

<domain>
## Phase Boundary

Make the device's wake/poll interval (`SKYPANE_SLEEP_S`) configurable from the
companion web interface — promoted from
`.planning/seeds/SEED-002-web-configurable-wake-interval.md` — instead of
requiring an SSH edit to `/opt/skypane/skypane.env` and a
`skypane-byos.service` restart.

This phase covers: a new `wake_interval_s` field in `device_config.py`'s
registry (validated min/max), a companion Settings page field to set it, and
delivery to the device via the existing `/device/v1/display` poll response
(the device honors the returned `sleep_s` as its next sleep duration — no
service restart). It does not cover: a per-time-of-day variable interval
(that's what Phase 10's quiet-hours window already does), or any change to
the device firmware (the device already treats `sleep_s` as an opaque
server-controlled value, confirmed in Phase 10). It shares one touchpoint
with Phase 10: `stub-server/byos_server.py`'s `/device/v1/display` handler's
`sleep_s` computation — see Integration Points below for the exact layering
this phase must preserve.

</domain>

<decisions>
## Implementation Decisions

**All decisions below were auto-selected (`--auto` mode) — Claude picked the
recommended option for every question without developer confirmation.**

### Delivery mechanism
- **D-01:** [auto] Delivery mechanism — Q: "Should the wake interval be
  delivered to the device via the poll/`/display` response (device honors it
  as its next sleep duration, no restart) or via a service restart triggered
  by the config write?" → Selected: "Poll-response delivery, no restart"
  (recommended default — this is SEED-002's own explicitly recommended
  option (a), matches how CFG-01/CFG-12 already deliver live config to the
  device on every poll with zero service-restart plumbing, and needs no new
  protocol field since `sleep_s` already exists in the response).

### Validation bounds
- **D-02:** [auto] Min/max bounds — Q: "What min/max should the wake
  interval accept?" → Selected: "min 10s, max 3600s (1 hour)" (recommended
  default — 10s floors the interval well above any risk of hammering the
  free-tier ADS-B aggregators or the server itself; 3600s caps staleness at
  worst-case one hour, matching the seed's own "too short burns battery, too
  long risks staleness" framing). **Flagged for developer confirmation** —
  this specific pair of numbers was not discussed live; the developer may
  want a different max in particular (e.g. capping it much lower, given the
  whole point of the frame is near-real-time departure info).

### Interaction with Phase 10 (quiet hours)
- **D-03:** [auto] Base-value layering — Q: "Does the new configurable wake
  interval replace the CLI `--sleep` argument as the 'base' `sleep_s` that
  Phase 10's `quiet_hours_sleep_s()` extends, or does it layer
  independently?" → Selected: "New config field becomes the base value;
  `--sleep` becomes the bootstrap/fallback default" (recommended default —
  matches every other `device_config.py` field's own "degrade to documented
  default when absent" contract, and preserves Phase 10's existing
  `quiet_hours_sleep_s(base_sleep_s, ...)` call shape unchanged: only what
  gets passed as `base_sleep_s` changes, from `self.args.sleep` directly to
  a device-config-aware read that falls back to `self.args.sleep`).

### Field naming and companion UI
- **D-04:** [auto] Field name — Q: "What should the new registry field be
  called?" → Selected: "`wake_interval_s`" (recommended default — this is
  SEED-002's own suggested name, and matches the existing `_s` suffix
  convention `quiet_hours_start`/`_end` do not use but a plain duration
  field arguably should, for unit clarity at the call site).
- **D-05:** [auto] Companion UI presentation — Q: "How should the companion
  Settings page present this field?" → Selected: "A plain numeric
  `<input type=\"number\">` labeled 'Wake interval (seconds)', with a
  caption naming the trade-off (shorter = fresher info, more battery drain;
  longer = more battery life, staler info at a glance)" (recommended
  default — this is the first plain numeric input anywhere in the companion
  app; every existing field is a radio, checkbox, or the Phase 10
  `type=\"time\"` input, so this is a genuinely new UI pattern worth a
  real-preview check, same discipline Phase 10 used for its own first
  `type=\"time\"` input).

### Apply-timing convention
- **D-06:** [auto] When does an edit take effect? → Selected: "Same
  'applies on the device's next scheduled poll' convention every other
  Settings field already uses (`06-CONTEXT.md` D-06/D-07)" (recommended
  default — no new mechanism needed; the device already re-reads `sleep_s`
  fresh on every poll, so the very next poll after a save uses the new
  interval, same latency characteristics as every other config field).

### Claude's Discretion
- Exact validation error copy for an out-of-bounds or non-numeric submitted
  value (mirror the existing generic save-failed flash, per every other
  field's `save_device_config()`-raises-`ValueError` contract).
- Exact companion-page form layout/spacing for the new field (mirror the
  existing Settings page's fieldset pattern; validate against a real
  preview before treating it as final, given D-05's "new UI pattern" flag).
- Whether the field pre-fills with the *current effective* interval (the
  live device-config value, defaulting to the CLI `--sleep` value on first
  load) — expected yes, matching every other field's pre-fill behavior, but
  not explicitly re-derived here since it's the obvious, only sane choice.
- Exact wording of the trade-off caption text under the field.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase's own seed
- `.planning/seeds/SEED-002-web-configurable-wake-interval.md` — the
  original seed this phase was promoted from; already recommends the exact
  delivery mechanism (D-01) and flags the min/max validation need (D-02)

### Server-side mechanism (D-01, D-03)
- `stub-server/byos_server.py` — the `/device/v1/display` handler's
  `"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir)`
  line (~415) is where the new device-config-aware base value replaces the
  direct `self.args.sleep` reference; `read_quiet_hours()` (~line 130+) is
  the exact "local modification" pattern this phase's own device-config
  read should follow
- `firmware/main/state_machine.c` (~line 51) and `firmware/main/app_main.c`
  (~line 172) — confirm (again, already confirmed in Phase 10) that
  `sleep_s` is consumed as-is from the server response with no firmware
  interpretation — this phase needs zero firmware changes for the same
  reason Phase 10 did

### Config registry pattern (D-02, D-04)
- `server/device_config.py` — `DEFAULT_QUIET_HOURS_ENABLED`/`_START`/`_END`
  (~lines 56-59), `THEME_IDS`/`RUNWAY_IDS` tuples (~lines 325-326),
  `normalise_*()` + `load_device_config()`/`save_device_config()` — the
  exact pattern the new `wake_interval_s` field must follow, including the
  "never raise, degrade to a safe default" read-path contract and the
  strict write-path validation contract

### Prior phase precedent (D-01, D-03, D-06)
- `.planning/phases/10-scheduled-quiet-hours/10-CONTEXT.md` and
  `10-RESEARCH.md` — D-01 (the discovery that `sleep_s` is already a fully
  server-controlled, per-response value needing zero firmware changes —
  same discovery this phase reuses) and the Integration Points note that
  explicitly flags this phase as sharing the same `/display` handler
  touchpoint
- `.planning/phases/10-scheduled-quiet-hours/10-03-SUMMARY.md` — the
  concrete current shape of the `/display` handler's `sleep_s` line this
  phase must read and extend, not assume
- `.planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-CONTEXT.md`
  — D-06/D-07 (config applies on device's next scheduled poll — direct
  precedent for D-06 above)

### Project planning docs
- `.planning/ROADMAP.md` — Phase 11 section
- `.planning/REQUIREMENTS.md` — no requirement ID mapping expected; this is
  an unmapped backlog phase, matching Phase 10's own precedent

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/device_config.py`'s registry pattern (`normalise_*()` + load/save
  with safe-default degradation) — direct template for the new
  `wake_interval_s` field, same as Phase 10 used for its own three fields
- Phase 10's `read_quiet_hours()` in `stub-server/byos_server.py` — direct
  template for a `read_wake_interval()`-equivalent best-effort config read,
  though this phase's read is simpler (one numeric field, no window
  arithmetic)

### Established Patterns
- "Config changes apply on the device's next scheduled poll"
  (`06-CONTEXT.md` D-06/D-07) — governs D-06 directly
- `byos_server.py`'s "local modification" discipline (tracked in
  `stub-server/VENDOR.md`) — this phase's device-config read should follow
  the same small, documented, best-effort-degrading shape Phase 10's
  `read_quiet_hours()` already established there

### Integration Points
- `stub-server/byos_server.py`'s `/display` handler — the exact point where
  this phase's new base-value read must slot in underneath Phase 10's
  existing `quiet_hours_sleep_s(base_sleep_s, ...)` call (D-03). **Mutual
  awareness discipline**: Phase 10 already flagged this shared touchpoint
  in its own `10-CONTEXT.md` Integration Points section — read
  `10-03-SUMMARY.md` before assuming the handler's current structure, since
  this phase executes second.
- `companion/pages/config_page.py` — the Settings page's existing
  fieldset-rendering and form-handling functions, where the new wake-interval
  field/section attaches (likely as a fifth group, after Quiet hours)

</code_context>

<specifics>
## Specific Ideas

None captured live — this was a fully autonomous (`--auto`) discussion pass
with no developer interaction. SEED-002.md itself is the closest thing to a
specific idea record; its recommended delivery mechanism (option a) was
adopted as D-01.

</specifics>

<deferred>
## Deferred Ideas

- A per-time-of-day variable wake interval (e.g. faster polling during
  daytime, slower overnight) — out of this phase's scope; Phase 10's
  quiet-hours window already covers the "pause entirely overnight" case,
  and a general variable-cadence schedule would be its own future phase if
  ever wanted.

### Reviewed Todos (not folded)
None — no pending todos matched this phase (`todo.match-phase 11` returned
zero matches).

</deferred>

---

*Phase: 11-web-configurable-wake-interval*
*Context gathered: 2026-09-04 (fully autonomous --auto pass — not yet reviewed by the developer)*
