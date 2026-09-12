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
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import app as companion_app  # noqa: E402
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
        # render — the count below is 7, not 6, for that reason alone,
        # not a rename.
        ctx = {
            "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(ctx)
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements anywhere on the page, found one"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements anywhere on the page, found one"
        if rendered.count('class="theme-status"') != 7:
            return False, "expected exactly 7 theme-status-wrapped groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display/Notifications), got %d" % rendered.count('class="theme-status"')
        if "theme-chip-grid" not in rendered:
            return False, "expected the Theme group to render a .theme-chip-grid"
        if rendered.count('<label class="runway-card') != 3:
            return False, "expected exactly 3 runway-card labels, got %d" % rendered.count('<label class="runway-card')
        if "Save settings" not in rendered:
            return False, "expected the 'Save settings' submit button copy"
        return True, ""
    check(
        "render() emits Theme's .theme-chip-grid (no <fieldset>, D-01), seven theme-status-wrapped groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display/Notifications), three runway-card labels, and a Save settings submit button",
        _render_shape_theme_chip_grid_runway_cards_groups_and_save_button)

    def _led_group_carries_classed_label_and_unchanged_input_attrs():
        # quick task 260901-qif: pins the settings-checkbox label class
        # (renamed from led-checkbox by 10-05-PLAN.md Task 2) and guards
        # the input's name/value/checked attribute sequence against a
        # future markup edit silently reordering it - the two live-HTTP
        # LED checks further down this file match on that exact sequence.
        checked_html = config_page.led_group(True)
        unchecked_html = config_page.led_group(False)
        label_open = '<label class="settings-checkbox">'
        if checked_html.count(label_open) != 1:
            return False, "expected led_group(True) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        if unchecked_html.count(label_open) != 1:
            return False, "expected led_group(False) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        led_value = escape_html(config_page.LED_CHECKBOX_VALUE)
        expected_checked = 'name="led_enabled" value="%s" checked' % led_value
        if expected_checked not in checked_html:
            return False, "expected led_group(True) to carry %r" % (expected_checked,)
        # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - with no
        # error, the input now carries a bare aria-describedby pointing
        # at LED_SECTION_CAPTION_ID (via _field_error_attrs()'s hint_id)
        # before the closing '>', not a bare closing '>' any more.
        expected_unchecked = (
            'name="led_enabled" value="%s" aria-describedby="%s">'
            % (led_value, escape_html(config_page.LED_SECTION_CAPTION_ID)))
        if expected_unchecked not in unchecked_html:
            return False, "expected led_group(False) to carry %r with no checked flag" % (expected_unchecked,)
        if "checked" in unchecked_html:
            return False, "expected led_group(False) to carry no checked flag at all"
        return True, ""
    check(
        "led_group() emits the settings-checkbox label class and preserves the input's name/value/checked attribute sequence",
        _led_group_carries_classed_label_and_unchanged_input_attrs)

    # ------------------------------------------------------------------
    # 10-05-PLAN.md Task 3: quiet_hours_group() markup/field-order/
    # escaping and render() wiring checks (D-03/D-04, 10-UI-SPEC.md).
    # ------------------------------------------------------------------

    def _quiet_hours_group_markup_checkbox_and_time_inputs():
        checked_html = config_page.quiet_hours_group(True, "23:00", "07:00")
        unchecked_html = config_page.quiet_hours_group(False, "23:00", "07:00")
        label_open = '<label class="settings-checkbox">'
        if checked_html.count(label_open) != 1:
            return False, "expected quiet_hours_group(True, ...) to carry exactly one <label class=\"settings-checkbox\"> occurrence"
        if 'name="quiet_hours_start"' not in checked_html or 'type="time"' not in checked_html:
            return False, "expected a type=\"time\" input named quiet_hours_start"
        if 'value="23:00"' not in checked_html:
            return False, "expected quiet_hours_start's value to be 23:00"
        if 'name="quiet_hours_end"' not in checked_html:
            return False, "expected an input named quiet_hours_end"
        if 'value="07:00"' not in checked_html:
            return False, "expected quiet_hours_end's value to be 07:00"
        if checked_html.count("checked") != 1:
            return False, "expected quiet_hours_group(True, ...) to carry exactly one checked flag, got %d" % checked_html.count("checked")
        if "checked" in unchecked_html:
            return False, "expected quiet_hours_group(False, ...) to carry no checked flag at all"
        if "theme-status__row" in checked_html:
            return False, "expected no theme-status__row wrapper — Start/End must stack vertically (10-UI-SPEC.md)"
        if "disabled" in checked_html or "disabled" in unchecked_html:
            return False, "expected no disabled attribute on either branch — the time inputs are never disabled (10-UI-SPEC.md)"
        return True, ""
    check(
        "quiet_hours_group() emits the settings-checkbox label, one type=\"time\" input each for Start/End with their current values, exactly one checked flag when enabled and none when disabled, no theme-status__row, and no disabled attribute",
        _quiet_hours_group_markup_checkbox_and_time_inputs)

    def _quiet_hours_group_field_order_heading_caption_checkbox_start_end():
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
        heading_close = rendered.index("</h2>")
        caption_pos = rendered.index("section-caption")
        checkbox_pos = rendered.index('name="quiet_hours_enabled"')
        start_pos = rendered.index('name="quiet_hours_start"')
        end_pos = rendered.index('name="quiet_hours_end"')
        if not (heading_close < caption_pos < checkbox_pos < start_pos < end_pos):
            return False, (
                "expected heading < caption < checkbox < start < end in document order, got positions %r"
                % ((heading_close, caption_pos, checkbox_pos, start_pos, end_pos),))
        return True, ""
    check(
        "quiet_hours_group()'s field order is heading, then caption, then the enable checkbox, then Start, then End, in document order (10-UI-SPEC.md's locked field order)",
        _quiet_hours_group_field_order_heading_caption_checkbox_start_end)

    def _quiet_hours_group_escapes_crafted_current_values():
        rendered = config_page.quiet_hours_group(True, '"><script>', "07:00")
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
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
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
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
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
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
        if 'data-preset-start="08:00" data-preset-end="18:00"' not in rendered:
            return False, "expected the Work day preset to carry data-preset-start=08:00/data-preset-end=18:00"
        return True, ""
    check(
        "the Work day preset carries data-preset-start=\"08:00\" data-preset-end=\"18:00\"",
        _quiet_hours_group_workday_preset_carries_expected_times)

    def _quiet_hours_group_always_on_preset_disables_with_no_time_attrs():
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
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

    def _quiet_hours_group_preset_row_between_checkbox_and_time_inputs():
        rendered = config_page.quiet_hours_group(True, "23:00", "07:00")
        checkbox_pos = rendered.index("settings-checkbox")
        preset_pos = rendered.index(config_page.QUIET_HOURS_PRESET_ATTR)
        time_pos = rendered.index('type="time"')
        if not (checkbox_pos < preset_pos < time_pos):
            return False, (
                "expected the preset row to fall after the settings-checkbox label and before the first "
                "type=\"time\" input, got positions %r" % ((checkbox_pos, preset_pos, time_pos),))
        return True, ""
    check(
        "the preset button row appears after the .settings-checkbox label and before the first "
        "type=\"time\" input (D-14's locked position)",
        _quiet_hours_group_preset_row_between_checkbox_and_time_inputs)

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
        if 'name="quiet_hours_enabled"' not in rendered:
            return False, "expected the quiet-hours enable checkbox to appear in the rendered page"
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
        if rendered.count('<input type="number" name="wake_interval_s"') != 1:
            return False, "expected exactly one <input type=\"number\" name=\"wake_interval_s\">"
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
        headings = [
            "Theme", "Runway", config_page.LED_SECTION_HEADING,
            config_page.QUIET_HOURS_SECTION_HEADING,
            config_page.WAKE_INTERVAL_SECTION_HEADING,
        ]
        positions = [rendered.index(h) for h in headings]
        if positions != sorted(positions):
            return False, "expected the five settings groups in locked order Theme/Runway/Diagnostic LED/Quiet hours/Wake interval, got positions %r" % (positions,)
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
    # 12-05-PLAN.md Task 1/Task 2: display_group() markup, its caption's
    # locked copy, render()'s D-09 prefill default, and handle_post()'s
    # three-shape checkbox resolution ladder (12-UI-SPEC.md, 12-CONTEXT.md
    # D-02/D-08/D-09).
    # ------------------------------------------------------------------

    def _display_group_markup_shape_checked_and_unchecked():
        # Bullet 1: display_group(True) emits one .theme-status[data-dirty-
        # section] wrapper, the locked heading and caption, one
        # .settings-checkbox label, exactly one checkbox input named for
        # the field, exactly one checked flag; display_group(False) emits
        # none; and neither emits <fieldset>/<legend>/type="time"/
        # type="number"/disabled - this group has no dependent fields and
        # must not grow any.
        checked_html = config_page.display_group(True)
        unchecked_html = config_page.display_group(False)
        for rendered in (checked_html, unchecked_html):
            if rendered.count('class="theme-status"') != 1:
                return False, "expected exactly one .theme-status wrapper"
            if config_page.DIRTY_SECTION_ATTR not in rendered:
                return False, "expected the wrapper to carry DIRTY_SECTION_ATTR"
            expected_heading = (
                '<h2 class="text-heading">%s</h2>'
                % escape_html(config_page.DISPLAY_SECTION_HEADING))
            if rendered.count(expected_heading) != 1:
                return False, "expected exactly one heading %r" % (expected_heading,)
            # 19-11-PLAN.md Task 3 (D-12/A-30): retargeted in place - the
            # caption now carries DISPLAY_SECTION_CAPTION_ID (the
            # checkbox's own aria-describedby target).
            expected_caption = (
                '<p class="text-label section-caption" id="%s">%s</p>'
                % (
                    escape_html(config_page.DISPLAY_SECTION_CAPTION_ID),
                    escape_html(config_page.DISPLAY_SECTION_CAPTION)))
            if rendered.count(expected_caption) != 1:
                return False, "expected exactly one caption %r" % (expected_caption,)
            if rendered.count('<label class="settings-checkbox">') != 1:
                return False, "expected exactly one <label class=\"settings-checkbox\">"
            if rendered.count('<input type="checkbox" name="display_enabled"') != 1:
                return False, "expected exactly one checkbox input named display_enabled"
            if "<fieldset" in rendered:
                return False, "expected no <fieldset> - this group deliberately doesn't use one"
            if "<legend" in rendered:
                return False, "expected no <legend> - a <legend> only has accessible-name semantics inside a <fieldset>"
            if 'type="time"' in rendered:
                return False, "expected no type=\"time\" input - this group has no dependent fields"
            if 'type="number"' in rendered:
                return False, "expected no type=\"number\" input - this group has no dependent fields"
            if "disabled" in rendered:
                return False, "expected no disabled attribute - no sibling control's enabled state depends on this one"
        if checked_html.count(" checked") != 1:
            return False, "expected display_group(True) to carry exactly one checked flag"
        if unchecked_html.count(" checked") != 0:
            return False, "expected display_group(False) to carry zero checked flags"
        return True, ""
    check(
        "display_group(True)/display_group(False) emit exactly one .theme-status[data-dirty-section] wrapper, the locked heading/caption, one .settings-checkbox label, one checkbox input named display_enabled, and the correct checked count, with none of <fieldset>/<legend>/type=\"time\"/type=\"number\"/disabled",
        _display_group_markup_shape_checked_and_unchecked)

    def _display_section_caption_locked_verbatim():
        # Bullet 2: exact equality is a stronger gate here than a
        # word-level absence rule (e.g. "instant"/"immediate" not present)
        # and does not risk pinning fragile phrasing beyond the locked
        # sentence itself (12-UI-SPEC.md Copywriting Contract, D-02).
        expected = (
            "Turns the physical panel off remotely, without touching the "
            "hardware. Takes effect within about 5 minutes, both "
            "switching off and back on.")
        if config_page.DISPLAY_SECTION_CAPTION != expected:
            return False, "expected DISPLAY_SECTION_CAPTION to equal the locked sentence, got %r" % (config_page.DISPLAY_SECTION_CAPTION,)
        return True, ""
    check(
        "DISPLAY_SECTION_CAPTION equals 12-UI-SPEC.md's locked sentence exactly, stating the ~5-minute apply latency in both directions and never claiming immediacy (D-02)",
        _display_section_caption_locked_verbatim)

    def _render_display_prefill_defaults_checked_and_honors_saved_false():
        # Bullet 3: render() with an empty device_config produces a
        # checked box (D-09 reaching the page, not just the loader), and
        # {"display_enabled": False} produces an unchecked one.
        #
        # 20-07-PLAN.md Task 2 (D-19): display_group()'s own quick-action
        # slot now renders several nested <div>s BEFORE the checkbox
        # inside the same outer wrapper — the old "slice to the first
        # </div> after the dirty-section marker" no longer reaches the
        # checkbox at all (it now closes an inner quick-action <div>
        # instead). Retargeted to find the checkbox's own <input> tag
        # directly, which is robust to whatever precedes it in the card.
        rendered = config_page.render({"device_config": {}, "state_dir": "/tmp"})
        if rendered.count('name="display_enabled"') != 1:
            return False, "expected exactly one display_enabled input"
        checkbox_marker = rendered.index('<input type="checkbox" name="display_enabled"')
        checkbox_tag = rendered[checkbox_marker:rendered.index(">", checkbox_marker) + 1]
        if " checked" not in checkbox_tag:
            return False, "expected an empty device_config to render the Display box checked (D-09)"

        rendered_off = config_page.render({
            "device_config": {"display_enabled": False}, "state_dir": "/tmp"})
        checkbox_marker_off = rendered_off.index('<input type="checkbox" name="display_enabled"')
        checkbox_tag_off = rendered_off[checkbox_marker_off:rendered_off.index(">", checkbox_marker_off) + 1]
        if " checked" in checkbox_tag_off:
            return False, "expected device_config={'display_enabled': False} to render the box unchecked"
        return True, ""
    check(
        "render() with an empty device_config renders the Display checkbox checked (D-09), and with display_enabled explicitly False renders it unchecked",
        _render_display_prefill_defaults_checked_and_honors_saved_false)

    def _handle_post_display_enabled_three_shapes():
        # Bullet 4: all three checkbox shapes - absent means off and is
        # persisted as off; the exact constant means on; a crafted value
        # returns the generic save-failed flash and leaves a pre-existing
        # device_config.json byte-identical, proving all-or-nothing
        # rejection still holds across all eight fields.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for an absent display_enabled, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["display_enabled"] is not False:
                return False, "expected display_enabled False on disk, got %r" % (on_disk["display_enabled"],)
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
        "handle_post() resolves display_enabled through all three checkbox shapes: absent persists False, DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key and leaves a pre-existing device_config.json byte-identical",
        _handle_post_display_enabled_three_shapes)

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
        # 19-11-PLAN.md Task 3 (D-12/A-30): Theme's and Runway's own <h2>
        # now carry an id (the two chip grids'/runway row's own
        # aria-labelledby target) - retargeted in place, not a rename of
        # this check's own premise (each group is still named exactly once).
        heading_ids = {
            "Theme": config_page.THEME_GROUP_HEADING_ID,
            "Runway": config_page.RUNWAY_GROUP_HEADING_ID,
        }
        for name in ("Theme", "Runway", "Diagnostic LED", config_page.POLL_SECTION_HEADING):
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

    def _render_dirty_bar_is_sibling_of_form_last_on_page():
        # quick task 260901-re6: inverted wholesale from the pre-merge
        # version of this check (which asserted the bar was a genuine
        # descendant of the form). `position: sticky` resolved against
        # the form's own short box, so the bar detached from the
        # viewport bottom on a tall page — the fix moves the bar to be a
        # sibling of the form, emitted last on the page (after both
        # </form> and the Poll section), submitting via a form= attribute
        # instead of native DOM nesting.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if rendered.count('<form class="config-form"') != 1:
            return False, "expected exactly one config-form <form>, no duplicate"
        if "</form>" not in rendered:
            return False, "expected a closing </form> tag"
        if "data-dirty-bar" not in rendered:
            return False, "expected data-dirty-bar to appear in render()'s output"
        bar_pos = rendered.index("data-dirty-bar")
        # 20-07-PLAN.md Task 2 (D-19): SCOPE_ALL's legacy flat join still
        # calls the now-restructured display_group()/quiet_hours_group()
        # (both are still members of scope_groups(SCOPE_ALL)'s own fixed
        # tuple), and each now embeds its own small quick-action <form>
        # ahead of the settings form's real closing tag — so the FIRST
        # "</form>" in the document is no longer necessarily the settings
        # form's own. The bottom static Save button is the last thing the
        # settings form itself emits before its own closing tag (render()'s
        # own template: "...Save settings</button></form>"), so the
        # settings form's real "</form>" is the first one AFTER that
        # button's own text.
        save_button_pos = rendered.index("Save settings")
        if save_button_pos >= bar_pos:
            return False, "expected the bottom Save settings button to appear before the dirty bar"
        form_end = rendered.index("</form>", save_button_pos)
        if bar_pos <= form_end:
            return False, "expected data-dirty-bar to appear AFTER </form> closes, not inside it"
        poll_heading = '<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING
        if poll_heading not in rendered:
            return False, "expected the Poll section heading to be present"
        poll_pos = rendered.index(poll_heading)
        if bar_pos <= poll_pos:
            return False, "expected data-dirty-bar to appear after the Poll section heading too, so the bar is genuinely last on the page"
        form_start = rendered.index('<form class="config-form"')
        form_segment = rendered[form_start:form_end]
        if "Save settings" not in form_segment:
            return False, "expected the always-visible bottom Save settings fallback button to still appear inside the form"
        save_button_marker = 'class="dirty-bar__save" form="%s"' % config_page.SETTINGS_FORM_ID
        if save_button_marker not in rendered:
            return False, "expected the dirty-bar's own save button to carry form=%r" % (config_page.SETTINGS_FORM_ID,)
        return True, ""
    check(
        "render()'s dirty-state bar is a sibling of the config-form <form>, emitted last on the page after both </form> and the Poll section, with its save button carrying form=SETTINGS_FORM_ID (quick task 260901-re6)",
        _render_dirty_bar_is_sibling_of_form_last_on_page)

    def _theme_fieldset_one_radio_per_registry_entry():
        # merge of origin/main (Phase 8): this exact check existed pre-
        # 06.6.3-03, was retired outright when the registry briefly held
        # just "sky" (a one-option radio group has no real decision
        # value — D-04's read-only-status branch took over that case),
        # and is reinstated here now that the merged registry holds 19
        # real entries again — theme_fieldset()'s existing len()==1
        # fallback (unmodified by this merge) means this assertion is
        # exercising real, currently-live markup, not a retired code path.
        rendered = config_page.theme_fieldset("black")
        radio_count = rendered.count('name="theme"')
        if radio_count != len(device_config.THEMES):
            return False, (
                "expected %d theme radios (len(THEMES)), got %d"
                % (len(device_config.THEMES), radio_count))
        return True, ""
    check(
        "theme_fieldset() emits one radio per THEMES registry entry now that the registry holds more than one theme (merge of origin/main, Phase 8)",
        _theme_fieldset_one_radio_per_registry_entry)

    def _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex():
        # D-04, Task 2 Test 1: with a synthetic single-member THEME_IDS
        # registry (monkeypatched for the duration of this check only),
        # theme_fieldset() renders the read-only status block — zero
        # <input> occurrences — showing "{label} · current" and swatch
        # chip hex values computed at test time from
        # panel_format.PALETTE_RGB, not hardcoded expected strings.
        #
        # merge of origin/main (Phase 8): the real global THEME_IDS
        # registry now permanently holds 19 entries, so this check can no
        # longer rely on "the real (unmodified) registry" to exercise the
        # len()==1 branch — it monkeypatches a clean, isolated one-member
        # registry instead, mirroring the pattern the sibling
        # multi-theme-fallback check below already uses.
        original_themes = device_config.THEMES
        original_ids = device_config.THEME_IDS
        default_id = device_config.DEFAULT_THEME_ID
        device_config.THEMES = {default_id: dict(original_themes[default_id])}
        device_config.THEME_IDS = tuple(device_config.THEMES)
        try:
            rendered = config_page.theme_fieldset(default_id)
            if "<input" in rendered:
                return False, "expected zero <input occurrences in the read-only branch"
            expected_label = "%s · current" % device_config.theme_label(default_id)
            if expected_label not in rendered:
                return False, "expected %r in the rendered output" % (expected_label,)
            theme = device_config.THEMES[default_id]
            departing_hex = config_page._palette_hex(theme["departing_index"])
            arriving_hex = config_page._palette_hex(theme["arriving_index"])
            if ("background:%s" % departing_hex) not in rendered:
                return False, "expected the departing swatch hex %r derived from PALETTE_RGB" % (departing_hex,)
            if ("background:%s" % arriving_hex) not in rendered:
                return False, "expected the arriving swatch hex %r derived from PALETTE_RGB" % (arriving_hex,)
            if "Phase 7" in rendered:
                return False, "expected no leaked internal 'Phase 7' planning reference (UXA-05)"
        finally:
            device_config.THEMES = original_themes
            device_config.THEME_IDS = original_ids
        return True, ""
    check(
        "theme_fieldset() renders the read-only theme-status block with real panel-color swatch hex values when THEME_IDS has one member (D-04)",
        _theme_fieldset_single_theme_renders_read_only_status_with_real_swatch_hex)

    def _theme_fieldset_falls_back_to_chip_grid_when_multiple_themes_registered():
        # D-04, Task 2 Test 2: a synthetic 2-member THEME_IDS (monkeypatched
        # for the duration of this check only) makes theme_fieldset() fall
        # back to the editable chip-grid markup (06.6.4.1.1-05, D-01) — a
        # len() check, not a hardcoded single-theme assumption.
        #
        # merge of origin/main (Phase 8): THEMES is now REPLACED with a
        # clean 2-entry dict rather than dict(original_themes) plus one
        # more key — copying the real registry would now start from 19
        # entries, not 1, breaking this test's own "exactly 2 theme radios"
        # assertion below.
        original_themes = device_config.THEMES
        original_ids = device_config.THEME_IDS
        default_id = device_config.DEFAULT_THEME_ID
        device_config.THEMES = {
            default_id: dict(original_themes[default_id]),
            "dusk": {
                "departing_index": original_themes[default_id]["departing_index"],
                "arriving_index": original_themes[default_id]["arriving_index"],
                "ink_index": original_themes[default_id]["ink_index"],
                "label": "Dusk",
            },
        }
        device_config.THEME_IDS = tuple(device_config.THEMES)
        try:
            rendered = config_page.theme_fieldset(default_id)
        finally:
            device_config.THEMES = original_themes
            device_config.THEME_IDS = original_ids
        # 06.6.4.1.1-05: the fallback branch no longer emits a
        # <fieldset>/<legend> radio group — it emits a .theme-chip-grid
        # inside the same .theme-status card idiom Runway/Diagnostic LED
        # use, carrying data-dirty-section="Theme" on that wrapper.
        if "<fieldset" in rendered or "<legend" in rendered:
            return False, "expected zero <fieldset>/<legend> once >1 theme is registered (D-01 retires the radio-list markup)"
        if "theme-chip-grid" not in rendered:
            return False, "expected the fallback branch to render a .theme-chip-grid"
        if ('%s="%s"' % (config_page.DIRTY_SECTION_ATTR, escape_html("Theme"))) not in rendered:
            return False, "expected the fallback .theme-status card to carry data-dirty-section=\"Theme\""
        if rendered.count('name="theme"') != 2:
            return False, "expected 2 theme radios, got %d" % rendered.count('name="theme"')
        return True, ""
    check(
        "theme_fieldset() falls back to the editable D-01 chip grid the moment a second theme is registered (D-04, 06.6.4.1.1-05)",
        _theme_fieldset_falls_back_to_chip_grid_when_multiple_themes_registered)

    def _theme_fieldset_covers_every_registered_theme_with_own_id_and_label():
        # 08-CONTEXT.md D-01/D-02/D-03/D-04, widened by the 08-06 on-glass
        # session (5 themes -> 11): proves the CFG-01 picker absorbs every
        # registered theme purely through the registry - driven from
        # THEME_IDS/theme_label(), not a hardcoded list or count, so this
        # stays true for a future twelfth theme with zero test-file change
        # needed. Deliberately no `len(theme_ids) != N` assertion - that
        # exact literal is what broke every time this registry's membership
        # changed; the real invariant is "every id THEME_IDS actually
        # holds renders its own radio+label", checked below instead.
        rendered = config_page.theme_fieldset("white")
        theme_ids = device_config.THEME_IDS
        if not theme_ids:
            return False, "THEME_IDS is empty - nothing to render"
        for theme_id in theme_ids:
            value_needle = 'value="%s"' % escape_html(theme_id)
            if value_needle not in rendered:
                return False, "expected a radio carrying value=%r, not found in rendered fieldset" % (theme_id,)
            label_needle = escape_html(device_config.theme_label(theme_id))
            if label_needle not in rendered:
                return False, "expected theme %r's plain label %r as visible text, not found" % (theme_id, label_needle)
        return True, ""
    check(
        "theme_fieldset() renders one radio per registered theme, each carrying its own registry id as value and its own plain "
        "label as visible text, with zero hardcoded ids/labels/counts in the assertion itself",
        _theme_fieldset_covers_every_registered_theme_with_own_id_and_label)

    def _theme_fieldset_default_selects_exactly_the_white_option():
        # Phase 15 D-05: theme_fieldset() now always renders a second
        # (arrivals) chip grid alongside the first (departures) one, called
        # here with no explicit theme_arriving override (the default), so
        # the second grid pre-selects the SAME effective theme as the
        # first — doubling the selected-radio count from 1 to 2, one per
        # grid, both landing on White.
        rendered = config_page.theme_fieldset(device_config.DEFAULT_THEME_ID)
        if rendered.count(" checked") != 2:
            return False, "expected exactly two selected radios (one per grid), found %d" % rendered.count(" checked")
        # 06.6.4.1.1-05: the chip's radio carries class="visually-hidden"
        # between value= and checked (matching .runway-card's own radio
        # attribute sequence), so the needle grows an intervening
        # attribute compared to the retired bare radio-list markup.
        white_option_needle = 'value="white" class="visually-hidden" checked'
        if rendered.count(white_option_needle) != 2:
            return False, (
                "expected the white option selected in both grids (expected %r twice), got %d"
                % (white_option_needle, rendered.count(white_option_needle)))
        if rendered.count('theme-chip theme-chip--selected') != 2:
            return False, "expected the White chip's <label> to carry theme-chip--selected in both grids"
        return True, ""
    check(
        "theme_fieldset() rendered with the new default theme id and no arrivals override marks exactly one option "
        "selected PER grid (Phase 15 D-05 doubles this from 1 to 2), and both are White",
        _theme_fieldset_default_selects_exactly_the_white_option)

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
    # 06.6.4.1 Task 1 (D-01, D-02, D-05 form half, D-26): the new
    # single-column, three-wrapped-section, one-merged-form shape.
    # ------------------------------------------------------------------

    def _render_exactly_five_dirty_sections_in_order():
        # Acceptance criterion: the rendered output contains exactly
        # eight elements carrying data-dirty-section, whose attribute
        # values in document order are "Theme", "Runway", "Diagnostic
        # LED", "Quiet hours", "Wake interval", "Display", "Calendar",
        # "Notifications" — 10-05-PLAN.md Task 1 wired Quiet hours in as
        # the fourth group after Diagnostic LED, 11-03-PLAN.md Task 1
        # wired Wake interval in as the fifth, after Quiet hours,
        # 12-05-PLAN.md Task 1 wired Display in as the sixth, after Wake
        # interval, 16-05-PLAN.md Task 1 wired Calendar in as the
        # seventh, after Display (16-UI-SPEC.md Section Anatomy's
        # Placement recommendation), and 20-11-PLAN.md Task 1 wires
        # Notifications in as the eighth and last, after Calendar — the
        # legacy SCOPE_ALL tuple's own trailing position for the group
        # (scope_groups()'s own D-26 comment).
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        found = re.findall(
            r'%s="([^"]*)"' % re.escape(config_page.DIRTY_SECTION_ATTR), rendered)
        expected = [
            "Theme", "Runway", "Diagnostic LED", "Quiet hours",
            "Wake interval", config_page.DISPLAY_SECTION_HEADING, "Calendar",
            "Notifications"]
        if found != expected:
            return False, "expected %r in document order, got %r" % (expected, found)
        return True, ""
    check(
        "render() carries exactly eight data-dirty-section elements, in document order Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display/Calendar/Notifications",
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

    def _theme_and_runway_section_captions_appear_exactly_once():
        rendered = config_page.render({
            "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        theme_caption = escape_html(config_page.THEME_SECTION_CAPTION)
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        if rendered.count(theme_caption) != 1:
            return False, "expected THEME_SECTION_CAPTION exactly once, got %d" % rendered.count(theme_caption)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once, got %d" % rendered.count(runway_caption)
        return True, ""
    check(
        "render() carries THEME_SECTION_CAPTION and RUNWAY_SECTION_CAPTION exactly once each (quick task 260901-re6)",
        _theme_and_runway_section_captions_appear_exactly_once)

    def _each_group_emits_exactly_one_caption_between_heading_and_control():
        # quick task 260901-re6 Task 3: the direct proof of the merge and
        # of the position — the check that would have caught this bug.
        # Calls theme_fieldset()/runway_fieldset()/led_group() directly
        # and asserts each returns markup with exactly one <p occurrence
        # and exactly one section-caption occurrence, with the caption's
        # index falling after the group's own naming element and before
        # the group's control.
        #
        # 06.6.4.1.1-05: theme_fieldset("black") (any valid theme id —
        # "sky" no longer exists post-merge of origin/main) now returns
        # the D-01 chip-grid branch, named by the same <h2 class=
        # "text-heading"> element runway_fieldset()/led_group() already
        # use — its control marker is "theme-chip-grid", not the retired
        # radio-list's bare "options" skip-marker.
        #
        # Phase 15 D-05: theme_fieldset() now emits a SECOND <p> — the
        # "Arrivals theme" label (.theme-direction-label) above the
        # revealed second grid — which is a real, deliberate addition, not
        # a regression of the one-caption-per-section rule: that rule
        # governs section-caption <p> elements specifically (still exactly
        # one, asserted below unchanged), and the new <p> carries a
        # different class entirely. theme_fieldset() is therefore the one
        # group in this table with an expected <p> count of 2, not 1.
        theme_rendered = config_page.theme_fieldset("black")
        runway_rendered = config_page.runway_fieldset("3")
        led_rendered = config_page.led_group(True)
        groups = (
            ("theme_fieldset()", theme_rendered, "</h2>", "theme-chip-grid", 2),
            ("runway_fieldset()", runway_rendered, "</h2>", "runway-row", 1),
            ("led_group()", led_rendered, "</h2>", "settings-checkbox", 1),
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
        "theme_fieldset()/runway_fieldset()/led_group() each emit exactly one section-caption <p> element, positioned after the group's own naming element and before its control (quick task 260901-re6, merge of origin/main)",
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
        theme_caption = escape_html(config_page.THEME_SECTION_CAPTION)
        runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
        led_caption = escape_html(config_page.LED_SECTION_CAPTION)
        poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
        if rendered.count(theme_caption) != 1:
            return False, "expected THEME_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(theme_caption)
        if rendered.count(runway_caption) != 1:
            return False, "expected RUNWAY_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(runway_caption)
        if rendered.count(led_caption) != 1:
            return False, "expected LED_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(led_caption)
        if rendered.count(poll_caption) != 1:
            return False, "expected POLL_SECTION_CAPTION exactly once (escaped-verbatim), got %d" % rendered.count(poll_caption)
        return True, ""
    check(
        "the theme, runway, LED, and poll section captions all appear escaped-verbatim exactly once in render()'s output (quick task 260901-re6, quick task 260901-s5o)",
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
        if 'value="black" class="visually-hidden" checked' not in rendered:
            return False, "expected the saved theme (black) to be marked selected via its radio input"
        # Phase 15 D-05: with no theme_arriving override in device_config,
        # theme_fieldset()'s second (arrivals) grid pre-selects the SAME
        # effective theme as the first (departures) grid — doubling this
        # count from 1 to 2, one per grid, both landing on "black".
        # 20-09-PLAN.md Tasks 1/3 (D-14d/D-15b): SCOPE_ALL's legacy render
        # also carries Calendar's own compact chip grid and the Flight-
        # colours add form's compact chip grid — two more single-
        # selection compact grids, +2 more (one each), for 4 total.
        if rendered.count("theme-chip--selected") != 4:
            return False, (
                "expected exactly four theme-chip--selected modifiers (Theme's two grids plus "
                "Calendar's and Flight-colours' own compact grids), got %d"
                % rendered.count("theme-chip--selected"))
        return True, ""
    check(
        "the currently-saved theme is shown current in both of Theme's own chip grids (Phase 15 D-05 "
        "doubles this from 1 to 2 absent an arrivals override), Calendar's and Flight-colours' own "
        "compact chip grids each mark their own default selection too (4 total), and the (non-default) "
        "saved runway card is the one marked selected",
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
            if on_disk != {"theme": "black", "theme_arriving": None, "calendar_theme_id": None, "tracked_runway": "06-24", "led_enabled": False, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "display_enabled": False, "wake_interval_s": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": False, "frame_silent": False, "lang": "en"}}:
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
    def _handle_post_empty_form_persists_led_false():
        # Bullet 1: the shape a browser sends when nothing is checked and
        # nothing is selected.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post({}, ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected led_enabled False on disk, got %r" % (on_disk["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post({}, ctx) - the shape a browser sends when nothing is checked and nothing is selected - persists led_enabled False and returns the saved flash key",
        _handle_post_empty_form_persists_led_false)

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
        input_match = re.search(r'<input type="number" name="wake_interval_s"[^>]*>', rendered)
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
            submitted={"theme": "black"})
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
        # 20-09-PLAN.md Task 1 (D-14c): the write-only calendar_url field
        # moved out of render()'s own errors/submitted plumbing entirely,
        # into calendar_connect_section()'s own `errors` parameter — this
        # function never accepts `submitted` at all (nothing to
        # repopulate: the one field it renders is write-only), so there
        # is no submitted URL for it to echo in the first place.
        rendered = config_page.calendar_connect_section(False, errors={"calendar_url": "msg"})
        if "msg" not in rendered:
            return False, "expected the calendar_url error message to render"
        if 'name="calendar_url"' not in rendered:
            return False, "expected the calendar_url field itself to still render"
        after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
        if "value=" in after_name:
            return False, "expected no value attribute on the calendar_url field even with an error present"
        return True, ""
    check(
        "calendar_connect_section(False, errors={\"calendar_url\": \"msg\"}) renders the error message "
        "under the field while the write-only field itself still carries no value attribute at all "
        "(D-07/T-19-12/D-14c)",
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

    def _dirty_state_js_references_dirty_section_attr_and_has_no_forbidden_syntax():
        source = _read_static("dirty-state.js")
        if config_page.DIRTY_SECTION_ATTR not in source:
            return False, "expected dirty-state.js to reference the literal value of DIRTY_SECTION_ATTR"
        # 19-10-PLAN.md (D-09/A-27): also pins the dirty-ready marker
        # literal, keeping this script and style.css's retargeted
        # fallback-hide selector from drifting apart.
        if "dirty-ready" not in source:
            return False, "expected dirty-state.js to reference the literal string dirty-ready"
        for forbidden in ("innerHTML", "let ", "const ", "=>", "`"):
            if forbidden in source:
                return False, "forbidden ES5-unsafe/HTML-writing construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js references config_page.DIRTY_SECTION_ATTR's literal value and the dirty-ready marker, and "
        "contains none of innerHTML/let /const /=>/backtick",
        _dirty_state_js_references_dirty_section_attr_and_has_no_forbidden_syntax)

    def _dirty_state_js_sets_dirty_ready_only_after_bar_guard():
        # 19-10-PLAN.md (D-09/A-27): the same source-ordering technique
        # test_companion_app.py's _panel_lookup_optional_replace_lookup_
        # stays_outside_mandatory_guard check already uses - dirty-ready
        # must only ever be set once the bar's existence is proven (the
        # [data-dirty-bar] guard clause), never before it.
        source = _read_static("dirty-state.js")
        if "dirty-ready" not in source or "data-dirty-bar" not in source:
            return False, "expected both dirty-ready and data-dirty-bar to be present in dirty-state.js"
        if source.index("dirty-ready") <= source.index("data-dirty-bar"):
            return False, "expected the first dirty-ready occurrence to come after the first data-dirty-bar occurrence"
        return True, ""
    check(
        "dirty-state.js's first dirty-ready occurrence comes after its first data-dirty-bar occurrence (D-09: set "
        "only after the bar guard passes)",
        _dirty_state_js_sets_dirty_ready_only_after_bar_guard)

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
        beforeunload_idx = source.index("beforeunload")
        # The guard's own listener body must reference countDifferences -
        # reused, never reimplemented as a separate flag that can drift
        # from the bar's own dirty state.
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
        source = _read_static("style.css")
        if config_page.STATIC_SAVE_FALLBACK_ATTR not in source:
            return False, "expected style.css to reference the literal value of STATIC_SAVE_FALLBACK_ATTR"
        idx = source.index(config_page.STATIC_SAVE_FALLBACK_ATTR)
        window = source[idx:idx + 120]
        if "display: none" not in window and "display:none" not in window:
            return False, "expected the fallback-hide rule to set display: none near the attribute reference"
        # 19-10-PLAN.md (D-09/A-27): retargeted from .js to .dirty-ready -
        # the fallback now hides only once dirty-state.js has proven the
        # bar exists, not merely because nav-dropdown.js's unconditional
        # .js class is present. The selector prefix sits BEFORE the
        # attribute reference (".dirty-ready [data-static-save-fallback]"),
        # so widen the window backwards too rather than only forwards.
        selector_window = source[max(0, idx - 40):idx + 120]
        if "dirty-ready" not in selector_window:
            return False, "expected the fallback-hide rule's selector to reference dirty-ready"
        old_selector = ".js [%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR
        if old_selector in source:
            return False, "expected the old .js-gated selector to be gone entirely"
        return True, ""
    check(
        "style.css contains the .dirty-ready-gated fallback-hide rule referencing "
        "config_page.STATIC_SAVE_FALLBACK_ATTR's literal value, and no longer the old .js-gated selector",
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

    def _style_css_needs_no_new_selector_for_display_group():
        # 12-05-PLAN.md Task 2 bullet 5: a cross-file guard that style.css
        # needs no new selector for the Display group - both classes
        # display_group() depends on (.theme-status, .settings-checkbox)
        # are already declared above, matching led_group()'s/
        # quiet_hours_group()'s own precedent (12-UI-SPEC.md: zero new
        # selectors, zero new declarations, zero new design tokens).
        source = _read_static("style.css")
        if ".theme-status {" not in source:
            return False, "expected style.css to already declare a .theme-status rule"
        checkbox_selector = '.settings-checkbox input[type="checkbox"] {'
        if checkbox_selector not in source:
            return False, "expected style.css to already declare a %r rule" % (checkbox_selector,)
        return True, ""
    check(
        "style.css already declares .theme-status and .settings-checkbox - the Display group introduces zero new CSS selectors",
        _style_css_needs_no_new_selector_for_display_group)

    def _theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme():
        # 06.6.4.1.1-05: the cross-module route contract — every chip's
        # <img src> is built from theme_preview.THEME_PREVIEW_ROUTE_PREFIX
        # (rebound as config_page.THEME_PREVIEW_ROUTE_PREFIX) plus the
        # theme's own registry id, asserted against the constant rather
        # than a re-typed literal, for every entry in THEME_IDS.
        rendered = config_page.theme_fieldset("white")
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
        # Phase 15 D-05: theme_fieldset() now renders TWO chip grids (one
        # per THEME_IDS entry each), doubling this count from *2 to *4 —
        # 2 dots per chip, 2 grids.
        rendered = config_page.theme_fieldset("white")
        if rendered.count("theme-chip__dot") != len(device_config.THEME_IDS) * 4:
            return False, (
                "expected exactly %d .theme-chip__dot occurrences (2 per theme, 2 grids), got %d"
                % (len(device_config.THEME_IDS) * 4, rendered.count("theme-chip__dot")))
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
        "every theme chip in both grids carries exactly two .theme-chip__dot swatches whose inline background "
        "values equal _palette_hex() computed from that theme's own departing_index/arriving_index (06.6.4.1.1-05, "
        "doubled to *4 by Phase 15 D-05's second grid)",
        _theme_chip_swatch_dots_carry_real_palette_hex_values)

    def _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip():
        # 06.6.4.1.1-05: the markup half of the CSS-only selection reveal
        # — every chip's radio is visually-hidden (never display:none, so
        # keyboard/no-JS selection keeps working natively), and every chip
        # carries a .theme-chip__check glyph with its visually-hidden
        # "Selected" text, present on all 16 chips regardless of which one
        # is actually selected.
        #
        # Phase 15 D-05: theme_fieldset() now renders TWO chip grids, so
        # the check-glyph and "Selected" text counts double from
        # theme_count to theme_count * 2 (the name="theme" radio count
        # itself stays scoped to the first grid only, since the second
        # grid's radios carry name="theme_arriving" instead).
        rendered = config_page.theme_fieldset("white")
        theme_count = len(device_config.THEME_IDS)
        if rendered.count('name="theme" value="') != theme_count:
            return False, "expected %d theme radios, got %d" % (theme_count, rendered.count('name="theme" value="'))
        if rendered.count('class="visually-hidden"') < theme_count:
            return False, "expected every chip's radio to carry class=\"visually-hidden\""
        if "display:none" in rendered or "display: none" in rendered:
            return False, "expected the radio hidden via the visually-hidden utility class, never display:none"
        if rendered.count('<span class="theme-chip__check">') != theme_count * 2:
            return False, (
                "expected exactly %d .theme-chip__check occurrences (one per chip, regardless of selection, "
                "across both grids), got %d"
                % (theme_count * 2, rendered.count('<span class="theme-chip__check">')))
        if rendered.count('<span class="visually-hidden">Selected</span>') != theme_count * 2:
            return False, "expected every chip's check glyph to carry the visually-hidden \"Selected\" text, across both grids"
        return True, ""
    check(
        "every theme chip's radio carries class=\"visually-hidden\" (never display:none) and every chip in both "
        "grids carries a .theme-chip__check glyph with visually-hidden \"Selected\" text, present on all chips "
        "regardless of selection (06.6.4.1.1-05, doubled by Phase 15 D-05's second grid)",
        _theme_chip_radio_hidden_and_check_glyph_present_on_every_chip)

    # ------------------------------------------------------------------
    # 15-04-PLAN.md (D-04/D-05): the arrivals-override checkbox, its
    # revealed second chip grid, and handle_post()'s clearable-checkbox
    # contract (15-VALIDATION.md row 7).
    # ------------------------------------------------------------------

    def _theme_arriving_markup_both_grids_copy_and_checkbox_present():
        # Task 3 markup checks: both grids present in the rendered
        # Settings page; the second carries name="theme_arriving" radios
        # and the data-arrival-grid attribute; both new copy strings
        # appear escaped-verbatim; the checkbox carries the
        # theme-arriving-toggle id and is nested in a settings-checkbox
        # label; the total preview-image count is exactly twice
        # len(THEME_IDS).
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        })
        if 'class="theme-chip-grid"' not in rendered:
            return False, "expected the first (departures) grid's plain class"
        if 'class="theme-chip-grid theme-chip-grid--arrivals"' not in rendered:
            return False, "expected the second (arrivals) grid's modifier class"
        if config_page.ARRIVAL_GRID_ATTR not in rendered:
            return False, "expected the second grid to carry data-arrival-grid"
        theme_count = len(device_config.THEME_IDS)
        if rendered.count('name="theme_arriving" value="') != theme_count:
            return False, (
                "expected %d theme_arriving radios, got %d"
                % (theme_count, rendered.count('name="theme_arriving" value="')))
        # Pinned as literal copy strings (matching how this harness already
        # pins the existing helper texts), not just via the constant, so a
        # future accidental rewording of the constant's own value is
        # caught here too.
        if "Use a different theme for arrivals" not in rendered:
            return False, "expected THEME_ARRIVING_CHECKBOX_LABEL (\"Use a different theme for arrivals\") escaped-verbatim"
        if "Arrivals theme" not in rendered:
            return False, "expected THEME_DIRECTION_LABEL (\"Arrivals theme\") escaped-verbatim"
        if config_page.THEME_ARRIVING_CHECKBOX_LABEL != "Use a different theme for arrivals":
            return False, "expected THEME_ARRIVING_CHECKBOX_LABEL to equal the locked copy exactly"
        if config_page.THEME_DIRECTION_LABEL != "Arrivals theme":
            return False, "expected THEME_DIRECTION_LABEL to equal the locked copy exactly"
        toggle_match = re.search(
            r'<input[^>]*%s[^>]*>' % re.escape(config_page.THEME_ARRIVING_TOGGLE_ID), rendered)
        if not toggle_match:
            return False, "expected an <input> carrying the theme-arriving-toggle id"
        if 'name="theme_arriving_enabled"' not in toggle_match.group(0):
            return False, "expected the toggle's <input> to carry name=\"theme_arriving_enabled\""
        label_start = rendered.rindex('<label class="settings-checkbox">', 0, toggle_match.start())
        label_end = rendered.index("</label>", label_start)
        if not (label_start < toggle_match.start() < label_end):
            return False, "expected the toggle to be nested inside a <label class=\"settings-checkbox\">"
        # 20-09-PLAN.md Tasks 1/3 (D-14d/D-15b): this ctx carries no
        # calendar/colour_rules keys, but SCOPE_ALL's legacy render still
        # calls calendar_group() and _rules_section_html() unconditionally
        # (show_rules/GROUP_CALENDAR both always present on that scope) —
        # each contributes its OWN compact theme-chip grid (one full set
        # of preview images apiece), so the total is FOUR grids' worth,
        # not two.
        expected_preview_count = 4 * theme_count
        if rendered.count('class="theme-chip__preview"') != expected_preview_count:
            return False, (
                "expected exactly %d theme-chip__preview <img> occurrences (Theme's two grids plus "
                "Calendar's and Flight-colours' own compact grids, one full theme set each), got %d"
                % (expected_preview_count, rendered.count('class="theme-chip__preview"')))
        return True, ""
    check(
        "the rendered Settings page carries both theme chip grids (the plain .theme-chip-grid and its "
        ".theme-chip-grid--arrivals/[data-arrival-grid] sibling), the arrivals checkbox nested in a "
        "settings-checkbox label with id=theme-arriving-toggle, both new copy strings escaped-verbatim, and "
        "exactly 4*len(THEME_IDS) theme-chip__preview images (Theme's two grids plus Calendar's and "
        "Flight-colours' own compact grids, Phase 15 D-05 / 20-09-PLAN.md D-14d/D-15b)",
        _theme_arriving_markup_both_grids_copy_and_checkbox_present)

    def _theme_arriving_override_preselects_second_grid_and_checks_the_box():
        # Task 3 pre-selection checks, the "override stored" half — the
        # "no override" half is already covered by
        # _theme_fieldset_default_selects_exactly_the_white_option and
        # _current_theme_and_runway_are_selected above, both updated in
        # place by this same plan to expect the doubled count.
        rendered = config_page.theme_fieldset("white", "black")
        toggle_match = re.search(
            r'<input[^>]*%s[^>]*>' % re.escape(config_page.THEME_ARRIVING_TOGGLE_ID), rendered)
        if not toggle_match or "checked" not in toggle_match.group(0):
            return False, "expected the arrivals checkbox to render checked when theme_arriving is set"
        grid = rendered.split(config_page.ARRIVAL_GRID_ATTR, 1)[1]
        if not re.search(r'name="theme_arriving" value="black"[^>]*checked', grid):
            return False, "expected the second grid's checked radio to be the stored override (black)"
        if re.search(r'name="theme_arriving" value="white"[^>]*checked', grid):
            return False, "expected the departures theme (white) to NOT be marked selected in the arrivals grid once an override is set"
        return True, ""
    check(
        "theme_fieldset() with a stored theme_arriving override checks the arrivals checkbox and pre-selects "
        "the OVERRIDE (not the departures theme) in the second grid (Phase 15 D-05)",
        _theme_arriving_override_preselects_second_grid_and_checks_the_box)

    def _handle_post_theme_arriving_checked_persists_chosen_id():
        # Task 2 <behavior> bullet 1.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
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
        "handle_post with theme_arriving_enabled=ARRIVING_CHECKBOX_VALUE and a valid theme_arriving persists that id",
        _handle_post_theme_arriving_checked_persists_chosen_id)

    def _handle_post_theme_arriving_checkbox_absent_clears_previous_override():
        # Task 2 <behavior> bullet 2 - the checkbox's absence clears a
        # previously-set override even though theme_arriving itself is
        # still present with a valid id (the always-rendered second grid
        # means a real browser submission always carries it).
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                },
                ctx)
            flash_key = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": device_config.DEFAULT_RUNWAY_ID,
                    "theme_arriving": "black",
                },
                ctx)
            if flash_key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED, got %r" % (flash_key,)
            on_disk = device_config.load_device_config(tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "unchecking the arrivals checkbox failed to clear theme_arriving, got %r"
                    % (on_disk["theme_arriving"],))
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with theme_arriving_enabled absent but theme_arriving still present with a valid id clears "
        "a previously-set override back to None",
        _handle_post_theme_arriving_checkbox_absent_clears_previous_override)

    def _handle_post_crafted_theme_arriving_checkbox_value_rejected():
        # Task 2 <behavior> bullet 3.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "3")
            before = open(device_config.device_config_path(tmpdir), "rb").read()
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {"theme_arriving_enabled": "yes", "theme_arriving": "black"}, ctx)
            after = open(device_config.device_config_path(tmpdir), "rb").read()
            if flash_key != config_page.FLASH_SAVE_FAILED:
                return False, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
            if before != after:
                return False, "expected device_config.json to be byte-identical, it changed"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    check(
        "handle_post with a crafted theme_arriving_enabled value (\"yes\") rejects the whole submission and "
        "writes nothing",
        _handle_post_crafted_theme_arriving_checkbox_value_rejected)

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
                    {
                        "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
                        "theme_arriving": payload,
                    },
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
        "SQL-shaped payload) rejects the whole submission and writes nothing",
        _handle_post_nonmember_theme_arriving_rejected)

    def _handle_post_theme_arriving_partial_post_still_carries_other_fields():
        # Task 2 <behavior> bullet 5: every other field's behaviour is
        # unchanged - a partial-field post still carries the other
        # settings forward.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            _write_device_config(tmpdir, "black", "06-24")
            ctx = {"state_dir": tmpdir}
            flash_key = config_page.handle_post(
                {
                    "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
                    "theme_arriving": "white",
                },
                ctx)
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
        "a post carrying only theme_arriving_enabled/theme_arriving still carries the existing theme/runway "
        "forward unchanged",
        _handle_post_theme_arriving_partial_post_still_carries_other_fields)

    def _theme_arriving_clearable_contract_full_round_trip():
        # 15-VALIDATION.md row 7 - the acceptance criterion the whole plan
        # exists for. Named so a failure says plainly that unchecking the
        # box failed to clear the override. Proves the full sequence: save
        # with the box checked and a chosen arrivals theme (confirm it
        # persisted), save again with the checkbox key simply absent and
        # theme_arriving still present with a valid id (confirm
        # theme_arriving comes back None), and confirm every other
        # setting from the first save survived the second save unchanged.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-page-unit-")
        try:
            ctx = {"state_dir": tmpdir}
            first = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                },
                ctx)
            if first != config_page.FLASH_SAVED:
                return False, "expected the first (checked) save to return FLASH_SAVED, got %r" % (first,)
            after_first = device_config.load_device_config(tmpdir)
            if after_first["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' to persist after the checked save, got %r"
                    % (after_first["theme_arriving"],))

            second = config_page.handle_post(
                {
                    "theme": "white", "tracked_runway": "06-24",
                    "led_enabled": config_page.LED_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                },
                ctx)
            if second != config_page.FLASH_SAVED:
                return False, "expected the second (unchecked) save to return FLASH_SAVED, got %r" % (second,)
            after_second = device_config.load_device_config(tmpdir)
            if after_second["theme_arriving"] is not None:
                return False, (
                    "unchecking the arrivals checkbox failed to clear the override - expected theme_arriving "
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
        "the clearable contract (15-VALIDATION.md row 7): a checked save with a chosen arrivals theme persists it, "
        "then an unchecked save (with theme_arriving still present) clears it back to None while every other "
        "setting survives unchanged - fails loudly if unchecking stops clearing the override",
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
        # 20-11-PLAN.md Task 1: the count is 8, not 7, now that
        # Notifications joined as the eighth and last group — again not
        # a rename of this check's own premise.
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "poll_cooldown_remaining": 0,
        })
        if "<fieldset" in rendered:
            return False, "expected zero <fieldset> elements on the rendered Settings page"
        if "<legend" in rendered:
            return False, "expected zero <legend> elements on the rendered Settings page"
        if rendered.count(config_page.DIRTY_SECTION_ATTR) != 8:
            return False, (
                "expected exactly 8 %s occurrences (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display/Calendar/Notifications), got %d"
                % (config_page.DIRTY_SECTION_ATTR, rendered.count(config_page.DIRTY_SECTION_ATTR)))
        return True, ""
    check(
        "the rendered Settings page contains no <fieldset> and no <legend>, and exactly eight "
        "data-dirty-section groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display/Calendar/Notifications)",
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
        if "border: 2px solid var(--color-accent);" not in window:
            return False, ".runway-card--selected must keep its existing 2px accent border"
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
        "idiom, added alongside (not replacing) their existing border and check glyph (06.6.4.1.1-06)",
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

        # Phase 15 D-05 adds a SECOND @supports selector(:has(*)) block —
        # the arrivals-checkbox CSS-only reveal — placed after this one
        # (the live-selection-state block quick task 260904-bbi added).
        # index() below still resolves to this block's own opening brace
        # (the first occurrence), so every selector-position assertion
        # below (idx < supports_idx meaning "lives inside this block")
        # is unaffected by the second, later block's existence.
        supports_marker = "@supports selector(:has(*)) {"
        if source.count(supports_marker) != 2:
            return False, (
                "expected exactly two %r blocks (this live-selection-state one, plus Phase 15 D-05's "
                "arrivals-reveal one), got %d" % (supports_marker, source.count(supports_marker)))
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

        # Theme chip: strong border, body wash, check glyph shown.
        body, err = _rule_body(".theme-chip:has(input:checked) {")
        if body is None:
            return False, err
        if "border: 2px solid var(--color-accent);" not in body:
            return False, ".theme-chip:has(input:checked) must carry the 2px accent border"

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
        if "box-shadow: none;" not in window:
            return False, ".theme-chip:has(input:checked):hover must clear the hover shadow"

        # Runway card: strong border + wash on one rule (no body wrapper),
        # check glyph shown.
        body, err = _rule_body(".runway-card:has(input:checked) {")
        if body is None:
            return False, err
        if "border: 2px solid var(--color-accent);" not in body:
            return False, ".runway-card:has(input:checked) must carry the 2px accent border"
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
        if "box-shadow: none;" not in window:
            return False, ".runway-card:has(input:checked):hover must clear the hover shadow"

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

        return True, ""
    check(
        "the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore) is keyed to "
        "live :has(input:checked) state inside one @supports selector(:has(*)) block, for both .theme-chip and "
        ".runway-card, with every pre-existing --selected fallback rule surviving verbatim (quick task 260904-bbi)",
        _strong_selected_treatment_is_keyed_to_the_live_checked_radio)

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

        current_literal = 'content: "Current";'
        if source.count(current_literal) != 2:
            return False, (
                "expected exactly 2 occurrences of %r, got %d" % (current_literal, source.count(current_literal)))

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
        "wash/check glyph cleared and an English \"Current\" ::after tag (exactly 2 occurrences site-wide, zero "
        "French copy), reusing the established muted-text strength rather than inventing a new one "
        "(quick task 260904-bbi)",
        _saved_but_unchecked_card_degrades_to_a_quiet_current_marker)

    def _style_css_carries_section_caption_and_restyled_fixed_dirty_bar():
        # quick task 260901-re6 Task 3: the third new cross-file guard,
        # following the same index-plus-window technique the neighbouring
        # guards above use (never a regex CSS parser). quick task
        # 260901-s5o: retargeted and extended in place (no count change)
        # onto the floating-card treatment.
        source = _read_static("style.css")

        # (a) .section-caption declares only the file's existing 70%
        # muted color-mix idiom.
        caption_selector = ".section-caption {"
        if caption_selector not in source:
            return False, "expected style.css to declare a .section-caption rule"
        idx = source.index(caption_selector)
        window = source[idx:idx + 200]
        if "color-mix(in srgb, var(--color-text) 70%, transparent)" not in window:
            return False, "expected .section-caption's rule body to carry the 70% color-mix muted idiom"

        # (b) the base (non-media-query) .dirty-bar rule is a fully-bordered
        # floating card: dominant surface, a full border (no top-only
        # hairline), the card radius token, and a token-based shadow (no
        # upward-only literal), and no longer carries the old muted
        # --color-secondary surface.
        base_match = re.search(r'^\.dirty-bar \{(.*?)^\}', source, re.MULTILINE | re.DOTALL)
        if not base_match:
            return False, "expected a top-level (non-media-query) .dirty-bar rule"
        base_body = base_match.group(1)
        if "var(--color-dominant)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry var(--color-dominant)"
        if "border: 1px solid var(--color-border)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry a full border: 1px solid var(--color-border) declaration"
        if "border-top:" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry a border-top: declaration"
        if "var(--color-secondary)" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry var(--color-secondary)"
        if "border-radius: var(--radius-card)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry border-radius: var(--radius-card), now load-bearing at every width"
        if "box-shadow: var(--shadow-card-hover)" not in base_body:
            return False, "expected the base .dirty-bar rule body to carry box-shadow: var(--shadow-card-hover) as its first shadow layer"
        if "box-shadow: 0 -" in base_body:
            return False, "expected the base .dirty-bar rule body to no longer carry the retired upward-only literal shadow"

        # (c) the >=960px .dirty-bar rule is fixed, not sticky, and no
        # .dirty-bar rule body anywhere still says position: sticky.
        media_match = re.search(r'^  \.dirty-bar \{(.*?)^  \}', source, re.MULTILINE | re.DOTALL)
        if not media_match:
            return False, "expected an indented (>=960px media query) .dirty-bar rule"
        media_body = media_match.group(1)
        if "position: fixed" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry position: fixed"
        if "position: sticky" in base_body or "position: sticky" in media_body:
            return False, "expected no .dirty-bar rule body to carry position: sticky anywhere"

        # (d) the 240px literal the fixed rule's left uses still equals
        # .dashboard-shell's grid-template-columns first track - a
        # duplicated-not-imported must-equal pair with no shared token,
        # now a three-term left expression with the inset as a third addend.
        if "grid-template-columns: 240px" not in source:
            return False, "expected style.css to declare grid-template-columns: 240px on .dashboard-shell"
        if "calc(240px + var(--space-xl) + var(--space-md))" not in media_body:
            return False, "expected the >=960px .dirty-bar rule's left offset to be calc(240px + var(--space-xl) + var(--space-md))"

        # (e) the inset itself: right pulled in by var(--space-md), bottom
        # by the larger var(--space-lg) (260901-s5o direct follow-up: a
        # bigger edge gap reads more clearly as "floating"), max-width
        # reduced by twice the var(--space-md) inset so the cap doesn't
        # silently cancel it above roughly 1712px (where min(1440px, 100%)
        # alone would size the box, flush with .dashboard-main on both
        # sides), and no corner-squaring override left to re-dock the bar.
        if "bottom: var(--space-lg)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry bottom: var(--space-lg)"
        if "right: var(--space-md)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry right: var(--space-md)"
        if "calc(min(1440px, 100%) - var(--space-md) * 2)" not in media_body:
            return False, "expected the >=960px .dirty-bar rule's max-width to be calc(min(1440px, 100%) - var(--space-md) * 2)"
        if "border-radius: 0" in media_body:
            return False, "expected the >=960px .dirty-bar rule body to no longer carry a corner-squaring border-radius: 0 override"

        # (f) 260901-s5o direct follow-up: developer feedback after seeing
        # the floating card live was "correct shape, too wide, not visible
        # enough." `width: fit-content` is the fix for "too wide" - without
        # it, `width:auto` plus both `left` and `right` set non-auto makes
        # the box stretch to fill the whole positioning region (full
        # .dashboard-main width) per the CSS2.1 abs/fixed sizing rules.
        # The >=960px padding override is gone outright now that the bar
        # is compact rather than full-width - it existed only to align a
        # full-width bar's controls with the content gutter, so the base
        # rule's plain padding: var(--space-md) now governs unmodified.
        if "width: fit-content" not in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry width: fit-content, so it sizes to its own content instead of stretching the full column"
        if "padding:" in media_body:
            return False, "expected the >=960px .dirty-bar rule body to carry no padding override - the base rule's padding: var(--space-md) should apply unmodified now that the bar is compact"
        return True, ""
    check(
        "style.css declares .section-caption (70% muted color-mix), the restyled base .dirty-bar as a floating rounded card (full border, radius token, surrounding token-based shadow, no --color-secondary), and the fixed-not-sticky >=960px .dirty-bar rule: inset by var(--space-md)/var(--space-lg) with a correspondingly reduced max-width, no corner-squaring, and width: fit-content so it sizes to its own content instead of stretching the full column (quick task 260901-re6, quick task 260901-s5o, 260901-s5o direct follow-up)",
        _style_css_carries_section_caption_and_restyled_fixed_dirty_bar)

    def _dirty_state_js_has_no_hardcoded_section_names():
        source = _read_static("dirty-state.js")
        for literal in ("Theme", "Runway", "Diagnostic LED"):
            if literal in source:
                return False, "expected no hardcoded occurrence of %r - section labels must come from the DOM" % (literal,)
        return True, ""
    check(
        "dirty-state.js contains no hardcoded occurrence of \"Theme\", \"Runway\", or \"Diagnostic LED\" (labels come from the DOM)",
        _dirty_state_js_has_no_hardcoded_section_names)

    def _dirty_state_js_still_has_no_network_or_timer_sinks():
        source = _read_static("dirty-state.js")
        for forbidden in ("fetch(", "XMLHttpRequest", "setInterval", "setTimeout"):
            if forbidden in source:
                return False, "forbidden network/timer construct found in dirty-state.js: %r" % (forbidden,)
        return True, ""
    check(
        "dirty-state.js still contains no fetch/XMLHttpRequest/setInterval/setTimeout",
        _dirty_state_js_still_has_no_network_or_timer_sinks)

    # ==================================================================
    # 15-05-PLAN.md Task 3 (D-10, D-11, 15-VALIDATION.md row 10): the
    # per-flight colour-rules editor's markup/copy checks.
    # ==================================================================

    def _rules_section_renders_between_form_and_poll_section():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        })
        form_end = rendered.index("</form>")
        rules_pos = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_pos = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        if not (form_end < rules_pos < poll_pos):
            return False, (
                "expected </form> < Rules heading < Poll heading, got positions %d/%d/%d"
                % (form_end, rules_pos, poll_pos))
        return True, ""
    check(
        "render() places the rules section between the settings </form> and the Poll section (Phase 15 D-10)",
        _rules_section_renders_between_form_and_poll_section)

    def _rules_section_empty_state_then_list_once_a_rule_exists():
        empty_ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        rendered = config_page.render(empty_ctx)
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
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
        rendered = config_page.render(filled_ctx)
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
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
        })
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
        })
        copy_strings = (
            config_page.RULES_SECTION_HEADING,
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

    def _rules_section_heading_locked_verbatim():
        # Exact equality is a stronger gate than a substring check, and
        # pins the section heading against 20-UI-SPEC.md's Copywriting
        # Contract literally — "Flight colours" (D-15a) — rather than
        # only via the RULES_SECTION_HEADING constant every check above
        # already reuses.
        if config_page.RULES_SECTION_HEADING != "Flight colours":
            return False, (
                "expected RULES_SECTION_HEADING to equal the locked heading exactly, got %r"
                % (config_page.RULES_SECTION_HEADING,))
        return True, ""
    check(
        "RULES_SECTION_HEADING equals 20-UI-SPEC.md's locked \"Flight colours\" heading exactly (D-15a)",
        _rules_section_heading_locked_verbatim)

    def _rules_no_select_and_three_named_radios_one_checked():
        rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        })
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
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
        })
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
        })
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
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
            })
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
        if 'class="rule-suggestion-chip" data-kind="callsign" data-value="AFR1380"' not in rules_segment:
            return False, "expected a suggestion chip for the seeded callsign"

        empty_rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
            "state_dir": None,
        })
        rules_start = empty_rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = empty_rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        empty_segment = empty_rendered[rules_start:poll_start]
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
        rendered = config_page.render(ctx)
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
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
        })
        rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
        poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
        rules_segment = rendered[rules_start:poll_start]
        if config_page.DIRTY_SECTION_ATTR in rules_segment:
            return False, "expected the rules section to carry no data-dirty-section attribute"
        return True, ""
    check(
        "the rules section carries no data-dirty-section attribute - it is not part of the tracked "
        "settings form, exactly like the Poll section",
        _rules_section_carries_no_dirty_section_attr)

    def _rules_french_render_shows_french_heading_and_button():
        ctx = {
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
            "poll_cooldown_remaining": 0,
        }
        try:
            prefs.set_request_prefs(lang="fr")
            rendered = config_page.render(ctx)
        finally:
            prefs.set_request_prefs(lang="en")
        if "Couleurs de vol" not in rendered:
            return False, "expected the French heading 'Couleurs de vol'"
        if "Ajouter la règle" not in rendered:
            return False, "expected the French Add-rule button 'Ajouter la règle'"
        return True, ""
    check(
        "a French render of the Flight-colours section shows 'Couleurs de vol' and 'Ajouter la règle' "
        "(D-05)",
        _rules_french_render_shows_french_heading_and_button)

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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
                calendar_last_synced_at=None)
            rendered = config_page.render(ctx)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        for needle in (token, host, path, query_param, url):
            if needle in rendered:
                return False, "expected %r never to appear in the rendered page" % (needle,)
        return True, ""
    check(
        "with the calendar secret file holding a URL carrying a distinctive token, render() never emits "
        "the token, the host, the path segment, or the query-parameter name (T-16-SECRET)",
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
            rendered = config_page.render(ctx)
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
            rendered = config_page.render(ctx)
            rules_start = rendered.index(config_page.RULES_SECTION_HEADING)
            poll_start = rendered.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
            rules_segment = rendered[rules_start:poll_start]
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
        # 20-09-PLAN.md Task 1 (D-14d): the retired <select> is replaced
        # by the compact theme-chip grid — the third consumer of
        # _theme_chip_grid_html(), after Theme's own two grids.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx)
        if rendered.count('name="calendar_theme_id"') != len(device_config.THEME_IDS):
            return False, (
                "expected one calendar_theme_id radio per THEME_IDS member, got %d"
                % rendered.count('name="calendar_theme_id"'))
        grid_match = re.search(
            r'<div class="theme-chip-grid theme-chip-grid--compact" role="radiogroup" '
            r'aria-labelledby="%s">(.*?)</div>\s*(?:<p|<details|</div>)'
            % re.escape(config_page.CALENDAR_HEADING_ID),
            rendered, re.S)
        if not grid_match:
            return False, "expected the calendar theme grid carrying role=radiogroup and aria-labelledby"
        options = re.findall(r'name="calendar_theme_id" value="([^"]*)"', grid_match.group(1))
        if options != list(device_config.THEME_IDS):
            return False, "expected radios in THEME_IDS order, got %r" % (options,)
        return True, ""
    check(
        "the Calendar card's compact theme-chip grid carries exactly one calendar_theme_id radio per "
        "THEME_IDS member in order, with role=radiogroup and aria-labelledby pointing at the card's own "
        "heading (D-14d)",
        _calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order)

    def _calendar_theme_chip_grid_saved_value_is_checked():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], calendar_theme_id="black")
        rendered = config_page.render(ctx)
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
        "radio does (D-14d)",
        _calendar_theme_chip_grid_saved_value_is_checked)

    def _calendar_theme_chip_grid_defaults_to_base_theme_when_unset():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        ctx["device_config"] = dict(ctx["device_config"], theme="black")
        rendered = config_page.render(ctx)
        checked_ids = re.findall(
            r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
            rendered)
        if checked_ids != ["black"]:
            return False, (
                "expected the currently-selected base theme ('black') checked by default, got %r"
                % (checked_ids,))
        return True, ""
    check(
        "with no saved calendar_theme_id, the chip matching the currently-selected base theme is checked "
        "by default (D-14d)",
        _calendar_theme_chip_grid_defaults_to_base_theme_when_unset)

    def _calendar_placement_after_display_before_form_close_with_dirty_attr():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx)
        display_index = rendered.index(
            '<h2 class="text-heading">%s</h2>' % config_page.DISPLAY_SECTION_HEADING)
        # 20-09-PLAN.md Task 1 (D-14d): the Calendar heading now carries
        # its own id (the compact chip grid's aria-labelledby target).
        calendar_index = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.CALENDAR_HEADING_ID, config_page.CALENDAR_SECTION_HEADING))
        # 20-07-PLAN.md Task 2 (D-19): display_group() now embeds its own
        # small quick-action <form>, which closes well before the
        # settings form's own closing tag — the FIRST "</form>" in the
        # whole document is that inner form's, not the settings form's.
        # The real one is the first "</form>" AFTER the Calendar heading
        # (Calendar itself embeds no form of its own).
        form_close_index = rendered.index("</form>", calendar_index)
        if not (display_index < calendar_index < form_close_index):
            return False, (
                "expected Display < Calendar < </form>, got %d, %d, %d"
                % (display_index, calendar_index, form_close_index))
        if '%s="%s"' % (config_page.DIRTY_SECTION_ATTR, config_page.CALENDAR_SECTION_HEADING) not in rendered:
            return False, "expected the Calendar group to carry the dirty-section attribute"
        return True, ""
    check(
        "the Calendar heading's index is greater than Display's and less than the settings form's closing "
        "tag, and the group carries the dirty-section attribute",
        _calendar_placement_after_display_before_form_close_with_dirty_attr)

    def _calendar_group_no_inline_js_and_chip_grid_within_form():
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
        rendered = config_page.render(ctx)
        form_start = rendered.index('<form class="config-form"')
        grid_index = rendered.index('name="calendar_theme_id"')
        # 20-07-PLAN.md Task 2 (D-19): the first "</form>" in the whole
        # document is now display_group()'s own small quick-action
        # <form>, which closes before the calendar_theme_id chip grid
        # even renders (Calendar follows Display in SCOPE_ALL's fixed
        # order) — the real settings-form closing tag is the first
        # "</form>" AFTER the chip grid itself.
        form_end = rendered.index("</form>", grid_index) + len("</form>")
        if not (form_start < grid_index < form_end):
            return False, "expected the calendar_theme_id chip grid to sit inside the settings form"
        calendar_start = rendered.index(
            '%s="%s"' % (config_page.DIRTY_SECTION_ATTR, config_page.CALENDAR_SECTION_HEADING))
        calendar_segment = rendered[calendar_start:form_end]
        if "onclick" in calendar_segment or "onchange" in calendar_segment or "<script" in calendar_segment:
            return False, "expected no inline event-handler attribute or script tag in the Calendar group"
        return True, ""
    check(
        "the Calendar group renders no inline event-handler attribute and no script tag, and its "
        "compact chip grid sits inside the settings form's markup range (no-JS correctness)",
        _calendar_group_no_inline_js_and_chip_grid_within_form)

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
        for payload in ("chartreuse", "", "../../etc/passwd", "sky'; DROP TABLE flights; --"):
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
        "handle_post with a non-member calendar_theme_id (empty string, a plain invalid id, a "
        "path-traversal-shaped payload, and a SQL-shaped payload) rejects the whole submission and writes "
        "nothing",
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
        # 20-09-PLAN.md Task 1/2 (D-14c): the write-only feed-URL field
        # moved OUT of calendar_group() entirely, into its own
        # calendar_connect_section() — calendar_group() itself no longer
        # receives the URL at all (T-20-12: the function that would
        # introduce a leak now structurally cannot).
        for configured in (False, True):
            html = config_page.calendar_connect_section(configured)
            if 'name="calendar_url"' not in html:
                return False, "expected the calendar_url field when configured=%r" % (configured,)
            after_name = html.split('name="calendar_url"', 1)[1].split(">", 1)[0]
            if "value=" in after_name:
                return False, (
                    "expected no value attribute on the calendar_url field when configured=%r"
                    % (configured,))
        return True, ""
    check(
        "the write-only calendar_url field renders in calendar_connect_section()'s own markup for both "
        "the connected and not-connected states and never carries a value attribute (D-14c)",
        _calendar_connect_field_never_carries_value_in_either_state)

    def _calendar_connect_wraps_in_details_only_when_configured():
        # D-14c: "While connected, the URL input is hidden behind a
        # 'Replace the feed URL' disclosure; while not connected, render
        # it unwrapped."
        connected_html = config_page.calendar_connect_section(True)
        if "<details" not in connected_html:
            return False, "expected the connect form wrapped in <details> when configured"
        if escape_html(config_page.CALENDAR_REPLACE_URL_SUMMARY) not in connected_html:
            return False, "expected the Replace-the-feed-URL summary when configured"
        not_connected_html = config_page.calendar_connect_section(False)
        if "<details" in not_connected_html:
            return False, "expected the connect form unwrapped when not configured"
        if 'action="%s"' % config_page.CALENDAR_CONNECT_ROUTE not in not_connected_html:
            return False, "expected the connect form to post to CALENDAR_CONNECT_ROUTE either way"
        return True, ""
    check(
        "calendar_connect_section() wraps its form in <details>'Replace the feed URL' only when "
        "configured, and renders it unwrapped, posting to CALENDAR_CONNECT_ROUTE, when not (D-14c)",
        _calendar_connect_wraps_in_details_only_when_configured)

    def _calendar_containment_at_the_renderer_five_needles():
        # The same five needles _calendar_secret_never_reaches_served_
        # http_bytes() (Section 3, below) uses, applied directly at
        # calendar_group() AND calendar_connect_section() - the two
        # functions that together render everything the Calendar card
        # shows - rather than only at the served-HTTP-bytes boundary or
        # the whole-page render() boundary the two other T-17-SECRET
        # checks already cover.
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
            connect_html = config_page.calendar_connect_section(configured)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        for needle in (token, host, path, query_param, url):
            if needle in group_html or needle in connect_html:
                return False, "expected %r never to appear in calendar_group()/calendar_connect_section()'s own markup" % (needle,)
        return True, ""
    check(
        "calendar_group() and calendar_connect_section(), called directly rather than through render(), "
        "never emit the token, host, path segment, query-parameter name, or whole URL of a configured "
        "calendar (T-17-SECRET, leak caught at the functions that introduce it)",
        _calendar_containment_at_the_renderer_five_needles)

    def _calendar_disconnect_checkbox_never_appears_in_calendar_group():
        # 19-11-PLAN.md Task 1 (D-08/A-26): the in-form disconnect
        # checkbox is retired outright from calendar_group() in EVERY
        # one of its four distinguishable states — disconnecting is now
        # calendar_disconnect_section()'s own standalone, confirmed form,
        # checked separately below.
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

    def _calendar_disconnect_section_appears_only_when_expected():
        for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
            html = config_page.calendar_disconnect_section(configured, drift)
            expected = configured or drift
            has_form = bool(html)
            if has_form != expected:
                return False, (
                    "state %r: expected disconnect-form presence %r, got %r"
                    % ((configured, drift), expected, has_form))
            if has_form:
                if '<form method="post" action="%s"' % config_page.CALENDAR_DISCONNECT_ROUTE not in html:
                    return False, "expected the form to post to CALENDAR_DISCONNECT_ROUTE"
                if 'data-confirm-field' not in html:
                    return False, "expected the hidden confirm field to carry data-confirm-field"
                if 'name="%s" value=""' % config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD not in html:
                    return False, "expected the hidden confirm field to render with an EMPTY value"
                if "data-confirm=" not in html:
                    return False, "expected a data-confirm attribute carrying the confirm question"
        return True, ""
    check(
        "calendar_disconnect_section() renders only when the calendar is connected or drifted, posting "
        "to CALENDAR_DISCONNECT_ROUTE with a hidden, empty, data-confirm-field-carrying confirm field "
        "(D-08/A-26)",
        _calendar_disconnect_section_appears_only_when_expected)

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
        # from SCOPE_DEVICE to SCOPE_DISPLAY in place.
        ctx = dict(_CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        settings_form_close = rendered.find("</form>")
        disconnect_form_open = rendered.find(
            '<form method="post" action="%s"' % config_page.CALENDAR_DISCONNECT_ROUTE)
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
        "Device by 20-07-PLAN.md Task 1/D-11)",
        _calendar_disconnect_form_is_not_inside_settings_form_on_display_scope)

    def _calendar_connect_form_appears_before_the_runway_card_on_display_scope():
        # Polish fix 4 (D-14c): calendar_connect_section() used to render
        # after the WHOLE Display scope — below Runway and Flight
        # colours — far from the Calendar card. It now renders
        # immediately after </form> closes (which itself now closes
        # right after the Calendar card, since "What it watches"/Runway
        # moved to a later sibling supersection), so its own <form>'s
        # opening tag appears strictly BEFORE the Runway card's own
        # radio input in document order.
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
        verdict, detail = _calendar_status_parts(config_page.render(ctx))
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
        # on, in that document order, and nowhere on the Device scope
        # (Device's own intro sentence/caption are explicitly unchanged,
        # per D-12 — no supersection tier there at all).
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
        if "section-intro" in device:
            return False, "expected no section-intro on the Device scope (D-12: unchanged intro/caption)"
        return True, ""
    check(
        "the Display scope renders exactly three section-intro headings, in the locked Look/What it "
        "watches/When it is on order, and the Device scope renders none (D-12)",
        _display_render_carries_three_section_intros_in_locked_order)

    def _every_grouped_card_under_a_display_supersection_carries_nested_class():
        # 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C):
        # Theme, Calendar, Runway, Display and Quiet hours each gain the
        # --nested modifier so their own <h2> renders at the extended
        # .theme-status--nested/.page-section--nested > h2 tier
        # (20-04-PLAN.md Task 1's own CSS selector).
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
        if nested_count < 5:
            return False, "expected at least 5 --nested occurrences on Display, got %d" % nested_count
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
        expected = [
            # 21-04-PLAN.md Task 1 (D-01/D-02): the shared Frame strip's
            # own <h2> is now the very first heading on the page,
            # before "Look" — it renders outside <form id="settings-
            # form"> entirely, immediately after the page header.
            layout.FRAME_STRIP_HEADING,
            config_page.DISPLAY_LOOK_HEADING, "Theme", config_page.RULES_SECTION_HEADING,
            config_page.CALENDAR_SECTION_HEADING, config_page.DISPLAY_WATCHES_HEADING,
            "Runway", config_page.DISPLAY_ON_HEADING, config_page.DISPLAY_SECTION_HEADING,
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
        "the Display scope's rendered <h2> order is exactly Look, Theme, Flight colours, Calendar, "
        "What it watches, Runway, When it is on, Screen on / off, Quiet hours, and every "
        "calendar_theme_id radio carries a form=\"settings-form\" attribute (D-12 fix, "
        "20-REVIEW.md verification gap)",
        _display_h2_order_matches_d12_after_calendar_placement_fix)

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

    def _four_scheduled_inputs_carry_form_settings_form():
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for needle in (
                '<input type="checkbox" name="display_enabled" value="on" checked form="settings-form"',
                '<input type="checkbox" name="quiet_hours_enabled" value="on" checked form="settings-form"',
                '<input type="time" name="quiet_hours_start" value="22:00" required form="settings-form"',
                '<input type="time" name="quiet_hours_end" value="06:00" required form="settings-form"'):
            if needle not in rendered:
                return False, "expected %r in the rendered Display page" % (needle,)
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
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        for heading in (config_page.DISPLAY_SECTION_HEADING, config_page.QUIET_HOURS_SECTION_HEADING):
            start = rendered.index('<h2 class="text-heading">%s</h2>' % heading)
            next_heading = rendered.find('<h2 class="text-heading"', start + 1)
            segment = rendered[start:next_heading] if next_heading != -1 else rendered[start:]
            if "quick-action" in segment:
                return False, "expected the %r card to carry no quick-action markup" % (heading,)
        return True, ""
    check(
        "neither the Screen on/off card nor the Quiet hours card carries any quick-action markup "
        "any more — both switches moved into the shared Frame strip (D-01/D-02)",
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
        "all four scheduled inputs (display_enabled, quiet_hours_enabled, quiet_hours_start, "
        "quiet_hours_end) carry form=\"settings-form\" via the SETTINGS_FORM_ID constant (D-19)",
        _four_scheduled_inputs_carry_form_settings_form)

    def _applies_next_wake_sentence_appears_exactly_twice():
        # 21-04-PLAN.md Task 1 (D-01/D-02): the constant moved to
        # companion/layout.py along with the switch markup it captions.
        rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
        count = rendered.count(escape_html(layout.QUICK_ACTION_APPLIES_SENTENCE))
        if count != 2:
            return False, (
                "expected the shared instant-switch sentence to appear exactly twice, got %d" % count)
        return True, ""
    check(
        "the shared \"Applies the next time the frame wakes up.\" sentence appears exactly twice on "
        "the Display page — once per instant switch (D-19)",
        _applies_next_wake_sentence_appears_exactly_twice)

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
                             "S’applique la prochaine fois que le cadre se réveille."):
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
                layout.QUICK_ACTION_APPLIES_SENTENCE, config_page.THEME_SECTION_CAPTION,
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
        if 'name="theme_arriving_enabled"' in device or 'name="quiet_hours_enabled"' in device:
            return False, "expected no theme/quiet-hours group on the Device page"
        if display.count('<h1 class="page-title">Display</h1>') != 1:
            return False, "expected the Display page title"
        if device.count('<h1 class="page-title">Device</h1>') != 1:
            return False, "expected the Device page title"
        # 20-07-PLAN.md Task 1 (D-11): Flight colours (the rules section)
        # moved from Device to Display with its Calendar group — Manual
        # refresh (the Poll section) stays Device-only, unaffected.
        if config_page.POLL_SECTION_HEADING in display:
            return False, "expected the manual-refresh section off the Display page"
        if config_page.RULES_SECTION_HEADING not in display:
            return False, "expected the rules (Flight colours) section on the Display page (D-11)"
        if config_page.POLL_SECTION_HEADING not in device:
            return False, "expected the manual-refresh section on the Device page"
        if config_page.RULES_SECTION_HEADING in device:
            return False, "expected the rules (Flight colours) section off the Device page (D-11)"
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
            # Device-page save: no display/quiet fields -> both stay True;
            # its own absent LED box -> False.
            key = config_page.handle_post(
                {"scope": "device", "tracked_runway": "06-24"}, {"state_dir": tmp})
            if key != config_page.FLASH_SAVED:
                return False, "expected FLASH_SAVED for the device-page save, got %r" % key
            cfg = device_config.load_device_config(tmp)
            if cfg["display_enabled"] is not True or cfg["quiet_hours_enabled"] is not True:
                return False, "expected display/quiet-hours carried forward on a device-page save, got %r" % (cfg,)
            if cfg["led_enabled"] is not False or cfg["tracked_runway"] != "06-24":
                return False, "expected the device-page save's own fields to persist, got %r" % (cfg,)
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
            # The legacy unscoped body keeps its absent-means-False contract.
            key = config_page.handle_post({"theme": "white"}, {"state_dir": tmp})
            cfg = device_config.load_device_config(tmp)
            if key != config_page.FLASH_SAVED or cfg["display_enabled"] is not False:
                return False, "expected the legacy unscoped save to keep absent-checkbox-means-False"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "handle_post() treats a checkbox absent from an out-of-scope group as 'leave unchanged' (a Display "
        "save never flips the LED, a Device save never flips the screen or quiet hours), keeps "
        "absent-means-False inside the submitted scope and for the legacy unscoped form, and a "
        "scoped submission without the Calendar group always carries the calendar forward",
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
        for caption in (
                config_page.THEME_SECTION_CAPTION, config_page.RUNWAY_SECTION_CAPTION,
                config_page.LED_SECTION_CAPTION, config_page.QUIET_HOURS_SECTION_CAPTION,
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
        "each of Theme/Runway/LED/Quiet-hours/Wake-interval's own caption gains the '(next wake ≈ "
        "HH:MM)' suffix when the value is known, and is byte-identical to its own constant when it "
        "is not (D-13)",
        _affected_captions_gain_the_suffix_only_when_known)

    def _display_section_caption_never_gains_a_suffix():
        known_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
            "state_dir": "/tmp", "poll_cooldown_remaining": 0,
        }
        # GROUP_DISPLAY is an everyday group (companion/screens.py) — it
        # renders on the Display scope, not Device.
        rendered = config_page.render(known_ctx, scope=config_page.SCOPE_DISPLAY)
        escaped_caption = escape_html(config_page.DISPLAY_SECTION_CAPTION)
        if escaped_caption not in rendered:
            return False, "expected DISPLAY_SECTION_CAPTION to render unchanged"
        if (escaped_caption + " (next wake") in rendered:
            return False, "expected DISPLAY_SECTION_CAPTION to never gain a next-wake suffix (D-01/D-13)"
        return True, ""
    check(
        "DISPLAY_SECTION_CAPTION never gains a next-wake suffix, even when the value is known "
        "(12-CONTEXT.md D-01's own honest ~5-minute-latency exception)",
        _display_section_caption_never_gains_a_suffix)

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
            confirmation = escape_html(
                companion_app.FLASH_MESSAGES[companion_app.FLASH_KEY_SAVED])
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
            status, headers, _ = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=b"")
            if status != 303:
                return False, "expected a 303 redirect on save, got %d" % status
            location = headers.get("Location", "")
            if "flash=saved" not in location:
                return False, "expected the saved flash key in the redirect, got %r" % location
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["led_enabled"] is not False:
                return False, "expected on-disk led_enabled False after an empty-body POST, got %r" % (on_disk["led_enabled"],)
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
            "persists led_enabled False, and a follow-up GET renders the control unchecked"
            % (config_page.SETTINGS_ROUTE, config_page.SETTINGS_ROUTE),
            _settings_post_empty_body_persists_led_false_and_renders_unchecked)

        def _settings_form_raw_post_no_js_clears_and_sets_theme_arriving():
            # 15-VALIDATION.md row 11 (the Settings-form half this plan
            # owns): a raw, URL-encoded POST to the live SETTINGS_ROUTE -
            # no client script involved - once with the arrivals checkbox
            # key present, once with it absent, proving the set/clear
            # contract holds over the real HTTP path, not just in-process.
            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving_enabled": config_page.ARRIVING_CHECKBOX_VALUE,
                    "theme_arriving": "black",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the checked save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] != "black":
                return False, (
                    "expected theme_arriving 'black' after the checked raw POST, got %r"
                    % (on_disk["theme_arriving"],))

            status, _headers, _body = http_request(
                base + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3",
                    "theme_arriving": "black",
                }).encode())
            if status != 303:
                return False, "expected a 303 redirect on the unchecked save, got %d" % status
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme_arriving"] is not None:
                return False, (
                    "expected theme_arriving None after the unchecked raw POST (the checkbox key was simply "
                    "absent), got %r" % (on_disk["theme_arriving"],))
            return True, ""
        check(
            "a raw, URL-encoded no-JS POST to SETTINGS_ROUTE sets theme_arriving when the arrivals checkbox key "
            "is present and clears it back to None when the checkbox key is simply absent, over the real HTTP "
            "path (15-VALIDATION.md row 11, the Settings-form half)",
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
            for needle in (calendar_token, calendar_host, calendar_path, calendar_query_param, calendar_url):
                if needle in body_text:
                    return False, "expected %r never to appear in the served response body" % (needle,)
            return True, ""
        check(
            "with a calendar configured via its secret file to a URL carrying a distinctive token, a real "
            "authenticated HTTP GET of the Settings page never serves the token, the host, the path "
            "segment, or the query-parameter name in the response body (T-16-SECRET, real HTTP round trip)",
            _calendar_secret_never_reaches_served_http_bytes)
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
        input_match = re.search(r'<input type="checkbox" name="led_enabled"[^>]*>', rendered)
        if not input_match:
            return False, "expected the led_enabled checkbox to still render"
        describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
        if not describedby_match:
            return False, "expected an aria-describedby on the errored led_enabled checkbox"
        ids = describedby_match.group(1).split(" ")
        if ids != [config_page.LED_SECTION_CAPTION_ID, "led-enabled-error"]:
            return False, "expected the hint id first, then the error id, got %r" % (ids,)
        return True, ""
    check(
        "a control carrying both a hint and an error (led_enabled, rendered with an errors dict) has "
        "BOTH ids in its aria-describedby, hint first then error, never one overwriting the other "
        "(D-12/A-30)",
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
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
            scope=config_page.SCOPE_DISPLAY)
        if rendered.count('class="theme-live-preview"') != 1:
            return False, (
                "expected exactly one .theme-live-preview figure, got %d"
                % rendered.count('class="theme-live-preview"'))
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

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-page: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
