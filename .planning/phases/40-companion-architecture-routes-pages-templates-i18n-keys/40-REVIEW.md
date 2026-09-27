---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
reviewed: 2026-09-27T00:00:00Z
depth: standard
files_reviewed: 91
files_reviewed_list:
  - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
  - .claude/skills/sketch-findings-skypane/references/data-density.md
  - .planning/REQUIREMENTS.md
  - companion/app.py
  - companion/battery_chart.py
  - companion/draw.py
  - companion/flash.py
  - companion/frame_state.py
  - companion/freshness.py
  - companion/health_sections.py
  - companion/health_signals.py
  - companion/i18n.py
  - companion/i18n_fr/__init__.py
  - companion/i18n_fr/airlines.py
  - companion/i18n_fr/calendar_group.py
  - companion/i18n_fr/common.py
  - companion/i18n_fr/display.py
  - companion/i18n_fr/flights.py
  - companion/i18n_fr/frame_state.py
  - companion/i18n_fr/health.py
  - companion/i18n_fr/home.py
  - companion/i18n_fr/nav.py
  - companion/i18n_fr/notifications.py
  - companion/i18n_fr/registry.py
  - companion/i18n_fr/rules.py
  - companion/layout.py
  - companion/login_page.py
  - companion/page_context.py
  - companion/pages/__init__.py
  - companion/pages/airlines_page.py
  - companion/pages/config_page.py
  - companion/pages/health_page.py
  - companion/pages/history_page.py
  - companion/pages/home_page.py
  - companion/post_actions.py
  - companion/request_body.py
  - companion/routes.py
  - companion/screens.py
  - companion/settings/__init__.py
  - companion/settings/calendar.py
  - companion/settings/form.py
  - companion/settings/form_post.py
  - companion/settings/notifications.py
  - companion/settings/quiet_hours.py
  - companion/settings/rules.py
  - companion/settings/runway_led.py
  - companion/settings/theme.py
  - companion/settings/wake_interval.py
  - companion/static/style.css
  - companion/static_files.py
  - companion/test_browser_ux_03.py
  - companion/test_browser_ux_04.py
  - companion/test_companion_app_01.py
  - companion/test_companion_app_02.py
  - companion/test_companion_app_04.py
  - companion/test_companion_app_05.py
  - companion/test_config_page_01.py
  - companion/test_config_page_02.py
  - companion/test_config_page_03.py
  - companion/test_config_page_04b.py
  - companion/test_config_page_05.py
  - companion/test_health_signals.py
  - companion/test_i18n.py
  - companion/test_page_context.py
  - companion/test_render_baseline.py
  - companion/test_route_table.py
  - companion/test_static_cache.py
  - companion/test_status_pages_03.py
  - companion/test_status_pages_04.py
  - companion/test_status_pages_05.py
  - companion/test_status_pages_05b.py
  - companion/test_status_pages_07.py
  - companion/test_structure_guards.py
  - companion/test_stylesheet_structure.py
  - companion/test_view_pages_02.py
  - companion/test_view_pages_03.py
  - companion/test_view_pages_04.py
  - companion/testdata/battery_chart_baseline.json
  - companion/testdata/render_baseline.json
  - companion/theme_preview.py
  - companion/ui_base.py
  - companion/ui_components.py
  - companion/ui_nav.py
  - companion/ui_shell.py
  - companion/ui_time.py
  - stub-server/test_poll_cycle.py
  - test-support/companion_render_snapshot.py
  - test-support/companion_structure.py
  - test-support/computed_style_snapshot.py
  - test-support/i18n_ids.py
  - test-support/test_i18n_ids.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 40: Code Review Report

**Reviewed:** 2026-09-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 91
**Status:** issues_found

## Summary

This phase splits `companion/app.py`'s pre-table if-chains into a declarative
route table (`companion/routes.py`), a static-asset allowlist
(`companion/static_files.py`), a typed `PageContext`
(`companion/page_context.py`), a page-shell/component library split across
`companion/ui_base.py`/`ui_time.py`/`ui_nav.py`/`ui_components.py`/`ui_shell.py`,
per-settings-group modules under `companion/settings/`, and the three small
feature additions (CFG-34 live relative-time ages via
`companion/ui_time.py`'s `relative_time_html()`/`relative_copy_attrs()`,
CFG-39's battery chart rebuilt on `companion/draw.py`'s shared SVG
primitives via `companion/battery_chart.py`, and CFG-52's keyboard-operable
artwork drop zone in `companion/pages/airlines_page.py`).

I read every module in the file list end to end (route table, static
allowlist, page-context builder/lazy-loader machinery, the full
`companion/app.py` request-handling surface including auth/session/cookie
handling and the Origin/Sec-Fetch-Site POST gate, `post_actions.py`'s eight
settings-action POST handlers, `request_body.py`'s capped-body reader,
every `companion/ui_*.py` module, every page module, every
`companion/settings/*.py` group module, `battery_chart.py`/`draw.py`,
`health_signals.py`/`health_sections.py`, `frame_state.py`,
`theme_preview.py`, `login_page.py`, and `i18n.py`/`i18n_fr/__init__.py`),
cross-referencing constants that are deliberately duplicated rather than
imported (to avoid the documented import-cycle constraints between
`companion.app`, `companion.routes`, the page modules, and the
`companion.settings.*` group modules) against their sibling definitions.

**Overall assessment:** the implementation is unusually disciplined —
every dynamic value is escaped through one `escape_html()`/`draw.escape()`
choke point, every user-facing string is declared as a stable-ID
`i18n.msg()` Message (`i18n.t()`/`i18n.t_lang()` reject a plain `str`
outright), every broad `except Exception` is a documented fail-closed
degrade rather than a silent swallow, the route table's auth-gating is
table-driven and covered by `test_route_table.py` against a committed
pre-refactor baseline, and the request-body/multipart parsing in
`request_body.py`/`post_actions.py` is bounded and defensive against
malformed input. I did not find a security vulnerability, a data-loss
risk, or a behavioural regression against the stated "no behaviour change
except the three CFG-34 conversions" contract.

I found one quality defect (a hardcoded, untranslated English fallback
inside a component the rest of the file otherwise treats with strict
i18n discipline) and one purely cosmetic redundancy. Neither is a
blocker.

## Warnings

### WR-01: `data_table()`'s empty-rows fallback bypasses the i18n system

**File:** `companion/ui_components.py:576-577`
**Issue:** `data_table()` is otherwise fully disciplined about the
project's bilingual-UI requirement — every other string in this file (and
every string in the ~90 files reviewed) is declared via `i18n.msg()` and
resolved through `i18n.t()`. Its one no-rows fallback branch, however,
calls `empty_state()` with two bare Python string literals instead of
Messages:

```python
def data_table(headers, rows, mono_columns=(), raw_columns=(), desc_columns=(), prose=False,
               modifier=None):
    if not rows:
        return empty_state("No data yet.", "Nothing to show here yet.")
```

Every other empty-state call site in the reviewed files (`history_page.py`,
`health_page.py`, `health_sections.py`, `airlines_page.py`, ...) passes
`i18n.t(SOME_MESSAGE)` for both arguments. `escape_html()` (called
internally by `empty_state()`) accepts a plain `str` without complaint, so
nothing raises — the English text simply renders untranslated to a French
reader if this branch is ever reached, in direct violation of
`CLAUDE.md`'s "every user-facing string literal" bilingual requirement and
of `test_i18n.py`'s own stated intent to scan every render for
untranslated copy.

In the current codebase this branch is unreachable from any real caller —
`health_page.py`'s and `health_sections.py`'s own call sites already guard
`data_table()` with an empty-rows check before ever calling it (both
`_battery_section()`'s `trend_rows` and `resolution_stats()`'s `rows` are
verified non-empty first) — so this is a latent defect, not a
currently-observable bug. It is also proven byte-for-byte by
`companion/test_status_pages_02.py`'s
`test_empty_state_default_form_is_byte_identical_and_compact_is_opt_in`,
so this is a pre-existing/pinned behaviour rather than something newly
introduced by this phase's diff — but it is still a real defect sitting in
a file this phase touched, and the very next caller that forgets to
pre-check emptiness (e.g. a future page module) will silently ship
untranslated English.

**Fix:** declare the two literals as `i18n.msg()` Messages and translate
them at the call site, matching every other `empty_state()` caller in the
codebase:

```python
_DATA_TABLE_EMPTY_HEADING = i18n.msg("common.no_data_yet", "No data yet.")
_DATA_TABLE_EMPTY_BODY = i18n.msg(
    "common.nothing_to_show_here_yet", "Nothing to show here yet.")

def data_table(...):
    if not rows:
        return empty_state(i18n.t(_DATA_TABLE_EMPTY_HEADING), i18n.t(_DATA_TABLE_EMPTY_BODY))
```

(`companion/ui_components.py` does not currently import `companion.i18n`;
it would need to, matching every sibling `ui_*.py` module's own import.)

## Info

### IN-01: Redundant duplicate `except` clauses

**File:** `companion/app.py:770-773`
**Issue:** `_serve_theme_preview_image()` catches `OSError` and then
`Exception` back to back, with identical handling in both branches:

```python
try:
    payload = theme_preview.cached_preview_bytes(
        self.args.state_dir, theme_id, live_event=live_event)
except OSError:
    return self.send_html(404, self._not_found_page())
except Exception:
    return self.send_html(404, self._not_found_page())
```

`OSError` is already a subclass of `Exception`, so the first clause is
dead code — every `OSError` that would reach the first `except` is also
caught (identically) by the second. This isn't a bug (the observable
behaviour is correct either way), but it's a maintenance trap: a future
reader may reasonably read the split as meaningful (e.g. assume the two
branches differ, or later specialise one without noticing the other still
shadows it).

**Fix:** collapse to a single clause:

```python
except Exception:
    return self.send_html(404, self._not_found_page())
```

---

_Reviewed: 2026-09-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
