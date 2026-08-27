---
phase: quick-260827-kih
plan: 01
subsystem: enrichment
tags: [adsbdb, illustration-selection, correction-seam, provenance]

requires:
  - phase: quick-260827-hyy
    provides: enrich.airline_from_callsign()/_ICAO_AIRLINE_PREFIXES (the prefix-only fallback path the new seam's invariant is checked against)
  - phase: quick-260827-jz6
    provides: KM Malta Airlines/TUIfly Belgium target airlines (deliberately left unchanged by this plan)
provides:
  - enrich._AIRLINE_NAME_CORRECTIONS / correct_airline_name() / apply_airline_name_correction() (single prefix-scoped correction seam)
  - Four vendored illustration files renamed to their carriers' real current names (air-corsica, air-corsica-atr72, asl-airlines-france, corsair)
  - Amelia added as a new illustration target (primary + Embraer secondary, artwork outstanding)
affects: [any future carrier-naming quick task, a future JAF/TUIfly-Belgium correction decision, external illustration-generation batch]

tech-stack:
  added: []
  patterns:
    - "Prefix-scoped correction seam keyed on (ICAO callsign prefix, exact upstream string) rather than a global string replace"
    - "Correction applied on cache read, never on cache write - persisted state stays a faithful record of upstream API output"
    - "Machine-checked cross-table invariant between a correction table and a static fallback table, asserted in tests rather than assumed"

key-files:
  created:
    - server/fixtures/adsbdb_hit_AIA6412.json
  modified:
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/plane/render.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_render.py
    - server/fixtures/README.md
    - server/assets/icons/VENDOR.md
    - server/assets/icons/illustrations/HANDOFF.md
    - server/assets/icons/illustrations/VENDOR.md
    - server/assets/icons/illustrations/ccm-airlines.png -> air-corsica.png (git mv)
    - server/assets/icons/illustrations/ccm-airlines-atr72.png -> air-corsica-atr72.png (git mv)
    - server/assets/icons/illustrations/europe-airpost.png -> asl-airlines-france.png (git mv)
    - server/assets/icons/illustrations/corsairfly.png -> corsair.png (git mv)

key-decisions:
  - "QT-kih-D-01: one correction table keyed on (ICAO prefix, exact upstream string), one function, one call site - never a global string replace"
  - "QT-kih-D-02: cache stores adsbdb's raw payload; correction applied on read only - an already-deployed poll_state.json needs zero migration"
  - "QT-kih-D-03: the prefix-only fallback table already holds corrected values by construction; a machine-checked invariant proves the two tables agree"
  - "QT-kih-D-04: the four renamed files carry over their VENDOR.md digests verbatim rather than recomputing them - the bytes did not change"
  - "QT-kih-D-05: Amelia filed as 'Amelia' (not 'Amelia International'); primary A320, secondary Embraer E145 (moderate-confidence livery, flagged for developer verification)"
  - "QT-kih-D-06: supersedes, for FPO/CRL/CCM only, Phase 3.1 P-01/D-04, 03.1-LIVE-RESOLUTION.md Step B/C, and 260827-hyy's D-01"
  - "QT-kih-D-07: TUIfly Belgium (JAF) and KM Malta Airlines (KMM) deliberately left untouched - the correction seam was NOT extended to JAF this session"
  - "QT-kih-D-08: render.py's P-01 display alias retained unchanged as a defensive no-op; comment-only update"

patterns-established:
  - "Illustration/caption correctness now flows through one seam (enrich.correct_airline_name()) rather than requiring every downstream consumer to special-case a stale upstream string"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "Prefix-scoped correction seam (_AIRLINE_NAME_CORRECTIONS/correct_airline_name()/apply_airline_name_correction()) applied at the single seam inside lookup_route(), covering fresh-hit, cached-hit, and prefix-only paths identically"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 28-33"
        status: pass
      - kind: unit
        ref: "server/test_enrich.py check 32 (cross-table invariant, D-kih-03)"
        status: pass
    human_judgment: false
  - id: D2
    description: "AIA (Amelia) correction row added with real live-curl evidence; the real adsbdb response recorded as a fixture"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 28, 30, 31"
        status: pass
      - kind: other
        ref: "server/fixtures/adsbdb_hit_AIA6412.json (real captured 200 response, curl https://api.adsbdb.com/v0/callsign/AIA6412, 2026-08-27)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Three stale-brand carriers (FPO/CRL/CCM) corrected end to end (resolve_route -> select_illustration -> caption text); a corrected-away string under an unrelated prefix is provably left alone"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_enrich.py checks 34-35"
        status: pass
      - kind: unit
        ref: "server/test_render.py check 42"
        status: pass
      - kind: other
        ref: "Live demonstration in Task 4 (see below): resolve_route()+select_illustration()+_flight_line2_text() against all four corrections plus the negative unrelated-prefix case, real printed values recorded"
        status: pass
    human_judgment: false
  - id: D4
    description: "Four illustration files renamed with git mv (history preserved); VENDOR.md digests carried over and re-verified against the renamed files on disk"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_illustrations.py check 46"
        status: pass
      - kind: other
        ref: "git log --follow --oneline for all four renamed paths (Task 4); shasum -a 256 re-derivation cross-checked against VENDOR.md rows"
        status: pass
    human_judgment: false
  - id: D5
    description: "Amelia added as a primary + Embraer secondary illustration target; no artwork fabricated, hand-off report names the two files with type/livery for external generation"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_illustrations.py check 45; server/plane/illustrations.py --outstanding lists 5 files"
        status: pass
    human_judgment: true
    rationale: "Actual PNG artwork generation is an external, human/AI-image-tool step (D-09) outside this environment's capability - the developer must review and confirm nose-left orientation and type-matches-filename by eye once generated, per this project's established practice."
  - id: D6
    description: "HANDOFF.md and VENDOR.md rewritten around the new naming rule with full supersession record and the JAF/KMM carve-out; prompt-section headings match --targets line for line"
    verification:
      - kind: other
        ref: "diff between `illustrations.py --targets` output and HANDOFF.md's extracted section headings (Task 4, exit 0)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-27
status: complete
---

# Quick Task 260827-kih: Introduce an adsbdb-resolved-name correction mechanism Summary

**Built a single prefix-scoped correction seam in `enrich.py` that reconciles adsbdb's stale/wrong airline names against the callsign's ICAO prefix on every read — fixed three real stale-brand mismatches (Air Corsica, ASL Airlines France, Corsair) and one outright wrong-carrier attribution (Amelia, previously mislabeled as the defunct Estonian carrier "Avies"), with a machine-checked invariant proving the fix and its illustration selection stay in agreement.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-27T15:02Z (plan commit)
- **Completed:** 2026-08-27T15:30Z (approx, this SUMMARY)
- **Tasks:** 4/4 completed
- **Files modified:** 14 (10 modified + 1 created + 4 renamed via `git mv`, counted once each)

## Accomplishments

- Built the one-table, one-function, one-call-site correction seam (`_AIRLINE_NAME_CORRECTIONS` / `correct_airline_name()` / `apply_airline_name_correction()`) inside `enrich.lookup_route()`, converging the cache-hit and fresh-fetch success paths on a single `apply_airline_name_correction()` return.
- Discovered and fixed a real wrong-carrier-attribution bug live: `adsbdb`'s `AIA` callsign prefix (a real Amelia flight, `AIA6412`) resolves to `"Avies"`, a different, defunct Estonian carrier that ceased operations in 2016 and happened to hold the same ICAO code. Captured the real live response verbatim as a fixture.
- Corrected three real stale-brand mismatches (Air Corsica, ASL Airlines France, Corsair) that Phase 3.1 and quick task `260827-hyy` had deliberately mirrored verbatim because no correction mechanism existed then — renamed their four vendored illustration files with `git mv` (history preserved, digests carried over) so the panel's illustration filenames match the carriers' real current names too.
- Added a machine-checked cross-table invariant (`test_enrich.py` check 32) that fails the suite the moment `_AIRLINE_NAME_CORRECTIONS` and `_ICAO_AIRLINE_PREFIXES` disagree — the property that proves the adsbdb-hit path and the prefix-only fallback path always agree on the same displayed/selected name.
- Deliberately left TUIfly Belgium (`JAF`) and KM Malta Airlines (`KMM`) untouched, recording the developer's explicit decision not to extend the new seam there this session, in four places (`enrich.py`, `illustrations.py`, `HANDOFF.md`, `VENDOR.md`).
- Rewrote `HANDOFF.md`'s Naming rules section and `illustrations/VENDOR.md`'s provenance record around the new (inverted) rule, with the full supersession chain named explicitly.

## Task Commits

1. **Task 1: Build the prefix-scoped correction seam and land Amelia through it** - `c3ba883` (feat)
2. **Task 2: Apply the seam to the three stale-brand carriers and rename their four vendored files** - `1e0b111` (feat)
3. **Task 3: Rewrite the hand-off spec and the provenance record around the new naming rule** - `b6bd327` (docs)
4. **Task 4: Full-gate verification and developer hand-off report** - (no source edits; this SUMMARY records the verification output)

## Files Created/Modified

- `server/plane/enrich.py` — `_AIRLINE_NAME_CORRECTIONS`, `correct_airline_name()`, `apply_airline_name_correction()`; `lookup_route()` restructured to converge on the seam; `_AIRLINE_PREFIX_SHAPE_RE` moved up beside `_CALLSIGN_SAFE_RE`; `AIA`/`FPO`/`CRL`/`CCM` prefix-table values corrected
- `server/plane/illustrations.py` — Amelia primary + Embraer secondary added to `_ILLUSTRATION_TARGETS`; three renamed-carrier entries updated; `_LIVE_RESOLVED_AIRLINES`'s CCM entry corrected; module docstring's naming rule inverted with the full supersession record
- `server/plane/render.py` — comment-only supersession note above `_AIRLINE_DISPLAY_ALIASES` (QT-kih-D-08); no logic/table change
- `server/fixtures/adsbdb_hit_AIA6412.json` — real captured 200 response from `curl https://api.adsbdb.com/v0/callsign/AIA6412` (2026-08-27), attributing `AIA` to the defunct Estonian carrier "Avies"
- `server/fixtures/README.md` — provenance entry for the new fixture
- `server/test_enrich.py` — 27 → 35 checks (correction seam, cross-table invariant, hostile-input battery, three-carrier end-to-end)
- `server/test_illustrations.py` — 44 → 46 checks (Amelia targets, inverted current-brand-vs-stale check, renamed-file existence check)
- `server/test_render.py` — 41 → 42 checks (corrected-route caption + display-alias no-op)
- `server/assets/icons/VENDOR.md` — one filename mention renamed
- `server/assets/icons/illustrations/VENDOR.md` — four digest-table rows renamed (digests carried over); dated `260827-kih` subsection added; `_unresolved/amelia-international.png`'s disposition updated
- `server/assets/icons/illustrations/HANDOFF.md` — 38-file plan; Naming rules inverted; Coverage caveat rewritten for Amelia; prompt sections renamed/inserted/renumbered to match `--targets` exactly
- `server/assets/icons/illustrations/ccm-airlines.png` → `air-corsica.png` (git mv, history preserved)
- `server/assets/icons/illustrations/ccm-airlines-atr72.png` → `air-corsica-atr72.png` (git mv, history preserved)
- `server/assets/icons/illustrations/europe-airpost.png` → `asl-airlines-france.png` (git mv, history preserved)
- `server/assets/icons/illustrations/corsairfly.png` → `corsair.png` (git mv, history preserved)

## Decisions Made

See `key-decisions` in frontmatter (QT-kih-D-01 through D-08) — all eight decisions from the plan's objective were implemented as specified, with no deviation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `apply_airline_name_correction()` did not guard against `route.get()` raising**

- **Found during:** Task 1, writing check 33's hostile-input battery (a route whose `.get()` raises).
- **Issue:** The plan's behavior spec explicitly requires both new functions to "never raise... for... a route whose `.get` raises", but the first implementation of `apply_airline_name_correction()` called `route.get("airline_name")` without a try/except, so a route object with a raising `.get()` would propagate the exception.
- **Fix:** Wrapped the `route.get("airline_name")` call in a `try/except Exception: return route`, mirroring `illustrations.select_illustration()`'s existing defensive shape for exactly this case.
- **Files modified:** `server/plane/enrich.py`
- **Commit:** `c3ba883` (folded into Task 1's commit, caught before that commit was made)

**2. [Rule 1 - Bug] Stale/inaccurate comments in `enrich.py` and `illustrations.py` describing the (now partly superseded) old rule**

- **Found during:** Task 1/Task 2, while writing the correction seam's own documentation.
- **Issue:** Two pre-existing comment blocks became actively misleading once this plan's changes landed: (a) `enrich.py`'s comment above `_ICAO_AIRLINE_PREFIXES` said "Amelia International and La Compagnie are deliberately absent" — no longer true for Amelia once the `AIA` row was added in Task 1; (b) `illustrations.py`'s comment above `_ILLUSTRATION_TARGETS` pointed at the (soon-to-be-renamed) "Filenames mirror the data source" docstring section for Europe Airpost/Corsairfly guidance.
- **Fix:** Rewrote both comments to reflect the current state — (a) now says La Compagnie alone is absent, with Amelia's new status explained; (b) now points at the new "Filenames mirror the carrier's real current name" section.
- **Files modified:** `server/plane/enrich.py`, `server/plane/illustrations.py`
- **Commits:** `c3ba883`, `1e0b111`

No other deviations — every other task action was executed exactly as the plan specified.

## Task 4: Live Verification Output

All commands below were run for real against the actual code in this worktree; output is reproduced verbatim (trimmed where noted).

### 1. Full 9-harness suite (`scripts/run-all-tests.sh`)

```
dither: 6/6 checks pass
enrich: 35/35 checks pass
illustrations: 46/46 checks pass
pipeline-e2e: 5/5 checks pass
plane-detection: 28/28 checks pass
poll-loop: 5/5 checks pass
render: 42/42 checks pass
runway-config: 14/14 checks pass
poll-cycle: 17/17 checks pass
==> Coverage report: TOTAL 1096 stmts, 205 miss, 81% (floor 75%)
==> Result: PASS
```

### 2. Linter (`ruff check .`)

```
All checks passed!
```

### 3. Attribution checker (`scripts/check-attribution.sh`)

```
PASS: 51 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text.
```

### 4. Illustration validator

`--validate` exits 0, no unexpected-file report. `--targets` lists 38 files (verified: `wc -l` = 38). `--outstanding` lists exactly 5:

```
km-malta-airlines.png
tuifly-belgium.png
amelia.png
royal-air-maroc-embraer.png
amelia-embraer.png
```

### 5. `git log --follow` for all four renamed asset paths

```
$ git log --follow --oneline -- server/assets/icons/illustrations/air-corsica.png
1e0b111 feat(260827-kih-02): apply the correction seam...
a678843 Add airline aircraft illustrations

$ git log --follow --oneline -- server/assets/icons/illustrations/air-corsica-atr72.png
1e0b111 feat(260827-kih-02): apply the correction seam...
e0193e8 feat(03.1-05): register provenance for 25/26 delivered illustrations...

$ git log --follow --oneline -- server/assets/icons/illustrations/asl-airlines-france.png
1e0b111 feat(260827-kih-02): apply the correction seam...
e0193e8 feat(03.1-05): register provenance for 25/26 delivered illustrations...

$ git log --follow --oneline -- server/assets/icons/illustrations/corsair.png
1e0b111 feat(260827-kih-02): apply the correction seam...
e0193e8 feat(03.1-05): register provenance for 25/26 delivered illustrations...
```

All four reach past this session's rename commit into the file's original life under its previous name.

### 6. Live end-to-end demonstration against the real code (throwaway in-memory cache, no network, nothing written to `server/state/poll_state.json`)

```
=== Live demonstration: four corrections through resolve_route() + select_illustration() + _flight_line2_text() ===
callsign=AIA6412 upstream_string='Avies' -> airline_name='Amelia' source=fresh_hit illustration=generic-a320.png caption='Amelia · A320'
callsign=FPO701 upstream_string='Europe Airpost' -> airline_name='ASL Airlines France' source=fresh_hit illustration=asl-airlines-france.png caption='ASL Airlines France · 737-800'
callsign=CRL8025 upstream_string='Corsairfly' -> airline_name='Corsair' source=fresh_hit illustration=corsair.png caption='Corsair · A330-900neo'
callsign=CCM21AW upstream_string='CCM Airlines' -> airline_name='Air Corsica' source=fresh_hit illustration=air-corsica.png caption='Air Corsica · A320'

=== Negative case: corrected-away string under an UNRELATED prefix must come back untouched ===
callsign=ZZZ9999 upstream_string='CCM Airlines' -> airline_name='CCM Airlines' source=fresh_hit (expected unchanged)

=== QT-kih-D-02: a pre-correction-shaped cache entry (as an already-deployed poll_state.json would hold) ===
resolve_route() against the hand-seeded pre-correction cache -> airline_name='Amelia' source=cache_hit
the cache entry itself still holds the raw upstream string: 'Avies'
```

Amelia's illustration correctly falls to `generic-a320.png` (Tier 3, correct-shape neutral fallback) rather than a wrong-brand file, because `amelia.png` does not exist on disk yet — exactly the expected degradation while its artwork is outstanding. The three renamed carriers all resolve to their real, on-disk renamed files. The negative case proves the correction is genuinely prefix-scoped, not a blind string replace. The hand-seeded cache case proves QT-kih-D-02: an already-deployed server needs no cache migration to start showing corrected names.

## Developer Hand-off — Outstanding Illustration Artwork

**No PNG artwork was generated, faked, or placed by this session.** Five files remain outstanding project-wide (unchanged from before this plan for three of them; two new ones added by this plan):

| # | Filename | Status | Type / Livery |
|---|---|---|---|
| 1 | `km-malta-airlines.png` | outstanding since `260827-jz6` | Airbus A320neo, post-2023 KM Malta livery |
| 2 | `tuifly-belgium.png` | outstanding since `260827-jz6` | Boeing 737 MAX 8, current TUI "Dynamic Wave" livery |
| 3 | `royal-air-maroc-embraer.png` | outstanding since Phase 3.1 | Embraer E190, Royal Air Maroc livery |
| 4 | `amelia.png` (new, this plan) | outstanding | Airbus A320, white fuselage/blue tail/lowercase "amelia" wordmark — **livery detail is moderate confidence**, verify against a real photo before generating |
| 5 | `amelia-embraer.png` (new, this plan) | outstanding | Embraer E145, same livery as above — **also moderate confidence** |

The two new files' generation prompts are `HANDOFF.md` sections **#25** (`amelia.png`) and **#30** (`amelia-embraer.png`), each carrying an explicit livery-confidence note in the prompt block's surrounding prose.

**Post-generation commands, in order, once new files are dropped into `server/assets/icons/illustrations/`:**

```
server/.venv/bin/python3 server/plane/illustrations.py --outstanding   # confirm what's left
server/.venv/bin/python3 server/plane/illustrations.py --validate      # must exit 0
scripts/check-attribution.sh                                          # must exit 0
```

Additionally, confirm **by eye** for every newly delivered file: the nose points left, and the depicted aircraft type matches the filename (A320 for `amelia.png`, Embraer E145 for `amelia-embraer.png`).

**`_unresolved/amelia-international.png`** (a leftover from Phase 3.1, generated under the old incorrect "Amelia International" name) may be promoted to a real target by `git mv`-ing it to `amelia.png` or `amelia-embraer.png` *after* the developer confirms by eye which type it actually depicts and that the nose points left — or the developer may simply regenerate fresh art from the two prompts above instead. It is not moved or renamed by this plan.

## Self-Check: PASSED

- FOUND: server/plane/enrich.py
- FOUND: server/plane/illustrations.py
- FOUND: server/plane/render.py
- FOUND: server/fixtures/adsbdb_hit_AIA6412.json
- FOUND: server/assets/icons/illustrations/air-corsica.png
- FOUND: server/assets/icons/illustrations/air-corsica-atr72.png
- FOUND: server/assets/icons/illustrations/asl-airlines-france.png
- FOUND: server/assets/icons/illustrations/corsair.png
- FOUND commit c3ba883
- FOUND commit 1e0b111
- FOUND commit b6bd327
