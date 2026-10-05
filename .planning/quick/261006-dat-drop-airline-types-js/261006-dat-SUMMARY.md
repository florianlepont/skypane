---
quick_id: 261006-dat
status: complete
---

# 261006-dat summary

- `companion/static/airline-types.js` is deleted along with its route, shell constant, route
  alias, Airlines page script entry and render-snapshot route entry. It was loaded only by the
  Airlines page (the per-page script map), not by every page.
- Nothing used it: no code emits the attributes or class it queried, and the stylesheet had no
  rules for them (the carousel CSS went with 261006-alr).
- `test_companion_app_03.py`: the shell script pin goes from 17 to 16.
- Render baseline: the four `/airlines` page entries lose exactly the
  `<script src="/static/airline-types.js" defer>` tag and the `GET /static/airline-types.js`
  route entry is gone; the other 44 pages are unchanged.
