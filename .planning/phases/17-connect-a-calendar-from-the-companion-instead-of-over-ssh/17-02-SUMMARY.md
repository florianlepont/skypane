---
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
plan: 02
status: complete
tasks_completed: 3
commits:
  - 11ee1cf
  - 7fd448e
  - afb0abe
summary_authored_by: orchestrator
---

# Plan 17-02 Summary — both accessors move off the environment; the throttle gains a bypass

## Note on how this file came to exist

**The executor completed all three tasks and committed them, then died before writing this
summary.** Its first dispatch was killed mid-task by an API transport error (`ENOTFOUND`), leaving
`server/plane/calendar_rules.py` half-refactored in the working tree — the constant deleted from
its definition site while two function bodies still referenced it. That state **imported cleanly**
and would have passed a shallow "does it load" check, but every call to either accessor raised
`NameError`. The orchestrator reproduced that failure explicitly, discarded the partial edit
(nine lines of comment rewriting, nothing worth salvaging), and re-dispatched. The retry landed
all three task commits and then ended without the summary.

This summary is therefore reconstructed by the orchestrator from the committed diffs, the commit
messages, and **independent re-verification** — not from the executor's own report, which never
arrived. Everything asserted below was re-checked against the tree rather than taken on trust.

## What shipped

**Task 1 (`11ee1cf`) — the read path swaps its source.** `calendar_is_configured(state_dir)` and
`configured_calendar_url(state_dir)` now read `calendar_secret_path(state_dir)` and consult
wave 1's permission guard *before* ever opening the file (D-02). They read the process environment
for nothing at all. `CALENDAR_URL_ENV_VAR` is deleted outright, along with its line in
`deploy/skypane.env.example` and the Settings copy that interpolated its name (D-03).
`refresh_calendar_registry()` gains `min_interval_s=None`, threaded to `calendar_fetch_is_due()`;
`server/poll_loop.py`'s call site is untouched (D-06).

`companion/app.py`'s page context now threads `state_dir` through, and its comment was rewritten.
The old text claimed the companion "must never learn its value" and that the accessor "has no call
site anywhere under companion/". The first half was already false when Phase 16 shipped it —
`POST /poll-now` runs `poll_loop.run_once()` in-process, which refreshes the calendar, which reads
the URL. The new comment states the property that is actually true: the key is a boolean because a
status line needs presence rather than the value, and the value has no rendering, logging or flash
call site. Correcting that comment was not in the plan; it is a correct call, and it removes a
docstring that would have misled the next reader.

**Task 2 (`7fd448e`) — 38 environment references become one fixture.** `_write_calendar_secret()`
replaces every `os.environ` save/set/restore dance (38 references across 10 distinct fixtures) with
a direct `save_calendar_url()` call against the test's own temporary state dir. Two fixtures needed
structural rework rather than a swap: the never-raises check now makes `calendar_rules.json` itself
a directory (root-independent, since the URL and the registry now share a `state_dir` and a
nonexistent dir would merely read as "unconfigured"), and the unconfigured-path check simply writes
no secret.

Seven new checks cover the swap: value-from-file; environment inertness (spying on
`os.environ.get()` rather than naming the retired constant, which the next task's zero-occurrence
gate forbids — a neat way to keep the check honest without reintroducing the name); a drifted file
refused *without ever being opened* (D-02); an ordinary-umask file refused end to end; the bool
contract by identity in all three states (D-08); a hand-written trailing newline stripped on read;
and `min_interval_s` bypassing the throttle while the default preserves it (D-06). Ledger 94 → 101.

**Task 3 (`afb0abe`) — the dependent harnesses reconcile and the gate closes.**
`server/test_poll_loop.py`'s two environment-mutating calendar fixtures move to the secret file, and
a dedicated D-06 regression check pins the new parameter's default to `None`, driven through
`run_once()`'s own production call site rather than a synthetic one. Ledger 80 → 81.

`companion/test_config_page.py`'s two fixtures move likewise. One genuine surprise, recorded as a
deviation by the executor: the rewritten `CALENDAR_STATUS_NOT_CONFIGURED` copy carries an
apostrophe, which `layout.escape_html()` renders as `&#x27;`, so three status-exclusivity checks now
compare against the escaped form. The plan had said these checks needed no edit; it had not
anticipated that changing the copy would change its escaping. That is a real behavioural
consequence, not a stale reference. Ledger unchanged at 127.

## Independent verification (orchestrator, after the fact)

| Check | Result |
|---|---|
| `grep -rn` for the retired constant and variable across `server/ companion/ stub-server/ scripts/ deploy/` | **zero hits** — D-03's gate closed |
| `calendar_is_configured()` return type, unconfigured and configured | `False` / `True` — genuine `bool`, D-08 holds |
| `refresh_calendar_registry` signature | `(state_dir, now, transport=None, min_interval_s=None)` — default preserves today's behaviour |
| `min_interval_s` in `server/poll_loop.py` | only on the unrelated `advance_is_due()`; the calendar call site is untouched |
| Secret file mode, written end to end | `0o600` |
| `bash scripts/run-all-tests.sh` | **PASS**, 92% coverage |
| `server/.venv/bin/ruff check .` | clean |
| `git diff --stat` vs pre-plan HEAD | exactly the 8 files in `files_modified`, no more |

**Mutation testing, run by the orchestrator rather than the executor** (the executor's own
mutation results were lost with its report):

| Mutation | Effect | Verdict |
|---|---|---|
| `refresh_calendar_registry(..., min_interval_s=0)` — default disables throttling | `test_poll_loop` 81 → **79**, `test_calendar_rules` 101 → **98** | 5 checks catch it; restoring returns both to green |

That mutation is the one worth being sure about. The frame polls every thirty minutes, and the
throttle is what keeps it from hammering a third party's calendar server. A default that silently
disabled it would look correct on screen and behave as an abusive client. Five independent checks
fail on it.

## Deviations

1. **Comment correction in `companion/app.py` beyond the plan's letter** — the stale T-16-SECRET
   claim was rewritten to the true property. Accepted: leaving a comment that asserts a
   non-existent process boundary is worse than the diff.
2. **Three status-exclusivity checks in `companion/test_config_page.py` retargeted to the escaped
   copy** — the plan's "no edit needed" guidance did not anticipate that the new copy's apostrophe
   would be HTML-escaped. Accepted: the checks assert rendered output, and the rendered output
   genuinely changed.
3. **This summary written by the orchestrator**, not the executor — see the note at the top.

## Threat flags

No new threats beyond `17-02-PLAN.md`'s own `<threat_model>`. T-17-SECRET and T-17-ENVGHOST are the
two this plan closes: the value now has a single file source consulted behind a permission guard,
and the environment name is gone from every tree, so no ghost of it can resurrect the old path.

## State at close

`server/test_calendar_rules.py` 101 · `server/test_poll_loop.py` 81 ·
`companion/test_config_page.py` 127 · `companion/test_companion_app.py` 165.
Full suite PASS, ruff clean. Wave 3 (`17-03`) may proceed.
