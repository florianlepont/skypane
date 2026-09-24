#!/usr/bin/env python3
"""companion/test_browser_ux.py — the D-02 browser-level harness
(22-01-PLAN.md Task 1/3, 22-CONTEXT.md D-01/D-02).

Every other harness in this repository compares rendered HTML strings.
None of them parses the real DOM, runs any JavaScript, or fires a real
`click`/`change` event — which is exactly why B1 (companion/static/
dirty-state.js listening on `<form>` itself, never seeing a `change`
from a field attached to it only via `form="settings-form"`) shipped
undetected: every field the bug affected still round-tripped correctly
through `form.elements` in a string-comparison harness, because that
collection is server-side-invisible. This file is the first harness in
the project that drives a real Chromium tab against a real running
`companion/app.py` subprocess, so this exact class of defect can be
pinned by a machine.

Follows every sibling harness's own conventions exactly: a `check(name,
fn)` helper with the same result-collecting shape, a module-level
`EXPECTED_CHECK_COUNT`, and a `main()` returning 0 or 1 — so the pytest
legacy-harness shim (companion/test_legacy_harness_shim.py, 32-13-PLAN.md)
needs zero special-casing for this file.

Two skip gates, both returning exit 0 with a printed `SKIP` line naming
this file and the exact remedy — never a failure — mirroring how the
suite already tolerates the documented macOS Pillow/FreeType digest
mismatch: a missing OPTIONAL capability is a skip, not a red build.
  1. `playwright` itself is not installed (a dev-only dependency, see
     server/requirements-dev.txt's own header comment).
  2. `playwright` is installed but no Chromium binary has been
     downloaded (`python -m playwright install chromium` was never run).

Security constraint, enforced by this file's own code, not only stated
here: every check below navigates ONLY to `Harness.base_url()` — a
`127.0.0.1:<ephemeral-port>` URL naming the exact subprocess this file
itself launched via `companion_app_server.LegacyHarness`. No external
URL is ever constructed or navigated to anywhere in this file.

Reuses `companion_app_server.LegacyHarness` for the subprocess-under-
test rather than inventing a second subprocess pattern (22-RESEARCH.md
Pattern 3): a free loopback port, an isolated `tempfile.mkdtemp()` state
directory, a real `companion/app.py` subprocess, a startup readiness
poll, and a `stop()` that SIGTERMs then SIGKILLs the process group
(33-19-PLAN.md Task 1: repointed from the retired copy of `Harness` the
companion-app harness used to export).

`seed_state_dir()` below reproduces 22-AUDIT.md's own methodology
fixture (36 runway events over 17h, ~40 days of battery history, 3
gallery renders, 2 unresolved prefixes, 1 manual resolution, 2 colour
rules, wake_interval_s 300, quiet hours 23:00-07:00) through the exact
modules companion/app.py and server/poll_loop.py themselves use to
write this data (server/history_db.py, server/device_config.py,
server/plane/manual_resolutions.py, server/plane/colour_rules.py,
server/poll_loop.py's own `_save_to_gallery()`) — never a hand-written
JSON/SQL fixture, which would silently drift from the real writers'
on-disk shape. Deterministic: every timestamp is derived from one fixed
`SEED_BASE_TS`, never `datetime.now()` captured twice.

Battery cadence note: 22-AUDIT.md's own methodology paragraph used a
3h-then-5min cadence across 40 days (order of 10,000 rows) — this
harness instead writes one reading per day across the same 40-day span.
Nothing this plan's checks assert reads the battery trend at all: the
higher-fidelity cadence would only slow every future run of this
already-the-slowest-harness-by-construction file for no assertion
gained. The 40-DAY SPAN itself (not the sub-day cadence) is what
several `server/history_db.py` call sites and `companion/pages/
health_page.py`'s own windowing logic key off, and that is preserved
exactly.

Stdlib + playwright (dev-only, see server/requirements-dev.txt) + PIL
(already a server dependency, transitively imported via
server.plane.render — used here only to hand a real `Image` to
`poll_loop._save_to_gallery()`, never to build a fixture PNG by another
path). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_browser_ux.py
"""
import collections
import io
import os
# MERGE NOTE (origin/main -> claude/phase-30-aspect-rebuilt): `re` is back.
# 31-01-PLAN.md Task 3 correctly dropped it when the last consumer in this
# file left with the extracted preamble; Phase 30's _ASPECT_REPIN_LEDGER
# guard (_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement)
# then added a new one — it greps this file's OWN source for each row's
# `def`, which is what makes it a guard rather than a cross-file
# assumption. Without this line that check is an F821/NameError.
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# test-support/ (companion_app_server, for LegacyHarness/TEST_PASSWORD) -
# this file runs as a standalone script (server/.venv/bin/python3
# companion/test_browser_ux.py), never through pytest, so conftest.py's
# own sys.path insert never runs for it.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from companion import auth, i18n, layout  # noqa: E402
from companion_app_server import LegacyHarness as Harness, TEST_PASSWORD  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page, config_page, history_page)
from server import device_config, history_db  # noqa: E402
from companion import illustration_normalize  # noqa: E402
from server.plane import illustrations, manual_resolutions  # noqa: E402
# 31-01-PLAN.md Task 3: everything below was module-level in this file
# through 31-01's own predecessor commit; it now lives in
# companion.test_browser_ux_helpers so plans 02/03's extracted sibling
# harnesses can import it too, without duplicating ~2,600 lines.
# 31-02-PLAN.md: VIEWPORT_WIDTH_NARROW, _RING_INK_PROBE and
# _TILE_CONTENT_PROBE dropped from this import — their only call sites
# left with the drawings group for
# companion/test_browser_ux_health_drawings.py.
# MERGE NOTE (origin/main -> claude/phase-30-aspect-rebuilt): two names
# move relative to origin/main's own version of this list, both because
# Phase 30 changed WHO CALLS WHAT in this file and for no other reason.
# _SUBMIT_PROBE is ADDED: 31-01 left it out because this file's only
# remaining consumer at the time was inside the extracted preamble, and
# 30-04's calendar-row check (which resolves the calendar palette radio's
# own .form property in a live browser) is a new consumer that stayed
# behind. _operate_with_keyboard is REMOVED: all three of its call sites
# in origin/main's version of this file were the carousel keyboard/pager
# checks 30-03 retired and ledgered to 30-08, whose accordion-shaped
# replacements drive the keyboard through the native radiogroup instead —
# grepped whole-file before dropping it, zero remaining consumers, the
# same retire-with-your-last-consumer discipline 30-03 applied to the
# carousel selector/probe block. It remains exported by the helpers
# module for the two extracted sibling harnesses that still call it.
from companion.test_browser_ux_helpers import (  # noqa: E402
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE, VIEWPORT_WIDTHS_ALL, VIEWPORT_WIDTHS_RESPONSIVE,
    VIEW_TRANSITION_NAMES, VIEW_TRANSITION_ROUTES,
    _assert_hit_target, _assert_js_gate, _assert_no_page_overflow,
    _assert_surfaces_agree, _await_upload_zone, _bar_text, _click_control,
    _commit_field, _display_page_height, _drop_files,
    _guard_armed, _handle_sel, _in_both_themes, _login, _no_js_page,
    _persist_without_js, _quiet_arc_minutes, _save_via_bar, _SUBMIT_PROBE,
    _set_ui_theme, _upload_without_js, _upload_zone_state, _wait_for_bar,
    _wait_for_bar_hidden, seed_state_dir,
)

EXPECTED_CHECK_COUNT = 6  # 22-01-PLAN.md Task 1: one check (the Flights
# detail row), proving the harness itself (subprocess, seed, real
# browser, real selectors) against a behaviour that already works today.
# 22-01-PLAN.md Task 3: +4 (Display reveal/persist across all four
# form=-attached field kinds, the identical Device round trip, the
# fallback-Save-stays-reachable-until-proven-live contract, and Cancel/
# T1/T8 together). 1 + 4 = 5, recomputed directly against the real
# on-disk check(...) call count at execution time (5/5 pass), not
# trusted from arithmetic alone.
# 22-05-PLAN.md Task 3 (D-04): +1. A real-browser proof that activating a
# Frame strip switch with unsaved Display edits present navigates with
# NO beforeunload dialog, while a plain nav-link navigation with the
# same unsaved edit still raises one. The Display reveal/persist check
# above is retargeted in place (its own "Enable-display checkbox" bullet
# is retired along with display_group(), 22-05-PLAN.md Task 1) — no
# count change from that edit. 5 + 1 = 6, recomputed directly against
# the real on-disk check(...) call count at execution time (6/6 pass),
# not trusted from arithmetic alone.
# 22-09-PLAN.md Task 1 (X5): net 0 — the Flights detail-row scenario is
# RETARGETED in place onto the icon-only toggle and extended inside the
# same check(...) call site (no visible text label, a >=44x44 hit area
# measured from the ::before's own computed inset, an accessible name
# that swaps with the state, the script's own clickable marker class,
# the delegated whole-row click, and the interactive-target early return
# proven by the toggle toggling exactly once rather than twice). 6 + 0 =
# 6, recomputed directly against the real on-disk check(...) call count
# at execution time (6/6 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 6
# 22-09-PLAN.md Task 3 (B11): +1 — at a 390px viewport the Flights filter
# count and Clear control report the same bounding-box top. This is
# Phase 18's A-18 regressing a SECOND time, so it is closed this time
# with a measurement that fails if it reopens rather than with an
# inspection. 6 + 1 = 7, recomputed directly against the real on-disk
# check(...) call count at execution time (7/7 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 7
# 22-10-PLAN.md Task 2 (B9): +1 — at a 390px viewport the three runway
# cards report one shared line, equal heights and border-excluded widths
# equal within 1px, each still clearing 44x44. The measured defect was a
# 2 + 1 orphan (150x150, 150x150, then a lone 308x217), which only a real
# layout engine can see. 7 + 1 = 8, recomputed directly against the real
# on-disk check(...) call count at execution time (8/8 pass), not trusted
# from arithmetic alone.
EXPECTED_CHECK_COUNT = 8
# 22-10-PLAN.md Task 3 (D-09, B8/T10): +1 — the no-JS floor asserted at
# this plan's own commit rather than deferred to wave 12, because this
# plan re-homes a control through the cross-DOM form= idiom and converts
# a CSS `content` literal to an attribute read: both can look fine with
# scripts running and be dead without them. 8 + 1 = 9, recomputed
# directly against the real on-disk check(...) call count at execution
# time (9/9 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 9
# 22-11-PLAN.md Task 2 (X7): +1 — at a 390px viewport every Airlines
# illustration grid renders exactly two cards per row, each row's two
# columns equal within 1px, the main grid's cards near 159px, and the
# whole page under a ceiling recalibrated against the audit's measured
# 5800px one-per-row collapse. Only a real layout engine resolves
# `repeat(auto-fill, minmax(200px, 1fr))`,
# which is what silently collapsed to ONE column inside a 342px content
# column — a stylesheet assertion cannot see it. 9 + 1 = 10, recomputed
# directly against the real on-disk check(...) call count at execution
# time (10/10 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 10
# 22-11-PLAN.md Task 3 (B11): +1 — at a 390px viewport the Airlines
# filter count and Clear control report the same bounding-box top, both
# inside the one shared .filter-bar__meta group plan 22-09 introduced,
# adopted verbatim with no per-page variant. This is the second of the
# three filtered pages the audit measured; Health is plan 22-12's. 10 + 1
# = 11, recomputed directly against the real on-disk check(...) call
# count at execution time (11/11 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 11
# 22-12-PLAN.md Task 2 (B12): +1 — at a 1280px viewport, in BOTH
# languages, Health's unresolved-prefix table reports scrollWidth ===
# clientWidth on its .data-table-wrap, the Resolve column sits inside
# that wrap's own box, and no header is clipped. This is the measurement
# that CHOSE the fix rather than one that confirmed it: only a real
# layout engine resolves .data-table's `min-width: max-content` floor
# against six columns of real content, and the numbers it returned
# (wrap 830px; EN 886 / FR 1026 before, EN 830 / FR 900 after stacking
# the timestamp cells, EN 830 / FR 830 after also shortening the two
# French headers) are what proved the shorter-headers lever alone could
# not fit and the card fallback was not needed. 11 + 1 = 12, recomputed
# directly against the real on-disk check(...) call count at execution
# time (12/12 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 12
# 22-12-PLAN.md Task 3 (B11/C5 and D-09): +2 — at 390px Health's filter
# count and Clear report the same bounding-box top inside the one shared
# .filter-bar__meta group (the THIRD and last of the three filtered
# pages the audit measured, Phase 18's A-18 closed for the third time by
# measurement rather than by inspection) and the page header's Updated
# clock carries .time-value and not .mono; and the no-JS floor holds for
# Health at this plan's own commit, with all four tiles rendering their
# label/verdict/detail slots exactly once each, the filter bar, the
# unresolved-prefix rows and a Resolve action that actually navigates.
# 12 + 2 = 14, recomputed directly against the real on-disk check(...)
# call count at execution time (14/14 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 14
# 22-13-PLAN.md Task 3 (X3): +3 — the login card's field and primary
# measured at 390px AND 1280px (same width, filling the card's content
# column, both 44px tall, one shared radius, a 16px gap, against the
# audit's own 225x44-beside-68x30 and 0px-gap measurements); the
# show-password toggle revealing ITSELF at load, swapping aria-pressed
# and its translated name, keeping .copy-btn's synthesized 44x44 hit
# area, and staying absent with scripts blocked while the form still
# signs in; and the lockout countdown ticking from the server's own seed
# and re-enabling both controls at zero, driven by Playwright's clock
# rather than by sleeping through a real five-minute window. The second
# of the three found a real defect no string-comparison harness could
# see: `.copy-btn`'s `display: inline-flex` beat the user-agent
# `[hidden] { display: none }`, so the scripts-blocked page rendered a
# dead toggle until `.login-reveal[hidden]` was added. 14 + 3 = 17,
# recomputed directly against the real on-disk check(...) call count at
# execution time (17/17 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 17
# 22-14-PLAN.md Task 2 (B10/X9/T5): +2 — the two French nav-status
# segments each reporting exactly ONE client rect at both the 240px
# sidebar and 390px (a count only a real layout engine produces; the
# audit measured the old inline run at 207x48 breaking "Screen on ·
# Quiet hours" / "on"), the reminder inside B10's 48px ceiling, the
# reduced dropdown's remaining push inside X9's 220px target, and the
# Home reminder rendering as a <span> with no href whose announced name
# IS the visible state; and D-02's own minimum-set item 3, the mobile
# nav's close path, on both halves of T5 — a descendant's transitionend
# never hiding an OPEN panel, and a close with no transition applying
# the hidden property synchronously instead of waiting for an event that
# never arrives. The first of the two found a real defect no
# string-comparison harness could see, twice over: a stray comment
# terminator (22-10's, and this plan's own first draft) silently dropped
# the rule that followed it, which is what the new structural guard in
# companion/test_status_pages.py now pins. 17 + 2 = 19, recomputed
# directly against the real on-disk check(...) call count at execution
# time (19/19 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 19
# 22-14-PLAN.md Task 3 (D-10, T7): +1 — at 390x844 on Display with a
# real unsaved edit, the save bar and the bottom tab bar both visible,
# their bounding boxes NOT intersecting, both hit-testable at their own
# centre points via elementFromPoint, and the save bar above the tab bar
# on stacking order at the one value it declares at both breakpoints;
# repeated at 1280x900, where the tab bar must be absent and the same
# stacking value must still be there (T7's desktop half); and at both
# widths the page scrolled to its own foot with the last section ending
# above the bar, which is the only way to prove the .dirty-ready
# clearance is big enough rather than merely present. 19 + 1 = 20,
# recomputed directly against the real on-disk check(...) call count at
# execution time (20/20 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 20
# 22-15-PLAN.md Task 2 (T13): +1 — Health's refresh endpoint made to
# fail, then to recover, with Playwright's clock driving the 45s cadence
# and the 45s first retry rung so the check costs no wall clock. It
# proves the three things only a real browser can: the loop does not
# stop (a retry really fires after the failure), a visible NEUTRAL
# .dot--off badge carrying no warn token really appears while the
# "Updating" pill stands down, and the badge really goes away on
# recovery AND computes display: none, which is the only way to see that
# the .banner__pill[hidden] guard is doing its job. The pre-existing B9
# runway-card check was retargeted in place by Task 1 (22-10's stated T6
# border allowance deleted) with no count change. 20 + 1 = 21,
# recomputed directly against the real on-disk check(...) call count at
# execution time (21/21 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 21
# 22-15-PLAN.md Task 3 (T14): +1 — a real double click on the save bar's
# Save, with the POST answered 204 so no new document commits and the
# page under test survives to be clicked again. It proves the one thing
# no source scan can: that the guard's DEFERRED disable really lands
# between the two clicks, which is the whole mechanism (an inline
# disable would drop a named submit button's own name/value from the
# form data set, and the theme and language pickers are built from
# exactly those). It also re-proves the two flows the guard must not
# fight — a real save still persists, a Frame strip switch still
# navigates — with the guard installed. 21 + 1 = 22, recomputed directly
# against the real on-disk check(...) call count at execution time
# (22/22 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 22
# Quick task 260913-bjy (B11): +1 — Home measured against the viewport
# and against its own recent-flight row boxes, in BOTH languages, at
# 390px AND 1280px. B11 is the audit's "no horizontal scrollbar at
# 390px", closed by measurement on Flights (22-09), Airlines (22-11) and
# Health (22-12); Home was its missing FOURTH surface, the one page
# nobody re-measured after 22-07 put the recent-flight time on one line,
# and it had been scrolling sideways in both themes and both languages
# ever since (documentElement.scrollWidth 411 FR / 408 EN against 390).
# The cause was a percentage width cap on `.recent-flight__time`
# resolving against the content-sized `auto` grid track the item itself
# sizes — so it clamped the box to 60% of its OWN content, and
# `white-space: nowrap` left nothing able to reflow into the smaller box.
# That is why this check measures the CARD boundary as well as the
# viewport: the clamp held at every width from 320px to 1440px, and at
# 1280px the age still painted outside its row (right edge 1253 against a
# row ending at 1191) while staying inside the viewport, where scrollWidth
# is blind to it. Mutation-tested by restoring the deleted declaration:
# 22/23, this check the only one red, naming `time-value__age` as the
# element painting past the edge. 22 + 1 = 23, recomputed directly
# against the real on-disk check(...) call count at execution time
# (23/23 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 23
# Quick task 260913-cz6 (B12's cause, third table): +1 — Health's tables
# each measured against their OWN `.data-table-wrap`, at 390px, in both
# languages, with every <details> on the page forced open first. This is
# the first check in this file that measures a page STATE rather than a
# page: the battery readings table sits behind a closed-by-default
# disclosure, so it was invisible to every sweep here, and its overflow
# was invisible even once opened because the WRAP scrolls while
# `document.documentElement.scrollWidth` stays exactly 390. Measured
# before the fix: a 308px wrap against a 432px (FR) / 369px (EN) table,
# 124px over, the Timestamp column alone taking 302px. Mutation-tested by
# reverting the stylesheet rule: 23/24, this check the only one red, and
# it named the table class, the 308px wrap, the 432px table and the
# per-column widths. 23 + 1 = 24, recomputed directly against the real
# on-disk check(...) call count at execution time (24/24 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 24
# Quick task 260913-dgh: +1 — Home's recent-flight callsign measured
# against its OWN content, at 320, 360, 390, 768 AND 1280px, in both
# languages. Every overflow check in this file until now measured a box
# against a CONTAINER; this defect collapses the box itself, so the
# element stayed inside its row and inside the viewport while its text
# painted straight over the time beside it. Measured before the fix:
# a callsign box of 10.9px (FR) / 18.6px (EN) for 57.8px of content at
# 320px, and 50.9px (FR) at 360px — a common Android width, which is why
# this check does not stop at 320. 1280px is measured because the row is
# only 292.4px there and the callsign track had 7.5px of slack against a
# relative-age string with no upper bound. Mutation-tested by reverting
# the stylesheet rule: 24/25, this check the only one red, naming the
# starved callsign, its box and its content width. 24 + 1 = 25,
# recomputed directly against the real on-disk check(...) call count at
# execution time (25/25 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 25
# Quick task 260913-eab: +1 — the GENERAL form of the disclosure check.
# Every <details> on every page (all six authenticated pages plus the
# login page) forced open, at 360, 390 and 1280px in both languages,
# asserting the page never scrolls sideways, nothing paints right of the
# viewport, and no scroll container's content is wider than its own box.
# A collapsed <details> has its contents not laid out at all, so every
# sweep in this file before 260913-cz6 measured pages in their DEFAULT
# state and everything inside a disclosure was invisible BY
# CONSTRUCTION; cz6 pinned exactly one of them, by name, on one page.
# This covers the 26 that exist today (1 Home / 3 Display / 16 Flights /
# 1 Airlines / 4 Health / 1 Device / 0 login, re-derived by running —
# Flights was 37 before 29-03-PLAN.md/CFG-83 paginated it to
# history_page.FLIGHTS_PAGE_SIZE) and any added later without editing
# this file. Each page asserts a minimum
# disclosure count AND that at least one was closed beforehand, so a
# selector change fails it instead of silently measuring nothing.
# Mutation-tested by restoring `min-width: max-content` on
# table.data-table--readings — the exact defect cz6 fixed. With both
# checks present: 24/26, both red. Then again with cz6's own check
# DELETED from this file, because "both went red" does not by itself
# prove this one did the work: 24/25, this check the only red one,
# reporting `.data-table-wrap` at a 278px box against 369px of content
# at 360px/en. It catches the readings-table defect unaided. Restoring
# the rule returns 26/26. 25 + 1 = 26, recomputed directly against the
# real on-disk check(...) call count at execution time (26/26 pass),
# not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 26
# 23-02-PLAN.md Task 1: net 0, and deliberately so. The three
# scripts-blocked checks above were refactored onto one shared
# `_no_js_page()` helper and the repeated inline viewport dicts onto the
# named set below; not one check(...) call site was added, removed or
# retargeted, and not one assertion inside the three was altered. The
# count is recorded IN PLACE rather than re-asserted below because a new
# assignment here would claim a change this plan did not make. Still 26,
# recomputed directly against the real on-disk check(...) call count at
# execution time (26/26 pass), not trusted from arithmetic alone.
# 23-02-PLAN.md Task 2: net 0 again. The general disclosure sweep gained
# a reduced-motion context and nothing else. 26/26, recomputed the same
# way.
# 23-04-PLAN.md Task 2 (D10/CFG-33): +2. The two ways a cross-document
# view transition fails SILENTLY, made loud. (1) Per-route uniqueness of
# every transition name, counted from the COMPUTED value on every element
# of every authenticated route — not from the stylesheet's selectors,
# because the risk is not that the sheet declares a name twice, it is
# that one selector MATCHES twice in a document companion/layout.py
# puts two navigation landmarks into (three until 22-14 removed the
# preferences panel's copy — re-counted here, not carried from the
# brief); a name that matches twice makes the browser drop the whole
# transition with no error anywhere. (2) The
# reduced-motion opt-out, asserted through the CSSOM rather than by
# watching a cross-fade: on the slowest file in the suite a visual timing
# assertion would be a flakiness generator, while the condition guarding
# the at-rule is deterministic and is exactly the property that gets got
# wrong. Mutation-tested, both of them, and both mutations were chosen to
# leave the companion-app harness's source-level motion guard GREEN
# (271/273 throughout) so these two are proven to do the work unaided.
# "Simplifying" the sidebar's selector to the bare `nav` element took the
# first red at 27/28, reporting the name, the count, the route and the
# offending tags (`nav.sidebar-nav`, `nav.tab-bar`); deleting the
# `.page-title` declaration took it red at 27/28 on the declared-set
# guard instead, which is what stops it degenerating into a check that
# passes by measuring nothing. Moving the at-rule out of its
# `no-preference` wrapper while LEAVING that wrapper in the file took the
# second red at 27/28 (live under reduced motion), and narrowing the
# wrapper to a condition that can never match took it red at 27/28 the
# other way (wrapped into something nobody ever sees). 26 + 2 = 28,
# recomputed directly against the real on-disk
# check(...) call count at execution time (28/28 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 28
# 23-05-PLAN.md Task 3 (D14/CFG-34): +4. The ticker's four behavioural
# claims, none of which any string-comparison harness can see. (1) The
# age ADVANCES in a real visible tab — asserted on element TEXT read
# twice with a real wait between the reads, never on a timer internal, a
# check that would otherwise pass on a script ticking a detached node.
# (2) A page reporting itself hidden does no work at all, against a
# CONTROL proving the same age does move while visible — without that
# control the assertion passes on an element that never changes for any
# reason, the vacuity shape 23-03 caught in its own work — and it is
# repainted IMMEDIATELY on return rather than after an interval.
# (3) With scripts blocked at 360px in both languages the element is
# present AND static; presence alone would pass on a page where the
# enhancement had silently taken over. (4) An expired countdown reads
# the server's own translated waiting wording, gains the breathing class
# and never a warn/error/alert one, with the class proven to resolve to
# the stylesheet's single animation.
# Mutation-tested, each isolated so the Python harnesses stay green and
# these four are proven to do the work unaided. Stopping the script's
# interval took (1) red at 31/32 naming the two equal texts; deleting
# the visibility gate took (2) red at 31/32 naming the two DIFFERENT
# texts a hidden tab should not have produced; both left
# companion-app 279/281 and status-pages 275/276 untouched.
# THE HIDDEN-TAB MECHANISM IS WEAKER THAN A REAL BACKGROUND TAB, and
# says so in its own comment: neither a second page taking focus nor
# CDP's Emulation.setPageVisibilityOverride can hide a page in this
# harness (the first leaves visibilityState "visible" in headless
# Chromium, the second is not implemented in this Chromium at all), so
# the page's own visibility state is overridden in-page and a real
# visibilitychange Event dispatched. What is simulated is the BROWSER'S
# REPORT; what is exercised is the shipped script's own listener and its
# own document.hidden reads.
# 28 + 4 = 32, recomputed directly against the real on-disk check(...)
# call count at execution time (32/32 pass), not trusted from arithmetic
# alone.
EXPECTED_CHECK_COUNT = 32
# 23-06-PLAN.md Task 3 (D1/CFG-35): +6. The three skip rules, the number
# D-12 protects, the fade's condition and the settings page's no-JS
# floor — none of which any string-comparison harness can see.
#
# HOW A REFRESH IS FORCED: the loop's cadence is 45 seconds, so these
# checks drive its own CATCH-UP path — Date.now is shifted forward for
# the duration of one dispatched visibilitychange and restored on the
# next statement (doRefresh() runs synchronously inside the listener).
# What is simulated is the CLOCK; what runs is the shipped script's own
# listener, elapsed comparison and guards.
#
# EVERY ONE OF THE SIX CARRIES ITS OWN CONTROL, because every one of them
# asserts that something did NOT happen and a dead loop satisfies all of
# them:
#  (1) focus: the focused region is CHANGED first so the "unchanged
#      region" skip cannot be what saves it, a second region proves a
#      swap happened at all, and a second phase proves the SAME changed
#      region is replaced once nothing is focused inside it.
#  (2) pending: the same shape — marker injected here because plan 23-07
#      is what sets it in production — with a second phase proving the
#      same region is replaced once the marker is removed.
#  (3) dirty form: REQUESTS are counted, not DOM state, because a page
#      that fetched and then declined to swap is a different and worse
#      behaviour; the control is the same trigger on the clean page.
#  (4) hidden tab: requests counted on ALL THREE pages, each against a
#      control proving that page does fetch while visible. The
#      visibility mechanism is 23-05's and carries its limits in its own
#      comment.
#  (5) the fade: both phases in one check — the same picture must not
#      animate, a genuinely different src must, and the class must
#      resolve to the stylesheet's own fade-in block.
#  (6) no-JS Display: a real save through the fallback Save, at 360px, in
#      both languages, asserted against the config on DISK.
# 32 + 6 = 38, recomputed directly against the real on-disk check(...)
# call count at execution time (38/38 pass), not trusted from arithmetic
# alone.
# 23-07-PLAN.md Task 3 (D2/CFG-36): +4 — the optimistic flip proven to
# land BEFORE the answer (against a held request that has genuinely been
# issued), the rollback proven on BOTH terminal branches in both
# languages with a control phase proving the flip lands first, the
# D1-races-D2 rule proven from the D2 side against the marker the
# SHIPPED script sets, and the scripts-blocked floor for all three
# switches at 360px in both languages. 38 + 4 = 42, re-derived by
# RUNNING.
EXPECTED_CHECK_COUNT = 42
# 23-08-PLAN.md Task 3 (D7/CFG-37 + D3's two Flights clauses): +4 — a
# detection recorded while the page is open proven to arrive at the top
# and be the ONLY thing highlighted (both directions, both renderings,
# with a first-load clause and a nothing-changed clause the empty-known-
# set mutation reddens); the filter proven neither interrupted (requests
# counted, with a control) nor undone by the swap that follows; a
# COLLAPSED detail row proven to let none of its controls take focus,
# against a control phase proving they are reachable once open, plus the
# reveal wrapper's real computed transition; and the phone card proven to
# open from a tap on its own face at 360px with scripts on AND with
# scripts blocked; plus the half a swapped list gets wrong silently — a
# refresh neither unfolding the whole table nor closing the row that was
# opened, proven by EVENT identity against a renumbering insertion and
# with focus blurred so the loop's focus skip cannot be what passes it.
# 42 + 5 = 47, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 47
# 23-09-PLAN.md Task 3 (D3/CFG-32 + T14's deferred label): +3 on the
# app's most-iterated component, which carried B1.
#  (1) the bar ARRIVES: its entrance resolves to the stylesheet's own
#      block rather than merely being declared in a file, a hidden bar
#      still computes display:none with that entrance on it (B1's own
#      collision class, which no source scan can see), and the count —
#      recorded by a MutationObserver installed BEFORE the first edit,
#      so what is measured is the sequence a screen reader would hear —
#      is written once per genuinely different number, never empty,
#      never tweened, and not at all by a real edit that leaves the
#      sentence the same. That last clause has its own control: the
#      trigger is a third theme value, and its landing is asserted, so
#      the clause cannot pass by nothing having happened.
#  (2) the in-flight label, proven not to change the payload: the same
#      edit posted twice, once via requestSubmit() with no submitter (so
#      the relabel stands down by its own first clause) and once via the
#      bar's Save, the two bodies captured ON THE WIRE and compared byte
#      for byte, in both languages, against a control asserting the
#      relabel really ran — plus the completed state read off the page
#      the POST actually lands on.
#  (3) B1's floor with scripts blocked at 360px in both languages,
#      asserting what 23-06's sibling check does not: neither hiding
#      marker on <html>, the bar computing display:none with the
#      entrance declared, and the fallback Save VISIBLE with a real box
#      rather than merely rendered — which is precisely the shape B1
#      took.
# One PRE-EXISTING clause was retargeted in place, contributing nothing
# to this count: T14's "the guard changes no label" assertion, whose own
# message named D3 Phase 23 as the plan that would change it. This is
# that plan.
# 47 + 3 = 50, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 50
# 23-10-PLAN.md Task 1 (D3/CFG-32): +1 — at 390px, selecting a theme chip
# ANSWERS (a scale > 1, a wash that changes, and both transitioning over
# var(--motion-fast)) while its own LAYOUT box and its neighbour's stay
# plain-equal before and after. Only a real layout engine can hold those
# two statements at once, and the offsetWidth/getBoundingClientRect
# distinction between them is the whole reason T6 cannot recur through a
# transform. The three-runway-card check above is extended IN PLACE (no
# count change) to neutralise the transform for its own LAYOUT-box read
# and to prove exactly one card carries the scale. 50 + 1 = 51,
# re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 51
# 23-10-PLAN.md Task 2 (D3/CFG-32): +2. One measures both <dialog>s
# mid-flight two frames after their trigger (a real entrance is running,
# not an instant open), settling opaque, and then hit-tests the viewport
# centre immediately after close() with NO settle wait — the close path
# is the half no source scan can see, and a modal left displayed is an
# invisible sheet that swallows every click beneath it (T-23-36). One
# asserts the live preview's SETTLED src after the crossfade (settling on
# the wrong theme is T-23-38, and it looks identical to a correct
# stylesheet and a correct script read separately) and that Cancel
# restores the saved theme THROUGH the crossfade rather than around it
# (T8). 51 + 2 = 53, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 53
# 23-10-PLAN.md Task 3 (D3/CFG-32): +1 — Home's frame picture and a theme
# chip's preview band each reserve their FINAL box before their image
# arrives, measured at the 360px contract floor and at 1280px by HOLDING
# the real image request rather than racing it. This is the only
# assertion that proves a skeleton did what it was for, and the defect it
# found was real: Home's picture measured 2x2 before the image resolved
# and 380x506 after, a ~500px jump at 1280px. The same plan corrects the
# seed fixture's 8x8 stand-in render to the 600x800 the markup itself
# declares, because an image whose loaded ratio is 1:1 against a 3:4
# promise makes this measurement meaningless. 53 + 1 = 54, re-derived by
# RUNNING.
EXPECTED_CHECK_COUNT = 54
# 24-04-PLAN.md Task 4 (CFG-40/CFG-45/D-09): +3 — the battery ring,
# measured where it actually has to be correct. One reads the RESOLVED
# paint of the value arc on both pages in both themes through 24-02's
# theme and computed-paint helpers, and refuses the SVG default, the
# track's own paint, and an unchanged value across the theme switch.
# One reads each arc's bounding box back from the browser, expands it by
# half its RESOLVED stroke width — the half-stroke overhang is the single
# most common way a ring gets clipped, so it is added in the open rather
# than hidden inside a getBBox() option dictionary whose support would
# have to be assumed — and asserts it lies inside the emitter's own
# viewBox. One pins the 360px floor: no body overflow on either page,
# Home's Battery tile exactly as tall as the Frame tile beside it, and
# both rings still rendering AND still painting a dark-mode token with
# scripts blocked through _no_js_page().
#
# The tile assertion is deliberately NOT "all three tiles are equal
# height". Measured on this tree: at 360px `.dashboard-grid` collapses
# to one column and the three are 111.59 / 111.59 / 131.19, so "all
# equal" is FALSE; at 1280px they share a row under `align-items:
# stretch`, so "all equal" is VACUOUS. Comparing Battery against the
# untouched Frame tile's own content height is the property that is
# neither.
# 54 + 3 = 57, re-derived by RUNNING (57/57).
EXPECTED_CHECK_COUNT = 57
# 24-05-PLAN.md Task 3 (CFG-41/CFG-45/D-09): +2 — the battery chart's
# area, marked reading and low-battery threshold, measured rather than
# read. One resolves all four shapes' paint in both themes and asks three
# different questions of them (not the SVG default; the area/line/mark
# sharing one currentColor ink while the threshold deliberately does not;
# every one of them moving when the theme does), then COMPOSITES the
# translucent area over the card's own resolved background and runs the
# result through the app's own contrast formula — "present but invisible"
# is this feature's specific failure mode and a resolved fill alone
# cannot see it. One pins the 360px floor in BOTH languages (French is
# the longer copy), the legend's box against all four axis labels, its
# swatch's real 12x1 measurement — which is what proves the legend's flex
# context is doing something, since an inline <span> ignores width and
# height — the canvas's share of the grid (the legend claiming the
# auto-sized Y-label column squeezes the drawing from 229.97px to ~109px
# while overflowing nothing, and the first version of this check could
# not see it), the mark's edge-hung ink staying inside the card, and all
# four elements rendering and painting dark-mode tokens with scripts
# blocked.
# 57 + 2 = 59, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 59
# 24-06-PLAN.md Task 3 (CFG-42): +2 - the day band. One reads the
# resolved paint of its frame, shaded span and marks in both themes and
# asserts the three are distinguishable from each other and from the
# card (the frame and the span are ONE token at two strengths, so "not
# the SVG default" says nothing about whether they can be told apart).
# One measures the band at the 360px floor in both languages: the mark's
# real rendered width, the canvas's real width with draw.py's spacing
# constant re-derived from it, the hour labels' placement, and the whole
# band again with scripts blocked. Both own an isolated Harness, because
# the shared fixture seeds no check-in on the band's own Paris day.
# 59 + 2 = 61, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 61
# 24-07-PLAN.md Task 3 (CFG-43): +2 - the check-in regularity grid. One
# measures all FOUR cell states in both themes and asserts every one of
# the six pairs stays past the app's own MIN_SIGNAL_PERCEPTUAL_DISTANCE,
# because four states that read as three in dark mode is a defect no
# source scan can see - and that each key swatch composites to exactly
# the colour of the cell it explains, which is the only thing making the
# key and the grid one declaration rather than two. One measures the
# drawing at 360px in both languages (the card's content box re-derived
# against draw.CARD_DRAWING_WIDTH_PX, the cell size against the target-
# size floor, the ink against the viewBox, the label row against the
# canvas), again with scripts blocked, and again at 1280px and 320px
# where the two responsive declarations are each the one doing the work.
# Both own an isolated Harness: the shared fixture's newest device_health
# row is 40 days before SEED_BASE_TS, so the grid's own window holds
# nothing and three of the four states would never be painted.
# 61 + 2 = 63, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 63
# 24-08-PLAN.md Task 3 (CFG-44/CFG-45/D-09): +2 — D4's hero, measured
# where the difference between stacking and shrinking is visible. One
# pins the 360px floor in both languages: one column, the 16px/24px
# proximity that IS the composition asserted as equalities (a 40px gap
# is what parts keeping their own bottom margins render, and it passes
# every "at least" a reader would think to write), the ring still at its
# own declared 36px and the band's canvas still at the 278px draw.py's
# mark spacing was derived from, and both drawings painting inverting
# tokens in both themes through selectors scoped INSIDE the hero. One
# measures the grouping at 360px AND 1280px, asserts the tiles stack at
# the floor and share a row on the desktop (so the stack is a floor
# behaviour rather than the only one), asserts the band gets more room
# as the viewport grows rather than less, runs every one of Home's
# declared refresh-swap selectors through the browser's own selector
# engine, and compares the scripts-blocked layout against the scripted
# one. Both reuse 24-06's band harness, the only fixture in this file
# that seeds check-ins on the band's own Paris day.
# 63 + 2 = 65, re-derived by RUNNING (65/65).
EXPECTED_CHECK_COUNT = 65
# 25-03-PLAN.md Task 3 (CFG-47): +3 — the runway map, measured where it
# has to be correct, and not one of the three measures that it RENDERS.
# One proves the runway still reaches DISK with scripts blocked, at
# 360px and in BOTH shipped languages, through 25-02's operate-submit-
# persist helper (which gains a `cookies` passthrough here so the one
# java_script_enabled=False call site stays one), with the map's
# presence on that page asserted only AFTER the save so it can never
# stand in for it. One proves the map did not break the native
# radiogroup: one ArrowDown moves to the registry's next entry, an
# ArrowDown/ArrowDown/ArrowUp returns to it, zero pointer events fire,
# the recorder proves itself, and the live :has(input:checked) card
# follows the keyboard rather than the saved value. One measures the
# floors at 360px: all three labels hit-tested in THEIR OWN container,
# every drawing fitting inside its card without stretching, no sideways
# page scroll, and the paint as a FLOOR — context/own/selected three
# different colours, each differing between the themes — sampled only
# once the browser's own Web Animations `finished` promise says the
# 180ms fill transition is over, because the first version of that
# clause read an interpolation frame and reported a theme that does not
# invert.
# 65 + 3 = 68, re-derived by RUNNING (68/68).
EXPECTED_CHECK_COUNT = 68
# 25-04-PLAN.md Task 4 (CFG-48/CFG-52): +3 — D17's quiet-hours dial, and
# again not one of the three measures that it RENDERS. One proves the
# window still reaches DISK with scripts blocked, both ends, at 360px and
# in both shipped languages, through 25-02's operate-submit-persist
# helper, then runs the gate in both directions and asserts the
# SERVER-DRAWN arc, the readout, both time inputs, B14's two 24h siblings
# and the three presets are all present on the scripts-blocked page —
# which is what makes this dial's fallback a feature rather than an
# absence. One drags a handle to a point this check computes itself,
# proves the announcement moved ON THE HANDLE rather than on the wrapper,
# proves the save bar woke and the dragged value reached disk, then
# drives the same handle with the keyboard alone (one ArrowRight is one
# stated step; End and Home reach the day's own ends) with zero pointer
# events and the recorder proving itself, clicks a preset and requires
# BOTH handles to move, and reads 23:00→07:00 back as eight hours. One
# measures the floors at 360px: four hit-area measurements in the
# control's OWN container across two windows, the overlapping case
# recorded and its document-order z-rule confirmed, the drawing's box by
# getBoundingClientRect rather than clientWidth, the four anchor hours
# each on their own axis, no sideways page scroll, and the paint as a
# FLOOR — the day and the window two different colours, the grip with an
# edge, and all five differing between the themes.
# 68 + 3 = 71, re-derived by RUNNING (71/71).
EXPECTED_CHECK_COUNT = 71
# 25-05-PLAN.md Task 3 (CFG-49/CFG-52): +3 — D18's wake-interval slider,
# and again not one of the three measures that it RENDERS. One proves the
# interval still reaches DISK with scripts blocked, at 360px and in both
# shipped languages, then runs the gate in both directions, MEASURES both
# gauges' boxes on the scripts-blocked page (a count passes against a
# gauge moved behind the gate), and re-proves the out-of-range trap end to
# end: with 30 s written straight into the config file — the one state
# save_device_config() refuses to create, so the UI cannot produce it —
# the number input carries NO value attribute, no range and no gauge
# render at all, and the whole Settings form still saves a corrected
# value. That last clause is the one defect on this card that takes down
# the WHOLE page rather than one field. One drags the range and requires
# three things to move together (the native number input, the freshness
# sentence and the battery sentence), asserts the script's own wording
# EQUALS the server's for the same two cadences, proves the save bar woke
# and the dragged value reached disk, drives the same control by keyboard
# alone (one ArrowRight is one stated step; End and Home reach
# device_config's own ceiling and floor) with zero pointer events and the
# recorder proving itself, types into the number input and requires the
# range to follow, and asserts at every one of those positions that the
# battery gauge produces NO days figure from this fixture's rising series.
# One measures the floors at 360px: the hit area in the control's OWN
# container, the box by getBoundingClientRect rather than clientWidth,
# the Device page's own no-sideways-scroll baseline, and the paint as a
# FLOOR — both gauges and the control's accent and surface all differing
# between the themes, sampled only once the browser's own Web Animations
# `finished` promise says the 150ms background transition the global
# `input` rule declares is over, because the first version of that clause
# read an interpolation frame and reported a token that does not invert.
# 71 + 3 = 74, re-derived by RUNNING (74/74, 0 SKIPs).
EXPECTED_CHECK_COUNT = 74
# 25-06-PLAN.md Task 1 (CFG-50): +1 — Display's own rendered document
# height at 390px and at 360px, recorded BEFORE this plan changed a byte
# of markup. This is the one item in the phase whose success criterion is
# a MEASUREMENT rather than a behaviour (22-10 recorded X6's height
# target as "NOT met and cannot be by density alone"), so the
# before-number is taken by the same registered instrument that later
# produces the after-number rather than typed into a document by hand
# once the change is in. The check asserts NO target — it asserts only
# that the instrument is pointed at the authenticated Display page, at
# the width asked for, at a document taller than the viewport, and that
# the narrower measurement is not the smaller of the two. There is no
# production behaviour in this task and therefore NO RED PHASE, which is
# stated rather than manufactured.
# 74 + 1 = 75, re-derived by RUNNING the harness (75/75, 0 SKIPs), never
# by arithmetic.
EXPECTED_CHECK_COUNT = 75
# 25-06-PLAN.md Task 4 (CFG-50/D-09): +3 — D5's carousel measured, and
# not one of the three measures that it RENDERS. One proves the theme
# still reaches DISK with scripts blocked, at 360px and in both shipped
# languages, and on that same scripts-blocked page: all eighteen chips
# present, the strip really overflowing and really ONE row (a count
# passes against eighteen chips stacked in a column), the saved radio
# taking focus and one ArrowDown moving the selection — the property
# `display: none` would destroy and `.visually-hidden` exists to keep —
# the <details> OPENING on a click and turning that row into a real grid
# holding the SAME eighteen radios, and no sideways page scroll; then
# the gate in both directions. One drives the strip by keyboard alone at
# one, six and seventeen steps with zero pointer events and the recorder
# proving itself, and asserts at every one of those positions that the
# selected chip is still fully inside the scrollport — the clause the
# carousel adds, and the one that FAILED before the strip reserved a
# chip's width, because the browser only ever scrolls the 1px
# visually-hidden radio into view and stops. It also asserts the live
# preview follows a KEYBOARD selection (the existing crossfade check
# clicks) and that the two pagers scroll forward and exactly back while
# changing no selection at all. One measures the floors at 360px: four
# hit-area measurements in this control's OWN container, the strip's box
# against its panel's content box by getBoundingClientRect, the page's
# own no-sideways-scroll baseline with the grid both shut and open, and
# the paint as a FLOOR — chip name, chip surface, disclosure summary and
# pager chevron all differing between the themes, no name painted in its
# own surface and neither the summary nor the chevron in the canvas
# colour, sampled only once the browser's own Web Animations `finished`
# promise says `.theme-chip`'s transitions are over.
# 75 + 3 = 78, re-derived by RUNNING the harness (78/78, 0 SKIPs), never
# by arithmetic.
EXPECTED_CHECK_COUNT = 78
# 25-07-PLAN.md Task 3 (CFG-51/D19): +3 — D19's artwork drop zone, on
# its OWN isolated Harness() seeded with a Step-B manual entry (name
# saved, no artwork yet), which is the one state where BOTH copies of
# the upload form render at once. Every one of the three restores that
# fixture as its last act.
#
# One is the no-JS floor, and it is the only one in this phase whose
# scriptless proof is an UPLOAD rather than a field save:
# `_persist_without_js()` operates by assigning to `.value`, which the
# browser forbids on `<input type="file">`, so this task adds the stated
# variant `_upload_without_js()` beside it — same `_no_js_page()`, same
# read-the-verdict-off-disk discipline, plus the clause the field case
# has no counterpart for (the illustration route SERVES the artwork back
# afterwards, as an image at illustration_normalize's own frame size).
# It also asserts the gate in both directions on the fallback panel's
# own zone.
#
# One is the equivalence that proves the whole design: the same source
# file stored BYTE-IDENTICALLY whether picked or dropped, with the
# stored file deleted between the two uploads so a drop that never
# reached the server could not pass on the picked file left behind. The
# drop is dispatched through Chromium's DevTools protocol rather than
# synthesised in the page, because panel-lookup.js refuses an untrusted
# drop — so the same check measures BOTH the real gesture and the
# refusal of the fake one. Its floor clauses are measured against the
# INPUT, never against a message: zero files, a wrong type, several at
# once and an oversized file each assign nothing and each say something
# DIFFERENT, with the oversized fixture proved over the app's own cap
# before it is used.
#
# One is the 360px/both-themes floor: the hit target measured in this
# control's own container, no sideways page scroll, the preview box's
# reserved ASPECT RATIO (by getBoundingClientRect, never clientWidth)
# read out of illustration_normalize.py, and the paint as a floor rather
# than a ceiling in both themes.
# 78 + 3 = 81, re-derived by RUNNING the harness (81/81, 0 SKIPs), never
# by arithmetic.
#
# 27-02-PLAN.md Task 4 (CFG-62/CFG-71): +1 — THE arc/handles/caption
# agreement check. 81 + 1 = 82, re-derived by RUNNING (82/82, 0 SKIPs).
#
# 27-03-PLAN.md Task 3 (CFG-64): +1 — the no-JS floor proven to save TO
# DISK after 27-03-PLAN.md Task 2 simplifies the fallback-hide rule to
# the plain .js gate: tracked_runway operated with scripts blocked,
# submitted through the real form, re-read from disk, in both shipped
# languages, with the fallback submit itself asserted present and
# visible AFTER the save
# (_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies).
# 82 + 1 = 83, re-derived by RUNNING.
#
# 27-04-PLAN.md Task 4 (D-04/CFG-63): the dirty save bar is retired and
# auto-save replaces it. A large number of existing checks are RETARGETED
# IN PLACE (no count change): the reveal-and-persist checks (Display,
# Device), the fallback-hides-immediately check, the leave-guard/live-
# preview pair, the tab-bar-overlap check, the double-submit check, the
# freshness-stand-down check, the strip-switch-vs-leave-guard check, the
# status-region-animates-its-element check, the auto-save-posts-the-
# whole-form check, the no-script-fallback-is-the-only-way check, the
# quiet-hours/wake-interval drag-and-key checks (via _set_window()/
# _set_interval()), the arc/handles/caption agreement check, and the
# theme-carousel keyboard check. Added: THE two checks this plan exists
# to ship — _the_save_settles_the_field_the_region_and_disk_agree (+1,
# RENAMED by 28-10-PLAN.md Task 2 to
# _the_bar_settles_the_field_disk_agree_and_the_bar_hides once the save
# bar it now asserts against was itself restored — its own retired
# no-save-button-visible clause is gone, not this check)
# and _a_rejected_value_claims_nothing_the_toast_fires_and_disk_is_
# untouched (+1, RENAMED by 28-10-PLAN.md Task 3 — see that check's own
# comment for why the toast half is gone). 83 + 2 = 85, re-derived by
# RUNNING (85/85, 0 SKIPs).
EXPECTED_CHECK_COUNT = 85

# 27-05-PLAN.md Task 3 (CFG-66): CFG-47's schematic runway map RETIRED.
# -3: the three checks 25-03-PLAN.md Task 3 added above (the map's own
# save-corroboration, its keyboard/paint proof, its 360px floor
# measurement) are gone, named in 27-05-SUMMARY.md, along with the
# `_runway_ids()`/`_SETTLE_STRIPS` helpers only they used. +1:
# _the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_
# floor replaces all three — the map is gone AND the radios AND the
# photographs are not, asserted as ONE relationship (D-32), with the
# touch target the map's own card used to provide now measured in the
# control's own container at 360px in both themes (T-27-05-B) rather
# than assumed. The radios' OWN scripts-blocked save-to-disk proof
# (CFG-64, line ~826 above) is UNCHANGED by this removal.
# 85 - 3 + 1 = 83, re-derived by RUNNING (83/83, 0 SKIPs).
EXPECTED_CHECK_COUNT = 83

# 27-07-PLAN.md Task 2 (CFG-68): +3 — the arrivals grid's own
# scripts-blocked save proof
# (_arrivals_still_saves_with_scripts_blocked_through_its_own_carousel),
# the per-instance disclosure-toggle independence proof
# (_each_carousels_own_disclosure_toggles_only_its_own_strip), and the
# keyboard-keeps-the-chip-in-view proof generalised from departures
# alone to arrivals+calendar
# (_arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed).
# 83 + 3 = 86, re-derived by RUNNING (86/86, 0 SKIPs).
EXPECTED_CHECK_COUNT = 86

# 27-08-PLAN.md Task 2/3 (CFG-69/CFG-70): +2 — the Quiet hours caption
# schedule link's own hit-target-plus-floor proof
# (_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px) and the
# .copy-btn/.row-toggle family's own resolved-not-declared hit-target
# proof (_copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_
# containers). 86 + 2 = 88, re-derived by RUNNING (88/88, 0 SKIPs).
EXPECTED_CHECK_COUNT = 88

# 28-02-PLAN.md Task 2 (CFG-73, Bug B): +1 —
# _the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press, which
# samples the quiet-dial handle's resolved distance from the dial's own
# centre throughout a held press (not just before/after), in both
# themes. 88 + 1 = 89, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 89

# 28-03-PLAN.md Task 3 (CFG-73, Bug A): +1 —
# _the_dial_caption_keeps_its_form_after_every_interaction_kind, which
# reads the caption's ACTUAL DISPLAYED TEXT after each of a drag, a
# keyboard step, a typed field edit and a preset click, asserting the
# decoded endpoints, a non-empty duration equal to the wrapped-
# difference computation worded from the page's own
# layout.DURATION_ATTRS, and the caption's structural shape unchanged
# from the server-rendered reference — in both shipped languages, with
# the preset step crossing midnight. 89 + 1 = 90, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 90

# 28-04-PLAN.md Task 2 (CFG-72): +1 —
# _a_settings_card_title_renders_identically_on_both_settings_pages, THE
# rendered proof: one probe loads both settings pages in one session,
# addresses every settings-card title by structural position, and
# asserts the combined getComputedStyle set across both pages has
# cardinality 1. 90 + 1 = 91, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 91

# 28-05-PLAN.md Task 2 (CFG-75): +1 —
# _scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_
# selects_nothing, which drives all three carousel strips through four
# real intermediate scroll positions each, in both UI themes at the
# 360px floor, independently computing the geometrically centered chip
# (the same nearest-centre getBoundingClientRect arithmetic
# theme-preview.js itself uses) and asserting the live preview matches
# it — proves scroll never selects (no radio's checked state moves, a
# reload shows the SAVED theme) and proves one carousel's scroll never
# reaches a sibling's state (27-07's strip_id-per-instance discipline).
# 91 + 1 = 92, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 92

# 28-10-PLAN.md (CFG-77/CFG-78): -1 — the auto-save helpers/status
# region this file's checks reached through are retired by 28-08's own
# restoration of the pre-Phase-27 save bar. Task 1 retargets nine
# mechanical owners onto the bar (net 0), REMOVES
# _a_double_fire_of_change_before_the_first_save_resolves_coalesces_to_
# one_follow_up and its own _hold_posts() helper outright (its subject,
# fetch coalescing, ceased to exist with the auto-save model rather than
# being dropped for convenience: -1), and Tasks 2/3 rewrite the
# remaining seven owners in place (net 0 each — every rewrite replaces
# one check with one renamed check, never adds or drops a second one).
# 92 - 1 = 91, re-derived by RUNNING (91/91, 0 SKIPs — the two checks
# outside this plan's own seventeen-owner list that were already broken
# by 28-08's merge, #5/#8 in that plan's own SUMMARY.md list of 20, are
# explicitly NOT this plan's — see 28-10-SUMMARY.md's own "Out of Scope"
# section).
EXPECTED_CHECK_COUNT = 91

# 28-11-PLAN.md (CFG-77): +3 — the three checks CFG-77 still owed, with
# no executable coverage anywhere in the phase until this plan. Task 1:
# _section_naming_reflects_the_fields_actually_changed_in_document_order,
# proving the bar names real changed fields in document order (not click
# order), in both languages. Task 2:
# _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_
# dom, proving Annuler's side effects (the theme live preview, the
# quiet-hours dial) by reading the resulting DOM after 28-08's deferred
# tick, never by spying on refresh()/repaintAll(). Task 3:
# _the_leave_guard_re_arms_after_a_new_edit_following_cancel, closing the
# one coverage gap BLOCKER 3 named: a new edit after Cancel re-arms the
# leave-guard. 91 + 3 = 94, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 94

# 28-09-PLAN.md Task 1 (CFG-78): +2 — the single-affordance audit
# (_exactly_one_submit_shaped_control_resolves_to_the_settings_form,
# resolving every submit-shaped control's own .form property in a live
# browser rather than counting <button occurrences) and the runway
# form= regression check
# (_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end,
# closing the path CFG-74(c) named before it was superseded). 94 + 2 =
# 96, re-derived by RUNNING (96/96).
EXPECTED_CHECK_COUNT = 96

# 30-03-PLAN.md Task 3 (CFG-85): -6/+1 = -5. Six checks pinning the
# retiring scroll-snap-strip/pager/disclosure carousel are removed:
# _each_carousels_own_disclosure_toggles_only_its_own_strip and
# _arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed retire
# outright (scroll-into-view and per-carousel disclosure toggling have
# no meaning over a static wrapping grid, so no property survives);
# _keying_the_strip_selects_scrolls_into_view_and_moves_the_preview,
# _scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_
# selects_nothing, _the_carousel_meets_its_floors_at_360px_in_both_themes
# and _the_no_js_floor_holds_for_both_settings_pages are LEDGERED to
# 30-08 — see _ASPECT_REPIN_LEDGER below. Two more checks are NARROWED,
# NOT a net-new or net-removed check(...) call (the SAME registered
# check() survives under a new name: _the_theme_still_saves_with_
# scripts_blocked, _arrivals_still_saves_with_scripts_blocked, so this
# is a RETARGET, matching this file's own established "retargeted
# in place" convention, and contributes 0 to the count) — their deleted
# strip-probe halves are ALSO ledgered, under their OLD (now un-def'd)
# names, since the property that half proved has no home in this file
# any more. Plus one new check, this file's own ledger guard
# (_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement).
# 96 - 6 + 1 = 91, re-derived by RUNNING (91/91 — modulo the 3
# pre-existing FAILs this file's own floor already carries forward
# unchanged from 30-01/30-02, see this plan's own SUMMARY.md).
EXPECTED_CHECK_COUNT = 91

# 30-08-PLAN.md Task 2 (CFG-85): +4 — every remaining _ASPECT_REPIN_
# LEDGER row in this file is cleared this plan (all six, all owed_by
# "30-08"): _keying_the_palette_moves_the_preview,
# _the_preview_follows_hover_and_focus_and_selects_nothing,
# _the_accordion_is_operable_and_saves_with_scripts_blocked (which also
# repays the "<details> disclosure opens on a click" half of the two
# still-saves-with-scripts-blocked rows and the retired no-JS-floor
# row) and _the_palette_meets_its_floors_at_360px_in_both_themes are
# four genuinely NEW check(...) registrations; the two narrowed
# still-saves-with-scripts-blocked checks and the four re-pointed
# .theme-chip/.palette-chip checks (30-04-SUMMARY.md's own "4 new,
# unledgered" inventory) are extended/re-pointed IN PLACE, contributing
# 0 to the count. 91 + 4 = 95, re-derived by RUNNING (92/95 — the same
# 3 pre-existing FAILs this file's own floor carries forward unchanged
# since 30-01, none newly introduced by this plan).
EXPECTED_CHECK_COUNT = 95

# MERGE NOTE (origin/main -> claude/phase-30-aspect-rebuilt): the two
# blocks below are Phase 31's OWN rationale for its OWN changes to this
# file's count, re-based onto Phase 30's 95 rather than onto the 96 both
# phases independently branched from. The two phases touched DISJOINT
# check groups — Phase 31 (CI parallelisation) moved the health-drawings
# and quiet-hours/wake groups out of this file wholesale, Phase 30 (the
# Aspect rebuild) retired and re-pinned the Aspect/Display group in
# place — so neither phase's delta lands on a check the other one
# touched, and the two compose. The arithmetic sentences below are
# restated from 96 to 95 for that reason and no other; nothing about
# WHAT either phase moved or retired is changed here. The live value at
# the end of this chain is re-derived by RUNNING, as always.

# 31-02-PLAN.md (D-04): -11 — the complete 24-04/24-06/24-07/24-08
# drawings series (the battery ring, the battery chart, the day band,
# the regularity grid and the Home hero) moved verbatim to
# companion/test_browser_ux_health_drawings.py, its own independently
# runnable harness, so the suite's worker pool can run it concurrently
# with the rest of this file. 95 - 11 = 84, re-derived by RUNNING the
# reduced file, never by subtracting on paper.
EXPECTED_CHECK_COUNT = 84

# 31-03-PLAN.md (D-04): -9 — the 25-04/25-05 quiet-hours dial and
# wake-interval slider group moved verbatim to
# companion/test_browser_ux_quiet_wake.py, its own independently
# runnable harness, so the suite's worker pool can run it concurrently
# with the rest of this file. 84 - 9 = 75, re-derived by RUNNING the
# reduced file (75/75 registered, 72/75 passing — the same 3
# pre-existing, phase-unrelated FAILs this file's own floor has carried
# since 30-01), never by subtracting on paper.
EXPECTED_CHECK_COUNT = 75

# 30-03-PLAN.md Task 3 (CFG-85): this file's own coverage-gap ledger,
# same five-key row shape and EXPECTED-TO-EMPTY convention as
# companion/test_config_page.py's _ASPECT_REPIN_LEDGER (see that file's
# own header comment for the shared rationale) — kept as a SEPARATE
# tuple rather than a shared import, because each guard reads its OWN
# file's source, which is what makes it a guard rather than a cross-file
# assumption. Every row here is owed by 30-08.
_ASPECT_REPIN_LEDGER = (
    {
        "retired": "_the_theme_still_saves_with_scripts_blocked_through_the_carousel",
        "property": (
            "with scripts blocked, every registry theme's radio is present in the "
            "carousel, the strip really overflows and is one row, keyboard ArrowDown "
            "moves the selection, the <details> disclosure opens on a click and reveals "
            "the same radios, and the pager gate holds in both directions"),
        "replacement": "_the_accordion_is_operable_and_saves_with_scripts_blocked",
        "owed_by": "",
        "why": (
            "every deleted assertion (strip chip count, overflow, keyboard-through-the-"
            "strip, disclosure, pager gate) reads the retiring strip/pager DOM directly; "
            "the markup-agnostic 'radio is present' half already survives renamed as "
            "_the_theme_still_saves_with_scripts_blocked (30-03), now extended by "
            "30-08-PLAN.md Task 2 to prove it holds for a CLOSED row too; the "
            "'<details> disclosure opens on a click' half re-keys onto the real property "
            "left in this row's own landing name — a real pointer click opening a closed "
            "grouped <details> row and closing its previously-open sibling"),
    },
    {
        "retired": "_arrivals_still_saves_with_scripts_blocked_through_its_own_carousel",
        "property": (
            "with scripts blocked, the arrivals row's own strip carries every theme plus "
            "the leading 'Same as departures' chip, really overflows, and its own "
            "<details> disclosure (resolved by walking up from its own strip) opens on a "
            "click"),
        "replacement": "_the_accordion_is_operable_and_saves_with_scripts_blocked",
        "owed_by": "",
        "why": (
            "the same reasoning as the departures twin above — the deleted half reads the "
            "retiring strip/disclosure DOM directly; the markup-agnostic 'radio is "
            "present' half already survives renamed as "
            "_arrivals_still_saves_with_scripts_blocked (30-03), now extended by "
            "30-08-PLAN.md Task 2; the disclosure-opens-on-click half re-keys onto this "
            "row's own landing name, the same generic grouped-<details> proof"),
    },
    {
        "retired": "_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview",
        "property": (
            "arrow-keying the palette's native radiogroup with the keyboard still moves "
            "the live preview to match the newly-selected theme, settled fully opaque"),
        "replacement": "_keying_the_palette_moves_the_preview",
        "owed_by": "",
        "why": (
            "the scroll-into-view and pager assertions this check makes have no "
            "equivalent over a static wrapping grid"),
    },
    {
        "retired": (
            "_scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_selects_"
            "nothing"),
        "property": (
            "hovering or focusing a palette chip previews that theme without ever "
            "writing a radio, firing a change event, or moving a form value — the saved "
            "selection stays untouched until a chip is actually chosen"),
        "replacement": "_the_preview_follows_hover_and_focus_and_selects_nothing",
        "owed_by": "",
        "why": (
            "the scroll-to-centred-chip tracking this check measures has no meaning once "
            "there is nothing to scroll; the replacement re-keys the same preview-is-not-"
            "selection property onto hover/focus. Lands under a different name than this "
            "row originally predicted — the same same-name-repoint guard collision "
            "30-05/30-06/30-07-SUMMARY.md already documented, resolved the same way, and "
            "matching this file's own required SUMMARY artifact name"),
    },
    {
        "retired": "_the_carousel_meets_its_floors_at_360px_in_both_themes",
        "property": (
            "the palette's touch targets, its container geometry, and its paint (chip "
            "name/surface and whatever replaces the disclosure summary/pager chevron) "
            "all meet 30-UI-SPEC.md's Touch Targets table by real hit-testing in their "
            "own containers, as a floor in both UI themes"),
        "replacement": "_the_palette_meets_its_floors_at_360px_in_both_themes",
        "owed_by": "",
        "why": (
            "every geometry/paint assertion this check makes is read off the retiring "
            "strip/pager DOM shape directly"),
    },
    {
        "retired": "_the_no_js_floor_holds_for_both_settings_pages",
        "property": (
            "with scripts blocked, no control on either settings page is unreachable or "
            "unsaveable: every accordion row's controls remain in the form despite being "
            "visually closed, every summary is natively operable by pointer and "
            "keyboard, and a settings save still round-trips to disk"),
        "replacement": "_the_accordion_is_operable_and_saves_with_scripts_blocked",
        "owed_by": "",
        "why": (
            "the retired check's collapsed-usage-panel count (the retired card's own "
            "usage-panel class, named in full at this row's former call site) has no "
            "equivalent mechanism once the colour_usage radiogroup is retired — see "
            "that former call site "
            "for the full requirement-text-vs-approved-design discrepancy the "
            "replacement proves instead, more strongly than a visible-stack claim. Lands "
            "under a different name than this row originally predicted, matching this "
            "plan's own required SUMMARY artifact name — the same same-name-repoint "
            "guard collision 30-05/30-06/30-07-SUMMARY.md already documented"),
    },
)

# --- The view-transition names this app declares (23-04-PLAN.md Task 2,
# D10/CFG-33) and, for each, the authenticated routes on which EXACTLY
# ONE element must carry it. Both halves are asserted: the declared set
# is compared against what the served stylesheet actually declares (so a
# name added, renamed or dropped there fails here rather than silently
# widening the contract), and the routes are compared against the
# rendered documents.
#
# The route lists are structural facts, not preferences, and each one is
# the REASON its selector was chosen over an obvious alternative:
#   .dashboard-sidebar  the <aside>, rendered once per authenticated
#                       document. NOT a shared navigation class: three
#                       navigation copies (sidebar, preferences panel,
#                       tab bar) are in the DOM of every one of these
#                       pages simultaneously, hidden from each other only
#                       by a media query, so a name on a class they share
#                       would be declared three times in one document.
#   .page-title         page_header()'s single <h1>.
#   .preview-frame__image  Home's frame picture, the app's ONLY render
#                       site of that class — hence the one-route list,
#                       which a plan that renders it elsewhere must widen
#                       here on purpose.


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "SKIP companion/test_browser_ux.py — playwright not installed "
            "(dev-only dependency; run "
            "`pip install -r server/requirements-dev.txt` to enable this harness)")
        return 0

    try:
        with sync_playwright() as p:
            probe = p.chromium.launch()
            probe.close()
    except Exception as exc:
        print(
            "SKIP companion/test_browser_ux.py — Chromium launch failed (%r); "
            "run `python -m playwright install chromium`" % (exc,))
        return 0

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

    harness = Harness()
    seed_state_dir(harness.tmpdir)
    harness.start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                # ==========================================================
                # 30-03-PLAN.md Task 3 (CFG-85): this file's own ledger
                # guard, same idiom as companion/test_config_page.py's own
                # (reads THIS file's source via __file__, mirroring the
                # established "check that reads its own project's Python
                # source" pattern).
                # ==========================================================

                def _every_aspect_repin_ledger_row_names_a_live_or_owed_replacement():
                    if not _ASPECT_REPIN_LEDGER:
                        return False, (
                            "_ASPECT_REPIN_LEDGER is empty — this guard must never pass "
                            "vacuously; if every row has genuinely been repaid, this check "
                            "itself should be retired, not left to pass against nothing")
                    with open(os.path.join(HERE, "test_browser_ux.py")) as fh:
                        own_source = fh.read()
                    for row in _ASPECT_REPIN_LEDGER:
                        for key in ("retired", "property", "replacement", "why"):
                            if not row.get(key):
                                return False, "ledger row %r is missing/empty key %r" % (row, key)
                        if "owed_by" not in row:
                            return False, "ledger row %r is missing key 'owed_by'" % (row,)
                        if len(row["property"].split()) < 8:
                            return False, (
                                "ledger row %r's 'property' is under eight words — it must "
                                "name the PROPERTY under test, not restate a selector"
                                % (row["retired"],))
                        if re.search(r"def %s\(" % re.escape(row["retired"]), own_source):
                            return False, (
                                "retired check %r still has a def in this file — a retired "
                                "check left behind is the OTHER failure shape this guard "
                                "exists to catch" % (row["retired"],))
                        if row["owed_by"]:
                            if row["owed_by"] not in ("30-05", "30-06", "30-07", "30-08"):
                                return False, (
                                    "ledger row %r names owed_by=%r, not one of this "
                                    "phase's own later plans" % (row["retired"], row["owed_by"]))
                        else:
                            if not re.search(
                                    r"def %s\(" % re.escape(row["replacement"]), own_source):
                                return False, (
                                    "ledger row %r names owed_by='' (repaid in THIS file) "
                                    "but its replacement %r has no def here — the "
                                    "repayment claim is false"
                                    % (row["retired"], row["replacement"]))
                    return True, ""
                check(
                    "_ASPECT_REPIN_LEDGER is non-empty, every row is well-formed (all five "
                    "keys present, 'property' naming an actual property in at least eight "
                    "words, not a restated selector), no 'retired' name still has a def in "
                    "this file, every 'owed_by' names one of this phase's own later plans, "
                    "and any row claiming repayment IN this file (empty owed_by) names a "
                    "replacement that genuinely has a def here — so a forgotten re-pin is "
                    "a red build, not a silent coverage loss (CFG-85, 30-03-PLAN.md Task 3)",
                    _every_aspect_repin_ledger_row_names_a_live_or_owed_replacement)

                def _flights_detail_row_expands_and_collapses():
                    # 22-09-PLAN.md Task 1 (X5) retargets this scenario
                    # onto the icon-only toggle: the same expand/collapse
                    # contract, plus the three properties only a real
                    # browser can measure — the synthesized 44x44 hit
                    # area, the accessible NAME swapping with the state
                    # (there is no visible label left to read), and the
                    # delegated whole-row click, including its early
                    # return for an interactive target (T-22-32).
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/flights")
                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        if toggle.get_attribute("aria-expanded") != "false":
                            return False, "expected the first row-toggle to start collapsed (aria-expanded=false)"
                        controls_id = toggle.get_attribute("aria-controls")
                        if not controls_id:
                            return False, "expected the row-toggle to carry aria-controls"
                        detail_row = page.locator("#" + controls_id)
                        if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row to start collapsed"

                        # Icon-only: no visible text, a real accessible name.
                        label_text = toggle.inner_text().strip()
                        if any(ch.isalnum() for ch in label_text):
                            # The decorative chevron glyph is the icon,
                            # not a label; any alphanumeric character
                            # here would be a visible text label.
                            return False, (
                                "expected the toggle to render no visible text label, got %r"
                                % (label_text,))
                        collapsed_name = toggle.get_attribute("aria-label")
                        if not collapsed_name:
                            return False, "expected the icon-only toggle to carry an aria-label"

                        # The real hit area: a 22x22 visual box plus the
                        # ::before's negative 11px inset on every side.
                        hit = toggle.evaluate(
                            "el => { var r = el.getBoundingClientRect();"
                            " var s = getComputedStyle(el, '::before');"
                            " return [r.width - parseFloat(s.left) - parseFloat(s.right),"
                            " r.height - parseFloat(s.top) - parseFloat(s.bottom)]; }")
                        if not hit or hit[0] < 44 or hit[1] < 44:
                            return False, (
                                "expected the toggle's hit area to measure at least 44x44 in "
                                "both axes, measured %r" % (hit,))

                        toggle.click()
                        if toggle.get_attribute("aria-expanded") != "true":
                            return False, "expected aria-expanded to flip to true after a click"
                        if "flight-detail-row--collapsed" in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row's collapsed class to be removed after expanding"
                        expanded_name = toggle.get_attribute("aria-label")
                        if expanded_name == collapsed_name:
                            return False, (
                                "expected the accessible name to change with the state, it stayed %r"
                                % (collapsed_name,))
                        # A click ON the toggle must toggle exactly ONCE:
                        # the row's own delegated handler returns early
                        # for an interactive target, so an unguarded
                        # handler would double-toggle back to collapsed.
                        if not expanded_name:
                            return False, "expected an aria-label in the expanded state too"

                        toggle.click()
                        if toggle.get_attribute("aria-expanded") != "false":
                            return False, "expected aria-expanded to flip back to false after a second click"
                        if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
                            return False, "expected the detail row's collapsed class to return after collapsing"
                        if toggle.get_attribute("aria-label") != collapsed_name:
                            return False, "expected the collapsed accessible name to return"

                        # The whole row is clickable: a click on a plain,
                        # non-interactive cell expands the same row.
                        row = page.locator("[data-flight-row]").first
                        if "flight-row--clickable" not in (row.get_attribute("class") or ""):
                            return False, (
                                "expected flight-rows.js to add its own clickable marker class "
                                "to each summary row at load")
                        row.locator("td").nth(2).click()
                        if toggle.get_attribute("aria-expanded") != "true":
                            return False, (
                                "expected a click on a non-interactive cell to expand the row")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Flights detail row expands and collapses from an icon-only toggle with no visible "
                    "text, a >=44x44 synthesized hit area and an accessible name that swaps with the "
                    "state, flipping aria-expanded and toggling the row aria-controls resolves to; and a "
                    "click on a non-interactive cell of the same row expands it, while a click on the "
                    "toggle itself toggles exactly once (22-09-PLAN.md Task 1, X5/T-22-32)",
                    _flights_detail_row_expands_and_collapses)

                # ==========================================================
                # 27-08-PLAN.md Task 2 (CFG-69): the Quiet hours caption
                # link's own hit target — it sits in a dense strip cell
                # beside a switch, the exact geometry that already produced
                # this file's 30x45 pager and 43x43 handle. Measured on
                # Home (the strip is one shared component, D-23; the
                # status-pages check proves it is the SAME markup on
                # Display), at the 360px floor, in both themes.
                # ==========================================================

                def _the_quiet_schedule_link_meets_the_hit_target_floor_at_360px():
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        recorded = {}
                        for route in ("/", "/display"):
                            page.goto(harness.base_url() + route)
                            overflow = page.evaluate(
                                "document.documentElement.scrollWidth > "
                                "document.documentElement.clientWidth")
                            if overflow:
                                return False, (
                                    "%s: expected no horizontal page scroll at 360px with the "
                                    "schedule link in the strip — the link is a FLOOR addition, "
                                    "not one that pushes the strip past the viewport" % (route,))
                        page.goto(harness.base_url() + "/")
                        for theme in ("light", "dark"):
                            _set_ui_theme(page, theme)
                            seen = _assert_hit_target(
                                page, "a.frame-strip__schedule-link",
                                "the Quiet hours caption's schedule link, in its own frame-strip "
                                "cell, %s theme" % theme)
                            recorded[theme] = (seen["visual"], seen["hit"])
                        if recorded["light"][1][0] < 44 or recorded["light"][1][1] < 44:
                            return False, "expected the light-theme hit area to clear 44px, got %r" % (
                                recorded["light"][1],)
                        if recorded["dark"][1][0] < 44 or recorded["dark"][1][1] < 44:
                            return False, "expected the dark-theme hit area to clear 44px, got %r" % (
                                recorded["dark"][1],)
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the Quiet hours caption's schedule link clears the 44px hit-target floor by "
                    "real hit-testing in its own frame-strip cell, in both themes, at the 360px "
                    "floor, on both Home and Display, with neither page gaining horizontal scroll "
                    "from the addition (CFG-69, 27-08-PLAN.md Task 2)",
                    _the_quiet_schedule_link_meets_the_hit_target_floor_at_360px)

                # ==========================================================
                # 27-08-PLAN.md Task 3 (CFG-70): `.copy-btn` (a Flights
                # detail row) and `.row-toggle` (the Flights list's own
                # toggle) — measured in THEIR OWN containers, never a
                # declared-vs-resolved assumption. `.row-toggle` reuses
                # `.copy-btn`'s values verbatim (style.css's own comment),
                # so both are measured here as ONE check about the family,
                # not two independent ones — the shape that let a declared
                # 44 ship beside a resolved 34x26 in the first place.
                #
                # `.row-toggle` and the desktop `.copy-btn` trio only exist
                # in `.data-table-wrap`, which this app's own responsive
                # rule hides below 960px in favour of `.history-cards` —
                # there is no 360px rendering of either to measure, so they
                # are measured at the narrowest width they actually occupy
                # (960px) instead, in both themes. The mobile `.copy-btn`
                # trio (inside each `.history-card`'s own `<details>`) DOES
                # render at 360px and is measured there, in both themes,
                # closing the literal 360px case for this family too.
                # ==========================================================

                def _copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_containers():
                    recorded = {}

                    def _measure_desktop(page):
                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        controls_id = toggle.get_attribute("aria-controls")
                        if toggle.get_attribute("aria-expanded") != "true":
                            toggle.click()
                        page.wait_for_timeout(50)
                        detail_sel = "#" + controls_id
                        page.locator(detail_sel).hover()
                        seen = _assert_hit_target(
                            page, "[data-row-toggle]",
                            "the Flights list's own row-toggle, in ITS OWN container (the "
                            "summary row, not the detail row's grid)")
                        recorded["row-toggle/desktop"] = (seen["visual"], seen["hit"])
                        for label, value in (
                                ("hex", "399023"), ("timestamp", "2026-08-01T22:31:40+00:00"),
                                ("callsign", "AFR135")):
                            sel = '%s [data-copy-value="%s"]' % (detail_sel, value)
                            page.locator(sel).focus()
                            seen = _assert_hit_target(
                                page, sel,
                                "the %s .copy-btn, in ITS OWN container (the Flights detail "
                                "row's grid, hovered/focused so its opacity/pointer-events "
                                "reveal fires)" % (label,))
                            recorded["copy-btn/desktop/%s" % label] = (seen["visual"], seen["hit"])

                    def _measure_mobile(page):
                        card = page.locator(".history-card").first
                        card.wait_for(state="visible")
                        card.locator("summary").first.click()
                        for label, value in (
                                ("hex", "399023"), ("timestamp", "2026-08-01T22:31:40+00:00"),
                                ("callsign", "AFR135")):
                            sel = '.history-card [data-copy-value="%s"]' % (value,)
                            seen = _assert_hit_target(
                                page, sel,
                                "the mobile %s .copy-btn, in ITS OWN container (the "
                                "<details> card, not the desktop grid)" % (label,))
                            recorded["copy-btn/mobile/%s" % label] = (seen["visual"], seen["hit"])

                    context_desktop = browser.new_context(viewport={"width": 960, "height": 900})
                    try:
                        page = context_desktop.new_page()
                        _login(page, harness.base_url())
                        for theme in ("light", "dark"):
                            page.goto(harness.base_url() + "/flights")
                            _set_ui_theme(page, theme)
                            _measure_desktop(page)
                    finally:
                        context_desktop.close()

                    context_mobile = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context_mobile.new_page()
                        _login(page, harness.base_url())
                        for theme in ("light", "dark"):
                            page.goto(harness.base_url() + "/flights")
                            _set_ui_theme(page, theme)
                            _measure_mobile(page)
                    finally:
                        context_mobile.close()

                    for key, (visual, hit) in recorded.items():
                        if hit[0] < 44 or hit[1] < 44:
                            return False, (
                                "%s: expected a resolved hit area >=44x44, got %r (visual box "
                                "%r) — a declared 44 is not a resolved 44"
                                % (key, hit, visual))
                    return True, ""
                check(
                    "every icon control in the .copy-btn/.row-toggle family resolves to the 44px "
                    "hit-target floor in its OWN container, by real hit-testing rather than a "
                    "declared value: .row-toggle and the desktop Flights detail row's three "
                    ".copy-btn (hex/timestamp/callsign, each hovered/focused to clear the "
                    "opacity-at-rest reveal) at 960px, and the mobile <details> card's own three "
                    ".copy-btn at the 360px floor — both in both themes, ONE check for the whole "
                    "family sharing .copy-btn's values (CFG-70, 27-08-PLAN.md Task 3)",
                    _copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_containers)

                def _filter_count_and_clear_share_one_line_at_390px():
                    # B11 (22-09-PLAN.md Task 3): Phase 18's A-18
                    # REGRESSING A SECOND TIME — at 390px "Clear" dropped
                    # alone onto its own line under the filter bar. Two
                    # `nowrap` siblings in a wrapping flex container do
                    # not wrap as a unit; one `.filter-bar__meta` group
                    # does. Measured, not inspected: equal
                    # getBoundingClientRect().top is the contract, and
                    # this assertion fails if it ever reopens a third
                    # time.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/flights")
                        count = page.locator("[data-filter-count]").first
                        clear = page.locator("[data-filter-clear]").first
                        count.wait_for(state="visible")
                        clear.wait_for(state="visible")
                        count_box = count.bounding_box()
                        clear_box = clear.bounding_box()
                        if count_box is None or clear_box is None:
                            return False, "expected both the count and Clear to have a box at 390px"
                        if round(count_box["y"]) != round(clear_box["y"]):
                            return False, (
                                "expected the filter count and Clear to report the same top at "
                                "390px (A-18 regressing a second time), got %r and %r"
                                % (count_box["y"], clear_box["y"]))
                        if page.viewport_size["width"] != 390:
                            return False, "expected the measurement to be taken at 390px"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px on Flights the filter count and the Clear control report the same "
                    "bounding-box top — Clear never drops alone onto its own line (B11, "
                    "22-09-PLAN.md Task 3, a regression of Phase 18's A-18)",
                    _filter_count_and_clear_share_one_line_at_390px)

                def _airlines_grid_renders_two_cards_per_row_at_390px():
                    # X7 (22-11-PLAN.md Task 2): the audit measured a
                    # 5800px Airlines page at 390px because
                    # `repeat(auto-fill, minmax(200px, 1fr))` collapses
                    # to ONE column inside a 342px content column. Only a
                    # real layout engine resolves auto-fill, so this is
                    # measured rather than asserted off the stylesheet.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/airlines")
                        # The gap strip carries its own narrower
                        # `.illustration-grid illustration-grid--gap`,
                        # so each grid is measured on its own rather than
                        # pooling two grids' rows into one histogram.
                        curated = ".illustration-grid:not(.illustration-grid--gap)"
                        page.locator(curated + " .airline-card").first.wait_for(state="visible")
                        grids = page.eval_on_selector_all(
                            ".illustration-grid",
                            "els => els.map(el => Array.from("
                            "  el.querySelectorAll('.airline-card')).map(card => {"
                            "    const r = card.getBoundingClientRect();"
                            "    return {top: Math.round(r.y), width: r.width};"
                            "}))")
                        if len(grids) < 1:
                            return False, "expected at least one illustration grid on Airlines"
                        widest_row = None
                        for grid_index, cards in enumerate(grids):
                            if not cards:
                                return False, "expected grid %d to hold cards" % (grid_index,)
                            rows = {}
                            for card in cards:
                                rows.setdefault(card["top"], []).append(card)
                            ordered = [rows[top] for top in sorted(rows)]
                            for index, row in enumerate(ordered):
                                # Every row but a grid's last holds
                                # exactly two; the last may hold one when
                                # that grid's card count is odd.
                                if len(row) > 2 or (index < len(ordered) - 1 and len(row) != 2):
                                    return False, (
                                        "expected exactly two cards per row at 390px, grid %d row "
                                        "%d held %d" % (grid_index, index, len(row)))
                                if len(row) == 2 and abs(row[0]["width"] - row[1]["width"]) > 1:
                                    return False, (
                                        "expected the two columns to be equal within 1px, got %r "
                                        "and %r" % (row[0]["width"], row[1]["width"]))
                                if len(row) == 2 and (
                                        widest_row is None
                                        or row[0]["width"] > widest_row[0]["width"]):
                                    widest_row = row
                        if widest_row is None:
                            return False, (
                                "expected at least one full two-card row to measure at 390px")
                        # 22-UI-SPEC.md §2's own arithmetic for the
                        # page's main content column: (342 - 24) / 2.
                        if not (150 <= widest_row[0]["width"] <= 170):
                            return False, (
                                "expected each card near the 159px the contract predicts, got %r"
                                % (widest_row[0]["width"],))
                        # X7's second half: the 5800px collapsed page
                        # roughly halves under a working two-per-row grid.
                        # Originally pinned at 3200px against a measured
                        # 2594px baseline for the 27 airlines on the grid
                        # when 22-11 shipped this check (22-11-SUMMARY.md).
                        # Recalibrated here (quick task 260921-v9c) after
                        # nine more illustrated carriers (27->36 airlines)
                        # legitimately grew the grid: CI measured 3318px
                        # for the new, correctly-laid-out two-per-row page,
                        # so the ceiling moves to 3800px — comparable
                        # proportional headroom to the original (roughly
                        # +15% over the freshly measured baseline, vs the
                        # original's +23%), while staying nowhere near the
                        # ~2x a real one-per-row collapse would produce
                        # (~6600px on today's card count). Measured, with
                        # headroom, so this fails on a regression rather
                        # than on a pixel — and moves again, deliberately,
                        # the next time the airline count legitimately
                        # changes.
                        height = page.evaluate("document.documentElement.scrollHeight")
                        if height > 3800:
                            return False, (
                                "expected the two-per-row grid to roughly halve the audit's 5800px "
                                "page, measured %r" % (height,))
                        if page.viewport_size["width"] != 390:
                            return False, "expected the measurement to be taken at 390px"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px every Airlines illustration grid renders exactly two cards per row "
                    "(never the one-per-row auto-fill collapse that made the page 5800px tall), "
                    "with each row's two columns equal within 1px, the main grid's cards near the "
                    "159px the contract predicts, and the whole page under 3800px (X7, "
                    "22-11-PLAN.md Task 2, ceiling recalibrated by quick task 260921-v9c for the "
                    "27->36 airline count)",
                    _airlines_grid_renders_two_cards_per_row_at_390px)

                def _airlines_filter_count_and_clear_share_one_line_at_390px():
                    # B11 (22-11-PLAN.md Task 3): the SECOND of the three
                    # filtered pages. Same defect, same shared
                    # `.filter-bar__meta` group plan 22-09 added — adopted
                    # verbatim, never forked into a per-page variant,
                    # which is how Phase 18's A-18 came back the first
                    # time. Measured, like its Flights sibling: equal
                    # getBoundingClientRect().top is the contract.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/airlines")
                        count = page.locator("[data-filter-count]").first
                        clear = page.locator("[data-filter-clear]").first
                        count.wait_for(state="visible")
                        clear.wait_for(state="visible")
                        count_box = count.bounding_box()
                        clear_box = clear.bounding_box()
                        if count_box is None or clear_box is None:
                            return False, "expected both the count and Clear to have a box at 390px"
                        if round(count_box["y"]) != round(clear_box["y"]):
                            return False, (
                                "expected the Airlines filter count and Clear to report the same "
                                "top at 390px (A-18 regressing), got %r and %r"
                                % (count_box["y"], clear_box["y"]))
                        # Adopted, not forked: the pair is inside the one
                        # shared group element, and Airlines adds no
                        # variant of its own.
                        in_group = page.eval_on_selector_all(
                            ".filter-bar__meta",
                            "els => els.map(el => [!!el.querySelector('[data-filter-count]'),"
                            " !!el.querySelector('[data-filter-clear]')])")
                        if in_group != [[True, True]]:
                            return False, (
                                "expected exactly one .filter-bar__meta group on Airlines holding "
                                "both controls, got %r" % (in_group,))
                        if page.viewport_size["width"] != 390:
                            return False, "expected the measurement to be taken at 390px"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px on Airlines the filter count and the Clear control report the same "
                    "bounding-box top, both inside the one shared .filter-bar__meta group plan "
                    "22-09 introduced — adopted verbatim, no per-page variant (B11, 22-11-PLAN.md "
                    "Task 3, the second of the three filtered pages)",
                    _airlines_filter_count_and_clear_share_one_line_at_390px)

                def _health_registry_table_fits_1280px_in_both_languages():
                    # B12 (22-12-PLAN.md Task 2): the audit measured the
                    # unresolved-prefix table overflowing a 1280px
                    # desktop in French — "EXEMPLE D'INDIC" clipped, and
                    # the Resolve column only reachable by scrolling a
                    # container whose one affordance is a 12px shadow.
                    # The lever choice was made BY THIS MEASUREMENT, not
                    # by eye (the same discipline that settled the
                    # Flights table): only a real layout engine resolves
                    # `.data-table`'s `min-width: max-content` floor
                    # against six columns of real content in two
                    # languages.
                    #
                    # Measured here at every step, wrap clientWidth 830px:
                    #   before          EN  886   FR 1026
                    #   stacked cells   EN  830   FR  900
                    #   + short FR hdrs EN  830   FR  830
                    for lang in ("en", "fr"):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            base_url = harness.base_url()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
                            page.goto(base_url + "/health")
                            page.locator("table.data-table--registry").first.wait_for(
                                state="visible")
                            box = page.eval_on_selector(
                                "table.data-table--registry",
                                "table => {"
                                "  const wrap = table.closest('.data-table-wrap');"
                                "  const heads = Array.from(table.querySelectorAll('th'));"
                                "  const resolve = heads[heads.length - 1];"
                                "  const cells = Array.from("
                                "    table.querySelectorAll('tbody tr'))"
                                "    .map(tr => tr.children[tr.children.length - 1]);"
                                "  return {"
                                "    sw: wrap.scrollWidth, cw: wrap.clientWidth,"
                                "    wrapRight: wrap.getBoundingClientRect().right,"
                                "    resolveRight: Math.max(resolve.getBoundingClientRect().right,"
                                "      ...cells.map(td => td.getBoundingClientRect().right)),"
                                "    headClipped: heads.filter("
                                "      h => h.scrollWidth > h.clientWidth + 1).map(h => h.textContent),"
                                "    rowCount: table.querySelectorAll('tbody tr').length,"
                                "  };"
                                "}")
                            if box["rowCount"] < 1:
                                return False, (
                                    "expected the seeded registry to render at least one row (%s)"
                                    % (lang,))
                            if box["sw"] != box["cw"]:
                                return False, (
                                    "expected .data-table-wrap scrollWidth === clientWidth at "
                                    "1280px in %s, got %r vs %r (B12)"
                                    % (lang, box["sw"], box["cw"]))
                            # "Reachable without horizontal scrolling" is
                            # the audit's own wording — asserted as a
                            # geometric fact, not inferred from the
                            # scrollWidth equality above.
                            if box["resolveRight"] > box["wrapRight"] + 1:
                                return False, (
                                    "expected the Resolve column to sit inside the wrap's own box "
                                    "at 1280px in %s, got right edge %r vs %r"
                                    % (lang, box["resolveRight"], box["wrapRight"]))
                            if box["headClipped"]:
                                return False, (
                                    "expected no clipped header at 1280px in %s, got %r"
                                    % (lang, box["headClipped"]))
                            if page.viewport_size["width"] != 1280:
                                return False, "expected the measurement to be taken at 1280px"
                        finally:
                            context.close()
                    return True, ""
                check(
                    "at 1280px in BOTH languages Health's unresolved-prefix table reports "
                    "scrollWidth === clientWidth on its .data-table-wrap, the Resolve column sits "
                    "inside that wrap's own box (reachable with no horizontal scrolling) and no "
                    "header is clipped — the French table measured 1026px against an 830px wrap "
                    "before the stacked cells and the shortened headers (B12, 22-12-PLAN.md Task 2)",
                    _health_registry_table_fits_1280px_in_both_languages)

                def _health_filter_count_and_clear_share_one_line_at_390px():
                    # B11 (22-12-PLAN.md Task 3): the THIRD and last of
                    # the three filtered pages. Same defect, same shared
                    # `.filter-bar__meta` group plan 22-09 added and plan
                    # 22-11 adopted — taken verbatim again, never forked
                    # into a per-page variant, which is how Phase 18's
                    # A-18 came back the first time. Measured, like both
                    # its siblings: equal getBoundingClientRect().top is
                    # the contract, so a third regression fails here
                    # instead of being noticed by eye.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/health")
                        count = page.locator("[data-filter-count]").first
                        clear = page.locator("[data-filter-clear]").first
                        count.wait_for(state="visible")
                        clear.wait_for(state="visible")
                        count_box = count.bounding_box()
                        clear_box = clear.bounding_box()
                        if count_box is None or clear_box is None:
                            return False, "expected both the count and Clear to have a box at 390px"
                        if round(count_box["y"]) != round(clear_box["y"]):
                            return False, (
                                "expected the Health filter count and Clear to report the same "
                                "top at 390px (A-18 regressing a third time), got %r and %r"
                                % (count_box["y"], clear_box["y"]))
                        in_group = page.eval_on_selector_all(
                            ".filter-bar__meta",
                            "els => els.map(el => [!!el.querySelector('[data-filter-count]'),"
                            " !!el.querySelector('[data-filter-clear]')])")
                        if in_group != [[True, True]]:
                            return False, (
                                "expected exactly one .filter-bar__meta group on Health holding "
                                "both controls, got %r" % (in_group,))
                        # C5: the page header's own clock left the
                        # monospace family for the one time-value role.
                        clock_class = page.eval_on_selector(
                            "[data-refresh-clock]", "el => el.className")
                        if "mono" in clock_class.split() or "time-value" not in clock_class.split():
                            return False, (
                                "expected the page header's Updated clock on .time-value and not "
                                "on .mono, got %r" % (clock_class,))
                        if page.viewport_size["width"] != 390:
                            return False, "expected the measurement to be taken at 390px"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px on Health the filter count and the Clear control report the same "
                    "bounding-box top, both inside the one shared .filter-bar__meta group — the "
                    "third and last of the three filtered pages — and the page header's Updated "
                    "clock carries .time-value, never .mono (B11/C5, 22-12-PLAN.md Task 3)",
                    _health_filter_count_and_clear_share_one_line_at_390px)

                def _the_no_js_floor_holds_for_health():
                    # D-09 asks the floor to hold THROUGHOUT the phase,
                    # so it is asserted at THIS plan's own commit rather
                    # than deferred to the phase-closing sweep. This plan
                    # rebuilds every tile body, restructures a table's
                    # cells and re-wraps a filter bar — all server-
                    # rendered, and all of it must therefore be complete
                    # with scripts blocked.
                    with _no_js_page(browser.new_context, harness.base_url(), "/health") as page:
                        tiles = page.eval_on_selector_all(".stat-tile", "els => els.length")
                        if tiles != 4:
                            return False, (
                                "expected all four Health tiles to render with scripts blocked, "
                                "got %d" % (tiles,))
                        # Every tile is complete, not merely present.
                        slots = page.eval_on_selector_all(
                            ".stat-tile",
                            "els => els.map(el => ["
                            "  el.querySelectorAll(':scope > .stat-tile__caption').length,"
                            "  el.querySelectorAll("
                            "    ':scope > .widget-verdict, :scope > .stat-tile__value,"
                            "     :scope > .empty-state > .empty-state__heading').length,"
                            "  el.querySelectorAll("
                            "    ':scope > .widget-detail, :scope > .empty-state >"
                            "     .empty-state__body').length])")
                        for index, slot in enumerate(slots):
                            if slot != [1, 1, 1]:
                                return False, (
                                    "expected tile %d to render its label/verdict/detail slots "
                                    "exactly once each with scripts blocked, got %r"
                                    % (index, slot))
                        if not page.query_selector(".filter-bar [data-filter-input]"):
                            return False, "expected the registry filter bar with scripts blocked"
                        if not page.query_selector("[data-filter-clear]"):
                            return False, "expected the Clear control with scripts blocked"
                        # The table OR its card fallback — whichever the
                        # viewport resolves to — must be present, and the
                        # Resolve action reachable from it.
                        rows = page.eval_on_selector_all(
                            "table.data-table--registry tbody tr, ul.data-cards > li", "els => els.length")
                        if rows < 1:
                            return False, (
                                "expected the unresolved-prefix rows (table or card fallback) with "
                                "scripts blocked, got %d" % (rows,))
                        # `:visible` matters: this card list and this
                        # table are BOTH in the DOM at every width (the
                        # `.data-cards ~ .data-table-wrap` toggle is
                        # CSS-only, by design, so the no-JS path has
                        # both), and the card list renders first. The
                        # reachable one is whichever the viewport
                        # actually shows — which is the thing "reachable
                        # without scripts" means.
                        resolve = page.locator('a[href^="/airlines?resolve="]:visible').first
                        if resolve.count() == 0:
                            return False, (
                                "expected the per-row Resolve action to be reachable with scripts "
                                "blocked")
                        href = resolve.get_attribute("href")
                        with page.expect_navigation():
                            resolve.click()
                        if "/airlines" not in page.url or "resolve=" not in page.url:
                            return False, (
                                "expected the Resolve link (%r) to navigate to the Airlines "
                                "resolve surface with scripts blocked, got %r" % (href, page.url))
                        return True, ""
                check(
                    "with scripts blocked Health renders in full — all four tiles with their "
                    "label/verdict/detail slots each exactly once, the registry filter bar and "
                    "Clear, the unresolved-prefix rows, and a per-row Resolve action that actually "
                    "navigates to the Airlines resolve surface (D-09's floor asserted at this "
                    "plan's own commit, 22-12-PLAN.md Task 3)",
                    _the_no_js_floor_holds_for_health)

                # ----------------------------------------------------------------
                # 22-01-PLAN.md Task 3 (D-01/D-02, B1/T1/T8): the four checks
                # this whole plan exists to make possible.
                # ----------------------------------------------------------------

                def _display_reveal_and_persist_across_all_field_kinds():
                    # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED from
                    # auto-save onto the restored bar — the pre-27-04 name
                    # is genuinely honest again: a committed edit REVEALS
                    # the bar (never a click before that) and only
                    # Enregistrer PERSISTS it (never a click-free
                    # auto-save). Its real value (three cross-DOM
                    # form=-attached field KINDS — radio-as-chip,
                    # radio-as-card, time input — each genuinely
                    # committing, revealing the bar, and persisting once
                    # saved) survives unchanged.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        theme_ids = device_config.THEME_IDS
                        runway_ids = device_config.RUNWAY_IDS

                        def on_disk():
                            return device_config.load_device_config(harness.tmpdir)

                        # 1. Theme chip (Frame colours card, form=-attached,
                        # rendered as a sibling of <form id="settings-form">).
                        page.goto(base_url + "/display")
                        target_theme = theme_ids[1]
                        theme_sel = 'input[name="theme"][value="%s"]' % target_theme
                        _click_control(page, theme_sel)
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        if on_disk()["theme"] != target_theme:
                            return False, (
                                "expected the theme chip's committed value to reach disk, got %r"
                                % (on_disk()["theme"],))

                        # 2. Runway card (also a sibling of the form).
                        target_runway = runway_ids[1]
                        runway_sel = 'input[name="tracked_runway"][value="%s"]' % target_runway
                        _click_control(page, runway_sel)
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        if str(on_disk()["tracked_runway"]) != str(target_runway):
                            return False, (
                                "expected the runway card's committed value to reach disk, got %r"
                                % (on_disk()["tracked_runway"],))

                        # 3. Enable-display checkbox — RETIRED outright by
                        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the Frame
                        # strip is now the ONLY on/off control for the
                        # screen, so this settings page no longer renders
                        # a display_enabled checkbox for the B1 regression
                        # to cover here at all. No replacement checkbox
                        # exists on Display any more (Quiet hours' own
                        # on/off checkbox is retired the same way) — the
                        # remaining two field kinds below (radio, time
                        # input) still prove the cross-DOM form=
                        # delegation this check exists for.

                        # 4. Quiet-hours time field (a sibling of the form).
                        # .fill() dispatches `input` only (Playwright's own
                        # documented contract) — never `change` — so
                        # _commit_field() fires the real `change` a blur
                        # would, which is the exact commit the bar's own
                        # document-level listener is waiting for.
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.fill(quiet_sel, "22:15")
                        _commit_field(page, quiet_sel)
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        if str(on_disk()["quiet_hours_start"]) != "22:15":
                            return False, (
                                "expected the quiet-hours time field's committed value to reach "
                                "disk, got %r" % (on_disk()["quiet_hours_start"],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Display: a theme chip, a runway card and a quiet-hours time field each commit "
                    "via change, REVEAL the bar, and PERSIST to DISK once Enregistrer is clicked "
                    "(form=-attached radio and time-input field kinds — the Enable-display checkbox "
                    "this check also covered is retired outright by 22-05-PLAN.md Task 1, "
                    "X1/D-04/D-12.1; retargeted from the retired auto-save onto the restored bar by "
                    "28-10-PLAN.md Task 1, CFG-77/CFG-78)",
                    _display_reveal_and_persist_across_all_field_kinds)

                def _device_reveal_and_persist_stays_in_step_with_display():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        # 23-07-PLAN.md Task 2 (D2/CFG-36, X1/D-04):
                        # RETARGETED IN PLACE from the Diagnostic LED
                        # checkbox to the wake-interval field. The LED is
                        # no longer a Save-governed control at all — it
                        # is a role="switch" applying instantly over
                        # /quick/led. 28-10-PLAN.md Task 1 (CFG-77/CFG-78):
                        # retargeted AGAIN, from auto-save onto the
                        # restored bar — the wake-interval field commits
                        # via change, REVEALS the bar, and PERSISTS to
                        # DISK once Enregistrer is clicked, exactly like
                        # Display's own fields, proving the two scopes
                        # still stay in step.
                        page.goto(base_url + "/device")
                        wake_sel = 'input[name="wake_interval_s"]'
                        before = page.eval_on_selector(wake_sel, "el => el.value")
                        target = "1800" if before != "1800" else "3600"
                        page.fill(wake_sel, target)
                        _commit_field(page, wake_sel)
                        _wait_for_bar(page)
                        _save_via_bar(page)
                        stored = device_config.load_device_config(harness.tmpdir)["wake_interval_s"]
                        if str(stored) != target:
                            return False, (
                                "expected the edited wake interval to reach disk, got %r"
                                % (stored,))
                        # And the LED switch, which is NOT part of that
                        # form, must be unmoved by the save — the whole
                        # point of T-23-25.
                        led_state = page.eval_on_selector(
                            '[data-quick-region] button[role="switch"]',
                            "el => el.getAttribute('aria-checked')")
                        if led_state not in ("true", "false"):
                            return False, (
                                "expected the Device page to render an LED switch with a real "
                                "aria-checked, got %r" % (led_state,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Device: the wake-interval field commits via change, REVEALS the bar, and "
                    "PERSISTS to DISK once Enregistrer is clicked, proving the two scopes stay in "
                    "step (B1) — witnessed by the wake-interval field since the Diagnostic LED "
                    "stopped being a Save-governed control (retargeted in place by 23-07-PLAN.md "
                    "Task 2, D2/CFG-36; retargeted from the retired auto-save onto the restored bar "
                    "by 28-10-PLAN.md Task 1, CFG-77/CFG-78)",
                    _device_reveal_and_persist_stays_in_step_with_display)

                def _the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): RETARGETED — the
                    # polarity this check asserted is INVERTED, not a
                    # mechanical swap. 27-03-PLAN.md Task 2 (CFG-64) and
                    # 27-04-PLAN.md Task 4 (CFG-63) both asserted the
                    # fallback Save button stayed HIDDEN before AND after
                    # an edit, because neither of their models had a
                    # visible save affordance to reveal (auto-save's own
                    # bar never returned; CFG-64's fallback button was
                    # purely a scripts-blocked floor with nothing left to
                    # click). 28-08-PLAN.md restored the bar as the SAME
                    # element (`[data-static-save-fallback]`, relocated
                    # inside the bar's own markup rather than duplicated)
                    # — server-rendered VISIBLE now, because the bar's own
                    # visible state IS the no-JS floor; hidden by script
                    # the instant script proves itself live
                    # (dirty-state.js's own `bar.hidden = true` at init,
                    # before any listener is attached); revealed again the
                    # instant a real edit exists. This is the exact clause
                    # a future reader would "correct" back to the retired
                    # polarity — written down here so they do not.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()

                        page.goto(base_url + "/display")
                        bar = page.locator("[data-dirty-bar]")
                        # 1. Script has proven itself live: the bar hides
                        #    at init, on a page with no edits at all.
                        if bar.is_visible():
                            return False, (
                                "expected the bar to be HIDDEN immediately once script runs on "
                                "a fresh load — dirty-state.js's own bar.hidden = true at init, "
                                "the no-JS-floor polarity this check exists to pin down")

                        theme_ids = device_config.THEME_IDS
                        target = theme_ids[2]
                        _click_control(page, 'input[name="theme"][value="%s"]' % target)
                        # 2. An edit REVEALS the bar — the opposite of the
                        #    retired contract, which asserted nothing on
                        #    the page was ever supposed to show a save
                        #    affordance again.
                        _wait_for_bar(page)
                        count_text = _bar_text(page)
                        if not count_text:
                            return False, (
                                "expected [data-dirty-count] to name the changed section once "
                                "the bar reveals, got an empty string")

                        # 3. Clicking the bar's own Save persists to disk
                        #    through a real navigation.
                        _save_via_bar(page)
                        stored = device_config.load_device_config(harness.tmpdir)["theme"]
                        if stored != target:
                            return False, (
                                "expected the theme edit to reach disk once the bar's own Save "
                                "is clicked, got %r" % (stored,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the bar (the single [data-static-save-fallback] Save affordance, relocated "
                    "inside it, never a second button) is server-rendered VISIBLE — the no-JS "
                    "floor — and hides IMMEDIATELY once script proves itself live; an edit "
                    "REVEALS it again, naming the changed section via [data-dirty-count]; and "
                    "clicking its own Save persists to disk through a real navigation — the "
                    "INVERSE of 27-03-PLAN.md Task 2 (CFG-64) and 27-04-PLAN.md Task 4 "
                    "(CFG-63)'s own retired polarity, which this check's former name asserted "
                    "(D-01/CFG-64/CFG-77/CFG-78, retargeted onto the restored bar by "
                    "28-10-PLAN.md Task 2)",
                    _the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves)

                def _leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not a
                    # mechanical swap — the assertion this check made is
                    # INVERTED by the restoration, and half its subject
                    # (the save-status region) is deleted outright.
                    #
                    # 27-04-PLAN.md Task 4 (D-10/CFG-63) asserted the guard
                    # DISARMED the instant a change COMMITTED — correct
                    # under auto-save, where a committed change was already
                    # saved and there was nothing left to warn about. Under
                    # the restored bar (<restored_guard_semantics> in
                    # 28-10-PLAN.md), a committed-but-unsaved change is
                    # EXACTLY what the guard exists to warn about — it
                    # stays armed until Enregistrer or Annuler. Asserting
                    # the old disarm-on-commit clause here would prove the
                    # retired contract, not the current one.
                    #
                    # The save-status-silent clause is gone with the region
                    # itself; replaced by the equivalent-or-stronger bar
                    # clause below — the restored model has no silent
                    # phase at all, since the bar is already visible and
                    # already naming the section the instant the edit is
                    # merely TYPED, before any commit.
                    #
                    # The re-arm-after-Cancel clause (a NEW edit after
                    # Annuler re-arming the guard) is 28-11-PLAN.md's own
                    # check — not duplicated here; see that plan's
                    # leave-guard re-arm check for the clause this one
                    # deliberately stops short of.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/device")
                        # a. Fresh load: disarmed.
                        if _guard_armed(page):
                            return False, "expected the leave-guard to start disarmed on a clean page load"

                        wake_sel = 'input[name="wake_interval_s"]'
                        before = page.eval_on_selector(wake_sel, "el => el.value")
                        target = "1800" if before != "1800" else "3600"

                        # b. TYPE without committing — `input` fires per
                        #    keystroke; `change` does not fire until focus
                        #    leaves the field. This is the uncommitted
                        #    state, and it is still true, at equal
                        #    strength, after this restoration.
                        page.eval_on_selector(wake_sel, "el => el.focus()")
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.type(target)
                        if page.eval_on_selector(wake_sel, "el => el.value") != target:
                            return False, "expected the typed value to be held by the field before any commit"
                        if not _guard_armed(page):
                            return False, (
                                "expected the leave-guard to be armed for an edited-but-uncommitted "
                                "field (D-10) — countDifferences() > 0 the moment a keystroke "
                                "differs, never waiting for change")
                        # The equivalent-or-stronger replacement for the
                        # deleted silent-region clause: the restored model
                        # has NO silent phase — the bar is already visible
                        # and [data-dirty-count] already names the section
                        # even before this edit commits.
                        _wait_for_bar(page)
                        if not _bar_text(page):
                            return False, (
                                "expected [data-dirty-count] to already name the changed section "
                                "for a merely-typed, uncommitted edit — the restored model has no "
                                "silent phase, which is strictly more than the retired region ever "
                                "asserted")

                        # c. COMMIT it — blur fires `change`. Under the
                        #    restored semantics the guard STAYS ARMED: a
                        #    committed-but-unsaved change is exactly what
                        #    it exists to warn about.
                        page.keyboard.press("Tab")
                        if not _guard_armed(page):
                            return False, (
                                "expected the leave-guard to STAY ARMED the instant change "
                                "commits the edit — a committed change is unsaved until "
                                "Enregistrer, not the retired auto-save contract where a commit "
                                "disarmed the guard because it was already persisted")
                        stored = device_config.load_device_config(harness.tmpdir)["wake_interval_s"]
                        if str(stored) == target:
                            return False, (
                                "the committed value already reached disk with no Save click — "
                                "this check's own premise (unsaved-but-committed) does not hold")

                        # d. Click Annuler: the guard DISARMS and the bar
                        #    hides.
                        page.click("[data-dirty-cancel]")
                        _wait_for_bar_hidden(page)
                        if _guard_armed(page):
                            return False, "expected the leave-guard to disarm once Annuler is clicked"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the leave-guard stays armed for a field that has been edited but never fired "
                    "change (the bar already visible and already naming the section, the "
                    "restored model's no-silent-phase clause — strictly more than the retired "
                    "save-status region ever asserted); the guard STAYS ARMED, not disarmed, the "
                    "instant change commits the edit, because a committed-but-unsaved change is "
                    "exactly what the restored guard exists to warn about; and Annuler is the "
                    "guard's own exit, disarming it and hiding the bar (the re-arm-after-Cancel "
                    "clause is 28-11-PLAN.md's own check, not duplicated here) (D-10, "
                    "<restored_guard_semantics>, retargeted from the retired auto-save's own "
                    "inverted disarm-on-commit contract by 28-10-PLAN.md Task 2, CFG-77/CFG-78; "
                    "27-04-PLAN.md Task 4, CFG-63)",
                    _leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit)

                # --- 28-11-PLAN.md Task 3 (CFG-77): the leave-guard's
                # re-arm-after-Cancel clause — the one nothing in the
                # phase proves. The check above (28-10-PLAN.md Task 2)
                # proves armed-on-typed-edit, stays-armed-through-commit
                # and disarmed-by-Cancel, and stops there BY DESIGN (its
                # own comment names this one). CFG-77's own binding
                # wording: "does not disarm the leave-guard permanently...
                # kept exactly where CFG-63's own carve-out already put
                # it" (.planning/REQUIREMENTS.md). `git show 6dea46a`'s
                # own header names the historical defect this records: a
                # naive Cancel handler sets suppressGuard = true once and
                # never clears it, leaving the guard dead for the rest of
                # the page's life while steps 1-3 below alone would still
                # pass against that exact defect.
                def _the_leave_guard_re_arms_after_a_new_edit_following_cancel():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        # 1. Fresh load: disarmed, bar hidden.
                        if _guard_armed(page):
                            return False, (
                                "expected the leave-guard to start disarmed on a clean page "
                                "load")
                        _wait_for_bar_hidden(page)

                        runway_sel = 'input[name="tracked_runway"]'
                        current_runway = page.eval_on_selector(
                            "%s:checked" % runway_sel, "el => el.value")
                        first_target = next(
                            r for r in device_config.RUNWAY_IDS if r != current_runway)
                        second_target = next(
                            r for r in device_config.RUNWAY_IDS
                            if r != current_runway and r != first_target)

                        # 2. Edit a field: armed, bar visible. Kept
                        #    minimal on purpose — the check above already
                        #    proves the typed-vs-committed distinction;
                        #    this step is only the precondition steps 3-5
                        #    need.
                        _click_control(page, '%s[value="%s"]' % (runway_sel, first_target))
                        if not _guard_armed(page):
                            return False, "expected the leave-guard to arm for a real edit"
                        _wait_for_bar(page)

                        # 3. Click Annuler: disarmed, bar hides.
                        page.click("[data-dirty-cancel]")
                        _wait_for_bar_hidden(page)
                        if _guard_armed(page):
                            return False, (
                                "expected the leave-guard to disarm once Annuler is clicked")

                        # 4. THE WHOLE POINT. A NEW edit that FOLLOWS a
                        #    Cancel must RE-ARM the guard — nothing else
                        #    in this phase proves it, and it is exactly
                        #    what a naive `suppressGuard = true` (set once
                        #    in the Cancel handler, never cleared) gets
                        #    wrong, while steps 1-3 above alone would
                        #    still pass against that defect.
                        _click_control(page, '%s[value="%s"]' % (runway_sel, second_target))
                        if not _guard_armed(page):
                            return False, (
                                "expected the leave-guard to RE-ARM for an edit that follows a "
                                "Cancel — CFG-77's own 'does not disarm the leave-guard "
                                "permanently... kept exactly where CFG-63's own carve-out "
                                "already put it', and exactly the defect a Cancel handler that "
                                "sets suppressGuard=true once and never clears it reproduces")
                        _wait_for_bar(page)

                        # 5. A SECOND Annuler disarms again — a re-arm
                        #    that can only happen once is the same defect
                        #    wearing a different number.
                        page.click("[data-dirty-cancel]")
                        _wait_for_bar_hidden(page)
                        if _guard_armed(page):
                            return False, (
                                "expected the leave-guard to disarm on a SECOND Annuler too")

                        return True, ""
                    finally:
                        context.close()
                check(
                    "the leave-guard's re-arm-after-Cancel clause — CFG-77's own 'does not "
                    "disarm the leave-guard permanently... kept exactly where CFG-63's own "
                    "carve-out already put it' — has executable coverage for the first time: "
                    "fresh load (disarmed) -> edit (armed) -> Annuler (disarmed) -> a NEW edit "
                    "(RE-ARMED, the clause nothing else in this phase proves, and exactly the "
                    "defect a Cancel handler that sets suppressGuard=true once and never clears "
                    "it reproduces) -> a second Annuler (disarmed again, so a one-shot re-arm "
                    "cannot pass); reuses the existing _guard_armed() beforeunload probe "
                    "throughout — never a second one (CFG-77, 28-11-PLAN.md Task 3; "
                    "complements 28-10-PLAN.md Task 2's own armed-on-typed-edit/stays-armed-"
                    "through-commit/disarmed-by-Cancel check, which deliberately stops short of "
                    "this clause)",
                    _the_leave_guard_re_arms_after_a_new_edit_following_cancel)

                def _strip_switch_applies_without_the_leave_guard_while_other_navigation_still_warns():
                    # 22-05-PLAN.md Task 3 (D-04): a real browser proof,
                    # not a read of dirty-state.js's private suppressGuard
                    # variable. Chromium (headless, under Playwright)
                    # surfaces a beforeunload guard's own preventDefault()
                    # as a real `dialog` event of type "beforeunload" -
                    # confirmed experimentally against a minimal fixture
                    # before this check was written - so listening for
                    # that event and asserting its presence/absence is a
                    # genuine, non-cosmetic behavioural probe.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/display")
                        dialogs = []
                        page.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))

                        # 23-07-PLAN.md Task 1 (D2/CFG-36): RETARGETED IN
                        # PLACE, and made strictly stronger. This check
                        # used to assert the switch NAVIGATES. D2 is the
                        # decision that it no longer does: the flip lands
                        # under the finger and the POST goes out over
                        # fetch, so there is no unload at all and the
                        # dialog this check is about cannot fire for a
                        # mechanical reason.
                        #
                        # That would make the original assertion vacuous,
                        # so it is replaced by the property that actually
                        # matters now and that the original could not
                        # reach: after the switch has applied, the
                        # leave-guard must still be ARMED for the unsaved
                        # edit that is still sitting in the form. That is
                        # the real hazard the conversion introduced —
                        # dirty-state.js disarms its guard for any
                        # [data-quick-switch] submit, and on a page whose
                        # form was already dirty nothing would ever
                        # re-arm it. quick-switch.js listens in the
                        # capture phase and stops propagation precisely
                        # so that listener never runs for a submission
                        # that is not happening.
                        #
                        # 27-04-PLAN.md Task 4 (CFG-63): a radio commits
                        # (fires change) the instant it is clicked, which
                        # now means auto-save begins and the guard
                        # disarms again a moment later — a radio click can
                        # no longer hold this check's own "unsaved edit"
                        # precondition open. Focusing and TYPING would
                        # not survive either: clicking the switch button
                        # shifts DOM focus away from the field, which
                        # BLURS it and fires the very `change` that would
                        # commit and auto-save it before the assertion
                        # below even runs. countDifferences() (the guard's
                        # own predicate) reads the field's LIVE value
                        # against the load-time snapshot and needs no
                        # event at all to see a difference, so the value
                        # is set directly with no focus taken and no event
                        # dispatched — nothing to blur, nothing to commit.
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.eval_on_selector(quiet_sel, "el => { el.value = '04:44'; }")
                        if not _guard_armed(page):
                            return False, (
                                "control: the leave-guard was not armed before the switch was "
                                "touched, so the assertion below would prove nothing")
                        before = device_config.load_device_config(harness.tmpdir)["display_enabled"]
                        switch_sel = 'form[action="/quick/display"] button[type="submit"]'
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/quick/display"):
                            page.click(switch_sel)
                        page.wait_for_timeout(400)
                        if dialogs:
                            return False, (
                                "expected NO beforeunload dialog when activating the strip's own "
                                "switch with unsaved edits present, got %r" % (dialogs,))
                        after = device_config.load_device_config(harness.tmpdir)["display_enabled"]
                        if after == before:
                            return False, "expected the strip switch's own change to persist"
                        if page.url.split("?")[0] != base_url + "/display":
                            return False, (
                                "expected the switch to apply WITHOUT navigating (D2), but the "
                                "page moved to %r" % (page.url,))
                        if not _guard_armed(page):
                            return False, (
                                "the leave-guard was left DISARMED after a switch applied on a "
                                "page that still holds an unsaved edit — dirty-state.js disarms "
                                "for any [data-quick-switch] submit and re-arms only on the next "
                                "edit, so a form that was already dirty would lose its guard for "
                                "the rest of the page's life (D2/CFG-36, 23-07-PLAN.md Task 1)")
                        # The switch must also still be pressable: a
                        # submit-guard that disabled it on the way out
                        # would leave a dead control on a page that never
                        # reloads.
                        if page.eval_on_selector(switch_sel, "el => el.disabled"):
                            return False, (
                                "the switch was left disabled after applying — with no navigation "
                                "to replace the page, a disabled switch stays disabled forever")

                        # Reset: reload, make the SAME kind of unsaved
                        # edit again, then navigate away by a plain nav
                        # link - no [data-quick-switch] form involved at
                        # all - and the guard must still warn. Same
                        # focus-free value set as above, for the same
                        # reason: clicking the nav link would blur a
                        # FOCUSED field and commit it before the
                        # navigation's own beforeunload check ever runs.
                        page.goto(base_url + "/display")
                        dialogs[:] = []
                        page.eval_on_selector(quiet_sel, "el => { el.value = '05:55'; }")
                        with page.expect_navigation():
                            page.click('a[href="/"]')
                        if "beforeunload" not in dialogs:
                            return False, (
                                "expected a PLAIN navigation with the same unsaved edit to still "
                                "raise the beforeunload dialog, got %r" % (dialogs,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "activating a Frame strip switch with unsaved Display edits present applies over "
                    "fetch WITHOUT navigating, leaves the leave-guard ARMED for the edit still in "
                    "the form and the switch still pressable, and raises no dialog, while a plain "
                    "nav-link navigation with the same unsaved edit still raises one (22-05-PLAN.md "
                    "Task 3, D-04; retargeted in place by 23-07-PLAN.md Task 1, which is what took "
                    "the navigation away)",
                    _strip_switch_applies_without_the_leave_guard_while_other_navigation_still_warns)

                def _three_runway_cards_share_one_line_at_390px():
                    # B9 (22-AUDIT.md, 22-10-PLAN.md Task 2). The measured
                    # defect was a 2 + 1 orphan at 390px: 150x150, 150x150,
                    # then a lone 308x217. Only a real layout engine can
                    # see this, which is why it lives here and not in a
                    # string-comparison harness.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")
                        # 23-10-PLAN.md Task 1 (D3/CFG-32): the selected
                        # card now also carries a `transform: scale(...)`
                        # — the "selection answers" clause. A transform
                        # IS reflected in getBoundingClientRect(), which
                        # reports the VISUAL box, and is NOT reflected in
                        # the layout box. T6 and B9 are both statements
                        # about the LAYOUT box (a border that grew a
                        # flex item and pushed its siblings; a card that
                        # wrapped onto its own line), so the transform is
                        # neutralised for the duration of the
                        # measurement — with its own transition
                        # neutralised first, or the read below would
                        # catch the 180ms unwind mid-flight and measure a
                        # value that is neither the scaled nor the
                        # unscaled box.
                        #
                        # Neutralising it is only honest if the scale is
                        # really there, so the real computed transform is
                        # captured BEFORE the override and asserted
                        # below: exactly one of the three cards must be
                        # scaled (the selected one), and the other two
                        # must not be. That pairing is what keeps this
                        # check from passing for a build that dropped the
                        # scale entirely.
                        boxes = page.evaluate(
                            "() => [...document.querySelectorAll('.runway-card')]"
                            ".map(e => { const live = getComputedStyle(e).transform; "
                            "e.style.transition = 'none'; e.style.transform = 'none'; "
                            "const b = e.getBoundingClientRect(); "
                            "const s = getComputedStyle(e); "
                            "const bw = parseFloat(s.borderLeftWidth) "
                            "+ parseFloat(s.borderRightWidth); "
                            "e.style.removeProperty('transform'); "
                            "e.style.removeProperty('transition'); "
                            "return {w: b.width, inner: b.width - bw, border: bw, "
                            "h: b.height, top: b.top, left: b.left, live: live}; })")
                        if len(boxes) != 3:
                            return False, "expected 3 runway cards, got %d" % len(boxes)
                        scaled = [b["live"] for b in boxes if b["live"] not in ("none", "")]
                        if len(scaled) != 1:
                            return False, (
                                "expected EXACTLY ONE of the three runway cards to carry the "
                                "selection scale (D3's 'selecting a card answers with a small "
                                "scale'), got %r — this measurement neutralises the transform to "
                                "read the LAYOUT box, so it is only meaningful while the "
                                "transform genuinely exists"
                                % ([b["live"] for b in boxes],))

                        tops = [b["top"] for b in boxes]
                        if max(tops) - min(tops) > 0.5:
                            return False, (
                                "expected all three cards on ONE line (equal tops), got %r - a "
                                "2 + 1 orphan is exactly B9's defect" % (tops,))
                        heights = [b["h"] for b in boxes]
                        if max(heights) - min(heights) > 0.5:
                            return False, "expected three equal card heights, got %r" % (heights,)
                        lefts = sorted(b["left"] for b in boxes)
                        if lefts != [b["left"] for b in sorted(boxes, key=lambda b: b["left"])]:
                            return False, "expected three distinct columns"

                        # B9's "equal within 1px" is asserted on the cards'
                        # BORDER-EXCLUDED widths, which is what "three
                        # equal columns" actually means and what the flex
                        # rule controls - AND, since 22-15-PLAN.md Task 1
                        # closed T6, on their outer widths too.
                        #
                        # 22-10-PLAN.md's STATED EXCEPTION IS DELETED HERE.
                        # It read: the cards' outer widths are not equal
                        # within 1px, because the saved card carries
                        # `.runway-card--selected`'s 2px border against its
                        # siblings' 1px and `box-sizing: border-box` does
                        # not hold the OUTER box of a `flex: 1 1 0` item
                        # (measured 98.67 against 96.66/96.67 at 390px).
                        # It named 22-15-PLAN.md as the plan that removes
                        # it. That plan holds every selected-state border
                        # constant at 1px and carries selection on
                        # `box-shadow: inset 0 0 0 2px`, which occupies no
                        # layout space, so `inner` and `w` have converged
                        # and the allowance is gone: plain equality on
                        # BOTH, and every card's own border total must now
                        # be exactly 2.0 (1px per side) with no second
                        # value permitted.
                        inners = [b["inner"] for b in boxes]
                        if max(inners) - min(inners) > 1.0:
                            return False, (
                                "expected three equal card widths within 1px once each card's own "
                                "border is excluded, got %r (outer %r)"
                                % (inners, [b["w"] for b in boxes]))
                        outers = [b["w"] for b in boxes]
                        if max(outers) - min(outers) > 1.0:
                            return False, (
                                "expected three equal card OUTER widths within 1px now that T6 is "
                                "closed - a selected card must be the same size as its siblings, "
                                "got %r (inner %r)" % (outers, inners))
                        borders = sorted({round(b["border"], 2) for b in boxes})
                        if borders != [2.0]:
                            return False, (
                                "expected every card's border total to be exactly 2.0 (1px per "
                                "side) in every selection state - T6 moved the 2px accent signal "
                                "to an inset ring, got border totals %r" % (borders,))
                        # Touch target, confirmed by measurement rather than
                        # assumed: the cards get narrower, and the hidden
                        # radio's register entry is exempt BY DELEGATION to
                        # this wrapping <label>, so the label itself must
                        # still clear 44px in BOTH axes.
                        for b in boxes:
                            if b["w"] < 44 or b["h"] < 44:
                                return False, (
                                    "every runway card must stay >=44x44 for the hidden radio's "
                                    "exempt-by-delegation touch-target entry, got %r" % (b,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px the three runway cards report one shared line (equal tops), equal "
                    "heights, and BOTH their border-excluded and their outer widths equal within "
                    "1px at a border total of exactly 2.0 each - 22-10's stated T6 allowance for "
                    "the selected card's 2px border is deleted, closed by 22-15-PLAN.md Task 1 - "
                    "and each still clears 44x44 - never a 2 + 1 orphan (B9, 22-10-PLAN.md Task 2) "
                    "- with the transform neutralised for the read and EXACTLY ONE card proven to "
                    "carry 23-10's selection scale",
                    _three_runway_cards_share_one_line_at_390px)

                def _selecting_a_theme_chip_answers_and_moves_no_layout_box():
                    # 23-10-PLAN.md Task 1 (D3/CFG-32). Two statements
                    # that only a real layout engine can make together:
                    #
                    #   1. Selection ANSWERS - the chip scales, and its
                    #      body's wash fades in over var(--motion-fast)
                    #      rather than cutting.
                    #   2. Selection moves NO layout box - T6's defect
                    #      (a selected card a different size from its
                    #      siblings, measured at 98.67px against 96.66px
                    #      at 390px) cannot recur through a transform,
                    #      and this is the measurement that says so
                    #      rather than the reasoning that assumes it.
                    #
                    # The box is read through offsetWidth/offsetHeight/
                    # offsetLeft/offsetTop, NOT getBoundingClientRect():
                    # the offset* family reports the LAYOUT box and is
                    # transform-independent by definition, which is
                    # exactly the distinction this check exists to prove.
                    # Plain equality, no tolerance - these are integers
                    # from the same element measured twice.
                    #
                    # POSITIONS ARE MEASURED RELATIVE TO THE CHIP GRID,
                    # not to the page, and that is a correction this
                    # check needed rather than a convenience: selecting a
                    # chip makes the form dirty, and 23-09's save bar
                    # replaces the section's own inline fallback Save
                    # button when it arrives, which removes a real 36px
                    # from the page ABOVE this card (measured: every chip
                    # moved from y=1608 to y=1572). That is another
                    # plan's intended behaviour, it happens whichever
                    # chip is clicked, and a page-absolute assertion
                    # would report it as this plan's layout shift. The
                    # statement that belongs here is that nothing inside
                    # the grid moved, and every chip in the grid is
                    # measured, not just the clicked one.
                    # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from the
                    # retired [data-usage-panel-target]/label.theme-chip
                    # departures panel to details.usage-row[data-usage=
                    # "departures"]/label.palette-chip. The "answers with
                    # a scale" half of this check's ORIGINAL property does
                    # NOT survive the rebuild — confirmed directly against
                    # style.css (30-07-PLAN.md Task 1's own comment): the
                    # selected .palette-chip's :has(input:checked) rule
                    # adds exactly three consequences (border-colour,
                    # inset box-shadow ring, the .palette-chip__name wash)
                    # and NO transform/transition, a DELIBERATE, already-
                    # recorded 30-07 decision ("a fourth [treatment] would
                    # also need a new transition declared on this
                    # component's own base rule, out of this plan's
                    # scope"). Restating a scale/transition-duration
                    # assertion the real CSS no longer produces would make
                    # this check permanently red for a reason that is not
                    # a defect, so the property actually proved here is
                    # the one that DOES still hold: selection paints
                    # instantly via border/box-shadow/wash, and — the
                    # half that matters for T6 — moves no layout box at
                    # all, since box-shadow is `inset` and only the
                    # border's COLOUR (never its width) changes.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        probe = (
                            "() => {"
                            "const row = document.querySelector("
                            "'details.usage-row[data-usage=\"departures\"]');"
                            "if (!row) return {error: 'no departures row'};"
                            "const chips = [...row.querySelectorAll('label.palette-chip')]"
                            ".filter(c => c.querySelector('input[type=radio]'));"
                            "if (chips.length < 2) return {error: 'chips: ' + chips.length};"
                            "const target = chips.find("
                            "c => !c.querySelector('input[type=radio]').checked);"
                            "if (!target) return {error: 'every chip is already checked'};"
                            "const grid = target.closest('.palette');"
                            "if (!grid) return {error: 'no .palette'};"
                            "const read = e => { const s = getComputedStyle(e);"
                            "const name = e.querySelector('.palette-chip__name');"
                            "const ns = name ? getComputedStyle(name) : null;"
                            "return {w: e.offsetWidth, h: e.offsetHeight,"
                            " left: e.offsetLeft - grid.offsetLeft,"
                            " top: e.offsetTop - grid.offsetTop,"
                            " borderColor: s.borderColor, boxShadow: s.boxShadow,"
                            " wash: ns ? ns.backgroundColor : null}; };"
                            "return {value: target.querySelector('input[type=radio]').value,"
                            " chip: read(target),"
                            " grid: {w: grid.offsetWidth, h: grid.offsetHeight},"
                            " all: chips.map(c => { const r = read(c);"
                            " return [r.w, r.h, r.left, r.top]; })};"
                            "}")
                        before = page.evaluate(probe)
                        if before.get("error"):
                            return False, "could not find an unchecked palette chip: %s" % (
                                before["error"],)
                        value = before["value"]
                        _click_control(
                            page,
                            'details.usage-row[data-usage="departures"] '
                            'label.palette-chip input[type=radio][value="%s"]' % value)
                        # No transition to wait out any more (see the
                        # comment above) - a short settle for the change
                        # event/repaint is still cheap insurance.
                        page.wait_for_timeout(200)
                        after = page.evaluate(
                            probe.replace(
                                "const target = chips.find("
                                "c => !c.querySelector('input[type=radio]').checked);",
                                "const target = chips.find("
                                "c => c.querySelector('input[type=radio]').value === "
                                + repr(value).replace("'", '"') + ");"))
                        if after.get("error"):
                            return False, "could not re-find the clicked chip: %s" % (
                                after["error"],)

                        # --- 1. the answer is real -------------------
                        if before["chip"]["boxShadow"] not in ("none", ""):
                            return False, (
                                "expected an UNSELECTED palette chip to carry no box-shadow, got "
                                "%r" % (before["chip"]["boxShadow"],))
                        if after["chip"]["boxShadow"] in ("none", ""):
                            return False, (
                                "expected the newly-selected chip to carry the accent inset ring "
                                "(30-07-PLAN.md Task 1: box-shadow inset 0 0 0 2px), got %r - a "
                                "chip that switches state with no visible signal at all is the "
                                "behaviour this check exists to catch" % (after["chip"]["boxShadow"],))
                        if before["chip"]["borderColor"] == after["chip"]["borderColor"]:
                            return False, (
                                "expected the selected chip's border-colour to change to the "
                                "accent, both read %r" % (after["chip"]["borderColor"],))
                        if before["chip"]["wash"] == after["chip"]["wash"]:
                            return False, (
                                "expected the selected chip's .palette-chip__name wash to change "
                                "on selection, both read %r" % (after["chip"]["wash"],))

                        # --- 2. and nothing moved --------------------
                        for key in ("w", "h", "left", "top"):
                            if before["chip"][key] != after["chip"][key]:
                                return False, (
                                    "the chip's own LAYOUT box changed on selection: %s went from "
                                    "%r to %r. T6's defect was exactly this (98.67px against "
                                    "96.66px at 390px); a border-colour/inset-shadow selection "
                                    "signal must change no layout box at all"
                                    % (key, before["chip"][key], after["chip"][key]))
                        if before["grid"] != after["grid"]:
                            return False, (
                                "the chip grid's own layout box changed on selection: %r -> %r"
                                % (before["grid"], after["grid"]))
                        if before["all"] != after["all"]:
                            moved = [
                                (i, b, a) for i, (b, a)
                                in enumerate(zip(before["all"], after["all"])) if b != a]
                            return False, (
                                "chips MOVED inside the grid when one of them was selected - "
                                "siblings shifting is the visible half of T6, and it is exactly "
                                "what a border-width or padding-based selection signal does. "
                                "[index, before [w,h,left,top], after]: %r" % (moved,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "at 390px selecting a palette chip ANSWERS - the chip's border-colour changes "
                    "to the accent, an inset accent ring (box-shadow) appears, and the "
                    ".palette-chip__name wash changes - while its own LAYOUT box (offsetWidth/"
                    "Height/Left/Top), the grid's own box and EVERY chip's position inside it are "
                    "plain-equal before and after, so T6 cannot recur through the selection signal "
                    "(D3/CFG-32, 23-10-PLAN.md Task 1; re-pointed to .palette-chip and narrowed off "
                    "the scale/transition clauses 30-07-PLAN.md deliberately did not add, by "
                    "30-08-PLAN.md Task 2, CFG-85)",
                    _selecting_a_theme_chip_answers_and_moves_no_layout_box)

                def _both_dialogs_fade_in_and_leave_nothing_behind():
                    # 23-10-PLAN.md Task 2 (D3/CFG-32, T-23-36). The
                    # entrance is a stylesheet fact a source scan can
                    # read; the CLOSE is not. A <dialog> that fades out
                    # but never reaches `display: none` is an invisible
                    # sheet in the top layer that swallows every click on
                    # the page beneath it, and the only instrument that
                    # can see that is a real hit test. So this check
                    # does both: the opening is sampled mid-flight (a
                    # real transition is running, opacity below 1 two
                    # frames after the trigger), and the close is
                    # hit-tested at the viewport centre.
                    for route, trigger_sel in (
                        ("/history", "[data-view-panel-src]"),
                        ("/airlines", "[data-view-panel-src]"),
                    ):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            _login(page, harness.base_url())
                            page.goto(harness.base_url() + route)
                            page.wait_for_load_state("networkidle")
                            if page.query_selector(trigger_sel) is None:
                                return False, (
                                    "expected %s to render at least one %s dialog trigger"
                                    % (route, trigger_sel))
                            opening = page.evaluate(
                                "sel => new Promise(resolve => {"
                                "const d = document.getElementById('panel-lookup-dialog');"
                                "if (!d) { resolve({error: 'no dialog'}); return; }"
                                "document.querySelector(sel).click();"
                                "requestAnimationFrame(() => requestAnimationFrame(() => {"
                                "const s = getComputedStyle(d);"
                                "resolve({open: d.open, opacity: parseFloat(s.opacity),"
                                " dur: s.transitionDuration, props: s.transitionProperty,"
                                " transform: s.transform});"
                                "}));"
                                "})", trigger_sel)
                            if opening.get("error"):
                                return False, "%s: %s" % (route, opening["error"])
                            if not opening["open"]:
                                return False, (
                                    "%s: expected the trigger to open the dialog" % (route,))
                            if not (0 <= opening["opacity"] < 1):
                                return False, (
                                    "%s: expected the dialog to be MID-FADE two frames after "
                                    "opening (D3: both dialogs fade and zoom in via "
                                    "@starting-style), got opacity %r with transition %r on %r "
                                    "— a dialog already fully opaque two frames in is the "
                                    "instant open this plan replaces"
                                    % (route, opening["opacity"], opening["dur"],
                                       opening["props"]))
                            page.wait_for_timeout(600)
                            settled = page.evaluate(
                                "() => { const d ="
                                " document.getElementById('panel-lookup-dialog');"
                                "const s = getComputedStyle(d);"
                                "return {opacity: parseFloat(s.opacity), transform: s.transform,"
                                " display: s.display}; }")
                            if settled["opacity"] != 1:
                                return False, (
                                    "%s: expected the dialog to SETTLE fully opaque, got %r"
                                    % (route, settled))
                            if settled["transform"] not in ("none", "matrix(1, 0, 0, 1, 0, 0)"):
                                return False, (
                                    "%s: expected the dialog to settle at its own scale, got %r"
                                    % (route, settled["transform"]))

                            page.click("[data-view-panel-close]")
                            # Deliberately NO settle wait here: the whole
                            # point is that the close is over the instant
                            # it happens. A wait would hide exactly the
                            # defect this measures.
                            after = page.evaluate(
                                "() => { const d ="
                                " document.getElementById('panel-lookup-dialog');"
                                "const r = d.getBoundingClientRect();"
                                "const hit = document.elementFromPoint("
                                "Math.round(innerWidth / 2), Math.round(innerHeight / 2));"
                                "return {open: d.open, display: getComputedStyle(d).display,"
                                " area: r.width * r.height,"
                                " hit: !!(hit && d.contains(hit)),"
                                " hitTag: hit ? hit.tagName + '.' + hit.className : null}; }")
                            if after["open"]:
                                return False, "%s: the dialog is still open after close()" % (
                                    route,)
                            for field, expected, why in (
                                ("display", "none",
                                 "a dialog left displayed after close() is an invisible sheet "
                                 "over the page (T-23-36)"),
                            ):
                                if after[field] != expected:
                                    return False, (
                                        "%s: expected the closed dialog's %s to be %r, got %r — "
                                        "%s (full read %r)"
                                        % (route, field, expected, after[field], why, after))
                            if after["area"] != 0:
                                return False, (
                                    "%s: the closed dialog still occupies %r px2 — %r"
                                    % (route, after["area"], after))
                            if after["hit"]:
                                return False, (
                                    "%s: a hit test at the viewport centre still lands INSIDE "
                                    "the closed dialog (%r) — every click on the page beneath it "
                                    "is being swallowed (T-23-36)" % (route, after["hitTag"]))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "both <dialog>s FADE AND ZOOM in — measured mid-flight, two frames after the "
                    "trigger, on History and on the Airlines gallery — settle fully opaque at "
                    "their own scale, and on close() reach display:none with a zero-area box and "
                    "a viewport-centre hit test that lands OUTSIDE them, with no settle wait at "
                    "all, so an invisible click-swallowing sheet cannot hide behind one "
                    "(D3/CFG-32, T-23-36, 23-10-PLAN.md Task 2)",
                    _both_dialogs_fade_in_and_leave_nothing_behind)

                def _the_live_preview_crossfade_settles_correct_through_its_own_listener():
                    # 23-10-PLAN.md Task 2 (D3/CFG-32, T-23-38). The
                    # crossfade's one real failure mode is settling on
                    # the WRONG theme, or settling invisible: both look
                    # identical to every source-level scan, because the
                    # stylesheet and the script are each individually
                    # correct. So this asserts the SETTLED state after
                    # the transition, never a frame during it.
                    #
                    # 27-04-PLAN.md Task 2 (T8, CFG-63): the OTHER half
                    # this check used to assert — Cancel restoring the
                    # SAVED theme through the same crossfade — is deleted
                    # along with "Annuler" itself (dirty-state.js's own
                    # header records the account). What is proven here
                    # instead, by running rather than by inspection, is
                    # the claim Task 2's own action text requires: the
                    # live preview still follows a chip selection through
                    # theme-preview.js's OWN delegated listener on the
                    # card, with dirty-state.js never in the loop at all —
                    # this check drives no Cancel and no save of any kind.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")
                        read = (
                            "() => { const i ="
                            " document.querySelector('.theme-live-preview__image');"
                            "return {src: i.getAttribute('src'),"
                            " opacity: parseFloat(getComputedStyle(i).opacity)}; }")
                        page.evaluate(read)  # pre-click baseline; no longer compared (Cancel retired)
                        # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from
                        # the retired [data-usage-panel-target]/
                        # label.theme-chip departures panel to
                        # details.usage-row[data-usage="departures"]/
                        # label.palette-chip - the crossfade mechanism
                        # itself (theme-preview.js's applyPreviewSrc()/
                        # FADE_CLASS) is unchanged by the rebuild, so
                        # every OTHER clause below is unchanged too.
                        target = page.evaluate(
                            "() => { const row = document.querySelector("
                            "'details.usage-row[data-usage=\"departures\"]');"
                            "const chip = [...row.querySelectorAll('label.palette-chip')].find("
                            "c => c.getAttribute('data-preview-src')"
                            " && !c.querySelector('input[type=radio]').checked);"
                            "return chip ? {value: chip.querySelector("
                            "'input[type=radio]').value,"
                            " src: chip.getAttribute('data-preview-src')} : null; }")
                        if not target:
                            return False, "found no unchecked departures palette chip to click"
                        # Click, then WAIT FOR THE TRANSITION ITSELF to
                        # be created rather than sampling at a guessed
                        # instant. Without this the whole check would
                        # pass on the CUT this plan replaces: a preview
                        # that swaps instantly also settles on the right
                        # theme at opacity 1, so "settles correct" alone
                        # is satisfied by doing nothing.
                        #
                        # The original form sampled two rAF after the
                        # click and asserted 0 <= opacity < 1. That is
                        # the right INTENT measured the wrong way: two
                        # frames is a guess about the machine, not about
                        # the app, and on a loaded runner the transition
                        # has been created but has not yet painted a
                        # changed value. It failed exactly that way in CI
                        # (`got opacity 1 with transition '0.18s' on
                        # 'opacity'` — the transition was right there),
                        # and `deferred-items.md` had already recorded it
                        # as an intermittent seen in mutation runs.
                        #
                        # `transitionrun` fires when the browser CREATES
                        # the transition, before any delay and before the
                        # first painted step, so it is independent of
                        # frame timing — while a cut creates no
                        # transition at all and fires nothing. The
                        # listener is on `document` in the CAPTURE phase
                        # because the crossfade swaps layer elements: a
                        # listener bound to whichever image existed
                        # before the click can be watching the wrong one.
                        mid = page.evaluate(
                            "sel => new Promise(resolve => {"
                            "let ran = null;"
                            "const onRun = e => {"
                            "if (ran) return;"
                            "if (e.propertyName !== 'opacity') return;"
                            "if (!(e.target instanceof Element)) return;"
                            "if (!e.target.matches('.theme-live-preview__image')) return;"
                            "const s = getComputedStyle(e.target);"
                            "ran = {opacity: parseFloat(s.opacity), dur: s.transitionDuration,"
                            " props: s.transitionProperty};"
                            "};"
                            "document.addEventListener('transitionrun', onRun, true);"
                            "document.querySelector(sel).click();"
                            "setTimeout(() => {"
                            "document.removeEventListener('transitionrun', onRun, true);"
                            "const i = document.querySelector('.theme-live-preview__image');"
                            "const s = i ? getComputedStyle(i) : null;"
                            "resolve({ran: ran, dur: s && s.transitionDuration,"
                            " props: s && s.transitionProperty});"
                            "}, 400);"
                            "})",
                            'details.usage-row[data-usage="departures"] '
                            'label.palette-chip input[type=radio][value="%s"]' % target["value"])
                        if not mid["ran"]:
                            return False, (
                                "expected the live preview to CROSSFADE — no opacity transition "
                                "was created on .theme-live-preview__image within 400ms of the "
                                "chip being selected (the preview's own computed transition is "
                                "%r on %r) — a preview that changes with no transition at all is "
                                "the CUT this plan replaces, and every other assertion in this "
                                "check is satisfied by that cut"
                                % (mid["dur"], mid["props"]))
                        page.wait_for_timeout(900)
                        settled = page.evaluate(read)
                        if settled["src"] != target["src"]:
                            return False, (
                                "the crossfade settled on the WRONG theme: the preview reads %r "
                                "after selecting the chip whose own data-preview-src is %r "
                                "(T-23-38)" % (settled["src"], target["src"]))
                        if settled["opacity"] != 1:
                            return False, (
                                "the crossfade settled INVISIBLE (opacity %r) — a fade-out with "
                                "no fade back in is worse than the cut it replaced"
                                % (settled["opacity"],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the live theme preview CROSSFADES - proven by the opacity transition the "
                    "browser CREATES on the preview image, caught as a transitionrun event rather "
                    "than sampled at a guessed instant, because every other assertion here is "
                    "satisfied by the cut this plan replaces - and settles on the theme that was "
                    "actually selected, fully opaque rather than stuck mid-fade, driven entirely by "
                    "theme-preview.js's OWN delegated listener with no save and no dirty-state.js "
                    "involvement at all (D3/CFG-32, T-23-38, 23-10-PLAN.md Task 2; the Cancel half "
                    "retired by 27-04-PLAN.md Task 2, CFG-63; re-pointed to details.usage-row/"
                    ".palette-chip by 30-08-PLAN.md Task 2, CFG-85)",
                    _the_live_preview_crossfade_settles_correct_through_its_own_listener)

                def _images_hold_their_place_before_they_arrive():
                    # 23-10-PLAN.md Task 3 (D3/CFG-32, T-23-39). The only
                    # assertion that proves a skeleton did what it was
                    # for: the box BEFORE the image resource resolves
                    # equals the box AFTER, measured at the 360px
                    # contract floor and at 1280px.
                    #
                    # The image request is HELD by a route handler rather
                    # than raced against - "measure quickly and hope" is
                    # how this kind of check passes on a fast machine and
                    # proves nothing. Nothing is faked: the real request
                    # is paused, the real boxes are read, the real
                    # request is then let through, and the real decoded
                    # image is measured.
                    #
                    # A skeleton that does not reserve the final size IS
                    # the layout shift it exists to prevent, which is why
                    # the reserved box is asserted to be a real box
                    # (a collapsed 2x2 image box equals a collapsed 2x2
                    # image box, and that is how this check would
                    # otherwise pass on the defect: Home at 1280px
                    # measured 2x2 before and 380x506 after).
                    surfaces = (
                        ("/", ".preview-frame", ".preview-frame__image", "**/gallery/**", 100, ()),
                        # 30-08-PLAN.md Task 2 (CFG-85): the accordion's
                        # own .palette-chip renders NO <img> of any kind
                        # (30-UI-SPEC.md's Swatch Rendering Contract - a
                        # CSS-drawn shape only), so the departures/
                        # arrivals/calendar rows this surface used to
                        # measure no longer have one. The ONE surviving
                        # .theme-chip/.theme-chip__preview pair on
                        # Display now lives inside the rules row's own
                        # nested, closed-by-default rule-add disclosure -
                        # opened here (rules row summary, then the
                        # rule-add summary) before measuring, which keeps
                        # this a real, laid-out surface rather than the
                        # collapsed-box vacuity this check's own comment
                        # already warns about. 30, because that chip is
                        # the COMPACT variant, whose band is 36px rather
                        # than the base 56px - measured, not assumed.
                        # Still well clear of the ~2px a collapsed
                        # replaced element reports, which is the number
                        # this floor exists to exclude.
                        ("/display", ".theme-chip", ".theme-chip__preview",
                         "**/theme-preview/**", 30,
                         ('details.usage-row[data-usage="rules"] > summary',
                          '.rule-add > summary')),
                    )
                    for width in (VIEWPORT_MIN_SUPPORTED["width"],
                                  VIEWPORT_DESKTOP["width"]):
                        for route_path, box_sel, img_sel, url_glob, floor, openers in surfaces:
                            context = browser.new_context(
                                viewport={"width": width, "height": VIEWPORT_DESKTOP["height"]})
                            try:
                                page = context.new_page()
                                _login(page, harness.base_url())
                                held = []
                                page.route(url_glob, lambda route: held.append(route))
                                page.goto(harness.base_url() + route_path,
                                          wait_until="domcontentloaded")
                                for opener in openers:
                                    page.click(opener)
                                page.wait_for_selector(img_sel, state="attached")
                                page.wait_for_timeout(400)
                                read = (
                                    "sels => { const b = document.querySelector(sels[0]);"
                                    "const i = document.querySelector(sels[1]);"
                                    "if (!b || !i) return null;"
                                    "const r = e => { const x = e.getBoundingClientRect();"
                                    "return [Math.round(x.width * 100) / 100,"
                                    " Math.round(x.height * 100) / 100]; };"
                                    "return {box: r(b), img: r(i),"
                                    " skeleton: getComputedStyle(i).backgroundImage,"
                                    " complete: i.complete, nat: [i.naturalWidth,"
                                    " i.naturalHeight]}; }")
                                before = page.evaluate(read, [box_sel, img_sel])
                                if before is None:
                                    return False, (
                                        "%s at %dpx renders no %s/%s to measure"
                                        % (route_path, width, box_sel, img_sel))
                                if before["nat"][0]:
                                    return False, (
                                        "%s at %dpx: the image resolved before it could be "
                                        "measured unloaded — the hold did not hold (%r)"
                                        % (route_path, width, before))
                                if before["img"][1] < floor:
                                    return False, (
                                        "%s at %dpx: the UNLOADED image reserves only %r — a "
                                        "collapsed box is the layout shift a skeleton exists to "
                                        "prevent, and it would make the equality below pass for "
                                        "the wrong reason (T-23-39)"
                                        % (route_path, width, before["img"]))
                                if before["skeleton"] == "none":
                                    return False, (
                                        "%s at %dpx: %s paints no skeleton at all while its "
                                        "image is still coming — the reserved box is correct and "
                                        "completely blank"
                                        % (route_path, width, img_sel))
                                for route_obj in held:
                                    route_obj.continue_()
                                page.unroute(url_glob)
                                page.wait_for_function(
                                    "sel => { const i = document.querySelector(sel);"
                                    " return i.complete && i.naturalWidth > 0; }",
                                    arg=img_sel, timeout=5000)
                                page.wait_for_timeout(200)
                                after = page.evaluate(read, [box_sel, img_sel])
                                if before["box"] != after["box"]:
                                    return False, (
                                        "%s at %dpx: %s moved when its image arrived — %r before, "
                                        "%r after. A skeleton whose box differs from its image's "
                                        "box IS the layout shift it was added to prevent "
                                        "(T-23-39)"
                                        % (route_path, width, box_sel, before["box"],
                                           after["box"]))
                                if before["img"] != after["img"]:
                                    return False, (
                                        "%s at %dpx: %s itself resized when it arrived — %r "
                                        "before, %r after (T-23-39)"
                                        % (route_path, width, img_sel, before["img"],
                                           after["img"]))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "Home's frame picture and a theme chip's preview band each reserve their FINAL "
                    "box before their image arrives — the real request is HELD, the real box is "
                    "measured unloaded (and asserted to be a real box, not a collapsed one, with "
                    "a skeleton painted in it), the request is let through, and the box after the "
                    "decoded image lands is plain-equal to the box before it, at the 360px "
                    "contract floor and at 1280px (D3/CFG-32, T-23-39, 23-10-PLAN.md Task 3)",
                    _images_hold_their_place_before_they_arrive)

                # 30-03-PLAN.md Task 3 (CFG-85): the check that used to
                # live here — _the_no_js_floor_holds_for_both_settings_
                # pages — is RETIRED and LEDGERED to 30-08. Its "no
                # collapsed usage panel" assertion (`.frame-colours__
                # usage-panel`, D-08's floor) has no equivalent once the
                # colour_usage radiogroup/usage-panel mechanism is
                # retired.
                #
                # A REQUIREMENT-TEXT VS. APPROVED-DESIGN DISCREPANCY,
                # recorded here rather than papered over (see this
                # plan's own SUMMARY.md for the full argument, flagged
                # for the developer): CFG-85's own requirement text
                # includes "every row open with scripts blocked", but
                # 30-UI-SPEC.md's developer-approved accordion is a
                # native `<details name="aspect-rows">` group, which is
                # mutually exclusive by construction — "every row open"
                # is not achievable while keeping that accordion. The
                # PROPERTY CFG-85 is actually protecting — no control is
                # unreachable or unsaveable with scripts blocked — is
                # met, and met MORE strongly than by a visible stack: a
                # closed <details>'s form controls remain in the DOM and
                # DO participate in form submission; <summary> is
                # natively activatable by pointer and keyboard with
                # scripts blocked, so a visitor can open any row
                # themselves; and the preview is server-rendered for the
                # SAVED theme either way. 30-08's replacement must prove
                # all three of those points, with scripts blocked, at
                # 360px, in both languages, with the verdict read back
                # from disk — a STRONGER proof than this retired check's
                # single collapsed-panel count, never a quietly narrowed
                # one. See _ASPECT_REPIN_LEDGER below.

                # --- 22-13-PLAN.md Task 3 (X3): the login card ---

                def _login_card_stacks_at_both_widths():
                    # X3's measurement, re-taken by a real layout engine
                    # at both ends of the range the audit measured:
                    # desktop was a 225x44 r8 field beside a 68x30 r6
                    # button sitting 7px lower, and at 390px the field
                    # kept 225 of 278px with the button glued underneath
                    # at a 0px gap.
                    for width in (390, 1280):
                        context = browser.new_context(
                            viewport={"width": width, "height": 844})
                        try:
                            page = context.new_page()
                            page.goto(harness.base_url() + "/login")
                            field = page.locator(".login-form__input").bounding_box()
                            primary = page.locator(
                                '.login-card button[type="submit"]').bounding_box()
                            form = page.locator(".login-form").bounding_box()
                            if not field or not primary or not form:
                                return False, "%dpx: expected both controls to be laid out" % width
                            if abs(field["width"] - primary["width"]) > 1:
                                return False, (
                                    "%dpx: the field and the primary must be the same width, "
                                    "measured %.1f vs %.1f"
                                    % (width, field["width"], primary["width"]))
                            if abs(field["width"] - form["width"]) > 1:
                                return False, (
                                    "%dpx: both controls must fill the card's content column "
                                    "(%.1f), the field measured %.1f"
                                    % (width, form["width"], field["width"]))
                            for name, box in (("field", field), ("primary", primary)):
                                if abs(box["height"] - 44) > 0.5:
                                    return False, (
                                        "%dpx: the %s must be 44px tall, measured %.1f"
                                        % (width, name, box["height"]))
                            gap = primary["y"] - (field["y"] + field["height"])
                            if gap <= 0:
                                return False, (
                                    "%dpx: the two controls must be separated, measured a "
                                    "%.1fpx gap" % (width, gap))
                            if abs(gap - 16) > 1:
                                return False, (
                                    "%dpx: the gap must be the one medium spacing token "
                                    "(16px), measured %.1f" % (width, gap))
                            # Same radius as well as same height — the
                            # other half of C4's composition rule, which
                            # a bounding box cannot see.
                            radii = page.evaluate(
                                "() => [getComputedStyle(document.querySelector("
                                "'.login-form__input')).borderTopLeftRadius,"
                                " getComputedStyle(document.querySelector("
                                "'.login-card button[type=\\\"submit\\\"]'))"
                                ".borderTopLeftRadius]")
                            if radii[0] != radii[1]:
                                return False, (
                                    "%dpx: the field and the primary must share a radius, "
                                    "measured %r" % (width, radii))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "at 390px and at 1280px the login card's field and primary are stacked, the "
                    "same width, filling the card's content column, both 44px tall, sharing one "
                    "radius and separated by the one 16px token — never a 225x44 field beside a "
                    "68x30 button, and never glued at a 0px gap (X3, 22-13-PLAN.md Task 3)",
                    _login_card_stacks_at_both_widths)

                def _show_password_toggle_reveals_itself_and_swaps_its_name():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        page.goto(harness.base_url() + "/login")
                        toggle = page.locator("[data-login-reveal]")
                        toggle.wait_for(state="visible")
                        if toggle.get_attribute("hidden") is not None:
                            return False, (
                                "login-card.js must remove the server-rendered hidden "
                                "attribute, not merely override it in CSS — a visible "
                                "control that is still hidden from assistive tech is worse "
                                "than the defect")
                        show_name = toggle.get_attribute("aria-label")
                        if not show_name:
                            return False, "expected the icon-only toggle to carry an aria-label"
                        if toggle.get_attribute("aria-pressed") != "false":
                            return False, "expected the toggle to start unpressed"
                        if page.locator("#password").get_attribute("type") != "password":
                            return False, "expected the field to start masked"
                        # The class-at-load idiom: the gutter is
                        # reserved only now that the toggle is there.
                        wrapper_class = page.locator(".login-form__field").get_attribute("class")
                        if "login-form__field--with-toggle" not in (wrapper_class or ""):
                            return False, (
                                "expected login-card.js to append the padding modifier at "
                                "load, got %r" % (wrapper_class,))
                        # .copy-btn reused verbatim: a 22x22 visual box
                        # with the ::before inset synthesizing 44x44.
                        hit = toggle.evaluate(
                            "el => { var r = el.getBoundingClientRect();"
                            " var s = getComputedStyle(el, '::before');"
                            " return [r.width - parseFloat(s.left) - parseFloat(s.right),"
                            " r.height - parseFloat(s.top) - parseFloat(s.bottom)]; }")
                        if not hit or hit[0] < 44 or hit[1] < 44:
                            return False, (
                                "expected the toggle's hit area to measure at least 44x44 in "
                                "both axes, measured %r" % (hit,))
                        toggle.click()
                        hide_name = toggle.get_attribute("aria-label")
                        if hide_name == show_name or not hide_name:
                            return False, (
                                "the accessible name must swap with the state, still %r"
                                % (hide_name,))
                        if toggle.get_attribute("aria-pressed") != "true":
                            return False, "expected aria-pressed to flip to true"
                        if page.locator("#password").get_attribute("type") != "text":
                            return False, "expected the field to reveal its value"
                        toggle.click()
                        if toggle.get_attribute("aria-label") != show_name:
                            return False, "expected the accessible name to swap back"
                        if page.locator("#password").get_attribute("type") != "password":
                            return False, "expected the field to mask again"
                    finally:
                        context.close()

                    # D-09's floor, asserted at this plan's own commit:
                    # with scripts blocked the toggle is not there at all
                    # (never a dead control), no gutter is reserved for
                    # it, and the form still signs in.
                    with _no_js_page(
                            browser.new_context, harness.base_url(), "/login", sign_in=False) as page:
                        if page.locator("[data-login-reveal]").is_visible():
                            return False, (
                                "with scripts blocked the toggle must stay hidden — a "
                                "control that silently does nothing is worse than no "
                                "control")
                        wrapper_class = page.locator(".login-form__field").get_attribute("class")
                        if "login-form__field--with-toggle" in (wrapper_class or ""):
                            return False, (
                                "with scripts blocked the field must reserve no gutter for "
                                "a toggle that is not shown")
                        page.fill("#password", TEST_PASSWORD)
                        with page.expect_navigation():
                            page.click('button[type="submit"]')
                        if "/login" in page.url:
                            return False, (
                                "expected a scripts-blocked sign-in to succeed, landed on %r"
                                % page.url)
                        return True, ""
                check(
                    "the show-password toggle reveals ITSELF at load (the hidden attribute is "
                    "removed, not overridden), swaps aria-pressed and its translated accessible "
                    "name with the state, keeps .copy-btn's synthesized 44x44 hit area — and "
                    "with scripts blocked it never appears, reserves no gutter, and the form "
                    "still signs in (X3/D-09, 22-13-PLAN.md Task 3)",
                    _show_password_toggle_reveals_itself_and_swaps_its_name)

                def _lockout_countdown_ticks_and_re_enables_the_form():
                    # Its own isolated Harness(): driving the
                    # process-global LoginThrottle to its limit locks
                    # THAT subprocess out for the whole window, and the
                    # lockout branch is checked before the password is,
                    # so a correct password cannot unlock it over HTTP.
                    #
                    # Playwright's clock API drives the countdown to zero
                    # instead of this check sleeping for the real
                    # five-minute window. The timer under test is the
                    # page's own; only its clock is faked.
                    lockout_harness = Harness()
                    context = None
                    try:
                        lockout_harness.start()
                        base_url = lockout_harness.base_url()
                        context = browser.new_context()
                        page = context.new_page()
                        page.clock.install()
                        page.goto(base_url + "/login")
                        for _attempt in range(auth.LOGIN_FAILURE_LIMIT + 1):
                            page.fill("#password", "not-the-password")
                            with page.expect_navigation():
                                page.click('button[type="submit"]')
                        seed = page.locator(".login-form").get_attribute(
                            "data-lockout-seconds")
                        if not seed:
                            return False, (
                                "expected the locked-out form to carry the server's own "
                                "remaining-seconds seed")
                        remaining = int(seed)
                        if remaining <= 0:
                            return False, "expected a positive seed, got %r" % (seed,)
                        if not page.locator("#password").is_disabled():
                            return False, "expected the password field to be disabled"
                        if not page.locator('button[type="submit"]').is_disabled():
                            return False, "expected the primary to be disabled"
                        first_text = page.locator("#login-error").inner_text()
                        page.clock.run_for(2000)
                        ticked_text = page.locator("#login-error").inner_text()
                        if ticked_text == first_text:
                            return False, (
                                "the countdown must tick — the sentence was still %r after "
                                "two seconds" % (first_text,))
                        if str(remaining - 2) not in ticked_text:
                            return False, (
                                "expected the sentence to count down from the server's own "
                                "seed, got %r" % (ticked_text,))
                        # All the way to zero: the form re-enables itself
                        # with no reload.
                        page.clock.run_for((remaining + 2) * 1000)
                        if page.locator("#password").is_disabled():
                            return False, (
                                "expected the password field to re-enable itself at zero")
                        if page.locator('button[type="submit"]').is_disabled():
                            return False, "expected the primary to re-enable itself at zero"
                        if page.locator("#login-error").inner_text().strip():
                            return False, (
                                "expected the expired lockout sentence to be cleared")
                        if page.locator("#password").get_attribute("aria-describedby"):
                            return False, (
                                "expected the field to stop pointing at a message that is "
                                "no longer there")
                        return True, ""
                    finally:
                        if context is not None:
                            context.close()
                        lockout_harness.stop()
                        lockout_harness.cleanup()
                check(
                    "a locked-out login page ticks down from the server's own seed, with both "
                    "controls natively disabled, and re-enables them by itself at zero with no "
                    "reload — the message cleared and its aria-describedby dropped with it "
                    "(X3, 22-13-PLAN.md Task 3)",
                    _lockout_countdown_ticks_and_re_enables_the_form)

                def _nav_status_segments_never_break_mid_phrase_in_french():
                    # B10 (22-AUDIT.md's own measurement: .nav-status was
                    # 207x48 and broke "Screen on · Quiet hours" / "on";
                    # in French "Heures / calmes activées"). The target is
                    # getClientRects().length === 1 PER SEGMENT at both
                    # the 240px sidebar and a 390px phone — a count only a
                    # real layout engine can produce, which is why this
                    # one is here rather than in a source harness.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        context.add_cookies([{
                            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr",
                            "url": harness.base_url()}])
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")
                        desktop = page.evaluate(
                            "() => {"
                            " var aside = document.querySelector('.dashboard-sidebar');"
                            " var st = aside.querySelector('.nav-status');"
                            " return {"
                            "  asideWidth: aside.getBoundingClientRect().width,"
                            "  height: st.getBoundingClientRect().height,"
                            "  segments: Array.prototype.map.call("
                            "    st.querySelectorAll('.nav-status__segment'),"
                            "    function (sg) { return [sg.getClientRects().length,"
                            "      sg.textContent, sg.getBoundingClientRect().width]; })"
                            " };}")
                        if round(desktop["asideWidth"]) != 240:
                            return False, (
                                "expected the 240px sidebar this contract is measured against, "
                                "got %r" % (desktop["asideWidth"],))
                        if len(desktop["segments"]) != 2:
                            return False, (
                                "expected two state segments, got %r" % (desktop["segments"],))
                        for rects, text, width in desktop["segments"]:
                            if rects != 1:
                                return False, (
                                    "segment %r broke into %d client rects in the 240px sidebar "
                                    "— the line may break BETWEEN segments, never inside one"
                                    % (text, rects))
                            if not any(ch > "\x7f" for ch in text):
                                return False, (
                                    "expected the French reminder text, got %r — the English "
                                    "segments are shorter and would not exercise the contract"
                                    % (text,))
                            if width > 207:
                                return False, (
                                    "French's longest segment (%r, %rpx) must fit the sidebar's "
                                    "207px content column" % (text, width))
                        if desktop["height"] > 48:
                            return False, (
                                "expected the reminder to stay within B10's 48px ceiling, got %r"
                                % (desktop["height"],))
                        context.close()

                        # The same contract at 390px, inside the dropdown.
                        context = browser.new_context(viewport=VIEWPORT_PHONE)
                        page = context.new_page()
                        _login(page, harness.base_url())
                        context.add_cookies([{
                            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr",
                            "url": harness.base_url()}])
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")
                        page.click("#site-nav-toggle")
                        page.wait_for_timeout(400)
                        phone = page.evaluate(
                            "() => {"
                            " var panel = document.getElementById('mobile-nav');"
                            " var st = panel.querySelector('.nav-status');"
                            " return {"
                            "  tag: st.tagName, href: st.getAttribute('href'),"
                            "  height: st.getBoundingClientRect().height,"
                            "  panelHeight: panel.getBoundingClientRect().height,"
                            "  segments: Array.prototype.map.call("
                            "    st.querySelectorAll('.nav-status__segment'),"
                            "    function (sg) { return [sg.getClientRects().length,"
                            "      sg.textContent]; })"
                            " };}")
                        for rects, text in phone["segments"]:
                            if rects != 1:
                                return False, (
                                    "segment %r broke into %d client rects at 390px"
                                    % (text, rects))
                        if phone["height"] > 48:
                            return False, (
                                "expected the reminder within 48px at 390px, got %r"
                                % (phone["height"],))
                        if phone["tag"] != "A" or phone["href"] != "/":
                            return False, (
                                "off Home the reminder must stay a link to Home, got %r/%r"
                                % (phone["tag"], phone["href"]))
                        # X9's actual fix: the remaining push, measured.
                        if phone["panelHeight"] > 220:
                            return False, (
                                "X9's target is a remaining push of at most 220px, measured "
                                "%rpx" % (phone["panelHeight"],))

                        # And on Home it is not a link at all, so it
                        # cannot claim a destination the user occupies.
                        page.goto(harness.base_url() + "/")
                        page.wait_for_load_state("networkidle")
                        page.click("#site-nav-toggle")
                        page.wait_for_timeout(400)
                        home = page.evaluate(
                            "() => {"
                            " var st = document.getElementById('mobile-nav')"
                            "   .querySelector('.nav-status');"
                            " return {tag: st.tagName, href: st.getAttribute('href'),"
                            "         label: st.getAttribute('aria-label'),"
                            "         text: st.textContent};}")
                        if home["tag"] != "SPAN" or home["href"] is not None:
                            return False, (
                                "on Home the reminder must be a <span> with no href, got %r/%r"
                                % (home["tag"], home["href"]))
                        if "accueil" in (home["label"] or "").lower():
                            return False, (
                                "the Home reminder must not name a destination, got %r"
                                % (home["label"],))
                        if (home["label"] or "").strip() != (home["text"] or "").strip():
                            return False, (
                                "the announced name and the visible state must be the same "
                                "words, got %r vs %r" % (home["label"], home["text"]))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "in French the two nav-status segments each report exactly ONE client rect at both "
                    "the 240px sidebar and 390px — the line breaks between them, never mid-phrase — the "
                    "reminder stays within 48px, the reduced dropdown opens by at most 220px, and on "
                    "Home the reminder is a <span> with no href whose announced name is the visible "
                    "state and names no destination (B10/X9/D-04, 22-14-PLAN.md Task 2)",
                    _nav_status_segments_never_break_mid_phrase_in_french)

                def _mobile_nav_close_leaves_hidden_and_aria_expanded_consistent():
                    # T5, and D-02's own minimum-set item 3. Two paths,
                    # because the defect had two halves: a transitionend
                    # listener with no target/property filter (any child's
                    # colour transition could hide an OPEN panel), and a
                    # close with no transition at all that never re-applied
                    # the hidden property.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        def state():
                            return page.evaluate(
                                "() => {"
                                " var p = document.getElementById('mobile-nav');"
                                " var t = document.getElementById('site-nav-toggle');"
                                " return {hidden: p.hidden,"
                                "         expanded: t.getAttribute('aria-expanded'),"
                                "         open: p.classList.contains('mobile-nav--open'),"
                                "         height: p.getBoundingClientRect().height};}")

                        start = state()
                        if not start["hidden"] or start["expanded"] != "false":
                            return False, (
                                "expected the panel to start hidden and closed, got %r" % (start,))
                        page.click("#site-nav-toggle")
                        page.wait_for_timeout(400)
                        opened = state()
                        if opened["hidden"] or opened["expanded"] != "true" or not opened["open"]:
                            return False, "expected an open panel after the first click, got %r" % (opened,)
                        if opened["height"] <= 0:
                            return False, "expected the open panel to have a box"

                        # A descendant transition must NOT hide the open
                        # panel: fire a transitionend from a child with the
                        # very property the listener cares about, which is
                        # the strictest form of the target filter.
                        page.evaluate(
                            "() => {"
                            " var p = document.getElementById('mobile-nav');"
                            " var child = p.querySelector('button, a, form');"
                            " child.dispatchEvent(new TransitionEvent('transitionend',"
                            "   {bubbles: true, propertyName: 'max-height'}));}")
                        page.wait_for_timeout(50)
                        after_child = state()
                        if after_child["hidden"] or after_child["expanded"] != "true":
                            return False, (
                                "a descendant's transitionend must never hide an OPEN panel, got %r"
                                % (after_child,))

                        page.click("#site-nav-toggle")
                        page.wait_for_timeout(600)
                        closed = state()
                        if not closed["hidden"] or closed["expanded"] != "false" or closed["open"]:
                            return False, (
                                "expected hidden and aria-expanded to agree after a transitioned "
                                "close, got %r" % (closed,))
                        context.close()

                        # The no-transition path: reduced motion, where the
                        # stylesheet switches the transition off entirely
                        # and no transitionend will ever arrive.
                        context = browser.new_context(
                            viewport=VIEWPORT_PHONE, reduced_motion="reduce")
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")
                        page.click("#site-nav-toggle")
                        page.click("#site-nav-toggle")
                        reduced = page.evaluate(
                            "() => {"
                            " var p = document.getElementById('mobile-nav');"
                            " var t = document.getElementById('site-nav-toggle');"
                            " return {hidden: p.hidden,"
                            "         expanded: t.getAttribute('aria-expanded'),"
                            "         transition: getComputedStyle(p).transitionDuration};}")
                        if reduced["expanded"] != "false":
                            return False, "expected aria-expanded=false after the close"
                        if not reduced["hidden"]:
                            return False, (
                                "with no transition to wait for, hidden must be applied "
                                "SYNCHRONOUSLY — got %r" % (reduced,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the mobile nav opens and closes leaving the hidden property and aria-expanded "
                    "consistent on both paths — a descendant's transitionend never hides an open panel, "
                    "and a close with no transition applies hidden synchronously rather than waiting for "
                    "an event that never arrives (T5/D-02, 22-14-PLAN.md Task 2)",
                    _mobile_nav_close_leaves_hidden_and_aria_expanded_consistent)

                def _the_dirty_bar_never_overlaps_the_tab_bar_sidebar_or_the_pages_last_element():
                    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED, not
                    # a mechanical swap — this check's own pre-28-08
                    # subject proved the save-status region was NEVER
                    # position: fixed/sticky. That is exactly the contract
                    # this phase reverses: the restored bar IS
                    # position: fixed, at both breakpoints
                    # (28-08-PLAN.md Task 2). Retargeted onto the bar, and
                    # widened to the case 28-08's own clearance work turns
                    # on: the bar must never intersect the ONE other fixed
                    # element each breakpoint has (the tab bar under
                    # 960px, the sticky sidebar column at and above it),
                    # and the page's own last in-flow element must never
                    # sit under either — measured geometrically, via
                    # resolved getBoundingClientRect()es (never a CSS
                    # property value), in BOTH shipped languages, since
                    # the longer French copy is what makes the bar wrap
                    # to two lines — the case a single-language
                    # measurement misses.
                    #
                    # SCOPE NOTE: the scripts-BLOCKED variant of the
                    # last-in-flow-element clause is 28-08-PLAN.md Task
                    # 2's own acceptance criterion. 28-08's own SUMMARY
                    # records it as verified LIVE in a real Chromium tab
                    # during that plan's own execution, not as an
                    # automated Playwright check in this file — the
                    # automated coverage that DOES exist for it
                    # (test_config_page.py/test_status_pages.py) reads the
                    # CSS SOURCE for the :has(.dirty-bar) clearance rule
                    # rather than rendering a scripts-blocked page and
                    # measuring it. That gap is named here rather than
                    # assumed covered; this check itself only runs with
                    # scripts ENABLED.
                    def _intersects(a, b):
                        return (a["left"] < b["right"] and b["left"] < a["right"]
                                and a["top"] < b["bottom"] and b["top"] < a["bottom"])

                    for lang in ("en", "fr"):
                        for width, height, label, fixed_sel, fixed_name in (
                                (390, 844, "390x844", ".tab-bar", "the tab bar"),
                                (1280, 900, "1280x900", ".dashboard-sidebar",
                                 "the sidebar column")):
                            context = browser.new_context(
                                viewport={"width": width, "height": height})
                            try:
                                page = context.new_page()
                                _login(page, harness.base_url())
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": harness.base_url()}])
                                page.goto(harness.base_url() + "/display")
                                page.wait_for_load_state("networkidle")
                                current = page.eval_on_selector(
                                    'input[name="theme"]:checked', "el => el.value")
                                other = next(
                                    t for t in device_config.THEME_IDS if t != current)
                                _click_control(
                                    page, 'input[name="theme"][value="%s"]' % other)
                                _wait_for_bar(page)
                                # Well past var(--motion-fast) (180ms):
                                # the bar's own entrance animation
                                # (skypane-bar-arrive) translates it from
                                # var(--space-md) below its resting
                                # position — reading geometry mid-flight
                                # would measure a frame that is not the
                                # settled position this check asserts.
                                page.wait_for_timeout(600)

                                # SCROLLED TO THE BOTTOM: getBoundingClientRect()
                                # is viewport-relative, and both the bar
                                # (fixed near the viewport's own foot)
                                # and the page's last in-flow element can
                                # only ever occupy the SAME region of the
                                # viewport once the page is scrolled that
                                # far — unscrolled, the last element sits
                                # far below the fold and could never
                                # intersect the bar regardless of whether
                                # the clearance padding exists at all.
                                page.evaluate(
                                    "() => window.scrollTo(0, document.body.scrollHeight)")

                                # The bar itself renders as the LAST
                                # in-DOM-order child of .dashboard-main
                                # (config_page.py's render()) — it is
                                # taken OUT of flow by its own position:
                                # fixed, so the page's own last IN-FLOW
                                # element is the bar's last non-fixed
                                # PRECEDING sibling, never the bar
                                # comparing against itself.
                                geom = page.evaluate(
                                    "sel => {"
                                    " var bar = document.querySelector('[data-dirty-bar]');"
                                    " var fixedEl = document.querySelector(sel);"
                                    " var main = document.querySelector('.dashboard-main');"
                                    " var last = main ? main.lastElementChild : null;"
                                    " while (last && getComputedStyle(last).position === "
                                    "        'fixed') {"
                                    "   last = last.previousElementSibling;"
                                    " }"
                                    " var r = bar.getBoundingClientRect();"
                                    " var out = {bar: {top: r.top, bottom: r.bottom,"
                                    "                   left: r.left, right: r.right},"
                                    "            barPosition: getComputedStyle(bar).position,"
                                    "            fixedPresent: !!fixedEl, lastPresent: !!last};"
                                    " if (fixedEl) {"
                                    "   var f = fixedEl.getBoundingClientRect();"
                                    "   out.fixedEl = {top: f.top, bottom: f.bottom,"
                                    "                  left: f.left, right: f.right};"
                                    "   out.fixedDisplay = getComputedStyle(fixedEl).display;"
                                    " }"
                                    " if (last) {"
                                    "   var l = last.getBoundingClientRect();"
                                    "   out.last = {top: l.top, bottom: l.bottom,"
                                    "               left: l.left, right: l.right};"
                                    " }"
                                    " return out;}", fixed_sel)

                                if geom["barPosition"] != "fixed":
                                    return False, (
                                        "%s/%s: expected the bar to be position: fixed, got %r "
                                        "— the restored bar IS fixed at both breakpoints "
                                        "(28-08-PLAN.md Task 2)"
                                        % (label, lang, geom["barPosition"]))
                                if not geom["fixedPresent"] or geom.get("fixedDisplay") == "none":
                                    return False, (
                                        "%s/%s: expected %s (%r) visible, got display %r"
                                        % (label, lang, fixed_name, fixed_sel,
                                           geom.get("fixedDisplay")))
                                if _intersects(geom["bar"], geom["fixedEl"]):
                                    return False, (
                                        "%s/%s: the bar and %s must not intersect; bar %r vs "
                                        "%s %r" % (label, lang, fixed_name, geom["bar"],
                                                   fixed_name, geom["fixedEl"]))
                                if not geom["lastPresent"]:
                                    return False, (
                                        "%s/%s: expected the page's own last in-flow element "
                                        "(.dashboard-main's last child) to exist"
                                        % (label, lang))
                                if _intersects(geom["bar"], geom["last"]):
                                    return False, (
                                        "%s/%s: the bar must not cover the page's own last "
                                        "in-flow element; bar %r vs last element %r"
                                        % (label, lang, geom["bar"], geom["last"]))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "the restored bar — genuinely position: fixed at both breakpoints, the "
                    "INVERSE of this check's own retired position: fixed/sticky refusal — never "
                    "intersects the ONE other fixed element each breakpoint has (the tab bar "
                    "under 960px, the sticky sidebar column at and above it) and never covers "
                    "the page's own last in-flow element, measured via resolved "
                    "getBoundingClientRect()es (never a CSS property value) at 390x844 and "
                    "1280x900, in BOTH shipped languages (the longer French copy is what makes "
                    "the bar wrap to two lines) — the scripts-blocked variant of the "
                    "last-in-flow clause is 28-08-PLAN.md Task 2's own acceptance criterion, "
                    "verified LIVE by that plan rather than by an automated check in this file, "
                    "named here rather than assumed covered (CFG-31, 27-04-PLAN.md D-04/CFG-63; "
                    "retargeted onto the restored bar by 28-10-PLAN.md Task 3, CFG-77/CFG-78; "
                    "retired the fixed save-bar-vs-tab-bar geometry D-10/T7, 22-14-PLAN.md Task "
                    "3, this check now measures again)",
                    _the_dirty_bar_never_overlaps_the_tab_bar_sidebar_or_the_pages_last_element)

                def _refresh_loop_shows_a_neutral_pill_on_failure_and_clears_on_recovery():
                    # T13 (22-15-PLAN.md Task 2). The defect was that any
                    # non-OK response stopped the loop for the life of
                    # the page with NO visible sign - a frozen page and a
                    # live one looked identical. Only a real browser can
                    # prove the repair: it needs a real fetch to fail, a
                    # real timer to fire the retry, and a real element to
                    # appear and then go away again.
                    #
                    # Playwright's clock is what makes this a fast check
                    # rather than a two-minute one: freshness.js's
                    # cadence is 45s and its first retry rung is another
                    # 45s, so real time would cost 90s of wall clock per
                    # run. install() is called AFTER login so the login
                    # navigation runs on a real clock.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.clock.install()
                        page.goto(base_url + "/health")
                        page.wait_for_load_state("networkidle")

                        badge = "[data-refresh-state-pill]"
                        if page.locator(badge).count() != 0:
                            return False, (
                                "expected no loop-state badge on a healthy page load - the badge "
                                "exists only while the loop is retrying or deliberately idle")

                        # Break the endpoint the loop polls. The route is
                        # added after the initial navigation, so only the
                        # script's own fetch is affected.
                        failing = {"on": True}

                        def _health_route(route):
                            if failing["on"]:
                                route.abort()
                            else:
                                route.continue_()

                        page.route("**/health", _health_route)

                        # Fire one interval tick: the fetch fails, the
                        # ladder schedules a retry and the badge appears.
                        page.clock.run_for(46000)
                        page.wait_for_selector(badge + ":not([hidden])", timeout=10000)
                        state = page.evaluate(
                            "() => {"
                            " var el = document.querySelector('[data-refresh-state-pill]');"
                            " var dot = el.querySelector('.dot');"
                            " var cs = getComputedStyle(el);"
                            " return {cls: el.getAttribute('class'),"
                            "         dot: dot ? dot.getAttribute('class') : null,"
                            "         text: el.textContent.trim(),"
                            "         display: cs.display,"
                            "         updating: document.querySelector("
                            "           '[data-refresh-pill]').hidden};}")
                        if "dot--off" not in (state["dot"] or ""):
                            return False, (
                                "the loop-state badge must carry the NEUTRAL .dot--off dot - a "
                                "browser that lost its connection is not a device fault - got %r"
                                % (state["dot"],))
                        for warn_token in ("warn", "error", "danger"):
                            if warn_token in (state["cls"] or "") or warn_token in (state["dot"] or ""):
                                return False, (
                                    "the loop-state badge must carry no warn token at all, got "
                                    "class %r dot %r" % (state["cls"], state["dot"]))
                        if not state["text"]:
                            return False, "expected visible copy in the loop-state badge"
                        if not state["updating"]:
                            return False, (
                                "expected the 'Updating' pill to be hidden while the state badge "
                                "shows - exactly one pill is ever visible")

                        # Recover. The first rung is another 45s; the
                        # next attempt succeeds and the badge clears.
                        failing["on"] = False
                        page.clock.run_for(46000)
                        page.wait_for_function(
                            "() => {"
                            " var el = document.querySelector('[data-refresh-state-pill]');"
                            " return !el || el.hidden === true;}",
                            timeout=10000)

                        # The [hidden]-versus-display collision: the
                        # badge composes .banner__pill, whose own rule
                        # declares display: inline-flex, and an author
                        # display always beats the user-agent
                        # [hidden] { display: none } regardless of source
                        # order. Without style.css's own guard the badge
                        # would still be painted right here.
                        hidden_display = page.evaluate(
                            "() => {"
                            " var el = document.querySelector('[data-refresh-state-pill]');"
                            " return el ? getComputedStyle(el).display : 'absent';}")
                        if hidden_display not in ("none", "absent"):
                            return False, (
                                "a hidden loop-state badge must compute display: none - the "
                                ".banner__pill[hidden] guard is what makes the native hidden "
                                "attribute work on this component, got %r" % (hidden_display,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "when Health's refresh endpoint starts failing the loop does NOT stop: it schedules a "
                    "backed-off retry and shows a visible NEUTRAL .dot--off badge carrying no warn token "
                    "while the 'Updating' pill stands down, and when the endpoint recovers the next "
                    "attempt succeeds and the badge goes away and computes display: none through the "
                    ".banner__pill[hidden] guard (T13, 22-15-PLAN.md Task 2)",
                    _refresh_loop_shows_a_neutral_pill_on_failure_and_clears_on_recovery)

                # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): REMOVED outright —
                # _a_double_fire_of_change_before_the_first_save_resolves_
                # coalesces_to_one_follow_up and its own _hold_posts()
                # helper (27-04-PLAN.md Task 4, T-27-04-C/D, CFG-63) tested
                # that two rapid `change` commits arriving while a fetch
                # was still in flight coalesced into exactly one follow-up
                # POST. That entire subject — an in-flight fetch, a
                # held/released route, a coalesced follow-up request — no
                # longer exists: the restored bar issues no request at all
                # until the user clicks Enregistrer, once, whenever they
                # like, and a native form submission has no "in flight"
                # window for a second commit to race against from this
                # file's own vantage point. There is nothing left to
                # contort this check into that would not be a different
                # check wearing its name, so it is REMOVED rather than
                # retargeted — its subject (fetch coalescing) ceased to
                # exist with the auto-save model, it was not dropped for
                # convenience. `_hold_posts()` had no other caller in this
                # file and is removed with it.

                def _home_paints_nothing_outside_the_viewport_or_its_cards():
                    # B11 (quick task 260913-bjy) — the audit's "no
                    # horizontal scrollbar at 390px" closed on its FOURTH
                    # and last surface. Flights (22-09), Airlines (22-11)
                    # and Health (22-12) were each measured and closed;
                    # Home is the page nobody re-measured after 22-07 put
                    # the recent-flight time on one line, and it had been
                    # scrolling sideways ever since (documentElement
                    # .scrollWidth 411 FR / 408 EN against a 390 client
                    # width, in both themes).
                    #
                    # Written to catch the CLASS on this page rather than
                    # the one selector that happened to cause it: every
                    # element is measured against the viewport, and every
                    # recent-flights descendant against its own row box.
                    #
                    # The second half is not redundant. The cause was a
                    # percentage width cap resolving against a
                    # content-sized `auto` grid track, so it clamped the
                    # box to 60% of its own content at EVERY width, not
                    # just narrow ones. At 1280px the age still painted
                    # outside its card (right edge 1253 against a row
                    # ending at 1191) while staying inside the viewport —
                    # so scrollWidth alone is blind to the desktop half of
                    # the same defect, which is exactly how it survived
                    # nine plans of review.
                    #
                    # Both languages, because French is the wider driver
                    # here ("(il y a 42 j)" against "(42d ago)") and the
                    # seeded age string only grows with wall-clock time —
                    # the day bucket in layout.relative_age_text() has no
                    # ceiling, so this check can only get stronger.
                    probe = (
                        "() => {"
                        "  const vw = window.innerWidth;"
                        "  const escaped = [], spilled = [];"
                        "  document.querySelectorAll('*').forEach(el => {"
                        "    const r = el.getBoundingClientRect();"
                        "    if (r.width > 0 && r.right > vw + 0.5)"
                        "      escaped.push(el.className.toString() || el.tagName);"
                        "  });"
                        "  document.querySelectorAll('.recent-flight').forEach(row => {"
                        "    const rr = row.getBoundingClientRect();"
                        "    row.querySelectorAll('*').forEach(el => {"
                        "      const r = el.getBoundingClientRect();"
                        "      if (r.width > 0 && (r.right > rr.right + 0.5 || r.left < rr.left - 0.5))"
                        "        spilled.push(el.className.toString() || el.tagName);"
                        "    });"
                        "  });"
                        "  return {sw: document.documentElement.scrollWidth,"
                        "          cw: document.documentElement.clientWidth,"
                        "          rows: document.querySelectorAll('.recent-flight').length,"
                        "          escaped: [...new Set(escaped)],"
                        "          spilled: [...new Set(spilled)]};"
                        "}")
                    for width in (390, 1280):
                        for lang in ("en", "fr"):
                            context = browser.new_context(
                                viewport={"width": width, "height": 844})
                            try:
                                page = context.new_page()
                                base_url = harness.base_url()
                                _login(page, base_url)
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + "/")
                                page.locator(".recent-flight").first.wait_for(state="visible")
                                seen = page.evaluate(probe)
                                if page.viewport_size["width"] != width:
                                    return False, (
                                        "expected the measurement to be taken at %dpx" % (width,))
                                if not seen["rows"]:
                                    return False, (
                                        "expected the seeded recent-flight rows to render at "
                                        "%dpx/%s — with none, this check measures nothing"
                                        % (width, lang))
                                if seen["sw"] > width:
                                    return False, (
                                        "Home scrolls sideways at %dpx/%s: documentElement."
                                        "scrollWidth %d against a client width of %d, painted "
                                        "past the right edge by %r (B11)"
                                        % (width, lang, seen["sw"], seen["cw"],
                                           seen["escaped"]))
                                if seen["escaped"]:
                                    return False, (
                                        "expected nothing on Home to paint right of the %dpx "
                                        "viewport in %s, got %r (B11)"
                                        % (width, lang, seen["escaped"]))
                                if seen["spilled"]:
                                    return False, (
                                        "expected every recent-flight row to contain its own "
                                        "content at %dpx/%s, but %r painted outside its row box "
                                        "— the half of this defect no scrollWidth can see (B11)"
                                        % (width, lang, seen["spilled"]))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "Home paints nothing outside the viewport and nothing outside its own "
                    "recent-flight rows, measured in BOTH languages at 390px and at 1280px: "
                    "documentElement.scrollWidth never exceeds the viewport, no element's right "
                    "edge clears it, and no row's content escapes its own box (B11's fourth and "
                    "last surface, quick task 260913-bjy)",
                    _home_paints_nothing_outside_the_viewport_or_its_cards)

                def _recent_flight_callsigns_are_never_starved():
                    # Quick task 260913-dgh. The Home check immediately
                    # above measures every element against the VIEWPORT
                    # and every row descendant against its own ROW box,
                    # and is structurally blind to this defect: the
                    # starved element's own box stays well inside the
                    # row — it is the box itself that collapses, and the
                    # TEXT paints out of it, straight over the time
                    # beside it. Nothing in this file measured a box
                    # against its own content until now.
                    #
                    # Measured before the fix, callsign box against
                    # callsign content: 10.9px for 57.8px at 320px in
                    # French and 18.6px at 320px in English, 50.9px at
                    # 360px in French. 360px is a common Android width
                    # and is measured here for exactly that reason —
                    # a 320px-only check would have called English at
                    # 360px clean and stopped.
                    #
                    # 1280px is measured too, and not as ceremony: the
                    # row is 292.4px there (the desktop sidebar and the
                    # two-column picture row narrow it), the callsign
                    # track had 7.5px of slack, and
                    # layout.relative_age_text()'s day bucket has no
                    # upper bound — so the seeded age only ever grows
                    # and the desktop was a handful of pixels from the
                    # same defect. This check gets stronger with
                    # wall-clock time, never weaker.
                    #
                    # The 768px assertion is the other half, and it is
                    # what stops the fix being "give the time its own
                    # line everywhere": with 686px of row there, the
                    # callsign and the time must still share the first
                    # line. It is deliberately NOT asserted at 1280px,
                    # where the growing age string will legitimately
                    # wrap one day — that is the fix working, not
                    # failing.
                    probe = (
                        "() => {"
                        "  const rows = document.querySelectorAll('.recent-flight');"
                        "  const starved = [];"
                        "  let cells = 0, sameLine = 0, twoLine = 0;"
                        "  rows.forEach(row => {"
                        "    const cs = row.querySelector('.recent-flight__callsign');"
                        "    const tm = row.querySelector('.recent-flight__time');"
                        "    if (!cs) return;"
                        "    cells += 1;"
                        "    const box = cs.getBoundingClientRect().width;"
                        "    const range = document.createRange();"
                        "    range.selectNodeContents(cs);"
                        "    const text = range.getBoundingClientRect().width;"
                        "    if (text > box + 0.5)"
                        "      starved.push(cs.textContent + ': box ' + box.toFixed(2)"
                        "        + 'px for ' + text.toFixed(2) + 'px of content');"
                        "    if (tm) {"
                        # Two items share a flex line when their boxes
                        # overlap VERTICALLY. Equal tops would be the
                        # wrong test, and was measured being wrong here:
                        # the row is baseline-aligned and the time
                        # renders at the smaller label size, so the two
                        # tops differ by 3px on the SAME line. The
                        # overlap test discriminates exactly — measured
                        # false at 320px in both languages and at 360px
                        # in French, true at every other width/language
                        # pair.
                        "      const a = cs.getBoundingClientRect();"
                        "      const b = tm.getBoundingClientRect();"
                        "      if (a.bottom > b.top + 0.5 && b.bottom > a.top + 0.5) sameLine += 1;"
                        "      else twoLine += 1;"
                        "    }"
                        "  });"
                        "  return {rows: rows.length, cells: cells, starved: starved,"
                        "          sameLine: sameLine, twoLine: twoLine,"
                        "          sw: document.documentElement.scrollWidth,"
                        "          cw: document.documentElement.clientWidth};"
                        "}")
                    for width in VIEWPORT_WIDTHS_ALL:
                        for lang in ("fr", "en"):
                            context = browser.new_context(
                                viewport={"width": width, "height": 844})
                            try:
                                page = context.new_page()
                                base_url = harness.base_url()
                                _login(page, base_url)
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + "/")
                                page.locator(".recent-flight").first.wait_for(state="visible")
                                seen = page.evaluate(probe)
                                if page.viewport_size["width"] != width:
                                    return False, (
                                        "expected the measurement to be taken at %dpx" % (width,))
                                if not seen["rows"] or seen["cells"] != seen["rows"]:
                                    return False, (
                                        "expected every seeded recent-flight row to carry a "
                                        "callsign at %dpx/%s, got %d callsigns in %d rows — "
                                        "with a mismatch this check measures nothing"
                                        % (width, lang, seen["cells"], seen["rows"]))
                                if seen["starved"]:
                                    return False, (
                                        "the recent-flight callsign column is STARVED at "
                                        "%dpx/%s — its box is narrower than its own text, so "
                                        "the callsign paints out of it and over the time "
                                        "beside it: %r"
                                        % (width, lang, seen["starved"]))
                                if seen["sw"] > width:
                                    return False, (
                                        "Home scrolls sideways at %dpx/%s (documentElement."
                                        "scrollWidth %d against a client width of %d) — a "
                                        "callsign column that refuses to yield must not buy "
                                        "that by pushing the row past the viewport (B11)"
                                        % (width, lang, seen["sw"], seen["cw"]))
                                if width == 768 and (seen["twoLine"] or not seen["sameLine"]):
                                    return False, (
                                        "expected the callsign and the time to share the first "
                                        "line at 768px/%s, where the row is 686px wide, but %d "
                                        "of %d rows put the time on its own line — the fix must "
                                        "not cost a line where there is room"
                                        % (lang, seen["twoLine"], seen["cells"]))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "no recent-flight callsign is ever starved by the time column - its box is "
                    "never narrower than its own text at 320, 360, 390, 768 or 1280px in EITHER "
                    "language, Home still never scrolls sideways at any of them, and at 768px "
                    "the callsign and the time still share one line (quick task 260913-dgh)",
                    _recent_flight_callsigns_are_never_starved)

                def _health_tables_fit_their_wraps_with_every_disclosure_open():
                    # Quick task 260913-cz6 — the page STATE nobody
                    # measured. Health's battery readings table sits
                    # inside a closed-by-default
                    # `details.readings-disclosure`, so it was invisible
                    # to two separate classes of check at once: every
                    # page-level sweep in this repo measures the page as
                    # first painted (the disclosure shut, the table not
                    # laid out at all), and every overflow assertion
                    # measures `document.documentElement.scrollWidth`,
                    # which stayed EXACTLY 390 open or closed because the
                    # WRAP scrolls, not the document.
                    #
                    # Measured before the fix, at 390px: the readings
                    # `.data-table-wrap` was 308px against a 432px (FR) /
                    # 369px (EN) table — 124px of overflow, its own
                    # horizontal scrollbar, and a completely still page.
                    #
                    # Written for the CLASS, not that one selector: it
                    # opens EVERY <details> on the page and measures
                    # EVERY `.data-table-wrap`, so any table that a
                    # future disclosure hides — or any new column on an
                    # existing one — is covered without editing this
                    # check. The wrap is the right boundary to measure
                    # because `overflow-x: auto` there is designed as a
                    # safety net for extreme widths, not as the normal
                    # state of a two-column table on a phone.
                    #
                    # Both languages, because French is the wider driver
                    # ("(il y a 44 j)" against "(44d ago)") and the
                    # seeded age string only grows with wall-clock time —
                    # layout.relative_age_text()'s day bucket has no
                    # ceiling, so this check can only get stronger.
                    probe = (
                        "() => {"
                        "  document.querySelectorAll('details').forEach(d => { d.open = true; });"
                        "  const over = [];"
                        "  const wraps = document.querySelectorAll('.data-table-wrap');"
                        "  let rows = 0;"
                        "  wraps.forEach(w => {"
                        "    const t = w.querySelector('table');"
                        "    if (t) rows += t.querySelectorAll('tbody tr').length;"
                        "    if (w.scrollWidth > w.clientWidth + 0.5) {"
                        "      const cells = t ? t.querySelectorAll('tbody tr:first-child td') : [];"
                        "      over.push({cls: (t ? t.className : w.className).toString(),"
                        "                 wrap: w.clientWidth, table: Math.round(w.scrollWidth),"
                        "                 cols: [...cells].map("
                        "                   c => Math.round(c.getBoundingClientRect().width))});"
                        "    }"
                        "  });"
                        "  return {wraps: wraps.length, rows: rows, over: over,"
                        "          docSW: document.documentElement.scrollWidth,"
                        "          docCW: document.documentElement.clientWidth};"
                        "}")
                    #
                    # 23-08-PLAN.md Task 3: THE CONTEXT REQUESTS REDUCED
                    # MOTION, and this is a deliberate fix rather than a
                    # tidy-up. 23-02 gave its own generalised sibling
                    # (260913-eab) exactly this treatment and recorded,
                    # as a finding, that THIS check has the identical
                    # exposure and was left alone only because that
                    # plan's scope named one check and its acceptance
                    # criterion pinned an occurrence count.
                    #
                    # The exposure: this check sets `details.open = true`
                    # and measures in the SAME task, which is sound only
                    # while nothing animates. Health carries four
                    # disclosures. A box measured mid-transition is
                    # NARROWER than its final box, so this would begin
                    # failing intermittently on geometry that is in fact
                    # correct — and it would be harder to diagnose than
                    # its sibling's version of the same fault, because
                    # the sibling is green.
                    #
                    # STATED PLAINLY: 23-08's own animations cannot reach
                    # this check today. Every one of them is scoped to a
                    # Flights-only selector (.flight-detail-row__reveal,
                    # .row-toggle__glyph, .history-card__summary) and
                    # /health renders none of them. This is therefore
                    # prophylaxis, taken now because the cost is one
                    # argument and because 23-10 owns the rest of D3's
                    # motion and will animate more. An intermittently red
                    # check is worse than no check: it teaches people to
                    # ignore it.
                    #
                    # It weakens nothing. Reduced motion makes the final
                    # state the IMMEDIATE state through the app's own
                    # global override; the widths this check measures are
                    # not a function of motion, so the same geometry is
                    # asserted, just deterministically. It takes this
                    # file's count of reduce-requesting contexts from 2
                    # to 3 — written without the literal on purpose, so a
                    # grep for the literal keeps counting contexts rather
                    # than prose about them (23-01's own lesson).
                    width = 390
                    for lang in ("en", "fr"):
                        context = browser.new_context(
                            viewport={"width": width, "height": 844},
                            reduced_motion="reduce")
                        try:
                            page = context.new_page()
                            base_url = harness.base_url()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/health")
                            page.locator("details.readings-disclosure").first.wait_for(
                                state="attached")
                            seen = page.evaluate(probe)
                            if page.viewport_size["width"] != width:
                                return False, (
                                    "expected the measurement to be taken at %dpx" % (width,))
                            # Both guards exist so this check cannot pass
                            # by measuring an empty page: the seeded
                            # fixture renders the readings table, and a
                            # render that stops emitting it must fail
                            # here rather than quietly measure nothing.
                            if not seen["wraps"]:
                                return False, (
                                    "expected at least one .data-table-wrap on Health at %dpx/%s "
                                    "with every disclosure open — with none, this check measures "
                                    "nothing" % (width, lang))
                            if not seen["rows"]:
                                return False, (
                                    "expected the seeded tables to render body rows at %dpx/%s — "
                                    "with none, this check measures nothing" % (width, lang))
                            if seen["over"]:
                                return False, (
                                    "a table inside a disclosure overflows its own wrap at "
                                    "%dpx/%s, giving it a horizontal scrollbar the page itself "
                                    "never shows (documentElement.scrollWidth %d against a client "
                                    "width of %d): %r — each entry is the table's class, its "
                                    "wrap's clientWidth, the table's scrollWidth and the first "
                                    "row's column widths (B12's cause, quick task 260913-cz6)"
                                    % (width, lang, seen["docSW"], seen["docCW"], seen["over"]))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "Health's tables each fit inside their own .data-table-wrap at 390px in BOTH "
                    "languages with EVERY <details> on the page forced open — the readings table "
                    "is reachable only through a closed-by-default disclosure, and its wrap "
                    "scrolls while documentElement.scrollWidth never moves, so no page-level "
                    "assertion can see it (B12's cause on its third table, quick task 260913-cz6)",
                    _health_tables_fit_their_wraps_with_every_disclosure_open)

                def _every_disclosure_on_every_page_opens_without_overflow():
                    # Quick task 260913-eab. The general form of the check
                    # immediately above, and the reason it exists: a
                    # COLLAPSED <details> has its contents not laid out at
                    # all — no width, no position, nothing to measure — so
                    # every sweep in this repo (including the 24-
                    # combination visual pass) measured pages in their
                    # DEFAULT state, and everything asleep inside a
                    # disclosure was invisible to measurement BY
                    # CONSTRUCTION. One disclosure was pinned before this
                    # check: Health's readings table, by name, by the
                    # check above. This one opens EVERY <details> on EVERY
                    # page, so it covers the disclosures that exist today
                    # AND any added later without editing this file —
                    # that generality is the whole point of it.
                    #
                    # Surveyed on this branch, at 390px, in French, with
                    # every disclosure forced open (counts re-derived by
                    # running, never carried from a brief):
                    #
                    #   page       route       <details>  kinds
                    #   Accueil    /            1        nav
                    #   Affichage  /display     3        nav + 2 "how it works"
                    #   Vols       /flights    16        nav + 15 row cards
                    #   Compagnies /airlines    1        nav
                    #   État       /health      4        nav + readings + 2 cards
                    #   Appareil   /device      1        nav
                    #   Connexion  /login       0        (no nav is rendered)
                    #
                    # 26 in total, not the ~83 an earlier task reported:
                    # /preview and /settings are 303 redirects (to /flights
                    # and /display), so the "panel-preview page" in that
                    # figure is /flights counted a second time. The raw
                    # number flatters the coverage either way — 15 of
                    # Vols' 16 are one component repeated per row, so the
                    # distinct KINDS number five.
                    #
                    # 29-03-PLAN.md (CFG-83): Vols' row-card count was 36
                    # (one per seed_state_dir() flight, rendered without a
                    # cap) before Vols was paginated to
                    # history_page.FLIGHTS_PAGE_SIZE by default. It is
                    # FLIGHTS_PAGE_SIZE now, not the fixture's own 36 —
                    # the total below is derived from that constant for
                    # the same reason.
                    #
                    # Two assertions, because one of them cannot see the
                    # defect that motivated this:
                    #   1. documentElement.scrollWidth never exceeds the
                    #      viewport, and nothing paints right of it.
                    #   2. No element whose computed overflow-x is auto or
                    #      scroll has content wider than its own box. This
                    #      is the readings-table class: the WRAP scrolls
                    #      while the page does not, so scrollWidth stayed
                    #      exactly 390 with the disclosure both closed AND
                    #      open. Restricted to auto/scroll deliberately —
                    #      overflow: hidden is excluded because
                    #      text-overflow: ellipsis makes scrollWidth >
                    #      clientWidth BY DESIGN, and flagging it would be
                    #      noise, not a defect.
                    #
                    # Anti-rot, the reason a selector change cannot make
                    # this pass by measuring nothing: each page asserts a
                    # minimum disclosure count (its surveyed count above),
                    # and asserts at least one was CLOSED before being
                    # forced — without that second half this degenerates
                    # into an ordinary default-state page sweep and stops
                    # adding anything. All 26 are closed by default today.
                    # /flights' minimum is deliberately coupled to
                    # history_page.FLIGHTS_PAGE_SIZE (no longer to
                    # seed_state_dir()'s 36 runway events, since 29-03
                    # capped the default render below the fixture's own
                    # size): if that constant or the coupling changes,
                    # this must be re-derived here on purpose, not left
                    # to slide.
                    #
                    # 360px is measured alongside the brief's 390/1280
                    # because 360 is the minimum supported viewport
                    # (developer decision 2026-09-13, recorded in
                    # .claude/skills/sketch-findings-skypane/SKILL.md) and
                    # both fixes of that day were driven by 360px
                    # failures a phone-sized assumption had missed. It
                    # costs ~3s of the check's ~10s and was measured
                    # clean before being added, never assumed.
                    #
                    # Known limit, stated rather than papered over: images
                    # marked loading="lazy" below the fold are not loaded
                    # when this measures, so a future overflow caused by
                    # one is invisible here. This is not a consequence of
                    # the cheap readiness wait — a networkidle wait leaves
                    # the identical images pending, verified by measuring
                    # both ways — it is what lazy loading means. Every
                    # image inside a disclosure today is loaded when this
                    # runs.
                    #
                    # Measuring synchronously in the same evaluate() as
                    # the forced open is sound here: getBoundingClientRect
                    # forces layout, and no script in companion/static
                    # listens for `toggle` or queries `details` at all
                    # (freshness.js's own listener was removed by D-02),
                    # so there is no JS-driven content to wait for.
                    #
                    # Sound TODAY, and the context below is what keeps it
                    # sound tomorrow. This sweep sets `details.open =
                    # true` and measures in the SAME task, which is
                    # correct only while nothing animates. Phase 23
                    # animates disclosures on purpose (23-08's Flights
                    # detail row and its chevron, 23-10's remainder), and
                    # a box measured mid-transition is NARROWER than its
                    # final box — so this check would begin failing on
                    # geometry that is in fact correct, intermittently,
                    # on the slowest file in the suite. An intermittently
                    # red check is worse than no check: it teaches people
                    # to ignore it, and this one was built because a real
                    # phone found a defect sixteen plans and 22 automated
                    # checks had missed.
                    #
                    # So the context below REQUESTS REDUCED MOTION, and
                    # that is the whole fix. It makes the final state the
                    # IMMEDIATE state through the app's OWN global
                    # override (companion/static/style.css's
                    # `prefers-reduced-motion: reduce` block, which
                    # drives every transition and animation to 0.01ms) —
                    # so a measurement taken straight after the state
                    # change is final geometry by construction rather
                    # than by luck. It has a second virtue: it exercises
                    # that override on every route, in both languages, at
                    # all three widths, for free.
                    #
                    # Deliberately NOT a timeout, a sleep or an
                    # event listener. A timing wait across 26 disclosures
                    # x 6 routes x 2 languages x 3 widths is a flakiness
                    # generator and real wall clock on a file already at
                    # ~50s; and listening for the event a <details> fires
                    # when it opens is the same family of mechanism the
                    # paragraph above already rules out.
                    probe = (
                        "() => {"
                        "  const all = [...document.querySelectorAll('details')];"
                        "  const closedBefore = all.filter(d => !d.open).length;"
                        "  all.forEach(d => { d.open = true; });"
                        "  const vw = window.innerWidth;"
                        "  const escaped = [], scrolled = [];"
                        "  document.querySelectorAll('*').forEach(el => {"
                        "    const r = el.getBoundingClientRect();"
                        "    if (r.width > 0 && r.right > vw + 0.5)"
                        "      escaped.push(el.className.toString() || el.tagName);"
                        "    const ox = getComputedStyle(el).overflowX;"
                        "    if ((ox === 'auto' || ox === 'scroll')"
                        "        && el.scrollWidth > el.clientWidth + 0.5) {"
                        "      const kid = el.firstElementChild;"
                        "      scrolled.push({box: el.className.toString() || el.tagName,"
                        "                     boxWidth: el.clientWidth,"
                        "                     content: Math.round(el.scrollWidth),"
                        "                     firstChild: kid ? (kid.className.toString()"
                        "                                        || kid.tagName) : null});"
                        "    }"
                        "  });"
                        "  return {n: all.length, closedBefore: closedBefore,"
                        "          sw: document.documentElement.scrollWidth,"
                        "          cw: document.documentElement.clientWidth,"
                        "          escaped: [...new Set(escaped)].slice(0, 12),"
                        "          scrolled: scrolled};"
                        "}")

                    # (route, minimum <details> the page must render). Every
                    # authenticated page, in nav order. Each route's own
                    # floor is its page-specific disclosure count plus the
                    # ONE shared `<details class="tab-bar__more">` every
                    # authenticated page renders (layout.py) — visible in
                    # the "/" / "/airlines" / "/device" floors of 1, which
                    # have no page-specific disclosure of their own.
                    #
                    # 29-03-PLAN.md (CFG-83): /flights' floor was 37 (one
                    # `<details>` per phone card, against the harness's own
                    # ~36-flight realistic fixture, +1 for the shared
                    # tab-bar disclosure) before Vols was paginated. It is
                    # now `history_page.FLIGHTS_PAGE_SIZE + 1` — the
                    # rendered fixture no longer determines this floor,
                    # the page's own default page size does, and a stale
                    # literal here would silently stop proving anything
                    # the moment that constant next changes.
                    pages = (("/", 1), ("/display", 3),
                             ("/flights", history_page.FLIGHTS_PAGE_SIZE + 1),
                             ("/airlines", 1), ("/health", 4), ("/device", 1))

                    def _assert_clean(seen, where, width):
                        if seen["sw"] > width:
                            return (
                                "%s scrolls sideways with every disclosure open: "
                                "documentElement.scrollWidth %d against a client width of %d, "
                                "painted past the right edge by %r"
                                % (where, seen["sw"], seen["cw"], seen["escaped"]))
                        # The scroll-container diagnostic is reported
                        # BEFORE the viewport one, and not by accident:
                        # when a container overflows, every descendant's
                        # layout rect extends past the viewport too, so
                        # `escaped` fires as well and reports a list of
                        # tag names. Naming the container, its box and
                        # its content width first is what actually points
                        # at the cause — measured on this task's own
                        # mutation, where the generic list read
                        # ['data-table data-table--readings', 'THEAD',
                        # 'TR', 'TH', ...] and told you nothing.
                        if seen["scrolled"]:
                            return (
                                "%s gives a scroll container its own horizontal scrollbar with "
                                "every disclosure open, which the page itself never shows "
                                "(documentElement.scrollWidth %d against a client width of %d): "
                                "%r — each entry is the container's class, its clientWidth, its "
                                "scrollWidth and its first child (the readings-table class, "
                                "quick task 260913-eab)"
                                % (where, seen["sw"], seen["cw"], seen["scrolled"]))
                        if seen["escaped"]:
                            return (
                                "%s lays %r out right of the viewport with every disclosure "
                                "open, while the page itself never scrolls sideways "
                                "(documentElement.scrollWidth %d against a client width of %d) "
                                "and no scroll container reports overflow either — so this is "
                                "content escaping with nothing offering a way to reach it"
                                % (where, seen["escaped"], seen["sw"], seen["cw"]))
                        return ""

                    for width in VIEWPORT_WIDTHS_RESPONSIVE:
                        for lang in ("en", "fr"):
                            context = browser.new_context(
                                viewport={"width": width, "height": 844},
                                reduced_motion="reduce")
                            try:
                                page = context.new_page()
                                base_url = harness.base_url()
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])

                                # The login page is measured FIRST, in this
                                # same context, while it is still the real
                                # unauthenticated page — after _login()
                                # below, /login is a 303 to /. It renders
                                # no nav and so carries no <details> at
                                # all: its own "this measured something"
                                # guard is the password field, not a
                                # disclosure count, which is why it is not
                                # in `pages` above. Asserting a non-zero
                                # count here would assert a falsehood.
                                page.goto(base_url + "/login")
                                page.locator("#password").wait_for(state="visible")
                                seen = page.evaluate(probe)
                                if page.viewport_size["width"] != width:
                                    return False, (
                                        "expected the measurement to be taken at %dpx" % (width,))
                                bad = _assert_clean(
                                    seen, "/login at %dpx/%s" % (width, lang), width)
                                if bad:
                                    return False, bad

                                _login(page, base_url)
                                for route, want in pages:
                                    page.goto(base_url + route)
                                    page.locator("main").first.wait_for(state="visible")
                                    seen = page.evaluate(probe)
                                    where = "%s at %dpx/%s" % (route, width, lang)
                                    if seen["n"] < want:
                                        return False, (
                                            "expected at least %d <details> on %s, found %d — "
                                            "with fewer, this check measures a state that is no "
                                            "longer there, so it must fail rather than pass on an "
                                            "empty selector (quick task 260913-eab)"
                                            % (want, where, seen["n"]))
                                    if not seen["closedBefore"]:
                                        return False, (
                                            "expected at least one of %s's %d <details> to be "
                                            "CLOSED before being forced open on %s — with none, "
                                            "this check measures the same state every other sweep "
                                            "in this file already measures, and adds nothing"
                                            % (route, seen["n"], where))
                                    bad = _assert_clean(seen, where, width)
                                    if bad:
                                        return False, bad
                            finally:
                                context.close()
                    return True, ""
                check(
                    "EVERY <details> on EVERY page opens without overflowing anything — all six "
                    "authenticated pages plus the login page, at 360px, 390px and 1280px, in BOTH "
                    "languages, with every disclosure on the page forced open: documentElement."
                    "scrollWidth never exceeds the viewport, nothing paints right of it, and no "
                    "scroll container's content is wider than its own box (the readings-table "
                    "class, which no page-level assertion can see). Each page asserts a minimum "
                    "disclosure count and that at least one was closed beforehand, so a selector "
                    "change makes this fail rather than silently measure nothing (quick task "
                    "260913-eab)",
                    _every_disclosure_on_every_page_opens_without_overflow)

                # --- 23-04-PLAN.md Task 2 (D10/CFG-33): the two ways a
                # cross-document view transition fails silently ---

                def _view_transition_names_are_unique_on_every_route():
                    # WHY THIS IS COUNTED IN A BROWSER AND FROM COMPUTED
                    # VALUES. A stylesheet scan can prove that a name is
                    # DECLARED once; it cannot prove that its selector
                    # MATCHES once. companion/layout.py puts two
                    # navigation landmarks into every authenticated
                    # document at the same time — the sidebar's vertical
                    # one and the bottom tab bar — and the 960px media
                    # query decides only which is VISIBLE, never how many
                    # exist. (23-RESEARCH.md and 23-04-PLAN.md both say
                    # three, counting the preferences panel's copy; 22-14
                    # Task 2 REMOVED that one rather than emptying it, so
                    # the count is two today and would be three again the
                    # moment a panel-level landmark returns. Measured
                    # here, not carried from the brief.) A name hung on a
                    # class those share — or on the bare `nav` element,
                    # the "simplification" a later reader is most likely
                    # to reach for — is declared exactly once in
                    # style.css, passes every source scan in this
                    # repository, and resolves to two elements in the
                    # DOM, at which point the browser drops the entire
                    # transition with no error, no console warning and no
                    # visual difference from a browser that never
                    # supported it. That is the defect this check exists
                    # for, and only a real document can see it.
                    #
                    # Three anti-vacuity guards, because "no name appears
                    # twice" is trivially satisfied by a page that
                    # declares no names at all — the exact shape of
                    # vacuous check 23-03 caught in its own work:
                    #   1. the set of names the SERVED stylesheet
                    #      declares must equal VIEW_TRANSITION_NAMES's
                    #      keys, so dropping or renaming a declaration
                    #      fails here instead of quietly emptying the
                    #      measurement;
                    #   2. every name must resolve to EXACTLY one element
                    #      on each route its entry lists — zero is a
                    #      failure, not a pass;
                    #   3. and to zero elements on the routes it does
                    #      not, so widening a selector is a deliberate
                    #      edit here rather than a silent one.
                    probe = (
                        "() => {"
                        "  const declared = [];"
                        "  const walk = (rules) => {"
                        "    for (const r of rules) {"
                        "      if (r.style && r.style.viewTransitionName)"
                        "        declared.push(r.style.viewTransitionName);"
                        "      if (r.cssRules) walk(r.cssRules);"
                        "    }"
                        "  };"
                        "  for (const sheet of document.styleSheets) {"
                        "    try { walk(sheet.cssRules); } catch (e) {}"
                        "  }"
                        "  const counts = {}, where = {};"
                        "  const all = document.querySelectorAll('*');"
                        "  all.forEach(el => {"
                        "    const v = getComputedStyle(el).viewTransitionName;"
                        "    if (!v || v === 'none') return;"
                        "    counts[v] = (counts[v] || 0) + 1;"
                        "    (where[v] = where[v] || []).push("
                        "      el.tagName.toLowerCase() + '.' + (el.className.toString() || '-'));"
                        "  });"
                        "  return {declared: declared, counts: counts, where: where,"
                        "          elements: all.length};"
                        "}")
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        for route in VIEW_TRANSITION_ROUTES:
                            page.goto(base_url + route)
                            page.locator("main").first.wait_for(state="visible")
                            seen = page.evaluate(probe)
                            if seen["elements"] < 20:
                                return False, (
                                    "expected a rendered document on %s, found %d elements — "
                                    "with fewer, this check measures nothing"
                                    % (route, seen["elements"]))
                            declared = sorted(set(seen["declared"]))
                            if declared != sorted(VIEW_TRANSITION_NAMES):
                                return False, (
                                    "the stylesheet served to %s declares the view-transition "
                                    "names %r, but this file pins %r (VIEW_TRANSITION_NAMES) — a "
                                    "name added, renamed or dropped in companion/static/style.css "
                                    "must be a deliberate edit here too, because every assertion "
                                    "below is empty for a name nobody declares"
                                    % (route, declared, sorted(VIEW_TRANSITION_NAMES)))
                            # Duplicates FIRST, and over every computed
                            # name rather than only the declared three:
                            # the browser's own `root` name on the
                            # document element counts here too, so a plan
                            # that ever declares `root` collides with the
                            # UA rule and is caught by the same line.
                            for name, count in sorted(seen["counts"].items()):
                                if count > 1:
                                    return False, (
                                        "the view-transition name %r resolves to %d elements on "
                                        "%s (%r) — names must be unique per rendered document or "
                                        "the browser drops the transition silently; if this is a "
                                        "navigation selector, note that more than one navigation "
                                        "landmark is in the DOM of every authenticated page at "
                                        "once, hidden from each other only by a media query"
                                        % (name, count, route, seen["where"][name]))
                            for name, routes in sorted(VIEW_TRANSITION_NAMES.items()):
                                got = seen["counts"].get(name, 0)
                                if route in routes and got != 1:
                                    return False, (
                                        "expected exactly one element carrying the view-transition "
                                        "name %r on %s, found %d — its selector matches nothing "
                                        "there any more, so the transition it names is gone and "
                                        "every uniqueness assertion about it is vacuous"
                                        % (name, route, got))
                                if route not in routes and got:
                                    return False, (
                                        "the view-transition name %r now resolves on %s, which "
                                        "VIEW_TRANSITION_NAMES does not list for it — widening a "
                                        "named selector is a deliberate edit, not a side effect"
                                        % (name, route))
                    finally:
                        context.close()
                    return True, ""
                check(
                    "every view-transition name the served stylesheet declares resolves to AT MOST "
                    "one element on each of the six authenticated routes, counted from the "
                    "COMPUTED value on every element of the real document — the sidebar and the "
                    "page title on all six, Home's frame picture on Home only, and the declared "
                    "set itself pinned so a dropped declaration fails rather than emptying the "
                    "measurement. A name matching twice (two navigation landmarks share every "
                    "authenticated DOM, and a bare `nav` selector reaches both) makes the browser "
                    "drop the whole transition with no error anywhere, and no source scan can see "
                    "it (D10/CFG-33, 23-04-PLAN.md Task 2)",
                    _view_transition_names_are_unique_on_every_route)

                def _the_view_transition_is_off_under_reduced_motion():
                    # ASKING THE CSSOM, NOT WATCHING THE PIXELS. A visual
                    # assertion here would be a timing test on the
                    # slowest file in the suite, and an intermittently
                    # red check teaches people to ignore it. The
                    # condition guarding the at-rule is deterministic and
                    # is precisely the property that gets got wrong.
                    #
                    # AND NOT matchMedia() ON ITS OWN, which would be the
                    # vacuous version of this check: `matchMedia(
                    # '(prefers-reduced-motion: no-preference)').matches`
                    # is false in a reduce context no matter what this
                    # app's stylesheet says, so it would pass with the
                    # at-rule sitting unwrapped at the top level — the
                    # whole defect. The condition evaluated below is read
                    # OFF THE AT-RULE'S OWN PARENT RULE, so the check
                    # fails unless the at-rule is genuinely nested inside
                    # a media rule whose condition is false under reduced
                    # motion and true otherwise. A wrapper around some
                    # other rule does not satisfy it, an inverted
                    # `reduce` wrapper does not satisfy it, and
                    # `navigation: none` does not satisfy it either.
                    probe = (
                        "() => {"
                        "  const found = [];"
                        "  const walk = (rules, parent) => {"
                        "    for (const r of rules) {"
                        "      if (r.constructor.name === 'CSSViewTransitionRule') {"
                        "        const cond = parent && parent.conditionText"
                        "          ? parent.conditionText : null;"
                        "        found.push({nav: r.navigation, text: r.cssText,"
                        "                    parent: parent ? parent.constructor.name : null,"
                        "                    cond: cond,"
                        "                    matches: cond === null"
                        "                      ? null : matchMedia(cond).matches});"
                        "      }"
                        "      if (r.cssRules) walk(r.cssRules, r);"
                        "    }"
                        "  };"
                        "  for (const sheet of document.styleSheets) {"
                        "    try { walk(sheet.cssRules, null); } catch (e) {}"
                        "  }"
                        "  return found;"
                        "}")
                    # Both context modes, because the two halves of the
                    # contract are different statements: under reduce the
                    # transition must not be set up at all, and under
                    # no-preference it must be — a wrapper that never
                    # matches would satisfy the first half alone and ship
                    # a feature nobody ever sees.
                    for reduced, want_match in ((True, False), (False, True)):
                        extra = {"reduced_motion": "reduce"} if reduced else {}
                        context = browser.new_context(**extra)
                        try:
                            page = context.new_page()
                            base_url = harness.base_url()
                            _login(page, base_url)
                            page.goto(base_url + "/")
                            page.locator("main").first.wait_for(state="visible")
                            found = page.evaluate(probe)
                            where = ("a reduced_motion='reduce' context" if reduced
                                     else "a default (no-preference) context")
                            if len(found) != 1:
                                return False, (
                                    "expected exactly one view-transition at-rule in the CSSOM of "
                                    "the stylesheet served to %s, found %d (%r) — zero means the "
                                    "feature is gone, more than one means two rules disagree about "
                                    "whether navigations animate" % (where, len(found), found))
                            rule = found[0]
                            if rule["nav"] != "auto":
                                return False, (
                                    "the view-transition at-rule declares navigation %r in %s — "
                                    "only 'auto' actually animates a navigation"
                                    % (rule["nav"], where))
                            if rule["parent"] != "CSSMediaRule" or not rule["cond"]:
                                return False, (
                                    "the view-transition at-rule sits at the top level of the "
                                    "stylesheet in %s (parent rule %r) rather than inside a media "
                                    "rule — so it is LIVE UNDER REDUCED MOTION: style.css's global "
                                    "`*, *::before, *::after` override matches ELEMENTS and never "
                                    "reaches the ::view-transition pseudo-element tree, which is "
                                    "why this wrapper is the opt-out and not a duplicate of it"
                                    % (where, rule["parent"]))
                            if "prefers-reduced-motion" not in rule["cond"]:
                                return False, (
                                    "the view-transition at-rule is nested in `@media %s` in %s, "
                                    "which says nothing about motion preference — the wrapper "
                                    "exists to prevent the transition being SET UP for a visitor "
                                    "who asked for less motion" % (rule["cond"], where))
                            if rule["matches"] is not want_match:
                                return False, (
                                    "the media condition guarding the view-transition at-rule "
                                    "(`%s`) evaluates to %r in %s, expected %r — under reduced "
                                    "motion the transition must never be set up, and under "
                                    "no-preference it must be, or the feature is wrapped into "
                                    "something nobody ever sees"
                                    % (rule["cond"], rule["matches"], where, want_match))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the cross-document view transition is genuinely OPT-OUT: its at-rule is the "
                    "only one in the CSSOM, declares navigation: auto, and is nested inside a "
                    "media rule whose own conditionText — read off the at-rule's parent, never "
                    "from a bare matchMedia() call, which would pass with the at-rule unwrapped — "
                    "evaluates FALSE in a reduced_motion='reduce' context and TRUE in a default "
                    "one, so a visitor who asked for less motion never has the transition set up "
                    "at all rather than having one set up and run fast (D3+D10/CFG-33, "
                    "23-04-PLAN.md Task 2)",
                    _the_view_transition_is_off_under_reduced_motion)

                # --- 23-05-PLAN.md Task 3 (D14/CFG-34): the ticker,
                # proven in a browser. The claim is "the user sees it
                # change, and a background tab costs nothing" — so every
                # assertion below reads element TEXT twice with a real
                # wait between the reads, never a timer internal. A check
                # that asserted "an interval exists" would pass on a
                # script that ticks a detached node.

                TICK_SETTLE_MS = 2200
                FRESHNESS_AGE = ".page-header__freshness time[data-relative]"

                def _the_relative_age_ticks_in_a_real_tab():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/health")
                        page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
                        first = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
                        # The server-rendered floor: the element already
                        # reads something correct before any script runs.
                        if not first or not first.strip():
                            return False, (
                                "expected the freshness age to be rendered by the SERVER before "
                                "anything ticks — the no-JS floor is this element's own text, "
                                "got %r" % (first,))
                        if "#" in first:
                            return False, (
                                "expected the rendered age to carry no quantity placeholder — "
                                "the wordings are filled server-side and by the script, never "
                                "shown raw, got %r" % (first,))
                        page.wait_for_timeout(TICK_SETTLE_MS)
                        second = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
                        if first == second:
                            return False, (
                                "expected the freshness age to ADVANCE within %dms in a visible "
                                "tab, read %r then %r — a page that says 'Updated 14:32' is "
                                "telling the truth about a moment and saying nothing about now "
                                "(D14/D22)" % (TICK_SETTLE_MS, first, second))
                        if "#" in second:
                            return False, (
                                "the ticked text carries a raw quantity placeholder: %r" % (second,))
                        # 23-06-PLAN.md: the other half of the same
                        # contract the no-JS check below states. The
                        # server renders a CLOCK here; with scripts on
                        # the ticker must have replaced it with a live
                        # age, so the settled text must NOT still be the
                        # clock the element's own datetime resolves to.
                        # The FIRST read is deliberately not pinned to
                        # the clock: the ticker's first repaint lands one
                        # second after load and this harness cannot
                        # promise to read faster than that.
                        instant = page.eval_on_selector(
                            FRESHNESS_AGE, "el => el.getAttribute('datetime')")
                        parsed = layout.parse_iso(instant or "")
                        if parsed is None:
                            return False, (
                                "expected a machine-readable datetime for the ticker to read, "
                                "got %r" % (instant,))
                        clock = layout.local_clock_text(parsed, now_parsed=parsed)
                        if second == clock:
                            return False, (
                                "expected the ticker to have replaced the server's clock %r with "
                                "a live age within %dms — the clock is the no-JS floor, the age "
                                "is the enhancement over it (D14/D22)" % (clock, TICK_SETTLE_MS))
                        # It rewrote ONE element's text and nothing else:
                        # the prefix and the pill beside it are untouched.
                        wrapper = page.eval_on_selector(
                            ".page-header__freshness", "el => el.textContent")
                        if "Updated" not in wrapper:
                            return False, (
                                "expected the freshness line's own prefix to survive the tick — "
                                "the ticker writes textContent on the <time> element and must "
                                "never rewrite a sibling, got %r" % (wrapper,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the Health freshness line's <time data-relative> text ADVANCES within ~2s in "
                    "a real visible tab, starting from text the server already rendered, ending "
                    "on something that is no longer the server's own clock (the enhancement "
                    "really did take over), carrying no raw quantity placeholder, and leaving the "
                    "prefix and pill beside it untouched (D14/CFG-34, 23-05-PLAN.md Task 3; the "
                    "clock-to-age half added by 23-06-PLAN.md)",
                    _the_relative_age_ticks_in_a_real_tab)

                def _a_hidden_tab_does_no_work_and_catches_up_on_return():
                    # WHICH MECHANISM, AND WHY THIS ONE. Two real ways to
                    # hide a page were tried in this harness first and
                    # neither works here, which is recorded rather than
                    # worked around silently:
                    #   - a second page in the same context taking focus
                    #     (page2.bring_to_front()) leaves the first page's
                    #     document.visibilityState at "visible" in
                    #     headless Chromium;
                    #   - CDP's Emulation.setPageVisibilityOverride is not
                    #     present in this Chromium at all ("wasn't
                    #     found").
                    # So the page's own visibility state is overridden
                    # in-page and a real `visibilitychange` Event is
                    # dispatched on document — which is what the browser
                    # itself dispatches. What that simulates is the
                    # BROWSER'S REPORT; what it exercises is the shipped
                    # script's own listener and its own document.hidden
                    # reads, unmodified, which is the contract under
                    # test. It is weaker than a genuinely backgrounded
                    # tab and stronger than asserting a listener exists:
                    # a script with no listener, a script that ignores
                    # document.hidden, and a script that never re-arms on
                    # return all fail it.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/health")
                        page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
                        read = "() => document.querySelector(%r).textContent" % FRESHNESS_AGE
                        # CONTROL FIRST. Without this the check passes on
                        # a page whose element never changes for any
                        # reason at all — the vacuity shape 23-03 caught
                        # in its own work.
                        control_before = page.evaluate(read)
                        page.wait_for_timeout(TICK_SETTLE_MS)
                        control_after = page.evaluate(read)
                        if control_before == control_after:
                            return False, (
                                "control: the age did not move in a VISIBLE tab (%r twice), so "
                                "the hidden-tab assertion below would measure nothing"
                                % (control_before,))
                        page.evaluate(
                            "() => {"
                            "  Object.defineProperty(document, 'hidden',"
                            "    {configurable: true, get: () => true});"
                            "  Object.defineProperty(document, 'visibilityState',"
                            "    {configurable: true, get: () => 'hidden'});"
                            "  document.dispatchEvent(new Event('visibilitychange'));"
                            "}")
                        hidden_before = page.evaluate(read)
                        page.wait_for_timeout(TICK_SETTLE_MS)
                        hidden_after = page.evaluate(read)
                        if hidden_before != hidden_after:
                            return False, (
                                "expected the age NOT to change while the page reports itself "
                                "hidden, read %r then %r over %dms — a once-a-second timer in "
                                "every background tab forever is the one real cost this file "
                                "carries (T-23-14)"
                                % (hidden_before, hidden_after, TICK_SETTLE_MS))
                        # Back in view: the repaint happens IMMEDIATELY,
                        # well inside one tick. A tab returning after a
                        # long hidden stretch showing a stale age is the
                        # same defect this file exists to remove, just
                        # later on.
                        page.evaluate(
                            "() => {"
                            "  Object.defineProperty(document, 'hidden',"
                            "    {configurable: true, get: () => false});"
                            "  Object.defineProperty(document, 'visibilityState',"
                            "    {configurable: true, get: () => 'visible'});"
                            "  document.dispatchEvent(new Event('visibilitychange'));"
                            "}")
                        returned = page.evaluate(read)
                        if returned == hidden_after:
                            return False, (
                                "expected the age to be repainted IMMEDIATELY on becoming "
                                "visible again rather than after waiting out an interval, still "
                                "read %r" % (returned,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a page reporting itself hidden runs no ticker work at all — its age is "
                    "byte-identical across ~2s, against a control proving the same age DOES move "
                    "while visible — and on becoming visible again it is repainted immediately "
                    "rather than after waiting out an interval (T-23-14, 23-05-PLAN.md Task 3; "
                    "the visibility mechanism and its limits are stated in this check's own "
                    "comment)",
                    _a_hidden_tab_does_no_work_and_catches_up_on_return)

                def _the_relative_age_is_server_rendered_and_static_without_scripts():
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        # 25-02-PLAN.md: this used to open the file's
                        # SECOND java_script_enabled=False context by
                        # hand, because it needs the UI-language cookie
                        # set before the first navigation and
                        # `_no_js_page()` had no way to take one. It does
                        # now, so this composes with the one call site
                        # again. The sequence is otherwise unchanged:
                        # same viewport, same cookie, same sign-in, same
                        # landing route.
                        with _no_js_page(
                                browser.new_context, base_url, "/health",
                                viewport=VIEWPORT_MIN_SUPPORTED,
                                cookies=[{
                                    "name": auth.UI_LANG_COOKIE_NAME,
                                    "value": lang, "url": base_url}]) as page:
                            found = page.locator(FRESHNESS_AGE).count()
                            if found != 1:
                                return False, (
                                    "lang=%s: expected exactly one server-rendered <time "
                                    "data-relative> in the freshness line with scripts blocked, "
                                    "found %d" % (lang, found))
                            seen = page.eval_on_selector(
                                FRESHNESS_AGE,
                                "el => [el.textContent, el.getAttribute('datetime')]")
                            first, instant = seen[0], seen[1]
                            # 23-06-PLAN.md (23-05's own finding 2, fixed
                            # here rather than deferred to the wave-9
                            # sweep): this assertion is REVERSED on
                            # purpose. 23-05 required the ladder's zero
                            # bucket here, which is what a page with no
                            # ticker freezes on — "Updated 0s ago", true
                            # at load and false one second later, which
                            # is 19-09/A-20's own defect handed to the
                            # one reader who has nothing to advance it.
                            # The server now renders the CLOCK as this
                            # element's text and the ticker replaces it
                            # with the live age when it runs. The
                            # expected value is derived from the
                            # element's OWN datetime attribute rather
                            # than from a wall clock read in this
                            # process, so the assertion cannot flake
                            # across a minute boundary.
                            parsed = layout.parse_iso(instant or "")
                            if parsed is None:
                                return False, (
                                    "lang=%s: expected a machine-readable datetime on the "
                                    "freshness element for the ticker to read, got %r"
                                    % (lang, instant))
                            expected = layout.local_clock_text(parsed, now_parsed=parsed)
                            if first != expected:
                                return False, (
                                    "lang=%s: expected the scripts-blocked page to read the "
                                    "server's own clock %r — a value that stays true with no "
                                    "script to advance it — got %r" % (lang, expected, first))
                            frozen_zero = layout.relative_age_text(0, lang=lang)
                            if first == frozen_zero:
                                return False, (
                                    "lang=%s: the scripts-blocked page reads the ladder's zero "
                                    "bucket %r, which nothing here can ever advance — that is "
                                    "A-20's frozen zero, not a no-JS floor" % (lang, frozen_zero))
                            if " ago" in first or "il y a" in first:
                                return False, (
                                    "lang=%s: the scripts-blocked page reads a relative age "
                                    "(%r); an age is a claim about NOW and only the ticker can "
                                    "keep it true" % (lang, first))
                            if "#" in first:
                                return False, (
                                    "lang=%s: a raw quantity placeholder reached the page: %r"
                                    % (lang, first))
                            # PRESENCE ALONE IS NOT THE CHECK. An element
                            # that is present AND changing would mean the
                            # enhancement had silently taken over in a
                            # context that is supposed to have none, and
                            # a presence-only assertion would pass on it.
                            page.wait_for_timeout(TICK_SETTLE_MS)
                            second = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
                            if first != second:
                                return False, (
                                    "lang=%s: the age CHANGED on a scripts-blocked page (%r -> "
                                    "%r) — no script can be running there, so something else is "
                                    "rewriting it" % (lang, first, second))
                            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                return False, "expected the measurement at the 360px contract floor"
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, the freshness line still "
                    "renders exactly one <time data-relative> carrying the server's own CLOCK — "
                    "derived from the element's own datetime, never the ladder's zero bucket and "
                    "never any age, because nothing there can advance one — and it does NOT "
                    "change over ~2s, which is what separates an intact no-JS floor from an "
                    "enhancement that quietly took over (CFG-38, 23-05-PLAN.md Task 3; the "
                    "frozen-zero half reversed by 23-06-PLAN.md)",
                    _the_relative_age_is_server_rendered_and_static_without_scripts)

                def _an_expired_countdown_reads_waiting_and_never_a_warning():
                    # No page renders a countdown yet — 23-06's next-wake
                    # line is relative_time_html(countdown=True)'s first
                    # consumer — so the element is seeded into a real
                    # rendered page here rather than waited for. That is
                    # deliberate and it is not a weaker test of THIS
                    # plan's subject: the script re-queries the document
                    # on every tick, so a seeded element goes through the
                    # shipped code path exactly as a server-rendered one
                    # will. The SERVER half (an expired countdown renders
                    # the waiting wording with no JS at all) is pinned in
                    # the companion-app harness instead, where the
                    # renderer can be called directly.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page = context.new_page()
                            _login(page, base_url)
                            page.goto(base_url + "/health")
                            page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
                            page.evaluate(
                                "() => {"
                                "  var el = document.createElement('time');"
                                "  el.setAttribute('id', 'seeded-countdown');"
                                "  el.setAttribute('data-relative', '');"
                                "  el.setAttribute('data-relative-countdown', '');"
                                "  el.setAttribute('datetime',"
                                "    new Date(Date.now() - 120000).toISOString());"
                                "  el.textContent = 'seeded';"
                                "  document.querySelector('main').appendChild(el);"
                                "}")
                            page.wait_for_timeout(TICK_SETTLE_MS)
                            seen = page.eval_on_selector(
                                "#seeded-countdown",
                                "el => [el.textContent, el.getAttribute('class') || '']")
                            text, klass = seen[0], seen[1]
                            expected = page.eval_on_selector(
                                "body",
                                "el => el.getAttribute('data-relative-waiting')")
                            if not expected:
                                return False, (
                                    "lang=%s: the page renders no waiting wording on <body> for "
                                    "the script to read" % lang)
                            if text != expected:
                                return False, (
                                    "lang=%s: expected a countdown whose instant has passed to "
                                    "read the server's own waiting wording %r, got %r — it must "
                                    "not turn itself into an age"
                                    % (lang, expected, text))
                            if " ago" in text or "il y a" in text:
                                return False, (
                                    "lang=%s: an expired countdown became an age: %r"
                                    % (lang, text))
                            if "is-breathing" not in klass.split():
                                return False, (
                                    "lang=%s: expected an expired countdown to breathe, got "
                                    "class=%r" % (lang, klass))
                            for verdict in ("warn", "error", "alert", "danger", "late"):
                                if verdict in klass:
                                    return False, (
                                        "lang=%s: an expired countdown carries NO warn class — "
                                        "a wake that has not happened yet is not a fault (the "
                                        "false alarm X2 removed), got class=%r" % (lang, klass))
                            # And the breathing is motion this app's own
                            # reduced-motion floor already covers: the
                            # class resolves to the one animation the
                            # stylesheet defines.
                            animation = page.eval_on_selector(
                                "#seeded-countdown",
                                "el => getComputedStyle(el).animationName")
                            if animation != "skypane-pulse":
                                return False, (
                                    "lang=%s: expected the breathing class to resolve to the "
                                    "stylesheet's one animation, got %r" % (lang, animation))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a countdown whose instant has already passed reads the server's own "
                    "translated waiting wording in BOTH languages, never an age, gains the "
                    "breathing class and no warn/error/alert class at all, and that class "
                    "resolves to the one animation the stylesheet defines (D14/CFG-34, "
                    "23-05-PLAN.md Task 3)",
                    _an_expired_countdown_reads_waiting_and_never_a_warning)

                # --- 23-06-PLAN.md Task 3 (D1/CFG-35): the three skips,
                # and the number D-12 was written to protect.
                #
                # HOW A REFRESH IS FORCED, once, for every check below.
                # The loop's own cadence is 45 seconds and no test may
                # wait that long, so these checks drive the loop's
                # CATCH-UP path instead: freshness.js re-arms on
                # visibilitychange and refetches immediately when more
                # than one interval has passed since the document was
                # generated. Date.now is shifted forward for the
                # duration of the dispatch and restored on the next
                # statement — doRefresh() is called synchronously inside
                # the listener, so the shift is over before anything
                # else can observe it. What is simulated is the CLOCK;
                # what is exercised is the shipped script's own
                # listener, its own elapsed comparison and its own
                # guards, unmodified.
                #
                # Every request assertion COUNTS REQUESTS rather than
                # reading the DOM. "Zero requests" is the contract D-12
                # protects, and a DOM-based proxy would pass on a page
                # that fetched and then declined to swap — a different
                # and much worse behaviour.

                REFRESH_SETTLE_MS = 1200

                def _force_refresh(page):
                    page.evaluate(
                        "() => {"
                        "  var real = Date.now;"
                        "  Date.now = function () { return real() + 600000; };"
                        "  try {"
                        "    document.dispatchEvent(new Event('visibilitychange'));"
                        "  } finally {"
                        "    Date.now = real;"
                        "  }"
                        "}")

                def _count_document_requests(page, url):
                    """A live counter of fetches of `url` made by the page
                    itself. Returns a zero-argument reader."""
                    seen = []
                    page.on("request", lambda request: (
                        seen.append(request.url)
                        if request.url.split("?")[0] == url else None))
                    return lambda: len(seen)

                def _mark(page, selector, name):
                    """Tag a live node with a JS expando — the only handle
                    that proves NODE IDENTITY across a swap. An attribute
                    would not do: the replacement comes from a second
                    document and would never carry it, so an
                    attribute-based check could not tell "this node
                    survived" from "a node matching the same selector is
                    here"."""
                    page.eval_on_selector(
                        selector, "el => { el.__skypaneProbe = %r; }" % name)

                def _marked(page, selector, name):
                    return page.eval_on_selector(
                        selector, "el => el.__skypaneProbe === %r" % name)

                def _dirty_the_region(page, selector):
                    """Make a live region DIFFER from its freshly-fetched
                    counterpart, so the "this region did not change" skip
                    cannot be what leaves it alone.

                    Without this these checks would be vacuous in the
                    quietest possible way: on a page nothing has changed
                    on, isEqualNode() skips every region anyway, and an
                    assertion that a region survived would pass on a loop
                    with no focus rule and no pending rule at all.
                    """
                    page.eval_on_selector(
                        selector, "el => el.setAttribute('data-probe-dirty', '1')")

                def _a_swap_leaves_the_region_holding_focus_alone():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        region = ".frame-strip"
                        focus_target = ".frame-strip button[type=\"submit\"]"
                        page.eval_on_selector(focus_target, "el => el.focus()")
                        _mark(page, region, "focused-region")
                        _mark(page, focus_target, "focused")
                        _dirty_the_region(page, region)
                        # THE FIRST CONTROL: a refresh that swapped
                        # NOTHING would satisfy "the region survived"
                        # perfectly. The freshness line differs on every
                        # cycle by construction (its pill carries
                        # data-loaded-at, a new instant each time), so it
                        # is the honest witness that a swap happened.
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the focus assertion "
                                "below would prove nothing — the freshness line's own node "
                                "survived a refresh it should not have")
                        if not _marked(page, region, "focused-region"):
                            return False, (
                                "the region holding keyboard focus was REPLACED — a refresh that "
                                "silently moves focus to the top of the document while someone "
                                "is tabbing through a card is A-20's own harm, smaller (D1)")
                        active = page.evaluate(
                            "() => document.activeElement.__skypaneProbe === 'focused'")
                        if not active:
                            return False, (
                                "focus left the element the user was in: document.activeElement "
                                "is no longer that node")
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about FOCUS rather than about that
                        # region: blur, change the region in the same way
                        # again, and it must now be replaced.
                        page.evaluate("() => document.activeElement.blur()")
                        _mark(page, region, "unfocused-region")
                        _dirty_the_region(page, region)
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, region, "unfocused-region"):
                            return False, (
                                "control: the same changed region survived with NOTHING focused "
                                "inside it, so the assertion above was not measuring the focus "
                                "rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Home refresh swaps the regions that changed while leaving the one holding "
                    "keyboard focus untouched — asserted on NODE IDENTITY through a JS expando, "
                    "not on a selector match, because a replaced node matching the same selector "
                    "is exactly the defect — against a control proving another region really was "
                    "swapped in the same cycle (D1/CFG-35, 23-06-PLAN.md Task 3)",
                    _a_swap_leaves_the_region_holding_focus_alone)

                def _a_swap_leaves_a_pending_region_alone():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        # The marker is injected here because plan 23-07
                        # is what sets it in production — the swap rule
                        # lands first, on purpose, so that plan only has
                        # to mark its own control. The element goes
                        # INSIDE the region, not on it, which is the
                        # harder of the two cases the skip handles.
                        region = ".home-status-grid"
                        page.eval_on_selector(
                            region,
                            "el => { var probe = document.createElement('span');"
                            "  probe.setAttribute('data-pending', '');"
                            "  el.appendChild(probe); el.__skypaneProbe = 'pending'; }")
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the pending assertion "
                                "below would prove nothing")
                        if not _marked(page, region, "pending"):
                            return False, (
                                "a region holding an element marked data-pending was replaced — "
                                "that repaints an optimistic control with the server's older "
                                "answer and makes it bounce back under the user's finger "
                                "(T-23-21, the D1-races-D2 rule plan 23-07 depends on)")
                        still_there = page.eval_on_selector_all(
                            region + " [data-pending]", "els => els.length")
                        if still_there != 1:
                            return False, (
                                "expected the pending marker itself to survive the cycle, found "
                                "%d" % (still_there,))
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about the MARKER: drop it, change
                        # the region the same way, and it must now be
                        # replaced. Without this the check passes on a
                        # loop that never swaps that region for any
                        # reason at all.
                        page.eval_on_selector(
                            region,
                            "el => { el.querySelector('[data-pending]').removeAttribute("
                            "  'data-pending');"
                            "  el.__skypaneProbe = 'unmarked'; }")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, region, "unmarked"):
                            return False, (
                                "control: the same changed region survived with the marker "
                                "REMOVED, so the assertion above was not measuring the pending "
                                "rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a region containing a [data-pending] element survives a refresh untouched, by "
                    "node identity, while another region on the same page is swapped in the same "
                    "cycle — the reconciliation rule plan 23-07 sets its marker for, proven before "
                    "it has a marker to set (T-23-21, 23-06-PLAN.md Task 3)",
                    _a_swap_leaves_a_pending_region_alone)

                def _a_dirty_settings_form_stands_the_whole_cycle_down():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")
                        page.wait_for_load_state("networkidle")
                        count = _count_document_requests(page, base_url + "/display")
                        # CONTROL FIRST: with the form clean, the very
                        # same trigger DOES fetch. Without this the
                        # assertion below passes on a page whose loop
                        # never ran for any reason at all.
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        clean_requests = count()
                        if clean_requests < 1:
                            return False, (
                                "control: a clean Display page issued no request at all (%d), so "
                                "the dirty-form assertion below would measure nothing"
                                % (clean_requests,))
                        # 27-04-PLAN.md Task 4 (CFG-63): RETARGETED — a
                        # radio commits (fires change) the instant it is
                        # clicked, which now means the form is clean again
                        # a moment later (auto-save's own optimistic
                        # snapshot advance) — a radio click can no longer
                        # hold this check's own precondition open. The
                        # genuinely uncommitted state this check needs is
                        # a value typed but not yet blurred, read through
                        # window.SkyPaneDirtyState.hasUncommittedEdits() —
                        # the exact predicate freshness.js's own gate now
                        # reads (this plan's own deviation, replacing the
                        # retired bar's liveness+visibility gate).
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.eval_on_selector(quiet_sel, "el => el.focus()")
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.type("03:33")
                        uncommitted = page.evaluate(
                            "() => !!(window.SkyPaneDirtyState "
                            "&& window.SkyPaneDirtyState.hasUncommittedEdits())")
                        if not uncommitted:
                            return False, (
                                "expected the typed-but-uncommitted edit to report unsaved edits "
                                "— this check gates on that same predicate, so a page that never "
                                "reports one would make it vacuous")
                        before = count()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        during_edit = count() - before
                        if during_edit != 0:
                            return False, (
                                "expected ZERO requests while the settings form has unsaved "
                                "edits, counted %d — a page mid-edit should not be fetching and "
                                "diffing itself at all, and a swap landing on a half-edited form "
                                "is B1 with a new cause" % (during_edit,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Display page with a typed-but-uncommitted edit issues ZERO requests when "
                    "the same trigger that fetched on the clean page fires — counted as REQUESTS, "
                    "not inferred from the DOM, because a page that fetched and then declined to "
                    "swap is a different and worse behaviour — against a control proving the clean "
                    "page does fetch (T-23-20/T-23-21, 23-06-PLAN.md Task 3; retargeted from the "
                    "retired save bar's own gate by 27-04-PLAN.md Task 4, CFG-63)",
                    _a_dirty_settings_form_stands_the_whole_cycle_down)

                def _a_hidden_tab_issues_zero_requests_on_all_three_pages():
                    base_url = harness.base_url()
                    for route in ("/", "/display", "/health"):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            page.goto(base_url + route)
                            page.wait_for_load_state("networkidle")
                            count = _count_document_requests(page, base_url + route)
                            # CONTROL: the page really is running a loop.
                            _force_refresh(page)
                            page.wait_for_timeout(REFRESH_SETTLE_MS)
                            if count() < 1:
                                return False, (
                                    "control: %s issued no request when visible (%d), so the "
                                    "hidden-tab assertion below would measure nothing — this "
                                    "page is not running the loop at all"
                                    % (route, count()))
                            # The same limitation 23-05 recorded applies:
                            # neither a second page taking focus nor CDP's
                            # visibility override works in this harness, so
                            # the page's own report is overridden in-page
                            # and a real visibilitychange Event dispatched.
                            # What is simulated is the BROWSER'S REPORT;
                            # what is exercised is the shipped script's own
                            # listener and its own document.hidden reads.
                            page.evaluate(
                                "() => {"
                                "  Object.defineProperty(document, 'hidden',"
                                "    {configurable: true, get: () => true});"
                                "  Object.defineProperty(document, 'visibilityState',"
                                "    {configurable: true, get: () => 'hidden'});"
                                "}")
                            before = count()
                            _force_refresh(page)
                            page.wait_for_timeout(REFRESH_SETTLE_MS)
                            hidden_requests = count() - before
                            if hidden_requests != 0:
                                return False, (
                                    "%s issued %d request(s) while reporting itself hidden — "
                                    "zero from a backgrounded tab is the number D-12 was written "
                                    "to protect, and three pages polling instead of one is only "
                                    "acceptable because of it (T-23-20)"
                                    % (route, hidden_requests))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a tab reporting itself hidden issues ZERO requests on ALL THREE pages that "
                    "now run the loop — counted as requests, each against a control proving the "
                    "same page and the same trigger DO fetch while visible — which is the number "
                    "D-12 was written to protect and the reason three pages polling is acceptable "
                    "at all (T-23-20, 23-06-PLAN.md Task 3)",
                    _a_hidden_tab_issues_zero_requests_on_all_three_pages)

                def _the_picture_fades_only_when_the_picture_changed():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        image = ".preview-frame__image"
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: nothing was swapped, so 'it did not fade' below would "
                                "prove nothing")
                        klass = page.eval_on_selector(
                            image, "el => el.getAttribute('class') || ''")
                        if "is-fading-in" in klass.split():
                            return False, (
                                "the picture faded in on a cycle that brought back the SAME "
                                "picture (class=%r) — a flash every 45 seconds for no "
                                "information is worse than no fade at all" % (klass,))
                        # And now a genuinely different picture: the live
                        # src is changed so the fetched one differs from
                        # it, which is exactly the state a new render
                        # produces.
                        page.eval_on_selector(
                            image, "el => { el.setAttribute('src', el.getAttribute('src')"
                                   " + '?stale=1'); }")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        klass = page.eval_on_selector(
                            image, "el => el.getAttribute('class') || ''")
                        if "is-fading-in" not in klass.split():
                            return False, (
                                "a NEW picture arrived and did not fade in (class=%r) — the fade "
                                "is the only thing that says a render happened" % (klass,))
                        animation = page.eval_on_selector(
                            image, "el => getComputedStyle(el).animationName")
                        if animation != "skypane-fade-in":
                            return False, (
                                "expected the fade class to resolve to the stylesheet's own "
                                "fade-in block, got %r" % (animation,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the frame picture fades in when a NEW render arrives and does NOT animate "
                    "when the same picture is swapped back in — both phases in one check, against "
                    "a control proving a swap happened at all, with the class proven to resolve to "
                    "the stylesheet's own fade-in block (D1+D3, 23-06-PLAN.md Task 3)",
                    _the_picture_fades_only_when_the_picture_changed)

                def _display_still_saves_with_scripts_blocked_at_360px():
                    # THE ONE ASSERTION IN THIS PLAN THAT WOULD CATCH THE
                    # PHASE 22 P0 RECURRING, which is why it lives at
                    # this plan's own commit rather than in the closing
                    # sweep: this plan adds markup to Display's header,
                    # and a wrapper that broke the form= association B1
                    # depends on would make the page unsaveable with
                    # scripts blocked, exactly as B1 did with them on.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")
                            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                return False, "expected the measurement at the 360px contract floor"
                            current = device_config.load_device_config(harness.tmpdir)["theme"]
                            other = next(
                                t for t in device_config.THEME_IDS if t != current)
                            page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % other,
                                "el => el.checked = true")
                            save = page.query_selector(
                                "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                            if save is None:
                                return False, (
                                    "lang=%s: the fallback Save is the ONLY way to save this page "
                                    "with scripts blocked, and it is not rendered" % (lang,))
                            # 28-10-PLAN.md (CFG-77/CFG-78), a direct
                            # consequence of 28-08's own restoration: the
                            # relocated Save button is now inside
                            # .dirty-bar, whose entrance `animation:
                            # skypane-bar-arrive` (style.css) is on the
                            # BASE rule, unconditional on script — it
                            # fires on the very first paint regardless of
                            # scripts being blocked, since CSS animations
                            # are independent of JS. Well past
                            # var(--motion-fast) (180ms): a coordinate
                            # click during that window fails Playwright's
                            # own stability check against a button that
                            # is still translating into place.
                            page.wait_for_timeout(600)
                            with page.expect_navigation():
                                save.click()
                            saved = device_config.load_device_config(harness.tmpdir)["theme"]
                            if saved != other:
                                return False, (
                                    "lang=%s: a Display save did not persist with scripts blocked "
                                    "at 360px — expected theme %r, got %r. This is the P0 Phase "
                                    "22 existed to fix" % (lang, other, saved))
                            # The freshness line this plan added renders
                            # there too, and renders NOTHING that moves.
                            if page.locator(".page-header__freshness").count() != 1:
                                return False, (
                                    "lang=%s: expected exactly one freshness line on a "
                                    "scripts-blocked Display page" % (lang,))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, a Display setting still "
                    "saves through the fallback Save and persists to disk, with the freshness line "
                    "this plan added rendering beside it — the one assertion here that would catch "
                    "the Phase 22 P0 recurring (B1/CFG-38, 23-06-PLAN.md Task 3)",
                    _display_still_saves_with_scripts_blocked_at_360px)

                # --- 23-07-PLAN.md Task 3 (D2/CFG-36): the optimistic
                # switch, proven in a real browser. Three properties no
                # string-comparison harness can see — that the flip
                # lands BEFORE the answer, that it comes back when the
                # answer is bad, and that a refresh arriving mid-flight
                # does not repaint it — plus the scripts-blocked floor
                # for all three switches at 360px in both languages.
                #
                # HOW "BEFORE THE ANSWER" IS MADE A REAL MOMENT. The
                # page's own window.fetch is wrapped in a promise this
                # harness releases by hand, so there is no sleep, no
                # race and no timing assumption anywhere below: between
                # the click and the release the request has genuinely
                # been issued and genuinely has no answer. This is the
                # same discipline the clock override above uses — what
                # is simulated is the TRANSPORT; what is exercised is
                # the shipped script's own ordering, its own attribute
                # writes and its own terminal branches, unmodified.

                SWITCH_SEL = 'form[action="/quick/display"] button[role="switch"]'

                def _hold_fetch(page):
                    """Wrap window.fetch so the next POST hangs until
                    _release_fetch() is called. Returns nothing; the
                    release hook lives on window.

                    POSTs ONLY, and that is load-bearing rather than
                    tidy: freshness.js's refresh loop is a GET through
                    the same window.fetch, and holding it too would stop
                    the very refresh the race check below has to land.
                    Found by that check timing out, not reasoned about
                    in advance."""
                    page.evaluate(
                        "() => {"
                        "  var realFetch = window.fetch;"
                        "  window.__skypaneHeld = null;"
                        "  window.fetch = function (url, opts) {"
                        "    if (!opts || opts.method !== 'POST') {"
                        "      return realFetch(url, opts);"
                        "    }"
                        "    return new Promise(function (resolve, reject) {"
                        "      window.__skypaneHeld = function () {"
                        "        realFetch(url, opts).then(resolve, reject);"
                        "      };"
                        "    });"
                        "  };"
                        "}")

                def _fetch_was_issued(page):
                    return page.evaluate("() => !!window.__skypaneHeld")

                def _release_fetch(page):
                    page.evaluate("() => { window.__skypaneHeld(); }")

                def _switch_state(page, selector=None):
                    return page.eval_on_selector(
                        selector or SWITCH_SEL, "el => el.getAttribute('aria-checked')")

                def _a_switch_flips_before_the_server_answers():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        before = _switch_state(page)
                        if before not in ("true", "false"):
                            return False, (
                                "expected a server-rendered aria-checked on the Screen switch, "
                                "got %r" % (before,))
                        on_disk_before = device_config.load_device_config(
                            harness.tmpdir)["display_enabled"]
                        _hold_fetch(page)
                        page.click(SWITCH_SEL)
                        # THE CONTROL for this check: a request really was
                        # issued. Without it, "the attribute already
                        # changed" would also be satisfied by a script
                        # that flipped the switch and never talked to the
                        # server at all — which is a worse bug than the
                        # one this check is about.
                        if not _fetch_was_issued(page):
                            return False, (
                                "control: no fetch was issued at all, so the assertion below "
                                "would prove nothing about ORDER")
                        during = _switch_state(page)
                        if during == before:
                            return False, (
                                "aria-checked was still %r while the request had no answer — the "
                                "flip is not optimistic, it is waiting for the server, which is "
                                "the whole of what D2 asks for (23-07-PLAN.md Task 3)" % (during,))
                        # The server has NOT been told yet, which is what
                        # makes the line above a statement about order.
                        if device_config.load_device_config(
                                harness.tmpdir)["display_enabled"] is not on_disk_before:
                            return False, (
                                "the stored value changed before the held request was released — "
                                "the hold is not holding and this check is measuring nothing")
                        # In flight: the region is marked, which is the
                        # one thing plan 23-06's swap reads.
                        pending = page.eval_on_selector_all(
                            ".frame-strip [data-pending]", "els => els.length")
                        if pending != 1:
                            return False, (
                                "expected exactly one pending-marked region while the request is "
                                "in flight, found %d — this is the marker 23-06's swap skips and "
                                "the only thing this plan owes that contract" % (pending,))
                        _release_fetch(page)
                        page.wait_for_timeout(600)
                        if _switch_state(page) != during:
                            return False, (
                                "a CONFIRMED flip must stay where it was put, got %r"
                                % _switch_state(page))
                        if page.eval_on_selector_all(
                                ".frame-strip [data-pending]", "els => els.length") != 0:
                            return False, (
                                "the pending marker survived a successful answer — a region whose "
                                "control is settled must go back to being refreshable")
                        if device_config.load_device_config(
                                harness.tmpdir)["display_enabled"] is on_disk_before:
                            return False, "expected the confirmed flip to have persisted to disk"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a switch flips its aria-checked BEFORE the server answers — proven against a "
                    "held request that has genuinely been issued and genuinely has no answer, with "
                    "the stored value still unchanged at that instant — marks exactly one region "
                    "pending while in flight, and on a 204 keeps the flip and clears the marker "
                    "(D2/CFG-36, 23-07-PLAN.md Task 3)",
                    _a_switch_flips_before_the_server_answers)

                def _a_switch_rolls_back_and_announces_on_both_failure_branches():
                    base_url = harness.base_url()
                    for lang, failure_copy in (
                            ("en", layout.QUICK_SWITCH_FAILED_TEXT),
                            ("fr", i18n.t_lang(layout.QUICK_SWITCH_FAILED_TEXT, "fr"))):
                        context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/")
                            page.wait_for_load_state("networkidle")
                            # THE CONTROL PHASE. An assertion that a flip
                            # came BACK proves nothing unless the flip
                            # goes out in the first place, and a switch
                            # that never moves satisfies "it was restored"
                            # perfectly. So: prove it lands, then break
                            # the server and prove it returns.
                            start = _switch_state(page)
                            page.click(SWITCH_SEL)
                            page.wait_for_timeout(600)
                            landed = _switch_state(page)
                            if landed == start:
                                return False, (
                                    "lang=%s control: the switch did not move on a WORKING "
                                    "request, so the rollback assertions below would pass on a "
                                    "control that simply never flips" % (lang,))
                            toast_sel = "[%s]" % layout.QUICK_TOAST_ATTR
                            if page.eval_on_selector(toast_sel, "el => el.textContent") != "":
                                return False, (
                                    "lang=%s control: the toast announced something on a "
                                    "SUCCESSFUL flip — it is a failure announcement only"
                                    % (lang,))
                            # Branch 1: a non-OK status.
                            for branch, handler in (
                                    ("a 500 from the server",
                                     lambda route: route.fulfill(status=500, body="")),
                                    ("a network-level failure",
                                     lambda route: route.abort())):
                                page.goto(base_url + "/")
                                page.wait_for_load_state("networkidle")
                                page.route("**/quick/display", handler)
                                try:
                                    known = _switch_state(page)
                                    stored = device_config.load_device_config(
                                        harness.tmpdir)["display_enabled"]
                                    page.click(SWITCH_SEL)
                                    page.wait_for_timeout(800)
                                    if _switch_state(page) != known:
                                        return False, (
                                            "lang=%s, %s: aria-checked stayed at %r instead of "
                                            "rolling back to %r — an optimistic switch that keeps "
                                            "a state the server never accepted is a switch that "
                                            "lies (T-23-26)"
                                            % (lang, branch, _switch_state(page), known))
                                    if page.eval_on_selector_all(
                                            ".frame-strip [data-pending]",
                                            "els => els.length") != 0:
                                        return False, (
                                            "lang=%s, %s: the pending marker was left behind — a "
                                            "region whose control never confirmed would hold "
                                            "itself stale forever" % (lang, branch))
                                    if device_config.load_device_config(
                                            harness.tmpdir)["display_enabled"] is not stored:
                                        return False, (
                                            "lang=%s, %s: the stored value moved on a failed "
                                            "request" % (lang, branch))
                                    announced = page.eval_on_selector(
                                        toast_sel, "el => el.textContent")
                                    if announced != failure_copy:
                                        return False, (
                                            "lang=%s, %s: expected the translated failure copy "
                                            "%r in the toast, got %r"
                                            % (lang, branch, failure_copy, announced))
                                    # V7/T-23-27: no server internal ever.
                                    for internal in ("500", "http", "/quick/", "TypeError"):
                                        if internal in announced:
                                            return False, (
                                                "lang=%s, %s: the toast carries %r — a user-facing "
                                                "failure names no status code, no URL and no "
                                                "server internal" % (lang, branch, internal))
                                    visible = page.eval_on_selector(
                                        toast_sel,
                                        "el => getComputedStyle(el).opacity")
                                    if visible == "0":
                                        return False, (
                                            "lang=%s, %s: the toast carries the right words but "
                                            "is not visible — a live region nobody can see is "
                                            "half an announcement" % (lang, branch))
                                finally:
                                    page.unroute("**/quick/display")
                        finally:
                            context.close()
                    return True, ""
                check(
                    "a switch rolls its aria-checked back, clears its pending marker, leaves the "
                    "stored value alone and announces the TRANSLATED generic failure in a visible "
                    "toast — on a 500 AND on a network-level failure, in English and in French, "
                    "each against a control phase proving the same switch DOES flip and does NOT "
                    "announce on a working request (D2/CFG-36, T-23-26/T-23-27, 23-07-PLAN.md "
                    "Task 3)",
                    _a_switch_rolls_back_and_announces_on_both_failure_branches)

                def _a_refresh_landing_mid_flip_does_not_repaint_the_switch():
                    # THE D1-RACES-D2 RULE, asserted from the D2 side.
                    # 23-06 proved its swap skips a [data-pending] region
                    # using a marker this harness injected by hand; this
                    # is the same rule measured against the marker the
                    # SHIPPED script sets, which is the half 23-06 could
                    # not reach.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/")
                        page.wait_for_load_state("networkidle")
                        before = _switch_state(page)
                        _hold_fetch(page)
                        page.click(SWITCH_SEL)
                        if not _fetch_was_issued(page):
                            return False, "control: no fetch was issued, so nothing is in flight"
                        optimistic = _switch_state(page)
                        if optimistic == before:
                            return False, "control: the switch did not flip, so nothing is pending"
                        # Focus must leave the strip first. freshness.js
                        # ALSO skips the region holding the active
                        # element, and with focus still on the switch this
                        # check would pass on a loop with no pending rule
                        # at all — vacuous in the quietest possible way.
                        page.evaluate("() => document.activeElement.blur()")
                        _mark(page, ".frame-strip", "strip")
                        _mark(page, ".page-header__freshness", "elsewhere")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        # THE CONTROL: a cycle that swapped nothing would
                        # satisfy everything below for free.
                        if _marked(page, ".page-header__freshness", "elsewhere"):
                            return False, (
                                "control: no region was swapped at all, so the assertions below "
                                "would prove nothing")
                        if not _marked(page, ".frame-strip", "strip"):
                            return False, (
                                "the strip was REPLACED while a flip was unconfirmed — the "
                                "fetched document still carries the server's older state, so the "
                                "switch would bounce back under the user's finger (T-23-26, the "
                                "D1-races-D2 rule)")
                        if _switch_state(page) != optimistic:
                            return False, (
                                "the optimistic state was repainted by a refresh: expected %r, "
                                "got %r" % (optimistic, _switch_state(page)))
                        # THE SECOND CONTROL, and the one that makes this
                        # a statement about the MARKER rather than about
                        # the strip: release, let the marker clear, dirty
                        # the region the same way, and it must now be
                        # replaced.
                        _release_fetch(page)
                        page.wait_for_timeout(600)
                        if page.eval_on_selector_all(
                                ".frame-strip [data-pending]", "els => els.length") != 0:
                            return False, "expected the marker to clear once the answer arrived"
                        _mark(page, ".frame-strip", "settled-strip")
                        _dirty_the_region(page, ".frame-strip")
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/"):
                            _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _marked(page, ".frame-strip", "settled-strip"):
                            return False, (
                                "control: the same changed strip survived with NO marker on it, "
                                "so the assertion above was not measuring the pending rule at all")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a Home refresh landing while a flip is unconfirmed leaves the Frame strip "
                    "untouched — by NODE IDENTITY and by the optimistic aria-checked surviving — "
                    "against one control proving another region really was swapped in the same "
                    "cycle and a second proving the same changed strip IS replaced once the marker "
                    "has cleared, with focus deliberately moved off the strip so the focus skip "
                    "cannot be what satisfies it (D1+D2, T-23-26, 23-07-PLAN.md Task 3)",
                    _a_refresh_landing_mid_flip_does_not_repaint_the_switch)

                def _all_three_switches_still_post_with_scripts_blocked_at_360px():
                    # THE FLOOR, and the reason this plan built the switch
                    # AS the shipped form rather than beside it. A control
                    # that renders and silently does nothing with scripts
                    # blocked is the exact defect Phase 22 found on the
                    # login page; the only assertion that catches it is
                    # one that submits and then reads the DISK.
                    base_url = harness.base_url()
                    switches = (
                        ("/", "display_enabled", 'form[action="/quick/display"] button[role="switch"]'),
                        ("/", "quiet_hours_enabled",
                         'form[action="/quick/quiet-hours"] button[role="switch"]'),
                        ("/device", "led_enabled",
                         'button[role="switch"][form="%s"]' % config_page.QUICK_LED_FORM_ID),
                    )
                    for lang in ("en", "fr"):
                        for route, field, selector in switches:
                            with _no_js_page(browser.new_context, base_url, route,
                                             viewport=VIEWPORT_MIN_SUPPORTED) as page:
                                page.context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + route)
                                if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                    return False, "expected the 360px contract floor"
                                control = page.query_selector(selector)
                                if control is None:
                                    return False, (
                                        "lang=%s, %s: the %s switch does not render at all with "
                                        "scripts blocked" % (lang, route, field))
                                # The accessible state is SERVER-rendered,
                                # so it is correct on this page too.
                                stored = device_config.load_device_config(harness.tmpdir)[field]
                                rendered = control.get_attribute("aria-checked")
                                if rendered != ("true" if stored is True else "false"):
                                    return False, (
                                        "lang=%s, %s: the scripts-blocked page claims "
                                        "aria-checked=%r for a stored %r — role=switch is a "
                                        "description of what the button does, not a promise the "
                                        "script keeps" % (lang, field, rendered, stored))
                                # Centred first. At 360px the fixed tab
                                # bar owns the bottom 56px of the
                                # viewport, and a switch that happens to
                                # land under it fails the click with a
                                # pointer-interception error that says
                                # nothing about this plan. Centring is
                                # what a real thumb would do too.
                                page.eval_on_selector(
                                    selector, "el => el.scrollIntoView({block: 'center'})")
                                # 44px in BOTH axes, met directly.
                                box = control.bounding_box()
                                if box["width"] < 44 or box["height"] < 44:
                                    return False, (
                                        "lang=%s, %s: the switch measures %sx%s at 360px, under "
                                        "the 44px touch floor"
                                        % (lang, field, box["width"], box["height"]))
                                with page.expect_navigation():
                                    control.click()
                                after = device_config.load_device_config(harness.tmpdir)[field]
                                if after is stored:
                                    return False, (
                                        "lang=%s, %s: the switch did NOT persist with scripts "
                                        "blocked — it rendered and did nothing, which is the "
                                        "exact defect Phase 22 found on the login page (CFG-38)"
                                        % (lang, field))
                                # And the server's own flash is what tells
                                # this reader it worked: there is no
                                # toast without a script.
                                if page.locator("[%s]" % layout.QUICK_TOAST_ATTR).count() != 1:
                                    return False, (
                                        "lang=%s, %s: expected the toast region to still render "
                                        "(inert) with scripts blocked" % (lang, field))
                                if page.eval_on_selector(
                                        "[%s]" % layout.QUICK_TOAST_ATTR,
                                        "el => el.textContent") != "":
                                    return False, (
                                        "lang=%s, %s: the toast announced something on a page "
                                        "with no script at all" % (lang, field))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, all THREE switches render "
                    "with the server's own aria-checked, clear the 44px touch floor in both axes, "
                    "submit their real form and PERSIST to disk — the assertion that would catch a "
                    "control that renders and silently does nothing (D2/CFG-36, CFG-38, "
                    "23-07-PLAN.md Task 3)",
                    _all_three_switches_still_post_with_scripts_blocked_at_360px)

                # --- 23-08-PLAN.md Task 3 (D7/CFG-37 + D3's two Flights
                # clauses): the live list, proven live -----------------
                #
                # The refresh is forced the same way every 23-06 check
                # above forces it (_force_refresh + REFRESH_SETTLE_MS):
                # the loop's own visibilitychange catch-up, against a
                # shifted Date.now, with the shipped guards unmodified.

                FLIGHT_ID_ATTR = layout.REFRESH_ROW_ID_ATTR
                NEW_ROW_CLASS = layout.REFRESH_NEW_ROW_CLASS

                def _record_a_new_detection(callsign, hex_value, ts):
                    """One more runway_events row, written through the
                    same module server/poll_loop.py writes them with —
                    never a hand-built INSERT, so the row this check
                    calls "a new detection" is the shape a real detection
                    has."""
                    with history_db.open_db(harness.tmpdir) as conn:
                        history_db.record_runway_event(
                            conn, ts=ts, hex=hex_value, callsign=callsign,
                            aircraft_type="A320", confirmed_state="confirmed",
                            corroborated=True, route_source="adsb",
                            airline="Air France", origin="LFPO", destination="LFPG",
                            tracked_runway=device_config.RUNWAY_IDS[0])

                def _row_ids(page):
                    return page.evaluate(
                        "(attr) => [...document.querySelectorAll('tr[data-flight-row][' + attr"
                        " + ']')].map(el => el.getAttribute(attr))", FLIGHT_ID_ATTR)

                def _highlighted(page):
                    return page.evaluate(
                        "(cls) => [...document.querySelectorAll('.' + cls)].length",
                        NEW_ROW_CLASS)

                def _a_new_detection_is_highlighted_and_an_existing_row_is_not():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")

                        before_ids = _row_ids(page)
                        if len(before_ids) < 2:
                            return False, (
                                "expected the seeded fixture to render several rows, got %d — "
                                "with fewer this check measures nothing" % len(before_ids))
                        if len(set(before_ids)) != len(before_ids):
                            return False, (
                                "expected every rendered row identity to be distinct, got %r"
                                % (before_ids,))
                        if _highlighted(page):
                            return False, (
                                "a freshly LOADED page already highlights %d element(s) — the "
                                "highlight means 'this arrived while you were watching', and on "
                                "first paint nothing did" % _highlighted(page))

                        # PHASE 1 — a refresh with nothing new. The known
                        # set was taken from the page as first rendered,
                        # so this cycle must announce nothing. This is
                        # the clause that reddens when the set starts
                        # empty: every row would read as new.
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if _highlighted(page):
                            return False, (
                                "a refresh that brought nothing new highlighted %d element(s) — "
                                "a list that announces itself every cycle has told the reader "
                                "nothing, and is how they learn to ignore it"
                                % _highlighted(page))

                        # PHASE 2 — a genuinely new detection, written to
                        # the same database the page reads, between two
                        # swaps.
                        _record_a_new_detection(
                            "NEWDET", "39ffff", "2026-08-01T23:30:00+00:00")
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)

                        after_ids = _row_ids(page)
                        # 29-03-PLAN.md (CFG-83): Vols is now paginated to
                        # history_page.FLIGHTS_PAGE_SIZE by default, so
                        # "grows by exactly one" only holds BELOW that
                        # cap — at or above it (this harness's own
                        # realistic fixture already renders a full page),
                        # a new detection arriving pushes the oldest
                        # visible row off-page and the count holds flat.
                        # Both shapes are the SAME real behaviour; the
                        # invariant that survives pagination is the one
                        # `arrived`/`marked` below actually test: exactly
                        # one identity is new, and it is at the top.
                        want_after = min(
                            len(before_ids) + 1, history_page.FLIGHTS_PAGE_SIZE)
                        if len(after_ids) != want_after:
                            return False, (
                                "expected the swap to bring the new detection into the live "
                                "list: %d rows before, %d after, wanted %d (min(before+1, "
                                "FLIGHTS_PAGE_SIZE=%d)) — with no new row this check "
                                "would be asserting a highlight on nothing"
                                % (len(before_ids), len(after_ids), want_after,
                                   history_page.FLIGHTS_PAGE_SIZE))
                        arrived = [rid for rid in after_ids if rid not in before_ids]
                        if len(arrived) != 1:
                            return False, (
                                "expected exactly one identity to be new after the swap, got %r"
                                % (arrived,))
                        if after_ids[0] != arrived[0]:
                            return False, (
                                "expected the new detection at the TOP of the list, got %r at "
                                "the top and %r as the new identity" % (after_ids[0], arrived[0]))

                        # BOTH DIRECTIONS. A check that only asserted the
                        # presence of a highlight would pass on an
                        # implementation that highlights everything —
                        # which is the likelier bug, and the more
                        # damaging one.
                        marked = page.evaluate(
                            "([attr, cls]) => [...document.querySelectorAll("
                            "'tr[data-flight-row].' + cls)].map(el => el.getAttribute(attr))",
                            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
                        if marked != arrived:
                            return False, (
                                "expected exactly the arrived row %r to carry the highlight, "
                                "got %r — a highlight on a row that was already there is a "
                                "claim that it just landed, which is false" % (arrived, marked))
                        # And the phone card for the same event is
                        # marked too: Flights renders every flight twice
                        # and a reader on a phone must get the same
                        # signal a reader on a desktop does.
                        card_marked = page.evaluate(
                            "([attr, cls]) => [...document.querySelectorAll("
                            "'li.history-card.' + cls)].map(el => el.getAttribute(attr))",
                            [FLIGHT_ID_ATTR, NEW_ROW_CLASS])
                        if card_marked != arrived:
                            return False, (
                                "expected the phone card for the same event to be marked too, "
                                "got %r" % (card_marked,))
                        # The animation is the stylesheet's own, once,
                        # on the phase's ambient token.
                        animation = page.eval_on_selector(
                            "tr[data-flight-row]." + NEW_ROW_CLASS,
                            "el => [getComputedStyle(el).animationName,"
                            " getComputedStyle(el).animationIterationCount,"
                            " getComputedStyle(el).animationDuration]")
                        if animation[0] != "skypane-row-arrive":
                            return False, (
                                "expected the highlight class to resolve to the stylesheet's own "
                                "arrival block, got %r" % (animation[0],))
                        if animation[1] != "1":
                            return False, (
                                "expected the highlight to run exactly once, got %r iterations"
                                % (animation[1],))
                        if animation[2] != "2s":
                            return False, (
                                "expected the highlight to spend --motion-slow (2s), got %r — a "
                                "180ms flash on a row nobody was looking at is no signal at all"
                                % (animation[2],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a detection recorded while the Flights page is open arrives at the top of the "
                    "live list on the next refresh and is the ONLY thing highlighted — in both the "
                    "table and the phone card list — while a row that was already there is not, "
                    "nothing at all is highlighted on first load, and a refresh that brings nothing "
                    "new announces nothing; the class resolves to the stylesheet's own single-run "
                    "arrival animation on --motion-slow (D7/CFG-37, 23-08-PLAN.md Task 3)",
                    _a_new_detection_is_highlighted_and_an_existing_row_is_not)

                def _a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened():
                    # The half a swapped list gets wrong silently. The
                    # SERVER renders every detail row VISIBLE — that is
                    # D-15's locked no-JS floor and it carries no
                    # open/closed state at all — so a refresh arrives
                    # with every row expanded and every toggle reading
                    # aria-expanded="false". Without flight-rows.js
                    # re-deriving its own state after the swap, one
                    # refresh unfolds the whole table; with a record
                    # keyed to the row's POSITION instead of its event
                    # identity, a detection arriving at the top reopens
                    # the wrong row.
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")

                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        opened_id = page.eval_on_selector(
                            "#" + toggle.get_attribute("aria-controls"),
                            "(el, attr) => el.getAttribute(attr)", FLIGHT_ID_ATTR)
                        if not opened_id:
                            return False, "expected the detail row to carry its event identity"
                        toggle.click()

                        # BLURRED ON PURPOSE. The click leaves focus on
                        # the toggle, and freshness.js skips any region
                        # containing the active element — so with focus
                        # still there this check would pass against a
                        # script that re-derives nothing at all.
                        page.evaluate("() => document.activeElement.blur()")

                        _record_a_new_detection(
                            "OPENSRV", "39fffe", "2026-08-02T00:15:00+00:00")
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)

                        seen = page.evaluate(
                            "([idAttr, openId]) => {"
                            "  const details = [...document.querySelectorAll("
                            "    'tr.flight-detail-row')];"
                            "  const open = details.filter(el =>"
                            "    el.className.indexOf('flight-detail-row--collapsed') === -1);"
                            "  return {total: details.length,"
                            "          open: open.map(el => el.getAttribute(idAttr)),"
                            "          expanded: [...document.querySelectorAll("
                            "            '[data-row-toggle][aria-expanded=\\\"true\\\"]')].length,"
                            "          stillThere: !!document.querySelector("
                            "            'tr.flight-detail-row[' + idAttr + '=\\\"' + openId"
                            "            + '\\\"]')};"
                            "}", [FLIGHT_ID_ATTR, opened_id])
                        if seen["total"] < 2:
                            return False, (
                                "expected the swapped list to still render its detail rows, got "
                                "%d — with fewer this check measures nothing" % seen["total"])
                        if not seen["stillThere"]:
                            return False, (
                                "the row that was opened is no longer in the list at all, so "
                                "nothing below is a statement about it")
                        if seen["open"] != [opened_id]:
                            return False, (
                                "after a refresh %d of %d detail rows are open (%r), expected "
                                "exactly the one that was opened (%r). Every row open is the "
                                "server's own markup arriving un-collapsed; the WRONG row open "
                                "is a record keyed to a position that just renumbered"
                                % (len(seen["open"]), seen["total"], seen["open"], opened_id))
                        if seen["expanded"] != 1:
                            return False, (
                                "expected exactly one toggle to report aria-expanded=true after "
                                "the refresh, got %d — the class and the announced state are "
                                "written in one place precisely so they cannot drift"
                                % seen["expanded"])
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a refresh neither unfolds the Flights table nor closes the row you opened: "
                    "with focus deliberately blurred off the toggle (so the loop's focus skip "
                    "cannot be what passes this) and a new detection renumbering every row below "
                    "it, exactly the row that was opened is still open — by EVENT identity, not by "
                    "position — and exactly one toggle still announces it (D7/CFG-37, "
                    "23-08-PLAN.md Task 3)",
                    _a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened)

                def _a_refresh_never_interrupts_or_undoes_the_filter():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        page.wait_for_load_state("networkidle")
                        requests = _count_document_requests(page, base_url + "/flights")

                        # 29-03-PLAN.md (CFG-83): Vols is now paginated
                        # to history_page.FLIGHTS_PAGE_SIZE by default, so
                        # a hardcoded callsign from seed_state_dir()'s own
                        # 36-flight fixture is no longer guaranteed to be
                        # among the rows the SERVER actually sent — this
                        # reads the first rendered row's own
                        # data-filter-text (unique per row: "{callsign
                        # lowercased} {hex}") straight off the page
                        # instead, so the query always targets a row
                        # that is genuinely there, whatever the default
                        # page size is.
                        query = page.eval_on_selector(
                            "tr[data-flight-row]", "el => el.getAttribute('data-filter-text')")
                        if not query:
                            return False, (
                                "expected the first rendered row to carry a non-empty "
                                "data-filter-text to filter by — with none, this check has "
                                "nothing to type")
                        page.click("[data-filter-input]")
                        page.type("[data-filter-input]", query)
                        visible = page.evaluate(
                            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
                            ".filter(el => !el.hidden).length")
                        if visible != 1:
                            return False, (
                                "expected the query to narrow the table to one row before "
                                "anything else is measured, got %d" % visible)
                        count_text = page.eval_on_selector(
                            "[data-filter-count]", "el => el.textContent")

                        # PHASE 1 — with the caret still in the box, the
                        # whole cycle stands down. Counted as REQUESTS,
                        # not as DOM state: a page that fetched and then
                        # declined to swap is a different behaviour.
                        before = requests()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if requests() != before:
                            return False, (
                                "the loop fetched while the caret was in the filter box — "
                                "userIsInteracting() exists so a half-typed query is never "
                                "swapped out from under the person typing it (%d request(s))"
                                % (requests() - before))

                        # CONTROL — the same trigger, focus moved off the
                        # input, MUST fetch. Without this phase 1 would
                        # pass on a page whose loop never runs at all.
                        page.evaluate("() => document.activeElement.blur()")
                        before = requests()
                        _force_refresh(page)
                        page.wait_for_timeout(REFRESH_SETTLE_MS)
                        if requests() == before:
                            return False, (
                                "control: the same trigger issued no request with focus off the "
                                "input either — this page's loop is not running, so phase 1 "
                                "proved nothing")

                        # PHASE 2 — and that swap must not have undone
                        # the query. The SERVER renders the list
                        # unfiltered; it knows nothing about what was
                        # typed here.
                        visible = page.evaluate(
                            "() => [...document.querySelectorAll('tr[data-flight-row]')]"
                            ".filter(el => !el.hidden).length")
                        if visible != 1:
                            return False, (
                                "a refresh handed back %d visible rows under a query that "
                                "matches one — the server renders the list unfiltered, so a swap "
                                "that is not followed by a re-filter silently undoes what the "
                                "reader asked for" % visible)
                        if page.eval_on_selector(
                                "[data-filter-count]", "el => el.textContent") != count_text:
                            return False, (
                                "the live count reverted to the server's own unfiltered sentence "
                                "after a refresh, expected it to still read %r" % (count_text,))
                        if page.eval_on_selector(
                                "[data-filter-input]", "el => el.value") != query:
                            return False, "the typed query itself did not survive the refresh"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a refresh never interrupts the filter and never undoes it: with the caret in "
                    "the box the loop issues ZERO requests (counted, against a control proving the "
                    "same trigger does fetch with focus moved off), and the swap that then happens "
                    "leaves the typed query applied — same visible rows, same live count, same "
                    "input value — because the server renders the list unfiltered (D7/CFG-37, "
                    "23-08-PLAN.md Task 3)",
                    _a_refresh_never_interrupts_or_undoes_the_filter)

                def _a_collapsed_detail_row_cannot_be_reached_by_keyboard():
                    context = browser.new_context(viewport=VIEWPORT_DESKTOP)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        toggle = page.locator("[data-row-toggle]").first
                        toggle.wait_for(state="visible")
                        detail_id = toggle.get_attribute("aria-controls")

                        # Every focusable thing inside the row is asked
                        # to take focus, one at a time, and must fail to.
                        # This is the keyboard question asked directly
                        # rather than through a proxy: an element that
                        # cannot become document.activeElement is an
                        # element Tab cannot land on, and display:none is
                        # also what keeps it out of the accessibility
                        # tree.
                        probe = (
                            "(id) => {"
                            "  const row = document.getElementById(id);"
                            "  const kids = [...row.querySelectorAll("
                            "    'a[href], button, input, select, textarea, [tabindex]')];"
                            "  const reached = [];"
                            "  kids.forEach(el => { el.focus();"
                            "    if (document.activeElement === el) reached.push("
                            "      el.tagName + '.' + (el.className || ''));"
                            "    el.blur(); });"
                            "  return {kids: kids.length, reached: reached};"
                            "}")
                        seen = page.evaluate(probe, detail_id)
                        if not seen["kids"]:
                            return False, (
                                "expected the seeded detail row to contain focusable controls "
                                "(its copy buttons) — with none, this check measures nothing")
                        if seen["reached"]:
                            return False, (
                                "a COLLAPSED detail row let %d of its %d controls take focus "
                                "(%r) — a row held present at zero height is still in the tab "
                                "order and still in the accessibility tree, so a keyboard user "
                                "walks into a row nobody can see (T-23-32)"
                                % (len(seen["reached"]), seen["kids"], seen["reached"]))

                        # CONTROL — open the row and the SAME controls
                        # must become reachable. Without this the check
                        # would pass just as well on a page that renders
                        # no detail row at all.
                        toggle.click()
                        seen = page.evaluate(probe, detail_id)
                        if not seen["reached"]:
                            return False, (
                                "control: an OPEN detail row's %d controls were still "
                                "unreachable — so the assertion above is about the page being "
                                "empty, not about the row being closed" % seen["kids"])

                        # And the opening really is a height animation,
                        # on the wrapper rather than on the row box.
                        style = page.eval_on_selector(
                            "#" + detail_id + " .flight-detail-row__reveal",
                            "el => [getComputedStyle(el).display,"
                            " getComputedStyle(el).transitionProperty,"
                            " getComputedStyle(el).transitionDuration]")
                        if style[0] != "grid":
                            return False, (
                                "expected the reveal wrapper to be a grid, got %r" % (style[0],))
                        if "grid-template-rows" not in style[1]:
                            return False, (
                                "expected grid-template-rows to be the transitioned property, "
                                "got %r — a guessed max-height either clips tall content or "
                                "animates through empty space, and interpolate-size is "
                                "Chromium-only" % (style[1],))
                        if style[2] != "0.18s":
                            return False, (
                                "expected the reveal to spend --motion-fast (180ms), got %r"
                                % (style[2],))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a COLLAPSED Flights detail row lets none of its own controls take focus — the "
                    "deliberate display:none end state, asked as the keyboard question directly — "
                    "against a control phase proving the same controls ARE reachable once the row "
                    "is open, and the opening really animates grid-template-rows on a grid wrapper "
                    "at --motion-fast (D3/CFG-32, T-23-32, 23-08-PLAN.md Task 3)",
                    _a_collapsed_detail_row_cannot_be_reached_by_keyboard)

                def _a_phone_card_opens_from_a_tap_anywhere_with_and_without_scripts():
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/flights")
                        card = page.locator("li.history-card").first
                        card.wait_for(state="visible")
                        details = card.locator("details.history-card__details")
                        if details.evaluate("el => el.open"):
                            return False, (
                                "expected the card to start closed — with it open this check "
                                "cannot tell a tap that worked from a card that was never shut")
                        # The "anywhere" property, measured: the summary's
                        # own box must cover the card's whole face,
                        # padding included. A summary that stopped at the
                        # padding's inner edge would leave a rim that
                        # looks tappable and is not.
                        boxes = page.evaluate(
                            "() => {"
                            "  const li = document.querySelector('li.history-card');"
                            "  const s = li.querySelector('summary.history-card__summary');"
                            "  const a = li.getBoundingClientRect();"
                            "  const b = s.getBoundingClientRect();"
                            "  return [a.width, b.width, a.top, b.top];"
                            "}")
                        if boxes[1] < boxes[0] - 2.5:
                            return False, (
                                "the card's summary is %spx wide inside a %spx card — a tap on "
                                "the rim between them lands on nothing, which reads as a broken "
                                "control rather than as a boundary" % (boxes[1], boxes[0]))
                        # Tapped on the secondary line, which is not a
                        # control and never was: the route and the state.
                        card.locator(".history-card__secondary").click()
                        if not details.evaluate("el => el.open"):
                            return False, (
                                "a tap on the card's own face away from every control did not "
                                "open it — D7 asks for a card you tap anywhere, through the "
                                "native disclosure it already contained")
                        # Nothing nested inside the summary can steal
                        # that activation, because nothing is nested in
                        # it: the one-hop resolve link sits outside.
                        nested = page.eval_on_selector(
                            "summary.history-card__summary",
                            "el => el.querySelectorAll('a[href], button').length")
                        if nested:
                            return False, (
                                "expected no control nested inside the card's summary, found %d"
                                % nested)
                    finally:
                        context.close()

                    # And with no script at all, at the same 360px floor.
                    # The disclosure is native, so this is not a fallback
                    # path that could rot — it is the same control.
                    with _no_js_page(browser.new_context, harness.base_url(), "/flights",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        card = page.locator("li.history-card").first
                        card.wait_for(state="visible")
                        details = card.locator("details.history-card__details")
                        if details.evaluate("el => el.open"):
                            return False, "expected the scripts-blocked card to start closed too"
                        card.locator(".history-card__secondary").click()
                        if not details.evaluate("el => el.open"):
                            return False, (
                                "the phone card did not open with scripts blocked — the whole "
                                "point of building this on the <details> the card already had is "
                                "that it needs no script (CFG-38)")
                        # The detail ROW floor, in the same context: with
                        # no script nothing is collapsed and every detail
                        # is on screen, exactly as before this plan.
                        collapsed = page.evaluate(
                            "() => document.querySelectorAll("
                            "'.flight-detail-row--collapsed').length")
                        if collapsed:
                            return False, (
                                "%d detail row(s) are collapsed on a page with no script — the "
                                "collapsing class has exactly one writer and it cannot run here "
                                "(D-15, locked)" % collapsed)
                        live = page.evaluate(
                            "() => document.documentElement.className.indexOf("
                            "'flight-rows-live') !== -1")
                        if live:
                            return False, (
                                "the live-script class is on <html> with no script running — the "
                                "height animation is keyed on it precisely so a scripts-blocked "
                                "page animates nothing")
                    return True, ""
                check(
                    "a phone card at 360px opens from a tap on its own face away from every "
                    "control, through the native disclosure it already contained, with its summary "
                    "box covering the whole card and no control nested inside it — and it does the "
                    "same with SCRIPTS BLOCKED, where no detail row is collapsed and the "
                    "live-script class the height animation is keyed on is absent (D7/CFG-37, "
                    "CFG-38, 23-08-PLAN.md Task 3)",
                    _a_phone_card_opens_from_a_tap_anywhere_with_and_without_scripts)

                # --- 23-09-PLAN.md Task 3 (D3/CFG-32): the save bar,
                # the app's most-iterated component and the one that
                # carried B1, gaining motion and a label. Everything
                # below is a regression surface before it is a feature:
                # the bar's own checks above (reveal-and-persist on both
                # scopes, the fallback's visibility contract, Cancel and
                # the leave-guard, the tab-bar geometry, the
                # double-submit guard) were run and recorded GREEN
                # before a line of this plan's CSS or JS was written.

                def _the_dirty_count_arrives_and_moves_only_when_the_word_does():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not a
                    # mechanical swap — this check's own subject
                    # ([data-save-status] and its exact [saving, saved]
                    # text sequence) is deleted outright with the auto-save
                    # model, and a straight deletion would silently drop
                    # real coverage. One genuinely valuable idea survives:
                    # clicking an ALREADY-CHECKED radio fires no native
                    # `change`, so a role="status" element must announce
                    # nothing for it — a live-region hygiene contract the
                    # restored bar shares (it is role="status" too).
                    # Retargeted onto [data-dirty-count], with a
                    # MutationObserver installed BEFORE the first edit so
                    # the exact sequence of writes is recorded rather than
                    # sampled at the end.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")
                        current_theme = page.eval_on_selector(
                            'input[name="theme"]:checked', "el => el.value")
                        theme_target, theme_target2 = [
                            t for t in device_config.THEME_IDS if t != current_theme][:2]

                        page.evaluate(
                            "() => {"
                            " window.__countWords = [];"
                            " var el = document.querySelector('[data-dirty-count]');"
                            " new MutationObserver(function () {"
                            "   window.__countWords.push(el.textContent);"
                            " }).observe(el, {childList: true, characterData: true,"
                            "                 subtree: true});"
                            "}")

                        # a. THE SURVIVING CONTROL PHASE: clicking the
                        # ALREADY-CHECKED radio fires no native `change`
                        # (the checked state does not change), so
                        # countDifferences() stays at 0 and the count
                        # element must not be written AT ALL — this is now
                        # testing setCountText()'s own changed-text gate,
                        # the mechanism that makes a no-op click produce no
                        # write.
                        _click_control(page, 'input[name="theme"][value="%s"]' % current_theme)
                        page.wait_for_timeout(150)
                        after_noop = page.evaluate("() => window.__countWords.slice()")
                        if after_noop:
                            return False, (
                                "re-clicking the ALREADY-selected theme wrote to "
                                "[data-dirty-count]: %r — a click that changed no value must not "
                                "announce one" % (after_noop,))

                        # b. A REAL CHANGE — exactly ONE text mutation, to
                        # the section's own name, read off the bar's OWN
                        # data-dirty-changed-suffix and the field's own
                        # data-dirty-section wrapper, never hardcoded in
                        # English (this file's own D-06 idiom).
                        expected_label = page.evaluate(
                            "() => {"
                            " var field = document.querySelector('input[name=\"theme\"]');"
                            " var wrapper = field.closest('[data-dirty-section]');"
                            " var bar = document.querySelector('[data-dirty-bar]');"
                            " return wrapper.getAttribute('data-dirty-section')"
                            "   + bar.getAttribute('data-dirty-changed-suffix');"
                            "}")
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target)
                        _wait_for_bar(page)
                        words = page.evaluate("() => window.__countWords.slice()")
                        if len(words) != 1:
                            return False, (
                                "expected exactly ONE text mutation to [data-dirty-count] for a "
                                "real change, got %r" % (words,))
                        if words[0] != expected_label:
                            return False, (
                                "expected [data-dirty-count] to read %r after the real change, "
                                "got %r" % (expected_label, words[0]))
                        if "is-fading-in" not in (
                                page.locator("[data-dirty-count]").get_attribute("class") or ""):
                            return False, (
                                "expected [data-dirty-count] to carry the changed-value class "
                                "after a real change")

                        # c. A DIFFERENT VALUE, SAME RENDERED LABEL — the
                        # gate genuinely exercised. MEASURED, not
                        # assumed: re-selecting the value a radio already
                        # holds fires NO native `change` at all
                        # (confirmed live — a checked-state no-op never
                        # reaches this listener), so phase (a)'s own
                        # already-checked click can never reach
                        # setCountText() either, regardless of its own
                        # gate. The gate this check's own mutation names
                        # is only reachable when updateBar() genuinely
                        # RUNS (a real change fires) but resolves to the
                        # SAME text as before — which a second, DIFFERENT
                        # theme inside the identical data-dirty-section
                        # wrapper produces: a real change (a different
                        # radio becomes checked), yet dirtySectionLabels()
                        # names the same section, so setCountText()
                        # receives the identical string and the gate is
                        # what decides whether that write happens.
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_target2)
                        page.wait_for_timeout(150)
                        after_second = page.evaluate("() => window.__countWords.slice()")
                        if after_second != words:
                            return False, (
                                "changing to a DIFFERENT theme inside the same section wrote a "
                                "new mutation to [data-dirty-count]: %r became %r — the two "
                                "renders are textually IDENTICAL, so a write here is "
                                "setCountText()'s own changed-text gate failing to suppress a "
                                "no-op text assignment" % (words, after_second))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "[data-dirty-count] ARRIVES rather than appearing, and stays silent for "
                    "anything that is not a genuine change: clicking an ALREADY-CHECKED radio "
                    "writes nothing (the surviving control-phase idea from the retired "
                    "save-status region — MEASURED live to fire no native change at all, never "
                    "reaching updateBar()); a REAL change writes the section's own name EXACTLY "
                    "ONCE, read off the bar's own data-* attributes never hardcoded in English, "
                    "and carries the changed-value class; and changing to a SECOND, DIFFERENT "
                    "theme inside the identical data-dirty-section wrapper — a real change that "
                    "resolves to the textually IDENTICAL label — writes nothing further, which "
                    "is setCountText()'s own changed-text gate genuinely exercised (a same-value "
                    "re-click, tried first, never reaches the listener at all and so cannot "
                    "prove the gate) — a new phase this check gains over its retired predecessor "
                    "(D3/CFG-32, 23-09-PLAN.md Task 3; retargeted from the retired save-status "
                    "region onto the restored bar by 28-10-PLAN.md Task 2, CFG-77/CFG-78)",
                    _the_dirty_count_arrives_and_moves_only_when_the_word_does)

                def _the_bars_save_persists_every_field_never_only_the_touched_one():
                    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED —
                    # the subject moved from a request body to disk. A
                    # native form submission posts every named field by
                    # construction (the browser builds the body from
                    # every form control, form=-attached or not), so
                    # intercepting the request and reading its body would
                    # be testing the BROWSER, not this app. What still
                    # matters and can still regress is CFG-36's own
                    # hazard: a single field's save must never silently
                    # clobber every OTHER field's on-disk value. Proven
                    # here against disk instead of a request body — a
                    # STRONGER surface, not a weaker one: a server that
                    # posts the whole form correctly but then only WRITES
                    # the touched key would still pass the retired
                    # request-body check and still fail this one.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            # tracked_runway: a cross-DOM form=-attached
                            # field living OUTSIDE the physical <form> —
                            # the exact shape CFG-36's own hazard was
                            # found in — on a scope (Display) with
                            # several OTHER fields for the assertion to
                            # have something to catch.
                            before = device_config.load_device_config(harness.tmpdir)
                            target = next(
                                r for r in device_config.RUNWAY_IDS
                                if str(r) != str(before["tracked_runway"]))

                            page.goto(base_url + "/display")
                            _click_control(
                                page, 'input[name="tracked_runway"][value="%s"]' % target)
                            _wait_for_bar(page)
                            _save_via_bar(page)

                            after = device_config.load_device_config(harness.tmpdir)
                            if str(after["tracked_runway"]) != str(target):
                                return False, (
                                    "lang=%s: the save did not persist — expected "
                                    "tracked_runway %r, got %r"
                                    % (lang, target, after["tracked_runway"]))
                            changed_keys = [k for k in before if before[k] != after.get(k)]
                            if changed_keys != ["tracked_runway"]:
                                return False, (
                                    "lang=%s: saving ONE field (tracked_runway) changed %r on "
                                    "disk — a save that clobbers an untouched field is CFG-36's "
                                    "own hazard; before=%r after=%r"
                                    % (lang, changed_keys, before, after))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the bar's own Save persists EVERY field to disk, never only the touched one: "
                    "reading the FULL on-disk config before and after a single-field "
                    "(tracked_runway) save, in both languages, and asserting the two dicts "
                    "differ in EXACTLY the one key touched — a STRONGER surface than the retired "
                    "request-body capture, since a server that posts the whole form but only "
                    "writes the touched key would still pass that check and fail this one "
                    "(T-27-04-D, CFG-36's own hazard; retargeted from the request body onto disk "
                    "by 28-10-PLAN.md Task 3, CFG-77/CFG-78; 27-04-PLAN.md Task 4, CFG-63; "
                    "supersedes the retired Save-button relabel check, T14's deferred label, "
                    "23-09-PLAN.md Task 3/D3/CFG-32)",
                    _the_bars_save_persists_every_field_never_only_the_touched_one)

                def _with_no_script_the_fallback_save_is_the_only_way():
                    # 27-04-PLAN.md Task 4 (CFG-63): SUPERSEDES this
                    # check's own pre-27-04 subject — THE FLOOR THIS
                    # COMPONENT BROKE ONCE (B1: the save bar never
                    # appeared, and the fallback had already hidden
                    # itself). The bar and both of its former liveness
                    # markers (dirty-ready/dirty-shown) are retired
                    # outright, so there is nothing left on <html> or in
                    # the DOM for a scripts-blocked page to prove absent
                    # — what survives is the floor itself: the fallback
                    # Save is VISIBLE, has a real box, and still saves.
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            # quick-260923-em4: the ROOT CAUSE the 260923-9na partial fix
                            # below was circling. Clicking the fallback while the bar's
                            # `skypane-bar-arrive` entrance animation is still running stalls
                            # Playwright's `stable` actionability leg in this scripts-blocked
                            # context: measured ~0.7-1.0s per click in isolation (vs ~0.06s with
                            # motion reduced) and, inside this full harness, a hang for the whole
                            # 30000ms budget — no request and no navigation fired during it
                            # (traced with framenavigated/request listeners), so the click never
                            # happened at all. Reduced motion zeroes the entrance through the
                            # stylesheet's own `prefers-reduced-motion: reduce` override. This
                            # check's subject is that the fallback is visible, has a box and
                            # SAVES, not the entrance animation, so nothing it asserts is lost.
                            # Every local full-harness run failed here without this; 2/2 pass
                            # with it.
                            page.emulate_media(reduced_motion="reduce")
                            page.goto(base_url + "/display")
                            if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
                                return False, "expected the measurement at the 360px contract floor"
                            fallback = page.locator(
                                "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                            if fallback.count() != 1:
                                return False, (
                                    "lang=%s: expected exactly one fallback Save, got %d — with "
                                    "no script it is the ONLY way to save this page"
                                    % (lang, fallback.count()))
                            if not fallback.is_visible():
                                return False, (
                                    "lang=%s: the fallback Save is rendered but not visible — "
                                    "which is precisely the shape B1 took, and a check that only "
                                    "asked whether it EXISTS would have passed through it"
                                    % (lang,))
                            box = fallback.bounding_box()
                            if not box or box["width"] <= 0 or box["height"] <= 0:
                                return False, (
                                    "lang=%s: the fallback Save has no box at 360px (%r)"
                                    % (lang, box))
                            current = device_config.load_device_config(harness.tmpdir)["theme"]
                            target = next(
                                t for t in device_config.THEME_IDS if t != current)
                            page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % target,
                                "el => el.checked = true")
                            # quick-260923-9na: expect_navigation()'s 30000ms clock
                            # starts the instant this `with` is entered — BEFORE
                            # click()'s own actionability poll (visible/stable/
                            # receives-events/enabled) has even begun, so under CI
                            # load that poll silently eats the SAME budget the
                            # navigation wait needs. Real CI (run 35818514258 on
                            # main, 2026-09-23) recorded `TimeoutError('Timeout
                            # 31ms exceeded ... "domcontentloaded" event fired')` —
                            # the actionability poll had already burned 29969ms of
                            # the 30000ms before navigation got a look-in. Waiting
                            # for visibility here, on its OWN clock, before the
                            # `with` block starts, removes that portion of the
                            # overlap without widening any timeout.
                            fallback.wait_for(state="visible")
                            with page.expect_navigation():
                                fallback.click()
                            saved = device_config.load_device_config(harness.tmpdir)["theme"]
                            if saved != target:
                                return False, (
                                    "lang=%s: a Display save did not persist through the "
                                    "fallback Save with scripts blocked at 360px — expected "
                                    "theme %r, got %r. This is the P0 Phase 22 existed to fix"
                                    % (lang, target, saved))
                    return True, ""
                check(
                    "with scripts blocked at 360px, in BOTH languages, the fallback Save is "
                    "VISIBLE with a real box and still saves to disk — B1's floor re-asserted "
                    "after the bar and both its former liveness markers are retired outright "
                    "(B1/CFG-38, 23-09-PLAN.md Task 3; retargeted by 27-04-PLAN.md Task 4, CFG-63)",
                    _with_no_script_the_fallback_save_is_the_only_way)

                # ----------------------------------------------------------
                # 27-05-PLAN.md Task 3 (CFG-66): CFG-47's schematic runway
                # map RETIRED. The three checks 25-03-PLAN.md Task 3 added
                # here — the map's own save-corroboration, its keyboard/
                # paint proof, and its 360px floor measurement — are GONE,
                # named in 27-05-SUMMARY.md, along with the `_runway_ids()`
                # and `_SETTLE_STRIPS` helpers only they used.
                #
                # The radios' OWN scripts-blocked save-to-disk proof —
                # `_the_floor_saves_to_disk_with_scripts_blocked_after_the_
                # gate_simplifies` (CFG-64, 27-03-PLAN.md Task 3), further
                # down this file — never depended on the map's presence
                # and is UNCHANGED by this removal; it is the mitigation
                # T-27-05-A names.
                #
                # ONE check replaces the three: the map is gone, the
                # radios and the photographs are not — asserted as a
                # RELATIONSHIP (D-32) rather than as three separate facts,
                # because "the drawing is gone" alone would also pass on a
                # card that lost the control or the pictures with it. And
                # the touch target the map's own card used to provide is
                # measured rather than assumed, in the control's own
                # container, at 360px, in BOTH themes (T-27-05-B) — the
                # box changed when the drawing came out, and nobody had
                # re-measured it until now.
                # ----------------------------------------------------------

                def _the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor():
                    base_url = harness.base_url()
                    ids = device_config.RUNWAY_IDS
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        # THE RELATIONSHIP, IN ONE PLACE: the drawing is
                        # gone AND the control is not AND the photographs
                        # are not — three clauses about one rendering,
                        # because a check that only asked the first would
                        # pass against a card that lost everything else
                        # with it.
                        maps = page.locator(".runway-card .runway-map").count()
                        if maps != 0:
                            return False, (
                                "expected ZERO .runway-map elements on /display after CFG-66's "
                                "removal, found %d — the drawing is supposed to be gone" % (maps,))
                        radios = page.locator('input[name="tracked_runway"]').count()
                        if radios != len(ids):
                            return False, (
                                "expected %d tracked_runway radios, found %d — the map coming "
                                "out must not take the control it was wrapped around with it"
                                % (len(ids), radios))
                        photos = page.locator(".runway-card .runway-card__image").count()
                        if photos != len(ids):
                            return False, (
                                "expected %d runway photographs (.runway-card__image), found %d "
                                "— the developer objected to the drawn map, not to the "
                                "pictures, and this relationship must also fail if they vanish"
                                % (len(ids), photos))

                        message = _assert_no_page_overflow(
                            page, "the runway row on /display",
                            VIEWPORT_MIN_SUPPORTED["width"])
                        if message:
                            return False, message

                        # THE HIT TARGET THE MAP'S OWN CARD USED TO
                        # PROVIDE, MEASURED RATHER THAN ASSUMED (T-27-05-B).
                        # `.runway-row > .runway-card` is the SAME
                        # container the retired map check measured — only
                        # the box inside it changed, from a drawing plus a
                        # number to a number, a photograph and a check
                        # glyph. IN ITS OWN CONTAINER, never inherited from
                        # a class, and in BOTH themes: a card that only
                        # cleared the floor in one theme's box model would
                        # still fail a visitor using the other.
                        themes_measured = []
                        for state in _in_both_themes(page):
                            for index in range(len(ids)):
                                selector = (
                                    ".runway-row > .runway-card:nth-child(%d)" % (index + 1))
                                _assert_hit_target(
                                    page, selector,
                                    "the runway card %d of %d on /display in the %s theme, "
                                    "now that its map is gone"
                                    % (index + 1, len(ids), state["theme"]))
                            themes_measured.append(state["theme"])
                        if len(themes_measured) != 2:
                            return False, (
                                "expected a hit-target measurement in each of two themes, got "
                                "%d (%r)" % (len(themes_measured), themes_measured))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "CFG-66: the map is gone, the radios and the photographs are not — asserted "
                    "as ONE relationship rather than three separate facts: zero .runway-map "
                    "elements resolve on /display, exactly RUNWAY_IDS' own count of "
                    "tracked_runway radios and of .runway-card__image photographs still "
                    "resolve, the runway row does not scroll the page sideways at 360px, and "
                    "every runway card clears the 44px hit-target floor in ITS OWN container at "
                    "360px in BOTH themes — measured, not assumed, now that the map strip no "
                    "longer provides the box (CFG-66/D-32/T-27-05-B, retiring CFG-47's three "
                    "checks named in 27-05-SUMMARY.md)",
                    _the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor)

                # 30-03-PLAN.md Task 3 (CFG-85): THEME_STRIP_SEL,
                # THEME_PAGERS_SEL, THEME_DETAILS_SEL, _STRIP_PROBE,
                # _SETTLE_CAROUSEL, _CAROUSEL_INSTANCE_PROBE and
                # _TOGGLE_OWN_DISCLOSURE (the whole shared carousel
                # selector/probe block that used to live here) are
                # RETIRED WITH THEIR LAST CONSUMER
                # (_the_carousel_meets_its_floors_at_360px_in_both_
                # themes, ledgered above) — grepped whole-file before
                # deletion, zero remaining consumers of any of the
                # seven. THEME_PREVIEW_SEL SURVIVES — the live preview
                # element (`.theme-live-preview__image`) is unchanged by
                # this phase, and
                # _cancel_restores_the_field_the_preview_and_the_dial_
                # from_the_resulting_dom (below) still reads it.
                THEME_PREVIEW_SEL = ".theme-live-preview__image"

                # --- 25-06-PLAN.md Task 1 (CFG-50): the number this
                # plan is judged against, taken before there was any
                # incentive to like it. See _display_page_height() for
                # why this is an instrument rather than a sentence in a
                # document, and for what it refuses to measure.
                def _displays_page_height_is_recorded_at_both_phone_widths():
                    base_url = harness.base_url()
                    heights = {}
                    for viewport in (VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED):
                        seen = _display_page_height(browser.new_context, base_url, viewport)
                        heights[viewport["width"]] = seen["height"]
                        print(
                            "        [25-06 T1] Display document height at %dpx: "
                            "%d px (client %dx%d, %d theme radios)"
                            % (viewport["width"], seen["height"],
                               seen["clientWidth"], seen["clientHeight"],
                               seen["themeRadios"]))
                    # NO TARGET IS ASSERTED HERE, DELIBERATELY. 22-10
                    # recorded X6's height target as not met and not
                    # reachable by density alone; whether THIS plan
                    # reaches it is stated in that plan's own SUMMARY
                    # from these numbers, in either direction.
                    #
                    # AND NO CROSS-WIDTH RELATIONSHIP EITHER, BECAUSE THE
                    # OBVIOUS ONE IS FALSE ON THIS PAGE AND WAS MEASURED
                    # TO BE. The first version of this check asserted
                    # that a narrower viewport cannot make a reflowing
                    # page shorter. Run before a byte of this plan's
                    # markup existed, Display measured 4276 px at 390px
                    # and 4269 px at 360px — SEVEN PIXELS SHORTER at the
                    # narrower width — and the check duly failed against
                    # a page with nothing whatever wrong with it. The
                    # cause is ordinary: this page is a stack of cards
                    # whose rows each round independently, and a handful
                    # of them land on a different line count at one width
                    # than the other. The clause was removed rather than
                    # loosened to a tolerance, because a tolerance would
                    # have been a number invented to make a wrong belief
                    # pass. What is asserted instead is everything
                    # `_display_page_height()` asserts about WHERE the
                    # number came from, which is the property that makes
                    # a recorded height worth anything.
                    if not heights:
                        return False, "no viewport was measured at all"
                    return True, ""
                check(
                    "Display's full rendered document height is recorded at 390px and at 360px "
                    "by one instrument — proved to be pointed at the authenticated Display page "
                    "(its Aspect heading AND a full THEME_IDS-sized departures "
                    "radiogroup, never merely 'a page rendered'), at the width the caller asked "
                    "for, and taller than the viewport — asserting NO target, because the "
                    "number IS the criterion and 25-06 states in its own SUMMARY whether it is "
                    "met, and no cross-width relationship either, because the obvious one "
                    "(narrower cannot be shorter) was MEASURED FALSE on this page before the "
                    "plan changed anything (CFG-50, 25-06-PLAN.md Task 1)",
                    _displays_page_height_is_recorded_at_both_phone_widths)

                # --- 25-06-PLAN.md Task 4 (CFG-50/D-09) ---------------

                def _the_theme_still_saves_with_scripts_blocked():
                    # 30-03-PLAN.md Task 3 (CFG-85): NARROWED, not
                    # deleted. This is the markup-agnostic half of
                    # CFG-85's own named proof — it drives by field
                    # NAME and reads back from disk, never a strip/
                    # pager/disclosure selector — so it survives the
                    # rebuild verbatim. The trailing strip-probe half
                    # (carousel chip count, overflow, keyboard-arrow
                    # selection through the strip, the <details>
                    # disclosure, the pager gate) is LEDGERED to 30-08
                    # — see _ASPECT_REPIN_LEDGER below.
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(harness.tmpdir)["theme"]

                    before = read_back()
                    target = next(t for t in device_config.THEME_IDS if t != before)
                    seen = {}
                    # BOTH SHIPPED LANGUAGES: the UI language is a cookie
                    # the FIRST rendered document has to honour, and "it
                    # saves in English" is not the D-09 floor.
                    for lang in ("en", "fr"):
                        seen[lang] = _persist_without_js(
                            browser.new_context, base_url, "/display", "theme", target, read_back,
                            viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                      "value": lang, "url": base_url}])
                    after = read_back()
                    if str(after) != str(before):
                        return False, (
                            "the scripts-blocked save left the theme at %r, it started at %r — "
                            "a harness that changes a real setting edits its neighbours' "
                            "subject" % (after, before))
                    for lang, result in seen.items():
                        if str(result["stored"]) != str(target):
                            return False, (
                                "lang=%s: the theme did not reach disk, it reads %r"
                                % (lang, result["stored"]))
                        if str(result["restored"]) != str(before):
                            return False, (
                                "lang=%s: the restore leg did not put %r back, disk reads %r"
                                % (lang, before, result["restored"]))

                    # 30-08-PLAN.md Task 2 (CFG-85): the property plan
                    # 30-03 ledgered off this narrowed check ("every
                    # registry theme's radio is present") — restated for
                    # the accordion: every registry theme renders
                    # server-side and owes nothing to a script, whether
                    # its own row is OPEN (departures) or CLOSED
                    # (calendar) at load.
                    n_themes = len(device_config.THEME_IDS)
                    with _no_js_page(browser.new_context, base_url, "/display",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        # calendar_theme_id's own group also carries the
                        # leading "Same as departures" radio (D-09) - one
                        # MORE than the registry, unlike theme, which has
                        # no leading option at all.
                        for field, usage, state, expected in (
                                ("theme", "departures", "open", n_themes),
                                ("calendar_theme_id", "calendar", "closed", n_themes + 1)):
                            count = page.eval_on_selector_all(
                                'input[name="%s"]' % field, "els => els.length")
                            if count != expected:
                                return False, (
                                    "with scripts blocked, expected %d radios named %r (the "
                                    "%s row's own palette, %s by default) with no script "
                                    "involvement in rendering it - found %d"
                                    % (expected, field, usage, state, count))
                    return True, ""
                check(
                    "the theme still SAVES with scripts blocked, at 360px and in BOTH shipped "
                    "languages — operated natively by field name, submitted through the real "
                    "form, re-read FROM DISK after a fresh GET and restored the same way "
                    "(CFG-50/D-09/CFG-85, 25-06-PLAN.md Task 4, narrowed by 30-03-PLAN.md Task 3)",
                    _the_theme_still_saves_with_scripts_blocked)

                # --- 27-07-PLAN.md Task 2 (CFG-68): arrivals and
                # calendar fold the same way, and the arrivals grid gets
                # this plan's OWN scripts-blocked save proof — the
                # <no_js_floor> in 27-07-PLAN.md requires proving the
                # fold did not trap a no-JS reader, not merely that it
                # renders. ------------------------------------------

                def _arrivals_still_saves_with_scripts_blocked():
                    # 30-03-PLAN.md Task 3 (CFG-85): NARROWED, not
                    # deleted, same treatment as the departures twin
                    # above. The trailing strip-probe half (arrivals
                    # carousel chip count, overflow, its own disclosure
                    # opening) is LEDGERED to 30-08 — see
                    # _ASPECT_REPIN_LEDGER below.
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir).get("theme_arriving")

                    original_arriving = read_back()
                    # SEED A KNOWN, NON-NONE STARTING VALUE, through the
                    # validated server API (never a raw file write).
                    # theme_arriving's valid value set includes None
                    # ("Same as departures"), and _persist_once()'s own
                    # "stored is None" guard exists to catch a control
                    # that saves NOTHING — it cannot tell that apart
                    # from a deliberate restore-to-None, so starting
                    # from None would make _persist_without_js()'s own
                    # restore leg raise against a CORRECT outcome.
                    # Cleared back to None (via CLEAR_THEME_ARRIVING) as
                    # this check's LAST act if that is where it started.
                    current_theme = device_config.load_device_config(
                        harness.tmpdir)["theme"]
                    seed = next(
                        t for t in device_config.THEME_IDS if t != current_theme)
                    device_config.save_device_config(harness.tmpdir, theme_arriving=seed)
                    before = read_back()
                    if before != seed:
                        return False, (
                            "the seeded theme_arriving did not read back as written: %r"
                            % (before,))
                    target = next(t for t in device_config.THEME_IDS if t != before)

                    try:
                        seen = {}
                        for lang in ("en", "fr"):
                            seen[lang] = _persist_without_js(
                                browser.new_context, base_url, "/display", "theme_arriving", target,
                                read_back, viewport=VIEWPORT_MIN_SUPPORTED,
                                cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                          "value": lang, "url": base_url}])
                        after = read_back()
                        if str(after) != str(before):
                            return False, (
                                "the scripts-blocked save left theme_arriving at %r, it "
                                "started (seeded) at %r — a harness that changes a real "
                                "setting edits its neighbours' subject" % (after, before))
                        for lang, result in seen.items():
                            if str(result["stored"]) != str(target):
                                return False, (
                                    "lang=%s: theme_arriving did not reach disk, it reads %r"
                                    % (lang, result["stored"]))
                            if str(result["restored"]) != str(before):
                                return False, (
                                    "lang=%s: the restore leg did not put %r back, disk "
                                    "reads %r" % (lang, before, result["restored"]))

                        # 30-08-PLAN.md Task 2 (CFG-85): the property
                        # plan 30-03 ledgered off this narrowed check —
                        # restated for the accordion, from the arrivals
                        # twin's own perspective: every registry theme
                        # renders server-side with no script involvement
                        # whether its own row is CLOSED (arrivals, the
                        # default) or OPEN (departures).
                        n_themes = len(device_config.THEME_IDS)
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            # theme_arriving's own group also carries the
                            # leading "Same as departures" radio (D-09) -
                            # one MORE than the registry, unlike theme,
                            # which has no leading option at all.
                            for field, usage, state, expected in (
                                    ("theme_arriving", "arrivals", "closed", n_themes + 1),
                                    ("theme", "departures", "open", n_themes)):
                                count = page.eval_on_selector_all(
                                    'input[name="%s"]' % field, "els => els.length")
                                if count != expected:
                                    return False, (
                                        "with scripts blocked, expected %d radios named %r "
                                        "(the %s row's own palette, %s by default) with no "
                                        "script involvement in rendering it - found %d"
                                        % (expected, field, usage, state, count))

                        return True, ""
                    finally:
                        # LAST ACT: put theme_arriving back exactly
                        # where this check found it, through the SAME
                        # validated server API it was seeded with.
                        if original_arriving is None:
                            device_config.save_device_config(
                                harness.tmpdir,
                                theme_arriving=device_config.CLEAR_THEME_ARRIVING)
                        else:
                            device_config.save_device_config(
                                harness.tmpdir, theme_arriving=original_arriving)
                        final = read_back()
                        if final != original_arriving:
                            raise AssertionError(
                                "restoring theme_arriving failed: wanted %r, disk reads %r"
                                % (original_arriving, final))
                check(
                    "the arrivals grid still SAVES with scripts blocked, at 360px and in BOTH "
                    "shipped languages — operated natively by field name, submitted through "
                    "the real form, re-read FROM DISK after a fresh GET and restored the same "
                    "way (seeded through the validated save_device_config() API rather than a "
                    "raw file write, since theme_arriving's own None state would otherwise "
                    "defeat the shared helper's stored-is-None save-floor guard) (CFG-68/"
                    "CFG-85, 27-07-PLAN.md Task 2, narrowed by 30-03-PLAN.md Task 3)",
                    _arrivals_still_saves_with_scripts_blocked)

                # 30-03-PLAN.md Task 3 (CFG-85): two checks used to live
                # here — _each_carousels_own_disclosure_toggles_only_
                # its_own_strip and _arrivals_and_calendar_keep_the_
                # focused_chip_in_view_when_keyed — both drove real
                # scroll-snap-strip/pager/disclosure interactions that
                # have no equivalent in a wrapping grid. RETIRED
                # OUTRIGHT — no ledger row; scroll-into-view and
                # per-carousel disclosure toggling have no meaning once
                # the strip becomes a native accordion over a static
                # grid.

                # ==========================================================
                # 30-08-PLAN.md Task 2 (CFG-85): the phase's closing
                # browser proofs — the last unproven behaviour (hover/
                # focus preview-follow), the accordion's own scripts-
                # blocked operability, and the measured touch-target
                # floors. Clears every remaining _ASPECT_REPIN_LEDGER row
                # in this file.
                # ==========================================================

                def _keying_the_palette_moves_the_preview():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _keying_the_strip_selects_scrolls_into_view_and_
                    # moves_the_preview. The scroll-into-view and pager
                    # halves of that check's own property have no
                    # equivalent over a static wrapping grid; what
                    # survives, and is proven here, is the part that
                    # never depended on a strip at all: native radiogroup
                    # keyboard navigation (ArrowDown) still moves the
                    # SELECTION, and theme-preview.js's own delegated
                    # change listener still follows it to the live
                    # preview, settled fully opaque.
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        checked_value = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"]:checked', "el => el.value")
                        page.focus(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"][value="%s"]' % checked_value)
                        page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(200)
                        new_value = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"]:checked', "el => el.value")
                        if new_value == checked_value:
                            return False, (
                                "ArrowDown inside the departures palette's native radiogroup "
                                "did not move the checked selection off %r" % (checked_value,))
                        expected_src = page.eval_on_selector(
                            'details.usage-row[data-usage="departures"] '
                            'input[name="theme"][value="%s"]' % new_value,
                            "el => el.closest('.palette-chip').getAttribute('data-preview-src')")
                        try:
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected"
                                " && parseFloat(getComputedStyle(img).opacity) === 1; }",
                                arg={"sel": THEME_PREVIEW_SEL, "expected": expected_src},
                                timeout=3000)
                        except Exception:
                            live_src = page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")
                            return False, (
                                "expected the live preview to settle on %r (the newly "
                                "ArrowDown-selected chip's own data-preview-src), fully opaque, "
                                "after keying the palette with no click at all - it reads %r"
                                % (expected_src, live_src))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "arrow-keying the departures palette's native radiogroup (no click at all) "
                    "still moves the checked selection, and the live preview still follows it "
                    "via theme-preview.js's own delegated change listener, settled fully opaque "
                    "- the one property _keying_the_strip_selects_scrolls_into_view_and_moves_"
                    "the_preview proved that survives a static wrapping grid with no strip/"
                    "scroll/pager to key through (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, "
                    "CFG-85)",
                    _keying_the_palette_moves_the_preview)

                def _the_preview_follows_hover_and_focus_and_selects_nothing():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _scrolling_a_strip_moves_its_own_preview_to_the_
                    # centered_chip_and_selects_nothing. The scroll-to-
                    # centred-chip mechanism that retired check measured
                    # has no meaning once there is nothing to scroll; the
                    # SAME underlying property (the preview can show
                    # something other than the saved selection, non-
                    # destructively) is re-keyed here onto hover and
                    # keyboard focus - theme-preview.js's own genuinely
                    # NEW interaction (30-RESEARCH.md Pitfall 4: there was
                    # no existing hover/focus code to "re-key", this is
                    # new code proven here for the first time).
                    context = browser.new_context(viewport=VIEWPORT_PHONE)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        page.goto(harness.base_url() + "/display")
                        page.wait_for_load_state("networkidle")

                        def read_back():
                            return device_config.load_device_config(harness.tmpdir)["theme"]

                        def preview_src():
                            return page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

                        def checked_value():
                            return page.eval_on_selector(
                                'details.usage-row[data-usage="departures"] '
                                'input[name="theme"]:checked', "el => el.value")

                        # TWO selectors, deliberately, not one: the radio
                        # itself is visually-hidden via `clip-path:
                        # inset(50%)` (this app's own selectable-card
                        # idiom, `_click_control()`'s own docstring),
                        # which clips its hit-testable area to nothing -
                        # a REAL pointer hover (unlike page.focus(), which
                        # does not require actionability) can only ever
                        # land on the wrapping, visible <label>.
                        def chip_label_selector(value):
                            return (
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:has('
                                'input[type=radio][value="%s"])' % value)

                        def chip_selector(value):
                            return (
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip input[type=radio][value="%s"]' % value)

                        def wait_for_src(expected):
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected; }",
                                arg={"sel": THEME_PREVIEW_SEL, "expected": expected},
                                timeout=3000)

                        before_disk = read_back()
                        chips = page.evaluate(
                            "() => [...document.querySelectorAll("
                            "'details.usage-row[data-usage=\"departures\"] "
                            "label.palette-chip')]"
                            ".map(c => ({value: c.querySelector('input[type=radio]').value,"
                            " checked: c.querySelector('input[type=radio]').checked,"
                            " src: c.getAttribute('data-preview-src')}))")
                        checked_chip = next((c for c in chips if c["checked"]), None)
                        unchecked = [c for c in chips if not c["checked"]]
                        if checked_chip is None or len(unchecked) < 2:
                            return False, (
                                "expected one checked departures chip and at least 2 unchecked "
                                "siblings to hover, got checked=%r unchecked=%d"
                                % (checked_chip, len(unchecked)))
                        chip_a, chip_b = unchecked[0], unchecked[1]

                        # --- 1. hovering an unchecked chip previews it,
                        #        and selects nothing -------------------
                        page.hover(chip_label_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        if checked_value() != checked_chip["value"]:
                            return False, (
                                "hovering an unchecked chip changed the CHECKED radio from %r "
                                "to %r - a preview must never become a selection"
                                % (checked_chip["value"], checked_value()))
                        if read_back() != before_disk:
                            return False, "hovering an unchecked chip changed the value ON DISK"

                        # --- moving away reverts to the checked chip ---
                        page.hover("body", position={"x": 2, "y": 2})
                        wait_for_src(checked_chip["src"])

                        # --- 2. the same pair, via keyboard focus ------
                        page.focus(chip_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        if checked_value() != checked_chip["value"]:
                            return False, (
                                "keyboard-focusing an unchecked chip changed the CHECKED radio "
                                "from %r to %r" % (checked_chip["value"], checked_value()))
                        page.eval_on_selector(chip_selector(chip_a["value"]), "el => el.blur()")
                        wait_for_src(checked_chip["src"])

                        # --- 3. chip A -> chip B never flashes the
                        #        checked selection's own src in between -
                        page.hover(chip_label_selector(chip_a["value"]))
                        wait_for_src(chip_a["src"])
                        page.evaluate(
                            "sel => { var img = document.querySelector(sel);"
                            " window.__paletteHoverFrames = [];"
                            " window.__paletteHoverObserver = new MutationObserver("
                            "   function () {"
                            "     window.__paletteHoverFrames.push(img.getAttribute('src'));"
                            "   });"
                            " window.__paletteHoverObserver.observe("
                            "   img, {attributes: true, attributeFilter: ['src']}); }",
                            THEME_PREVIEW_SEL)
                        page.hover(chip_label_selector(chip_b["value"]))
                        wait_for_src(chip_b["src"])
                        page.wait_for_timeout(200)
                        frames = page.evaluate(
                            "() => { window.__paletteHoverObserver.disconnect();"
                            " return window.__paletteHoverFrames; }")
                        if checked_chip["src"] in frames:
                            return False, (
                                "hovering directly from chip A to chip B passed THROUGH the "
                                "checked selection's own src %r before settling on chip B's own "
                                "%r - frames observed: %r"
                                % (checked_chip["src"], chip_b["src"], frames))
                        final_src = preview_src()
                        if final_src != chip_b["src"]:
                            return False, (
                                "expected the preview to end on chip B's own src %r after "
                                "hovering straight from chip A to chip B, got %r"
                                % (chip_b["src"], final_src))

                        # --- disk is unchanged, start to finish --------
                        if read_back() != before_disk:
                            return False, (
                                "the value on disk changed over the course of this check - "
                                "hovering/focusing must never write a selection")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "hovering or keyboard-focusing an unchecked palette chip previews that "
                    "chip's own theme in the ONE live preview, writing NO radio's checked state "
                    "and NO value on disk; moving the pointer/focus away reverts the preview to "
                    "the checked chip's own src; hovering straight from chip A to chip B never "
                    "passes through the checked selection's own src in between (observed via a "
                    "live MutationObserver on the preview's src attribute), settling on B; and "
                    "the value on disk is unchanged start to finish - the genuinely new "
                    "interaction this phase adds, with no existing hover/focus precedent to "
                    "re-key (30-RESEARCH.md Pitfall 4, _ASPECT_REPIN_LEDGER, 30-08-PLAN.md "
                    "Task 1+2, CFG-85)",
                    _the_preview_follows_hover_and_focus_and_selects_nothing)

                def _the_accordion_is_operable_and_saves_with_scripts_blocked():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _the_no_js_floor_holds_for_both_settings_pages (and,
                    # for the "a closed row's radios still reach disk"
                    # half, for _the_theme_still_saves_with_scripts_
                    # blocked_through_the_carousel/_arrivals_still_saves_
                    # with_scripts_blocked_through_its_own_carousel's own
                    # "the <details> disclosure opens on a click" clause).
                    #
                    # CFG-85's own requirement text reads "every row open
                    # with scripts blocked". A grouped <details
                    # name="aspect-rows"> set is mutually exclusive BY
                    # BROWSER CONSTRUCTION, so that literal wording is
                    # UNACHIEVABLE alongside the zero-script accordion the
                    # developer already approved (30-04-SUMMARY.md's own
                    # <two_recorded_deviations> item 2; 30-03-SUMMARY.md's
                    # own <no_js_floor_note>). What is proved here
                    # instead, and is STRONGER than a visible stack:
                    #   1. all four rows are present, each with its own
                    #      <summary>;
                    #   2. every theme radiogroup is present in the DOM
                    #      at FULL REGISTRY SIZE, including inside CLOSED
                    #      rows - the fact that makes a closed row
                    #      harmless;
                    #   3. a closed row's own <summary> is natively
                    #      activatable by a REAL pointer click with
                    #      scripts blocked, and opening it closes the
                    #      previously-open sibling - the native grouped-
                    #      <details> mechanism CFG-85's zero-script floor
                    #      actually rests on;
                    #   4. a palette selection made INSIDE a row the
                    #      visitor opened THEMSELVES reaches disk, read
                    #      back via device_config.load_device_config(),
                    #      with the restore leg putting the old value
                    #      back.
                    # A check that quietly asserted something weaker than
                    # its own requirement's words is the failure shape
                    # this comment exists to head off.
                    base_url = harness.base_url()
                    n_themes = len(device_config.THEME_IDS)

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir).get("calendar_theme_id")

                    for lang in ("en", "fr"):
                        with _no_js_page(browser.new_context, base_url, "/display",
                                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
                            page.context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            # --- 1. every row, every summary ----------
                            rows = page.query_selector_all("details.usage-row")
                            if len(rows) != 4:
                                return False, (
                                    "lang=%s: expected 4 usage rows, found %d"
                                    % (lang, len(rows)))
                            for row in rows:
                                if row.query_selector("summary") is None:
                                    return False, (
                                        "lang=%s: a usage row carries no <summary>" % (lang,))

                            # --- 2. full registry size, even closed ---
                            # theme_arriving/calendar_theme_id each also
                            # carry the leading "Same as departures"
                            # radio (D-09) inside the SAME name group -
                            # one MORE than the registry; theme/
                            # rule_theme_id have no leading option.
                            for field, expected in (
                                    ("theme", n_themes),
                                    ("theme_arriving", n_themes + 1),
                                    ("calendar_theme_id", n_themes + 1),
                                    ("rule_theme_id", n_themes)):
                                count = page.eval_on_selector_all(
                                    'input[name="%s"]' % field, "els => els.length")
                                if count != expected:
                                    return False, (
                                        "lang=%s: expected %d radios named %r in the DOM "
                                        "regardless of which row is open, found %d"
                                        % (lang, expected, field, count))

                            # --- 3. grouped exclusivity, real click ---
                            calendar_row = page.query_selector(
                                'details.usage-row[data-usage="calendar"]')
                            departures_row = page.query_selector(
                                'details.usage-row[data-usage="departures"]')
                            if calendar_row.get_attribute("open") is not None:
                                return False, (
                                    "lang=%s: expected the calendar row closed at load"
                                    % (lang,))
                            if departures_row.get_attribute("open") is None:
                                return False, (
                                    "lang=%s: expected the departures row open at load"
                                    % (lang,))
                            calendar_row.query_selector("summary").click()
                            if calendar_row.get_attribute("open") is None:
                                return False, (
                                    "lang=%s: a real pointer click on a closed row's own "
                                    "<summary> did not open it, with scripts blocked" % (lang,))
                            if departures_row.get_attribute("open") is not None:
                                return False, (
                                    "lang=%s: opening the calendar row did not close its "
                                    "previously-open sibling - the native grouped-<details> "
                                    "behaviour CFG-85's zero-script floor rests on" % (lang,))

                            # --- 4. a selection made in the row the
                            #        visitor just opened reaches disk ---
                            before = read_back()
                            target = next(
                                t for t in device_config.THEME_IDS if t != before)
                            _click_control(
                                page,
                                'input[name="calendar_theme_id"][value="%s"]' % target)
                            held = page.eval_on_selector(
                                'input[name="calendar_theme_id"][value="%s"]' % target,
                                "el => el.checked")
                            if not held:
                                return False, (
                                    "lang=%s: the browser refused to check calendar_theme_id=%r "
                                    "with scripts blocked" % (lang, target))
                            # ARMED before the click, matching
                            # _persist_once()'s own established sequence
                            # — a wait AFTER the click races the
                            # navigation the click itself starts, and
                            # this context's own close() below can abort
                            # an in-flight request that lost that race.
                            with page.expect_navigation():
                                via = page.evaluate(
                                    _SUBMIT_PROBE, {"field": "calendar_theme_id"})

                        stored = read_back()
                        if str(stored) != str(target):
                            return False, (
                                "lang=%s: a selection made inside a row the visitor opened "
                                "themselves (via the %s) did NOT reach disk - expected %r, "
                                "got %r" % (lang, via, target, stored))

                        # --- restore, through the validated server API -
                        # calendar_theme_id=None means "not supplied,
                        # carry forward" at the WRITE path (unlike the
                        # READ path's own normalise_calendar_theme_id(),
                        # which degrades a non-member value TO None) - so
                        # restoring an originally-unset value needs the
                        # empty string, its own documented clear signal,
                        # never the bare None a "leave unchanged" write
                        # would silently no-op against.
                        device_config.save_device_config(
                            harness.tmpdir,
                            calendar_theme_id=before if before is not None else "")
                        restored = read_back()
                        if restored != before:
                            raise AssertionError(
                                "restoring calendar_theme_id failed: wanted %r, disk reads %r"
                                % (before, restored))
                    return True, ""
                check(
                    "with scripts blocked, in BOTH languages, at 360px: all 4 usage rows carry "
                    "their own <summary>; every registry theme's radio (theme/theme_arriving/"
                    "calendar_theme_id/rule_theme_id) is present in the DOM at full registry "
                    "size regardless of which row is open; a REAL pointer click on a closed "
                    "row's own <summary> opens it and closes the previously-open sibling (the "
                    "native grouped <details name=\"aspect-rows\"> mechanism); and a palette "
                    "selection made INSIDE the row the visitor just opened themselves reaches "
                    "disk, read back via device_config.load_device_config(), with the restore "
                    "leg putting the old value back - CFG-85's own \"every row open\" wording is "
                    "unachievable alongside the grouped, mutually-exclusive accordion the "
                    "developer already approved, and this check's own comment states that "
                    "discrepancy plainly rather than narrowing the claim "
                    "(_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)",
                    _the_accordion_is_operable_and_saves_with_scripts_blocked)

                def _the_palette_meets_its_floors_at_360px_in_both_themes():
                    # _ASPECT_REPIN_LEDGER replacement for
                    # _the_carousel_meets_its_floors_at_360px_in_both_
                    # themes. Every geometry/paint assertion the retired
                    # check made was read off the retiring strip/pager
                    # DOM shape directly; this is 30-UI-SPEC.md's own
                    # Touch Targets table, MEASURED (never declared)
                    # fresh against the real .palette-chip/.usage-row/
                    # .leading-option/.rule-add markup.
                    base_url = harness.base_url()
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    recorded = {}
                    try:
                        page = context.new_page()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        def open_row(usage):
                            # IDEMPOTENT, deliberately: a grouped
                            # <details name="aspect-rows"> summary click
                            # TOGGLES, so clicking an ALREADY-open row
                            # (departures, the server's own default)
                            # would CLOSE it rather than leave it open -
                            # measured directly on this tree: a closed
                            # row's own content keeps a real, non-zero
                            # getBoundingClientRect() in this browser
                            # (layout is retained for cheap re-display)
                            # while its PAINT and HIT-TEST are
                            # suppressed, so an unconditional click here
                            # would make _assert_hit_target() report a
                            # spurious "occluded" failure against a row
                            # that was never meant to be closed.
                            row = page.query_selector(
                                'details.usage-row[data-usage="%s"]' % usage)
                            if row.get_attribute("open") is None:
                                row.query_selector("summary").click()

                        for theme in UI_THEMES_EXPLICIT:
                            _set_ui_theme(page, theme)
                            theme_record = {}

                            # --- the open row's FIRST/LAST palette-chip
                            open_row("departures")
                            chip_count = page.eval_on_selector_all(
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip', "els => els.length")
                            if chip_count < 2:
                                return False, (
                                    "theme=%s: expected at least 2 .palette-chip in the open "
                                    "departures row, found %d" % (theme, chip_count))
                            theme_record["chip_first"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:first-of-type',
                                "theme=%s: the FIRST palette-chip in the open departures row"
                                % theme)
                            theme_record["chip_last"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:last-of-type',
                                "theme=%s: the LAST palette-chip in the open departures row"
                                % theme)

                            # --- the usage-row <summary> (always visible)
                            theme_record["row_summary"] = _assert_hit_target(
                                page, 'details.usage-row[data-usage="departures"] > summary',
                                "theme=%s: the departures row's own <summary>" % theme)

                            # --- the arrivals row's leading option -----
                            open_row("arrivals")
                            theme_record["leading_option"] = _assert_hit_target(
                                page,
                                'details.usage-row[data-usage="arrivals"] .leading-option',
                                "theme=%s: the arrivals row's \"Same as departures\" leading "
                                "option" % theme)

                            # --- the nested rule-add <summary> ---------
                            open_row("rules")
                            theme_record["rule_add_summary"] = _assert_hit_target(
                                page, ".rule-add > summary",
                                "theme=%s: the nested \"+ Add rule\" disclosure's own <summary>"
                                % theme)

                            # --- the palette grid never scrolls sideways
                            for usage in ("departures", "arrivals"):
                                open_row(usage)
                                grid = page.eval_on_selector(
                                    'details.usage-row[data-usage="%s"] .palette' % usage,
                                    "el => ({scrollWidth: el.scrollWidth,"
                                    " clientWidth: el.clientWidth})")
                                if grid["scrollWidth"] > grid["clientWidth"]:
                                    return False, (
                                        "theme=%s: the %s row's own .palette grid scrolls "
                                        "horizontally - scrollWidth %r > clientWidth %r, "
                                        "exactly the strip CFG-85 retires"
                                        % (theme, usage, grid["scrollWidth"],
                                           grid["clientWidth"]))

                            # --- the page itself never overflows sideways
                            msg = _assert_no_page_overflow(
                                page, "the Aspect card on /display (theme=%s)" % theme,
                                VIEWPORT_MIN_SUPPORTED["width"])
                            if msg:
                                return False, msg

                            # --- the swatch paints distinct from its
                            #     own surrounding chip surface ----------
                            # Deliberately the "black" theme, not the
                            # FIRST chip: THEME_IDS[0] is "white" (a
                            # solid #FFFFFF fill), and --color-dominant
                            # is ALSO #FFFFFF in light mode (style.css) -
                            # a white swatch on a white card surface is
                            # a REAL, correct product fact (the chip's
                            # own border is what distinguishes it there),
                            # never the "invisible swatch" defect this
                            # clause exists to catch. "black" fills
                            # #000000, which differs from BOTH themes'
                            # own --color-dominant (#FFFFFF light,
                            # #151922 dark).
                            open_row("departures")
                            paint = page.eval_on_selector(
                                'details.usage-row[data-usage="departures"] '
                                'label.palette-chip:has(input[type=radio][value="black"])',
                                "el => { var swatch = el.querySelector('.palette-swatch');"
                                " var chip = getComputedStyle(el);"
                                " return {swatch: getComputedStyle(swatch).backgroundColor,"
                                " chipSurface: chip.backgroundColor}; }")
                            if paint["swatch"] == paint["chipSurface"]:
                                return False, (
                                    "theme=%s: the 'black' palette-chip's own swatch paints "
                                    "IDENTICALLY to its surrounding chip surface (%r) - a "
                                    "swatch invisible against its own card is the defect a "
                                    "hit-target measurement cannot see" % (theme, paint["swatch"]))
                            theme_record["paint"] = paint

                            recorded[theme] = theme_record
                        # 30-08-PLAN.md Task 2's own required artifact:
                        # every measured box, printed for the SUMMARY -
                        # a measurement nobody can read back off the
                        # check's own PASS line otherwise.
                        for theme, rec in recorded.items():
                            for control in (
                                    "chip_first", "chip_last", "row_summary",
                                    "leading_option", "rule_add_summary"):
                                seen = rec[control]
                                print(
                                    "        [30-08 T2] theme=%s %s: hit=%r visual=%r"
                                    % (theme, control, seen["hit"], seen["visual"]))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "30-UI-SPEC.md's Touch Targets table, MEASURED (never declared) in each "
                    "control's own container, in both UI themes, at the 360px contract floor: "
                    "the open row's first and last .palette-chip, the usage-row's own <summary>, "
                    "the arrivals row's leading \"Same as departures\" option, and the nested "
                    "rule-add disclosure's own <summary> all clear 44px; the palette grid never "
                    "scrolls horizontally, the page itself never overflows sideways, and the "
                    "swatch paints visibly distinct from its own surrounding chip surface in "
                    "both themes (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85)",
                    _the_palette_meets_its_floors_at_360px_in_both_themes)

                # --- 27-03-PLAN.md Task 3 (CFG-64) -----------------------

                def _the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies():
                    """CFG-64: 27-03-PLAN.md Task 2 reverted the
                    fallback-hide rule from the two-marker
                    `.dirty-ready.dirty-shown` gate to the plain `.js`
                    gate 06.6.4.1-01 originally shipped. This is the
                    proof that the floor UNDER that change still holds —
                    a value on DISK, never a rendering — using
                    tracked_runway, the same field and the same
                    form="settings-form" mutation 25-03's own M20
                    recorded (25-03-SUMMARY.md), because the subject
                    under test is the identical no-JS save path, now
                    reached through a simplified gate rather than a
                    proven-live save bar.

                    Unlike 25-03's own check, which corroborates with the
                    runway MAP's presence, this one asserts the SUBMIT
                    itself — the element the simplified gate actually
                    governs — is present and VISIBLE AFTER the save. A
                    check that only asked whether it renders would pass
                    against the exact defect Phase 22's P0 found; a check
                    that only asked whether it renders would ALSO pass
                    against a submit whose value never reaches disk. This
                    check carries both facts about the one relationship
                    that matters, deliberately never split into two.
                    """
                    base_url = harness.base_url()

                    def read_back():
                        return device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"]

                    before = read_back()
                    target = next(r for r in device_config.RUNWAY_IDS if r != before)
                    seen = {}
                    # BOTH SHIPPED LANGUAGES, at the 360px floor: the UI
                    # language is a cookie the FIRST rendered document
                    # already has to honour, and "it saves in English" is
                    # not the D-09 floor.
                    for lang in ("en", "fr"):
                        seen[lang] = _persist_without_js(
                            browser.new_context, base_url, "/display", "tracked_runway",
                            target, read_back, viewport=VIEWPORT_MIN_SUPPORTED,
                            cookies=[{"name": auth.UI_LANG_COOKIE_NAME,
                                      "value": lang, "url": base_url}])
                    after = read_back()
                    if str(after) != str(before):
                        return False, (
                            "the scripts-blocked save left tracked_runway at %r, it started at "
                            "%r — a harness that changes a real setting is a test that edits "
                            "its neighbours' subject" % (after, before))
                    for lang, result in seen.items():
                        if str(result["stored"]) != str(target):
                            return False, (
                                "lang=%s: tracked_runway did not reach disk, it reads %r"
                                % (lang, result["stored"]))
                        if str(result["restored"]) != str(before):
                            return False, (
                                "lang=%s: the restore leg did not put %r back, disk reads %r"
                                % (lang, before, result["restored"]))

                    # AND THE SUBMIT ITSELF, ASSERTED AFTER THE SAVE
                    # ABOVE — never before, and never in its place. A
                    # rendering can never stand in for the save this
                    # check just proved.
                    with _no_js_page(browser.new_context, base_url, "/display",
                                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
                        submit = page.locator(
                            "[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)
                        if submit.count() != 1:
                            return False, (
                                "expected exactly one fallback submit with scripts blocked "
                                "AFTER the save above, found %d" % submit.count())
                        if not submit.is_visible():
                            return False, (
                                "the fallback submit rendered but is not VISIBLE with scripts "
                                "blocked after the save — this is precisely the shape Phase "
                                "22's P0 took")
                    return True, ""
                check(
                    "the no-JS floor still SAVES TO DISK after the gate simplifies to the "
                    "plain .js rule (CFG-64) — tracked_runway operated natively, submitted "
                    "through the real form, re-read FROM DISK after a fresh GET, in BOTH "
                    "shipped languages, at 360px, restored as the last act (the same field and "
                    "mutation 25-03's own M20 recorded) — and the data-static-save-fallback "
                    "submit is present and VISIBLE on that scripts-blocked page AFTER the save, "
                    "so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3)",
                    _the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies)

                # ==========================================================
                # 27-04-PLAN.md Task 4 (CFG-63/CFG-71): THE two checks —
                # a scripted save proven on disk, and its failure proven
                # honest. Two endpoints (a DOM read and a disk read) are
                # not a relationship; this plan's whole discipline is to
                # assert them as ONE.
                # ==========================================================

                def _the_bar_settles_the_field_disk_agree_and_the_bar_hides():
                    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not
                    # a mechanical swap — this check's own retired-region
                    # ordering clause is gone with the region, and its
                    # never-visible-save-button clauses asserted CFG-63's
                    # own "no save button" contract verbatim, which THIS
                    # phase reverses. Left mechanical, it would either fail
                    # immediately or, worse, "fixed" by loosening the
                    # selector, pass while asserting the opposite of the
                    # current requirement. Rewritten as the bar's own
                    # settle contract, keeping the three-way agreement
                    # shape (field / bar / disk) that was worth
                    # preserving, on different surfaces.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/display")

                        # Precondition: the bar starts hidden (script has
                        # proven itself live).
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_visible():
                            return False, "expected the bar to be hidden before any edit"

                        before = str(device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"])
                        target = next(
                            r for r in device_config.RUNWAY_IDS if r != before)

                        # a. CHANGE A FIELD: the bar reveals, the count
                        # names the section, the field shows the new
                        # value, and disk STILL shows the OLD value — the
                        # bar means *unsaved*, and asserting disk is
                        # untouched at this point is strictly stronger
                        # than anything the retired check ever asserted.
                        _click_control(page, 'input[name="tracked_runway"][value="%s"]' % target)
                        _wait_for_bar(page)
                        if not _bar_text(page):
                            return False, (
                                "expected [data-dirty-count] to name the changed section once "
                                "the bar reveals")
                        field_now = str(page.eval_on_selector(
                            'input[name="tracked_runway"]:checked', "el => el.value"))
                        if field_now != target:
                            return False, (
                                "expected the field's own DOM value to already read %r, got %r"
                                % (target, field_now))
                        disk_before_save = str(device_config.load_device_config(
                            harness.tmpdir)["tracked_runway"])
                        if disk_before_save != before:
                            return False, (
                                "expected disk to still read %r while the bar is visible and "
                                "unsaved, got %r — the bar means UNSAVED" % (before, disk_before_save))

                        # b. CLICK ENREGISTRER — a real navigation.
                        _save_via_bar(page)

                        # c. AFTER THE NAVIGATION: field, bar and disk all
                        # agree on the new value — three surfaces, same
                        # shape as the retired check's own field/disk
                        # agreement, now including the bar's own hidden
                        # state as the third.
                        _assert_surfaces_agree(
                            page,
                            {
                                "the field's own DOM value": lambda: str(page.eval_on_selector(
                                    'input[name="tracked_runway"]:checked', "el => el.value")),
                                "the value on disk": lambda: str(device_config.load_device_config(
                                    harness.tmpdir)["tracked_runway"]),
                            },
                            requested=target, before=before,
                            where="Display's runway card after the bar's own save settles")
                        if page.locator("[data-dirty-bar]").is_visible():
                            return False, (
                                "expected the bar to be HIDDEN after the navigation lands — a "
                                "bar still visible after a successful save means the save was "
                                "never recorded as settled")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the bar's own settle contract: changing a field REVEALS the bar, names the "
                    "changed section, updates the field's own DOM value, and leaves DISK "
                    "UNTOUCHED (the bar means unsaved, stronger than anything the retired check "
                    "asserted); clicking Enregistrer causes a real navigation; and after it lands "
                    "the field, the bar (now HIDDEN) and disk all agree on the requested value — "
                    "three surfaces, on different surfaces than before (CFG-63/CFG-71/CFG-77/"
                    "CFG-78, 27-04-PLAN.md Task 4; retargeted onto the restored bar by "
                    "28-10-PLAN.md Task 2, which also retires the CFG-63 'no save button visible' "
                    "clause this check used to assert)",
                    _the_bar_settles_the_field_disk_agree_and_the_bar_hides)

                def _a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched():
                    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED —
                    # the failure surface changed from a toast to an
                    # inline error. The settings form no longer raises
                    # .quick-toast at all; announceFailure() is
                    # EXCLUSIVELY quick-switch.js's now, serving the
                    # three role="switch" controls. A rejected value
                    # re-renders the SAME page at 200 with the field's
                    # OWN inline error (_field_error_html()'s existing
                    # D-07 shape), echoes the user's rejected text back
                    # so they can fix it rather than retype it, and
                    # leaves disk untouched — the two surviving clauses
                    # ("claims nothing", "disk is untouched") kept at
                    # full strength; the toast clause replaced with the
                    # inline-error one, plus an explicit NEGATIVE that no
                    # toast appears on this path at all, so the two
                    # failure mechanisms (this one and quick-switch.js's
                    # own) cannot be accidentally re-merged later.
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/device")

                        before = str(device_config.load_device_config(
                            harness.tmpdir)["wake_interval_s"])
                        # Below server/device_config.py's own WAKE_INTERVAL_MIN_S
                        # (60) — a genuine server-side rejection, exercising
                        # the 200-is-not-a-redirect branch, never a
                        # client-side shortcut.
                        rejected = "30"

                        wake_sel = 'input[name="wake_interval_s"]'
                        page.eval_on_selector(wake_sel, "el => el.focus()")
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.type(rejected)
                        page.keyboard.press("Tab")
                        _wait_for_bar(page)
                        # config_page.py's own wake_interval_group()
                        # comment documents this exact hazard: the native
                        # <input type="number" min="%d" max="%d"> means an
                        # out-of-range value fails HTML5 constraint
                        # validation, which blocks the browser from ever
                        # SUBMITTING the form at all — no request reaches
                        # the server, so this check's own subject (the
                        # SERVER's own rejection path) would never run.
                        # The real production hazard this validates
                        # against is a pre-existing out-of-range value
                        # already on disk/env (config_page.py's own
                        # comment names SKYPANE_SLEEP_S=30), which never
                        # goes through this client-side gate at all.
                        # noValidate disables only the BROWSER's own
                        # pre-flight check for this one native submit —
                        # the request that follows is still a REAL native
                        # POST, never a fetch shortcut, so the server's
                        # own validation is what is actually exercised.
                        page.eval_on_selector(
                            "#%s" % config_page.SETTINGS_FORM_ID,
                            "el => { el.noValidate = true; }")
                        _save_via_bar(page)

                        # 1. THE INLINE ERROR IS PRESENT AND NAMES THE
                        # FIELD — the field's own aria-describedby points
                        # at it (programmatic association, D-07/
                        # _field_error_attrs(), never merely visual
                        # adjacency), and its own text is non-empty.
                        described_by = page.get_attribute(wake_sel, "aria-describedby") or ""
                        if "wake-interval-s-error" not in described_by:
                            return False, (
                                "expected %r's own aria-describedby to name its error anchor "
                                "(wake-interval-s-error), got %r" % (wake_sel, described_by))
                        error_el = page.locator("#wake-interval-s-error")
                        if not error_el.count() or not (error_el.inner_text() or "").strip():
                            return False, (
                                "expected a non-empty inline error at #wake-interval-s-error")

                        # 2. THE USER'S REJECTED INPUT IS ECHOED BACK —
                        # not the on-disk value — so they can fix it
                        # rather than retype it (D-07's echo rule).
                        echoed = page.input_value(wake_sel)
                        if echoed != rejected:
                            return False, (
                                "expected the field to echo back the user's own rejected input "
                                "%r, got %r" % (rejected, echoed))

                        # 3. DISK IS UNTOUCHED — kept at full strength
                        # from the retired check.
                        stored = str(device_config.load_device_config(
                            harness.tmpdir)["wake_interval_s"])
                        if stored == rejected:
                            return False, (
                                "the rejected value %r reached disk — a validation failure must "
                                "never be mistaken for a save" % (rejected,))
                        if stored != before:
                            return False, (
                                "expected the stored wake interval to stay UNCHANGED at %r after "
                                "a rejected save, got %r" % (before, stored))

                        # 4. THE EXPLICIT NEGATIVE — no .quick-toast on
                        # this path at all. quick-switch.js's own
                        # TOAST_ATTR element renders PRESENT but
                        # class="quick-toast" (no "is-visible") by
                        # default — Playwright's own is_visible() would
                        # still call that VISIBLE (a non-empty box at
                        # opacity: 0 is not display:none/visibility:
                        # hidden), so the class itself, the same idiom
                        # announceFailure() uses to reveal it, is what
                        # this check has to read.
                        toast_class = page.eval_on_selector(
                            "body", "el => { var t = el.querySelector('[data-quick-toast]'); "
                            "return t ? t.className : null; }")
                        if toast_class and "is-visible" in toast_class.split():
                            return False, (
                                "expected NO .quick-toast on the settings form's own "
                                "rejected-value path — announceFailure() is exclusively "
                                "quick-switch.js's now, got class=%r" % (toast_class,))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a value the server's own validation rejects (wake_interval_s below its "
                    "floor) re-renders the SAME page with the field's OWN inline error, "
                    "programmatically associated via aria-describedby and naming the field; "
                    "echoes the user's rejected input back into the field rather than the "
                    "on-disk value (D-07's echo rule); leaves disk UNCHANGED; and raises NO "
                    ".quick-toast at all on this path — the explicit negative that keeps this "
                    "failure surface and quick-switch.js's own toast from merging (CFG-63/"
                    "CFG-71, 27-04-PLAN.md Task 4; retargeted from the toast onto the native "
                    "inline-error path by 28-10-PLAN.md Task 3, CFG-77/CFG-78)",
                    _a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched)

                # 30-03-PLAN.md Task 3 (CFG-85): two checks used to live
                # here — _keying_the_strip_selects_scrolls_into_view_and_
                # moves_the_preview and _scrolling_a_strip_moves_its_own_
                # preview_to_the_centered_chip_and_selects_nothing — both
                # drove real scroll-snap-strip geometry (scroll-into-view
                # on arrow-key selection, geometric-centre scroll-tracking
                # for the preview) that has no equivalent over a static
                # wrapping grid. RETIRED, and LEDGERED to 30-08: keying's
                # surviving half (arrow-keying the radiogroup still moves
                # the preview) and scrolling's surviving half (preview-is-
                # not-selection: hover/focus previews a theme and never
                # writes a radio, a change event or a form value) — see
                # _ASPECT_REPIN_LEDGER below.


                # --- 28-11-PLAN.md Task 1 (CFG-77): the section-naming
                # relationship — CFG-77 says the bar names the changed
                # section(s), in document order, not click order. A check
                # that merely asserted the bar became visible would pass
                # against a bar stuck on its raw-count fallback branch
                # ("1 unsaved change" forever, dirty-state.js's own
                # updateBar()), which is not this clause.
                def _section_naming_reflects_the_fields_actually_changed_in_document_order():
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            def wait_for_bar_text(expected, timeout=5000):
                                page.wait_for_function(
                                    "args => {"
                                    " var el = document.querySelector('[data-dirty-count]');"
                                    " return !!el && el.textContent === args.expected;}",
                                    arg={"expected": expected}, timeout=timeout)

                            runway_sel = 'input[name="tracked_runway"]'
                            current_runway = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            target_runway = next(
                                r for r in device_config.RUNWAY_IDS if r != current_runway)

                            current_quiet_start = page.input_value(
                                'input[name="quiet_hours_start"]')
                            target_quiet_start = (
                                "05:00" if current_quiet_start != "05:00" else "06:00")

                            # Built from the bar's OWN data-dirty-* words
                            # and each section wrapper's OWN label —
                            # never a hardcoded English/French literal, so
                            # this check works unchanged in either
                            # language (the suite's existing D-06 idiom).
                            runway_label = page.eval_on_selector(
                                runway_sel,
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            quiet_label = page.eval_on_selector(
                                'input[name="quiet_hours_start"]',
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            changed_suffix = page.eval_on_selector(
                                "[data-dirty-bar]",
                                "el => el.getAttribute('data-dirty-changed-suffix')")
                            and_word = page.eval_on_selector(
                                "[data-dirty-bar]", "el => el.getAttribute('data-dirty-and')")

                            expected_one = runway_label + changed_suffix
                            expected_two = (
                                runway_label + and_word + quiet_label + changed_suffix)

                            # Phase A: ONE changed field (Runway). The bar
                            # names ONLY it.
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))
                            _wait_for_bar(page)
                            actual_one = _bar_text(page)
                            if actual_one != expected_one:
                                return False, (
                                    "lang=%s: expected [data-dirty-count] to read %r for a "
                                    "single changed field (Runway), got %r"
                                    % (lang, expected_one, actual_one))

                            # Phase B: ALSO change a Quiet hours field.
                            # The bar names BOTH, Runway before Quiet
                            # hours — DOCUMENT order (Runway's own
                            # [data-dirty-section] wrapper precedes Quiet
                            # hours' on the Display page). Runway was
                            # clicked first in THIS pass too, so this
                            # alone cannot distinguish document order from
                            # click order — the reversed pass below does.
                            page.fill(
                                'input[name="quiet_hours_start"]', target_quiet_start)
                            _commit_field(page, 'input[name="quiet_hours_start"]')
                            wait_for_bar_text(expected_two)

                            # Fresh load, REVERSED click order: Quiet
                            # hours first, Runway second. dirtySection
                            # Labels() walks the DOCUMENT, so the bar must
                            # still read Runway before Quiet hours — a
                            # CLICK-order implementation would pass the
                            # first ordering above and fail THIS one.
                            page.goto(base_url + "/display")
                            page.fill(
                                'input[name="quiet_hours_start"]', target_quiet_start)
                            _commit_field(page, 'input[name="quiet_hours_start"]')
                            _wait_for_bar(page)
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))
                            wait_for_bar_text(expected_two)
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the bar's own [data-dirty-count] names which section(s) actually changed, "
                    "built from the bar's own data-dirty-* attributes plus each section "
                    "wrapper's own label — never hardcoded English/French, never merely 'the "
                    "bar is visible' or 'the text is non-empty': a single changed Runway field "
                    "reads exactly that wrapper's own label plus the changed-suffix, and a "
                    "second, different-section change (Quiet hours) reads the two-item join "
                    "with Runway BEFORE Quiet hours in BOTH click orders — the reversed-order "
                    "pass is what proves DOCUMENT order rather than click order, since "
                    "dirtySectionLabels() walks the document and Runway's own wrapper precedes "
                    "Quiet hours' on Display regardless of which the visitor touches first; run "
                    "in both site languages (CFG-77, 28-11-PLAN.md Task 1)",
                    _section_naming_reflects_the_fields_actually_changed_in_document_order)

                # --- 28-11-PLAN.md Task 2 (CFG-77): Cancel's side
                # effects, read off the RESULTING DOM — never by spying on
                # refresh()/repaintAll(). 28-08 built the mechanism (a
                # single setTimeout(fn, 0) deferred tick inside
                # dirty-state.js's reset handler, calling BOTH
                # window.SkyPaneLivePreview.refresh() and
                # value-controls.js's exported repaintAll() once the
                # native reset has actually restored the fields); this
                # check proves the DOM STATE that mechanism produces.
                #
                # CONTEXT.md separately claimed the quiet-hours dial
                # repaints "for free" because value-controls.js's
                # document-level click listener fires on the Cancel
                # button's own click. That claim is FALSE BY
                # SPECIFICATION, already refuted in writing by 28-08: a
                # click on a <button type="reset"> dispatches and bubbles
                # to COMPLETION before the button's own default action —
                # the reset — runs, so that listener repaints the dial
                # from the EDITED values the user just asked to discard.
                # This check does not re-open that as an empirical
                # question; Mutation 2 (see this plan's own SUMMARY)
                # records the stale-repaint observation as CORROBORATION
                # of 28-08's spec argument, never as a fresh finding.
                def _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        page.goto(base_url + "/display")

                        def handle_values():
                            return (
                                int(page.get_attribute(
                                    _handle_sel("quiet_hours_start"), "aria-valuenow")),
                                int(page.get_attribute(
                                    _handle_sel("quiet_hours_end"), "aria-valuenow")),
                            )

                        def preview_src():
                            return page.eval_on_selector(
                                THEME_PREVIEW_SEL, "el => el.getAttribute('src')")

                        # --- Setup: record the pre-edit state of every
                        # surface, off the DOM.
                        original_theme = page.eval_on_selector(
                            'input[name="theme"]:checked', "el => el.value")
                        original_preview_src = preview_src()
                        original_arc = _quiet_arc_minutes(page, "before the edit")
                        original_handles = handle_values()

                        target_theme = next(
                            t for t in device_config.THEME_IDS if t != original_theme)
                        # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from
                        # .theme-chip to .palette-chip - the departures
                        # radio's own wrapping label class changed under
                        # the accordion rebuild, the data-preview-src
                        # attribute it carries did not.
                        target_preview_src = page.eval_on_selector(
                            'input[name="theme"][value="%s"]' % target_theme,
                            "el => el.closest('.palette-chip')"
                            ".getAttribute('data-preview-src')")

                        current_start = page.input_value(
                            'input[name="quiet_hours_start"]')
                        target_start = "05:00" if current_start != "05:00" else "06:00"

                        # --- Edit: a DIFFERENT theme via a carousel chip,
                        # AND a different quiet-hours window. Confirm both
                        # surfaces actually MOVED before Cancel — a no-op
                        # edit would make every assertion below vacuous.
                        _click_control(
                            page, 'input[name="theme"][value="%s"]' % target_theme)
                        _wait_for_bar(page)
                        page.wait_for_function(
                            "args => { var img = document.querySelector(args.sel);"
                            " return !!img && img.getAttribute('src') === args.expected; }",
                            arg={"sel": THEME_PREVIEW_SEL, "expected": target_preview_src})

                        page.fill('input[name="quiet_hours_start"]', target_start)
                        _commit_field(page, 'input[name="quiet_hours_start"]')

                        moved_arc = _quiet_arc_minutes(page, "after the edit, before Cancel")
                        moved_handles = handle_values()
                        if moved_arc == original_arc or moved_handles == original_handles:
                            return False, (
                                "the quiet-hours edit did not move the dial before Cancel: arc "
                                "%r -> %r, handles %r -> %r — a no-op edit proves nothing about "
                                "Cancel"
                                % (original_arc, moved_arc, original_handles, moved_handles))

                        # --- Cancel: a real click on the native
                        # type="reset" button, exercising both the native
                        # reset and 28-08's scripted enhancement at once.
                        page.click("[data-dirty-cancel]")
                        _wait_for_bar_hidden(page)

                        # a. The theme chip's checked state is back to
                        #    the original.
                        try:
                            page.wait_for_function(
                                "args => {"
                                " var f = document.querySelector("
                                "   'input[name=\"theme\"]:checked');"
                                " return !!f && f.value === args.expected; }",
                                arg={"expected": original_theme}, timeout=3000)
                        except Exception:
                            restored_theme = page.eval_on_selector(
                                'input[name="theme"]:checked', "el => el.value")
                            return False, (
                                "expected the theme radio to be restored to %r after Annuler, "
                                "got %r" % (original_theme, restored_theme))

                        # b. The live preview's <img> resolved src is back
                        #    to the ORIGINALLY-selected theme's own — the
                        #    clause that proves
                        #    window.SkyPaneLivePreview.refresh() actually
                        #    ran, since form.reset() fires no change event
                        #    and the preview cannot repaint on its own.
                        #    Waited for on the deferred tick, never read
                        #    synchronously right after the click.
                        try:
                            page.wait_for_function(
                                "args => { var img = document.querySelector(args.sel);"
                                " return !!img && img.getAttribute('src') === args.expected; }",
                                arg={
                                    "sel": THEME_PREVIEW_SEL, "expected": original_preview_src},
                                timeout=3000)
                        except Exception:
                            return False, (
                                "expected the live preview's src to be back to the "
                                "originally-selected theme's own %r after Annuler (proving "
                                "window.SkyPaneLivePreview.refresh() actually ran), it still "
                                "reads %r" % (original_preview_src, preview_src()))

                        # c. The quiet-hours dial's decoded arc AND its
                        #    handles' aria-valuenow are back to the
                        #    PRE-EDIT window — 28-08's own explicit
                        #    deferred repaint of value-controls.js's
                        #    repaintAll(), proven by the DOM STATE it
                        #    produces, never by asserting the function was
                        #    called.
                        try:
                            page.wait_for_function(
                                "args => {"
                                " var s = document.querySelector(args.sSel);"
                                " var e = document.querySelector(args.eSel);"
                                " return !!s && !!e"
                                "   && s.getAttribute('aria-valuenow') === String(args.s)"
                                "   && e.getAttribute('aria-valuenow') === String(args.e); }",
                                arg={
                                    "sSel": _handle_sel("quiet_hours_start"),
                                    "eSel": _handle_sel("quiet_hours_end"),
                                    "s": original_handles[0], "e": original_handles[1]},
                                timeout=3000)
                        except Exception:
                            return False, (
                                "expected the quiet-hours handles' aria-valuenow to be back to "
                                "%r after Annuler (28-08's deferred repaint of "
                                "value-controls.js's repaintAll()), still read %r"
                                % (original_handles, handle_values()))
                        restored_arc = _quiet_arc_minutes(
                            page, "after Annuler, once the deferred tick has run")
                        if restored_arc != original_arc:
                            return False, (
                                "expected the quiet-hours dial's decoded arc to be back to %r "
                                "after Annuler, got %r" % (original_arc, restored_arc))

                        # d. The bar is hidden — asserted above via
                        #    _wait_for_bar_hidden(), the SYNCHRONOUS half
                        #    of the reset handler.
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a real Annuler click restores every surface, read off the RESULTING DOM: "
                    "the theme chip's checked state is back to the original, the live preview "
                    "<img>'s resolved src is back to the ORIGINALLY-selected theme's own (never "
                    "the discarded one) — proving window.SkyPaneLivePreview.refresh() actually "
                    "ran, since form.reset() fires no change event — and the quiet-hours dial's "
                    "decoded arc and its handles' aria-valuenow are back to the pre-edit window, "
                    "proving 28-08's own explicit deferred repaint of value-controls.js's "
                    "repaintAll() landed; both edits are confirmed to have actually MOVED both "
                    "surfaces before Cancel is ever clicked, and every post-Cancel read waits "
                    "for 28-08's setTimeout(fn, 0) deferred tick rather than reading "
                    "synchronously after the click; asserting that refresh()/repaintAll() was "
                    "CALLED is explicitly not acceptable and this check never does — the "
                    "dial-repaints-for-free claim CONTEXT.md made is false by specification "
                    "(already refuted in writing by 28-08) and this check does not re-litigate "
                    "it (CFG-77, 28-11-PLAN.md Task 2; re-pointed to .palette-chip by "
                    "30-08-PLAN.md Task 2, CFG-85)",
                    _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom)

                # 30-03-PLAN.md Task 3 (CFG-85): the check that used to
                # live here — _the_carousel_meets_its_floors_at_360px_
                # in_both_themes — measured the strip/pager control's
                # touch targets, geometry, overflow and paint floors.
                # LEDGERED to 30-08 (replacement:
                # _the_palette_meets_its_floors_at_360px_in_both_themes)
                # — the replacement measures the four controls in
                # 30-UI-SPEC.md's Touch Targets table by real
                # hit-testing in their own containers, the same
                # discipline this check used. See _ASPECT_REPIN_LEDGER
                # below. This is also the shared selector block's LAST
                # consumer of THEME_STRIP_SEL/THEME_PAGERS_SEL/
                # THEME_DETAILS_SEL/_STRIP_PROBE/_SETTLE_CAROUSEL —
                # deleted below, together with it.

                # ==========================================================
                # 28-04-PLAN.md Task 2 (CFG-72): THE real proof. 27-06's own
                # markup-level inventory (test_config_page.py's structural
                # check) is explicitly insufficient — that is CFG-72's whole
                # lesson, and it is exactly how this defect shipped in the
                # first place: 27-06 counted class names and never once
                # rendered Display and Device side by side to read what the
                # browser actually painted. This check does that: ONE probe
                # loads both settings pages in one session, reads
                # getComputedStyle on every settings-card title, and asserts
                # the two pages' sets are equal.
                # ==========================================================

                _SETTINGS_CARD_TITLE_SELECTOR = (
                    ".theme-status > h2.text-heading, .page-section > h2.text-heading")

                def _settings_card_title_probe(page):
                    """Every settings-card title on the CURRENTLY LOADED
                    settings page, addressed by STRUCTURAL POSITION — the
                    `<h2>` that is a direct child of a `.theme-status`/
                    `.page-section` settings-card wrapper — never by class
                    name. Addressing by class name is the exact move that
                    let 27-06 miss this defect (its own inventory grouped
                    by `.text-heading`, which every h2 on this page
                    carries, card title and supersection intro alike).

                    A supersection's own intro heading
                    (`.section-intro > h2`) is EXCLUDED, structurally
                    rather than by an explicit `:not()`: it lives under
                    `.section-intro`, never directly under
                    `.theme-status`/`.page-section`, so the selector above
                    never reaches it. That exclusion is deliberate — a
                    supersection intro is a different, generically-worded
                    role (companion/test_config_page.py's own title-form
                    inventory, 27-06-PLAN.md Task 1, and SKILL.md's
                    three-rung heading ladder both document why) — not an
                    oversight this check should "fix" into asserting the
                    ladder away.
                    """
                    return page.evaluate(
                        "sel => Array.from(document.querySelectorAll(sel)).map(h => {"
                        "  var s = getComputedStyle(h);"
                        "  return {text: h.textContent, fontSize: s.fontSize,"
                        "          fontWeight: s.fontWeight, fontFamily: s.fontFamily};"
                        "})", _SETTINGS_CARD_TITLE_SELECTOR)

                def _a_settings_card_title_renders_identically_on_both_settings_pages():
                    context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()

                        # Every (page, theme) combination this app can
                        # paint a settings-card title in, all folded into
                        # ONE combined set below — never compared pairwise,
                        # so a third, page-local variant cannot hide.
                        entries = []
                        by_page = {"/display": [], "/device": []}
                        for theme in UI_THEMES_EXPLICIT:
                            for route in ("/display", "/device"):
                                page.goto(base_url + route)
                                _set_ui_theme(page, theme)
                                for title in _settings_card_title_probe(page):
                                    triple = (
                                        title["fontSize"], title["fontWeight"],
                                        title["fontFamily"])
                                    entry = {
                                        "page": route, "theme": theme,
                                        "text": title["text"], "triple": triple}
                                    entries.append(entry)
                                    by_page[route].append(entry)

                        # Clause (a): BOTH sides non-empty, naming the
                        # empty one — a comparator with an empty side
                        # passes vacuously, which is how a grep-level
                        # check misses a rendering defect.
                        for route, side in by_page.items():
                            if not side:
                                return False, (
                                    "expected at least one settings-card title on %s, got "
                                    "NONE — a comparator with an empty side would pass "
                                    "vacuously" % route)

                        # Device must contribute exactly the four NAMED
                        # cards — a probe that silently missed the Poll
                        # card (which reaches the page by a different
                        # route from the other three, outside `builders`
                        # entirely, through a `.page-section` wrapper
                        # rather than `.theme-status` like its siblings)
                        # would pass this check while leaving CFG-72
                        # unmet on a card the developer can see — the
                        # shape of miss 27-06 made. Two properties, NOT
                        # an exact-four-count: (i) every title found is
                        # one of the four canonical names (no unrelated
                        # heading — e.g. a supersection intro — leaked
                        # in), and (ii) the Poll card's OWN title is
                        # specifically among them, proving the probe's
                        # reach extends past the three `.theme-status`
                        # cards to the one `.page-section` card too.
                        # Deliberately NOT "exactly four": M-C
                        # (28-04-PLAN.md Task 2) removes one Device card
                        # from `builders` on purpose and this check must
                        # still PASS on the genuinely smaller set that
                        # produces — proof the comparator is not
                        # secretly COUNTING rather than comparing.
                        allowed_device_texts = {
                            config_page.LED_SECTION_HEADING,
                            config_page.WAKE_INTERVAL_SECTION_HEADING,
                            config_page.NOTIFICATIONS_SECTION_HEADING,
                            config_page.POLL_SECTION_HEADING}
                        device_texts = {e["text"] for e in by_page["/device"]}
                        unexpected = device_texts - allowed_device_texts
                        if unexpected:
                            return False, (
                                "expected every Device settings-card title to be one of %r, "
                                "found unexpected title(s) %r — a probe addressing titles by "
                                "class name rather than structural position would pick up "
                                "supersection intro headings too, which is exactly the "
                                "27-06-shaped mistake this check exists to avoid"
                                % (sorted(allowed_device_texts), sorted(unexpected)))
                        if config_page.POLL_SECTION_HEADING not in device_texts:
                            return False, (
                                "expected the Poll card's own title (%r) among Device's "
                                "settings-card titles — it reaches the page through a "
                                ".page-section wrapper, not .theme-status like the other "
                                "three, and a probe that silently misses it would pass this "
                                "check while leaving CFG-72 unmet on a card the developer "
                                "can see" % config_page.POLL_SECTION_HEADING)

                        # Clause (b): the combined set's own cardinality is
                        # 1 — one typographic form for a settings-card
                        # title, CFG-72's literal wording.
                        triples = sorted({e["triple"] for e in entries})
                        if len(triples) != 1:
                            majority = collections.Counter(
                                e["triple"] for e in entries).most_common(1)[0][0]
                            offender = next(
                                e for e in entries if e["triple"] != majority)
                            # Clause (c): the message names the offending
                            # page, the offending title's text, and BOTH
                            # triples — "titles differ" is not diagnostic.
                            return False, (
                                "expected exactly one (font-size, font-weight, font-family) "
                                "triple across every settings-card title on both settings "
                                "pages, got %d distinct triples — %r on %s (theme=%s) "
                                "renders %r, while the rest render %r"
                                % (len(triples), offender["text"], offender["page"],
                                   offender["theme"], offender["triple"], majority))
                        return True, ""
                    finally:
                        context.close()
                check(
                    "THE real proof, not a grep: ONE probe renders BOTH settings pages "
                    "(Display and Device) in one session, addresses every settings-card title "
                    "by STRUCTURAL POSITION rather than by class name, reads its "
                    "getComputedStyle font-size/font-weight/font-family, and asserts the "
                    "combined set across both pages has cardinality 1 — CFG-72's literal "
                    "wording. Fails naming the empty side if either page contributes zero "
                    "titles; every Device title must be one of the four named cards "
                    "(Diagnostic LED, Wake interval, Notifications, Manual refresh) and the "
                    "Poll card's own title specifically must be among them — proving the "
                    "probe's reach extends to the one .page-section card, not just the three "
                    ".theme-status ones — while a genuinely SMALLER set (one Device card "
                    "removed from `builders`) still passes, proving the comparator is not "
                    "secretly counting; the failure message names the offending page, the "
                    "offending title's text and BOTH triples. Supersection intro headings "
                    "(.section-intro > h2) are excluded structurally, deliberately — a "
                    "different, generically-worded tier (27-06-PLAN.md Task 1, SKILL.md's "
                    "three-rung heading ladder), not an inconsistency this check should assert "
                    "away. Both themes exercised via _set_ui_theme(), at the 360px floor "
                    "(CFG-72, 28-04-PLAN.md Task 2)",
                    _a_settings_card_title_renders_identically_on_both_settings_pages)

                # --- 28-09-PLAN.md Task 1 (CFG-78): the single-affordance
                # audit. "Exactly one save affordance" has been true BY
                # CONSTRUCTION since 28-08 relocated the native submit into
                # the bar and 28-08 Task 2 deleted the `.js`-hide rule — but
                # "by construction" is exactly what 27-06 said about the
                # title form, and it was wrong (CFG-65's own investigation).
                # This check resolves every submit-shaped control's OWN
                # `.form` property in a live browser — never a hand-
                # maintained allow-list of expected buttons, never a count
                # of `<button` occurrences in the HTML string — and
                # requires exactly one whose form id is
                # config_page.SETTINGS_FORM_ID.
                #
                # "Submit-shaped" is `input[type="submit"]`,
                # `button[type="submit"]`, AND a bare `<button>` with no
                # `type` attribute — the HTML default IS submit, and a
                # check that only looked at explicit `type="submit"` would
                # miss the exact regression class it exists to catch (a
                # button added without a type, inside the form, silently
                # becoming a second save affordance).
                #
                # THE ONE DELIBERATE EXCLUSION: the bar's own Cancel is a
                # native `<button type="reset" form="settings-form">`
                # (28-08-PLAN.md Task 1). It IS form-ASSOCIATED with the
                # settings form — exactly what this audit hunts for — but
                # it is not submit-SHAPED (an explicit `type="reset"`
                # excludes it from every branch of the selector below) and
                # it saves nothing. Recorded here because "a second control
                # inside the bar that points at the settings form" looks
                # exactly like the regression this audit exists to catch,
                # and the next reader deserves to know it was considered,
                # not missed.
                def _submit_shaped_controls(page):
                    return page.evaluate(
                        "() => {"
                        " var sel = 'input[type=\"submit\"], button[type=\"submit\"], "
                        "button:not([type])';"
                        " var els = Array.prototype.slice.call(document.querySelectorAll(sel));"
                        " return els.map(function (el) {"
                        "   var text = (el.textContent || el.value || '').trim().slice(0, 60);"
                        "   return {"
                        "     tag: el.tagName.toLowerCase(),"
                        "     type: el.getAttribute('type') || '(default submit)',"
                        "     formId: el.form ? el.form.id : null,"
                        "     text: text,"
                        "     fallback: el.hasAttribute('%s'),"
                        "     inBar: !!el.closest('[data-dirty-bar]')"
                        "   };"
                        " });"
                        "}" % config_page.STATIC_SAVE_FALLBACK_ATTR)

                def _exactly_one_submit_shaped_control_resolves_to_the_settings_form():
                    base_url = harness.base_url()
                    for scope_route in ("/display", "/device"):
                        for lang in ("en", "fr"):
                            context = browser.new_context()
                            try:
                                page = context.new_page()
                                _login(page, base_url)
                                context.add_cookies([{
                                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                    "url": base_url}])
                                page.goto(base_url + scope_route)

                                controls = _submit_shaped_controls(page)
                                settings_controls = [
                                    c for c in controls
                                    if c["formId"] == config_page.SETTINGS_FORM_ID]

                                if len(controls) < 2:
                                    return False, (
                                        "%s lang=%s: expected MORE than one submit-shaped "
                                        "control on the page (the bar's own Save plus at "
                                        "least one other form's own submit control), found "
                                        "only %r — with only one candidate ever considered "
                                        "the exactly-one assertion below would be vacuous"
                                        % (scope_route, lang, controls))

                                if len(settings_controls) != 1:
                                    offenders = "; ".join(
                                        "%s[type=%s] form=%r text=%r"
                                        % (c["tag"], c["type"], c["formId"], c["text"])
                                        for c in controls)
                                    return False, (
                                        "%s lang=%s: expected exactly ONE submit-shaped "
                                        "control whose own .form.id resolves to %r, got %d "
                                        "— every collected submit-shaped control on this "
                                        "page: %s"
                                        % (scope_route, lang, config_page.SETTINGS_FORM_ID,
                                           len(settings_controls), offenders))

                                the_one = settings_controls[0]
                                if not the_one["fallback"]:
                                    return False, (
                                        "%s lang=%s: the one settings-form submit control "
                                        "does not carry %s — %r"
                                        % (scope_route, lang,
                                           config_page.STATIC_SAVE_FALLBACK_ATTR, the_one))
                                if not the_one["inBar"]:
                                    return False, (
                                        "%s lang=%s: the one settings-form submit control "
                                        "is not a descendant of [data-dirty-bar] — %r"
                                        % (scope_route, lang, the_one))

                                # The complement — the relationship half,
                                # not merely the endpoint: every OTHER
                                # submit-shaped control this scope renders
                                # (whichever of calendar/rules/
                                # notifications-test/quick-LED/quick-switch
                                # actually appear on THIS page — Airlines'
                                # own "Enregistrer le nom" form is excluded
                                # by construction too, trivially, since
                                # this check never navigates to that page)
                                # resolves to a form id that is NOT the
                                # settings form. Already implied by the
                                # exactly-one assertion above, but named
                                # per-control here so a regression that
                                # somehow gave TWO controls the settings-
                                # form id would still be caught with each
                                # offender's own identity in the message —
                                # the developer's own confirmed scope
                                # boundary ("laisser ces deux-la tels
                                # quels") expressed as a contract, not a
                                # comment.
                                bad = [
                                    c for c in controls
                                    if c is not the_one
                                    and c["formId"] == config_page.SETTINGS_FORM_ID]
                                if bad:
                                    return False, (
                                        "%s lang=%s: expected every OTHER submit-shaped "
                                        "control to resolve to a NON-settings-form id, "
                                        "found a second one pointed at settings-form: %r"
                                        % (scope_route, lang, bad))
                            finally:
                                context.close()
                    return True, ""
                check(
                    "exactly ONE submit-shaped control on the whole settings page resolves "
                    "its own .form.id to config_page.SETTINGS_FORM_ID, on both /display and "
                    "/device, in both site languages — resolved via the browser's OWN .form "
                    "property, never a count of <button occurrences in the HTML string and "
                    "never a hand-maintained allow-list; covers input[type=submit], "
                    "button[type=submit] AND a bare <button> with no type attribute (the "
                    "HTML default IS submit); the bar's native type=\"reset\" Cancel is "
                    "deliberately excluded (form-associated but not submit-shaped, and it "
                    "saves nothing); the one settings-form control must carry "
                    "data-static-save-fallback and be a descendant of [data-dirty-bar]; the "
                    "failure message NAMES every collected control as a tagName/type/form-"
                    "id/text tuple so a regression says WHICH control drifted; and the "
                    "complement is asserted too — calendar/rules/notifications-test/quick-"
                    "LED/quick-switch controls, whichever this scope renders, each resolve "
                    "to a NON-settings-form id (CFG-78, 28-09-PLAN.md Task 1)",
                    _exactly_one_submit_shaped_control_resolves_to_the_settings_form)

                # --- 28-09-PLAN.md Task 1 (CFG-74(c)/CFG-78): the runway
                # radios' cross-tree form="settings-form" regression check
                # — the developer's ORIGINAL, narrower report ("Quand je
                # fais un changement de parametre (comme la piste) je ne
                # vois pas le bouton enregistrer apparaitre") that carries
                # forward from the superseded CFG-74 with its value intact.
                # The runway radios live OUTSIDE <form id="settings-form">
                # (runway_fieldset()'s own docstring) and reach it only
                # through a form="settings-form" attribute on each radio —
                # a form element never receives a `change` event from a
                # control that is merely form=-associated with it, which is
                # exactly the B1 defect dirty-state.js's document-level
                # delegation exists to handle. This proves the whole path
                # end to end, against the restored bar's real POST rather
                # than the retired fetch.
                def _the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end():
                    base_url = harness.base_url()
                    for lang in ("en", "fr"):
                        context = browser.new_context()
                        try:
                            page = context.new_page()
                            _login(page, base_url)
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page.goto(base_url + "/display")

                            # 1. Fresh load: script has run, nothing dirty.
                            _wait_for_bar_hidden(page)

                            runway_sel = 'input[name="tracked_runway"]'
                            current_runway = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            target_runway = next(
                                r for r in device_config.RUNWAY_IDS
                                if r != current_runway)

                            # Built from the bar's OWN data-dirty-*
                            # attribute plus the runway wrapper's own
                            # [data-dirty-section] label — never a
                            # hardcoded English/French literal (the
                            # suite's existing D-06 idiom, reused verbatim
                            # from 28-11's section-naming check).
                            runway_label = page.eval_on_selector(
                                runway_sel,
                                "el => el.closest('[data-dirty-section]')"
                                ".getAttribute('data-dirty-section')")
                            changed_suffix = page.eval_on_selector(
                                "[data-dirty-bar]",
                                "el => el.getAttribute('data-dirty-changed-suffix')")
                            expected = runway_label + changed_suffix

                            # 2. Select a runway radio whose value differs
                            #    from disk, via the same real
                            #    element.click() every other visually-
                            #    hidden selectable-card radio on this page
                            #    uses (_click_control()'s own docstring
                            #    warns a coordinate click can silently
                            #    land elsewhere).
                            _click_control(
                                page, '%s[value="%s"]' % (runway_sel, target_runway))

                            # 3. The bar becomes visible AND names EXACTLY
                            #    Runway — proving the cross-tree form=
                            #    association actually reached
                            #    dirtySectionLabels()'s own
                            #    [data-dirty-section] walk, not merely
                            #    that "something" became dirty. Asserting
                            #    visibility alone would not prove this.
                            _wait_for_bar(page)
                            actual = _bar_text(page)
                            if actual != expected:
                                return False, (
                                    "lang=%s: expected [data-dirty-count] to read %r after "
                                    "selecting a cross-tree form=-associated runway radio, "
                                    "got %r — the section-naming walk must resolve this "
                                    "control's own [data-dirty-section] ancestor even though "
                                    "the radio is not a literal descendant of <form "
                                    "id=\"settings-form\">"
                                    % (lang, expected, actual))

                            # 4. Click Enregistrer, wait for the REAL
                            #    navigation.
                            _save_via_bar(page)

                            # 5. Re-read tracked_runway OFF DISK.
                            saved = device_config.load_device_config(
                                harness.tmpdir)["tracked_runway"]
                            if saved != target_runway:
                                return False, (
                                    "lang=%s: expected tracked_runway on disk to be %r "
                                    "after a real Enregistrer navigation through the "
                                    "runway's own cross-tree form= path, got %r"
                                    % (lang, target_runway, saved))

                            # Reload: the round trip, not just the write.
                            page.goto(base_url + "/display")
                            checked = page.eval_on_selector(
                                "%s:checked" % runway_sel, "el => el.value")
                            if checked != target_runway:
                                return False, (
                                    "lang=%s: expected the reloaded page's checked runway "
                                    "radio to be %r, got %r"
                                    % (lang, target_runway, checked))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "the runway radios' cross-tree form=\"settings-form\" wiring drives the "
                    "SAME bar-appears -> Enregistrer -> persisted-to-disk path every "
                    "natively-nested control does — closing the path CFG-74(c) named before "
                    "it was superseded, now against the real POST instead of the retired "
                    "fetch: selecting a runway radio (rendered OUTSIDE the settings form) "
                    "reveals the bar naming exactly its own Runway/Piste label, a real "
                    "Enregistrer navigation writes tracked_runway to disk, and a reload "
                    "shows the radio reflecting the saved value — both site languages "
                    "(CFG-74(c)/CFG-78, 28-09-PLAN.md Task 1)",
                    _the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end)

                # ==========================================================
                # 25-07-PLAN.md Task 3 (CFG-51/D19): THE ARTWORK DROP ZONE.
                #
                # ITS OWN ISOLATED Harness(), for the reason 25-02's own
                # helper docstring gives about T-25-02-A: these checks
                # UPLOAD an illustration and add a manual resolution, and
                # the shared fixture is the subject of forty other checks
                # in this file. Every one of them below also deletes the
                # override file it wrote, so the block leaves its own
                # fixture as it found it too.
                #
                # THE SUBJECT IS A MANUAL ENTRY WITH NO ARTWORK YET —
                # Step B — because that is the one state where BOTH copies
                # of the upload form render at once: the in-page no-JS
                # fallback panel (a real action, the scriptless floor) and
                # the dialog's copy (the placeholder action panel-lookup.js
                # rewrites). The two are the same builder's output.
                # ==========================================================
                artwork_harness = Harness()
                seed_state_dir(artwork_harness.tmpdir)
                ARTWORK_PREFIX = "NEW"
                ARTWORK_NAME = "Totally Novel Airline"
                if manual_resolutions.add_entry(
                        artwork_harness.tmpdir, ARTWORK_PREFIX,
                        ARTWORK_NAME) != manual_resolutions.ADD_OK:
                    raise AssertionError("could not seed the Step-B manual entry")
                ARTWORK_KEY = manual_resolutions.illustration_key_for_name(ARTWORK_NAME)
                ARTWORK_ROUTE = "/airlines?resolve=" + ARTWORK_PREFIX
                ARTWORK_SERVE = "/illustration/%s.png" % ARTWORK_KEY
                FALLBACK_ZONE = "[data-resolve-fallback] [data-upload-drop]"
                # 29-01-PLAN.md (CFG-81): the dialog's Replace form now
                # renders UNCONDITIONALLY (edit_mode is gone), so the
                # shared #panel-lookup-dialog carries BOTH upload-drop
                # zones at once from here on — this one (the needs-
                # artwork resolve zone, id_suffix="-dialog") and
                # REPLACE_INPUT_ID's own ("airline-replace-input"),
                # panel-lookup.js's `mode` gate hides whichever does not
                # apply, but both are always present in the DOM, so a
                # bare "[data-upload-drop]" now matches two elements —
                # this check's own subject is the needs-artwork one,
                # disambiguated by the same UPLOAD_DROP_INPUT_ATTR value
                # panel-lookup.js itself reads to decide which to hide.
                DIALOG_ZONE = "#panel-lookup-dialog [%s='%s']" % (
                    airlines_page.UPLOAD_DROP_INPUT_ATTR,
                    airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog",
                )

                art_dir = tempfile.mkdtemp(prefix="skypane-browser-ux-artwork-")
                artwork_harness.start()
                try:
                    from PIL import Image as _ArtImage

                    # A real, plausible illustration: a landscape PNG with
                    # transparent padding, the shape every vendored file
                    # has and the shape illustration_normalize.py crops.
                    art_path = os.path.join(art_dir, "artwork.png")
                    art = _ArtImage.new("RGBA", (1200, 300), (0, 0, 0, 0))
                    for ax in range(200, 1000):
                        for ay in range(80, 220):
                            art.putpixel((ax, ay), (200, 40, 40, 255))
                    art.save(art_path)

                    # Not an image at all, and over the server's own cap.
                    # The oversized one is INCOMPRESSIBLE NOISE on purpose:
                    # a large flat PNG compresses to nothing and would sail
                    # under a cap this check exists to reach.
                    not_png_path = os.path.join(art_dir, "not-an-image.txt")
                    with open(not_png_path, "wb") as fh:
                        fh.write(b"this is not a png\n")
                    oversized_path = os.path.join(art_dir, "oversized.png")
                    _ArtImage.frombytes(
                        "RGBA", (1200, 1200), os.urandom(1200 * 1200 * 4)
                    ).save(oversized_path)
                    OVERSIZED_BYTES = os.path.getsize(oversized_path)
                    ART_BYTES = os.path.getsize(art_path)

                    def _override_path():
                        return illustrations.override_path_for_key(
                            ARTWORK_KEY, artwork_harness.tmpdir)

                    def _stored_artwork():
                        """The stored override's BYTES, or None. The
                        verdict for every upload below, read off the real
                        state directory rather than off the page — a POST
                        this app rejected redirects to a page that looks
                        exactly like success."""
                        path = _override_path()
                        if not path or not os.path.isfile(path):
                            return None
                        with open(path, "rb") as fh:
                            return fh.read()

                    def _clear_stored_artwork():
                        path = _override_path()
                        if path and os.path.isfile(path):
                            os.unlink(path)

                    def _artwork_uploads_and_is_served_with_scripts_blocked():
                        try:
                            # BOTH DIRECTIONS OF THE GATE FIRST, because
                            # a successful upload moves this entry out of
                            # Step B and the fallback panel stops
                            # rendering the zone at all.
                            #
                            # `prepare` un-hides the in-page fallback on
                            # BOTH pages, and that is not a poke to make a
                            # check pass: a ?resolve= deep link auto-opens
                            # the dialog and panel-lookup.js hides the
                            # in-page copy as a duplicate sitting behind
                            # the backdrop (Phase 18 audit). Without this
                            # the two directions would measure two
                            # different elements. It is applied identically
                            # to both pages, which is the helper's own
                            # stated requirement.
                            def unhide_fallback(page):
                                page.evaluate(
                                    "() => { const f = document.querySelector("
                                    "'[data-resolve-fallback]'); if (f) f.hidden = false; }")
                            gate = _assert_js_gate(
                                browser.new_context, artwork_harness.base_url(), ARTWORK_ROUTE,
                                FALLBACK_ZONE, viewport=VIEWPORT_MIN_SUPPORTED,
                                prepare=unhide_fallback)
                            if gate["blocked"]["candidates"] != 0:
                                return False, (
                                    "the drop zone holds %d focusable descendant(s) — it is a "
                                    "hint, a preview and a message, and nothing in it should be "
                                    "reachable at all" % gate["blocked"]["candidates"])

                            before = _stored_artwork()
                            if before is not None:
                                return False, (
                                    "the fixture already has stored artwork for %r, so an upload "
                                    "could not be told from the state before it" % ARTWORK_KEY)
                            seen = _upload_without_js(
                                browser.new_context, artwork_harness.base_url(), ARTWORK_ROUTE,
                                "#%s" % airlines_page.MANUAL_UPLOAD_INPUT_ID,
                                "#%s button[type=\"submit\"]" % airlines_page.MANUAL_UPLOAD_FORM_ID,
                                art_path, _stored_artwork, ARTWORK_SERVE,
                                viewport=VIEWPORT_MIN_SUPPORTED)
                            # "Stored and served" is two claims. The
                            # second one is what a visitor sees, so it is
                            # measured as an IMAGE rather than as 200 plus
                            # a byte count: the route normalises on the
                            # way out, and the size it normalises to is
                            # illustration_normalize.py's own frame.
                            served = _ArtImage.open(io.BytesIO(seen["served"]))
                            if served.size != illustration_normalize.ILLUSTRATION_TARGET_SIZE:
                                return False, (
                                    "%s serves a %r image after a scripts-blocked upload, but "
                                    "companion/illustration_normalize.py's frame is %r — the "
                                    "route is not the normaliser's output"
                                    % (ARTWORK_SERVE, served.size,
                                       illustration_normalize.ILLUSTRATION_TARGET_SIZE))
                            _ = (seen["stored_len"], gate)
                            return True, ""
                        finally:
                            _clear_stored_artwork()
                    check(
                        "with scripts blocked at 360px, an artwork file chosen through the native "
                        "<input type=\"file\"> and submitted through the fallback panel's own form "
                        "is STORED (read back off the real state directory, never off the page — a "
                        "rejected upload redirects to a page that looks like success) and SERVED "
                        "back by the illustration route as an image at "
                        "illustration_normalize.ILLUSTRATION_TARGET_SIZE; and the drop zone beside "
                        "it measures zero height and holds zero focusable descendants with scripts "
                        "blocked while occupying a real box with them on (CFG-51/D-09, "
                        "25-07-PLAN.md Task 3)",
                        _artwork_uploads_and_is_served_with_scripts_blocked)

                    def _dropped_and_picked_files_are_stored_identically():
                        context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                        try:
                            if _stored_artwork() is not None:
                                return False, (
                                    "stored artwork for %r was already on disk when this check "
                                    "started — the previous check did not restore the fixture, "
                                    "and this entry would render as `art` rather than "
                                    "`needs-artwork`, hiding the upload zone entirely"
                                    % (ARTWORK_KEY,))
                            page = context.new_page()
                            _login(page, artwork_harness.base_url())
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)
                            submit = "#%s button[type=\"submit\"]" % (
                                airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog")

                            def upload_current_selection():
                                """Submit, then read the stored bytes and
                                put the fixture BACK into Step B.

                                The reset is not tidiness, it is what
                                makes the next upload possible at all: a
                                successful upload moves this entry from
                                `needs-artwork` to `art`, and
                                panel-lookup.js hides the dialog's upload
                                zone in every mode but the first. It is
                                also what makes the byte comparison mean
                                anything — with the previous file left in
                                place, a drop that never reached the
                                server would leave it there and compare
                                equal to itself.
                                """
                                with page.expect_navigation():
                                    page.click(submit)
                                written = _stored_artwork()
                                _clear_stored_artwork()
                                page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                                _await_upload_zone(page, DIALOG_ZONE)
                                return written

                            # THE FIXTURES, PROVED NON-VACUOUS AGAINST THE
                            # APP'S OWN NUMBER before anything is dropped.
                            # An "oversized" file that is not actually
                            # over the cap tests nothing while reading
                            # exactly like a passing check, and the cap is
                            # companion/app.py's, rendered into the page,
                            # never retyped here.
                            cap = int(page.locator(DIALOG_ZONE).get_attribute(
                                "data-upload-drop-max-bytes"))
                            if OVERSIZED_BYTES <= cap:
                                return False, (
                                    "the oversized fixture is %d bytes and the app's own cap is "
                                    "%d — the oversized case would be measuring nothing"
                                    % (OVERSIZED_BYTES, cap))
                            if ART_BYTES >= cap:
                                return False, (
                                    "the valid-artwork fixture is %d bytes, at or over the app's "
                                    "own %d cap — every acceptance below would be measuring the "
                                    "wrong thing" % (ART_BYTES, cap))

                            # --- THE FLOOR, MEASURED BEFORE THE CEILING ---
                            # A drop zone that silently accepts what the
                            # picker would reject is a defect, so every
                            # refusal is measured against the INPUT, not
                            # against a message: the question is whether
                            # anything was assigned.
                            floor = {}
                            _drop_files(page, DIALOG_ZONE, [])
                            floor["zero-files"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [not_png_path])
                            floor["wrong-type"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [art_path, art_path])
                            floor["several"] = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [oversized_path])
                            floor["oversized"] = _upload_zone_state(page, DIALOG_ZONE)
                            for label, state in floor.items():
                                if state["files"] != 0:
                                    return False, (
                                        "a %s drop assigned %d file(s) to the form's input — the "
                                        "refusal has to happen BEFORE the assignment or it "
                                        "refuses nothing (%r)" % (label, state["files"], state))
                                if not state["message"]:
                                    return False, (
                                        "a %s drop was refused silently — a drop target that "
                                        "declines without saying so is indistinguishable from one "
                                        "that is broken (%r)" % (label, state))
                                if not state["imageHidden"]:
                                    return False, (
                                        "a %s drop still rendered a preview (%r)" % (label, state))
                                # AND THE SRC IS GONE, not merely hidden.
                                # A hidden <img> still holding a data:
                                # URL keeps the whole decoded file alive
                                # for the life of the document — the same
                                # leak an unrevoked object URL would have
                                # been, and invisible to a check that only
                                # asks whether the preview is showing.
                                if state["imageScheme"] != "":
                                    return False, (
                                        "after a %s drop the preview <img> still holds a %r src — "
                                        "hidden is not released, and the whole decoded file stays "
                                        "in the document (%r)"
                                        % (label, state["imageScheme"], state))
                            if floor["oversized"]["message"] == floor["wrong-type"]["message"]:
                                return False, (
                                    "the oversized drop and the wrong-type drop say the same "
                                    "thing (%r) — the visitor cannot tell which rule they hit"
                                    % (floor["oversized"]["message"],))
                            if floor["several"]["message"] == floor["wrong-type"]["message"]:
                                return False, (
                                    "a several-files drop and a wrong-type drop say the same "
                                    "thing (%r)" % (floor["several"]["message"],))

                            # REPLACING A PREVIEW AND THEN BEING REFUSED,
                            # which is the only sequence in which "the
                            # preview is released" can be measured at
                            # all: every drop above was refused with no
                            # preview on screen to release, so an <img>
                            # that never let go of its data: URL would
                            # have passed all four of them.
                            _drop_files(page, DIALOG_ZONE, [art_path])
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            shown = _upload_zone_state(page, DIALOG_ZONE)
                            _drop_files(page, DIALOG_ZONE, [not_png_path])
                            after = _upload_zone_state(page, DIALOG_ZONE)
                            if after["imageScheme"] != "":
                                return False, (
                                    "a refused drop left the previous preview's %r src on the "
                                    "<img> (%r) — the decoded file stays in the document for as "
                                    "long as the page does"
                                    % (after["imageScheme"], after))
                            if after["files"] != 1 or after["size"] != shown["size"]:
                                return False, (
                                    "a refused drop discarded the file the visitor had already "
                                    "chosen (%r was holding %r, now %r) — declining to perform "
                                    "its own act is the script doing nothing; removing somebody "
                                    "else's choice is the script doing harm"
                                    % (shown["name"], shown["size"], after))
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)

                            # --- THE EQUIVALENCE, WHICH IS THE WHOLE POINT ---
                            # The same source file, uploaded twice: once
                            # picked, once dropped. The stored result must
                            # be byte-identical, because the ONLY thing
                            # between the file and the route is a
                            # DataTransfer assignment — no crop, no
                            # resize, no re-encode.
                            _clear_stored_artwork()
                            page.set_input_files(
                                "#%s" % (airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog"),
                                art_path)
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            picked_state = _upload_zone_state(page, DIALOG_ZONE)
                            picked_bytes = upload_current_selection()
                            if picked_bytes is None:
                                return False, (
                                    "picking the file and submitting stored nothing — before "
                                    "comparing two paths, one of them has to work")
                            if _stored_artwork() is not None:
                                return False, "could not clear the stored artwork between uploads"
                            dragged = _drop_files(page, DIALOG_ZONE, [art_path])
                            page.wait_for_function(
                                "sel => { const im = document.querySelector(sel)"
                                ".querySelector('.upload-drop__image');"
                                " return !im.hidden && !!im.getAttribute('src'); }",
                                arg=DIALOG_ZONE, timeout=5000)
                            dropped_state = _upload_zone_state(page, DIALOG_ZONE)
                            if dropped_state["files"] != 1:
                                return False, (
                                    "a trusted drop of a valid PNG assigned %d file(s) (%r)"
                                    % (dropped_state["files"], dropped_state))
                            dropped_bytes = upload_current_selection()
                            if dropped_bytes is None:
                                return False, (
                                    "dropping the same file and submitting stored NOTHING, while "
                                    "picking it stored %d bytes — the drop path does not reach "
                                    "the server the picked file reaches" % (len(picked_bytes),))
                            if dropped_bytes != picked_bytes:
                                return False, (
                                    "the SAME source file stored %d bytes when picked and %d when "
                                    "dropped — a second transform crept into the drop path, which "
                                    "is exactly the drift no client-side crop was written to "
                                    "avoid" % (len(picked_bytes), len(dropped_bytes)))
                            if picked_state["size"] != dropped_state["size"]:
                                return False, (
                                    "the picked file measured %r bytes in the input and the "
                                    "dropped one %r — the script altered the file on the way in"
                                    % (picked_state["size"], dropped_state["size"]))
                            if dropped_state["imageScheme"] != "data":
                                return False, (
                                    "the preview's src scheme is %r — this app's own "
                                    "Content-Security-Policy is img-src 'self' data:, under which "
                                    "a blob: preview is blocked outright"
                                    % (dropped_state["imageScheme"],))
                            if dropped_state["natural"] != [1200, 300]:
                                return False, (
                                    "the preview decoded to %r, not the source file's own "
                                    "1200x300 — the preview is the file, not a redrawing of it"
                                    % (dropped_state["natural"],))

                            # A SYNTHETIC drop, the one a page script can
                            # construct, must change nothing.
                            _clear_stored_artwork()
                            page.evaluate(
                                "sel => { const z = document.querySelector(sel);"
                                "  const dt = new DataTransfer();"
                                "  const ev = new DragEvent('drop',"
                                "    {bubbles: true, cancelable: true, dataTransfer: dt});"
                                "  z.dispatchEvent(ev); }", DIALOG_ZONE)
                            synthetic = _upload_zone_state(page, DIALOG_ZONE)
                            if synthetic["message"]:
                                return False, (
                                    "a synthetic (isTrusted: false) drop reached the handler and "
                                    "produced %r — the only way into it should be a gesture a "
                                    "person performed" % (synthetic["message"],))

                            # And the drag state was really on, DURING the
                            # drag, and really off after it.
                            if not dragged["active_during_drag"]:
                                return False, (
                                    "the drag-over state never appeared while the browser was in "
                                    "a drag — sampled between dragOver and drop, %r" % (dragged,))
                            if dragged["active_after_drop"]:
                                return False, "the drag-over state survived the drop (%r)" % (dragged,)
                            if dragged["paint_during_drag"] == dragged["paint_at_rest"]:
                                return False, (
                                    "the zone paints identically at rest and mid-drag (%r) — the "
                                    "state is set but invisible, which is the same as not having "
                                    "one" % (dragged["paint_at_rest"],))
                            return True, ""
                        finally:
                            _clear_stored_artwork()
                            context.close()
                    check(
                        "the SAME source file stored byte-identically whether it was PICKED or "
                        "DROPPED (with the stored file deleted between the two uploads, so a drop "
                        "that never reached the server could not pass on the picked file left "
                        "behind), the preview decoding to the source's own 1200x300 through a "
                        "data: URL (a blob: one is blocked by this app's own CSP); and the FLOOR "
                        "measured against the INPUT rather than against a message — zero files, a "
                        "wrong type, several at once and an oversized file each assign nothing, "
                        "each say something, and each say something different, while a synthetic "
                        "drop changes nothing at all and the drag-over state is sampled visible "
                        "BETWEEN dragOver and drop (CFG-51/D19, 25-07-PLAN.md Task 3)",
                        _dropped_and_picked_files_are_stored_identically)

                    def _drop_zone_meets_its_floors_at_360px_in_both_themes():
                        context = browser.new_context(viewport=VIEWPORT_MIN_SUPPORTED)
                        try:
                            page = context.new_page()
                            _login(page, artwork_harness.base_url())
                            page.goto(artwork_harness.base_url() + ARTWORK_ROUTE)
                            _await_upload_zone(page, DIALOG_ZONE)

                            # THE HIT TARGET, MEASURED IN THIS CONTROL'S
                            # OWN CONTAINER rather than inherited from a
                            # class — 25-06's pagers measured 30x45 in
                            # theirs while the same class measured 45x45
                            # elsewhere.
                            hit = _assert_hit_target(
                                page, DIALOG_ZONE, "the artwork drop zone on Airlines at 360px")
                            msg = _assert_no_page_overflow(
                                page, "the artwork drop zone on Airlines",
                                VIEWPORT_MIN_SUPPORTED["width"])
                            if msg:
                                return False, msg

                            # THE RESERVED BOX, before any image exists.
                            # A ratio, not a size: the box is fluid and
                            # the promise is its SHAPE. getBoundingClientRect,
                            # never clientWidth, which rounds to an integer
                            # and can fail a correct drawing.
                            at_rest = _upload_zone_state(page, DIALOG_ZONE)
                            want = (illustration_normalize.ILLUSTRATION_TARGET_WIDTH
                                    / illustration_normalize.ILLUSTRATION_TARGET_HEIGHT)
                            got = at_rest["preview"][0] / at_rest["preview"][1]
                            if abs(got - want) > 0.02:
                                return False, (
                                    "the preview box reserves %.4f:1 (%r) before any image "
                                    "exists, but illustration_normalize.py's frame is %.4f:1 — a "
                                    "box reserved at the wrong shape still makes the card jump"
                                    % (got, at_rest["preview"], want))
                            if not at_rest["imageHidden"]:
                                return False, (
                                    "the preview <img> is showing before a file was chosen (%r)"
                                    % (at_rest,))

                            painted = []
                            for measured in _in_both_themes(page):
                                paint = page.evaluate(
                                    "sel => { const z = document.querySelector(sel);"
                                    "  const n = z.querySelector('.upload-drop__note');"
                                    "  const p = z.querySelector('.upload-drop__preview');"
                                    "  return {note: getComputedStyle(n).color,"
                                    "          frame: getComputedStyle(p).borderTopColor,"
                                    "          surface: getComputedStyle(p).backgroundColor}; }",
                                    DIALOG_ZONE)
                                if paint["note"] == measured["canvas"]:
                                    return False, (
                                        "%s: the drop zone's hint text is the canvas colour (%r) "
                                        "— an invisible instruction is no instruction"
                                        % (measured["theme"], paint["note"]))
                                if paint["frame"] == paint["surface"]:
                                    return False, (
                                        "%s: the preview frame (%r) is its own fill, so the "
                                        "reserved box has no visible edge before an image arrives"
                                        % (measured["theme"], paint["frame"]))
                                painted.append((measured["theme"], paint))
                            if painted[0][1] == painted[1][1]:
                                return False, (
                                    "the drop zone paints identically in both themes (%r) — one "
                                    "of them is not reading the theme's tokens"
                                    % (painted[0][1],))
                            _set_ui_theme(page, "light")
                            _ = hit
                            return True, ""
                        finally:
                            context.close()
                    check(
                        "the artwork drop zone clears the 44px target by real hit-testing in ITS "
                        "OWN container at 360px, the Airlines page does not scroll sideways there, "
                        "the preview box reserves illustration_normalize.py's own aspect ratio "
                        "(by getBoundingClientRect, never clientWidth) BEFORE any image exists "
                        "with the <img> still hidden, and the paint is a FLOOR not a ceiling: the "
                        "hint text is never the canvas colour, the preview frame is never its own "
                        "fill, and the whole zone paints differently in the two themes (CFG-51/"
                        "CFG-52, 25-07-PLAN.md Task 3)",
                        _drop_zone_meets_its_floors_at_360px_in_both_themes)
                finally:
                    artwork_harness.stop()
                    artwork_harness.cleanup()
                    shutil.rmtree(art_dir, ignore_errors=True)

            finally:
                browser.close()
    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("browser-ux: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
