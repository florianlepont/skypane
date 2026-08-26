---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
plan: 03
subsystem: legal-compliance
tags: [mit-license, ofl-1.1, attribution, compliance, adsb, licensing]

requires:
  - phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
    provides: "04-01's clean, history-scrubbed repo and repo-root .gitignore; 04-02's dev-tooling pins and scripts/run-all-tests.sh as the canonical test entry point"
provides:
  - "Repo-root MIT LICENSE with an accurate scope note excluding server/assets/"
  - "COMPLIANCE.md documenting all five real third-party data sources this project touches"
  - "server/assets/fonts/Inter-OFL.txt closing a real, previously-undetected OFL notice gap"
  - "scripts/check-attribution.sh — machine-checked, CI-ready attribution completeness gate"
  - "Real adsb.fi attribution citation text, satisfying their published terms"
affects: ["04-04 (CI wires check-attribution.sh in)", "04-05 (README mirrors the adsb.fi citation)", "04-06 (publish gate — legal coherence prerequisite)"]

tech-stack:
  added: []
  patterns:
    - "Per-source compliance documentation shape mirrored from VENDOR.md: source, upstream link, terms-checked date, requirement, verdict"
    - "Attribution completeness as a machine-checked shell script (scripts/check-attribution.sh), not a one-time manual review"

key-files:
  created:
    - LICENSE
    - COMPLIANCE.md
    - server/assets/fonts/Inter-OFL.txt
    - scripts/check-attribution.sh
  modified:
    - server/assets/fonts/VENDOR.md

key-decisions:
  - "Vendored Inter's real OFL 1.1 text from the same pinned v4.1 release tag VENDOR.md already cites for the TTFs, rather than copying a sibling font's licence text"
  - "adsb.fi citation placed as real citation-sentence text in both COMPLIANCE.md and (per plan 04-05) README.md, not merely described"
  - "airplanes.live terms recorded as an open, unresolved item (confirmed 403 on three separate automated fetch attempts across two sessions) with a named route to closure, rather than fabricated or silently dropped"
  - "In the interim, airplanes.live receives the same courtesy attribution as adsb.fi, explicitly labeled as good-faith pending confirmation — not a claim of a confirmed requirement"

patterns-established:
  - "scripts/check-attribution.sh: enumerate non-markdown files under server/assets/, fail naming any file absent from a VENDOR.md, fail if any font family lacks a *-OFL.txt licence text — bash 3.2 compatible (no associative arrays, since macOS ships bash 3.2 as /bin/bash)"

requirements-completed: [D-13, D-14]

coverage:
  - id: D1
    description: "Repo-root MIT LICENSE with grant/conditions/disclaimer intact and a scope note excluding server/assets/"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "grep -q 'MIT License' LICENSE && grep -q 'Permission is hereby granted, free of charge' LICENSE && grep -q 'THE SOFTWARE IS PROVIDED \"AS IS\"' LICENSE && grep -qi 'server/assets' LICENSE"
        status: pass
    human_judgment: false
  - id: D2
    description: "Inter OFL 1.1 licence text vendored, closing the real gap VENDOR.md previously claimed was already closed"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "test -f server/assets/fonts/Inter-OFL.txt && grep -qi 'SIL OPEN FONT LICENSE' server/assets/fonts/Inter-OFL.txt && grep -qi 'inter' server/assets/fonts/Inter-OFL.txt"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/check-attribution.sh enumerates all vendored assets, fails naming any unattributed file or font family missing its licence text, passes when complete"
    requirement: "D-14"
    verification:
      - kind: manual_procedural
        ref: "Deliberate rename of server/assets/icons/aircraft-silhouette.png -> checker exited 1 naming the exact file; reverted; checker exited 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "COMPLIANCE.md documents all five real third-party data sources (adsb.fi, airplanes.live, adsbdb.com, PRIM/IDFM, AeroDataBox) with terms-checked date and verdict per source"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "for s in adsb.fi airplanes.live adsbdb PRIM AeroDataBox; do grep -qi \"$s\" COMPLIANCE.md; done && grep -qi 'https://adsb.fi' COMPLIANCE.md && grep -qiE 'open item|unconfirmed|403' COMPLIANCE.md && grep -qi 'detect.py' COMPLIANCE.md && grep -qi 'enrich.py' COMPLIANCE.md"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-26
status: complete
---

# Phase 04 Plan 03: LICENSE, COMPLIANCE.md, and Machine-Checked Attribution Summary

**MIT LICENSE with an asset-scope note, a real Inter OFL 1.1 gap closed, a bash-3.2-compatible attribution checker, and COMPLIANCE.md covering all five actual third-party data sources — including the one nobody had named yet (adsbdb.com) — with the confirmed adsb.fi attribution requirement met by real citation text.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-26
- **Tasks:** 3/3
- **Files modified:** 5 (LICENSE, COMPLIANCE.md, server/assets/fonts/Inter-OFL.txt, server/assets/fonts/VENDOR.md, scripts/check-attribution.sh)

## Accomplishments

- Repo-root `LICENSE` (MIT, verbatim grant/conditions/disclaimer, 2026 / Florian Lepont) with a scope note that explicitly excludes `server/assets/` and points readers at the per-directory `VENDOR.md` files rather than restating detail.
- Closed a real, previously-undetected compliance gap: `server/assets/fonts/VENDOR.md` claimed the full OFL 1.1 text was vendored for Inter; it was not. Fetched the real text directly from the same pinned `v4.1` release tag already cited for the TTFs (`https://raw.githubusercontent.com/rsms/inter/v4.1/LICENSE.txt`, sha256 `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`), vendored it as `server/assets/fonts/Inter-OFL.txt`, and corrected VENDOR.md's Inter entry with an explicit dated correction note plus a sentence tying retention (not deletion, post-Phase-3 supersession) to why the OFL obligation still applies.
- Full asset attribution audit performed for real (not just asserted): enumerated all 23 non-markdown files under `server/assets/` — every one is named in a `VENDOR.md`. Verified `server/assets/icons/illustrations/VENDOR.md` **already exists and is complete** (per-file sha256 digests, generation provenance, coverage note) — this corrects a stale claim in both `04-CONTEXT.md` ("still doesn't exist") and `04-PATTERNS.md` (listed as a gap to fill). `server/assets/icons/VENDOR.md` needed no changes; the audit found nothing wrong there and this is recorded explicitly rather than silently.
- Built `scripts/check-attribution.sh`, a bash-3.2-compatible (macOS's `/bin/bash` is 3.2.57, no associative arrays — used a plain-array de-dup loop instead of `declare -A`) checker that enumerates every non-markdown file under `server/assets/`, fails naming any file absent from a `VENDOR.md`, and fails if any font family present in `server/assets/fonts/` lacks its own `*-OFL.txt` licence text — the exact check that would have caught the Inter gap the day it happened.
- Created `COMPLIANCE.md` documenting **five** real third-party data sources, not the three D-14 originally named — `server/plane/enrich.py`'s `adsbdb.com` callsign/route lookup is a fourth source reached in production that no phase document had named until this session. Every behavioural claim (poll cadence, caching, non-republication) cites `server/plane/detect.py` and `server/plane/enrich.py` by name.
- The adsb.fi attribution requirement (confirmed unmet at planning time) is now met with real citation text, present in two places (see below).
- The airplanes.live terms remain genuinely unresolved (403 confirmed on three separate automated fetch attempts across two sessions — 04-RESEARCH.md's two, plus one more made live during this plan's execution) and are recorded as the single OPEN row in COMPLIANCE.md's status table, with a named, actionable route to closure rather than fabricated or dropped.

## Task Commits

1. **Task 1: MIT LICENSE with an accurate asset-scope note** - `23fcd6a` (feat)
2. **Task 2: Audit asset attribution completeness and close the OFL gap** - `c7343c7` (feat)
3. **Task 3: COMPLIANCE.md — per-source terms, status, and the honest open item** - `89bd184` (docs)

_No plan-level metadata commit is created by the executor per the sequential-execution instructions for this wave — orchestrator handles final phase-level bookkeeping._

## Files Created/Modified

- `LICENSE` — MIT licence, verbatim, plus a scope note naming `server/assets/fonts/`, `server/assets/icons/plane-takeoff.*`/`plane-landing.*`, and `server/assets/icons/illustrations/` as separately-licensed, pointing to their `VENDOR.md` files.
- `server/assets/fonts/Inter-OFL.txt` — real SIL OFL 1.1 text for Inter, fetched from the pinned `v4.1` release tag, sha256 `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`.
- `server/assets/fonts/VENDOR.md` — Inter entry corrected: names the now-present licence text and its retrieval provenance, adds a dated correction note explaining the prior false claim, and ties the still-committed TTFs' retention to why the OFL obligation remains live.
- `scripts/check-attribution.sh` — new, executable, machine-checked attribution completeness gate; wired into CI by plan 04-04.
- `COMPLIANCE.md` — new, repo root; five per-source subsections (adsb.fi, airplanes.live, adsbdb.com, PRIM/IDFM, AeroDataBox), a runtime-behaviour section citing `detect.py`/`enrich.py`, and a closing status table with exactly one open row.

## Attribution Audit Result (full account, per plan's output instructions)

**Full asset inventory walked:** 23 non-markdown files under `server/assets/` (8 in `fonts/` including the newly-added `Inter-OFL.txt`, 2 root-level icon SVG/PNG pairs = 4 files, 8 illustration PNGs, `plane-takeoff.svg`/`.png` and `plane-landing.svg`/`.png` = 4 files). All 23 are named in one of the three `VENDOR.md` files (`server/assets/fonts/VENDOR.md`, `server/assets/icons/VENDOR.md`, `server/assets/icons/illustrations/VENDOR.md`) — confirmed both by manual read during this plan's `read_first` steps and by `scripts/check-attribution.sh`'s own automated enumeration (`PASS: 23 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text.`).

**Items already correct (explicitly reported, not silently passed over):**
- `server/assets/icons/VENDOR.md` — complete as-is for the Lucide-derived icons and the CC0 aircraft silhouette; no changes made.
- `server/assets/icons/illustrations/VENDOR.md` — **already exists and is complete** (per-file sha256 digests, dimensions, per-airline mapping, licensing rationale, nose-orientation convention, coverage note for uncovered carriers). This directly contradicts `04-CONTEXT.md` ("`server/assets/icons/illustrations/VENDOR.md` was flagged as a real gap... still doesn't exist") and `04-PATTERNS.md` (which lists it as a gap to fill via a "split/promotion" of the parent VENDOR.md's content). Both documents are stale as of this session; this SUMMARY is the correction record.
- `ZillaSlab-*` and `PTSerif-*` entries in `server/assets/fonts/VENDOR.md` — already complete with pinned-commit provenance, sha256 digests, and vendored `*-OFL.txt` files; no changes made.

**The one real gap found and closed:** the Inter entry in `server/assets/fonts/VENDOR.md` asserted "the full OFL 1.1 text is vendored alongside the upstream release archive's own `LICENSE.txt`" — no such file existed anywhere in the repository, while `Inter-Regular.ttf`/`Inter-Bold.ttf` remained committed and shipped (retained for provenance post-Phase-3 supersession by Zilla Slab, later PT Serif — never deleted). Closed by fetching the real text from `https://raw.githubusercontent.com/rsms/inter/v4.1/LICENSE.txt` (same pinned tag already cited for the TTFs), vendoring it as `Inter-OFL.txt`, and correcting the VENDOR.md claim with a dated, explicit correction note.

## Checker Evidence: Fail Then Pass

Ran `scripts/check-attribution.sh` against a deliberate rename to prove it actually catches a gap, then reverted:

```
$ mv server/assets/icons/aircraft-silhouette.png server/assets/icons/aircraft-silhouette-RENAMED.png
$ ./scripts/check-attribution.sh
...
FAIL: the following asset file(s) are not named in any VENDOR.md:
    - server/assets/icons/aircraft-silhouette-RENAMED.png
...
FAIL: attribution check found gap(s) above.
exit=1

$ mv server/assets/icons/aircraft-silhouette-RENAMED.png server/assets/icons/aircraft-silhouette.png
$ ./scripts/check-attribution.sh
...
PASS: 23 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text.
exit=0
```

The rename was reverted before continuing; `git status --short server/assets/` showed no residual change from this test.

## adsb.fi Citation: Exact Wording and Location

Real citation-sentence text (not a description of the requirement), present in **two** places per the plan's `key_links`:

1. **`COMPLIANCE.md`**, adsb.fi subsection, "Verdict" block:
   > This project uses real-time ADS-B aircraft position data from [adsb.fi](https://adsb.fi) as a secondary aggregator source.

2. **`README.md`**, Data Sources section — to be added by plan **04-05** per the plan's own key_links note ("the citation is deliberately present in both, because the term requires it be visible and the README is what a visitor actually reads"). `README.md` does not yet exist as of this plan's completion; 04-03's own scope covers only `LICENSE`/`COMPLIANCE.md`/asset attribution, so the README half of this citation is 04-05's responsibility, explicitly cross-referenced here so it isn't dropped.

## Decisions Made

- Fetched Inter's real OFL 1.1 text live from GitHub's raw content endpoint at the pinned `v4.1` tag rather than copying a sibling font's licence text and hand-editing it — matches this project's existing pinned-commit-and-verify discipline (sha256 recorded in VENDOR.md).
- `scripts/check-attribution.sh` written for bash 3.2 compatibility (no `declare -A`) after the first draft failed on this machine's `/bin/bash` — macOS ships 3.2.57 by default, and CI (plan 04-04) may run on a similarly old shell unless explicitly overridden; writing portably up front avoids a second, silent compatibility bug.
- adsb.fi's home page link recorded as `https://adsb.fi` (matches 04-RESEARCH.md's own citation of the source); the live automated fetch of that URL returned HTTP 403 during this session too (bot-detection, consistent with the airplanes.live pattern), but the citation itself does not depend on the page being fetchable — it only needs to link to the home page, which it does.
- airplanes.live's interim courtesy attribution is explicitly labeled in COMPLIANCE.md as "good-faith... pending confirmation," never presented as satisfying a confirmed requirement — avoids fabricating compliance with unread terms.

## Deviations from Plan

None — plan executed exactly as written. The `server/assets/icons/VENDOR.md` "modified if the audit finds anything; otherwise unchanged" artifact note resolved to "unchanged," as anticipated by the plan itself.

## Issues Encountered

- First draft of `scripts/check-attribution.sh` used `declare -A` for family de-duplication and failed immediately on this machine's `/bin/bash` (3.2.57, no associative arrays). Rewrote the de-dup logic with a plain array + linear-scan check before the checker's first successful run — no functional behaviour change, same pass/fail semantics.

## Next Phase Readiness

- `scripts/check-attribution.sh` is ready for plan 04-04 to wire into CI as a blocking step.
- The adsb.fi citation text above is ready for plan 04-05 to mirror into `README.md`'s Data Sources section verbatim.
- `COMPLIANCE.md`'s one OPEN item (airplanes.live terms) is a real, unresolved external dependency (manual browser read or pending email reply) — not a blocker for 04-04/04-05/04-06, but should be revisited before any future terms-sensitive change to how airplanes.live is used.
- All 9 test harnesses (117 checks) and `ruff check .` pass unchanged after this plan — the asset audit did not move, rename, or otherwise disturb any file the render path loads.

## Self-Check: PASSED

All claimed files exist (`LICENSE`, `COMPLIANCE.md`, `server/assets/fonts/Inter-OFL.txt`, `scripts/check-attribution.sh`, this SUMMARY) and all three task commit hashes (`23fcd6a`, `c7343c7`, `89bd184`) are present in `git log --oneline --all`.

---
*Phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Completed: 2026-08-26*
