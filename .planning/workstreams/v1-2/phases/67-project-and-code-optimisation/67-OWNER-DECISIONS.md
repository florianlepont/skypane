# Phase 67: Owner decisions

One list of every decision left to the owner, with the provisional default
for each. Nothing in this plan deletes anything. Generated on 2026-11-27
against `main` at the time of the plan.

Every "Owner answer" cell is empty on purpose: rows marked "provisional
default, owner may override" stay at their default until the owner fills the
cell.

## 0. Decisions already answered (D-12, D-13)

These were open in earlier drafts. The owner answered them on 2026-11-27;
they are recorded here, not re-asked.

| Decision | Owner answer | Remaining gate |
|---|---|---|
| Two SQLite migration mechanisms (history.db, fleet.db) | UNIFY into one shared mechanism, keeping the concurrent-open safety of history.db and the refusal of a newer fleet.db | none beyond the plan's own tests |
| Rollback-era duplicates (enrolment secret and token mirrors, per-device copies of the three airline registries and of the artwork) | RETIRE | owner-run read-only check G1 (pasted result) before the fallback is retired; quarantine by the owner-run tool, never deleted |
| `legacy-admin` session principal | RETIRE (schema 5; the previous release then refuses fleet.db, recovery is the nightly backup) | owner's pasted G3 count and written G6 confirmation that the rollback period is over |
| Leftovers without a writer (`META_LAST_POLL_TRIGGER`, three unused `fleet_db` location helpers) | REMOVE | none |
| `wake_epochs` table | KEEP (G4 = KEEP); the table drop does not run. Revisit only if the link between battery life and wake interval is abandoned | none |
| fleet.db fallback | RETIRED in principle (G1 approved): the device server reads identity from fleet.db only and refuses to answer if it is unreadable | owner's G1 check result |
| Module regrouping, function-size gate extension, other defaults, 30-run CI repeat of the flaky test, branch deletion | Accepted as in the plans; branch deletion only per name in plan 12 | per-name approval for each branch |

Order is unify, then retire, then remove. Deploy stays manual for the owner.

## 1. Remote branches

Source: GitHub REST API only (`branches`, `compare`, `pulls`). Count:
**40 non-main branches** (the plan expected 39; one more appeared since).
There are 0 open pull requests, so the Open PR column is "no" for every row.
Ahead and behind are commit counts relative to `main`. The "Note" column
marks exploratory-looking prefixes (`explore/`, `sketch/`, `codex/`) as
likely live work. Recommendation: **nothing is deleted without written,
per-name approval from the owner**.

<!-- branch-count: 40 -->

| Branch | Ahead of main | Behind main | Last commit | Open PR | Note |
|---|---|---|---|---|---|
| `ci/runner-vm-cleanup` | 1 | 27 | 2026-11-26 | no |  |
| `claude/finalisation-phase-5-2bff7e` | 3 | 659 | 2026-09-14 | no |  |
| `claude/flights-boarding-cards` | 10 | 456 | 2026-10-04 | no |  |
| `claude/flights-filter-chips` | 3 | 453 | 2026-10-04 | no |  |
| `claude/home-status-bar` | 6 | 462 | 2026-10-03 | no |  |
| `claude/home-status-hero` | 9 | 461 | 2026-10-03 | no |  |
| `claude/nifty-maxwell-sg7rga` | 1 | 464 | 2026-10-12 | no |  |
| `claude/optimize-tests-ci-278bc4` | 36 | 552 | 2026-09-22 | no |  |
| `claude/plan-phase-36` | 55 | 487 | 2026-09-26 | no |  |
| `claude/public-repo-prep-0ad81d` | 10 | 549 | 2026-09-23 | no |  |
| `claude/web-companion-audit-ux-refactor-bqx7si` | 60 | 566 | 2026-09-12 | no |  |
| `codex/v1.1-battery-and-companion` | 32 | 465 | 2026-10-01 | no | likely live (exploratory prefix) |
| `codex/v1.1-companion-ui-seed` | 1 | 465 | 2026-09-30 | no | likely live (exploratory prefix) |
| `docs/69-08-companion-follow-up` | 1 | 24 | 2026-11-27 | no |  |
| `docs/69-08-companion-validated` | 1 | 22 | 2026-11-27 | no |  |
| `docs/69-adopt-one-part` | 2 | 93 | 2026-11-24 | no |  |
| `docs/69-alt-print-result` | 3 | 97 | 2026-11-24 | no |  |
| `docs/69-close-phase` | 19 | 33 | 2026-11-26 | no |  |
| `docs/69-merged-variant` | 2 | 109 | 2026-11-24 | no |  |
| `docs/69-one-part-is-main` | 2 | 93 | 2026-11-24 | no |  |
| `explore/photo-mode-v1-3` | 6 | 305 | 2026-11-13 | no | likely live (exploratory prefix) |
| `feat/69-stand-hinged` | 19 | 89 | 2026-11-24 | no |  |
| `firmware/phase-57-result` | 3 | 226 | 2026-11-15 | no |  |
| `fix/companion-mat-strips-everywhere` | 1 | 24 | 2026-11-27 | no |  |
| `fix/companion-preview-no-mat-strips` | 1 | 28 | 2026-11-26 | no |  |
| `gsd/phase-64-walkthrough-marks` | 1 | 204 | 2026-11-15 | no |  |
| `gsd/phase-65-findings` | 3 | 206 | 2026-11-15 | no |  |
| `hardware/cad-files` | 1 | 216 | 2026-11-17 | no |  |
| `hardware/phase34-session` | 1 | 497 | 2026-09-25 | no |  |
| `phase-66-closeout` | 1 | 13 | 2026-11-27 | no |  |
| `phase-68-1-build-plans` | 4 | 60 | 2026-11-25 | no |  |
| `phase-68-1-build-plans-rev` | 3 | 60 | 2026-11-25 | no |  |
| `phase-68-1-design-system-consistency` | 15 | 78 | 2026-11-25 | no |  |
| `phase-70-close` | 1 | 20 | 2026-11-27 | no |  |
| `phase-70-closeout` | 1 | 19 | 2026-11-27 | no |  |
| `phase-70-dossier` | 2 | 22 | 2026-11-27 | no |  |
| `phase-70-even-shards` | 1 | 28 | 2026-11-26 | no |  |
| `phase-70-flip-v14` | 1 | 19 | 2026-11-27 | no |  |
| `sketch/photo-companion` | 12 | 305 | 2026-11-11 | no | likely live (exploratory prefix) |
| `tmp-repeat-lightbox-67` | 3 | 9 | 2026-11-27 | no |  |

A branch with commits ahead of `main` and no pull request can hold work that
exists nowhere else; "ahead" above is the number of such commits. Branches
whose name matches a closed phase (`phase-70-*`, `docs/69-*`) are the most
likely to be already merged or superseded, but that is a guess: the owner
decides per name.

## 2. Planning-note cleanup candidates

List only. Nothing is deleted. The count is the number of other tracked
files that contain the candidate's base file name (`git grep -F`); a
generic base name such as `ARCHITECTURE.md` or `STATE.md` over-counts
because other files share the name. Any file with a count above 0 is
**must keep** (owner decisions and history that other documents reference).

| Candidate | References | Status | Comment |
|---|---|---|---|
| `.planning/research/STACK.md` | 9 | must keep | Kept as history per `.claude/CLAUDE.md` |
| `.planning/research/PITFALLS.md` | 12 | must keep | Referenced |
| `.planning/research/FEATURES.md` | 2 | must keep | Referenced |
| `.planning/research/ARCHITECTURE.md` | 63 (generic name) | must keep | Pre-build research, history |
| `.planning/research/SUMMARY.md` | 518 (generic name) | must keep | Pre-build research, history |
| `.planning/research/questions.md` | 0 | candidate | No other file names it; superseded by phase research |
| `.planning/MILESTONES.md` | 0 | candidate | Not named elsewhere; used by the workflow tooling, check before any change |
| `.planning/debug/overhead-style-state.md` | 0 | candidate | Debug session left outside `resolved/` |
| `.planning/sketches/WRAP-UP-SUMMARY.md` | 0 | candidate | Sketch wrap-up, history |
| `.planning/sketches/phase-44-companion/general-directions.html` | 0 | candidate | Sketch artefact |
| `.planning/seeds/SEED-011` (unverified e-mail sign-in message) | 0 | candidate | Seed with no references |
| `.planning/seeds/SEED-016` (user-selectable power saving) | 0 | candidate | Seed with no references |
| `.planning/seeds/SEED-018` (firmware update policy) | 0 | candidate | Seed with no references |
| `.planning/seeds/SEED-019` (battery discharge curve validation) | 0 | candidate | Seed with no references |
| `.planning/seeds/SEED-021` (shim and tray in one part) | 0 | candidate | Seed with no references |
| `.planning/seeds/SEED-022` (enclosure for the 13.3 inch frame) | 0 | candidate | Seed with no references |
| `.planning/todos/pending/comment-history-guard-residue.md` | 1 | must keep | Pending todo, referenced |
| `.planning/notes/*` (7 notes, `skypane-ops-board.html`) | 2 to 8 each | must keep | All referenced |
| `.planning/audits/2026-09-23-code-audit.md` | 5 | must keep | Referenced |
| `.planning/quick/*` (about 390 files) | mostly 0 | history | One-off task records, each its own history; zero references is normal for them, deletion not recommended |
| `.planning/spikes/*`, `.planning/ui-reviews/*` | 1 to 22 | must keep | Referenced via manifests |

Candidates with 0 references are the only ones that could be removed
without breaking a link; seeds and sketches are still owner ideas, so the
recommendation is to keep all of them unless the owner says otherwise.

### 2b. Outcome of the planning-note review (owner, 2026-11-27)

Deleted: `.planning/research/questions.md`, `.planning/debug/overhead-style-state.md`,
`.planning/sketches/WRAP-UP-SUMMARY.md`,
`.planning/sketches/phase-44-companion/general-directions.html`, SEED-021.
Kept: `.planning/MILESTONES.md` (read by the workflow tooling), SEED-016, SEED-018,
SEED-011, SEED-019, SEED-022. SEED-011 was first chosen for deletion, then kept by the
owner after seeing that ten other documents cite it by identifier (the reference
count above was by file name and missed this).

## 3. Open decisions

Each row is a provisional default, owner may override. The owner-answer
column is empty until filled.

| # | Decision | Provisional default | Owner answer |
|---|---|---|---|
| 1 | Hide or drop the tested-but-unused API (about 30 functions that only tests call) | provisional default, owner may override: keep as test seams, list the names in the plan that owns the list | Delete the test-only functions together with their tests (owner, 2026-11-27); needs a new plan and one lowering of `MIN_EXECUTED` to the measured count |
| 2 | SPDX headers on the 879 Python files | provisional default, owner may override: decision or CI gate only, no mass edit | Add `SPDX-License-Identifier: AGPL-3.0-only` to all Python files without a header (owner, 2026-11-27); files that already carry Apache-2.0, MIT or 0BSD keep theirs; plus a CI rule for new files |
| 3 | How far server modules are regrouped | provisional default, owner may override (accepted as in the plans per D-13): three groups, `firmware_*`, polling-support, pairing; one group per PR with `sys.modules` alias shims; `fleet_db`, `history_db`, `device_config`, `poll_loop` stay where they are | |
| 4 | Ruff `B` rules | provisional default, owner may override: not adopted; the B023 findings are listed for a later review | Not adopted in this phase (owner, 2026-11-27) |
| 5 | Function-size gate extension to companion, deploy and scripts | provisional default, owner may override (accepted per D-13): yes; plan 10 only tightens CI and edits one `ci.yml` step | |
| 6 | Remote branch deletion | provisional default, owner may override: nothing deleted; only per-name approval in plan 12 | All 40 branches deleted by the owner on 2026-11-27 |
| 7 | Planning-note cleanup (section 2) | provisional default, owner may override: nothing deleted; zero-reference candidates reviewed by the owner one by one | Decided one by one (owner, 2026-11-27); see section 2b |
| 8 | README "Licence" and "Contributing" sections say the repository is private | provisional default, owner may override: left as written until the visibility change closes in Phase 70.1, then reworded in one change | Fixed now (owner, 2026-11-27): the README and CONTRIBUTING sections say the repository is currently public; to be reworded again when the visibility changes |
| 9 | `pyproject.toml` comment still says the local venv is 3.11 (it is 3.13 here, 3.14 in CI and production) | provisional default, owner may override: fix the comment in the next code-touching change, not in this docs-only plan | Fixed now in a small comment-only change (owner, 2026-11-27) |
| 10 | Dependency upgrades (section 4) | provisional default, owner may override: none needed now; re-run the advisory lookup before each release | No upgrades now; re-run the advisory lookup before each release (owner, 2026-11-27) |

Rows already answered are in section 0 and are not repeated here
(migration mechanism, rollback-era duplicates, leftovers, `wake_epochs`,
the legacy-admin principal).

## 4. Dependency review

Read-only: nothing was installed or upgraded and no lock file was edited.

Lock status:

- `server/requirements.txt` (runtime): 6 pinned packages, every one carries
  sha256 hashes (6 of 6). Direct pins in `requirements.in`: Pillow and
  requests.
- `server/requirements-dev.txt` (CI superset): 29 pinned packages, every one
  carries sha256 hashes (29 of 29). Both are generated by
  `scripts/lock-deps.sh` and installed with `--require-hashes`.

Runtime pins: certifi 2026.10.19, charset-normalizer 3.5.1, idna 3.20,
pillow 13.0.0, requests 2.34.2, urllib3 2.8.0. This matches the installed
versions of Pillow and requests in the local virtualenv.

Dev pins: ast-serialize 0.13.1, coverage 7.17.4, execnet 2.1.2, greenlet
3.5.6, iniconfig 2.3.0, librt 0.16.0, mypy 2.4.1, mypy-extensions 1.1.0,
packaging 26.3, pathspec 1.1.1, playwright 1.65.2, pluggy 1.6.0, pygments
2.21.0, pytest 9.2.0, pytest-cov 7.1.0, pytest-playwright 0.10.0,
pytest-socket 0.8.1, pytest-xdist 3.8.0, python-slugify 8.0.4, ruff 0.17.6,
text-unidecode 1.3, types-requests 2.33.0.20261030, typing-extensions
4.16.0 (plus the runtime pins).

Advisories: `pip-audit` is not installed, so the public OSV database
(`api.osv.dev`, read-only POST query per package and exact version) was used
on 2026-11-27. Result: **no known advisory for any of the 29 packages
checked** (all runtime and dev pins above, including coverage 7.17.4). OSV
lists advisories published up to the query time only; a clean result is not
a guarantee.

Recommendation: no upgrade is needed; re-run the lookup before each release
and whenever `scripts/lock-deps.sh` regenerates the locks.
