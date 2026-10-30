# Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access - Pattern Map

**Mapped:** 2026-10-30
**Files analyzed:** 27 (13 new source/test-support, 14 modified)
**Analogs found:** 25 / 27

Line numbers are from the working tree on 2026-10-30. Excerpts below were read directly.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `companion/routes.py` (modify) | route table | request-response | itself (`Route` namedtuple, lines 28, 201-223) | exact |
| `companion/access.py` (new) | utility (pure gate) | request-response | `companion/routes.py` `match()` (pure, table-driven) + `companion/auth.py` `post_origin_ok` (pure predicate) | role-match |
| `companion/oidc.py` (new) | utility/service (pure OIDC + bounded attempt table) | request-response | `companion/auth.py` `LoginThrottle` (bounded in-memory table) + `password_ok` (constant-time) | role-match |
| `companion/sign_in.py` (new) | Handler mixin | request-response | `companion/post_actions.py` `SettingsActionsMixin` (line 204) | exact |
| `companion/auth.py` (modify) | utility | request-response | itself (cookie helpers 174-222 stay; token code 134-171 deleted) | exact |
| `companion/app.py` (modify: `_dispatch`, `_is_authenticated`, `_handle_login_*`, `_handle_logout_post`, `main`) | controller | request-response | itself (lines 547-570, 888-909, 938-990) | exact |
| `companion/login_page.py` (modify) | component (server markup) | request-response | itself (`login_body`, 109-194) | exact |
| Account page markup (new, in `companion/pages/account_page.py` or `login_page.py`) | component | request-response | `companion/pages/health_page.py`-style `render(ctx)` pages via `h._render_tab` | role-match |
| `companion/i18n_fr/*.py` (modify) | config (catalogue) | transform | `i18n.msg(key, english)` use in `login_page.py` lines 27-79 | exact |
| `server/fleet_db.py` (modify: migration v2, race fix, `get_device_owner`) | model/migration | CRUD | itself (`_migrate_v1` 82-117, `migrate_schema` 153-172) | exact |
| `server/fleet_sessions.py` (new) | service (SQLite) | CRUD | `server/fleet_db.py` user CRUD (282-336) + `transaction()` (224-232) | exact |
| `server/fleet_migrate.py` (modify) | service | batch | itself (`plan_migration`, `migrate`; not read in full, see research gotcha 2) | exact |
| `stub-server/fleet_cli.py` (modify: `unlink-identity`, disable drops sessions) | utility (CLI) | CRUD | itself (`cmd_users_*`, 74-107) | exact |
| `test-support/fake_auth0.py` (new) | test utility (fake IdP) | request-response | `test-support/companion_app_server.py` `InProcessAppServer` (301-346) | role-match |
| `test-support/companion_app_server.py` (modify: Auth0 login helpers) | test utility | request-response | `login()` / `cookie_value()` (95-120) | exact |
| `test-support/test_fake_auth0.py` (new) | test | request-response | `test-support/test_test_support.py` | role-match |
| `companion/test_oidc.py` (new) | test | transform | `companion/test_companion_app_01.py` Section 1 (pure auth unit tests) | role-match |
| `companion/test_auth0_login.py`, `test_auth0_cookies.py`, `test_legacy_admin.py`, `test_sessions_http.py`, `test_account_page.py` (new) | test | request-response | `companion/test_post_origin.py` (module-scoped `module_app_server_factory`, raw `http_request`) | role-match |
| `companion/test_access_matrix.py` (new) | test | request-response | `companion/test_route_table.py` (60-145) | exact |
| `companion/test_route_table.py` (modify) | test | request-response | itself | exact |
| `companion/test_browser_auth0.py` (new) | test (browser) | request-response | existing pytest-playwright tests using `companion/conftest.py` `new_context` | role-match |
| `server/test_fleet_sessions.py` (new) / `server/test_fleet_db.py` (extend) | test | CRUD | `server/test_fleet_db.py` | exact |
| `companion/test_companion_app_01.py` Section 1 (rewrite) | test | transform | itself | exact |
| `companion/testdata/render_baseline.json` (regenerate) | config/snapshot | transform | `test-support/companion_render_snapshot.py` CLI | exact |
| `deploy/Caddyfile`, `deploy/tests/test_caddyfile.py` (modify) | config + test | transform | itself (block-depth parser) | exact |
| `deploy/skypane.env.example`, `deploy/README.md` (modify) | config/docs | n/a | existing `SKYPANE_COMPANION_*` entries | exact |
| `pyproject.toml` `[tool.mypy] files` (modify) | config | n/a | existing module list | exact |
| `stub-server/byos_server.py` (NOT modified; proof tests only) | controller | request-response | `stub-server/test_phase47_freeze.py`, `test_fleet_auth.py` | exact |

## Pattern Assignments

### `companion/routes.py` (route table, request-response)

**Analog:** itself. Replace the 4th field `auth_required` with an `access` field validated at construction.

**Current shape to replace** (lines 25-28):
```python
Exact = collections.namedtuple("Exact", "path")
PrefixSuffix = collections.namedtuple("PrefixSuffix", "prefix suffix")
RouteMatch = collections.namedtuple("RouteMatch", "path query captured")
Route = collections.namedtuple("Route", "method matcher handler auth_required")
```
Keep `Exact`, `PrefixSuffix`, `RouteMatch` untouched. Replace `Route` with a subclass whose `__new__` raises `TypeError` unless `access` is an `Access` (see RESEARCH "Access Annotation", lines 152-167). Every `True`/`False` literal at the end of the ~45 `Route(...)` calls (lines 75, 85, 90-138, 146-198) becomes `PUBLIC` / `SIGNED_IN` / `ADMIN_ONLY`.

**Classification when converting:**
- `PUBLIC`: GET/POST `/login` (85, 146), `_static_get_routes()` (75), new GET `/login/auth0`, new GET `/callback`.
- `SIGNED_IN`: `/ui-theme` (164), `/ui-lang` (165), `/logout` (166), new GET `/account`.
- `ADMIN_ONLY`: everything else (D-11).

**Static route builder pattern to keep** (lines 68-77):
```python
def _static_get_routes():
    return tuple(
        Route("GET", Exact(route), lambda h, m: h._serve_static_route(m.path), False)
        for route in static_files.STATIC_ROUTES
    )
```
Change only the trailing `False` to `PUBLIC`.

**Handler lambda convention** (lines 85, 166): `lambda h, m: h._handle_xxx()`; `m.captured` for prefix routes. New routes follow it: `Route("GET", Exact("/callback"), lambda h, m: h._handle_callback_get(), PUBLIC)`.

**Literal-duplication convention** (lines 30-43): constants that live in `app.py` are repeated as literals here because `routes.py` never imports `companion.app`. New `ACCOUNT_ROUTE`, `CALLBACK_ROUTE`, `LOGIN_AUTH0_ROUTE` follow the same rule.

**`match()` must keep reading module-global `ROUTES` at call time** (lines 201-223); the matrix HTTP layer monkeypatches `routes.ROUTES`.

---

### `companion/access.py` (new, pure gate)

**Analogs:** `companion/routes.py` `match()` (pure, table-driven, returns a tuple or None) for shape; `companion/auth.py` `password_ok` (lines 123-131) for the "never raises on hostile input" style.

**Hostile-input style to copy** (`auth.py` 123-131):
```python
def password_ok(submitted):
    """Constant-time check ... A non-string submission degrades to
    "wrong password", never a 500.
    """
    if not isinstance(submitted, str):
        submitted = ""
    return hmac.compare_digest(submitted.encode(), configured_password())
```

**Core pattern:** the `decide(principal, access, captured, owner_lookup)` body in RESEARCH lines 175-188 (ALLOW / LOGIN / NOT_FOUND). `Principal = namedtuple("Principal", "kind user_id email role")`. Validate captured device ids with `^d_[0-9a-f]{8}$` before calling `owner_lookup`. No I/O inside; the owner lookup is injected (`fleet_db.get_device_owner` in production).

No sqlite3 import here (same stdlib-only rule as `auth.py`).

---

### `companion/oidc.py` (new, pure OIDC + `AttemptTable`)

**Analog 1 (bounded in-memory table):** `companion/auth.py` `LoginThrottle` (lines ~264-352). Copy its structure: a lock, a bounded dict, injected clock, oldest-evicted. Read lines 249-352 before writing `AttemptTable` (max ~4096 entries, 10 min TTL, `pop` on first use).

**Analog 2 (constant-time):** `hmac.compare_digest` as in `password_ok`, for `state` and `nonce`.

**Code to copy from RESEARCH (these are the planner's reference, no codebase analog exists):** `new_pkce()` and `authorize_url()` (RESEARCH 435-451), `exchange_code(cfg, code, verifier, post)` with the injected `post` callable (453-467). Claim-check list at RESEARCH line 259. Use `requests.Session()` with `trust_env=False`, `allow_redirects=False`, `timeout=(3.05, 10)`; do NOT use `server.http_fetch.pinned_request` (https-only, refuses loopback, `http_fetch.py:320-346`).

**Error style:** raise one `SignInError(reason_code)` carrying a reason code only, never a body, code, token or secret (generic 400 page for the user).

---

### `companion/sign_in.py` (new, Handler mixin)

**Analog:** `companion/post_actions.py` `SettingsActionsMixin` (class at line 204). Docstring contract to copy:

```python
class SettingsActionsMixin:
    """... `Handler` inherits this ahead of `BaseHTTPRequestHandler`
    (`Handler(SettingsActionsMixin, BaseHTTPRequestHandler)`), so every method below runs with the full
    `self` a request handler provides (`self.args`, `self.read_form()`,
    `self.redirect()`, `self.send_html()`, `self.page_context()`, ...).
```
Imports pattern (post_actions.py lines 15-24, 58-65): stdlib first, then `from companion import layout`, then `from server import ...`. Module may never import `companion.app` (cycle).

Methods: `_handle_login_auth0_get`, `_handle_callback_get`, `_handle_logout_post`, `_handle_account_get`. Each ends in `self.send_html(...)` / `self.redirect(..., set_cookie=...)`. Add the mixin to `Handler`'s bases in `app.py`.

**Landing/logout interstitial:** `landing_page(target)` in RESEARCH 469-476 (200, meta refresh, `no-referrer`, no inline script because CSP is `script-src 'self'`). Do not 303 to a foreign origin after a POST (`form-action 'self'`).

---

### `companion/auth.py` (modify)

**Keep (analog is itself):** `configured_password`, `password_ok` (109-131), `secure_cookie_flag` (174-182), `parse_cookies` (210-222), `client_ip`, `LoginThrottle`, `login_throttle_key`, `post_origin_ok`.

**Delete:** `_PROCESS_SALT`, `_signing_key`, `_REVOKED`, `revoke`, `is_revoked` (lines 34-99), `issue_session_token`, `verify_session_token` (134-171).

**Cookie header shape to keep, changing only the lifetime** (lines 185-207):
```python
return (
    "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
    % (SESSION_COOKIE_NAME, token, secure_cookie_flag(), SESSION_TTL_S))
```
`SESSION_TTL_S` becomes 30 days (2592000). Add a sibling `oidc_attempt_set_cookie_header(attempt_id)` with `SameSite=Lax; Path=/callback; Max-Age=600` built the same way. Add pure `new_session_token()` (`secrets.token_urlsafe(32)`) and `hash_session_token()` (`sha256` hex). `auth.py` must not import sqlite3 or `server/`.

---

### `companion/app.py` (modify)

**`_is_authenticated` to replace with a per-request `_principal()`** (lines 547-553):
```python
def _is_authenticated(self):
    cookies = auth.parse_cookies(self.headers.get("Cookie"))
    token = cookies.get(auth.SESSION_COOKIE_NAME)
    return bool(token) and auth.verify_session_token(token) and not auth.is_revoked(token)
```
Same cookie-read first two lines; then hash and look up via `fleet_sessions.lookup_session`. Cache on `self`, reset at the top of `_dispatch`. Resolve lazily and only for non-`ANONYMOUS` routes so static assets never open `fleet.db`.

**`require_session` anonymous redirect behaviour to keep byte-for-byte** (lines 555-570), since the committed baseline records the `?next=` Locations. Move it into the `LOGIN` outcome of `decide`.

**`_dispatch` to rewrite** (lines 938-954); the gate line to replace is 952-953:
```python
if method == "POST" and not auth.post_origin_ok(self.headers):
    return self.send_html(403, self._forbidden_page())
parsed = urlsplit(self.path)
result = routes.match(method, parsed.path, parsed.query)
if result is None:
    return self.send_html(404, self._not_found_page())
route, route_match = result
if route.auth_required and not self.require_session():
    return None
return route.handler(self, route_match)
```
Origin gate stays first. New order: origin gate, match, `decide`, handler. `NOT_FOUND` outcome reuses `self.send_html(404, self._not_found_page())` so the body equals the unknown-path 404.

**Per-request DB scope pattern** (lines 923-932, `do_GET`): `with history_db.connection_scope(self.args.state_dir): return self._dispatch("GET")`. Mirror this for the `fleet.db` connection (open lazily, close at request end). On `sqlite3.Error`/`FleetDbError` while resolving a principal answer 503, never allow and never redirect to `/login`.

**Login POST to keep and adapt** (lines 966-990): read form, validated `next`, throttle lockout 429, `password_ok`, record success/failure. Changes: refuse with 403 first when the legacy flag is off (no throttle touch, no `password_ok`); on success create a `legacy-admin` session row instead of `issue_session_token()`; `print` an audit line (IP bucket only, never the password).

**Logout** (lines 900-909): replace `auth.revoke(token)` with `fleet_sessions.delete_session`, clear cookie first, then interstitial to Auth0 (or 303 `/login` for legacy-admin / Auth0 unconfigured).

**`_not_found_page()` / `_forbidden_page()` (643-675):** compute the Health dot only for admin/legacy-admin principals (RESEARCH pitfall 5).

**`_handle_login_get`** (888-898): redirect by role (`user` goes to `/account`).

**`main()`** (~1304-1310): fail closed; validate `SKYPANE_LEGACY_PASSWORD_LOGIN` (unset or `1` enabled, `0` disabled, anything else exit 1), Auth0 variables all-or-nothing, at least one method usable, name variables only.

**Does `_validated_next_route`** (336-343, exact NAV_TABS membership) stay: reuse unchanged for the pre-login `next`.

---

### `companion/login_page.py` (modify)

**Analog:** itself. Pure markup, takes already-computed state, never reads the request, never imports `companion.app`.

**i18n pattern for every new string** (lines 27-29, 76-78):
```python
LOGIN_EXPLANATION_TEXT = i18n.msg(
    "common.sign_in_to_manage_this_device_s_settings",
    "Sign in to manage this device's settings.")
_SIGN_IN_TEXT = i18n.msg("common.sign_in", "Sign in")
```
Translate at the render site with `i18n.t(...)` and escape with `layout.escape_html(...)` (see lines 121, 182-187). Add the French in `companion/i18n_fr/` (new keys in `common.py` or a new `account.py` registered in `registry.py`).

**Form markup pattern** (lines 168-188): `<form method="post" action="%s" class="login-form"%s>` with the hidden `next` field and `login_reveal_toggle_html()`. For the new layout (UI-SPEC surface 1) the Auth0 entry is a plain GET link/button to `/login/auth0` (must be a navigation, not a form POST), and the existing password form becomes the secondary option rendered only when the legacy flag is on. Keep `aria-describedby` / `aria-invalid` / lockout handling intact.

**Error page pattern for the "not invited" refusal and generic sign-in errors** (`not_found_page`/`forbidden_page`, lines 197-229): `layout.page_header(title, purpose=...)` plus a link paragraph, wrapped in `layout.page_shell(title=..., active="", body=body, ui_theme=ui_theme, health_alert=health_alert)`; pass `health_alert=None` for these. 403 status, no session cookie.

Account page: a `page_shell` with `active="account"`; the language/theme controls reuse the `_lang_form_html` / `_theme_form_html` partials (UI-SPEC surface 4), empty state via `ui_components.empty_state`. The sidebar for a `user` must be built from the route table so a link exists iff the route is reachable (UI-SPEC surface 6).

---

### `server/fleet_db.py` (modify: migration v2, race fix, owner lookup)

**Migration pattern** (lines 82-120): add `_migrate_v2(conn)` that executes the `CREATE TABLE sessions` and two `CREATE INDEX` statements (RESEARCH 215-226), then `MIGRATIONS = (_migrate_v1, _migrate_v2)`. `SCHEMA_VERSION = len(MIGRATIONS)` follows automatically. Expand-only.

**Race fix** in `migrate_schema` (lines 153-172): the version is read at line 158 before `BEGIN IMMEDIATE` at 164. Inside the loop, after `BEGIN IMMEDIATE`, re-read `schema_version(conn)` and, when `>= index + 1`, `ROLLBACK`/`COMMIT` and `continue` without running the step.
```python
for index in range(current, len(migrations)):
    conn.execute("BEGIN IMMEDIATE")
    try:
        migrations[index](conn)
        conn.execute("PRAGMA user_version = %d" % (index + 1))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
```

**Typed accessor style for `get_device_owner`** (lines 329-336, `get_user_role`): select only the needed column, return `None` for unknown:
```python
def get_user_role(conn: sqlite3.Connection, user_id: int) -> str | None:
    row = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    return None if row is None else str(row["role"])
```
`get_device_owner` selects only `owner_user_id` (never `secret_sha256` or `token`).

`connect()` (175-196) creates the file mode 0600 and migrates; the companion calls `fleet_db.connect(state_dir)`. `transaction()` (224-232) is the write wrapper.

---

### `server/fleet_sessions.py` (new, typed SQL for sessions and linking)

**Analog:** `server/fleet_db.py` user CRUD (lines 282-336) for style; annotated signatures (module is added to `[tool.mypy] files`), `sqlite3.Row` results, `fleet_db.transaction(conn)` for writes, `fleet_db.utc_now_iso()` replaced by an injected epoch-seconds `now` for the session clock.

Functions: `create_session`, `lookup_session` (JOIN `users`; returns role/disabled; applies the 30-day absolute and 7-day idle checks; throttled `last_seen_at` write), `delete_session`, `delete_sessions_for_user`, `prune_expired`, `link_identity` (one `BEGIN IMMEDIATE`, `UPDATE users SET iss=?, sub=? WHERE id=? AND sub IS NULL`, require `rowcount == 1`), `get_user_by_identity`.

Email handling: reuse `fleet_db.normalize_email` (282-287) and the `users` columns `iss`/`sub` (UNIQUE) already in v1. No insert path for users exists in this module (D-01). Function size gate: max 80 lines (`server/` is gated).

---

### `stub-server/fleet_cli.py` (modify)

**Analog:** itself. Command shape (lines 74-107):
```python
def _set_disabled(args, disabled):
    conn = _open(args)
    with fleet_db.transaction(conn):
        found = fleet_db.set_user_disabled(conn, args.email, disabled)
    if not found:
        return _fail("no such user: %s" % args.email, 1)
    print("%s %s" % ("disabled" if disabled else "enabled", args.email))
    return 0
```
Add `cmd_users_unlink_identity` the same way (clears `iss`, `sub`) and register it beside the `disable`/`enable` loop at lines 278-281 (`verbs.add_parser(...)`, `--email`). When disabling, also call `fleet_sessions.delete_sessions_for_user` inside the same transaction. Update the module usage docstring (lines 18-20).

---

### `test-support/fake_auth0.py` (new)

**Analog:** `test-support/companion_app_server.py` `InProcessAppServer` (lines 301-346): stdlib `ThreadingHTTPServer` on `127.0.0.1` with a free port, run in a daemon thread, `base_url()`, `stop()` doing `shutdown()` then `server_close()`.
```python
self.port = pick_free_port()
self.server = ThreadingHTTPServer(("127.0.0.1", self.port), app_module.Handler)
self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
self.thread.start()
```
No pytest import in the module. Endpoints `/authorize`, `/oauth/token`, `/v2/logout`, an ordered `calls` log and the failure-knob list are specified in RESEARCH 301-309. The id token is `header.payload.junk-signature` so production can never depend on the signature.

---

### `test-support/companion_app_server.py` (modify)

**Analog:** `login()` and `cookie_value()` (lines 95-120):
```python
def cookie_value(headers):
    raw = headers.get("Set-Cookie")
    if not raw:
        return None
    return raw.split(";", 1)[0]

def login(server, password=TEST_PASSWORD):
    status, headers, _ = http_request(
        server.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": password}).encode())
    if status != 303:
        raise AssertionError(...)
```
Add `login_via_auth0(server, fake, ...)` beside it, a non-following client that performs the two hops by hand (GET `/login/auth0`, GET the fake's authorize URL, GET `/callback?...` with the `sp_oidc` cookie) and returns the session cookie. The callback now answers 200 with the cookie, not 303. Keep `login()` working unchanged (legacy flag default on) so the ~80 modules stay green. `InProcessAppServer.__init__`/`stop` (lines 323-324, 343-346) set and restore `PASSWORD_ENV_VAR`; extend the same set/restore for the Auth0 and legacy-flag variables.

---

### `companion/test_access_matrix.py` (new) and `companion/test_route_table.py` (modify)

**Analog:** `companion/test_route_table.py` lines 54-126. Patterns to copy: the fixed expectation set built independently of the table (`_PUBLIC_EXEMPTIONS`, lines 60-64), parametrization over `routes.ROUTES` with generated ids (66-70), a module-scoped shared server (87-94, `module_app_server_factory`), and per-case assertions on real HTTP status and `Location` (97-126). The `_SAMPLE_MIDDLE[matcher]` / `baseline[key]` KeyError behaviour is a deliberate forcing function; keep it.

Updates in `test_route_table.py`: line 78 `not r.auth_required` becomes `r.access.min_role == routes.ANONYMOUS`; the public-set expectation (79-83) gains GET `/callback` and GET `/login/auth0`; add a test that `routes.Route(..., True)` and a missing access raise `TypeError`.

Matrix layers (RESEARCH 198-205): pure `decide()` over the hand-written expectation table keyed by `(method, matcher)` with a completeness test against `routes.ROUTES`; HTTP layer on `InProcessAppServer` with every handler monkeypatched to a recording stub via `routes.ROUTES`; probe family `Route("GET", PrefixSuffix("/d/", "/_probe"), stub, Access(USER, "device"))` registered only in the test, with two users and two devices seeded via `fleet_db.add_user` / `add_device`.

---

### `companion/test_post_origin.py`-style integration tests (new files listed in the classification)

**Analog:** `companion/test_post_origin.py` (module-scoped `origin_server` fixture; raw `http_request`). Use `companion_app_server.http_request`, `cookie_value`, `login`, and the new `fake_auth0` helper. Assert on real `Set-Cookie` attributes for the cookie tests, never on source text (behaviour-over-source rule enforced by `companion/test_suite_guards.py`).

---

### `server/test_fleet_sessions.py` (new) / `server/test_fleet_db.py` (extend)

**Analog:** `server/test_fleet_db.py` (not read in full; follow its fixtures). Use `fleet_db.connect_memory()` (line 215) or a tmp `state_dir` with `fleet_db.connect`. Add: v1 to v2 in place upgrade, idempotence, two-connection upgrade race, too-new refusal still raised (`FleetDbTooNew`), and `stub-server/test_fleet_auth.py:~170` style `user_version = SCHEMA_VERSION + 1` too-new fixture remains valid.

---

### `deploy/Caddyfile` + `deploy/tests/test_caddyfile.py`, `deploy/skypane.env.example`, `deploy/README.md`

**Analog:** themselves. Caddy filter block is given in RESEARCH 273-283; `test_caddyfile.py` parses site blocks by brace depth (~lines 29-34), so the nested `format filter { ... request>uri query { ... } }` braces must keep it passing; add an assertion that the companion block contains the three `delete` lines. Env example: add `SKYPANE_AUTH0_DOMAIN`, `SKYPANE_AUTH0_CLIENT_ID`, `SKYPANE_AUTH0_CLIENT_SECRET`, `SKYPANE_LEGACY_PASSWORD_LOGIN`, optional `SKYPANE_COMPANION_PUBLIC_URL`, following the existing `SKYPANE_COMPANION_HOST` entry style. README: owner steps (Allowed Callback/Logout URLs, sign-up disabled), the root-owned `fleet.db` failure mode, the rollback sentence about schema v2, and the event-driven legacy-admin removal note.

## Shared Patterns

### Constant-time comparison and fail-closed config
**Source:** `companion/auth.py` lines 109-131.
**Apply to:** `oidc.py` (`state`, `nonce`), `app.py` `main()` startup rules.
Error messages name the variable only, never a value (`AuthNotConfigured` text, lines 102-120).

### Secure cookie attributes
**Source:** `companion/auth.py` lines 174-207 (`secure_cookie_flag()`, `session_set_cookie_header`, `logout_set_cookie_header`).
**Apply to:** session cookie (Strict), pre-login `sp_oidc` cookie (Lax, `Path=/callback`), logout clearing of both.

### Login throttle and client identity
**Source:** `companion/auth.py` `LoginThrottle`, `login_throttle_key`; `app.py:956-990` `_login_throttle_key`, `LOGIN_THROTTLE` (app.py:240).
**Apply to:** legacy password POST only.

### Origin gate before routing
**Source:** `app.py:945-946` (`auth.post_origin_ok`).
**Apply to:** unchanged, must remain the first statement of `_dispatch`. This is the only CSRF control added to this phase (no per-session tokens; open question for Phase 55).

### Per-request DB scope and fail-closed errors
**Source:** `app.py:923-932` `do_GET` / `history_db.connection_scope`.
**Apply to:** the `fleet.db` connection used by principal resolution; 503 on DB error for gated routes.

### i18n for every user-facing literal
**Source:** `companion/login_page.py` lines 27-79 (`i18n.msg(key, english)` at module level, `i18n.t(...)` + `layout.escape_html(...)` at render).
**Apply to:** login, not-invited, interstitial, account pages and the legacy-access flag.

### Hostile-id handling
**Source:** `fleet_db.add_device` id format (`d_` + 8 hex, `fleet_db.py:386-420`); `routes.match()` captured values.
**Apply to:** `access.decide` / `device_for` (regex-validate before any lookup).

### Conventions enforced by CI
Function size max 80 (`server/`, `stub-server/`), no plan/phase/decision IDs in comments (`scripts/check_comment_history.py`), ruff, mypy for typed server modules, tests assert behaviour not source text, English code/comments with French strings only under `companion/i18n_fr/`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| OIDC PKCE/claim validation inside `companion/oidc.py` | utility | transform | No OAuth or JWT code exists in the repo; use RESEARCH 435-467 and the claim-check list at 259 |
| `companion/test_browser_auth0.py` | test | request-response | Browser tests exist but none cross two sites; use `localhost` for the fake and `127.0.0.1` for the app (RESEARCH 311) and the `companion/conftest.py` `new_context` guard (allows `127.0.0.1`, `localhost`, `::1`) |

## Metadata

**Analog search scope:** `companion/`, `server/fleet_db.py`, `stub-server/fleet_cli.py`, `test-support/`, `deploy/`
**Files read for excerpts:** `companion/routes.py`, `companion/auth.py` (100-230), `companion/app.py` (545-575, 885-995), `companion/login_page.py`, `companion/test_route_table.py` (50-145), `server/fleet_db.py` (75-340), `stub-server/fleet_cli.py` (70-110), `test-support/companion_app_server.py` (95-155, 296-347), `companion/post_actions.py` (imports, mixin header)
**Not re-read (relied on RESEARCH.md line references):** `fleet_migrate.py`, `byos_server.py`, `deploy/*`, `LoginThrottle` body, `test_fleet_db.py`
**Pattern extraction date:** 2026-10-30
