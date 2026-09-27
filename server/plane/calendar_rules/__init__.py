#!/usr/bin/env python3
"""Calendar-sourced theme input: parses an operator's iCal feed into a
bounded list of match candidates for `match_calendar_theme()`.

A package, not a single module — `ics.py` (the RFC 5545 subset parser),
`registry.py` (the on-disk registry/secret file and its throttle/window
machinery) and `match.py` (comparing a detected flight against the
loaded registry) each own one slice; this `__init__.py` keeps the
orchestration (`default_calendar_transport`, `fetch_ics`,
`refresh_calendar_registry` — the once-per-cycle entry point
`poll_loop.py` calls) and re-exports every public and test-visible name
from the three submodules, so `import server.plane.calendar_rules` still
behaves exactly like the single module it replaces. Named `calendar_
rules`, never `calendar` — a package called `calendar` would shadow the
stdlib module of that name whenever a `server/plane/*.py` script runs
directly.

Leaf package: stdlib + `requests` + `server.device_config` only (plus
`server.net.safe_fetch`, the shared SSRF gate). Never import
`colour_rules`, `enrich`, `detect`, `illustrations`, `manual_resolutions`
or `render` — `poll_loop.py` calls this package before `colour_rules`,
so a back-import would create an import cycle. Submodules never import
this `__init__` (no cycles); `registry` and `match` both import `ics`,
`match` also imports `registry`.

The registry (`{state_dir}/calendar_rules.json`) lives outside the
git-tracked tree so it survives a redeploy. Persisted entries carry only
five keys (airline, origin, destination, start, end) — this data is a
named person's work schedule, so nothing else is retained.
"""
import os  # noqa: F401 - re-exported so `cr.os` keeps reaching registry.py's real os calls
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

from server import http_fetch
from server.net import safe_fetch

from .ics import (  # noqa: F401
    CALENDAR_MAX_RAW_EXAMINED,
    CATEGORY_FLIGHT,
    STATUS_CANCELLED,
    _AIRLINE_IATA_RE,
    _AIRPORT_IATA_RE,
    _ICAL_UTC_RE,
    _SUMMARY_ROUTE_RE,
    _TRACKED_PROPERTIES,
    _build_entry,
    parse_ics_datetime,
    parse_ics_events,
    split_property,
    unfold_ics_lines,
)
from .registry import (  # noqa: F401
    CALENDAR_FETCH_INTERVAL_S,
    CALENDAR_MAX_ENTRIES,
    CALENDAR_REGISTRY_KEYS,
    CALENDAR_REGISTRY_LOCK_FILENAME,
    CALENDAR_REGISTRY_LOCK_TIMEOUT_S,
    CALENDAR_RULES_FILENAME,
    CALENDAR_SECRET_FILENAME,
    CALENDAR_WINDOW_FORWARD_S,
    CLEAR_CALENDAR_URL,
    FETCH_FAILED,
    FETCH_OK,
    FETCH_REJECTED_URL,
    FETCH_SKIPPED_THROTTLED,
    FETCH_SKIPPED_UNCONFIGURED,
    FETCH_SUPERSEDED,
    _WRITE_LOCK,
    _calendar_registry_lock,
    _calendar_registry_lock_path,
    _calendar_secret_mode_is_safe,
    _normalise_calendar_entry,
    _normalise_calendar_url,
    _rebuild_capped_entries,
    _resolve_retention_now,
    _window_filtered_entries,
    calendar_fetch_is_due,
    calendar_is_configured,
    calendar_rules_path,
    calendar_secret_mode_is_unsafe,
    calendar_secret_path,
    configured_calendar_url,
    load_calendar_registry,
    save_calendar_url,
    select_window_entries,
    write_calendar_registry,
)
from .match import (  # noqa: F401
    ARRIVING_STATE,
    CALENDAR_MATCH_TOLERANCE_S,
    DEPARTING_STATE,
    _airline_iata_from_route,
    _entry_far_end_iata,
    _far_end_iata,
    _reference_time,
    match_calendar_theme,
)

# --- SSRF gate aliases (Task 1 of this plan) --------------------------------
#
# Identity, not copies: server.net.safe_fetch owns the one SSRF gate
# shared with notify.py. Kept under this package's historical names since
# every existing caller/test here already reads them off `calendar_rules`.
USER_AGENT = safe_fetch.USER_AGENT
_address_is_public = safe_fetch._address_is_public
_host_is_safe = safe_fetch.host_is_safe
_url_is_safe = safe_fetch.url_is_safe

# --- Bounded, SSRF-hardened fetch --------------------------------------------
#
# This project's first outbound request to an operator-chosen host, and
# its first runtime secret outside companion/auth.py. Four independent
# bounds apply together: the resolved address must be public on every
# redirect hop (not only the configured URL), the response body is
# capped while streamed, the request has a hard timeout, and redirects
# are bounded. Exception logging here deliberately logs only the
# exception type, never the exception object — several requests
# exceptions embed the request URL, which carries the calendar's access
# token, in their default string form.

# Per-request (connect/read) timeout, clamped further per hop to the
# time left under CALENDAR_FETCH_DEADLINE_S below - generous for a small
# iCal feed, short enough that a hung upstream never meaningfully delays
# the 30s poll cycle.
CALENDAR_FETCH_TIMEOUT_S = 5.0

# Total wall-clock deadline across every hop of one fetch_ics() call
# (the original request plus every redirect it follows) - CALENDAR_FETCH_
# TIMEOUT_S alone only bounds a single connect/read, so a feed trickling
# one byte at a time across several hops could otherwise run far longer
# than that. Worst case per call is this plus one more read timeout: the
# chunk in flight when the deadline check fires can still take up to
# CALENDAR_FETCH_TIMEOUT_S to arrive before the loop notices.
CALENDAR_FETCH_DEADLINE_S = 10.0

# Hard response-size cap, enforced by streaming rather than trusting a
# response's own declared-length header, which a hostile or misconfigured
# server can omit, understate or exceed. 2 MiB comfortably exceeds any
# plausible multi-month roster export.
CALENDAR_MAX_RESPONSE_BYTES = 2 * 1024 * 1024

# Bounded redirect-following; each hop is re-validated against the same
# SSRF gate as the original URL, never trusted transitively.
CALENDAR_MAX_REDIRECTS = 5


def default_calendar_transport(url, timeout):
    """GET `url` with this package's `USER_AGENT` through `http_fetch.
    pinned_request()`, returning the response object unread.

    `pinned_request()` resolves the hostname once, refuses the whole
    host unless every resolved address is public, and connects only to
    an address it already checked — closing the gap where a plain HTTP
    client call would re-resolve the hostname again at connect time (DNS
    rebinding: the address `_url_is_safe()` checked and the address the
    socket actually reaches could otherwise differ). It
    never follows a redirect itself, so `fetch_ics()` can re-validate
    each `Location` target through `_url_is_safe()` before following it
    — a hook a self-following client has no equivalent for. Bounded by
    `CALENDAR_FETCH_DEADLINE_S` (the total deadline across every hop —
    see `fetch_ics()`), on top of this call's own `timeout`. The
    injectable `transport` parameter lets tests replace this with a
    hermetic fake.
    """
    return http_fetch.pinned_request(
        "GET",
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        deadline_s=CALENDAR_FETCH_DEADLINE_S,
    )


def fetch_ics(url, timeout=None, transport=None, max_redirects=None, max_bytes=None,
              deadline_s=None, clock=None):
    """Fetch `url` and return its decoded body text, or `None` on any
    refusal or failure. Never raises.

    Five independent bounds, all defaulting from this package's
    constants: `_url_is_safe()` re-checked on every redirect hop; one
    total wall-clock `deadline_s` across every hop combined (not just a
    per-request `timeout`) — checked before each hop and after every
    chunk, so a feed trickling one byte at a time across several
    redirects cannot run far longer than the deadline; the response is
    read in chunks with a running byte count, aborting past `max_bytes`
    rather than trusting a declared length; a per-hop `timeout`, clamped
    to `min(timeout, time left under the deadline)`; and at most
    `max_redirects` hops. Redirects are never followed automatically
    (`default_calendar_transport()`'s underlying `pinned_request()` never
    follows one) — each `Location` target is re-validated before being
    requested.

    The only paths that log are the transport-exception and deadline-
    exceeded catches, which log `type(exc).__name__` only, never the
    exception object — several `requests.exceptions.*` subclasses embed
    the request URL, which carries the calendar's access token, in their
    default string form.

    `url` is normalised once, before the redirect loop, so a hand-edited
    secret file (bypassing `save_calendar_url()`'s own normalisation)
    still resolves a `webcal://` scheme. Redirect targets are not
    separately normalised — a `Location` header is a live HTTP response,
    never a calendar-client convention.
    """
    if timeout is None:
        timeout = CALENDAR_FETCH_TIMEOUT_S
    if max_redirects is None:
        max_redirects = CALENDAR_MAX_REDIRECTS
    if max_bytes is None:
        max_bytes = CALENDAR_MAX_RESPONSE_BYTES
    if deadline_s is None:
        deadline_s = CALENDAR_FETCH_DEADLINE_S
    if clock is None:
        clock = time.monotonic
    if transport is None:
        transport = default_calendar_transport

    deadline = clock() + deadline_s
    current_url = _normalise_calendar_url(url)
    for _ in range(max_redirects + 1):
        if not safe_fetch.url_is_safe(current_url):
            return None

        try:
            time_left = deadline - clock()
            if time_left <= 0:
                raise http_fetch.DeadlineExceeded(
                    "fetch_ics: total deadline exceeded before a hop")
            response = transport(current_url, min(timeout, time_left))
        except Exception as exc:
            # Deliberately broad: a caller-supplied fake transport or a
            # future requests version is not guaranteed to only raise
            # RequestException, and this fetch must never abort a poll
            # cycle. Logs the exception type only, never `exc` itself or
            # the URL — see this function's own docstring.
            print(
                "calendar_rules: fetch_ics() transport call failed: %s"
                % type(exc).__name__,
                file=sys.stderr,
            )
            return None

        if getattr(response, "is_redirect", False):
            location = response.headers.get("Location")
            response.close()
            if not location:
                return None
            current_url = urljoin(current_url, location)
            continue

        if response.status_code != 200:
            response.close()
            return None

        chunks = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=8192):
                total += len(chunk)
                if total > max_bytes:
                    response.close()
                    return None
                chunks.append(chunk)
                if clock() > deadline:
                    raise http_fetch.DeadlineExceeded(
                        "fetch_ics: total deadline exceeded while reading the response")
        except Exception as exc:
            # Deliberately broad - see the transport-call catch above.
            print(
                "calendar_rules: fetch_ics() reading the response body failed: %s"
                % type(exc).__name__,
                file=sys.stderr,
            )
            response.close()
            return None
        response.close()
        return b"".join(chunks).decode("utf-8", errors="replace")

    # Too many redirect hops - give up rather than loop.
    return None


# --- Once-per-cycle throttle, fetch, parse, window and persist step ---------
#
# The single function poll_loop.py calls once per cycle. Performs no
# network I/O when the feature is unconfigured or the throttle has not
# elapsed, since the fetch must never delay a render.


def refresh_calendar_registry(state_dir, now, transport=None, min_interval_s=None):
    """Throttle, fetch, parse, window and persist the calendar registry
    for this poll cycle. Returns `(result_code, registry)`, always a
    usable dict. Never raises.

    No transport call when unconfigured, or when the throttle has not
    elapsed (the dominant case — the poll timer fires every 30s against a
    much longer interval). `min_interval_s=0` lets the Settings save
    bypass the throttle for one attempt, so connecting a calendar is not
    silently delayed up to half an hour.

    Three steps, each under its own brief lock acquisition — the network
    fetch itself runs with NO lock held, so a companion save or disconnect
    never waits behind it: (1) under the lock, load the registry, decide
    unconfigured/throttled/due, and — only when due — record the attempt
    (`last_attempt_at = now`) before releasing; (2) without the lock, fetch
    and parse; (3) under the lock again, reload the registry and re-read
    the configured URL. If it no longer matches the URL this attempt
    fetched (a companion save or disconnect landed while the fetch was in
    flight), the stale result is discarded entirely — nothing is written,
    and `FETCH_SUPERSEDED` is returned with the reloaded (newer) registry;
    the newer URL always wins over this cycle's own fetch. Otherwise a
    failed fetch re-persists the previous entries unchanged (the attempt
    was already recorded in step 1), and a successful one persists the
    windowed parse with `last_synced_at` derived from `now` — the
    injected clock, never the wall clock.

    `last_attempt_at` updates on every attempt that runs; `last_synced_at`
    only after a body was fetched, parsed, and found to still match the
    configured URL. An empty result on genuine success is a legitimate
    empty window, distinguishable from a broken feed only by
    `last_synced_at` having moved.

    Prints nothing on the throttled/unconfigured paths (near-every-cycle
    volume); at most one line, never the URL, once step 3 has a verdict.
    The same `now` threads through every registry call here, so a
    re-persist stays correctly windowed and byte-equal to disk.
    """
    # Wrapped so nothing escapes: every callee is already never-raising,
    # but this function must never gain a new failure mode from a future
    # change to a callee. Also absorbs TimeoutError from
    # _calendar_registry_lock() below — a stuck holder degrades this
    # cycle to FETCH_FAILED rather than wedging the poll loop.
    try:
        with _calendar_registry_lock(state_dir):
            registry = load_calendar_registry(state_dir, now)

            url = configured_calendar_url(state_dir)
            if url is None:
                # Not a failing feed - a feature that is simply off.
                # Leaving last_attempt_at untouched means the first fetch
                # after configuring runs immediately.
                return FETCH_SKIPPED_UNCONFIGURED, registry

            if not calendar_fetch_is_due(registry["last_attempt_at"], now, min_interval_s):
                return FETCH_SKIPPED_THROTTLED, registry

            # Record the attempt now, before the lock is released and the
            # fetch begins: a second refresh starting while this one's
            # fetch is still in flight must see the throttle correctly
            # (the normal 30s-cycle-against-30-minute-interval case),
            # rather than racing this same fetch.
            write_calendar_registry(
                state_dir, registry["entries"], now, registry["last_synced_at"], now=now)

        # Outside the lock: the network fetch never blocks a companion
        # save or disconnect (see this function's own docstring).
        body = fetch_ics(url, transport=transport)
        windowed = select_window_entries(parse_ics_events(body), now) if body is not None else None

        with _calendar_registry_lock(state_dir):
            reloaded = load_calendar_registry(state_dir, now)
            current_url = configured_calendar_url(state_dir)

            if current_url != url:
                # The configured URL changed or was cleared while this
                # fetch was in flight - the newer URL always wins, so
                # this cycle's own result (success or failure) is
                # discarded rather than persisted.
                print(
                    "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                    % (FETCH_SUPERSEDED, len(reloaded["entries"])),
                    file=sys.stderr,
                )
                return FETCH_SUPERSEDED, reloaded

            if windowed is None:
                # A transient blip must not erase an otherwise-valid
                # window before its natural expiry - the attempt was
                # already recorded above, nothing else changes.
                print(
                    "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                    % (FETCH_FAILED, len(reloaded["entries"])),
                    file=sys.stderr,
                )
                return FETCH_FAILED, reloaded

            # An empty windowed result here is still success -
            # distinguishable from a broken feed only by last_synced_at
            # having moved.
            last_synced_at = datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")
            wrote_ok = write_calendar_registry(state_dir, windowed, now, last_synced_at, now=now)
            result_registry = {
                "entries": windowed,
                "last_attempt_at": now,
                "last_synced_at": last_synced_at,
            }
            result_code = FETCH_OK if wrote_ok else FETCH_FAILED
            print(
                "calendar_rules: refresh_calendar_registry() result=%s entries=%d"
                % (result_code, len(result_registry["entries"])),
                file=sys.stderr,
            )
            return result_code, result_registry
    except Exception:
        # Defence in depth only - see the comment above. Fall back to
        # whatever is durably on disk rather than propagate.
        return FETCH_FAILED, load_calendar_registry(state_dir, now)
