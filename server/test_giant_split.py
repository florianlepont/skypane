"""Behaviour tests for the automatic destination splitter."""
import re

import pytest

from server.plane.render.giant import split

WORST_STRETCH_BOUND = 1.2

NAMES = [
    "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Strasbourg",
    "Montpellier", "Bordeaux", "Lille", "Rennes", "Reims", "Le Havre",
    "Saint-Etienne", "Toulon", "Grenoble", "Dijon", "Angers", "Nimes",
    "Clermont-Ferrand", "Brest", "Limoges", "Tours", "Amiens", "Metz",
    "Perpignan", "Besancon", "Orleans", "Rouen", "Caen", "Nancy", "Pau",
    "Aix", "Ajaccio", "Bastia", "Biarritz", "Villefranche-sur-Saone",
    "Aix-en-Provence", "Boulogne-sur-Mer", "Saint-Denis de la Reunion",
    "London", "Barcelona", "Madrid", "Lisbon", "Frankfurt", "Munich",
    "Amsterdam", "Brussels", "Casablanca", "Marrakech", "New York",
    "Palma de Mallorca", "Rome", "Milan", "Vienna", "Copenhagen",
    "Stockholm", "Edinburgh", "Dublin", "Istanbul", "Tel Aviv",
    "Las Palmas de Gran Canaria", "Reykjavik", "Geneve", "Zurich",
    "Saint–Malo", "Cote d'Azur", "Compagnie Nationale Royale Air Maroc Express",
    "Air France", "Royal Air Maroc", "Tunisair Express", "Lufthansa CityLine",
    "Ibiza", "Faro", "Oslo", "Bergen", "Goteborg", "Malaga", "Valencia",
    "Évian-les-Bains", "Île d'Yeu", "Sevilla", "Praha", "Budapest",
]


def test_name_list_is_large_enough_and_has_required_cases():
    assert len(NAMES) >= 60
    for required in ("Marseille", "Villefranche-sur-Saone", "Pau", "Aix",
                     "Compagnie Nationale Royale Air Maroc Express"):
        assert required in NAMES


@pytest.mark.parametrize("name,lines", [
    ("New York", ("NEW", "YORK")),
    ("Saint-Etienne", ("SAINT", "ETIENNE")),
    ("Palma de Mallorca", ("PALMA DE", "MALLORCA")),
    ("Clermont-Ferrand", ("CLERMONT", "FERRAND")),
    ("Nice", ("NI", "CE")),
    ("Lyon", ("LY", "ON")),
    ("Toulouse", ("TOUL", "OUSE")),
    ("Bordeaux", ("BORD", "EAUX")),
    ("London", ("LON", "DON")),
    ("Metz", ("ME", "TZ")),
    ("Pau", ("PAU",)),
    ("Aix", ("AIX",)),
    ("Villefranche-sur-Saone", ("VILLEFRANCHE", "SUR", "SAONE")),
])
def test_expected_splits(name, lines):
    assert split.split_destination(name, split.PORTRAIT).lines == lines


def test_landscape_is_one_line_with_hyphens_as_spaces():
    out = split.split_destination("Saint-Etienne", split.LANDSCAPE)
    assert out.lines == ("SAINT ETIENNE",)
    assert not out.shrink_block


def test_normalise_collapses_and_uppercases():
    assert split.normalise_destination("  saint–etienne —  x ") == "SAINT-ETIENNE - X"
    assert split.normalise_destination("évian") == "ÉVIAN"


def test_normalise_caps_length():
    assert len(split.normalise_destination("a" * 500)) == split.MAX_NAME_CHARS


def test_invented_name_uses_the_same_rule():
    out = split.split_destination("Zzz Qqq Xxx Yyy", split.PORTRAIT)
    assert out.lines == ("ZZZ QQQ", "XXX YYY")


def test_empty_and_separator_only_names_give_no_lines():
    assert split.split_destination("", split.PORTRAIT).lines == ()
    assert split.split_destination(" - ", split.PORTRAIT).lines == ()


def test_squeezed_names_ask_for_a_shorter_block():
    out = split.split_destination("Compagnie Nationale Royale Air Maroc Express")
    assert out.shrink_block
    assert not split.split_destination("New York").shrink_block


def _words(name):
    return [w for w in re.split(r"[\s\-]+", split.normalise_destination(name)) if w]


@pytest.mark.parametrize("name", NAMES)
def test_split_properties(name):
    normalised = split.normalise_destination(name)
    lines = split.split_destination(name, split.PORTRAIT).lines
    letters = re.sub(r"[\s\-]", "", normalised)
    assert "".join(re.sub(r"[\s\-]", "", x) for x in lines) == letters
    if len(letters) <= split.SHORT_NAME_LETTERS:
        assert len(lines) == 1
        return
    assert 2 <= len(lines) <= split.MAX_LINES
    assert all(len(x.replace(" ", "")) >= 2 for x in lines)
    words = _words(name)
    if len(words) > 1:
        # No word is cut: every line is a run of whole words.
        assert [w for x in lines for w in x.split(" ")] == words
    stretches = split._log_stretches(lines)
    assert max(abs(s) for s in stretches) < WORST_STRETCH_BOUND


@pytest.mark.parametrize("name", NAMES)
def test_landscape_property(name):
    lines = split.split_destination(name, split.LANDSCAPE).lines
    assert len(lines) == 1
    assert lines[0] == split.normalise_destination(name).replace("-", " ")


def test_split_is_deterministic():
    assert split.split_destination("Marseille") == split.split_destination("marseille")
