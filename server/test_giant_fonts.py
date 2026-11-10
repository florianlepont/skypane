"""Behaviour tests for the giant-lettering Anton loader."""
import hashlib
import os
import re

import pytest

from server.plane.render.giant import fonts

FONT_DIR = os.path.dirname(fonts.ANTON_PATH)


def test_anton_is_cached_and_sized():
    assert fonts.anton(100) is fonts.anton(100)
    assert fonts.anton(100) is not fonts.anton(50)
    assert fonts.anton(100).size == 100


def test_cap_height_ignores_accents_and_scales():
    assert fonts.cap_height(200) > fonts.cap_height(100) > 0
    assert 0.5 * 100 < fonts.cap_height(100) < 1.2 * 100


@pytest.mark.parametrize("text", ["SAINT-ÉTIENNE", "PARIS", "ÈÇŒßñ", "Aix en Provence", ""])
def test_supports_latin(text):
    assert fonts.supports(text)


@pytest.mark.parametrize("text", ["МОСКВА", "ΑΘΗΝΑ", "東京", "PARIS МОСКВА"])
def test_rejects_other_scripts(text):
    assert not fonts.supports(text)


def test_ascii_fallback():
    assert fonts.ascii_fallback("Saint-Étienne") == "Saint-Etienne"
    assert fonts.ascii_fallback("東京") is None
    assert fonts.ascii_fallback("") is None
    assert fonts.ascii_fallback("Zürich 東京") == "Zurich"


def test_vendored_files_match_recorded_digests():
    vendor = open(os.path.join(FONT_DIR, "VENDOR.md"), encoding="utf-8").read()
    section = vendor[vendor.index("## `Anton-Regular.ttf`"):]
    for name in ("Anton-Regular.ttf", "Anton-OFL.txt"):
        digest = hashlib.sha256(open(os.path.join(FONT_DIR, name), "rb").read()).hexdigest()
        assert re.search(r"`%s`:\s+`%s`" % (re.escape(name), digest), section)
