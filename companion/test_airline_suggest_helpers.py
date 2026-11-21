"""Shared rig for the airline-name suggestion tests: an in-process companion
with a seeded fleet, one frame holding unidentified prefixes, the suggestion
service switched on with a dummy key and a counting fake in place of the
network client. Holds no test of its own."""
import json
import os
import urllib.parse

from fake_anthropic import DUMMY_KEY

import companion.test_status_pages_helpers as shp
import fleet_console_support as fx
from companion import auth, device_scope
from companion_app_server import InProcessAppServer, http_request, with_csrf
from server import fleet_db
from server.plane import airline_suggest as ais

__test__ = False

EDITOR = "/airlines/manage"
STAMP = "2026-11-17T10:29:00+00:00"
CO_EMAIL = "co-manager@example.test"
GAPS = {
    "OCN": (9, "OCN123"), "ITI": (8, "ITI45"), "ZLN": (7, "ZLN9"), "CMA": (6, "CMA7"),
    "QQQ": (5, "QQQ1"), "RRR": (4, "RRR1")}


class FakeClient:
    """Stands in for the network client: scripted replies, every body seen."""

    def __init__(self, name="Oceanair", reply=None, error=None):
        self.name = name
        self.reply = reply
        self.error = error
        self.bodies = []

    def complete(self, body):
        self.bodies.append(body)
        if self.error is not None:
            raise self.error
        if self.reply is not None:
            return self.reply
        from fake_anthropic import airline_body
        return ais.Reply(200, airline_body(self.name), "")


class Rig:
    def __init__(self, server, seed, cookies, client):
        self.server = server
        self.seed = seed
        self.cookies = cookies
        self.client = client
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)
        self.frame = "/devices/%s" % seed.owned_id

    @property
    def root(self):
        return self.server.state_dir

    def cookie(self, who, lang=None):
        base = self.cookies.get(who)
        if lang:
            pair = "%s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
            return "%s; %s" % (base, pair) if base else pair
        return base

    def get(self, who, path, lang=None):
        status, headers, body = http_request(self.server.url(path), cookie=self.cookie(who, lang))
        return status, headers, body.decode("utf-8", "replace")

    def post(self, who, path, form, lang=None, csrf=True):
        cookie = self.cookie(who, lang)
        data = with_csrf(cookie, form) if csrf else urllib.parse.urlencode(form).encode()
        status, headers, body = http_request(
            self.server.url(path), method="POST", cookie=cookie, data=data,
            extra_headers={"Origin": self.server.base_url()})
        return status, headers, body.decode("utf-8", "replace")

    def suggest(self, prefix="OCN", index="0", who="admin", lang=None, **kwargs):
        status, _h, body = self.post(
            who, self.frame + "/airlines/suggest", {"prefix": prefix, "index": index},
            lang=lang, **kwargs)
        return status, (json.loads(body) if status == 200 else body)

    def seed_gaps(self, prefixes=("OCN", "ITI", "ZLN", "CMA")):
        shp.seed_unresolved_prefixes(self.owned_dir, {
            p: {"count": GAPS[p][0], "first_seen": STAMP, "last_seen": STAMP,
                "example_callsign": GAPS[p][1]} for p in prefixes})

    def write_cache(self, entries):
        """Write `{prefix: (state, name)}` straight into the cache file."""
        doc = {p: {"state": e[0], "model": ais.MODEL_ID, "asked_at": STAMP,
                   **({"name": e[1]} if len(e) > 1 else {})} for p, e in entries.items()}
        with open(ais.cache_path(self.root), "w") as handle:
            json.dump({"entries": doc, "calls": []}, handle)

    def files(self):
        """Every file under the root by relative path with its bytes."""
        found = {}
        for base, _dirs, names in os.walk(self.root):
            for name in names:
                if name.endswith((".json", ".png")):
                    path = os.path.join(base, name)
                    with open(path, "rb") as handle:
                        found[os.path.relpath(path, self.root)] = handle.read()
        return found

    def audit(self):
        conn = fleet_db.connect(self.root)
        try:
            return [dict(row) for row in fleet_db.list_audit(conn, "all", 50, 0)]
        finally:
            conn.close()


def make_rig(tmp_path, monkeypatch, key=DUMMY_KEY, client=None):
    monkeypatch.delenv(ais.ENV_BASE_URL, raising=False)
    if key is None:
        monkeypatch.delenv(ais.ENV_API_KEY, raising=False)
    else:
        monkeypatch.setenv(ais.ENV_API_KEY, key)
    client = client if client is not None else FakeClient()
    monkeypatch.setattr(ais, "make_client", lambda: client)
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "admin": fx.admin_cookie(state_dir),
        "anonymous": None,
    }
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()
    return Rig(server, seed, cookies, client)


def rig_with_gaps(tmp_path, monkeypatch):
    """The body of each test module's own `rig` fixture: the rig with the
    four unidentified prefixes seeded, stopped afterwards."""
    built = make_rig(tmp_path, monkeypatch)
    built.seed_gaps()
    yield built
    built.server.stop()
