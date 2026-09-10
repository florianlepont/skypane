# Phase 18: Companion audit & UX refactor - Context

**Gathered:** 2026-09-10
**Status:** Shipped on branch `claude/web-companion-audit-ux-refactor-bqx7si` (see 18-01-SUMMARY.md)

**Process note:** the GSD entry points (`/gsd-quick`, `/gsd-execute-phase`) were not available in the session that did this work; this folder was written by hand to the same shape so the planning record stays in sync with the code.

<domain>
## Phase Boundary

A full audit of the companion web app, and the UX/IA refactor it motivated, driven by one new requirement: **a second household member with basic computer skills will use the companion** and must be able to do so without an explanation. That splits every function into "everyday" (is the frame alive, what is it showing, switch it off, change the look) and "advanced" (setup, diagnostics, registries, debugging), and the navigation has to make that split visible.

**In scope:** the audit ledger (18-AUDIT.md); the navigation regrouping; a new Home page of widgets; splitting Settings into Display (everyday) and Device (advanced); one-tap quick actions; the per-screen-type seam so future screen kinds can carry their own settings; the display and copy defects the audit found that were cheap and safe to fix in the same pass.

**Out of scope, deliberately:** French localisation (S-01), field-level validation errors (A-25), the Health page's auto-reload and sparkline scaling (A-20, A-22), auth hardening (A-32/A-33), per-screen on-disk config (the rest of A-40). Each is recorded with its evidence in 18-AUDIT.md so it can be promoted on its own.
</domain>

<decisions>
## Implementation Decisions

- **D-01: Two nav groups, one declaration.** `layout.NAV_GROUPS` is the only place the tab set lives; `NAV_TABS` is derived from it so every existing consumer (the login `?next=` allowlist, `_referring_tab()`, the page-title guard, both nav renderers) keeps working. The everyday group is unlabelled; the second carries the "Advanced" label so the split reads at a glance.
- **D-02: Home is a page of widgets, not a dashboard of charts.** Three plain-language status tiles (Frame / Battery / Flight data), three quick-action cards, the current panel image, five recent flights. Every widget reads one slice of `ctx`; Home imports no sibling page module (the `companion/pages` boundary holds).
- **D-03: Quick actions are idempotent state writes, not toggles.** `POST /quick/display` and `/quick/quiet-hours` carry `state=on|off` — a double-tap on a slow connection must not flip the screen twice. Every other config value is carried forward via `save_device_config()`'s `None`-means-unchanged contract.
- **D-04: One settings form, two scopes.** `config_page.render(ctx, scope=...)` composes the Display or Device page; `POST /settings` stays the single write route. A hidden `scope` field tells `handle_post()` which groups were on the page so an absent checkbox from an *unrendered* group means "leave unchanged", never "switch off" — the one place the split could have silently broken a saved value. `render(ctx)` with no scope still renders the legacy full page so the existing harness pins stay meaningful.
- **D-05: Screen types are a registry, not a hard-coded list.** `companion/screens.py` declares, per screen type, which settings groups belong to Display and which to Device, plus whether the screen has colour rules and a manual poll. Single screen today; the on-disk config is still one document, and that is the documented next step (A-40).
- **D-06: Local time everywhere it is visible.** `layout.local_clock_text()` renders Europe/Paris, with the day when not today; the ISO string stays in `title`. The bare "UTC" suffix is retired.
- **D-07: Old routes redirect, they do not 404.** `/settings` → `/display`, `/history` → `/flights`, `/preview` → `/flights` — fixed literals, unlike the deliberate 404 on `/config` (06.6.4.1 D-26), because these were live bookmarks for a year of use.
- **D-08: Fix now only what is cheap, safe and visible.** The audit's remaining findings are tracked, not half-fixed.
</decisions>

<specifics>
## Specific Ideas

- The "Advanced" label uses the existing 12px uppercase label voice and a hairline top; no new tokens.
- Quick-action cards signal "on" with the status-ok colour on their left edge — never the accent, which stays reserved.
- Home's battery percentage is an explicit estimate (≈, linear 3.3–4.2 V) until the Phase 5 discharge run yields a real curve.
</specifics>

<deferred>
## Deferred Ideas

Everything in 18-AUDIT.md's Open and Suggestions sections, S-01 (French localisation) and A-40's remaining steps (per-screen config, a screen selector) first among them.
</deferred>
