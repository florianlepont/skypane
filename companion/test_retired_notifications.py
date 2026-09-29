"""The Device page, its routes and its settings save carry no push-alert
feature, and a device_config.json written by an older version that still
holds a stored alert group keeps loading without ever surfacing it.

Every check asserts on served HTML, HTTP status codes, handle_post()'s
return value or bytes on disk.
"""
import json
import os

import pytest

from companion import auth
from companion.pages import config_page
from companion_app_server import http_request, login
from server import device_config

_RETIRED_ROUTE = "/settings/notifications/test"
_LEGACY_TOPIC_URL = "https://push.example/secret-topic"


def _device_page(server, cookie, lang):
    cookie_header = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    status, _headers, body = http_request(
        server.base_url() + "/device", cookie=cookie_header)
    assert status == 200, "expected an authenticated 200 for /device, got %d" % status
    return body.decode("utf-8", errors="replace")


def _write_legacy_config(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, device_config.DEVICE_CONFIG_FILENAME), "w") as fh:
        json.dump({
            "theme": "black",
            "notifications": {
                "topic_url": _LEGACY_TOPIC_URL,
                "battery_low": True,
                "frame_silent": True,
                "lang": "fr",
            },
        }, fh)


@pytest.mark.parametrize("lang, send_test_text, intro", [
    ("en", "Send a test", "— the light on the frame."),
    ("fr", "Envoyer un test", "— le voyant du cadre."),
])
def test_device_page_has_no_push_alert_card(app_server_in_process, lang, send_test_text, intro):
    """the Device page carries no topic-URL field, no send-a-test form and no
    push-topic wording, and its 'How it tells you' section introduces only the
    frame's light while still holding the Diagnostic LED card"""
    server = app_server_in_process
    rendered = _device_page(server, login(server), lang)
    assert 'id="notifications-topic-url"' not in rendered
    assert _RETIRED_ROUTE not in rendered
    assert "Push topic URL" not in rendered
    assert send_test_text not in rendered
    assert 'id="%s"' % config_page.DEVICE_TELLS_SECTION_ID in rendered
    assert intro in rendered
    assert "phone" not in rendered.split('id="%s"' % config_page.DEVICE_TELLS_SECTION_ID, 1)[1].split(
        'id="%s"' % config_page.DEVICE_POLL_SECTION_ID, 1)[0]
    assert config_page.QUICK_LED_STATE_ID in rendered


def test_device_page_never_renders_a_legacy_stored_topic_url(app_server_in_process):
    """a device_config.json still holding a legacy alert object renders the
    Device page normally and never echoes the stored topic URL"""
    server = app_server_in_process
    _write_legacy_config(server.state_dir)
    session = login(server)
    for lang in ("en", "fr"):
        rendered = _device_page(server, session, lang)
        assert _LEGACY_TOPIC_URL not in rendered
        assert "secret-topic" not in rendered


def test_retired_test_route_answers_404_signed_out_and_signed_in(app_server_in_process):
    """POST /settings/notifications/test is not a route: 404 both signed out
    and signed in, like any unknown POST path"""
    server = app_server_in_process
    url = server.base_url() + _RETIRED_ROUTE
    status_out, _h, _b = http_request(url, method="POST", data=b"")
    assert status_out == 404, "expected 404 signed out, got %d" % status_out
    status_in, _h, _b = http_request(url, method="POST", data=b"", cookie=login(server))
    assert status_in == 404, "expected 404 signed in, got %d" % status_in


def test_settings_save_ignores_crafted_push_alert_fields(tmp_path):
    """a Device-scope save carrying crafted push-alert fields still saves,
    and the crafted URL never reaches device_config.json"""
    crafted = "https://attacker.example/forward-me"
    flash_key = config_page.handle_post(
        {
            "scope": config_page.SCOPE_DEVICE,
            "notifications_topic_url": crafted,
            "notifications_battery": "1",
            "notifications_silent": "1",
        },
        {"state_dir": str(tmp_path), "lang": "en"})
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    path = os.path.join(str(tmp_path), device_config.DEVICE_CONFIG_FILENAME)
    on_disk = b""
    if os.path.exists(path):
        with open(path, "rb") as fh:
            on_disk = fh.read()
    assert crafted.encode() not in on_disk
    assert b"attacker.example" not in on_disk
