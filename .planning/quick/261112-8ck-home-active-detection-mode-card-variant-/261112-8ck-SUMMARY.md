---
status: complete
---
# Quick task 261112-8ck: Home "Detection" card (variant A)

Shipped on `feat/home-detection-mode-card` (draft PR, not merged).

- `companion/detection_summary.py`: `home_card_html()`, new messages (FR in `i18n_fr/detection.py`).
- `companion/pages/home_page.py`, `routes.py`, `post_actions.py`: the card renders on Home for every role that can open Home.
- `companion/ui_nav.py`, `companion/static/freshness.js`: the card joins Home's live-refresh regions.
- `companion/test_home_detection_card.py`: 12 behaviour tests (modes, no place, outside France, FR, link, per-frame, escaping, admin, co-manager, outsider).
- `companion/testdata/render_baseline.json`: regenerated (only the freshness.js version hash moved).

Findings:
- `tracked_runway` is written on every config save, so "never chosen" cannot be distinguished from a chosen legacy runway 3. The card shows Orly 07/25 as an airport setting rather than claiming "default".
- A place renamed elsewhere reaches an open Home on the next full refresh, not on the cheap freshness tick.
- Chromium of this container cannot launch the repo's browser tests (missing headless shell); they were skipped here and must be green in CI.
