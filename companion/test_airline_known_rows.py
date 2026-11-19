"""The airlines known by name only in the Airlines editor: one read-only row each, with the name, the
prefix and the Artwork button that opens the shared add-artwork step; a chip filters them; an airline
that gains artwork or a hand-made name leaves the block. Checked over HTTP against a real server."""
import html
import os
import re

import pytest

import fleet_console_support as fx
from companion_app_server import InProcessAppServer, http_request
from server.plane import enrich, illustrations, manual_resolutions

EDITOR = "/airlines/manage"
ROW = re.compile(r'<tbody class="airline-group airline-group--known".*?</tbody>', re.S)


@pytest.fixture
def known(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fx.seed_fleet(state_dir)
    cookie = fx.admin_cookie(state_dir)

    def get(lang="en"):
        status, _h, raw = http_request(
            server.url(EDITOR), cookie=cookie, extra_headers={"Accept-Language": lang})
        assert status == 200
        return raw.decode("utf-8")

    yield state_dir, get
    server.stop()


def _rows(page):
    return ROW.findall(page)


def test_one_read_only_row_per_airline_known_by_name_only(known):
    _state, get = known
    page = get()
    rows = _rows(page)
    pairs = enrich.names_without_artwork()
    assert len(rows) == len(pairs)
    for row, (prefix, name) in zip(rows, pairs):
        text = html.unescape(row)
        assert name in text and prefix in text
        assert "<form" not in row and "<input" not in row
        assert 'aria-label="Add the first artwork for %s"' % name in text
        assert 'data-filter-kind="known"' in row
    assert "Known by name only · %d" % len(pairs) in page


def test_the_labels_are_french_in_french(known):
    _state, get = known
    page = html.unescape(get("fr"))
    count = len(enrich.names_without_artwork())
    assert "Connues par leur nom seulement · %d" % count in page
    assert "Ajouter la première illustration pour Turkish Airlines" in page
    assert ">Illustration<" in page


def test_the_chip_counts_the_known_rows(known):
    _state, get = known
    page = get()
    chip = re.search(r'<input[^>]*value="known"[^>]*>.*?</label>', page, re.S)
    assert chip and ">%d<" % len(enrich.names_without_artwork()) in chip.group(0)
    assert "Known by name only" in chip.group(0)


def test_an_airline_with_artwork_leaves_the_block(known):
    state_dir, get = known
    key = manual_resolutions.illustration_key_for_name("Finnair")
    path = illustrations.override_path_for_key(key, state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG")
    assert "Finnair" not in " ".join(_rows(get()))


def test_an_airline_named_by_hand_leaves_the_block(known):
    state_dir, get = known
    assert "KLM Royal" in " ".join(_rows(get()))
    manual_resolutions.add_entry(state_dir, "KLM", "KLM Royal Dutch Airlines")
    assert "KLM Royal" not in " ".join(_rows(get()))
