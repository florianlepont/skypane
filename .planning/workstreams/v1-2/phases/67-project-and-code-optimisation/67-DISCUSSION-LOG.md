# Phase 67: Project and Code Optimisation - Discussion Log

> **Audit trail only.** Decisions are in 67-CONTEXT.md.

**Date:** 2026-11-27
**Areas discussed:** order of work, structural change, coverage floor

## Order of work
Options: databases/state then ARCHITECTURE then tests/dead code (recommended); tests and dead code first; documentation first.
**User's choice:** recommended order.

## Structural change
Options: small steps, no module moves (recommended); module moves allowed with shims.
**User's choice:** module moves allowed.
**Notes:** recorded as D-03 with guard rails (one subpackage per PR, shims, own check).

## Coverage floor
Options: raise to measured end value (recommended); keep.
**User's choice:** raise to measured end value.
