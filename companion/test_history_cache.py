"""The folded history is reused between requests and recomputed after any write."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import airline_collection, flight_card, history_cache
from companion.pages import history_page
from server import history_db


@pytest.fixture(autouse=True)
def _fresh_cache():
    history_cache.clear()
    yield
    history_cache.clear()


def _event(index, **extra):
    fields = {"ts": "2026-09-21T10:%02d:00+00:00" % index, "hex": "ab%04d" % index,
              "callsign": "AFR%d" % index, "airline": "Air France"}
    fields.update(extra)
    return fields


def _folds(monkeypatch):
    calls = []
    real = flight_card.fold_repeated_passes

    def counting(rows, limit=None):
        calls.append(len(rows))
        return real(rows, limit)

    monkeypatch.setattr(flight_card, "fold_repeated_passes", counting)
    return calls


def _rendered_callsigns(tmp_path):
    rendered = history_page.render(vp.history_ctx(tmp_path))
    return {name for name in ("AFR1", "AFR2", "AFR3") if name in rendered}


def test_flights_fold_the_history_once_until_a_write_and_then_show_it(tmp_path, monkeypatch):
    vp.seed_runway_events(tmp_path, [_event(1), _event(2)])
    calls = _folds(monkeypatch)
    first = history_page.render(vp.history_ctx(tmp_path))
    second = history_page.render(vp.history_ctx(tmp_path))
    assert len(calls) == 1
    assert first.count("AFR1") == second.count("AFR1") > 0
    vp.seed_runway_events(tmp_path, [_event(3)])
    third = history_page.render(vp.history_ctx(tmp_path))
    assert len(calls) == 2 and "AFR3" in third and "AFR3" not in second


def test_a_flight_stored_between_two_requests_is_never_missed(tmp_path):
    vp.seed_runway_events(tmp_path, [_event(1)])
    assert _rendered_callsigns(tmp_path) == {"AFR1"}
    vp.seed_runway_events(tmp_path, [_event(2)])
    assert _rendered_callsigns(tmp_path) == {"AFR1", "AFR2"}
    with history_db.open_db(str(tmp_path)) as conn:
        conn.execute("DELETE FROM runway_events WHERE callsign = 'AFR1'")
        conn.commit()
    assert _rendered_callsigns(tmp_path) == {"AFR2"}


def test_the_airline_collection_reuses_its_fold_and_follows_a_write(tmp_path, monkeypatch):
    vp.seed_runway_events(tmp_path, [_event(1)])
    calls = _folds(monkeypatch)

    def seen():
        with history_db.open_db(str(tmp_path)) as conn:
            entries, _summary = airline_collection.airline_collection(
                conn, "2026-09-22T00:00:00+00:00")
        return sum(entry.times_seen for entry in entries)

    assert seen() == 1 and seen() == 1
    assert len(calls) == 1
    vp.seed_runway_events(tmp_path, [_event(2, hex="cd0002")])
    assert seen() == 2 and len(calls) == 2


def test_different_databases_do_not_share_a_cache_entry(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    vp.seed_runway_events(first, [_event(1)])
    vp.seed_runway_events(second, [_event(2)])
    assert _rendered_callsigns(first) == {"AFR1"}
    assert _rendered_callsigns(second) == {"AFR2"}
