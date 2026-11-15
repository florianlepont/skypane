# 58-04 summary: native layout, pairing test, battery sample

Closed 2026-11-15 by the owner, with the battery part not delivered.

## Done

- Native 800x480 layout seen on the panel; the owner judged it good (a judgement, not itemised measurements).
- Pairing screen redrawn in the status charter (#397). The four real-panel pairing checks passed on 2026-11-14: code legible from 4 metres, claimed, retired, re-activated with a new code.

## Not delivered: the battery sample and the rebuilt model

- A discharge run started on 2026-11-15 at 09:08 (USB unplugged, first reading 4064 mV, rated capacity about 3000 mAh from the owner's memory). It was interrupted by USB plugs and by the bench server stopping, and the owner could not keep the computer on for days. The log was not provided. No valid sample exists.
- No battery value was measured. The values of the evaluation type in `server/hardware.py` stay what they were: copied from the legacy profile, marked provisional. Nothing was derived or estimated.
- Accepted by the owner on 2026-11-15 ("clôture la 58 avec le modèle provisoire"). Real battery data is expected from production use of the unit; Phase 64 (criterion 7) and Phase 65 (battery curves) carry it.
- The 4064 mV first reading looks low for a full cell; a multimeter check was not done.

## Method kept

`hardware/SECOND-HARDWARE-BATTERY.md` holds the capture and analysis method, reusing `hardware/logtools.py` read-only.
