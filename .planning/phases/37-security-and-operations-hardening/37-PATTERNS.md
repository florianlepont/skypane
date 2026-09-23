# Phase 37: Security and operations hardening - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 32 (15 modified, 17 new)
**Analogs found:** 28 / 32

Line numbers are from `main` at `a2bf2db`. Phase 32 (pytest), Phase 33 (test
migration) and Phase 36 (`byos_server.py`, atomic writes) will move some of
them. Executors must re-read the anchors below (grep the quoted symbol, not the
line number) before editing (D-02).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `companion/auth.py` (keyed `LoginThrottle`, `client_ip()`) | utility (security) | request-response | itself, `LoginThrottle` `auth.py:301-356` | exact (in-place rewrite) |
| `companion/app.py` (throttle key, `_post_origin_ok`, 403 page, `--bind`, offbox env const) | controller | request-response | itself: `_handle_login_post` :3053, `do_POST` :3453, `_not_found_page` :1712, `build_parser`/`main` :3627-3667, `SLEEP_ENV_VAR` :146-153 | exact |
| `companion/pages/health_page.py` (off-box backup card + severity) | component (page) | transform (file read -> HTML) | `_pipeline_section` :2647, registry card in `render()` :4440-4480, `overall_severity` :2039 | exact |
| `companion/i18n_fr/health.py` (FR strings) | config (catalogue) | n/a | itself :106-112, :191-195 | exact |
| `companion/i18n_fr/common.py` (FR for 403 page strings) | config (catalogue) | n/a | `companion/i18n_fr/health.py` | exact |
| `deploy/Caddyfile` (HSTS) | config | n/a | itself, both site blocks :45, :94 | exact |
| `deploy/skypane-byos.service` | config (systemd) | n/a | itself :13-36 | exact |
| `deploy/skypane-companion.service` (`--bind 127.0.0.1`, `current/` paths, hardening) | config (systemd) | n/a | itself :57-77 | exact |
| `deploy/skypane-poll.service` | config (systemd) | n/a | itself :91-108 | exact |
| `deploy/skypane-backup.service` (new) | config (systemd oneshot) | batch | `deploy/skypane-poll.service` | exact |
| `deploy/skypane-backup.timer` (new) | config (systemd timer) | batch | `deploy/skypane-poll.timer` | exact |
| `deploy/deploy.sh` (rewrite: `git archive \| ssh` + activate) | script (transport) | file-I/O | itself | exact |
| `deploy/activate.sh` (new, VPS root) | script (ops) | batch | `deploy/provision.sh` (root guard, host regex, anchored sed, install/daemon-reload) | role-match |
| `deploy/provision.sh` (release dirs, backup user, env chown, sshd drop-in) | script (ops) | batch | itself | exact |
| `deploy/skypane.env.example` (`SKYPANE_OFFBOX_MARKER`) | config | n/a | itself, `SKYPANE_CADDY_ACCESS_LOG` block | exact |
| `deploy/README.md` | docs | n/a | itself :115-140, :262-271 | exact |
| `deploy/backup/skypane_backup.py` (new) | service (CLI job) | batch / file-I/O | `server/poll_loop.py` `build_parser`/`main` :1943-1987 + `byos_server.save_state` :152-156 | role-match |
| `deploy/backup/backup_gate.py` (new) | service (forced command) | request-response (stdin/stdout) | same as above (argparse-free CLI + atomic write) | partial |
| `deploy/backup/install-backup-key.sh` (new) | script (ops) | batch | `deploy/provision.sh` | role-match |
| `deploy/backup/mac/skypane-backup-pull.sh` (new, POSIX sh) | script (client) | file-I/O | `deploy/deploy.sh` (header/usage/`echo "==>"` style) | partial (bash vs sh) |
| `deploy/backup/mac/skypane-backup-pull.plist.template` (new) | config (launchd) | n/a | none | no analog |
| `deploy/backup/mac/install-launchagent.sh` (new) | script | batch | `deploy/provision.sh` | partial |
| `.github/workflows/ci.yml` (env: secrets, shellcheck, systemd-analyze) | config (CI) | n/a | itself :84-100, :133-147 | exact |
| `companion/test_login_throttle.py` (new, pytest) | test | unit + HTTP | `companion/test_companion_app.py` :1720-1786, :7938-7990, `Harness` :1220-1300 | role-match (harness -> pytest) |
| `companion/test_post_origin.py` (new, pytest) | test | HTTP integration | `companion/test_companion_app.py` `http_request(extra_headers=)` :1174-1208 + `Harness` | role-match |
| `companion/test_health_offbox.py` (new, pytest) or add to health tests | test | unit render | `companion/test_status_pages.py` `check()`/`_mkstate` :1292-1310 | role-match |
| `deploy/tests/conftest.py` (fake root + PATH stubs) | test fixture | n/a | none (no PATH-stub test in repo) | no analog |
| `deploy/tests/test_activate.py`, `test_caddyfile.py`, `test_units.py`, `test_ci_secrets.py`, `test_provision_ssh.py`, `test_backup.py`, `test_backup_gate.py`, `test_mac_pull.py` | test | subprocess / file parse | `companion/test_companion_app.py` `_env_example_documents_insecure_cookies_flag` :1680-1692 (repo-file text assertions) + `Harness` subprocess pattern | partial |
| `pyproject.toml` (testpaths/coverage source for `deploy/`) | config | n/a | itself `[tool.coverage.run]` | exact |
| `companion/test_browser_*` (Playwright cross-origin form) | test (browser) | HTTP | existing `companion/test_browser_ux.py` | role-match |
| `stub-server/byos_server.py` (Wave B: `--bind`, env secret) | controller | request-response | `companion/app.py` `build_parser` (after this phase's `--bind`) | exact (Wave B, after Phase 36) |

---

## Pattern Assignments

### `companion/auth.py` — keyed `LoginThrottle` + `client_ip()` (utility, request-response)

**Analog:** the class itself, `companion/auth.py:301-356`, and constants `:69-70`.

Constants to keep (`auth.py:69-70`):
```python
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_S = 300
```

Current class shape to preserve (lock, fresh-count-after-window contract, `seconds_remaining` int) — `auth.py:317-356`:
```python
    def __init__(self, limit=LOGIN_FAILURE_LIMIT, lockout_s=LOGIN_LOCKOUT_S):
        self._limit = limit
        self._lockout_s = lockout_s
        self._failures = 0
        self._locked_until = 0.0
        self._lock = threading.Lock()

    def record_failure(self):
        # A-32/D-15: once the previous lockout window has fully elapsed,
        # a new failure must start a fresh count ...
        with self._lock:
            if self._failures >= self._limit and time.time() >= self._locked_until:
                self._failures = 0
            self._failures += 1
            if self._failures >= self._limit:
                self._locked_until = time.time() + self._lockout_s

    def record_success(self): ...
    def locked_out(self): ...
    def seconds_remaining(self):
        with self._lock:
            remaining = self._locked_until - time.time()
        return int(remaining) if remaining > 0 else 0
```
Changes (RESEARCH §SEC-01): add `key` parameter to all four methods, `clock=time.time` injectable in `__init__`, `max_entries=4096`, `collections.OrderedDict[key] -> (failures, locked_until, last_seen)`; replace every `time.time()` with `self._clock()`. The class docstring (`:302-315`) says "Per-IP throttling was considered ... and deliberately deferred" — rewrite it (why-only, D-A3). Module docstring lists stdlib imports (`:5-6` "hashlib, hmac, http.cookies, os, time, secrets") — add `ipaddress`, `collections` there. `client_ip(peer, xff)` goes here as a pure function; use RESEARCH "Code Examples" verbatim plus IPv6 `/64` keying.

---

### `companion/app.py` (controller, request-response)

**Analog:** itself.

**Singleton** (`app.py:685-688`) — keep singleton, update comment:
```python
# Process-global, not per-session (06-RESEARCH.md Pitfall 8's own login
# analogue) — D-01/D-02 mean there are no distinct users for a per-session
# counter to key on.
LOGIN_THROTTLE = auth.LoginThrottle()
```

**Login handler to key** (`app.py:3053-3080`):
```python
    def _handle_login_post(self):
        form = self.read_form()
        next_route = _validated_next_route(form.get("next"))
        if LOGIN_THROTTLE.locked_out():
            remaining = LOGIN_THROTTLE.seconds_remaining()
            return self.send_html(429, self._render_login_page(
                lockout_seconds=remaining, next_route=next_route))
        submitted = form.get("password", "")
        if auth.password_ok(submitted):
            LOGIN_THROTTLE.record_success()
            token = auth.issue_session_token()
            return self.redirect(
                next_route or HOME_ROUTE,
                set_cookie=auth.session_set_cookie_header(token))
        LOGIN_THROTTLE.record_failure()
        return self.send_html(401, self._render_login_page(
            error=i18n.t("Incorrect password. Try again."), next_route=next_route))
```
Insert `key = auth.client_ip(self.client_address[0], self.headers.get("X-Forwarded-For"))` once at the top and pass `key` to each call. Also grep `seconds_remaining` at `app.py:~1850` (login page seed) — it must receive the same key.

**POST dispatcher hook** (`app.py:3453-3459`) — gate goes before `path == LOGIN_ROUTE`:
```python
    def do_POST(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            return self._handle_login_post()
```
`urlsplit` is already imported. Helper shape: RESEARCH "SEC-03 gate" code example; make it a `Handler` method or module function taking `self.headers`.

**403 body** — copy `_not_found_page` (`app.py:1712-1757`), which is pre-auth safe (resolves lang from cookie, computes `health_alert` only when `self._is_authenticated()`):
```python
        prefs.set_request_prefs(lang=self._lang_from_request())
        health_alert = None
        if self._is_authenticated():
            health_state = health_page.safe_health_state(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = health_state["severity"] if health_state else "ok"
        body = (
            layout.page_header(i18n.t(NOT_FOUND_TITLE), purpose=i18n.t(NOT_FOUND_PURPOSE_TEXT))
            + '<p class="text-body"><a href="%s">%s</a></p>'
            % (HOME_ROUTE, layout.escape_html(i18n.t("Back to Home")))
        )
        return layout.page_shell(
            title=i18n.t("Not Found"), active="", body=body,
            ui_theme=self._resolved_ui_theme(), health_alert=health_alert)
```
Respond with `self.send_html(403, ...)` — `send_html` (`:1256-1267`) already adds `Cache-Control: no-store` and the hardening headers. New `FORBIDDEN_*` string constants need FR entries (`test_i18n.py` Check 1/2 scan `app.py` with `ast`; every `i18n.t()` literal must be in the catalogue and every catalogue entry must be read).

**`--bind` flag (D-22)** — `build_parser` (`app.py:3627-3646`) and `main` (`:3649-3667`):
```python
def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--state-dir",
        default=poll_loop.DEFAULT_STATE_DIR,
        help="...",
    )
    ...
    Handler.args = args
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("companion: serving on port %d (state_dir=%s)" % (args.port, args.state_dir))
```
Add `parser.add_argument("--bind", default="0.0.0.0", help=...)` following the `--geofence` help style; use `(args.bind, args.port)`; include the bind address in the startup print. The module docstring (`app.py:17-22`, "This service binds all interfaces (0.0.0.0) ...") must be updated.

**Env var constant for the marker** — copy `SLEEP_ENV_VAR` (`app.py:146-153`) and the per-call read of `server/wake.py:env_sleep_s()` (`wake.py:64-94`):
```python
SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"
...
    raw = os.environ.get(SLEEP_ENV_VAR)   # read on every call, never cached at import
```
Put `OFFBOX_MARKER_ENV_VAR = "SKYPANE_OFFBOX_MARKER"` in `health_page.py` (the reader) or `companion/wake.py`-style helper; pages may not import `app.py`.

---

### `companion/pages/health_page.py` — off-box backup card (component, transform)

**Analog:** `_pipeline_section` (`health_page.py:2647-2720`), registry card in `render()` (`:4440-4480`), `staleness_status` (`:918-935`), `overall_severity` (`:2039-2092`), `compute_health_state` (`:2095-2211`).

**Status verdict** (`health_page.py:918-935`) — reuse, note None -> "warn":
```python
def staleness_status(age_seconds, warn_s, error_s):
    if age_seconds is None:
        return "warn"
    if age_seconds < 0:
        age_seconds = 0
    if age_seconds >= error_s:
        return "error"
    if age_seconds >= warn_s:
        return "warn"
    return "ok"
```
Threshold constants follow `STALE_PIPELINE_WARN_S = 180  # 3 minutes — ...` (`:113-115`). For D-23 (warning only), pass an `error_s` that is never reached, or map to `"warn"` explicitly.

**Age + timestamp** (`_pipeline_section` :2705-2720):
```python
    age = layout.age_seconds(pipeline_ts, now)
    state = staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)
    verdict = escape_html(
        i18n.t(PIPELINE_STATE_TEXT.get(state, PIPELINE_STATE_TEXT["warn"])))
    # D-09: concise_timestamp_html() already returns pre-escaped-safe
    # markup — wrapping it in escape_html() a second time would double-encode
```
`layout.age_seconds(ts, now_ts)` (`layout.py:1052`) needs ISO strings: convert the archive-name time `YYYYMMDDTHHMMSSZ` to ISO (`+00:00`) first. `layout.concise_timestamp_html(ts, now_ts, fallback=...)` (`layout.py:1559`) gives the ticking "HH:MM (N ago)" markup.

**Nested status card** (`render()` :4440-4480) — the pattern the new card copies:
```python
    registry_modifier = layout.card_status_class("page-section", coverage_status(registry_rows))
    registry_class = "page-section page-section--nested" + (
        (" " + registry_modifier) if registry_modifier else "")
    server_data_section_html = (
        layout.section_intro_html(
            SERVER_DATA_SECTION_ID, i18n.t(SERVER_DATA_SECTION_HEADING),
            i18n.t(SERVER_DATA_SECTION_DESCRIPTION))
        + '<div class="dashboard-grid">' + server_data_tiles_html + '</div>'
        + '<section class="%s"><h2 class="text-heading">%s</h2>%s</section>' % (
            registry_class, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)),
            _registry_section(registry_rows, now))
        + _stats_section_html(stats)
    )
```
Append the off-box card to this concatenation; return `""` when the env var is unset (same shape as `_stats_section_html` returning `""` when empty, `:4225-4237`). Use `layout.status_dot(state, label)` (`layout.py:3300`) for dot+label.

**Nav dot (D-23)** — widen `overall_severity` with a defaulted kwarg, exactly as 19-05 did for `coverage_state` (`:2039-2092`):
```python
def overall_severity(
    device_state, pipeline_state, battery_state, disagreement_warn,
    coverage_state="ok", source_fault=False,
):
    if source_fault:
        return "error"
    states = (device_state, pipeline_state, battery_state)
    if "error" in states:
        return "error"
    if "warn" in states or disagreement_warn or coverage_state == "warn":
        return "warn"
    return "ok"
```
Add `offbox_state="ok"` to the warn clause only. Update `collect_anomalies` in parallel (`:1973-2036`, `anomalies.append(i18n.t("..."))`), and compute/publish `offbox_state` / `offbox_html` in `compute_health_state` (`:2179-2211` dict) so `safe_health_state` feeds the nav dot (`app.py:1517`) and `render()` reuses it. Do not change the precedence of existing args (pinned by `test_status_pages.py:4968`).

---

### `companion/i18n_fr/health.py` (catalogue)

**Analog:** itself (`:106-112`, `:191-195`):
```python
    # --- Device / Pipeline / Corroboration tiles ------------------------
    "Device last checked in": "Dernière connexion de l’appareil",
    "Flight data last updated": "Dernière mise à jour des données de vol",
    ...
    "Server & data": "Serveur et données",
```
Rules from the module docstring (`:15-19`): sentence case, U+2019 apostrophe, U+00A0 before `: ; ? !`, U+00A0 between a number and its unit. Key = exact English literal passed to `i18n.t()`, including `%s`/`%d`. Anomaly sentences sit at `:89-96`. 403 page strings go to `companion/i18n_fr/common.py` (where "Not Found" lives).

---

### `deploy/Caddyfile` (config)

**Analog:** itself. Insert one line into each block after `reverse_proxy`:
```
203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:8642
    ...
config-203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:8643
```
Keep placeholder lines unchanged at column 0 (`^203-0-113-10\.nip\.io {` / `^config-203-0-113-10\.nip\.io {`): both `provision.sh:121-122` and the new render depend on those anchors.

---

### systemd units (config) — `skypane-{byos,companion,poll}.service`, new `skypane-backup.service/.timer`

**Analog:** `deploy/skypane-poll.service` (oneshot) and `deploy/skypane-companion.service` (long-running).

Existing `[Service]` + hardening block to extend (`skypane-companion.service:57-77`):
```ini
[Service]
Type=simple
User=skypane
Group=skypane
EnvironmentFile=/opt/skypane/skypane.env
WorkingDirectory=/opt/skypane
ExecStart=/opt/skypane/venv/bin/python3 /opt/skypane/companion/app.py \
    --port ${SKYPANE_COMPANION_PORT} \
    --state-dir ${SKYPANE_STATE_DIR} \
    --geofence /opt/skypane/config/runway3.json
Restart=always
RestartSec=5

# Hardening - cheap and unconditional for a single-purpose unprivileged
# service. ReadWritePaths is scoped to the state directory only; everything
# else the process might touch is read-only or private.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/skypane/state
```
Edits: code paths -> `/opt/skypane/current/...`, `--geofence /opt/skypane/current/adsb-test/runway3.json`, companion adds `--bind 127.0.0.1` (and the header comment `:3-8` about binding 0.0.0.0 is rewritten), append the SEC-06 directive table (RESEARCH §SEC-06) under the hardening comment. No `IPAddressDeny` on companion/poll (D-22).

New timer copies `skypane-poll.timer` layout (comment explaining cadence, `[Timer]`, `Unit=`, `[Install] WantedBy=timers.target`):
```ini
[Timer]
OnBootSec=30s
OnUnitActiveSec=30s
AccuracySec=1s
Unit=skypane-poll.service

[Install]
WantedBy=timers.target
```
-> `OnCalendar=*-*-* 03:15:00 UTC`, `Persistent=true`, `RandomizedDelaySec=10m`, `Unit=skypane-backup.service`.
New backup service copies `skypane-poll.service` (`Type=oneshot`, no `[Install]`, no `Restart`), adds `PrivateNetwork=true`, `RestrictAddressFamilies=AF_UNIX`, `ReadWritePaths=/opt/skypane/state /var/lib/skypane-backup/archives`. No `EnvironmentFile=` needed unless the job reads `SKYPANE_STATE_DIR`.

---

### `deploy/deploy.sh` (rewrite) and `deploy/activate.sh` (new)

**Analog:** `deploy/deploy.sh` for header/usage; `deploy/provision.sh` for root-side logic.

Header + usage + strict mode (`deploy.sh:1-34`):
```bash
#!/usr/bin/env bash
# SkyPane — repeatable code-push to an already-provisioned VPS
# ...
# Usage:
#   deploy/deploy.sh <ssh-target>
set -euo pipefail

APP_ROOT="/opt/skypane"
SSH_TARGET="${1:?usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh root@203.0.113.10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"

echo "==> Syncing server/ to ${SSH_TARGET}:${APP_ROOT}/server/"
```
Keep `echo "==> step"` progress lines and `"${VAR}"` quoting. Change usage example to `ubuntu@` (SEC-08). Drop local `sha256sum` (`:64`) — hash compare moves into `activate.sh` against `venv/.requirements.sha256`.

Root guard (`provision.sh:36-39`) — copy into `activate.sh`:
```bash
if [ "$(id -u)" -ne 0 ]; then
    echo "provision.sh must run as root (sudo ./provision.sh [public-host [companion-host]])" >&2
    exit 1
fi
```
Hostname validation (`provision.sh:41-48`) — reuse for values parsed from `skypane.env` (never `source` it):
```bash
for host in "${PUBLIC_HOST}" "${COMPANION_HOST}"; do
    if [ -n "${host}" ] && ! [[ "${host}" =~ ^[A-Za-z0-9.-]+$ ]]; then
        echo "provision.sh: invalid hostname '${host}' (letters, digits, dots and dashes only)" >&2
        exit 1
    fi
done
```
Anchored Caddyfile render (`provision.sh:118-123`) — extract into one shared function/script used by both provision and activate:
```bash
    sed -e "s/^config-203-0-113-10\.nip\.io {/${COMPANION_HOST} {/" \
        -e "s/^203-0-113-10\.nip\.io {/${PUBLIC_HOST} {/" \
        "${HERE}/Caddyfile" > /etc/caddy/Caddyfile
```
Unit install + reload (`provision.sh:109-113, 133-142`):
```bash
install -m 644 "${HERE}/skypane-byos.service" /etc/systemd/system/skypane-byos.service
...
systemctl daemon-reload
systemctl enable skypane-byos.service
```
Restart + journal tail (`deploy.sh:76-85`) is the model for activate's restart and failure-path `journalctl -u <unit> -n 50 --no-pager`. Every system path in `activate.sh` must be an overridable variable (`SKYPANE_ROOT`, `SYSTEMD_UNIT_DIR`, `CADDYFILE`, `ENV_FILE`, `BACKUP_GATE_DIR`) for the fake-root tests.

---

### `deploy/provision.sh` (modify)

**Analog:** itself. Keep idempotent style (`id -u X >/dev/null 2>&1 || useradd ...`, `:55-57`):
```bash
id -u "${APP_USER}" >/dev/null 2>&1 || \
    useradd --system --home-dir "${APP_ROOT}" --create-home \
        --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p "${APP_ROOT}/server" "${APP_ROOT}/stub-server" "${APP_ROOT}/companion" "${APP_ROOT}/config" "${STATE_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"
```
Note `chown -R ... ${APP_ROOT}` at `:59` would re-own a root-owned `releases/` and a `root:root` `skypane.env` on every re-run — must be narrowed. Replace SSH block `:159-164` (which ends in `|| true`) with the `sshd_config.d/00-skypane.conf` + `sshd -t` + `systemctl try-reload-or-restart ssh.service` sequence. Replace final "Next:" echo `:166-170` wording to say `chown root:root`. Add `skypane-backup` user/dirs and `ufw` stays as is (`:144-157`).

---

### `deploy/skypane.env.example` (modify)

**Analog:** the `SKYPANE_CADDY_ACCESS_LOG` entry (last block): a `#` paragraph explaining who reads the variable and why, then `KEY=value`. Add `SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull` the same way. Fix the header claim (`:8-9`) that systemd reads it only for poll and byos. Existing doc-test precedent: `test_companion_app.py:1680-1692` asserts an env var name is present in this file — mirror it for `SKYPANE_OFFBOX_MARKER`.

---

### `deploy/backup/skypane_backup.py` and `deploy/backup/backup_gate.py` (new, stdlib)

**Analog:** `server/poll_loop.py` CLI (`:1943-1987`) and `stub-server/byos_server.py` atomic write (`:152-156`).

CLI shape (`poll_loop.py:1943-1987`):
```python
def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Directory holding panel.bin / poll_state.json (default: server/state/).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        run_once(state_dir=args.state_dir, geofence=args.geofence, caddy_log=args.caddy_log)
    except Exception as exc:
        # A failed cycle must leave the previously served panel intact and
        # never crash-loop the systemd timer silently - log to stdout
        # (journald captures this) and exit non-zero.
        print("poll_loop: cycle failed: %s: %s" % (type(exc).__name__, exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
`main(argv=None)` returning an int is what makes in-process pytest calls easy. The gate takes no argv; read `os.environ["SSH_ORIGINAL_COMMAND"]` and `shlex.split` it, with dirs overridable by env for tests.

Atomic write (`byos_server.py:152-156`):
```python
def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))
```
Use for `pulled/last-pull` and the `.sha256` file (add `fsync` for the archive, per RESEARCH). If Phase 36 INT-02 has landed a shared atomic-write helper, do NOT import it from `deploy/` (the gate runs as `/usr/bin/python3` outside the venv/release); keep the gate self-contained. SQLite snapshot: RESEARCH "Code Examples" `snapshot_db`. Formatting style: `%` string formatting (ruff selects only E4/E7/E9/F, `pyproject.toml`).

---

### `deploy/backup/mac/*` (new)

**Analog:** `deploy/deploy.sh` header comment/usage/`echo "==>"` convention only. Must be `#!/bin/sh` POSIX (no `[[ ]]`, no arrays, no `${BASH_SOURCE}`), linted with `shellcheck --shell=sh`. The plist template has no analog — use RESEARCH §SEC-04 "launchd plist template" (Label `com.skypane.backup-pull`, `StartCalendarInterval` + `RunAtLoad`, absolute log paths substituted by the installer).

---

### `.github/workflows/ci.yml` (modify)

**Analog:** itself. Step style in `test` job (`ci.yml:93-100`): a `- name:` that states the purpose, a one-line `run:`:
```yaml
      - name: Lint (blocking — rule set lives in pyproject.toml)
        run: server/.venv/bin/ruff check .

      - name: Run full test suite with coverage threshold
        run: ./scripts/run-all-tests.sh
```
Add `Shellcheck deploy scripts` and `systemd-analyze security (offline) on unit files` steps the same way, in `test` (not touching `concurrency`, D-13).

Deploy job lines to change (`ci.yml:133-147`), keeping the explanatory step comments:
```yaml
      - name: Trust the production host key
        run: |
          mkdir -p ~/.ssh
          chmod 700 ~/.ssh
          echo "${{ secrets.DEPLOY_HOST_KEY }}" >> ~/.ssh/known_hosts
          chmod 644 ~/.ssh/known_hosts

      - name: Deploy
        run: ./deploy/deploy.sh "${{ secrets.DEPLOY_SSH_TARGET }}"
```
Target shape: RESEARCH "ci.yml deploy job (D-20)" snippet (`env:` + `"$DEPLOY_HOST_KEY"` / `"$DEPLOY_SSH_TARGET"`). The `webfactory/ssh-agent` `with:` input (`:128-131`) stays. The deploy step comment ("owns every bit of the rsync/pip/systemd-restart logic") needs rewording. Phase 32 also edits this file — re-read before editing.

---

### Companion tests (pytest) — `test_login_throttle.py`, `test_post_origin.py`, off-box health tests

**Analog:** `companion/test_companion_app.py` (stdlib harness today; Phase 32/33 turns these into pytest fixtures — use those fixtures when present, D-02).

Subprocess server (`Harness`, `test_companion_app.py:1220-1300`) — the pattern a local fixture should copy if Phase 33 has no companion-server fixture:
```python
    def start(self):
        env = dict(os.environ)
        env[auth.PASSWORD_ENV_VAR] = TEST_PASSWORD
        cmd = [
            sys.executable, APP_PATH,
            "--port", str(self.port),
            "--state-dir", self.tmpdir,
        ] + self.extra_args
        ...
        while time.time() < deadline:
            ...
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                return
```
`extra_args` is how a test passes `--bind 127.0.0.1`; `env` is how a test sets `SKYPANE_OFFBOX_MARKER`.

HTTP client with headers (`http_request`, `:1174-1208`) — `extra_headers` sends `Origin` / `Sec-Fetch-Site` / `X-Forwarded-For`; `_NoRedirectHandler` keeps 303 visible:
```python
def http_request(
        url, method="GET", data=None, cookie=None, timeout=10,
        content_type=None, extra_headers=None):
```
Lockout-isolation rule (`:7938-7946`): each lockout test gets its own server process, because `LOGIN_THROTTLE` is process-global.

Unit throttle checks to port (`:1720-1786`): the three `_login_throttle_*` functions; replace `throttle._locked_until = time.time() - 1` time travel with the injected clock.

Health render tests: `companion/test_status_pages.py` builds a state dir (`_mkstate`) and calls `health_page` functions directly; extend with `monkeypatch.setenv("SKYPANE_OFFBOX_MARKER", ...)` cases (unset -> absent, missing file -> warn, stale -> warn, fresh -> ok, FR via `i18n.t_lang`).

---

## Shared Patterns

### Environment reads (per call, never at import)
**Source:** `server/wake.py:64-94`, `companion/auth.py:160-171`
**Apply to:** off-box marker path, byos secret (Wave B)
```python
    raw = os.environ.get(SLEEP_ENV_VAR)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
```

### Response helpers carry hardening headers
**Source:** `companion/app.py:1250-1267` (`_send_hardening_headers`, `send_html`)
**Apply to:** the 403 CSRF rejection — always go through `send_html`, never a bare `send_response`.

### i18n
**Source:** `companion/i18n.py:21-30`, `companion/i18n_fr/health.py` docstring
**Apply to:** every new user-visible string (health card, 403 page). Wrap `i18n.t()` at the literal call site; add an FR key; `test_i18n.py` fails on missing or unused keys.

### Fail-closed health computation
**Source:** `health_page.safe_health_state` (`:2214-2238`, broad `except` -> `None`)
**Apply to:** the marker read — a malformed marker must yield "never"/warn, never raise into every page render.

### Shell script conventions
**Source:** `deploy/provision.sh`, `deploy/deploy.sh`
**Apply to:** `activate.sh`, `install-backup-key.sh`, rewritten `deploy.sh`, provision edits
- `#!/usr/bin/env bash` + `set -euo pipefail` (Mac pull script: `#!/bin/sh`, `set -eu`)
- header comment: purpose, where it runs (laptop vs VPS, root), `Usage:` block, idempotency note
- `echo "==> Step"` progress, `echo "    detail"` sub-lines, errors `>&2` prefixed with the script name
- uppercase `"${VAR}"`-quoted variables, `HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`
- never `|| true` on a step whose failure matters (SEC-08)

### Comment discipline (audit D-A3)
Existing files carry long plan-history comments (e.g. "06-11-PLAN.md", "quick task 260902-gjj"). New code: English, explains why, no plan/ticket IDs. Rewrite comments that the change makes false (companion/byos unit headers, `app.py` docstring :17-22, `LoginThrottle` docstring, README "fully reproducible" paragraph, `ci.yml` deploy step comment); do not purge unrelated comments (Phase 35).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `deploy/tests/conftest.py` (fake root, PATH stubs for `systemctl`/`curl`/`caddy`/`runuser`/`journalctl`/`sshd`/`ssh`) | test fixture | n/a | No existing test stubs executables on PATH; follow RESEARCH "Pattern: fake-root shell testing" |
| `deploy/backup/mac/skypane-backup-pull.plist.template` | config (launchd) | n/a | No macOS artefacts in repo; RESEARCH §SEC-04 Mac side |
| `deploy/tests/test_units.py` (`configparser` over unit files) | test | file parse | Nearest is the env-example text assertion (`test_companion_app.py:1680-1692`); use `configparser.ConfigParser(strict=False, interpolation=None)` |
| `/etc/ssh/sshd_config.d/00-skypane.conf` content | config | n/a | Written by provision.sh from a heredoc-free `printf`/`install`; content in RESEARCH §SEC-08 |

## Metadata

**Analog search scope:** `companion/` (app, auth, layout, i18n, i18n_fr, pages/health_page, tests), `deploy/`, `.github/workflows/`, `server/poll_loop.py`, `server/wake.py`, `stub-server/byos_server.py`, `pyproject.toml`, `.claude/skills/sketch-findings-skypane/SKILL.md` (index only)
**Files scanned:** 24
**Pattern extraction date:** 2026-09-23
