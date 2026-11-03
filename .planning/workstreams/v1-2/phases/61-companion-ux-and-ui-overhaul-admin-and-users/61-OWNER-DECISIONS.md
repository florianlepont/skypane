# Phase 61: Owner decisions ledger

Source: the "Open for owner validation" list at the end of `61-UI-SPEC.md`.

## Rule

A dependent plan checks its row here before it starts. An owner answer
replaces the spec default and is applied by that plan; whoever records the
answer also updates the row (status "owner answered", with the answer in the
Notes column). This is a non-blocking gate: with no answer, the plan proceeds
on the default. The run is non-interactive, so no question is asked; every
row below starts as "default applies".

## Open items (14)

| # | Item | Spec default | Status | Depending plan | Notes |
|---|------|--------------|--------|----------------|-------|
| 1 | Fleet page name | EN "Fleet", FR "Flotte" | default applies | 61-06 | D11 already fixes the name |
| 2 | Last image in the fleet list | Not shown | default applies | 61-06 | D12 already fixes this |
| 3 | Raw "Register a frame" (MAC + secret) form | Removed from every page; `/fleet/register` route and tests stay | default applies | 61-06 | |
| 4 | Users page actions as a "Manage user" dialog | One dialog per user | default applies | 61-08 | |
| 5 | Health for users | Out of the user tab bar and sidebar, reached from the Home status card | default applies | 61-04 | D14 already fixes this |
| 6 | Admin "My views" tabs | Home, Display, Flights; Health in the bar, Airlines/Device in More/sidebar | default applies | 61-04 | |
| 7 | "Use another account" on the not-invited page | Adds `prompt=login` to the Auth0 start | default applies | 61-11 | |
| 8 | First-visit hint wording | No mention of Auth0 sign-up (spec section 5 wording) | default applies | 61-11 | |
| 9 | Welcome toast on the first identity link | Included (small "first link" flag) | default applies | 61-11 | |
| 10 | User redirect from un-prefixed pages | 303 to the user's own frame | default applies | 61-05 | D13 already fixes this |
| 11 | Invite button wording | "Invite user" replaces "Send invitation" | default applies | 61-08 | |
| 12 | Pending frames in the Fleet list | Stay in the main list (hollow dot, after active frames) | default applies | 61-06 | |
| 13 | Landing frame for a multi-frame user | First by name | default applies | 61-05 | |
| 14 | Manage access reopens after each add/remove | Reopens via `?access=<id>` | default applies | 61-07 | |

## Audit items brought into scope

The owner answered "yes, in scope" on 2026-11-03 for the three small items
from `61-VISUAL-AUDIT-NOTES.md` that had no owning plan. Plan 61-15
implements the three.

| Row | Item | Source line in 61-VISUAL-AUDIT-NOTES.md | Owning plan | Status |
|-----|------|------------------------------------------|-------------|--------|
| A | Device page: the Diagnostic LED switch is drawn with an orange box around it | line 61 | 61-15 | in scope (owner, 2026-11-03) |
| B | Health page: the Frame connection row says "Has not checked in" three ways | line 62 | 61-15 | in scope (owner, 2026-11-03) |
| C | Empty states are large serif blocks (Current frame card empty, other empty states) | lines 58-59 | 61-15 | in scope (owner, 2026-11-03) |
