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
`EXPECTED_CHECK_COUNT`, and a `main()` returning 0 or 1 — so
`scripts/run_all_tests.py` needs zero special-casing for this file.

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
itself launched via `companion.test_companion_app.Harness`. No external
URL is ever constructed or navigated to anywhere in this file.

Reuses `companion.test_companion_app.Harness` for the subprocess-under-
test rather than inventing a second subprocess pattern (22-RESEARCH.md
Pattern 3): free port via `socket.bind(("127.0.0.1", 0))`, an isolated
`tempfile.mkdtemp()` state directory, a real `companion/app.py`
subprocess, a startup readiness poll, and a `stop()` that `terminate()`s
then `kill()`s.

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
import contextlib
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth, i18n, layout  # noqa: E402
from companion.test_companion_app import Harness, TEST_PASSWORD  # noqa: E402
from companion.pages import config_page  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import colour_rules, manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

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
# whole page under 3200px against the audit's measured 5800px. Only a
# real layout engine resolves `repeat(auto-fill, minmax(200px, 1fr))`,
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
# This covers the 47 that exist today (1 Home / 3 Display / 37 Flights /
# 1 Airlines / 4 Health / 1 Device / 0 login, re-derived by running) and
# any added later without editing this file. Each page asserts a minimum
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
# leave companion/test_companion_app.py's source-level motion guard GREEN
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
VIEW_TRANSITION_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")
VIEW_TRANSITION_NAMES = {
    "skypane-sidebar": VIEW_TRANSITION_ROUTES,
    "skypane-title": VIEW_TRANSITION_ROUTES,
    "skypane-picture": ("/",),
}

# --- The viewport sizes this file measures at (23-02-PLAN.md Task 1) ---
# One named set replacing the inline {"width": ..., "height": ...} dicts
# this file repeated at nine call sites. 360 is here because it is the
# MINIMUM SUPPORTED VIEWPORT (developer decision 2026-09-13, recorded in
# .claude/skills/sketch-findings-skypane/SKILL.md) and until now nothing
# in this file could name it — the assertions were a mix of 320 and 390.
#
# 320 STAYS a measured width even though the contract floor is 360, and
# that is deliberate, not an oversight for a later reader to tidy away.
# SKILL.md states both of the floor's non-licences in as many words: it
# "does not license shipping something broken at 360 px", and it "does
# not mean deleting the 320 px assertions that already exist in
# companion/test_browser_ux.py. They pass today, they cost nothing, and
# they catch real defects. Keep them." The narrow rung below is that
# sentence, executable.
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 900}
# Out of contract since 2026-09-13, still measured — see above.
VIEWPORT_WIDTH_NARROW = 320
VIEWPORT_WIDTH_TABLET = 768
# The two width ladders, for the checks that build one context per width
# rather than one fixed-size context. Derived from the three sizes above
# so a width has exactly one definition in this file.
VIEWPORT_WIDTHS_RESPONSIVE = (
    VIEWPORT_MIN_SUPPORTED["width"], VIEWPORT_PHONE["width"],
    VIEWPORT_DESKTOP["width"])
VIEWPORT_WIDTHS_ALL = (
    VIEWPORT_WIDTH_NARROW, VIEWPORT_MIN_SUPPORTED["width"],
    VIEWPORT_PHONE["width"], VIEWPORT_WIDTH_TABLET,
    VIEWPORT_DESKTOP["width"])

# Fixed, deterministic — never datetime.now(). 06:00 UTC so the 17h runway
# window (06:00-23:00) and a 23:00-07:00 quiet-hours window share no
# overlap with each other by construction, keeping the two concerns
# independent in the seeded fixture.
SEED_BASE_TS = datetime(2026, 8, 1, 6, 0, 0, tzinfo=timezone.utc)


def seed_state_dir(state_dir, base_ts=SEED_BASE_TS):
    """Write 22-AUDIT.md's own methodology fixture into a fresh temp
    state directory, through the same modules companion/app.py and
    server/poll_loop.py use to write this data themselves — see this
    file's own module docstring for the full rationale and the one
    deliberate deviation (battery cadence).
    """
    runway_ids = device_config.RUNWAY_IDS
    theme_ids = device_config.THEME_IDS

    with history_db.open_db(state_dir) as conn:
        # 36 runway events over 17h.
        step = timedelta(hours=17) / 36
        for i in range(36):
            ts = base_ts + step * i
            history_db.record_runway_event(
                conn,
                ts=ts.isoformat(),
                hex="39%04x" % (0x9000 + i),
                callsign="AFR%03d" % (100 + i),
                aircraft_type="A320",
                confirmed_state="confirmed",
                corroborated=(i % 3 != 0),
                route_source="adsb" if i % 2 == 0 else "schedule",
                airline="Air France",
                origin="LFPO",
                destination="LFPG",
                tracked_runway=runway_ids[i % len(runway_ids)],
            )

        # ~40 days of battery readings, one reading per day (see the
        # module docstring's cadence note).
        for day in range(40, 0, -1):
            ts = base_ts - timedelta(days=day)
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=4200 - day * 3,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")

    device_config.save_device_config(
        state_dir, theme=theme_ids[0], tracked_runway=runway_ids[0],
        wake_interval_s=300, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00",
        display_enabled=True,
    )

    now_iso = base_ts.isoformat()

    # 2 unresolved prefixes — same registry shape
    # companion/test_status_pages.py's own _seed_unresolved_prefixes()
    # helper writes, through the identical save_poll_state() call.
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": {
        "TVF": {
            "count": 5, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "TVF123",
        },
        "EZY": {
            "count": 2, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "EZY456",
        },
    }})

    # 1 manual resolution.
    manual_resolutions.add_entry(state_dir, "RYR", "Ryanair", now=now_iso)

    # 2 colour rules.
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_PREFIX, "AFR", theme_ids[0], now=now_iso)
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_CALLSIGN, "EZY456", theme_ids[-1], now=now_iso)

    # 3 gallery renders, archived through poll_loop's own writer — never a
    # hand-written PNG dropped straight into the gallery directory, so the
    # on-disk filename/format contract can never drift from what a real
    # poll cycle produces.
    from PIL import Image
    canvas = Image.new("RGB", (8, 8), "white")
    for i in range(3):
        render_ts = (base_ts + timedelta(minutes=i)).isoformat()
        poll_loop._save_to_gallery(state_dir, canvas, render_ts)


def _login(page, base_url):
    """Drive the real login form through the UI (never a bare HTTP POST —
    this file exists specifically to exercise the browser), and wait for
    the post-login redirect to land.
    """
    page.goto(base_url + "/login")
    page.fill("#password", TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@contextlib.contextmanager
def _no_js_page(browser, base_url, route, viewport=None, sign_in=True):
    """A scripts-blocked browser context, signed in, landed on `route`.

    The one place in this file that blocks scripts. Three checks each
    spelled this sequence out by hand (Health, the two settings pages,
    and the login card), and 23-RESEARCH.md's Wave 0 gap list names five
    more controls that each need one; a transcribed sequence is a
    sequence that can be transcribed WRONG, and a scripts-blocked proof
    that quietly ran with scripts enabled would pass while proving
    nothing. Keeping the flag to a single call site is what makes that
    failure mode unavailable rather than merely unlikely.

    `sign_in=False` exists for the login card, whose whole subject is the
    unauthenticated page: it asserts what /login renders with scripts
    blocked and THEN signs in as its last act. That is not a weaker use
    of the helper, it is the only honest one for a check about signing
    in.

    `viewport` is optional and defaults to the Playwright default the
    three converted checks already ran under, so converting them changes
    nothing at all. Pass VIEWPORT_MIN_SUPPORTED to measure a
    scripts-blocked control at the 360px contract floor.

    `context.close()` runs in a finally, the discipline every check in
    this file already follows by hand.
    """
    extra = {} if viewport is None else {"viewport": viewport}
    context = browser.new_context(java_script_enabled=False, **extra)
    try:
        page = context.new_page()
        if sign_in:
            page.goto(base_url + "/login")
            page.fill("#password", TEST_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_load_state("load")
        page.goto(base_url + route)
        yield page
    finally:
        context.close()


def _click_control(page, selector):
    """Click a checkbox/radio input through the browser's own native
    .click() method (JS-level, not Playwright's mouse-coordinate click).

    Every checkbox/radio this file's checks click below is visually
    hidden (config_page.py's own selectable-card idiom: a
    visually-hidden native input wrapped in a full-card <label>), via
    `clip-path: inset(50%)` (companion/static/style.css's own
    .visually-hidden rule) — which clips the element's paintable AND
    hit-testable area to nothing. A coordinate-based click (Playwright's
    own `locator.click()`, even with `force=True`) dispatches at that
    point and can silently land on whatever the browser's hit-test
    resolves to there instead (confirmed live: it left the target
    control unchecked with no error). `element.click()` is the DOM's own
    "activation behaviour" algorithm — it runs regardless of paint/hit-
    test visibility and is what every real assistive-technology/keyboard
    activation path already relies on for this exact selectable-card
    pattern, so it is the correct thing to call here, not a workaround.
    """
    page.eval_on_selector(selector, "el => el.click()")


def _guard_armed(page):
    """T1: whether dirty-state.js's beforeunload guard is currently
    armed, tested by constructing a real, cancelable `beforeunload`
    Event object in-page and dispatching it directly on window, then
    reading `defaultPrevented` — never by trying to trigger an actual
    navigation and observe a native "leave site?" dialog, which
    Chromium suppresses/auto-resolves under Playwright and which
    Playwright's own `dialog` event does not reliably surface for
    beforeunload specifically. Dispatching the Event directly still
    exercises dirty-state.js's own real listener (the one registered via
    `window.addEventListener("beforeunload", ...)`) with no change to
    that file — this is a black-box behavioural probe, not an internal
    read of the private `suppressGuard` variable.
    """
    return page.evaluate(
        "() => { var e = new Event('beforeunload', {cancelable: true}); "
        "window.dispatchEvent(e); return e.defaultPrevented; }")


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
                        # X7's second half: the 5800px page roughly
                        # halves. Measured, with headroom, so this fails
                        # on a regression rather than on a pixel.
                        height = page.evaluate("document.documentElement.scrollHeight")
                        if height > 3200:
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
                    "159px the contract predicts, and the whole page under 3200px (X7, "
                    "22-11-PLAN.md Task 2)",
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
                    with _no_js_page(browser, harness.base_url(), "/health") as page:
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
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        theme_ids = device_config.THEME_IDS
                        runway_ids = device_config.RUNWAY_IDS

                        # 1. Theme chip (Frame colours card, form=-attached,
                        # rendered as a sibling of <form id="settings-form">):
                        # reveal, name the section, submit, persist.
                        page.goto(base_url + "/display")
                        target_theme = theme_ids[1]
                        theme_sel = 'input[name="theme"][value="%s"]' % target_theme
                        _click_control(page, theme_sel)
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a theme chip click"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Frame colours" not in count_text:
                            return False, "expected the bar to name Frame colours, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if not page.eval_on_selector(theme_sel, "el => el.checked"):
                            return False, "expected the saved theme chip to be checked after reload"

                        # 2. Runway card (also a sibling of the form).
                        page.goto(base_url + "/display")
                        target_runway = runway_ids[1]
                        runway_sel = 'input[name="tracked_runway"][value="%s"]' % target_runway
                        _click_control(page, runway_sel)
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a runway card click"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Runway" not in count_text:
                            return False, "expected the bar to name Runway, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if not page.eval_on_selector(runway_sel, "el => el.checked"):
                            return False, "expected the saved runway card to be checked after reload"

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
                        page.goto(base_url + "/display")
                        quiet_sel = 'input[name="quiet_hours_start"]'
                        page.fill(quiet_sel, "22:15")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible after a quiet-hours time edit"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Quiet hours" not in count_text:
                            return False, "expected the bar to name Quiet hours, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/display")
                        if page.eval_on_selector(quiet_sel, "el => el.value") != "22:15":
                            return False, "expected the saved quiet-hours start time to persist after reload"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Display: a theme chip, a runway card and a quiet-hours time field each reveal the "
                    "save bar, name their own section, and persist on save (B1, form=-attached radio "
                    "and time-input field kinds — the Enable-display checkbox this check also covered "
                    "is retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1)",
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
                        # /quick/led — so it cannot witness a save-bar
                        # round trip any more. The wake-interval number
                        # input is the Device scope's surviving
                        # form=-attached field and carries this check's
                        # real subject unchanged: the bar reveals, names
                        # its own section, and the value persists on
                        # save, exactly as Display's does. (The LED's own
                        # no-JS persistence is proven separately, in this
                        # file's scripts-blocked switch check.)
                        page.goto(base_url + "/device")
                        wake_sel = 'input[name="wake_interval_s"]'
                        before = page.eval_on_selector(wake_sel, "el => el.value")
                        target = "1800" if before != "1800" else "3600"
                        page.fill(wake_sel, target)
                        bar = page.locator("[data-dirty-bar]")
                        if bar.is_hidden():
                            return False, "expected the save bar to become visible on Device too"
                        count_text = page.locator("[data-dirty-count]").inner_text()
                        if "Wake interval" not in count_text:
                            return False, "expected the bar to name Wake interval, got %r" % count_text
                        with page.expect_navigation():
                            page.locator(".dirty-bar__save").click()
                        page.goto(base_url + "/device")
                        if page.eval_on_selector(wake_sel, "el => el.value") != target:
                            return False, (
                                "expected the edited wake interval to have persisted, got %r"
                                % page.eval_on_selector(wake_sel, "el => el.value"))
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
                    "Device: the same reveal-and-persist round trip proves the two scopes stay in "
                    "step (B1) — witnessed by the wake-interval field since the Diagnostic LED "
                    "stopped being a Save-governed control (retargeted in place by 23-07-PLAN.md "
                    "Task 2, D2/CFG-36)",
                    _device_reveal_and_persist_stays_in_step_with_display)

                def _fallback_save_reachable_until_bar_proven_live():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()

                        # With the bar never revealed, the fallback stays visible
                        # and submitting it saves (D-01: the fallback is the only
                        # write path a broken/blocked script leaves behind).
                        page.goto(base_url + "/display")
                        fallback = page.locator("[data-static-save-fallback]")
                        if not fallback.is_visible():
                            return False, "expected the fallback Save button to be visible before the bar is ever shown"
                        with page.expect_navigation():
                            fallback.click()
                        if "/display" not in page.url:
                            return False, "expected the fallback Save button to actually submit the form"

                        # Once the bar has been revealed once, the fallback hides.
                        page.goto(base_url + "/display")
                        fallback = page.locator("[data-static-save-fallback]")
                        if not fallback.is_visible():
                            return False, "expected the fallback Save button to still be visible before any edit on a fresh load"
                        theme_ids = device_config.THEME_IDS
                        _click_control(page, 'input[name="theme"][value="%s"]' % theme_ids[2])
                        if page.locator("[data-dirty-bar]").is_hidden():
                            return False, "expected the save bar to become visible after the edit"
                        if fallback.is_visible():
                            return False, "expected the fallback Save button to hide once the bar has genuinely been shown"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "the fallback Save button stays reachable and functional until the bar has actually been "
                    "shown once, then hides (D-01: the no-way-to-save-at-all fix)",
                    _fallback_save_reachable_until_bar_proven_live)

                def _cancel_restores_preview_and_rearms_guard():
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        _login(page, harness.base_url())
                        base_url = harness.base_url()
                        page.goto(base_url + "/display")
                        theme_ids = device_config.THEME_IDS
                        original_sel = 'input[name="theme"]:checked'
                        original_value = page.eval_on_selector(original_sel, "el => el.value")
                        original_src = page.locator(".theme-live-preview__image").get_attribute("src")

                        if _guard_armed(page):
                            return False, "expected the leave-guard to start disarmed on a clean page load"

                        other_theme = next(t for t in theme_ids if t != original_value)
                        _click_control(page, 'input[name="theme"][value="%s"]' % other_theme)
                        new_src = page.locator(".theme-live-preview__image").get_attribute("src")
                        if new_src == original_src:
                            return False, "expected the live preview to change immediately after the edit"
                        if not _guard_armed(page):
                            return False, "expected the leave-guard to be armed after a real edit"

                        page.locator("[data-dirty-cancel]").click()
                        # T8: Cancel restores both the form value AND the live
                        # preview - form.reset() alone only restores the former.
                        if not page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % original_value, "el => el.checked"):
                            return False, "expected Cancel to restore the original theme chip's checked state"
                        restored_src = page.locator(".theme-live-preview__image").get_attribute("src")
                        if restored_src != original_src:
                            return False, (
                                "expected Cancel to restore the live preview to its original src, got %r "
                                "(T8)" % (restored_src,))
                        if _guard_armed(page):
                            return False, "expected Cancel to disarm the leave-guard"

                        # T1: the NEXT edit re-arms the guard - it must not stay
                        # disarmed for the rest of the page's life after Cancel.
                        _click_control(page, 'input[name="theme"][value="%s"]' % other_theme)
                        if not _guard_armed(page):
                            return False, "expected a subsequent edit after Cancel to re-arm the leave-guard (T1)"
                        return True, ""
                    finally:
                        context.close()
                check(
                    "Cancel restores the form value AND the live theme preview (T8), and a subsequent edit "
                    "re-arms the leave-guard (T1)",
                    _cancel_restores_preview_and_rearms_guard)

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

                        theme_ids = device_config.THEME_IDS
                        original_sel = 'input[name="theme"]:checked'
                        original_value = page.eval_on_selector(original_sel, "el => el.value")
                        other_theme = next(t for t in theme_ids if t != original_value)

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
                        _click_control(page, 'input[name="theme"][value="%s"]' % other_theme)
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
                        # all - and the guard must still warn.
                        page.goto(base_url + "/display")
                        dialogs[:] = []
                        current_value = page.eval_on_selector(original_sel, "el => el.value")
                        alt_theme = next(t for t in theme_ids if t != current_value)
                        _click_control(page, 'input[name="theme"][value="%s"]' % alt_theme)
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
                        boxes = page.evaluate(
                            "() => [...document.querySelectorAll('.runway-card')]"
                            ".map(e => { const b = e.getBoundingClientRect(); "
                            "const s = getComputedStyle(e); "
                            "const bw = parseFloat(s.borderLeftWidth) "
                            "+ parseFloat(s.borderRightWidth); "
                            "return {w: b.width, inner: b.width - bw, border: bw, "
                            "h: b.height, top: b.top, left: b.left}; })")
                        if len(boxes) != 3:
                            return False, "expected 3 runway cards, got %d" % len(boxes)

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
                    "and each still clears 44x44 - never a 2 + 1 orphan (B9, 22-10-PLAN.md Task 2)",
                    _three_runway_cards_share_one_line_at_390px)

                def _the_no_js_floor_holds_for_both_settings_pages():
                    # D-09's floor, asserted at THIS plan's own commit
                    # rather than deferred to the phase's end: this plan
                    # re-homes a control through the cross-DOM `form=`
                    # idiom (B8) and converts a CSS `content` literal to
                    # an attribute read (T10). Both are exactly the kind
                    # of change that can look fine with scripts running
                    # and be dead without them, so a break must fail here.
                    base_url = harness.base_url()
                    with _no_js_page(browser, base_url, "/display") as page:
                        if not page.query_selector(".theme-chip"):
                            return False, "Display must render its chips with scripts blocked"
                        # T10: the badge's text is an ATTRIBUTE now, so it
                        # has to be in the server's own HTML.
                        badge = page.eval_on_selector_all(
                            "[data-current-label]", "els => els.map(e => e.dataset.currentLabel)")
                        if not badge or not all(badge):
                            return False, (
                                "expected the 'Current' badge's text to be server-rendered into "
                                "data-current-label, got %r" % (badge,))
                        # D-08's no-JS floor: the server never emits
                        # `hidden` on a usage panel, so every control is
                        # reachable without theme-preview.js.
                        hidden_panels = page.eval_on_selector_all(
                            ".frame-colours__usage-panel",
                            "els => els.filter(e => e.hidden "
                            "|| e.classList.contains('frame-colours__usage-panel--collapsed')).length")
                        if hidden_panels:
                            return False, (
                                "expected no collapsed usage panel with scripts blocked, got %d"
                                % hidden_panels)
                        # A settings save still round-trips.
                        theme_ids = device_config.THEME_IDS
                        current = device_config.load_device_config(harness.tmpdir)["theme"]
                        other = next(t for t in theme_ids if t != current)
                        page.eval_on_selector(
                            'input[name="theme"][value="%s"]' % other, "el => el.checked = true")
                        with page.expect_navigation():
                            page.click('#settings-form button[type="submit"]')
                        if device_config.load_device_config(harness.tmpdir)["theme"] != other:
                            return False, "expected a settings save to persist with scripts blocked"

                        page.goto(base_url + "/device")
                        # B8: the re-homed button must be inside the card
                        # AND still own its form, which with scripts
                        # blocked is entirely the browser's own `form=`
                        # resolution - nothing else can supply it.
                        btn = page.query_selector('button[form="notifications-test"]')
                        if btn is None:
                            return False, "expected the re-homed 'Send a test' button on Device"
                        owned = page.eval_on_selector(
                            'button[form="notifications-test"]',
                            "el => el.form && el.form.getAttribute('action')")
                        if owned != "/settings/notifications/test":
                            return False, (
                                "expected the button's form= attachment to resolve to the test "
                                "form's own action with scripts blocked, got %r" % (owned,))
                        with page.expect_navigation():
                            btn.click()
                        if "/device" not in page.url:
                            return False, (
                                "expected the test submission to redirect back to Device, got %r"
                                % page.url)
                        return True, ""
                check(
                    "with scripts blocked both settings pages render and stay usable: the 'Current' "
                    "badge's text is server-rendered into data-current-label, no usage panel is "
                    "collapsed, a Display save round-trips, and the re-homed 'Send a test' button "
                    "resolves its own form= attachment and submits (D-09 floor asserted at this "
                    "plan's own commit, 22-10-PLAN.md Task 3)",
                    _the_no_js_floor_holds_for_both_settings_pages)

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
                            browser, harness.base_url(), "/login", sign_in=False) as page:
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

                def _save_bar_and_tab_bar_never_overlap_at_390x844():
                    # D-10's "must not cover the pinned save bar", and
                    # 22-UI-SPEC.md §3.1's own acceptance sentence,
                    # verified rather than asserted. Both elements are
                    # `position: fixed` at the same corner of a 390x844
                    # viewport, so nothing short of a real layout engine
                    # can answer whether they intersect.
                    #
                    # Geometric separation is checked FIRST, because that
                    # is the order the fix is built in: the save bar's
                    # own bottom offset gains the tab bar's height, so in
                    # the normal case the two never overlap at all. The
                    # stacking order is the belt-and-braces half and is
                    # checked second.
                    def centre_owner(page, selector):
                        return page.evaluate(
                            "(sel) => {"
                            " var el = document.querySelector(sel);"
                            " var r = el.getBoundingClientRect();"
                            " var hit = document.elementFromPoint("
                            "   Math.round(r.left + r.width / 2),"
                            "   Math.round(r.top + r.height / 2));"
                            " return hit ? (hit === el || el.contains(hit)) : false;}",
                            selector)

                    for width, height, label in ((390, 844, "390x844"), (1280, 900, "1280x900")):
                        context = browser.new_context(
                            viewport={"width": width, "height": height})
                        try:
                            page = context.new_page()
                            _login(page, harness.base_url())
                            page.goto(harness.base_url() + "/display")
                            page.wait_for_load_state("networkidle")
                            current = page.eval_on_selector(
                                'input[name="theme"]:checked', "el => el.value")
                            other = next(
                                t for t in device_config.THEME_IDS if t != current)
                            _click_control(
                                page, 'input[name="theme"][value="%s"]' % other)
                            page.wait_for_timeout(300)

                            if not page.locator("[data-dirty-bar]").is_visible():
                                return False, (
                                    "expected the save bar to be visible after an unsaved edit "
                                    "at %s" % label)
                            geom = page.evaluate(
                                "() => {"
                                " var bar = document.querySelector('[data-dirty-bar]');"
                                " var tabs = document.querySelector('.tab-bar');"
                                " var b = bar.getBoundingClientRect();"
                                " var out = {bar: {top: b.top, bottom: b.bottom,"
                                "                  left: b.left, right: b.right},"
                                "            barZ: getComputedStyle(bar).zIndex,"
                                "            tabsPresent: !!tabs};"
                                " if (tabs) {"
                                "   var t = tabs.getBoundingClientRect();"
                                "   out.tabs = {top: t.top, bottom: t.bottom,"
                                "               left: t.left, right: t.right};"
                                "   out.tabsDisplay = getComputedStyle(tabs).display;"
                                "   out.tabsZ = getComputedStyle(tabs).zIndex;"
                                " }"
                                " return out;}")
                            if geom["barZ"] != "30":
                                return False, (
                                    "expected ONE save-bar stacking value across both "
                                    "breakpoints (30), got %r at %s" % (geom["barZ"], label))
                            if not centre_owner(page, "[data-dirty-bar]"):
                                return False, (
                                    "the save bar must be hit-testable at its own centre at %s"
                                    % label)

                            if width >= 960:
                                # T7's desktop half: no tab bar here, so
                                # the only thing to prove is that the
                                # stacking value is the same one.
                                if geom.get("tabsDisplay") not in (None, "none"):
                                    return False, (
                                        "the tab bar must not render at %s, got display %r"
                                        % (label, geom.get("tabsDisplay")))
                            else:
                                if geom.get("tabsDisplay") != "flex":
                                    return False, (
                                        "expected the tab bar visible at %s, got display %r"
                                        % (label, geom.get("tabsDisplay")))
                                bar, tabs = geom["bar"], geom["tabs"]
                                overlaps = (
                                    bar["left"] < tabs["right"]
                                    and tabs["left"] < bar["right"]
                                    and bar["top"] < tabs["bottom"]
                                    and tabs["top"] < bar["bottom"])
                                if overlaps:
                                    return False, (
                                        "the save bar and the tab bar must not intersect at %s; "
                                        "save %r vs tabs %r" % (label, bar, tabs))
                                if bar["bottom"] > tabs["top"]:
                                    return False, (
                                        "the save bar must float ABOVE the tab bar, got "
                                        "bar bottom %r against tab top %r"
                                        % (bar["bottom"], tabs["top"]))
                                if int(geom["tabsZ"]) >= int(geom["barZ"]):
                                    return False, (
                                        "the save bar is the active task and the tab bar is "
                                        "ambient chrome — the save bar must win on stacking "
                                        "order too, got %r vs %r"
                                        % (geom["barZ"], geom["tabsZ"]))
                                if not centre_owner(page, ".tab-bar"):
                                    return False, (
                                        "the tab bar must stay hit-testable at its own centre "
                                        "at %s" % label)

                            # T7: the fixed bar must cover no content.
                            page.evaluate(
                                "() => window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(200)
                            covered = page.evaluate(
                                "() => {"
                                " var bar = document.querySelector('[data-dirty-bar]');"
                                " var barTop = bar.getBoundingClientRect().top;"
                                " var sections = document.querySelectorAll("
                                "   '.page-content .page-section');"
                                " var last = sections[sections.length - 1];"
                                " return {contentBottom: last.getBoundingClientRect().bottom,"
                                "         barTop: barTop,"
                                "         atBottom: (window.innerHeight + window.scrollY) >="
                                "                   (document.documentElement.scrollHeight - 2)};}")
                            if not covered["atBottom"]:
                                return False, (
                                    "expected the page to be scrolled to its own foot at %s"
                                    % label)
                            if covered["contentBottom"] > covered["barTop"]:
                                return False, (
                                    "the fixed save bar must cover no page content at %s: the "
                                    "last section ends at %r, the bar starts at %r"
                                    % (label, covered["contentBottom"], covered["barTop"]))
                        finally:
                            context.close()
                    return True, ""
                check(
                    "at 390x844 on Display with an unsaved edit the save bar and the bottom tab bar are "
                    "both visible, their bounding boxes do not intersect, both are hit-testable at their "
                    "centre points and the save bar wins on stacking order at the ONE value it declares "
                    "at both breakpoints — and at neither breakpoint does the fixed bar cover the last "
                    "section once the page is scrolled to its foot (D-10/T7, 22-14-PLAN.md Task 3)",
                    _save_bar_and_tab_bar_never_overlap_at_390x844)

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

                def _a_second_click_on_save_produces_no_second_post():
                    # T14 (22-15-PLAN.md Task 3). The audit found exactly
                    # one double-submission guard in the app - the poll
                    # button's - and every other form accepting a repeat
                    # POST. Only a real browser can prove the shared
                    # guard works, because the whole mechanism is the
                    # ordering between a submit event, the form data set
                    # the browser builds from it, and a zero-delay timer.
                    #
                    # The POST is intercepted and answered 204 rather
                    # than allowed through. That is what makes this check
                    # deterministic instead of a race: a 204 is the one
                    # response to a form POST that commits no new
                    # document, so the page stays put, the button is
                    # still there to click a second time and to inspect,
                    # and every POST that reaches the wire is counted
                    # exactly once. (Aborting the route does NOT work
                    # here - Chromium commits its own network-error
                    # document, which destroys the page under test.)
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        base_url = harness.base_url()
                        _login(page, base_url)
                        theme_ids = device_config.THEME_IDS

                        page.goto(base_url + "/display")
                        original = page.eval_on_selector(
                            'input[name="theme"]:checked', "el => el.value")
                        target = next(t for t in theme_ids if t != original)
                        _click_control(page, 'input[name="theme"][value="%s"]' % target)
                        if page.locator("[data-dirty-bar]").is_hidden():
                            return False, "expected the save bar after a theme edit"

                        posts = {"n": 0}

                        def _count_and_block(route, request):
                            if request.method == "POST":
                                posts["n"] += 1
                                route.fulfill(status=204, body="")
                            else:
                                route.continue_()

                        page.route("**/*", _count_and_block)

                        save = '.dirty-bar__save'
                        page.eval_on_selector(save, "el => el.click()")
                        # The guard disables from a zero-delay timer, on
                        # purpose: a submit button's own name/value is
                        # contributed to the form data set AFTER the
                        # listeners return, so an inline disable can drop
                        # it. Wait for the timer rather than assuming it.
                        page.wait_for_function(
                            "() => {"
                            " var b = document.querySelector('.dirty-bar__save');"
                            " return !!b && b.disabled === true;}",
                            timeout=5000)
                        if posts["n"] != 1:
                            return False, (
                                "expected exactly one POST from the first click, got %d"
                                % posts["n"])

                        # The second click, as a separate task - which is
                        # what a human double click actually is.
                        page.eval_on_selector(save, "el => el.click()")
                        page.wait_for_timeout(300)
                        if posts["n"] != 1:
                            return False, (
                                "expected a repeat click to produce NO second POST, got %d total "
                                "(T14)" % posts["n"])
                        label = page.eval_on_selector(save, "el => el.textContent.trim()")
                        for progress_word in ("Saving", "Enregistrement", "…"):
                            if progress_word in label:
                                return False, (
                                    "the guard must not change any button's label - a progress "
                                    "word is D3, Phase 23 - got %r" % (label,))

                        # And the two flows the guard must not fight
                        # still work, with the route removed: a real save
                        # persists, and a strip switch still navigates.
                        page.unroute("**/*")
                        page.goto(base_url + "/display")
                        _click_control(page, 'input[name="theme"][value="%s"]' % target)
                        with page.expect_navigation():
                            page.locator(save).click()
                        page.goto(base_url + "/display")
                        if not page.eval_on_selector(
                                'input[name="theme"][value="%s"]' % target, "el => el.checked"):
                            return False, (
                                "expected the save bar to still persist a real save with the "
                                "shared guard installed (T14)")
                        switch = page.locator("[data-quick-switch] button[type=\"submit\"]").first
                        if switch.count() == 0:
                            return False, "expected a Frame strip switch to exercise"
                        # 23-07-PLAN.md Task 1 (D2/CFG-36): retargeted in
                        # place. This used to assert the switch still
                        # NAVIGATES with the shared guard installed; D2
                        # is the decision that it applies over fetch
                        # instead. The property this clause is actually
                        # about — that T14's guard does not fight the
                        # switch — survives intact and is now asserted on
                        # the response and the control's own state
                        # rather than on a navigation that no longer
                        # happens.
                        before = device_config.load_device_config(harness.tmpdir)["display_enabled"]
                        with page.expect_response(
                                lambda r: r.url.split("?")[0] == base_url + "/quick/display"):
                            switch.click()
                        page.wait_for_timeout(400)
                        after = device_config.load_device_config(harness.tmpdir)["display_enabled"]
                        if after == before:
                            return False, (
                                "expected the strip switch to still apply with the shared guard "
                                "installed (T14 + D2)")
                        if switch.evaluate("el => el.disabled"):
                            return False, (
                                "the shared guard left the switch disabled — with no navigation "
                                "to replace the page it would stay dead (T14 + D2)")
                        return True, ""
                    finally:
                        context.close()
                check(
                    "a second click on the save bar's Save produces NO second POST - the shared guard "
                    "disables the submitting control from a zero-delay timer, so the browser has already "
                    "built the form data set (which is what keeps the named theme/language submit buttons "
                    "working) - and it changes no label, while a real save still persists and a Frame "
                    "strip switch still APPLIES with the guard installed, without navigating and "
                    "without being left disabled (T14, 22-15-PLAN.md Task 3; retargeted in place by "
                    "23-07-PLAN.md Task 1)",
                    _a_second_click_on_save_produces_no_second_post)

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
                    width = 390
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
                    #   Vols       /flights    37        nav + 36 row cards
                    #   Compagnies /airlines    1        nav
                    #   État       /health      4        nav + readings + 2 cards
                    #   Appareil   /device      1        nav
                    #   Connexion  /login       0        (no nav is rendered)
                    #
                    # 47 in total, not the ~83 an earlier task reported:
                    # /preview and /settings are 303 redirects (to /flights
                    # and /display), so the "panel-preview page" in that
                    # figure is /flights counted a second time. The raw
                    # number flatters the coverage either way — 36 of
                    # Vols' 37 are one component repeated per row, so the
                    # distinct KINDS number five.
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
                    # adding anything. All 47 are closed by default today.
                    # /flights' minimum of 37 is deliberately coupled to
                    # seed_state_dir()'s own 36 runway events: if the seed
                    # or a row cap changes, this must be re-derived here
                    # on purpose, not left to slide.
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
                    # event listener. A timing wait across 47 disclosures
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
                    # authenticated page, in nav order.
                    pages = (("/", 1), ("/display", 3), ("/flights", 37),
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
                        context = browser.new_context(
                            java_script_enabled=False, viewport=VIEWPORT_MIN_SUPPORTED)
                        try:
                            context.add_cookies([{
                                "name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                                "url": base_url}])
                            page = context.new_page()
                            page.goto(base_url + "/login")
                            page.fill("#password", TEST_PASSWORD)
                            page.click('button[type="submit"]')
                            page.wait_for_load_state("load")
                            page.goto(base_url + "/health")
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
                        finally:
                            context.close()
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
                    # companion/test_companion_app.py instead, where the
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
                        # Now a real edit, made the way a user makes one.
                        current = device_config.load_device_config(harness.tmpdir)["theme"]
                        other = next(t for t in device_config.THEME_IDS if t != current)
                        _click_control(page, 'input[name="theme"][value="%s"]' % other)
                        page.wait_for_timeout(200)
                        bar_shown = page.eval_on_selector(
                            "[data-dirty-bar]", "el => !el.hidden")
                        if not bar_shown:
                            return False, (
                                "expected the save bar to report the unsaved edit — this check "
                                "gates on the bar's own live answer, so a bar that never "
                                "appeared would make it vacuous")
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
                    "a Display page whose save bar reports unsaved edits issues ZERO requests when "
                    "the same trigger that fetched on the clean page fires — counted as REQUESTS, "
                    "not inferred from the DOM, because a page that fetched and then declined to "
                    "swap is a different and worse behaviour — against a control proving the clean "
                    "page does fetch (T-23-20/T-23-21, 23-06-PLAN.md Task 3)",
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
                        with _no_js_page(browser, base_url, "/display",
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
                            with _no_js_page(browser, base_url, route,
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
