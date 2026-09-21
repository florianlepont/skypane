# Phase 29: Companion review feedback round 3 — Context

**Gathered:** 2026-09-21, across this session's own developer tour (six live cases, one per screenshot) and the AskUserQuestion round that split them into Lot A / Phase 29 / Phase 30.
**Status:** Ready for planning

<domain>
## Phase Boundary

The developer toured the deployed companion on 2026-09-21 and reported eight cases in one sitting. Five yielded one-line fixes and already shipped ahead of this phase, as quick tasks 260921-n2n ("Lot A") and 260921-p2w (a same-day follow-up: Lot A's Safari fix was incomplete, root-caused to a hyphen in the filter-input `id`, now fixed and developer-confirmed on real Safari). The first case (the Display "Aspect" section) is large enough to be its own phase and is Phase 30. The last (a real domain name for the companion) is an operations task with no code, recorded in `.planning/STATE.md`'s Roadmap Evolution, not here.

This phase is the remaining six cases, plus three leftovers of the measured 2026-09-17 audit (`.planning/ui-reviews/2026-09-17-companion-ui-ux-audit.md`) that the developer selected to fold in because they touch the same pages this phase already opens. The audit's fourth open item (44px tap targets) was explicitly NOT selected and stays in that audit's own backlog — do not add it to this phase's scope.

</domain>

<decisions>
## Implementation Decisions

### Editorial floor (CFG-79)
- One sentence under a card title, at most ~12 words, no mechanism clause, no reason clause.
- "Applies at the next wake" is said in exactly one place per page (the Frame strip / save bar), never repeated under each card.
- Anything longer moves into the existing "How it works" `<details>` disclosure, or is deleted outright.
- Scope is site-wide **except** Display's Aspect section — Phase 30 owns that card's copy, since it is being rebuilt from scratch there.
- Enforced by a harness check measuring RENDERED caption length on every authenticated route, in both languages, mutation-proven against a deliberately long caption.
- The runway card's stale schematic-map clause is already cut in Lot A (quick task 260921-n2n) — this requirement's own check must not re-fail on that already-fixed text; it asserts the FLOOR going forward, not a diff against Lot A.

### Quiet hours as one object (CFG-80)
- Start and End render on one line as one visual unit with the dial, not as two separate stacked field groups.
- The normalised HH:MM twin beside each native `<input type="time">` (`_normalised_time_html()`, B14/22-10) is hidden at load when the native field already renders unambiguous 24h — kept alive as the scripts-blocked / forced-12h-browser fallback. B14's own ground for existing at all is unchanged; only its default visibility changes.
- Presets become a segmented control with short labels ("Nuit", "Journée") — the hours are already spoken by the dial's own caption, so the button labels don't need to repeat them.
- The uncommitted CSS fix sitting in the MAIN CHECKOUT (not this worktree) from the 2026-09-17 audit session — `_normalised_time_html()`'s sibling gaining a `field=` parameter so it can hide conditionally — is now MOOT: Phase 28 already fixed the dial's minute-vs-HHMM bug a different way (CFG-73, 28-03), and this requirement's own "hide the twin" mechanism is a fresh, independent implementation. Do NOT attempt to merge or replay that uncommitted diff; it predates Phase 28 and would conflict with CFG-73's shipped fix.

### The illustration dialog owns its own actions (CFG-81)
- Replace picture (and Delete, for a manually resolved entry) render in the dialog on EVERY open, unconditionally — the page-wide `edit_mode` query param and the "Modifier les images" / "Change pictures" toggle are removed entirely.
- "Send a picture" for an airline with no artwork yet is unchanged — it was never gated by `edit_mode`.
- The resolve-context block's two bugs (empty-instead-of-hidden, caption-as-callsign) are already fixed in Lot A — this requirement is the SCOPE change (always-rendered actions), not a repeat of those two bug fixes.
- Removing `edit_mode` also removes the reason the resolve-context block was ever reachable from a page-wide toggle — no separate change needed there beyond what Lot A already shipped.

### Compagnies gallery-first (CFG-82)
- Filter + known-airline gallery render directly under the page title.
- Unidentified prefixes and any remaining editing affordance move into a clearly announced secondary section below the gallery.
- The 2026-09-17 audit's own fix for the truncated "Compagnies" tab label — `.tab-bar__pill`'s horizontal margin from `var(--space-sm)` to `calc(var(--space-xs) / 2)` — sits uncommitted in the MAIN CHECKOUT's `style.css`, NOT in this worktree. **Do not attempt to pull or merge that diff.** Re-derive the same fix fresh in this worktree's `companion/static/style.css` (the rule and its surrounding comment are described in the 2026-09-17 audit file and in this project's design-system skill's "Navigation" entry) and verify it against Phase 28's current tab-bar CSS, which has moved since that diff was written.

### Vols paginated (CFG-83)
- Show 10–15 flights, then a real "Afficher plus" / "Show more" action that works with scripts blocked — either a server-side `?limit=` query param re-render, or a native `<details>`-style progressive reveal. Planner's choice; record the reasoning in the plan.
- The filter bar stays immediately visible above the first card at all times — pagination must not push it below the fold or hide it while collapsed.
- The summary card's grid stays stable on a 390px phone — the 2026-09-17 audit's P1 finding was the timestamp and callsign fighting for one line at this width; the fix must not regress once pagination is added.
- No existing pagination pattern exists anywhere in this codebase (verified: `grep -ri paginat` across `companion/` returns nothing) — this is genuinely new UI, closer to research territory than the other five requirements.

### État's title shortened (CFG-84)
- The battery-trend `<h2>` reads "Batterie · 3 mois" / "Battery · 3 months"; "moyenne quotidienne" / "daily average" moves to the card's existing caption, not the heading.

### Claude's Discretion
- CFG-83's exact reveal mechanism (query-param re-render vs. `<details>`) — planner picks based on what's cheapest against the existing `history_page.py` structure and the no-JS floor this app holds everywhere else.
- Whether CFG-82's secondary section for unidentified prefixes reuses an existing disclosure pattern (`<details>`) or a plain lower page-section — planner's call, consistent with the rest of the page.
- Ordering of the six plans / waves — planner's call based on real file-ownership overlap (several of these touch `companion/pages/history_page.py`, `companion/pages/airlines_page.py`, and `companion/static/style.css` and cannot safely run in parallel against the same file).

</decisions>

<specifics>
## Specific Ideas

The developer's own words (French, verbatim), each already investigated live against the code before this phase was scoped — full findings are in the ROADMAP.md Phase 29 entry itself, not repeated here:

1. *"il y a trop de texte descriptif qui servent à rien sur l'ensemble du site"* — CFG-79.
2. *"pas très joli ce composant"* (quiet-hours screenshot) — CFG-80.
3. *"ce bouton est pas au bon endroit... quand on est dans la liste d'avion on ne le voit plus"* (Modifier les images) — CFG-81, CFG-82.
4. *"une bonne part de ces infos ne servent à rien. Le bouton « remplacer l'image » pourrait être ici"* (illustration lightbox) — CFG-81.

The three folded-in 2026-09-17 audit leftovers (Vols pagination, Compagnies gallery order + tab label, État's title) are CFG-82/83/84 above.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning.**

### Prior phase precedent for this phase's discipline
- `.planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/` — established the "review-feedback discipline" standing contract this phase inherits: assert relationships not endpoints, measure the resolved hit-target box in its own container, mutation-test every new check.
- `.planning/phases/28-companion-review-feedback-round-2-five-more-findings-from-th/` — CFG-73's fix is what CFG-80's quiet-hours work builds on top of; do not re-open CFG-73.

### Audits this phase draws from
- `.planning/ui-reviews/2026-09-17-companion-ui-ux-audit.md` — the measured audit; P1/P2 findings for Vols, Compagnies, État are the source of CFG-82/83/84.
- `.planning/ui-reviews/2026-09-20-mistral-companion-audit.md` — corroborates CFG-79/80/82 in passing; contributes nothing this phase doesn't already have from the 2026-09-17 audit or the developer's own tour.

### Design system
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the companion's living design-system reference. Read before any CSS/markup change; it documents the current save-bar mechanism (CFG-77/78, Phase 28), the settings-page patterns, and the no-JS control contract this phase's changes must not break.

### Already-shipped, do not re-touch
- Quick task `260921-n2n` (Lot A) and `260921-p2w` (the Safari follow-up) — both merged into `main`. Their SUMMARYs are at `.planning/quick/260921-n2n-lot-a-five-fixes-from-the-developer-tour/260921-n2n-SUMMARY.md` and `.planning/quick/260921-p2w-filter-input-dashed-ids-trigger-safari-c/260921-p2w-SUMMARY.md`. This phase's plans must not re-fix what these already fixed (the three filter-input Safari attributes and ids, the resolve-context CSS/JS bugs, the stale runway caption's schematic clause).

</canonical_refs>

<deferred>
## Deferred Ideas

- The 2026-09-17 audit's 44px tap-target item (presets, Effacer, Envoyer un test, manual refresh) — explicitly not selected by the developer for this phase. Stays in that audit's own backlog.
- The Chrome "save password?" report from the developer's tour — investigated, no confirmed mechanism found (no enclosing form, no password field on the same page), and the developer subsequently retracted it ("c'est une erreur de ma part"). No action needed.
- The maintainability debt of `config_page.py` and `style.css` (Mistral's one real contribution) — explicitly recorded as "hors de cet arriéré d'interface, à traiter par opportunité" in the distilled Mistral audit. Not this phase.

</deferred>

---

*Phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o*
*Context gathered: 2026-09-21, from this session's own investigation and AskUserQuestion round*
