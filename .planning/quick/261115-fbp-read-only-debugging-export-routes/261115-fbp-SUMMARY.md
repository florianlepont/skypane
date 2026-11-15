---
status: complete
---
# Quick 261115-fbp summary

`companion/export_api.py` now serves `flights`, `poll-cycles` and `status` next
to `battery-history`, behind the same token, throttle and error answers.
`server/history_db.py` gains the `poll_cycles` table, its writer and pruner and
a table-whitelisted read-only reader; `server/poll_cycle.py` builds the trace
row and writes it inside the one history transaction (own SAVEPOINT).

Guards kept: one connection and one commit per cycle; nothing under
`companion/` mentions `wake_epochs`; every `CREATE TABLE` guarded (count is now
five). Docs: `deploy/README.md`, `deploy/skypane.env.example`.

Checks: server, stub-server, companion (non-browser) and deploy suites
(11300 passed), ruff, mypy, function-size gate, comment-history guard, shard
check. Browser tests were not run locally (no Chromium); CI runs them.
