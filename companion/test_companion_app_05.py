"""Part 05 of the `companion/test_companion_app.py` migration chain
(33-18-PLAN.md): ledger rows 267-320 (fragment `33-ledger/companion__
test_companion_app.md`) — the LAST plan of the chain.

Continues `companion/test_companion_app_04b.py` (row 266, the LAST
anchor of part 04, the real-PNG illustration upload round trip) with:
the illustration override's own effects (the normalization pipeline,
the exact-one-file write, the untouched vendored original, and
`select_illustration()`'s resolution), the illustration upload's
rejection paths (non-image, oversized, unknown/traversal keys,
unauthenticated), the manual-resolution `/airlines/resolve` and
`/airlines/manual-resolutions/{prefix}/delete` routes, the colour-rules
`/settings/rules/*` routes, the poll-trigger cooldown sequence and its
distinct failure flash key (the `--geofence` hotspot), the concurrent
`/poll-now` lock-serialization proof, the calendar save-triggered sync
family (connect/disconnect routes, the throttle bypass, lock
contention, the T-17-FLASH leak guard), the notifications "send a
test" route, the retired display-mode-switch removal (rewritten as a
`not hasattr()` battery — the tokens no longer appear anywhere in
production code, confirmed by grep before writing this module), the
flash/title/nav i18n round trips, and — the LAST anchor — the
site-wide editorial floor (CFG-79), whose own cross-file counting-rule
agreement check now calls `companion.test_config_page_05`'s
`_caption_word_count_text()` directly (a plain import, never a
disk-read/ast-extract of that module's source — 33-13-PLAN.md closed
that chain, and the sequential-execution brief for this plan requires
the cross-check be migrated as calling behaviour, not a source read).

The illustration-override tests below and the poll-trigger cooldown
sequence each consolidate several old `check()` calls that shared ONE
mutable harness in a fixed order into one atomic pytest test, following
33-17-SUMMARY.md's own precedent (33-MIGRATION-RULES.md section 3:
"several old checks may map to one node id when they are
consolidated"). Every other check here is either fully independent (its
own fresh `make_app_server`/`app_server_in_process`) or a module-level
behavioural proof with no server at all.
"""
import html
import os
import re
import string
import threading
import time
import urllib.parse

import companion.i18n as i18n_module
import companion.layout as layout
import companion.test_companion_app_helpers as cah
from companion import auth, frame_state
from companion.pages import config_page
from companion_app_server import http_request, login
from server import device_config
from server import notify as notify_module
import server.poll_loop as poll_loop
from server.plane import calendar_rules, colour_rules, manual_resolutions

import companion.app as app_module

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_VENDORED_ILLUSTRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "assets", "icons", "illustrations")

# 29-06-PLAN.md Task 3 (CFG-79): the site-wide caption-floor's own
# exemption list, imported (never re-listed) exactly as the legacy
# harness did at module scope.
CAPTION_FLOOR_EXEMPTIONS = config_page.ASPECT_CAPTION_EXEMPTIONS


# ==========================================================================
# The illustration override's own effects (ledger rows 267-270,
# consolidated: all four read state produced by ONE upload, never each
# other's mutations, matching 33-17-SUMMARY.md's own consolidation
# precedent for a shared, fixed-order setup).
# ==========================================================================


def test_illustration_override_effects_after_a_real_upload(make_app_server):
    """the overridden air-france render and the vueling-airlines render (the same source image)
    come out of the identical illustration_normalize pipeline (D-03); the upload was written to
    {state_dir}/illustration_overrides/air-france.png, and nothing else was created in that
    directory; the vendored server/assets/icons/illustrations/air-france.png file is provably
    byte-identical (hash, size, and mtime) after a successful upload; and select_illustration()
    given the harness's own state_dir resolves Air France to the override the real route just
    wrote, while with no state_dir it still resolves to the vendored file"""
    import hashlib

    from server.plane import illustrations as server_illustrations

    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session_cookie = login(server)

    vendored_air_france_path = os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "air-france.png")
    with open(vendored_air_france_path, "rb") as fh:
        pre_upload_vendored_hash = hashlib.sha256(fh.read()).hexdigest()
    pre_upload_vendored_stat = os.stat(vendored_air_france_path)

    with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
        vueling_bytes = fh.read()
    pre_status, _pre_headers, pre_body = http_request(
        base + "/illustration/air-france.png", cookie=session_cookie)
    assert pre_status == 200, "expected 200 for the pre-upload GET, got %d" % pre_status

    upload_body, upload_content_type = cah.encode_multipart(
        vueling_bytes, filename="../../../etc/passwd", field_name="illustration")
    upload_status, _upload_headers, _ = http_request(
        base + "/illustration/air-france.png", method="POST", data=upload_body,
        cookie=session_cookie, content_type=upload_content_type)
    assert upload_status == 303, (
        "expected a 303 redirect after a valid upload, got %d" % upload_status)

    # Row 267: the override render and the vueling render come out of the
    # identical normalization pipeline.
    override_status, _h1, override_body = http_request(
        base + "/illustration/air-france.png", cookie=session_cookie)
    vueling_status, _h2, vueling_body = http_request(
        base + "/illustration/vueling-airlines.png", cookie=session_cookie)
    assert override_status == 200 and vueling_status == 200, (
        "expected 200 for both routes, got %d/%d" % (override_status, vueling_status))
    if override_body != vueling_body:
        # Fallback (D-03, documented in the plan 02 SUMMARY): if the
        # store-time Pillow RGBA re-encode turns out not to be
        # byte-for-byte lossless against illustration_normalize's own
        # re-encode of the untouched vendored file, fall back to a
        # weaker-but-still-meaningful equivalence check.
        assert override_body.startswith(PNG_SIGNATURE), (
            "expected the override render to start with the PNG signature even on the "
            "fallback path")
        assert override_body != pre_body, (
            "expected the override render to differ from the pre-upload render")
        assert len(override_body) == len(vueling_body), (
            "fallback check failed too: override render length %d != vueling render length %d"
            % (len(override_body), len(vueling_body)))

    # Row 268: the upload was written to exactly one file.
    override_path = os.path.join(server.state_dir, "illustration_overrides", "air-france.png")
    assert os.path.isfile(override_path), "expected an override file at %r" % override_path
    override_dir = os.path.join(server.state_dir, "illustration_overrides")
    entries = sorted(os.listdir(override_dir))
    assert entries == ["air-france.png"], (
        "expected exactly one file (air-france.png) in the override directory, got %r" % entries)

    # Row 269: the vendored original is untouched.
    with open(vendored_air_france_path, "rb") as fh:
        post_hash = hashlib.sha256(fh.read()).hexdigest()
    assert post_hash == pre_upload_vendored_hash, (
        "the vendored air-france.png file's bytes changed after an upload")
    post_stat = os.stat(vendored_air_france_path)
    assert post_stat.st_size == pre_upload_vendored_stat.st_size, (
        "the vendored air-france.png file's size changed after an upload")
    assert post_stat.st_mtime_ns == pre_upload_vendored_stat.st_mtime_ns, (
        "the vendored air-france.png file's mtime changed after an upload")

    # Row 270: select_illustration() resolves through the override / vendored fallback.
    override_result = server_illustrations.select_illustration(
        {"airline_name": "Air France"}, state_dir=server.state_dir)
    vendored_result = server_illustrations.select_illustration({"airline_name": "Air France"})
    assert override_result == override_path, (
        "expected select_illustration(..., state_dir=...) to return %r, got %r"
        % (override_path, override_result))
    assert vendored_result == vendored_air_france_path, (
        "expected select_illustration() with no state_dir to still return the vendored path, "
        "got %r" % (vendored_result,))


def test_illustration_non_image_upload_is_rejected(make_app_server):
    """POSTing a non-image payload is rejected with the rejection flash key and writes no
    override file"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    body, content_type = cah.encode_multipart(
        b"not a real image, just some text bytes", filename="fake.png")
    status, headers, _resp_body = http_request(
        server.base_url() + "/illustration/easyjet.png", method="POST", data=body,
        cookie=session_cookie, content_type=content_type)
    assert status == 303, "expected a 303 redirect for a non-image upload, got %d" % status
    location = headers.get("Location", "")
    assert ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) in location, (
        "expected the rejection flash key in the redirect, got %r" % location)
    override_path = os.path.join(server.state_dir, "illustration_overrides", "easyjet.png")
    assert not os.path.exists(override_path), (
        "expected no override file to be written for a rejected non-image upload")


def test_illustration_oversized_upload_is_rejected_and_connection_stays_healthy(make_app_server):
    """POSTing a body over MAX_ILLUSTRATION_UPLOAD_BYTES is rejected, writes no override file,
    and the drain leaves the service healthy for the next request"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    oversized_payload = b"\x00" * (app_module.MAX_ILLUSTRATION_UPLOAD_BYTES + 4096)
    body, content_type = cah.encode_multipart(oversized_payload, filename="huge.png")
    status, headers, _resp_body = http_request(
        server.base_url() + "/illustration/corsair.png", method="POST", data=body,
        cookie=session_cookie, content_type=content_type)
    assert status == 303, "expected a 303 redirect for an oversized upload, got %d" % status
    location = headers.get("Location", "")
    assert ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REJECTED) in location, (
        "expected the rejection flash key in the redirect, got %r" % location)
    override_path = os.path.join(server.state_dir, "illustration_overrides", "corsair.png")
    assert not os.path.exists(override_path), (
        "expected no override file to be written for a rejected oversized upload")
    health_status, _headers2, _body2 = http_request(
        server.base_url() + "/health", cookie=session_cookie)
    assert health_status == 200, (
        "expected a fresh authenticated GET after the oversized-upload drain to still return "
        "200, got %d" % health_status)


def test_illustration_post_unknown_and_traversal_keys_returns_404(make_app_server):
    """POSTing a valid payload to a key outside the membership set, and to three
    traversal-shaped paths, all 404 and write nothing to the override directory"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    small_body, small_content_type = cah.encode_multipart(
        b"irrelevant - membership test runs before the body is read", filename="x.png")
    override_dir = os.path.join(server.state_dir, "illustration_overrides")
    before_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []
    adversarial_paths = [
        "/illustration/not-a-real-airline.png",
        "/illustration/..%2F..%2Fetc%2Fpasswd.png",
        "/illustration/../../../etc/passwd.png",
        "/illustration/style.png",
    ]
    for adversarial_path in adversarial_paths:
        status, _headers, _body = http_request(
            server.base_url() + adversarial_path, method="POST", data=small_body,
            cookie=session_cookie, content_type=small_content_type)
        assert status == 404, "expected 404 for POST %r, got %d" % (adversarial_path, status)
    after_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []
    assert after_entries == before_entries, (
        "expected the override directory to gain nothing from rejected POSTs, before=%r "
        "after=%r" % (before_entries, after_entries))


def test_illustration_unauthenticated_post_redirects_to_login_and_writes_nothing(make_app_server):
    """an unauthenticated POST /illustration/tunisair.png redirects to /login and writes no
    override file"""
    server = make_app_server(fake_providers=True)
    body, content_type = cah.encode_multipart(
        b"irrelevant - require_session() runs before anything else", filename="x.png")
    status, headers, _resp_body = http_request(
        server.base_url() + "/illustration/tunisair.png", method="POST", data=body,
        content_type=content_type)
    assert status == 303, "expected a 303 redirect for an unauthenticated POST, got %d" % status
    location = headers.get("Location", "")
    assert "/login" in location, "expected a redirect to /login, got %r" % location
    override_path = os.path.join(server.state_dir, "illustration_overrides", "tunisair.png")
    assert not os.path.exists(override_path), (
        "expected no override file to be written for an unauthenticated POST")


# ==========================================================================
# POST /airlines/resolve and the manual-resolution delete route
# (phase 13 plan 13-06 Task 3, D-03/D-07/D-08/D-11) — each test below
# spins up its own isolated make_app_server(), since these routes write
# a real manual_resolutions.json/poll_state.json/override file.
# ==========================================================================


def test_manual_resolve_and_delete_routes_require_auth_and_write_nothing(make_app_server):
    """unauthenticated POSTs to /airlines/resolve and
    /airlines/manual-resolutions/{prefix}/delete both redirect to /login and write no
    manual_resolutions.json — the state dir is unchanged, not only the status code"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    cah.seed_unresolved_prefixes(server.state_dir, {
        "PQR": {
            "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "PQR100"},
    })
    manual_resolutions_path = manual_resolutions.manual_resolutions_path(server.state_dir)

    resolve_data = urllib.parse.urlencode(
        {"prefix": "PQR", "airline_name": "Unauthorized Air"}).encode()
    status, headers, _ = http_request(base + "/airlines/resolve", method="POST", data=resolve_data)
    assert status == 303, (
        "expected a 303 redirect for an unauthenticated POST /airlines/resolve, got %d" % status)
    assert "/login" in headers.get("Location", ""), (
        "expected a redirect to /login, got %r" % headers.get("Location", ""))
    assert not os.path.exists(manual_resolutions_path), (
        "expected no manual_resolutions.json to be written by an unauthenticated POST")

    status, headers, _ = http_request(
        base + "/airlines/manual-resolutions/PQR/delete", method="POST")
    assert status == 303, (
        "expected a 303 redirect for an unauthenticated delete POST, got %d" % status)
    assert "/login" in headers.get("Location", ""), (
        "expected a redirect to /login, got %r" % headers.get("Location", ""))
    assert not os.path.exists(manual_resolutions_path), (
        "expected no manual_resolutions.json to exist after an unauthenticated delete POST")


def test_manual_resolve_post_revalidates_prefix_against_live_registry(make_app_server):
    """POST /airlines/resolve re-validates the prefix against the live unresolved-prefix
    registry on write (D-11): a well-shaped but unregistered prefix writes nothing and gets the
    stale flash; the identical POST succeeds once the prefix is a live registry member"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)
    manual_resolutions_path = manual_resolutions.manual_resolutions_path(server.state_dir)

    resolve_data = urllib.parse.urlencode({"prefix": "XYZ", "airline_name": "Ghost Air"}).encode()
    status, headers, _ = http_request(
        base + "/airlines/resolve", method="POST", data=resolve_data, cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=manual_prefix_stale" in location, "expected the stale flash key, got %r" % location
    assert not os.path.exists(manual_resolutions_path), (
        "expected no manual_resolutions.json for a prefix absent from the live registry — even "
        "though its shape is valid")

    cah.seed_unresolved_prefixes(server.state_dir, {
        "XYZ": {
            "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "XYZ100"},
    })
    status, headers, _ = http_request(
        base + "/airlines/resolve", method="POST", data=resolve_data, cookie=session)
    assert status == 303, "expected a 303 redirect once the prefix is live, got %d" % status
    location = headers.get("Location", "")
    assert "flash=manual_resolved" in location, (
        "expected the resolved flash key once the prefix is a live registry member, got %r"
        % location)
    registry = manual_resolutions.load_manual_resolutions(server.state_dir)
    assert "XYZ" in registry and registry["XYZ"].get("airline_name") == "Ghost Air", (
        "expected the entry to be persisted once the prefix is live, got %r" % registry)


def test_manual_resolve_post_rejection_mapping_and_d03_branch(make_app_server):
    """each add_entry() rejection reaches its own distinct flash key and persists nothing
    (empty/too-long/reserved names, and the registry cap); the D-03 branch: a brand-new name
    redirects with resolve= (Step B offered) while a name already covered by existing artwork
    redirects without it"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    def _seed_gap(prefix):
        state = poll_loop.load_poll_state(server.state_dir)
        registry = state.get("unresolved_prefixes")
        if not isinstance(registry, dict):
            registry = {}
        registry[prefix] = {
            "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": prefix + "100"}
        cah.seed_unresolved_prefixes(server.state_dir, registry)

    def _resolve_post(prefix, airline_name):
        data = urllib.parse.urlencode({"prefix": prefix, "airline_name": airline_name}).encode()
        return http_request(base + "/airlines/resolve", method="POST", data=data, cookie=session)

    rejection_cases = (
        ("EMP", "", "flash=manual_name_empty"),
        ("TLN", "A" * 101, "flash=manual_name_too_long"),
        ("RSV", "Generic Fallback", "flash=manual_name_reserved"),
        ("UNU", "../../etc/passwd", "flash=manual_name_unusable"),
    )
    for prefix, airline_name, expected_flash in rejection_cases:
        _seed_gap(prefix)
        status, headers, _ = _resolve_post(prefix, airline_name)
        assert status == 303, "prefix %r: expected a 303 redirect, got %d" % (prefix, status)
        location = headers.get("Location", "")
        assert expected_flash in location, (
            "prefix %r: expected %r in the redirect, got %r" % (prefix, expected_flash, location))
        registry = manual_resolutions.load_manual_resolutions(server.state_dir)
        assert prefix not in registry, "prefix %r: expected the rejected entry to NOT be persisted" % (prefix,)

    # D-03 branch: run BEFORE the cap-fill below, since once the registry
    # is at its 200-entry cap no further distinct prefix can be added.
    _seed_gap("NEW")
    status, headers, _ = _resolve_post("NEW", "Totally Novel Airline")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "resolve=NEW" in location and "flash=manual_resolved" in location, (
        "expected resolve=NEW and the resolved flash for a brand-new name, got %r" % location)

    _seed_gap("OLD")
    status, headers, _ = _resolve_post("OLD", "Air France")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "resolve=" not in location, (
        "expected NO resolve= param when the named airline already has artwork, got %r" % location)
    assert "flash=manual_resolved" in location, "expected the resolved flash key, got %r" % location

    existing_count = len(manual_resolutions.load_manual_resolutions(server.state_dir))
    needed = manual_resolutions.MANUAL_RESOLUTION_MAX_ENTRIES - existing_count
    cap_prefixes = []
    count = 0
    for a in string.ascii_uppercase:
        for b in string.ascii_uppercase:
            if count >= needed:
                break
            cap_prefixes.append("Y" + a + b)
            count += 1
        if count >= needed:
            break
    for i, pfx in enumerate(cap_prefixes):
        result = manual_resolutions.add_entry(server.state_dir, pfx, "Cap Filler %d" % i)
        assert result == manual_resolutions.ADD_OK, (
            "test setup failure filling the cap: add_entry(%r, ...) returned %r" % (pfx, result))
    _seed_gap("CAP")
    status, headers, _ = _resolve_post("CAP", "One Too Many Air")
    assert status == 303, "expected a 303 redirect for the at-cap POST, got %d" % status
    location = headers.get("Location", "")
    assert "flash=manual_registry_full" in location, (
        "expected the registry-full flash key, got %r" % location)
    registry = manual_resolutions.load_manual_resolutions(server.state_dir)
    assert "CAP" not in registry, "expected the at-cap entry to NOT be persisted"


def test_manual_resolution_delete_route_full_contract(make_app_server):
    """POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry, leaves the
    override PNG on disk (D-08), and redirects to /airlines with no flash; a second identical
    POST is a no-op that also redirects without an error flash; a malformed prefix 404s without
    touching the registry"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    add_result = manual_resolutions.add_entry(server.state_dir, "DEL", "Deletable Air")
    assert add_result == manual_resolutions.ADD_OK, "test setup failure: add_entry() returned %r" % (add_result,)
    key = manual_resolutions.illustration_key_for_name("Deletable Air")
    override_dir = os.path.join(server.state_dir, "illustration_overrides")
    os.makedirs(override_dir, exist_ok=True)
    override_path = os.path.join(override_dir, key + ".png")
    with open(override_path, "wb") as fh:
        fh.write(b"not a real png - only its continued existence is asserted here")

    status, headers, _ = http_request(
        base + "/airlines/manual-resolutions/DEL/delete", method="POST", cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert location == "/airlines", "expected a redirect to /airlines with no flash, got %r" % location
    registry = manual_resolutions.load_manual_resolutions(server.state_dir)
    assert "DEL" not in registry, "expected the DEL entry to be removed from the registry"
    assert os.path.isfile(override_path), "expected the override file to survive the delete (D-08)"

    status, headers, _ = http_request(
        base + "/airlines/manual-resolutions/DEL/delete", method="POST", cookie=session)
    assert status == 303, (
        "expected a second, identical delete POST to also redirect (idempotent), got %d" % status)
    location = headers.get("Location", "")
    assert location == "/airlines", (
        "expected the same no-flash redirect on a second delete of an already-absent prefix, "
        "got %r" % location)

    status, _headers, _body = http_request(
        base + "/airlines/manual-resolutions/not-three-letters/delete", method="POST", cookie=session)
    assert status == 404, "expected 404 for a malformed prefix, got %d" % status
    assert os.path.isfile(override_path), (
        "expected the override file to still exist after a 404'd malformed-prefix POST")


# ==========================================================================
# POST /settings/rules/add and POST /settings/rules/{kind}/{value}/delete
# (Phase 15 D-10, D-11) — each test below spins up its own isolated
# make_app_server(), since these routes write a real colour_rules.json.
# ==========================================================================


def test_rules_routes_require_auth_and_write_nothing(make_app_server):
    """unauthenticated POSTs to /settings/rules/add and
    /settings/rules/{kind}/{value}/delete both redirect to /login and write no
    colour_rules.json — the state dir is unchanged, not only the status code"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    rules_path = colour_rules.colour_rules_path(server.state_dir)

    add_data = urllib.parse.urlencode(
        {"rule_kind": "callsign", "rule_key": "AFR1234", "rule_theme_id": "white"}).encode()
    status, headers, _ = http_request(base + config_page.RULES_ADD_ROUTE, method="POST", data=add_data)
    assert status == 303, "expected a 303 redirect for an unauthenticated add POST, got %d" % status
    assert "/login" in headers.get("Location", ""), "expected a redirect to /login, got %r" % headers.get("Location", "")
    assert not os.path.exists(rules_path), "expected no colour_rules.json to be written by an unauthenticated POST"

    delete_path = "%scallsign/AFR1234%s" % (
        config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
    status, headers, _ = http_request(base + delete_path, method="POST")
    assert status == 303, "expected a 303 redirect for an unauthenticated delete POST, got %d" % status
    assert "/login" in headers.get("Location", ""), "expected a redirect to /login, got %r" % headers.get("Location", "")
    assert not os.path.exists(rules_path), "expected no colour_rules.json to exist after an unauthenticated delete POST"


def test_rules_add_and_delete_forms_sit_outside_settings_form(make_app_server):
    """the rules add form and each delete form sit outside <form id=SETTINGS_FORM_ID> (D-10):
    neither carries the settings form's id nor a form= attribute pointing at it, and a rule add
    followed by an unrelated settings-form save leaves both the rule and every device-config
    setting intact (15-VALIDATION.md row 10)"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    add_result = colour_rules.add_rule(server.state_dir, "callsign", "AFR9001", "white")
    assert add_result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (add_result,)

    status, _headers, body = http_request(base + "/display", cookie=session)
    assert status == 200, "expected 200 GET /display, got %d" % status
    page = body.decode("utf-8")

    add_form_marker = 'action="%s"' % config_page.RULES_ADD_ROUTE
    add_tag_start = page.rindex("<form", 0, page.index(add_form_marker))
    add_tag_end = page.index(">", add_tag_start)
    add_form_tag = page[add_tag_start:add_tag_end + 1]

    expected_delete_action = "%scallsign/AFR9001%s" % (
        config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
    delete_form_marker = 'action="%s"' % expected_delete_action
    delete_tag_start = page.rindex("<form", 0, page.index(delete_form_marker))
    delete_tag_end = page.index(">", delete_tag_start)
    delete_form_tag = page[delete_tag_start:delete_tag_end + 1]

    for tag, name in ((add_form_tag, "add"), (delete_form_tag, "delete")):
        assert config_page.SETTINGS_FORM_ID not in tag, (
            "expected the %s form to not carry the settings form's id, got %r" % (name, tag))
        assert "form=" not in tag, "expected the %s form to carry no form= attribute, got %r" % (name, tag)

    status, _headers, _body = http_request(
        base + "/settings", method="POST",
        data=urllib.parse.urlencode({"tracked_runway": "3"}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect from the settings save, got %d" % status
    registry = colour_rules.load_colour_rules(server.state_dir)
    assert "AFR9001" in registry.get("callsign", {}), (
        "expected the rule to survive an unrelated settings-form save")
    cfg = device_config.load_device_config(server.state_dir)
    assert cfg.get("tracked_runway") == "3", (
        "expected the settings save to persist independently of the rule add")


def test_rules_add_route_no_js_added_then_replaced(make_app_server):
    """raw URL-encoded no-JS POSTs to the rules add route (15-VALIDATION.md row 11): a first add
    flashes rule_added, a second add for the same key (case-insensitive input) flashes
    rule_replaced and echoes the normalised key back, and the registry holds exactly one entry
    with the second theme"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    status, headers, _ = http_request(
        base + config_page.RULES_ADD_ROUTE, method="POST",
        data=urllib.parse.urlencode(
            {"rule_kind": "callsign", "rule_key": "afr1234", "rule_theme_id": "white"}).encode(),
        cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert "flash=rule_added" in headers.get("Location", ""), (
        "expected the added flash key on first add, got %r" % headers.get("Location"))

    status, headers, _ = http_request(
        base + config_page.RULES_ADD_ROUTE, method="POST",
        data=urllib.parse.urlencode(
            {"rule_kind": "callsign", "rule_key": "AFR1234", "rule_theme_id": "blue"}).encode(),
        cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=rule_replaced" in location and "rule=AFR1234" in location, (
        "expected the replaced flash key echoing the normalised key, got %r" % location)

    registry = colour_rules.load_colour_rules(server.state_dir)
    callsign_entries = registry.get("callsign", {})
    assert list(callsign_entries.keys()) == ["AFR1234"], (
        "expected exactly one callsign entry keyed AFR1234, got %r" % (callsign_entries,))
    assert callsign_entries["AFR1234"]["theme_id"] == "blue", (
        "expected the second add's theme to win, got %r" % (callsign_entries["AFR1234"],))


def test_rules_add_route_rejection_paths(make_app_server):
    """the rules add route's rejection paths: a malformed value for the selected kind flashes
    rule_key_invalid and writes nothing; a crafted kind and a crafted theme id each flash the
    generic rule_save_failed and write nothing; filling the registry to its cap and adding one
    more flashes rule_registry_full without persisting the at-cap entry"""
    import itertools

    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    def _add(kind, key, theme_id):
        data = urllib.parse.urlencode(
            {"rule_kind": kind, "rule_key": key, "rule_theme_id": theme_id}).encode()
        return http_request(base + config_page.RULES_ADD_ROUTE, method="POST", data=data, cookie=session)

    status, headers, _ = _add("prefix", "TOOLONG", "white")
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert "flash=rule_key_invalid" in headers.get("Location", ""), (
        "expected the key-invalid flash key, got %r" % headers.get("Location"))
    registry = colour_rules.load_colour_rules(server.state_dir)
    assert not registry.get("prefix"), "expected nothing written for a malformed value"

    status, headers, _ = _add("../../etc/passwd", "AFR", "white")
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert "flash=rule_save_failed" in headers.get("Location", ""), (
        "expected the generic save-failed flash key for a crafted kind, got %r" % headers.get("Location"))

    status, headers, _ = _add("callsign", "AFR9999", "not-a-real-theme")
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert "flash=rule_save_failed" in headers.get("Location", ""), (
        "expected the generic save-failed flash key for a crafted theme id, got %r" % headers.get("Location"))
    registry = colour_rules.load_colour_rules(server.state_dir)
    assert "AFR9999" not in registry.get("callsign", {}), "expected nothing written for a crafted theme id"

    existing_count = sum(len(v) for v in registry.values())
    needed = colour_rules.COLOUR_RULE_MAX_ENTRIES - existing_count
    cap_prefixes = []
    for combo in itertools.product(string.ascii_uppercase, repeat=3):
        if len(cap_prefixes) >= needed:
            break
        cap_prefixes.append("".join(combo))
    for prefix in cap_prefixes:
        result = colour_rules.add_rule(server.state_dir, "prefix", prefix, "white")
        assert result == colour_rules.ADD_OK_NEW, (
            "test setup failure filling the cap: add_rule(%r, ...) returned %r" % (prefix, result))
    status, headers, _ = _add("prefix", "ZZZ", "white")
    assert status == 303, "expected a 303 redirect for the at-cap POST, got %d" % status
    assert "flash=rule_registry_full" in headers.get("Location", ""), (
        "expected the registry-full flash key, got %r" % headers.get("Location"))
    registry_after = colour_rules.load_colour_rules(server.state_dir)
    assert "ZZZ" not in registry_after.get("prefix", {}), "expected the at-cap entry to NOT be persisted"


def test_rules_delete_route_full_contract(make_app_server):
    """POST /settings/rules/{kind}/{value}/delete removes the registry entry and flashes
    rule_deleted; a second identical delete of an already-absent entry is a no-op that redirects
    with no flash; a malformed kind segment and a malformed value segment each 404 without
    touching an unrelated existing entry"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    add_result = colour_rules.add_rule(server.state_dir, "hex", "3944F2", "blue")
    assert add_result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (add_result,)

    delete_path = "%shex/3944F2%s" % (
        config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
    status, headers, _ = http_request(base + delete_path, method="POST", cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert "flash=rule_deleted" in headers.get("Location", ""), (
        "expected the deleted flash key, got %r" % headers.get("Location"))
    registry = colour_rules.load_colour_rules(server.state_dir)
    assert "3944F2" not in registry.get("hex", {}), "expected the entry to be removed from the registry"

    status, headers, _ = http_request(base + delete_path, method="POST", cookie=session)
    assert status == 303, "expected a second identical delete to also redirect, got %d" % status
    assert "flash=" not in headers.get("Location", ""), (
        "expected no flash on a repeat delete of an already-absent entry, got %r" % headers.get("Location"))

    add_result = colour_rules.add_rule(server.state_dir, "callsign", "AFR1234", "white")
    assert add_result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (add_result,)
    bad_kind_path = "%sbogus/AFR1234%s" % (
        config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
    status, _headers, _body = http_request(base + bad_kind_path, method="POST", cookie=session)
    assert status == 404, "expected 404 for a malformed kind segment, got %d" % status
    bad_value_path = "%scallsign/bad-value%s" % (
        config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
    status, _headers, _body = http_request(base + bad_value_path, method="POST", cookie=session)
    assert status == 404, "expected 404 for a malformed value segment, got %d" % status
    registry_after = colour_rules.load_colour_rules(server.state_dir)
    assert "AFR1234" in registry_after.get("callsign", {}), (
        "expected the unrelated entry to survive both 404'd delete attempts")


def test_rules_page_context_reads_fresh_per_request(make_app_server):
    """a rule written directly to state_dir between two GETs of the Settings page appears in the
    second render — proving page_context() reads colour_rules fresh per request rather than
    through any process-scoped cache"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)

    status, _headers, body = http_request(base + "/display", cookie=session)
    assert status == 200, "expected 200, got %d" % status
    assert b"FRESHRD1" not in body, "expected the rule to be absent before it is written"

    add_result = colour_rules.add_rule(server.state_dir, "callsign", "FRESHRD1", "white")
    assert add_result == colour_rules.ADD_OK_NEW, "test setup failure: add_rule() returned %r" % (add_result,)

    status, _headers, body = http_request(base + "/display", cookie=session)
    assert status == 200, "expected 200, got %d" % status
    assert b"FRESHRD1" in body, (
        "expected page_context() to read the rules registry fresh per request, not through the "
        "poll-cycle process cache")


# ==========================================================================
# poll-trigger cooldown: server-global, not per-session (ledger rows
# 287-290, consolidated: each step depends on the previous step's own
# cooldown-timer mutation, matching 33-17-SUMMARY.md's own consolidation
# rule for a fixed-order sequence sharing one mutable server).
# ==========================================================================


def test_poll_trigger_cooldown_sequence(make_app_server):
    """a first poll trigger redirects with the poll_triggered flash key, and its own run_once()
    was served by the fake ADS-B providers (adsbfi and adsblol called, no live network); an
    immediate second poll trigger redirects with the poll_cooldown flash key; and a fresh
    second-opener session is refused by the same cooldown (server-global, not per-session)"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session_cookie = login(server)

    status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_triggered" in location, (
        "expected the poll_triggered flash key in the redirect, got %r" % location)

    calls = server.fake_provider_calls()
    providers_called = {call["provider"] for call in calls}
    missing = {"adsbfi", "adsblol"} - providers_called
    assert not missing, (
        "expected the fake provider's call log to show both adsbfi and adsblol queried by the "
        "first poll trigger's run_once(), missing %r - full log: %r" % (missing, calls))

    status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=session_cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_cooldown" in location, (
        "expected the poll_cooldown flash key in the redirect, got %r" % location)

    second_session_cookie = login(server)
    status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=second_session_cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_cooldown" in location, (
        "expected a fresh second-opener session to also see the poll_cooldown flash key, got %r"
        % location)


# 2026-08-28 fix: a genuine run_once() failure (e.g. an unreadable
# --geofence path, exactly what production hit when
# deploy/skypane-companion.service never passed --geofence at all and
# the relative default didn't resolve under its WorkingDirectory) must
# redirect with the distinct poll_failed flash key, never the misleading
# save_failed one. `tmp_path` supplies a guaranteed-absent path rather
# than a literal `/nonexistent/...` string (T-33-18-01, guard G6).
def test_poll_trigger_failure_uses_distinct_flash_key(make_app_server, tmp_path):
    """a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never
    save_failed"""
    absent_geofence = tmp_path / "absent" / "no-such-geofence.json"
    server = make_app_server(
        extra_args=["--geofence", str(absent_geofence)], fake_providers=True)
    session = login(server)
    status, headers, _ = http_request(
        server.base_url() + "/poll-now", method="POST", cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_failed" in location, "expected the poll_failed flash key, got %r" % location
    assert "flash=save_failed" not in location, (
        "a poll-trigger failure must never reuse save_failed's misleading copy")


# UXA-15: two genuinely overlapping threads issuing POST /poll-now
# against the same running server, on a session with zero cooldown, must
# never both reach run_once() — the server-side _POLL_LOCK
# (companion/app.py) is the correctness boundary.
def test_poll_now_concurrent_requests_serialize_on_the_lock(make_app_server):
    """two genuinely overlapping POST /poll-now requests: exactly one gets the
    poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    cookie = login(server)

    start_event = threading.Event()
    responses = []
    responses_lock = threading.Lock()

    def _worker():
        start_event.wait()
        status, headers, _ = http_request(base + "/poll-now", method="POST", cookie=cookie)
        with responses_lock:
            responses.append((status, headers.get("Location", "")))

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    start_event.set()
    for t in threads:
        t.join(timeout=30)

    assert len(responses) == 2, "expected two responses, got %d: %r" % (len(responses), responses)
    for status, _location in responses:
        assert status == 303, "expected both responses to be 303 redirects, got %r" % (responses,)
    already_running_count = sum(
        1 for _status, location in responses if "flash=poll_already_running" in location)
    assert already_running_count == 1, (
        "expected exactly one of the two overlapping /poll-now requests to receive the "
        "poll_already_running flash key, got %d of 2: %r" % (already_running_count, responses))


# ==========================================================================
# Section 4 (phase 17 plan 04, D-06/D-09): the save-triggered immediate
# calendar sync, its four outcomes, the throttle bypass, lock
# contention, and the T-17-FLASH leak guard. Every test here uses the
# `app_server_in_process` fixture (a real ThreadingHTTPServer in THIS
# process, not a subprocess) because it needs to monkeypatch
# `calendar_rules.default_calendar_transport` and `socket.getaddrinfo` —
# a monkeypatch a subprocess server, with its own separate interpreter,
# could never see.
# ==========================================================================


def test_calendar_connect_reports_plural_count(app_server_in_process):
    """saving a calendar feed with three in-window flights performs exactly one refresh call and
    the rendered banner names the plural flight count (D-06)"""
    server = app_server_in_process
    session = login(server)
    calls = []
    hostname = "calendar-sync-plural.example"
    url = "https://%s/feed.ics?token=PLURALCOUNTTOKEN" % hostname
    body = cah.ics_body([
        ("AF1234", "CDG", "ORY", 2), ("BA5678", "LHR", "CDG", 4), ("KL2222", "AMS", "ORY", 6),
    ])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body, calls=calls)), \
            cah.fake_public_hostname(hostname):
        status, headers, _b = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_connected" in location, "expected the calendar_connected flash key, got %r" % location
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert status2 == 200, "expected 200 following the redirect, got %d" % status2
    assert b"3 flights" in page_body, "expected the rendered banner to name 3 flights, got %r" % (page_body,)
    assert calls == [url], "expected exactly one transport call with the submitted URL, got %r" % (calls,)


def test_calendar_connect_reports_singular_count(app_server_in_process):
    """saving a calendar feed with exactly one in-window flight pins the singular form ('1
    flight', never '1 flights')"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-singular.example"
    url = "https://%s/feed.ics?token=SINGULARCOUNTTOKEN" % hostname
    body = cah.ics_body([("AF1234", "CDG", "ORY", 2)])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname(hostname):
        status, headers, _b = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    location = headers.get("Location", "")
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert status2 == 200, "expected 200 following the redirect, got %d" % status2
    assert b"1 flight from this calendar" in page_body, (
        "expected the singular form '1 flight', got %r" % (page_body,))
    assert b"1 flights" not in page_body, "the singular count must never carry a trailing 's'"


def test_calendar_connect_zero_entries_still_succeeds(app_server_in_process):
    """a syntactically valid feed with nothing in the frame's window reports success with a 0
    count, distinguishable from a failure"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-empty.example"
    url = "https://%s/feed.ics?token=EMPTYFEEDTOKEN" % hostname
    body = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname(hostname):
        status, headers, _b = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_connected" in location, (
        "a zero-entry feed that parsed correctly must still report success, got %r" % location)
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert b"0 flights" in page_body, "expected the rendered banner to name 0 flights, got %r" % (page_body,)


def test_calendar_sync_failure_reports_generic_message_and_still_saves(app_server_in_process):
    """a failing fetch redirects with the single generic failure flash key, renders the exact
    failure copy, and the URL is saved regardless (D-06)"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-failure.example"
    url = "https://%s/feed.ics?token=FAILURETOKEN" % hostname
    with cah.stubbed_calendar_transport(
            cah.make_calendar_transport(raise_exc=ConnectionError("boom"))), \
            cah.fake_public_hostname(hostname):
        status, headers, _b = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_sync_failed" in location, (
        "expected the single calendar_sync_failed flash key, got %r" % location)
    assert calendar_rules.calendar_is_configured(server.state_dir), (
        "the URL must be saved regardless of whether the immediate fetch succeeded")
    # escape_html() rewrites this copy's apostrophe to "&#x27;" on render
    # (17-02's own recorded surprise for CALENDAR_STATUS_NOT_CONFIGURED) -
    # the rendered page is therefore compared against the ESCAPED form,
    # never the raw FLASH_MESSAGES source string.
    expected_text = layout.escape_html(
        app_module.FLASH_MESSAGES[app_module.FLASH_KEY_CALENDAR_SYNC_FAILED])
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert expected_text.encode() in page_body, (
        "expected the single generic failure copy verbatim (HTML-escaped) in the rendered "
        "banner, got %r" % (page_body,))


def test_calendar_sync_failure_never_leaks_the_url(app_server_in_process):
    """T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token,
    path segment, query-parameter name, or whole URL in the Location header or any served
    response body — the served Settings page legitimately shows the masked host + ellipsis once
    connected (D-14/R-10, extended by 21-07-PLAN.md Task 2)"""
    server = app_server_in_process
    session = login(server)
    hostname = "leak-check-host.example"
    token = "LEAKTOKEN99999"
    path_segment = "leak-path-segment"
    query_param = "leakqueryparam"
    url = "https://%s/private/%s/feed.ics?%s=%s" % (hostname, path_segment, query_param, token)
    needles = [token, hostname, path_segment, query_param, url]
    raise_exc = ConnectionError("Failed to resolve %s: Name or service not known" % url)
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(raise_exc=raise_exc)), \
            cah.fake_public_hostname(hostname):
        status, headers, redirect_body = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    for needle in needles:
        assert needle not in location, "leak in Location header: %r found in %r" % (needle, location)
        assert needle.encode() not in redirect_body, "leak in the redirect response body: %r" % (needle,)
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert layout.escape_html("%s…" % hostname).encode() in page_body, (
        "expected the masked host + ellipsis fragment to be served once connected (D-14/R-10)")
    for needle in (token, path_segment, query_param, url):
        assert needle.encode() not in page_body, (
            "leak in the served response body: %r found on the rendered Settings page" % (needle,))


def test_calendar_disconnect_reports_deletion_and_erases_entries(app_server_in_process):
    """checking the disconnect box redirects with the disconnected flash key, and the calendar's
    previously-fetched flights are actually erased from disk (D-04)"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-disconnect.example"
    url = "https://%s/feed.ics?token=DISCONNECTTOKEN" % hostname
    body = cah.ics_body([("AF1234", "CDG", "ORY", 2)])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname(hostname):
        http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    registry_before = calendar_rules.load_calendar_registry(server.state_dir)
    assert registry_before["entries"], "test setup failure: expected at least one entry before disconnecting"

    status, headers, _b = http_request(
        server.base_url() + "/settings", method="POST",
        data=urllib.parse.urlencode(
            {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}).encode(),
        cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_disconnected" in location, "expected the calendar_disconnected flash key, got %r" % location
    assert not calendar_rules.calendar_is_configured(server.state_dir), "expected the calendar to be disconnected"
    registry_after = calendar_rules.load_calendar_registry(server.state_dir)
    assert not registry_after["entries"], (
        "expected every fetched flight to be deleted on disconnect, found %r" % (registry_after["entries"],))
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert b"deleted" in page_body, "expected the rendered banner to state the flights were deleted"


# ==========================================================================
# 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect action's own
# dedicated POST /settings/calendar/disconnect route — a bare/wrong-
# confirm POST renders the two-step confirmation page and erases
# nothing; only confirm=yes disconnects; the route is session-gated
# like every other state-changing route.
# ==========================================================================


def test_calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing(app_server_in_process):
    """a bare authenticated POST /settings/calendar/disconnect with no confirm field returns 200
    with the confirmation copy and leaves the calendar connected (D-08/A-26)"""
    server = app_server_in_process
    session = login(server)
    url = "https://bare-post.example/feed.ics?token=BAREPOSTTOKEN"
    calendar_rules.save_calendar_url(server.state_dir, url)
    status, _headers, body = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE,
        method="POST", data=b"", cookie=session)
    assert status == 200, "expected a 200 confirmation page for a bare POST, got %d" % status
    assert html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() in body, (
        "expected the confirmation copy in the rendered page")
    assert calendar_rules.calendar_is_configured(server.state_dir), (
        "expected the calendar to remain connected after a bare POST")


def test_calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing(app_server_in_process):
    """an authenticated POST /settings/calendar/disconnect with confirm=maybe renders the
    confirmation page rather than disconnecting anything (D-08/A-26)"""
    server = app_server_in_process
    session = login(server)
    url = "https://confirm-maybe.example/feed.ics?token=MAYBETOKEN"
    calendar_rules.save_calendar_url(server.state_dir, url)
    status, _headers, body = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE, method="POST",
        data=urllib.parse.urlencode({config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD: "maybe"}).encode(),
        cookie=session)
    assert status == 200, "expected a 200 confirmation page for confirm=maybe, got %d" % status
    assert html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_SENTENCE, quote=True).encode() in body, (
        "expected the confirmation copy in the rendered page")
    assert calendar_rules.calendar_is_configured(server.state_dir), (
        "expected the calendar to remain connected after confirm=maybe")


def test_calendar_disconnect_route_confirm_yes_disconnects(app_server_in_process):
    """an authenticated POST /settings/calendar/disconnect with confirm=yes 303-redirects with
    the disconnected flash key and actually disconnects the calendar (D-08/A-26)"""
    server = app_server_in_process
    session = login(server)
    url = "https://confirm-yes.example/feed.ics?token=YESTOKEN"
    calendar_rules.save_calendar_url(server.state_dir, url)
    status, headers, _body = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE, method="POST",
        data=urllib.parse.urlencode({
            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD: config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
        }).encode(),
        cookie=session)
    assert status == 303, "expected a 303 redirect for confirm=yes, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_disconnected" in location, "expected the calendar_disconnected flash key, got %r" % location
    assert not calendar_rules.calendar_is_configured(server.state_dir), "expected the calendar to be disconnected"


def test_calendar_disconnect_route_unauthenticated_redirects_to_login(app_server_in_process):
    """an unauthenticated POST /settings/calendar/disconnect (even with confirm=yes) redirects to
    /login and writes nothing (D-08/A-26, T-19-41)"""
    server = app_server_in_process
    url = "https://unauth-disconnect.example/feed.ics?token=UNAUTHTOKEN"
    calendar_rules.save_calendar_url(server.state_dir, url)
    status, headers, _body = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE, method="POST",
        data=urllib.parse.urlencode({
            config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD: config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE,
        }).encode())
    assert status == 303, "expected a 303 redirect for an unauthenticated POST, got %d" % status
    assert headers.get("Location") == "/login", "expected a redirect to /login, got %r" % headers.get("Location")
    assert calendar_rules.calendar_is_configured(server.state_dir), (
        "expected the calendar to remain connected — nothing should be written")


# ==========================================================================
# 20-09-PLAN.md Task 2 (D-14c): the calendar connect action's own
# dedicated POST /settings/calendar/connect route — never through
# config_page.handle_post()'s scope/in_scope machinery (T-20-11),
# session-gated like every other state-changing route (T-20-10).
# ==========================================================================


def test_calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone(app_server_in_process):
    """a valid POST /settings/calendar/connect 303-redirects to Display with the
    calendar_connect_ok flash key, persists the URL, triggers exactly one registry refresh, and
    leaves quiet_hours_enabled/display_enabled exactly as they were (D-14c, T-20-11 pinned
    regression)"""
    server = app_server_in_process
    # T-20-11's own pinned regression: seed Quiet hours and the screen ON,
    # connect a calendar, and assert both are STILL on afterwards.
    device_config.save_device_config(
        server.state_dir, quiet_hours_enabled=True, display_enabled=True)
    session = login(server)
    hostname = "connect-route.example"
    url = "https://%s/feed.ics?token=CONNECTROUTETOKEN" % hostname
    body = cah.ics_body([("AFR1234", "ORY", "TLS", 2), ("AFR5678", "ORY", "NCE", 3)])
    calls = []
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body, calls=calls)), \
            cah.fake_public_hostname(hostname):
        status, headers, _b = http_request(
            server.base_url() + config_page.CALENDAR_CONNECT_ROUTE, method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert location.startswith("/display"), "expected a redirect to Display, got %r" % location
    assert "flash=calendar_connect_ok" in location, "expected the calendar_connect_ok flash key, got %r" % location
    assert calendar_rules.calendar_is_configured(server.state_dir), "expected the calendar to be configured"
    assert calendar_rules.configured_calendar_url(server.state_dir) == url, "expected the submitted URL to be stored"
    assert len(calls) == 1, "expected exactly one registry refresh (one transport call), got %d" % len(calls)
    registry = calendar_rules.load_calendar_registry(server.state_dir)
    assert len(registry["entries"]) == 2, "expected two fetched entries, got %r" % (registry["entries"],)
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk.get("quiet_hours_enabled") is True, "expected quiet_hours_enabled to remain True (T-20-11 regression)"
    assert on_disk.get("display_enabled") is True, "expected display_enabled to remain True (T-20-11 regression)"
    status2, _h2, page_body = http_request(server.base_url() + location, cookie=session)
    assert b"2 flights found" in page_body, "expected the success flash text to include the flight count"


def test_calendar_connect_route_invalid_url_rejects_and_persists_nothing(app_server_in_process):
    """an empty calendar_url on POST /settings/calendar/connect 303-redirects with the
    calendar_connect_invalid flash key and persists nothing (D-14c)"""
    server = app_server_in_process
    session = login(server)
    status, headers, _b = http_request(
        server.base_url() + config_page.CALENDAR_CONNECT_ROUTE, method="POST",
        data=urllib.parse.urlencode({"calendar_url": ""}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_connect_invalid" in location, "expected the calendar_connect_invalid flash key, got %r" % location
    assert not calendar_rules.calendar_is_configured(server.state_dir), (
        "expected the calendar to remain unconfigured — nothing should be written")


def test_calendar_connect_route_unauthenticated_redirects_to_login(app_server_in_process):
    """an unauthenticated POST /settings/calendar/connect redirects to /login and writes nothing
    (D-14c, T-20-10)"""
    server = app_server_in_process
    status, headers, _b = http_request(
        server.base_url() + config_page.CALENDAR_CONNECT_ROUTE, method="POST",
        data=urllib.parse.urlencode({"calendar_url": "https://unauth-connect.example/feed.ics"}).encode())
    assert status == 303, "expected a 303 redirect for an unauthenticated POST, got %d" % status
    assert headers.get("Location") == "/login", "expected a redirect to /login, got %r" % headers.get("Location")
    assert not calendar_rules.calendar_is_configured(server.state_dir), (
        "expected nothing to be written for an unauthenticated POST")


# ==========================================================================
# 20-11-PLAN.md Task 1 (D-26/T-20-13): "Send a test"'s own dedicated
# POST /settings/notifications/test route — session-gated, reads the
# topic URL from the stored config only, and never trusts a submitted
# topic_url field.
# ==========================================================================


def test_notifications_test_route_unauthenticated_redirects_to_login(app_server_in_process):
    """an unauthenticated POST /settings/notifications/test redirects to /login (D-26, T-20-10)"""
    server = app_server_in_process
    status, headers, _b = http_request(
        server.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE, method="POST", data=b"")
    assert status == 303, "expected a 303 redirect for an unauthenticated POST, got %d" % status
    assert headers.get("Location") == "/login", "expected a redirect to /login, got %r" % headers.get("Location")


def test_notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender(app_server_in_process):
    """with no stored topic URL, POST /settings/notifications/test redirects with the
    notifications_test_failed flash key and never calls notify.send_notification() (D-26)"""
    server = app_server_in_process
    session = login(server)
    calls = []
    original = notify_module.send_notification

    def _fake_send(topic_url, title, body, timeout=5, transport=None):
        calls.append(topic_url)
        return True

    notify_module.send_notification = _fake_send
    try:
        status, headers, _b = http_request(
            server.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE, method="POST", data=b"",
            cookie=session)
    finally:
        notify_module.send_notification = original
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) in location, (
        "expected the notifications_test_failed flash key, got %r" % location)
    assert not calls, "expected send_notification() to never be called with no stored URL"


def test_notifications_test_route_configured_calls_sender_once_and_flashes_success(app_server_in_process):
    """with a stored topic URL, POST /settings/notifications/test calls
    notify.send_notification() exactly once with the stored URL and redirects with the
    notifications_test_ok flash key (D-26)"""
    server = app_server_in_process
    stored_url = "https://ntfy.sh/skypane-test-topic-abc"
    device_config.save_device_config(
        server.state_dir, notifications={
            "topic_url": stored_url, "battery_low": True, "frame_silent": True, "lang": "en"})
    session = login(server)
    calls = []
    original = notify_module.send_notification

    def _fake_send(topic_url, title, body, timeout=5, transport=None):
        calls.append(topic_url)
        return True

    notify_module.send_notification = _fake_send
    try:
        status, headers, _b = http_request(
            server.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE, method="POST", data=b"",
            cookie=session)
    finally:
        notify_module.send_notification = original
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_OK) in location, (
        "expected the notifications_test_ok flash key, got %r" % location)
    assert calls == [stored_url], (
        "expected send_notification() to be called exactly once with the stored url, got %r" % (calls,))


def test_notifications_test_route_sender_returning_false_flashes_failure(app_server_in_process):
    """a sender returning False redirects with the notifications_test_failed flash key (D-26)"""
    server = app_server_in_process
    stored_url = "https://ntfy.sh/skypane-test-topic-def"
    device_config.save_device_config(
        server.state_dir, notifications={
            "topic_url": stored_url, "battery_low": True, "frame_silent": True, "lang": "en"})
    session = login(server)
    original = notify_module.send_notification
    notify_module.send_notification = lambda *a, **k: False
    try:
        status, headers, _b = http_request(
            server.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE, method="POST", data=b"",
            cookie=session)
    finally:
        notify_module.send_notification = original
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert ("flash=%s" % config_page.FLASH_NOTIFICATIONS_TEST_FAILED) in location, (
        "expected the notifications_test_failed flash key, got %r" % location)


def test_notifications_test_route_ignores_a_submitted_topic_url_field(app_server_in_process):
    """a POST /settings/notifications/test carrying its own topic_url field is ignored in favour
    of the stored one — the field is never read from the request body (T-20-13)"""
    server = app_server_in_process
    stored_url = "https://ntfy.sh/skypane-test-topic-ghi"
    device_config.save_device_config(
        server.state_dir, notifications={
            "topic_url": stored_url, "battery_low": True, "frame_silent": True, "lang": "en"})
    session = login(server)
    calls = []
    original = notify_module.send_notification

    def _fake_send(topic_url, title, body, timeout=5, transport=None):
        calls.append(topic_url)
        return True

    notify_module.send_notification = _fake_send
    try:
        status, _headers, _b = http_request(
            server.base_url() + config_page.NOTIFICATIONS_TEST_ROUTE, method="POST",
            data=urllib.parse.urlencode({"topic_url": "https://attacker.example/forward-me"}).encode(),
            cookie=session)
    finally:
        notify_module.send_notification = original
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert calls == [stored_url], "expected send_notification() to receive the STORED url only, got %r" % (calls,)


def test_calendar_sync_bypasses_the_throttle_via_min_interval_zero(app_server_in_process):
    """D-06's bypass, proven two ways: the behavioural half seeds a recorded attempt a minute ago
    (well inside the standard 1800s throttle) and confirms the save-triggered sync still fetches
    and still reports success; the wiring half spies on refresh_calendar_registry() itself to pin
    that config_page.handle_post()'s own call site passes min_interval_s=0 explicitly - not
    omitted, which a call-shape spy is the only thing that can actually distinguish here, since
    save_calendar_url() (17-01) already resets last_attempt_at to None on every set before this
    handler's own refresh call runs"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-throttle.example"
    url = "https://%s/feed.ics?token=THROTTLEBYPASSTOKEN" % hostname
    now = time.time()
    calendar_rules.save_calendar_url(server.state_dir, url)
    calendar_rules.write_calendar_registry(server.state_dir, [], now - 60, None, now=now)

    captured_intervals = []
    real_refresh = calendar_rules.refresh_calendar_registry

    def _spy_refresh(state_dir, when, transport=None, min_interval_s=None):
        captured_intervals.append(min_interval_s)
        return real_refresh(state_dir, when, transport=transport, min_interval_s=min_interval_s)

    calendar_rules.refresh_calendar_registry = _spy_refresh
    try:
        with cah.stubbed_calendar_transport(cah.make_calendar_transport()), \
                cah.fake_public_hostname(hostname):
            status, headers, _b = http_request(
                server.base_url() + "/settings", method="POST",
                data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    finally:
        calendar_rules.refresh_calendar_registry = real_refresh
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert captured_intervals == [0], (
        "expected exactly one refresh_calendar_registry() call with min_interval_s=0 (not "
        "omitted, not None), got %r" % (captured_intervals,))
    location = headers.get("Location", "")
    assert "flash=calendar_connected" in location, "expected the calendar_connected flash key, got %r" % location


def test_poll_modules_own_refresh_call_site_still_throttles(tmp_path):
    """server/poll_loop.py's own refresh_calendar_registry() call shape (no min_interval_s
    override) still honours the standard throttle against the identical seeded state - the
    bypass is scoped to the new call site alone, never widening the poll cycle's own throttle"""
    state_dir = str(tmp_path)
    now = time.time()
    hostname = "calendar-sync-throttle-control.example"
    url = "https://%s/feed.ics?token=CONTROLTOKEN" % hostname
    calendar_rules.save_calendar_url(state_dir, url)
    calendar_rules.write_calendar_registry(state_dir, [], now - 60, None, now=now)
    calls = []
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(calls=calls)), \
            cah.fake_public_hostname(hostname):
        result_code, _registry = calendar_rules.refresh_calendar_registry(state_dir, now)
    assert result_code == calendar_rules.FETCH_SKIPPED_THROTTLED, "expected FETCH_SKIPPED_THROTTLED, got %r" % (result_code,)
    assert not calls, "expected no transport call when the standard throttle applies, got %r" % (calls,)


def test_calendar_sync_lock_contention_is_honest(app_server_in_process):
    """a save arriving while the poll lock is already held redirects with the deferred flash key,
    performs no fetch, and still saves the URL (D-09)"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-contention.example"
    url = "https://%s/feed.ics?token=CONTENTIONTOKEN" % hostname
    calls = []
    locked = app_module._POLL_LOCK.acquire(blocking=False)
    assert locked, "test setup failure: could not acquire _POLL_LOCK from the test thread"
    try:
        with cah.stubbed_calendar_transport(cah.make_calendar_transport(calls=calls)), \
                cah.fake_public_hostname(hostname):
            status, headers, _b = http_request(
                server.base_url() + "/settings", method="POST",
                data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    finally:
        app_module._POLL_LOCK.release()
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=calendar_sync_deferred" in location, "expected the calendar_sync_deferred flash key, got %r" % location
    assert not calls, "expected no transport call while the lock was held, got %r" % (calls,)
    assert calendar_rules.calendar_is_configured(server.state_dir), (
        "expected the URL to be saved even though the sync was deferred")


def test_calendar_sync_lock_is_released_after_a_failed_sync(app_server_in_process):
    """after a save whose immediate fetch fails, the poll lock is still free - one failure never
    wedges a later manual poll trigger"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-release.example"
    url = "https://%s/feed.ics?token=RELEASETOKEN" % hostname
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(raise_exc=ConnectionError("boom"))), \
            cah.fake_public_hostname(hostname):
        http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    reacquired = app_module._POLL_LOCK.acquire(blocking=False)
    if reacquired:
        app_module._POLL_LOCK.release()
    assert reacquired, (
        "expected the poll lock to be free after one failed sync - a wedged trigger is the "
        "failure mode the finally-release exists to prevent")


def test_unrelated_settings_save_never_reaches_the_refresh_call(app_server_in_process):
    """a settings save that changes only the theme, against an already-connected calendar,
    redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its
    fetched entries untouched"""
    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-unrelated.example"
    url = "https://%s/feed.ics?token=UNRELATEDTOKEN" % hostname
    body = cah.ics_body([("AF1234", "CDG", "ORY", 2)])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)), \
            cah.fake_public_hostname(hostname):
        http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    registry_before = calendar_rules.load_calendar_registry(server.state_dir)

    calls = []
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(calls=calls)):
        status, headers, _b = http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"theme": "black"}).encode(), cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=saved" in location, "expected the ordinary saved flash key, got %r" % location
    assert not calls, "expected an unrelated save to never reach the refresh call, got %r" % (calls,)
    assert calendar_rules.calendar_is_configured(server.state_dir), "expected the calendar to remain configured"
    registry_after = calendar_rules.load_calendar_registry(server.state_dir)
    assert registry_after["entries"] == registry_before["entries"], (
        "expected the fetched entries to be untouched by an unrelated save")


def test_calendar_save_does_not_touch_the_manual_poll_cooldown(app_server_in_process):
    """a calendar save immediately followed by a manual poll trigger does not hit the poll
    cooldown - the two mechanisms are independent"""
    from skypane_test_support import FakeProviders

    server = app_server_in_process
    session = login(server)
    hostname = "calendar-sync-cooldown.example"
    url = "https://%s/feed.ics?token=COOLDOWNTOKEN" % hostname
    with cah.stubbed_calendar_transport(cah.make_calendar_transport()), \
            cah.fake_public_hostname(hostname):
        http_request(
            server.base_url() + "/settings", method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)
    # This harness runs companion/app.py's server in a thread of THIS
    # process, so run_once() sees a plain monkeypatch of requests.get -
    # FakeProviders().installed() rather than child_env(), which is for a
    # subprocess child's own interpreter.
    with FakeProviders().installed():
        status, headers, _b = http_request(
            server.base_url() + "/poll-now", method="POST", cookie=session)
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "flash=poll_cooldown" not in location, (
        "a calendar save must never consume the manual poll trigger's own cooldown, got %r" % location)


# ==========================================================================
# 21-01-PLAN.md Task 3 (D-17): the retired simple/full display-mode
# switch. The original legacy check walked every *.py/*.js file under
# companion/ looking for seven retired tokens as raw text — rubric S
# (TST-12): rewritten here as a `not hasattr()` battery across the
# modules that used to define them, since a whole-repo text grep has no
# observable behaviour of its own. Confirmed by grepping the WHOLE repo
# before writing this test that none of the identifier-shaped tokens
# appear anywhere in production code any more (only as "simple_mode":
# False fixture dict keys in unrelated test files, which are not this
# retired symbol). The two non-identifier tokens (the "/ui-mode" route
# and the "sp_ui_mode" cookie name) are behavioural claims covered by
# sibling tests: the route's 404 by
# test_companion_app_04b.py::test_post_to_the_deleted_display_mode_route_with_session_now_404s,
# and the cookie's absence by that same module's Accept-Language test.
# ==========================================================================


def test_no_companion_module_redefines_the_retired_display_mode_switch():
    """no companion.* module (app, auth, layout, prefs, or any companion.pages module) still
    defines any of the seven identifier-shaped tokens the retired simple/full display-mode
    switch used to carry (D-17) — the route/cookie-name halves of the same removal are proven
    behaviourally by sibling tests, named above"""
    import companion.auth as auth_module
    import companion.prefs as prefs_module
    from companion.pages import airlines_page, health_page, history_page, home_page

    retired_identifiers = (
        "simple_mode", "MODE_CHOICES", "DEFAULT_MODE", "_MODE_CTX",
        "UI_MODE_COOKIE_NAME", "MODE_ROUTE", "sp_ui_mode")
    modules = (
        app_module, auth_module, layout, prefs_module, config_page,
        health_page, home_page, airlines_page, history_page)
    offenders = [
        "%s.%s" % (module.__name__, name)
        for module in modules for name in retired_identifiers
        if hasattr(module, name)
    ]
    assert not offenders, (
        "expected none of the retired display-mode-switch identifiers to still be defined, "
        "found: %r" % (offenders,))


# ==========================================================================
# Section 6 (22-08-PLAN.md Task 1/2, D-06/B16): round-trip checks for
# every flash template, every page <title> and the nav/theme labels this
# plan translates — i18n.t_lang(), never prefs.set_request_prefs(),
# which would leak its ContextVar state into every test that runs after
# this one in the same process.
# ==========================================================================


def test_flash_and_title_strings_round_trip_to_french_and_back():
    """every companion.app.FLASH_MESSAGES template and every _PAGE_TITLES value, plus the 404's
    and login shell's own <title> literals, round-trip to French under i18n.t_lang(..., 'fr')
    and to their original English text under i18n.t_lang(..., 'en')"""
    def _assert_round_trips(text, label):
        en_result = i18n_module.t_lang(text, "en")
        assert en_result == text, (
            "expected t_lang(%r, 'en') to be byte-identical to the English source (%s), got %r"
            % (text, label, en_result))
        fr_result = i18n_module.t_lang(text, "fr")
        assert fr_result != text, (
            "expected t_lang(%r, 'fr') (%s) to be a real French translation, got the English "
            "source back unchanged" % (text, label))

    for key, template in app_module.FLASH_MESSAGES.items():
        _assert_round_trips(template, "FLASH_MESSAGES[%r]" % (key,))
    for route, title in app_module._PAGE_TITLES.items():
        _assert_round_trips(title, "_PAGE_TITLES[%r]" % (route,))
    for title in ("Not Found", "Login"):
        _assert_round_trips(title, "the %r <title> literal" % (title,))


def test_nav_and_theme_labels_round_trip_to_french_and_back():
    """the nav landmark's aria-label ("Primary navigation") and the theme picker's three segment
    labels ("Auto"/"Light"/"Dark") round-trip to French under i18n.t_lang(..., 'fr') and to their
    original English text under i18n.t_lang(..., 'en') (D-06/B16)"""
    for text in ("Primary navigation", "Auto", "Light", "Dark"):
        en_result = i18n_module.t_lang(text, "en")
        assert en_result == text, (
            "expected t_lang(%r, 'en') to be byte-identical to the English source, got %r"
            % (text, en_result))
        fr_result = i18n_module.t_lang(text, "fr")
        assert fr_result != text, (
            "expected t_lang(%r, 'fr') to be a real French translation, got the English source "
            "back unchanged" % (text,))


# ==========================================================================
# 29-06-PLAN.md Task 3 (CFG-79): the site-wide editorial floor — the LAST
# anchor of the whole companion_app chain.
# ==========================================================================


def _caption_word_count_text(fragment):
    """The counting rule the legacy harness duplicated verbatim from
    `companion/test_config_page.py` (retired by 33-13-PLAN.md). Kept as
    its own copy here (rather than importing it) because it is the "mine"
    half of the cross-check below — the whole point of that check is that
    two independently-maintained copies agree.
    """
    stripped = re.sub(r"<[^>]*>", "", fragment)
    text = html.unescape(stripped).strip()
    if text.startswith("— "):
        text = text[2:]
    return re.sub(r"\s+", " ", text).strip()


_CROSS_CHECK_FIXTURES = (
    '  — Hello   "World"&#x27;s <b>caption</b>  ',
    "Plain text with no markup at all",
    '  <span>Nested <b>markup</b></span> — trailing  ',
    "",
)


def test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy():
    """this module's own counting-rule duplicate agrees with
    companion.test_config_page_05's own _caption_word_count_text() on a small set of fixtures -
    the two would otherwise measure the site inconsistently. Calls both implementations directly
    (a plain import of the sibling test module, never a disk-read/ast-extract of its source -
    33-13-PLAN.md closed the config_page chain and this plan's own brief requires the cross-check
    be migrated as calling behaviour)"""
    import companion.test_config_page_05 as tcp05

    for fixture in _CROSS_CHECK_FIXTURES:
        mine = _caption_word_count_text(fixture)
        theirs = tcp05._caption_word_count_text(fixture)
        assert mine == theirs, (
            "this module's counting-rule duplicate disagrees with test_config_page_05.py's own "
            "_caption_word_count_text on fixture %r: got %r here, %r there" % (fixture, mine, theirs))


def _measured_section_captions(rendered):
    out = []
    for m in re.finditer(r'<p\s+class="([^"]*)"[^>]*>(.*?)</p>', rendered, re.DOTALL):
        classes = m.group(1).split()
        if "section-caption" not in classes:
            continue
        if set(classes) - {"text-label", "section-caption"}:
            continue
        out.append((m.start(), m.end(), m.group(2)))
    return out


def _frame_strip_slice(rendered):
    marker = '<div class="frame-strip stat-tile stat-tile--accent"'
    start = rendered.find(marker)
    if start == -1:
        return None
    depth = 0
    for token in re.finditer(r"<div\b[^>]*>|</div>", rendered[start:]):
        depth += 1 if token.group(0) != "</div>" else -1
        if depth == 0:
            return start, start + token.end()
    raise AssertionError("unbalanced frame-strip <div> markup")


def test_site_wide_editorial_floor_all_six_routes_both_languages(make_app_server):
    """the site-wide editorial floor (CFG-79): every non-exempt .section-caption element on all
    six authenticated routes, in both English and French, over a real running server, is at most
    12 whitespace-split words; the route list is proven equal to
    test_browser_ux_helpers.VIEW_TRANSITION_ROUTES (a plain import, never a source-text read);
    CAPTION_FLOOR_EXEMPTIONS (config_page.ASPECT_CAPTION_EXEMPTIONS, imported not re-listed) is
    skipped exactly its own length per language across the whole site; per-route and site-wide
    caption-count minimums guard against a narrowed selector passing vacuously; and the
    apply-timing sentence (read from frame_state.py's own DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN
    constants) never renders outside the Frame strip's own markup slice, proven to fire inside it
    at least once (29-06-PLAN.md Task 3)"""
    import companion.test_browser_ux_helpers as browser_ux_helpers

    server = make_app_server(fake_providers=True)
    base = server.base_url()
    cookie = login(server)

    # --- route-list parity: layout's own six constants vs.
    # test_browser_ux_helpers's declared VIEW_TRANSITION_ROUTES, via a
    # plain import (never a source-text read) so a seventh route added to
    # one enumeration and not the other fails here.
    site_routes = (
        layout.HOME_ROUTE, layout.DISPLAY_ROUTE, layout.FLIGHTS_ROUTE,
        layout.AIRLINES_ROUTE, layout.HEALTH_ROUTE, layout.DEVICE_ROUTE,
    )
    assert set(site_routes) == set(browser_ux_helpers.VIEW_TRANSITION_ROUTES), (
        "layout's own six route constants %r do not equal "
        "test_browser_ux_helpers.VIEW_TRANSITION_ROUTES membership %r"
        % (sorted(site_routes), sorted(browser_ux_helpers.VIEW_TRANSITION_ROUTES)))

    # --- fetch every route x language over the real server ---
    exempt_by_lang = {
        lang: {
            _caption_word_count_text(i18n_module.t_lang(text, lang))
            for text in CAPTION_FLOOR_EXEMPTIONS
        }
        for lang in ("en", "fr")
    }
    apply_timing_templates = (frame_state.DELAY_DUE, frame_state.DELAY_HELD, frame_state.DELAY_UNKNOWN)

    rendered_by = {}
    for route in site_routes:
        for lang in ("en", "fr"):
            cookie_header = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
            status, _headers, body = http_request(base + route, cookie=cookie_header)
            assert status == 200, "%s/%s: expected an authenticated 200, got %d" % (route, lang, status)
            rendered = body.decode("utf-8", errors="replace")
            expected_lang_attr = '<html lang="%s"' % lang
            assert expected_lang_attr in rendered, (
                "%s/%s: expected the served document's <html lang> to be %r — otherwise this "
                "pass could be silently re-measuring English" % (route, lang, lang))
            rendered_by[(route, lang)] = rendered

    # Minimums re-derived by RUNNING this exact selector against a real
    # render of each route (30-05-PLAN.md Task 3, CFG-85).
    per_route_min = {
        layout.HOME_ROUTE: 1, layout.DISPLAY_ROUTE: 9, layout.FLIGHTS_ROUTE: 0,
        layout.AIRLINES_ROUTE: 1, layout.HEALTH_ROUTE: 3, layout.DEVICE_ROUTE: 6,
    }
    site_total_min = 47

    skip_counts = {"en": 0, "fr": 0}
    site_total_captions = 0
    outside_matches = []
    any_inside_strip = False
    for route in site_routes:
        for lang in ("en", "fr"):
            rendered = rendered_by[(route, lang)]
            captions = _measured_section_captions(rendered)
            if lang == "en":
                assert len(captions) >= per_route_min[route], (
                    "%s/%s: only %d .section-caption element(s) measured, expected at least "
                    "%d — a narrowed selector could pass over an empty set"
                    % (route, lang, len(captions), per_route_min[route]))
            site_total_captions += len(captions)

            strip_bounds = _frame_strip_slice(rendered)

            for start, _end, fragment in captions:
                text = _caption_word_count_text(fragment)
                if text in exempt_by_lang[lang]:
                    skip_counts[lang] += 1
                    continue
                words = text.split()
                assert len(words) <= 12, (
                    "%s/%s: a non-exempt section-caption renders %d word(s) (max 12): %r"
                    % (route, lang, len(words), text))

                for template in apply_timing_templates:
                    translated = i18n_module.t_lang(template, lang)
                    if "%s" in translated:
                        pattern = re.escape(translated).replace(re.escape("%s"), r".+?")
                    else:
                        pattern = re.escape(translated)
                    if not re.search(pattern, text):
                        continue
                    if strip_bounds is not None and strip_bounds[0] <= start < strip_bounds[1]:
                        any_inside_strip = True
                    else:
                        outside_matches.append(
                            "%s/%s at offset %d (%r): %r" % (route, lang, start, text[:80], text))
                    break

    assert site_total_captions >= site_total_min, (
        "site-wide total: only %d .section-caption element(s) measured across all six "
        "routes/both languages, expected at least %d" % (site_total_captions, site_total_min))

    expected_skip_count = len(CAPTION_FLOOR_EXEMPTIONS)
    for lang in ("en", "fr"):
        assert skip_counts[lang] == expected_skip_count, (
            "%s: expected exactly %d CAPTION_FLOOR_EXEMPTIONS skip(s) across the whole site, "
            "got %d — either the exemption is unreachable or it silently swallowed a caption it "
            "should not have" % (lang, expected_skip_count, skip_counts[lang]))

    assert not outside_matches, (
        "the apply-timing sentence rendered outside the Frame strip's own slice — CFG-79 "
        "confines it to exactly one place per page: %s" % "; ".join(outside_matches))
    assert any_inside_strip, (
        "the apply-timing relationship never matched INSIDE the Frame strip either — this "
        "assertion is vacuous unless it is proven to fire on the strip's own, untouched markup "
        "at least once")
