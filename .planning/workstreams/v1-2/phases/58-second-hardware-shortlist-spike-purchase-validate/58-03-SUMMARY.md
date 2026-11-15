# 58-03 summary: cable flash, real OTA and signing bench on the evaluation unit

Closed 2026-11-15. Evidence: `hardware/SECOND-HARDWARE-VALIDATION.md` and the commands in `hardware/SECOND-HARDWARE-BENCH-RUNBOOK.md`.

## Done on the unit (2026-11-14)

- Cable flash of a signed dev image, first refresh, Wi-Fi and enrolment provisioning.
- Data path and colours: the six inks show; the picture reads as designed with the cable tail at the bottom (mounting decided).
- Signed OTA installed (`trial`, then `installed`); wrong signature refused (`fail-image`, firmware kept); unsigned image refused by the server; raised floor installed and a lower offer refused (`fail-floor`, no download).
- Two defects found and fixed: hardware type claim (#394), http offer URL in dev (#395). The floor test option is in `firmware/build.sh` (#396).

## Not done, and why

- Wrong-hardware image on the panel: not run, by the owner's decision (the live frame's image could drive the wrong panel driver). Shown on the server side only: the server never offered the legacy image to the unit.
- No serial log of a whole wake was captured (native USB disappears in deep sleep).

## Outcome

The pass conditions of `firmware/SIGNING.md` steps 3 to 7 were observed. Gating of the type in production stays with the owner (Phase 64).
