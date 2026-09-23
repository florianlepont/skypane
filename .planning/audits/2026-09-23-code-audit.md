# Code audit — 2026-09-23

Whole-repository audit of code quality, efficiency and software architecture,
run on `main` at `2808f8a` by four parallel read-only reviews (firmware,
server pipeline, companion app, infra/tests/CI), with the headline findings
re-checked by hand against the code. The developer asked for **100 % of the
findings, low severity included**, to be remediated **inside milestone v1.0**
(phases 32–41), not deferred to a later milestone.

This file is the ledger. Every finding has one stable requirement ID; the
same IDs appear in `REQUIREMENTS.md` (section "Audit remediation") and in the
ROADMAP entries of phases 32–41. Phase 41 closes the ledger by re-verifying
every row against the code.

## Decisions taken with the developer (2026-09-23)

| # | Question | Decision |
|---|----------|----------|
| D-A1 | Secrets in device flash | **Per-device enrolment secret**, and byos refuses to re-enrol a known MAC. No flash/NVS encryption (burns eFuses, irreversible). |
| D-A2 | Test framework | **Full migration to pytest** (dev-only dependency; production stays stdlib + Pillow + requests). Replaces the 24 hand-rolled harnesses, `run_all_tests.py`'s hand list and every `EXPECTED_CHECK_COUNT`. |
| D-A3 | Comment volume (55–85 % of lines, mostly plan/ticket history) | **Purge in the source**: keep only the *why* and the invariants; history lives in git and `.planning/`. **Everything in English** — code, comments, docstrings, docs, commit messages. The UI stays bilingual FR/EN. |
| D-A4 | Python version | **CI aligned on production** (the distro `python3` the VPS runs). |
| D-A5 | Milestone | Remediation is **v1.0 scope**, phases 32–41. |
| D-A6 | Git history | No history rewrite (the 15 MB log stays in past commits); only the working tree is cleaned. |

## Measured baseline

- Suite: 2018/2018 checks pass as a non-root user in ~221 s wall
  (`test_browser_ux.py` alone sets the wall time); fails as root (3 harnesses);
  browser harnesses print `SKIP` and report `PASS` when Chromium is missing.
- Coverage 93 % (gate 83); `companion/app.py` and `stub-server/byos_server.py`
  excluded from measurement.
- Test code ≈ 62 k lines vs ≈ 17 k lines of production *code* (3.6 : 1).
- Comments/docstrings: 55–78 % of non-blank lines in `server/`, 57–68 % in
  `companion/` Python; `companion/static/style.css` is 510 KB of which 432 KB
  are comments.
- Poll cycle without network: ~160 ms first render, 26–32 ms repeat,
  3–6 ms empty sky; import cost 90–120 ms. Network waits dominate, plus a
  fixed 1.1 s sleep.
- Firmware no-change wake ≈ 4.4 s, of which ≈ 3.0 s is DHCP.

## Phase 32 — Test foundation: pytest and CI you can trust

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| TST-01 | 24 hand-rolled harnesses, no test selection, no fail-fast, parallelism per file only (`scripts/run_all_tests.py`) | pytest + pytest-xdist + pytest-cov as dev deps in `server/requirements-dev.txt`; config in `pyproject.toml`; shared fixtures in `conftest.py`; coverage gate moves to pytest-cov; CLAUDE.md stack row and CONTRIBUTING updated |
| TST-02 | Server-side harnesses (`server/test_*.py` ×14, `stub-server/test_poll_cycle.py`) | Migrated to pytest; every old check mapped in a migration ledger (old check name → new test id, or deletion with a reason) |
| TST-03 | `/poll-now` tests call live adsb.fi / adsb.lol / adsbdb (`companion/test_companion_app.py` ~10771 → real `poll_loop.run_once`) | Injectable fake provider fixture; a conftest guard fails any test that opens a non-loopback socket |
| TST-04 | CI tests Python 3.12, production runs the distro `python3` (3.14 on Ubuntu 26.04, `deploy/provision.sh:62-71`); ruff targets py311 | CI (and ruff `target-version`) on the production version |
| TST-05 | Firmware host tests (`firmware/tests/run_host_tests.sh`, 0.35 s) never run in CI | Run them in `firmware.yml` |
| TST-06 | CI concurrency: workflow group held by a run waiting for deploy approval queues the next push's tests; deploy group `cancel-in-progress: true` can kill a half-done rsync (`ci.yml:110-112`) | Separate test and deploy concurrency groups; never cancel an in-flight deploy |
| TST-07 | Chromium downloaded with `--with-deps` every run, no cache | `--only-shell`, cache `~/.cache/ms-playwright` |
| TST-08 | Only direct deps pinned; urllib3/certifi/idna float; no hashes | Hash-pinned lock files for runtime and dev deps |
| TST-09 | `companion/app.py` and `byos_server.py` excluded from coverage; gate 10 points below measured | Subprocess coverage (`patch = ["subprocess"]`), then raise `fail_under` to the measured floor |

## Phase 33 — Companion tests on pytest, behaviour over source text

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| TST-10 | Companion harnesses (`test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_i18n.py`, `test_contrast_check.py`); `Harness` copied ×5, `http_request` ×6, `_NoRedirectHandler` ×4 | Migrated to pytest; one app-server fixture replaces every copy |
| TST-11 | Browser harnesses (`test_browser_ux*.py`) skip silently and count as PASS when Chromium is missing (`test_browser_ux.py:22-29`) | pytest-playwright; a missing browser is a failure in CI; parallelised per test with xdist |
| TST-12 | Tests assert implementation text: 309 checks read source files, 77 read `style.css` as text, some assert comments contain ticket IDs (`test_status_pages.py:8394`), some read `.planning/*.md` / `UI-SPEC.md` (`test_status_pages.py:8401-8412`, `test_config_page.py:8595-8628`) while CI `paths-ignore`s those files | Each rewritten as a behaviour or parsed-DOM assertion, or deleted with a stated reason in the migration ledger. No test reads `.planning/` or asserts on comments |
| TST-13 | Suite not root-safe (`chmod` read-only checks in `test_manual_resolutions.py`, `test_companion_app.py`, `test_status_pages.py`); `anomaly_active("/nonexistent/...")` creates that directory on the host as root (`test_status_pages.py:8201`) | Permission tests skip under euid 0; every path inside `tmp_path` |
| TST-14 | `HARNESSES` hand list (`run_all_tests.py:65`) and dozens of hand-maintained `EXPECTED_CHECK_COUNT` redefinitions | `run_all_tests.py` and all check counts retired; pytest discovery; `scripts/run-all-tests.sh` becomes a thin pytest wrapper |
| TST-15 | Migration must not lose coverage | Closing parity: every one of the 2018 pre-migration checks accounted for in the ledger; coverage ≥ pre-migration figure |

## Phase 34 — Firmware: resilience, power, security, cleanup (one hardware session)

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| FW-01 | Crash/brownout/WDT reset skips backoff: no `esp_reset_reason()`; next boot labelled `power-on` and polls at once (`app_main.c:52-53,118-124,132`); `ESP_ERROR_CHECK` in `epd13in3e.c:167,172,185,192` | Reset reason checked at boot → increment `FP_NVS_BACKOFF_N` and sleep; `epd_init` returns errors |
| FW-02 | Watchdog inert: `CONFIG_ESP_TASK_WDT_PANIC` unset, no `esp_task_wdt_add`; comment at `sdkconfig.defaults:21-23` wrong; no bound on total awake time (download loop `api_client.c:420-427`) | Whole-wake deadline (one-shot `esp_timer` → deep sleep with backoff) and a real WDT; comment corrected |
| FW-03 | A rejected token is never replaced: 401 → `step=status` → backoff forever (`state_machine.c:36-53`) | 401/403 clears `FP_NVS_DEVICE_TOKEN`; next wake re-enrols; distinct error code |
| FW-04 | `sleep_s` accepted up to 2^32−1 s (`api_client.c:316-319`) | Cap at 86400 s; above → JSON error |
| FW-05 | Unchecked returns: `esp_http_client_write`/`fetch_headers` (`api_client.c:154-156`), `busy_wait("POF")` (`epd13in3e.c:265`) | Checked and mapped to the right `step=` |
| FW-06 | Host tests cover only backoff/panel guard/divider/dead `api_base` | Response validation (hash, URL, `sleep_s`, `led_enabled`, token), size/SHA gate and the sleep decision extracted into pure helpers with host tests |
| FW-07 | `url_valid` accepts `http://` (`api_client.c:87`); full public CA bundle | https-only in production builds; custom bundle with the ISRG roots only |
| FW-08 | Shared setup secret not bound to a device; anyone holding it can re-enrol a MAC and revoke its token (`byos_server.py:140-157`) — decision D-A1 | Per-device enrolment secret; byos refuses re-enrolment of a known MAC |
| FW-09 | DHCP ≈ 3.0 s of a 4.4 s wake (`hardware/logs/backoff-run.log`; `wifi.c:104-147`) | `CONFIG_LWIP_DHCP_RESTORE_LAST_IP`, no ARP check (or static IP); measured on hardware |
| FW-10 | Fresh TLS handshake per request, no session reuse (`api_client.c:204-221,281-296,403-433`); ~28 s unexplained per-cycle overhead (`hardware/BATTERY-RUN.md:333-345`) | One keep-alive client for display + image; TLS session tickets in RTC memory; wake duration logged (diagnostic line, Log Line Contract untouched); overhead explained |
| FW-11 | Battery read with radio on, single sample (`api_client.c:137`, `battery.c:107`) | Read once before Wi-Fi, 8-sample average |
| FW-12 | PSRAM memtest every boot (~446 ms); 800 µs busy-wait per row (`epd13in3e.c:234`, ~2.6 s/blit); up to 90 s fully awake waiting for refresh spacing (`panel.c:97`) | `CONFIG_SPIRAM_MEMTEST=n`; shorter row wait if the datasheet allows; timed light sleep during the spacing wait |
| FW-13 | Upstream leftovers: `api_base.c` compiled but unused while `api_base_get` doesn't normalise (trailing slash → `//device`); `fp_api_post_logs` unused; `reset` field required then ignored (`api_client.c:330`); orphan `CONFIG_FP_PROVISION_TIMEOUT_S`/`FP_FACTORY_PREP`; rollback enabled without `esp_ota_mark_app_valid*` | Use `fp_api_base_normalize` or delete; delete dead code; drop orphan symbols; rollback disabled until OTA exists |
| FW-14 | Duplication: hex check ×2 (`api_client.c:66-71,235-240`); NVS open/read/close ×3; HTTP client config ×3 | One helper each |
| FW-15 | `PROJECT_VER "0.1.0-p1"` never bumped (`CMakeLists.txt:13`) | Derived from `git describe` |

## Phase 35 — Comment purge (English only) and dead code

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| HYG-01 | Python comments/docstrings 55–78 % of lines, ~2 100 plan/decision references (e.g. `app.py:3242` 40-line docstring over one line; `run_once` ~620 comment lines of 952) | Keep what the code does, the *why* and invariants; drop plan/ticket history |
| HYG-02 | `style.css` 432 KB comments of 510 KB; JS files mostly comments (`freshness.js` 644/1073) | Same purge in CSS and JS |
| HYG-03 | C, shell, systemd, Caddyfile, env example comments | Same purge |
| HYG-04 | Language rule not written down (D-A3) | English-only rule for code, comments, docs and commits in CLAUDE.md and CONTRIBUTING.md |
| HYG-05 | Dead Python: `health_page.health_severity` (:2241), `anomaly_active` (:2267), `draw.usable_pairs` (:294), `draw.label_grid` (:692); comments about removed features (`app.py:3450,3514`, `auth.py:63`) | Deleted |
| HYG-06 | Nothing prevents the history from coming back | Lint guard in CI rejecting plan/ticket IDs in comments (e.g. `\d{2}-\d{2}-PLAN`, `D-\d+`, `WR-\d+`) |

## Phase 36 — State integrity and device protocol

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| INT-01 | Two processes write `poll_state.json`/`panel.bin` (timer oneshot + companion `/poll-now`, `app.py:3310`); `_POLL_LOCK` is a thread lock only (`app.py:699`); reproduced 14/36 exceptions over 200 concurrent saves | `fcntl.flock` on `state/poll.lock` around `run_once` |
| INT-02 | ~11 copies of atomic write with fixed `path + ".tmp"` (`poll_loop.py:727,754`, `device_config.py:958`, …) | One `atomic_write(path, data)` with unique temp names |
| INT-03 | `save_device_config` read-modify-write without lock (`device_config.py:910-970`) | Thread lock + flock |
| INT-04 | Theme preview temp name shared across threads (`theme_preview.py:371`); cache never pruned; `lru_cache(maxsize=None)` keyed by mtime (`illustration_normalize.py:134`) | `mkstemp`, pruning, bounded cache |
| INT-05 | `/img/<sha>.bin` ignores the sha and serves the current panel (`byos_server.py:718-728`) → SHA mismatch on the device if the panel changes mid-wake | Content-addressed `state/img/<sha>.bin` (last N kept); 404 on unknown hash |
| INT-06 | byos: negative/huge `Content-Length` blocks a thread forever, no socket timeout (`:557-562`); non-string `mac` crashes the handler (`:588`); token compared with `in values()` (`:564-567`) | Validated length, `Handler.timeout`, typed input, `hmac.compare_digest` |
| INT-07 | `skypane-poll.service` oneshot has no start timeout; `requests` timeouts are per-read | `TimeoutStartSec`; total deadline per HTTP call |
| INT-08 | adsbdb 429/5xx/timeouts cached as permanent misses; FIFO eviction (`enrich.py:398-408,926`) | Miss only on 404/empty route; TTL (misses ~1 day, hits ~30 days); LRU |
| INT-09 | Caddy log tailer skips a partial last line but advances past it (`history_db.py:613`); corrupt offset / out-of-range `ts` raise uncaught (`:705`) | Advance to last newline; errors caught |
| INT-10 | Non-dict provider JSON → `AttributeError` fails the cycle (`detect.py:413-416`) | Type-checked |
| INT-11 | `main()` logs type + message only (`poll_loop.py:1980`) | Full traceback |
| INT-12 | `last_synced_at` uses `datetime.now()` not the injected clock (`calendar_rules.py:1945`); flock held across the network fetch | Injected clock; lock released during fetch |
| INT-13 | A queued detection doesn't update "last detection" (`poll_loop.py:1796`) | Updated |
| INT-14 | SSRF docstring claims DNS-rebinding protection that `requests` re-resolution defeats | Pin the resolved IP for the connection (or correct the claim) |

## Phase 37 — Security and operations

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| SEC-01 | Process-global `LoginThrottle` (`auth.py:301`): 5 wrong guesses from anyone lock the owner out, repeatable | Per-client-IP throttle (trusted `X-Forwarded-For` from loopback Caddy) |
| SEC-02 | No HSTS (`deploy/Caddyfile`) | `Strict-Transport-Security` |
| SEC-03 | CSRF relies on `SameSite=Strict` alone (`app.py:3480`) | `Origin`/`Sec-Fetch-Site` check on every POST |
| SEC-04 | No backup of `/opt/skypane/state` (history.db, tokens, config); README claims it is reproducible (`deploy/README.md:267-269`) | Nightly `sqlite3 .backup` + off-box copy; README corrected |
| SEC-05 | `deploy.sh` rsyncs while services run, no health check; units and Caddyfile never deployed | Release dir + symlink swap (or timer stopped); post-deploy `systemctl is-active` + HTTP probes fail the job; units/Caddyfile deployed with `daemon-reload` |
| SEC-06 | systemd hardening incomplete; byos binds 0.0.0.0 | `CapabilityBoundingSet=`, `PrivateDevices`, `ProtectKernel*`, `RestrictAddressFamilies`, `SystemCallFilter=@system-service`, `UMask=0027`; byos `--bind 127.0.0.1` + `IPAddressDeny=any`/`IPAddressAllow=localhost` |
| SEC-07 | byos secret on the command line (`skypane-byos.service:22`); env file owned by the service user; `DEPLOY_HOST_KEY` interpolated into script (`ci.yml:136`) | Secret via env; env file `root:root 600`; secret passed through `env:` |
| SEC-08 | SSH hardening edits main `sshd_config` only (`provision.sh:159-164`); no `PermitRootLogin`, no `sshd -t` | `sshd_config.d/00-skypane.conf`, `PermitRootLogin no`, validated |

## Phase 38 — Efficiency (measured before and after)

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| EFF-01 | No compression in Caddy; no ETag/Last-Modified (`app.py:1269`); static files re-read per request (`app.py:1957`) | `encode zstd gzip`; validators + 304; static bytes cached in memory |
| EFF-02 | 15 `<script defer>` on every page (`layout.py:3147-3161`) | Only the scripts each page uses (no build step) |
| EFF-03 | 16 SQLite connections per page request, each running PRAGMAs + `init_schema` + commit (`history_db.py:196-201`); 3 per poll cycle, 6 commits | One connection per request/cycle; schema once per process; one transaction |
| EFF-04 | `page_context` reads 6+ JSON files and builds full Health markup just for a severity (`health_page.py:2095-2200`); `freshness.js` refetches the whole page every 45 s (`:170`) | Lazy context; severity computed without markup; light freshness endpoint |
| EFF-05 | `poll_state.json` saved twice per cycle in some branches (`:1305/:1341`, `:1790/:1860`), `indent=1`, even when unchanged | Saved once, only if changed, compact |
| EFF-06 | Fixed 1.1 s sleep between two *different* providers (`detect.py:143`) | Providers queried in parallel, per-provider rate limit kept |

## Phase 39 — Server architecture

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| ARC-01 | `run_once` 952 lines, CC 38; render→pack→write→gallery ×4 (`poll_loop.py:989-1940`) | `load_cycle_context` / `decide_hold` / `advance_display_queue` / `render_and_publish` / `persist` / `record` over a `CycleContext` dataclass |
| ARC-02 | Companion imports the entrypoint `server.poll_loop` as a library | `server/state_store.py` owns `poll_state.json`; companion imports it |
| ARC-03 | `render.py` 2932 lines, `calendar_rules.py` 2221, `device_config.py` mixes persistence/themes/quiet hours; `notify.py:188` imports private `calendar_rules._url_is_safe` | `render/{layout,text,hold_screens,cli}`, `calendar/{ics,registry,match}`, `themes.py`, shared `net/safe_fetch.py` |
| ARC-04 | Module-global setters mutated every cycle (`poll_loop.py:1074-1086`) | Explicit injection |
| ARC-05 | Duplicated logic: quiet hours (`device_config.py:983` / `byos_server.py:294`), battery critical (`wake.py:96` / `byos_server.py:219`), battery curve (`poll_loop.py:492` / `companion/battery.py`); "vendored byos" rationale obsolete (`ARCHITECTURE.md:327`) | One shared module used by server, byos and companion |
| ARC-06 | 0 of 281 server functions typed | Type hints on the pure core; mypy in CI |

## Phase 40 — Companion architecture

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| CMP-01 | `do_GET`/`do_POST` if-chains with ~20 hand-repeated `require_session()` (`app.py:2901,3453`) | Route table `(method, matcher, handler, auth_required)` |
| CMP-02 | 17 route constants + 17 paths + 17 `_serve_*` + 17 branches for static files (`app.py:161-236,665-682,1998-2141,2924-2977`) | One `{route: path}` allowlist |
| CMP-03 | `config_page.py` 6652 lines, `layout.py` 4168 | Split by settings group / by responsibility |
| CMP-04 | `page_context()` god dict (`app.py:1476-1708`) | Typed per-page context |
| CMP-05 | `page_shell` with 15 positional `%s` (`layout.py:2917,3147-3161`) | Named templates |
| CMP-06 | 41 functions over 100 lines (`config_page.render` :5246, `handle_post` :6123, `battery_sparkline_svg` :1441, …) | Broken down; `handle_post` per settings group |
| CMP-07 | `read_form`/`_read_upload_body` duplicate drain loop (`app.py:1405,1444`); theme/lang cookie built twice (`:3421,3434`) | Shared helpers |
| CMP-08 | 29 duplicated CSS selectors; 45 hard-coded hex colours | Merged; colours → tokens |
| CMP-09 | i18n keyed by the English sentence: rewording silently drops the French | Stable message IDs |

## Phase 41 — Docs, repository hygiene, closing re-audit

| ID | Finding (evidence) | Remediation |
|----|--------------------|-------------|
| DOC-01 | Doc drift: byos "bound to loopback" (`ARCHITECTURE.md:47`, `deploy/README.md:30`) vs 0.0.0.0; "persists nothing / unmodified" (`ARCHITECTURE.md:409-414`, `Caddyfile:52-56`, `skypane.env.example:86-89`) vs `battery_state.json`; "single writer" (`poll_loop.py:1116`); "18 harnesses" (`ci.yml:4`); log mode 640 vs 660; env path (`skypane.env.example:3`) | All docs aligned with the code as it stands after phases 32–40 |
| DOC-02 | `hardware/logs/backoff-powercycle.log` 15.4 MB (88 KB gzipped); unused `_unresolved/air-caraibes-atr72-unused.png` shipped; `.planning` 1198 files / 49 MB | Log gzipped in the tree (no history rewrite, D-A6); unused asset removed from the deploy; completed v1.0 phases archived via `/gsd-cleanup` at milestone close |
| DOC-03 | — | Re-audit: every ID in this ledger verified against the code and marked closed |
