---
phase: 11
slug: web-configurable-wake-interval
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-04
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Hand-rolled `check(name, fn)` / `EXPECTED_CHECK_COUNT` harness (stdlib-only, no pytest) — this project's own convention |
| **Config file** | none — each test file is directly executable |
| **Quick run command** | `server/.venv/bin/python3 companion/test_config_page.py` (fastest relevant harness; touches the changed page module directly) |
| **Full suite command** | `scripts/run-all-tests.sh` |
| **Estimated runtime** | ~30 seconds (single harness) / ~2-3 minutes (full suite with coverage) |

---

## Sampling Rate

- **After every task commit:** the single harness touched by that task (`server/test_config_history.py`, `companion/test_config_page.py`, or `stub-server/test_poll_cycle.py`)
- **After every plan wave:** `scripts/run-all-tests.sh` (all harnesses + coverage threshold)
- **Before `/gsd-verify-work`:** Full suite green, plus `server/.venv/bin/python3 -m ruff check .`
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

No requirement IDs are mapped to this phase (unmapped backlog phase promoted
from `SEED-002`). Task IDs are assigned during planning — this table maps
each locked decision to its test coverage per `11-RESEARCH.md`'s Validation
Architecture section.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | D-02/D-04 (registry field) | T-06-01-01 (input validation, reused) | `normalise_wake_interval_s()` accepts in-range ints, rejects out-of-range/bool/non-int, returns `None` on failure; `save_device_config()` raises `ValueError` for invalid submissions | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing 39-check harness) | ⬜ pending |
| TBD | TBD | TBD | Regression: 11 dict-equality literals | — | All 11 exact-dict-equality assertions in `test_config_history.py` updated for the new 7th key (mechanically certain to fail otherwise, per research Pitfall 2) | unit (regression) | same file as above | ✅ | ⬜ pending |
| TBD | TBD | TBD | D-05/D-07 (companion UI + pre-fill) | T-06-01-01 | `wake_interval_group()` renders correct markup, escapes current value, omits `value=` when `None`; pre-fills from `SKYPANE_SLEEP_S` env var when device-config value is unset | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ (extend existing 73-check harness) | ⬜ pending |
| TBD | TBD | TBD | Regression: theme-status group count | — | Group-count assertion updated 3→4 (mechanically certain to fail otherwise, per research Pitfall 3) | unit (regression) | same file as above | ✅ | ⬜ pending |
| TBD | TBD | TBD | `handle_post()` int-conversion | T-06-01-01 | Explicit `int()` conversion before `save_device_config()`; rejects non-numeric with `FLASH_SAVE_FAILED`; empty string treated as "leave unchanged" | unit | same file as above | ✅ | ⬜ pending |
| TBD | TBD | TBD | D-01/D-03 (delivery + layering) | — | `read_wake_interval_s()` degrades to `default` on missing/malformed/out-of-range/bool; `/display` handler's `sleep_s` reflects the configured value and still correctly extends through an active quiet-hours window (Phase 10 regression) | unit + integration | `python3 stub-server/test_poll_cycle.py` | ✅ (extend existing 29-check harness) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — every harness this phase touches (`server/test_config_history.py`,
`companion/test_config_page.py`, `stub-server/test_poll_cycle.py`) already
exists with the `EXPECTED_CHECK_COUNT` convention in place. The only
mechanical requirement is incrementing each touched file's count by exactly
the number of new `check(...)` calls added, in the same commit as the new
checks (current counts: `test_config_history.py` = 39, `test_config_page.py`
= 73, `test_poll_cycle.py` = 29).

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Wake-interval field visual design (first plain numeric input in the companion app) | D-05 | `11-CONTEXT.md`/`11-RESEARCH.md` both flag this as a genuinely new UI pattern needing a real-preview check, same discipline Phase 10 used for its own first `type="time"` input | Load the companion Settings page in a real browser, confirm the numeric input's fill/border/radius/height match the page's other fields |
| Pre-fill accuracy against a real deployment | D-07 | `os.environ.get("SKYPANE_SLEEP_S")` behavior can only be confirmed end-to-end against a process actually launched with the systemd `EnvironmentFile=` directive, not a bare `python3 companion/app.py` invocation | On the real VPS (or a local run with `SKYPANE_SLEEP_S` exported), confirm the Settings page pre-fills the field with that value when `device_config.json` has no `wake_interval_s` set yet |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
