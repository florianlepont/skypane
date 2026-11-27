# Assembly note: rear enclosure of the 7.3 inch frame

How the printed enclosure of the Seeed EE04 frame (7.3 inch, 800 x 480) goes
into the IKEA RÖDALM 13 x 18 cm frame. Every statement is either reported by the
owner (with its date) or a design value (not measured). Nothing here was
checked by the assistant on a real part.

## Parts

Printed in PLA (owner's decision of 2026-11-23, on a Bambu Lab X1 Carbon, 0.2 mm
layers, textured PEI plate; files in `hardware/cad/print/`):

| Part | File | What it is |
|------|------|------------|
| Tray and shim in one part | `skypane_tray_shim_merged.stl` | holds the board, the antenna and the battery, and centres the screen; printed with supports (owner, 2026-11-26) |
| Lid | `skypane_lid.stl` | wall hooks, rests for the frame tabs, two hinge lugs, the engraved name, logo and button letters |
| Stand | `skypane_stand.stl` | one leg on a diagonal hinge with a stop; stands the frame in landscape and in portrait |

The print project with the three parts is `skypane_print_project.3mf`. The
Blender source is `hardware/cad/source/skypane_cassette.blend`; the generating
script is stored inside it.

Not printed: the IKEA frame with its glass and its mat (the mat is not cut; the
image is reframed to its opening by the server), the EE04 board with its screen,
its antenna and its ribbon, the 3000 mAh battery pack of 8 x 50 x 60 mm (Kubii,
vendor size), M2 self-tapping screws for the board, JST-PH 2.0 mm extension cables (used in
the frame, per the owner on 2026-11-26; where they go is not stated), anti-slip pads for the foot
of the stand (the owner has some and did not use them).

## Order of assembly

1. Print the three parts. The first assembly on 2026-11-23 and 2026-11-24 was
   reported by the owner as working: the board went on the four standoffs with M2
   screws ("j'ai pu visser proprement la carte"), all components fitted in the
   tray, the lid held on the frame tabs by itself.
2. Screw the board on the four standoffs of the tray. Pass the screen ribbon
   through the slot of the tray.
3. Place the antenna, then the battery pack in its pocket, and connect the
   battery last (design order).
4. Put the tray into the rebate of the frame behind the screen.
5. Fit the lid on the frame tabs. No screw holds it: the owner found the screws
   useless on 2026-11-24 and the lugs were removed.
6. Snap the two pins of the leg into the hinge lugs of the lid. Reported by the
   owner on 2026-11-26: the pins snap in and hold. Reported on 2026-11-27: both
   lugs of that lid then broke off at assembly (PLA, 1.5 mm plate); the lid was
   redesigned with thicker lugs on a socle (`ENCLOSURE-PRINT-ORDER.md`, entry of
   2026-11-27) and must be reprinted. Advice for the new lid, not tested: lay the
   lid flat on a table with the lugs over the table, not over the edge, and press
   one pin down into its throat at a time, straight down; do not lever the leg
   sideways while a pin is half in.

## Using it

- On a wall: the hooks of the lid take a wall screw. Wall hanging works
  perfectly (owner, 2026-11-26); no load or time test was reported.
- On furniture: open the leg to its stop. It stands the frame at about 26
  degrees in portrait and 27 in landscape (design values); it does not close
  under the frame and the stop resists when pushed (owner, 2026-11-26). Fold it
  flat on the lid to put the frame away.
- Access: USB-C, switch, RESET and buttons are reachable (owner, 2026-11-26, "pas
  de souci"). The three buttons other than RESET carry the letters A, B, C; which
  letter is which key is not known yet.

## Known limits

- The foot of the leg touches the desk on part of its surface only, with and
  without the frame (owner's photos, 2026-11-26). The owner decided to change
  nothing in the model; the anti-slip pads were not used (owner, 2026-11-26), so
  how the stand behaves with pads is not tested.
- The teeth of the horizontal hook slot are too small to be useful (owner,
  2026-11-26).
- Wi-Fi with the enclosure: no loss against the bare frame (the readings and
  their limits are in `ENCLOSURE-WIFI-TEST.md`); the interleaved test was not
  done.
- The 3 mm printed PLA hinge pins and the thin lid plate (1.5 mm) were not
  stressed beyond the checks above; the first hinge lugs of the lid broke at
  assembly (2026-11-27), and the reinforced lugs are not printed yet.
- Taking the frame apart again risks breaking the printed PLA threads of the
  screw holes (owner, 2026-11-26).
- The displayed image is reframed to the mat opening by the server for the EE04
  only; the window and its readings are in `ENCLOSURE-VISIBLE-WINDOW.md`.
