---
quick_id: 261005-hrd
status: complete
---

# 261005-hrd summary

- Health's Resolve links (table row and phone card) are triggers for the shared resolve dialog:
  full `data-view-panel-*` vocabulary plus `data-view-panel-return="health"`, `href` to
  `/airlines?resolve=<prefix>` kept for scripts-blocked visitors. `panel-lookup.js` loads on Health
  and copies the return target into a hidden `return` field of the name form.
- New `companion/resolve_dialog.py`: the return allow-list (`health` only, anything else means
  Airlines), trigger attributes, a hidden step-B trigger and the dialog with the return field.
  `airlines_page.py` only gained an optional hidden-HTML hook on its name form (kept under the
  1500-line ceiling).
- `post_actions.py`: the name POST reads `return`, the upload POST reads `?return=`; both redirect
  through `resolve_dialog.return_route()`. Refusals redirect to `/health?resolve=<prefix>` so the
  dialog reopens on the name step with the field focused; a saved name without artwork reopens it
  on the artwork step.
- Health no longer lists a prefix with a manual entry, so a resolved row leaves at once.
- Tests: `companion/test_health_resolve_dialog.py` (served HTML, allow-list, routes) and
  `companion/test_browser_health_resolve.py` (390/1280, EN/FR, light/dark, no-JS). Two Health
  counting tests (`<use>` and heading counts) now include the dialog. Render baseline: only the
  four Health entries changed.
- A flake found while stabilising: the dialog's entrance scales it, so a box measured right after
  opening was 43 px; the test now waits for the animations to finish.
- Not changed: a refused artwork upload from Health lands on Health with the error toast but does
  not reopen the artwork step (same as Airlines, which does not either).
