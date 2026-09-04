---
phase: 10
slug: scheduled-quiet-hours
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-09-03
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| companion HTTP POST → `save_device_config()` | Untrusted submitted quiet-hours strings cross into a persisted document | Enabled flag + two HH:MM strings |
| `device_config.json` on disk → `load_device_config()` / `read_quiet_hours()` | A hand-edited or corrupted config file crosses into every reader (server, vendored stub-server, poll loop) | Enabled flag + two HH:MM strings |
| `poll_loop.py` → `build_canvas(quiet_hours_until=...)` | A config-derived string crosses into text drawn onto the physical panel | One HH:MM string |
| device → `GET /device/v1/display` | An authenticated but untrusted network client reaches the always-on protocol service | Bearer-gated HTTP request |
| `poll_state.json` on disk → `run_once()` | A corrupted state document reaches the render-once/hold decision | Boolean flag |
| browser POST `/settings` → `handle_post()` | Untrusted submitted quiet-hours strings cross into a persisted document | Enabled flag + two HH:MM strings |
| saved config → rendered Settings HTML | A stored value is interpolated back into markup on the next page load | Enabled flag + two HH:MM strings |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01-01 | Denial of Service | `server/device_config.py` write path (`save_device_config()`) | medium | mitigate | Every submitted quiet-hours value gated by `isinstance(..., bool)` or `_HHMM_RE.match()` before the file is touched; an invalid value raises `ValueError` and leaves the pre-existing file byte-identical | closed |
| T-10-01-02 | Denial of Service | `server/device_config.py` read path (`load_device_config()`, `quiet_hours_status()`) | high | mitigate | `normalise_*()` helpers and `quiet_hours_status()` never raise, degrade to documented defaults / `(None, None)` — verified: no hostile string reaches `int()`/`datetime.replace()` without clearing `_HHMM_RE` first | closed |
| T-10-01-03 | Tampering | `_HHMM_RE` anchoring | low | mitigate | Verified in code (`server/device_config.py:68`): `_HHMM_RE = re.compile(r"^([01]\d\|2[0-3]):([0-5]\d)\Z")` — `\Z`, not `$`, so a trailing newline cannot smuggle a dirty value past the shape gate | closed |
| T-10-02-01 | Denial of Service | `_build_quiet_hours_canvas()` | medium | mitigate | A missing/empty/non-string `quiet_hours_until` omits the body line instead of raising or drawing a `None` literal; caller (10-04) only ever passes a value that already cleared `_HHMM_RE` | closed |
| T-10-02-02 | Tampering | panel palette legality | low | mitigate | Canvas built exclusively from `IDX_WHITE`/`EMPTY_INK`; legal-palette membership check over every pixel confirmed passing in `server/test_render.py` (127/127) | closed |
| T-10-03-01 | Denial of Service | `read_quiet_hours()` / `/device/v1/display` handler | high | mitigate | `read_quiet_hours()` never raises — every failure mode (missing/unreadable file, malformed JSON, non-dict, `quiet_hours_enabled` not literally `True`, either time string failing `_HHMM_RE`) returns `None`, resolving to the pre-existing unmodified `sleep_s`; covered by hostile-config integration check | closed |
| T-10-03-02 | Denial of Service | `seconds_until_quiet_hours_end()` reached from a request handler | high | mitigate | No submitted string reaches `int()`/`datetime.replace()` without first clearing `_HHMM_RE` inside `read_quiet_hours()` | closed |
| T-10-03-03 | Tampering | duplicated window arithmetic across the vendor boundary | medium | mitigate | Verified in code: `stub-server/byos_server.py:74`'s `_HHMM_RE` is byte-for-byte identical to `server/device_config.py:68`'s; automated drift guard in `stub-server/test_poll_cycle.py` plus a recorded negative-control run (code review independently re-diffed and confirmed) | closed |
| T-10-03-04 | Elevation of Privilege | quiet-hours read placed relative to the bearer gate | low | accept | `quiet_hours_sleep_s()` runs inside the `/device/v1/display` branch, which returns 401 before any of it when `bearer_ok()` fails — no new auth surface added | closed |
| T-10-04-01 | Denial of Service | `run_once()`'s quiet-hours gate | high | mitigate | Gate's only inputs (`load_device_config()`, `quiet_hours_status()`) never raise; a corrupted config resolves to "not in a window" and can never abort a poll cycle or leave the panel unwritten | closed |
| T-10-04-02 | Tampering | `poll_state["quiet_hours_active"]` | low | mitigate | Verified in code: `server/poll_loop.py:697,804` both read via `bool(poll_state.get("quiet_hours_active", False))` — any non-bool or absent value degrades to `False` | closed |
| T-10-04-03 | Denial of Service | `_record_history()` on the quiet path | low | accept | Already contained by that function's own catch-and-log discipline (T-06-10-05); no new exposure from calling it on one more branch | closed |
| T-10-05-01 | Denial of Service | `handle_post()` → `save_device_config()` | medium | mitigate | Every submitted value validated before the file is touched; crafted checkbox value rejected by exact-equality check; malformed HH:MM raises `ValueError`, caught by the existing `except (ValueError, OSError)`, returns the generic save-failed flash — never reaches a `datetime` constructor, never leaves a partial write | closed |
| T-10-05-02 | Information Disclosure / Tampering | `quiet_hours_group()`'s value interpolation | medium | mitigate | Verified in code (`companion/pages/config_page.py:471-476`): heading, caption, checkbox value, current start, and current end all routed through `escape_html()` before interpolation | closed |
| T-10-05-03 | Elevation of Privilege | access to the new fieldset | low | accept | No new auth surface — companion site's existing single shared-password gate covers every Settings field uniformly, inside the same already-gated form/route | closed |
| T-10-SC | Tampering | npm/pip/cargo installs | high | accept | Zero new packages across all 5 plans — `zoneinfo` is stdlib since Python 3.9. No package-manager install task in any Phase 10 plan; `git diff --quiet server/requirements.txt` / `git diff --quiet deploy/` were acceptance criteria and confirmed unchanged | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-03-04, T-10-05-03 | No new authentication surface introduced — both the device bearer-token gate (`/device/v1/display`) and the companion single shared-password gate already cover the new quiet-hours code paths uniformly with existing controls | Phase 10 planner (per-plan threat model) | 2026-09-03 |
| AR-10-02 | T-10-04-03 | `_record_history()`'s existing catch-and-log discipline (T-06-10-05) already fully contains this path; calling it from one additional branch adds no new exposure | Phase 10 planner (per-plan threat model) | 2026-09-03 |
| AR-10-03 | T-10-SC | Zero new dependencies added by this phase (stdlib `zoneinfo` only); enforced by acceptance criteria requiring `server/requirements.txt` and `deploy/` to remain byte-unchanged | Phase 10 planner (per-plan threat model) | 2026-09-03 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-03 | 16 | 16 | 0 | /gsd-secure-phase orchestrator (L1 grep-depth verification, ASVS level 1 — register authored at plan time across all 5 PLAN.md files, all mitigations independently grep-verified against the implementation; also cross-checked against 10-REVIEW.md's and 10-VERIFICATION.md's independent findings) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-03
