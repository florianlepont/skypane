"""Behaviour of the single frame status resolver and its rendered dot."""
import re
from types import SimpleNamespace

import pytest

from companion import frame_state, frame_status, i18n


def _row(**overrides):
    fields = dict(
        kind="live", offline=False, last_seen=1000.0, battery_percent=80,
        state=frame_state.STATE_DUE, screen_off=False)
    fields.update(overrides)
    return SimpleNamespace(**fields)


CASES = [
    ("retired", _row(kind="retired"), "dot--hollow", "Retired"),
    ("pending", _row(kind="pending", last_seen=None), "dot--hollow",
     "Waiting for pairing"),
    ("offline", _row(offline=True), "dot--error", "No contact"),
    ("never seen", _row(last_seen=None), "dot--warn", "Not seen yet"),
    ("late", _row(state=frame_state.STATE_LATE), "dot--warn", "Overdue"),
    ("low battery", _row(battery_percent=5), "dot--warn", "Low battery"),
    ("held", _row(state=frame_state.STATE_HELD), "dot--off", "Resting"),
    ("screen off", _row(screen_off=True), "dot--off", "Resting"),
    ("healthy", _row(), "dot--ok", "Up to date"),
]


@pytest.mark.parametrize("name,row,dot_class,word", CASES)
def test_priority_table_rows(name, row, dot_class, word):
    html = frame_status.status_dot_html(row)
    assert 'class="dot %s"' % dot_class in html
    assert str(frame_status.frame_status(row).word) == word
    assert 'role="img"' in html
    assert 'aria-label="%s"' % word in html
    assert 'title="%s"' % word in html


def test_word_is_not_visible():
    html = frame_status.status_dot_html(_row())
    assert 'class="dot-label visually-hidden"' in html
    assert not re.search(r'class="dot-label"', html)


def test_offline_beats_low_battery_and_late():
    row = _row(offline=True, battery_percent=1, state=frame_state.STATE_LATE)
    assert frame_status.frame_status(row).key == frame_status.KEY_NO_CONTACT


def test_retired_beats_offline():
    row = _row(kind="retired", offline=True)
    assert frame_status.frame_status(row).key == frame_status.KEY_RETIRED


def test_late_beats_resting():
    row = _row(state=frame_state.STATE_LATE, screen_off=True)
    assert frame_status.frame_status(row).key == frame_status.KEY_OVERDUE


def test_threshold_override_and_missing_battery():
    assert frame_status.frame_status(
        _row(battery_percent=30), low_battery_percent=30).key == (
            frame_status.KEY_LOW_BATTERY)
    assert frame_status.frame_status(
        _row(battery_percent=None)).key == frame_status.KEY_UP_TO_DATE


def test_french_words():
    expected = {
        frame_status.WORD_RETIRED: "Retiré",
        frame_status.WORD_WAITING: "En attente d’appairage",
        frame_status.WORD_NO_CONTACT: "Sans contact",
        frame_status.WORD_NOT_SEEN: "Pas encore vu",
        frame_status.WORD_OVERDUE: "En retard",
        frame_status.WORD_LOW_BATTERY: "Batterie faible",
        frame_status.WORD_RESTING: "Au repos",
        frame_status.WORD_UP_TO_DATE: "À jour",
    }
    for message, french in expected.items():
        assert i18n.t_lang(message, "fr") == french
