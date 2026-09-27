# Phase 40: Companion architecture — routes, pages, templates, i18n keys - Context

**Gathered:** 2026-09-27
**Status:** Ready for planning
**Source:** Orchestrator brief (audit remediation) + developer answers (AskUserQuestion, 2026-09-27)

<domain>
## Phase Boundary

Structural refactor of `companion/` that remediates CMP-01..CMP-09 of the
2026-09-23 code audit, plus three developer-confirmed open requirements
(CFG-39, CFG-52 artwork drop zone, CFG-34 (a)-(c)). Behaviour and rendered
output of every page must not change, except where CFG-34 deliberately turns
three static ages into live `<time data-relative>` ages.

The audit's line numbers and sizes are stale: Phases 32–38 already shrank
`app.py` (2849 lines), `layout.py` (2597) and moved `config_page.py` to
`companion/pages/config_page.py` (3384). Research must re-measure.

</domain>

<decisions>
## Implementation Decisions

### CMP-01 — Route table
- Every route declared once in a table of `(method, matcher, handler, auth_required)`; `do_GET`/`do_POST` dispatch through it. The hand-repeated `require_session()` calls go away.
- A test enumerates the table and proves every route not explicitly public answers without a session with the same unauthenticated response as today (redirect to login / 401 / 403 as currently served).
- Public routes are an explicit, short allowlist (login, static assets, health probe — whatever is public today; nothing new becomes public).

### CMP-02 — Static allowlist
- One `{route: path}` mapping replaces the per-file route constants, `_serve_*` functions and branches. Must keep Phase 38's in-memory static cache, ETags and conditional GET, content types and cache headers byte-for-byte.

### CMP-03 — File split
- `pages/config_page.py` split by settings group; `layout.py` split by responsibility. No companion file over ~1500 lines (success criterion 2).

### CMP-04 — Typed per-page context
- Replace the `page_context()` god dict with typed per-page context (dataclasses or equivalent). MUST preserve Phase 38's laziness (`_LazyContext`: nothing computed that a page does not read), one SQLite connection per request, conditional-GET freshness tokens, and the per-page script sets guarded by `test_page_scripts.py`.

### CMP-05 — Named templates
- `page_shell` stops using positional `%s`; named placeholders (e.g. `string.Template` or `str.format_map` with a named dict — stdlib only). Output byte-identical.

### CMP-06 — Function size
- No function over ~80 code lines (success criterion 2); `handle_post` split per settings group. A guard test measures it.

### CMP-07 — Shared helpers
- `read_form` / `_read_upload_body` share one body-drain helper; theme/lang cookies built by one helper.

### CMP-08 — CSS
- No duplicated CSS selector; no hard-coded colour outside the token definitions (success criterion 3). Computed styles unchanged — prove it in a browser (both themes).

### CMP-09 — i18n stable IDs
- Translations keyed by stable message IDs, so rewording the English cannot silently drop the French (success criterion 4). A test proves every ID has both languages.

### CFG-39 — Battery chart on draw.py (developer chose: MIGRATE)
- Move the battery chart onto `companion/draw.py` (the shared SVG drawing module). Rendered SVG must stay equivalent (prove with a before/after comparison of the emitted SVG); the chart contract checks already applied to the other drawings then apply to it. Tick CFG-39 only if every clause in its REQUIREMENTS row holds.

### CFG-52 — Artwork drop zone keyboard (developer chose: MEASURE)
- Measure keyboard-only operability of the artwork drop zone with the existing `_operate_with_keyboard()` browser instrument (no pointer event). Fix if it fails. Tick CFG-52 if all six clauses then hold.

### CFG-34 (a)-(c) — Live ages (developer chose: ALL THREE)
- Flights desktop "When" cell, Calendar "refreshed Xm ago", and Health's unresolved-prefix cells become `<time data-relative>` via `layout.relative_time_html()` and the existing `relative-time.js` ticker. The fourth (battery-trend) stays static and enumerated as a deliberate exception. These are the ONLY intended rendered-output changes in the phase.

### Out of scope
- CFG-50 (Display page height) — developer confirmed out of scope.

### Testing rules (Phases 32/33 conventions)
- pytest (+ xdist), browser tests via pytest-playwright; behaviour-over-source rule (`companion/test_suite_guards.py`): tests assert served HTML/CSS/JS or a browser, never source text or `.planning/`. Structural guards (function length, file length, route table coverage, i18n completeness) assert through imports/introspection of runtime objects, not by grepping source text — check `test_suite_guards.py` for what is allowed.
- Rendered-output equality: capture served HTML for every page (both languages, both themes where relevant) before the refactor and assert equality after, where useful.
- Comment rules: English, no plan/phase/ticket IDs in comments (`scripts/check_comment_history.py check`).
- Coverage gate at the measured floor must not drop.

### Coordination
- This session owns `companion/`. Phase 39 (parallel session) owns `server/`, `stub-server/`, new shared modules, and may make small import switches in companion (state_store, shared battery/quiet-hours module). Merge `origin/main` often; keep both sides' intent on conflict.
- Base: `claude/plan-phase-38` content (PR #150 not yet merged into main at start).

### Claude's Discretion
- Exact module names for the split, the typed-context shape, the template mechanism, message ID naming scheme, plan/wave breakdown.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md` — CMP-01..CMP-09 rows, decisions D-A1..D-A6
- `.planning/REQUIREMENTS.md` — CMP-*, CFG-34, CFG-39, CFG-52 rows (and their traceability notes)
- `.planning/ROADMAP.md` — Phase 40 success criteria
- `.planning/phases/38-*/` — Phase 38 summaries (lazy context, per-page scripts, static cache, freshness tokens)
- `.planning/phases/32-*/`, `.planning/phases/33-*/` — pytest/browser test conventions
- `.claude/skills/sketch-findings-skypane/SKILL.md` — design tokens (CMP-08)
- `.claude/CLAUDE.md` — conventions

</canonical_refs>

<specifics>
## Specific Ideas

- Route-coverage test: iterate the route table, for each non-public route issue a request with no cookie and assert the unauthenticated response.
- Snapshot served HTML before refactor waves → equality test after.

</specifics>

<deferred>
## Deferred Ideas

- CFG-50 Display page height.

</deferred>

---

*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Context gathered: 2026-09-27 from orchestrator brief + developer answers*
