<!-- GSD:project-start source:PROJECT.md -->

## Project

**SkyPane**

An e-ink wall/desk frame that shows real-time departure info: flights taking off from Paris-Orly (ORY) and the next RER trains from Orly-Ville station, switchable via a physical button. Built on the same "wake → poll → display → deep sleep" architecture as the flightportrait reference project, running on battery power, with a small always-on cloud server generating the display images.

**Core Value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.

### Constraints

- **Budget**: Hardware ≤ €300 total (display + compute) — user-set ceiling, roughly matches flightportrait-class hardware cost
- **Power**: Battery-only for v1, no solar, no wall power — indoor solar placement is unreliable, and the user wants real battery-life data before considering solar
- **Server hosting**: Small always-on cloud VPS, not a home server — a home server/Raspberry Pi is only reachable while powered and networked; the device should always find a reachable server

<!-- GSD:project-end -->

<!-- GSD:stack-start source:shipped code (hand-maintained, quick 260923-9fe) -->

## Technology Stack

This is the stack that actually ships. The pre-build research in
`.planning/research/STACK.md` (AeroDataBox, PRIM, Hetzner, FastAPI,
APScheduler) is kept as history but no longer describes the code — the
project pivoted to ADS-B detection of runway-3 traffic before v1.

| Area | What ships |
|------|-----------|
| Device | Seeed XIAO ePaper DIY Kit EE02 (XIAO ESP32-S3 Plus + 13.3" E Ink Spectra 6, 1200×1600, 6-color), 3.7 V LiPo — `hardware/BOM.md` |
| Firmware | ESP-IDF 5.3.1 (C), built in the `espressif/idf:v5.3.1` container (`firmware/build.sh`); Apache-2.0, derived from flightportrait/frame — `firmware/VENDOR.md` |
| Flight data | adsb.fi + adsb.lol (ADS-B positions, corroborated), adsbdb.com (callsign → airline/route); airplanes.live opt-in only — `COMPLIANCE.md` |
| Server | Python 3.12, stdlib + Pillow + requests only (`server/requirements.txt`); poll loop is a systemd timer oneshot every 30 s; device protocol served by `stub-server/byos_server.py` (`skypane-byos.service`) |
| Companion | stdlib `ThreadingHTTPServer` (`companion/app.py`), shared-password auth, English/French UI |
| Hosting | OVH VPS-1, Ubuntu, Caddy for TLS, three systemd units — `deploy/README.md` |
| Tests / CI | stdlib test harnesses (`./scripts/run-all-tests.sh`), ruff, coverage gate, Playwright for browser UX checks; GitHub Actions with a reviewer-gated production deploy |

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

- **Sketch findings for skypane** (the companion app's current design system — tokens, colour and contrast, typography, spacing, cards, control density, navigation, and page patterns — maintained continuously across phases) → `Skill("sketch-findings-skypane")`
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
