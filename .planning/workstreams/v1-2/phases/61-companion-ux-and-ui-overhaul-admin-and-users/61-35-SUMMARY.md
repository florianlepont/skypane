# Phase 61 Plan 35: Home notification at the top and dot-word title Summary

Quick follow-up after owner validation of the deployed companion.

- The amber/red Home notification now renders directly under the page title and above the state card, for every role. It stays inside the `.home-facts` freshness swap region (the region moved, its selector and the swap registry are unchanged), so it still updates with the status. Its content, mailto behaviour and escaping are untouched.
- The state card's big title is now the same word as the status dot (frame_status words: Up to date / Resting / Low battery / Overdue / Not seen yet / No contact; FR: À jour / Au repos / Batterie faible / En retard / Pas encore vu / Sans contact). The screen on/off information stays on the Screen switch row. No new strings. Title, dot and notification can no longer disagree.
- 61-UI-SPEC.md Home section updated with both rules.

Tests updated in place: `test_home_notice.py` (served-HTML order title, notification, state card; title/dot agreement in EN and FR), `test_home_state_card.py` (title wording), `test_browser_home_notice.py` and the sweep case in `test_browser_overhaul_sweep.py` (order, title equals dot word, 44 px link, no overflow at 360 and 1280 px, EN/FR, both themes). `companion/testdata/render_baseline.json` regenerated.

Deviations: none.
