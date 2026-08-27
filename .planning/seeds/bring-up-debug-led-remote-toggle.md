---
title: Bring-up/debug LED (GPIO21 built-in), optionally remote-toggleable via the poll protocol
trigger_condition: >
  Revisit if the developer keeps finding hardware bring-up/reflash sessions
  frustrating without visual feedback (the immediate pain point that raised
  this). Also revisit once the companion web interface (CFG-01..04) gets
  built, since a remote toggle for this LED converges naturally with CFG-03
  (device health status) — worth building the two together rather than
  bolting the toggle on afterward.
planted_date: 2026-08-27
---

## Context

Raised 2026-08-27, mid-session, right after the developer flashed for the
05-03 battery-ADC checkpoint. Motivation in the developer's own words: it's
frustrating to power up the board with no feedback, because it's unclear
whether anything is actually happening. The idea: a status LED, understood
from the start to sit **behind the picture/frame** (not visible from the
wall-facing side in normal use) — so it doesn't reopen `REQUIREMENTS.md`'s
existing "no status LEDs" decision (Out of Scope table: *"would make the
frame read as a gadget rather than ambient art"*), since that decision was
about a permanently wall-visible indicator, not a hidden bring-up aid.

## What was established (technical feasibility)

**No new hardware, no soldering** — same shape of finding as the battery-ADC
research earlier this session. The XIAO ESP32-S3(-Plus) module has a
built-in **"User LED"** (separate from the existing charge-status LED) wired
to **GPIO21**, active-low. Confirmed unclaimed by this project's pin map
(`firmware/sdkconfig.ee02.defaults`'s full claimed-pin list — SCK=7, MOSI=9,
CS_M=44, CS_S=41, DC=10, RST=38, BUSY=4, EN=43, KEY0=5, KEY1=3, KEY2=2,
BATTERY_ADC=1, BATTERY_ADC_EN=6 — GPIO21 appears in none of it).
[CITED, WebSearch aggregation of Seeed community/board-reference sources,
not yet cross-verified against an official Seeed schematic for this exact
board combination the way the battery-ADC finding was — same category of
"high confidence, verify on real hardware before relying on it" as that
finding started out.]

**Power budget — the one real design constraint.** An LED lit continuously
during deep sleep would be genuinely damaging to this project's battery-life
goal: an LED typically draws single-digit-to-tens of mA, against a deep-sleep
budget in the tens of µA — leaving it on through sleep could plausibly cut
battery life by an order of magnitude or more, directly undermining Phase 5's
whole purpose. The fix is a firmware discipline, not a hardware limit: **the
LED must be strictly scoped to the active wake window** (boot → WiFi connect
→ poll → optional panel refresh, a few seconds to tens of seconds), during
which its draw is negligible next to what WiFi/the panel already cost for
that same window. Left on for the full active window, cost is close to free;
left on through sleep, it isn't.

## Remote-toggle idea (developer's follow-up question)

Asked explicitly: could this LED be enabled/disabled remotely via a web
interface? Yes, and it fits the project's existing architecture without
needing the full companion web interface (`CFG-01`..`CFG-04`, still an
unscoped v2/v3 idea) to exist first:

- The poll protocol already has this exact shape for `sleep_s` — the
  **server decides, the device reads the value on its next poll and obeys
  for that cycle** (see `backoff.c`'s precedent, and the
  `presence-adaptive-poll-cadence.md` seed's note on the same pattern). A
  `led_enabled` flag would slot in identically: server-side state (even just
  a config value at first, no UI needed to start), included in the
  `/display` response, read by firmware, applied for that wake window only.
- **Converges with `CFG-03`** (device health status via the web interface,
  already seeded): both answer "is the device alive?", just through
  different channels — CFG-03 shows it on a screen, a remote LED toggle
  gives an immediate physical confirmation. Worth designing together rather
  than as two unrelated features, if/when the companion web interface is
  actually built.

## Real risks / open questions, not yet resolved

- GPIO21's identity as the "User LED" is sourced from web research this
  session, not yet confirmed against the real, assembled board the way the
  battery-ADC circuit will be confirmed by 05-03's own checkpoint — same
  "flash and observe, no risk either way" verification approach would apply
  here too, before relying on it.
- Exact trigger semantics not decided: always-on during every active window
  (simplest, ~free), a single blink at wake (cheaper, less continuously
  informative), or only lit while a specific fault condition holds (closer
  to the "communication/data outage fault icon" idea another concurrent
  session captured the same day — worth checking for overlap before
  building either).
- Whether this needs its own protocol field or could piggyback on an
  existing one (e.g. reusing/extending the `reset` boolean's slot in the
  `/display` response) is an implementation detail, not decided here.
