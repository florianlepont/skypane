---
phase: 46-two-run-battery-analysis-and-operating-decision
plan: 03
subsystem: hardware-evidence
tags: [battery, two-run-model, decision-document, BAT-03, BAT-04, POL-01, POL-02]
requires: [46-01, 46-02]
provides:
  - "hardware/logs/battery-model.json: verbatim battery-model output on the committed inputs"
  - "test_committed_model_json_is_reproduced: byte-identical regeneration check"
  - "hardware/BATTERY-MODEL.md: autonomy for 5/10/15/30 min, assumptions, uncertainty, limits, pack criteria, blank owner-decision block"
affects: [46-04]
key-files:
  created:
    - hardware/logs/battery-model.json
    - hardware/BATTERY-MODEL.md
  modified:
    - hardware/test_logtools_model.py
    - hardware/BATTERY-RUN.md
key-decisions:
  - "Quiet hours are a note only, not a table row (adds an unmeasured assumption)"
  - "Run one firmware is not printed by the tool, so the document says 'not recorded in the tool output; owner to verify'"
  - "Worst-case data age is given in seconds, as the JSON holds it, to avoid a hand conversion"
requirements-completed: [BAT-03, BAT-04, POL-01, POL-02]
completed: 2026-10-12
---

# Phase 46 Plan 03: model JSON and decision document Summary

The two-run model is committed as machine output, pinned by a reproduction test, and written up for the owner in `hardware/BATTERY-MODEL.md`. Every figure is copied from the JSON. No interval and no pack is chosen; each owner-decision field reads `pending (owner)`.

## Tasks and commits

| Task | Commit |
|------|--------|
| 1 `battery-model.json` + `test_committed_model_json_is_reproduced` | 9eb9b37a |
| 2 `BATTERY-MODEL.md` + one pointer line in `BATTERY-RUN.md` | eca74c2f |

## Verification

- Command run three times (repo root, scratch path, from `hardware/` with relative paths): byte-identical each time, exit 0. No absolute path in the JSON (`grep -c '"/'` is 0).
- `pytest hardware -q --no-cov -n0`: 89 passed. `ruff check hardware`, `check_comment_history.py check`, `logtools.py selftest`: clean.
- Document verify script passes (each required heading exactly once, `does_not_measure` and `assumptions` verbatim, every autonomy figure present, `battery_percent(3300)` = 6 printed as `6 %`). Extra script check: gains, sweep tables and fit figures all found in the text.
- Greps: no `0 % at 3300`, no host or `nip.io`, no pre-selected wording; 7 `pending (owner)` fields.
- The four run inputs under `hardware/logs` are unchanged; `BATTERY-RUN.md` gained only the pointer line.

## Deviations from Plan

None - plan executed as written.

## Not verified

- Run one firmware label (the tool prints none): written as owner to verify.
- Pack protection, fit, charger current, price: all in the document's owner-to-verify list; nothing invented.
- On-device behaviour and the real standing current: Phase 47.

## Known Stubs

None. The `pending (owner)` fields are intentional.

## Self-Check: PASSED
