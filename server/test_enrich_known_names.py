# SPDX-License-Identifier: AGPL-3.0-only
"""The read accessor of the airlines known by name only."""
from server.plane import enrich


def test_pairs_are_an_immutable_sorted_tuple_of_prefix_and_name():
    pairs = enrich.names_without_artwork()
    assert isinstance(pairs, tuple)
    assert pairs
    names = [name.casefold() for _prefix, name in pairs]
    assert names == sorted(names)
    assert ("THY", "Turkish Airlines") in pairs


def test_the_accessor_never_hands_out_the_lookup_table():
    before = dict(enrich._ICAO_AIRLINE_NAMES_WITHOUT_ARTWORK)
    enrich.names_without_artwork()
    assert enrich._ICAO_AIRLINE_NAMES_WITHOUT_ARTWORK == before
    assert enrich.names_without_artwork() == enrich.names_without_artwork()
    assert all(isinstance(pair, tuple) for pair in enrich.names_without_artwork())
