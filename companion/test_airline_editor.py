"""The Airline editor at /airlines/manage: an administrator keeps every editing
capability with the same validation and refusals, and every edit returns to the
editor; an owner and a co-manager are refused and nothing is written. Checks run
over HTTP against a real server and compare the stored files."""
import html
import io
import os
import re
import urllib.parse

import pytest
from PIL import Image

import companion.test_companion_app_helpers as cah
import companion.test_status_pages_helpers as shp
import fleet_console_support as fx
from companion import device_scope
from companion_app_server import InProcessAppServer, csrf_url, http_request, with_csrf
from server import fleet_db
from server.plane import airline_default_types, manual_resolutions, name_overrides

CO_EMAIL = "co-manager@example.test"
EDITOR = "/airlines/manage"
VENDORED = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "assets", "icons", "illustrations")
STAMP = "2026-01-01T00:00:00+00:00"


class Rig:
    def __init__(self, server, seed, cookies):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)
        self.frame = "/devices/%s" % seed.owned_id

    def get(self, who, path):
        status, headers, body = http_request(self.server.url(path), cookie=self.cookies.get(who))
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, path, form):
        cookie = self.cookies.get(who)
        status, headers, body = http_request(
            self.server.url(path), method="POST", cookie=cookie,
            data=with_csrf(cookie, form), extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def upload(self, who, path, payload):
        body, content_type = cah.encode_multipart(payload, field_name="illustration")
        status, headers, _b = http_request(
            csrf_url(self.cookies.get(who), self.server.url(path)), method="POST", data=body,
            cookie=self.cookies.get(who), content_type=content_type,
            extra_headers={"Origin": self.server.base_url()})
        return status, headers

    def stored(self):
        """Every file the editing flows write, by relative path with its bytes."""
        found = {}
        for root, _dirs, names in os.walk(self.owned_dir):
            for name in names:
                if name.endswith((".json", ".png")):
                    path = os.path.join(root, name)
                    with open(path, "rb") as handle:
                        found[os.path.relpath(path, self.owned_dir)] = handle.read()
        return found


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()
    yield Rig(server, seed, cookies)
    server.stop()


def _query(headers):
    parts = urllib.parse.urlsplit(headers["Location"])
    return parts.path, urllib.parse.parse_qs(parts.query)


def test_a_rename_returns_to_the_editor_on_the_same_frame(rig):
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/rename",
        {"airline": "Air France", "airline_name": "AF Test"})
    path, query = _query(headers)
    assert (status, path) == (303, rig.frame + EDITOR)
    assert query["flash"] == ["airline_renamed"]
    assert name_overrides.load_name_overrides(rig.owned_dir)


def test_a_refused_rename_reopens_the_sheet_in_the_editor_with_the_same_refusals(rig):
    for name, flash in (("", "manual_name_empty"), ("x" * 101, "manual_name_too_long")):
        status, headers, _b = rig.post(
            "admin", rig.frame + "/airlines/rename", {"airline": "Air France", "airline_name": name})
        path, query = _query(headers)
        assert (status, path) == (303, rig.frame + EDITOR)
        assert query["flash"] == [flash] and query["sheet"] == ["air-france"]
    stale = rig.post(
        "admin", rig.frame + "/airlines/rename", {"airline": "No Such Airline", "airline_name": "Q"})
    assert _query(stale[1])[1]["flash"] == ["airline_rename_stale"]
    assert name_overrides.load_name_overrides(rig.owned_dir) == {}


def test_a_rename_reset_returns_to_the_editor(rig):
    rig.post("admin", rig.frame + "/airlines/rename", {"airline": "Air France", "airline_name": "AF Test"})
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/rename/reset", {"airline": "Air France"})
    path, query = _query(headers)
    assert (status, path, query["flash"]) == (303, rig.frame + EDITOR, ["airline_rename_reset"])
    assert name_overrides.load_name_overrides(rig.owned_dir) == {}


def _seed_gaps(rig):
    gap = {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ZZZ123"}
    shp.seed_unresolved_prefixes(rig.owned_dir, {"ZZZ": gap, "YYY": dict(gap)})


def test_resolving_an_unidentified_prefix_goes_back_to_the_editor_step_two(rig):
    _seed_gaps(rig)
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve", {"prefix": "ZZZ", "airline_name": "Zed Air"})
    path, query = _query(headers)
    assert (status, path) == (303, rig.frame + EDITOR)
    assert query["resolve"] == ["ZZZ"]
    assert "ZZZ" in manual_resolutions.load_manual_resolutions(rig.owned_dir)
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve", {"prefix": "YYY", "airline_name": ""})
    assert _query(headers)[1]["flash"] == ["manual_name_empty"]
    assert "YYY" not in manual_resolutions.load_manual_resolutions(rig.owned_dir)
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve", {"prefix": "QQQ", "airline_name": "Quux Air"})
    assert _query(headers)[1]["flash"] == ["manual_prefix_stale"]


def test_a_picture_is_replaced_and_a_bad_file_is_refused(rig):
    path = rig.frame + "/illustration/air-france.png"
    status, headers = rig.upload("admin", path, b"not an image at all")
    assert (status, _query(headers)[0]) == (303, rig.frame + EDITOR)
    assert _query(headers)[1]["flash"] == ["illustration_not_png"]
    assert not rig.stored()
    with open(os.path.join(VENDORED, "vueling-airlines.png"), "rb") as handle:
        good = handle.read()
    status, headers = rig.upload("admin", path, good)
    assert (status, _query(headers)[0]) == (303, rig.frame + EDITOR)
    assert _query(headers)[1]["flash"] == ["illustration_replaced"]
    assert "illustration_overrides/air-france.png" in rig.stored()


def _png(size, mode="RGBA", fill=(0, 0, 0, 0)):
    buffer = io.BytesIO()
    Image.new(mode, size, fill).save(buffer, format="PNG")
    return buffer.getvalue()


REFUSALS = {
    "not_png": ("illustration_not_png", "Couldn't use that file", "isn't a PNG image"),
    "too_large": ("illustration_too_large", "Couldn't use that image", "too large"),
    "opaque": ("illustration_not_transparent", "Couldn't use that image", "transparent background"),
    "too_small": ("illustration_too_small", "Couldn't use that image", "at least 1200 pixels wide"),
}


def _refusal_cases():
    from companion import post_actions
    return {
        "a text file": (b"not an image at all", "not_png"),
        "a corrupt PNG": (b"\x89PNG\r\n\x1a\n" + b"garbage" * 40, "not_png"),
        "an opaque PNG": (_png((1200, 500), "RGB", (9, 9, 9)), "opaque"),
        "a narrow PNG": (_png((600, 300)), "too_small"),
        "a portrait PNG": (_png((1200, 1300)), "too_small"),
        "a file over the size cap": (
            b"\x00" * (post_actions.MAX_ILLUSTRATION_UPLOAD_BYTES + 4096), "too_large"),
        "a picture over the pixel cap": (_png((8000, 5001), "1", 0), "too_large"),
    }


@pytest.mark.parametrize("case", sorted(_refusal_cases()))
def test_a_refused_picture_says_which_rule_it_broke(rig, case):
    payload, reason = _refusal_cases()[case]
    key, _title, detail = REFUSALS[reason]
    path = rig.frame + "/illustration/air-france.png"
    status, headers = rig.upload("admin", path, payload)
    assert (status, _query(headers)[0]) == (303, rig.frame + EDITOR)
    assert _query(headers)[1]["flash"] == [key]
    assert not rig.stored()
    page = html.unescape(rig.get("admin", rig.frame + EDITOR + "?flash=" + key)[2])
    assert detail in page


def test_each_refusal_reason_is_french_in_french(rig):
    seen = set()
    for key, _title, _detail in REFUSALS.values():
        status, _headers, raw = http_request(
            rig.server.url(rig.frame + EDITOR + "?flash=" + key),
            cookie=rig.cookies["admin"], extra_headers={"Accept-Language": "fr"})
        page = html.unescape(raw.decode("utf-8"))
        assert status == 200 and "Couldn't use that" not in page
        assert "Impossible d’utiliser" in page
        seen.add(key)
    assert len(seen) == 4


def test_deleting_a_manual_resolution_returns_to_the_editor_and_removes_it(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZZZ", "Zed Air", now=STAMP)
    page = rig.get("admin", rig.frame + EDITOR)[2]
    assert 'action="%s/airlines/manual-resolutions/ZZZ/delete"' % rig.frame in page
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/manual-resolutions/ZZZ/delete", {})
    assert (status, _query(headers)[0]) == (303, rig.frame + EDITOR)
    assert manual_resolutions.load_manual_resolutions(rig.owned_dir) == {}
    assert "manual-resolutions/ZZZ/delete" not in rig.get("admin", rig.frame + EDITOR)[2]


def test_a_hand_named_airline_keeps_its_row_with_a_pill_and_a_delete_item(rig):
    manual_resolutions.add_entry(rig.owned_dir, "ZZZ", "Zed Air", now=STAMP)
    page = rig.get("admin", rig.frame + EDITOR)[2]
    assert "manual-resolutions/" not in page.split("</table>")[1]
    group = re.search(r'<tbody class="airline-group"(?:(?!</tbody>).)*Zed Air.*?</tbody>', page, re.S)
    assert group, "the hand-named airline has no row"
    text = group.group(0)
    assert 'class="airlines-pill">Named by hand<' in text
    form = re.search(r'<form class="airlines-menu__form"[^>]*manual-resolutions/ZZZ/delete".*?</form>', text, re.S)
    assert form and ">Delete my name<" in form.group(0)
    assert re.search(r'<input type="hidden" name="[a-z_]*csrf[a-z_]*" value="[^"]+">', form.group(0))
    assert "Manual resolutions" not in page


def _override(rig, key):
    folder = os.path.join(rig.owned_dir, "illustration_overrides")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, key + ".png")
    with open(os.path.join(VENDORED, "vueling-airlines.png"), "rb") as handle:
        data = handle.read()
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def _audit_actions(rig):
    conn = fleet_db.connect(rig.server.state_dir)
    try:
        return [row["action"] for row in fleet_db.list_audit(conn, "all", 50, 0)]
    finally:
        conn.close()


def test_deleting_an_uploaded_artwork_reverts_to_the_default_and_is_audited(rig):
    airline = _override(rig, "air-france")
    per_type = _override(rig, "air-france-b737")
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/artwork/delete", {"key": "air-france-b737"})
    path, query = _query(headers)
    assert (status, path, query["flash"]) == (303, rig.frame + EDITOR, ["airline_artwork_deleted"])
    assert not os.path.exists(per_type) and os.path.exists(airline)
    again = rig.post("admin", rig.frame + "/airlines/artwork/delete", {"key": "air-france-b737"})
    assert _query(again[1])[1]["flash"] == ["airline_artwork_deleted"]
    assert os.path.isfile(os.path.join(VENDORED, "air-france.png"))
    assert _audit_actions(rig).count("airline.artwork_delete") == 2


@pytest.mark.parametrize("key", ("", "nope", "../air-france", "air-france-zz", "generic-fallback.png/.."))
def test_deleting_artwork_of_an_unknown_key_changes_nothing(rig, key):
    _override(rig, "air-france")
    before = rig.stored()
    status, headers, _b = rig.post("admin", rig.frame + "/airlines/artwork/delete", {"key": key})
    assert (status, _query(headers)[1]["flash"]) == (303, ["airline_artwork_stale"])
    assert rig.stored() == before
    assert "airline.artwork_delete" not in _audit_actions(rig)


def test_the_default_type_is_stored_cleared_validated_and_audited(rig):
    route = rig.frame + "/airlines/default-type"
    status, headers, _b = rig.post("admin", route, {"airline_key": "air-france", "type": "a320"})
    assert (status, _query(headers)[1]["flash"]) == (303, ["airline_default_type_saved"])
    assert airline_default_types.load_default_types(rig.owned_dir) == {"air-france": "A320"}
    rig.post("admin", route, {"airline_key": "air-france", "type": ""})
    assert airline_default_types.load_default_types(rig.owned_dir) == {}
    for form in ({"airline_key": "air-france", "type": "x; y"}, {"airline_key": "nope", "type": "A320"}):
        rig.post("admin", route, form)
        assert airline_default_types.load_default_types(rig.owned_dir) == {}
    assert _audit_actions(rig).count("airline.default_type") == 2


@pytest.mark.parametrize("who", ("owner", "co", "anonymous"))
def test_the_artwork_routes_refuse_everyone_but_the_administrator(rig, who):
    _override(rig, "air-france")
    before = rig.stored()
    for route, form in (("/airlines/artwork/delete", {"key": "air-france"}),
                        ("/airlines/default-type", {"airline_key": "air-france", "type": "A320"})):
        status, _h, _b = rig.post(who, rig.frame + route, form)
        assert status in (303, 404), status
    assert rig.stored() == before


def test_naming_a_prefix_inline_stays_on_the_editor_and_stores_the_default_type(rig):
    shp.seed_unresolved_prefixes(rig.owned_dir, {
        "XQZ": {"count": 5, "first_seen": STAMP, "last_seen": STAMP, "example_callsign": "XQZ1"}})
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve",
        {"prefix": "XQZ", "airline_name": "Xqz Wings", "inline": "1", "default_type": "B738"})
    path, query = _query(headers)
    assert (status, path, query) == (303, rig.frame + EDITOR, {"flash": ["manual_resolved"]})
    assert airline_default_types.load_default_types(rig.owned_dir) == {"xqz-wings": "B738"}
    assert "airline.resolve" in _audit_actions(rig)


@pytest.mark.parametrize("who", ("owner", "co"))
def test_a_refused_caller_writes_nothing_and_reads_nothing(rig, who):
    manual_resolutions.add_entry(rig.owned_dir, "ZZZ", "Zed Air", now=STAMP)
    before = rig.stored()
    unknown = rig.get(who, "/no-such-page-anywhere")
    for path in (rig.frame + EDITOR, EDITOR):
        assert rig.get(who, path)[0] == unknown[0] == 404
        assert rig.get(who, path)[2] == unknown[2]
    posts = (
        ("/airlines/resolve", {"prefix": "YYY", "airline_name": "Why Air"}),
        ("/airlines/rename", {"airline": "Air France", "airline_name": "AF Test"}),
        ("/airlines/rename/reset", {"airline": "Air France"}),
        ("/airlines/manual-resolutions/ZZZ/delete", {}),
    )
    for path, form in posts:
        status, _h, body = rig.post(who, rig.frame + path, form)
        assert status == 404 and body == unknown[2]
    body, content_type = cah.encode_multipart(b"x", field_name="illustration")
    status, _h, page = http_request(
        csrf_url(rig.cookies[who], rig.server.url(rig.frame + "/illustration/air-france.png")),
        method="POST", data=body,
        cookie=rig.cookies[who], content_type=content_type,
        extra_headers={"Origin": rig.server.base_url()})
    assert status == 404 and page.decode("utf-8", "replace") == unknown[2]
    assert rig.stored() == before


def test_an_anonymous_caller_is_sent_to_sign_in(rig):
    for path in (EDITOR, rig.frame + EDITOR):
        status, headers, _b = rig.get("anonymous", path)
        assert status == 303 and headers["Location"].startswith("/login")


def test_the_editor_is_titled_and_framed_as_a_console_page(rig):
    page = rig.get("admin", rig.frame + EDITOR)[2]
    assert '<h1 class="page-title">Airline editor</h1>' in page
    assert "frame-menu" not in page
    assert re.search(
        r'<a class="space-switch__segment space-switch__segment--current" href="/fleet"'
        r'[^>]*aria-current="page"', page)


def test_the_frame_chip_is_absent_with_a_single_frame(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    try:
        fx.seed_users(state_dir)
        cookie = fx.admin_cookie(state_dir)
        status, _h, body = http_request(server.url(EDITOR), cookie=cookie)
        assert status in (200, 303)
        if status == 303:
            status, _h, body = http_request(
                server.url(_h["Location"]), cookie=cookie)
        assert status == 200 and "frame-menu" not in body.decode("utf-8", "replace")
    finally:
        server.stop()


@pytest.mark.parametrize("who", ("owner", "admin"))
def test_the_account_page_does_not_link_to_the_editor(rig, who):
    page = rig.get(who, "/account")[2]
    assert "/airlines/manage" not in page and "Airline editor" not in page
