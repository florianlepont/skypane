#!/usr/bin/env python3
"""Contract harness for companion/pages/history_page.py (CFG-06/CFG-10/
CFG-11) — the page that absorbed companion/pages/preview_page.py's entire
live-panel/render-gallery content in 06.6.4.1-05; that module itself was
deleted outright by 06.6.4.1-08 (D-22) once its standalone /preview page
route became a plain redirect to History.

Covers: the flight-history log's empty state, newest-first row ordering,
the two reused render-module presentation mappings (friendly aircraft-
type labels with a raw-designator fallback, the display-airline alias),
route-unavailable wording agreement with server/plane/render.py's own
ROUTE_FALLBACK_TEXT, monospace column styling, per-cell escaping
(including a markup-shaped callsign), degrade-not-raise behaviour
against an unreadable database; quick task 260903-etm's retirement of
History's top-of-page render-gallery <section> outright (developer
redirection superseding quick task 260903-c4o's own always-visible
render-gallery section on this same unmerged branch) — that the section
is fully absent (zero <h2, zero page-section, zero gallery-grid/
gallery-tile) both with seeded gallery content and with an empty
gallery, that the per-row View-panel mechanism and History's own card
disclosures survive in the same render, that the gallery filename-
timestamp helper degrades safely, the per-row View-panel lookup and
shared lightbox including a native title tooltip byte-equal to the
trigger's aria-label, that the orphaned colour caveat is rehomed into
the lightbox note exactly once, the unresolved-airline link to Health;
and one end-to-end HTTP round trip proving companion/app.py's router and
this page module agree, including a real PNG fetched over
/gallery/{name}.png (the route the per-row lightbox links to,
/preview.png having been retired outright by quick task 260903-c4o and
now 404ing) and the retired /preview page route's redirect to /history.

Every fixture is seeded programmatically into a temporary state
directory - flight events via server/history_db.py's own writer
functions, a real panel.bin via server.plane.render.render_panel(), and
gallery files as small real PNGs via Pillow - never a committed fixture
file, so this harness cannot drift from the schema/format those modules
define.

Stdlib-only, plus the modules under test (server.plane.render,
server.history_db) and Pillow - Pillow is a hard dependency of the
render pipeline this harness seeds fixtures through, so this harness
must be run under server/.venv's interpreter, not the bare system
python3. No pytest.

Usage:
    server/.venv/bin/python3 companion/test_view_pages.py
"""
import html
import math
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

from companion import auth  # noqa: E402
import companion.battery as battery  # noqa: E402
import companion.draw as draw  # noqa: E402
import companion.layout as layout  # noqa: E402
from companion.pages import airlines_page, health_page, history_page  # noqa: E402
from server import device_config  # noqa: E402
from server import history_db  # noqa: E402
from server.plane import illustrations  # noqa: E402
from server.plane import render as panel_render  # noqa: E402
# 19-08-PLAN.md Task 1 (D-21): the same crossing point airlines_page.py
# itself already sanctions (companion/pages/__init__.py only forbids a
# page module importing another page module, not a test harness
# importing server.poll_loop) - used solely to seed a real unresolved-
# prefix registry for the gap-strip checks below.
import server.poll_loop as poll_loop  # noqa: E402
# 21-06-PLAN.md Task 1 (D-19): same crossing point, used solely to seed
# a real Step-B manual-resolution entry (name saved, no artwork yet)
# for the upload-zone-unconditional checks below.
from server.plane import manual_resolutions  # noqa: E402

TEST_PASSWORD = "view-pages-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 83  # 79 + 4 (19-08-PLAN.md Task 3: D-22's edit-gated lightbox forms —
# 4 new checks: a default render has none of the three edit-only forms, a default render keeps
# exactly one resolve-name form, an edit_mode=True render has exactly one of each edit-only form,
# and a real HTTP GET proves the exact-"1" membership test end to end) — was 79
# 79 = 78 + 1 (19-08-PLAN.md Task 2: D-21/A-38's resolve-panel back link now
# names and targets Airlines instead of Health — 1 new check, the back link renders exactly
# once with href == AIRLINES_ROUTE) — was 78
# 78 = 76 + 2 (19-08-PLAN.md Task 1: D-21/A-38's "Unidentified airlines" gap
# strip — 2 new checks: a render with an eligible gap emits the strip's heading/sentence before
# the filter bar with no gap card in the curated grid, and a render with no gaps emits no strip
# at all) — was 76
# 76 = 73 + 3 (19-03-PLAN.md Task 3: D-20's visible "Copied" swap for 1.5s —
# 3 new checks: the rendered copy-btn__icon/copy-btn__label span pair with data-copy-feedback
# intact, copy-button.js referencing copy-btn__label/copy-btn--copied/1500ms, and style.css
# styling both classes) — was 73
# 73 = 70 + 3 (19-03-PLAN.md Task 2: A-37/D-20's per-row copy labels and
# real-success gating — retargeted the raw-label aria-label check in place, plus 3 new checks: 2
# distinct aria-labels on differently-named rows, each button naming its own row, and
# copy-button.js propagating execCommand's real result) — was 70
# 70 = 67 + 3 (19-03-PLAN.md Task 1: A-36/D-19's 7->6 column drop and
# clock-only Timestamp cell — retargeted the .data-table-wrap exact-match and 7-column checks in
# place, plus 3 new checks: the runway survives in the <tr title>/mobile details, the scroller is
# focusable and named, and the desktop Timestamp cell drops its relative-age suffix) — was 67
# 67 = 65 + 2 (19-01-PLAN.md Task 1: D-01's battery_percent() move — the
# retargeted battery.battery_percent() check, plus the two new boundary checks proving the
# function is gone from home_page and that companion/battery.py imports neither companion.pages
# nor server) — was 65
# 65 = 63 + 2 (phase 18: Home page) — was 63 # + 8 (phase 14 plan 14-05 Task 2: 8 new
# source-content checks pinning panel-lookup.js's own contract without a
# live DOM - no image.src="" anywhere; image.removeAttribute("src") is
# conditional, not unconditional at module scope; the shared populate
# function (openFromTrigger) is defined exactly once and called from at
# least two sites; location.search is read exactly once, at script init,
# outside any click-only-reachable function; every one of the eleven new
# data-view-panel-* attribute name literals appears in the file's source;
# the mode-governed elements' hidden assignments all occur, textually,
# before the shared function's own showModal() call; evt.preventDefault()
# appears exactly once, positioned after the trigger-null-check and
# before any showModal()-reaching call; and exactly one
# document.getElementById("panel-lookup-dialog")/document.addEventListener
# ("click", ...) pair still exists) = 63.
# 55 = 54 + 1 (phase 14 plan 14-01 Task 2: the new
# reflection-driven _view_panel_attr_constants_all_classified() check -
# _lightbox_dom_contract_three_file_guard() itself was restructured onto
# three classified token tuples in place, still one check) = 55.
# 54 = 52 + 2 (quick 260903-peo Task 3: UIR-17's desktop
# copy-button reveal stylesheet contract — [data-copy-value]-scoped, opacity
# + pointer-events only, both tr:hover/tr:focus-within named — and the
# cross-file markup guard pinning the [data-copy-value] discriminator that
# keeps the View-panel/eye button always visible)
# 52 = merge origin/main into
# claude/history-preview-gallery-32b974 (2026-09-03): this branch forked
# from main at 49 (46 + 3, quick task 260902-w4t, see below) and made a
# net +0 change of its own on top (quick task 260903-c4o +1 -> 50, quick
# task 260903-etm -5+4 -> 49 - see below for both). Independently, main
# went from that same 49 to 52 (+1 quick task 260902-v26, +2 quick task
# 260903-btu - both entirely absent from this branch until now). Net:
# 49 + 0 (this branch) + 3 (main) = 52.
#
# --- this branch's own history since the 49 fork point ---
# 49 = 50 - 5 (quick task 260903-etm: History's
# top-of-page render-gallery <section> retired outright, superseding
# quick task 260903-c4o's own always-visible section on this same
# unmerged branch - _render_gallery_nonempty_structure,
# _render_gallery_empty_state, _render_gallery_not_a_disclosure and
# _render_gallery_display_limit_newest_first all asserted structure that
# no longer exists, and _recent_renders_malformed_filename_caption_
# fallback's tile-class subject was deleted with the section - its
# residual "a malformed filename degrades safely" coverage already lives
# in _gallery_name_to_iso_fixtures and in nearest_gallery_entry()'s own
# unparseable-entry-is-skipped fixture) + 4 (quick task 260903-etm's
# replacement checks: _history_render_gallery_section_absent_with_content,
# _history_render_gallery_section_absent_when_empty,
# _view_panel_trigger_title_matches_aria_label,
# _colour_caveat_rehomed_into_lightbox_note).
# Deliberately KEPT rather than replaced, despite living among the
# retired group: _render_gallery_no_preview_apparatus_even_with_panel_file
# - every one of its assertions still passes unmodified, and its real
# subject is quick task 260903-c4o's /preview.png route retirement, not
# the render-gallery section this task removes; only its check()
# description prose was refreshed.
# 50 = quick task 260903-c4o's own tip on this same branch, +1 from the
# same 49 fork point below.
#
# --- main's own history since the same 49 fork point ---
# 52 = 47 + 5 (quick task 260902-w4t Task 3, UIR-04:
# _status_dot_title_backward_compatible_and_escaped,
# _corroboration_none_row_shows_short_label_with_tooltip, and
# _data_table_wrap_scroll_edge_affordance_css - status_dot()'s new
# backward-compatible title parameter, the shortened corroboration
# label's tooltip in both renderings, and the CSS-only scroll-edge
# affordance's background-attachment/pointer-events contract; Task 2,
# UIR-06: _hex_only_row_promotes_hex_to_primary - a callsign-less row
# with a hex promotes the hex into the primary slot on both the desktop
# cell and the mobile card, with a no-copy-button "no callsign" note,
# and a row with neither callsign nor hex renders without raising;
# Task 1, UIR-05: _airline_fallback_distinct_from_route_fallback - a
# no-airline row's AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT are
# distinct strings in distinct columns, and the unresolved-link's
# UNRESOLVED_LINK_CLASS is styled in style.css and present on the
# rendered anchor - all three merged in from main, additive to this
# branch's own chain below, zero overlap in the checks each side added).
# 47 = 44 + 1 (quick task 260902-v26 Task 3: render({}) with a
# literal empty dict still contains the .illustration-grid gallery
# container, pinning the ctx.get("state_dir") tolerance render(ctx) grew
# in this task) + 2 (quick task 260903-btu Task 4: a real, seeded
# history_page.render() call carries zero replace-related markup, and
# the two new Airlines-only lightbox constants each appear in
# panel-lookup.js/airlines_page.render()/style.css and never in a real
# history_page.render() call — _lightbox_dom_contract_three_file_guard()
# and _airlines_lightbox_constants_match_history() themselves were left
# unmodified, since their existing tokens/pairs are all still true).
# 44 = 43 + 1 (quick task 260902-tli Task 2: the
# airlines_page/history_page cross-module LIGHTBOX_DIALOG_ID/
# _VIEW_PANEL_*_ATTR equality guard. _lightbox_dom_contract_three_file_
# guard() was widened in place to also assert the six shared tokens
# against a real airlines_page.render() output - no count change from
# that retarget) + 1 (quick task 260902-v26 Task 3: render({}) with a
# literal empty dict still contains the .illustration-grid gallery
# container, pinning the ctx.get("state_dir") tolerance render(ctx) grew
# in this task) + 2 (quick task 260903-btu Task 4: a real, seeded
# history_page.render() call carries zero replace-related markup, and
# the two new Airlines-only lightbox constants each appear in
# panel-lookup.js/airlines_page.render()/style.css and never in a real
# history_page.render() call — _lightbox_dom_contract_three_file_guard()
# and _airlines_lightbox_constants_match_history() themselves were left
# unmodified, since their existing tokens/pairs are all still true).
# 43 = 06.6.4.1-08 Task 3: 56 - 16 (Section 2's whole
# companion/pages/preview_page.py-specific test section deleted outright —
# the module itself is deleted, and every one of its 16 checks either has
# a live History-side equivalent already (plan 05) or was carried over
# onto history_page.py's absorbed symbols below) + 3 (2 carried-over
# checks the History side did not already have — _gallery_name_to_iso()'s
# degrade-safely fixtures, and a malformed gallery filename's
# caption-fallback rendering in the Recent-renders disclosure — plus 1
# new check pinning that a View-panel trigger still carries non-empty
# <svg icon markup after the nav shrink) = 43. Section 3's end-to-end
# check was retargeted in place (still 1 check, not counted as new) to
# assert the /preview -> /history redirect instead of a 200/"Preview"
# heading, while still proving /preview.png (untouched) returns a real
# PNG. # 56 = 51 (pre-06.6.4.1-05 Task 3) + 5 (06.6.4.1-05
# Task 3: the unresolved-airline link absent for a resolved airline,
# present exactly once per representation for an unresolved airline,
# keyed on the airline label and not the route label, its href matching
# health_page.SERVER_DATA_SECTION_ID, and no prefix-registry table
# duplicated onto History). Prior baseline: 47 (pre-06.6.4.1-05 Task 2) +
# 4 (06.6.4.1-05 Task 2: nearest_gallery_entry()'s at-or-before/boundary/skip/None
# behaviour; three interleaved rows' desktop+mobile View-panel triggers
# carrying byte-identical, correctly-targeted attributes plus exactly one
# lightbox dialog; zero triggers/zero dialog with an empty gallery entry
# list; the LIGHTBOX_DIALOG_ID/data-view-panel-*/lightbox__* three-file
# DOM-contract guard). Prior baseline: 42 (pre-06.6.4.1-05) + 5
# (06.6.4.1-05 Task 1: History's own Now-showing section with a panel
# present/absent, the Recent-renders disclosure closed by default with a
# correct shown-count summary, the same disclosure's empty-gallery
# no-renders empty state, and confirmation that Preview's page-level
# freshness apparatus (data-loaded-at/data-stale-banner) was deliberately
# not ported). Prior baseline: 41 (pre-06.6.4-05) + 1 (06.6.4-05 Task 3: the
# shared [data-filter-clear] Clear-control contract - History renders the
# attribute, style.css styles it by attribute, no class-keyed rule
# competes). Prior baseline: 35 (pre-06.6.3-07) + 6 (06.6.3-07 Task 3:
# _gallery_name_to_iso() fixtures; matte-frame/sizing/caption re-asserted
# against the full render() output; no-panel branch stays img/frame-less
# in the full render() output; gallery sizing/links/D-10 window label
# re-asserted against the full render() output; a malformed gallery
# filename's caption-fallback re-asserted against the full render()
# output; Preview's data-loaded-at/data-stale-banner markers). Prior
# baseline: 30 (pre-06.6.3-05) + 5 (06.6.3-05 Task 3: filter bar markers
# present-once; data-filter-text on both representations; desktop
# Callsign+Hex cell's 2 copy buttons + feedback siblings; mobile details
# region's 3 copy buttons + feedback siblings; confirmed_state/
# tracked_runway presentation labels re-asserted against the full
# render() output). Prior baseline: 28 (pre-06.6.2-04) + 2 (06.6.2-04:
# History/Preview page_header() shared component checks). Before that:
# 25 (pre-06.6-03) + 3 (06.6-03 Task 1: History Timestamp column reads
# "ISO (Nm ago)"; Task 2: Preview's Captured caption reads "Captured ISO
# (Nm ago)"; Task 3: corroboration copy cross-page drift guard, D-03)
EXPECTED_CHECK_COUNT = 92  # 20-06-PLAN.md Task 3 (D-05/D-09): +2 (90 -> 92)
# — a fully-seeded Home render under lang='fr' end to end (page title,
# section headings, status-row labels, next-update headline, no English
# leaking in, callsign/airline data untranslated) plus the identical
# render under the default language re-asserting every pre-existing
# English needle, and a check that every key in companion/i18n_fr/
# home.py's own CATALOG is also a key of the merged companion.i18n_fr.
# CATALOG (proving the auto-merge package picked the module up).
# Recomputed directly against the real on-disk check(...) call count at
# execution time (92/92 pass), not trusted from arithmetic alone.
# 90 = 20-06-PLAN.md Task 2 (D-17.2/D-18/D-20): +3
# (87 -> 90) — the recent-flights thumbnail resolved-vs-placeholder check,
# the hero's flight-one-liner presence/absence plus .preview-frame-before-
# .status-card document-order check, and a French-render check proving
# Home's headings and a thumbnail's alt text translate while the
# callsign/airline data itself stays untranslated. Recomputed directly
# against the real on-disk check(...) call count at execution time
# (90/90 pass), not trusted from arithmetic alone.
# 87 = 20-06-PLAN.md Task 1 (D-16/D-17/D-21): net +2
# (85 -> 87) — retargeted the seeded-render check and the empty-ctx check
# off the deleted Quick-actions/stat_tile markup, replaced the single
# _home_page_renders_next_wake_figure_only_when_known() check (-1) with
# three new checks (+3): no quick-action markup/no /quick/ action
# anywhere plus exactly three status-row blocks with the Frame verdict
# appearing exactly once (the 20-RESEARCH.md Pitfall 3 regression test),
# the status card's "Next update ≈"/"Expected since" headline across
# future/past/never-checked-in next-wake states, and the "See details on
# Health" link's simple_mode gating (D-30). Recomputed directly against
# the real on-disk check(...) call count at execution time (87/87 pass),
# not trusted from arithmetic alone.
# 85 = 19-12-PLAN.md Task 3 (D-13/S-02): +2 (wake.
# next_wake_at_iso()'s None-for-falsy/unparseable/unknown-interval contract
# plus the screen-on/screen-off arithmetic, and Home rendering the ≈
# figure only when both a check-in and an interval are known). 83 + 2 =
# 85, recomputed directly against the real on-disk check(...) call count
# at execution time (85/85 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 97  # 20-10-PLAN.md Task 1 (D-36): +5 (92 -> 97) — a
# default render carries exactly one "Change pictures" toggle linking to
# /airlines?edit=1 plus its explanatory sentence, an edit_mode=True render
# shows "Done" linking back to /airlines with no query, a simple_mode=True
# render carries neither the toggle nor its sentence, a simple_mode=True
# AND edit_mode=True render still carries every edit-only lightbox form
# (D-30's presentation-not-access-control gate proven directly, not just
# asserted), and a French render shows "Modifier les images"/"Terminé".
# Recomputed directly against the real on-disk check(...) call count at
# execution time (97/97 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 100  # 20-10-PLAN.md Task 2 (D-05): +3 (97 -> 100) —
# a French render translates the page title, filter label, lightbox
# aria-label and toggle text while a real curated airline name stays
# untranslated data; a fully-seeded French render (gap strip + resolve
# panel) shows every new French string with no English leaking in, the
# seeded example callsign stays untranslated, and the identical seeded
# render under the default language still carries every pre-existing
# English needle; and every key of companion/i18n_fr/airlines.py is a
# key of the merged CATALOG. Recomputed directly against the real
# on-disk check(...) call count at execution time (100/100 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 103  # 20-10-PLAN.md Task 3 (D-05): +3 (100 -> 103) —
# a French render of Flights translates the page title, column headers
# and filter label while a seeded callsign stays untranslated data; a
# fully-seeded French render shows the direction words, the unresolved-
# airline fallback, the no-callsign note, the disclosure summary and the
# filter's Clear button with no English leaking in, the seeded callsign
# stays untranslated, and the identical seeded render under the default
# language still carries every pre-existing English needle; and every
# key of companion/i18n_fr/flights.py is a key of the merged CATALOG.
# Recomputed directly against the real on-disk check(...) call count at
# execution time (103/103 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 104  # 20-11-PLAN.md Task 3 (D-06): +1 (a Flights
# render's copy buttons carry data-copied-text="Copied" under the
# default language and data-copied-text="Copié" under lang='fr' — the
# feedback text companion/static/copy-button.js reads at click time
# instead of a hardcoded English literal). 103 + 1 = 104, recomputed
# directly against the real on-disk check(...) call count at execution
# time (104/104 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 105  # 20-11-PLAN.md Task 3/D-06 orchestrator
# addendum: +1 (History's filter bar carries data-filter-count-
# template="%d of %d shown" under the default language and the French
# "%d sur %d affichés" under lang='fr' — companion/static/list-filter.js
# reads this attribute instead of hardcoding the English words "of"/
# "shown"). 104 + 1 = 105, recomputed directly against the real on-disk
# check(...) call count at execution time (105/105 pass), not trusted
# from arithmetic alone.
EXPECTED_CHECK_COUNT = 106  # Polish fix 2 (French Home status rows):
# +1 (Home's status card, fed a REAL health_page.compute_health_state()
# result computed under lang='fr', fully localises the Frame/Flight-
# data rows' timestamps — no English month abbreviation or ' ago'
# survives — and joins the Flight-data row's separate clauses with
# ' · ' instead of running them together; the regression guard for the
# companion/app.py page_context() request-ordering bug this fix
# closes). 105 + 1 = 106, recomputed directly against the real on-disk
# check(...) call count at execution time (106/106 pass), not trusted
# from arithmetic alone.
EXPECTED_CHECK_COUNT = 107  # Polish fix 5 (Registry labels shown in
# French, D-05): +1 (a French Flights render translates the
# tracked_runway cell's registry label — "Runway 3 (07/25)" ->
# "Piste 3 (07/25)" — with no English label leaking in). 106 + 1 = 107,
# recomputed directly against the real on-disk check(...) call count
# at execution time (107/107 pass), not trusted from arithmetic alone.
# 21-01-PLAN.md Task 2 (D-17): -2. The two airlines toggle checks that
# exercised its now-deleted display-mode gate are deleted outright
# (the toggle's gate no longer exists; existing default/edit_mode=True
# coverage is unaffected). The Home health-link check is rewritten in
# place to assert the link always renders (net 0 for that one).
# 107 - 2 = 105, recomputed directly against the
# real on-disk check(...) call count at execution time (105/105 pass),
# not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 105

# 21-03-PLAN.md Task 1 (D-15): +3 net. Several pre-existing desktop-row
# checks were retargeted in place (no count change) to the new
# five-column/two-line-cell shape; three genuinely new checks were
# added (status_dot()'s visually_hide_label keyword default, the
# dot-only Corroboration cell, the When/Flight one-primary/one-
# secondary shape). 105 + 3 = 108, recomputed directly against the real
# on-disk check(...) call count at execution time (108/108 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 108

# 21-03-PLAN.md Task 2 (D-15/R-12): +3 net. Three genuinely new checks
# were added (the detail-row/summary-row pairing by aria-controls/id
# with no hidden/inline-style and aria-expanded="false", the hex/ISO/
# runway living in the detail row and not the summary row, no inline
# <script>/on*= handler anywhere on the page); one pre-existing check
# (the newest-first row count) and one (the one-line-cell contract) were
# retargeted in place (no count change) for the new sibling detail row.
# 108 + 3 = 111, recomputed directly against the real on-disk check(...)
# call count at execution time (111/111 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 111

# 21-03-PLAN.md Task 3 (D-15): +2. The static half of the 880px
# width-budget guarantee a Python harness can actually assert: the
# table.data-table--flights padding rule uses var(--space-sm) on both
# axes, and the rendered <thead> carries exactly six <th> cells in
# both en and fr. 111 + 2 = 113, recomputed directly against the real
# on-disk check(...) call count at execution time (113/113 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 113
# 21-04-PLAN.md Task 3 (D-04/D-05/R-06): net 0 — four checks retargeted
# in place at the rebuilt Home (the document-order check now asserts
# header -> .frame-strip -> .home-status-grid -> .home-picture-row with
# .preview-frame before the recent-flights section; the quick-action
# check now asserts quick-action markup exists exactly once, inside
# the strip, with exactly three stat-tile elements and the Frame
# verdict exactly once; the headline check now calls
# layout.frame_strip_html() instead of the deleted
# home_page._status_card_html(); the Health-link check now calls
# home_page._status_tiles_html()), plus one new assertion folded into
# the already-seeded-state check (.preview-frame before a real
# .recent-flight row). No check added or removed. 113 + 0 = 113,
# recomputed directly against the real on-disk check(...) call count
# at execution time (113/113 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 113
# 21-06-PLAN.md Task 1 (D-19): +1 - a new check that a default
# (edit_mode absent) render of a Step-B entry (name saved, no artwork
# yet) contains exactly one upload zone, zero delete forms and zero
# replace forms. 113 + 1 = 114, recomputed directly against the real
# on-disk check(...) call count at execution time (114/114 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 114
# 21-06-PLAN.md Task 2 (D-19): net 0 — three checks retargeted in
# place, no check added or removed. _airlines_default_render_has_no_
# edit_only_forms now also asserts exactly one upload zone present
# (the lightbox's own copy is unconditional too) and switches its
# replace/delete absence assertions to exact `class="..."` matching
# (a bare substring would false-positive on lightbox__replace-hint/
# -icon, which now render unconditionally as part of the upload
# zone's own markup). _airlines_default_render_step_b_upload_zone_
# unconditional now expects exactly two upload zones (fallback panel
# + lightbox) instead of one, since both surfaces' guards are dropped
# together. _airlines_edit_query_param_exact_one_membership_test drops
# RESOLVE_UPLOAD_ZONE_CLASS from its edit-only tuple and instead
# asserts it present across every query variant (the exact-"1"
# membership test no longer governs it). 114 + 0 = 114, recomputed
# directly against the real on-disk check(...) call count at
# execution time (114/114 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 114
# 22-02-PLAN.md Task 1 (D-03/CFG-26): net 0 — the quiet-hours-active
# fixtures (a window opening during the base interval, an enabled-but-
# inactive window, an active window beating a screen-off cadence, and
# the richer next_wake_status() accessor's None-triple/interval/
# hold_reason results) were added as new assertions INSIDE the existing
# _wake_next_wake_at_iso_contract() check function rather than as new
# check(...) call sites, matching the style every assertion above it
# already uses (one check() call bundling several named assertions).
# 114 + 0 = 114, recomputed directly against the real on-disk check(...)
# call count at execution time (114/114 pass), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 114
# 22-02-PLAN.md Task 2 (D-03/D-04): +2 - two new checks:
# _frame_state_resolve_state_contract() (the due/held/late/unknown
# resolution, the invisible grace window, the held-cannot-escalate
# rule, and the nightly regression end to end through
# wake.next_wake_status()) and _frame_state_view_free_and_i18n_contract()
# (the view-free/no-dot-class source checks plus the six copy
# constants' EN/FR round trip). 114 + 2 = 116, recomputed directly
# against the real on-disk check(...) call count at execution time
# (116/116 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 116
# 22-07-PLAN.md Task 1: +5 (116 -> 121) — Home's Frame tile matches the strip byte-for-byte
# on the nightly held regression (same clock, zero warn/error tokens) and flips to late
# together with it; the Flight-data tile renders exactly one verdict with Health's verdict-
# free pipeline_detail_html beneath it, never Health's own verdict a second time (B2);
# airline names route through display_airline_name(), matching Flights (X4); and exactly one
# element on the page is named "Frame" (X4). Re-derived by running the harness (121/121).
EXPECTED_CHECK_COUNT = 121
# 22-07-PLAN.md Task 2: +5 (121 -> 126) — the recent-flight time cell carries no monospace
# class and reads on one line (.time-value clock, .cell-inline-sep, .time-value__age);
# .home-status-grid declares align-items: stretch and .recent-flight__time declares
# white-space: nowrap in the stylesheet; the real thumbnail and its placeholder each join
# their respective shipped CSS treatment; and the single @supports selector(:has(*)) block
# stays pinned at exactly one. Re-derived by running the harness (126/126).
EXPECTED_CHECK_COUNT = 126
# 22-09-PLAN.md Task 1 (X5): +4 (126 -> 130) — the rendered table carries zero visible
# More/Plus/Less/Moins button labels and exactly one icon-only toggle per row, each with a
# translated aria-label that swaps with its state and names the picture inside; no <tr> in the
# RENDERED page carries aria-expanded and every occurrence sits on a <button> (a source-level
# count cannot gate this — history_page.py's own source carries the string more than once);
# style.css's new .row-toggle block reuses .copy-btn's 22x22/-11px inset/14px glyph pattern with
# no new size literal, and the pointer cursor is keyed only on the class flight-rows.js adds at
# load; and flight-rows.js reads every attribute name the page renders, swaps aria-label rather
# than a visible label, guards interactive click targets and uses no markup-writing sink, while
# the server still renders every detail row visible. Re-derived by running the harness (130/130).
EXPECTED_CHECK_COUNT = 130
# 22-09-PLAN.md Task 2 (X5): +5 (130 -> 135) — one day-separator row per EUROPE/PARIS calendar
# day, translated in both languages, with a row whose UTC day differs from its Paris day grouped
# by the Paris one; the separator's absolute label proven equal to the day portion of
# layout.local_clock_text()'s own cross-day output, history_page.py proven free of any direct
# date-formatting call, paris_day() proven to degrade rather than raise, and the separator's CSS
# rule proven to declare no positioning (T4); the phone card's route/state pair joined by the
# module's existing middle dot; the raw ISO proven to appear ONLY inside a data-copy-value
# attribute, with the visible timestamp in the .time-value role; and the phone card's airline
# name plus its artwork thumbnail on the shared white-backing rule, with no <img> at all when no
# artwork file exists. EIGHT further checks were RETARGETED in place with no count change: the
# three-events row count (+1 separator), the summary row's now-absent picture control, that
# control's title/visible-label/no-aria-label contract, its small-grey-secondary treatment
# replacing the icon, the per-row trigger attributes now read from the detail row, and the four
# unresolved-link checks now pinning the one-hop resolve route. Re-derived by running the
# harness (135/135).
EXPECTED_CHECK_COUNT = 135
# 22-09-PLAN.md Task 3 (B11): +1 (135 -> 136) — the markup half of the fix the browser harness
# measures: History's count and Clear render as siblings inside one .filter-bar__meta group,
# whose page-agnostic rule declares flex/centre/nowrap/auto-left-margin so plans 22-11 and 22-12
# can adopt it verbatim, with no page-scoped fork of the converged [data-filter-clear] rule and
# no per-page variant of the group itself. Re-derived by running the harness (136/136).
EXPECTED_CHECK_COUNT = 136
# 22-11-PLAN.md Task 1 (B5/D-05): +3 (136 -> 139) — the resolve dialog's first-seen/last-seen
# attributes proven to carry FORMATTED Europe/Paris text byte-identical to the no-JS path's own
# rendered <dd> text for the same row (a 15:49 UTC sighting reading 17:49, so an unconverted
# value cannot pass on shape alone), with zero ISO-8601 timestamps anywhere in either render;
# panel-lookup.js proven to contain no date-parsing or date-formatting API at all and to assign
# both values straight to textContent; and Save and Close proven to share one .lightbox__actions
# row (quiet Close first, primary re-attached by the native form= attribute) while the no-JS
# fallback keeps its own submit inside its own form, with the row's rule declaring
# flex/centre/space-between, no shared height (C4) and no .btn-- family.
# Re-derived by running the harness (139/139).
EXPECTED_CHECK_COUNT = 139
# 22-11-PLAN.md Task 2 (X7, D-06/B16): +4 (139 -> 143) — the Change pictures toggle and its
# caption proven normal-case via text-transform: none on the toggle's OWN existing class plus a
# caption selector scoped inside the wrapper, with .page-header__screen itself keeping the
# uppercase the Device page's caption usage needs and no .btn-- family anywhere; an edit-mode
# render proven to carry exactly one .banner__pill Editing badge and exactly one
# .calendar-disconnect-btn Replace control per card, each carrying the SAME full data-view-panel
# vocabulary the zoom trigger carries, with a verb-plus-noun label whose accessible name contains
# it in both languages, against a normal render carrying neither and exactly one
# .calendar-disconnect-btn base rule serving both consumers; the manual-resolution count proven to
# render as a real filter control inside the filter bar wearing .airline-card__chip's voice with
# the 12px bare link's copied property list retired, reading "1 manual resolution" (FR "1
# resolution manuelle") at one entry and "2 manual resolutions" at two; and .illustration-grid
# proven to take a FIXED repeat(2, minmax(0, 1fr)) template below 960px while the desktop
# auto-fill idiom is left alone. Re-derived by running the harness (143/143).
EXPECTED_CHECK_COUNT = 143
# 23-03-PLAN.md Task 1 (D14/CFG-34): +1 — History's Timestamp cells now
# carry concise_timestamp_html()'s new <time data-relative> element.
# History is the widest surface that reads THROUGH that function, and
# its cells travel data_table()'s raw_columns path, so this is also the
# proof that a raw-markup producer's new element arrives as markup
# rather than as a double-escaped "&lt;time" literal on the page — the
# one failure mode T-23-09 names. Re-derived by running the harness
# (144/144).
EXPECTED_CHECK_COUNT = 144
# 23-03-PLAN.md Task 2 (D14/CFG-34): +2 — Home's two visible relative
# ages. The recent-flight age is converted by this task and its check
# went RED first (145/146, "expected the age half to be a <time
# data-relative> element, got '10m ago'"). The rendered-picture caption
# was ALREADY converted, by Task 1, because it reads through
# concise_timestamp_html() — so its check passed the moment it was
# written. That is the point of writing it rather than inspecting the
# call chain: the caption reaches the page through an i18n template's
# own "%s", and an escaping mistake THERE would paint literal markup
# instead of removing an element. Both checks assert the rendered text
# is what the page produced before, in both languages. Re-derived by
# running the harness (146/146).
EXPECTED_CHECK_COUNT = 146
# 23-08-PLAN.md Task 1 (D7/CFG-37): +2. One pins the stable EVENT
# identity both Flights renderings now carry — non-empty, unique, the
# same set on both sides, and unchanged when a newer detection arrives
# at the top, which is the one property the row's position does not
# have and the whole basis of the new-row highlight. One pins the loop's
# two gates on the page's own output: exactly one data-loaded-at marker,
# a witness in the rendered markup for every registry region, and no
# region naming the filter input list-filter.js captured at load.
# 146 + 2 = 148, recomputed by RUNNING.
EXPECTED_CHECK_COUNT = 148
# 23-08-PLAN.md Task 2 (D3/CFG-32's two Flights clauses + D7's card
# clause): +4. The detail row's grid reveal wrapper and the deliberate
# one-directional animation whose collapsed end state is still
# display: none; the chevron's transform transition and the stylesheet's
# unmoved live prefers-reduced-motion count; the phone card's face as
# its own <summary> with the resolve link kept out of it; and the filter
# count animating its element rather than its number.
# 148 + 4 = 152, recomputed by RUNNING.
EXPECTED_CHECK_COUNT = 152
# 23-10-PLAN.md Task 2 (D3/CFG-32): +1. Both <dialog>s arrive through ONE
# @starting-style entrance on .lightbox[open] - one rule, two dialogs -
# fading and zooming from opacity 0 over var(--motion-fast), with
# `display`/`allow-discrete` deliberately absent (a modal that has not
# reached display:none is an invisible sheet over the page) and
# ::backdrop unanimated (the global reduced-motion override matches only
# element selectors and cannot reach it). 152 + 1 = 153, re-derived by
# RUNNING.
EXPECTED_CHECK_COUNT = 153
# 24-04-PLAN.md Task 3 (CFG-40): +1 — Home's small battery ring. The
# check deliberately does NOT grep for `draw.` in two page modules: both
# files could import the emitter and still draw two different pictures.
# It renders BOTH pages and compares the two rings' PROPORTIONS —
# radius-over-box and stroke-over-box identical while the boxes
# themselves differ — which is exactly "one drawing at two sizes" and is
# the property a drifting copy destroys first. It also pins the ring as
# an ADDITION (the verdict, the "≈ NN%" and the millivolt detail all
# still printed, which is what keeps the drawing's aria-hidden honest),
# the ring's placement inside the Battery tile rather than merely on the
# page, the frame verdict still appearing exactly once (a recorded fixed
# bug here), and no ring at all for a device with no reading.
# 153 + 1 = 154, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 154
# 24-06-PLAN.md Task 1 (CFG-42): +4 - the time domain. One proves the
# new scale is a TIME scale and not the index scale beside it (the two
# are indistinguishable on an evenly-spaced fixture, so it is written
# around the case they disagree about: two instants an hour apart stay
# 1/24 of the band apart however many others are on it). One renders a
# wrapping night window as two spans rather than one inverted one. One
# pins the collapse and its exact reported count. One pins the emitted
# class vocabulary and the absence of any colour literal.
# 154 + 4 = 158, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 158
# 24-06-PLAN.md Task 2 (CFG-42): +3 - the band on Home. One draws it
# for the Paris day with its caption, and covers the empty day and the
# unreadable database (T-24-06-D). One shades the configured
# quiet-hours window and nothing at all when it is off. One pins the
# Paris/UTC boundary in BOTH directions plus a real 25-hour Paris day,
# counts render()'s history.db reads (2 before this plan, 3 after) and
# re-checks that the frame verdict still appears exactly once.
# 158 + 3 = 161, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 161
# 24-08-PLAN.md Task 1 (CFG-44): +1 — D4's hero. One check, written
# against the ONE failure mode the requirement has: a hero that looks
# composed but carries its own copies of the ring and the band. It pins
# a single hero container holding the shared Frame strip (rendered once,
# never inlined a second time), the tiles and the day band; the picture
# row OUTSIDE it; exactly one ring and exactly one band, both inside it,
# matched on whole class attributes because the band frame's own name is
# a prefix of the span's and the mark's; no geometry and no unqualified
# battery_percent( in the page module; and the recorded
# frame-verdict-exactly-once bug re-asked in BOTH languages, since a
# hero is precisely the shape that reintroduces it.
# 161 + 1 = 162, re-derived by RUNNING (162/162).
EXPECTED_CHECK_COUNT = 162
# 24-08-PLAN.md Task 2 (CFG-44): +2 — "fed by", proven. One is
# STRUCTURAL: the hero's ring and Health's carry one class vocabulary
# COMPUTED from the markup, the hero's band draws three shapes and not
# one, every class either emits is a constant companion/draw.py itself
# names, and neither the page module nor the check itself writes any of
# those strings down — a literal keeps passing against a forked copy
# that still uses the old one. One is BEHAVIOURAL, and is what CFG-44
# actually asks for: a class constant inside draw.py is replaced at
# check time and both the hero and the page the emitter was borrowed
# from change, while the band's own mutation moves the hero and leaves
# Health byte-identical (the mutation is targeted, not a global
# perturbation).
# 162 + 2 = 164, re-derived by RUNNING (164/164).
EXPECTED_CHECK_COUNT = 164

# quick task 260921-n2n Task 1: +1 (the Safari contact-autofill
# suppression-attributes check on History's search filter input).
# 164 + 1 = 165, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 165

# quick task 260921-n2n Task 2: +1 (the contextCallsign.textContent
# gated-on-count check). 165 + 1 = 166, re-derived by RUNNING.
EXPECTED_CHECK_COUNT = 166

# 29-01-PLAN.md (CFG-81): -4 net. Five checks retired outright (the
# edit_mode=True "one of each edit-only form" duplicate, the
# "Change pictures" toggle default-render check, the "Done" toggle
# edit_mode=True check, the French toggle-label check, and the CSS-rule
# .airlines-edit-toggle in-normal-case check — its own CSS rule block is
# deleted by Task 1 so it cannot be retargeted); one new absence check
# added (no toggle class, no ?edit= literal, either language) covers the
# property worth keeping from two of those retirements. Two checks
# inverted/replaced in place (net 0 each): the default-render "no
# edit-only forms" check now asserts the opposite (forms always
# present), and the badge/per-card-control check now asserts their
# absence plus the trigger's own vocabulary as a relationship. One
# browser-level check retargeted in place (net 0): the exact-"1"
# membership test is gone with the parameter, replaced by proving the
# dialog's forms render unconditionally over real HTTP. 5 retired - 1
# added back = -4. 166 - 4 = 162, re-derived by RUNNING (162/162 pass).
EXPECTED_CHECK_COUNT = 162

# 29-02-PLAN.md (CFG-82): +2 net. One existing check
# (_airlines_gap_strip_renders_before_filter_bar_with_heading_and_no_grid_placeholder,
# renamed to its "_after_the_gallery_" form) is retargeted in place (net
# 0) to the new order — the strip now renders after the filter bar and
# the gallery grid, not before them. Two checks are new: one asserts the
# whole page's section order as a chain of index relationships (title <
# filter < gallery < gap strip < lightbox, each literal exactly once);
# one re-proves render()'s existing no-chrome gate survives the reorder
# untouched (a gap-cards-only fixture still shows the filter bar, a
# neither fixture shows none). 0 (retarget) + 2 (new) = +2.
# 162 + 2 = 164, re-derived by RUNNING (164/164).
EXPECTED_CHECK_COUNT = 164

# 29-03-PLAN.md (CFG-83): +1 net. Task 1 retargets the existing
# registry-witness check's witness dict (a ".flights-more" entry added
# alongside the new swap-registry region) in place — net 0, no new
# check(...) call. Task 2 adds one new check: the
# .history-card__primary two-track-grid relationship (CSS declarations
# plus all three primary_value_html branches producing a placeable
# child set). 0 (retarget) + 1 (new) = +1. 164 + 1 = 165, re-derived by
# RUNNING (165/165).
EXPECTED_CHECK_COUNT = 165

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# --- lightbox DOM-contract token classification (phase 14 plan 14-01 Task 2) ---
#
# _lightbox_dom_contract_three_file_guard() below used to carry a single
# inline `tokens` tuple. That worked while History and the Airlines
# gallery rendered an identical vocabulary, but Airlines-only lightbox
# markup (the replace form) already exists today and this phase is about
# to add more server-rendered vocabulary that panel-lookup.js never
# reads. Restructuring the guard's data into three explicitly-scoped
# tuples, each with its own present/absent contract, lets the guard keep
# growing without ever again silently degrading into "shared" coverage
# for something that is provably not shared.
#
# _view_panel_attr_constants_all_classified() (below, in main()) enforces
# by reflection that every airlines_page._VIEW_PANEL_*_ATTR constant's
# *value* lives in exactly one of these three tuples - a constant left
# out of all three, or placed in two at once, fails the harness by
# construction rather than by someone remembering to update this list.

# Must appear in companion/static/panel-lookup.js's source, in the
# rendered History page, and in the rendered Airlines page - the
# vocabulary every one of the three genuinely shares today.
_LIGHTBOX_SHARED_TOKENS = (
    history_page.LIGHTBOX_DIALOG_ID,
    "data-view-panel-src",
    "data-view-panel-caption",
    "lightbox__image",
    "lightbox__caption",
    "lightbox__note",
    "data-view-panel-close",
)

# Must appear in panel-lookup.js's source and in the rendered Airlines
# page, and must be absent from the rendered History page - History
# deliberately renders no replace form and never should (see
# airlines_page.py's own comment on _VIEW_PANEL_REPLACE_ACTION_ATTR).
#
# Phase 14 plan 14-05 Task 2 promotes every member 14-02 staged in
# _LIGHTBOX_RENDER_ONLY_TOKENS (below, now empty) into this tuple:
# panel-lookup.js now reads every one of the eleven new
# data-view-panel-* attributes and looks up every one of the six new
# dialog classes, and every one of them is, like the replace form
# before it, genuinely Airlines-only - History never renders a
# resolve/gap/manual surface, so none of Phase 14's own new tokens ever
# lands in _LIGHTBOX_SHARED_TOKENS.
_LIGHTBOX_AIRLINES_ONLY_TOKENS = (
    "data-view-panel-replace-action",
    "lightbox__replace",
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
    airlines_page.LIGHTBOX_HEADING_CLASS,
    airlines_page.LIGHTBOX_MANUAL_NOTE_CLASS,
    airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS,
    airlines_page.LIGHTBOX_DELETE_CLASS,
    airlines_page.RESOLVE_CONTEXT_CLASS,
    airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
)

# Server-rendered vocabulary the script does not read yet: asserted
# present in the rendered Airlines page only, with no assertion at all
# against panel-lookup.js. A staging area for one wave at most - plan
# 14-05 Task 2 emptied this back to () by promoting every token it held
# (the eleven new data-view-panel-* attribute values, the four
# new/promoted dialog classes, resolve-context, resolve-upload-zone)
# into _LIGHTBOX_AIRLINES_ONLY_TOKENS above, once panel-lookup.js
# learned to read/look up all of them. Stays empty absent a future wave
# introducing a fourth rendered-but-not-yet-scripted token.
_LIGHTBOX_RENDER_ONLY_TOKENS = ()

# The eleven data-view-panel-* attribute name literals 14-02 added to
# the vocabulary (14-05 Task 2's own check #5) - built from the same
# airlines_page constants already threaded into
# _LIGHTBOX_AIRLINES_ONLY_TOKENS above, never a second hand-copied list.
_NEW_VIEW_PANEL_ATTR_NAMES = (
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
)


def _strip_js_comments(src):
    """Crude but sufficient for this one hand-written file: strips
    /* */ block comments and // line comments so a source-content check
    can search "real code" without a comment's own prose (e.g. an
    explanatory mention of the exact anti-pattern being pinned as
    absent) producing a false positive. Not a full JS tokenizer - does
    not account for either sequence appearing inside a string literal -
    but panel-lookup.js's own actual string literals never contain "//"
    or "/*", so this is safe for this file's real content.
    """
    without_block = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    without_line = re.sub(r"//[^\n]*", "", without_block)
    return without_line


def _read_panel_lookup_source():
    js_path = os.path.join(HERE, "static", "panel-lookup.js")
    with open(js_path) as fh:
        return fh.read()


# --- fixture helpers -----------------------------------------------------


def _mkstate(prefix):
    return tempfile.mkdtemp(prefix="skypane-view-pages-%s-" % prefix)


def _seed_runway_events(state_dir, events):
    """`events`: an iterable of kwarg dicts for record_runway_event()."""
    with history_db.open_db(state_dir) as conn:
        for fields in events:
            history_db.record_runway_event(conn, **fields)


def _seed_unresolved_prefixes(state_dir, registry):
    """19-08-PLAN.md Task 1 (D-21): mirrors
    companion/test_status_pages.py's own helper of the same name — the
    one sanctioned write path for a real `poll_state.json`'s
    `unresolved_prefixes` dict, never a hand-written JSON literal."""
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def _write_panel_file(state_dir):
    """A real, production-produced 960,000-byte panel.bin - the same
    bytes server.poll_loop.write_panel_atomic() would write - so the
    preview round trip this harness exercises is against genuine
    production output, not a hand-built fixture.
    """
    os.makedirs(state_dir, exist_ok=True)
    packed = panel_render.render_panel(None, "empty")
    with open(os.path.join(state_dir, "panel.bin"), "wb") as fh:
        fh.write(packed)


def _write_gallery_png(path):
    from PIL import Image
    Image.new("RGB", (4, 4), color=(200, 200, 200)).save(path, format="PNG")


def _seed_gallery(state_dir, names):
    gallery_dir = os.path.join(state_dir, "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    for name in names:
        _write_gallery_png(os.path.join(gallery_dir, name))


def _history_ctx(state_dir, now=None, gallery_entries=None, flights_limit=None):
    return {
        "state_dir": state_dir,
        "now": now or history_db.utc_now_iso(),
        "gallery_entries": gallery_entries or [],
        # 29-03-PLAN.md Task 1 (CFG-83): the raw `?limit=` value, mirroring
        # app.py's own ctx key exactly (None when the caller does not care).
        "flights_limit": flights_limit,
    }


def _detail_row_block(rendered, index):
    """The inner markup of the sibling detail `<tr>` for row `index`, or
    None (22-09-PLAN.md Task 2). `_row_block()` can only find the
    SUMMARY row (it keys on `data-filter-group`, which the detail row
    does not carry), and this plan moves the panel-picture control into
    the detail row — so several trigger checks need this locator rather
    than that one.
    """
    match = re.search(
        r'<tr class="flight-detail-row" id="flight-detail-%d"[^>]*>(.*?)</tr>' % index,
        rendered, re.S)
    return match.group(1) if match else None


def _table_markup(rendered):
    """The `<table>...</table>` slice of a rendered Flights page, or
    None (22-09-PLAN.md Task 1). Several X5 assertions are about the
    TABLE specifically and would false-positive against the mobile card
    list rendered beside it — the cards' own `<summary>More details</
    summary>` disclosure, for instance, legitimately carries the word
    "More" and is not a per-row text button.
    """
    match = re.search(r"<table[^>]*>.*?</table>", rendered, re.S)
    return match.group(0) if match else None


# --- HTTP harness (Section 3 only) ----------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(url, method="GET", data=None, cookie=None, timeout=10):
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
    """Structurally identical to companion/test_companion_app.py's own
    Harness class - owns the companion/app.py subprocess lifecycle.
    """

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-view-pages-e2e-")
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

    # ======================================================================
    # Section 1: companion/pages/history_page.py
    # ======================================================================

    def _empty_db_good_news_no_table():
        tmp = _mkstate("h-empty")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if history_page._NO_FLIGHTS_HEADING not in rendered:
                return False, "expected the flight-history empty-state heading"
            if "<table" in rendered:
                return False, "did not expect a <table with zero events"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an empty database renders the flight-history empty-state copy and no <table",
        _empty_db_good_news_no_table)

    def _three_events_newest_first():
        tmp = _mkstate("h-three")
        try:
            events = [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "bbb222", "callsign": "FLT2"},
                {"ts": "2026-08-27T10:02:00+00:00", "hex": "ccc333", "callsign": "FLT3"},
            ]
            _seed_runway_events(tmp, events)
            rendered = history_page.render(_history_ctx(tmp))
            # 21-03-PLAN.md Task 2 (D-15): each summary row now carries a
            # sibling .flight-detail-row <tr> - 1 header + 3 summary + 3
            # detail = 7, not 1 header + 3 summary = 4.
            # 22-09-PLAN.md Task 2 (X5): +1 day-separator row — all three
            # fixture events fall on the SAME Europe/Paris day, so
            # exactly one separator opens the single group: 7 + 1 = 8.
            if rendered.count("<tr") != 8:
                return False, (
                    "expected exactly 1 day separator + 3 summary rows + 3 detail rows + 1 "
                    "header row, got %d <tr" % rendered.count("<tr"))
            if rendered.count('<tr class="flight-day-row">') != 1:
                return False, (
                    "expected exactly one day-separator row for three same-day events, got %d"
                    % rendered.count('<tr class="flight-day-row">'))
            idx3 = rendered.find("FLT3")
            idx2 = rendered.find("FLT2")
            idx1 = rendered.find("FLT1")
            if not (idx3 < idx2 < idx1):
                return False, "expected newest-first ordering (FLT3, FLT2, FLT1)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "three seeded runway events render one row each, newest first",
        _three_events_newest_first)

    def _known_aircraft_type_friendly_label():
        tmp = _mkstate("h-known-type")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d1", "aircraft_type": "b738"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_label = panel_render._TYPE_DISPLAY_LABELS["B738"]
            if expected_label not in rendered:
                return False, "expected the friendly label %r for aircraft_type=b738" % expected_label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a known aircraft-type designator renders its friendly label (case-insensitive)",
        _known_aircraft_type_friendly_label)

    def _unknown_aircraft_type_raw_designator():
        tmp = _mkstate("h-unknown-type")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d2", "aircraft_type": "ZZZZ"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if "ZZZZ" not in rendered:
                return False, "expected the raw designator ZZZZ to appear, not an empty cell"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "an aircraft type absent from the display-label table renders the raw designator, not an empty cell",
        _unknown_aircraft_type_raw_designator)

    def _no_airline_no_route_matches_render_fallback():
        tmp = _mkstate("h-no-route")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d3", "callsign": "NOROUTE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            # Read the expected string from the render module itself, never a
            # literal, so the History page and the panel cannot silently drift.
            if panel_render.ROUTE_FALLBACK_TEXT not in rendered:
                return False, "expected server.plane.render.ROUTE_FALLBACK_TEXT to appear"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a row with no airline and no route renders the same fallback wording server.plane.render.py uses (read from the module)",
        _no_airline_no_route_matches_render_fallback)

    def _mono_columns_present():
        # 06.6.1-02: the merged Callsign+Hex cell moved its monospace
        # treatment off a td[class="mono"] attribute and onto the
        # cell-primary/cell-secondary span classes (both mono in
        # style.css) - a plain "mono" attribute on the merged <td> would
        # fight the 12px secondary size, per _merged_cell()'s docstring.
        # Timestamp is the one remaining td[class="mono"] cell; callsign
        # and hex are asserted via the merged-cell span classes instead.
        tmp = _mkstate("h-mono")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "abc123", "callsign": "MONO1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count('class="mono"') < 1:
                return False, "expected the timestamp cell to carry the monospace CSS class"
            if ('class="%s"' % history_page.CELL_PRIMARY_CLASS) not in rendered:
                return False, "expected the merged-cell primary span to carry its mono CSS class"
            if ('class="%s"' % history_page.CELL_SECONDARY_CLASS) not in rendered:
                return False, "expected the merged-cell secondary span to carry its mono CSS class"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "timestamp, callsign and hex columns carry monospace CSS classes",
        _mono_columns_present)

    def _hostile_callsign_escaped():
        tmp = _mkstate("h-hostile")
        try:
            hostile = "<script>alert(1)</script>"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d4", "callsign": hostile},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if hostile in rendered:
                return False, "an unescaped callsign reached the rendered output"
            if "&lt;script&gt;" not in rendered:
                return False, "expected the escaped form of the hostile callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a callsign containing angle brackets renders escaped",
        _hostile_callsign_escaped)

    def _unreadable_db_degrades_without_raising():
        base = tempfile.mkdtemp(prefix="skypane-view-pages-blocked-")
        blocked_state_dir = os.path.join(base, "blocked")
        try:
            with open(blocked_state_dir, "w") as fh:
                fh.write("this is a file, not a directory")
            rendered = history_page.render(_history_ctx(blocked_state_dir))
            if history_page._HISTORY_UNAVAILABLE_TEXT not in rendered:
                return False, "expected the health-unavailable copy when the database cannot be opened"
            return True, ""
        finally:
            shutil.rmtree(base, ignore_errors=True)
    check(
        "a state directory that cannot hold a database renders the health-unavailable copy without raising",
        _unreadable_db_degrades_without_raising)

    def _history_page_never_imports_html_module():
        with open(os.path.join(HERE, "pages", "history_page.py")) as fh:
            source = fh.read()
        for line in source.splitlines():
            if line.strip() == "import html":
                return False, "history_page.py must never import the stdlib html module directly"
        return True, ""
    check(
        "companion/pages/history_page.py never imports the stdlib html module directly",
        _history_page_never_imports_html_module)

    def _history_page_never_redefines_type_labels():
        with open(os.path.join(HERE, "pages", "history_page.py")) as fh:
            source = fh.read()
        if re.search(r"_TYPE_DISPLAY_LABELS\s*=", source):
            return False, "history_page.py must import _TYPE_DISPLAY_LABELS from the render module, not redefine it"
        return True, ""
    check(
        "companion/pages/history_page.py never redefines _TYPE_DISPLAY_LABELS locally",
        _history_page_never_redefines_type_labels)

    def _history_page_opens_with_shared_page_header():
        # 06.6.2-04 (D-16): History's top-level heading now goes through
        # layout.page_header() instead of an independent bare <h1>.
        tmp = _mkstate("h-page-header")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if '<h1 class="page-title">Flights</h1>' not in rendered:
                return False, "expected the page_header()-rendered <h1 class=\"page-title\">History</h1>"
            if '<h1 class="text-heading">' in rendered:
                return False, "expected no bare <h1 class=\"text-heading\"> heading"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History opens with the shared layout.page_header() component, not a bare <h1>",
        _history_page_opens_with_shared_page_header)

    def _history_table_wrapped_for_horizontal_scroll_dot_survives():
        # D-03/D-22 regression pin: History's own hand-built table gained
        # the same .data-table-wrap horizontal-scroll wrapper Airlines and
        # Health already had (mirrors test_companion_app.py's
        # _data_table_wrapped_for_horizontal_scroll() check for
        # layout.data_table() itself), and the Corroboration cell's
        # unescaped status_dot() embedding must survive the wrap untouched.
        tmp = _mkstate("h-wrap")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d5", "callsign": "WRAP1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            # A-36/D-19: the wrapper now also carries tabindex/role/
            # aria-label (see the scroller-focusable checks below), so
            # this can no longer be an exact-tag match — the substring
            # keeps checking the same wrapper class is still present.
            if '<div class="data-table-wrap"' not in rendered:
                return False, "expected the flight table to be wrapped in .data-table-wrap"
            # 21-03-PLAN.md Task 1 (D-15): the table now also carries the
            # scoped data-table--flights modifier (the 8px, not 16px,
            # cell-padding rule) - still a substring match, not an
            # exact-tag match, so a future class addition doesn't retrip
            # this check either.
            if 'class="data-table data-table--flights"' not in rendered:
                return False, "expected the .data-table--flights modifier to still be present"
            if "dot--" not in rendered:
                return False, "expected the Corroboration cell's status_dot() dot class to survive the wrap"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's flight table gains the .data-table-wrap horizontal-scroll wrapper Airlines/Health already have, without disturbing the Corroboration status dot",
        _history_table_wrapped_for_horizontal_scroll_dot_survives)

    def _six_columns_named_and_ordered():
        # 21-03-PLAN.md Task 1 (D-15): proves the 6->5-data-column
        # compaction shipped, plus the sixth, visually-hidden "Details"
        # toggle-column header - the five data header labels come from
        # history_page._HEADERS itself (the contract), not a re-typed
        # literal list. Was _six_columns_named_and_ordered() /
        # A-36/D-19's own 7->6 pin before this task's drop.
        tmp = _mkstate("h-6col")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d6", "callsign": "SEVEN1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            th_count = len(re.findall(r"<th>", rendered))
            if th_count != 6:
                return False, "expected exactly 6 <th> cells (5 data + 1 toggle), got %d" % th_count
            positions = []
            for header in history_page._HEADERS:
                idx = rendered.find("<th>%s</th>" % header)
                if idx == -1:
                    return False, "expected header %r to appear as a <th>" % header
                positions.append(idx)
            details_th = '<th><span class="visually-hidden">Details</span></th>'
            details_idx = rendered.find(details_th)
            if details_idx == -1:
                return False, "expected the sixth <th> to be the visually-hidden Details toggle header"
            positions.append(details_idx)
            if positions != sorted(positions):
                return False, "expected the 6 headers (5 data + Details) in left-to-right order"
            if "<th>Hex</th>" in rendered or "<th>Airline</th>" in rendered:
                return False, "did not expect standalone Hex/Airline header cells after the merge"
            if "<th>Runway</th>" in rendered:
                return False, "did not expect a standalone Runway header cell after A-36/D-19's drop"
            if "<th>Type</th>" in rendered or "<th>Callsign</th>" in rendered or "<th>Timestamp</th>" in rendered:
                return False, "did not expect the retired Type/Callsign/Timestamp header cells"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History renders exactly the 5 data headers in history_page._HEADERS plus a sixth, "
        "visually-hidden 'Details' toggle-column header, all in order, with no standalone "
        "Hex/Airline/Runway/Type/Callsign/Timestamp column (21-03-PLAN.md Task 1, D-15)",
        _six_columns_named_and_ordered)

    def _runway_survives_in_row_title_and_mobile_details():
        # A-36/D-19: the dropped Runway column's value must survive
        # somewhere - the desktop <tr>'s title attribute, and the
        # mobile card's existing <dt>Runway</dt> disclosure row (which
        # this task deliberately leaves untouched).
        tmp = _mkstate("h-runway-title")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "rwt01",
                    "callsign": "RWTITLE", "tracked_runway": "3",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            runway_label = device_config.runway_label("3")
            # A plain regex, not the shared _row_block() helper (defined
            # later in this function's own source order — a nested def
            # is only bound once execution reaches it, and this check
            # runs earlier): its capture starts AFTER the opening tag's
            # own ">", so it cannot see an attribute on the <tr> itself
            # (only its inner content) - the title lives on the tag, so
            # match the whole opening tag directly instead.
            tr_tag_match = re.search(
                r'<tr[^>]*data-filter-group="0"[^>]*>', rendered)
            li_match = re.search(
                r'<li[^>]*data-filter-group="0"[^>]*>(.*?)</li>', rendered, re.S)
            if tr_tag_match is None or li_match is None:
                return False, "could not locate row block for data-filter-group=0"
            tr_tag = tr_tag_match.group(0)
            li_block = li_match.group(1)
            if ('title="%s"' % layout.escape_html(runway_label)) not in tr_tag:
                return False, "expected the desktop <tr> to carry the runway in its title attribute"
            if "<dt>Runway</dt><dd>%s</dd>" % layout.escape_html(runway_label) not in li_block:
                return False, "expected the mobile card's More details to still show Runway"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the runway value the dropped desktop Runway column used to show survives in the "
        "<tr title=\"...\"> attribute and, unchanged, in the mobile card's More details (A-36/D-19)",
        _runway_survives_in_row_title_and_mobile_details)

    def _scroller_focusable_and_named():
        # A-36/D-19: a keyboard user must be able to Tab to the
        # .data-table-wrap scroller and arrow-scroll it - tabindex="0"
        # plus a non-empty accessible name (aria-label).
        tmp = _mkstate("h-scroller")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "scr01", "callsign": "SCROLL1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            wrap_match = re.search(r'<div class="data-table-wrap"([^>]*)>', rendered)
            if wrap_match is None:
                return False, "expected a .data-table-wrap opening tag"
            attrs = wrap_match.group(1)
            if 'tabindex="0"' not in attrs:
                return False, "expected the scroller to carry tabindex=\"0\""
            if 'role="region"' not in attrs:
                return False, "expected the scroller to carry role=\"region\""
            aria_match = re.search(r'aria-label="([^"]*)"', attrs)
            if aria_match is None or not aria_match.group(1):
                return False, "expected the scroller to carry a non-empty aria-label"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the .data-table-wrap scroller is focusable (tabindex=\"0\") and carries a non-empty "
        "aria-label naming what it scrolls (A-36/D-19)",
        _scroller_focusable_and_named)

    def _desktop_when_cell_clock_primary_relative_age_secondary():
        # 21-03-PLAN.md Task 1 (D-15): the desktop When cell now REINTRODUCES
        # a relative-age line, deliberately - but as a second, STACKED
        # cell-secondary line (never an inline suffix, Pitfall 4), and the
        # full ISO string is no longer carried in a title attribute on
        # this cell at all (it moves into the Task 2 detail row's own
        # "Full timestamp" dt/dd pair instead).
        tmp = _mkstate("h-clock-only")
        try:
            raw_ts = "2026-08-27T10:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": raw_ts, "hex": "clk01", "callsign": "CLOCK1"},
            ])
            now = "2026-08-27T10:05:00+00:00"
            rendered = history_page.render(_history_ctx(tmp, now=now))
            # Inlined rather than the shared _row_block() helper, which
            # is defined later in this function's source order.
            tr_match = re.search(
                r'<tr[^>]*data-filter-group="0"[^>]*>(.*?)</tr>', rendered, re.S)
            if tr_match is None:
                return False, "could not locate row block for data-filter-group=0"
            tr_block = tr_match.group(1)
            if "title=\"%s\"" % layout.escape_html(raw_ts) in tr_block:
                return False, "did not expect the full ISO timestamp in a title attribute any more"
            if "5m ago" not in tr_block:
                return False, "expected the When cell's relative-age secondary line ('5m ago')"
            first_td_match = re.search(r"<td>(.*?)</td>", tr_block, re.S)
            if first_td_match is None:
                return False, "expected a first <td> (the When cell)"
            when_cell = first_td_match.group(1)
            if '<span class="cell-primary">12:00</span>' not in when_cell:
                return False, "expected the When cell's primary slot to carry the local clock text"
            if '<span class="cell-secondary">5m ago</span>' not in when_cell:
                return False, "expected the When cell's secondary slot to carry the relative age"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop When cell shows a local clock primary line plus a STACKED relative-age "
        "secondary line, with no title attribute carrying the full ISO string any more (21-03-"
        "PLAN.md Task 1, D-15)",
        _desktop_when_cell_clock_primary_relative_age_secondary)

    def _merged_flight_cell_carries_callsign_airline_and_type():
        # 21-03-PLAN.md Task 1 (D-15): the Flight column's merge changed
        # shape - callsign (primary) plus "{airline} · {aircraft type}"
        # (secondary), and the hex value is no longer shown anywhere in
        # the desktop table's visible text (it moves into the Task 2
        # detail row instead, still to come in this same plan).
        tmp = _mkstate("h-merge-data")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "39d301",
                    "callsign": "AFR123", "aircraft_type": "A320",
                    "airline": "AFR",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_type_label = panel_render._TYPE_DISPLAY_LABELS.get("A320", "A320")
            expected_airline_label = panel_render.display_airline_name("AFR")
            for value in ("AFR123", expected_type_label, expected_airline_label):
                if value not in rendered:
                    return False, "expected merged value %r to still appear somewhere" % value
            # Scope the same-<td> check to the desktop table's <tbody> -
            # the mobile card representation (06.6.3-05) also renders
            # "AFR123" earlier in the document (the primary line's
            # <span>, outside any <td>), so a whole-document .find()
            # would locate that occurrence instead of the table's.
            tbody_match = re.search(r"<tbody>(.*)</tbody>", rendered, re.S)
            if not tbody_match:
                return False, "expected a <tbody> element in the rendered table"
            tbody = tbody_match.group(1)
            idx = tbody.find("AFR123")
            td_start = tbody.rfind("<td>", 0, idx)
            td_end = tbody.find("</td>", idx)
            if idx == -1 or td_start == -1 or td_end == -1:
                return False, "could not locate the callsign's enclosing <td>"
            cell = tbody[td_start:td_end]
            if expected_airline_label not in cell or expected_type_label not in cell:
                return False, "expected the airline/aircraft-type secondary line inside the same <td> as the callsign"
            if "39d301" in cell:
                return False, "did not expect the hex value visible inside the Flight cell"
            # The hex still lives in the row's own data-filter-text
            # attribute (list-filter.js's match key, unchanged) - only
            # the VISIBLE Flight <td> content is asserted hex-free above.
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the Flight cell's callsign and its airline/aircraft-type secondary line both appear "
        "inside the same <td>, and the hex value is not visible in the desktop table (21-03-"
        "PLAN.md Task 1, D-15)",
        _merged_flight_cell_carries_callsign_airline_and_type)

    def _merged_cells_stay_one_line():
        # Row-height contract (Variant A guard, data-density.md's "What to
        # Avoid"): the merged cells must stay on one line - Variant A
        # ("Stacked cells") was rejected specifically because a taller row
        # works against fast scanning. A future two-line "improvement"
        # must fail this check, not read as progress. Scoped to the
        # SUMMARY row only (21-03-PLAN.md Task 2, D-15): the sibling
        # .flight-detail-row legitimately carries a <dl>/<div> grid -
        # that is a different <tr>, not the summary row's own <td>s, and
        # this check must not conflate the two.
        tmp = _mkstate("h-oneline")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d7", "callsign": "LINE1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            summary_tr_match = re.search(
                r'<tr class="row"[^>]*>(.*?)</tr>', rendered, re.S)
            if not summary_tr_match:
                return False, "expected a summary <tr> in the rendered table"
            summary_tr = summary_tr_match.group(1)
            if "<br" in summary_tr:
                return False, "did not expect a <br> inside the summary row (one-line cell contract)"
            if "<div" in summary_tr or "<p " in summary_tr:
                return False, "did not expect a block-level element inside the summary row's <td>s (one-line cell contract)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the merged Callsign/Hex and Type/Airline cells stay on one line - no <br>, no block-level child",
        _merged_cells_stay_one_line)

    def _merged_cell_hostile_values_escaped():
        tmp = _mkstate("h-merge-hostile")
        try:
            hostile_callsign = '<b>AFR"1</b>'
            hostile_hex = '<i>39"d</i>'
            hostile_type = '<u>A32"0</u>'
            hostile_airline = '<s>AFR"L</s>'
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": hostile_hex,
                    "callsign": hostile_callsign, "aircraft_type": hostile_type,
                    "airline": hostile_airline,
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for raw in (hostile_callsign, hostile_hex, hostile_type, hostile_airline):
                if raw in rendered:
                    return False, "an unescaped merged-cell value reached the rendered output: %r" % raw
            if "&lt;" not in rendered:
                return False, "expected at least one escaped '<' from the hostile merged-cell fixtures"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "hostile values in both merged cells (Callsign/Hex, Type/Airline) render escaped",
        _merged_cell_hostile_values_escaped)

    def _merged_cell_classes_agree_with_stylesheet():
        # Cross-file drift guard (same pattern 06.5-02 established for the
        # Python/CSS/JS trio): if history_page.py's class constants
        # (cell-primary, cell-secondary, cell-inline-sep) and style.css's
        # selectors ever diverge, the merged cells silently render as
        # unstyled plain text instead of failing loudly. Read by symbol
        # below (history_page.CELL_*_CLASS), never re-typed as literals.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        for name in (
            history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
            history_page.CELL_SEPARATOR_CLASS,
        ):
            if name not in css:
                return False, "class %r is emitted by history_page but not styled in style.css" % name
        tmp = _mkstate("h-class-agree")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "d8", "callsign": "CLS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for name in (
                history_page.CELL_PRIMARY_CLASS, history_page.CELL_SECONDARY_CLASS,
                history_page.CELL_SEPARATOR_CLASS,
            ):
                if ('class="%s"' % name) not in rendered:
                    return False, "expected class %r to appear in the rendered History page" % name
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "history_page's CELL_PRIMARY_CLASS/CELL_SECONDARY_CLASS/CELL_SEPARATOR_CLASS all appear in style.css and in the rendered page",
        _merged_cell_classes_agree_with_stylesheet)

    def _timestamp_column_absolute_and_relative():
        # D-09 (06.6.3-05): History's Timestamp column/mobile primary
        # line now read through the shared
        # companion.layout.concise_timestamp_html() helper instead of
        # the old bare "ISO (Nm ago)" text - reads the expected markup
        # from the layout module itself, never a hand-typed literal, so
        # the two cannot silently diverge.
        tmp = _mkstate("h-ts-relative")
        try:
            seeded_ts = "2026-08-28T13:58:02+00:00"
            three_min_later = "2026-08-28T14:01:02+00:00"
            _seed_runway_events(tmp, [
                {"ts": seeded_ts, "hex": "d9", "callsign": "TS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp, now=three_min_later))
            expected = layout.concise_timestamp_html(seeded_ts, three_min_later)
            if expected not in rendered:
                return False, "expected %r in the rendered History page" % expected

            # A one-argument format_event_row() call degrades to the raw
            # stored timestamp, unchanged — no hypothetical existing
            # caller that hasn't been updated to pass `now` breaks.
            one_arg = history_page.format_event_row({"ts": seeded_ts})
            if one_arg["ts"] != seeded_ts:
                return False, (
                    "expected a one-argument format_event_row() call to "
                    "return the raw timestamp unchanged, got %r" % one_arg["ts"])

            # A row with no stored timestamp still produces an empty
            # Timestamp cell, not the shared helper's "no reading yet"
            # default.
            no_ts = history_page.format_event_row({}, three_min_later)
            if no_ts["ts"] != "":
                return False, (
                    "expected a missing timestamp to render an empty "
                    "cell, got %r" % no_ts["ts"])

            # render(ctx) with no "now" key still renders without raising
            # and still shows a relative suffix (falls back to
            # history_db.utc_now_iso()).
            rendered_no_now = history_page.render({"state_dir": tmp})
            # 23-03-PLAN.md Task 1 (D14/CFG-34): retargeted in place, not
            # weakened — the parenthesised relative age is now a <time
            # data-relative> element, so the bare " ago)" substring this
            # pinned before no longer exists (the "</time>" closes
            # between them). The replacement asserts MORE: the
            # parentheses stay outside the element and the age between
            # them is the element's own text.
            if not re.search(
                    r'\(<time datetime="[^"]*" data-relative>[^<]* ago</time>\)',
                    rendered_no_now):
                return False, (
                    "expected a relative-age suffix even when ctx carries "
                    "no 'now' key (render() must fall back to "
                    "history_db.utc_now_iso())")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Timestamp column/mobile primary line read through layout.concise_timestamp_html(), format_event_row() degrades gracefully with one argument or a missing timestamp, and render() falls back when ctx carries no 'now' key",
        _timestamp_column_absolute_and_relative)

    def _history_timestamps_carry_a_relative_time_element():
        # 23-03-PLAN.md Task 1 (D14/CFG-34): concise_timestamp_html()'s
        # relative half is now a <time data-relative> element, so every
        # surface that reads THROUGH that function inherits the
        # convention without its own page module changing at all.
        # History is the widest such surface, and its cells go through
        # data_table()'s raw_columns — so this check is also the proof
        # that the element survives that path as MARKUP rather than
        # arriving double-escaped as literal text on the page.
        tmp = _mkstate("h-ts-relative-element")
        try:
            seeded_ts = "2026-08-28T13:58:02+00:00"
            three_min_later = "2026-08-28T14:01:02+00:00"
            _seed_runway_events(tmp, [
                {"ts": seeded_ts, "hex": "d9", "callsign": "TS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp, now=three_min_later))
            # 23-08-PLAN.md Task 1: RETARGETED IN PLACE, no count change.
            # Flights joined the refresh loop, so its header now carries
            # layout.freshness_line_html()'s own <time data-relative>
            # clock — and a bare re.search() over the whole page found
            # THAT element first and measured the page's render instant
            # instead of the row's age. The subject of this check has
            # always been the Timestamp CELL and the raw_columns path it
            # travels, so it measures inside the table now. The header's
            # element is asserted present and distinct in the same
            # breath, because "measure the table" is only honest while
            # something proves the other element is really there to have
            # been confused with.
            if "data-refresh-clock" not in rendered:
                return False, (
                    "expected the page header's own freshness clock to be present — this check "
                    "narrowed its search to the table precisely because that element exists, "
                    "and with it gone the narrowing would be measuring nothing in particular")
            cards = re.search(r'<ul class="history-cards">.*?</ul>', rendered, re.S)
            if cards is None:
                return False, "expected a rendered History card list"
            body = cards.group(0)
            if "data-refresh-clock" in body:
                return False, (
                    "did not expect the header's freshness clock inside the row list — the two "
                    "elements must stay distinct or this check is back to measuring whichever "
                    "the regex reached first")
            match = re.search(
                r'<time datetime="([^"]*)" data-relative>([^<]*)</time>', body)
            if match is None:
                return False, (
                    "expected at least one <time datetime=... data-relative> element in the "
                    "rendered History row list — this is the surface that reaches the page "
                    "through concise_timestamp_html()")
            if "&lt;time" in rendered:
                return False, (
                    "expected the element to reach the page as markup — a double-escaped "
                    "'&lt;time' means a raw-markup producer was escaped again by its caller")
            if match.group(2) != layout.relative_age_text(
                    layout.age_seconds(seeded_ts, three_min_later)):
                return False, (
                    "expected the element's text to be the unchanged relative age, got %r"
                    % (match.group(2),))
            if layout.age_seconds(match.group(1), three_min_later) != 180:
                return False, (
                    "expected the element's own machine-readable instant to name the seeded "
                    "row's moment, got %r" % (match.group(1),))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's Timestamp cells carry layout.concise_timestamp_html()'s new "
        "<time data-relative> element through data_table()'s raw_columns — as real markup, "
        "never double-escaped — with its text and its instant both intact (23-03, D14/CFG-34)",
        _history_timestamps_carry_a_relative_time_element)

    def _corroboration_copy_agrees_with_health_page():
        # D-03, restated by quick task 260902-w4t (UIR-04): History's
        # "None" (single-source) label was shortened to "Single-source"
        # to fix an overlong Corroboration column, so the two pages'
        # visible labels are now DELIBERATELY allowed to diverge for
        # that one key - health_page._CORROBORATION_ROWS still carries
        # the long form as ITS OWN visible label by design. This guard
        # is restated, not weakened, to keep asserting everything that
        # must still agree: statuses agree key-by-key for True/False
        # (22-12-PLAN.md Task 1 removed "None" from that loop and pinned
        # each page's own value by name instead — see the loop's own
        # comment); visible labels are still identical for True/False (the
        # two keys this task did not touch); and for None, History's
        # visible label must be the short form AND
        # history_page._CORROBORATION_TITLES["None"] (the tooltip) must
        # equal Health's full label exactly, so a future edit to
        # Health's copy still fails this check loudly instead of
        # silently going stale in History's tooltip.
        health_rows = {
            stored: (status, label)
            for stored, label, status, _explanation in health_page._CORROBORATION_ROWS
        }
        history_labels = history_page._CORROBORATION_LABELS
        history_titles = history_page._CORROBORATION_TITLES

        if set(health_rows) != {"True", "None", "False"}:
            return False, "expected health_page._CORROBORATION_ROWS to cover exactly True/None/False"
        if set(history_labels) != {"True", "None", "False"}:
            return False, "expected history_page._CORROBORATION_LABELS to cover exactly True/None/False"

        # Statuses must agree key-by-key for True and False.
        #
        # RETARGETED IN PLACE, STRICTLY NARROWER (22-12-PLAN.md Task 1,
        # X8 / 22-UI-SPEC.md §5 contract 4). This loop used to cover all
        # three keys. Health's "None" row moved from the ok token to the
        # neutral `.dot--off` one — it used to render in exactly the same
        # green as "Both agree", so a state that only means "there was
        # nothing to compare against" was painted as good news — while
        # History's desktop table deliberately keeps "ok": 21-UI-SPEC/
        # D-15 scoped the dot-only treatment to that table alone, and
        # 22-UI-SPEC.md §5 contract 4 states in terms that Health's own
        # table is unaffected. The two pages therefore now diverge on
        # this key's STATUS exactly as they already diverge on its LABEL,
        # both by design.
        #
        # Rather than dropping the key from the loop (which would stop
        # asserting anything about it), each side is pinned to its own
        # exact expected value below — strictly stronger than the
        # equality this replaces, because a drift on EITHER side now
        # fails, where equality would have passed if both drifted
        # together.
        for key in ("True", "False"):
            if history_labels[key][0] != health_rows[key][0]:
                return False, (
                    "corroboration status drifted for %r: history_page has %r, "
                    "health_page has %r" % (key, history_labels[key][0], health_rows[key][0]))

        # Visible labels must still be identical for True/False.
        for key in ("True", "False"):
            if history_labels[key][1] != health_rows[key][1]:
                return False, (
                    "corroboration label drifted for %r: history_page has %r, "
                    "health_page has %r" % (key, history_labels[key][1], health_rows[key][1]))

        # None: History's visible label is the documented short form...
        if history_labels["None"][1] != "Single-source":
            return False, (
                "expected history_page's 'None' visible label to be the short form "
                "'Single-source', got %r" % (history_labels["None"][1],))
        # ...and its tooltip carries Health's full label exactly, so a
        # future edit to Health's copy fails this check, not silently.
        if history_titles.get("None") != health_rows["None"][1]:
            return False, (
                "expected history_page._CORROBORATION_TITLES['None'] to equal "
                "health_page's 'None' visible label %r, got %r"
                % (health_rows["None"][1], history_titles.get("None")))

        # D-03/D-15: the single-source, uncorroborated "None" state is a
        # genuinely unknown state, NEVER a failure. That invariant is
        # unchanged and is still asserted for both pages; what the two
        # pages express it with now differs, deliberately, and each side
        # is pinned by name (22-12-PLAN.md Task 1, X8).
        if history_labels["None"][0] != "ok":
            return False, "expected history_page's 'None' (single-source) status to be 'ok', not a failure"
        if health_rows["None"][0] != "off":
            return False, (
                "expected health_page's 'None' (single-source) status to be the neutral 'off' "
                "token (X8, 22-UI-SPEC.md §5 contract 4 — never the same green as 'Both agree'), "
                "got %r" % (health_rows["None"][0],))
        for page_name, status in (
                ("history_page", history_labels["None"][0]),
                ("health_page", health_rows["None"][0])):
            if status in ("warn", "error"):
                return False, (
                    "%s's 'None' (single-source) status must never read as a failure, got %r"
                    % (page_name, status))
        # X8's own safety clause: colour is not the only signal. The two
        # states a reader must be able to tell apart carry different
        # visible label text on Health, so the page is readable with
        # colour vision entirely absent.
        if health_rows["None"][1] == health_rows["True"][1]:
            return False, (
                "expected Health's 'None' and 'True' rows to carry DIFFERENT visible labels — "
                "colour is never the only signal (22-UI-SPEC.md §5 contract 4)")

        return True, ""
    check(
        "history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS on "
        "status key-by-key and on visible label for True/False; History's shortened 'None' label "
        "is the documented short form and its _CORROBORATION_TITLES tooltip equals Health's own "
        "full label exactly; the single-source 'None' state is pinned by name on each side "
        "(History 'ok', Health the neutral 'off'), is never a failure in either table, and carries "
        "a visible label distinct from 'Both agree' (quick task 260902-w4t UIR-04, retargeted by "
        "22-12-PLAN.md Task 1's X8)",
        _corroboration_copy_agrees_with_health_page)

    def _status_dot_title_backward_compatible_and_escaped():
        # quick task 260902-w4t (UIR-04, 3a): status_dot()'s new third
        # `title` parameter must be fully backward-compatible - every
        # pre-existing 2-arg call site's output stays character-for-
        # character identical - and, when supplied, must escape a
        # hostile value the same way `label` already is.
        two_arg = layout.status_dot("ok", "All good")
        if "title=" in two_arg:
            return False, "expected the 2-arg call to emit no title attribute at all"
        three_arg_equivalent = layout.status_dot("ok", "All good", None)
        if three_arg_equivalent != two_arg:
            return False, "expected an explicit title=None to produce byte-identical markup to the 2-arg call"
        titled = layout.status_dot("ok", "All good", "Long form")
        if 'title="Long form"' not in titled:
            return False, "expected a truthy title to appear as an escaped title attribute"
        hostile = layout.status_dot("ok", "All good", "<script>evil()</script>")
        if "<script>" in hostile:
            return False, "expected a hostile title value to be escaped, not rendered raw"
        if "&lt;script&gt;" not in hostile:
            return False, "expected the escaped form of the hostile title value"
        return True, ""
    check(
        "layout.status_dot()'s 2-arg output is unchanged, an explicit title=None is byte-identical "
        "to omitting it, and a truthy title renders as an escaped title attribute "
        "(quick task 260902-w4t, UIR-04)",
        _status_dot_title_backward_compatible_and_escaped)

    def _status_dot_visually_hide_label_defaults_false_byte_identical():
        # 21-03-PLAN.md Task 1 (D-15): status_dot()'s new fourth keyword,
        # visually_hide_label, must be fully backward-compatible - every
        # pre-existing call site (which never passes it) gets a
        # byte-identical return value, matching stat_tile()'s own
        # keyword-with-default contract this parameter copies.
        without_keyword = layout.status_dot("ok", "All good", "A tooltip")
        explicit_false = layout.status_dot("ok", "All good", "A tooltip", visually_hide_label=False)
        if explicit_false != without_keyword:
            return False, "expected visually_hide_label=False to be byte-identical to omitting it"
        if 'class="dot-label"' not in without_keyword:
            return False, "expected the pre-existing call shape to keep its plain dot-label class"
        hidden = layout.status_dot("ok", "All good", "A tooltip", visually_hide_label=True)
        if 'class="dot-label visually-hidden"' not in hidden:
            return False, "expected visually_hide_label=True to add the visually-hidden class"
        if 'title="A tooltip"' not in hidden:
            return False, "expected the title attribute to survive visually_hide_label=True unchanged"
        if ">All good<" not in hidden:
            return False, "expected the escaped label text to survive visually_hide_label=True unchanged"
        return True, ""
    check(
        "layout.status_dot()'s visually_hide_label keyword defaults to False with a byte-"
        "identical return value, and True adds the visually-hidden class to the label span "
        "while leaving its text/title unchanged (21-03-PLAN.md Task 1, D-15)",
        _status_dot_visually_hide_label_defaults_false_byte_identical)

    # Relocated ahead of its original first use (was defined further down,
    # in Section 1c) so this section's own new UIR-04 check below — the
    # first check in file order that needs it — can call it: Python
    # resolves a nested function's free variables against the enclosing
    # scope at CALL time, not definition time, so a check registered (and
    # immediately invoked by check()) before this def executes would hit
    # "cannot access free variable '_row_block'" even though the name
    # exists later in the same function body. Every later call site is
    # unaffected — this is the same function, only earlier.
    def _row_block(rendered, tag, group_index):
        pattern = r"<%s[^>]*data-filter-group=\"%d\"[^>]*>(.*?)</%s>" % (
            tag, group_index, tag)
        match = re.search(pattern, rendered, re.S)
        return match.group(1) if match else None

    def _corroboration_none_row_shows_short_label_with_tooltip():
        # quick task 260902-w4t (UIR-04): a "None" (single-source) row's
        # Corroboration cell must render the short visible label in BOTH
        # the desktop <td> and the mobile <dd>, with the long form
        # reachable only via a title attribute, in both renderings.
        tmp = _mkstate("h-corrob-none")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cn01", "callsign": "CORNONE",
                 "corroborated": None},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a None-corroboration row"
            long_form = history_page._CORROBORATION_TITLES["None"]
            for label, block in (("desktop", tr_block), ("mobile", li_block)):
                if ">Single-source<" not in block:
                    return False, "expected the short 'Single-source' label visible in the %s row" % label
                if 'title="%s"' % long_form not in block:
                    return False, "expected the long form in a title attribute in the %s row" % label
                # The long form's parenthetical must not appear as separate
                # VISIBLE text - only inside the title attribute value.
                visible_text = re.sub(r'\stitle="[^"]*"', "", block)
                if "(uncorroborated)" in visible_text:
                    return False, "did not expect the parenthetical to appear as visible text in the %s row" % label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a 'None' (single-source) row's Corroboration cell shows the short visible label with the "
        "long form only in a title attribute, in both the desktop and mobile renderings "
        "(quick task 260902-w4t, UIR-04)",
        _corroboration_none_row_shows_short_label_with_tooltip)

    def _desktop_corroboration_cell_dot_only_no_visible_word():
        # 21-03-PLAN.md Task 1 (D-15): the desktop Corroboration cell's
        # visible label is gone (status_dot(visually_hide_label=True)) -
        # the dot alone remains visible; the word is still present for
        # a screen reader, carried by the visually-hidden class, never
        # deleted outright. The phone card's own Corroboration <dd> is
        # unaffected (D-16) and may still show the word visibly.
        tmp = _mkstate("h-corrob-dot-only")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cdo01", "callsign": "CDOTONLY",
                 "corroborated": "True"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for the corroboration-dot-only row"
            if 'class="dot-label visually-hidden"' not in tr_block:
                return False, "expected the desktop Corroboration cell's label to carry visually-hidden"
            # The word itself is still IN the markup (a screen reader
            # must still announce it) - only its CSS class changes to
            # visually-hidden. Assert the accessible name survives,
            # never that the text vanished from the document.
            if ">Both agree<" not in tr_block:
                return False, "expected the corroboration word to survive (in the accessibility tree) inside the desktop <tr>"
            if 'class="dot-label visually-hidden"' in li_block:
                return False, "did not expect the mobile card's own Corroboration <dd> to be hidden too"
            if ">Both agree<" not in li_block:
                return False, "expected the mobile card's Corroboration <dd> to still show the word (D-16)"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop Corroboration cell renders the dot only, with the visible word hidden via "
        "visually-hidden (not deleted); the mobile card's own Corroboration <dd> still shows the "
        "word (21-03-PLAN.md Task 1, D-15/D-16)",
        _desktop_corroboration_cell_dot_only_no_visible_word)

    def _when_and_flight_cells_each_carry_one_primary_one_secondary():
        # 21-03-PLAN.md Task 1 (D-15): both new two-line cells are built
        # through the shared _merged_cell() pattern - exactly one
        # cell-primary and one cell-secondary span each.
        tmp = _mkstate("h-when-flight-merged")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "wf01", "callsign": "WHENFLT",
                 "aircraft_type": "A320", "airline": "AFR"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            if tr_block is None:
                return False, "could not locate row block for the When/Flight merged-cell row"
            td_matches = re.findall(r"<td>(.*?)</td>", tr_block, re.S)
            if len(td_matches) < 2:
                return False, "expected at least 2 <td> cells (When, Flight)"
            when_cell, flight_cell = td_matches[0], td_matches[1]
            for name, cell in (("When", when_cell), ("Flight", flight_cell)):
                if cell.count('class="cell-primary"') + cell.count('class="cell-primary mono"') != 1:
                    return False, "expected exactly one cell-primary span in the %s cell" % name
                if cell.count("cell-secondary") != 1:
                    return False, "expected exactly one cell-secondary span in the %s cell" % name
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop When and Flight cells each carry exactly one cell-primary span and one "
        "cell-secondary span (21-03-PLAN.md Task 1, D-15)",
        _when_and_flight_cells_each_carry_one_primary_one_secondary)

    def _data_table_wrap_scroll_edge_affordance_css():
        # quick task 260902-w4t (UIR-04, 3d): the CSS-only, pointer-inert
        # scroll-edge affordance must declare both background-attachment
        # values (local for the covers, scroll for the shadows) and must
        # introduce no pointer-events-blocking overlay anywhere in the
        # stylesheet's .data-table-wrap rule.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule_match = re.search(r"\.data-table-wrap\s*\{([^}]*)\}", css, re.S)
        if rule_match is None:
            return False, "expected a base .data-table-wrap rule in style.css"
        rule_body = rule_match.group(1)
        if "background-attachment" not in rule_body:
            return False, "expected .data-table-wrap to declare background-attachment"
        if "local" not in rule_body or "scroll" not in rule_body:
            return False, "expected .data-table-wrap's background-attachment to declare both local and scroll"
        if "pointer-events" in rule_body:
            return False, "did not expect a pointer-events declaration on .data-table-wrap"
        override_match = re.search(
            r"\.page-section \.data-table-wrap,\s*\n\.battery-trend-section \.data-table-wrap\s*\{([^}]*)\}",
            css, re.S)
        if override_match is None:
            return False, "expected the .page-section/.battery-trend-section .data-table-wrap surface override"
        if "pointer-events" in override_match.group(1):
            return False, "did not expect a pointer-events declaration on the surface override rule"
        return True, ""
    check(
        ".data-table-wrap declares both background-attachment values (local covers, scroll "
        "shadows) and style.css introduces no pointer-events-blocking overlay "
        "(quick task 260902-w4t, UIR-04)",
        _data_table_wrap_scroll_edge_affordance_css)

    def _filter_bar_markers_present_once():
        # D-20: exactly one of each list-filter.js attribute marker,
        # only rendered when there is data to filter (a zero-row page
        # renders no filter bar at all, matching the table/card
        # renderers' own "no chrome with no data" rule).
        tmp = _mkstate("h-filter-bar")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fb01", "callsign": "FB1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for marker in (
                "data-filter-input", "data-filter-count", "data-filter-clear",
                "data-filter-empty",
            ):
                # 20-11-PLAN.md Task 3 (D-06): a negative lookahead excludes
                # data-filter-count's own new sibling attribute, data-
                # filter-count-template — a real second attribute (the
                # server-rendered "%d of %d shown" template list-filter.js
                # now reads), not a second occurrence of this marker.
                count = len(re.findall(r"%s(?!-template)" % re.escape(marker), rendered))
                if count != 1:
                    return False, "expected exactly one %r marker, got %d" % (marker, count)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's filter bar carries exactly one data-filter-input/-count/-clear/-empty marker each",
        _filter_bar_markers_present_once)

    def _filter_input_carries_safari_autofill_suppression_attributes():
        # Quick task 260921-n2n Task 1: the developer photographed Safari
        # offering household contact/phone-number autofill on Flights'
        # search filter on 2026-09-21 — a bare `<input type="search">`
        # with no `name` and no `autocomplete` is exactly the shape
        # Safari's heuristic treats as a contact field. Pin all three
        # suppression attributes on the rendered input so a future edit
        # cannot silently drop one back to the bare, autofill-prone form.
        tmp = _mkstate("h-filter-autofill")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fb01", "callsign": "FB1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for attr in ('autocomplete="off"', 'spellcheck="false"', 'autocapitalize="characters"'):
                if attr not in rendered:
                    return False, (
                        "expected History's search filter input to carry %r — without it, "
                        "iOS Safari offers contact/phone-number autofill on the field "
                        "(the defect the developer photographed on 2026-09-21)" % (attr,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's search filter input carries autocomplete=off/spellcheck=false/"
        "autocapitalize=characters (Safari contact-autofill suppression)",
        _filter_input_carries_safari_autofill_suppression_attributes)

    def _filter_count_template_attribute_english_and_french():
        # 20-11-PLAN.md Task 3 (D-06): companion/static/list-filter.js
        # reads its live "X of Y shown" count text from
        # data-filter-count-template instead of hardcoding the English
        # words "of"/"shown" — this is that attribute's own translated
        # value, under each language in turn, with both "%d" placeholders
        # left unformatted for the script to fill in.
        import companion.prefs as _prefs
        tmp = _mkstate("h-filter-count-template")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fc01", "callsign": "FC1"},
            ])
            rendered_en = history_page.render(_history_ctx(tmp))
            if 'data-filter-count-template="%d of %d shown"' not in rendered_en:
                return False, "expected the English filter-count template under the default language"

            _prefs.set_request_prefs(lang="fr")
            try:
                rendered_fr = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
            if 'data-filter-count-template="%d sur %d affichés"' not in rendered_fr:
                return False, "expected the French filter-count template under lang='fr'"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "History's filter bar carries data-filter-count-template=\"%d of %d shown\" under the "
        "default language and the French \"%d sur %d affichés\" under lang='fr' (D-06)",
        _filter_count_template_attribute_english_and_french)

    def _filter_bar_count_and_clear_wrap_as_one_group():
        # B11 (22-09-PLAN.md Task 3): the markup half of the fix the
        # browser harness measures — the count and the Clear control are
        # siblings inside ONE .filter-bar__meta group, so they are a
        # single flex item that wraps whole or not at all. This is Phase
        # 18's A-18 regressing a SECOND time; two `nowrap` siblings in a
        # wrapping flex container never wrapped as a unit.
        tmp = _mkstate("h-filter-meta")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fm01", "callsign": "FILTMETA"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            group = re.search(
                r'<div class="filter-bar__meta">(.*?)</div>', rendered, re.S)
            if group is None:
                return False, "expected a .filter-bar__meta group in the rendered filter bar"
            if "data-filter-count" not in group.group(1):
                return False, "expected the live count inside the group"
            if "data-filter-clear" not in group.group(1):
                return False, "expected the Clear control inside the group"
            if rendered.count("data-filter-clear") != 1:
                return False, "expected exactly one Clear control on the page"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule = re.search(r"^\.filter-bar__meta\s*\{([^}]*)\}", css, re.S | re.M)
        if rule is None:
            return False, "expected a .filter-bar__meta rule block in style.css"
        for declaration in ("display: flex", "align-items: center",
                            "white-space: nowrap", "margin-left: auto"):
            if declaration not in rule.group(1):
                return False, (
                    "expected the group rule to declare %r so the pair moves together and stays "
                    "at the end of the bar" % declaration)
        if "flight" in rule.group(1) or "history" in rule.group(1):
            return False, "expected the group rule to carry no page-scoped anything"
        # The rule must be adoptable verbatim by Airlines (22-11) and
        # Health (22-12): no page-scoped selector anywhere, and no
        # page-scoped fork of the converged Clear control.
        declarations = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        declarations = re.sub(r",\s*\n\s*", ", ", declarations)
        forks = re.findall(
            r"(flight|airline|health|registry)[^{\n]*\[data-filter-clear\]", declarations)
        if forks:
            return False, (
                "expected no page-scoped fork of the converged [data-filter-clear] rule, found "
                "%r" % (forks,))
        if declarations.count(".filter-bar__meta {") != 1:
            return False, "expected exactly one .filter-bar__meta rule, never a per-page variant"
        return True, ""
    check(
        "History's filter count and Clear control render as siblings inside one "
        ".filter-bar__meta group whose page-agnostic rule declares flex/centre/nowrap/auto-left-"
        "margin, with no page-scoped fork of the converged [data-filter-clear] rule anywhere "
        "(B11, 22-09-PLAN.md Task 3 — a regression of Phase 18's A-18)",
        _filter_bar_count_and_clear_wrap_as_one_group)

    def _clear_control_shared_attribute_contract():
        # 06.6.4-05 (D-08): History's Clear <button> and Airlines' Clear
        # <a> converge on one shared style.css rule keyed by the
        # [data-filter-clear] attribute both pages already emit, not a
        # new shared class - so a future author adding a class to one
        # page and not the other is exactly how the two Clear controls
        # would silently diverge again. Pins all three legs of that
        # contract: History's rendered output still carries the
        # attribute, style.css styles it via the attribute selector, and
        # style.css contains no competing class-keyed Clear-control rule.
        tmp = _mkstate("h-clear-attr")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "ca01", "callsign": "CA1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if "data-filter-clear" not in rendered:
                return False, "expected History's rendered filter bar to carry data-filter-clear"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        # Comments are stripped first: this task's own commit adds prose
        # explaining the attribute-selector choice, and that prose must
        # not trip the check it documents.
        declarations = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        # WR-05 fix: the rule-matching regex below requires the selector
        # and its opening `{` on the same line, so a multi-line,
        # comma-grouped selector (e.g. `a:focus-visible,\nbutton:focus-
        # visible {`) would otherwise have its earlier lines silently
        # dropped from `selector`, undermining this check's own
        # regression guard. Joining each selector-list newline back onto
        # one line first makes the regex robust to that style.css
        # convention.
        declarations = re.sub(r",\s*\n\s*", ", ", declarations)
        if "[data-filter-clear]" not in declarations:
            return False, "expected a [data-filter-clear] rule in style.css"
        for m in re.finditer(r"\n([^{\n]*\{[^}]*\})", declarations):
            rule = m.group(1)
            selector = rule.split("{", 1)[0]
            if "[data-filter-clear]" in selector:
                continue
            if "clear" in selector.lower() and (
                    "background: none" in rule or "text-decoration: underline" in rule):
                return False, (
                    "found a class-keyed Clear-control rule outside "
                    "[data-filter-clear]: %r - the shared attribute "
                    "contract must stay the only Clear-control styling "
                    "site" % selector.strip())
        return True, ""
    check(
        "the Clear control's shared [data-filter-clear] contract holds: History renders the "
        "attribute, style.css styles it by attribute, and no class-keyed rule competes",
        _clear_control_shared_attribute_contract)

    def _filter_text_attribute_on_both_representations():
        # D-20/T-06.6.3-09: the same escaped, lowercased "callsign hex"
        # value drives both the desktop <tr> and the mobile <li> for the
        # same flight, so a filter query matches both representations
        # identically.
        tmp = _mkstate("h-filter-text")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "3944F0", "callsign": "AFR123"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            expected_attr = 'data-filter-text="afr123 3944f0"'
            count = rendered.count(expected_attr)
            if count != 2:
                return False, (
                    "expected %r to appear exactly twice (desktop <tr> + "
                    "mobile <li>), got %d" % (expected_attr, count))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real flight's data-filter-text attribute (lowercased escaped callsign+hex) appears on both the desktop <tr> and the mobile <li>",
        _filter_text_attribute_on_both_representations)

    def _desktop_flight_cell_carries_no_copy_buttons():
        # 21-03-PLAN.md Task 1 (D-15): the retired _callsign_hex_cell()'s
        # 2 copy buttons (callsign, hex) do not move onto the new Flight
        # cell - they move into the Task 2 detail row instead (a later
        # task in this same plan). At this point the desktop Flight <td>
        # carries zero copy buttons.
        tmp = _mkstate("h-copy-desktop")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cd01", "callsign": "CDONE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tbody_match = re.search(r"<tbody>(.*)</tbody>", rendered, re.S)
            if not tbody_match:
                return False, "expected a <tbody> element in the rendered table"
            tbody = tbody_match.group(1)
            idx = tbody.find("CDONE")
            td_start = tbody.rfind("<td>", 0, idx)
            td_end = tbody.find("</td>", idx)
            if idx == -1 or td_start == -1 or td_end == -1:
                return False, "could not locate the callsign's enclosing <td>"
            cell = tbody[td_start:td_end]
            if cell.count("data-copy-value") != 0:
                return False, (
                    "expected zero copy buttons in the desktop Flight cell, got %d"
                    % cell.count("data-copy-value"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the desktop Flight cell contains zero copy buttons (21-03-PLAN.md Task 1, D-15 - they "
        "move into the Task 2 detail row instead)",
        _desktop_flight_cell_carries_no_copy_buttons)

    def _detail_row_pairs_with_summary_row_by_aria_controls_and_id():
        # 21-03-PLAN.md Task 2 (D-15/R-12): one detail <tr> per summary
        # row, matched by aria-controls/id, neither carrying `hidden`
        # nor an inline `style=` (the no-JS floor is a fully visible
        # detail row); the toggle's aria-expanded starts "false".
        tmp = _mkstate("h-detail-row-pairing")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "dr01", "callsign": "DETAIL1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "dr02", "callsign": "DETAIL2"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            detail_row_count = rendered.count('class="flight-detail-row"')
            if detail_row_count != 2:
                return False, "expected exactly 2 detail rows (one per summary row), got %d" % detail_row_count
            for index in (0, 1):
                if ('aria-controls="flight-detail-%d"' % index) not in rendered:
                    return False, "expected row %d's toggle to name flight-detail-%d via aria-controls" % (index, index)
                if ('id="flight-detail-%d"' % index) not in rendered:
                    return False, "expected a detail row with id=flight-detail-%d" % index
            detail_tr_matches = re.findall(
                r'<tr class="flight-detail-row"[^>]*>', rendered)
            if len(detail_tr_matches) != 2:
                return False, "expected exactly 2 <tr class=\"flight-detail-row\"> opening tags"
            for tag in detail_tr_matches:
                if "hidden" in tag:
                    return False, "did not expect a detail row to carry the hidden attribute"
                if "style=" in tag:
                    return False, "did not expect a detail row to carry an inline style attribute"
            if rendered.count('aria-expanded="false"') < 2:
                return False, "expected both row-toggle buttons to start aria-expanded=\"false\""
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "each summary row gets exactly one sibling detail row, matched by aria-controls/id, "
        "with no hidden attribute and no inline style (the no-JS floor), and every row-toggle "
        "starts aria-expanded=\"false\" (21-03-PLAN.md Task 2, D-15/R-12)",
        _detail_row_pairs_with_summary_row_by_aria_controls_and_id)

    # ======================================================================
    # Section 1b-X5: 22-09-PLAN.md Task 1 — the icon-only row toggle.
    # ======================================================================

    def _row_toggle_is_icon_only_and_named_in_both_languages():
        # 22-09-PLAN.md Task 1 (X5): zero visible per-row text buttons.
        # The toggle renders a decorative aria-hidden glyph and NO text,
        # and carries a translated aria-label that swaps with the state
        # AND names the picture reachable inside the detail row.
        import companion.i18n as _i18n
        import companion.prefs as _prefs
        tmp = _mkstate("h-toggle-icon-only")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "tg01", "callsign": "TOGGLE1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "tg02", "callsign": "TOGGLE2"},
            ])
            rendered_en = history_page.render(_history_ctx(tmp))
            _prefs.set_request_prefs(lang="fr")
            try:
                rendered_fr = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")

            for lang, rendered in (("en", rendered_en), ("fr", rendered_fr)):
                table = _table_markup(rendered)
                if table is None:
                    return False, "could not locate the rendered table (%s)" % lang
                # The retired visible labels are gone from the table —
                # both language forms, checked as a rendered STRING, not
                # as a source-level constant.
                for retired in ("More", "Plus", "Less", "Moins"):
                    if (">%s<" % retired) in table:
                        return False, (
                            "expected zero visible %r button labels in the rendered table "
                            "(%s), found one" % (retired, lang))
                toggles = re.findall(r"<button[^>]*data-row-toggle[^>]*>(.*?)</button>",
                                     table, re.S)
                if len(toggles) != 2:
                    return False, (
                        "expected exactly one toggle button per summary row (2), got %d (%s)"
                        % (len(toggles), lang))
                for inner in toggles:
                    if re.sub(r"<[^>]*>", "", inner).strip() != history_page._TOGGLE_GLYPH:
                        return False, (
                            "expected the toggle's only content to be the decorative glyph, "
                            "got %r (%s)" % (inner, lang))
                    if 'aria-hidden="true"' not in inner:
                        return False, "expected the glyph span to be aria-hidden (%s)" % lang

                show = _i18n.t_lang(history_page._TOGGLE_SHOW_LABEL, lang)
                hide = _i18n.t_lang(history_page._TOGGLE_HIDE_LABEL, lang)
                if lang == "fr" and (show == history_page._TOGGLE_SHOW_LABEL
                                     or hide == history_page._TOGGLE_HIDE_LABEL):
                    return False, "expected both toggle labels to have French catalogue entries"
                for needle in (
                        'aria-label="%s"' % layout.escape_html(show),
                        '%s="%s"' % (history_page._TOGGLE_SHOW_LABEL_ATTR,
                                     layout.escape_html(show)),
                        '%s="%s"' % (history_page._TOGGLE_HIDE_LABEL_ATTR,
                                     layout.escape_html(hide)),
                ):
                    if table.count(needle) != 2:
                        return False, (
                            "expected %r exactly once per row (2) in the %s table, found %d"
                            % (needle, lang, table.count(needle)))
                # The name advertises the picture, not only the details
                # (the picture control moves into the detail row in
                # Task 2 — a name saying only "details" would hide it).
                for label in (history_page._TOGGLE_SHOW_LABEL, history_page._TOGGLE_HIDE_LABEL):
                    if "picture" not in label:
                        return False, (
                            "expected the toggle's English accessible name to name the picture "
                            "reachable inside the detail row, got %r" % (label,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Flights table carries zero visible More/Plus/Less/Moins button labels and "
        "exactly one icon-only toggle button per row, each carrying a translated aria-label that "
        "swaps with its state and names the picture reachable inside (22-09-PLAN.md Task 1, X5)",
        _row_toggle_is_icon_only_and_named_in_both_languages)

    def _aria_expanded_sits_only_on_buttons_never_on_a_tr():
        # 22-09-PLAN.md Task 1 (X5, 22-UI-SPEC.md §2): "the toggle stays
        # a real <button>" — a <tr> is not focusable and cannot carry
        # the state. Asserted against the RENDERED table, never a
        # source-level count: history_page.py's own source legitimately
        # contains the string "aria-expanded" more than once across its
        # table and card builders, so a grep of the module cannot gate
        # this.
        tmp = _mkstate("h-aria-expanded-placement")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "ae01", "callsign": "ARIAEXP"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_with_state = re.findall(r"<tr[^>]*aria-expanded", rendered)
            if tr_with_state:
                return False, (
                    "expected zero <tr ... aria-expanded> in the rendered page, found %d"
                    % len(tr_with_state))
            for match in re.finditer(r"<([a-z]+)[^>]*\baria-expanded=", rendered):
                if match.group(1) != "button":
                    return False, (
                        "expected every aria-expanded to sit on a <button>, found one on <%s>"
                        % match.group(1))
            if not re.search(r"<button[^>]*\baria-expanded=", rendered):
                return False, "expected at least one <button ... aria-expanded>"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "in the RENDERED Flights page no <tr> carries aria-expanded and every aria-expanded "
        "occurrence sits on a <button> (22-09-PLAN.md Task 1, X5 — the state never moves onto "
        "the row element)",
        _aria_expanded_sits_only_on_buttons_never_on_a_tr)

    def _row_toggle_css_reuses_the_copy_btn_icon_only_pattern():
        # 22-09-PLAN.md Task 1 (X5): .row-toggle had NO CSS rule at all
        # before this plan, so this is a new rule block — and every size
        # in it must be one .copy-btn already ships (22x22 visual box,
        # 6px radius, the ::before -11px inset synthesizing a real 44x44
        # hit area, the 14px glyph), never a newly-invented icon-button
        # size.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()

        def _rule_body(selector):
            match = re.search(
                r"^" + re.escape(selector) + r"\s*\{([^}]*)\}", css, re.S | re.M)
            return match.group(1) if match else None

        bodies = {}
        for selector in (".copy-btn", ".copy-btn::before", ".copy-btn .icon",
                         ".row-toggle", ".row-toggle::before", ".row-toggle__glyph"):
            body = _rule_body(selector)
            if body is None:
                return False, "expected a %s rule block in style.css" % selector
            bodies[selector] = body

        for prop in ("width", "height", "border-radius"):
            copy_value = re.search(prop + r":\s*([^;]+);", bodies[".copy-btn"])
            toggle_value = re.search(prop + r":\s*([^;]+);", bodies[".row-toggle"])
            if copy_value is None or toggle_value is None:
                return False, "expected both .copy-btn and .row-toggle to declare %s" % prop
            if copy_value.group(1).strip() != toggle_value.group(1).strip():
                return False, (
                    "expected .row-toggle's %s (%r) to equal .copy-btn's (%r)"
                    % (prop, toggle_value.group(1).strip(), copy_value.group(1).strip()))
        if "inset:" not in bodies[".row-toggle::before"]:
            return False, "expected .row-toggle::before to synthesize the hit area with inset"
        copy_inset = re.search(r"inset:\s*([^;]+);", bodies[".copy-btn::before"]).group(1).strip()
        toggle_inset = re.search(
            r"inset:\s*([^;]+);", bodies[".row-toggle::before"]).group(1).strip()
        if copy_inset != toggle_inset:
            return False, (
                "expected .row-toggle::before's inset (%r) to equal .copy-btn::before's (%r) — "
                "22 + 11 + 11 = 44 in both axes" % (toggle_inset, copy_inset))

        copy_sizes = set(re.findall(r"\d+px", " ".join(
            bodies[s] for s in (".copy-btn", ".copy-btn::before", ".copy-btn .icon"))))
        toggle_sizes = set(re.findall(r"\d+px", " ".join(
            bodies[s] for s in (".row-toggle", ".row-toggle::before", ".row-toggle__glyph"))))
        new_sizes = toggle_sizes - copy_sizes
        if new_sizes:
            return False, (
                "expected .row-toggle to introduce no new size literal, found %s"
                % sorted(new_sizes))
        if "14px" not in toggle_sizes:
            return False, "expected the .row-toggle glyph to be sized at .copy-btn's own 14px"

        # The pointer cursor is keyed ONLY on the class flight-rows.js
        # adds at load — never rendered server-side (the no-JS floor).
        clickable = _rule_body(".flight-row--clickable")
        if clickable is None or "cursor: pointer" not in clickable:
            return False, "expected a .flight-row--clickable rule declaring cursor: pointer"
        page_source = open(
            os.path.join(HERE, "pages", "history_page.py")).read()
        if "flight-row--clickable" in page_source:
            return False, (
                "did not expect history_page.py to render the script's own clickable marker "
                "class — a scripts-blocked page must show no pointer cursor on a row")
        return True, ""
    check(
        "style.css's new .row-toggle rule block reuses .copy-btn's icon-only pattern verbatim "
        "(same 22x22 box, same radius, the same ::before inset synthesizing 44x44, the same 14px "
        "glyph) and introduces no new size literal; the pointer cursor is keyed only on the class "
        "flight-rows.js adds at load (22-09-PLAN.md Task 1, X5)",
        _row_toggle_css_reuses_the_copy_btn_icon_only_pattern)

    def _flight_rows_js_swaps_the_name_and_delegates_the_row_click():
        # 22-09-PLAN.md Task 1 (X5): the three-file contract — the two
        # data-*-label attribute names and the row hook this page
        # renders must all appear in flight-rows.js's own source, the
        # script must swap aria-label (not a text label) and must return
        # early for an interactive click target (T-22-32), and the no-JS
        # floor stays exactly where Phase 21's R-11 contract put it.
        js_path = os.path.join(HERE, "static", "flight-rows.js")
        with open(js_path) as fh:
            js = fh.read()
        for token in (history_page._TOGGLE_SHOW_LABEL_ATTR,
                      history_page._TOGGLE_HIDE_LABEL_ATTR,
                      "data-flight-row", "data-row-toggle",
                      "flight-detail-row--collapsed", "flight-row--clickable"):
            if token not in js:
                return False, "expected flight-rows.js to read/write %r" % (token,)
        if 'setAttribute("aria-label"' not in js:
            return False, "expected flight-rows.js to swap the button's aria-label"
        for retired in ("data-more-text", "data-less-text", "textContent"):
            if retired in js:
                return False, (
                    "expected flight-rows.js to stop writing the retired visible label (%r)"
                    % (retired,))
        for tag in ("A:", "BUTTON:", "INPUT:", "SELECT:", "TEXTAREA:", "LABEL:", "SUMMARY:"):
            if tag not in js:
                return False, (
                    "expected flight-rows.js's interactive-target guard to name %s" % tag)
        if "innerHTML" in js or "insertAdjacentHTML" in js:
            return False, "expected flight-rows.js to use no markup-writing DOM sink"

        # The no-JS floor, asserted on the server's own output: the
        # collapsing class exists ONLY in the script.
        tmp = _mkstate("h-no-js-floor")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "nj01", "callsign": "NOJSFLR"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if "flight-detail-row--collapsed" in rendered:
                return False, (
                    "expected the server-rendered detail row to carry no collapsing class "
                    "(the no-JS floor is a fully visible detail row)")
            detail = re.search(r'<tr class="flight-detail-row"[^>]*>', rendered)
            if detail is None:
                return False, "expected a server-rendered detail row"
            if "hidden" in detail.group(0) or "style=" in detail.group(0):
                return False, (
                    "expected the detail row to carry neither a hidden attribute nor an "
                    "inline style")
            if "cursor" in rendered:
                return False, "did not expect any cursor declaration in the server's own output"
            if rendered.count("data-flight-row") != 1:
                return False, (
                    "expected exactly one data-flight-row hook per summary row, found %d"
                    % rendered.count("data-flight-row"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "companion/static/flight-rows.js reads every attribute name history_page.py renders, "
        "swaps aria-label instead of a visible label, returns early for an interactive click "
        "target (T-22-32) and uses no markup-writing sink; the server still renders every detail "
        "row visible with no collapsing class, no hidden and no inline style (22-09-PLAN.md "
        "Task 1, X5/D-09)",
        _flight_rows_js_swaps_the_name_and_delegates_the_row_click)

    def _detail_row_carries_hex_iso_runway_not_in_summary_row():
        # 21-03-PLAN.md Task 2 (D-15): the hex, the raw ISO timestamp
        # and the runway appear inside the detail row and NOT in the
        # summary row's own slice.
        tmp = _mkstate("h-detail-row-content")
        try:
            raw_ts = "2026-08-27T10:00:00+00:00"
            _seed_runway_events(tmp, [
                {
                    "ts": raw_ts, "hex": "3944F2", "callsign": "DETCONTENT",
                    "tracked_runway": "3",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            summary_match = re.search(r'<tr class="row"[^>]*>(.*?)</tr>', rendered, re.S)
            detail_match = re.search(
                r'<tr class="flight-detail-row"[^>]*>(.*?)</tr>', rendered, re.S)
            if summary_match is None or detail_match is None:
                return False, "could not locate the summary/detail row pair"
            summary_block = summary_match.group(1)
            detail_block = detail_match.group(1)
            runway_label = device_config.runway_label("3")
            for value in ("3944F2", raw_ts, runway_label):
                if value not in detail_block:
                    return False, "expected %r inside the detail row" % (value,)
                if value in summary_block:
                    return False, "did not expect %r visible inside the summary row" % (value,)
            if 'colspan="6"' not in detail_block and 'colspan="6"' not in rendered:
                return False, "expected the detail row's <td> to span all 6 columns"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the hex, the raw ISO timestamp and the runway render inside the detail row and NOT in "
        "the summary row's own slice (21-03-PLAN.md Task 2, D-15)",
        _detail_row_carries_hex_iso_runway_not_in_summary_row)

    def _flights_render_has_no_inline_script_or_handler_attribute():
        # 21-03-PLAN.md Task 2 (D-15/R-12): the rendered page contains no
        # inline <script> and no on*= handler attribute anywhere.
        tmp = _mkstate("h-no-inline-script")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "ni01", "callsign": "NOINLINE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", rendered):
                return False, "expected no inline <script> without a src, found %r" % match.group(0)
            if re.search(r'\son[a-z]+="', rendered):
                return False, "expected no on*= inline handler attribute"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a rendered Flights page contains no inline <script> and no on*= handler attribute "
        "(21-03-PLAN.md Task 2, D-15/R-12)",
        _flights_render_has_no_inline_script_or_handler_attribute)

    def _flights_table_padding_rule_uses_space_sm_token_both_axes():
        # 21-03-PLAN.md Task 3 (D-15): the static half of the 880px
        # width-budget guarantee a Python harness can actually assert -
        # style.css's table.data-table--flights padding rule uses
        # var(--space-sm) on BOTH axes, never a literal px value (the
        # UI-SPEC's own column-width arithmetic depends on this token,
        # not a hardcoded number, staying in sync with --space-sm).
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule_match = re.search(
            r"table\.data-table--flights td,\s*\ntable\.data-table--flights th\s*\{([^}]*)\}",
            css, re.S)
        if rule_match is None:
            return False, "expected a table.data-table--flights td/th padding rule in style.css"
        rule_body = rule_match.group(1)
        if "padding: var(--space-sm) var(--space-sm);" not in rule_body:
            return False, (
                "expected the padding rule to use var(--space-sm) on both axes, not a literal "
                "px value")
        return True, ""
    check(
        "style.css's table.data-table--flights padding rule uses var(--space-sm) on both axes, "
        "never a literal px value (21-03-PLAN.md Task 3, D-15)",
        _flights_table_padding_rule_uses_space_sm_token_both_axes)

    def _flights_thead_carries_exactly_six_cells_in_both_languages():
        # 21-03-PLAN.md Task 3 (D-15): the other static half of the
        # width-budget guarantee - the rendered table's <thead> carries
        # exactly six <th> cells in both en and fr, the fact the width
        # budget depends on (six columns at 8px horizontal padding each
        # = 96px of padding inside the real 880px box).
        import companion.prefs as _prefs
        tmp = _mkstate("h-thead-six-both-languages")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "th01", "callsign": "THEADSIX"},
            ])
            rendered_en = history_page.render(_history_ctx(tmp))
            thead_en = re.search(r"<thead>(.*?)</thead>", rendered_en, re.S)
            if thead_en is None or len(re.findall(r"<th>", thead_en.group(1))) != 6:
                return False, "expected exactly 6 <th> cells in the English <thead>"

            _prefs.set_request_prefs(lang="fr")
            try:
                rendered_fr = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
            thead_fr = re.search(r"<thead>(.*?)</thead>", rendered_fr, re.S)
            if thead_fr is None or len(re.findall(r"<th>", thead_fr.group(1))) != 6:
                return False, "expected exactly 6 <th> cells in the French <thead>"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Flights table's <thead> carries exactly six <th> cells in both en and fr "
        "(21-03-PLAN.md Task 3, D-15)",
        _flights_thead_carries_exactly_six_cells_in_both_languages)

    def _mobile_details_three_copy_buttons():
        # D-23: the mobile card's details region carries all 3 copy
        # buttons (callsign, hex, full timestamp), each immediately
        # followed by its data-copy-feedback sibling.
        tmp = _mkstate("h-copy-mobile")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cm01", "callsign": "CMONE"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            details_match = re.search(
                r'<details class="history-card__details">(.*?)</details>', rendered, re.S)
            if not details_match:
                return False, "expected a history-card__details block"
            details = details_match.group(1)
            if details.count("data-copy-value") != 3:
                return False, (
                    "expected exactly 3 copy buttons in the mobile "
                    "details region, got %d" % details.count("data-copy-value"))
            feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", details))
            if feedback_pairs != 3:
                return False, (
                    "expected each mobile copy button to be immediately "
                    "followed by its data-copy-feedback sibling, found %d pairs"
                    % feedback_pairs)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the mobile card's details region contains exactly 3 copy buttons (callsign, hex, full timestamp), each immediately followed by its data-copy-feedback sibling",
        _mobile_details_three_copy_buttons)

    def _copy_button_carries_data_copied_text_english_and_french():
        # 20-11-PLAN.md Task 3 (D-06): copy-button.js reads its
        # on-success feedback text from each button's own
        # data-copied-text attribute instead of a hardcoded English
        # literal — this is that attribute's own translated value, under
        # each language in turn.
        import companion.prefs as _prefs
        tmp = _mkstate("h-copy-data-attr")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "cd01", "callsign": "CDONE"},
            ])
            rendered_en = history_page.render(_history_ctx(tmp))
            if 'data-copied-text="Copied"' not in rendered_en:
                return False, "expected data-copied-text=\"Copied\" under the default (English) language"

            _prefs.set_request_prefs(lang="fr")
            try:
                rendered_fr = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
            if 'data-copied-text="Copié"' not in rendered_fr:
                return False, "expected data-copied-text=\"Copié\" under lang='fr'"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a Flights render's copy buttons carry data-copied-text=\"Copied\" under the default "
        "language and data-copied-text=\"Copié\" under lang='fr' (D-06)",
        _copy_button_carries_data_copied_text_english_and_french)

    def _quick_260903_peo_desktop_copy_reveal_stylesheet_contract():
        # UIR-17: the desktop-only reveal rule lives inside the shared
        # min-width: 960px block, is scoped by [data-copy-value] (never
        # the bare .copy-btn class the always-visible View-panel/eye
        # trigger also carries), reveals via opacity + pointer-events
        # (never visibility: hidden or display: none, which would remove
        # the control from the tab order and break keyboard access — the
        # exact regression this finding forbids), and names both
        # tr:hover and tr:focus-within as its reveal triggers.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css_source = fh.read()

        media_marker = "@media (min-width: 960px) {"
        if media_marker not in css_source:
            return False, "expected style.css to declare the shared min-width: 960px block"
        media_start = css_source.index(media_marker)
        brace_at = css_source.index("{", media_start)
        depth, i = 0, brace_at
        while True:
            ch = css_source[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        media_block = css_source[brace_at + 1:i]
        # Same multi-line-selector normalization the existing
        # [data-filter-clear] guard above uses (joining a comma-grouped
        # selector split across lines onto one line), so this check is
        # not fooled by the file's own line-wrapping convention.
        normalized = re.sub(r",\s*\n\s*", ", ", media_block)

        rest_selector = ".data-table tbody tr [data-copy-value] {"
        if rest_selector not in normalized:
            return False, (
                "expected the at-rest rule to be scoped by [data-copy-value] "
                "inside the 960px block, not the bare .copy-btn class")
        rest_start = normalized.index(rest_selector)
        rest_body = normalized[rest_start:normalized.index("}", rest_start)]
        if "opacity" not in rest_body:
            return False, "expected the at-rest rule to declare opacity"
        if "visibility: hidden" in rest_body or "display: none" in rest_body:
            return False, (
                "expected the at-rest rule to use opacity + pointer-events, "
                "never visibility: hidden or display: none")

        reveal_selector = (
            ".data-table tbody tr:hover [data-copy-value], "
            ".data-table tbody tr:focus-within [data-copy-value] {")
        if reveal_selector not in normalized:
            return False, "expected one reveal rule naming both tr:hover and tr:focus-within"
        reveal_start = normalized.index(reveal_selector)
        reveal_body = normalized[reveal_start:normalized.index("}", reveal_start)]
        if "opacity: 1" not in reveal_body:
            return False, "expected the reveal rule to restore opacity: 1"
        if "visibility: hidden" in reveal_body or "display: none" in reveal_body:
            return False, "expected the reveal rule to carry no visibility/display override"
        return True, ""
    check(
        "the desktop copy-button reveal rule lives inside the shared 960px block, is scoped by "
        "[data-copy-value] (never the bare .copy-btn class), reveals via opacity + pointer-events "
        "(never visibility: hidden or display: none) on both tr:hover and tr:focus-within "
        "(quick task 260903-peo, UIR-17)",
        _quick_260903_peo_desktop_copy_reveal_stylesheet_contract)

    def _quick_260903_peo_desktop_row_copy_buttons_and_eye_button_discriminator():
        # UIR-17's original cross-file guard proved the desktop <tr>'s
        # copy buttons carried the [data-copy-value] discriminator the
        # reveal rule depends on. 21-03-PLAN.md Task 1 (D-15) moves
        # those copy buttons off the summary <tr> entirely (they land in
        # the Task 2 detail row instead, a later task in this same
        # plan) - this check is retargeted to prove the summary <tr> now
        # carries ZERO copy buttons, while the View-panel/eye trigger
        # (which never carried data-copy-value to begin with) still
        # renders unaffected.
        tmp = _mkstate("h-copy-reveal-discriminator")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "rev01", "callsign": "REVEAL"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            tr_block = _row_block(rendered, "tr", 0)
            if tr_block is None:
                return False, "could not locate the seeded row's desktop <tr>"
            if tr_block.count("data-copy-value") != 0:
                return False, (
                    "expected zero copy buttons in the desktop summary row, got %d"
                    % tr_block.count("data-copy-value"))
            # 22-09-PLAN.md Task 2 (X5): the picture control is no longer
            # in the summary row at all — it is a labelled control inside
            # the detail row now, which is what leaves the summary row's
            # scan path a single chevron. It still must never carry
            # data-copy-value, the discriminator the desktop reveal rule
            # keys on (it is NOT a copy button and must stay visible).
            if "data-view-panel-src" in tr_block:
                return False, (
                    "did not expect the picture control in the summary row — it moved into "
                    "the detail row (22-09-PLAN.md Task 2, X5)")
            detail_block = _detail_row_block(rendered, 0)
            if detail_block is None or "data-view-panel-src" not in detail_block:
                return False, "expected the row's picture control to render in the detail row"
            view_panel_start = detail_block.index("data-view-panel-src")
            view_panel_tag = detail_block[
                detail_block.rindex("<", 0, view_panel_start):
                detail_block.index(">", view_panel_start) + 1]
            if "data-copy-value" in view_panel_tag:
                return False, (
                    "the picture control must never carry data-copy-value "
                    "— that is the sole discriminator separating it from any "
                    "copy button the desktop reveal rule targets")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a real rendered desktop History summary row carries zero copy buttons (21-03-PLAN.md "
        "Task 1, D-15) and no picture control at all (22-09-PLAN.md Task 2, X5 — it moved into "
        "the detail row), and that control still never carries data-copy-value — the "
        "discriminator the desktop reveal rule depends on "
        "(quick task 260903-peo, UIR-17)",
        _quick_260903_peo_desktop_row_copy_buttons_and_eye_button_discriminator)

    def _copy_buttons_no_longer_share_one_aria_label():
        # A-37/D-20: the defect this task closes — every one of a
        # page's ~50 copy buttons used to share one identical
        # aria-label. Two differently-named rows must now render at
        # least two distinct aria-label values among their copy
        # buttons.
        tmp = _mkstate("h-copy-distinct-labels")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "dl01", "callsign": "DISTINCT1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "dl02", "callsign": "DISTINCT2"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            aria_labels = set(re.findall(r'aria-label="([^"]*)"', rendered))
            copy_labels = {
                label for label in aria_labels
                if "Copy callsign" in label or "Copy hex ID" in label
                or "Copy timestamp" in label}
            if len(copy_labels) < 2:
                return False, (
                    "expected at least 2 distinct copy-button aria-labels, got %d: %r"
                    % (len(copy_labels), copy_labels))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with two differently-named rows, at least two distinct copy-button aria-label values "
        "render on the page — the '50 identical names' defect closed (A-37/D-20)",
        _copy_buttons_no_longer_share_one_aria_label)

    def _each_copy_button_aria_label_names_its_own_row():
        # A-37/D-20: each row's copy buttons must name THAT row's own
        # callsign, not merely differ from each other. 21-03-PLAN.md
        # Task 1 (D-15) moves the desktop copy buttons off the summary
        # <tr> (they land in the Task 2 detail row instead, a later
        # task in this same plan) - retargeted to the mobile <li>'s own
        # copy buttons, which are unchanged (D-16).
        tmp = _mkstate("h-copy-own-row")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "or01", "callsign": "OWNROW1"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "or02", "callsign": "OWNROW2"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            # Rows render newest-first (history_db.recent_runway_events()'s
            # own ordering) - the later timestamp (OWNROW2) lands at
            # data-filter-group=0, the earlier one (OWNROW1) at 1.
            for index, callsign in ((0, "OWNROW2"), (1, "OWNROW1")):
                li_block = _row_block(rendered, "li", index)
                if li_block is None:
                    return False, "could not locate mobile row block for data-filter-group=%d" % index
                if callsign not in li_block:
                    return False, "expected %r inside its own row's markup" % callsign
                if ('aria-label="Copy callsign %s"' % callsign) not in li_block:
                    return False, (
                        "expected row %d's callsign copy button to name its own "
                        "callsign %r" % (index, callsign))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "each row's mobile-card callsign copy button carries an aria-label naming that row's "
        "own callsign, not a shared/generic name (A-37/D-20, retargeted off the desktop row by "
        "21-03-PLAN.md Task 1)",
        _each_copy_button_aria_label_names_its_own_row)

    def _copy_button_script_propagates_execcommand_success():
        # A-37/D-20's third half: fallbackCopy() used to call
        # document.execCommand("copy") and discard its boolean return
        # value, so handleClick() showed "Copied" even when the copy
        # silently failed. Source-level check, mirroring
        # test_companion_app.py's own token-ban convention for static
        # scripts (companion/static/panel-lookup.js et al.).
        js_path = os.path.join(HERE, "static", "copy-button.js")
        with open(js_path) as fh:
            src = fh.read()
        if "return document.execCommand" not in src:
            return False, "expected fallbackCopy() to return document.execCommand(...)'s result"
        banned = (
            "let ", "const ", "=>", "`", "innerHTML", "insertAdjacentHTML",
            "document.write", "eval(",
        )
        for token in banned:
            if token in src:
                return False, "copy-button.js must not contain %r" % token
        return True, ""
    check(
        "copy-button.js propagates fallbackCopy()'s real document.execCommand(...) result "
        "instead of discarding it, and stays ES5-safe/sink-free (A-37/D-20)",
        _copy_button_script_propagates_execcommand_success)

    def _copy_button_markup_carries_icon_and_label_spans():
        # D-20: every rendered copy button must carry exactly one
        # .copy-btn__icon span (wrapping the SVG, aria-hidden) and one
        # .copy-btn__label span (empty at rest, copy-button.js's own
        # write target) - and the data-copy-feedback sibling contract
        # copy-button.js depends on must survive unchanged.
        tmp = _mkstate("h-copy-spans")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "sp01", "callsign": "SPANS1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            button_count = rendered.count("data-copy-value")
            if button_count == 0:
                return False, "expected at least one copy button to render"
            icon_count = rendered.count('<span class="copy-btn__icon" aria-hidden="true">')
            if icon_count != button_count:
                return False, (
                    "expected exactly one copy-btn__icon span per copy button, got %d for %d buttons"
                    % (icon_count, button_count))
            label_count = rendered.count('<span class="copy-btn__label"></span>')
            if label_count != button_count:
                return False, (
                    "expected exactly one empty copy-btn__label span per copy button, got %d for %d buttons"
                    % (label_count, button_count))
            feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", rendered))
            if feedback_pairs != button_count:
                return False, (
                    "expected every copy button to still be immediately followed by its "
                    "data-copy-feedback sibling, found %d pairs for %d buttons"
                    % (feedback_pairs, button_count))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every rendered copy button carries exactly one copy-btn__icon span and one empty "
        "copy-btn__label span, and its data-copy-feedback sibling still immediately follows "
        "the button (D-20)",
        _copy_button_markup_carries_icon_and_label_spans)

    def _copy_button_script_references_label_class_and_1500ms():
        js_path = os.path.join(HERE, "static", "copy-button.js")
        with open(js_path) as fh:
            src = fh.read()
        if "copy-btn__label" not in src:
            return False, "expected copy-button.js to reference copy-btn__label"
        if "copy-btn--copied" not in src:
            return False, "expected copy-button.js to reference copy-btn--copied"
        if "1500" not in src:
            return False, "expected copy-button.js's FEEDBACK_RESET_MS to be 1500"
        return True, ""
    check(
        "copy-button.js references the copy-btn__label/copy-btn--copied class names and the "
        "1.5s (1500ms) feedback window (D-20)",
        _copy_button_script_references_label_class_and_1500ms)

    def _style_css_styles_both_copy_feedback_classes():
        # Cross-file CSS guard, mirroring
        # _data_table_wrap_scroll_edge_affordance_css()'s own regex-
        # rule-match technique above - never a regex CSS parser, just a
        # targeted selector-presence check.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        if re.search(r"\.copy-btn__label\s*\{", css) is None:
            return False, "expected a .copy-btn__label rule in style.css"
        if re.search(r"\.copy-btn--copied\s+\.copy-btn__label\s*\{", css) is None:
            return False, "expected a .copy-btn--copied .copy-btn__label rule in style.css"
        return True, ""
    check(
        "style.css styles both copy-btn__label and copy-btn--copied (D-20)",
        _style_css_styles_both_copy_feedback_classes)

    def _presentation_labels_in_full_render():
        # UXA-05: Task 1's format_event_row()-level fixture, re-asserted
        # against the full render() output (both the desktop cell and
        # the mobile card), and confirms the audit's own incorrect
        # literal state-value strings never appear.
        #
        # merge of origin/main (quick task 260902-j21): runway "3"'s
        # device_config.runway_label() display text was relabelled from
        # "Runway 3 (07/25)" to the official "Piste 3" — derived here at
        # test time from the real registry rather than hardcoded, so this
        # check tracks whatever label device_config actually returns
        # instead of re-drifting the next time the copy changes.
        tmp = _mkstate("h-labels")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "pl01", "callsign": "PL1",
                    "confirmed_state": "departing", "tracked_runway": "3",
                },
                {
                    "ts": "2026-08-27T10:01:00+00:00", "hex": "pl02", "callsign": "PL2",
                    "confirmed_state": "taxiing",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            for expected in ("Departing", device_config.runway_label("3"), "Taxiing"):
                if expected not in rendered:
                    return False, "expected %r in the rendered History page" % expected
            for wrong in ("on_runway", "approaching", 'departed"'):
                if wrong in rendered:
                    return False, (
                        "did not expect the audit's own incorrect literal "
                        "state value %r in the rendered History page" % wrong)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "confirmed_state/tracked_runway presentation labels (Task 1's format_event_row() fixture) also appear correctly through the full render() output",
        _presentation_labels_in_full_render)

    def _french_render_translates_the_runway_cell_label():
        # Polish fix 5 (D-05): history_page._runway_label() now
        # translates device_config.runway_label()'s registry text via
        # i18n.t() (companion/i18n_fr/registry.py) — the runway id
        # itself ("3") is data, never translated.
        import companion.prefs as _prefs
        tmp = _mkstate("h-labels-fr")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "pl03", "callsign": "PL3",
                    "confirmed_state": "departing", "tracked_runway": "3",
                },
            ])
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
            if "Piste 3 (07/25)" not in rendered:
                return False, "expected the French runway label 'Piste 3 (07/25)' in the rendered page"
            if device_config.runway_label("3") in rendered:
                return False, (
                    "expected the English runway label %r to be absent from the French render"
                    % (device_config.runway_label("3"),))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a French Flights render translates the tracked_runway cell's registry label "
        "('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), with no English label leaking in "
        "(Polish fix 5, D-05)",
        _french_render_translates_the_runway_cell_label)

    # ======================================================================
    # Section 1b: quick task 260903-etm - History's top-of-page render-
    # gallery <section> retired outright (developer redirection superseding
    # quick task 260903-c4o's own always-visible render-gallery section on
    # this same unmerged branch). The per-row "View panel near this time"
    # lightbox (D-20) is the sole surviving way to see a rendered panel on
    # this page; the orphaned colour caveat is rehomed into its note.
    # ======================================================================

    def _history_render_gallery_section_absent_with_content():
        tmp = _mkstate("h-gallery-section-absent")
        try:
            names = [
                "2026-08-27T10-02-00+00-00.png",
                "2026-08-27T10-01-00+00-00.png",
                "2026-08-27T10-00-00+00-00.png",
            ]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:03:00+00:00", "hex": "notdisc1", "callsign": "NOTDISC"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            if "<h2" in rendered:
                return False, "did not expect any <h2 element - the render-gallery section is gone"
            if "page-section" in rendered:
                return False, "did not expect any page-section element - the render-gallery section is gone"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid container element"
            if 'class="gallery-tile"' in rendered:
                return False, "did not expect a gallery-tile element"
            if "Recent renders" in rendered:
                return False, "did not expect the retired render-gallery heading text"
            if "No renders yet." in rendered:
                return False, "did not expect the retired no-renders empty-state heading text"
            # The per-row mechanism must survive in the SAME render that
            # proves the section is gone (T-etm-03) - a careless "remove
            # the gallery" reading could sever gallery_entries_list along
            # with the markup it used to feed.
            if "data-view-panel-src" not in rendered:
                return False, "expected at least one View-panel trigger to survive"
            if rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) != 1:
                return False, "expected exactly one lightbox dialog to survive"
            if '<details class="history-card__details"' not in rendered:
                return False, "expected History's own card disclosures to survive"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with 3 gallery entries and one seeded flight row, the rendered page carries zero <h2, "
        "zero page-section, zero gallery-grid/gallery-tile elements and zero occurrences of the "
        "retired heading/empty-state text, WHILE the per-row View-panel mechanism (a trigger, "
        "exactly one lightbox dialog) and History's own card disclosures survive in the same render",
        _history_render_gallery_section_absent_with_content)

    def _history_render_gallery_section_absent_when_empty():
        tmp = _mkstate("h-gallery-section-absent-empty")
        try:
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=[]))
            if "<h2" in rendered:
                return False, "did not expect any <h2 element with an empty gallery"
            if "page-section" in rendered:
                return False, "did not expect any page-section element with an empty gallery"
            if 'class="gallery-grid"' in rendered:
                return False, "did not expect a gallery-grid container element"
            if 'class="gallery-tile"' in rendered:
                return False, "did not expect a gallery-tile element"
            if "Recent renders" in rendered:
                return False, "did not expect the retired render-gallery heading text"
            if "No renders yet." in rendered:
                return False, "did not expect the retired no-renders empty-state heading text"
            if "data-view-panel-src" in rendered:
                return False, "did not expect any View-panel trigger with an empty gallery"
            if ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) in rendered:
                return False, "did not expect a lightbox dialog with an empty gallery"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with gallery_entries=[], the same absences hold (the section is gone, not merely "
        "emptied) and, as before, zero View-panel triggers and zero lightbox dialogs render",
        _history_render_gallery_section_absent_when_empty)

    def _view_panel_trigger_is_a_labelled_control_with_the_long_form_as_title():
        # 22-09-PLAN.md Task 2 (X5): retargeted from "title byte-equal to
        # its own aria-label". The control is no longer a 16px icon-only
        # eye whose only name was an aria-label: it carries a VISIBLE
        # translated label ("View picture"), which is therefore its
        # accessible name, and the longer VIEW_PANEL_LABEL survives as
        # the `title` a pointer user gets on hover. A duplicate
        # aria-label would now CONTRADICT the visible text (WCAG 2.5.3
        # label-in-name), so its absence is the contract.
        tmp = _mkstate("h-view-panel-title")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vptt01", "callsign": "VPTITLE"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        escaped_label = layout.escape_html(history_page.VIEW_PANEL_LABEL)
        expected_title = 'title="%s"' % escaped_label
        expected_text = '>%s</button>' % layout.escape_html(
            history_page.VIEW_PICTURE_LABEL)
        detail_block = _detail_row_block(rendered, 0)
        li_block = _row_block(rendered, "li", 0)
        if detail_block is None or li_block is None:
            return False, "could not locate the detail row / mobile card for row 0"
        for label, block in (("detail <tr>", detail_block), ("mobile <li>", li_block)):
            if expected_title not in block:
                return False, "expected %s to carry title=%r" % (label, escaped_label)
            if expected_text not in block:
                return False, (
                    "expected %s's picture control to carry the visible label %r"
                    % (label, history_page.VIEW_PICTURE_LABEL))
            trigger_start = block.index("data-view-panel-src")
            trigger_tag = block[
                block.rindex("<", 0, trigger_start):block.index(">", trigger_start) + 1]
            if "aria-label" in trigger_tag:
                return False, (
                    "did not expect an aria-label on %s's picture control — the visible label "
                    "is its accessible name (WCAG 2.5.3 label-in-name)" % label)
        return True, ""
    check(
        "the rendered picture control is a LABELLED text control carrying the translated "
        "\"View picture\" text and no aria-label, with \"View panel near this time\" surviving "
        "as its title, on both the desktop detail row and the mobile card (22-09-PLAN.md "
        "Task 2, X5)",
        _view_panel_trigger_is_a_labelled_control_with_the_long_form_as_title)

    def _colour_caveat_rehomed_into_lightbox_note():
        tmp = _mkstate("h-caveat-rehomed")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "cvt001", "callsign": "CAVEAT"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if rendered.count(history_page.COLOUR_CAVEAT) != 1:
            return False, "expected the colour caveat sentence exactly once in the rendered page"
        note_match = re.search(
            r'<p class="lightbox__note text-body">(.*?)</p>', rendered, re.S)
        if note_match is None:
            return False, "could not locate the lightbox__note element"
        if history_page.COLOUR_CAVEAT not in note_match.group(1):
            return False, "expected the colour caveat to fall inside the lightbox__note element"
        return True, ""
    check(
        "the colour caveat sentence appears exactly once in the rendered page, and that single "
        "occurrence lies inside the lightbox__note element (the caveat's new, and only, home "
        "after the render-gallery section's removal)",
        _colour_caveat_rehomed_into_lightbox_note)

    def _render_gallery_no_preview_apparatus_even_with_panel_file():
        tmp = _mkstate("h-gallery-no-preview-apparatus")
        try:
            names = ["20260827T100000Z.png"]
            _seed_gallery(tmp, names)
            _write_panel_file(tmp)
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
            for marker in ("/preview.png", "preview-frame", "preview-image"):
                if marker in rendered:
                    return False, "did not expect %r anywhere in the rendered page" % marker
            if "No panel has been rendered yet." in rendered:
                return False, "did not expect the retired no-panel caption sentence"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with a real panel.bin on disk and gallery entries seeded, the rendered output contains "
        "zero occurrences of /preview.png, preview-frame, preview-image, and the old no-panel "
        "caption sentence - a present panel file changes nothing about the markup any more "
        "(this check's real subject is quick task 260903-c4o's /preview.png route retirement, "
        "not the render-gallery section retired by this task; kept in place rather than dropped)",
        _render_gallery_no_preview_apparatus_even_with_panel_file)

    def _now_showing_no_preview_freshness_apparatus():
        # D-18: Preview's page-level freshness apparatus (its own
        # data-loaded-at Refresh link and paired data-stale-banner) was
        # deliberately not ported when Preview's content first moved onto
        # History (06.6.4.1-05), and quick task 260903-c4o's further
        # restructure (folding the newest render into the gallery grid,
        # retiring the separate frame) does not change that guarantee.
        #
        # 23-08-PLAN.md Task 1: RETARGETED IN PLACE, no count change, and
        # this one is a real reversal rather than a re-scoping — so it is
        # written down here rather than quietly dropped.
        #
        # D7/CFG-37 (locked on the Phase 23 ROADMAP) puts Flights on the
        # same self-refreshing loop Home, Display and Health already run,
        # and companion/static/freshness.js returns at its first guard on
        # any page with no [data-loaded-at]: no marker, no loop. So the
        # marker is now REQUIRED — exactly once, and only as
        # layout.freshness_line_html()'s own output, which is the clause
        # that keeps a hand-built second apparatus out.
        #
        # What this check still forbids is what D-18 was actually about:
        # the RETIRED mechanism. `data-stale-banner` is gone for good
        # (its own SUPERSEDED record is in freshness.js's header), and so
        # is the manual Refresh LINK the marker used to hang on — the
        # marker's home now is a hidden pill the loop reveals, not a
        # control the reader has to press. Both are asserted.
        tmp = _mkstate("h-no-freshness")
        try:
            rendered = history_page.render(_history_ctx(tmp))
            if "data-stale-banner" in rendered:
                return False, "did not expect a data-stale-banner element on the History page"
            if rendered.count("data-loaded-at") != 1:
                return False, (
                    "expected exactly one data-loaded-at marker on the History page — D7/CFG-37 "
                    "puts this page on the refresh loop and freshness.js returns at its first "
                    "guard without one, while a second would be two claims about when this "
                    "document was generated; found %d" % rendered.count("data-loaded-at"))
            built = layout.freshness_line_html(_history_ctx(tmp)["now"])
            if "data-loaded-at" not in built:
                return False, (
                    "expected layout.freshness_line_html() to be the thing that carries the "
                    "marker — this check reads it back from the builder rather than pinning a "
                    "literal, so the builder stays the one definition site")
            marker_at = rendered.index("data-loaded-at")
            around = rendered[max(0, marker_at - 400):marker_at]
            if "<a " in around[around.rfind("<p class=\"page-header__freshness"):]:
                return False, (
                    "did not expect a link inside the freshness line — D-18 retired the manual "
                    "Refresh control outright and the marker's home is the hidden pill the loop "
                    "reveals, never an anchor the reader has to press")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered History page carries no data-stale-banner and no Refresh link — D-18's "
        "retired apparatus stays retired — while carrying exactly one data-loaded-at marker, "
        "built by layout.freshness_line_html(), because D7/CFG-37 puts this page on the refresh "
        "loop and freshness.js returns at its first guard without one (retargeted in place by "
        "23-08-PLAN.md Task 1)",
        _now_showing_no_preview_freshness_apparatus)

    def _gallery_name_to_iso_fixtures():
        # D-22/06.6.3-RESEARCH.md Pitfall 2: the well-formed reversal only
        # touches the time+offset portion; a missing "T" separator or a
        # malformed time+offset portion both degrade to None rather than
        # raising. Carried over here (06.6.4.1-08 Task 3) from
        # companion/pages/preview_page.py's own now-deleted coverage of
        # the identical helper, which history_page.py absorbed byte-for-
        # byte in 06.6.4.1-05 — not otherwise duplicated on the History
        # side.
        well_formed = history_page._gallery_name_to_iso(
            "2026-08-30T19-20-42+00-00.png")
        if well_formed != "2026-08-30T19:20:42+00:00":
            return False, (
                "expected the well-formed fixture to reverse to %r, got %r"
                % ("2026-08-30T19:20:42+00:00", well_formed))
        if history_page._gallery_name_to_iso("not-a-real-name.png") is not None:
            return False, "expected a filename with no 'T' separator to return None"
        if history_page._gallery_name_to_iso("2026-08-30Tgarbage.png") is not None:
            return False, "expected a malformed time+offset portion to return None"
        return True, ""
    check(
        "history_page._gallery_name_to_iso() reverses a well-formed gallery filename and "
        "returns None (never raising) on a missing 'T' separator or a "
        "malformed time+offset portion",
        _gallery_name_to_iso_fixtures)

    def _view_panel_trigger_reuses_the_small_grey_secondary_treatment():
        # 06.6.4.1-08 (D-22) Task 2 acceptance criterion, placed here
        # (test_view_pages.py) rather than test_companion_app.py since
        # this needs a full History render with a matched gallery entry
        # — layout-level coverage that icon_html("icon-nav-preview")
        # itself returns non-empty markup lives in
        # test_companion_app.py's own eye-glyph-survives-nav-shrink check.
        tmp = _mkstate("h-view-panel-icon")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpicon1", "callsign": "VPICON"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if "data-view-panel-src" not in rendered:
            return False, "expected at least one View-panel trigger to render"
        trigger_start = rendered.find("data-view-panel-src")
        button_start = rendered.rfind("<button", 0, trigger_start)
        button_end = rendered.find("</button>", trigger_start)
        button_markup = rendered[button_start:button_end]
        # 22-09-PLAN.md Task 2 (X5): retargeted from "carries a non-empty
        # <svg> icon". The 16px icon-only eye is exactly the defect — the
        # control is a labelled text button now, reusing
        # .calendar-disconnect-btn's small-grey-secondary treatment (its
        # SECOND consumer, the pattern references/control-density.md
        # names for a small de-emphasised secondary action), with no
        # glyph of its own and no new .btn family.
        if "<svg" in button_markup:
            return False, (
                "did not expect an icon glyph on the picture control — it is a labelled text "
                "control now, not a 16px icon-only eye")
        if 'class="calendar-disconnect-btn"' not in button_markup:
            return False, (
                "expected the picture control to reuse .calendar-disconnect-btn's "
                "small-grey-secondary treatment, got %r" % button_markup[:120])
        if "btn--" in rendered:
            return False, "did not expect a .btn-- family class to be started"
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        if ".calendar-disconnect-btn {" not in css:
            return False, "expected the reused .calendar-disconnect-btn rule to exist in style.css"
        return True, ""
    check(
        "a rendered History page's picture control carries no icon glyph at all and reuses "
        ".calendar-disconnect-btn's small-grey-secondary treatment — that component's second "
        "consumer, with no .btn family started (22-09-PLAN.md Task 2, X5)",
        _view_panel_trigger_reuses_the_small_grey_secondary_treatment)

    # ======================================================================
    # Section 1c: 06.6.4.1-05 Task 2 - server-side nearest-render lookup,
    # per-row View-panel buttons, and the shared lightbox (D-20).
    # ======================================================================

    def _nearest_gallery_entry_behaviour():
        entries = [
            "2026-08-27T10-05-00+00-00.png",
            "2026-08-27T10-02-00+00-00.png",
            "2026-08-27T10-00-00+00-00.png",
            "not-a-real-gallery-name.png",  # unparseable - must be skipped
        ]

        # Between two entries: matches the latest one at or before row_ts.
        match = history_page.nearest_gallery_entry(entries, "2026-08-27T10:03:00+00:00")
        if match != ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"):
            return False, "expected the latest entry at or before 10:03:00, got %r" % (match,)

        # Exact boundary: row_ts equal to an entry's own recovered
        # timestamp still matches that entry ("at or before" is
        # inclusive).
        match = history_page.nearest_gallery_entry(entries, "2026-08-27T10:02:00+00:00")
        if match != ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"):
            return False, "expected an exact-boundary row_ts to match its own entry, got %r" % (match,)

        # Every recoverable entry strictly after row_ts -> None.
        if history_page.nearest_gallery_entry(entries, "2026-08-27T09:00:00+00:00") is not None:
            return False, "expected None when every recoverable entry is strictly after row_ts"

        # Empty entry list -> None.
        if history_page.nearest_gallery_entry([], "2026-08-27T10:03:00+00:00") is not None:
            return False, "expected None for an empty entry list"

        # Unparseable/empty row_ts -> None, never raising.
        if history_page.nearest_gallery_entry(entries, "") is not None:
            return False, "expected None for an empty row_ts"
        if history_page.nearest_gallery_entry(entries, "not-a-real-timestamp") is not None:
            return False, "expected None for an unparseable row_ts"
        if history_page.nearest_gallery_entry(entries, None) is not None:
            return False, "expected None for a None row_ts, never raising"

        return True, ""
    check(
        "nearest_gallery_entry() matches the latest at-or-before entry (inclusive boundary), skips "
        "an entry with an unrecoverable filename timestamp, and returns None for an empty entry "
        "list, an empty/unparseable row_ts, or when every recoverable entry is strictly after row_ts",
        _nearest_gallery_entry_behaviour)

    def _view_panel_triggers_per_row_full_render():
        tmp = _mkstate("h-view-panel-rows")
        try:
            names = [
                "2026-08-27T10-05-00+00-00.png",
                "2026-08-27T10-02-00+00-00.png",
                "2026-08-27T10-00-00+00-00.png",
            ]
            _seed_gallery(tmp, names)
            # Newest-first row order (history_rows()'s own ordering):
            # VP-C (10:10) -> VP-B (10:03) -> VP-A (10:01).
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpa01", "callsign": "VPA"},
                {"ts": "2026-08-27T10:03:00+00:00", "hex": "vpb01", "callsign": "VPB"},
                {"ts": "2026-08-27T10:10:00+00:00", "hex": "vpc01", "callsign": "VPC"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))

            expected_by_group = {
                0: ("2026-08-27T10-05-00+00-00.png", "2026-08-27T10:05:00+00:00"),  # VPC
                1: ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"),  # VPB
                2: ("2026-08-27T10-00-00+00-00.png", "2026-08-27T10:00:00+00:00"),  # VPA
            }
            for index, (expected_name, expected_iso) in expected_by_group.items():
                expected_src = "/gallery/%s" % expected_name
                expected_caption = history_page.lightbox_caption_text(expected_iso)

                # 22-09-PLAN.md Task 2 (X5): the desktop trigger moved
                # from the summary row into its sibling detail row.
                tr_block = _detail_row_block(rendered, index)
                li_block = _row_block(rendered, "li", index)
                if tr_block is None or li_block is None:
                    return False, "could not locate row block for row %d" % index

                for label, block in (("detail <tr>", tr_block), ("mobile <li>", li_block)):
                    if ('data-view-panel-src="%s"' % expected_src) not in block:
                        return False, (
                            "expected %s for row %d to carry data-view-panel-src=%r"
                            % (label, index, expected_src))
                    if ('data-view-panel-caption="%s"' % expected_caption) not in block:
                        return False, (
                            "expected %s for row %d to carry data-view-panel-caption=%r"
                            % (label, index, expected_caption))
                    if history_page.VIEW_PANEL_LABEL not in block:
                        return False, (
                            "expected %s for row %d to carry the View-panel title" % (label, index))
                    if history_page.VIEW_PICTURE_LABEL not in block:
                        return False, (
                            "expected %s for row %d to carry the visible picture label"
                            % (label, index))

                tr_src = re.search(r'data-view-panel-src="([^"]*)"', tr_block).group(1)
                li_src = re.search(r'data-view-panel-src="([^"]*)"', li_block).group(1)
                tr_caption = re.search(r'data-view-panel-caption="([^"]*)"', tr_block).group(1)
                li_caption = re.search(r'data-view-panel-caption="([^"]*)"', li_block).group(1)
                if tr_src != li_src or tr_caption != li_caption:
                    return False, (
                        "expected byte-identical trigger attributes on the desktop and mobile "
                        "representations of row %d" % index)

            if rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) != 1:
                return False, "expected exactly one lightbox dialog element"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "for three gallery entries and three interleaved rows, each row's desktop and mobile "
        "View-panel trigger carries byte-identical, correctly-targeted data-view-panel-src/-caption "
        "attributes matching its own nearest gallery entry, and exactly one lightbox dialog is emitted",
        _view_panel_triggers_per_row_full_render)

    def _view_panel_empty_gallery_zero_triggers_zero_dialog():
        tmp = _mkstate("h-view-panel-empty-gallery")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "vpe01", "callsign": "VPEMPTY"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=[]))
            if "data-view-panel-src" in rendered:
                return False, "did not expect any View-panel trigger with an empty gallery entry list"
            if ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) in rendered:
                return False, "did not expect a lightbox dialog element with an empty gallery entry list"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "with an empty gallery entry list, History renders zero View-panel triggers and zero "
        "lightbox dialog elements, never a disabled or broken control",
        _view_panel_empty_gallery_zero_triggers_zero_dialog)

    def _lightbox_dom_contract_three_file_guard():
        # Source/DOM-contract guard, restructured (phase 14 plan 14-01
        # Task 2) into three classified token tuples instead of one
        # inline literal: _LIGHTBOX_SHARED_TOKENS must appear in
        # panel-lookup.js's source and in both pages' rendered markup;
        # _LIGHTBOX_AIRLINES_ONLY_TOKENS must appear in panel-lookup.js
        # and in Airlines' rendered markup, and must be absent from
        # History's; _LIGHTBOX_RENDER_ONLY_TOKENS is asserted present in
        # Airlines' rendered markup only, with no claim at all against
        # panel-lookup.js or History. A drift in any of the three would
        # leave the button silently doing nothing with no signal from
        # any file in isolation.
        js_path = os.path.join(HERE, "static", "panel-lookup.js")
        with open(js_path) as fh:
            js_source = fh.read()

        tmp = _mkstate("h-dom-contract")
        try:
            names = ["2026-08-27T10-00-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "dc01", "callsign": "DOMCONTRACT"},
            ])
            history_rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        # 29-01-PLAN.md (CFG-81): LIGHTBOX_REPLACE_FORM_CLASS
        # ("lightbox__replace") is unconditional now — the page-wide
        # editing mode this guard used to need is deleted — so a plain
        # default render already carries it.
        airlines_rendered = airlines_page.render({})

        for token in _LIGHTBOX_SHARED_TOKENS:
            if token not in js_source:
                return False, "expected shared token %r to appear in companion/static/panel-lookup.js" % token
            if token not in history_rendered:
                return False, "expected shared token %r to appear in the rendered History page" % token
            if token not in airlines_rendered:
                return False, "expected shared token %r to appear in the rendered Airlines page" % token

        for token in _LIGHTBOX_AIRLINES_ONLY_TOKENS:
            if token not in js_source:
                return False, (
                    "expected Airlines-only token %r to appear in companion/static/panel-lookup.js" % token)
            if token not in airlines_rendered:
                return False, "expected Airlines-only token %r to appear in the rendered Airlines page" % token
            if token in history_rendered:
                return False, "did not expect Airlines-only token %r in the rendered History page" % token

        for token in _LIGHTBOX_RENDER_ONLY_TOKENS:
            if token not in airlines_rendered:
                return False, "expected render-only token %r to appear in the rendered Airlines page" % token

        return True, ""
    check(
        "the shared, Airlines-only and render-only lightbox token tuples each appear (or, for "
        "Airlines-only, are absent from History) exactly where their own classification says they "
        "must, across companion/static/panel-lookup.js and both pages' rendered markup",
        _lightbox_dom_contract_three_file_guard)

    def _view_panel_attr_constants_all_classified():
        # Reflection-driven coverage check (phase 14 plan 14-01 Task 2):
        # enumerate every airlines_page module attribute matching the
        # exact shape _VIEW_PANEL_...(_ATTR) and assert its *value*
        # appears in exactly one of the three classified token tuples
        # above. A hand-copied list here would be the same drift this
        # guard exists to catch, one level up - so this walks
        # dir(airlines_page) instead of restating a name list.
        all_tuples = (
            _LIGHTBOX_SHARED_TOKENS,
            _LIGHTBOX_AIRLINES_ONLY_TOKENS,
            _LIGHTBOX_RENDER_ONLY_TOKENS,
        )

        # The three tuples must never overlap - a token classified in
        # two of them at once would carry contradictory expectations.
        seen = {}
        for tuple_name, tup in (
            ("_LIGHTBOX_SHARED_TOKENS", _LIGHTBOX_SHARED_TOKENS),
            ("_LIGHTBOX_AIRLINES_ONLY_TOKENS", _LIGHTBOX_AIRLINES_ONLY_TOKENS),
            ("_LIGHTBOX_RENDER_ONLY_TOKENS", _LIGHTBOX_RENDER_ONLY_TOKENS),
        ):
            for token in tup:
                if token in seen:
                    return False, (
                        "token %r is classified in both %s and %s - the three tuples must be "
                        "pairwise disjoint" % (token, seen[token], tuple_name))
                seen[token] = tuple_name

        for name in dir(airlines_page):
            if not (name.startswith("_VIEW_PANEL_") and name.endswith("_ATTR")):
                continue
            value = getattr(airlines_page, name)
            memberships = [tup for tup in all_tuples if value in tup]
            if len(memberships) == 0:
                return False, (
                    "airlines_page.%s = %r is not classified in any of _LIGHTBOX_SHARED_TOKENS, "
                    "_LIGHTBOX_AIRLINES_ONLY_TOKENS or _LIGHTBOX_RENDER_ONLY_TOKENS" % (name, value))
            if len(memberships) > 1:
                return False, (
                    "airlines_page.%s = %r is classified in more than one of the three token "
                    "tuples" % (name, value))
        return True, ""
    check(
        "every airlines_page._VIEW_PANEL_*_ATTR constant's value is classified in exactly one of "
        "the three lightbox token tuples, discovered by reflection over dir(airlines_page) rather "
        "than a hand-copied name list",
        _view_panel_attr_constants_all_classified)

    # --- Phase 14 plan 14-05 Task 2: eight source-content checks pinning
    # panel-lookup.js's own contract without a live DOM/JS engine (no
    # headless browser exists in this project's toolchain - see
    # RESEARCH.md's Validation Architecture section). ---------------------

    def _panel_lookup_never_sets_image_src_to_empty_string():
        stripped = _strip_js_comments(_read_panel_lookup_source())
        if 'image.src = ""' in stripped:
            return False, (
                'expected zero occurrences of image.src = "" in panel-lookup.js\'s '
                "comment-stripped source (D-02/RESEARCH.md Pitfall 1)")
        return True, ""
    check(
        "panel-lookup.js never sets image.src to the empty string anywhere in its "
        "comment-stripped source - D-02/RESEARCH.md Pitfall 1's single riskiest line, "
        "the exact cross-browser spurious-request bug this phase's imageless-open branch exists "
        "to avoid",
        _panel_lookup_never_sets_image_src_to_empty_string)

    def _panel_lookup_remove_attribute_src_is_conditional():
        src = _read_panel_lookup_source()
        needle = 'image.removeAttribute("src")'
        if needle not in src:
            return False, "expected %r to appear at least once" % needle
        line = next(line for line in src.splitlines() if needle in line)
        indent = len(line) - len(line.lstrip(" "))
        # Every bare top-level statement inside the IIFE (a var
        # declaration, a function definition) sits at 2-space indent;
        # anything nested one level deeper than that (inside an
        # if/else/for) sits at 4+ spaces - this must be nested, never a
        # bare, unconditional module-scope statement.
        if indent <= 2:
            return False, (
                "expected image.removeAttribute(\"src\") indented inside a conditional branch, "
                "not written unconditionally at module scope (indent was %d)" % indent)
        return True, ""
    check(
        "panel-lookup.js's image.removeAttribute(\"src\") call is nested inside a conditional "
        "branch (the src-absent case), never written unconditionally at module scope",
        _panel_lookup_remove_attribute_src_is_conditional)

    def _panel_lookup_shared_populate_function_two_call_sites():
        src = _read_panel_lookup_source()
        def_needle = "function openFromTrigger(trigger)"
        def_count = src.count(def_needle)
        if def_count != 1:
            return False, "expected exactly one openFromTrigger definition, got %d" % def_count
        total_mentions = src.count("openFromTrigger(")
        call_sites = total_mentions - def_count
        if call_sites < 2:
            return False, (
                "expected openFromTrigger referenced (called) from at least two sites, found %d"
                % call_sites)
        return True, ""
    check(
        "panel-lookup.js's shared populate-and-open function (openFromTrigger) is defined exactly "
        "once and referenced from at least two call sites - the click listener and the load-time "
        "auto-open (RESEARCH.md Pitfall 2's mandatory factoring)",
        _panel_lookup_shared_populate_function_two_call_sites)

    def _panel_lookup_location_search_read_once_outside_click_only_function():
        src = _read_panel_lookup_source()
        stripped = _strip_js_comments(src)
        code_count = stripped.count("location.search")
        if code_count != 1:
            return False, (
                "expected location.search to be read exactly once in panel-lookup.js's own code "
                "(comments excluded), got %d" % code_count)
        # openFromTrigger is the one function reachable from a click;
        # location.search's single read must sit outside its body,
        # after the click listener that calls it is already wired
        # (RESEARCH.md Pitfall 2, D-13/D-14).
        func_start = src.index("function openFromTrigger(trigger)")
        func_end = src.index("\n  }\n", func_start)
        search_idx = src.index("location.search")
        click_listener_idx = src.index('document.addEventListener("click"')
        if func_start < search_idx < func_end:
            return False, "expected location.search's one read outside openFromTrigger's own body"
        if search_idx < click_listener_idx:
            return False, "expected location.search's one read positioned after the click listener is wired"
        return True, ""
    check(
        "panel-lookup.js reads location.search exactly once in its own code, at script init, "
        "outside openFromTrigger (the one function reachable from a click) and after the click "
        "listener is already wired",
        _panel_lookup_location_search_read_once_outside_click_only_function)

    def _panel_lookup_eleven_new_attrs_present_in_source():
        src = _read_panel_lookup_source()
        missing = [name for name in _NEW_VIEW_PANEL_ATTR_NAMES if name not in src]
        if missing:
            return False, (
                "expected every one of the eleven new data-view-panel-* attribute name literals "
                "in panel-lookup.js's source, missing: %r" % missing)
        return True, ""
    check(
        "every one of the eleven new data-view-panel-* attribute name literals 14-02 added to the "
        "vocabulary appears at least once in panel-lookup.js's own source",
        _panel_lookup_eleven_new_attrs_present_in_source)

    def _panel_lookup_mode_hidden_toggles_before_showmodal():
        src = _read_panel_lookup_source()
        func_start = src.index("function openFromTrigger(trigger)")
        show_modal_idx = src.index("dialog.showModal();", func_start)
        func_body = src[func_start:show_modal_idx]
        needles = (
            'resolveNameForm.hidden = (mode !== "gap")',
            'resolveUploadZone.hidden = (mode !== "needs-artwork")',
            'replaceForm.hidden = (mode !== "art")',
        )
        for needle in needles:
            if needle not in func_body:
                return False, (
                    "expected %r to occur, textually, before openFromTrigger's own "
                    "dialog.showModal() call" % needle)
        return True, ""
    check(
        "the mode-governed elements' (resolveNameForm/resolveUploadZone/replaceForm) hidden "
        "assignments all occur, textually, before openFromTrigger's own dialog.showModal() call "
        "(RESEARCH.md Pitfall 3 - showModal()'s one-time autofocus placement must see the final, "
        "already-toggled subtree)",
        _panel_lookup_mode_hidden_toggles_before_showmodal)

    def _panel_lookup_prevent_default_once_correctly_positioned():
        src = _read_panel_lookup_source()
        click_idx = src.index('document.addEventListener("click"')
        # 25-07-PLAN.md Task 2 (CFG-51/D19) retargets this check IN
        # PLACE — no EXPECTED_CHECK_COUNT change, because it is the same
        # claim measured better. D-12's clause has always been about the
        # CLICK path: exactly one interception, positioned between the
        # trigger-null-check and the one showModal()-reaching call. A
        # bare whole-file count was only ever a proxy for that, and the
        # drop zone adds two more preventDefault() calls with reasons of
        # their own — without one on `dragover` an element is not a drop
        # target at all, and without one on `drop` the browser navigates
        # away from the page to the dropped file. Both are now asserted
        # BY LOCATION, so a fourth appearing anywhere still fails, and
        # the click path's own count is scoped rather than inferred.
        if src.count("evt.preventDefault()") != 3:
            return False, (
                "expected evt.preventDefault() exactly three times (the click interception, plus "
                "the dragover/drop pair that makes an element a drop target and stops the browser "
                "navigating to the dropped file), got %d" % src.count("evt.preventDefault()"))
        drop_block = src[src.index("function wireUploadDropZone("):click_idx]
        if drop_block.count("evt.preventDefault()") != 2:
            return False, (
                "expected exactly two evt.preventDefault() calls inside wireUploadDropZone(), got "
                "%d" % drop_block.count("evt.preventDefault()"))
        for handler in ('zone.addEventListener("dragover"', 'zone.addEventListener("drop"'):
            handler_idx = drop_block.index(handler)
            if "evt.preventDefault()" not in drop_block[handler_idx:drop_block.index("});", handler_idx)]:
                return False, (
                    "expected an evt.preventDefault() inside %s's own handler — without it that "
                    "half of the gesture does not work at all" % (handler,))
        if src[click_idx:].count("evt.preventDefault()") != 1:
            return False, (
                "expected exactly one evt.preventDefault() at or after the click listener, got %d"
                % src[click_idx:].count("evt.preventDefault()"))
        null_check_idx = src.index("if (!trigger) {", click_idx)
        prevent_idx = src.index("evt.preventDefault()", click_idx)
        open_call_idx = src.index("openFromTrigger(trigger)", click_idx)
        if not (click_idx < null_check_idx < prevent_idx < open_call_idx):
            return False, (
                "expected evt.preventDefault() positioned after the trigger-null-check and before "
                "openFromTrigger() (the one showModal()-reaching call) inside the click listener")
        return True, ""
    check(
        "panel-lookup.js's evt.preventDefault() appears exactly once, inside the click listener, "
        "positioned after the trigger-null-check and before the showModal()-reaching "
        "openFromTrigger() call (D-12's <a> interception)",
        _panel_lookup_prevent_default_once_correctly_positioned)

    def _panel_lookup_single_dialog_lookup_single_click_listener():
        src = _read_panel_lookup_source()
        dialog_count = src.count('document.getElementById("panel-lookup-dialog")')
        click_count = src.count('document.addEventListener("click"')
        if dialog_count != 1:
            return False, (
                'expected exactly one document.getElementById("panel-lookup-dialog"), got %d'
                % dialog_count)
        if click_count != 1:
            return False, (
                'expected exactly one document.addEventListener("click", ...), got %d' % click_count)
        return True, ""
    check(
        "panel-lookup.js still contains exactly one document.getElementById(\"panel-lookup-dialog\") "
        "and exactly one document.addEventListener(\"click\", ...) - this plan extended the existing "
        "single mechanism rather than adding a second one (D-03's own rejected alternative)",
        _panel_lookup_single_dialog_lookup_single_click_listener)

    def _panel_lookup_context_callsign_write_gated_on_count():
        # Quick task 260921-n2n Task 2: for an ordinary art card,
        # `captionText` is the illustration's own caption, not a callsign
        # at all — an ungated write here printed the picture's title
        # under the "Example callsign" label on every ordinary picture.
        # Pin two things without a live DOM: exactly one
        # contextCallsign.textContent assignment survives in the file
        # (no second, ungated write reappears alongside the gated one),
        # and that one assignment is gated on the SAME `count` that
        # gates resolveContext.hidden, never a second independent
        # condition.
        src = _read_panel_lookup_source()
        n = src.count("contextCallsign.textContent")
        if n != 1:
            return False, (
                "expected exactly one contextCallsign.textContent assignment in panel-lookup.js, "
                "got %d — an ungated second write would print an illustration's own caption under "
                "the 'Example callsign' label again" % n)
        if 'contextCallsign.textContent = count ? captionText : "";' not in src:
            return False, (
                "expected contextCallsign.textContent's one assignment to be gated on the same "
                "`count` that gates resolveContext.hidden — an ungated assignment prints the "
                "picture's own caption under the 'Example callsign' label on every ordinary "
                "illustration")
        return True, ""
    check(
        "panel-lookup.js's contextCallsign.textContent is assigned exactly once, gated on the same "
        "`count` that gates resolveContext.hidden, so an ordinary illustration's own caption can "
        "never be printed under the 'Example callsign' label (quick task 260921-n2n Task 2)",
        _panel_lookup_context_callsign_write_gated_on_count)

    def _airlines_lightbox_constants_match_history():
        # quick task 260902-tli: the dialog id and the three
        # data-view-panel-* attribute names are duplicated, not imported
        # (a page module has no import path to a sibling page module),
        # into airlines_page.py from history_page.py's own values -
        # pinned here so a drift fails loudly instead of leaving the
        # Airlines trigger silently inert.
        pairs = (
            ("LIGHTBOX_DIALOG_ID", airlines_page.LIGHTBOX_DIALOG_ID, history_page.LIGHTBOX_DIALOG_ID),
            ("_VIEW_PANEL_SRC_ATTR", airlines_page._VIEW_PANEL_SRC_ATTR, history_page._VIEW_PANEL_SRC_ATTR),
            ("_VIEW_PANEL_CAPTION_ATTR", airlines_page._VIEW_PANEL_CAPTION_ATTR,
                history_page._VIEW_PANEL_CAPTION_ATTR),
            ("_VIEW_PANEL_CLOSE_ATTR", airlines_page._VIEW_PANEL_CLOSE_ATTR, history_page._VIEW_PANEL_CLOSE_ATTR),
        )
        for name, airlines_value, history_value in pairs:
            if airlines_value != history_value:
                return False, (
                    "expected airlines_page.%s (%r) to equal history_page.%s (%r)"
                    % (name, airlines_value, name, history_value))
        return True, ""
    check(
        "airlines_page's LIGHTBOX_DIALOG_ID and its three _VIEW_PANEL_*_ATTR constants each equal "
        "history_page's own values (the duplicated-not-imported shared-lightbox contract)",
        _airlines_lightbox_constants_match_history)

    def _history_lightbox_carries_zero_replace_markup():
        # new (quick task 260903-btu): actually exercises history_page.
        # render() against a seeded fixture — a real gallery entry and a
        # real runway event, mirroring _lightbox_dom_contract_three_file_
        # guard()'s own fixture shape — since History only emits its
        # dialog when at least one row carries a trigger; a fixture with
        # no entries would prove absence for the wrong reason.
        tmp = _mkstate("h-no-replace-markup")
        try:
            names = ["2026-08-27T10-05-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:06:00+00:00", "hex": "dc02", "callsign": "NOREPLACE"},
            ])
            rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        dialog_count = rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID)
        if dialog_count != 1:
            return False, "expected the History dialog exactly once (proves the absence checks below mean something), got %d" % dialog_count
        for token, label in (
                (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS"),
                (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR"),
                ("<form", "<form"),
                ('<input type="file"', '<input type="file"'),
                ("enctype", "enctype"),
                # quick task 260903-df3: the framed zone's three new
                # class constants extend this non-regression guard too —
                # History must carry none of this task's new markup any
                # more than it carried the old inline-row markup.
                (airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS, "airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS"),
                (airlines_page.REPLACE_HINT_CLASS, "airlines_page.REPLACE_HINT_CLASS"),
                (airlines_page.REPLACE_ICON_CLASS, "airlines_page.REPLACE_ICON_CLASS")):
            count = rendered.count(token)
            if count != 0:
                return False, "expected zero occurrences of %s in a real, seeded history_page.render() output, got %d" % (label, count)
        return True, ""
    check(
        "a real, seeded history_page.render() call (real gallery entry, real runway event) renders its "
        "lightbox dialog exactly once, and carries zero occurrences of airlines_page's replace-form class, "
        "replace-action attribute, <form>, file input, enctype, or the framed zone's three class constants "
        "(quick task 260903-df3) anywhere (quick task 260903-btu)",
        _history_lightbox_carries_zero_replace_markup)

    def _replace_lightbox_names_appear_in_three_files_never_in_history():
        # new (quick task 260903-btu): the three-file contract for the
        # two new names, mirroring _lightbox_dom_contract_three_file_
        # guard()'s style — each token must appear in panel-lookup.js's
        # source and in a real airlines_page.render({}) call, and must
        # never appear in a real, seeded history_page.render() call.
        # These two constants deliberately have no history_page
        # counterpart and must never be added to
        # _airlines_lightbox_constants_match_history()'s pairs tuple.
        js_path = os.path.join(HERE, "static", "panel-lookup.js")
        with open(js_path) as fh:
            js_source = fh.read()
        style_css_path = os.path.join(HERE, "static", "style.css")
        with open(style_css_path) as fh:
            style_css_source = fh.read()

        # 29-01-PLAN.md (CFG-81): LIGHTBOX_REPLACE_FORM_CLASS is
        # unconditional now (see the DOM-contract guard's own identical
        # retarget above) - a plain default render already carries it.
        airlines_rendered = airlines_page.render({})
        tmp = _mkstate("h-replace-tokens-absent")
        try:
            names = ["2026-08-27T10-07-00+00-00.png"]
            _seed_gallery(tmp, names)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:08:00+00:00", "hex": "dc03", "callsign": "TOKENGONE"},
            ])
            history_rendered = history_page.render(_history_ctx(tmp, gallery_entries=names))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        for token in (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, airlines_page.LIGHTBOX_REPLACE_FORM_CLASS):
            if token not in js_source:
                return False, "expected %r in companion/static/panel-lookup.js" % (token,)
            if token not in airlines_rendered:
                return False, "expected %r in a real airlines_page.render({}) call" % (token,)
            if token in history_rendered:
                return False, "expected %r to never appear in a real, seeded history_page.render() call" % (token,)
        # quick task 260903-df3: a bare substring test here is no longer
        # sufficient — LIGHTBOX_REPLACE_FORM_CLASS ("lightbox__replace")
        # is now also a prefix of LIGHTBOX_REPLACE_ZONE_CLASS's own
        # selector ("lightbox__replace-zone"), so the bare substring
        # would keep passing even if the `.lightbox__replace { ... }`
        # rule itself were deleted from the stylesheet (the zone
        # selector alone would satisfy it). Require the exact selector,
        # built from the constant rather than hard-coding the literal.
        #
        # Phase 14 (14-03-PLAN.md Task 2) retargeted this pattern IN
        # PLACE (no count change to EXPECTED_CHECK_COUNT — same check,
        # re-scoped): .lightbox__replace's own selector is now the head
        # of a three-way group (`.lightbox__replace,\n.lightbox__resolve-
        # name,\n.lightbox__delete {`), so the class name is followed by
        # a comma, not always " {". A lookahead for whitespace/comma/
        # brace immediately after the class name (excluding the
        # "-zone" hyphen continuation) still proves the exact selector
        # exists as its own token, in either the old standalone form or
        # the new grouped form.
        #
        # 14-08 on-glass fix (2026-09-06) retargeted this pattern IN
        # PLACE a second time: a real-browser check found `display:
        # block` on this group winning a specificity tie against the UA
        # stylesheet's `[hidden] { display: none }`, so every selector
        # in the group now carries `:not([hidden])` immediately after
        # the class name — a colon, not whitespace/comma/brace. Added
        # `:` to the lookahead so the exact-selector proof still holds
        # for the scoped form.
        exact_selector_pattern = re.compile(
            r'\.' + re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS) + r'(?=[\s,{:])')
        if not exact_selector_pattern.search(style_css_source):
            return False, (
                "expected a '.%s' selector (not merely a '-zone' prefix match) in "
                "companion/static/style.css — the fourth file in the chain, and the one whose drift would "
                "leave the form functional but unstyled" % (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,))
        return True, ""
    check(
        "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR and airlines_page.LIGHTBOX_REPLACE_FORM_CLASS each "
        "appear in companion/static/panel-lookup.js's source and in a real airlines_page.render({}) call, "
        "the exact '.lightbox__replace' selector (not merely a substring, which the newer "
        "'.lightbox__replace-zone' selector could otherwise satisfy) appears in companion/static/style.css "
        "standalone or as the head of the phase-14 three-way group, and neither token appears in a real, "
        "seeded history_page.render() call (quick task 260903-btu; these two constants have no history_page "
        "counterpart by design and must never join _airlines_lightbox_constants_match_history()'s pairs "
        "tuple; pattern retargeted in place by phase 14 plan 14-03 Task 2)",
        _replace_lightbox_names_appear_in_three_files_never_in_history)

    def _airlines_render_empty_ctx_still_contains_gallery_grid():
        # quick task 260902-v26 threaded an optional state_dir read
        # through render(ctx) via ctx.get("state_dir") - this pins that
        # render({}) with a literal empty dict (exactly what
        # _lightbox_dom_contract_three_file_guard() above already calls)
        # still succeeds and its output still contains the gallery grid,
        # not just that it doesn't raise.
        rendered = airlines_page.render({})
        if "illustration-grid" not in rendered:
            return False, "expected render({}) to still contain the .illustration-grid gallery container"
        return True, ""
    check(
        "airlines_page.render({}) with a literal empty dict still succeeds and its output still contains the "
        "gallery grid (quick task 260902-v26's ctx.get(\"state_dir\") tolerance)",
        _airlines_render_empty_ctx_still_contains_gallery_grid)

    # ======================================================================
    # 19-08-PLAN.md Task 1 (D-21/A-38): the "Unidentified airlines" gap
    # strip - its own explained home for the coverage-gap cards, moved
    # off the head of the curated artwork grid.
    #
    # 29-02-PLAN.md (CFG-82) SUPERSEDES this section's own check in
    # place: D-21 put the strip BEFORE the filter bar (first thing on
    # the page); CFG-82 moves it AFTER the filter bar and the gallery
    # grid instead, so a household member reaches the page's main
    # content before a diagnostic list. The check below is retargeted
    # to the new order, not retired - the "no gap card ever leaks into
    # the curated grid" property it proves is unchanged by the reorder.
    # ======================================================================

    def _airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder():
        tmp = _mkstate("a-gap-strip")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 3, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            rendered = airlines_page.render({"state_dir": tmp})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if airlines_page.GAP_STRIP_HEADING not in rendered:
            return False, "expected the gap strip's heading in a render with an eligible gap"
        if airlines_page.GAP_STRIP_BODY not in rendered:
            return False, "expected the gap strip's exact sentence in a render with an eligible gap"
        try:
            strip_index = rendered.index(airlines_page.GAP_STRIP_HEADING)
            filter_bar_index = rendered.index('class="filter-bar')
            gallery_index = rendered.index('class="illustration-grid"')
        except ValueError as exc:
            return False, (
                "expected the gap strip heading, the filter bar and the gallery grid all present: %s"
                % (exc,))
        if strip_index <= filter_bar_index:
            return False, "expected the gap strip to render after the filter bar (CFG-82, 29-02-PLAN.md)"
        if strip_index <= gallery_index:
            return False, "expected the gap strip to render after the gallery grid (CFG-82, 29-02-PLAN.md)"
        # The curated artwork grid never holds a gap card: every gap
        # card carries .airline-card__placeholder, and no curated card
        # ever does, so zero occurrences BEFORE the gap strip's own
        # index (i.e. inside the filter bar and the gallery grid, which
        # now render entirely before it) proves the grid holds none.
        if "airline-card__placeholder" in rendered[:strip_index]:
            return False, "expected the curated artwork grid to hold no gap card placeholder"
        return True, ""
    check(
        "a render with an eligible gap emits the \"Unidentified airlines\" strip with its exact heading and "
        "sentence after the filter bar and the gallery grid, and the curated artwork grid holds no gap card "
        "(D-21/A-38, 19-08-PLAN.md Task 1, order superseded by CFG-82, 29-02-PLAN.md)",
        _airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder)

    def _airlines_gap_strip_absent_with_no_gaps():
        tmp = _mkstate("a-no-gap-strip")
        try:
            rendered = airlines_page.render({"state_dir": tmp})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if airlines_page.GAP_STRIP_HEADING in rendered:
            return False, "expected no gap strip heading when there are no eligible gaps"
        if "<section class=\"page-section\">" in rendered:
            return False, "expected no empty gap-strip <section> at all when there are no eligible gaps"
        return True, ""
    check(
        "a render with no eligible gaps emits no \"Unidentified airlines\" strip and no empty section "
        "(D-21, 19-08-PLAN.md Task 1)",
        _airlines_gap_strip_absent_with_no_gaps)

    # ======================================================================
    # 29-02-PLAN.md (CFG-82): the page's whole section order, asserted as
    # a chain of relationships (never a literal offset) - the filter bar
    # and the known-airline gallery are the first two things under the
    # title, and the unidentified-prefix strip is a secondary section
    # below the gallery.
    # ======================================================================

    def _airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox():
        tmp = _mkstate("a-section-order")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 3, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            # illustrations.target_variants_by_airline() is the real
            # curated in-repo catalog and is never empty in this app, so
            # every gallery card term is non-empty here with no
            # monkeypatch needed - the same "never empty" premise
            # render()'s own comments state.
            rendered = airlines_page.render({"state_dir": tmp})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        literals = (
            ("title", '<h1 class="page-title"'),
            ("filter", 'class="filter-bar"'),
            ("gallery", 'class="illustration-grid"'),
            ("gapstrip", airlines_page.GAP_STRIP_HEADING),
            ("lightbox", '<dialog class="lightbox'),
        )
        indices = {}
        for name, literal in literals:
            occurrences = rendered.count(literal)
            if occurrences != 1:
                return False, (
                    "expected exactly one occurrence of %r (the %s section), found %d"
                    % (literal, name, occurrences))
            indices[name] = rendered.index(literal)

        order = ["title", "filter", "gallery", "gapstrip", "lightbox"]
        for earlier, later in zip(order, order[1:]):
            if not indices[earlier] < indices[later]:
                return False, (
                    "expected %s before %s, but got indices title=%d filter=%d gallery=%d "
                    "gapstrip=%d lightbox=%d (CFG-82, 29-02-PLAN.md)"
                    % (earlier, later, indices["title"], indices["filter"], indices["gallery"],
                       indices["gapstrip"], indices["lightbox"]))
        return True, ""
    check(
        "on a render with both an eligible gap and at least one curated gallery card, the page's own "
        "sections chain title < filter bar < gallery grid < \"Unidentified airlines\" strip < the lightbox "
        "dialog, each literal occurring exactly once (CFG-82, 29-02-PLAN.md)",
        _airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox)

    def _airlines_no_chrome_gate_survives_the_reorder():
        original_target_variants_by_airline = illustrations.target_variants_by_airline
        # Fixture A: gap cards present, the gallery's own curated pairs
        # empty - monkeypatched, since the real catalog is never empty
        # (render()'s own comment). The no-chrome gate is
        # `pairs or gap_shown`, so this fixture must still show chrome.
        tmp_a = _mkstate("a-no-chrome-gap-only")
        try:
            _seed_unresolved_prefixes(tmp_a, {
                "XYZ": {
                    "count": 3, "first_seen": "t1", "last_seen": "t2",
                    "example_callsign": "XYZ123",
                },
            })
            illustrations.target_variants_by_airline = lambda: []
            rendered_gap_only = airlines_page.render({"state_dir": tmp_a})
        finally:
            illustrations.target_variants_by_airline = original_target_variants_by_airline
            shutil.rmtree(tmp_a, ignore_errors=True)
        if 'class="filter-bar"' not in rendered_gap_only:
            return False, (
                "expected the filter bar to still render when there are gap cards but no curated pairs "
                "(the gate is `pairs or gap_shown`, CFG-82, 29-02-PLAN.md)")

        # Fixture B: neither gap cards nor curated pairs - the existing
        # no-chrome-with-no-data rule must still hold after the reorder.
        tmp_b = _mkstate("a-no-chrome-neither")
        try:
            illustrations.target_variants_by_airline = lambda: []
            rendered_neither = airlines_page.render({"state_dir": tmp_b})
        finally:
            illustrations.target_variants_by_airline = original_target_variants_by_airline
            shutil.rmtree(tmp_b, ignore_errors=True)
        if 'class="filter-bar"' in rendered_neither:
            return False, (
                "expected no filter bar at all when there is nothing to filter (the no-chrome-with-no-data "
                "gate, CFG-82, 29-02-PLAN.md)")
        return True, ""
    check(
        "the reorder does not touch render()'s own no-chrome gate: a render with gap cards but no curated "
        "pairs still shows the filter bar, and a render with neither shows no filter bar at all (CFG-82, "
        "29-02-PLAN.md)",
        _airlines_no_chrome_gate_survives_the_reorder)

    # ======================================================================
    # 19-08-PLAN.md Task 2 (D-21/A-38): the resolve panel's back link now
    # names and targets Airlines, not Health.
    # ======================================================================

    def _airlines_resolve_panel_back_link_names_and_targets_airlines():
        # No live gap, no manual entry for "XYZ": the stale/invalid
        # branch, one of the six _resolve_section_html() branches that
        # all share the same back_link, built once.
        tmp = _mkstate("a-resolve-back-link")
        try:
            rendered = airlines_page.render({"state_dir": tmp, "resolve_prefix": "XYZ"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        matches = re.findall(
            r'<a class="text-label" href="([^"]*)">%s</a>' % re.escape(airlines_page.RESOLVE_BACK_LINK_TEXT),
            rendered)
        if len(matches) != 1:
            return False, "expected exactly one resolve-panel back link, found %d" % (len(matches),)
        if matches[0] != airlines_page.AIRLINES_ROUTE:
            return False, "expected the back link's href to equal AIRLINES_ROUTE, got %r" % (matches[0],)
        return True, ""
    check(
        "the resolve panel's back link renders exactly once, named \"" +
        airlines_page.RESOLVE_BACK_LINK_TEXT.replace("\"", "'") +
        "\" and targeting airlines_page.AIRLINES_ROUTE, superseding the Phase 13 Copy Deck's "
        "\"Back to Health\" (D-21, A-38, 19-08-PLAN.md Task 2)",
        _airlines_resolve_panel_back_link_names_and_targets_airlines)

    # ======================================================================
    # 29-01-PLAN.md (CFG-81): the shared lightbox's replace, upload and
    # delete forms all render unconditionally now — the page-wide
    # editing mode that used to gate replace/delete behind an exact
    # ?edit=1 is deleted outright. panel-lookup.js decides which of
    # replace/delete is VISIBLE on a given open, from the clicked
    # trigger's own mode/manual data attributes.
    # ======================================================================

    def _airlines_default_render_always_has_the_dialogs_forms():
        rendered = airlines_page.render({})
        # Exact `class="{token}"` (with the closing quote), never a
        # bare substring - LIGHTBOX_REPLACE_FORM_CLASS
        # ("lightbox__replace") is itself a prefix of several sibling
        # classes (lightbox__replace-zone, lightbox__replace-icon,
        # lightbox__replace-hint) that also render unconditionally as
        # part of the upload zone's own markup.
        for token in (
                airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,
                airlines_page.LIGHTBOX_DELETE_CLASS,
                airlines_page.RESOLVE_UPLOAD_ZONE_CLASS):
            count = rendered.count('class="%s"' % token)
            if count != 1:
                return False, (
                    "expected exactly one %r in a default render (no page-wide editing mode "
                    "gates this dialog form any more, CFG-81), got %d" % (token, count))
        return True, ""
    check(
        "a default airlines_page.render({}) call (no query parameter involved) carries exactly "
        "one each of the dialog's replace form, delete form and upload zone — the page-wide "
        "editing mode that used to gate replace/delete behind an exact ?edit=1 is deleted "
        "(CFG-81, 29-01-PLAN.md)",
        _airlines_default_render_always_has_the_dialogs_forms)

    def _airlines_default_render_step_b_upload_zone_unconditional():
        # 21-06-PLAN.md Task 1 (D-19): a Step-B entry (name saved, no
        # artwork yet) offers the upload zone in the no-JS resolve
        # panel — naming an airline and giving it a picture is one job.
        # airlines_page.render() always emits both the fallback panel
        # and the lightbox when there is at least one card, so a Step-B
        # render carries TWO upload zones (one per surface).
        #
        # 29-01-PLAN.md (CFG-81): the shared delete form is unconditional
        # now too, and an entry exists at this point (Step B), so it
        # renders once from the no-JS fallback panel (a real,
        # server-computed action) and once from the dialog (an
        # `action=""` placeholder panel-lookup.js fills in per click) —
        # two, not zero. The dialog's replace form is unconditional as
        # well, but this no-JS fallback panel has no replace form of its
        # own, so that stays exactly one (the dialog's own copy).
        tmp = _mkstate("a-step-b-upload-default")
        try:
            result = manual_resolutions.add_entry(tmp, "NEW", "Totally Novel Airline")
            if result != manual_resolutions.ADD_OK:
                return False, "test setup failure: add_entry returned %r" % (result,)
            rendered = airlines_page.render({"state_dir": tmp, "resolve_prefix": "NEW"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        upload_count = rendered.count('class="%s"' % airlines_page.RESOLVE_UPLOAD_ZONE_CLASS)
        if upload_count != 2:
            return False, (
                "expected exactly two %r (fallback panel + lightbox) in a Step-B render, got %d"
                % (airlines_page.RESOLVE_UPLOAD_ZONE_CLASS, upload_count))
        # Exact `class="{token}"` (with the closing quote), never a bare
        # substring - LIGHTBOX_REPLACE_FORM_CLASS ("lightbox__replace")
        # is itself a prefix of several sibling classes
        # (lightbox__replace-zone, lightbox__replace-icon,
        # lightbox__replace-hint) that render unconditionally as part of
        # the upload zone's own markup.
        delete_count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_DELETE_CLASS)
        if delete_count != 2:
            return False, (
                "expected exactly two %r (fallback panel + lightbox) in a Step-B render, got %d"
                % (airlines_page.LIGHTBOX_DELETE_CLASS, delete_count))
        replace_count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
        if replace_count != 1:
            return False, (
                "expected exactly one %r (the dialog's own copy — this no-JS fallback panel has "
                "none of its own) in a Step-B render, got %d"
                % (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, replace_count))
        return True, ""
    check(
        "a render of a Step-B entry (name saved, no artwork yet) contains exactly two upload "
        "zones and two manual-delete forms (the no-JS fallback panel's own copy plus the "
        "lightbox's, both unconditional per CFG-81), and exactly one replace form (the "
        "dialog's own copy — this no-JS fallback panel has none of its own) (D-19, "
        "21-06-PLAN.md Task 1; retargeted by 29-01-PLAN.md)",
        _airlines_default_render_step_b_upload_zone_unconditional)

    def _airlines_default_render_keeps_exactly_one_resolve_name_form():
        rendered = airlines_page.render({})
        count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS)
        if count != 1:
            return False, (
                "expected exactly one %r form in a default render (the everyday naming path), "
                "got %d" % (airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS, count))
        return True, ""
    check(
        "a default airlines_page.render({}) call still contains exactly one "
        "lightbox__resolve-name form - naming a prefix stays the everyday action (D-22, "
        "19-08-PLAN.md Task 3)",
        _airlines_default_render_keeps_exactly_one_resolve_name_form)

    # 29-01-PLAN.md (CFG-81): the check that used to prove "exactly one
    # of each edit-only form under edit_mode=True" is retired — the
    # property is now _airlines_default_render_always_has_the_dialogs_
    # forms()'s own, above, since there is no longer a second render
    # state to distinguish.

    # ======================================================================
    # 29-01-PLAN.md (CFG-81): the "Change pictures"/"Done" toggle, its
    # editing badge and its explanatory caption are deleted outright —
    # the door that used to hide the dialog's own actions is gone, not
    # relocated. The checks that used to exercise it
    # (_airlines_default_render_has_one_change_pictures_toggle,
    # _airlines_edit_mode_render_shows_done_toggle_with_no_query,
    # _airlines_french_render_shows_translated_toggle_labels) are
    # retired; the one property worth keeping — that the toggle can
    # never come back by accident — is the new absence check below.
    # ======================================================================

    def _airlines_no_page_wide_editing_mode_survives():
        import companion.prefs as _prefs
        try:
            for lang in ("en", "fr"):
                _prefs.set_request_prefs(lang=lang)
                for rendered in (
                        airlines_page.render({}),
                        airlines_page.render({"resolve_prefix": "not-a-real-prefix"})):
                    if 'class="airlines-edit-toggle"' in rendered:
                        return False, (
                            "expected no airlines-edit-toggle anchor to ever render again "
                            "(lang=%r)" % (lang,))
                    if "?edit=" in rendered:
                        return False, (
                            "expected no ?edit= query literal to ever render again (lang=%r)"
                            % (lang,))
        finally:
            _prefs.set_request_prefs(lang="en")
        return True, ""
    check(
        "the deleted page-wide editing toggle (its class literal) and the deleted ?edit= query "
        "parameter (its literal form) never render again, in either language, whether the query "
        "string is absent or carries an arbitrary unrelated value (CFG-81, 29-01-PLAN.md)",
        _airlines_no_page_wide_editing_mode_survives)

    # ======================================================================
    # 20-10-PLAN.md Task 2 (D-05): the rest of Airlines through i18n.t(),
    # with companion/i18n_fr/airlines.py's own French catalogue.
    # ======================================================================

    def _airlines_french_render_translates_headings_not_data():
        import companion.prefs as _prefs
        try:
            _prefs.set_request_prefs(lang="fr")
            rendered = airlines_page.render({})
        finally:
            _prefs.set_request_prefs(lang="en")
        for needle in (
                ">Compagnies<", "Filtrer par compagnie ou indicatif",
                "Illustration de la compagnie"):
            if needle not in rendered:
                return False, "expected the French %r in a French Airlines render" % (needle,)
        if "Air France" not in rendered:
            return False, "expected the seeded/curated airline name 'Air France' to stay untranslated data"
        return True, ""
    check(
        "a French render of Airlines shows the French page title, filter label and lightbox "
        "aria-label, while a real airline name ('Air France') stays untranslated data (D-05, "
        "20-10-PLAN.md Task 2; the toggle-text needle retired by 29-01-PLAN.md/CFG-81)",
        _airlines_french_render_translates_headings_not_data)

    def _airlines_full_seeded_render_french_end_to_end():
        import companion.prefs as _prefs
        tmp = _mkstate("airlines-fr")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 5, "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-02T00:00:00+00:00", "example_callsign": "XYZ123",
                },
            })
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered_fr = airlines_page.render({"state_dir": tmp})
                resolve_fr = airlines_page.render(
                    {"state_dir": tmp, "resolve_prefix": "XYZ"})
            finally:
                _prefs.set_request_prefs(lang="en")
            for needle in (
                    ">Compagnies<", "Compagnies non identifiées",
                    "Le cadre a vu ces indicatifs mais ne connaît pas la compagnie"):
                if needle not in rendered_fr:
                    return False, "expected the French %r in the French Airlines render" % (needle,)
            for needle in (
                    "Identifier un vol non reconnu", "Nom de la compagnie",
                    "Enregistrer le nom de la compagnie"):
                if needle not in resolve_fr:
                    return False, "expected the French %r in the French resolve-panel render" % (needle,)
            if "XYZ123" not in rendered_fr and "XYZ123" not in resolve_fr:
                return False, "expected the seeded example callsign to stay untranslated data"

            rendered_en = airlines_page.render({"state_dir": tmp})
            for needle in (
                    '<h1 class="page-title">Airlines</h1>', airlines_page.GAP_STRIP_HEADING,
                    airlines_page.GAP_STRIP_BODY):
                if needle not in rendered_en:
                    return False, "expected the English %r in the default-language Airlines render" % (
                        needle,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-seeded Airlines render under lang='fr' shows the French gap-strip heading/sentence "
        "and resolve-panel copy with no English leaking in, the seeded example callsign stays "
        "untranslated data, and the identical seeded render under the default language still "
        "carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 2; the toggle-label "
        "needle retired by 29-01-PLAN.md/CFG-81)",
        _airlines_full_seeded_render_french_end_to_end)

    def _airlines_catalog_keys_all_present_in_merged_catalog():
        import companion.i18n_fr as i18n_fr
        import companion.i18n_fr.airlines as i18n_fr_airlines
        missing = [k for k in i18n_fr_airlines.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from the merged CATALOG: %r" % (missing,)
        return True, ""
    check(
        "every key in companion/i18n_fr/airlines.py's own CATALOG is also a key of the merged "
        "companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up "
        "(20-10-PLAN.md Task 2)",
        _airlines_catalog_keys_all_present_in_merged_catalog)

    # ======================================================================
    # 22-11-PLAN.md Task 1 (D-05, B5): the resolve dialog reads in Paris
    # local time, and its Save and Close sit on one action row.
    # ======================================================================

    # An ISO-8601 instant as the unresolved-prefix registry writes it
    # (server/plane/enrich.py's note_unresolved_prefix()) — the exact
    # shape B5 found leaking into the dialog.
    _ISO_INSTANT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

    def _resolve_dialog_seen_attributes_carry_formatted_paris_local_text():
        # B5: `data-view-panel-first-seen`/`-last-seen` used to carry the
        # raw registry ISO, which panel-lookup.js textContent-copies
        # straight into the dialog — so the dialog read
        # "2026-09-09T15:49:27+00:00" while the no-JS path beside it
        # already rendered the identical value as Paris local time. The
        # two are halves of one contract, so this asserts EQUALITY
        # between them, not merely that each looks plausible.
        tmp = _mkstate("a-seen-local")
        now = "2026-09-13T09:00:00+00:00"
        first_seen = "2026-09-09T15:49:27+00:00"
        last_seen = "2026-09-11T06:05:00+00:00"
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 7, "first_seen": first_seen, "last_seen": last_seen,
                    "example_callsign": "XYZ123",
                },
            })
            rendered = airlines_page.render({"state_dir": tmp, "now": now})
            fallback = airlines_page.render(
                {"state_dir": tmp, "now": now, "resolve_prefix": "XYZ"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        attrs = {}
        for name, attr in (("first", airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR),
                           ("last", airlines_page._VIEW_PANEL_LAST_SEEN_ATTR)):
            values = [v for v in re.findall(r'%s="([^"]*)"' % re.escape(attr), rendered) if v]
            if len(values) != 1:
                return False, (
                    "expected exactly one non-empty %s attribute for the one seeded gap, found %r"
                    % (attr, values))
            attrs[name] = html.unescape(values[0])

        # The no-JS path's rendered TEXT for the same row: the <dd>'s
        # content with concise_timestamp_html()'s own <span> wrapper
        # stripped, which is exactly what a browser paints there.
        texts = {}
        for name, dd_class in (("first", "resolve-context__first-seen"),
                               ("last", "resolve-context__last-seen")):
            bodies = [b for b in re.findall(
                r'<dd class="%s[^"]*"[^>]*>(.*?)</dd>' % dd_class, fallback, re.S) if b.strip()]
            if len(bodies) != 1:
                return False, (
                    "expected exactly one populated %s <dd> in the no-JS fallback, found %r"
                    % (dd_class, bodies))
            texts[name] = html.unescape(re.sub(r"<[^>]*>", "", bodies[0]))

        for name in ("first", "last"):
            if attrs[name] != texts[name]:
                return False, (
                    "expected the JS path's %s-seen attribute to equal the no-JS path's rendered "
                    "text byte for byte, got %r and %r" % (name, attrs[name], texts[name]))
            if _ISO_INSTANT_RE.search(attrs[name]):
                return False, (
                    "expected no raw ISO-8601 in the %s-seen attribute, got %r"
                    % (name, attrs[name]))
        # D-05's "Paris local time everywhere": 15:49 UTC is 17:49 in
        # Paris on that date, so an unconverted value would still read
        # "15:49" here and pass every shape check above.
        if "17:49" not in attrs["first"]:
            return False, (
                "expected the 15:49 UTC sighting to render as 17:49 Europe/Paris, got %r"
                % (attrs["first"],))
        # And nothing anywhere in either render carries the ISO shape —
        # the dialog's own static markup included.
        #
        # 23-03-PLAN.md Task 1 (D14/CFG-34): with ONE exemption, stated
        # rather than silently widened. layout.relative_time_html()'s
        # <time datetime="..." data-relative> element carries a
        # machine-readable instant in the attribute HTML defines for
        # exactly that purpose — never painted, never copied into the
        # dialog, and already converted onto Europe/Paris (so it is not
        # the raw registry string B5 found either way). This is the same
        # line test_status_pages.py already draws for the battery
        # chart's data-ts hit targets: "D-05 is about visible/tooltip
        # text, not every attribute". The exemption is written as an
        # EXACT-SHAPE substitution so that a change to the element
        # convention stops exempting anything and this check fails
        # loudly, and so the sweep still catches an ISO leak anywhere
        # else on the page, the attribute's own siblings included.
        for label, page in (("gallery", rendered), ("resolve fallback", fallback)):
            page = re.sub(
                r'<time datetime="[^"]*" data-relative>', "<time data-relative>", page)
            leaks = _ISO_INSTANT_RE.findall(page)
            if leaks:
                return False, (
                    "expected zero ISO-8601 timestamps in the %s render, found %r"
                    % (label, leaks))
        return True, ""
    check(
        "the resolve dialog's data-view-panel-first-seen/-last-seen carry FORMATTED Europe/Paris "
        "text byte-identical to the no-JS path's own rendered <dd> text for the same row (15:49 UTC "
        "reading 17:49), and neither render carries a single ISO-8601 timestamp anywhere (B5/D-05, "
        "22-11-PLAN.md Task 1)",
        _resolve_dialog_seen_attributes_carry_formatted_paris_local_text)

    def _panel_lookup_js_does_no_date_math_of_any_kind():
        # D-05's enforceability rests on this: the Paris-local rule is
        # kept in ONE place (layout.local_clock_text()) only for as long
        # as the client never formats a date itself. panel-lookup.js
        # copies server-rendered text verbatim; the moment it parses a
        # date, a second, untranslatable formatter exists.
        path = os.path.join(HERE, "static", "panel-lookup.js")
        with open(path) as fh:
            source = fh.read()
        forbidden = (
            "new Date(", "Date.now", "toISOString", "toLocaleDateString",
            "toLocaleTimeString", "toLocaleString", "getHours", "getMinutes",
            "getTime", "Intl.DateTimeFormat",
        )
        found = [token for token in forbidden if token in source]
        if found:
            return False, (
                "expected panel-lookup.js to do no date parsing or formatting, found %r" % (found,))
        # The positive half: it still writes the two values it is given,
        # straight into textContent, with no transformation between.
        for attr in (airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
                     airlines_page._VIEW_PANEL_LAST_SEEN_ATTR):
            if ('getAttribute("%s")' % attr) not in source:
                return False, "expected panel-lookup.js to read %s off the trigger" % (attr,)
        for var in ("firstSeen", "lastSeen"):
            if ("textContent = %s;" % var) not in source:
                return False, (
                    "expected panel-lookup.js to assign %s straight to textContent, unmodified"
                    % (var,))
        return True, ""
    check(
        "companion/static/panel-lookup.js contains no date-parsing or date-formatting API at all "
        "(new Date/Date.now/toISOString/toLocale*/getHours/getMinutes/getTime/Intl.DateTimeFormat) "
        "and assigns the first-seen/last-seen attribute values straight to textContent — the "
        "property that keeps D-05's Paris-local rule enforceable server-side (B5, 22-11-PLAN.md "
        "Task 1)",
        _panel_lookup_js_does_no_date_math_of_any_kind)

    def _resolve_dialog_save_and_close_share_one_action_row():
        # B5: Save sat inside .lightbox__resolve-name and Close was the
        # dialog's bare last child, so the two stacked as two block rows.
        rendered = airlines_page.render({})
        row = re.search(
            r'<div class="%s">(.*?)</div>' % re.escape(airlines_page.LIGHTBOX_ACTIONS_CLASS),
            rendered, re.S)
        if row is None:
            return False, "expected one .lightbox__actions row in the rendered dialog"
        if rendered.count('class="%s"' % airlines_page.LIGHTBOX_ACTIONS_CLASS) != 1:
            return False, "expected exactly one action row on the page"
        body = row.group(1)
        if airlines_page._VIEW_PANEL_CLOSE_ATTR not in body:
            return False, "expected the Close control inside the action row"
        dialog_form_id = airlines_page.MANUAL_RESOLVE_FORM_ID + "-dialog"
        if ('<button type="submit" form="%s">' % dialog_form_id) not in body:
            return False, (
                "expected the primary Save inside the same row, re-attached to its form by the "
                "native form= attribute")
        # Quiet Close FIRST (left), primary SECOND (right) — read from
        # source order, which is what the flex row lays out.
        close_at = body.index(airlines_page._VIEW_PANEL_CLOSE_ATTR)
        submit_at = body.index('type="submit"')
        if close_at > submit_at:
            return False, "expected the quiet Close to precede the primary in the action row"
        # The form it names actually exists, and no longer encloses a
        # submit of its own in the dialog copy.
        if ('id="%s"' % dialog_form_id) not in rendered:
            return False, "expected the dialog's resolve form to carry the id the button names"
        dialog_form = re.search(
            r'<form class="%s" id="%s".*?</form>'
            % (re.escape(airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS), re.escape(dialog_form_id)),
            rendered, re.S)
        if dialog_form is None:
            return False, "expected to locate the dialog's resolve form"
        if 'type="submit"' in dialog_form.group(0):
            return False, "expected the dialog form's own submit to have moved into the action row"

        # The no-JS floor: the fallback section's form keeps its submit
        # INSIDE itself and renders no action row at all.
        tmp = _mkstate("a-actions-nojs")
        try:
            _seed_unresolved_prefixes(tmp, {
                "XYZ": {
                    "count": 4, "first_seen": "2026-09-09T15:49:27+00:00",
                    "last_seen": "2026-09-11T06:05:00+00:00", "example_callsign": "XYZ123",
                },
            })
            fallback = airlines_page.render(
                {"state_dir": tmp, "now": "2026-09-13T09:00:00+00:00", "resolve_prefix": "XYZ"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        nojs_form = re.search(
            r'<form class="%s" id="%s" .*?</form>'
            % (re.escape(airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS),
               re.escape(airlines_page.MANUAL_RESOLVE_FORM_ID)),
            fallback, re.S)
        if nojs_form is None:
            return False, "expected the no-JS fallback's resolve form with its own unsuffixed id"
        if 'type="submit"' not in nojs_form.group(0):
            return False, (
                "expected the no-JS fallback's submit to stay inside its own form — the scriptless "
                "floor must not depend on a form= re-attachment")

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule = re.search(
            r"^\.%s\s*\{([^}]*)\}" % re.escape(airlines_page.LIGHTBOX_ACTIONS_CLASS),
            css, re.S | re.M)
        if rule is None:
            return False, "expected a .lightbox__actions rule block in style.css"
        for declaration in ("display: flex", "align-items: center",
                            "justify-content: space-between"):
            if declaration not in rule.group(1):
                return False, (
                    "expected the action row to declare %r so the pair shares one line, quiet left "
                    "and primary right" % declaration)
        # C4 as 22-UI-SPEC.md §4 states it: two SEPARATE objects on a
        # shared row are centre-aligned and keep their own registered
        # geometry — so this row must force no shared height.
        for forbidden in ("height", "min-height", "border-radius"):
            if forbidden in rule.group(1):
                return False, (
                    "expected the action row to declare no %r — these two controls read as "
                    "separate objects and keep their own registered geometry (C4)" % forbidden)
        # No new button family rides in on this row.
        if ".btn--" in re.sub(r"/\*.*?\*/", "", css, flags=re.S):
            return False, "expected no .btn-- family anywhere in style.css"
        return True, ""
    check(
        "the resolve dialog's Save and Close share ONE .lightbox__actions row — quiet Close first, "
        "primary Save second and re-attached to its form by the native form= attribute — while the "
        "no-JS fallback keeps its own submit inside its own form, and the row's rule declares "
        "flex/centre/space-between with no shared height (C4) and no .btn-- family (B5, "
        "22-11-PLAN.md Task 1)",
        _resolve_dialog_save_and_close_share_one_action_row)

    # ======================================================================
    # 22-11-PLAN.md Task 2 (X7): edit mode becomes visible, the toggle
    # stops shouting, and the manual count becomes a filter control.
    #
    # 29-01-PLAN.md (CFG-81) retires the first two checks below outright:
    # the toggle they exercised (and its caption, its badge, and the
    # per-card Replace control) are deleted, not merely restyled. The
    # `.airlines-edit-toggle` CSS rule block
    # `_airlines_edit_toggle_and_its_caption_render_in_normal_case()`
    # used to read out of style.css is deleted by Task 1, so that check
    # cannot be retargeted; its absence is proven instead by the new
    # `_airlines_no_page_wide_editing_mode_survives()` check above.
    # `_airlines_edit_mode_shows_a_badge_and_one_replace_control_per_card()`
    # is replaced below with an absence-plus-vocabulary check of the new
    # shape: no badge, no per-card control, but the zoom trigger itself
    # still carries every data-view-panel-* attribute this module
    # defines for it.
    # ======================================================================

    def _airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary():
        rendered = airlines_page.render({})

        if "banner__pill" in rendered:
            return False, "expected no Editing badge anywhere — the page-wide editing mode is gone"
        if "calendar-disconnect-btn" in rendered:
            return False, (
                "expected zero per-card Replace controls anywhere — the affordance moved into the "
                "dialog (CFG-81)")

        triggers = re.findall(r'<(?:button type="button"|a href="[^"]*") class="airline-card__zoom" .*?</(?:button|a)>',
                               rendered, re.S)
        if len(triggers) < 2:
            return False, "expected the curated grid to render triggers to count vocabulary against"

        # Never a hardcoded 15 (or 14): derive the trigger's own
        # vocabulary from the module's own constants. Every
        # `_VIEW_PANEL_*_ATTR` constant is a `data-view-panel-*`
        # attribute name; `_VIEW_PANEL_CLOSE_ATTR` alone is excluded
        # because it belongs to the dialog's own Close button, never to
        # a card trigger — panel_attrs (the trigger's own builder) never
        # references it, only `_lightbox_html()`'s Close button does.
        attr_names = {
            getattr(airlines_page, name) for name in dir(airlines_page)
            if re.match(r"^_VIEW_PANEL_[A-Z0-9_]*_ATTR$", name)
            and name != "_VIEW_PANEL_CLOSE_ATTR"
        }
        expected_count = len(attr_names)

        counts = set()
        for trigger in triggers:
            found = set(re.findall(r'(data-view-panel-[a-z-]+)=', trigger))
            if found != attr_names:
                return False, (
                    "expected every airline-card__zoom trigger to carry the same data-view-panel-* "
                    "attribute set %r, got %r" % (sorted(attr_names), sorted(found)))
            counts.add(len(found))
        if counts != {expected_count}:
            return False, (
                "expected every trigger to carry exactly %d data-view-panel-* attributes (the "
                "module's own _VIEW_PANEL_*_ATTR count, minus the Close-button-only one), got %r"
                % (expected_count, counts))
        return True, ""
    check(
        "a normal Airlines render carries no Editing badge and no per-card Replace control "
        "anywhere (both deleted outright, CFG-81) — while every airline-card__zoom trigger still "
        "carries the SAME full data-view-panel-* vocabulary, its size derived from the module's "
        "own _VIEW_PANEL_*_ATTR constants rather than a hardcoded number (29-01-PLAN.md)",
        _airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary)

    def _airlines_manual_count_is_a_filter_control_in_the_filter_bar():
        # X7: "1 manual resolutions" rendered as a 12px underlined bare
        # link between the filter bar and the grid — a filter control
        # drawn as body prose. D-06 rides here: the singular form.
        import companion.prefs as _prefs
        tmp = _mkstate("a-manual-chip")
        try:
            registry = {"QQQ": {"airline_name": "Air France",
                                "created_at": "2026-09-01T10:00:00+00:00"}}
            rendered = airlines_page.render({"state_dir": tmp, "manual_resolutions": registry})
            two = airlines_page.render({"state_dir": tmp, "manual_resolutions": dict(
                registry, RRR={"airline_name": "KLM",
                               "created_at": "2026-09-02T10:00:00+00:00"})})
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered_fr = airlines_page.render(
                    {"state_dir": tmp, "manual_resolutions": registry})
            finally:
                _prefs.set_request_prefs(lang="en")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        bar = re.search(r'<div class="filter-bar">(.*?)</div>\s*<div class="empty-state"',
                        rendered, re.S)
        if bar is None:
            return False, "expected to locate the rendered filter bar"
        if "data-filter-set=\"manual\"" not in bar.group(1):
            return False, (
                "expected the manual-resolution control INSIDE the filter bar, not as loose prose "
                "below it")
        if 'class="airline-card__chip manual-summary"' not in bar.group(1):
            return False, (
                "expected the control to reuse the card-chip label voice verbatim")
        if rendered.count('data-filter-set="manual"') != 1:
            return False, "expected exactly one manual-resolution filter control on the page"

        # The 12px bare underlined link is retired: .manual-summary no
        # longer restates [data-filter-clear]'s property list.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        if re.search(r"^\.manual-summary\s*\{", css, re.M):
            return False, (
                "expected the .manual-summary base rule block to be gone — the chip class now "
                "carries the whole treatment, and a surviving copy is a fork")
        if not re.search(r"^\.manual-summary:hover\s*\{", css, re.M):
            return False, "expected .manual-summary to survive as the hover-only additive rule"

        # D-06/B16: one entry reads "1 manual resolution", two read
        # "2 manual resolutions", in both languages.
        if "1 manual resolution<" not in rendered:
            return False, (
                "expected the singular form for exactly one manual resolution, got %r"
                % (re.findall(r'data-filter-set="manual">([^<]*)<', rendered),))
        if "2 manual resolutions<" not in two:
            return False, (
                "expected the plural form for two manual resolutions, got %r"
                % (re.findall(r'data-filter-set="manual">([^<]*)<', two),))
        if "1 résolution manuelle<" not in rendered_fr:
            return False, (
                "expected the French singular, got %r"
                % (re.findall(r'data-filter-set="manual">([^<]*)<', rendered_fr),))
        return True, ""
    check(
        "the manual-resolution count renders as a real filter control INSIDE the Airlines filter "
        "bar wearing .airline-card__chip's label voice — the 12px bare link and its copied "
        "[data-filter-clear] property list are retired, leaving only a hover-additive rule — and "
        "one entry reads '1 manual resolution' (FR '1 resolution manuelle') while two read "
        "'2 manual resolutions' (X7 + D-06/B16, 22-11-PLAN.md Task 2)",
        _airlines_manual_count_is_a_filter_control_in_the_filter_bar)

    def _airlines_grid_is_two_fixed_columns_below_960px():
        # The markup-side half of the browser harness's own measurement:
        # a FIXED two-column template below 960px, not a re-tuned
        # auto-fill floor (which is what collapsed to one column).
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        block = re.search(
            r"@media \(max-width: 959\.98px\) \{\s*\.illustration-grid \{([^}]*)\}", css, re.S)
        if block is None:
            return False, (
                "expected a sub-960px .illustration-grid rule giving the grid a fixed template")
        declaration = block.group(1)
        if "repeat(2, minmax(0, 1fr))" not in declaration:
            return False, (
                "expected exactly two columns with a zero minimum so a 450x132 frame can shrink "
                "into a 159px column, got %r" % (declaration,))
        if "auto-fill" in declaration or "auto-fit" in declaration:
            return False, (
                "expected a fixed template below 960px — an auto-fill floor is what collapsed to "
                "one column in a 342px content column")
        base = re.search(r"^\.illustration-grid \{([^}]*)\}", css, re.S | re.M)
        if base is None or "auto-fill" not in base.group(1):
            return False, (
                "expected the desktop auto-fill idiom to be left alone above 960px")
        return True, ""
    check(
        "below 960px .illustration-grid takes a FIXED repeat(2, minmax(0, 1fr)) template — two "
        "cards per row with a zero column minimum — while the desktop auto-fill idiom above 960px "
        "is left untouched (X7, 22-11-PLAN.md Task 2)",
        _airlines_grid_is_two_fixed_columns_below_960px)

    # ======================================================================
    # Section 1d: the unresolved-airline link. 06.6.4.1-05 Task 3 (D-21)
    # pointed it at Health's read-only Server & data anchor — two hops
    # from a flight to naming its airline. 22-09-PLAN.md Task 2 (X5)
    # retargets every check below onto the ONE-HOP link straight to the
    # Airlines resolve view for that row's own prefix.
    # ======================================================================

    def _unresolved_link_absent_for_resolved_airline():
        tmp = _mkstate("h-link-resolved")
        try:
            _seed_runway_events(tmp, [
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "lkr01", "callsign": "LINKRES",
                    "airline": "AFR", "origin": "LFPO", "destination": "LFPG",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a resolved-airline row"
            for label, block in (("desktop cell", tr_block), ("mobile card", li_block)):
                if "?resolve=" in block:
                    return False, (
                        "did not expect a resolve link in the %s for a resolved airline" % label)
                if "/health" in block:
                    return False, (
                        "did not expect the retired two-hop Health link in the %s" % label)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a formatted row with a resolved airline produces a Flight cell (desktop) and a phone "
        "card (mobile) carrying neither a one-hop resolve link nor the retired two-hop Health "
        "route (22-09-PLAN.md Task 2, X5)",
        _unresolved_link_absent_for_resolved_airline)

    def _unresolved_link_present_once_each_for_unresolved_airline():
        tmp = _mkstate("h-link-unresolved")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "lku01", "callsign": "LINKUNR"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for an unresolved-airline row"
            # ONE HOP: the link resolves straight to the Airlines
            # resolve view for THIS row's own prefix ("LINKUNR" -> LIN),
            # never to Health's read-only list.
            href_attr = 'href="%s"' % (history_page.RESOLVE_LINK_HREF_TEMPLATE % "LIN")
            for label, block in (("desktop cell", tr_block), ("mobile card", li_block)):
                if block.count(href_attr) != 1:
                    return False, (
                        "expected exactly one one-hop resolve link (%s) in the %s, found %d"
                        % (href_attr, label, block.count(href_attr)))
                if history_page.RESOLVE_LINK_TEXT not in block:
                    return False, "expected the resolve link's text in the %s" % label
                if "/health" in block:
                    return False, (
                        "expected the retired two-hop Health route to be gone from the %s"
                        % label)
            # The prefix the link names is the one the resolve view's own
            # boundary normaliser would accept for this callsign — not a
            # re-typed literal.
            if history_page.resolve_prefix_for_callsign("LINKUNR") != "LIN":
                return False, "expected the prefix to be derived from the callsign itself"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a formatted row whose airline is unresolved produces exactly one ONE-HOP resolve anchor "
        "in the desktop Flight cell and exactly one on the phone card, both naming the prefix "
        "derived from that row's own callsign (22-09-PLAN.md Task 2, X5)",
        _unresolved_link_present_once_each_for_unresolved_airline)

    def _unresolved_link_keyed_on_airline_not_route():
        tmp = _mkstate("h-link-route-only")
        try:
            _seed_runway_events(tmp, [
                # airline resolved, but no origin/destination -> route
                # unavailable while the airline itself is not.
                {
                    "ts": "2026-08-27T10:00:00+00:00", "hex": "lkro1", "callsign": "LINKROUTE",
                    "airline": "AFR",
                },
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a route-only-unresolved row"
            if panel_render.ROUTE_FALLBACK_TEXT not in tr_block:
                return False, "expected the Route cell to still render the fallback text"
            if "?resolve=" in tr_block:
                return False, "did not expect a resolve link when only the route is unresolved"
            if "?resolve=" in li_block:
                return False, "did not expect a resolve link on the phone card either"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a row whose route is unresolved but whose airline IS resolved produces no unresolved-"
        "airline link - the link is keyed on the airline label, not on the route label",
        _unresolved_link_keyed_on_airline_not_route)

    def _airline_fallback_distinct_from_route_fallback():
        # quick task 260902-w4t (UIR-05): a no-airline row must render
        # AIRLINE_FALLBACK_TEXT ("Airline unknown") in the Type+Airline
        # cell/Aircraft detail row and panel_render.ROUTE_FALLBACK_TEXT
        # ("Route unavailable") in the Route cell/detail row - two
        # distinct strings in two distinct columns, never the same
        # phrase borrowed twice. Also pins the new anchor class
        # (UNRESOLVED_LINK_CLASS) into both the rendered page and
        # style.css, matching _merged_cell_classes_agree_with_stylesheet's
        # own cross-file drift discipline.
        if history_page.AIRLINE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT:
            return False, "AIRLINE_FALLBACK_TEXT must not equal ROUTE_FALLBACK_TEXT"
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        if history_page.UNRESOLVED_LINK_CLASS.split()[-1] not in css:
            return False, (
                "expected UNRESOLVED_LINK_CLASS's spacing class to be styled in style.css")
        tmp = _mkstate("h-airline-fallback")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "af01", "callsign": "AIRFB1"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for a no-airline row"
            for label, block in (("desktop", tr_block), ("mobile", li_block)):
                if history_page.AIRLINE_FALLBACK_TEXT not in block:
                    return False, "expected AIRLINE_FALLBACK_TEXT in the %s row" % label
                if panel_render.ROUTE_FALLBACK_TEXT not in block:
                    return False, "expected ROUTE_FALLBACK_TEXT in the %s row" % label
                if block.count(panel_render.ROUTE_FALLBACK_TEXT) != 1:
                    return False, (
                        "expected ROUTE_FALLBACK_TEXT exactly once (Route column only) in "
                        "the %s row, found %d" % (label, block.count(panel_render.ROUTE_FALLBACK_TEXT)))
                if 'class="%s"' % history_page.UNRESOLVED_LINK_CLASS not in block:
                    return False, "expected the unresolved-link's class attribute in the %s row" % label
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct "
        "strings in two distinct columns, and the unresolved-link's spacing class is styled in "
        "style.css and present in the rendered anchor (quick task 260902-w4t, UIR-05)",
        _airline_fallback_distinct_from_route_fallback)

    def _hex_only_row_promotes_hex_to_primary():
        # quick task 260902-w4t (UIR-06): a callsign-less row must never
        # render a dead copy button on a blank primary value. When a hex
        # is present it is promoted to the primary slot on the MOBILE
        # card's primary line (D-16, unchanged), with a "no callsign"
        # secondary note carrying NO copy button of its own.
        #
        # 21-03-PLAN.md Task 1 (D-15): the desktop Flight cell no longer
        # shows the hex at all (it is not visible on the summary row any
        # more; it moves into the Task 2 detail row instead, a later
        # task in this same plan) - a callsign-less row's desktop
        # primary slot is simply empty, with zero copy buttons, never a
        # dead/blank-value affordance either way.
        tmp = _mkstate("h-hex-only")
        try:
            _seed_runway_events(tmp, [
                # Row 0 (newest, ts sorts DESC): hex only, no callsign.
                {"ts": "2026-08-27T10:02:00+00:00", "hex": "34560d"},
                # Row 1: neither callsign nor hex.
                {"ts": "2026-08-27T10:01:00+00:00"},
                # Row 2: callsign present, no hex - unaffected control.
                {"ts": "2026-08-27T10:00:00+00:00", "callsign": "CTRL01"},
            ])
            rendered = history_page.render(_history_ctx(tmp))

            # Row 0: hex-only, desktop - empty primary, zero copy buttons,
            # hex never visible.
            tr_block = _row_block(rendered, "tr", 0)
            li_block = _row_block(rendered, "li", 0)
            if tr_block is None or li_block is None:
                return False, "could not locate row block for the hex-only row"
            if "34560d" in tr_block:
                return False, "did not expect the hex value visible in the desktop summary row"
            if tr_block.count("data-copy-value") != 0:
                return False, (
                    "expected zero copy buttons in the hex-only desktop row, got %d"
                    % tr_block.count("data-copy-value"))

            # Row 0: hex-only, mobile primary line (never blank, D-16 unchanged).
            if '<span class="cell-primary mono">34560d</span>' not in li_block:
                return False, "expected the mobile card's primary line to carry the hex"
            if ('<span class="cell-secondary">%s</span>'
                    % history_page.NO_CALLSIGN_NOTE_TEXT) not in li_block:
                return False, "expected the mobile card's primary line to carry the no-callsign note"

            # Row 1: both falsy - no crash, zero copy buttons in the Flight cell.
            tr_block_1 = _row_block(rendered, "tr", 1)
            if tr_block_1 is None:
                return False, "could not locate row block for the both-falsy row"
            flight_td = re.search(r"<td>(.*?)</td>", tr_block_1, re.S)
            if flight_td is None:
                return False, "expected a <td> for the both-falsy row's When cell"
            if tr_block_1.count("data-copy-value") != 0:
                return False, "expected zero copy buttons in the both-falsy desktop row"

            # Row 2 (control): callsign-present branch is unaffected.
            tr_block_2 = _row_block(rendered, "tr", 2)
            if tr_block_2 is None or "CTRL01" not in tr_block_2:
                return False, "expected the control row's callsign to render unchanged"
            if history_page.NO_CALLSIGN_NOTE_TEXT in tr_block_2:
                return False, "did not expect the no-callsign note on a row with a callsign"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a callsign-less row's desktop Flight cell is empty with zero copy buttons and no "
        "visible hex (21-03-PLAN.md Task 1, D-15); the mobile card still promotes the hex to "
        "its primary slot with a no-copy-button 'no callsign' note (D-16); a callsign+hex row "
        "is unaffected; a row with neither renders without raising "
        "(quick task 260902-w4t, UIR-06)",
        _hex_only_row_promotes_hex_to_primary)

    def _resolve_link_template_matches_the_airlines_resolve_view():
        # 22-09-PLAN.md Task 2 (X5): the same cross-module discipline the
        # retired Health-anchor guard applied, retargeted — the one-hop
        # template must be built from the REAL airlines_page route and
        # query-parameter constants, never a re-typed literal, and the
        # prefix it interpolates must be one that view's own boundary
        # normaliser accepts.
        expected = "%s?%s=%%s" % (
            airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
        if history_page.RESOLVE_LINK_HREF_TEMPLATE != expected:
            return False, (
                "expected history_page.RESOLVE_LINK_HREF_TEMPLATE to equal %r, got %r"
                % (expected, history_page.RESOLVE_LINK_HREF_TEMPLATE))
        if hasattr(history_page, "UNRESOLVED_LINK_HREF"):
            return False, "expected the retired two-hop Health link constant to be gone"
        for callsign, expected_prefix in (
                ("AFR1234", "AFR"), ("tvf16vb ", "TVF"), ("ZZP9", "ZZP"),
                ("ZZP", None), ("", None), (None, None), ("12A345", None)):
            got = history_page.resolve_prefix_for_callsign(callsign)
            if got != expected_prefix:
                return False, (
                    "expected resolve_prefix_for_callsign(%r) -> %r, got %r"
                    % (callsign, expected_prefix, got))
        # The derived prefix is exactly what the resolve view's own
        # membership test normalises to — the two can never disagree.
        if manual_resolutions.normalise_prefix("AFR") != "AFR":
            return False, "expected the shared prefix normaliser to accept a derived prefix"
        return True, ""
    check(
        "history_page.RESOLVE_LINK_HREF_TEMPLATE is built from airlines_page.AIRLINES_ROUTE and "
        "RESOLVE_QUERY_PARAM (never a re-typed literal), the retired two-hop Health constant is "
        "gone, and resolve_prefix_for_callsign() derives a prefix only for a callsign the "
        "registry writer's own shape gate would accept (22-09-PLAN.md Task 2, X5/T-22-30)",
        _resolve_link_template_matches_the_airlines_resolve_view)

    # ======================================================================
    # Section 1e: 22-09-PLAN.md Task 2 — day separators, the picture
    # control's new home, the phone card's airline + artwork, and the raw
    # ISO behind the copy control (X5).
    # ======================================================================

    def _day_separators_group_rows_by_europe_paris_calendar_day():
        # Three events across three EUROPE/PARIS days, one of which
        # (22:30 UTC on the 27th = 00:30 Paris on the 28th) falls on a
        # DIFFERENT day in UTC than in Paris — so a UTC grouping would
        # emit two separators here and merge the first two rows, while
        # the Paris grouping this plan requires emits three.
        import companion.prefs as _prefs
        tmp = _mkstate("h-day-separators")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-26T10:00:00+00:00", "hex": "ds01", "callsign": "DAYONE"},
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "ds02", "callsign": "DAYTWO"},
                {"ts": "2026-08-27T22:30:00+00:00", "hex": "ds03", "callsign": "DAYTHREE"},
            ])
            now = "2026-08-28T09:00:00+00:00"
            rendered_en = history_page.render(_history_ctx(tmp, now=now))
            _prefs.set_request_prefs(lang="fr")
            try:
                rendered_fr = history_page.render(_history_ctx(tmp, now=now))
            finally:
                _prefs.set_request_prefs(lang="en")

            expected = {
                "en": ["Today", "Yesterday", "26 Aug"],
                "fr": ["Aujourd’hui", "Hier", "26 août"],
            }
            for lang, rendered in (("en", rendered_en), ("fr", rendered_fr)):
                rows = re.findall(
                    r'<tr class="flight-day-row"><th scope="colgroup" colspan="6"'
                    r' class="text-label">(.*?)</th></tr>', rendered)
                if rows != expected[lang]:
                    return False, (
                        "expected the %s separators to read %r (one per Europe/Paris day, "
                        "newest first), got %r" % (lang, expected[lang], rows))
                # Each separator opens its own group: the 22:30 UTC row
                # must sit under the FIRST separator, not with the 10:00
                # row, which is the whole UTC-vs-Paris distinction. Scoped
                # to the TABLE — the phone cards render before it and
                # carry the same callsigns.
                table = _table_markup(rendered)
                if table is None:
                    return False, "could not locate the rendered table (%s)" % lang
                first_sep = table.index('class="flight-day-row"')
                second_sep = table.index('class="flight-day-row"', first_sep + 1)
                if not (first_sep < table.index("DAYTHREE") < second_sep):
                    return False, (
                        "expected the 22:30 UTC row (00:30 Paris the next day) to sit under "
                        "its own separator (%s)" % lang)
                if table.index("DAYTWO") < second_sep:
                    return False, (
                        "expected the 10:00 UTC row to sit under the SECOND separator (%s)"
                        % lang)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Flights table carries exactly one day-separator row per EUROPE/PARIS "
        "calendar day present in the rows — Today / Yesterday / an absolute date, translated in "
        "both languages — and a row whose UTC day differs from its Paris day is grouped by the "
        "Paris one (22-09-PLAN.md Task 2, X5/D-05)",
        _day_separators_group_rows_by_europe_paris_calendar_day)

    def _day_label_is_the_paris_day_formatters_own_output_and_never_sticky():
        # The separator's absolute form must be the SAME day and the SAME
        # words layout.local_clock_text()'s own cross-day branch produces
        # for that timestamp — not a second date path, and never a
        # strftime call in this module.
        import companion.prefs as _prefs
        page_source = open(os.path.join(HERE, "pages", "history_page.py")).read()
        if "strftime" in page_source:
            return False, (
                "expected zero strftime calls in history_page.py — the day label is the Paris-day "
                "formatter's own output, not a licence to format a date here")
        raw_ts = "2026-08-26T10:00:00+00:00"
        parsed = layout.parse_iso(raw_ts)
        day = history_page.paris_day(raw_ts)
        if day is None:
            return False, "expected paris_day() to date a well-formed timestamp"
        for lang in ("en", "fr"):
            _prefs.set_request_prefs(lang=lang)
            try:
                label = history_page.day_label(day, None)
                formatter = layout.local_clock_text(
                    parsed, layout._FULL_TIMESTAMP_SENTINEL_NOW)
            finally:
                _prefs.set_request_prefs(lang="en")
            # local_clock_text()'s cross-day output is "D Mon HH:MM";
            # the separator is its day portion, exactly.
            if formatter.rsplit(" ", 1)[0] != label:
                return False, (
                    "expected the %s absolute day label (%r) to equal the day portion of "
                    "local_clock_text()'s own cross-day output (%r)" % (lang, label, formatter))
        # Degrade-not-raise (T-22-31).
        for bad in (None, "", "not-a-timestamp", 17):
            if history_page.paris_day(bad) is not None:
                return False, "expected paris_day(%r) to degrade to None" % (bad,)
        import companion.i18n as _i18n
        if history_page.day_label(day, day) != _i18n.t_lang("Today", "en"):
            return False, "expected a same-day group to read Today"

        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        rule = re.search(r"^\.flight-day-row th\s*\{([^}]*)\}", css, re.S | re.M)
        if rule is None:
            return False, "expected a .flight-day-row th rule block in style.css"
        if "position" in rule.group(1) or "sticky" in rule.group(1):
            return False, (
                "expected the day separator to declare no positioning at all — sticky day "
                "headers are D7/Phase 23, and T4 removes the app's one broken sticky claim "
                "rather than adding a second")
        return True, ""
    check(
        "the day separator's absolute label is the day portion of layout.local_clock_text()'s own "
        "cross-day output in both languages, history_page.py contains zero strftime calls, "
        "paris_day() degrades to None rather than raising, and the separator's CSS rule declares "
        "no positioning (22-09-PLAN.md Task 2, X5/D-05/T4)",
        _day_label_is_the_paris_day_formatters_own_output_and_never_sticky)

    # --- 23-08-PLAN.md Task 1 (D7/CFG-37): Flights joins the refresh
    # loop, and a genuinely new detection says so once -----------------

    def _every_flights_row_carries_a_stable_event_identity():
        # D7's highlight is a DIFF over row identity, so the identity is
        # the whole mechanism and the one thing a wrong implementation
        # gets wrong in a way nothing else notices: `flight-detail-%d`
        # and `data-filter-group` are both the row's POSITION in this
        # render, and a highlight keyed to a position lights up every
        # row below an insertion instead of the one that arrived.
        #
        # So this asserts the property a position does not have. The
        # same two events are rendered twice — once alone, once with a
        # NEWER third event prepended — and each surviving row must keep
        # the identity it had. An index-based attribute passes every
        # other clause here and fails this one.
        tmp = _mkstate("h-row-identity")
        try:
            older = [
                {"ts": "2026-08-27T09:00:00+00:00", "hex": "id01", "callsign": "IDONE"},
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "id02", "callsign": "IDTWO"},
            ]
            _seed_runway_events(tmp, older)
            before = history_page.render(_history_ctx(tmp))
            attr = layout.REFRESH_ROW_ID_ATTR

            def _ids(rendered, tag):
                return re.findall(
                    r"<%s[^>]*\s%s=\"([^\"]*)\"" % (tag, re.escape(attr)), rendered)

            tr_ids = _ids(before, "tr")
            li_ids = _ids(before, "li")
            # Two summary rows + two detail rows on the desktop side.
            if len(tr_ids) != 4:
                return False, (
                    "expected both the summary row and its sibling detail row to carry %r in "
                    "the desktop table (4 for 2 events), found %r" % (attr, tr_ids))
            if len(li_ids) != 2:
                return False, (
                    "expected every phone card to carry %r, found %r" % (attr, li_ids))
            if any(not value for value in tr_ids + li_ids):
                return False, "expected every identity attribute to be non-empty, got %r" % (
                    tr_ids + li_ids,)
            if sorted(set(tr_ids)) != sorted(set(li_ids)):
                return False, (
                    "expected the table and the card list to name the SAME events: table %r "
                    "against cards %r" % (sorted(set(tr_ids)), sorted(set(li_ids))))
            if len(set(li_ids)) != len(li_ids):
                return False, (
                    "expected two rows never to share one identity, found %r" % (li_ids,))

            # The property a position does not have.
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T11:00:00+00:00", "hex": "id03", "callsign": "IDTHREE"},
            ])
            after = history_page.render(_history_ctx(tmp))
            after_ids = _ids(after, "li")
            if len(after_ids) != 3:
                return False, "expected three phone cards after the insertion, got %r" % (
                    after_ids,)
            if after_ids[1:] != li_ids:
                return False, (
                    "expected a newer event arriving at the TOP to leave every existing row's "
                    "identity untouched — before %r, after %r. An identity that shifts with the "
                    "row's position is an index, and a highlight keyed to it would light up "
                    "every row below an insertion (D7/CFG-37)" % (li_ids, after_ids))
            if after_ids[0] in li_ids:
                return False, (
                    "expected the newly-arrived event to carry an identity no existing row "
                    "already had, got %r" % (after_ids[0],))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "every rendered Flights row carries a non-empty, unique event identity in BOTH "
        "representations, the table and the card list name the same event set, and a newer "
        "detection arriving at the top leaves every existing row's identity unchanged — the "
        "property the row's position does not have and the whole basis of the new-row highlight "
        "(D7/CFG-37, 23-08-PLAN.md Task 1)",
        _every_flights_row_carries_a_stable_event_identity)

    def _flights_declares_its_refresh_regions_and_never_the_filter_input():
        # The loop's two gates, measured on the page's own output: no
        # [data-loaded-at] marker means freshness.js returns at its first
        # guard, and a registry region that matches nothing is a list
        # entry that can never fire. The exclusion is the interesting
        # half — list-filter.js captures its input once at load, so a
        # swap that replaced it would leave the filter permanently dead
        # and discard an in-progress query.
        tmp = _mkstate("h-refresh-regions")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "rr01", "callsign": "REGION"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if rendered.count("data-loaded-at") != 1:
                return False, (
                    "expected exactly one data-loaded-at marker on Flights (no marker, no loop; "
                    "two markers, two claims about when this document was generated), found %d"
                    % rendered.count("data-loaded-at"))
            selectors = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_FLIGHTS]
            # Each region, reduced to a literal the rendered markup must
            # carry. Deliberately not a CSS engine: the point is that
            # every declared region names something this page actually
            # renders.
            witnesses = {
                ".page-header__freshness": 'class="page-header__freshness',
                "ul.history-cards": '<ul class="history-cards"',
                ".data-table-wrap": 'class="data-table-wrap"',
                "[data-filter-count]": "data-filter-count ",
                # 29-03-PLAN.md Task 1 (CFG-83): this fixture seeds
                # exactly one row, so _show_more_html(1, 1) renders the
                # EMPTY nav (shown >= total_available) — the witness
                # still matches, because the element itself is always
                # present (see that function's own comment for why).
                ".flights-more": 'class="flights-more"',
            }
            if sorted(witnesses) != sorted(selectors):
                return False, (
                    "Flights' registry entry is %r, and this check knows how to witness %r — a "
                    "region added to the registry must be witnessed in the rendered page here "
                    "too, or it is a list entry that can never fire"
                    % (sorted(selectors), sorted(witnesses)))
            for selector in selectors:
                if witnesses[selector] not in rendered:
                    return False, (
                        "registry region %r matches nothing in the rendered Flights page "
                        "(looked for %r)" % (selector, witnesses[selector]))
            for selector in selectors:
                if "data-filter-input" in selector:
                    return False, (
                        "the filter input is a swap target (%r) — list-filter.js captures it "
                        "once at load, so replacing it leaves the filter permanently dead and "
                        "silently discards an in-progress query" % (selector,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered Flights page carries exactly one data-loaded-at marker and a witness for "
        "every one of its REFRESH_SWAP_SELECTORS_BY_PAGE regions, and no region names the filter "
        "input list-filter.js captured at load (D7/CFG-37, 23-08-PLAN.md Task 1)",
        _flights_declares_its_refresh_regions_and_never_the_filter_input)

    # --- 23-08-PLAN.md Task 2 (D3/CFG-32's Flights clauses): the detail
    # row opens with height, the chevron turns, the card answers a tap
    # anywhere, and the count moves ---------------------------------------

    def _css_rule_body(css, selector):
        match = re.search(
            r"(?:^|\n)[ ]*%s\s*\{([^}]*)\}" % re.escape(selector), css)
        return match.group(1) if match else None

    def _detail_row_height_animates_and_a_closed_row_is_unreachable():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        js_path = os.path.join(HERE, "static", "flight-rows.js")
        with open(js_path) as fh:
            js = fh.read()

        # The mechanism, by name. `interpolate-size`/`calc-size()` are
        # Chromium-only — they would animate for some visitors and
        # silently do nothing for the rest — and 23-01's own guard bans
        # both; this is the Flights-side restatement, so a reader of THIS
        # rule sees why it is shaped the way it is.
        if "grid-template-rows: 0fr" not in css:
            return False, (
                "expected the detail row's height to animate from grid-template-rows: 0fr — "
                "the one mechanism 23-RESEARCH.md's Baseline table picks for this job")
        for banned in ("interpolate-size", "calc-size("):
            if banned in re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL):
                return False, (
                    "companion/static/style.css declares %r — Chromium-only, banned by 23-01's "
                    "own guard" % (banned,))

        # A <tr> is not a grid container, so the animation cannot live on
        # the row box: it belongs to a wrapper inside the <td>, and the
        # page must actually render that wrapper.
        tmp = _mkstate("h-detail-reveal")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "rv01", "callsign": "REVEAL"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            detail = _detail_row_block(rendered, 0)
            if detail is None:
                return False, "expected a server-rendered detail row"
            if "flight-detail-row__reveal" not in detail:
                return False, (
                    "expected the detail cell's content to sit inside the grid reveal wrapper — "
                    "a <tr> is not a grid container and `display` is discrete, so the animation "
                    "cannot live on the row box, got %r" % (detail[:200],))
            if detail.index("flight-detail-row__reveal") > detail.index(
                    "flight-detail-row__grid"):
                return False, (
                    "expected the reveal wrapper to WRAP the detail grid, not to follow it")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        # Scoped to the class flight-rows.js adds to <html> itself, and
        # that scoping is the no-JS floor rather than tidiness: with
        # scripts blocked every detail row is already open, and an
        # entry animation firing over all of them on first paint is
        # motion nobody asked for on a page nobody has touched.
        if "flight-rows-live" not in js:
            return False, (
                "expected flight-rows.js to add its own live-script class — the animation is "
                "keyed on it so a scripts-blocked page animates nothing at all")
        reveal = _css_rule_body(css, ".flight-rows-live .flight-detail-row__reveal")
        if reveal is None:
            return False, (
                "expected the reveal wrapper's animated rule to be scoped to the live-script "
                "class")
        if "display: grid" not in reveal or "grid-template-rows" not in reveal:
            return False, (
                "expected the reveal wrapper to be a grid whose row track is what animates, "
                "got %r" % (reveal,))
        if "var(--motion-fast)" not in reveal:
            return False, (
                "expected the reveal transition to spend var(--motion-fast) — somebody pressed "
                "a control and is watching for it to answer — got %r" % (reveal,))
        if "@starting-style" not in css:
            return False, (
                "expected an @starting-style block: a row going from display:none to displayed "
                "has no previous computed value to transition FROM, so without one the rule is "
                "a transition that never runs")

        # THE DELIBERATE CHOICE, and the property the harness asserts.
        # The collapsed end state stays `display: none` and only the
        # OPENING direction animates. That is what keeps a closed row's
        # links, buttons and copy controls out of the tab order and out
        # of the accessibility tree — a row held present at zero height
        # is still focusable, still announced, and still a row the
        # keyboard walks into and finds nothing.
        collapsed = _css_rule_body(css, ".flight-detail-row--collapsed")
        if collapsed is None or "display: none" not in collapsed:
            return False, (
                "expected the collapsed detail row to resolve to display: none — the animation "
                "is one-directional on purpose, because that is the only end state that removes "
                "the row from the tab order AND the accessibility tree, got %r" % (collapsed,))
        return True, ""
    check(
        "the Flights detail row animates open through a grid reveal wrapper inside its own <td> "
        "(grid-template-rows 0fr, var(--motion-fast), an @starting-style entry, scoped to the "
        "class flight-rows.js adds to <html>), neither interpolate-size nor calc-size() appears, "
        "and the collapsed end state is still display: none — the one state that takes a closed "
        "row out of both the tab order and the accessibility tree (D3/CFG-32, 23-08-PLAN.md "
        "Task 2)",
        _detail_row_height_animates_and_a_closed_row_is_unreachable)

    def _the_chevron_turns_and_carries_no_reduced_motion_block_of_its_own():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()
        glyph = _css_rule_body(css, ".row-toggle__glyph")
        if glyph is None:
            return False, "expected a .row-toggle__glyph rule"
        if "transition" not in glyph:
            return False, (
                "expected the chevron to take a transition of its own — D3's clause, and the "
                "one references/control-density.md:78 pre-approved, got %r" % (glyph,))
        if "var(--motion-fast)" not in glyph:
            return False, (
                "expected the chevron transition to spend var(--motion-fast) rather than a bare "
                "literal, got %r" % (glyph,))
        if "transform" not in glyph:
            return False, (
                "expected the chevron to transition TRANSFORM specifically — the rotation is the "
                "only thing that changes and a blanket `all` would animate properties nobody "
                "chose, got %r" % (glyph,))
        # NO per-rule reduced-motion block, stated in advance by
        # references/control-density.md:78: the global override already
        # covers a plain transform for free, and a block here would be
        # dead code rather than a safety net. Measured as the file's
        # whole live count, so a block added anywhere fails this.
        live = "\n".join(
            line for line in css.splitlines() if not re.match(r"^ *[*/]", line))
        if live.count("prefers-reduced-motion") != 3:
            return False, (
                "expected companion/static/style.css to carry exactly 3 live "
                "prefers-reduced-motion occurrences (the global reduce override, .js "
                ".mobile-nav's narrow one, and 23-04's no-preference view-transition wrapper) — "
                "this plan's chevron and its row animation add none, got %d"
                % live.count("prefers-reduced-motion"))
        return True, ""
    check(
        "the row-toggle chevron transitions TRANSFORM on var(--motion-fast) and adds no per-rule "
        "reduced-motion block — the global override already covers a plain transform for free, "
        "and the stylesheet's live prefers-reduced-motion count is unmoved at 3 (D3/CFG-32, "
        "references/control-density.md:78, 23-08-PLAN.md Task 2)",
        _the_chevron_turns_and_carries_no_reduced_motion_block_of_its_own)

    def _the_phone_cards_own_face_is_its_disclosure_summary():
        tmp = _mkstate("h-card-face-summary")
        try:
            key = illustrations.normalise_airline_key("Air France")
            override_path = illustrations.override_path_for_key(key, tmp)
            os.makedirs(os.path.dirname(override_path), exist_ok=True)
            _write_gallery_png(override_path)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "fc01", "callsign": "FACEONE",
                 "airline": "Air France"},
                # No airline at all, so airline_label falls to
                # AIRLINE_FALLBACK_TEXT and the one-hop resolve link is
                # actually rendered — the whole point of the second row.
                {"ts": "2026-08-27T09:00:00+00:00", "hex": "fc02", "callsign": "FACETWO"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            li = _row_block(rendered, "li", 0)
            if li is None:
                return False, "could not locate the phone card"
            summary = re.search(
                r'<summary class="history-card__summary">(.*?)</summary>', li, re.S)
            if summary is None:
                return False, (
                    "expected the card's own face to BE the disclosure's <summary> — a tap "
                    "anywhere on the card is the native disclosure answering, not a new "
                    "mechanism, got %r" % (li[:300],))
            face = summary.group(1)
            for part in ("history-card__primary", "history-card__secondary",
                         "history-card__airline", "history-card__thumb",
                         "history-card__airline-name", "history-card__time"):
                if part not in face:
                    return False, (
                        "expected %r to be part of the card's tappable face — the thumbnail and "
                        "the airline name shipped in 22-09 and are NOT rebuilt here, they are "
                        "where they already were" % (part,))
            # The one thing that must NOT be inside the summary. It is a
            # control in its own right, and a disclosure whose accessible
            # name ends in another control's call to action is naming an
            # action it does not perform.
            li_unresolved = _row_block(rendered, "li", 1)
            if li_unresolved is None:
                return False, "could not locate the unresolved-airline card"
            if history_page.RESOLVE_LINK_TEXT not in li_unresolved:
                return False, (
                    "expected the unresolved card to still carry its one-hop resolve link "
                    "somewhere on the card — the phone card must not lose an affordance the "
                    "desktop row has")
            unresolved_summary = re.search(
                r'<summary class="history-card__summary">(.*?)</summary>', li_unresolved, re.S)
            if unresolved_summary is None:
                return False, "expected the unresolved card to have a face summary too"
            if history_page.RESOLVE_LINK_TEXT in unresolved_summary.group(1):
                return False, (
                    "did not expect the resolve LINK inside the summary: it is a control in its "
                    "own right, and inside a <summary> it both joins the disclosure's accessible "
                    "name and competes with the disclosure for the same activation")
            if "<a " in unresolved_summary.group(1) or "<button" in unresolved_summary.group(1):
                return False, (
                    "did not expect any nested control inside the card's summary, got %r"
                    % (unresolved_summary.group(1),))
            # And the disclosure BODY is unchanged: still one <details>
            # per card, still exactly the three copy buttons.
            if li.count("<details") != 1 or li.count("</details>") != 1:
                return False, (
                    "expected exactly one <details> per card, got %d open / %d close"
                    % (li.count("<details"), li.count("</details>")))
            body = li[li.index("</summary>"):]
            if body.count("data-copy-value") != 3:
                return False, (
                    "expected the disclosure body to still hold exactly the three copy buttons, "
                    "got %d" % body.count("data-copy-value"))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the phone card's own face IS the native disclosure's <summary> — the primary line, the "
        "secondary line, the time and 22-09's thumbnail and airline name all inside it, so a tap "
        "anywhere opens the card with no script at all — while the one-hop resolve link stays on "
        "the card and OUT of the summary, and the disclosure body still holds exactly the three "
        "copy buttons (D7/CFG-37, 23-08-PLAN.md Task 2)",
        _the_phone_cards_own_face_is_its_disclosure_summary)

    def _history_card_primary_grid_pins_the_timestamp_track():
        # 29-03-PLAN.md Task 2 (CFG-83, 2026-09-17 audit P1): the CSS
        # half — .history-card__primary is a two-track grid, its second
        # track pinned to auto and its timestamp span forbidden from
        # wrapping — plus the RELATIONSHIP that matters: the markup's
        # three primary_value_html branches must each produce a child
        # set the two-track grid can actually place, with no branch
        # producing a third, unclassified top-level child.
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path) as fh:
            css = fh.read()

        primary_block = _css_rule_body(css, ".history-card__primary")
        if primary_block is None:
            return False, "could not locate the .history-card__primary rule block"
        if not re.search(r"display:\s*grid\s*;", primary_block):
            return False, (
                "expected .history-card__primary to declare display: grid, got block %r"
                % primary_block)
        tracks_match = re.search(r"grid-template-columns:\s*([^;]+);", primary_block)
        if tracks_match is None:
            return False, (
                "expected .history-card__primary to declare grid-template-columns, found none "
                "in %r" % primary_block)
        tracks = tracks_match.group(1).strip()
        if not re.match(r"^minmax\(\s*0\s*,\s*1fr\s*\)\s+auto$", tracks):
            return False, (
                "expected grid-template-columns to declare exactly two tracks — minmax(0, 1fr) "
                "then auto — got %r" % tracks)
        if "justify-content" in primary_block:
            return False, (
                "expected justify-content ABSENT from .history-card__primary (meaningless on a "
                "two-track grid whose second track is auto), found it in %r" % primary_block)

        time_block = _css_rule_body(css, ".history-card__time")
        if time_block is None:
            return False, "could not locate the .history-card__time rule block"
        if not re.search(r"white-space:\s*nowrap\s*;", time_block):
            return False, (
                "expected .history-card__time to declare white-space: nowrap, got %r" % time_block)
        if "margin-left" in time_block:
            return False, (
                "expected .history-card__time to declare no margin-left (the grid places it now "
                "instead of the flex auto-margin trick), found %r" % time_block)

        branches = (
            ("callsign", {"ts": "2026-09-21T10:00:00+00:00", "callsign": "GRD01"}),
            ("hex-plus-note", {"ts": "2026-09-21T10:00:00+00:00", "hex": "abc123"}),
            ("empty", {"ts": "2026-09-21T10:00:00+00:00"}),
        )
        for name, fields in branches:
            tmp = _mkstate("h-grid-%s" % name)
            try:
                _seed_runway_events(tmp, [fields])
                rendered = history_page.render(_history_ctx(tmp))
                li_block = _row_block(rendered, "li", 0)
                if li_block is None:
                    return False, "%s branch: could not locate the rendered card" % name
                primary_match = re.search(
                    r'<div class="history-card__primary">(.*?)</div>', li_block, re.S)
                if primary_match is None:
                    return False, (
                        "%s branch: could not locate .history-card__primary markup in %r"
                        % (name, li_block))
                primary_markup = primary_match.group(1)
                if primary_markup.count('<span class="history-card__time">') != 1:
                    return False, (
                        "%s branch: expected exactly one history-card__time (track-2) child, "
                        "found %d in %r" % (
                            name, primary_markup.count('<span class="history-card__time">'),
                            primary_markup))
                track2_start = primary_markup.index('<span class="history-card__time">')
                track1_markup = primary_markup[:track2_start]
                track1_children = re.findall(
                    r'<span class="(cell-primary|cell-secondary)[^"]*"', track1_markup)
                if not track1_children:
                    return False, (
                        "%s branch: expected at least one track-1 (.cell-primary/.cell-secondary) "
                        "child before the timestamp span, found none in %r"
                        % (name, primary_markup))
                # Strip every classified track-1 child; anything left
                # over is a THIRD top-level child the two-track grid has
                # no track for — the property this check exists to
                # prove, per branch.
                unclassified = re.sub(
                    r'<span class="cell-(?:primary|secondary)[^"]*">.*?</span>', "",
                    track1_markup, flags=re.S).strip()
                if unclassified:
                    return False, (
                        "%s branch: expected every child before the timestamp span to be a "
                        "classified .cell-primary/.cell-secondary track-1 child, found leftover "
                        "unclassified markup %r in %r" % (name, unclassified, primary_markup))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "the phone summary card's .history-card__primary line is a two-track CSS grid "
        "(minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time "
        "(white-space: nowrap, no margin-left: auto), and all three primary_value_html branches — "
        "callsign, hex-plus-note, empty — produce a child set the grid can place with no third, "
        "unclassified top-level child (2026-09-17 audit P1, 29-03-PLAN.md Task 2)",
        _history_card_primary_grid_pins_the_timestamp_track)

    def _the_count_animates_without_its_text_production_moving():
        js_path = os.path.join(HERE, "static", "list-filter.js")
        with open(js_path) as fh:
            js = fh.read()
        # The text production, untouched: the template comes from the
        # server-rendered attribute and the two %d are filled from the
        # two counts. That attribute is the only thing that knows the
        # translated plural, and a script that composed the sentence
        # itself would be back to hardcoded English.
        for token in ('getAttribute("data-filter-count-template")',
                      '.replace("%d", String(visibleCount))',
                      '.replace("%d", String(totalCount))'):
            if token not in js:
                return False, (
                    "expected the count's text production to be unchanged (%r) — only its "
                    "presentation animates" % (token,))
        # The ELEMENT animates, never the number: the text is written
        # first and the class second, so the displayed value is correct
        # at every instant including the first frame of the animation.
        if "is-fading-in" not in js:
            return False, (
                "expected the count to spend the stylesheet's existing changed-value animation "
                "rather than declare a fourth keyframes block")
        count_at = js.index("var countEl = document.querySelector(COUNT_SELECTOR);")
        block = js[count_at:count_at + 1400]
        text_at = block.index("countEl.textContent =")
        class_at = block.index("classList.add(")
        if text_at > class_at:
            return False, (
                "expected the count's text to be written BEFORE the animation class is added — "
                "the number is never what moves, so it is never wrong mid-animation")
        if "classList.remove(" not in block:
            return False, (
                "expected the animation class to be removed and re-added so a second change "
                "restarts it — a class already present runs nothing")
        if "offsetWidth" not in block:
            return False, (
                "expected a forced reflow between the removal and the re-add — without it the "
                "browser coalesces both into no change at all and the animation never restarts")
        # And only on a real change. A count re-rendered with the same
        # value has not changed, and animating it would be motion that
        # carries no information.
        if "!==" not in block:
            return False, (
                "expected the animation to fire only when the rendered text actually differs")
        return True, ""
    check(
        "the filter count animates its ELEMENT and never its number: the template-driven text "
        "production is untouched, the text is written before the class is added, the class is "
        "removed and re-added across a forced reflow so a second change restarts it, and it "
        "fires only when the rendered value actually differs (D7/CFG-37, 23-08-PLAN.md Task 2)",
        _the_count_animates_without_its_text_production_moving)

    def _phone_card_route_and_state_carry_the_existing_middle_dot():
        tmp = _mkstate("h-card-separator")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "sep01", "callsign": "SEPCARD",
                 "origin": "LFPO", "destination": "KJFK", "confirmed_state": "departing"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            match = re.search(
                r'<div class="history-card__secondary">(.*?)</div>', rendered, re.S)
            if match is None:
                return False, "could not locate the phone card's secondary line"
            expected = (
                "<span>LFPO → KJFK</span>"
                '<span class="%s">%s</span>'
                "<span>Departing</span>"
            ) % (history_page.CELL_SEPARATOR_CLASS,
                 layout.escape_html(history_page.CELL_SEPARATOR_TEXT))
            if match.group(1) != expected:
                return False, (
                    "expected the route and state to be joined by the module's existing "
                    "middle-dot separator, got %r" % match.group(1))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the phone card's \"ORY → JFK Departing\" line carries the module's EXISTING "
        "cell-inline-sep middle dot between the route and the state, reused rather than "
        "reinvented (22-09-PLAN.md Task 2, X5)",
        _phone_card_route_and_state_carry_the_existing_middle_dot)

    def _raw_iso_survives_only_behind_the_copy_control():
        tmp = _mkstate("h-raw-iso-behind-copy")
        try:
            raw_ts = "2026-08-27T10:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": raw_ts, "hex": "iso01", "callsign": "ISOROW"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if ('data-copy-value="%s"' % raw_ts) not in rendered:
                return False, "expected the raw ISO to survive as the copy control's value"
            # Strip every data-copy-value attribute; the raw ISO must not
            # appear anywhere in what is left (D-05: raw ISO survives
            # only behind a copy control).
            stripped = re.sub(r'data-copy-value="[^"]*"', "", rendered)
            if raw_ts in stripped:
                return False, (
                    "expected the raw ISO timestamp to appear ONLY inside a data-copy-value "
                    "attribute, found it elsewhere in the rendered page")
            # What IS visible is the Paris local clock in the time-value
            # role — never monospace, which stays reserved for identifiers.
            visible = history_page.full_local_time_text(raw_ts)
            if visible == raw_ts:
                return False, "expected a formatted local clock, not the raw ISO"
            for needle in ('<dd class="time-value">%s</dd>' % visible,):
                if needle not in rendered:
                    return False, "expected the visible full timestamp to read %r" % (visible,)
            if '<dd class="mono">%s' % raw_ts in rendered:
                return False, "did not expect the raw ISO in a monospace dd"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the raw ISO timestamp appears only inside a data-copy-value attribute, while the visible "
        "full timestamp is the Europe/Paris local clock in the .time-value role on both the "
        "desktop detail row and the phone card (22-09-PLAN.md Task 2, X5/D-05/C5)",
        _raw_iso_survives_only_behind_the_copy_control)

    def _phone_cards_carry_the_airline_name_and_artwork_thumbnail():
        tmp = _mkstate("h-card-airline-thumb")
        try:
            key = illustrations.normalise_airline_key("Air France")
            override_path = illustrations.override_path_for_key(key, tmp)
            os.makedirs(os.path.dirname(override_path), exist_ok=True)
            _write_gallery_png(override_path)
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "th01", "callsign": "THUMBED",
                 "airline": "Air France"},
                {"ts": "2026-08-27T09:00:00+00:00", "hex": "th02", "callsign": "NOART",
                 "airline": "Totally Unknown Air"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            li_thumbed = _row_block(rendered, "li", 0)
            li_noart = _row_block(rendered, "li", 1)
            if li_thumbed is None or li_noart is None:
                return False, "could not locate both phone cards"
            if 'class="history-card__airline-name">Air France<' not in li_thumbed:
                return False, "expected the phone card to carry the airline name on its own face"
            expected_img = (
                '<img class="history-card__thumb" loading="lazy" decoding="async" '
                'src="%s%s.png"' % (history_page.ILLUSTRATION_ROUTE_PREFIX, key))
            if expected_img not in li_thumbed:
                return False, (
                    "expected the phone card to carry the artwork thumbnail, got %r"
                    % li_thumbed[:200])
            if "history-card__thumb" in li_noart:
                return False, (
                    "did not expect a thumbnail for an airline with no artwork file — an "
                    "unconditional <img> would 404 and render as a broken-image icon")
            if "history-card__airline-name" not in li_noart:
                return False, "expected every card to name its airline, artwork or not"
            # The thumbnail joins the SHARED white-backing/hairline/radius
            # rule as an additional selector — one rule, no new colour
            # literal — with its own contain-fitted 56px box declared after.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            shared = re.search(
                r"((?:^\.?[a-z.\-_]+[^{]*,\s*\n)*[^{\n]*img\.history-card__thumb)\s*\{([^}]*)\}",
                css, re.S | re.M)
            if shared is None:
                return False, (
                    "expected img.history-card__thumb to join a shared rule's selector list")
            if ".now-showing__image" not in shared.group(1) or \
                    ".preview-frame__image" not in shared.group(1):
                return False, (
                    "expected img.history-card__thumb to join the SHARED white-backing/hairline/"
                    "radius rule .now-showing__image and .preview-frame__image already share, "
                    "got selector list %r" % shared.group(1))
            # Its OWN sizing rule is the later, same-specificity block —
            # the shared rule above also ends its selector list with this
            # exact selector at line start, so match every candidate and
            # require one of them to carry the 56px contain-fitted box.
            own_bodies = [
                body for body in re.findall(
                    r"^img\.history-card__thumb\s*\{([^}]*)\}", css, re.S | re.M)]
            if not any("height: 56px" in body and "object-fit: contain" in body
                       for body in own_bodies):
                return False, (
                    "expected img.history-card__thumb's own rule to declare a fixed 56px-tall "
                    "box with contain fitting, got %r" % (own_bodies,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a phone card carries the airline name and, when real artwork exists for it, the Airlines "
        "gallery's own served frame as a thumbnail joining the shared white-backing/hairline/"
        "radius rule in a contain-fitted 56px box — and no <img> at all when no artwork file "
        "exists (22-09-PLAN.md Task 2, X5)",
        _phone_cards_carry_the_airline_name_and_artwork_thumbnail)

    def _no_prefix_registry_duplicated_on_history():
        tmp = _mkstate("h-no-registry")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "reg01", "callsign": "REGCHK"},
            ])
            rendered = history_page.render(_history_ctx(tmp))
            if health_page.UNRESOLVED_SECTION_HEADING in rendered:
                return False, "did not expect Health's Unresolved-prefixes registry heading on History"
            if "<th>Prefix</th>" in rendered or "<th>First seen</th>" in rendered:
                return False, "did not expect the registry table's own column headers on History"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the rendered History page contains no prefix-registry table and no element carrying the "
        "registry table's own headers",
        _no_prefix_registry_duplicated_on_history)

    # ======================================================================
    # 20-10-PLAN.md Task 3 (D-05): the Flights page through i18n.t(), with
    # companion/i18n_fr/flights.py's own French catalogue.
    # ======================================================================

    def _flights_french_render_translates_headings_not_data():
        import companion.prefs as _prefs
        tmp = _mkstate("flights-fr-headings")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1",
                 "airline": "AFR", "origin": "LFPO", "destination": "LFPG",
                 "confirmed_state": "departing", "corroborated": "True"},
            ])
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for needle in (
                ">Vols<", ">Quand<", ">Trajet<", ">Sens<", "Indicatif",
                "Filtrer par indicatif ou code hex"):
            if needle not in rendered:
                return False, "expected the French %r in a French Flights render" % (needle,)
        if "FLT1" not in rendered:
            return False, "expected the seeded callsign 'FLT1' to stay untranslated data"
        return True, ""
    check(
        "a French render of Flights shows the French page title, column headers and filter label, "
        "while a seeded callsign stays untranslated data (D-05, 20-10-PLAN.md Task 3)",
        _flights_french_render_translates_headings_not_data)

    def _flights_full_seeded_render_french_end_to_end():
        import companion.prefs as _prefs
        tmp = _mkstate("flights-fr-full")
        try:
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1",
                 "airline": None, "confirmed_state": "departing", "corroborated": "True"},
                {"ts": "2026-08-27T10:01:00+00:00", "hex": "bbb222", "callsign": "",
                 "airline": None, "confirmed_state": "arriving", "corroborated": "False"},
            ])
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered_fr = history_page.render(_history_ctx(tmp))
            finally:
                _prefs.set_request_prefs(lang="en")
            for needle in (
                    ">Vols<", "Compagnie inconnue", "aucun indicatif",
                    "Au départ", "À l’arrivée", ">Quand<", ">Vol<", ">Trajet<", ">Sens<",
                    "Plus de détails", "Effacer"):
                if needle not in rendered_fr:
                    return False, "expected the French %r in the French Flights render" % (needle,)
            for english_only in (
                    "Airline unknown", "no callsign", "Departing", "Arriving",
                    ">When<", ">Flight<", ">Route<", ">State<"):
                if english_only in rendered_fr:
                    return False, "expected no English %r leaking into the French render" % (
                        english_only,)
            if "FLT1" not in rendered_fr:
                return False, "expected the seeded callsign to stay untranslated data"

            rendered_en = history_page.render(_history_ctx(tmp))
            for needle in (
                    '<h1 class="page-title">Flights</h1>', history_page.AIRLINE_FALLBACK_TEXT,
                    history_page.NO_CALLSIGN_NOTE_TEXT, "Departing", "Arriving",
                    ">When<", ">Flight<", ">Route<", ">State<"):
                if needle not in rendered_en:
                    return False, "expected the English %r in the default-language Flights render" % (
                        needle,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-seeded Flights render under lang='fr' shows every new French string (column "
        "headers, direction words, the unresolved-airline fallback, the no-callsign note, the "
        "disclosure summary and the filter's Clear button) with no English leaking in, the seeded "
        "callsign stays untranslated data, and the identical seeded render under the default "
        "language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 3)",
        _flights_full_seeded_render_french_end_to_end)

    def _flights_catalog_keys_all_present_in_merged_catalog():
        import companion.i18n_fr as i18n_fr
        import companion.i18n_fr.flights as i18n_fr_flights
        missing = [k for k in i18n_fr_flights.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from the merged CATALOG: %r" % (missing,)
        return True, ""
    check(
        "every key in companion/i18n_fr/flights.py's own CATALOG is also a key of the merged "
        "companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up "
        "(20-10-PLAN.md Task 3)",
        _flights_catalog_keys_all_present_in_merged_catalog)

    # ======================================================================
    # Section 3: one end-to-end check - a real companion/app.py subprocess,
    # logged in, fetching /history, the retired /preview redirect, the
    # retired /preview.png route (now 404), and a real /gallery/{name}.png
    # (quick task 260903-etm: the per-row View-panel lightbox is now the
    # sole consumer of this route, the top-of-page render gallery having
    # been retired outright).
    # ======================================================================

    # --- Phase 18: the Home page -------------------------------------------

    def _home_page_render_with_seeded_state():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home")
        try:
            now = "2026-08-27T12:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
                 "airline": "Air France", "origin": "ORY", "destination": "TLS",
                 "confirmed_state": "departing"},
                {"ts": "2026-08-27T11:40:00+00:00", "hex": "4b1a72", "callsign": "<XYZ>"},
            ])
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
            ctx = {
                "state_dir": tmp, "now": now,
                "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
                "last_checkin_ts": "2026-08-27T11:55:00+00:00",
                "device_config": {"wake_interval_s": 900, "display_enabled": True},
                "health_state": {"device_state": "ok", "pipeline_state": "warn",
                                 "battery_state": "ok",
                                 "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                                 "pipeline_html": "<p>A little stale</p>"},
                "simple_mode": False,
            }
            rendered = home_page.render(ctx)
            for needle in (
                    '<h1 class="page-title">Home</h1>', "AFR1380", "Air France", "ORY → TLS",
                    'src="/gallery/2026-08-27T11-50-00+00-00.png"', "3750 mV",
                    "≈ 50%", "Next update ≈"):
                if needle not in rendered:
                    return False, "expected %r in the Home page" % needle
            if "<XYZ>" in rendered or "&lt;XYZ&gt;" not in rendered:
                return False, "expected the hostile callsign to be escaped"
            if rendered.count('class="recent-flight"') != 2:
                return False, "expected exactly two recent-flight rows"
            # 21-04-PLAN.md Task 3 (D-04): .preview-frame precedes the
            # first real .recent-flight row inside .home-picture-row.
            if rendered.index('<figure class="preview-frame">') > rendered.index(
                    'class="recent-flight"'):
                return False, "expected .preview-frame before .recent-flight in document order"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "home_page.render() with seeded flights, a battery reading and a gallery entry renders "
        "the hero picture, the battery percentage estimate, escaped recent flights, and the "
        "Next-update headline, with .preview-frame before .recent-flight in document order (D-04)",
        _home_page_render_with_seeded_state)

    def _home_battery_ring_is_the_same_drawing_at_a_smaller_size():
        """CFG-40 (24-04-PLAN.md Task 3): Home's small battery ring.

        WHAT THIS CHECK IS FOR, and what it deliberately does NOT do. A
        check that greps for `draw.` in two page modules proves nothing
        about whether the two rings share behaviour — both files could
        import the module and then draw two different pictures. So this
        one renders BOTH pages and compares the two rings' PROPORTIONS:
        radius-over-side and stroke-over-side must be identical while the
        sides themselves differ. That is precisely "one drawing, two
        sizes", and it is the property a second copy destroys first — a
        copy that drifts to a fixed 2px stroke keeps the same radius
        ratio and fails on the stroke one.

        The tile must also still print everything it printed before. The
        ring is an ADDITION: removing the printed percentage in favour of
        the picture would break the aria-hidden justification the emitter
        relies on AND would remove the only exact value on the tile.
        """
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home-ring")
        blank = _mkstate("home-ring-none")
        try:
            now = "2026-08-27T12:00:00+00:00"
            # 3690 mV lands on 43% of the 3300-4200 estimate span — a
            # fraction no plausible constant (empty, half, full)
            # coincides with.
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3690)
            health_state = {"device_state": "ok", "pipeline_state": "ok",
                            "battery_state": "ok",
                            "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                            "pipeline_html": "<p>Fresh</p>"}
            ctx = {"state_dir": tmp, "now": now, "gallery_entries": [],
                   "last_checkin_ts": "2026-08-27T11:55:00+00:00",
                   "device_config": {"wake_interval_s": 900, "display_enabled": True},
                   "health_state": health_state, "simple_mode": False}
            rendered = home_page.render(ctx)

            def _rings(markup):
                return (re.findall(r'<circle class="%s"[^>]*/>'
                                   % re.escape(draw.DRAWING_RING_TRACK_CLASS), markup),
                        re.findall(r'<circle class="%s"[^>]*/>'
                                   % re.escape(draw.DRAWING_RING_VALUE_CLASS), markup))

            tracks, values = _rings(rendered)
            if len(tracks) != 1 or len(values) != 1:
                return False, (
                    "expected exactly one ring on Home (one track, one value arc), got %d "
                    "track(s) and %d value arc(s)" % (len(tracks), len(values)))

            # It is inside the BATTERY tile: between that tile's own
            # caption and the next tile's.
            battery_at = rendered.index(home_page.BATTERY_ROW_LABEL)
            data_at = rendered.index(home_page.DATA_ROW_LABEL)
            ring_at = rendered.index(draw.DRAWING_RING_TRACK_CLASS)
            if not battery_at < ring_at < data_at:
                return False, (
                    "the ring is not inside the Battery tile — battery caption at %d, ring at "
                    "%d, next tile's caption at %d" % (battery_at, ring_at, data_at))

            # The tile still prints all three of its own texts.
            tile = rendered[battery_at:data_at]
            for needle in ("≈ 43%", "3690 mV"):
                if needle not in tile:
                    return False, (
                        "expected the Battery tile to still print %r — the ring is an "
                        "ADDITION to the verdict, the percentage and the millivolt detail, "
                        "never a replacement for them" % (needle,))
            if 'class="text-body widget-verdict"' not in tile:
                return False, "expected the Battery tile to still print its verdict"

            # The drawn fraction equals the percentage printed beside it.
            radius = float(re.search(r' r="([0-9.]+)"', values[0]).group(1))
            dash = re.search(r'stroke-dasharray="([0-9.]+) ', values[0])
            drawn = float(dash.group(1)) if dash else 2 * math.pi * radius
            drawn_fraction = drawn / (2 * math.pi * radius)
            if abs(drawn_fraction - 0.43) > 0.0005:
                return False, (
                    "Home's ring draws %.4f of its circumference while the tile prints "
                    "'≈ 43%%' beside it (CFG-40)" % (drawn_fraction,))

            # ONE EMITTER, TWO SIZES — measured across both pages.
            health_tmp = _mkstate("home-ring-health")
            try:
                with _hdb.open_db(health_tmp) as conn:
                    for minute, mv in ((50, 3600), (55, 3690)):
                        _hdb.record_device_health(
                            conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
                health_rendered = health_page.render(
                    {"state_dir": health_tmp, "now": now})
            finally:
                shutil.rmtree(health_tmp, ignore_errors=True)

            def _geometry(markup, where):
                svg = re.search(
                    r'<svg class="%s[^"]*" viewBox="0 0 ([0-9.]+) [0-9.]+"'
                    % re.escape(draw.DRAWING_FIGURE_CLASS), markup)
                if svg is None:
                    return None, "found no ring figure on %s" % where
                side = float(svg.group(1))
                arc = _rings(markup)[1][0]
                return (side,
                        float(re.search(r' r="([0-9.]+)"', arc).group(1)),
                        float(re.search(r'stroke-width="([0-9.]+)"', arc).group(1))), ""

            home_geom, err = _geometry(rendered, "Home")
            if err:
                return False, err
            health_geom, err = _geometry(health_rendered, "Health")
            if err:
                return False, err
            if home_geom[0] >= health_geom[0]:
                return False, (
                    "Home's ring is not SMALLER than Health's — %r against %r; two sizes is "
                    "half of what CFG-40 asks for" % (home_geom[0], health_geom[0]))
            for index, label in ((1, "radius"), (2, "stroke width")):
                home_ratio = home_geom[index] / home_geom[0]
                health_ratio = health_geom[index] / health_geom[0]
                if abs(home_ratio - health_ratio) > 0.001:
                    return False, (
                        "the two rings disagree about %s as a proportion of their own box: "
                        "Home %.4f, Health %.4f. They are not one drawing at two sizes — they "
                        "are two components, which is exactly the drift CFG-40 forbids"
                        % (label, home_ratio, health_ratio))

            # The frame verdict still appears exactly once (a recorded
            # fixed bug on this page, B2).
            verdicts = [text for text in home_page.FRAME_STATE_TEXT.values()
                        if rendered.count(text)]
            for text in verdicts:
                if rendered.count(text) != 1:
                    return False, (
                        "expected the frame verdict %r exactly once on Home, got %d"
                        % (text, rendered.count(text)))

            # No reading: no ring, and no empty one either.
            blank_ctx = dict(ctx, state_dir=blank)
            blank_rendered = home_page.render(blank_ctx)
            for class_name in (draw.DRAWING_RING_TRACK_CLASS, draw.DRAWING_RING_VALUE_CLASS):
                if class_name in blank_rendered:
                    return False, (
                        "a device with no battery reading rendered %r on Home — an empty ring "
                        "reads as 0%%, which is a false statement about a device that has "
                        "simply not checked in" % (class_name,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(blank, ignore_errors=True)
    check(
        "Home's Battery tile draws exactly one ring, inside that tile, whose drawn fraction "
        "equals the '≈ NN%' it still prints beside its own millivolt detail and verdict; the "
        "ring is SMALLER than Health's yet identical to it in radius-over-box and "
        "stroke-over-box, proving one emitter at two sizes rather than two components; the "
        "frame verdict still appears exactly once; and a device with no reading draws no ring "
        "at all (CFG-40)",
        _home_battery_ring_is_the_same_drawing_at_a_smaller_size)

    # ======================================================================
    # 23-03-PLAN.md Task 2 (D14/CFG-34): Home's two visible relative ages
    # become <time data-relative> elements. Both checks assert that
    # NOTHING READS DIFFERENTLY — the rendered text must equal the text
    # the page produces today, in both languages — because this is a
    # wrapping, and a wrapping that changes a string is a rewording.
    # ======================================================================

    _HOME_RELATIVE_ELEMENT_RE = re.compile(
        r'<time datetime="([^"]*)" data-relative>([^<]*)</time>')

    def _home_seeded_ctx(tmp, now, flight_ts):
        from server import history_db as _hdb
        _seed_runway_events(tmp, [
            {"ts": flight_ts, "hex": "3c6444", "callsign": "AFR1380",
             "airline": "Air France", "origin": "ORY", "destination": "TLS",
             "confirmed_state": "departing"},
        ])
        with _hdb.open_db(tmp) as conn:
            _hdb.record_device_health(conn, flight_ts, battery_mv=3750)
        return {
            "state_dir": tmp, "now": now,
            "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
            "last_checkin_ts": flight_ts,
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {"device_state": "ok", "pipeline_state": "ok",
                             "battery_state": "ok",
                             "device_detail_html": "",
                             "pipeline_html": ""},
            "simple_mode": False,
        }

    def _home_recent_flight_age_is_an_element_reading_exactly_as_before():
        import companion.prefs as prefs
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        flight_ts = "2026-08-27T11:50:00+00:00"  # 10 minutes before `now`
        for lang in ("en", "fr"):
            tmp = _mkstate("home-relative-%s" % lang)
            try:
                prefs.set_request_prefs(lang=lang)
                rendered = home_page.render(_home_seeded_ctx(tmp, now, flight_ts))
                expected_age = layout.relative_age_text(600, lang=lang)
                # The age still sits in its own .time-value__age role
                # beside the .time-value clock, joined by the existing
                # .cell-inline-sep dot — C5's split, which this wrapping
                # must not undo.
                cell = re.search(
                    r'<span class="time-value">([^<]*)</span>'
                    r'<span class="cell-inline-sep">·</span>'
                    r'<span class="time-value__age">\((.*?)\)</span>', rendered)
                if cell is None:
                    return False, (
                        "lang=%s: expected the recent-flight time cell to keep C5's clock/age "
                        "split with the age parenthesised inside .time-value__age" % (lang,))
                element = _HOME_RELATIVE_ELEMENT_RE.fullmatch(cell.group(2))
                if element is None:
                    return False, (
                        "lang=%s: expected the age half to be a <time data-relative> element, "
                        "got %r" % (lang, cell.group(2)))
                if element.group(2) != expected_age:
                    return False, (
                        "lang=%s: expected Home's recent-flight age to read exactly what it "
                        "reads today (%r), got %r" % (lang, expected_age, element.group(2)))
                if not element.group(1):
                    return False, "lang=%s: expected a non-empty datetime attribute" % (lang,)
                if layout.age_seconds(element.group(1), now) != 600:
                    return False, (
                        "lang=%s: expected the element's own instant to carry the ROW's moment, "
                        "not the page's, got %r" % (lang, element.group(1)))
                if "&lt;time" in rendered:
                    return False, (
                        "lang=%s: found a double-escaped '&lt;time' — a raw-markup producer was "
                        "escaped again by its caller" % (lang,))
            finally:
                prefs.set_request_prefs(lang="en")
                shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "Home's recent-flight relative age is a <time data-relative> element carrying the ROW's "
        "own instant, reading exactly what it reads today in both languages, with C5's "
        ".time-value/.cell-inline-sep/.time-value__age split and its parentheses intact "
        "(23-03, D14/CFG-34)",
        _home_recent_flight_age_is_an_element_reading_exactly_as_before)

    def _home_rendered_caption_carries_the_element_through_the_template():
        # The caption reaches the page through an i18n template's own
        # "%s", so an escaping mistake THERE would show as literal
        # markup on the page rather than as a missing element. Asserted,
        # never inspected.
        import companion.i18n as i18n
        import companion.prefs as prefs
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        flight_ts = "2026-08-27T11:50:00+00:00"
        gallery_iso = "2026-08-27T11:50:00+00:00"
        for lang in ("en", "fr"):
            tmp = _mkstate("home-caption-%s" % lang)
            try:
                prefs.set_request_prefs(lang=lang)
                rendered = home_page.render(_home_seeded_ctx(tmp, now, flight_ts))
                caption = re.search(
                    r'<figcaption class="preview-frame__caption text-label">(.*?)</figcaption>',
                    rendered, re.S)
                if caption is None:
                    return False, "lang=%s: expected the rendered-picture caption" % (lang,)
                expected_caption = i18n.t_lang(
                    home_page.RENDERED_CAPTION_TEMPLATE, lang) % layout.concise_timestamp_html(
                        gallery_iso, now, lang=lang)
                if not caption.group(1).startswith(expected_caption):
                    return False, (
                        "lang=%s: expected the caption to be its unchanged wording around "
                        "concise_timestamp_html()'s own output %r, got %r"
                        % (lang, expected_caption, caption.group(1)))
                element = _HOME_RELATIVE_ELEMENT_RE.search(caption.group(1))
                if element is None:
                    return False, (
                        "lang=%s: expected the caption's relative half to be a <time "
                        "data-relative> element, got %r" % (lang, caption.group(1)))
                if element.group(2) != layout.relative_age_text(600, lang=lang):
                    return False, (
                        "lang=%s: expected the caption's age to read exactly what it reads "
                        "today, got %r" % (lang, element.group(2)))
                if "&lt;time" in caption.group(1):
                    return False, (
                        "lang=%s: the caption template double-escaped the element — it would "
                        "paint as literal markup on the page" % (lang,))
            finally:
                prefs.set_request_prefs(lang="en")
                shutil.rmtree(tmp, ignore_errors=True)
        return True, ""
    check(
        "Home's rendered-picture caption carries concise_timestamp_html()'s <time data-relative> "
        "element THROUGH its i18n template's own %s — as markup, never double-escaped — with the "
        "caption's wording and the age's text unchanged in both languages (23-03, D14/CFG-34)",
        _home_rendered_caption_carries_the_element_through_the_template)

    def _recent_flight_thumb_resolved_vs_placeholder():
        # Polish fix 1 (Home thumbnails only when artwork exists, D-17):
        # _recent_flight_thumb_html() now takes a state_dir and checks
        # illustrations.resolved_illustration_path() before ever
        # emitting an <img> — retargeted from the pre-fix signature
        # (which rendered any truthy key unconditionally, 404ing on an
        # airline with no artwork file on disk). No state_dir exists on
        # disk for any of these three cases; "air-france" resolves from
        # the vendored illustration directory regardless (state_dir only
        # matters for a per-installation override file).
        from companion.pages import home_page
        no_state_dir = "/tmp/skypane-no-such-state-dir"
        resolved_row = {"callsign": "AFR1380", "airline": "Air France"}
        thumb_resolved = home_page._recent_flight_thumb_html(resolved_row, no_state_dir)
        if thumb_resolved.count("<img") != 1:
            return False, "expected exactly one <img> for a resolved airline"
        if 'loading="lazy"' not in thumb_resolved:
            return False, "expected the thumbnail <img> to be lazily loaded"
        if "/illustration/air-france.png" not in thumb_resolved:
            return False, "expected the resolved illustration route in the <img> src"
        unresolved_row = {"callsign": "XYZ", "airline": None}
        thumb_placeholder = home_page._recent_flight_thumb_html(unresolved_row, no_state_dir)
        if "<img" in thumb_placeholder:
            return False, "expected no <img> at all for a null/unrecognised airline"
        if "recent-flight__thumb--placeholder" not in thumb_placeholder:
            return False, "expected the dashed placeholder span for a null/unrecognised airline"
        # A key that normalises truthily but resolves to no file on disk
        # anywhere (override or vendored) — the exact "easyJet Europe"
        # regression this fix closes — must ALSO fall back to the
        # placeholder, never a broken-image <img src="...404...">.
        no_artwork_row = {"callsign": "EZS123", "airline": "easyJet Europe"}
        thumb_no_artwork = home_page._recent_flight_thumb_html(no_artwork_row, no_state_dir)
        if "<img" in thumb_no_artwork:
            return False, (
                "expected no <img> for an airline whose normalised key resolves to no file "
                "on disk (D-17 fix: a truthy key alone must never be enough)")
        if "recent-flight__thumb--placeholder" not in thumb_no_artwork:
            return False, "expected the dashed placeholder span for an airline with no artwork file"
        return True, ""
    check(
        "a recent-flight row whose airline resolves to a real illustration file renders exactly "
        "one lazily-loaded /illustration/ thumbnail <img>; a null/unrecognised airline AND an "
        "airline whose normalised key resolves to no file on disk anywhere (override or "
        "vendored) both render the dashed placeholder span with no <img> at all (D-17 fix)",
        _recent_flight_thumb_resolved_vs_placeholder)

    def _hero_figure_precedes_status_card_with_flight_one_liner_when_known():
        from companion.pages import home_page
        hero_ctx = {
            "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
            "now": "2026-08-27T12:00:00+00:00",
        }
        current_flight_row = {
            "callsign": "AFR1380", "airline": "Air France", "origin": "ORY",
            "destination": "TLS", "confirmed_state": "departing",
        }
        hero_with_flight = home_page._current_picture_html(hero_ctx, current_flight_row)
        if "preview-frame__flight" not in hero_with_flight:
            return False, "expected the flight one-liner when the current flight is known"
        if '<span class="mono">AFR1380</span> · Air France · ORY → TLS' not in hero_with_flight:
            return False, "expected the callsign/airline/route flight one-liner text"
        hero_without_flight = home_page._current_picture_html(hero_ctx, None)
        if "preview-frame__flight" in hero_without_flight:
            return False, "expected no flight one-liner when there is no current flight"

        # 21-04-PLAN.md Task 3 (D-04): retargeted document-order check —
        # .status-card/.home-hero no longer exist; the new order is
        # header -> .frame-strip -> .home-status-grid -> .home-picture-
        # row, with .preview-frame before .recent-flight inside the last.
        full_ctx = {
            "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
            "now": "2026-08-27T12:00:00+00:00", "health_state": {}, "device_config": {},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        rendered = home_page.render(full_ctx)
        header_pos = rendered.index('<h1 class="page-title">')
        strip_pos = rendered.index('class="frame-strip stat-tile stat-tile--accent"')
        tiles_pos = rendered.index('class="dashboard-grid home-status-grid"')
        picture_row_pos = rendered.index('class="home-columns home-picture-row"')
        if not (header_pos < strip_pos < tiles_pos < picture_row_pos):
            return False, (
                "expected header -> .frame-strip -> .home-status-grid -> .home-picture-row, "
                "got positions %d, %d, %d, %d" % (header_pos, strip_pos, tiles_pos, picture_row_pos))
        if rendered.index('<figure class="preview-frame">') > rendered.index(
                'id="home-flights"'):
            return False, "expected .preview-frame before the recent-flights section inside .home-picture-row"
        return True, ""
    check(
        "the hero's flight one-liner (callsign in .mono, then airline, then the route) appears "
        "when the current flight is known and is absent otherwise, and the page reads header -> "
        ".frame-strip -> .home-status-grid -> .home-picture-row (.preview-frame before "
        ".recent-flight inside it) (D-04)",
        _hero_figure_precedes_status_card_with_flight_one_liner_when_known)

    def _home_page_french_render_translates_headings_and_alt_text_not_data():
        from companion.pages import home_page
        import companion.prefs as _prefs
        ctx = {
            "gallery_entries": [],
            "now": "2026-08-27T12:00:00+00:00", "health_state": {}, "device_config": {},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        row = {"callsign": "AFR1380", "airline": "Air France"}
        try:
            _prefs.set_request_prefs(lang="fr")
            rendered = home_page.render(ctx)
            thumb = home_page._recent_flight_thumb_html(row, ctx["state_dir"])
        finally:
            _prefs.set_request_prefs(lang="en")
        for needle in ("Vols récents", "Voir tous les vols"):
            if needle not in rendered:
                return False, "expected the French heading/link %r" % (needle,)
        if "Illustration Air France" not in thumb:
            return False, "expected the French alt-text template applied to the untranslated airline name"
        if "Air France" not in thumb:
            return False, "expected the airline name itself to stay untranslated data"
        return True, ""
    check(
        "under a French request Home's headings ('Vols récents'/'Voir tous les vols') and a "
        "thumbnail's alt text translate while the callsign/airline name stay untranslated data "
        "(D-05)",
        _home_page_french_render_translates_headings_and_alt_text_not_data)

    def _home_page_full_seeded_render_french_end_to_end():
        from companion.pages import home_page
        from server import history_db as _hdb
        import companion.prefs as _prefs
        tmp = _mkstate("home-fr")
        try:
            now = "2026-08-27T12:00:00+00:00"
            _seed_runway_events(tmp, [
                {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
                 "airline": "Air France", "origin": "ORY", "destination": "TLS",
                 "confirmed_state": "departing"},
            ])
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
            ctx = {
                "state_dir": tmp, "now": now,
                "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
                "last_checkin_ts": "2026-08-27T11:55:00+00:00",
                "device_config": {"wake_interval_s": 900, "display_enabled": True},
                "health_state": {"device_state": "ok", "pipeline_state": "warn",
                                 "battery_state": "ok",
                                 "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                                 "pipeline_html": "<p>A little stale</p>"},
                "simple_mode": False,
            }
            try:
                _prefs.set_request_prefs(lang="fr")
                rendered_fr = home_page.render(ctx)
            finally:
                _prefs.set_request_prefs(lang="en")
            for needle in (
                    ">Accueil<", "Vols récents", "Voir tous les vols", "Cadre", "Batterie",
                    "Données de vol", "Au départ"):
                if needle not in rendered_fr:
                    return False, "expected the French %r in the French Home render" % (needle,)
            if "Prochaine mise à jour" not in rendered_fr and "Attendue depuis" not in rendered_fr:
                return False, "expected either French next-update headline wording"
            for english_only in (
                    "Recent flights", "See all flights", ">Frame<", ">Battery<", "Departing"):
                if english_only in rendered_fr:
                    return False, "expected no English %r leaking into the French render" % (
                        english_only,)
            if "AFR1380" not in rendered_fr or "Air France" not in rendered_fr:
                return False, "expected the callsign/airline data to stay untranslated in French"

            rendered_en = home_page.render(ctx)
            for needle in (
                    '<h1 class="page-title">Home</h1>', "Recent flights", "See all flights",
                    home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL,
                    home_page.DATA_ROW_LABEL, "Next update ≈"):
                if needle not in rendered_en:
                    return False, "expected the English %r in the default-language Home render" % (
                        needle,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a fully-seeded Home render under lang='fr' shows the French page title, section "
        "headings, status-row labels and next-update headline with no English string leaking "
        "in (while the callsign/airline data stays untranslated), and the identical seeded "
        "render under the default language still carries every pre-existing English needle",
        _home_page_full_seeded_render_french_end_to_end)

    def _home_status_card_localises_real_health_state_timestamps_under_french():
        # Polish fix 2: unlike the check above (which hand-builds
        # ctx["health_state"] with already-English literal fragments,
        # never exercising the real timestamp-formatting path), this
        # check derives ctx["health_state"] from a REAL health_page.
        # compute_health_state() call — the exact value companion/
        # app.py's page_context() threads into every authenticated
        # page's ctx — with `now` on a different calendar day from
        # every seeded timestamp, so a surviving English month
        # abbreviation or "ago" is unmistakable.
        #
        # 22-07-PLAN.md Task 1 (B2) RETARGET: this check used to also
        # assert the Flight-data row's detail joined its verdict/
        # timestamp/last-detection clauses with " · " — that was
        # exercising the OLD re-embedded-pipeline_html defect this very
        # plan removes. Home now reads pipeline_detail_html (health_
        # page.py's verdict-free, SINGLE-clause sibling of pipeline_
        # html, 22-03-PLAN.md), so the Flight-data row's detail is one
        # clause, not three, and never joins anything with " · " at
        # all — the assertion below is flipped to pin exactly that.
        from companion.pages import home_page
        from server import history_db as _hdb
        import companion.prefs as _prefs
        tmp = _mkstate("home-fr-health")
        try:
            now = "2026-09-12T00:00:00+00:00"
            device_ts = "2026-09-10T23:58:00+00:00"
            with _hdb.open_db(tmp) as conn:
                _hdb.record_device_health(conn, device_ts, battery_mv=3800)
                _hdb.set_meta(conn, _hdb.META_LAST_PIPELINE_RUN, device_ts)
                _hdb.set_meta(conn, _hdb.META_LAST_DETECTION, device_ts)
            try:
                _prefs.set_request_prefs(lang="fr")
                health_state = health_page.compute_health_state(tmp, now=now)
                ctx = {
                    "state_dir": tmp, "now": now, "gallery_entries": [],
                    "last_checkin_ts": device_ts,
                    "device_config": {"wake_interval_s": 900, "display_enabled": True},
                    "health_state": health_state, "simple_mode": False,
                }
                rendered = home_page.render(ctx)
            finally:
                _prefs.set_request_prefs(lang="en")
            if "sept." not in rendered:
                return False, "expected the French month abbreviation 'sept.' in the Home render"
            if " ago" in rendered:
                return False, "expected no English ' ago' in the Home render"
            for english_month in (
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                    "Oct", "Nov", "Dec"):
                if english_month in rendered:
                    return False, "expected no English month abbreviation %r in the Home render" % (
                        english_month,)
            # "Données de vol" is companion/i18n_fr/home.py's own French
            # translation of DATA_ROW_LABEL ("Flight data") — the label
            # itself is French text by this point in the render, so the
            # anchor must be too.
            data_row_start = rendered.index("Données de vol")
            data_row_end = rendered.index("</div>", data_row_start)
            data_row = rendered[data_row_start:data_row_end]
            if data_row.count(" · ") != 0:
                return False, (
                    "expected NO ' · '-joined multi-clause detail in the Flight-data row — "
                    "22-07-PLAN.md Task 1 (B2) replaced the re-embedded 3-clause pipeline_html "
                    "with the verdict-free, single-clause pipeline_detail_html (got %r)"
                    % (data_row,))
            if health_page.PIPELINE_STATE_TEXT["error"] in data_row:
                return False, (
                    "expected Health's own PIPELINE_STATE_TEXT verdict wording NOT to appear "
                    "inside Home's Flight-data row — Home renders its OWN verdict only (B2)")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's status card, fed a REAL health_page.compute_health_state() result computed "
        "under lang='fr', fully localises the Frame/Flight-data rows' timestamps (no English "
        "month abbreviation or ' ago' survives) and the Flight-data row's detail is now a "
        "single, verdict-free clause — never joined with ' · ', never repeating Health's own "
        "verdict wording (Polish fix 2 / 22-07-PLAN.md Task 1 B2 retarget)",
        _home_status_card_localises_real_health_state_timestamps_under_french)

    # --- 22-07-PLAN.md Task 1 (X2/B2/X4): Home reads one frame state, one
    # pipeline detail and one airline name -----------------------------

    def _home_frame_tile_matches_strip_for_the_nightly_held_regression():
        # The exact X2 nightly false alarm fixture (22-UI-SPEC.md §3.3
        # rule 6, mirrored from test_status_pages.py's own
        # _frame_strip_nightly_regression_held_is_neutral_never_warn):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00
        # Europe/Paris. battery_state/pipeline_state are pinned "ok" in
        # the fixture so the warn/error scan below is unambiguously
        # about the Frame signal alone, not an unrelated tile.
        from companion.pages import home_page
        from datetime import datetime, timezone, timedelta
        paris = timezone(timedelta(hours=1))
        device_cfg = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
        ctx = {
            "last_checkin_ts": checkin.isoformat(), "device_config": device_cfg,
            "now": clock.isoformat(), "gallery_entries": [],
            "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        rendered = home_page.render(ctx)
        for warn_token in ("dot--warn", "dot--error", "stat-tile--warn", "stat-tile--error"):
            if warn_token in rendered:
                return False, "expected zero %r in a held Home render, found it" % (warn_token,)
        strip_match = re.search(r'time-value time-value--primary">([^<]+)</span>', rendered)
        tile_match = re.search(r'<span class="time-value">([^<]+)</span>', rendered)
        if not strip_match or not tile_match:
            return False, "expected both the strip and the Frame tile to render a clock value"
        if strip_match.group(1) != tile_match.group(1):
            return False, (
                "expected the SAME clock string in the strip and the Frame tile, got %r vs %r"
                % (strip_match.group(1), tile_match.group(1)))
        if home_page.FRAME_STATE_TEXT["off"] not in rendered:
            return False, "expected the held Frame tile's own neutral verdict text"
        return True, ""
    check(
        "the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/"
        "Paris): Home's Frame tile and the strip render the SAME clock string, and zero warn/"
        "error tokens appear anywhere on the page (X2, D-03/CFG-26)",
        _home_frame_tile_matches_strip_for_the_nightly_held_regression)

    def _home_frame_tile_flips_to_late_together_with_the_strip():
        from companion.pages import home_page
        device_cfg = {"wake_interval_s": 900, "display_enabled": True}
        ctx = {
            "last_checkin_ts": "2026-08-27T11:00:00+00:00", "device_config": device_cfg,
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
            "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
            "state_dir": "/tmp/skypane-no-such-state-dir",
        }
        rendered = home_page.render(ctx)
        if "Expected since" not in rendered:
            return False, "expected the strip's own late headline"
        if "dot--warn" not in rendered:
            return False, "expected the strip's own warn dot for a late frame"
        if home_page.FRAME_STATE_TEXT["warn"] not in rendered:
            return False, "expected the Frame tile's own late verdict text"
        if "stat-tile stat-tile--warn" not in rendered:
            return False, "expected the Frame tile's own warn border class"
        return True, ""
    check(
        "a late frame flips the strip to 'Expected since'/dot--warn and Home's Frame tile to "
        "its own late verdict/stat-tile--warn together, at the same threshold — they cannot "
        "disagree because neither computes anything the other does not (X2)",
        _home_frame_tile_flips_to_late_together_with_the_strip)

    def _home_flight_data_tile_one_verdict_verdict_free_detail():
        from companion.pages import home_page
        ctx = {
            "health_state": {
                "device_state": "ok", "pipeline_state": "warn", "battery_state": "ok",
                "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                "pipeline_html": (
                    '<p>%s</p><p>10 Sep 23:58 (1d ago)</p>' % health_page.PIPELINE_STATE_TEXT["warn"]),
                "pipeline_detail_html": '<span class="mono">10 Sep 23:58 (1d ago)</span>',
            },
            "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        }
        rendered = home_page.render(ctx)
        if rendered.count(home_page.DATA_STATE_TEXT["warn"]) != 1:
            return False, "expected Home's own Flight-data verdict exactly once"
        if health_page.PIPELINE_STATE_TEXT["warn"] in rendered:
            return False, (
                "expected Health's own pipeline verdict text NOT to appear on Home — re-"
                "embedding it is the exact double-verdict stacking B2 removes")
        if "10 Sep 23:58" not in rendered:
            return False, "expected the verdict-free pipeline_detail_html's own timestamp to render"
        return True, ""
    check(
        "Home's Flight-data tile renders exactly one verdict (its own DATA_STATE_TEXT) with "
        "Health's verdict-free pipeline_detail_html beneath it, never Health's own "
        "PIPELINE_STATE_TEXT verdict sentence a second time (B2)",
        _home_flight_data_tile_one_verdict_verdict_free_detail)

    def _home_recent_flights_use_display_airline_name_matching_flights():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home-airline-alias")
        try:
            with _hdb.open_db(tmp) as conn:
                _hdb.record_runway_event(
                    conn, ts="2026-08-27T11:50:00+00:00", hex="3c6444", callsign="CCM123",
                    airline="CCM Airlines", origin="ORY", destination="AJA",
                    confirmed_state="departing")
            ctx = {
                "state_dir": tmp, "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
                "health_state": {}, "device_config": {},
            }
            rendered = home_page.render(ctx)
            if "Air Corsica" not in rendered:
                return False, "expected the aliased display name 'Air Corsica' on Home"
            if "CCM Airlines" in rendered:
                return False, "expected the raw upstream airline string not to leak onto Home"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "a recent-flight row whose stored airline is an alias (\"CCM Airlines\") renders the "
        "SAME display name (\"Air Corsica\") Flights shows via display_airline_name(), never "
        "the raw upstream string (X4)",
        _home_recent_flights_use_display_airline_name_matching_flights)

    def _home_exactly_one_element_named_frame():
        from companion.pages import home_page
        ctx = {
            "health_state": {}, "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        }
        rendered = home_page.render(ctx)
        if rendered.count(">Frame<") != 1:
            return False, (
                "expected exactly one element named 'Frame' (the strip's own heading), got %d"
                % (rendered.count(">Frame<"),))
        if home_page.FRAME_ROW_LABEL == "Frame":
            return False, "expected the tile caption to be renamed away from 'Frame' (X4 collision)"
        if home_page.FRAME_ROW_LABEL not in rendered:
            return False, "expected the renamed tile caption to still render"
        return True, ""
    check(
        "exactly one element on a rendered Home page is named 'Frame' (the shared strip's own "
        "heading) — Home's tile caption is renamed to resolve the X4 collision",
        _home_exactly_one_element_named_frame)

    # --- 22-07-PLAN.md Task 2 (B18/B2): one line for the time, one height
    # for the tiles, one weight for the thumbnails -----------------------

    def _home_recent_flight_time_one_line_no_mono_class():
        from companion.pages import home_page
        from server import history_db as _hdb
        tmp = _mkstate("home-time-one-line")
        try:
            with _hdb.open_db(tmp) as conn:
                _hdb.record_runway_event(
                    conn, ts="2026-08-27T11:35:00+00:00", hex="3c6444", callsign="AFR1380",
                    airline="Air France", origin="ORY", destination="TLS",
                    confirmed_state="departing")
            ctx = {
                "state_dir": tmp, "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
                "health_state": {}, "device_config": {},
            }
            rendered = home_page.render(ctx)
            start = rendered.index('class="recent-flight__time')
            end = rendered.index("</li>", start)
            time_cell = rendered[start:end]
            if "mono" in time_cell:
                return False, "expected no monospace class in the recent-flight time cell"
            if 'class="time-value"' not in time_cell:
                return False, "expected the clock to carry the .time-value role"
            if 'class="cell-inline-sep"' not in time_cell:
                return False, "expected the existing .cell-inline-sep middle dot"
            if 'class="time-value__age"' not in time_cell:
                return False, "expected the relative age in the .time-value__age muted role"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "the recent-flight time cell markup carries no monospace class, and reads the clock "
        "(.time-value), the existing .cell-inline-sep middle dot and the relative age "
        "(.time-value__age) as one line (B18)",
        _home_recent_flight_time_one_line_no_mono_class)

    def _home_status_grid_declares_align_items_stretch_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        start = css_source.index(".home-status-grid {")
        end = css_source.index("}", start)
        block = css_source[start:end]
        if "align-items: stretch" not in block:
            return False, "expected .home-status-grid to declare align-items: stretch (B2)"
        return True, ""
    check(
        ".home-status-grid's own CSS rule declares align-items: stretch (B2)",
        _home_status_grid_declares_align_items_stretch_in_css)

    def _recent_flight_time_nowrap_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        # .recent-flight__time appears in TWO rules — a shared colour-only
        # rule with .recent-flight__detail, and its own dedicated rule
        # (text-align/justify-self/white-space). The bare selector text
        # cannot anchor this lookup: the shared rule ends in the IDENTICAL
        # ".recent-flight__time {" and comes first in source order. So
        # anchor on a declaration unique to the dedicated rule.
        #
        # Quick task 260913-bjy: that anchor used to be the percentage
        # width cap, which this task deleted — it clamped the box to 60%
        # of its OWN max-content (the item sits in a content-sized `auto`
        # grid track, so the percentage resolved against the very content
        # it bounded) and painted the relative age outside the card at
        # every width, off the right edge of a 390px viewport. The anchor
        # moved to the grid end-alignment declaration, verified unique in
        # the stylesheet. It is deliberately a DIFFERENT declaration from
        # the asserted one, so this check still fails if `white-space:
        # nowrap` alone is ever dropped.
        #
        # Quick task 260913-dgh: that anchor is gone in turn — the row is
        # a wrapping flex line now, so a grid-only self-alignment would
        # have been a dead declaration. The anchor moves to the auto
        # inline-start margin that replaced it, re-verified as the single
        # occurrence in the stylesheet (the only other `margin-inline-
        # start` there carries a length, not the keyword). The
        # different-declaration property above is preserved: the anchor
        # is still not the assertion.
        start = css_source.index("margin-inline-start: auto")
        block_start = css_source.rindex("{", 0, start)
        end = css_source.index("}", start)
        block = css_source[block_start:end]
        if "white-space: nowrap" not in block:
            return False, "expected .recent-flight__time to declare white-space: nowrap (B18)"
        return True, ""
    check(
        ".recent-flight__time's own CSS rule declares white-space: nowrap so the clock/age "
        "pair can never wrap onto a second line (B18)",
        _recent_flight_time_nowrap_in_css)

    def _recent_flight_thumbnails_share_the_shipped_treatments_in_css():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        # The real thumbnail joins the shared white-backing/hairline/
        # radius rule .now-showing__image/.preview-frame__image already
        # carry — tag-qualified (img.recent-flight__thumb) so it can
        # never accidentally match the placeholder <span>, which shares
        # the bare .recent-flight__thumb class for its own 40x40 sizing.
        shared_start = css_source.index(".now-showing__image,")
        shared_end = css_source.index("}", shared_start)
        shared_block = css_source[shared_start:shared_end]
        if "img.recent-flight__thumb" not in shared_block:
            return False, (
                "expected img.recent-flight__thumb to join the shared white-backing/hairline/"
                "radius rule (B18)")
        # The placeholder's own dashed/canvas-fill values string-equal
        # .airline-card__placeholder's (reused BY VALUE, never a new
        # literal) — NOT selector-shared with it, since companion/
        # test_status_pages.py (a sibling plan's file this plan may not
        # edit) pins ".airline-card__placeholder {" as a standalone
        # selector whose own rule body alone carries all five of its
        # declarations.
        if ".airline-card__placeholder,\n.recent-flight__thumb--placeholder" in css_source:
            return False, (
                "expected .airline-card__placeholder's OWN selector to stay standalone — "
                "companion/test_status_pages.py pins it as such")
        placeholder_start = css_source.index(".recent-flight__thumb--placeholder {\n  border:")
        placeholder_end = css_source.index("}", placeholder_start)
        placeholder_block = css_source[placeholder_start:placeholder_end]
        for expected in (
                "border: 1px dashed var(--color-border)", "background: var(--color-canvas)"):
            if expected not in placeholder_block:
                return False, (
                    "expected .recent-flight__thumb--placeholder's own rule to reuse %r "
                    "(the exact value .airline-card__placeholder declares) (B18)" % (expected,))
        return True, ""
    check(
        "the real recent-flight thumbnail joins the shared white-backing/hairline/radius rule "
        "and the placeholder's own rule reuses .airline-card__placeholder's exact dashed/"
        "canvas-fill values (never a new literal, never sharing that pinned selector), so a "
        "missing thumbnail matches the real ones in weight (B18)",
        _recent_flight_thumbnails_share_the_shipped_treatments_in_css)

    def _single_has_supports_block_unmoved():
        css_path = os.path.join(HERE, "static", "style.css")
        with open(css_path, "r", encoding="utf-8") as fh:
            css_source = fh.read()
        count = css_source.count("@supports selector(:has(*)) {")
        if count != 1:
            return False, "expected exactly one @supports selector(:has(*)) block, got %d" % count
        return True, ""
    check(
        "companion/static/style.css still carries exactly one @supports selector(:has(*)) "
        "block — this plan opens no second one",
        _single_has_supports_block_unmoved)

    def _home_catalog_keys_all_present_in_merged_catalog():
        import companion.i18n_fr as i18n_fr
        import companion.i18n_fr.home as i18n_fr_home
        missing = [k for k in i18n_fr_home.CATALOG if k not in i18n_fr.CATALOG]
        if missing:
            return False, "keys missing from the merged CATALOG: %r" % (missing,)
        return True, ""
    check(
        "every key in companion/i18n_fr/home.py's own CATALOG is also a key of the merged "
        "companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up",
        _home_catalog_keys_all_present_in_merged_catalog)

    def _home_page_full_render_has_quick_action_only_inside_the_strip_and_three_tiles():
        # 21-04-PLAN.md Task 3 (D-04/D-05): retargeted — D-01 puts the
        # Screen/Quiet-hours instant switches ON Home now, inside the
        # shared Frame strip, so "no quick-action anywhere" (the old
        # D-16 assertion) is no longer the correct claim; the new claim
        # is "quick-action markup exists exactly once, inside the
        # strip, and nowhere else on the page."
        from companion.pages import home_page
        ctx = {
            "health_state": {"device_state": "ok", "pipeline_state": "ok", "battery_state": "ok"},
            "device_config": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
            "now": "2026-08-27T12:00:00+00:00",
        }
        rendered = home_page.render(ctx)
        if "status-card__rows" in rendered or "home-hero" in rendered:
            return False, "expected no status-card__rows or home-hero markup on the rebuilt Home page"
        strip_start = rendered.index('class="frame-strip stat-tile stat-tile--accent"')
        tiles_start = rendered.index('class="dashboard-grid home-status-grid"')
        outside_strip = rendered[:strip_start] + rendered[tiles_start:]
        if "quick-action" in outside_strip:
            return False, "expected no quick-action markup anywhere outside .frame-strip"
        strip_segment = rendered[strip_start:tiles_start]
        on_off_count = strip_segment.count("quick-action--on") + strip_segment.count("quick-action--off")
        if on_off_count != 2:
            return False, (
                "expected exactly two quick-action--on/off cells inside .frame-strip, got %d"
                % on_off_count)
        if rendered.count('class="stat-tile ') != 3:
            return False, "expected exactly three stat-tile elements, got %d" % (
                rendered.count('class="stat-tile '),)
        for label in (home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL,
                      home_page.DATA_ROW_LABEL):
            if label not in rendered:
                return False, "expected the %r tile label" % (label,)
        if rendered.count(home_page.FRAME_STATE_TEXT["ok"]) != 1:
            return False, (
                "expected the Frame state sentence to appear exactly once — the "
                "20-RESEARCH.md Pitfall 3 duplicated-verdict regression test")
        return True, ""
    check(
        "a rendered Home page carries no status-card__rows/home-hero markup, quick-action markup "
        "only inside .frame-strip (exactly two cells) and nowhere else, exactly three stat-tile "
        "elements labelled Frame/Battery/Flight data, and the Frame verdict sentence exactly once "
        "(D-04/D-05)",
        _home_page_full_render_has_quick_action_only_inside_the_strip_and_three_tiles)

    def _home_status_card_headline_next_update_or_expected_since():
        # 21-04-PLAN.md Task 3 (D-01/D-04): retargeted at
        # layout.frame_strip_html() — home_page._status_card_html() is
        # deleted; the headline computation it owned moved to the
        # strip helper unchanged (Task 1).
        import companion.wake as wake
        base_ctx = {
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {}, "state_dir": "/tmp/skypane-no-such-state-dir",
        }

        def _strip_html(ctx):
            next_wake_iso = wake.next_wake_at_iso(
                ctx.get("last_checkin_ts"), ctx.get("device_config"))
            return layout.frame_strip_html(
                ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)

        future_ctx = dict(
            base_ctx, last_checkin_ts="2026-08-27T11:55:00+00:00", now="2026-08-27T12:00:00+00:00")
        rendered_future = _strip_html(future_ctx)
        # 11:55 UTC + 15 minutes = 12:10 UTC = 14:10 Europe/Paris (CEST,
        # UTC+2, in effect in late August) — still AFTER the 12:00 UTC
        # "now", so this is the not-yet-due branch.
        # 22-04-PLAN.md Task 2 (C5): the clock value is now its own
        # <span class="time-value time-value--primary"> element rather
        # than baked into the sentence's plain text, so "Next update ≈
        # 14:10" is no longer one contiguous substring — checked as two
        # pieces instead.
        if "Next update ≈" not in rendered_future or "14:10" not in rendered_future:
            return False, "expected the future next-update headline"
        if "status-card__headline--warn" in rendered_future:
            return False, "expected no warn modifier for a future next-update"

        past_ctx = dict(
            base_ctx, last_checkin_ts="2026-08-27T11:00:00+00:00", now="2026-08-27T12:00:00+00:00")
        rendered_past = _strip_html(past_ctx)
        # 11:00 UTC + 15 minutes = 11:15 UTC, already BEFORE the 12:00 UTC
        # "now" — the overdue, warn-treatment branch.
        if "Expected since" not in rendered_past:
            return False, "expected the overdue headline wording"
        if "status-card__headline--warn" not in rendered_past:
            return False, "expected the warn modifier for an overdue next-update"

        missing_checkin = dict(base_ctx, last_checkin_ts=None, now="2026-08-27T12:00:00+00:00")
        if "status-card__headline" in _strip_html(missing_checkin):
            return False, "expected no headline at all when there is no check-in yet"
        missing_interval = dict(
            base_ctx, device_config={}, last_checkin_ts="2026-08-27T11:55:00+00:00",
            now="2026-08-27T12:00:00+00:00")
        if "status-card__headline" in _strip_html(missing_interval):
            return False, "expected no headline at all when the wake interval is unknown"
        return True, ""
    check(
        "the Frame strip's headline reads 'Next update ≈ HH:MM' for a future next-update, "
        "'Expected since HH:MM' in the warn treatment for a past one, and renders no headline "
        "at all when either the check-in or the wake interval is unknown (D-01, moved from the "
        "deleted _status_card_html())",
        _home_status_card_headline_next_update_or_expected_since)

    def _home_status_card_always_shows_health_link():
        """D-17 (21-01-PLAN.md Task 2): the display-mode gate that used
        to hide this link is deleted — replaces a deleted check that
        tested that now-removed mechanism. 21-04-PLAN.md Task 3:
        retargeted at _status_tiles_html(), the deleted
        _status_card_html()'s own replacement.
        """
        from companion.pages import home_page
        ctx = {
            "health_state": {}, "device_config": {},
            "state_dir": "/tmp/skypane-no-such-state-dir", "now": "2026-08-27T12:00:00+00:00",
        }
        rendered = home_page._status_tiles_html(ctx)
        if home_page.HEALTH_LINK_TEXT not in rendered:
            return False, "expected the Health link to always render (D-17)"
        return True, ""
    check(
        "a default Home render always carries the status tiles section's 'See details on "
        "Health' link (D-17)",
        _home_status_card_always_shows_health_link)

    def _home_page_render_degrades_with_nothing():
        from companion.pages import home_page
        rendered = home_page.render({})
        for needle in (home_page.NO_FLIGHTS_HEADING, home_page.NO_PANEL_HEADING,
                       home_page.NO_READING_TEXT):
            if needle not in rendered:
                return False, "expected %r for an empty ctx" % needle
        if battery.battery_percent(4200) != 100 or battery.battery_percent(3300) != 0:
            return False, "expected the percentage estimate to clamp at the full/empty voltages"
        if battery.battery_percent("x") is not None or battery.battery_percent(0) is not None:
            return False, "expected a non-numeric or zero reading to yield None"
        if home_page._gallery_name_to_iso("2026-09-10T21-38-48+00-00.png") != "2026-09-10T21:38:48+00:00":
            return False, "expected the gallery filename to round-trip to its ISO timestamp"
        if home_page._gallery_name_to_iso("junk.png") is not None or home_page._gallery_name_to_iso(None) is not None:
            return False, "expected an unparseable gallery name to yield None"
        return True, ""
    check(
        "home_page.render({}) degrades to its empty states without raising, battery.battery_percent() "
        "clamps and rejects bad input, and the gallery filename parser round-trips or returns None",
        _home_page_render_degrades_with_nothing)

    def _battery_percent_moved_out_of_home_page():
        from companion.pages import home_page
        if hasattr(home_page, "battery_percent"):
            return False, "expected home_page.battery_percent to be gone after the D-01 move"
        return True, ""
    check(
        "battery_percent() no longer exists on home_page after moving to companion/battery.py (D-01)",
        _battery_percent_moved_out_of_home_page)

    # --- 24-06-PLAN.md Task 1 (CFG-42): the time domain -----------------
    #
    # THE ONE THING THESE FOUR CHECKS ARE FOR. Every other drawing in
    # this phase maps an INDEX to an x position, and an index scale is
    # indistinguishable from a time scale on any series that arrived on
    # a perfectly even cadence — which is exactly what a seeded fixture
    # tends to be. So the checks below are written around the case the
    # two scales DISAGREE about: a gap. Under an index scale a six-hour
    # outage is one step, the same width as the fifteen minutes either
    # side of it; under a time scale it is a quarter of the band with
    # nothing in it. The mutation recorded in the summary substitutes
    # draw.percent_x() for draw.percent_time() and _day_band_time_scale_
    # places_by_when_not_by_index() is the check that goes red.

    # An arbitrary, fixed epoch second standing in for a Paris midnight.
    # The scale is pure arithmetic on two numbers in the same unit, so
    # nothing here needs a real timezone — which is the point of the
    # helper taking numbers rather than datetimes (companion/draw.py may
    # not import the server package, where the one Paris-day conversion
    # lives).
    _BAND_DAY_START = 1756000000

    def _band_hour(n):
        return _BAND_DAY_START + int(n * 3600)

    def _band_shapes(markup, class_name):
        """Every <rect> in `markup` carrying exactly `class_name`.

        The closing quote in the pattern is load-bearing: `drawing-band`
        is a strict prefix of both `drawing-band-span` and
        `drawing-band-mark`, so a `'class="drawing-band"' in element`
        test would report all three as the frame. This file has been bitten
        by that collision before (companion/test_companion_app.py:4134's
        own `(?<![-\\w])fill="none"` records the mirror case).
        """
        return re.findall(
            r'<rect class="%s"[^>]*/>' % re.escape(class_name), markup)

    def _band_attr(element, name):
        found = re.search(r'\s%s="([^"]*)"' % re.escape(name), element)
        return found.group(1) if found else None

    def _band_percent(element, name):
        raw = _band_attr(element, name)
        if raw is None or not raw.endswith("%"):
            return None
        return float(raw[:-1])

    def _day_band_time_scale_places_by_when_not_by_index():
        day = draw.SECONDS_PER_DAY
        # Midnight, midday, and the day's own final instant.
        for offset, expected in ((0, 0.0), (day / 2.0, 50.0), (day, 100.0)):
            got = draw.percent_time(_BAND_DAY_START + offset, _BAND_DAY_START)
            if got is None or abs(got - expected) > 1e-9:
                return False, (
                    "expected %+.1fs into the day at %.1f%%, got %r — the three positions a "
                    "reader checks a time axis against first" % (offset, expected, got))
        # Outside the day is REJECTED, never positioned. A clamped
        # instant would put yesterday's check-in at this band's midnight
        # and make today's drawing claim a check-in that never happened
        # (T-24-06-A).
        for outside in (_BAND_DAY_START - 1, _BAND_DAY_START + day + 1):
            if draw.percent_time(outside, _BAND_DAY_START) is not None:
                return False, (
                    "expected an instant outside the day to be rejected, got %r for %r — "
                    "clamping it would invent a check-in at an edge of the band"
                    % (draw.percent_time(outside, _BAND_DAY_START), outside))
        # Totality, because these numbers arrive from stored text.
        for hostile in (None, True, float("nan"), float("inf"), "12:00", [], {}):
            if draw.percent_time(hostile, _BAND_DAY_START) is not None:
                return False, "expected %r as an instant to be rejected" % (hostile,)
            if draw.percent_time(_BAND_DAY_START, hostile) is not None:
                return False, "expected %r as a day start to be rejected" % (hostile,)
        if draw.percent_time(_BAND_DAY_START, _BAND_DAY_START, 0) is not None:
            return False, "expected a zero-length day to be rejected rather than divided by"

        # A Europe/Paris day is 23 or 25 hours twice a year, so the
        # day's length is a parameter and an hour is a share of THAT
        # day, not of a hardcoded 86400.
        short = draw.percent_time(_BAND_DAY_START + 3600, _BAND_DAY_START, 23 * 3600)
        if short is None or abs(short - 100.0 / 23) > 1e-9:
            return False, (
                "on a 23-hour DST day an hour should be %.4f%% of the band, got %r"
                % (100.0 / 23, short))

        # THE PROPERTY AN INDEX SCALE DOES NOT HAVE: the distance between
        # two instants an hour apart is the same 1/24 of the band however
        # many other instants are on it. Measured off the drawn band, not
        # off the helper, because the band is what a reader sees.
        hour_percent = 100.0 / 24
        seen = []
        for fillers in ([], [_band_hour(h) for h in (0, 2, 4, 6, 20, 22)]):
            instants = fillers + [_band_hour(8), _band_hour(9)]
            markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
            if collapsed:
                return False, (
                    "expected no collapsing in a %d-instant series spaced two hours apart, "
                    "got %d collapsed" % (len(instants), collapsed))
            marks = [_band_percent(el, "x") for el in _band_shapes(markup, "drawing-band-mark")]
            if len(marks) != len(instants):
                return False, (
                    "expected one mark per instant (%d), got %d" % (len(instants), len(marks)))
            eight = min(marks, key=lambda p: abs(p - 8 * hour_percent))
            nine = min(marks, key=lambda p: abs(p - 9 * hour_percent))
            seen.append((len(instants), eight, nine))
            if abs(eight - 8 * hour_percent) > 0.02:
                return False, (
                    "with %d instants on the band, the 08:00 check-in is drawn at %.2f%% "
                    "instead of %.2f%% — that is an INDEX position, not a time position "
                    "(under draw.percent_x() it would sit at %.2f%%)"
                    % (len(instants), eight, 8 * hour_percent,
                       draw.percent_x(sorted(instants).index(_band_hour(8)), len(instants))))
            if abs((nine - eight) - hour_percent) > 0.02:
                return False, (
                    "with %d instants on the band, an hour measures %.2f%% of it instead of "
                    "%.2f%% — an index scale distributes points evenly whenever they happened, "
                    "so a six-hour outage would draw as one ordinary step"
                    % (len(instants), nine - eight, hour_percent))
        if abs(seen[0][1] - seen[1][1]) > 0.02 or abs(seen[0][2] - seen[1][2]) > 0.02:
            return False, (
                "the same two instants landed at different positions on a 2-instant band %r "
                "and an 8-instant band %r — a time scale places an instant by WHEN it "
                "happened and nothing else" % (seen[0][1:], seen[1][1:]))
        return True, ""
    check(
        "draw.percent_time() is a TIME scale and not the index scale beside it: midnight/"
        "midday/the day's final instant land at 0/50/100%, an hour is 1/24 of the band however "
        "many other instants are on it (so an outage draws as an outage), a DST day's own "
        "length is a parameter rather than a hardcoded 86400, and an instant outside the day is "
        "REJECTED rather than clamped onto an edge where it would invent a check-in "
        "(CFG-42, T-24-06-A, 24-06-PLAN.md Task 1)",
        _day_band_time_scale_places_by_when_not_by_index)

    def _day_band_night_window_shades_the_night_as_two_spans():
        day = draw.SECONDS_PER_DAY
        hour_percent = 100.0 / 24

        # 22:00-07:00 — a NIGHT window, which is what quiet hours
        # normally is, not an edge case.
        markup, _ = draw.day_band(
            _BAND_DAY_START, day, [], window=(_band_hour(22), _band_hour(7)))
        spans = _band_shapes(markup, "drawing-band-span")
        if len(spans) != 2:
            return False, (
                "expected a 22:00-07:00 window to shade TWO spans on a one-day band, got %d — "
                "one span from 22:00 back to 07:00 has a negative width, and the obvious "
                "repair (swap them) shades the whole DAY and leaves the night clear, which "
                "looks entirely plausible" % (len(spans),))
        widths = [_band_percent(el, "width") for el in spans]
        starts = [_band_percent(el, "x") for el in spans]
        if None in widths or None in starts:
            return False, "expected every span to carry percentage x/width, got %r" % (spans,)
        if abs(sum(widths) - 9 * hour_percent) > 0.02:
            return False, (
                "expected the two spans to cover nine hours (%.2f%%), got %.2f%% — %r"
                % (9 * hour_percent, sum(widths), list(zip(starts, widths))))
        if abs(min(starts)) > 1e-9:
            return False, (
                "expected the leading span to start at the band's own 00:00, got %r" % (starts,))
        ends = [s + w for s, w in zip(starts, widths)]
        if abs(max(ends) - 100.0) > 0.02:
            return False, (
                "expected the trailing span to reach the band's own 24:00, got %r" % (ends,))
        # And the middle of the day is NOT shaded: the failure this
        # check exists for is a band that shades 07:00-22:00.
        for start, width in zip(starts, widths):
            if start < 12 * hour_percent < start + width:
                return False, (
                    "midday falls inside a shaded span (%.2f%%..%.2f%%) — the night window has "
                    "been rendered inverted" % (start, start + width))

        # A daytime window is ONE span, so "always two" is not the fix.
        markup, _ = draw.day_band(
            _BAND_DAY_START, day, [], window=(_band_hour(9), _band_hour(17)))
        spans = _band_shapes(markup, "drawing-band-span")
        if len(spans) != 1:
            return False, "expected a 09:00-17:00 window to shade exactly one span, got %d" % (
                len(spans),)
        if abs(_band_percent(spans[0], "x") - 9 * hour_percent) > 0.02:
            return False, "expected the span to start at 09:00, got %r" % (spans[0],)
        if abs(_band_percent(spans[0], "width") - 8 * hour_percent) > 0.02:
            return False, "expected the span to be eight hours wide, got %r" % (spans[0],)

        # No window, a zero-width window and a window outside the day
        # all shade nothing. A zero-width window is never ACTIVE
        # (server/device_config.py's seconds_until_quiet_hours_end()
        # says so in as many words), so a hairline of shade would claim
        # a window the device does not honour.
        for label, window in (
                ("absent", None),
                ("zero-width", (_band_hour(9), _band_hour(9))),
                ("outside the day", (_BAND_DAY_START - 7200, _band_hour(7))),
                ("malformed", ("23:00", "07:00")),
                ("not a pair", 3)):
            markup, _ = draw.day_band(_BAND_DAY_START, day, [], window=window)
            spans = _band_shapes(markup, "drawing-band-span")
            if spans:
                return False, "expected a %s window to shade nothing, got %r" % (label, spans)
            if len(_band_shapes(markup, "drawing-band")) != 1:
                return False, "expected the band's own frame to survive a %s window" % (label,)
        return True, ""
    check(
        "the day band renders a wrapping night window (22:00-07:00) as TWO shaded spans "
        "covering nine hours, one flush to 00:00 and one flush to 24:00 with midday left "
        "clear — never one inverted span that would shade the middle of the day — while a "
        "daytime window stays one span and an absent/zero-width/out-of-day/malformed window "
        "shades nothing at all (CFG-42, 24-06-PLAN.md Task 1)",
        _day_band_night_window_shades_the_night_as_two_spans)

    def _day_band_collapses_crowded_marks_and_reports_exactly_how_many():
        day = draw.SECONDS_PER_DAY
        spacing = draw.DAY_BAND_MIN_MARK_SPACING_PERCENT
        ceiling = int(100.0 / spacing) + 1

        # A 30-minute cadence is 48 marks in the band's ~330px at the
        # 360px floor — about 7px apart, which is drawable. Nothing is
        # collapsed and the caller may caption the exact number.
        sparse = [_BAND_DAY_START + 1800 * i for i in range(48)]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, sparse)
        marks = _band_shapes(markup, "drawing-band-mark")
        if len(marks) != 48 or collapsed != 0:
            return False, (
                "expected 48 marks and 0 collapsed at a 30-minute cadence, got %d and %d"
                % (len(marks), collapsed))

        # A 60-second cadence is 1440 marks in the same 330px. Drawing
        # them all would let the reader believe the band shows 1440
        # things; the emitter collapses and SAYS how many.
        for cadence, total in ((60, 1440), (1, 86400)):
            instants = [_BAND_DAY_START + cadence * i for i in range(total)]
            markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
            marks = _band_shapes(markup, "drawing-band-mark")
            if len(marks) + collapsed != total:
                return False, (
                    "at a %ds cadence %d marks + %d collapsed != the %d instants supplied — "
                    "the number the caption is written from has to be exact"
                    % (cadence, len(marks), collapsed, total))
            if len(marks) > ceiling:
                return False, (
                    "at a %ds cadence the band drew %d marks, over the %d its own minimum "
                    "spacing allows — T-24-06-C is that the element count is bounded by the "
                    "band's WIDTH, never by the row count" % (cadence, len(marks), ceiling))
            positions = [_band_percent(el, "x") for el in marks]
            if positions != sorted(positions):
                return False, "expected the kept marks in chronological order, got %r" % (
                    positions[:8],)
            tight = [(a, b) for a, b in zip(positions, positions[1:])
                     if b - a < spacing - 0.011]
            if tight:
                return False, (
                    "at a %ds cadence two kept marks sit %.2f%% apart, under the %.2f%% "
                    "minimum — they would paint as one smear and the band would show fewer "
                    "things than it appears to" % (cadence, tight[0][1] - tight[0][0], spacing))
            # THE LOWER BOUND, and the half of this check the three
            # assertions above cannot see. They are all CEILINGS — at
            # most `ceiling` marks, none closer than the minimum — and
            # every one of them is satisfied perfectly by a band that
            # draws ONE mark at 00:00 and nothing else. That is not a
            # hypothetical: it is what this emitter does if its forward
            # pass compares each position against its immediate
            # PREDECESSOR rather than against the last KEPT mark, since
            # at a sub-minimum cadence every consecutive gap is under
            # the minimum and so nothing after the first is ever kept.
            # A day of 1 440 check-ins would then draw as one check-in
            # at midnight and an empty day after it — the band saying
            # the device died at 00:00 — with `collapsed` dutifully
            # reporting 1 439 and every ceiling above still green. The
            # mutation is recorded in 24-06-SUMMARY.md; these two
            # assertions are what it now fails.
            #
            # Both are consequences of the greedy rule rather than
            # chosen thresholds: a candidate lying a full
            # minimum-spacing past the last kept mark is kept BY
            # DEFINITION, so neither an interior gap nor the unmarked
            # tail at the band's end can reach the minimum plus one
            # cadence step. The 0.011 is the same allowance the `tight`
            # assertion above carries and is not slack in the rule: this
            # check reads POSITIONS OFF THE DRAWING, and an x attribute
            # carries two decimals, so a gap between two rounded
            # endpoints can differ from the true one by up to 0.01.
            step_percent = cadence / float(day) * 100
            last_instant = (instants[-1] - _BAND_DAY_START) / float(day) * 100
            if last_instant - positions[-1] >= spacing + 0.011:
                return False, (
                    "at a %ds cadence the kept marks stop at %.2f%% while the instants run to "
                    "%.2f%% — a tail of %.2f%% carrying %d check-ins drew nothing, though the "
                    "greedy rule keeps anything a full %.2f%% past the last kept mark. The band "
                    "would say the device stopped checking in"
                    % (cadence, positions[-1], last_instant, last_instant - positions[-1],
                       int((last_instant - positions[-1]) / step_percent), spacing))
            slack = [(a, b) for a, b in zip(positions, positions[1:])
                     if b - a > spacing + step_percent + 0.011]
            if slack:
                return False, (
                    "at a %ds cadence two kept marks sit %.2f%% apart, over the %.2f%% the "
                    "greedy rule allows — instants that had room for a mark of their own were "
                    "dropped, so the band shows a gap where the device was checking in "
                    "normally" % (cadence, slack[0][1] - slack[0][0], spacing + step_percent))

        # An instant the band cannot place counts as not-individually-
        # visible too, so a caller captioning from this number can never
        # name a total the drawing does not reach.
        mixed = [_BAND_DAY_START, _BAND_DAY_START - 60, "not a number", None,
                 _BAND_DAY_START + day // 2]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, mixed)
        marks = _band_shapes(markup, "drawing-band-mark")
        if len(marks) != 2 or collapsed != 3:
            return False, (
                "expected 2 marks and 3 unplaceable instants reported, got %d and %d"
                % (len(marks), collapsed))
        # Every mark is centred on its instant rather than hung to the
        # right of it: a 23:59 mark whose LEFT edge were the instant
        # would sit entirely outside the canvas. Asserted on the band
        # just drawn, which has two marks — asserting it on an empty
        # band is a loop that runs zero times and proves nothing.
        offset = -draw.DAY_BAND_MARK_WIDTH_PX / 2.0
        for element in marks:
            if _band_attr(element, "transform") != "translate(%.2f 0)" % offset:
                return False, "expected every mark centred on its instant, got %r" % (element,)

        markup, collapsed = draw.day_band(_BAND_DAY_START, day, 17)
        if collapsed != 0 or _band_shapes(markup, "drawing-band-mark"):
            return False, "expected a non-iterable series to draw no marks and report 0"
        return True, ""
    check(
        "the day band collapses marks closer than its own stated minimum spacing and returns "
        "EXACTLY how many it hid — 48 marks at a 30-minute cadence with nothing collapsed, a "
        "60-second and a 1-second cadence both bounded by the band's width rather than the row "
        "count (T-24-06-C), no two kept marks under the minimum apart, and an unplaceable "
        "instant counted too so a caption built from the number can never claim a total the "
        "drawing does not reach (T-24-06-B, 24-06-PLAN.md Task 1)",
        _day_band_collapses_crowded_marks_and_reports_exactly_how_many)

    def _day_band_emits_only_registered_classes_and_no_colour():
        markup, _ = draw.day_band(
            _BAND_DAY_START, draw.SECONDS_PER_DAY,
            [_band_hour(h) for h in (1, 5, 9, 13, 17, 21)],
            window=(_band_hour(23), _band_hour(7)), label="the day")
        for constant in (draw.DRAWING_BAND_CLASS, draw.DRAWING_BAND_SPAN_CLASS,
                         draw.DRAWING_BAND_MARK_CLASS):
            if constant not in draw.DRAWING_CLASSES:
                return False, (
                    "the band's class %r is not in draw.DRAWING_CLASSES, so the guard that "
                    "every emitted class resolves to a real selector cannot see it — a class "
                    "that exists in Python and nowhere in CSS paints nothing at all"
                    % (constant,))
        for class_name in re.findall(r'class="([^"]*)"', markup):
            for token in class_name.split():
                if token not in draw.DRAWING_CLASSES:
                    return False, (
                        "the band emitted class %r, which is not one of draw.py's own named "
                        "constants" % (token,))
        for forbidden in ("url(", "#", "rgb(", "style=", "<linearGradient"):
            if forbidden in markup:
                return False, (
                    "the band's markup carries %r — a colour decided in Python is correct in "
                    "one theme only, and an external reference is banned outright"
                    % (forbidden,))
        if 'role="group"' not in markup or 'aria-label="the day"' not in markup:
            return False, (
                "expected a labelled band: it is the only statement of its data, so it is not "
                "aria-hidden the way the ring beside its own printed percentage is")
        unlabelled, _ = draw.day_band(_BAND_DAY_START, draw.SECONDS_PER_DAY, [])
        if 'aria-hidden="true"' not in unlabelled:
            return False, "expected an unlabelled band to be hidden rather than an unnamed group"
        return True, ""
    check(
        "every class the day band emits is one of companion/draw.py's own named constants and "
        "is registered in DRAWING_CLASSES (so the stylesheet-resolution guard can see it), the "
        "markup carries no colour literal, no url() reference and no inline style, and a band "
        "supplied with a label announces itself as a named group rather than being hidden "
        "(CFG-39/CFG-42, 24-06-PLAN.md Task 1)",
        _day_band_emits_only_registered_classes_and_no_colour)

    # --- 24-06-PLAN.md Task 2 (CFG-42): the day band on Home -------------
    #
    # The band's three risks, one check each: that it shows the wrong DAY
    # (the Paris/UTC boundary), that it shows the wrong WINDOW (quiet
    # hours), and that it disappears rather than degrades (an empty day,
    # an absent database). The "no check-ins" case is a distinct STATE and
    # not an error: an absent section is indistinguishable from an unbuilt
    # feature, and this page already draws that distinction elsewhere (the
    # battery tile's "No reading yet" verdict rather than a zero).

    def _home_day_band_section(rendered):
        """The day band's <section> only, or None.

        Sliced out rather than searched for in the whole page because two
        of the assertions below are about what the caption does NOT say,
        and "quiet hours" appears elsewhere on this page in the frame
        strip's own switch. A page-wide `"quiet" not in rendered` would be
        green only on a page that had lost the strip.
        """
        opened = re.search(r'<section class="[^"]*\bday-band\b[^"]*"', rendered)
        if opened is None:
            return None
        end = rendered.index("</section>", opened.start())
        return rendered[opened.start():end + len("</section>")]

    def _home_band_marks(section):
        return re.findall(r'<rect class="drawing-band-mark"[^>]*/>', section)

    def _home_band_spans(section):
        return re.findall(r'<rect class="drawing-band-span"[^>]*/>', section)

    def _home_band_ctx(tmp, now, checkins, config=None):
        from server import history_db as _hdb
        with _hdb.open_db(tmp) as conn:
            for ts in checkins:
                _hdb.record_device_health(conn, ts, battery_mv=3750)
        return {
            "state_dir": tmp, "now": now,
            "last_checkin_ts": checkins[-1] if checkins else None,
            "device_config": config or {"wake_interval_s": 900, "display_enabled": True},
            "health_state": {"device_state": "ok", "pipeline_state": "ok",
                             "battery_state": "ok", "device_detail_html": "",
                             "pipeline_html": ""},
            "simple_mode": False,
        }

    def _home_day_band_renders_the_day_and_says_what_it_shows():
        from companion.pages import home_page
        # Paris 14:00 on 2026-08-27 (CEST, UTC+2), so the band's day runs
        # 2026-08-26T22:00Z .. 2026-08-27T22:00Z.
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("band-day")
        try:
            # 08:00, 12:00 and 13:00 Paris — two of them an hour apart, so
            # the time scale's own property is visible on the real page and
            # not only in the unit check above.
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
                "2026-08-27T11:00:00+00:00",
            ])
            rendered = home_page.render(ctx)
            section = _home_day_band_section(rendered)
            if section is None:
                return False, "expected a day-band section on Home, got none"
            marks = _home_band_marks(section)
            if len(marks) != 3:
                return False, "expected one mark per check-in (3), got %d" % (len(marks),)
            xs = sorted(float(re.search(r'x="([\d.]+)%"', el).group(1)) for el in marks)
            hour = 100.0 / 24
            for got, want_hour in zip(xs, (8, 12, 13)):
                if abs(got - want_hour * hour) > 0.02:
                    return False, (
                        "expected the %02d:00 Paris check-in at %.2f%%, got %.2f%% — the band's "
                        "marks are placed by the PARIS clock, which is what every other date on "
                        "this page uses" % (want_hour, want_hour * hour, got))
            # The caption names the day it is showing. A band captioned
            # only "today" cannot be checked against the row beneath it.
            if "2026-08-27" not in section:
                return False, "expected the caption to name the Paris day it draws, got %r" % (
                    section,)
            if "3" not in re.sub(r"<[^>]*>", " ", section):
                return False, "expected the caption to state the check-in count as text"

            # THE EMPTY DAY IS A STATE, NOT AN ABSENCE.
            empty = _mkstate("band-empty")
            try:
                empty_ctx = _home_band_ctx(empty, now, [])
                # A check-in on a DIFFERENT day, so the table is not empty
                # and the emptiness is the band's bucketing rather than an
                # unreadable database.
                from server import history_db as _hdb
                with _hdb.open_db(empty) as conn:
                    _hdb.record_device_health(conn, "2026-08-20T10:00:00+00:00", battery_mv=3700)
                rendered_empty = home_page.render(empty_ctx)
                empty_section = _home_day_band_section(rendered_empty)
                if empty_section is None:
                    return False, (
                        "expected the band section to survive a day with no check-ins — an "
                        "absent section reads as an unbuilt feature, an empty band reads as "
                        "no activity, and those are different statements")
                if _home_band_marks(empty_section):
                    return False, "expected no marks on an empty day, got %r" % (
                        _home_band_marks(empty_section),)
                if 'class="drawing-band"' not in empty_section:
                    return False, "expected the band's own frame to render on an empty day"
                if "2026-08-27" not in empty_section:
                    return False, "expected the empty band's caption to name the day too"
            finally:
                shutil.rmtree(empty, ignore_errors=True)

            # THE COLLAPSE, CAPTIONED (T-24-06-B). The band above drew
            # three well-separated marks and must NOT carry the merge
            # sentence — a caption that always admitted a collapse would
            # be as untrue as one that never did. A day at a one-minute
            # cadence must carry it, because at that density the band
            # genuinely cannot show each check-in separately and a reader
            # counting marks would otherwise conclude it lost some.
            if home_page.DAY_BAND_COLLAPSED_TEXT in section:
                return False, (
                    "the band collapsed nothing (3 marks for 3 check-ins) yet its caption said "
                    "marks were merged — a caption that always admits a collapse tells the "
                    "reader nothing and is untrue on every sparse day")
            dense = _mkstate("band-dense")
            try:
                from server import history_db as _hdb
                minutes = ["2026-08-27T%02d:%02d:00+00:00" % (6 + i // 60, i % 60)
                           for i in range(300)]
                dense_ctx = _home_band_ctx(dense, now, minutes)
                dense_section = _home_day_band_section(home_page.render(dense_ctx))
                if dense_section is None:
                    return False, "expected a band on a dense day"
                dense_marks = _home_band_marks(dense_section)
                if len(dense_marks) >= len(minutes):
                    return False, (
                        "expected a one-minute cadence to collapse (300 check-ins cannot be 300 "
                        "distinguishable marks in ~330px), got %d marks" % (len(dense_marks),))
                if home_page.DAY_BAND_COLLAPSED_TEXT not in dense_section:
                    return False, (
                        "the band drew %d marks for %d check-ins and its caption did not say "
                        "they were merged — the drawing dropping marks silently and the caption "
                        "printing a total are the two halves of one lie (T-24-06-B)"
                        % (len(dense_marks), len(minutes)))
                dense_text = re.sub(r"<[^>]*>", " ", dense_section)
                if str(len(minutes)) not in dense_text:
                    return False, (
                        "expected the true total still printed as TEXT beside the merge "
                        "sentence — the count is honest, only the COUNTING of marks is not")
            finally:
                shutil.rmtree(dense, ignore_errors=True)

            # NO DATABASE AT ALL: no band, no raise, a page that still
            # renders (T-24-06-D).
            #
            # The unreadable database is made unreadable by putting a
            # DIRECTORY where history.db belongs, not by chmod: this
            # harness runs as root in its container, where a 0o500 state
            # dir is not read-only at all (the same reason the four WR-11
            # checks in companion/test_companion_app.py fail here and
            # pass in CI). sqlite cannot open a directory whoever you
            # are, so this check measures the same degradation in both
            # environments.
            absent = _mkstate("band-nodb")
            try:
                absent_ctx = _home_band_ctx(absent, now, [])
                for name in os.listdir(absent):
                    path = os.path.join(absent, name)
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                os.mkdir(os.path.join(absent, "history.db"))
                rendered_absent = home_page.render(absent_ctx)
                if '<h1 class="page-title">' not in rendered_absent:
                    return False, "expected Home to render with history.db absent"
                if _home_day_band_section(rendered_absent) is not None:
                    return False, (
                        "expected NO band with history.db unreadable — an empty band there "
                        "would claim the device made no check-ins when nothing was read")
            finally:
                shutil.rmtree(absent, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band draws one mark per check-in at its PARIS clock position, captions the "
        "Paris day it shows and states the count as text; a day with no check-ins still renders "
        "the band and its frame with a caption naming the day (an absent section would read as "
        "an unbuilt feature, an empty band reads as no activity); and with history.db unreadable "
        "the page renders with no band at all rather than an empty one claiming no check-ins "
        "(CFG-42, T-24-06-D, 24-06-PLAN.md Task 2)",
        _home_day_band_renders_the_day_and_says_what_it_shows)

    def _home_day_band_shades_quiet_hours_only_when_configured():
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        checkins = ["2026-08-27T10:00:00+00:00"]
        hour = 100.0 / 24
        tmp = _mkstate("band-quiet")
        try:
            # The DEFAULT night window, and the case a naive span renders
            # inverted: 23:00-07:00 wraps midnight.
            ctx = _home_band_ctx(tmp, now, checkins, config={
                "wake_interval_s": 900, "display_enabled": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
            })
            section = _home_day_band_section(home_page.render(ctx))
            if section is None:
                return False, "expected a day-band section"
            spans = _home_band_spans(section)
            if len(spans) != 2:
                return False, (
                    "expected the default 23:00-07:00 quiet hours to shade TWO spans on a "
                    "one-day band, got %d — one span would shade the middle of the DAY and "
                    "leave the night clear" % (len(spans),))
            widths = [float(re.search(r'width="([\d.]+)%"', el).group(1)) for el in spans]
            if abs(sum(widths) - 8 * hour) > 0.05:
                return False, (
                    "expected the shaded spans to cover the window's eight hours (%.2f%%), got "
                    "%.2f%%" % (8 * hour, sum(widths)))
            text = re.sub(r"<[^>]*>", " ", section)
            if "23:00" not in text or "07:00" not in text:
                return False, (
                    "expected the caption to name the shaded window's own hours, got %r" % (text,))

            # DISABLED: nothing shaded, and the caption does not mention a
            # window the device is not honouring.
            off = _mkstate("band-quiet-off")
            try:
                off_ctx = _home_band_ctx(off, now, checkins, config={
                    "wake_interval_s": 900, "display_enabled": True,
                    "quiet_hours_enabled": False,
                    "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                    "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
                })
                off_section = _home_day_band_section(home_page.render(off_ctx))
                if off_section is None:
                    return False, "expected the band to render with quiet hours disabled"
                if _home_band_spans(off_section):
                    return False, (
                        "expected zero shaded spans with quiet hours disabled, got %r"
                        % (_home_band_spans(off_section),))
                off_text = re.sub(r"<[^>]*>", " ", off_section).lower()
                if "quiet" in off_text or "23:00" in off_text:
                    return False, (
                        "expected the band's caption to say nothing about quiet hours when they "
                        "are off — a legend for a span that is not drawn describes a band the "
                        "reader is not looking at. Got %r" % (off_text,))
                if not _home_band_marks(off_section):
                    return False, "expected the check-in marks to survive quiet hours being off"
            finally:
                shutil.rmtree(off, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band shades the CONFIGURED quiet-hours window — the default 23:00-07:00 "
        "wrapping night window as two spans covering its eight hours, named in the caption — and "
        "with quiet hours disabled shades nothing and says nothing about them, while still "
        "drawing the day's check-ins (CFG-42/D-03, 24-06-PLAN.md Task 2)",
        _home_day_band_shades_quiet_hours_only_when_configured)

    def _home_day_band_buckets_by_paris_day_and_costs_one_read():
        from companion.pages import home_page
        from server import history_db as _hdb
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("band-boundary")
        try:
            # THE BOUNDARY THIS BREAKS AT IF IT BREAKS. Paris is UTC+1/+2
            # and so never BEHIND UTC — 24-06-PLAN.md Task 2's own
            # acceptance criterion names "23:30 Paris on a date whose UTC
            # instant falls on the next day", which cannot occur for
            # Europe/Paris. The real case is its mirror, and it is the
            # same defect: 00:30 Paris is 22:30 UTC on the PREVIOUS day,
            # so a band bucketed by the UTC date drops it from today and
            # picks up tomorrow's 00:30 instead. Both directions below.
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-26T21:30:00+00:00",  # Paris 2026-08-26 23:30 — yesterday
                "2026-08-26T22:30:00+00:00",  # Paris 2026-08-27 00:30 — TODAY
                "2026-08-27T22:30:00+00:00",  # Paris 2026-08-28 00:30 — tomorrow
            ])
            section = _home_day_band_section(home_page.render(ctx))
            if section is None:
                return False, "expected a day-band section"
            marks = _home_band_marks(section)
            if len(marks) != 1:
                return False, (
                    "expected exactly ONE of the three check-ins on the 2026-08-27 Paris band, "
                    "got %d — under a UTC date bucket the 22:30Z check-in (Paris 00:30 today) "
                    "drops off and the 2026-08-27T22:30Z one (Paris 00:30 TOMORROW) appears "
                    "instead, which is the same count from the wrong rows" % (len(marks),))
            got = float(re.search(r'x="([\d.]+)%"', marks[0]).group(1))
            want = 0.5 * (100.0 / 24)  # 00:30 Paris
            if abs(got - want) > 0.02:
                return False, (
                    "expected the 00:30 Paris check-in at %.2f%%, got %.2f%%" % (want, got))

            # A 25-HOUR PARIS DAY. 2026-10-25 is the EU autumn transition,
            # so the band is 25 hours wide and midday sits at 52.00%, not
            # at the 54.17% a hardcoded 86400 would put it at.
            dst = _mkstate("band-dst")
            try:
                dst_ctx = _home_band_ctx(
                    dst, "2026-10-25T12:00:00+00:00", ["2026-10-25T11:00:00+00:00"])
                dst_section = _home_day_band_section(home_page.render(dst_ctx))
                dst_marks = _home_band_marks(dst_section or "")
                if len(dst_marks) != 1:
                    return False, "expected one mark on the DST band, got %d" % (len(dst_marks),)
                dst_got = float(re.search(r'x="([\d.]+)%"', dst_marks[0]).group(1))
                if abs(dst_got - 52.0) > 0.02:
                    return False, (
                        "on the 25-hour Paris day 2026-10-25 the 12:00 check-in belongs at "
                        "52.00%% of the band, got %.2f%% — a hardcoded 86400 puts it at 54.17%% "
                        "and leaves an hour of the band unreachable" % (dst_got,))
            finally:
                shutil.rmtree(dst, ignore_errors=True)

            # ONE READ, REUSED (D-20), MEASURED. render() made two
            # history.db reads before this plan; the band adds exactly
            # one, and a band that re-queried per section would show up
            # here as three or more.
            counted = _mkstate("band-reads")
            try:
                read_ctx = _home_band_ctx(counted, now, ["2026-08-27T10:00:00+00:00"])
                opened = []
                real_open = _hdb.open_db
                def _counting_open(state_dir):
                    opened.append(state_dir)
                    return real_open(state_dir)
                _hdb.open_db = _counting_open
                try:
                    rendered = home_page.render(read_ctx)
                finally:
                    _hdb.open_db = real_open
                if len(opened) != 3:
                    return False, (
                        "expected render() to make exactly 3 history.db reads — the 2 it made "
                        "before this plan (recent flights, latest battery) plus the band's one "
                        "— got %d. 'One read, reused' is measured here, not assumed"
                        % (len(opened),))
                # The frame verdict still appears exactly once on the page
                # (_status_tiles_html()'s own recorded property, which a
                # new section carrying a state word could quietly break).
                verdicts = [v for v in home_page.FRAME_STATE_TEXT.values()
                            if rendered.count(v)]
                for verdict in verdicts:
                    if rendered.count(verdict) != 1:
                        return False, (
                            "expected the frame verdict %r exactly once on Home, got %d"
                            % (verdict, rendered.count(verdict)))
                if len(verdicts) != 1:
                    return False, (
                        "expected exactly one frame verdict rendered on Home, got %r" % (
                            verdicts,))
            finally:
                shutil.rmtree(counted, ignore_errors=True)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's day band buckets check-ins by the PARIS day — a 22:30Z check-in (Paris 00:30 "
        "today) is on the band and a 2026-08-27T22:30Z one (Paris 00:30 tomorrow) is not, the "
        "mirror of the boundary 24-06-PLAN.md Task 2 named since Paris is never behind UTC — "
        "and spans a real 25-hour Paris day so midday lands at 52.00% rather than the 54.17% a "
        "hardcoded 86400 would give; it costs render() exactly one history.db read more than "
        "the two it made before, measured, and the frame verdict still appears exactly once "
        "(CFG-42/D-20, 24-06-PLAN.md Task 2)",
        _home_day_band_buckets_by_paris_day_and_costs_one_read)

    # --- 24-08-PLAN.md Task 1 (CFG-44): D4's hero, assembled from calls -
    #
    # "The Home hero the others feed" is a STRUCTURAL claim with exactly
    # one failure mode: a hero that looks composed but carries its own
    # copies of the ring and the band, which then drift from the
    # originals the first time either is fixed. This codebase has already
    # paid for that once (companion/battery.py exists because
    # battery_percent() had been copied), so the checks here are written
    # against that failure rather than against the markup's shape.

    def _home_hero_inner(rendered):
        """The hero container's own inner markup, or None when the page
        renders no hero at all.

        A BALANCED SCAN, never `rendered.index("</div>")`: the hero holds
        sections that hold divs of their own, so the first closing tag
        after the opening one belongs to a descendant. A slicer that took
        it would return a fragment that happened to start with the strip
        and stop somewhere inside the tiles, and every "is inside the
        hero" assertion below would then be measuring a shorter string
        than its own message names — green for the wrong reason, which is
        the one way a containment check fails silently.
        """
        from companion.pages import home_page
        opened = re.search(
            r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered)
        if opened is None:
            return None
        depth = 0
        for token in re.finditer(r"<div\b|</div>", rendered[opened.start():]):
            depth += 1 if token.group(0) == "<div" else -1
            if depth == 0:
                return rendered[opened.end():opened.start() + token.start()]
        return None

    def _home_top_is_one_composition_holding_the_ring_and_the_band():
        import inspect
        import companion.draw as _draw
        import companion.i18n as _i18n
        import companion.prefs as _prefs
        from companion.pages import home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-compose")
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ])
            ctx["gallery_entries"] = ["2026-08-27T11-50-00+00-00.png"]
            rendered = home_page.render(ctx)

            # ONE hero. Two containers would be the phase-20 collision
            # back in a new costume (22-07 had to rename a second thing
            # called "Frame" on this very page).
            opens = len(re.findall(
                r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered))
            if opens != 1:
                return False, (
                    "expected exactly one hero container on Home, got %d" % (opens,))
            inner = _home_hero_inner(rendered)
            if inner is None:
                return False, "expected the hero container to open and close"

            # Its three parts, each still rendered by the builder that
            # owns it. The strip is matched on the class the SHARED
            # helper emits, so a hero that inlined a second rendering of
            # it would have to reproduce that class to pass — and would
            # then fail the count below.
            for label, pattern in (
                    ("the shared Frame strip",
                     r'class="frame-strip stat-tile stat-tile--accent"'),
                    ("the three status tiles",
                     r'class="dashboard-grid home-status-grid"'),
                    ("the day band", r'<section class="[^"]*\bday-band\b')):
                if re.search(pattern, inner) is None:
                    return False, (
                        "expected %s inside the hero — a composition that does not contain "
                        "its parts is a wrapper, not a hero (looked for %r)"
                        % (label, pattern))
            if rendered.count('class="frame-strip stat-tile stat-tile--accent"') != 1:
                return False, (
                    "expected the shared Frame strip rendered exactly once — the hero wraps "
                    "the shared component, it never inlines a second rendering of it")

            # What the hero is NOT. The picture row is the page's own
            # second half and sits after it; a hero that swallowed it
            # would make every 360px stacking measurement below about
            # the whole page instead of the composition.
            for absent in ("home-picture-row", "preview-frame", "recent-flight"):
                if absent in inner:
                    return False, (
                        "expected %r outside the hero — the hero is Home's TOP, not its "
                        "whole body" % (absent,))
            if rendered.index('class="home-columns home-picture-row"') < rendered.index(
                    '<div class="%s"' % home_page.HERO_CLASS):
                return False, "expected the hero to precede the picture row"

            # EXACTLY ONE RING AND EXACTLY ONE BAND, both the hero's.
            # The needles are whole class ATTRIBUTES rather than bare
            # class names: the band frame's own name is a prefix of the
            # span's and the mark's, so a substring test would count
            # three things as the frame (the trap
            # companion/test_companion_app.py:4134 records from the
            # other direction).
            for label, needle in (
                    ("battery ring value arc",
                     'class="%s"' % _draw.DRAWING_RING_VALUE_CLASS),
                    ("day band frame", 'class="%s"' % _draw.DRAWING_BAND_CLASS)):
                if rendered.count(needle) != 1:
                    return False, (
                        "expected exactly one %s on Home, got %d"
                        % (label, rendered.count(needle)))
                if needle not in inner:
                    return False, (
                        "expected the %s INSIDE the hero — CFG-44's hero is the composition "
                        "the drawings feed, not a container beside them" % (label,))

            # NO GEOMETRY AND NO SECOND ESTIMATE IN THIS MODULE. The
            # boundary regex on the estimator is the point: a bare
            # `battery_percent(` is a local copy, while the qualified
            # call through companion/battery.py is the one home the
            # allow-list permits.
            source = inspect.getsource(home_page)
            for token in ("stroke-dasharray", "BATTERY_FULL_MV", "4200", "3300"):
                if token in source:
                    return False, (
                        "companion/pages/home_page.py contains %r — geometry and battery "
                        "arithmetic belong to the shared modules, and a page that carries "
                        "either has started a second copy" % (token,))
            if re.search(r"(?<![-\w.])battery_percent\s*\(", source) is not None:
                return False, (
                    "companion/pages/home_page.py names battery_percent( with no module "
                    "qualifier — either a local definition or a bare `from companion.battery "
                    "import` — and both make the estimator read as this page's own. It has "
                    "exactly two allowed homes and this module is not one of them, so every "
                    "call site here says so")
            for call in ("draw.ring_gauge(", "draw.day_band("):
                if call not in source:
                    return False, (
                        "expected %r in home_page.py — the hero is assembled from CALLS into "
                        "the shared emitters" % (call,))

            # THE RECORDED FIXED BUG (20-RESEARCH.md Pitfall 3), re-asked
            # in BOTH languages because a hero is precisely the shape
            # that reintroduces it and French is a separate string table
            # that could disagree.
            for lang in ("en", "fr"):
                _prefs.set_request_prefs(lang=lang)
                try:
                    page = home_page.render(ctx)
                    seen = [_i18n.t(v) for v in home_page.FRAME_STATE_TEXT.values()
                            if page.count(_i18n.t(v))]
                    if len(seen) != 1:
                        return False, (
                            "in %s expected exactly one frame verdict on Home, got %r"
                            % (lang, seen))
                    if page.count(seen[0]) != 1:
                        return False, (
                            "in %s expected the frame verdict %r exactly once on Home, got "
                            "%d — the duplicated verdict 21-04 deleted a whole status-card "
                            "builder to remove" % (lang, seen[0], page.count(seen[0])))
                finally:
                    _prefs.set_request_prefs(lang="en")
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "Home's top is ONE composition: a single hero container holds the shared Frame strip "
        "(rendered once, unforked), the three status tiles carrying the battery ring, and the "
        "day band — the picture row stays outside it, the ring and the band each appear exactly "
        "once and both inside the hero, home_page.py carries no ring geometry and no second "
        "battery estimate (an unqualified battery_percent( is refused by a boundary regex), and "
        "the frame verdict still appears exactly once in BOTH languages (CFG-44, 24-08-PLAN.md "
        "Task 1)",
        _home_top_is_one_composition_holding_the_ring_and_the_band)

    # --- 24-08-PLAN.md Task 2 (CFG-44): "fed by", proven ---------------
    #
    # Two checks with two different jobs, named for what they prove so a
    # later tidy-up does not read them as duplicate coverage of the
    # hero's markup. The first is STRUCTURAL: every class the hero's two
    # drawings carry is one of companion/draw.py's OWN named constants,
    # read from that module at check time and never restated here — a
    # literal would keep passing against a forked copy that still used
    # the old string, which is precisely the failure being tested for.
    # The second is BEHAVIOURAL, and it is the one CFG-44 actually asks
    # for: change a shared emitter and watch BOTH the hero and the page
    # the emitter was borrowed from move with it.

    def _classes_inside_svg(markup, opening_class):
        """The set of class attributes emitted INSIDE the first <svg>
        whose own class begins with `opening_class`, or None when there
        is no such element.

        Non-greedy to the first closing tag, which is correct for both
        drawings this is asked about: neither nests an <svg>. A drawing
        that did would need a balanced scan, the same way the hero's own
        container does.
        """
        svg = re.search(
            r'<svg class="%s[^"]*"[^>]*>(.*?)</svg>' % re.escape(opening_class),
            markup, re.S)
        if svg is None:
            return None
        return set(re.findall(r'class="([^"]*)"', svg.group(1)))

    def _the_heros_ring_is_the_emitter_healths_ring_is():
        import ast
        import inspect
        import textwrap
        import companion.draw as _draw
        from companion.pages import health_page, home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-vocab")
        health_tmp = _mkstate("hero-vocab-health")
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ], config={
                "wake_interval_s": 900, "display_enabled": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
                "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
            })
            rendered = home_page.render(ctx)
            hero = _home_hero_inner(rendered)
            if hero is None:
                return False, "expected a hero container on Home"
            with history_db.open_db(health_tmp) as conn:
                for minute, mv in ((50, 3600), (55, 3690)):
                    history_db.record_device_health(
                        conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
            health_rendered = health_page.render({"state_dir": health_tmp, "now": now})

            # ONE RING, TWO PAGES. The two rings' class vocabularies are
            # COMPUTED from the markup rather than listed here, so this
            # cannot drift into a hand-maintained copy of the emitter's
            # own list — which would be the same defect one level up.
            hero_ring = _classes_inside_svg(hero, _draw.DRAWING_FIGURE_CLASS)
            health_ring = _classes_inside_svg(health_rendered, _draw.DRAWING_FIGURE_CLASS)
            if not hero_ring:
                return False, "found no ring inside Home's hero"
            if not health_ring:
                return False, "found no ring on Health"
            if hero_ring != health_ring:
                return False, (
                    "the hero's ring and Health's carry different class vocabularies (%r "
                    "against %r) — one drawing at two sizes emits one vocabulary; two "
                    "vocabularies means two components"
                    % (sorted(hero_ring), sorted(health_ring)))

            # THE BAND, AND ITS FLOOR. "Every class is one of the shared
            # module's own" is satisfied by a band that drew nothing but
            # its frame, so the distinct-element floor is asserted
            # alongside it: the frame, the shaded quiet-hours span and
            # the check-in marks are three different shapes, and a band
            # that lost two of them would still pass the vocabulary half
            # on its own.
            hero_band = _classes_inside_svg(hero, _draw.DRAWING_CANVAS_CLASS)
            if not hero_band:
                return False, "found no day band inside Home's hero"
            if len(hero_band) < 3:
                return False, (
                    "the hero's band draws only %d kind(s) of shape (%r) — with a quiet-hours "
                    "window configured and two check-ins on the day it owes three: its own "
                    "frame, the shaded span and the marks" % (len(hero_band), sorted(hero_band)))

            # EVERY ONE OF THEM A NAMED CONSTANT OF THE SHARED MODULE.
            # A forked copy is free to emit any string it likes; this is
            # what refuses the ones draw.py does not own.
            for class_name in sorted(hero_ring | hero_band):
                for token in class_name.split():
                    if token not in _draw.DRAWING_CLASSES:
                        return False, (
                            "the hero emits the drawing class %r, which companion/draw.py does "
                            "not name — a class the shared module does not own came from "
                            "somewhere else" % (token,))

            # THE PAGE MODULE RESTATES NONE OF THEM, AND NEITHER DOES
            # THIS CHECK. That is the fork's own fingerprint: markup
            # emitted by hand has to write these strings down somewhere.
            #
            # A BARE SUBSTRING SCAN CANNOT ASK THIS, and finding that out
            # cost this check a draft: draw.DRAWING_GRID_CLASS is the
            # single word "drawing", which appears in home_page.py's
            # PROSE ("a drawing that implied calibration would out-claim
            # the number it sits beside") and in this check's own failure
            # messages. A scan that reads English as evidence is the
            # phase's own recorded trap — check your own prose does not
            # satisfy your own grep — so what is scanned is string
            # LITERALS only, docstrings excluded, and each one is asked
            # two precise questions instead of one loose one.
            def _restated_drawing_class(source):
                tree = ast.parse(source)
                docs = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Module, ast.ClassDef,
                                         ast.FunctionDef, ast.AsyncFunctionDef)):
                        if ast.get_docstring(node, clean=False) is not None:
                            docs.add(id(node.body[0].value))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Constant) or id(node) in docs:
                        continue
                    if not isinstance(node.value, str):
                        continue
                    # Question one: is the literal a class name outright
                    # (the `'<circle class="%s"' % "..."` shape)?
                    if node.value in _draw.DRAWING_CLASSES:
                        return node.value
                    # Question two: does it write one into a class
                    # attribute (the inlined-markup shape)?
                    for attribute in re.findall(r'class="([^"]*)"', node.value):
                        for token in attribute.split():
                            if token in _draw.DRAWING_CLASSES:
                                return token
                return None

            restated = _restated_drawing_class(inspect.getsource(home_page))
            if restated is not None:
                return False, (
                    "companion/pages/home_page.py writes the drawing class %r into a string "
                    "literal — the page calls the emitters, it does not restate their markup"
                    % (restated,))
            restated = _restated_drawing_class(textwrap.dedent(
                inspect.getsource(_the_heros_ring_is_the_emitter_healths_ring_is)
                + inspect.getsource(_classes_inside_svg)))
            if restated is not None:
                return False, (
                    "this check writes the drawing class %r into a literal instead of reading "
                    "it from companion/draw.py — rename the constant and a literal here goes "
                    "on passing against the fork" % (restated,))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(health_tmp, ignore_errors=True)
    check(
        "the hero's battery ring is the same emitter Health's ring is — the two pages' rings "
        "carry one class vocabulary, computed from the markup rather than listed; the hero's "
        "day band draws three different shapes and not one; every class either of them emits is "
        "a constant companion/draw.py itself names; and neither companion/pages/home_page.py nor "
        "this check writes any of those strings down, because a literal goes on passing against "
        "a forked copy that still uses the old one (CFG-44, 24-08-PLAN.md Task 2)",
        _the_heros_ring_is_the_emitter_healths_ring_is)

    def _breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from():
        import companion.draw as _draw
        from companion.pages import health_page, home_page
        now = "2026-08-27T12:00:00+00:00"
        tmp = _mkstate("hero-link")
        health_tmp = _mkstate("hero-link-health")
        # Not a member of DRAWING_CLASSES and not a substring of one, so
        # "the sentinel arrived" and "the original left" are two
        # independent readings rather than one.
        sentinel = "skypane-emitter-under-mutation"
        try:
            ctx = _home_band_ctx(tmp, now, [
                "2026-08-27T06:00:00+00:00",
                "2026-08-27T10:00:00+00:00",
            ])
            with history_db.open_db(health_tmp) as conn:
                for minute, mv in ((50, 3600), (55, 3690)):
                    history_db.record_device_health(
                        conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
            health_ctx = {"state_dir": health_tmp, "now": now}
            home_before = home_page.render(ctx)
            health_before = health_page.render(health_ctx)

            def _mutated(attr):
                """Both pages rendered with one of draw.py's class
                constants replaced, the constant restored afterwards
                whatever happens."""
                original = getattr(_draw, attr)
                setattr(_draw, attr, sentinel)
                try:
                    return original, home_page.render(ctx), health_page.render(health_ctx)
                finally:
                    setattr(_draw, attr, original)

            # THE RING: one definition, two pages. A hero built from its
            # own copy would still carry the ORIGINAL class here while
            # Health carried the sentinel — which is exactly the drift
            # CFG-44 is about, and is invisible to any check that only
            # looks at the markup as shipped.
            original, home_after, health_after = _mutated("DRAWING_RING_VALUE_CLASS")
            for label, before, after in (("the hero", home_before, home_after),
                                         ("Health", health_before, health_after)):
                if sentinel not in after:
                    return False, (
                        "a change inside the shared ring emitter did not reach %s — it draws "
                        "its own ring, not the shared one" % (label,))
                if 'class="%s"' % original in after:
                    return False, (
                        "%s still carries the ring's original class after the emitter was "
                        "changed — part of that drawing is a copy" % (label,))
                if after == before:
                    return False, "%s rendered identically under the mutation" % (label,)

            # THE MUTATION WAS TARGETED, not a global perturbation: the
            # band is Home's alone, so changing it must move the hero and
            # leave Health BYTE-IDENTICAL. Without this, "both pages
            # changed" above would be worth much less.
            original, home_after, health_after = _mutated("DRAWING_BAND_MARK_CLASS")
            if sentinel not in home_after:
                return False, (
                    "a change inside the shared band emitter did not reach the hero — its band "
                    "is a copy")
            if 'class="%s"' % original in home_after:
                return False, (
                    "the hero still carries the band mark's original class after the emitter "
                    "was changed — part of that drawing is a copy")
            if health_after != health_before:
                return False, (
                    "changing the band emitter also changed Health, which draws no band — the "
                    "mutation is not measuring what it names")

            # THE RESTORE IS PART OF THE CHECK. A mutation left behind
            # would make every later check in this file measure a
            # sabotaged module, and the failure would land somewhere
            # else entirely.
            if home_page.render(ctx) != home_before:
                return False, "Home did not return to its pre-mutation markup"
            if health_page.render(health_ctx) != health_before:
                return False, "Health did not return to its pre-mutation markup"
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(health_tmp, ignore_errors=True)
    check(
        "breaking a shared emitter breaks the hero WITH the page it borrowed it from: one class "
        "constant inside companion/draw.py's ring emitter is replaced at check time and both "
        "Home's hero and Health's readout change, neither keeping the original string (a hero "
        "built from its own copy would); the band emitter's own mutation reaches the hero and "
        "leaves Health byte-identical, proving the mutation is targeted rather than a global "
        "perturbation; and both pages return to their pre-mutation markup (CFG-44, "
        "24-08-PLAN.md Task 2)",
        _breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from)

    # --- 19-12-PLAN.md Task 3 (D-13/S-02): the "Next wake ≈ HH:MM" figure --

    def _wake_next_wake_at_iso_contract():
        import companion.wake as wake
        from server import device_config as _dc
        from datetime import datetime, timedelta, timezone
        # None for a falsy/unparseable ts, or no known interval.
        if wake.next_wake_at_iso(None, {}) is not None:
            return False, "expected None for a falsy last_checkin_ts"
        if wake.next_wake_at_iso("", {"wake_interval_s": 900}) is not None:
            return False, "expected None for an empty-string last_checkin_ts"
        if wake.next_wake_at_iso("not-a-timestamp", {"wake_interval_s": 900}) is not None:
            return False, "expected None for an unparseable last_checkin_ts"
        if wake.next_wake_at_iso("2026-08-27T11:55:00+00:00", {}) is not None:
            return False, "expected None for a config with no known interval and no env fallback"
        # A screen-on config: last_checkin + wake_interval_s. Pre-existing
        # fixture, pinned byte-identical — 22-02-PLAN.md Task 1 must not
        # move this string, since this config carries no quiet-hours key
        # at all and quiet_hours_status() degrades to (None, None) for it.
        got = wake.next_wake_at_iso(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
        if got != "2026-08-27T12:10:00+00:00":
            return False, "expected last_checkin + wake_interval_s, got %r" % (got,)
        # A screen-off config: last_checkin + DISPLAY_OFF_SLEEP_S, the D-13
        # screen-off rule — wins over wake_interval_s regardless of its value.
        # Pre-existing fixture, pinned byte-identical for the same reason.
        got = wake.next_wake_at_iso(
            "2026-08-27T11:55:00+00:00",
            {"wake_interval_s": 900, "display_enabled": False})
        expected = (
            datetime(2026, 8, 27, 11, 55, 0, tzinfo=timezone.utc)
            + timedelta(seconds=_dc.DISPLAY_OFF_SLEEP_S)).isoformat()
        if got != expected:
            return False, "expected last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config, got %r" % (got,)

        # --- 22-02-PLAN.md Task 1 (D-03/CFG-26): the quiet-hours-active
        # fixtures the phase's validation contract lists as a Wave 0 gap
        # (22-VALIDATION.md line 48) — the existing pinned test above
        # covered screen-on/screen-off only, never a held frame, which is
        # exactly the case X2 is about.

        # Fixture A: quiet hours 23:00-07:00 Europe/Paris, last check-in
        # 22:58 Europe/Paris (a non-DST date), interval 900s. The naive
        # last_checkin + interval candidate (23:13) falls INSIDE the
        # window that opens two minutes after the check-in — the window
        # must win, returning the window's end (07:00 the next day), not
        # 23:13. This is the exact fixture 22-UI-SPEC.md §3.3 rule 6 (the
        # nightly regression) is built from.
        qh_config_a = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin_a = datetime(2026, 1, 15, 22, 58, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_a.isoformat(), qh_config_a)
        expected_a = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
        if got != expected_a:
            return False, (
                "fixture A (quiet hours 23:00-07:00, check-in 22:58, interval 900s): "
                "expected the window's end (%r), not the naive 23:13 candidate, got %r"
                % (expected_a, got))
        status_a = wake.next_wake_status(checkin_a.isoformat(), qh_config_a)
        if status_a[0] != expected_a:
            return False, "fixture A: next_wake_status()'s ISO element disagreed with next_wake_at_iso()"
        if status_a[2] != wake.HOLD_QUIET_HOURS:
            return False, "fixture A: expected hold_reason == HOLD_QUIET_HOURS, got %r" % (status_a[2],)
        if (checkin_a + timedelta(seconds=status_a[1])).isoformat() != expected_a:
            return False, (
                "fixture A: effective_interval_s (%r) added back to the check-in did not "
                "reproduce the returned ISO string" % (status_a[1],))

        # Fixture B: quiet hours enabled, but nowhere near active at the
        # check-in instant NOR at the check-in-plus-interval candidate —
        # returns the plain interval, unmodified. The window is evaluated
        # relative to last_checkin_ts, never at a render-time "now".
        qh_config_b = dict(qh_config_a)
        checkin_b = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_b.isoformat(), qh_config_b)
        expected_b = (checkin_b + timedelta(seconds=900)).isoformat()
        if got != expected_b:
            return False, (
                "fixture B (quiet hours enabled but inactive at check-in and at "
                "check-in+interval): expected the plain interval (%r), got %r"
                % (expected_b, got))
        status_b = wake.next_wake_status(checkin_b.isoformat(), qh_config_b)
        if status_b[2] is not None:
            return False, "fixture B: expected hold_reason is None when quiet hours never engages"

        # Fixture C: quiet hours active AND the screen off — the window
        # still wins when its remaining time is longer than
        # DISPLAY_OFF_SLEEP_S (300s); the screen-off cadence alone would
        # otherwise have won every 5 minutes all night.
        qh_config_c = {
            "wake_interval_s": 900, "display_enabled": False,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin_c = datetime(2026, 1, 16, 1, 0, 0, tzinfo=timezone(timedelta(hours=1)))
        got = wake.next_wake_at_iso(checkin_c.isoformat(), qh_config_c)
        expected_c = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
        if got != expected_c:
            return False, (
                "fixture C (quiet hours active AND screen off): expected the window's end "
                "(%r), got %r — the window must win over the 300s screen-off cadence"
                % (expected_c, got))
        status_c = wake.next_wake_status(checkin_c.isoformat(), qh_config_c)
        if status_c[2] != wake.HOLD_QUIET_HOURS:
            return False, "fixture C: expected hold_reason == HOLD_QUIET_HOURS"

        # Fixture D: the richer accessor's None-triple for the same
        # never-raise edge cases the bare-ISO wrapper already covers.
        if wake.next_wake_status(None, {}) != (None, None, None):
            return False, "expected (None, None, None) for a falsy last_checkin_ts"
        if wake.next_wake_status("2026-08-27T11:55:00+00:00", {}) != (None, None, None):
            return False, (
                "expected (None, None, None) for a config with no known interval and no "
                "env fallback")

        # Fixture E: the richer accessor returns the effective interval
        # and hold reason (None) alongside the ISO string for the two
        # pre-existing, non-quiet-hours fixtures above.
        status_on = wake.next_wake_status(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
        if status_on != ("2026-08-27T12:10:00+00:00", 900, None):
            return False, "expected the screen-on fixture's richer result to carry interval=900, " \
                "hold_reason=None, got %r" % (status_on,)
        status_off = wake.next_wake_status(
            "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": False})
        if status_off != (expected, _dc.DISPLAY_OFF_SLEEP_S, None):
            return False, "expected the screen-off fixture's richer result to carry " \
                "interval=DISPLAY_OFF_SLEEP_S, hold_reason=None, got %r" % (status_off,)
        return True, ""
    check(
        "wake.next_wake_at_iso()/next_wake_status() return None/(None, None, None) for a "
        "falsy/unparseable ts or an unknown interval, last_checkin + wake_interval_s for a "
        "screen-on config, last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config (D-13's "
        "screen-off rule), and — 22-02-PLAN.md Task 1, D-03/CFG-26 — the quiet-hours-active "
        "fixtures: a window opening during the base interval wins over the naive candidate, an "
        "enabled-but-nowhere-near-active window changes nothing, an active window beats a "
        "300s screen-off cadence, and the richer accessor carries the same effective interval "
        "and hold reason for every fixture above",
        _wake_next_wake_at_iso_contract)

    # --- 22-02-PLAN.md Task 2 (D-03/D-04): the one frame-state
    # resolution and the one delay sentence ---------------------------

    def _frame_state_resolve_state_contract():
        import companion.frame_state as frame_state
        from datetime import datetime, timedelta, timezone

        # No check-in recorded at all: unknown, no dot class claimed —
        # this module never returns a dot class in the first place.
        if frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00") \
                != frame_state.STATE_UNKNOWN:
            return False, "expected STATE_UNKNOWN for a falsy next_wake_iso"
        if frame_state.headline_template(
                frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00")) \
                != frame_state.HEADLINE_DUE:
            return False, "expected the unknown state to degrade to HEADLINE_DUE, never None"
        if frame_state.delay_sentence_template(None, None, None) != frame_state.DELAY_UNKNOWN:
            return False, "expected DELAY_UNKNOWN when no next_wake_iso is known"

        next_wake = "2026-01-15T12:00:00+00:00"
        interval_s = 900

        # now before next_wake: due.
        now_before = "2026-01-15T11:00:00+00:00"
        if frame_state.resolve_state(next_wake, interval_s, None, now_before) != frame_state.STATE_DUE:
            return False, "expected STATE_DUE when now is before next_wake"
        if frame_state.headline_template(frame_state.STATE_DUE) != frame_state.HEADLINE_DUE:
            return False, "expected HEADLINE_DUE for STATE_DUE"

        # now between next_wake and next_wake + 2 * interval: still due,
        # same copy — the grace window is invisible (rule 3), no third
        # state, no colour shift.
        now_in_grace = (
            datetime.fromisoformat(next_wake) + timedelta(seconds=interval_s)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, None, now_in_grace) != frame_state.STATE_DUE:
            return False, "expected STATE_DUE inside the grace window (next_wake + 1 * interval)"

        # now >= next_wake + 2 * interval, no hold: late.
        now_late = (
            datetime.fromisoformat(next_wake) + timedelta(seconds=2 * interval_s)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, None, now_late) != frame_state.STATE_LATE:
            return False, "expected STATE_LATE at exactly next_wake + 2 * interval"
        if frame_state.headline_template(frame_state.STATE_LATE) != frame_state.HEADLINE_LATE:
            return False, "expected HEADLINE_LATE for STATE_LATE"

        # hold reason quiet hours: held, regardless of how far now sits
        # past next_wake + 2 * interval (rule 4: a held frame cannot
        # escalate to late by elapsed time alone).
        import companion.wake as wake
        far_past = (
            datetime.fromisoformat(next_wake) + timedelta(days=3)).isoformat()
        if frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, now_late) \
                != frame_state.STATE_HELD:
            return False, "expected STATE_HELD when hold_reason is HOLD_QUIET_HOURS"
        if frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, far_past) \
                != frame_state.STATE_HELD:
            return False, (
                "expected STATE_HELD to survive 3 days past next_wake + 2 * interval — "
                "elapsed time alone must never escalate a held frame to late")
        if frame_state.headline_template(frame_state.STATE_HELD) != frame_state.HEADLINE_HELD:
            return False, "expected HEADLINE_HELD for STATE_HELD"

        # The delay sentence has exactly three branches — due, held,
        # unknown, never a fourth "late" branch.
        if frame_state.delay_sentence_template(next_wake, interval_s, None) != frame_state.DELAY_DUE:
            return False, "expected DELAY_DUE for a due (or late) triple"
        if frame_state.delay_sentence_template(next_wake, interval_s, wake.HOLD_QUIET_HOURS) \
                != frame_state.DELAY_HELD:
            return False, "expected DELAY_HELD when hold_reason is HOLD_QUIET_HOURS"

        # --- The nightly regression (22-UI-SPEC.md §3.3 binding rule 6):
        # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00,
        # Europe/Paris (a non-DST date) — the resolved state must be
        # STATE_HELD, never STATE_LATE, end to end through
        # wake.next_wake_status() into frame_state.resolve_state().
        paris = timezone(timedelta(hours=1))
        qh_config = {
            "wake_interval_s": 900, "display_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        }
        checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
        next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
            checkin.isoformat(), qh_config)
        clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
        nightly_state = frame_state.resolve_state(
            next_wake_iso, effective_interval_s, hold_reason, clock.isoformat())
        if nightly_state != frame_state.STATE_HELD:
            return False, (
                "the nightly regression: expected STATE_HELD at 02:00 for a 22:58 check-in "
                "inside a 23:00-07:00 quiet-hours window, got %r (next_wake=%r, "
                "effective_interval_s=%r, hold_reason=%r) — this is exactly X2's nightly "
                "false alarm" % (nightly_state, next_wake_iso, effective_interval_s, hold_reason))

        return True, ""
    check(
        "companion.frame_state.resolve_state() resolves due/held/late/unknown from a "
        "(next_wake_iso, effective_interval_s, hold_reason, now) tuple with an invisible grace "
        "window and a held frame that cannot escalate by elapsed time alone, "
        "headline_template()/delay_sentence_template() return the matching three-branch copy "
        "constants, and the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock "
        "02:00 Europe/Paris) resolves to STATE_HELD end to end through wake.next_wake_status() "
        "(D-03/D-04, 22-02-PLAN.md Task 2, 22-UI-SPEC.md §3.3 binding rule 6)",
        _frame_state_resolve_state_contract)

    def _frame_state_view_free_and_i18n_contract():
        frame_state_path = os.path.join(REPO_ROOT, "companion", "frame_state.py")
        with open(frame_state_path, "r", encoding="utf-8") as fh:
            source = fh.read()
        if "dot--warn" in source:
            return False, "expected frame_state.py to never name a CSS dot class"
        for needle in ("import layout", "from companion.layout", "from .layout"):
            if needle in source:
                return False, "expected frame_state.py to stay view-free (no layout import)"

        import companion.frame_state as frame_state
        import companion.i18n as i18n
        # Each of the three headline and three delay-sentence constants
        # round-trips through the French catalogue (either frame_state's
        # own new entries, or — for the two deliberately-not-redefined
        # collisions — the pre-existing entries this module's docstring
        # names) and renders unchanged in English.
        headline_pairs = (
            (frame_state.HEADLINE_DUE, "Prochaine mise à jour ≈ %s"),
            (frame_state.HEADLINE_HELD, "Prochain réveil vers %s · heures calmes"),
            # 22-04-PLAN.md Task 1 (critical constraint 8): reconciled
            # from "Attendue depuis %s" (feminine agreement) to the
            # locked Copywriting Contract value, in companion/i18n_fr/
            # home.py, in the same commit as this plan's real consumer.
            (frame_state.HEADLINE_LATE, "Attendu depuis %s"),
        )
        for english, french in headline_pairs:
            if i18n.t_lang(english, "en") != english:
                return False, "expected %r unchanged under lang='en'" % (english,)
            if i18n.t_lang(english, "fr") != french:
                return False, "expected %r to translate to %r under lang='fr', got %r" % (
                    english, french, i18n.t_lang(english, "fr"))
        delay_pairs = (
            (frame_state.DELAY_DUE, "S’applique au prochain réveil, vers %s."),
            (frame_state.DELAY_HELD, "S’applique à la fin des heures calmes, vers %s."),
            (frame_state.DELAY_UNKNOWN, "S’applique au prochain réveil du cadre."),
        )
        for english, french in delay_pairs:
            if i18n.t_lang(english, "en") != english:
                return False, "expected %r unchanged under lang='en'" % (english,)
            if i18n.t_lang(english, "fr") != french:
                return False, "expected %r to translate to %r under lang='fr', got %r" % (
                    english, french, i18n.t_lang(english, "fr"))
        return True, ""
    check(
        "companion/frame_state.py names no dot--warn class and imports no layout module "
        "(view-free, D-03), and each of its six copy constants round-trips through "
        "companion.i18n's French catalogue unchanged in English (22-02-PLAN.md Task 2)",
        _frame_state_view_free_and_i18n_contract)

    def _battery_module_never_imports_pages_or_server():
        battery_path = os.path.join(REPO_ROOT, "companion", "battery.py")
        with open(battery_path, "r") as fh:
            source = fh.read()
        if "companion.pages" in source or "from server" in source:
            return False, (
                "expected companion/battery.py to never import companion.pages or server, "
                "keeping it usable by both home_page and health_page without either importing "
                "the other")
        return True, ""
    check(
        "companion/battery.py imports neither companion.pages nor server, preserving its "
        "shared, page-independent boundary (D-01)",
        _battery_module_never_imports_pages_or_server)

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()
        session_cookie = _login(harness)

        _seed_runway_events(harness.tmpdir, [
            {"ts": "2026-08-27T10:00:00+00:00", "hex": "e2e001", "callsign": "E2E001"},
        ])
        # A present panel.bin that changes nothing about the markup any
        # more is part of what this check proves (quick task 260903-c4o).
        _write_panel_file(harness.tmpdir)
        _seed_gallery(harness.tmpdir, ["20260827T100002Z.png"])

        def _history_preview_gallery_end_to_end():
            # 06.6.4.1-08 (D-22): /preview is retired as a page — this
            # subprocess-level check proves the redirect. Quick task
            # 260903-c4o further retires /preview.png outright (404 now,
            # not a real PNG) and upgrades this check to also prove the
            # route the per-row View-panel lightbox links to
            # (/gallery/{name}.png) genuinely serves full-resolution
            # bytes, against a real running service - the only consumer
            # of that route since quick task 260903-etm retired the
            # top-of-page render gallery.
            status, _headers, body = http_request(base + "/flights", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for /history, got %d" % status
            if b"Flights" not in body:
                return False, "expected the 'Flights' heading in /flights's response body"

            status, headers, body = http_request(base + "/preview", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect for /preview, got %d" % status
            if headers.get("Location") != "/flights":
                return False, "expected /preview to redirect to /history, got %r" % headers.get("Location")

            status, _headers, body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for the retired /preview.png route, got %d" % status

            status, headers, body = http_request(
                base + "/gallery/20260827T100002Z.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for a real /gallery/{name}.png, got %d" % status
            if not body.startswith(_PNG_SIGNATURE):
                return False, "expected a real PNG signature at the start of the gallery image body"
            content_type = headers.get("Content-Type", "")
            if content_type != "image/png":
                return False, "expected Content-Type: image/png, got %r" % content_type
            return True, ""
        check(
            "GET /history returns 200 with its own heading, GET /preview redirects (303) to "
            "/history, GET /preview.png now returns 404 (the route is retired), and GET "
            "/gallery/{name}.png returns 200 image/png with a real PNG signature — proving the "
            "route the per-row View-panel lightbox now links to genuinely serves full-resolution "
            "bytes, against a real running service",
            _history_preview_gallery_end_to_end)

        def _airlines_dialog_forms_render_unconditionally_over_real_http():
            # 29-01-PLAN.md (CFG-81): the exact-"1" ?edit= membership
            # test this check used to prove end to end is deleted along
            # with the query parameter itself - a real authenticated
            # HTTP GET now renders the dialog's replace/delete/upload
            # forms with NO query string at all, and an arbitrary
            # leftover ?edit=1 in a bookmark changes nothing, proving
            # the removed parameter has no reader anywhere in the real
            # request path (not just in a direct render() call).
            unconditional_tokens = (
                airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,
                airlines_page.LIGHTBOX_DELETE_CLASS,
                airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
            )
            for query in ("", "?edit=1"):
                status, _headers, body = http_request(
                    base + "/airlines" + query, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200 for /airlines%s, got %d" % (query, status)
                body_text = body.decode("utf-8", "replace")
                for token in unconditional_tokens:
                    if ('class="%s"' % token) not in body_text:
                        return False, (
                            "expected /airlines%s to render a %r form (CFG-81: unconditional now)"
                            % (query, token))
            return True, ""
        check(
            "a real authenticated GET of /airlines renders the dialog's replace, delete and "
            "upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark "
            "renders identically — against a real running service, proving the removed query "
            "parameter has no reader anywhere in the real request path (CFG-81, 29-01-PLAN.md)",
            _airlines_dialog_forms_render_unconditionally_over_real_http)

        def _both_dialogs_arrive_through_one_starting_style_entrance():
            """23-10-PLAN.md Task 2 (D3/CFG-32): both <dialog>s fade and
            zoom in, from ONE rule.

            The two dialogs — History's panel lightbox and the Airlines
            gallery's wide variant — are the same component under two
            classes, so the entrance is declared once on `.lightbox` and
            reaches both. This check asserts that count directly (one
            entrance, two dialogs) rather than letting a second, drifting
            copy appear for the wide variant.

            It also asserts what is deliberately ABSENT. 23-08-PLAN.md
            Task 2 already set this app's precedent for a one-directional
            entrance — opening animates, closing is instant — and wrote
            down the reason: an element kept in the flow through
            `transition-behavior: allow-discrete` is still in the tab
            order and still in the accessibility tree for the whole of
            its exit, and for every browser that does not support the
            property. A <dialog> raises the stakes rather than lowering
            them, because a modal that has not reached `display: none`
            is an invisible sheet over the page that swallows clicks
            (T-23-36). So `display` must not appear in the lightbox
            transition at all: `close()` must end the dialog outright.
            """
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path, "r", encoding="utf-8") as fh:
                css = fh.read()
            # Comment-stripped, for the reason this file's own sibling
            # scans already record: the paragraphs around these rules
            # discuss @starting-style, allow-discrete and `display` by
            # name, and a raw scan would be answered by the prose that
            # explains the rule instead of by the rule.
            stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)

            rendered = []
            for label, module, dialog_class in (
                ("history", history_page, "lightbox"),
                ("airlines", airlines_page, "lightbox lightbox--wide"),
            ):
                marker = '<dialog class="%s"' % dialog_class
                rendered.append((label, marker))

            entrances = re.findall(
                r"@starting-style\s*\{\s*\.lightbox\[open\]", stripped)
            # The open-state rule is counted with the @starting-style
            # blocks REMOVED, because the entrance block necessarily
            # repeats the same selector - counting the bare literal
            # reads 2 on a correct file, which is a number that means
            # nothing. What must be exactly one is the open-state rule
            # itself: one entrance, two dialogs.
            without_entrances = re.sub(
                r"@starting-style\s*\{.*?\}\s*\}", "", stripped, flags=re.DOTALL)
            open_rule = ".lightbox[open] {"
            if without_entrances.count(open_rule) != 1:
                return False, (
                    "expected exactly one %r rule outside @starting-style — one entrance serving "
                    "BOTH dialogs, got %d"
                    % (open_rule, without_entrances.count(open_rule)))
            if len(entrances) != 1:
                return False, (
                    "expected exactly ONE @starting-style entrance for .lightbox[open] (one "
                    "rule, two dialogs — History's and the Airlines gallery's wide variant are "
                    "the same component under two classes), got %d" % (len(entrances),))
            start_body = stripped[stripped.index(entrances[0]):]
            start_body = start_body[:start_body.index("}")]
            if "opacity: 0" not in start_body:
                return False, (
                    "expected the @starting-style entrance to start from opacity 0 — an element "
                    "going from display:none to displayed has no previous computed value to "
                    "transition from, which is the whole job of this block")
            if "scale(" not in start_body:
                return False, (
                    "expected the @starting-style entrance to start from a scale — D3's clause "
                    "is that both dialogs FADE AND ZOOM in")

            base_idx = stripped.index("\n.lightbox {")
            base = stripped[base_idx:stripped.index("}", base_idx)]
            if "transition:" not in base:
                return False, "expected .lightbox to declare the entrance transition"
            decl = base[base.index("transition:"):]
            decl = decl[:decl.index(";") + 1]
            for prop in ("opacity", "transform"):
                if prop not in decl:
                    return False, (
                        "expected the .lightbox transition to name %r, got %r" % (prop, decl))
            if "var(--motion-fast)" not in decl:
                return False, (
                    "expected the dialog entrance to spend var(--motion-fast), got %r" % (decl,))
            if "display" in decl or "allow-discrete" in decl:
                return False, (
                    "the .lightbox transition must NOT carry `display`/`allow-discrete`: a modal "
                    "that has not reached display:none is an invisible sheet over the page that "
                    "swallows clicks (T-23-36), and it stays in the tab order and the "
                    "accessibility tree for the whole of its exit — 23-08-PLAN.md Task 2's own "
                    "one-directional precedent, raised in stakes by a modal. Got %r" % (decl,))
            # ::backdrop is deliberately NOT animated, and that is a
            # reduced-motion fact rather than a taste one: the global
            # override matches `*, *::before, *::after`, which are
            # ELEMENT selectors — ::backdrop is in neither, exactly as
            # this file already records for the view-transition
            # pseudo-element tree. An animated backdrop would be motion
            # a reduced-motion visitor cannot switch off.
            backdrop_idx = stripped.index(".lightbox::backdrop {")
            backdrop = stripped[backdrop_idx:stripped.index("}", backdrop_idx)]
            if "transition" in backdrop or "animation" in backdrop:
                return False, (
                    ".lightbox::backdrop must not be animated — the global reduced-motion "
                    "override matches `*, *::before, *::after`, none of which is ::backdrop, so "
                    "a backdrop transition is motion a reduced-motion visitor cannot escape")

            # And both dialogs really do render with the class the one
            # rule above is keyed to.
            tmp = _mkstate("dialog-entrance")
            try:
                # History emits its dialog only on a page that has a
                # panel to show, so the fixture has to have one - an
                # empty-state render carries no dialog at all, which
                # would make the assertion below pass for the wrong
                # reason if it were inverted, and fail for the wrong
                # reason as written.
                names = ["2026-08-27T10-00-00+00-00.png"]
                _seed_gallery(tmp, names)
                _seed_runway_events(tmp, [
                    {"ts": "2026-08-27T10:03:00+00:00", "hex": "dlgent1",
                     "callsign": "DLGENT"},
                ])
                history_html = history_page.render(
                    _history_ctx(tmp, gallery_entries=names))
                airlines_html = airlines_page.render({})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            for label, marker in rendered:
                html_text = history_html if label == "history" else airlines_html
                if marker not in html_text:
                    return False, (
                        "expected the %s page to render %r so the one .lightbox[open] entrance "
                        "reaches it" % (label, marker))
            return True, ""
        check(
            "both <dialog>s arrive through ONE @starting-style entrance on .lightbox[open] — "
            "fading and zooming from opacity 0 over var(--motion-fast), reaching History's "
            "lightbox and the Airlines gallery's wide variant from a single rule, with `display`/"
            "`allow-discrete` deliberately absent so close() ends the dialog outright rather than "
            "leaving an invisible click-swallowing sheet over the page (T-23-36), and with "
            "::backdrop unanimated because the global reduced-motion override cannot reach it "
            "(D3/CFG-32, 23-10-PLAN.md Task 2)",
            _both_dialogs_arrive_through_one_starting_style_entrance)

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("view-pages: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
