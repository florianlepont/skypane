"""Build 68.1-PROPOSAL-P15-REALISTIC.html from the served Home page.

Run from the repo root: python3 -I <this file> OUTPUT.html

It starts the seeded companion app (test-support/provisioned_fleet.py, the
helper capture_pages.py uses in local mode), gives one frame a current flight
per scenario, fetches the served Home HTML in English and French, inlines
companion/static/style.css and style-home.css, strips scripts and every
network reference, and writes one standalone file. TODAY is the served page;
PROPOSED is the same page with only the P15 change applied (markup move plus
an overlay stylesheet). Nothing in the product is modified.
"""
import base64
import json
import os
from datetime import datetime, timedelta, timezone
import re
import sys
import tempfile
import urllib.request

REPO = os.getcwd()
for entry in (os.path.join(REPO, "test-support"), REPO):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import companion_app_server  # noqa: E402
import provisioned_fleet  # noqa: E402
from server import history_db  # noqa: E402

SCENARIOS = {
    "A": dict(callsign="AF1234", state="departing", airline="Air France", origin="LFPO",
              destination="LFLL", aircraft_type="A320", registration="F-GKXA"),
    "B": dict(callsign="EZY12AB", state="arriving", airline="easyJet", origin="EGKK",
              destination="LFPO", aircraft_type="A319", registration=None),
    "C": dict(callsign="WZZ6ABCD", state="arriving", airline="Wizz Air", origin="LROP",
              destination="LFPO", aircraft_type=None, registration="HA-LTA"),
    "D": dict(callsign="TVF65GH", state="departing", airline=None, origin=None,
              destination=None, aircraft_type=None, registration=None),
}

OVERLAY_CSS = """
/* P15 overlay: the only difference between TODAY and PROPOSED. */
.home-flight { flex-wrap: wrap; container-type: inline-size; }
.home-flight > .home-flight__call {
  flex: 1 0 100%;
  font-size: min(56px, 17cqw);
  line-height: 1;
  letter-spacing: -0.04em;
  margin: 0 0 var(--space-xs);
}
.home-flight__meta { flex: 1 1 0; min-width: 0; }
.home-flight__type { font-size: var(--font-caption-size); }
.home-flight__id { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-sm); }
.home-flight__reg {
  font-family: var(--font-mono);
  font-size: var(--font-caption-size);
  line-height: 1.2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text);
  border: 1px solid var(--color-text);
  border-radius: 6px;
  padding: 2px var(--space-sm);
}
"""
NO_MOTION_CSS = "*,*::before,*::after{animation:none!important;transition:none!important}"


def fetch(url, cookie, binary=False):
    req = urllib.request.Request(url, headers={"Cookie": cookie})
    data = urllib.request.urlopen(req).read()
    return data if binary else data.decode("utf-8")


def seed_and_fetch(key, scenario, workdir):
    state_dir = os.path.join(workdir, "state-" + key)
    ids = provisioned_fleet.provision_fleet(state_dir, live_owner="a")
    device_dir = provisioned_fleet.device_dir(state_dir, ids.a1)
    provisioned_fleet.mark_checked_in(state_dir, ids.a1)
    with history_db.open_db(device_dir) as conn:
        fields = {k: v for k, v in scenario.items() if k not in ("registration", "state")}
        history_db.record_device_health(
            conn, (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(timespec="seconds"),
            battery_mv=3890, fw_version="1.4.2")
        detected = datetime.now(timezone.utc) - timedelta(minutes=3)
        history_db.record_runway_event(
            conn, ts=detected.isoformat(timespec="seconds"),
            confirmed_state=scenario["state"], corroborated=True, tracked_runway="03",
            route_source="adsbdb", gallery_name="sample.png", **fields)
    server = companion_app_server.AppServer(state_dir)
    server.start()
    try:
        cookie = companion_app_server.session_cookie_for_state_dir(
            state_dir, email="user-a@example.test", role="user")
        base = server.base_url()
        preview = fetch(
            "%s/devices/%s/frame-preview/white.png?state=%s&size=small&layout=classic" % (
                base, ids.a1, scenario["state"]), cookie, binary=True)
        with open(os.path.join(device_dir, "gallery", "sample.png"), "wb") as fh:
            fh.write(preview)
        out = {}
        for lang in ("en", "fr"):
            out[lang] = fetch("%s/devices/%s/" % (base, ids.a1),
                              cookie + "; sp_ui_lang=" + lang)
        return out, preview, ids.a1
    finally:
        server.stop()


def standalone(html, theme, preview_b64):
    """Strip scripts and network references; keep the served body."""
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<template\b.*?</template>", "", html, flags=re.S)
    html = re.sub(r"<dialog\b.*?</dialog>", "", html, flags=re.S)
    html = re.sub(r'<div class="splash".*?</p></div>\n', "", html, count=1, flags=re.S)
    html = re.sub(r'<img class="preview-frame__image" src="[^"]*"',
                  '<img class="preview-frame__image" src="data:image/png;base64,%s"' % preview_b64, html)
    body = html[html.index("<body"):html.index("</body>") + 7]
    lang = re.search(r'<html lang="(\w+)"', html).group(1)
    return lang, theme, body


def propose(body, sc):
    """The P15 markup change: callsign out of the text column to a full-width row,
    route and aircraft type on their own lines, registration as a plate."""
    call = re.search(r'<div class="home-flight__call tnum">.*?</div>', body).group(0)
    body = body.replace(call, "", 1)
    body = re.sub(r'(<h2 class="visually-hidden" id="home-flight">[^<]*</h2>)', r"\1" + call, body, count=1)
    route = ""
    if sc["origin"] and sc["destination"]:
        route = '<div class="home-flight__details">%s → %s</div>' % (sc["origin"], sc["destination"])
    ident = ""
    parts = []
    if sc["aircraft_type"]:
        parts.append('<span class="home-flight__type">%s</span>' % sc["aircraft_type"])
    if sc["registration"]:
        parts.append('<span class="home-flight__reg">%s</span>' % sc["registration"])
    if parts:
        ident = '<div class="home-flight__id">%s</div>' % "".join(parts)
    body = re.sub(r'<div class="home-flight__details">.*?</div>', lambda m: route + ident, body, count=1)
    if not route and ident:
        pass
    if not re.search(r'home-flight__details', body) and ident and ident not in body:
        body = body.replace('<div class="home-flight__detected">', ident + '<div class="home-flight__detected">', 1)
    return body


# (scenario, lang, theme, width, caption)
CELLS = [
    ("A", "en", "light", 360), ("B", "en", "light", 360),
    ("C", "en", "light", 360), ("D", "en", "light", 360),
    ("A", "en", "dark", 360), ("C", "en", "dark", 360),
    ("A", "fr", "light", 360), ("C", "fr", "dark", 360),
    ("A", "en", "light", 1280), ("C", "fr", "dark", 1280),
]


def main(out_path):
    css = "".join(open(os.path.join(REPO, "companion/static", name)).read()
                  for name in ("style.css", "style-home.css")) + NO_MOTION_CSS
    pages = {}
    with tempfile.TemporaryDirectory() as workdir:
        for key, sc in SCENARIOS.items():
            html_by_lang, preview, _ = seed_and_fetch(key, sc, workdir)
            b64 = base64.b64encode(preview).decode()
            for lang, html in html_by_lang.items():
                pages[(key, lang)] = standalone(html, "light", b64)[2]
    items = []
    for key, lang, theme, width in CELLS:
        sc = SCENARIOS[key]
        today = pages[(key, lang)]
        items.append(dict(scenario=key, lang=lang, theme=theme, width=width,
                          today=today, proposed=propose(today, sc), data=sc))
    payload = json.dumps(dict(css=css, overlay=OVERLAY_CSS, items=items)).replace("</", "<\\/")
    template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p15_realistic_template.html")).read()
    with open(out_path, "w") as fh:
        fh.write(template.replace("/*__PAYLOAD__*/null", payload))


if __name__ == "__main__":
    main(sys.argv[1])
