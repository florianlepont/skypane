# Phase 65 export snapshot

**Status:** COMPLETE (all three routes fetched, no route failed)
**Fetched at:** 2026-11-15T13:41:13Z (UTC), `since=2026-11-01T00:00:00Z`
**Tool:** `scripts/export_snapshot.py` (stdlib, read-only GET, token injected by the proxy, never seen by the script)
**Files:** `data/` in this phase directory; checksums also in `data/MANIFEST.json`

Later plans must read these files, never the live API.

## Files

| File | Route | Rows | sha256 | First ts | Last ts |
|------|-------|------|--------|----------|---------|
| `runway_events.jsonl` | `/api/export/flights` | 5031 | `d4e81942975749262e658002a1d4bb4f1a7ad09bb5b36af72b69379f559133dc` | 2026-11-01T05:09:42+00:00 | 2026-11-15T13:39:01+00:00 |
| `poll_cycles.jsonl` | `/api/export/poll-cycles` | 75 | `f43009e85d89d1aa2bb06ee7b194723bba9585b018aeb37e4ed6bad73635ee7b` | 2026-11-15T12:13:50+00:00 | 2026-11-15T13:40:35+00:00 |
| `status.json` | `/api/export/status` | 1 object | `6157d69c69b1ca98512659fe11e50395e9e207b57c676561fd8cd87a3d5e01b2` | n/a (`now` 2026-11-15T13:41:15+00:00) | n/a |

`runway_events.jsonl` is 1.5 MB; the other two are small. All are committed because `poll_cycles` expires after 14 days.

## runway_events by confirmed_state

| State | Rows |
|-------|------|
| departing | 2841 |
| arriving | 2189 |
| none (stateless) | 1 |
| total | 5031 |

Versus the counts recorded in the phase context at planning time (5019 total, 2841 departing, 2177 arriving, 1 stateless): the departing and stateless counts are equal, arriving grew by 12 as flights kept landing before this fetch. Rows only grow, as expected.

## poll_cycles caveat

`poll_cycles` holds 75 rows, all from 2026-11-15 (12:13 to 13:40 UTC): 71 arriving, 4 departing. The table only began recording with the release that introduced it, and each cycle that saw, queued, dropped or drew an aircraft gets one row. It therefore covers about 1.5 hours, not the full 2026-11-01..11-15 period. Downstream plans cannot use it to replay the full fortnight. Per-flight comparison must rely on `runway_events` for the period, and on `poll_cycles` only for the held-state and pending analysis of 2026-11-15. The planning-time count of 38 rows was an earlier read of the same growing table.

## Secret scan (before commit)

- `grep -rIil 'bearer\|secret\|token\|password\|authorization'` over `data/`: no match.
- `@` count in all three files: 0 (no e-mail address).
- `status.json` keys: `now`, `shown`, `shown_state`, `previous`, `pending`, `hold_state`, `last_advance_at`, `last_flight_redraw_at`, `device`, `check_interval_experiment`, `meta`. Nested keys: aircraft fields (hex, callsign, type, altitude, rate, on_ground), settings (`wake_interval_s`, `tracked_runway`, `display_enabled`, quiet hours, `timezone`), the experiment (`check_interval_s`, `expires_at`), and the heartbeat (`last_detection`, `last_pipeline_run`, `last_poll_trigger`, `provider_last_call:*`, `source_fault`). All match the fields `deploy/README.md` documents for the status route. No credential, location or name.
- `poll_cycles.jsonl` has one column beyond the README list (`branch`); it is a plain code-path label, not sensitive.
- Redactions: none. The sha256 values above are those of the committed files.
