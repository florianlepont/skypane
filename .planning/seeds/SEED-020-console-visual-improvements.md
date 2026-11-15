---
id: SEED-020
status: dormant
planted: 2026-11-15
planted_during: "v1.2, owner's roadmap discussion of 2026-11-15"
trigger_when: "Milestone v1.3, set by the owner on 2026-11-15 when v1.3 and v1.4 were split; it covers the screens added by photo mode; surface it at /gsd-new-milestone."
target_milestone: v1.3
scope: medium
---

# SEED-020: Console improvements (visual)

## Why This Matters

The owner sees "quite a few visual improvements" to make on the console. The
list is not written down yet. The companion was overhauled in Phase 61 (rounds
of owner validation, follow-up plans 61-100 to 61-129 in the validation
ledger) and its design system is kept in the `sketch-findings-skypane` skill, so
this seed is about the next layer of polish, not a redesign.

## When to Surface

**Trigger:** milestone v1.3. It fits next to the getting-started wizard and the
photo mode screens (SEED-013), which add new pages that must follow the same
visual rules.

## Scope Estimate

**Medium; the real size depends on the list.** First step at milestone start:
the owner walks the deployed console and lists what to change, with screenshots,
as was done for Phase 61. Then sort by value.

Points to settle:

- **Which console:** the administrator console, the owner's companion pages, or
  both (the owner wrote "console"; confirm).
- **Source of the list:** the owner's walkthrough, plus the follow-up plans of
  Phase 61 that were not done (see the validation ledger in
  `.planning/workstreams/v1-2/phases/61-*/`).
- **Rules:** keep the design system (tokens, contrast, spacing, density); any new
  pattern is added to it. Both languages (English and French) and phone width
  keep working. Mockups before code, as for the active-mode card.
- **Tests:** behaviour-over-source rule, browser tests for what changes
  visually, accessibility checks kept.

## Breadcrumbs

- `companion/` (pages, `companion/i18n_fr/`) and the `sketch-findings-skypane` skill (design system)
- `.planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/` (validation ledger and follow-up plans)
- `.planning/seeds/SEED-010-companion-interface-polish.md` (earlier polish, fulfilled)
- `.planning/seeds/SEED-013-photo-display-mode.md` (new screens that must match)

## Notes

Phase 67 (project and code optimisation, v1.2) must not change how the console
looks; visual work waits for v1.3.

## Items noted during the Phase 64 walk-through

- 2026-11-15, owner, with a screenshot: on the Fleet page of a frame, a retired
  frame ("Le Petit Cadre", "Anciennement <owner e-mail>") is listed although the
  owner is on the view of another frame. It is unclear which frame the page is
  about when other frames are listed on it. To settle with the list above.
- 2026-11-15, owner, with a screenshot: on the Fleet page the row menu of the last
  frame of the "Autres cadres" list is clipped at the bottom, so its actions (for
  example Re-activate) cannot be reached. Also recorded as a gap of the Phase 64
  walk-through.
- 2026-11-15, owner, with a screenshot: on the Flight history page, when the browser is narrowed, the search field drops under the title at some width, which looks odd.
- 2026-11-15, owner: on the theme page, switching tab reloads all the frame previews, even those of the other tab. The preview images carry a 5-minute cache, so check whether each tab change is a full navigation or whether the preview URLs change at each render.
- 2026-11-15, owner: "Back to Fleet" from a frame's page lands on the first frame of the list, not on the frame that was being viewed. The selected frame should be carried back.
