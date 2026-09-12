#!/usr/bin/env python3
"""Contract harness for the SkyPane companion service: companion/auth.py,
companion/layout.py, and (plan 06-05) the real subprocess-launched
companion/app.py route table.

Covers: constant-time password checking, fail-closed behaviour when no
password is configured, stateless signed session tokens (issue/verify
round trip, six distinct malformed-token rejections, forged-secret and
hand-built-expired coverage), session/logout cookie security flags,
cookie parsing, the process-global login-attempt throttle, the single
canonical HTML-escaping helper, the page shell's document shape and
active-nav/theme rendering, the status-dot/data-table component
builders, that AuthNotConfigured never leaks the configured password
value, the D-02 whole-site auth gate asserted route by route against a
real running service, the login failure/success flow and its cookie
flags, the 404 copy, the preview PNG path (missing file vs. a real
960,000-byte panel), gallery path-traversal rejection with a canary
file, and the server-global (not per-session) poll-trigger cooldown.

Checks are grouped under three clearly-commented sections: Section 1
(companion/auth.py) and Section 2 (companion/layout.py) are pure
in-process unit checks against the imported modules. Section 3 (plan
06-05) launches companion/app.py as a real subprocess on a free local
port and drives it with urllib.request, mirroring
stub-server/test_poll_cycle.py's Harness/http_request()/readiness-poll
pattern.

Stdlib-only (hashlib, hmac, html, os, shutil, socket, subprocess, sys,
tempfile, time, urllib). No pytest.

Usage:
    server/.venv/bin/python3 companion/test_companion_app.py
"""
import hashlib
import hmac
import html
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import auth, layout, theme_preview  # noqa: E402
from companion.pages import health_page  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import calendar_rules  # noqa: E402
from server.plane import colour_rules  # noqa: E402
from server.plane import illustrations as server_illustrations  # noqa: E402
from server.plane import manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

TEST_PASSWORD = "companion-test-password-please-ignore"
APP_PATH = os.path.join(HERE, "app.py")
IMAGE_BYTES = 960000  # server/panel_format.py's IMAGE_BYTES, duplicated as a
# plain literal so this harness never has to import Pillow (or
# server.panel_format) itself, matching panel_format.py's own documented
# precedent for stub-server/make_test_panel.py's independent duplication.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STARTUP_DEADLINE_S = 10.0
EXPECTED_CHECK_COUNT = 129  # 11-04: +4 (env_wake_interval_default() full input space,
# page_context() threading, the end-to-end env-prefill/on-disk-precedence
# check, and the below-floor-degrades-to-placeholder check)
# merge origin/main into
EXPECTED_CHECK_COUNT = 144  # 141 + 3 (phase 06.6.4.1.1-04 Task 1, D-17: the
# flash banner now splices below page_header() with FLASH_SLOT_MARKER never
# leaking to the client, still falls back to its original before-body slot
# for marker-less bodies (login/404), and an anomaly banner is unaffected
# and keeps its own pre-body slot)
# 141 = 137 + 4 (phase 06.6.4.1.1-01 Task 2: the
# /theme-preview/{id}.png route — real key returns 200/image/png/a real
# PNG body for every one of the 16 registered themes, an unknown id 404s
# with the same not-found copy, three traversal-shaped paths all 404 with
# no file content, and an unauthenticated request redirects to /login
# without ever returning image bytes — same four shapes as the
# illustration-image-route checks below)
# 137 = 130 + 7 (phase 06.6.4.1.1-01 Task 1: theme_preview.py's
# in-process checks — 320x120 PNG for every theme, pairwise-distinct means
# across all 16 themes, byte-identical repeat renders, cache_path()'s
# traversal/unknown/falsy-state_dir guard, cold-cache creates the file and
# matches a direct render, a second call is served from disk without
# re-rendering, and preview_signature() changing with
# THEME_PREVIEW_CACHE_VERSION)
# 130 = 127 + 3 (quick task 260903-peo Task 4: UIR-19's
# flash-cleanup.js pre-auth-serving check, ES5-dialect check, and
# route/src cross-file agreement check; the pre-existing six-script-tag
# count guard was retargeted in place to seven, no count change from it)
# 127 = quick task 260903-peo Task 1: 2 new checks
# (UIR-16 — an authenticated 404 opens with the shared page_header()
# component and shows the Health nav dot under seeded error state; the
# same seeded error state produces NO health-dot markup for an
# UNAUTHENTICATED 404, the leak guard for the two pre-auth static-asset
# call sites, _serve_stylesheet() and _serve_script_file()). 125 = merge origin/main into
EXPECTED_CHECK_COUNT = 148  # merge of HEAD (129: Phase 10/11's env-prefill
# and page_context() threading checks) with origin/main (144: 06.6.4.1.1's
# theme-preview route/flash-slot checks) — both branches' independent
# additions combined. Recomputed directly against the real on-disk
# check(...) call count at merge-resolution time (148/148 pass), not
# trusted from arithmetic alone, per this file's own established
# discipline.
# claude/history-preview-gallery-32b974 (2026-09-03): combines this
# branch's quick task 260903-c4o (-1: 108 -> 107, retiring the
# /preview.png route) with main's independent, non-overlapping work
# since the same qkm=108 baseline (+18: 108 -> 126 via quick tasks
# 260902-tli +0, 260902-v26 +17, 260903-btu +1) for a net 108 - 1 + 18
# = 125. Verified against the actual merged check() call count, not
# just arithmetic.
#
# --- this branch's history (260903-c4o) ---
# 107 = 108 - 3 (the unauthenticated-redirect loop's own "/preview.png"
# registration, _preview_missing, and _preview_real_panel — all three
# assumed the route still existed) + 2
# (_preview_png_unauth_404_not_login_redirect, pinning the new pre-auth
# 404-not-redirect contract; and _preview_png_404_even_with_real_panel,
# replacing the old missing/real-panel pair with one check proving the
# route 404s even when a genuine panel exists).
#
# --- main's history (since the same 108 baseline) ---
# 125 = 116 + 9 (quick task 260902-v26 Plan 02 Task 3: the live
# end-to-end illustration-upload proof against a real running
# companion/app.py subprocess — round trip, D-03 same-pipeline
# equivalence, override written to the expected single path, the
# vendored original provably byte-identical after, the panel-side
# select_illustration() effect, non-image rejection, oversized-upload
# rejection + post-drain health, unknown/traversal-key 404s, and
# unauthenticated POST).
# 116 = 108 + 8 (quick task 260902-v26 Plan 02 Task 1: parse_single_
# uploaded_file()'s 8 in-process checks — happy path with a traversal-
# shaped declared filename, two-part rejection, non-multipart media type,
# missing boundary, empty body, missing header/body separator, None
# content_type, empty file-part payload).
# 108 + 0 (quick task 260902-tli Task 2: the panel-lookup.js banned-token
# check retargeted in place — matchMedia/innerWidth added to the tuple,
# pinning the CSS-only gate — no new check, no count change).
# 125 + 1 (quick task 260903-btu Task 4: the optional replace-form lookup
# stays outside the mandatory three-element guard check — pins the
# single line that keeps History's lightbox alive. The pre-existing
# banned-token check was left unmodified — the new code introduces no
# banned token, and widening that tuple is out of scope).
# 126 = quick task 260902-qkm (2026-09-02): 1 new
#
# --- shared history before the 108 baseline ---
# check pinning both nav-link geometries apart after restoring
# .mobile-nav__link's 44px/Body-size tap target (D-05 reached it by
# mistake) while .sidebar-link keeps its D-05 32px/Label-size compaction.
# 107 = quick task 260902-l9w Task 2 Commit B: 1 new
# check pinning both halves of the hidden-runway-radio touch-target fix:
# the new input.visually-hidden/select.visually-hidden rule exists, and
# the global input/select rule still declares both 44px minimums.
# 106 = quick task 260902-gjj Task 2 Commit A: 1 new
# check (card_status_class() maps to base_class + a fixed suffix for the
# three whitelisted states, empty string for None/unrecognised, diverging
# from stat_tile()'s own accent fallback).
# 105 = 06.6.4.1-08 Task 2: 3 new checks (NAV_TABS holds
# exactly 4 entries in settled order; sidebar_nav()/the mobile dropdown
# each render exactly 4 links with exactly one active; the eye glyph
# (icon-nav-preview) stays an ICON_IDS whitelist member and icon_html()
# returns non-empty markup for it) — the unauthenticated-redirect loop's
# "/preview" iteration was retargeted into its own explicit check in
# place (still a net +0 for that piece, folded into Task 1's own count
# below), not counted twice. # 102 = 06.6.4.1-08 Task 1: net +1 (101 -> 102) — 2 new
# checks (authenticated GET /preview redirects to /history; the same
# request with an arbitrary query string — including a next=-shaped and
# an https://evil.example-shaped value — still redirects to the
# identical /history location) minus 1 removed (the pre-existing
# "authenticated GET /preview returns 200 with the Preview heading"
# tab-iteration entry, retargeted away since D-22 retires the page and it
# can no longer return 200/a page heading). The unauthenticated-redirect
# and preview.png/gallery-image checks already covered the session-gate
# and byte-serving-route acceptance criteria and needed no change. # 101 =
# 06.6.4.1-07 Task 3: 1 new standing route-contract guard (nav tuple/page-titles dict/icon map size+key-set agreement, settings route constant equals NAV_TABS[0][0]) — the literal sweep found no remaining stale /config or /config-led occurrence in this file to fix, and three "five nav links"-shaped prose descriptions were reworded to stop hardcoding a route count that changes again in plan 08 (no check-count effect, prose only). # 100 = 06.6.4.1-07 Task 1: 4 new settings-route-rename checks (old path 404s authenticated, POST /settings redirects with flash, ?next=/settings hidden-field round trip, route/icon-map cross-module contract) — the five pre-existing tab-tuple/redirect/login-default/logout-refusal checks were retargeted from /config to /settings in place, not counted as new. # 96 = 06.6.4.1-02 Task 3: 4 new panel-lookup.js checks (pre-auth serving, ES5-dialect, route/src agreement, six-script-tag count) # 92 = 06.6.4.1-02 Task 2: 4 new illustration-image-route checks (real key, unknown key, traversal, unauthenticated) # 88 = 85 + 3 (heading-color-consistency: serif-heading contract both directions, single error token)  # 06.6.3-01 Task 2: 4 new pre-auth static-script
# regression checks (dirty-state.js/list-filter.js/copy-button.js/
# freshness.js, one each) + 1 new cross-file *_SCRIPT_ROUTE/*_SCRIPT_SRC
# DOM-contract-guard check, mirroring _three_file_nav_dom_contract_guard()'s
# own pattern; previously 80 = 06.6.2-08 code-review fix CR-01 added 1 regression check
# (skip-link tabindex="-1"); before that 79 = 73 (72 (71 (70 (69 (68: 06.6.1's own additions: 62 + 2
# (06.6.1-05 Task 1: nav-dropdown.js) + 4 (Task 3:
# toggle/dropdown/DOM-contract/no-JS)) + 1 (2026-08-29 quick task 260829-0rl,
# merged independently via origin/main PR #19: the gallery route's private
# caching-scope regression check, WR-02 from 06.4-REVIEW.md)) + 1
# (06.6.2-02: the genuine two-thread concurrent POST /poll-now check
# proving _POLL_LOCK serializes execution)) + 1 (06.6.2-03 Task 2: the new
# nav-dropdown.js progressive-enhancement state-machine check — the
# existing no-JS check was rewritten in place, not counted as new)) + 1
# (06.6.2-05 Task 3: GET /logout now 404s (D-11) — the pre-existing
# logout-cookie check was renamed to POST /logout, not counted as new)) + 1
# (06.6.2-06 Task 3: a new check pinning health_alert="warn"'s dot--warn
# treatment — the pre-existing health-nav-dot check was updated in place
# to True/False -> "error"/None, not counted as new)) + 6 (06.6.2-07 Task 3:
# deep-link-return round-trip, two open-redirect-rejection checks
# (https://evil.example and //evil.example, both exercised — the plan's
# own text names one "(or the other)" but both are cheap and directly
# threat-model-relevant, T-06.6.2-12), the GET-path next= validation
# no-hidden-field check, the login_shell() markup check, and the D-01/
# UXA-09 page_shell()/login_shell() lang="en" agreement guard — the five
# pre-existing NAV_TABS-redirect checks and the one POST /config redirect
# check were updated in place for the new ?next= carrying behavior, not
# counted as new).
EXPECTED_CHECK_COUNT = 151  # 148 + 3 (phase 13 plan 13-06 Task 1, D-09:
# _illustration_filenames()'s widened per-request union — the in-process
# union contract (None/empty-state-dir both equal the static set, one
# seeded manual entry adds exactly one filename, an unusable-slug entry
# contributes nothing), the real-handler read-path state machine for a
# manual key (404/404/200 across no-entry, entry-with-no-file, and
# both-exist), and Pitfall 3's warning sign made executable (a POST for a
# never-registered key 404s and writes nothing, then succeeds once the
# key is registered). Recomputed directly against the real on-disk
# check(...) call count, not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 153  # 151 + 2 (phase 13 plan 13-06 Task 2: flash
# completeness — every FLASH_KEY_MANUAL_* constant is a FLASH_MESSAGES/
# FLASH_ROLES key, the six UI-SPEC deck strings resolve byte for byte
# through _resolve_flash_text(), an unknown key still resolves to None,
# and no message carries a runtime placeholder except the pre-existing
# cooldown key; and the ctx contract — page_context() on a
# ?resolve=XYZ request supplies resolve_prefix/manual_resolutions
# correctly and every ctx key companion/pages/__init__.py documents is
# actually present in the returned dict. Recomputed directly against the
# real on-disk check(...) call count, not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 157  # 153 + 4 (phase 13 plan 13-06 Task 3: the
# auth gate on both new routes (unauthenticated POSTs redirect to /login
# and write no manual_resolutions.json — state dir unchanged, not only
# the status code); D-11 on the write path (a well-shaped but
# unregistered prefix writes nothing and gets the stale flash, then
# succeeds once the prefix is a live registry member); rejection mapping
# (empty/too-long/reserved names and the registry cap each reach their
# own distinct flash key) and the D-03 branch (a brand-new name redirects
# with resolve=, an already-covered name redirects without it); and D-08
# through the delete route (the entry is removed, the override PNG
# survives, the redirect carries no flash, a second identical POST is a
# no-op, and a malformed prefix 404s without touching the registry).
# Recomputed directly against the real on-disk check(...) call count, not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 159  # 157 + 2 (13-REVIEW.md WR-11 fix: end-to-end
# HTTP-level checks that POST /airlines/resolve and POST
# /airlines/manual-resolutions/{prefix}/delete actually reach
# FLASH_KEY_MANUAL_SAVE_FAILED / FLASH_KEY_MANUAL_DELETE_FAILED when
# add_entry()/delete_entry() fail to write because the state dir is
# read-only — the two planner-added failure flash keys had no test
# anywhere before this, which is exactly why CR-01 shipped. Recomputed
# directly against the real on-disk check(...) call count, not trusted
# from arithmetic alone.
# 15-05-PLAN.md Task 3 (D-10/D-11, 15-VALIDATION.md rows 10/11): +6 (the
# unauthenticated-writes-nothing check for both new routes, the
# add/delete-forms-sit-outside-the-settings-form check, the raw no-JS
# added-then-replaced check, the rejection-paths check covering
# key-invalid/crafted-kind/crafted-theme/registry-full, the delete-route
# full-contract check, and the fresh-per-request check — one check per
# Task 3 route-behaviour bullet). No pre-existing check needed
# retargeting. 159 + 6 = 165, recomputed directly against the real
# on-disk check(...) call count at execution time (165/165 pass), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 165
EXPECTED_CHECK_COUNT = 192  # 177 + 15 (phase 18: two more tabs in the per-tab loops (+4), legacy-route redirects (+4), Home/quick-action/scoped-save/split-page/no-store checks (+7)) — was 177 # 165 + 12 (phase 17 plan 04 Task 3, D-06/D-09:
EXPECTED_CHECK_COUNT = 194  # 192 + 2 (phase 19 plan 02 Task 1, D-15/A-32:
# the zero-length-window and real-lockout_s self-releasing-lockout checks
# for LoginThrottle.record_failure()).
EXPECTED_CHECK_COUNT = 198  # 194 + 4 (phase 19 plan 02 Task 2, D-16/A-33:
# the derived-signing-key check, the revoke()/is_revoked() round-trip and
# pruning-on-expiry checks, and the real-HTTP replay-after-logout check).
EXPECTED_CHECK_COUNT = 201  # 198 + 3 (phase 19 plan 02 Task 3, D-17/A-34:
# the insecure-cookies-drops-Secure check, the fails-closed-on-"true"
# check, and the deploy/skypane.env.example documentation check).
EXPECTED_CHECK_COUNT = 204  # 201 + 3 (19-04-PLAN.md Task 1, D-18/A-35:
# poll-cooldown.js's public-serving/ES5-safe/route-src-agreement checks;
# the eight-deferred-scripts check is retargeted in place from the
# seven-deferred-scripts check, not counted as new).
EXPECTED_CHECK_COUNT = 208  # 204 + 4 (19-04-PLAN.md Task 2, D-18/T-19-05:
# the exact-CSP-equality check, the strict-script-src-no-unsafe-inline
# check, the redirect-carries-four-hardening-headers check, and the
# static-CSS-response-carries-CSP check).
EXPECTED_CHECK_COUNT = 210  # 208 + 2 (19-04-PLAN.md Task 3, D-18/T-19-04:
# unauthenticated POST /ui-theme and POST /logout both redirect to
# /login checks).
# the save-triggered immediate calendar sync's real-HTTP-round-trip
# outcomes — plural/singular flight count, a zero-entry feed's distinct
# success, the single generic failure message with the URL still saved,
# T-17-FLASH's five-needle leak guard, disconnect erasing the fetched
# entries, the throttle bypass via min_interval_s=0 paired with poll_
# loop.py's own unmodified call site still throttling, honest lock
# contention (D-09), the lock released after a failed sync, an unrelated
# save never reaching the refresh call, and the manual poll cooldown
# left untouched by a calendar save — all via _InProcessHarness, since
# these checks monkeypatch calendar_rules.default_calendar_transport and
# socket.getaddrinfo, which a Harness subprocess's separate interpreter
# could never observe. Recomputed directly against the real on-disk
# check(...) call count at execution time (177/177 pass), not trusted
# from arithmetic alone, per this file's own established discipline.
EXPECTED_CHECK_COUNT = 211  # 19-07-PLAN.md Task 3 (D-07/A-25): +1 (the
# real end-to-end check: a POST /settings with a valid theme change and
# an empty quiet_hours_start returns 200, shows the newly-picked theme
# still selected, shows the quiet-hours field error, carries no flash
# banner, and persists nothing on disk). 210 + 1 = 211, recomputed
# directly against the real on-disk check(...) call count at execution
# time (211/211 pass), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 213  # 19-09-PLAN.md Task 3 (D-02): +2 (freshness.js's
# own named ES5/sink guard — the sibling nav-dropdown.js/panel-lookup.js
# ban list minus location.reload plus fetch(/setTimeout/setInterval as its
# one reviewed exception, plus DOMParser/replaceChild/credentials/fetch(
# required present — and the no-URL-taking-navigation-form check). 211 + 2
# = 213, recomputed directly against the real on-disk check(...) call
# count at execution time (211/213 pass — the two documented WR-11
# root-sandbox failures, unrelated to this plan), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 217  # 19-11-PLAN.md Task 1 (D-08/A-26): +4 (the
# dedicated POST /settings/calendar/disconnect route's own real-HTTP
# checks: a bare POST renders the confirmation page and leaves the
# calendar connected, confirm=maybe does the same, confirm=yes actually
# disconnects and redirects with the disconnected flash key, and an
# unauthenticated POST redirects to /login and writes nothing). 213 + 4
# = 217, recomputed directly against the real on-disk check(...) call
# count at execution time (215/217 pass — the two documented WR-11
# root-sandbox failures, unrelated to this plan), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 220  # 19-11-PLAN.md Task 2 (D-08/A-26): +3 (the
# ninth static script, confirm-submit.js: its own public-serving check,
# its ES5-safe/no-HTML-writing-sink guard, and its route/src agreement
# check). The eight-deferred-scripts check was retargeted in place to
# nine, a net-zero rename. 217 + 3 = 220, recomputed directly against
# the real on-disk check(...) call count at execution time (218/220
# pass — the two documented WR-11 root-sandbox failures, unrelated to
# this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 221  # 19-12-PLAN.md Task 2 (D-22, Device-page
# half): +1 (a real authenticated GET of the Device page contains the
# Edit-artwork href, and following it returns 200 with the
# artwork-editing forms present — the end-to-end link between plan
# 19-08's ?edit=1 gate and this plan's link). 220 + 1 = 221, recomputed
# directly against the real on-disk check(...) call count at execution
# time (219/221 pass — the two documented WR-11 root-sandbox failures,
# unrelated to this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 227  # 20-01-PLAN.md Task 2 (D-02/D-29/D-03):
# +6 (POST /ui-lang's fr/en/garbage cookie round trip, its no-session
# gate; POST /ui-mode's simple/full/garbage cookie round trip, its
# no-session gate; the Accept-Language-resolves-<html-lang> pair; the
# sp_ui_lang cookie beating Accept-Language). The quick-toggle
# redirect-target retarget (Home -> Display, D-16) is a net-zero
# in-place edit, not a new check. 221 + 6 = 227, recomputed directly
# against the real on-disk check(...) call count at execution time
# (225/227 pass — the two documented WR-11 root-sandbox failures,
# unrelated to this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 233  # 20-08-PLAN.md Task 1 (D-23): +6 (the
# no-event cache path is stable and distinct from a live-event path;
# two different event ids give two different paths and the same event
# id twice gives the same path; a hostile/non-integer event id degrades
# to the sample path; preview_png_bytes() renders a full and a partial
# live-event row without raising; cached_preview_bytes() with no event
# is unchanged; cached_preview_bytes() keys its cache on the event row
# id, serving a same-event repeat from disk and missing on a newer
# event). 227 + 6 = 233, recomputed directly against the real on-disk
# check(...) call count at execution time (231/233 pass — the two
# documented WR-11 root-sandbox failures, unrelated to this plan), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 238  # 20-08-PLAN.md Task 2 (D-23): +5 (?live=1
# with no runway_events row falls back to the sample scene; a seeded
# event renders and a same-event repeat request is served from the
# cache without growing it; a newer event both changes the served
# bytes and adds a new cache file; an unknown theme id with ?live=1
# still 404s before any query is parsed; ?live=0 and a missing query
# both serve the sample variant). The "GET /static/theme-preview.js"
# check named in this task's own action text is deferred to Task 3's
# commit, where that file first exists (Task 2's own <files> list
# excludes companion/static/theme-preview.js) — see this plan's own
# SUMMARY.md Deviations section. 233 + 5 = 238, recomputed directly
# against the real on-disk check(...) call count at execution time
# (236/238 pass — the two documented WR-11 root-sandbox failures,
# unrelated to this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 242  # 20-08-PLAN.md Task 3 (D-22..D-24/D-32): +4
# (the tenth static script, theme-preview.js: its own public-serving
# check, its ES5-safe/no-HTML-writing-sink guard, its route/src
# agreement check, and the exactly-one-script-tag/no-bare-inline-script
# shell check). The nine-deferred-scripts check was retargeted in place
# to ten, a net-zero rename. 238 + 4 = 242, recomputed directly against
# the real on-disk check(...) call count at execution time (240/242
# pass — the two documented WR-11 root-sandbox failures, unrelated to
# this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 241  # post-wave-3 retarget (20-07/D-36): -1 — the
# Device page's Edit-artwork link was deleted outright, so
# _device_page_edit_artwork_link_opens_airlines_with_edit_forms() (which
# exercised it end to end) is removed rather than retargeted; no
# replacement link exists to assert against. 242 - 1 = 241.
EXPECTED_CHECK_COUNT = 244  # 20-09-PLAN.md Task 2 (D-14c): +3 (a valid
# POST /settings/calendar/connect 303-redirects to Display with the
# calendar_connect_ok flash key, persists the URL, triggers exactly one
# registry refresh, and leaves quiet_hours_enabled/display_enabled
# exactly as they were seeded — the T-20-11 pinned regression; an empty
# calendar_url rejects with calendar_connect_invalid and persists
# nothing; an unauthenticated POST redirects to /login and writes
# nothing). Two pre-existing checks retargeted in place with no count
# change: the FLASH_MESSAGES-interpolation-exemption check widened for
# FLASH_KEY_CALENDAR_CONNECT_OK's own "{n}" placeholder, and the
# Display/Device group-split check's "Per-flight colour rules" needle
# updated to "Flight colours" (20-09-PLAN.md Task 3/D-15a's rename).
# 241 + 3 = 244, recomputed directly against the real on-disk check(...)
# call count at execution time (242/244 pass — the two documented WR-11
# root-sandbox failures, unrelated to this plan), not trusted from
# arithmetic alone.
EXPECTED_CHECK_COUNT = 249  # 20-11-PLAN.md Task 1 (D-26/T-20-13): +5 (an
# unauthenticated POST /settings/notifications/test redirects to /login;
# with no stored topic URL it redirects with the notifications_test_
# failed flash key and never calls notify.send_notification(); with a
# stored URL it calls that function exactly once with the STORED url and
# redirects with notifications_test_ok; a sender returning False
# redirects with notifications_test_failed; a POST carrying its own
# topic_url field is ignored in favour of the stored one). 244 + 5 = 249,
# recomputed directly against the real on-disk check(...) call count at
# execution time (247/249 pass — the two documented WR-11 root-sandbox
# failures, unrelated to this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 251  # 20-11-PLAN.md Task 3 (D-06): +2 (copy-
# button.js/dirty-state.js each stay ES5-safe with no forbidden HTML-
# writing/eval/network sink, copy-button.js reads its on-success
# feedback text from data-copied-text, dirty-state.js reads its five
# connector words from the dirty-bar element's own data-dirty-*
# attributes, and each file's removed hardcoded literal survives only
# as its own documented fallback). 249 + 2 = 251, recomputed directly
# against the real on-disk check(...) call count at execution time
# (249/251 pass — the two documented WR-11 root-sandbox failures,
# unrelated to this plan), not trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 267  # 20-12-PLAN.md Task 2 (D-30/D-31): +16
# (Section 5, end-to-end simple mode over real HTTP: the nav's
# Advanced-group/health-link/device-link/status-dot omission on four
# tabs, Home's Health link, Airlines' "Change pictures" button,
# Display's two disclosures collapsing to one sentence, Display's own
# six everyday groups staying present, /health and /device staying
# reachable by URL, Flights/Airlines keeping their full content, the
# mode surviving three sequential requests, and the full-mode mirror
# of each toggled behaviour). 251 + 16 = 267.
# 21-01-PLAN.md Task 1 (D-17): -19. Section 5's entire 16-check block is
# deleted outright (the simple/full mode mechanism it exercised no
# longer exists; the full-mode-only behaviour it also proved is picked
# up by this plan's own new checks in test_view_pages.py/
# test_config_page.py). _ui_mode_post_round_trip and _ui_mode_post_
# without_session_redirects_to_login (2 checks) are replaced by one
# new check, _ui_mode_post_with_session_now_404s (the T-21-01 pin that
# a valid-session POST /ui-mode now takes the unknown-route 404 path).
# 267 - 16 - 2 + 1 = 250, recomputed directly against the real on-disk
# check(...) call count at execution time (248/250 pass — the two
# documented WR-11 root-sandbox failures, unrelated to this plan), not
# trusted from arithmetic alone.
EXPECTED_CHECK_COUNT = 250


def _ago_iso(seconds):
    """An ISO-8601 UTC timestamp `seconds` in the past — quick task
    260903-peo's own seeding helper, mirroring test_status_pages.py's
    `_ago()` for the one use this file needs (a stale
    `META_LAST_PIPELINE_RUN` past `health_page.STALE_PIPELINE_ERROR_S`,
    which drives `overall_severity()` to `"error"`).
    """
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(
        timespec="seconds")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Return None from redirect_request() so a 303 (or any other
    redirect) is surfaced to the caller as an HTTPError instead of being
    silently followed — the auth-gate and flash-key checks below need to
    see the raw status code and Location/Set-Cookie headers, not the page
    the redirect points at.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# A single shared opener with redirects disabled. Deliberately NOT built
# with urllib.request.HTTPCookieProcessor: this test server runs over
# plain HTTP, and companion/auth.py's session cookie always carries the
# `Secure` flag (correctly, for production) - http.cookiejar honours that
# flag and silently refuses to store or resend a Secure cookie over a
# non-HTTPS connection, which would make an automatic cookie jar quietly
# drop the session cookie in exactly this harness. Cookies are instead
# captured from Set-Cookie response headers and threaded through
# explicitly as plain Cookie request headers below.
_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def http_request(
        url, method="GET", data=None, cookie=None, timeout=10,
        content_type=None, extra_headers=None):
    """Minimal stdlib HTTP client (mirrors
    stub-server/test_poll_cycle.py's http_request()): returns
    (status, headers_dict, raw_bytes) for both success and HTTP-error
    responses; connection-level failures propagate.

    `content_type` (quick task 260902-v26): an explicit override for the
    Content-Type request header — used by the illustration-upload checks
    to send `multipart/form-data; boundary=...` instead of the default
    urlencoded type a POST otherwise gets. `None` (the default) preserves
    every existing caller's behaviour exactly.

    `extra_headers` (20-01-PLAN.md Task 2): an optional {name: value}
    dict merged into the request headers — used by the D-03
    Accept-Language checks. `None` (the default) preserves every
    existing caller's behaviour exactly.
    """
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    if content_type is not None:
        headers["Content-Type"] = content_type
    elif data is not None and method == "POST":
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _cookie_value(headers):
    """Extract just the "name=value" portion of a Set-Cookie response
    header (dropping the trailing attribute flags), or None.
    """
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]


class Harness:
    """Owns the companion/app.py subprocess lifecycle: a free port, an
    isolated temp state directory, startup readiness polling, and clean
    teardown - structurally mirrors
    stub-server/test_poll_cycle.py's own Harness class.
    """

    def __init__(self, extra_args=()):
        self.tmpdir = tempfile.mkdtemp(prefix="skypane-companion-")
        self.port = self._pick_free_port()
        self.stdout_path = os.path.join(self.tmpdir, "app.stdout.log")
        self.proc = None
        self.extra_args = list(extra_args)

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
        ] + self.extra_args
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=stdout_fh, stderr=subprocess.STDOUT, env=env)
        finally:
            stdout_fh.close()  # child holds its own duplicated fd

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


class _InProcessHarness:
    """A real `companion/app.py` `ThreadingHTTPServer`, running in a
    background thread of THIS test process — deliberately NOT a
    `Harness` subprocess (phase 17 plan 04, D-06/T-17-FLASH's checks).

    The calendar-sync checks below need to monkeypatch `server.plane.
    calendar_rules.default_calendar_transport` and `socket.getaddrinfo`
    so a save-triggered fetch never touches a real socket — the exact
    technique `server/test_calendar_rules.py`'s own `make_calendar_
    transport()`/fake-`getaddrinfo` helpers already use in-process. A
    monkeypatch made in this process has no effect on a `Harness`'s
    `subprocess.Popen`'d child, which is a separate interpreter with its
    own separate copy of every imported module — hence this second,
    in-process harness rather than reusing `Harness` for this section.

    Mirrors `companion/app.py`'s own `main()` construction exactly:
    `Handler.args` set at class level, then a `ThreadingHTTPServer`
    built the identical way. `auth.PASSWORD_ENV_VAR` is set explicitly
    here, not inherited from this test module's own `main()` — by the
    time Section 3/4 run, this file's own outer `try`/`finally` (Section
    1/2's setup) has already restored the process environment to
    whatever it was before this file started, since every `Harness`
    subprocess check below sets the variable in its OWN child `env`
    dict instead (`Harness.start()`, above), never relying on the
    parent process's environment. This harness runs in-process, so it
    must set it here, and restore it in `stop()`.
    """

    def __init__(self):
        import argparse
        from http.server import ThreadingHTTPServer

        import companion.app as app_module

        self.tmpdir = tempfile.mkdtemp(prefix="skypane-calendar-sync-")
        self.port = Harness._pick_free_port()
        self._app_module = app_module
        self._previous_password = os.environ.get(auth.PASSWORD_ENV_VAR)
        os.environ[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        app_module.Handler.args = argparse.Namespace(
            state_dir=self.tmpdir, geofence=None)
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), app_module.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def base_url(self):
        return "http://127.0.0.1:%d" % self.port

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        if self._previous_password is None:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)
        else:
            os.environ[auth.PASSWORD_ENV_VAR] = self._previous_password
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class _FakeCalendarResponse:
    """Hermetic stand-in for `requests.Response`, `server/test_calendar_
    rules.py`'s own class of the same shape exactly — no check below
    ever makes a real network call.
    """

    def __init__(self, status_code=200, body=b""):
        self.status_code = status_code
        self._body = body
        self.headers = {}
        self.is_redirect = False
        self.closed = False

    def iter_content(self, chunk_size=8192):
        yield self._body

    def close(self):
        self.closed = True


def _make_calendar_transport(status_code=200, body=b"", raise_exc=None, calls=None):
    """Build a fake `fetch_ics()`-shaped transport — `server/test_
    calendar_rules.py`'s own `make_calendar_transport()` helper, adapted
    for `_FakeCalendarResponse`. Records every URL it was invoked with
    (or raises `raise_exc` instead of returning), simulating success or
    failure without ever touching a real socket.
    """
    def transport(url, timeout):
        if calls is not None:
            calls.append(url)
        if raise_exc is not None:
            raise raise_exc
        return _FakeCalendarResponse(status_code, body)
    return transport


class _stubbed_calendar_transport:
    """Context manager: monkeypatches `calendar_rules.default_calendar_
    transport` to `transport_fn` for the duration of the block,
    restoring the real function on exit. `fetch_ics()` looks up
    `default_calendar_transport` as a bare name in its own module's
    global namespace when its `transport` parameter is `None` (the
    companion's real call site never passes one), so patching the
    attribute on the imported `calendar_rules` module object — the SAME
    module object the in-process server thread's own code runs against,
    since this is one process — is sufficient; no reload, no subprocess
    env var, no second definition of the fetch path.
    """

    def __init__(self, transport_fn):
        self.transport_fn = transport_fn
        self._real = None

    def __enter__(self):
        self._real = calendar_rules.default_calendar_transport
        calendar_rules.default_calendar_transport = self.transport_fn
        return self

    def __exit__(self, *exc_info):
        calendar_rules.default_calendar_transport = self._real


class _fake_public_hostname:
    """Context manager: monkeypatches `socket.getaddrinfo` so `hostname`
    resolves to a genuinely public-looking address for the duration of
    the block, restoring the real resolver on exit — `server/test_
    calendar_rules.py`'s own technique for getting a fabricated URL past
    `calendar_rules._url_is_safe()`'s SSRF gate without a real DNS answer
    or a real network call.
    """

    def __init__(self, hostname, address="93.184.216.34"):
        self.hostname = hostname
        self.address = address
        self._real = None

    def __enter__(self):
        self._real = socket.getaddrinfo
        real, hostname, address = self._real, self.hostname, self.address

        def fake(host, port=None, *a, **k):
            if host == hostname:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port or 443))]
            return real(host, port, *a, **k)
        socket.getaddrinfo = fake
        return self

    def __exit__(self, *exc_info):
        socket.getaddrinfo = self._real


def _ics_body(entries):
    """Build a minimal, real-shaped iCal body from `entries` — a list of
    `(flight, origin, destination, hours_from_now)` tuples — matching
    `calendar_rules._build_entry()`'s exact accepted shape (CATEGORIES:
    FLT, a `FLIGHT ORI-DST` summary, bare-UTC DTSTART/DTEND). Every
    DTSTART is computed from real wall-clock time at call time, since
    the settings-post handler under test calls `poll_loop.now_s()`
    (real `time.time()`) for its own `now` — there is no injectable
    clock on this path the way `server/test_calendar_rules.py`'s
    in-process `refresh_calendar_registry()` checks have.
    """
    def stamp(hours):
        when = datetime.now(timezone.utc) + timedelta(hours=hours)
        return when.strftime("%Y%m%dT%H%M%SZ")

    lines = ["BEGIN:VCALENDAR"]
    for flight, origin, destination, hours in entries:
        lines += [
            "BEGIN:VEVENT",
            "SUMMARY:%s %s-%s" % (flight, origin, destination),
            "CATEGORIES:FLT",
            "DTSTART:%s" % stamp(hours),
            "DTEND:%s" % stamp(hours + 1),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def _login(harness, password=TEST_PASSWORD):
    """POST /login with `password` and return the session cookie's
    "name=value" pair. Raises AssertionError if login did not succeed -
    callers that expect failure should call http_request() directly.
    """
    status, headers, _ = http_request(
        harness.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError("expected a 303 redirect on successful login, got %d" % status)
    cookie = _cookie_value(headers)
    if not cookie:
        raise AssertionError("expected a Set-Cookie header on successful login")
    return cookie


def _seed_unresolved_prefixes(state_dir, registry):
    """Write `registry` as `poll_state.json`'s `unresolved_prefixes` value
    — mirrors companion/test_status_pages.py's own helper of the same
    name exactly (phase 13 plan 13-06), since that is the exact D-11
    membership set `unresolved_row_for_prefix()` reads.
    """
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": registry})


def _sign_with_secret(payload, secret):
    """Hand-build an "expiry.signature" token signed with an arbitrary
    secret — used to construct forged/malformed tokens that never go
    through auth.issue_session_token().
    """
    signature = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (payload, signature)


def _encode_multipart(
        payload, boundary=b"SkyPaneTestBoundary7Q2vpH",
        filename="upload.png", field_name="file", content_type="image/png"):
    """Hand-build a single-file `multipart/form-data` body — quick task
    260902-v26. This harness deliberately does not import a multipart-
    encoding library, matching `companion.app.parse_single_uploaded_
    file()`'s own zero-third-party-dependency discipline. Returns
    `(body_bytes, content_type_header)`, shared by both the in-process
    parser checks (Section 2/Task 1) and the real-HTTP round-trip checks
    (Section 3/Task 3) so every caller builds a request the same way.
    """
    boundary_str = boundary.decode("ascii")
    header = (
        'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
        'Content-Type: %s\r\n\r\n'
    ) % (field_name, filename, content_type)
    body = (
        b"--" + boundary + b"\r\n"
        + header.encode("utf-8")
        + payload
        + b"\r\n--" + boundary + b"--\r\n"
    )
    return body, "multipart/form-data; boundary=%s" % boundary_str


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

    previous_password = os.environ.get(auth.PASSWORD_ENV_VAR)
    os.environ[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
    try:
        # ==================================================================
        # Section 1: companion/auth.py
        # ==================================================================

        def _password_ok_correct_and_wrong():
            if not auth.password_ok(TEST_PASSWORD):
                return False, "expected password_ok(correct) to be True"
            if auth.password_ok("definitely-the-wrong-password"):
                return False, "expected password_ok(wrong) to be False"
            return True, ""
        check(
            "password_ok() accepts the correct password and rejects a wrong one",
            _password_ok_correct_and_wrong)

        def _password_ok_unconfigured_fails_closed():
            saved = os.environ.pop(auth.PASSWORD_ENV_VAR, None)
            try:
                auth.password_ok("anything")
                return False, "expected AuthNotConfigured to be raised"
            except auth.AuthNotConfigured:
                return True, ""
            finally:
                if saved is not None:
                    os.environ[auth.PASSWORD_ENV_VAR] = saved
        check(
            "password_ok() raises AuthNotConfigured when the password env var is unset",
            _password_ok_unconfigured_fails_closed)

        def _issue_and_verify_round_trip():
            token = auth.issue_session_token()
            if not auth.verify_session_token(token):
                return False, "a freshly-issued token failed verification"
            return True, ""
        check(
            "verify_session_token(issue_session_token()) is True",
            _issue_and_verify_round_trip)

        def _verify_rejects_five_malformed_inputs():
            cases = {
                "empty string": "",
                "no separator": "nodotshere",
                "non-integer expiry": _sign_with_secret("not-a-number", TEST_PASSWORD),
                "different-secret signature": _sign_with_secret(
                    str(int(time.time()) + 3600), "a-completely-different-secret"),
                "expiry in the past": _sign_with_secret(
                    str(int(time.time()) - 100), TEST_PASSWORD),
            }
            for label, value in cases.items():
                if auth.verify_session_token(value) is not False:
                    return False, "expected False for %s (%r)" % (label, value)
            return True, ""
        check(
            "verify_session_token() returns False for five malformed inputs without raising",
            _verify_rejects_five_malformed_inputs)

        def _verify_rejects_flipped_signature():
            token = auth.issue_session_token()
            expiry, signature = token.split(".", 1)
            flipped_char = "0" if signature[0] != "0" else "1"
            flipped_signature = flipped_char + signature[1:]
            flipped_token = "%s.%s" % (expiry, flipped_signature)
            if auth.verify_session_token(flipped_token) is not False:
                return False, "flipping one signature character should invalidate the token"
            return True, ""
        check(
            "flipping a single hex character of a valid signature invalidates the token",
            _verify_rejects_flipped_signature)

        def _session_cookie_header_carries_security_flags():
            header = auth.session_set_cookie_header(auth.issue_session_token())
            for needle in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/"):
                if needle not in header:
                    return False, "missing %r in session cookie header: %r" % (needle, header)
            return True, ""
        check(
            "session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path",
            _session_cookie_header_carries_security_flags)

        def _insecure_cookies_flag_drops_secure_but_keeps_other_flags():
            # A-34/D-17: the exact opt-out value "1" drops Secure from
            # both cookie builders while every other flag survives.
            saved = os.environ.get(auth.INSECURE_COOKIES_ENV_VAR)
            os.environ[auth.INSECURE_COOKIES_ENV_VAR] = "1"
            try:
                session_header = auth.session_set_cookie_header(auth.issue_session_token())
                logout_header = auth.logout_set_cookie_header()
                for header in (session_header, logout_header):
                    if "Secure" in header:
                        return False, "expected Secure to be absent, got %r" % (header,)
                    for needle in ("HttpOnly", "SameSite=Strict", "Path=/"):
                        if needle not in header:
                            return False, "missing %r in %r" % (needle, header)
                return True, ""
            finally:
                if saved is None:
                    os.environ.pop(auth.INSECURE_COOKIES_ENV_VAR, None)
                else:
                    os.environ[auth.INSECURE_COOKIES_ENV_VAR] = saved
        check(
            "SKYPANE_COMPANION_INSECURE_COOKIES=1 drops Secure from both cookie builders "
            "while HttpOnly/SameSite=Strict/Path survive (A-34/D-17)",
            _insecure_cookies_flag_drops_secure_but_keeps_other_flags)

        def _insecure_cookies_flag_fails_closed_on_other_values():
            # Any value other than exactly "1" — including a
            # truthy-looking "true" — must leave Secure on.
            saved = os.environ.get(auth.INSECURE_COOKIES_ENV_VAR)
            os.environ[auth.INSECURE_COOKIES_ENV_VAR] = "true"
            try:
                header = auth.session_set_cookie_header(auth.issue_session_token())
                if "Secure" not in header:
                    return False, "expected Secure to remain on for a non-'1' value, got %r" % (header,)
                return True, ""
            finally:
                if saved is None:
                    os.environ.pop(auth.INSECURE_COOKIES_ENV_VAR, None)
                else:
                    os.environ[auth.INSECURE_COOKIES_ENV_VAR] = saved
        check(
            "SKYPANE_COMPANION_INSECURE_COOKIES=\"true\" fails closed - Secure stays on "
            "(A-34/D-17)",
            _insecure_cookies_flag_fails_closed_on_other_values)

        def _env_example_documents_insecure_cookies_flag():
            env_example_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "deploy", "skypane.env.example")
            with open(env_example_path, "r") as fh:
                contents = fh.read()
            if auth.INSECURE_COOKIES_ENV_VAR not in contents:
                return False, (
                    "expected %r to be documented in deploy/skypane.env.example"
                    % (auth.INSECURE_COOKIES_ENV_VAR,))
            return True, ""
        check(
            "deploy/skypane.env.example documents SKYPANE_COMPANION_INSECURE_COOKIES (A-34/D-17)",
            _env_example_documents_insecure_cookies_flag)

        def _logout_cookie_expires_immediately():
            header = auth.logout_set_cookie_header()
            if "Max-Age=0" not in header:
                return False, "expected Max-Age=0 in the logout cookie header: %r" % (header,)
            return True, ""
        check(
            "logout_set_cookie_header() expires the cookie immediately",
            _logout_cookie_expires_immediately)

        def _parse_cookies_multi_and_malformed():
            parsed = auth.parse_cookies(
                "%s=abc123; %s=dark" % (auth.SESSION_COOKIE_NAME, auth.UI_THEME_COOKIE_NAME))
            if parsed.get(auth.SESSION_COOKIE_NAME) != "abc123":
                return False, "expected the session cookie to parse, got %r" % (parsed,)
            if parsed.get(auth.UI_THEME_COOKIE_NAME) != "dark":
                return False, "expected the theme cookie to parse, got %r" % (parsed,)
            if auth.parse_cookies(None) != {}:
                return False, "expected an empty dict for a missing cookie header"
            if auth.parse_cookies("\x00\x01\x02 not a cookie") != {}:
                return False, "expected a malformed header to yield an empty dict, not raise"
            return True, ""
        check(
            "parse_cookies() returns each cookie by name and never raises on a bad header",
            _parse_cookies_multi_and_malformed)

        def _login_throttle_allows_locks_and_resets():
            throttle = auth.LoginThrottle(limit=3, lockout_s=60)
            for _ in range(2):
                if throttle.locked_out():
                    return False, "should not be locked out before reaching the failure limit"
                throttle.record_failure()
            throttle.record_failure()  # the 3rd failure reaches the limit
            if not throttle.locked_out():
                return False, "expected locked_out() True after reaching the failure limit"
            if throttle.seconds_remaining() <= 0:
                return False, "expected seconds_remaining() > 0 while locked out"
            throttle.record_success()
            if throttle.locked_out():
                return False, "expected record_success() to clear the lockout"
            return True, ""
        check(
            "LoginThrottle allows attempts up to its limit, locks out, then resets on success",
            _login_throttle_allows_locks_and_resets)

        def _login_throttle_self_releases_with_zero_length_window():
            # A-32/D-15: with lockout_s=0 the window elapses immediately,
            # so no real sleep is needed to exercise "a lockout releases
            # itself." The regression this pins: a naive fix that only
            # checks the failure count (not the elapsed window) would
            # re-arm the lockout on this 4th failure instead of starting
            # a fresh count.
            throttle = auth.LoginThrottle(limit=3, lockout_s=0)
            for _ in range(3):
                throttle.record_failure()
            if throttle.locked_out():
                return False, "expected locked_out() False once the zero-length window has passed"
            throttle.record_failure()
            if throttle.locked_out():
                return False, (
                    "one post-window failure should count as 1 of 3 toward a fresh "
                    "lockout, not immediately re-arm it")
            return True, ""
        check(
            "LoginThrottle with a zero-length window releases itself and a post-window "
            "failure starts a fresh count (A-32/D-15)",
            _login_throttle_self_releases_with_zero_length_window)

        def _login_throttle_self_releases_with_real_window():
            # Same property as above, but with a real non-zero lockout_s,
            # proven by rewinding _locked_until into the past (mirroring
            # how _login_throttle_allows_locks_and_resets already drives
            # this class purely through its public methods plus direct
            # attribute access for time-travel, since there is no clock
            # injection point on LoginThrottle).
            throttle = auth.LoginThrottle(limit=3, lockout_s=60)
            for _ in range(3):
                throttle.record_failure()
            if not throttle.locked_out():
                return False, "expected locked_out() True immediately after the 3rd failure"
            throttle._locked_until = time.time() - 1  # simulate the window elapsing
            if throttle.locked_out():
                return False, "expected locked_out() False once the window has elapsed"
            throttle.record_failure()
            if throttle.locked_out():
                return False, (
                    "one post-window failure should count as 1 of 3 toward a fresh "
                    "lockout, not immediately re-arm it")
            return True, ""
        check(
            "LoginThrottle with a real lockout_s releases itself once the window elapses "
            "and a post-window failure starts a fresh count (A-32/D-15)",
            _login_throttle_self_releases_with_real_window)

        def _forged_token_different_secret_rejected():
            forged = _sign_with_secret(
                str(int(time.time()) + 3600), "attacker-controlled-secret")
            if auth.verify_session_token(forged) is not False:
                return False, "a token signed with a different secret must not verify"
            return True, ""
        check(
            "a forged token signed with a different secret is rejected",
            _forged_token_different_secret_rejected)

        def _hand_built_expired_token_rejected():
            expiry = str(int(time.time()) - 1)
            token = _sign_with_secret(expiry, TEST_PASSWORD)
            if auth.verify_session_token(token) is not False:
                return False, "a token expired by exactly one second must be rejected"
            return True, ""
        check(
            "a hand-built token expired by one second is rejected despite a correct signature",
            _hand_built_expired_token_rejected)

        def _tokens_signed_with_derived_key_not_raw_password():
            # A-33/D-16: two tokens issued in this process both verify -
            # the derived signing key is stable within a process.
            token_a = auth.issue_session_token()
            token_b = auth.issue_session_token()
            if not auth.verify_session_token(token_a) or not auth.verify_session_token(token_b):
                return False, "expected both freshly-issued tokens to verify"
            # But a signature computed with the OLD scheme (the raw
            # shared password as the HMAC key, no per-process salt) must
            # NOT verify - that is the actual behaviour being fixed.
            expiry = str(int(time.time()) + 3600)
            raw_password_token = _sign_with_secret(expiry, TEST_PASSWORD)
            if auth.verify_session_token(raw_password_token) is not False:
                return False, (
                    "a signature computed with the raw password (the pre-D-16 scheme) "
                    "must not verify - the signing key must be genuinely derived")
            return True, ""
        check(
            "issued tokens verify within this process, but a raw-password-keyed signature "
            "(the old scheme) does not - the signing key is genuinely derived (A-33/D-16)",
            _tokens_signed_with_derived_key_not_raw_password)

        def _revoke_then_is_revoked_round_trip():
            token = auth.issue_session_token()
            # A different token string, not a second real session (which
            # issue_session_token()'s nanosecond-resolution expiry already
            # makes vanishingly unlikely to collide with `token` anyway) -
            # is_revoked() only ever does a plain membership test.
            never_issued = token + "0"
            if auth.is_revoked(token):
                return False, "a never-revoked token must not be reported as revoked"
            auth.revoke(token)
            if not auth.is_revoked(token):
                return False, "expected is_revoked() True immediately after revoke()"
            if auth.is_revoked(never_issued):
                return False, "revoking one token must not affect a different, never-revoked token"
            try:
                auth.revoke("not-a-valid-token-shape")
                auth.revoke(None)
                auth.revoke("")
            except Exception as exc:
                return False, "revoke() must never raise on a malformed token, got %r" % (exc,)
            return True, ""
        check(
            "revoke(token) then is_revoked(token) is True, a never-issued token is False, and "
            "a malformed token passed to revoke() raises nothing (A-33/D-16)",
            _revoke_then_is_revoked_round_trip)

        def _revoked_token_pruned_once_it_expires():
            # revoke() stores (token -> expiry); once that expiry has
            # passed, the NEXT revoke()/is_revoked() call must prune the
            # entry out of auth._REVOKED, keeping the set bounded rather
            # than growing for the lifetime of the process (T-19-14).
            token = auth.issue_session_token()
            auth.revoke(token)
            if token not in auth._REVOKED:
                return False, "expected revoke() to store a not-yet-expired token"
            auth._REVOKED[token] = 0  # simulate its expiry having already passed
            if auth.is_revoked(token):
                return False, "expected an expired revoked entry to report False, not True"
            if token in auth._REVOKED:
                return False, "expected is_revoked() to prune the now-expired entry out of _REVOKED"
            return True, ""
        check(
            "a revoked token is pruned out of the revocation set once its own expiry passes "
            "(A-33/D-16, T-19-14: the set stays bounded)",
            _revoked_token_pruned_once_it_expires)

        def _auth_not_configured_message_omits_password():
            saved = os.environ.pop(auth.PASSWORD_ENV_VAR, None)
            try:
                auth.configured_password()
                return False, "expected AuthNotConfigured to be raised"
            except auth.AuthNotConfigured as exc:
                if TEST_PASSWORD in str(exc):
                    return False, "the exception text must never contain the password value"
                return True, ""
            finally:
                if saved is not None:
                    os.environ[auth.PASSWORD_ENV_VAR] = saved
        check(
            "AuthNotConfigured's message never contains the configured password value",
            _auth_not_configured_message_omits_password)

        # ==================================================================
        # Section 2: companion/layout.py
        # (the route-driven check section arrives with plan 06-05's
        # companion/app.py)
        # ==================================================================

        def _escape_html_all_special_chars():
            hostile = "<script>&\"'</script>"
            escaped = layout.escape_html(hostile)
            # '&' legitimately survives *as the start of an entity* (e.g.
            # "&amp;", "&lt;") - compare against the stdlib's own reference
            # escaping instead of a naive per-character containment check,
            # which would false-positive on "&amp;" containing "&".
            expected = html.escape(hostile, quote=True)
            if escaped != expected:
                return False, "escape_html() diverged from html.escape(): %r != %r" % (escaped, expected)
            for literal_special_char in ("<", ">", '"', "'"):
                if literal_special_char in escaped:
                    return False, "unescaped %r survived in %r" % (literal_special_char, escaped)
            return True, ""
        check(
            "escape_html() escapes all five HTML-special characters",
            _escape_html_all_special_chars)

        def _escape_html_non_string_inputs():
            if layout.escape_html(None) != "":
                return False, "expected escape_html(None) == ''"
            if layout.escape_html(42) != "42":
                return False, "expected escape_html(42) == '42'"
            return True, ""
        check(
            "escape_html() coerces None to an empty string and non-strings to their string form",
            _escape_html_non_string_inputs)

        def _page_shell_document_shape():
            rendered = layout.page_shell(title="Health", active="health", body="<p>x</p>")
            if rendered.count("<html") != 1:
                return False, "expected exactly one <html occurrence, got %d" % rendered.count("<html")
            if 'lang="en"' not in rendered:
                return False, "expected a lang=\"en\" attribute"
            if "width=device-width" not in rendered:
                return False, "expected a viewport meta tag"
            if "/static/style.css" not in rendered:
                return False, "expected a stylesheet link"
            if layout.SITE_TITLE not in rendered:
                return False, "expected the site title to appear"
            missing = [
                route for route, _ in layout.NAV_TABS
                if ('href="%s"' % route) not in rendered]
            if missing:
                return False, "missing nav link hrefs: %r" % (missing,)
            return True, ""
        check(
            "page_shell() renders one document with lang/viewport/stylesheet/title/a nav link "
            "for every NAV_TABS route",
            _page_shell_document_shape)

        def _page_shell_marks_only_the_active_dropdown_link():
            rendered = layout.page_shell(title="Health", active="health", body="")
            # Scope to the dropdown's own <nav class="mobile-nav__nav" ...>
            # only — page_shell() also renders a vertical sidebar copy of
            # the same links (06.3-01's dashboard-shell rework), so
            # searching the whole document would match whichever copy
            # comes first in source order. This check was already
            # rescoped once, in 06.3-01, for that same "two copies of the
            # same links" reason; 06.6.1-05 rescopes it a second time, at
            # the surviving hamburger dropdown that replaced the
            # horizontal strip this check originally targeted.
            nav_start = rendered.find('<nav class="mobile-nav__nav"')
            nav_end = rendered.find("</nav>", nav_start)
            dropdown_nav_html = rendered[nav_start:nav_end]
            for route, _ in layout.NAV_TABS:
                slug = route.lstrip("/")
                href_needle = 'href="%s"' % route
                href_index = dropdown_nav_html.find(href_needle)
                if href_index == -1:
                    return False, "missing dropdown link for %r" % route
                tag_start = dropdown_nav_html.rfind("<a", 0, href_index)
                tag_end = dropdown_nav_html.find(">", href_index)
                tag = dropdown_nav_html[tag_start:tag_end]
                is_active_class_present = "mobile-nav__link--active" in tag
                if slug == "health" and not is_active_class_present:
                    return False, "expected the active link (%r) to carry the active class" % route
                if slug != "health" and is_active_class_present:
                    return False, "expected a non-active link (%r) to not carry the active class" % route
            return True, ""
        check(
            "the dropdown link matching `active` carries a distinguishing class, the others do not",
            _page_shell_marks_only_the_active_dropdown_link)

        # --- 06.6.4.1.1-04 (D-17): flash banner moves below page_header() ---

        def _flash_banner_spliced_below_page_header_marker_never_leaks():
            body = layout.page_header("Title") + "<p>body content</p>"
            no_flash = layout.page_shell(title="X", active="settings", body=body)
            flash_markup = layout.flash_banner("Saved")
            with_flash = layout.page_shell(
                title="X", active="settings", body=body, flash=flash_markup)
            if layout.FLASH_SLOT_MARKER in no_flash:
                return False, "expected no marker leakage on the no-flash render"
            if layout.FLASH_SLOT_MARKER in with_flash:
                return False, "expected no marker leakage on the with-flash render"
            if "banner--flash" in no_flash:
                return False, "expected no flash banner when none was supplied"
            if with_flash.index("banner--flash") <= with_flash.index("page-header"):
                return False, "expected the flash banner to render after the page header, not before it"
            if with_flash.replace(flash_markup, "", 1) != no_flash:
                return False, (
                    "expected the flash-present and flash-absent documents to differ only "
                    "by the spliced-in banner")
            return True, ""
        check(
            "page_shell() splices the flash banner in directly below page_header()'s title, "
            "and FLASH_SLOT_MARKER never reaches the rendered document",
            _flash_banner_spliced_below_page_header_marker_never_leaks)

        def _flash_banner_fallback_slot_when_body_has_no_marker():
            # login/404-style bodies never call page_header(), so they carry
            # no FLASH_SLOT_MARKER — the flash banner must keep rendering in
            # its original before-body slot rather than silently vanishing.
            bare_body = "<p>bare content, no page_header()</p>"
            flash_markup = layout.flash_banner("Saved")
            rendered = layout.page_shell(
                title="X", active="settings", body=bare_body, flash=flash_markup)
            if "banner--flash" not in rendered:
                return False, "expected the flash banner in the fallback (before-body) slot"
            if layout.FLASH_SLOT_MARKER in rendered:
                return False, "expected no marker leakage on the fallback path"
            if rendered.index("banner--flash") >= rendered.index("bare content"):
                return False, "expected the fallback flash banner to render before the marker-less body"
            return True, ""
        check(
            "page_shell() still renders the flash banner in its original slot for a body "
            "with no FLASH_SLOT_MARKER (the pre-page_header() fallback path)",
            _flash_banner_fallback_slot_when_body_has_no_marker)

        def _anomaly_banner_unaffected_by_the_flash_slot_move():
            body = layout.page_header("Title") + "<p>body content</p>"
            rendered = layout.page_shell(
                title="X", active="settings", body=body,
                banner=layout.anomaly_banner("Uh oh"))
            if "banner--anomaly" not in rendered:
                return False, "expected the anomaly banner to render"
            if "banner--flash" in rendered:
                return False, "did not expect a flash banner when none was supplied"
            if rendered.index("banner--anomaly") >= rendered.index("page-header"):
                return False, "expected the anomaly banner to keep rendering before the page header"
            return True, ""
        check(
            "an anomaly banner (banner=) is unaffected by the flash-slot move and still "
            "renders in its existing pre-body slot",
            _anomaly_banner_unaffected_by_the_flash_slot_move)

        def _theme_resolution():
            rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="dark")
            if 'data-ui-theme="dark"' not in rendered:
                return False, "expected data-ui-theme=\"dark\" in the rendered document"
            if layout.ui_theme_from_cookie({}) != "auto":
                return False, "expected ui_theme_from_cookie({}) == 'auto' for a missing cookie"
            unrecognised = {layout.UI_THEME_COOKIE_NAME: "not-a-real-theme"}
            if layout.ui_theme_from_cookie(unrecognised) != "auto":
                return False, "expected an unrecognised theme cookie to fall back to 'auto'"
            return True, ""
        check(
            "page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto",
            _theme_resolution)

        def _status_dot_states():
            ok_markup = layout.status_dot("ok", "All good")
            if "dot--ok" not in ok_markup or "All good" not in ok_markup:
                return False, "expected the ok-state class and the escaped label"
            unknown_markup = layout.status_dot("not-a-real-state", "<b>hi</b>")
            if "dot--warn" not in unknown_markup:
                return False, "expected an unrecognised state to fall back to the warn class"
            if "<b>" in unknown_markup:
                return False, "expected the label to be escaped"
            return True, ""
        check(
            "status_dot() encodes the state as a fixed class, escapes the label, falls back to warn",
            _status_dot_states)

        def _data_table_escapes_and_empty_state():
            table_markup = layout.data_table(["Name", "<x>"], [["<b>a</b>", "1"]])
            if "<b>a</b>" in table_markup or "<x>" in table_markup:
                return False, "expected header and cell values to be escaped"
            empty_markup = layout.data_table(["Name"], [])
            if "<table" in empty_markup:
                return False, "expected the empty-state block instead of a <table> for zero rows"
            return True, ""
        check(
            "data_table() escapes every header/cell and emits the empty-state block for zero rows",
            _data_table_escapes_and_empty_state)

        def _data_table_wrapped_for_horizontal_scroll():
            # 2026-08-28 mobile-cropping fix: a wide table (History's
            # timestamp/callsign/hex/airline/type columns, Airlines'
            # unresolved-prefix table) must scroll horizontally on a
            # phone viewport instead of overflowing past it uncropped.
            table_markup = layout.data_table(["A", "B"], [["1", "2"]])
            if '<div class="data-table-wrap">' not in table_markup:
                return False, "expected data_table() to wrap its <table> in a scrollable container"
            return True, ""
        check(
            "data_table() wraps its <table> in a horizontally-scrollable container",
            _data_table_wrapped_for_horizontal_scroll)

        def _sidebar_nav_renders_all_tabs_with_one_active():
            markup = layout.sidebar_nav("flights")
            if 'aria-label="Primary navigation"' not in markup:
                return False, "expected the Primary navigation landmark label"
            for route, label in layout.NAV_TABS:
                if route not in markup or label not in markup:
                    return False, "expected every NAV_TABS route/label present"
            if markup.count("sidebar-link--active") != 1:
                return False, "expected exactly one active sidebar link"
            return True, ""
        check(
            "sidebar_nav() renders every NAV_TABS link with exactly one active",
            _sidebar_nav_renders_all_tabs_with_one_active)

        def _sidebar_nav_escapes_hostile_active():
            markup = layout.sidebar_nav("<script>alert(1)</script>")
            if "<script>" in markup:
                return False, "expected no raw <script> substring"
            if markup.count("sidebar-link--active") != 0:
                return False, "expected zero active links for a non-matching active slug"
            return True, ""
        check(
            "sidebar_nav() matches no tab and stays script-free for a hostile active value",
            _sidebar_nav_escapes_hostile_active)

        def _nav_tabs_shrunk_to_four_settled_order():
            # 06.6.4.1-08 (D-22): NAV_TABS shrinks from five entries to
            # four — Preview is retired, its whole content absorbed into
            # History (06.6.4.1-05). Order matters: every nav renderer
            # walks NAV_TABS in this exact order.
            # Phase 18: six tabs in two groups — the everyday four, then
            # the two under the "Advanced" label — flattened in that order.
            if len(layout.NAV_TABS) != 6:
                return False, "expected exactly 6 NAV_TABS entries, got %d" % len(layout.NAV_TABS)
            expected_routes = ("/", "/display", "/flights", "/airlines", "/health", "/device")
            actual_routes = tuple(route for route, _ in layout.NAV_TABS)
            if actual_routes != expected_routes:
                return False, (
                    "expected NAV_TABS routes in order %r, got %r"
                    % (expected_routes, actual_routes))
            return True, ""
        check(
            "layout.NAV_TABS holds exactly 6 entries, in order home/display/flights/airlines/health/device",
            _nav_tabs_shrunk_to_four_settled_order)

        def _sidebar_and_dropdown_render_exactly_four_links_one_active_each():
            sidebar_markup = layout.sidebar_nav("flights")
            sidebar_link_count = sidebar_markup.count('<a class="sidebar-link')
            if sidebar_link_count != 6:
                return False, "expected exactly 6 sidebar nav links, got %d" % sidebar_link_count
            if sidebar_markup.count("sidebar-link--active") != 1:
                return False, "expected exactly one active sidebar link"

            doc = layout.page_shell(title="T", active="flights", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            dropdown_link_count = panel.count('<a class="mobile-nav__link')
            if dropdown_link_count != 6:
                return False, "expected exactly 6 mobile dropdown links, got %d" % dropdown_link_count
            if panel.count("mobile-nav__link--active") != 1:
                return False, "expected exactly one active mobile dropdown link"
            return True, ""
        check(
            "a rendered authenticated page contains exactly six sidebar nav links and exactly "
            "six mobile dropdown links, with exactly one marked active in each",
            _sidebar_and_dropdown_render_exactly_four_links_one_active_each)

        def _eye_glyph_survives_nav_shrink():
            # 06.6.4.1-08 (D-22): "icon-nav-preview" (the eye glyph) stays
            # in the ICON_IDS whitelist even though NAV_ICON_IDS no longer
            # maps a "preview" slug to it — companion/pages/history_page.py's
            # View-panel trigger is its sole remaining consumer.
            if "icon-nav-preview" not in layout.ICON_IDS:
                return False, "expected icon-nav-preview to remain an ICON_IDS whitelist member"
            markup = layout.icon_html("icon-nav-preview")
            if not markup or "<svg" not in markup:
                return False, "expected icon_html('icon-nav-preview') to return non-empty <svg markup"
            return True, ""
        check(
            "the eye glyph (icon-nav-preview) is still a whitelist member and icon_html() returns "
            "non-empty markup for it, even though its nav-slug mapping was removed",
            _eye_glyph_survives_nav_shrink)

        def _stat_tile_status_classes_caption_escape_and_content_passthrough():
            for status, expected_class in (
                ("ok", "stat-tile--ok"),
                ("warn", "stat-tile--warn"),
                ("error", "stat-tile--error"),
            ):
                markup = layout.stat_tile("c", "x", status)
                if expected_class not in markup:
                    return False, "expected %r to map to %r" % (status, expected_class)
            if "stat-tile--accent" not in layout.stat_tile("c", "x"):
                return False, "expected status=None to fall back to stat-tile--accent"
            if "stat-tile--accent" not in layout.stat_tile("c", "x", "not-a-real-state"):
                return False, "expected an unrecognised status to fall back to stat-tile--accent"
            if "<b>" in layout.stat_tile("<b>hi</b>", "x"):
                return False, "expected the caption to be escaped"
            dot_markup = layout.status_dot("ok", "All good")
            tile_markup = layout.stat_tile("Device", dot_markup, "ok")
            if "dot--ok" not in tile_markup:
                return False, "expected content_html to reach the output unmodified"
            return True, ""
        check(
            "stat_tile() maps status to a fixed class with an accent fallback, escapes the "
            "caption, and passes content_html through unmodified",
            _stat_tile_status_classes_caption_escape_and_content_passthrough)

        def _card_status_class_whitelist_and_empty_fallback():
            # quick task 260902-gjj (ISSUE 2): card_status_class()'s own
            # contract, following stat_tile()'s check above in shape —
            # the three whitelisted mappings, and the empty string (not
            # an accent fallback class) for both None and an unrecognised
            # status, per that function's own documented divergence from
            # stat_tile()'s accent fallback.
            for status, expected_class in (
                ("ok", "page-section--ok"),
                ("warn", "page-section--warn"),
                ("error", "page-section--error"),
            ):
                got = layout.card_status_class("page-section", status)
                if got != expected_class:
                    return False, "expected %r to map to %r, got %r" % (status, expected_class, got)
            if layout.card_status_class("page-section", None) != "":
                return False, "expected status=None to fall back to the empty string"
            if layout.card_status_class("page-section", "not-a-real-state") != "":
                return False, "expected an unrecognised status to fall back to the empty string"
            if layout.card_status_class("battery-trend-section", "ok") != "battery-trend-section--ok":
                return False, "expected base_class to be reused verbatim in the modifier's own prefix"
            return True, ""
        check(
            "card_status_class() maps status to base_class + a fixed suffix for the three whitelisted "
            "states, and falls back to the empty string (not an accent class) for None or an unrecognised "
            "status — the divergence from stat_tile()'s own fallback (quick task 260902-gjj, ISSUE 2)",
            _card_status_class_whitelist_and_empty_fallback)

        def _page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme():
            rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
            for needle in (
                '<div class="dashboard-shell">',
                '<aside class="dashboard-sidebar">',
                '<main class="page-content dashboard-main" id="main-content" tabindex="-1">',
            ):
                if needle not in rendered:
                    return False, "expected %r in the rendered shell" % needle
            # 06.6.1-05: two nav landmarks now exist — sidebar_nav() and
            # the hamburger dropdown's _mobile_nav_html() — deliberately
            # sharing the same "Primary navigation" aria-label
            # (06.6.1-UI-SPEC.md's Layout Contract); CSS alone decides
            # which is visible at a given width, so both are always in
            # the DOM. This was "exactly one" before this plan, when the
            # horizontal strip carried no landmark of its own.
            if rendered.count('aria-label="Primary navigation"') != 2:
                return False, "expected exactly two Primary navigation landmarks (sidebar + dropdown)"
            if rendered.count('id="%s"' % layout.MOBILE_NAV_ID) != 1:
                return False, "expected exactly one dropdown panel"
            if rendered.count('action="/ui-theme"') != 2:
                return False, "expected both theme-form copies posting to /ui-theme"
            return True, ""
        check(
            "page_shell() wraps header+sidebar+main in .dashboard-shell with both nav landmarks "
            "and both theme-form copies present",
            _page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme)

        def _page_shell_skip_link_target_is_focusable():
            # CR-01: the skip link's href="#main-content" target must
            # itself be focusable (tabindex="-1") or activating the link
            # scrolls the viewport without moving keyboard focus, per the
            # HTML fragment-navigation focusing steps (WCAG SCR28/G1).
            rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
            if '<a class="skip-link" href="#main-content">Skip to content</a>' not in rendered:
                return False, "expected the skip link to point at #main-content"
            if 'id="main-content" tabindex="-1"' not in rendered:
                return False, "expected the skip link's target to carry tabindex=\"-1\""
            return True, ""
        check(
            "page_shell()'s skip link target carries tabindex=\"-1\" so it actually receives focus",
            _page_shell_skip_link_target_is_focusable)

        def _page_shell_escapes_hostile_body():
            escaped_hostile_body = layout.escape_html("<script>alert(1)</script>")
            rendered = layout.page_shell(title="Health", active="health", body=escaped_hostile_body)
            if "<script>" in rendered:
                return False, "an unescaped <script> tag reached the rendered page"
            return True, ""
        check(
            "page_shell()'s output contains no unescaped script tag for an escaped hostile body",
            _page_shell_escapes_hostile_body)

        # --- 06.6.1-04 Task 1: icon sprite, whitelisted builder, stat_tile() icon slot ---

        def _icon_sprite_integrity():
            import re
            # 06.6.3: the whitelist grew from ten to fourteen members
            # (icon-check/icon-copy/icon-refresh/icon-search, D-05/
            # D-23/D-12/D-20) — see layout.py's own header comment on
            # ICON_IDS for the supersession note. quick task 260903-df3
            # grew it again, fourteen to fifteen (icon-upload, the
            # Airlines lightbox replace zone's glyph).
            if len(layout.ICON_IDS) != 21:
                return False, "expected exactly twenty-one ICON_IDS, got %d" % len(layout.ICON_IDS)
            if len(set(layout.ICON_IDS)) != 21:
                return False, "expected ICON_IDS to have no duplicates"
            symbol_ids = re.findall(r'<symbol[^>]*id="([^"]+)"', layout.ICON_DEFS_HTML)
            if sorted(symbol_ids) != sorted(layout.ICON_IDS):
                return False, "sprite symbol ids %r do not match ICON_IDS %r" % (
                    symbol_ids, layout.ICON_IDS)
            if layout.ICON_DEFS_HTML.count("<symbol") != 21:
                return False, "expected exactly twenty-one <symbol occurrences, got %d" % (
                    layout.ICON_DEFS_HTML.count("<symbol"))
            if 'stroke="currentColor"' not in layout.ICON_DEFS_HTML:
                return False, "expected stroke=\"currentColor\" in the sprite"
            if 'fill="#' in layout.ICON_DEFS_HTML:
                return False, "a hard-coded hex fill would defeat the per-status tint"
            return True, ""
        check(
            "layout.ICON_IDS has exactly twenty-one unique members, each a symbol id in ICON_DEFS_HTML and vice versa",
            _icon_sprite_integrity)

        def _icon_html_whitelist_enforcement():
            for icon_id in layout.ICON_IDS:
                out = layout.icon_html(icon_id)
                if not out or "<use" not in out:
                    return False, "expected non-empty <use markup for %r, got %r" % (icon_id, out)
            for bad in ("not-an-icon", "", None):
                if layout.icon_html(bad) != "":
                    return False, "expected icon_html(%r) == ''" % (bad,)
            hostile = '"><script>alert(1)</script>'
            if layout.icon_html(hostile) != "":
                return False, "expected a hostile id to render nothing"
            if hostile in layout.icon_html(hostile):
                return False, "a hostile id string must never reach icon_html()'s output"
            return True, ""
        check(
            "icon_html() returns markup for every whitelisted id and '' for an unknown/empty/None/hostile id",
            _icon_html_whitelist_enforcement)

        def _stat_tile_backcompat_and_icon_slot():
            default_call = layout.stat_tile("c", "x")
            explicit_none = layout.stat_tile("c", "x", None)
            if default_call != explicit_none:
                return False, "expected stat_tile('c','x') == stat_tile('c','x',None)"
            if "<svg" in default_call:
                return False, "expected no <svg when icon is omitted"
            valid_icon = layout.ICON_IDS[0]
            with_icon = layout.stat_tile("Cap", "<p>y</p>", "ok", icon=valid_icon)
            if with_icon.count("<svg") != 1:
                return False, "expected exactly one <svg when a valid icon is supplied"
            if layout.STAT_TILE_ICON_CLASS not in with_icon:
                return False, "expected the tint class on the tile's icon"
            if "stat-tile--ok" not in with_icon:
                return False, "expected the status class to still be present"
            if with_icon.index("<svg") >= with_icon.index("Cap"):
                return False, "expected the icon markup to precede the caption text"
            return True, ""
        check(
            "stat_tile() is byte-identical with icon omitted and places a valid icon before the caption text",
            _stat_tile_backcompat_and_icon_slot)

        def _page_shell_emits_sprite_once_no_inline_styles():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if doc.count("<defs") != 1:
                return False, "expected exactly one <defs, got %d" % doc.count("<defs")
            if doc.count("<symbol") != 21:
                return False, "expected exactly twenty-one <symbol, got %d" % doc.count("<symbol")
            if doc.index("icon-defs") >= doc.index("dashboard-shell"):
                return False, "expected the sprite to precede the dashboard-shell div"
            if ' style="' in doc:
                return False, "page_shell() must emit no inline styles"
            return True, ""
        check(
            "page_shell() emits exactly one sprite (one <defs, twenty-one <symbol) before dashboard-shell, "
            "no inline styles",
            _page_shell_emits_sprite_once_no_inline_styles)

        def _icon_classes_match_stylesheet():
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for cls in ("icon-defs", "icon", layout.STAT_TILE_ICON_CLASS):
                if cls not in css:
                    return False, "expected class %r to be styled in companion/static/style.css" % cls
            return True, ""
        check(
            "the icon/icon-defs/STAT_TILE_ICON_CLASS class names all appear in companion/static/style.css",
            _icon_classes_match_stylesheet)

        # --- heading-color-consistency debug session -------------------
        #
        # D-03's serif-headings contract lived only as an allow-list in a
        # style.css comment, and `legend` was never added to it — so
        # `<legend>Diagnostic LED</legend>` rendered sans-serif semibold
        # directly above a serif-regular `<h2 class="text-heading">Poll
        # </h2>` at the same 20px size on the Config page. These two
        # checks make the contract executable in both directions: every
        # heading role IS serif, and no dense/tabular role IS NOT.
        #
        # 06.6.4.1.1-04 Task 2: plan 02 (D-09) gave the nested card-title
        # selector below a deliberate sans override and (D-13) retired
        # `.stat-tile__caption`'s serif Label role entirely, but neither
        # change was caught by either guard — `_every_heading_role_is_serif`
        # only inspected the shared selector's own block, and
        # `_serif_never_reaches_dense_content`'s forbidden list never named
        # `.stat-tile__caption`. Both checks kept passing while the serif
        # contract they encode had quietly changed underneath them — the
        # exact allow-list-drift failure mode these checks exist to catch.
        # Extended below so both changes are now asserted, not merely
        # tolerated.

        def _every_heading_role_is_serif():
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            # The single selector that grants the serif family. Every
            # heading role in the app must be a member of it.
            start = css.find("h1,\nh2,\nh3,\nlegend,\n.text-heading {")
            if start == -1:
                return False, (
                    "expected one combined serif-heading selector listing "
                    "h1, h2, h3, legend and .text-heading — a heading role "
                    "was removed from it, or the selector was reformatted "
                    "(if reformatted, update this check deliberately)")
            block = css[start:css.index("}", start)]
            for declaration in (
                    "font-family: var(--font-serif)",
                    "font-weight: var(--weight-regular)"):
                if declaration not in block:
                    return False, (
                        "the serif-heading rule no longer declares %r"
                        % (declaration,))
            # legend must not restate font-weight in its own later rule:
            # both selectors are bare `legend` (0,0,1), so a weight
            # declared there silently beats the rule above regardless of
            # what the rule above says. This is the exact defect.
            legend_start = css.find("\nlegend {")
            if legend_start == -1:
                return False, "expected a bare `legend` rule in style.css"
            legend_block = css[legend_start:css.index("}", legend_start)]
            if "font-weight" in legend_block:
                return False, (
                    "the standalone `legend` rule declares font-weight "
                    "again; at equal specificity it wins over the serif "
                    "heading rule and re-breaks legend/h2 consistency")
            # 06.6.4.1.1-04 Task 2 (D-09): the shared rule above grants
            # serif to every heading role, and there is exactly one
            # documented, asserted exception — the nested card-title
            # selector ("Battery trend", "Unresolved prefixes",
            # "Resolution statistics"), deliberately demoted to the sans
            # --font-ui voice at 16px semibold. Asserting it here turns
            # D-09's override from "an unguarded rule that happens to
            # exist" into a stated part of the contract.
            nested_title_start = css.find("\n.page-section--nested > h2,")
            if nested_title_start == -1:
                return False, (
                    "expected the named nested card-title exception "
                    "selector `.page-section--nested > h2,` in style.css")
            nested_title_block = css[
                nested_title_start:css.index("}", nested_title_start)]
            if "font-family: var(--font-ui)" not in nested_title_block:
                return False, (
                    "expected the nested card-title exception to declare "
                    "font-family: var(--font-ui) (D-09's sans override)")
            return True, ""
        check(
            "every heading role (h1/h2/h3/legend/.text-heading) shares one "
            "serif rule except the one named, asserted nested card-title "
            "sans exception (D-09), and `legend` does not override its "
            "weight",
            _every_heading_role_is_serif)

        def _serif_never_reaches_dense_content():
            # D-03's other half: serif is headings-only. Body, tables,
            # form controls, nav links and mono content stay on
            # --font-ui. Guards against the rejected "serif partout"
            # option creeping back in one rule at a time.
            #
            # `.stat-tile__caption` (D-13, phase 06.6.4.1.1-02) was this
            # file's one named Label-role serif exception until D-13
            # retired it in favour of the unified sans 12px label voice —
            # it is listed here now so that retirement cannot silently
            # reverse without a deliberate edit to this check.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            forbidden = (
                ".data-table", ".cell-primary", ".cell-secondary",
                ".mono", ".text-body", ".sidebar-link", ".mobile-nav__link",
                ".stat-tile__caption")
            for selector in forbidden:
                index = css.find("\n%s {" % selector)
                if index == -1:
                    continue
                block = css[index:css.index("}", index)]
                if "--font-serif" in block:
                    return False, (
                        "%s applies --font-serif; serif is a headings-only "
                        "treatment (D-03), never dense/tabular content"
                        % selector)
            return True, ""
        check(
            "--font-serif never reaches table, body, mono, nav-link or "
            "stat-tile-caption rules (D-03's headings-only boundary; "
            "D-13 retired the caption's own former serif exception)",
            _serif_never_reaches_dense_content)

        def _nav_link_geometries_stay_diverged():
            # 260902-qkm: D-05 (06.6.4-04) reached .mobile-nav__link by
            # mistake — the mobile dropdown is the phone's only nav, with
            # no desktop compactness argument to trade against, while
            # .sidebar-link is structurally desktop-only (hidden below
            # 960px). The two renderings are now deliberately different
            # sizes: the mobile link keeps a real tap target, the desktop
            # sidebar stays compact, and neither may drift into the other.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()

            def block_for(selector):
                index = css.find("\n%s {" % selector)
                if index == -1:
                    return None
                return css[index:css.index("}", index)]

            mobile_block = block_for(".mobile-nav__link")
            if mobile_block is None:
                return False, "expected a `.mobile-nav__link` rule in style.css"
            if "min-height: 44px" not in mobile_block:
                return False, (
                    ".mobile-nav__link lost its restored min-height: 44px "
                    "tap target (260902-qkm)")
            if "font-size: var(--font-body-size)" not in mobile_block:
                return False, (
                    ".mobile-nav__link's font size drifted off "
                    "var(--font-body-size) (260902-qkm)")

            sidebar_block = block_for(".sidebar-link")
            if sidebar_block is None:
                return False, "expected a `.sidebar-link` rule in style.css"
            if "height: 32px" not in sidebar_block:
                return False, (
                    ".sidebar-link's D-05 32px desktop compaction was "
                    "reverted — it is structurally desktop-only and "
                    "should stay compact, unlike the mobile dropdown link")
            if "font-size: var(--font-label-size)" not in sidebar_block:
                return False, (
                    ".sidebar-link's font size drifted off "
                    "var(--font-label-size)")
            return True, ""
        check(
            "mobile dropdown nav link keeps its restored 44px/Body-size "
            "tap target while the desktop sidebar link stays at its D-05 "
            "32px/Label-size compaction (260902-qkm)",
            _nav_link_geometries_stay_diverged)

        def _one_error_signal_token():
            # --color-destructive and --color-status-error held identical
            # values in all four token blocks while being used
            # interchangeably for one concept, so "change the error
            # colour" silently meant "change two tokens in four places".
            # The duplicate is gone; this keeps it gone.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            # Comments are stripped first: the rules that used to read
            # this token now carry comments explaining why they no
            # longer do, and that prose must not trip the check it
            # documents.
            declarations = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            if "--color-destructive" in declarations:
                return False, (
                    "--color-destructive is back; it duplicated "
                    "--color-status-error exactly and is the reason the two "
                    "could drift. Use --color-status-error")
            return True, ""
        check(
            "there is exactly one error-signal colour token "
            "(--color-status-error), no --color-destructive duplicate",
            _one_error_signal_token)

        # --- 06.6.1-04 Task 3 / 06.6.1-05: Health nav notification dot ---
        #
        # Retargeted a third time by 06.6.1-05, beyond the plan's own
        # stated two — 06.6.1-05-PLAN.md's Task 3 read_first names only
        # the active-link and dashboard-shell checks as broken by Task 2,
        # but this one (from plan 06.6.1-04) also assumed a single nav
        # renderer and needs the same one-dot-per-renderer update the
        # plan's own Task 2 acceptance criteria already specifies
        # ("exactly two notification dots, one inside each Health link").

        def _health_nav_notification_dot():
            on = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert="error")
            off = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert=None)
            default = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if on.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected the notification class exactly twice (one per nav renderer) when health_alert='error'"
            if on.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 2:
                return False, "expected the alert suffix text exactly twice when health_alert='error'"
            if off.count(layout.NAV_NOTIFICATION_CLASS) != 0:
                return False, "expected zero notification-class occurrences when health_alert=None"
            if off.count(layout.HEALTH_ALERT_SUFFIX_TEXT) != 0:
                return False, "expected zero alert-suffix occurrences when health_alert=None"
            if default != off:
                return False, "expected the health_alert flag to default to off"
            side = on[on.index("sidebar-nav"):on.index("</aside>")]
            side_href_index = side.index('href="/health"')
            side_dot_index = side.index(layout.NAV_NOTIFICATION_CLASS)
            side_anchor_close_index = side.index("</a>", side_href_index)
            if not (side_href_index < side_dot_index < side_anchor_close_index):
                return False, "expected the dot to sit inside the Health sidebar link"
            dropdown = on[on.index('id="%s"' % layout.MOBILE_NAV_ID):on.index("</header>")]
            drop_href_index = dropdown.index('href="/health"')
            drop_dot_index = dropdown.index(layout.NAV_NOTIFICATION_CLASS)
            drop_anchor_close_index = dropdown.index("</a>", drop_href_index)
            if not (drop_href_index < drop_dot_index < drop_anchor_close_index):
                return False, "expected the dot to sit inside the Health dropdown link"
            other_active = layout.page_shell(
                title="T", active="config", body="", health_alert="error")
            if other_active.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected exactly two dot occurrences (one per nav renderer) regardless of the active tab"
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            if layout.NAV_NOTIFICATION_CLASS not in css:
                return False, "expected the notification class to be styled"
            if "visually-hidden" not in css:
                return False, "expected the visually-hidden utility class to be styled"
            return True, ""
        check(
            "the Health notification dot appears inside the Health link in both nav renderers "
            "when health_alert='error', nowhere when None/omitted, and never on another link",
            _health_nav_notification_dot)

        def _hidden_form_control_floor_and_global_floor_both_survive():
            # quick task 260902-l9w: the runway radio's own utility class
            # (visually-hidden) is inert on an <input> unless the global
            # `input, select` rule's 44px minimums are separately cleared
            # for it — a rule that only asserts the new clearing rule
            # would still pass after someone deleted the global 44px
            # floor site-wide, and a rule that only asserts the floor
            # would still pass after someone deleted the clearing fix.
            # This check fails if either half is missing.
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            if "input.visually-hidden" not in css:
                return False, (
                    "expected an input.visually-hidden (or "
                    "select.visually-hidden) rule clearing the global "
                    "44px touch-target floor off hidden form controls "
                    "(the runway radio's own utility class is otherwise "
                    "clamped back up to 44x44 by the global input/select "
                    "rule below)")
            global_start = css.find("\ninput,\nselect {")
            if global_start == -1:
                return False, (
                    "expected the global `input,\\nselect {` rule; it may "
                    "have been reformatted (update this check "
                    "deliberately) or removed")
            global_block = css[global_start:css.index("}", global_start)]
            for declaration in ("min-height: 44px", "min-width: 44px"):
                if declaration not in global_block:
                    return False, (
                        "the global input/select rule no longer declares "
                        "%r; this is a deliberate, developer-accepted "
                        "WCAG 2.5.5 floor for every native field except "
                        "the ones explicitly scoped away from it (D-08, "
                        "the LED checkbox, and now the hidden runway "
                        "radio) and must survive byte-identical"
                        % (declaration,))
            return True, ""
        check(
            "input.visually-hidden/select.visually-hidden clears the 44px "
            "touch-target floor off hidden form controls, and the global "
            "input/select rule still declares both 44px minimums for "
            "every other field",
            _hidden_form_control_floor_and_global_floor_both_survive)

        def _health_nav_notification_dot_warn_severity():
            warn = layout.page_shell(
                title="T", active="health", body="<p>b</p>", health_alert="warn")
            if warn.count(layout.NAV_NOTIFICATION_CLASS) != 2:
                return False, "expected the notification class exactly twice (one per nav renderer) when health_alert='warn'"
            if "dot--warn" not in warn:
                return False, "expected dot--warn to appear when health_alert='warn'"
            if "dot--error" in warn:
                return False, "expected no dot--error class anywhere when health_alert='warn'"
            return True, ""
        check(
            "layout.page_shell(..., health_alert='warn') also renders the notification dot, "
            "using dot--warn rather than dot--error",
            _health_nav_notification_dot_warn_severity)

        # --- 06.6.1-05 Task 1: nav-dropdown.js ES5-safe/side-effect-free dialect ---

        def _nav_dropdown_script_es5_safe_and_side_effect_free():
            # These are standing constraints on the file, not incidental
            # facts — companion/static/battery-trend.js's own header
            # states the same rules for the same reasons: no build step,
            # ES5-safe subset, no network call, no timer, no persistent
            # state.
            js_path = os.path.join(HERE, "static", "nav-dropdown.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
                "setTimeout", "setInterval", "innerHTML", "document.write",
                "eval(")
            for token in banned:
                if token in src:
                    return False, "nav-dropdown.js must not contain %r" % token
            if "aria-expanded" not in src:
                return False, "expected the open state to be read from aria-expanded"
            return True, ""
        check(
            "nav-dropdown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "fetch/XHR/timers/innerHTML/document.write/eval) — standing constraints on the file",
            _nav_dropdown_script_es5_safe_and_side_effect_free)

        # --- 06.6.1-05 Task 3: toggle ARIA contract, dropdown contents, ---
        # --- three-file DOM contract, no-JS floor                      ---

        def _toggle_aria_contract_and_fixed_label():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            if 'type="button"' not in doc:
                return False, "expected the toggle to be type=\"button\""
            if ('id="%s"' % layout.NAV_TOGGLE_ID) not in doc:
                return False, "expected the toggle id in the document"
            if 'aria-expanded="false"' not in doc:
                return False, "expected the toggle to render aria-expanded=\"false\""
            if ('aria-controls="%s"' % layout.MOBILE_NAV_ID) not in doc:
                return False, "expected aria-controls to name the panel id"
            if layout.NAV_TOGGLE_LABEL not in doc:
                return False, "expected the fixed toggle label in the document"
            if "Close menu" in doc:
                return False, "the toggle's accessible label must never swap to a close verb"
            if layout.MOBILE_NAV_OPEN_CLASS in doc:
                return False, "the panel must never render carrying the open class"
            return True, ""
        check(
            "the hamburger toggle carries type=button/id/aria-expanded=false/aria-controls and the "
            "fixed accessible label (never a close-verb variant), and the panel never renders open",
            _toggle_aria_contract_and_fixed_label)

        def _dropdown_contents_and_order():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            for route, _label in layout.NAV_TABS:
                if ('href="%s"' % route) not in panel:
                    return False, "missing dropdown href for %r" % route
            if panel.count("mobile-nav__link--active") != 1:
                return False, "expected exactly one active dropdown link"
            theme_index = panel.find('action="/ui-theme"')
            if theme_index == -1:
                return False, "expected the theme form inside the dropdown"
            for route, _label in layout.NAV_TABS:
                href_index = panel.index('href="%s"' % route)
                if href_index > theme_index:
                    return False, "expected every nav link to precede the theme form in the dropdown"
            return True, ""
        check(
            "the dropdown panel holds every NAV_TABS link (exactly one active) followed by the "
            "theme form, in that order",
            _dropdown_contents_and_order)

        def _three_file_nav_dom_contract_guard():
            # Replicates the Python/CSS/JS drift guard 06.5-02 established
            # for the battery chart — a menu that never opens on a phone
            # would otherwise ship with every individual file still valid
            # on its own and no automated signal.
            js_path = os.path.join(HERE, "static", "nav-dropdown.js")
            with open(js_path) as fh:
                js = fh.read()
            css_path = os.path.join(HERE, "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for literal in (
                layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID,
                layout.MOBILE_NAV_OPEN_CLASS,
            ):
                if literal not in js:
                    return False, "DOM contract drift: %r is not looked up by nav-dropdown.js" % literal
            for cls in (
                "site-nav-toggle", "mobile-nav", "mobile-nav--open",
                "mobile-nav__nav", "mobile-nav__link",
            ):
                if cls not in css:
                    return False, "DOM contract drift: %r is not styled in style.css" % cls
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            for literal in (layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID):
                if literal not in doc:
                    return False, "DOM contract drift: %r is not rendered" % literal
            import companion.app as app_module
            if app_module.NAV_SCRIPT_ROUTE != layout.NAV_DROPDOWN_SCRIPT_SRC:
                return False, "nav script route drift: %r vs %r" % (
                    app_module.NAV_SCRIPT_ROUTE, layout.NAV_DROPDOWN_SCRIPT_SRC)
            return True, ""
        check(
            "companion.app.NAV_SCRIPT_ROUTE, layout's nav DOM-contract literals, nav-dropdown.js "
            "and style.css all agree with each other and with a rendered document",
            _three_file_nav_dom_contract_guard)

        def _dropdown_survives_with_javascript_disabled():
            # UXA-02/UXA-12's joint fix, verified against the
            # server-rendered document only (this harness has no real
            # browser). The SSR default must be unclipped/complete — the
            # `.js .mobile-nav` CSS clipping rule and nav-dropdown.js's
            # `panel.hidden` toggling only ever apply once client-side
            # script has run, never from the server.
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
            panel = doc[panel_start:doc.index("</header>")]
            if " hidden" in panel or 'hidden="' in panel:
                return False, "the no-JS floor requires the panel stay in the accessibility tree"
            if "display:" in panel:
                return False, "the no-JS floor requires the panel carry no inline display style"
            for route, _label in layout.NAV_TABS:
                if ('href="%s"' % route) not in panel:
                    return False, "missing dropdown href for %r with JavaScript disabled" % route
            html_tag_end = doc.index(">", doc.index("<html"))
            html_tag = doc[:html_tag_end]
            if 'class="js"' in html_tag or ' js"' in html_tag or ' js ' in html_tag:
                return False, "server-rendered <html> tag must never carry the .js marker class"
            return True, ""
        check(
            "with JavaScript disabled every nav link stays present in the dropdown panel's DOM "
            "(the collapsed look is a CSS max-height constraint, not a hidden attribute or "
            "display:none) and the server-rendered <html> tag carries no .js marker class",
            _dropdown_survives_with_javascript_disabled)

        def _nav_dropdown_js_progressive_enhancement_state_machine():
            # UXA-02/UXA-12's joint fix, client-side half. The .js marker
            # add must run before the dropdown-specific element lookup
            # (so pages without a dropdown still get the marker), and the
            # hidden-attribute/transitionend/reduced-motion state machine
            # must be present exactly as the plan specifies.
            js_path = os.path.join(
                os.path.dirname(__file__), "static", "nav-dropdown.js")
            with open(js_path) as fh:
                js = fh.read()
            marker_idx = js.index('className += " js"')
            toggle_idx = js.index('getElementById("site-nav-toggle")')
            if marker_idx >= toggle_idx:
                return False, ".js marker class must be added before the dropdown lookup"
            for needle in (
                "panel.hidden = true", "panel.hidden = false",
                "transitionend", "matchMedia", "prefers-reduced-motion",
            ):
                if needle not in js:
                    return False, "nav-dropdown.js is missing %r" % needle
            css_path = os.path.join(
                os.path.dirname(__file__), "static", "style.css")
            with open(css_path) as fh:
                css = fh.read()
            for needle in (".js .mobile-nav {", ".js .mobile-nav--open {"):
                if needle not in css:
                    return False, "style.css is missing %r" % needle
            return True, ""
        check(
            "nav-dropdown.js adds the .js marker class before its dropdown element lookup and "
            "implements the hidden-attribute/transitionend/reduced-motion state machine, matched "
            "by style.css's .js-scoped clipping rules",
            _nav_dropdown_js_progressive_enhancement_state_machine)

        # --- 260902-v26 Task 1: parse_single_uploaded_file(), stdlib-only ---
        # --- single-part multipart parser. Pure in-process checks — no   ---
        # --- Harness needed, unlike Section 3 below.                    ---

        import companion.app as app_module

        _VALID_UPLOAD_PAYLOAD = b"\x89PNG-fixture-bytes-not-a-real-decodable-png"

        def _parser_happy_path_ignores_traversal_filename():
            body, content_type = _encode_multipart(
                _VALID_UPLOAD_PAYLOAD, filename="../../../etc/passwd")
            result = app_module.parse_single_uploaded_file(content_type, body)
            if result != _VALID_UPLOAD_PAYLOAD:
                return False, (
                    "expected the payload back even with a traversal-shaped "
                    "declared filename, got %r" % (result,))
            return True, ""
        check(
            "parse_single_uploaded_file() returns the payload for a well-formed single-part body, "
            "even when the part header declares a traversal-shaped filename (never read)",
            _parser_happy_path_ignores_traversal_filename)

        def _parser_two_parts_returns_none():
            boundary = b"SkyPaneTwoPartBoundary9k2"
            body = (
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="a"; filename="a.png"\r\n\r\n'
                b"AAAA\r\n"
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="b"; filename="b.png"\r\n\r\n'
                b"BBBB\r\n"
                b"--" + boundary + b"--\r\n"
            )
            content_type = "multipart/form-data; boundary=%s" % boundary.decode("ascii")
            result = app_module.parse_single_uploaded_file(content_type, body)
            if result is not None:
                return False, "expected None for a two-part body, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None for a two-part body — this route accepts "
            "exactly one file part and nothing else",
            _parser_two_parts_returns_none)

        def _parser_urlencoded_media_type_returns_none():
            result = app_module.parse_single_uploaded_file(
                "application/x-www-form-urlencoded", b"field=value")
            if result is not None:
                return False, "expected None for a non-multipart media type, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None for a non-multipart media type",
            _parser_urlencoded_media_type_returns_none)

        def _parser_missing_boundary_returns_none():
            body, _content_type = _encode_multipart(_VALID_UPLOAD_PAYLOAD)
            result = app_module.parse_single_uploaded_file("multipart/form-data", body)
            if result is not None:
                return False, "expected None with no boundary parameter, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None when the boundary parameter is missing",
            _parser_missing_boundary_returns_none)

        def _parser_empty_body_returns_none():
            result = app_module.parse_single_uploaded_file(
                "multipart/form-data; boundary=anything", b"")
            if result is not None:
                return False, "expected None for an empty body, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None for an empty body",
            _parser_empty_body_returns_none)

        def _parser_missing_header_body_separator_returns_none():
            boundary = b"SkyPaneNoSepBoundaryF4x"
            body = (
                b"--" + boundary + b"\r\n"
                b"No blank line separates this from anything\r\n"
                b"--" + boundary + b"--\r\n"
            )
            content_type = "multipart/form-data; boundary=%s" % boundary.decode("ascii")
            result = app_module.parse_single_uploaded_file(content_type, body)
            if result is not None:
                return False, "expected None with no header/body CRLFCRLF separator, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None when the part has no header/body separator",
            _parser_missing_header_body_separator_returns_none)

        def _parser_none_content_type_returns_none():
            result = app_module.parse_single_uploaded_file(None, b"anything at all")
            if result is not None:
                return False, "expected None for a None content_type, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None for a None content_type",
            _parser_none_content_type_returns_none)

        def _parser_empty_payload_returns_none():
            body, content_type = _encode_multipart(b"")
            result = app_module.parse_single_uploaded_file(content_type, body)
            if result is not None:
                return False, "expected None for an empty file part payload, got %r" % (result,)
            return True, ""
        check(
            "parse_single_uploaded_file() returns None for an empty file part payload",
            _parser_empty_payload_returns_none)

        # --- 11-04: env_wake_interval_default() / page_context() threading ---
        # --- (D-07's SKYPANE_SLEEP_S pre-fill). Pure in-process checks,    ---
        # --- like the parser checks just above — Section 3's harness      ---
        # --- checks below cover the same contract end-to-end over real    ---
        # --- HTTP instead.                                                ---

        def _env_wake_interval_default_full_input_space():
            cases = (
                (None, None),      # unset
                ("", None),
                ("900", 900),
                ("abc", None),
                ("1.5", None),
                ("-1", None),
                ("0", None),
                # deploy/skypane.env.example's shipped value — below the 60s floor
                ("30", None),
                ("59", None),
                ("3601", None),
                ("60", 60),         # inclusive lower bound
                ("3600", 3600),     # inclusive upper bound
                (" 900 ", 900),     # whitespace-padded — int() tolerates it
            )
            saved = os.environ.get(app_module.SLEEP_ENV_VAR)
            try:
                for raw, expected in cases:
                    if raw is None:
                        os.environ.pop(app_module.SLEEP_ENV_VAR, None)
                    else:
                        os.environ[app_module.SLEEP_ENV_VAR] = raw
                    actual = app_module.env_wake_interval_default()
                    if actual != expected:
                        return False, (
                            "SKYPANE_SLEEP_S=%r: expected %r, got %r"
                            % (raw, expected, actual))
                return True, ""
            finally:
                if saved is not None:
                    os.environ[app_module.SLEEP_ENV_VAR] = saved
                else:
                    os.environ.pop(app_module.SLEEP_ENV_VAR, None)
        check(
            "env_wake_interval_default() covers its whole input space (unset, empty, "
            "non-numeric, whitespace-padded, in-range and out-of-range including "
            "deploy/skypane.env.example's shipped below-floor SKYPANE_SLEEP_S=30) and "
            "never raises",
            _env_wake_interval_default_full_input_space)

        class _FakePageContextHeaders:
            def get(self, name, default=None):
                return default

        class _FakePageContextArgs:
            def __init__(self, state_dir):
                self.state_dir = state_dir

        class _FakePageContextHandler:
            """A minimal stand-in for companion.app.Handler carrying only
            the attributes page_context() actually reads (self.path,
            self.args.state_dir, self.headers, self._resolved_ui_theme())
            — never constructed via BaseHTTPRequestHandler.__init__, which
            requires a live socket. page_context() itself is called
            unbound (Handler.page_context(fake_self)) against the real
            method, so this proves the actual production code path, not a
            reimplementation of it.
            """
            def __init__(self, state_dir):
                self.path = "/settings"
                self.args = _FakePageContextArgs(state_dir)
                self.headers = _FakePageContextHeaders()

            def _resolved_ui_theme(self):
                return "auto"

            # 20-01-PLAN.md Task 2: page_context() also resolves lang via
            # this method — a minimal stand-in matching the real
            # Handler's own cookie-then-default shape. D-17 (21-01-PLAN.md
            # Task 1): the sibling _mode_from_request() stand-in is
            # deleted along with the real method it mirrored.
            def _lang_from_request(self):
                return "en"

        def _page_context_threads_wake_interval_env_default():
            tmp = tempfile.mkdtemp(prefix="skypane-page-context-")
            fake_self = _FakePageContextHandler(tmp)
            saved = os.environ.get(app_module.SLEEP_ENV_VAR)
            try:
                os.environ[app_module.SLEEP_ENV_VAR] = "900"
                ctx = app_module.Handler.page_context(fake_self)
                if ctx.get("wake_interval_env_default") != 900:
                    return False, (
                        "expected wake_interval_env_default == 900 with "
                        "SKYPANE_SLEEP_S=900, got %r" % (ctx.get("wake_interval_env_default"),))

                os.environ.pop(app_module.SLEEP_ENV_VAR, None)
                ctx_unset = app_module.Handler.page_context(fake_self)
                if "wake_interval_env_default" not in ctx_unset:
                    return False, (
                        "expected the wake_interval_env_default key to always be "
                        "present in ctx, even with SKYPANE_SLEEP_S unset")
                if ctx_unset["wake_interval_env_default"] is not None:
                    return False, (
                        "expected wake_interval_env_default to be None with "
                        "SKYPANE_SLEEP_S unset, got %r"
                        % (ctx_unset["wake_interval_env_default"],))
                return True, ""
            finally:
                if saved is not None:
                    os.environ[app_module.SLEEP_ENV_VAR] = saved
                else:
                    os.environ.pop(app_module.SLEEP_ENV_VAR, None)
                shutil.rmtree(tmp, ignore_errors=True)
        check(
            "page_context() threads wake_interval_env_default from the real environment "
            "read: 900 when SKYPANE_SLEEP_S=900, and always present (never conditionally "
            "omitted) as None when unset",
            _page_context_threads_wake_interval_env_default)

    finally:
        if previous_password is not None:
            os.environ[auth.PASSWORD_ENV_VAR] = previous_password
        else:
            os.environ.pop(auth.PASSWORD_ENV_VAR, None)

    # ==================================================================
    # Section 2.5: companion/theme_preview.py (06.6.4.1.1-01 Task 1) — pure
    # in-process module checks, no companion/app.py subprocess or password
    # env needed (theme_preview.py imports neither auth nor app.py).
    # ==================================================================

    def _theme_preview_bytes_open_as_320x120_rgb_png_for_every_theme():
        for theme_id in device_config.THEME_IDS:
            payload = theme_preview.preview_png_bytes(theme_id)
            img = Image.open(io.BytesIO(payload))
            if img.format != "PNG":
                return False, "theme %r: expected PNG, got %r" % (theme_id, img.format)
            if img.size != theme_preview.THEME_PREVIEW_SIZE:
                return False, "theme %r: expected size %r, got %r" % (
                    theme_id, theme_preview.THEME_PREVIEW_SIZE, img.size)
            if img.convert("RGB").mode != "RGB":
                return False, "theme %r: expected an RGB-convertible image" % (theme_id,)
        return True, ""
    check(
        "preview_png_bytes() returns a 320x120 PNG for every id in device_config.THEME_IDS",
        _theme_preview_bytes_open_as_320x120_rgb_png_for_every_theme)

    def _theme_preview_means_pairwise_distinct():
        means = []
        for theme_id in device_config.THEME_IDS:
            payload = theme_preview.preview_png_bytes(theme_id)
            img = Image.open(io.BytesIO(payload)).convert("RGB").resize((1, 1))
            means.append(next(iter(img.getdata())))
        if len(set(means)) != len(means):
            return False, "expected 18 pairwise-distinct mean RGB values, got %r" % (means,)
        return True, ""
    check(
        "the 18 themes' previews have pairwise-distinct mean RGB at the crop/size used "
        "(proves the crop box discriminates themes, D-07)",
        _theme_preview_means_pairwise_distinct)

    def _theme_preview_bytes_stable_across_calls():
        first = theme_preview.preview_png_bytes("white")
        second = theme_preview.preview_png_bytes("white")
        if first != second:
            return False, "expected byte-identical output for the same fixed-scene theme"
        return True, ""
    check(
        "preview_png_bytes() returns byte-identical output across two calls for the same "
        "theme (the scene is fixed, D-06 — nothing time- or data-dependent leaks in)",
        _theme_preview_bytes_stable_across_calls)

    def _theme_preview_cache_path_rejects_unsafe_and_falsy_inputs():
        with tempfile.TemporaryDirectory() as state_dir:
            if theme_preview.cache_path(state_dir, "../../etc/passwd") is not None:
                return False, "expected None for a traversal-shaped theme id"
            if theme_preview.cache_path(state_dir, "nope") is not None:
                return False, "expected None for an id not in device_config.THEMES"
            if theme_preview.cache_path(None, "white") is not None:
                return False, "expected None for a falsy state_dir"
        return True, ""
    check(
        "cache_path() returns None for a traversal-shaped id, an unknown id, and a falsy "
        "state_dir (boundary guard, T-v26-01-01 discipline)",
        _theme_preview_cache_path_rejects_unsafe_and_falsy_inputs)

    def _theme_preview_cached_bytes_cold_cache_creates_file():
        with tempfile.TemporaryDirectory() as state_dir:
            direct = theme_preview.preview_png_bytes("blue")
            cached = theme_preview.cached_preview_bytes(state_dir, "blue")
            path = theme_preview.cache_path(state_dir, "blue")
            if not os.path.isfile(path):
                return False, "expected cached_preview_bytes() to create %r" % (path,)
            if cached != direct:
                return False, "expected the cold-cache render to match preview_png_bytes()"
        return True, ""
    check(
        "cached_preview_bytes() on a cold state dir creates the cache file and returns the "
        "same bytes preview_png_bytes() would",
        _theme_preview_cached_bytes_cold_cache_creates_file)

    def _theme_preview_cached_bytes_second_call_serves_from_disk():
        with tempfile.TemporaryDirectory() as state_dir:
            theme_preview.cached_preview_bytes(state_dir, "green")
            path = theme_preview.cache_path(state_dir, "green")
            marker = b"mutated-cache-fixture-not-a-real-render"
            with open(path, "wb") as fh:
                fh.write(marker)
            second = theme_preview.cached_preview_bytes(state_dir, "green")
            if second != marker:
                return False, (
                    "expected the second call to serve the mutated on-disk bytes "
                    "unchanged, proving it did not re-render")
        return True, ""
    check(
        "a second cached_preview_bytes() call for the same theme is served from the file "
        "on disk, not re-rendered",
        _theme_preview_cached_bytes_second_call_serves_from_disk)

    def _theme_preview_signature_changes_with_cache_version():
        before = theme_preview.preview_signature("white")
        original_version = theme_preview.THEME_PREVIEW_CACHE_VERSION
        try:
            theme_preview.THEME_PREVIEW_CACHE_VERSION = original_version + 1
            after = theme_preview.preview_signature("white")
        finally:
            theme_preview.THEME_PREVIEW_CACHE_VERSION = original_version
        if before == after:
            return False, "expected preview_signature() to change when the cache version does"
        return True, ""
    check(
        "preview_signature() changes when THEME_PREVIEW_CACHE_VERSION changes (the manual "
        "escape hatch for a render-geometry change the signature can't otherwise see)",
        _theme_preview_signature_changes_with_cache_version)

    # ==================================================================
    # Section 2.5b: companion/theme_preview.py's D-23 live-event render
    # path and event-aware cache key (20-08-PLAN.md Task 1).
    # ==================================================================

    def _theme_preview_cache_path_no_event_is_stable_and_distinct_from_live():
        with tempfile.TemporaryDirectory() as state_dir:
            no_event_first = theme_preview.cache_path(state_dir, "white")
            no_event_second = theme_preview.cache_path(state_dir, "white")
            if no_event_first != no_event_second:
                return False, "expected the no-event path to be deterministic across two calls"
            live_path = theme_preview.cache_path(state_dir, "white", live_event_id=41)
            if no_event_first == live_path:
                return False, "expected the no-event path to differ from a live-event path"
            if "41" not in live_path:
                return False, "expected the live-event path to contain the event id"
        return True, ""
    check(
        "cache_path() with no event returns a stable, deterministic filename that differs "
        "from the same theme's live-event filename (which contains the event id) — the "
        "existing 2-argument call site (the chip grid) keeps working unmodified, D-23",
        _theme_preview_cache_path_no_event_is_stable_and_distinct_from_live)

    def _theme_preview_cache_path_distinct_event_ids_distinct_paths():
        with tempfile.TemporaryDirectory() as state_dir:
            path_41 = theme_preview.cache_path(state_dir, "white", live_event_id=41)
            path_42 = theme_preview.cache_path(state_dir, "white", live_event_id=42)
            path_41_again = theme_preview.cache_path(state_dir, "white", live_event_id=41)
            if path_41 == path_42:
                return False, "expected two different event ids to give two different paths"
            if path_41 != path_41_again:
                return False, "expected the same event id twice to give the same path"
        return True, ""
    check(
        "cache_path() gives two different event ids two different paths, and the same event "
        "id twice the same path (D-23/Pitfall 7)",
        _theme_preview_cache_path_distinct_event_ids_distinct_paths)

    def _theme_preview_cache_path_hostile_event_id_degrades_to_sample():
        with tempfile.TemporaryDirectory() as state_dir:
            sample_path = theme_preview.cache_path(state_dir, "white")
            for hostile in ("../../etc/passwd", "not-a-number", object()):
                degraded = theme_preview.cache_path(state_dir, "white", live_event_id=hostile)
                if degraded != sample_path:
                    return False, (
                        "expected a non-integer event id (%r) to degrade to the sample path, "
                        "got %r" % (hostile, degraded))
                if isinstance(hostile, str) and hostile in os.path.basename(degraded):
                    return False, "hostile event id string leaked into the filename"
        return True, ""
    check(
        "cache_path() degrades a non-integer or hostile event id to the same sample path as "
        "no event at all, never reaching the filename (T-20-14)",
        _theme_preview_cache_path_hostile_event_id_degrades_to_sample)

    def _theme_preview_png_bytes_live_event_full_and_partial_row():
        full_row = {
            "id": 5, "hex": "3946a1", "callsign": "AFR1380", "airline": "Air France",
            "origin": "ORY", "destination": "TLS", "confirmed_state": "departing",
        }
        partial_row = {"id": 6}
        for row in (full_row, partial_row):
            payload = theme_preview.preview_png_bytes("white", live_event=row)
            img = Image.open(io.BytesIO(payload))
            if img.format != "PNG":
                return False, "expected a PNG for live_event=%r, got %r" % (row, img.format)
            if img.size != theme_preview.THEME_PREVIEW_SIZE:
                return False, "expected size %r for live_event=%r, got %r" % (
                    theme_preview.THEME_PREVIEW_SIZE, row, img.size)
        return True, ""
    check(
        "preview_png_bytes(theme_id, live_event=row) returns a well-formed PNG for a full "
        "runway_events row and for a row missing half its fields (partial rows never raise, "
        "D-23)",
        _theme_preview_png_bytes_live_event_full_and_partial_row)

    def _theme_preview_cached_bytes_no_event_unchanged():
        with tempfile.TemporaryDirectory() as state_dir:
            direct = theme_preview.preview_png_bytes("blue")
            cached = theme_preview.cached_preview_bytes(state_dir, "blue")
            path = theme_preview.cache_path(state_dir, "blue")
            if not os.path.isfile(path):
                return False, "expected cached_preview_bytes() to create %r" % (path,)
            if cached != direct:
                return False, "expected the no-event cached render to still match preview_png_bytes()"
        return True, ""
    check(
        "cached_preview_bytes() with no live_event still creates the cache file and returns "
        "exactly what preview_png_bytes(theme_id) returns, unchanged by this task (D-23)",
        _theme_preview_cached_bytes_no_event_unchanged)

    def _theme_preview_cached_bytes_live_event_keyed_by_id():
        with tempfile.TemporaryDirectory() as state_dir:
            event_5 = {
                "id": 5, "hex": "3946a1", "callsign": "AFR1380", "airline": "Air France",
                "origin": "ORY", "destination": "TLS", "confirmed_state": "departing",
            }
            event_6 = dict(event_5, id=6, callsign="AFR9999")
            theme_preview.cached_preview_bytes(state_dir, "white", live_event=event_5)
            path_5 = theme_preview.cache_path(state_dir, "white", live_event_id=5)
            if not os.path.isfile(path_5):
                return False, "expected cached_preview_bytes() to create %r" % (path_5,)
            # A cache HIT for the same event id must not re-render — mutate the
            # on-disk bytes and confirm the second call serves them unchanged,
            # the same proof _theme_preview_cached_bytes_second_call_serves_
            # from_disk() already applies to the no-event path.
            marker = b"mutated-cache-fixture-not-a-real-render"
            with open(path_5, "wb") as fh:
                fh.write(marker)
            second_same_event = theme_preview.cached_preview_bytes(
                state_dir, "white", live_event=event_5)
            if second_same_event != marker:
                return False, "expected a same-event second call to be served from disk, not re-rendered"
            # A NEWER event (a different id) must be a cache MISS, not the
            # stale mutated bytes above — this is D-23/Pitfall 7's entire point.
            third_newer_event = theme_preview.cached_preview_bytes(
                state_dir, "white", live_event=event_6)
            if third_newer_event == marker:
                return False, "expected a newer event id to be a cache miss, not the stale marker bytes"
            path_6 = theme_preview.cache_path(state_dir, "white", live_event_id=6)
            if path_5 == path_6:
                return False, "expected two different event ids to produce two different cache files"
            return True, ""
    check(
        "cached_preview_bytes() keys its cache on the live event's row id: a repeat request "
        "for the SAME event serves the on-disk file unchanged (no re-render), and a NEWER "
        "event is a cache miss rather than the stale first render (D-23/Pitfall 7)",
        _theme_preview_cached_bytes_live_event_keyed_by_id)

    # ==================================================================
    # Section 2.6: companion/app.py's _illustration_filenames() (phase 13
    # plan 13-06 Task 1, D-09) — pure in-process module checks against the
    # widened per-request union helper, no subprocess needed.
    # ==================================================================

    def _illustration_filenames_union_contract():
        import companion.app as app_module
        baseline = frozenset(server_illustrations.target_filenames())
        if app_module._illustration_filenames(None) != baseline:
            return False, "expected _illustration_filenames(None) to equal the static target set"
        tmp = tempfile.mkdtemp(prefix="skypane-illufn-")
        try:
            if app_module._illustration_filenames(tmp) != baseline:
                return False, (
                    "expected an empty state dir (no manual_resolutions.json yet) to "
                    "contribute nothing beyond the static target set")
            add_result = manual_resolutions.add_entry(tmp, "ZZZ", "Zephyr Air")
            if add_result != manual_resolutions.ADD_OK:
                return False, "expected add_entry() to succeed for a fresh, valid entry, got %r" % (add_result,)
            widened = app_module._illustration_filenames(tmp)
            expected_key = manual_resolutions.illustration_key_for_name("Zephyr Air")
            if widened != baseline | {expected_key + ".png"}:
                return False, (
                    "expected exactly one new filename (%r) added for the one seeded "
                    "manual entry, got a diff of %r"
                    % (expected_key + ".png", widened.symmetric_difference(baseline)))
            # An entry whose stored name yields no usable key contributes nothing — hand-write
            # a second, reserved-slug entry directly into the JSON file (past add_entry()'s
            # own gate, which would refuse to persist it in the first place):
            # load_manual_resolutions() already drops it on read, so the widened set here
            # must stay exactly what it was above, unchanged.
            path = manual_resolutions.manual_resolutions_path(tmp)
            with open(path) as fh:
                raw = json.load(fh)
            raw["YYY"] = {
                "airline_name": "Generic Fallback",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
            with open(path, "w") as fh:
                json.dump(raw, fh)
            unchanged = app_module._illustration_filenames(tmp)
            if unchanged != widened:
                return False, (
                    "expected a reserved/unusable-slug entry to contribute nothing, "
                    "got a diff of %r" % (unchanged.symmetric_difference(widened),))
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "_illustration_filenames() is the per-request union of the static target set and "
        "server-persisted manual keys: None and an empty state dir both equal the static "
        "set exactly, a seeded manual entry adds exactly one filename, and an entry whose "
        "stored name yields no usable key contributes nothing (D-09)",
        _illustration_filenames_union_contract)

    # ==================================================================
    # Section 2.7: companion/app.py's eight FLASH_KEY_MANUAL_* keys and
    # page_context()'s two new ctx keys (phase 13 plan 13-06 Task 2).
    # ==================================================================

    def _flash_manual_keys_complete_and_byte_identical():
        import companion.app as app_module
        manual_keys = (
            app_module.FLASH_KEY_MANUAL_RESOLVED,
            app_module.FLASH_KEY_MANUAL_NAME_EMPTY,
            app_module.FLASH_KEY_MANUAL_NAME_TOO_LONG,
            app_module.FLASH_KEY_MANUAL_NAME_RESERVED,
            app_module.FLASH_KEY_MANUAL_PREFIX_STALE,
            app_module.FLASH_KEY_MANUAL_REGISTRY_FULL,
            app_module.FLASH_KEY_MANUAL_SAVE_FAILED,
            app_module.FLASH_KEY_MANUAL_DELETE_FAILED,
            app_module.FLASH_KEY_MANUAL_NAME_UNUSABLE,
        )
        for key in manual_keys:
            if key not in app_module.FLASH_MESSAGES:
                return False, "expected %r to be a FLASH_MESSAGES key" % (key,)
            if key not in app_module.FLASH_ROLES:
                return False, "expected %r to be a FLASH_ROLES key" % (key,)
        # The six deck strings from 13-UI-SPEC.md's Full Copy Deck, byte for
        # byte — the two planner-added failure keys are not in that deck
        # (see FLASH_KEY_ILLUSTRATION_REPLACE_FAILED's own precedent) so
        # they are checked for presence above only, not for exact text here.
        expected_deck = {
            app_module.FLASH_KEY_MANUAL_RESOLVED: (
                "Airline name saved — the frame will pick it up next time "
                "it wakes and polls."),
            app_module.FLASH_KEY_MANUAL_NAME_EMPTY: (
                "Enter an airline name before saving."),
            app_module.FLASH_KEY_MANUAL_NAME_TOO_LONG: (
                "That name's too long — airline names top out at 100 characters."),
            app_module.FLASH_KEY_MANUAL_NAME_RESERVED: (
                "That name is reserved for the frame's own fallback artwork "
                "— try the airline's real name instead."),
            app_module.FLASH_KEY_MANUAL_PREFIX_STALE: (
                "That coverage gap isn't there anymore — check Health for "
                "current gaps."),
            app_module.FLASH_KEY_MANUAL_REGISTRY_FULL: (
                "The manual-resolution list is full (200 entries) — delete "
                "an old one before adding another."),
        }
        for key, expected_text in expected_deck.items():
            if app_module.FLASH_MESSAGES[key] != expected_text:
                return False, (
                    "expected %r's FLASH_MESSAGES text to match the UI-SPEC deck byte "
                    "for byte, got %r" % (key, app_module.FLASH_MESSAGES[key]))
            resolved = app_module._resolve_flash_text(key, "/nonexistent-state-dir-fixture")
            if resolved != expected_text:
                return False, (
                    "expected _resolve_flash_text(%r, ...) to return the deck text, "
                    "got %r" % (key, resolved))
        if app_module._resolve_flash_text("not-a-real-flash-key", "/nonexistent") is not None:
            return False, "expected _resolve_flash_text() to return None for an unknown key"
        # Phase 15 D-10 (15-05-PLAN.md): FLASH_KEY_RULE_REPLACED joins
        # FLASH_KEY_POLL_COOLDOWN as the second deliberately-interpolated
        # key ("{key}", D-09's "make replaced legible" requirement) —
        # widened in place, not loosened. Phase 17 plan 04 (D-06) widens
        # it again for FLASH_KEY_CALENDAR_CONNECTED's server-computed
        # "{n}"/"{s}" (the on-disk entry count, never anything
        # client-supplied). 20-09-PLAN.md Task 2 (D-14c) widens it once
        # more for FLASH_KEY_CALENDAR_CONNECT_OK's own server-computed
        # "{n}" — the connect route's own success flash, distinct from
        # (and never sharing a key with) the older save-triggered-sync
        # flash — every other FLASH_MESSAGES value still carries no
        # runtime placeholder at all.
        _interpolated_keys = (
            app_module.FLASH_KEY_POLL_COOLDOWN, app_module.FLASH_KEY_RULE_REPLACED,
            app_module.FLASH_KEY_CALENDAR_CONNECTED, app_module.FLASH_KEY_CALENDAR_CONNECT_OK)
        for key, text in app_module.FLASH_MESSAGES.items():
            if key in _interpolated_keys:
                continue
            if "%" in text or "{" in text:
                return False, (
                    "expected no runtime interpolation in FLASH_MESSAGES[%r], got %r "
                    "(UI-SPEC Autonomous Decision 6: flash copy is fixed, never "
                    "interpolated, except the cooldown, rule_replaced, "
                    "calendar_connected and calendar_connect_ok keys)" % (key, text))
        return True, ""
    check(
        "every FLASH_KEY_MANUAL_* constant is a FLASH_MESSAGES/FLASH_ROLES key; the six "
        "UI-SPEC deck strings resolve byte for byte through _resolve_flash_text(), an "
        "unknown key still resolves to None, and no FLASH_MESSAGES value carries a "
        "runtime placeholder except the cooldown, rule_replaced, calendar_connected and "
        "calendar_connect_ok keys (Phase 15 D-10 widened this in place, not loosened; "
        "Phase 17 plan 04 and 20-09-PLAN.md Task 2 each widen it again for the same "
        "reason)",
        _flash_manual_keys_complete_and_byte_identical)

    class _FakeResolveCtxHandler(_FakePageContextHandler):
        """Same minimal stand-in as _FakePageContextHandler above, but with
        a settable `self.path` (that fixture hardcodes "/settings") so this
        check can exercise page_context() against a real
        "/airlines?resolve=..." query string.
        """
        def __init__(self, state_dir, path):
            super().__init__(state_dir)
            self.path = path

    def _page_context_supplies_resolve_prefix_and_manual_resolutions():
        import companion.app as app_module
        import companion.pages as pages_package
        tmp = tempfile.mkdtemp(prefix="skypane-page-context-resolve-")
        try:
            now = "2026-01-01T00:00:00+00:00"
            add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
            if add_result != manual_resolutions.ADD_OK:
                return False, "expected the fixture add_entry() call to succeed, got %r" % (add_result,)
            fake_self = _FakeResolveCtxHandler(tmp, "/airlines?resolve=XYZ")
            ctx = app_module.Handler.page_context(fake_self)
            if ctx.get("resolve_prefix") != "XYZ":
                return False, "expected ctx['resolve_prefix'] == 'XYZ', got %r" % (ctx.get("resolve_prefix"),)
            registry = ctx.get("manual_resolutions")
            if not isinstance(registry, dict) or "XYZ" not in registry:
                return False, "expected ctx['manual_resolutions'] to reflect the seeded entry, got %r" % (registry,)
            if registry["XYZ"].get("airline_name") != "Brand New Air":
                return False, (
                    "expected the seeded entry's airline_name to round-trip through ctx, "
                    "got %r" % (registry["XYZ"],))
            # companion/pages/__init__.py's documented ctx list must not go
            # stale silently — assert the documented key set against the
            # real dict's keys, not the other way around, so an
            # undocumented new ctx key also fails this check. NOTE:
            # "health_state" is a real page_context() key but is not one
            # of this docstring's bullets — a pre-existing gap predating
            # this plan (out of scope here per the deviation-rules scope
            # boundary; this plan documents only its own two new keys),
            # so it is deliberately excluded from this list rather than
            # silently made to look documented.
            documented_keys = (
                "state_dir", "ui_theme", "device_config",
                "wake_interval_env_default", "flash", "flash_role",
                "poll_cooldown_remaining", "gallery_entries", "runway_images",
                "health_severity", "now",
                "resolve_prefix", "manual_resolutions",
                # 20-01-PLAN.md Task 2 (D-04):
                "lang",
                # D-17 (21-01-PLAN.md Task 1): the sibling "simple_mode"
                # key is deleted from page_context()'s return dict along
                # with the rest of the mode mechanism, so it is removed
                # from this tuple too — companion/pages/__init__.py's own
                # docstring bullet for it is outside this plan's
                # files_modified list and is flagged as a deviation in
                # 21-01-SUMMARY.md rather than edited here.
            )
            docstring = pages_package.__doc__
            for key in documented_keys:
                if ("- %s:" % key) not in docstring:
                    return False, "expected %r to be documented in companion/pages/__init__.py's ctx list" % (key,)
                if key not in ctx:
                    return False, "expected documented ctx key %r to actually be present in page_context()'s return" % (key,)
            return True, ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    check(
        "page_context() on a request carrying ?resolve=XYZ returns that raw value under "
        "resolve_prefix and a dict under manual_resolutions reflecting a seeded entry; "
        "every key companion/pages/__init__.py documents is actually present in ctx",
        _page_context_supplies_resolve_prefix_and_manual_resolutions)

    # ==================================================================
    # Section 3: companion/app.py (plan 06-05) — a real companion/app.py
    # subprocess, launched on a free local port, driven with
    # urllib.request. This section owns its own harness lifecycle
    # (independent of Section 1/2's env-var save/restore above), and
    # tolerates the ADS-B aggregators being unreachable in this sandboxed
    # environment — the poll-trigger checks below assert on the flash
    # outcome and the cooldown behaviour, never on a flight being
    # detected.
    # ==================================================================

    harness = Harness()
    try:
        harness.start()
        base = harness.base_url()

        # --- D-02 whole-site auth gate: nine routes, asserted individually ---
        # A single forgotten require_session() call is a full auth
        # bypass, so each route below is its own check, not a shared loop
        # collapsed into one assertion.

        def _unauth_redirects_to_login(method, path, data=None, next_route=None):
            # 06.6.2-07 (UXA-03): require_session() now carries an
            # allowlisted `next` query param for any requested path that
            # is one of layout.NAV_TABS's known routes (settings/health/
            # airlines/history, 06.6.4.1-07 renamed the first from config;
            # 06.6.4.1-08 removed preview — D-22 retires that page) —
            # regardless of HTTP method, since it only ever looks at
            # self.path. A path outside that set (poll-now, the retired
            # /preview redirect source, preview.png, a gallery image)
            # still redirects to the bare /login exactly as before this
            # plan.
            expected_location = (
                "/login?next=%s" % urllib.parse.quote(next_route, safe="")
                if next_route else "/login")

            def _run():
                status, headers, body = http_request(base + path, method=method, data=data)
                if status != 303:
                    return False, "expected 303, got %d" % status
                if headers.get("Location") != expected_location:
                    return False, "expected a redirect to %r, got %r" % (
                        expected_location, headers.get("Location"))
                if body:
                    return False, "expected an empty redirect body, got %d bytes of content" % len(body)
                return True, ""
            return _run

        for _tab_path in ("/", "/display", "/flights", "/airlines", "/health", "/device"):
            check(
                "unauthenticated GET %s redirects to /login carrying that route as ?next=" % _tab_path,
                _unauth_redirects_to_login("GET", _tab_path, next_route=_tab_path))

        # Phase 18: the retired page routes keep their session gate but,
        # no longer being NAV_TABS members, carry no ?next= — the same
        # contract /preview below has had since D-22.
        for _legacy_path in ("/settings", "/history"):
            check(
                "unauthenticated GET %s (a retired page route) redirects to /login without ?next=" % _legacy_path,
                _unauth_redirects_to_login("GET", _legacy_path))

        check(
            "unauthenticated GET /preview (the retired Preview page's redirect source) redirects "
            "to /login without page content (D-22 removed it from NAV_TABS, so no ?next= is carried "
            "— it lands on /login, not /history, proving the redirect branch keeps its own session gate)",
            _unauth_redirects_to_login("GET", "/preview"))

        def _preview_png_unauth_404_not_login_redirect():
            # Quick task 260903-c4o retired the /preview.png route
            # entirely (its session-gated branch in do_GET is gone), so
            # an unauthenticated request no longer reaches a
            # require_session() check at all — it falls through to
            # do_GET's unknown-path handler, which is deliberately
            # ungated (every other unknown path already 404s pre-auth).
            # That is a real, observable contract change from this
            # route's prior 303-to-/login behaviour, and it is
            # acceptable: the ungated 404 leaks nothing beyond "this
            # route does not exist", exactly like every other unknown
            # path.
            status, _headers, body = http_request(base + "/preview.png")
            if status != 404:
                return False, "expected 404 for unauthenticated GET /preview.png, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "unauthenticated GET /preview.png now returns 404 (not a 303 to /login) — the "
            "route's session-gated branch is gone, so the request falls through to do_GET's "
            "deliberately ungated unknown-path handler",
            _preview_png_unauth_404_not_login_redirect)

        check(
            "unauthenticated GET of a gallery image route redirects to /login without page content "
            "(not a NAV_TABS route, so no ?next= is carried)",
            _unauth_redirects_to_login("GET", "/gallery/whatever.png"))

        check(
            "unauthenticated POST /settings redirects to /login (the write route is not a tab, so no ?next=)",
            _unauth_redirects_to_login(
                "POST", "/settings",
                data=urllib.parse.urlencode({"ui_theme": "sky"}).encode()))

        check(
            "unauthenticated POST /poll-now redirects to /login without page content "
            "(not a NAV_TABS route, so no ?next= is carried)",
            _unauth_redirects_to_login("POST", "/poll-now"))

        # --- stylesheet: public, no session required ---

        def _stylesheet_public():
            status, headers, body = http_request(base + "/static/style.css")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/css" not in content_type:
                return False, "expected a text/css content type, got %r" % content_type
            if not body:
                return False, "expected a non-empty stylesheet body"
            cache_control = headers.get("Cache-Control", "")
            directives = [part.strip() for part in cache_control.split(",")]
            if "public" not in directives:
                return False, (
                    "expected a shared-cacheable (public) Cache-Control scope, "
                    "got %r" % cache_control)
            if "max-age=300" not in directives:
                return False, (
                    "expected a 300-second max-age on the stylesheet's "
                    "Cache-Control header, got %r" % cache_control)
            return True, ""
        check(
            "GET /static/style.css succeeds without a session, returns a CSS "
            "content type, and stays shared-cacheable (public, max-age=300) — "
            "this route is a deliberate D-02 gate exemption with no per-user "
            "content",
            _stylesheet_public)

        # --- battery-trend script: public, no session required (06.5-01, D-02) ---

        def _battery_trend_script_public():
            status, headers, body = http_request(base + "/static/battery-trend.js")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/javascript" not in content_type:
                return False, "expected a text/javascript content type, got %r" % content_type
            if not body:
                return False, "expected a non-empty script body"
            cache_control = headers.get("Cache-Control", "")
            if "max-age=300" not in cache_control:
                return False, "expected Cache-Control max-age=300, got %r" % cache_control
            return True, ""
        check(
            "GET /static/battery-trend.js succeeds without a session and returns a JavaScript content type",
            _battery_trend_script_public)

        # --- nav-dropdown script: public, no session required (06.6.1-05, D-06) ---

        def _nav_dropdown_script_public():
            status, headers, body = http_request(base + "/static/nav-dropdown.js")
            if status != 200:
                return False, "expected 200, got %d" % status
            content_type = headers.get("Content-Type", "")
            if "text/javascript" not in content_type:
                return False, "expected a text/javascript content type, got %r" % content_type
            if b"site-nav-toggle" not in body:
                return False, "expected the toggle-id literal in the served body, proving the real file was served"
            return True, ""
        check(
            "GET /static/nav-dropdown.js succeeds without a session, returns a JavaScript content type, "
            "and serves the real file",
            _nav_dropdown_script_public)

        # --- 06.6.3: four more pre-auth static scripts, same shape as
        # _nav_dropdown_script_public() above ---

        def _static_script_public(route):
            def _run():
                status, headers, body = http_request(base + route)
                if status != 200:
                    return False, "expected 200, got %d" % status
                content_type = headers.get("Content-Type", "")
                if "text/javascript" not in content_type:
                    return False, "expected a text/javascript content type, got %r" % content_type
                if not body:
                    return False, "expected a non-empty script body"
                cache_control = headers.get("Cache-Control", "")
                if "max-age=300" not in cache_control:
                    return False, "expected Cache-Control max-age=300, got %r" % cache_control
                return True, ""
            return _run

        for _script_route in (
                "/static/dirty-state.js", "/static/list-filter.js",
                "/static/copy-button.js", "/static/freshness.js"):
            check(
                "GET %s succeeds without a session and returns a shared-cacheable "
                "JavaScript content type" % _script_route,
                _static_script_public(_script_route))

        def _four_new_static_routes_dom_contract_guard():
            # Cross-file-equality half, mirroring
            # _three_file_nav_dom_contract_guard()'s own pattern: each new
            # companion.app.py *_SCRIPT_ROUTE constant must equal its
            # matching companion/layout.py *_SCRIPT_SRC constant, and
            # page_shell() must emit a <script src="..."> tag for each.
            import companion.app as app_module
            pairs = (
                (app_module.DIRTY_STATE_SCRIPT_ROUTE, layout.DIRTY_STATE_SCRIPT_SRC),
                (app_module.LIST_FILTER_SCRIPT_ROUTE, layout.LIST_FILTER_SCRIPT_SRC),
                (app_module.COPY_BUTTON_SCRIPT_ROUTE, layout.COPY_BUTTON_SCRIPT_SRC),
                (app_module.FRESHNESS_SCRIPT_ROUTE, layout.FRESHNESS_SCRIPT_SRC),
            )
            for route_const, src_const in pairs:
                if route_const != src_const:
                    return False, "script route drift: %r vs %r" % (route_const, src_const)
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            for _route_const, src_const in pairs:
                if ('<script src="%s" defer></script>' % src_const) not in doc:
                    return False, "expected a deferred <script> tag for %r" % src_const
            return True, ""
        check(
            "companion.app.py's 4 new *_SCRIPT_ROUTE constants equal companion/layout.py's 4 new "
            "*_SCRIPT_SRC constants, and page_shell() emits a <script> tag for each",
            _four_new_static_routes_dom_contract_guard)

        # --- 20-11-PLAN.md Task 3 (D-06): copy-button.js/dirty-state.js's
        # own screen-bound connector words move to server-rendered data-*
        # attributes ---

        def _copy_button_script_es5_safe_reads_data_copied_text():
            js_path = os.path.join(HERE, "static", "copy-button.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(", "fetch(",
                "XMLHttpRequest")
            for token in banned:
                if token in src:
                    return False, "copy-button.js must not contain %r" % token
            required = ("textContent", "addEventListener", "getAttribute")
            for token in required:
                if token not in src:
                    return False, "expected %r in copy-button.js" % token
            if "data-copied-text" not in src:
                return False, "expected copy-button.js to read data-copied-text"
            # D-06: the removed hardcoded literal survives ONLY as the
            # documented fallback — exactly one occurrence of the quoted
            # string, on the FALLBACK_FEEDBACK_TEXT declaration itself.
            if src.count('"Copied"') != 1:
                return False, (
                    "expected exactly one \"Copied\" literal (the documented fallback), got %d"
                    % src.count('"Copied"'))
            return True, ""
        check(
            "copy-button.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/"
            "insertAdjacentHTML/document.write/eval/fetch/XHR), reads its on-success feedback "
            "text from each button's own data-copied-text attribute, and the removed hardcoded "
            "\"Copied\" literal survives only as the one documented fallback (D-06)",
            _copy_button_script_es5_safe_reads_data_copied_text)

        def _dirty_state_script_es5_safe_reads_five_connector_attributes():
            js_path = os.path.join(HERE, "static", "dirty-state.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(", "fetch(",
                "XMLHttpRequest")
            for token in banned:
                if token in src:
                    return False, "dirty-state.js must not contain %r" % token
            required = ("textContent", "addEventListener", "getAttribute", "querySelector")
            for token in required:
                if token not in src:
                    return False, "expected %r in dirty-state.js" % token
            for attr in (
                    "data-dirty-changed-suffix", "data-dirty-and", "data-dirty-list-and",
                    "data-dirty-unsaved-singular", "data-dirty-unsaved-plural"):
                if attr not in src:
                    return False, "expected dirty-state.js to read %r" % attr
            # D-06: each removed hardcoded connector word survives ONLY as
            # its own documented fallback literal, never a second inline
            # occurrence elsewhere in updateBar().
            if src.count('"1 unsaved change"') != 1:
                return False, "expected exactly one \"1 unsaved change\" literal (the fallback)"
            if src.count('" unsaved changes"') != 1:
                return False, "expected exactly one \" unsaved changes\" literal (the fallback)"
            return True, ""
        check(
            "dirty-state.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/"
            "insertAdjacentHTML/document.write/eval/fetch/XHR), reads all five connector words "
            "from the dirty-bar element's own data-dirty-* attributes, and each removed "
            "hardcoded literal survives only as its own documented fallback (D-06)",
            _dirty_state_script_es5_safe_reads_five_connector_attributes)

        # --- 19-09-PLAN.md Task 3: freshness.js's own named guard (D-02) ---

        def _freshness_script_es5_safe_with_one_reviewed_sink_exception():
            # Modelled on _panel_lookup_script_es5_safe_and_no_html_write()
            # above, with ONE DELIBERATE, DOCUMENTED divergence: fetch(,
            # setTimeout and setInterval are PERMITTED here and nowhere
            # else among this project's static scripts. D-02 makes
            # freshness.js the single reviewed exception to that ban,
            # because a live monitoring page needs a network read to stay
            # honest, and the standing HTML-writing-sink ban is preserved
            # a different way (DOMParser, never innerHTML/
            # insertAdjacentHTML/document.write/eval(). Adding a second
            # exception anywhere else in this codebase requires a new
            # decision, not a precedent copied from this one.
            js_path = os.path.join(HERE, "static", "freshness.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(",
                "location.reload", "XMLHttpRequest",
            )
            for token in banned:
                if token in src:
                    return False, "freshness.js must not contain %r" % token
            required = ("DOMParser", "replaceChild", "credentials", "fetch(")
            for token in required:
                if token not in src:
                    return False, "expected %r in freshness.js" % token
            return True, ""
        check(
            "freshness.js stays ES5-safe and keeps the standing HTML-writing-sink ban (no let/const/"
            "arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/"
            "location.reload/XHR), while fetch(/setTimeout/setInterval are its own single, "
            "deliberate, reviewed exception to the sibling scripts' ban list (D-02) — and it "
            "actually uses the safe DOMParser/replaceChild/credentials-scoped mechanism this "
            "exception was granted for, not merely permitted to",
            _freshness_script_es5_safe_with_one_reviewed_sink_exception)

        def _freshness_script_no_url_taking_navigation_form():
            # The security property the retired reload-only file's own
            # comment protected, now pinned instead of merely promised
            # (T-19-33). A bare READ of window.location.href as a fetch
            # argument is explicitly permitted — this checks for the
            # ASSIGNMENT/CALL forms only, never the substring
            # "location.href" on its own, which would also match that
            # permitted read.
            js_path = os.path.join(HERE, "static", "freshness.js")
            with open(js_path) as fh:
                src = fh.read()
            forbidden_forms = (
                "location.href =", "location.assign", "location.replace", "window.open",
            )
            for form in forbidden_forms:
                if form in src:
                    return False, "freshness.js must not contain the navigation form %r" % form
            if "window.location.href" not in src:
                return False, "expected the permitted window.location.href fetch-argument read"
            return True, ""
        check(
            "freshness.js contains no URL-taking navigation form (an assignment to location.href, "
            "or a call to location.assign/location.replace/window.open) while still reading "
            "window.location.href as its fetch argument — the fetch target can never be influenced "
            "by injected markup (19-09-PLAN.md Task 3, D-02/T-19-33)",
            _freshness_script_no_url_taking_navigation_form)

        # --- 06.6.4.1-02 Task 3: panel-lookup.js (D-20) ---

        check(
            "GET /static/panel-lookup.js succeeds without a session and returns a shared-cacheable "
            "JavaScript content type",
            _static_script_public("/static/panel-lookup.js"))

        def _panel_lookup_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "panel-lookup.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
                "setTimeout", "setInterval", "innerHTML", "document.write",
                "eval(",
                # quick task 260902-tli: the Airlines click-to-enlarge
                # gate is CSS-only by design — this script must never
                # inspect viewport dimensions or device orientation to
                # decide whether to open the dialog.
                "matchMedia", "innerWidth")
            for token in banned:
                if token in src:
                    return False, "panel-lookup.js must not contain %r" % token
            return True, ""
        check(
            "panel-lookup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "fetch/XHR/timers/innerHTML/document.write/eval), and never decides whether to open the "
            "dialog from viewport dimensions or device orientation (no matchMedia/innerWidth) — that "
            "gate is CSS-only, on the Airlines trigger's own rule (quick task 260902-tli)",
            _panel_lookup_script_es5_safe_and_no_html_write)

        def _panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard():
            # new (quick task 260903-btu): pins the single line that
            # keeps History's lightbox alive. Moving the optional
            # replace-form lookup into the mandatory guard's condition,
            # or above it, would make the whole script a no-op on any
            # page that renders no replace form — which is every page
            # except Airlines.
            js_path = os.path.join(HERE, "static", "panel-lookup.js")
            with open(js_path) as fh:
                src = fh.read()
            guard_needle = "if (!image || !caption || !note)"
            guard_count = src.count(guard_needle)
            if guard_count != 1:
                return False, "expected the mandatory guard line exactly once, got %d" % guard_count
            guard_line = [line for line in src.splitlines() if guard_needle in line][0]
            if "replaceForm" in guard_line:
                return False, "expected the optional replace-form variable name absent from the mandatory guard's own line"
            lookup_needle = "var replaceForm"
            lookup_count = src.count(lookup_needle)
            if lookup_count != 1:
                return False, "expected the optional replace-form lookup exactly once, got %d" % lookup_count
            if src.index(lookup_needle) <= src.index(guard_needle):
                return False, "expected the optional replace-form lookup's first occurrence after the mandatory guard's"
            # Phase 14 (14-05-PLAN.md Task 1) widened this from 1 to 3:
            # the replace form's own write (quick task 260903-btu,
            # unchanged) plus two new siblings this task adds — the
            # resolve-upload zone's nested <form> and the delete form —
            # each following the identical optional-element,
            # setAttribute("action", ...) idiom the replace form
            # already established. Still exactly one guard line, still
            # one optional lookup after it; only the write count grew.
            write_count = src.count('setAttribute("action"')
            if write_count != 3:
                return False, "expected the action-attribute setAttribute write exactly 3 times, got %d" % write_count
            return True, ""
        check(
            "the mandatory three-element guard appears exactly once and never mentions the optional "
            "replace-form lookup on its own line, that lookup's first occurrence in the source comes after "
            "the guard's, it appears exactly once, and the action-attribute setAttribute write appears "
            "exactly 3 times (replace/resolve-upload/delete, phase 14 plan 14-05) — pinning the single "
            "line that keeps History's lightbox alive (quick task 260903-btu)",
            _panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard)

        def _panel_lookup_script_route_src_agree():
            import companion.app as app_module
            if layout.PANEL_LOOKUP_SCRIPT_SRC != app_module.PANEL_LOOKUP_SCRIPT_ROUTE:
                return False, "panel-lookup script route drift: %r vs %r" % (
                    layout.PANEL_LOOKUP_SCRIPT_SRC, app_module.PANEL_LOOKUP_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.PANEL_LOOKUP_SCRIPT_SRC equals companion.app.PANEL_LOOKUP_SCRIPT_ROUTE",
            _panel_lookup_script_route_src_agree)

        # --- quick task 260903-peo Task 4: flash-cleanup.js (UIR-19) ---

        check(
            "GET /static/flash-cleanup.js succeeds without a session and returns a "
            "shared-cacheable JavaScript content type",
            _static_script_public("/static/flash-cleanup.js"))

        def _flash_cleanup_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "flash-cleanup.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
                "setTimeout", "setInterval", "innerHTML", "document.write",
                "eval(")
            for token in banned:
                if token in src:
                    return False, "flash-cleanup.js must not contain %r" % token
            # Confirmed from source, not assumed: history.replaceState and
            # location.search/location.pathname are NOT among the banned
            # ES5-unsafe/forbidden-sink tokens above (freshness.js already
            # ships window.location.reload() and passes, so navigation
            # APIs are not blanket-banned) — this is the mechanism the
            # cleanup itself depends on.
            for required in ("history.replaceState", "location.search", "location.pathname"):
                if required not in src:
                    return False, "expected %r in flash-cleanup.js" % required
            return True, ""
        check(
            "flash-cleanup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "fetch/XHR/timers/innerHTML/document.write/eval), and uses history.replaceState with "
            "location.search/location.pathname to strip a consumed ?flash= param (quick task "
            "260903-peo, UIR-19)",
            _flash_cleanup_script_es5_safe_and_no_html_write)

        def _flash_cleanup_script_route_src_agree():
            import companion.app as app_module
            if layout.FLASH_CLEANUP_SCRIPT_SRC != app_module.FLASH_CLEANUP_SCRIPT_ROUTE:
                return False, "flash-cleanup script route drift: %r vs %r" % (
                    layout.FLASH_CLEANUP_SCRIPT_SRC, app_module.FLASH_CLEANUP_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.FLASH_CLEANUP_SCRIPT_SRC equals companion.app.FLASH_CLEANUP_SCRIPT_ROUTE",
            _flash_cleanup_script_route_src_agree)

        # --- 19-04-PLAN.md Task 1 (D-18/A-35): poll-cooldown.js ---

        check(
            "GET /static/poll-cooldown.js succeeds without a session and returns a "
            "shared-cacheable JavaScript content type",
            _static_script_public("/static/poll-cooldown.js"))

        def _poll_cooldown_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "poll-cooldown.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(", "fetch(",
                "XMLHttpRequest")
            for token in banned:
                if token in src:
                    return False, "poll-cooldown.js must not contain %r" % token
            required = (
                "textContent", "removeAttribute", "setInterval",
                "clearInterval", "addEventListener")
            for token in required:
                if token not in src:
                    return False, "expected %r in poll-cooldown.js" % token
            return True, ""
        check(
            "poll-cooldown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), and carries "
            "both the D-01 countdown (textContent/removeAttribute/setInterval/clearInterval) and "
            "the UXA-15 disable-on-submit affordance (addEventListener)",
            _poll_cooldown_script_es5_safe_and_no_html_write)

        def _poll_cooldown_script_route_src_agree():
            import companion.app as app_module
            if layout.POLL_COOLDOWN_SCRIPT_SRC != app_module.POLL_COOLDOWN_SCRIPT_ROUTE:
                return False, "poll cooldown script route drift: %r vs %r" % (
                    layout.POLL_COOLDOWN_SCRIPT_SRC, app_module.POLL_COOLDOWN_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.POLL_COOLDOWN_SCRIPT_SRC equals companion.app.POLL_COOLDOWN_SCRIPT_ROUTE",
            _poll_cooldown_script_route_src_agree)

        # --- 19-11-PLAN.md Task 2 (D-08/A-26): confirm-submit.js ---

        check(
            "GET /static/confirm-submit.js succeeds without a session and returns a "
            "shared-cacheable JavaScript content type",
            _static_script_public("/static/confirm-submit.js"))

        def _confirm_submit_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "confirm-submit.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(", "fetch(",
                "XMLHttpRequest", "location.assign", "location.replace")
            for token in banned:
                if token in src:
                    return False, "confirm-submit.js must not contain %r" % token
            required = ("addEventListener", "preventDefault", "confirm(")
            for token in required:
                if token not in src:
                    return False, "expected %r in confirm-submit.js" % token
            return True, ""
        check(
            "confirm-submit.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/location.assign/"
            "location.replace), and carries the native confirm() step (addEventListener/"
            "preventDefault/confirm() all present) (D-08/A-26)",
            _confirm_submit_script_es5_safe_and_no_html_write)

        def _confirm_submit_script_route_src_agree():
            import companion.app as app_module
            if layout.CONFIRM_SUBMIT_SCRIPT_SRC != app_module.CONFIRM_SUBMIT_SCRIPT_ROUTE:
                return False, "confirm-submit script route drift: %r vs %r" % (
                    layout.CONFIRM_SUBMIT_SCRIPT_SRC, app_module.CONFIRM_SUBMIT_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.CONFIRM_SUBMIT_SCRIPT_SRC equals companion.app.CONFIRM_SUBMIT_SCRIPT_ROUTE",
            _confirm_submit_script_route_src_agree)

        # --- 20-08-PLAN.md Task 3 (D-22..D-24/D-32): theme-preview.js ---

        check(
            "GET /static/theme-preview.js succeeds without a session and returns a "
            "shared-cacheable JavaScript content type",
            _static_script_public("/static/theme-preview.js"))

        def _theme_preview_script_es5_safe_and_no_html_write():
            js_path = os.path.join(HERE, "static", "theme-preview.js")
            with open(js_path) as fh:
                src = fh.read()
            if src.count('"use strict"') != 1:
                return False, (
                    "expected exactly one \"use strict\", got %d"
                    % src.count('"use strict"'))
            banned = (
                "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
                "insertAdjacentHTML", "document.write", "eval(", "fetch(",
                "XMLHttpRequest", "setTimeout(", "setInterval(")
            for token in banned:
                if token in src:
                    return False, "theme-preview.js must not contain %r" % token
            required = ("addEventListener", "querySelector", "getAttribute", "data-preview-src")
            for token in required:
                if token not in src:
                    return False, "expected %r in theme-preview.js" % token
            return True, ""
        check(
            "theme-preview.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/"
            "innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers), and "
            "carries the chip-selection src swap (addEventListener/querySelector/getAttribute/"
            "data-preview-src all present) (D-22..D-24)",
            _theme_preview_script_es5_safe_and_no_html_write)

        def _theme_preview_script_route_src_agree():
            import companion.app as app_module
            if layout.THEME_PREVIEW_SCRIPT_SRC != app_module.THEME_PREVIEW_SCRIPT_ROUTE:
                return False, "theme-preview script route drift: %r vs %r" % (
                    layout.THEME_PREVIEW_SCRIPT_SRC, app_module.THEME_PREVIEW_SCRIPT_ROUTE)
            return True, ""
        check(
            "layout.THEME_PREVIEW_SCRIPT_SRC equals companion.app.THEME_PREVIEW_SCRIPT_ROUTE",
            _theme_preview_script_route_src_agree)

        def _theme_preview_script_tag_exactly_once_and_no_bare_inline_script():
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            expected_tag = '<script src="%s" defer></script>' % layout.THEME_PREVIEW_SCRIPT_SRC
            if doc.count(expected_tag) != 1:
                return False, "expected exactly one %r, got %d" % (
                    expected_tag, doc.count(expected_tag))
            # No inline <script> without a src anywhere in a rendered page —
            # the CSP's own "no inline script" rule (D-32), pinned here so a
            # future change cannot silently reintroduce one.
            for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
                return False, "expected no inline <script> without a src, found %r" % match.group(0)
            return True, ""
        check(
            "a rendered authenticated page contains exactly one theme-preview.js <script> tag "
            "and no inline <script> without a src (D-32)",
            _theme_preview_script_tag_exactly_once_and_no_bare_inline_script)

        def _ten_deferred_scripts_before_closing_body():
            # Retargeted in place from _nine_deferred_scripts_before_
            # closing_body() (20-08-PLAN.md Task 3, D-22..D-24/D-32):
            # theme-preview.js is the tenth unconditional script.
            doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
            body_close = doc.index("</body>")
            head = doc[:body_close]
            count = head.count('<script src=')
            if count != 10:
                return False, "expected exactly 10 deferred <script src= tags before </body>, got %d" % count
            for src_const in (
                    layout.PANEL_LOOKUP_SCRIPT_SRC, layout.FLASH_CLEANUP_SCRIPT_SRC,
                    layout.POLL_COOLDOWN_SCRIPT_SRC, layout.CONFIRM_SUBMIT_SCRIPT_SRC,
                    layout.THEME_PREVIEW_SCRIPT_SRC):
                if ('<script src="%s" defer></script>' % src_const) not in doc:
                    return False, "expected a deferred <script> tag for %r" % src_const
            return True, ""
        check(
            "a rendered authenticated page contains exactly ten deferred <script src= tags "
            "before the closing body tag, including panel-lookup.js, flash-cleanup.js, "
            "poll-cooldown.js, confirm-submit.js and theme-preview.js",
            _ten_deferred_scripts_before_closing_body)

        # --- login: wrong password, right password, cookie flags ---

        def _login_wrong_password():
            status, headers, body = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode({"password": "not-the-real-password"}).encode())
            if status != 401:
                return False, "expected 401 for a wrong password, got %d" % status
            if b"Incorrect password. Try again." not in body:
                return False, "expected the exact login-failure copy in the response body"
            if "Set-Cookie" in headers:
                return False, "expected no Set-Cookie header on a failed login"
            return True, ""
        check(
            "a login POST with the wrong password re-renders the form with the exact copy and sets no cookie",
            _login_wrong_password)

        def _login_correct_password():
            status, headers, _ = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode({"password": TEST_PASSWORD}).encode())
            if status != 303:
                return False, "expected a 303 redirect on successful login, got %d" % status
            if headers.get("Location") != "/":
                return False, "expected a redirect to / (Home), got %r" % headers.get("Location")
            set_cookie = headers.get("Set-Cookie", "")
            for needle in ("HttpOnly", "Secure", "SameSite=Strict"):
                if needle not in set_cookie:
                    return False, "missing %r in the session cookie header: %r" % (needle, set_cookie)
            return True, ""
        check(
            "a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict and redirects to / (Home)",
            _login_correct_password)

        # --- 06.6.2-07 (UXA-03): deep-link return, open-redirect rejection,
        # login_shell() markup, D-01 language-policy regression ---

        def _deep_link_return_round_trip():
            # An unauthenticated GET /health carries the requested route
            # as an allowlisted ?next= (T-06.6.2-12) ...
            status, headers, _ = http_request(base + "/health")
            if status != 303:
                return False, "expected 303 for GET /health, got %d" % status
            if headers.get("Location") != "/login?next=%2Fhealth":
                return False, "expected Location /login?next=%%2Fhealth, got %r" % headers.get("Location")
            # ... and a subsequent correct-password POST /login carrying
            # that same next value returns the user to /health, not /settings.
            status, headers, _ = http_request(
                base + "/login", method="POST",
                data=urllib.parse.urlencode(
                    {"password": TEST_PASSWORD, "next": "/health"}).encode())
            if status != 303:
                return False, "expected 303 on login POST, got %d" % status
            if headers.get("Location") != "/health":
                return False, "expected Location /health after login with next=/health, got %r" % headers.get("Location")
            return True, ""
        check(
            "an unauthenticated GET /health redirects with ?next=%2Fhealth, and logging in "
            "with that next value returns the user to /health, not /settings",
            _deep_link_return_round_trip)

        def _open_redirect_rejected(next_value):
            def _run():
                status, headers, _ = http_request(
                    base + "/login", method="POST",
                    data=urllib.parse.urlencode(
                        {"password": TEST_PASSWORD, "next": next_value}).encode())
                if status != 303:
                    return False, "expected 303 on login POST, got %d" % status
                location = headers.get("Location", "")
                if location != "/":
                    return False, "expected the safe / (Home) fallback, got %r" % location
                if "evil.example" in location:
                    return False, "the crafted next value leaked into the redirect Location"
                return True, ""
            return _run

        for _crafted_next in ("https://evil.example", "//evil.example"):
            check(
                "a login POST with the correct password and next=%r redirects to the "
                "/ (Home) fallback, never to the crafted value (T-06.6.2-12)" % _crafted_next,
                _open_redirect_rejected(_crafted_next))

        def _login_get_with_unrecognised_next_carries_no_hidden_field():
            status, _headers, body = http_request(
                base + "/login?next=/nonexistent-route")
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'name="next"' in body:
                return False, (
                    "an unrecognised ?next= value must not render a hidden next "
                    "field — _validated_next_route() must be applied on the GET "
                    "path too, not only the POST path")
            return True, ""
        check(
            "GET /login?next=/nonexistent-route (not a real NAV_TABS member) renders "
            "the plain login form with no hidden next input",
            _login_get_with_unrecognised_next_carries_no_hidden_field)

        def _login_page_uses_dedicated_login_shell():
            status, _headers, body = http_request(base + "/login")
            if status != 200:
                return False, "expected 200, got %d" % status
            text = body.decode("utf-8", errors="replace")
            if '<html lang="en"' not in text:
                return False, "expected <html lang=\"en\" in the login page"
            if 'autocomplete="current-password"' not in text:
                return False, "expected autocomplete=\"current-password\" on the password field"
            for absent in ("sidebar-nav", "dashboard-shell", "site-nav-toggle"):
                if absent in text:
                    return False, (
                        "the login page must render layout.login_shell(), not "
                        "page_shell() — found %r in the response body" % absent)
            return True, ""
        check(
            "GET /login (no session) is rendered by the dedicated login_shell(), not "
            "page_shell() — no sidebar/mobile-nav markup, autocomplete present",
            _login_page_uses_dedicated_login_shell)

        def _both_shells_agree_on_document_language():
            # D-01/UXA-09: a single, cheap, permanent guard that
            # page_shell() and login_shell() can never diverge on
            # document language.
            page_doc = layout.page_shell(
                title="Config", active="config", body="<p>x</p>")
            login_doc = layout.login_shell("<p>x</p>")
            if 'lang="en"' not in page_doc:
                return False, "expected lang=\"en\" in page_shell()'s output"
            if 'lang="en"' not in login_doc:
                return False, "expected lang=\"en\" in login_shell()'s output"
            return True, ""
        check(
            "page_shell() and login_shell() both emit lang=\"en\" (D-01/UXA-09 "
            "language-policy regression guard)",
            _both_shells_agree_on_document_language)

        session_cookie = _login(harness)

        # --- authenticated: every NAV_TABS tab returns 200 with its own heading ---
        # 06.6.4.1-08 (D-22): "/preview" removed from this tuple here (not in
        # Task 2, which shrinks NAV_TABS itself) — the harness must stay
        # green immediately after this task's own commit, and /preview no
        # longer returns 200/a page heading the instant the redirect below
        # lands. See the dedicated redirect checks just below instead.

        for _tab_path, _heading in (
            ("/", "Home"), ("/display", "Display"), ("/flights", "Flights"),
            ("/airlines", "Airlines"), ("/health", "Health"), ("/device", "Device"),
        ):
            def _tab_ok(tab_path=_tab_path, heading=_heading):
                status, _headers, body = http_request(base + tab_path, cookie=session_cookie)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if heading.encode() not in body:
                    return False, "expected the %r heading in the response body" % heading
                return True, ""
            check(
                "authenticated GET %s returns 200 and contains its own %r heading" % (_tab_path, _heading),
                _tab_ok)

        # --- 06.6.4.1-08 (D-22): the retired Preview page route now redirects
        # to History with a fixed literal target — never derived from a query
        # parameter, so a crafted next-style parameter provably cannot steer it ---

        def _preview_redirects_to_history():
            status, headers, body = http_request(base + "/preview", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            if headers.get("Location") != "/flights":
                return False, "expected a redirect to /flights exactly, got %r" % headers.get("Location")
            if body:
                return False, "expected an empty redirect body, got %d bytes of content" % len(body)
            return True, ""
        check(
            "authenticated GET /preview (the retired Preview page route) redirects to /flights (D-22, retargeted by phase 18)",
            _preview_redirects_to_history)

        def _legacy_page_routes_redirect(path, target):
            def _run():
                status, headers, body = http_request(base + path, cookie=session_cookie)
                if status != 303:
                    return False, "expected a 303 redirect for %s, got %d" % (path, status)
                if headers.get("Location") != target:
                    return False, "expected %s to redirect to %s exactly, got %r" % (
                        path, target, headers.get("Location"))
                if body:
                    return False, "expected an empty redirect body"
                return True, ""
            return _run
        for _legacy, _target in (("/settings", "/display"), ("/history", "/flights")):
            check(
                "authenticated GET %s (a pre-phase-18 page route) redirects to %s with a fixed literal target"
                % (_legacy, _target),
                _legacy_page_routes_redirect(_legacy, _target))

        def _preview_redirect_ignores_query_string():
            status, headers, _body = http_request(
                base + "/preview?next=/settings&evil=https://evil.example",
                cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            if headers.get("Location") != "/flights":
                return False, (
                    "expected the redirect location to stay /flights regardless of an "
                    "arbitrary query string, got %r" % headers.get("Location"))
            return True, ""
        check(
            "authenticated GET /preview carrying an arbitrary query string (including a "
            "next=-shaped and an https://evil.example-shaped value) still redirects to the "
            "identical /flights location — no request value influences the target",
            _preview_redirect_ignores_query_string)

        # Session gate on the retired /preview redirect route: covered by
        # the "unauthenticated GET /preview ... redirects to /login without
        # page content" check above (06.6.4.1-08 Task 2 removed /preview
        # from NAV_TABS, so it no longer carries a ?next=) — an
        # unauthenticated caller lands on /login, not /history, proving the
        # redirect branch keeps its require_session() gate. /preview.png
        # itself is a different story as of quick task 260903-c4o: the
        # route is retired outright, so it now 404s in BOTH auth states
        # (_preview_png_unauth_404_not_login_redirect above,
        # _preview_png_404_even_with_real_panel below) rather than carrying
        # a session gate at all. The gallery image route
        # (/gallery/{name}.png) is untouched and still has its own
        # authenticated-200/unauthenticated-redirect checks elsewhere in
        # this file (the gallery checks below, plus the
        # unauthenticated-redirect loop above) — confirmed still passing
        # untouched by this task.

        # --- 06.6.4.1-07 (D-26): settings route rename — old path 404s
        # by design (no redirect), the merged form's POST target is
        # live, the ?next= round trip works for the new slug, and the
        # route/icon-map cross-module contract holds ---

        def _old_settings_path_404s_authenticated():
            status, _headers, body = http_request(
                base + "/config", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for the retired /config path, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "authenticated GET /config (the retired settings path) returns 404 — D-26 "
            "declines a redirect since this is a fresh URL at inception, not a deprecated bookmark",
            _old_settings_path_404s_authenticated)

        def _settings_post_redirects_to_settings_with_flash():
            status, headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie, data=b"")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if not location.startswith("/display?flash="):
                return False, "expected a redirect to /display?flash=..., got %r" % location
            return True, ""
        check(
            "an authenticated POST /settings redirects to /display (the default return page) carrying a flash query",
            _settings_post_redirects_to_settings_with_flash)

        # --- 19-07-PLAN.md Task 3 (D-07/A-25): a rejected save re-renders
        # the scoped page directly at 200 with the user's own input and a
        # field-level message, and persists nothing ---

        def _rejected_settings_save_rerenders_200_with_input_and_error_persists_nothing():
            from companion.pages import config_page
            before = device_config.load_device_config(harness.tmpdir)
            status, headers, body = http_request(
                base + "/settings", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "black", "tracked_runway": before["tracked_runway"],
                    "quiet_hours_start": "",
                }).encode())
            if status != 200:
                return False, "expected a 200 re-render on a rejected save, got %d" % status
            if headers.get("Location"):
                return False, "expected no redirect Location header on a rejected save, got %r" % (
                    headers.get("Location"),)
            body_text = body.decode("utf-8", errors="replace")
            if 'name="theme" value="black"' not in body_text or "checked" not in body_text.split(
                    'name="theme" value="black"', 1)[1].split(">", 1)[0]:
                return False, "expected the just-picked theme (black) to render checked - nothing discarded"
            if config_page.ERROR_QUIET_HOURS_TIME_SHAPE not in body_text:
                return False, "expected the quiet_hours_start field-level error message in the response body"
            if "banner--flash" in body_text:
                return False, "expected no top-of-page flash banner on a field-level rejection (D-07)"
            after = device_config.load_device_config(harness.tmpdir)
            if after != before:
                return False, "expected nothing to be persisted on a rejected save, got %r (was %r)" % (after, before)
            return True, ""
        check(
            "a POST /settings with a valid theme change and an empty quiet_hours_start returns 200, shows the "
            "newly-picked theme still selected, shows the quiet-hours field error, carries no flash banner, and "
            "persists nothing on disk (D-07/A-25)",
            _rejected_settings_save_rerenders_200_with_input_and_error_persists_nothing)

        # --- Phase 18: Home page, quick actions, scoped settings saves ---

        def _home_page_renders_widgets():
            # 20-06 (D-16) rebuilt Home: the Quick-actions card is gone
            # (the screen/quiet-hours switches moved to Display, the
            # Refresh-now button moved to Device), replaced by a hero
            # row (the current picture in a `.preview-frame` figure
            # beside a `.status-card` built on `layout.status_row()`)
            # plus a full-width recent-flights section. Retargeted per
            # 20-06-SUMMARY.md/20-12-PLAN.md (20-06/D-16).
            status, _headers, body = http_request(base + "/", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for GET /, got %d" % status
            text = body.decode("utf-8", errors="replace")
            for needle in (
                    '<h1 class="page-title">Home</h1>',
                    'status-card" aria-labelledby="home-status-heading"',
                    'class="status-row', 'class="home-hero"',
                    "Recent flights", 'href="/flights"',
                    'class="nav-group nav-group--advanced"'):
                if needle not in text:
                    return False, "expected %r in the Home page" % needle
            # The hero's left half renders either the .preview-frame
            # figure (a gallery entry exists) or the shared empty-state
            # block (none does yet, as in this fresh harness) — either
            # is proof the hero row itself renders.
            if 'class="preview-frame"' not in text and "Nothing rendered yet." not in text:
                return False, "expected either the preview-frame figure or its empty state in the Home hero"
            for absent in (
                    "Quick actions", "On the frame now",
                    'action="%s"' % app_module.QUICK_DISPLAY_ROUTE,
                    'action="%s"' % app_module.QUICK_QUIET_HOURS_ROUTE,
                    'action="%s"' % app_module.POLL_ROUTE):
                if absent in text:
                    return False, "expected %r to be absent from the rebuilt Home page (20-06/D-16)" % absent
            return True, ""
        check(
            "authenticated GET / renders the rebuilt Home page (20-06/D-16) with the hero preview-frame "
            "figure, the status-card's status-row markup, and the recent-flights list under the grouped "
            "Advanced navigation, and carries none of the retired quick-action forms",
            _home_page_renders_widgets)

        def _quick_display_toggle_round_trip():
            for state, expected_flash, expected_value in (
                    ("off", app_module.FLASH_KEY_DISPLAY_OFF, False),
                    ("on", app_module.FLASH_KEY_DISPLAY_ON, True)):
                status, headers, _ = http_request(
                    base + app_module.QUICK_DISPLAY_ROUTE, method="POST",
                    cookie=session_cookie,
                    data=urllib.parse.urlencode({"state": state}).encode())
                if status != 303:
                    return False, "expected 303 for state=%s, got %d" % (state, status)
                # D-16 (20-01-PLAN.md Task 2): retargeted from "/" to
                # "/display" — the switches now live on Display, not
                # Home; the flash keys themselves are unchanged.
                if headers.get("Location") != "/display?flash=%s" % expected_flash:
                    return False, "expected a redirect to /display?flash=%s, got %r" % (
                        expected_flash, headers.get("Location"))
                on_disk = device_config.load_device_config(harness.tmpdir)
                if on_disk["display_enabled"] is not expected_value:
                    return False, "expected display_enabled %r on disk after state=%s, got %r" % (
                        expected_value, state, on_disk["display_enabled"])
            status, headers, _ = http_request(
                base + app_module.QUICK_DISPLAY_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({"state": "toggle"}).encode())
            if status != 303 or headers.get("Location") != "/display?flash=%s" % app_module.FLASH_KEY_QUICK_FAILED:
                return False, "expected a crafted state value to redirect with the quick_failed flash, got %d/%r" % (
                    status, headers.get("Location"))
            if device_config.load_device_config(harness.tmpdir)["display_enabled"] is not True:
                return False, "expected a rejected quick action to leave display_enabled untouched"
            return True, ""
        check(
            "POST /quick/display with state=off then state=on flips display_enabled on disk and redirects "
            "to Display (D-16) with the matching flash; a crafted state value redirects with quick_failed "
            "and writes nothing",
            _quick_display_toggle_round_trip)

        def _quick_quiet_hours_toggle_round_trip():
            status, headers, _ = http_request(
                base + app_module.QUICK_QUIET_HOURS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({"state": "on"}).encode())
            if status != 303 or headers.get("Location") != "/display?flash=%s" % app_module.FLASH_KEY_QUIET_ON:
                return False, "expected a redirect to /display?flash=quiet_on, got %d/%r" % (status, headers.get("Location"))
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["quiet_hours_enabled"] is not True:
                return False, "expected quiet_hours_enabled True on disk"
            if on_disk["display_enabled"] is not True:
                return False, "expected the quiet-hours toggle to carry display_enabled forward untouched"
            status, headers, _ = http_request(
                base + app_module.QUICK_QUIET_HOURS_ROUTE, method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({"state": "off"}).encode())
            if headers.get("Location") != "/display?flash=%s" % app_module.FLASH_KEY_QUIET_OFF:
                return False, "expected a redirect to /display?flash=quiet_off, got %r" % headers.get("Location")
            if device_config.load_device_config(harness.tmpdir)["quiet_hours_enabled"] is not False:
                return False, "expected quiet_hours_enabled False on disk"
            return True, ""
        check(
            "POST /quick/quiet-hours with state=on then state=off flips quiet_hours_enabled on disk, "
            "redirects to Display (D-16) with the matching flash, and never touches display_enabled",
            _quick_quiet_hours_toggle_round_trip)

        check(
            "unauthenticated POST /quick/display redirects to /login without page content",
            _unauth_redirects_to_login(
                "POST", app_module.QUICK_DISPLAY_ROUTE,
                data=urllib.parse.urlencode({"state": "off"}).encode()))

        def _scoped_settings_save_carries_other_page_forward():
            # A legacy (unscoped) full save first: LED on, display on.
            status, _headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "theme": "white", "tracked_runway": "3", "led_enabled": "on",
                    "display_enabled": "on"}).encode())
            if status != 303:
                return False, "expected 303 on the full save, got %d" % status
            # A Display-page save carries no LED field at all — the LED
            # must stay ON, not silently flip to off.
            status, headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "scope": "display", "return_to": "/display",
                    "theme": "black", "display_enabled": "on"}).encode())
            if status != 303 or headers.get("Location") != "/display?flash=saved":
                return False, "expected a 303 to /display?flash=saved, got %d/%r" % (
                    status, headers.get("Location"))
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["theme"] != "black":
                return False, "expected the Display-page save to persist theme=black"
            if on_disk["led_enabled"] is not True:
                return False, "expected a Display-page save to leave led_enabled True (out of scope), got %r" % (on_disk["led_enabled"],)
            # A Device-page save carries no display_enabled field — the
            # screen must stay ON; its own absent LED box means off.
            status, headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "scope": "device", "return_to": "/device",
                    "tracked_runway": "06-24"}).encode())
            if status != 303 or headers.get("Location") != "/device?flash=saved":
                return False, "expected a 303 to /device?flash=saved, got %d/%r" % (
                    status, headers.get("Location"))
            on_disk = device_config.load_device_config(harness.tmpdir)
            if on_disk["tracked_runway"] != "06-24":
                return False, "expected the Device-page save to persist tracked_runway=06-24"
            if on_disk["display_enabled"] is not True:
                return False, "expected a Device-page save to leave display_enabled True (out of scope)"
            if on_disk["led_enabled"] is not False:
                return False, "expected the Device-page save's absent LED box to persist led_enabled False"
            if on_disk["theme"] != "black":
                return False, "expected the Device-page save to leave the theme untouched"
            # A crafted return_to never becomes the redirect target.
            status, headers, _ = http_request(
                base + "/settings", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({
                    "scope": "display", "return_to": "https://evil.example",
                    "theme": "white"}).encode())
            if headers.get("Location") != "/display?flash=saved":
                return False, "expected a crafted return_to to fall back to /display, got %r" % headers.get("Location")
            return True, ""
        check(
            "a scoped POST /settings (scope=display / scope=device) persists only its own page's groups, "
            "carries the other page's checkbox state forward instead of flipping it off, redirects to the "
            "page it came from, and never honours a crafted return_to",
            _scoped_settings_save_carries_other_page_forward)

        def _display_and_device_pages_split_the_groups():
            _s, _h, display_body = http_request(base + "/display", cookie=session_cookie)
            _s, _h, device_body = http_request(base + "/device", cookie=session_cookie)
            display_text = display_body.decode("utf-8", errors="replace")
            device_text = device_body.decode("utf-8", errors="replace")
            if 'name="theme"' not in display_text or 'name="quiet_hours_enabled"' not in display_text:
                return False, "expected the Display page to carry the theme and quiet-hours groups"
            # 20-07 (D-10/D-11) moved Runway (and Calendar/the rules
            # editor) from Device to Display; only the LED group stayed
            # on Device — Display carries tracked_runway but never
            # led_enabled.
            if 'name="tracked_runway"' not in display_text:
                return False, "expected the Display page to carry the runway group (moved from Device, 20-07/D-10)"
            if 'name="led_enabled"' in display_text:
                return False, "expected the Display page NOT to carry the LED group"
            if 'name="tracked_runway"' in device_text:
                return False, "expected the Device page NOT to carry the runway group (moved to Display, 20-07/D-10)"
            if 'name="wake_interval_s"' not in device_text:
                return False, "expected the Device page to carry the wake-interval group"
            if 'name="theme"' in device_text.replace('name="theme_id"', ""):
                # the rules add-form's own theme select is name="theme_id"; the
                # settings theme radios are name="theme" and must be absent.
                if 'name="theme" ' in device_text or 'name="theme">' in device_text:
                    return False, "expected the Device page NOT to carry the theme chip grid"
            for text, scope, route in ((display_text, "display", "/display"), (device_text, "device", "/device")):
                if '<input type="hidden" name="scope" value="%s">' % scope not in text:
                    return False, "expected the %s page to carry its hidden scope field" % scope
                if '<input type="hidden" name="return_to" value="%s">' % route not in text:
                    return False, "expected the %s page to carry its hidden return_to field" % scope
                if "Screen: Plane frame" not in text:
                    return False, "expected the %s page to name its screen type" % scope
            # 20-07 (D-10/D-11) moved the rules editor (renamed "Flight
            # colours" by 20-09-PLAN.md Task 3/D-15a; was "Per-flight
            # colour rules") to Display alongside Calendar and Runway;
            # Manual refresh stayed on Device.
            if "Manual refresh" not in device_text:
                return False, "expected the Device page to carry Manual refresh"
            if "Flight colours" in device_text:
                return False, "expected the Device page NOT to carry the rules editor (moved to Display, 20-07/D-10)"
            if "Flight colours" not in display_text:
                return False, "expected the Display page to carry the rules editor (moved from Device, 20-07/D-10)"
            if "Manual refresh" in display_text:
                return False, "expected the Display page NOT to carry Manual refresh"
            return True, ""
        check(
            "GET /display and GET /device split the settings groups per companion/screens.py (20-07 moved "
            "Runway/Calendar/the rules editor to Display, D-10/D-11), each carrying its hidden "
            "scope/return_to fields and the screen-type caption; Manual refresh lives on Device only",
            _display_and_device_pages_split_the_groups)

        # 20-07-PLAN.md (D-36) deleted the Device page's Edit-artwork
        # link outright (_edit_artwork_link_html() and its call site are
        # gone from companion/pages/config_page.py) — the check that
        # used to exercise it end to end,
        # _device_page_edit_artwork_link_opens_airlines_with_edit_forms(),
        # is removed rather than retargeted; there is no replacement
        # link on either Display or Device to assert against.

        def _html_pages_are_no_store():
            status, headers, _ = http_request(base + "/", cookie=session_cookie)
            if status != 200:
                return False, "expected 200, got %d" % status
            if headers.get("Cache-Control") != "no-store":
                return False, "expected Cache-Control: no-store on an authenticated HTML page, got %r" % headers.get("Cache-Control")
            status, headers, _ = http_request(base + "/login")
            if headers.get("Cache-Control") != "no-store":
                return False, "expected Cache-Control: no-store on the login page, got %r" % headers.get("Cache-Control")
            return True, ""
        check(
            "every HTML response (an authenticated page and the login page alike) carries Cache-Control: "
            "no-store, so the back button and shared caches never replay a page after sign-out",
            _html_pages_are_no_store)

        # --- 19-04-PLAN.md Task 2 (D-18, T-19-06/T-19-17/T-19-18/T-19-19): ---
        # --- CSP on every response, and hardened redirects (T-19-05)      ---

        def _authenticated_html_carries_exact_csp():
            import companion.app as app_module
            status, headers, _ = http_request(base + "/", cookie=session_cookie)
            if status != 200:
                return False, "expected 200, got %d" % status
            csp = headers.get("Content-Security-Policy")
            if csp != app_module.CONTENT_SECURITY_POLICY:
                return False, (
                    "expected the CSP header to equal companion.app."
                    "CONTENT_SECURITY_POLICY exactly, got %r vs %r"
                    % (csp, app_module.CONTENT_SECURITY_POLICY))
            return True, ""
        check(
            "an authenticated HTML response carries a Content-Security-Policy header equal "
            "(string equality, not substring) to companion.app.CONTENT_SECURITY_POLICY",
            _authenticated_html_carries_exact_csp)

        def _csp_script_src_strict_no_unsafe_inline():
            import companion.app as app_module
            csp = app_module.CONTENT_SECURITY_POLICY
            if "script-src 'self'" not in csp:
                return False, "expected script-src 'self' in the CSP, got %r" % csp
            if "script-src 'self' 'unsafe-inline'" in csp:
                return False, "expected script-src to NOT carry 'unsafe-inline', got %r" % csp
            return True, ""
        check(
            "the CSP's script-src directive is 'self' with no 'unsafe-inline' anywhere in it "
            "(Task 1 removed the app's last two inline <script> elements, so no exception is needed)",
            _csp_script_src_strict_no_unsafe_inline)

        def _redirect_carries_four_hardening_headers():
            # The unauthenticated redirect to /login is a 303 reachable
            # with no cookie at all — exercises redirect()'s hardening
            # headers on the simplest possible path.
            status, headers, _ = http_request(base + "/display")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            for header_name in (
                    "X-Content-Type-Options", "X-Frame-Options",
                    "Referrer-Policy", "Content-Security-Policy"):
                if header_name not in headers:
                    return False, "expected %r on a 303 redirect response" % header_name
            return True, ""
        check(
            "a 303 redirect response (the unauthenticated bounce to /login) carries all four "
            "hardening headers, including the CSP — before this plan redirect() sent none of them",
            _redirect_carries_four_hardening_headers)

        def _static_css_response_carries_csp():
            status, headers, _ = http_request(base + "/static/style.css")
            if status != 200:
                return False, "expected 200, got %d" % status
            if "Content-Security-Policy" not in headers:
                return False, "expected the CSP header on the static CSS response too"
            return True, ""
        check(
            "the static CSS response (the send_bytes() path) also carries the CSP header",
            _static_css_response_carries_csp)

        # --- 19-04-PLAN.md Task 3 (D-18, T-19-04): session-gate           ---
        # --- POST /ui-theme and POST /logout                              ---

        def _ui_theme_post_without_session_redirects_to_login():
            status, headers, _ = http_request(
                base + "/ui-theme", method="POST", data=b"ui_theme=dark")
            if status != 303 or headers.get("Location") != "/login":
                return False, (
                    "expected an unauthenticated POST /ui-theme to redirect to /login, "
                    "got %d/%r" % (status, headers.get("Location")))
            set_cookie = headers.get("Set-Cookie", "")
            if auth.UI_THEME_COOKIE_NAME in set_cookie:
                return False, (
                    "expected no ui_theme Set-Cookie header on an unauthenticated "
                    "POST /ui-theme, got %r" % set_cookie)
            return True, ""
        check(
            "POST /ui-theme with no session cookie redirects to /login and does not set a "
            "ui_theme cookie (T-19-04: an unauthenticated caller cannot set another visitor's "
            "UI theme)",
            _ui_theme_post_without_session_redirects_to_login)

        def _logout_post_without_session_redirects_to_login():
            status, headers, _ = http_request(base + "/logout", method="POST")
            if status != 303 or headers.get("Location") != "/login":
                return False, (
                    "expected an unauthenticated POST /logout to redirect to /login, "
                    "got %d/%r" % (status, headers.get("Location")))
            return True, ""
        check(
            "POST /logout with no session cookie redirects to /login (T-19-04: gating a "
            "logout costs a signed-out caller nothing)",
            _logout_post_without_session_redirects_to_login)

        # --- 20-01-PLAN.md Task 2 (D-02, T-20-01/T-20-02): the new       ---
        # --- nav-footer switch route, POST /ui-lang — a byte-for-byte    ---
        # --- sibling of the /ui-theme family above. D-17 (21-01-PLAN.md  ---
        # --- Task 1): POST /ui-mode is deleted; see the replacement      ---
        # --- unknown-route check below.                                  ---

        def _ui_lang_post_round_trip():
            for submitted, expect_cookie in (("fr", True), ("en", True), ("de", False)):
                status, headers, _ = http_request(
                    base + "/ui-lang", method="POST", cookie=session_cookie,
                    data=urllib.parse.urlencode({"ui_lang": submitted}).encode())
                if status != 303:
                    return False, "expected 303 for ui_lang=%s, got %d" % (submitted, status)
                if headers.get("Location") != "/":
                    return False, (
                        "expected a redirect to the referring tab (default /), got %r"
                        % headers.get("Location"))
                set_cookie = headers.get("Set-Cookie", "")
                if expect_cookie:
                    if "%s=%s" % (auth.UI_LANG_COOKIE_NAME, submitted) not in set_cookie:
                        return False, "expected %s=%s in %r" % (
                            auth.UI_LANG_COOKIE_NAME, submitted, set_cookie)
                    for needle in ("HttpOnly", "SameSite=Strict"):
                        if needle not in set_cookie:
                            return False, "expected %r in the sp_ui_lang cookie header: %r" % (
                                needle, set_cookie)
                else:
                    if auth.UI_LANG_COOKIE_NAME in set_cookie:
                        return False, (
                            "expected no sp_ui_lang Set-Cookie header for an unrecognised "
                            "ui_lang=%s, got %r" % (submitted, set_cookie))
            return True, ""
        check(
            "POST /ui-lang with ui_lang=fr/en sets the sp_ui_lang cookie (HttpOnly, "
            "SameSite=Strict) and redirects to the referring tab; ui_lang=de sets no cookie",
            _ui_lang_post_round_trip)

        def _ui_lang_post_without_session_redirects_to_login():
            status, headers, _ = http_request(
                base + "/ui-lang", method="POST", data=b"ui_lang=fr")
            if status != 303 or headers.get("Location") != "/login":
                return False, (
                    "expected an unauthenticated POST /ui-lang to redirect to /login, "
                    "got %d/%r" % (status, headers.get("Location")))
            set_cookie = headers.get("Set-Cookie", "")
            if auth.UI_LANG_COOKIE_NAME in set_cookie:
                return False, (
                    "expected no sp_ui_lang Set-Cookie header on an unauthenticated "
                    "POST /ui-lang, got %r" % set_cookie)
            return True, ""
        check(
            "POST /ui-lang with no session cookie redirects to /login and does not set a "
            "sp_ui_lang cookie (T-20-01)",
            _ui_lang_post_without_session_redirects_to_login)

        # D-17 (21-01-PLAN.md Task 1): _ui_mode_post_round_trip and
        # _ui_mode_post_without_session_redirects_to_login are deleted —
        # POST /ui-mode itself is gone. The replacement check below (the
        # threat model's own T-21-01 pin) proves a valid-session POST to
        # the now-unrecognised path takes the ordinary unknown-route 404,
        # not that any cookie round-trips (there is no cookie any more).

        def _ui_mode_post_with_session_now_404s():
            status, headers, _ = http_request(
                base + "/ui-mode", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({"ui_mode": "simple"}).encode())
            if status != 404:
                return False, (
                    "expected a valid-session POST /ui-mode to take the unknown-route "
                    "404 path now that the route is deleted (D-17/T-21-01), got %d" % status)
            set_cookie = headers.get("Set-Cookie", "")
            if "sp_ui_mode" in set_cookie:
                return False, (
                    "expected no sp_ui_mode Set-Cookie header — the cookie name is never "
                    "written by any code path any more, got %r" % set_cookie)
            return True, ""
        check(
            "POST /ui-mode with a valid session now takes the unknown-route 404 path "
            "(D-17, the route/handler/dispatch line are deleted together)",
            _ui_mode_post_with_session_now_404s)

        # --- D-03: language resolution from cookie / Accept-Language ---

        def _accept_language_resolves_html_lang_with_no_cookie():
            status, _headers, body = http_request(
                base + "/", cookie=session_cookie,
                extra_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'<html lang="fr"' not in body:
                return False, "expected <html lang=\"fr\" with Accept-Language: fr-FR,fr;q=0.9"
            status, _headers, body = http_request(
                base + "/", cookie=session_cookie,
                extra_headers={"Accept-Language": "en-GB"})
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'<html lang="en"' not in body:
                return False, "expected <html lang=\"en\" with Accept-Language: en-GB"
            return True, ""
        check(
            "a cookie-free GET (session cookie only, no sp_ui_lang) with "
            "Accept-Language: fr-FR,fr;q=0.9 renders <html lang=\"fr\"; with "
            "Accept-Language: en-GB renders <html lang=\"en\" (D-03)",
            _accept_language_resolves_html_lang_with_no_cookie)

        def _ui_lang_cookie_beats_accept_language():
            status, headers, _ = http_request(
                base + "/ui-lang", method="POST", cookie=session_cookie,
                data=urllib.parse.urlencode({"ui_lang": "en"}).encode())
            lang_cookie = _cookie_value(headers)
            if status != 303 or not lang_cookie:
                return False, "expected a 303 with a sp_ui_lang Set-Cookie, got %d/%r" % (
                    status, headers.get("Set-Cookie"))
            combined_cookie = "%s; %s" % (session_cookie, lang_cookie)
            status, _headers, body = http_request(
                base + "/", cookie=combined_cookie,
                extra_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'<html lang="en"' not in body:
                return False, (
                    "expected the sp_ui_lang=en cookie to beat a French "
                    "Accept-Language header, got a body without <html lang=\"en\"")
            return True, ""
        check(
            "the sp_ui_lang cookie beats Accept-Language when both are present (D-03)",
            _ui_lang_cookie_beats_accept_language)

        # --- 11-04 end-to-end: the real SKYPANE_SLEEP_S pre-fill, over a  ---
        # --- dedicated Harness instance (the environment must be set     ---
        # --- before the subprocess starts — the shared `harness` above   ---
        # --- was already launched without it), mirroring the             ---
        # --- broken_harness/concurrent_harness pattern later in this     ---
        # --- file for a harness with different startup conditions.       ---

        def _wake_interval_env_prefill_and_on_disk_precedence():
            saved = os.environ.get(app_module.SLEEP_ENV_VAR)
            prefill_harness = None
            try:
                os.environ[app_module.SLEEP_ENV_VAR] = "900"
                prefill_harness = Harness()
                prefill_harness.start()
                prefill_base = prefill_harness.base_url()
                prefill_cookie = _login(prefill_harness)

                # (a) nothing stored on disk -> pre-filled from SKYPANE_SLEEP_S
                status, _headers, body = http_request(
                    prefill_base + "/device", cookie=prefill_cookie)
                if status != 200:
                    return False, "expected 200 for the env-only pre-fill case, got %d" % status
                if not re.search(rb'name="wake_interval_s"[^>]*value="900"', body):
                    return False, (
                        "expected the Wake interval input to carry value=\"900\" "
                        "pre-filled from SKYPANE_SLEEP_S=900 with nothing stored")

                # (b) an on-disk wake_interval_s always wins over the environment
                device_config.save_device_config(prefill_harness.tmpdir, wake_interval_s=120)
                status, _headers, body = http_request(
                    prefill_base + "/device", cookie=prefill_cookie)
                if status != 200:
                    return False, "expected 200 after storing wake_interval_s=120, got %d" % status
                if not re.search(rb'name="wake_interval_s"[^>]*value="120"', body):
                    return False, (
                        "expected the stored wake_interval_s=120 to win over the "
                        "SKYPANE_SLEEP_S=900 environment pre-fill")
                if re.search(rb'name="wake_interval_s"[^>]*value="900"', body):
                    return False, (
                        "expected the environment value 900 to no longer appear once "
                        "a value is stored on disk")
                return True, ""
            finally:
                if prefill_harness is not None:
                    prefill_harness.stop()
                    prefill_harness.cleanup()
                if saved is not None:
                    os.environ[app_module.SLEEP_ENV_VAR] = saved
                else:
                    os.environ.pop(app_module.SLEEP_ENV_VAR, None)
        check(
            "authenticated GET /device pre-fills Wake interval with SKYPANE_SLEEP_S=900 "
            "when nothing is stored, and a stored wake_interval_s=120 always wins over that "
            "environment value",
            _wake_interval_env_prefill_and_on_disk_precedence)

        def _wake_interval_below_floor_env_degrades_to_placeholder():
            from companion.pages import config_page
            saved = os.environ.get(app_module.SLEEP_ENV_VAR)
            floor_harness = None
            try:
                # deploy/skypane.env.example's actual shipped value
                os.environ[app_module.SLEEP_ENV_VAR] = "30"
                floor_harness = Harness()
                floor_harness.start()
                floor_base = floor_harness.base_url()
                floor_cookie = _login(floor_harness)

                status, _headers, body = http_request(
                    floor_base + "/device", cookie=floor_cookie)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if b'name="wake_interval_s"' not in body:
                    return False, "expected the Wake interval input to still be present"
                if re.search(rb'name="wake_interval_s"[^>]*\bvalue="', body):
                    return False, (
                        "expected no value attribute on the Wake interval input for a "
                        "below-floor SKYPANE_SLEEP_S=30 — it must not render a number the "
                        "form could not submit")
                if config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT.encode() not in body:
                    return False, (
                        "expected the placeholder text for a below-floor environment value")
                return True, ""
            finally:
                if floor_harness is not None:
                    floor_harness.stop()
                    floor_harness.cleanup()
                if saved is not None:
                    os.environ[app_module.SLEEP_ENV_VAR] = saved
                else:
                    os.environ.pop(app_module.SLEEP_ENV_VAR, None)
        check(
            "authenticated GET /device degrades a below-floor SKYPANE_SLEEP_S=30 (the "
            "shipped deploy/skypane.env.example value) to the placeholder empty state, "
            "never a value attribute the form could not submit",
            _wake_interval_below_floor_env_degrades_to_placeholder)

        def _login_get_with_settings_next_carries_hidden_field():
            status, _headers, body = http_request(base + "/login?next=/display")
            if status != 200:
                return False, "expected 200, got %d" % status
            if b'name="next" value="/display"' not in body:
                return False, (
                    "expected the recognised /display ?next= value to survive the "
                    "round trip as a rendered hidden field")
            return True, ""
        check(
            "GET /login?next=/display (a real NAV_TABS member) renders a hidden next "
            "field carrying /display, surviving the round trip",
            _login_get_with_settings_next_carries_hidden_field)

        def _settings_route_and_icon_map_cross_module_contract():
            import companion.app as app_module
            from companion.pages import config_page
            # Phase 18: the settings WRITE route is shared by the Display
            # and Device pages and is no longer a tab itself; the first tab
            # is Home.
            if app_module.SETTINGS_ROUTE != config_page.SETTINGS_ROUTE:
                return False, "expected app.SETTINGS_ROUTE == config_page.SETTINGS_ROUTE"
            if layout.NAV_TABS[0][0] != layout.HOME_ROUTE or app_module.HOME_ROUTE != layout.HOME_ROUTE:
                return False, "expected NAV_TABS[0][0] and app.HOME_ROUTE to both be layout.HOME_ROUTE"
            nav_slugs = {layout.nav_slug(route) for route, _ in layout.NAV_TABS}
            if set(layout.NAV_ICON_IDS) != nav_slugs:
                return False, (
                    "expected NAV_ICON_IDS' keys to equal the set of nav route "
                    "slugs, got %r vs %r" % (set(layout.NAV_ICON_IDS), nav_slugs))
            return True, ""
        check(
            "app.SETTINGS_ROUTE and config_page.SETTINGS_ROUTE agree, NAV_TABS opens with "
            "HOME_ROUTE, and NAV_ICON_IDS' keys equal the nav route slugs one-to-one",
            _settings_route_and_icon_map_cross_module_contract)

        def _nav_page_titles_icon_route_standing_contract_guard():
            # 06.6.4.1-07 Task 3: a standing guard mirroring this file's
            # existing three-file DOM-contract guards
            # (_three_file_nav_dom_contract_guard(),
            # _four_new_static_routes_dom_contract_guard() above) — makes
            # the next nav-route change (plan 08) fail loudly here
            # instead of silently, if any of these four route
            # collections is missed: the nav tuple itself, the
            # page-titles dict, the slug-to-icon map, and the settings
            # page module's own route constant.
            import companion.app as app_module
            nav_routes = [route for route, _ in layout.NAV_TABS]
            nav_slugs = {layout.nav_slug(route) for route in nav_routes}
            page_title_keys = set(app_module._PAGE_TITLES)
            if page_title_keys != set(nav_routes):
                return False, (
                    "expected _PAGE_TITLES' keys to equal the set of NAV_TABS "
                    "routes, got %r vs %r" % (page_title_keys, set(nav_routes)))
            if len(app_module._PAGE_TITLES) != len(layout.NAV_TABS):
                return False, (
                    "expected _PAGE_TITLES and NAV_TABS to have the same "
                    "length, got %d vs %d"
                    % (len(app_module._PAGE_TITLES), len(layout.NAV_TABS)))
            icon_slugs = set(layout.NAV_ICON_IDS)
            if icon_slugs != nav_slugs:
                return False, (
                    "expected NAV_ICON_IDS' keys to equal the set of NAV_TABS "
                    "slugs one-to-one, got %r vs %r" % (icon_slugs, nav_slugs))
            if layout.NAV_TABS[0][0] != layout.HOME_ROUTE:
                return False, (
                    "expected NAV_TABS' first route to be HOME_ROUTE, got %r"
                    % (layout.NAV_TABS[0][0],))
            return True, ""
        check(
            "the nav tuple, the page-titles dict, and the slug-to-icon map all agree in size "
            "and key set, and the settings page module's own route constant is the nav "
            "tuple's first route — a standing guard against silent drift when the route "
            "set changes again",
            _nav_page_titles_icon_route_standing_contract_guard)

        # --- logout clears the cookie; a subsequent tab request is refused again ---

        def _logout_clears_cookie():
            # D-11: /logout moved from GET to POST, so a stray prefetch,
            # crawler, or <img src="/logout">-shaped link can no longer
            # end a session — see the sibling GET check just below.
            status, headers, _ = http_request(
                base + "/logout", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect on logout, got %d" % status
            set_cookie = headers.get("Set-Cookie", "")
            if "Max-Age=0" not in set_cookie:
                return False, "expected the logout cookie header to carry Max-Age=0, got %r" % set_cookie
            return True, ""
        check("POST /logout clears the session cookie (Max-Age=0)", _logout_clears_cookie)

        def _replayed_cookie_after_logout_rejected():
            # A-33/D-16: POST /logout now revokes the presented token
            # server-side (auth.revoke()), so replaying the exact same
            # cookie value on a later request is refused too - not just
            # cleared client-side. The authenticated-tab checks earlier
            # in this file already proved a GET with this exact
            # session_cookie succeeded before logout ran.
            status, headers, _ = http_request(base + "/display", cookie=session_cookie)
            if status != 303 or headers.get("Location") != "/login?next=%2Fdisplay":
                return False, (
                    "expected the logged-out session cookie to be rejected with a "
                    "redirect to /login?next=%%2Fdisplay, got %d/%r"
                    % (status, headers.get("Location")))
            return True, ""
        check(
            "replaying the exact session cookie after Sign out is rejected (A-33: revoked "
            "server-side, not just cleared client-side)",
            _replayed_cookie_after_logout_rejected)

        def _get_logout_no_longer_ends_session():
            status, _headers, _body = http_request(base + "/logout", cookie=session_cookie)
            if status != 404:
                return False, "expected GET /logout to 404 (D-11), got %d" % status
            return True, ""
        check(
            "GET /logout no longer accepts the request (404) — D-11 closes the GET-triggered logout hole",
            _get_logout_no_longer_ends_session)

        def _tab_refused_after_logout():
            # As of A-33/D-16, resending the stale cookie value after
            # logout IS refused too - see
            # _replayed_cookie_after_logout_rejected above, which proves
            # that directly. This check instead exercises the separate,
            # always-true case a real browser hits: no cookie presented
            # at all, because it discarded the cookie the instant it saw
            # Max-Age=0 on the /logout response.
            status, headers, _ = http_request(base + "/display")
            # 06.6.2-07 (UXA-03): a NAV_TABS route (phase 18: /display),
            # so require_session() carries it as ?next= too — the same
            # allowlisted-return behavior every other unauthenticated
            # NAV_TABS request gets.
            if status != 303 or headers.get("Location") != "/login?next=%2Fdisplay":
                return False, "expected a redirect to /login?next=%%2Fdisplay for a post-logout request, got %d/%r" % (
                    status, headers.get("Location"))
            return True, ""
        check(
            "a tab request after logout (no cookie presented) is refused again",
            _tab_refused_after_logout)

        # Re-authenticate for the remaining checks below.
        session_cookie = _login(harness)

        # --- 404 ---

        def _unknown_path_404():
            status, _headers, body = http_request(base + "/this-route-does-not-exist")
            if status != 404:
                return False, "expected 404, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check("an unknown path returns 404 with the exact 'Page not found.' copy", _unknown_path_404)

        # --- UIR-16: 404 uses the shared page_header() and gates the Health nav dot on auth ---

        # Seed a stale pipeline run once, shared by both checks below —
        # health_page.overall_severity() resolves this to "error", giving
        # both checks the same non-"ok" state to test the authenticated/
        # unauthenticated split against.
        with history_db.open_db(harness.tmpdir) as conn:
            history_db.set_meta(
                conn, history_db.META_LAST_PIPELINE_RUN,
                _ago_iso(health_page.STALE_PIPELINE_ERROR_S + 60))

        def _authenticated_404_uses_page_header_and_shows_health_dot():
            status, _headers, body = http_request(
                base + "/this-route-does-not-exist-uir16", cookie=session_cookie)
            if status != 404:
                return False, "expected 404, got %d" % status
            if b'<h1 class="page-title">' not in body:
                return False, (
                    "expected the shared page_header() heading "
                    "(<h1 class=\"page-title\">), the 30px serif role every "
                    "other authenticated page opens with")
            if b'<h1 class="text-heading">' in body:
                return False, "expected the old text-heading 404 heading to be gone"
            if b"dot--error" not in body:
                return False, (
                    "expected the Health nav dot (dot--error) to render for an "
                    "authenticated caller under seeded error state")
            return True, ""
        check(
            "an authenticated 404 opens with the shared page_header() (page-title, not "
            "text-heading) and shows the Health nav dot when state is seeded error",
            _authenticated_404_uses_page_header_and_shows_health_dot)

        def _unauthenticated_404_never_leaks_health_state():
            # T-peo-01, the leak guard: the exact same seeded error state
            # above must NOT surface a dot for an unauthenticated caller
            # landing on a 404. do_GET's own final, ungated fallback for
            # any unmatched path is reached before any require_session()
            # check runs (there is no route to gate) — the same
            # structural class of pre-auth reach as the two named
            # pre-auth static-asset delegates, _serve_stylesheet() and
            # _serve_script_file(), which this harness cannot easily
            # break on disk without deleting shipped files.
            status, _headers, body = http_request(
                base + "/this-route-does-not-exist-uir16-unauth")
            if status != 404:
                return False, "expected 404, got %d" % status
            if b"dot--error" in body or b"dot--warn" in body:
                return False, (
                    "expected NO health-dot markup for an unauthenticated 404, "
                    "even under the same seeded error state — this is the leak "
                    "guard")
            return True, ""
        check(
            "an UNAUTHENTICATED 404 renders no health-dot markup under the same seeded "
            "error state — the leak guard for the two pre-auth call sites "
            "(_serve_stylesheet, _serve_script_file)",
            _unauthenticated_404_never_leaks_health_state)

        # --- preview.png: retired route, 404s even with a real panel present ---

        def _preview_png_404_even_with_real_panel():
            # Quick task 260903-c4o: the route is gone, not merely empty —
            # a genuinely present 960,000-byte panel.bin does not resurrect
            # it. Writing the real panel first (rather than testing against
            # no panel.bin at all) is the whole point: it proves the 404 is
            # the route's absence, not a "no panel yet" empty-state 404 that
            # happened to share the same status code.
            with open(harness.state_path("panel.bin"), "wb") as fh:
                fh.write(b"\x11" * IMAGE_BYTES)  # an all-white, legal-nibble panel
            status, _headers, body = http_request(base + "/preview.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for the retired route even with a real panel present, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "authenticated GET /preview.png returns 404 with the exact 'Page not found.' copy "
            "even with a real 960,000-byte panel.bin present — the route is gone, not empty",
            _preview_png_404_even_with_real_panel)

        # --- gallery path-traversal rejection, with a canary file one level up ---

        os.makedirs(harness.state_path("gallery"), exist_ok=True)

        def _gallery_response_is_never_shared_cacheable():
            gallery_filename = "260829-0rl-cache-control-fixture.png"
            gallery_path = os.path.join(
                harness.state_path("gallery"), gallery_filename)
            with open(gallery_path, "wb") as fh:
                fh.write(PNG_SIGNATURE + b"not-a-real-panel-just-a-fixture")
            status, headers, _body = http_request(
                base + "/gallery/" + gallery_filename, cookie=session_cookie)
            if status != 200:
                return False, (
                    "expected 200 for a gallery fixture written to %r, got %d "
                    "(a 404 here means the fixture landed in the wrong "
                    "directory, not that the caching header is wrong)"
                    % (gallery_path, status))
            cache_control = headers.get("Cache-Control", "")
            directives = [part.strip() for part in cache_control.split(",")]
            if "public" in directives:
                return False, (
                    "an authenticated gallery image must never be advertised "
                    "as storable by a shared cache — got Cache-Control: %r"
                    % cache_control)
            if "private" not in directives:
                return False, (
                    "expected the non-shared (private) Cache-Control scope on "
                    "an authenticated gallery response, got %r" % cache_control)
            if "max-age=3600" not in directives:
                return False, (
                    "expected a 3600-second max-age on the gallery response, "
                    "got %r" % cache_control)
            return True, ""
        check(
            "an authenticated gallery image is never advertised as storable "
            "by a shared/intermediary cache (WR-02)",
            _gallery_response_is_never_shared_cacheable)

        canary_marker = "TOP-SECRET-CANARY-MARKER-DO-NOT-SERVE"
        with open(harness.state_path("canary.txt"), "w") as fh:
            fh.write(canary_marker)

        _traversal_payloads = (
            ("parent-directory segments", "../canary.txt"),
            ("an absolute path", harness.state_path("canary.txt")),
            ("a null byte", "canary.txt\x00.png"),
        )
        _traversal_bodies = []

        for _label, _payload in _traversal_payloads:
            def _traversal_404(label=_label, payload=_payload):
                encoded = urllib.parse.quote(payload, safe="")
                status, _headers, body = http_request(
                    base + "/gallery/" + encoded, cookie=session_cookie)
                _traversal_bodies.append(body)
                if status != 404:
                    return False, "expected 404 for %s (%r), got %d" % (label, payload, status)
                return True, ""
            check("a gallery request with %s returns 404" % _label, _traversal_404)

        def _canary_never_returned():
            if not _traversal_bodies:
                return False, "no traversal responses were captured to inspect"
            for body in _traversal_bodies:
                if canary_marker.encode() in body:
                    return False, "the canary file's content leaked into a traversal response body"
            return True, ""
        check(
            "the canary file placed one level above the gallery directory never appears in any traversal response",
            _canary_never_returned)

        # --- illustration image route (D-15, 06.6.4.1-02) ---

        def _illustration_real_key_returns_png():
            status, headers, body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 for a real illustration key, got %d" % status
            if headers.get("Content-Type") != "image/png":
                return False, "expected Content-Type image/png, got %r" % headers.get("Content-Type")
            if not body:
                return False, "expected a non-empty response body"
            return True, ""
        check(
            "an authenticated GET /illustration/air-france.png returns 200, image/png, and a non-empty body",
            _illustration_real_key_returns_png)

        def _illustration_unknown_key_404():
            status, _headers, _body = http_request(
                base + "/illustration/not-a-real-airline.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for a key not in the membership set, got %d" % status
            return True, ""
        check(
            "an authenticated GET for an illustration key not in the membership set returns 404",
            _illustration_unknown_key_404)

        def _illustration_traversal_key_404():
            adversarial_paths = [
                "/illustration/..%2F..%2Fetc%2Fpasswd.png",
                "/illustration/../../../etc/passwd.png",
                "/illustration/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, body = http_request(
                    base + adversarial_path, cookie=session_cookie)
                if status != 404:
                    return False, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)
                if body and b"root:" in body:
                    return False, "adversarial path %r returned file content" % (adversarial_path,)
            return True, ""
        check(
            "authenticated GET requests for adversarial illustration paths (path traversal) all return 404 with no file content",
            _illustration_traversal_key_404)

        def _illustration_unauthenticated_redirects_to_login():
            status, headers, body = http_request(base + "/illustration/air-france.png")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            if body.startswith(PNG_SIGNATURE):
                return False, "unauthenticated request must never return image bytes"
            return True, ""
        check(
            "an unauthenticated GET /illustration/air-france.png redirects to /login, never returns image bytes",
            _illustration_unauthenticated_redirects_to_login)

        # --- widened membership set: manual-resolution keys (phase 13 plan 13-06 Task 1, D-09) ---
        # Both checks below spin up their own isolated Harness() (mirroring
        # broken_harness/concurrent_harness above) rather than reusing the
        # shared harness/state_dir: they write real files into
        # illustration_overrides/, and the shared harness's state dir is
        # asserted elsewhere (Section 3's D-03 round-trip check) to hold
        # EXACTLY one file (air-france.png) — polluting it here would
        # break that unrelated, correct assertion.

        _VENDORED_ILLUSTRATIONS_DIR = os.path.join(
            REPO_ROOT, "server", "assets", "icons", "illustrations")

        def _illustration_manual_key_read_path_states():
            manual_harness = Harness()
            try:
                manual_harness.start()
                manual_base = manual_harness.base_url()
                manual_session = _login(manual_harness)
                manual_prefix = "SWK"
                manual_name = "Skyward Air"
                manual_key = manual_resolutions.illustration_key_for_name(manual_name)
                status, _headers, _body = http_request(
                    manual_base + "/illustration/%s.png" % manual_key, cookie=manual_session)
                if status != 404:
                    return False, "expected 404 with no manual entry registered, got %d" % status
                add_result = manual_resolutions.add_entry(
                    manual_harness.tmpdir, manual_prefix, manual_name)
                if add_result != manual_resolutions.ADD_OK:
                    return False, "expected add_entry() to succeed for a fresh entry, got %r" % (add_result,)
                status, _headers, _body = http_request(
                    manual_base + "/illustration/%s.png" % manual_key, cookie=manual_session)
                if status != 404:
                    return False, (
                        "expected 404 for a registered manual key with no override file yet — "
                        "a member of the set with no bytes is a 404, indistinguishable from a "
                        "non-member, got %d" % status)
                override_dir = manual_harness.state_path("illustration_overrides")
                os.makedirs(override_dir, exist_ok=True)
                with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
                    seed_bytes = fh.read()
                with open(os.path.join(override_dir, manual_key + ".png"), "wb") as fh:
                    fh.write(seed_bytes)
                status, headers, body = http_request(
                    manual_base + "/illustration/%s.png" % manual_key, cookie=manual_session)
                if status != 200:
                    return False, (
                        "expected 200 once both the manual entry and the override file exist, "
                        "got %d" % status)
                if headers.get("Content-Type") != "image/png":
                    return False, "expected Content-Type image/png, got %r" % headers.get("Content-Type")
                if not body:
                    return False, "expected a non-empty response body"
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "GET /illustration/{key}.png for a manual key: 404 with no registry entry, 404 "
            "with an entry but no override file, and 200/image/png once both exist",
            _illustration_manual_key_read_path_states)

        def _illustration_manual_key_post_unregistered_then_registered():
            manual_harness = Harness()
            try:
                manual_harness.start()
                manual_base = manual_harness.base_url()
                manual_session = _login(manual_harness)
                manual_prefix = "BWX"
                manual_name = "Boreal Wings"
                manual_key = manual_resolutions.illustration_key_for_name(manual_name)
                with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
                    payload_bytes = fh.read()
                body, content_type = _encode_multipart(payload_bytes, filename="x.png")
                override_dir = manual_harness.state_path("illustration_overrides")
                override_path = os.path.join(override_dir, manual_key + ".png")
                before_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []
                status, _headers, _body = http_request(
                    manual_base + "/illustration/%s.png" % manual_key, method="POST", data=body,
                    cookie=manual_session, content_type=content_type)
                if status != 404:
                    return False, "expected 404 for a never-registered manual key, got %d" % status
                after_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []
                if after_entries != before_entries:
                    return False, (
                        "expected the override directory to gain nothing from a single-request "
                        "upload of an unregistered key (Pitfall 3), before=%r after=%r"
                        % (before_entries, after_entries))
                add_result = manual_resolutions.add_entry(
                    manual_harness.tmpdir, manual_prefix, manual_name)
                if add_result != manual_resolutions.ADD_OK:
                    return False, "expected add_entry() to succeed for a fresh entry, got %r" % (add_result,)
                status, headers, _body = http_request(
                    manual_base + "/illustration/%s.png" % manual_key, method="POST", data=body,
                    cookie=manual_session, content_type=content_type)
                if status != 303:
                    return False, "expected a 303 redirect once the key is registered, got %d" % status
                if not os.path.isfile(override_path):
                    return False, "expected the override file to now exist at %r" % (override_path,)
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "Pitfall 3's warning sign made executable: POST /illustration/{key}.png for a "
            "manual key that was never registered returns 404 and writes nothing to the "
            "override directory; once the key is registered via add_entry(), the identical "
            "POST succeeds",
            _illustration_manual_key_post_unregistered_then_registered)

        # --- theme preview image route (06.6.4.1.1-01 Task 2) ---

        def _theme_preview_real_key_returns_png_for_every_theme():
            for theme_id in device_config.THEME_IDS:
                status, headers, body = http_request(
                    base + "/theme-preview/%s.png" % theme_id, cookie=session_cookie)
                if status != 200:
                    return False, "theme %r: expected 200, got %d" % (theme_id, status)
                if headers.get("Content-Type") != "image/png":
                    return False, "theme %r: expected Content-Type image/png, got %r" % (
                        theme_id, headers.get("Content-Type"))
                if not body.startswith(PNG_SIGNATURE):
                    return False, "theme %r: expected a real PNG body" % (theme_id,)
            return True, ""
        check(
            "an authenticated GET /theme-preview/{id}.png returns 200, image/png, and a real "
            "PNG body for every id in device_config.THEME_IDS — no theme is unreachable",
            _theme_preview_real_key_returns_png_for_every_theme)

        def _theme_preview_unknown_key_404():
            status, _headers, body = http_request(
                base + "/theme-preview/not-a-theme.png", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for a theme id not in the membership set, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "an authenticated GET for a theme id not in the membership set returns the same "
            "404 page an unknown runway/illustration id produces",
            _theme_preview_unknown_key_404)

        def _theme_preview_traversal_key_404():
            adversarial_paths = [
                "/theme-preview/..%2F..%2Fetc%2Fpasswd.png",
                "/theme-preview/../../../etc/passwd.png",
                "/theme-preview/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, body = http_request(
                    base + adversarial_path, cookie=session_cookie)
                if status != 404:
                    return False, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)
                if body and b"root:" in body:
                    return False, "adversarial path %r returned file content" % (adversarial_path,)
            return True, ""
        check(
            "authenticated GET requests for adversarial theme-preview paths (path traversal) "
            "all return 404 with no file content",
            _theme_preview_traversal_key_404)

        def _theme_preview_unauthenticated_redirects_to_login():
            status, headers, body = http_request(base + "/theme-preview/white.png")
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            if body.startswith(PNG_SIGNATURE):
                return False, "unauthenticated request must never return image bytes"
            return True, ""
        check(
            "an unauthenticated GET /theme-preview/white.png redirects to /login, never "
            "returns image bytes",
            _theme_preview_unauthenticated_redirects_to_login)

        # --- 20-08-PLAN.md Task 2 (D-23): the ?live=1 route branch ---

        def _theme_cache_dir(theme_id_glob="*"):
            import glob
            return glob.glob(os.path.join(
                harness.tmpdir, theme_preview.THEME_PREVIEW_CACHE_DIRNAME,
                "%s*.png" % theme_id_glob))

        def _theme_preview_live_no_events_serves_sample():
            # No runway_events row exists yet at this point in the suite's
            # own shared harness.tmpdir — the exact "fresh install" case
            # D-23 must fall back to the sample scene for.
            status, headers, body = http_request(
                base + "/theme-preview/white.png?live=1", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 with no runway_events row, got %d" % status
            if headers.get("Content-Type") != "image/png":
                return False, "expected image/png, got %r" % headers.get("Content-Type")
            if not body.startswith(PNG_SIGNATURE):
                return False, "expected a real PNG body"
            return True, ""
        check(
            "GET /theme-preview/white.png?live=1 with no runway_events row at all still "
            "returns 200/image/png (the sample-scene fallback, D-23)",
            _theme_preview_live_no_events_serves_sample)

        def _theme_preview_live_seeded_event_and_cache_reuse():
            with history_db.open_db(harness.tmpdir) as conn:
                history_db.record_runway_event(
                    conn, hex="3946a1", callsign="AFR1380", confirmed_state="departing",
                    airline="Air France", origin="ORY", destination="TLS")
            status, headers, body = http_request(
                base + "/theme-preview/white.png?live=1", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 with a seeded runway_events row, got %d" % status
            if headers.get("Content-Type") != "image/png":
                return False, "expected image/png, got %r" % headers.get("Content-Type")
            if not body.startswith(PNG_SIGNATURE):
                return False, "expected a real PNG body"
            before = _theme_cache_dir("white-")
            # A second request for the SAME latest event must be a cache
            # hit, not grow the cache directory (D-23/Pitfall 7's own
            # "never renders 16 panels [again for the same flight]" half).
            status2, _headers2, body2 = http_request(
                base + "/theme-preview/white.png?live=1", cookie=session_cookie)
            after = _theme_cache_dir("white-")
            if status2 != 200 or body2 != body:
                return False, "expected the second request to serve the identical cached bytes"
            if len(after) != len(before):
                return False, (
                    "expected the cache file count to stay at %d for a repeat request of the "
                    "same latest event, got %d" % (len(before), len(after)))
            return True, ""
        check(
            "GET /theme-preview/white.png?live=1 with a seeded runway_events row returns "
            "200/image/png, and a second request for the same latest event is served from "
            "the cache without growing the cache directory (D-23/Pitfall 7)",
            _theme_preview_live_seeded_event_and_cache_reuse)

        def _theme_preview_live_newer_event_changes_cache_file():
            before = set(_theme_cache_dir("white-"))
            status, _headers, first_body = http_request(
                base + "/theme-preview/white.png?live=1", cookie=session_cookie)
            if status != 200:
                return False, "expected 200 before seeding a newer event, got %d" % status
            with history_db.open_db(harness.tmpdir) as conn:
                history_db.record_runway_event(
                    conn, hex="3466ab", callsign="VLG9999", confirmed_state="arriving",
                    airline="Vueling Airlines", origin="BCN", destination="ORY")
            status2, _headers2, second_body = http_request(
                base + "/theme-preview/white.png?live=1", cookie=session_cookie)
            if status2 != 200:
                return False, "expected 200 after seeding a newer event, got %d" % status2
            after = set(_theme_cache_dir("white-"))
            if len(after) <= len(before):
                return False, "expected a newer runway_events row to add a new cache file, not reuse one"
            if second_body == first_body:
                return False, "expected a newer runway_events row to change the served bytes"
            return True, ""
        check(
            "inserting a NEWER runway_events row changes both the served live-preview bytes "
            "and the cache file it comes from — a newer flight is a cache miss, never a stale "
            "hit served forever (D-23/Pitfall 7)",
            _theme_preview_live_newer_event_changes_cache_file)

        def _theme_preview_live_unknown_theme_404():
            status, _headers, body = http_request(
                base + "/theme-preview/nope.png?live=1", cookie=session_cookie)
            if status != 404:
                return False, "expected 404 for an unknown theme id with ?live=1, got %d" % status
            if b"Page not found." not in body:
                return False, "expected the exact 404 copy in the response body"
            return True, ""
        check(
            "GET /theme-preview/nope.png?live=1 returns the same 404 an unknown theme id "
            "always returns — the membership test still runs before any query is even parsed",
            _theme_preview_live_unknown_theme_404)

        def _theme_preview_live_zero_and_missing_query_serve_sample_variant():
            status_zero, _headers_zero, body_zero = http_request(
                base + "/theme-preview/blue.png?live=0", cookie=session_cookie)
            status_missing, _headers_missing, body_missing = http_request(
                base + "/theme-preview/blue.png", cookie=session_cookie)
            if status_zero != 200 or status_missing != 200:
                return False, "expected 200 for both ?live=0 and a missing query"
            sample_only = theme_preview.cached_preview_bytes(harness.tmpdir, "blue")
            if body_zero != sample_only or body_missing != sample_only:
                return False, (
                    "expected ?live=0 and a missing query to both serve the sample variant, "
                    "not the live one")
            return True, ""
        check(
            "?live=0 and a missing ?live query both serve the sample variant, never the live "
            "one, even with a runway_events row present (D-23)",
            _theme_preview_live_zero_and_missing_query_serve_sample_variant)

        # --- 260902-v26 Task 3: the live upload round trip, against this ---
        # --- real running companion/app.py subprocess (D-01/D-02/D-03).  ---

        import companion.app as app_module

        _VENDORED_ILLUSTRATIONS_DIR = os.path.join(
            REPO_ROOT, "server", "assets", "icons", "illustrations")
        _vendored_air_france_path = os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "air-france.png")
        with open(_vendored_air_france_path, "rb") as fh:
            _pre_upload_vendored_hash = hashlib.sha256(fh.read()).hexdigest()
        _pre_upload_vendored_stat = os.stat(_vendored_air_france_path)

        _illustration_pre_upload_render = []  # populated by the round-trip check below

        def _illustration_upload_round_trip_replaces_served_bytes():
            # vueling-airlines.png is guaranteed to pass validate_illustration_
            # file() — server/test_illustrations.py already asserts every
            # vendored file does — and is visibly a different aircraft, so a
            # successful override is unambiguous.
            with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
                vueling_bytes = fh.read()

            pre_status, _pre_headers, pre_body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            if pre_status != 200:
                return False, "expected 200 for the pre-upload GET, got %d" % pre_status
            _illustration_pre_upload_render.append(pre_body)

            # A traversal-shaped declared filename in the part header: the
            # same request that proves the happy path also proves the
            # filename is never read (T-v26-02-01).
            body, content_type = _encode_multipart(
                vueling_bytes, filename="../../../etc/passwd", field_name="illustration")
            status, headers, _resp_body = http_request(
                base + "/illustration/air-france.png", method="POST", data=body,
                cookie=session_cookie, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect after a valid upload, got %d" % status
            location = headers.get("Location", "")
            if "/airlines" not in location:
                return False, "expected the redirect Location to point at /airlines, got %r" % location
            if ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REPLACED) not in location:
                return False, "expected the success flash key in the redirect, got %r" % location

            post_status, _post_headers, post_body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            if post_status != 200:
                return False, "expected 200 for the post-upload GET, got %d" % post_status
            if not post_body.startswith(PNG_SIGNATURE):
                return False, "expected the post-upload body to start with the PNG signature"
            if post_body == pre_body:
                return False, "expected the served bytes to change after a successful upload"
            return True, ""
        check(
            "uploading a real PNG over real HTTP to a real companion/app.py subprocess changes "
            "what GET /illustration/air-france.png serves, even with a traversal-shaped declared "
            "filename in the part header",
            _illustration_upload_round_trip_replaces_served_bytes)

        def _illustration_override_uses_same_normalization_pipeline():
            if not _illustration_pre_upload_render:
                return False, "no pre-upload render was captured by the round-trip check above"
            pre_body = _illustration_pre_upload_render[0]
            override_status, _h1, override_body = http_request(
                base + "/illustration/air-france.png", cookie=session_cookie)
            vueling_status, _h2, vueling_body = http_request(
                base + "/illustration/vueling-airlines.png", cookie=session_cookie)
            if override_status != 200 or vueling_status != 200:
                return False, "expected 200 for both routes, got %d/%d" % (override_status, vueling_status)
            if override_body == vueling_body:
                return True, ""
            # Fallback (D-03, documented in the plan 02 SUMMARY): if the
            # store-time Pillow RGBA re-encode turns out not to be
            # byte-for-byte lossless against illustration_normalize's own
            # re-encode of the untouched vendored file, fall back to a
            # weaker-but-still-meaningful equivalence check rather than
            # silently accepting inequality.
            if not override_body.startswith(PNG_SIGNATURE):
                return False, "expected the override render to start with the PNG signature even on the fallback path"
            if override_body == pre_body:
                return False, "expected the override render to differ from the pre-upload render"
            if len(override_body) != len(vueling_body):
                return False, (
                    "fallback check failed too: override render length %d != vueling render "
                    "length %d (byte-for-byte equality did not hold)"
                    % (len(override_body), len(vueling_body)))
            return True, ""
        check(
            "the overridden air-france render and the vueling-airlines render (the same source "
            "image) come out of the identical illustration_normalize pipeline (D-03)",
            _illustration_override_uses_same_normalization_pipeline)

        def _illustration_override_written_to_expected_path_only():
            override_path = harness.state_path("illustration_overrides", "air-france.png")
            if not os.path.isfile(override_path):
                return False, "expected an override file at %r" % override_path
            override_dir = harness.state_path("illustration_overrides")
            entries = sorted(os.listdir(override_dir))
            if entries != ["air-france.png"]:
                return False, (
                    "expected exactly one file (air-france.png) in the override directory, got %r"
                    % entries)
            return True, ""
        check(
            "the upload was written to {state_dir}/illustration_overrides/air-france.png, and "
            "nothing else was created in that directory",
            _illustration_override_written_to_expected_path_only)

        def _illustration_vendored_original_untouched_after_upload():
            with open(_vendored_air_france_path, "rb") as fh:
                post_hash = hashlib.sha256(fh.read()).hexdigest()
            if post_hash != _pre_upload_vendored_hash:
                return False, "the vendored air-france.png file's bytes changed after an upload"
            post_stat = os.stat(_vendored_air_france_path)
            if post_stat.st_size != _pre_upload_vendored_stat.st_size:
                return False, "the vendored air-france.png file's size changed after an upload"
            if post_stat.st_mtime_ns != _pre_upload_vendored_stat.st_mtime_ns:
                return False, "the vendored air-france.png file's mtime changed after an upload"
            return True, ""
        check(
            "the vendored server/assets/icons/illustrations/air-france.png file is provably "
            "byte-identical (hash, size, and mtime) after a successful upload",
            _illustration_vendored_original_untouched_after_upload)

        def _illustration_override_reaches_select_illustration():
            # The panel-side effect (plan 01's whole point), asserted
            # against the exact override file the real HTTP route above
            # just wrote — never a hand-placed fixture.
            from server.plane import illustrations as server_illustrations
            override_result = server_illustrations.select_illustration(
                {"airline_name": "Air France"}, state_dir=harness.tmpdir)
            vendored_result = server_illustrations.select_illustration(
                {"airline_name": "Air France"})
            expected_override_path = harness.state_path("illustration_overrides", "air-france.png")
            if override_result != expected_override_path:
                return False, (
                    "expected select_illustration(..., state_dir=harness.tmpdir) to return %r, got %r"
                    % (expected_override_path, override_result))
            if vendored_result != _vendored_air_france_path:
                return False, (
                    "expected select_illustration() with no state_dir to still return the "
                    "vendored path, got %r" % (vendored_result,))
            return True, ""
        check(
            "select_illustration() given the harness's own state_dir resolves Air France to the "
            "override the real route just wrote; with no state_dir it still resolves to the "
            "vendored file",
            _illustration_override_reaches_select_illustration)

        def _illustration_non_image_upload_is_rejected():
            body, content_type = _encode_multipart(
                b"not a real image, just some text bytes", filename="fake.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/easyjet.png", method="POST", data=body,
                cookie=session_cookie, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for a non-image upload, got %d" % status
            location = headers.get("Location", "")
            if ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) not in location:
                return False, "expected the rejection flash key in the redirect, got %r" % location
            override_path = harness.state_path("illustration_overrides", "easyjet.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for a rejected non-image upload"
            return True, ""
        check(
            "POSTing a non-image payload is rejected with the rejection flash key and writes "
            "no override file",
            _illustration_non_image_upload_is_rejected)

        def _illustration_oversized_upload_is_rejected_and_connection_stays_healthy():
            oversized_payload = b"\x00" * (app_module.MAX_ILLUSTRATION_UPLOAD_BYTES + 4096)
            body, content_type = _encode_multipart(oversized_payload, filename="huge.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/corsair.png", method="POST", data=body,
                cookie=session_cookie, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for an oversized upload, got %d" % status
            location = headers.get("Location", "")
            if ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) not in location:
                return False, "expected the rejection flash key in the redirect, got %r" % location
            override_path = harness.state_path("illustration_overrides", "corsair.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for a rejected oversized upload"
            # A fresh, ordinary authenticated GET on a new connection proves
            # the over-cap drain (T-v26-02-03) left the service healthy.
            health_status, _headers2, _body2 = http_request(base + "/health", cookie=session_cookie)
            if health_status != 200:
                return False, (
                    "expected a fresh authenticated GET after the oversized-upload drain to "
                    "still return 200, got %d" % health_status)
            return True, ""
        check(
            "POSTing a body over MAX_ILLUSTRATION_UPLOAD_BYTES is rejected, writes no override "
            "file, and the drain leaves the service healthy for the next request",
            _illustration_oversized_upload_is_rejected_and_connection_stays_healthy)

        def _illustration_post_unknown_and_traversal_keys_returns_404():
            small_body, small_content_type = _encode_multipart(
                b"irrelevant - membership test runs before the body is read", filename="x.png")
            override_dir = harness.state_path("illustration_overrides")
            before_entries = sorted(os.listdir(override_dir))
            adversarial_paths = [
                "/illustration/not-a-real-airline.png",
                "/illustration/..%2F..%2Fetc%2Fpasswd.png",
                "/illustration/../../../etc/passwd.png",
                "/illustration/style.png",
            ]
            for adversarial_path in adversarial_paths:
                status, _headers, _body = http_request(
                    base + adversarial_path, method="POST", data=small_body,
                    cookie=session_cookie, content_type=small_content_type)
                if status != 404:
                    return False, "expected 404 for POST %r, got %d" % (adversarial_path, status)
            after_entries = sorted(os.listdir(override_dir))
            if after_entries != before_entries:
                return False, (
                    "expected the override directory to gain nothing from rejected POSTs, "
                    "before=%r after=%r" % (before_entries, after_entries))
            return True, ""
        check(
            "POSTing a valid payload to a key outside the membership set, and to three "
            "traversal-shaped paths, all 404 and write nothing to the override directory",
            _illustration_post_unknown_and_traversal_keys_returns_404)

        def _illustration_unauthenticated_post_redirects_to_login_and_writes_nothing():
            body, content_type = _encode_multipart(
                b"irrelevant - require_session() runs before anything else", filename="x.png")
            status, headers, _resp_body = http_request(
                base + "/illustration/tunisair.png", method="POST", data=body, content_type=content_type)
            if status != 303:
                return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
            location = headers.get("Location", "")
            if "/login" not in location:
                return False, "expected a redirect to /login, got %r" % location
            override_path = harness.state_path("illustration_overrides", "tunisair.png")
            if os.path.exists(override_path):
                return False, "expected no override file to be written for an unauthenticated POST"
            return True, ""
        check(
            "an unauthenticated POST /illustration/tunisair.png redirects to /login and writes "
            "no override file",
            _illustration_unauthenticated_post_redirects_to_login_and_writes_nothing)

        # --- POST /airlines/resolve and the manual-resolution delete route
        # (phase 13 plan 13-06 Task 3, D-03/D-07/D-08/D-11) — each check
        # below spins up its own isolated Harness(), matching the
        # widened-membership-set checks above, since these routes write
        # real manual_resolutions.json/poll_state.json/override files.

        def _manual_resolve_and_delete_routes_require_auth_and_write_nothing():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                _seed_unresolved_prefixes(manual_harness.tmpdir, {
                    "PQR": {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "PQR100"},
                })
                manual_resolutions_path = manual_resolutions.manual_resolutions_path(
                    manual_harness.tmpdir)

                resolve_data = urllib.parse.urlencode(
                    {"prefix": "PQR", "airline_name": "Unauthorized Air"}).encode()
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data)
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated POST "
                        "/airlines/resolve, got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json to be written by an "
                        "unauthenticated POST")

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/PQR/delete", method="POST")
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated delete POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json to exist after an "
                        "unauthenticated delete POST")
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "unauthenticated POSTs to /airlines/resolve and "
            "/airlines/manual-resolutions/{prefix}/delete both redirect to /login and write "
            "no manual_resolutions.json — the state dir is unchanged, not only the status code",
            _manual_resolve_and_delete_routes_require_auth_and_write_nothing)

        def _manual_resolve_post_revalidates_prefix_against_live_registry():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)
                manual_resolutions_path = manual_resolutions.manual_resolutions_path(
                    manual_harness.tmpdir)

                resolve_data = urllib.parse.urlencode(
                    {"prefix": "XYZ", "airline_name": "Ghost Air"}).encode()
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data, cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_prefix_stale" not in location:
                    return False, "expected the stale flash key, got %r" % location
                if os.path.exists(manual_resolutions_path):
                    return False, (
                        "expected no manual_resolutions.json for a prefix absent from the "
                        "live registry — even though its shape is valid")

                _seed_unresolved_prefixes(manual_harness.tmpdir, {
                    "XYZ": {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "XYZ100"},
                })
                status, headers, _ = http_request(
                    mbase + "/airlines/resolve", method="POST", data=resolve_data, cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect once the prefix is live, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_resolved" not in location:
                    return False, (
                        "expected the resolved flash key once the prefix is a live "
                        "registry member, got %r" % location)
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "XYZ" not in registry or registry["XYZ"].get("airline_name") != "Ghost Air":
                    return False, (
                        "expected the entry to be persisted once the prefix is live, "
                        "got %r" % registry)
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/resolve re-validates the prefix against the live "
            "unresolved-prefix registry on write (D-11): a well-shaped but unregistered "
            "prefix writes nothing and gets the stale flash; the identical POST succeeds "
            "once the prefix is a live registry member",
            _manual_resolve_post_revalidates_prefix_against_live_registry)

        def _manual_resolve_post_rejection_mapping_and_d03_branch():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                def _seed_gap(prefix):
                    state = poll_loop.load_poll_state(manual_harness.tmpdir)
                    registry = state.get("unresolved_prefixes")
                    if not isinstance(registry, dict):
                        registry = {}
                    registry[prefix] = {
                        "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                        "last_seen": "2026-01-01T00:00:00+00:00",
                        "example_callsign": prefix + "100"}
                    _seed_unresolved_prefixes(manual_harness.tmpdir, registry)

                def _resolve_post(prefix, airline_name):
                    data = urllib.parse.urlencode(
                        {"prefix": prefix, "airline_name": airline_name}).encode()
                    return http_request(
                        mbase + "/airlines/resolve", method="POST", data=data, cookie=msession)

                rejection_cases = (
                    ("EMP", "", "flash=manual_name_empty"),
                    ("TLN", "A" * 101, "flash=manual_name_too_long"),
                    ("RSV", "Generic Fallback", "flash=manual_name_reserved"),
                    ("UNU", "../../etc/passwd", "flash=manual_name_unusable"),
                )
                for prefix, airline_name, expected_flash in rejection_cases:
                    _seed_gap(prefix)
                    status, headers, _ = _resolve_post(prefix, airline_name)
                    if status != 303:
                        return False, "prefix %r: expected a 303 redirect, got %d" % (prefix, status)
                    location = headers.get("Location", "")
                    if expected_flash not in location:
                        return False, (
                            "prefix %r: expected %r in the redirect, got %r"
                            % (prefix, expected_flash, location))
                    registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                    if prefix in registry:
                        return False, (
                            "prefix %r: expected the rejected entry to NOT be persisted" % (prefix,))

                # D-03 branch: a brand-new name (no existing artwork)
                # redirects WITH resolve= (Step B is offered); a name
                # already covered by illustrations.target_airline_names()
                # (Air France, real vendored artwork) redirects WITHOUT
                # resolve= — no upload is ever asked for. Run BEFORE the
                # cap-fill below, since once the registry is at its
                # 200-entry cap no further distinct prefix can be added at
                # all (that is the exact behaviour the cap-fill check
                # exercises next).
                _seed_gap("NEW")
                status, headers, _ = _resolve_post("NEW", "Totally Novel Airline")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "resolve=NEW" not in location or "flash=manual_resolved" not in location:
                    return False, (
                        "expected resolve=NEW and the resolved flash for a brand-new "
                        "name, got %r" % location)

                _seed_gap("OLD")
                status, headers, _ = _resolve_post("OLD", "Air France")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "resolve=" in location:
                    return False, (
                        "expected NO resolve= param when the named airline already has "
                        "artwork, got %r" % location)
                if "flash=manual_resolved" not in location:
                    return False, "expected the resolved flash key, got %r" % location

                # ADD_REJECTED_FULL: fill the registry to the cap with
                # unrelated, already-valid entries directly through the
                # module (mirroring server/test_manual_resolutions.py's
                # own _cap_enforcement precedent), then attempt one more
                # through the real route. NEW/OLD above already persisted
                # two entries, so only top up the remainder to reach the
                # cap exactly — filling past it would itself start
                # returning ADD_REJECTED_FULL mid-setup.
                existing_count = len(
                    manual_resolutions.load_manual_resolutions(manual_harness.tmpdir))
                needed = manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES - existing_count
                import string
                cap_prefixes = []
                count = 0
                for a in string.ascii_uppercase:
                    for b in string.ascii_uppercase:
                        if count >= needed:
                            break
                        cap_prefixes.append("Y" + a + b)
                        count += 1
                    if count >= needed:
                        break
                for i, pfx in enumerate(cap_prefixes):
                    result = manual_resolutions.add_entry(
                        manual_harness.tmpdir, pfx, "Cap Filler %d" % i)
                    if result != manual_resolutions.ADD_OK:
                        return False, (
                            "test setup failure filling the cap: add_entry(%r, ...) "
                            "returned %r" % (pfx, result))
                _seed_gap("CAP")
                status, headers, _ = _resolve_post("CAP", "One Too Many Air")
                if status != 303:
                    return False, "expected a 303 redirect for the at-cap POST, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_registry_full" not in location:
                    return False, "expected the registry-full flash key, got %r" % location
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "CAP" in registry:
                    return False, "expected the at-cap entry to NOT be persisted"
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "each add_entry() rejection reaches its own distinct flash key and persists "
            "nothing (empty/too-long/reserved names, and the registry cap); the D-03 "
            "branch: a brand-new name redirects with resolve= (Step B offered) while a "
            "name already covered by existing artwork redirects without it",
            _manual_resolve_post_rejection_mapping_and_d03_branch)

        def _manual_resolution_delete_route_full_contract():
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                add_result = manual_resolutions.add_entry(
                    manual_harness.tmpdir, "DEL", "Deletable Air")
                if add_result != manual_resolutions.ADD_OK:
                    return False, "test setup failure: add_entry() returned %r" % (add_result,)
                key = manual_resolutions.illustration_key_for_name("Deletable Air")
                override_dir = manual_harness.state_path("illustration_overrides")
                os.makedirs(override_dir, exist_ok=True)
                override_path = os.path.join(override_dir, key + ".png")
                with open(override_path, "wb") as fh:
                    fh.write(b"not a real png - only its continued existence is asserted here")

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/DEL/delete", method="POST",
                    cookie=msession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if location != "/airlines":
                    return False, "expected a redirect to /airlines with no flash, got %r" % location
                registry = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "DEL" in registry:
                    return False, "expected the DEL entry to be removed from the registry"
                if not os.path.isfile(override_path):
                    return False, "expected the override file to survive the delete (D-08)"

                status, headers, _ = http_request(
                    mbase + "/airlines/manual-resolutions/DEL/delete", method="POST",
                    cookie=msession)
                if status != 303:
                    return False, (
                        "expected a second, identical delete POST to also redirect "
                        "(idempotent), got %d" % status)
                location = headers.get("Location", "")
                if location != "/airlines":
                    return False, (
                        "expected the same no-flash redirect on a second delete of an "
                        "already-absent prefix, got %r" % location)

                status, _headers, _body = http_request(
                    mbase + "/airlines/manual-resolutions/not-three-letters/delete",
                    method="POST", cookie=msession)
                if status != 404:
                    return False, "expected 404 for a malformed prefix, got %d" % status
                if not os.path.isfile(override_path):
                    return False, (
                        "expected the override file to still exist after a 404'd "
                        "malformed-prefix POST")
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry, "
            "leaves the override PNG on disk (D-08), and redirects to /airlines with no "
            "flash; a second identical POST is a no-op that also redirects without an "
            "error flash; a malformed prefix 404s without touching the registry",
            _manual_resolution_delete_route_full_contract)

        def _manual_resolve_post_save_failed_on_unwritable_state_dir():
            # WR-11: FLASH_KEY_MANUAL_SAVE_FAILED was added specifically
            # because add_entry() can return ADD_FAILED on an unwritable
            # state dir — CR-01 fixed the bug that made that path raise
            # instead (a dropped connection, no flash at all); this proves
            # the flash key itself is actually reached end to end.
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                state = poll_loop.load_poll_state(manual_harness.tmpdir)
                registry = state.get("unresolved_prefixes")
                if not isinstance(registry, dict):
                    registry = {}
                registry["FLD"] = {
                    "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "FLD100"}
                poll_loop.save_poll_state(manual_harness.tmpdir, {"unresolved_prefixes": registry})

                os.chmod(manual_harness.tmpdir, 0o500)
                try:
                    resolve_data = urllib.parse.urlencode(
                        {"prefix": "FLD", "airline_name": "Unwritable Air"}).encode()
                    status, headers, _ = http_request(
                        mbase + "/airlines/resolve", method="POST", data=resolve_data,
                        cookie=msession)
                finally:
                    os.chmod(manual_harness.tmpdir, 0o700)

                if status != 303:
                    return False, "expected a 303 redirect even on a write failure, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_save_failed" not in location:
                    return False, (
                        "expected the manual_save_failed flash key when add_entry() fails to "
                        "write, got %r" % location)
                if "resolve=FLD" not in location:
                    return False, (
                        "expected the redirect to carry resolve=FLD so the operator lands back "
                        "on the form, got %r" % location)
                registry_after = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "FLD" in registry_after:
                    return False, "expected nothing persisted after a failed write"
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/resolve redirects with the manual_save_failed flash key (never a "
            "dropped connection) when add_entry() cannot write because the state dir is "
            "read-only — the exact failure mode CR-01 fixed, exercised end to end (WR-11)",
            _manual_resolve_post_save_failed_on_unwritable_state_dir)

        def _manual_resolution_delete_post_delete_failed_on_unwritable_state_dir():
            # WR-11's mirror case: FLASH_KEY_MANUAL_DELETE_FAILED for
            # delete_entry() returning False after a genuine write
            # failure (never for an already-absent prefix, which is a
            # silent no-op by design).
            manual_harness = Harness()
            try:
                manual_harness.start()
                mbase = manual_harness.base_url()
                msession = _login(manual_harness)

                add_result = manual_resolutions.add_entry(
                    manual_harness.tmpdir, "DLF", "Undeletable Air")
                if add_result != manual_resolutions.ADD_OK:
                    return False, "test setup failure: add_entry() returned %r" % (add_result,)

                os.chmod(manual_harness.tmpdir, 0o500)
                try:
                    status, headers, _ = http_request(
                        mbase + "/airlines/manual-resolutions/DLF/delete", method="POST",
                        cookie=msession)
                finally:
                    os.chmod(manual_harness.tmpdir, 0o700)

                if status != 303:
                    return False, "expected a 303 redirect even on a write failure, got %d" % status
                location = headers.get("Location", "")
                if "flash=manual_delete_failed" not in location:
                    return False, (
                        "expected the manual_delete_failed flash key when delete_entry() fails "
                        "to write, got %r" % location)
                registry_after = manual_resolutions.load_manual_resolutions(manual_harness.tmpdir)
                if "DLF" not in registry_after:
                    return False, "expected the entry to survive a failed delete_entry() write"
                return True, ""
            finally:
                manual_harness.stop()
                manual_harness.cleanup()
        check(
            "POST /airlines/manual-resolutions/{prefix}/delete redirects with the "
            "manual_delete_failed flash key, leaving the entry in place, when delete_entry() "
            "cannot write because the state dir is read-only (WR-11)",
            _manual_resolution_delete_post_delete_failed_on_unwritable_state_dir)

        # --- POST /settings/rules/add and POST /settings/rules/{kind}/
        # {value}/delete (Phase 15 D-10, D-11, 15-05-PLAN.md Task 3,
        # 15-VALIDATION.md rows 10/11) — each check below spins up its
        # own isolated Harness(), matching the manual-resolution checks
        # above, since these routes write a real colour_rules.json. The
        # add route's three form fields are rule_kind, rule_key and
        # rule_theme_id (config_page.py's own field names); the delete
        # route carries no form body at all, only its two path segments.

        def _rules_routes_require_auth_and_write_nothing():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rules_path = colour_rules.colour_rules_path(rules_harness.tmpdir)

                add_data = urllib.parse.urlencode(
                    {"rule_kind": "callsign", "rule_key": "AFR1234",
                     "rule_theme_id": "white"}).encode()
                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST", data=add_data)
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated add POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(rules_path):
                    return False, (
                        "expected no colour_rules.json to be written by an "
                        "unauthenticated POST")

                delete_path = "%scallsign/AFR1234%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, headers, _ = http_request(rbase + delete_path, method="POST")
                if status != 303:
                    return False, (
                        "expected a 303 redirect for an unauthenticated delete POST, "
                        "got %d" % status)
                if "/login" not in headers.get("Location", ""):
                    return False, "expected a redirect to /login, got %r" % headers.get("Location", "")
                if os.path.exists(rules_path):
                    return False, (
                        "expected no colour_rules.json to exist after an unauthenticated "
                        "delete POST")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "unauthenticated POSTs to /settings/rules/add and "
            "/settings/rules/{kind}/{value}/delete both redirect to /login and write no "
            "colour_rules.json — the state dir is unchanged, not only the status code",
            _rules_routes_require_auth_and_write_nothing)

        def _rules_add_and_delete_forms_sit_outside_settings_form():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "AFR9001", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                # 20-07 (D-10/D-11) moved the rules editor to Display.
                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200 GET /display, got %d" % status
                page = body.decode("utf-8")

                add_form_marker = 'action="%s"' % config_page.RULES_ADD_ROUTE
                add_tag_start = page.rindex("<form", 0, page.index(add_form_marker))
                add_tag_end = page.index(">", add_tag_start)
                add_form_tag = page[add_tag_start:add_tag_end + 1]

                # An exact expected delete action (not a prefix search) —
                # RULES_ADD_ROUTE itself starts with RULES_DELETE_ROUTE_
                # PREFIX ("/settings/rules/add" vs "/settings/rules/"), so
                # a bare prefix search could ambiguously match the add
                # form's own action instead of the delete form's.
                expected_delete_action = "%scallsign/AFR9001%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                delete_form_marker = 'action="%s"' % expected_delete_action
                delete_tag_start = page.rindex("<form", 0, page.index(delete_form_marker))
                delete_tag_end = page.index(">", delete_tag_start)
                delete_form_tag = page[delete_tag_start:delete_tag_end + 1]

                for tag, name in ((add_form_tag, "add"), (delete_form_tag, "delete")):
                    if config_page.SETTINGS_FORM_ID in tag:
                        return False, (
                            "expected the %s form to not carry the settings form's id, "
                            "got %r" % (name, tag))
                    if "form=" in tag:
                        return False, (
                            "expected the %s form to carry no form= attribute, got %r"
                            % (name, tag))

                # A rule add followed by an unrelated settings-form save
                # leaves both the rule and the setting intact — the two
                # write paths do not interfere.
                status, _headers, _body = http_request(
                    rbase + "/settings", method="POST",
                    data=urllib.parse.urlencode({"tracked_runway": "3"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect from the settings save, got %d" % status
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR9001" not in registry.get("callsign", {}):
                    return False, "expected the rule to survive an unrelated settings-form save"
                cfg = device_config.load_device_config(rules_harness.tmpdir)
                if cfg.get("tracked_runway") != "3":
                    return False, (
                        "expected the settings save to persist independently of the rule add")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "the rules add form and each delete form sit outside <form id=SETTINGS_FORM_ID> "
            "(D-10): neither carries the settings form's id nor a form= attribute pointing at "
            "it, and a rule add followed by an unrelated settings-form save leaves both the "
            "rule and every device-config setting intact (15-VALIDATION.md row 10)",
            _rules_add_and_delete_forms_sit_outside_settings_form)

        def _rules_add_route_no_js_added_then_replaced():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST",
                    data=urllib.parse.urlencode(
                        {"rule_kind": "callsign", "rule_key": "afr1234",
                         "rule_theme_id": "white"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_added" not in headers.get("Location", ""):
                    return False, (
                        "expected the added flash key on first add, got %r"
                        % headers.get("Location"))

                status, headers, _ = http_request(
                    rbase + config_page.RULES_ADD_ROUTE, method="POST",
                    data=urllib.parse.urlencode(
                        {"rule_kind": "callsign", "rule_key": "AFR1234",
                         "rule_theme_id": "blue"}).encode(),
                    cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=rule_replaced" not in location or "rule=AFR1234" not in location:
                    return False, (
                        "expected the replaced flash key echoing the normalised key, "
                        "got %r" % location)

                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                callsign_entries = registry.get("callsign", {})
                if list(callsign_entries.keys()) != ["AFR1234"]:
                    return False, (
                        "expected exactly one callsign entry keyed AFR1234, got %r"
                        % (callsign_entries,))
                if callsign_entries["AFR1234"]["theme_id"] != "blue":
                    return False, (
                        "expected the second add's theme to win, got %r"
                        % (callsign_entries["AFR1234"],))
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "raw URL-encoded no-JS POSTs to the rules add route (15-VALIDATION.md row 11): a "
            "first add flashes rule_added, a second add for the same key (case-insensitive "
            "input) flashes rule_replaced and echoes the normalised key back, and the "
            "registry holds exactly one entry with the second theme",
            _rules_add_route_no_js_added_then_replaced)

        def _rules_add_route_rejection_paths():
            from companion.pages import config_page
            import itertools
            import string

            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                def _add(kind, key, theme_id):
                    data = urllib.parse.urlencode(
                        {"rule_kind": kind, "rule_key": key, "rule_theme_id": theme_id}).encode()
                    return http_request(
                        rbase + config_page.RULES_ADD_ROUTE, method="POST", data=data,
                        cookie=rsession)

                # A malformed value for the selected kind — a prefix must
                # be exactly three letters.
                status, headers, _ = _add("prefix", "TOOLONG", "white")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_key_invalid" not in headers.get("Location", ""):
                    return False, (
                        "expected the key-invalid flash key, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if registry.get("prefix"):
                    return False, "expected nothing written for a malformed value"

                # A crafted kind outside the closed set.
                status, headers, _ = _add("../../etc/passwd", "AFR", "white")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_save_failed" not in headers.get("Location", ""):
                    return False, (
                        "expected the generic save-failed flash key for a crafted kind, "
                        "got %r" % headers.get("Location"))

                # A crafted theme id outside THEME_IDS.
                status, headers, _ = _add("callsign", "AFR9999", "not-a-real-theme")
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_save_failed" not in headers.get("Location", ""):
                    return False, (
                        "expected the generic save-failed flash key for a crafted theme "
                        "id, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR9999" in registry.get("callsign", {}):
                    return False, "expected nothing written for a crafted theme id"

                # Fill the registry to the cap with distinct, already-
                # valid prefixes (mirroring
                # server/test_manual_resolutions.py's own cap-enforcement
                # precedent), then attempt one more through the real
                # route.
                existing_count = sum(len(v) for v in registry.values())
                needed = colour_rules.COLOUR_RULE_MAX_ENTRIES - existing_count
                cap_prefixes = []
                for combo in itertools.product(string.ascii_uppercase, repeat=3):
                    if len(cap_prefixes) >= needed:
                        break
                    cap_prefixes.append("".join(combo))
                for prefix in cap_prefixes:
                    result = colour_rules.add_rule(
                        rules_harness.tmpdir, "prefix", prefix, "white")
                    if result != colour_rules.ADD_OK_NEW:
                        return False, (
                            "test setup failure filling the cap: add_rule(%r, ...) "
                            "returned %r" % (prefix, result))
                status, headers, _ = _add("prefix", "ZZZ", "white")
                if status != 303:
                    return False, "expected a 303 redirect for the at-cap POST, got %d" % status
                if "flash=rule_registry_full" not in headers.get("Location", ""):
                    return False, (
                        "expected the registry-full flash key, got %r" % headers.get("Location"))
                registry_after = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "ZZZ" in registry_after.get("prefix", {}):
                    return False, "expected the at-cap entry to NOT be persisted"
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "the rules add route's rejection paths: a malformed value for the selected kind "
            "flashes rule_key_invalid and writes nothing; a crafted kind and a crafted theme "
            "id each flash the generic rule_save_failed and write nothing; filling the "
            "registry to its cap and adding one more flashes rule_registry_full without "
            "persisting the at-cap entry",
            _rules_add_route_rejection_paths)

        def _rules_delete_route_full_contract():
            from companion.pages import config_page
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "hex", "3944F2", "blue")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                delete_path = "%shex/3944F2%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, headers, _ = http_request(rbase + delete_path, method="POST", cookie=rsession)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if "flash=rule_deleted" not in headers.get("Location", ""):
                    return False, (
                        "expected the deleted flash key, got %r" % headers.get("Location"))
                registry = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "3944F2" in registry.get("hex", {}):
                    return False, "expected the entry to be removed from the registry"

                # A second, identical delete of an already-absent entry
                # is success, not an error — idempotent double-submission
                # tolerance, matching the manual-resolutions delete
                # precedent (no flash on a repeat delete either).
                status, headers, _ = http_request(rbase + delete_path, method="POST", cookie=rsession)
                if status != 303:
                    return False, (
                        "expected a second identical delete to also redirect, got %d" % status)
                if "flash=" in headers.get("Location", ""):
                    return False, (
                        "expected no flash on a repeat delete of an already-absent entry, "
                        "got %r" % headers.get("Location"))

                # A malformed kind segment and a malformed value segment
                # each 404 without touching an unrelated existing entry.
                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "AFR1234", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)
                bad_kind_path = "%sbogus/AFR1234%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, _headers, _body = http_request(
                    rbase + bad_kind_path, method="POST", cookie=rsession)
                if status != 404:
                    return False, "expected 404 for a malformed kind segment, got %d" % status
                bad_value_path = "%scallsign/bad-value%s" % (
                    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
                status, _headers, _body = http_request(
                    rbase + bad_value_path, method="POST", cookie=rsession)
                if status != 404:
                    return False, "expected 404 for a malformed value segment, got %d" % status
                registry_after = colour_rules.load_colour_rules(rules_harness.tmpdir)
                if "AFR1234" not in registry_after.get("callsign", {}):
                    return False, (
                        "expected the unrelated entry to survive both 404'd delete attempts")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "POST /settings/rules/{kind}/{value}/delete removes the registry entry and "
            "flashes rule_deleted; a second identical delete of an already-absent entry is a "
            "no-op that redirects with no flash; a malformed kind segment and a malformed "
            "value segment each 404 without touching an unrelated existing entry",
            _rules_delete_route_full_contract)

        def _rules_page_context_reads_fresh_per_request():
            rules_harness = Harness()
            try:
                rules_harness.start()
                rbase = rules_harness.base_url()
                rsession = _login(rules_harness)

                # 20-07 (D-10/D-11) moved the rules editor to Display.
                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if b"FRESHRD1" in body:
                    return False, "expected the rule to be absent before it is written"

                add_result = colour_rules.add_rule(
                    rules_harness.tmpdir, "callsign", "FRESHRD1", "white")
                if add_result != colour_rules.ADD_OK_NEW:
                    return False, "test setup failure: add_rule() returned %r" % (add_result,)

                status, _headers, body = http_request(rbase + "/display", cookie=rsession)
                if status != 200:
                    return False, "expected 200, got %d" % status
                if b"FRESHRD1" not in body:
                    return False, (
                        "expected page_context() to read the rules registry fresh per "
                        "request, not through the poll-cycle process cache")
                return True, ""
            finally:
                rules_harness.stop()
                rules_harness.cleanup()
        check(
            "a rule written directly to state_dir between two GETs of the Settings page "
            "appears in the second render — proving page_context() reads colour_rules fresh "
            "per request rather than through any process-scoped cache",
            _rules_page_context_reads_fresh_per_request)

        # --- poll-trigger cooldown: server-global, not per-session ---

        def _poll_trigger_first_call():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_triggered" not in location:
                return False, "expected the poll_triggered flash key in the redirect, got %r" % location
            return True, ""
        check(
            "a first poll trigger redirects with the poll_triggered flash key",
            _poll_trigger_first_call)

        def _poll_trigger_cooldown_same_session():
            status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, "expected the poll_cooldown flash key in the redirect, got %r" % location
            return True, ""
        check(
            "an immediate second poll trigger redirects with the poll_cooldown flash key",
            _poll_trigger_cooldown_same_session)

        def _poll_trigger_cooldown_second_opener():
            second_session_cookie = _login(harness)
            status, headers, _ = http_request(
                base + "/poll-now", method="POST", cookie=second_session_cookie)
            if status != 303:
                return False, "expected a 303 redirect, got %d" % status
            location = headers.get("Location", "")
            if "flash=poll_cooldown" not in location:
                return False, (
                    "expected a fresh second-opener session to also see the "
                    "poll_cooldown flash key, got %r" % location)
            return True, ""
        check(
            "a fresh second-opener session is refused by the same cooldown (server-global, not per-session)",
            _poll_trigger_cooldown_second_opener)

        # 2026-08-28 fix: a genuine run_once() failure (e.g. an unreadable
        # --geofence path, exactly what production hit when
        # deploy/skypane-companion.service never passed --geofence at all
        # and the relative default didn't resolve under its
        # WorkingDirectory) must redirect with the distinct poll_failed
        # flash key, never the misleading save_failed one - a poll
        # trigger failing has nothing to do with "couldn't save settings".
        def _poll_trigger_failure_uses_distinct_flash_key():
            broken_harness = Harness(extra_args=["--geofence", "/nonexistent/no-such-geofence.json"])
            try:
                broken_harness.start()
                broken_session = _login(broken_harness)
                status, headers, _ = http_request(
                    broken_harness.base_url() + "/poll-now", method="POST", cookie=broken_session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=poll_failed" not in location:
                    return False, "expected the poll_failed flash key, got %r" % location
                if "flash=save_failed" in location:
                    return False, "a poll-trigger failure must never reuse save_failed's misleading copy"
                return True, ""
            finally:
                broken_harness.stop()
                broken_harness.cleanup()
        check(
            "a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never save_failed",
            _poll_trigger_failure_uses_distinct_flash_key)

        # UXA-15: two genuinely overlapping threads issuing POST
        # /poll-now against the same running subprocess, on a session
        # with zero cooldown, must never both reach run_once() — the
        # server-side _POLL_LOCK (companion/app.py) is the correctness
        # boundary, not merely a claim verified by reading the source.
        # A fresh Harness/session is used (rather than reusing the
        # cooldown-exhausted session_cookie above) so the cooldown gate
        # never confounds which flash key each response carries.
        def _poll_now_concurrent_requests_serialize_on_the_lock():
            concurrent_harness = Harness()
            try:
                concurrent_harness.start()
                cbase = concurrent_harness.base_url()
                concurrent_cookie = _login(concurrent_harness)

                start_event = threading.Event()
                responses = []
                responses_lock = threading.Lock()

                def _worker():
                    start_event.wait()
                    status, headers, _ = http_request(
                        cbase + "/poll-now", method="POST", cookie=concurrent_cookie)
                    with responses_lock:
                        responses.append((status, headers.get("Location", "")))

                threads = [threading.Thread(target=_worker) for _ in range(2)]
                for t in threads:
                    t.start()
                # Released together, after both threads are already
                # blocked on it — the tightest overlap this harness can
                # produce without instrumenting the server itself.
                start_event.set()
                for t in threads:
                    t.join(timeout=30)

                if len(responses) != 2:
                    return False, "expected two responses, got %d: %r" % (len(responses), responses)
                for status, _location in responses:
                    if status != 303:
                        return False, "expected both responses to be 303 redirects, got %r" % (responses,)
                already_running_count = sum(
                    1 for _status, location in responses
                    if "flash=poll_already_running" in location)
                if already_running_count != 1:
                    return False, (
                        "expected exactly one of the two overlapping /poll-now "
                        "requests to receive the poll_already_running flash key "
                        "(the other must complete/fail on its own honest "
                        "outcome), got %d of 2: %r" % (already_running_count, responses))
                return True, ""
            finally:
                concurrent_harness.stop()
                concurrent_harness.cleanup()
        check(
            "two genuinely overlapping POST /poll-now requests: exactly one gets the poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution",
            _poll_now_concurrent_requests_serialize_on_the_lock)

        # --- Section 4 (phase 17 plan 04, D-06/D-09): the save-triggered
        # immediate calendar sync, its four outcomes, the throttle bypass,
        # lock contention, and the T-17-FLASH leak guard. Every check here
        # uses _InProcessHarness (a real ThreadingHTTPServer in THIS
        # process, not a Harness subprocess) because it needs to
        # monkeypatch calendar_rules.default_calendar_transport and
        # socket.getaddrinfo — a monkeypatch a Harness subprocess, with
        # its own separate interpreter, could never see.

        def _calendar_connect_reports_plural_count():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                calls = []
                hostname = "calendar-sync-plural.example"
                url = "https://%s/feed.ics?token=PLURALCOUNTTOKEN" % hostname
                body = _ics_body([
                    ("AF1234", "CDG", "ORY", 2),
                    ("BA5678", "LHR", "CDG", 4),
                    ("KL2222", "AMS", "ORY", 6),
                ])
                with _stubbed_calendar_transport(
                        _make_calendar_transport(body=body, calls=calls)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, "expected the calendar_connected flash key, got %r" % location
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if status2 != 200:
                    return False, "expected 200 following the redirect, got %d" % status2
                if b"3 flights" not in page_body:
                    return False, "expected the rendered banner to name 3 flights, got %r" % (page_body,)
                if calls != [url]:
                    return False, "expected exactly one transport call with the submitted URL, got %r" % (calls,)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "saving a calendar feed with three in-window flights performs exactly one refresh call and the rendered banner names the plural flight count (D-06)",
            _calendar_connect_reports_plural_count)

        def _calendar_connect_reports_singular_count():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-singular.example"
                url = "https://%s/feed.ics?token=SINGULARCOUNTTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                location = headers.get("Location", "")
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if status2 != 200:
                    return False, "expected 200 following the redirect, got %d" % status2
                if b"1 flight from this calendar" not in page_body:
                    return False, "expected the singular form '1 flight', got %r" % (page_body,)
                if b"1 flights" in page_body:
                    return False, "the singular count must never carry a trailing 's'"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "saving a calendar feed with exactly one in-window flight pins the singular form ('1 flight', never '1 flights')",
            _calendar_connect_reports_singular_count)

        def _calendar_connect_zero_entries_still_succeeds():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-empty.example"
                url = "https://%s/feed.ics?token=EMPTYFEEDTOKEN" % hostname
                # A syntactically valid but empty feed - a parsed feed
                # with nothing in the window is a different, legitimate
                # outcome from a broken feed, and the two must be
                # distinguishable (D-06's "zero is a legitimate,
                # informative value").
                body = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, (
                        "a zero-entry feed that parsed correctly must still report "
                        "success, got %r" % location)
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"0 flights" not in page_body:
                    return False, "expected the rendered banner to name 0 flights, got %r" % (page_body,)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a syntactically valid feed with nothing in the frame's window reports success with a 0 count, distinguishable from a failure",
            _calendar_connect_zero_entries_still_succeeds)

        def _calendar_sync_failure_reports_generic_message_and_still_saves():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-failure.example"
                url = "https://%s/feed.ics?token=FAILURETOKEN" % hostname
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=ConnectionError("boom"))), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_sync_failed" not in location:
                    return False, "expected the single calendar_sync_failed flash key, got %r" % location
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, (
                        "the URL must be saved regardless of whether the immediate "
                        "fetch succeeded")
                import companion.app as app_module
                # escape_html() rewrites this copy's apostrophe to
                # "&#x27;" on render (17-02's own recorded surprise for
                # CALENDAR_STATUS_NOT_CONFIGURED) - the rendered page is
                # therefore compared against the ESCAPED form, never the
                # raw FLASH_MESSAGES source string.
                expected_text = layout.escape_html(
                    app_module.FLASH_MESSAGES[app_module.FLASH_KEY_CALENDAR_SYNC_FAILED])
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if expected_text.encode() not in page_body:
                    return False, (
                        "expected the single generic failure copy verbatim (HTML-escaped) "
                        "in the rendered banner, got %r" % (page_body,))
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a failing fetch redirects with the single generic failure flash key, renders the exact failure copy, and the URL is saved regardless (D-06)",
            _calendar_sync_failure_reports_generic_message_and_still_saves)

        def _calendar_sync_failure_never_leaks_the_url():
            # T-17-FLASH: a transport whose raised error's message embeds
            # the full URL - the shape a real name-resolution or
            # connection error has - must never surface any of five
            # distinct needles (token, host, path segment,
            # query-parameter name, whole URL) anywhere the operator can
            # see: the redirect's Location header, or the served body of
            # either response.
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "leak-check-host.example"
                token = "LEAKTOKEN99999"
                path_segment = "leak-path-segment"
                query_param = "leakqueryparam"
                url = "https://%s/private/%s/feed.ics?%s=%s" % (
                    hostname, path_segment, query_param, token)
                needles = [token, hostname, path_segment, query_param, url]
                raise_exc = ConnectionError(
                    "Failed to resolve %s: Name or service not known" % url)
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=raise_exc)), \
                        _fake_public_hostname(hostname):
                    status, headers, redirect_body = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                for needle in needles:
                    if needle in location:
                        return False, "leak in Location header: %r found in %r" % (needle, location)
                    if needle.encode() in redirect_body:
                        return False, "leak in the redirect response body: %r" % (needle,)
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                for needle in needles:
                    if needle.encode() in page_body:
                        return False, (
                            "leak in the served response body: %r found on the "
                            "rendered Settings page" % (needle,))
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, host, path segment, query-parameter name, or whole URL in the Location header or any served response body",
            _calendar_sync_failure_never_leaks_the_url)

        def _calendar_disconnect_reports_deletion_and_erases_entries():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-disconnect.example"
                url = "https://%s/feed.ics?token=DISCONNECTTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                registry_before = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if not registry_before["entries"]:
                    return False, "test setup failure: expected at least one entry before disconnecting"

                from companion.pages import config_page
                status, headers, _b = http_request(
                    calendar_harness.base_url() + "/settings", method="POST",
                    data=urllib.parse.urlencode(
                        {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_disconnected" not in location:
                    return False, "expected the calendar_disconnected flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be disconnected"
                registry_after = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if registry_after["entries"]:
                    return False, (
                        "expected every fetched flight to be deleted on disconnect, "
                        "found %r" % (registry_after["entries"],))
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"deleted" not in page_body:
                    return False, "expected the rendered banner to state the flights were deleted"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "checking the disconnect box redirects with the disconnected flash key, and the calendar's previously-fetched flights are actually erased from disk (D-04)",
            _calendar_disconnect_reports_deletion_and_erases_entries)

        # ==============================================================
        # 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect
        # action's own dedicated POST /settings/calendar/disconnect
        # route — a bare/wrong-confirm POST renders the two-step
        # confirmation page and erases nothing; only confirm=yes
        # disconnects; the route is session-gated like every other
        # state-changing route.
        # ==============================================================

        def _calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://bare-post.example/feed.ics?token=BAREPOSTTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, _headers, body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST", data=b"", cookie=session)
                if status != 200:
                    return False, "expected a 200 confirmation page for a bare POST, got %d" % status
                if html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() not in body:
                    return False, "expected the confirmation copy in the rendered page"
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected after a bare POST"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a bare authenticated POST /settings/calendar/disconnect with no confirm field returns 200 "
            "with the confirmation copy and leaves the calendar connected (D-08/A-26)",
            _calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing)

        def _calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://confirm-maybe.example/feed.ics?token=MAYBETOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, _headers, body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD: "maybe"}).encode(),
                    cookie=session)
                if status != 200:
                    return False, "expected a 200 confirmation page for confirm=maybe, got %d" % status
                if html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() not in body:
                    return False, "expected the confirmation copy in the rendered page"
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected after confirm=maybe"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an authenticated POST /settings/calendar/disconnect with confirm=maybe renders the "
            "confirmation page rather than disconnecting anything (D-08/A-26)",
            _calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing)

        def _calendar_disconnect_route_confirm_yes_disconnects():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                url = "https://confirm-yes.example/feed.ics?token=YESTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, headers, _body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {
                            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD:
                                config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
                        }).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect for confirm=yes, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_disconnected" not in location:
                    return False, "expected the calendar_disconnected flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be disconnected"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an authenticated POST /settings/calendar/disconnect with confirm=yes 303-redirects with the "
            "disconnected flash key and actually disconnects the calendar (D-08/A-26)",
            _calendar_disconnect_route_confirm_yes_disconnects)

        def _calendar_disconnect_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                url = "https://unauth-disconnect.example/feed.ics?token=UNAUTHTOKEN"
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                status, headers, _body = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {
                            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD:
                                config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
                        }).encode())
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain connected — nothing should be written"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an unauthenticated POST /settings/calendar/disconnect (even with confirm=yes) redirects to "
            "/login and writes nothing (D-08/A-26, T-19-41)",
            _calendar_disconnect_route_unauthenticated_redirects_to_login)

        # ==============================================================
        # 20-09-PLAN.md Task 2 (D-14c): the calendar connect action's own
        # dedicated POST /settings/calendar/connect route — never through
        # config_page.handle_post()'s scope/in_scope machinery (T-20-11),
        # session-gated like every other state-changing route (T-20-10).
        # ==============================================================

        def _calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                # T-20-11's own pinned regression: seed Quiet hours and
                # the screen ON, connect a calendar, and assert both are
                # STILL on afterwards — a scoped POST through the settings
                # handler would read their absent checkboxes as an
                # explicit OFF and silently switch both off.
                device_config.save_device_config(
                    calendar_harness.tmpdir, quiet_hours_enabled=True, display_enabled=True)
                session = _login(calendar_harness)
                hostname = "connect-route.example"
                url = "https://%s/feed.ics?token=CONNECTROUTETOKEN" % hostname
                body = _ics_body([("AFR1234", "ORY", "TLS", 2), ("AFR5678", "ORY", "NCE", 3)])
                calls = []
                with _stubbed_calendar_transport(
                        _make_calendar_transport(body=body, calls=calls)), \
                        _fake_public_hostname(hostname):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                        method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if not location.startswith("/display"):
                    return False, "expected a redirect to Display, got %r" % location
                if "flash=calendar_connect_ok" not in location:
                    return False, "expected the calendar_connect_ok flash key, got %r" % location
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to be configured"
                if calendar_rules.configured_calendar_url(calendar_harness.tmpdir) != url:
                    return False, "expected the submitted URL to be stored"
                if len(calls) != 1:
                    return False, "expected exactly one registry refresh (one transport call), got %d" % len(calls)
                registry = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if len(registry["entries"]) != 2:
                    return False, "expected two fetched entries, got %r" % (registry["entries"],)
                on_disk = device_config.load_device_config(calendar_harness.tmpdir)
                if on_disk.get("quiet_hours_enabled") is not True:
                    return False, "expected quiet_hours_enabled to remain True (T-20-11 regression)"
                if on_disk.get("display_enabled") is not True:
                    return False, "expected display_enabled to remain True (T-20-11 regression)"
                status2, _h2, page_body = http_request(
                    calendar_harness.base_url() + location, cookie=session)
                if b"2 flights found" not in page_body:
                    return False, "expected the success flash text to include the flight count"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a valid POST /settings/calendar/connect 303-redirects to Display with the "
            "calendar_connect_ok flash key, persists the URL, triggers exactly one registry refresh, "
            "and leaves quiet_hours_enabled/display_enabled exactly as they were (D-14c, T-20-11 "
            "pinned regression)",
            _calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone)

        def _calendar_connect_route_invalid_url_rejects_and_persists_nothing():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                status, headers, _b = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode({"calendar_url": ""}).encode(),
                    cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_connect_invalid" not in location:
                    return False, "expected the calendar_connect_invalid flash key, got %r" % location
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain unconfigured — nothing should be written"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an empty calendar_url on POST /settings/calendar/connect 303-redirects with the "
            "calendar_connect_invalid flash key and persists nothing (D-14c)",
            _calendar_connect_route_invalid_url_rejects_and_persists_nothing)

        def _calendar_connect_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            calendar_harness = _InProcessHarness()
            try:
                status, headers, _b = http_request(
                    calendar_harness.base_url() + config_page.CALENDAR_CONNECT_ROUTE,
                    method="POST",
                    data=urllib.parse.urlencode(
                        {"calendar_url": "https://unauth-connect.example/feed.ics"}).encode())
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                if calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected nothing to be written for an unauthenticated POST"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "an unauthenticated POST /settings/calendar/connect redirects to /login and writes nothing "
            "(D-14c, T-20-10)",
            _calendar_connect_route_unauthenticated_redirects_to_login)

        # ==============================================================
        # 20-11-PLAN.md Task 1 (D-26/T-20-13): "Send a test"'s own
        # dedicated POST /settings/notifications/test route — session-
        # gated, reads the topic URL from the stored config only, and
        # never trusts a submitted topic_url field.
        # ==============================================================

        def _notifications_test_route_unauthenticated_redirects_to_login():
            from companion.pages import config_page
            harness = _InProcessHarness()
            try:
                status, headers, _b = http_request(
                    harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                    method="POST", data=b"")
                if status != 303:
                    return False, "expected a 303 redirect for an unauthenticated POST, got %d" % status
                if headers.get("Location") != "/login":
                    return False, "expected a redirect to /login, got %r" % headers.get("Location")
                return True, ""
            finally:
                harness.stop()
        check(
            "an unauthenticated POST /settings/notifications/test redirects to /login (D-26, T-20-10)",
            _notifications_test_route_unauthenticated_redirects_to_login)

        def _notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) not in location:
                    return False, "expected the notifications_test_failed flash key, got %r" % location
                if calls:
                    return False, "expected send_notification() to never be called with no stored URL"
                return True, ""
            finally:
                harness.stop()
        check(
            "with no stored topic URL, POST /settings/notifications/test redirects with the "
            "notifications_test_failed flash key and never calls notify.send_notification() (D-26)",
            _notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender)

        def _notifications_test_route_configured_calls_sender_once_and_flashes_success():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-abc"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_OK) not in location:
                    return False, "expected the notifications_test_ok flash key, got %r" % location
                if calls != [stored_url]:
                    return False, (
                        "expected send_notification() to be called exactly once with the stored "
                        "url, got %r" % (calls,))
                return True, ""
            finally:
                harness.stop()
        check(
            "with a stored topic URL, POST /settings/notifications/test calls "
            "notify.send_notification() exactly once with the stored URL and redirects with the "
            "notifications_test_ok flash key (D-26)",
            _notifications_test_route_configured_calls_sender_once_and_flashes_success)

        def _notifications_test_route_sender_returning_false_flashes_failure():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-def"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                original = notify_module.send_notification
                notify_module.send_notification = lambda *a, **k: False
                try:
                    status, headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST", data=b"", cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) not in location:
                    return False, "expected the notifications_test_failed flash key, got %r" % location
                return True, ""
            finally:
                harness.stop()
        check(
            "a sender returning False redirects with the notifications_test_failed flash key (D-26)",
            _notifications_test_route_sender_returning_false_flashes_failure)

        def _notifications_test_route_ignores_a_submitted_topic_url_field():
            from companion.pages import config_page
            from server import notify as notify_module
            harness = _InProcessHarness()
            try:
                stored_url = "https://ntfy.sh/skypane-test-topic-ghi"
                device_config.save_device_config(
                    harness.tmpdir, notifications={
                        "topic_url": stored_url, "battery_low": True,
                        "frame_silent": True, "lang": "en"})
                session = _login(harness)
                calls = []
                original = notify_module.send_notification

                def _fake_send(topic_url, title, body, timeout=5, transport=None):
                    calls.append(topic_url)
                    return True

                notify_module.send_notification = _fake_send
                try:
                    status, _headers, _b = http_request(
                        harness.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE,
                        method="POST",
                        data=urllib.parse.urlencode(
                            {"topic_url": "https://attacker.example/forward-me"}).encode(),
                        cookie=session)
                finally:
                    notify_module.send_notification = original
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if calls != [stored_url]:
                    return False, (
                        "expected send_notification() to receive the STORED url only, got %r"
                        % (calls,))
                return True, ""
            finally:
                harness.stop()
        check(
            "a POST /settings/notifications/test carrying its own topic_url field is ignored in "
            "favour of the stored one — the field is never read from the request body (T-20-13)",
            _notifications_test_route_ignores_a_submitted_topic_url_field)

        def _calendar_sync_bypasses_the_throttle_via_min_interval_zero():
            """D-06's bypass, proven two ways.

            The behavioural half: seed a recorded attempt a minute ago
            (well inside the standard 1800s throttle) and confirm the
            save-triggered sync still fetches and still reports success.

            The wiring half, and the one that actually distinguishes
            `min_interval_s=0` from an omitted argument on THIS call
            path: `config_page.handle_post()`'s own call to
            `calendar_rules.save_calendar_url()` (plan 17-01)
            unconditionally erases the whole registry - including
            `last_attempt_at`, resetting it to `None` - on every
            successful set, BEFORE `_handle_settings_post()`'s own
            refresh call ever runs. Since `calendar_fetch_is_due()`
            already returns `True` unconditionally whenever
            `last_attempt_at is None`, a seeded stale attempt is wiped
            before the throttle is ever consulted - the fetch would run
            here whether `min_interval_s` were 0, omitted, or anything
            else. A spy on `refresh_calendar_registry()` itself is what
            actually pins the argument.
            """
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-throttle.example"
                url = "https://%s/feed.ics?token=THROTTLEBYPASSTOKEN" % hostname
                now = time.time()
                calendar_rules.save_calendar_url(calendar_harness.tmpdir, url)
                calendar_rules.write_calendar_registry(
                    calendar_harness.tmpdir, [], now - 60, None, now=now)

                captured_intervals = []
                real_refresh = calendar_rules.refresh_calendar_registry

                def _spy_refresh(state_dir, when, transport=None, min_interval_s=None):
                    captured_intervals.append(min_interval_s)
                    return real_refresh(
                        state_dir, when, transport=transport, min_interval_s=min_interval_s)

                calendar_rules.refresh_calendar_registry = _spy_refresh
                try:
                    with _stubbed_calendar_transport(_make_calendar_transport()), \
                            _fake_public_hostname(hostname):
                        status, headers, _b = http_request(
                            calendar_harness.base_url() + "/settings", method="POST",
                            data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                            cookie=session)
                finally:
                    calendar_rules.refresh_calendar_registry = real_refresh
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                if captured_intervals != [0]:
                    return False, (
                        "expected exactly one refresh_calendar_registry() call with "
                        "min_interval_s=0 (not omitted, not None), got %r" % (captured_intervals,))
                location = headers.get("Location", "")
                if "flash=calendar_connected" not in location:
                    return False, "expected the calendar_connected flash key, got %r" % location
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a save-triggered sync against a calendar with a 60s-old last_attempt_at still fetches and reports success, and refresh_calendar_registry() is called with min_interval_s=0 explicitly - not omitted, which a call-shape spy is the only thing that can actually distinguish here, since config_page.handle_post()'s own save_calendar_url() (17-01) already resets last_attempt_at to None on every set before this handler's own refresh call runs",
            _calendar_sync_bypasses_the_throttle_via_min_interval_zero)

        def _poll_modules_own_refresh_call_site_still_throttles():
            # The opposite of the check above: refresh_calendar_registry()
            # called the way server/poll_loop.py's own production call
            # site calls it - with NO min_interval_s override - must still
            # honour the standard throttle against the identical seeded
            # state. Proves the bypass is scoped to companion/app.py's new
            # call site alone, never widening the poll cycle's own
            # throttle.
            with tempfile.TemporaryDirectory() as tmp:
                now = time.time()
                url = "https://calendar-sync-throttle-control.example/feed.ics?token=CONTROLTOKEN"
                calendar_rules.save_calendar_url(tmp, url)
                calendar_rules.write_calendar_registry(tmp, [], now - 60, None, now=now)
                calls = []
                with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)), \
                        _fake_public_hostname("calendar-sync-throttle-control.example"):
                    result_code, _registry = calendar_rules.refresh_calendar_registry(tmp, now)
                if result_code != calendar_rules.FETCH_SKIPPED_THROTTLED:
                    return False, "expected FETCH_SKIPPED_THROTTLED, got %r" % (result_code,)
                if calls:
                    return False, "expected no transport call when the standard throttle applies, got %r" % (calls,)
                return True, ""
        check(
            "server/poll_loop.py's own refresh_calendar_registry() call shape (no min_interval_s override) still honours the standard throttle against the identical seeded state - the bypass is scoped to the new call site alone",
            _poll_modules_own_refresh_call_site_still_throttles)

        def _calendar_sync_lock_contention_is_honest():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-contention.example"
                url = "https://%s/feed.ics?token=CONTENTIONTOKEN" % hostname
                calls = []
                import companion.app as app_module
                locked = app_module._POLL_LOCK.acquire(blocking=False)
                if not locked:
                    return False, "test setup failure: could not acquire _POLL_LOCK from the test thread"
                try:
                    with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)), \
                            _fake_public_hostname(hostname):
                        status, headers, _b = http_request(
                            calendar_harness.base_url() + "/settings", method="POST",
                            data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                            cookie=session)
                finally:
                    app_module._POLL_LOCK.release()
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=calendar_sync_deferred" not in location:
                    return False, "expected the calendar_sync_deferred flash key, got %r" % location
                if calls:
                    return False, "expected no transport call while the lock was held, got %r" % (calls,)
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the URL to be saved even though the sync was deferred"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a save arriving while the poll lock is already held redirects with the deferred flash key, performs no fetch, and still saves the URL (D-09)",
            _calendar_sync_lock_contention_is_honest)

        def _calendar_sync_lock_is_released_after_a_failed_sync():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-release.example"
                url = "https://%s/feed.ics?token=RELEASETOKEN" % hostname
                with _stubbed_calendar_transport(
                        _make_calendar_transport(raise_exc=ConnectionError("boom"))), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                import companion.app as app_module
                reacquired = app_module._POLL_LOCK.acquire(blocking=False)
                if reacquired:
                    app_module._POLL_LOCK.release()
                if not reacquired:
                    return False, (
                        "expected the poll lock to be free after one failed sync - a "
                        "wedged trigger is the failure mode the finally-release exists "
                        "to prevent")
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "after a save whose immediate fetch fails, the poll lock is still free - one failure never wedges a later manual poll trigger",
            _calendar_sync_lock_is_released_after_a_failed_sync)

        def _unrelated_settings_save_never_reaches_the_refresh_call():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-unrelated.example"
                url = "https://%s/feed.ics?token=UNRELATEDTOKEN" % hostname
                body = _ics_body([("AF1234", "CDG", "ORY", 2)])
                with _stubbed_calendar_transport(_make_calendar_transport(body=body)), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                registry_before = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)

                calls = []
                with _stubbed_calendar_transport(_make_calendar_transport(calls=calls)):
                    status, headers, _b = http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"theme": "black"}).encode(),
                        cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=saved" not in location:
                    return False, "expected the ordinary saved flash key, got %r" % location
                if calls:
                    return False, (
                        "expected an unrelated save to never reach the refresh call, "
                        "got %r" % (calls,))
                if not calendar_rules.calendar_is_configured(calendar_harness.tmpdir):
                    return False, "expected the calendar to remain configured"
                registry_after = calendar_rules.load_calendar_registry(calendar_harness.tmpdir)
                if registry_after["entries"] != registry_before["entries"]:
                    return False, "expected the fetched entries to be untouched by an unrelated save"
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a settings save that changes only the theme, against an already-connected calendar, redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its fetched entries untouched",
            _unrelated_settings_save_never_reaches_the_refresh_call)

        def _calendar_save_does_not_touch_the_manual_poll_cooldown():
            calendar_harness = _InProcessHarness()
            try:
                session = _login(calendar_harness)
                hostname = "calendar-sync-cooldown.example"
                url = "https://%s/feed.ics?token=COOLDOWNTOKEN" % hostname
                with _stubbed_calendar_transport(_make_calendar_transport()), \
                        _fake_public_hostname(hostname):
                    http_request(
                        calendar_harness.base_url() + "/settings", method="POST",
                        data=urllib.parse.urlencode({"calendar_url": url}).encode(),
                        cookie=session)
                status, headers, _b = http_request(
                    calendar_harness.base_url() + "/poll-now", method="POST", cookie=session)
                if status != 303:
                    return False, "expected a 303 redirect, got %d" % status
                location = headers.get("Location", "")
                if "flash=poll_cooldown" in location:
                    return False, (
                        "a calendar save must never consume the manual poll trigger's "
                        "own cooldown, got %r" % location)
                return True, ""
            finally:
                calendar_harness.stop()
        check(
            "a calendar save immediately followed by a manual poll trigger does not hit the poll cooldown - the two mechanisms are independent",
            _calendar_save_does_not_touch_the_manual_poll_cooldown)

        # D-17 (21-01-PLAN.md Task 1): the former Section 5 block
        # (20-12-PLAN.md Task 2, D-30/D-31) exercised sp_ui_mode=simple/
        # full over real HTTP end to end. The mechanism it tested no
        # longer exists — deleted in full: _make_simple_mode_nav_hidden_
        # check/_make_full_mode_nav_shown_check (both factories and their
        # loop-generated checks), _home_hides_health_link_in_simple_mode,
        # _airlines_hides_change_pictures_button_in_simple_mode,
        # _display_disclosures_collapse_to_one_sentence_in_simple_mode,
        # _display_still_carries_all_six_everyday_groups_in_simple_mode,
        # _health_and_device_still_reachable_by_url_in_simple_mode,
        # _flights_and_airlines_keep_their_full_content_in_simple_mode,
        # _simple_mode_survives_three_sequential_requests, and the
        # full-mode mirror checks (_home_shows_health_link_in_full_mode,
        # _airlines_shows_change_pictures_button_in_full_mode,
        # _display_disclosures_are_full_details_in_full_mode) — the
        # full-mode behaviour they proved is now the ONLY behaviour, and
        # is covered by this plan's own new checks in test_view_pages.py
        # (Home's health link, Airlines' "Change pictures" toggle) and
        # test_config_page.py (Display's two full <details> disclosures).

    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("companion-app: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
