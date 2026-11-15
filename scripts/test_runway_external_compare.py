"""Tests for scripts/runway_external_compare.py: sampling and reference join."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import runway_external_compare as rec  # noqa: E402


def _row(ts, hex_, callsign, state, airline="Air France", origin="ORY", dest="NCE"):
    return {"ts": ts, "hex": hex_, "callsign": callsign, "confirmed_state": state,
            "airline": airline, "origin": origin, "destination": dest}


def _many():
    rows = []
    for day in range(1, 11):
        for i in range(30):
            state = "departing" if i % 2 else "arriving"
            airline = "Transavia France" if i % 3 == 0 else "Air France"
            rows.append(_row(f"2026-11-{day:02d}T{(i % 20) + 4:02d}:00:00+00:00",
                             f"{day:02x}{i:04x}", f"XX{day}{i}", state, airline))
    return rows


def test_rows_of_one_flight_collapse_into_one_event():
    rows = [_row("2026-11-01T05:00:00+00:00", "a", "AFR1", "departing"),
            _row("2026-11-01T05:01:00+00:00", "a", "AFR1", "departing"),
            _row("2026-11-01T09:00:00+00:00", "a", "AFR1", "departing")]
    events = rec.build_events(rows)
    assert [e["ts"] for e in events] == ["2026-11-01T05:00:00+00:00",
                                         "2026-11-01T09:00:00+00:00"]


def test_sampling_is_reproducible_and_covers_every_day():
    events = rec.build_events(_many())
    first = rec.stratified_sample(events, 40, seed=7)
    second = rec.stratified_sample(events, 40, seed=7)
    assert first == second
    assert len(first) == 40
    assert {e["ts"][:10] for e in first} == {e["ts"][:10] for e in events}
    assert rec.stratified_sample(events, 40, seed=8) != first


def test_airline_family_separates_low_cost_from_legacy():
    assert rec.airline_family("Transavia France") == "low-cost"
    assert rec.airline_family("Air France") == "legacy"


def _ref(ts, callsign, direction, **extra):
    base = {"callsign": callsign, "ts": ts, "direction": direction, "runway": "3",
            "source": "example.org"}
    base.update(extra)
    return base


def _ev(callsign="AFR1", state="departing", ts="2026-11-01T10:00:00+00:00"):
    return {"ts": ts, "hex": "abc", "callsign": callsign, "confirmed_state": state,
            "origin": "ORY", "destination": "NCE", "airline": "Air France"}


def _verdict(sample, refs, events=None):
    out = rec.classify(sample, refs, events or sample, window_min=15)
    return [v["verdict"] for v in out["verdicts"]], out


def test_match():
    got, _ = _verdict([_ev()], [_ref("2026-11-01T10:05:00+00:00", "AFR1", "departing")])
    assert got == ["match"]


def test_direction_mismatch():
    got, _ = _verdict([_ev()], [_ref("2026-11-01T10:05:00+00:00", "AFR1", "arriving")])
    assert got == ["direction-mismatch"]


def test_route_mismatch_is_separate_from_direction():
    ref = _ref("2026-11-01T10:05:00+00:00", "AFR1", "departing", destination="LYS")
    got, _ = _verdict([_ev()], [ref])
    assert got == ["route-mismatch"]


def test_hex_agreement_matches_when_callsigns_differ():
    ref = _ref("2026-11-01T10:05:00+00:00", "AF123", "departing", hex="ABC")
    got, _ = _verdict([_ev()], [ref])
    assert got == ["match"]


def test_unverifiable_without_reference_or_outside_window():
    got, _ = _verdict([_ev()], [_ref("2026-11-01T12:00:00+00:00", "AFR1", "departing")])
    assert got == ["unverifiable-no-reference"]


def test_missed_aircraft_is_reference_row_without_any_event():
    refs = [_ref("2026-11-01T10:05:00+00:00", "AFR1", "departing"),
            _ref("2026-11-01T11:00:00+00:00", "BAW9", "arriving"),
            _ref("2026-12-01T11:00:00+00:00", "BAW9", "arriving")]
    _, out = _verdict([_ev()], refs)
    assert [m["callsign"] for m in out["missed"]] == ["BAW9"]
    assert out["missed"][0]["ts"].startswith("2026-11-01")


def test_other_runway_reference_rows_are_ignored():
    refs = [_ref("2026-11-01T10:05:00+00:00", "AFR1", "departing", runway="26")]
    got, out = _verdict([_ev()], refs)
    assert got == ["unverifiable-no-reference"]
    assert out["missed"] == []


def test_reference_can_be_read_from_csv(tmp_path):
    path = tmp_path / "ref.csv"
    path.write_text("callsign,ts,direction,runway,source\n"
                    "AFR1,2026-11-01T10:05:00Z,departing,3,example.org\n"
                    "AFR2,2026-11-01T11:05:00Z,arriving,,example.org\n", encoding="utf-8")
    rows = rec._read_jsonl(str(path))
    assert rows[0]["callsign"] == "AFR1"
    assert "runway" not in rows[1]
