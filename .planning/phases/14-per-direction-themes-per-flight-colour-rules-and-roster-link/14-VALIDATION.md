---
phase: 14
slug: per-direction-themes-per-flight-colour-rules-and-roster-link
status: draft
nyquist_compliant: false
wave_0_complete: false  # Wave 0 item is the new server/test_colour_rules.py harness
created: 2026-09-06
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `14-RESEARCH.md` § Validation Architecture. Written before the
> planner runs, so the Task IDs below are **slots**: the planner assigns real
> `14-NN-MM` ids and must carry every row here into a plan's `<verify>` or
> `must_haves`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom stdlib-only `check(name, fn)` / `main()` harness per file — not pytest, not unittest. Every file defines `EXPECTED_CHECK_COUNT` and exits non-zero when the actual pass count does not match. Do **not** introduce pytest, a `conftest.py`, or any new package. |
| **Config file** | none — `scripts/run-all-tests.sh`'s `HARNESSES` array is the single source of truth for which files run |
| **Quick run command** | `server/.venv/bin/python3 server/test_colour_rules.py` (new) — or whichever single harness the task touched |
| **Full suite command** | `scripts/run-all-tests.sh` (all existing harnesses plus the new one, under `coverage`, enforcing the `pyproject.toml` floor) |
| **Estimated runtime** | ~60 seconds full suite; a single harness is sub-second (figure carried from `13-VALIDATION.md`, same suite) |

---

## Sampling Rate

- **After every task commit:** run the specific new or extended harness for the file just touched (`server/test_colour_rules.py`, `server/test_config_history.py`, `companion/test_config_page.py`, or `server/test_poll_loop.py`). This matches the per-task RED/GREEN discipline recorded throughout STATE.md.
- **After every plan wave:** `scripts/run-all-tests.sh`, coverage floor enforced.
- **Before `/gsd-verify-work`:** full suite green, with one documented exception below.
- **Max feedback latency:** 60 seconds.

**Accepted pre-existing exception.** The macOS-versus-Linux `panel.bin` digest NOTE recorded in STATE.md is an environment-specific non-regression, not a Phase 14 gate failure, **provided it is already present on a clean pre-Phase-14 checkout**. Confirm that baseline before blaming any plan for it.

---

## Per-Task Verification Map

This phase has no REQUIREMENTS.md ID — it is unmapped, promoted from a seed, following the Phase 10, 11, 12 and 13 precedent. The map is keyed to the phase's own locked decisions from `14-CONTEXT.md`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | registry | 0 | D-12 | T-14-01 | Registry load/add/delete never raises; tmp-write-then-`os.replace()`; all-or-nothing rejection; bounded entry count; stray-`.tmp` cleanup | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ❌ W0 | ⬜ pending |
| TBD | registry | 0 | D-08 | T-14-01 | Hostile input rejected for all three kinds: path-separator and parent-directory payloads, oversized strings, wrong-shape hex/callsign/prefix, and a `theme_id` outside `THEME_IDS`. Allowlist re-applied on every read, not only at write | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ❌ W0 | ⬜ pending |
| TBD | registry | 0 | D-09 | — | Adding a key that already exists **replaces** the entry and reports replaced rather than added, so the UI can flash the correct message. Computed inside the write lock | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ❌ W0 | ⬜ pending |
| TBD | registry | 0 | D-12 | T-14-02 | Concurrent writers cannot lose an update: the whole load-check-mutate-write sequence is under one module-level lock, temp filenames are pid/thread-scoped | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ❌ W0 | ⬜ pending |
| TBD | resolver | 1 | D-13 | — | **Effective-theme truth table**, all seven rows: no rule and no override yields the base theme; override set with state arriving yields the override; override set with state departing yields the base theme; a matching prefix rule beats the base theme; a matching hex rule beats a matching prefix rule; a matching callsign rule beats a matching hex rule; a matching rule beats the arrivals override | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ❌ W0 | ⬜ pending |
| TBD | config | 1 | D-04 | — | `theme_arriving` unset degrades to `None`, never to `DEFAULT_THEME_ID`; a hostile or stale on-disk value degrades the same way; round-trips through save and load | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ extend | ⬜ pending |
| TBD | config | 1 | D-04 | — | **The clearable contract**: saving with the arrivals checkbox unchecked genuinely clears a previously-set `theme_arriving`, rather than carrying it forward. This is the behaviour `wake_interval_s` deliberately does **not** have, so it cannot be inherited by copying that field | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ extend | ⬜ pending |
| TBD | poll-loop | 2 | D-13 | T-14-03 | **Both-render-branches invariant**: the identical flight, across two `run_once()` calls where only the battery state changed between them, produces the identical effective theme id. A rule or override must never flip the panel's theme on a battery-icon repaint | integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ extend | ⬜ pending |
| TBD | poll-loop | 2 | D-13 | T-14-03 | The four flight-less `build_canvas()` call sites, both empty states and both hold screens, never consult a rule or the arrivals override, even when one is configured that would otherwise match | unit + integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ extend | ⬜ pending |
| TBD | settings UI | 3 | D-10 | — | Add and delete are immediate POSTs outside the Settings form: a pending rule edit is never captured by the dirty bar, and the main form's all-or-nothing `save_device_config()` contract is untouched | integration | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ extend | ⬜ pending |
| TBD | settings UI | 3 | D-10 | — | **The no-JS path**: a raw HTTP POST body, bypassing any client script, produces the correct persisted state for the Settings form, the rules add form, and a delete form | integration | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ extend | ⬜ pending |
| TBD | all plans | — | D-07 | — | A must-NOT-change check: `server/plane/render.py`'s composition is untouched and no new element reaches the panel. The existing `EXPECTED_CHECK_COUNT` ledgers in `server/test_render.py` hold without edit | unit | `server/.venv/bin/python3 server/test_render.py` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/test_colour_rules.py` — new harness covering the registry contract (load, add, delete, cap, hostile-input rejection, added-versus-replaced) and the resolver truth table. Mirror `server/test_manual_resolutions.py`'s structure and its `EXPECTED_CHECK_COUNT` ledger-comment discipline.
- [ ] `scripts/run-all-tests.sh` — register the new harness in the `HARNESSES` array. A harness that is not registered is not run by the suite or the coverage gate.
- [ ] No shared fixtures needed — use `tempfile.TemporaryDirectory()` per test, matching every existing harness. This project does not use pytest, so no `conftest.py` exists and none should be introduced.
- [ ] Framework install: none. The harness pattern requires zero new packages.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Genuine no-JS browser confirmation of the arrivals-grid reveal and the rules add/delete forms | D-05 / D-10 | The automated half covers the raw HTTP POST semantics, but the CSS reveal, focus order and screen-reader announcement need a real browser with scripting disabled. This project has a standing lesson that computed-style checks alone missed a real mobile navigation bug | Load Settings with JavaScript disabled. Confirm: the arrivals grid is reachable and selectable; toggling the checkbox reveals and hides it; a rule can be added and deleted; the dirty bar never claims unsaved changes because of a rule action. Runs as a `checkpoint:human-verify` at end of phase, matching `human_verify_mode: end-of-phase` and the 10-05 / 11-03 / 11-04 precedent |

**No on-glass verification is in scope.** Every rule and override resolves to an already-registered theme id, so nothing new reaches the physical panel. This is a deliberate consequence of D-07 and is recorded in the ROADMAP's revised "Closes with" line.

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
