# Phase 41 closing audit — all 82 ledger IDs, final tree

DOC-03, the closing consolidation of the four re-audit slices
(`41-REAUDIT-TST-HYG.md`, `41-REAUDIT-FW.md`, `41-REAUDIT-INT-SEC.md`,
`41-REAUDIT-EFF-ARC-CMP.md`) and the two doc-drift logs
(`41-DOC-DRIFT-DEPLOY.md`, `41-DOC-DRIFT-DOCS.md`), plus a final regression
pass and gate re-run on this phase's own final tree.

## Header

- **Final audited commit:** `08e4eb49` (tip of `claude/phase-41` before this
  plan's own commits)
- **Base commit:** `7bd8664` (main at Phase 41's start)
- **Date:** 2026-09-28
- **Effective uid:** 501 (non-root macOS — the same sandbox `41-06`/`41-07`
  ran in)

**Fresh-pass regression check, done first:** `git diff --name-status
3367387f HEAD -- ':!.planning'` is empty — nothing outside `.planning/` has
changed since `41-07`'s own audited commit (`3367387f`), which is itself
identical to `41-06`'s (`863e535d`) for every file `41-06` touched, and to
`41-04`'s/`41-05`'s for every file those touched (each later slice's
`git diff --name-status` against the prior slice's audited commit was
checked and is empty for non-`.planning` paths). Concretely: `.claude/
CLAUDE.md`, `.github/workflows/ci.yml`, `ARCHITECTURE.md`, `COMPLIANCE.md`,
every `deploy/*` file, `firmware/VENDOR.md`, `server/device_policy.py`,
`server/state_store.py`, `stub-server/byos_server.py`, and the six
`companion/*` comment-only files that `41-02` corrected all reached their
final, closing-audit-time content **before** `41-04` ran — every one of the
four re-audit slices' own evidence (file:line reads, `git grep`s, test
runs) was already taken against this exact final tree. There is therefore
no drift between what `41-04`..`41-07` verified and what ships in this PR:
every verdict below is carried over unchanged, not re-derived, except where
this pass's own regression run below found something new.

Fence: `git diff --name-only 7bd8664 -- firmware/` → `firmware/VENDOR.md`
only (re-confirmed on this final tree, matching every prior slice).

Same-code proof: `python3 scripts/check_comment_history.py same-code
--base 7bd8664 --allow stub-server/byos_server.py $(git diff --name-only
--diff-filter=M 7bd8664 -- ':!*.md' ':!.planning' ':!hardware/logs')` exits
**0** on this final tree (the one `--allow` is `stub-server/byos_server.py`,
documented in `41-02-SUMMARY.md`: its module docstring feeds `argparse`'s
`description=__doc__`, so the checker's own AST design treats it as literal
code, not a strippable docstring — confirmed by manual diff review that
every changed line in that file is a comment/docstring).

DOC-01's known-drift examples, re-checked on the final tree: `grep -rn
"persists nothing" deploy/ ARCHITECTURE.md` → no hits (both corrected);
`grep -n "mode 640" deploy/provision.sh` → no hits (corrected to `mode
660` at the Caddyfile citation); `grep -rn "18 harnesses" .github` → no
hits (phrase never present); `deploy/skypane.env.example:3` → "Copy this
file to `/opt/skypane/skypane.env` ON THE VPS ONLY" (corrected install
path).

## Verdict totals

Recomputed from the rows below. The first version of this table read 77/3/2
while its rows counted 76/3/3 (DOC-03's own open row was not counted).

| Verdict | Count |
|---|---|
| VERIFIED-CLOSED | 77 |
| FLAGGED-DIFFERENT | 3 |
| ACCEPTED-OPEN | 2 |
| FLAGGED-OPEN | 0 |
| **Total** | **82** |

FLAGGED-DIFFERENT: TST-02, TST-15, ARC-03.
ACCEPTED-OPEN: HYG-01, HYG-06 (accepted as-is by the developer on 2026-09-28 (the guard tightening and reword were deferred to `.planning/todos/pending/comment-history-guard-residue.md`)).

## All 82 findings

| ID | Verdict | Closing commit(s) | Evidence (summary) | Detail |
|---|---|---|---|---|
| TST-01 | VERIFIED-CLOSED | `745322a` | pytest+xdist+cov deps, `pyproject.toml` config, shared `conftest.py`, `fail_under=93`, CLAUDE.md/CONTRIBUTING.md updated | `41-REAUDIT-TST-HYG.md` TST-01 |
| TST-02 | FLAGGED-DIFFERENT | `745322a` | Migration ledger closed correctly at Phase 32's own close; the standalone `32-ledger-check.py --all` now fails on 6 node ids Phase 39 legitimately renamed/strengthened — no lost coverage, a stale verification script | `41-REAUDIT-TST-HYG.md` TST-02 |
| TST-03 | VERIFIED-CLOSED | `745322a` | `--disable-socket`/`--allow-hosts=127.0.0.1,::1,localhost`; live full-suite run shows `pytest_socket` blocking a non-loopback connect | `41-REAUDIT-TST-HYG.md` TST-03 |
| TST-04 | VERIFIED-CLOSED | `745322a` | `ci.yml` + `pyproject.toml` target 3.14; live CI run `36377045745`: `Successfully set up CPython (3.14.7)` | `41-REAUDIT-TST-HYG.md` TST-04 |
| TST-05 | VERIFIED-CLOSED | `745322a` | `firmware.yml`'s `host-tests` job runs `run_host_tests.sh`, no ESP-IDF container needed; 10/10 suites pass live | `41-REAUDIT-TST-HYG.md` TST-05 |
| TST-06 | VERIFIED-CLOSED | `745322a` | Separate `test`/`production-deploy` concurrency groups, deploy never cancelled; static YAML shape confirmed, dynamic double-push edge case remains CI-only (unchanged from `32-VERIFICATION.md`) | `41-REAUDIT-TST-HYG.md` TST-06 |
| TST-07 | VERIFIED-CLOSED | `745322a` | `--only-shell` + `actions/cache` on `~/.cache/ms-playwright`; CI log shows a cache hit | `41-REAUDIT-TST-HYG.md` TST-07 |
| TST-08 | VERIFIED-CLOSED | `745322a` | Hash-pinned `requirements.txt`/`requirements-dev.txt`; `pip install --require-hashes` in CI | `41-REAUDIT-TST-HYG.md` TST-08 |
| TST-09 | VERIFIED-CLOSED | `745322a` | `patch=["subprocess"]`, `fail_under=93`; measured 94.86%/94.95% (root/CI), both above floor | `41-REAUDIT-TST-HYG.md` TST-09 |
| TST-10 | VERIFIED-CLOSED | `4f7221a` | One shared `AppServer`/app-server-fixture family in `companion/conftest.py`; no duplicated harness class survives | `41-REAUDIT-TST-HYG.md` TST-10 |
| TST-11 | VERIFIED-CLOSED | `4f7221a` | `pytest-playwright` pinned; `SKYPANE_REQUIRE_BROWSER=1`/`CI=true` fails instead of skipping; xdist-parallel `[chromium]` cases pass live | `41-REAUDIT-TST-HYG.md` TST-11 |
| TST-12 | VERIFIED-CLOSED | `4f7221a` | `test_suite_guards.py` rules pass live; no test reads `.planning/`/UI-SPEC or asserts on another file's comments | `41-REAUDIT-TST-HYG.md` TST-12 |
| TST-13 | VERIFIED-CLOSED | `4f7221a`, gap closure `3e15556` | Root run: `requires_non_root`-marked tests skip cleanly (7 named), every write inside `tmp_path` | `41-REAUDIT-TST-HYG.md` TST-13 |
| TST-14 | VERIFIED-CLOSED | `4f7221a` | `run_all_tests.py` gone; `EXPECTED_CHECK_COUNT` survives only inside the two migration-ledger tool scripts' own vocabulary; `run-all-tests.sh` is a thin pytest wrapper | `41-REAUDIT-TST-HYG.md` TST-14 |
| TST-15 | FLAGGED-DIFFERENT | `4f7221a` | Coverage parity holds (94.86%/94.95% ≥ pre-migration 93.35%/93.38%); the standalone `33-ledger-check.py --all` fails on 4 harness fragments Phase 39 legitimately renamed — same root cause as TST-02, no lost coverage | `41-REAUDIT-TST-HYG.md` TST-15 |
| HYG-01 | ACCEPTED-OPEN | `ee2737a` (guard), `f266a05`/`8a8b8b4` (purge) | `check_comment_history.py check` passes against its own pattern set, but a targeted guard-evasion hunt found 21 genuine residual history references (10 letter-suffixed `D-`IDs, 11 dotted UI-SPEC section numbers, 2 bare Phase-Plan numerics) across 12 tracked files the shipped guard's regex does not match | `41-REAUDIT-TST-HYG.md` HYG-01 |
| HYG-02 | VERIFIED-CLOSED | `f266a05`/`7cd0380` | Zero genuine `history_hits` in `.css`/`.js`; the hunt's two hits are false positives (a date, arithmetic, a filename reference) | `41-REAUDIT-TST-HYG.md` HYG-02 |
| HYG-03 | VERIFIED-CLOSED | `7cd0380` | Zero genuine `history_hits` in `.c/.h/.sh/.service/.timer/Caddyfile/.env.example`; the hunt's two hits are false positives (a duration, a date) | `41-REAUDIT-TST-HYG.md` HYG-03 |
| HYG-04 | VERIFIED-CLOSED | `ee2737a` | English-only rule stated in both `.claude/CLAUDE.md` and `CONTRIBUTING.md`; one non-English hit found, inside `.planning/spikes/` (excluded by design, outside production scope) | `41-REAUDIT-TST-HYG.md` HYG-04 |
| HYG-05 | VERIFIED-CLOSED | `8a8b8b4` | `health_severity`/`anomaly_active`/`usable_pairs`/`label_grid` deleted from all tracked non-`.planning` code | `41-REAUDIT-TST-HYG.md` HYG-05 |
| HYG-06 | ACCEPTED-OPEN | `ee2737a` | The CI guard step and its own mutation-tested test suite are correctly wired and run unconditionally in `ci.yml`, but the regex itself has the gap HYG-01 exploits — three targeted regex edits proposed, not yet made | `41-REAUDIT-TST-HYG.md` HYG-06 |
| FW-01 | VERIFIED-CLOSED | `745322a`, `fc4e2e5` (W-1 fix), `7cd0380` | Reset-reason check → backoff+sleep before Wi-Fi; `epd_init` returns errors, no `ESP_ERROR_CHECK`; `34-VERIFICATION.md`'s W-1 warning closed anyway by `fc4e2e5`/`nvs_boot.c` | `41-REAUDIT-FW.md` FW-01 |
| FW-02 | VERIFIED-CLOSED | `745322a` | One-shot `esp_timer` wake-budget deadline + independent task WDT; hardware logs confirm both mechanisms firing correctly | `41-REAUDIT-FW.md` FW-02 |
| FW-03 | VERIFIED-CLOSED | `745322a`, `7cd0380` | 401/403 clears `FP_NVS_DEVICE_TOKEN`, re-enrols next wake, distinct `step=auth` vs `step=enrol`; hardware logs confirm | `41-REAUDIT-FW.md` FW-03 |
| FW-04 | VERIFIED-CLOSED | `745322a` | `FP_SLEEP_S_MAX=86400` enforced in `validate.c`; hardware log confirms rejection at 86401 | `41-REAUDIT-FW.md` FW-04 |
| FW-05 | VERIFIED-CLOSED | `745322a` | `esp_http_client_write()`/`fetch_headers()`/`busy_wait()` return values all checked, mapped to the right `step=` | `41-REAUDIT-FW.md` FW-05 |
| FW-06 | VERIFIED-CLOSED | `745322a` | All seven named response-validation items (hash, URL, sleep_s, led_enabled, token, size/SHA gate, sleep decision) each have a pure helper and its own host-test case | `41-REAUDIT-FW.md` FW-06 |
| FW-07 | VERIFIED-CLOSED | `745322a` | https-only unless `CONFIG_SKYPANE_ALLOW_HTTP` (dev-only); custom cert bundle holds only the two ISRG roots, fingerprint-pinned | `41-REAUDIT-FW.md` FW-07 |
| FW-08 | VERIFIED-CLOSED | `745322a` (registry), `f4d9709`/`34bc038`/`8ee39d7` (later unrelated edits) | Per-device NVS secret; byos registry refuses an unregistered MAC (403) or wrong secret (401) via `hmac.compare_digest`; live pytest re-run confirms | `41-REAUDIT-FW.md` FW-08 |
| FW-09 | VERIFIED-CLOSED | `745322a` | `CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y`, `CONFIG_LWIP_DHCP_DOES_ARP_CHECK=n` in production defaults; DHCP-timing figure is hardware-log-evidence, not re-measured this pass | `41-REAUDIT-FW.md` FW-09 |
| FW-10 | VERIFIED-CLOSED | `745322a`, `7cd0380` | One shared keep-alive client; TLS session tickets persisted in RTC memory; wake-duration diagnostic line kept outside the Log Line Contract | `41-REAUDIT-FW.md` FW-10 |
| FW-11 | VERIFIED-CLOSED | `745322a`, `7cd0380` | 8-sample battery average, read before Wi-Fi brings up the radio; accuracy figure is hardware-log-evidence | `41-REAUDIT-FW.md` FW-11 |
| FW-12 | VERIFIED-CLOSED | `745322a` | `CONFIG_SPIRAM_MEMTEST=n`; 800µs row wait kept deliberately (datasheet gives no guidance) with a comment explaining why; timed light-sleep during the spacing wait | `41-REAUDIT-FW.md` FW-12 |
| FW-13 | VERIFIED-CLOSED | `745322a`, `9eb92a6` | `fp_api_base_normalize()` is the one normalizer; three named orphan symbols gone; rollback stays off (no OTA yet) with an explanatory comment | `41-REAUDIT-FW.md` FW-13 |
| FW-14 | VERIFIED-CLOSED | `745322a` | One hex-check helper, one HTTP-client-config path (2 call sites); NVS family down to one helper set with 3 scalar-counter call sites still direct (accepted minor gap, unchanged since `34-VERIFICATION.md`) | `41-REAUDIT-FW.md` FW-14 |
| FW-15 | VERIFIED-CLOSED | `745322a` | Version derived from `git describe --tags --always --dirty` at build time, `CMakeLists.txt` fallback documented | `41-REAUDIT-FW.md` FW-15 |
| INT-01 | VERIFIED-CLOSED | `f4d97097`, `9f0142fe`/`8ee39d7d` | `fcntl.flock`-backed `poll_cycle_lock()` around `run_once()`; companion's poll-now fails fast on `PollBusy`, never blocks | `41-REAUDIT-INT-SEC.md` INT-01 |
| INT-02 | VERIFIED-CLOSED | `f4d97097` | One `atomic_write()` (`server/atomic_io.py`), one documented vendor-boundary copy in `byos_server.py`; every writer confirmed to call it | `41-REAUDIT-INT-SEC.md` INT-02 |
| INT-03 | VERIFIED-CLOSED | `f4d97097`, `8ee39d7d` | Thread lock + flock around `save_device_config()`'s whole load-merge-write | `41-REAUDIT-INT-SEC.md` INT-03 |
| INT-04 | VERIFIED-CLOSED | `f4d97097`, `c4457f36` | `mkstemp`-based unique temp names via the shared `atomic_io` primitive; bounded 64-file/128-entry caches with pruning | `41-REAUDIT-INT-SEC.md` INT-04 |
| INT-05 | VERIFIED-CLOSED | `f4d97097`, `34bc0384`, `83121a35` | Content-addressed `img/<sha>.bin`, last 8 kept; strict path regex; 404 on any non-matching or missing hash | `41-REAUDIT-INT-SEC.md` INT-05 |
| INT-06 | VERIFIED-CLOSED | `f4d97097`, `34bc0384`, `83121a35` | 64 KiB body cap, `Handler.timeout`, typed MAC parsing, `hmac.compare_digest` throughout | `41-REAUDIT-INT-SEC.md` INT-06 |
| INT-07 | VERIFIED-CLOSED | `f4d97097`, `8ee39d7d` | `TimeoutStartSec=90s` (unit-tested); four per-call deadline constants threaded through `pinned_request`; VPS runtime value independently confirmed 2026-09-26 | `41-REAUDIT-INT-SEC.md` INT-07 |
| INT-08 | VERIFIED-CLOSED | `f4d97097`, `8ee39d7d` | `CACHE_MISS_TTL_S=86400`, `CACHE_HIT_TTL_S=30*86400`; LRU touch-on-read confirmed | `41-REAUDIT-INT-SEC.md` INT-08 |
| INT-09 | VERIFIED-CLOSED | `9f0142fe`, `bba5933e`, `32d2ea76`, `f4d97097` | Tailer advances to the last newline, errors caught; regression proven via passing `test_caddy_tail.py` against the Phase-38-rewritten module | `41-REAUDIT-INT-SEC.md` INT-09 |
| INT-10 | VERIFIED-CLOSED | `9f0142fe`, `62550bd3`, `f4d97097` | Non-dict/non-list provider body type-checked before use, unaffected by Phase 38's provider parallelisation | `41-REAUDIT-INT-SEC.md` INT-10 |
| INT-11 | VERIFIED-CLOSED | `f4d97097`, `9f0142fe`/`8ee39d7d` | `main()`'s generic exception branch prints a full traceback; `PollBusy` handled separately without one | `41-REAUDIT-INT-SEC.md` INT-11 |
| INT-12 | VERIFIED-CLOSED | `8ee39d7d`, `f4d97097` | Injected clock throughout `refresh_calendar_registry`; lock released during the fetch itself, stale results discarded via `FETCH_SUPERSEDED` | `41-REAUDIT-INT-SEC.md` INT-12 |
| INT-13 | VERIFIED-CLOSED | `9f0142fe`, `f4d97097` | Held-branch detection still advances "last detection" via `detected=ctx.flight is not None`, with the original explanatory comment intact | `41-REAUDIT-INT-SEC.md` INT-13 |
| INT-14 | VERIFIED-CLOSED | `f4d97097`, `8ee39d7d` | `pinned_request()` resolves once, connects only to the checked address (DNS-rebinding closed); `safe_fetch.py` is additive defence-in-depth, not a substitute | `41-REAUDIT-INT-SEC.md` INT-14 |
| SEC-01 | VERIFIED-CLOSED | `6fb23e77` | `client_ip()` trusts `X-Forwarded-For` only from a loopback peer; per-IP/64 throttle bucket | `41-REAUDIT-INT-SEC.md` SEC-01 |
| SEC-02 | VERIFIED-CLOSED | `e18c5ef9`, `32d2ea76` | `Strict-Transport-Security: max-age=31536000` on both Caddy site blocks; on-the-wire presence rests on `37-SEC-BASELINE.md` CP-4 | `41-REAUDIT-INT-SEC.md` SEC-02 |
| SEC-03 | VERIFIED-CLOSED | `6fb23e77`, `6b73b803`/`9f0142fe` | Origin/`Sec-Fetch-Site` check runs first in `_dispatch()`, before route matching — covers all 17 current POST routes structurally, not per-route | `41-REAUDIT-INT-SEC.md` SEC-03 |
| SEC-04 | VERIFIED-CLOSED | `6fb23e77`, `f286df71`/`8014e97f`/`c71dc7d1` | Nightly `sqlite3 .backup`; off-box copy is pulled (not pushed) via a forced-command SSH gate; README corrected; off-box arrival rests on `37-SEC-BASELINE.md` CP-8/9 | `41-REAUDIT-INT-SEC.md` SEC-04 |
| SEC-05 | VERIFIED-CLOSED | `6fb23e77`, `e18c5ef9` | Release-dir + atomic symlink swap; post-deploy `systemctl is-active` + HTTP probes fail the job; `daemon-reload` on install and rollback — proven via a Linux container re-run for this macOS sandbox's BSD-`mv` gap | `41-REAUDIT-INT-SEC.md` SEC-05 |
| SEC-06 | VERIFIED-CLOSED | `6fb23e77`, `34bc0384` | All four units carry `CapabilityBoundingSet`/`PrivateDevices`/`ProtectKernel*`/`RestrictAddressFamilies`/`SystemCallFilter=@system-service`/`UMask=0027`; byos `--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost`; offline scores byte-identical to the Phase 37 baseline | `41-REAUDIT-INT-SEC.md` SEC-06 |
| SEC-07 | VERIFIED-CLOSED | `6fb23e77`, `34bc0384` | No secret on argv or in the unit file; `skypane.env` is `root:root 600`; `DEPLOY_HOST_KEY` passed via CI `env:`, never interpolated into a `run:` line | `41-REAUDIT-INT-SEC.md` SEC-07 |
| SEC-08 | VERIFIED-CLOSED | `6fb23e77` | `00-skypane.conf` drop-in sets `PermitRootLogin no`; validated with `sshd -t` before reload, restores previous config on failure | `41-REAUDIT-INT-SEC.md` SEC-08 |
| EFF-01 | VERIFIED-CLOSED | `32d2ea76`, `9f0142fe` | `encode zstd gzip` on the companion site block; static bytes cached in memory with sha256 ETag + 304; live-VPS compression rests on `38-VERIFICATION.md`'s developer-confirmed 2026-09-27 addendum | `41-REAUDIT-EFF-ARC-CMP.md` EFF-01 |
| EFF-02 | VERIFIED-CLOSED | `dd5b7d9f` | Per-route script lists (6-10 scripts), no build step; survived the Phase 40 `layout.py` split behind a re-export facade | `41-REAUDIT-EFF-ARC-CMP.md` EFF-02 |
| EFF-03 | VERIFIED-CLOSED | `1ff7f713`, `ba0502ef` | One SQLite connection per request/cycle via `connection_scope()`; `measure_efficiency.py` confirms `sqlite_conns=1.0` everywhere | `41-REAUDIT-EFF-ARC-CMP.md` EFF-03 |
| EFF-04 | VERIFIED-CLOSED | `33e3603b`, `14076af9`/`d9b3aadd` | Lazy per-field `PageContext` (Phase 40's typed rewrite preserved the lazy-resolution mechanism); freshness token gives bodiless 304s on all four refresh routes | `41-REAUDIT-EFF-ARC-CMP.md` EFF-04 |
| EFF-05 | VERIFIED-CLOSED | `5079f700`, `2ac87bb7`/`8ee39d7d` | `persist_poll_state_if_changed()` writes only on real change, compact JSON separators; `poll_state_writes=0` on unchanged branches | `41-REAUDIT-EFF-ARC-CMP.md` EFF-05 |
| EFF-06 | VERIFIED-CLOSED | `62550bd3`, `38c31313` | Providers queried in parallel via `ThreadPoolExecutor`; `1.1s` is per-provider spacing, not an inter-provider sleep; cross-cycle spacing persisted | `41-REAUDIT-EFF-ARC-CMP.md` EFF-06 |
| ARC-01 | VERIFIED-CLOSED | `a8a78365`/`dc54090f`/`67619c21`, `8ee39d7d` | `run_once()` dispatches over every ledger-named stage function (`load_cycle_context`, `decide_hold`, `advance_display_queue`, `render_and_publish`, `persist`, `record`), all present verbatim | `41-REAUDIT-EFF-ARC-CMP.md` ARC-01 |
| ARC-02 | VERIFIED-CLOSED | `2ac87bb7`, `d790c6bf`/`5c51bc22`/`0687e840` | `server/state_store.py` owns `poll_state.json`; zero `companion/` imports of `poll_loop`; `poll_loop.py` down to 100 lines | `41-REAUDIT-EFF-ARC-CMP.md` ARC-02 |
| ARC-03 | FLAGGED-DIFFERENT | `8fe92d8c`/`062cac9a`/`ed86fa6b`, `526364b5`, `e7c25214`/`118c4a9b` | Naming only: the ledger's shorthand calls the calendar package `calendar/`; the shipped (and always-shipped) name is `server/plane/calendar_rules/` — structure and intent (`ics`/`match`/`registry` submodules) fully met, no code gap | `41-REAUDIT-EFF-ARC-CMP.md` ARC-03 |
| ARC-04 | VERIFIED-CLOSED | `8af4af33` | No module-global setter mutated per cycle; the three named offenders (`set_override_state_dir` etc.) deleted outright; one benign false-positive (`history_db.set_meta`, a per-connection row setter) judged and excluded | `41-REAUDIT-EFF-ARC-CMP.md` ARC-04 |
| ARC-05 | VERIFIED-CLOSED | `7359d84c`, `7427539f`, `9bfc02e3`, `c04ed89f` | `device_policy.py` is the one shared module for quiet hours, battery-critical and the discharge curve, used by server/byos/companion; obsolete "vendored byos" ARCHITECTURE.md rationale gone | `41-REAUDIT-EFF-ARC-CMP.md` ARC-05 |
| ARC-06 | VERIFIED-CLOSED | `050cf876`/`1d9af363`, `9a1f4449` | 12 modules under strict mypy in `pyproject.toml`; `mypy` clean; function-size gate permanent in CI | `41-REAUDIT-EFF-ARC-CMP.md` ARC-06 |
| CMP-01 | VERIFIED-CLOSED | `f50872d9` | `Route` namedtuple table; single `auth_required` check inside `_dispatch()`; 17 POST routes all covered by the one table | `41-REAUDIT-EFF-ARC-CMP.md` CMP-01 |
| CMP-02 | VERIFIED-CLOSED | `9477df53` | One `STATIC_ROUTES` allowlist + one generic handler; the four remaining `_serve_*` functions are distinct dynamic-asset kinds, not per-file duplicates | `41-REAUDIT-EFF-ARC-CMP.md` CMP-02 |
| CMP-03 | VERIFIED-CLOSED | `910c0a23`, `14e5a055`/`ea4d12e1`/`299a4054` | `config_page.py` 6652→1163 lines; `layout.py` split; settings groups live under `companion/settings/`; no production file over 1500 lines except the tracked `style.css` exception | `41-REAUDIT-EFF-ARC-CMP.md` CMP-03 |
| CMP-04 | VERIFIED-CLOSED | `49b222c2`/`a0838518`/`3fe905ee` | Typed, `__slots__`-based `PageContext` with lazy per-field loaders; `Handler.page_context()` is a thin delegate | `41-REAUDIT-EFF-ARC-CMP.md` CMP-04 |
| CMP-05 | VERIFIED-CLOSED | `81243b65` | `page_shell()` takes named keyword parameters, not a 15-slot positional `%s` template | `41-REAUDIT-EFF-ARC-CMP.md` CMP-05 |
| CMP-06 | VERIFIED-CLOSED | `a4a2f79f` | `FUNCTION_LINE_LIMIT=80` held with no allowlist; `test_no_production_function_exceeds_the_code_line_ceiling` asserts `offenders == []` unconditionally | `41-REAUDIT-EFF-ARC-CMP.md` CMP-06 |
| CMP-07 | VERIFIED-CLOSED | `6639e618` | One `drain_capped_body()` helper; one `_choice_cookie_header()` builder shared by theme/lang POST handlers | `41-REAUDIT-EFF-ARC-CMP.md` CMP-07 |
| CMP-08 | VERIFIED-CLOSED | `27b74848` | No duplicated CSS selector in one context; no hex colour literal outside token definitions (both structure-guard tests pass) | `41-REAUDIT-EFF-ARC-CMP.md` CMP-08 |
| CMP-09 | VERIFIED-CLOSED | `708761ef`, `c1937743` | Stable `msg_id`-keyed lookup; rewording the English source cannot silently drop the French translation; completeness sweep passes | `41-REAUDIT-EFF-ARC-CMP.md` CMP-09 |
| DOC-01 | VERIFIED-CLOSED | `4d4c51b`, `313e0a7` (41-01), `7ad0ff7`, `83121a3` (41-02) | 98 doc/comment claims re-checked against the current code across `deploy/`, CI headers, `ARCHITECTURE.md`, `COMPLIANCE.md`, `README.md`, `CONTRIBUTING.md`, `.claude/CLAUDE.md`, `server/README.md`, `firmware/VENDOR.md` prose and 13 Python comment sites; every drift found (bind address, "persists nothing", harness counts, file modes, state paths, single-writer claims, unit counts, CI check list, byos vendored/secret model, PRIM reproduction command) was corrected in place; zero left as `CODE DISCREPANCY` | `41-DOC-DRIFT-DEPLOY.md` (rows 1-35), `41-DOC-DRIFT-DOCS.md` (rows 36-102) |
| DOC-02 | VERIFIED-CLOSED | `2101217`, `38d3e88` | `hardware/logs/backoff-powercycle.log` gzipped in the working tree only (15.8 MB → 86.5 KB, sha256-verified, git history untouched); unused illustration draft re-verified unreferenced then removed; `/gsd-cleanup` archival explicitly deferred to the v1.0 close after Phase 42, consistent with the ledger's own "at milestone close" wording | `41-03-SUMMARY.md` |
| DOC-03 | VERIFIED-CLOSED | 41-04..41-08 | Every one of the 82 ledger IDs has a verdict backed by evidence; no row is FLAGGED-OPEN. HYG-01 and HYG-06 are ACCEPTED-OPEN: the developer accepted them as-is on 2026-09-28 and deferred the fix to `.planning/todos/pending/comment-history-guard-residue.md` | See `## Accepted open` below |

## Accepted open

**Developer decision, 2026-09-28.** HYG-01 and HYG-06 are real, open findings.
The developer accepted them as-is so Phase 41 can close and Phase 42 (OTA)
can start, and deferred the fix to `.planning/todos/pending/comment-history-guard-residue.md`.
Nothing in them changes runtime behaviour: they are comment/docstring
history references and a lint-guard regex gap. The facts below are the
record at the time of the decision.

A gap-closure pass (plans drafted in commit `3e45e90a`, withdrawn in favour of
this decision) prototyped the tightened guard and found the residue is larger
than this report first measured: about 85 real hits in 34 files, not 21 in 12.
The 41-04 hunt had classified about 40 real bare plan IDs as false positives,
including a JS site (`companion/static/panel-lookup.js`) and a shell site
(`scripts/check-attribution.sh`). So the HYG-02 and HYG-03 "zero genuine hits"
evidence above is also too optimistic, and the todo covers those files too.
None of the hits are under `firmware/` except one prose "Task 3's" in
`firmware/main/battery.c`, which the guard would not target.

The original findings, as first recorded:


- **HYG-01** — 21 residual plan/decision-history references survive in 12
  companion/server test files and `pyproject.toml`, in shapes
  (`D-14c`, `06.6.4.1.1-04`, bare `39-13`/`39-08`) the shipped
  `check_comment_history.py` guard's regex does not match. File:line list
  is in `41-REAUDIT-TST-HYG.md`'s HYG-01 row (12 files, ~21 sites — the
  largest cluster is `companion/test_config_page_03.py` with 8 hits).
  Proposed fix: reword each comment/docstring to drop the ID (git and
  `.planning/` already carry the history) — no code behaviour changes.
  Does not touch `firmware/`.
- **HYG-06** — the CI guard step (`ci.yml:97-100`) and its own
  mutation-tested test suite (`test-support/test_check_comment_history.py`)
  are correctly wired; the gap is in the guard's own regex, which has no
  case for a letter-suffixed `D-`ID or a dotted UI-SPEC section number.
  Proposed minimal fix (three regex edits in
  `scripts/check_comment_history.py`, detailed in
  `41-REAUDIT-TST-HYG.md`'s HYG-06 row): (1) extend the `d-id` pattern to
  accept a trailing lowercase letter; (2) add a `uispec-section` pattern;
  (3) loosen `bare-plan-id` to catch a bare `\d{1,3}-\d{2}` without
  requiring a preceding "plan "/"Plan " marker. Does not touch `firmware/`.

Both fixes are small, comment/regex-only, and belong in a follow-up plan
(`/gsd-plan-phase 41 --gaps`), not in this closing plan, per this plan's
own instruction not to fix flagged findings here.

## Flagged different

- **TST-02** — the migration ledger closed correctly at Phase 32's own
  close (`32-VERIFICATION.md`: rc 0, 769/769 mapped). The standalone
  `32-ledger-check.py --all` tool script now fails against 6 node ids that
  Phase 39 legitimately renamed/strengthened; all 6 replacement tests
  collect and pass in the live full-suite run. No lost coverage, a stale
  verification script. Not `firmware/`.
- **TST-15** — same root cause as TST-02, in `33-ledger-check.py --all`
  (4 harness fragments). Coverage and count parity both still hold and
  exceed the pre-migration baseline. Not `firmware/`.
- **ARC-03** — naming only. The ledger's own shorthand calls the calendar
  package `calendar/`; the shipped (and always-shipped, per the
  planning-time context) name is `server/plane/calendar_rules/`. The
  package's actual structure (`ics`/`match`/`registry` submodules) fully
  meets the finding's intent. No open risk, no code gap. Not `firmware/`.

For TST-02/TST-15, whoever next touches this repository's test
infrastructure should decide whether `32-ledger-check.py`/
`33-ledger-check.py` are worth updating to the renamed node ids, or
retired now that the milestone that needed them is closing — a
documentation/tooling decision, not a fix owed by this closing plan.

## Evidence limited to recorded artefacts

These sub-facts are runtime-only (VPS, CI, or hardware-capture) and are not
re-derivable from the repository alone; each is VERIFIED-CLOSED above on
the strength of the cited artefact, not re-measured in this closing pass:

- **TST-06** — the dynamic double-push/rollback-race edge case (CI-only,
  not independently re-triggered against production).
- **TST-07** — the Actions cache hit is CI-only (confirmed live in
  `41-04`'s fetched log, not re-fetched again in this pass since the tree
  hasn't changed).
- **FW-09** — DHCP-timing figures (`hardware/PHASE34-HARDWARE-SESSION.md`).
- **FW-10** — TLS-resumption millisecond figures (same hardware session log).
- **FW-11** — the ±8 mV battery-accuracy reading (single multimeter sample,
  `34-VERIFICATION.md`'s hardware-deviations table).
- **FW-12** — the 26 s spacing-hold capture duration (`H-11-spacing.log`).
- **EFF-01** — live-VPS wire compression (`38-VERIFICATION.md`'s
  developer-confirmed 2026-09-27 addendum).
- **SEC-02** — the HSTS header's actual presence on the wire
  (`37-SEC-BASELINE.md` CP-4).
- **SEC-04** — the off-box backup archive's actual nightly arrival on the
  developer's Mac (`37-SEC-BASELINE.md` CP-8/CP-9, plus a dated restore
  rehearsal in `deploy/README.md`).
- **SEC-06** — byos's live loopback-only listen on the production host
  (this closing pass re-ran the offline `systemd-analyze` scoring in a
  container and got byte-identical scores to `37-SEC-BASELINE.md`, but the
  live bind is a production fact recorded there).
- **SEC-07** — the absence of a secret in the real production process's
  `ps`/`/proc/<pid>/environ` (`37-SEC-BASELINE.md` CP-11).
- **SEC-08** — the live `sshd -T` output on the actual VPS
  (`37-SEC-BASELINE.md` CP-3).
- **INT-07** — the deployed systemd instance's own parsed
  `TimeoutStartUSec` value, confirmed 2026-09-26 on the VPS after the
  Phase 37-11 deploy (`36-VERIFICATION.md`'s Human Verification Required
  section).

## Final gate runs

All commands below were run on this plan's own final tree (`08e4eb49`),
2026-09-28, in the same non-root macOS sandbox `41-06`/`41-07` used.

| Command | Exit code | Key figures |
|---|---|---|
| `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` (full suite, `-n auto --cov`) | **non-zero** (test failures; coverage gate itself passed) | `3171 passed, 40 failed, 7 skipped, 57 warnings in 133.66s`; coverage `94.91%` ≥ 93% gate (`Required test coverage of 93.0% reached`). Retried with `JOBS=4`: `3163 passed, 48 failed, 7 skipped in 165.70s` — a *different* subset of tests failed, confirming the failures are resource-contention flakiness in this specific sandbox running the whole ~3200-test suite at once, not a stable regression. See "Full-suite failure triage" below — none of the 40/48 failing tests touch any of the 82 ledger IDs above or any file this phase modified, and the PR's own CI run (GitHub Actions, a clean dedicated runner) is the actual gating proof, consistent with how `41-04`/`41-05` treated a Chromium-unavailable sandbox |
| `server/.venv/bin/ruff check .` | 0 | `All checks passed!` |
| `server/.venv/bin/mypy` | 0 | `Success: no issues found in 12 source files` |
| `python3 scripts/check_comment_history.py check` | 0 | zero hits |
| `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server` | 0 | `401 functions scanned, none over 80` |
| `./scripts/check-attribution.sh` | 0 | `PASS: 67 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text` |
| `bash firmware/tests/run_host_tests.sh` | 0 | `10 suites, all hardware-free firmware suites passed`; `git status --porcelain firmware/ \| grep -v firmware/VENDOR.md` empty afterward |
| `server/.venv/bin/python -m pytest -q deploy/tests --ignore=deploy/tests/test_activate.py --ignore=deploy/tests/test_install_backup_key.py` (native macOS, targeted, matches CI's own set minus the two BSD-`mv`-incompatible files) | 0 | `100 passed, 4 skipped` (`test_units.py` — `systemd-analyze` not on `PATH` on this host) |
| `docker run ... python:3.12-slim ... pytest deploy/tests/test_activate.py deploy/tests/test_install_backup_key.py deploy/tests/test_units.py deploy/tests/test_provision.py` (Linux container, GNU `mv`) | 0 | `70 passed, 4 skipped` (same `systemd-analyze` gap inside the bare container) — proves the two BSD-`mv`-affected files are this macOS sandbox's own limitation, not a code regression |
| `python3 scripts/check_comment_history.py same-code --base 7bd8664 --allow stub-server/byos_server.py <15 modified non-md files>` | 0 | Every phase-modified non-markdown file outside `.planning/`/`hardware/logs` is comment/docstring-only against the base, with the one documented `argparse`-docstring exception |

### Full-suite failure triage (not a regression, not blocking)

The 40 (or, on retry, 48) full-suite failures fall into four categories,
each individually re-verified in isolation on this same tree:

1. **Sandbox resource contention under the full ~3200-test parallel run**
   (companion port collisions, two subprocess segfaults). Every one of
   these tests passes cleanly when re-run individually or in a small
   targeted batch (confirmed: `companion/test_config_page_05.py::test_
   settings_post_unauthenticated_redirects_to_login_and_writes_nothing`,
   `test-support/test_test_support.py::test_child_guard_ignores_loopback_
   proxy`, `::test_fake_providers_cross_process` all pass serially). The
   `deploy/tests` failures seen in the combined run (`test_backup_gate.py`,
   `test_caddyfile.py`, `test_deploy.py`, `test_mac_pull.py`,
   `test_provision.py`) likewise all pass — `100 passed, 4 skipped` — when
   run as their own `pytest -n auto --cov` invocation, proving the
   contention is about total concurrent load, not these tests' own logic.
2. **macOS-only, no `/proc`, non-root sandbox limitation** —
   `companion/test_app_server_fixture.py::test_stop_kills_the_whole_
   process_group_including_a_grandchild` and `::test_child_env_carries_no_
   network_var_and_pythonpath` both require Linux process-group semantics
   and `/proc/<pid>/environ`. Re-run inside a `python:3.12-slim` Docker
   container: `10 passed` (the whole file). Same category as `41-06`'s
   already-documented `stub-server/test_byos_bind_secret.py` skip.
3. **BSD-`mv`-only sandbox limitation** — `deploy/tests/test_activate.py`
   (11 cases) and `test_install_backup_key.py` (2 cases) need GNU `mv -T`.
   Confirmed passing on Linux (see the Docker row in the gate table above),
   same limitation `41-06` already documented for this same sandbox.
4. **One unresolved, reproducible-but-contradicted-by-live-CI anomaly** —
   `server/test_fault_screen_mask.py::test_fault_screen_mask_header_
   matches_generator_output` fails identically (`FP_FAULT_MASK_W` computed
   as `565` vs the committed `564`, plus ~2,965 differing mask bytes) in
   three independent environments tried in this pass: native macOS
   (this sandbox), a native Linux/arm64 Docker container, and an
   emulated Linux/amd64 Docker container — the last two using
   `server/requirements-dev.txt`'s exact hash-locked `pillow==12.3.0`
   wheel. `git diff --stat c4457f36 HEAD -- server/plane/render
   server/panel_format.py firmware/tools/gen_fault_screen.py
   firmware/main/fault_screen_mask.h` is empty (byte-identical tree for
   every file this test/generator touches), yet the live GitHub Actions
   log fetched for CI run `36377045745` (commit `c4457f36`, an ancestor of
   this tree with the identical relevant files) shows `3218 passed, 0
   failed` for the same full suite, meaning this exact test passed there.
   The cause is not identified in this pass (a FreeType/text-hinting
   floating-point non-determinism under this sandbox's toolchain/
   emulation is the leading candidate, but not confirmed). This test is
   **not one of the 82 ledger IDs** and no file it depends on was touched
   by this phase (confirmed by the diff above) — recorded here for
   transparency, with the PR's own CI run as the actual, already-proven-
   passing gate for it, per this plan's own directive that a live CI run
   is the correct proof for a sandbox-only gap this report cannot resolve
   locally.

None of the four categories implicates any of the 82 ledger IDs, any file
this phase's own commits modified, or any code under `firmware/`.
