# Phase 36: State integrity and device protocol - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning (execution gated on Phase 35, see G-35)
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (INT-01..INT-14), the developer's phase brief for this session, and a re-location of every finding against `main` at `9eb92a6` (after Phases 32–34 and the first 13 plans of Phase 35)

<domain>
## Phase Boundary

No shared state file can be torn or lose an update. The device always downloads the image it was told about. No single bad input or slow upstream can hang or fail a poll cycle.

In scope: INT-01..INT-14 as re-located below (`36-RESEARCH.md` has the current file:line evidence for each).

**Not in this phase:**
- byos `--bind 127.0.0.1` and "no secret in argv" (SEC-06/SEC-07 remainder): plan **37-11**, which waits for this phase. This phase must leave byos's server construction as one `ThreadingHTTPServer((<host>, args.port), Handler)` line and add no outbound connection from byos, so 37-11 can add `--bind` and `IPAddressDeny=any` unchanged.
- Parallel providers (EFF-06), saving `poll_state.json` once per cycle (EFF-05), one DB connection per cycle (EFF-03): Phase 38. This phase changes how `poll_state.json` is written (lock, unique temp name), not how often.
- `run_once` decomposition (ARC-01), `state_store.py` (ARC-02), a shared `net/safe_fetch.py` and moving `_url_is_safe` out of `calendar_rules` (ARC-03), one shared module for byos/server duplicates (ARC-05): Phase 39. This phase adds small helpers those phases will absorb; it does not restructure modules.
- Firmware: no change (INT-05 was checked against `firmware/main/api_client.c` and `state_machine.c`, see decisions).
</domain>

<decisions>
## Implementation Decisions

### Execution gate (locked)
- **G-35:** no plan runs before Phase 35 is complete on `main`: all 22 `35-*-SUMMARY.md` files present, `35-VERIFICATION.md` status passed, ROADMAP marks Phase 35 complete. The first task of every wave-1 plan checks this and stops with "blocked: Phase 35 not complete on main" otherwise. Reason: Phase 35 is still purging comments in companion tests, JS/CSS, `deploy/` and CI; Phase 36 edits `companion/app.py` tests, `deploy/skypane-poll.service` and `deploy/backup/backup_gate.py`, and the comment guard (`scripts/check_comment_history.py check`) must cover every file this phase writes.
- Every plan re-reads the files it edits on the current `main` before editing: the line numbers in this CONTEXT and in RESEARCH are from `9eb92a6` and Phase 35's remaining plans move text around.

### Findings already fixed by a previous phase (re-scoped, say so in SUMMARY)
- **INT-06 "non-string `mac` crashes the handler"**: fixed by Phase 34 (FW-08, plan 34-03): `/device/v1/setup` goes through `normalize_mac()` and answers 422. Still open in INT-06: unbounded/negative `Content-Length`, no socket timeout, bearer token compared with `in values()`, and non-dict entries in `/device/v1/log`'s `logs` list (`entry.get` on a non-dict raises).
- **INT-06 "hmac.compare_digest"** is already used for the enrolment secret (`secret_matches`); what remains is the bearer token check in `bearer_ok()`.
- No other INT finding was fixed by Phases 32–35. Phase 35 only removed comments, so all other findings are open at new line numbers.

### INT-01 — one poll cycle at a time, across processes (locked)
- `fcntl.flock` on `<state_dir>/poll.lock` held for the whole of `run_once()`. The lock lives in `server/poll_loop.py` so both callers (systemd oneshot `main()` and the companion's `POST /poll-now`) get it.
- The systemd oneshot waits for the lock (bounded wait, then fails the cycle with a clear message). The companion never blocks an HTTP thread on it: a busy lock gives the existing "already running" flash (`FLASH_KEY_POLL_ALREADY_RUNNING`), exactly like the current thread-lock path. `_POLL_LOCK` stays as the in-process fast path.
- Proof: a reproduction test with two OS processes × 200 saves each, zero exceptions and zero lost updates (a counter read-modify-written under the lock ends at 400). It must fail on today's code shape (fixed `.tmp` name, no lock) — record the failing run in SUMMARY.

### INT-02 — one `atomic_write` helper (locked)
- New `server/atomic_io.py` (stdlib only): `atomic_write(path, data, mode=None)` writes bytes or str to a temp file created with `tempfile.mkstemp(dir=<same dir>, prefix="." + basename + ".", suffix=".tmp")`, flushes + fsyncs, sets `mode` when given (created with that mode, never chmod-after for secrets), `os.replace`s, and removes the temp file on any failure. Plus one `exclusive_lock(lock_path, timeout_s, blocking=True)` context manager over `fcntl.flock` used by INT-01, INT-03 and the calendar lock (INT-12).
- Every fixed `path + ".tmp"` and every pid-only temp name is replaced: `server/poll_loop.py` (poll_state, panel.bin, and the gallery PNG, which today is written in place), `server/device_config.py`, `server/plane/calendar_rules.py` (registry, URL secret), `server/plane/colour_rules.py`, `server/plane/manual_resolutions.py`, `companion/app.py` (illustration upload temps), `companion/theme_preview.py`.
- **byos** (`stub-server/byos_server.py`) keeps its "never import `server.*`" vendor boundary until Phase 39 (ARC-05) retires it: it gets one local `_atomic_write` with the same contract, used by its three writers (`save_state`, `save_registry` with mode 0600, `save_battery_state`). A behaviour-parity test (not a source-text drift guard) pins both helpers to the same observable contract. SUMMARY records the copy as a Phase 39 ARC-05 input.
- **`deploy/backup/backup_gate.py`** must stay self-contained (runs as `/usr/bin/python3` outside the venv and the release): its fixed `.last-pull.tmp` becomes a local `mkstemp` in `pulled_dir`.
- **`deploy/backup/skypane_backup.py`** is out of scope: its `.partial-<archive name>` files are unique per archive, written by a single timer-driven oneshot, and cleaned by its own prune step. Not a fixed `.tmp` name.
- **`deploy/activate.sh`** (`.current.tmp` symlink swap at deploy time) is out of scope: a single deploy step, serialized by the CI deploy job's concurrency group, and not a state file. Success criterion 2 therefore applies to Python code.
- Success criterion 2 is checked by grep in plan acceptance criteria and in verification, not by a test (tests assert behaviour, never source text).

### INT-03 — `save_device_config` (locked)
- Module-level `threading.Lock` plus `exclusive_lock(<state_dir>/device_config.lock)` around load-merge-write. Today only the companion writes this file, from several threads; the flock covers any second process (a CLI, a future writer).

### INT-04 — theme preview and illustration caches (locked)
- Theme preview writes go through `atomic_write` (unique temp name). After a successful write, stale cache files for the same theme and event with a different signature are removed, and the cache directory is bounded to a fixed number of files (oldest removed first).
- `illustration_normalize._cached_normalized_png_bytes` gets a bounded `lru_cache` (sized above the 43 vendored assets plus overrides, e.g. 128).

### INT-05 — content-addressed image download (locked)
- byos owns `<state_dir>/img/`. On `GET /device/v1/display` it hashes the current `--image` bytes, writes `img/<sha>.bin` through `_atomic_write` if absent, and prunes `img/` to the newest N files (N = 8). `GET /img/<sha>.bin` serves exactly that file; any name not matching `^[0-9a-f]{64}\.bin$` or not present → 404. The current `--image` is never served under a hash it does not have.
- Works for every `--image` (production `panel.bin` and the LAN stub flow) and survives a byos restart between `/display` and `/img`. `img` and `*.tmp` are already in `skypane_backup.py`'s `KNOWN_EXCLUDED`, so no backup change.
- **No firmware change (confirmed):** the firmware downloads `image_url`, checks HTTP 200 + exactly 960 000 bytes + SHA-256 against `image_hash` (`firmware/main/api_client.c` `fp_download_verdict`), and treats a non-200 as a failed download step (`state_machine.c`), retried on the next wake. A 404 can only happen if more than N panels rotate during one wake.
- End-to-end test: `/display` returns hash X, the panel file is replaced with Y, `/img/X.bin` still returns the X bytes whose SHA-256 is X; `/img/<unknown>.bin` → 404.

### INT-06 — byos request hardening (locked)
- `Content-Length`: missing → treated as 0; non-integer, negative, or above a small cap (e.g. 64 KiB; the device's largest body is the log batch) → 400/413 without reading. `Handler.timeout` set (e.g. 15 s) so a stalled client cannot pin a thread.
- `bearer_ok()` compares the presented token against each stored token with `hmac.compare_digest` (no early exit on the first mismatch).
- `/device/v1/log`: non-dict entries skipped (or 422), never an exception.
- A malformed request never produces a 500 or a thread traceback; the next valid request is served.

### INT-07 — bounded poll cycle (locked)
- `deploy/skypane-poll.service`: `TimeoutStartSec=` (90 s; a normal cycle is well under 10 s, the worst legitimate case with every upstream at its limit is under a minute).
- Every outbound HTTP call has a total wall-clock deadline, not only per-read timeouts: detect providers, adsbdb, calendar fetch, ntfy send. For the `requests` calls this is a streaming read that checks a monotonic deadline between chunks and caps the body size (a new small helper; the planner decides its home, e.g. `server/http_fetch.py`). The documented bound is "deadline + one read timeout".

### INT-08 — adsbdb cache (locked)
- A miss is cached only for a 404 or a 2xx whose body yields no route. 429, 5xx, timeouts and transport exceptions are never cached (not even as a short-lived entry): the aircraft is re-queried on the next cycle it is seen.
- Entries carry `cached_at` (epoch seconds, from an injected clock). TTL: misses 1 day, hits 30 days. Legacy entries without `cached_at`: misses are treated as expired (they may be poisoned transient misses); hits are kept and stamped on first read.
- LRU: a cache read moves the entry to the end; `trim_cache` still evicts from the front.

### INT-09 — Caddy log tailer (locked)
- Read in binary from the offset; only complete lines (up to the last `\n`) are parsed; the new offset is just past the last newline, so a partial last line is re-read next cycle.
- A non-integer or negative stored offset resets to 0. An out-of-range epoch `ts` (OverflowError/OSError/ValueError) skips the line. Nothing in the tailer can fail the poll cycle.

### INT-10 — provider JSON shape (locked)
- `query_provider` raises `ValueError` when the body is not a dict or the aircraft value is not a list (caught per provider like any other failure); non-dict aircraft records are dropped before geofencing.

### INT-11 — traceback (locked)
- `poll_loop.main()` prints the full traceback (`traceback.print_exc()` to stdout, which journald captures) before returning 1.

### INT-12 — calendar clock and lock (locked)
- `last_synced_at` comes from the injected `now`, not `datetime.now()`.
- The cross-process registry lock is not held during the network fetch: lock → load, throttle check, record `last_attempt_at` → unlock → fetch → lock → reload, and write only if the configured URL is still the one that was fetched (a URL saved or cleared during the fetch wins) → unlock.
- `_calendar_registry_lock` delegates to `atomic_io.exclusive_lock`.

### INT-14 — SSRF: pin the resolved address (decided)
- **Decision: pin, not just correct the docstring.** Rationale: the claim is a security claim on the only two user-supplied outbound URLs (calendar feed and ntfy topic); `requests`/`urllib` re-resolve the hostname at connect time, so today the check and the connection can see different addresses. Pinning closes that with a small stdlib primitive (resolve once, check every address, connect to the checked address, TLS SNI and certificate verification still against the hostname), and Phase 39's `net/safe_fetch.py` (ARC-03) needs exactly this primitive. Correcting the docstring alone would leave a real, if narrow, gap on an owner-authenticated feature.
- Both `calendar_rules` (fetch, including each redirect hop) and `notify` (POST, no redirects) connect through the pinned primitive. Tests prove the socket connects to the address that was checked even when a second resolution would return a private address, and that certificate verification uses the hostname.

### INT-13 — last detection (locked)
- A cycle that detected an aircraft updates `META_LAST_DETECTION` even when the aircraft was queued rather than displayed (the held branch today passes `flight=None` to `_record_history`).

### Tests and conventions (locked)
- pytest, Phase 32/33 fixtures (`fake_providers`, `test-support/companion_app_server.py`, the byos subprocess harness in `stub-server/test_poll_cycle.py`), no network (pytest-socket + the DNS guard; TLS tests use loopback only), behaviour over source text: no test reads a production source file.
- Comments and docstrings follow D-A3 (English, the why, no plan/ticket IDs); `scripts/check_comment_history.py check` and `ruff check .` stay green.
- One writer per file per wave.

### Claude's Discretion
- Exact constants (lock wait for the oneshot, N kept images, body cap, preview cache size) within the ranges above.
- Home and name of the bounded-HTTP helper and of the pinned-connection primitive (one small module each, or one module), as long as `server/` stays stdlib + Pillow + requests.
- Plan split, as long as files stay disjoint within a wave.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md`: INT-01..INT-14, decisions D-A1..D-A6
- `.planning/REQUIREMENTS.md`: INT-01..INT-14
- `.planning/ROADMAP.md`: Phase 36 success criteria; Phase 37 (37-11 waits on this phase), 38, 39 boundaries
- `.planning/phases/37-security-and-operations-hardening/37-11-PLAN.md`: what 37-11 expects of `byos_server.py` after this phase
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-CONTEXT.md`: behaviour-over-source rule
- Device protocol: `stub-server/byos_server.py` (module docstring and `Handler`) and `stub-server/test_poll_cycle.py` (`validate_display_response`, `verify_panel_bytes`, the end-to-end test); upstream `docs/PROTOCOL.md` is not in this repository
- `firmware/main/api_client.c`, `firmware/main/state_machine.c`: download verdict and failure handling (read only)
- `stub-server/VENDOR.md`: byos vendor boundary
</canonical_refs>

<specifics>
## Specific Ideas

- Cost discipline: research was done inline by the orchestrator; one planner run and one checker run.
- Commit messages in English.
</specifics>

<deferred>
## Deferred Ideas

- byos `--bind` / no secret in argv: 37-11.
- Removing byos's local `_atomic_write` copy: Phase 39 (ARC-05).
- Moving the pinned-fetch primitive and `_url_is_safe` into `net/safe_fetch.py`: Phase 39 (ARC-03).
</deferred>

---

*Phase: 36-state-integrity-and-device-protocol*
*Context gathered: 2026-09-25 from the audit ledger and the session brief*
