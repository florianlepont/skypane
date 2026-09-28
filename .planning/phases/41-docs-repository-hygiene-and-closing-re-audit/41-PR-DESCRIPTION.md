## Summary

Phase 41 closes the 2026-09-23 whole-repository code audit's remediation
arc (Phases 32-41, milestone v1.0, 82 findings). This PR itself: aligns
every doc claim named by the audit's DOC-01 finding against the code as it
stands after Phases 32-40 (98 claims checked, corrected in place where
stale); gzips an oversized hardware log in the tree (no history rewrite)
and removes one confirmed-unused illustration draft (DOC-02); and runs a
full closing re-audit of all 82 findings plus the REQUIREMENTS.md
bookkeeping for CFG-72/CFG-73 (DOC-03).

## The remediation arc, phase by phase

- **Phase 32** (#105) — Test foundation: pytest+xdist+cov, hash-locked
  deps, CI on production Python 3.14. Verified: 5/5 roadmap criteria, 9/9
  requirements. Re-audit: TST-01, TST-03..TST-09 VERIFIED-CLOSED; TST-02
  FLAGGED-DIFFERENT (stale standalone ledger-check tool, no lost coverage).
- **Phase 33** (#127) — Companion tests on pytest, behaviour over source
  text. Verified: 9/9 must-haves. Re-audit: TST-10..TST-14
  VERIFIED-CLOSED; TST-15 FLAGGED-DIFFERENT (same stale-tool cause as
  TST-02).
- **Phase 34** (#102, closed #134/#135) — Firmware resilience, power,
  security, cleanup, one hardware session. Verified: 5/5 criteria, 15/15
  requirements. Re-audit: FW-01..FW-15, all 15 VERIFIED-CLOSED (read-only
  against `firmware/`).
- **Phase 35** (#140/#141) — English-only comment purge, dead code, a CI
  guard against plan/ticket IDs reappearing. Verified: 4/4 must-haves.
  Re-audit: HYG-02..HYG-05 VERIFIED-CLOSED; **HYG-01 and HYG-06
  ACCEPTED-OPEN**: the shipped guard's regex misses some ID shapes, so
  history references survive in comments. Accepted as-is by the developer,
  fix deferred to a todo.
- **Phase 36** (#142) — State integrity and device protocol. Verified:
  14/14 must-haves. Re-audit: INT-01..INT-14, all 14 VERIFIED-CLOSED.
- **Phase 37** (#114-118, #143/#144) — Security and operations hardening.
  Verified: 13/13 must-haves. Re-audit: SEC-01..SEC-08, all 8
  VERIFIED-CLOSED.
- **Phase 38** (#145-153) — Efficiency: compression/caching, one SQLite
  connection per cycle, lazy context, write-once state, parallel provider
  queries. Verified: 10/10 must-haves. Re-audit: EFF-01..EFF-06, all 6
  VERIFIED-CLOSED.
- **Phase 39** (#154) — Server architecture: `run_once` split into named
  steps, `state_store`/`device_policy` shared modules, package splits,
  mypy in CI. Verified: 10/10 must-haves. Re-audit: ARC-01, ARC-02,
  ARC-04..ARC-06 VERIFIED-CLOSED; **ARC-03 FLAGGED-DIFFERENT** (naming
  only — the ledger's shorthand says `calendar/`, the shipped package is
  `server/plane/calendar_rules/`; intent fully met, no open risk).
- **Phase 40** (#155) — Companion architecture: route table, typed page
  context, named templates, CSS tokens, stable i18n IDs. Verified: 12/12
  must-haves. Re-audit: CMP-01..CMP-09, all 9 VERIFIED-CLOSED.
- **Phase 41** (this PR) — Docs, repository hygiene, closing re-audit.
  DOC-01, DOC-02 and DOC-03 VERIFIED-CLOSED (DOC-03 on the developer's
  acceptance of HYG-01/HYG-06).

## Closing re-audit

**Totals across all 82 ledger IDs (`41-CLOSING-AUDIT.md`):**
77 VERIFIED-CLOSED, 3 FLAGGED-DIFFERENT, 2 ACCEPTED-OPEN, 0 FLAGGED-OPEN.

**ACCEPTED-OPEN (2), developer decision 2026-09-28:**
- **HYG-01** — 21 residual plan/decision-history references (`D-14c`-style
  IDs, dotted UI-SPEC section numbers, two bare Phase-Plan numerics) across
  12 companion/server test files and `pyproject.toml`, in shapes the
  shipped comment-history guard's regex does not catch.
- **HYG-06** — the CI guard step and its own mutation-tested test suite
  are correctly wired; the gap is in the guard's own regex (three targeted
  edits proposed in `41-CLOSING-AUDIT.md`), which is what HYG-01 exploits.

Neither involves runtime behaviour. A gap-closure pass prototyped the
tightened guard and found the residue is bigger than first measured (about
85 real hits in 34 files, including one JS and one shell file). Rather than
run six more plans before Phase 42, the developer accepted both as-is and
deferred the fix to `.planning/todos/pending/comment-history-guard-residue.md`. The drafted plans are
recoverable from commit `3e45e90a`. `41-VERIFICATION.md` records this as
a developer override, and DOC-03 is ticked on that basis.

**FLAGGED-DIFFERENT (3), all naming/tooling-only, no open risk:**
- **TST-02** — Phase 32's own migration ledger closed correctly; a
  standalone helper script (`32-ledger-check.py`) now reports 6 node ids
  Phase 39 legitimately renamed, not a coverage loss.
- **TST-15** — same root cause as TST-02, in `33-ledger-check.py` (4
  fragments); coverage and count parity both still exceed the
  pre-migration baseline.
- **ARC-03** — the calendar package's shipped name is
  `server/plane/calendar_rules/`, not the ledger's own shorthand
  `calendar/`; the `ics`/`match`/`registry` submodule structure the
  finding asked for is fully present.

See `41-CLOSING-AUDIT.md` for the full 82-row table, evidence, and the
`## Evidence limited to recorded artefacts` section (CI-only, VPS-only and
hardware-capture-only sub-facts this report cites rather than re-derives).

## Bookkeeping

- **CFG-72** and **CFG-73** ticked in `REQUIREMENTS.md`: their three named
  tests (`test_a_settings_card_title_renders_identically_on_both_settings_pages`,
  `test_the_dial_caption_keeps_its_form_after_every_interaction_kind`,
  `test_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press`)
  pass on this tree, and the `button:active` exclusion for
  `.value-control__handle` is present in `companion/static/style.css`.
- **CFG-74** deliberately left exactly as recorded — SUPERSEDED before
  implementation, never built, checkbox unticked, no text change, per the
  developer's own explicit 2026-09-28 decision (not this phase's call to
  make).
- **CFG-34, CFG-37, CFG-39, CFG-42, CFG-50, CFG-52, CFG-65** and every OTA
  requirement: untouched, pending separate product/Phase 42 decisions.

## Not in this PR

- No `firmware/` behaviour change — only `firmware/VENDOR.md` prose was
  edited (doc-drift correction), confirmed by
  `git diff --name-only <base> -- firmware/`.
- No OTA-01..12 work — that is Phase 42, whose gate **G-41** requires this
  PR merged to `main` first.
- No git-history rewrite — the oversized hardware log was gzipped in the
  working tree only (decision D-A6); the uncompressed blob remains
  reachable in every prior commit.
- `/gsd-cleanup` phase-directory archival is deferred to the real v1.0
  close, after Phase 42 finishes (Phase 42 is already scoped into this
  same v1.0 milestone, immediately after this phase).

## Test plan

From `41-CLOSING-AUDIT.md`'s `## Final gate runs`:

- [x] `ruff check .` — 0, all checks passed
- [x] `mypy` — 0, no issues in 12 source files
- [x] `check_comment_history.py check` — 0, zero hits
- [x] `check_function_size.py check --max 80` — 0, 401 functions scanned
- [x] `check-attribution.sh` — 0, PASS
- [x] `firmware/tests/run_host_tests.sh` — 0, 10/10 suites
- [x] `deploy/tests` (targeted, native + a Linux container for the two
      BSD-`mv`-incompatible files) — 174/174 passed (100 native + 70 in
      container overlapping test_units/test_provision), 4 skipped
      (`systemd-analyze` absent on this sandbox)
- [x] `check_comment_history.py same-code --base <phase base>` — 0
- [ ] **Full suite, `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`,
      on this PR's own CI run** — the local sandbox run for this plan saw
      40-48 failures that are sandbox-only (resource contention under the
      full ~3200-test parallel run, this macOS host's missing `/proc`,
      BSD `mv`, and one Pillow/FreeType anomaly that a live GitHub Actions
      log for an equivalent tree already shows passing at 3218/3218).
      None touch any of the 82 ledger IDs or any file this phase modified.
      **This PR's own CI run is the pending, authoritative proof.**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
