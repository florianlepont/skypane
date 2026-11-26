# Visible window of the mat on the 7.3 inch frame

What part of the 800 x 480 pixel screen of the Seeed EE04 stays visible behind
the mat of the IKEA RÖDALM 13 x 18 cm frame, and how the server uses it.

## Reading

Method: a calibration image (rulers every 5 pixels, a number every 25, on the
four edges, three rulers per side) was shown on the assembled frame on
2026-11-26; the owner took one photo of the frame and sent it. The numbers
below were read by the assistant from that photo, on enlarged crops, to about
plus or minus 2 pixels. They are not the owner's own readings and not a
measurement with an instrument.

| Side | Hidden pixels read from the photo | Ruler tick seen at the mat edge |
|------|-----------------------------------|---------------------------------|
| Left | about 47 | the 50 tick, 3 pixels inside the edge |
| Right | about 49 to 50 | the 50 tick, right at the edge |
| Top | about 30 | the 30 tick, half cut |
| Bottom | about 1 to 2 | the 5 tick, then the top half of the 0 label |

The visible area is therefore about 704 x 449 pixels (about 140.8 x 89.8 mm at
0.2 mm per pixel), against 705 x 451 pixels expected from the mat window of
140.93 x 90.27 mm typed by the owner on 2026-11-23 (design value).

The image looked straight on the photo; the camera was not square to the frame,
so a tilt below about 1 degree cannot be excluded.

## Window used by the server

`x = 48, y = 30, width = 702, height = 448` (the readings, with one pixel of
safety on each side). It is a field of the EE04 hardware profile only; the
13.3 inch frame and the simulated landscape type have none. The server draws
each screen at the window size and pastes it into the 800 x 480 image; the
strips the mat hides repeat the nearest edge of the screen.

The owner confirmed these values on 2026-11-26 ("ces valeurs sont bonnes"), after seeing the readings and the window; that confirmed the values.

## Result on the assembled frame

The window was merged (PR 614) and deployed to production on 2026-11-26 (deploy
run 45899235327). The owner then tested the assembled frame and reported on
2026-11-26 that everything is good ("j'ai testé le cadre et tout est bon"),
reported by the owner; which screens were looked at and any finer detail were
not stated. The four numbers stay as they are.

If a screen later shows text cut by the mat, the readings are repeated and the
four numbers corrected.
