# Phase 1: Foundation — Hardware Bring-up & ADS-B Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-04
**Phase:** 1-Foundation — Hardware Bring-up & ADS-B Validation
**Areas discussed:** ADS-B receiver setup, Firmware bring-up path, Battery measurement method, Hardware readiness & stub server hosting

---

## ADS-B receiver setup

| Option | Description | Selected |
|--------|-------------|----------|
| Build the permanent pipeline now | Pi + dump1090/readsb + forward to VPS, set up in Phase 1 | |
| Temporary validation only | RTL-SDR + laptop, prove reception only | |
| Test the aggregator API first | ADS-B Exchange / adsb.fi / airplanes.live — no local hardware | ✓ |
| Go straight to local RTL-SDR | Skip API test, buy dongle now | |

**User's choice:** Test the aggregator API first (ADS-B Exchange / adsb.fi / airplanes.live). Only fall back to local RTL-SDR (and later a Pi) if the API's coverage right at runway 3 (near-ground altitude) proves insufficient.

**Notes:** User self-identified as having very limited hardware technical knowledge and asked for a detailed explanation of what RTL-SDR/dump1090/local-forwarding actually means before answering. User also asked whether receiving ADS-B is legal (answered: yes, it's an unencrypted public broadcast, receive-only is standard hobbyist practice, not legal advice) and whether an API platform would be simpler — this surfaced the ADS-B aggregator API option, which was not originally presented as a first-class choice (REQUIREMENTS.md currently lists it as "fallback only"). This is a meaningful reversal of PROJECT.md's current "local ADS-B primary" framing — flagged as a downstream note in CONTEXT.md rather than edited directly, since Phase 1's job is to validate which approach actually works.

Follow-up: if the local RTL-SDR/Pi fallback is ever needed, its cost is tracked as a **separate** budget line from the €300 "display + compute" ceiling (user said "you decide"; Claude's reasoning: PROJECT.md scoped €300 specifically to the frame device itself).

---

## Firmware bring-up path

| Option | Description | Selected |
|--------|-------------|----------|
| Keep XIAO + EE02 kit | Original board choice, pre-matched to the 13.3" dual-chip panel | ✓ |
| Switch to Arduino Nano ESP32 | Different board, no ready-made panel driver | |
| Straight to ESP-IDF | Skip Arduino prototyping, needed for sleep/backoff control | ✓ |
| Arduino first, then rewrite | Faster first visible result, more total work | |

**User's choice:** Keep the XIAO ESP32-S3 Plus + EE02 kit (board hardware); go straight to ESP-IDF (firmware framework) with no Arduino prototyping detour.

**Notes:** User asked mid-discussion "what about the Arduino Nano ESP32?" — this required clarifying that "Arduino" was being used in two different senses (a programming framework vs. a specific board product from Arduino the company). Once clarified, user confirmed keeping the originally planned board.

---

## Battery measurement method

| Option | Description | Selected |
|--------|-------------|----------|
| Simple: time-to-depletion | Charge fully, run untouched, note days-until-dead | ✓ |
| USB power meter | More precise, requires extra hardware/reading | |

**User's choice:** Simple time-to-depletion approach — no extra hardware, charge fully, let it run, note days/cycles until dead or low-battery.

**Notes:** User asked "what is the easiest way for a non technical guy?" — answered with a plain-language walkthrough of the time-to-depletion method before confirming.

---

## Hardware readiness & stub server hosting

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing bought yet | All hardware still needs ordering | ✓ |
| Already have it | Hands-on work can start immediately | |
| Partially — some on hand | Mixed | |
| Real Hetzner VPS | Provision now, validates real reachability | |
| Local stub for now | Defer VPS to Phase 2 | ✓ |

**User's choice:** Nothing purchased yet (screen kit, battery pack, and conditionally the RTL-SDR all still need ordering — plan must budget lead time). Stub server runs locally for Phase 1; real Hetzner VPS provisioning deferred to Phase 2.

**Notes:** None beyond the selections above.

---

## Claude's Discretion

- Which specific ADS-B aggregator API to test first (ADS-B Exchange vs. adsb.fi vs. airplanes.live)
- Exact wake-interval cadence for the Phase 1 backoff/battery test
- Local stub server implementation details (language/framework)

## Deferred Ideas

- Building the permanent local ADS-B receiver pipeline (Pi + dump1090/readsb + forwarder) — deferred pending Phase 1's aggregator-API validation result
- Provisioning the real Hetzner VPS — deferred to Phase 2
- Updating PROJECT.md/REQUIREMENTS.md's ADS-B "primary vs. fallback" framing — deferred until Phase 1 produces a validation result
