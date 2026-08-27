---
title: On-screen fault icon for comm/data outages, pointing to the web interface
trigger_condition: >
  Revisit once the companion web interface (CFG-01..04) work starts, since
  CFG-05 depends on it existing as the destination the icon points users
  to. DEVICE-06 (the firmware-local fallback screen) is technically
  independent and could be picked up earlier if device-communication
  outages become a real pain point before the web interface exists.
planted_date: 2026-08-27
---

## Context

Explored 2026-08-27 in a continuation of the same-day hardware-capabilities
brainstorm that produced CFG-01..04 and the presence-adaptive-polling seed.
The starting idea: alongside the (not-yet-built) low-battery icon
(DEVICE-04), it'd be useful to have a second small icon that tells the user
"something's wrong, go check the web interface" — rather than the frame
just failing silently.

## Two trigger paths need two different mechanisms

The natural first framing — "one generic fault icon" — splits into two
genuinely different implementations once you follow where each kind of
failure actually happens:

**Device-side communication failure** (WiFi down, server unreachable) is
the harder case, because it's exactly the situation where the normal
render pipeline can't help: `fp_panel_draw()` blits whatever buffer the
*server* already rendered and sent down in a successful poll
(`firmware/main/panel.h`); `state_machine.c` explicitly draws nothing on a
failed poll (comment: "Neither is a failure ... — the panel keeps its
last content"). If the server can never be reached, it can never bake an
alert icon into anything either. The only way to get a real-time signal
during an actual outage is a fallback the *device* can produce entirely on
its own.

**Server-side data-source failure** (adsb.fi/adsb.lol erroring) is the
easier case: as long as the device *can* still reach the server, the
server already controls exactly what gets rendered into the image it
sends back — no new mechanism needed beyond "notice the source failed,
and bake in a small icon instead of / alongside the usual composition."

## Feasibility of the local fallback (DEVICE-06)

Checked against the actual firmware interface, not assumed:

- `fp_panel_draw(const uint8_t *buf)` / `epd_blit()` (`firmware/main/panel.h`,
  `epd13in3e.h`) take a raw, already-composited buffer — `EPD_BYTES`
  = 1200×1600/2 = 960,000 bytes (4 bits/pixel, 6-color packed). There is
  currently **no local drawing/text-rendering capability in firmware at
  all** — every panel update today is a server-rendered blob, blitted
  as-is.
- Embedding a full 960KB pre-rendered fallback image in flash was the
  first instinct, but it's unnecessary and would eat a large slice of the
  2.4MB (`0x250000`) app partition (`firmware/partitions.csv`) for what is
  mostly a blank screen. A solid-color `memset()` fill computed at
  wake-time, plus a small pre-baked icon bitmap blitted at a fixed offset,
  gets the same result for a few KB of flash — no compression, no new
  panel-driver work, same `fp_panel_draw()` call path.
- Natural trigger: `backoff_n` already exists in NVS for exactly this kind
  of escalation (the doubling curve — 300/600/1200/2400/4800s — captured
  live in Phase 1's 01-07). Decided during this session: fire the local
  fallback at `backoff_n >= 2` (~15-20 min of cumulative failure) rather
  than waiting for a later backoff level — favors a responsive signal over
  tolerating a longer transient blip.

## Scoping the "stale data" side (CFG-05) to avoid a false-alarm trap

The project already has a standing decision (STATE.md, 2026-08-11): no
freshness-timestamp / stale-data indicator in v1, despite research
flagging it as a common pitfall. This idea doesn't reverse that decision
wholesale — it was scoped narrowly during this session specifically to
avoid the failure mode that decision was guarding against: the render
pipeline's normal **Empty state** (no aircraft in the deadband right now,
source responding fine) must never trigger this icon. Only a genuine
upstream failure — the server unable to query adsb.fi/adsb.lol at all —
counts as the "stale data" trigger. Conflating "no plane right now" with
"something's broken" would make the icon fire constantly during Orly's
normal quiet periods and train the user to ignore it.

## No conflict with the existing low-battery icon (DEVICE-04)

DEVICE-04 bakes a low-battery icon into the image on the *success* path
(device reports battery voltage via `X-Battery-Mv`, server renders
accordingly). This fault icon only ever appears on a *failure* path
(device-local fallback, or CFG-05's server-side outage render) — the two
never compete for the same rendered frame.

## Open questions, not resolved during this brainstorm

- Exact visual design of the local fallback icon/screen (a real design
  pass, not just a technical feasibility check).
- Whether `backoff_n` resets/re-triggers cleanly across the local-fallback
  path the same way it does today for the normal poll-retry path — needs
  verification once this is actually planned, not assumed from this
  conversation alone.
- Whether CFG-05's icon should look identical to DEVICE-06's local
  fallback icon (same alert glyph reused in two different rendering
  contexts) or be visually distinct — leaning toward "same icon" for a
  consistent user-facing signal, but not settled.
