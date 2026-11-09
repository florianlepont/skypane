"""The admin-only Components reference page: who can open it, that it is not in the
navigation, that it renders every catalogued helper (so a new helper cannot skip
the page) and that every public helper of the component modules is catalogued or
named as exempt with a reason."""
import importlib
import types
import re

import pytest

import fleet_console_support as fx
from companion import prefs
from companion.pages import components_page


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    return server


def test_an_administrator_opens_the_page_and_it_has_one_anchor_per_family(rig):
    status, _headers, html = fx.get(rig, fx.admin_cookie(rig.state_dir), "/components")
    assert status == 200
    for family in components_page.CATALOGUE:
        assert 'id="components-%s"' % family.slug in html
        assert 'href="#components-%s"' % family.slug in html
    assert "<h1" in html and "Components" in html


def test_a_signed_in_user_and_a_visitor_get_the_unknown_path_404(rig):
    status, _headers, _html = fx.get(rig, fx.user_cookie(rig.state_dir), "/components")
    assert status == 404
    status, _headers, _html = fx.get(rig, None, "/components")
    assert status in (302, 303, 404)


def test_the_page_is_not_in_the_navigation_but_the_system_view_links_to_it(rig):
    cookie = fx.admin_cookie(rig.state_dir)
    _status, _headers, fleet = fx.get(rig, cookie, "/fleet")
    nav = re.findall(r'<(?:nav|aside)\b.*?</(?:nav|aside)>', fleet, re.S)
    assert nav and not any('href="/components"' in block for block in nav)
    _status, _headers, system = fx.get(rig, cookie, "/fleet?view=system")
    assert 'href="/components"' in system


def test_the_page_is_in_french_when_the_reader_chose_french(rig):
    cookie = fx.admin_cookie(rig.state_dir) + "; sp_ui_lang=fr"
    status, _headers, html = fx.get(rig, cookie, "/components")
    assert status == 200
    assert "Composants" in html and "Contrôles segmentés" in html


def _resolve(dotted):
    module_name, function_name = dotted.split(".")
    module = importlib.import_module("companion." + module_name)
    return module, function_name


def test_every_catalogued_helper_is_called_while_the_page_renders(monkeypatch):
    calls = set()
    for dotted in components_page.catalogued_helpers():
        module, name = _resolve(dotted)
        original = getattr(module, name)

        def spy(*args, __dotted=dotted, __original=original, **kwargs):
            calls.add(__dotted)
            return __original(*args, **kwargs)

        monkeypatch.setattr(module, name, spy)
    components_page.render()
    assert components_page.catalogued_helpers() - calls == set()


def test_every_public_component_helper_is_catalogued_or_exempt_with_a_reason():
    public = set()
    for module_name in components_page.COMPONENT_MODULES:
        module = importlib.import_module("companion." + module_name)
        for name, function in vars(module).items():
            if (isinstance(function, types.FunctionType) and function.__module__ == module.__name__
                    and not name.startswith("_")):
                public.add("%s.%s" % (module_name, name))
    catalogued = components_page.catalogued_helpers()
    exempt = set(components_page.EXEMPT)
    assert not catalogued & exempt
    assert all(reason.strip() for reason in components_page.EXEMPT.values())
    assert public - catalogued - exempt == set(), (
        "a new component helper needs a family on the Components page (or an EXEMPT reason)")
    assert (catalogued | exempt) - public == set(), "a listed helper no longer exists"


def test_every_family_renders_at_least_one_state_and_the_page_has_no_raw_error():
    html = components_page.render()
    for family in components_page.CATALOGUE:
        assert family.build(), family.slug
    assert "Traceback" not in html and "%s" not in html
