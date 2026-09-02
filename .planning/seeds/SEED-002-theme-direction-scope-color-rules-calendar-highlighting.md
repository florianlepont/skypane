---
id: SEED-002
status: dormant
planted: 2026-09-02
planted_during: "Phase 9: Diagonal band theme"
trigger_when: "When the companion web interface's config surface (Phase 6, CFG-01..12) is next revisited for a new milestone of personalization features — this seed bundles three related but separable ideas, and any one of them could trigger a look at the others. The calendar-import sub-idea additionally needs a decision on calendar source/auth (most likely a public iCal feed URL, to avoid OAuth) before it can be scoped for real."
scope: large
---

# SEED-002: Per-theme departure/arrival scope, callsign/tail-number color-override rules, and calendar-linked flight highlighting

## Why This Matters

Today the render pipeline has exactly one active theme at a time
(`device_config.py`'s `THEMES` registry, selected via CFG-01's radio-button
picker in `companion/pages/config_page.py`), and each theme already carries
*two* background colors internally — `departing_index`/`arriving_index` —
picked via `theme_background_index()`. That's a fixed departing/arriving
color pair baked into one theme, not a way to run visually distinct themes
depending on direction, and there's no way to single out an individual
flight for special treatment at all. The user wants three escalating levels
of personalization on top of that:

1. **Direction-scoped themes** — choose, per theme, whether it applies to
   departures, arrivals, or both — rather than one globally-active theme
   whose departing/arriving colors are just two indices within it.
2. **Manual highlight rules** — override the display color when a specific
   aircraft (by tail number / ICAO24) or callsign is detected, independent
   of the active theme.
3. **Calendar-linked highlighting** — import a friend's calendar (most
   likely an iCal feed) and, when their scheduled flight matches a detected
   flight, apply a distinct highlight color automatically — turning the
   frame into a "someone I care about is flying right now" signal, not just
   a generic departure board.

All three are variations on the same underlying need: let something more
specific than "the one active theme" decide the display's color for a given
render, with increasing levels of automation (config toggle → manual rule →
externally-sourced match).

## When to Surface

**Trigger:** When the companion web interface's config surface is next
extended for a personalization-focused milestone. Any one of the three
sub-ideas below could be picked up independently, but they share enough
plumbing (a rule-resolution step ahead of the existing theme-color lookup)
that it's worth reviewing all three together before committing to a design
for just one.

This seed will also surface during `/gsd-new-milestone` when the milestone
scope matches.

## Scope Estimate

**Large** — this is really three features, each big enough to be its own
phase:

1. **Direction-scoped theme applicability.** Real design question: does
   this replace the current single-active-theme model with "pick a theme
   for departures and a (possibly different) theme for arrivings," or does
   it stay additive — a theme gets tagged departures/arrivals/both, and the
   picker filters/validates accordingly? The former is a bigger structural
   change to `device_config.py`'s config schema (today `"theme"` is a single
   string) and to `theme_background_index()`'s lookup path. Needs to be
   reconciled with the *existing* departing_index/arriving_index-per-theme
   mechanism — are those retired in favor of per-direction theme selection,
   or does this stack on top (a theme's own two colors, plus which
   direction(s) it's even eligible to run in)?
2. **Callsign/tail-number color-override rules.** A new rule store (likely
   a list of `{match: callsign_or_icao24, color: ...}` entries) alongside
   the existing config registry, a companion UI section to add/edit/remove
   rules (mirroring `theme_fieldset()`'s pattern), and a hook in the render
   path that checks the current flight's normalized callsign against the
   rule list *before* falling back to the active theme's color — matching
   needs to key off `enrich.py`'s existing `normalise_callsign()` output so
   it handles the same casing/format quirks the airline-resolution path
   already does.
3. **Calendar-linked flight highlighting.** The hardest of the three:
   needs a calendar data source decision (a public iCal URL the user pastes
   in is the cheapest path — avoids building OAuth against Google/Apple
   Calendar), a periodic fetch/parse step to extract upcoming flight
   entries (event title or description would need to encode a flight
   number in some recognizable format — this needs a real convention
   decided with the user, e.g. "AF1234" in the event title), and a matching
   step against the detected flight's callsign/route. Also raises a privacy
   question worth flagging explicitly: this stores and polls a second
   person's calendar URL on the server — worth confirming that person is
   fine with it, distinct from the purely-technical scoping.

## Breadcrumbs

- `server/device_config.py` — `THEMES` registry, `normalise_theme_id()`,
  `theme_background_index()` (the existing departing_index/arriving_index
  per-theme model that sub-idea 1 would extend or restructure)
- `server/plane/enrich.py` — `normalise_callsign()` (~line 103), the
  normalized-callsign primitive sub-idea 2's matching would key off
- `server/plane/render.py` — `draw_source_fault_badge()` is the closest
  existing precedent for a conditional color/badge overlay applied on top
  of the normal theme-driven composition
- `companion/pages/config_page.py` — `theme_fieldset()` (~line 89) and the
  runway-picker fieldset are the UI patterns a rules-editor and a
  calendar-URL field would follow
- `.planning/REQUIREMENTS.md` — CFG-01..12 (Companion Configuration Web
  Interface) is the natural home for new CFG-13+ entries if any of these
  three get promoted

## Notes

Captured 2026-09-02, mid-conversation, from the user's own description of
wanting per-direction theme scoping, manual color rules keyed on a specific
plane, and calendar-based highlighting for a friend's flights. Not yet
scoped against a new requirement ID — REQUIREMENTS.md's v1 list currently
ends at CFG-12; promoting any of these three would add new CFG entries
there. The three sub-ideas are deliberately kept in one seed file rather
than split into three, since they share the same "something more specific
than the active theme picks the color" shape and are worth reviewing
together — but they don't have to ship together.
