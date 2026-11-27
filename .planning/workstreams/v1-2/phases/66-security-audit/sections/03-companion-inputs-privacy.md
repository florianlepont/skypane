# Area: Companion input handling and photo privacy

## Scope read

Companion request handling and routing (`app.py`, `routes.py`, `route_types.py`, `access.py`, `auth.py`, `request_body.py`, `upload_form.py`, `page_policy.py`, `next_route.py`, `server_error.py`, `static_files.py`), the POST handlers and upload path (`post_actions.py`, `airline_actions.py`, `co_managers.py`, `frame_rename.py`, `resolve_dialog.py`), the export API (`export_api.py`), the flash-message vocabulary (`flash.py`, `console_flash.py`), the console modules, the page renderers and their escaping helpers, the two scripts that insert server fragments, the illustration validation in the server package, and the backup script under `deploy/backup/`.

## Method

Code and configuration reading, the registered route table inspected locally (no server started), and the existing local companion tests selected by name (CSRF, headers, upload, escaping, XSS, traversal, size). Browser tests were not run here and rely on CI. No request was sent to any server, no fuzzing, no real data read.

## Checks performed

- [x] Route inventory: 124 registered routes, 42 of them POST. Every POST route requires the per-session anti-forgery token (checked from the route table, no POST route without it), after the Origin / Sec-Fetch-Site gate that runs before routing.
- [x] CSRF design: token derived from the session token (constant-time compare), session cookie HttpOnly and SameSite=Strict, pre-login cookie SameSite=Lax scoped to the callback path only. 303 reopen links use the route's own path, never the query.
- [x] Request size limits: form bodies capped at 8 KiB, upload bodies at 4 MiB, both enforced by one capped read that drains the remainder; unparseable or negative lengths degrade to an empty body; socket timeouts are bounded.
- [x] Upload handling: strict multipart reader (token part first, one file part, no other parts), part headers and filenames never read, destination key checked against a known-name allow-list, temp file created with a unique name and removed on every path, image decoded only after a header check (PNG format, minimum width, landscape, alpha, 40-million-pixel ceiling), then re-encoded in memory before being stored. Only the administrator role can upload.
- [x] Path handling: gallery files are matched against a directory listing and never joined from the request; runway images are membership-tested before use; illustration names are allow-listed; device ids match a strict pattern; static assets are an exact allow-list with no catch-all directory route; the export `device` parameter is format-checked, looked up in the fleet database, and the directory is built from the stored path.
- [x] Output escaping: page renderers escape user-supplied text (device names, airline names, e-mail addresses, audit fields) through the shared escape helper or a module-local wrapper of it; the two scripts that use `innerHTML` only insert fragments returned by the same-origin server.
- [x] Response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy` (no inline script, `frame-ancestors 'none'`, `form-action 'self'`), `Permissions-Policy` on every response; `Cache-Control: no-store` or private on authenticated pages; HSTS is set at the reverse proxy.
- [x] Redirect targets: the sign-in `next` value is matched against exact page routes with a restricted query pattern; resolve-flow return targets come from a fixed allow-list; frame redirects are built from the frame id and a re-encoded query.
- [x] Data access: SQL in the companion binds parameters; the two statements that build a table or column name take them from fixed in-code mappings. No subprocess or shell invocation in the companion.
- [x] Error pages: unexpected errors return a generic page; the log line holds the method and path only, never headers, cookies, bodies or query strings.
- [x] JSON and export endpoints: bearer-token only (cookie never read), constant-time compare, per-client failure throttle checked before the compare, strict `since` and `device` parsing, row cap, `no-store`, no secret, name, location or path in the output.
- [x] Targeted tests: 262 passed, 1 skipped (a browser-dependent test that needs a Chromium download, relies on CI).

## Administrator and user photos

Current state: photo mode is not built, so no user-provided photo is stored or served. The per-device image routes (display archive, theme and frame previews, airline artwork) serve renderings produced by the server from flight data and vendored or administrator-uploaded artwork. Per-device routes follow the shared access rule that an administrator reaches any existing device. The export API carries only flight, battery and status rows, no image. The nightly backup archives the per-device state directories, including the display archive. No log line records image content or names that identify people.

No test asserting that an administrator cannot fetch a device image was added: the access rules of the earlier sign-in, console and co-management phases deliberately let the administrator open any frame's pages, and no photo route exists yet to assert against.

## Result

pending consolidation

## Medium and low items

| ID | Category | Location | Recommendation | Severity |
|----|----------|----------|----------------|----------|
| C-01 | Documentation drift | `companion/post_actions.py` (docstrings of the manual-resolve and delete handlers) | Comments say these routes carry no token; the route table now requires it. Update the comments so a reader is not misled. | Low |
| C-02 | Hardening | `companion/page_policy.py` | `style-src` allows inline styles. Move the theme-swatch colours to classes or custom properties so the allowance can be dropped. | Low |
| C-03 | Resource limits | `server/plane/illustrations.py` (pixel ceiling) | The 40-million-pixel ceiling is far above what an illustration needs; a lower ceiling bounds memory use of the one decode, which only the administrator can trigger. | Low |
| C-04 | Defence in depth | `companion/auth.py` (Origin gate) | A POST with no Origin and no Sec-Fetch-Site is accepted, by design, for header-less clients. The token and SameSite=Strict cover it; no change required, keep covered by tests. | Informational |

## Follow-ups for next milestones

- Photo privacy (v1.4): per-device routes admit the administrator for any frame today. Stored user photos need their own access kind that excludes the administrator (owner and co-managers only), a storage location outside the directories the administrator-facing routes and export read, and an explicit decision on whether and how photos are included in or excluded from the backup archive. Add the behaviour test for "administrator cannot fetch another user's photo" together with the feature.
