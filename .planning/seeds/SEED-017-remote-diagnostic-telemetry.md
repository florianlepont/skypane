---
id: SEED-017
status: dormant
planted: 2026-11-15
planted_during: "v1.2, owner's question of 2026-11-15: does the firmware report enough to investigate a frame remotely?"
trigger_when: "Milestone v1.3, confirmed by the owner on 2026-11-15, because the simplified Wi-Fi setup (SEED-013, item 6) already needs a firmware release; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: medium
---

# SEED-017: Remote diagnostic telemetry from the frame

## Why This Matters

Frames will sit in other people's homes, anywhere in France. When one stops
updating, the owner must be able to tell why without getting the frame back.
The audit of 2026-11-15 found that the frame reports a good set of health
numbers but not the detail needed to explain a crash or a lost connection.

## What the frame reports today

Sent as request headers on every display call and stored in the
`device_health` table (`server/history_db.py`): battery in millivolts, Wi-Fi
signal strength, firmware version, boot reason, the result of the last
over-the-air update, and a wake-stats header (`X-Wake-Stats`) with this wake's
boot time, Wi-Fi time and attempt count, plus the previous wake's awake,
request, download, draw, panel bus and TLS times, whether the panel was
redrawn, and an outcome token.

## Gaps to close

1. **Crash cause.** Boot reason says "panic" or "brownout" but not where or why.
   Candidate: keep a short crash record (program counter, task, reset count) in
   storage that survives a restart, and send it on the next wake.
2. **Memory.** No free-heap or lowest-free-heap figure, so a slow leak is
   invisible.
3. **Wi-Fi failure detail.** Only the number of attempts is sent. Missing: the
   channel, the access point identifier, and the reason code of the last
   failed connection.
4. **Panel faults.** A panel busy timeout or a driver error is not itemised.
5. **Failures before the first request.** When the frame cannot reach the
   server, nothing is recorded until a later wake succeeds. A small ring of the
   last few failed wakes, reported afterwards, would cover it.
6. **Logs.** Nothing leaves the frame except over USB. A short, bounded log of
   the last wake, sent only on request or after a fault, is an option.

## Constraints

- **Privacy:** no Wi-Fi password, no enrolment secret, no network name, no
  location. Diagnostic values are counters, codes and durations, as
  `firmware/main/wake_telemetry.h` already states for the wake stats.
- **Battery:** extra header bytes and flash writes cost energy. Measure with the
  Phase 47.1 method before shipping, and keep the header within a bounded size.
- **Server agreement:** the server drops the whole wake-stats header on any rule
  violation, and a CI check compares the firmware and server limits
  (`server/test_wake_stats_firmware_agreement.py`). New fields extend both.
- **Reach:** a firmware change reaches existing frames only by over-the-air
  update (Phase 57 sequencing, signing).
- **Companion:** decide what the owner sees on the health page, and what a
  co-manager or user sees (probably only the plain-language state).

## Breadcrumbs

- `firmware/main/api_client.c` (telemetry headers), `firmware/main/wake_telemetry.c`, `firmware/main/wake_record.c`
- `firmware/main/app_main.c` (boot reason handling, fault screen)
- `server/wake_stats.py`, `server/history_db.py` (`device_health`)
- `.planning/seeds/on-device-fault-icon.md` (on-screen fault icon, fulfilled)
