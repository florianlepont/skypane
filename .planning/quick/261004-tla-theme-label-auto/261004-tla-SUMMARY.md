# 261004-tla Summary

## Root cause

`.theme-form .theme-option` segments are equal-width (`flex: 1 1 0; min-width: 0`) with
`white-space: nowrap` and no overflow handling. In the 240 px desktop sidebar a segment is
66 px wide (50 px of text after 8 px padding each side); "Automatique" needs about 70 px, so
it painted over "Clair" (scrollWidth 86 vs clientWidth 66). At 320 px in the mobile menu it
also overflowed (86 vs 82). 360 px and wider phones fit.

## Changes

- FR `nav.auto` "Automatique" becomes "Auto"; new `nav.auto_full` ("Auto (suit le système)" /
  "Auto (follows the system)") is the Auto button's aria-label, which starts with the visible text.
- CSS: segment padding 8px to 4px, `overflow: hidden; text-overflow: ellipsis`, so a longer label
  is clipped inside its own box.
- `companion/test_browser_theme_switch.py`: FR/EN x light/dark x 320..1280 px, no segment
  overflow, neighbours never intersect; oversized-label clipping; Auto accessible name.
- Render baseline regenerated (label, aria-label attribute).

Shortening the label alone fixes today's strings; the CSS change is what keeps a future longer
label from colliding.
