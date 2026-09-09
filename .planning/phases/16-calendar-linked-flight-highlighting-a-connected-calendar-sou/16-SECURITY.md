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
last_audited: 2026-09-08
---

# Phase 16 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register consolidated from the `<threat_model>` blocks of `16-01-PLAN.md` through
`16-07-PLAN.md` (12 distinct threat IDs, most appearing in more than one plan). Every
row below was verified against shipped code, not against plan or summary prose. Where
a plan named a specific test as the proof, that test was located **and executed**;
where a plan named a verification command rather than a shipped check, the command was
re-derived and run by the audit.

**Two audit runs, two baselines.** The original run verified every row at `aca81e0` and
left T-16-PRIV open. The second run (2026-09-08, see `## Security Audit 2026-09-08`)
re-verified T-16-PRIV against `2963619` after commits `c7b5745` / `0d7bb47` shipped its
mitigation, and re-checked every other row for regression against the same HEAD.

**Reading the line numbers.** The T-16-PRIV row and the `## Security Audit 2026-09-08`
section cite **HEAD (`2963619`) line numbers**. Every other row keeps the original run's
`aca81e0` line numbers, which the second run did not re-map because it established
something stronger: 18 of `calendar_rules.py`'s 26 top-level functions — including every
one those rows cite — are **byte-identical** to `aca81e0`, and `poll_loop.py`,
`colour_rules.py`, `device_config.py`, `companion/app.py`, `companion/pages/config_page.py`,
`companion/auth.py` and `deploy/` are untouched across the whole range. Only
`server/plane/calendar_rules.py` moved, and only downward by the lines `66823a3` and
`c7b5745` inserted above.

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
| T-16-PRIV | Information Disclosure | the fixture; the record shape; the registry at rest; the page; the journal | medium | mitigate | **All five plan-shares now verified.** Shares 1-4 were closed by the original run and re-confirmed unchanged: the committed fixture is entirely synthetic bar the `PRODID` exporter string (`server/fixtures/README.md:286-320` carries the real-versus-synthetic marking); the entry record carries five keys and no flight number, UID, summary or description at both the parse tier (`_build_entry()`'s return, `calendar_rules.py:359-365` at HEAD, function byte-identical to `aca81e0`) and the read/write tier (`_normalise_calendar_entry()`'s return, `:597-602`); the Settings page shows a status and an age and nothing else; no calendar-specific key exists in either result dict or the poll log line (`poll_loop.py` untouched across the range — only `last_calendar_theme_id`, a theme id, is persisted). **Share 5 — 16-03's rolling-window retention bound — was OPEN at `aca81e0` and was closed on 2026-09-08 by `c7b5745` (implementation) + `0d7bb47` (regression + anti-drift checks); see `## Security Audit 2026-09-08` for the full re-verification, and the History note below the register for what the gap was.** Verified mitigation at HEAD: `_rebuild_capped_entries(raw_entries, context, now)` (`:630-696`) applies `select_window_entries()` at `:695-696` after its cap loop, and is the ONLY caller of the normalise-and-cap path — reached from `load_calendar_registry()` (`:750`) and `write_calendar_registry()` (`:806-807`), the module's only reader and only writer of `calendar_rules.json` (`calendar_rules_path()` is referenced at exactly two places, the read `open()` at `:743` and the write at `:821`; no other code in the repo touches the file). `now` is a REQUIRED third positional with no default, so a caller cannot silently skip the window. `select_window_entries()` (`:887-935`, byte-identical to `aca81e0`) remains the sole implementation of both edges — `CALENDAR_WINDOW_FORWARD_S` is referenced in executable code exactly once (`:921`) and the day-start edge exactly once (`:918`). `refresh_calendar_registry()` threads one `now` into all four registry calls (`:1241`, `:1261-1262`, `:1282`, `:1298`). `_resolve_retention_now()` (`:606-627`) guards the new clock seam. **Reproduced closed, not assumed:** the original run's own reproduction re-run against the shipped module at HEAD (read-only, temp dir) — the stale entry is gone from the RAW on-disk file after every one of three consecutive `fetch_failed` cycles; the same script against the `aca81e0` module still shows it surviving, so the reproduction is non-vacuous. | closed |
| T-16-CYCLE | Tampering | an import cycle silently reintroduced | medium | mitigate | Re-derived by AST, not by reading the diff: `colour_rules.py`'s import set is `{datetime, json, os, re, server(.device_config), threading}` — unchanged, and `git diff` over the phase range adds **zero** import lines to that file. Its docstring's forbidden list now names `server.plane.calendar_rules` explicitly (`colour_rules.py:10`). Precedence is wired by a caller-computed keyword (`:471`, `:500`), which is what preserves the leaf contract under D-02. | closed |
| T-16-DISPLAY | Tampering (of displayed information) | matching on the wrong flight | medium | mitigate | D-04's three-part key asserted part-by-part (far end alone, airline alone, time alone — three separate passing checks), so a matcher silently dropping one condition fails the suite. Direction symmetry enforced by the `_far_end_iata()`/`_entry_far_end_iata()` helper pair (`calendar_rules.py:1230-1265`) and pinned by two symmetry checks. Same-route collision resolves to exactly one candidate by time proximity with a deterministic tie-break (`:1363-1372`), pinned by four fixture-driven ambiguity checks including a list-order-reversal determinism check. The `fresh_hit`/`cache_hit` narrowing is encoded as a field-presence test (`:1327-1341`) and proven against `airline_only`-, `manual`- and `None`-shaped routes. | closed |
| T-16-CSRF | Cross-site request forgery | the `calendar_theme_id` field's write path | medium | transfer | Transfer target verified to actually cover the new field — see Transfer Verification below. | closed |
| T-16-SC | Tampering (package installs) | package installs | n/a | accept | Acceptance rationale re-verified against the phase diff — see Accepted Risks Log ACC-16-01. | closed (accepted) |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party / existing control)*

**All 12 threats are CLOSED as of 2026-09-08. `threats_open: 0` is now a "no open threats
at any severity" zero, not merely a zero at the blocking threshold — the register's one
remaining open row (T-16-PRIV, `medium`) was closed by this second audit run against a
shipped mitigation, not by lowering a bar.**

### History — T-16-PRIV's gap, preserved

The finding is recorded here rather than erased, because the register's value depends on
its audit trail surviving the fix.

**Declared mitigation (16-03):** *"D-03's rolling window is the mitigation and is
implemented here: retention is bounded to the current UTC day plus 48 hours and every
write replaces the whole file, so the schedule on disk is never a growing mirror of the
feed."*

**The gap, as found at `aca81e0` (2026-09-08, first run).** Four of the five plan-shares
held. The fifth did not: the window was applied only on `refresh_calendar_registry()`'s
**success** path. When `fetch_ics()` returned `None` the function re-persisted
`registry["entries"]` verbatim, and `load_calendar_registry()` re-validated record
*shape* but never re-applied the *window*. A permanently unreachable or permanently
failing feed therefore left the last successful window on disk indefinitely, re-written
every 30 minutes with no expiry — the opposite of the declared bound. Reproduced at the
time against the shipped module: an entry that ended 10 days ago survived three
consecutive failing refresh cycles on disk while `select_window_entries()` on the same
data returned `[]`. Rated `medium` and non-blocking because a stale entry cannot cause a
wrong render (the matcher's 90-minute `CALENDAR_MATCH_TOLERANCE_S` excludes it) and the
entry cap still bounded growth — a *retention* failure, not an unbounded-growth or
tampering one.

**Closed 2026-09-08 by `c7b5745` (implementation) + `0d7bb47` (regression + anti-drift
checks)**, which took the first of the two resolutions the original run suggested and
then went past it: rather than adding a trim to the failure path, the window was moved
into `_rebuild_capped_entries()` — the single helper both the loader and the writer
already routed every entry list through — so load and write agree on the window by
construction and the failure path inherits the bound without a trim call of its own. The
gap's own reproduction was re-run against HEAD by the second audit run and now shows the
stale entry absent from the raw on-disk file on every cycle. Full evidence in
`## Security Audit 2026-09-08`.

---

## Open Threats

**None.** 12/12 closed; 0 blocking, 0 non-blocking. T-16-PRIV, this register's only ever
open row, was verified closed on 2026-09-08 — see the History note above and
`## Security Audit 2026-09-08`.

Two residuals of the newly shipped mitigation are recorded as unregistered flags
(UF-16-04, UF-16-05) rather than as open threats, because in each case the declared
mitigation is present and enforced and the residual sits outside what the declared
mitigation's own wording governs. Neither is blocking. A third — the accepted cost of
the cap-then-window ordering — is recorded under Residual Notes.

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
UF-16-04 and UF-16-05 were added by the 2026-09-08 re-audit, from the surface the
T-16-PRIV mitigation itself introduced. None is a blocker; none invalidates a declared
mitigation.

| Flag | Surface | Severity | Assessment |
|------|---------|----------|------------|
| UF-16-01 | The secret is in the **companion process's environment**, not only the poll service's — `deploy/skypane-companion.service:22` loads the same `EnvironmentFile=/opt/skypane/skypane.env` as `skypane-poll.service:15` | low | T-16-SECRET's declared mitigation is *code-level* architectural denial ("`configured_calendar_url()` has no call site anywhere under `companion/`") and that mitigation is fully present and verified. The residual is that process-level containment does not match: any future code under `companion/` could read `os.environ` directly. Verified there is **no** env-dump path today — `companion/` performs exactly three `os.environ.get()` calls, all for specific named variables (`auth.py:69`, `app.py:528`). Note also that `deploy/skypane.env.example`'s new comment ("skypane-companion.service reads only whether it is set") describes the code, but reads as a claim about the process; a future reader could take it as a deployment guarantee it is not. Non-blocking. |
| UF-16-02 | `calendar_rules.json` is written with default umask (observed `0644`) into a state dir provisioned `chmod g+ws` (`deploy/provision.sh:77`) | low | The file holds a named person's near-term schedule and is group/world-readable on the VPS. This is *consistent with* T-16-PRIV's own declared exposure model, which explicitly scopes the registry at "the same exposure level as the registry file itself (both require VPS access)", and matches the mode every other `state_dir` file already uses. Recorded because file mode is a real at-rest property that no declared mitigation covers, not because this phase regressed it. Non-blocking. |
| UF-16-03 | `_url_is_safe()` does not restrict the **port** — `https://example.com:22/a.ics` is accepted | low | Outside the declared mitigation (scheme + resolved-address range + bounded redirects + streamed size cap + timeout). The SSRF target of concern is internal services, and every internal address range is refused by `_address_is_public()`, so this only permits contacting a non-standard port on a genuinely **public** host. Noted, not opened. |
| UF-16-04 | *(added 2026-09-08)* The retention window is enforced on every **read** and every **write**, but the two paths that perform **no write** leave the previous file's bytes in place: `FETCH_SKIPPED_THROTTLED` and `FETCH_SKIPPED_UNCONFIGURED` both return before `write_calendar_registry()` | low | Verified behaviourally at HEAD (read-only, temp dir): with a stale entry seeded on disk, five unconfigured cycles and one throttled cycle each return `entries=[]` in memory while the file stays **byte-identical** with the stale record still in it. For the throttled path this is bounded — the next due cycle (≤ `CALENDAR_FETCH_INTERVAL_S`, 30 min) trims it, negligible against a ≥24h window, and the no-write behaviour is itself T-16-DOS's own verified mitigation. For the **unconfigured** path it is unbounded: an operator who removes `SKYPANE_CALENDAR_ICS_URL` leaves the last ≤48h window frozen on disk until the file is deleted by hand. Not an open threat: 16-03's declared mitigation is scoped to what happens on *every write* ("every write replaces the whole file"), and a path that performs no write is outside that sentence; the loader also never hands the stale content to any caller on any path, so nothing renders or displays it. Recorded because "retention is bounded to the current UTC day plus 48 hours" reads, to a future operator, as a claim about the bytes on disk in every state — including the feature-off state. Worth one line in the deploy/uninstall notes. |
| UF-16-05 | *(added 2026-09-08)* `_resolve_retention_now()`'s guard admits a **finite but out-of-range** timestamp, which `select_window_entries()` then cannot convert — so it returns `[]` and the write ERASES the registry rather than trimming it | low | The guard is complete for every hostile class the quick task enumerated: driven end to end through `write_calendar_registry(now=…)` and `load_calendar_registry(now)` for `None`, `True`, `False`, `"abc"`, `NaN`, `+Infinity`, `-Infinity`, `[]`, `{}`, `object()` and `complex(1,2)`, all eleven resolve to real `time.time()` and the valid entry survives on disk. It is **not** total: `1e300`, `-1e300` and `2**63` pass `math.isfinite()`, reach `select_window_entries()`, trip its `OverflowError`/`ValueError` catch and yield `[]` — exactly the data-loss mode the guard was written to prevent, one class short. Not an open threat: `now` is an internal seam with no untrusted input path (`server/poll_loop.py:765` passes `now_s()`; `companion/app.py:1033` omits it), and erasure is the conservative direction for a privacy threat. Closing it fully is a one-line range check beside the existing `isfinite` test. |

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
- **T-16-DOS — the cap-then-window ORDER has an accepted cost, verified.** The cap runs
  first (`_rebuild_capped_entries()` breaks the loop at `CALENDAR_MAX_ENTRIES` survivors)
  and the window applies only to what survived, so a hand-edited file whose in-window
  entries sit beyond the cap position yields fewer than 200 — measured: a 50 000-entry
  file of nothing but stale records loads to `[]`, because the cap admitted 200 stale
  records and the window then dropped all of them. This is the hostile-file bound doing
  its job and is stated explicitly in the helper's own docstring. It cannot arise from
  production data: `write_calendar_registry()` is the file's only writer and it persists
  a windowed, `start_at`-ascending list, so out-of-window records can never precede
  in-window ones on disk. The **inverse** ordering would have been the real defect —
  windowing 50 000 records before capping would have removed the bound the cap exists to
  provide.
- **T-16-DOS — the loader now normalises each surviving entry twice.**
  `_rebuild_capped_entries()` calls `_normalise_calendar_entry()` in its cap loop, and
  `select_window_entries()` calls it again on each survivor. Bounded at 2 x
  `CALENDAR_MAX_ENTRIES` per load, and it runs on every authenticated companion page
  render (`companion/app.py:1033`). Measured at HEAD: a 50 000-entry hostile registry
  loads in ≤0.03 s in all three shapes tried (all-in-window, all-stale, all-malformed).
  No bound was lost; the extra pass is a fourth application of T-16-INPUT's allowlists,
  not a reuse of an already-validated dict.
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

*Everything below this line is the **first run's** method, at baseline `aca81e0`, kept
verbatim. The second run's method and its own executed evidence are in
`## Security Audit 2026-09-08` above — including the harness counts at HEAD, which moved
(`test_calendar_rules.py` 74 → 80 across `66823a3` and `0d7bb47`).*

- **Proofs executed, not merely located.** At `aca81e0`: `server/test_calendar_rules.py`
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

## Security Audit 2026-09-08

Second run. Baseline `aca81e0` → HEAD `2963619` (branch `claude/t-16-priv-retention`,
off `claude/seed-3-roster-highlight`; **phase 16 is not on `main`**). The workflow's
short-circuit rule (`threats_open: 0` + plan-time register + L1) was deliberately NOT
taken: `threats_open: 0` at `aca81e0` only reflected that T-16-PRIV sat at `medium`,
below the `high` block threshold. A newly shipped mitigation needs verification, not a
rubber stamp.

Two implementation commits landed after the first run's baseline, both unaudited until
now: `66823a3` (two code-review blockers in the parser and validator) and `c7b5745`
(the T-16-PRIV retention fix), plus `0d7bb47` (tests) and `2963619` (docs).

### 1. T-16-PRIV — mitigation verified present, and reproduced closed

**Reproduction re-run, not trusted to the suite.** The first run's own reproduction —
seed an entry that ended 10 days ago, drive three consecutive **failing** refresh cycles
(advancing past `CALENDAR_FETCH_INTERVAL_S` each time so the throttle genuinely lets
each attempt through, `fetch_failed` asserted per cycle), then read the **raw** file with
`json.load()` rather than through the loader — was re-executed against the shipped module
at HEAD in a temp dir. Result: the stale entry is absent from the raw file after **every**
cycle, and the returned registry matches the raw file on every cycle. The identical
script driven against the `aca81e0` module (loaded side by side, as a control) still
shows the stale entry surviving all three cycles — so the reproduction is **non-vacuous**
and the difference is the fix, not the harness.

**"One place owns the invariant" — verified literally, not from the diff.**

| Claim | How it was checked | Result |
|-------|--------------------|--------|
| One window implementation | `CALENDAR_WINDOW_FORWARD_S` in executable code, and the day-start edge (`replace(hour=0…)`), repo-wide | 1 site each, both inside `select_window_entries()` (`:921`, `:918`) |
| Nothing else recomputes the edges | `select_window_entries` production call sites | 2, both calling the same sole implementation: `_rebuild_capped_entries():696` and `refresh_calendar_registry():1276` |
| One trim site on load/persist | `_rebuild_capped_entries` callers | 2: `load_calendar_registry():750`, `write_calendar_registry():806` — the module's only reader and only writer |
| No second file path | `calendar_rules_path()` references | 2: the read `open()` at `:743`, the write at `:821`. No other module in the repo names the file |
| Window cannot be skipped | `_rebuild_capped_entries(raw_entries, context, now)` signature at `:630` | `now` is positional with **no default** |
| All four refresh calls threaded | `refresh_calendar_registry()` body | `:1241`, `:1261-1262`, `:1282`, `:1298` — one `now`, four calls |
| Sole implementation unchanged | per-function source hash vs `aca81e0` | `select_window_entries()` **byte-identical** |
| Anti-drift guard shipped | `server/test_calendar_rules.py:1764-1790` | asserts the loader's entries are exactly `select_window_entries(list, now)` for any list and any `now` |

Production entry points outside the module: `server/poll_loop.py:765` (`refresh`, passes
`now_s()`) and `companion/app.py:1033` (`load`, omits `now` → `_resolve_retention_now()`
resolves to real current time). Both windowed.

**The `_resolve_retention_now()` guard genuinely prevents erasure.** Driven end to end
through `write_calendar_registry(state_dir, entries, …, now=<hostile>)` and
`load_calendar_registry(state_dir, <hostile>)`, reading the raw file after each: for
`None`, `True`, `False`, `"abc"`, `NaN`, `+Infinity`, `-Infinity`, `[]`, `{}`,
`object()` and `complex(1,2)` — all eleven resolve to real `time.time()`, the write
succeeds, and the valid in-window entry is still on disk and still returned by the
loader. Without the guard each of these would have erased the file. One class escapes it
(finite but out-of-range) — recorded as UF-16-05, not reachable from any production call
site.

**Routine expiry does not flood the journal — verified, not accepted on the docstring's
word.** A read of a file holding three stale entries returns `entries=0` while emitting
**zero** stderr lines, and does **not** rewrite the file. The drop-count warning fires
only for the cap/malformed classes, exactly as claimed.

### 2. Regression on the eleven previously closed threats

Structural fence first: `aca81e0..HEAD` touches **four** files —
`server/plane/calendar_rules.py` and three harnesses. `server/poll_loop.py`,
`server/plane/colour_rules.py`, `server/device_config.py`, `companion/app.py`,
`companion/pages/config_page.py`, `companion/auth.py`, `deploy/` and
`server/requirements*.txt` are all byte-identical to the audited baseline, so
T-16-TAMPER, T-16-BRANCH, T-16-PLACEMENT, T-16-CSRF and ACC-16-01's diff evidence stand
untouched by construction. Within `calendar_rules.py`, an AST-level per-function source
comparison against `aca81e0` shows **18 of 26 byte-identical**, 1 added
(`_resolve_retention_now`), 7 changed.

| Threat | Verification at HEAD | Verdict |
|--------|----------------------|---------|
| T-16-SSRF | `fetch_ics()` source SHA-256 identical to `aca81e0` (`9776f6e78d6bd3f6` both) — the executor's out-of-scope `getattr()` rewrite of the `status_code` check was reverted and left **no trace**; the module's only `getattr` is the pre-existing `is_redirect` read at `:1137`. `_url_is_safe()`, `_host_is_safe()`, `_address_is_public()`, `default_calendar_transport()` all byte-identical. 15-URL adversarial sweep re-run at HEAD: **15/15 refused** (decimal-int, hex-octet, `localhost`, IPv4-mapped IPv6, metadata address, ULA, link-local, `0.0.0.0`, scheme-relative, `http://`, `file://`, RFC1918 x3). Exactly one real `requests.*` call (`requests.get` at `:1052`, `allow_redirects=False`). | CLOSED, untouched |
| T-16-SECRET | The `print()` statement **set** (AST-unparsed, order-independent) is **identical** to `aca81e0` — 6 → 6, zero added, zero removed. The fix added no log line, and window drops are deliberately unlogged (verified above). The only two exception-path prints still emit `type(exc).__name__` alone. `configured_calendar_url` call sites under `companion/`: **0**. `grep -ci content-length`: **0**. `companion/test_config_page.py` 127/127 including the real-HTTP secret-containment check. | CLOSED |
| T-16-INPUT | The four allowlists, `CALENDAR_REGISTRY_KEYS` and `_TRACKED_PROPERTIES` are AST-identical to `aca81e0`. Three tiers intact: `_build_entry()` at parse time (byte-identical), `_normalise_calendar_entry()` via `_rebuild_capped_entries()` from **both** `load` (`:750`) and `write` (`:806`), and `match_calendar_theme()`'s own walk (`:1524`, function byte-identical). Entries still rebuilt from scratch and never reused — `select_window_entries()` appends the fresh `normalised` dict, so the window step is a **fourth** application of the gates rather than a reuse. `_normalise_calendar_entry()`'s only change since the audit is `66823a3`'s added `math.isfinite()` gate — a **strengthening** that closed a NaN/Infinity permanent-match vector. | CLOSED, strengthened |
| T-16-CYCLE | Re-derived by AST, not from the diff. HEAD import set: `{datetime.datetime, datetime.timezone, ipaddress, json, math, os, re, requests, server.device_config, socket, sys, threading, time, urllib.parse.urljoin, urllib.parse.urlparse}`. Delta vs `aca81e0`: `+math` (`66823a3`), `+time` (`c7b5745`) — both stdlib, no new dependency. Zero hits for `enrich`, `colour_rules`, `manual_resolutions`, `illustrations`, `detect`, `render`. `colour_rules.py`'s own import set unchanged. Leaf contract holds. | CLOSED |
| T-16-DOS | Cap-then-window **order** confirmed by AST position inside `_rebuild_capped_entries()` (cap test precedes the `select_window_entries()` call) and by the `break` on `len(survivors) >= CALENDAR_MAX_ENTRIES` still being present; `select_window_entries()` still slices `kept[:CALENDAR_MAX_ENTRIES]`. Hostile-file bound exercised, not assumed: 50 000-entry registries in three shapes (all in-window / all stale / all malformed) each load in ≤0.03 s and return ≤200; a 50 000-entry write persists 200. `calendar_fetch_is_due()`'s code body is AST-identical (docstring-only change) and still returns `True` on negative elapsed, `False` inside the interval. Poll-loop's ten-throttled-cycles-no-write check passes. Windowing after the cap removed no bound — it **added** one. | CLOSED |
| T-16-BRANCH | `poll_loop.py` byte-identical; `match_calendar_theme(` == 1 real call site (`:1204`), held branch at `:1315-1317` passes the value read from `poll_state.json` at `:984`. The headline check — *"a battery-icon repaint … hours after the calendar entry's own time window has closed …"* — passes at HEAD, which matters more than usual here: the retention fix means the second cycle's registry is now genuinely **empty on disk**, so the check would fail immediately if the held branch consulted the registry instead of the persisted id. | CLOSED, re-proven under the new behaviour |
| T-16-PLACEMENT | Counts re-derived from the shipped file: real call sites are `match_calendar_theme(` == 1 (`:1204`), `refresh_calendar_registry(` == 1 (`:765`), `resolve_effective_theme_id(` == 2 (`:1206`, `:1315`); `theme_id=theme_id` == 4, `theme_id=effective_theme_id` == 2, of 6 `build_canvas(` sites. (Raw `grep -c` reports 2/3 for refresh/resolver — the extras are comment mentions at `:757` and `:746`.) File untouched. | CLOSED |
| T-16-TAMPER | All five `THEMES` gates plus the poll-state gate sit in files untouched by the range; `match_calendar_theme()` byte-identical; `colour_rules` 33/33 including the non-member `calendar_theme_id` check; poll-loop's hand-edited-`poll_state.json` check passes. | CLOSED |
| T-16-DISPLAY | `match_calendar_theme()`, `_far_end_iata()`, `_entry_far_end_iata()`, `_reference_time()`, `_airline_iata_from_route()` all byte-identical to `aca81e0`; `CALENDAR_MATCH_TOLERANCE_S` unchanged at 5400; the D-04 part-by-part, symmetry, ambiguity and order-reversal checks all pass. | CLOSED |
| T-16-CSRF | Transfer target untouched — `companion/app.py`, `companion/pages/config_page.py` and `companion/auth.py` are byte-identical to the audited baseline; `companion/test_config_page.py`'s only change in the range is threading `now=` into two fixture writes (`EXPECTED_CHECK_COUNT` still 127, no assertion altered). | CLOSED |
| T-16-SC | `server/requirements.txt` / `requirements-dev.txt` byte-identical across the range; the two new imports are stdlib (`math`, `time`). ACC-16-01's rationale still holds verbatim. | CLOSED (accepted) |

### 3. Harnesses executed at HEAD

`server/test_calendar_rules.py` **80/80** (ledger `EXPECTED_CHECK_COUNT = 80`, raised
76 → 80 by `0d7bb47`), `server/test_poll_loop.py` **80/80**,
`companion/test_config_page.py` **127/127**, `server/test_colour_rules.py` **33/33**.
The four new calendar checks are the T-16-PRIV reproduction, the load-windows-without-
rewriting check, the writer-refuses-what-the-loader-would-drop check, and the
`select_window_entries()` behavioural-equivalence anti-drift guard.

### 4. Explicitly unaffected

`UF-16-02` (the `0644` file mode) is **not** affected. `write_calendar_registry()`'s
tmp-write block is unchanged apart from the added `now` argument, the module contains no
`chmod` or `umask` call anywhere, and the mode was re-observed at HEAD as **`0o644`** —
identical to the first run's observation and to every other `state_dir` file. `UF-16-01`
and `UF-16-03` are likewise untouched (`deploy/` and `_url_is_safe()` both byte-identical).

Implementation files were never modified by this run. All reproduction ran against the
shipped modules via `server/.venv/bin/python3` in temporary directories.

---

## Security Audit Trail

| Audit Date | Baseline | Threats Total | Closed | Open (blocking) | Open (non-blocking) | Run By |
|------------|----------|---------------|--------|-----------------|---------------------|--------|
| 2026-09-08 | `aca81e0` | 12 | 11 | 0 | 1 (T-16-PRIV, medium) | gsd-security-auditor |
| 2026-09-08 | `2963619` | 12 | 12 | 0 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (ACC-16-01)
- [x] `threats_open: 0` confirmed — and now a genuine zero at **every** severity, not only at `block_on: high`
- [x] T-16-PRIV's mitigation verified by re-running the original finding's own reproduction against HEAD, with the pre-fix module as a non-vacuity control
- [x] The T-16-PRIV finding's history preserved rather than erased on closure
- [x] All eleven previously closed threats re-checked for regression against the two unaudited implementation commits (`66823a3`, `c7b5745`)
- [x] Residuals of the new mitigation recorded as unregistered flags (UF-16-04, UF-16-05), not silently dropped
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-08 (second run) — ships. 12/12 closed. No follow-up is
required to ship; UF-16-04 (a leftover registry file after the feature is turned off)
and UF-16-05 (a one-class gap in the retention clock guard) are low-severity hardening
candidates for a future pass.
