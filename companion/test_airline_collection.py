"""The Airline collection read model: counts, rarity, newness and badges
computed from a seeded runway_events history and the curated airline list."""
from datetime import datetime, timedelta, timezone

import pytest

from companion import airline_collection as collection
from companion import airline_display
from server import history_db
from server.plane import illustrations

NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
CURATED = [name for name, _shapes in illustrations.target_variants_by_airline()]
RARE_AIRLINE, OCCASIONAL_AIRLINE, REGULAR_AIRLINE = CURATED[0], CURATED[1], CURATED[2]
UNCURATED = "Zed Charter Wings"


def _iso(days_ago, minutes=0):
    return (NOW - timedelta(days=days_ago, minutes=minutes)).isoformat()


class Seed:
    def __init__(self, conn):
        self.conn = conn
        self._n = 0

    def event(self, airline, days_ago, **fields):
        """One distinct flight: its own aircraft hex and callsign."""
        self._n += 1
        fields.setdefault("hex", "a%05d" % self._n)
        fields.setdefault("callsign", "FLT%04d" % self._n)
        fields.setdefault("confirmed_state", "departing")
        history_db.record_runway_event(
            self.conn, ts=_iso(days_ago, minutes=self._n), airline=airline, **fields)


@pytest.fixture
def conn(tmp_path):
    with history_db.open_db(str(tmp_path)) as connection:
        yield connection


@pytest.fixture
def seed(conn):
    return Seed(conn)


def _by_name(entries):
    return {entry.name: entry for entry in entries}


def _collect(conn, **kwargs):
    return collection.airline_collection(conn, NOW.isoformat(), **kwargs)


def _seed_history(seed):
    seed.event(RARE_AIRLINE, 30, aircraft_type="A320")
    for age in (40, 20, 10):
        seed.event(OCCASIONAL_AIRLINE, age, aircraft_type="B738")
    for index in range(12):
        seed.event(REGULAR_AIRLINE, 60 - index, aircraft_type="A21N" if index % 3 else "A320")
    seed.event(UNCURATED, 5)
    seed.event(UNCURATED, 4)
    seed.event(None, 3)
    seed.event("", 3)
    seed.event("   ", 3)


def test_rarity_follows_the_sighting_count(conn, seed):
    _seed_history(seed)
    entries, _summary = _collect(conn)
    rows = _by_name(entries)
    shown = lambda name: rows[collection.render_text.display_airline_name(name)]  # noqa: E731
    assert shown(RARE_AIRLINE).rarity == collection.RARITY_RARE
    assert shown(RARE_AIRLINE).times_seen == 1
    assert shown(OCCASIONAL_AIRLINE).rarity == collection.RARITY_OCCASIONAL
    assert shown(OCCASIONAL_AIRLINE).times_seen == 3
    assert shown(REGULAR_AIRLINE).rarity == collection.RARITY_REGULAR
    assert shown(REGULAR_AIRLINE).times_seen == 12


def test_threshold_boundaries():
    assert collection.rarity_for(0) == collection.RARITY_NONE
    assert collection.rarity_for(2) == collection.RARITY_RARE
    assert collection.rarity_for(3) == collection.RARITY_OCCASIONAL
    assert collection.rarity_for(9) == collection.RARITY_OCCASIONAL
    assert collection.rarity_for(10) == collection.RARITY_REGULAR


def test_uncurated_airline_is_spotted_but_not_in_the_total(conn, seed):
    _seed_history(seed)
    entries, summary = _collect(conn)
    extra = [entry for entry in entries if not entry.curated]
    assert [(entry.name, entry.times_seen) for entry in extra] == [(UNCURATED, 2)]
    assert summary.total == len(CURATED)
    assert summary.spotted == 4
    assert len(entries) == len(CURATED) + 1


def test_null_and_blank_airlines_appear_nowhere(conn, seed):
    _seed_history(seed)
    entries, _summary = _collect(conn)
    assert sum(entry.times_seen for entry in entries) == 1 + 3 + 12 + 2
    assert all(entry.name.strip() for entry in entries)
    assert not any("unknown" in entry.name.lower() for entry in entries)


def test_curated_order_is_kept_and_unseen_airlines_are_listed(conn, seed):
    _seed_history(seed)
    entries, _summary = _collect(conn)
    curated = [entry for entry in entries if entry.curated]
    expected = [
        airline_display.shown_name(collection.render_text.display_airline_name(name))
        for name in CURATED]
    assert [entry.name for entry in curated] == expected
    unseen = [entry for entry in curated if not entry.seen]
    assert len(unseen) == len(CURATED) - 3
    assert all(
        entry.rarity == collection.RARITY_NONE and entry.times_seen == 0
        and not entry.is_new and entry.first_ts == "" for entry in unseen)


def test_first_and_last_seen_types_and_callsigns(conn, seed):
    _seed_history(seed)
    entries, _summary = _collect(conn)
    regular = _by_name(entries)[collection.render_text.display_airline_name(REGULAR_AIRLINE)]
    oldest = conn.execute(
        "SELECT MIN(ts) FROM runway_events WHERE airline = ?", (REGULAR_AIRLINE,)).fetchone()[0]
    assert regular.first_ts == oldest
    assert regular.first_day <= regular.last_day
    assert regular.types[0] == "A21N"
    assert set(regular.types) == {"A21N", "A320"}
    assert len(regular.callsigns) == collection.RECENT_CALLSIGNS
    newest = conn.execute(
        "SELECT callsign FROM runway_events WHERE airline = ? ORDER BY ts DESC LIMIT 1",
        (REGULAR_AIRLINE,)).fetchone()[0]
    assert regular.callsigns[0] == newest


def test_new_pill_only_within_seven_days_of_the_first_sighting(conn, seed):
    seed.event(RARE_AIRLINE, 6)
    seed.event(OCCASIONAL_AIRLINE, 8)
    seed.event(REGULAR_AIRLINE, 20)
    seed.event(REGULAR_AIRLINE, 1)
    rows = _by_name(_collect(conn)[0])
    shown = collection.render_text.display_airline_name
    assert rows[shown(RARE_AIRLINE)].is_new is True
    assert rows[shown(OCCASIONAL_AIRLINE)].is_new is False
    assert rows[shown(REGULAR_AIRLINE)].is_new is False


@pytest.mark.parametrize("spotted, earned, goal", [
    (0, (), 1), (1, (1,), 5), (4, (1,), 5), (5, (1, 5), 10),
    (10, (1, 5, 10), 25), (25, (1, 5, 10, 25), 50), (50, (1, 5, 10, 25, 50), None)])
def test_badges_are_the_thresholds_reached(spotted, earned, goal):
    summary = collection._summary(spotted, 62)
    assert summary.earned == earned
    assert summary.next_goal == goal


def test_empty_history_is_all_not_seen_yet(conn):
    entries, summary = _collect(conn)
    assert summary.spotted == 0 and summary.earned == ()
    assert summary.total == len(CURATED)
    assert not any(entry.seen for entry in entries)


def test_a_pass_stored_twice_counts_once(conn, seed):
    """The poll loop stores a second event when the corroboration flag flips;
    the collection counts flights, not stored rows."""
    for corroborated in (True, None):
        history_db.record_runway_event(
            conn, ts=(NOW - timedelta(days=2, seconds=0 if corroborated else -30)).isoformat(), hex="abc123",
            callsign="AFR12", airline=RARE_AIRLINE, confirmed_state="arriving",
            corroborated=corroborated)
    seed_row = _by_name(_collect(conn)[0])[
        collection.render_text.display_airline_name(RARE_AIRLINE)]
    stored = conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0]
    assert stored == 2
    assert seed_row.times_seen == 1


def test_the_same_aircraft_on_another_day_is_another_sighting(conn):
    for days in (3, 2):
        history_db.record_runway_event(
            conn, ts=_iso(days), hex="abc123", callsign="AFR12",
            airline=RARE_AIRLINE, confirmed_state="arriving")
    row = _by_name(_collect(conn)[0])[collection.render_text.display_airline_name(RARE_AIRLINE)]
    assert row.times_seen == 2


def test_airline_text_is_matched_by_normalised_key(conn, seed):
    seed.event(RARE_AIRLINE.upper(), 3)
    seed.event(RARE_AIRLINE.lower(), 2)
    entries, summary = _collect(conn)
    row = _by_name(entries)[collection.render_text.display_airline_name(RARE_AIRLINE)]
    assert row.times_seen == 2
    assert all(entry.curated for entry in entries)
    assert summary.spotted == 1


def test_a_renamed_curated_airline_keeps_its_card_and_history(conn, seed):
    overrides = {"AFR": {"airline_name": "Frenchy Air", "created_at": "2026-01-01"}}
    seed.event("Frenchy Air", 3)
    seed.event("Air France", 2)
    entries, _summary = _collect(conn, overrides=overrides)
    row = _by_name(entries)["Frenchy Air"]
    assert row.curated and row.times_seen == 2
    assert not any(entry.name == "Air France" for entry in entries)


def test_hostile_text_is_kept_verbatim_for_the_page_to_escape(conn, seed):
    seed.event("<script>alert(1)</script>", 1, callsign="<b>x</b>")
    entries, _summary = _collect(conn)
    extra = [entry for entry in entries if not entry.curated]
    assert extra[0].name == "<script>alert(1)</script>"
    assert extra[0].slug == "script-alert-1-script"
    assert extra[0].callsigns == ("<b>x</b>",)


def test_the_read_model_writes_nothing(conn, seed):
    _seed_history(seed)
    before = conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0]
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    _collect(conn)
    assert conn.execute("SELECT COUNT(*) FROM runway_events").fetchone()[0] == before
    assert {r[0] for r in conn.execute("SELECT name FROM sqlite_master")} == tables
    assert not conn.in_transaction


def test_sightings_across_frames_are_merged_newest_first_and_counted_together(tmp_path):
    now = datetime.now(timezone.utc)
    dirs = []
    for index, (days, hex_code) in enumerate(((1, "aa0001"), (3, "bb0002"))):
        state_dir = str(tmp_path / ("frame%d" % index))
        with history_db.open_db(state_dir) as frame_conn:
            history_db.record_runway_event(
                frame_conn, ts=(now - timedelta(days=days)).isoformat(), hex=hex_code,
                callsign="AFR%03d" % index, aircraft_type="A320",
                confirmed_state="departing", airline="Air France")
        dirs.append(state_dir)
    merged = collection.sightings_across(dirs + [dirs[0], "", str(tmp_path / "missing" / "x")])
    assert [row["hex"] for row in merged] == ["aa0001", "bb0002"]
    entries, _summary = collection.collection_from_events(merged, now.isoformat())
    france = next(entry for entry in entries if entry.name == "Air France")
    assert france.times_seen == 2
