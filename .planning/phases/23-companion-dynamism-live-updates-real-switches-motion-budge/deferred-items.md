# Phase 23 — deferred items

Out-of-scope discoveries logged during execution, not fixed by the plan that
found them.

## 1. CFG-32 … CFG-38 are missing from `.planning/REQUIREMENTS.md`

**Found during:** 23-01, state-update step.

`ROADMAP.md`'s Phase 23 entry names seven requirements (CFG-32 motion budget,
CFG-33 view transitions, CFG-34 live counters + D22's remainder, CFG-35
self-refreshing Home and Frame strip, CFG-36 real switches, CFG-37 live flights
list, CFG-38 the regression floor). `REQUIREMENTS.md` stops at CFG-31, so none of
them has a checkbox or a traceability row:

    grep -c 'CFG-3[2-8]' .planning/REQUIREMENTS.md   ->  0
    gsd-sdk query requirements.mark-complete CFG-32  ->  not_found

**Consequence:** every Phase 23 plan's `requirements:` frontmatter is currently
unlandable, and 23-11's coverage ledger cannot reconcile against a file that does
not list the requirements it is meant to cover.

**Why not fixed here:** 23-01 owns `companion/static/style.css` and
`companion/test_companion_app.py` only. Authoring seven requirement rows is a
planning-artifact change, not this plan's licence.

**Disposition:** add the seven rows to `REQUIREMENTS.md` before 23-11, and
re-run `requirements.mark-complete` for every plan already executed (23-01 →
CFG-32).
