"""Part 03 of the `companion/test_companion_app.py` migration chain
(33-16-PLAN.md): the original harness's `check()` calls #123-#177 (by
ledger row).

Covers the second half of Section 3's static-script gauntlet: dirty-
state.js's own animation contract, freshness.js/panel-lookup.js/flash-
cleanup.js/poll-cooldown.js/confirm-submit.js/theme-preview.js/flight-
rows.js/submit-guard.js/relative-time.js/quick-switch.js/value-controls.js
(each script's public-route check, its ES5-safe/sink-free contract, its
route/src cross-file agreement, and — where the original registered a
deferred `<script>` tag — the page_shell() tag-count guard), the
relative-time/duration wording ladders, the `.js` gate and shared control
vocabulary in `companion/static/style.css`, `companion.battery`'s total
life-estimate contract, and the executable `_NO_JS_CONTROL_REGISTRY`
contract (25-01-PLAN.md Task 4).

Two checks from the original slice read production source as text with
no directly observable HTTP/DOM consequence, and are REWRITTEN per rubric
S rather than ported as-is (see the ledger fragment's Part 03 note and
this plan's SUMMARY):
- `_relative_time_ladder_mirrors_layouts_own_boundaries` used the
  `inspect` module's own source-introspection helper (banned by guard
  G2) to read the three s/m/h/d boundaries out of the Python source.
  Rewritten to DISCOVER those same boundaries behaviourally, by
  bisecting over `layout._age_bucket()`'s own return value — the
  boundaries are exactly as observable this way, and the check never
  reads a line of source.
- `_battery_module_imports_neither_a_page_module_nor_the_server_package`
  used a syntax-tree walk (also banned by G2) over `companion/battery.py`'s
  own source. Rewritten as a subprocess import + `sys.modules` check,
  the same technique 33-15-PLAN.md's `test_draw_module_imports_no_page_
  and_no_server` already established for the identical shape of check.

One check (`_real_get_submit_guard_route_serves_one_shared_disable_on_
submit_guard`) also used to open `companion/static/style.css` and
`companion/app.py` from disk. The CSS half is rewritten over the served
stylesheet's parsed rules (`companion_markup.css_rules()`), preserving
source order without a text scan; the CSP half is rewritten as a real
HTTP response header read (`companion.app.CONTENT_SECURITY_POLICY` is
also the exact runtime value copied onto every response), which is
strictly stronger than reading the Python literal that builds it.

One check (`_exactly_one_has_feature_query_block_survives`) counts
distinct `@supports selector(:has(*))` FEATURE-QUERY BLOCKS in the
stylesheet — a boundary `companion_markup.css_rules()`'s per-rule
`at_rules` tuples cannot distinguish from a second, identically-nested
block, since the parser records at-rule PRELUDE TEXT, not block
position. No structural API expresses this specific property, so it
stays a regex count over the SERVED (HTTP-fetched) stylesheet, comment-
stripped locally — never a disk read (F-01's own sanctioned exception
for cases genuinely inexpressible over `css_rules()`/`declarations_for()`).
"""
import json
import re
import subprocess
import sys

import pytest

import companion.app as app_module
import companion.i18n as i18n_module
import companion.layout as layout
import companion.test_companion_app_helpers as cah
from companion import battery as battery_module
from companion.pages import airlines_page, config_page
from companion_app_server import http_request, login, served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for
from skypane_test_support import REPO_ROOT, child_env


@pytest.fixture(scope="module")
def app03_server(module_app_server_factory):
    """One module-scoped, read-only `companion/app.py` server shared by every check in this
    module that needs real HTTP: none of the module-scoped tests here logs in or otherwise
    mutates server state, matching 33-MIGRATION-RULES.md section 2's "read-only GETs may share a
    module-scoped server" guidance. The one test that DOES log in
    (`test_no_js_control_contract_holds_for_every_registered_control`) uses its own
    function-scoped `make_app_server` server instead.
    """
    return module_app_server_factory(fake_providers=True)


@pytest.fixture(scope="module")
def served_css(app03_server):
    """The stylesheet `companion/app.py` actually serves."""
    return served_stylesheet(app03_server)


# ==========================================================================
# dirty-state.js's own animation contract (CFG-77/CFG-78, 28-08-PLAN.md
# Task 3)
# ==========================================================================


def test_dirty_state_animates_the_bars_own_count_element_and_never_its_word(app03_server):
    """dirty-state.js animates the restored bar's own count element and never its word: exactly
    one text write site, gated on the text having genuinely changed, written before the class is
    added, spending the stylesheet's existing .is-fading-in rule through a remove/reflow/re-add
    with no interval/rAF anywhere — so the role="status" bar announces each change once and
    never a partial word (CFG-77/CFG-78, 28-08-PLAN.md Task 3)"""
    src = served_asset(app03_server, "/static/dirty-state.js")

    # ONE write site.
    write_sites = [m.start() for m in re.finditer(r"countEl\.textContent =(?!=)", src)]
    assert len(write_sites) == 1, (
        "expected exactly ONE assignment to the count element's textContent in dirty-state.js, "
        "got %d — the bar is role=\"status\", so every extra write site is another way for the "
        "same word to be announced twice" % (len(write_sites),))

    # THE GATE.
    assert "countEl.textContent === text" in src, (
        "expected the count element's write to be gated on the text having actually changed — "
        "an unrelated re-render must write nothing at all, not the same string again")

    # TEXT FIRST, CLASS SECOND.
    assert "is-fading-in" in src, (
        "expected the count element to spend the stylesheet's EXISTING changed-value animation "
        "(.is-fading-in), not a fourth keyframes block")
    write_at = write_sites[0]
    add_at = src.index("classList.add(")
    assert add_at > write_at, (
        "expected the count element's text to be written BEFORE the animation class is added, "
        "so the displayed word is the real one from the first frame")
    for token in ("classList.remove(", "offsetWidth"):
        assert token in src, (
            "expected %r — a class that is already present animates nothing on the next change "
            "unless it is removed, a layout property is read, and it is re-added" % (token,))
    remove_at = src.index("classList.remove(")
    assert write_at < remove_at < add_at, (
        "expected the order write-text, remove-class, re-add-class, got offsets %d/%d/%d"
        % (write_at, remove_at, add_at))

    # And the reflow is NOT a timer.
    for forbidden in ("setInterval", "requestAnimationFrame"):
        assert forbidden not in src, "dirty-state.js must not contain %r" % (forbidden,)


# ==========================================================================
# freshness.js (19-09-PLAN.md Task 3, D-02)
# ==========================================================================


def test_freshness_script_es5_safe_with_one_reviewed_sink_exception(app03_server):
    """freshness.js stays ES5-safe and keeps the standing HTML-writing-sink ban (no let/const/
    arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/location.reload/
    XHR), while fetch(/setTimeout/setInterval are its own single, deliberate, reviewed exception
    to the sibling scripts' ban list (D-02) — and it actually uses the safe DOMParser/
    replaceChild/credentials-scoped mechanism this exception was granted for, not merely
    permitted to"""
    src = served_asset(app03_server, "/static/freshness.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(",
        "location.reload", "XMLHttpRequest",
    )
    for token in banned:
        assert token not in src, "freshness.js must not contain %r" % token
    required = ("DOMParser", "replaceChild", "credentials", "fetch(")
    for token in required:
        assert token in src, "expected %r in freshness.js" % token


def test_freshness_script_no_url_taking_navigation_form(app03_server):
    """freshness.js contains no URL-taking navigation form (an assignment to location.href, or a
    call to location.assign/location.replace/window.open) while still reading
    window.location.href as its fetch argument — the fetch target can never be influenced by
    injected markup (19-09-PLAN.md Task 3, D-02/T-19-33)"""
    src = served_asset(app03_server, "/static/freshness.js")
    forbidden_forms = (
        "location.href =", "location.assign", "location.replace", "window.open",
    )
    for form in forbidden_forms:
        assert form not in src, "freshness.js must not contain the navigation form %r" % form
    assert "window.location.href" in src, (
        "expected the permitted window.location.href fetch-argument read")


# ==========================================================================
# panel-lookup.js (06.6.4.1-02 Task 3, D-20)
# ==========================================================================


def test_panel_lookup_script_public(app03_server):
    """GET /static/panel-lookup.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/panel-lookup.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_panel_lookup_script_es5_safe_and_no_html_write(app03_server):
    """panel-lookup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/
    XHR/timers/innerHTML/document.write/eval), and never decides whether to open the dialog from
    viewport dimensions or device orientation (no matchMedia/innerWidth) — that gate is CSS-only,
    on the Airlines trigger's own rule (quick task 260902-tli)"""
    src = served_asset(app03_server, "/static/panel-lookup.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
        "setTimeout", "setInterval", "innerHTML", "document.write",
        "eval(", "matchMedia", "innerWidth")
    for token in banned:
        assert token not in src, "panel-lookup.js must not contain %r" % token


def test_panel_lookup_drop_handling_writes_the_forms_own_input_and_no_canvas(app03_server):
    """panel-lookup.js's drop handling names NO canvas API and no object URL, assigns the
    dropped file to the form's own <input type="file"> through exactly one `new DataTransfer()`
    (so dropped and picked bytes travel one path, with one size cap and one parser), routes BOTH
    the drop and the picker through exactly one shared uploadRefusal() called exactly twice,
    consults it BEFORE assigning, and refuses an untrusted drop event (CFG-51/D19,
    25-07-PLAN.md Task 2)"""
    src = served_asset(app03_server, "/static/panel-lookup.js")
    for token in ("getContext", "drawImage", "toBlob", "toDataURL",
                  "OffscreenCanvas", "createImageBitmap"):
        assert token not in src, (
            "panel-lookup.js names %r — no canvas API may appear in this file. The crop belongs "
            "to companion/illustration_normalize.py alone" % (token,))
    assert "createObjectURL" not in src, (
        "panel-lookup.js names createObjectURL — an object URL is a blob: URL, and this app's "
        "Content-Security-Policy (img-src 'self' data:) blocks a blob: image")
    assert "input.files = transfer.files" in src, (
        "panel-lookup.js never assigns a DataTransfer's files to the form's own file input — "
        "that assignment IS the design")
    assert src.count("new DataTransfer()") == 1, (
        "expected exactly one `new DataTransfer()` in panel-lookup.js, got %d"
        % src.count("new DataTransfer()"))
    assert src.count("function uploadRefusal(") == 1, (
        "expected exactly one uploadRefusal() definition in panel-lookup.js, got %d"
        % src.count("function uploadRefusal("))
    callers = re.findall(r"= uploadRefusal\(zone, files\);", src)
    assert len(callers) == 2, (
        "expected uploadRefusal() to be called exactly twice (once from the drop path, once "
        "from the picker path), got %d" % (len(callers),))
    assert src.index("var refusal = uploadRefusal(zone, files);") \
        < src.index("input.files = transfer.files"), (
        "panel-lookup.js assigns the dropped file BEFORE consulting the validator")
    assert "if (!evt.isTrusted)" in src, (
        "panel-lookup.js's drop handler does not refuse an untrusted event")


def test_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard(app03_server):
    """the mandatory three-element guard appears exactly once and never mentions the optional
    replace-form lookup on its own line, that lookup's first occurrence in the source comes
    after the guard's, it appears exactly once, and the action-attribute setAttribute write
    appears exactly 3 times (replace/resolve-upload/delete, phase 14 plan 14-05) — pinning the
    single line that keeps History's lightbox alive (quick task 260903-btu)"""
    src = served_asset(app03_server, "/static/panel-lookup.js")
    guard_needle = "if (!image || !caption || !note)"
    assert src.count(guard_needle) == 1, (
        "expected the mandatory guard line exactly once, got %d" % src.count(guard_needle))
    guard_line = [line for line in src.splitlines() if guard_needle in line][0]
    assert "replaceForm" not in guard_line, (
        "expected the optional replace-form variable name absent from the mandatory guard's own "
        "line")
    lookup_needle = "var replaceForm"
    assert src.count(lookup_needle) == 1, (
        "expected the optional replace-form lookup exactly once, got %d" % src.count(lookup_needle))
    assert src.index(lookup_needle) > src.index(guard_needle), (
        "expected the optional replace-form lookup's first occurrence after the mandatory "
        "guard's")
    assert src.count('setAttribute("action"') == 3, (
        "expected the action-attribute setAttribute write exactly 3 times, got %d"
        % src.count('setAttribute("action"'))


def test_panel_lookup_script_route_src_agree():
    """layout.PANEL_LOOKUP_SCRIPT_SRC equals companion.app.PANEL_LOOKUP_SCRIPT_ROUTE"""
    assert layout.PANEL_LOOKUP_SCRIPT_SRC == app_module.PANEL_LOOKUP_SCRIPT_ROUTE


# ==========================================================================
# flash-cleanup.js (quick task 260903-peo Task 4, UIR-19)
# ==========================================================================


def test_flash_cleanup_script_public(app03_server):
    """GET /static/flash-cleanup.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/flash-cleanup.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_flash_cleanup_script_es5_safe_and_no_html_write(app03_server):
    """flash-cleanup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/
    XHR/timers/innerHTML/document.write/eval), and uses history.replaceState with
    location.search/location.pathname to strip a consumed ?flash= param (quick task 260903-peo,
    UIR-19)"""
    src = served_asset(app03_server, "/static/flash-cleanup.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
        "setTimeout", "setInterval", "innerHTML", "document.write", "eval(")
    for token in banned:
        assert token not in src, "flash-cleanup.js must not contain %r" % token
    for required in ("history.replaceState", "location.search", "location.pathname"):
        assert required in src, "expected %r in flash-cleanup.js" % required


def test_flash_cleanup_script_route_src_agree():
    """layout.FLASH_CLEANUP_SCRIPT_SRC equals companion.app.FLASH_CLEANUP_SCRIPT_ROUTE"""
    assert layout.FLASH_CLEANUP_SCRIPT_SRC == app_module.FLASH_CLEANUP_SCRIPT_ROUTE


# ==========================================================================
# poll-cooldown.js (19-04-PLAN.md Task 1, D-18/A-35)
# ==========================================================================


def test_poll_cooldown_script_public(app03_server):
    """GET /static/poll-cooldown.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/poll-cooldown.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_poll_cooldown_script_es5_safe_and_no_html_write(app03_server):
    """poll-cooldown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), and carries both the
    D-01 countdown (textContent/removeAttribute/setInterval/clearInterval) and the UXA-15
    disable-on-submit affordance (addEventListener)"""
    src = served_asset(app03_server, "/static/poll-cooldown.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(", "fetch(",
        "XMLHttpRequest")
    for token in banned:
        assert token not in src, "poll-cooldown.js must not contain %r" % token
    required = (
        "textContent", "removeAttribute", "setInterval",
        "clearInterval", "addEventListener")
    for token in required:
        assert token in src, "expected %r in poll-cooldown.js" % token


def test_poll_cooldown_script_route_src_agree():
    """layout.POLL_COOLDOWN_SCRIPT_SRC equals companion.app.POLL_COOLDOWN_SCRIPT_ROUTE"""
    assert layout.POLL_COOLDOWN_SCRIPT_SRC == app_module.POLL_COOLDOWN_SCRIPT_ROUTE


# ==========================================================================
# confirm-submit.js (19-11-PLAN.md Task 2, D-08/A-26)
# ==========================================================================


def test_confirm_submit_script_public(app03_server):
    """GET /static/confirm-submit.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/confirm-submit.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_confirm_submit_script_es5_safe_and_no_html_write(app03_server):
    """confirm-submit.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/location.assign/
    location.replace), and carries the native confirm() step (addEventListener/preventDefault/
    confirm() all present) (D-08/A-26)"""
    src = served_asset(app03_server, "/static/confirm-submit.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(", "fetch(",
        "XMLHttpRequest", "location.assign", "location.replace")
    for token in banned:
        assert token not in src, "confirm-submit.js must not contain %r" % token
    required = ("addEventListener", "preventDefault", "confirm(")
    for token in required:
        assert token in src, "expected %r in confirm-submit.js" % token


def test_confirm_submit_script_route_src_agree():
    """layout.CONFIRM_SUBMIT_SCRIPT_SRC equals companion.app.CONFIRM_SUBMIT_SCRIPT_ROUTE"""
    assert layout.CONFIRM_SUBMIT_SCRIPT_SRC == app_module.CONFIRM_SUBMIT_SCRIPT_ROUTE


# ==========================================================================
# theme-preview.js (20-08-PLAN.md Task 3, D-22..D-24/D-32)
# ==========================================================================


def test_theme_preview_script_public(app03_server):
    """GET /static/theme-preview.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/theme-preview.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_theme_preview_script_es5_safe_and_no_html_write(app03_server):
    """theme-preview.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers/a page-wide
    single-grid lookup), and carries the row->chip src-swap contract (addEventListener/
    querySelector/getAttribute/data-preview-src/data-usage all present) (D-08/D-12/R-11,
    extended by 21-05-PLAN.md Task 3 from D-22..D-24's own original single-grid version)"""
    src = served_asset(app03_server, "/static/theme-preview.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(", "fetch(",
        "XMLHttpRequest", "setTimeout(", "setInterval(",
        'querySelector(".theme-chip-grid")')
    for token in banned:
        assert token not in src, "theme-preview.js must not contain %r" % token
    required = (
        "addEventListener", "querySelector", "getAttribute", "data-preview-src", "data-usage")
    for token in required:
        assert token in src, "expected %r in theme-preview.js" % token


def test_theme_preview_script_route_src_agree():
    """layout.THEME_PREVIEW_SCRIPT_SRC equals companion.app.THEME_PREVIEW_SCRIPT_ROUTE"""
    assert layout.THEME_PREVIEW_SCRIPT_SRC == app_module.THEME_PREVIEW_SCRIPT_ROUTE


def test_theme_preview_script_tag_exactly_once_and_no_bare_inline_script():
    """a rendered authenticated page contains exactly one theme-preview.js <script> tag and no
    inline <script> without a src (D-32)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    expected_tag = '<script src="%s" defer></script>' % layout.THEME_PREVIEW_SCRIPT_SRC
    assert doc.count(expected_tag) == 1, (
        "expected exactly one %r, got %d" % (expected_tag, doc.count(expected_tag)))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))


# ==========================================================================
# flight-rows.js (21-03-PLAN.md Task 2, D-15/R-12)
# ==========================================================================


def test_flight_rows_script_public(app03_server):
    """GET /static/flight-rows.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/flight-rows.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_flight_rows_script_es5_safe_and_no_html_write(app03_server):
    """flight-rows.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers), and carries the
    detail-row toggle contract (addEventListener/querySelectorAll/data-row-toggle/
    flight-detail-row--collapsed/aria-expanded/aria-controls all present) (D-15/R-12)"""
    src = served_asset(app03_server, "/static/flight-rows.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(", "fetch(",
        "XMLHttpRequest", "setTimeout(", "setInterval(")
    for token in banned:
        assert token not in src, "flight-rows.js must not contain %r" % token
    required = (
        "addEventListener", "querySelectorAll", "data-row-toggle",
        "flight-detail-row--collapsed", "aria-expanded", "aria-controls")
    for token in required:
        assert token in src, "expected %r in flight-rows.js" % token


def test_flight_rows_script_route_src_agree():
    """layout.FLIGHT_ROWS_SCRIPT_SRC equals companion.app.FLIGHT_ROWS_SCRIPT_ROUTE"""
    assert layout.FLIGHT_ROWS_SCRIPT_SRC == app_module.FLIGHT_ROWS_SCRIPT_ROUTE


def test_flight_rows_script_tag_exactly_once_and_no_bare_inline_script():
    """a rendered authenticated page contains exactly one flight-rows.js <script> tag and no
    inline <script> without a src (D-15/R-12)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    expected_tag = '<script src="%s" defer></script>' % layout.FLIGHT_ROWS_SCRIPT_SRC
    assert doc.count(expected_tag) == 1, (
        "expected exactly one %r, got %d" % (expected_tag, doc.count(expected_tag)))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))


def test_real_get_flight_rows_route_serves_expected_body(app03_server):
    """a real GET of /static/flight-rows.js returns 200 with data-row-toggle and
    flight-detail-row--collapsed present, and none of innerHTML/document.write/=>/ let / const
    (21-03-PLAN.md Task 2)"""
    text = served_asset(app03_server, "/static/flight-rows.js")
    for token in ("data-row-toggle", "flight-detail-row--collapsed"):
        assert token in text, "expected %r in the served flight-rows.js body" % token
    for banned in ("innerHTML", "document.write", "=>", " let ", " const "):
        assert banned not in text, "did not expect %r in the served flight-rows.js body" % banned


def test_fifteen_deferred_scripts_before_closing_body():
    """a rendered authenticated page contains exactly fifteen deferred <script src= tags before
    the closing body tag, including panel-lookup.js, flash-cleanup.js, poll-cooldown.js,
    confirm-submit.js, theme-preview.js, flight-rows.js, submit-guard.js, relative-time.js,
    quick-switch.js and value-controls.js — and NOT login-card.js, which login_shell() alone
    emits, nor submit-guard.js/relative-time.js/quick-switch.js/value-controls.js on that login
    shell, which still emits exactly one (retargeted in place by 25-01-PLAN.md Task 1)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    body_close = doc.index("</body>")
    head = doc[:body_close]
    count = head.count('<script src=')
    assert count == 15, "expected exactly 15 deferred <script src= tags before </body>, got %d" % count
    for src_const in (
            layout.PANEL_LOOKUP_SCRIPT_SRC, layout.FLASH_CLEANUP_SCRIPT_SRC,
            layout.POLL_COOLDOWN_SCRIPT_SRC, layout.CONFIRM_SUBMIT_SCRIPT_SRC,
            layout.THEME_PREVIEW_SCRIPT_SRC, layout.FLIGHT_ROWS_SCRIPT_SRC,
            layout.SUBMIT_GUARD_SCRIPT_SRC, layout.RELATIVE_TIME_SCRIPT_SRC,
            layout.QUICK_SWITCH_SCRIPT_SRC, layout.VALUE_CONTROLS_SCRIPT_SRC):
        expected_tag = '<script src="%s" defer></script>' % src_const
        assert expected_tag in doc, "expected a deferred <script> tag for %r" % src_const
    assert layout.LOGIN_CARD_SCRIPT_SRC not in doc, (
        "login-card.js must not be emitted on an authenticated page — nothing there carries a "
        ".login-form")
    login_doc = layout.login_shell("<p>login</p>")
    for shell_only in (layout.SUBMIT_GUARD_SCRIPT_SRC,
                       layout.RELATIVE_TIME_SCRIPT_SRC,
                       layout.QUICK_SWITCH_SCRIPT_SRC,
                       layout.VALUE_CONTROLS_SCRIPT_SRC):
        assert shell_only not in login_doc, (
            "%s is registered on the authenticated shell only — the login shell keeps emitting "
            "exactly one deferred script" % shell_only)
    assert login_doc.count('<script src=') == 1, (
        "expected the login shell to keep emitting exactly one deferred script, got %d"
        % login_doc.count('<script src='))
