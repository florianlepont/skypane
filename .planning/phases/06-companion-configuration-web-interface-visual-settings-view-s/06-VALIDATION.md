---
phase: 6
slug: companion-configuration-web-interface-visual-settings-view-s
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-27
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — project convention: stdlib-only, directly-executable `test_*.py` scripts (no pytest; see `server/README.md`) |
| **Config file** | none — see Wave 0 |
| **Quick run command** | `server/.venv/bin/python3 companion/test_companion_app.py` |
| **Full suite command** | `scripts/run-all-tests.sh` (once `companion/test_companion_app.py` is added to its `HARNESSES` array) |
| **Estimated runtime** | ~10-20 seconds (matching this project's existing `test_*.py` harnesses) |

---

## Sampling Rate

- **After every task commit:** Run `server/.venv/bin/python3 companion/test_companion_app.py` (and `server/test_plane_detection.py` for any CFG-12 work)
- **After every plan wave:** Run `scripts/run-all-tests.sh` (full suite)
- **Before `/gsd-verify-work`:** Full suite green, plus `ruff check .` and `scripts/check-attribution.sh` (unchanged, already required repo-wide)
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

Task IDs, plan numbers, and wave assignments are not yet known — this maps requirements to test coverage now, ahead of planning. The planner should thread the actual `{N}-01-01`-style Task IDs and Wave numbers into this table (or its PLAN.md equivalents) once tasks exist.

| Requirement | Wave | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-------------|------|----------|------------|-----------|-------------------|-------------|--------|
| CFG-01 | TBD | Theme saved persists to `device_config.json`, `render.py` reads it | — | unit + integration | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |
| CFG-03 | TBD | Health page renders trend from `history.db`/Caddy-tailed battery data | — | integration | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |
| CFG-04 | TBD | Unresolved-prefix registry rendered read-only | — | integration | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |
| CFG-06 | TBD | Flight log lists recent `runway_events` rows | — | integration | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |
| CFG-07 | TBD | Manual poll trigger calls `run_once()`, cooldown enforced globally | — | integration | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |
| CFG-08 | TBD | Resolution stats aggregate query returns expected shape | — | unit | `companion/test_companion_app.py` (or a dedicated `history_db` test) | ❌ Wave 0 | ⬜ pending |
| CFG-09 | TBD | Dark/light theme toggle persists client-side | — | manual | N/A (see Manual-Only Verifications) | — | ⬜ pending |
| CFG-10 | TBD | `/preview.png` returns a viewable image matching `panel.bin`'s content | — | unit | `server/.venv/bin/python3 companion/test_panel_preview.py` (round-trip `pack_panel`→`unpack_panel`) | ❌ Wave 0 | ⬜ pending |
| CFG-11 | TBD | Gallery retention caps at N, prunes oldest | — | unit | extend `server/test_poll_loop.py` | ❌ Wave 0 | ⬜ pending |
| CFG-12 | TBD | `select_aircraft_for_runway()` correctly gates each of the 3 runways; `select_runway3_aircraft()` back-compat wrapper unchanged | T-06-CFG12-01 (spoofed/malformed `tracked_runway`) | unit (regression) | extend `server/test_plane_detection.py` (all 28 existing checks must still pass) | ✅ existing file, ❌ new checks Wave 0 | ⬜ pending |
| D-01/D-02 (auth) | TBD | Password gate blocks every route without a valid session; login issues a valid cookie | T-06-AUTH-01..04 (CSRF, XSS, timing, cookie theft — see Security Domain below) | unit | `companion/test_companion_app.py` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `companion/test_companion_app.py` — stdlib harness, subprocess-launches `companion/app.py` on a free local port and drives it with `urllib.request`, mirroring `stub-server/test_poll_cycle.py`'s exact pattern (deterministic setup, `EXPECTED_CHECK_COUNT` convention, exit 0 only on full pass) — covers auth, CFG-01/03/04/06/07/08 route behavior
- [ ] `companion/test_panel_preview.py` (or fold into the above) — round-trips `pack_panel()` → `unpack_panel()` on a known canvas and asserts pixel-for-pixel equality
- [ ] Extend `server/test_plane_detection.py` — new checks for `select_aircraft_for_runway()` against 06/24 and 02/20 geometry (using the already-committed neighbouring-runway coordinates from `runway3.json`, now as *positive* fixtures instead of only exclusion regressions), while keeping all 28 existing checks green unchanged
- [ ] Extend `server/test_poll_loop.py` — gallery retention, `history.db` write-on-state-change-only behavior, `device_config.json` read path
- [ ] Add `companion/` to `pyproject.toml`'s `[tool.coverage.run] source` list and `scripts/run-all-tests.sh`'s `HARNESSES` array once the new test file(s) exist
- [ ] Framework install: none — stdlib only, no new `pip install` needed for tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dark/light theme toggle visibly changes the page's appearance | CFG-09 | Purely client-side CSS/visual state — no server-side behavior to assert against | Load the page, toggle the theme control, confirm the page's colors invert; confirm the choice survives a reload (D-09 uses `localStorage` or an equivalent per-viewer preference) |
| Mobile responsiveness (D-22) | CFG-01, CFG-03..12 | Layout/readability judgment, not a assertable property | Load each page at a phone-width viewport (e.g. 375px), confirm text is readable and controls are tappable without horizontal scrolling |
| "SkyPane" title/header renders (D-24) | — | Trivial visual check | Load any page, confirm the header text is present |

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Single shared password, `hmac.compare_digest()` constant-time check, no plaintext logging of the password anywhere (matches `deploy/skypane.env.example`'s existing secrets discipline) |
| V3 Session Management | Yes | Stateless HMAC-signed, expiry-stamped session cookie (`HttpOnly`/`Secure`/`SameSite=Strict`); no server-side session store to leak or grow unbounded |
| V4 Access Control | Yes (narrow) | D-02: uniform, whole-site gate — no differentiated roles/permissions to get wrong |
| V5 Input Validation | Yes | `html.escape()` on every ADS-B/adsbdb-sourced string before HTML interpolation; theme/runway selection values validated against the fixed `THEMES`/`RUNWAY_CONFIGS` key sets server-side |
| V6 Cryptography | Yes (narrow) | `hmac`/`hashlib.sha256` only, stdlib, no custom cipher, no password hashing needed (shared secret compared directly via `hmac.compare_digest()` against an env var, matching `byos_server.py`'s own `--secret` comparison pattern) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSRF against `POST /config`, `POST /poll-now`, `POST /login` | Spoofing/Tampering | `SameSite=Strict` cookie — sufficient for a single-origin, single-user tool with no legitimate cross-site use case |
| Reflected/stored XSS via airline name/callsign/unresolved-prefix fields | Tampering | `html.escape()` on every dynamic interpolation site |
| Timing side-channel on password comparison | Information Disclosure | `hmac.compare_digest()` |
| Session cookie theft via missing `Secure`/`HttpOnly` | Information Disclosure/Elevation of Privilege | Explicit cookie flags |
| Brute-forcing the single shared password | Elevation of Privilege | A simple failed-attempt backoff/lockout (Claude's Discretion per D-01/D-02 — e.g. a short delay after N consecutive failures; D-01 already rejected IP-based mechanisms as impractical) |
| SQL injection into `history.db` queries | Tampering | Always use parameterized `sqlite3` queries (`?` placeholders) — never string-format a value into SQL text |
| CFG-12: a spoofed/malformed `tracked_runway` value reaching `detect.py` | Tampering | The companion service must validate the submitted runway id against `RUNWAY_CONFIGS`'s fixed key set before writing `device_config.json`; `detect.py`'s corridor-parameter lookup should degrade safely (fall back to a default, never raise) on an unrecognized `runway_id` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
