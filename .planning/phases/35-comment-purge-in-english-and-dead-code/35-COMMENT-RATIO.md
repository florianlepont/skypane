# Phase 35 comment ratios, per PR group

Recorded by each group-closing plan as it purges its files, using
`server/.venv/bin/python scripts/check_comment_history.py ratio --before
35-BASELINE/ratio-before.tsv --markdown <files>`. "Before" figures come from
`35-BASELINE/ratio-before.tsv` (measured on commit `83f4620` plus the
foundation plan's own additions); "after" figures are measured on this
group's own HEAD once its files are code-unchanged (proven by `same-code`)
and history-free (proven by `check`). A file above the ~35% review-trigger
guideline after purge is listed with a one-line justification pulled from
its plan's SUMMARY — the guideline is advisory, not a hard gate; the actual
gate is 0 history hits.

## Group 2 — server/

Source plans: 35-02 (`server/plane/{render,illustrations,colour_rules,
dither,runway_config}.py`), 35-03 (`server/plane/{calendar_rules,enrich,
detect,manual_resolutions}.py`), 35-04 (`server/poll_loop.py,
device_config.py, history_db.py, wake.py, notify.py, panel_format.py,
panel_preview.py, requirements.in, requirements-dev.in, .gitignore,
state/.gitignore`), 35-05 (every `server/test_*.py`).

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| server/.gitignore | 15 | 15 | 26.7% | 26.7% | 0 -> 0 |
| server/device_config.py | 1154 | 726 | 55.6% | 29.5% | 113 -> 0 |
| server/history_db.py | 723 | 539 | 47.0% | 28.9% | 28 -> 0 |
| server/notify.py | 212 | 130 | 60.4% | 35.4% | 25 -> 0 |
| server/panel_format.py | 145 | 99 | 66.2% | 50.5% | 19 -> 0 |
| server/panel_preview.py | 160 | 126 | 47.5% | 33.3% | 7 -> 0 |
| server/plane/__init__.py | 0 | 0 | 0.0% | 0.0% | 0 -> 0 |
| server/plane/calendar_rules.py | 2221 | 1418 | 61.8% | 40.2% | 118 -> 0 |
| server/plane/colour_rules.py | 532 | 394 | 44.4% | 25.6% | 27 -> 0 |
| server/plane/detect.py | 1129 | 857 | 58.9% | 45.9% | 46 -> 0 |
| server/plane/dither.py | 140 | 105 | 53.6% | 38.1% | 10 -> 0 |
| server/plane/enrich.py | 1157 | 773 | 68.7% | 50.6% | 95 -> 0 |
| server/plane/illustrations.py | 1177 | 884 | 43.5% | 24.8% | 93 -> 0 |
| server/plane/manual_resolutions.py | 508 | 430 | 53.5% | 45.1% | 28 -> 0 |
| server/plane/render.py | 3044 | 2049 | 52.1% | 29.1% | 312 -> 0 |
| server/plane/runway_config.py | 97 | 61 | 74.2% | 59.0% | 12 -> 0 |
| server/poll_loop.py | 1986 | 1307 | 56.8% | 34.4% | 218 -> 0 |
| server/requirements-dev.in | 32 | 32 | 68.8% | 68.8% | 3 -> 0 |
| server/requirements.in | 12 | 12 | 83.3% | 83.3% | 0 -> 0 |
| server/state/.gitignore | 2 | 2 | 0.0% | 0.0% | 0 -> 0 |
| server/test_calendar_rules.py | 2145 | 2140 | 13.5% | 13.3% | 24 -> 0 |
| server/test_colour_rules.py | 481 | 480 | 10.8% | 10.6% | 13 -> 0 |
| server/test_config_history.py | 1889 | 1857 | 16.8% | 16.2% | 44 -> 0 |
| server/test_dither.py | 100 | 100 | 29.0% | 29.0% | 12 -> 0 |
| server/test_enrich.py | 1044 | 1038 | 14.1% | 13.6% | 61 -> 0 |
| server/test_fault_screen_mask.py | 60 | 59 | 28.3% | 27.1% | 2 -> 0 |
| server/test_illustrations.py | 821 | 830 | 13.9% | 13.6% | 40 -> 0 |
| server/test_manual_resolutions.py | 353 | 352 | 11.9% | 11.6% | 14 -> 0 |
| server/test_notify.py | 207 | 207 | 24.2% | 24.2% | 7 -> 0 |
| server/test_panel_preview.py | 204 | 204 | 19.6% | 19.6% | 1 -> 0 |
| server/test_pipeline_e2e.py | 462 | 457 | 29.9% | 29.1% | 12 -> 0 |
| server/test_plane_detection.py | 1114 | 1115 | 31.2% | 31.3% | 12 -> 0 |
| server/test_poll_loop.py | 3268 | 3265 | 15.8% | 15.7% | 65 -> 0 |
| server/test_render.py | 3750 | 3190 | 27.5% | 14.5% | 186 -> 0 |
| server/test_runway_config.py | 154 | 152 | 22.1% | 21.1% | 6 -> 0 |
| server/wake.py | 442 | 201 | 71.3% | 37.3% | 36 -> 0 |
| **Group 2 total** | **30940** | **25606** | **37.2%** | **24.1%** | **1689 -> 0** |

The group total matches `35-BASELINE/INDEX.md`'s "before" row for group 2
(36 files, 30940 lines, 37% ratio, 1689 history hits) exactly, confirming
every file the baseline counted is accounted for here.

### Files still above the ~35% guideline

Each was re-read a second time in its plan hunting for restatement, scope
talk, and "who calls this" asides; nothing remained to cut without dropping
a genuine invariant. Justifications summarized from the source plan
SUMMARYs (35-02/35-03/35-04):

| File | After | Justification |
|---|---:|---|
| server/plane/runway_config.py | 59.0% | Smallest file in the group (61 lines); its entire content is one asymmetric-confidence warning (descend threshold real-flight-backed, climb threshold symmetry-derived and unverified) that purge_rules require to survive — a 61-line file with one paragraph of that density cannot sit under 35%. |
| server/plane/enrich.py | 50.6% | Dominated by one 46-entry curated ICAO-airline-prefix table where roughly a third of entries need a short correction/attribution rationale so a future contributor does not "fix" a deliberately non-obvious mapping; purely evidentiary citations were already stripped. |
| server/panel_format.py | 50.5% | Smallest file in its plan (99 lines): the `PALETTE_RGB` table carries necessarily-brief per-entry hardware-calibration annotations, and `pack_panel()`'s docstring is a genuine bit-manipulation correctness proof. |
| server/plane/detect.py | 45.9% | Two functions document a genuinely complex contract — the candidate-set cross-validation algorithm across two independent ADS-B feeders, and the geofence output-tag contract — both compressed to algorithmic essence, not restatement. |
| server/plane/manual_resolutions.py | 45.1% | Small, security-dense file by design: this project's first runtime-writable identity namespace, where nearly every function documents a distinct defence-in-depth layer (two-layer path safety, write-lock vs. a plain race, deliberate no-touch on delete). |
| server/plane/calendar_rules.py | 40.2% | Concentrates six largely-independent security/correctness domains (SSRF-hardened fetch, cross-process advisory lock, hand-rolled RFC 5545 subset parser, tamper-resistant registry with two DoS bounds, permission-drift detector, matching algorithm) each earning its own short why-comment. |
| server/plane/dither.py | 38.1% | Documents three distinct, non-obvious Pillow footguns (palette-pad, `.point()` remap, 6-colour quantizer misclassification) across four short functions in a 105-line file; four one-line invariants alone put it above 35%. |
| server/wake.py | 37.3% | Small module (201 lines) of precedence lists and staleness-threshold derivations shared by server and companion; `next_wake_status()`'s docstring documents a genuinely non-obvious two-call composition that is algorithmic why, not restatement. |
| server/notify.py | 35.4% | Sits essentially at the guideline: remaining comments are almost entirely the SSRF-gate-reuse and redirect-refusal security invariants purge_rules require to survive. |
| server/requirements-dev.in | 68.8% | Hash-comment dependency manifest, not Python code — nearly every line is a one-line why-comment explaining an install/lint/test package's purpose or dev-only scope; already history-free (3 -> 0 hits). |
| server/requirements.in | 83.3% | Hash-comment dependency manifest never carried any history reference (0 hits before and after) — its comments explain the runtime-only dependency policy and the regeneration procedure, not project history. |
