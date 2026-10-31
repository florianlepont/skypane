---
phase: 52-fleet-poll-cycle-zones-and-request-budget
verified: 2026-10-30T00:00:00Z
status: passed
score: 3/3 roadmap criteria verified, 17/17 decisions honoured; 2 minor non-blocking gaps (stale text)
gaps:
  - truth: "Poll now is removed completely including its strings (D-10)"
    status: partial
    reason: "The empty-history card still tells the user to 'Use Poll now to run one', a control that no longer exists (EN and FR)."
    artifacts:
      - path: "companion/pages/history_page.py"
        issue: "line 211 EN default string references Poll now"
      - path: "companion/i18n_fr/flights.py"
        issue: "line 78 FR string references 'Vérifier maintenant'"
      - path: "companion/settings/rules.py"
        issue: "module docstring line 4 mentions a manual 'Trigger poll now' control"
    missing:
      - "Reword flights.device_empty_body in EN and FR (e.g. 'appear after the next check')"
      - "Fix the rules.py docstring"
  - truth: "No stale /poll-now references in server/ comments"
    status: partial
    reason: "Comments in server/ still describe the removed companion POST /poll-now as a live caller."
    artifacts:
      - path: "server/history_db.py"
        issue: "line 52"
      - path: "server/plane/detect.py"
        issue: "lines 682 and 717 (_spaced_query / poll_current_aircraft docs)"
      - path: "server/poll_cycle.py"
        issue: "lines 4, 87, 1313, 1340"
      - path: "server/state_store.py"
        issue: "line 112"
      - path: "server/poll_loop.py"
        issue: "line 23 (also a 'plan 02-05' reference at line 56, a plan ID in a comment/help text)"
    missing:
      - "Reword to 'the companion's calendar sync' or drop the poll-now mention; remove the 'plan 02-05' id (the comment-history check does not catch it)"
deferred: []
human_verification: []
---

# Phase 52: Fleet Poll Cycle, Zones and Request Budget - Verification

**Goal:** The poll loop serves the whole fleet while total ADS-B requests stay within 1 per second.
**Status:** gaps_found (goal achieved; two cosmetic/stale-text gaps, no blocker)

## Test evidence (run by the verifier, server/.venv)

`pytest server/test_fleet_budget_simulation.py server/test_request_budget_processes.py server/test_fleet_cycle.py server/test_request_budget.py server/test_zone_fetch.py stub-server/test_phase47_freeze.py server/test_fleet_zones.py server/test_poll_loop.py server/test_provider_rate.py`: all pass, 1 skip (a permission-bit test that needs a non-root user). `scripts/check_comment_history.py check`: exit 0.

## Roadmap success criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Shared zone is one upstream request set; budget holds across providers and overlapping processes (persisted, file-locked) | VERIFIED | `server/request_budget.py`: `RequestLedger.acquire` holds an exclusive flock (`atomic_io.exclusive_lock`), reads last_request_at, sleeps out at most 1.1 s, stamps and persists, with global spacing independent of provider. `fleet_zones`/`fleet_cycle.plan_zones` group devices by exact (centre, radius); `_FleetRun.fetch` fetches once per group and every device runs on that `ZoneFetch`. `server/test_request_budget_processes.py` (real processes) passes. |
| 2 | Simulated 100-device fleet with fake clock shows at most 1 request per second | VERIFIED | `server/test_fleet_budget_simulation.py` passes. It covers 100 devices, a capacity-exceeding fleet (12 zones served) and the small-deadline case. |
| 3 | A provider failure or timeout for one device or zone leaves the others on time | VERIFIED | Per-device try/except in `run_device`. `fetch` catches fetcher errors and returns `_failed_fetch()`. `_query_one` swallows provider errors and pauses the provider. Simulation tests for a last-zone failure, a slow provider, a raising fetcher and a raising runner pass. |

## Requirements

| Req | Status | Evidence |
|-----|--------|----------|
| FLT-03 | SATISFIED | Persisted flock ledger, shared across providers and processes, one fetch per zone. |
| FLT-04 | SATISFIED | 100-device fake-clock simulation, failure isolation tests. |

(REQUIREMENTS.md still shows both as Pending; the orchestrator should tick them.)

## Decisions D-01..D-17

| D | Status | Evidence |
|---|--------|----------|
| D-01 | OK | One global spacing across providers. `fetch_zone._check_providers` rejects any provider outside `DEFAULT_PROVIDER_ORDER` (adsbfi, adsblol), so airplanes.live is impossible for the fleet. |
| D-02 | OK | Spacing 1.1 s and the provider pause are never relaxed; 4xx/429 handling is routed through `report_failure`. |
| D-03 | OK | Only the unit comment of `deploy/skypane-poll.service` changed (no deploy). |
| D-04 | OK | `fetch_zone` queries adsbfi then adsblol sequentially, so a zone costs 2 requests. Capacity of 12 zones per 25 s is asserted in the simulation. |
| D-05 | OK | Sequential, 1.1 s global spacing in `acquire`. |
| D-06 | OK | `report_failure` persists a 60 s pause in the ledger; `acquire` returns False while paused, with no stamp; the zone falls back to a single source. A failed request still stamped the slot (the stamp happens in `acquire`, before the call). |
| D-07 | OK | `fleet_zones.order_zones` puts live-frame zones first, then oldest-served via `zone_last_served`. `mark_served` only records a zone with results where a device ran. |
| D-08 | OK | `runnable_devices` skips devices inactive for 7 days with the live and new-device exemptions; `test_inactive_devices_are_never_run` passes. |
| D-09 | OK | `serve_held` runs held devices with `ZoneFetch.not_fetched()` at zero cost (`test_held_devices_alone_in_a_zone_cost_no_request`). |
| D-10 | PARTIAL | Route, buttons, cooldown JS and tests are removed (`companion/test_poll_removal.py`, `test_access_matrix.py` assert 404 and no cycle). Residual stale user-facing string (see gaps). |
| D-11 | OK | Removal is the last code commit (64e8478) after the merge of main (3efd732). |
| D-12 | OK | Exact (centre, radius) zone key; no quantisation. |
| D-13 | OK | adsbdb is outside the ledger. `server/plane/shared_route_cache.py` plus `SharedRouteTransport` deduplicate lookups (`test_shared_route_cache.py`). |
| D-14 | OK | `request_ledger.json` plus `request_ledger.lock` in the state root, flock, sanitised and clamped on read. `fleet_db.py` has no schema change in this phase's commits (not in the diff since d525a14). |
| D-15 | OK | `zone_fetch.fetch_zone` fetches; `detect.select_from_provider_results` selects, pure. |
| D-16 | OK | Per-device isolation, a zone fetch failure marks only that zone's devices, `FLEET_START_DEADLINE_S = 25` under TimeoutStartSec 90. |
| D-17 | OK | The live frame is run via the root state dir with `reconcile_firmware=device.is_live`; others use their `devices/<id>` directory. |

## Specific checks

1. **No bypass of the ledger.** In server/ and companion/ production code, `detect.query_provider` has exactly one caller, `zone_fetch._query_one`, which calls `ledger.acquire` first. The standalone single-device path (`poll_cycle._fetch_standalone`) also goes through `fetch_zone` with a ledger. `companion/` has no ADS-B caller at all. `poll_current_aircraft` and `_spaced_query` (own per-process spacing, no ledger) are called only by `detect.main`, a developer CLI (`python -m server.plane.detect`) that is not referenced by deploy/, scripts or the companion, and in tests. They are unreachable from fleet or companion code. Residual WARNING: the dev CLI can send unbudgeted requests if an operator runs it by hand on the VPS while the timer runs; consider routing it through the ledger or marking it dev-only. `scripts/measure_efficiency.py` and `test-support/efficiency_probe.py` reference `query_provider` for measurement and are not on the production path (not exercised here).
2. **Live frame unchanged / expand-only.** `stub-server/test_phase47_freeze.py` passes against the frozen measured fields. No `fleet_db.py` schema change in Phase 52 commits. New files (`request_ledger.json`, `request_ledger.lock`, `adsbdb_shared_cache.json`) live in the state root. The previous release's byos server never lists the state root (its only `os.listdir` is the image dir), so it ignores them. There is no explicit automated test that the previous release tolerates the new files (WARNING, covered by inspection only).
3. **12th-zone design note.** `fetch_zone` checks the deadline before each provider, but `acquire` may then sleep up to 1.1 s, so the second request of the last started zone can go out slightly after 25 s. The zone's non-live devices are then deferred and the requests are spent without an image update. Judgement: not a violation. Criterion 2 (at most 1 request per second) still holds, since spacing is enforced in `acquire`; criterion 3 holds (other devices unaffected). The overrun is bounded to about one zone, so the run finishes near 25 + 1.1 + 8 s, well under 90 s (the simulation asserts `< detect_deadline() + 1.2` for start times). The deferred zone is not marked served, so it ages and is first in line next cycle (no starvation). Cost is at most two wasted requests per capacity-exceeding cycle. This is an efficiency note, not a gap. A cheap improvement would be to check the deadline again after `acquire` returns, or to skip the second provider when fewer than about 1.1 s remain.
4. **Stale /poll-now references in server/ comments.** Found (see gaps): history_db.py, detect.py, poll_cycle.py, state_store.py, poll_loop.py. Also a stale user-facing string in companion.
5. **Plan/phase IDs in comments.** The new Phase 52 modules (request_budget, fleet_cycle, fleet_zones, zone_fetch) are clean, and the comment-history check passes (exit 0). One leftover: `server/poll_loop.py:56` has "plan 02-05" in the `--once` help text (pre-existing, not caught by the guard).

## Anti-patterns

No TODO/FIXME/TBD markers found in the new modules. No stubs: ledger, zone fetch and fleet cycle are substantive and wired into `poll_loop.main`.

## Gaps summary

No blocker. The phase goal and all 3 criteria are achieved and tested. Open items are text-only: the stale "Use Poll now" empty-state string (EN and FR), stale `/poll-now` comments in server/, and a leftover "plan 02-05" in `poll_loop.py` help text. Warnings (no action required for the phase): the dev-only `detect` CLI bypasses the ledger by design; no direct test for previous-release tolerance of the new state files.


## Gap closure

The two text-only gaps (the stale "Poll now" user-facing string and its French twin, and stale `/poll-now` and plan-ID comments in `server/`) were fixed after verification. The post-deadline second request of the last started zone is bounded to at most two requests per over-capacity cycle and is accepted.
