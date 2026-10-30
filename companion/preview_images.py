"""Theme and frame preview PNG routes, moved out of `companion/app.py`'s
`Handler`. Packaged as a `PreviewImagesMixin` `Handler` inherits, like
`DeviceDispatchMixin`.

Never imports `companion.app` (that would be a cycle). The facts it needs
from the handler (`self.path`, `self.send_html()`, `self.send_bytes()`,
`self._not_found_page()`) are provided by `Handler`.
"""
from urllib.parse import parse_qs, urlsplit

from companion import theme_preview
from server import device_config, history_db
from server.plane import name_overrides


def _safe_latest_runway_event(state_dir):
    """The single most recent `runway_events` row (the `?live=1` render
    source), or `None` on any failure — a missing/locked/unreadable
    database, a malformed row, or simply no event recorded yet.
    Deliberately a broad `except Exception` (not the narrower
    `(sqlite3.Error, OSError)` `_safe_last_checkin_ts()` above uses): any
    exception reading the event must degrade to `live_event=None` (the
    fixed fictional scene), never a 500 — this route's one query is not
    allowed to be the reason a preview image fails to render.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(
                conn, limit=1,
                airline_names=name_overrides.names_by_prefix(
                    name_overrides.load_name_overrides(state_dir)))
    except Exception:
        return None
    return rows[0] if rows else None


class PreviewImagesMixin:
    def _serve_theme_preview_image(self, device, theme_id):
        # Membership test first, same shape as _serve_runway_image().
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        # The non-live variant is always the fixed fictional scene. A
        # `?live=1` request reads the operator's own most recent
        # runway_events row and renders it into a raster (never markup);
        # any read/coercion failure degrades to the fixed scene.
        parsed = urlsplit(self.path)
        live_flag = parse_qs(parsed.query).get("live", [None])[0]
        live_event = None
        if live_flag == "1":
            live_event = _safe_latest_runway_event(device.state_dir)
        try:
            payload = theme_preview.cached_preview_bytes(
                device.state_dir, theme_id, live_event=live_event)
        except OSError:
            return self.send_html(404, self._not_found_page())
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _serve_frame_preview_image(self, device, theme_id):
        # Every part is an allow-list member before it reaches the cache
        # path: the theme id from the registry, state and size from
        # theme_preview's own tuples. A missing parameter takes the
        # default; an unknown one is a 404, never a guess.
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        query = parse_qs(urlsplit(self.path).query)
        state = query.get("state", [theme_preview.FRAME_PREVIEW_STATE_DEPARTING])[0]
        size = query.get("size", [theme_preview.FRAME_PREVIEW_SIZE_LARGE])[0]
        if (state not in theme_preview.FRAME_PREVIEW_STATES
                or size not in theme_preview.FRAME_PREVIEW_SIZES):
            return self.send_html(404, self._not_found_page())
        try:
            payload = theme_preview.cached_frame_preview_bytes(
                device.state_dir, theme_id, state, size)
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)
