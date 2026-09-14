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

## 23-05: `test_i18n.py`'s Check 6 excludes "a bare selector" in prose but not in code

**Discovered during:** 23-05 Task 1, twice — once for `relative-time.js`'s own
`[data-relative]` hook and once for `freshness.js`'s new `[data-refresh-live-dot]`
one.

**Symptom:** Check 6's module comment states its allowlist keeps it "from
demanding a translation for a CSS class, a selector, an attribute name or an
event name". `_container_exclusion_reason()` implements the class/attribute/event
half (`_HYPHENATED_IDENTIFIER_RE` plus a required `-`), but a BRACKETED attribute
selector — `"[data-relative]"` — matches none of the exclusion rules, so an
upper-case constant holding one is demanded as translatable prose. No script
carried such a constant before this plan, which is why it had never surfaced.

**Why not fixed here:** widening an exclusion list is weakening a check, and the
standing constraint for this phase is that the suite carries no test exception.
23-05 sidestepped it instead, in both files, by giving the attribute NAME its own
constant and building the selector from it (`"[" + RELATIVE_ATTR + "]"`) — which
is independently better (the name then has exactly one site) and leaves the
harness untouched. Each site says so in its own comment.

**For 23-11 (or whichever plan next edits `test_i18n.py`):** either tighten the
allowlist to match its own stated boundary with an exact `^\[[a-z0-9_-]+\]$`
shape, or amend the comment so it stops promising an exclusion that does not
exist. The second is cheaper and arguably more honest; the first needs a mutation
proving it does not over-exclude.

## 23-05: 23-03-SUMMARY.md assigns `health_page.py`'s freshness line to 23-06, but 23-05 owns it

**Discovered during:** 23-05 Task 2, while reading the inventory 23-03 built.

**Symptom:** `23-03-SUMMARY.md`'s "CONVERTED BY A LATER PLAN" table routes
`health_page.py:3009` — the freshness line's own `relative_age_text()` — to
**23-06**, on the stated ground that "`health_page.py` is not in this plan's
`files_modified`; 23-06 owns it". `23-05-PLAN.md` names
`companion/pages/health_page.py` in its own `files_modified` and its Task 2 is
precisely that conversion, so the routing is one plan out.

**Consequence:** none — 23-05 executed alone in its wave, did the conversion, and
`health_page.py` is not touched by any other plan in flight. The line noted there
as 23-06's is now live.

**For 23-06:** its own plan text may still say it promotes the freshness line into
`layout.py` as one builder. That work is now a REFACTOR of something that already
renders a `<time data-relative>` element, not a conversion. `health_page.py:1150`
— the `when` text `battery-trend.js` copies into a `title` attribute — is
untouched and still cannot become an element without changing that script's
transport first, exactly as 23-03 recorded.

## 23-06: Display's page header now carries a freshness line above the screen caption

**Discovered during:** 23-06 Task 2, while wiring the Display scope's call site.

**Symptom (not a defect — a visual change to check on a device):** the Display
scope's `page_header()` call now passes `freshness_html`, which `page_header()`
concatenates BEFORE `action_html`. So the header reads title → "Updated 14:32"
(+ hidden pill) → screen caption/selector → purpose sentence. The hidden
"Updating…" pill is absolutely positioned to `.page-header`'s top-right corner,
which on that page is unoccupied today because `_screen_selector_html()` renders
`""` with a single-member screen registry.

**Why not resolved here:** nothing is wrong to fix. It is a layout question no
string-comparison harness can answer, at a 360px width the wave-9 sweep already
visits, and the collision it could become does not exist yet.

**For 23-11 (human sweep):** look at `/display` at 360px and confirm the
freshness line reads as a caption under the title rather than as a competing
header row. **And for any plan that adds a control to Display's header**: the
top-right corner is now the refresh pill's, and two things stacked on the same
coordinates is not a state a user can read (the same argument 22-15 made when it
put the state badge in flow rather than in that slot).

## 23-06: `.is-fading-in` exists before 23-10's "preview crossfade" is planned

**Discovered during:** 23-06 Task 2, spending 23-01's `--motion-fast` token.

**State on disk:** `companion/static/style.css` now declares a SECOND
`@keyframes` block (`skypane-fade-in`) and one consumer, `.is-fading-in`, which
`companion/static/freshness.js` adds to `.preview-frame__image` when a refresh
brings a genuinely different `src`. The ROADMAP's Phase 23 entry assigns "preview
crossfade" to 23-10.

**Why not resolved here:** 23-10 is not this plan's to write, and the rule that
exists is the one D1 needed (a one-shot fade on a new render), not necessarily
the crossfade D3 asks for.

**For 23-10:** spend `.is-fading-in` and `skypane-fade-in` rather than declaring
a third block — 23-01's guard fails a second definition of the same name, and two
near-identical fade blocks is exactly the failure that guard's own message names.
If a true crossfade (old and new visible at once) is wanted, it is a different
mechanism from this one and needs its own argument in the stylesheet beside the
existing paragraph.

## 23-09: two shipped scripts-blocked checks fail by 30s TIMEOUT, not by a message, when the fallback Save is hidden

**Discovered during:** 23-09 Task 3, mutation M8 (the `.dirty-ready.dirty-shown`
gate on `[data-static-save-fallback]` replaced by an unconditional
`display: none` — a faithful reproduction of B1's second half).

**Symptom:** the mutation reddens four checks, and only ONE of them says what
happened. `_the_no_js_floor_holds_for_both_settings_pages` (22-10-PLAN.md Task 3)
and `_display_still_saves_with_scripts_blocked_at_360px` (23-06-PLAN.md Task 3)
both call `.click()` on the hidden control and fail with a raw Playwright
`TimeoutError`/`Element is not attached to the DOM` after 30 seconds each — one
minute of runtime, and a message a reader has to decode. 23-09's own new check
fails in the same run with `the fallback Save is rendered but not visible — which
is precisely the shape B1 took, and a check that only asked whether it EXISTS
would have passed through it`.

**Why not fixed here:** both checks belong to other plans and neither is wrong —
they DO go red, which is the property that matters, and adding an
`is_visible()` precondition to each is a two-check edit with its own mutation
burden inside a plan already carrying the app's most-iterated component. It is a
diagnosability cost, not a correctness gap, and the one-sentence diagnosis now
exists beside them.

**For 23-11 (or whichever plan next edits `test_browser_ux.py`):** give both a
cheap `is_visible()` precondition before the click, so B1's own shape produces a
sentence rather than a minute of waiting. The message to reuse is in
`_with_no_script_there_is_no_bar_and_the_fallback_save_is_the_only_way()`.
