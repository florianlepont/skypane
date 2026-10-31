"""Deterministic aircraft lattice and comparison helpers for detection tests.

Fully deterministic: the same call always yields the same records. Positions come
from detect.runway_axis so the edge bands sit at exact along-track and
cross-track values (a gate edge, one metre inside, one metre outside) rather
than at guessed latitudes and longitudes.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from server.plane import detect

LATTICE_LAT_STEPS = 40
LATTICE_LON_STEPS = 70
LATTICE_MARGIN_DEG = 1e-3
ALTITUDES: tuple[Any, ...] = (450, 2999, 3000, 3001, "ground", None)
GROUP_SIZE = 8


def _track_values(bearing: float) -> tuple[Any, ...]:
    return (bearing, bearing + 180.0, bearing + 29.0, bearing + 31.0, 0.0, "missing")


def _position(axis: dict[str, Any], along: float, cross: float) -> tuple[float, float]:
    x = along * axis["ux"] - cross * axis["uy"]
    y = along * axis["uy"] + cross * axis["ux"]
    lat = axis["lat0"] + y / detect._M_PER_DEG_LAT
    lon = axis["lon0"] + x / axis["lon_scale"]
    return lat, lon


def _steps(low: float, high: float, count: int) -> list[float]:
    return [low + (high - low) * i / (count - 1) for i in range(count)]


def _lattice_positions(doc: dict[str, Any]) -> list[tuple[float, float]]:
    bbox = doc["bbox"]
    lats = _steps(
        bbox["lat_min"] - LATTICE_MARGIN_DEG, bbox["lat_max"] + LATTICE_MARGIN_DEG, LATTICE_LAT_STEPS
    )
    lons = _steps(
        bbox["lon_min"] - LATTICE_MARGIN_DEG, bbox["lon_max"] + LATTICE_MARGIN_DEG, LATTICE_LON_STEPS
    )
    return [(lat, lon) for lat in lats for lon in lons]


def _bbox_edge_positions(reference_bbox: dict[str, float]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    eps = 1e-5
    lat_edges = [reference_bbox["lat_min"], reference_bbox["lat_max"]]
    lon_edges = [reference_bbox["lon_min"], reference_bbox["lon_max"]]
    lon_span = _steps(lon_edges[0] - 0.01, lon_edges[1] + 0.01, 120)
    lat_span = _steps(lat_edges[0] - 0.01, lat_edges[1] + 0.01, 60)
    for lat in lat_edges:
        for d in (-eps, 0.0, eps):
            points += [(lat + d, lon) for lon in lon_span]
    for lon in lon_edges:
        for d in (-eps, 0.0, eps):
            points += [(lat, lon + d) for lat in lat_span]
    return points


def _band_positions(axis: dict[str, Any]) -> list[tuple[float, float]]:
    """Positions at every gate edge: corridor, extension, pavement, bbox."""
    length = axis["length_m"]
    along_line = [-2600.0 + 50.0 * i for i in range(int((length + 5200.0) // 50) + 1)]
    along_line += [0.0, length, -2500.0, length + 2500.0]
    cross_line = [-600.0 + 25.0 * i for i in range(49)]
    tip_cross = [float(c) for c in range(-120, 121, 10)]
    points: list[tuple[float, float]] = []
    for edge in (499.0, 500.0, 501.0, 74.0, 75.0, 76.0):
        for sign in (1.0, -1.0):
            points += [_position(axis, a, sign * edge) for a in along_line]
    for edge in (-2501.0, -2500.0, -2499.0, -76.0, -75.0, -74.0):
        points += [_position(axis, edge, c) for c in cross_line]
    for edge in (length + 2499.0, length + 2500.0, length + 2501.0,
                 length + 74.0, length + 75.0, length + 76.0):
        points += [_position(axis, edge, c) for c in cross_line]
    for edge in (-2500.0, length + 2500.0):
        points += [_position(axis, edge, c) for c in tip_cross]
    return points


def sweep_cells(doc: dict[str, Any], runway_id: str, bbox_edges: dict[str, float] | None = None
                ) -> Iterator[dict[str, Any]]:
    """Aircraft records for the lattice plus the dense edge bands.

    `doc` supplies the lattice extent and the runway axis; `bbox_edges` (the
    other document's bbox, when it differs) adds bands along its edges.
    """
    axis = detect.runway_axis(doc, runway_id=runway_id)
    if axis is None:
        raise ValueError("document has no axis for the runway")
    positions = _lattice_positions(doc)
    positions += _band_positions(axis)
    positions += _bbox_edge_positions(doc["bbox"])
    if bbox_edges:
        positions += _bbox_edge_positions(bbox_edges)
    index = 0
    for lat, lon in positions:
        for track in _track_values(axis["bearing_deg"]):
            for altitude in ALTITUDES:
                record: dict[str, Any] = {
                    "hex": "%06x" % index,
                    "flight": "SW%04d " % (index % 10000),
                    "lat": lat,
                    "lon": lon,
                    "alt_baro": altitude,
                    "gs": 120.0,
                    "seen_pos": float(index % 7),
                }
                if track != "missing":
                    record["track"] = track
                yield record
                index += 1


def compare(legacy_doc: dict[str, Any], generic_doc: dict[str, Any], runway_id: str,
            records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Records whose candidacy or tagged geometry differs between documents."""
    left = {r["hex"]: r for r in detect.runway_candidates(records, legacy_doc, runway_id=runway_id)}
    right = {r["hex"]: r for r in detect.runway_candidates(records, generic_doc, runway_id=runway_id)}
    by_hex = {r["hex"]: r for r in records}
    return [by_hex[h] for h in sorted(set(left) | set(right)) if left.get(h) != right.get(h)]


def _without_seen_pos(selection: dict[str, Any] | None) -> dict[str, Any] | None:
    if selection is None:
        return None
    return {k: v for k, v in selection.items() if k != "seen_pos"}


def compare_selections(legacy_doc: dict[str, Any], generic_doc: dict[str, Any], runway_id: str,
                       records: list[dict[str, Any]], group_size: int = GROUP_SIZE
                       ) -> list[list[dict[str, Any]]]:
    """Groups of records whose normalised selection differs between documents.

    Each group is selected single-provider and two-provider (both orders),
    the second provider seeing the reversed group minus its first record.
    """
    differing: list[list[dict[str, Any]]] = []
    for start in range(0, len(records), group_size):
        group = records[start:start + group_size]
        second = group[::-1][:-1]
        for results in ([("a", group)], [("a", group), ("b", second)], [("b", second), ("a", group)]):
            outcomes = [
                _without_seen_pos(
                    detect.select_from_provider_results(results, doc, runway_id=runway_id))
                for doc in (legacy_doc, generic_doc)
            ]
            if outcomes[0] != outcomes[1]:
                differing.append(group)
                break
    return differing
