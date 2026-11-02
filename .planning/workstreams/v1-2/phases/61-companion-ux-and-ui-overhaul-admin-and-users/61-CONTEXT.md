# Phase 61: Companion UX and UI Overhaul (Admin and Users) — Context

**Gathered:** 2026-11-02 (walkthrough with the owner, one task at a time)
**Status:** Ready for UI-SPEC and planning
Evidence: `61-WALKTHROUGH.md` (frictions F1-F12, current step counts per
task), `61-VISUAL-AUDIT-NOTES.md` (page sweep on fake data).

<domain>
Rework navigation, page structure, the admin console, the user view and
the sign-in/invitation messages of the companion (requirements UX-01..UX-04).
</domain>

<decisions>
## Locked by the owner
- D1 Admin signs in on a 100% admin space (fleet, users, locations, audit,
  releases) with a link to their own personal views (Home, Display,
  Flights). No "Admin" tab inside the everyday app.
- D2 Fleet list shows frame name, owner and ONE status dot. No state
  column, firmware, battery or location. (Last image: to confirm in spec.)
- D3 Creation and lifecycle forms open from a "+" / action button in a
  modal (native <dialog>): invite a user, add a frame (pairing by code
  only), retire, reassign, re-activate, manage access.
- D4 Vocabulary: the physical device is a "cadre" (frame); button "Ajouter
  un cadre". The fleet page needs a name distinct from "cadre" (not
  "Cadres"): pick in UI-SPEC copy.
- D5/D6 Co-management leaves Home. Admin: "Manage access" per frame in the
  fleet list (modal). User: "Manage access" on the "My frames" list, owned
  frames only (modal). Server rules unchanged (owner or admin adds/removes,
  a co-manager can leave).
- D7 A user lands on the Home of their frame (not Account). With several
  frames a frame switcher stays at the top of every page; "My frames" lives
  in that switcher or under Account.
- D8 A user reads a frame's state from ONE status dot, same vocabulary as
  the fleet list.
- D9 All display settings stay for users; the "location" and "detection"
  cards merge into one.
- D10 Scope: rework navigation and page structure; architecture stays
  (stdlib server, hand-written CSS, no framework, no new runtime
  dependency); visual style unchanged.
- The raw "Register a frame" (MAC + secret) form is not used by the owner:
  remove it from the page body (keep it reachable only if the spec finds a
  need; to settle in UI-SPEC).
- Sign-in works for the owner; UX-04 (unverified email message, guided
  first arrival, actionable errors, SEED-011) stays in scope from the
  requirement. SEED-012 stays out.

## Walkthrough step counts to beat (record after)
Admin: fleet state 2, invite ~5, pair ~6, retire/reassign ~4, co-manager ~5,
audit 2. User: sign in ~4, see frames 1 (but lands on Account), frame
state ~3, change a setting ~4.
</decisions>

<constraints>
- Phase 47 files and hardware/ are untouchable; the live frame keeps its
  image, interval, auth and responses; stub-server/test_phase47_freeze.py
  stays green; changes are expand-only.
- Do not deploy or merge (CI deploys production on merge to main); PRs
  stay draft.
- No real secrets, no real network in tests (pytest-socket, fake Auth0).
- Bilingual EN/FR (strings in companion/i18n_fr/), 360 px width, 44 px tap
  targets, both themes.
- CLAUDE.md conventions: stdlib + Pillow + requests, English comments with
  no plan/phase IDs, check_comment_history.py, functions <= 80 lines,
  behaviour tests not source tests, ruff, mypy.
- In shared planning docs touch only phase-61 lines; merge main into the
  branch before finishing.
- Design system: .claude/skills/sketch-findings-skypane (dated 2026-09;
  verify against current companion/static/style.css).
</constraints>

<deferred>
- SEED-012 (invite creates the Auth0 account): owner decision, not in phase.
- Visual restyle: not in scope (D10).
</deferred>
