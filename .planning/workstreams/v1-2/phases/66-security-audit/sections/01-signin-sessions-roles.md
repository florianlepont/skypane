# Area: Sign-in, sessions, roles and default-deny access

## Scope read

- Companion sign-in: `companion/oidc.py`, `companion/sign_in.py`, `companion/auth.py`, `companion/next_route.py`, `companion/login_page.py` (interstitial), `companion/auth0_management.py`
- Roles and access: `companion/access.py`, `companion/routes.py`, `companion/route_types.py`, `companion/console_routes.py`, `companion/user_pairing.py`, `companion/frame_rename.py`, `companion/co_managers.py`, `companion/console_users.py`, `companion/page_policy.py`
- Request dispatch in `companion/app.py` (origin gate, route match, access decision, CSRF check)
- Server-side session store: `server/fleet_sessions.py`

## Method

Code and configuration reading only. No request was sent to any host. Existing local tests for these modules were run (non-browser selection); browser tests rely on CI. Configuration was read by variable name only; no value was read or printed.

## Checks performed

- [x] Authorization-code flow with PKCE (S256), per-attempt state and nonce, single-use bounded attempt table, constant-time state and nonce comparison
- [x] ID-token claim validation (issuer, audience, authorized party, expiry, issued-at, nonce, subject bounds, `alg: none` refusal); token endpoint call hardened (no proxy or netrc, TLS verification, no redirects, size and time caps)
- [x] Redirect target after sign-in: positive allow-list of known page routes, strict query pattern, length cap; interstitial refuses anything but a local path or fixed provider URL and escapes it
- [x] Session cookie attributes (HttpOnly, Secure by default, SameSite=Strict, Path, Max-Age); pre-login cookie scoped to the callback path with SameSite=Lax by necessity
- [x] Session lifetime (absolute and idle limits), only a hash of the token stored, rotation of a previous session on sign-in, deletion on logout, expiry swept on sight and periodically
- [x] Role, disabled state and existence read from the local fleet database on every request; an identity with no local record or an unverified address gets no session
- [x] CSRF: origin and fetch-site gate on every POST before routing, per-session token on state-changing routes, constant-time comparison, empty values refused
- [x] Shared-password fallback: no longer a sign-in path; leftover session rows of that kind are refused and deleted
- [x] Management token: read from the environment only, audience-only request, never logged
- [x] Rate limiting: per-client limit on sign-in starts (IPv6 collapsed to /64), forwarded-address header trusted only from a loopback peer, failure throttle on the bearer-token export routes
- [x] Constant-time comparison for the bearer token and for state and nonce values
- [x] Route x role x owner matrix: owner, non-owner, co-manager, administrator and anonymous outcomes per route, owner-only routes exclude co-managers, un-prefixed device routes are administrator-only, malformed or unknown device ids give the same answer as an unknown path
- [x] Default-deny proof: `companion/test_access_matrix.py` enumerates the registered route table and fails when a route has no policy row or a row has no route; it also checks every route over HTTP against the local fixture server for each caller kind, plus disabled, deleted, expired, legacy and demoted-session cases. No extension was needed.
- [x] Co-manager grants and device scope: grant, removal and leave handlers are bound to the gate-authorised device; the access view is offered to the owner and administrators only

## Test run

`pytest companion -k "auth or access or oidc or role or scope"` with the project addopts overridden (the socket-guard plugin is not installed in this environment) and browser test files excluded: 2624 passed. Browser tests rely on CI.

## Result

medium/low recorded

## Medium and low items

| ID | Category | Location | Recommendation | Severity |
|----|----------|----------|----------------|----------|
| A-01 | Hardening | `companion/auth.py` (`csrf_token`) | The anti-forgery value is derived from the session token and is stable for the session. Acceptable with an HttpOnly cookie; consider a per-session random value stored beside the session if forms ever render in less trusted contexts. | Low |

## Follow-ups for next milestones

- Self sign-up is disabled in the identity provider tenant (checked by the owner on 2026-11-27); the sign-in path relies on invitation.
- ID-token signature is not verified locally because the token arrives straight from the provider over TLS in the code exchange; this is documented in the module and is within the protocol rules. Revisit if any other token source is ever accepted.
- Callback and sign-out have no per-client throttle of their own; the callback is bounded by the attempt table and requires a live attempt cookie. Revisit with the deploy-area review of the reverse proxy.
