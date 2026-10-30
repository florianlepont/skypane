# Device-scoped routes

Inventory of the companion routes that act on one device, for the auth phase to annotate with a minimum role and an ownership check.

The tables below were generated from `companion/routes.ROUTES` at the commit this file was written (a throwaway script walked the table; nothing in the repository reads this file). Count check: **13 GET + 14 POST = 27** routes have `device_scoped=True`; `companion/test_device_routes.py::TestPrefixMatching::test_flagged_routes_equal_the_explicit_list` fails if the route table and the explicit expected set diverge, so a route that changes scope cannot go unnoticed.

`{id}` is a device id of the form `d_` plus eight lowercase hex digits (`^/devices/(d_[0-9a-f]{8})(/.*)?$`, anchored on the raw path). `{key}` is the one captured path segment of a prefix-matched route (a gallery file name, an illustration key, a theme id, a manual-resolution prefix or a colour-rule key). Every route is also reachable un-prefixed, where it acts on the live frame (the first device in the fleet).

Access class is a suggestion for the auth phase, not an existing control: `read` returns device data or an image, `write` changes the device's configuration or picture, `destructive` removes stored configuration. The last column is intentionally empty.

## Device-scoped GET routes (13)

| Method | Un-prefixed path | Path under the prefix | Handler | Access class | What it reads or writes in the device directory | Minimum role / ownership check (auth phase) |
|---|---|---|---|---|---|---|
| GET | `/` | `/devices/{id}` | `Handler._render_tab with home_page.render` | read | Reads the device's picture (gallery/), history.db, battery_state.json, poll_state.json, device_config.json; never-seen and offline states derive from the device's own check-ins. | |
| GET | `/display` | `/devices/{id}/display` | `Handler._render_tab with config_page.render` | read | Reads device_config.json, colour_rules.json, calendar_rules.json, airline_name_overrides.json; `?sheet=manage` opens the calendar sheet. | |
| GET | `/device` | `/devices/{id}/device` | `Handler._render_tab with config_page.render` | read | Reads device_config.json, battery_state.json and history.db (device_health); shows hardware type, wake interval, time zone, LED and poll controls. | |
| GET | `/flights` | `/devices/{id}/flights` | `Handler._render_tab with history_page.render` | read | Reads history.db (runway events) and gallery/ for the device. | |
| GET | `/health` | `/devices/{id}/health` | `Handler._render_tab with health_page.render` | read | Reads history.db (device_health), battery_state.json, poll_state.json; the device's own last check-in drives the unreachable toast. | |
| GET | `/airlines` | `/devices/{id}/airlines` | `Handler._render_tab with airlines_page.render` | read | Reads poll_state.json (unresolved prefixes), manual_resolutions.json, airline_name_overrides.json, illustration_overrides/; `?resolve=<prefix>` opens the resolve dialog. | |
| GET | `/settings` | `/devices/{id}/settings` | `Handler.redirect` | read | Fixed 303 to the device's Display page; reads nothing. | |
| GET | `/history` | `/devices/{id}/history` | `Handler.redirect` | read | Fixed 303 to the device's Flights page; reads nothing. | |
| GET | `/preview` | `/devices/{id}/preview` | `Handler.redirect` | read | Fixed 303 to the device's Flights page; reads nothing. | |
| GET | `/gallery/{key}` | `/devices/{id}/gallery/{key}` | `Handler._serve_gallery_image` | read | Serves one file of the device's gallery/ directory (exact scandir match, never joined onto a path). | |
| GET | `/illustration/{key}.png` | `/devices/{id}/illustration/{key}.png` | `Handler._serve_illustration_image` | read | Serves the vendored or device-overridden illustration (illustration_overrides/). | |
| GET | `/theme-preview/{key}.png` | `/devices/{id}/theme-preview/{key}.png` | `Handler._serve_theme_preview_image` | read | Renders a theme preview for the device's panel size; `?live=1` reads the device's newest runway event. | |
| GET | `/frame-preview/{key}.png` | `/devices/{id}/frame-preview/{key}.png` | `Handler._serve_frame_preview_image` | read | Renders a frame preview (theme, `state`, `size` query) for the device's panel size. | |

## Device-scoped POST routes (14)

| Method | Un-prefixed path | Path under the prefix | Handler | Access class | What it reads or writes in the device directory | Minimum role / ownership check (auth phase) |
|---|---|---|---|---|---|---|
| POST | `/settings` | `/devices/{id}/settings` | `Handler._handle_settings_post` | write | Validates and writes device_config.json; may sync the device's calendar feed under its poll lock (calendar_rules.json). | |
| POST | `/poll-now` | `/devices/{id}/poll-now` | `Handler._handle_poll_now` | write (action) | Runs one poll cycle against the device directory only, under its own lock and cooldown: writes poll_state.json, history.db, panel.bin, img/. Refused for hardware the cycle cannot render. | |
| POST | `/quick/display` | `/devices/{id}/quick/display` | `Handler._handle_quick_toggle` | write | Flips display_enabled in device_config.json. | |
| POST | `/quick/quiet-hours` | `/devices/{id}/quick/quiet-hours` | `Handler._handle_quick_toggle` | write | Flips quiet_hours_enabled in device_config.json. | |
| POST | `/quick/led` | `/devices/{id}/quick/led` | `Handler._handle_quick_toggle` | write | Flips led_enabled in device_config.json. Session-checked POST only (no CSRF token); return_to is whitelisted. | |
| POST | `/airlines/resolve` | `/devices/{id}/airlines/resolve` | `Handler._handle_manual_resolve_post` | write | Adds a manual airline resolution to manual_resolutions.json. | |
| POST | `/airlines/rename` | `/devices/{id}/airlines/rename` | `Handler._handle_airline_rename_post` | write | Writes airline_name_overrides.json and may copy artwork into illustration_overrides/. | |
| POST | `/airlines/rename/reset` | `/devices/{id}/airlines/rename/reset` | `Handler._handle_airline_rename_reset_post` | write | Clears entries in airline_name_overrides.json. | |
| POST | `/airlines/manual-resolutions/{key}/delete` | `/devices/{id}/airlines/manual-resolutions/{key}/delete` | `Handler._handle_manual_resolution_delete` | destructive | Deletes one entry from manual_resolutions.json. | |
| POST | `/illustration/{key}.png` | `/devices/{id}/illustration/{key}.png` | `Handler._handle_illustration_replace` | write (upload) | Re-encodes an uploaded image and writes it to illustration_overrides/ (client bytes are never stored raw). | |
| POST | `/settings/rules/add` | `/devices/{id}/settings/rules/add` | `Handler._handle_rule_add_post` | write | Adds a colour rule to colour_rules.json. | |
| POST | `/settings/calendar/disconnect` | `/devices/{id}/settings/calendar/disconnect` | `Handler._handle_calendar_disconnect_post` | destructive | Clears the calendar feed URL and registry in calendar_rules.json. | |
| POST | `/settings/calendar/connect` | `/devices/{id}/settings/calendar/connect` | `Handler._handle_calendar_connect_post` | write | Saves the calendar feed URL (a secret) in calendar_rules.json and syncs under the device's poll lock. | |
| POST | `/settings/rules/{key}/delete` | `/devices/{id}/settings/rules/{key}/delete` | `Handler._handle_rule_delete_post` | destructive | Deletes a colour rule from colour_rules.json. | |

## Routes that are not device-scoped

These never match under `/devices/{id}` (`routes.match` returns None there, which the dispatcher answers with the 404 page).

| Method | Path | Handler | Session required | Why it is global |
|---|---|---|---|---|
| GET | `/login` | `Handler._handle_login_get` | no | Pre-session (`auth_required=False`); no device. |
| GET | `/update` | `Handler._render_tab with update_page.render` | yes | Firmware update page. The OTA registry is per hardware type at the state root, not per device. |
| GET | `/runway-image/{key}.png` | `Handler._serve_runway_image` | yes | Static runway diagram from a fixed id allow-list; identical for every device. Session required. |
| POST | `/login` | `Handler._handle_login_post` | no | Pre-session (`auth_required=False`); creates the session. |
| POST | `/ui-theme` | `Handler._handle_theme_post` | yes | Browser preference cookie; not device state. |
| POST | `/ui-lang` | `Handler._handle_lang_post` | yes | Browser preference cookie; not device state. |
| POST | `/logout` | `Handler._handle_logout_post` | yes | Ends the session; not tied to a device. |
| POST | `/update/install` | `Handler._handle_update_install_post` | yes | Publishes or schedules a release in the per-hardware-type OTA registry at the root, not per device. |
| POST | `/update/cancel` | `Handler._handle_update_cancel_post` | yes | Cancels a scheduled release in the per-hardware-type OTA registry at the root, not per device. |
| GET | `/static/...` (21 fixed asset paths from `companion/static_files.STATIC_ROUTES`) | `Handler._serve_static_route` | no | Public stylesheet, scripts, favicon and touch icon; identical for every device and needed before login. |

Constants as named in `companion/routes.py`: `UPDATE_ROUTE` = `/update`, `UPDATE_INSTALL_ROUTE` = `/update/install`, `UPDATE_CANCEL_ROUTE` = `/update/cancel`; all three stay global because the OTA registry is per hardware type at the state root.

## How the annotation hook works

- `routes.Route` has a `device_scoped` field. It is derived once in `routes.ROUTES` from `_DEVICE_SCOPED_KEYS` (page and image keys plus action keys), so adding a route to the table without listing it there leaves it global.
- `routes.match(method, path, query)` strips a well-formed `/devices/{id}` prefix, matches the remainder against the `device_scoped` routes only, and reports the id on `RouteMatch.device_id`. A malformed prefix (wrong length, upper case, encoded slash, trailing newline) finds nothing.
- `Handler._dispatch` order: POST Origin / Sec-Fetch-Site gate, then `routes.match` (no match: 404), then the session gate (`require_session()`, for every route with `auth_required=True`), then device resolution in `_dispatch_for_device`. The session gate therefore always runs before any device lookup, and an unauthenticated request cannot probe which device ids exist.
- `_dispatch_for_device` resolves `RouteMatch.device_id` through `device_scope.find_device` against `fleet.db`; the result is passed to the handler as `RouteMatch.device` (a `device_scope.Device` with `id`, `name`, `hardware_type`, `state_path`, `state_dir`, `is_live`). An id with no `fleet.db` row is the 404 page. An un-prefixed route uses the live frame (the first loaded device). There is no fallback from an unknown id to the live frame, and no handler reads a global state directory for device data.
- This is the single place for the auth phase to add the check: after `find_device` returns and before `route.handler` runs, compare the session's user against `Device` ownership (`fleet.db` `devices.owner_user_id`, user roles in `fleet.db`) using the route's access class. `Device` does not yet carry the owner; add it to `device_scope.load_devices` / `find_device` when needed.
- `GET` device-scoped pages also accept a `?device=<id>` query (the no-script selector form); `device_scope.switch_target` redirects to the same page under that device, 404 for an unknown id. The redirect target is built only from the fixed page path and a validated id.
- The device selector, the in-page links, form actions and `return_to` values on every device page are covered by `TestPrefixCrawl` in `companion/test_device_routes.py`, which classifies each address through `routes.match`.

## BYOS device endpoints (not companion routes)

Served by `stub-server/byos_server.py` (`skypane-byos.service`), a separate HTTP server from the companion. They are authenticated by the frame's own credential, never by the companion session and never by the companion password, so the auth phase must not treat them as companion routes or gate them on a user session.

| Method | Path | Authentication | Device resolution | Notes |
|---|---|---|---|---|
| POST | `/device/v1/setup` | Provision secret in the body (`secret_matches` against the registered hash) | MAC in the body; must be registered | Enrolment: issues the device token. 403 unregistered, 401 bad secret, 503 enrolment unavailable. |
| GET | `/device/v1/display` | `Authorization: Bearer <device token>` (constant-time compare over all tokens) | Token to MAC, then the `fleet.db` row by MAC | 401 for an unknown token or a MAC with no `fleet.db` row; 503 when the stored state path or hardware type is unusable or the panel file is missing or wrong-sized; never serves the live image to another device. Non-live devices get `image_url` `/img/{id}/{sha256}.bin`; the live frame gets `/img/{sha256}.bin`. Also records telemetry and the OTA offer. |
| POST | `/device/v1/log` | Bearer device token | None (logged to stdout only) | Frame log lines. |
| GET | `/img/{sha256}.bin` | None (content-addressed) | Live frame's `img/` directory | The hash is unguessable and is only advertised to an authenticated frame. |
| GET | `/img/{id}/{sha256}.bin` | None (content-addressed) | `fleet.db` row by id; only a non-live `devices/` directory; unknown id, live id or unusable path is the same 404 | Per-device image download. |
| GET | `/fw/{sha256}.bin` | None (signed release images carry no credential) | Release registered in the OTA registry | OTA download. The OTA offer itself is part of the `/device/v1/display` response. |

The device-scoped companion routes and the BYOS endpoints share one state directory and `fleet.db`, but the two sides authenticate differently: users by session, frames by token.
