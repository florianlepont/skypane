# SPDX-License-Identifier: AGPL-3.0-only
"""The Auth0 Management variables in deploy/skypane.env.example are
documented as commented-out placeholders and never carry a real value."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_EXAMPLE = _REPO_ROOT / "deploy" / "skypane.env.example"
_README = _REPO_ROOT / "deploy" / "README.md"

_NAMES = (
    "SKYPANE_AUTH0_MGMT_CLIENT_ID",
    "SKYPANE_AUTH0_MGMT_CLIENT_SECRET",
    "SKYPANE_AUTH0_DB_CONNECTION",
    "SKYPANE_AUTH0_DB_CONNECTION_ID",
    "SKYPANE_AUTH0_CUSTOM_DOMAIN",
)


def _assignments(text):
    """name -> values for every `NAME=value` found, active or commented."""
    found = {}
    for raw in text.splitlines():
        line = raw.lstrip("# ").strip().lstrip("- ").strip("`")
        name, sep, value = line.partition("=")
        if sep and name in _NAMES:
            found.setdefault(name, []).append(value.split("`")[0].split(" ")[0])
    return found


def test_management_variables_are_commented_out_placeholders():
    text = _ENV_EXAMPLE.read_text()
    for raw in text.splitlines():
        assert not raw.startswith(_NAMES), "must stay commented out: " + raw
    found = _assignments(text)
    assert set(found) == set(_NAMES)
    for values in found.values():
        assert all(v.startswith("<") and v.endswith(">") for v in values)


def test_readme_documents_minimal_scopes_and_placeholders_only():
    readme = _README.read_text()
    assert "create:users" in readme and "create:user_tickets" in readme
    found = _assignments(readme)
    assert set(found) == set(_NAMES)
    for values in found.values():
        assert all(v.startswith("<") and v.endswith(">") for v in values)
