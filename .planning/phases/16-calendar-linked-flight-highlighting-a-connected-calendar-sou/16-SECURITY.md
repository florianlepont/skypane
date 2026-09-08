---
phase: 16
slug: calendar-linked-flight-highlighting-a-connected-calendar-sou
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-09-08
---

# Phase 16 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register consolidated from the `<threat_model>` blocks of `16-01-PLAN.md` through
`16-07-PLAN.md` (12 distinct threat IDs, most appearing in more than one plan). Every
row below was verified against the shipped code at HEAD (`aca81e0`), not against plan
or summary prose. Where a plan named a specific test as the proof, that test was
located **and executed**; where a plan named a verification command rather than a
shipped check, the command was re-derived and run by this audit.

No id collision with `15-SECURITY.md`: phase 15 uses `T-15-*`, phase 16 uses `T-16-*`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| operator-supplied iCal feed body → `parse_ics_events()` | Fully untrusted third-party text becomes the candidate list that decides what the physical panel renders | Arbitrary text |
| operator-supplied URL in `skypane.env` → outbound HTTPS request from the VPS | The project's **first** outbound request to a host the developer did not choose; the VPS's own loopback and private-network services sit behind it | URL, resolved addresses |
| third-party redirect response → the next request the VPS makes | A `Location` header is attacker-controlled input deciding where the next connection goes | URL |
| caught exception object → `journalctl -u skypane-poll` | `requests.exceptions.*` embed the request URL — which carries the subscription token — in their default `__str__()` | Secret URL |
| process environment (`SKYPANE_CALENDAR_ICS_URL`) → companion's rendered HTML | The calendar URL is a subscription credential; the web tier is the surface other people in the room can see | Secret URL / boolean |
| hand-edited `{state_dir}/calendar_rules.json` → `load_calendar_registry()` → matcher | An operator-inspectable file becomes the candidate set every displayed flight is compared against | Arbitrary JSON |
| hand-edited `{state_dir}/device_config.json` `calendar_theme_id` → resolver | A single stored string decides the panel's colour on a matched flight | Theme id (closed set) |
| hand-edited `{state_dir}/poll_state.json` `last_calendar_theme_id` → held-branch resolver | A persisted theme id is read back and passed into the resolver on a repaint | Theme id (closed set) |
| authenticated operator → `POST /settings` → `save_device_config(calendar_theme_id=…)` | A submitted string becomes durable config consulted on every poll cycle | Theme id (closed set) |
| one cycle's computed calendar value → two mutually exclusive render branches | The calendar value is the **first** resolver input that is a function of the clock | Theme id |
| `{state_dir}/calendar_rules.json` at rest → anyone with VPS access | The file holds a named person's near-term work schedule | Flight window records |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation (verified in shipped code) | Status |
|-----------|----------|-----------|----------|-------------|---------------------------------------|--------|
| T-16-SSRF | Tampering / Information Disclosure | `_url_is_safe()`, `_host_is_safe()`, `fetch_ics()`'s redirect loop | high | mitigate | Validation is on the **resolved address**, not the hostname string: `_host_is_safe()` (`server/plane/calendar_rules.py:865-897`) calls `socket.getaddrinfo()` and refuses if **any** returned address fails `_address_is_public()` (`:840-863`, delegating range classification to stdlib `ipaddress` across `is_private`/`is_loopback`/`is_link_local`/`is_reserved`/`is_multicast`/`is_unspecified`). Scheme pinned to exactly `https` (`:903`). The gate is the **first statement of every redirect-loop iteration** (`:993-994`), so each `Location` target — resolved through `urljoin()` at `:1025` — is re-validated before any transport call (`:998`), never transitively trusted. Hop count bounded at `CALENDAR_MAX_REDIRECTS + 1` (`:120`, `:993`). | closed |
| T-16-SECRET | Information Disclosure | every log path in the new module; the companion's access to the URL | high | mitigate | Re-derived independently: `calendar_rules.py` contains exactly six `print()` sites (`:452`, `:599`, `:1013`, `:1043`, `:1136`, `:1157`); the only two on an exception path emit `type(exc).__name__` alone (`:1015`, `:1045`) — no path anywhere in the module interpolates `exc` or the URL. The value has a single accessor, `configured_calendar_url()` (`:500`), with a separate boolean accessor `calendar_is_configured()` (`:478`) for the presence question; **zero call sites of `configured_calendar_url` exist under `companion/`** (recursive grep re-run: only a test docstring mentions the env var name). `page_context()` carries a bool + a timestamp only (`companion/app.py:1023`, `:1033`). | closed |
| T-16-INPUT | Tampering / Elevation of Privilege | the four compiled allowlists, applied at three tiers | high | mitigate | Four compiled positive allowlists (`calendar_rules.py:190`, `:198`, `:201`, `:206`) applied at **three independent tiers**: at parse time in `_build_entry()` (`:301-364`, entries rebuilt from scratch as a fixed five-key dict, never by reusing the accumulated property dict); on **every read and every write** via `_normalise_calendar_entry()` (`:519-566`) reached through `_rebuild_capped_entries()` from both `load_calendar_registry()` (`:625`) and `write_calendar_registry()` (`:697`), with an exact-key-set test, `bool`-rejecting numeric tests and an ordering test; and a **third** time inside `match_calendar_theme()`'s own walk (`:1358`), so the matcher never depends on the loader having been the only writer. Plan 16-04 dispositions this `transfer`-to-16-01 at the fetch tier; the transfer target is present and the transfer's own proof (a punctuation body driven end to end) passes. | closed |
| T-16-TAMPER | Tampering | the theme id's path from four stores to `build_canvas()` | high | mitigate | **Five** independent `THEMES` membership gates located and executed: (1) `save_device_config()` raises `ValueError` before the file is opened (`server/device_config.py:713-714`); (2) `normalise_calendar_theme_id()` degrades a non-member to `None` — never `DEFAULT_THEME_ID` — on every read (`device_config.py:479-509`, wired at `:635`); (3) `config_page.handle_post()`'s HTTP-layer test before the value leaves the web tier (`companion/pages/config_page.py:1710-1714` → `FLASH_SAVE_FAILED`, nothing written); (4) `match_calendar_theme()`'s first-statement guard (`calendar_rules.py:1319-1321`); (5) `resolve_effective_theme_id()`'s guard on the keyword (`server/plane/colour_rules.py:500`). A sixth covers the poll-state file specifically (`server/poll_loop.py:984-987`). | closed |
| T-16-BRANCH | Tampering (of displayed information) | divergence between the two flight-displaying branches | high | mitigate | Holds **by construction and re-derived by count**: `match_calendar_theme(` appears exactly **once** in `poll_loop.py` (`:1204`, the flight-detected branch); the held/repaint branch (`:1315-1317`) passes `current_calendar_theme_id` — the value *read* from `poll_state.json` at `:984` — and never calls the matcher. Persisted on the same lines as `last_flight`/`last_route` (`:1232`) so the two cannot drift. Test non-vacuity **independently proven**, not assumed — see Test Discrimination below. | closed |
| T-16-PLACEMENT | Tampering (of displayed information) | where the match and the refresh are called | high | mitigate | Counts re-derived from the shipped file, not from the summary: `grep -c "match_calendar_theme("` == 1 (`poll_loop.py:1204`), `refresh_calendar_registry(` == 1 (`:765`, after the priming block), `resolve_effective_theme_id(` == 2 (`:1206`, `:1315`). Ordering verified by line position: `enrich.resolve_route()` at `:1134` precedes the match at `:1204`, which precedes the first resolver call at `:1206`. Phase 15's exact call-site split still holds: `theme_id=theme_id` == 4 (`:879`, `:1105`, `:1332`, `:1366`) and `theme_id=effective_theme_id` == 2 (`:1216`, `:1325`) out of six `build_canvas()` sites. Three flight-less-branch behavioural checks pass. | closed |
| T-16-DOS | Denial of Service | oversized/slow body, redirect loop, unbounded parse, unbounded registry, per-cycle fetching | medium | mitigate | Bounds located and each independently exercised: body capped **while streamed** with a running counter (`calendar_rules.py:1035-1039`) and `grep -ci "content-length"` over the module == **0** — the declared length is genuinely never consulted; hard timeout passed to the transport (`:110`, asserted from the transport's recorded arguments); redirect hops bounded (`:993`); parse stops at `CALENDAR_MAX_ENTRIES` and discards an unterminated `VEVENT` rather than buffering it live (`:443-446`); read, write and window each re-cap (`:580`, `:697`, `:818`); `calendar_fetch_is_due()` returns `True` on negative elapsed time so a backwards clock step cannot wedge the feature (`:764-765`). See Residual Notes for one declared proof that ships as a manual check rather than an automated one. | closed |
| T-16-PRIV | Information Disclosure | the fixture; the record shape; the registry at rest; the page; the journal | medium | mitigate | Four of the five plan-shares fully verified: the committed fixture is entirely synthetic bar the `PRODID` exporter string (grep for real-carrier/crew vocabulary returns only `PRODID`; `server/fixtures/README.md:286-320` carries the real-versus-synthetic marking); the entry record carries five keys and no flight number, UID, summary or description (`calendar_rules.py:355-361`); the Settings page shows a status and an age and nothing else (`_calendar_no_preview_no_count_in_rendered_page` passes); no calendar-specific key was added to either result dict or the poll log line (re-derived from `poll_loop.py:1424-1465`). **The fifth share — 16-03's rolling-window retention bound — does not hold on the fetch-failure path.** See Open Threats. | **open — below high threshold (non-blocking)** |
| T-16-CYCLE | Tampering | an import cycle silently reintroduced | medium | mitigate | Re-derived by AST, not by reading the diff: `colour_rules.py`'s import set is `{datetime, json, os, re, server(.device_config), threading}` — unchanged, and `git diff` over the phase range adds **zero** import lines to that file. Its docstring's forbidden list now names `server.plane.calendar_rules` explicitly (`colour_rules.py:10`). Precedence is wired by a caller-computed keyword (`:471`, `:500`), which is what preserves the leaf contract under D-02. | closed |
| T-16-DISPLAY | Tampering (of displayed information) | matching on the wrong flight | medium | mitigate | D-04's three-part key asserted part-by-part (far end alone, airline alone, time alone — three separate passing checks), so a matcher silently dropping one condition fails the suite. Direction symmetry enforced by the `_far_end_iata()`/`_entry_far_end_iata()` helper pair (`calendar_rules.py:1230-1265`) and pinned by two symmetry checks. Same-route collision resolves to exactly one candidate by time proximity with a deterministic tie-break (`:1363-1372`), pinned by four fixture-driven ambiguity checks including a list-order-reversal determinism check. The `fresh_hit`/`cache_hit` narrowing is encoded as a field-presence test (`:1327-1341`) and proven against `airline_only`-, `manual`- and `None`-shaped routes. | closed |
| T-16-CSRF | Cross-site request forgery | the `calendar_theme_id` field's write path | medium | transfer | Transfer target verified to actually cover the new field — see Transfer Verification below. | closed |
| T-16-SC | Tampering (package installs) | package installs | n/a | accept | Acceptance rationale re-verified against the phase diff — see Accepted Risks Log ACC-16-01. | closed (accepted) |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party / existing control)*

**All six `high`-severity threats are CLOSED. `threats_open: 0` is a genuine zero at the
blocking threshold — but it is NOT a "no open threats at any severity" zero: T-16-PRIV
is open at `medium` and is filtered out by `block_on: high`. Read the next section.**

---

## Open Threats

### T-16-PRIV — open, non-blocking (medium, below the `high` block threshold)

**Declared mitigation (16-03):** *"D-03's rolling window is the mitigation and is
implemented here: retention is bounded to the current UTC day plus 48 hours and every
write replaces the whole file, so the schedule on disk is never a growing mirror of the
feed."*

**What is present.** `select_window_entries()` (`calendar_rules.py:770-818`) implements
the window correctly, and `write_calendar_registry()` genuinely replaces the whole file
(`:667-728`) — both halves pass their named checks. On the **success** path the window
is applied before persisting (`:1144-1150`).

**What is absent.** The bound is not applied on the fetch-failure path. When `fetch_ics()`
returns `None`, `refresh_calendar_registry()` re-persists `registry["entries"]` verbatim
(`:1128-1131`), and `load_calendar_registry()` re-validates *shape* but never re-applies
the *window*. A permanently unreachable or permanently failing feed therefore leaves the
last successful window on disk indefinitely, re-written every 30 minutes, with no
expiry — the opposite of "retention is bounded to the current UTC day plus 48 hours".

**Reproduced against the shipped module (read-only, temp dir):** seeded one entry that
ended 10 days ago, then drove three failing refresh cycles. The entry was still on disk
after all three, while `select_window_entries()` on the same data returns `[]`. The
retention bound is genuinely unenforced on that path, not merely unproven.

**Impact.** Privacy-at-rest only. Stale entries cannot cause a wrong render — the
matcher's `CALENDAR_MATCH_TOLERANCE_S` (90 min) window excludes them — and the entry cap
still bounds growth, so this is a *retention* failure, not an unbounded-growth or
tampering failure. Exposure requires VPS access, the level T-16-PRIV already scopes.

**Suggested resolution (do not patch during this audit — implementation is read-only):**
either apply `select_window_entries(registry["entries"], now)` on the failure re-persist
path, or apply the window inside `load_calendar_registry()` so every read is bounded.
Alternatively, record it in this log as an accepted risk with an explicit rationale.

*Severity `medium` < `block_on: high`, so this does not count toward `threats_open` and
does not block ship.*

---

## Transfer Verification (T-16-CSRF)

`transfer` was not taken on trust. The declared target — Phase 15's verified site-wide
session gate plus the session cookie's `SameSite=Strict` flag — was verified to cover
the **new field** specifically:

1. **No new route exists.** The full `companion/app.py` diff over the phase range
   (`f726058..HEAD`) adds exactly two keys to `page_context()` and one import — no
   `do_POST()` branch, no route constant, no handler. Re-derived from the diff, not
   from the plan's claim.
2. **The field rides the already-gated handler.** `calendar_theme_id` is read by
   `config_page.handle_post()` (`config_page.py:1701`), which is reached only from
   `do_POST()`'s `SETTINGS_ROUTE` branch, where `require_session()` runs **before**
   `read_form()`, before `page_context()` and before dispatch
   (`companion/app.py:1964-1971`).
3. **The flag is actually set.** `companion/auth.py:138` emits
   `…; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=…` — the same header Phase 15
   verified by execution.
4. **Suite executed at HEAD.** `companion/test_config_page.py` 127/127 pass, including
   the four adversarial `calendar_theme_id` payload checks (empty string, plain invalid
   id, path-traversal-shaped, SQL-shaped) that assert the whole submission is rejected
   and nothing is written.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| ACC-16-01 | T-16-SC | **Zero package installs, re-verified against the phase diff (`f726058..HEAD`).** No `server/requirements.txt`, `server/requirements-dev.txt`, lockfile, `package*.json` or `pyproject.toml` appears in the 24-file changed set; `git log -- server/requirements*.txt` shows the last touch was Phase 04 (`bc308f2`). `server/requirements.txt` still reads exactly `Pillow==12.3.0` / `requests==2.34.2`. The one new module's AST-derived import set is `{datetime, ipaddress, json, os, re, requests, server(.device_config), socket, sys, threading, urllib.parse}` — stdlib plus the already-pinned `requests` (used by `detect.py`/`enrich.py` since Phase 02) plus one first-party leaf module. No component library, CSS framework, client script or build step was added. The supply-chain gate is genuinely not applicable. | gsd-security-auditor (plan-time disposition, all seven plans) | 2026-09-08 |

*Accepted risks do not resurface in future audit runs.*

---

## Test Discrimination (T-16-BRANCH)

The brief required satisfying that the headline test genuinely distinguishes a reusing
implementation from a recomputing one rather than passing vacuously. Confirmed three
ways rather than assumed:

1. **The test's premise is true.** Driving `match_calendar_theme()` directly against the
   shipped module with a registry entry at `T` returns `"green"` at `T` and returns
   `None` at `T + CALENDAR_MATCH_TOLERANCE_S + 3600` — exactly the clock offset the test
   applies before forcing the repaint. A recomputing held branch would therefore resolve
   to the base theme `"white"` on the second cycle.
2. **The assertion is on the real render call, not the reported metadata.** The check
   spies on `render.build_canvas` and compares the captured `theme_id` arguments across
   the two cycles, *and* separately asserts each cycle's reported `effective_theme`
   equals what was actually passed — so a divergence between metadata and render cannot
   hide.
3. **It fails if both branches are wrong in the same direction.** The check additionally
   asserts `rendered_theme_1 == "green"`, so an implementation that returned the base
   theme on *both* cycles (identical, but wrong) still fails.

`server/test_poll_loop.py` 80/80 pass at HEAD.

---

## Unregistered Flags (WARNING — new surface with no threat mapping)

**None of the seven SUMMARY.md files carries a `## Threat Flags` section**, so no
executor-declared flags exist to reconcile. Per the audit brief, that absence was not
treated as evidence of no new surface: the phase's new attack surface was enumerated
independently from the diff (new env-var secret, new outbound request, new `state_dir`
file, new form field, new `poll_state.json` key) and each maps to a registered threat.
The following surfaced during that pass and are recorded rather than silently dropped.
Neither is a blocker; neither invalidates a declared mitigation.

| Flag | Surface | Severity | Assessment |
|------|---------|----------|------------|
| UF-16-01 | The secret is in the **companion process's environment**, not only the poll service's — `deploy/skypane-companion.service:22` loads the same `EnvironmentFile=/opt/skypane/skypane.env` as `skypane-poll.service:15` | low | T-16-SECRET's declared mitigation is *code-level* architectural denial ("`configured_calendar_url()` has no call site anywhere under `companion/`") and that mitigation is fully present and verified. The residual is that process-level containment does not match: any future code under `companion/` could read `os.environ` directly. Verified there is **no** env-dump path today — `companion/` performs exactly three `os.environ.get()` calls, all for specific named variables (`auth.py:69`, `app.py:528`). Note also that `deploy/skypane.env.example`'s new comment ("skypane-companion.service reads only whether it is set") describes the code, but reads as a claim about the process; a future reader could take it as a deployment guarantee it is not. Non-blocking. |
| UF-16-02 | `calendar_rules.json` is written with default umask (observed `0644`) into a state dir provisioned `chmod g+ws` (`deploy/provision.sh:77`) | low | The file holds a named person's near-term schedule and is group/world-readable on the VPS. This is *consistent with* T-16-PRIV's own declared exposure model, which explicitly scopes the registry at "the same exposure level as the registry file itself (both require VPS access)", and matches the mode every other `state_dir` file already uses. Recorded because file mode is a real at-rest property that no declared mitigation covers, not because this phase regressed it. Non-blocking. |
| UF-16-03 | `_url_is_safe()` does not restrict the **port** — `https://example.com:22/a.ics` is accepted | low | Outside the declared mitigation (scheme + resolved-address range + bounded redirects + streamed size cap + timeout). The SSRF target of concern is internal services, and every internal address range is refused by `_address_is_public()`, so this only permits contacting a non-standard port on a genuinely **public** host. Noted, not opened. |

---

## Residual Notes on Closed Threats

- **T-16-SSRF — the irreducible TOCTOU.** The validating `socket.getaddrinfo()` call in
  `_host_is_safe()` and urllib3's own connect-time resolution are two separate lookups;
  nothing pins the connection to the address that was validated. A resolver answer that
  changes between the two moments (short-TTL rebinding, round two) is not covered.
  Closing this fully requires connecting to the validated IP with an explicit `Host`
  header via a custom adapter, which no plan declared. The declared mitigation —
  "resolve explicitly and classify every returned address" — is exactly what
  16-RESEARCH.md's own *Don't Hand-Roll* section prescribes and is fully implemented,
  so **T-16-SSRF stays CLOSED**; this is the known residual of the prescribed pattern,
  recorded so a future reader does not mistake it for full rebinding immunity.
- **T-16-SSRF — adversarial URL sweep run, no bypass found.** Fifteen crafted URLs were
  driven through the shipped `_url_is_safe()`: decimal-integer (`https://2130706433/`),
  hex-octet, trailing-dot, userinfo-prefixed, `localhost`, IPv4-mapped IPv6
  (`[::ffff:127.0.0.1]`), the cloud metadata address, unique-local and link-local IPv6,
  `0.0.0.0`, scheme-relative, `http://`, and `file://` — **every one refused**. One case
  (`https://0177.0.0.1/`) is accepted, and correctly so: `getaddrinfo()` resolves it to
  the genuinely public `177.0.0.1` on this platform, and because the *connection* uses
  the same resolver, validation and connection agree. No parser-divergence bypass exists.
- **T-16-DOS — one declared proof ships as a manual check.** Plan 16-05 declared
  "Task 2's criterion that an authenticated GET of the Settings route returns 200 with
  `calendar_rules.json` containing non-JSON bytes." No such automated check exists in
  `companion/test_config_page.py` or `companion/test_companion_app.py`; `16-05-SUMMARY.md:83`
  records it as *"manual live-server verification"* instead. **This audit executed the
  equivalent itself** against the shipped modules: `load_calendar_registry()` on
  `}{ not json at all \x00\xff` returns the documented empty shape without raising, and
  a full `config_page.render()` with a hostile `last_synced_at` of
  `<script>alert(1)</script>` completes normally and falls back to the pending copy
  rather than echoing it (neither raw nor escaped markup reaches the page). The
  mitigation — a contractually never-raising loader — is present and proven at the
  module tier (`_load_degrades_to_empty_shape_for_hostile_files` passes). **T-16-DOS
  stays CLOSED**; the missing automated HTTP-tier assertion is an evidence gap worth
  closing in a future test pass, not an absent control.
- **T-16-SSRF — one declared proof is a plan-time command, not a shipped check.** Plan
  16-04 declared "the AST criterion asserting every `requests` call disables redirect
  following." `server/test_calendar_rules.py` contains no `ast` usage. This audit
  re-derived it: the module contains exactly **one** `requests.*` call — `requests.get`
  at `calendar_rules.py:935` with `allow_redirects=False`, `stream=True` and `timeout`.
  The property holds.
- **T-16-PRIV — the journal still carries an indirect signal.** No calendar-specific
  field was added to the poll log line, exactly as declared. But the pre-existing
  `effective_theme=` field (Phase 15) will read as the operator's calendar theme on a
  matched cycle, so a journal reader with VPS access can infer that a match fired. This
  is the declared behaviour of an existing field rather than new exposure, and sits at
  the exposure level 16-UI-SPEC.md explicitly accepts for data at rest.
- **`deploy/skypane.env.example` ships a non-blank placeholder.** An unedited copy sets
  `SKYPANE_CALENDAR_ICS_URL=replace-with-your-private-ics-feed-url`, which makes
  `calendar_is_configured()` return `True` and the Settings page show "connected,
  pending" while every fetch is refused by the scheme gate. Cosmetic/UX, no security
  consequence — recorded so it is not later mistaken for a broken fetch.

---

## Verification Method

ASVS L1 (grep-depth: mitigation present in the cited file). Depth applied was in
practice higher than L1 for all six `high` rows and for both non-`mitigate`
dispositions, because grep alone could not have distinguished a present-but-misplaced
or present-but-vacuous control.

- **Proofs executed, not merely located.** At HEAD: `server/test_calendar_rules.py`
  74/74, `server/test_poll_loop.py` 80/80, `companion/test_config_page.py` 127/127,
  `server/test_colour_rules.py` 33/33. Every named proof check passed, including the
  mixed public+private DNS answer (T-16-SSRF), the loopback-redirect refusal, the
  oversized body declaring `Content-Length: 1`, the seven-failure-path secret
  containment group (whose transport exception's message *is* the full secret URL), the
  eight-hostile-entry-shapes read sweep, the hand-edited `poll_state.json` fallback, and
  the past-the-window repaint check.
- **Counts re-derived from the shipped file**, never from a summary's claim:
  `match_calendar_theme(` == 1, `refresh_calendar_registry(` == 1,
  `resolve_effective_theme_id(` == 2, `theme_id=theme_id` == 4,
  `theme_id=effective_theme_id` == 2, `content-length` == 0, `requests.*` calls == 1,
  added import lines in `colour_rules.py` == 0.
- **AST-derived import sets** for both `calendar_rules.py` and `colour_rules.py`,
  rather than reading the docstrings' claims (T-16-CYCLE, T-16-SC).
- **Behavioural spot checks against the live modules** (read-only, via
  `server/.venv/bin/python3`, temp dirs only): the 15-URL adversarial SSRF sweep; the
  corrupt-registry Settings render; the stale-entry retention reproduction that found
  T-16-PRIV's gap; and the direct matcher call that proved T-16-BRANCH's test
  non-vacuous.
- **Both non-`mitigate` dispositions re-derived from code**: the CSRF transfer target
  was traced route-by-route through `do_POST()` and the acceptance rationale was
  re-checked against the phase diff and the AST import set.
- **Both 16-RESEARCH.md corrections honoured.** CORRECTION 1 (no static IATA↔ICAO table)
  is respected in shipped code — the airline is derived at runtime from
  `route["callsign_iata"]` (`calendar_rules.py:1187-1228`) and no carrier table exists
  in the module. CORRECTION 2 (bare UTC only) is respected — `_ICAL_UTC_RE` is the sole
  accepted form and no `zoneinfo`/`pytz` import exists.
- **Implementation files were never modified.** All reproduction ran against the shipped
  modules in temporary directories.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open (blocking) | Open (non-blocking) | Run By |
|------------|---------------|--------|-----------------|---------------------|--------|
| 2026-09-08 | 12 | 11 | 0 | 1 (T-16-PRIV, medium) | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (ACC-16-01)
- [x] `threats_open: 0` confirmed (severity-filtered at `block_on: high`)
- [x] One open threat below the block threshold documented, not silently dropped (T-16-PRIV)
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-08 — ships. T-16-PRIV to be resolved or explicitly
accepted in a follow-up.
