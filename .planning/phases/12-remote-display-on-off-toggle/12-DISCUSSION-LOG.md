# Phase 12 — Discussion Log

**Date:** 2026-09-05
**Participants:** developer + Claude (Opus 5)
**Outcome:** `12-CONTEXT.md`, D-01 through D-09

Human-reference record only. Downstream agents read `12-CONTEXT.md`, not this file.

---

## How the discussion opened

Four gray areas were presented: the off-state sleep bound (framed as central), the off-state panel appearance, precedence against quiet hours, and the config default.

The framing rested on scouting done before the discussion, which had established two things:

- Phase 10's gate is an **early return placed deliberately before detection** — `10-RESEARCH.md` Pitfall 4 records that the surgical-looking insertion point sits after detection, which would query the free-tier ADS-B aggregators every 30s all night and discard every result.
- **A precedent already exists for exceeding the config ceiling**: `WAKE_INTERVAL_MAX_S = 3600` bounds the stored field, but `quiet_hours_sleep_s()` is explicitly permitted to exceed it during a window, and the firmware accepts `range 30 86400`. So the design space for a bound was genuinely open, not constrained.

## The developer's challenge — the turning point

The developer did not pick from the four areas. They pushed back on the framing itself:

> *"pas possible de juste faire ON/OFF ? on peut modifier le firmware si besoin hin"*

This was right to ask, and it changed the phase. Two things came out of taking it seriously:

**Where the challenge did not land.** The periodic wake is not a firmware limitation, so offering to change the firmware does not remove it. The device is poll-only and accepts no inbound connections; it deep-sleeps between cycles; the server therefore cannot reach it, and it must wake and ask. With no external wake source the only lever is timer length — and the firmware already allows 24h, so there was nothing to unlock.

**Where it landed hard.** The assumed battery-versus-latency trade-off was much weaker than presented. On e-ink the panel refresh is typically the dominant per-cycle cost, and an off device does not refresh. "Normal cadence, skip the render" therefore plausibly captures most of the saving *and* stays responsive — which collapses the tension the phase had been built around, removes the need for a new bound, and shrinks the phase back toward the seed's own original "small" estimate.

**The honest caveat, surfaced rather than buried:** nobody knows the real energy split, because `DEVICE-05` — the multi-day discharge run — has never been executed. It is the single remaining open item on the v1 roadmap, and SEED-004's own trigger condition had named that verdict as the moment to revisit this idea.

## The choice offered

Given that, three options were put to the developer rather than one:

1. **Simple** — normal cadence, no render. Responsive, no new constants, probably captures most of the saving.
2. **Long sleep during off** — maximum guaranteed saving, hours-long on-latency, optimising without data.
3. **Wait for DEVICE-05 first** — decide on real numbers, and close the roadmap's last open item on the way.

**Chosen: option 1.** Recorded as D-01, with the un-measured assumption stated explicitly in CONTEXT.md and the refinement path recorded in `<deferred>` rather than lost.

## Remaining questions

With the central decision collapsed, two real questions were left:

**Off-state panel appearance → D-03.** Chosen: a dedicated sober screen, Phase 10's shape minus the return-time promise. A blank field was rejected as indistinguishable from a dead device or an outage — the project ships a source-fault icon (CFG-05) whose meaning that ambiguity would erode. A blank field with a discreet corner mark was rejected as inventing a new composition needing its own on-glass validation for no decisive gain.

**Config default → D-09.** Chosen: `True`. Follows `DEFAULT_LED_ENABLED` / `DEFAULT_QUIET_HOURS_ENABLED` — explicit boolean, never "empty means off", nothing changes for a running installation until someone opts in.

## The developer's refinement, after the options round

Mid-write, the developer added:

> *"Je pense que par contre quand l'écran est off, il faut que les check de la liseuse soient fixes à 300s"*

This replaced D-01's original "keep the normal cadence" wording, and it is better on both axes rather than being a trade: at a short `wake_interval_s` (floor 60s) a fixed 300s cuts wakes ~5× during an off period, and at a long one (ceiling 3600s) it makes switching back on *faster*, giving a predictable "back within 5 minutes" instead of "up to an hour". 300s also sits inside the existing 60-3600 bounds, so it needs none of the ceiling-exceeding latitude quiet hours was granted.

It did have one consequence worth recording: the phase now **does** touch the vendored `stub-server/byos_server.py`, contrary to the note written minutes earlier under the original D-01. The served `sleep_s` chain is `read_wake_interval_s()` → `quiet_hours_sleep_s()`, and the 300s pin composes into it — a fourth `VENDOR.md` local-modification entry alongside Phases 06.2, 10 and 11.

It also forced the precedence question open again (see D-05 below), because the obvious reading of "off wins" would have made the device wake *more* often during an off period that overlaps a quiet window than quiet hours alone would.

## Settled by derivation, not asked

Precedence was not put to the developer, to avoid a third question round on a point with an obvious answer. D-05/D-06/D-07 are marked in CONTEXT.md as **derived, and the planner may revisit them with reasoning**:

- **D-05** — precedence splits into two axes that resolve differently. *What the panel shows*: the toggle wins, being the explicit manual instruction against a standing schedule. *How long the device sleeps*: the longest value wins, `max(300, quiet_hours_remaining)`. Collapsing these into a single "off wins always" would pin sleep at 300s inside a quiet window and make the device wake more often with the display off than quiet hours alone — inverting the point of both features, for no operator-visible gain, since the panel is dark either way and a switch-back-on at 02:00 shows nothing until the window ends regardless.
- **D-06** — the display-off gate is evaluated first, and like the quiet-hours gate must sit before detection. Same Pitfall 4 reasoning, with more force, since an off period can last indefinitely.
- **D-07** — moving between two hold states must not trigger an e-ink refresh. If a quiet window ends while the toggle is still off, the panel stays put rather than repainting from one hold screen to another: a refresh costs energy and flashes visibly for no informational gain. This makes the existing single-purpose `quiet_hours_active` latch insufficient as-is; generalising it is planning work.

D-07 is the one derived decision with real design weight — it is flagged here so a reviewer can challenge it rather than inherit it silently.

---

*Phase: 12-remote-display-on-off-toggle*
