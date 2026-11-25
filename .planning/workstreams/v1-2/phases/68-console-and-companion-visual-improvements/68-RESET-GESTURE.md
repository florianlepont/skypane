# Phase 68 plan 11: reset gesture per hardware type

Gesture settled by the owner (2026-11-18): every frame has a Reset button, known and used for a long time. Older notes that say no Reset button was within reach describe an earlier kit or session and are not a contradiction. Only the place of the button and its reachability inside the enclosure are open (UNCONFIRMED).

| Profile key | Family | Gesture | Control, as printed / named in the documents | Place | Reachable in the enclosure | Alternative |
|---|---|---|---|---|---|---|
| `xiao-ee02-13in3-spectra6` | EE02 (XIAO ESP32-S3 Plus, 13.3 in, 1200x1600) | Press the Reset button | "RESET" button; the board has only RESET, no BOOT (`hardware/BRINGUP-LOG.md:1205`, `:1441`) | UNCONFIRMED (no document places it; the enclosure has one common 47.5 mm notch for "buttons and switch" and an L-shaped service bay 20 mm wide in front of the buttons, `hardware/ENCLOSURE-3D-DESIGN.md:57-59`) | UNCONFIRMED (the notch suggests yes) | Power switch OFF then ON, a `power-on` reset the firmware treats as a normal start (`hardware/PHASE34-HARDWARE-SESSION.md:190-192`; `firmware/main/reset_reason.c:71`) |
| `sim-ee02-clone` | follows EE02 (copy of the legacy profile, simulated, `server/hardware.py:200`) | same as EE02 | same | same | same | same |
| `seeed-ee04-7in3-spectra6` | EE04 (XIAO ePaper Display Board EE04, 7.3 in, 800x480) | Press the Reset button | "one reset and three user buttons"; battery connector "with power switch" (`hardware/SECOND-HARDWARE.md:81`); RESET pressed after provisioning (`hardware/SECOND-HARDWARE-BENCH-RUNBOOK.md:114-115`) | UNCONFIRMED (not stated in any document) | UNCONFIRMED (depends on the EE04 enclosure, not yet documented) | Power switch OFF then ON (`hardware/SECOND-HARDWARE-BENCH-RUNBOOK.md:29`, switch exists on the board) |
| `sim-landscape-800x480` | follows EE04 for the screen (landscape 800x480, simulated, `server/hardware.py:213`) | same as EE04 | same | same | same | same |

## What the device does after the restart

A Reset or power-on is not an abnormal reset, so the firmware does not back off: it starts the radio and polls at once (`firmware/main/app_main.c:350`, `fp_reset_is_abnormal`, only abnormal resets such as panic or watchdog sleep first; `firmware/main/reset_reason.c:71`). The server answers a retired frame with its retired image and `RETIRED_SLEEP_S` = 86400 s (`stub-server/byos_server.py:1463`); once the frame is re-activated (pending), the same poll returns the pairing code screen. So after Reset the code appears within one poll (minutes at most), not 24 h later.

## Open for the owner (UNCONFIRMED)

1. EE02: where is the Reset button and can it be pressed with the frame in its enclosure?
2. EE04: where is the Reset button and can it be pressed with the frame in its enclosure?
