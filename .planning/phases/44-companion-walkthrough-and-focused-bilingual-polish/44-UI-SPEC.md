---
phase: 44
slug: companion-walkthrough-and-focused-bilingual-polish
status: draft
shadcn_initialized: false
preset: none
created: 2026-09-30
---

# Phase 44 — UI Design Contract

> Visual and interaction contract for the focused bilingual companion polish. This phase proves findings before changing UI; it preserves the established companion system rather than redesigning it.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | None; preserve the hand-written, build-step-free stylesheet |
| Preset | Not applicable |
| Component library | None; use the existing shared shell, page modules, and native HTML controls |
| Icon library | Existing inline SVG icon definitions in `companion/ui_base.py`; do not add an icon package |
| Font | System UI sans for content and controls; Iowan Old Style / Charter-led system serif stack for heading roles only |

The companion is a server-rendered stdlib application, not a React, Next.js, or Vite project. The shadcn initialization gate is therefore not applicable. Do not introduce a framework, build step, external asset, or duplicate client state.

### Scope and Finding Gate

1. Complete the recorded walkthrough before proposing product changes. Cover Home, Display, Flights, Airlines, Health, Device, and Update in English and French at 1280 px, 390 px, and 360 px.
2. Record every observation in `44-WALKTHROUGH.md` with fixture, route, language, viewport, user action, observable evidence, reproducible trigger, user impact, and exactly one disposition: `keep`, `fix now`, or `defer`.
3. A `fix now` finding must block task completion, misrepresent current frame state, obscure warning versus intentional sleep, impair setting feedback, break readable layout, or make touch or keyboard operation unreliable. Keep or defer all other observations.
4. Map every accepted finding to one existing owner: route table, typed page context, page renderer, shared shell/navigation, tokenized stylesheet, named page script, or stable i18n message ID and French catalogue. One finding must not create a new global behaviour bundle or a companion rewrite.
5. On Home, the current frame-state summary is the primary visual anchor; all supporting data must preserve its immediate scanability.
5. Keep battery-policy presentation out of this phase. Health and Device language must remain compatible with the pending Phase 46 operating decision.

---

## Spacing Scale

Use the existing token scale. Do not add a one-off spacing value for a walkthrough fix.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Icon gaps, compact inline separation, active-tab pill margins |
| `--space-sm` | 8px | Label-to-control and compact component spacing |
| `--space-md` | 16px | Default component padding, form groups, and control clusters |
| `--space-lg` | 24px | Card padding and adjacent section spacing |
| `--space-xl` | 32px | Major layout gaps and mobile shell rhythm |
| `--space-2xl` | 48px | Desktop content inset and major section breaks |
| `--space-3xl` | 64px | Desktop page-level horizontal inset |

Exceptions: existing compact control geometry is retained. Native inputs and the navigation toggle remain at least 44 px in both dimensions. The mobile tab-bar destination cells remain 56 px tall. Existing 30 px desktop buttons and 36 px narrow-mobile buttons may remain only where the established touch-target register and real hit-target coverage already prove them; a new or changed icon-only control must provide a real 44 by 44 px hit area.

---

## Typography

Preserve the exact four-size, two-weight system. New page copy must use an existing role; do not introduce a fifth type size or third weight.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Label | 14px | 400 | Existing label rhythm; uppercase label variants retain their existing tracking |
| Body and controls | 16px | 400 | 1.5 |
| Section heading | 22px | 400 | 1.25 |
| Page title | 32px | 600 | 1.15 |

The two permitted weights are 400 and 600. Use the serif family only for page titles, section headings, and semantic `legend` elements that retain the established heading role. Keep navigation, controls, tables, body copy, status text, and mono identifiers on the system UI or mono family already assigned to them. Preserve the existing 16 px sans-semibold nested-card-title exception and compact empty-state hierarchy where those components already use it.

---

## Color

The 60/30/10 ratio describes visual hierarchy, not a mandate to repaint individual pages. Retain the existing light and dark tokens and their contrast/separation checks.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | Light `--color-canvas` `#F7F4EF`; dark `#0C0F14` | Page background and the broadest visual field |
| Secondary surface (30%) | Light `--color-secondary` `#EEE8DE`; dark `#1C222D` | Sidebar, mobile navigation, elevated navigation surfaces, and quiet control surfaces |
| Accent (10%) | Light `--color-accent` `#B13F16`; dark `#FF8A5C` | Primary submit actions, links, keyboard focus outline, active navigation indicator, selected choice, and existing neutral wayfinding treatment |
| Destructive / error | Light `--color-status-error` `#BE123C`; dark `#FB7185` | Error text, destructive action treatment, and error feedback only |

Cards and standard controls use the existing `--color-dominant` surface (`#FFFFFF` light / `#151922` dark), structural `--color-border`, and hairline-at-rest treatment. Do not restore a resting card shadow. Keep status semantic: green signals healthy state, amber signals warning or attention, and crimson/rose signals error or destructive consequence. A healthy scheduled sleep must never be styled or described as an error.

Accent is reserved for primary submit actions, links, the 2 px visible keyboard-focus outline, active sidebar/dropdown/tab-bar navigation, selected runway/theme choices, native radio and checkbox selection, the existing neutral wayfinding mark, and already-established switch/arrival state uses. Do not use accent as a generic card border, a second error signal, or decoration for every interactive element.

---

## Responsive and Interaction Contract

### Layout

- 360 px is the minimum supported viewport. 390 px is the reference phone width. 1280 px is the walkthrough desktop width. Retain existing 320 px regression assertions when they pass, but do not contort a confirmed 360 px design solely to solve a 320 px-only cosmetic issue.
- At widths below 960 px, use the established mobile shell and fixed bottom tab bar. Reserve the tab bar's height plus safe-area inset in `.has-tab-bar .page-content`; no changed card, form action, or feedback message may be hidden beneath it.
- At 960 px and above, retain the sidebar/grid shell, readable bounded content width, and desktop dirty-save bar placement. Do not duplicate navigation landmarks or expose both desktop and mobile navigation to the tab sequence or accessibility tree at the same viewport.
- Keep meaningful content in normal document flow. Mobile navigation panels must push content rather than overlap it. Preserve responsive table/card transformations already owned by the relevant route.
- Test every changed route in English and French at 360 px and 390 px for overflow, clipping, unreachable content, truncation that changes meaning, and controls obscured by the tab bar. Test the desktop representation at 1280 px.

### Semantic Controls and Keyboard Operation

- Use native `<a>` for navigation, `<button>` for actions, `<form>` plus native inputs/selects for settings, `<summary>` for disclosure, and `role="switch"` only where the existing switch pattern is already required. Do not add click handlers to non-interactive containers.
- Preserve a visible `:focus-visible` outline of `2px solid var(--color-accent)` with a `2px` offset for links, buttons, inputs, selects, and summaries. A local visual change must not suppress focus without an equally visible replacement.
- Every changed interaction must work in logical Tab order, operate with Enter or Space where native semantics require it, expose its actual state through native state or the existing ARIA state, and leave focus in a useful place after its action completes.
- Retain no-JavaScript server fallbacks. A local enhancement belongs in the page's existing named static script only when its base control remains operable through the served document and native POST flow.
- Keep touch and pointer feedback separate from selection and status semantics. Hover styling may enrich desktop use but must never be the only way to discover an action or status.

### Feedback and State Clarity

- Keep the shared flash slot directly after the page header for success and failure feedback. Successful changes must use the existing `common.saved` message contract (`Saved — %s` / `Enregistré — %s`) or a route-specific existing success message with the same outcome-first meaning.
- Settings retain the existing primary CTA pair: `Save settings` / `Enregistrer les réglages`. The dirty bar may describe real unsaved edits and must remain a native submit path; it must not claim unsaved changes before an edit exists.
- A rejected save must preserve submitted data where the current flow does, identify the field-level problem beside the affected field, and present the established failure flash rather than silently discarding the error. Do not add an optimistic success state before storage and any documented immediate-sync result are known.
- Distinguish a current warning, an unavailable reading, and an intentional display-off or scheduled-sleep condition through their existing status text, icon, and semantic state. Do not collapse those states into one generic alert.

---

## Copywriting Contract

All user-facing additions must start as stable English `i18n.msg()` IDs and have a matching French catalogue entry with placeholder parity. Do not put untranslated English literals in page markup, script messages, ARIA labels, button labels, tooltips, empty states, errors, or confirmation prompts.

| Element | Copy contract |
|---------|---------------|
| Primary settings CTA | `Save settings` / `Enregistrer les réglages`; retain native submit semantics and the existing dirty-save feedback sequence |
| Existing generic success | `Saved — %s` / `Enregistré — %s`; the substitution names the completed change and never claims a frame result that is still pending |
| Empty-state heading | Use the owning route's existing resource-specific empty-state message. A new state names the missing resource plainly and does not imply a fault when no data is expected. |
| Empty-state body | State the next useful action only when one exists: add, connect, wait, or return to the relevant route. Do not invent a CTA for an unavailable capability. |
| Error state | State what failed, preserve the distinction between validation, unavailable data, and failed persistence, then give the immediate recovery action such as correcting the highlighted field or trying again. Keep language factual and concise. |
| Destructive confirmation | Retain the owning route's existing confirmation pattern. Name the irreversible action and the affected item; the confirm label uses the action verb, never a vague `OK`. |

For bilingual parity, English and French must communicate the same action, status, severity, and next step. The translated string may use different word order or grammatical gender, but it may not omit a warning, confirmation consequence, accessible name, or placeholder present in the paired language.

---

## Verification Evidence Contract

| Requirement | Required evidence |
|-------------|-------------------|
| CMP-01 | A recorded matrix for seven authenticated routes, both languages, and 1280/390/360 px viewports using the seeded production-shaped fixtures and real login. |
| CMP-02 | `44-WALKTHROUGH.md` records each observation's trigger, impact, evidence, and keep/fix-now/defer decision before product edits. |
| CMP-03 | Every changed flow has targeted delivered HTML/CSS/JS or browser coverage for EN/FR meaning, responsive layout, visible keyboard focus, semantic controls, and successful/rejected feedback where it posts. |
| CMP-04 | Each accepted finding is linked to its smallest existing owner and protected by the closest route, page, shell, stylesheet, i18n, or browser regression test. |

Use the existing isolated subprocess/browser fixtures and real rendered documents. Do not substitute planning-text checks, source-only assertions, mock DOM snapshots, unreviewed screenshots, or a new browser harness for behavioural evidence. Re-run applicable route-table, page-context, stylesheet-structure, i18n, and affected page regressions after the focused fixes.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | None | Not applicable: shadcn is not initialized and this is not a React-family project |
| Third-party registries | None | No third-party UI code may be added in this phase |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
