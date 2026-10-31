# Phase 53: Detection Modes - Discussion Log

> **Audit trail only.** Decisions are in 53-CONTEXT.md.

**Date:** 2026-10-31
**Areas discussed:** position centre and settings UI, catalogue and label, position rules, parallel runways and current frame

| Question | Chosen |
|---|---|
| Position centre | Device location + radius |
| Where to set | New dedicated page |
| Selector | Search then runway list |
| Catalogue scope | All, closed runways excluded |
| Label | IATA else ICAO |
| Position rules | Airborne, <=10,000 ft, 2-15 NM, lowest first |
| Rounding / bounds | 2 decimals, France + Corsica bounding box |
| Current Orly frame | Switch to generic logic (owner chose B after explanation; kept conditional on identical replay) |
| Parallel runways | Narrow corridor from nearest parallel |
| Runway entity | Full pair |
