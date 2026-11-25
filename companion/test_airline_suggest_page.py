"""The Airlines editor's rows with a suggested airline name, served over HTTP:
the Suggestion tag, Edit and the check, the pending lookup, the silent
fallback to "Name it", the Edit dialog, and the guarantee that rendering a
page never calls the service or writes a file."""
import html
import re

import pytest

from companion.test_airline_suggest_helpers import EDITOR, make_rig, rig_with_gaps
from server.plane import airline_suggest as ais

HOSTILE = 'Ocean "Air" & Co'


@pytest.fixture
def rig(tmp_path, monkeypatch):
    yield from rig_with_gaps(tmp_path, monkeypatch)


def _page(rig, who="admin", lang=None):
    status, _h, body = rig.get(who, rig.frame + EDITOR, lang=lang)
    assert status == 200
    return body


def _row(page, prefix):
    """The `<tbody>` of one unidentified prefix."""
    rows = re.findall(r'<tbody class="airline-group airline-group--gap".*?</tbody>', page, re.S)
    assert rows
    return next(r for r in rows if '<span class="airlines-gap__prefix mono">%s</span>' % prefix in r)


def test_a_cached_suggestion_shows_the_tag_the_name_edit_and_a_check_form(rig):
    rig.write_cache({"OCN": ("suggested", HOSTILE)})
    row = _row(_page(rig), "OCN")
    assert 'class="airlines-tag"' in row and ">Suggestion<" in row
    assert '<span class="airlines-gap__name">%s</span>' % html.escape(HOSTILE) in row
    assert HOSTILE not in row.replace(html.escape(HOSTILE), "")
    assert re.search(r'<a href="#name-prefix-0" class="airlines-gap__edit"[^>]*data-modal-open>Edit</a>', row)
    form = re.search(r'<form method="post" action="([^"]+)" class="airlines-gap__check">(.*?)</form>', row, re.S)
    assert form and form.group(1) == rig.frame + "/airlines/resolve"
    for name, value in (("prefix", "OCN"), ("inline", "1"), ("airline_name", html.escape(HOSTILE))):
        assert '<input type="hidden" name="%s" value="%s">' % (name, value) in form.group(2)
    assert 'name="csrf_token"' in form.group(2)
    label = html.escape("Use the suggestion %s for OCN" % HOSTILE)
    assert 'aria-label="%s"' % label in form.group(2)
    assert "Name it" not in row.split("<dialog")[0]
    assert "data-suggest-prefix" not in row


def test_the_french_page_speaks_french(rig):
    rig.write_cache({"OCN": ("suggested", "Oceanair")})
    row = _row(_page(rig, lang="fr"), "OCN")
    assert ">Suggestion<" in row and ">Modifier</a>" in row
    assert 'aria-label="Utiliser la suggestion Oceanair pour OCN"' in row
    assert "Modifier le nom" in row and "Suggéré automatiquement à partir de l’indicatif" in row
    assert "Retirer la suggestion" in row


def test_a_hand_edited_cache_with_markup_in_a_name_shows_nothing(rig):
    rig.write_cache({"OCN": ("suggested", "<script>alert(1)</script>")})
    page = _page(rig)
    assert "alert(1)" not in page
    row = _row(page, "OCN")
    assert 'class="airlines-tag"' not in row and "airlines-gap__name" not in row


def test_a_prefix_never_asked_is_pending_and_keeps_name_it(rig):
    rig.write_cache({"ITI": ("suggested", "Itavia Express")})
    row = _row(_page(rig), "OCN")
    assert 'data-suggest-prefix="OCN" data-suggest-index="0"' in row
    assert 'data-suggest-url="%s/airlines/suggest"' % rig.frame in row
    assert 'class="airlines-tag airlines-tag--pending" role="status"' in row and "Looking for a name" in row
    assert re.search(r'<a href="#name-prefix-0"[^>]*class="btn btn--secondary"[^>]*>Name it</a>', row)


def test_only_three_rows_of_a_page_are_pending(rig):
    rig.seed_gaps(("OCN", "ITI", "ZLN", "CMA", "QQQ", "RRR"))
    page = _page(rig)
    assert page.count("data-suggest-prefix=") == 3
    assert page.count("Looking for a name") == 3


@pytest.mark.parametrize("entry", [
    ("none",), ("rejected",), ("accepted",), ("edited",), ("failed",)])
def test_a_decided_or_failed_prefix_looks_like_name_it_only(rig, entry):
    plain = _row(_page(rig), "OCN")  # pending now
    rig.write_cache({"OCN": entry})
    if entry[0] == "failed":
        doc = ais._load(rig.root)
        doc[0]["OCN"]["failed_until"] = 4_000_000_000.0
        ais._save(rig.root, doc[0], doc[1])
    row = _row(_page(rig), "OCN")
    assert "airlines-tag" not in row and "data-suggest" not in row and "Looking" not in row
    assert plain != row
    assert re.search(r'class="btn btn--secondary"[^>]*>Name it</a>', row)


def test_an_expired_failure_is_asked_again(rig):
    rig.write_cache({"OCN": ("failed",)})
    assert 'data-suggest-prefix="OCN"' in _row(_page(rig), "OCN")


def test_with_the_service_off_the_page_is_the_plain_manual_flow(tmp_path, monkeypatch):
    off = make_rig(tmp_path, monkeypatch, key=None)
    try:
        off.seed_gaps()
        before = _page(off)
        off.write_cache({"OCN": ("suggested", "Oceanair"), "ITI": ("none",)})
        after = _page(off)
        assert after == before
        for marker in ("airlines-tag", "data-suggest", "airlines-check", "Looking for a name"):
            assert marker not in after
        assert after.count(">Name it</a>") == 4
        assert off.client.bodies == []
    finally:
        off.server.stop()


def test_the_edit_dialog_has_the_hint_and_remove_only_for_a_suggestion(rig):
    rig.write_cache({"OCN": ("suggested", "Oceanair"), "ITI": ("none",)})
    page = _page(rig)
    suggested = _row(page, "OCN")
    assert 'value="Oceanair"' in suggested and "OCN · Edit the name" in suggested
    assert "Suggested automatically from the callsign. Check it before using it." in suggested
    assert re.search(
        r'<button type="submit" class="btn btn--ghost airlines-remove" '
        r'formaction="%s/airlines/suggest/reject" formnovalidate>Remove the suggestion</button>'
        % re.escape(rig.frame), suggested)
    plain = _row(page, "ITI")
    assert "Remove the suggestion" not in plain and "Suggested automatically" not in plain
    assert "ITI · Name the airline" in plain


def test_rendering_a_page_never_calls_the_service_and_never_writes(rig):
    rig.write_cache({"OCN": ("suggested", "Oceanair")})
    before = rig.files()
    for path in (rig.frame + EDITOR, EDITOR, rig.frame + EDITOR + "?types=all", "/fleet", "/airlines"):
        rig.get("admin", path)
    assert rig.client.bodies == []
    assert rig.files() == before


def test_a_page_without_scripts_still_names_through_the_check(rig):
    rig.write_cache({"OCN": ("suggested", "Oceanair")})
    status, headers, _b = rig.post(
        "admin", rig.frame + "/airlines/resolve",
        {"prefix": "OCN", "airline_name": "Oceanair", "inline": "1"})
    assert status == 303 and "flash=manual_resolved" in headers["Location"]
    assert 'data-suggest-prefix="OCN"' not in _page(rig)
