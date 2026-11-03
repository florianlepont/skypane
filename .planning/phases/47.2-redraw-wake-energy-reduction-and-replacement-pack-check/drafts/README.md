# Drafts salvaged from the 47.1 planning

These eight files are the former plans 47.1-09 to 47.1-16 (selection of reductions, redraw-policy record, gzip on the server, panel-wait light sleep, gzip in the firmware, Wi-Fi channel hint, owner-gated reduction release with before/after comparison, replacement-pack check). They are design notes, not executable plans:

- they carry the suffix `-DRAFT.md` so tooling does not treat them as plans;
- their frontmatter, plan numbers, wave numbers, `depends_on` and file lists are the 47.1 ones and are stale; their content is otherwise kept as it was written;
- they are to be re-planned just in time, after the 47.1 baseline is recorded (the choice of reductions comes from the measured breakdown, not from a prior).

## Plan check findings that apply to these drafts

The plan check of 2026-11-03 raised these; each must be resolved when the drafts are re-planned.

- W7 (draft 11): the compression-ratio measurement on every shipped production theme (and the check that an inflate routine exists in ESP-IDF 5.3.1) belongs before the owner's choice of candidates, as part of the evidence the owner decides on, not after the choice.
- W8 (draft 10, task 2 "Decision record and the owner's answer"): split into an auto task (run the replay, write the decision record and the French part) and a pure `checkpoint:decision` task that only asks the owner and records the answer.
- W9 (drafts 09, 14, 15, static IP): a static IP is a replacement of the fleet registry entry plus a Wi-Fi password typed only into the no-echo prompt of the provisioning step, never in chat. Either drop the static IP candidate, or specify the full procedure (registry replacement, the no-echo prompt, router reservation, way back).
- W10 (draft 16, pack curve): the pack-curve step must name its per-wake-cost source (the baseline fit or the duration-only comparison, whichever exists) and cannot use the old rated curve of the old pack for the new pack.

Other points for the re-plan: the closure rules in `47.2-CONTEXT.md` are PROPOSED and need the owner's agreement; the draft 13 and draft 14 gates still depend on drafts 11 and 12 results; keep each plan within two or three tasks (draft 15 mixes a tool, a release gate and a comparison and should be split).
