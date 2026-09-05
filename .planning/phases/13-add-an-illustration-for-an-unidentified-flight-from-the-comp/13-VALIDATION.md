---
phase: 13
slug: add-an-illustration-for-an-unidentified-flight-from-the-comp
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-05
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `13-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom stdlib-only `check()`/`main()` harness per file — not pytest/unittest. Every file defines `EXPECTED_CHECK_COUNT` and exits non-zero when the actual pass count does not match exactly, so a forgotten new check fails loudly instead of silently. |
| **Config file** | none — `scripts/run-all-tests.sh` is the single source of truth for the harness list (16 files today) |
| **Quick run command** | `server/.venv/bin/python3 server/test_enrich.py` (or any single harness directly) |
| **Full suite command** | `scripts/run-all-tests.sh` |
| **Estimated runtime** | ~60 seconds full suite; a single harness is sub-second |

---

## Sampling Rate

- **After every task commit:** the single most relevant harness for the file just touched (`server/test_enrich.py` after an `enrich.py` edit, `companion/test_status_pages.py` after a page edit, and so on)
- **After every plan wave:** `scripts/run-all-tests.sh`
- **Before `/gsd-verify-work`:** full suite green, plus the `pyproject.toml` coverage threshold `run-all-tests.sh` already enforces
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

This phase has no REQUIREMENTS.md ID (unmapped, promoted from a seed — the Phase 10/11/12 precedent). The map is keyed to the phase's own locked decisions from `13-CONTEXT.md` instead. Task IDs fill in once PLAN.md files exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | D-05 | — | Registry load/save never raises; tmp-write-then-`os.replace`; all-or-nothing rejection; bounded entry count | unit | `server/.venv/bin/python3 server/test_manual_resolutions.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | D-08 | — | Deleting a manual entry never removes `illustration_overrides/{key}.png` | unit | `server/.venv/bin/python3 server/test_manual_resolutions.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | D-01 | T-hyy-01 | A manually-registered prefix resolves only after the static table is consulted; the returnable set is now operator-supplied, so path-construction boundaries must hold alone | unit | `server/.venv/bin/python3 server/test_enrich.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | D-02 | — | `resolve_route()` returns `"manual"`, never `"airline_only"`, when the manual registry did the resolving | unit | `server/.venv/bin/python3 server/test_enrich.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | D-06 | — | A hand-resolved prefix later added to the static table reports "superseded"; the static name wins at runtime | unit | `server/.venv/bin/python3 server/test_enrich.py` + `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | D-09 | — | `select_illustration()` / `resolved_illustration_path()` behaviour byte-for-byte unchanged — a must-NOT-change check: the existing `EXPECTED_CHECK_COUNT` holds with zero new checks | regression | `server/.venv/bin/python3 server/test_illustrations.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-11 / D-12 | T-v26-02-01 | `?resolve={prefix}` membership-tested against the live registry; displayed context re-read server-side, never taken from the query string | unit + integration | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | Route/threat parity | T-v26-02-01 | The `_ILLUSTRATION_FILENAMES` widening admits only server-persisted keys, never a request-derived one | integration | `server/.venv/bin/python3 companion/test_companion_app.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-13 | — | The `<datalist>` offers exactly `illustrations.target_airline_names()`, escaped once; a free-typed name slugging to a reserved key (`generic-fallback`, `generic-*`) is rejected | unit | `server/.venv/bin/python3 companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-14 | — | A resolved prefix leaves `unresolved_prefixes` on the next `run_once()` that observes it, independent of `route_source` | unit | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/test_manual_resolutions.py` — new harness, same `check()`/`EXPECTED_CHECK_COUNT`/`main()` shape as `server/test_enrich.py`, covering the new module's load/save/add/delete/cap contract (D-05, D-08)
- [ ] `scripts/run-all-tests.sh` — add the new harness to its canonical file-list array. **Load-bearing:** the script's own header documents it as the single source of truth for CI and the README, so a harness missing from that array silently never runs.
- [ ] No framework install needed — the existing venv and harness style cover this phase entirely

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The resolve form reads and behaves correctly in a real browser — `<datalist>` suggestions appear and are dismissible, the JS-free path degrades cleanly, and the management list is legible on mobile | D-07 / D-13 | `<datalist>` rendering is browser-owned and has no precedent anywhere in this codebase; the harness can assert the emitted markup but not the browser's popup behaviour | Open Airlines on the deployed instance, follow a Health deep link, confirm suggestions appear while typing, submit with and without a suggestion, then check the management list at mobile width |

**No on-glass verification is in scope.** D-09 keeps the render path unchanged; the ROADMAP entry's original "Closes with" was amended accordingly on 2026-09-05.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
