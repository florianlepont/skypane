# Phase 58: part 2 preparation audit (server side, no hardware)

Date 2026-11-14. Read-only audit of the server code against what the evaluation unit needs. Previews were
rendered from `server.pairing_image` for the simulated 800x480 profile; nothing was changed.

## Finding 1: the evaluation unit has no hardware profile yet

- `server/hardware.py` `REGISTRY` holds the legacy type and two simulated types only. The EE04 exists as a
  number-free `PLANNED_BATTERY_SLOTS` entry (`seeed-ee04-7in3-spectra6`), not as a profile.
- The server resolves a device's type from `devices.hardware_type` in `fleet.db` through
  `hardware.get_profile(...)`, which raises for a key that is not in `available_types()`. Simulated types are
  visible only when the simulation environment variable is set.
- Consequence: plan 58-03 Task 3 (`import-bench` into the evaluation unit's type, scheduling, offers) and
  plan 58-04 Task 1 (rendering for the unit) cannot run until a profile for the unit exists.
- Proposed addition (code, no hardware needed): register the evaluation unit's profile with the same gate as
  the simulated types (hidden unless the simulation variable is set, so production does not offer a type with
  no real unit), landscape layout family, 800x480, firmware target and `max_image_bytes` from the packed size,
  battery values copied from the legacy profile and marked provisional with a "not a measurement" source (the
  pattern of `_SIM_LANDSCAPE`). The 58-04 battery task later replaces it with measured values and the owner
  decides when to lift the gate. Tests first in `server/test_hardware.py`.

## Finding 2: the pairing screen is not a native landscape composition

- `server/pairing_image.py` draws the pairing screen on the 1200x1600 portrait reference canvas and scales it
  by `min(w/1200, h/1600)` for other profiles. For 800x480 that factor is 0.3, so the whole composition is a
  small centred block. The retired screen already has a native landscape variant.
- Preview of the code `ABCD-2345` (rendered, not on glass): the code has a cap height of about 36 px, which is
  about 7 mm on the 0.2 mm pixel pitch of the 7.3" panel; by the usual rule (cap height about distance / 200)
  that reads at about 1.4 m. The two body lines are about 12 px (2.4 mm), readable at about 0.5 m. Most of the
  panel stays empty.
- The 58-04 pairing test ("code legible at wall-reading distance") is therefore likely to be marginal. Options
  after the real-panel look: accept as is, or add a native landscape pairing composition (a larger code, using
  the status-screen layout of the retired screen). That is a new code task for the owner to decide; it is not
  added to the plans before the panel has been seen.

## Finding 3: landscape hold screens exist, the rest was not checked

`server/plane/render/landscape_hold.py` provides empty, quiet hours, display off, battery empty, no connection
and updating screens for the landscape family. The flight screens (`landscape.py`, `giant/compose_landscape.py`)
were approved as previews in an earlier phase. A legibility check at 400 mm and 1 m on the real panel stays in
58-04 Task 1.
