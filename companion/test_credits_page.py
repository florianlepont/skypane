"""Tests for the public credits page: the data file validator, the markup,
and (below) the served route.
"""
import copy
import json

import pytest

from companion import credits_page, prefs


def _shipped():
    with open(credits_page.DEFAULT_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _write(tmp_path, data):
    path = tmp_path / "credits.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _source(data, source_id):
    return next(s for s in data["sources"] if s["id"] == source_id)


def test_shipped_file_lists_the_four_sources():
    sources = credits_page.load_credits()
    assert [s["id"] for s in sources] == [
        "adsbfi", "adsblol", "adsbdb", "ourairports"]


def _broken_variants():
    def unknown_version(data):
        data["version"] = 2

    def missing_id(data):
        data["sources"] = [s for s in data["sources"] if s["id"] != "adsbdb"]

    def duplicate_id(data):
        data["sources"].append(copy.deepcopy(data["sources"][0]))

    def extra_key(data):
        data["sources"][0]["logo"] = "x.png"

    def http_url(data):
        _source(data, "adsblol")["url"] = "http://adsb.lol"

    def javascript_url(data):
        _source(data, "adsblol")["url"] = "javascript:alert(1)"

    def no_host(data):
        _source(data, "adsblol")["url"] = "https://"

    def no_description_en(data):
        del _source(data, "adsbdb")["description"]["en"]

    def no_description_fr(data):
        del _source(data, "adsbdb")["description"]["fr"]

    def no_description(data):
        del _source(data, "adsbdb")["description"]

    def wrong_adsbfi_host(data):
        _source(data, "adsbfi")["url"] = "https://example.com"

    def extra_top_level(data):
        data["note"] = "x"

    return {
        "unknown_version": unknown_version,
        "missing_id": missing_id,
        "duplicate_id": duplicate_id,
        "extra_key": extra_key,
        "http_url": http_url,
        "javascript_url": javascript_url,
        "no_host": no_host,
        "no_description_en": no_description_en,
        "no_description_fr": no_description_fr,
        "no_description": no_description,
        "wrong_adsbfi_host": wrong_adsbfi_host,
        "extra_top_level": extra_top_level,
    }


@pytest.mark.parametrize("name", sorted(_broken_variants()))
def test_a_malformed_file_is_rejected(tmp_path, name):
    data = _shipped()
    _broken_variants()[name](data)
    with pytest.raises(ValueError):
        credits_page.load_credits(_write(tmp_path, data))


def test_invalid_json_is_rejected(tmp_path):
    path = tmp_path / "credits.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        credits_page.load_credits(str(path))


def _render(lang, sources=None):
    prefs.set_request_prefs(lang=lang)
    try:
        return credits_page.credits_body(sources)
    finally:
        prefs.set_request_prefs(lang="en")


def test_markup_links_adsbfi_and_uses_safe_rel():
    html = _render("en")
    assert 'href="https://adsb.fi"' in html
    assert 'rel="noopener noreferrer"' in html
    for name in ("adsb.fi", "adsb.lol", "adsbdb", "OurAirports"):
        assert name in html
    assert "javascript:" not in html


def test_language_selects_the_description():
    sources = credits_page.load_credits()
    english = _render("en")
    french = _render("fr")
    assert sources[0]["description"]["en"][:30] in english
    assert sources[0]["description"]["fr"][:30] in french
    assert sources[0]["description"]["fr"][:30] not in english


def test_text_is_escaped(tmp_path):
    data = _shipped()
    _source(data, "adsbdb")["description"]["en"] = "<script>alert(1)</script>"
    _source(data, "adsbdb")["name"] = '"><img src=x onerror=1>'
    sources = credits_page.load_credits(_write(tmp_path, data))
    html = _render("en", sources)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x" not in html
