# Deferred Items — Phase 23

Out-of-scope discoveries logged per the executor's scope-boundary rule
(not fixed in the plan that found them; each names the plan that should).

## 23-01 / 23-04: CFG-32 and CFG-33 traceability rows are stale, and their boxes stay unticked

**Discovered during:** 23-01 Task 2 (the rows did not exist at all), reconfirmed
during 23-04 (they exist now, but describe work as "Planned" that has landed).

**State on disk:** `.planning/REQUIREMENTS.md` now carries CFG-32…CFG-38 (added
after 23-01 reported the gap). Both rows relevant to the plans executed so far
still read:

- `| CFG-32 | Phase 23 | Planned — served by 23-01 (…), then 23-04, 23-05, 23-08, 23-09, 23-10; 23-11 closes |`
- `| CFG-33 | Phase 23 | Planned — 23-04, closed by 23-11 |`

**Why not fixed here:** 23-04's `<files_owned>` names exactly three files
(`companion/static/style.css`, `companion/test_companion_app.py`,
`companion/test_browser_ux.py`), none of them `REQUIREMENTS.md`, and the standing
instruction for this wave is explicitly *not* to tick either checkbox — 23-11
closes both requirements and owns the coverage ledger.

**For 23-11:** tick CFG-32 and CFG-33 and rewrite both rows against what actually
landed. CFG-33 is served IN FULL by 23-04 (one media-wrapped at-rule, three names,
per-route uniqueness proven in a browser); nothing about D10 remains open beyond
the human sweep.

## 23-04: `.now-showing__image` is a selector with no render site

**Discovered during:** 23-04 Task 1, while answering the plan's `read_first`
question about the four-selector rule `.preview-frame__image` shares
(`companion/static/style.css:6436`, was `:6353` before this plan).

**Symptom:** `.now-showing__image` appears twice in `style.css` (the shared
white-backing/hairline/radius rule, and its own `max-width: 360px` sizing rule
immediately below) but `grep -rn "now-showing__image" companion/**/*.py` returns
only harness files — **no page module renders that class any more.** The
`.now-showing` wrapper rule above it is in the same position.

**Why not fixed here:** out of scope by the executor's scope boundary — it is not
caused by this plan's changes, and deleting rules from a stylesheet that four
harnesses scan is a deliberate edit with its own verification, not a side effect
of adding nine declarations. It is also harmless: the rule is inert, and
`.preview-frame__image` (which legitimately shares it) is unaffected either way.

**For 23-11:** worth a look during the design-system sweep, together with the
`test_view_pages.py:5173` check that asserts the two classes share that rule —
that check would need retargeting, not deleting, if the dead selector goes.

## 23-04: 23-RESEARCH.md and every unexecuted Phase 23 plan state a nav count that is wrong

**Discovered during:** 23-04 Task 2, by measurement (mutation M2).

**Symptom:** `23-RESEARCH.md`'s Risk 3 and `23-04-PLAN.md`'s `<interfaces>` both
state that `companion/layout.py` renders **three** navigation copies into every
authenticated document (sidebar, `.mobile-nav` preferences panel, `.tab-bar`).
**22-14 Task 2 removed `<nav class="mobile-nav__nav">` outright** rather than
emptying it (`layout.py:1821`, with its own comment explaining that an empty
landmark would still be announced). The live count is **two**:
`nav.sidebar-nav` (`layout.py:1440`) and `nav.tab-bar` (`layout.py:1621`).

**Consequence:** none for D10 — two is still a collision and the prescription
(`.dashboard-sidebar`, never a shared class) is unchanged. 23-04 corrected the
claim in the two files it owns. Any later plan quoting the research on this
should quote two.
