# Plan 61-113 Summary: graphite logo and page icon (owner decision W179)

The favicon and apple-touch icon now use the graphite tile instead of the old orange (#B13F16). The favicon also has a night-mode version.

## Changes
- `companion/static/favicon.svg`: same shape. It now uses a `<style>` block with two classes (`tile`, `glyph`) and no inline colours.
  - Light mode: tile #1F2430, white glyph.
  - Dark mode (`prefers-color-scheme: dark`): tile #F2EFE9, glyph #1F2430.
  - Content type, cache headers and the route are unchanged.
- `scripts/render_apple_touch_icon.py`: tile constant is now #1F2430 and the glyph stays white. `companion/static/apple-touch-icon.png` was regenerated. It is still 180x180, and re-rendering gives an identical sha256.
- `companion/test_brand_logo.py` (updated in place):
  - The favicon test now allows exactly one `<style>` block. It previously forbade `<style>`.
  - New test: graphite tile in light, ivory tile in dark, glyph colours, and no old orange.
  - The apple-touch pixel test now expects graphite at two tile points.
- `companion/test_browser_brand_logo.py`: new test renders the served favicon as an `<img>` at 16 and 32 px under `color_scheme` light and dark, and checks tile and glyph colours.

## Other places the brand colour appears (audited)
- No web manifest and no other PNG icons exist.
- `theme-color` meta tags carry the page background (#12151D etc.), not the logo tile. Left alone.
- `--color-toast-pending: #B13F16` in `style.css` is a toast state colour. Left alone.
- `--color-accent` and the contrast-check entries for #B13F16 are the UI accent, not the logo. Left alone.
- The in-page `icon-logo` sprite uses `currentColor` plus the accent flick, so it follows the theme. Not changed.
- The favicon link has no `?v=` hash, so the render baseline and digests did not move.

## Not verified
- Real browser tab rendering. Safari ignores `prefers-color-scheme` inside SVG icons, so it will always show the light version.
- iOS home-screen icon rendering.
