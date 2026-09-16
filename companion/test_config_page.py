#!/usr/bin/env python3
"""Contract harness for companion/pages/config_page.py — CFG-01's theme
picker, CFG-12's runway picker, and CFG-07's manual poll-trigger control
(06-CONTEXT.md).

Covers: render() emitting both fieldsets from server.device_config's own
registries with the current values pre-selected, both helper texts
appearing escaped-verbatim, the poll-trigger button's enabled/disabled
states, handle_post()'s server-side membership-test validation (a
non-member theme or runway writes nothing and reports the save-failure
flash key, a partial-field post carries the other setting forward
unchanged, two adversarial path-traversal/SQL-shaped payloads are
rejected by the same membership test), and one end-to-end HTTP round
trip proving the D-07 confirmation copy reaches a real browser response
after a real save.

Stdlib-only (json, os, shutil, socket, subprocess, sys, tempfile, time,
urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_config_page.py
"""
import ast
import datetime
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import tokenize
import io
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import app as companion_app  # noqa: E402
from companion import battery  # noqa: E402
from companion import draw  # noqa: E402
from companion import i18n  # noqa: E402
from companion import auth  # noqa: E402
import companion.i18n_fr as i18n_fr  # noqa: E402
import companion.layout as layout  # noqa: E402
from companion.layout import escape_html  # noqa: E402
import companion.prefs as prefs  # noqa: E402
from companion.pages import config_page  # noqa: E402
import companion.i18n_fr.display as i18n_fr_display  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import calendar_rules, colour_rules  # noqa: E402

TEST_PASSWORD = "config-page-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
# 06.6.3-03: 39 (pre-plan baseline) -> 42 (Task 1: D-02/D-06 LED copy
# rename + heading-dedup checks, +3) -> 45 (Task 2: D-04/D-05 theme/runway
# checks, net +3 — the old "theme_fieldset() emits one radio per THEMES
# registry entry" check was replaced outright, its own assumption no
# longer true for the real single-theme registry, by two new checks plus
# two new runway-card checks) -> 46 (Task 3: D-03 dirty-state bar
# nesting/ordering check, +1) -> 47 (heading-color-consistency: one
# consistent heading level for all four settings groups, +1).
# 06.6.4.1-03: 47 (pre-plan baseline) -> 51 (Task 1: D-01/D-02/D-05 form
# half/D-26 single-column three-wrapped-section merged-form shape, +4 —
# the three-dirty-sections-in-order check, the single-top-level-div
# runway_fieldset() check, the Theme/Runway description-sentence check,
# and the bottom-button static-fallback-attribute check; several
# pre-existing checks were retargeted in place onto the new markup shape
# without changing the total, per this file's own established
# discipline) -> 56 (Task 2: D-05 handle_post() LED-merge behaviour, +5,
# one check per <behavior> bullet) -> 60 (Task 3: D-03/D-04/D-06
# cross-file DOM-contract guards between config_page.py's constants and
# dirty-state.js/style.css, +4).
# 06.6.4.1-07: 60 (pre-plan baseline) -> heading text and every /config
# route literal retargeted to /settings in place, no count change (Task
# 1) -> 54 (Task 2, D-05: the 8 checks exercising the now-deleted
# led_fieldset()/led_section()/handle_led_post() were deleted outright
# (-8; their coverage is superseded by the pre-existing handle_post()
# LED-merge checks and the render() shape check, confirmed before
# deleting, not re-added) plus 1 new source-assertion check that
# config_page exposes none of the three retired symbols (+1); the two
# live-HTTP LED checks were retargeted in place from /config-led onto
# SETTINGS_ROUTE (no count change) and 1 new check pins the retired
# /config-led route now 404s (+1); net -6).
# quick task 260901-qif: 54 (pre-plan baseline) -> 57 (Task 3, +3: the
# .runway-row containment/ordering check, the led-checkbox label class +
# unchanged input-attribute-sequence check, and the third cross-file
# DOM-contract guard proving style.css actually styles .theme-status/
# .runway-row/.led-checkbox. Task 2's retarget of
# _runway_fieldset_returns_single_top_level_div() (one div pair -> two)
# was in place, no count change).
# quick task 260901-re6: 57 (pre-plan baseline) -> 57 (Task 1, no count
# change: the runway-row containment/ordering check, the section-
# captions-appear-once check, and the helper-texts-appear-verbatim check
# were all retargeted in place onto the merged THEME/RUNWAY/LED
# _SECTION_CAPTION constants and restyled markup, per this file's own
# established retarget-without-recounting discipline) -> 57 (Task 2, no
# count change: the form-class-hook check gained the SETTINGS_FORM_ID
# assertion in place, and the dirty-bar-nested-inside-form check was
# inverted wholesale into a dirty-bar-is-sibling-of-form check, both
# retargeted onto the moved/restyled save bar with no count change) -> 60
# (Task 3, +3: observed on-disk baseline was 57 before this task; added
# the one-caption-per-group position-assertion check, the retired-
# helper/description-symbol source assertion check, and the cross-file
# CSS DOM contract guard covering .section-caption, the restyled
# .dirty-bar, fixed-not-sticky positioning, and the 240px must-equal
# pair).
# quick task 260901-s5o: observed on-disk baseline was 60 before this
# task. Task 1 (+1): added the Poll-caption both-branches-and-position
# check, and widened _section_captions_appear_escaped_verbatim_exactly_once()
# in place to cover a fourth constant (POLL_SECTION_CAPTION), no count
# change for that widening. Task 2 (no count change): the cross-file CSS
# guard (_style_css_carries_section_caption_and_restyled_fixed_dirty_bar())
# was retargeted and extended in place onto the floating-card save-bar
# treatment.
# merge of origin/main (Phase 8 six-Spectra-6-colour theme rework, 19
# real theme entries replacing the single "sky" placeholder): main's own
# _theme_fieldset_one_radio_per_registry_entry() check is reinstated (see
# that check's own comment for why), and three checks testing main's
# still-pre-06.6.4.1-07 dual-form LED architecture (led_fieldset()/a
# second /config-led form) were dropped as testing functionality this
# branch already retired. No further checks were added or removed fixing
# the 5 newly-surfaced post-merge failures in the existing (pre-conflict,
# cleanly-inherited-from-HEAD) theme_fieldset()-isolation checks — those
# were in-place rewrites. Recomputed directly against the real on-disk
# check(...) call count at merge-resolution time rather than trusting the
# incremental arithmetic above, which had drifted from actual: 64.
# 10-05-PLAN.md: 64 (pre-plan baseline) -> 68 (Task 3, +4: markup/field-
# order/escaping checks for quiet_hours_group() plus the render()-wiring
# check) -> 73 (Task 3, +5: handle_post()'s quiet-hours save-checkbox-on,
# save-checkbox-absent-still-persists-times, reject-malformed-time,
# reject-crafted-checkbox-value, and all-or-nothing-across-groups checks).
# Five pre-existing checks were retargeted in place (the theme-status
# count 2->3, the dirty-section count 3->4, and three class-literal
# renames from led-checkbox to settings-checkbox) with no count change,
# per this file's own established retarget-without-recounting discipline.
# 11-03: +6 (Task 1, no count change: two pre-existing count-shaped
# checks — the theme-status count 3->4 and the five-dirty-section-order
# check 4->5 — were retargeted in place, per this file's own
# retarget-without-recounting discipline; the round-trip dict-equality
# literal gained "wake_interval_s": None in place too, no count change.
# Task 2, +6: wake_interval_group() markup, wake_interval_group()'s
# value-attribute-only-for-in-range-non-bool-int empty-state check,
# render()'s five-group placement/pre-fill-resolution check,
# handle_post()'s string-to-int conversion/persistence check, its
# rejection-paths-byte-identical check, and its
# empty-or-absent-leaves-unchanged check).
EXPECTED_CHECK_COUNT = 79
EXPECTED_CHECK_COUNT = 65  # + 1 (quick task 260903-peo Task 4: UIR-19's
# save-round-trip check pinning the server-side PRG redirect unchanged
# (SETTINGS_ROUTE?flash=saved) and the rendered redirect target carrying
# both the flash banner and flash-cleanup.js's deferred script tag)
# 06.6.4.1.1-05: 65 (pre-plan baseline, observed on-disk at plan start) ->
# 69 (Task 3, +4: the theme-chip preview-route contract check, the
# real-palette swatch-dot check, the hidden-radio + check-glyph markup
# check, and the zero-fieldset/three-dirty-section page-shape check — one
# new check per <behavior> bullet the plan's Task 3 lists. Seven
# pre-existing checks testing the retired fieldset/radio-list contract
# were retargeted in place onto the D-01 chip-grid markup with no count
# change, per this file's own established retarget-without-recounting
# discipline, and the cross-file CSS guard was extended in place with the
# four new .theme-chip* selector assertions, also no count change).
# 06.6.4.1.1-06 (developer checkpoint follow-up, after the developer's
# real-device review reported the selected element was hard to see): 69
# -> 70 (+1: the background-wash check proving both .runway-card--selected
# and .theme-chip--selected .theme-chip__body carry the same 12%-accent
# color-mix wash .theme-form .theme-option--active already uses).
# quick task 260904-bbi (selected state must follow the LIVE :checked
# choice, not the saved config): 70 -> 72 (+2, RED run confirmed 70/72
# with both new checks failing for the expected reason before any CSS
# was written: the strong-treatment-keyed-to-:has(input:checked) check,
# and the saved-card-degrades-to-a-quiet-marker check).
EXPECTED_CHECK_COUNT = 87  # merge of HEAD (79: Phase 10/11's Quiet hours +
# Wake interval groups) with origin/main (72: 06.6.4.1.1's theme-chip grid +
# quick task 260904-bbi's live-selection re-key) — both branches started
# from the same 64-check common-ancestor baseline (see the merge-of-
# origin/main comment above) and added 15 and 8 checks respectively with no
# overlap, so 64 + 15 + 8 = 87. Recomputed directly against the real
# on-disk check(...) call count at merge-resolution time (87/87 pass),
# not trusted from arithmetic alone, per this file's own established
# discipline.
# 12-05: +5 (Display settings group markup/checked-count check, its
# locked-caption exact-equality check, render()'s D-09 empty-config-
# checked / saved-False-unchecked prefill check, handle_post()'s
# three-checkbox-shape resolution check (absent/exact-constant/crafted,
# with byte-identity on rejection), and the cross-file guard proving
# style.css needs no new selector for the group — one new check per
# Task 2 behavior bullet. Three pre-existing fail-closed checks (the
# theme-status count 5->6, the dirty-section order 5-entry->6-entry list,
# and the DIRTY_SECTION_ATTR occurrence count 5->6) were retargeted in
# place with no count change, per this file's own established retarget-
# without-recounting discipline; the round-trip dict-equality literal
# gained "display_enabled": False in place too, no count change.
# 87 + 5 = 92, recomputed directly against the real on-disk check(...)
# call count at execution time (92/92 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 92
# 15-04-PLAN.md (D-04/D-05): +9 (the arrivals-checkbox/second-grid markup
# check, the "override stored" pre-selection check, one check per Task 2
# <behavior> bullet — checked persists, checkbox-absent clears, crafted
# checkbox value rejected, non-member theme_arriving rejected across
# three adversarial payloads, and a partial post still carries theme/
# runway forward — the named clearable-contract full round trip
# (15-VALIDATION.md row 7), and the raw no-JS HTTP POST check
# (15-VALIDATION.md row 11, the Settings-form half)). Five pre-existing
# checks were retargeted in place with no count change, per this file's
# own established retarget-without-recounting discipline: the
# theme_fieldset() default-selection and current-theme-and-runway checks
# now expect the doubled per-grid selected-radio/theme-chip--selected
# counts, the one-caption-per-group position check now expects
# theme_fieldset()'s second (Arrivals theme label) <p>, the
# .theme-chip__dot/.theme-chip__check/visually-hidden-Selected counts
# were doubled to *4/*2/*2 for the second grid, and the live-selection-
# state check's @supports selector(:has(*)) block count moved from 1 to
# 2 now that this plan adds a second, separate feature-query block for
# the arrivals-checkbox reveal. 92 + 9 = 101, recomputed directly against
# the real on-disk check(...) call count at execution time (101/101
# pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 101
# 15-05-PLAN.md Task 3 (D-10/D-11): +8 (the rules-section-placement
# check, the empty-state-then-list check, the cards-before-table DOM-
# order check, the escaped-verbatim copy check, the kind-cell/add-form-
# option shared-mapping check, the computed-swatch check, the
# no-data-dirty-section check, and the locked-heading exact-equality
# check pinning "Per-flight colour rules" literally — one check per
# Task 3 markup/copy bullet, plus the literal-text pin). No pre-existing
# count-shaped assertion needed retargeting: the new section's
# `<form>`/`<section class="page-section">` elements sit outside every
# existing count-shaped check's own scoped substring (the per-group
# `<p>`/section-caption checks call theme_fieldset()/runway_fieldset()/
# led_group() directly rather than the whole page, and the whole-page
# DIRTY_SECTION_ATTR/STATIC_SAVE_FALLBACK_ATTR counts are both
# unaffected since the rules section carries neither attribute).
# 101 + 8 = 109, recomputed directly against the real on-disk check(...)
# call count at execution time (109/109 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 109
# 16-05-PLAN.md Task 3: +18 (the Calendar settings group - three status
# states mutually exclusive, the unparseable-timestamp-falls-back-to-
# pending check, the copy-fidelity-against-16-UI-SPEC.md check, the
# forbidden-vocabulary check, the secret-never-reaches-render() check,
# the secret-never-reaches-served-HTTP-bytes check (a second, dedicated
# harness with the env var set), the no-preview/no-count check, the D-01
# no-calendar-row-in-rules-list check, three theme-select checks (exactly
# one field/populated in order, saved value selected, default-to-base-
# theme), the placement-and-dirty-attr check, the no-inline-JS check, and
# three handle_post() checks (valid persists and carries forward, four
# adversarial payloads rejected, absent leaves unchanged) - one check per
# Task 3 <action> bullet. No pre-existing check needed retargeting beyond
# the two count-shaped ones Task 1 already retargeted in place (6 -> 7
# dirty-section groups, with no count change for that retargeting).
# 109 + 18 = 127, recomputed directly against the real on-disk check(...)
# call count at execution time (127/127 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 127
# 17-03-PLAN.md Task 3: +11 (the write-only calendar_url field's no-
# value-attribute check across all four calendar_group() states, the
# five-needle containment check applied directly at calendar_group()
# rather than only at render()/served-HTTP-bytes, the disconnect
# checkbox's presence-and-unchecked check across all four states, the
# drift status's exclusivity-and-ordering check, the drift status's
# names-the-remedy-names-nothing-forbidden check, the D-07 empty-field-
# with-no-checkbox regression across two unrelated saves (the single
# most important check in this plan), the disconnect path, the D-05
# replace path, and three all-or-nothing rejection checks — a URL+
# checkbox contradiction, a crafted checkbox value, and an over-length
# URL — one check per Task 3 <action> item. No pre-existing check needed
# retargeting: calendar_group()'s widened signature and the four-branch
# status resolution are exercised only through render(), which already
# degrades calendar_drift to a falsy default, so every pre-existing
# calendar check (Section 1b above) keeps passing unmodified.
# 127 + 11 = 138, recomputed directly against the real on-disk check(...)
# call count at execution time (138/138 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 142  # 138 + 4 (phase 18: page scopes / screens registry)
EXPECTED_CHECK_COUNT = 147  # 19-07-PLAN.md Task 1 (D-07/A-25): +5 (the
# no-errors-arg-byte-identical-flash-keys check, the errors-dict-filled-
# per-field check across six real-user-error cases, the errors-dict-
# stays-empty-on-success check, the empty-quiet_hours_start-writes-
# nothing all-or-nothing pin, and the local HH:MM regex/
# save_device_config() agreement check over the plan's own input table).
# 142 + 5 = 147, recomputed directly against the real on-disk check(...)
# call count at execution time (147/147 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 153  # 19-07-PLAN.md Task 2 (D-07/A-25/T-19-12):
# +6 (render()-with-no-new-args byte-identical/no-field-error-markup
# check, the wake_interval_s message/value/aria-invalid/aria-describedby
# check, the submitted-theme-id-checked-even-when-differs check, the
# both-time-inputs-carry-required check, the calendar_url error-without-
# secret-echo check, and the cross-file style.css .field-error guard).
# 147 + 6 = 153, recomputed directly against the real on-disk check(...)
# call count at execution time (153/153 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 154  # 19-07-PLAN.md Task 3 (D-07/A-25): +1 (the
# rejected-save-without-errors-arg-still-returns-save-failed legacy-
# contract pin). 153 + 1 = 154, recomputed directly against the real
# on-disk check(...) call count at execution time (154/154 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 155  # 19-10-PLAN.md Task 1 (D-09/A-27): +1 (the
# dirty-ready-set-only-after-bar-guard source-ordering check; the other
# two edits this task made were in-place retargets, not additions).
# 154 + 1 = 155, recomputed directly against the real on-disk check(...)
# call count at execution time (155/155 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 156  # 19-10-PLAN.md Task 2 (D-10/A-28): +1 (the
# beforeunload-guard-reuses-countDifferences check). 155 + 1 = 156,
# recomputed directly against the real on-disk check(...) call count at
# execution time (156/156 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 163  # 19-10-PLAN.md Task 3 (D-14/S-04): +7 (the
# exactly-three-button-presets check, the Night-preset-matches-
# device_config-defaults check, the Work day preset check, the
# Always-on preset check, the preset-row-position check, the
# handle_post()-treats-a-preset-shaped-submission-identically check
# (T-19-38), and the dirty-state.js/config_page.py cross-file
# data-preset-* attribute-agreement check). 156 + 7 = 163, recomputed
# directly against the real on-disk check(...) call count at execution
# time (163/163 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 167  # 19-11-PLAN.md Task 1 (D-08/A-26): +4 net
# (the calendar_disconnect checkbox check was retargeted in place from
# "appears only when expected and unchecked" to "never appears at all",
# a net-zero rename; four checks were added:
# calendar_disconnect_section()'s own presence/absence-plus-shape check,
# calendar_disconnect_confirm_page()'s post-back-with-confirm-preset
# check, the disconnect form's sibling-not-descendant position check on
# the Device scope, and the disconnect form's absence when not
# configured/on the Display scope). 163 + 4 = 167, recomputed directly
# against the real on-disk check(...) call count at execution time
# (167/167 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 170  # 19-11-PLAN.md Task 3 (D-12/A-30): +3 (the
# Display-has-two/Device-has-one role="radiogroup" check, the
# every-aria-reference-resolves-and-none-is-empty check across all three
# scopes, and the hint-plus-error-both-ids-in-order check). Several
# existing checks were also retargeted in place to tolerate the new
# id="..."/aria-*="..." attributes now present (a net-zero rename, not
# a new premise): the wake-interval/display caption literals, the
# runway-row opening-tag literal, the "every settings group named
# exactly once" heading literals, the wake-interval aria-describedby
# check, and the calendar-theme select's required-attribute regex.
# 167 + 3 = 170, recomputed directly against the real on-disk check(...)
# call count at execution time (170/170 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 176  # 19-12-PLAN.md Task 2 (D-23/D-22): +6 (the
# empty-string-for-the-real-registry check, the monkeypatched
# multi-member-registry <select>/<option>/selected/accessible-name check,
# the render()-carries-no-selector-today check, the crafted-screen_id
# rejection check, the valid-screen_id round-trip check, and the
# Device-has-one/Display-has-none Edit-artwork-anchor check). 170 + 6 =
# 176, recomputed directly against the real on-disk check(...) call count
# at execution time (176/176 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 180  # 19-12-PLAN.md Task 3 (D-13/S-02): +4 (the
# _with_next_wake() helper contract, each affected caption gaining the
# suffix only when known, DISPLAY_SECTION_CAPTION never gaining one, and
# the Device header's own Next-wake line rendering only when known).
# 176 + 4 = 180, recomputed directly against the real on-disk check(...)
# call count at execution time (180/180 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 181  # 19-REVIEW.md WR-01 fix: +1 (the
# _screen_selector_html() field-level error message check). 180 + 1 =
# 181, recomputed directly against the real on-disk check(...) call
# count at execution time (181/181 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 184  # 20-07-PLAN.md Task 1 (D-10/D-11/D-12): +3
# (scope_groups(SCOPE_DISPLAY) carries Runway/Calendar and
# scope_groups(SCOPE_DEVICE) carries neither; the three section-intro
# headings render on Display in the locked order and none on Device;
# every grouped card under a Display supersection carries a --nested
# class) net of retargeting seven pre-existing checks in place (the
# calendar-disconnect confirm page's cancel link, the disconnect-form
# placement/absence pair, the scoped-render runway/LED/rules/poll
# assertions, the out-of-scope calendar-signal assertions, the HTTP
# round-trip's runway/calendar GETs, and the radiogroup count) — no
# count change from those seven, since each replaces its own prior
# assertion rather than adding a new check(...) call. 181 + 3 = 184,
# recomputed directly against the real on-disk check(...) call count at
# execution time (184/184 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 190  # 20-07-PLAN.md Task 2 (D-19/Pitfall 1): +6
# (a Display render carries exactly one action="/quick/display" form and
# one action="/quick/quiet-hours" form; neither is a descendant of
# <form id=settings-form>; the rendered Display page contains no <form>
# nested inside another <form> anywhere — the pinned regression test for
# Pitfall 1; all four scheduled inputs carry form="settings-form"; the
# shared "Applies the next time the frame wakes up." sentence appears
# exactly twice; a POST through handle_post() with the same field set as
# before this task still saves identically) net of retargeting four
# pre-existing checks that this task's own restructuring of display_
# group()/quiet_hours_group() genuinely broke (running the whole suite
# BEFORE writing any new check, per this task's own instruction, found
# these four: the Display-checkbox-checked-state check, the dirty-bar-
# sibling-of-form check, and two Calendar-placement checks — all four
# had assumed the FIRST "</form>" in a SCOPE_ALL/legacy render was the
# settings form's own closing tag, which stopped holding once display_
# group()/quiet_hours_group() started embedding their own small
# quick-action <form> ahead of it). 184 + 6 = 190, recomputed directly
# against the real on-disk check(...) call count at execution time
# (190/190 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 194  # 20-07-PLAN.md Task 3 (D-05/D-36): +4 (a
# French Display render carries the three supersection headings, the
# purpose sentence and the instant-switch sentence in French with none
# of their English counterparts; an English render still carries every
# pre-existing pinned English string; the Device render carries no
# edit-artwork markup or ?edit=1 link in either language; every key of
# companion/i18n_fr/display.py is a key of the merged companion.i18n_fr
# .CATALOG) net of retargeting the pre-existing Edit-artwork-anchor
# check in place (D-36: the link and its builder are deleted outright,
# so the check now asserts absence on both scopes instead of one
# anchor on Device) — no count change from that retarget, since it
# replaces its own prior assertion rather than adding a new check(...)
# call. 190 + 4 = 194, recomputed directly against the real on-disk
# check(...) call count at execution time (194/194 pass), not trusted
# from arithmetic alone.
EXPECTED_CHECK_COUNT = 200  # 20-09-PLAN.md Task 1 (D-14a..d) and Task 3
# (D-15a..e): the Calendar card and Flight colours section were both
# rebuilt in this same continuous editing pass, so their test retargets
# land together here rather than as two separate counts. Net effect:
# every render()-shape check against the old <select>-based calendar
# theme picker, the old one-piece calendar-status sentence, the old
# calendar_url-inside-calendar_group() field, and the old table/card
# rules list was retargeted in place to the new status_row()/compact-
# chip-grid/calendar_connect_section()/.rule-list shapes; new checks
# were added for the native-radio "Match by" segmented control, the
# rule-row kind badge/data-confirm Remove form, the plain-sans empty
# state, the suggestion chips, both disclosures' simple-mode collapse,
# and a French render of each section. Recomputed directly against the
# real on-disk check(...) call count at execution time (200/200 pass),
# not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 205  # 20-11-PLAN.md Task 1 (D-26/D-28): +5 (the
# Notifications group's status row reads Configured/Not configured and
# never leaks a substring of the stored URL; the write-only topic-URL
# input never carries a value attribute; the two checkboxes reflect
# stored state; a handle_post() round trip with a URL and both boxes
# persists the whole group and writes lang from ctx["lang"]; an empty
# URL submission leaves the stored URL intact; and the page carries no
# notifications_lang control). 200 + 5 = 205, recomputed directly
# against the real on-disk check(...) call count at execution time
# (205/205 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 209  # 20-11-PLAN.md Task 2 (D-22..D-24): +4 (a
# Display render carries exactly one .theme-live-preview figure whose
# <img> src ends in the saved theme's ?live=1 URL, loading="eager" and
# explicit width/height; every chip's own <label> carries a
# data-preview-src ending in .png?live=1 while each chip's own <img>
# keeps loading="lazy" and the fixed, non-live src; the caption names a
# seeded event's callsign and falls back to the sample wording with no
# events; a French render's live preview shows the seeded callsign
# after "Aperçu avec votre dernier vol : "). 205 + 4 = 209, recomputed
# directly against the real on-disk check(...) call count at execution
# time (209/209 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 210  # Polish fix 4 (Calendar connect form belongs
# with its card, D-14c): +1 (on the Display scope,
# calendar_connect_section()'s own <form> opening tag renders
# immediately after the Calendar card and strictly before the Runway
# card's own radio input, never after the whole page's groups).
# 209 + 1 = 210, recomputed directly against the real on-disk check(...)
# call count at execution time (210/210 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 211  # Polish fix 5 (Registry labels shown in
# French, D-05): +1 (a French Display render translates the default
# theme name and default runway label, and both scopes' screen
# caption translates "Plane frame" -> "Cadre avion", while the theme/
# runway ids stay untranslated attribute values). 210 + 1 = 211,
# recomputed directly against the real on-disk check(...) call count
# at execution time (211/211 pass), not trusted from arithmetic alone.

EXPECTED_CHECK_COUNT = 212  # D-12 fix (20-REVIEW.md verification gap):
# +1 (the Display scope's rendered <h2> order is exactly Look, Theme,
# Flight colours, Calendar, What it watches, Runway, When it is on,
# Screen on / off, Quiet hours - restoring D-12's locked Theme ->
# Flight colours -> Calendar reading order inside "Look" - and every
# calendar_theme_id radio carries a form="settings-form" attribute).
# 211 + 1 = 212, recomputed directly against the real on-disk check(...)
# call count at execution time (212/212 pass), not trusted from
# arithmetic alone.
# 21-01-PLAN.md Task 2 (D-17): net 0. The rules-disclosure collapse
# check is deleted and replaced one-for-one by
# _plain_render_carries_both_disclosures_in_full_never_collapsed (the
# display mode that selected the collapsed variant no longer exists).
# 212 + 0 = 212, recomputed directly against the real on-disk
# check(...) call count at execution time (212/212 pass), not trusted
# from arithmetic alone.
EXPECTED_CHECK_COUNT = 212
# 21-04-PLAN.md Task 1 (D-01/D-02): +4 (a Display render carries exactly
# one .quick-action--on/--off pair per switch, both inside .frame-strip;
# neither the Screen on/off nor the Quiet hours card carries any
# quick-action markup any more; both instant-switch forms carry a
# return_to hidden input whose value is the Display route; the Frame
# strip renders immediately after the page header and before the first
# section-intro) plus retargeting three pre-existing checks in place
# (the <h2> order check now expects "Frame" first; the two
# instant-switch-forms/applies-sentence checks read
# layout.QUICK_ACTION_APPLIES_SENTENCE, not the deleted
# config_page.QUICK_ACTION_APPLIES_SENTENCE). 212 + 4 = 216, recomputed
# directly against the real on-disk check(...) call count at execution
# time (216/216 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 216
# 21-05-PLAN.md Task 1/Task 2/Task 3 (D-06..D-12, R-05, R-07, R-11): net
# -1. theme_fieldset() and its five direct-call tests are deleted
# outright, along with the arrivals-override checkbox's own markup/
# handle_post checks (both replaced one-for-one by the Frame colours
# card's own new coverage: the "Same as departures" leading chip, the
# empty-string clear signal on both theme_arriving and
# calendar_theme_id, the retargeted calendar-chip-grid/rules-panel/h2-
# order/English-render/next-wake-suffix/scoped-render checks, and one
# new consolidated full-shape checklist test). Every RULES_SECTION_
# HEADING-anchored check is retargeted onto the rules panel's own
# data-usage-panel-target attribute and re-scoped to SCOPE_DISPLAY
# (Flight colours is no longer a standalone SCOPE_ALL section). 216 - 1
# = 215, recomputed directly against the real on-disk check(...) call
# count at execution time (215/215 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 215
# 21-07-PLAN.md Task 1 (D-13/D-14, Pitfall 2): +3. calendar_connect_
# section()/calendar_disconnect_section() are retired outright and
# merged into ONE calendar_group() returning a single .page-section
# plus a data-only disconnect-form sibling fragment; every check that
# used to call either retired function directly, or that relied on
# Calendar rendering on the legacy SCOPE_ALL scope (removed from
# `builders` there for the identical HTML-forms-can't-nest reason
# Theme's own entry was removed in 21-05), is retargeted in place with
# no count change. Three new checks: exactly one Calendar page-section
# on the Display scope in both states; no <form> nested inside another
# across all four of calendar_group()'s own distinguishable states; the
# two new short button-text constants (Replace/Disconnect) are each a
# contiguous substring of 21-UI-SPEC.md. 215 + 3 = 218, recomputed
# directly against the real on-disk check(...) call count at execution
# time (218/218 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 218
# 21-07-PLAN.md Task 2 (D-14/R-10): +1. The masked feed-URL line
# (host + "…", via the new _masked_calendar_url() helper reading
# calendar_rules.configured_calendar_url(state_dir) — the one call site
# in this module that reads a stored calendar secret back for display)
# is folded into calendar_group()'s own connected branch. The two
# existing secret-leak checks (render-function and real-served-HTTP-
# bytes) are EXTENDED in place, not replaced: both now assert the
# masked host + ellipsis fragment DOES appear while the token, path,
# query-parameter name and whole raw URL still never do — no count
# change for either. One new check: a hostile/unparseable stored value
# ("not a url", the empty string, a javascript: URI) renders no masked-
# URL line at all and raises nothing. 218 + 1 = 219, recomputed
# directly against the real on-disk check(...) call count at execution
# time (219/219 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 219
# 21-07-PLAN.md Task 3 (D-13/R-08/Pitfall 2): +1. Both Calendar-card
# fusion CSS rules (.page-section:has(+ .calendar-disconnect-form),
# .calendar-disconnect-form) are deleted from style.css, and the now-
# empty @supports selector(:has(*)) block that used to hold the first
# of the two is deleted outright — the whole-file pinned block count
# (_strong_selected_treatment_is_keyed_to_the_live_checked_radio, this
# file's own history comment at lines ~172/~215) moves from 2 to 1,
# retargeted in place with no count change. One new check: neither
# retired selector appears anywhere in style.css. 219 + 1 = 220,
# recomputed directly against the real on-disk check(...) call count
# at execution time (220/220 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 220
# 22-01-PLAN.md Task 2 (D-01/B1): +1. Two existing checks were retargeted
# in place, not deleted (the dirty-section-attr/forbidden-syntax check
# now also pins B1's own delegation fix - no surviving
# form.addEventListener("change" registration, document-level delegation
# gated on e.target.form === form; the style.css fallback-attr check now
# requires BOTH .dirty-ready and .dirty-shown in the fallback-hide
# selector, and that neither the old .js-gated nor the old
# single-marker .dirty-ready-only selector survives). One new check:
# dirty-state.js's first dirty-shown occurrence comes after both its
# first dirty-ready occurrence and its bar.hidden = false branch. 220 + 1
# = 221, recomputed directly against the real on-disk check(...) call
# count at execution time (221/221 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 221
# 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): display_group() and its three
# direct-call checks (markup shape checked/unchecked, the locked caption,
# the D-09 prefill default) are deleted outright (-3); the CSS
# cross-file guard for display_group() is deleted too (-1, it tests a
# retired function, not a live behaviour); the three-shapes handle_post()
# check is retargeted in place (absent now means unchanged, not False —
# net 0, same check, new meaning); two new checks land: a whole-page
# no-checkbox-anywhere regression guard (+1) and the named T-22-16
# theme-only-save four-starting-combination regression guard (+1).
# 221 - 3 - 1 + 1 + 1 = 219; several other pre-existing checks were
# retargeted in place (count-shaped assertions repaired per this plan's
# own interfaces block: the theme-status count 6->5, the
# data-dirty-section count 6->5 at both its call sites, the six-entry
# document-order list losing "Display", the nested-modifier floor 5->4,
# the <h2> order list losing "Screen on / off", the suffix-check loop
# losing QUIET_HOURS_SECTION_CAPTION) with no net count change each.
# A further new check pins D-09's no-JS floor at THIS plan's own commit
# (+1, 22-RESEARCH.md Pitfall 4). Re-derived directly against the real
# on-disk check(...) call count at execution time (219/219 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 219
# 22-05-PLAN.md Task 2 (D-04): +4. Three branch checks (due/held/unknown)
# pin the Quiet hours caption and the post-save flash reading the SAME
# one computed delay sentence on one request, plus one repository-wide
# source scan proving none of the three retired delay wordings survives
# anywhere under companion/ or server/ (excluding this file's own
# test_*.py harnesses). The three-shapes handle_post()/live-save-round-
# trip checks touched by the FLASH_KEY_SAVED template change are
# retargeted in place, no net count change. 219 + 4 = 223, recomputed
# directly against the real on-disk check(...) call count at execution
# time (223/223 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 223
# 22-10-PLAN.md Task 1 (X6/T10/T12/C1): +4. One check pins the single
# chip density across all four Display grids plus the one-per-grid swatch
# legend; one pins the "Current" badge's server-rendered, translated
# data-current-label on exactly the --selected elements (EN and FR); one
# pins T12's global-label-margin reset beside C1's later, higher-
# specificity non-serif legend override (with bare `legend` still in the
# shared serif selector); one pins the rules add-form as a left-aligned,
# centre-aligned ROW. Two existing count-shaped assertions are RETARGETED
# in place, no net count change from either: the departures grid's
# "plain class" assertion inverts to "no plain grid survives", and the
# quiet-marker check swaps `content: "Current"` for `content:
# attr(data-current-label)` (comment-filtered, so the rule's own
# four-point justification prose survives the grep). 223 + 4 = 227,
# recomputed directly against the real on-disk check(...) call count at
# execution time (227/227 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 227
# 22-10-PLAN.md Task 2 (B9/B14/B15/B7/C3): +2. One check pins B14's
# `lang` attribute plus the visible normalised-24h sibling on both time
# inputs, in both languages, and that the value was not smuggled into a
# placeholder or a title instead; one pins B9's zero-basis runway card
# (with `.runway-row` still wrapping for its second consumer, the
# quiet-hours preset row), B15's content-width left-aligned calendar
# button with its accent kept, and B7/C3's active-segment hover restore
# at the register's own 12% accent wash. The form="settings-form"
# assertion the new `lang` attribute sits inside is RETARGETED in place,
# no net count change. 227 + 2 = 229, recomputed directly against the
# real on-disk check(...) call count at execution time (229/229 pass),
# not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 229
# 22-10-PLAN.md Task 3 (B8/B17): +2. One check pins "Send a test" inside
# the Notifications card, attached to an EMPTY sibling <form> by the
# cross-DOM form= idiom's fifth consumer, with no control left between
# two cards and the form's own action untouched; one pins the
# wake-interval field's label-above-control shape, its sibling unit, and
# the content-fit 8ch/96px rule that declares no height (so the 44px
# touch-target floor is untouched) and is placed to actually beat the
# phase-18 `width: 100%` rule rather than merely follow it. Two existing
# markup assertions are RETARGETED in place for the input's new id=, no
# net count change. 229 + 2 = 231, recomputed directly against the real
# on-disk check(...) call count at execution time (231/231 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 231
# 22-10-PLAN.md Task 3 (D-06/B16/CFG-29): +1 — the Calendar status
# detail gains a singular form, so a feed holding exactly one flight
# never reads "1 upcoming flights". 22-08-PLAN.md found this string and
# deliberately left it because that plan does not own config_page.py;
# this plan does. 231 + 1 = 232, recomputed directly against the real
# on-disk check(...) call count at execution time (232/232 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 232
# 22-15-PLAN.md Task 1 (T2/T6/T15): +1 — one structural scan covering
# all three cascade/box-model defects this harness can see from the
# stylesheet source: the Disconnect control's element-qualified (0,1,1)
# selector placed after the primary rule (with the primary rule's own
# specificity intact and no :where() shortcut), zero 2px borders
# anywhere in the file with all three selectable surfaces on a constant
# 1px edge plus an inset accent ring, and summary joining the global
# focus-visible floor beside a selected-card focus ring that lives
# inside the ONE feature-query block. Four PRE-EXISTING clauses in the
# two selected-state checks above were retargeted in place for T6 (2px
# border -> constant border + inset ring; "clears the shadow" -> "must
# not clear the shadow"), each strictly narrower than what it replaced
# and each contributing nothing to this count. 232 + 1 = 233,
# recomputed directly against the real on-disk check(...) call count at
# execution time (233/233 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 233
# 23-06-PLAN.md Task 2 (D1/CFG-35): +2 — the Display scope joins the
# refresh loop D1 puts on Home and Health. One check pins the line it
# renders as layout.freshness_line_html()'s own output verbatim (one
# builder, three call sites), exactly one data-loaded-at and one
# data-refresh-pill, the page key on <body>, and the degrade for a
# caller with no render instant: no marker at all rather than an element
# carrying an invented one. One pins what the loop must never touch —
# no Display swap region may name a form, a dirty marker or a save
# control, and the settings form, its cross-DOM form= attachment and the
# fallback Save must all still render, with the freshness line above
# them in the header. That second one is 22-01/B1 kept closed: a swap
# landing on this page's form is the P0 Phase 22 existed to fix.
# 233 + 2 = 235, recomputed directly against the real on-disk check(...)
# call count at execution time, not trusted from arithmetic alone.
# 23-07-PLAN.md Task 2 (D2/CFG-36, X1/D-04): +2. One pins that the
# Diagnostic LED group renders exactly ONE control — a server-rendered
# role=switch whose aria-checked is the stored value in both directions,
# with no input[name="led_enabled"] checkbox surviving beside it. One
# pins its cross-DOM form: an EMPTY sibling of #settings-form carrying
# the inverted posted state, placed outside the settings form on Device
# and not rendered at all on Display. The eight-combination absent-field
# guard was EXTENDED in place rather than duplicated, so it contributes
# nothing to this count. 235 + 2 = 237, recomputed by RUNNING.
EXPECTED_CHECK_COUNT = 237
# 23-09-PLAN.md Task 1 (D3/CFG-32): +1 — the save bar's entrance, and
# every decision that made the bar what it is asserted to have survived
# it in the same check: an animation (not a transition out of display:
# none, which would animate only where @starting-style is supported)
# built from transform and opacity on var(--motion-fast) with no fill
# mode, declaring no size, box or display value anywhere in its
# keyframes; the [hidden] override still hiding by display: none, after
# the base rule, on a base rule that still declares display — B1's own
# collision class, asserted rather than reasoned about; and the z-index
# declared at both breakpoints, the fit-content width, the resting
# shadow and BOTH of T7's MEASURED clearance figures unchanged.
# 237 + 1 = 238, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 238
# 23-09-PLAN.md Task 2 (D3/CFG-32, closing T14's deferred label): +1 —
# the in-flight word, and the argument that makes relabelling a
# submitter safe. The word is a server-rendered, translated data-*
# attribute on the same bar element the five connector words already
# ride on, with a byte-identical English fallback in dirty-state.js; the
# relabel runs only for a <button> carrying no name, because a control
# with no name contributes no entry to the form data set at all and an
# <input type="submit">'s label IS its submitted value; it writes
# textContent and never `value`, never `disabled` (submit-guard.js owns
# the one disable in the app) and never preventDefault. The same check
# asserts no companion/static/*.js reaches for client storage, on
# comment-stripped source — a "Saved" flag carried across the save's own
# navigation is precisely what would have introduced the first one.
# 238 + 1 = 239, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 239
# 23-10-PLAN.md Task 2 (D3/CFG-32): +1 — the live theme preview
# crossfades rather than cuts, held as the same cross-file DOM contract
# the dirty-state.js checks above already use: one class literal written
# out here, declared in style.css and driven from theme-preview.js, with
# neither file importing the other. The mechanism must be event-driven
# (transitionend plus the image's own load/error) and never timed — a
# timed crossfade lets the swap and the fade drift apart and the preview
# settles on whichever won, which is the spoofing disposition T-23-38
# names. T8's window.SkyPaneLivePreview.refresh() is asserted to survive
# in the same check, because Cancel's restore has to come through the
# crossfade rather than around it.
# 239 + 1 = 240, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 240
# 25-03-PLAN.md Task 1 (CFG-47): +4 — the schematic Orly runway map. One
# check that the drawing follows device_config.RUNWAY_IDS and nothing
# else (proved by adding a fourth entry to the registry alone and
# demanding a fourth radio AND a fourth strip on every map); one that
# every strip's bearing is DERIVED from the designator in its own
# registry label rather than pinned, including the id-first trap that
# would draw Orly's ADP-numbered "3" at 030 while its label says 07/25,
# a non-reciprocal pair refused, and T-25-03-D's stated fallback for an
# entry that parses as nothing; one that the emitted markup carries no
# colour literal, gives every shape a paint route, is aria-hidden with
# an explicit size route, and escapes registry text (T-25-03-B); and one
# that the CONTROL is untouched — same radiogroup ids, nothing marked
# with nothing selected, and the three photographs still rendered from
# the session-gated route and still on disk.
# 240 + 4 = 244, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 244
# 25-03-PLAN.md Task 2 (CFG-47/CFG-52): +1 — the map's paint, asserted as
# one thing because the parts fail together. Every class the EMITTED
# markup carries resolves to a real selector (scanned off the markup, not
# off a constant list, with a boundary lookahead so one class is never
# reported as resolved by a longer one's rule); every colour comes from a
# theme token so both themes are correct from one rule; the max-width/
# height pair that keeps an intrinsic 64px drawing inside a ~54px card at
# the 360px floor is declared; the transition sits on the base rule and
# spends an existing motion token; the live selected strip JOINS the ONE
# feature query with its no-:has() fallback outside it declaring the
# IDENTICAL paint; no accent appears anywhere in the component; and the
# @keyframes and prefers-reduced-motion counts are pinned at the
# baselines this plan measured before touching the file.
# 244 + 1 = 245, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 245
# 25-04-PLAN.md Task 1 (CFG-48): +1 — the wrapping-midnight arithmetic,
# settled before anything is drawn. 23:00→07:00 is 480 minutes and
# 07:00→23:00 its 960-minute complement (the pair, because 480 alone
# passes against an implementation that always returns the shorter arc);
# 00:00→00:01 and 23:59→00:00 are both 1; the drawn sweep is the returned
# minute count over a lattice of pairs rather than a second computation;
# the span's LENGTH is reconstructed from what
# server.device_config.seconds_until_quiet_hours_end() has left at a
# shared instant, so the dial and the server cannot drift into two
# wrapping-window arithmetics; equal ends is the zero-width window that
# function's own docstring calls never-active, asserted against it at
# five instants; and every unparseable input — including "99:99", which
# the shape regex alone accepts — returns the render-nothing signal
# rather than raising (T-25-04-C) or fabricating a zero.
# 245 + 1 = 246, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 246
# 25-04-PLAN.md Task 2 (CFG-48/CFG-52): +3 — the server-drawn ring, above
# the unchanged inputs. One check recomputes the arc from the ATTRIBUTES
# THE SERVER EMITTED (a third of the emitted circle for 23:00→07:00 and
# two thirds for its complement, a dash pattern that adds up to that
# circle's own circumference, and a rotation of a quarter turn plus the
# window's own start about its own centre — because an eight-hour arc
# drawn from the wrong hour is the same length and a different window),
# plus the readout against both the times and the duration at once, the
# absence of any role="status"/aria-live region on the card (CFG-52), the
# no-window floor (the day ring still draws, the arc and the words do
# not) and T-25-04-B. One check holds the card's four controls as an
# ADDITION: both time inputs keep every locked attribute and are never
# disabled, B14's visible 24h sibling still renders beside each, the
# three presets keep the data attributes dirty-state.js writes through,
# the one caption keeps its computed delay sentence, the order is
# caption → ring → presets → Start → End, and the arc echoes the
# SUBMITTED window on a rejected save (D-07). One check holds the paint:
# every emitted class resolves to a real boundary-anchored selector,
# every shape has a class, an explicit fill="none" and a stroke width,
# the canvas has viewBox/intrinsic size/aria-hidden/focusable, nothing is
# coloured in Python, each rule paints from a theme token, no accent
# appears anywhere, and no rule declares stroke-width in CSS where it
# would beat the derived presentation attribute.
# 246 + 3 = 249, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 249
# 25-04-PLAN.md Task 3 (CFG-48/CFG-52): +2 — the two handles. One check
# holds them as a LAYER: both are real <button type="button"> sliders
# inside 25-01's .js gate and nowhere else (asserted in BOTH directions —
# every element carrying the wrapper attribute carries the gate class
# itself, AND every element carrying the handle attribute is inside a
# wrapper, which a wrapper-only scan is blind to); each announces through
# aria-valuetext in its own input's HH:MM rather than a minute count, and
# the two agree; each wrapper carries layout's own steering attributes
# including the clock codec and is painted at the fraction its input's
# value implies; --value-fraction is pinned in all three files it travels
# through, because it deliberately has no Python constant; the
# aria-valuetext token is not one of the format artefacts the i18n
# harness scans French renders for (it was "{}" and had to stop being);
# and an end that does not parse gets no handle. One check holds the
# geometry: the stylesheet's dial width and handle radius equal the
# emitter's own constants, the two shared rules keep the source order
# that makes the absolute `position` win at equal specificity, both
# stacked layers are pointer-transparent while the handle is not, the
# transform reads both custom properties, and no z-index re-decides the
# document-order overlap rule.
# 249 + 2 = 251, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 251
# 25-05-PLAN.md Task 1 (CFG-49): +3 — D18's two gauges, and not one of
# the three asserts that they RENDER. One holds what they may CLAIM: the
# freshness sentence is a BOUND ("at most", rounded UP, because "at most
# 1 min" is FALSE for a 90-second cadence) naming the same whole minutes
# the interval implies at both ends of the configured band; the battery
# sentence prints an absolute figure ONLY when companion/battery.py's own
# estimate supports one — recomputed from the estimator rather than
# restated, singular and plural both, and the fixture is checked to
# actually produce a figure first or the clause would be vacuous — and
# renders the NAMED "not enough history yet" state with no digit anywhere
# in it for a RISING series (the device was charged), a one-day span and
# an empty one. One is the source scan: no days-remaining arithmetic
# anywhere under companion/pages/, asserted over NAME tokens so that
# reading the estimator's own key back out of its dict (a STRING) is the
# one permitted shape, plus the qualified-call rule and the "#" quantity
# mark. One holds that all of this is an ADDITION: across six argument
# shapes the <input type="number"> is byte-identical to its pre-plan
# output — including the value-attribute guard's two directions, which
# matter more here than on any other field, because an out-of-range value
# on a native numeric input blocks submission of the ENTIRE Settings form.
# 251 + 3 = 254, re-derived by RUNNING (254/254).
EXPECTED_CHECK_COUNT = 254
# 25-05-PLAN.md Task 2 (CFG-49/CFG-52): +2 — the gated range and the
# seam it shares with the phase's one script. One holds what the range
# may never become: it carries NO name (a named range would post a
# second value for the same setting and the last to arrive would win,
# silently), no role="slider" on top of an element that already is one,
# bounds read from server.device_config rather than restated, a step
# equal to the minute both gauges speak in, an accessible name of its
# own, an aria-describedby pointing at the gauges, and no rendering at
# all either outside 25-01's gate or without a saved interval to start
# from — a range with no value attribute sits at the midpoint of its own
# band, which is a number nobody chose and which one drag would save.
# One pins the readout seam from BOTH sides, because a rename on either
# side alone is a gauge that is correct at load and stale for ever
# after, which no comparison against a rendered page would notice: every
# attribute named in both files, the same CEILING in both (a floor would
# print "at most 1 min" for a 90-second cadence, which is false), all
# three gesture listeners standing aside for a wrapper holding a native
# mirror, the relative clause rendering EMPTY at the saved value, and —
# the honesty clause, made structural — no readout template containing
# the days wording at all, so a script that only substitutes into
# templates cannot invent a figure the server declined to state.
# 254 + 2 = 256, re-derived by RUNNING (256/256).
EXPECTED_CHECK_COUNT = 256
# 25-06-PLAN.md Task 2 (CFG-50): +2 — D5's theme carousel, and neither of
# the two is "a carousel renders". One asserts that NOTHING WAS FORKED: a
# source scan of config_page.py finds exactly one function emitting a
# chip <label> carrying data-preview-src (the attribute theme-preview.js
# reads off a chip to swap the live preview, so a second renderer either
# copies it and is caught, or silently breaks the preview for its own
# chips), the strip keeps every class and attribute it already had and
# gains the id its pagers name, it holds exactly len(THEME_IDS)
# visually-hidden form-associated radios named `theme` in registry order
# — ONE set, never the two that would put two visibly-disagreeing copies
# of one setting in one form — no display:none appears anywhere on the
# card, the swatch legend still renders AFTER the element carrying
# role="radiogroup", and exactly one of the card's four grids is
# converted. One asserts the dots row is aria-hidden, reuses the chips'
# own swatch geometry rather than a second set of numbers, carries one
# dot per theme in registry order painted from the registry's own
# palette with more than one colour among them, and carries no
# selected-state modifier at all; plus the six layout declarations the
# strip needs and the two-part grid-blowout fix, with
# .theme-chip--compact still declaring no selected-state rule of any
# kind.
# 256 + 2 = 258, re-derived by RUNNING (258/258).
EXPECTED_CHECK_COUNT = 258
# 25-06-PLAN.md Task 3 (CFG-50): +1 — the disclosure and the two pagers.
# It answers the duplication question on the WHOLE rendered Display page
# rather than on the card: exactly len(THEME_IDS) radios named `theme`,
# so the strip and the full grid are provably one set and the page can
# never show one setting in two places that disagree (T-25-06-B). It
# pins the disclosure as a native <details>/<summary> and asserts NO
# <dialog> anywhere, because a dialog has no way to open without script
# and eighteen themes behind one is eighteen themes behind a dead
# control. It pins the disclosure BEFORE the strip, which is not a
# preference: the stylesheet reaches the strip through an
# adjacent-sibling [open] rule that only matches in that order. It pins
# both pagers inside 25-01's gate and zero pager markup outside it, each
# with a real aria-label (they draw their arrow in CSS and have no text
# of their own) and an aria-controls naming the strip — which is also
# how theme-preview.js finds the element to scroll, so one contract
# rather than two. And it asserts the script registers NO key listener
# and calls NO preventDefault at all, because a pager capturing an arrow
# key would take the native radiogroup selection away from the
# scripts-blocked path that depends on it.
# 258 + 1 = 259, re-derived by RUNNING (259/259).
#
# 27-02-PLAN.md Tasks 2-3 (CFG-62): +1 — the pair seam's own markup
# check (_the_pair_seam_publishes_both_handles_onto_the_shared_ancestor).
# The two readout-structure fixes inside existing checks (the at-rest
# byte-identical text and the D-07 echo, both narrowed to survive the
# caption's new three-child shape) add no new check of their own.
# 259 + 1 = 260, re-derived by RUNNING (260/260).
#
# 27-03-PLAN.md Task 1 (CFG-64): +1 — the source-and-render proof that
# the native submit's emission is unconditional
# (_the_native_submit_is_emitted_unconditionally_on_every_render).
# 260 + 1 = 261, re-derived by RUNNING (261/261).
#
# 27-04-PLAN.md (D-04/CFG-63): the dirty save bar is retired outright.
# Deleted: _render_dirty_bar_is_sibling_of_form_last_on_page (-1),
# _the_save_control_says_what_it_is_doing_without_changing_what_it_posts
# (-1, retargeted into a new check below rather than a bare delete),
# _dirty_state_js_dirty_shown_marker_set_only_inside_update_bar (-1),
# _dirty_state_js_sets_dirty_ready_only_after_bar_guard (-1),
# _style_css_gives_the_dirty_bar_an_entrance_and_keeps_every_decision_
# that_made_it (-1, retargeted into a new check below rather than a bare
# delete). Retargeted in place (no count change):
# _dirty_state_js_references_dirty_section_attr_and_has_no_forbidden_
# syntax, _style_css_carries_section_caption_and_restyled_fixed_dirty_
# bar, _dirty_state_js_still_has_no_network_or_timer_sinks,
# _dirty_state_js_beforeunload_guard_reuses_count_differences. Added:
# _save_status_region_sits_beside_the_heading_empty_and_announcing (+1),
# _the_save_status_region_carries_both_translated_words_and_no_script_
# holds_client_state (+1, the retarget of the deleted relabel check),
# _skypane_bar_arrive_keyframes_survive_unreferenced (+1). Net: 261 - 5
# + 3 = 259, re-derived by RUNNING (259/259).
EXPECTED_CHECK_COUNT = 259

# 27-05-PLAN.md Task 3 (CFG-66): CFG-47's schematic runway map RETIRED.
# Removed, named: _runway_map_is_drawn_from_the_registry_never_a_typed_
# list, _runway_strip_bearings_come_from_the_designators,
# _runway_map_paint_resolves_and_joins_the_one_feature_query (-3).
# Mutated in place (map-only assertion dropped, non-map subject kept,
# no count change): _runway_map_paints_through_classes_and_announces_
# nothing_twice -> _runway_fieldset_escapes_a_hostile_registry_label;
# _the_map_changed_the_presentation_and_not_the_control ->
# _the_controls_semantics_and_the_photographs_survive_the_map_s_removal.
# Net: 259 - 3 = 256, re-derived by RUNNING (256/256).
EXPECTED_CHECK_COUNT = 256

# 27-06-PLAN.md Task 1 (CFG-65): +1 — the title-form inventory check
# (_title_form_inventory_classifies_every_h2_text_heading_on_both_routes),
# reproducing 27-01-SUMMARY.md's 7/3/2 browser count server-side and
# stating the Outcome-2 conclusion before any markup is touched. Net:
# 256 + 1 = 257, re-derived by RUNNING (257/257).
EXPECTED_CHECK_COUNT = 257

# 27-06-PLAN.md Task 2 (CFG-65): +1 — Outcome 2 found no markup to
# convert, so this is the substitute for "the check that proves the
# conversion happened": the source-level "zero card builder ever calls
# section_intro_html()" guard
# (_no_card_builder_function_ever_calls_section_intro_html). Net: 257 +
# 1 = 258, re-derived by RUNNING (258/258).
EXPECTED_CHECK_COUNT = 258

# 27-06-PLAN.md Task 3 (CFG-67): +3 — one check per shortened region
# (the wake-interval caption, the two wake gauges combined, the Quiet
# hours paragraph), each proving "shorter than 27-01-SUMMARY.md's own
# baseline" and, where the honesty contract or the live delay sentence
# applies, the refusal/survival — on the SAME reading, in both
# languages. Net: 258 + 3 = 261, re-derived by RUNNING (261/261).
EXPECTED_CHECK_COUNT = 261

# 27-07-PLAN.md Task 1 (CFG-68): +1 — the page-wide no-duplicate-id
# check (_the_rendered_settings_page_carries_no_duplicate_id), the proof
# THEME_CAROUSEL_STRIP_ID's required-argument fix actually closes the
# trap rather than merely relocating it. Net: 261 + 1 = 262, re-derived
# by RUNNING (262/262).
EXPECTED_CHECK_COUNT = 262

# 27-07-PLAN.md Task 3 (CFG-70): +1 — the swatch-legend relationship
# check (_the_swatch_legend_names_as_many_things_as_the_registry_
# carries), which computes its expected label count from the registry
# at check time rather than restating THEME_CHIP_SWATCH_LEGEND's own
# literal. Net: 262 + 1 = 263, re-derived by RUNNING (263/263).
EXPECTED_CHECK_COUNT = 263

# 28-03-PLAN.md Task 3 (CFG-73 Bug A): +1 — the quiet-dial readout's own
# server-render contract check
# (_the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages),
# proving both endpoint spans carry the readout-scoped clock-format
# attribute and the duration span carries a non-empty value for every
# one of layout.DURATION_ATTRS, in both shipped languages. Net:
# 263 + 1 = 264, re-derived by RUNNING (264/264).
EXPECTED_CHECK_COUNT = 264

# 28-04-PLAN.md Task 2 (CFG-72): +1 — the cheap structural guard
# (_device_scope_wraps_all_four_settings_cards_with_the_nested_modifier),
# asserting the Device scope's rendered output wraps all four of its
# settings cards with the --nested modifier and carries zero unmodified
# settings-card wrappers. Task 1's own two edits (the D-12 section-intro
# check retargeted, and the title-form inventory reconciled) both
# retargeted EXISTING check() calls in place — neither is a new
# registration, so neither moves this count. Net: 264 + 1 = 265,
# re-derived by RUNNING (265/265).
EXPECTED_CHECK_COUNT = 265


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Same rationale as companion/test_companion_app.py's own copy: the
    end-to-end check below needs to see the real 303 and its Location
    header (to follow the save redirect by hand), not have it silently
    auto-followed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
    """Minimal stdlib HTTP client, mirroring
    companion/test_companion_app.py's own http_request()."""
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Owns the companion/app.py subprocess lifecycle — structurally
    identical to companion/test_companion_app.py's own Harness class.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None

    @staticmethod
    def _pick_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
        finally:
            s.close()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def state_path(self, *parts):
        return os.path.join(self.tmpdir, *parts)

    def start(self):
        env = dict(os.environ)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        stdout_fh = open(self.stdout_path, "w")
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ]
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()

        deadline = time.time() + STARTUP_DEADLINE_S
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(
                    "companion/app.py exited early (code %s) before "
                    "accepting connections:\n%s"
                    % (self.proc.returncode, self.read_stdout()))
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(
            "companion/app.py did not start listening within %.0fs" % STARTUP_DEADLINE_S)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc = None

    def read_stdout(self):
        try:
            with open(self.stdout_path) as fh:
                return fh.read()
        except OSError:
            return ""

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)


def _login(harness, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def _write_device_config(state_dir, theme, tracked_runway, led_enabled=None):
    os.makedirs(state_dir, exist_ok=True)
    doc = {"theme": theme, "tracked_runway": tracked_runway}
    if led_enabled is not None:
        doc["led_enabled"] = led_enabled
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump(doc, fh)


def _python_identifiers(path):
    """Every NAME token in the Python file at `path`, as a set.

    25-05-PLAN.md Task 1 (CFG-49). Tokenised rather than grepped, for
    this project's own standing reason, and the tokeniser gives it for
    free in BOTH directions: a NAME token can never come from a comment,
    a docstring or a string literal, so the prose explaining a rule can
    neither satisfy nor break it — and reading a key back out of a dict
    (`estimate["days_remaining"]`) is a STRING token, which is exactly
    the one shape a page module is allowed to use.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    names = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME:
            names.add(token.string)
    return names


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    # ==================================================================
    # Section 1: unit checks against render()/theme_fieldset()/
    # runway_fieldset()/poll_trigger_section() (Task 1 behavior bullets)
    # and handle_post() (Task 2 behavior bullets), each driven against a
    # temporary state directory and a hand-built ctx dict.
    # ==================================================================

    def _render_shape_theme_chip_grid_runway_cards_groups_and_save_button():
        # merge of origin/main (06.6.4.1.1-05, D-01/D-02/D-08, sketch 004
        # variant B): Theme's own <fieldset>/<legend> radio group is retired
        # outright in favour of a .theme-chip-grid inside the same
        # .theme-status card idiom every other Settings group already uses —
        # the whole rendered Settings page now emits zero <fieldset> and zero
        # <legend> anywhere. This supersedes the pre-06.6.4.1.1-05 version of
        # this check (itself the result of the earlier merge of origin/main's
        # Phase 8 six-colour theme rework), which asserted the OPPOSITE:
        # exactly one <fieldset>, Theme's own.
        #
        # 10-05-PLAN.md Task 3 / 11-03: Quiet hours and Wake interval join
        # Theme/Runway/Diagnostic LED as the fourth and fifth .theme-status-
        # wrapped groups — the count below is 5, not the pre-Phase-10/11
        # value of 3, for that reason alone, not a rename.
        #
        # 12-05-PLAN.md: Display joins as the sixth .theme-status-wrapped
        # group — the count was 6, not 5, for that reason alone, not a
        # rename.
        #
        # 20-11-PLAN.md Task 1 (D-26): Notifications joins as the seventh
        # and last .theme-status-wrapped group on the legacy SCOPE_ALL
        # render — the count was 7, not 6, for that reason alone, not a
        # rename. 21-05-PLAN.md Task 1 (D-06): theme_fieldset() (Theme's
        # own .theme-status-wrapped card) is retired outright, and its
        # replacement (the Frame colours card) only ever renders on the
        # Display scope, never on this legacy SCOPE_ALL render — the
        # count drops from 7 to 6, and this legacy page no longer emits
        # any .theme-chip-grid at all (Calendar's own compact grid and
        # the rules editor's own compact grid, this page's other two
        # former chip-grid sources, are both also gone from SCOPE_ALL,
        # D-06/D-10).
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the count drops from 6 to
        # 5 — display_group() (the Screen on/off card) is retired outright,
        # its own on/off checkbox replaced by nothing on this page (the
        # Frame strip is the only remaining control), so Display no longer
        # contributes a .theme-status-wrapped group here at all.
        ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements anywhere on the page, found one"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements anywhere on the page, found one"
        if rendered.count('class="theme-status"') != 5:
            return False, "expected exactly 5 theme-status-wrapped groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications), got %d" % rendered.count('class="theme-status"')
        if "theme-chip-grid" in rendered:
            return False, "expected no .theme-chip-grid anywhere on this legacy SCOPE_ALL render"
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if "Save settings" not in rendered:
            return False, "expected the 'Save settings' submit button copy"
        return True, ""
    check(
        "render() emits no <fieldset>/<legend> and no .theme-chip-grid on this legacy SCOPE_ALL render "
        "(Theme's card retired outright, D-01/21-05-PLAN.md Task 1 D-06), five theme-status-wrapped "
        "groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications — Display's own card "
        "retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1), three "
        "runway-card labels, and a Save settings submit button",
        _render_shape_theme_chip_grid_runway_cards_groups_and_save_button)

    def _led_group_carries_the_switch_and_its_state_attribute_sequence():
        # quick task 260901-qif used to pin the settings-checkbox label
        # class and the input's name/value/checked attribute sequence.
        # 23-07-PLAN.md Task 2 (D2/CFG-36) RETARGETS it in place: that
        # checkbox is gone and its label class with it, because the LED
        # is now a role="switch" applying instantly over /quick/led.
        # The property this check is actually about — that the control's
        # state-bearing attribute sequence cannot be reordered silently
        # by a later markup edit, since the live-HTTP LED checks further
        # down this file match on it — survives verbatim; only the
        # sequence itself has changed.
        checked_html = config_page.led_group(True)
        unchecked_html = config_page.led_group(False)
        if 'class="settings-checkbox"' in checked_html:
            return False, (
                "the settings-checkbox label is retired with the checkbox it wrapped — the LED "
                "has ONE control now (X1/D-04)")
        for name, rendered, expected_state in (
                ("led_group(True)", checked_html, "true"),
                ("led_group(False)", unchecked_html, "false")):
            expected = 'class="switch" role="switch" aria-checked="%s"' % expected_state
            if rendered.count(expected) != 1:
                return False, "expected %s to carry exactly one %r" % (name, expected)
            if rendered.count('class="switch__thumb"') != 1:
                return False, "expected %s to carry exactly one switch thumb" % name
        if 'aria-checked="true"' in unchecked_html:
            return False, "expected led_group(False) to claim no on state at all"
        return True, ""
    check(
        "led_group() emits the switch and preserves its class/role/aria-checked attribute sequence "
        "in both states, with the retired settings-checkbox label gone (retargeted in place from "
        "the checkbox's own sequence by 23-07-PLAN.md Task 2)",
        _led_group_carries_the_switch_and_its_state_attribute_sequence)

    # ------------------------------------------------------------------
    # 10-05-PLAN.md Task 3: quiet_hours_group() markup/field-order/
    # escaping and render() wiring checks (D-03/D-04, 10-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _quiet_hours_group_markup_no_checkbox_and_time_inputs():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the on/off checkbox this
        # check used to pin (both a checked and an unchecked render) is
        # retired outright — the Frame strip is the ONLY on/off control
        # left, so quiet_hours_group() itself never renders one any more,
        # regardless of the current on-disk quiet_hours_enabled value.
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        if 'name="quiet_hours_enabled"' in rendered:
            return False, "expected no quiet_hours_enabled checkbox anywhere in quiet_hours_group()'s own output"
        if "settings-checkbox" in rendered:
            return False, "expected no .settings-checkbox label — this group has no checkbox left to normalise"
        if 'name="quiet_hours_start"' not in rendered or 'type="time"' not in rendered:
            return False, "expected a type=\"time\" input named quiet_hours_start"
        if 'value="23:00"' not in rendered:
            return False, "expected quiet_hours_start's value to be 23:00"
        if 'name="quiet_hours_end"' not in rendered:
            return False, "expected an input named quiet_hours_end"
        if 'value="07:00"' not in rendered:
            return False, "expected quiet_hours_end's value to be 07:00"
        if "checked" in rendered:
            return False, "expected no checked flag anywhere — there is no checkbox left to carry one"
        if "theme-status__row" in rendered:
            return False, "expected no theme-status__row wrapper — Start/End must stack vertically (10-UI-SPEC.md)"
        if "disabled" in rendered:
            return False, "expected no disabled attribute — the time inputs are never disabled (10-UI-SPEC.md)"
        return True, ""
    check(
        "quiet_hours_group() renders no on/off checkbox at all any more (the Frame strip is the only "
        "control left, 22-05-PLAN.md Task 1 X1/D-04/D-12.1), one type=\"time\" input each for Start/End "
        "with their current values, no theme-status__row, and no disabled attribute",
        _quiet_hours_group_markup_no_checkbox_and_time_inputs)

    def _quiet_hours_group_field_order_heading_caption_start_end():
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        heading_close = rendered.index("</h2>")
        caption_pos = rendered.index("section-caption")
        start_pos = rendered.index('name="quiet_hours_start"')
        end_pos = rendered.index('name="quiet_hours_end"')
        if not (heading_close < caption_pos < start_pos < end_pos):
            return False, (
                "expected heading < caption < start < end in document order, got positions %r"
                % ((heading_close, caption_pos, start_pos, end_pos),))
        return True, ""
    check(
        "quiet_hours_group()'s field order is heading, then caption, then Start, then End, in document "
        "order — the enable checkbox this order used to include is retired outright (22-05-PLAN.md "
        "Task 1, X1/D-04/D-12.1)",
        _quiet_hours_group_field_order_heading_caption_start_end)

    def _quiet_hours_group_escapes_crafted_current_values():
        rendered = config_page.quiet_hours_group('"><script>', "07:00")
        if "<script>" in rendered:
            return False, "expected the crafted current_start value to be escaped, found a raw <script> substring"
        return True, ""
    check(
        "quiet_hours_group() escapes a crafted current_start value — no raw <script> substring reaches the markup",
        _quiet_hours_group_escapes_crafted_current_values)

    # ------------------------------------------------------------------
    # 19-10-PLAN.md Task 3 (D-14/S-04): the three Quiet hours presets -
    # markup shape/values, document position, and the T-19-38 mitigation
    # that handle_post() treats a preset-filled submission identically to
    # a hand-typed one (no new server code path).
    # ------------------------------------------------------------------

    def _quiet_hours_group_renders_exactly_three_button_presets():
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        if rendered.count(config_page.QUIET_HOURS_PRESET_ATTR) != 3:
            return False, (
                "expected exactly three data-quiet-preset occurrences, got %d"
                % rendered.count(config_page.QUIET_HOURS_PRESET_ATTR))
        preset_buttons = re.findall(
            r'<button\b[^>]*%s[^>]*>' % re.escape(config_page.QUIET_HOURS_PRESET_ATTR), rendered)
        if len(preset_buttons) != 3:
            return False, "expected exactly three preset <button> elements, got %d" % len(preset_buttons)
        for button_html in preset_buttons:
            if 'type="button"' not in button_html:
                return False, "expected every preset button to carry type=\"button\", got %r" % (button_html,)
        return True, ""
    check(
        "quiet_hours_group() renders exactly three data-quiet-preset <button type=\"button\"> elements",
        _quiet_hours_group_renders_exactly_three_button_presets)

    def _quiet_hours_group_night_preset_matches_device_config_defaults():
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        expected = 'data-preset-start="%s" data-preset-end="%s"' % (
            device_config.DEFAULT_QUIET_HOURS_START, device_config.DEFAULT_QUIET_HOURS_END)
        if expected not in rendered:
            return False, "expected the Night preset's start/end to equal device_config's own shipped defaults"
        return True, ""
    check(
        "the Night preset's data-preset-start/data-preset-end equal server.device_config's "
        "DEFAULT_QUIET_HOURS_START/DEFAULT_QUIET_HOURS_END",
        _quiet_hours_group_night_preset_matches_device_config_defaults)

    def _quiet_hours_group_workday_preset_carries_expected_times():
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        if 'data-preset-start="08:00" data-preset-end="18:00"' not in rendered:
            return False, "expected the Work day preset to carry data-preset-start=08:00/data-preset-end=18:00"
        return True, ""
    check(
        "the Work day preset carries data-preset-start=\"08:00\" data-preset-end=\"18:00\"",
        _quiet_hours_group_workday_preset_carries_expected_times)

    def _quiet_hours_group_always_on_preset_disables_with_no_time_attrs():
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        always_on_match = re.search(
            r'<button\b[^>]*data-preset-enabled="0"[^>]*>', rendered)
        if not always_on_match:
            return False, "expected exactly one button carrying data-preset-enabled=\"0\""
        button_html = always_on_match.group(0)
        if "data-preset-start" in button_html or "data-preset-end" in button_html:
            return False, "expected the Always-on preset to carry no time attributes, got %r" % (button_html,)
        return True, ""
    check(
        "the Always-on preset carries data-preset-enabled=\"0\" and no data-preset-start/data-preset-end attributes",
        _quiet_hours_group_always_on_preset_disables_with_no_time_attrs)

    def _quiet_hours_group_preset_row_between_caption_and_time_inputs():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): retargeted from "after
        # the .settings-checkbox label" (that label is gone, along with
        # the checkbox it wrapped) to "after the section caption" — the
        # preset row's own locked position relative to the time inputs
        # is otherwise unchanged.
        rendered = config_page.quiet_hours_group("23:00", "07:00")
        caption_pos = rendered.index("section-caption")
        preset_pos = rendered.index(config_page.QUIET_HOURS_PRESET_ATTR)
        time_pos = rendered.index('type="time"')
        if not (caption_pos < preset_pos < time_pos):
            return False, (
                "expected the preset row to fall after the section caption and before the first "
                "type=\"time\" input, got positions %r" % ((caption_pos, preset_pos, time_pos),))
        return True, ""
    check(
        "the preset button row appears after the section caption and before the first "
        "type=\"time\" input (D-14's locked position, retargeted by 22-05-PLAN.md Task 1 now that "
        "the checkbox it used to follow is gone)",
        _quiet_hours_group_preset_row_between_caption_and_time_inputs)

    def _handle_post_preset_filled_submission_treated_identically_to_hand_typed():
        # T-19-38: the presets write into the SAME two fields a hand-typed
        # submission already posts through - this proves handle_post()
        # needs no new code path by driving it with exactly the values
        # the Night preset would write, then confirming the persisted
        # result is identical to the pre-existing hand-typed test above
        # (_handle_post_quiet_hours_checkbox_on_persists_all_three).
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "quiet_hours_enabled": config_page.QUIET_HOURS_CHECKBOX_VALUE,
                    "quiet_hours_start": config_page.QUIET_HOURS_PRESET_NIGHT_START,
                    "quiet_hours_end": config_page.QUIET_HOURS_PRESET_NIGHT_END,
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_start"] != config_page.QUIET_HOURS_PRESET_NIGHT_START:
                return False, "expected the Night preset's start to persist unchanged"
            if on_disk["quiet_hours_end"] != config_page.QUIET_HOURS_PRESET_NIGHT_END:
                return False, "expected the Night preset's end to persist unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() persists a Night-preset-shaped submission (quiet_hours_start/end equal to "
        "device_config's own defaults) exactly as it would a hand-typed value - no new server code path (T-19-38)",
        _handle_post_preset_filled_submission_treated_identically_to_hand_typed)

    def _render_wires_quiet_hours_group_after_led_before_save_button():
        rendered = config_page.render({
            "device_config": {
                "theme": "black", "tracked_runway": "3", "led_enabled": True,
                "quiet_hours_enabled": True, "quiet_hours_start": "22:30",
                "quiet_hours_end": "06:15",
            },
            "poll_cooldown_remaining": 0,
        })
        if 'value="22:30"' not in rendered or 'value="06:15"' not in rendered:
            return False, "expected the current quiet-hours times to appear in the rendered page"
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): inverted — no scope
        # renders a quiet_hours_enabled checkbox any more; the Frame
        # strip is the only on/off control left.
        if 'name="quiet_hours_enabled"' in rendered:
            return False, "expected no quiet-hours enable checkbox anywhere on the rendered page"
        led_heading_pos = rendered.index(config_page.LED_SECTION_HEADING)
        quiet_heading_pos = rendered.index(config_page.QUIET_HOURS_SECTION_HEADING)
        save_button_pos = rendered.index("Save settings")
        if not (led_heading_pos < quiet_heading_pos < save_button_pos):
            return False, "expected the Quiet hours group to render after Diagnostic LED and before the Save settings button"
        return True, ""
    check(
        "render() wires quiet_hours_group() with the saved current values, positioned after Diagnostic LED and before the Save settings button",
        _render_wires_quiet_hours_group_after_led_before_save_button)

    # ------------------------------------------------------------------
    # 11-03-PLAN.md Task 1/Task 2: wake_interval_group() markup/empty-state
    # and render() placement/pre-fill-resolution checks (11-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _wake_interval_group_markup_in_range_value():
        rendered = config_page.wake_interval_group(120)
        if rendered.count('class="theme-status"') != 1:
            return False, "expected exactly one .theme-status wrapper"
        if config_page.DIRTY_SECTION_ATTR not in rendered:
            return False, "expected the wrapper to carry DIRTY_SECTION_ATTR"
        expected_heading = (
            '<h2 class="text-heading">%s</h2>'
            % escape_html(config_page.WAKE_INTERVAL_SECTION_HEADING))
        if rendered.count(expected_heading) != 1:
            return False, "expected exactly one heading %r" % (expected_heading,)
        # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - the
        # caption now carries WAKE_INTERVAL_SECTION_CAPTION_ID (the
        # number input's own aria-describedby target).
        expected_caption = (
            '<p class="text-label section-caption" id="%s">%s</p>'
            % (
                escape_html(config_page.WAKE_INTERVAL_SECTION_CAPTION_ID),
                escape_html(config_page.WAKE_INTERVAL_SECTION_CAPTION)))
        if rendered.count(expected_caption) != 1:
            return False, "expected exactly one caption %r" % (expected_caption,)
        # 22-10-PLAN.md Task 3 (B17): retargeted in place - the input now
        # carries its own id= (the label above it points at that id
        # instead of wrapping the control), which sits between `number`
        # and `name`. The one-input contract this line exists for is
        # unchanged; only the literal it greps had to absorb the id.
        expected_input = (
            '<input type="number" id="%s" name="wake_interval_s"'
            % config_page.WAKE_INTERVAL_INPUT_ID)
        if rendered.count(expected_input) != 1:
            return False, "expected exactly one %r" % (expected_input,)
        if 'min="%d"' % device_config.WAKE_INTERVAL_MIN_S not in rendered:
            return False, "expected min to equal device_config.WAKE_INTERVAL_MIN_S"
        if 'max="%d"' % device_config.WAKE_INTERVAL_MAX_S not in rendered:
            return False, "expected max to equal device_config.WAKE_INTERVAL_MAX_S"
        if 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT not in rendered:
            return False, "expected the locked placeholder text"
        if 'value="120"' not in rendered:
            return False, "expected the matching value attribute"
        if "<fieldset" in rendered:
            return False, "expected no <fieldset> — these sibling groups deliberately don't use one"
        if "<legend" in rendered:
            return False, "expected no <legend> — a <legend> only has accessible-name semantics inside a <fieldset>"
        if "settings-checkbox" in rendered:
            return False, "expected no settings-checkbox class — that class normalises a checkbox, not a numeric input"
        return True, ""
    check(
        "wake_interval_group(120) emits one .theme-status[data-dirty-section] wrapper, the locked heading/caption, one type=\"number\" input with min/max from device_config and the locked placeholder and a matching value, and none of <fieldset>/<legend>/settings-checkbox",
        _wake_interval_group_markup_in_range_value)

    def _wake_interval_group_value_attribute_only_for_in_range_non_bool_int():
        # An out-of-range or wrong-typed value attribute would fail native
        # HTML5 constraint validation and block submission of the entire
        # Settings form, not just this field (11-UI-SPEC.md, T-11-03-03) —
        # this is the direct regression guard for that risk.
        no_value_cases = (None, True, False, "120", 30, 59, 3601, 7200)
        for case in no_value_cases:
            if "value=" in config_page.wake_interval_group(case):
                return False, "expected wake_interval_group(%r) to emit no value attribute" % (case,)
        for case, expected in ((60, 60), (3600, 3600), (120, 120)):
            rendered = config_page.wake_interval_group(case)
            if 'value="%d"' % expected not in rendered:
                return False, "expected wake_interval_group(%r) to emit value=\"%d\"" % (case, expected)
        return True, ""
    check(
        "wake_interval_group() emits a value attribute only for an in-range, non-bool int (None/True/False/a str/30/59/3601/7200 all emit none; 60/3600/120 each emit theirs) — an out-of-range or wrong-typed value would fail native constraint validation and block the whole form",
        _wake_interval_group_value_attribute_only_for_in_range_non_bool_int)

    def _render_places_wake_interval_last_and_resolves_prefill():
        base_ctx = {
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(base_ctx)
        # 21-05-PLAN.md Task 1 (D-06): "Theme" no longer renders anywhere
        # on this legacy SCOPE_ALL page (theme_fieldset() is retired,
        # and its replacement, the Frame colours card, only ever renders
        # on the Display scope) — dropped from this locked-order list.
        headings = [
            "Runway", config_page.LED_SECTION_HEADING,
            config_page.QUIET_HOURS_SECTION_HEADING,
            config_page.WAKE_INTERVAL_SECTION_HEADING,
        ]
        positions = [rendered.index(h) for h in headings]
        if positions != sorted(positions):
            return False, "expected the four remaining settings groups in locked order Runway/Diagnostic LED/Quiet hours/Wake interval, got positions %r" % (positions,)
        if "value=" in rendered.split('name="wake_interval_s"')[1].split(">")[0]:
            return False, "expected no value attribute when neither on-disk nor ctx fallback is present"

        on_disk_ctx = dict(base_ctx)
        on_disk_ctx["device_config"] = dict(
            base_ctx["device_config"], wake_interval_s=180)
        on_disk_ctx["wake_interval_env_default"] = 900
        rendered = config_page.render(on_disk_ctx)
        if 'value="180"' not in rendered:
            return False, "expected the on-disk wake_interval_s to win over the ctx fallback"

        fallback_ctx = dict(base_ctx)
        fallback_ctx["wake_interval_env_default"] = 900
        rendered = config_page.render(fallback_ctx)
        if 'value="900"' not in rendered:
            return False, "expected the ctx fallback to be used when the on-disk value is None"
        return True, ""
    check(
        "render() places Wake interval last in the locked five-group order, resolves no value attribute when neither source is present, prefers an on-disk wake_interval_s over ctx['wake_interval_env_default'], and falls back to the ctx default when the on-disk value is None",
        _render_places_wake_interval_last_and_resolves_prefill)

    # ------------------------------------------------------------------
    # 12-05-PLAN.md Task 1/Task 2's display_group() markup/caption/prefill
    # checks are deleted outright by 22-05-PLAN.md Task 1 (X1/D-04/D-12.1)
    # along with display_group() itself — the Frame strip is now the ONLY
    # on/off control for the screen, so this settings page renders no
    # Screen on/off card, no checkbox and no caption for it at all. What
    # survives (retargeted, not deleted) is handle_post()'s own three-shape
    # resolution ladder for display_enabled below — its meaning changed
    # (absent now means "leave unchanged", D-12.1), not its existence.
    # ------------------------------------------------------------------

    def _no_page_and_no_scope_renders_a_display_or_quiet_hours_on_off_checkbox():
        # X1/D-04: the Frame strip is the ONLY on/off control for Screen
        # and for Quiet hours — pinned across the legacy SCOPE_ALL render
        # and both live scopes, so a regression can never reintroduce
        # either checkbox on any settings page.
        base_ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        legacy = config_page.render(base_ctx)
        display = config_page.render(base_ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(base_ctx, scope=config_page.SCOPE_DEVICE)
        for rendered, name in ((legacy, "legacy"), (display, "display"), (device, "device")):
            if 'name="display_enabled"' in rendered:
                return False, "expected no display_enabled input on the %s render" % (name,)
            if 'name="quiet_hours_enabled"' in rendered:
                return False, "expected no quiet_hours_enabled input on the %s render" % (name,)
        return True, ""
    check(
        "X1/D-04: no settings render (legacy SCOPE_ALL, Display, Device) carries a display_enabled or "
        "quiet_hours_enabled input any more — the Frame strip is the only on/off control for either "
        "setting (22-05-PLAN.md Task 1, superseding 12-05-PLAN.md/10-05-PLAN.md's own checkbox markup)",
        _no_page_and_no_scope_renders_a_display_or_quiet_hours_on_off_checkbox)

    def _no_js_floor_holds_on_display_and_device_after_the_checkbox_removal():
        # D-09's no-JS floor, asserted at THIS plan's own commit rather
        # than deferred to the phase's end (22-RESEARCH.md Pitfall 4):
        # removing two form controls is exactly the kind of wave-3 break
        # that only surfaces at a much later wave if this floor is not
        # checked here. With scripts blocked there is no JS to move a
        # switch — every setting still reachable on a scoped page must
        # have a plain, server-rendered <form> control and a reachable
        # fallback Save button; neither scope needs one for
        # display_enabled/quiet_hours_enabled any more, since the Frame
        # strip's own plain POST forms (companion/layout.py, unaffected
        # by this plan) are what a no-JS visitor uses for those two.
        base_ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        for scope in (config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
            rendered = config_page.render(base_ctx, scope=scope)
            if config_page.STATIC_SAVE_FALLBACK_ATTR not in rendered:
                return False, "expected a reachable fallback Save button on scope=%r" % (scope,)
            if '<form class="config-form"' not in rendered:
                return False, "expected a plain <form method=\"post\"> settings form on scope=%r" % (scope,)
        # A save posted without any script (a plain, URL-encoded POST
        # body, exactly what a no-JS browser submits) still round-trips
        # the Quiet hours schedule — the one control this plan leaves on
        # the Display page for this setting.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-nojs-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"scope": "display", "quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for a plain no-JS Quiet-hours-schedule save, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_start"] != "22:15" or on_disk["quiet_hours_end"] != "06:45":
                return False, "expected the plain POST's schedule to round-trip, got %r" % (on_disk,)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "D-09's no-JS floor holds at this plan's own commit: scripts-blocked Display and Device "
        "renders each carry a reachable fallback Save button inside a plain server-rendered form, "
        "and a plain (no-JS) POST still round-trips the Quiet hours schedule",
        _no_js_floor_holds_on_display_and_device_after_the_checkbox_removal)

    def _handle_post_display_enabled_three_shapes():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1, T-22-16): retargeted from
        # "absent means off" to "absent means leave unchanged" — the
        # regression this whole plan exists to close. The explicit-value
        # and crafted-value shapes are unchanged from before this plan.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            device_config.save_device_config(tmpdir, display_enabled=True)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "black"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for an absent display_enabled, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["display_enabled"] is not True:
                return False, (
                    "expected an absent display_enabled to LEAVE the stored True value unchanged, "
                    "got %r" % (on_disk["display_enabled"],))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"display_enabled": config_page.DISPLAY_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the exact checkbox constant, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["display_enabled"] is not True:
                return False, "expected display_enabled True on disk, got %r" % (on_disk["display_enabled"],)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3", led_enabled=True)
            with open(device_config.device_config_path(tmpdir), "r") as fh:
                doc = json.load(fh)
            doc["display_enabled"] = True
            with open(device_config.device_config_path(tmpdir), "w") as fh:
                json.dump(doc, fh)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"display_enabled": "<crafted>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted display_enabled value, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() resolves display_enabled through all three shapes: absent LEAVES the stored "
        "value unchanged (D-12.1, retargeted from the pre-22-05 absent-means-False bug), "
        "DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key "
        "and leaves a pre-existing device_config.json byte-identical",
        _handle_post_display_enabled_three_shapes)

    def _handle_post_theme_only_save_never_flips_display_quiet_hours_or_led_off():
        # T-22-16 / 22-RESEARCH.md Pitfall 1: THE named regression this
        # check exists to prevent — a settings save that touches only an
        # unrelated field (theme) must never silently switch the screen,
        # quiet hours or the diagnostic LED off, in ANY of their starting
        # combinations.
        #
        # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1) EXTENDS this check
        # rather than adding a sibling beside it. led_enabled is the
        # third flag whose control leaves the settings form, and the
        # asymmetry that made its absence mean False was correct only
        # while its checkbox was still rendered. One check, one place,
        # three flags: a fourth flag joining them later has exactly one
        # obvious place to go, and the three can never drift into
        # disagreeing about what an absent field means.
        for start_display, start_quiet, start_led in (
                (True, True, True), (True, True, False),
                (True, False, True), (True, False, False),
                (False, True, True), (False, True, False),
                (False, False, True), (False, False, False)):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-regression-")
            try:
                device_config.save_device_config(
                    tmpdir, display_enabled=start_display, quiet_hours_enabled=start_quiet,
                    led_enabled=start_led)
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post({"theme": "white"}, ctx)
                if flash_key != config_page.FLASH_SAVED:
                    return False, "expected FLASH_SAVED for a theme-only save, got %r" % (flash_key,)
                on_disk = device_config.load_device_config(tmpdir)
                if on_disk["display_enabled"] is not start_display:
                    return False, (
                        "REGRESSION (T-22-16): a theme-only save flipped display_enabled from %r to %r"
                        % (start_display, on_disk["display_enabled"]))
                if on_disk["quiet_hours_enabled"] is not start_quiet:
                    return False, (
                        "REGRESSION (T-22-16): a theme-only save flipped quiet_hours_enabled from "
                        "%r to %r" % (start_quiet, on_disk["quiet_hours_enabled"]))
                if on_disk["led_enabled"] is not start_led:
                    return False, (
                        "REGRESSION (T-22-16/T-23-25): a theme-only save flipped led_enabled from "
                        "%r to %r — the LED's control is a /quick/led switch now, so its absence "
                        "from a settings body means 'this form never had a way to change it', not "
                        "'the user unticked a box' (D-12.1, 23-07-PLAN.md Task 2)"
                        % (start_led, on_disk["led_enabled"]))
                if on_disk["theme"] != "white":
                    return False, "expected the theme change itself to still persist, got %r" % (on_disk["theme"],)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "REGRESSION GUARD (T-22-16/T-23-25, 22-RESEARCH.md Pitfall 1): a settings save that only "
        "changes the theme leaves display_enabled, quiet_hours_enabled AND led_enabled EXACTLY as "
        "they were, across all eight starting True/False combinations — extended in place from the "
        "two-flag/four-combination version 22-05 landed, never duplicated beside it",
        _handle_post_theme_only_save_never_flips_display_quiet_hours_or_led_off)

    def _every_settings_group_is_named_exactly_once():
        # heading-color-consistency debug session, extended by 06.6.4.1
        # (D-05) and 06.6.4.1.1-05 (D-01): Config carries four settings
        # groups. D-05 already merged Diagnostic LED off its own
        # <fieldset>/<legend> onto the shared <h2 class="text-heading">
        # role Theme/Runway/Poll used. The merge of origin/main (Phase 8)
        # briefly reopened a second <legend> — D-04's read-only-vs-editable
        # fallback took the editable <fieldset><legend>Theme</legend>
        # branch once THEME_IDS held more than one real entry.
        # 06.6.4.1.1-05 closes that gap for good: the multi-theme branch
        # is now the D-01 chip grid inside a .theme-status card, so all
        # four groups are named by the same <h2 class="text-heading">
        # element, at one consistent heading level, with zero <legend>
        # anywhere on the page.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        # 19-11-PLAN.md Task 3 (D-12/A-30): Runway's own <h2> carries an
        # id (the runway row's own aria-labelledby target) - retargeted
        # in place, not a rename of this check's own premise (each group
        # is still named exactly once). 21-05-PLAN.md Task 1 (D-06):
        # "Theme" is retired from this list along with theme_fieldset()
        # and THEME_GROUP_HEADING_ID — its replacement (the Frame
        # colours card) only ever renders on the Display scope, never
        # on this legacy SCOPE_ALL render.
        heading_ids = {
            "Runway": config_page.RUNWAY_GROUP_HEADING_ID,
            # 23-07-PLAN.md Task 2 (D2/CFG-36): the LED heading gained an
            # id for the same reason Runway's has one — it is now the
            # accessible NAME of a control (this group's role="switch",
            # through aria-labelledby) rather than only a heading. The
            # heading role, its level and its text are untouched.
            "Diagnostic LED": config_page.QUICK_LED_LABEL_ID,
        }
        for name in ("Runway", "Diagnostic LED", config_page.POLL_SECTION_HEADING):
            heading_id = heading_ids.get(name)
            if heading_id:
                heading = '<h2 class="text-heading" id="%s">%s</h2>' % (
                    escape_html(heading_id), name)
            else:
                heading = '<h2 class="text-heading">%s</h2>' % name
            if rendered.count(heading) != 1:
                return False, (
                    "expected exactly one %r group heading, got %d"
                    % (heading, rendered.count(heading)))
        if "<legend" in rendered:
            return False, (
                "expected zero <legend> elements anywhere on the page — "
                "Theme's own <fieldset>/<legend> radio group is retired "
                "(06.6.4.1.1-05, D-01)")
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements anywhere on the page"
        # The old label-paragraph shape must not come back alongside
        # Theme's own naming — that would name the Theme group twice.
        if '<p class="text-label">Theme</p>' in rendered:
            return False, (
                "the Theme group is named twice: the superseded "
                "text-label paragraph is still present next to its own naming element")
        return True, ""
    check(
        "all four Config settings groups (Theme/Runway/Diagnostic LED/Poll) are named "
        "exactly once, all via the shared <h2 class=\"text-heading\"> role, with zero "
        "<legend> and zero <fieldset> anywhere on the page (06.6.4.1.1-05, D-01)",
        _every_settings_group_is_named_exactly_once)

    def _render_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): Settings' top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        # 06.6.4.1-07 (D-26): the heading text itself was retargeted from
        # "Config" to "Settings", matching the route rename and the nav
        # label — the page's own on-screen name must agree with both.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if '<h1 class="page-title">Settings</h1>' not in rendered:
            return False, "expected the page_header()-rendered <h1 class=\"page-title\">Settings</h1>"
        if '<h1 class="text-heading">' in rendered:
            return False, "expected no bare <h1 class=\"text-heading\"> heading"
        return True, ""
    check(
        "Settings opens with the shared layout.page_header() component, not a bare <h1>",
        _render_opens_with_shared_page_header)

    def _the_save_status_region_carries_both_translated_words_and_no_script_holds_client_state():
        # 27-04-PLAN.md Task 3 (D-04/CFG-63): SUPERSEDES this check's own
        # pre-27-04 subject (23-09-PLAN.md Task 2's Save-button relabel,
        # D3/CFG-32) wholesale — the relabel, and the Save button it
        # relabelled, are both retired along with the dirty bar itself
        # (dirty-state.js's own header records the full account). What
        # replaces it is the auto-save status region's own two words,
        # tested here the identical way: a server-rendered, translated
        # data-* attribute with a byte-identical English fallback.
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        with open(os.path.join(static_dir, "dirty-state.js")) as fh:
            source = fh.read()

        for attr_const, text_const in (
                (config_page.SAVE_STATUS_SAVING_ATTR, config_page.SAVE_STATUS_SAVING_TEXT),
                (config_page.SAVE_STATUS_SAVED_ATTR, config_page.SAVE_STATUS_SAVED_TEXT)):
            rendered = config_page.render({
                "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
                "poll_cooldown_remaining": 0,
            }, scope=config_page.SCOPE_DISPLAY)
            marker = '%s="%s"' % (attr_const, text_const)
            if marker not in rendered:
                return False, (
                    "expected the save-status region to carry %r — both words belong on the "
                    "same element, the same idiom the retired bar's own words used" % (marker,))
            if attr_const not in source:
                return False, "expected dirty-state.js to read %r off the region" % (attr_const,)
            if ('"%s"' % text_const) not in source:
                return False, (
                    "expected dirty-state.js's English fallback literal for %r to match the "
                    "server constant byte for byte, or a region rendered without the attribute "
                    "says something different from one rendered with it" % (attr_const,))
            try:
                prefs.set_request_prefs(lang="fr")
                fr_rendered = config_page.render({
                    "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
                    "poll_cooldown_remaining": 0,
                }, scope=config_page.SCOPE_DISPLAY)
            finally:
                prefs.set_request_prefs(lang="en")
            fr_word = layout.i18n.t_lang(text_const, "fr")
            if fr_word == text_const:
                return False, (
                    "expected a French entry for %r — every new visible word is a catalogue entry"
                    % (text_const,))
            if ('%s="%s"' % (attr_const, fr_word)) not in fr_rendered:
                return False, "expected a French render to carry the French word for %r" % (attr_const,)

        # NO CLIENT STATE, in any script. The completed state is not
        # persisted client-side at all — the fetch's own 204 IS the
        # confirmation, read once and written straight to the region;
        # carrying a flag anywhere longer-lived would mean browser
        # storage, and this app holds none, on purpose. Measured on
        # COMMENT-STRIPPED source, the way 23-01's own motion guard
        # measures its bans, so a script may still write down WHY it
        # holds no client state without failing the rule.
        for name in sorted(os.listdir(static_dir)):
            if not name.endswith(".js"):
                continue
            with open(os.path.join(static_dir, name)) as fh:
                live = re.sub(r"/\*.*?\*/", "", fh.read(), flags=re.DOTALL)
            live = re.sub(r"^\s*//.*$", "", live, flags=re.MULTILINE)
            for store in ("sessionStorage", "localStorage", "indexedDB"):
                if store in live:
                    return False, (
                        "companion/static/%s reaches for %s — this app holds no client state at "
                        "all, deliberately, and a 'Saved' flag carried across a page's own "
                        "lifetime is exactly the thing that would introduce one" % (name, store))
        return True, ""
    check(
        "the save-status region's two words (SAVE_STATUS_SAVING_TEXT/SAVE_STATUS_SAVED_TEXT) are "
        "server-rendered, translated data-* attributes with byte-identical English fallbacks in "
        "dirty-state.js, and no script anywhere reaches for client storage (27-04-PLAN.md Task 3, "
        "D-04/CFG-63, supersedes the retired Save-button relabel check, 23-09-PLAN.md Task 2/D3/CFG-32)",
        _the_save_status_region_carries_both_translated_words_and_no_script_holds_client_state)

    def _settings_form_carries_config_form_class_hook():
        # D-01 stable class hook: the settings form (POST /config) needs a
        # class attribute so plan 06.3-02's desktop two-column fieldset
        # grid rule (companion/static/style.css's 960px breakpoint) can
        # target it without a brittle attribute selector.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'class="config-form"' not in rendered:
            return False, "expected the settings form to carry class=\"config-form\""
        # 06.6.3-03 (D-03): the form tag also carries data-dirty-form now,
        # the DOM-attribute hook dirty-state.js (06.6.3-01) reads.
        # 06.6.4.1 (D-05): the action is now config_page.SETTINGS_ROUTE
        # ("/settings"), not the old "/config" literal — the single
        # definition of that route lives in config_page, never re-typed
        # here as a literal.
        # quick task 260901-re6: the form tag also carries an id now
        # (config_page.SETTINGS_FORM_ID), interpolated the same way
        # SETTINGS_ROUTE already is — never re-typed as a literal — so
        # the dirty-bar's save button (now a sibling of the form) can
        # associate with it via a `form=` attribute.
        expected_tag = (
            '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
            % (config_page.SETTINGS_FORM_ID, config_page.SETTINGS_ROUTE))
        if expected_tag not in rendered:
            return False, "expected the config-form class, id, data-dirty-form, method=\"post\", and action=%r on the same form tag" % (config_page.SETTINGS_ROUTE,)
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form in render()'s output, got %d" % rendered.count('<form class="config-form"')
        return True, ""
    check(
        "the settings form keeps the stable config-form class hook the desktop two-column fieldset layout targets",
        _settings_form_carries_config_form_class_hook)

    def _save_status_region_sits_beside_the_heading_empty_and_announcing():
        # 27-04-PLAN.md Task 3 (D-04/D-06/CFG-63): SUPERSEDES this check's
        # own pre-27-04 subject (the dirty save bar, a sibling emitted
        # LAST on the page — quick task 260901-re6). The bar and its own
        # placement contract are retired outright along with dirty_bar_
        # html() itself; what replaces it is placed FIRST, immediately
        # after the page's own heading, "beside the form's heading" per
        # that plan's own wording — the opposite end of the page from
        # where the bar used to live.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form>, no duplicate"
        if config_page.SAVE_STATUS_ATTR not in rendered:
            return False, "expected the save-status region's own attribute to appear in render()'s output"
        region_pos = rendered.index(config_page.SAVE_STATUS_ATTR)
        heading_marker = "<h1"
        if heading_marker not in rendered:
            return False, "expected a page heading"
        heading_pos = rendered.index(heading_marker)
        if region_pos <= heading_pos:
            return False, "expected the save-status region to appear AFTER the page's own heading"
        form_pos = rendered.index('<form class="config-form"')
        if region_pos >= form_pos:
            return False, "expected the save-status region to appear BEFORE the settings form, not after it"
        # EMPTY at rest: a region already carrying its saved word on a
        # fresh load would be the same stale-claim defect this phase
        # exists to fix, in a sentence instead of an arc.
        region_start = rendered.index("<p class=\"save-status")
        region_end = rendered.index("</p>", region_start) + len("</p>")
        region_markup = rendered[region_start:region_end]
        if not region_markup.endswith("></p>"):
            return False, "expected the save-status region to render with no text content at rest, got %r" % (region_markup,)
        if 'role="status"' not in region_markup:
            return False, "expected the save-status region to carry role=\"status\""
        if 'aria-live="polite"' not in region_markup:
            return False, "expected the save-status region to carry aria-live=\"polite\", not role=\"alert\" — a failed save's toast, not this region, is the assertive announcement"
        return True, ""
    check(
        "render() places one save-status region beside the page's own heading, before the settings form — EMPTY at rest, carrying role=\"status\" and aria-live=\"polite\" (27-04-PLAN.md Task 3, D-04/CFG-63, supersedes the retired dirty bar's own end-of-page placement check)",
        _save_status_region_sits_beside_the_heading_empty_and_announcing)

    # 21-05-PLAN.md Task 1 (D-06): theme_fieldset() is retired outright —
    # every direct-call test against it (one-radio-per-registry-entry,
    # the single-theme read-only fallback, the multi-theme fallback, the
    # per-theme id/label coverage, and the default-selection doubling
    # across two always-rendered grids) is deleted along with it. The
    # single-theme read-only branch has no replacement in the Frame
    # colours card (a real, multi-theme registry is this app's only
    # shipped shape, and the new card assumes a real radiogroup); the
    # remaining, still-true assertions (one radio per registered theme,
    # each carrying its own id/label; the currently-selected chip is
    # marked) are covered directly against `_frame_colours_card_html()`
    # below.

    def _frame_colours_card_covers_every_registered_theme_with_own_id_and_label():
        ctx = {"colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS}}
        rendered = config_page._frame_colours_card_html(ctx, "white", None, None)
        theme_ids = device_config.THEME_IDS
        if not theme_ids:
            return False, "THEME_IDS is empty - nothing to render"
        for theme_id in theme_ids:
            value_needle = 'value="%s"' % escape_html(theme_id)
            if value_needle not in rendered:
                return False, "expected a radio carrying value=%r, not found in the rendered card" % (theme_id,)
            label_needle = escape_html(device_config.theme_label(theme_id))
            if label_needle not in rendered:
                return False, "expected theme %r's plain label %r as visible text, not found" % (theme_id, label_needle)
        return True, ""
    check(
        "_frame_colours_card_html() renders one radio per registered theme in its departures grid, each "
        "carrying its own registry id as value and its own plain label as visible text (D-06, replacing "
        "the retired theme_fieldset()'s equivalent coverage)",
        _frame_colours_card_covers_every_registered_theme_with_own_id_and_label)

    def _frame_colours_card_default_selects_exactly_the_white_departures_option():
        ctx = {"colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS}}
        rendered = config_page._frame_colours_card_html(
            ctx, device_config.DEFAULT_THEME_ID, None, None)
        white_option_needle = 'value="white" class="visually-hidden" form="%s" checked' % (
            config_page.SETTINGS_FORM_ID)
        if rendered.count(white_option_needle) != 1:
            return False, (
                "expected the White departures chip selected exactly once (expected %r once), got %d"
                % (white_option_needle, rendered.count(white_option_needle)))
        return True, ""
    check(
        "_frame_colours_card_html() rendered with the default theme id marks exactly the White chip "
        "selected in the departures grid (D-06/D-07, replacing the retired theme_fieldset()'s "
        "equivalent coverage)",
        _frame_colours_card_default_selects_exactly_the_white_departures_option)

    def _runway_fieldset_exactly_three_radios():
        rendered = config_page.runway_fieldset("3")
        radio_count = rendered.count('name="tracked_runway"')
        if radio_count != 3:
            return False, "expected exactly 3 runway radios, got %d" % radio_count
        return True, ""
    check(
        "runway_fieldset() emits exactly three runway radio inputs",
        _runway_fieldset_exactly_three_radios)

    def _runway_fieldset_cards_visually_hidden_radio_and_selected_class():
        # D-05, Task 2 Test 3: three .runway-card <label>s, each wrapping a
        # visually-hidden (not display:none) native radio, with only the
        # "3" card carrying runway-card--selected.
        rendered = config_page.runway_fieldset("3", images_available=())
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if rendered.count("runway-card--selected") != 1:
            return False, "expected exactly one runway-card--selected modifier"
        # Polish fix 4 (D-14c): each radio now also carries an explicit
        # form="settings-form" attribute (config_page.SETTINGS_FORM_ID),
        # inserted between class="visually-hidden" and checked.
        if 'value="3" class="visually-hidden" form="%s" checked' % config_page.SETTINGS_FORM_ID not in rendered:
            return False, (
                "expected the selected card's radio to carry class=\"visually-hidden\", "
                "form=\"settings-form\" and checked")
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('class="visually-hidden"') < 3:
            return False, "expected every card's radio to carry the visually-hidden class"
        return True, ""
    check(
        "runway_fieldset('3') renders three selectable cards, each wrapping a visually-hidden radio, with only the '3' card selected (D-05)",
        _runway_fieldset_cards_visually_hidden_radio_and_selected_class)

    def _runway_fieldset_cards_image_rendering_per_card():
        # D-05, Task 2 Test 4: an <img> renders inside exactly the cards
        # named in images_available, none inside any other card.
        rendered = config_page.runway_fieldset("3", images_available=("3", "06-24"))
        if rendered.count("<img") != 2:
            return False, "expected exactly 2 <img occurrences, got %d" % rendered.count("<img")
        if "/runway-image/3.png" not in rendered or "/runway-image/06-24.png" not in rendered:
            return False, "expected <img> src pointing at both supplied runway images"
        if "/runway-image/02-20.png" in rendered:
            return False, "expected no <img> for the runway not in images_available"
        return True, ""
    check(
        "runway_fieldset('3', images_available=('3', '06-24')) renders an <img> inside exactly those two cards, none in the third (D-05)",
        _runway_fieldset_cards_image_rendering_per_card)

    # ------------------------------------------------------------------
    # 27-05-PLAN.md Task 3 (CFG-66): CFG-47's schematic Orly runway map
    # was RETIRED — the drawing came out, the three native radios and
    # the three photographs did not. `_temporary_registry()`/
    # `_runway_entry()` below survive because the escaping check just
    # past them still needs a hostile registry entry to swap in; every
    # check that asserted the map's own classes, geometry or bearing
    # derivation (four of them, plus their `_MAP_STRIP_ATTR` helper) is
    # gone, named in 27-05-SUMMARY.md.
    # ------------------------------------------------------------------

    def _temporary_registry(entries):
        """Swap device_config.RUNWAYS/RUNWAY_IDS for `entries` and put
        them back. A context manager rather than a try/finally at four
        call sites: this fixture mutates a module-level registry every
        other check in this file reads, and one missed restore would
        make an unrelated neighbour fail in a way nobody would trace
        back to here.
        """
        import contextlib

        @contextlib.contextmanager
        def _swap():
            was_runways = device_config.RUNWAYS
            was_ids = device_config.RUNWAY_IDS
            device_config.RUNWAYS = entries
            device_config.RUNWAY_IDS = tuple(entries)
            try:
                yield
            finally:
                device_config.RUNWAYS = was_runways
                device_config.RUNWAY_IDS = was_ids
        return _swap()

    def _runway_entry(label):
        return {"label": label, "tag_text": label, "empty_heading": label}

    def _runway_fieldset_escapes_a_hostile_registry_label():
        # T-25-03-B, MUTATED IN PLACE by 27-05-PLAN.md Task 3 (CFG-66):
        # this check used to also assert runway_map_svg("h") never
        # interpolated the hostile label unescaped, alongside every
        # colour/paint-route/aria/size assertion the now-retired map's
        # own <svg> carried. The map is gone; the registry-text-reaching-
        # the-page threat it was ALSO defending against is not — a
        # runway's plain-text label still renders on this card, so the
        # escaping proof stays, narrowed to the surface that still
        # exists.
        hostile = 'Runway <script>"x"</script> (07/25)'
        with _temporary_registry({"h": _runway_entry(hostile)}):
            rendered = config_page.runway_fieldset("h")
            if "<script>" in rendered:
                return False, (
                    "a registry label containing markup reached the page unescaped")
            if "&lt;script&gt;" not in rendered:
                return False, (
                    "expected the hostile registry label to render escaped, not dropped")
        return True, ""
    check(
        "runway_fieldset() escapes a hostile registry label rather than dropping or "
        "interpolating it unescaped (T-25-03-B, narrowed from the retired map's own "
        "coverage by 27-05-PLAN.md Task 3, CFG-66)",
        _runway_fieldset_escapes_a_hostile_registry_label)

    def _the_controls_semantics_and_the_photographs_survive_the_map_s_removal():
        # MUTATED IN PLACE by 27-05-PLAN.md Task 3 (CFG-66): this check
        # used to be titled "the map changed the presentation and not
        # the control" and additionally asserted that
        # RUNWAY_MAP_THIS_STRIP_CLASS survived a current_runway_id=None
        # render — the one assertion in this function whose subject was
        # the now-retired drawing itself, removed with it. Everything
        # below it is the radiogroup's OWN semantics and the
        # photographs' own presence, neither of which the map's removal
        # may touch, so both stay and both are re-asserted here rather
        # than lost when the check that used to carry them was renamed.
        rendered = config_page.runway_fieldset("3")
        for fragment in (
                'role="radiogroup"',
                'aria-labelledby="%s"' % config_page.RUNWAY_GROUP_HEADING_ID,
                'aria-describedby="%s"' % config_page.RUNWAY_SECTION_CAPTION_ID):
            if fragment not in rendered:
                return False, "expected the row to keep %s" % (fragment,)
        # Nothing selected means nothing marked.
        none_selected = config_page.runway_fieldset(None)
        if "runway-card--selected" in none_selected:
            return False, (
                "current_runway_id=None still marked a card selected")
        if " checked" in none_selected:
            return False, "current_runway_id=None still left a radio checked"
        # The photographs are the map's former neighbour, not its
        # casualty.
        empty = config_page.runway_fieldset("3", images_available=())
        if "<img" in empty:
            return False, "images_available=() still rendered an <img>"
        with_images = config_page.runway_fieldset(
            "3", images_available=device_config.RUNWAY_IDS)
        if with_images.count("<img") != len(device_config.RUNWAY_IDS):
            return False, (
                "expected one <img> per available runway image, got %d"
                % with_images.count("<img"))
        if config_page.RUNWAY_IMAGE_ROUTE_PREFIX not in with_images:
            return False, (
                "expected the session-gated runway-image route to still be the src")
        for runway_id in device_config.RUNWAY_IDS:
            path = os.path.join(HERE, "static", "runway-%s.png" % runway_id)
            if not os.path.exists(path):
                return False, (
                    "%s is gone from disk — the developer objected to the drawn map, "
                    "not to the photographs, and deleting real imagery here would be "
                    "an unrelated, irreversible loss" % (path,))
        return True, ""
    check(
        "the control's own semantics and the photographs survive the map's removal — the row "
        "keeps role=\"radiogroup\" with the same aria-labelledby/aria-describedby ids, "
        "current_runway_id=None marks nothing selected and leaves no radio checked, and the "
        "three runway photographs still render from the session-gated route and still exist on "
        "disk (CFG-66, retitled from CFG-47's retired 25-03-PLAN.md Task 1 check by "
        "27-05-PLAN.md Task 3)",
        _the_controls_semantics_and_the_photographs_survive_the_map_s_removal)

    # ------------------------------------------------------------------
    # 25-04-PLAN.md Task 1 (CFG-48): the wrapping-midnight arithmetic,
    # settled before anything is drawn.
    # ------------------------------------------------------------------

    def _the_quiet_window_wraps_midnight_the_short_way_round():
        """CFG-48 (25-04-PLAN.md Task 1): `quiet_window_span()` goes
        FORWARD from start to end through midnight.

        Asserted AT the boundary rather than near it, because the values
        an `end - start` implementation gets wrong are precisely the ones
        the device ships with: 23:00 to 07:00 is the factory default.
        """
        span_of = config_page.quiet_window_span
        day = config_page.QUIET_WINDOW_MINUTES_PER_DAY
        if day != 1440:
            return False, "expected a 1440-minute day, got %r" % (day,)

        # THE DEFAULT WINDOW, AND THE COMPLEMENT THAT PROVES DIRECTION.
        # Asserting 480 alone passes against an implementation that
        # returns the SHORTER of the two arcs whichever way round it was
        # asked; the complement is what refuses that.
        for start, end, expected in (
                ("23:00", "07:00", 480),
                ("07:00", "23:00", 960),
                ("00:00", "00:01", 1),
                ("23:59", "00:00", 1),
                ("00:00", "23:59", 1439),
                ("12:00", "12:00", 0)):
            span = span_of(start, end)
            if span is None:
                return False, "expected %s→%s to produce a span, got None" % (start, end)
            if span.minutes != expected:
                return False, (
                    "%s→%s is %d minutes forward through midnight, and quiet_window_span() "
                    "returns %d — an `end - start` implementation returns %d here, which is the "
                    "single most likely arithmetic defect in this control"
                    % (start, end, expected, span.minutes,
                       config_page.quiet_window_minute_of_day(end)
                       - config_page.quiet_window_minute_of_day(start)))

        # THE SWEEP IS THE MINUTES, NOT A SECOND COMPUTATION. Asserted
        # over every pair above and a lattice besides, because the defect
        # is a card that prints "8 h" beside an arc covering two thirds
        # of the day, and two agreeing numbers for one case could be a
        # coincidence.
        for start_minute in range(0, 1440, 37):
            for end_minute in range(0, 1440, 53):
                start = "%02d:%02d" % divmod(start_minute, 60)
                end = "%02d:%02d" % divmod(end_minute, 60)
                span = span_of(start, end)
                if span is None:
                    return False, "expected %s→%s to parse" % (start, end)
                if abs(span.sweep_fraction - span.minutes / 1440.0) > 1e-12:
                    return False, (
                        "%s→%s: sweep_fraction %r is not minutes/%d (%r) — the drawn arc and the "
                        "printed duration are two computations and can disagree"
                        % (start, end, span.sweep_fraction, day, span.minutes / 1440.0))
                if abs(span.start_fraction - start_minute / 1440.0) > 1e-12:
                    return False, (
                        "%s→%s: start_fraction %r is not %r"
                        % (start, end, span.start_fraction, start_minute / 1440.0))
                if not (0.0 <= span.sweep_fraction < 1.0):
                    return False, (
                        "%s→%s: sweep_fraction %r left [0, 1)" % (start, end, span.sweep_fraction))
        default_span = span_of("23:00", "07:00")
        if abs(default_span.sweep_fraction - 1 / 3.0) > 1e-9:
            return False, (
                "the default window's sweep is %r turns, not the third of the ring 480 of 1440 "
                "minutes is" % (default_span.sweep_fraction,))

        # AGREEMENT WITH THE SERVER'S OWN AUTHORITY, ON A SHARED CASE.
        # server.device_config.seconds_until_quiet_hours_end() is what
        # actually decides whether the device is inside a wrapping
        # window; this function only draws one. Pinning 480 here and
        # trusting them to stay in step is how two wrapping-window
        # arithmetics drift. So the span's own LENGTH is reconstructed
        # from what the server says is left at a shared instant.
        #
        # BOTH SIDES OF MIDNIGHT, AND THAT IS NOT BELT-AND-BRACES.
        # seconds_until_quiet_hours_end() answers a wrapping window
        # through TWO different branches — one for an instant after the
        # start and before midnight, one for an instant after midnight
        # and before the end — and a probe taken only after midnight
        # leaves the first branch unexercised. Measured: mutating that
        # branch's `timedelta(days=1)` to `days=2` changed nothing here
        # until this clause grew its before-midnight probes.
        #
        # Times are Europe/Paris in mid-January, which is UTC+1.
        for start, end, utc_hm, local_minute in (
                ("23:00", "07:00", (1, 0), 2 * 60),
                ("23:00", "07:00", (22, 30), 23 * 60 + 30),
                ("22:30", "06:15", (23, 0), 0),
                ("22:30", "06:15", (21, 45), 22 * 60 + 45),
                ("01:00", "03:00", (1, 0), 2 * 60)):
            now_utc = datetime.datetime(
                2026, 1, 15, utc_hm[0], utc_hm[1], tzinfo=datetime.timezone.utc)
            span = span_of(start, end)
            remaining = device_config.seconds_until_quiet_hours_end(now_utc, start, end)
            if remaining is None:
                return False, (
                    "expected server.device_config to place local %02d:%02d inside %s→%s"
                    % (local_minute // 60, local_minute % 60, start, end))
            elapsed = (local_minute - config_page.quiet_window_minute_of_day(start)) % 1440
            if remaining != (span.minutes - elapsed) * 60:
                return False, (
                    "the dial and server.device_config disagree about %s→%s: the server has %d "
                    "seconds left at local %02d:%02d, and the dial's %d-minute span with %d "
                    "minutes elapsed implies %d"
                    % (start, end, remaining, local_minute // 60, local_minute % 60,
                       span.minutes, elapsed, (span.minutes - elapsed) * 60))

        # EQUAL ENDS IS ZERO, AND THE SERVER SAYS SO TOO. Its own
        # docstring calls a zero-width window "never active, and that is
        # intentional rather than a bug to 'fix' into an always-active
        # window" — so this is agreement, not a number chosen here.
        zero = span_of("23:00", "23:00")
        if zero.minutes != 0 or zero.sweep_fraction != 0.0:
            return False, (
                "expected equal ends to be a ZERO-length window (the reading "
                "seconds_until_quiet_hours_end() implies), got %r" % (zero,))
        for instant_hour in (0, 2, 12, 22, 23):
            probe = datetime.datetime(
                2026, 1, 15, (instant_hour - 1) % 24, 0, tzinfo=datetime.timezone.utc)
            if device_config.seconds_until_quiet_hours_end(probe, "23:00", "23:00") is not None:
                return False, (
                    "server.device_config reports 23:00→23:00 ACTIVE at local %02d:00, so the "
                    "zero reading above no longer agrees with it — one of the two has changed "
                    "its mind about a zero-width window" % instant_hour)

        # THE RENDER-NOTHING SIGNAL. None, never an exception (T-25-04-C:
        # the Display page renders this) and never a zero, which would
        # draw a real, empty window and claim one is configured.
        for hostile in ("", None, "7:00", "0700", "99:99", "24:00", "23:60", "ab:cd",
                        "23:00 ", 5, True, object(), "<b>23:00</b>"):
            if span_of(hostile, "07:00") is not None:
                return False, (
                    "expected quiet_window_span(%r, '07:00') to be None — the render-nothing "
                    "signal, not a fabricated window" % (hostile,))
            if span_of("23:00", hostile) is not None:
                return False, (
                    "expected quiet_window_span('23:00', %r) to be None" % (hostile,))
            if config_page.quiet_window_minute_of_day(hostile) is not None:
                return False, (
                    "expected quiet_window_minute_of_day(%r) to be None" % (hostile,))

        # ONE PARSE DISCIPLINE. Anything the dial is willing to DRAW, the
        # B14 24h sibling must be willing to PRINT — a value that reaches
        # the arc but not the text is a card whose picture and whose
        # words disagree about what is stored.
        for value in ("00:00", "07:00", "23:59", "12:34", "99:99", "7:00", "", "24:00"):
            if config_page.quiet_window_minute_of_day(value) is not None \
                    and config_page._normalised_time_html(value) == "":
                return False, (
                    "quiet_window_minute_of_day(%r) parses but _normalised_time_html(%r) renders "
                    "nothing — the arc and B14's visible 24h sibling have drifted into two parse "
                    "disciplines" % (value, value))
        return True, ""
    check(
        "the quiet window's span goes FORWARD through midnight — 23:00→07:00 is 480 minutes and "
        "07:00→23:00 its 960-minute complement, 00:00→00:01 and 23:59→00:00 are both 1, the "
        "drawn sweep is the returned minute count and never a second computation, the span's "
        "length is reconstructed from what server.device_config.seconds_until_quiet_hours_end() "
        "has left at a shared instant rather than pinned, equal ends is the zero-width window "
        "that server's own docstring calls never-active, and every unparseable input returns the "
        "render-nothing signal rather than raising or fabricating a zero "
        "(CFG-48, 25-04-PLAN.md Task 1)",
        _the_quiet_window_wraps_midnight_the_short_way_round)

    # ------------------------------------------------------------------
    # 25-04-PLAN.md Task 2 (CFG-48): the server-drawn ring, above the
    # unchanged inputs.
    # ------------------------------------------------------------------

    _DIAL_CIRCLE_RE = re.compile(r"<circle\b[^>]*/>")

    def _dial_circle(markup, class_name):
        """The one `<circle>` in `markup` carrying exactly `class_name`,
        as a dict of its attributes, or None.

        Matched on a whole `class="..."` ATTRIBUTE rather than a
        substring, because this component's day-ring class is not a
        prefix of its arc's but a substring test is how a check comes to
        count two shapes as one anyway.
        """
        for tag in _DIAL_CIRCLE_RE.finditer(markup):
            attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', tag.group(0)))
            if attrs.get("class") == class_name:
                return attrs
        return None

    def _the_ring_draws_the_saved_window_from_the_emitted_attributes():
        """CFG-48 (25-04-PLAN.md Task 2): the arc's DRAWN length,
        recomputed from the attributes the server emitted rather than
        from the input that produced them.

        Recomputing from the input would pass against an emitter that
        ignored its own arithmetic entirely and drew a fixed arc.
        """
        import math
        for start, end, expected_turns in (
                ("23:00", "07:00", 1 / 3.0),
                ("07:00", "23:00", 2 / 3.0),
                ("00:00", "06:00", 0.25),
                ("23:59", "00:00", 1 / 1440.0)):
            markup = config_page.quiet_hours_group(start, end)
            day = _dial_circle(markup, config_page.QUIET_DIAL_DAY_CLASS)
            arc = _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS)
            if day is None:
                return False, "%s→%s: the dial emits no full-day ring at all" % (start, end)
            if arc is None:
                return False, "%s→%s: the dial emits no quiet arc" % (start, end)
            if day["r"] != arc["r"] or day["cx"] != arc["cx"] or day["cy"] != arc["cy"]:
                return False, (
                    "%s→%s: the arc is not drawn on the day ring — day %r, arc %r"
                    % (start, end, day, arc))
            circumference = 2 * math.pi * float(arc["r"])
            drawn = float(arc["stroke-dasharray"].split()[0])
            gap = float(arc["stroke-dasharray"].split()[1])
            if abs(drawn + gap - circumference) > 0.01:
                return False, (
                    "%s→%s: the dash pattern %r does not add up to the circumference %.4f of the "
                    "r=%s circle it is painted on" % (start, end, arc["stroke-dasharray"],
                                                      circumference, arc["r"]))
            if abs(drawn / circumference - expected_turns) > 1e-4:
                return False, (
                    "%s→%s draws %.4f of the ring, not the %.4f its %d-minute span asks for — "
                    "recomputed from the emitted r=%s and stroke-dasharray=%r"
                    % (start, end, drawn / circumference, expected_turns,
                       config_page.quiet_window_span(start, end).minutes,
                       arc["r"], arc["stroke-dasharray"]))
            # WHERE THE ARC STARTS, WHICH A LENGTH CHECK IS BLIND TO. An
            # eight-hour arc drawn from 07:00 instead of 23:00 is the
            # same length and a different window.
            span = config_page.quiet_window_span(start, end)
            rotation = re.match(
                r"rotate\((-?[\d.]+) (\d+) (\d+)\)", arc["transform"])
            if not rotation:
                return False, "%s→%s: unreadable arc transform %r" % (start, end, arc["transform"])
            if abs(float(rotation.group(1)) - (-90.0 + 360.0 * span.start_fraction)) > 1e-3:
                return False, (
                    "%s→%s: the arc is rotated %s°, but a window starting at %.6f of the way "
                    "round from twelve o'clock needs %.4f° (a quarter turn back from <circle>'s "
                    "own three-o'clock dash origin, plus the window's own start)"
                    % (start, end, rotation.group(1), span.start_fraction,
                       -90.0 + 360.0 * span.start_fraction))
            if (rotation.group(2), rotation.group(3)) != (arc["cx"], arc["cy"]):
                return False, (
                    "%s→%s: the arc rotates about %r, not its own centre %r"
                    % (start, end, rotation.group(2, 3), (arc["cx"], arc["cy"])))

        # THE READOUT SAYS WHAT THE ARC DRAWS, asserted against BOTH at
        # once: the two times it names and the duration the span implies.
        #
        # 27-02-PLAN.md Task 3 (CFG-62): the readout is now THREE
        # children (two `data-value-readout` endpoints plus a duration
        # span), not one text node — so "at rest, byte-identical" is
        # checked against the STRIPPED text (what a visitor reads), and
        # the structural seam is checked separately.
        markup = config_page.quiet_hours_group("23:00", "07:00")
        readout = re.search(
            r'<p class="time-value %s"([^>]*)>(.*?)</p>'
            % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), markup, re.DOTALL)
        if not readout:
            return False, "the card renders no dial readout"
        span = config_page.quiet_window_span("23:00", "07:00")
        expected_text = "23:00 → 07:00 · %s" % layout.duration_text(span.minutes * 60)
        stripped_text = re.sub(r"<[^>]*>", "", readout.group(2))
        if stripped_text != expected_text:
            return False, (
                "the readout reads %r at rest; the span it is drawn from is %d minutes, which "
                "this app's one duration ladder names %r — AT REST this must be byte-identical "
                "to what shipped before the pair seam (27-02-PLAN.md Task 3's own acceptance "
                "bar)" % (stripped_text, span.minutes, expected_text))
        if 'aria-hidden="true"' not in readout.group(1):
            return False, (
                "the readout is not aria-hidden — both time inputs already announce their own "
                "values natively and this would say the same thing twice (%r)" % readout.group(1))

        # THE THREE CHILDREN, EACH WIRED THROUGH THE EXISTING READOUT
        # SEAM. 28-03-PLAN.md Task 1 (CFG-73 Bug A) widened both halves:
        # the two endpoints now ALSO carry
        # VALUE_CONTROL_READOUT_FORMAT_ATTR="clock" (the readout-scoped
        # clock signal, alongside their existing bare-token template);
        # the duration span no longer carries an EMPTY template at all —
        # it carries its own data-value-readout-base PLUS all four
        # layout.DURATION_ATTRS, each holding a non-empty translated
        # wording, so value-controls.js can compose a live duration from
        # the pair without inventing any language of its own.
        for field, value in (("quiet_hours_start", "23:00"), ("quiet_hours_end", "07:00")):
            endpoint = re.search(
                r'<span %s="%s" %s="%s" %s="%s">%s</span>'
                % (re.escape(layout.VALUE_CONTROL_READOUT_ATTR), re.escape(field),
                   re.escape(layout.VALUE_CONTROL_READOUT_FORMAT_ATTR),
                   re.escape(layout.VALUE_CONTROL_FORMAT_CLOCK),
                   re.escape(layout.VALUE_CONTROL_READOUT_TEXT_ATTR),
                   re.escape(layout.VALUE_CONTROL_TEXT_TOKEN), re.escape(value)),
                readout.group(2))
            if not endpoint:
                return False, (
                    "no %s readout span carrying the clock-format attribute and the bare token "
                    "template and %r: %r" % (field, value, readout.group(2)))
        duration_span = re.search(
            r'<span %s="quiet_hours_start" %s="(\d+)"((?: %s="[^"]*"){%d})>([^<]*)</span>'
            % (re.escape(layout.VALUE_CONTROL_READOUT_ATTR),
               re.escape(layout.VALUE_CONTROL_READOUT_BASE_ATTR),
               "(?:%s)" % "|".join(re.escape(attr) for attr in layout.DURATION_ATTRS),
               len(layout.DURATION_ATTRS)),
            readout.group(2))
        if not duration_span:
            return False, (
                "no duration span carrying a data-value-readout-base and all %d "
                "layout.DURATION_ATTRS: %r" % (len(layout.DURATION_ATTRS), readout.group(2)))
        if int(duration_span.group(1)) != config_page.quiet_window_minute_of_day("23:00"):
            return False, (
                "the duration span's data-value-readout-base is %s minutes; the saved window's "
                "own start is %d" % (duration_span.group(1),
                                      config_page.quiet_window_minute_of_day("23:00")))
        for attr in layout.DURATION_ATTRS:
            if ('%s="' % attr) not in duration_span.group(2):
                return False, (
                    "the duration span is missing %r, one of layout.DURATION_ATTRS: %r"
                    % (attr, duration_span.group(2)))
        if duration_span.group(3) != layout.duration_text(span.minutes * 60):
            return False, (
                "the duration span's own text is %r at rest, not this app's one duration ladder's "
                "%r" % (duration_span.group(3), layout.duration_text(span.minutes * 60)))

        # CFG-52: NOTHING ON THIS CARD IS A LIVE REGION. Dragging fires
        # continuously and a role="status" here would re-announce the
        # identical phrase on every step — the defect Phase 23 hit with
        # its three switches, and the one this plan exists to avoid.
        for banned in ('role="status"', "aria-live", 'role="alert"', 'role="log"'):
            if banned in markup:
                return False, (
                    "the Quiet hours card carries %r — the focused handle's own aria-valuetext "
                    "is the native, debounced announcement path and a live region beside it "
                    "re-announces the same phrase on every drag step (CFG-52)" % banned)

        # THE FLOOR: NO WINDOW MEANS NO ARC AND NO WORDS, never a full
        # ring and never a zero-length dash (which renders as a dot under
        # a round cap and would read as "a few minutes").
        for start, end, why in (
                ("", "", "nothing stored"),
                ("23:00", "", "half stored"),
                ("99:99", "07:00", "an unparseable start")):
            markup = config_page.quiet_hours_group(start, end)
            if _dial_circle(markup, config_page.QUIET_DIAL_DAY_CLASS) is None:
                return False, "%s: the full-day ring must still draw" % why
            if _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS) is not None:
                return False, (
                    "%s (%r→%r): an arc was emitted anyway — a drawn window claims one is "
                    "configured" % (why, start, end))
            if config_page.QUIET_DIAL_READOUT_CLASS in markup:
                return False, "%s (%r→%r): a readout was emitted anyway" % (why, start, end)
        zero = config_page.quiet_hours_group("23:00", "23:00")
        if _dial_circle(zero, config_page.QUIET_DIAL_ARC_CLASS) is not None:
            return False, (
                "a zero-length window emitted an arc — a zero-length dash is a DOT under a round "
                "cap, so 'no window' would read as a few minutes")
        if config_page.QUIET_DIAL_READOUT_CLASS not in zero:
            return False, (
                "a zero-length window is a real, stored state (server.device_config calls it "
                "never-active) and its readout must still say so")

        # T-25-04-B: a hostile stored value reaching the arc or readout.
        hostile = config_page.quiet_hours_group(
            "23:00", "07:00",
            submitted={"quiet_hours_start": '"><script>alert(1)</script>',
                       "quiet_hours_end": "07:00"})
        if "<script>" in hostile:
            return False, "an unescaped <script> reached the Quiet hours card"
        if _dial_circle(hostile, config_page.QUIET_DIAL_ARC_CLASS) is not None:
            return False, "a value that is not a time drew an arc"
        return True, ""
    check(
        "the quiet dial's arc is recomputed from the attributes the SERVER emitted — 23:00→07:00 "
        "draws a third of the emitted circle and 07:00→23:00 its two thirds, the dash pattern "
        "adds up to that circle's own circumference, and the arc is rotated by a quarter turn "
        "plus the window's own start about its own centre (an eight-hour arc drawn from the "
        "wrong hour is the same length and a different window); the readout names both times and "
        "the duration the same span implies and is aria-hidden; nothing on the card is a "
        "role=\"status\"/aria-live region (CFG-52); nothing stored draws no arc and no words "
        "while the full-day ring still draws; and a hostile submitted value reaches neither "
        "(T-25-04-B) (CFG-48, 25-04-PLAN.md Task 2)",
        _the_ring_draws_the_saved_window_from_the_emitted_attributes)

    def _the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages():
        # 28-03-PLAN.md Task 3 (CFG-73 Bug A): quiet_dial_readout_html()'s
        # own server-render contract, checked directly rather than only
        # through the byte-identical-at-rest assertion above — both
        # endpoint spans carry the readout-scoped clock-format attribute,
        # and the duration span carries a non-empty value for EVERY one
        # of layout.DURATION_ATTRS, in BOTH shipped languages.
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                markup = config_page.quiet_hours_group("23:00", "07:00")
            finally:
                prefs.set_request_prefs(lang="en")
            readout = re.search(
                r'<p class="time-value %s"([^>]*)>(.*?)</p>'
                % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), markup, re.DOTALL)
            if not readout:
                return False, "lang=%s: the card renders no dial readout" % lang
            body = readout.group(2)
            clock_count = body.count(
                '%s="%s"' % (layout.VALUE_CONTROL_READOUT_FORMAT_ATTR,
                             layout.VALUE_CONTROL_FORMAT_CLOCK))
            if clock_count != 2:
                return False, (
                    "lang=%s: expected %s=%r exactly twice (once per endpoint span), found %d "
                    "in %r" % (lang, layout.VALUE_CONTROL_READOUT_FORMAT_ATTR,
                               layout.VALUE_CONTROL_FORMAT_CLOCK, clock_count, body))
            for attr in layout.DURATION_ATTRS:
                m = re.search(r'%s="([^"]*)"' % re.escape(attr), body)
                if not m:
                    return False, (
                        "lang=%s: the duration span carries no %r: %r" % (lang, attr, body))
                if not m.group(1):
                    return False, (
                        "lang=%s: %r is present but EMPTY — every bucket wording must be "
                        "non-empty so the client never has to invent one: %r"
                        % (lang, attr, body))
        return True, ""
    check(
        "quiet_dial_readout_html() carries data-value-readout-format=\"clock\" on both endpoint "
        "spans and a non-empty value for each of the four layout.DURATION_ATTRS on the duration "
        "span, in both shipped languages (CFG-73 Bug A, 28-03-PLAN.md Task 3)",
        _the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages)

    def _the_ring_is_an_addition_and_the_four_controls_are_untouched():
        """CFG-48 (25-04-PLAN.md Task 2): B14 has been broken once
        already, and the two time inputs are the only controls on this
        card a visitor can TYPE into.

        The byte-identical diff against the pre-task builder was taken
        once, by hand, across five argument shapes (recorded in the
        SUMMARY). What lives here is the durable half: the properties
        that diff proved, asserted in a form that keeps holding.
        """
        for start, end, submitted in (
                ("23:00", "07:00", None),
                ("08:00", "18:00", None),
                ("", "", None),
                ("23:00", "07:00", {"quiet_hours_start": "07:30",
                                    "quiet_hours_end": "zz"})):
            markup = config_page.quiet_hours_group(
                start, end, submitted=submitted,
                errors={"quiet_hours_end": "Bad"} if submitted else None)
            effective_start = config_page._submitted_or_current(
                submitted, "quiet_hours_start", start)
            effective_end = config_page._submitted_or_current(
                submitted, "quiet_hours_end", end)

            # BOTH NATIVE TIME INPUTS, with every attribute the card's
            # own docstring locks — and NEVER `disabled`, which
            # 10-RESEARCH.md's Open Question 2 settled in the affirmative
            # (a window may be pre-configured whether or not quiet hours
            # is currently on).
            for field, effective in (("quiet_hours_start", effective_start),
                                     ("quiet_hours_end", effective_end)):
                tag = re.search(r'<input type="time" name="%s"[^>]*>' % field, markup)
                if not tag:
                    return False, (
                        "%r→%r: no <input type=\"time\" name=%r> — the dial is an ADDITION and "
                        "the native input is what the form posts" % (start, end, field))
                element = tag.group(0)
                for needed in ('value="%s"' % escape_html(effective), " required",
                               'lang="%s"' % prefs.current_lang(),
                               'form="%s"' % config_page.SETTINGS_FORM_ID):
                    if needed not in element:
                        return False, (
                            "%r→%r: %s lost %r — %s" % (start, end, field, needed, element))
                if "disabled" in element:
                    return False, (
                        "%r→%r: %s is disabled; neither time input may ever be, whatever the "
                        "on/off state is — %s" % (start, end, field, element))

            # B14's VISIBLE 24h SIBLING, present verbatim beside each
            # input. A browser in en-US renders the stored "23:00" as
            # "11:00 PM" directly beside a preset labelled
            # "Night (23:00-07:00)"; this element is the fix, and a dial
            # that removed it would reopen a closed defect.
            for field, effective in (("quiet_hours_start", effective_start),
                                     ("quiet_hours_end", effective_end)):
                sibling = config_page._normalised_time_html(effective)
                if sibling and sibling not in markup:
                    return False, (
                        "%r→%r: B14's visible 24h sibling for %s (%r) is gone from the card"
                        % (start, end, field, sibling))
                if sibling and markup.count(sibling) < 1:
                    return False, "%r→%r: %s's 24h sibling is not rendered" % (start, end, field)

            # THE THREE PRESETS, and the data attributes dirty-state.js
            # writes into the two fields from. The dial reads FROM those
            # same fields, which is what makes a preset move the handles
            # with no code at all.
            presets = re.findall(r'<button type="button" %s[^>]*>'
                                 % re.escape(config_page.QUIET_HOURS_PRESET_ATTR), markup)
            if len(presets) != 3:
                return False, (
                    "%r→%r: expected the three presets, got %d" % (start, end, len(presets)))
            for needed in ('data-preset-start="%s"' % config_page.QUIET_HOURS_PRESET_NIGHT_START,
                           'data-preset-end="%s"' % config_page.QUIET_HOURS_PRESET_NIGHT_END,
                           'data-preset-start="%s"' % config_page.QUIET_HOURS_PRESET_WORKDAY_START,
                           'data-preset-end="%s"' % config_page.QUIET_HOURS_PRESET_WORKDAY_END,
                           'data-preset-enabled="0"'):
                if needed not in markup:
                    return False, "%r→%r: the preset row lost %r" % (start, end, needed)

            # THE CAPTION, INCLUDING ITS ONE COMPUTED DELAY SENTENCE, and
            # exactly one caption element — the one-caption-per-section
            # rule, which a drawing is the obvious way to break.
            caption = re.search(
                r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
                % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), markup)
            if not caption:
                return False, "%r→%r: the section caption is gone" % (start, end)
            if markup.count('class="text-label section-caption"') != 1:
                return False, (
                    "%r→%r: the card renders %d section captions; one section, one caption"
                    % (start, end, markup.count('class="text-label section-caption"')))
            if not caption.group(1).startswith(
                    escape_html(config_page.QUIET_HOURS_SECTION_CAPTION)):
                return False, "%r→%r: the caption's first sentence changed" % (start, end)
            if len(caption.group(1)) <= len(escape_html(config_page.QUIET_HOURS_SECTION_CAPTION)):
                return False, (
                    "%r→%r: the caption lost its computed delay sentence — the SAME triple the "
                    "Frame strip reads, never a second one computed here" % (start, end))

            # THE LOCKED ORDER, AND WHERE THE RING JOINS IT. The four
            # controls keep their positions and their adjacency; the ring
            # is an addition between the caption and the presets, so the
            # picture reads before the things that change it.
            positions = [
                ("caption", markup.index('class="text-label section-caption"')),
                ("dial", markup.index('class="%s"' % config_page.QUIET_DIAL_CLASS)),
                ("presets", markup.index('class="runway-row"')),
                ("start", markup.index('name="quiet_hours_start"')),
                ("end", markup.index('name="quiet_hours_end"')),
            ]
            if [name for name, _ in sorted(positions, key=lambda pair: pair[1])] != [
                    "caption", "dial", "presets", "start", "end"]:
                return False, (
                    "%r→%r: the card's order is %r — 10-UI-SPEC.md locks presets, then Start, "
                    "then End, and the ring is an addition between the caption and the presets, "
                    "never a reordering"
                    % (start, end, sorted(positions, key=lambda pair: pair[1])))

            # NOT SIDE BY SIDE. 10-UI-SPEC.md rejects that explicitly, to
            # keep two native time pickers from wrapping at 360px.
            if "theme-status__row" in markup:
                return False, "%r→%r: the two time fields were put side by side" % (start, end)

        # THE D-07 ECHO, WHICH IS WHY THE ARC READS THE EFFECTIVE VALUES.
        # On a rejected save the picture must show what the visitor
        # submitted, not what is stored, or the two disagree on exactly
        # the screen where a mistake is being fixed.
        echoed = config_page.quiet_hours_group(
            "23:00", "07:00", errors={"quiet_hours_end": "Bad"},
            submitted={"quiet_hours_start": "09:00", "quiet_hours_end": "17:00"})
        submitted_span = config_page.quiet_window_span("09:00", "17:00")
        arc = _dial_circle(echoed, config_page.QUIET_DIAL_ARC_CLASS)
        if arc is None:
            return False, "the rejected-save render drew no arc at all"
        drawn = float(arc["stroke-dasharray"].split()[0])
        import math
        if abs(drawn / (2 * math.pi * float(arc["r"])) - submitted_span.sweep_fraction) > 1e-4:
            return False, (
                "the rejected-save render drew %.4f of the ring; the SUBMITTED 09:00→17:00 "
                "window is %.4f, and the stored 23:00→07:00 one is %.4f — the arc must echo the "
                "submission, the same D-07 rule the two inputs already follow"
                % (drawn / (2 * math.pi * float(arc["r"])), submitted_span.sweep_fraction,
                   config_page.quiet_window_span("23:00", "07:00").sweep_fraction))
        # 27-02-PLAN.md Task 3 (CFG-62): the readout is now three
        # children, not one text node, so the echo is checked per span
        # rather than as one contiguous substring.
        echoed_readout = re.search(
            r'<p class="time-value %s"[^>]*>(.*?)</p>'
            % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), echoed, re.DOTALL)
        if not echoed_readout:
            return False, "the rejected-save render carries no dial readout at all"
        if (">09:00<" not in echoed_readout.group(1)
                or ">17:00<" not in echoed_readout.group(1)):
            return False, (
                "the rejected-save readout does not echo the submitted window: %r"
                % echoed_readout.group(1))
        return True, ""
    check(
        "the ring is an ADDITION: both native <input type=\"time\"> fields keep their value/"
        "required/lang/form attributes and are never disabled, B14's visible 24h sibling still "
        "renders beside each, the three presets keep the data attributes dirty-state.js writes "
        "through, the one section caption keeps its computed delay sentence, the card's order is "
        "caption → ring → presets → Start → End with the four controls' own order and adjacency "
        "untouched and no side-by-side row, and the arc echoes the SUBMITTED window on a "
        "rejected save rather than the stored one (B14/D-07/CFG-48, 25-04-PLAN.md Task 2)",
        _the_ring_is_an_addition_and_the_four_controls_are_untouched)

    def _the_dials_paint_resolves_and_decides_nothing_in_python():
        """CFG-48/CFG-52 (25-04-PLAN.md Task 2): the dial's paint,
        asserted as one thing because the parts fail together.

        A class that exists in Python and nowhere in the stylesheet
        paints nothing at all, and nothing else in this codebase would
        notice.
        """
        with open(os.path.join(HERE, "static", "style.css")) as fh:
            source = fh.read()
        markup = config_page.quiet_hours_group("23:00", "07:00")
        # From the dial's own opening tag to the end of its readout —
        # the whole component, handle layer included, so a class added
        # inside the gate is scanned on exactly the same terms as one
        # outside it.
        dial = markup[markup.index('<div class="%s"' % config_page.QUIET_DIAL_CLASS):]
        dial = dial[:dial.index("</p>", dial.index(
            config_page.QUIET_DIAL_READOUT_CLASS)) + len("</p>")]

        # NO COLOUR DECIDED IN PYTHON. A literal here is correct in one
        # theme and invisible in the other, and invisible to the contrast
        # harness too.
        colours = re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\(", dial + " " + markup[
            markup.index(config_page.QUIET_DIAL_READOUT_CLASS):][:400])
        if colours:
            return False, "the dial's emitted markup carries colour literals %r" % (colours,)

        # EVERY CLASS THE EMITTED MARKUP CARRIES RESOLVES TO A REAL
        # SELECTOR, scanned off the markup rather than off a list of
        # constants — the failure being defended against is a class that
        # exists in Python and nowhere in the stylesheet, which a list
        # written by the same hand would share. Boundary-anchored, so one
        # class is never reported as resolved by a longer one's rule.
        emitted = set()
        for attr in re.findall(r'class="([^"]*)"', dial):
            emitted.update(attr.split())
        emitted.add(config_page.QUIET_DIAL_READOUT_CLASS)
        for class_name in sorted(emitted):
            if not re.search(r"\.%s(?![-\w])" % re.escape(class_name), source):
                return False, (
                    "the dial emits the class %r, which has no selector in style.css — it paints "
                    "nothing at all and nothing else in this codebase would notice" % class_name)

        # EVERY SHAPE HAS A PAINT ROUTE, and the canvas has a size route.
        for tag in re.finditer(r"<circle\b[^>]*>", dial):
            element = tag.group(0)
            if 'class="' not in element:
                return False, (
                    "an unclassed shape: %r — with neither a class nor a fill it takes the SVG "
                    "default black, correct in one theme and invisible in the other" % element)
            if 'fill="none"' not in element:
                return False, (
                    "a stroked shape with no explicit fill: %r — the SVG default is a filled "
                    "black disc across the middle of the card" % element)
            if "stroke-width=" not in element:
                return False, "a stroked shape with no stroke width: %r" % element
        svg = re.search(r"<svg\b[^>]*>", dial).group(0)
        for needed in ('viewBox="0 0 %d %d"' % (config_page.QUIET_DIAL_SIZE,
                                                config_page.QUIET_DIAL_SIZE),
                       'width="%d"' % config_page.QUIET_DIAL_SIZE,
                       'height="%d"' % config_page.QUIET_DIAL_SIZE,
                       'aria-hidden="true"', 'focusable="false"'):
            if needed not in svg:
                return False, (
                    "the dial's canvas is missing %r — an <svg> with neither an intrinsic "
                    "attribute nor a CSS rule renders at the format's own 300x150 default: %r"
                    % (needed, svg))

        # THE PAINT ITSELF: a theme token, never a literal, so both
        # themes are correct from one rule. Accent is reserved (this
        # file's header comment keeps an exhaustive list) and a dial is
        # not on it, so the ring says what it says in INK.
        for selector, token in ((".quiet-dial__day", "--color-border"),
                                (".quiet-dial__arc", "--color-text"),
                                (".quiet-dial__hour", "--color-text")):
            rule = re.search(r"\%s\s*\{([^}]*)\}" % selector, source)
            if not rule:
                return False, "no %s rule in style.css" % selector
            if token not in rule.group(1):
                return False, (
                    "%s paints from %r rather than %s — a paint that does not come from a theme "
                    "token is correct in one theme only" % (selector, rule.group(1), token))
            if "--color-accent" in rule.group(1):
                return False, (
                    "%s paints accent; the header comment's accent-reservation list is "
                    "exhaustive and a dial is not on it" % selector)
            # The presentation attributes must stay presentation
            # attributes: a CSS stroke-width of any specificity beats
            # one, which would flatten the geometry the constants derive.
            if "stroke-width" in rule.group(1):
                return False, (
                    "%s declares stroke-width in CSS, which beats the presentation attribute the "
                    "emitter derives from its own size constants" % selector)
        return True, ""
    check(
        "the quiet dial's paint resolves — every class the EMITTED markup carries has a real "
        "selector (scanned off the markup, boundary-anchored), every shape carries a class, an "
        "explicit fill=\"none\" and a stroke width, the canvas declares its viewBox, its "
        "intrinsic size, aria-hidden and focusable, no colour is decided in Python, the day "
        "ring/arc/hour labels each paint from a theme token so both themes are correct from one "
        "rule, no accent appears anywhere in the component, and no rule declares stroke-width in "
        "CSS where it would beat the derived presentation attribute (CFG-48/CFG-52, "
        "25-04-PLAN.md Task 2)",
        _the_dials_paint_resolves_and_decides_nothing_in_python)

    # ------------------------------------------------------------------
    # 25-04-PLAN.md Task 3 (CFG-48): the two handles, gated,
    # keyboard-first, holding no value of their own.
    # ------------------------------------------------------------------

    _WRAPPER_RE = re.compile(
        r'<div class="([^"]*)"([^>]*\bdata-value-control\b[^>]*)>(.*?)</div>', re.DOTALL)

    def _the_two_handles_are_gated_and_hold_no_value_of_their_own():
        """CFG-48 (25-04-PLAN.md Task 3): two real `<button>` sliders,
        inside the gate and nowhere else, announcing the value the two
        native inputs already hold.

        The point every clause below defends: the handles are a LAYER.
        Delete the script and both times are still rendered, still
        validated, still posted and still saved by the two
        `<input type="time">` fields underneath.
        """
        with open(os.path.join(HERE, "static", "value-controls.js")) as fh:
            script = fh.read()
        with open(os.path.join(HERE, "static", "style.css")) as fh:
            css = fh.read()
        markup = config_page.quiet_hours_group("23:00", "07:00")

        wrappers = _WRAPPER_RE.findall(markup)
        if len(wrappers) != 2:
            return False, "expected exactly two gated handle wrappers, got %d" % len(wrappers)

        # EVERY element carrying the wrapper attribute carries the gate
        # class ITSELF. A wrapper rendered outside the gate is the
        # control that renders and does nothing: visible with scripts
        # blocked, inert, and competing with the input that works.
        for tag in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
            text = tag.group(0)
            if not re.search(r"(?<![-\w])%s(?![-\w])"
                             % re.escape(layout.VALUE_CONTROL_ATTR), text):
                continue
            class_match = re.search(r'\bclass="([^"]*)"', text)
            classes = class_match.group(1).split() if class_match else []
            if layout.JS_GATE_CLASS not in classes:
                return False, (
                    "an element carries %s outside the %r gate: %s"
                    % (layout.VALUE_CONTROL_ATTR, layout.JS_GATE_CLASS, text))

        # AND NO HANDLE MARKUP OUTSIDE A WRAPPER. The converse of the
        # clause above, and the one a wrapper-only scan is blind to: a
        # <button data-value-handle> rendered beside the gate rather than
        # inside it is a grabbable thing that steers nothing.
        inside = "".join(body for _classes, _attrs, body in wrappers)
        if markup.count(layout.VALUE_CONTROL_HANDLE_ATTR) != inside.count(
                layout.VALUE_CONTROL_HANDLE_ATTR):
            return False, (
                "%d element(s) carry %s but only %d are inside a gated wrapper"
                % (markup.count(layout.VALUE_CONTROL_HANDLE_ATTR),
                   layout.VALUE_CONTROL_HANDLE_ATTR,
                   inside.count(layout.VALUE_CONTROL_HANDLE_ATTR)))

        expected = (("quiet_hours_start", "23:00", 1380, config_page.QUIET_DIAL_START_LABEL),
                    ("quiet_hours_end", "07:00", 420, config_page.QUIET_DIAL_END_LABEL))
        for (classes, attrs, body), (field, clock, minute, label) in zip(wrappers, expected):
            if layout.JS_GATE_CLASS not in classes.split():
                return False, "the %s wrapper is not gated: %r" % (field, classes)
            # THE STEERING CONTRACT, read off the wrapper. Every name
            # here is companion/layout.py's, never a literal typed twice.
            for attr, value in ((layout.VALUE_CONTROL_FIELD_ATTR, field),
                                (layout.VALUE_CONTROL_FORM_ATTR, config_page.SETTINGS_FORM_ID),
                                (layout.VALUE_CONTROL_MIN_ATTR, "0"),
                                (layout.VALUE_CONTROL_MAX_ATTR, "1439"),
                                (layout.VALUE_CONTROL_STEP_ATTR, "15"),
                                (layout.VALUE_CONTROL_GEOMETRY_ATTR, "angular"),
                                (layout.VALUE_CONTROL_FORMAT_ATTR,
                                 layout.VALUE_CONTROL_FORMAT_CLOCK),
                                (layout.VALUE_CONTROL_TEXT_ATTR,
                                 layout.VALUE_CONTROL_TEXT_TOKEN)):
                if ('%s="%s"' % (attr, value)) not in attrs:
                    return False, (
                        "the %s wrapper does not carry %s=%r: %s" % (field, attr, value, attrs))
            # THE SERVER-PAINTED INITIAL POSITION, without which the
            # handle renders at the top of the ring until something
            # touches it.
            fraction = re.search(r"--value-fraction: ([\d.]+)", attrs)
            if not fraction:
                return False, "the %s wrapper paints no initial position: %s" % (field, attrs)
            if abs(float(fraction.group(1))
                   - config_page.quiet_dial_handle_fraction(minute)) > 1e-6:
                return False, (
                    "the %s handle is painted at %s of a turn; the %d minutes its input holds is "
                    "%.6f" % (field, fraction.group(1), minute,
                              config_page.quiet_dial_handle_fraction(minute)))

            # A REAL <button type="button">, never a bare <div>: a button
            # is focusable, activatable and announced with no ARIA at
            # all, and `type="button"` is what stops Enter on a handle
            # from submitting the settings form.
            handle = re.search(r'<button\b[^>]*%s[^>]*>'
                               % re.escape(layout.VALUE_CONTROL_HANDLE_ATTR), body)
            if not handle:
                return False, "the %s wrapper's handle is not a <button>: %r" % (field, body)
            for needed in ('type="button"', 'role="slider"', 'aria-valuemin="0"',
                           'aria-valuemax="1439"', 'aria-valuenow="%d"' % minute,
                           'aria-valuetext="%s"' % clock,
                           'aria-label="%s"' % escape_html(label)):
                if needed not in handle.group(0):
                    return False, (
                        "the %s handle is missing %r — %s" % (field, needed, handle.group(0)))
            # THE ANNOUNCED VALUE IS THE TIME, NOT THE MINUTE COUNT. A
            # screen reader reading "one thousand three hundred and
            # eighty" instead of "23:00" is the whole reason
            # aria-valuetext exists.
            if 'aria-valuetext="%d"' % minute in handle.group(0):
                return False, "the %s handle announces its minute count, not its time" % field
            # AND IT IS THE VALUE THE INPUT ACTUALLY HOLDS.
            tag = re.search(r'<input type="time" name="%s"[^>]*>' % field, markup)
            if ('value="%s"' % clock) not in tag.group(0):
                return False, (
                    "the %s handle announces %r while its own input holds something else: %s"
                    % (field, clock, tag.group(0)))

        # BOTH ENDS OF THE SEAM, PINNED. A rename on either side alone is
        # a control that renders and steers nothing, and nothing else in
        # this tree would notice.
        if ('"%s"' % layout.VALUE_CONTROL_FORMAT_ATTR) not in script:
            return False, "value-controls.js does not name %r" % layout.VALUE_CONTROL_FORMAT_ATTR
        for wire in ('=== "%s"' % layout.VALUE_CONTROL_FORMAT_CLOCK, '=== "angular"'):
            if wire not in script:
                return False, (
                    "value-controls.js never compares against %r, so the markup's own value is "
                    "read by nothing" % wire)
        # THE PAINTED POSITION, PINNED IN ALL THREE FILES IT TRAVELS
        # THROUGH — the server writes it, the script rewrites it, the
        # stylesheet reads it. It has no Python constant (see
        # companion/layout.py for why), so this is the guard instead.
        for where, source, needle in (
                ("the emitted markup", markup, "--value-fraction:"),
                ("value-controls.js", script, '"--value-fraction"'),
                ("style.css", css, "var(--value-fraction")):
            if needle not in source:
                return False, (
                    "%s does not name --value-fraction (%r) — the handle's position travels on "
                    "that property through all three, and a rename in one leaves it pinned at "
                    "the start of its own range" % (where, needle))
        # THE TOKEN THAT REACHES A RENDERED PAGE. "{}" here fails
        # companion/test_i18n.py's French-render artefact scan, which is
        # why it is not "{}" any more.
        if layout.VALUE_CONTROL_TEXT_TOKEN in ("{}", "%s", "%d"):
            return False, (
                "layout.VALUE_CONTROL_TEXT_TOKEN is %r, which is one of the format artefacts the "
                "i18n harness scans every French render for — it reaches the browser as an "
                "attribute value on a rendered page" % layout.VALUE_CONTROL_TEXT_TOKEN)
        if ('"%s"' % layout.VALUE_CONTROL_TEXT_TOKEN) not in script:
            return False, "value-controls.js does not name the token %r" % (
                layout.VALUE_CONTROL_TEXT_TOKEN,)

        # THE FRENCH ACCESSIBLE NAMES. A handle whose only name is
        # English is a control a French screen-reader user cannot tell
        # apart from the other one.
        prefs.set_request_prefs(lang="fr")
        try:
            french = config_page.quiet_hours_group("23:00", "07:00")
        finally:
            prefs.set_request_prefs(lang="en")
        for label in (config_page.QUIET_DIAL_START_LABEL, config_page.QUIET_DIAL_END_LABEL):
            translated = i18n_fr.CATALOG.get(label)
            if not translated or translated == label:
                return False, "%r has no French sibling" % label
            if ('aria-label="%s"' % escape_html(translated)) not in french:
                return False, "the French render does not name the handle %r" % translated

        # OMIT, DON'T FABRICATE: an end that does not parse gets no
        # handle, because a handle at an invented position claims a value
        # that was never set.
        for start, end, expected_handles in (("23:00", "", 1), ("", "", 0), ("zz", "07:00", 1)):
            partial = config_page.quiet_hours_group(start, end)
            got = len(_WRAPPER_RE.findall(partial))
            if got != expected_handles:
                return False, (
                    "%r→%r emitted %d handle(s), expected %d"
                    % (start, end, got, expected_handles))
        return True, ""
    check(
        "the quiet dial's two handles are real <button type=\"button\"> sliders INSIDE 25-01's "
        ".js gate and nowhere else (every element carrying the wrapper attribute carries the "
        "gate class itself, and every element carrying the handle attribute is inside a "
        "wrapper); each carries role/aria-valuemin/aria-valuemax/aria-valuenow and an "
        "aria-valuetext that is the HH:MM its own input holds rather than a minute count, plus a "
        "translated aria-label in both languages; each wrapper carries layout's own steering "
        "attributes including the clock codec, is painted at the fraction its input's value "
        "implies, and names --value-fraction in all three files it travels through; the "
        "aria-valuetext token is not one of the format artefacts the i18n harness scans French "
        "renders for; and an end that does not parse gets no handle at all (CFG-48, "
        "25-04-PLAN.md Task 3)",
        _the_two_handles_are_gated_and_hold_no_value_of_their_own)

    def _the_handle_rides_the_ring_the_emitter_drew():
        """CFG-48 (25-04-PLAN.md Task 3): the handle's geometry and the
        two stacked layers' pointer discipline.

        Two numbers have to agree across two files here — the dial's
        rendered width and the radius the handle is thrown out to — and
        two numbers that have to agree and live in two files agree until
        one of them is edited.
        """
        with open(os.path.join(HERE, "static", "style.css")) as fh:
            source = fh.read()

        def rule(selector):
            found = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", source)
            return found.group(1) if found else None

        dial_rule = rule(".quiet-dial")
        if dial_rule is None:
            return False, "no .quiet-dial rule in style.css"
        width = re.search(r"width:\s*(\d+)px", dial_rule)
        radius = re.search(r"--quiet-dial-radius:\s*(\d+)px", dial_rule)
        if not width or int(width.group(1)) != config_page.QUIET_DIAL_SIZE:
            return False, (
                "the dial's CSS width is %r and its emitter draws a %dpx canvas — the handle is "
                "positioned against the CSS box and the arc is drawn in the canvas, so a "
                "mismatch puts the grip off the stroke it steers"
                % (width and width.group(0), config_page.QUIET_DIAL_SIZE))
        if not radius or int(radius.group(1)) != config_page.QUIET_DIAL_RADIUS:
            return False, (
                "the handle rides a radius of %r; the ring's own stroke centre line is %dpx"
                % (radius and radius.group(0), config_page.QUIET_DIAL_RADIUS))

        # THE SOURCE-ORDER PIN. The handle wears three classes and two of
        # them declare `position` at equal (0,1,0) specificity, so the
        # later rule wins — and the one that must win is the absolute
        # one, or the handle stops being positioned against the ring at
        # all.
        hit_at = source.index(".control-hit-area {")
        handle_at = source.index(".value-control__handle {")
        if handle_at < hit_at:
            return False, (
                "the shared .value-control__handle rule now precedes the shared hit-area rule; "
                "both declare `position` at equal specificity, so the relative one would win and "
                "the handle would sit wherever the text flow put it")

        # THE POINTER DISCIPLINE. Two full-size layers are stacked over
        # the ring; without these three declarations the upper one
        # swallows every press meant for the ring or for the other end.
        for selector, expected in ((".quiet-dial__handles", "none"),
                                   (".quiet-dial__handle-track", "none"),
                                   (".quiet-dial__handle", "auto")):
            body = rule(selector)
            if body is None:
                return False, "no %s rule in style.css" % selector
            if ("pointer-events: %s" % expected) not in body:
                return False, (
                    "%s does not declare `pointer-events: %s` — with two full-size layers "
                    "stacked over one ring, the upper one otherwise claims every press"
                    % (selector, expected))

        handle_rule = rule(".quiet-dial__handle")
        for needed in ("var(--value-fraction", "var(--quiet-dial-radius"):
            if needed not in handle_rule:
                return False, "the handle's transform does not read %r: %s" % (
                    needed, handle_rule)
        # Z-ORDER IS DOCUMENT ORDER, WHICH IS THE STATED DECISION: the
        # END handle is emitted second and therefore wins a pointer-down
        # in an overlap. A z-index on either would silently re-decide it.
        if "z-index" in handle_rule:
            return False, (
                "the handle declares a z-index; the overlap decision this control records is "
                "document order, and a z-index re-decides it somewhere nobody is looking")
        # Paint from tokens, and no accent — the header comment's
        # reservation list is exhaustive and a dial is not on it.
        if "--color-accent" in handle_rule:
            return False, "the handle paints accent"
        for token in ("var(--color-canvas)", "var(--color-text)"):
            if token not in handle_rule:
                return False, (
                    "the handle does not paint from %s — the shared hit-area class is "
                    "transparent and borderless by design, so a handle wearing it and nothing "
                    "else is invisible" % token)
        return True, ""
    check(
        "the quiet dial's handle rides the ring the emitter drew — the stylesheet's dial width "
        "and handle radius equal config_page.QUIET_DIAL_SIZE and QUIET_DIAL_RADIUS, the shared "
        "handle rule still follows the shared hit-area rule so the absolute `position` wins at "
        "equal specificity, both stacked layers are pointer-transparent while the handle itself "
        "is not, the transform reads both custom properties, no z-index re-decides the "
        "document-order overlap rule, and the grip paints from theme tokens with no accent "
        "(CFG-48/CFG-52, 25-04-PLAN.md Task 3)",
        _the_handle_rides_the_ring_the_emitter_drew)

    # ------------------------------------------------------------------
    # 27-02-PLAN.md Tasks 1-2 (CFG-62): THE PAIR SEAM — the ancestor two
    # handles publish their fraction onto, and the .js-scoped rule that
    # redraws the arc from it once script is running.
    # ------------------------------------------------------------------

    def _the_pair_seam_publishes_both_handles_onto_the_shared_ancestor():
        """CFG-62 (27-02-PLAN.md Tasks 1-2): the ancestor carries the pair
        marker and all three fractions, computed from the SAME span the
        arc is drawn from; each handle names which one is its own; the
        script names both attributes and reuses the existing ancestor
        walker rather than a second one; and the presentation attributes
        this rule overrides stay untouched.
        """
        with open(os.path.join(HERE, "static", "value-controls.js")) as fh:
            script = fh.read()
        with open(os.path.join(HERE, "static", "style.css")) as fh:
            css = fh.read()

        # THE SCRIPT NAMES BOTH ATTRIBUTES, AND REUSES ancestorWith()
        # RATHER THAN A SECOND WALKER. `while (node` is ancestorWith()'s
        # own loop and ancestorForm()'s; a plan that added a second
        # walker would show a THIRD occurrence here.
        for needle in ('"data-value-pair"', '"data-value-pair-property"'):
            if needle not in script:
                return False, "value-controls.js does not name %s" % needle
        walker_loops = script.count("while (node")
        if walker_loops != 2:
            return False, (
                "value-controls.js has %d 'while (node' loops, expected exactly 2 "
                "(ancestorWith() and ancestorForm()) — the pair seam must reuse "
                "ancestorWith() rather than add a second walker" % walker_loops)

        markup = config_page.quiet_hours_group("23:00", "07:00")
        span = config_page.quiet_window_span("23:00", "07:00")
        end_fraction = (span.start_fraction + span.sweep_fraction) % 1.0

        dial_tag = re.search(r"<div class=\"quiet-dial\"[^>]*>", markup)
        if not dial_tag:
            return False, "no .quiet-dial opening tag in the markup"
        if ('%s="%s"' % (config_page.QUIET_DIAL_PAIR_ATTR,
                          config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"])) not in dial_tag.group(0):
            return False, (
                "the .quiet-dial ancestor does not carry %s=%r: %s"
                % (config_page.QUIET_DIAL_PAIR_ATTR,
                   config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"], dial_tag.group(0)))
        for prop, expected in (
                (config_page.QUIET_DIAL_PAIR_PROPERTIES["start"], span.start_fraction),
                (config_page.QUIET_DIAL_PAIR_PROPERTIES["end"], end_fraction),
                (config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"], span.sweep_fraction)):
            found = re.search(r"%s:\s*([\d.]+)" % re.escape(prop), dial_tag.group(0))
            if not found:
                return False, (
                    "the .quiet-dial ancestor's inline style is missing %s: %s"
                    % (prop, dial_tag.group(0)))
            if abs(float(found.group(1)) - expected) > 1e-6:
                return False, (
                    "%s is %s on the ancestor; the span it must be computed from (no second "
                    "window arithmetic) implies %.6f" % (prop, found.group(1), expected))

        # EACH HANDLE NAMES WHICH PROPERTY IS ITS OWN, AND THE TWO DIFFER.
        wrappers = _WRAPPER_RE.findall(markup)
        if len(wrappers) != 2:
            return False, "expected exactly two handle wrappers, got %d" % len(wrappers)
        pair_properties = []
        for _classes, attrs, _body in wrappers:
            found = re.search(
                r'%s="([^"]*)"' % re.escape(config_page.QUIET_DIAL_PAIR_PROPERTY_ATTR), attrs)
            if not found:
                return False, "a handle wrapper carries no %s: %s" % (
                    config_page.QUIET_DIAL_PAIR_PROPERTY_ATTR, attrs)
            pair_properties.append(found.group(1))
        if pair_properties[0] == pair_properties[1]:
            return False, (
                "both handles publish under the SAME property (%r) — the sweep can only be "
                "derived from two DIFFERENT fractions" % pair_properties[0])
        if set(pair_properties) != {config_page.QUIET_DIAL_PAIR_PROPERTIES["start"],
                                     config_page.QUIET_DIAL_PAIR_PROPERTIES["end"]}:
            return False, "the two handles publish %r, not the start/end pair" % (pair_properties,)

        # THE PRESENTATION ATTRIBUTES THIS RULE OVERRIDES ARE UNTOUCHED —
        # still real user-unit values from draw.unit_circle_dash_array(),
        # never pathLength-relative fractions (measured, in this task, to
        # corrupt the no-JS rendering when pathLength="1" is also present;
        # see quiet_dial_svg()'s own docstring).
        arc = _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS)
        if arc is None:
            return False, "the dial emits no arc for a real window"
        if "pathLength" in arc:
            return False, (
                "the arc carries pathLength=%r — measured on this tree to corrupt the presentation "
                "attribute's own rendering when combined with real user-unit stroke-dasharray "
                "values (companion/static/style.css's own comment beside the .js override records "
                "the measurement)" % arc["pathLength"])
        expected_dash = draw.unit_circle_dash_array(
            span.sweep_fraction, config_page.QUIET_DIAL_RADIUS)
        if arc["stroke-dasharray"] != expected_dash:
            return False, (
                "the arc's stroke-dasharray is %r, not %r — the pair seam must not change the "
                "presentation attribute the no-JS floor depends on"
                % (arc["stroke-dasharray"], expected_dash))

        # THE .js-SCOPED OVERRIDE RULE EXISTS, READS THE THREE ANCESTOR
        # PROPERTIES, AND THE EXISTING --quiet-dial-radius (never a
        # radius literal, and never pathLength).
        override = re.search(
            r"\.js \.quiet-dial \.quiet-dial__arc\s*\{([^}]*)\}", css, re.DOTALL)
        if not override:
            return False, "no .js .quiet-dial .quiet-dial__arc override rule in style.css"
        body = override.group(1)
        for needle in ("var(--quiet-start-fraction", "var(--quiet-sweep-fraction",
                       "var(--quiet-dial-radius"):
            if needle not in body:
                return False, "the .js override rule does not read %r: %s" % (needle, body)
        if "pathLength" in body or "path-length" in body:
            return False, "the .js override rule mentions pathLength: %s" % body
        return True, ""
    check(
        "the pair seam publishes both handles onto the shared ancestor (CFG-62, 27-02-PLAN.md "
        "Tasks 1-2) — value-controls.js names both data-value-pair* attributes and reuses "
        "ancestorWith() rather than a second walker (still exactly 2 'while (node' loops); the "
        ".quiet-dial ancestor carries the pair marker (its own value naming the derived sweep "
        "property) and all three fractions, computed from the SAME span triple the arc is drawn "
        "from; the two handles publish under DIFFERENT, correctly-named properties; the arc's own "
        "presentation attributes are untouched real user-unit values (no pathLength, measured to "
        "corrupt them); and the .js-scoped override rule reads the three ancestor properties plus "
        "the existing --quiet-dial-radius, never a radius literal",
        _the_pair_seam_publishes_both_handles_onto_the_shared_ancestor)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 1 (D-01, D-02, D-05 form half, D-26): the new
    # single-column, three-wrapped-section, one-merged-form shape.
    # ------------------------------------------------------------------

    def _render_exactly_five_dirty_sections_in_order():
        # Acceptance criterion: the rendered output contains exactly
        # seven elements carrying data-dirty-section, whose attribute
        # values in document order are "Runway", "Diagnostic LED",
        # "Quiet hours", "Wake interval", "Display", "Calendar",
        # "Notifications" — 10-05-PLAN.md Task 1 wired Quiet hours in as
        # the fourth group after Diagnostic LED, 11-03-PLAN.md Task 1
        # wired Wake interval in as the fifth, after Quiet hours,
        # 12-05-PLAN.md Task 1 wired Display in as the sixth, after Wake
        # interval, 16-05-PLAN.md Task 1 wired Calendar in as the
        # seventh, after Display (16-UI-SPEC.md Section Anatomy's
        # Placement recommendation), and 20-11-PLAN.md Task 1 wires
        # Notifications in as the eighth and last, after Calendar — the
        # legacy SCOPE_ALL tuple's own trailing position for the group
        # (scope_groups()'s own D-26 comment). 21-05-PLAN.md Task 1
        # (D-06): Theme's own former "Theme" entry is gone — SCOPE_ALL's
        # legacy render no longer renders theme_fieldset() (retired) or
        # its replacement (the Frame colours card, Display-scope only),
        # dropping the count from eight to seven. 21-07-PLAN.md Task 1
        # (D-13/Pitfall 2): Calendar's own entry is ALSO gone from
        # SCOPE_ALL now — the merged calendar_group() embeds a real
        # connect/replace <form> in every state, which would nest inside
        # <form id="settings-form"> on this legacy render, so
        # screens.GROUP_CALENDAR has no entry in `builders` here any
        # more either (the same accepted, documented fate Theme's own
        # entry already had), dropping the count from seven to six.
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): Display's own entry is
        # ALSO gone — display_group() is retired outright and
        # screens.GROUP_DISPLAY is no longer a member of ANY screen
        # type's own group tuple, dropping the count from six to five
        # (+0/-1: "Display" removed from the expected list below).
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        found = re.findall(
            r'%s="([^"]*)"' % re.escape(config_page.DIRTY_SECTION_ATTR), rendered)
        expected = [
            "Runway", "Diagnostic LED", "Quiet hours",
            "Wake interval", "Notifications"]
        if found != expected:
            return False, "expected %r in document order, got %r" % (expected, found)
        return True, ""
    check(
        "render() carries exactly five data-dirty-section elements, in document order Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications (Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 D-06; Calendar's own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/Pitfall 2; Display's own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1)",
        _render_exactly_five_dirty_sections_in_order)

    def _runway_fieldset_returns_single_top_level_div():
        # Acceptance criterion: runway_fieldset(...) returns a string
        # that starts with a single opening div tag and ends with its
        # matching closing tag — one top-level element, not five siblings
        # (D-01's root-cause fix). Retargeted in place (quick task
        # 260901-qif): the count moved from one div pair to two because a
        # nested `.runway-row` layout container was introduced around just
        # the cards — the original "exactly one <div> pair" wording was a
        # proxy for the top-level invariant rather than the invariant
        # itself. The startswith/endswith assertions are untouched; those
        # are the ones that actually prove the single-top-level-element
        # invariant.
        rendered = config_page.runway_fieldset("3")
        if not rendered.startswith('<div class="theme-status"'):
            return False, "expected runway_fieldset() to start with a single <div class=\"theme-status\"> wrapper"
        if not rendered.endswith("</div>"):
            return False, "expected runway_fieldset() to end with the wrapper's matching </div>"
        if rendered.count("<div") != 2 or rendered.count("</div>") != 2:
            return False, "expected exactly two div pairs - the top-level .theme-status wrapper and the nested .runway-row layout container"
        return True, ""
    check(
        "runway_fieldset() returns exactly two div pairs - the top-level .theme-status wrapper and the nested .runway-row layout container, not five flat siblings (D-01)",
        _runway_fieldset_returns_single_top_level_div)

    def _runway_row_starts_after_caption_and_nothing_follows_it():
        # quick task 260901-re6: inverted from the pre-merge version of
        # this check (which asserted a trailing helper paragraph rendered
        # AFTER .runway-row closed). Now asserts RUNWAY_SECTION_CAPTION
        # renders BEFORE .runway-row opens, and that no <p element
        # appears anywhere after the row closes inside the wrapper — the
        # actual proof the second paragraph is gone, not merely moved.
        rendered = config_page.runway_fieldset("3")
        caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - the row
        # now also carries role="radiogroup"/aria-labelledby/
        # aria-describedby, so the opening tag itself is no longer a
        # bare literal; the match still proves there is exactly one
        # .runway-row element.
        row_open = '<div class="runway-row" role="radiogroup"'
        if rendered.count(row_open) != 1:
            return False, "expected exactly one <div class=\"runway-row\" role=\"radiogroup\"...> opening tag, got %d" % rendered.count(row_open)
        caption_pos = rendered.index(caption)
        row_start = rendered.index(row_open)
        if caption_pos >= row_start:
            return False, "expected RUNWAY_SECTION_CAPTION to render before .runway-row opens"
        row_close = rendered.index("</div>", row_start)
        card_positions = [m.start() for m in re.finditer(r'<label class="runway-card', rendered)]
        if len(card_positions) != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % len(card_positions)
        if not all(row_start < pos < row_close for pos in card_positions):
            return False, "expected all three runway-card labels to fall inside the .runway-row container"
        after_row = rendered[row_close + len("</div>"):]
        if "<p" in after_row:
            return False, "expected no <p element anywhere after .runway-row closes - the retired trailing helper paragraph must be gone, not merely moved"
        return True, ""
    check(
        "runway_fieldset() renders RUNWAY_SECTION_CAPTION before .runway-row opens, and no <p element after .runway-row closes (quick task 260901-re6)",
        _runway_row_starts_after_caption_and_nothing_follows_it)

    def _runway_section_caption_appears_exactly_once():
        # 21-05-PLAN.md Task 1 (D-06): THEME_SECTION_CAPTION is retired
        # along with theme_fieldset() — this check narrows to Runway,
        # its own former co-subject, unchanged.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once, got %d" % rendered.count(runway_caption)
        return True, ""
    check(
        "render() carries RUNWAY_SECTION_CAPTION exactly once (quick task 260901-re6, narrowed by "
        "21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired)",
        _runway_section_caption_appears_exactly_once)

    def _each_group_emits_exactly_one_caption_between_heading_and_control():
        # quick task 260901-re6 Task 3: the direct proof of the merge and
        # of the position — the check that would have caught this bug.
        # Calls runway_fieldset()/led_group() directly and asserts each
        # returns markup with exactly one <p occurrence and exactly one
        # section-caption occurrence, with the caption's index falling
        # after the group's own naming element and before the group's
        # control.
        #
        # 21-05-PLAN.md Task 1 (D-06): theme_fieldset() is retired
        # outright — its own row in this table (the one group with an
        # expected <p> count of 2, for its now-gone "Arrivals theme"
        # label) is dropped along with it. The Frame colours card that
        # replaces it is assembled and checked separately (its own
        # tests, elsewhere in this file), not through this direct-call
        # table.
        runway_rendered = config_page.runway_fieldset("3")
        led_rendered = config_page.led_group(True)
        groups = (
            ("runway_fieldset()", runway_rendered, "</h2>", "runway-row", 1),
            # 23-07-PLAN.md Task 2 (D2/CFG-36): the control marker is
            # retargeted in place from "settings-checkbox" to the
            # switch's own class — the LED's control changed, the
            # heading-then-caption-then-control ORDER this row is about
            # did not.
            ("led_group()", led_rendered, "</h2>", 'class="switch"', 1),
        )
        for name, rendered, heading_close_marker, control_marker, expected_p_count in groups:
            if rendered.count("<p") != expected_p_count:
                return False, "expected %s to emit exactly %d <p element(s), got %d" % (name, expected_p_count, rendered.count("<p"))
            if rendered.count("section-caption") != 1:
                return False, "expected %s to emit exactly one section-caption occurrence, got %d" % (name, rendered.count("section-caption"))
            heading_close = rendered.index(heading_close_marker)
            caption_pos = rendered.index("section-caption")
            if not (heading_close < caption_pos):
                return False, "expected %s's caption to fall after %s" % (name, heading_close_marker)
            if control_marker not in rendered:
                return False, "expected %s's control marker %r to be present" % (name, control_marker)
            control_pos = rendered.index(control_marker)
            if not (caption_pos < control_pos):
                return False, "expected %s's caption to fall before its control (%r)" % (name, control_marker)
        return True, ""
    check(
        "runway_fieldset()/led_group() each emit exactly one section-caption <p> element, positioned "
        "after the group's own naming element and before its control (quick task 260901-re6, merge of "
        "origin/main; narrowed by 21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired)",
        _each_group_emits_exactly_one_caption_between_heading_and_control)

    def _bottom_save_button_carries_static_fallback_attr():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR) != 1:
            return False, (
                "expected exactly one data-static-save-fallback occurrence, got %d"
                % rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR))
        button_match = re.search(
            r'<button\b[^>]*%s[^>]*>Save settings</button>'
            % re.escape(config_page.STATIC_SAVE_FALLBACK_ATTR), rendered)
        if not button_match:
            return False, "expected the fallback attribute on a type=\"submit\" Save settings button"
        if 'type="submit"' not in button_match.group(0):
            return False, "expected the fallback button to carry type=\"submit\""
        return True, ""
    check(
        "render()'s bottom Save settings button carries data-static-save-fallback exactly once (D-04)",
        _bottom_save_button_carries_static_fallback_attr)

    def _section_captions_appear_escaped_verbatim_exactly_once():
        # quick task 260901-re6: retargeted onto all three merged caption
        # constants, strengthened from "is present" to "appears exactly
        # once" for each. quick task 260901-s5o: widened in place to a
        # fourth constant, POLL_SECTION_CAPTION - same check, same
        # assertion shape, one more constant, no new check added.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        # 21-05-PLAN.md Task 1 (D-06): THEME_SECTION_CAPTION is retired
        # along with theme_fieldset() — dropped from this list.
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        led_caption = escape_html(config_page.LED_SECTION_CAPTION)
        poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(runway_caption)
        if rendered.count(led_caption) != 1:
            return False, "expected LED_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(led_caption)
        if rendered.count(poll_caption) != 1:
            return False, "expected POLL_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(poll_caption)
        return True, ""
    check(
        "the runway, LED, and poll section captions all appear escaped-verbatim exactly once in "
        "render()'s output (quick task 260901-re6, quick task 260901-s5o; narrowed by 21-05-PLAN.md "
        "Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired)",
        _section_captions_appear_escaped_verbatim_exactly_once)

    def _current_theme_and_runway_are_selected():
        # merge of origin/main (Phase 8): the Runway assertions below
        # predate this merge and are unaffected by it.
        #
        # 06.6.4.1.1-05: Theme's chip radio now carries
        # class="visually-hidden" between value= and checked — the same
        # attribute sequence Runway's own card markup already uses — so
        # the needle grows the intervening class attribute compared to
        # the retired bare radio-list markup.
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "06-24"},
            "poll_cooldown_remaining": 0,
        })
        # Polish fix 4 (D-14c): each runway radio now also carries an
        # explicit form="settings-form" attribute, inserted between
        # class="visually-hidden" and checked.
        if ('value="06-24" class="visually-hidden" form="%s" checked'
                % config_page.SETTINGS_FORM_ID) not in rendered:
            return False, "expected the non-default saved runway (06-24) to be marked selected"
        if ('value="3" class="visually-hidden" form="%s" checked'
                % config_page.SETTINGS_FORM_ID) in rendered:
            return False, "expected runway 3 (not the saved value) to NOT be marked selected"
        if rendered.count("runway-card--selected") != 1:
            return False, "expected exactly one runway-card--selected modifier"
        # 21-05-PLAN.md Task 1 (D-06): theme_fieldset(), Calendar's own
        # compact chip grid, and the Flight-colours add form's compact
        # chip grid are all retired from this legacy SCOPE_ALL render —
        # zero .theme-chip--selected modifiers remain on this page at
        # all (their replacement, the Frame colours card, only ever
        # renders on the Display scope; its own selection state is
        # covered by its own tests elsewhere in this file).
        if "theme-chip--selected" in rendered:
            return False, (
                "expected zero .theme-chip--selected modifiers on this legacy SCOPE_ALL render, got %d"
                % rendered.count("theme-chip--selected"))
        return True, ""
    check(
        "the (non-default) saved runway card is the one marked selected, and this legacy SCOPE_ALL "
        "render carries zero .theme-chip--selected modifiers now that theme_fieldset(), Calendar's own "
        "chip grid, and the rules add-form's own chip grid are all retired from it (D-06)",
        _current_theme_and_runway_are_selected)

    def _poll_trigger_enabled_at_zero_cooldown():
        rendered = config_page.poll_trigger_section(0)
        # UXA-15 (06.6.2-02): scoped to the <button ...> tag itself, not
        # a bare substring search — the zero-cooldown branch's own
        # submit-affordance script now legitimately contains the word
        # "disabled" as a JS property name (`btn.disabled = true;`),
        # which a whole-document substring check would false-positive
        # on.
        button_tag = re.search(r"<button\b[^>]*>", rendered)
        if not button_tag:
            return False, "expected a <button> tag to extract"
        if "disabled" in button_tag.group(0):
            return False, "expected no disabled attribute at zero cooldown"
        if "Trigger poll now" not in rendered:
            return False, "expected the Trigger poll now button copy"
        return True, ""
    check(
        "poll_trigger_section(0) renders an enabled button",
        _poll_trigger_enabled_at_zero_cooldown)

    def _poll_trigger_disabled_with_remaining_seconds():
        rendered = config_page.poll_trigger_section(17)
        if "disabled" not in rendered:
            return False, "expected a disabled attribute at a non-zero cooldown"
        if "17" not in rendered:
            return False, "expected the remaining-seconds figure (17) in the visible copy"
        return True, ""
    check(
        "poll_trigger_section(17) renders a disabled button and the remaining-seconds copy",
        _poll_trigger_disabled_with_remaining_seconds)

    def _poll_section_caption_renders_on_both_branches_under_the_heading():
        # quick task 260901-s5o: the Poll section's own new caption check
        # — the group Task 1's non-goal explicitly excludes from
        # _each_group_emits_exactly_one_caption_between_heading_and_control()
        # (Poll's heading lives in render(), not in poll_trigger_section(),
        # and its disabled branch legitimately emits a second <p>).
        poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
        for cooldown_remaining in (0, 17):
            rendered = config_page.poll_trigger_section(cooldown_remaining)
            if rendered.count("section-caption") != 1:
                return False, (
                    "expected poll_trigger_section(%d) to emit exactly one "
                    "section-caption occurrence, got %d"
                    % (cooldown_remaining, rendered.count("section-caption")))
            if rendered.count(poll_caption) != 1:
                return False, (
                    "expected poll_trigger_section(%d) to carry "
                    "POLL_SECTION_CAPTION escaped-verbatim exactly once, got %d"
                    % (cooldown_remaining, rendered.count(poll_caption)))
            caption_pos = rendered.index("section-caption")
            trigger_pos = rendered.index('<form method="post" action="/poll-now">')
            if not caption_pos < trigger_pos:
                return False, (
                    "expected poll_trigger_section(%d)'s caption to precede "
                    "the poll-trigger form" % cooldown_remaining)

        # The render()-level position proof: the heading is emitted by
        # render(), the caption by poll_trigger_section() — two different
        # functions whose relative order nothing else guards.
        page = config_page.render({
            "device_config": {
                "theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if page.count(poll_caption) != 1:
            return False, (
                "expected render() to carry POLL_SECTION_CAPTION "
                "escaped-verbatim exactly once, got %d" % page.count(poll_caption))
        heading_pos = page.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        page_caption_pos = page.index(poll_caption)
        poll_now_pos = page.index('action="/poll-now"')
        if not heading_pos < page_caption_pos < poll_now_pos:
            return False, (
                "expected the Poll caption to fall between the Poll <h2> "
                "heading and the poll-trigger form's action attribute")
        return True, ""
    check(
        "poll_trigger_section() emits POLL_SECTION_CAPTION exactly once on both the enabled and disabled branches, before the poll-trigger form, and render() places it directly under the Poll <h2> heading (quick task 260901-s5o)",
        _poll_section_caption_renders_on_both_branches_under_the_heading)

    def _poll_trigger_live_countdown_seeded_from_server_value():
        # D-18/A-35 (19-04-PLAN.md): RETARGETED — the disabled branch no
        # longer ships an inline <script> at all (that behaviour moved to
        # companion/static/poll-cooldown.js, D-01/UXA-15 externalized).
        # This check now pins the data-* attribute contract the script
        # reads instead: id="poll-trigger-btn"/id="poll-cooldown-text",
        # the unchanged server-rendered no-JS copy, and every value the
        # script needs exposed as an escape_html()-gated data attribute
        # on the button — never a hardcoded quoted string, so this check
        # stays correct if the id/token constants are ever changed
        # deliberately.
        d17 = config_page.poll_trigger_section(17)
        d5 = config_page.poll_trigger_section(5)
        z = config_page.poll_trigger_section(0)

        if "<script" in d17:
            return False, "expected zero <script occurrences at cooldown=17 (D-18: externalized to poll-cooldown.js)"
        if "<script" in z:
            return False, "expected zero <script occurrences at cooldown=0 (D-18: externalized to poll-cooldown.js)"
        if ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) not in d17:
            return False, "expected the button's id attribute"
        if ('id="%s"' % config_page.POLL_COOLDOWN_TEXT_ID) not in d17:
            return False, "expected the paragraph's id attribute"

        visible_copy = escape_html(
            config_page.POLL_COOLDOWN_HELPER_TEXT.format(n=17))
        if visible_copy not in d17:
            return False, "expected the unchanged, server-rendered no-JS copy"

        template = escape_html(config_page.POLL_COOLDOWN_HELPER_TEXT.format(
            n=config_page.POLL_COOLDOWN_TEMPLATE_TOKEN))
        token = escape_html(config_page.POLL_COOLDOWN_TEMPLATE_TOKEN)
        expected_attrs = [
            'data-cooldown="17"',
            'data-cooldown-text-id="%s"' % escape_html(config_page.POLL_COOLDOWN_TEXT_ID),
            'data-cooldown-template="%s"' % template,
            'data-cooldown-token="%s"' % token,
        ]
        for attr in expected_attrs:
            if attr not in d17:
                return False, "expected data attribute %r on the disabled branch" % (attr,)

        if 'data-cooldown="5"' not in d5:
            return False, "expected the seed to come from the argument (5), not a hardcoded value"

        return True, ""
    check(
        "poll_trigger_section() emits zero <script> elements and ships the D-01/UXA-15 data-* "
        "attribute contract companion/static/poll-cooldown.js reads instead, on both the "
        "disabled and zero-cooldown branches (D-18/A-35, 19-04-PLAN.md)",
        _poll_trigger_live_countdown_seeded_from_server_value)

    def _poll_trigger_zero_cooldown_ships_submit_affordance_script():
        # D-18/A-35 (19-04-PLAN.md): RETARGETED — supersedes the
        # pre-existing "ships its own inline <script>" assertion, no
        # longer true by design now that the UXA-15 disable-on-submit
        # affordance lives in companion/static/poll-cooldown.js. Pins
        # the new contract instead: poll_trigger_section(0) carries
        # id="poll-trigger-btn" and a data-submit-pending attribute, no
        # <script> anywhere, while poll_trigger_section(30) carries the
        # disabled-branch data-cooldown attribute set instead.
        rendered = config_page.poll_trigger_section(0)
        if "Trigger poll now" not in rendered:
            return False, "expected the Trigger poll now button copy"
        # Scoped to the <button ...> tag, not a bare substring search —
        # see _poll_trigger_enabled_at_zero_cooldown()'s own comment on
        # why (poll-cooldown.js's own body legitimately contains
        # "disabled" as a JS property name, though that no longer
        # reaches this render() output at all post-externalization).
        button_tag = re.search(r"<button\b[^>]*>", rendered)
        if not button_tag:
            return False, "expected a <button> tag to extract"
        if "disabled" in button_tag.group(0):
            return False, "expected no disabled attribute at zero cooldown"
        if ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) not in rendered:
            return False, "expected the button's id attribute"
        if "<script" in rendered:
            return False, "expected zero <script occurrences at zero cooldown (D-18: externalized to poll-cooldown.js)"
        if 'data-submit-pending="%s"' % escape_html(config_page.POLL_SUBMIT_PENDING_TEXT) not in rendered:
            return False, "expected the data-submit-pending attribute carrying the pending label"

        nonzero = config_page.poll_trigger_section(30)
        if 'data-cooldown="30"' not in nonzero:
            return False, (
                "expected poll_trigger_section(30) to carry the disabled-branch "
                "data-cooldown attribute")
        return True, ""
    check(
        "poll_trigger_section(0) ships id=\"poll-trigger-btn\" and a data-submit-pending "
        "attribute with zero <script> elements, while poll_trigger_section(30) carries the "
        "disabled-branch data-cooldown attribute instead (D-18/A-35, 19-04-PLAN.md)",
        _poll_trigger_zero_cooldown_ships_submit_affordance_script)

    # The whole forbidden-sink family in one place, so a future reader
    # can see it at a glance (06.5-01-PLAN.md's own sink-safety gate for
    # companion/static/battery-trend.js established this pattern first).
    _FORBIDDEN_SCRIPT_SINKS = (
        "innerHTML", "outerHTML", "insertAdjacentHTML",
        "document.write", "eval(", "fetch(", "XMLHttpRequest",
    )
    _REQUIRED_SCRIPT_OPERATIONS = (
        "use strict", "textContent", "removeAttribute",
        "setInterval", "clearInterval",
    )
    _POLL_COOLDOWN_JS_PATH = os.path.join(HERE, "static", "poll-cooldown.js")

    def _poll_cooldown_script_has_no_forbidden_sink():
        # D-18/A-35 (19-04-PLAN.md): RETARGETED IN PLACE — the countdown
        # no longer renders as an inline <script>, so this check now
        # asserts poll_trigger_section(17) contains NO <script substring
        # at all plus the required data attributes, and moves the
        # forbidden-sink/required-operation coverage this check used to
        # provide onto companion/static/poll-cooldown.js's own source
        # (read from disk) instead of dropping it.
        rendered = config_page.poll_trigger_section(17)
        if "<script" in rendered:
            return False, "expected zero <script occurrences at cooldown=17 (D-18: externalized to poll-cooldown.js)"
        for attr in (
                'data-cooldown="17"',
                'data-cooldown-text-id="%s"' % escape_html(config_page.POLL_COOLDOWN_TEXT_ID)):
            if attr not in rendered:
                return False, "expected data attribute %r on the disabled branch" % (attr,)
        with open(_POLL_COOLDOWN_JS_PATH) as fh:
            src = fh.read()
        for forbidden in _FORBIDDEN_SCRIPT_SINKS:
            if forbidden in src:
                return False, "forbidden sink found in poll-cooldown.js: %r" % (forbidden,)
        for required in _REQUIRED_SCRIPT_OPERATIONS:
            if required not in src:
                return False, "expected required operation %r in poll-cooldown.js" % (required,)
        return True, ""
    check(
        "poll_trigger_section(17) carries no <script substring and ships the countdown's "
        "required data attributes; companion/static/poll-cooldown.js's own source contains "
        "none of the forbidden HTML-writing/eval/network sinks and does contain strict mode "
        "plus the permitted DOM/timer operations (retargeted, D-18/A-35)",
        _poll_cooldown_script_has_no_forbidden_sink)

    def _poll_submit_script_has_no_forbidden_sink():
        # D-18/A-35 (19-04-PLAN.md): RETARGETED IN PLACE — the
        # disable-on-submit affordance no longer renders as an inline
        # <script>, so this check now asserts poll_trigger_section(0)
        # contains NO <script substring at all plus the
        # data-submit-pending attribute, and moves the forbidden-sink
        # coverage onto companion/static/poll-cooldown.js's own source
        # (read from disk) instead of dropping it.
        rendered = config_page.poll_trigger_section(0)
        if "<script" in rendered:
            return False, "expected zero <script occurrences at cooldown=0 (D-18: externalized to poll-cooldown.js)"
        if 'data-submit-pending="%s"' % escape_html(config_page.POLL_SUBMIT_PENDING_TEXT) not in rendered:
            return False, "expected the data-submit-pending attribute carrying the pending label"
        with open(_POLL_COOLDOWN_JS_PATH) as fh:
            src = fh.read()
        for forbidden in _FORBIDDEN_SCRIPT_SINKS:
            if forbidden in src:
                return False, "forbidden sink found in poll-cooldown.js: %r" % (forbidden,)
        if "use strict" not in src:
            return False, "expected strict mode"
        if "addEventListener" not in src:
            return False, "expected a submit event listener"
        return True, ""
    check(
        "poll_trigger_section(0) carries no <script substring and ships the data-submit-pending "
        "attribute; companion/static/poll-cooldown.js's own source contains none of the "
        "forbidden HTML-writing/eval/network sinks and attaches a submit listener (retargeted, "
        "D-18/A-35, UXA-15)",
        _poll_submit_script_has_no_forbidden_sink)

    def _valid_save_writes_both_and_returns_saved_key():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "black", "tracked_runway": "06-24"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            # 06.6.4.1 (D-05): led_enabled is now resolved by handle_post()
            # itself, with checkbox-absent-means-False semantics (never
            # carried forward like theme/runway) — this posted form omits
            # led_enabled entirely, so the persisted value is False, not
            # DEFAULT_LED_ENABLED (True). The theme value itself is
            # "black", matching what the fixture above actually posted —
            # pre-merge this assertion read "sky" because "black" wasn't
            # yet a valid THEME_IDS entry and handle_post()'s validation
            # silently kept the prior/default value instead; the merged
            # Phase 8 registry (19 real entries) makes "black" valid, so
            # it now persists as posted.
            # Phase 15 (15-02): load_device_config() now always returns
            # theme_arriving too. It is None here because this post carries no
            # arrivals override, and None means "same theme as departures" —
            # never DEFAULT_THEME_ID. Added to this full-dict equality the same
            # mechanical way 15-02 updated its 9 siblings in
            # server/test_config_history.py; the assertion stays an exact-dict
            # comparison rather than being loosened to a subset check.
            # Phase 16 (16-02): load_device_config() now always returns
            # calendar_theme_id too, None here because no calendar theme has
            # been chosen. Same mechanical update as the Phase 15 line above,
            # and for the same reason — a new always-returned key changes what
            # this exact-dict comparison must expect. Still an exact-dict
            # comparison, deliberately not loosened to a subset check.
            # 19-12-PLAN.md Task 1 (D-23): load_device_config() now always
            # returns screen_id too, "plane-frame" (DEFAULT_SCREEN_ID) here
            # because this post carries no screen_id field. Same mechanical
            # update as the two lines above.
            # 20-02-PLAN.md Task 3 (D-26): load_device_config() now always
            # returns notifications too.
            # 20-11-PLAN.md Task 1 (D-26): screens.GROUP_NOTIFICATIONS now
            # joins the legacy SCOPE_ALL tuple this un-scoped post resolves
            # to (submitted_scope(form) with no "scope" field present
            # returns SCOPE_ALL), so the group is now IN SCOPE for this
            # post — its two checkboxes resolve absent-means-False, like
            # every other in-scope checkbox this handler owns, rather than
            # DEFAULT_NOTIFICATIONS's own True/True. The topic URL still
            # carries forward the (here, never-set) on-disk value, and lang
            # falls back to "en" (this test's ctx carries no "lang" key).
            # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): display_enabled is
            # True here, not the pre-22-05 False — this posted form omits
            # display_enabled entirely, and that field's absence now means
            # "leave unchanged" UNCONDITIONALLY (never "switch it off"),
            # so on this fresh state directory it falls through to
            # DEFAULT_DISPLAY_ENABLED (True), never to a hard-coded False.
            # quiet_hours_enabled stays False here too, but for a different
            # reason now: its own absence also means "leave unchanged",
            # and DEFAULT_QUIET_HOURS_ENABLED already IS False, so the
            # value is coincidentally unchanged from the pre-22-05 fixture.
            # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1): led_enabled is
            # True here, not the pre-23-07 False, for exactly the reason
            # display_enabled already was — this posted form omits it and
            # that absence now means "leave unchanged" unconditionally,
            # so on a fresh state directory it falls through to
            # DEFAULT_LED_ENABLED rather than to a hard-coded False.
            if on_disk != {"theme": "black", "theme_arriving": None, "calendar_theme_id": None, "tracked_runway": "06-24", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "display_enabled": True, "wake_interval_s": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": False, "frame_silent": False, "lang": "en"}}:
                return False, "on-disk config does not match the posted values: %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a valid theme and runway writes both and returns the saved flash key",
        _valid_save_writes_both_and_returns_saved_key)

    def _nonmember_theme_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "not-a-real-theme", "tracked_runway": "06-24"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member theme writes nothing and returns the save-failure flash key",
        _nonmember_theme_writes_nothing)

    def _nonmember_runway_writes_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "black", "tracked_runway": "not-a-real-runway"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a non-member runway writes nothing and returns the save-failure flash key",
        _nonmember_runway_writes_nothing)

    def _theme_only_post_carries_runway_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "black"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a theme but no runway field carries the existing runway forward unchanged",
        _theme_only_post_carries_runway_forward)

    def _path_traversal_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "../../etc/passwd", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a path-traversal-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a directory-traversal-shaped theme value is rejected by the membership test",
        _path_traversal_theme_rejected)

    def _sql_fragment_theme_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "sky'; DROP TABLE flights; --", "tracked_runway": "3"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a SQL-shaped theme, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a SQL-fragment-shaped theme value is rejected by the membership test",
        _sql_fragment_theme_rejected)

    def _save_oserror_returns_failure_key_not_raise():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            original_save = device_config.save_device_config

            def _raising_save(*args, **kwargs):
                raise OSError("simulated disk failure")

            device_config.save_device_config = _raising_save
            try:
                flash_key = config_page.handle_post(
                    {"theme": "black", "tracked_runway": "3"}, ctx)
            finally:
                device_config.save_device_config = original_save
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED when save_device_config() raises OSError, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a save that raises OSError returns the save-failure flash key rather than propagating",
        _save_oserror_returns_failure_key_not_raise)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 2 (D-05): handle_post() absorbs LED validation as one
    # all-or-nothing submission — one check per <behavior> bullet.
    # ------------------------------------------------------------------

    # merge of origin/main (Phase 8): main's own version of this section
    # still tested the pre-06.6.4.1-07 dual-form architecture —
    # led_fieldset() as a standalone function, and a second, distinct
    # <form action="/config-led"> — because main never received that
    # plan's LED-into-the-single-Settings-form merge (see that plan's own
    # SUMMARY: "the 8 checks exercising the now-deleted led_fieldset()/
    # led_section()/handle_led_post() were deleted outright ... 1 new
    # check pins the retired /config-led route now 404s"). Those three
    # functions (_led_fieldset_checked_true, _led_fieldset_unchecked_false,
    # _render_has_second_form_for_led_route) tested functions/routes that
    # no longer exist on this side and are dropped, not reconciled — this
    # is the same retirement 06.6.4.1-07 already made, main just hadn't
    # merged it yet. The unified-form behaviour they were partially
    # re-covering is already exercised by the bullet-per-behaviour checks
    # below (_handle_post_empty_form_persists_led_false and its
    # siblings), so no coverage gap is left behind.
    def _handle_post_empty_form_leaves_led_unchanged():
        # Bullet 1: the shape a browser sends when nothing is checked and
        # nothing is selected.
        #
        # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25): RETARGETED IN
        # PLACE, and made two-directional. It used to assert this empty
        # body persists led_enabled False, which was the correct reading
        # while the LED checkbox was still rendered in this form. It is
        # not any more: absence now means "leave unchanged", so the honest
        # assertion is that BOTH a stored True and a stored False survive.
        # Asserting only the False direction would pass on a handler that
        # hard-codes False, which is the very behaviour this change
        # removes.
        for stored in (True, False):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                device_config.save_device_config(tmpdir, led_enabled=stored)
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post({}, ctx)
                if flash_key != config_page.FLASH_SAVED:
                    return False, "expected FLASH_SAVED, got %r" % (flash_key,)
                on_disk = device_config.load_device_config(tmpdir)
                if on_disk["led_enabled"] is not stored:
                    return False, (
                        "expected an empty body to LEAVE the stored led_enabled %r unchanged, "
                        "got %r" % (stored, on_disk["led_enabled"]))
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post({}, ctx) - the shape a browser sends when nothing is checked and nothing is "
        "selected - LEAVES the stored led_enabled unchanged in both directions and returns the "
        "saved flash key (retargeted in place from absent-means-False by 23-07-PLAN.md Task 2)",
        _handle_post_empty_form_leaves_led_unchanged)

    def _handle_post_led_checkbox_value_persists_led_true():
        # Bullet 2.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"led_enabled": config_page.LED_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not True:
                return False, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True",
        _handle_post_led_checkbox_value_persists_led_true)

    def _handle_post_crafted_led_value_rejected_byte_identical():
        # Bullet 3.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3", led_enabled=True)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"led_enabled": "<crafted>"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"led_enabled\": \"<crafted>\"}, ctx) returns the save-failed flash key and leaves device_config.json byte-identical",
        _handle_post_crafted_led_value_rejected_byte_identical)

    def _handle_post_invalid_theme_rejects_led_half_too():
        # Bullet 4: an invalid theme rejects the LED half too - proving
        # the merge stays all-or-nothing across all three fields.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "sky", "3", led_enabled=False)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "not-a-real-theme", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"theme\": \"<not a registered theme>\", \"led_enabled\": LED_CHECKBOX_VALUE}, ctx) returns save-failed and leaves the file byte-identical (an invalid theme rejects the LED half too)",
        _handle_post_invalid_theme_rejects_led_half_too)

    def _handle_post_valid_runway_and_led_persist_together_one_call():
        # Bullet 5: persists both in one call.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"tracked_runway": "06-24", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected tracked_runway 06-24 on disk, got %r" % (on_disk["tracked_runway"],)
            if on_disk["led_enabled"] is not True:
                return False, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"tracked_runway\": <a real runway id>, \"led_enabled\": LED_CHECKBOX_VALUE}, ctx) persists both in one call and returns the saved flash key",
        _handle_post_valid_runway_and_led_persist_together_one_call)

    # ------------------------------------------------------------------
    # 10-05-PLAN.md Task 3: handle_post()'s quiet-hours save/reject paths
    # (D-03/D-04, 10-UI-SPEC.md's unchecked-checkbox-still-saves-times
    # semantics — the resolution of 10-RESEARCH.md Assumption A1).
    # ------------------------------------------------------------------

    def _handle_post_quiet_hours_checkbox_on_persists_all_three():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "quiet_hours_enabled": config_page.QUIET_HOURS_CHECKBOX_VALUE,
                    "quiet_hours_start": "22:30", "quiet_hours_end": "06:15",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_enabled"] is not True:
                return False, "expected quiet_hours_enabled True on disk, got %r" % (on_disk["quiet_hours_enabled"],)
            if on_disk["quiet_hours_start"] != "22:30" or on_disk["quiet_hours_end"] != "06:15":
                return False, "expected the submitted times to persist, got %r/%r" % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"])
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with quiet_hours_enabled=QUIET_HOURS_CHECKBOX_VALUE and both times persists all three quiet-hours fields and returns the saved flash key",
        _handle_post_quiet_hours_checkbox_on_persists_all_three)

    def _handle_post_quiet_hours_checkbox_absent_still_persists_times():
        # The direct pin of 10-UI-SPEC.md's resolution of 10-RESEARCH.md
        # Assumption A1 / Open Question 2: a user can pre-configure a
        # window before ever turning it on. Must not be dropped or
        # inverted.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"quiet_hours_start": "22:30", "quiet_hours_end": "06:15"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["quiet_hours_enabled"] is not False:
                return False, "expected quiet_hours_enabled False on disk (checkbox absent), got %r" % (on_disk["quiet_hours_enabled"],)
            if on_disk["quiet_hours_start"] != "22:30" or on_disk["quiet_hours_end"] != "06:15":
                return False, "expected the edited times to persist even though the checkbox was left unchecked, got %r/%r" % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"])
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with quiet_hours_enabled absent but both times submitted persists quiet_hours_enabled False and the edited times (a user can pre-configure a window before enabling it)",
        _handle_post_quiet_hours_checkbox_absent_still_persists_times)

    def _handle_post_malformed_quiet_hours_time_rejected_byte_identical():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"quiet_hours_start": "24:00"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a malformed HH:MM, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"quiet_hours_start\": \"24:00\"}, ctx) against a legitimately-saved config returns the save-failed flash key and leaves device_config.json byte-identical",
        _handle_post_malformed_quiet_hours_time_rejected_byte_identical)

    def _handle_post_crafted_quiet_hours_checkbox_value_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"quiet_hours_enabled": "yes"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted quiet_hours_enabled value, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"quiet_hours_enabled\": \"yes\"}, ctx) returns the save-failed flash key, matching the LED field's own third shape",
        _handle_post_crafted_quiet_hours_checkbox_value_rejected)

    def _handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "quiet_hours_end": "24:00"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical (the theme must not persist either), it changed"
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme"] != "black":
                return False, "expected the pre-existing theme to be unchanged, got %r" % (on_disk["theme"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post with a valid theme AND a malformed quiet_hours_end returns save-failed and persists neither — the theme on disk is unchanged (all-or-nothing across groups)",
        _handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing)

    # ------------------------------------------------------------------
    # 11-03-PLAN.md Task 2: handle_post()'s wake_interval_s conversion,
    # rejection, and leave-unchanged checks (D-05, 11-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _handle_post_wake_interval_string_converts_to_int_and_persists():
        # The direct regression guard for 11-RESEARCH.md Pitfall 1: a
        # stored string would round-trip through load_device_config() as
        # None (normalise_wake_interval_s() rejects non-int values) and
        # silently look like "unset" instead of like a bug — asserting
        # isinstance(..., int) explicitly is what catches that.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if not isinstance(on_disk["wake_interval_s"], int):
                return False, "expected the submitted string \"120\" to convert to an int, got %r" % (on_disk["wake_interval_s"],)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s 120 on disk, got %r" % (on_disk["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"wake_interval_s\": \"120\"}, ctx) explicitly string-to-int converts before persisting, stores the int (not a string) 120, and returns the saved flash key (11-RESEARCH.md Pitfall 1 regression guard)",
        _handle_post_wake_interval_string_converts_to_int_and_persists)

    def _handle_post_wake_interval_rejection_paths_byte_identical():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if seed_flash != config_page.FLASH_SAVED:
                return False, "expected the seeding save to succeed, got %r" % (seed_flash,)
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            # "abc"/"1.5" fail at this handler's own int() gate; "59"/
            # "3601"/"-1" are syntactically valid ints but fail inside
            # save_device_config()'s bounded-range check.
            for bad in ("abc", "1.5", "59", "3601", "-1"):
                flash_key = config_page.handle_post({"wake_interval_s": bad}, ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for wake_interval_s=%r, got %r" % (bad, flash_key)
                if before != after:
                    return False, "expected device_config.json to stay byte-identical after rejecting wake_interval_s=%r" % (bad,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post rejects \"abc\"/\"1.5\" (handler's int() gate) and \"59\"/\"3601\"/\"-1\" (save_device_config()'s bounded-range check), each returning the save-failed flash key and leaving a pre-existing device_config.json byte-identical",
        _handle_post_wake_interval_rejection_paths_byte_identical)

    def _handle_post_wake_interval_empty_or_absent_leaves_unchanged():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
            if seed_flash != config_page.FLASH_SAVED:
                return False, "expected the seeding save to succeed, got %r" % (seed_flash,)
            empty_flash = config_page.handle_post({"wake_interval_s": ""}, ctx)
            if empty_flash != config_page.FLASH_SAVED:
                return False, "expected an empty-string wake_interval_s to succeed (leave unchanged), got %r" % (empty_flash,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s to remain 120 after an empty-string submission, got %r" % (on_disk["wake_interval_s"],)
            absent_flash = config_page.handle_post({}, ctx)
            if absent_flash != config_page.FLASH_SAVED:
                return False, "expected an absent wake_interval_s key to succeed (leave unchanged), got %r" % (absent_flash,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["wake_interval_s"] != 120:
                return False, "expected wake_interval_s to remain 120 after an absent-key submission, got %r" % (on_disk["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "after a save that stored wake_interval_s 120, a later submission with wake_interval_s as the empty string, and another with the key absent entirely, both return the saved flash key and leave the stored value at 120 (11-RESEARCH.md Open Question 2)",
        _handle_post_wake_interval_empty_or_absent_leaves_unchanged)

    # ------------------------------------------------------------------
    # 19-07-PLAN.md Task 1 (D-07/A-25): handle_post()'s new optional
    # `errors` dict parameter — the legacy no-errors callers stay
    # byte-identical, and each new field-level pre-check fills exactly
    # one keyed message without changing the returned flash-key string.
    # ------------------------------------------------------------------

    def _handle_post_no_errors_arg_returns_identical_flash_keys():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            valid_flash = config_page.handle_post({"theme": "white"}, ctx)
            if valid_flash != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for a representative valid save, got %r" % (valid_flash,)
            invalid_flash = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
            if invalid_flash != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a representative invalid save, got %r" % (invalid_flash,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx) with no errors argument still returns exactly the same flash keys it did "
        "before this plan, for both a representative valid save and a representative invalid save",
        _handle_post_no_errors_arg_returns_identical_flash_keys)

    def _handle_post_errors_dict_filled_for_each_real_user_error_field():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            cases = (
                ({"wake_interval_s": "7"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
                ({"wake_interval_s": "abc"}, "wake_interval_s", config_page.ERROR_WAKE_INTERVAL_RANGE),
                ({"quiet_hours_start": "24:00"}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                ({"quiet_hours_start": ""}, "quiet_hours_start", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                ({"quiet_hours_end": "not-a-time"}, "quiet_hours_end", config_page.ERROR_QUIET_HOURS_TIME_SHAPE),
                (
                    {
                        "calendar_url": "https://example.com/feed.ics",
                        "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
                    },
                    "calendar_url", config_page.ERROR_CALENDAR_URL_INVALID,
                ),
            )
            for form, field, expected_message in cases:
                errors = {}
                flash_key = config_page.handle_post(form, ctx, errors=errors)
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for form=%r, got %r" % (form, flash_key)
                if errors != {field: expected_message}:
                    return False, "expected errors == {%r: %r} for form=%r, got %r" % (
                        field, expected_message, form, errors)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx, errors=d) fills d with exactly one field-keyed message for each real-user-error "
        "case (wake_interval_s non-numeric/out-of-range, quiet_hours_start/quiet_hours_end malformed including "
        "empty, and a contradictory calendar_url+calendar_disconnect submission)",
        _handle_post_errors_dict_filled_for_each_real_user_error_field)

    def _handle_post_errors_dict_stays_empty_on_a_valid_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            errors = {}
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "quiet_hours_start": "22:30",
                    "quiet_hours_end": "06:15", "wake_interval_s": "120",
                },
                ctx, errors=errors)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if errors != {}:
                return False, "expected errors to stay empty on a valid save, got %r" % (errors,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post(form, ctx, errors=d) leaves d empty when the save succeeds",
        _handle_post_errors_dict_stays_empty_on_a_valid_save)

    def _handle_post_empty_quiet_hours_start_writes_nothing():
        # The all-or-nothing contract's own direct pin for the NEW
        # pre-check: an empty quiet_hours_start must reject before
        # save_device_config() is ever called, leaving a pre-existing
        # config byte-identical - not merely returning the right flash
        # key.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            errors = {}
            flash_key = config_page.handle_post(
                {"theme": "white", "quiet_hours_start": ""}, ctx, errors=errors)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for an empty quiet_hours_start, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to stay byte-identical, it changed"
            if errors != {"quiet_hours_start": config_page.ERROR_QUIET_HOURS_TIME_SHAPE}:
                return False, "expected exactly one quiet_hours_start error, got %r" % (errors,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({\"theme\": \"white\", \"quiet_hours_start\": \"\"}, ctx, errors=d) rejects the whole save, "
        "writes nothing (the theme must not persist either), and reports the error on quiet_hours_start alone",
        _handle_post_empty_quiet_hours_start_writes_nothing)

    def _local_quiet_hours_regex_agrees_with_save_device_config():
        # 19-07-PLAN.md Task 1: this module's own local HH:MM shape gate
        # (_QUIET_HOURS_TIME_RE) is a UX pre-check only -
        # save_device_config()'s identical gate stays authoritative. This
        # pins the two never silently drifting apart, over the exact
        # table of inputs the plan names.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            for candidate in ("", "7:00", "07:00", "24:00", "abc", "23:59", "00:00"):
                pre_check_says_ok = bool(config_page._QUIET_HOURS_TIME_RE.match(candidate))
                try:
                    device_config.save_device_config(
                        tmpdir, quiet_hours_start=candidate)
                    save_device_config_says_ok = True
                except ValueError:
                    save_device_config_says_ok = False
                if pre_check_says_ok != save_device_config_says_ok:
                    return False, (
                        "disagreement for %r: pre-check says ok=%r, save_device_config() says ok=%r"
                        % (candidate, pre_check_says_ok, save_device_config_says_ok))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "config_page._QUIET_HOURS_TIME_RE agrees with server.device_config.save_device_config()'s own HH:MM "
        "shape gate over the table \"\"/\"7:00\"/\"07:00\"/\"24:00\"/\"abc\"/\"23:59\"/\"00:00\"",
        _local_quiet_hours_regex_agrees_with_save_device_config)

    # ------------------------------------------------------------------
    # 19-07-PLAN.md Task 2 (D-07/A-25): render() repopulates every
    # control from a rejected save's own submission and renders each
    # field's error message and aria wiring — while staying byte-
    # identical to today whenever errors/submitted are not passed.
    # ------------------------------------------------------------------

    _TASK2_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "now": "2026-09-07T09:12:04+00:00",
    }

    def _render_no_new_args_byte_identical_and_no_field_error_markup():
        plain = config_page.render(_TASK2_BASE_CTX)
        explicit_none = config_page.render(_TASK2_BASE_CTX, errors=None, submitted=None)
        if plain != explicit_none:
            return False, "expected render(ctx) to be byte-identical to render(ctx, errors=None, submitted=None)"
        if "field-error" in plain:
            return False, "expected no field-error markup when no errors are passed"
        return True, ""
    check(
        "render(ctx) with no new arguments is byte-identical to render(ctx, errors=None, submitted=None) and "
        "contains no field-error markup",
        _render_no_new_args_byte_identical_and_no_field_error_markup)

    def _render_wake_interval_error_shows_message_value_and_aria():
        rendered = config_page.render(
            _TASK2_BASE_CTX, errors={"wake_interval_s": "msg"},
            submitted={"wake_interval_s": "7"})
        if rendered.count("msg") != 1:
            return False, "expected the error message to render exactly once, got %d" % rendered.count("msg")
        if 'value="7"' not in rendered:
            return False, "expected the submitted value 7 to be echoed back into the input"
        # 22-10-PLAN.md Task 3 (B17): retargeted in place for the new id=.
        input_match = re.search(
            r'<input type="number" id="[^"]*" name="wake_interval_s"[^>]*>', rendered)
        if not input_match:
            return False, "expected the wake_interval_s input to still be present"
        if 'aria-invalid="true"' not in input_match.group(0):
            return False, "expected aria-invalid=\"true\" on the errored input"
        describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
        if not describedby_match:
            return False, "expected an aria-describedby attribute on the errored input"
        # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - the
        # value is now a SPACE-SEPARATED list (the hint id first, then
        # the error id), not a single id, so each token must be checked
        # individually against the rendered page's own ids.
        ids = describedby_match.group(1).split(" ")
        if len(ids) != 2:
            return False, "expected exactly two space-separated ids (hint, then error), got %r" % (ids,)
        if ids[0] != config_page.WAKE_INTERVAL_SECTION_CAPTION_ID:
            return False, "expected the hint id to come first, got %r" % (ids,)
        for token in ids:
            if ('id="%s"' % token) not in rendered:
                return False, "expected an element carrying id=%r matching aria-describedby" % (token,)
        return True, ""
    check(
        "render(ctx, errors={\"wake_interval_s\": \"msg\"}, submitted={\"wake_interval_s\": \"7\"}) renders the "
        "message once, echoes value=\"7\" back into the input, and sets aria-invalid plus a matching "
        "aria-describedby",
        _render_wake_interval_error_shows_message_value_and_aria)

    def _render_submitted_theme_id_checked_even_when_differs_from_stored():
        rendered = config_page.render(
            dict(_TASK2_BASE_CTX, device_config={"theme": "white", "tracked_runway": "3"}),
            submitted={"theme": "black"}, scope=config_page.SCOPE_DISPLAY)
        if not re.search(r'name="theme" value="black"[^>]*checked', rendered):
            return False, "expected the submitted theme (black) to render checked even though the stored theme is white"
        if re.search(r'name="theme" value="white"[^>]*checked', rendered):
            return False, "expected the stored theme (white) to NOT render checked once a different submission is being repopulated"
        return True, ""
    check(
        "a submitted theme id is rendered as the CHECKED radio even when it differs from the stored theme "
        "(D-07 repopulation)",
        _render_submitted_theme_id_checked_even_when_differs_from_stored)

    def _render_both_quiet_hours_time_inputs_carry_required():
        rendered = config_page.render(_TASK2_BASE_CTX)
        start_match = re.search(r'<input type="time" name="quiet_hours_start"[^>]*>', rendered)
        end_match = re.search(r'<input type="time" name="quiet_hours_end"[^>]*>', rendered)
        if not start_match or "required" not in start_match.group(0):
            return False, "expected the quiet_hours_start input to carry required"
        if not end_match or "required" not in end_match.group(0):
            return False, "expected the quiet_hours_end input to carry required"
        return True, ""
    check(
        "both quiet-hours time inputs carry required in the rendered Settings page",
        _render_both_quiet_hours_time_inputs_carry_required)

    def _calendar_connect_url_error_never_echoes_the_submitted_secret():
        # 20-09-PLAN.md Task 1 (D-14c), retargeted by 21-07-PLAN.md
        # Task 1 (D-13) after calendar_connect_section()'s retirement:
        # the write-only calendar_url field's own `errors` parameter now
        # lives directly on the merged calendar_group() — it never
        # accepts `submitted` at all (nothing to repopulate: the one
        # field it renders is write-only), so there is no submitted URL
        # for it to echo in the first place.
        rendered = config_page.calendar_group(
            False, False, None, None, "2026-09-07T09:12:04+00:00", 0,
            errors={"calendar_url": "msg"})
        if "msg" not in rendered:
            return False, "expected the calendar_url error message to render"
        if 'name="calendar_url"' not in rendered:
            return False, "expected the calendar_url field itself to still render"
        after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
        if "value=" in after_name:
            return False, "expected no value attribute on the calendar_url field even with an error present"
        return True, ""
    check(
        "the merged calendar_group(..., errors={\"calendar_url\": \"msg\"}) renders the error message "
        "under the field while the write-only field itself still carries no value attribute at all "
        "(D-07/T-19-12/D-13, retargeted after calendar_connect_section()'s retirement)",
        _calendar_connect_url_error_never_echoes_the_submitted_secret)

    def _style_css_styles_field_error():
        style_path = os.path.join(REPO_ROOT, "companion", "static", "style.css")
        with open(style_path, encoding="utf-8") as fh:
            css = fh.read()
        idx = css.find(".field-error")
        if idx == -1:
            return False, "expected a .field-error rule in companion/static/style.css"
        window = css[idx:idx + 400]
        if "--color-status-error" not in window:
            return False, "expected .field-error to read the existing --color-status-error token"
        return True, ""
    check(
        "companion/static/style.css styles .field-error using the existing --color-status-error token "
        "(cross-file DOM contract guard)",
        _style_css_styles_field_error)

    # ------------------------------------------------------------------
    # 19-07-PLAN.md Task 3 (D-07/A-25): the legacy no-errors-arg contract
    # is intact even for a rejected save — companion/app.py's own
    # errors-branch (which now ALSO fires whenever errors is non-empty)
    # depends on handle_post() still returning FLASH_SAVE_FAILED, not
    # some new sentinel, when no errors dict is passed at all.
    # ------------------------------------------------------------------

    def _handle_post_rejected_save_without_errors_arg_still_returns_save_failed():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme": "not-a-real-theme"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED with no errors argument, got %r" % (flash_key,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a rejected save still returns FLASH_SAVE_FAILED from handle_post() when no errors dict is passed "
        "(the legacy contract is intact)",
        _handle_post_rejected_save_without_errors_arg_still_returns_save_failed)

    # ------------------------------------------------------------------
    # 06.6.4.1-07 (D-05): led_fieldset()/led_section()/handle_led_post()
    # and the separate POST /config-led route were retired outright —
    # the eight checks that used to exercise them directly were deleted
    # here (they would now raise AttributeError against the deleted
    # symbols). Their coverage is superseded, not lost: the merged
    # led_group()/handle_post() checks above (D-05 handle_post() bullets)
    # and _render_shape_read_only_theme_runway_cards_led_group_and_save_button()
    # near the top of this file already cover the same three submitted-
    # value shapes, the cross-field all-or-nothing rejection, and the
    # single-heading-level/no-<fieldset> markup contract.
    # ------------------------------------------------------------------

    def _render_has_no_action_pointing_at_retired_led_route():
        # 06.6.4.1 (D-05), retired route confirmed 06.6.4.1-07: the LED
        # group is merged into the single settings form — render() must
        # never emit a second, independently-submittable
        # <form action="/config-led"> at all. The separate POST
        # /config-led route and its handler no longer exist anywhere in
        # the app, so this is now a pure markup regression guard.
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if 'action="%s"' % config_page.SETTINGS_ROUTE not in rendered:
            return False, "expected the settings form action to be present"
        if 'action="/config-led"' in rendered:
            return False, "expected no action=\"/config-led\" in render()'s output (D-05 merge)"
        return True, ""
    check(
        "render() emits no action pointing at the retired separate LED form path (D-05)",
        _render_has_no_action_pointing_at_retired_led_route)

    def _config_page_exposes_no_retired_led_symbols():
        # 06.6.4.1-07 (D-05): source assertion that the deleted handler,
        # section wrapper, and markup builder are genuinely gone, not
        # merely unreferenced.
        for name in ("led_fieldset", "led_section", "handle_led_post"):
            if hasattr(config_page, name):
                return False, "expected config_page to expose no %r attribute" % name
        return True, ""
    check(
        "companion.pages.config_page exposes neither led_fieldset, led_section, nor "
        "handle_led_post (all three retired, D-05)",
        _config_page_exposes_no_retired_led_symbols)

    def _config_page_exposes_no_retired_helper_or_description_symbols():
        # quick task 260901-re6 Task 3: source assertion that the five
        # constants retired by Task 1 (THEME_HELPER_TEXT,
        # THEME_SECTION_DESCRIPTION, RUNWAY_HELPER_TEXT,
        # RUNWAY_SECTION_DESCRIPTION, LED_HELPER_TEXT) are genuinely gone,
        # not merely unreferenced — same precedent
        # _config_page_exposes_no_retired_led_symbols() above set for the
        # 06.6.4.1-07 LED-route retirement.
        retired = (
            "THEME_HELPER_TEXT", "THEME_SECTION_DESCRIPTION",
            "RUNWAY_HELPER_TEXT", "RUNWAY_SECTION_DESCRIPTION",
            "LED_HELPER_TEXT")
        for name in retired:
            if hasattr(config_page, name):
                return False, "expected config_page to expose no %r attribute" % name
        return True, ""
    check(
        "companion.pages.config_page exposes none of THEME_HELPER_TEXT/THEME_SECTION_DESCRIPTION/"
        "RUNWAY_HELPER_TEXT/RUNWAY_SECTION_DESCRIPTION/LED_HELPER_TEXT (all five retired, quick task 260901-re6)",
        _config_page_exposes_no_retired_helper_or_description_symbols)

    # ------------------------------------------------------------------
    # Runway-image existence detection (Task 1, D-03) - each check uses
    # its own tempfile.mkdtemp() image_dir and never touches the real
    # companion/static/ (06.4-RESEARCH.md Pitfall 1).
    # ------------------------------------------------------------------

    def _runway_images_available_empty_dir_yields_empty_set():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != set():
                return False, "expected an empty set for an empty directory, got %r" % (result,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() returns the empty set when the image directory has no files",
        _runway_images_available_empty_dir_yields_empty_set)

    def _runway_images_available_detects_single_present_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            with open(os.path.join(tmpdir, "runway-3.png"), "wb") as fh:
                fh.write(b"not-a-real-png-just-test-bytes")
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != {"3"}:
                return False, "expected {'3'}, got %r" % (result,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() returns exactly {'3'} when only runway-3.png exists",
        _runway_images_available_detects_single_present_file)

    def _runway_images_available_missing_dir_yields_empty_set_no_raise():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        nonexistent = os.path.join(tmpdir, "does-not-exist")
        shutil.rmtree(tmpdir, ignore_errors=True)
        result = companion_app.runway_images_available(image_dir=nonexistent)
        if result != set():
            return False, "expected an empty set for a non-existent directory, got %r" % (result,)
        return True, ""
    check(
        "runway_images_available() returns the empty set (does not raise) when image_dir does not exist",
        _runway_images_available_missing_dir_yields_empty_set_no_raise)

    def _runway_images_available_bounded_by_registry_not_directory_listing():
        tmpdir = tempfile.mkdtemp(prefix="skypane-runway-images-")
        try:
            with open(os.path.join(tmpdir, "runway-99.png"), "wb") as fh:
                fh.write(b"not-a-registry-member")
            with open(os.path.join(tmpdir, "style.css"), "w") as fh:
                fh.write("/* not a runway image */")
            result = companion_app.runway_images_available(image_dir=tmpdir)
            if result != set():
                return False, (
                    "expected an empty set (non-registry files must be ignored), got %r"
                    % (result,))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "runway_images_available() ignores files that are not RUNWAY_IDS members, proving it is registry-bounded not directory-listing-bounded",
        _runway_images_available_bounded_by_registry_not_directory_listing)

    # ------------------------------------------------------------------
    # runway_fieldset() image emission (Task 2, D-01/D-03) - unit checks
    # against the string output only, no filesystem/subprocess involved.
    # ------------------------------------------------------------------

    def _runway_fieldset_emits_img_only_for_available_runway():
        rendered = config_page.runway_fieldset("3", {"3"})
        if rendered.count("<img") != 1:
            return False, "expected exactly one <img occurrence, got %d" % rendered.count("<img")
        if "/runway-image/3.png" not in rendered:
            return False, "expected the src to point at /runway-image/3.png"
        if "runway-image/06-24" in rendered or "runway-image/02-20" in rendered:
            return False, "expected no image reference for runways not in images_available"
        return True, ""
    check(
        "runway_fieldset(images_available={'3'}) emits exactly one <img, for runway 3 only",
        _runway_fieldset_emits_img_only_for_available_runway)

    def _runway_fieldset_graceful_fallback_no_images():
        rendered = config_page.runway_fieldset("3", set())
        if "<img" in rendered:
            return False, "expected zero <img occurrences with an empty images_available set"
        if rendered.count('name="tracked_runway"') != 3:
            return False, "expected all three runway radios still present"
        for runway_id in device_config.RUNWAY_IDS:
            if escape_html(device_config.runway_label(runway_id)) not in rendered:
                return False, "expected the label text for runway %r" % (runway_id,)
        return True, ""
    check(
        "runway_fieldset(images_available=set()) renders zero <img tags and all three number/heading labels (D-03 graceful fallback)",
        _runway_fieldset_graceful_fallback_no_images)

    def _render_forwards_ctx_runway_images_key():
        rendered = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
            "runway_images": {"06-24"},
        })
        if "/runway-image/06-24.png" not in rendered:
            return False, "expected render() to forward ctx['runway_images'] into the <img> src"
        # 06.6.4.1.1-05: scoped to the runway-card image class specifically
        # — the page now also carries one theme-chip preview <img> per
        # THEME_IDS entry, so a bare "<img" count is no longer exclusive
        # to the runway picker.
        if rendered.count('<img class="runway-card__image"') != 1:
            return False, (
                "expected exactly one runway-card__image <img occurrence, got %d"
                % rendered.count('<img class="runway-card__image"'))
        return True, ""
    check(
        "render() forwards ctx['runway_images'] to runway_fieldset() rather than relying on the parameter default",
        _render_forwards_ctx_runway_images_key)

    # ------------------------------------------------------------------
    # 06.6.4.1 Task 3 (D-03, D-04, D-06): cross-file DOM-contract guards
    # between config_page.py's constants and the two static assets that
    # read them by literal value, dirty-state.js and style.css. Neither
    # static file imports this module — these checks are what keeps the
    # three in sync.
    # ------------------------------------------------------------------

    _STATIC_DIR = os.path.join(REPO_ROOT, "companion", "static")

    def _read_static(name):
        with open(os.path.join(_STATIC_DIR, name)) as fh:
            return fh.read()

    def _dirty_state_js_delegates_change_only_at_document_level_and_has_no_forbidden_syntax():
        # 27-04-PLAN.md Task 2 (CFG-63): SUPERSEDES this check's own
        # pre-27-04 subject — DIRTY_SECTION_ATTR and the dirty-ready
        # marker are both retired along with the bar that read them
        # (dirtySectionLabels() and updateBar() are both gone; see
        # dirty-state.js's own header for the full account). B1's own
        # fix (22-01-PLAN.md Task 2, D-01) survives unchanged: no
        # form.addEventListener registration may return, and the
        # delegation must stay at the document level gated on the
        # control's own .form property.
        source = _read_static("dirty-state.js")
        if config_page.DIRTY_SECTION_ATTR in source:
            return False, (
                "expected dirty-state.js to reference NEITHER DIRTY_SECTION_ATTR's value nor "
                "dirty-ready any more — dirtySectionLabels() and the bar's own liveness marker "
                "are both retired along with the bar itself (CFG-63)")
        if "dirty-ready" in source or "dirty-shown" in source:
            return False, (
                "expected dirty-state.js to carry neither the dirty-ready nor the dirty-shown "
                "marker any more — style.css's fallback-hide rule keys on a plain .js gate now "
                "(27-03-PLAN.md/CFG-64) and there is no bar left to prove the liveness of")
        if 'form.addEventListener("change"' in source:
            return False, "expected no surviving form.addEventListener(\"change\" registration (B1 regression)"
        if "document.addEventListener" not in source:
            return False, "expected at least one document.addEventListener registration (change)"
        if "e.target.form === form" not in source and "e.target.form===form" not in source:
            return False, "expected the document-level delegation to gate on e.target.form === form"
        # D-04: `input` no longer drives anything — there is no bar left
        # to update on a keystroke, and a save on `input` would be the
        # exact keystroke-is-a-decision mistake this plan's own
        # PROVISIONAL note argues against. Measured on the document-level
        # registration specifically, not a file-wide scan: "input" the
        # substring also appears inside ordinary words (e.g. the file's
        # own comments), so only the delegated-listener call sites count.
        if 'document.addEventListener("input"' in source:
            return False, (
                "expected no document-level \"input\" listener — only `change` drives a save now "
                "(D-04)")
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references neither DIRTY_SECTION_ATTR nor the retired dirty-ready/dirty-shown "
        "markers any more, delegates ONLY change (never input) at document level gated on "
        "e.target.form === form with no surviving form.addEventListener(\"change\" registration (B1), "
        "and contains none of innerHTML/let /const /=>/backtick (27-04-PLAN.md Task 2, CFG-63)",
        _dirty_state_js_delegates_change_only_at_document_level_and_has_no_forbidden_syntax)

    def _live_preview_crossfades_through_one_class_shared_by_css_and_js():
        """23-10-PLAN.md Task 2 (D3/CFG-32): the live theme preview
        crossfades instead of cutting.

        The same cross-file DOM-contract shape the checks above already
        hold: one class literal, declared in style.css and driven from
        theme-preview.js, with neither file importing the other. The
        literal is written out here rather than imported, which is the
        point — if either side renames it, this check is what says so.

        The mechanism must be EVENT-DRIVEN, never timed. theme-preview.js
        carries a standing no-timer rule in its own header (and
        test_companion_app.py enforces it), and a crossfade on a timer is
        the specific way this goes wrong: the swap and the fade drift
        apart, and the preview settles on whichever the timer happened to
        win. `transitionend` is when the fade-out is genuinely over, and
        the image's own `load`/`error` is when the new frame is genuinely
        there.
        """
        fade_class = "theme-live-preview__image--swapping"
        css = _read_static("style.css")
        # Comment-stripped, and this was NOT a precaution: the first
        # version of the timer ban below was answered by this file's own
        # new paragraph explaining that the crossfade must never use a
        # timer. A scan over raw source is satisfied by a comment that
        # promises a rule nobody wrote, and broken by a comment that
        # explains one correctly - the same idiom test_companion_app.py's
        # motion-budget guard already records for style.css.
        js = re.sub(
            r"/\*.*?\*/|//[^\n]*", "", _read_static("theme-preview.js"), flags=re.DOTALL)

        base_marker = "\n.theme-live-preview__image {"
        if base_marker not in css:
            return False, "expected style.css to declare .theme-live-preview__image"
        base_idx = css.index(base_marker) + len(base_marker)
        base = css[base_idx:css.index("}", base_idx)]
        if "transition:" not in base:
            return False, (
                "expected .theme-live-preview__image to declare the crossfade transition on its "
                "own base rule, so the fade runs in BOTH directions from one declaration")
        decl = base[base.index("transition:"):]
        decl = decl[:decl.index(";") + 1]
        if "opacity" not in decl:
            return False, (
                "expected the live preview's transition to name opacity, got %r" % (decl,))
        if "var(--motion-fast)" not in decl:
            return False, (
                "expected the live preview crossfade to spend var(--motion-fast) — somebody just "
                "clicked a chip and is watching for the preview to answer, got %r" % (decl,))

        fade_marker = "\n.%s {" % fade_class
        if fade_marker not in css:
            return False, "expected style.css to declare .%s" % (fade_class,)
        fade_idx = css.index(fade_marker) + len(fade_marker)
        fade_body = css[fade_idx:css.index("}", fade_idx)]
        if "opacity: 0" not in fade_body:
            return False, (
                "expected .%s to be the opacity-0 half of the crossfade, got %r"
                % (fade_class, fade_body.strip()))

        if fade_class not in js:
            return False, (
                "theme-preview.js must drive the crossfade through the same %r class style.css "
                "declares — neither file imports the other, and this literal is the only thing "
                "keeping them in step" % (fade_class,))
        for token in ("transitionend", '"load"', '"error"'):
            if token not in js:
                return False, (
                    "expected theme-preview.js to listen for %s — the crossfade must be driven "
                    "by the events that actually mark the fade-out ending and the new frame "
                    "arriving, never by a timer" % (token,))
        # The one stall an event-driven crossfade can have, pinned as a
        # structural fact because its browser-level reproduction is
        # probabilistic (measured 4 stalls in 14 runs before the fix, 0
        # in 14 after). A transitionend only arrives if a transition
        # actually RAN, and it does not run when the image is already
        # invisible, nor when the class is removed and re-added without a
        # style recalculation in between - an image load and a click
        # landing in the same frame does exactly that. The preview then
        # sits at opacity 0 on the discarded theme forever. Consulting
        # the COMPUTED opacity is what lets the script tell "a fade is
        # about to run" from "there is nothing left to fade", so a swap
        # can never be waiting on an event that will not come.
        if "getComputedStyle" not in js:
            return False, (
                "theme-preview.js must consult the COMPUTED opacity before waiting on "
                "transitionend: a transition that never runs never ends, and the preview then "
                "sits invisible on the discarded theme forever (measured: 4 stalls in 14 runs "
                "without this)")
        for banned in ("setTimeout", "setInterval", "requestAnimationFrame"):
            if banned in js:
                return False, (
                    "theme-preview.js must stay timer-free (%r found): a timed crossfade lets the "
                    "swap and the fade drift apart, and the preview settles on whichever won"
                    % (banned,))
        # T8 survives: dirty-state.js's Cancel handler calls this, and a
        # crossfade that bypassed refresh() would leave Cancel showing
        # the discarded theme again — the exact defect T8 closed.
        if "SkyPaneLivePreview" not in js or "refresh" not in js:
            return False, (
                "expected theme-preview.js to keep exposing window.SkyPaneLivePreview.refresh() "
                "— dirty-state.js's Cancel handler calls it after form.reset(), and T8 exists "
                "because reset() fires no change event")
        return True, ""
    check(
        "the live theme preview CROSSFADES rather than cuts: .theme-live-preview__image declares an "
        "opacity transition at var(--motion-fast) on its own base rule, a .theme-live-preview__image--swapping "
        "class carries the opacity-0 half, theme-preview.js drives that same class literal from transitionend "
        "and the image's own load/error (never a timer) while consulting the computed opacity so a swap can "
        "never wait on a transition that never runs, and T8's window.SkyPaneLivePreview.refresh() survives "
        "(D3/CFG-32, 23-10-PLAN.md Task 2)",
        _live_preview_crossfades_through_one_class_shared_by_css_and_js)

    # ------------------------------------------------------------------
    # 19-10-PLAN.md Task 2 (D-10/A-28): a beforeunload guard, keyed on
    # the existing countDifferences() predicate, warns before a real
    # navigation discards unsaved settings edits.
    # ------------------------------------------------------------------

    def _dirty_state_js_beforeunload_guard_reuses_count_differences():
        source = _read_static("dirty-state.js")
        if "beforeunload" not in source:
            return False, "expected dirty-state.js to register a beforeunload listener"
        if "returnValue" not in source:
            return False, "expected dirty-state.js's beforeunload guard to set evt.returnValue"
        if "preventDefault" not in source:
            return False, "expected dirty-state.js's beforeunload guard to call evt.preventDefault()"
        # 27-04-PLAN.md (CFG-63): located by the LISTENER REGISTRATION
        # itself, not the bare word — this file's own header prose now
        # discusses the leave-guard by name before the registration
        # appears in source, and a bare-word search would find that prose
        # instead of the real listener body.
        listener_marker = 'addEventListener("beforeunload"'
        if listener_marker not in source:
            return False, "expected dirty-state.js to call addEventListener(\"beforeunload\", ...)"
        beforeunload_idx = source.index(listener_marker)
        # The guard's own listener body must reference countDifferences -
        # reused, never reimplemented as a separate flag that can drift
        # from the form's own dirty state.
        listener_body = source[beforeunload_idx:beforeunload_idx + 400]
        if "countDifferences" not in listener_body:
            return False, "expected the beforeunload listener's body to reference countDifferences"
        if 'addEventListener("submit"' not in source:
            return False, "expected dirty-state.js to register a submit listener on the form"
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js registers a beforeunload listener whose body references countDifferences and sets "
        "returnValue/calls preventDefault, and a submit listener clears the guard; contains none of "
        "innerHTML/let /const /=>/backtick",
        _dirty_state_js_beforeunload_guard_reuses_count_differences)

    # ------------------------------------------------------------------
    # 19-10-PLAN.md Task 3 (D-14/S-04): cross-file guard keeping
    # dirty-state.js's preset reader in agreement with config_page.py's
    # QUIET_HOURS_PRESET_ATTR/data-preset-* markup.
    # ------------------------------------------------------------------

    def _dirty_state_js_references_quiet_preset_attrs():
        source = _read_static("dirty-state.js")
        for literal in (
                config_page.QUIET_HOURS_PRESET_ATTR, "data-preset-start",
                "data-preset-end", "data-preset-enabled"):
            if literal not in source:
                return False, "expected dirty-state.js to reference the literal %r" % (literal,)
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references config_page.QUIET_HOURS_PRESET_ATTR's literal value and the three "
        "data-preset-* attribute names, and contains none of innerHTML/let /const /=>/backtick",
        _dirty_state_js_references_quiet_preset_attrs)

    def _style_css_references_static_save_fallback_attr():
        # 19-10-PLAN.md (D-09/A-27): retargeted from .js to .dirty-ready;
        # 22-01-PLAN.md Task 2 (D-01/B1) retargeted it AGAIN, to require
        # BOTH .dirty-ready and .dirty-shown (proven liveness rather than
        # mere element presence). 27-03-PLAN.md Task 2 (CFG-64) retargets
        # it a THIRD time, in the opposite direction: the floor is kept
        # by render()'s emission being unconditional now (Task 1's own
        # source proof), so the two narrowing markers have nothing left
        # to prove on THIS rule and the selector reverts to the plain
        # script-presence gate it originally shipped as — the B1/P0
        # contract is SUPERSEDED, not deleted, and the style.css comment
        # block records that in writing, dated, right above the rule.
        source = _read_static("style.css")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in source:
            return False, "expected style.css to reference the literal value of STATIC_SAVE_FALLBACK_ATTR"
        idx = source.index(config_page.STATIC_SAVE_FALLBACK_ATTR)
        window = source[idx:idx + 120]
        if "display: none" not in window and "display:none" not in window:
            return False, "expected the fallback-hide rule to set display: none near the attribute reference"
        # The selector prefix sits BEFORE the attribute reference
        # (the plain `.js` gate), so widen the window backwards too
        # rather than only forwards.
        selector_window = source[max(0, idx - 40):idx + 120]
        if "dirty-ready" in selector_window or "dirty-shown" in selector_window:
            return False, (
                "expected the fallback-hide rule's OWN selector to carry neither dirty-ready nor "
                "dirty-shown any more (CFG-64: the floor is kept by unconditional emission, not "
                "by these two markers) — selector window reads %r" % (selector_window,))
        combined_selector = ".dirty-ready.dirty-shown [%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR
        if combined_selector in source:
            return False, "expected the superseded two-marker selector to be gone entirely (CFG-64)"
        # THE SUPERSEDED CONTRACT IS AMENDED IN WRITING, NOT ERASED: the
        # original comment's own distinctive sentences must still be
        # present (its history survives), and a dated Phase 27 paragraph
        # must follow it naming what replaced it.
        for distinctive in (
                "PROVEN its own replacement bar is actually live",
                "turned out to still be element PRESENCE, not proven liveness (B1)",
                "B1's proven-liveness fix"):
            if distinctive not in source:
                return False, (
                    "expected the ORIGINAL comment's own sentence %r to survive verbatim — "
                    "the B1/P0 contract must be superseded in writing, not deleted" % (distinctive,))
        if "27-03-PLAN.md" not in source or "SUPERSEDED" not in source:
            return False, (
                "expected a dated 27-03-PLAN.md paragraph stating the contract is SUPERSEDED, "
                "not merely that the rule changed")
        return True, ""
    check(
        "style.css's fallback-hide rule reverts to the plain .js gate (CFG-64: the floor is now "
        "kept by render()'s unconditional emission, not by this rule's specificity), the "
        "superseded two-marker selector is gone, and B1/P0's own contract survives in writing — "
        "its original sentences intact plus a dated 27-03-PLAN.md paragraph naming what replaced "
        "it (27-03-PLAN.md Task 2)",
        _style_css_references_static_save_fallback_attr)

    def _style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors():
        # quick task 260901-qif: the third new cross-file guard - unlike
        # DIRTY_SECTION_ATTR/STATIC_SAVE_FALLBACK_ATTR above, no Python
        # constant carries these three class-name literals, so they are
        # asserted directly here. Same index-plus-window technique the
        # neighbouring guards use, never a regex CSS parser. Keeps
        # style.css's .theme-status/.runway-row/.settings-checkbox rules
        # from silently drifting out of sync with the markup
        # config_page.py's runway_fieldset()/led_group()/
        # quiet_hours_group() now emit. 10-05-PLAN.md Task 2 renamed the
        # third selector from .led-checkbox to .settings-checkbox.
        source = _read_static("style.css")

        if ".theme-status {" not in source:
            return False, "expected style.css to declare a .theme-status rule"
        idx = source.index(".theme-status {")
        window = source[idx:idx + 400]
        if "var(--color-dominant)" not in window:
            return False, "expected .theme-status's rule body to carry the --color-dominant card-surface token"
        if ".theme-status:hover" not in source:
            return False, "expected style.css to declare a .theme-status:hover selector"

        if ".runway-row {" not in source:
            return False, "expected style.css to declare a .runway-row rule"
        idx = source.index(".runway-row {")
        window = source[idx:idx + 200]
        if "display: flex" not in window:
            return False, "expected .runway-row's rule body to set display: flex"

        checkbox_selector = '.settings-checkbox input[type="checkbox"] {'
        if checkbox_selector not in source:
            return False, "expected style.css to declare a %r rule" % (checkbox_selector,)
        idx = source.index(checkbox_selector)
        window = source[idx:idx + 400]
        if "min-height: 0" not in window:
            return False, "expected .settings-checkbox input[type=\"checkbox\"]'s rule body to clear the global rule's min-height"

        # 06.6.4.1.1-05: the fourth cross-file guard, same index-plus-
        # window technique, covering the new .theme-chip* selectors
        # theme_fieldset()'s D-01 chip-grid markup now depends on.
        if ".theme-chip-grid {" not in source:
            return False, "expected style.css to declare a .theme-chip-grid rule"
        idx = source.index(".theme-chip-grid {")
        window = source[idx:idx + 200]
        if "display: flex" not in window:
            return False, "expected .theme-chip-grid's rule body to set display: flex"

        if ".theme-chip {" not in source:
            return False, "expected style.css to declare a .theme-chip rule"
        idx = source.index(".theme-chip {")
        window = source[idx:idx + 700]
        if "var(--color-dominant)" not in window:
            return False, "expected .theme-chip's rule body to carry the --color-dominant card-surface token"
        if "width: 160px" not in window:
            return False, "expected .theme-chip's rule body to set width: 160px"

        if ".theme-chip--selected {" not in source:
            return False, "expected style.css to declare a .theme-chip--selected rule"
        idx = source.index(".theme-chip--selected {")
        window = source[idx:idx + 100]
        if "var(--color-accent)" not in window:
            return False, "expected .theme-chip--selected's rule body to carry var(--color-accent)"

        if ".theme-chip__preview {" not in source:
            return False, "expected style.css to declare a .theme-chip__preview rule"
        idx = source.index(".theme-chip__preview {")
        window = source[idx:idx + 200]
        if "height: 56px" not in window:
            return False, "expected .theme-chip__preview's rule body to set height: 56px"
        return True, ""
    check(
        "style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex display), "
        '.settings-checkbox input[type="checkbox"] (cleared min-height), and .theme-chip-grid/.theme-chip/'
        ".theme-chip--selected/.theme-chip__preview (flex display, card surface + 160px width, accent border, "
        "56px preview band) - the selectors config_page.py's new markup depends on",
        _style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors)

    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the check that used to live
    # here (_style_css_needs_no_new_selector_for_display_group) is deleted
    # outright along with display_group() itself — there is no longer a
    # Display group for style.css to need, or not need, a new selector for.

    def _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
        # 06.6.4.1.1-05: the cross-module route contract — every chip's
        # <img src> is built from theme_preview.THEME_PREVIEW_ROUTE_PREFIX
        # (rebound as config_page.THEME_PREVIEW_ROUTE_PREFIX) plus the
        # theme's own registry id, asserted against the constant rather
        # than a re-typed literal, for every entry in THEME_IDS.
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() directly onto the ONE low-level chip-grid
        # renderer it used to call twice — _theme_chip_grid_html()'s own
        # per-chip output shape is unchanged by this plan.
        rendered = config_page._theme_chip_grid_html("theme", "white")
        for theme_id in device_config.THEME_IDS:
            expected_src = 'src="%s%s.png"' % (
                config_page.THEME_PREVIEW_ROUTE_PREFIX, escape_html(theme_id))
            if expected_src not in rendered:
                return False, "expected chip %r to carry %r" % (theme_id, expected_src)
        return True, ""
    check(
        "every theme chip's <img src> points at THEME_PREVIEW_ROUTE_PREFIX + the theme's own registry id, "
        "for every entry in device_config.THEME_IDS (06.6.4.1.1-05)",
        _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme)

    def _theme_chip_swatch_dots_carry_real_palette_hex_values():
        # 06.6.4.1.1-05: each chip carries exactly two .theme-chip__dot
        # spans whose inline background values are computed from
        # _palette_hex() against the theme's own departing_index/
        # arriving_index — real panel palette colours, never hardcoded.
        #
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() (which used to call this grid builder twice)
        # onto a single _theme_chip_grid_html() call directly — the
        # per-chip dot count this check pins is a property of that one
        # low-level function, unaffected by how many usage panels the
        # Frame colours card now composes it into.
        rendered = config_page._theme_chip_grid_html("theme", "white")
        if rendered.count("theme-chip__dot") != len(device_config.THEME_IDS) * 2:
            return False, (
                "expected exactly %d .theme-chip__dot occurrences (2 per theme), got %d"
                % (len(device_config.THEME_IDS) * 2, rendered.count("theme-chip__dot")))
        for theme_id in device_config.THEME_IDS:
            theme = device_config.THEMES[theme_id]
            departing_hex = config_page._palette_hex(theme["departing_index"])
            arriving_hex = config_page._palette_hex(theme["arriving_index"])
            if ('theme-chip__dot" style="background:%s"' % departing_hex) not in rendered:
                return False, "expected theme %r's departing swatch dot to carry %r" % (theme_id, departing_hex)
            if ('theme-chip__dot" style="background:%s"' % arriving_hex) not in rendered:
                return False, "expected theme %r's arriving swatch dot to carry %r" % (theme_id, arriving_hex)
        return True, ""
    check(
        "every theme chip carries exactly two .theme-chip__dot swatches whose inline background values "
        "equal _palette_hex() computed from that theme's own departing_index/arriving_index "
        "(06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by 21-05-PLAN.md Task 1 D-06 "
        "once theme_fieldset() is retired)",
        _theme_chip_swatch_dots_carry_real_palette_hex_values)

    def _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
        # 06.6.4.1.1-05: the markup half of the CSS-only selection reveal
        # — every chip's radio is visually-hidden (never display:none, so
        # keyboard/no-JS selection keeps working natively), and every chip
        # carries a .theme-chip__check glyph with its visually-hidden
        # "Selected" text, present on all 16 chips regardless of which one
        # is actually selected.
        #
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # theme_fieldset() onto a single _theme_chip_grid_html() call —
        # this low-level function's own per-chip markup shape (and this
        # check's premise) is unaffected by the Frame colours card's own
        # multi-panel composition above it.
        rendered = config_page._theme_chip_grid_html("theme", "white")
        theme_count = len(device_config.THEME_IDS)
        if rendered.count('name="theme" value="') != theme_count:
            return False, "expected %d theme radios, got %d" % (theme_count, rendered.count('name="theme" value="'))
        if rendered.count('class="visually-hidden"') < theme_count:
            return False, "expected every chip's radio to carry class=\"visually-hidden\""
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('<span class="theme-chip__check">') != theme_count:
            return False, (
                "expected exactly %d .theme-chip__check occurrences (one per chip, regardless of selection), "
                "got %d"
                % (theme_count, rendered.count('<span class="theme-chip__check">')))
        if rendered.count('<span class="visually-hidden">Selected</span>') != theme_count:
            return False, "expected every chip's check glyph to carry the visually-hidden \"Selected\" text"
        return True, ""
    check(
        "every theme chip's radio carries class=\"visually-hidden\" (never display:none) and every chip "
        "carries a .theme-chip__check glyph with visually-hidden \"Selected\" text, present on all chips "
        "regardless of selection (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by "
        "21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired)",
        _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip)

    # ------------------------------------------------------------------
    # 15-04-PLAN.md (D-04/D-05): the arrivals-override checkbox, its
    # revealed second chip grid, and handle_post()'s clearable-checkbox
    # contract (15-VALIDATION.md row 7).
    # ------------------------------------------------------------------

    def _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox():
        # 21-05-PLAN.md Task 1 (D-06/D-09): retargeted from the retired
        # arrivals-override checkbox onto the Frame colours card's own
        # "Same as departures" leading chip — both grids present in the
        # rendered Display page; the arrivals grid carries
        # name="theme_arriving" radios AND a leading empty-string chip;
        # THEME_ARRIVING_CHECKBOX_LABEL/THEME_ARRIVING_TOGGLE_ID/
        # theme_arriving_enabled exist nowhere on the page any more.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        # 22-10-PLAN.md Task 1 (X6): retargeted in place. The departures
        # grid used to be the page's one full-size grid and was asserted
        # here by its plain `class="theme-chip-grid"`; X6 gives the whole
        # Display page one chip density, so that plain class must now be
        # ABSENT and every grid must carry the compact modifier. The
        # dedicated one-density check below owns the positive assertion;
        # this line keeps the negative one at the site that used to pin
        # the opposite, so the reversal cannot be missed by a reader.
        if 'class="theme-chip-grid"' in rendered:
            return False, (
                "expected NO plain (non-compact) chip grid on Display any more - X6 gives the "
                "page one chip density")
        if 'class="theme-chip-grid theme-chip-grid--compact"' not in rendered:
            return False, "expected the arrivals/calendar grids' compact modifier class"
        theme_count = len(device_config.THEME_IDS)
        # +1 per compact grid (arrivals, calendar) for the leading "Same
        # as departures" chip, which also submits name="theme_arriving"/
        # name="calendar_theme_id" with value="".
        if rendered.count('name="theme_arriving" value="') != theme_count + 1:
            return False, (
                "expected %d theme_arriving radios (theme_count + 1 leading chip), got %d"
                % (theme_count + 1, rendered.count('name="theme_arriving" value="')))
        if "theme_arriving_enabled" in rendered:
            return False, "expected no theme_arriving_enabled checkbox anywhere on the page (D-09)"
        if "Use a different theme for arrivals" in rendered:
            return False, "expected no THEME_ARRIVING_CHECKBOX_LABEL text anywhere on the page (D-09)"
        for retired_name in ("THEME_ARRIVING_CHECKBOX_LABEL", "THEME_ARRIVING_TOGGLE_ID",
                              "ARRIVING_CHECKBOX_VALUE", "THEME_DIRECTION_LABEL"):
            if hasattr(config_page, retired_name):
                return False, "expected config_page to expose no %s constant any more" % (retired_name,)
        same_as_departures = escape_html(config_page.SAME_AS_DEPARTURES_LABEL)
        if rendered.count(same_as_departures) < 2:
            return False, (
                "expected the 'Same as departures' chip label to appear at least twice "
                "(arrivals grid + calendar grid)")
        return True, ""
    check(
        "the Frame colours card's arrivals/calendar grids carry a leading 'Same as departures' chip "
        "(submitting the empty string) instead of the retired arrivals-override checkbox, and no trace "
        "of that checkbox's own constants survives anywhere (D-06/D-09)",
        _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox)

    def _frame_colours_arrivals_override_preselects_the_override_not_same_as_departures():
        # 21-05-PLAN.md Task 1 (D-06/D-09): retargeted from the retired
        # theme_fieldset(theme, theme_arriving) direct call onto
        # _frame_colours_card_html() directly — with a stored override,
        # the leading "Same as departures" chip must NOT be checked, and
        # the override's own chip must be.
        ctx = {"colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS}}
        rendered = config_page._frame_colours_card_html(ctx, "white", "black", None)
        arrivals_start = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_ARRIVALS))
        arrivals_end = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_CALENDAR))
        grid = rendered[arrivals_start:arrivals_end]
        if not re.search(r'name="theme_arriving" value="black"[^>]*checked', grid):
            return False, "expected the arrivals grid's checked radio to be the stored override (black)"
        if re.search(r'name="theme_arriving" value=""[^>]*checked', grid):
            return False, "expected the leading 'Same as departures' chip to NOT be checked once an override is set"
        if re.search(r'name="theme_arriving" value="white"[^>]*checked', grid):
            return False, "expected the departures theme (white) to NOT be marked selected in the arrivals grid once an override is set"
        return True, ""
    check(
        "_frame_colours_card_html() with a stored theme_arriving override pre-selects the OVERRIDE (not "
        "'Same as departures', not the departures theme) in the arrivals grid (D-06/D-09, replacing the "
        "retired arrivals-override checkbox)",
        _frame_colours_arrivals_override_preselects_the_override_not_same_as_departures)

    def _handle_post_theme_arriving_valid_id_persists_chosen_id():
        # 21-05-PLAN.md Task 2 (D-09/R-07): retargeted — no checkbox
        # exists any more; submitting a real, membership-checked
        # theme_arriving id persists it outright.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "black",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme_arriving"] != "black":
                return False, "expected theme_arriving 'black' on disk, got %r" % (on_disk["theme_arriving"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a valid theme_arriving id persists it, with no checkbox field involved (D-06/D-09, "
        "retargeted from the retired arrivals-override checkbox)",
        _handle_post_theme_arriving_valid_id_persists_chosen_id)

    def _handle_post_theme_arriving_empty_string_clears_previous_override():
        # 21-05-PLAN.md Task 2 (D-09/R-07): retargeted — the clear
        # signal is now theme_arriving="" (the Frame colours card's own
        # leading "Same as departures" chip, Task 1), never
        # checkbox-absence.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "black",
                },
                ctx)
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "submitting theme_arriving='' failed to clear the override, got %r"
                    % (on_disk["theme_arriving"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with theme_arriving='' clears a previously-set override back to None (D-06/D-09, "
        "retargeted from the retired arrivals-override checkbox's own absence)",
        _handle_post_theme_arriving_empty_string_clears_previous_override)

    def _handle_post_calendar_theme_id_empty_string_saves_as_none():
        # 21-05-PLAN.md Task 2 (D-09/R-07): the parallel, lower-risk
        # half — calendar_theme_id never had a checkbox, so once its
        # gate exempts "", the existing pass-through plus
        # normalise_calendar_theme_id("")'s own documented None-degrade
        # already does the right thing (no second resolution block
        # needed).
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            config_page.handle_post({"calendar_theme_id": "white"}, {"state_dir": tmpdir})
            flash_key = config_page.handle_post({"calendar_theme_id": ""}, {"state_dir": tmpdir})
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] is not None:
                return False, (
                    "submitting calendar_theme_id='' failed to clear the override, got %r"
                    % (on_disk["calendar_theme_id"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with calendar_theme_id='' saves and reads back as None, mirroring theme_arriving's own "
        "empty-string clear signal (D-06/D-09)",
        _handle_post_calendar_theme_id_empty_string_saves_as_none)

    def _handle_post_crafted_non_member_theme_and_calendar_values_still_rejected():
        # 21-05-PLAN.md Task 2 (Pitfall 1): the empty string is carved
        # out of both gates, but every OTHER non-member value (a plain
        # invalid id, a value that merely looks close to a real one, a
        # bare space) is still rejected exactly as before — the gate is
        # widened, not weakened. Replaces the retired crafted-checkbox-
        # value check (that field no longer exists).
        for field, payload in (
                ("theme_arriving", "nope"), ("theme_arriving", " "),
                ("theme_arriving", "WHITE "), ("calendar_theme_id", "nope"),
                ("calendar_theme_id", " "), ("calendar_theme_id", "WHITE ")):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                flash_key = config_page.handle_post({field: payload}, {"state_dir": tmpdir})
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for %s=%r, got %r" % (field, payload, flash_key)
                if before != after:
                    return False, "expected device_config.json to be byte-identical for %s=%r, it changed" % (
                        field, payload)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post still rejects a crafted non-member theme_arriving/calendar_theme_id value (a plain "
        "invalid id, a bare space, a near-miss uppercase/trailing-space variant) and writes nothing — the "
        "empty-string exemption does not widen the gate to anything else (D-09/Pitfall 1)",
        _handle_post_crafted_non_member_theme_and_calendar_values_still_rejected)

    def _handle_post_nonmember_theme_arriving_rejected():
        # Task 2 <behavior> bullet 4, including a path-traversal-shaped
        # and a SQL-shaped payload, matching theme's own adversarial
        # coverage.
        for payload in ("chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post(
                    {"theme_arriving": payload},
                    ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, "expected FLASH_SAVE_FAILED for theme_arriving=%r, got %r" % (payload, flash_key)
                if before != after:
                    return False, "expected device_config.json to be byte-identical for theme_arriving=%r, it changed" % (payload,)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post with a non-member theme_arriving (a plain invalid id, a path-traversal-shaped payload, and a "
        "SQL-shaped payload) rejects the whole submission and writes nothing — '' is explicitly exempted from "
        "this rejection (D-09)",
        _handle_post_nonmember_theme_arriving_rejected)

    def _handle_post_theme_arriving_partial_post_still_carries_other_fields():
        # Task 2 <behavior> bullet 5: every other field's behaviour is
        # unchanged - a partial-field post still carries the other
        # settings forward. Retargeted from the retired checkbox onto
        # the plain theme_arriving field alone.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"theme_arriving": "white"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,)
            if on_disk["theme"] != "black":
                return False, "expected the existing theme to be carried forward unchanged, got %r" % (on_disk,)
            if on_disk["theme_arriving"] != "white":
                return False, "expected theme_arriving 'white' on disk, got %r" % (on_disk["theme_arriving"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a post carrying only theme_arriving still carries the existing theme/runway forward unchanged "
        "(retargeted from the retired arrivals-override checkbox, D-09)",
        _handle_post_theme_arriving_partial_post_still_carries_other_fields)

    def _theme_arriving_clearable_contract_full_round_trip():
        # 15-VALIDATION.md row 7 - the acceptance criterion the whole plan
        # exists for. Named so a failure says plainly that the empty-
        # string clear signal stopped working. Proves the full sequence:
        # save with a chosen arrivals theme (confirm it persisted), save
        # again with theme_arriving="" (confirm theme_arriving comes back
        # None), and confirm every other setting from the first save
        # survived the second save unchanged. 21-05-PLAN.md Task 2
        # (D-09/R-07): retargeted from the retired checkbox's own
        # absence onto the new empty-string clear signal.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            first = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                },
                ctx)
            if first != config_page.FLASH_SAVED:
                return False, "expected the first save to return FLASH_SAVED, got %r" % (first,)
            after_first = device_config.load_device_config(tmpdir)
            if after_first["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' to persist after the first save, got %r"
                    % (after_first["theme_arriving"],))

            second = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving": "",
                },
                ctx)
            if second != config_page.FLASH_SAVED:
                return False, "expected the second (clearing) save to return FLASH_SAVED, got %r" % (second,)
            after_second = device_config.load_device_config(tmpdir)
            if after_second["theme_arriving"] is not None:
                return False, (
                    "theme_arriving='' failed to clear the override - expected theme_arriving "
                    "None, got %r" % (after_second["theme_arriving"],))
            if (
                after_second["theme"] != "white"
                or after_second["tracked_runway"] != "06-24"
                or after_second["led_enabled"] is not True
            ):
                return False, "expected every other setting to survive the second save unchanged, got %r" % (after_second,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "the clearable contract (15-VALIDATION.md row 7): a save with a chosen arrivals theme persists it, "
        "then a save with theme_arriving='' clears it back to None while every other setting survives "
        "unchanged (D-06/D-09, retargeted from the retired arrivals-override checkbox's own absence)",
        _theme_arriving_clearable_contract_full_round_trip)

    def _settings_page_has_zero_fieldsets_and_five_dirty_sections():
        # 06.6.4.1.1-05: the rendered Settings page contains no <fieldset
        # and no <legend anywhere — so dirty-state.js's section-aware walk
        # still finds Theme as one addressable unit after the rewrite.
        # merge of Phase 10/11: the data-dirty-section count is 5, not
        # 06.6.4.1.1-05's own 3 (Theme/Runway/Diagnostic LED), now that
        # Quiet hours and Wake interval each joined as a fourth and fifth
        # group — not a rename of this check's own premise.
        # 12-05-PLAN.md: the count is 6, not 5, now that Display joined as
        # the sixth and last group — again not a rename of this check's
        # own premise.
        # 16-05-PLAN.md: the count is 7, not 6, now that Calendar joined
        # as the seventh and last group — again not a rename of this
        # check's own premise.
        # 20-11-PLAN.md Task 1: the count was 8, not 7, now that
        # Notifications joined as the eighth and last group — again not
        # a rename of this check's own premise. 21-05-PLAN.md Task 1
        # (D-06): the count drops back to 7 — theme_fieldset() (Theme's
        # own data-dirty-section) is retired outright, and its
        # replacement (the Frame colours card) only ever renders on the
        # Display scope, never on this legacy SCOPE_ALL render.
        # 21-07-PLAN.md Task 1 (D-13/Pitfall 2): the count drops to 6 —
        # the merged calendar_group() now embeds a real connect/replace
        # <form> in every state, which would nest inside <form id=
        # "settings-form"> on this legacy render, so it has no entry in
        # `builders` here any more either (Calendar's own data-dirty-
        # section entry only ever renders on the Display scope now,
        # exactly like Theme's).
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the count drops to 5 —
        # display_group() is retired outright and screens.GROUP_DISPLAY
        # is no longer a member of any screen type's own group tuple, so
        # this legacy render no longer contributes a Display entry either
        # (+0/-1: "Display" removed from the expected-groups comment).
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements on the rendered Settings page"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements on the rendered Settings page"
        if rendered.count(config_page.DIRTY_SECTION_ATTR) != 5:
            return False, (
                "expected exactly 5 %s occurrences (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications), got %d"
                % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))
        return True, ""
    check(
        "the rendered Settings page contains no <fieldset> and no <legend>, and exactly five "
        "data-dirty-section groups (Runway/Diagnostic LED/Quiet hours/Wake interval/"
        "Notifications — Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 "
        "D-06; Calendar's own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/"
        "Pitfall 2; Display's own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1)",
        _settings_page_has_zero_fieldsets_and_five_dirty_sections)

    def _selected_runway_card_and_theme_chip_carry_a_background_wash():
        # 06.6.4.1.1-06 (developer checkpoint follow-up): the developer
        # reported that, across the whole site, the selected element was
        # "very hard to see" — a border-only + check-glyph treatment was
        # too subtle at density. The fix adds a background wash matching
        # `.theme-form .theme-option--active`'s own established idiom
        # (color-mix(in srgb, var(--color-accent) 12%, transparent)) to
        # BOTH selectable-card components, alongside their existing
        # border and check glyph, not replacing either.
        source = _read_static("style.css")
        wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

        runway_selector = ".runway-card--selected {"
        if runway_selector not in source:
            return False, "expected style.css to still declare a .runway-card--selected rule"
        idx = source.index(runway_selector)
        window = source[idx:idx + 1600]
        # RETARGETED by 22-15-PLAN.md Task 1 (T6). This clause used to
        # read `border: 2px solid var(--color-accent);`. T6 is the
        # defect that selection shifted layout by 2px: under
        # `box-sizing: border-box` a 2px border still widens the OUTER
        # box of a `flex: 1 1 0` card (measured 98.67px against
        # 96.66/96.67px at 390px), so a selected card was a different
        # size from its siblings. The border is now constant at 1px and
        # only recolours; the 2px accent signal moved to an inset ring,
        # which occupies no layout space at all. Strictly narrower than
        # the clause it replaces: it pins BOTH halves of the new
        # treatment and additionally forbids the 2px border returning.
        if "border-color: var(--color-accent);" not in window:
            return False, ".runway-card--selected must recolour its constant 1px border to the accent"
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".runway-card--selected must carry T6's inset accent ring — the selection signal "
                "that replaced the layout-shifting 2px border")
        if "border: 2px" in window:
            return False, (
                ".runway-card--selected must never declare a 2px border again — that is T6, the "
                "2px layout shift this treatment exists to avoid")
        if wash not in window:
            return False, (
                "expected .runway-card--selected to carry the same 12%-accent background wash "
                ".theme-form .theme-option--active uses")

        # .theme-chip--selected itself must stay border-only (no
        # background) — the wash must be scoped to .theme-chip__body
        # only, so it never sits behind the rendered preview band and
        # tints it. Isolate this rule's own body precisely (up to its
        # closing brace), not an arbitrary fixed-size window, so a
        # background declared just after the rule can't false-positive.
        chip_selected_selector = ".theme-chip--selected {"
        if chip_selected_selector not in source:
            return False, "expected style.css to still declare a .theme-chip--selected rule"
        idx = source.index(chip_selected_selector) + len(chip_selected_selector)
        rule_body = source[idx:source.index("}", idx)]
        if "background:" in rule_body:
            return False, (
                "expected .theme-chip--selected itself to stay border-only — the wash must be "
                "scoped to .theme-chip__body, not the whole chip (which would tint the preview band)")

        theme_chip_body_selector = ".theme-chip--selected .theme-chip__body {"
        if theme_chip_body_selector not in source:
            return False, "expected style.css to declare a %r rule" % (theme_chip_body_selector,)
        idx = source.index(theme_chip_body_selector)
        window = source[idx:idx + 200]
        if wash not in window:
            return False, (
                "expected .theme-chip--selected .theme-chip__body to carry the same 12%-accent "
                "background wash .theme-form .theme-option--active uses")
        return True, ""
    check(
        "both .runway-card--selected and .theme-chip--selected .theme-chip__body carry a 12%-accent "
        "background wash (color-mix), matching .theme-form .theme-option--active's established active-state "
        "idiom, added alongside (not replacing) their check glyph and their now-constant 1px border, whose "
        "2px accent signal moved to an inset ring (06.6.4.1.1-06, retargeted by 22-15-PLAN.md Task 1 for T6)",
        _selected_runway_card_and_theme_chip_carry_a_background_wash)

    def _strong_selected_treatment_is_keyed_to_the_live_checked_radio():
        # quick task 260904-bbi: the developer found that the strong
        # "this is your selection" treatment followed the SAVED config,
        # not the user's LIVE choice, because every selected-state rule
        # keyed off the server-computed --selected class alone. This
        # check proves the strong treatment is now driven by live
        # :has(input:checked) state, inside a single
        # @supports selector(:has(*)) feature-query block, for BOTH
        # selectable-card components — and that the D-03a hover guard
        # (which would otherwise clear the newly-checked chip's border,
        # since it is keyed to :not(--selected) which still matches the
        # newly-checked-but-not-yet-saved chip) is answered with a
        # positive restore rule rather than a re-scoped guard.
        source = _read_static("style.css")

        # Phase 15 D-05 used to add a SECOND @supports selector(:has(*))
        # block — the arrivals-checkbox CSS-only reveal — placed after
        # this one (the live-selection-state block quick task 260904-bbi
        # added); that block's own arrivals-reveal rule was later
        # retired outright by 21-05-PLAN.md Task 1 (D-06/D-09), but the
        # block itself survived one more phase because a SECOND,
        # unrelated rule (20-04-PLAN.md's Calendar-card fusion) still
        # lived inside it. 21-07-PLAN.md Task 3 (D-13/R-08/Pitfall 2)
        # retires that fusion rule too — with no rule left inside it,
        # the block itself is deleted outright, moving the file's own
        # total block count from 2 to 1. index() below still resolves to
        # this (the only remaining) block's own opening brace, so every
        # selector-position assertion below (idx < supports_idx meaning
        # "lives inside this block") is unaffected.
        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block (the live-selection-state one — the Calendar-card "
                "fusion block that used to follow it is retired outright by 21-07-PLAN.md Task 3), "
                "got %d" % (supports_marker, source.count(supports_marker)))
        supports_idx = source.index(supports_marker)

        wash = "background: color-mix(in srgb, var(--color-accent) 12%, transparent);"

        def _rule_body(selector):
            if selector not in source:
                return None, "expected style.css to declare %r" % (selector,)
            idx = source.index(selector)
            if idx < supports_idx:
                return None, "expected %r to live inside the @supports selector(:has(*)) block" % (selector,)
            body = source[idx + len(selector):source.index("}", idx)]
            return body, ""

        # T6 (22-15-PLAN.md Task 1) retargets every "2px accent border"
        # clause in this check to the constant-1px-plus-inset-ring
        # treatment that replaced it, and additionally forbids the 2px
        # border ever returning. See
        # _selected_runway_card_and_theme_chip_carry_a_background_wash()
        # above for the measurement and the full reasoning. Both halves
        # of the live-state treatment must match the `--selected`
        # fallback exactly, or a browser without :has() renders a
        # different-sized card.
        def _carries_the_constant_border_and_inset_ring(body, label):
            if "border-color: var(--color-accent);" not in body:
                return "%s must recolour its constant 1px border to the accent" % (label,)
            if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in body:
                return "%s must carry T6's inset accent ring" % (label,)
            if "border: 2px" in body:
                return "%s must never declare a 2px border again (T6's layout shift)" % (label,)
            return None

        # Theme chip: strong border, body wash, check glyph shown.
        body, err = _rule_body(".theme-chip:has(input:checked) {")
        if body is None:
            return False, err
        err = _carries_the_constant_border_and_inset_ring(
            body, ".theme-chip:has(input:checked)")
        if err:
            return False, err

        body, err = _rule_body(".theme-chip:has(input:checked) .theme-chip__body {")
        if body is None:
            return False, err
        if wash not in body:
            return False, ".theme-chip:has(input:checked) .theme-chip__body must carry the 12%-accent wash"

        body, err = _rule_body(".theme-chip:has(input:checked) .theme-chip__check {")
        if body is None:
            return False, err
        if "display: inline-flex;" not in body:
            return False, ".theme-chip:has(input:checked) .theme-chip__check must be shown"

        # Theme chip hover/focus-within restore (D-03a transferred to
        # live state) - a POSITIVE rule, not a re-scoped guard.
        hover_selector = ".theme-chip:has(input:checked):hover,"
        if hover_selector not in source:
            return False, "expected a live-state hover restore selector for .theme-chip"
        idx = source.index(hover_selector)
        if idx < supports_idx:
            return False, "expected the .theme-chip live-state hover restore rule inside @supports"
        window = source[idx:idx + 250]
        if "border-color: var(--color-accent);" not in window:
            return False, ".theme-chip:has(input:checked):hover must restore the accent border-color"
        # RETARGETED by 22-15-PLAN.md Task 1 (T6): this clause used to
        # require `box-shadow: none;`, whose only job was to suppress
        # the hover elevation shadow. Once selection IS a box-shadow,
        # `none` erases the selection ring the instant a pointer crosses
        # a selected chip. Restating the ring suppresses the elevation
        # just as completely (box-shadow is one property) while keeping
        # the signal — and this clause is narrower, because it now
        # forbids the erasure as well as requiring the suppression.
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".theme-chip:has(input:checked):hover must RESTATE T6's inset ring, which "
                "suppresses the hover elevation without erasing the selection signal")
        if "box-shadow: none;" in window:
            return False, (
                ".theme-chip:has(input:checked):hover must not clear the shadow — that would "
                "erase T6's selection ring on hover")

        # Runway card: strong border + wash on one rule (no body wrapper),
        # check glyph shown.
        body, err = _rule_body(".runway-card:has(input:checked) {")
        if body is None:
            return False, err
        err = _carries_the_constant_border_and_inset_ring(
            body, ".runway-card:has(input:checked)")
        if err:
            return False, err
        if wash not in body:
            return False, ".runway-card:has(input:checked) must carry the 12%-accent wash directly (no body wrapper)"

        body, err = _rule_body(".runway-card:has(input:checked) .runway-card__check {")
        if body is None:
            return False, err
        if "display: inline-flex;" not in body:
            return False, ".runway-card:has(input:checked) .runway-card__check must be shown"

        hover_selector = ".runway-card:has(input:checked):hover,"
        if hover_selector not in source:
            return False, "expected a live-state hover restore selector for .runway-card"
        idx = source.index(hover_selector)
        if idx < supports_idx:
            return False, "expected the .runway-card live-state hover restore rule inside @supports"
        window = source[idx:idx + 250]
        if "border-color: var(--color-accent);" not in window:
            return False, ".runway-card:has(input:checked):hover must restore the accent border-color"
        # Same T6 retarget as the chip's own hover clause above.
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in window:
            return False, (
                ".runway-card:has(input:checked):hover must RESTATE T6's inset ring rather than "
                "clearing the shadow")
        if "box-shadow: none;" in window:
            return False, (
                ".runway-card:has(input:checked):hover must not clear the shadow — that would "
                "erase T6's selection ring on hover")

        # Fallback intact: all four pre-existing server-class rules must
        # still exist verbatim (source.index would already have raised/
        # returned an error above via the wash check, but assert the two
        # not otherwise touched here too).
        for selector in (
            ".theme-chip--selected {",
            ".theme-chip--selected .theme-chip__body {",
            ".runway-card--selected {",
            ".theme-chip--selected .theme-chip__check {",
            ".runway-card--selected .runway-card__check {",
        ):
            if selector not in source:
                return False, "expected the pre-existing fallback rule %r to survive verbatim" % (selector,)

        # --- 23-10-PLAN.md Task 1 (D3/CFG-32): SELECTION ANSWERS -----
        # D3's clause is that selecting a chip or a card answers with a
        # small scale and a wash that fades in, rather than switching
        # state instantly. The entire risk in that sentence is the
        # feature-query block count above: the live treatment lives
        # inside @supports, so the obvious way to animate it is a second
        # @supports block, which is what Phase 15's D-05 did and had
        # retired, and what 23-RESEARCH.md names as the single largest
        # threat to this count in the whole phase.
        #
        # It is not needed, and this is the assertion that keeps the
        # next editor from reaching for it anyway: a `transition` is a
        # property of the ELEMENT, not of the state. Declared on the
        # BASE rule it animates the property however the state that
        # changes it is reached — live `:has(input:checked)` inside the
        # query, and the server-rendered `--selected` fallback outside
        # it, from one declaration. So this check asserts BOTH halves in
        # one place: the transitions exist on the base rules (outside
        # the query), AND the query itself contains no `transition` at
        # all. Both live in this ONE check function on purpose, so that
        # "helpfully" moving a transition inside the block fails exactly
        # once rather than twice.
        def _base_rule_body(selector):
            # Newline-anchored, not a bare substring search:
            # ".theme-chip__body {" also occurs inside
            # ".theme-chip--selected .theme-chip__body {", which sits
            # EARLIER in the file, so str.index() on the bare selector
            # would silently measure the wrong rule.
            anchored = "\n" + selector
            if anchored not in source:
                return None, "expected style.css to declare the base rule %r" % (selector,)
            idx = source.index(anchored)
            if idx > supports_idx:
                return None, (
                    "expected the base rule %r to be declared BEFORE (outside) the one "
                    "@supports selector(:has(*)) block" % (selector,))
            start = idx + len(anchored)
            return source[start:source.index("}", start)], ""

        def _carries_transition(body, label, properties):
            if "transition:" not in body:
                return (
                    "%s must declare the selection transition on its OWN base rule — a "
                    "transition declared on the base rule animates the property however the "
                    "state is reached, which is why the live :has() treatment needs no second "
                    "feature query (D3, 23-10-PLAN.md Task 1)" % (label,))
            decl = body[body.index("transition:"):]
            decl = decl[:decl.index(";") + 1] if ";" in decl else decl
            for prop in properties:
                if prop not in decl:
                    return (
                        "%s's transition must name %r — it is one of the properties that "
                        "actually changes on selection, and a property absent from the list "
                        "switches instantly (got %r)" % (label, prop, decl.strip()))
            if "var(--motion-fast)" not in decl:
                return (
                    "%s's transition must spend var(--motion-fast), the phase's REACTION token "
                    "— a selection is a state change the user just caused and is watching for "
                    "confirmation of (got %r)" % (label, decl.strip()))
            return None

        for selector, properties in (
            (".theme-chip {", ("transform", "border-color", "box-shadow")),
            (".theme-chip__body {", ("background-color",)),
            (".runway-card {",
             ("transform", "border-color", "box-shadow", "background-color")),
        ):
            body, err = _base_rule_body(selector)
            if body is None:
                return False, err
            err = _carries_transition(body, selector.rstrip(" {"), properties)
            if err:
                return False, err

        # The scale itself, and the fallback parity that is the whole
        # reason one transition declaration is enough: the live rule and
        # the --selected fallback must carry the SAME transform, or a
        # browser without :has() gets a differently-sized selected card
        # — the identical contract T6 already holds for the border and
        # the ring.
        def _scale_of(selector, inside):
            if selector not in source:
                return None, "expected style.css to declare %r" % (selector,)
            idx = source.index(selector)
            if inside and idx < supports_idx:
                return None, "expected %r to live inside the feature query" % (selector,)
            if not inside and idx > supports_idx:
                return None, "expected %r to live outside the feature query" % (selector,)
            start = idx + len(selector)
            body = source[start:source.index("}", start)]
            match = re.search(r"transform:\s*scale\(([^)]+)\)", body)
            if not match:
                return None, (
                    "expected %r to carry the selection scale (`transform: scale(...)`) — the "
                    "wash's fade is the primary signal and the scale is its punctuation, and a "
                    "transform changes no layout box so T6 cannot recur through it" % (selector,))
            return match.group(1).strip(), ""

        scales = {}
        for selector, inside in (
            (".theme-chip:has(input:checked) {", True),
            (".theme-chip--selected {", False),
            (".runway-card:has(input:checked) {", True),
            (".runway-card--selected {", False),
        ):
            value, err = _scale_of(selector, inside)
            if value is None:
                return False, err
            scales[selector] = value
        if len(set(scales.values())) != 1:
            return False, (
                "the live :has(input:checked) rules and their --selected fallbacks must carry "
                "the SAME scale, or a browser without :has() renders a different-sized selected "
                "card — the identical parity contract T6 already holds for the border and the "
                "ring, got %r" % (scales,))

        # Saved-but-not-live must CLEAR the scale, exactly as it already
        # clears the accent ring and the wash: a chip can be saved while
        # its neighbour is the live choice, and two scaled chips would
        # claim two selections.
        for selector in (
            ".theme-chip--selected:not(:has(input:checked)) {",
            ".runway-card--selected:not(:has(input:checked)) {",
        ):
            if selector not in source:
                return False, "expected style.css to declare %r" % (selector,)
            start = source.index(selector) + len(selector)
            body = source[start:source.index("}", start)]
            if "transform: none;" not in body:
                return False, (
                    "%s must clear the selection scale with `transform: none;` — it already "
                    "clears the accent ring and the wash for the same reason, and a saved-but-"
                    "not-live chip that stays scaled claims a selection it does not have"
                    % (selector,))

        # And the block itself carries NO transition. Measured on
        # comment-stripped source, because the paragraphs inside that
        # block (and the one this plan adds above it) discuss the very
        # word this scan counts — a raw scan would be tripped by the
        # comment that explains why the rule is not there.
        stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        if stripped.count(supports_marker) != 1:
            return False, (
                "expected exactly one %r block in comment-stripped source, got %d"
                % (supports_marker, stripped.count(supports_marker)))
        open_idx = stripped.index(supports_marker) + len(supports_marker) - 1
        depth = 0
        close_idx = None
        for pos in range(open_idx, len(stripped)):
            if stripped[pos] == "{":
                depth += 1
            elif stripped[pos] == "}":
                depth -= 1
                if depth == 0:
                    close_idx = pos
                    break
        if close_idx is None:
            return False, "the @supports selector(:has(*)) block is never closed"
        if "transition" in stripped[open_idx:close_idx]:
            return False, (
                "the ONE @supports selector(:has(*)) block declares a `transition` — it must "
                "not. A transition belongs on each selectable surface's BASE rule, where it "
                "animates the live :has() treatment and the --selected fallback identically "
                "from one declaration; moving it inside the query is the first step toward the "
                "second feature-query block Phase 15's D-05 already had retired (D3, "
                "23-10-PLAN.md Task 1)")

        return True, ""
    check(
        "the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore) is keyed to "
        "live :has(input:checked) state inside one @supports selector(:has(*)) block, for both .theme-chip and "
        ".runway-card, with every pre-existing --selected fallback rule surviving verbatim (quick task 260904-bbi) "
        "— and, since 23-10-PLAN.md Task 1 (D3/CFG-32), selection ANSWERS: a fast transition naming the transform, "
        "the border colour, the shadow and the wash is declared on each selectable surface's BASE rule, the live "
        "rules and their --selected fallbacks carry the SAME scale, saved-but-not-live clears it, and the ONE "
        "feature-query block declares no transition at all — asserted together so moving one inside fails once",
        _strong_selected_treatment_is_keyed_to_the_live_checked_radio)

    def _destructive_disconnect_is_secondary_and_selection_is_free_and_focusable():
        """22-15-PLAN.md Task 1 — T2, T6 and T15 in one structural scan.

        All three were defects a code READER could see and no harness
        could: every declaration involved was present in the file and
        string-comparison correct, and the bugs lived entirely in the
        cascade and in the box model.

        T2  — the destructive Disconnect control wore the page's primary
              accent fill because a bare class (0,1,0) loses to
              `button[type="submit"]` (0,1,1). The fix is the element-
              qualified selector at equal specificity, later in source;
              the prohibition on weakening the primary rule with
              `:where()` is asserted too, because that shortcut would
              surrender the accent fill file-wide.
        T6  — selection grew the border from 1px to 2px, so a selected
              card was a different size from its siblings. No rule in
              this file may declare a 2px border again.
        T15 — a selected card's focus state was pixel-identical to rest
              (the real focus target is an off-screen radio), and
              `summary` was missing from the focus-visible floor.
        """
        source = _read_static("style.css")

        # --- T2 -----------------------------------------------------
        primary = 'button[type="submit"] {'
        disconnect = "button.calendar-disconnect-btn {"
        if primary not in source:
            return False, "expected style.css to still declare the primary button[type=submit] rule"
        if disconnect not in source:
            return False, (
                "expected the Disconnect control's rule to be element-qualified "
                "(button.calendar-disconnect-btn), the (0,1,1) form that is equal in specificity "
                "to the primary rule — T2")
        if source.index(disconnect) <= source.index(primary):
            return False, (
                "expected button.calendar-disconnect-btn to sit AFTER button[type=\"submit\"] in "
                "source order — at equal specificity source order is the whole mechanism (T2)")
        # The primary rule keeps its own specificity: a zero-specificity
        # wrapper around it is the shortcut 22-UI-SPEC.md's T2 row bans
        # by name, because it hands the accent fill to every competing
        # zero-specificity rule in the file at once.
        if ":where(button" in source:
            return False, (
                "expected NO :where() wrapper on the primary button rule — dropping it to (0,0,0) "
                "surrenders the accent fill file-wide (T2)")
        disconnect_body = source[
            source.index(disconnect) + len(disconnect):
            source.index("}", source.index(disconnect))]
        if "box-shadow: none;" not in disconnect_body:
            return False, (
                "expected button.calendar-disconnect-btn to neutralize box-shadow — this is a "
                "submit button and would otherwise keep the primary rule's inset highlight, the "
                "same reason .logout-form button/.dirty-bar__cancel/.frame-strip__cell button all "
                "carry it (T2)")

        # --- T6: not one 2px border left anywhere in the file --------
        if "border: 2px" in source or "border-width: 2px" in source:
            return False, (
                "expected ZERO 2px border declarations in style.css — T6 holds every selectable "
                "surface at a constant 1px and carries selection on an inset ring, so a 2px "
                "border anywhere is a reintroduction of the 2px layout shift")
        # The third selectable surface, which lives outside the chip/card
        # group the checks above cover.
        row_selector = "input:checked + .frame-colours__row {"
        if row_selector not in source:
            return False, "expected style.css to still declare %r" % (row_selector,)
        row_body = source[
            source.index(row_selector) + len(row_selector):
            source.index("}", source.index(row_selector))]
        if "border-color: var(--color-accent);" not in row_body:
            return False, "expected the checked frame-colours row to recolour its 1px border (T6)"
        if "box-shadow: inset 0 0 0 2px var(--color-accent);" not in row_body:
            return False, "expected the checked frame-colours row to carry T6's inset ring"

        # --- T15 ----------------------------------------------------
        focus_rule = (
            "a:focus-visible,\n"
            "button:focus-visible,\n"
            "input:focus-visible,\n"
            "select:focus-visible,\n"
            "summary:focus-visible {")
        if focus_rule not in source:
            return False, (
                "expected summary to have joined the global focus-visible selector list — it is a "
                "native interactive element with no visible focus state at all today (T15)")
        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 1:
            return False, (
                "expected exactly one @supports selector(:has(*)) block, got %d"
                % source.count(supports_marker))
        supports_idx = source.index(supports_marker)
        selected_focus = (
            ".runway-card:has(input:focus-visible),\n"
            "  .theme-chip:has(input:focus-visible) {")
        if selected_focus not in source:
            return False, (
                "expected a :has(input:focus-visible) focus ring covering BOTH selectable-card "
                "components — a selected card's focus state is invisible without it (T15)")
        if source.index(selected_focus) < supports_idx:
            return False, (
                "expected the selected-card focus ring INSIDE the one @supports selector(:has(*)) "
                "block — this file is pinned at exactly one block, never two")
        focus_body = source[
            source.index(selected_focus) + len(selected_focus):
            source.index("}", source.index(selected_focus))]
        # The global floor's OWN values, not a new treatment.
        for decl in ("outline: 2px solid var(--color-accent);", "outline-offset: 2px;"):
            if decl not in focus_body:
                return False, (
                    "expected the selected-card focus ring to reuse the global focus-visible "
                    "floor's own %r, not invent a treatment (T15)" % (decl,))
        return True, ""
    check(
        "the destructive Disconnect control is element-qualified to (0,1,1) and placed after "
        "button[type=\"submit\"] with the primary rule's own specificity intact and no :where() "
        "shortcut (T2); style.css declares ZERO 2px borders anywhere, with all three selectable "
        "surfaces carrying a recoloured constant 1px edge plus an inset accent ring (T6); and "
        "summary has joined the global focus-visible floor while a selected chip or card gets that "
        "same floor's own outline values through a :has(input:focus-visible) rule inside the ONE "
        "feature-query block (T15) — 22-15-PLAN.md Task 1",
        _destructive_disconnect_is_secondary_and_selection_is_free_and_focusable)

    def _calendar_fusion_css_retired_from_the_stylesheet():
        # 21-07-PLAN.md Task 3 (D-13/R-08/Pitfall 2): both retired
        # fusion rules must be gone from the real stylesheet, not merely
        # dead-but-present — a plan that deletes the merged card's
        # separate-siblings markup while leaving this CSS behind would
        # ship dead rules that no longer match anything (Pitfall 2).
        source = _read_static("style.css")
        for retired_selector in (
                ".page-section:has(+ .calendar-disconnect-form)",
                ".calendar-disconnect-form {"):
            if retired_selector in source:
                return False, "expected %r to be retired from style.css entirely" % (retired_selector,)
        return True, ""
    check(
        "style.css carries neither retired Calendar-card fusion selector "
        "(.page-section:has(+ .calendar-disconnect-form), .calendar-disconnect-form) anywhere "
        "(D-13/R-08/Pitfall 2)",
        _calendar_fusion_css_retired_from_the_stylesheet)

    def _saved_but_unchecked_card_degrades_to_a_quiet_current_marker():
        # quick task 260904-bbi: the server-rendered --selected class is
        # demoted from driving the strong treatment to an honest, quiet
        # "this is what is saved" marker once it is no longer the live
        # choice: an accent-free dashed 70%-muted-text ring, its wash and
        # check glyph cleared, and an English "Current" tag rendered as a
        # ::after pseudo-element (see PLAN.md's
        # <current_tag_markup_decision> for why a pseudo-element and not
        # a <span>).
        source = _read_static("style.css")
        muted = "color-mix(in srgb, var(--color-text) 70%, transparent)"

        for prefix in (".theme-chip--selected:not(:has(input:checked))", ".runway-card--selected:not(:has(input:checked))"):
            base_selector = prefix + " {"
            if base_selector not in source:
                return False, "expected style.css to declare %r" % (base_selector,)
            idx = source.index(base_selector)
            body = source[idx + len(base_selector):source.index("}", idx)]
            if "dashed" not in body:
                return False, "%r must use a dashed ring, not a solid one" % (base_selector,)
            if muted not in body:
                return False, "%r must use the established 70%%-muted-text colour, not a new strength" % (base_selector,)
            if "var(--color-accent)" in body:
                return False, "%r must be accent-free - the quiet marker signals 'saved', not 'selected'" % (base_selector,)

        chip_body_selector = ".theme-chip--selected:not(:has(input:checked)) .theme-chip__body {"
        if chip_body_selector not in source:
            return False, "expected style.css to declare %r" % (chip_body_selector,)
        idx = source.index(chip_body_selector)
        window = source[idx:idx + 100]
        if "background: transparent;" not in window:
            return False, "%r must clear the wash back to transparent" % (chip_body_selector,)

        for check_selector in (
            ".theme-chip--selected:not(:has(input:checked)) .theme-chip__check {",
            ".runway-card--selected:not(:has(input:checked)) .runway-card__check {",
        ):
            if check_selector not in source:
                return False, "expected style.css to declare %r" % (check_selector,)
            idx = source.index(check_selector)
            window = source[idx:idx + 100]
            if "display: none;" not in window:
                return False, "%r must hide the check glyph" % (check_selector,)

        # 22-10-PLAN.md Task 1 (T10): retargeted in place. The badge's
        # text used to be the hard-coded English literal
        # `content: "Current";`, twice, in an app that ships in two
        # languages. It is now `content: attr(data-current-label)`, with
        # the translated string server-rendered onto the element. The
        # pseudo-element itself is unchanged, so every other assertion in
        # this check still holds verbatim; only the source of the text
        # moved. The English literal must now be ABSENT.
        current_literal = "content: attr(%s)" % config_page.CURRENT_BADGE_ATTR
        if source.count(current_literal) != 2:
            return False, (
                "expected exactly 2 occurrences of %r, got %d" % (current_literal, source.count(current_literal)))
        hard_coded = 'content: "Current"'
        # Comment-filtered deliberately, and this filter is load-bearing
        # rather than convenient: the DECLARATION is gone, but the rule's
        # own comment block still quotes `content: "Current"` while
        # recording the four-point justification for keeping a
        # pseudo-element instead of a <span>. 22-UI-SPEC.md §2's T10 row
        # says that justification is unchanged, so the comment must
        # survive — deleting prose to satisfy a grep is the defect this
        # filter exists to prevent. Same filter shape as this plan's own
        # acceptance criterion (`grep -v '^ *[*/]'`).
        declarations = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith(("*", "/")))
        if hard_coded in declarations:
            return False, (
                "expected zero hard-coded English %r DECLARATIONS - T10 moves the badge's "
                "text to a server-rendered, translated attribute" % (hard_coded,))

        for after_selector in (
            ".theme-chip--selected:not(:has(input:checked))::after {",
            ".runway-card--selected:not(:has(input:checked))::after {",
        ):
            if after_selector not in source:
                return False, "expected style.css to declare %r" % (after_selector,)
            idx = source.index(after_selector)
            window = source[idx:idx + 250]
            if current_literal not in window:
                return False, "%r must render the English 'Current' tag" % (after_selector,)

        if "actuel" in source.lower():
            return False, "expected zero occurrences of the French word for 'current' - DP-2 requires English copy"

        muted_count = source.count(muted)
        if muted_count < 17:
            return False, (
                "expected the established 70%%-muted-text mix to appear at least 17 times (16 pre-existing plus "
                "the new quiet-marker rules), got %d - a new muted strength must not be invented" % (muted_count,))

        return True, ""
    check(
        "the saved-but-no-longer-live --selected card degrades to an accent-free dashed 70%-muted ring with its "
        "wash/check glyph cleared and a \"Current\" ::after tag whose text is read from the server-rendered, "
        "translated data-current-label attribute (exactly 2 occurrences site-wide, zero hard-coded English "
        "declarations, zero French copy in the stylesheet), reusing the established muted-text strength rather "
        "than inventing a new one (quick task 260904-bbi; retargeted by 22-10-PLAN.md Task 1, T10)",
        _saved_but_unchecked_card_degrades_to_a_quiet_current_marker)

    def _style_css_carries_section_caption_and_no_dirty_bar_rules_survive():
        # 27-04-PLAN.md (D-04/CFG-63): SUPERSEDES this check's own
        # pre-27-04 subject — quick task 260901-re6/260901-s5o's floating-
        # card restyle and its >=960px fixed positioning are both deleted
        # wholesale along with `.dirty-bar` itself (style.css's own
        # superseding comment records the account, right where the rule
        # used to be). (a) below is the one assertion that survives
        # unchanged: `.section-caption` is unrelated to the bar and this
        # is its only test site.
        source = _read_static("style.css")

        caption_selector = ".section-caption {"
        if caption_selector not in source:
            return False, "expected style.css to declare a .section-caption rule"
        idx = source.index(caption_selector)
        window = source[idx:idx + 200]
        if "color-mix(in srgb, var(--color-text) 70%, transparent)" not in window:
            return False, "expected .section-caption's rule body to carry the 70% color-mix muted idiom"

        if ".dirty-bar" in source:
            return False, "expected zero occurrences of .dirty-bar anywhere in style.css — CFG-63 retired it"
        return True, ""
    check(
        "style.css declares .section-caption (70% muted color-mix) and carries zero occurrences of "
        ".dirty-bar anywhere — the floating-card restyle and its fixed->=960px positioning "
        "(quick task 260901-re6, quick task 260901-s5o, 23-09-PLAN.md Task 1's entrance) are all "
        "retired wholesale along with the component (27-04-PLAN.md, D-04/CFG-63)",
        _style_css_carries_section_caption_and_no_dirty_bar_rules_survive)

    def _skypane_bar_arrive_keyframes_survive_unreferenced():
        # 27-04-PLAN.md (D-04/CFG-63): the save bar's own entrance
        # (23-09-PLAN.md Task 1, D3/CFG-32) animated from this block, and
        # every rule that referenced it (the base .dirty-bar rule's own
        # `animation:` declaration) is retired along with the bar. The
        # @keyframes DEFINITION is kept rather than deleted — this file's
        # own @keyframes count is pinned at 4 by a separate check below,
        # a live count re-derived by running rather than a value this
        # plan is free to move — so removing it would require the phase
        # to invent a replacement use or renumber the pin; neither is
        # this plan's to do. It is therefore orphaned deliberately: no
        # rule anywhere in the file may still reference its name.
        source = _read_static("style.css")
        keyframes_marker = "@keyframes skypane-bar-arrive {"
        if source.count(keyframes_marker) != 1:
            return False, (
                "expected exactly one %s block (kept, not deleted, to hold the @keyframes count "
                "at 4), got %d" % (keyframes_marker, source.count(keyframes_marker)))
        if "animation: skypane-bar-arrive" in source:
            return False, (
                "expected NO rule anywhere to still declare animation: skypane-bar-arrive — the "
                "one rule that did (the retired .dirty-bar) is gone, and this block must not be "
                "silently reattached to something else without a plan saying so")
        return True, ""
    check(
        "the retired save bar's own @keyframes skypane-bar-arrive block survives, unreferenced by "
        "any rule, so the file's pinned @keyframes count of 4 does not move (27-04-PLAN.md, CFG-63)",
        _skypane_bar_arrive_keyframes_survive_unreferenced)

    def _dirty_state_js_has_no_hardcoded_section_names():
        source = _read_static("dirty-state.js")
        for literal in ("Theme", "Runway", "Diagnostic LED"):
            if literal in source:
                return False, "expected no hardcoded occurrence of %r - section labels must come from the DOM" % (literal,)
        return True, ""
    check(
        "dirty-state.js contains no hardcoded occurrence of \"Theme\", \"Runway\", or \"Diagnostic LED\" (labels come from the DOM)",
        _dirty_state_js_has_no_hardcoded_section_names)

    def _dirty_state_js_only_fetches_never_polls_debounces_or_xhrs():
        # 27-04-PLAN.md Task 2 (CFG-63): SUPERSEDES this check's own
        # pre-27-04 ban — dirty-state.js is now the settings form's
        # auto-save driver and fetch is exactly how it saves, the
        # identical model quick-switch.js already ships. XMLHttpRequest
        # and setInterval stay forbidden outright: the first would be a
        # second, older request vocabulary beside fetch's already-shipped
        # one, and the second would mean a poll loop this file has no
        # business running. setTimeout is NOT banned outright — it drives
        # the SAME toast-dismiss timer quick-switch.js's own announce
        # Failure() already uses (TOAST_DISMISS_MS), duplicated rather
        # than shared for the identical no-cross-file-import reason every
        # other constant here is. What IS forbidden is using it to
        # DEBOUNCE a save — this plan's own D-04 note explicitly declines
        # that design — so the one setTimeout call in this file must be
        # scoped to the toast, never to beginSave().
        source = _read_static("dirty-state.js")
        if "fetch(" not in source:
            return False, "expected dirty-state.js to call fetch( — it is now the auto-save driver"
        for forbidden in ("XMLHttpRequest", "setInterval"):
            if forbidden in source:
                return False, "forbidden network/timer construct found in dirty-state.js: %r" % (forbidden,)
        if source.count("setTimeout") != 1:
            return False, (
                "expected exactly one setTimeout call — the toast's own dismiss timer, "
                "duplicated from quick-switch.js's identical idiom — got %d"
                % source.count("setTimeout"))
        timeout_idx = source.index("setTimeout")
        timeout_call = source[timeout_idx:timeout_idx + 200]
        if "beginSave" in timeout_call:
            return False, "expected the one setTimeout call to never reference beginSave — no debounced save"
        if "TOAST_DISMISS_MS" not in timeout_call:
            return False, "expected the one setTimeout call to be the toast's own TOAST_DISMISS_MS dismiss"
        return True, ""
    check(
        "dirty-state.js calls fetch( (it is now the auto-save driver), contains neither "
        "XMLHttpRequest nor setInterval, and its one setTimeout call is the toast's own "
        "TOAST_DISMISS_MS dismiss timer — never a debounced save (27-04-PLAN.md Task 2, CFG-63)",
        _dirty_state_js_only_fetches_never_polls_debounces_or_xhrs)

    # ==================================================================
    # 15-05-PLAN.md Task 3 (D-10, D-11, 15-VALIDATION.md row 10): the
    # per-flight colour-rules editor's markup/copy checks.
    # ==================================================================

    # 21-05-PLAN.md Task 1 (D-06/D-10): the rules editor is no longer a
    # standalone sibling section — it relocated into the Frame colours
    # card's own "Per-flight rules" usage panel, which only the
    # SCOPE_DISPLAY render carries (Frame colours is never rendered on
    # SCOPE_ALL/SCOPE_DEVICE any more). Every check below is retargeted
    # to render at SCOPE_DISPLAY and to bound the rules panel's own
    # segment via its data-usage-panel-target attribute through to the
    # next section (the Calendar card, which always follows it), rather
    # than the retired RULES_SECTION_HEADING/POLL_SECTION_HEADING pair
    # (Display never renders Poll at all).
    def _rules_panel_segment(rendered):
        start = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_RULES))
        end = rendered.index('<div class="page-section page-section--nested" ', start)
        return rendered[start:end]

    def _frame_colours_card_full_shape_checklist():
        # 21-05-PLAN.md Task 1/Task 3 (D-06..D-12, R-11): the one
        # consolidated checklist test covering every remaining bullet
        # from Task 1's own <action> "Checks" paragraph and Task 3's own
        # markup-contract bullets, against a real Display render.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)

        # Exactly one .frame-colours card, first under "Look".
        look_pos = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        frame_colours_pos = rendered.index('class="page-section frame-colours')
        if rendered.count('class="page-section frame-colours') != 1:
            return False, "expected exactly one .frame-colours card"
        if not (look_pos < frame_colours_pos):
            return False, "expected the Frame colours card after the Look section intro"

        # Exactly four colour_usage radios, in locked order, departures checked.
        usage_matches = re.findall(
            r'name="colour_usage" value="([^"]*)" class="visually-hidden"( checked)?', rendered)
        if [u for u, _c in usage_matches] != list(config_page.COLOUR_USAGES):
            return False, "expected the four colour_usage radios in locked order, got %r" % (usage_matches,)
        checked_usages = [u for u, c in usage_matches if c]
        if checked_usages != [config_page.COLOUR_USAGE_DEPARTURES]:
            return False, "expected only departures checked by default, got %r" % (checked_usages,)

        # Exactly four usage panels, none carrying hidden or style=.
        panel_matches = re.findall(r'<fieldset class="frame-colours__usage-panel"[^>]*>', rendered)
        if len(panel_matches) != 4:
            return False, "expected exactly four usage panels, got %d" % len(panel_matches)
        for tag in panel_matches:
            if "hidden" in tag or "style=" in tag:
                return False, "expected no hidden/style= attribute on a usage panel, got %r" % (tag,)

        # Each of the three chip grids' radios carry form="settings-form".
        for field in ("theme", "theme_arriving", "calendar_theme_id"):
            if ('name="%s"' % field) not in rendered:
                return False, "expected at least one %s radio" % field
            total = rendered.count('name="%s" value="' % field)
            with_form = len(re.findall(
                r'name="%s" value="[^"]*" class="visually-hidden"( form="%s")'
                % (re.escape(field), re.escape(config_page.SETTINGS_FORM_ID)), rendered))
            if with_form != total:
                return False, "expected every %s radio to carry form=%r, got %d/%d" % (
                    field, config_page.SETTINGS_FORM_ID, with_form, total)

        # Arrivals'/calendar's leading chip submits the empty string.
        if rendered.count('name="theme_arriving" value=""') != 1:
            return False, "expected exactly one leading empty-string theme_arriving chip"
        if rendered.count('name="calendar_theme_id" value=""') != 1:
            return False, "expected exactly one leading empty-string calendar_theme_id chip"

        # The rules panel holds the rule list/empty-state, the add form
        # and the "How rules combine" details.
        rules_segment = _rules_panel_segment(rendered)
        if 'action="%s"' % config_page.RULES_ADD_ROUTE not in rules_segment:
            return False, "expected the rule add form inside the rules panel"
        if escape_html(config_page.RULES_HOW_RULES_COMBINE_SUMMARY) not in rules_segment:
            return False, "expected the How rules combine disclosure inside the rules panel"

        # No trace of the retired checkbox/heading/Calendar-card grid.
        if "theme_arriving_enabled" in rendered:
            return False, "expected no theme_arriving_enabled checkbox anywhere"
        if "Use a different theme for arrivals" in rendered:
            return False, "expected no arrivals-override checkbox label anywhere"
        calendar_start = rendered.index(
            '<h2 class="text-heading" id="%s">' % config_page.CALENDAR_HEADING_ID)
        calendar_end = rendered.index(
            escape_html(config_page.CALENDAR_HOW_IT_WORKS_SUMMARY), calendar_start)
        if "theme-chip-grid" in rendered[calendar_start:calendar_end]:
            return False, "expected no chip grid inside the Calendar card"

        # No nested <form> anywhere (the pinned Pitfall-1 regression check).
        depth = 0
        pos = 0
        while True:
            open_pos = rendered.find("<form", pos)
            close_pos = rendered.find("</form>", pos)
            if open_pos == -1 and close_pos == -1:
                break
            if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                if depth >= 1:
                    return False, "expected no <form> nested inside another <form>"
                depth += 1
                pos = open_pos + len("<form")
            else:
                depth -= 1
                pos = close_pos + len("</form>")

        # A French render shows the four row labels and "Comme les départs".
        try:
            prefs.set_request_prefs(lang="fr")
            fr_rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        for fr_label in ("Départs", "Arrivées", "Vols du calendrier", "Règles par vol"):
            if fr_label not in fr_rendered:
                return False, "expected the French row label %r" % (fr_label,)
        if "Comme les départs" not in fr_rendered:
            return False, "expected the French 'Comme les départs' text"
        return True, ""
    check(
        "the Frame colours card's full shape: one card first under Look, four colour_usage radios in "
        "locked order (departures checked), four hidden/style=-free usage panels, every theme/"
        "theme_arriving/calendar_theme_id radio carrying form=\"settings-form\", a leading empty-string "
        "chip on arrivals/calendar, the rules panel holding the add form and How-rules-combine "
        "disclosure, no trace of the retired checkbox/heading/Calendar-card grid, no nested <form>, "
        "and a French render showing all four row labels plus 'Comme les départs' (21-05-PLAN.md "
        "Task 1/Task 3)",
        _frame_colours_card_full_shape_checklist)

    def _rules_section_renders_inside_frame_colours_after_form():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        form_end = rendered.index("</form>")
        rules_pos = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_RULES))
        calendar_pos = rendered.index('<div class="page-section page-section--nested" ', rules_pos)
        if not (form_end < rules_pos < calendar_pos):
            return False, (
                "expected </form> < rules panel < Calendar card, got positions %d/%d/%d"
                % (form_end, rules_pos, calendar_pos))
        return True, ""
    check(
        "render() places the rules panel, inside the Frame colours card, after the settings </form> "
        "and before the Calendar card (Phase 15 D-10, relocated by 21-05-PLAN.md Task 1 D-06)",
        _rules_section_renders_inside_frame_colours_after_form)

    def _rules_section_empty_state_then_list_once_a_rule_exists():
        empty_ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(empty_ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        if config_page.RULES_EMPTY_HEADING not in rules_segment:
            return False, "expected the empty-state heading with no rules"
        # 20-09-PLAN.md Task 3 (D-15c/d): the retired table/card split is
        # gone outright — a plain .rule-list, never a table.
        if "rule-list" in rules_segment or "<table" in rules_segment:
            return False, "expected no list markup in the empty-state branch"

        tmp = tempfile.mkdtemp(prefix="skypane-rules-markup-")
        try:
            result = colour_rules.add_rule(
                tmp, "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
            if result != colour_rules.ADD_OK_NEW:
                return False, "test setup failure: add_rule() returned %r" % (result,)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        filled_ctx = dict(empty_ctx)
        filled_ctx["colour_rules"] = registry
        filled_ctx["now"] = "2026-01-02T00:00:00+00:00"
        rendered = config_page.render(filled_ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        if config_page.RULES_EMPTY_HEADING in rules_segment:
            return False, "expected the empty state to be replaced once a rule exists"
        if '<ul class="rule-list">' not in rules_segment:
            return False, "expected the .rule-list once a rule exists"
        if "AFR1234" not in rules_segment:
            return False, "expected the seeded rule's key to appear in the rendered list"
        return True, ""
    check(
        "the rules section renders the empty state with no rules, and the empty state is replaced by "
        "the .rule-list once a rule exists (D-15c/d, retargeted from the retired cards-then-table shape)",
        _rules_section_empty_state_then_list_once_a_rule_exists)

    def _rules_list_orders_most_specific_first_then_alphabetically():
        # D-15c: rows ordered callsign, then hex, then prefix - and
        # alphabetically within each kind. colour_rules.rule_rows() itself
        # already guarantees this order (RULE_KINDS order, then sorted
        # value) - this check pins _rule_list_html()'s own consumption of
        # that order at the rendered-markup level, not just at the data
        # layer.
        tmp = tempfile.mkdtemp(prefix="skypane-rules-order-")
        try:
            for kind, value, theme_id in (
                ("prefix", "AFR", "red"),
                ("callsign", "BAW1234", "blue"),
                ("hex", "3944F2", "white"),
                ("callsign", "AFR1234", "black"),
            ):
                result = colour_rules.add_rule(
                    tmp, kind, value, theme_id, now="2026-01-01T00:00:00+00:00")
                if result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule(%r) returned %r" % (kind, result)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": registry,
            "poll_cooldown_remaining": 0,
            "now": "2026-01-02T00:00:00+00:00",
        }, scope=config_page.SCOPE_DISPLAY)
        list_match = re.search(r'<ul class="rule-list">(.*?)</ul>', rendered, re.S)
        if not list_match:
            return False, "expected a .rule-list"
        list_segment = list_match.group(1)
        expected_order = ["AFR1234", "BAW1234", "3944F2", "AFR"]
        positions = [
            list_segment.index('<span class="rule-row__key mono">%s</span>' % value)
            for value in expected_order
        ]
        if positions != sorted(positions):
            return False, (
                "expected callsign(alpha)/hex/prefix order %r, got positions %r"
                % (expected_order, positions))
        return True, ""
    check(
        "a seeded set of rules of every kind renders most-specific first (callsign, then hex, then "
        "prefix), alphabetically within each kind (D-15c)",
        _rules_list_orders_most_specific_first_then_alphabetically)

    def _rules_copy_appears_escaped_verbatim():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        copy_strings = (
            # 21-05-PLAN.md Task 1 (D-06): RULES_SECTION_HEADING is
            # retired outright — the rules row's own label (also its
            # panel's <legend>) is the replacement naming text.
            config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],
            config_page.RULES_SECTION_CAPTION,
            config_page.RULE_KIND_FIELD_LABEL,
            config_page.RULE_VALUE_FIELD_LABEL,
            config_page.RULE_ADD_BUTTON_TEXT,
            config_page.RULES_EMPTY_HEADING,
            config_page.RULES_EMPTY_BODY,
            config_page.RULES_HOW_RULES_COMBINE_SUMMARY,
            config_page.RULES_HOW_RULES_COMBINE_BODY,
        )
        for text in copy_strings:
            if escape_html(text) not in rendered:
                return False, "expected %r to appear escaped-verbatim in the rendered page" % (text,)
        for kind, label in config_page.RULE_KIND_LABELS.items():
            if escape_html(label) not in rendered:
                return False, "expected the kind label %r (for %r) to appear escaped-verbatim" % (label, kind)
        for kind, title in config_page.RULE_KIND_TITLES.items():
            if escape_html(title) not in rendered:
                return False, "expected the kind title %r (for %r) to appear escaped-verbatim" % (title, kind)
        return True, ""
    check(
        "every Flight-colours copy string (heading, caption, field labels, kind labels/titles, "
        "empty-state heading/body, the How-rules-combine disclosure) appears escaped-verbatim, "
        "matching 20-UI-SPEC.md's Copywriting Contract byte for byte",
        _rules_copy_appears_escaped_verbatim)

    def _frame_colours_rules_row_label_locked_verbatim():
        # 21-05-PLAN.md Task 1 (D-06/D-07): retargeted from the retired
        # RULES_SECTION_HEADING ("Flight colours") to the rules row's
        # own locked label — the replacement naming text, per
        # 21-UI-SPEC.md's Copywriting Contract §D.
        if config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES] != "Per-flight rules":
            return False, (
                "expected the rules row label to equal the locked \"Per-flight rules\" text exactly, "
                "got %r" % (config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_RULES],))
        return True, ""
    check(
        "the Frame colours card's rules row label equals 21-UI-SPEC.md's locked \"Per-flight rules\" "
        "text exactly (D-06/D-07, retargeted from the retired RULES_SECTION_HEADING)",
        _frame_colours_rules_row_label_locked_verbatim)

    def _rules_no_select_and_three_named_radios_one_checked():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        if "<select" in rules_segment:
            return False, "expected no <select> anywhere in the Flight-colours section (D-15b)"
        radio_count = rules_segment.count('name="rule_kind"')
        if radio_count != len(colour_rules.RULE_KINDS):
            return False, "expected %d rule_kind radios, got %d" % (len(colour_rules.RULE_KINDS), radio_count)
        for kind in colour_rules.RULE_KINDS:
            if 'id="rule-kind-%s"' % kind not in rules_segment:
                return False, "expected a rule_kind radio with id rule-kind-%s" % kind
            if 'title="%s"' % escape_html(config_page.RULE_KIND_TITLES[kind]) not in rules_segment:
                return False, "expected the %s radio's label to carry the technical title" % kind
        # Scoped to just the three rule_kind <input> tags themselves — the
        # compact theme-chip grid immediately below also uses " checked"
        # for its own selected chip, which a whole-segment count would
        # wrongly fold in.
        kind_inputs = re.findall(r'<input type="radio" name="rule_kind"[^>]*>', rules_segment)
        if len(kind_inputs) != len(colour_rules.RULE_KINDS):
            return False, "expected %d rule_kind <input> tags, got %d" % (
                len(colour_rules.RULE_KINDS), len(kind_inputs))
        checked_inputs = [tag for tag in kind_inputs if " checked" in tag]
        if len(checked_inputs) != 1:
            return False, "expected exactly one checked rule_kind radio by default, got %d" % len(checked_inputs)
        if 'value="%s"' % colour_rules.RULE_KIND_CALLSIGN not in checked_inputs[0]:
            return False, "expected the callsign/Flight radio to be the one checked by default"
        return True, ""
    check(
        "the Flight-colours section carries no <select>, and its add form's three rule_kind radios "
        "carry the three kind ids and the three technical titles, exactly one checked by default "
        "(D-15b)",
        _rules_no_select_and_three_named_radios_one_checked)

    def _rules_row_carries_pill_badge_and_confirmed_remove_form():
        tmp = tempfile.mkdtemp(prefix="skypane-rules-row-")
        try:
            result = colour_rules.add_rule(
                tmp, "callsign", "AFR1234", "white", now="2026-01-01T00:00:00+00:00")
            if result != colour_rules.ADD_OK_NEW:
                return False, "test setup failure: add_rule() returned %r" % (result,)
            registry = colour_rules.load_colour_rules(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": registry,
            "poll_cooldown_remaining": 0,
            "now": "2026-01-02T00:00:00+00:00",
        }, scope=config_page.SCOPE_DISPLAY)
        row_match = re.search(r'<li class="rule-row">(.*?)</li>', rendered, re.S)
        if not row_match:
            return False, "expected a .rule-row list item"
        row = row_match.group(1)
        if 'class="rule-row__kind banner__pill"' not in row:
            return False, "expected the kind badge to compose .banner__pill"
        if escape_html(config_page.RULE_KIND_LABELS["callsign"]) not in row:
            return False, "expected the plain-language kind word in the badge"
        if "data-confirm=" not in row:
            return False, "expected the Remove form to carry data-confirm (D-15c, locked)"
        if escape_html(config_page.RULE_REMOVE_BUTTON_TEXT) not in row:
            return False, "expected the Remove button's own text, not the airlines gallery's Delete"
        expected_hex = config_page._palette_hex(device_config.THEMES["white"]["departing_index"])
        if 'class="theme-chip__dot" style="background:%s"' % escape_html(expected_hex) not in row:
            return False, "expected the row's swatch dot to carry the real _palette_hex() value"
        return True, ""
    check(
        "a rendered rule row carries a .banner__pill kind badge with the plain-language word, a "
        "computed _palette_hex() swatch dot, and a data-confirm Remove form (D-15c)",
        _rules_row_carries_pill_badge_and_confirmed_remove_form)

    def _rules_empty_state_carries_no_heading_element():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        empty_match = re.search(r'<div class="empty-state-plain">(.*?)</div>', rules_segment, re.S)
        if not empty_match:
            return False, "expected the .empty-state-plain wrapper"
        if "<h" in empty_match.group(1):
            return False, "expected the empty state to carry no heading element, muted sans only (D-15d)"
        if escape_html(config_page.RULES_EMPTY_HEADING) not in empty_match.group(1):
            return False, "expected the empty-state heading sentence"
        return True, ""
    check(
        "the empty state is muted sans copy in .empty-state-plain and carries no <h*> heading element, "
        "never the serif empty_state() heading (D-15d)",
        _rules_empty_state_carries_no_heading_element)

    def _rules_suggestion_chips_present_with_data_and_absent_with_no_events():
        tmpdir = tempfile.mkdtemp(prefix="skypane-rules-suggestions-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            rendered = config_page.render({
                "device_config": {"theme": "white", "tracked_runway": "3"},
                "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
                "poll_cooldown_remaining": 0,
                "state_dir": tmpdir,
            }, scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        rules_segment = _rules_panel_segment(rendered)
        if 'class="rule-suggestion-chip" data-kind="callsign" data-value="AFR1380"' not in rules_segment:
            return False, "expected a suggestion chip for the seeded callsign"

        empty_rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
            "state_dir": None,
        }, scope=config_page.SCOPE_DISPLAY)
        empty_segment = _rules_panel_segment(empty_rendered)
        if "rule-suggestion-chip" in empty_segment:
            return False, "expected no suggestion chips when there are no recent events"
        return True, ""
    check(
        "up to five suggestion chips render with data-kind/data-value from recent runway events, and "
        "none render when there are no events (D-15e)",
        _rules_suggestion_chips_present_with_data_and_absent_with_no_events)

    def _plain_render_carries_both_disclosures_in_full_never_collapsed():
        """D-17 (21-01-PLAN.md Task 2): the display mode that used to
        collapse both disclosures to one plain sentence is deleted —
        replaces a deleted check that tested that now-removed
        mechanism.
        """
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        if escape_html(config_page.RULES_HOW_RULES_COMBINE_SUMMARY) not in rules_segment:
            return False, "expected the full 'How rules combine' <details> disclosure"
        if "<details>" not in rules_segment:
            return False, "expected a <details> disclosure for rules"
        calendar_start = rendered.index(
            '<h2 class="text-heading" id="%s">' % config_page.CALENDAR_HEADING_ID)
        if escape_html(config_page.CALENDAR_HOW_IT_WORKS_SUMMARY) not in rendered[calendar_start:]:
            return False, "expected the full Calendar 'How it works' <details> disclosure"
        # D-17: neither collapsed one-sentence variant may appear anywhere in
        # the rendered body — their exact punctuation ("wins." / "screen.")
        # never occurs as a substring of the full <details> body text above
        # ("wins — a flight..." / "colour a flight that happens..."), so this
        # is an unambiguous check, not a coincidental prefix match.
        if "It only colours a flight already on screen." in rendered:
            return False, "expected no collapsed one-sentence Calendar disclosure anywhere"
        if "The most specific match wins." in rendered:
            return False, "expected no collapsed one-sentence rules disclosure anywhere"
        return True, ""
    check(
        "a plain Display render always carries the full 'How rules combine' and Calendar "
        "'How it works' <details> disclosures, never a collapsed one-sentence variant (D-17)",
        _plain_render_carries_both_disclosures_in_full_never_collapsed)

    def _rules_section_carries_no_dirty_section_attr():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        rules_segment = _rules_panel_segment(rendered)
        if config_page.DIRTY_SECTION_ATTR in rules_segment:
            return False, "expected the rules panel to carry no data-dirty-section attribute"
        return True, ""
    check(
        "the rules panel, inside the Frame colours card, carries no data-dirty-section attribute of "
        "its own — the card's OWN outer wrapper carries the one attribute for all four usages, "
        "exactly like the Poll section carries none",
        _rules_section_carries_no_dirty_section_attr)

    def _rules_french_render_shows_french_row_label_and_button():
        # 21-05-PLAN.md Task 1 (D-06): retargeted from the retired
        # "Couleurs de vol" heading (RULES_SECTION_HEADING) to the
        # rules row's own French label, "Règles par vol" — the
        # replacement naming text now rendered both by the assignment
        # row and by the panel's own <legend>.
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if "Règles par vol" not in rendered:
            return False, "expected the French rules row label 'Règles par vol'"
        if "Ajouter la règle" not in rendered:
            return False, "expected the French Add-rule button 'Ajouter la règle'"
        return True, ""
    check(
        "a French Display render of the Frame colours card's rules row/panel shows 'Règles par vol' "
        "and 'Ajouter la règle' (D-05, retargeted from the retired Flight-colours heading)",
        _rules_french_render_shows_french_row_label_and_button)

    # ==================================================================
    # Section 1b (16-05-PLAN.md Task 3): the Calendar settings group -
    # render() copy/status/theme-select checks, plus handle_post()'s
    # calendar_theme_id membership gate. 16-VALIDATION.md's registry row
    # (D-01) and T-16-SECRET row are both covered here.
    # ==================================================================

    _CALENDAR_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
        "now": "2026-09-07T09:12:04+00:00",
    }

    def _calendar_status_parts(rendered):
        # 20-09-PLAN.md Task 1 (D-14b): the status sentence is now
        # layout.status_row()'s verdict/detail pair, not a single
        # <p class="calendar-status"> (retired).
        match = re.search(
            r'<span class="status-row__verdict">(.*?)</span>'
            r'<span class="status-row__detail">(.*?)</span>',
            rendered, re.S)
        if not match:
            raise AssertionError("expected a .status-row element")
        return match.group(1), match.group(2)

    _CALENDAR_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_CONNECTED_VERDICT, quote=True)
    _CALENDAR_NOT_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT, quote=True)

    def _calendar_status_not_configured_is_exclusive():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_NOT_CONNECTED_ESCAPED:
            return False, "expected the 'Not connected' verdict, got %r" % (verdict,)
        if detail:
            return False, "expected an empty detail when not configured, got %r" % (detail,)
        return True, ""
    check(
        "with no calendar configured, render() emits the 'Not connected' verdict with an empty detail "
        "(D-14b)",
        _calendar_status_not_configured_is_exclusive)

    def _calendar_status_configured_pending_is_exclusive():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail:
            return False, (
                "expected an empty detail when configured with no attempt recorded yet, got %r" % (detail,))
        return True, ""
    check(
        "with a calendar configured and no fetch attempt recorded yet, render() emits the 'Connected' "
        "verdict with an empty detail (D-14b)",
        _calendar_status_configured_pending_is_exclusive)

    def _calendar_status_configured_fetch_failed_is_exclusive():
        # D-14b/T-20-30: at least one attempt recorded with no usable
        # sync yet is the one derivable failed-fetch category — the
        # fixed, mapped sentence, never a caught exception's own text.
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None,
            calendar_last_attempt_at=1893456000.0)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail != escape_html(config_page.CALENDAR_STATUS_FETCH_FAILED_DETAIL):
            return False, "expected the mapped fetch-failed sentence, got %r" % (detail,)
        return True, ""
    check(
        "with a calendar configured, an attempt recorded, and no usable sync, render() emits the mapped "
        "'The feed could not be read' detail — never an exception's own text (D-14b/T-20-30)",
        _calendar_status_configured_fetch_failed_is_exclusive)

    def _calendar_status_configured_synced_is_exclusive_with_relative_age():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True,
            calendar_last_synced_at="2026-09-07T09:00:00+00:00", calendar_entry_count=12)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if "12" not in detail:
            return False, "expected the entry count '12' in the detail, got %r" % (detail,)
        if "ago" not in detail:
            return False, "expected a relative-age fragment, proving relative_age_text() was used"
        return True, ""
    check(
        "with a calendar configured and a last_synced_at present, render() emits the 'Connected' verdict "
        "with a detail carrying the entry count and a relative-age fragment, never a bare ISO string "
        "(D-14b)",
        _calendar_status_configured_synced_is_exclusive_with_relative_age)

    def _calendar_status_unparseable_synced_falls_back_to_no_detail():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True,
            calendar_last_synced_at="not-a-real-timestamp")
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_CONNECTED_ESCAPED:
            return False, "expected the 'Connected' verdict, got %r" % (verdict,)
        if detail:
            return False, "expected an empty detail for an unparseable stored value, got %r" % (detail,)
        return True, ""
    check(
        "with a calendar configured and a last_synced_at that is present but unparseable, the empty "
        "detail is used rather than a fabricated time (D-14b)",
        _calendar_status_unparseable_synced_falls_back_to_no_detail)

    def _calendar_copy_fidelity_against_ui_spec():
        spec_path = os.path.join(
            REPO_ROOT, ".planning", "phases",
            "20-companion-suggestions-from-the-audit-french-localisation-liv",
            "20-UI-SPEC.md")
        with open(spec_path, encoding="utf-8") as fh:
            spec = fh.read()
        for name in (
                "CALENDAR_CAPTION",
                "CALENDAR_STATUS_DETAIL_TEMPLATE",
                "CALENDAR_STATUS_FETCH_FAILED_DETAIL",
                "CALENDAR_CONNECT_BUTTON_TEXT",
                "CALENDAR_REPLACE_URL_SUMMARY"):
            value = getattr(config_page, name)
            if value not in spec:
                return False, "%s is not a contiguous substring of 20-UI-SPEC.md: %r" % (name, value)
        return True, ""
    check(
        "the caption, the status detail template, the fetch-failed sentence, the Connect button text, "
        "and the Replace-URL disclosure summary are each a contiguous substring of 20-UI-SPEC.md, so a "
        "paraphrase fails rather than merely looking different (D-14a..c)",
        _calendar_copy_fidelity_against_ui_spec)

    def _calendar_merged_button_copy_fidelity_against_21_ui_spec():
        # 21-07-PLAN.md Task 1 (D-13/D-14): the two new short button-
        # text constants the merge introduces — pinned against phase
        # 21's own UI-SPEC, matching _calendar_copy_fidelity_against_
        # ui_spec()'s established discipline for the phase-20 strings.
        spec_path = os.path.join(
            REPO_ROOT, ".planning", "phases",
            "21-companion-feedback-round-3-frame-controls-up-front-home-with",
            "21-UI-SPEC.md")
        with open(spec_path, encoding="utf-8") as fh:
            spec = fh.read()
        for name in ("CALENDAR_REPLACE_BUTTON_TEXT", "CALENDAR_DISCONNECT_BUTTON_TEXT"):
            value = getattr(config_page, name)
            if value not in spec:
                return False, "%s is not a contiguous substring of 21-UI-SPEC.md: %r" % (name, value)
        return True, ""
    check(
        "the merged card's own two new short button-text constants (the connected-state Replace "
        "button, the small grey Disconnect button) are each a contiguous substring of 21-UI-SPEC.md "
        "(D-13/D-14)",
        _calendar_merged_button_copy_fidelity_against_21_ui_spec)

    def _calendar_forbidden_vocabulary_absent():
        # 16-UI-SPEC.md's own "What this section deliberately does NOT
        # say" section (carried forward, unaffected by this plan's
        # rewording) bans AFFIRMATIVE real-time-awareness claims and
        # person/role/employer/crew-function nouns.
        blob = " ".join([
            config_page.CALENDAR_SECTION_HEADING,
            config_page.CALENDAR_CAPTION,
            config_page.CALENDAR_HOW_IT_WORKS_BODY,
            config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT,
            config_page.CALENDAR_STATUS_CONNECTED_VERDICT,
        ]).lower()
        forbidden_phrases = (
            "watches", "watch for", "follows", "monitors", "notifies",
            "currently flying", "in the air now", "on duty", "crew",
            "roster", "pilot", "duty roster",
        )
        bad = [phrase for phrase in forbidden_phrases if phrase in blob]
        if bad:
            return False, "forbidden vocabulary found: %r" % (bad,)
        if re.search(r"\btracks\b|\bis tracking\b|\bwatching\b|\bmonitoring\b", blob):
            return False, "found an affirmative tracking/watching/monitoring claim"
        if "does not track" not in blob:
            return False, "expected the mandated negated 'does not track ... on its own' construction"
        return True, ""
    check(
        "the Calendar card's copy carries none of the phase's banned affirmative real-time-awareness or "
        "crew-role vocabulary, while still carrying the mandated negated 'does not track' construction "
        "verbatim",
        _calendar_forbidden_vocabulary_absent)

    def _calendar_secret_never_reaches_render_function():
        # 21-07-PLAN.md Task 2 (D-14/R-10): EXTENDED, not replaced — this
        # check now also exercises the masked-URL line (state_dir wired
        # through), asserting the host + "…" fragment DOES appear (proof
        # the masking helper actually ran) while the token, path, query-
        # parameter name and the whole raw URL still never do.
        token = "sk1-distinctive-token-2rv9"
        host = "private-crew-calendar.example.internal"
        path = "feeds/roster-export"
        query_param = "auth_token"
        url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            assert calendar_rules.save_calendar_url(tmpdir, url) is True
            configured = calendar_rules.calendar_is_configured(tmpdir)
            if not configured:
                return False, "expected calendar_is_configured() to report True with the secret file written"
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=configured,
                calendar_last_synced_at=None, state_dir=tmpdir)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        if escape_html("%s…" % host) not in rendered:
            return False, "expected the masked host + ellipsis fragment to appear once connected"
        for needle in (token, path, query_param, url):
            if needle in rendered:
                return False, "expected %r never to appear in the rendered page" % (needle,)
        return True, ""
    check(
        "with the calendar secret file holding a URL carrying a distinctive token, render() emits the "
        "masked host + ellipsis fragment but never the token, the path segment, the query-parameter "
        "name, or the whole raw URL (T-16-SECRET, extended by 21-07-PLAN.md Task 2 for the new masked-"
        "URL line, D-14/R-10)",
        _calendar_secret_never_reaches_render_function)

    def _calendar_no_preview_no_count_in_rendered_page():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            entries = [
                {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                 "start_at": 1893456000.0, "end_at": 1893459600.0},
                {"airline_iata": "AF", "origin_iata": "NCE", "destination_iata": "ORY",
                 "start_at": 1893484800.0, "end_at": 1893488400.0},
                {"airline_iata": "BA", "origin_iata": "LHR", "destination_iata": "ORY",
                 "start_at": 1893500000.0, "end_at": 1893503600.0},
            ]
            # This check's subject is the Settings page's rendered copy, not
            # retention - an explicit `now` bracketing the 2030-dated
            # fixture entries keeps them in-window regardless of the wall
            # clock (render() itself never reads this file back, so this
            # has no effect on the assertions below, but it keeps the write
            # path exercised the same way every run).
            now = 1893456000.0
            if not calendar_rules.write_calendar_registry(
                    tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now):
                return False, "expected the fixture registry write to succeed"
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=True,
                calendar_last_synced_at="2026-09-07T09:00:00+00:00",
                calendar_entry_count=len(entries),
                colour_rules={kind: {} for kind in colour_rules.RULE_KINDS})
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            for code_pattern in (r"\bORY\b", r"\bTLS\b", r"\bNCE\b", r"\bLHR\b", r"\bAF\b", r"\bBA\b"):
                if re.search(code_pattern, rendered):
                    return False, "expected no calendar-derived code matching %r anywhere on the rendered page" % (code_pattern,)
            # D-14b (this plan's own status row) deliberately DOES show a
            # derived flight count now — the old prohibition on a count
            # is retired; only the specific airport/airline codes stay
            # forbidden (16-UI-SPEC.md's own D-01 isolation, unaffected).
            if not re.search(r"\b3\s+upcoming\s+flights?\b", rendered.lower()):
                return False, "expected the D-14b status detail's own flight-count phrase"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "a populated calendar registry (real-shaped routes/airline codes) never surfaces any airport "
        "code or airline code, while the status row's own entry count DOES appear (D-14b; 16-UI-SPEC.md "
        "D-01's code-isolation half carried forward, its count-prohibition half retired)",
        _calendar_no_preview_no_count_in_rendered_page)

    def _calendar_d01_registry_entries_never_appear_in_rules_list():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            entries = [
                {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                 "start_at": 1893456000.0, "end_at": 1893459600.0},
            ]
            # This check's subject is D-01 isolation from the rules list, not
            # retention - an explicit `now` bracketing the 2030-dated
            # fixture entry keeps it in-window regardless of the wall clock,
            # for the same reason given in the check above.
            now = 1893456000.0
            if not calendar_rules.write_calendar_registry(
                    tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now):
                return False, "expected the fixture registry write to succeed"
            result = colour_rules.add_rule(
                tmpdir, colour_rules.RULE_KIND_CALLSIGN, "AFR1234", "black")
            if result not in (colour_rules.ADD_OK_NEW, colour_rules.ADD_OK_REPLACED):
                return False, "expected the manual rule to be added, got %r" % (result,)
            registry = colour_rules.load_colour_rules(tmpdir)
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=True,
                calendar_last_synced_at="2026-09-07T09:00:00+00:00",
                colour_rules=registry)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            rules_segment = _rules_panel_segment(rendered)
            if "AFR1234" not in rules_segment:
                return False, "expected the manually-added rule's key to appear in the rules list"
            for code_pattern in (r"\bORY\b", r"\bTLS\b"):
                if re.search(code_pattern, rules_segment):
                    return False, "expected no calendar-sourced row (matching %r) in the rules editor" % (code_pattern,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "with both a populated calendar registry and one hand-added colour rule, the rendered rules list "
        "shows exactly the manual rule and no calendar-sourced row (16-VALIDATION.md registry row, D-01)",
        _calendar_d01_registry_entries_never_appear_in_rules_list)

    def _calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order():
        # 21-05-PLAN.md Task 1 (D-06/D-09): the calendar_theme_id grid
        # moved off the Calendar card entirely, into the Frame colours
        # card's own "Calendar flights" usage panel — a leading "Same
        # as departures" chip (submitting the empty string) now
        # precedes the THEME_IDS-ordered chips, so the total radio
        # count is len(THEME_IDS) + 1, not len(THEME_IDS).
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        if rendered.count('name="calendar_theme_id"') != len(device_config.THEME_IDS) + 1:
            return False, (
                "expected one calendar_theme_id radio per THEME_IDS member plus one leading "
                "'Same as departures' chip, got %d"
                % rendered.count('name="calendar_theme_id"'))
        # Scoped to the calendar usage panel specifically — the arrivals
        # panel carries an identical class/aria-labelledby shape (both
        # are compact grids labelled by the same card heading), so a
        # page-wide regex would grab the wrong (earlier) panel.
        panel_start = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_CALENDAR))
        panel_segment = rendered[panel_start:rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_RULES))]
        # 27-07-PLAN.md Task 2 (CFG-68): the calendar grid now ALSO
        # carries the strip modifier and its own id (folded into a
        # carousel, same as departures/arrivals) — both are matched
        # rather than re-asserting an unconverted shape here, since this
        # check's own subject is the radio population/order, not the
        # carousel wrapper (that is _the_departures_grid_is_the_one_
        # renderer_presented_as_a_strip's job, generalised in Task 2).
        grid_match = re.search(
            r'<div class="theme-chip-grid theme-chip-grid--compact theme-chip-grid--strip" '
            r'role="radiogroup" aria-labelledby="%s" id="%s">(.*?)</div>\s*(?:<p|</fieldset)'
            % (re.escape(config_page.FRAME_COLOURS_HEADING_ID),
               re.escape(config_page.THEME_CAROUSEL_STRIP_ID_CALENDAR)),
            panel_segment, re.S)
        if not grid_match:
            return False, "expected the calendar theme grid carrying role=radiogroup and aria-labelledby"
        options = re.findall(r'name="calendar_theme_id" value="([^"]*)"', grid_match.group(1))
        if options != [""] + list(device_config.THEME_IDS):
            return False, (
                "expected the leading empty-string chip then radios in THEME_IDS order, got %r"
                % (options,))
        return True, ""
    check(
        "the Frame colours card's compact calendar_theme_id grid carries one leading 'Same as "
        "departures' chip plus exactly one radio per THEME_IDS member in order, with role=radiogroup "
        "and aria-labelledby pointing at the card's own heading (D-06/D-09, relocated by 21-05-PLAN.md "
        "Task 1)",
        _calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order)

    def _calendar_theme_chip_grid_saved_value_is_checked():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], calendar_theme_id="black")
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        # D-12 fix (20-REVIEW.md verification gap): every calendar_theme_id
        # radio now also carries a form="settings-form" attribute between
        # class="visually-hidden" and checked - see the Display <h2>-order
        # check further below for the full form= assertion.
        checked_ids = re.findall(
            r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
            rendered)
        if checked_ids != ["black"]:
            return False, "expected exactly the saved calendar_theme_id ('black') checked, got %r" % (checked_ids,)
        return True, ""
    check(
        "with a saved calendar_theme_id, that chip's radio carries checked and no other calendar_theme_id "
        "radio (including the leading 'Same as departures' chip) does (D-06/D-09)",
        _calendar_theme_chip_grid_saved_value_is_checked)

    def _calendar_theme_chip_grid_same_as_departures_checked_when_unset():
        # 21-05-PLAN.md Task 1 (D-09): R-07's own new semantics — an
        # unset calendar_theme_id now checks the leading "Same as
        # departures" chip (submitting the empty string), never the
        # chip matching the base theme itself. This REPLACES the old
        # (pre-D-09) "defaults to the base theme" visual behaviour that
        # test used to pin — the server-side storage semantics
        # (device_config.normalise_calendar_theme_id("") -> None) are
        # unaffected; only which chip's radio is marked `checked`
        # changes.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], theme="black")
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        checked_ids = re.findall(
            r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
            rendered)
        if checked_ids != [""]:
            return False, (
                "expected only the leading 'Same as departures' chip (value='') checked when "
                "calendar_theme_id is unset, got %r" % (checked_ids,))
        return True, ""
    check(
        "with no saved calendar_theme_id, only the leading 'Same as departures' chip is checked — "
        "never the chip matching the currently-selected base theme (D-06/D-09, replacing the retired "
        "pre-D-09 default-to-base-theme behaviour)",
        _calendar_theme_chip_grid_same_as_departures_checked_when_unset)

    def _calendar_placement_after_display_form_close_with_dirty_attr():
        # 21-07-PLAN.md Task 1 (D-13/Pitfall 2): retargeted from SCOPE_ALL
        # (the legacy render — Calendar no longer has an entry in
        # `builders` there at all, see the two dirty-section-count checks
        # above) to SCOPE_DISPLAY, and from "before the settings form's
        # closing tag" to "after" it — the merged calendar_group() now
        # embeds its own connect/replace <form>, which HTML forbids
        # nesting inside <form id="settings-form">, so the merged card
        # renders as a sibling AFTER that form closes, exactly like
        # Runway/Frame colours already do. The comparison landmark
        # changes too: DISPLAY_SECTION_HEADING ("Screen on / off") no
        # longer precedes Calendar on this scope at all (it moved to a
        # LATER supersection, 21-04-PLAN.md Task 1) — Frame colours'
        # own heading is the one that reliably still does.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        frame_colours_index = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.FRAME_COLOURS_HEADING_ID, config_page.FRAME_COLOURS_HEADING))
        # 20-09-PLAN.md Task 1 (D-14d): the Calendar heading carries its
        # own id (an aria-labelledby target elsewhere on the page).
        calendar_index = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.CALENDAR_HEADING_ID, config_page.CALENDAR_SECTION_HEADING))
        form_close_index = rendered.index(
            '<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
        form_close_index = rendered.index("</form>", form_close_index)
        if not (form_close_index < frame_colours_index < calendar_index):
            return False, (
                "expected </form> < Frame colours < Calendar, got %d, %d, %d"
                % (form_close_index, frame_colours_index, calendar_index))
        if '%s="%s"' % (config_page.DIRTY_SECTION_ATTR, config_page.CALENDAR_SECTION_HEADING) not in rendered:
            return False, "expected the Calendar group to carry the dirty-section attribute"
        return True, ""
    check(
        "on the Display scope, the Calendar heading's index is greater than the settings form's own "
        "closing tag and greater than Frame colours' own heading — a sibling AFTER the form, never a "
        "descendant before it, now that the merged card embeds its own connect/replace <form> — and "
        "the group still carries the dirty-section attribute (retargeted by 21-07-PLAN.md Task 1, "
        "D-13/Pitfall 2)",
        _calendar_placement_after_display_form_close_with_dirty_attr)

    def _calendar_group_no_inline_js_and_chip_grid_cross_submits_form():
        # 21-05-PLAN.md Task 1 (D-06, Structural Note 2): the
        # calendar_theme_id chip grid moved off the Calendar card into
        # the Frame colours card, which renders as a SIBLING of <form
        # id="settings-form"> — it no longer sits inside the form's own
        # markup range at all. Every calendar_theme_id radio instead
        # cross-submits via an explicit form="settings-form" attribute
        # (the same idiom Runway's own radios already use), which is
        # the correctness property this check now pins instead.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        radio_count = rendered.count('name="calendar_theme_id"')
        if radio_count < 1:
            return False, "expected at least one calendar_theme_id radio"
        # Every real theme's own radio and the leading empty-string chip
        # all share the identical attribute sequence up to form=, so a
        # per-value scan (rather than one fixed literal) covers all of
        # them.
        for theme_id in ("",) + device_config.THEME_IDS:
            needle = (
                'name="calendar_theme_id" value="%s" class="visually-hidden" form="%s"'
                % (theme_id, config_page.SETTINGS_FORM_ID))
            if needle not in rendered:
                return False, "expected calendar_theme_id=%r to cross-submit via form=%r" % (
                    theme_id, config_page.SETTINGS_FORM_ID)
        calendar_start = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_CALENDAR))
        calendar_end = rendered.index(
            '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_RULES))
        calendar_segment = rendered[calendar_start:calendar_end]
        if "onclick" in calendar_segment or "onchange" in calendar_segment or "<script" in calendar_segment:
            return False, "expected no inline event-handler attribute or script tag in the Calendar panel"
        return True, ""
    check(
        "the Frame colours card's calendar usage panel renders no inline event-handler attribute and "
        "no script tag, and every calendar_theme_id radio (including the leading 'Same as departures' "
        "chip) cross-submits into the settings form via form=\"settings-form\" despite the card being "
        "a sibling of that form (no-JS correctness, D-06/Structural Note 2)",
        _calendar_group_no_inline_js_and_chip_grid_cross_submits_form)

    def _handle_post_calendar_theme_id_valid_persists_and_carries_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({"calendar_theme_id": "white"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] != "white":
                return False, (
                    "expected calendar_theme_id 'white' on disk, got %r"
                    % (on_disk["calendar_theme_id"],))
            if on_disk["theme"] != "black":
                return False, (
                    "expected the existing theme 'black' to be carried forward unchanged, got %r"
                    % (on_disk["theme"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a valid calendar_theme_id persists it and carries every other field forward",
        _handle_post_calendar_theme_id_valid_persists_and_carries_forward)

    def _handle_post_calendar_theme_id_adversarial_rejected():
        # 21-05-PLAN.md Task 2 (D-09/R-07): "" is retargeted OUT of this
        # adversarial list — it is now the Frame colours card's own
        # legitimate "Same as departures" clear signal, covered by its
        # own dedicated round-trip check elsewhere in this file.
        for payload in ("chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"):
            tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
            try:
                _write_device_config(tmpdir, "black", "3")
                before = open(device_config.device_config_path(tmpdir), "rb").read()
                ctx = {"state_dir": tmpdir}
                flash_key = config_page.handle_post({"calendar_theme_id": payload}, ctx)
                after = open(device_config.device_config_path(tmpdir), "rb").read()
                if flash_key != config_page.FLASH_SAVE_FAILED:
                    return False, (
                        "expected FLASH_SAVE_FAILED for calendar_theme_id=%r, got %r"
                        % (payload, flash_key))
                if before != after:
                    return False, (
                        "expected device_config.json to be byte-identical for calendar_theme_id=%r, it changed"
                        % (payload,))
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return True, ""
    check(
        "handle_post with a non-member calendar_theme_id (a plain invalid id, a path-traversal-shaped "
        "payload, and a SQL-shaped payload) rejects the whole submission and writes nothing — '' is "
        "explicitly exempted from this rejection (D-09)",
        _handle_post_calendar_theme_id_adversarial_rejected)

    def _handle_post_calendar_theme_id_absent_leaves_unchanged():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            device_config.save_device_config(tmpdir, calendar_theme_id="green")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["calendar_theme_id"] != "green":
                return False, (
                    "expected calendar_theme_id to remain 'green' when the field is absent, got %r"
                    % (on_disk["calendar_theme_id"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with no calendar_theme_id field at all leaves an already-saved value untouched",
        _handle_post_calendar_theme_id_absent_leaves_unchanged)

    # ==================================================================
    # Section 1c (17-03-PLAN.md Task 3, D-01/D-02/D-07): the write-only
    # calendar_url field, the disconnect checkbox, the fourth (drift)
    # status state, and handle_post()'s three-way calendar resolution.
    # The empty-field-with-no-checkbox regression check below is the
    # single most important check in this plan (17-03-PLAN.md Task 3
    # item 6) — it is the regression the checkbox exists to prevent, and
    # it is invisible to any check that only exercises the calendar
    # fields deliberately.
    # ==================================================================

    # Four distinguishable calendar_group() states, matching Task 1's
    # own <behavior> bullets: (configured, drift, last_synced_at).
    _CALENDAR_GROUP_STATES = (
        (False, False, None),
        (True, False, None),
        (True, False, "2026-09-07T09:00:00+00:00"),
        (False, True, None),
    )

    def _calendar_group_call(configured, drift, last_synced_at):
        # 20-09-PLAN.md Task 1: calendar_group()'s widened signature —
        # last_attempt_at/entry_count are the two new parameters D-14b
        # needs, both harmlessly None/0 for these markup-shape checks.
        return config_page.calendar_group(
            configured, drift, last_synced_at, None, "2026-09-07T09:12:04+00:00",
            0, None, "white")

    def _calendar_connect_field_never_carries_value_in_either_state():
        # 21-07-PLAN.md Task 1 (D-13/D-14): the write-only feed-URL field
        # is now merged INTO calendar_group() itself — the not-connected
        # branch renders it unwrapped, the connected branch renders the
        # SAME field inside the Replace disclosure. Either way the field
        # never carries a value attribute (T-20-12).
        for configured in (False, True):
            html = _calendar_group_call(configured, False, None)
            if 'name="calendar_url"' not in html:
                return False, "expected the calendar_url field when configured=%r" % (configured,)
            after_name = html.split('name="calendar_url"', 1)[1].split(">", 1)[0]
            if "value=" in after_name:
                return False, (
                    "expected no value attribute on the calendar_url field when configured=%r"
                    % (configured,))
        return True, ""
    check(
        "the write-only calendar_url field renders in the merged calendar_group()'s own markup for "
        "both the connected and not-connected states and never carries a value attribute (D-13/D-14, "
        "retargeted after calendar_connect_section()'s retirement)",
        _calendar_connect_field_never_carries_value_in_either_state)

    def _calendar_connect_wraps_in_details_only_when_configured():
        # D-13/D-14: "While connected, the URL input is hidden behind a
        # 'Replace the feed URL' disclosure; while not connected, render
        # it unwrapped." The merged card ALSO always renders a second,
        # unrelated <details> ("How it works") in every state, so this
        # check scans for the Replace disclosure's own specific class
        # rather than a bare "<details" substring, which would always
        # be true now (Pitfall of the merge, not of the original check).
        connected_html = _calendar_group_call(True, False, None)
        if 'class="calendar-url-disclosure"' not in connected_html:
            return False, "expected the connect form wrapped in <details class=calendar-url-disclosure> when configured"
        if escape_html(config_page.CALENDAR_REPLACE_URL_SUMMARY) not in connected_html:
            return False, "expected the Replace-the-feed-URL summary when configured"
        not_connected_html = _calendar_group_call(False, False, None)
        if 'class="calendar-url-disclosure"' in not_connected_html:
            return False, "expected the connect form unwrapped (no calendar-url-disclosure) when not configured"
        if 'action="%s"' % config_page.CALENDAR_CONNECT_ROUTE not in not_connected_html:
            return False, "expected the connect form to post to CALENDAR_CONNECT_ROUTE either way"
        return True, ""
    check(
        "the merged calendar_group() wraps its connect form in <details class=calendar-url-disclosure> "
        "'Replace the feed URL' only when configured, and renders it unwrapped, posting to "
        "CALENDAR_CONNECT_ROUTE, when not (D-13/D-14, retargeted after calendar_connect_section()'s "
        "retirement)",
        _calendar_connect_wraps_in_details_only_when_configured)

    def _calendar_containment_at_the_renderer_five_needles():
        # The same five needles _calendar_secret_never_reaches_served_
        # http_bytes() (Section 3, below) uses, applied directly at the
        # merged calendar_group() — the one function that now renders
        # everything the Calendar card shows, including the connect/
        # replace form and the disconnect button — rather than only at
        # the served-HTTP-bytes boundary or the whole-page render()
        # boundary the two other T-17-SECRET checks already cover.
        # 21-07-PLAN.md Task 1: calendar_group() itself still never
        # receives the raw URL as of this task (Task 2 widens that
        # contract, narrowly, for the masked-URL line only — see that
        # task's own extended coverage of the two checks named above).
        token = "sk1-distinctive-token-9fq2"
        host = "private-roster-calendar.example.internal"
        path = "feeds/duty-export"
        query_param = "auth_token"
        url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            assert calendar_rules.save_calendar_url(tmpdir, url) is True
            configured = calendar_rules.calendar_is_configured(tmpdir)
            drift = calendar_rules.calendar_secret_mode_is_unsafe(tmpdir)
            group_html = _calendar_group_call(configured, drift, None)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        for needle in (token, host, path, query_param, url):
            if needle in group_html:
                return False, "expected %r never to appear in the merged calendar_group()'s own markup" % (needle,)
        return True, ""
    check(
        "the merged calendar_group(), called directly rather than through render(), never emits the "
        "token, host, path segment, query-parameter name, or whole URL of a configured calendar, even "
        "though it now also renders the connect/replace form and the disconnect button (T-17-SECRET, "
        "retargeted after calendar_connect_section()'s retirement)",
        _calendar_containment_at_the_renderer_five_needles)

    def _calendar_disconnect_checkbox_never_appears_in_calendar_group():
        # 19-11-PLAN.md Task 1 (D-08/A-26): the in-form disconnect
        # checkbox is retired outright from calendar_group() in EVERY
        # one of its four distinguishable states — disconnecting is now
        # its own standalone, confirmed form, checked separately below.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_group_call(configured, drift, last_synced_at)
            if 'name="calendar_disconnect"' in html:
                return False, (
                    "state %r: expected calendar_group() to render no calendar_disconnect "
                    "checkbox at all (D-08 retires it)" % ((configured, drift),))
        return True, ""
    check(
        "calendar_group() renders no calendar_disconnect checkbox in any of its four states "
        "(D-08/A-26: disconnecting is now its own standalone form, not an in-form checkbox)",
        _calendar_disconnect_checkbox_never_appears_in_calendar_group)

    def _calendar_disconnect_form_appears_only_when_expected():
        # 21-07-PLAN.md Task 1 (D-14): retargeted after calendar_
        # disconnect_section()'s retirement — the disconnect form is now
        # a data-only sibling fragment the merged calendar_group()
        # concatenates onto its own card, under the same predicate
        # (configured or drift) the retired standalone function used.
        # Drift additionally gets a visible small Disconnect button
        # (with no Replace disclosure — drift's own verdict already
        # reads "Not connected") so a drifted, unreadable stored link
        # can still be cleared.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_group_call(configured, drift, last_synced_at)
            has_form = (
                '<form id="%s" method="post" action="%s"'
                % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE)
            ) in html
            expected = configured or drift
            if has_form != expected:
                return False, (
                    "state %r: expected disconnect-form presence %r, got %r"
                    % ((configured, drift), expected, has_form))
            if has_form:
                if 'data-confirm-field' not in html:
                    return False, "expected the hidden confirm field to carry data-confirm-field"
                if 'name="%s" value=""' % config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD not in html:
                    return False, "expected the hidden confirm field to render with an EMPTY value"
                if "data-confirm=" not in html:
                    return False, "expected a data-confirm attribute carrying the confirm question"
                if (
                    'form="%s" class="calendar-disconnect-btn"' % config_page.CALENDAR_DISCONNECT_FORM_ID
                ) not in html:
                    return False, "expected a visible Disconnect button cross-submitting via form="
            else:
                # D-13: a plain not-connected render (no drift either)
                # shows the URL field and the primary Connect button —
                # and no Replace disclosure, no Disconnect button, no
                # data-confirm attribute at all.
                if "calendar-disconnect-btn" in html:
                    return False, "expected no Disconnect button when neither configured nor drifted"
                if "data-confirm=" in html:
                    return False, "expected no data-confirm attribute when neither configured nor drifted"
                if 'class="calendar-url-disclosure"' in html:
                    return False, "expected no Replace disclosure when neither configured nor drifted"
        return True, ""
    check(
        "the merged calendar_group() renders its disconnect form only when the calendar is connected "
        "or drifted, posting to CALENDAR_DISCONNECT_ROUTE with a hidden, empty, data-confirm-field-"
        "carrying confirm field, alongside a visible small Disconnect button cross-submitting via "
        "form= (D-08/A-26/D-14, retargeted after calendar_disconnect_section()'s retirement)",
        _calendar_disconnect_form_appears_only_when_expected)

    def _calendar_exactly_one_page_section_on_display_scope():
        # D-13: "there is no second Calendar page-section and no
        # trailing disconnect card" — checked in both states, since the
        # connected state additionally concatenates a data-only sibling
        # <form> fragment that must never itself carry a page-section
        # class.
        for configured in (False, True):
            ctx = dict(
                _CALENDAR_BASE_CTX, calendar_configured=configured, calendar_last_synced_at=None)
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            count = rendered.count('data-dirty-section="%s"' % config_page.CALENDAR_SECTION_HEADING)
            if count != 1:
                return False, (
                    "configured=%r: expected exactly one Calendar page-section, got %d"
                    % (configured, count))
        return True, ""
    check(
        "the Display render carries exactly one Calendar page-section in both the connected and "
        "not-connected states — no second Calendar card, no trailing disconnect card (D-13)",
        _calendar_exactly_one_page_section_on_display_scope)

    def _calendar_group_never_nests_a_form_inside_another_in_either_state():
        # D-13/Pitfall 2: the merged card's own connect/replace <form>
        # and its data-only disconnect-form sibling must never nest one
        # inside the other, in either the connected or not-connected
        # state — the same depth-tracking algorithm the Frame colours
        # card's own full-shape checklist uses, applied directly at the
        # merged calendar_group()'s own return value (card + sibling
        # disconnect form) rather than only at the whole-page boundary.
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = _calendar_group_call(configured, drift, last_synced_at)
            depth = 0
            pos = 0
            while True:
                open_pos = html.find("<form", pos)
                close_pos = html.find("</form>", pos)
                if open_pos == -1 and close_pos == -1:
                    break
                if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                    if depth >= 1:
                        return False, (
                            "state %r: expected no <form> nested inside another <form>"
                            % ((configured, drift),))
                    depth += 1
                    pos = open_pos + len("<form")
                else:
                    depth -= 1
                    pos = close_pos + len("</form>")
        return True, ""
    check(
        "the merged calendar_group()'s own return value (the card plus its data-only disconnect-form "
        "sibling) never nests one <form> inside another, in any of its four distinguishable states "
        "(D-13/Pitfall 2)",
        _calendar_group_never_nests_a_form_inside_another_in_either_state)

    def _calendar_disconnect_confirm_page_posts_back_with_confirm_preset():
        rendered = config_page.calendar_disconnect_confirm_page({})
        expected_form = (
            '<form method="post" action="%s">'
            '<input type="hidden" name="%s" value="%s">'
        ) % (
            config_page.CALENDAR_DISCONNECT_ROUTE,
            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD,
            html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE, quote=True),
        )
        if expected_form not in rendered:
            return False, "expected the confirm page's form to post to the same route with the confirm field pre-set"
        # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
        # Display this phase, so the cancel link now points back to the
        # page the disconnect action itself lives on.
        if 'href="%s"' % layout.DISPLAY_ROUTE not in rendered:
            return False, "expected a cancel link back to the Display page"
        if "<fieldset" in rendered or "<legend" in rendered:
            return False, "expected no <fieldset>/<legend> on the confirm page"
        return True, ""
    check(
        "calendar_disconnect_confirm_page() renders a form posting to CALENDAR_DISCONNECT_ROUTE with the "
        "confirm field pre-set to the accepted value, plus a plain cancel link to Display (D-08/A-26, "
        "retargeted from Device by 20-07-PLAN.md Task 1/D-11)",
        _calendar_disconnect_confirm_page_posts_back_with_confirm_preset)

    def _calendar_disconnect_form_is_not_inside_settings_form_on_display_scope():
        # 20-07-PLAN.md Task 1 (D-11): Calendar (and its disconnect
        # action) moved from Device to Display this phase — retargeted
        # from SCOPE_DEVICE to SCOPE_DISPLAY in place. 21-07-PLAN.md
        # Task 1 (D-14): the disconnect form's own opening tag now
        # carries an id attribute FIRST (id, method, action, data-
        # confirm, data-confirm-value, per 21-UI-SPEC.md §E's own given
        # markup order) — the literal search below is updated to match.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        settings_form_close = rendered.find("</form>")
        disconnect_form_open = rendered.find(
            '<form id="%s" method="post" action="%s"'
            % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE))
        if settings_form_close == -1:
            return False, "expected the settings form to be present"
        if disconnect_form_open == -1:
            return False, "expected the disconnect form to be present on the Display scope"
        if disconnect_form_open < settings_form_close:
            return False, "expected the disconnect form's opening tag to appear AFTER the settings form's closing tag"
        return True, ""
    check(
        "on the Display scope, the calendar disconnect form's opening tag appears after the settings "
        "form's own closing tag — it is a sibling, never a descendant (D-08/A-26, retargeted from "
        "Device by 20-07-PLAN.md Task 1/D-11, and again by 21-07-PLAN.md Task 1/D-14 for the id-first "
        "attribute order)",
        _calendar_disconnect_form_is_not_inside_settings_form_on_display_scope)

    def _calendar_connect_form_appears_before_the_runway_card_on_display_scope():
        # Polish fix 4 (D-14c): the connect/replace form used to render
        # after the WHOLE Display scope — below Runway and Flight
        # colours — far from the Calendar card. It now renders inside
        # the merged calendar_group()'s own connected-state Replace
        # disclosure (21-07-PLAN.md Task 1, D-13/D-14), which itself
        # renders after </form> closes (which itself now closes right
        # after the Frame colours card, since "What it watches"/Runway
        # moved to a later sibling supersection), so its own <form>'s
        # opening tag still appears strictly BEFORE the Runway card's
        # own radio input in document order.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        calendar_heading_index = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.CALENDAR_HEADING_ID, config_page.CALENDAR_SECTION_HEADING))
        connect_form_index = rendered.index(
            '<form method="post" action="%s"' % config_page.CALENDAR_CONNECT_ROUTE)
        runway_index = rendered.index('name="tracked_runway"')
        if not (calendar_heading_index < connect_form_index < runway_index):
            return False, (
                "expected Calendar heading < connect form < Runway card, got %d, %d, %d"
                % (calendar_heading_index, connect_form_index, runway_index))
        return True, ""
    check(
        "on the Display scope, calendar_connect_section()'s own <form> opening tag renders "
        "immediately after the Calendar card and strictly before the Runway card's own radio "
        "input, never after the whole page's groups (Polish fix 4, D-14c)",
        _calendar_connect_form_appears_before_the_runway_card_on_display_scope)

    def _calendar_disconnect_form_absent_when_not_configured_or_on_device_scope():
        # 20-07-PLAN.md Task 1 (D-11): Calendar never renders on Device
        # any more — retargeted in place (was: "...or on Display scope,
        # which never renders Calendar", the exact inverse, before this
        # phase moved the group).
        not_connected_ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        display_rendered = config_page.render(not_connected_ctx, scope=config_page.SCOPE_DISPLAY)
        if config_page.CALENDAR_DISCONNECT_ROUTE in display_rendered:
            return False, "expected no disconnect form when the calendar is not configured or drifted"
        connected_ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        device_rendered = config_page.render(connected_ctx, scope=config_page.SCOPE_DEVICE)
        if config_page.CALENDAR_DISCONNECT_ROUTE in device_rendered:
            return False, "expected no disconnect form on the Device scope, which never renders Calendar"
        return True, ""
    check(
        "the disconnect form is absent when the calendar is neither configured nor drifted, and absent "
        "from the Device scope, which never renders the Calendar group at all (D-08/A-26, retargeted "
        "from Display by 20-07-PLAN.md Task 1/D-11)",
        _calendar_disconnect_form_absent_when_not_configured_or_on_device_scope)

    def _calendar_status_drift_is_exclusive_and_precedes_not_configured():
        ctx = dict(
            _CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None,
            calendar_drift=True)
        verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
        if verdict != _CALENDAR_NOT_CONNECTED_ESCAPED:
            return False, "expected the 'Not connected' verdict when drifted, got %r" % (verdict,)
        if detail != escape_html(config_page.CALENDAR_STATUS_PERMISSION_UNSAFE):
            return False, "expected the drift detail sentence, got %r" % (detail,)
        return True, ""
    check(
        "with the stored calendar link's permissions drifted, render() emits the 'Not connected' verdict "
        "with the drift detail sentence — the drift branch, checked before 'not configured', still wins "
        "(D-02 ordering, D-14b)",
        _calendar_status_drift_is_exclusive_and_precedes_not_configured)

    def _calendar_status_drift_names_remedy_and_nothing_forbidden():
        text = config_page.CALENDAR_STATUS_PERMISSION_UNSAFE
        if "/" in text or "\\" in text:
            return False, "expected no path separator in the drift status string"
        if ".json" in text or ".ics" in text or "calendar_rules" in text:
            return False, "expected no filename in the drift status string"
        if "http" in text.lower():
            return False, "expected no part of a URL in the drift status string"
        if "paste" not in text.lower() or "feed url" not in text.lower():
            return False, "expected the drift status to name the remedy (paste the feed URL again)"
        return True, ""
    check(
        "the permission-drift status string names the remedy (paste the feed URL again) and names no path "
        "separator, filename, or part of a URL (D-02, 17-CONTEXT.md prohibitions)",
        _calendar_status_drift_names_remedy_and_nothing_forbidden)

    def _handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            for _ in range(2):
                flash_key = config_page.handle_post(
                    {"theme": "white", "calendar_url": ""}, ctx)
                if flash_key != config_page.FLASH_SAVED:
                    return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if not calendar_rules.calendar_is_configured(tmpdir):
                return False, "expected the calendar to remain configured after two unrelated saves"
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if len(registry["entries"]) != 1:
                return False, (
                    "expected the fetched entry to survive untouched, got %r" % (registry["entries"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "the single most important check in this plan (D-07): a form that changes an unrelated setting "
        "and carries an empty calendar_url field with no checkbox, submitted twice in a row via "
        "handle_post(), leaves a configured calendar and its fetched entries completely untouched",
        _handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves)

    def _handle_post_disconnect_clears_url_and_registry():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            if calendar_rules.calendar_is_configured(tmpdir):
                return False, "expected the calendar to be disconnected"
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if registry["entries"]:
                return False, "expected zero entries after disconnect, got %r" % (registry["entries"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with the disconnect checkbox at its expected value succeeds, disconnects the "
        "calendar, and empties its fetched-entries registry (D-04)",
        _handle_post_disconnect_clears_url_and_registry)

    def _handle_post_replace_url_stores_new_value_and_clears_registry():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/old.ics") is True
            now = time.time()
            entries = [{
                "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
                "start_at": now + 3600, "end_at": now + 7200}]
            assert calendar_rules.write_calendar_registry(
                tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"calendar_url": "https://example.invalid/new.ics"}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            new_url = calendar_rules.configured_calendar_url(tmpdir)
            if new_url != "https://example.invalid/new.ics":
                return False, "expected the new URL to be stored, got %r" % (new_url,)
            registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
            if registry["entries"]:
                return False, (
                    "expected zero entries after replacing the URL, got %r" % (registry["entries"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a different non-empty URL stores the new URL and clears the previous "
        "calendar's fetched-entries registry (D-05)",
        _handle_post_replace_url_stores_new_value_and_clears_registry)

    def _handle_post_contradiction_rejects_whole_save_including_unrelated_field():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme": "white",
                    "calendar_url": "https://example.invalid/other.ics",
                    "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
                },
                ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a non-empty URL together with the disconnect checkbox, plus a changed "
        "unrelated setting, rejects the whole save - neither the calendar nor the unrelated setting is "
        "written (D-07 contradiction, all-or-nothing)",
        _handle_post_contradiction_rejects_whole_save_including_unrelated_field)

    def _handle_post_crafted_disconnect_value_rejects_whole_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "calendar_disconnect": "yes"}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a crafted calendar_disconnect value rejects the whole save - neither the "
        "calendar nor the unrelated setting is written",
        _handle_post_crafted_disconnect_value_rejects_whole_save)

    def _handle_post_overlength_url_rejects_whole_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
            before_device = open(device_config.device_config_path(tmpdir), "rb").read()
            before_url = calendar_rules.configured_calendar_url(tmpdir)
            overlength = "https://example.invalid/" + "a" * (config_page.CALENDAR_URL_MAX_LEN + 100)
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme": "white", "calendar_url": overlength}, ctx)
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            after_device = open(device_config.device_config_path(tmpdir), "rb").read()
            if before_device != after_device:
                return False, (
                    "expected device_config.json to be byte-identical, the unrelated setting was written")
            if calendar_rules.configured_calendar_url(tmpdir) != before_url:
                return False, "expected the previously configured calendar to be unchanged"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a calendar_url longer than CALENDAR_URL_MAX_LEN rejects the whole save - "
        "neither the calendar nor the unrelated setting is written",
        _handle_post_overlength_url_rejects_whole_save)

    # ==================================================================
    # Section 2: one end-to-end check — launches the real companion/app.py
    # subprocess, logs in, posts a valid theme-and-runway pair, follows
    # the redirect, and asserts the rendered page carries D-07's
    # confirmation copy verbatim and shows the newly-saved runway
    # selected. No unit check can establish that the router, this page
    # module, and the persistence layer actually agree end to end.
    # ==================================================================

    # --- Phase 18: page scopes and the screen-type registry ---------------

    def _scope_groups_follow_the_screen_registry():
        from companion import screens
        screen = screens.screen_type()
        if config_page.scope_groups(config_page.SCOPE_DISPLAY) != tuple(screen["everyday_groups"]):
            return False, "expected the display scope to render the screen's everyday groups"
        if config_page.scope_groups(config_page.SCOPE_DEVICE) != tuple(screen["advanced_groups"]):
            return False, "expected the device scope to render the screen's advanced groups"
        everyday = set(config_page.scope_groups(config_page.SCOPE_DISPLAY))
        advanced = set(config_page.scope_groups(config_page.SCOPE_DEVICE))
        if everyday & advanced:
            return False, "expected no settings group on both pages, got %r" % (everyday & advanced,)
        if set(config_page.scope_groups(config_page.SCOPE_ALL)) != everyday | advanced:
            return False, "expected the legacy all-scope to be exactly the union of the two pages"
        if screens.screen_type("no-such-screen") is not screens.screen_type():
            return False, "expected an unknown screen id to fall back to the default screen"
        if screens.current_screen_id({"screen_id": "no-such-screen"}) != screens.DEFAULT_SCREEN_ID:
            return False, "expected a hostile ctx screen_id to resolve to the default screen"
        return True, ""
    check(
        "scope_groups() renders the display/device pages from companion/screens.py's per-screen "
        "declaration — disjoint, together equal to the legacy single page — and unknown screen ids "
        "fall back to the default screen",
        _scope_groups_follow_the_screen_registry)

    # --- 23-07-PLAN.md Task 2 (D2/CFG-36, X1/D-04): the Diagnostic LED
    # becomes the third real switch. ONE control for the setting
    # afterwards — a switch beside a surviving checkbox is exactly the
    # defect X1/D-04 was written to remove.

    def _the_led_group_renders_one_switch_and_no_surviving_checkbox():
        for stored in (True, False):
            rendered = config_page.led_group(stored)
            if 'name="led_enabled"' in rendered:
                return False, (
                    "stored=%r: an input named led_enabled still renders in the LED group — the "
                    "switch and a surviving checkbox would be TWO controls for one setting, the "
                    "exact defect X1/D-04 exists to remove" % (stored,))
            expected = (
                '<button type="submit" class="switch" role="switch" aria-checked="%s"'
                ' aria-labelledby="%s" aria-describedby="%s %s" %s form="%s">'
                % ("true" if stored else "false",
                   config_page.QUICK_LED_LABEL_ID, config_page.QUICK_LED_STATE_ID,
                   config_page.LED_SECTION_CAPTION_ID, layout.QUICK_SWITCH_CONTROL_ATTR,
                   config_page.QUICK_LED_FORM_ID))
            if expected not in rendered:
                return False, (
                    "stored=%r: expected the server-rendered switch %r — aria-checked is the "
                    "SAVED value, the name is the setting, and the group's own caption stays "
                    "reachable as a description; got %r"
                    % (stored, expected, rendered))
            if rendered.count('role="switch"') != 1:
                return False, (
                    "stored=%r: expected exactly ONE control in the LED group, got %d role=switch "
                    "elements" % (stored, rendered.count('role="switch"')))
            # The button is attached ACROSS the DOM to a form that is a
            # sibling of #settings-form: the group renders INSIDE the
            # settings form, and a <form> can never nest inside another.
            if ('form="%s"' % config_page.QUICK_LED_FORM_ID) not in rendered:
                return False, (
                    "stored=%r: the switch must reach its own form through a form= attribute — "
                    "the cross-DOM idiom the Send-a-test button already uses, because this card "
                    "renders inside <form id=\"settings-form\">" % (stored,))
            if config_page.LED_SECTION_CAPTION_ID not in rendered:
                return False, "stored=%r: the group's caption id is gone" % (stored,)
            # The pending-marker host and both translated state wordings.
            if layout.QUICK_SWITCH_REGION_ATTR not in rendered:
                return False, (
                    "stored=%r: the LED card carries no %s — quick-switch.js has nothing to mark "
                    "pending" % (stored, layout.QUICK_SWITCH_REGION_ATTR))
            if (layout.QUICK_STATE_ON_ATTR not in rendered
                    or layout.QUICK_STATE_OFF_ATTR not in rendered):
                return False, "stored=%r: expected both state wordings server-rendered" % (stored,)
        return True, ""
    check(
        "config_page.led_group() renders exactly ONE control for the setting — a server-rendered "
        "role=switch whose aria-checked is the stored value in both directions, named by the "
        "setting, described by its state span AND the group's own caption, attached across the DOM "
        "to its own /quick/led form — and no input[name=\"led_enabled\"] checkbox survives beside "
        "it (D2/CFG-36, X1/D-04, 23-07-PLAN.md Task 2)",
        _the_led_group_renders_one_switch_and_no_surviving_checkbox)

    def _the_quick_led_form_is_a_sibling_of_the_settings_form():
        # The <form> must never nest inside <form id="settings-form">:
        # HTML forbids it and the browser silently drops the inner one,
        # which would make the switch post the SETTINGS route instead —
        # a partial settings save, the exact shape T-23-25 is about.
        section = config_page.quick_led_form_html(True)
        if not section.startswith('<form method="post" action="/quick/led" '):
            return False, (
                "expected the LED quick form to open with its own literal method/action, got %r"
                % (section[:120],))
        if ('id="%s"' % config_page.QUICK_LED_FORM_ID) not in section:
            return False, "expected the form to carry the id the switch's form= attribute names"
        if "data-quick-switch" not in section:
            return False, (
                "expected the D-04 handshake attribute on the form — dirty-state.js and "
                "quick-switch.js both key on it")
        for token in ('<input type="hidden" name="state" value="off">',
                      '<input type="hidden" name="return_to" value="/device">'):
            if token not in section:
                return False, "expected %r in the LED quick form, got %r" % (token, section)
        if config_page.quick_led_form_html(False).count('name="state" value="on"') != 1:
            return False, (
                "the posted state must be the OPPOSITE of the stored one, or pressing the switch "
                "with scripts blocked re-asserts the state it is already in")
        if "<button" in section:
            return False, (
                "the form stays EMPTY — its button lives in the LED card and reaches it across "
                "the DOM, mirroring notifications_test_section()'s own shape")
        # And on a real Device render it is a sibling, not a descendant.
        tmp = tempfile.mkdtemp(prefix="skypane-quick-led-")
        try:
            device_config.save_device_config(tmp, led_enabled=True)
            ctx = {"state_dir": tmp, "device_config": device_config.load_device_config(tmp)}
            device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
            form_open = device.index('<form class="config-form"')
            form_close = device.index("</form>", form_open)
            quick_at = device.index('action="/quick/led"')
            if form_open < quick_at < form_close:
                return False, (
                    "the LED quick form renders INSIDE <form id=\"settings-form\"> — a nested "
                    "<form> is dropped by every browser and the switch would post /settings "
                    "instead, which is a partial settings save (T-23-25)")
            display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            if "/quick/led" in display:
                return False, "expected no LED quick form on the Display scope, which has no LED group"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "config_page.quick_led_form_html() is an EMPTY form carrying its own method/action/id, the "
        "D-04 handshake attribute and the two hidden fields with the posted state inverted from the "
        "stored one — and render() places it as a SIBLING of the settings form on the Device scope "
        "and not at all on Display (D2/CFG-36, 23-07-PLAN.md Task 2)",
        _the_quick_led_form_is_a_sibling_of_the_settings_form)

    def _display_scope_carries_runway_and_calendar_device_carries_neither():
        # 20-07-PLAN.md Task 1 (D-10/D-11): the group move itself, at the
        # registry level.
        display_groups = config_page.scope_groups(config_page.SCOPE_DISPLAY)
        device_groups = config_page.scope_groups(config_page.SCOPE_DEVICE)
        from companion import screens
        if screens.GROUP_RUNWAY not in display_groups or screens.GROUP_CALENDAR not in display_groups:
            return False, "expected Runway and Calendar in scope_groups(SCOPE_DISPLAY), got %r" % (display_groups,)
        if screens.GROUP_RUNWAY in device_groups or screens.GROUP_CALENDAR in device_groups:
            return False, "expected neither Runway nor Calendar in scope_groups(SCOPE_DEVICE), got %r" % (device_groups,)
        return True, ""
    check(
        "scope_groups(SCOPE_DISPLAY) contains Runway and Calendar, and scope_groups(SCOPE_DEVICE) "
        "contains neither (D-10/D-11)",
        _display_scope_carries_runway_and_calendar_device_carries_neither)

    def _display_render_carries_three_section_intros_in_locked_order():
        # 20-07-PLAN.md Task 1 (D-12): Look, What it watches, When it is
        # on, in that document order.
        #
        # RETARGETED (28-04-PLAN.md Task 1, CFG-72): this check used to
        # also assert "and nowhere on the Device scope" — Device's own
        # intro sentence/caption were unchanged by D-12, so Device had no
        # supersection tier at all. CFG-72 gives Device two supersections
        # of its own ("When it wakes"/"How it tells you") plus a third,
        # one-card supersection introducing the Poll card ("When you
        # can't wait") — Device now renders three section-intro headings
        # too, in that locked order. The Display half of this check is
        # untouched; only the Device assertion is retargeted, from
        # "absent" to "present, exactly three, in order".
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        if display.count("section-intro") != 3:
            return False, "expected exactly three section-intro occurrences on Display, got %d" % display.count("section-intro")
        look_pos = display.find('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        watches_pos = display.find('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID)
        on_pos = display.find('id="%s"' % config_page.DISPLAY_ON_SECTION_ID)
        if -1 in (look_pos, watches_pos, on_pos):
            return False, "expected all three supersection heading ids to be present"
        if not (look_pos < watches_pos < on_pos):
            return False, "expected Look < What it watches < When it is on in document order"
        if device.count("section-intro") != 3:
            return False, "expected exactly three section-intro occurrences on Device, got %d" % device.count("section-intro")
        wakes_pos = device.find('id="%s"' % config_page.DEVICE_WAKES_SECTION_ID)
        tells_pos = device.find('id="%s"' % config_page.DEVICE_TELLS_SECTION_ID)
        poll_pos = device.find('id="%s"' % config_page.DEVICE_POLL_SECTION_ID)
        if -1 in (wakes_pos, tells_pos, poll_pos):
            return False, "expected all three Device supersection heading ids to be present"
        if not (wakes_pos < tells_pos < poll_pos):
            return False, "expected When it wakes < How it tells you < When you can't wait in document order"
        return True, ""
    check(
        "the Display scope renders exactly three section-intro headings, in the locked Look/What it "
        "watches/When it is on order, and the Device scope renders exactly three of its own, in the "
        "locked When it wakes/How it tells you/When you can't wait order (D-12, retargeted by "
        "28-04-PLAN.md Task 1/CFG-72 from 'the Device scope renders none')",
        _display_render_carries_three_section_intros_in_locked_order)

    def _every_grouped_card_under_a_display_supersection_carries_nested_class():
        # 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C):
        # Theme, Calendar, Runway, Display and Quiet hours each gain the
        # --nested modifier so their own <h2> renders at the extended
        # .theme-status--nested/.page-section--nested > h2 tier
        # (20-04-PLAN.md Task 1's own CSS selector).
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the floor drops from 5 to
        # 4 — Display's own nested card (theme-status--nested) is retired
        # outright along with display_group() itself, leaving Frame
        # colours/Calendar (page-section--nested) and Runway/Quiet hours
        # (theme-status--nested).
        ctx = {
            "device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        for needle in ("theme-status theme-status--nested", "page-section page-section--nested"):
            if needle not in display:
                return False, "expected %r on the Display scope" % (needle,)
        nested_count = display.count("theme-status--nested") + display.count("page-section--nested")
        if nested_count < 4:
            return False, "expected at least 4 --nested occurrences on Display, got %d" % nested_count
        return True, ""
    check(
        "every grouped card the Display scope renders under one of its three supersections carries "
        "a --nested modifier class (D-12)",
        _every_grouped_card_under_a_display_supersection_carries_nested_class)

    def _display_h2_order_matches_d12_after_calendar_placement_fix():
        # D-12 fix (20-REVIEW.md verification gap): before this fix, the
        # physical <form id="settings-form"> closed right after the
        # Calendar card, which forced Flight colours (a real <form> that
        # cannot nest inside another <form>) to render after "What it
        # watches" instead of between Theme and Calendar. This pins the
        # exact <h2> order the fix restores, and that Calendar's compact
        # chip-grid radios still post through the physical form despite
        # the card itself no longer being a literal descendant of it.
        ctx = {
            "device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        headings = re.findall(r'<h2[^>]*>(.*?)</h2>', display)
        # 21-05-PLAN.md Task 1 (D-06): Theme's own <h2> and the standalone
        # Flight-colours card's own <h2> (RULES_SECTION_HEADING) are both
        # retired — replaced by a single "Frame colours" <h2>, the Frame
        # colours card's own heading (its rules panel is named by its own
        # <legend>, never a second <h2>).
        expected = [
            # 21-04-PLAN.md Task 1 (D-01/D-02): the shared Frame strip's
            # own <h2> is now the very first heading on the page,
            # before "Look" — it renders outside <form id="settings-
            # form"> entirely, immediately after the page header.
            layout.FRAME_STRIP_HEADING,
            config_page.DISPLAY_LOOK_HEADING, config_page.FRAME_COLOURS_HEADING,
            config_page.CALENDAR_SECTION_HEADING, config_page.DISPLAY_WATCHES_HEADING,
            "Runway", config_page.DISPLAY_ON_HEADING,
            # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): config_page.
            # DISPLAY_SECTION_HEADING ("Screen on / off") is retired
            # outright along with display_group() — the Frame strip is
            # the only Screen on/off control left, so "When it is on" now
            # renders only the Quiet hours card.
            config_page.QUIET_HOURS_SECTION_HEADING,
        ]
        if headings != expected:
            return False, "expected <h2> order %r, got %r" % (expected, headings)
        calendar_radio_count = display.count('name="calendar_theme_id"')
        calendar_radio_with_form_count = len(
            re.findall(r'name="calendar_theme_id"[^>]*form="%s"' % config_page.SETTINGS_FORM_ID, display))
        if calendar_radio_count == 0 or calendar_radio_with_form_count != calendar_radio_count:
            return False, (
                "expected every one of the %d calendar_theme_id radios to carry form=\"%s\", got %d"
                % (calendar_radio_count, config_page.SETTINGS_FORM_ID, calendar_radio_with_form_count))
        return True, ""
    check(
        "the Display scope's rendered <h2> order is exactly Look, Frame colours, Calendar, What it "
        "watches, Runway, When it is on, Quiet hours (Theme's and the standalone Flight-colours "
        "card's own former headings both retired into one Frame colours heading, 21-05-PLAN.md "
        "Task 1 D-06; Screen on/off's own heading retired outright by 22-05-PLAN.md Task 1 "
        "X1/D-04/D-12.1), and every calendar_theme_id radio carries a form=\"settings-form\" "
        "attribute (D-12 fix, 20-REVIEW.md verification gap)",
        _display_h2_order_matches_d12_after_calendar_placement_fix)

    # ==================================================================
    # 27-06-PLAN.md Task 1 (CFG-65): the title-form inventory, RUN
    # before any markup choice. 27-RESEARCH.md's own grep produced a
    # provisional 8/3/2 split and said so ("the regex matches a
    # formatting convention, not a grammar"); 27-01-SUMMARY.md's browser
    # inventory measured the real rendered split at 7/3/2 and named the
    # eighth grep hit config_page.py never renders on either settings
    # route. This check reproduces that inventory server-side (against
    # config_page.render() directly, no browser needed) and classifies
    # every one of the 12 instances by NAME, not just by count:
    #
    #   7 SETTINGS-CARD titles (form A, `[data-dirty-section] > h2`):
    #   Frame colours/Calendar/Runway/Quiet hours (Display) and
    #   Diagnostic LED/Wake interval/Notifications (Device) — each is
    #   the FIRST thing inside its own bordered tile.
    #
    #   3 SUPERSECTION intros (form B, `.section-intro > h2`,
    #   layout.section_intro_html() — SHARED, byte-identical, with
    #   health_page.py, whose own structural checks match its markup
    #   literally): Look/What it watches/When it is on. These are a
    #   different, unbordered, generically-worded object — "Look" alone
    #   introduces TWO cards (Frame colours and Calendar, render()'s own
    #   5029/5183 ordering), which a card title, naming exactly one
    #   card, cannot do.
    #
    #   2 UNCLASSIFIED headings that are neither: the Frame strip's own
    #   live-status heading (layout.frame_strip_html(), Display only —
    #   an unrelated preview widget, not a settings group) and the Poll
    #   card's own bare `<section class="page-section">` heading
    #   (config_page.py's poll_trigger_section() wrapper, Device only —
    #   it carries no [data-dirty-section] attribute only because it
    #   holds no persisted field for dirty-tracking to watch; its ROLE
    #   — one heading, first thing inside its own box, naming exactly
    #   the one card it belongs to — is otherwise identical to form A).
    #
    # CONCLUSION (stated here, before any markup is touched): Outcome 2.
    # There is already exactly one title form for settings CARDS. The
    # 7-vs-3 split is a real grammar distinction — supersection intro
    # versus card title — not an inconsistency to convert away, and
    # converting it either direction would mean either editing the
    # shared, Health-pinned section_intro_html() call sites away from
    # their documented "must never drift" shape, or reversing
    # 20-07-PLAN.md's own D-12 supersection restructure (still pinned by
    # the two checks immediately above this one). See 27-06-SUMMARY.md
    # for the full substitute-cause investigation (heading SIZE, the
    # spacing above a supersection's first card, and caption-as-title
    # were each measured and found to be either a developer-confirmed,
    # three-round-trip-validated decision this plan does not reopen, or
    # a convention shared identically with Health, or unsupported by
    # measurement).
    #
    # SUPERSEDED IN PART (28-04-PLAN.md Task 1, CFG-72). Outcome 2's own
    # conclusion — "one title form for settings CARDS" — is not
    # reversed here, it is EXTENDED: the developer's second, rendered-
    # and-measured report (the second "Ok mais visuellement les titres
    # sont toujours incohérents !") found that Device's own four cards
    # (including the Poll card this banner already discussed) rendered
    # at the un-nested 22px/400/serif tier while Display's rendered at
    # the nested 16px/600/sans tier — a real defect this banner's own
    # "markup-level" inventory could not see, because it counted
    # elements rather than reading computed style (see 28-04-SUMMARY.md
    # for the rendered-and-measured proof). Device's counts move from
    # (4, 3, 0, 1) to (7, 3, 3, 1): it gains three supersection intros
    # of its own ("When it wakes"/"How it tells you"/"When you can't
    # wait", `_device_groups_html()`), mirroring Display's three. The
    # Poll card's own bare heading — this banner's second UNCLASSIFIED
    # instance — is NOW WRAPPED with `page-section--nested` under its
    # own "When you can't wait" supersection, so it is no longer
    # typographically distinct from the other three Device cards. It
    # STAYS the check's one remaining unclassified instance below,
    # UNCHANGED reason: this check's own [data-dirty-section]-based
    # arithmetic classifies it "unclassified" only because it holds no
    # persisted field for dirty-tracking to watch — exactly what this
    # banner already said above, and exactly why wrapping it was
    # correct rather than a second, competing title form.
    # ==================================================================

    def _title_form_inventory_classifies_every_h2_text_heading_on_both_routes():
        ctx_display = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "calendar_configured": True, "calendar_last_synced_at": None,
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        }
        ctx_device = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 5,
        }
        display = config_page.render(ctx_display, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx_device, scope=config_page.SCOPE_DEVICE)

        counts = {}
        for label, rendered in (("display", display), ("device", device)):
            total = rendered.count('class="text-heading"')
            form_a = rendered.count('%s="' % config_page.DIRTY_SECTION_ATTR)
            form_b = rendered.count("section-intro")
            counts[label] = (total, form_a, form_b, total - form_a - form_b)
        # RE-DERIVED BY RUNNING (28-04-PLAN.md Task 1, CFG-72): Device's
        # own tuple moved from (4, 3, 0, 1) to (7, 3, 3, 1) — three new
        # h2.text-heading instances (the "When it wakes"/"How it tells
        # you"/"When you can't wait" supersection intros), form-A
        # unmoved at 3 (the wrap adds a class, not a [data-dirty-
        # section] attribute), form-B 0 -> 3, unclassified unmoved at 1
        # (the Poll card's own bare heading — see the banner above).
        # Display's own tuple is untouched by this task.
        expected = {"display": (8, 4, 3, 1), "device": (7, 3, 3, 1)}
        if counts != expected:
            return False, (
                "expected {route: (total h2.text-heading, form-A card titles, form-B "
                "supersection intros, unclassified)} == %r, measured %r by running. This is "
                "27-01-SUMMARY.md's own browser-driven inventory (7/3/2 total, corrected from "
                "27-RESEARCH.md's provisional 8/3/2), reproduced server-side — a drift here "
                "means the classification this check names below is stale" % (expected, counts))

        card_title_headings = {
            "display": (
                config_page.FRAME_COLOURS_HEADING, config_page.CALENDAR_SECTION_HEADING,
                "Runway", config_page.QUIET_HOURS_SECTION_HEADING),
            "device": (
                config_page.LED_SECTION_HEADING, config_page.WAKE_INTERVAL_SECTION_HEADING,
                config_page.NOTIFICATIONS_SECTION_HEADING),
        }
        for route, rendered in (("display", display), ("device", device)):
            for heading in card_title_headings[route]:
                needle = ">%s</h2>" % escape_html(heading)
                if needle not in rendered:
                    return False, (
                        "expected the settings-card heading %r to render inside its own "
                        "[data-dirty-section] tile on the %s scope, and it did not"
                        % (heading, route))

        # The two unclassified instances, identified by name — neither
        # is a settings card or a supersection intro.
        frame_strip_needle = ">%s</h2>" % escape_html(layout.FRAME_STRIP_HEADING)
        if frame_strip_needle not in display or frame_strip_needle in device:
            return False, (
                "expected the Frame strip's own <h2> (Display's unclassified instance) to "
                "render on Display and never on Device")
        # 28-04-PLAN.md Task 1 (CFG-72): the Poll card's own bare <h2> is
        # now inside a `page-section page-section--nested` wrapper (it
        # was a bare `page-section` before), but the <h2> TEXT itself is
        # untouched — same needle, still present on Device only.
        poll_needle = '<h2 class="text-heading">%s</h2>' % escape_html(
            config_page.POLL_SECTION_HEADING)
        if poll_needle not in device or poll_needle in display:
            return False, (
                "expected Poll's own <h2> (Device's unclassified instance) to render on Device "
                "and never on Display (Display never renders Poll)")

        # OUTCOME 2: the two label vocabularies never overlap. A
        # supersection's own text is always a GENERIC group label,
        # never one of the 7 cards' own SPECIFIC names. 28-04-PLAN.md
        # Task 1 (CFG-72) widens the supersection-label side with
        # Device's own three new labels.
        overlap = (
            set(card_title_headings["display"]) | set(card_title_headings["device"])
        ) & {
            config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
            config_page.DISPLAY_ON_HEADING, config_page.DEVICE_WAKES_HEADING,
            config_page.DEVICE_TELLS_HEADING, config_page.DEVICE_POLL_HEADING,
        }
        if overlap:
            return False, (
                "expected the settings-card vocabulary and the supersection-label vocabulary "
                "to share no text — found %r in both, which would mean a card's own identity "
                "and a group's own label had collapsed into the same word" % (overlap,))
        return True, ""
    check(
        "the title-form inventory, run before any markup choice: both settings routes' "
        "h2.text-heading instances count and classify as 7 settings-card titles (form A, 3 on "
        "Device + 4 on Display) + 3 supersection intros (form B, layout.section_intro_html(), "
        "shared with health_page.py) + 2 unrelated headings (the Frame strip's own live-status "
        "heading on Display, Poll's own bare-<section> heading on Device — neither a settings "
        "card nor a supersection), reproducing 27-01-SUMMARY.md's corrected 7/3/2 browser count "
        "server-side, with the two label vocabularies never overlapping (CFG-65, 27-06-PLAN.md "
        "Task 1). SUPERSEDED IN PART (28-04-PLAN.md Task 1, CFG-72): a rendered-and-measured "
        "check (companion/test_browser_ux.py) found the 7 settings-card titles were NOT one "
        "typographic form after all — Device's four rendered 22px/400/serif against Display's "
        "16px/600/sans — so Device now gains 3 supersection intros of its own (form B unmoved "
        "in shape, Device's own count 0 -> 3, counts re-derived by running below) and its own "
        "Poll card is wrapped, closing that gap; the settings-card/supersection-label GRAMMAR "
        "distinction this check's own name asserts is unchanged, and the label-vocabulary "
        "overlap clause now also covers Device's three new labels",
        _title_form_inventory_classifies_every_h2_text_heading_on_both_routes)

    # ==================================================================
    # 27-06-PLAN.md Task 2 (CFG-65): Task 1 concluded Outcome 2 — there
    # is already one title form for settings cards, so there is no
    # conversion to make (converting either direction would edit the
    # shared, Health-pinned section_intro_html() call sites, or reverse
    # 20-07-PLAN.md's own D-12 supersection restructure — both out of
    # this plan's scope, per its own "form B is not editable" and "pick
    # based on what costs less disruption" constraints). No markup or
    # CSS changed for the title-form correction.
    #
    # In its place: the structural guarantee that keeps "one title form
    # for cards" true GOING FORWARD, not just in today's markup. Every
    # one of the 7 functions that builds a settings card's own tile
    # returns its own <h2> (form A) as a fixed, flat string and never
    # reaches for the shared supersection builder to do it — asserted
    # here at the SOURCE level via AST, so the "losing form" this check
    # names (a card's own heading produced through the supersection-
    # intro shape) is ZERO, enforced independently of whatever the
    # rendered markup happens to look like on any given day.
    # ==================================================================

    def _no_card_builder_function_ever_calls_section_intro_html():
        card_builder_names = (
            "_frame_colours_card_html", "runway_fieldset", "led_group",
            "quiet_hours_group", "wake_interval_group", "notifications_group",
            "calendar_group",
        )
        with open(os.path.join(HERE, "pages", "config_page.py")) as fh:
            source = fh.read()
        tree = ast.parse(source)
        found_names = {
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name in card_builder_names}
        if found_names != set(card_builder_names):
            return False, (
                "expected to find all 7 card-builder functions by name in config_page.py, "
                "missing %r — this check's own allowlist is stale"
                % (set(card_builder_names) - found_names,))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in card_builder_names:
                for call in ast.walk(node):
                    if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                            and call.func.attr == "section_intro_html"):
                        offenders.append(node.name)
        if offenders:
            return False, (
                "expected ZERO of the 7 settings-card builder functions to call "
                "layout.section_intro_html() (form B) for their own <h2> — found it called "
                "from %r. A card's own title must stay form A, never borrow the shared "
                "supersection builder" % (offenders,))
        return True, ""
    check(
        "none of the 7 settings-card builder functions (_frame_colours_card_html/"
        "runway_fieldset/led_group/quiet_hours_group/wake_interval_group/notifications_group/"
        "calendar_group) ever calls layout.section_intro_html() for their own heading — the "
        "losing form (a card title produced through the supersection-intro shape) is ZERO, "
        "enforced at the source level rather than only in today's rendered markup (CFG-65, "
        "27-06-PLAN.md Task 2 — Outcome 2, no conversion, see 27-06-SUMMARY.md)",
        _no_card_builder_function_ever_calls_section_intro_html)

    # ==================================================================
    # 28-04-PLAN.md Task 2 (CFG-72): the cheap structural guard. THIS IS
    # NOT THE PROOF — companion/test_browser_ux.py's cross-page
    # getComputedStyle comparator is, and that is stated here rather
    # than left implicit, so nobody later mistakes this check for a
    # substitute (that exact mistake is how 27-06 shipped in the first
    # place). This only asserts that the Device scope's rendered markup
    # wraps every one of its four settings cards with the --nested
    # modifier and that zero unmodified settings-card wrappers of either
    # base class survive on that page.
    # ==================================================================

    def _device_scope_wraps_all_four_settings_cards_with_the_nested_modifier():
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        nested_theme_status = device.count('class="theme-status theme-status--nested"')
        if nested_theme_status != 3:
            return False, (
                "expected exactly 3 theme-status--nested settings-card wrappers on Device "
                "(LED, wake interval, notifications), got %d" % nested_theme_status)
        nested_page_section = device.count('class="page-section page-section--nested"')
        if nested_page_section != 1:
            return False, (
                "expected exactly 1 page-section--nested settings-card wrapper on Device "
                "(Poll), got %d" % nested_page_section)
        bare_theme_status = device.count('class="theme-status"')
        if bare_theme_status != 0:
            return False, (
                "expected zero unmodified .theme-status settings-card wrappers on Device, "
                "got %d" % bare_theme_status)
        bare_page_section = device.count('class="page-section"')
        if bare_page_section != 0:
            return False, (
                "expected zero unmodified .page-section settings-card wrappers on Device, "
                "got %d" % bare_page_section)
        return True, ""
    check(
        "the cheap structural guard, NOT the real proof (that is test_browser_ux.py's "
        "cross-page getComputedStyle comparator): the Device scope's rendered output wraps "
        "all four of its settings cards with the --nested modifier (three "
        "theme-status--nested, one page-section--nested) and carries zero unmodified "
        "settings-card wrappers of either base class (CFG-72, 28-04-PLAN.md Task 2)",
        _device_scope_wraps_all_four_settings_cards_with_the_nested_modifier)

    # ==================================================================
    # 20-07-PLAN.md Task 2 (D-19/Pitfall 1): the instant switches, and
    # the form restructure that makes them valid HTML.
    # ==================================================================

    _TASK2_BASE_CTX = {
        "device_config": {
            "display_enabled": True, "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        },
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
    }

    def _display_render_carries_exactly_two_quick_action_forms():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        if rendered.count('action="%s"' % config_page.QUICK_DISPLAY_ROUTE) != 1:
            return False, "expected exactly one action=\"/quick/display\" form"
        if rendered.count('action="%s"' % config_page.QUICK_QUIET_HOURS_ROUTE) != 1:
            return False, "expected exactly one action=\"/quick/quiet-hours\" form"
        return True, ""
    check(
        "a Display render contains exactly one action=\"/quick/display\" form and one "
        "action=\"/quick/quiet-hours\" form (D-19)",
        _display_render_carries_exactly_two_quick_action_forms)

    def _quick_action_forms_are_not_descendants_of_settings_form():
        # 21-04-PLAN.md Task 1 (D-01/D-02): retargeted — both instant-
        # switch forms now render inside the shared Frame strip, BEFORE
        # the settings form even opens, not after it closes.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        settings_form_open = rendered.index('<form class="config-form"')
        for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
            quick_form_pos = rendered.index('action="%s"' % route)
            if quick_form_pos >= settings_form_open:
                return False, (
                    "expected the %s instant-switch form to appear in the Frame strip, "
                    "before the settings form even opens, not nested inside it" % route)
        return True, ""
    check(
        "neither instant-switch form is a descendant of <form id=settings-form> — both render in "
        "the shared Frame strip, before the settings form even opens (D-01/D-02/Pitfall 1)",
        _quick_action_forms_are_not_descendants_of_settings_form)

    def _display_render_carries_no_form_nested_inside_a_form():
        # The pinned regression test for Pitfall 1: a whole-body scan
        # for any "<form" whose nearest preceding unclosed "<form" has
        # not yet been closed — i.e. no <form> is ever a descendant of
        # another <form> anywhere in the rendered Display page.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        depth = 0
        pos = 0
        while True:
            open_pos = rendered.find("<form", pos)
            close_pos = rendered.find("</form>", pos)
            if open_pos == -1 and close_pos == -1:
                break
            if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                if depth >= 1:
                    return False, (
                        "expected no <form> nested inside another <form>, found one "
                        "opening at offset %d" % open_pos)
                depth += 1
                pos = open_pos + len("<form")
            else:
                depth -= 1
                pos = close_pos + len("</form>")
        if depth != 0:
            return False, "expected every <form> to be closed, got an unbalanced depth of %d" % depth
        return True, ""
    check(
        "the rendered Display page contains no <form> nested inside another <form> anywhere "
        "(D-19/Pitfall 1, the required structural fix)",
        _display_render_carries_no_form_nested_inside_a_form)

    def _two_scheduled_inputs_carry_form_settings_form():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): retargeted from four
        # scheduled inputs to two — the display_enabled and
        # quiet_hours_enabled checkboxes this check used to pin are
        # retired outright, along with display_group() and
        # quiet_hours_group()'s own on/off checkbox. Only the Quiet
        # hours schedule itself (Start/End) still cross-submits via
        # form="settings-form" now.
        # 22-10-PLAN.md Task 2 (B14): retargeted again, in place — each
        # time input now also carries `lang` (the site language) between
        # `required` and `form=`. The form= contract this check exists
        # for is unchanged; only the literal it greps had to absorb the
        # new attribute.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for needle in (
                '<input type="time" name="quiet_hours_start" value="22:00" required'
                ' lang="en" form="settings-form"',
                '<input type="time" name="quiet_hours_end" value="06:00" required'
                ' lang="en" form="settings-form"'):
            if needle not in rendered:
                return False, "expected %r in the rendered Display page" % (needle,)
        if 'name="display_enabled"' in rendered or 'name="quiet_hours_enabled"' in rendered:
            return False, "expected no display_enabled/quiet_hours_enabled input on the Display page"
        return True, ""
    # ==================================================================
    # 21-04-PLAN.md Task 1 (D-01/D-02): the Frame strip replaces the two
    # cards' own instant switches — one .quick-action--on/--off pair,
    # inside .frame-strip; neither schedule card carries any
    # quick-action markup any more; each switch's return_to hidden
    # field carries the Display route; the strip sits right after the
    # page header, before the first .section-intro.
    # ==================================================================

    def _display_render_has_exactly_one_quick_action_pair_inside_the_strip():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        on_off_count = (
            rendered.count('quick-action quick-action--on')
            + rendered.count('quick-action quick-action--off'))
        if on_off_count != 2:
            return False, "expected exactly two .quick-action--on/--off cells (Screen + Quiet hours), got %d" % (
                on_off_count,)
        strip_start = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
        strip_end = rendered.index('<form class="config-form"', strip_start)
        strip_segment = rendered[strip_start:strip_end]
        if (
            strip_segment.count('quick-action quick-action--on')
            + strip_segment.count('quick-action quick-action--off') != 2
        ):
            return False, "expected both quick-action cells to sit inside .frame-strip"
        return True, ""
    check(
        "a Display render carries exactly one .quick-action--on/--off pair per switch, both inside "
        ".frame-strip (D-01/D-02)",
        _display_render_has_exactly_one_quick_action_pair_inside_the_strip)

    def _schedule_cards_carry_no_quick_action_markup():
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): retargeted to Quiet hours
        # only — the Screen on/off card this loop used to also check is
        # retired outright along with display_group() itself, so there is
        # no longer a second card to check here.
        # 27-08-PLAN.md Task 1 (CFG-69): the literal absorbs the heading's
        # new id="{QUIET_HOURS_GROUP_HEADING_ID}" — the quick-action
        # contract this check exists for is unchanged; only the markup it
        # greps had to grow the new attribute.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for heading in (config_page.QUIET_HOURS_SECTION_HEADING,):
            start = rendered.index(
                '<h2 class="text-heading" id="%s">%s</h2>'
                % (config_page.QUIET_HOURS_GROUP_HEADING_ID, heading))
            next_heading = rendered.find('<h2 class="text-heading"', start + 1)
            segment = rendered[start:next_heading] if next_heading != -1 else rendered[start:]
            if "quick-action" in segment:
                return False, "expected the %r card to carry no quick-action markup" % (heading,)
        return True, ""
    check(
        "the Quiet hours card carries no quick-action markup any more — its switch moved into the "
        "shared Frame strip (D-01/D-02); the Screen on/off card this check used to also cover is "
        "retired outright by 22-05-PLAN.md Task 1 (X1/D-04/D-12.1)",
        _schedule_cards_carry_no_quick_action_markup)

    def _quick_action_forms_carry_return_to_the_display_route():
        # A DIFFERENT, pre-existing "return_to" hidden field also lives
        # inside <form id="settings-form"> itself (_scope_fields_html(),
        # D-10's own scope-aware save-and-return-to-the-same-page
        # mechanism) — same field NAME, different form, different
        # route, no collision in what either POST body actually
        # carries. Scoped to each quick-action <form>...</form> block
        # specifically, not a whole-page substring count, so this check
        # cannot be confused by that unrelated field.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        needle = '<input type="hidden" name="return_to" value="%s">' % layout.DISPLAY_ROUTE
        for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
            form_start = rendered.index('action="%s"' % route)
            form_end = rendered.index("</form>", form_start)
            if needle not in rendered[form_start:form_end]:
                return False, "expected %r inside the %s form" % (needle, route)
        return True, ""
    check(
        "both instant-switch forms on Display carry a return_to hidden input whose value is the "
        "Display route (R-02)",
        _quick_action_forms_carry_return_to_the_display_route)

    def _frame_strip_renders_after_header_before_first_section_intro():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        header_pos = rendered.index('<h1 class="page-title">')
        strip_pos = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
        intro_pos = rendered.index('class="section-intro"')
        if not (header_pos < strip_pos < intro_pos):
            return False, (
                "expected the page header, then the Frame strip, then the first "
                "section-intro, got positions %d, %d, %d" % (header_pos, strip_pos, intro_pos))
        return True, ""
    check(
        "the Frame strip renders immediately after the page header and before the first "
        "section-intro on Display (D-02)",
        _frame_strip_renders_after_header_before_first_section_intro)

    check(
        "the two remaining scheduled inputs (quiet_hours_start, quiet_hours_end) carry "
        "form=\"settings-form\" via the SETTINGS_FORM_ID constant (D-19), and neither "
        "display_enabled nor quiet_hours_enabled renders on the Display page any more "
        "(22-05-PLAN.md Task 1, X1/D-04/D-12.1)",
        _two_scheduled_inputs_carry_form_settings_form)

    def _applies_next_wake_sentence_appears_exactly_three_times():
        # 21-04-PLAN.md Task 1 (D-01/D-02): the constant moved to
        # companion/layout.py along with the switch markup it captions.
        # 22-05-PLAN.md Task 2 (D-04): retargeted from "exactly twice" to
        # "exactly three times" — layout.QUICK_ACTION_APPLIES_SENTENCE is
        # byte-identical to frame_state.DELAY_UNKNOWN (22-04-PLAN.md's own
        # alias), and _TASK2_BASE_CTX carries no last_checkin_ts, so
        # frame_state resolves STATE_UNKNOWN/DELAY_UNKNOWN for the Quiet
        # hours caption's own computed delay sentence too — a THIRD,
        # genuinely independent consumer of the same translated text, not
        # a widened count for the same two switches.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        count = rendered.count(escape_html(layout.QUICK_ACTION_APPLIES_SENTENCE))
        if count != 3:
            return False, (
                "expected the shared instant-switch/delay sentence to appear exactly three times, "
                "got %d" % count)
        return True, ""
    check(
        "the shared \"Applies the next time the frame wakes up.\" sentence appears exactly three "
        "times on the Display page — once per instant switch, plus once as the Quiet hours card's "
        "own computed delay sentence when no check-in data exists yet (D-19, 22-05-PLAN.md Task 2 "
        "D-04)",
        _applies_next_wake_sentence_appears_exactly_three_times)

    def _handle_post_same_field_set_after_restructure_saves_the_same_config():
        # D-13: only the DOM position of display_group()/quiet_hours_
        # group() changed — handle_post()'s own field set and its
        # absent-checkbox carry-forward are untouched, so a POST with
        # the same field set as before this task still saves identically.
        tmp = tempfile.mkdtemp(prefix="skypane-config-task2-")
        try:
            key = config_page.handle_post(
                {
                    "scope": "display", "theme": "black", "display_enabled": "on",
                    "quiet_hours_enabled": "on", "quiet_hours_start": "23:00",
                    "quiet_hours_end": "07:00",
                },
                {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (key,)
            cfg = device_config.load_device_config(tmp)
            if (
                cfg["theme"] != "black" or cfg["display_enabled"] is not True
                or cfg["quiet_hours_enabled"] is not True
                or cfg["quiet_hours_start"] != "23:00" or cfg["quiet_hours_end"] != "07:00"
            ):
                return False, "expected the same field set to persist identically, got %r" % (cfg,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a POST through handle_post() with the same field set as before the Task 2 restructure "
        "still produces the same saved config (D-13/T-20-26)",
        _handle_post_same_field_set_after_restructure_saves_the_same_config)

    # ==================================================================
    # 20-07-PLAN.md Task 3 (D-05): config_page.py through t(), and its
    # French catalogue (companion/i18n_fr/display.py).
    # ==================================================================

    _TASK3_I18N_CTX = {
        "device_config": {
            "display_enabled": True, "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        },
        "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        "calendar_configured": True, "calendar_last_synced_at": None,
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    }

    def _french_display_render_carries_french_headings_no_english():
        try:
            prefs.set_request_prefs(lang="fr")
            fr_rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        for french_text in ("Aspect", "Ce qu’il surveille", "Quand il est allumé",
                             "Tout ce que le cadre affiche, et quand.",
                             "S’applique au prochain réveil du cadre."):
            if french_text not in fr_rendered:
                return False, "expected %r in the French Display render" % (french_text,)
        for english_text in ("Look", "What it watches", "When it is on",
                              "Everything about what the frame shows and when.",
                              "Applies the next time the frame wakes up."):
            if english_text in fr_rendered:
                return False, "expected %r to be absent from the French Display render" % (english_text,)
        return True, ""
    check(
        "a French Display render (prefs.set_request_prefs(lang='fr')) carries the three "
        "supersection headings, the purpose sentence and the instant-switch sentence in French, "
        "and none of their English counterparts (D-05)",
        _french_display_render_carries_french_headings_no_english)

    def _french_display_and_device_render_translate_registry_labels():
        # Polish fix 5 (D-05): device_config.theme_label()/runway_
        # label()'s registry text and screens.py's screen label are
        # translated at their config_page.py display sites via
        # i18n.t(), backed by companion/i18n_fr/registry.py — the
        # default theme ("white" -> "White"/"Blanc") and default
        # runway ("3" -> "Runway 3 (07/25)"/"Piste 3 (07/25)") both
        # apply here since _TASK3_I18N_CTX's device_config carries
        # neither key. The ids themselves ("white", "3") are never
        # translated, so they must still appear as attribute values.
        try:
            prefs.set_request_prefs(lang="fr")
            fr_display = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
            fr_device = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DEVICE)
        finally:
            prefs.set_request_prefs(lang="en")
        for french_text in ("Blanc", "Piste 3 (07/25)", "Cadre avion"):
            if french_text not in fr_display:
                return False, "expected the French %r in the French Display render" % (french_text,)
        if "Cadre avion" not in fr_device:
            return False, "expected the French screen label in the French Device render"
        for english_text in ("Runway 3 (07/25)",):
            if english_text in fr_display:
                return False, "expected %r to be absent from the French Display render" % (english_text,)
        if 'value="white"' not in fr_display or 'value="3"' not in fr_display:
            return False, "expected the theme/runway ids themselves to stay untranslated attribute values"
        return True, ""
    check(
        "a French Display render translates the default theme name ('White' -> 'Blanc') and "
        "default runway label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), and both scopes' screen "
        "caption translates 'Plane frame' -> 'Cadre avion', while the theme/runway ids stay "
        "untranslated attribute values (Polish fix 5, D-05)",
        _french_display_and_device_render_translate_registry_labels)

    def _english_display_render_still_carries_every_pinned_english_string():
        # The default (no prefs override) render must stay byte-identical
        # to every pre-existing English-language check in this file —
        # t()'s own fallback-to-English-unchanged contract, exercised at
        # the whole-page level rather than per-string.
        rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
        for english_text in (
                config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
                config_page.DISPLAY_ON_HEADING, config_page.DISPLAY_PAGE_PURPOSE,
                layout.QUICK_ACTION_APPLIES_SENTENCE, config_page.FRAME_COLOURS_CAPTION,
                config_page.RUNWAY_SECTION_CAPTION, config_page.CALENDAR_CAPTION):
            if escape_html(english_text) not in rendered:
                return False, "expected the English constant %r to still render verbatim" % (english_text,)
        return True, ""
    check(
        "an English (default) Display render still contains every pre-existing English string this "
        "file's own checks assert — t() never touches the default-language render (D-05)",
        _english_display_render_still_carries_every_pinned_english_string)

    def _device_render_carries_no_edit_artwork_markup_in_either_language():
        for lang in ("en", "fr"):
            try:
                prefs.set_request_prefs(lang=lang)
                rendered = config_page.render(
                    {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0},
                    scope=config_page.SCOPE_DEVICE)
            finally:
                prefs.set_request_prefs(lang="en")
            if "edit-artwork" in rendered:
                return False, "lang=%r: expected no edit-artwork markup on the Device page (D-36)" % (lang,)
            if "?edit=1" in rendered:
                return False, "lang=%r: expected no ?edit=1 link on the Device page (D-36)" % (lang,)
        return True, ""
    check(
        "the Device render contains no edit-artwork markup and no ?edit=1 link, in either language "
        "(D-36)",
        _device_render_carries_no_edit_artwork_markup_in_either_language)

    def _every_display_catalogue_key_is_a_key_of_the_merged_catalog():
        missing = [key for key in i18n_fr_display.CATALOG if key not in i18n_fr.CATALOG]
        if missing:
            return False, "expected every companion/i18n_fr/display.py key in the merged CATALOG, missing %r" % (missing,)
        return True, ""
    check(
        "every key of companion/i18n_fr/display.py is a key of the merged companion.i18n_fr.CATALOG "
        "(the auto-merge package actually picked this module up)",
        _every_display_catalogue_key_is_a_key_of_the_merged_catalog)

    def _submitted_scope_and_return_route_are_allowlisted():
        if config_page.submitted_scope({}) != config_page.SCOPE_ALL:
            return False, "expected a form without a scope field to resolve to the legacy all-scope"
        if config_page.submitted_scope({"scope": "device"}) != config_page.SCOPE_DEVICE:
            return False, "expected scope=device to resolve to SCOPE_DEVICE"
        if config_page.submitted_scope({"scope": "<script>"}) != config_page.SCOPE_ALL:
            return False, "expected a crafted scope to degrade to the all-scope, never be echoed"
        if config_page.submitted_return_route({"return_to": "/device"}) != "/device":
            return False, "expected /device to be an allowed return route"
        for hostile in ("https://evil.example", "//evil.example", "/settings", "/login", ""):
            if config_page.submitted_return_route({"return_to": hostile}) != "/display":
                return False, "expected %r to fall back to /display" % hostile
        return True, ""
    check(
        "submitted_scope() and submitted_return_route() are strict allowlists: unknown scopes degrade "
        "to the legacy all-scope and any non-member return_to falls back to /display",
        _submitted_scope_and_return_route_are_allowlisted)

    def _scoped_render_carries_hidden_fields_and_omits_other_groups():
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        legacy = config_page.render(ctx)
        if 'name="scope" value="display"' not in display or 'name="return_to" value="/display"' not in display:
            return False, "expected the display scope's hidden scope/return_to fields"
        if 'name="scope" value="device"' not in device or 'name="return_to" value="/device"' not in device:
            return False, "expected the device scope's hidden scope/return_to fields"
        if 'name="scope"' in legacy:
            return False, "expected the legacy all-scope render to carry no scope field"
        # 20-07-PLAN.md Task 1 (D-10): Runway moved from Device's
        # advanced_groups to Display's everyday_groups this phase — LED
        # stays Device-only, unaffected.
        if 'name="led_enabled"' in display:
            return False, "expected no LED group on the Display page"
        if 'name="tracked_runway"' not in display:
            return False, "expected the runway group to render on the Display page (D-10)"
        if 'name="tracked_runway"' in device:
            return False, "expected no runway group on the Device page (D-10)"
        # 21-05-PLAN.md Task 1 (D-06): theme_arriving_enabled is retired
        # outright — "quiet_hours_enabled"-in-device is the surviving
        # half of this assertion's own original premise.
        if 'name="quiet_hours_enabled"' in device:
            return False, "expected no quiet-hours group on the Device page"
        if display.count('<h1 class="page-title">Display</h1>') != 1:
            return False, "expected the Display page title"
        if device.count('<h1 class="page-title">Device</h1>') != 1:
            return False, "expected the Device page title"
        # 20-07-PLAN.md Task 1 (D-11): Flight colours (the rules editor)
        # moved from Device to Display with its Calendar group — Manual
        # refresh (the Poll section) stays Device-only, unaffected.
        # 21-05-PLAN.md Task 1 (D-06/D-10): the rules editor is no longer
        # a standalone section with its own heading — it relocated into
        # the Frame colours card's own "Per-flight rules" usage panel,
        # located here via its own data-usage-panel-target attribute.
        if config_page.POLL_SECTION_HEADING in display:
            return False, "expected the manual-refresh section off the Display page"
        rules_panel_marker = '%s="%s"' % (
            config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, config_page.COLOUR_USAGE_RULES)
        if rules_panel_marker not in display:
            return False, "expected the rules panel, inside the Frame colours card, on the Display page (D-11)"
        if config_page.POLL_SECTION_HEADING not in device:
            return False, "expected the manual-refresh section on the Device page"
        if rules_panel_marker in device:
            return False, "expected the rules panel off the Device page (D-11)"
        hostile = config_page.render(ctx, scope="<script>")
        if 'name="scope"' in hostile or "&lt;script&gt;" in hostile:
            return False, "expected a hostile scope value to degrade to the legacy all-scope, never to be echoed"
        return True, ""
    check(
        "render(scope=display/device) carries the matching hidden fields and only its own groups; the "
        "legacy render(ctx) carries no scope field; a hostile scope never reaches the markup",
        _scoped_render_carries_hidden_fields_and_omits_other_groups)

    def _handle_post_scope_carries_out_of_scope_checkboxes_forward():
        tmp = tempfile.mkdtemp(prefix="skypane-config-scope-")
        try:
            device_config.save_device_config(
                tmp, led_enabled=True, display_enabled=True, quiet_hours_enabled=True,
                theme="white", tracked_runway="3")
            # Display-page save: no LED field on the page -> LED stays True.
            key = config_page.handle_post(
                {"scope": "display", "theme": "black", "display_enabled": "on",
                 "quiet_hours_enabled": "on"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the display-page save, got %r" % key
            cfg = device_config.load_device_config(tmp)
            if cfg["led_enabled"] is not True or cfg["theme"] != "black":
                return False, "expected led_enabled carried forward and theme persisted, got %r" % (cfg,)
            # Device-page save: no display/quiet fields -> both stay True.
            # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25):
            # RETARGETED IN PLACE. This clause used to read "its own
            # absent LED box -> False", which was the correct reading
            # while the Device page still rendered an led_enabled
            # checkbox. It does not any more — the LED's control is a
            # role="switch" posting to /quick/led — so an absent
            # led_enabled here means the same thing display_enabled's
            # absence has meant since 22-05: leave it alone. The LED is
            # seeded True above and must still be True after a Device
            # save that never mentions it; the pre-23-07 handler would
            # have switched the physical LED off on this exact call.
            key = config_page.handle_post(
                {"scope": "device", "tracked_runway": "06-24"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the device-page save, got %r" % key
            cfg = device_config.load_device_config(tmp)
            if cfg["display_enabled"] is not True or cfg["quiet_hours_enabled"] is not True:
                return False, "expected display/quiet-hours carried forward on a device-page save, got %r" % (cfg,)
            if cfg["led_enabled"] is not True or cfg["tracked_runway"] != "06-24":
                return False, (
                    "expected a Device save that names no led_enabled to LEAVE it True and to "
                    "persist its own runway, got %r" % (cfg,))
            # And the explicit value is still honoured, which is what
            # makes the clause above a statement about ABSENCE rather
            # than about led_enabled having stopped being writable here.
            key = config_page.handle_post(
                {"scope": "device", "led_enabled": config_page.LED_CHECKBOX_VALUE},
                {"state_dir": tmp})
            if key != config_page.FLASH_SAVED or device_config.load_device_config(
                    tmp)["led_enabled"] is not True:
                return False, "expected an explicit led_enabled value to still be honoured"
            # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
            # Display's everyday_groups this phase — a device-page
            # submission now ignores even a stray calendar_disconnect
            # field (its own scope no longer renders the Calendar group
            # at all), while a display-page submission's calendar
            # fields are live, resolving per submitted_calendar_signal()'s
            # own per-field gates. Retargeted in place from the exact
            # inverse (pre-phase, Calendar was Device-only).
            if config_page.submitted_calendar_signal({"scope": "device"}) != config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD:
                return False, "expected a device-page submission without calendar fields to carry the calendar forward"
            if config_page.submitted_calendar_signal({"scope": "device", "calendar_disconnect": "on"}) != config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD:
                return False, "expected a device-page submission to ignore a stray calendar_disconnect field (D-11)"
            if config_page.submitted_calendar_signal({"scope": "display", "calendar_disconnect": "on"}) != config_page.CALENDAR_URL_SIGNAL_CLEAR:
                return False, "expected a display-page submission's calendar_disconnect field to resolve clear now that Calendar renders there (D-11)"
            # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1, T-22-16): inverted from
            # the pre-22-05 "the legacy unscoped body keeps its
            # absent-means-False contract" — display_enabled and
            # quiet_hours_enabled now resolve absent to "leave unchanged"
            # UNCONDITIONALLY, including on this legacy unscoped
            # SCOPE_ALL path, which is precisely the regression this
            # plan exists to close: before this fix, this exact call
            # would have silently switched the screen back off.
            key = config_page.handle_post({"theme": "white"}, {"state_dir": tmp})
            cfg = device_config.load_device_config(tmp)
            if key != config_page.FLASH_SAVED or cfg["display_enabled"] is not True:
                return False, (
                    "expected the legacy unscoped save to LEAVE display_enabled unchanged (True), "
                    "got %r" % (cfg["display_enabled"],))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "handle_post() treats a checkbox absent from an out-of-scope group as 'leave unchanged' (a "
        "Display save never flips the LED, a Device save never flips the screen or quiet hours), "
        "leaves display_enabled/quiet_hours_enabled/led_enabled unchanged even in-scope and on the "
        "legacy unscoped form while still honouring an explicit value, and a scoped submission "
        "without the Calendar group always carries the calendar forward (D-12.1, 22-05-PLAN.md "
        "Task 1; the led_enabled half retargeted in place from absent-means-False by "
        "23-07-PLAN.md Task 2)",
        _handle_post_scope_carries_out_of_scope_checkboxes_forward)

    # --- 19-12-PLAN.md Task 2 (D-23/D-22): the conditional screen selector
    # and the Device-page Edit artwork link -------------------------------

    def _screen_selector_empty_for_the_real_single_member_registry():
        html = config_page._screen_selector_html("plane-frame")
        if html != "":
            return False, "expected the empty string for today's single-member registry, got %r" % (html,)
        return True, ""
    check(
        "_screen_selector_html() returns the empty string for the real single-member screens registry",
        _screen_selector_empty_for_the_real_single_member_registry)

    def _screen_selector_renders_for_a_multi_member_registry():
        from companion import screens
        saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
        try:
            screens.SCREEN_TYPES["rer-board"] = {
                "label": "RER board", "description": "d",
                "everyday_groups": (), "advanced_groups": (),
                "has_colour_rules": False, "has_manual_poll": False,
            }
            screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
            html = config_page._screen_selector_html("plane-frame")
            if '<select name="screen_id"' not in html:
                return False, "expected a <select name=\"screen_id\"> once a second screen type is registered"
            if html.count("<option") != 2:
                return False, "expected exactly one <option> per registered screen type, got %r" % (html,)
            if 'value="plane-frame" selected' not in html:
                return False, "expected the current screen id's option to carry the selected attribute"
            if 'value="rer-board" selected' in html:
                return False, "expected only the current screen id's option to carry selected"
            if "<label" not in html or 'for="screen-id-selector"' not in html:
                return False, "expected a <label for=...> supplying the control's accessible name"
            return True, ""
        finally:
            screens.SCREEN_TYPES.clear()
            screens.SCREEN_TYPES.update(saved_types)
            screens.SCREEN_IDS = saved_ids
    check(
        "_screen_selector_html() emits exactly one <select name=\"screen_id\"> with one <option> per "
        "registered screen type, the current one selected, and a non-empty accessible name once a "
        "second screen type is registered",
        _screen_selector_renders_for_a_multi_member_registry)

    def _render_carries_no_screen_selector_today():
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        if '<select name="screen_id"' in display or '<select name="screen_id"' in device:
            return False, "expected no screen selector with today's single-member registry"
        return True, ""
    check(
        "render() at Display and Device scope contains no <select name=\"screen_id\"> today (a "
        "single-member registry has no real choice to offer)",
        _render_carries_no_screen_selector_today)

    def _handle_post_rejects_a_crafted_screen_id():
        tmp = tempfile.mkdtemp(prefix="skypane-config-screen-id-")
        try:
            device_config.save_device_config(tmp, theme="white")
            errors = {}
            key = config_page.handle_post(
                {"theme": "black", "screen_id": "not-a-real-screen"}, {"state_dir": tmp}, errors=errors)
            if key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED for a crafted screen_id, got %r" % (key,)
            if "screen_id" not in errors:
                return False, "expected a field error noted for screen_id"
            cfg = device_config.load_device_config(tmp)
            if cfg["theme"] != "white":
                return False, "expected the whole save rejected — theme must not have changed to 'black'"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "handle_post() rejects a crafted screen_id with FLASH_SAVE_FAILED, notes a field error, and "
        "writes nothing (all-or-nothing)",
        _handle_post_rejects_a_crafted_screen_id)

    def _valid_screen_id_round_trips():
        tmp = tempfile.mkdtemp(prefix="skypane-config-screen-id-")
        try:
            key = config_page.handle_post({"screen_id": "plane-frame"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for a valid screen_id, got %r" % (key,)
            cfg = device_config.load_device_config(tmp)
            if cfg["screen_id"] != "plane-frame":
                return False, "expected screen_id='plane-frame' to round-trip, got %r" % (cfg["screen_id"],)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a valid screen_id round-trips through save_device_config()",
        _valid_screen_id_round_trips)

    def _screen_selector_renders_the_field_error_message():
        # WR-01 (19-REVIEW.md): _screen_selector_html() is the only
        # render call site for screen_id and, unlike every sibling field
        # this plan touches, never rendered its own _field_error_html()
        # message. Only reachable through a multi-member registry, same
        # as the sibling checks above.
        from companion import screens
        saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
        try:
            screens.SCREEN_TYPES["rer-board"] = {
                "label": "RER board", "description": "d",
                "everyday_groups": (), "advanced_groups": (),
                "has_colour_rules": False, "has_manual_poll": False,
            }
            screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
            errors = {"screen_id": config_page.ERROR_INVALID_CHOICE}
            html_out = config_page._screen_selector_html("plane-frame", errors=errors)
            expected = escape_html(config_page.ERROR_INVALID_CHOICE)
            if html_out.count(expected) != 1:
                return False, (
                    "expected the screen_id field-error message to appear exactly once, got %r"
                    % (html_out,))
            return True, ""
        finally:
            screens.SCREEN_TYPES.clear()
            screens.SCREEN_TYPES.update(saved_types)
            screens.SCREEN_IDS = saved_ids
    check(
        "_screen_selector_html() renders the screen_id field-level error message exactly once when "
        "errors carries one",
        _screen_selector_renders_the_field_error_message)

    def _neither_scope_renders_an_edit_artwork_link():
        # 20-07-PLAN.md Task 3 (D-36): the Device page's "Edit artwork"
        # link is deleted outright — retargeted in place from "the
        # Device scope renders exactly one... Display renders none" to
        # its own inverse, now that neither scope renders it at all.
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        href_fragment = "/airlines?edit=1"
        if href_fragment in display:
            return False, "expected no Edit-artwork link on the Display page"
        if href_fragment in device:
            return False, "expected no Edit-artwork link on the Device page (D-36)"
        if "edit-artwork" in display or "edit-artwork" in device:
            return False, "expected no edit-artwork markup on either scope (D-36)"
        if "_edit_artwork_link_html" in dir(config_page):
            return False, "expected _edit_artwork_link_html() to be deleted outright (D-36)"
        return True, ""
    check(
        "neither the Display nor the Device scope renders an Edit-artwork link or markup any more — "
        "the link and its builder are deleted outright (D-36)",
        _neither_scope_renders_an_edit_artwork_link)

    # --- 19-12-PLAN.md Task 3 (D-13/S-02): "next wake ≈ HH:MM" caption
    # suffixes on Display/Device -------------------------------------------

    def _with_next_wake_helper_contract():
        if config_page._with_next_wake("caption.", None) != "caption.":
            return False, "expected the caption unchanged for a falsy next_wake_clock"
        if config_page._with_next_wake("caption.", "") != "caption.":
            return False, "expected the caption unchanged for an empty-string next_wake_clock"
        got = config_page._with_next_wake("caption.", "14:10")
        if got != "caption. (next wake ≈ 14:10)":
            return False, "expected the suffix appended when next_wake_clock is known, got %r" % (got,)
        return True, ""
    check(
        "_with_next_wake() returns the caption byte-identical for a falsy clock and appends "
        "'(next wake ≈ HH:MM)' when the clock is known",
        _with_next_wake_helper_contract)

    def _affected_captions_gain_the_suffix_only_when_known():
        known_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        unknown_ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        known_display = config_page.render(known_ctx, scope=config_page.SCOPE_DISPLAY)
        known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
        unknown_display = config_page.render(unknown_ctx, scope=config_page.SCOPE_DISPLAY)
        unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
        # 21-05-PLAN.md Task 1 (D-06): THEME_SECTION_CAPTION is retired
        # along with theme_fieldset() — its replacement, the Frame
        # colours card's own FRAME_COLOURS_CAPTION, is a fixed, complete,
        # locked sentence (21-UI-SPEC.md §D) that never gains this
        # suffix, so it is deliberately NOT added to this list.
        #
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): QUIET_HOURS_SECTION_
        # CAPTION is ALSO removed from this list — it no longer ends on
        # the generic "applies on the next scheduled poll" clause this
        # suffix mechanism augments; Task 2 gives it its own one computed
        # delay sentence (companion/frame_state.py) instead, pinned by
        # its own dedicated check below.
        for caption in (
                config_page.RUNWAY_SECTION_CAPTION,
                config_page.LED_SECTION_CAPTION,
                config_page.WAKE_INTERVAL_SECTION_CAPTION):
            # escape_html() is what the render pipeline actually applies —
            # several of these captions carry an apostrophe (e.g. "the
            # device's"), so the RAW constant never appears verbatim in the
            # rendered HTML; every comparison below must go through the
            # same escaping the render call site itself uses.
            escaped_caption = escape_html(caption)
            escaped_suffix = config_page.NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % "14:10"
            if (escaped_caption + escaped_suffix) not in known_display and (escaped_caption + escaped_suffix) not in known_device:
                return False, "expected %r to gain the suffix when the next-wake value is known" % (caption,)
            if escaped_caption not in (unknown_display + unknown_device):
                return False, "expected %r to render byte-identical to its own constant when unknown" % (caption,)
            if (escaped_caption + " (next wake") in (unknown_display + unknown_device):
                return False, "expected %r to carry no suffix when the next-wake value is unknown" % (caption,)
        return True, ""
    check(
        "each of Runway/LED/Wake-interval's own caption gains the '(next wake ≈ "
        "HH:MM)' suffix when the value is known, and is byte-identical to its own constant when it "
        "is not (D-13; narrowed by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/"
        "theme_fieldset() are retired, and by 22-05-PLAN.md Task 1 X1/D-04/D-12.1 once Quiet hours' "
        "own caption moves to its own computed delay sentence instead — the Frame colours card's own "
        "caption never gains this suffix either)",
        _affected_captions_gain_the_suffix_only_when_known)

    def _device_header_shows_next_wake_line_when_known():
        known_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        unknown_ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
        if "Next wake" not in known_device or "≈ 14:10" not in known_device:
            return False, "expected the Device header to carry a Next wake ≈ HH:MM line when known"
        unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
        if "Next wake" in unknown_device:
            return False, "expected no Next wake line in the Device header when the value is unknown"
        return True, ""
    check(
        "the Device page header carries a 'Next wake ≈ HH:MM' line when the value is known and "
        "none at all when it is not (D-13's 'Home and Device show' wording)",
        _device_header_shows_next_wake_line_when_known)

    # ==================================================================
    # 22-05-PLAN.md Task 2 (D-04): the one computed delay sentence, in
    # its three branches, for the Quiet hours caption AND the post-save
    # flash — pinned against the SAME frame_state.py source of truth the
    # Frame strip itself reads (22-04-PLAN.md).
    # ==================================================================

    def _quiet_hours_caption_and_flash_agree_on_the_due_branch():
        ctx = {
            "device_config": {"wake_interval_s": 900, "quiet_hours_enabled": False},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_caption_fragment = escape_html("Applies at the next wake, around 14:10.")
        if expected_caption_fragment not in display:
            return False, (
                "expected the Quiet hours caption to carry the DUE delay sentence with the "
                "computed clock, not found in %r" % (display,))
        flash = companion_app._resolve_flash_text(
            companion_app.FLASH_KEY_SAVED, "/tmp",
            last_checkin_ts=ctx["last_checkin_ts"], device_cfg=ctx["device_config"])
        if flash != "Saved — applies at the next wake, around 14:10.":
            return False, "expected the DUE flash text, got %r" % (flash,)
        return True, ""
    check(
        "with a due result, the Quiet hours caption and the post-save flash both read the DUE delay "
        "sentence naming the same computed time (D-04)",
        _quiet_hours_caption_and_flash_agree_on_the_due_branch)

    def _quiet_hours_caption_and_flash_agree_on_the_held_branch():
        # The nightly regression fixture (22-UI-SPEC.md §3.3 binding rule
        # 6, 22-02-PLAN.md Task 2's own pinned example): quiet hours
        # 23:00-07:00 Europe/Paris, last check-in 22:58, clock 02:00 the
        # next morning (a non-DST January date) — held, never late.
        device_cfg = {
            "wake_interval_s": 900, "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        ctx = {
            "device_config": device_cfg,
            "last_checkin_ts": "2026-01-15T22:58:00+01:00", "now": "2026-01-16T02:00:00+01:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_caption_fragment = escape_html("Applies when quiet hours end, around 07:00.")
        if expected_caption_fragment not in display:
            return False, (
                "expected the Quiet hours caption to carry the HELD delay sentence naming the "
                "window's own end, not found in %r" % (display,))
        flash = companion_app._resolve_flash_text(
            companion_app.FLASH_KEY_SAVED, "/tmp",
            last_checkin_ts=ctx["last_checkin_ts"], device_cfg=device_cfg)
        if flash != "Saved — applies when quiet hours end, around 07:00.":
            return False, "expected the HELD flash text, got %r" % (flash,)
        return True, ""
    check(
        "with a held result (the nightly regression fixture), the Quiet hours caption and the "
        "post-save flash both read the HELD delay sentence naming the window's own end, never the "
        "generic due wording (D-04, 22-UI-SPEC.md §3.3 binding rule 6)",
        _quiet_hours_caption_and_flash_agree_on_the_held_branch)

    def _quiet_hours_caption_and_flash_agree_on_the_unknown_branch():
        ctx = {"device_config": {}, "state_dir": "/tmp", "poll_cooldown_remaining": 0}
        display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        expected_caption_fragment = escape_html("Applies the next time the frame wakes up.")
        if expected_caption_fragment not in display:
            return False, (
                "expected the Quiet hours caption to carry the UNKNOWN delay sentence, not found "
                "in %r" % (display,))
        flash = companion_app._resolve_flash_text(companion_app.FLASH_KEY_SAVED, "/tmp")
        if flash != "Saved — applies the next time the frame wakes up.":
            return False, "expected the UNKNOWN flash text, got %r" % (flash,)
        return True, ""
    check(
        "with no check-in at all, the Quiet hours caption and the post-save flash both read the "
        "UNKNOWN delay sentence, which names no time (D-04)",
        _quiet_hours_caption_and_flash_agree_on_the_unknown_branch)

    def _retired_delay_wordings_appear_nowhere_under_companion_or_server():
        # The three literal wordings this plan retires — deliberately NOT
        # typed as a single searchable constant here, so this check's own
        # source is a real, independent occurrence check, not a
        # tautology. Excludes this repository's own test_*.py harnesses
        # (which necessarily name these exact strings, including this
        # very check, to prove their absence) and, deliberately, includes
        # companion/frame_state.py's own source (that module documents
        # the retirement in prose without retyping any of the three
        # literals — see its own comment).
        retired = (
            "Takes effect within about 5 minutes",
            "Applies on the next scheduled poll, which may now be hours away",
            "Saved — will apply on the frame's next scheduled refresh",
        )
        for root in ("companion", "server"):
            for dirpath, _dirnames, filenames in os.walk(root):
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    if filename.startswith("test_"):
                        continue
                    path = os.path.join(dirpath, filename)
                    with open(path, encoding="utf-8") as fh:
                        source = fh.read()
                    for wording in retired:
                        if wording in source:
                            return False, "found retired wording %r in %s" % (wording, path)
        return True, ""
    check(
        "none of the three retired delay wordings ('Takes effect within about 5 minutes', "
        "'Applies on the next scheduled poll, which may now be hours away', 'Saved — will apply "
        "on the frame's next scheduled refresh') appears anywhere under companion/ or server/, "
        "excluding this repository's own test_*.py harnesses (D-04)",
        _retired_delay_wordings_appear_nowhere_under_companion_or_server)

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        def _save_round_trip_shows_confirmation_and_new_selection():
            # 06.6.4.1-07 (D-26): posts to the live SETTINGS_ROUTE
            # ("/settings") now that companion/app.py actually dispatches
            # it — the old "/config" path 404s by design (no redirect).
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode(
                    {"theme": "black", "tracked_runway": "06-24"}).encode())
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            redirect_status, _redirect_headers, body = http_request(
                base + location, cookie=session_cookie)
            if redirect_status != 200:
                return False, "expected 200 following the save redirect, got %d" % redirect_status
            # D-07's confirmation sentence is defined exactly once in the
            # repository, in companion/app.py's FLASH_MESSAGES mapping —
            # referenced here rather than re-typed, so this file is never
            # a second place that literal sentence lives.
            #
            # 22-05-PLAN.md Task 2 (D-04): FLASH_MESSAGES[FLASH_KEY_SAVED]
            # is now a template ("Saved — %s"), never the whole fixed
            # sentence — the confirmation body actually served is what
            # companion_app._resolve_flash_text() resolves it to, given
            # the SAME facts (no check-in yet recorded on this harness's
            # own fresh state dir) the real request itself reads.
            confirmation = escape_html(
                companion_app._resolve_flash_text(
                    companion_app.FLASH_KEY_SAVED, harness.tmpdir,
                    last_checkin_ts=None, device_cfg={}))
            if confirmation.encode() not in body:
                return False, "expected D-07's exact confirmation copy in the response body"
            # 20-07-PLAN.md Task 1 (D-10): the runway group moved from
            # Device to Display this phase, so the newly-saved selection
            # is read back from there now (retargeted from DEVICE_ROUTE).
            _s, _h, body = http_request(
                base + companion_app.DISPLAY_ROUTE, cookie=session_cookie)
            # Polish fix 4 (D-14c): each runway radio now also carries an
            # explicit form="settings-form" attribute.
            if (b'value="06-24" class="visually-hidden" form="%s" checked'
                    % config_page.SETTINGS_FORM_ID.encode()) not in body:
                return False, "expected the newly-saved runway (06-24) to be shown selected"
            return True, ""
        check(
            "a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway selected",
            _save_round_trip_shows_confirmation_and_new_selection)

        def _settings_save_redirect_carries_flash_banner_and_cleanup_script():
            # Quick task 260903-peo (UIR-19): the server-side PRG redirect
            # itself is unchanged by this task — this pins the pairing
            # that makes the client-side cleanup reachable: the rendered
            # redirect target carries BOTH the flash banner
            # flash-cleanup.js looks for (.banner--flash) AND
            # flash-cleanup.js's own deferred <script> tag.
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode(
                    {"theme": "black", "tracked_runway": "06-24"}).encode())
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            # Phase 18: a POST with no return_to field lands on the
            # Display page, the default return route.
            expected_location = "%s?flash=saved" % companion_app.DISPLAY_ROUTE
            if location != expected_location:
                return False, (
                    "expected the PRG redirect target to stay exactly %r, got %r — "
                    "the server-side redirect must be unchanged by this task"
                    % (expected_location, location))
            redirect_status, _redirect_headers, body = http_request(
                base + location, cookie=session_cookie)
            if redirect_status != 200:
                return False, "expected 200 following the save redirect, got %d" % redirect_status
            body_text = body.decode("utf-8", errors="replace")
            if "banner--flash" not in body_text:
                return False, "expected the rendered redirect target to carry the flash banner"
            expected_script_tag = (
                '<script src="%s" defer></script>' % companion_app.FLASH_CLEANUP_SCRIPT_ROUTE)
            if expected_script_tag not in body_text:
                return False, (
                    "expected the rendered redirect target to carry flash-cleanup.js's own "
                    "deferred <script> tag — the pairing that makes the client-side cleanup "
                    "reachable")
            return True, ""
        check(
            "a real HTTP save round trip keeps the server-side PRG redirect exactly "
            "SETTINGS_ROUTE?flash=saved, and the rendered redirect target carries BOTH the "
            "flash banner and flash-cleanup.js's deferred script tag (quick task 260903-peo, "
            "UIR-19)",
            _settings_save_redirect_carries_flash_banner_and_cleanup_script)

        def _settings_post_empty_body_persists_led_false_and_renders_unchecked():
            # 06.6.4.1-07 (D-05): the separate LED route is retired — this
            # is the live-HTTP successor to the old "empty-body POST
            # /config-led" check, now posting to the single merged
            # SETTINGS_ROUTE with nothing submitted at all (the shape a
            # browser sends when nothing is checked/selected). Same
            # persisted outcome, same redirect-with-flash shape.
            # Seeded rather than assumed: this check is about an empty
            # body LEAVING the stored value alone, so it needs a known
            # starting value it can then read back, and the follow-up GET
            # below asserts the rendered control agrees with it.
            device_config.save_device_config(harness.tmpdir, led_enabled=False)
            led_before = False
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=b"")
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25):
            # RETARGETED IN PLACE from "persists led_enabled False". The
            # field's absence now means "leave unchanged", so what this
            # live round trip must show is that whatever was stored
            # BEFORE the empty POST is still stored after it.
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["led_enabled"] is not led_before:
                return False, (
                    "expected an empty-body POST to LEAVE the stored led_enabled %r unchanged, "
                    "got %r" % (led_before, on_disk["led_enabled"]))
            get_status, _get_headers, body = http_request(
                base + companion_app.DEVICE_ROUTE, cookie=session_cookie)
            if get_status != 200:
                return False, "expected 200 on the follow-up GET %s, got %d" % (
                    companion_app.DEVICE_ROUTE, get_status)
            if b'name="led_enabled" value="on" checked' in body:
                return False, "expected the LED checkbox to render unchecked after saving False"
            return True, ""
        check(
            "a live authenticated POST %s with an empty body 303-redirects to %s?flash=saved, "
            "LEAVES the stored led_enabled exactly as it was, and a follow-up GET renders the "
            "control in that same off state (retargeted in place from absent-means-False by "
            "23-07-PLAN.md Task 2)"
            % (config_page.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE),
            _settings_post_empty_body_persists_led_false_and_renders_unchecked)

        def _settings_form_raw_post_no_js_clears_and_sets_theme_arriving():
            # 15-VALIDATION.md row 11 (the Settings-form half this plan
            # owns): a raw, URL-encoded POST to the live SETTINGS_ROUTE -
            # no client script involved - once with a real theme_arriving
            # id, once with theme_arriving="" (the Frame colours card's
            # own leading "Same as departures" chip's real submitted
            # shape), proving the set/clear contract holds over the real
            # HTTP path, not just in-process. 21-05-PLAN.md Task 2
            # (D-09/R-07): retargeted from the retired arrivals-override
            # checkbox onto the new empty-string clear signal.
            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving": "black",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the set save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' after the set raw POST, got %r"
                    % (on_disk["theme_arriving"],))

            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving": "",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the clearing save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "expected theme_arriving None after the theme_arriving='' raw POST, got %r"
                    % (on_disk["theme_arriving"],))
            return True, ""
        check(
            "a raw, URL-encoded no-JS POST to SETTINGS_ROUTE sets theme_arriving to a real id and clears it "
            "back to None via theme_arriving='', over the real HTTP path (15-VALIDATION.md row 11, the "
            "Settings-form half; D-06/D-09, retargeted from the retired arrivals-override checkbox)",
            _settings_form_raw_post_no_js_clears_and_sets_theme_arriving)

        def _settings_post_unauthenticated_redirects_to_login_and_writes_nothing():
            # 06.6.4.1-07 (D-05): live-HTTP successor to the old
            # "unauthenticated POST /config-led" check — same target
            # (now SETTINGS_ROUTE), same no-write assertion.
            config_path = device_config.device_config_path(harness.tmpdir)
            existed_before = os.path.exists(config_path)
            before = open(config_path, "rb").read() if existed_before else None
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            exists_after = os.path.exists(config_path)
            if not existed_before and exists_after:
                return False, "an unauthenticated POST %s created device_config.json" % config_page.SETTINGS_ROUTE
            if existed_before:
                after = open(config_path, "rb").read()
                if before != after:
                    return False, "an unauthenticated POST %s modified device_config.json" % config_page.SETTINGS_ROUTE
            return True, ""
        check(
            "an unauthenticated POST %s redirects to /login and writes nothing" % config_page.SETTINGS_ROUTE,
            _settings_post_unauthenticated_redirects_to_login_and_writes_nothing)

        def _led_route_retired_returns_404():
            # 06.6.4.1-07 (D-05): the separate LED POST route no longer
            # exists anywhere in the app — an authenticated POST to it
            # now falls through to the standard 404, same as any other
            # unrouted path.
            status, _headers, _body = http_request(
                base + "/config-led", method="POST", cookie=session_cookie, data=b"")
            if status != 404:
                return False, "expected 404 for the retired /config-led route, got %d" % status
            return True, ""
        check(
            "an authenticated POST to the retired /config-led route returns 404 (D-05)",
            _led_route_retired_returns_404)

        def _runway_image_route_requires_session():
            status, headers, _ = http_request(base + "/runway-image/3.png")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if location != "/login":
                return False, "expected a Location of /login, got %r" % location
            return True, ""
        check(
            "an unauthenticated GET /runway-image/3.png redirects to /login",
            _runway_image_route_requires_session)

        def _runway_image_route_honest_present_or_absent():
            path = companion_app._runway_image_path("3")
            status, headers, _ = http_request(
                base + "/runway-image/3.png", cookie=session_cookie)
            if os.path.isfile(path):
                if status != 200:
                    return False, "expected 200 when the file exists, got %d" % status
                if headers.get("Content-Type") != "image/png":
                    return False, "expected Content-Type image/png, got %r" % headers.get("Content-Type")
            else:
                if status != 404:
                    return False, "expected 404 when the file is absent (D-02 shipped state), got %d" % status
            return True, ""
        check(
            "a session-authenticated GET /runway-image/3.png returns the branch matching real on-disk state (never 500)",
            _runway_image_route_honest_present_or_absent)

        def _runway_image_route_path_traversal_rejected():
            adversarial_paths = [
                "/runway-image/..%2F..%2Fetc%2Fpasswd.png",
                "/runway-image/../../../etc/passwd.png",
                "/runway-image/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, _ = http_request(
                    base + adversarial_path, cookie=session_cookie)
                if status not in (404,):
                    return False, (
                        "expected 404 for adversarial path %r, got %d"
                        % (adversarial_path, status))
            return True, ""
        check(
            "session-authenticated GET requests for three adversarial runway-image paths all return 404, never 200/500",
            _runway_image_route_path_traversal_rejected)

    finally:
        harness.stop()
        harness.cleanup()

    # ==================================================================
    # Section 3 (16-05-PLAN.md Task 3, T-16-SECRET; rewritten by phase 17
    # plan 02, D-03): a second, dedicated harness with a calendar
    # configured, proving the secret never reaches the SERVED HTTP bytes —
    # not just render()'s in-process return value (Section 1b's own check
    # above covers that half). A separate subprocess keeps this one
    # specific scenario isolated from every assertion the main Section 2
    # harness already covers, rather than for any environment-snapshot
    # reason — the secret now lives in this harness's own state directory
    # on disk, which the running companion process reads fresh on every
    # request (calendar_rules.configured_calendar_url()'s per-call,
    # nothing-cached contract), so it could equally be written before or
    # after the process starts.
    # ==================================================================

    calendar_token = "sk1-distinctive-token-2rv9"
    calendar_host = "private-crew-calendar.example.internal"
    calendar_path = "feeds/roster-export"
    calendar_query_param = "auth_token"
    calendar_url = "https://%s/%s?%s=%s" % (
        calendar_host, calendar_path, calendar_query_param, calendar_token)

    calendar_harness = Harness()
    assert calendar_rules.save_calendar_url(calendar_harness.tmpdir, calendar_url) is True
    try:
        calendar_harness.start()
        calendar_base = calendar_harness.base_url()
        calendar_cookie = _login(calendar_harness)

        def _calendar_secret_never_reaches_served_http_bytes():
            # 20-07-PLAN.md Task 1 (D-11): Calendar moved from Device to
            # Display this phase — retargeted from DEVICE_ROUTE.
            # 21-07-PLAN.md Task 2 (D-14/R-10): EXTENDED, not replaced —
            # the served bytes now legitimately carry the masked host +
            # "…" fragment (the whole point of D-14); the token, path,
            # query-parameter name and the whole raw URL still never do.
            status, _headers, body = http_request(
                calendar_base + companion_app.DISPLAY_ROUTE, cookie=calendar_cookie)
            if status != 200:
                return False, "expected 200 on the authenticated Display page, got %d" % status
            body_text = body.decode("utf-8", errors="replace")
            # 20-09-PLAN.md Task 1 (D-14b): the old one-piece "pending"
            # sentence is retired — a configured calendar with no sync
            # recorded yet now renders the bare "Connected" verdict.
            if config_page.CALENDAR_STATUS_CONNECTED_VERDICT not in body_text:
                return False, "expected the 'Connected' verdict (no sync recorded yet)"
            if escape_html("%s…" % calendar_host) not in body_text:
                return False, "expected the masked host + ellipsis fragment to be served once connected"
            for needle in (calendar_token, calendar_path, calendar_query_param, calendar_url):
                if needle in body_text:
                    return False, "expected %r never to appear in the served response body" % (needle,)
            return True, ""
        check(
            "with a calendar configured via its secret file to a URL carrying a distinctive token, a real "
            "authenticated HTTP GET of the Settings page serves the masked host + ellipsis fragment but "
            "never the token, the path segment, the query-parameter name, or the whole raw URL in the "
            "response body (T-16-SECRET, real HTTP round trip, extended by 21-07-PLAN.md Task 2 for the "
            "new masked-URL line, D-14/R-10)",
            _calendar_secret_never_reaches_served_http_bytes)

        def _calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing():
            # 21-07-PLAN.md Task 2 (D-14/R-10): a stored value that
            # cannot be parsed into a meaningful host must never crash
            # the page and must never render a fabricated placeholder —
            # the whole masked-URL <p> is simply omitted.
            for hostile in ("not a url", "", "javascript:alert(1)"):
                hostile_tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
                try:
                    assert calendar_rules.save_calendar_url(hostile_tmpdir, hostile) is not None
                    ctx = dict(
                        _CALENDAR_BASE_CTX, calendar_configured=True,
                        calendar_last_synced_at=None, state_dir=hostile_tmpdir)
                    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
                finally:
                    shutil.rmtree(hostile_tmpdir, ignore_errors=True)
                if "calendar-masked-url" in rendered:
                    return False, (
                        "hostile value %r: expected no calendar-masked-url line at all" % (hostile,))
            return True, ""
        check(
            "a hostile or unparseable stored calendar URL ('not a url', the empty string, a "
            "javascript: URI) renders no calendar-masked-url line at all and raises nothing (D-14/R-10, "
            "_masked_calendar_url()'s own fail-soft, never-fabricate contract)",
            _calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing)
    finally:
        calendar_harness.stop()
        calendar_harness.cleanup()

    # ==================================================================
    # 19-11-PLAN.md Task 3 (D-12/A-30): the two chip grids and the
    # runway row as named radiogroups, and every hint linked to its
    # control via aria-describedby - no dangling ARIA reference, no
    # empty aria-describedby, and hint+error ids coexisting in order.
    # ==================================================================

    _TASK3_BASE_CTX = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }

    def _display_scope_has_three_radiogroups_device_has_none():
        # 20-07-PLAN.md Task 1 (D-10): Runway moved from Device to
        # Display this phase — Display now carries Theme's two chip
        # grids PLUS the Runway row's own radiogroup (three), while
        # Device (LED, Wake interval only) carries none. Retargeted from
        # "Display >= 2, Device >= 1 (the Runway row)" in place.
        display_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        device_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        display_count = display_rendered.count('role="radiogroup"')
        if display_count < 3:
            return False, (
                "expected at least three role=\"radiogroup\" occurrences on the Display "
                "scope (Theme's two chip grids plus the Runway row), got %d" % display_count)
        device_count = device_rendered.count('role="radiogroup"')
        if device_count != 0:
            return False, (
                "expected no role=\"radiogroup\" occurrence on the Device scope "
                "(LED and Wake interval have no radio groups), got %d" % device_count)
        return True, ""
    check(
        "the Display scope renders at least three role=\"radiogroup\" elements (Theme's departures and "
        "arrivals chip grids, plus the Runway row) and the Device scope renders none (D-12/A-30, "
        "retargeted by 20-07-PLAN.md Task 1/D-10)",
        _display_scope_has_three_radiogroups_device_has_none)

    _ID_RE = re.compile(r'\bid="([^"]*)"')
    _LABELLEDBY_RE = re.compile(r'aria-labelledby="([^"]*)"')
    _DESCRIBEDBY_RE = re.compile(r'aria-describedby="([^"]*)"')

    def _every_aria_reference_resolves_and_none_is_empty():
        for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
            rendered = config_page.render(_TASK3_BASE_CTX, scope=scope)
            existing_ids = set(_ID_RE.findall(rendered))
            for value in _DESCRIBEDBY_RE.findall(rendered):
                if not value:
                    return False, "scope %r: expected no empty aria-describedby, found one" % (scope,)
                for token in value.split(" "):
                    if token not in existing_ids:
                        return False, (
                            "scope %r: aria-describedby token %r does not match any id "
                            "the same output emits" % (scope, token))
            for value in _LABELLEDBY_RE.findall(rendered):
                if not value:
                    return False, "scope %r: expected no empty aria-labelledby, found one" % (scope,)
                for token in value.split(" "):
                    if token not in existing_ids:
                        return False, (
                            "scope %r: aria-labelledby token %r does not match any id "
                            "the same output emits" % (scope, token))
        return True, ""
    check(
        "every aria-labelledby and aria-describedby value render() emits, at every scope, resolves to "
        "an id the same output actually carries, and no element emits an empty aria-describedby or "
        "aria-labelledby (D-12/A-30)",
        _every_aria_reference_resolves_and_none_is_empty)

    def _control_with_both_hint_and_error_carries_both_ids_in_order():
        rendered = config_page.render(
            _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE,
            errors={"led_enabled": "msg"}, submitted={})
        # 23-07-PLAN.md Task 2 (D2/CFG-36): retargeted in place from the
        # led_enabled CHECKBOX to the role="switch" that replaced it. The
        # contract is unchanged and now has a third id to keep in order:
        # the switch's own state span, then the group's caption (the hint
        # the checkbox carried through _field_error_attrs()'s hint_id),
        # then the error anchor — hint still before error, and none of
        # the three overwriting another.
        input_match = re.search(r'<button type="submit" class="switch"[^>]*>', rendered)
        if not input_match:
            return False, "expected the led_enabled switch to render"
        describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
        if not describedby_match:
            return False, "expected an aria-describedby on the errored led_enabled switch"
        ids = describedby_match.group(1).split(" ")
        if ids != [config_page.QUICK_LED_STATE_ID, config_page.LED_SECTION_CAPTION_ID,
                   "led-enabled-error"]:
            return False, (
                "expected the state id, then the hint id, then the error id, got %r" % (ids,))
        # And with no error the third id simply is not there — so the
        # clause above is about the ERROR rather than about a constant
        # three-id string.
        clean = config_page.render(
            _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE, errors={}, submitted={})
        clean_match = re.search(r'<button type="submit" class="switch"[^>]*>', clean)
        if not clean_match or "led-enabled-error" in clean_match.group(0):
            return False, (
                "expected no error id on the switch's aria-describedby when there is no error")
        return True, ""
    check(
        "a control carrying both a hint and an error (led_enabled's switch, rendered with an errors "
        "dict) has its state, hint and error ids in its aria-describedby, hint still before error, "
        "never one overwriting another, and no error id at all when there is no error (D-12/A-30; "
        "retargeted in place from the retired checkbox by 23-07-PLAN.md Task 2)",
        _control_with_both_hint_and_error_carries_both_ids_in_order)

    # ==================================================================
    # 20-11-PLAN.md Task 1 (D-26/D-28): the Notifications group — a
    # write-only topic URL, two checkboxes, no language selector.
    # ==================================================================

    def _notifications_group_status_row_configured_vs_not_and_write_only_url():
        rendered_unconfigured = config_page.render(
            {"device_config": {}, "poll_cooldown_remaining": 0}, scope=config_page.SCOPE_DEVICE)
        if config_page.NOTIFICATIONS_SECTION_HEADING not in rendered_unconfigured:
            return False, "expected the Notifications heading on the Device scope"
        if config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT not in rendered_unconfigured:
            return False, "expected the 'Not configured' verdict with no topic URL stored"
        if config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT in rendered_unconfigured:
            return False, "expected no 'Configured' verdict with no topic URL stored"

        seeded_url = "https://ntfy.sh/skypane-secret-token-xyz"
        rendered_configured = config_page.render(
            {
                "device_config": {
                    "notifications": {
                        "topic_url": seeded_url, "battery_low": True,
                        "frame_silent": False, "lang": "en"}},
                "poll_cooldown_remaining": 0,
            },
            scope=config_page.SCOPE_DEVICE)
        if config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT not in rendered_configured:
            return False, "expected the 'Configured' verdict with a topic URL stored"
        if config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT in rendered_configured:
            return False, "expected no 'Not configured' verdict with a topic URL stored"
        if seeded_url in rendered_configured or "secret-token-xyz" in rendered_configured:
            return False, "expected no substring of the stored topic URL anywhere in the rendered page"
        for rendered in (rendered_unconfigured, rendered_configured):
            match = re.search(r'<input[^>]*name="notifications_topic_url"[^>]*>', rendered)
            if not match:
                return False, "expected the notifications_topic_url input to render"
            if "value=" in match.group(0):
                return False, "expected no value attribute on the write-only topic-URL input"
        return True, ""
    check(
        "notifications_group()'s status row reads 'Not configured' with no URL stored and "
        "'Configured' with one, the topic-URL input never carries a value attribute in either "
        "state, and no substring of a seeded URL appears anywhere in the rendered page (T-20-12)",
        _notifications_group_status_row_configured_vs_not_and_write_only_url)

    def _notifications_checkboxes_reflect_stored_state():
        rendered = config_page.render(
            {
                "device_config": {
                    "notifications": {
                        "topic_url": "https://ntfy.sh/x", "battery_low": False,
                        "frame_silent": True, "lang": "fr"}},
                "poll_cooldown_remaining": 0,
            },
            scope=config_page.SCOPE_DEVICE)
        battery_match = re.search(
            r'<input type="checkbox" name="notifications_battery"[^>]*>', rendered)
        silent_match = re.search(
            r'<input type="checkbox" name="notifications_silent"[^>]*>', rendered)
        if not battery_match or not silent_match:
            return False, "expected both notifications checkboxes to render"
        if " checked" in battery_match.group(0):
            return False, "expected notifications_battery unchecked when stored False"
        if " checked" not in silent_match.group(0):
            return False, "expected notifications_silent checked when stored True"
        return True, ""
    check(
        "notifications_group()'s two checkboxes reflect the stored battery_low/frame_silent "
        "booleans",
        _notifications_checkboxes_reflect_stored_state)

    def _notifications_group_has_no_lang_selector():
        rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        if "notifications_lang" in rendered:
            return False, "expected no notifications_lang control anywhere on the page"
        return True, ""
    check(
        "the Device page contains no notifications_lang control anywhere (D-28: lang travels "
        "silently, never through a <select>)",
        _notifications_group_has_no_lang_selector)

    def _handle_post_notifications_round_trip_writes_lang_from_ctx():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir, "lang": "fr"}
            flash_key = config_page.handle_post(
                {
                    "scope": config_page.SCOPE_DEVICE,
                    "notifications_topic_url": "https://ntfy.sh/skypane-abc123",
                    "notifications_battery": config_page.NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
                    "notifications_silent": config_page.NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)["notifications"]
            expected = {
                "topic_url": "https://ntfy.sh/skypane-abc123",
                "battery_low": True, "frame_silent": True, "lang": "fr"}
            if on_disk != expected:
                return False, "expected %r, got %r" % (expected, on_disk)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() with scope=device, a topic URL and both checkboxes persists the whole "
        "notifications group and writes lang from ctx['lang'] (D-26/D-28)",
        _handle_post_notifications_round_trip_writes_lang_from_ctx)

    def _handle_post_empty_notifications_url_leaves_stored_url_intact():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            device_config.save_device_config(
                tmpdir, notifications={
                    "topic_url": "https://ntfy.sh/skypane-seeded",
                    "battery_low": True, "frame_silent": True, "lang": "en"})
            flash_key = config_page.handle_post(
                {"scope": config_page.SCOPE_DEVICE, "notifications_topic_url": ""}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)["notifications"]
            if on_disk["topic_url"] != "https://ntfy.sh/skypane-seeded":
                return False, (
                    "expected the stored URL to survive an empty submission, got %r"
                    % (on_disk["topic_url"],))
            if on_disk["battery_low"] is not False or on_disk["frame_silent"] is not False:
                return False, "expected both checkboxes to resolve absent-means-False"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post() with an empty notifications_topic_url leaves the previously stored URL "
        "unchanged (D-26: empty means 'leave unchanged', never 'clear it')",
        _handle_post_empty_notifications_url_leaves_stored_url_intact)

    # ==================================================================
    # 20-11-PLAN.md Task 2 (D-22..D-24): the live theme preview above
    # the chip grid.
    # ==================================================================

    def _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions():
        # 21-05-PLAN.md Task 1 (D-07): the figure now also carries the
        # Frame colours card's own layout modifier
        # (frame-colours__preview) alongside the unchanged
        # theme-live-preview class — retargeted from an exact-class-
        # attribute match to a substring match for that reason.
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
            scope=config_page.SCOPE_DISPLAY)
        if rendered.count('class="theme-live-preview frame-colours__preview"') != 1:
            return False, (
                "expected exactly one .theme-live-preview.frame-colours__preview figure, got %d"
                % rendered.count('class="theme-live-preview frame-colours__preview"'))
        match = re.search(r'<img class="theme-live-preview__image"[^>]*>', rendered)
        if not match:
            return False, "expected the live preview's own <img> element"
        tag = match.group(0)
        if 'src="%sblue.png?live=1"' % config_page.THEME_PREVIEW_ROUTE_PREFIX not in tag:
            return False, "expected the live preview's src to end in the saved theme's ?live=1 URL"
        if 'loading="eager"' not in tag:
            return False, 'expected the live preview\'s own <img> to carry loading="eager"'
        if 'width="%d"' % config_page.THEME_LIVE_PREVIEW_WIDTH not in tag:
            return False, "expected an explicit width attribute"
        if 'height="%d"' % config_page.THEME_LIVE_PREVIEW_HEIGHT not in tag:
            return False, "expected an explicit height attribute"
        return True, ""
    check(
        "a Display render contains exactly one .theme-live-preview figure whose <img> src ends in "
        'the saved theme\'s ?live=1 URL, carries loading="eager" and explicit width/height '
        "(D-22..D-24)",
        _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions)

    def _every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy():
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
            scope=config_page.SCOPE_DISPLAY)
        labels = re.findall(r'<label class="theme-chip[^>]*data-preview-src="([^"]+)"', rendered)
        if len(labels) < len(device_config.THEME_IDS):
            return False, (
                "expected at least one data-preview-src per registered theme, got %d"
                % len(labels))
        for src in labels:
            if not src.endswith(".png?live=1"):
                return False, "expected every data-preview-src to end in .png?live=1, got %r" % (src,)
        chip_images = re.findall(r'<img class="theme-chip__preview"[^>]*>', rendered)
        if not chip_images:
            return False, "expected at least one chip <img>"
        for tag in chip_images:
            if 'loading="lazy"' not in tag:
                return False, 'expected every chip <img> to keep loading="lazy"'
            if "?live=1" in tag:
                return False, "expected the chip's own <img> src to stay the fixed, non-live preview"
        return True, ""
    check(
        'every chip\'s own <label> carries a data-preview-src ending in .png?live=1, while each '
        'chip\'s own <img> keeps loading="lazy" and the fixed, non-live src (D-24)',
        _every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy)

    def _live_preview_caption_names_seeded_callsign_and_falls_back_to_sample():
        tmpdir = tempfile.mkdtemp(prefix="skypane-theme-live-preview-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            with_event = config_page.render(
                {
                    "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                    "state_dir": tmpdir,
                },
                scope=config_page.SCOPE_DISPLAY)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        expected_caption = (
            config_page.THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE % "AFR1380")
        if escape_html(expected_caption) not in with_event:
            return False, "expected the caption to name the seeded event's callsign"

        without_event = config_page.render(
            {
                "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                "state_dir": None,
            },
            scope=config_page.SCOPE_DISPLAY)
        if escape_html(config_page.THEME_LIVE_PREVIEW_CAPTION_SAMPLE) not in without_event:
            return False, "expected the sample-flight caption with no events/no state_dir"
        return True, ""
    check(
        "the live preview's caption names the seeded event's callsign, and falls back to the "
        "sample-flight wording with no events (D-24)",
        _live_preview_caption_names_seeded_callsign_and_falls_back_to_sample)

    def _french_display_render_shows_the_live_preview_caption_with_flight_in_french():
        tmpdir = tempfile.mkdtemp(prefix="skypane-theme-live-preview-fr-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(
                    conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2",
                    callsign="AFR1380")
            prefs.set_request_prefs(lang="fr")
            try:
                rendered = config_page.render(
                    {
                        "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                        "state_dir": tmpdir,
                    },
                    scope=config_page.SCOPE_DISPLAY)
            finally:
                prefs.set_request_prefs(lang="en")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        if "Aperçu avec votre dernier vol : AFR1380" not in rendered:
            return False, "expected the French live-preview caption naming the seeded callsign"
        return True, ""
    check(
        "a French Display render's live preview shows ‘Aperçu avec votre dernier "
        "vol : ’ followed by the seeded event's callsign (D-24/D-05)",
        _french_display_render_shows_the_live_preview_caption_with_flight_in_french)

    # --- 22-10-PLAN.md Task 1 (X6, T10, T12, C1) ----------------------

    def _display_renders_one_chip_density_and_a_swatch_legend_under_every_grid():
        # X6: one chip size on the whole page. Before this plan the
        # departures grid rendered eighteen 160x108 chips while the
        # Arrivals/Calendar/Rules grids rendered the same eighteen themes
        # at ~104px - one control, two shapes, on one page.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)

        grid_classes = re.findall(r'<div class="(theme-chip-grid[^"]*)"', rendered)
        if len(grid_classes) != 4:
            return False, (
                "expected 4 chip grids on Display (departures, arrivals, calendar, rules), got %d"
                % len(grid_classes))
        for cls in grid_classes:
            if "theme-chip-grid--compact" not in cls:
                return False, "every chip grid must carry the compact modifier, got %r" % (cls,)

        chip_classes = re.findall(r'<label class="(theme-chip[^"]*)"', rendered)
        theme_count = len(device_config.THEME_IDS)
        # 4 grids x every theme, plus the two leading "Same as departures"
        # placeholder chips (arrivals + calendar), which are
        # .theme-chip--placeholder and carry no --compact modifier of
        # their own (they have no preview band to shrink).
        real_chips = [c for c in chip_classes if "theme-chip--placeholder" not in c]
        if len(real_chips) != theme_count * 4:
            return False, (
                "expected %d real chips (%d themes x 4 grids), got %d"
                % (theme_count * 4, theme_count, len(real_chips)))
        for cls in real_chips:
            if "theme-chip--compact" not in cls:
                return False, "every chip must carry the size-only compact modifier, got %r" % (cls,)

        # The legend: one line under each grid, never one per chip.
        legend = escape_html(config_page.THEME_CHIP_SWATCH_LEGEND)
        if rendered.count(legend) != 4:
            return False, (
                "expected the swatch legend exactly once per grid (4), got %d - it is a legend "
                "under the grid, not a caption per chip" % rendered.count(legend))
        legend_html = '<p class="text-label section-caption">%s</p>' % legend
        if legend_html not in rendered:
            return False, (
                "expected the legend to carry .text-label section-caption's exact declaration set")
        # Outside the radiogroup, immediately after its closing </div>.
        if ("</label></div>" + legend_html) not in rendered:
            return False, "expected the legend to render as a sibling AFTER the grid, not inside it"
        return True, ""
    check(
        "every colour-usage chip grid on Display renders at the compact density (one chip size per "
        "page, X6) and each grid is followed by exactly one swatch legend in .text-label "
        "section-caption's own declaration set, outside the radiogroup (22-10-PLAN.md Task 1)",
        _display_renders_one_chip_density_and_a_swatch_legend_under_every_grid)

    # ------------------------------------------------------------------
    # 27-07-PLAN.md Task 3 (CFG-70): the legend stops naming a
    # distinction the registry does not carry.
    # ------------------------------------------------------------------

    def _the_swatch_legend_names_as_many_things_as_the_registry_carries():
        # THE RELATIONSHIP, COMPUTED FROM THE REGISTRY AT CHECK TIME —
        # never the literal string "Departures & arrivals". A literal
        # check would go stale silently the day a theme makes departures
        # and arrivals differ, pinning a lie in place exactly like the
        # defect this task fixes wore a different hat. "·" is the
        # separator the PREVIOUS copy used to name two things
        # ("Departures · Arrivals"); splitting on it is how this check
        # counts how many things the CURRENT copy names, whatever that
        # copy's own wording turns out to be.
        legend = config_page.THEME_CHIP_SWATCH_LEGEND
        labels = [part.strip() for part in legend.split("·") if part.strip()]
        label_count = len(labels)
        for theme_id in device_config.THEME_IDS:
            theme = device_config.THEMES[theme_id]
            colours = {
                config_page._palette_hex(theme["departing_index"]),
                config_page._palette_hex(theme["arriving_index"]),
            }
            expected = len(colours)
            if label_count != expected:
                return False, (
                    "theme=%r: the registry gives this theme %d distinct swatch colour(s) "
                    "(departing_index=%r, arriving_index=%r) but the shared legend %r names "
                    "%d label(s) — the legend is ONE line shown for every theme's chip, so it "
                    "must name exactly as many things as the registry gives that theme"
                    % (theme_id, expected, theme["departing_index"], theme["arriving_index"],
                       legend, label_count))
        return True, ""
    check(
        "the chip swatch legend names exactly as many things as the registry gives EVERY "
        "theme — computed from _palette_hex(departing_index)/_palette_hex(arriving_index) at "
        "check time, never a restated literal, so a future theme that DOES give departures "
        "and arrivals different inks would make this check demand two labels on its own "
        "(CFG-70, 27-07-PLAN.md Task 3)",
        _the_swatch_legend_names_as_many_things_as_the_registry_carries)

    def _the_current_badge_reads_a_server_rendered_translated_attribute():
        # T10: the badge's text used to be hard-coded English inside
        # style.css. It is now rendered onto the saved chip/card only -
        # the only element `--selected:not(:has(input:checked))::after`
        # can match - and read back with content: attr(...).
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        attr = config_page.CURRENT_BADGE_ATTR
        en = '%s="%s"' % (attr, escape_html(config_page.CURRENT_BADGE_LABEL))
        # One saved runway card, plus the saved theme chip in each of the
        # four grids that has "white" as its effective selection. Assert
        # the invariant that matters instead of a brittle total: every
        # element carrying the attribute also carries a --selected class,
        # and every --selected element carries the attribute.
        if rendered.count(attr + "=") == 0:
            return False, "expected the saved chip/card to carry the %s attribute" % attr
        if rendered.count(en) != rendered.count(attr + "="):
            return False, "expected every %s value to be the translated badge label" % attr
        for tag in re.findall(r"<label class=\"[^\"]*\"[^>]*>", rendered):
            has_attr = (attr + "=") in tag
            is_selected = "--selected" in tag
            if has_attr != is_selected:
                return False, (
                    "the %s attribute must be emitted on exactly the --selected elements, got %r"
                    % (attr, tag))

        prefs.set_request_prefs(lang="fr")
        try:
            fr_rendered = config_page.render({
                "device_config": {"theme": "white", "tracked_runway": "3"},
                "poll_cooldown_remaining": 0,
            }, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if ('%s="Actuel"' % attr) not in fr_rendered:
            return False, "expected the French render to carry the translated badge text"
        if ('%s="Current"' % attr) in fr_rendered:
            return False, "expected no English badge text in a French render"
        return True, ""
    check(
        "the 'Current' badge's text is server-rendered as a translated data-current-label attribute "
        "on exactly the --selected chip/card (never on any other), and the French render carries the "
        "French text (T10/B16, 22-10-PLAN.md Task 1)",
        _the_current_badge_reads_a_server_rendered_translated_attribute)

    def _segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif():
        source = _read_static("style.css")

        # T12: the global `label { margin-bottom: var(--space-sm) }` made
        # the segmented rule-kind control 8px taller than its own 28px
        # segments plus 2px padding, with the segments floating against
        # the container's top edge.
        selector = '.theme-form input[type="radio"] + label {'
        if selector not in source:
            return False, "expected style.css to declare %r" % (selector,)
        body = source[source.index(selector) + len(selector):source.index("}", source.index(selector))]
        if "margin-bottom: 0" not in body:
            return False, "%r must reset the global label margin-bottom (T12)" % (selector,)
        if "height: 28px" not in body:
            return False, "%r must keep its registered 28px segment height" % (selector,)

        # C1: the label-voice legend leaves the serif family by a LATER,
        # HIGHER-SPECIFICITY rule - `legend` itself stays in the shared
        # serif selector, which it earned as a bug fix.
        serif_selector = "legend,\n.text-heading {"
        if serif_selector not in source:
            return False, "expected `legend` to stay in the shared serif selector"
        serif_idx = source.index(serif_selector)
        legend_selector = ".frame-colours__panel-legend {"
        if legend_selector not in source:
            return False, "expected style.css to declare %r" % (legend_selector,)
        legend_idx = source.index(legend_selector)
        if legend_idx <= serif_idx:
            return False, (
                "the label-voice legend's override must come AFTER the shared serif rule in "
                "source order")
        legend_body = source[legend_idx + len(legend_selector):source.index("}", legend_idx)]
        if "font-family: var(--font-ui)" not in legend_body:
            return False, "%r must take the label-voice legend out of the serif family" % (legend_selector,)
        return True, ""
    check(
        "the segmented control resets the global label margin-bottom while keeping its 28px segments "
        "(T12), and the label-voice legend leaves the serif family through a later, higher-specificity "
        "rule while bare `legend` stays in the shared serif selector (C1, 22-10-PLAN.md Task 1)",
        _segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif)

    def _the_rules_add_form_is_one_left_aligned_centre_aligned_row():
        source = _read_static("style.css")
        selector = ".rule-add-form--inline {"
        if selector not in source:
            return False, "expected style.css to declare %r" % (selector,)
        body = source[source.index(selector) + len(selector):source.index("}", source.index(selector))]
        # The real defect: this modifier never reset .rule-add-form's own
        # flex-direction: column, so `align-items: flex-end` aligned every
        # child to the RIGHT of an 830px form, each on its own line.
        if "flex-direction: row" not in body:
            return False, (
                "%r must reset .rule-add-form's own flex-direction: column - that, not a "
                "margin-left: auto, is what right-aligned this form" % (selector,))
        if "align-items: center" not in body:
            return False, (
                "%r must centre-align its four separate controls (C4's composition rule)" % (selector,))
        if "flex-end" in body:
            return False, "%r must not keep the flex-end cross-axis alignment" % (selector,)
        if "margin-left: auto" in body:
            return False, "%r must declare no auto left margin" % (selector,)
        return True, ""
    check(
        "the rules add-form renders as one left-aligned, centre-aligned flex ROW (X6/C4) - the "
        "flex-direction: column it never reset, not an auto margin, is what pushed 'Add rule' to the "
        "far right (22-10-PLAN.md Task 1)",
        _the_rules_add_form_is_one_left_aligned_centre_aligned_row)

    # --- 22-10-PLAN.md Task 2 (B9, B14, B15, B7/C3) -------------------

    def _each_time_input_carries_the_site_language_and_a_visible_24h_sibling():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for name, value in (("quiet_hours_start", "22:00"), ("quiet_hours_end", "06:00")):
            needle = '<input type="time" name="%s" value="%s"' % (name, value)
            if needle not in rendered:
                return False, "expected %r in the rendered Display page" % (needle,)
            idx = rendered.index(needle)
            tail = rendered[idx:idx + 400]
            if 'lang="en"' not in tail:
                return False, "%s must carry the site language as lang= (B14)" % name
            sibling = (
                '<span class="text-label field-inline-value" aria-hidden="true">%s</span>' % value)
            if sibling not in tail:
                return False, (
                    "%s must be followed by a VISIBLE sibling showing the normalised 24h value, "
                    "not a placeholder and not a title (B14)" % name)
            # The value must not have been smuggled into a placeholder or
            # a title instead - both are what B14's fix column rules out.
            input_tag = rendered[idx:rendered.index(">", idx)]
            if "placeholder=" in input_tag or "title=" in input_tag:
                return False, "%s must carry neither a placeholder nor a title (B14)" % name

        prefs.set_request_prefs(lang="fr")
        try:
            fr_rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        finally:
            prefs.set_request_prefs(lang="en")
        if 'lang="fr"' not in fr_rendered:
            return False, "expected a French render to set lang=\"fr\" on its time inputs"
        if 'type="time" name="quiet_hours_start" value="22:00" required lang="en"' in fr_rendered:
            return False, "expected no lang=\"en\" time input in a French render"
        return True, ""
    check(
        "each <input type=\"time\"> carries the site language and a visible sibling showing the "
        "normalised 24h value (never a placeholder, never a title), in both languages "
        "(B14, 22-10-PLAN.md Task 2)",
        _each_time_input_carries_the_site_language_and_a_visible_24h_sibling)

    def _style_css_carries_the_b9_b15_and_b7_geometry_rules():
        source = _read_static("style.css")

        # B9: three equal runway cards on one line, never a 2 + 1 orphan.
        # A zero basis with no minimum is what makes wrapping structurally
        # impossible for three items; the 150px/140px pair it replaces is
        # exactly what produced the measured orphan at 390px.
        selector = ".runway-card {"
        idx = source.index(selector)
        body = source[idx + len(selector):source.index("\n}", idx)]
        if "flex: 1 1 0;" not in body:
            return False, ".runway-card must take a zero flex basis (B9)"
        if "min-width: 0;" not in body:
            return False, ".runway-card must take no minimum width (B9)"
        # Comment-filtered: the rule keeps a SUPERSEDED comment naming the
        # 150px/140px pair it replaces and why that pair produced the
        # orphan. That prose is the record of the change and must not be
        # deleted to satisfy a grep - so only DECLARATION lines are read.
        declarations = "\n".join(
            line for line in body.splitlines() if not line.lstrip().startswith(("*", "/")))
        if "150px" in declarations or "140px" in declarations:
            return False, ".runway-card must not keep the 150px basis / 140px floor that wrapped 2 + 1"
        # .runway-row has a SECOND consumer (the quiet-hours preset row),
        # which must keep wrapping - so the fix must not sit on the row.
        row_idx = source.index(".runway-row {")
        row_body = source[row_idx + len(".runway-row {"):source.index("\n}", row_idx)]
        if "nowrap" in row_body:
            return False, (
                ".runway-row must keep flex-wrap: wrap - quiet_hours_group()'s preset row shares "
                "this class and must still be allowed to wrap")

        # B15: the calendar Connect/Replace button is content-width and
        # left-aligned, and keeps its accent fill (geometry only).
        b15 = '.rule-add-form:not(.rule-add-form--inline) > button[type="submit"] {'
        if b15 not in source:
            return False, "expected style.css to declare %r (B15)" % (b15,)
        b15_body = source[source.index(b15) + len(b15):source.index("\n}", source.index(b15))]
        if "align-self: flex-start" not in b15_body:
            return False, "%r must opt the button out of the column's stretch (B15)" % (b15,)
        if "width: auto" not in b15_body:
            return False, "%r must declare an automatic width (B15)" % (b15,)
        for banned in ("width: 100%", "display: block", "flex: 1"):
            if banned in b15_body:
                return False, "%r must declare no full-width treatment, found %r" % (b15, banned)

        # B7/C3: the selected-and-hovered segment restore rule, at the
        # register's own 12% accent wash - no new percentage.
        b7 = ".theme-form .theme-option--active:hover {"
        if b7 not in source:
            return False, "expected style.css to declare %r (B7/C3)" % (b7,)
        b7_body = source[source.index(b7) + len(b7):source.index("\n}", source.index(b7))]
        if "color-mix(in srgb, var(--color-accent) 12%, transparent)" not in b7_body:
            return False, (
                "%r must restore the register's own 12%% accent wash, not a new percentage "
                "(22-AUDIT.md's '12-18%%' is a suggestion; the register is the contract)" % (b7,))
        if "color: var(--color-accent)" not in b7_body:
            return False, "%r must restore the active segment's accent text" % (b7,)
        # Its :not()-scoped partner must still exist, or a hover on a
        # non-active segment would fall through to the primary fill.
        partner = ".theme-form .theme-option:not(.theme-option--active):hover {"
        if partner not in source:
            return False, "expected the :not()-scoped non-active hover rule to stay (B7/C3)"
        if source.index(partner) > source.index(b7):
            return False, "the :not()-scoped rule must stay ahead of the active restore rule"
        return True, ""
    check(
        "style.css carries B9's zero-basis runway card (with .runway-row still wrapping for its "
        "second consumer), B15's content-width left-aligned calendar button with its accent kept, "
        "and B7/C3's active-segment hover restore at the register's own 12% accent wash "
        "(22-10-PLAN.md Task 2)",
        _style_css_carries_the_b9_b15_and_b7_geometry_rules)

    # --- 22-10-PLAN.md Task 3 (B8, B17) -------------------------------

    def _send_a_test_lives_inside_the_notifications_card_via_the_form_idiom():
        # B8: the button used to render after </form> closed, as an
        # orphan floating between the Notifications card and the next
        # card. It now renders inside the card and reaches its own empty
        # <form> across the DOM.
        card = config_page.notifications_group(True, False, False)
        button = '<button type="submit" form="notifications-test">%s</button>' % escape_html(
            config_page.NOTIFICATIONS_TEST_BUTTON_TEXT)
        if button not in card:
            return False, "expected the test button INSIDE the Notifications card (B8)"
        if not card.rstrip().endswith("</div>"):
            return False, "expected the card to still close its own wrapper last"

        section = config_page.notifications_test_section()
        expected_form = (
            '<form method="post" action="/settings/notifications/test" '
            'id="notifications-test" class="notifications-test-form"></form>')
        if section != expected_form:
            return False, (
                "expected notifications_test_section() to render an EMPTY form carrying the id "
                "the button's form= names, got %r" % (section,))
        if "<button" in section:
            return False, "the sibling form must hold no control of its own (B8)"

        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DEVICE)
        if rendered.count('form="notifications-test"') != 1:
            return False, "expected exactly one cross-DOM attachment to the test form"
        if rendered.count('id="notifications-test"') != 1:
            return False, "expected exactly one element carrying that id"
        # Nothing renders between the settings form's own close and the
        # empty form: the two are adjacent, with no control in between.
        if "</form><form" not in rendered.replace("\n", ""):
            return False, (
                "expected the empty test form to render immediately after the settings form, "
                "with no orphaned control between the two cards (B8)")
        # And the button is inside the card, not after it.
        card_end = rendered.index('id="notifications-test"')
        if rendered.index('form="notifications-test"') > card_end:
            return False, "expected the button to render BEFORE the empty form, inside its card"
        # The action and its handler are untouched by the move - form
        # ownership comes from the attribute, not from proximity (T-22-34).
        if config_page.NOTIFICATIONS_TEST_ROUTE not in rendered:
            return False, "expected the test form to keep its own action route"
        return True, ""
    check(
        "'Send a test' renders inside the Notifications card and reaches its own EMPTY sibling "
        "<form> through the cross-DOM form= idiom's fifth consumer - no control renders between "
        "two cards, and the form keeps its own action (B8, 22-10-PLAN.md Task 3)",
        _send_a_test_lives_inside_the_notifications_card_via_the_form_idiom)

    def _the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input():
        # B17: the label used to WRAP the input, which put both on one
        # line and started the control at x=515 while every other Device
        # field started at x=361.
        rendered = config_page.wake_interval_group(300)
        label = '<label for="%s">%s</label>' % (
            config_page.WAKE_INTERVAL_INPUT_ID,
            escape_html(config_page.i18n.t("Wake interval (seconds)")))
        if label not in rendered:
            return False, "expected the label to be its own element above the control (B17)"
        if "</label><input" not in rendered:
            return False, "expected the input to be the label's SIBLING, not its child (B17)"
        unit = (
            '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
            % config_page.WAKE_INTERVAL_UNIT_LABEL)
        if unit not in rendered:
            return False, "expected the unit as a sibling label, not a placeholder (B17)"
        input_tag = rendered[rendered.index('<input type="number"'):]
        input_tag = input_tag[:input_tag.index(">") + 1]
        # The unit must be a SIBLING, never the control's own placeholder
        # or title - both are what B17's fix column rules out, and the
        # placeholder slot is already spoken for by the locked
        # "Uses server default" empty-state text.
        if 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT not in input_tag:
            return False, "expected the locked placeholder text to survive untouched"
        if "title=" in input_tag:
            return False, "the unit must not be carried as a title on the control (B17)"

        source = _read_static("style.css")
        selector = '.config-form input[name="wake_interval_s"] {'
        if selector not in source:
            return False, "expected style.css to declare %r (B17)" % (selector,)
        body = source[source.index(selector) + len(selector):source.index("}", source.index(selector))]
        if "width: 8ch" not in body:
            return False, "%r must declare a character-based width (B17)" % (selector,)
        if "min-width: 96px" not in body:
            return False, "%r must declare a pixel minimum (B17)" % (selector,)
        if "height" in body:
            return False, (
                "%r must declare NO height - the global input/select 44px min-height is the touch-"
                "target register's 'kept' entry for <input type=\"number\"> and stays untouched"
                % (selector,))
        # It must beat, not merely follow, the phase-18 width rule.
        competitor = '.config-form input[type="number"],'
        if source.index(competitor) > source.index(selector):
            return False, (
                "the content-fit rule must come AFTER .config-form input[type=\"number\"]'s own "
                "width: 100% at equal specificity, or it silently loses")
        return True, ""
    check(
        "the wake-interval field puts its label on its own line above a content-sized input (8ch "
        "with a 96px minimum, no height declared so the 44px touch-target floor is untouched) with "
        "the unit as a sibling label (B17, 22-10-PLAN.md Task 3)",
        _the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input)

    def _the_calendar_status_detail_has_a_singular_form():
        # D-06/B16/CFG-29: this string read "1 upcoming flights" whenever
        # the feed held exactly one. 22-08-PLAN.md found it and left it
        # because that plan does not own this file.
        synced = "2026-09-13T09:00:00+00:00"
        now = "2026-09-13T09:05:00+00:00"

        def detail_for(count):
            return config_page.calendar_group(
                True, False, synced, None, now, count)

        one = detail_for(1)
        if "1 upcoming flights" in one:
            return False, "expected a singular form for exactly one upcoming flight"
        if escape_html(config_page.CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE.split(" ·")[0]) not in one:
            return False, "expected the singular template's own text at a count of 1"
        for count in (0, 2, 7):
            many = detail_for(count)
            if "%d upcoming flights" % count not in many:
                return False, "expected the plural form at a count of %d" % count
        # Both forms must be translatable, and both must be real
        # catalogue keys (test_i18n.py's own completeness scan proves the
        # second half; this proves the call site reaches both).
        prefs.set_request_prefs(lang="fr")
        try:
            fr_one = detail_for(1)
            fr_many = detail_for(3)
        finally:
            prefs.set_request_prefs(lang="en")
        if "1 vol à venir" not in fr_one:
            return False, "expected the French singular form"
        if "3 vols à venir" not in fr_many:
            return False, "expected the French plural form"
        return True, ""
    check(
        "the Calendar status detail has a singular form, so a feed holding exactly one flight "
        "never reads '1 upcoming flights', in both languages (D-06/B16/CFG-29, 22-10-PLAN.md "
        "Task 3 — found by 22-08, landed here because this plan owns config_page.py)",
        _the_calendar_status_detail_has_a_singular_form)

    # --- 23-06-PLAN.md Task 2 (D1/CFG-35): the Display scope joins the
    # refresh loop, and its form does not move ---------------------------

    def _display_ctx(now=None):
        ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True,
                              "wake_interval_s": 900, "display_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
            "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        }
        if now is not None:
            ctx["now"] = now
        return ctx

    def _the_display_scope_refreshes_itself_from_the_same_builder():
        now = "2026-08-27T12:00:00+00:00"
        rendered = config_page.render(_display_ctx(now), scope=config_page.SCOPE_DISPLAY)
        built = layout.freshness_line_html(now)
        if built not in rendered:
            return False, (
                "expected the Display scope's freshness line to be layout.freshness_line_html()'s "
                "own output verbatim — the same builder Health and Home call, so the three pages "
                "cannot disagree about what a freshness line is. Built:\n%r" % (built,))
        for attr, want in (("data-loaded-at", 1), ("data-refresh-pill", 1)):
            if rendered.count(attr) != want:
                return False, (
                    "expected exactly %d %s on the Display scope — freshness.js reads the first "
                    "with a single querySelector and a second would silently win, got %d"
                    % (want, attr, rendered.count(attr)))
        # The loop's own gate: without the marker there is no loop, and
        # with a page key that declares no regions there is no swap.
        if layout.REFRESH_PAGE_DISPLAY not in layout.REFRESH_SWAP_SELECTORS_BY_PAGE:
            return False, "expected the Display scope to declare its own swap regions"
        shell = layout.page_shell(
            title="Display", active=layout.REFRESH_PAGE_DISPLAY, body=rendered)
        if ('%s="%s"' % (layout.REFRESH_PAGE_ATTR, layout.REFRESH_PAGE_DISPLAY)) not in shell:
            return False, "expected the Display document to carry its own page key on <body>"
        # A ctx with no render instant renders no freshness line at all
        # rather than an element carrying an empty or invented one — the
        # same degrade frame_strip_html() applies to a missing next wake.
        bare = config_page.render(_display_ctx(), scope=config_page.SCOPE_DISPLAY)
        if "data-loaded-at" in bare:
            return False, (
                "expected no freshness marker at all when the caller has no render instant — an "
                "element carrying an empty instant reads as a correct time to a script and is "
                "worse than no element")
        return True, ""
    check(
        "the Display scope renders layout.freshness_line_html()'s own output verbatim with exactly "
        "one data-loaded-at and one data-refresh-pill, declares its own swap regions, carries its "
        "page key on <body>, and renders no freshness marker at all when the caller has no render "
        "instant (D1/CFG-35, 23-06-PLAN.md Task 2)",
        _the_display_scope_refreshes_itself_from_the_same_builder)

    def _the_display_form_is_untouched_by_the_refresh_loop():
        # The one thing a swap must never touch. Display is a settings
        # page, and 22-01/B1 — this page rendered unsaveable with JS on —
        # is the defect of record this clause exists to keep closed.
        now = "2026-08-27T12:00:00+00:00"
        rendered = config_page.render(_display_ctx(now), scope=config_page.SCOPE_DISPLAY)
        for selector in layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_DISPLAY]:
            for banned in ("form", config_page.SETTINGS_FORM_ID, "dirty", "save"):
                if banned in selector:
                    return False, (
                        "the Display scope declares the swap region %r, which names %r — a swap "
                        "that lands on this page's form is the P0 Phase 22 existed to fix"
                        % (selector, banned))
        # The form, its cross-DOM attachment and the fallback Save are
        # all still rendered, unchanged by this plan's header edit.
        if ('<form class="config-form" method="post" id="%s"' % config_page.SETTINGS_FORM_ID) \
                not in rendered and ('id="%s"' % config_page.SETTINGS_FORM_ID) not in rendered:
            return False, "expected the settings form to still render on the Display scope"
        if ('form="%s"' % config_page.SETTINGS_FORM_ID) not in rendered:
            return False, (
                "expected the cross-DOM form= attachment B1 depends on to survive — every saved "
                "theme radio submits through it")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in rendered:
            return False, (
                "expected the fallback Save button to stay reachable — with scripts blocked it "
                "is the ONLY way to save this page")
        # The freshness line is in the page HEADER, above the form, and
        # the form is not inside it.
        header_at = rendered.index("page-header__freshness")
        form_at = rendered.index('id="%s"' % config_page.SETTINGS_FORM_ID)
        if header_at > form_at:
            return False, (
                "expected the freshness line in the page header, above the settings form, got "
                "it at %d with the form at %d" % (header_at, form_at))
        return True, ""
    check(
        "no Display swap region names a form, a dirty marker or a save control, and the settings "
        "form, its cross-DOM form= attachment and the fallback Save all still render with the "
        "freshness line above them in the page header — a swap landing on this page's form is the "
        "P0 Phase 22 existed to fix (B1/D1, 23-06-PLAN.md Task 2)",
        _the_display_form_is_untouched_by_the_refresh_loop)

    # ------------------------------------------------------------------
    # 25-05-PLAN.md Task 1 (CFG-49): D18's two gauges, server-rendered.
    #
    # The card showed neither side of the trade-off it exists for. These
    # three checks are about what the two new sentences may CLAIM, not
    # about whether they render: one of them can be true today and the
    # other one cannot, and the whole subject here is that the second
    # one says so.
    # ------------------------------------------------------------------

    # A daily-average battery series in server/history_db.py's own row
    # shape, oldest first (order does not matter — battery.py sorts).
    def _battery_series(*pairs):
        return [{"ts": ts, "battery_mv": mv, "reading_count": 3}
                for ts, mv in pairs]

    # Six shapes, each named for the answer it must produce. The three
    # that support NO figure are the point of the fixture: a series that
    # is rising (the device was charged), one whose span is a single day
    # (inside this series' own noise) and one with nothing in it at all.
    _FALLING = _battery_series(
        ("2026-09-01", 4100), ("2026-09-04", 3800), ("2026-09-07", 3600))
    _FALLING_ONE_DAY_LEFT = _battery_series(
        ("2026-09-05", 3600), ("2026-09-07", 3400))
    _RISING = _battery_series(
        ("2026-09-01", 3400), ("2026-09-04", 3700), ("2026-09-07", 4100))
    _ONE_DAY_SPAN = _battery_series(("2026-09-06", 4100), ("2026-09-07", 3900))
    _EMPTY = []

    def _the_two_gauges_claim_exactly_what_the_data_supports():
        """CFG-49 (25-05-PLAN.md Task 1): the freshness sentence is a
        BOUND and the battery sentence is an OBSERVATION — and the
        second one has to be able to say that it has nothing to say.

        The audit asked for "estimated battery life ≈ 38 days". That
        figure does not exist anywhere in this codebase: computing it
        needs a per-wake energy cost this project has never measured
        (DEVICE-05's discharge run is still open), so the only absolute
        figure permitted here is one derived from this device's OWN
        observed discharge slope, and every other case renders a named
        state instead.
        """
        min_s = device_config.WAKE_INTERVAL_MIN_S
        max_s = device_config.WAKE_INTERVAL_MAX_S

        # 1. THE BOUND, at both ends of the configured band and in the
        #    middle — and the words "at most" are part of the claim, not
        #    decoration: without them the sentence becomes a statement
        #    about TYPICAL behaviour, which nothing measures.
        bound_words = config_page.WAKE_FRESHNESS_TEXT.split(
            layout.VALUE_CONTROL_TEXT_TOKEN)[0].strip()
        if "at most" not in bound_words:
            return False, (
                "the freshness wording %r does not say 'at most' before its quantity — a bound "
                "stated without it is a claim about typical behaviour, and nothing in this "
                "project measures that" % config_page.WAKE_FRESHNESS_TEXT)
        for seconds, minutes in ((min_s, 1), (max_s, 60), (600, 10), (90, 2), (1800, 30)):
            said = config_page.wake_freshness_text(seconds)
            if bound_words not in said:
                return False, "wake_freshness_text(%d) = %r drops the bound" % (seconds, said)
            numbers = re.findall(r"\d+", said)
            if numbers != [str(minutes)]:
                return False, (
                    "wake_freshness_text(%d) names %r; %d seconds is %d whole minutes — and it "
                    "must round UP, because 'at most 1 min' is FALSE for a 90-second cadence"
                    % (seconds, numbers, seconds, minutes))

        # 2. THE ABSOLUTE FIGURE, AND IT IS battery.py's OWN. Recomputed
        #    from the estimator and required to appear verbatim, so a
        #    second days-remaining computation in the page module would
        #    have to agree with the first one to pass — and the fixture
        #    is checked to actually PRODUCE a figure first, or this
        #    whole clause would be vacuous.
        estimate = battery.battery_life_estimate(_FALLING, 600, 600)
        days = estimate["days_remaining"]
        if estimate["trend"] != battery.LIFE_TREND_FALLING or not isinstance(days, int):
            return False, (
                "the falling fixture no longer produces a figure (%r) — the clause below would "
                "pass against a card that never prints one" % (estimate,))
        said = config_page.wake_battery_observed_text(600, _FALLING)
        if str(days) not in re.findall(r"\d+", said):
            return False, (
                "the battery sentence %r does not carry battery_life_estimate()'s own figure "
                "(%d days) — the one estimate lives in companion/battery.py" % (said, days))
        if "≈" not in said:
            return False, (
                "the battery sentence %r drops the ≈ honesty marker this app already wears on "
                "the battery percentage — an observed projection is not a datasheet figure"
                % said)

        # THE SINGULAR, which is reachable (a nearly-empty battery) and
        # is the plural defect this project's i18n harness has caught
        # before.
        one_day = battery.battery_life_estimate(_FALLING_ONE_DAY_LEFT, 600, 600)
        if one_day["days_remaining"] != 1:
            return False, (
                "the one-day fixture reports %r days — the singular wording below would never "
                "be exercised" % (one_day["days_remaining"],))
        singular = config_page.wake_battery_observed_text(600, _FALLING_ONE_DAY_LEFT)
        if singular != i18n.t(config_page.WAKE_BATTERY_DAY_TEXT).replace(
                layout.VALUE_CONTROL_TEXT_TOKEN, "1"):
            return False, (
                "a one-day estimate renders %r rather than the singular wording — '1 days' is "
                "the missing-plural defect" % singular)

        # 3. THE THREE SHAPES THAT SUPPORT NO FIGURE AT ALL, each
        #    required to render the NAMED state — a real sentence, never
        #    a blank, and never a number.
        unknown = i18n.t(config_page.WAKE_BATTERY_UNKNOWN_TEXT)
        for name, rows in (("rising (the device was charged)", _RISING),
                           ("a one-day span", _ONE_DAY_SPAN),
                           ("no history at all", _EMPTY)):
            said = config_page.wake_battery_observed_text(600, rows)
            if said != unknown:
                return False, (
                    "with %s the battery sentence reads %r; it owes the named 'not enough "
                    "history yet' state, which is a rendered sentence rather than a blank"
                    % (name, said))
            if re.search(r"\d", said):
                return False, (
                    "with %s the battery sentence carries a number (%r) — a figure the data "
                    "cannot support is the dishonest state Phase 22 spent a phase removing"
                    % (name, said))
            if "-" in said.replace("—", "") and re.search(r"-\d", said):
                return False, "with %s the battery sentence carries a negative (%r)" % (name, said)

        # 4. NEITHER SENTENCE INVENTS A SUBJECT. No saved interval, no
        #    gauges — the same omit-don't-fabricate rule the `value`
        #    attribute and 25-04's handles already follow.
        for absent in (None, 0, True, "", "300"):
            if config_page.wake_gauge_interval_s(absent) is not None:
                return False, (
                    "wake_gauge_interval_s(%r) resolved to an interval — only a real int inside "
                    "the configured band is one" % (absent,))
        if config_page.wake_gauges_html(None, _FALLING) != "":
            return False, "the gauges rendered with no interval to describe"
        for out_of_band in (min_s - 1, max_s + 1):
            if config_page.wake_gauge_interval_s(out_of_band) is not None:
                return False, (
                    "wake_gauge_interval_s(%d) accepted a value outside [%d, %d]"
                    % (out_of_band, min_s, max_s))

        # 5. D-07's ECHO, AND ITS FLOOR. A rejected save's raw string is
        #    what the gauges describe — but only when it is a usable
        #    interval, because "at most 0 min" for a submitted "7" would
        #    describe a cadence this device cannot be configured to use.
        if config_page.wake_gauge_interval_s(600, {"wake_interval_s": "900"}) != 900:
            return False, (
                "a rejected save's echoed 900 is not what the gauges describe — the picture and "
                "the field must not disagree on the screen where a mistake is being fixed")
        for junk in ("7", "", "abc", "99999", "60.5", None):
            if config_page.wake_gauge_interval_s(600, {"wake_interval_s": junk}) is not None:
                return False, (
                    "an echoed %r produced a gauge subject — a gauge about a value this device "
                    "cannot use is a gauge about nothing" % (junk,))

        # 6. THE SCREEN-OFF CLAUSE, which is what keeps BOTH sentences
        #    from over-claiming: neither is in force while the screen is
        #    off, because server/wake.py pins DISPLAY_OFF_SLEEP_S ahead
        #    of this field entirely.
        off = config_page.wake_screen_off_text()
        if layout.duration_text(device_config.DISPLAY_OFF_SLEEP_S) not in off:
            return False, (
                "the screen-off clause %r does not name device_config.DISPLAY_OFF_SLEEP_S (%d s) "
                "through the app's own duration ladder"
                % (off, device_config.DISPLAY_OFF_SLEEP_S))
        card = config_page.wake_gauges_html(600, _FALLING)
        if escape_html(off) not in card:
            return False, (
                "the rendered gauges do not carry the screen-off clause — a visitor who has "
                "turned the screen off reads a battery claim that does not apply to their frame")
        return True, ""
    check(
        "the freshness gauge states a BOUND (\"at most\", rounded UP) naming the same whole "
        "minutes the interval implies at the band's minimum, its maximum and in between; the "
        "battery gauge prints an absolute figure ONLY when companion/battery.py's own estimate "
        "supports one — recomputed from the estimator, singular and plural both — and renders "
        "the NAMED \"not enough history yet\" sentence with no number at all for a rising, a "
        "one-day and an empty series; neither gauge renders without a usable interval, D-07's "
        "echo is honoured only where it is usable, and the screen-off cadence is stated "
        "(CFG-49, 25-05-PLAN.md Task 1)",
        _the_two_gauges_claim_exactly_what_the_data_supports)

    def _no_days_remaining_arithmetic_lives_outside_companion_battery():
        """CFG-49 (25-05-PLAN.md Task 1): the page module CALLS the
        estimate; it never computes one.

        `test_companion_app.py`'s one-home guard already catches a second
        estimate by NAME and by the millivolt-endpoint pair. This is the
        third net and the narrow one: the arithmetic itself — a division
        by an observed slope, or a distance to the empty endpoint —
        appearing anywhere under `companion/pages/`. Comments and
        docstrings are stripped first, for this file's own standing
        reason: the prose that explains the rule must neither satisfy
        nor break it.
        """
        banned = ("days_remaining", "mv_per_day", "BATTERY_EMPTY_MV",
                  "BATTERY_FULL_MV", "observed_span_days")
        pages_dir = os.path.join(HERE, "pages")
        for name in sorted(os.listdir(pages_dir)):
            if not name.endswith(".py"):
                continue
            for used in _python_identifiers(os.path.join(pages_dir, name)):
                if used in banned:
                    return False, (
                        "companion/pages/%s uses %r as an IDENTIFIER — the days-remaining "
                        "arithmetic has exactly one home and companion/pages is not it. "
                        "(Reading the estimator's own returned key back out of its dict is a "
                        "STRING, not an identifier, and is the one permitted shape.)"
                        % (name, used))
        # And the call itself is QUALIFIED, per references/
        # data-density.md: a bare `from companion.battery import
        # battery_life_estimate` makes the estimate read as the page's
        # own, which is the drift the shared module exists to prevent.
        names = _python_identifiers(os.path.join(HERE, "pages", "config_page.py"))
        if "battery_life_estimate" not in names:
            return False, (
                "config_page.py never names battery_life_estimate() — the battery gauge would "
                "then be reading its figure from somewhere else")
        import ast
        with open(os.path.join(HERE, "pages", "config_page.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("battery"):
                return False, (
                    "config_page.py imports %r OUT of companion.battery — the estimator is "
                    "called QUALIFIED so it can never read as this page's own "
                    "(references/data-density.md)"
                    % [alias.name for alias in node.names])
        # Every template this plan added carries the quantity mark the
        # script substitutes into, and is a real catalogue key.
        for template in (config_page.WAKE_FRESHNESS_TEXT,
                         config_page.WAKE_BATTERY_DAY_TEXT,
                         config_page.WAKE_BATTERY_DAYS_TEXT,
                         config_page.WAKE_BATTERY_INSTEAD_TEXT):
            if layout.VALUE_CONTROL_TEXT_TOKEN not in template:
                return False, (
                    "the template %r carries no %r — the script substitutes the quantity into it "
                    "and would render the sentence unchanged"
                    % (template, layout.VALUE_CONTROL_TEXT_TOKEN))
            for artefact in ("%s", "{}"):
                if artefact in template:
                    return False, (
                        "the template %r carries %r — these reach the browser as attribute "
                        "values and companion/test_i18n.py's Check 3 scans every French render "
                        "for exactly that artefact" % (template, artefact))
            if template not in i18n_fr.CATALOG:
                return False, "the template %r has no French sibling" % template
        return True, ""
    check(
        "no days-remaining arithmetic exists anywhere under companion/pages/ — every one of "
        "days_remaining/mv_per_day/observed_span_days/the two millivolt endpoints appears only "
        "as a read of the estimator's own returned dict, comments and docstrings stripped first "
        "— the estimate is called QUALIFIED off companion.battery, and every quantity template "
        "this card adds carries the \"#\" mark rather than a format artefact and has a French "
        "sibling (CFG-49/D-27, 25-05-PLAN.md Task 1)",
        _no_days_remaining_arithmetic_lives_outside_companion_battery)

    # ==================================================================
    # 27-06-PLAN.md Task 3 (CFG-67): the three texts, cut against
    # 27-01-SUMMARY.md's own recorded baselines (measured 360px,
    # rendered, both languages). Each check is ONE read of the region,
    # with every assertion made against that SAME read — "shorter" and,
    # where the honesty contract applies, "still refuses" are proven
    # about one rendering, never two separate ones (T-27-06-A).
    #
    # The forbidden pattern is scoped to the DAYS-CLAIM SHAPE itself
    # ("≈ <digits> day(s)/jour(s)"), never to "≈" near any digit —
    # 27-01-SUMMARY.md found the naive `≈\s*\d` pattern false-positives
    # on the wake-interval caption's own legitimate "(next wake ≈ 31
    # Jul 08:05)" text, a real derivable timestamp, not an invented
    # figure. That caption is a SEPARATE region from the gauges below in
    # any case, but the pattern is scoped correctly regardless.
    # ==================================================================

    _DAYS_FIGURE_PATTERN = re.compile(r"≈\s*\d+\s*(?:day|days|jour|jours)\b")

    def _html_region_text(fragment):
        """Strip tags, unescape entities, collapse whitespace — the
        python-side equivalent of reading `.textContent` off a rendered
        element, without a browser.
        """
        stripped = re.sub(r"<[^>]*>", "", fragment)
        return re.sub(r"\s+", " ", html.unescape(stripped)).strip()

    def _wake_interval_caption_is_shortened_in_both_languages():
        baseline = 220
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.wake_interval_group(
                    300, next_wake_clock="31 Jul 08:05")
            finally:
                prefs.set_request_prefs(lang="en")
            m = re.search(
                r'<p class="text-label section-caption" id="%s">(.*?)</p>'
                % re.escape(config_page.WAKE_INTERVAL_SECTION_CAPTION_ID), rendered)
            if not m:
                return False, "%s: #%s is missing from wake_interval_group()'s own markup" % (
                    lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID)
            text = _html_region_text(m.group(1))
            if len(text) >= baseline:
                return False, (
                    "%s: #%s renders %d character(s), against a recorded baseline of %d "
                    "(27-01-SUMMARY.md). The copy was not cut. It reads %r"
                    % (lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID, len(text), baseline,
                       text))
        return True, ""
    check(
        "the wake-interval caption (#wake-interval-caption) is materially shorter than "
        "27-01-SUMMARY.md's recorded 220-char baseline in BOTH languages — the mechanism and "
        "apply-timing sentences are cut, the derived \"(next wake ≈ ...)\" suffix (a real "
        "timestamp, not an invented figure) is untouched (CFG-67, 27-06-PLAN.md Task 3)",
        _wake_interval_caption_is_shortened_in_both_languages)

    def _wake_gauges_are_shortened_and_the_battery_refusal_survives_in_both_languages():
        baseline = 254
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                # No battery_rows: the insufficient-history state — the
                # one 27-01-SUMMARY.md's baseline was measured against,
                # and the one whose refusal this check must prove
                # survives on the SAME reading as the length.
                rendered = config_page.wake_gauges_html(300)
            finally:
                prefs.set_request_prefs(lang="en")
            segments = re.findall(
                r'<p class="[^"]*\bwake-gauge\b[^"]*"[^>]*>(.*?)</p>', rendered, re.S)
            if len(segments) != 2:
                return False, (
                    "%s: expected 2 .wake-gauge elements, found %d" % (lang, len(segments)))
            text = " ".join(_html_region_text(seg) for seg in segments)
            text = re.sub(r"\s+", " ", text).strip()
            # ONE READ, TWO ASSERTIONS, per T-27-06-A — both against
            # `text` as measured above, never a second re-render.
            if len(text) >= baseline:
                return False, (
                    "%s: .wake-gauge renders %d character(s) across %d element(s), against a "
                    "recorded baseline of %d (27-01-SUMMARY.md). The copy was not cut. It "
                    "reads %r" % (lang, len(text), len(segments), baseline, text))
            found = _DAYS_FIGURE_PATTERN.search(text)
            if found:
                return False, (
                    "%s: .wake-gauge did get shorter (%d character(s), under the %d baseline) "
                    "but the insufficient-history state now matches %r at %r — a shorter "
                    "sentence that starts claiming a figure this frame's own history cannot "
                    "support is a regression, not a cut. The whole region reads %r"
                    % (lang, len(text), baseline, _DAYS_FIGURE_PATTERN.pattern,
                       found.group(0), text))
        return True, ""
    check(
        "the two wake gauges (.wake-gauge) are materially shorter than 27-01-SUMMARY.md's "
        "recorded 254-char combined baseline in BOTH languages, and the insufficient-history "
        "state still prints NO absolute battery figure — asserted about the SAME reading the "
        "length is measured from, with the forbidden pattern scoped to the days-claim shape "
        "itself so it does not false-positive on an unrelated ≈-bearing timestamp (D18's "
        "honesty contract, CFG-67, 27-06-PLAN.md Task 3)",
        _wake_gauges_are_shortened_and_the_battery_refusal_survives_in_both_languages)

    def _quiet_hours_caption_is_shortened_and_the_delay_sentence_survives_in_both_languages():
        baseline = 188
        delay_sentence = "Applies at the next wake, around 31 Jul 08:05."
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.quiet_hours_group(
                    "23:00", "07:00", delay_sentence=delay_sentence)
            finally:
                prefs.set_request_prefs(lang="en")
            m = re.search(
                r'<p class="text-label section-caption" id="%s">(.*?)</p>'
                % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), rendered)
            if not m:
                return False, "%s: #%s is missing from quiet_hours_group()'s own markup" % (
                    lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID)
            text = _html_region_text(m.group(1))
            if len(text) >= baseline:
                return False, (
                    "%s: #%s renders %d character(s), against a recorded baseline of %d "
                    "(27-01-SUMMARY.md). The copy was not cut. It reads %r"
                    % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, len(text), baseline,
                       text))
            # delay_sentence carries LIVE STATE (frame_state.DELAY_UNKNOWN
            # by default), not explanation — the cut is scoped to
            # QUIET_HOURS_SECTION_CAPTION alone, and this asserts the
            # delay sentence survived it, on the SAME reading.
            if delay_sentence not in text:
                return False, (
                    "%s: #%s lost its own computed delay sentence (%r) — expected it to survive "
                    "the caption cut untouched, and it reads %r instead"
                    % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, delay_sentence, text))
        return True, ""
    check(
        "the Quiet hours paragraph (#quiet-hours-caption) is materially shorter than "
        "27-01-SUMMARY.md's recorded 188-char baseline in BOTH languages, with its own computed "
        "delay sentence — live state, not explanation, defaulting to i18n.t(frame_state."
        "DELAY_UNKNOWN) — asserted to survive the cut on the SAME reading (CFG-67, 27-06-PLAN.md "
        "Task 3)",
        _quiet_hours_caption_is_shortened_and_the_delay_sentence_survives_in_both_languages)

    def _the_gauges_are_an_addition_and_the_number_input_is_untouched():
        """CFG-49 (25-05-PLAN.md Task 1): the `<input type="number">` is
        the ONLY thing on this card that posts, and its `value`-attribute
        guard is load-bearing in a way no other field's is.

        An out-of-range `value` on a native numeric input fails HTML5
        constraint validation, which blocks submission of the ENTIRE
        Settings form — not just this field. That is live rather than
        hypothetical: `deploy/skypane.env.example` ships
        SKYPANE_SLEEP_S=30, below the 60 s floor, and plan 11-04 feeds
        that value in as the pre-fill fallback.

        The byte-identical diff against the pre-task builder was taken
        once, by hand, across four argument shapes (recorded in the
        SUMMARY). What lives here is the durable half.
        """
        min_s = device_config.WAKE_INTERVAL_MIN_S
        max_s = device_config.WAKE_INTERVAL_MAX_S
        expected_head = (
            '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
            ' placeholder="%s"' % (
                escape_html(config_page.WAKE_INTERVAL_INPUT_ID), min_s, max_s,
                escape_html(i18n.t(config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT))))
        # The fifth column is whether the gauges are owed at all: they
        # describe the value the FIELD will hold, so every shape where
        # the field deliberately shows nothing is a shape where the
        # gauges must show nothing either.
        cases = (
            ("saved, in band", 600, None, ' value="600"', True),
            ("stored BELOW the floor", 30, None, "", False),
            ("stored above the ceiling", max_s + 1, None, "", False),
            ("never set", None, None, "", False),
            ("a rejected save's raw echo", 600, {"wake_interval_s": "7"},
             ' value="7"', False),
            ("a rejected save echoing a usable value", 600,
             {"wake_interval_s": "900"}, ' value="900"', True),
        )
        for name, current, submitted, value_attr, owes_gauges in cases:
            markup = config_page.wake_interval_group(
                current, submitted=submitted, battery_rows=_FALLING)
            tag = re.search(r'<input type="number"[^>]*>', markup)
            if not tag:
                return False, "%s: no <input type=\"number\"> at all" % name
            element = tag.group(0)
            if not element.startswith(expected_head):
                return False, (
                    "%s: the number input is no longer byte-identical to its pre-plan output.\n"
                    "  expected it to start %r\n  got %r" % (name, expected_head, element))
            if value_attr and value_attr not in element:
                return False, "%s: expected %r in %s" % (name, value_attr, element)
            if not value_attr and " value=" in element:
                return False, (
                    "%s: the number input carries a value attribute (%s) — an out-of-range value "
                    "fails HTML5 constraint validation and blocks submission of the WHOLE "
                    "Settings form, not just this field" % (name, element))
            # THE LABEL, THE UNIT SIBLING AND THE ERROR BLOCK, in their
            # B17 order: label ABOVE the control, unit sibling directly
            # after it. The gauges are APPENDED after all of them.
            label = '<label for="%s">%s</label>' % (
                escape_html(config_page.WAKE_INTERVAL_INPUT_ID),
                escape_html(i18n.t("Wake interval (seconds)")))
            unit = ('<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
                    % escape_html(config_page.WAKE_INTERVAL_UNIT_LABEL))
            if label not in markup or unit not in markup:
                return False, "%s: the B17 label or the unit sibling changed" % name
            if markup.index(label) > markup.index(element):
                return False, "%s: the label is no longer ABOVE the control (B17)" % name
            if markup.index(unit) != markup.index(element) + len(element):
                return False, (
                    "%s: the unit sibling no longer sits immediately after the input — something "
                    "was inserted between them" % name)
            gauge_at = markup.find('id="%s"' % config_page.WAKE_GAUGE_FRESHNESS_ID)
            if owes_gauges and gauge_at == -1:
                return False, "%s: the gauges did not render" % name
            if not owes_gauges and gauge_at != -1:
                return False, (
                    "%s: a gauge rendered for a value the field itself refuses to show — that "
                    "is the card inventing a subject" % name)
            if gauge_at != -1 and gauge_at < markup.index(unit):
                return False, (
                    "%s: a gauge renders BEFORE the control it describes — they are appended "
                    "after the error block, which is what makes the rest of the card an "
                    "untouched prefix" % name)
        # A STORED value below the floor still renders both gauges off
        # the value the FIELD will hold, which is nothing — so nothing
        # claims a cadence that was never set.
        # The error block still attaches to the field, with the gauges
        # after it.
        with_error = config_page.wake_interval_group(
            600, errors={"wake_interval_s": "Enter a whole number of seconds."},
            submitted={"wake_interval_s": "900"}, battery_rows=_FALLING)
        # LOCATED BY ITS OWN ELEMENT, never by the bare id string: the
        # input's aria-describedby NAMES that id too, and the first
        # version of this clause found THAT — so it read a position
        # inside the input tag and passed against the gauges rendered
        # between the input and its error message, which is the one
        # arrangement it exists to refuse (measured; see the SUMMARY's
        # vacuity section).
        error_block = re.search(
            r'<p class="field-error[^"]*" id="wake-interval-s-error"', with_error)
        if not error_block:
            return False, "the field error block no longer renders"
        gauge_at = with_error.find('id="%s"' % config_page.WAKE_GAUGE_BATTERY_ID)
        if gauge_at == -1:
            return False, "the gauges did not render beside a rejected save's usable echo"
        if gauge_at < error_block.start():
            return False, (
                "a gauge renders between the input and its own error message (gauge at %d, "
                "error block at %d) — the message has to read as attached to the control it is "
                "about" % (gauge_at, error_block.start()))
        return True, ""
    check(
        "the two gauges are an ADDITION: across five argument shapes (in band, stored below the "
        "60s floor, stored above the ceiling, never set, and a rejected save's raw echo) the "
        "<input type=\"number\"> is byte-identical to its pre-plan output — same id, name, min, "
        "max and placeholder, the value attribute present exactly when the guard admits it and "
        "absent otherwise (an out-of-range value blocks submission of the ENTIRE form) — with "
        "B17's label still above it, the unit sibling still immediately after it, the error "
        "block still attached, and both gauges appended after all of them "
        "(CFG-49/D-07/B17, 25-05-PLAN.md Task 1)",
        _the_gauges_are_an_addition_and_the_number_input_is_untouched)

    # ------------------------------------------------------------------
    # 25-05-PLAN.md Task 2 (CFG-49/CFG-52): the gated range, and the
    # seam it shares with the one script.
    # ------------------------------------------------------------------

    def _the_range_is_gated_nameless_and_bounded_by_device_config():
        """CFG-49/CFG-52 (25-05-PLAN.md Task 2): the range may never
        become a second source of truth, and it may never widen what the
        number input enforces.

        `name` is the attribute a future editor adds by reflex — it is
        what every other input on this page carries — and a named range
        would post a SECOND `wake_interval_s` on every save, with
        whichever arrived last winning, silently. So it is asserted
        directly rather than inferred from "the form posts one value".
        """
        markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
        tag = re.search(r'<input type="range"[^>]*>', markup)
        if not tag:
            return False, "no <input type=\"range\"> renders on the card"
        element = tag.group(0)
        if re.search(r"\bname=", element):
            return False, (
                "the range carries a name (%s) — it would post a second value for the same "
                "setting and whichever arrived last would win, silently" % element)
        if "role=" in element:
            return False, (
                "the range carries a role (%s) — a native range input IS a slider, with its own "
                "aria-valuenow and its own keyboard model; role=\"slider\" on top of that is the "
                "double-role error" % element)
        # THE BOUNDS ARE READ FROM THE MODULE, never restated: one
        # control must not accept what the other, and
        # save_device_config()'s own server-side re-check, reject.
        for attr, expected in (("min", device_config.WAKE_INTERVAL_MIN_S),
                               ("max", device_config.WAKE_INTERVAL_MAX_S),
                               ("step", config_page.WAKE_SLIDER_STEP_S),
                               ("value", 600)):
            if ('%s="%d"' % (attr, expected)) not in element:
                return False, (
                    "the range's %s is not %d — %s" % (attr, expected, element))
        if config_page.WAKE_SLIDER_STEP_S != config_page.WAKE_GAUGE_SECONDS_PER_MINUTE:
            return False, (
                "the slider steps by %d s while the gauges speak in %d-second minutes — every "
                "position the slider can reach has to be a whole number of minutes, or the "
                "sentences round and the reader sees a number that does not match the field"
                % (config_page.WAKE_SLIDER_STEP_S, config_page.WAKE_GAUGE_SECONDS_PER_MINUTE))
        # The accessible name is its OWN, and it points at the gauges.
        for needed in ('aria-label="%s"' % escape_html(i18n.t(config_page.WAKE_SLIDER_LABEL)),
                       'aria-describedby="%s %s"' % (config_page.WAKE_GAUGE_FRESHNESS_ID,
                                                     config_page.WAKE_GAUGE_BATTERY_ID)):
            if needed not in element:
                return False, "the range is missing %r — %s" % (needed, element)
        if i18n.t(config_page.WAKE_SLIDER_LABEL) == i18n.t("Wake interval (seconds)"):
            return False, (
                "the range and the number input share one accessible name — a screen-reader "
                "visitor cannot tell which of the two they are on")
        # EVERY element carrying the wrapper attribute carries the gate
        # class, AND the range itself lives inside one. The second half
        # is what a wrapper-only scan is blind to.
        for tag_match in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
            text = tag_match.group(0)
            if layout.VALUE_CONTROL_ATTR not in text:
                continue
            if layout.JS_GATE_CLASS not in text:
                return False, (
                    "an element carries %s outside the %r gate: %s"
                    % (layout.VALUE_CONTROL_ATTR, layout.JS_GATE_CLASS, text))
        gate_at = markup.find(layout.JS_GATE_CLASS)
        gate_end = markup.find("</div>", gate_at)
        if not (gate_at != -1 and gate_at < markup.index(element) < gate_end):
            return False, (
                "the range is rendered outside the gated wrapper (gate at %d, range at %d, "
                "wrapper closes at %d) — a script-only affordance rendered without the gate "
                "shows permanently whenever the script does not run"
                % (gate_at, markup.index(element), gate_end))
        if markup.count('<input type="range"') != 1:
            return False, "the card renders %d ranges" % markup.count('<input type="range"')
        # NOT A LIVE REGION, anywhere on this card (CFG-52): the gauges
        # change on every step of a drag, and a live region would
        # re-announce the identical phrase continuously — the defect
        # Phase 23 hit with its three switches.
        # (`role="alert"` is deliberately NOT in this list: the field's
        # own error message wears it, renders only on a rejected save,
        # and says something once rather than on every step.)
        for banned in ("aria-live", 'role="status"'):
            if banned in markup:
                return False, (
                    "the wake-interval card carries %r — the gauges move on every step of a "
                    "drag and would flood a screen reader" % banned)
        # AND NOTHING AT ALL when there is no saved interval: the range
        # would otherwise default to the midpoint of its own band, which
        # is a fabricated position a drag would then SAVE.
        empty = config_page.wake_interval_group(None, battery_rows=_FALLING)
        if "<input type=\"range\"" in empty or layout.VALUE_CONTROL_ATTR in empty:
            return False, (
                "a range renders with no saved interval — a range with no value attribute sits "
                "at the midpoint of its band, which is a number nobody chose and which one drag "
                "would save")
        return True, ""
    check(
        "the wake-interval range is NAMELESS (a named one would post a second value for the "
        "same setting and the last to arrive would win), carries no role=\"slider\" on top of a "
        "native slider, takes its min/max from server.device_config rather than a literal, steps "
        "by exactly the minute both gauges speak in, has its own accessible name and describes "
        "itself by the two gauges, renders ONLY inside 25-01's .js gate and only when there is a "
        "saved interval to start from, and nothing on the card is a live region "
        "(CFG-49/CFG-52/T-25-05-D, 25-05-PLAN.md Task 2)",
        _the_range_is_gated_nameless_and_bounded_by_device_config)

    def _the_readout_seam_this_card_declares_is_the_one_the_script_reads():
        """CFG-49 (25-05-PLAN.md Task 2): both halves of a seam, pinned
        together — the markup this page emits and the script that
        consumes it.

        A rename on either side alone is a gauge that renders once and
        then never moves again, which no string comparison on the
        rendered page would notice: the sentence would be perfectly
        correct at load and permanently stale afterwards.
        """
        markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
        with open(os.path.join(HERE, "static", "value-controls.js"),
                  encoding="utf-8") as fh:
            script = fh.read()
        # 1. Every attribute this card emits is one the script names.
        for attr in (layout.VALUE_CONTROL_INPUT_ATTR, layout.VALUE_CONTROL_READOUT_ATTR,
                     layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
                     layout.VALUE_CONTROL_READOUT_SCALE_ATTR,
                     layout.VALUE_CONTROL_READOUT_BASE_ATTR):
            if attr not in markup:
                return False, "the card emits no %r" % attr
            if ('"%s"' % attr) not in script:
                return False, (
                    "value-controls.js never names %r, so the markup's own attribute is read by "
                    "nothing and the gauge is correct at load and stale for ever after" % attr)
        # 2. The readouts name the field the form actually posts.
        for match in re.finditer(
                r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR), markup):
            if match.group(1) != config_page.WAKE_INTERVAL_FIELD_NAME:
                return False, (
                    "a readout describes %r, which is not the field this form posts (%r)"
                    % (match.group(1), config_page.WAKE_INTERVAL_FIELD_NAME))
        # 3. THE SCRIPT ROUNDS THE SAME WAY THE SERVER DOES. Both state
        #    a BOUND, so both take the CEILING; a floor on either side
        #    would print "at most 1 min" for a 90-second cadence, which
        #    is false.
        if "Math.ceil(value / scale)" not in script:
            return False, (
                "value-controls.js does not take the CEILING of value/scale — the server does "
                "(_wake_minutes()), and a script that floored it would print a bound that is "
                "not true")
        # 4. A WRAPPER WITH A MIRROR TAKES NO GESTURES FROM THE SCRIPT.
        #    Without this the pointerdown handler's own preventDefault()
        #    cancels the native thumb drag and the slider is immovable by
        #    pointer, with every string comparison still green.
        if "function steeredHere(wrapper)" not in script:
            return False, (
                "value-controls.js has no mirror guard — its pointerdown handler calls "
                "preventDefault(), which cancels a native range's own thumb drag outright")
        for listener in ("keydown", "pointerdown", "pointermove"):
            block = script[script.index('document.addEventListener("%s"' % listener):]
            block = block[:block.index("});")]
            if "steeredHere(wrapper)" not in block:
                return False, (
                    "value-controls.js's %s listener does not stand aside for a wrapper with a "
                    "mirror — a native range would be stepped twice per key or pinned in place "
                    "by a prevented default" % listener)
        # 5. The BASE is the saved interval, so the relative clause says
        #    nothing at all until the visitor proposes something else —
        #    which is what every page load and every scripts-blocked
        #    render is.
        base = re.search(r'%s="(\d+)"' % re.escape(layout.VALUE_CONTROL_READOUT_BASE_ATTR),
                         markup)
        if not base or int(base.group(1)) != 600:
            return False, (
                "the relative readout's base is %r, not the saved interval — a readout with no "
                "base compares the saved value with itself on every page load"
                % (base.group(1) if base else None,))
        span = re.search(
            r'<span %s="[^"]*"[^>]*></span>' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR),
            markup)
        if not span:
            return False, (
                "the relative clause is not EMPTY at the saved value — the server renders the "
                "saved interval against itself, and 'every 10 min instead of every 10 min' "
                "would be noise on every page load")
        # 6. THE HONESTY CLAUSE, structural: no readout template on this
        #    card contains a days figure or its wording, so no script
        #    that only substitutes into templates can invent one.
        days_words = [w for w in (i18n.t(config_page.WAKE_BATTERY_DAYS_TEXT),
                                  i18n.t(config_page.WAKE_BATTERY_DAY_TEXT))]
        for match in re.finditer(
                r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_TEXT_ATTR), markup):
            template = html.unescape(match.group(1))
            for wording in days_words:
                stem = wording.split(layout.VALUE_CONTROL_TEXT_TOKEN)[-1].strip()
                if stem and stem in template:
                    return False, (
                        "a readout template carries the days wording (%r) — the absolute figure "
                        "is server-rendered from observed history, and a template containing it "
                        "is a script that can invent one" % template)
        return True, ""
    check(
        "the readout seam is pinned from BOTH sides: every attribute this card emits is named in "
        "companion/static/value-controls.js and vice versa, every readout describes the field "
        "the form actually posts, the script takes the same CEILING the server does (a floor "
        "would print a bound that is false), all three gesture listeners stand aside for a "
        "wrapper holding a native mirror (without which preventDefault cancels the thumb drag), "
        "the relative clause's base is the saved interval so it renders EMPTY until something "
        "else is proposed, and no readout template contains the days wording at all — so a "
        "script that only substitutes into templates cannot invent a figure the server declined "
        "to state (CFG-49/T-25-05-C, 25-05-PLAN.md Task 2)",
        _the_readout_seam_this_card_declares_is_the_one_the_script_reads)

    # ------------------------------------------------------------------
    # 25-06-PLAN.md Task 2 (CFG-50): D5's theme carousel — the departures
    # grid presented as a scroll-snap strip, around the ONE chip
    # renderer.
    # ------------------------------------------------------------------

    def _the_departures_grid_is_the_one_renderer_presented_as_a_strip():
        # THE PROPERTY UNDER TEST IS THAT NOTHING WAS FORKED. A carousel
        # that copied _theme_chip_grid_html() would pass every markup
        # assertion below on its own copy while the arrivals grid drifted
        # away from it — so the first clause is a SOURCE scan for a
        # second renderer, and the last is the three unconverted grids.
        module_src = open(
            os.path.join(REPO_ROOT, "companion", "pages", "config_page.py")).read()
        module_lines = module_src.split("\n")
        emitters = []
        for node in ast.walk(ast.parse(module_src)):
            if not isinstance(node, ast.FunctionDef):
                continue
            text = "\n".join(module_lines[node.lineno - 1:node.end_lineno])
            # `data-preview-src` is the chip's signature: it is the
            # attribute companion/static/theme-preview.js reads off a
            # chip's own <label> to swap the big live preview, so a
            # second chip renderer either emits it (and is caught here)
            # or silently breaks the live preview for its own chips.
            if "data-preview-src" in text and "<label" in text:
                emitters.append(node.name)
        if emitters != ["_theme_chip_grid_html"]:
            return False, (
                "expected exactly ONE function in config_page.py to emit a chip <label> "
                "carrying data-preview-src, got %r — four call sites share that renderer, and "
                "a second one is how the arrivals grid and the departures grid come to "
                "disagree about what a selected chip looks like" % (emitters,))

        card = config_page._frame_colours_card_html({}, "white", None, None)
        theme_count = len(device_config.THEME_IDS)

        # 27-07-PLAN.md Task 2 (CFG-68): GENERALISED FROM DEPARTURES-ONLY
        # TO ALL THREE. Departures has no leading chip (theme_count
        # radios); arrivals/calendar each prepend a "Same as departures"
        # chip submitting the empty string (D-09), so theme_count + 1.
        if card.count("theme-chip-grid--strip") != 3:
            return False, (
                "the card renders %d strips — Task 2 folds exactly three grids (departures, "
                "arrivals, calendar) into carousels, and the rule-add form's own grid stays "
                "out (see its own call site's comment)" % card.count("theme-chip-grid--strip"))
        strips = (
            ("theme", config_page.THEME_CAROUSEL_STRIP_ID, theme_count),
            ("theme_arriving", config_page.THEME_CAROUSEL_STRIP_ID_ARRIVALS, theme_count + 1),
            ("calendar_theme_id", config_page.THEME_CAROUSEL_STRIP_ID_CALENDAR, theme_count + 1),
        )
        departures_strip_open = None
        for field, strip_id, expected_radios in strips:
            # The strip IS the radiogroup: one grid div, carrying the
            # compact modifier it already had, the strip modifier, the
            # role, and ITS OWN id (the property the id-uniqueness check
            # elsewhere on this page proves is unique across all three).
            strip_open = re.search(
                r'<div class="([^"]*theme-chip-grid--strip[^"]*)"([^>]*id="%s"[^>]*)>'
                % re.escape(strip_id), card)
            if not strip_open:
                return False, (
                    "field=%r: no .theme-chip-grid--strip carrying id=%r is rendered — the "
                    "pagers' aria-controls would name nothing" % (field, strip_id))
            if field == "theme":
                departures_strip_open = strip_open
            classes = strip_open.group(1).split()
            attrs = strip_open.group(2)
            for required in ("theme-chip-grid", "theme-chip-grid--compact"):
                if required not in classes:
                    return False, (
                        "field=%r: the strip's class list is %r — it dropped %r, so the "
                        "carousel replaced the grid instead of laying it out"
                        % (field, classes, required))
            if 'role="radiogroup"' not in attrs:
                return False, (
                    "field=%r: the strip carries no role=\"radiogroup\" — %r" % (field, attrs))

            # The chips inside it are the renderer's own, unchanged.
            radios = re.findall(
                r'<input type="radio" name="%s" value="([^"]*)" class="visually-hidden"'
                r' form="([^"]*)"' % re.escape(field), card)
            if len(radios) != expected_radios:
                return False, (
                    "field=%r: expected %d visually-hidden, form-associated radios, got %d — "
                    "the strip must be the SAME native radio group, never a second set"
                    % (field, expected_radios, len(radios)))
            for _value, form in radios:
                if form != config_page.SETTINGS_FORM_ID:
                    return False, (
                        "field=%r: a strip radio carries form=%r, not %r — this card is a "
                        "SIBLING of the settings form, so without that attribute it posts "
                        "nowhere" % (field, form, config_page.SETTINGS_FORM_ID))

        # Departures' own radios, specifically, are in THEME_IDS'
        # registry order — the one field with no leading chip, so order
        # is a direct comparison.
        departures_radios = re.findall(
            r'<input type="radio" name="theme" value="([^"]*)" class="visually-hidden"'
            r' form="([^"]*)"', card)
        if [value for value, _form in departures_radios] != list(device_config.THEME_IDS):
            return False, (
                "the departures strip's radios are %r, not device_config.THEME_IDS in "
                "registry order" % ([value for value, _form in departures_radios],))
        if "display:none" in card or "display: none" in card:
            return False, (
                "the card emits a display:none — a radio hidden that way leaves the tab "
                "order, and arrow-key selection with it")

        # The swatch legend still renders under the departures grid and
        # OUTSIDE the element carrying role="radiogroup", with its
        # shipped copy — arrivals/calendar's own legend placement is
        # covered by 22-10-PLAN.md Task 1's own check (unaffected by
        # carousel wrapping: _theme_carousel_html() interpolates
        # grid_html, legend included, unchanged).
        legend = '<p class="text-label section-caption">%s</p>' % html.escape(
            config_page.THEME_CHIP_SWATCH_LEGEND, quote=False)
        strip_close = card.index("</div>", departures_strip_open.end())
        if legend not in card:
            return False, (
                "the swatch legend's shipped copy %r is not in the card"
                % (config_page.THEME_CHIP_SWATCH_LEGEND,))
        if card.index(legend) < strip_close:
            return False, (
                "the swatch legend renders INSIDE the element carrying role=\"radiogroup\" — "
                "a stray non-radio child is announced inside the group")

        # And the ONE grid this plan deliberately did not convert.
        if config_page._rule_add_form_html().count("theme-chip-grid--strip"):
            return False, "the rule-add form's own chip grid was converted too"
        return True, ""
    check(
        "departures/arrivals/calendar are all the ONE renderer's own output laid out as "
        "scroll-snap strips, never a fork: a source scan of config_page.py finds exactly one "
        "function emitting a chip <label> with data-preview-src, each strip keeps both the "
        "base and the compact grid classes plus role=\"radiogroup\" and ITS OWN id, each holds "
        "the right radio count for its field (theme_count for departures, +1 for arrivals/"
        "calendar's leading 'Same as departures' chip) each carrying form=\"settings-form\" "
        "(one set per field, never two), departures' own radios are in registry order, no "
        "display:none appears anywhere on the card, the swatch legend still renders after the "
        "departures radiogroup with its shipped copy, and exactly three of the card's four "
        "grids are converted — the rule-add form's stays out (CFG-50, 25-06-PLAN.md Task 2; "
        "generalised to arrivals/calendar, CFG-68, 27-07-PLAN.md Task 2)",
        _the_departures_grid_is_the_one_renderer_presented_as_a_strip)

    def _the_carousel_dots_are_real_colours_and_the_strip_rules_are_declared():
        card = config_page._frame_colours_card_html({}, "white", None, None)
        theme_count = len(device_config.THEME_IDS)
        dots_open = re.search(
            r'<div class="theme-carousel__dots ([^"]*)" aria-hidden="true">', card)
        if not dots_open:
            return False, (
                "no aria-hidden .theme-carousel__dots row is rendered — a dots row that is "
                "announced repeats eighteen radios' state in eighteen wordless nodes")
        if "theme-chip__swatches" not in dots_open.group(1).split():
            return False, (
                "the dots row does not reuse .theme-chip__swatches (%r) — a second swatch-row "
                "geometry is a second set of numbers to keep in step"
                % (dots_open.group(1),))
        row_end = card.index("</div>", dots_open.end())
        row = card[dots_open.end():row_end]
        found = re.findall(
            r'<span class="theme-chip__dot" style="background:([^"]*)"></span>', row)
        expected = [
            config_page._palette_hex(device_config.THEMES[t]["departing_index"])
            for t in device_config.THEME_IDS]
        if found != expected:
            return False, (
                "the dots row carries %r, expected one dot per theme in registry order "
                "carrying that theme's own _palette_hex(departing_index) %r — a dot row that "
                "is not the registry's own colours is decoration measuring nothing"
                % (found, expected))
        if len(found) != theme_count:
            return False, (
                "expected %d dots, got %d" % (theme_count, len(found)))
        # AND MORE THAN ONE COLOUR IN THE ROW, WHICH IS THE FLOOR RATHER
        # THAN THE CEILING. Measured on this registry while writing this
        # check: every one of the eighteen themes has
        # `departing_index == arriving_index`, and the eighteen resolve to
        # only SEVEN distinct hexes. So "the dots carry the departing ink"
        # and "the dots carry the arriving ink" are the same assertion
        # here — swapping one for the other in the renderer changes not a
        # byte of output, and was run and confirmed to change nothing.
        # What a wrong implementation WOULD do is read one fixed palette
        # index for every dot, which this clause and the equality above
        # both catch.
        if len(set(found)) < 2:
            return False, (
                "all %d dots are the same colour (%r) — the row is reading one fixed palette "
                "index rather than each theme's own" % (len(found), found[:1]))
        # NO SELECTION STATE, ASSERTED AS A FLOOR RATHER THAN LEFT
        # IMPLIED. A server-rendered "active dot" would be marking the
        # SAVED theme and would be visibly wrong the instant a chip is
        # clicked with scripts blocked; see _theme_carousel_html()'s
        # docstring for the whole argument.
        if "theme-carousel__dot--" in card or "--selected" in row:
            return False, (
                "a dot carries a selected-state modifier — with no script and no :has() chain "
                "it can only ever mark the SAVED theme, and would be wrong the moment a "
                "different chip is clicked")

        source = _read_static("style.css")
        strip_rules = {
            # 27-07-PLAN.md Task 1 (CFG-68/D-20): anchored with a
            # leading "\n" and NO indent, deliberately — the file's own
            # single @supports selector(:has(*)) block now ALSO carries
            # a compound selector ending in this exact class
            # (".theme-carousel:has(...) .theme-chip-grid--strip {"),
            # 2-space indented and textually earlier in the file than
            # this base rule. A bare `.theme-chip-grid--strip {` search
            # would find that compound selector FIRST and read ITS body
            # (flex-wrap: wrap, not nowrap) instead of this rule's —
            # measured: this is exactly the failure the standing
            # "locate by first occurrence" convention warns about, and
            # it was caught here by running this check, not reasoned
            # about in advance.
            "\n.theme-chip-grid--strip {": (
                "flex-wrap: nowrap;", "overflow-x: auto;",
                "scroll-snap-type: x mandatory;", "scroll-padding-right:"),
            ".theme-chip-grid--strip > .theme-chip {": (
                "flex: 0 0 auto;", "scroll-snap-align: start;"),
            ".theme-carousel__dots {": (
                "flex-wrap: wrap;", "margin-top: var(--space-sm);"),
            # THE TWO HALVES OF THE GRID-BLOWOUT FIX, pinned here
            # because each of them looks redundant beside the other and
            # neither is. Measured on this tree with the strip in place:
            # with only one of the two, documentElement.scrollWidth read
            # 2049 against a client width of 360 — the page itself
            # scrolling sideways by 1689px, which is the floor CFG-52
            # forbids. `1fr` is `minmax(auto, 1fr)` and an auto minimum
            # is the item's min-content; a <fieldset> re-introduces the
            # same minimum one level down through the UA's own
            # `min-inline-size: min-content`. The browser harness
            # measures the OUTCOME; this pins the two declarations that
            # produce it, so deleting either fails here as well.
            ".frame-colours__layout {": ("grid-template-columns: minmax(0, 1fr);",),
            ".frame-colours__usage-panel {": ("min-width: 0;",),
        }
        for selector, declarations in strip_rules.items():
            if selector not in source:
                return False, "style.css declares no %s rule" % selector.strip(" {\n")
            body = source[source.index(selector) + len(selector):]
            body = body[:body.index("}")]
            for declaration in declarations:
                if declaration not in body:
                    return False, (
                        "%s does not declare %r — %r"
                        % (selector.strip(" {\n"), declaration, body.strip()))

        # THE TWO NUMBERS THAT HAVE TO BE THE SAME NUMBER. The strip's
        # `scroll-padding-right` exists to keep the chip a keyboard
        # visitor just selected fully inside the scrollport: focus lands
        # on a 1px visually-hidden radio at the chip's top-left corner,
        # so the browser scrolls that into view and stops, leaving the
        # chip itself hanging off the right edge (measured at 360px: the
        # focused chip at left 224 inside a 278px strip). The reserved
        # width must be one chip's width, and the chip's width is
        # declared by `.theme-chip--compact`. Read BOTH out of the
        # stylesheet and compare, so a density pass that changes one
        # fails here rather than silently re-breaking the keyboard.
        def _px(selector, prop):
            if selector not in source:
                return None
            body = source[source.index(selector) + len(selector):]
            body = body[:body.index("}")]
            hit = re.search(r"(?m)^\s*%s:\s*(\d+(?:\.\d+)?)px;" % re.escape(prop), body)
            return float(hit.group(1)) if hit else None
        # Same anchoring as strip_rules above, and for the identical
        # reason: an un-anchored search would find the @supports block's
        # compound selector first.
        reserved = _px("\n.theme-chip-grid--strip {", "scroll-padding-right")
        chip_width = _px(".theme-chip--compact {", "width")
        if reserved is None or chip_width is None:
            return False, (
                "could not read both numbers: scroll-padding-right=%r, "
                ".theme-chip--compact width=%r" % (reserved, chip_width))
        if reserved != chip_width:
            return False, (
                "the strip reserves %gpx at its end edge but a compact chip is %gpx wide — "
                "the reservation exists to fit exactly one chip, and any other number leaves "
                "the chip a keyboard visitor just selected partly outside the scrollport"
                % (reserved, chip_width))

        # .theme-chip--compact STAYS SIZE-ONLY. The design system records
        # that every selected-state rule reaches a compact chip from the
        # BASE selectors automatically; one rule here and that contract
        # is broken silently.
        # COMMENTS STRIPPED FIRST, and that is not tidiness: the block
        # comment ABOVE `.theme-chip--compact` explains at length why the
        # modifier declares no `:has(input:checked)` rule, so a scan over
        # the raw source reports the rule's own justification as the
        # violation. Measured — this check failed exactly that way once.
        rules = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
        for match in re.finditer(r"([^{}]*)\{([^{}]*)\}", rules):
            selector, body = match.group(1), match.group(2)
            if "theme-chip--compact" not in selector:
                continue
            for banned in ("--selected", ":checked", ":has("):
                if banned in selector:
                    return False, (
                        "a .theme-chip--compact rule carries %r in its selector (%r) — the "
                        "compact modifier is SIZE-ONLY and inherits every selected-state rule "
                        "from the base .theme-chip selectors"
                        % (banned, selector.strip()))
        return True, ""
    check(
        "the carousel's dots row is aria-hidden, reuses .theme-chip__swatches/.theme-chip__dot "
        "rather than inventing a second swatch geometry, carries exactly one dot per theme in "
        "registry order painted with that theme's OWN _palette_hex(departing_index), and "
        "carries no selected-state modifier at all (with no script and no :has() chain it "
        "could only ever mark the SAVED theme); and style.css declares the strip's nowrap / "
        "overflow-x / scroll-snap-type, its chips' flex: 0 0 auto and scroll-snap-align, and "
        "the dots row's own wrap and top margin — with .theme-chip--compact still declaring no "
        "selected-state rule of any kind (CFG-50/CFG-52, 25-06-PLAN.md Task 2)",
        _the_carousel_dots_are_real_colours_and_the_strip_rules_are_declared)

    def _the_full_grid_sits_behind_a_native_details_and_the_pagers_behind_the_gate():
        # THE DUPLICATION QUESTION, ASSERTED RATHER THAN ASSUMED. The
        # whole page — not merely the card — must carry exactly
        # len(THEME_IDS) radios named `theme`. Two sets would share a
        # name and a form and so still post one value, but the page
        # would show a selection in two places, carry two --selected
        # chips and two copies of every chip image, for a setting with
        # one value (T-25-06-B).
        # SCOPE_DISPLAY, not the default SCOPE_ALL: the Frame colours
        # card is Display's, and the legacy SCOPE_ALL render (never
        # served) carries no theme radio at all — measured, and a page
        # with zero of them would make every count below pass for the
        # wrong reason.
        page = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        theme_count = len(device_config.THEME_IDS)
        posted = len(re.findall(r'<input type="radio" name="theme" ', page))
        if posted != theme_count:
            return False, (
                "the Display page renders %d radios named 'theme', expected exactly %d — the "
                "strip and the full grid are ONE set of radios, and a second set is two places "
                "showing one setting" % (posted, theme_count))

        # A NATIVE <details>, AND NOT A <dialog>. A dialog has no way to
        # open without script, so eighteen themes behind one is eighteen
        # themes behind a dead control — the exact defect this phase
        # exists to prevent.
        if "<dialog" in page:
            return False, (
                "the Display page renders a <dialog> — a dialog cannot be opened without "
                "script, and this disclosure is deliberately a native <details> instead "
                "(25-RESEARCH.md Decision 4)")
        # 27-07-PLAN.md Task 2 (CFG-68): GENERALISED FROM ONE CAROUSEL TO
        # THREE, scoped per USAGE PANEL rather than page-wide — each
        # panel's own segment (bounded by the NEXT panel's
        # data-usage-panel-target marker, the same delimiter
        # _calendar_theme_chip_grid_exactly_one_compact_radiogroup_
        # populated_in_order already uses) contains exactly one
        # carousel, so scoping to it is also THE RELATIONSHIP check
        # Task 2 asks for: each pager's aria-controls is asserted to
        # resolve to the strip id inside THIS SAME segment, never
        # merely "some strip id exists somewhere on the page" — a pager
        # wired to a DIFFERENT carousel's strip would pass a page-wide
        # existence check and fail this one.
        panel_markers = [
            (config_page.COLOUR_USAGE_DEPARTURES, config_page.THEME_CAROUSEL_STRIP_ID),
            (config_page.COLOUR_USAGE_ARRIVALS, config_page.THEME_CAROUSEL_STRIP_ID_ARRIVALS),
            (config_page.COLOUR_USAGE_CALENDAR, config_page.THEME_CAROUSEL_STRIP_ID_CALENDAR),
        ]
        boundaries = [config_page.COLOUR_USAGE_ARRIVALS, config_page.COLOUR_USAGE_CALENDAR,
                      config_page.COLOUR_USAGE_RULES]
        for (usage, strip_id), next_usage in zip(panel_markers, boundaries):
            seg_start = page.index(
                '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, usage))
            seg_end = page.index(
                '%s="%s"' % (config_page.COLOUR_USAGE_PANEL_TARGET_ATTR, next_usage))
            segment = page[seg_start:seg_end]

            disclosure = re.search(
                r'<details class="theme-carousel__all"><summary>([^<]*)</summary>', segment)
            if not disclosure:
                return False, (
                    "usage=%r: no <details class=\"theme-carousel__all\"><summary> is rendered"
                    % usage)
            if disclosure.group(1) != html.escape(
                    config_page.THEME_CAROUSEL_SUMMARY, quote=False):
                return False, (
                    "usage=%r: the disclosure's summary reads %r, expected %r"
                    % (usage, disclosure.group(1), config_page.THEME_CAROUSEL_SUMMARY))
            strip_at = segment.index('id="%s"' % strip_id)
            # 27-07-PLAN.md Task 1 (CFG-68/D-20): INVERTED from this
            # check's original assertion. The disclosure used to render
            # BEFORE the strip (an adjacent-sibling selector reached
            # forward from it); the developer read that as "Voir tous
            # les thèmes" sitting above the very thing it discloses,
            # backwards for a way OUT. It now renders AFTER the strip
            # (and after the pagers and dots — see
            # _theme_carousel_html()'s own return statement), and
            # style.css reaches the grid through a `:has()` rule scoped
            # to the shared `.theme-carousel` wrapper instead, which
            # does not care which of the two comes first.
            if disclosure.start() < strip_at:
                return False, (
                    "usage=%r: the disclosure renders BEFORE the strip — D-20 moved 'Voir "
                    "tous les thèmes' below the strip it discloses, and style.css's :has() "
                    "rule (scoped to the shared .theme-carousel wrapper) governs the grid's "
                    "layout regardless of order, so there is no longer a reason for the "
                    "disclosure to precede it" % usage)

            # BOTH PAGERS INSIDE THE GATE, AND ZERO PAGER MARKUP OUTSIDE
            # IT — WITHIN THIS CAROUSEL'S OWN SEGMENT.
            gate = re.search(
                r'<div class="theme-carousel__pagers ([^"]*)" (%s)>(.*?)</div>'
                % re.escape(config_page.THEME_CAROUSEL_WRAPPER_ATTR), segment, re.DOTALL)
            if not gate:
                return False, (
                    "usage=%r: no .theme-carousel__pagers wrapper carrying the wrapper "
                    "attribute" % usage)
            if layout.JS_GATE_CLASS not in gate.group(1).split():
                return False, (
                    "usage=%r: the pager wrapper's classes are %r — without %r it renders "
                    "permanently with scripts blocked, which is a control that shows and does "
                    "nothing" % (usage, gate.group(1), layout.JS_GATE_CLASS))
            inside = gate.group(3)
            total_pagers = segment.count(config_page.THEME_CAROUSEL_PAGER_ATTR + '="')
            if inside.count(config_page.THEME_CAROUSEL_PAGER_ATTR + '="') != 2:
                return False, (
                    "usage=%r: expected exactly two pagers inside the gate, found %d"
                    % (usage, inside.count(config_page.THEME_CAROUSEL_PAGER_ATTR + '="')))
            if total_pagers != 2:
                return False, (
                    "usage=%r: this carousel's own segment carries %d pager attributes but "
                    "only two are inside the gate — a pager rendered outside it is inert with "
                    "scripts blocked" % (usage, total_pagers))
            for direction, label in (
                    (config_page.THEME_CAROUSEL_PAGER_PREV,
                     config_page.THEME_CAROUSEL_PREV_LABEL),
                    (config_page.THEME_CAROUSEL_PAGER_NEXT,
                     config_page.THEME_CAROUSEL_NEXT_LABEL)):
                button = re.search(
                    r'<button type="button"([^>]*%s="%s"[^>]*)>'
                    % (re.escape(config_page.THEME_CAROUSEL_PAGER_ATTR), direction), inside)
                if not button:
                    return False, (
                        "usage=%r: no <button> carries the %r pager attribute"
                        % (usage, direction))
                attrs = button.group(1)
                if 'aria-label="%s"' % html.escape(label, quote=True) not in attrs:
                    return False, (
                        "usage=%r: the %s pager carries no aria-label=%r — it draws its arrow "
                        "in CSS and has no text of its own, so without one it announces "
                        "nothing at all: %r" % (usage, direction, label, attrs))
                # THE RELATIONSHIP ITSELF: this pager's aria-controls
                # must name THIS SEGMENT's OWN strip id, not merely any
                # strip id anywhere on the page — a pager wired to a
                # sibling carousel's strip would drive that OTHER
                # carousel silently, which is the exact trap Task 1
                # closed for the id itself and this check closes for
                # the pager wiring that depends on it.
                if ('aria-controls="%s"' % strip_id) not in attrs:
                    return False, (
                        "usage=%r: the %s pager's aria-controls does not name THIS carousel's "
                        "own strip (%r) — and that is not only an announcement: "
                        "theme-preview.js resolves the element to scroll through this very "
                        "attribute, so a pager wired to the wrong strip silently drives a "
                        "sibling carousel instead: %r" % (usage, direction, strip_id, attrs))
                if "aria-hidden" in attrs:
                    return False, (
                        "usage=%r: the %s pager is aria-hidden — these are real controls with "
                        "real labels, not decorations" % (usage, direction))
                if "control-hit-area" not in attrs and "control-hit-area" not in button.group(0):
                    return False, (
                        "usage=%r: the %s pager does not carry .control-hit-area, 25-01's "
                        "shared 22px-box-plus-44px-::before synthesis (.copy-btn's own values "
                        "verbatim)" % (usage, direction))

        # THE SCRIPT SIDE OF THE SAME SEAM, AND THE ONE THING IT MUST
        # NOT DO. A pager that listened for a key would take
        # ArrowLeft/ArrowRight away from the native radiogroup, which is
        # precisely the selection the scripts-blocked path depends on.
        script = _read_static("theme-preview.js")
        # ON A BOUNDARY, NEVER AS A BARE SUBSTRING. Measured: the first
        # version of this clause asked `attr not in script`, and a
        # mutation renaming the script's own constant to
        # "data-theme-pagerr" — which matches nothing in the markup and
        # leaves both pagers inert — passed it, because the typo
        # CONTAINS the real name. The same boundary discipline
        # test_companion_app.py's own gate-class pin records.
        if not re.search(
                r"(?<![-\w])%s(?![-\w])"
                % re.escape(config_page.THEME_CAROUSEL_PAGER_ATTR), script):
            return False, (
                "companion/static/theme-preview.js never names %r, so the two pagers it is "
                "supposed to own are two buttons that do nothing"
                % config_page.THEME_CAROUSEL_PAGER_ATTR)
        code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", " ", script, flags=re.DOTALL))
        for key_event in ("keydown", "keyup", "keypress"):
            if key_event in code:
                return False, (
                    "theme-preview.js registers a %r listener — a pager that captures an arrow "
                    "key breaks the native radiogroup selection the no-JS path depends on"
                    % key_event)
        if "preventDefault" in code:
            return False, (
                "theme-preview.js calls preventDefault — this file drives a native radio group "
                "and a native scroll container, and the browser owns both models")

        source = _read_static("style.css")
        rules = {
            # 27-07-PLAN.md Task 1 (CFG-68/D-20): the adjacent-sibling
            # selector this replaces cannot reach the strip once the
            # disclosure trails it in the DOM — see config_page.
            # _theme_carousel_html()'s own return statement. The
            # replacement is scoped to the shared .theme-carousel
            # wrapper, so it works regardless of which of the two comes
            # first, and stays inside the file's one @supports
            # selector(:has(*)) block (checked below by count).
            ".theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip {": (
                "flex-wrap: wrap;",),
            ".theme-carousel__pagers {": (
                "--js-gate-display: flex;", "gap: var(--space-lg);",
                "margin-top: var(--space-sm);"),
            ".theme-carousel__pager::after {": (
                'content: "";', "width: 6px;", "height: 6px;",
                "border-right: 2px solid currentColor;",
                "border-bottom: 2px solid currentColor;",
                "transform: rotate(-45deg);"),
            ".theme-carousel__pager--prev::after {": ("transform: rotate(135deg);",),
            # 27-07-PLAN.md Task 1 (CFG-68/D-20): `margin-top` joins
            # `margin-bottom` now that the disclosure is the LAST child
            # of .theme-carousel rather than the first — see
            # style.css's own comment on this rule.
            ".theme-carousel__all {": (
                "margin-top: var(--space-sm);", "margin-bottom: var(--space-sm);"),
        }
        for selector, declarations in rules.items():
            if selector not in source:
                return False, "style.css declares no %s rule" % selector.rstrip(" {")
            body = source[source.index(selector) + len(selector):]
            body = body[:body.index("}")]
            for declaration in declarations:
                if declaration not in body:
                    return False, (
                        "%s does not declare %r — %r"
                        % (selector.strip(" {\n"), declaration, body.strip()))
        return True, ""
    check(
        "each of the three carousels' full grid sits behind a native <details>/<summary> and "
        "never a <dialog> (a dialog cannot be opened without script, which would put eighteen "
        "themes behind a dead control), each disclosure renders AFTER its OWN strip (D-20, "
        "27-07-PLAN.md Task 1 — 'Voir tous les thèmes' reads as a way OUT below the strip "
        "rather than a preamble above it) with the stylesheet reaching each grid through a "
        ":has() rule scoped to its own .theme-carousel wrapper, the whole Display page carries "
        "exactly len(THEME_IDS) radios named 'theme' (ONE set, so the page can never show one "
        "setting in two disagreeing places), and — checked PER USAGE PANEL, which is also THE "
        "RELATIONSHIP Task 2 asks for — that panel's own two pagers render inside 25-01's gate "
        "wrapper with zero pager markup outside it, each carries a real aria-label and an "
        "aria-controls naming THAT SAME PANEL's own strip (never a sibling carousel's), neither "
        "is aria-hidden, both wear .control-hit-area, and theme-preview.js (shared by all three) "
        "registers no key listener and calls no preventDefault at all, because a pager "
        "capturing an arrow key would break the native radiogroup selection the no-JS path "
        "depends on (CFG-50/D-09, 25-06-PLAN.md Task 3; disclosure order and the :has() "
        "replacement, CFG-68/D-20, 27-07-PLAN.md Task 1; generalised to three carousels with "
        "the per-panel relationship check, CFG-68, 27-07-PLAN.md Task 2)",
        _the_full_grid_sits_behind_a_native_details_and_the_pagers_behind_the_gate)

    # ------------------------------------------------------------------
    # 27-07-PLAN.md Task 1 (CFG-68): THE TRAP CHECK. THEME_CAROUSEL_
    # STRIP_ID used to be a single id literal serving as both the
    # departures strip's own id AND what both pagers' aria-controls
    # named — fine with one carousel, but a SECOND carousel built from
    # the same literal (or from a helper that still defaulted to it)
    # would render two elements sharing one id, which is invalid HTML,
    # and every pager on the page would drive only the FIRST match.
    # _theme_carousel_html() now takes strip_id as a required argument
    # instead (no shared default), which makes that specific collision
    # impossible BY CONSTRUCTION — this check is the proof that holds
    # for every OTHER way a duplicate id could still reach the page
    # (a typo, a copy-pasted call site, anything), because it asserts
    # the property the trap violates directly: id uniqueness across the
    # whole rendered page, not "the carousel ids I expect differ".
    # ------------------------------------------------------------------

    def _the_rendered_settings_page_carries_no_duplicate_id():
        page = config_page.render({
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
        ids = re.findall(r'\bid="([^"]*)"', page)
        if not ids:
            return False, (
                "found no id=\"...\" attributes at all on the rendered Display page — this scan "
                "would pass against a page with none, which measures nothing")
        seen = {}
        for value in ids:
            seen[value] = seen.get(value, 0) + 1
        duplicates = {value: count for value, count in seen.items() if count > 1}
        if duplicates:
            # ONE named example, not the whole dict — a message a future
            # reader can act on immediately, matching this file's own
            # convention of naming the ACTUAL offending value rather
            # than a summary of how many things are wrong.
            dup_id, dup_count = sorted(duplicates.items())[0]
            return False, (
                "id=%r appears %d times on the rendered Display page — every id-based lookup "
                "(aria-controls, a <label for=>, aria-labelledby, document.getElementById) "
                "resolves to the FIRST match silently, so a duplicate id is not a cosmetic "
                "defect: whichever control names %r second is driving or describing the FIRST "
                "one instead of itself" % (dup_id, dup_count, dup_id))
        return True, ""
    check(
        "the rendered Display page carries no duplicate id anywhere — asserted as page-wide id "
        "uniqueness (THE property the THEME_CAROUSEL_STRIP_ID trap violates), never as 'the "
        "carousel ids I expect differ', with a failure message naming the duplicated id and how "
        "many times it appeared (CFG-68, 27-07-PLAN.md Task 1)",
        _the_rendered_settings_page_carries_no_duplicate_id)

    # --- 27-03-PLAN.md Task 1 (CFG-64) -------------------------------

    def _the_native_submit_is_emitted_unconditionally_on_every_render():
        """CFG-64: the no-JS floor is kept BY CONSTRUCTION, not by a
        visibility rule — the native submit carrying
        STATIC_SAVE_FALLBACK_ATTR must be reachable through every code
        path render() has, with no conditional of any kind governing its
        presence. Two proofs, not one, because a rendering-only proof
        would pass against a page whose SOURCE has a branch that merely
        never gets exercised by today's three scopes, and a source-only
        proof would pass against a render() that formats the attribute
        into a sub-template some caller forgets to include.

        THE SOURCE PROOF: render() has exactly one `return` statement (a
        second return would be a second, unproven code path), that
        return is a direct statement of the function's own body — never
        nested inside an `if`/`for`/`while`/`try` — and
        STATIC_SAVE_FALLBACK_ATTR appears exactly once inside it as a
        bare name, never behind an `ast.IfExp` (a ternary), which is the
        one shape that would make its presence depend on a runtime
        condition.

        THE RENDER PROOF: render() is actually called for every scope
        the page supports (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) and
        each rendering carries EXACTLY ONE `data-static-save-fallback`
        occurrence — never zero (the submit is missing) and never two or
        more (a second, competing save control). One check over all
        three scopes, not one per scope: the relationship under test is
        "every scope has it", and a per-scope check would let a future
        fourth scope ship with no proof at all.
        """
        with open(os.path.join(HERE, "pages", "config_page.py"), encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source)
        render_fn = next(
            (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "render"),
            None)
        if render_fn is None:
            return False, "config_page.py defines no top-level render() function any more"
        returns = [n for n in ast.walk(render_fn) if isinstance(n, ast.Return)]
        if len(returns) != 1:
            return False, (
                "expected exactly one return statement inside render(), found %d — a second "
                "return is a second code path, and the one that reaches "
                "STATIC_SAVE_FALLBACK_ATTR would no longer be the only one" % len(returns))
        only_return = returns[0]
        if only_return not in render_fn.body:
            return False, (
                "render()'s one return statement is NESTED inside a conditional/loop/try block "
                "of the function body — the submit's emission would then be reachable on some "
                "paths and not others, exactly the branch this check exists to rule out")
        carriers = [
            n for n in ast.walk(only_return.value)
            if isinstance(n, ast.Name) and n.id == "STATIC_SAVE_FALLBACK_ATTR"]
        if not carriers:
            return False, (
                "render()'s one return statement never names STATIC_SAVE_FALLBACK_ATTR at all "
                "— the submit is not part of what this function returns")
        if len(carriers) != 1:
            return False, (
                "STATIC_SAVE_FALLBACK_ATTR appears %d times in render()'s return — expected "
                "exactly one submit" % len(carriers))
        for node in ast.walk(only_return.value):
            if isinstance(node, ast.IfExp) and carriers[0] in ast.walk(node):
                return False, (
                    "STATIC_SAVE_FALLBACK_ATTR is reached through a ternary inside render()'s "
                    "return — its presence would then depend on a runtime condition, never "
                    "unconditional")
        base_ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
            rendered = config_page.render(base_ctx, scope=scope)
            count = rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR)
            if count != 1:
                return False, (
                    "expected exactly one %r occurrence on scope=%r, found %d — the native "
                    "submit must render unconditionally, once, on every scope"
                    % (config_page.STATIC_SAVE_FALLBACK_ATTR, scope, count))
        return True, ""
    check(
        "the native submit carrying STATIC_SAVE_FALLBACK_ATTR is emitted UNCONDITIONALLY — "
        "render() has exactly one return statement, it is never nested inside a branch, and "
        "the attribute reaches it as a bare name rather than through a ternary — AND every one "
        "of the three scopes (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) renders it exactly once, so "
        "there is no code path, past or future, that can omit the no-JS save floor (CFG-64, "
        "27-03-PLAN.md Task 1)",
        _the_native_submit_is_emitted_unconditionally_on_every_render)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-page: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
