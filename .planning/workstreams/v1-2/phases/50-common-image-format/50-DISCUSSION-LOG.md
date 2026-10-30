# Phase 50: Common Image Format - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-30
**Phase:** 50-common-image-format
**Areas discussed:** announce signal, header layout, reader scope, hash/URL/cut-over

---

## Area selection

Offered: announce signal (X-Img-Fmt vs X-Fw-Version threshold), header layout (palette id vs inline, CRC32 vs SHA-256, reserved compression), firmware reader scope (host-only vs wired), hash/URL/cut-over.

**User's choice:** "je te laisse tout choisir" — all four delegated to Claude.
**Notes:** Claude applied the milestone research defaults (explicit X-Img-Fmt header, 24-byte aligned header with palette id and CRC32, host-only reader, hash over served bytes) and resolved the 21-vs-24 byte header inconsistency.

## Claude's Discretion

All four areas above.

## Deferred Ideas

Reader wiring and OTA (Phase 57); per-device images (Phase 51); other palettes/geometries (Phases 56, 58); compression.
