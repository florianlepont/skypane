---
phase: quick-260903-etm
plan: 260903-etm
type: execute
mode: quick
wave: 1
depends_on: [260903-c4o]
files_modified:
  - companion/pages/history_page.py
  - companion/test_view_pages.py
  - companion/static/style.css
autonomous: true
requirements: [QUICK-260903-etm]

must_haves:
  truths:
    - "Developer redirection, superseding quick task 260903-c4o's own headline deliverable ON THE SAME BRANCH: History's top-of-page render-gallery `<section>` does not exist at all. Not enlarged, not uniform-in-a-grid, not collapsed behind a disclosure, not moved below the table — GONE. `render()`'s return value is `header + body + lightbox_html`, with no third term. The audit's own UIR-09 fix and c4o's replacement for it are both retired; the per-row lightbox is the sole way to see a rendered panel on this page."
    - "`gallery_tiles()` is deleted outright — `render()` was its only caller (grep-verified: `companion/pages/history_page.py` L924 was the sole call site repo-wide)."
    - "`gallery_entries_list` STAYS. It is not gallery-section state — it is the input to `nearest_gallery_entry(gallery_entries_list, row[\"raw_ts\"])`, which every per-row View-panel trigger depends on. Deleting it would silently remove every trigger button from the page. `shown_count` and `caption_and_caveat_html` DO go (they existed only to build the removed markup)."
    - "The per-row lookup keeps reading the FULL entry list, never a capped slice. `GALLERY_DISPLAY_LIMIT` only ever capped the visual grid (`entries[:GALLERY_DISPLAY_LIMIT]` inside `gallery_tiles()`); `nearest_gallery_entry()` already scans everything `companion/app.py::gallery_entries()` returns. Retiring the constant therefore cannot narrow which rows get a trigger — do not reintroduce a cap anywhere in the lookup path."
    - "Grep-confirmed dead after the two deletions above, and therefore removed: `RENDER_GALLERY_HEADING`, `RENDER_GALLERY_CAPTION_TEMPLATE`, `_NO_RENDERS_HEADING`, `_NO_RENDERS_BODY`, `GALLERY_DISPLAY_LIMIT`, `_PANEL_WIDTH`, `_PANEL_HEIGHT`, plus their explanatory comment blocks."
    - "`_PANEL_WIDTH`/`_PANEL_HEIGHT` were grep-checked during planning rather than assumed: their only reference in the whole repo is `companion/pages/history_page.py` L181, inside the `<img>` template in `gallery_tiles()`. Nothing else — not the lightbox, not `companion/app.py`, not `server/` — reads either constant. They go with their sole consumer."
    - "`_GALLERY_ROUTE_PREFIX` STAYS. Grep-confirmed shared: L166 (inside the deleted `gallery_tiles()`) AND L434 (`_view_panel_button_html()`, which this task keeps and extends). Deleting it would break every trigger's `data-view-panel-src` value."
    - "Untouched, byte-for-byte, `git diff`-empty on their function bodies: `_gallery_name_to_iso()`, `nearest_gallery_entry()`, `_lightbox_html()`, `LIGHTBOX_DIALOG_ID`, `LIGHTBOX_CAPTION_TEMPLATE`, `VIEW_PANEL_LABEL`, `_VIEW_PANEL_SRC_ATTR`, `_VIEW_PANEL_CAPTION_ATTR`, `_VIEW_PANEL_CLOSE_ATTR`. `_view_panel_button_html()` receives exactly ONE change (the new attribute below) and nothing else."
    - "`_view_panel_button_html()` gains a native `title` attribute on its trigger `<button>`, carrying the same `escape_html(VIEW_PANEL_LABEL)` value the existing `aria-label` already carries — one escape call's worth of change, computed once and interpolated into both slots so the two can never drift. No layout change, no new CSS, no new JS, no change to either `data-view-panel-*` attribute, no change to the icon. Well-precedented in this codebase: `layout.concise_timestamp_html()` (L543/L546) and `layout.status_dot()`'s optional `title` parameter (L1021, quick task 260902-w4t) both already use `title` for exactly this sighted-mouse-user purpose."
    - "RESOLVED DESIGN QUESTION (the one open item the task spec flagged, decided here rather than left to the executor): `COLOUR_CAVEAT` becomes fully orphaned by this removal — grep-verified, its only non-test reference in the entire repo is L913, inside the deleted section. It is NOT silently deleted and NOT left as orphaned dead prose. `LIGHTBOX_NOTE` absorbs it by COMPOSITION: `LIGHTBOX_NOTE` is redefined as its existing nearest-render sentence followed by `COLOUR_CAVEAT` verbatim, so `COLOUR_CAVEAT` keeps its definition, keeps its D-P2-03 provenance comment, gains a real live consumer, and exists in exactly one place with zero risk of two wordings drifting apart."
    - "Reasoning for that resolution, recorded so it is not re-litigated: the caveat's own documented rationale (`history_page.py` L57-65) is that a user comparing a render to the frame on the wall could otherwise mistake an expected render/glass colour mismatch for a hardware fault. That risk is a property of the rendered panel IMAGE, not of the grid layout that used to surround it — and the lightbox is now the only surface on History that shows that image at all, at a size where a user would actually compare colours. Deleting the caveat would drop a still-true safety note precisely as its relevance concentrated."
    - "Corroborating precedent, found during planning: `companion/test_status_pages.py` L4877-4881 records that the developer rejected note copy on the AIRLINES lightbox twice, and states the contrast explicitly — Airlines needs no note 'unlike History's own (which explains a real possible discrepancy an Airlines illustration never has)'. A render/glass colour mismatch is exactly such a real possible discrepancy, so this addition sits on the accepted side of that already-drawn line rather than reopening it."
    - "Reversal path if the developer rejects the composed two-sentence note anyway: revert `LIGHTBOX_NOTE` to its single sentence and delete `COLOUR_CAVEAT`. This is a two-line change with no structural consequence. SUMMARY.md MUST flag this decision explicitly for developer sign-off rather than presenting it as settled."
    - "`airlines_page.LIGHTBOX_NOTE` is a SEPARATE constant (`companion/pages/airlines_page.py` L94, deliberately `\"\"`), duplicated not imported. It must stay `\"\"` and `companion/pages/airlines_page.py` must carry zero diff from this task — the History note change cannot and must not leak onto Airlines."
    - "CI-BLOCKING CONSEQUENCE, found during planning, not discovered at commit time: `from companion.layout import empty_state, escape_html` (L41) currently binds `empty_state` for exactly ONE call site — L161, inside `gallery_tiles()`. The page's other empty state (L710) calls the module-qualified `layout.empty_state()`. Once `gallery_tiles()` is deleted the bare name is unused, and `server/.venv/bin/ruff check .` is a BLOCKING CI step (`.github/workflows/ci.yml` L42), so an F401 fails the build. The import MUST be narrowed to `escape_html` only. Do not `layout.`-qualify L710 instead; do not add a `# noqa`."
    - "History renders ZERO `<h2>` elements and ZERO `<section class=\"page-section\">` elements after this task. Grep-verified during planning: L918-919 were the page's only occurrences of either. This makes `count == 0` a genuinely strong structural assertion, not a proxy one."
    - "OUT OF SCOPE and carrying zero diff: `companion/app.py` (`gallery_entries()` still populates `ctx[\"gallery_entries\"]`, `/gallery/{name}.png` and `_serve_gallery_image()` still serve every lightbox image — both are load-bearing for the mechanism this task KEEPS), `companion/static/panel-lookup.js`, `companion/pages/airlines_page.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`, `companion/layout.py`, and everything under `server/`."
    - "`companion/static/style.css`: `.gallery-grid`, `.gallery-tile a` and `.gallery-grid img` (L2941-2961, comments included) are deleted — grep-verified during planning that `gallery_tiles()` was their only producer repo-wide and that Airlines' `.illustration-grid` (L2969) is a separate, differently-named rule that reuses none of the three selectors."
    - "Two style.css COMMENTS become factually wrong once those rules are gone and are corrected in place — they are prose, not the protected rules: L2599 (`Dashboard grid (D-02): same auto-fit/minmax idiom .gallery-grid already establishes as this file's responsive-grid precedent`) and L2963-2967 (`.illustration-grid`'s own 'A new class rather than a reuse of .gallery-grid above' rationale). Both point at a rule that will no longer exist. Correct them to name the surviving precedent instead. This is the ONLY change permitted to either neighbouring rule — the declarations themselves are untouched."
    - "L2184's `summary` comment already carried a stale mention of the 'Recent renders (N)' gallery disclosure (stale since c4o retired the disclosure). It is corrected in the same pass, dropping the now-nonexistent fourth call site from its enumeration. Same rule: comment text only, the `summary` declarations are untouched."
    - "NOT touched in style.css: `.copy-btn`, `.lightbox`, `.lightbox--wide`, `.lightbox__image`, `.lightbox__caption`, `.lightbox__note`, `.lightbox__note:empty`, `::backdrop`, `.readings-disclosure`, `.section-caption`, `.page-section`, `.illustration-grid`'s declarations. All have live consumers elsewhere (the lightbox itself, Airlines, Health's `<details>` disclosures, every other page's sections)."
    - "No new design tokens, no new fonts, no new JS file, no change to style.css's accent-reservation header comment, zero external references added to the stylesheet — the `sketch-findings-skypane` skill's standing constraints. This task adds no CSS at all; it only removes."
    - "No tombstone comments naming a deleted identifier survive in any edited file. A comment reading 'the gallery grid was removed by ...' would defeat its own dead-code gate. Removals are described in the commit message and in SUMMARY.md, never in the source file. Every verify gate below is comment-immune (Python via runtime attribute introspection and rendered-output inspection, CSS via a comment-stripping filter) so this rule is enforceable rather than aspirational."
    - "Test arithmetic, worked out during planning against the real file rather than left to the executor: FIVE checks are retired and FOUR are added, so `EXPECTED_CHECK_COUNT` goes 50 -> 49."
    - "The five retired checks and why: `_render_gallery_nonempty_structure` (asserts the heading, the caveat, the caption and three `<img>`s — every subject deleted), `_render_gallery_empty_state` (asserts `_NO_RENDERS_HEADING` and a single `<h2>` — both deleted), `_render_gallery_display_limit_newest_first` (asserts `GALLERY_DISPLAY_LIMIT` tiles — deleted), `_render_gallery_not_a_disclosure` (its whole subject was 'the render gallery is not wrapped in a disclosure'; with no render gallery it asserts nothing about anything that exists — its one surviving half, that History's own `history-card__details` disclosures live on, is FOLDED into new check 1 rather than dropped), and `_recent_renders_malformed_filename_caption_fallback` (asserts `class=\"gallery-tile\"` renders for a malformed filename — the tile is deleted; its residual value, that a malformed name degrades safely, is already covered TWICE, by `_gallery_name_to_iso_fixtures` and by `_nearest_gallery_entry_behaviour`'s own unparseable-entry-is-skipped fixture)."
    - "DELIBERATELY KEPT despite appearing in the task spec's list of five: `_render_gallery_no_preview_apparatus_even_with_panel_file`. Read at planning time — it asserts zero `/preview.png`, `preview-frame`, `preview-image` and the retired no-panel sentence, with a real `panel.bin` on disk. Every one of those assertions still passes unmodified after this task, and its real subject is the `/preview.png` ROUTE retirement, not the gallery section. Deleting it would silently drop c4o's route-retirement coverage. Retained in place; only its `check()` description prose is refreshed."
    - "The four added checks: (1) with a populated gallery AND seeded flight rows, the section is absent — zero `<h2`, zero `page-section`, zero grid-container class, zero tile class, zero heading text, zero empty-state heading text — WHILE the per-row mechanism is intact in the same render (at least one `data-view-panel-src`, exactly one lightbox dialog, and History's own card disclosures still present). (2) the same absence assertions hold with `gallery_entries=[]`, proving the section is gone in the empty case too and not merely emptied. (3) the trigger button carries `title=\"...\"` byte-equal to its own `aria-label` value, asserted on BOTH the desktop `<tr>` and the mobile `<li>` representation. (4) the colour caveat appears exactly once in the rendered page and that single occurrence lies inside the `lightbox__note` element — pinning the resolved design decision so it can be neither silently dropped nor accidentally duplicated."
    - "Check 3 follows the `title=\"...\"` contract-check style quick task 260902-w4t established at `companion/test_view_pages.py` L854-879 for `status_dot()` — assert the attribute's presence with its exact expected value, and assert the escaped form, rather than a bare substring match on `title`."
    - "ANTICIPATED collateral in `companion/test_view_pages.py`, found during planning — the executor retargets these rather than halting: `_img_tag_count()` (L210) and `_img_alt_values()` (L206) are helpers used at exactly two sites, L1203 and L1205, both inside `_render_gallery_nonempty_structure`. Both helpers become unused and are deleted with it. `_write_panel_file()` (L174) and `_seed_gallery()` (L191) STAY — both have surviving consumers. If ANY reference outside this anticipated set survives the sweep, STOP and report it in SUMMARY.md rather than deleting anyway."
    - "`_lightbox_dom_contract_three_file_guard` (L1544) was read during planning and references nothing being deleted — it must keep passing completely unmodified, as must `_nearest_gallery_entry_behaviour`, `_view_panel_triggers_per_row_full_render`, `_view_panel_empty_gallery_zero_triggers_zero_dialog`, `_view_panel_trigger_carries_nonempty_icon`, `_airlines_lightbox_constants_match_history`, `_gallery_name_to_iso_fixtures` and `_now_showing_no_preview_freshness_apparatus`. Do not edit any of them."
    - "Section 3's end-to-end check (`_history_preview_gallery_end_to_end`, L1883) keeps passing unmodified — `/gallery/{name}.png` is untouched and still returns a real PNG. Only its prose ('the route every gallery tile now links to') is refreshed to name the lightbox as the consumer, since there are no tiles any more. Prose-only: no count change."
    - "`scripts/run-all-tests.sh` reports ALL 16 canonical harnesses green with their exact pass counts recorded in SUMMARY.md — none skipped, `server/` included. Coverage stays above `fail_under = 83` and the exact reported percentage is recorded rather than assumed; deleting a covered function changes both numerator and denominator, so the direction of the shift must be measured."
    - "The browser verification runs against a COPY of `/tmp/skypane-prod-state` (confirmed present on disk at planning time), never the original: `cp -R` into scratch first, then serve from the copy. Do not start the server against the original snapshot under any circumstance."
    - "The BEFORE tree is reconstructible without depending on anyone remembering a pre-edit capture step: Task 1 records `BASE_SHA=$(git rev-parse HEAD)` as its very first action, and Task 3 rebuilds the before tree with `git archive $BASE_SHA`. That SHA is c4o's own tip, so the 'before' column measures c4o's shipped result — which is the comparison the developer actually asked for — while c4o-SUMMARY.md's recorded pre-c4o numbers supply the true original baseline for the third column."
    - "The mobile-height loop this task closes: c4o measured `/history` at 375px going 8423px (pre-c4o) -> 13450px (post-c4o, +5027px) and flagged it as an honest finding. This task's after-number at 375px MUST be recorded as an actual measurement and compared against BOTH of those figures. A number at or below 8423px closes the loop; anything else is a finding to report, not to hide."
    - "This task stays ON THE CURRENT BRANCH `claude/history-preview-gallery-32b974` (PR #36, unmerged). No new branch, no re-fork from origin/main. Its commits land on top of c4o's `ee74386` and `460d911`."
  artifacts:
    - path: "companion/pages/history_page.py"
      provides: "History with no top-of-page render-gallery section at all; the per-row View-panel lightbox as the sole rendered-panel surface, its trigger now carrying a native title tooltip, its note carrying the absorbed colour caveat"
      contains: "_view_panel_button_html"
    - path: "companion/test_view_pages.py"
      provides: "Four replacement checks pinning the section's total absence, the per-row mechanism's survival in the same render, the trigger's title/aria-label equality, and the caveat's new home"
      contains: "EXPECTED_CHECK_COUNT"
    - path: "companion/static/style.css"
      provides: "The stylesheet with the three orphaned gallery-grid rules retired and every comment that pointed at them corrected"
      contains: ".illustration-grid"
  key_links:
    - "render() -> nearest_gallery_entry(gallery_entries_list, ...) -> _view_panel_button_html() -> /gallery/{name}.png: the survival chain. Removing the section must not touch any link in it. The single most likely way to break this task is to delete gallery_entries_list along with the markup it used to feed."
    - "_view_panel_button_html()'s title and aria-label -> the SAME escaped VIEW_PANEL_LABEL value: computed once, interpolated twice, so a future edit cannot leave the tooltip and the accessible name saying different things."
    - "COLOUR_CAVEAT -> LIGHTBOX_NOTE -> _lightbox_html(): one constant, one composition, one render site. No second copy of the sentence anywhere."
    - "companion/app.py::gallery_entries() -> ctx['gallery_entries'] -> the lookup: untouched by this task but load-bearing for it. A zero-diff check on companion/app.py is part of the acceptance criteria precisely because this is the connection a careless 'remove the gallery' reading would sever."
---

<objective>
Remove History's top-of-page "Recent renders" gallery section entirely, per direct developer
redirection that supersedes quick task 260903-c4o's own headline deliverable on this same
unmerged branch. Every rendered panel stays reachable through the existing per-flight-row
"View panel near this time" lightbox (D-20), which this task keeps intact and improves with a
visible native tooltip on its trigger button.

Purpose: the developer decided, on reflection after seeing c4o's result, that the section
should not exist in any form — not enlarged, not uniform-in-a-grid, not behind a disclosure.
The per-row mechanism already covers the need. Removing the section also closes the mobile
page-height regression c4o measured and flagged (375px `scrollHeight` 8423px -> 13450px).

Output: `companion/pages/history_page.py` with the section, `gallery_tiles()` and seven dead
constants gone, the orphaned colour caveat rehomed into the lightbox note, and a `title`
attribute on the trigger button; `companion/test_view_pages.py` with five obsolete checks
retired and four replacements added (50 -> 49); `companion/static/style.css` with three
orphaned rules retired and three stale comments corrected.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/quick/260903-c4o-history-preview-gallery-from-06-6-4-1-ui/260903-c4o-SUMMARY.md
@companion/pages/history_page.py
@companion/test_view_pages.py
@companion/static/style.css
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: delete History's render-gallery section, rehome the colour caveat, give the View-panel trigger a native tooltip</name>
  <files>companion/pages/history_page.py, companion/test_view_pages.py</files>

  <behavior>
    - With three seeded gallery entries AND a seeded flight row, `history_page.render()` output
      contains zero `<h2` occurrences, zero `page-section` occurrences, zero occurrences of the
      grid container class, zero occurrences of the tile class, zero occurrences of the heading
      text, and zero occurrences of the no-renders empty-state heading text.
    - The SAME render still contains at least one `data-view-panel-src`, exactly one element
      with `id="panel-lookup-dialog"`, and at least one `<details class="history-card__details"`.
    - With `gallery_entries=[]`, all of the same absence assertions hold (the section is gone,
      not merely emptied) and, as before, zero triggers and zero dialogs render.
    - Every rendered View-panel trigger button carries `title="View panel near this time"` whose
      value is byte-equal to that same button's `aria-label` value, on both the desktop `<tr>`
      and the mobile `<li>` representation of the same row.
    - The colour caveat sentence appears exactly once in the rendered page, and that occurrence
      falls inside the `lightbox__note` element.
    - `companion.pages.history_page` no longer exposes `gallery_tiles`, `RENDER_GALLERY_HEADING`,
      `RENDER_GALLERY_CAPTION_TEMPLATE`, `GALLERY_DISPLAY_LIMIT`, `_NO_RENDERS_HEADING`,
      `_NO_RENDERS_BODY`, `_PANEL_WIDTH` or `_PANEL_HEIGHT`, and still exposes
      `_GALLERY_ROUTE_PREFIX`, `COLOUR_CAVEAT`, `nearest_gallery_entry`, `_gallery_name_to_iso`,
      `_view_panel_button_html`, `_lightbox_html`, `VIEW_PANEL_LABEL`, `LIGHTBOX_DIALOG_ID`,
      `LIGHTBOX_CAPTION_TEMPLATE` and `LIGHTBOX_NOTE`.
  </behavior>

  <action>
Record the base commit first, before touching anything: run `git rev-parse HEAD` and write the
SHA into your working notes. Task 3 needs it to rebuild the before-tree. Confirm `git branch
--show-current` reports `claude/history-preview-gallery-32b974` — if it reports anything else,
STOP and report, because this task must land on c4o's branch and must not fork a new one.

Then edit `companion/pages/history_page.py`.

Step A, `render()` (currently L878-964). Delete the entire block that builds the section: the
explanatory comment paragraph that opens it, the `shown_count` assignment, the
`caption_and_caveat_html` if/else, and the assignment that wraps a heading, a caption and the
tile grid in a `<section class="page-section">`. Keep the `gallery_entries_list` assignment
exactly as it is — it is the input to the per-row `nearest_gallery_entry()` call further down
and has nothing to do with the removed markup. Change the final return so it concatenates only
the header, the body and the lightbox markup, with no third section term. Do not reorder the
remaining terms, do not touch the `_DB_UNAVAILABLE` branch, and do not touch the per-row loop,
the `has_view_panel_button` computation, or the cards-before-table ordering comment.

Step B. Delete the whole `gallery_tiles()` function (currently L142-183) including its
docstring. Its only caller repo-wide was the block removed in Step A.

Step C. Delete these module-level constants together with the comment blocks that explain them:
the render-gallery heading constant, the render-gallery caption template, the two no-renders
empty-state constants, the gallery display-limit constant, and the two panel pixel-dimension
constants. Do NOT delete the gallery route prefix constant — it is shared with
`_view_panel_button_html()`.

Step D, the import on L41. It currently imports two names from `companion.layout`; the first of
them had exactly one binding site, inside the function deleted in Step B. Narrow the import to
the surviving name only. Do not switch the page's other empty-state call to a bare name to
"save" the import, and do not silence the lint with a suppression comment — `ruff check .` is a
blocking CI step and an unused import fails the build.

Step E, the colour caveat. It is now orphaned: its only non-test reference was the block deleted
in Step A. Keep the constant and its provenance comment, and give it a live consumer by
redefining the lightbox note constant as its existing single sentence, then a single space, then
the caveat constant concatenated in — one source of the sentence, no second wording anywhere.
Update the caveat's own comment block so its last paragraph states its current consumer (the
lightbox note, which is now the only place on this page a rendered panel image is shown) instead
of describing the retired section. Do not reword the caveat sentence itself; its wording is
verbatim from D-P2-03 and that lineage is deliberate. Do not touch `airlines_page`'s separate,
deliberately-empty note constant.

Step F, `_view_panel_button_html()` (currently L416-445). Add a native `title` attribute to the
trigger `<button>`. Compute the escaped label ONCE into a local, then interpolate that same local
into both the new `title` slot and the existing `aria-label` slot, so the tooltip and the
accessible name cannot drift. Change nothing else in this function: not the two
`data-view-panel-*` attributes, not the class, not the icon call, not the docstring's existing
content — append one sentence to the docstring noting the tooltip mirrors the accessible name
for sighted pointer users, and nothing more.

Leave `_gallery_name_to_iso()`, `nearest_gallery_entry()` and `_lightbox_html()` completely
alone. Do not leave a tombstone comment anywhere naming any symbol you deleted.

Now edit `companion/test_view_pages.py`.

Step G. Retire five checks and their registrations: the non-empty-structure check, the
empty-state check, the display-limit/newest-first check, the not-a-disclosure check, and the
malformed-filename caption-fallback check. Retire the two `<img>`-counting/alt-reading helpers
near L206-212 along with them — those two helpers' only call sites are inside the first of the
five. Keep the panel-file writer and the gallery seeder; both have surviving consumers.

Step H. KEEP the no-preview-apparatus check that sits among that group. Read it first: every one
of its assertions still holds after this task, and its real subject is c4o's `/preview.png` route
retirement, not the section. Refresh only its `check()` description prose so it no longer implies
a surrounding gallery section.

Step I. Add four checks in the retired group's place, in this order, each registered with a
`check()` description in the file's existing full-sentence style:

  1. Section-absent with content. Seed three gallery entries and one runway event, render, then
     assert every absence listed in this task's `<behavior>` block AND, in the same rendered
     string, assert the per-row mechanism survived: at least one trigger source attribute, exactly
     one dialog element keyed on the dialog-id constant, and at least one of History's own mobile
     card disclosure elements. Fold the surviving half of the retired not-a-disclosure check in
     here rather than dropping it.
  2. Section-absent with an empty gallery. Render with an empty entry list and assert the same
     absences, proving the section is gone rather than merely rendering empty.
  3. Trigger tooltip contract. Seed one gallery entry and one runway event so a trigger renders,
     locate the desktop row block and the mobile row block the way the existing per-row check
     already does, and for each assert the button carries a `title` attribute whose value equals
     the escaped label constant and equals that same block's `aria-label` value. Follow the
     assertion style of the `status_dot()` title check near L854-879 — assert the exact expected
     attribute string, not a bare substring match on the attribute name.
  4. Caveat rehomed. Render a page that emits a lightbox, assert the caveat sentence occurs
     exactly once in the whole output, and assert that occurrence lies within the note element's
     open/close tags.

Step J. Update `EXPECTED_CHECK_COUNT` from 50 to 49 and prepend a provenance comment in the
file's existing append-a-derivation idiom: 50 minus 5 retired plus 4 added, naming this quick
task. Also refresh the module docstring's opening paragraphs and Section 1b's banner comment so
neither still describes a render-gallery section as present, and refresh Section 3's end-to-end
`check()` description so it names the lightbox rather than gallery tiles as the consumer of the
image route — prose only, no assertion changes, no count change.

Do not edit any other check in this file. In particular do not touch the three-file DOM contract
guard, the nearest-entry behaviour check, the per-row trigger check, the empty-gallery
zero-triggers check, the trigger-icon check, the Airlines cross-module constants check, the
filename-reversal fixtures check, or the freshness-apparatus check.

Then run the sweep and report it: search the whole repo (excluding `.planning/`, `.venv` and
`__pycache__`) for each deleted symbol name and for the two retired grid class names. The only
surviving hits permitted are inside `companion/static/style.css` (Task 2 removes those) and
inside this plan's own file. Any other survivor: STOP and report it in SUMMARY.md instead of
deleting it.

Commit as one commit, conventional style, scope `quick-260903-etm`.

<!-- planner-discipline-allow: gallery-grid -->
<!-- planner-discipline-allow: gallery-tile -->
<!-- planner-discipline-allow: gallery_tiles -->
<!-- planner-discipline-allow: RENDER_GALLERY_HEADING -->
<!-- planner-discipline-allow: GALLERY_DISPLAY_LIMIT -->
<!-- planner-discipline-allow: _NO_RENDERS_HEADING -->
<!-- planner-discipline-allow: Recent renders -->
  </action>

  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && server/.venv/bin/python3 -c "
import companion.pages.history_page as m
gone = ['gallery_tiles','RENDER_GALLERY_HEADING','RENDER_GALLERY_CAPTION_TEMPLATE','GALLERY_DISPLAY_LIMIT','_NO_RENDERS_HEADING','_NO_RENDERS_BODY','_PANEL_WIDTH','_PANEL_HEIGHT']
kept = ['_GALLERY_ROUTE_PREFIX','COLOUR_CAVEAT','LIGHTBOX_NOTE','VIEW_PANEL_LABEL','LIGHTBOX_DIALOG_ID','LIGHTBOX_CAPTION_TEMPLATE','nearest_gallery_entry','_gallery_name_to_iso','_view_panel_button_html','_lightbox_html']
bad=[n for n in gone if hasattr(m,n)]; miss=[n for n in kept if not hasattr(m,n)]
assert not bad, 'still present: %r' % bad
assert not miss, 'wrongly removed: %r' % miss
assert m.COLOUR_CAVEAT in m.LIGHTBOX_NOTE, 'caveat not absorbed into the lightbox note'
b = m._view_panel_button_html('2026-08-27T10-00-00+00-00.png','2026-08-27T10:00:00+00:00')
import re
t = re.search(r'title=\"([^\"]*)\"', b); a = re.search(r'aria-label=\"([^\"]*)\"', b)
assert t and a and t.group(1) == a.group(1), 'title/aria-label mismatch: %r vs %r' % (t and t.group(1), a and a.group(1))
print('OK history_page symbol + tooltip + caveat contract')
"</automated>
    <automated>cd "$(git rev-parse --show-toplevel)" && server/.venv/bin/ruff check . && server/.venv/bin/python3 companion/test_view_pages.py</automated>
  </verify>

  <done>
`companion/pages/history_page.py` renders History with no `<h2>`, no `page-section` and no
render-gallery markup of any kind, while every per-row View-panel trigger, the single shared
lightbox and the nearest-render lookup behave exactly as before plus a `title` tooltip equal to
the accessible name; the colour caveat lives once, inside the lightbox note; `ruff check .` is
clean; `companion/test_view_pages.py` reports 49/49 with the five retired checks gone and the
four replacements passing; one commit scoped `quick-260903-etm` is on
`claude/history-preview-gallery-32b974`; the repo-wide sweep found no unanticipated survivor
outside `companion/static/style.css`.
  </done>
</task>

<task type="auto">
  <name>Task 2: retire the three orphaned gallery-grid stylesheet rules, correct every comment that pointed at them, and run the full suite</name>
  <files>companion/static/style.css</files>

  <action>
Re-run the grep that this plan already ran, and confirm the answer is unchanged before deleting
anything: the two grid class names must now appear in `companion/static/style.css` only, with
zero producers anywhere in `companion/`, `server/` or `stub-server/`, and Airlines' own
differently-named illustration grid must not reuse either of them. If the grep disagrees with
that expectation, STOP and report rather than deleting.

Then delete, from `companion/static/style.css`, the contiguous block currently at roughly
L2941-2961: the grid container rule with its own preceding two-line comment, the tile-anchor
`display: block` rule with its own preceding four-line comment, and the grid-image rule. Delete
each rule together with its own comment — leave no orphaned comment behind and no double blank
line where the block used to be.

Then correct three comments that will otherwise point at rules that no longer exist. These are
prose corrections only — do not change a single declaration in any of the three neighbouring
rules:

  1. The dashboard-grid comment near L2599 cites the deleted grid rule as this file's
     responsive-grid precedent. Repoint it at the surviving illustration grid, which now carries
     that role.
  2. The illustration-grid comment near L2963-2967 justifies itself as "a new class rather than a
     reuse of" the deleted rule and describes how its column floor and gap differ from it. With
     the comparand gone that rationale reads as a dangling reference. Rewrite it to state the
     rule's own contract (its column floor, its gap, and that it is this file's responsive-grid
     idiom) without citing a rule that no longer exists.
  3. The `summary` comment near L2178-2189 enumerates four real disclosure call sites, one of
     which is the migrated "Recent renders (N)" gallery disclosure. That fourth site was already
     retired by quick task 260903-c4o, so the enumeration has been stale since then; drop it and
     leave the three real sites. Do not touch the `summary` declarations themselves.

Do not touch, add to, or reformat any of these: the copy-button rule, any lightbox rule
including the wide variant, the note rule, the empty-note collapse rule, the backdrop rule, the
readings-disclosure rule, the section-caption rule, the page-section rules, the illustration-grid
declarations, or the stylesheet's accent-reservation header comment. Add no new rule, no new
token, no new font and no external reference — this task only removes.

Then run the full suite: `scripts/run-all-tests.sh`. Record every one of the 16 harnesses' exact
pass counts and the reported coverage percentage into your working notes for Task 3's SUMMARY —
deleting a covered function moves both the numerator and the denominator, so the direction of
the coverage shift must be read off the run, not predicted.

Commit as one commit, conventional style, scope `quick-260903-etm`.

<!-- planner-discipline-allow: gallery-grid -->
<!-- planner-discipline-allow: gallery-tile -->
<!-- planner-discipline-allow: Recent renders -->
  </action>

  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && python3 - <<'PY'
import re, sys
src = open('companion/static/style.css').read()
stripped = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
for token in ('gallery-grid', 'gallery-tile'):
    n = stripped.count(token)
    assert n == 0, 'expected 0 non-comment occurrences of %r, got %d' % (token, n)
for token in ('gallery-grid', 'gallery-tile'):
    n = src.count(token)
    assert n == 0, 'expected 0 occurrences of %r including comments (no dangling references), got %d' % (token, n)
for kept in ('.illustration-grid', '.copy-btn', '.lightbox__note', '.lightbox__note:empty', '.readings-disclosure', '.lightbox__image', '.lightbox__caption', '.lightbox--wide'):
    assert kept in stripped, 'wrongly removed protected selector %r' % kept
print('OK stylesheet retirement + no dangling comment references')
PY</automated>
    <automated>cd "$(git rev-parse --show-toplevel)" && scripts/run-all-tests.sh</automated>
  </verify>

  <done>
The three orphaned grid rules are gone from `companion/static/style.css` with their own comments,
no comment anywhere in the file still names either retired class, all three previously-citing
comments now describe only rules that exist, every protected selector is intact, and
`scripts/run-all-tests.sh` reports all 16 harnesses green with coverage above the 83 threshold —
exact pass counts and the coverage percentage recorded for the SUMMARY. One commit scoped
`quick-260903-etm` is on the branch.
  </done>
</task>

<task type="auto">
  <name>Task 3: real-browser before/after verification against production-shaped state, then SUMMARY.md</name>
  <files>.planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md</files>

  <action>
Pick the browser driver in this order, and record which one you actually used. First try a
Playwright MCP tool via ToolSearch — that is the preferred path. Only if it is genuinely
unreachable this session, fall back to the hand-driven Chrome DevTools Protocol technique quick
task 260903-c4o's executor documented: launch the repo's already-cached Playwright Chromium
(`~/Library/Caches/ms-playwright/chromium-1228`, confirmed present at planning time) with the
LEGACY `--headless` flag — c4o found the newer headless mode hangs indefinitely on screenshot
capture in this environment — and drive it over raw CDP using Node's built-in WebSocket/fetch
globals. Do not install anything.

Set up two trees and two state copies. `/tmp/skypane-prod-state` exists on disk (confirmed at
planning time); copy it, never serve from it:

  - AFTER: the current working tree, served against a fresh `cp -R` copy of the snapshot.
  - BEFORE: `git archive <BASE_SHA> | tar -x` into a scratch directory, where `<BASE_SHA>` is the
    SHA Task 1 recorded before its first edit — i.e. quick task 260903-c4o's own tip. Served
    against its own separate fresh copy of the same snapshot.

Run both under `server/.venv/bin/python3 companion/app.py --state-dir <copy>` with
`SKYPANE_COMPANION_PASSWORD` set for the session, authenticate, and load `/history` at 1440px and
375px in each tree.

Measure and record, for both trees at both widths:

  - the count of elements matching the retired grid container class on `/history` (must be 0 in
    the AFTER tree at both widths, and non-zero in the BEFORE tree — proving the measurement is
    actually looking at the right thing rather than passing vacuously),
  - the page's `scrollHeight`,
  - the flight list's `offsetTop`, choosing whichever of the mobile card list or the desktop
    table wrapper actually has non-zero rendered dimensions at that width — c4o hit exactly this
    trap, because the hidden one's `getBoundingClientRect()` is all zeroes,
  - the count of View-panel trigger buttons and the count of lightbox dialogs.

Then, in the AFTER tree only, verify the mechanism this task must not have broken:

  - read a trigger button's `title` and `aria-label` from the live DOM and confirm they are equal
    and non-empty (this is the developer's "improve access" half — confirm the attribute is
    genuinely on the element, not just in the server-rendered string Task 1 already asserted),
  - click a trigger, confirm the dialog opens, confirm the dialog image's `src` points at the
    expected `/gallery/{name}.png` and that the image actually loaded (non-zero `naturalWidth`),
    confirm the caption text matches the expected "Panel near {timestamp}" form, and confirm the
    note element's text contains the colour-caveat sentence,
  - capture screenshots at both widths for the record.

Then write `.planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md`
following the template, and specifically:

  - a **Browser Measurement (before/after)** table matching the format of the three prior quick
    tasks in this chain (260902-v2v, 260902-w4t, 260903-c4o). Give it THREE comparison columns
    where the numbers exist: the true original pre-c4o baseline (read from c4o-SUMMARY.md's own
    recorded figures — 375px `scrollHeight` 8423px, 1440px 4419px, 375px flight-list `offsetTop`
    975.19px, 1440px 1734.25px), c4o's shipped result measured fresh here as the BEFORE column,
    and this task's AFTER column. State plainly whether the 375px height came back at or below
    the original 8423px, and record the actual number either way. Do not round, do not
    approximate, and do not quote a number you did not measure.
  - the full 16-harness table with exact pass counts and the coverage percentage from Task 2,
  - an explicit, prominent flag on the colour-caveat design decision: state that `COLOUR_CAVEAT`
    became fully orphaned by this removal, that it was rehomed into the lightbox note by
    composition rather than deleted or left dangling, give the reasoning, and mark it as awaiting
    developer sign-off with the two-line reversal path spelled out. This is the one open design
    question this task was asked to resolve thoughtfully — it must not read as a settled
    incidental.
  - a note that `_render_gallery_no_preview_apparatus_even_with_panel_file` was deliberately KEPT
    rather than replaced, contrary to a literal reading of the task spec's list of five, with the
    reason (its subject is the `/preview.png` route retirement, all its assertions still pass, and
    deleting it would silently drop c4o's route-retirement coverage).
  - a note that a SIXTH check beyond the spec's five had to be retired
    (`_recent_renders_malformed_filename_caption_fallback`), why it was unavoidable, and where its
    residual coverage already lives.
  - a zero-diff confirmation via `git diff <BASE_SHA> --stat`: the diff must be exactly
    `companion/pages/history_page.py`, `companion/test_view_pages.py`,
    `companion/static/style.css` and this task's own planning artifacts — with explicit
    confirmation that `companion/app.py`, `companion/static/panel-lookup.js`,
    `companion/pages/airlines_page.py`, `companion/layout.py`, `companion/test_companion_app.py`,
    `companion/test_status_pages.py` and everything under `server/` carry zero diff.

No code commit for this task — per this chain's own convention, planning artifacts are left for
the orchestrator's final commit.
  </action>

  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && test -f .planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md && grep -q 'Browser Measurement' .planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md && grep -q 'scrollHeight' .planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md && grep -qi 'caveat' .planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md && echo 'OK summary present with measurement table and caveat decision'</automated>
    <automated>cd "$(git rev-parse --show-toplevel)" && git diff origin/main --stat -- companion/app.py companion/static/panel-lookup.js companion/pages/airlines_page.py companion/layout.py server/ | grep -q . && { echo 'FAIL: out-of-scope file changed'; exit 1; } || echo 'OK out-of-scope files carry zero diff vs origin/main'</automated>
  </verify>

  <done>
A real browser confirmed, against a copy of production-shaped state at 1440px and 375px: zero
retired-grid-container elements on `/history` in the AFTER tree (and non-zero in the BEFORE tree,
so the assertion is not vacuous); the 375px `scrollHeight` recorded as an actual measured number
and compared against both c4o's 13450px and the true original 8423px; at least one View-panel
trigger carrying a `title` equal to its `aria-label` in the live DOM; and a trigger click still
opening the lightbox with a loaded image, the correct caption and the caveat-bearing note.
SUMMARY.md exists with the three-column Browser Measurement table, the 16-harness pass counts and
coverage, the prominently-flagged colour-caveat decision awaiting developer sign-off, both
test-scope deviations explained, and a zero-diff confirmation on every out-of-scope file.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → companion HTTP service | Session-gated; every `/history` response is server-rendered from local state, no user-supplied input reaches this page's markup |
| gallery directory → `/gallery/{name}.png` | Filenames come from `os.scandir()` and are matched exactly before serving; path traversal is already rejected and pinned by `companion/test_companion_app.py`. Untouched by this task |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-etm-01 | Information disclosure | The new `title` attribute on the View-panel trigger | low | mitigate | The value is the same fixed module constant already used for `aria-label`, escaped through the same single `escape_html()` call and interpolated into both slots from one local — no row data, no filename and no timestamp reaches the tooltip |
| T-etm-02 | Tampering | Deleting a shared symbol by mistake (`_GALLERY_ROUTE_PREFIX`, `gallery_entries_list`) | medium | mitigate | Both were grep-verified as shared during planning and are named explicitly in `must_haves`; the Task 1 runtime gate asserts `_GALLERY_ROUTE_PREFIX` still exists and that a trigger button still renders with a well-formed `data-view-panel-src` |
| T-etm-03 | Denial of service | Removing the section could accidentally remove the lookup, leaving `/history` trigger-less | medium | mitigate | New check 1 asserts the per-row mechanism is intact in the SAME render that asserts the section is absent, and Task 3 confirms a real click-to-open in a browser |
| T-etm-04 | Repudiation | A silently-dropped safety caveat | low | mitigate | `COLOUR_CAVEAT` is rehomed by composition rather than deleted, pinned by new check 4, and flagged in SUMMARY.md for developer sign-off with a stated reversal path |
| T-etm-SC | Tampering | npm/pip/cargo installs | n/a | accept | This task installs nothing — no package-manager step exists in any of its three tasks, so no legitimacy gate applies |
</threat_model>

<verification>
- `server/.venv/bin/ruff check .` clean (blocking CI step; the narrowed import is the specific risk).
- `scripts/run-all-tests.sh`: all 16 harnesses green, `companion/test_view_pages.py` at 49/49,
  every other harness at its prior count, coverage above `fail_under = 83`.
- `companion/pages/airlines_page.py`, `companion/app.py`, `companion/static/panel-lookup.js`,
  `companion/layout.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` and
  all of `server/` carry zero diff against `origin/main` from this task.
- Repo-wide sweep for the seven deleted Python symbols and the two retired CSS class names returns
  hits only inside this plan and its SUMMARY.
- Real browser at 1440px and 375px: zero retired-grid-container elements, a non-vacuous BEFORE
  comparison, a live `title == aria-label` reading, and a working trigger → lightbox → loaded
  image → correct caption → caveat-bearing note round trip.
</verification>

<success_criteria>
- History's top-of-page render-gallery `<section>` does not exist in any form; `render()` returns
  header + body + lightbox only.
- The per-row "View panel near this time" lightbox is the sole way to see a rendered panel on
  `/history`, is functionally unchanged, and its trigger now shows a native tooltip equal to its
  accessible name.
- Seven dead Python symbols and three orphaned CSS rules are gone; every shared symbol survives;
  no comment anywhere still names a deleted rule or a deleted symbol.
- The orphaned colour caveat is rehomed into the lightbox note by composition, with the reasoning
  documented and flagged for developer sign-off — neither silently deleted nor left dangling.
- `companion/test_view_pages.py` at 49/49 with the section's absence, the per-row mechanism's
  survival, the tooltip contract and the caveat's new home each pinned.
- All 16 harnesses green with exact counts recorded; the 375px `scrollHeight` measured and
  compared against both c4o's 13450px and the true original 8423px.
- Two commits scoped `quick-260903-etm` on `claude/history-preview-gallery-32b974`, no new branch.
</success_criteria>

<output>
Create `.planning/quick/260903-etm-history-render-gallery-remove-the-top-of/260903-etm-SUMMARY.md` when done
</output>