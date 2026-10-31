"""Every credited source has a matching section in COMPLIANCE.md, and the
served credits page carries the OurAirports description in both languages.
"""
import os
import re

from companion import credits_page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OURAIRPORTS_EN = (
    "Open airport data: it names airports and places and orients the "
    "runways each frame can follow. Credited as a courtesy.")
OURAIRPORTS_FR = (
    "Données aéroportuaires ouvertes : elles nomment les aéroports et "
    "situent et orientent les pistes que chaque cadre peut suivre. "
    "Citées par courtoisie.")


def _headings(text):
    return [m.group(1).lower()
            for m in re.finditer(r"^## (.+)$", text, re.MULTILINE)]


def sources_without_heading(sources, compliance_text):
    """Names of credited sources that have no '## ' heading in the text."""
    headings = _headings(compliance_text)
    return [s["name"] for s in sources
            if not any(s["name"].lower() in h for h in headings)]


def _compliance_text():
    with open(os.path.join(ROOT, "COMPLIANCE.md"), encoding="utf-8") as handle:
        return handle.read()


def test_every_credited_source_has_a_compliance_heading():
    sources = credits_page.load_credits()
    assert sources_without_heading(sources, _compliance_text()) == []


def test_a_missing_heading_is_reported():
    sources = credits_page.load_credits()
    text = _compliance_text().replace("## OurAirports", "## Something else")
    assert sources_without_heading(sources, text) == ["OurAirports"]


def test_credits_page_shows_the_ourairports_description(app_server_in_process):
    from companion_app_server import http_request
    for lang, expected in (("en", OURAIRPORTS_EN), ("fr", OURAIRPORTS_FR)):
        status, _headers, body = http_request(
            app_server_in_process.url("/credits"),
            extra_headers={"Accept-Language": lang})
        assert status == 200
        assert expected in body.decode("utf-8")
