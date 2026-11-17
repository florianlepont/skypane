# Phase 57: Combined Legacy-Frame Firmware Release - Discussion Log

> Audit trail only. Decisions are in 57-CONTEXT.md.

**Date:** 2026-11-14
**Areas discussed:** signing lock, 401 recovery display, hardware header, mismatch policy, sequencing

- Lock: no spare board, wait for EE04 before any publication. Chosen: wait.
- 401 recovery display: "nothing new" chosen over an on-device message screen.
- Hardware header: send one chosen over none.
- Mismatch: strict chosen, narrowed by agreement to firmware offers and the new container only.
- Sequencing: single combined version chosen over waiting for the 47.1 window.
