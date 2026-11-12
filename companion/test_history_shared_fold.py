"""The stored history is folded once for every page that reads it: Flights and
the Airlines collection share one fold of the same rows, whatever the order or
the mix of requests, and a new flight costs one fold, not one per page. What
each page shows is unchanged: Flights still reads the owner's airline names and
only the newest events its scan covers; the collection reads every event under
the stored names."""
import threading
from datetime import datetime, timedelta, timezone

import pytest

from companion import airline_collection, flight_card, history_cache, history_query
from server import history_db

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
VIEW = history_query.parse_view({})


def _seed(state_dir, count=40):
    with history_db.open_db(state_dir) as conn:
        for i in range(count):
            history_db.record_runway_event(
                conn, ts=(NOW - timedelta(minutes=7 * i + 1)).isoformat(), hex="3a%04x" % i,
                callsign="%s%03d" % (("AFR", "TVF", "EZY")[i % 3], i), aircraft_type="A320",
                confirmed_state=("departing", "arriving")[i % 2], corroborated=True,
                route_source="adsb", airline=("Air France", "Transavia", "easyJet")[i % 3],
                origin="LFPO", destination="LFMN", tracked_runway=1)


def _add_flight(state_dir, index):
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=(NOW + timedelta(minutes=index)).isoformat(), hex="3b%04x" % index,
            callsign="VLG%03d" % index, aircraft_type="A320", confirmed_state="departing",
            corroborated=True, route_source="adsb", airline="Vueling", origin="LFPO",
            destination="LEBL", tracked_runway=1)


@pytest.fixture
def folds(monkeypatch):
    """Counts the folds of the whole history (a slow one, so that requests overlap)."""
    history_cache.clear()
    calls = []
    real = flight_card.fold_repeated_passes

    def counted(rows, limit=None):
        calls.append(len(rows))
        return real(rows, limit)

    monkeypatch.setattr(flight_card, "fold_repeated_passes", counted)
    yield calls
    history_cache.clear()


def _flights(state_dir, names=None):
    with history_db.open_db(state_dir) as conn:
        return history_query.select(conn, VIEW, 0, 50, names)


def _collection(state_dir):
    with history_db.open_db(state_dir) as conn:
        return airline_collection.airline_collection(conn, NOW)


def test_flights_and_the_collection_share_one_fold(tmp_path, folds):
    state = str(tmp_path)
    _seed(state)
    _flights(state)
    _collection(state)
    _flights(state, {"AFR": "Air Renamed"})
    assert len(folds) == 1, folds


def test_a_new_flight_costs_one_fold_whatever_the_mix_of_pages(tmp_path, folds):
    state = str(tmp_path)
    _seed(state)
    _collection(state)
    _flights(state)
    del folds[:]
    _add_flight(state, 1)
    threads = [threading.Thread(target=reader, args=(state,))
               for reader in (_flights, _collection, _flights, _collection)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(folds) == 1, folds


def test_each_page_still_reads_what_it_read(tmp_path, folds):
    """Flights shows the owner's name for a renamed prefix; the collection's stored names and
    counts are those of every event; neither changes what the other was given."""
    state = str(tmp_path)
    _seed(state, count=9)
    plain = _flights(state)
    renamed = _flights(state, {"AFR": "Air Renamed"})
    assert plain.total == renamed.total == 9
    assert {row["airline"] for row in plain.rows} == {"Air France", "Transavia", "easyJet"}
    assert {row["airline"] for row in renamed.rows} == {"Air Renamed", "Transavia", "easyJet"}
    # The first answer was not rewritten by the second.
    assert {row["airline"] for row in _flights(state).rows} == {
        "Air France", "Transavia", "easyJet"}
    entries, _summary = _collection(state)
    seen = {entry.name: entry.times_seen for entry in entries if entry.times_seen}
    assert seen == {"Air France": 3, "Transavia": 3, "easyJet": 3}, seen


def test_flights_only_counts_the_events_its_scan_covers(tmp_path, folds, monkeypatch):
    """the scan bound still applies to Flights alone: with a bound of 5 events it lists 5
    flights while the collection counts all 9"""
    state = str(tmp_path)
    _seed(state, count=9)
    monkeypatch.setattr(history_query, "SCAN_LIMIT", 5)
    assert _flights(state).total == 5
    entries, _summary = _collection(state)
    assert sum(entry.times_seen for entry in entries) == 9
