# Deferred items

Pre-existing failures found during plan execution, out of scope for the
plan that found them (not caused by that plan's own changes, per the
SCOPE BOUNDARY rule) — logged here rather than fixed.

## From 40-13 (Home/Flights/Airlines/Health pages onto stable i18n ids)

- `companion/test_browser_ux_03.py::test_cfg34_live_age_ticks_at_each_converted_site[chromium-health-registry]`
  fails with `AttributeError: module 'server.poll_loop' has no attribute
  'save_poll_state'`. Confirmed pre-existing: reproduces identically on
  the pre-40-13 commit (`f7d501e`'s parent), before this plan touched
  any file. `server/poll_loop.py` is Phase 39 territory (server/), not
  in 40-13's file scope — the fix belongs to whichever session owns
  that module's public API surface.
