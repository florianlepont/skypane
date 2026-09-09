---
phase: 17
slug: connect-a-calendar-from-the-companion-instead-of-over-ssh
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-09
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Hand-rolled `check(name, fn)` harness with a per-file `EXPECTED_CHECK_COUNT` ledger. The run exits non-zero on a count mismatch, so a check that is added but never registered, or silently dropped, fails the harness rather than passing quietly. |
| **Config file** | none — `scripts/run-all-tests.sh`'s `HARNESSES` array is the single source of truth (18 harnesses registered) |
| **Quick run command** | `server/.venv/bin/python3 <the one touched harness>` |
| **Full suite command** | `bash scripts/run-all-tests.sh` |
| **Estimated runtime** | full suite ~3 min; a single harness < 10 s |

**Baseline at plan time** (measured 2026-09-09, after merging `claude/t-16-priv-retention`, not
taken from research):

| Harness | Count | Note |
|---|---|---|
| `server/test_calendar_rules.py` | 80/80 | 76 before the T-16-PRIV merge — plan against 80 |
| `server/test_poll_loop.py` | 80/80 | |
| `companion/test_config_page.py` | 127/127 | file contains 5 successive `EXPECTED_CHECK_COUNT` assignments from past merges; only the last is live |
| `companion/test_companion_app.py` | 165/165 | same shape, 5 assignments |

Full suite: **PASS**, 92% total coverage. `server/.venv/bin/ruff check .`: clean.

---

## Sampling Rate

- **After every task commit:** the one harness most relevant to that task
- **After every plan wave:** `bash scripts/run-all-tests.sh` (all 18 harnesses)
- **Before `/gsd-verify-work`:** full suite green **and** `server/.venv/bin/ruff check .` clean
- **Max feedback latency:** ~10 s per task, ~3 min per wave

> **`run-all-tests.sh` has no lint step.** CI runs `ruff check .` as a separate blocking job, so a
> green local suite does not prove CI green. This exact gap failed CI once in Phase 15 (an `F507`
> format-placeholder mismatch a passing test file happily contained). Run ruff before every commit.

---

## Per-Task Verification Map

Behaviour-to-test mapping keys off the locked decisions — this phase has no mapped
`REQUIREMENTS.md` IDs (unmapped backlog phase, the Phase 10-16 precedent).

| Decision | Behavior to prove | Threat Ref | Test Type | Harness | Infra |
|---|---|---|---|---|---|
| D-01 | The secret file is mode 0600 **at creation**, not chmod'ed afterwards — assert on the tmp file's mode during the write, not only the final file's | T-17-MODE | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-01 | `os.replace()` onto a pre-existing 0644 file yields 0600 — proves the tmp file's mode is what governs | T-17-MODE | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-01 | The write survives a umask of 022 **and** 027 without widening | T-17-MODE | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-02 | A hand-widened mode makes `calendar_is_configured()` return `False` **and the value is never read** — assert the read path did not open the file, not merely that it returned False | T-17-MODE | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-02 | The distinct status renders in Settings and names the remedy | — | unit | `companion/test_config_page.py` | ✅ exists |
| D-03 | Both accessors read the file; `SKYPANE_CALENDAR_ICS_URL` is fully inert — set the env var to a distinctive token and assert it changes nothing | T-17-SECRET | unit | `server/test_calendar_rules.py` | ⚠️ ~34 existing references to `CALENDAR_URL_ENV_VAR` are fixtures to rewrite, not just new checks |
| D-04 + D-07 | Disconnect checkbox checked → URL cleared **and** fetched entries erased in the same save | T-17-PRIV | unit + integration | `server/test_calendar_rules.py` + `companion/test_companion_app.py` | ✅ exists |
| D-07 | **An empty field with the box unchecked changes nothing** — the regression that D-07 exists to prevent. Save an unrelated setting twice and assert the calendar stays connected. | T-17-PRIV | integration | `companion/test_companion_app.py` | ✅ exists |
| D-07 | A non-empty URL submitted with the box checked is rejected whole, nothing written | — | unit | `companion/test_config_page.py` | ✅ exists |
| D-05 | Replacing the URL clears the previous calendar's entries | T-17-PRIV | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-06 | `min_interval_s` threads through `refresh_calendar_registry()`; a save-triggered call fetches inside the 1800 s window | — | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-06 | **`server/poll_loop.py`'s existing call is behaviourally unchanged** — the default must preserve today's throttling | — | regression | `server/test_poll_loop.py` | ✅ exists |
| D-06 | The failure message never contains the URL or `str(exc)` | T-17-SECRET | integration | `companion/test_companion_app.py` | ✅ exists |
| D-08 | `calendar_is_configured()` still returns a genuine `bool` (`is True` / `is False`, not truthiness) in all three states | — | unit | `server/test_calendar_rules.py` | ✅ exists |
| D-09 | A save arriving during a running poll gets the already-running flash, never a concurrent registry write | — | integration | `companion/test_companion_app.py` | ✅ exists |

*Status column omitted — plans are not yet written; the planner assigns task IDs and fills it.*

---

## The assertion this phase must not get wrong

Every D-01/D-02 check must assert the **octal mode**, via `stat.S_IMODE(os.stat(path).st_mode)`,
against `0o600` — never `os.access()`, and never "the file exists and is readable by me". The
process runs as the file's owner in every test, so an owner-readable assertion passes identically
at 0600 and 0644 and would prove nothing. The bug this phase exists to prevent is a **group**-
readable file, and only the mode bits can see it.

Correspondingly, at least one check must be **negative**: create the file through the current
house idiom (default umask) and assert the accessor refuses it. A test suite that only ever
exercises the correct writer cannot tell whether the reader's guard works.

---

## Wave 0 Requirements

Existing infrastructure covers all phase behaviours. All four harnesses exist, are registered in
`scripts/run-all-tests.sh`, and have live `EXPECTED_CHECK_COUNT` ledgers to increment.

One caveat for whoever edits the ledgers: `companion/test_config_page.py` and
`companion/test_companion_app.py` each carry **five** `EXPECTED_CHECK_COUNT` assignments left by
past merges, only the last of which is live. Editing an earlier one has no effect and the harness
will still fail on the count. Edit the last assignment in the file.

`companion/test_config_page.py` also contains at least one whole-dict equality assertion over
`device_config`, which breaks by construction whenever a key is added. If this phase adds a
`device_config` key, repair that assertion as an exact-dict comparison — do not loosen it to a
subset check, which would stop catching unintended key additions.

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|---|---|---|
| The Calendar group still reads honestly with the field, the disconnect checkbox and four status states in it | Phase 16's copy discipline exists because an overpromising caption makes a working feature look broken. Automated checks pin the constants and reject surveillance verbs; whether the whole group still sounds truthful to someone who knows what the frame does is a judgement call — the same one Phase 16's UAT recorded. | Run the companion locally against an isolated state dir, connect a calendar, disconnect it, and read the group in a real browser at both connected and disconnected states. |
| The permission-drift state (D-02) reads as actionable | It is the one status that asks the operator to act on the server. It must name the remedy without naming the file's contents. | Widen the secret file's mode by hand, reload Settings, read the message. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or an explicit manual entry above
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references — **N/A, none missing**
- [ ] No watch-mode flags
- [ ] Feedback latency < 10 s per task
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
