"""The shared modal dialog: helper markup contract and the assets that make it
work (modal.js and the dialog.modal rules). Browser behaviour of the
component is asserted on the first page that adopts it."""
import pytest

from companion import i18n, layout, ui_modal
from companion_app_server import get, login, served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for, parse_html, strip_js_comments_and_strings

HOSTILE = '"><script>alert(1)</script>'


def _dialog(**overrides):
    args = dict(
        dialog_id="dlg-invite",
        title="Invite a user",
        form_action="/users/invite",
        csrf_html='<input type="hidden" name="csrf_token" value="tok">',
        body_html=(
            '<input type="hidden" name="x" value="1">'
            '<label for="e">Email</label><input id="e" name="email" type="email">'
            '<input id="r" name="role">'),
        submit_label="Invite user",
        dismiss_label="Back to Users",
        dismiss_href="/users",
    )
    args.update(overrides)
    return parse_html(ui_modal.dialog_html(**args))


def test_dialog_carries_the_markup_contract():
    doc = _dialog(subtitle="Frame 1")
    dialog = doc.select_one("dialog.modal")
    assert dialog.attrs["id"] == "dlg-invite"
    assert dialog.attrs["aria-labelledby"] == "dlg-invite-title"
    assert "open" not in dialog.attrs
    form = dialog.select_one("form")
    assert form.attrs["method"] == "post" and form.attrs["action"] == "/users/invite"
    assert form.select_one('input[name="csrf_token"]') is not None
    assert doc.select_one("h2#dlg-invite-title.modal__title").text() == "Invite a user"
    close = doc.select_one("a.modal__close")
    assert close.attrs["href"] == "/users" and "data-modal-close" in close.attrs
    assert close.attrs["aria-label"] == "Close"
    assert doc.select_one(".modal__subtitle").text() == "Frame 1"
    dismiss = doc.select_one(".modal__actions a")
    assert dismiss.attrs["href"] == "/users" and "data-modal-close" in dismiss.attrs
    assert dismiss.text() == "Back to Users"
    assert doc.select_one('.modal__actions button[type="submit"]').text() == "Invite user"


def test_close_label_is_translated():
    assert i18n.t_lang(ui_modal._CLOSE_LABEL_TEXT, "fr") == "Fermer"


def test_text_is_escaped():
    doc = _dialog(
        title=HOSTILE, subtitle=HOSTILE, submit_label=HOSTILE,
        dismiss_label=HOSTILE, dismiss_href="/x?a=%s" % HOSTILE,
        form_action="/y?%s" % HOSTILE)
    assert not doc.select("script")
    assert doc.select_one("h2.modal__title").text() == HOSTILE
    assert doc.select_one(".modal__subtitle").text() == HOSTILE


@pytest.mark.parametrize("bad", [HOSTILE, "", "Has Caps", "-lead", "a b", None, "x" * 80])
def test_hostile_ids_are_refused_rather_than_rendered(bad):
    with pytest.raises(ValueError):
        ui_modal.dialog_html(
            bad, "t", "/a", "", "", "go", "back", "/")
    with pytest.raises(ValueError):
        ui_modal.trigger_html(bad, "x")


def test_confirm_only_focuses_the_dismiss_control():
    doc = _dialog(confirm_only=True, body_html="<p>Sure?</p>", destructive=True)
    assert "autofocus" in doc.select_one(".modal__actions a").attrs
    assert "autofocus" not in doc.select_one('button[type="submit"]').attrs


def test_other_dialogs_focus_the_first_visible_field():
    doc = _dialog()
    assert "autofocus" in doc.select_one("#e").attrs
    assert "autofocus" not in doc.select_one("#r").attrs
    assert "autofocus" not in doc.select_one('input[name="x"]').attrs
    assert "autofocus" not in doc.select_one(".modal__actions a").attrs


def test_an_invalid_field_takes_focus_over_the_first_one():
    body = (
        '<input id="a" name="a"><input id="b" name="b" aria-invalid="true" '
        'aria-describedby="b-err">')
    doc = _dialog(body_html=body, open_=True)
    assert "autofocus" in doc.select_one("#b").attrs
    assert "autofocus" not in doc.select_one("#a").attrs
    assert "open" in doc.select_one("dialog").attrs


def test_focus_id_names_the_control_that_takes_the_initial_focus():
    doc = _dialog(focus_id="r")
    assert "autofocus" in doc.select_one("#r").attrs
    assert "autofocus" not in doc.select_one("#e").attrs
    assert "autofocus" not in doc.select_one('button[type="submit"]').attrs
    assert len([n for n in doc.select("*") if "autofocus" in n.attrs]) == 1


def test_focus_title_opens_on_the_heading_with_no_field_focused():
    doc = _dialog(focus_title=True)
    assert [n for n in doc.select("*") if "autofocus" in n.attrs] == []
    assert "data-focus-title" in doc.select_one("dialog").attrs
    assert doc.select_one("h2").attrs["tabindex"] == "-1"


def test_focus_title_still_focuses_an_invalid_field():
    body = '<input id="a" name="a" aria-invalid="true" aria-describedby="a-err">'
    doc = _dialog(body_html=body, open_=True, focus_title=True)
    assert "autofocus" in doc.select_one("#a").attrs
    assert "data-focus-title" not in doc.select_one("dialog").attrs


def test_an_invalid_field_still_wins_over_focus_id():
    body = (
        '<input id="a" name="a"><input id="b" name="b">'
        '<input id="c" name="c" aria-invalid="true" aria-describedby="c-err">')
    doc = _dialog(body_html=body, open_=True, focus_id="a")
    assert "autofocus" in doc.select_one("#c").attrs
    assert "autofocus" not in doc.select_one("#a").attrs


def test_a_focus_id_that_matches_no_control_is_refused():
    with pytest.raises(ValueError):
        _dialog(focus_id="nope")


def test_a_dialog_without_fields_focuses_the_submit_button():
    doc = _dialog(body_html="<p>Hello</p>")
    assert "autofocus" in doc.select_one('button[type="submit"]').attrs


def test_destructive_submit_differs_from_primary():
    destructive = _dialog(destructive=True).select_one('button[type="submit"]')
    primary = _dialog().select_one('button[type="submit"]')
    assert "btn--danger" in destructive.attrs["class"]
    assert "class" not in primary.attrs


def test_trigger_is_a_hash_link():
    node = parse_html(ui_modal.trigger_html("dlg-invite", "Invite", "btn-primary")).select_one("a")
    assert node.attrs["href"] == "#dlg-invite"
    assert "data-modal-open" in node.attrs
    assert node.attrs["class"] == "btn-primary"


def test_field_error_ids_match_between_paragraph_and_helper():
    paragraph = parse_html(ui_modal.field_error_html("dlg-invite", "email", HOSTILE))
    node = paragraph.select_one("p.field-error")
    assert node.attrs["id"] == ui_modal.error_id("dlg-invite", "email")
    assert node.text() == HOSTILE
    assert not paragraph.select("script")


# --- served assets -----------------------------------------------------------


def test_modal_js_is_served_and_listed_in_the_shell_scripts(app_server_in_process):
    server = app_server_in_process
    session = login(server)
    status, _headers, page = get(server, "/display", cookie=session)
    assert status == 200
    doc = parse_html(page.decode())
    srcs = [node.attrs["src"].split("?", 1)[0] for node in doc.select("script[src]")]
    assert layout.MODAL_SCRIPT_SRC in srcs
    assert layout.MODAL_SCRIPT_SRC in layout.GLOBAL_PAGE_SCRIPTS
    assert all("src" in node.attrs for node in doc.select("script")), "no inline script"
    source = served_asset(server, layout.MODAL_SCRIPT_SRC)
    code = strip_js_comments_and_strings(source)
    for token in ("showModal", "close", "data-modal-open", "data-modal-close", "row-menu"):
        assert token in source, token
    for token in ("eval(", "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write",
                  "fetch(", "XMLHttpRequest", "=>", "`"):
        assert token not in code, token


def _selectors(rules):
    return {sel for rule in rules for sel in rule.selectors}


def test_stylesheet_serves_the_modal_rules(app_server_in_process):
    css = served_stylesheet(app_server_in_process)
    rules = css_rules(css)
    selectors = _selectors(rules)
    for wanted in ("dialog.modal", "dialog.modal::backdrop", "a.modal__close",
                   ".modal[open]:not(.is-modal)", ".modal:target:not(.is-modal)",
                   ".modal__actions", "a.modal__dismiss"):
        assert wanted in selectors, wanted
    base = declarations_for(css, "dialog.modal")
    assert base["background"] == "var(--color-dominant)"
    assert base["color"] == "var(--color-text)"
    assert base["width"] == "min(480px, calc(100% - 48px))"
    assert base["box-shadow"] == "var(--shadow-pop)"
    assert base["border-radius"] == "var(--radius-card)"
    assert declarations_for(css, "dialog.modal::backdrop")["background"] == "var(--color-scrim)"


def test_modal_has_a_phone_bottom_sheet_and_a_no_script_card(app_server_in_process):
    css = served_stylesheet(app_server_in_process)
    phone = ("@media (max-width: 699.98px)",)
    sheet = declarations_for(css, "dialog.modal", phone)
    assert sheet["border-radius"] == "var(--radius-sheet) var(--radius-sheet) 0 0"
    assert sheet["width"] == "100%"
    # The action row carries the bottom padding (and the safe area) so it can stay in view.
    assert " 0 max(" in sheet["padding"]
    assert "var(--safe-bottom)" in declarations_for(css, ".modal__actions", phone)["padding-bottom"]
    assert declarations_for(css, ".modal__actions")["position"] == "sticky"
    assert declarations_for(css, ":root")["--safe-bottom"] == "env(safe-area-inset-bottom, 0px)"
    assert declarations_for(css, "dialog.modal::before", phone)["height"] == "4px"
    card = declarations_for(css, ".modal:target:not(.is-modal)")
    assert card["position"] == "fixed"
    assert "100vmax var(--color-scrim)" in card["box-shadow"]
    assert declarations_for(css, "dialog.modal")["max-height"] == "88svh"
    assert declarations_for(css, "dialog.modal button")["min-height"] == "44px"
    assert declarations_for(css, "a.modal__close")["width"] == "44px"
    assert declarations_for(
        css, "dialog.modal.is-modal[open]", ("@starting-style",))["opacity"] == "0"
