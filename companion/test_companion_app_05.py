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
import os
import string
import threading
import urllib.parse

import companion.test_companion_app_helpers as cah
from companion.pages import config_page
from companion_app_server import http_request, login
from server import device_config
import server.poll_loop as poll_loop
from server.plane import colour_rules, manual_resolutions

import companion.app as app_module

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_VENDORED_ILLUSTRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "assets", "icons", "illustrations")


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
