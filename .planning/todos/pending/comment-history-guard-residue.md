---
title: Tighten the comment-history guard and reword the residue it misses
created: 2026-09-28
source: Phase 41 closing re-audit (HYG-01, HYG-06 accepted open)
area: tooling / comments
---

# Tighten the comment-history guard and reword the residue it misses

## Why this exists

The Phase 41 re-audit found HYG-01 and HYG-06 genuinely open. On 2026-09-28
the developer accepted both as-is so Phase 41 could close and Phase 42 (OTA)
could start. This todo holds the deferred fix. No runtime behaviour is
involved: only comments, docstrings and a lint-guard regex.

## What is wrong

- **HYG-06**: `scripts/check_comment_history.py` misses:
  - letter-suffixed decision IDs (`D-14c`)
  - dotted UI-SPEC section IDs (`06.6.4.1.1-04`)
  - bare plan IDs with no "plan"/"Task" marker (`39-13`, `(23-03, D14)`, `22-15's`, `pre-06-10`)
  - dotted, `v`-prefixed or quick-task threat IDs (`T-03.1-03-01`, `T-v26-01-01`, `T-kih-01`)
  - the `A-`, `S-` and `UF-` finding prefixes
- **HYG-01**: a prototype of the tightened patterns found about 85 real hits
  in 34 files. Most are companion/server test files. The rest are
  `pyproject.toml`, `server/plane/render/cli.py`,
  `companion/static/panel-lookup.js` and `scripts/check-attribution.sh`. The
  JS and shell sites mean the HYG-02 and HYG-03 "zero genuine hits" evidence
  was also optimistic.
- Prose history no regex can enforce without false positives (planning-time
  upper bounds): "Task N" labels (~57), bare review codes like X5/D19 (~67),
  lowercase "phase N"/"plan N" (~15), planning-document names (~16),
  "Polish fix N" (~3).

## Ready-made plan

Six gap-closure plans were drafted and checker-approved, then withdrawn in
favour of the accept-as-is decision. Recover them with
`git show 3e45e90a --stat` and `git show 3e45e90a:<path>`.

| Plan | Scope |
|---|---|
| 41-09 | Guard tightening, test-first with mutation proof, then a whole-tree hunt ledger |
| 41-10 | Reword companion app / browser-UX tests and static JS |
| 41-11 | Reword settings-page and status-page tests |
| 41-12 | Reword view-page tests, `server/`, `pyproject.toml`, `check-attribution.sh` |
| 41-13 | Final gates: base replay against `3f8fb9ca`, comment-only proof, firmware fence |
| 41-14 | REQUIREMENTS.md and closing-audit bookkeeping |

The detailed gap specification is under `gaps_accepted:` in
`.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-VERIFICATION.md`.

## Constraints

- Never edit `firmware/` from this work. The one prose hit there
  (`firmware/main/battery.c`, "Task 3's") needs its own decision.
- Remove false positives by narrowing a pattern, never by allow-listing a
  real reference.
- The guard fails CI from the moment the regex is tightened until every
  reword lands, so land the regex and the rewording in one PR.
