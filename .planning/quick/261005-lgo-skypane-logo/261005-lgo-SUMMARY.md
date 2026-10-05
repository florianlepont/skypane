---
quick_id: 261005-lgo
status: complete
---

# 261005-lgo summary

- `icon-logo` sprite symbol (`ICON_IDS` 39 -> 40): currentColor ink plus one accent stroke with
  class `logo-accent`, bound to `--color-accent` by one stylesheet rule. The geometry lives in
  `LOGO_MARK_BODY` (`companion/ui_base.py`) and is shared by the symbol and the login card's inline
  copy (`logo_mark_html()`), because the login shell has no sprite.
- Brand lockup `.brand` = decorative mark + the existing `.site-title` text in the sidebar and the
  phone app bar. The 28px mark sits inside the title's line box, so the lockup is as tall as the
  bare title was (asserted in a browser). The brand was never a link; it still is not.
- Favicon: the `data:` Georgia "S" is replaced by `/static/favicon.svg` (the filled accent tile with
  the glyph knocked out) and `/static/apple-touch-icon.png` (180x180, rendered once with Chromium by
  `scripts/render_apple_touch_icon.py`, committed). Both are `STATIC_ROUTES` entries, so they are
  public like every static asset (the route table derives the public GETs from that dict), with the
  shared `public, no-cache` policy, ETag/Last-Modified and 304s. Every shell (page, login, error)
  emits the same `FAVICON_LINK_HTML`.
- `style.css` header: the accent-reservation comment named no consumers at all any more (the list
  had been trimmed away); it is now an exhaustive list generated from the rules that actually paint
  accent, plus the logo flick.
- Tests: `companion/test_brand_logo.py` (links on every page type in EN/FR, public routes, content
  type, caching, no secrets, PNG size/colour, lockup and login markup) and
  `companion/test_browser_brand_logo.py` (390/1280, light/dark, scripts-blocked login with
  `reduced_motion="reduce"`). Icon-count pins updated to 40.
- Render baseline regenerated: all 48 pages differ, and every difference is accounted for exactly:
  favicon link (48), brand lockup (88 = sidebar + app bar on 44 pages), sprite symbol (44) and the
  login mark (4); undoing those four changes reproduces the old bodies byte for byte.
- Design-system skill: added a short "Brand mark" section.
- Deferred: a README logo (it needs an outlined-path SVG, since GitHub does not load the repo's
  fonts).
