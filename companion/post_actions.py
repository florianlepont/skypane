"""The settings-action POST handlers moved out of `companion/app.py`'s
`Handler`: illustration replace, the two-step manual-resolution flow,
the colour-rules add/delete pair, and the calendar connect/disconnect
pair. Packaged as a `SettingsActionsMixin`
`Handler` inherits (`Handler(SettingsActionsMixin, BaseHTTPRequestHandler)`)
so every method keeps its historical name and `companion/routes.py`'s
`ROUTES` table keeps resolving it unchanged.

Never imports `companion.app` (that would be a cycle — app.py imports
this module). `_POLL_LOCK` lives here (guarding the calendar-connect
route's own sync below) because it must be the same lock object
`companion/app.py`'s `_handle_settings_post()`/`_handle_poll_now()`
serialise against; app.py rebinds it under its historical name.
"""
import email.message
import io
import os
import tempfile
import threading
from urllib.parse import quote

from PIL import Image

from companion import layout
from companion.flash import (
    FLASH_KEY_CALENDAR_CONNECT_INVALID,
    FLASH_KEY_CALENDAR_CONNECT_OK,
    FLASH_KEY_CALENDAR_DISCONNECTED,
    FLASH_KEY_CALENDAR_SYNC_DEFERRED,
    FLASH_KEY_CALENDAR_SYNC_FAILED,
    FLASH_KEY_ILLUSTRATION_REJECTED,
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED,
    FLASH_KEY_ILLUSTRATION_REPLACED,
    FLASH_KEY_MANUAL_DELETE_FAILED,
    FLASH_KEY_MANUAL_NAME_EMPTY,
    FLASH_KEY_MANUAL_NAME_RESERVED,
    FLASH_KEY_MANUAL_NAME_TOO_LONG,
    FLASH_KEY_MANUAL_NAME_UNUSABLE,
    FLASH_KEY_MANUAL_PREFIX_STALE,
    FLASH_KEY_MANUAL_REGISTRY_FULL,
    FLASH_KEY_MANUAL_RESOLVED,
    FLASH_KEY_MANUAL_SAVE_FAILED,
    FLASH_KEY_RENAME_FULL,
    FLASH_KEY_RENAME_TAKEN,
    FLASH_KEY_RENAME_RESET,
    FLASH_KEY_RENAME_SAVE_FAILED,
    FLASH_KEY_RENAME_STALE,
    FLASH_KEY_RENAMED,
    FLASH_KEY_RULE_ADDED,
    FLASH_KEY_RULE_DELETE_FAILED,
    FLASH_KEY_RULE_DELETED,
    FLASH_KEY_RULE_KEY_INVALID,
    FLASH_KEY_RULE_REGISTRY_FULL,
    FLASH_KEY_RULE_REPLACED,
    FLASH_KEY_RULE_SAVE_FAILED,
)
from companion.pages import airline_sheet, airlines_page, config_page
from companion.pages.airlines_page import unresolved_row_for_prefix
from server import atomic_io
from server.plane import (
    calendar_rules, colour_rules, enrich, illustrations, manual_resolutions, name_overrides,
)
import server.poll_cycle as poll_cycle

# Bounds peak memory per upload to a few MB. Enforced by the caller
# (SettingsActionsMixin._read_upload_body() on companion/app.py's
# Handler), not by parse_single_uploaded_file(). companion/app.py
# rebinds this under its historical name — companion/pages/airlines_page.py
# also imports it from there lazily.
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024

# Guards the calendar-connect route's own sync below against racing a
# concurrent /poll-now trigger or the systemd timer's own oneshot cycle;
# process-local only, unlike calendar_rules' own cross-process
# fcntl.flock(). companion/app.py's _handle_settings_post()/
# _handle_poll_now() share this exact object, rebound under its
# historical name — never a second, independent Lock().
_POLL_LOCK = threading.Lock()


def _illustration_filenames(state_dir=None):
    """The known-safe membership set for validating a requested
    illustration key before any filesystem path is constructed: the
    fixed vendored list, unioned with resolved `manual_resolutions.json`
    entries. The manual half comes from a prior, already-durable
    request, never the current one. Recomputed per call, never cached,
    since that manual state is mutable.
    """
    filenames = set(illustrations.target_filenames())
    if state_dir:
        for entry in manual_resolutions.load_manual_resolutions(state_dir).values():
            key = manual_resolutions.illustration_key_for_name(entry["airline_name"])
            if key:
                filenames.add(key + ".png")
        filenames |= _renamed_illustration_filenames(state_dir)
    return frozenset(filenames)


def _renamed_illustration_filenames(state_dir):
    """The artwork filenames of airlines the owner renamed: the new name's
    own key, plus one per aircraft-type variant the built-in airline has,
    so a renamed airline can be given artwork exactly as before."""
    filenames = set()
    for prefix, entry in name_overrides.load_name_overrides(state_dir).items():
        key = manual_resolutions.illustration_key_for_name(entry["airline_name"])
        if not key:
            continue
        filenames.add(key + ".png")
        built_in = enrich.static_airline_name_for_prefix(prefix)
        for shape in airline_sheet.artwork_shapes(built_in):
            filenames.add("%s-%s.png" % (key, shape))
    return filenames


def _carry_artwork_to_new_name(state_dir, from_name, to_name, shapes):
    """Best-effort copy of the artwork flights use under `from_name` to the
    key `to_name` resolves to, so renaming does not blank the airline's
    pictures on new flights. Copies, never moves, and only when `to_name`
    has no artwork at all (it may be another airline's name); the old
    key's files stay, so a reset (and every older picture) still finds them.
    """
    from_key = illustrations.normalise_airline_key(from_name)
    to_key = illustrations.normalise_airline_key(to_name)
    if not from_key or not to_key or from_key == to_key:
        return
    suffixes = [""] + ["-" + shape for shape in shapes]
    if any(illustrations.resolved_illustration_path(to_key + suffix, state_dir) for suffix in suffixes):
        return
    for suffix in suffixes:
        source = illustrations.resolved_illustration_path(from_key + suffix, state_dir)
        target = illustrations.override_path_for_key(to_key + suffix, state_dir)
        if source is None or target is None:
            continue
        try:
            with open(source, "rb") as fh:
                data = fh.read()
            os.makedirs(os.path.dirname(target), exist_ok=True)
            atomic_io.atomic_write(target, data)
        except OSError as exc:
            print("airline rename: could not carry artwork %s: %s" % (suffix or "base", exc))


_RENAME_FLASH_BY_RESULT = {
    manual_resolutions.ADD_REJECTED_NAME_TOO_LONG: FLASH_KEY_MANUAL_NAME_TOO_LONG,
    manual_resolutions.ADD_REJECTED_NAME_RESERVED: FLASH_KEY_MANUAL_NAME_RESERVED,
    manual_resolutions.ADD_REJECTED_PREFIX: FLASH_KEY_RENAME_STALE,
    manual_resolutions.ADD_REJECTED_FULL: FLASH_KEY_RENAME_FULL,
    name_overrides.SET_NAME_TAKEN: FLASH_KEY_RENAME_TAKEN,
}


def parse_single_uploaded_file(content_type, body):
    """Parse a `multipart/form-data` body known to hold exactly one file
    part, returning its raw payload `bytes`, or `None` for anything that
    doesn't match that exact shape. Never raises. The header block
    (filename, field name, media type) is discarded and never parsed —
    the destination path and the "is this an image" check both come
    from elsewhere, never from this body's own claims.
    """
    try:
        message = email.message.Message()
        message["content-type"] = content_type
        if message.get_content_type() != "multipart/form-data":
            return None
        boundary = message.get_param("boundary")
        if not isinstance(boundary, str) or not boundary:
            return None
        boundary_bytes = boundary.encode("ascii")
        if len(boundary_bytes) > 70:  # RFC 2046 boundary length ceiling.
            return None

        delimiter = b"--" + boundary_bytes
        segments = body.split(delimiter)
        # Exactly one part: a preamble, the part itself, and an epilogue.
        # Zero parts, two-or-more parts, and a missing closing delimiter
        # all produce a different segment count and are rejected here.
        if len(segments) != 3:
            return None
        preamble, part, epilogue = segments
        if preamble.strip(b"\r\n \t") != b"":
            return None
        if not epilogue.startswith(b"--"):
            return None

        if not part.startswith(b"\r\n"):
            return None
        part = part[2:]
        header_block, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            return None
        del header_block  # discarded — see docstring above.

        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if not payload:
            return None
        return payload
    except Exception:
        return None


class SettingsActionsMixin:
    """The eight settings-action POST handlers. `Handler` inherits this
    ahead of `BaseHTTPRequestHandler` (`Handler(SettingsActionsMixin,
    BaseHTTPRequestHandler)`), so every method below runs with the full
    `self` a request handler provides (`self.args`, `self.read_form()`,
    `self.redirect()`, `self.send_html()`, `self.page_context()`,
    `self._page_shell_for()`, `self._not_found_page()`, `self._read_upload_body()`).
    """

    def _handle_illustration_replace(self, key):
        """POST /illustration/{key}.png — upload a replacement
        illustration, the first untrusted file upload this codebase
        handles. Membership-tests `key` before any path is built or
        body byte is read. Only the server's own Pillow re-encode is
        ever written to disk — the client's original bytes are never
        stored. No CSRF token: relies on SameSite=Strict, like every
        other state-changing POST.
        """
        filename = key + ".png"
        if filename not in _illustration_filenames(self.args.state_dir):
            return self.send_html(404, self._not_found_page())

        raw = self._read_upload_body()
        if raw is None:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        payload = parse_single_uploaded_file(self.headers.get("Content-Type"), raw)
        if payload is None or len(payload) > MAX_ILLUSTRATION_UPLOAD_BYTES:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        state_dir = self.args.state_dir
        override_dir = illustrations.override_dir_for_state_dir(state_dir)
        try:
            os.makedirs(override_dir, exist_ok=True)
        except OSError:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))

        # The raw upload's temp lives in override_dir (mkstemp: a unique
        # name, so two concurrent uploads of the same key can never
        # collide) so it never needs a cross-filesystem copy before
        # validate_illustration_file()/Image.open() read it back. The
        # encoded PNG is never staged as a file at all - it is built in
        # memory and published straight through atomic_io.atomic_write(),
        # which owns its own unique temp name and cleans it up on any
        # failure.
        raw_tmp_path = None
        try:
            raw_tmp_fd, raw_tmp_path = tempfile.mkstemp(
                dir=override_dir, prefix="." + key + ".upload.", suffix=".tmp")
            with os.fdopen(raw_tmp_fd, "wb") as fh:
                fh.write(payload)

            # Reads format/dimensions from the header only, rejecting an
            # over-cap pixel count before any pixel data decodes — a
            # decompression-bomb upload is never expanded.
            problems = illustrations.validate_illustration_file(raw_tmp_path)
            if problems:
                for problem in problems:
                    print("illustration replace rejected for %r: %s" % (key, problem))
                return self.redirect(
                    "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

            with Image.open(raw_tmp_path) as img:
                rgba = img.convert("RGBA")
                buffer = io.BytesIO()
                rgba.save(buffer, format="PNG")

            override_path = illustrations.override_path_for_key(key, state_dir)
            atomic_io.atomic_write(override_path, buffer.getvalue())
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACED))
        except Exception:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))
        finally:
            if raw_tmp_path is not None:
                try:
                    os.unlink(raw_tmp_path)
                except OSError:
                    pass

    def _handle_manual_resolve_post(self):
        """POST /airlines/resolve — Step A of the two-step resolve flow.
        `prefix` is re-validated against the live unresolved-callsign
        registry, never trusted from the hidden form field; a stale
        prefix writes nothing. The illustration key on success is
        recomputed server-side from the just-persisted name, never from
        the form value. No CSRF token: relies on SameSite=Strict, like
        every other state-changing route.
        """
        form = self.read_form()
        state_dir = self.args.state_dir

        row = unresolved_row_for_prefix(state_dir, form.get("prefix"))
        if row is None:
            return self.redirect(
                "%s?flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_PREFIX_STALE)))
        prefix = row[0]

        result = manual_resolutions.add_entry(state_dir, prefix, form.get("airline_name"))

        if result == manual_resolutions.ADD_OK:
            registry = manual_resolutions.load_manual_resolutions(state_dir)
            entry = registry.get(prefix) or {}
            key = manual_resolutions.illustration_key_for_name(entry.get("airline_name"))
            if key and illustrations.resolved_illustration_path(key, state_dir) is not None:
                return self.redirect(
                    "%s?flash=%s"
                    % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_RESOLVED)))
            return self.redirect(
                "%s?resolve=%s&flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(prefix, safe=""),
                   quote(FLASH_KEY_MANUAL_RESOLVED)))

        if result == manual_resolutions.ADD_REJECTED_PREFIX:
            flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
        elif result == manual_resolutions.ADD_REJECTED_NAME_EMPTY:
            # add_entry() collapses "empty" and "supplied but unusable"
            # onto one result code; distinguish them here by re-reading
            # the same raw posted value, never re-deriving the regex.
            raw_name = form.get("airline_name")
            if isinstance(raw_name, str) and raw_name.strip():
                flash_key = FLASH_KEY_MANUAL_NAME_UNUSABLE
            else:
                flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
        elif result == manual_resolutions.ADD_REJECTED_NAME_TOO_LONG:
            flash_key = FLASH_KEY_MANUAL_NAME_TOO_LONG
        elif result == manual_resolutions.ADD_REJECTED_NAME_RESERVED:
            flash_key = FLASH_KEY_MANUAL_NAME_RESERVED
        elif result == manual_resolutions.ADD_REJECTED_FULL:
            flash_key = FLASH_KEY_MANUAL_REGISTRY_FULL
        elif result == manual_resolutions.ADD_FAILED:
            flash_key = FLASH_KEY_MANUAL_SAVE_FAILED
        else:
            # An unrecognised result must still speak, never fall through
            # to no flash at all.
            flash_key = FLASH_KEY_MANUAL_SAVE_FAILED
        return self.redirect(
            "%s?resolve=%s&flash=%s"
            % (airlines_page.AIRLINES_ROUTE, quote(prefix, safe=""), quote(flash_key)))

    def _rename_redirect(self, flash_key, sheet_key=None):
        """Back to /airlines with `flash_key`; a refusal reopens the sheet."""
        query = "flash=%s" % quote(flash_key)
        if sheet_key:
            query = "%s=%s&%s" % (airline_sheet.SHEET_QUERY_PARAM, quote(sheet_key, safe=""), query)
        return self.redirect("%s?%s" % (airlines_page.AIRLINES_ROUTE, query))

    def _handle_airline_rename_post(self):
        """POST /airlines/rename — set the owner's name for a built-in
        airline. `airline` is the built-in name and is re-validated against
        the built-in prefix table, never trusted: the prefixes the name
        applies to come from there. A name equal to the built-in one is a
        reset. The new name applies to flights stored from now on; history
        rows are untouched. No CSRF token: SameSite=Strict, like every
        other state-changing route.
        """
        form = self.read_form()
        state_dir = self.args.state_dir
        built_in = form.get("airline")
        prefixes = enrich.static_prefixes_for_name(built_in)
        if not prefixes:
            return self._rename_redirect(FLASH_KEY_RENAME_STALE)
        overrides = name_overrides.load_name_overrides(state_dir)
        sheet = airline_sheet.card_sheet(built_in, overrides)
        sheet_key = illustrations.normalise_airline_key(sheet["name"])
        raw_name = form.get("airline_name")
        name, rejection = manual_resolutions.check_name(raw_name)
        if rejection is None and name == built_in:
            return self._reset_airline_name(state_dir, prefixes, sheet_key)
        result = name_overrides.set_names(
            state_dir, prefixes, raw_name, own_builtin_name=built_in) if rejection is None else rejection
        if result == name_overrides.SET_OK:
            _carry_artwork_to_new_name(
                state_dir, sheet["name"], name, airline_sheet.artwork_shapes(built_in))
            return self._rename_redirect(FLASH_KEY_RENAMED)
        if result == manual_resolutions.ADD_REJECTED_NAME_EMPTY:
            flash_key = (
                FLASH_KEY_MANUAL_NAME_UNUSABLE if isinstance(raw_name, str) and raw_name.strip()
                else FLASH_KEY_MANUAL_NAME_EMPTY)
        else:
            flash_key = _RENAME_FLASH_BY_RESULT.get(result, FLASH_KEY_RENAME_SAVE_FAILED)
        return self._rename_redirect(flash_key, sheet_key)

    def _handle_airline_rename_reset_post(self):
        """POST /airlines/rename/reset — drop the owner's name for a
        built-in airline so new flights use SkyPane's name again."""
        form = self.read_form()
        prefixes = enrich.static_prefixes_for_name(form.get("airline"))
        if not prefixes:
            return self._rename_redirect(FLASH_KEY_RENAME_STALE)
        return self._reset_airline_name(self.args.state_dir, prefixes, None)

    def _reset_airline_name(self, state_dir, prefixes, sheet_key):
        if name_overrides.clear_names(state_dir, prefixes):
            return self._rename_redirect(FLASH_KEY_RENAME_RESET)
        return self._rename_redirect(FLASH_KEY_RENAME_SAVE_FAILED, sheet_key)

    def _handle_manual_resolution_delete(self, key):
        """POST /airlines/manual-resolutions/{prefix}/delete. `key` is
        normalised and used only as a dict key into
        `manual_resolutions.json`, never joined into a filesystem path.
        Deleting an already-absent prefix is success, not an error
        (idempotent double-submission tolerance); only a genuine write
        failure gets a failure flash.
        """
        prefix = manual_resolutions.normalise_prefix(key)
        if prefix is None:
            return self.send_html(404, self._not_found_page())

        state_dir = self.args.state_dir
        existed = prefix in manual_resolutions.load_manual_resolutions(state_dir)
        deleted = manual_resolutions.delete_entry(state_dir, prefix)
        if not deleted and existed:
            return self.redirect(
                "%s?flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_DELETE_FAILED)))
        return self.redirect(airlines_page.AIRLINES_ROUTE)

    def _handle_rule_add_post(self):
        """POST /settings/rules/add: the colour-rules editor's immediate
        add route, an action outside SETTINGS_ROUTE. `colour_rules.add_rule()`
        is the single validation authority; this handler validates
        nothing itself and maps every result to a flash key with an
        explicit branch, so an unrecognised result can never fall
        through silently. No CSRF token, like every state-changing route.
        """
        form = self.read_form()
        state_dir = self.args.state_dir

        submitted_kind = form.get("rule_kind")
        submitted_key = form.get("rule_key")
        submitted_theme_id = form.get("rule_theme_id")

        result = colour_rules.add_rule(
            state_dir, submitted_kind, submitted_key, submitted_theme_id)

        if result == colour_rules.ADD_OK_NEW:
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_RULE_ADDED)))
        if result == colour_rules.ADD_OK_REPLACED:
            # Both segments are already known-valid at this point (that is
            # exactly why add_rule() returned ADD_OK_REPLACED rather than
            # a rejection) — re-derived here, never trusted from the raw
            # form value (validate-then-echo).
            normalised_kind = colour_rules.normalise_rule_kind(submitted_kind)
            normalised_value = colour_rules.normalise_rule_value(
                normalised_kind, submitted_key)
            return self.redirect(
                "%s?flash=%s&rule=%s"
                % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_RULE_REPLACED),
                   quote(normalised_value, safe="")))
        if result == colour_rules.ADD_REJECTED_KEY:
            flash_key = FLASH_KEY_RULE_KEY_INVALID
        elif result == colour_rules.ADD_REJECTED_FULL:
            flash_key = FLASH_KEY_RULE_REGISTRY_FULL
        else:
            # ADD_REJECTED_KIND, ADD_REJECTED_THEME, ADD_FAILED, and any
            # unrecognised result all reuse the generic save-failed key —
            # a result must never fall through to no flash at all.
            flash_key = FLASH_KEY_RULE_SAVE_FAILED
        return self.redirect("%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(flash_key)))

    def _handle_rule_delete(self, kind, value):
        """POST /settings/rules/{kind}/{value}/delete. `kind` and
        `value` are re-normalised before any registry lookup — an
        unrecognised kind or malformed value 404s without touching the
        registry. Deleting an already-absent pair is success, not an
        error (idempotent double-submission tolerance).
        """
        normalised_kind = colour_rules.normalise_rule_kind(kind)
        if normalised_kind is None:
            return self.send_html(404, self._not_found_page())
        normalised_value = colour_rules.normalise_rule_value(normalised_kind, value)
        if normalised_value is None:
            return self.send_html(404, self._not_found_page())

        state_dir = self.args.state_dir
        registry = colour_rules.load_colour_rules(state_dir)
        existed = normalised_value in registry.get(normalised_kind, {})
        deleted = colour_rules.delete_rule(state_dir, normalised_kind, normalised_value)
        if deleted:
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_RULE_DELETED)))
        if existed:
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_RULE_DELETE_FAILED)))
        return self.redirect(layout.DISPLAY_ROUTE)

    def _handle_calendar_disconnect_post(self):
        """POST /settings/calendar/disconnect. Two-step confirmation,
        server-side: a bare or non-matching confirm value renders the
        confirm page at 200 without touching anything — the client-side
        `confirm()` dialog is a misclick guard only, never the security
        control. Only an exact confirm match proceeds to clear the URL.
        """
        form = self.read_form()
        confirm = form.get(config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD)
        if confirm != config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE:
            ctx = self.page_context()
            body = config_page.calendar_disconnect_confirm_page(ctx)
            return self.send_html(200, self._page_shell_for(layout.DISPLAY_ROUTE, body, ctx))
        state_dir = self.args.state_dir
        if calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
        return self.redirect(
            "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))

    def _handle_calendar_connect_post(self):
        """POST /settings/calendar/connect: the Calendar card's own
        dedicated route — never the scoped settings handler, since a
        scoped POST carrying only `calendar_url` would read every
        absent checkbox on Display as an explicit OFF. Writes the URL,
        then syncs under `_POLL_LOCK` (process-local; see
        `companion/app.py`'s `_handle_settings_post()` for the
        cross-process lock).
        """
        form = self.read_form()
        signal = config_page.submitted_calendar_signal(form)
        if signal in (
                config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD,
                config_page.CALENDAR_URL_SIGNAL_INVALID,
                config_page.CALENDAR_URL_SIGNAL_CLEAR):
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_CONNECT_INVALID)))
        state_dir = self.args.state_dir
        stripped_url = (form.get("calendar_url") or "").strip()
        if not calendar_rules.save_calendar_url(state_dir, stripped_url):
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))
        if not _POLL_LOCK.acquire(blocking=False):
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_DEFERRED)))
        try:
            result_code, _registry = calendar_rules.refresh_calendar_registry(
                state_dir, poll_cycle.now_s(), min_interval_s=0)
        finally:
            _POLL_LOCK.release()
        if result_code == calendar_rules.FETCH_OK:
            return self.redirect(
                "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_CONNECT_OK)))
        return self.redirect(
            "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))
