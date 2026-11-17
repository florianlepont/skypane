"""Real-browser checks that the button variants look the same on every page, whichever area
stylesheets the page links: a danger button is a transparent button with an error border and
error ink (never the filled primary), a primary button is the filled accent one, and the
unsaved-changes question's Save and continue is the primary of its three actions, in both
themes. State is waited for, never read right after an input."""
import pytest

from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_MIN_SUPPORTED,
    _login,
    _set_ui_theme,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

# Pages that link different sets of area stylesheets (the airline editor links no console sheet).
ROUTES = ("/airlines/manage", "/flights", "/airlines", "/display", "/account")

_PAINT = """() => {
  const host = document.querySelector('main');
  const make = (variant, type) => {
    const b = document.createElement('button');
    b.type = type; b.className = 'btn btn--' + variant; b.textContent = variant;
    host.appendChild(b); return b; };
  const read = (el) => { const s = getComputedStyle(el);
    return {bg: s.backgroundColor, color: s.color, border: s.borderTopColor}; };
  const out = {};
  for (const [variant, type] of [['primary', 'button'], ['primary', 'submit'],
      ['danger', 'submit'], ['danger', 'button'], ['secondary', 'submit']]) {
    const el = make(variant, type); out[variant + '/' + type] = read(el); el.remove(); }
  const error = document.createElement('span');
  error.style.color = 'var(--color-status-error)'; host.appendChild(error);
  out.error = getComputedStyle(error).color; error.remove();
  const accent = document.createElement('span');
  accent.style.color = 'var(--color-accent)'; host.appendChild(accent);
  out.accent = getComputedStyle(accent).color; accent.remove();
  return out; }"""


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("route", ROUTES)
def test_a_button_variant_paints_the_same_on_every_page(new_context, make_app_server, route, theme):
    server = make_app_server(seed=seed_state_dir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        _set_ui_theme(page, theme)
        paint = page.evaluate(_PAINT)
        for key in ("danger/submit", "danger/button"):
            assert paint[key]["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), (route, key, paint)
            assert paint[key]["color"] == paint["error"], (route, key, paint)
        for key in ("primary/button", "primary/submit"):
            assert paint[key]["bg"] != "rgba(0, 0, 0, 0)", (route, key, paint)
            assert paint[key]["bg"] == paint["primary/submit"]["bg"], (route, key, paint)
        assert paint["secondary/submit"]["bg"] != paint["primary/submit"]["bg"], (route, paint)
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_save_and_continue_is_the_primary_of_the_unsaved_changes_question(
        new_context, make_app_server, theme):
    server = make_app_server(seed=seed_state_dir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        _set_ui_theme(page, theme)
        paint = page.evaluate("""() => {
          const read = (sel) => { const s = getComputedStyle(document.querySelector(sel));
            return {bg: s.backgroundColor, border: s.borderTopColor, width: s.borderTopWidth}; };
          const d = 'dialog[data-leave-dialog] ';
          return {primary: read(d + '[data-leave-dialog-primary]'),
                  secondary: read(d + '[data-leave-dialog-secondary]'),
                  quiet: read(d + '[data-leave-dialog-quiet]'),
                  save: read('.dirty-bar__save')}; }""")
        assert paint["primary"]["bg"] == paint["save"]["bg"], paint
        assert paint["primary"]["bg"] != paint["secondary"]["bg"], paint
        assert paint["quiet"]["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), paint
    finally:
        context.close()


def test_the_catalogue_choice_sample_has_the_same_primary(new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/components")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        paint = page.evaluate("""() => {
          const bg = (el) => getComputedStyle(el).backgroundColor;
          const probe = document.createElement('button');
          probe.type = 'button'; probe.className = 'btn btn--primary';
          document.querySelector('main').appendChild(probe);
          return {sample: bg(document.querySelector('#components-choice [data-components-choice-primary]')),
                  primary: bg(probe)}; }""")
        assert paint["sample"] == paint["primary"], paint
    finally:
        context.close()
