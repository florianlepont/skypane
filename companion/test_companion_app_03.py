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
from companion_markup import at_rule_blocks, css_rules, declarations_for
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


def _first_rule_index(rules, selector):
    """The index of the first `rule` in `rules` (a `css_rules()` list, which preserves source
    order) whose `selectors` includes `selector` exactly, or None."""
    for index, rule in enumerate(rules):
        if selector in rule.selectors:
            return index
    return None


def test_submit_guard_script_serves_shared_disable_on_submit_guard(app03_server, served_css):
    """a real GET of /static/submit-guard.js returns 200 with an ES5-safe, sink-free body that
    delegates a submit listener and disables the submitting control from a ZERO-DELAY TIMER (so
    the browser has already built the form data set, which is what keeps the named theme/
    language submit buttons working), stands down when another listener cancelled the
    submission, skips the control poll-cooldown.js already owns, writes no label at all, reuses
    the ONE existing button:disabled rule still ordered after button:active, and changes no CSP
    (T14, 22-15-PLAN.md Task 3)"""
    text = served_asset(app03_server, "/static/submit-guard.js")
    for banned in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(",
                   "=>", " let ", " const ", "`"):
        assert banned not in text, "did not expect %r in the served submit-guard.js body" % banned
    for token in ("addEventListener", "submit", "disabled", "setTimeout"):
        assert token in text, "expected %r in the served submit-guard.js body" % token
    assert "window.setTimeout(function () {" in text, (
        "expected the disable to run from a zero-delay timer, not inline in the listener (T14)")
    assert "evt.defaultPrevented" in text, (
        "expected the guard to stand down when another listener cancelled the submission")
    assert "data-submit-pending" in text, (
        "expected the guard to skip the control poll-cooldown.js already owns")
    for progress_word in ("Saving", "Enregistrement", "textContent"):
        assert progress_word not in text, (
            "the guard must write only the `disabled` property — a progress label is D3, "
            "Phase 23, and this file must not pre-empt it (found %r)" % (progress_word,))

    # THE DISABLED APPEARANCE is the existing treatment, reused, never a new one: style.css
    # must still declare exactly the one button:disabled rule, ordered after the button:active
    # rule — checked structurally over the SERVED stylesheet's parsed rules (css_rules()
    # preserves source order), never a disk read or a text-offset comparison.
    rules = css_rules(served_css)
    active_selector = "button:not(.value-control__handle):active"
    disabled_indices = [i for i, r in enumerate(rules) if "button:disabled" in r.selectors]
    assert len(disabled_indices) == 1, (
        "expected exactly one button:disabled rule, got %d — T14 reuses the existing disabled "
        "treatment and adds no new disabled styling" % len(disabled_indices))
    active_index = _first_rule_index(rules, active_selector)
    assert active_index is not None, (
        "expected the button:active rule to still exist, narrowed to %r per 28-02-PLAN.md "
        "(CFG-73)" % active_selector)
    assert disabled_indices[0] > active_index, (
        "expected button:disabled to stay AFTER button:active in source order, or a pressed "
        "disabled button loses its own treatment")

    # No CSP change: script-src 'self', no inline, no nonce — read off a REAL response header
    # rather than the Python literal that builds it (strictly stronger than a source read, and
    # not a disk read at all).
    status, headers, _body = http_request(app03_server.base_url() + "/login")
    assert status == 200, "expected 200 from GET /login, got %d" % status
    csp = headers.get("Content-Security-Policy", "")
    assert "script-src 'self';" in csp, "expected the CSP's script-src to stay exactly 'self'"
    assert "script-src 'self' 'unsafe-inline'" not in csp and "nonce-" not in csp, (
        "T14 adds a same-origin file and nothing else — script-src must gain no unsafe-inline "
        "and no nonce")
    # The response header IS companion.app's own runtime constant, confirmed directly too.
    assert csp == app_module.CONTENT_SECURITY_POLICY


# ==========================================================================
# relative-time.js (23-05-PLAN.md Task 1, D14/CFG-34)
# ==========================================================================


def test_relative_time_script_public(app03_server):
    """GET /static/relative-time.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/relative-time.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_relative_time_script_es5_safe_and_no_html_write(app03_server):
    """relative-time.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/setTimeout), carries the
    ticker contract (setInterval+clearInterval, visibilitychange+document.hidden, textContent,
    data-relative, querySelectorAll, getAttribute) and no verdict vocabulary at all (D14/CFG-34,
    23-05-PLAN.md Task 1)"""
    src = served_asset(app03_server, "/static/relative-time.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(", "fetch(",
        "XMLHttpRequest", "setTimeout(")
    for token in banned:
        assert token not in src, "relative-time.js must not contain %r" % token
    required = (
        "setInterval", "clearInterval", "visibilitychange",
        "document.hidden", "textContent", "data-relative",
        "querySelectorAll", "getAttribute")
    for token in required:
        assert token in src, "expected %r in relative-time.js" % token
    for verdict in ("warn", "late", "held", "overdue"):
        assert verdict not in src, (
            "relative-time.js must carry no verdict vocabulary, found %r — this file measures a "
            "distance and picks a wording for it; it never decides that anything is at fault"
            % verdict)


def test_relative_time_script_route_src_agree():
    """layout.RELATIVE_TIME_SCRIPT_SRC equals companion.app.RELATIVE_TIME_SCRIPT_ROUTE"""
    assert layout.RELATIVE_TIME_SCRIPT_SRC == app_module.RELATIVE_TIME_SCRIPT_ROUTE


def test_relative_time_script_tag_exactly_once_and_no_bare_inline_script():
    """a rendered authenticated page contains exactly one relative-time.js <script> tag and no
    inline <script> without a src (D-32)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    expected_tag = '<script src="%s" defer></script>' % layout.RELATIVE_TIME_SCRIPT_SRC
    assert doc.count(expected_tag) == 1, (
        "expected exactly one %r, got %d" % (expected_tag, doc.count(expected_tag)))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))


def test_real_get_relative_time_route_serves_the_ticker(app03_server):
    """a real GET of /static/relative-time.js returns 200 with the served ticker body — the
    data-relative hook present, the visibility gate present, and none of innerHTML/document.write/
    =>/ let / const  (23-05-PLAN.md Task 1)"""
    text = served_asset(app03_server, "/static/relative-time.js")
    for banned in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(",
                   "=>", " let ", " const ", "`"):
        assert banned not in text, "did not expect %r in the served relative-time.js body" % banned
    assert "data-relative" in text and "querySelectorAll" in text, (
        "expected the served body to query the data-relative hook layout.relative_time_html() "
        "renders")
    assert "document.hidden" in text and "visibilitychange" in text, (
        "expected the served body to gate its timer on page visibility (T-23-14)")


def _age_bucket_boundaries(hi=200000, expected_count=3):
    """The `layout._age_bucket()` unit-transition boundaries in `[0, hi)`, found by bisecting
    over the function's OWN return value — never by reading its source (guard G2 bans a
    source-introspection or syntax-tree read of production code). `_age_bucket()` is monotonic
    (seconds -> minutes -> hours -> days as its input grows), so each boundary is the smallest
    `n` where the unit differs from `_age_bucket(n - 1)`'s.
    """
    boundaries = []
    unit_before = layout._age_bucket(0)[1]
    start = 0
    while len(boundaries) < expected_count:
        lo, top = start, hi
        assert layout._age_bucket(top - 1)[1] != unit_before or top - 1 == start, (
            "layout._age_bucket() never leaves unit %r within [0, %d) — cannot discover a third "
            "boundary behaviourally in this range" % (unit_before, hi))
        while top - lo > 1:
            mid = (lo + top) // 2
            if layout._age_bucket(mid)[1] == unit_before:
                lo = mid
            else:
                top = mid
        boundaries.append(top)
        unit_before = layout._age_bucket(top)[1]
        start = top
    return boundaries


def test_relative_time_ladder_mirrors_layouts_own_boundaries(app03_server):
    """relative-time.js's BUCKET_BOUNDARIES equals layout._age_bucket()'s own three boundaries,
    in order, with each number appearing exactly once in the script's code and the array actually
    read (23-RESEARCH.md Pitfall 4, 23-05-PLAN.md Task 1)

    layout._age_bucket()'s own three boundaries are DISCOVERED behaviourally, by bisecting over
    its return value, rather than read out of its source via introspection (guard G2).
    """
    py_bounds = _age_bucket_boundaries()
    js = served_asset(app03_server, "/static/relative-time.js")
    match = re.search(r"var BUCKET_BOUNDARIES = \[([^\]]*)\];", js)
    assert match, "expected a var BUCKET_BOUNDARIES = [...] array in relative-time.js"
    js_bounds = [int(n.strip()) for n in match.group(1).split(",") if n.strip()]
    assert js_bounds == py_bounds, (
        "relative-time.js's ladder is %r but layout._age_bucket()'s is %r — the script mirrors "
        "the Python and must never lead it" % (js_bounds, py_bounds))
    stripped = cah.strip_js_line_and_block_comments(js)
    for bound in py_bounds:
        hits = len(re.findall(r"\b%d\b" % bound, stripped))
        assert hits == 1, (
            "the boundary %d appears %d time(s) in relative-time.js's own code (comments "
            "stripped), expected exactly 1 — the array is the single site, and a second "
            "occurrence is a second ladder" % (bound, hits))
    assert stripped.count("BUCKET_BOUNDARIES") >= 2, (
        "BUCKET_BOUNDARIES is declared in relative-time.js but never read")


def test_relative_time_wordings_equal_the_ladders_own_output(app03_server):
    """every one of relative-time.js's nine wordings, filled with the quantity
    layout._age_bucket() picks, EQUALS relative_age_text()/relative_future_text()'s own output
    for every bucket in both languages; the waiting phrase is translated; and every attribute
    name reaches both the rendered <body> and the script that reads it (D14/CFG-34,
    23-05-PLAN.md Task 1)"""
    samples = (
        (0, "seconds"), (240, "minutes"), (7200, "hours"), (172800, "days"))
    mark = layout.RELATIVE_QUANTITY_MARK
    for lang in ("en", "fr"):
        pairs = dict(layout.relative_copy_attrs(lang=lang))
        for index, (seconds, bucket_name) in enumerate(samples):
            quantity, _unit = layout._age_bucket(seconds)
            for attrs, filler, direction in (
                    (layout.RELATIVE_PAST_ATTRS, layout.relative_age_text, "past"),
                    (layout.RELATIVE_FUTURE_ATTRS, layout.relative_future_text, "future")):
                attr = attrs[index]
                assert attr in pairs, (
                    "lang=%s: relative_copy_attrs() renders no %r attribute" % (lang, attr))
                wording = pairs[attr]
                filled = (wording.replace(mark, str(quantity), 1)
                          if mark in wording else wording)
                expected = filler(seconds, lang=lang)
                assert filled == expected, (
                    "lang=%s %s %s bucket: the wording on %s fills to %r but layout.%s() "
                    "renders %r" % (lang, direction, bucket_name, attr, filled,
                                    filler.__name__, expected))
    for lang, expected_waiting in (("en", None), ("fr", None)):
        pairs = dict(layout.relative_copy_attrs(lang=lang))
        waiting = pairs.get(layout.RELATIVE_WAITING_ATTR)
        assert waiting, "lang=%s: relative_copy_attrs() renders no waiting wording" % lang
        if lang == "fr":
            assert waiting != layout.RELATIVE_WAITING_TEXT, (
                "the waiting wording is untranslated under lang=fr")
    js = served_asset(app03_server, "/static/relative-time.js")
    for attr, _text in layout.relative_copy_attrs(lang="en"):
        assert ('"%s"' % attr) in js, (
            "layout.py renders the %r attribute but relative-time.js never names it" % attr)
    assert ('"%s"' % layout.RELATIVE_COUNTDOWN_ATTR) in js, (
        "relative-time.js never names %r" % layout.RELATIVE_COUNTDOWN_ATTR)
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    body_tag = doc[doc.index("<body"):doc.index(">", doc.index("<body")) + 1]
    for attr, text in layout.relative_copy_attrs():
        assert ('%s="%s"' % (attr, layout.escape_html(text))) in body_tag, (
            "expected %s on the rendered <body> tag, got %r" % (attr, body_tag))


def test_duration_wordings_equal_the_ladders_own_output(app03_server):
    """every one of layout.DURATION_ATTRS' four wordings, filled with the quantity
    layout._age_bucket() picks, EQUALS layout.duration_text()'s own output for every bucket in
    both languages, and every attribute name reaches value-controls.js (CFG-73 Bug A,
    28-03-PLAN.md Task 3)"""
    samples = (
        (0, "seconds"), (240, "minutes"), (7200, "hours"), (172800, "days"))
    texts = (
        layout.DURATION_SECONDS_TEXT, layout.DURATION_MINUTES_TEXT,
        layout.DURATION_HOURS_TEXT, layout.DURATION_DAYS_TEXT)
    mark = layout.RELATIVE_QUANTITY_MARK
    for lang in ("en", "fr"):
        for index, (seconds, bucket_name) in enumerate(samples):
            quantity, _unit = layout._age_bucket(seconds)
            wording = i18n_module.t_lang(texts[index], lang)
            filled = (wording.replace(mark, str(quantity), 1)
                      if mark in wording else wording)
            expected = layout.duration_text(seconds, lang=lang)
            assert filled == expected, (
                "lang=%s %s bucket: layout.DURATION_ATTRS[%d]'s wording (%r) fills to %r but "
                "layout.duration_text(%d, lang=%r) renders %r"
                % (lang, bucket_name, index, texts[index], filled, seconds, lang, expected))
    js = served_asset(app03_server, "/static/value-controls.js")
    for attr in layout.DURATION_ATTRS:
        assert ('"%s"' % attr) in js, (
            "layout.DURATION_ATTRS names %r but value-controls.js never names it" % attr)


def test_relative_time_html_countdown_keyword_is_marked_and_neutral():
    """layout.relative_time_html(countdown=True) marks the element, keeps the future form while
    the instant is ahead, reads the translated waiting wording once it has passed — never an age
    and never a warn/error/alert token — and the default rendering is byte-identical to the
    element 23-03 shipped (D14/CFG-34, 23-05-PLAN.md Task 1)"""
    now = "2026-08-01T12:00:00+00:00"
    soon = "2026-08-01T12:04:00+00:00"
    gone = "2026-08-01T11:58:00+00:00"
    plain = layout.relative_time_html(soon, now, lang="en")
    assert layout.RELATIVE_COUNTDOWN_ATTR not in plain, (
        "the default rendering must be byte-identical to the element 23-03 shipped, got %r"
        % plain)
    ahead = layout.relative_time_html(soon, now, lang="en", countdown=True)
    assert layout.RELATIVE_COUNTDOWN_ATTR in ahead, (
        "expected the countdown marker on a countdown element, got %r" % ahead)
    assert ">in 4m<" in ahead, (
        "a countdown that has NOT run out still reads the future form, got %r" % ahead)
    for lang, expected in (("en", layout.RELATIVE_WAITING_TEXT), ("fr", "en attente…")):
        expired = layout.relative_time_html(gone, now, lang=lang, countdown=True)
        assert (">%s<" % layout.escape_html(expected)) in expired, (
            "lang=%s: an expired countdown must read the waiting wording %r, got %r"
            % (lang, expected, expired))
        assert " ago" not in expired and "il y a" not in expired, (
            "lang=%s: an expired countdown must not turn itself into an age, got %r"
            % (lang, expired))
        for verdict in ("warn", "error", "alert"):
            assert verdict not in expired, (
                "lang=%s: an expired countdown carries no status vocabulary and no warn class, "
                "got %r" % (lang, expired))


# ==========================================================================
# quick-switch.js (23-07-PLAN.md Task 1, D2/CFG-36)
# ==========================================================================


def test_quick_switch_script_public(app03_server):
    """GET /static/quick-switch.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/quick-switch.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_quick_switch_script_es5_safe_and_no_html_write(app03_server):
    """quick-switch.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/
    outerHTML/insertAdjacentHTML/document.write/eval/XHR/setInterval and no URL-taking
    navigation), carries the optimistic-switch contract (aria-checked, preventDefault,
    stopPropagation, textContent, credentials same-origin, redirect manual, X-Requested-With,
    encodeURIComponent) and reaches its rollback from BOTH terminal branches through the
    ES3-safe bracket form (D2/CFG-36, 23-07-PLAN.md Task 1)"""
    src = served_asset(app03_server, "/static/quick-switch.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(",
        "XMLHttpRequest", "setInterval", "location.href", "location.assign",
        "location.replace")
    for token in banned:
        assert token not in src, "quick-switch.js must not contain %r" % token
    required = (
        "aria-checked", "preventDefault", "stopPropagation", "textContent",
        "credentials", "same-origin", "redirect", "manual",
        "X-Requested-With", "encodeURIComponent")
    for token in required:
        assert token in src, "expected %r in quick-switch.js" % token
    assert '["catch"]' in src, (
        "quick-switch.js must reach its network-failure branch through the bracket form "
        "promise[\"catch\"](...) — `catch` is a reserved word in ES3")
    assert src.count("rollBack(") >= 3, (
        "expected quick-switch.js to define one rollback and CALL it from BOTH terminal "
        "branches, found %d references to rollBack( in total" % src.count("rollBack("))


def test_quick_switch_script_route_src_agree():
    """layout.QUICK_SWITCH_SCRIPT_SRC equals companion.app.QUICK_SWITCH_SCRIPT_ROUTE"""
    assert layout.QUICK_SWITCH_SCRIPT_SRC == app_module.QUICK_SWITCH_SCRIPT_ROUTE


def test_quick_switch_script_tag_exactly_once_and_no_bare_inline_script():
    """a rendered authenticated page contains exactly one quick-switch.js <script> tag and no
    inline <script> without a src (D-32)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    expected_tag = '<script src="%s" defer></script>' % layout.QUICK_SWITCH_SCRIPT_SRC
    assert doc.count(expected_tag) == 1, (
        "expected exactly one %r, got %d" % (expected_tag, doc.count(expected_tag)))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))


def test_real_get_quick_switch_route_serves_the_optimistic_switch(app03_server):
    """a real GET of /static/quick-switch.js returns 200 with the served optimistic-switch body —
    layout.REFRESH_PENDING_ATTR and layout.QUICK_SWITCH_FAILED_ATTR both named, and none of
    innerHTML/document.write/=>/ let / const  (23-07-PLAN.md Task 1)"""
    text = served_asset(app03_server, "/static/quick-switch.js")
    for banned in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(",
                   "=>", " let ", " const ", "`"):
        assert banned not in text, "did not expect %r in the served quick-switch.js body" % banned
    assert '"%s"' % layout.REFRESH_PENDING_ATTR in text, (
        "expected the served body to name layout.REFRESH_PENDING_ATTR (%r)"
        % layout.REFRESH_PENDING_ATTR)
    assert '"%s"' % layout.QUICK_SWITCH_FAILED_ATTR in text, (
        "expected the served body to read the translated failure copy off <body> (%r)"
        % layout.QUICK_SWITCH_FAILED_ATTR)


def test_quick_switch_pending_marker_is_layouts_own_name(app03_server):
    """quick-switch.js's PENDING_ATTR, freshness.js's PENDING_ATTR and
    layout.REFRESH_PENDING_ATTR are the same attribute name — the setter, the skip and the Python
    that defines it, pinned in one place so a rename on any one side fails rather than silently
    disabling the D1-races-D2 rule (T-23-26, 23-07-PLAN.md Task 1)"""
    src = served_asset(app03_server, "/static/quick-switch.js")
    match = re.search(r'var PENDING_ATTR = "([^"]+)";', src)
    assert match, "expected quick-switch.js to declare `var PENDING_ATTR = \"...\";`"
    assert match.group(1) == layout.REFRESH_PENDING_ATTR, (
        "quick-switch.js's PENDING_ATTR is %r but layout.REFRESH_PENDING_ATTR is %r"
        % (match.group(1), layout.REFRESH_PENDING_ATTR))
    fresh = served_asset(app03_server, "/static/freshness.js")
    assert ('var PENDING_ATTR = "%s";' % layout.REFRESH_PENDING_ATTR) in fresh, (
        "freshness.js no longer names %r as its own PENDING_ATTR" % layout.REFRESH_PENDING_ATTR)


# ==========================================================================
# value-controls.js (25-01-PLAN.md Task 1, CFG-46; mirror clause
# 25-05-PLAN.md Task 2)
# ==========================================================================


def test_value_controls_script_public(app03_server):
    """GET /static/value-controls.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app03_server.base_url() + "/static/value-controls.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_value_controls_script_es5_safe_and_never_holds_the_value(app03_server):
    """value-controls.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/
    outerHTML/insertAdjacentHTML/document.write/eval/XHR/fetch/timer and no URL-taking
    navigation), carries the steering contract (preventDefault, getAttribute, dispatchEvent,
    aria-valuenow, aria-valuetext, parseFloat and the three Math clamps) and NEVER holds the
    value — exactly one `.value` assignment, inside the one write helper, reached by exactly two
    callers (the native input the form posts, and the nameless MIRROR written only from inside
    paint(), strictly downstream of a read off that field), and at least one read of
    `field.value` back (CFG-46, 25-01-PLAN.md Task 1; the mirror clause 25-05-PLAN.md Task 2)"""
    src = served_asset(app03_server, "/static/value-controls.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "innerHTML", "outerHTML",
        "insertAdjacentHTML", "document.write", "eval(",
        "XMLHttpRequest", "fetch(", "setInterval", "setTimeout",
        "location.href", "location.assign", "location.replace")
    for token in banned:
        assert token not in src, "value-controls.js must not contain %r" % token
    required = (
        "preventDefault", "getAttribute", "dispatchEvent",
        "aria-valuenow", "aria-valuetext", "parseFloat",
        "Math.round", "Math.max", "Math.min")
    for token in required:
        assert token in src, "expected %r in value-controls.js" % token
    value_writes = re.findall(r"(?<![-\w.])\w+\.value\s*=(?!=)", src)
    assert len(value_writes) == 1, (
        "expected exactly ONE assignment to a `.value` in value-controls.js, found %d: %r"
        % (len(value_writes), value_writes))
    assert re.search(r"function writeValue\(el, text\)", src), (
        "value-controls.js's one `.value` assignment is not inside writeValue()")
    for caller, why in (
            ("writeValue(field,", "the native input the form posts"),
            ("writeValue(mirrorFor(wrapper),",
             "the mirror, which posts nothing and is written only from paint()")):
        assert src.count(caller) == 1, (
            "expected exactly one `%s` in value-controls.js (%s), found %d"
            % (caller, why, src.count(caller)))
    paint_at = src.index("function paint(wrapper, bounds, value)")
    mirror_at = src.index("writeValue(mirrorFor(wrapper),")
    steer_at = src.index("function steer(wrapper, raw)")
    assert paint_at < mirror_at < steer_at, (
        "the mirror write is not inside paint() (paint at %d, write at %d, steer at %d)"
        % (paint_at, mirror_at, steer_at))
    assert re.search(r"(?<![-\w.])field\.value(?!\s*=)", src), (
        "expected value-controls.js to READ the native input back through `field.value`")


def test_value_controls_script_route_src_agree():
    """layout.VALUE_CONTROLS_SCRIPT_SRC equals companion.app.VALUE_CONTROLS_SCRIPT_ROUTE"""
    assert layout.VALUE_CONTROLS_SCRIPT_SRC == app_module.VALUE_CONTROLS_SCRIPT_ROUTE


def test_value_controls_script_tag_exactly_once_and_no_bare_inline_script():
    """a rendered authenticated page contains exactly one value-controls.js <script> tag and no
    inline <script> without a src (D-32, 25-01-PLAN.md Task 1)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    expected_tag = '<script src="%s" defer></script>' % layout.VALUE_CONTROLS_SCRIPT_SRC
    assert doc.count(expected_tag) == 1, (
        "expected exactly one %r, got %d" % (expected_tag, doc.count(expected_tag)))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", doc):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))


def test_real_get_value_controls_route_serves_the_registration_seam(app03_server):
    """a real GET of /static/value-controls.js returns 200 with the served steering body — all
    FIFTEEN of layout's VALUE_CONTROL_* seam attributes named, and none of innerHTML/
    insertAdjacentHTML/document.write/eval/=>/ let / const /backtick (CFG-46, 25-01-PLAN.md
    Task 1)"""
    text = served_asset(app03_server, "/static/value-controls.js")
    for banned in ("innerHTML", "insertAdjacentHTML", "document.write", "eval(",
                   "=>", " let ", " const ", "`"):
        assert banned not in text, (
            "did not expect %r in the served value-controls.js body" % banned)
    for attr in (layout.VALUE_CONTROL_ATTR, layout.VALUE_CONTROL_FIELD_ATTR,
                 layout.VALUE_CONTROL_FORM_ATTR, layout.VALUE_CONTROL_MIN_ATTR,
                 layout.VALUE_CONTROL_MAX_ATTR, layout.VALUE_CONTROL_STEP_ATTR,
                 layout.VALUE_CONTROL_HANDLE_ATTR, layout.VALUE_CONTROL_TRACK_ATTR,
                 layout.VALUE_CONTROL_TEXT_ATTR, layout.VALUE_CONTROL_FORMAT_ATTR,
                 layout.VALUE_CONTROL_INPUT_ATTR, layout.VALUE_CONTROL_READOUT_ATTR,
                 layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
                 layout.VALUE_CONTROL_READOUT_SCALE_ATTR,
                 layout.VALUE_CONTROL_READOUT_BASE_ATTR):
        assert ('"%s"' % attr) in text, (
            "expected the served body to name %r — the registration seam 25-04 and 25-05 opt "
            "into by attribute" % attr)


def test_value_controls_wakes_the_save_bar_through_dirty_states_own_listener(app03_server):
    """value-controls.js wakes the save bar through the ONE public surface — a bubbling event
    constructed identically in both its branches, whose name is dirty-state.js's own delegated
    document-level listener, pinned from both sides together with that listener's e.target.form
    filter, because a control that changes a value without waking the save bar silently loses the
    user's edit (CFG-46, 25-01-PLAN.md Task 1)"""
    src = served_asset(app03_server, "/static/value-controls.js")
    modern = re.findall(r'new window\.Event\("([a-z]+)"', src)
    legacy = re.findall(r'\.initEvent\("([a-z]+)"', src)
    assert len(modern) == 1 and len(legacy) == 1, (
        "expected value-controls.js to construct its notification exactly once each way, found "
        "%r and %r" % (modern, legacy))
    assert modern[0] == legacy[0], (
        "value-controls.js constructs %r in its modern branch and %r in its legacy branch"
        % (modern[0], legacy[0]))
    event_name = modern[0]
    assert "bubbles: true" in src, (
        "expected value-controls.js's notification event to be constructed as a BUBBLING event")
    assert re.search(r"(?<![-\w.])\w+\.dispatchEvent\(", src), (
        "expected value-controls.js to dispatch its notification")
    dirty = served_asset(app03_server, "/static/dirty-state.js")
    listener = 'document.addEventListener("%s"' % event_name
    assert listener in dirty, (
        "value-controls.js notifies with %r but dirty-state.js registers no document-level "
        "listener for it (%r not found)" % (event_name, listener))
    assert "e.target.form === form" in dirty, (
        "dirty-state.js's delegated listener no longer filters on `e.target.form === form`")


# ==========================================================================
# the .js gate and the shared control vocabulary (25-01-PLAN.md Task 2,
# CFG-46/D-09) — every check below reads the SERVED, STRUCTURALLY PARSED
# stylesheet (companion_markup.css_rules()/declarations_for()), never a
# disk read or a regex/substring scan of the raw served text (F-01).
# ==========================================================================


def test_js_gate_hides_by_default_and_reveals_under_js(served_css):
    """companion/static/style.css's `.js` gate hides by default (`.js-gate { display: none }` —
    out of the layout AND out of the tab order, never visibility or opacity) and reveals under
    `.js`, and no gate rule anywhere runs the reverse direction, which flashes a dead control on
    every load and shows it permanently when a script fails (D-09/CFG-46, 25-01-PLAN.md Task 2)"""
    base = declarations_for(served_css, ".js-gate")
    assert base.get("display") == "none", (
        "the default `.js-gate` rule declares display: %r — it must be `none`, so the gated "
        "content is out of the LAYOUT and out of the TAB ORDER with scripts blocked"
        % base.get("display"))
    revealed = declarations_for(served_css, ".js .js-gate")
    revealed_display = revealed.get("display")
    assert revealed_display and revealed_display != "none", (
        "the `.js .js-gate` rule declares display: %r — the reveal half must set a rendering "
        "display value" % revealed_display)
    if revealed_display.startswith("var(") and "," not in revealed_display:
        pytest.fail(
            "the `.js .js-gate` reveal declares display: %r with no fallback — a consumer that "
            "never sets --js-gate-display would resolve to nothing and the gate would never "
            "open" % revealed_display)
    # THE REVERSE DIRECTION, CAUGHT EXPLICITLY: no `.js <something-gate>` rule anywhere may hide
    # its own gated content — the gate runs hidden-by-default, revealed-under-.js, never the
    # other way round.
    gate_re = re.compile(r"^\.js\s+([-\w.]*gate[-\w.]*)$")
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            if gate_re.match(selector) and dict(rule.declarations).get("display") == "none":
                pytest.fail(
                    "`%s` hides its gated content under the `.js` class — the gate runs the "
                    "other way round: hidden by default, revealed under `.js`" % selector)


def test_control_vocabulary_reuses_the_registered_hit_area_verbatim(served_css):
    """the shared control vocabulary reuses references/control-density.md's RELOCATED hit-area
    values VERBATIM from `.copy-btn` (every geometry declaration equal, the same ::before inset,
    and 44px recomputed from the declared box plus inset rather than restated),
    `.value-control`/`.value-control__handle` both carry `touch-action: none` so a touch drag is
    not claimed by the browser's own panning gesture, and not one added rule introduces a colour
    literal (CFG-46, 25-01-PLAN.md Task 2)"""
    source_body = declarations_for(served_css, ".copy-btn")
    shared_body = declarations_for(served_css, ".control-hit-area")
    for prop in ("width", "height", "padding", "position", "display",
                 "align-items", "justify-content", "border", "border-radius", "background"):
        assert shared_body.get(prop) == source_body.get(prop), (
            "`.control-hit-area` declares %s: %r but `.copy-btn` declares %r — the shared class "
            "reuses the registered values VERBATIM rather than re-choosing them"
            % (prop, shared_body.get(prop), source_body.get(prop)))

    source_before = declarations_for(served_css, ".copy-btn::before")
    shared_before = declarations_for(served_css, ".control-hit-area::before")
    for prop in ("inset", "content", "position"):
        assert shared_before.get(prop) == source_before.get(prop), (
            "`.control-hit-area::before` declares %s: %r but `.copy-btn::before` declares %r"
            % (prop, shared_before.get(prop), source_before.get(prop)))

    inset = shared_before.get("inset")
    source_icon = declarations_for(served_css, ".copy-btn .icon")
    shared_icon = declarations_for(served_css, ".control-hit-area .icon")
    for prop in ("width", "height"):
        assert shared_icon.get(prop) == source_icon.get(prop), (
            "`.control-hit-area .icon` declares %s: %r but `.copy-btn .icon` declares %r"
            % (prop, shared_icon.get(prop), source_icon.get(prop)))

    box = shared_body.get("width")
    box_px = float(re.sub(r"[^\d.]", "", box or "0"))
    inset_px = abs(float(re.sub(r"[^-\d.]", "", inset or "0")))
    assert box_px + inset_px * 2 == 44.0, (
        "`.control-hit-area` synthesizes a %.1fpx hit area (%.1fpx box + %.1fpx on each side), "
        "not 44 — WCAG 2.5.5's AAA floor" % (box_px + inset_px * 2, box_px, inset_px))

    for selector in (".value-control", ".value-control__handle"):
        decls = declarations_for(served_css, selector)
        assert decls.get("touch-action") == "none", (
            "`%s` declares touch-action: %r — it must be `none`, or the browser's own panning "
            "gesture claims the drag" % (selector, decls.get("touch-action")))
    for selector in (".value-control", ".value-control__track"):
        assert declarations_for(served_css, selector).get("position") == "relative", (
            "`%s` must be `position: relative` — the positioning context an absolutely-placed "
            "handle is measured against" % selector)
    assert declarations_for(served_css, ".value-control__handle").get("position") == "absolute", (
        "`.value-control__handle` must be `position: absolute` — a handle placed in normal flow "
        "cannot be moved by the --value-fraction the script writes")

    for selector in (".control-hit-area", ".control-hit-area::before", ".value-control",
                     ".value-control__track", ".value-control__handle", ".js-gate", ".js .js-gate"):
        decls = declarations_for(served_css, selector)
        for prop, value in decls.items():
            for literal in re.finditer(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", value):
                pytest.fail(
                    "`%s` introduces the colour literal %r on %s — every colour in this file "
                    "comes from a theme token or currentColor" % (selector, literal.group(0), prop))


def test_style_css_carries_exactly_one_has_feature_query_block(served_css):
    """companion/static/style.css still carries exactly ONE @supports selector(:has(*)) block,
    counted on COMMENT-STRIPPED source and on the opening brace — the raw five-line grep counts
    the four paragraphs that explain the rule (CFG-46, 25-01-PLAN.md Task 2)

    Counted as parsed at-rule blocks of the served stylesheet, so the comments that explain
    the rule never count and a second, separate block with the same prelude does.
    """
    blocks = at_rule_blocks(served_css).count("@supports selector(:has(*))")
    assert blocks == 1, (
        "expected exactly ONE @supports selector(:has(*)) block in the served style.css, got %d"
        % (blocks,))


# ==========================================================================
# the battery-life estimate (25-01-PLAN.md Task 3, CFG-49)
# ==========================================================================


def test_battery_life_estimate_is_total_and_never_claims_what_it_cannot():
    """companion.battery.battery_life_estimate() is TOTAL over six series shapes (empty, one row,
    two flat rows, falling, RISING, and a newest row with a None reading) and never states a
    figure the data cannot support: a charged device's rising slope returns days_remaining=None
    rather than a negative or infinite lifetime, a flat series returns None, a series at or below
    the curve's bottom knot floors at zero, a series above the curve's top knot with falling
    millivolts but no measurable state-of-charge drop reports FALLING with days_remaining=None,
    the 'no reading' and 'not enough history' states are DIFFERENT named values, the falling
    series' figure is recomputed in STATE-OF-CHARGE space via battery_fraction() (SEED-006, quick
    260923-gaf) rather than by millivolt extrapolation, and the relative cadence factor is
    available in all six shapes and doubles exactly when the proposed cadence doubles (CFG-49,
    25-01-PLAN.md Task 3)"""
    current_s, proposed_s = 900, 1800

    def est(rows, proposed=proposed_s):
        return battery_module.battery_life_estimate(
            rows, current_wake_interval_s=current_s, proposed_wake_interval_s=proposed)

    falling = [
        {"ts": "2026-09-10", "battery_mv": 3900, "reading_count": 96},
        {"ts": "2026-09-04", "battery_mv": 4020, "reading_count": 96},
    ]
    rising = [
        {"ts": "2026-09-10", "battery_mv": 4000, "reading_count": 96},
        {"ts": "2026-09-04", "battery_mv": 3700, "reading_count": 96},
    ]
    flat = [
        {"ts": "2026-09-10", "battery_mv": 3900, "reading_count": 96},
        {"ts": "2026-09-04", "battery_mv": 3900, "reading_count": 96},
    ]
    newest_is_none = [
        {"ts": "2026-09-10", "battery_mv": None, "reading_count": 0},
        {"ts": "2026-09-04", "battery_mv": 3900, "reading_count": 96},
    ]
    one_row = [{"ts": "2026-09-10", "battery_mv": 3900, "reading_count": 96}]
    shapes = {
        "empty": [],
        "one-row": one_row,
        "two-flat-rows": flat,
        "falling": falling,
        "rising": rising,
        "newest-reading-None": newest_is_none,
    }

    results = {}
    for name, rows in shapes.items():
        results[name] = est(rows)
        assert isinstance(results[name], dict) and "trend" in results[name], (
            "battery_life_estimate(%s) returned %r" % (name, results[name]))

    assert results["empty"]["trend"] == battery_module.LIFE_TREND_NO_READING
    assert results["one-row"]["trend"] == battery_module.LIFE_TREND_NOT_ENOUGH_HISTORY
    assert (battery_module.LIFE_TREND_NO_READING
            != battery_module.LIFE_TREND_NOT_ENOUGH_HISTORY), (
        "LIFE_TREND_NO_READING and LIFE_TREND_NOT_ENOUGH_HISTORY must be different values")
    assert results["newest-reading-None"]["trend"] == battery_module.LIFE_TREND_NOT_ENOUGH_HISTORY
    assert results["newest-reading-None"]["latest_mv"] == 3900, (
        "expected the latest USABLE reading (3900) to survive a None newest row")

    assert results["rising"]["trend"] == battery_module.LIFE_TREND_RISING
    assert results["rising"]["days_remaining"] is None, (
        "a rising series returned days_remaining=%r — a charged device has no honest lifetime "
        "to divide out of it" % (results["rising"]["days_remaining"],))
    assert results["two-flat-rows"]["trend"] == battery_module.LIFE_TREND_FLAT
    assert results["two-flat-rows"]["days_remaining"] is None

    falling_result = results["falling"]
    assert falling_result["trend"] == battery_module.LIFE_TREND_FALLING
    span_days = 6.0
    oldest_fraction = battery_module.battery_fraction(4020)
    newest_fraction = battery_module.battery_fraction(3900)
    soc_drop_per_day = (oldest_fraction - newest_fraction) / span_days
    expected_days = int(round(newest_fraction / soc_drop_per_day))
    assert falling_result["days_remaining"] == expected_days, (
        "a falling series reported days_remaining=%r; recomputed in STATE-OF-CHARGE space it is "
        "%d" % (falling_result["days_remaining"], expected_days))
    assert expected_days == 16, (
        "the falling fixture's own SoC-space recomputation drifted off its documented anchor of "
        "16 days, got %d" % (expected_days,))

    one_day = est([
        {"ts": "2026-09-10", "battery_mv": 3800, "reading_count": 96},
        {"ts": "2026-09-09", "battery_mv": 3950, "reading_count": 96},
    ])
    assert one_day["trend"] == battery_module.LIFE_TREND_NOT_ENOUGH_HISTORY, (
        "a 150 mV fall measured across a ONE-day span reported %r (days_remaining %r)"
        % (one_day["trend"], one_day["days_remaining"]))
    assert one_day["days_remaining"] is None

    barely = est([
        {"ts": "2026-09-10", "battery_mv": 3899, "reading_count": 96},
        {"ts": "2026-09-07", "battery_mv": 3900, "reading_count": 96},
    ])
    assert barely["trend"] == battery_module.LIFE_TREND_FLAT, (
        "a 1 mV fall over three days reported %r (days_remaining %r)"
        % (barely["trend"], barely["days_remaining"]))
    assert barely["days_remaining"] is None

    flat_out = est([
        {"ts": "2026-09-10", "battery_mv": 2900, "reading_count": 96},
        {"ts": "2026-09-04", "battery_mv": 3100, "reading_count": 96},
    ])
    assert flat_out["days_remaining"] == 0, (
        "a series that has already fallen to or below the curve's bottom knot reported "
        "days_remaining=%r — the floor is zero, never a negative lifetime"
        % (flat_out["days_remaining"],))

    above_curve = est([
        {"ts": "2026-09-10", "battery_mv": 4150, "reading_count": 96},
        {"ts": "2026-09-04", "battery_mv": 4200, "reading_count": 96},
    ])
    assert above_curve["trend"] == battery_module.LIFE_TREND_FALLING
    assert above_curve["days_remaining"] is None, (
        "two readings above the curve's top knot produced days_remaining=%r — no "
        "state-of-charge drop is measurable above BATTERY_FULL_MV" % (above_curve["days_remaining"],))

    for name, result in results.items():
        assert result["relative_factor"] == 2.0, (
            "battery_life_estimate(%s) returned relative_factor=%r for 900s -> 1800s"
            % (name, result["relative_factor"]))
    doubled = est([], proposed=proposed_s * 2)["relative_factor"]
    assert doubled == results["empty"]["relative_factor"] * 2, (
        "doubling the proposed cadence moved the relative factor from %r to %r"
        % (results["empty"]["relative_factor"], doubled))
    for bad in (None, 0, -60, True, "900", 1.5e308):
        hostile = battery_module.battery_life_estimate(
            falling, current_wake_interval_s=bad, proposed_wake_interval_s=proposed_s)
        assert hostile["relative_factor"] is None, (
            "a current cadence of %r produced relative_factor=%r"
            % (bad, hostile["relative_factor"]))


def test_battery_module_imports_neither_a_page_module_nor_the_server_package():
    """companion/battery.py imports nothing from companion.pages and nothing from the server
    package — proven by importing it fresh in a subprocess and inspecting sys.modules, never by
    reading its source (D-27/CFG-49, 25-01-PLAN.md Task 3; guard G2 bans a syntax-tree walk of
    production code)"""
    script = (
        "import json, sys\n"
        "import companion.battery\n"
        "banned = sorted(\n"
        "    m for m in sys.modules\n"
        "    if m == 'server' or m.startswith('server.') or m.startswith('companion.pages')\n"
        ")\n"
        "print(json.dumps(banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    banned = json.loads(result.stdout.strip().splitlines()[-1])
    assert banned == [], (
        "importing companion.battery pulled %r into sys.modules — this module is stdlib-only on "
        "purpose (D-27)" % (banned,))


# ==========================================================================
# the no-JS control contract, made EXECUTABLE (25-01-PLAN.md Task 4,
# CFG-46/D-09)
# ==========================================================================

_NO_JS_CONTROL_REGISTRY = (
    {
        "control": "the quiet-hours dial's start handle (D17)",
        "plan": "25-04-PLAN.md Task 3",
        "wrapper_attr": layout.VALUE_CONTROL_ATTR,
        "field": "quiet_hours_start",
        "form": config_page.SETTINGS_FORM_ID,
        "form_assoc": "attribute",
        "render": lambda: config_page.quiet_hours_group("23:00", "07:00"),
    },
    {
        "control": "the quiet-hours dial's end handle (D17)",
        "plan": "25-04-PLAN.md Task 3",
        "wrapper_attr": layout.VALUE_CONTROL_ATTR,
        "field": "quiet_hours_end",
        "form": config_page.SETTINGS_FORM_ID,
        "form_assoc": "attribute",
        "render": lambda: config_page.quiet_hours_group("23:00", "07:00"),
    },
    # 30-03-PLAN.md Task 2 (CFG-85): the retired theme-carousel pagers row is DELETED OUTRIGHT,
    # not repointed — see companion/test_companion_app.py's own (still-legacy, pre-33-16) history
    # for the argument. Kept out of this registry rather than repointed at markup that introduces
    # no `layout.JS_GATE_CLASS`-wrapped element at all.
    {
        "control": "the wake-interval slider (D18)",
        "plan": "25-05-PLAN.md Task 2",
        "wrapper_attr": layout.VALUE_CONTROL_ATTR,
        "field": config_page.WAKE_INTERVAL_FIELD_NAME,
        "form": config_page.SETTINGS_FORM_ID,
        "form_assoc": "enclosing",
        "page_route": "/device",
        "render": lambda: config_page.wake_interval_group(600),
    },
    {
        "control": "the artwork drop zone (D19)",
        "plan": "25-07-PLAN.md Task 2",
        "wrapper_attr": airlines_page.UPLOAD_DROP_ATTR,
        "field": "image",
        "form": airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog",
        "form_assoc": "enclosing",
        "page_route": "/airlines",
        "render": lambda: airlines_page._resolve_upload_form_html("", "-dialog"),
    },
)

_NAMED_ELEMENT_RE = r'<(?P<tag>[a-zA-Z][-\w]*)\b[^>]*\bname="%s"'


def _no_js_control_violation(row, fetch_page):
    """None when `row` honours the contract, else the reason. Split out from the test so the
    fixtures in `test_no_js_control_contract_holds_for_every_registered_control` can run the
    IDENTICAL machine over a deliberately wrong control — an empty registry that merely returns
    True would be a guard nobody has ever seen fail.
    """
    label = "%s (%s)" % (row["control"], row["plan"])
    markup = row["render"]()
    if not isinstance(markup, str):
        return "%s: its group builder returned %r, not markup" % (label, type(markup))

    matches = list(re.finditer(_NAMED_ELEMENT_RE % re.escape(row["field"]), markup))
    if not matches:
        return (
            "%s: no element named %r appears in its group builder's own output"
            % (label, row["field"]))
    native = [m for m in matches if m.group("tag").lower() in ("input", "select")]
    if not native:
        return (
            "%s: %r is carried by <%s>, not a native <input>/<select>"
            % (label, row["field"], matches[0].group("tag")))
    element = markup[native[0].start():markup.index(">", native[0].start()) + 1]

    if row["form_assoc"] == "attribute":
        if ('form="%s"' % row["form"]) not in element:
            return (
                "%s: %r carries no form=%r. Element: %s"
                % (label, row["field"], row["form"], element))
    elif row["form_assoc"] == "enclosing":
        page = fetch_page(row["page_route"])
        if page is None:
            return "%s: could not fetch %r to check the enclosing form" % (
                label, row["page_route"])
        open_tag = re.search(r'<form\b[^>]*\bid="%s"[^>]*>' % re.escape(row["form"]), page)
        if not open_tag:
            return "%s: %s renders no <form id=%r>" % (label, row["page_route"], row["form"])
        close_at = page.find("</form>", open_tag.end())
        field_at = page.find('name="%s"' % row["field"], open_tag.end())
        if field_at == -1 or close_at == -1 or field_at > close_at:
            return (
                "%s: %r is not rendered INSIDE <form id=%r> on %s"
                % (label, row["field"], row["form"], row["page_route"]))
    else:
        return "%s: unknown form_assoc %r" % (label, row["form_assoc"])

    gated = 0
    for tag in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
        text = tag.group(0)
        if not re.search(r"(?<![-\w])%s(?![-\w])" % re.escape(row["wrapper_attr"]), text):
            continue
        class_match = re.search(r'\bclass="([^"]*)"', text)
        classes = class_match.group(1).split() if class_match else []
        if layout.JS_GATE_CLASS not in classes:
            return (
                "%s: an element carries %s OUTSIDE the %r gate — %s"
                % (label, row["wrapper_attr"], layout.JS_GATE_CLASS, text))
        gated += 1
    if gated == 0:
        return (
            "%s: its group builder emits no element carrying %s at all"
            % (label, row["wrapper_attr"]))
    return None


def test_no_js_control_contract_holds_for_every_registered_control(make_app_server):
    """every control in _NO_JS_CONTROL_REGISTRY holds its value in a native <input>/<select> the
    server renders unconditionally, associated with the form that posts it, with EVERY element
    carrying its wrapper attribute also carrying the .js-gate class — and the machine that judges
    that is proven non-vacuous against four fixtures built from real group-builder output: one
    correct control it must accept, and three it must reject (a field name nothing renders, a
    wrapper rendered outside the gate, and a value held by a div instead of a native input)
    (CFG-46/D-09, 25-01-PLAN.md Task 4)"""
    server = make_app_server(fake_providers=True)
    session = login(server)
    base = server.base_url()
    page_cache = {}

    def fetch_page(route):
        if route not in page_cache:
            status, _headers, body = http_request(base + route, cookie=session)
            page_cache[route] = body.decode("utf-8") if status == 200 else None
        return page_cache[route]

    gate_attr = layout.VALUE_CONTROL_ATTR
    wrapper_ok = (
        '<div class="value-control %s" %s %s="wake_interval_s"></div>'
        % (layout.JS_GATE_CLASS, gate_attr, layout.VALUE_CONTROL_FIELD_ATTR))
    wrapper_ungated = (
        '<div class="value-control" %s %s="wake_interval_s"></div>'
        % (gate_attr, layout.VALUE_CONTROL_FIELD_ATTR))
    real_group = config_page.wake_interval_group(900)
    div_instead_of_input = re.sub(
        r'<input\b([^>]*\bname="wake_interval_s"[^>]*)>',
        r'<div\1></div>', real_group)

    def fixture(render, field="wake_interval_s"):
        return {
            "control": "fixture", "plan": "25-01-PLAN.md Task 4",
            "wrapper_attr": gate_attr, "field": field,
            "form": config_page.SETTINGS_FORM_ID, "form_assoc": "enclosing",
            "page_route": "/device", "render": render,
        }

    good = fixture(lambda: real_group + wrapper_ok)
    violation = _no_js_control_violation(good, fetch_page)
    assert violation is None, "the contract rejected a CORRECT control: %s" % violation

    wrong = {
        "a field name nothing renders":
            fixture(lambda: real_group + wrapper_ok, field="wake_interval_seconds"),
        "a wrapper rendered outside the gate":
            fixture(lambda: real_group + wrapper_ungated),
        "a value held by a div instead of a native input":
            fixture(lambda: div_instead_of_input + wrapper_ok),
    }
    for name, bad_row in wrong.items():
        assert _no_js_control_violation(bad_row, fetch_page) is not None, (
            "the contract ACCEPTED %s — the guard is vacuous" % name)

    for row in _NO_JS_CONTROL_REGISTRY:
        violation = _no_js_control_violation(row, fetch_page)
        assert violation is None, violation
