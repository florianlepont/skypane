---
phase: quick-260921-v9c
plan: 01
subsystem: plane-detection
tags: [icao-prefixes, illustrations, enrich, adsbdb, airline-identification, provenance]

requires:
  - phase: quick-260827-kih
    provides: "the enrich.correct_airline_name()/_AIRLINE_NAME_CORRECTIONS correction seam this task's DJT row reuses"
  - phase: quick-260827-lgt
    provides: "the exact per-quick-task table/note shape (_ICAO_AIRLINE_PREFIXES row, optional correction row, _ILLUSTRATION_TARGETS tuple, VENDOR.md/HANDOFF.md record) this task follows"
provides:
  - "Eleven new ICAO prefix rows (CAJ, DJT, QAF, KAF, RJA, CTM, SRA, SVA, TFV, FGN, IPF) resolving statically via enrich.airline_from_callsign(), zero network calls"
  - "A real DJT flight attributed to La Compagnie on both the prefix-only fallback and a corrected adsbdb-hit path (the (DJT, 'Denver Jet') -> 'La Compagnie' correction row)"
  - "Nine vendored illustrations (target_filenames() 43 -> 52, target_airline_names() 27 -> 36), all reachable via select_illustration()'s Tier 2"
  - "The [DEVELOPER-OBSERVED] evidence-class token, defined in illustrations.py's docstring and in HANDOFF.md's new Verdict tokens glossary"
  - "A structural invariant test (every target airline has an unsuffixed primary file on disk) protecting the companion gallery's <img src> contract"
affects: [enrich, illustrations, companion-airlines-gallery, vendor-provenance]

tech-stack:
  added: []
  patterns:
    - "[DEVELOPER-OBSERVED] as a fourth evidence-class token alongside [VERIFIED-*]/[CITED: ...]/[UNCONFIRMED-PREFIX], for developer-witnessed-but-untranscribed observations"
    - "A shape-suffixed delivered filename can be deliberately vendored under the unsuffixed primary name when the companion gallery's primary-key-only <img src> contract would otherwise 404 (QT-v9c-D-04)"

key-files:
  created: []
  modified:
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - companion/test_status_pages.py
    - server/assets/icons/illustrations/VENDOR.md
    - server/assets/icons/illustrations/HANDOFF.md
    - server/assets/icons/illustrations/qatar-amiri-flight.png
    - server/assets/icons/illustrations/royal-jordanian.png
    - server/assets/icons/illustrations/saudi-royal-aviation.png
    - server/assets/icons/illustrations/saudia.png
    - server/assets/icons/illustrations/south-korea-government.png
    - server/assets/icons/illustrations/french-air-force.png
    - server/assets/icons/illustrations/la-compagnie.png
    - server/assets/icons/illustrations/gendarmerie-nationale.png
    - server/assets/icons/illustrations/iraqi-government.png

key-decisions:
  - "QT-v9c-D-01: CAJ (Air Caraïbes Atlantique) reuses the existing 'Air Caraïbes' key - zero new artwork, same precedent as WMT/EJU"
  - "QT-v9c-D-02: DJT -> 'La Compagnie' supersedes Phase 3.1's [UNRESOLVED] verdict, cleared by a real observed flight; the (DJT, 'Denver Jet') correction row is defensive, weaker evidence than the AIA precedent since 'Denver Jet' comes from an airline-endpoint probe, never a real callsign hit"
  - "QT-v9c-D-03: TFV is a defensive alias for a probable TFV60HA/TVF transposition, not a confirmed second ICAO code - reuses 'Transavia France', zero new artwork"
  - "QT-v9c-D-04: French Air Force's delivered file (french-air-force-a330.png) is vendored under the unsuffixed primary name french-air-force.png, not as an a330-suffixed secondary, because the companion gallery builds every card's <img src> from the primary key alone"
  - "QT-v9c-D-05: FGN (Gendarmerie Nationale) and IPF (Iraqi Government) are included as state operators with their own artwork, reversing an earlier 'not a real airline' scoping decision"
  - "QT-v9c-D-06: DEF, QEM, and the undelivered saudi-special-flight.png are deliberately out of scope - recorded as standing exclusions in both enrich.py and HANDOFF.md"
  - "Standing instruction: no _AIRLINE_NAME_CORRECTIONS row for RJA or SVA without a real observed transcript - both are ordinary commercial carriers whose adsbdb behavior is genuinely unknown"

requirements-completed: [QUICK-260921-v9c]

coverage:
  - id: D1
    description: "Eleven new ICAO prefixes (CAJ, DJT, QAF, KAF, RJA, CTM, SRA, SVA, TFV, FGN, IPF) each resolve through enrich.airline_from_callsign() to the exact intended airline-name string, zero network calls, zero manual_resolutions entries; DEF and QEM resolve to nothing"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "server/test_enrich.py — _v9c_eleven_new_prefixes_and_djt_correction_and_exclusions (60/60 checks pass)"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py — D-07 drift guard, cross-table agreement checks (unmodified, still pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A real DJT flight is attributed to La Compagnie on BOTH resolution paths: the prefix-only fallback and a corrected adsbdb-hit that returns 'Denver Jet'"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "server/test_enrich.py — _v9c_eleven_new_prefixes_and_djt_correction_and_exclusions (correct_airline_name assertion)"
        status: pass
      - kind: integration
        ref: "Manual end-to-end check via resolve_route() with a fake transport returning 'Denver Jet' (documented in this SUMMARY's Non-Vacuousness section)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nine externally-generated illustrations vendored byte-identically, each reachable by select_illustration() for its own carrier through Tier 2; --validate exits 0 with zero outstanding and zero unexpected files"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "server/test_illustrations.py — full suite (60/60 checks pass)"
        status: pass
      - kind: unit
        ref: "server/plane/illustrations.py --validate / --outstanding (0 outstanding, PASS on all 52 targets)"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py, server/test_render.py (311/311, 134/134)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The companion Airlines gallery renders one card per target airline and every card's image URL is a target_filenames() member - no 404s"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py — _every_card_image_source_passes_route_membership_test, _gallery_renders_one_card_per_target_airline (311/311)"
        status: pass
    human_judgment: false
  - id: D5
    description: "DEF, QEM, and saudi-special-flight.png are absent from every table and from the asset directory, with the reason recorded in-tree"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "server/test_enrich.py (DEF/QEM -> None), server/test_illustrations.py (QT-v9c-D-06 guard check)"
        status: pass
      - kind: other
        ref: "HANDOFF.md Coverage caveat section, VENDOR.md Quick task 260921-v9c section — both document all three exclusions"
        status: pass
    human_judgment: false
  - id: D6
    description: "Every hardcoded registry-count constant in the test tree updated from the machine-reported number (43->52, 27->36); three harnesses stay green"
    requirement: QUICK-260921-v9c
    verification:
      - kind: unit
        ref: "server/test_illustrations.py, companion/test_status_pages.py, server/test_render.py — full run (60/60, 311/311, 134/134)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-09-21
status: complete
---

# Quick Task 260921-v9c: Add Newly-Identified ICAO Airline Prefix Summary

**Eleven new ICAO prefixes (including a superseded-verdict La Compagnie/DJT resolution) and nine vendored illustrations, all backed by a new [DEVELOPER-OBSERVED] evidence-class token**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-09-21T21:00Z (approx, four commits between 22:51 and 22:59 local time, plus reading/planning time before)
- **Tasks:** 3 (plus one immediate follow-up fix commit, see Deviations)
- **Files modified:** 16 (2 tables, 3 test harnesses, 2 provenance docs, 9 new PNGs)

## Accomplishments

- Vendored nine developer-delivered illustrations (`qatar-amiri-flight.png`, `royal-jordanian.png`, `saudi-royal-aviation.png`, `saudia.png`, `south-korea-government.png`, `la-compagnie.png`, `gendarmerie-nationale.png`, `iraqi-government.png`, and `french-air-force-a330.png` renamed to `french-air-force.png` per QT-v9c-D-04) and registered them as `_ILLUSTRATION_TARGETS` — `target_filenames()` 43 → 52, `target_airline_names()` 27 → 36, zero outstanding both before and after
- Retired the superseded `_unresolved/la-compagnie.png` draft (different bytes from the fresh regenerated file) and reconciled both provenance docs to describe La Compagnie's new shipped status
- Added eleven new `_ICAO_AIRLINE_PREFIXES` rows (`CAJ`, `DJT`, `QAF`, `KAF`, `RJA`, `CTM`, `SRA`, `SVA`, `TFV`, `FGN`, `IPF`) and one `_AIRLINE_NAME_CORRECTIONS` row (`(DJT, "Denver Jet") -> "La Compagnie"`), each backed by the developer's own 2026-09-21 Orly observation
- Introduced and documented the `[DEVELOPER-OBSERVED]` evidence-class token (weaker than every `[VERIFIED-*]`/`[CITED: ...]` token already in use) in `illustrations.py`'s docstring and a new "Verdict tokens" glossary in `HANDOFF.md`
- Added three new machine checks: a nine-new-targets + QT-v9c-D-06 exclusion guard, a structural "every airline has an unsuffixed primary file" invariant (protecting the companion gallery's `<img src>` contract), and an eleven-prefix + DJT-correction + DEF/QEM-exclusion check in `test_enrich.py`
- Fixed a pre-existing drift in `HANDOFF.md`: the "Airline secondary-variant files" sub-list was two entries behind the machine (the two Air Caraïbes secondaries from a parallel 2026-08-27 session) even though the intro's running total already counted them — all three sub-lists now sum to exactly 52

## Task Commits

Each task was committed atomically:

1. **Task 1: Vendor the nine delivered illustrations and register them as targets** - `458a3d7` (feat)
2. **Follow-up fix: correct aircraft-type claims found on visual inspection** - `60e2137` (fix) — see Deviations
3. **Task 2: Add the eleven ICAO prefix rows and the DJT name-correction row** - `16ee525` (feat)
4. **Task 3: Record provenance and decisions in VENDOR.md and HANDOFF.md** - `4736ffe` (docs)

**Plan metadata:** commit pending (orchestrator's separate docs commit)

## Files Created/Modified

- `server/plane/illustrations.py` - Nine new `_ILLUSTRATION_TARGETS` entries, new docstring section, new evidence-class documentation
- `server/plane/enrich.py` - Eleven new `_ICAO_AIRLINE_PREFIXES` rows, one new `_AIRLINE_NAME_CORRECTIONS` row, header comment with the batch's two shared caveats
- `server/test_illustrations.py` - `EXPECTED_CHECK_COUNT` 58 → 60, two count-constant updates (43→52, 27→36), two new checks
- `server/test_enrich.py` - `EXPECTED_CHECK_COUNT` 59 → 60, one new check covering all eleven prefixes + DJT correction + DEF/QEM exclusion
- `companion/test_status_pages.py` - Five stale count mentions (43→52, 27→36) corrected — the three explicitly named in the plan's `_VENDORED_ILLUSTRATION_PATHS` section plus two further "(27 against today's data)" prose mentions found during execution (gallery-card-count and filter-bar-count check descriptions) — see Deviations
- `server/assets/icons/illustrations/VENDOR.md` - New "Quick task 260921-v9c" per-file provenance section, `_unresolved/` table reconciliation, Phase 3.1 exclusion bullet status change
- `server/assets/icons/illustrations/HANDOFF.md` - Running totals updated to 52, sub-list drift fix, new "Verdict tokens" glossary, new french-air-force.png rename subsection, new standing-decision bullets
- Nine new PNGs in `server/assets/icons/illustrations/`
- `server/assets/icons/illustrations/_unresolved/la-compagnie.png` - removed (superseded draft)

## Decisions Made

See `key-decisions` in frontmatter (QT-v9c-D-01 through D-06, plus the RJA/SVA standing instruction) — all cited from the plan and followed as specified, with one addition: the plan's Task 1 action text pre-wrote aircraft-type descriptions for the nine notes before the delivered art was inspected. This session inspected each of the nine PNGs (Read tool image view) and found five type mismatches — corrected in the follow-up fix commit rather than left inaccurate. See Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected five aircraft-type claims in the new `_ILLUSTRATION_TARGETS` notes**
- **Found during:** Task 1, after the initial commit, during preparation for Task 3's VENDOR.md provenance table (which required accurate "aircraft type actually depicted" data)
- **Issue:** The plan's Task 1 action text specified aircraft types for each of the nine new targets (e.g. "Airbus ACJ320" for Qatar Amiri Flight, "Airbus A320" for Royal Jordanian, "Boeing 747-8" for Saudi Royal Aviation, "Airbus A350-900" for La Compagnie, "Airbus H145" for Gendarmerie Nationale) before any of the delivered files had been visually inspected. Visual inspection (Read tool image view of all nine PNGs) found five of these were wrong: La Compagnie is labelled "AIRBUS A321neo LR" on the fuselage (not A350-900); Qatar Amiri Flight depicts a standard Qatar Airways commercial "QATAR" livery A320 with no visible registration (not a distinct ACJ320 VIP scheme, and the tail A7-MBK claim was unconfirmed); Royal Jordanian depicts a Boeing 787-8 Dreamliner, registration JY-BAA (not A320); Saudi Royal Aviation depicts a Boeing 777-300ER in "KINGDOM OF SAUDI ARABIA" livery, registration HZ-HM5 (not a 747-8); Gendarmerie Nationale's airframe is labelled "EC145 AIRBUS" (not "H145").
- **Fix:** Corrected all five notes in `server/plane/illustrations.py` to describe what is actually depicted, citing the visible registration/labelling where present. South Korea Government (747-8i, tail 22-001) and French Air Force (A330 MRTT Phénix) were already accurate and left unchanged.
- **Files modified:** `server/plane/illustrations.py`
- **Verification:** `server/test_illustrations.py` and `server/test_enrich.py` both re-ran at 60/60 after the fix (no selection-key, filename, or table-membership logic changed — text-only correction)
- **Committed in:** `60e2137`

**2. [Rule 1 - Bug] Corrected two additional stale "27" prose mentions in `companion/test_status_pages.py` beyond the plan's explicit list**
- **Found during:** Task 1, while updating the count constants
- **Issue:** The plan explicitly named two "further" stale prose count mentions to fix in `companion/test_status_pages.py` (the gallery-visible-illustrations measurement comment and the datalist check's parenthetical) beyond the three in the `_VENDORED_ILLUSTRATION_PATHS` section. A `grep` for the same `"(27...)"` pattern found two more: the gallery-card-count check's description (`"(27 against today's data)"`) and the filter-bar-count check's description (`"the real (27) card total"`) — same class of staleness, not explicitly named in the plan's enumeration.
- **Fix:** Updated both to 36, matching the rest of the file's corrected counts, for internal consistency (the plan's own must_haves truth requires "every hardcoded registry-count constant in the test tree is updated from the number illustrations.py itself reports").
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** `companion/test_status_pages.py` full suite re-ran at 311/311 after the change (these are description strings only — no assertion logic changed)
- **Committed in:** `458a3d7`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bug fixes — inaccurate documentation)
**Impact on plan:** Both fixes correct documentation accuracy; neither changes selection logic, filenames, or table membership. No scope creep — both are within the batch of files the plan already scoped for editing.

## Non-Vacuousness Spot-Check (per plan's `<verification>` item 7)

Temporarily renamed the "French Air Force" `_ILLUSTRATION_TARGETS` entry to "French Air Forcee" (one extra character) and re-ran the harnesses:

- **After Task 1 alone** (before Task 2's prefix table existed): `server/test_illustrations.py` dropped from 60/60 to 57/60, with three named failures — the pre-existing "every vendored .png is a target_filenames() member" check, the new nine-targets/QT-v9c-D-06 guard check, and the new every-airline-has-an-unsuffixed-primary check, each naming `french-air-force.png`/`'French Air Forcee'` explicitly.
- **After Task 2 also landed** (full combined check per the plan's overall `<verification>` item 7): re-ran both harnesses together. `server/test_illustrations.py` again failed the same three checks by name; `server/test_enrich.py` additionally dropped from 60/60 to 59/60, failing the D-07 drift guard by name (`"prefix table produces airline name(s) with no illustration target: ['French Air Force']"`).
- Restored the entry immediately after each run; `git status` showed no diff afterward and both harnesses returned to 60/60.

This confirms all new checks are non-vacuous — they fail specifically and by name when the invariant they claim to protect is actually broken.

**DJT end-to-end resolution (must_haves truth, verified manually, not a persisted test):**
- Prefix-only fallback: `enrich.airline_from_callsign("DJT4001")` → `"La Compagnie"`.
- Corrected adsbdb-hit path: `enrich.resolve_route("DJT4001", cache, transport=<fake returning "Denver Jet">)` → route with `airline_name == "La Compagnie"`, source `"fresh_hit"`; the cache entry itself still holds the raw `"Denver Jet"` string (correction-on-read, not on-write, matching the AIA precedent).

## Issues Encountered

**Plan/verify-script inconsistency (not a plan defect requiring a fix, documented for the record):** Task 1's `<verify>` automated block includes `bash scripts/check-attribution.sh | tail -2` under `set -e`, which would fail at that point in the sequence — the plan's own objective `<key_links>` section explicitly states the nine new PNGs "need their VENDOR.md rows (Task 3) before that script passes on the final tree." Ran `check-attribution.sh` at Task 1 for visibility (it failed exactly as the key_links note predicted, listing the eight then-undocumented PNGs — `french-air-force.png` was the ninth already-caught one) and deferred the passing assertion to Task 3, where the plan's own verify block runs the identical command first and where it does pass (confirmed: "PASS: 68 asset file(s) all attributed"). No plan content was changed; this is a sequencing note for a future planner.

## Full Suite Result

`PYTHON=server/.venv/bin/python3 scripts/run-all-tests.sh` — **PASS, zero failures.** All 21 harnesses green, including `server/test_illustrations.py` (60/60), `server/test_enrich.py` (60/60), `companion/test_status_pages.py` (311/311), and `server/test_render.py` (134/134). `companion/test_browser_ux.py` reported its own environment-level SKIP (playwright not installed in this sandbox — the harness's own documented dev-only-dependency skip, not a failure) and did not affect the overall PASS result. No named baseline exceptions were needed — there were no failures to compare against a baseline.

## Deferred Items (for the next session, per the plan's `<output>` spec)

- **`DEF`** — a privately-registered Cirrus SR22T (tail D-EFGM), not an operator. No prefix row, no target, no artwork. Not a gap; deliberately out of scope (QT-v9c-D-06).
- **`QEM`** — flagged by the developer as NOT Qatar Amiri Flight's official prefix; the aircraft actually observed under this code (Airbus ACJ320, tail A7-MBK) belongs to Qatar Amiri Flight and is reachable through this batch's `QAF` row instead. No prefix row, no target, no artwork. Not a gap; deliberately out of scope (QT-v9c-D-06).
- **`saudi-special-flight.png`** — a tenth file the developer delivered alongside the nine vendored this session, with no confirmed operator behind it (name says "Saudi", only candidate prefix discussed was for a Qatari aircraft). Neither copied nor referenced anywhere in this repo. Deferred to a future session — do not add as tidy-up without new evidence.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 52 illustration targets are vendored, validated, and zero outstanding; the companion Airlines gallery and the panel's Tier 1/2 selection both reach every new carrier's own art.
- Forty prefixes now resolve statically in `_ICAO_AIRLINE_PREFIXES` (29 pre-existing + 11 new), all cross-checked against `illustrations.target_airline_names()` by the unmodified D-07 drift guard.
- No blockers for future sessions; the three deferred items above are explicitly recorded so they are picked up from this record rather than rediscovered from memory.

## Self-Check: PASSED

All key-files (16) found on disk, including the nine vendored PNGs and the two provenance docs. The superseded `_unresolved/la-compagnie.png` draft confirmed absent. All four task commit hashes (`458a3d7`, `60e2137`, `16ee525`, `4736ffe`) confirmed present in git log.

---
*Phase: quick-260921-v9c*
*Completed: 2026-09-21*
