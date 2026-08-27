---
title: Presence-adaptive polling cadence via a motion (PIR) sensor
trigger_condition: >
  Revisit once Phase 5's real multi-day discharge run (05-01 Tasks 2-3)
  produces an actual battery-life verdict. If the measured runway is
  shorter than the developer wants, this is the first lever to pull before
  reaching for a bigger battery pack or solar — it buys back battery
  specifically during the long stretches nobody is near the frame (e.g.
  a workday), without sacrificing freshness at the moment someone actually
  looks. Also revisit if the companion web interface (CFG-01..04) gets
  built first, since presence events would naturally show up there too.
planted_date: 2026-08-27
---

## Context

Explored 2026-08-27 in an open-ended hardware-capabilities brainstorm
(`/gsd-explore`, no prior topic). The question that led here: does a
motion or light sensor add anything real to this device, beyond what's
already built?

**Light sensor: ruled out.** The Spectra 6 panel has no backlight to dim —
there's nothing to adjust based on ambient brightness. The one plausible
use ("suppress refreshes at night to save battery") is achievable with a
plain time-of-day schedule instead, since flight/RER activity at Orly
already has a real overnight lull — no new hardware needed for that gain.

**Motion (PIR): kept, reframed once during the conversation.** The first
framing considered was "refresh only when motion is detected" — rejected,
because the poll+blit cycle takes real time (~31.5s full refresh, ARCHITECTURE.md line ~135, plus
the network round-trip before that), so a viewer who just walked up would
see the *old* image for the first several seconds before it flips —
arguably worse than today's behavior, where a background poll already
keeps the display close to fresh regardless of whether anyone's looking.

The idea that survived: keep the existing periodic background poll (so
the display is already fresh by the time anyone glances at it), but let
**recent presence adjust the polling interval itself** — stretch `sleep_s`
out during long stretches with no detected motion (e.g. a workday with
nobody home), and pull it back to the normal cadence once motion resumes.
This targets battery savings specifically during the hours the display
provides zero value to anyone, without touching freshness during the
hours it matters.

## Why this fits the existing architecture, not a bolt-on

`app_main.c`'s wake loop already gets its next `sleep_s` handed to it by
the **server**, not decided locally by the device (see the backoff
mechanism in `backoff.c` for the existing precedent — the device reports
outcomes, the server/device-side logic computes the next interval, never
the reverse). Presence would slot into the exact same shape: the device
reports "motion last seen at T" (or simply a boolean "seen since last
wake") as part of its regular poll, and whichever side already owns the
`sleep_s` decision folds that signal in. No new decision-making surface
needed on the device beyond reading one more GPIO and reporting it.

Power-wise, this is very likely close to free: the ESP32-S3 can wake from
deep sleep on an external GPIO interrupt (the log contract already has an
unused "button" wake-reason slot that proves this wake path exists in the
firmware, even though nothing is wired to it yet — see
`firmware/main/app_main.c`'s `wake_reason_string()`), and small PIR
modules (e.g. AM312-class, ~2-3€) draw on the order of single-digit µA in
standby — comparable to the ESP32-S3's own deep-sleep draw, not a
material new power budget line.

## Real risks to design around, not just wave away

- **Debounce/cooldown required.** Without one, someone walking past
  repeatedly while getting ready could trigger far more wake cycles than
  the current fixed cadence — worse for both battery and the panel's
  wear budget (see `panel_guard.h`'s refresh-spacing protection, which
  exists for exactly this class of problem on the *blit* side already).
  Any presence-driven cadence change needs its own floor, not just an
  unbounded "shrink whenever motion is seen."
- **False positives/negatives are real** for cheap PIR sensors (pets,
  drafts, sunlight changes, temperature swings) — this should degrade
  gracefully to "acts like today's fixed cadence" rather than fail in a
  way that starves the display of updates.
- **Whether the device or the server should own the presence-to-interval
  mapping** is an open design question, not resolved during this
  brainstorm — leaning toward the server, to match how `sleep_s` and
  backoff are already decided there, but not settled.
