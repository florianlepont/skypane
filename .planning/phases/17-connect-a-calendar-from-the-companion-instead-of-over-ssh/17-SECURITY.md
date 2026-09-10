---
phase: 17
slug: connect-a-calendar-from-the-companion-instead-of-over-ssh
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-09-10
last_audited: 2026-09-10
audited_at_commit: 00aad2a
---

# Phase 17 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register consolidated from the `<threat_model>` blocks of `17-01-PLAN.md` through
`17-04-PLAN.md` — ten distinct threat IDs (T-17-AMP, T-17-DRIFT, T-17-ENVGHOST,
T-17-FLASH, T-17-MODE, T-17-PRIV, T-17-RACE, T-17-SC, T-17-SECRET, T-17-TAMPER).

**Every row below was verified against shipped code at `00aad2a`, by execution, not
by reading plan or summary prose.** This audit ran after the code review's own three
BLOCKER/WARNING fixes (CR-01, CR-02, WR-01, IN-01) and two UAT fixes (webcal
normalisation, cap-before-window reorder) were already committed — see `17-REVIEW.md`.
This is the load-bearing complication this audit had to account for: several threat
rows in the original plan text describe a mitigation (`_POLL_LOCK` closing the
cross-process race) that the phase's own code review proved **false** before this
audit ran, and the plan text was never rewritten. Where the original `<threat_model>`
prose and the corrected, shipped mitigation disagree, this register cites the
corrected mechanism and the evidence that it actually works — not the stale plan
sentence. This is exactly the failure mode `17-CONTEXT.md`'s own "Two corrections to
Phase 16's recorded security posture" section warns the next audit not to repeat.

**What "verified by execution" means here, concretely.** For every `mitigate` row,
a script was run against the real module (`server/plane/calendar_rules.py`) in a
scratch state directory, or a real authenticated HTTP round trip was made against a
running `companion/app.py` instance — not a re-reading of the test suite's own
assertions. Command output is quoted or paraphrased with its concrete result inline.
The full suite (`bash scripts/run-all-tests.sh`) was independently re-run and passed
at **19/19 harnesses, 92% coverage**; `server/.venv/bin/ruff check .` is clean. The
four phase-relevant harnesses were re-run individually and confirmed at their final
ledger counts: `server/test_calendar_rules.py` **113/113**, `server/test_poll_loop.py`
**81/81**, `companion/test_config_page.py` **138/138**,
`companion/test_companion_app.py` **177/177**.

No id collision with `15-SECURITY.md` or `16-SECURITY.md`: phase 15 uses `T-15-*`,
phase 16 uses `T-16-*`, phase 17 uses `T-17-*`.

---

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| the `skypane` service account → other members of the `skypane` group | `deploy/provision.sh` puts `caddy` (the internet-facing reverse proxy's own account) in this group and sets setgid on the state directory. A group-readable file in `state_dir` is readable by the proxy. |
| a hand-edited or externally-modified secret file → `calendar_rules.py`'s read path | `state_dir` is operator-inspectable on the VPS by design; permissions can drift through a future deploy step, a manual edit, or a restore from backup. |
| a connected calendar's fetched flights → the disk, after the operator disconnects or replaces the calendar | The registry holds a named person's near-term schedule. |
| the process environment → the calendar feature's configuration | Retired this phase; a surviving read anywhere would be a second, undocumented source of the secret. |
| `skypane-companion.service` (long-running, threaded HTTP) ↔ `skypane-poll.service` (oneshot, fired every 30s by its own timer) | **Two separate OS processes**, both writing `calendar_rules.json` and reading the secret file, under the same user and the same `state_dir`. Phase 16's and the original Phase 17 plan text's claim that a `threading.Lock` serialises these is false — corrected mid-phase by the code review (CR-01). |
| the operator's browser → the settings write handler | An authenticated but otherwise arbitrary form body decides whether a secret is stored, replaced, or erased along with a named person's flights. |
| the stored calendar URL → the rendered Settings page, and → any redirect/flash/log line | The one surface other people in the room, or `journalctl`, can see. |
| a failing upstream calendar host → the operator's rendered page | Network/name-resolution exception text routinely embeds the full request URL, which carries the subscription token. |
| the authenticated settings write path → an outbound network request | A form submission causes the server to make a request to a host the submitter chose. |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation (verified in shipped code, by execution) | Status |
|-----------|----------|-----------|----------|-------------|------------------------------------------------------|--------|
| T-17-MODE | Information Disclosure | `save_calendar_url()`'s temporary file and the file it renames onto | critical | mitigate | Ran `save_calendar_url()` in a scratch dir with `os.open` spied for both its `path` and `mode` argument: the temp file is created with `os.open(tmp, O_WRONLY\|O_CREAT\|O_EXCL, 0o600)`, and `stat.S_IMODE(os.fstat(fd).st_mode)` read **mid-write, before any rename** was `0o600` (decimal `384`) — the mode is an argument to the *creating* call, not a follow-up `chmod`. Repeated under `umask 022` → `0o600`; under `umask 027` over a **pre-existing `0o644` destination** → `0o600`. Killed the write mid-flight (`os.fdopen` monkeypatched to raise) — the abandoned temp file was removed; `os.listdir(state_dir)` afterward held only the lock file, no `.tmp` remnant, no secret. `grep`-confirmed zero `os.chmod(` calls anywhere in `save_calendar_url()`. | closed |
| T-17-DRIFT | Information Disclosure | `calendar_secret_mode_is_unsafe()` / `_calendar_secret_mode_is_safe()`; `configured_calendar_url()`/`calendar_is_configured()`'s read path | high | mitigate | Wrote a secret file through the codebase's *ordinary* umask-inheriting idiom (plain `open(path, "w")`, landing at `0o644`) — `calendar_secret_mode_is_unsafe()` returned `True`; `configured_calendar_url()` returned `None`; `calendar_is_configured()` returned `False`. Spied on the builtin `open()` during a call to `configured_calendar_url()` against the drifted file: **`opened_paths == []`** — the file's contents are never read when drifted, not merely discarded after reading. Confirmed `calendar_secret_mode_is_unsafe()` reports `False` (not `None`, not falsy-but-wrong) for both an owner-only file and an absent one — the `is False` identity comparison against the three-valued helper is present in the source (`calendar_secret_mode_is_unsafe()` returns `_calendar_secret_mode_is_safe(...) is False`), which is what keeps an absent file from misreporting as a permission problem. | closed |
| T-17-ENVGHOST | Tampering | the retired configuration source | medium | mitigate | `grep -rn "CALENDAR_URL_ENV_VAR\|SKYPANE_CALENDAR_ICS_URL" server companion deploy scripts stub-server` → **zero matches**, across code, comments and check names alike. `server/test_calendar_rules.py`'s own inertness check (set the retired variable to a distinctive token, with and without a secret file present) passes as part of the 113/113 run. | closed |
| T-17-PRIV | Information Disclosure | the fetched registry, on any change of calendar; the disconnect outcome's truthfulness | high | mitigate | **(a) Erase-before-write ordering, live:** confirmed in source — the clear branch erases the registry before removing the file; the set/replace branch (WR-01 fix) now builds and verifies the new secret file *before* erasing the old registry, so a write failure touches neither. Reproduced by monkeypatching `os.fdopen` to raise mid-write on a *replace*: the previously-fetched entries and the *old* URL both survived untouched, and the call returned `False`. **(b) CR-02 (the "disconnected" lie):** reproduced the code review's own scenario — `chflags uchg` on the secret file (macOS analogue of an immutable/read-only-filesystem failure) — and called `save_calendar_url(CLEAR_CALENDAR_URL)`: it now returns **`False`**, the file is still present, and `calendar_is_configured()` is still `True`. Traced `config_page.handle_post()`'s call site: a `False` return maps to `FLASH_SAVE_FAILED`, never to the "Calendar disconnected" flash. **(c) Live HTTP round trip:** connected a calendar via the real `/settings` POST, then submitted `calendar_disconnect=on` — the response redirected to `flash=calendar_disconnected`, the rendered banner read "Calendar disconnected — the flights it supplied have been deleted from the server," and the disconnect checkbox correctly disappeared on the next render (calendar no longer configured). **(d) CR-01 cross-process race, reproduced independently** (not merely trusted from the review): two Python threads standing in for `skypane-poll.service` and `skypane-companion.service` — thread P called `refresh_calendar_registry()` against a transport blocked mid-fetch inside a `threading.Event`; the main thread then called `save_calendar_url(CLEAR_CALENDAR_URL)` concurrently. The disconnect call **blocked for ~10s** (waiting on `_calendar_registry_lock()`, the `fcntl.flock`-based cross-process lock added by the CR-01 fix) until P's fetch completed and released it; the **final on-disk registry was empty** — the disconnect's erase was the last-completed operation, not overwritten by P's write. Re-ran with the *pre-CR-01* code path conceptually absent (i.e. relying on `_POLL_LOCK` alone, as the original plan text claimed) would have failed this exact way per the review's own documented reproduction; the shipped code closes it via a mechanism genuinely visible to both processes (`fcntl.flock()` on a dedicated file, not a `threading.Lock`). | closed |
| T-17-SECRET | Information Disclosure | the feed-URL field's rendering; the companion's served bytes | high | mitigate | `calendar_group()`'s signature is `(configured, drift, last_synced_at, now, current_calendar_theme_id, current_theme_id)` — **no URL parameter exists**; the value is structurally unreachable from this function regardless of future edits. **Live authenticated HTTP round trip** against a running instance (`companion/app.py --state-dir <scratch>`): logged in, submitted a calendar URL built from a distinctive token, host, path segment and query-parameter name (`AUDITTOKEN9182LEAKCHECK` / `audit-leak-host.example` / `secret-calendar-path-zz` / `auditparamname`). Grepped the **redirect response headers** (`Location`, all headers) — no match. Grepped the **rendered Settings page body** (banner text plus the full page) on the next GET — no match for any of the four needles. Confirmed via regex that the rendered `<input name="calendar_url" ...>` tag carries **no `value=` attribute** in any of the four status states (not-connected, connected, drifted). The disconnect checkbox correctly appeared (`name="calendar_disconnect" ... value="on"`, no `checked`) once the calendar was connected. | closed |
| T-17-RACE | Tampering | the calendar registry, under a concurrent save and poll cycle | medium | mitigate | **The original `<threat_model>` text is stale and was not taken on trust.** It credits `_POLL_LOCK` (an in-process `threading.Lock`) with closing the race against "a poll cycle's own calendar refresh" — the code review (CR-01) proved this false, since `skypane-poll.service` is a separate OS process invisible to any `threading.Lock`. The **corrected and shipped** mitigation is `calendar_rules._calendar_registry_lock()`, an `fcntl.flock()`-based lock on a third, dedicated file (`calendar_rules.lock` — distinct from `calendar_rules.json` and `calendar_url.secret`; confirmed by grep, no path collision), acquired around the **entire** load→throttle→fetch→write sequence in `refresh_calendar_registry()` and the entire erase-then-write/write-then-erase sequence in `save_calendar_url()`. Grep confirmed these are the *only* two call sites of `write_calendar_registry()` in the whole tree — no writer of the registry exists outside the lock's coverage. Released in a `try`/`finally` on every path, verified in source. Independently reproduced the cross-process race closing (see T-17-PRIV(d) above — same reproduction, same evidence). **One nuance the original plan text's "non-blocking" language does not describe** (see UF-17-01 below): the acquire is a *bounded* poll loop (up to `CALENDAR_REGISTRY_LOCK_TIMEOUT_S` = 15s), not a fail-fast `LOCK_NB` single attempt — this is a deliberate, documented design choice (chosen above the 10s fetch timeout so a save waits out a real poll cycle rather than failing spuriously), not an oversight, and it never blocks indefinitely (bounded wait, `TimeoutError` caught and mapped to the function's existing failure contract on both call sites). | closed |
| T-17-SC | Tampering (package installs) | package installs | low | accept | `git diff 4d6cd96..HEAD -- server/requirements.txt server/requirements-dev.txt` is empty — no file changed across the whole phase. Every name added across all four plans and the review's fixes (`os.open`/`os.fdopen`/`os.replace`/`os.stat`/`stat.S_IMODE`, `fcntl`, `contextlib.contextmanager`, `errno`, `time`) is standard library. | closed (accepted) |
| T-17-TAMPER | Tampering | the submitted calendar fields (`calendar_url`, `calendar_disconnect`) | medium | mitigate | Confirmed `submitted_calendar_signal()` is the **single** definition (grep: called only from `config_page.handle_post()` and `app.py::_handle_settings_post()`, defined once) and resolves to exactly one of four outcomes in the documented order: a crafted checkbox value → invalid; URL + checkbox together → invalid; checkbox alone → clear; empty/whitespace/absent URL with no checkbox → carry-forward; over-`CALENDAR_URL_MAX_LEN` (2048) → invalid; otherwise → set. `handle_post()` gates on the `invalid` outcome **before** the device-config persistence call, alongside every other membership/shape check, preserving the all-or-nothing contract. Path traversal is structurally impossible: `calendar_secret_path()` joins `state_dir` with the fixed module constant `CALENDAR_SECRET_FILENAME` — the submitted URL is stored as file *content*, never as any part of a path. | closed |
| T-17-FLASH | Information Disclosure | the outcome message and the redirect that carries it | high | mitigate | `awk`-extracted `_handle_settings_post()`'s full method body and grepped it: **zero occurrences of `except`** — structurally impossible for this method to read a caught exception's text, matching the plan's own static-verify assertion. The only runtime value interpolated into any of the four new flash messages is a registry entry count read fresh from disk at render time (`_resolve_flash_text()`'s third special case) — confirmed the redirect targets for all four outcomes (`connected`/`sync_failed`/`disconnected`/`sync_deferred`) carry only the flash *key* in the query string, never a count or any part of a URL. **Live reproduction:** submitted a calendar URL pointing at a non-resolving host (`audit-leak-host.example`, a real DNS failure, not a stub) through the live HTTP server; the response redirected to `flash=calendar_sync_failed`; the rendered banner read the fixed generic copy with no echo of the submitted host/path/token. The suite's own T-17-FLASH check (part of the 177/177 `companion/test_companion_app.py` run) additionally drives a transport whose raised error's message embeds the full URL and confirms none of five needles (token/host/path/query-name/whole-URL) appear in the `Location` header or served body — re-run and confirmed passing. | closed |
| T-17-AMP | Denial of Service | the save-triggered outbound fetch | medium | mitigate | Confirmed the route requires an active session: an unauthenticated `POST /settings` against the live instance redirected to `/login?next=%2Fsettings` (303), never reaching the handler. Confirmed `_POLL_LOCK.acquire(blocking=False)` (a genuine non-blocking acquire) gates entry to the fetch; on contention the request redirects with the deferred key and makes no transport call (part of the 177/177 suite run, re-confirmed). Confirmed `refresh_calendar_registry(state_dir, poll_loop.now_s(), min_interval_s=0)` is the only parameter changed from the poll loop's own call — `fetch_ics()`'s existing bounds (timeout, streamed byte cap, redirect-hop cap, SSRF address gate) are all still the module's own defaults, unchanged and unbypassed on this path. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party / existing control)*

**All 10 threats are CLOSED. `threats_open: 0`.**

---

## Additional adversarial verification performed beyond the declared register

### The SSRF gate after the late `_normalise_calendar_url()` change (UAT-01 fix)

Ran an adversarial sweep of 20+ URL shapes through `_normalise_calendar_url()` +
`_url_is_safe()` together, not read from the tests: decimal-integer IP, hex-octet
host, a userinfo-prefixed host (`user@127.0.0.1` and `evil.com@127.0.0.1`), an
IPv4-mapped IPv6 literal, the cloud metadata address, link-local and ULA IPv6,
`file://`, scheme-relative (`//host`), mixed-case `WebCal://`/`WEBCAL://`, a
double-scheme payload (`webcal://https://evil.com/...`), `webcal://` pointed at
loopback and at the metadata address, and a plain `http://` URL. **Every unsafe
shape was refused; case-insensitive `webcal` rewrite worked; no `webcal → http`
downgrade path exists** (confirmed: `_normalise_calendar_url()` contains no mapping
to plain `http`, only to `https`). Confirmed via `urlparse()` that Python's stdlib
already lowercases the scheme, so `_url_is_safe()`'s bare `!= "https"` comparison is
not itself case-bypassable independent of the webcal rewrite.

Ran `fetch_ics()` end-to-end against a scripted redirect chain: (1) an initial safe
URL redirecting to a loopback `Location` — refused, one transport call only; (2) an
initial safe URL redirecting to a `webcal://` `Location` — refused (redirect targets
are deliberately **not** normalised, so a `webcal` scheme there fails the `https`-only
gate exactly as the docstring claims); (3) an initial `webcal://` URL (normalised to
`https://`) redirecting to the cloud metadata address — refused; (4) the same,
redirecting to a safe host — succeeded, two transport calls, confirming per-hop
re-validation survives normalisation in both directions.

One test artifact worth recording honestly (not a defect): the sweep's "octal
loopback" case (`https://0177.0.0.1`) resolved via this machine's own libc to a
different, non-loopback address (`177.0.0.1`, dropped leading zero, no octal
reinterpretation) rather than being SSRF-relevant either way — `_address_is_public()`
checks whatever address `getaddrinfo()` actually returns, so no bypass exists
regardless of how a given libc parses the literal.

### T-16-SSRF's DNS-rebinding TOCTOU gap (pre-existing, out of Phase 17's scope, noted for completeness)

`_host_is_safe()` validates the addresses `socket.getaddrinfo()` returns at
check time; the actual fetch (`requests.get()` inside `default_calendar_transport()`)
performs its **own**, separate DNS resolution when it opens the connection. Nothing
pins the two resolutions to the same answer, so a DNS server returning a public
address on the first query and a private one on the second (classic rebinding) is
not structurally excluded by this design, despite `_host_is_safe()`'s own docstring
describing "resolve first, then check every address" as the rebinding mitigation.
This is unchanged by Phase 17 — `_normalise_calendar_url()` runs upstream of it and
does not touch this property either way — and was already reviewed and marked
`closed` under `16-SECURITY.md`'s T-16-SSRF row. Recorded here as an observation, not
a Phase 17 finding: it predates this phase, no T-17-* threat claims to close it, and
reopening Phase 16's own audit is out of this audit's mandate. Flagged for whoever
next touches `fetch_ics()` or `_host_is_safe()`.

---

## Unregistered Flags

### UF-17-01 — `_calendar_registry_lock()` is a bounded wait, not a true non-blocking acquire

**Found during:** live reproduction of the CR-01 fix (T-17-PRIV(d)/T-17-RACE above).

**Observation:** the phase's various docstrings describe the save-triggered sync's
locking as reusing a "non-blocking acquire." That is accurate for `_POLL_LOCK`
(`_POLL_LOCK.acquire(blocking=False)`, confirmed genuinely non-blocking by source and
by the deferred-outcome check). It is **not** accurate for the CR-01 fix's
`_calendar_registry_lock()`, which `_handle_settings_post()` reaches *after*
`_POLL_LOCK` is already held: that lock polls for `fcntl.flock(fd, LOCK_EX|LOCK_NB)`
every 0.05s for up to `CALENDAR_REGISTRY_LOCK_TIMEOUT_S` (15.0s) before raising
`TimeoutError`. In the live reproduction, the disconnect call genuinely **blocked for
~10 seconds** waiting on a concurrent (simulated) poll cycle's fetch to finish.

**Why this is not a blocker:** the wait is bounded (never indefinite — both call
sites catch `TimeoutError` and degrade to their existing failure contract), the
constant is deliberately set above the fetch timeout with a documented rationale
("a save arriving mid-poll-cycle almost always succeeds once the poll cycle's own
fetch finishes, rather than failing on a lock that would have come free moments
later"), the route is authenticated-only, and `ThreadingHTTPServer` continues serving
other requests on other threads during the wait. This is a real, working, bounded
design trade-off — not a wedge, not an unbounded hang, and not what any T-17-* threat
promises to prevent.

**Residual worth tracking:** an authenticated operator opening several concurrent
`/settings` POSTs during a real poll cycle could tie up several HTTP handler threads
for up to 15s each. Given this is a single-operator household device behind a
password gate, the realistic exposure is negligible; recorded here so a future
change to `CALENDAR_REGISTRY_LOCK_TIMEOUT_S` or to the companion's threading model
does not silently reintroduce a real one.

**Reproduction:** see T-17-PRIV(d)/T-17-RACE above — the same two-thread scratch-dir
script, timing the `save_calendar_url()` call's wall-clock duration while the
simulated poll cycle held the lock.

---

## Accepted Risks Log

| ID | Threat | Rationale | Accepted By | Date |
|----|--------|-----------|-------------|------|
| ACC-17-01 | T-17-SC | Zero new dependencies across all four plans and the review's fixes; every name added is Python standard library (`os`, `stat`, `fcntl`, `contextlib`, `errno`, `time`). `server/requirements.txt`/`requirements-dev.txt` byte-identical across the whole phase range (`git diff 4d6cd96..HEAD` empty). | gsd-security-auditor | 2026-09-10 |

---

## Open Threats

**None.** 10/10 closed; 0 blocking, 0 non-blocking.

---

## Verification Method Summary

| Check | Result |
|-------|--------|
| `save_calendar_url()` mode, mid-write, spied at the creating `os.open()` call, umask 022/027, over a pre-existing group-readable destination | `0o600` in every case |
| Abandoned temp file after a mid-write failure | removed; no `.tmp` remnant |
| `os.chmod(` calls in `save_calendar_url()` | zero |
| `configured_calendar_url()` against a drifted (`0o644`) file, with `open()` spied | returns `None`; file never opened |
| `grep -rn` retired env-var name/constant across `server/ companion/ deploy/ scripts/ stub-server/` | zero hits |
| CR-02 reproduction: `chflags uchg` on the secret, then `save_calendar_url(CLEAR_CALENDAR_URL)` | returns `False`; file still present; `calendar_is_configured()` still `True` |
| CR-01 reproduction: two-thread cross-process-race simulation (real `fcntl.flock()`, real `threading`) | final registry empty; disconnect's erase not overwritten; disconnect call bounded-blocked ~10s waiting on the lock |
| Live authenticated HTTP round trip, distinctive token/host/path/query-name | absent from all response headers and all response bodies across settings-save, failure, and disconnect flows |
| `calendar_group()` signature | `(configured, drift, last_synced_at, now, current_calendar_theme_id, current_theme_id)` — no URL parameter |
| `_handle_settings_post()` body | zero `except` clauses |
| SSRF adversarial sweep (20+ shapes) through `_normalise_calendar_url()` + `_url_is_safe()` | every unsafe shape refused; no `webcal→http` downgrade; per-redirect-hop re-validation holds after normalisation |
| UAT-02 reproduction: 250 historical + 8 in-window VEVENTs through `parse_ics_events()` + `select_window_entries()` | all 8 in-window survivors present (was 0 before the fix) |
| UAT-02 cap-still-enforced check: 250 genuinely in-window VEVENTs | capped at exactly `CALENDAR_MAX_ENTRIES` (200) |
| UF-16-05 closure: hostile `now` values (`None`, NaN, ±Infinity, `1e300`, non-numeric string, bools) against a populated registry | all resolve to real current time; zero erasure |
| Unauthenticated `POST /settings` | 303 to `/login?next=%2Fsettings`; handler never reached |
| Full suite | `bash scripts/run-all-tests.sh` → PASS, 19/19 harnesses, 92% coverage |
| Ruff | `server/.venv/bin/ruff check .` → clean |
| Phase-relevant harness ledgers | `test_calendar_rules.py` 113/113, `test_poll_loop.py` 81/81, `test_config_page.py` 138/138, `test_companion_app.py` 177/177 |

---

## Sign-Off

- [x] All ten threats have a disposition (nine mitigate, one accept) and are CLOSED
- [x] Accepted risk documented in Accepted Risks Log (ACC-17-01)
- [x] `threats_open: 0` confirmed at every severity, not only at `block_on: high`
- [x] Every `mitigate` row verified by execution against the shipped module or a live HTTP round trip — not by reading test assertions or plan/summary prose
- [x] Stale threat-register text (`T-17-RACE`'s original `_POLL_LOCK` claim, proven false by the phase's own code review) identified and the register cites the corrected, actually-shipped mitigation instead
- [x] Cross-process race (CR-01) and the false-success disconnect (CR-02) independently reproduced against the current tree, not merely trusted from `17-REVIEW.md`
- [x] SSRF gate adversarially swept after the late `_normalise_calendar_url()` addition (UAT-01), including per-redirect-hop re-validation
- [x] Retention/cap reorder (UAT-02) reproduced against the exact reported failure shape (250 historical + 8 in-window events)
- [x] One residual observation recorded as an unregistered flag (UF-17-01 — bounded, not non-blocking, lock wait) with a reproduction and an explicit non-blocker rationale
- [x] One pre-existing, out-of-scope observation recorded for a future audit (T-16-SSRF's DNS-rebinding TOCTOU gap) without being miscounted against this phase
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-10 — ships. 10/10 closed, 0 open at any severity.
