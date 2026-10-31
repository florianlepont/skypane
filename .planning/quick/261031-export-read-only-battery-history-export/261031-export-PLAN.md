---
quick_id: 261031-export
slug: read-only-battery-history-export
date: 2026-10-31
type: quick
---

# Quick 261031-export: read-only battery-history export over HTTPS

The owner wants the battery history fetched without SSH. The cloud environment's network
secret form injects `Authorization: Bearer <token>` into requests to an allowed host and path
prefix, so the companion gets one bearer-token route that returns the rows the SSH export in
`hardware/FIELD-VALIDATION-FR.md` Partie A produces.

## Tasks

1. Tests first (real HTTP against the shared app-server fixture): feature off unless
   `SKYPANE_EXPORT_TOKEN` has 32+ characters (404 like an unknown path); output format and
   headers; 401 for missing or wrong token with an identical body; no cookie ever grants access
   or is set; per-client throttle (429) checked before the comparison; strict `since`
   validation (400); other methods refused; 413 over the row cap; token never in the log. Add
   the route to the access matrix and the public-route table test.
2. Implement `companion/export_api.py` (mixin), a read-only `history_db.export_device_health`,
   `StartThrottle.is_blocked`, and the PUBLIC route entry.
3. Docs: `deploy/README.md` section, `deploy/skypane.env.example`, `Partie A bis` in the French
   field guide.

## Verification

ruff, comment-history guard, function-size gate, mypy, new tests, access matrix, route table,
suite guards, and the non-browser companion, server and deploy tests.
