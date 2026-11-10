# Plane screen layouts

The plane screen shows the flight taking off or landing in one of five
layouts. The giant-lettering family (`server/plane/render/giant/`) letters the
destination city (the origin when arriving) in oversized Anton and places the
aircraft over it. Layout ids live in `server/screen_layouts.py`.

## The layouts

| Id | Look |
|----|------|
| `classic` | The original card. Rendering is byte-for-byte unchanged. |
| `a` | Giant lettering; the nose comes in from the right edge and the rear half of the aircraft from the left edge. |
| `b` | Giant lettering; the whole aircraft centred over the lettering. |
| `c` | Giant lettering on top, the whole aircraft along the bottom. |
| `a_diagonal` | Layout `a` with a diagonal band across the field. |

Landscape canvases (for example the 800x480 simulated profile) have their own
compositors for the four giant layouts. Classic is only drawn in landscape by
the existing landscape card.

## Default layout

A frame that never chose a layout resolves to `DEFAULT_LAYOUT_ID`, which is
`"b"`. It is the only place the default is written down: change that one line
in `server/screen_layouts.py` to move every unconfigured frame to another
layout (use `"classic"` to go back to the original look). A stored layout id
that is unknown also resolves to the default; nothing stored is rewritten.

Live-frame impact: after this ships, a frame without a stored layout repaints
as layout `b` at its next screen transition, not immediately. Frames that
explicitly chose `classic` keep the original picture. The repaint is picked up
by the normal change detection, so there is no forced refresh.

## Pairings and the theme mapping

A pairing is a field colour with the ink that letters on it. The five pairings
are in `server/pairings.py` and reuse existing theme ids, so no stored theme is
ever rewritten:

| Pairing | Field | Lettering |
|---------|-------|-----------|
| `grey` | black dithered 40% toward white | black |
| `blue_light` | blue dithered 40% toward white | blue |
| `red_light` | red dithered 40% toward white | red |
| `yellow_light` | yellow dithered 75% toward white; small text dithered toward black | yellow |
| `white` | flat white | black |

Every theme in the registry maps onto a pairing from its colours alone: a theme
on a coloured field takes the field colour; a theme on paper with a stripe takes
the stripe colour; plain paper is `white`. Themes added to the registry later
are mapped without a code change.

Two assumed defaults, both adjustable only in `server/pairings.py`:

- Green themes map to the grey pairing (there is no green pairing).
- The white pairing has no band: `a_diagonal` with white draws like `a`, and
  black themes (plain or striped) land on grey.

## Status screens

Hold states (watching, quiet hours, display off, battery empty, no
connection, firmware update, retired) are drawn by
`server/plane/render/giant/status.py` in a calm style in portrait and
landscape. They ignore the theme and the pairing: the watching screen is black
on white, the other six are white on a dark dithered field. `battery_empty`
depends on the canvas size alone, so its bytes stay constant for a whole parked
episode.

## Splitting rule

A long name is split into at most three stacked lines by
`server/plane/render/giant/split.py`. The rule is deterministic and based on
the real Anton widths of the candidates (balanced natural widths, a penalty per
cut, protected letter groups such as CH or QU). There is no table of per-city
corrections. A name Anton cannot draw is retried without accents, then falls
back to the airline name and finally to the unknown-flight wording.

## Tuning constants for the glass check

The lettering is hard-thresholded (`MASK_THRESHOLD` in
`server/plane/render/giant/lettering.py`), so no mask ever blends palette
indices. `line_layer(..., downsample_2x=True)` draws at twice the size,
thresholds, halves with a box filter and thresholds again; it softens thin
joins the way the glass over the panel does and is the knob to adjust when
checking thin strokes behind the glass. Line spacing, box size and the squeeze
floor are constants at the top of `split.py` and `compose.py`.

## Rendering a layout

```
python -m server.plane.render --state departing --callsign AF1380 \
    --layout b --preview /tmp/b.png --out /tmp/b.bin
```

`--layout` accepts any id above; omitting it renders `classic`.

## Golden tests

The classic render is guarded by `server/fixtures/golden/legacy_render_baseline.json`
and `server/test_golden_render.py`. The giant family has its own manifest,
`server/fixtures/golden/giant_render_baseline.json`, and suite,
`server/test_golden_giant_render.py`. Hashes depend on the Pillow version; the
manifest records it and the hash test is skipped (not failed) when the installed
Pillow differs. Regenerate under the production pin (Pillow 13.0.0):

```
server/.venv/bin/python3 -c "import server.test_golden_giant_render as g; g.print_manifest()" > server/fixtures/golden/giant_render_baseline.json
```

Only do this when the change to the giant output is intended.

## Firmware masks

The NO CONNECTION and UPDATING hold screens are stamped by the firmware from
committed 1-bpp ink masks cut from the flat (two-colour) status canvases.
Regenerate them with `firmware/tools/gen_fault_screen.py` (and
`--screen updating`); the drift tests `server/test_fault_screen_mask.py` and
`server/test_updating_screen_mask.py` prove the headers match the renderer.
Flash-margin caveat: the two masks together add about 255 KB to the image
(156,825 bytes of bits each). The OTA slot is 0x250000 bytes (2,424,832) and a
10% margin needs the app to stay under 2,182,349 bytes; the current app size
was not measured. Read the built image size in CI before the next firmware
release. Nothing is pushed over the air by changing the server.

## Owner check on the real panel

Rendered previews use nominal colours and cannot show how the dithered fields,
the yellow pairing and thin Anton strokes read on the physical 6-colour panel
behind glass. Before relying on the new default, put each pairing on the real
frame (companion layout picker, one flight per layout, departing and
arriving) and check legibility from normal viewing distance, then confirm the
status screens, especially white text on the dithered field.
