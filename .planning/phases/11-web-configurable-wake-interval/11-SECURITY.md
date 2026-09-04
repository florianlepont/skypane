---
phase: 11
slug: web-configurable-wake-interval
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-09-04
---

# Phase 11 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| companion HTTP POST → `save_device_config()` | Untrusted submitted wake-interval value crosses into a persisted document | One integer (as a form string) |
| `device_config.json` on disk → `load_device_config()` / `read_wake_interval_s()` | A hand-edited or corrupted config file crosses into every reader, ultimately into `quiet_hours_sleep_s()`'s arithmetic and the device's deep-sleep duration | One integer field |
| `stub-server/byos_server.py` → device firmware (`GET /device/v1/display`) | The `sleep_s` field crosses the wire, consumed by `enter_deep_sleep()` as an opaque `uint32_t` | Integer, no firmware interpretation |
| Browser → `POST /settings` → `handle_post()` | An untrusted, always-string form value crosses into a typed config write | Form-encoded string |
| `device_config.json` → `render()` → browser HTML | A stored value crosses back out into interpolated markup | One integer field |
| Process environment (`SKYPANE_SLEEP_S`) → `env_wake_interval_default()` | A deployment-controlled string crosses into a value interpolated into rendered HTML | Environment variable string |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-11-01-01 | Tampering | `save_device_config()` write path | high | mitigate | Non-int/bool/out-of-range raises `ValueError` before the file is touched; byte-identity on rejection verified in code (`server/device_config.py`) | closed |
| T-11-01-02 | Tampering | `load_device_config()` read path | high | mitigate | `normalise_wake_interval_s()` never raises, degrades every hostile shape to `None` — verified in code (`server/device_config.py:426`) | closed |
| T-11-01-03 | Tampering | Bounded-int type test | medium | mitigate | Verified in code: every bounded-int check pairs `isinstance(value, int)` with `not isinstance(value, bool)` (`server/device_config.py:426,517`, `stub-server/byos_server.py:169`, `companion/pages/config_page.py:543`) | closed |
| T-11-01-04 | Denial of Service | Device battery via an extremely short interval | medium | mitigate | 60s floor enforced identically on read (degrade to `None`) and write (raise `ValueError`) paths; Settings form already behind session auth | closed |
| T-11-02-01 | Tampering | `read_wake_interval_s()` | high | mitigate | Explicit bool-excluded `isinstance`+range test; every other failure mode degrades to the caller's `--sleep` default — verified in code | closed |
| T-11-02-02 | Denial of Service | `GET /device/v1/display` availability | high | mitigate | Best-effort, never-raising read matching `read_led_enabled()`/`read_quiet_hours()`'s fail-open contract — verified in code | closed |
| T-11-02-03 | Denial of Service | Device battery (below-floor CLI default) | medium | mitigate | The 60s floor bounds only what a user can set through the web form; the deployed `--sleep` CLI default is a separate, pre-existing surface this phase does not widen | closed |
| T-11-02-04 | Tampering | Delivered `sleep_s` during an active quiet-hours window | medium | accept | Deliberately allowed to exceed `WAKE_INTERVAL_MAX_S` when quiet hours extend it (Phase 10's own intended behavior); re-clamping would strand the device waking hourly through an 8-hour window. Bounded above by the window length | closed |
| T-11-03-01 | Tampering | `handle_post()`'s submitted value | high | mitigate | `int()` gate (non-numeric raises before write) + `save_device_config()`'s strict range check (out-of-bounds raises before write); both precede any write — verified in code | closed |
| T-11-03-02 | Tampering | HTML5 `min`/`max` as a (non-)security boundary | medium | mitigate | Client-side attributes are UX sugar only; `save_device_config()` re-validates identical bounds server-side (ASVS V5) — verified in code | closed |
| T-11-03-03 | Denial of Service | Whole-form submittability via a bad pre-fill | medium | mitigate | `wake_interval_group()` emits a `value` attribute only for an in-range, non-bool int — verified in code (`companion/pages/config_page.py:539-544`), with `deploy/skypane.env.example`'s real `SKYPANE_SLEEP_S=30` as the concrete regression case | closed |
| T-11-03-04 | Information Disclosure | Interpolated group markup | low | mitigate | Heading/caption/placeholder routed through `escape_html()`; numeric value formatted with `%d` (digits/sign only, no injection surface) — verified in code (`companion/pages/config_page.py:534-537,546-558`) | closed |
| T-11-04-01 | Tampering | `env_wake_interval_default()` | medium | mitigate | Deployment-controlled but still parsed defensively: `int()` inside `try/except (TypeError, ValueError)`, then inclusive range test, `None` on any failure — verified in code (`companion/app.py:322-337`) | closed |
| T-11-04-02 | Denial of Service | Whole-form submittability via a bad env value | medium | mitigate | Same range-check discipline as T-11-03-03, defense-in-depth across both plans (`env_wake_interval_default()` and `wake_interval_group()` independently bounds-check) | closed |
| T-11-04-03 | Information Disclosure | The environment read | low | mitigate | Only `SKYPANE_SLEEP_S` is read (never the whole environment); returns int or `None`, never echoes a raw environment string into a page or exception — matches `configured_password()`'s own discipline | closed |
| T-11-04-04 | Elevation of Privilege | Route exposure | low | accept | Built inside `page_context()`, called only by authenticated page handlers; no new route added, existing session gate unchanged | closed |
| T-11-SC (×4, one per plan) | Tampering | npm/pip/cargo installs | high | accept | Zero new packages across all four plans — pure stdlib + existing first-party modules; `server/requirements.txt` untouched; `grep -cE '^\s*(from\|import) server'` on `byos_server.py` confirms the vendor boundary held | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-11-01 | T-11-02-04 | The delivered `sleep_s` is deliberately allowed to exceed 3600s during an active Phase 10 quiet-hours window — re-clamping would break Phase 10's own intended overnight-pause behavior. Bounded above by the window length, and the wire-protocol `uint32_t` guard still applies | Phase 11 planner (per-plan threat model) | 2026-09-04 |
| AR-11-02 | T-11-04-04 | No new route or auth surface — the env read is called only from inside `page_context()`, which every caller reaches through the existing authenticated page-handler path | Phase 11 planner (per-plan threat model) | 2026-09-04 |
| AR-11-03 | T-11-SC | Zero new dependencies across all four plans; enforced by acceptance criteria requiring `server/requirements.txt` unchanged and no new cross-boundary import into the vendored `stub-server/byos_server.py` | Phase 11 planner (per-plan threat model) | 2026-09-04 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-04 | 16 | 16 | 0 | /gsd-secure-phase orchestrator (L1 grep-depth verification, ASVS level 1 — register authored at plan time across all 4 PLAN.md files, all mitigations independently verified against the implementation; cross-checked against 11-REVIEW.md's and 11-VERIFICATION.md's independent findings) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-04
