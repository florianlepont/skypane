"""Who sees which airlines. Two users each own a frame, the administrator owns
the live frame; every frame has its own sightings and unidentified prefixes
(`airline_fleet_world`). The administrator's editor lists the whole fleet: every
airline any frame saw, every unidentified prefix with the counts of all frames
added up, the pictures of the fleet. A user's Airlines page covers the frame it is opened on
only (one of their own), shows no unidentified prefix, and nothing of another user's frames
reaches it, in the page, its dialogs or any cache it reads."""
import os
import re

import pytest

import fleet_console_support as fx
from companion import fleet_unresolved
from companion.airline_fleet_world import (
    GAPS_A, GAPS_B, GAPS_LIVE, World, _gap, artwork_png)
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import state_store
from server.plane import airline_suggest, manual_resolutions, render as panel_render

GAP_PREFIX_RE = re.compile(r'airlines-gap__prefix mono">([A-Z0-9]+)<')
GAP_META_RE = re.compile(
    r'airlines-gap__prefix mono">([A-Z0-9]+)</span><span class="airlines-gap__body">'
    r'<span class="airlines-gap__meta">([^<]*)<span class="cell-inline-sep">[^<]*</span>([^<]*)<')
ITEM_RE = re.compile(r'<li class="collection-item" data-filter-text="([^"]*)".*?</li>', re.S)
SEEN_RE = re.compile(r"Seen (once|\d+ times)")
KNOWN_NAME_RE = re.compile(r'airlines-known__name">([^<]+)<')
SUGGESTION_MARK = "Bravo Suggest Air"


@pytest.fixture
def world(tmp_path):
    root = str(tmp_path / "state")
    server = InProcessAppServer(root)
    rig = World(root)
    rig.server = server
    yield rig
    server.stop()


def _get(world, cookie, path):
    status, _headers, body = fx.get(world.server, cookie, path)
    return status, body


def _gap_prefixes(body):
    return GAP_PREFIX_RE.findall(body)


def _gap_facts(body):
    """`{prefix: (sample callsign, views text)}` of the unidentified rows."""
    return {m.group(1): (m.group(2), m.group(3)) for m in GAP_META_RE.finditer(body)}


def _seen_cards(body):
    """`{lower-case name: sightings}` of the cards the collection page marks
    as seen."""
    seen = {}
    for match in ITEM_RE.finditer(body):
        card = match.group(0)
        found = SEEN_RE.search(card)
        seen[match.group(1)] = 1 if found.group(1) == "once" else int(found.group(1).split()[0])
    return seen


def _views(body, name):
    """The views column of the editor row of the airline named `name`."""
    row = body[body.index('<span class="airlines-name airlines-name--fixed">%s</span>' % name):]
    return re.search(r'airlines-cell--views">([^<]*)<', row).group(1)


def test_admin_editor_lists_every_unidentified_prefix_of_the_fleet(world):
    status, body = _get(world, world.admin, "/airlines/manage")
    assert status == 200
    # Merged counts: AAA 5, BBB 4, CCC 2+2, LLL 3; DDD (2) is under the
    # threshold, EEE is already named; count then prefix orders the rows.
    assert _gap_prefixes(body) == ["AAA", "BBB", "CCC", "LLL"]
    # CCC was last seen on frame B, so its sample is that frame's callsign.
    assert _gap_facts(body) == {
        "AAA": ("AAA101", "5 views"), "BBB": ("BBB301", "4 views"),
        "CCC": ("CCC302", "4 views"), "LLL": ("LLL601", "3 views")}
    assert "CCC201" not in body and "DDD401" not in body


def test_admin_editor_is_the_same_whichever_frame_it_is_opened_on(world):
    lists = {
        tuple(_gap_prefixes(_get(world, world.admin, "/devices/%s/airlines/manage" % frame)[1]))
        for frame in (world.a_id, world.b_id)}
    assert lists == {("AAA", "BBB", "CCC", "LLL")}


def test_admin_editor_lists_every_airline_any_frame_saw_with_merged_views(world):
    _status, body = _get(world, world.admin, "/airlines/manage")
    assert _views(body, "Air France") == "3 views"
    # The airlines no list knows (seen by frame A and frame B) get a row.
    assert {"Quux Air", "Zorro Air"} <= set(KNOWN_NAME_RE.findall(body))
    for curated in ("Vueling Airlines", "Volotea"):
        assert "%s</span>" % curated in body
    assert _views(body, "Vueling Airlines") == "1 view"
    assert _views(body, "Volotea") == "1 view"


def test_admin_editor_shows_the_artwork_of_the_whole_fleet(world):
    from server.plane import illustrations
    path = illustrations.override_path_for_key("zorro-air", world.b_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(artwork_png())
    # Frame B's directory resolves to the one fleet directory, so the picture
    # is there for the editor opened on any frame, and the airline moves out
    # of "known by name only".
    for frame in (world.a_id, world.b_id):
        _s, body = _get(world, world.admin, "/devices/%s/airlines/manage" % frame)
        assert "illustration/zorro-air.png?v=" in body
        assert "Zorro Air" not in KNOWN_NAME_RE.findall(body)


def test_admin_names_a_prefix_only_another_frame_saw(world):
    cookie = world.admin
    form = {"prefix": "BBB", "airline_name": "Bravo Air"}
    status, headers, _b = http_request(
        world.server.url("/devices/%s/airlines/resolve" % world.a_id), method="POST",
        cookie=cookie, data=with_csrf(cookie, form),
        extra_headers={"Origin": world.server.base_url()})
    assert status == 303
    assert "flash=manual_prefix_stale" not in headers["Location"]
    assert manual_resolutions.load_manual_resolutions(world.root)["BBB"]["airline_name"] == "Bravo Air"
    _s, body = _get(world, cookie, "/airlines/manage")
    assert _gap_prefixes(body) == ["AAA", "CCC", "LLL"]


def test_a_prefix_no_frame_saw_is_still_refused_as_stale(world):
    cookie = world.admin
    status, headers, _b = http_request(
        world.server.url("/devices/%s/airlines/resolve" % world.a_id), method="POST",
        cookie=cookie, data=with_csrf(cookie, {"prefix": "QQQ", "airline_name": "Quux"}),
        extra_headers={"Origin": world.server.base_url()})
    assert status == 303 and "flash=manual_prefix_stale" in headers["Location"]


def test_user_page_lists_only_the_airlines_their_own_frame_saw(world):
    _s, body_a = _get(world, world.user_a, "/devices/%s/airlines" % world.a_id)
    _s, body_b = _get(world, world.user_b, "/devices/%s/airlines" % world.b_id)
    assert _seen_cards(body_a) == {"air france": 2, "zorro air": 1}
    assert _seen_cards(body_b) == {"vueling airlines": 1, "quux air": 2, "air france": 1}
    assert "Airlines your frame has seen" in body_a


def test_user_page_shows_no_unidentified_prefix_and_no_naming_control(world):
    for cookie, frame in ((world.user_a, world.a_id), (world.user_b, world.b_id)):
        _s, body = _get(world, cookie, "/devices/%s/airlines" % frame)
        for prefix in list(GAPS_A) + list(GAPS_B) + list(GAPS_LIVE):
            assert 'data-view-panel-resolve-prefix="%s"' % prefix not in body
            assert "Name the prefix" not in body
        assert "/airlines/resolve" not in body and "/airlines/manage" not in body


def test_user_never_sees_another_users_data(world):
    # A fleet-wide name for a prefix only frame B saw, and a cached suggestion.
    manual_resolutions.add_entry(world.root, "BBB", "Bravo Air")
    airline_suggest._save(world.root, {"BBB": {
        "state": airline_suggest.STATE_SUGGESTED, "name": SUGGESTION_MARK,
        "model": "m", "asked_at": "2026-03-01T00:00:00+00:00"}}, [])
    _s, body_a = _get(world, world.user_a, "/devices/%s/airlines" % world.a_id)
    _s, body_b = _get(world, world.user_b, "/devices/%s/airlines" % world.b_id)
    label = panel_render._TYPE_DISPLAY_LABELS.get
    only_b = ("Quux", "QUX", "VLG", "A21N", label("A21N", "A21N"), "E190", label("E190", "E190"),
              "BBB", "Bravo", "Echo", SUGGESTION_MARK, "Balcony")
    only_a = ("Zorro", "ZOR", "AAA", "AFR1", "Kitchen")
    for needle in only_b:
        assert needle not in body_a, needle
    for needle in only_a:
        assert needle not in body_b, needle
    # Air France is the one airline both saw: each page counts only its own.
    assert _seen_cards(body_a)["air france"] == 2 and _seen_cards(body_b)["air france"] == 1
    assert label("A320", "A320") in body_a


def test_user_cannot_open_another_users_frame_or_the_editor(world):
    for path in ("/devices/%s/airlines" % world.b_id, "/devices/%s/airlines/manage" % world.a_id,
                 "/airlines/manage"):
        status, body = _get(world, world.user_a, path)
        assert status in (302, 303, 403, 404) or "Quux" not in body
        assert "Quux" not in body and "BBB" not in body


def test_user_gains_no_write_ability(world):
    before = manual_resolutions.load_manual_resolutions(world.root)
    for frame in (world.a_id, world.b_id):
        status, _h, _b = http_request(
            world.server.url("/devices/%s/airlines/resolve" % frame), method="POST",
            cookie=world.user_a,
            data=with_csrf(world.user_a, {"prefix": "AAA", "airline_name": "Alpha Air"}),
            extra_headers={"Origin": world.server.base_url()})
        assert status in (403, 404)
    assert manual_resolutions.load_manual_resolutions(world.root) == before
    assert not os.path.exists(os.path.join(world.root, "illustration_overrides"))


def test_a_user_with_two_frames_sees_each_frame_on_its_own_page(world):
    from server import fleet_db
    conn = fleet_db.connect(world.root)
    try:
        fleet_db.add_co_manager(conn, world.b_id, world.seed.owner_id, world.seed.user_id)
    finally:
        conn.close()
    _s, on_a = _get(world, world.user_a, "/devices/%s/airlines" % world.a_id)
    _s, on_b = _get(world, world.user_a, "/devices/%s/airlines" % world.b_id)
    assert _seen_cards(on_a) == {"air france": 2, "zorro air": 1}
    assert _seen_cards(on_b) == {"vueling airlines": 1, "quux air": 2, "air france": 1}
    assert "Quux" not in on_a and "Zorro" not in on_b


def test_the_user_page_lists_only_seen_airlines_without_progress_or_filter_chips(world):
    _s, body = _get(world, world.user_a, "/devices/%s/airlines" % world.a_id)
    assert len(ITEM_RE.findall(body)) == 2
    for gone in ("collection-card--unseen", "collection-progress__bar", "<progress",
                 "filter-chip", 'name="show"', "Not yet seen", "spotted"):
        assert gone not in body, gone


def _dir(tmp_path, name, registry):
    directory = str(tmp_path / name)
    os.makedirs(directory, exist_ok=True)
    state_store.save_poll_state(directory, {"unresolved_prefixes": registry})
    return directory


def _merge(tmp_path, *registries):
    return fleet_unresolved.merged_registry(
        [_dir(tmp_path, "f%d" % index, registry) for index, registry in enumerate(registries)])


def test_merge_adds_counts_and_keeps_the_extremes_and_the_latest_example(tmp_path):
    merged = _merge(
        tmp_path,
        {"ZZZ": _gap(2, "2026-03-05T10:00:00+00:00", "ZZZ1")},
        {"ZZZ": {"count": 3, "first_seen": "2026-02-01T10:00:00+00:00",
                 "last_seen": "2026-03-09T10:00:00+00:00", "example_callsign": "ZZZ2"},
         "bad": "x", "BOOL": {"count": True}, "NOCNT": {}})
    assert merged == {"ZZZ": {
        "count": 5, "first_seen": "2026-02-01T10:00:00+00:00",
        "last_seen": "2026-03-09T10:00:00+00:00", "example_callsign": "ZZZ2"}}


def test_merge_is_independent_of_directory_order_for_counts_and_stamps(tmp_path):
    one = {"AB": _gap(1, "2026-03-05T10:00:00+00:00", "AB1")}
    two = {"AB": _gap(4, "2026-03-07T10:00:00+00:00", "AB2")}
    first = fleet_unresolved.merged_registry([_dir(tmp_path, "a", one), _dir(tmp_path, "b", two)])
    second = fleet_unresolved.merged_registry([_dir(tmp_path, "b", two), _dir(tmp_path, "a", one)])
    assert first == second
    assert first["AB"]["example_callsign"] == "AB2" and first["AB"]["count"] == 5


def test_cap_and_threshold_use_the_merged_counts(world):
    from companion.pages import airlines_page
    # 15 prefixes seen twice on A and twice on B (merged 4): all pass the
    # threshold and the cap keeps 12, the rest is the overflow.
    both = {"P%02d" % n: _gap(2, "2026-03-09T10:00:00+00:00", "P%02d1" % n) for n in range(15)}
    state_store.save_poll_state(world.a_dir, {"unresolved_prefixes": both})
    state_store.save_poll_state(world.b_dir, {"unresolved_prefixes": dict(both)})
    state_store.save_poll_state(world.root, {"unresolved_prefixes": {}})
    _s, body = _get(world, world.admin, "/airlines/manage")
    assert _gap_prefixes(body) == ["P%02d" % n for n in range(12)]
    assert airlines_page.GAP_BLOCK_CAP == 12
    assert "3 other unresolved prefixes" in body
