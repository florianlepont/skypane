# Phase 16: Calendar-linked flight highlighting — Research

**Researched:** 2026-09-07
**Domain:** Hand-rolled RFC 5545 (iCalendar) parsing under a stdlib-only constraint; bounded/hardened outbound HTTP from a 30-second oneshot; first-runtime-secret handling; extending an already-shipped resolver seam (Phase 15) with a second, higher-precedence rule source.
**Confidence:** HIGH on architecture/integration points and security posture (all directly verified against shipped code at HEAD); MEDIUM on the iCal parsing minimum-subset (verified against RFC 5545 text and the codebase's own measured-findings sample description, not against the actual unredacted export file, which is deliberately not available in this session); MEDIUM on the airline-matching mechanism (a real gap the measured findings did not close — flagged below as the single most important open question).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** A separate calendar registry, consulted at the same seam as the manual rules — never written into Phase 15's rule store (`server/plane/colour_rules.py`'s `colour_rules.json`). Rejected: writing real rules into Phase 15's registry; rejected: no storage, resolving straight off the cached feed.
- **D-02:** The calendar wins over a manual rule — including over a hand-typed exact-callsign rule, the narrowest thing an operator can write. Resolver order becomes: **calendar match → manual rule (callsign > hex > prefix) → arrivals override → base theme.**
- **D-03:** The registry holds a short rolling window — today plus the next 24–48h — rewritten whole on every fetch. Exact width is Claude's discretion. Rejected: mirroring the whole feed indefinitely (privacy).
- **D-04 (derived):** Matching is on **airline + the far-end airport + a time window**, never the flight number. The far end is the destination for a departure, the origin for an arrival. Matching runs **after** `enrich.resolve_route()`, never on the raw callsign.

### Claude's Discretion

- Time-window width and ambiguity resolution (recommendation given: generous enough for ordinary delay; on a same-route collision, take the closest match in time, never colour two candidates).
- Configuration surface specifics: env var name, whether to add a connection test or an upcoming-flights preview (UI-SPEC already resolved this: **no preview, no test button** — see Configured/Not Configured State section of 16-UI-SPEC.md).
- Fetch cadence and failure behaviour: throttled fetch inside the existing 30s oneshot, persisted to `state_dir`, never delaying a render; silent degrade-to-no-matches on a long-unreachable feed; whether the companion surfaces staleness is plan-time (UI-SPEC already resolved this too: a plain last-synced relative timestamp, no staleness banner).
- Field/file names, the record shape, the parser's module placement, all copy (UI-SPEC already locks copy), and test strategy.

### Deferred Ideas (OUT OF SCOPE)

- A calendar-driven view (the frame announcing a flight independent of detection).
- Multiple calendars, or per-calendar themes — one feed, one theme.
- A visible trace on History/Health that a calendar match fired.
- Registration (tail-number) matching.

</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md REQ-IDs apply — unmapped phase promoted from a seed, matching Phases 10–15's precedent (confirmed: `REQUIREMENTS.md` has no CAL-*/16-* entries). Traceability runs against `16-CONTEXT.md`'s D-01..D-04 instead:

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Separate calendar registry, never written into `colour_rules.json` | Research Target 5 — concrete module boundary and file shape recommended below |
| D-02 | Calendar beats manual rule, beats arrivals override | Research Target 5 — resolver call-order and signature-extension recommendation |
| D-03 | Short rolling window, rewritten whole on every fetch | Research Target 2 & 6 — throttle/persist pattern and expiry-by-rewrite mechanics |
| D-04 | Match on airline + far-end airport + time window, after `resolve_route()` | Research Target 5 — exact call-site placement, plus the airline-matching gap flagged in Open Questions |

</phase_requirements>

## Summary

This phase's entire risk surface is server-side; the UI is fully settled by `16-UI-SPEC.md`. Three things make this phase harder than an ordinary "add a rule source" change: (1) Python has no iCal parser in the standard library and this project forbids new dependencies, so a correct-enough hand-rolled RFC 5545 subset must be built and proven against a *redacted* fixture rather than the real (uncommitted) export; (2) the calendar URL is the project's first runtime-held secret and its fetch is the project's first outbound request to an operator-supplied, untrusted host — both need hardening this codebase has never needed before; (3) the match key the roadmap specifies (airline + far-end airport + time window) requires an airline-identity translation this codebase does not yet have, because the calendar encodes airline identity as a 2-letter IATA prefix (`TO`) while every existing airline-identity table in `server/plane/enrich.py` is keyed on the 3-letter ICAO callsign prefix (`TVF`). This translation gap is real and unresolved by the measured findings — it is this research's single most load-bearing open question.

Architecturally, the phase is small: a new leaf module (recommended `server/plane/calendar_rules.py`) owns fetch-throttling, parsing, the rolling-window registry file, and a pure match function; `server/device_config.py` gains one new optional key (the operator's chosen calendar theme, mirroring `theme_arriving`'s exact contract); `server/poll_loop.py` gains one throttled fetch call near its existing per-cycle priming calls and one match-lookup passed into `colour_rules.resolve_effective_theme_id()` at both of its two existing call sites; `colour_rules.py` gains one new, optional, backward-compatible keyword parameter (no new import, so its leaf-import contract survives unmodified). Nothing touches `render.py`. The outbound fetch needs IP-literal validation after DNS resolution (not just hostname/scheme checks) to close the DNS-rebinding gap that a naive SSRF filter leaves open, plus a hard response-size cap enforced by streaming rather than trusting `Content-Length`.

**Primary recommendation:** Build the calendar mechanism as one new leaf module that never imports and is never imported by `colour_rules.py`; thread its match result into `colour_rules.resolve_effective_theme_id()` as a new optional keyword argument computed identically at both of `poll_loop.py`'s existing flight-render call sites — this is the only design that satisfies D-01 (separate store), D-02 (precedence), and Phase 15's both-branches invariant without touching a single line of already-verified Phase 15 logic beyond one signature extension.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| iCal fetch (HTTPS GET, bounded/hardened) | API/Backend (`server/plane/calendar_rules.py`, invoked from `poll_loop.py`'s oneshot) | — | This is server-side outbound egress from the poll pipeline, the same tier `enrich.py`/`detect.py` already do bounded HTTP from |
| iCal parsing (unfold, parse properties, filter) | API/Backend (same new module) | — | Pure computation, no I/O beyond the fetch above; must stay a leaf per the codebase's layering discipline |
| Rolling-window registry persistence | Database/Storage (`state_dir` JSON file) | — | Same tier as `colour_rules.json`/`manual_resolutions.json`/`device_config.json` — flat JSON files under `state_dir`, not a database engine |
| Fetch throttle state | Database/Storage (same file or a sibling in `state_dir`) | — | Mirrors `poll_state.json`'s existing timestamp-gated fields (`last_advance_at`) |
| Calendar-vs-manual-rule precedence resolution | API/Backend (`server/plane/colour_rules.py`'s `resolve_effective_theme_id()`) | — | This is Phase 15's existing resolution seam; the phase's entire job is to feed it a new input, not duplicate it |
| Secret storage (`SKYPANE_CALENDAR_ICS_URL`) | API/Backend (process environment via `skypane.env` / systemd `EnvironmentFile=`) | — | Same tier and same mechanism as `SKYPANE_COMPANION_PASSWORD` — never a database row, never a JSON file, never a browser-visible value |
| "Configured / not configured" status display | Frontend Server / Companion web app (`companion/pages/config_page.py`) | — | Reads the env var's *presence*, never its value, mirroring `companion/app.py`'s `env_wake_interval_default()` |
| Theme-assignment `<select>` for calendar matches | Frontend Server / Companion web app | Database/Storage (`device_config.json`'s new key) | Settled by 16-UI-SPEC.md; the selected value is one more optional `device_config.json` key |

## Package Legitimacy Audit

**No new packages.** This phase adds zero entries to `server/requirements.txt` (currently `Pillow==12.3.0`, `requests==2.34.2` only — [VERIFIED: `server/requirements.txt`]). The iCal parser is hand-rolled stdlib Python (`re`, `datetime`, `json`, `os`, `threading` — the same import list `colour_rules.py` already declares); the outbound fetch reuses the already-vendored `requests` library exactly as `server/plane/enrich.py` and `server/plane/detect.py` already do. `CLAUDE.md`'s "no new dependencies" instruction and `16-UI-SPEC.md`'s explicit "stdlib-only Python HTTP app" framing both apply unchanged. The Package Legitimacy Gate protocol therefore has nothing to check — no `npm view`/`pip index versions` run was needed or performed.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(none)* | — | — | — | — | — | No packages installed by this phase |

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** none.

## Architecture Patterns

### System Architecture Diagram

```
                         operator (SSH)
                              |
                              v
                  skypane.env: SKYPANE_CALENDAR_ICS_URL
                    (systemd EnvironmentFile=, shared by
                     skypane-poll.service AND
                     skypane-companion.service)
                              |
             +----------------+-----------------+
             |                                   |
             v                                   v
   companion/app.py (long-running)      poll_loop.py run_once() (30s oneshot)
   reads env var PRESENCE only     -->  [1] throttle check (state_dir timestamp)
   -> "configured/not configured"        |  skip fetch if too recent
   status text, never the value          v
                                   [2] validate URL: https-only, resolve DNS,
                                        reject private/loopback/link-local IPs
                                        (both the URL host AND every redirect hop)
                                        |
                                        v
                                   [3] bounded GET: timeout=10s, stream=True,
                                        max N redirects re-validated per hop,
                                        abort at MAX_BYTES while streaming
                                        |
                                        v
                                   [4] hand-rolled RFC 5545 parser:
                                        unfold -> split BEGIN/END:VEVENT blocks
                                        -> filter CATEGORIES:FLT, drop CANCELLED
                                        -> parse SUMMARY "{num} {orig}-{dest}(+tz)"
                                        -> parse DTSTART/DTEND (UTC)
                                        |
                                        v
                                   [5] filter to rolling window (today .. +24-48h)
                                        -> write whole registry file
                                        (tmp-write + os.replace, mirrors
                                        colour_rules.py/manual_resolutions.py)
                                        |
                                        v
                              state_dir/calendar_rules.json
                              {entries: [...], last_attempt_at, last_synced_at}
                                        |
                                        v
                    [once per cycle, priming call, same spot as
                     colour_rules.set_colour_rules_state_dir()]
                                        |
                                        v
              current_flight settled  +  route = enrich.resolve_route(...)
                                        |
                                        v
              calendar_rules.match_calendar_theme(current_flight, route,
                                                    render_state, device_cfg)
                          (airline + far-end IATA + time window match,
                           closest-in-time tiebreak)
                                        |
                                        v         (returns calendar_theme_id or None)
              colour_rules.resolve_effective_theme_id(
                  render_state, current_flight, device_cfg,
                  calendar_theme_id=calendar_theme_id)   <-- D-02 checked FIRST
                                        |
                                        v
                          render.build_canvas(theme_id=effective_theme_id, ...)
                                        |
                                        v
                                  physical e-ink panel
```

### Recommended Project Structure

```
server/plane/
├── calendar_rules.py        # NEW — fetch/throttle, parse, registry file, match function (leaf)
├── colour_rules.py          # MODIFIED — resolve_effective_theme_id() gains one optional kwarg
├── manual_resolutions.py    # unchanged — prior art for the file contract, not imported
├── enrich.py                # unchanged — resolve_route() already gives origin_iata/destination_iata
server/
├── device_config.py         # MODIFIED — one new optional key (e.g. calendar_theme_id)
├── poll_loop.py             # MODIFIED — one throttled fetch call, one match-lookup call at each of the two existing colour_rules.resolve_effective_theme_id() call sites
server/test_calendar_rules.py         # NEW — mirrors test_colour_rules.py / test_manual_resolutions.py
server/plane/fixtures/                # NEW (or similar) — REDACTED CrewWebPlus-shaped .ics fixture
companion/pages/config_page.py        # MODIFIED — Calendar section per 16-UI-SPEC.md
companion/app.py                      # MODIFIED — env var presence check, theme <select> wiring
```

### Pattern 1: The bounded, never-raising fetch (copy `detect.py`'s per-provider try/except shape)

**What:** every existing outbound call in this codebase is a `requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)` wrapped in a narrow `except (requests.RequestException, ValueError)` that logs a one-line, non-sensitive message and degrades to "nothing this cycle" rather than raising out of `run_once()`.
**When to use:** for the calendar fetch, exactly. It must degrade to "the previous registry file stays as-is" (not to an empty registry — a transient network blip must not erase an otherwise-valid rolling window before its natural expiry).
**Example (verified against shipped code):**
```python
# server/plane/detect.py:404-417 — the pattern to copy
def query_provider(name, lat, lon, radius_nm, timeout=10.0):
    """... Raises on any failure ... caller is responsible for catching
    this per-provider so one aggregator being down never aborts a poll ..."""
    spec = PROVIDERS[name]
    url = spec["url_template"].format(lat=lat, lon=lon, dist=radius_nm)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    aircraft = data.get(spec["aircraft_key"]) or []
    return aircraft

# server/plane/detect.py:950-958 — the caller's catch shape
for i, name in enumerate(provider_names):
    ...
    try:
        aircraft = query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
    except (requests.RequestException, ValueError) as exc:
        print("detect: %s query failed: %s: %s" % (name, type(exc).__name__, exc), file=sys.stderr)
        failed.append(name)
        continue
```
The calendar fetch function should follow this exactly, with **one deliberate difference**: the exception log line must never include the URL (it embeds the secret token) — log only the exception type and a fixed description ("calendar fetch failed"), never `exc` interpolated with `%s` if `exc`'s string form could echo the request URL (some `requests.exceptions` subclasses do include the URL in their message — see Research Target 4 below for why this is a real, not theoretical, leak vector).

### Pattern 2: Throttle state as a `poll_state.json`-style timestamp, not a cron/thread

**What:** `poll_loop.py` has no long-running process of its own — `deploy/skypane-poll.timer` fires a fresh Python process every 30s (confirmed: `deploy/skypane-poll.service`/`deploy/skypane-poll.timer`, `Type=oneshot`, `OnUnitActiveSec=30s`). There is no in-memory scheduler to hold a "next fetch due" timer across cycles — throttle state must be durable, on disk, exactly like `poll_state.json`'s `last_advance_at` is.
**When to use:** the calendar module should store (at minimum) `last_attempt_at` (updated on every attempt, success or failure — this is what gates the throttle) separately from `last_synced_at` (updated only on a successful parse — this is what `16-UI-SPEC.md`'s `CALENDAR_STATUS_CONFIGURED_SYNCED` copy displays). Conflating the two would either hammer a broken feed every 30s forever (if throttle uses success-only) or hide a persistently-failing feed's staleness from the operator (if the UI shows attempt time instead of sync time).
**Example (the existing precedent to mirror):**
```python
# server/poll_loop.py:126, :179-199 — the injectable-clock, timestamp-gated pattern already in this file
def now_s():
    ...
def advance_is_due(last_advance_at, now, min_interval_s=None):
    if last_advance_at is None:
        return True
    elapsed = now - last_advance_at
    ...
```
A `calendar_fetch_is_due(last_attempt_at, now, min_interval_s=CALENDAR_FETCH_INTERVAL_S)` function of identical shape, called once near the top of `run_once()` beside the other three per-cycle priming calls (`illustrations.set_override_state_dir`, `manual_resolutions.set_manual_registry_state_dir`, `colour_rules.set_colour_rules_state_dir` — all at `server/poll_loop.py:737-749`), is the natural fourth entry in that list.

**Recommended throttle interval:** `[ASSUMED]` — not locked by CONTEXT.md. A crew roster is republished at most a few times a day; 15–30 minutes between fetch *attempts* comfortably tracks real-world roster update cadence while keeping the operator-supplied host from being hit every 30 seconds forever. This needs no more precision than a single module constant (e.g. `CALENDAR_FETCH_INTERVAL_S = 1800`), and should be named and commented the same way `MIN_SECONDS_BETWEEN_CALLS` is in `detect.py`.

### Pattern 3: `state_dir` file contract — copy `manual_resolutions.py` verbatim, not `colour_rules.py`

**What:** both existing `state_dir` registries share: never-raising load (bad JSON/missing file → empty shape, never an exception), per-field `normalise_*()` gates re-applied on every read (not just at write time), a hard entry cap, `tmp-write-then-os.replace()` with a pid+thread-id-qualified temp filename, and a module-level `threading.Lock()` wrapping the *entire* load-check-mutate-write sequence.
**When to use:** the calendar registry file needs the identical discipline, with two differences from both existing examples: (1) unlike `colour_rules.json`/`manual_resolutions.json`, this file is never written by an authenticated HTTP request — it is written exactly once per cycle by `poll_loop.py` itself (a single writer, not `ThreadingHTTPServer`'s multiple concurrent writers), so the `_WRITE_LOCK` is defence-in-depth rather than the load-bearing correctness property T-15-02 needed; (2) unlike both existing examples, this file's *entire content* is replaced on every successful fetch (D-03: "rewritten whole"), not merged/appended — closer to `render.py`'s cache-replacement style than to `add_rule()`'s single-entry mutation.
**Example (the exact idiom to copy — `server/plane/colour_rules.py:340-353`):**
```python
path = colour_rules_path(state_dir)
tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
try:
    os.makedirs(state_dir, exist_ok=True)
    with open(tmp, "w") as fh:
        json.dump(registry, fh, indent=1)
    os.replace(tmp, path)
except Exception:
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    return ADD_FAILED
```

### Pattern 4: The precedence extension — an optional keyword, not a new import

**What:** `colour_rules.py`'s own module docstring states an explicit, load-bearing leaf-import contract: *"This module ... must NEVER import `server.plane.enrich`, `server.plane.detect`, `server.plane.illustrations`, `server.plane.manual_resolutions`, or `server.plane.render` — `poll_loop.py` already imports all of those plus this module, and the reverse direction would make a real import cycle (D-13)."* A hypothetical `server/plane/calendar_rules.py` is not named in that list only because it doesn't exist yet — the same reasoning applies to it by construction (`poll_loop.py` needs to import both `calendar_rules` and `colour_rules`; `colour_rules` importing `calendar_rules` would create exactly the cycle the docstring warns against).
**Recommendation:** extend `resolve_effective_theme_id()`'s signature with one new, optional, keyword-only, defaulted-to-`None` parameter, checked *first* (D-02):
```python
# server/plane/colour_rules.py:466 — CURRENT signature (verified)
def resolve_effective_theme_id(state, flight, device_cfg):
    ...
    rule_theme = _rule_theme_from_cache(cache, RULE_KIND_CALLSIGN, callsign)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_HEX, hex_value)
    if rule_theme is None:
        rule_theme = _rule_theme_from_cache(cache, RULE_KIND_PREFIX, prefix)
    if rule_theme is not None and rule_theme in device_config.THEMES:
        return rule_theme
    ...

# RECOMMENDED new signature — additive, backward-compatible
def resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=None):
    """... Order: calendar match (D-02), then exact callsign rule, then hex
    rule, then prefix rule, then the arrivals override, then device_cfg["theme"].
    `calendar_theme_id` is computed by the CALLER (poll_loop.py, via
    calendar_rules.match_calendar_theme()) — this function does not import
    or know about the calendar module, preserving its leaf-import contract.
    """
    if isinstance(calendar_theme_id, str) and calendar_theme_id in device_config.THEMES:
        return calendar_theme_id
    # ... existing rule-lookup logic, unchanged ...
```
This is a **strictly additive** change: every existing call to `resolve_effective_theme_id(state, flight, device_cfg)` (both call sites plus every test in `server/test_colour_rules.py`) continues to work unmodified because the new parameter defaults to `None`, which the added `isinstance()` guard treats as "no calendar match" — identical to today's behaviour. `poll_loop.py`'s two call sites (`:1152` and `:1237`) each gain one extra computed argument, calling the new `calendar_rules.match_calendar_theme(...)` function with the same `current_flight`/`route`-or-`current_route` inputs each branch already has in scope — this is the same shape Phase 15 itself used to keep both branches in lockstep (T-15-10's proof).

**Rejected alternative:** writing calendar matches into `colour_rules.json` via `add_rule()`. Explicitly rejected by D-01 in `16-CONTEXT.md` — would make the store's writer plural (human + automaton), risking a colliding key silently replacing a manual rule, and would surface automatically-generated entries in the Phase 15 rules editor the operator did not create.

### Anti-Patterns to Avoid

- **Splitting the .ics text on bare `\n` without unfolding first.** RFC 5545 folds any content line over 75 octets by inserting `CRLF` followed by a single SPACE or HTAB continuation marker [CITED: https://icalendar.org/iCalendar-RFC-5545/3-1-content-lines.html, https://www.rfc-editor.org/rfc/inline-errata/rfc5545.html]. A naive per-line split treats a folded continuation as a brand-new, malformed "property" — for a long `SUMMARY`/`DESCRIPTION` this silently truncates or corrupts the exact field the parser depends on for the flight-number/route regex.
- **Reading `Content-Length` as a size guarantee.** A hostile or misconfigured server can omit it, lie about it, or stream chunked-encoded content past it — the response body must be capped while it is being read (`stream=True` + `iter_content()` + a running byte counter that aborts the connection), never trusted from a header alone.
- **Validating the URL's *hostname* against a private-range blocklist and stopping there.** This is vulnerable to DNS rebinding: the hostname can resolve to a public IP at validation time and a private one at connection time. The IP actually used for the TCP connection must be checked, not just the string in the URL.
- **Treating a `requests.exceptions.*` object's default string form as safe to log.** Several exception types embed the failing URL (which contains the secret token) in their `__str__()` — see Research Target 4 below.
- **Writing the calendar's parsed entries directly into `colour_rules.json`'s schema** (D-01 explicitly rejects this).
- **Calling `colour_rules.resolve_effective_theme_id()` at the top of `run_once()`, beside the priming calls.** The docstring at `server/poll_loop.py:759-772` explains exactly why this is wrong for the *existing* resolver (render_state/current_flight are not settled yet) — the same trap applies identically to computing the calendar match early: it must be computed at the same point the existing resolver call already is, once per branch, from the same settled inputs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|--------------|
| Detecting whether a candidate IP is in a private/loopback/link-local/reserved range | A hand-rolled CIDR-matching regex or manual octet comparison | Python stdlib `ipaddress.ip_address(ip_str).is_private` / `.is_loopback` / `.is_link_local` / `.is_reserved` / `.is_multicast` — covers both IPv4 and IPv6 in one call each [CITED: standard Python `ipaddress` module semantics; SSRF-mitigation pattern independently confirmed via web search, see Sources] |
| Resolving a hostname to the IP that will actually be connected to | Trusting `urllib.parse.urlparse(url).hostname` alone | `socket.getaddrinfo(hostname, port)` performed explicitly, with every returned address checked via `ipaddress` before the request is issued — this is what closes the DNS-rebinding gap a hostname-only check leaves open |
| Following redirects safely | `requests.get(url, allow_redirects=True)` (the default) | `requests.get(url, allow_redirects=False, ...)`, then a manual loop over at most N hops, re-validating each `Location` header target through the same scheme+IP-range gate before following it |

**Key insight:** this project has never before made an outbound request to an operator-supplied host — every existing `requests.get()` call in the codebase (`detect.py`'s aggregator queries, `enrich.py`'s adsbdb lookup) targets a fixed, developer-chosen URL template, so no SSRF-class validation exists anywhere in the codebase today to imitate [VERIFIED: `grep -rn "ipaddress\|is_private\|SSRF" server/ companion/` returns zero matches]. This phase must build that validation from scratch rather than adapt an existing pattern — the "Don't Hand-Roll" table above is about not hand-rolling the *IP-range logic itself* (use `ipaddress`), while still hand-rolling the *validation call site* (there is no library to delegate the whole SSRF gate to under the stdlib-only constraint, short of adding a third-party dependency this project's CLAUDE.md forbids).

## Common Pitfalls

### Pitfall 1: Naive line-split iCal parsing silently corrupts folded fields
**What goes wrong:** a parser that does `for line in text.split("\n"):` and treats each line as one property will, on any folded `SUMMARY`/`DESCRIPTION` line, either drop the continuation entirely or misparse it as a bogus new property (a line beginning with a single space or tab is a continuation, not a new `KEY:VALUE` pair). `16-CONTEXT.md`'s own research target explicitly flags that "the real export uses this" (folding), so this is not a hypothetical.
**Why it happens:** RFC 5545's line-folding rule is easy to miss because most short test fixtures never trigger it (lines under 75 octets never fold), so a parser that "works" against a hand-typed sample can still be wrong against the real export.
**How to avoid:** unfold *before* splitting into properties: walk the raw lines (after normalising line endings), and whenever a line starts with a SPACE or HTAB, strip that one leading whitespace character and concatenate it onto the *previous* logical line (not the next) [CITED: https://icalendar.org/iCalendar-RFC-5545/3-1-content-lines.html — "Any sequence of CRLF followed immediately by a single linear white-space character... is ignored... when processing the content line"].
**Warning signs:** a parsed `SUMMARY` that is truncated mid-word, or a route regex that matches on a majority but not all of a fixture's events.

### Pitfall 2: Splitting a property line on every `:` instead of the first
**What goes wrong:** `DTSTART;VALUE=DATE-TIME:20260904T104500Z` and similar parameter-bearing lines have their property-name-plus-parameters segment separated from the value by exactly one semantically significant colon — the *first* unescaped one. A parser that splits on `:` and takes the last segment, or that fails to separate parameters (`;VALUE=DATE-TIME`) from the bare property name (`DTSTART`) first, will mis-key entries or silently drop `DTSTART`/`DTEND`/`CATEGORIES` recognition.
**Why it happens:** looks like ordinary `key: value` text at a glance; the parameter-block syntax (`;PARAM=value;PARAM2=value`) is easy to skip when a first pass only looks at the well-behaved lines in a small sample.
**How to avoid:** `name_and_params, _, value = line.partition(":")`, then `name = name_and_params.split(";", 1)[0].upper()`. Document this partition-on-first-colon behaviour as the accepted minimum subset (a colon inside a quoted parameter value is a real RFC 5545 possibility this exporter is not known to use — treat it as explicitly out of scope, and prefer skipping a line that fails to parse over guessing).
**Warning signs:** `DTSTART`/`DTEND` parsing intermittently failing only on events that happen to carry a `TZID` or `VALUE=` parameter.

### Pitfall 3: Crashing (or silently mis-registering) on the `STATUS:CANCELLED` / 1899-placeholder junk events
**What goes wrong:** measured finding 1 states two junk events carry `STATUS:CANCELLED` with an 1899 placeholder date. A parser that tries to `datetime.strptime()` an out-of-range or malformed date before checking `STATUS` can raise; a parser that parses the date successfully but doesn't filter on `STATUS`/`CATEGORIES` can persist an entry with a match window in 1899, which is harmless for matching (it will never be "today ± 48h") but pollutes the registry and — worse — signals a parser that isn't actually checking `CATEGORIES:FLT`, which is the real filter this codebase should rely on.
**Why it happens:** the two junk events are a small minority in the sample (2 out of an unspecified total), easy to miss if development iterates only against a hand-picked subset of "clean" events.
**How to avoid:** filter on `CATEGORIES:FLT` as the *primary* gate (matching finding 1's own framing — `CATEGORIES:FLT` is what "separates flights from OFFD/CAHC/CPBL"), and treat any date-parsing failure as "skip this event, do not raise, do not enter the registry" — the same never-raising discipline `colour_rules.load_colour_rules()`/`manual_resolutions.load_manual_resolutions()` already apply to a malformed on-disk entry.
**Warning signs:** a registry entry with an implausible (very old or very future) `scheduled_start`/`scheduled_end`.

### Pitfall 4: Logging or re-rendering the secret via an exception's own string form
**What goes wrong:** `requests.exceptions.ConnectionError`, `MissingSchema`, and several other exception subclasses embed the *request URL* in their default `__str__()` output. If the fetch code does `print("calendar fetch failed: %s" % exc)` the way `detect.py`'s existing pattern does (`"%s: %s" % (type(exc).__name__, exc)`), the calendar URL — including its embedded access token — reaches a log line. `journalctl -u skypane-poll` is readable by anyone with VPS access, and this project's own security register (T-02-01-04, `poll_loop.py`'s own docstring) already states the discipline "never logs a bearer token or BYOS setup secret."
**Why it happens:** every other fetch in this codebase targets a fixed, non-secret URL, so logging `str(exc)` verbatim has never been a leak before — the calendar fetch is the first place this pattern becomes dangerous.
**How to avoid:** log only `type(exc).__name__` and a fixed, hand-written description ("calendar fetch failed") — never interpolate `exc` itself, and never log the URL even on success. This must be true of the throttle log line, the parse-failure log line, and any exception path in the module.
**Warning signs:** grepping the module's own source for `% exc` or `str(exc)` finds a hit whose surrounding context is the calendar fetch, not the ADS-B/adsbdb calls (which are safe because their URLs carry no secret).

### Pitfall 5: The airline-identity mismatch (IATA vs ICAO prefixes) silently producing zero matches
**What goes wrong:** the calendar's `SUMMARY` carries an IATA-style flight number (`TO7061` — Transavia France's IATA code is `TO`). Every existing airline-identity table in `server/plane/enrich.py` (`_ICAO_AIRLINE_PREFIXES`) is keyed on the 3-letter **ICAO** callsign prefix (`TVF` for the same carrier — verified: `enrich.py:484`, `"TVF": "Transavia France"`). There is no IATA→ICAO or IATA→airline-name table anywhere in this codebase today. A matcher that naively compares `flight[:2]` against `route["airline_name"]`'s first two letters, or that skips airline matching "because the route+time window is probably unique enough," will either never match anything or accidentally match the wrong carrier on a shared route.
**Why it happens:** the two measured findings focused on parsing structure and route/time collision-resolution — neither closed this specific translation gap, because the sample analysis compared *routes*, not airline codes, across sources.
**How to avoid:** see Research Target 5 / Open Questions below — this needs an explicit, small, extensible IATA-prefix→airline-name table owned by the new calendar module (the same "static table, documented as extensible" pattern `enrich._ICAO_AIRLINE_PREFIXES` already establishes), seeded at minimum with the one carrier the measured findings actually exercised (`"TO": "Transavia France"`), compared against `route["airline_name"]` (populated whenever `route_source` is `"fresh_hit"`/`"cache_hit"`/`"airline_only"`/`"manual"` — i.e. whenever `enrich.resolve_route()` didn't return a full miss).
**Warning signs:** the calendar feature "never fires" in testing even when a calendar entry's route and time clearly match a detection — the airline check should be the first thing to suspect.

## Code Examples

### RFC 5545 unfolding (verified against RFC text, not this codebase — new code)
```python
# Source: RFC 5545 §3.1 (icalendar.org / rfc-editor.org, see Sources) —
# CITED, not project code. This is the recommended minimum-correct
# unfolding pass, to run BEFORE splitting into logical property lines.
def _unfold(raw_text):
    raw_text = raw_text.replace("\r\n", "\n")  # tolerate LF-only exports
    logical_lines = []
    for line in raw_text.split("\n"):
        if line[:1] in (" ", "\t") and logical_lines:
            logical_lines[-1] += line[1:]
        else:
            logical_lines.append(line)
    return logical_lines
```

### Bounded, IP-validated fetch skeleton (new code, following the codebase's existing HTTP idiom)
```python
# Pattern derived from server/plane/detect.py:404-417's requests.get()
# idiom, extended with the SSRF hardening this is the first outbound
# request in this codebase to need (see Research Target 3).
import ipaddress
import socket
from urllib.parse import urlparse

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # generous for an iCal feed; caps a hostile/huge response

def _host_is_safe(hostname):
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True

def _url_is_safe(url):
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and _host_is_safe(parsed.hostname)

def fetch_ics(url, timeout=10.0):
    """Returns the response text, or None on any failure. Never raises,
    never logs the URL or an exception's raw string form (Pitfall 4)."""
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        if not _url_is_safe(current_url):
            return None
        try:
            response = requests.get(
                current_url, headers={"User-Agent": USER_AGENT},
                timeout=timeout, stream=True, allow_redirects=False,
            )
        except requests.RequestException:
            return None
        if response.is_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                return None
            current_url = location
            continue
        if response.status_code != 200:
            response.close()
            return None
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                response.close()
                return None
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")
    return None  # too many redirects
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| No runtime secret existed in this project | `SKYPANE_CALENDAR_ICS_URL` is the first | This phase | New handling discipline needed — see Research Target 4 |
| No outbound request ever targeted an operator-supplied host | The calendar fetch is the first | This phase | New SSRF-class hardening needed — see Research Target 3 |
| Phase 15's rule registry is the only theme-resolution input beyond the base/arrivals theme | A second, higher-precedence source is added | This phase | `resolve_effective_theme_id()` gains one optional parameter (additive) |

**Deprecated/outdated:** nothing in this phase deprecates prior work — it is purely additive to Phase 15's mechanism, per the phase's own explicit framing ("a new source for an existing mechanism, not a new mechanism").

## Runtime State Inventory

> Not a rename/refactor/migration phase — this section is omitted per the instructions. (For completeness: this phase introduces one brand-new `state_dir` file and one brand-new environment variable; it renames nothing and migrates no existing data.)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended throttle interval of ~15–30 minutes between fetch *attempts* | Architecture Patterns, Pattern 2 | Too short: unnecessary load on the operator's calendar host; too long: a freshly-published roster change takes longer to reach the panel. Low risk either way — CONTEXT.md leaves this to discretion and the feature already accepts "up to `wake_interval_s` away, never instantly" latency for its sibling mechanisms |
| A2 | A small, hand-maintained IATA-prefix→airline-name table (seeded with `"TO": "Transavia France"`) is the right mechanism for the airline half of D-04's match key | Common Pitfalls #5, Open Questions | If wrong, the feature could silently never match (if the table is empty/wrong) or mismatch across carriers sharing a route (if airline matching is skipped entirely). This is flagged as the single most important open question below, not asserted as settled |
| A3 | `MAX_RESPONSE_BYTES` of 2MB and `MAX_REDIRECTS` of 5 are reasonable bounds for an iCal feed | Code Examples | Too small: a legitimately large multi-month roster export could be rejected. Too large: less effective DoS protection. Both are easily tunable module constants, not architectural commitments |
| A4 | The real CrewWebPlus export's `DTSTART`/`DTEND` values are formatted as bare `YYYYMMDDTHHMMSSZ` (UTC, no `TZID` parameter) | Code Examples, Pitfall 2 | If the real export instead uses `DTSTART;TZID=Europe/Paris:...` for some or all events, the parser needs a timezone-database lookup this stdlib-only project has no library for (`zoneinfo` is stdlib since Python 3.9 and covers this, but the parser's happy-path assumption should be verified against a real sample at plan/execute time, not assumed) |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **How does the calendar's IATA-style flight-number prefix map to an airline identity the enriched route can compare against?**
   - What we know: the calendar's `SUMMARY` carries an IATA 2-letter airline code (`TO`); `route["airline_name"]` (populated by `enrich.resolve_route()` whenever it isn't a full miss) carries a full airline name string (`"Transavia France"`), itself sourced from either adsbdb, the static `_ICAO_AIRLINE_PREFIXES` table (keyed on the 3-letter ICAO prefix `TVF`), or the operator-writable manual-resolutions registry.
   - What's unclear: there is no existing IATA↔ICAO or IATA↔airline-name table anywhere in this codebase to bridge the two. The measured findings (`16-CONTEXT.md`) verified route/time collision resolution but did not address this translation.
   - Recommendation: add a small, explicitly extensible static table inside the new calendar module (mirroring `enrich._ICAO_AIRLINE_PREFIXES`'s own "documented as extensible, add more as needed" precedent), seeded with at least the one carrier the measured findings actually exercised. This should be raised explicitly at plan time as a decision point, not silently assumed.

2. **Does the real (uncommitted) export's `DTSTART`/`DTEND` ever carry a `TZID` parameter, or is it always the bare UTC `Z`-suffixed form the measured findings describe?**
   - What we know: measured finding 1 states "`DTSTART`/`DTEND` are UTC block times."
   - What's unclear: whether *every* event in the real export uses the bare-UTC form, or whether some (e.g. all-day `OFFD` entries, already filtered by `CATEGORIES:FLT`) use `VALUE=DATE` or a `TZID`-qualified local time. Since `OFFD`/`CAHC`/`CPBL` entries are filtered out before date-parsing matters, this is likely moot for events that reach the matcher, but should be confirmed against the redacted fixture (Research Target 6) rather than assumed silently.
   - Recommendation: the redacted fixture built for this phase should include at least one non-`FLT` event with a plausible (but fake) `VALUE=DATE` or `TZID` shape, so the parser's filter-before-parse ordering is actually exercised, not merely assumed correct.

3. **Exact rolling-window width (today + 24h vs today + 48h) and time-window tolerance around a calendar entry's `DTSTART`/`DTEND`.**
   - What we know: D-03 leaves the exact width to discretion; the Claude's Discretion notes recommend "generous enough to absorb ordinary delay."
   - What's unclear: no specific number is locked.
   - Recommendation: 48h forward window (D-03's stated upper bound) for the registry's retention, with a per-match tolerance of roughly ±90 minutes around `DTSTART`/`DTEND` for the time-window comparison itself (generous enough for a realistic delay, tight enough that a same-day return rotation 8 hours later, per measured finding 2's NCE-ORY example, is never ambiguously close). This is a plan-time-tunable constant, not an architectural decision.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `requests` | Bounded outbound iCal fetch | ✓ | 2.34.2 (pinned, `server/requirements.txt`) | — |
| Python `ipaddress`/`socket`/`urllib.parse` (stdlib) | SSRF-hardening the fetch | ✓ | stdlib, Python 3.12 | — |
| Python `zoneinfo` (stdlib, 3.9+) | Only if the real export's `DTSTART`/`DTEND` ever carries a non-UTC `TZID` (Open Question 2) | ✓ (stdlib) | — | If the real export is bare-UTC throughout (as measured finding 1 states), `zoneinfo` is not needed at all — confirm against the real export before adding this dependency to the parser's happy path |
| The operator's actual iCal endpoint (network reachability, uptime) | The whole feature | Unknown — external, operator-controlled | — | D-03/Claude's Discretion already specify the fallback: silent degrade to "no matches" on the panel when unreachable for a long time |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** the operator's calendar endpoint itself — already designed to degrade gracefully per the locked decisions.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Hand-rolled stdlib check harness (NOT pytest/unittest) — every existing `server/test_*.py` file uses a local `check(name, fn)` accumulator pattern with an `EXPECTED_CHECK_COUNT` ledger re-derived by running the harness, exiting 1 on any failure [VERIFIED: `server/test_colour_rules.py:20-60`] |
| Config file | none — no pytest.ini/conftest.py in this codebase; each harness is a standalone executable script |
| Quick run command | `server/.venv/bin/python3 server/test_calendar_rules.py` (new file, to be created) |
| Full suite command | `scripts/run-all-tests.sh` (append `server/test_calendar_rules.py` to the `HARNESSES` array, `scripts/run-all-tests.sh:34-52` — this array is the single source of truth CI and README both defer to) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Calendar entries never appear in `colour_rules.json` | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` (assert separate file, assert `colour_rules.load_colour_rules()` output is unaffected by a populated calendar file) | ❌ Wave 0 |
| D-02 | Calendar match wins over an exact-callsign manual rule | unit | new check in `server/test_calendar_rules.py` or an addition to `server/test_colour_rules.py`'s resolver checks, calling `resolve_effective_theme_id(..., calendar_theme_id=X)` against a flight that also matches a manual callsign rule, asserting `X` wins | ❌ Wave 0 |
| D-03 | Registry is rewritten whole, past entries expire | unit | assert a fetch with entries A+B, followed by a fetch returning only B, leaves the file with only B (never a merge) | ❌ Wave 0 |
| D-04 | Match requires airline + far-end airport + time window, computed after `resolve_route()` | unit + integration | `server/test_calendar_rules.py` (pure match-function checks: same route/different airline → no match; same airline/different far-end → no match; correct triple → match) + `server/test_poll_loop.py`/`server/test_pipeline_e2e.py` (end-to-end: a fixture calendar entry actually reaches `effective_theme_id` on a matching detection) | ❌ Wave 0 |
| Parser correctness (Research Target 1) | Folded lines, `CANCELLED`/1899 junk, `CATEGORIES` mix all handled correctly | unit | `server/test_calendar_rules.py` against the redacted fixture — assert exact parsed event count and exact field values | ❌ Wave 0 |
| Fetch hardening (Research Target 3) | A hostile/oversized/private-range/redirect-abusing feed is refused | unit | `server/test_calendar_rules.py` with an injectable `transport`/mock (mirroring `enrich.py`'s `default_transport`/injectable-`transport` pattern, `server/plane/enrich.py:163-182`) — no live network call in the test suite, exactly like every other harness in this codebase | ❌ Wave 0 |
| Secret handling (Research Target 4) | Env var never reaches a log line, a page, or `state_dir` | unit + manual grep | `server/test_calendar_rules.py` (assert the persisted registry file and any log capture never contain the configured URL string) + a manual `grep -r "SKYPANE_CALENDAR_ICS_URL" state_dir/` sanity check during plan-time verification | ❌ Wave 0 |
| Throttle (Research Target 2) | A fetch does not occur on every 30s cycle | unit | `server/test_calendar_rules.py` — inject a fake clock (mirroring `poll_loop.py`'s own `now_s()` injectable-clock seam) and assert the fetch function is not called twice within the throttle interval | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 server/test_calendar_rules.py` (and `server/test_colour_rules.py`/`server/test_poll_loop.py` if the shared signature/call sites were touched)
- **Per wave merge:** `scripts/run-all-tests.sh`
- **Phase gate:** full suite green before `/gsd-verify-work`, plus `/gsd-secure-phase 16` (mandatory per `ROADMAP.md`'s Phase 16 entry) before phase close

### Wave 0 Gaps
- [ ] `server/test_calendar_rules.py` — new harness, covers the parser, the throttle, the fetch-hardening gate, and the pure match function
- [ ] A redacted `.ics` fixture (see Research Target 6 recommendation below) — no test file references it yet because neither the fixture nor the harness exists
- [ ] Possibly a small addition to `server/test_colour_rules.py` for the `calendar_theme_id` keyword-argument precedence check (or this can live entirely in the new file — plan-time choice)
- [ ] `server/test_poll_loop.py`/`server/test_pipeline_e2e.py` — extend with one end-to-end fixture-driven case proving a calendar match actually reaches `effective_theme_id` on a real (fixture) detection, mirroring how Phase 15's own end-to-end proof worked

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth surface — the companion's existing session gate (`companion/auth.py`) already covers the one new Settings field |
| V3 Session Management | no | Unchanged — no new session state |
| V4 Access Control | yes | The calendar `<select>` saves through the existing authenticated `settings-form` POST route, gated by `require_session()` exactly like every other Settings field (Phase 15's T-15-13 transfer-verification precedent applies unchanged) |
| V5 Input Validation | yes | The iCal feed body is fully untrusted input — every parsed field (SUMMARY structure, DTSTART/DTEND, CATEGORIES) needs the same never-raising, degrade-on-malformed discipline `colour_rules.load_colour_rules()`/`manual_resolutions.load_manual_resolutions()` already establish for on-disk JSON |
| V6 Cryptography | no | No cryptographic primitive is introduced — HTTPS transport security is provided by `requests`'/the stdlib's existing TLS stack, not hand-rolled |
| V9 Communications (SSRF, roughly OWASP ASVS "Web Frontend Security"/URL handling) | yes | This is the actual core of the new threat surface — see Common Pitfalls and Don't Hand-Roll above: HTTPS-only, IP-range validation after DNS resolution, bounded redirects, bounded response size, bounded timeout |
| V14 Configuration / Secrets | yes | `SKYPANE_CALENDAR_ICS_URL` is the project's first runtime secret handled outside `companion/auth.py`'s existing precedent — needs the identical "never written to a file, never logged, never rendered" discipline that module's docstring already states for `SKYPANE_COMPANION_PASSWORD` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Server-Side Request Forgery via the operator-supplied calendar URL (an authenticated operator, or anyone who gains write access to `skypane.env`, could point the fetch at an internal service — e.g. a VPS-local metadata endpoint or another loopback service) | Tampering / Information Disclosure | HTTPS-only, post-DNS-resolution private/loopback/link-local/reserved-range rejection (`ipaddress` module), bounded redirects re-validated per hop, bounded response size via streaming, bounded timeout — see Code Examples above |
| Secret leak via log line, exception message, or a crafted flash/echo (this codebase's own precedent: Phase 15's T-15-14 covered an analogous echo-into-flash risk for the `rule=` query parameter) | Information Disclosure | Never interpolate `exc`'s raw string form when it might embed the URL (Pitfall 4); never surface the env var's value anywhere in `companion/`, only its presence (mirrors `companion/app.py:501-534`'s `env_wake_interval_default()` fail-open, value-never-returned-as-a-secret-but-here-the-value-itself-is-secret-so-return-only-a-boolean pattern) |
| Denial of service via an oversized or slow-drip feed response, or a feed that redirects in a loop | Denial of Service | Bounded response size (streamed, hard cap), bounded timeout, bounded redirect count — all three independently, since any one alone is an incomplete mitigation |
| Tampering via a hand-edited or corrupted `state_dir` calendar-registry file feeding a crafted `theme_id` into the resolver | Tampering | The same `normalise_rule_theme_id()`-style membership check against `device_config.THEMES` that `colour_rules.py`/`device_config.py` already apply on every read must be applied to the calendar registry's persisted theme selection too — never trust a value read from disk to already be a valid theme id |
| Denial of service via unbounded calendar-registry growth on a hostile/malformed feed | Denial of Service | A hard entry cap on the parsed/retained event list, mirroring `COLOUR_RULE_MAX_ENTRIES`/`MANUAL_RESOLUTION_MAX_ENTRIES`'s "reject/truncate, log the drop count, never grow unbounded" precedent |

## Sources

### Primary (HIGH confidence)
- `server/plane/colour_rules.py` (full read) — the resolver signature, precedence order, file-write contract, leaf-import discipline
- `server/plane/manual_resolutions.py` (full read) — the alternate/older file-contract precedent, its own T-13-02 allowlist discipline
- `server/plane/enrich.py` (relevant sections read: `normalise_callsign()`, `_parse_route()`, `resolve_route()`, `_ICAO_AIRLINE_PREFIXES`) — the enrichment seam this phase's matcher must run after, and the airline-identity gap
- `server/plane/detect.py` (relevant sections read: `query_provider()`, `poll_current_aircraft()`) — the bounded-HTTP-with-per-call-catch pattern to copy
- `server/poll_loop.py` (relevant sections read: `run_once()`'s docstring and per-cycle priming block, both `resolve_effective_theme_id()` call sites, `now_s()`/`advance_is_due()`) — the exact integration points and the throttle precedent
- `companion/auth.py` (full read) — the `PASSWORD_ENV_VAR` secret-handling precedent
- `companion/app.py` (relevant section read: `env_wake_interval_default()`) — the fail-open, per-call, never-cached env-var-read pattern
- `deploy/skypane-poll.service`, `deploy/skypane-poll.timer`, `deploy/skypane-companion.service`, `deploy/skypane.env.example` — confirmed the 30s oneshot cadence and that both processes share one `EnvironmentFile=`
- `server/requirements.txt`, `scripts/run-all-tests.sh` — confirmed no new dependencies and the exact test-harness registration mechanism
- `server/test_colour_rules.py` (header read) — confirmed the hand-rolled check-harness test framework (not pytest)
- `.planning/phases/16-.../16-CONTEXT.md`, `.planning/phases/16-.../16-UI-SPEC.md`, `.planning/ROADMAP.md` §Phase 16, `.planning/phases/15-.../15-CONTEXT.md`, `.planning/phases/15-.../15-SECURITY.md` — the locked decisions, the UI contract, and the threat-register vocabulary this phase extends

### Secondary (MEDIUM confidence)
- [RFC 5545 §3.1 Content Lines — icalendar.org](https://icalendar.org/iCalendar-RFC-5545/3-1-content-lines.html) — line-folding/unfolding rule, verified via WebSearch summary of the official spec text
- [RFC 5545 with inline errata — rfc-editor.org](https://www.rfc-editor.org/rfc/inline-errata/rfc5545.html) — the canonical spec text
- SSRF mitigation pattern (IP-range validation via `ipaddress`, post-DNS-resolution checks, bounded redirects) — corroborated via WebSearch against multiple independent secondary sources (Sourcery vulnerability database, Invicti); this is standard, widely-documented practice, not a single-source claim

### Tertiary (LOW confidence)
- None of the above findings rely on WebSearch-only, uncorroborated claims; the two external topics (RFC 5545 folding, SSRF hardening) were each corroborated against more than one source and against well-established, stable technical facts (an IETF standards-track RFC and a widely-documented web-security pattern), not fast-moving or contested information.

## Metadata

**Confidence breakdown:**
- Standard stack / architecture / integration points: HIGH — every claim about this codebase's existing structure was verified by direct file read at HEAD, not inferred from documentation or memory
- iCal parsing minimum subset: MEDIUM — RFC 5545 mechanics are well-established and cited, but the *exact* shape of the real (uncommitted) export beyond what `16-CONTEXT.md`'s measured findings already describe could not be independently re-verified in this session
- Airline-matching mechanism (Research Target 5 / D-04): MEDIUM-LOW — flagged explicitly as an open, unresolved design gap rather than asserted as solved; this is the one area where the planner must make a genuine new decision, not just apply a pattern
- Security posture / SSRF hardening: HIGH on the mechanism (`ipaddress`, DNS-then-validate, bounded streaming — standard, well-documented practice), MEDIUM on exact numeric bounds (byte cap, redirect count, throttle interval — all reasonable defaults, all tunable, none locked by CONTEXT.md)

**Research date:** 2026-09-07
**Valid until:** 30 days (stable domain — stdlib Python, an already-shipped internal resolver, and a fixed third-party export format are all slow-moving; re-verify sooner only if the real CrewWebPlus export's structure is found to differ from the measured findings once the redacted fixture is actually built)
