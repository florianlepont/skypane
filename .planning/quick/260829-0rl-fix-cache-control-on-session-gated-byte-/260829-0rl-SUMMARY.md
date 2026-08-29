---
phase: quick-260829-0rl
plan: 260829-0rl
subsystem: security
tags: [http, cache-control, companion, information-disclosure]

requires: []
provides:
  - "companion/app.py's Handler.send_bytes() now takes a fail-closed `public` flag deciding shared vs. private Cache-Control scope"
  - "GET /gallery/<name>.png (session-gated) now emits `private, max-age=3600` instead of `public, max-age=3600`"
  - "GET /static/style.css (D-02 gate exemption) unchanged behaviourally, now explicit via `public=True`"
affects: [companion-app, companion-security]

tech-stack:
  added: []
  patterns:
    - "Fail-closed boolean flags for security-relevant defaults (mirrors companion/auth.py's AuthNotConfigured pattern) — a forgetful future caller inherits the safe behaviour, not the leaky one"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/test_companion_app.py

key-decisions:
  - "Named the new send_bytes() parameter `public` (default False) rather than `private` (default False) so the leaky header is never the default a forgetful caller gets"
  - "Strengthened the existing stylesheet check in place rather than adding a second check for it — the count only moves for the genuinely new gallery assertion"

requirements-completed: [QUICK-260829-0rl]

coverage:
  - id: D1
    description: "Authenticated GET /gallery/<name>.png advertises its cached response as non-shareable (private, max-age=3600) instead of the previous shared-cacheable header"
    requirement: "QUICK-260829-0rl"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#an authenticated gallery image is never advertised as storable by a shared/intermediary cache (WR-02)"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /static/style.css (D-02 gate exemption) keeps its shared-cacheable, 300-second header byte-identical to before this change"
    requirement: "QUICK-260829-0rl"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#GET /static/style.css succeeds without a session, returns a CSS content type, and stays shared-cacheable (public, max-age=300)"
        status: pass
    human_judgment: false
  - id: D3
    description: "send_bytes()'s new caching-scope parameter is fail-closed (defaults to private) with exactly one opt-in call site in the whole file"
    requirement: "QUICK-260829-0rl"
    verification:
      - kind: unit
        ref: "grep -v '^#' companion/app.py | grep -c 'public=True'  ->  1"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-29
status: complete
---

# Quick Task 260829-0rl: Fix Cache-Control on session-gated byte-serving responses Summary

**`Handler.send_bytes()` in `companion/app.py` now scopes `Cache-Control` per call site (private for the session-gated gallery route, public only for the exempted stylesheet) via a fail-closed `public` flag, closing WR-02 from the Phase 06.4 code review.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-29T00:00:00Z (approx, session start)
- **Completed:** 2026-08-29
- **Tasks:** 2/2 completed
- **Files modified:** 2 (`companion/app.py`, `companion/test_companion_app.py`)

## Accomplishments

- `Handler.send_bytes()` gained a fail-closed `public` keyword parameter (default `False`) that selects the `Cache-Control` scope token (`private` vs `public`) whenever `cache_seconds > 0`, replacing the previous hardcoded `public` scope.
- `_serve_gallery_image()` (session-gated, behind `require_session()`) now relies on the new private default — its response is `Cache-Control: private, max-age=3600`, so a shared/intermediary cache can no longer store and replay it to a client that never presented the session cookie.
- `_serve_stylesheet()` (a documented D-02 gate exemption, no per-user content) explicitly opts in with `public=True`, keeping its response byte-identical: `Cache-Control: public, max-age=300`.
- `_serve_preview_image()` untouched — it passes no cache lifetime and still emits `no-store`.
- Module docstring's D-02 paragraph updated to note that the same gate-exemption list now also decides the byte-serving caching scope, so the two lists can't silently drift apart.
- `companion/test_companion_app.py` gained one new check (gallery caching scope) and strengthened the existing stylesheet check in place; `EXPECTED_CHECK_COUNT` moved 51 -> 52.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the RED regression checks to the companion harness** - `3f383d6` (test)
2. **Task 2: Distinguish public vs private per call site in send_bytes()** - `e6bfe26` (fix)

_No separate plan-metadata commit — this SUMMARY.md is committed by the orchestrator, not this executor, per the quick-task docs-commit convention._

## Files Created/Modified

- `companion/test_companion_app.py` - Strengthened the stylesheet check to assert its shared-cacheable scope (public, max-age=300); added a new check asserting the gallery route's response is never shared-cacheable (private, max-age=3600); `EXPECTED_CHECK_COUNT` 51 -> 52.
- `companion/app.py` - `send_bytes()` gained the fail-closed `public` parameter; `_serve_stylesheet()` opts in (`public=True`); `_serve_gallery_image()` relies on the new private default (comment added); module docstring's D-02 paragraph extended.

## The RED (Task 1, before any app.py edit)

Exact failure line observed, with `companion/app.py` unmodified:

```
FAIL an authenticated gallery image is never advertised as storable by a shared/intermediary cache (WR-02) - an authenticated gallery image must never be advertised as storable by a shared cache — got Cache-Control: 'public, max-age=3600'
...
companion-app: 51/52 checks pass
```

This was the only failure; the strengthened stylesheet check passed against the unmodified code, confirming its assertion described the current (correct) behaviour rather than a needed change.

## Final header values observed (Task 2, GREEN)

| Route | Auth posture | `Cache-Control` header |
|-------|--------------|-------------------------|
| `GET /gallery/<name>.png` | Session-gated (`require_session()`) | `private, max-age=3600` |
| `GET /static/style.css` | D-02 gate exemption (unauthenticated) | `public, max-age=300` |
| `GET /preview.png` | Session-gated, unedited | `no-store` (unchanged) |

`companion/test_companion_app.py`: `companion-app: 52/52 checks pass`.
`companion/test_config_page.py`: `config-page: 23/23 checks pass` (unedited).
`companion/test_view_pages.py`: `view-pages: 19/19 checks pass` (unedited).
Exactly one non-comment line in `companion/app.py` opts into shared cacheability (`_serve_stylesheet()`'s `public=True`).

## Decisions Made

- Named the new parameter `public` (defaulting to `False`) rather than `private` (defaulting to `False`), per the plan's fail-closed design note — mirrors `companion/auth.py`'s `AuthNotConfigured` fail-closed discipline already established in this codebase.
- Docstring wording for the `public` parameter avoids the literal substring `public=True` outside real code (rephrased as "a true `public` value") so the acceptance gate's `grep -c 'public=True'` count stays pinned to the one real call site, not an incidental docstring mention.

## Deviations from Plan

None affecting the plan's own scope - plan executed exactly as written for both tasks.

### Out-of-scope item logged, not fixed

**1. [Scope boundary] Pre-existing pinned-digest failure in `server/test_poll_loop.py`**
- **Found during:** Task 2's belt-and-braces full-suite run (`scripts/run-all-tests.sh`).
- **Issue:** `server/test_poll_loop.py`'s pinned `panel.bin` digest check fails (`poll-loop: 42/43 checks pass`) — a rendering-output digest mismatch tied to `server/plane/render.py`/`server/poll_loop.py`, neither of which this task touches.
- **Action:** NOT fixed — this task's `files_modified` are `companion/app.py` and `companion/test_companion_app.py` only; the failure is unrelated to Cache-Control and pre-dates this task's changes. Logged to `.planning/quick/260829-0rl-fix-cache-control-on-session-gated-byte-/deferred-items.md` for follow-up.
- **Verification that this task's own scope is unaffected:** all three companion harnesses green (52/52, 23/23, 19/19); coverage held at 90% (threshold 83), confirming no coverage regression from this task's change.

## Issues Encountered

The `grep -v '^#' companion/app.py | grep -c 'public=True'` acceptance gate initially counted 2 matches (the real call site plus a docstring mention of `` `public=True` ``, which doesn't start with `#` so wasn't filtered). Fixed by rewording the docstring to avoid the literal substring while keeping the same meaning ("a true `public` value"), re-verified the count is exactly 1.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

WR-02 from `.planning/phases/06.4-runway-picker-show-runway-number-and-airport-map/06.4-REVIEW.md` is closed. No blockers for the remaining 06.x backlog phases; `server/test_poll_loop.py`'s pinned-digest drift (see Deviations) remains open and should be addressed in a follow-up quick task or the next phase touching `render.py`.

---
*Phase: quick-260829-0rl*
*Completed: 2026-08-29*

## Self-Check: PASSED

- FOUND: companion/app.py
- FOUND: companion/test_companion_app.py
- FOUND: .planning/quick/260829-0rl-fix-cache-control-on-session-gated-byte-/260829-0rl-SUMMARY.md
- FOUND: .planning/quick/260829-0rl-fix-cache-control-on-session-gated-byte-/deferred-items.md
- FOUND commit: 3f383d6
- FOUND commit: e6bfe26
