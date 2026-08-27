---
phase: quick-260827-lgt
plan: 01
subsystem: infra
tags: [illustrations, enrichment, adsbdb, icao-prefix, provenance]

requires:
  - phase: quick-260827-kih
    provides: enrich.correct_airline_name()/_AIRLINE_NAME_CORRECTIONS correction seam, and the drift-guard pattern (test_enrich check 24/32) this plan extends
provides:
  - Three new ICAO-prefix airline rows (HOP/Air France Hop, WMT/Wizz Air, KLJ/KlasJet) in enrich._ICAO_AIRLINE_PREFIXES
  - Two new illustration targets with real evidence (air-france-hop.png primary + air-france-hop-atr72.png secondary, klasjet.png primary), target total 38 -> 41
  - Wizz Air Malta deliberately mapped to the existing "Wizz Air" target with zero new artwork (QT-lgt-D-01 brand-consolidation precedent)
  - HANDOFF.md/VENDOR.md fully updated and renumbered to reflect the new 41-file plan, 8 outstanding
affects: [illustration-generation, enrich-py, illustrations-py]

tech-stack:
  added: []
  patterns:
    - "New evidence class: a carrier (HOP) where adsbdb's own live resolution is already correct and current - no correction-seam row needed or permitted"
    - "Accepted-divergence pattern extended: a more-specific adsbdb answer (WMT -> 'Wizz Air Malta') is not a misattribution when the project deliberately chose the parent-brand key"
    - "New verdict token [UNCONFIRMED-PREFIX] for a prefix corroborated by reference sources but never live-confirmed, distinct from [VERIFIED-CALLSIGN-MISS]"

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/assets/icons/illustrations/HANDOFF.md
    - server/assets/icons/illustrations/VENDOR.md

key-decisions:
  - "QT-lgt-D-01: Wizz Air Malta (WMT) maps to the existing 'Wizz Air' selection key, zero new illustration target/artwork - the EJU->easyJet brand-consolidation precedent"
  - "QT-lgt-D-03/D-07: HOP! Air France needs no _AIRLINE_NAME_CORRECTIONS row - adsbdb's own live resolution is already correct and current, the first carrier in this project where that's true"
  - "QT-lgt-D-04: Air France Hop gets primary (Embraer) + secondary (ATR72) art, MEDIUM confidence on which type is primary"
  - "QT-lgt-D-06: KlasJet's KLJ prefix was never live-confirmed (~25 adsbdb probes all missed) - materially lower confidence than every other row, flagged everywhere it appears"
  - "QT-lgt-D-02: Wizz Air UK (WUK) explicitly out of scope, not researched, must not be added as tidy-up"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "Three new ICAO-prefix rows (HOP/WMT/KLJ) resolve their intended airline names with zero network call, each carrying an honest evidence comment"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 36-39"
        status: pass
    human_judgment: false
  - id: D2
    description: "Three new illustration targets wired (air-france-hop.png, air-france-hop-atr72.png, klasjet.png); target total 41, outstanding 8; Wizz Air Malta reuse guard holds"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_illustrations.py checks 45 (updated) and 47 (new)"
        status: pass
      - kind: other
        ref: "server/plane/illustrations.py --targets | wc -l == 41; --outstanding | wc -l == 8"
        status: pass
    human_judgment: false
  - id: D3
    description: "HANDOFF.md and VENDOR.md fully updated: required-files counts, coverage-caveat bullets, renumbered prompts (1-41, diff-verified against --targets), new VENDOR.md subsection"
    verification:
      - kind: other
        ref: "diff of HANDOFF.md prompt filenames vs illustrations.py --targets output (exact match); scripts/check-attribution.sh; illustrations.py --validate"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full 9-harness suite, ruff, check-attribution.sh all green with enrich 39/39 and illustrations 47/47 visible in the aggregate run"
    verification:
      - kind: integration
        ref: "scripts/run-all-tests.sh"
        status: pass
    human_judgment: false
  - id: D5
    description: "Three PNG artwork files (air-france-hop.png, air-france-hop-atr72.png, klasjet.png) need to be generated externally and dropped in by the developer - no code check can verify visual correctness"
    verification: []
    human_judgment: true
    rationale: "Illustration generation requires an external AI image tool this environment does not have; nose-left orientation, livery accuracy, and type-matches-filename can only be confirmed by human eye per HANDOFF.md's own established process"

duration: 11min
completed: 2026-08-27
status: complete
---

# Quick Task 260827-lgt: Add HOP! Air France, Wizz Air Malta, and KlasJet Summary

**Three new carriers wired into the ICAO-prefix and illustration-target tables (HOP/WMT/KLJ), cross-checked against the official Paris Aéroport Orly airline list — HOP! Air France introduces the first "adsbdb is already correct" evidence class, Wizz Air Malta deliberately reuses the existing wizz-air.png with zero new artwork, and KlasJet is flagged everywhere as a materially lower-confidence entry.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-27T13:37:14Z
- **Completed:** 2026-08-27T13:48:00Z
- **Tasks:** 3 (Task 3 was verification/reporting only, no source edits)
- **Files modified:** 6

## Accomplishments

- `enrich._ICAO_AIRLINE_PREFIXES` gained three new rows: `HOP` -> `"Air France Hop"`, `WMT` -> `"Wizz Air"`, `KLJ` -> `"KlasJet"`, each with a block-comment evidence citation in the style of the existing `EJU`/`KMM`/`JAF`/`AIA` rows.
- `illustrations._ILLUSTRATION_TARGETS` gained two new primaries (`"Air France Hop"`, `"KlasJet"`) and one new secondary (`"Air France Hop"`/`"atr72"`), taking `target_filenames()` from 38 to 41 entries and `outstanding_filenames()` from 5 to 8.
- Live-verified against `api.adsbdb.com` this session: `HOP4001` resolves to `"Air France Hop"` (matches the prefix table exactly, no correction needed — the first such case in this project); `WMT3001` resolves to `"Wizz Air Malta"` (a real, more-specific answer than the deliberately-chosen `"Wizz Air"` parent-brand key — an accepted divergence, not a misattribution); `KLJ123` (synthetic) confirmed `"unknown callsign"`, consistent with this project's prior ~25-probe research that no real `KLJ` callsign has ever been observed.
- No `_AIRLINE_NAME_CORRECTIONS` row was added for any of the three prefixes — a new machine-checked guard (`test_enrich.py` check 39) asserts this absence so a future reader cannot silently "complete the job."
- `HANDOFF.md` and `VENDOR.md` fully updated: required-files counts (38→41), primaries (25→27), secondaries (5→6), three new coverage-caveat bullets, three new prompt sections inserted in `--targets` order and the full heading sequence renumbered 1–41 (diff-verified byte-for-byte against `--targets` output), and a new `VENDOR.md` subsection recording the Wizz Air Malta reuse as a deliberate non-outstanding item.

## Task Commits

1. **Task 1: Wire all three carriers into the illustration target table and the ICAO-prefix airline table, with regression coverage** - `00c62c2` (feat)
2. **Task 2: Extend the D-09 hand-off spec and the provenance record to cover the three new targets and the one deliberate reuse** - `d202f0d` (docs)
3. **Task 3: Full-gate verification and developer hand-off report** - no commit (verification/reporting only, zero source edits, per plan's explicit scope)

**Plan metadata:** (pending — orchestrator commits SUMMARY.md/STATE.md/ROADMAP.md separately)

## Files Created/Modified

- `server/plane/enrich.py` - three new `_ICAO_AIRLINE_PREFIXES` rows (HOP/WMT/KLJ) with full evidence comments
- `server/plane/illustrations.py` - two new primary targets + one new secondary target in `_ILLUSTRATION_TARGETS`; docstring and `_TYPE_SHAPE_BUCKETS` comments extended
- `server/test_enrich.py` - four new checks (36-39), `EXPECTED_CHECK_COUNT` 35 → 39
- `server/test_illustrations.py` - check 45's hardcoded total updated to 41, new check 47 (drift guard + Wizz reuse guard), `EXPECTED_CHECK_COUNT` 46 → 47
- `server/assets/icons/illustrations/HANDOFF.md` - required-files counts, three coverage-caveat bullets, three new prompt sections, full renumber to 41
- `server/assets/icons/illustrations/VENDOR.md` - new dated subsection recording target/outstanding count changes, live-curl evidence, and the Wizz Air Malta reuse

## Decisions Made

- **QT-lgt-D-01:** Wizz Air Malta (`WMT`) maps to the existing `"Wizz Air"` selection key — zero new illustration target, zero new artwork — the same shipped `EJU` → `"easyJet"` brand-consolidation precedent. Its fleet (A320/A321neo) and livery are brand-standard Wizz Air, visually indistinguishable at this project's flat side-profile illustration fidelity.
- **QT-lgt-D-02:** Wizz Air UK (`WUK`, IATA W9) is explicitly out of scope — not researched this session, no decision exists for it, must not be added as tidy-up.
- **QT-lgt-D-03/D-07:** HOP! Air France is filed as `"Air France Hop"` — the exact string `adsbdb` live-resolved. This is the first carrier in this project where adsbdb's own answer is already correct and current, so no `_AIRLINE_NAME_CORRECTIONS` row exists or is needed.
- **QT-lgt-D-04:** HOP! Air France gets primary (Embraer) + secondary (ATR72) art, since the mainline `air-france.png` (an A320) doesn't represent the regional fleet. The Embraer/ATR72 split is a MEDIUM-confidence judgment on relative fleet size, flagged as such and documented as a one-token-reversible choice.
- **QT-lgt-D-05:** KlasJet is filed as `"KlasJet"` (real camel-case trading style), single primary file, Boeing 737-800.
- **QT-lgt-D-06:** KlasJet's `KLJ` prefix carries materially lower confidence than every other row — never live-confirmed (~25 adsbdb probes all missed), weaker evidence than `KMM`'s confirmed-negative. Flagged with a new, deliberately distinct `[UNCONFIRMED-PREFIX]` verdict token in `illustrations.py`, and with explicit remediation pointers in every document that names it.
- **QT-lgt-D-08:** KlasJet's 737-800-vs-BBJ airframe question is surfaced as an open question for the developer at generation time in HANDOFF.md's prompt, not resolved unilaterally.

## Deviations from Plan

None — plan executed exactly as written. The one research step the plan explicitly delegated to Task 1 (finding a real, live-resolving `WMT` callsign for the test/evidence comment) was completed successfully: `WMT3001` resolves live to `"Wizz Air Malta"`, confirming the accepted-divergence framing rather than requiring the synthetic fallback the plan allowed for.

## Issues Encountered

- **No pre-existing Python virtual environment in this worktree.** Git worktrees don't carry build artifacts like `.venv/` — the main repo checkout has one, but this isolated worktree started without it. Created a fresh `server/.venv` using the same pinned Python 3.11 interpreter and installed `server/requirements.txt` + `server/requirements-dev.txt` (Pillow 12.3.0, requests 2.34.2, ruff 0.16.4, coverage 7.15.4) before any verification could run. This is tooling setup, not a code change, and is not committed (the venv is gitignored, confirmed via `git status`).

## User Setup Required

None — no external service configuration required. However, **three PNG artwork files must be generated externally by the developer** (this environment has no image-generation tool, per D-09, unchanged from every prior illustration-hand-off task):

**Files to generate** (drop into `server/assets/icons/illustrations/`):

| Filename | Aircraft type | Livery | Confidence |
|---|---|---|---|
| `air-france-hop.png` | Embraer E190 | Post-2019 Air France mainline white/blue scheme, small `HOP` titling — **not** the pre-2019 standalone HOP! livery | MEDIUM confidence on the Embraer-primary/ATR72-secondary split (QT-lgt-D-04) — not on the livery itself |
| `air-france-hop-atr72.png` | ATR 72-600 | Same Air France regional livery as the primary, on the turboprop airframe | Same MEDIUM-confidence split as the primary |
| `klasjet.png` | Boeing 737-800 | White fuselage, abstract light-blue/yellow tail design | **Lower confidence than every other entry in this project** — check against a real photo before generating; and the 737-800-vs-BBJ airframe choice is an open question for you to resolve at generation time (QT-lgt-D-08) — KlasJet's fleet mixes 737-300/500/800 with Boeing Business Jets |

**Wizz Air Malta needs NO artwork.** It deliberately reuses the already-vendored `wizz-air.png` (QT-lgt-D-01) — do not go looking for a fourth file.

**After generating the files**, run exactly what `HANDOFF.md`'s "After generating the files" section prescribes:

```
server/.venv/bin/python3 server/plane/illustrations.py --outstanding   # see what's missing, drop files in
server/.venv/bin/python3 server/plane/illustrations.py --validate      # exits 0 only when every file present passes
server/.venv/bin/python3 server/plane/illustrations.py --outstanding   # confirm what (if anything) remains
```

Then confirm by eye (no code check exists for either): nose points **left** in all three, and each shows the aircraft type its filename names.

**Reminder:** the outstanding list is now **8** files, not 3 — `royal-air-maroc-embraer.png` (Phase 3.1), `km-malta-airlines.png`/`tuifly-belgium.png` (`260827-jz6`), and `amelia.png`/`amelia-embraer.png` (`260827-kih`) were all already outstanding before this task; this task added three more (`air-france-hop.png`, `air-france-hop-atr72.png`, `klasjet.png`).

**No PNG artwork was generated, faked, or placed by this task.** `render.py`, `poll_loop.py`, and `detect.py` were deliberately untouched.

## Findings

Nothing discovered while running the gates contradicted this plan's research. Both live lookups performed this session matched the plan's expectations exactly:

- `HOP4001` → `"Air France Hop"` (a populated, correct, current result — matches QT-lgt-D-03's expectation precisely).
- `WMT3001` → `"Wizz Air Malta"` (a populated, correct, *more-specific* result — the accepted-divergence case QT-lgt-D-01/D-07 anticipated, not the Amelia/Avies wrong-carrier failure mode this plan explicitly asked to watch for).

No adsbdb misattribution was found for either `WMT` or `HOP`. No `_AIRLINE_NAME_CORRECTIONS` row was added beyond what QT-lgt-D-07 specifies.

## Next Phase Readiness

- No code readiness gaps — all automated gates green (9-harness suite, ruff, check-attribution.sh, illustrations.py --validate).
- Blocked only on the developer's external image-generation step for the three new files listed above (an existing, unchanged pattern from every prior illustration-hand-off task in this project).
- This is quick-task work, not part of a phase sequence — no phase advancement implications.

---
*Phase: quick-260827-lgt*
*Completed: 2026-08-27*

## Self-Check: PASSED

All claimed files exist on disk (server/plane/enrich.py, server/plane/illustrations.py, server/test_enrich.py, server/test_illustrations.py, server/assets/icons/illustrations/HANDOFF.md, server/assets/icons/illustrations/VENDOR.md, this SUMMARY.md). Both task commits (`00c62c2`, `d202f0d`) verified present in `git log --oneline --all`.
