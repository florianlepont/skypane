# SPDX-License-Identifier: AGPL-3.0-only
"""A type with no picture family of its own is one "Other" row per airline that always has an upload
control, and its picture is what a flight of such a type is drawn with. Checked over HTTP against a
real server and against the picture selection."""
import html
import itertools
import os
import shutil
import re
from datetime import datetime, timezone

import pytest

import fleet_console_support as fx
from companion.test_airline_editor_helpers import EDITOR, Rig
from companion_app_server import InProcessAppServer, http_request
from server import history_db
from server.plane import illustrations

_HEX = itertools.count()
AIRLINE = "Transavia France"
KEY = "transavia-france"


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    yield Rig(server, seed, {"admin": fx.admin_cookie(state_dir)})
    server.stop()


def _see(rig, code, count=1):
    with history_db.open_db(rig.owned_dir) as conn:
        for index in range(count):
            history_db.record_runway_event(
                conn, ts=datetime.now(timezone.utc).isoformat(), airline=AIRLINE, aircraft_type=code,
                hex="c%05d" % next(_HEX), callsign="TST%04d" % index,
                confirmed_state="departing")


def _rows(rig, lang="en"):
    path = rig.frame + EDITOR + "?types=all"
    body = html.unescape(rig.get("admin", path)[2])
    start = body.index('<tbody class="airline-group" id="airline-%s"' % KEY)
    group = body[start:body.index("</tbody>", start)]
    return re.findall(r'<tr class="airlines-subrow">.*?</tr>', group, re.S)


def test_rare_types_share_one_other_row_with_an_upload_control(rig):
    _see(rig, "PC21", 2)
    _see(rig, "SB20")
    rows = [row for row in _rows(rig) if "airlines-type" in row and ">Other<" in row]
    assert len(rows) == 1
    row = rows[0]
    assert "PC21" in row and "SB20" in row
    # The upload goes to the airline's "other" slot and names the first type seen.
    assert "/illustration/%s-other.png" % KEY in row
    assert "(family)" not in row and 'title="' not in row.split("</th>")[0]


def test_every_type_row_has_an_upload_control(rig):
    for code in ("PC21", "ZZZZ", "C172", "B77W", "B190"):
        _see(rig, code)
    rows = _rows(rig)
    assert rows
    for row in rows:
        assert "/illustration/%s" % KEY in row and "Change artwork" in row or "Add artwork" in row, row


def test_a_mapped_rare_family_has_its_own_slot_not_other(rig):
    _see(rig, "B77W")
    rows = [row for row in _rows(rig) if "B77W" in row]
    assert len(rows) == 1 and "/illustration/%s-b777.png" % KEY in rows[0]
    assert ">Boeing 777<" in rows[0] and 'title="' not in rows[0].split("</th>")[0]


def test_the_other_row_is_french_in_french(rig):
    _see(rig, "PC21")
    _status, _headers, raw = http_request(
        rig.server.url(rig.frame + EDITOR + "?types=all"), cookie=rig.cookies["admin"],
        extra_headers={"Accept-Language": "fr"})
    body = html.unescape(raw.decode("utf-8"))
    assert ">Autre<" in body and 'title="Autre"' not in body and "(famille)" not in body


def test_an_airlines_other_picture_is_drawn_for_an_unmapped_type(tmp_path):
    state_dir = str(tmp_path)
    other = illustrations.override_path_for_key(KEY + "-other", state_dir)
    os.makedirs(os.path.dirname(other), exist_ok=True)
    shutil.copy(illustrations.resolved_illustration_path(KEY), other)
    route = {"airline_name": AIRLINE}
    assert illustrations.select_illustration(route, "PC21", state_dir) == other
    assert illustrations.select_illustration(route, "SB20", state_dir) == other
    # A type with a family never uses it; no type at all does not either.
    assert illustrations.select_illustration(route, "B738", state_dir) != other
    assert illustrations.select_illustration(route, None, state_dir) != other
