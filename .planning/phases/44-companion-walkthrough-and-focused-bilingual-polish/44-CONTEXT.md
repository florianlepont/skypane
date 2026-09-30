# Phase 44: Companion Walkthrough and Focused Bilingual Polish - Context

**Gathered:** 2026-09-30
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase improves the daily companion experience through a recorded,
task-based walkthrough and the smallest set of high-value fixes it proves.
It covers the authenticated Home, Display, Flights, Airlines, Health, Device,
and Update routes in English and French, on desktop and narrow mobile layouts.
It does not redesign the companion, add new product capabilities, or change
the frame's battery policy.

</domain>

<decisions>
## Implementation Decisions

### Walkthrough Method
- **D-01:** Perform the walkthrough before selecting implementation work. Use
  real owner journeys: orient and inspect the frame, change an operating
  setting, diagnose a warning, review data, and inspect update status.
- **D-02:** Cover every authenticated route in English and French at a desktop
  viewport and at 360 px and 390 px mobile widths. Include keyboard operation
  and visible focus for every changed interaction.
- **D-03:** Record every observation with a reproducible trigger, user impact,
  evidence, and one disposition: keep, fix now, or defer.

### Product-Finish Scope
- **D-04:** Prioritize clarity of current frame state, navigation orientation,
  warning versus intentional sleep status, setting feedback, readable density,
  and responsive touch/keyboard operation.
- **D-05:** Fix only confirmed, high-value walkthrough findings. Preserve the
  established calm editorial design; do not perform a wholesale restyle,
  introduce a UI framework, or duplicate application state.
- **D-06:** Use the existing companion seams: route table, typed page context,
  page modules, shared shell, tokenized stylesheet, named page scripts, and
  stable message IDs with French translations.

### Verification Standard
- **D-07:** Every changed flow must have targeted served-HTML/CSS/JS or
  browser coverage. Re-run bilingual, responsive, keyboard, and relevant
  regression checks after the fixes.
- **D-08:** Preserve the 360 px minimum supported width while retaining
  existing 320 px assertions when they already pass.

### Claude's Discretion
- Select the exact walkthrough fixtures, finding-log structure, and narrow
  implementation order from the live companion behaviour. Defer findings that
  require a separate capability or would expand the phase beyond product
  polish.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone scope and research
- `.planning/ROADMAP.md` — Phase 44 goal, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` — CMP-01 through CMP-04 acceptance boundary.
- `.planning/seeds/SEED-010-companion-interface-polish.md` — reason for a
  fresh walkthrough instead of a preselected defect list.
- `.planning/research/SUMMARY.md` — V1.1 recommendation for task-based,
  bilingual, focused companion polish.

### Companion architecture and design system
- `.claude/CLAUDE.md` — project language, testing, and workflow conventions.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — current visual system,
  responsive contract, accessibility constraints, and previously validated UI
  patterns.
- `companion/routes.py` — canonical authenticated route table.
- `companion/page_context.py` — shared typed page context and state boundary.
- `companion/layout.py` — shared shell, navigation, and page composition.
- `companion/static/style.css` — design tokens and component styles.
- `companion/i18n.py` and `companion/i18n_fr/` — stable message IDs and French
  translation boundary.

### Regression evidence
- `companion/test_browser_ux_01.py` through `companion/test_browser_ux_04.py`
  — browser walkthrough and responsive coverage patterns.
- `companion/test_i18n.py` — bilingual parity checks.
- `companion/test_stylesheet_structure.py` and `companion/test_route_table.py`
  — stylesheet and route-table contracts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `companion/routes.py`: explicit route dispatch keeps each authenticated view
  independently discoverable and testable.
- `companion/page_context.py`: shared, lazy typed context prevents duplicate
  state reads across pages.
- `companion/layout.py`, `companion/ui_nav.py`, and `companion/ui_shell.py`:
  shared navigation and shell primitives for cross-route consistency.
- `companion/static/style.css`: tokenized colour, type, spacing, card, control,
  focus, and responsive rules; retain its visual language.
- Companion browser, i18n, route, and stylesheet harnesses: existing proof
  mechanisms for the phase's required behaviours.

### Established Patterns
- Page modules own page markup; the shared shell owns shared structure.
- Per-page scripts are served through named static routes; do not add a global
  behaviour bundle for a local interaction.
- Stable English message IDs and the French catalogue enforce bilingual parity.
- Browser tests assert delivered behaviour rather than planning text or source
  implementation details.

### Integration Points
- Add finding-log evidence under this phase directory before changes.
- Map each confirmed finding to the smallest owning page, layout, static, or
  i18n module.
- Keep the Device and Health copy compatible with the still-pending battery
  operating decision in Phase 46.

</code_context>

<specifics>
## Specific Ideas

No predefined visual defect list is accepted as scope. The walkthrough is the
source of truth for what qualifies as a V1.1 companion improvement.

</specifics>

<deferred>
## Deferred Ideas

- The pending comment-history guard work remains deferred: it is unrelated to
  companion usability and belongs to a future tooling phase.
- Battery policy and any battery-pack presentation remain Phase 46 work after
  evidence exists.

</deferred>

---

*Phase: 44-companion-walkthrough-and-focused-bilingual-polish*
*Context gathered: 2026-09-30*
