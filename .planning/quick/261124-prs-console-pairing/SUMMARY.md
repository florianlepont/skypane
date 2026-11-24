# Quick 261124-prs Summary

Console "Add a frame" is now the same one-card /pair-frame page users have,
with an administrator-only Owner picker.

## What changed
- companion/user_pairing.py: owner handling for administrators; invariant
  comment rewritten. companion/pages/pair_frame_page.py: Owner field (only when
  the view carries owners).
- companion/console_pairing.py: dialog handler, POST /fleet/pair and
  `PAIR_PATH` removed; `owner_choice`/`owner_is_active`/`owner_options` shared;
  `/fleet?pair=1` redirects to /pair-frame.
- fleet_page `_add_dialog`, `open_add_dialog` and the dialog-only strings
  (EN and FR) removed; fleet list button, pending "Pair frame" button and
  frame_menu row are plain links to /pair-frame.
- Test-support matrix and render snapshot lose /fleet/pair; baseline regenerated.

## Security effect
An administrator can now pair a code-claimed frame to any ENABLED user (self
included) from /pair-frame; an unknown, non-numeric, empty or disabled owner is
refused with a 400 field error (checked after the lockout test, before the
code is evaluated), and the code stays valid. The role is read server-side
(`principal.role`); the form never decides it. A non-administrator never has
the owner field read: a tampered `owner_user_id` is ignored and the frame
belongs to the signed-in user (test
`test_a_plain_user_has_no_owner_field_and_cannot_pair_to_another_owner`). Both
throttles, CSRF, the two-minute code cookie and PRG are unchanged. Audit: the
existing `pairing.claim` row (actor = the administrator, detail has
`owner_user_id` of the owner) is written by the shared claim code, so who paired
for whom is kept. Choosing another owner lands on /fleet with the `fleet.paired`
flash; choosing oneself or being a plain user lands on the frame's Home.
The kept owner choice after a refused code rides as `&owner=<id>` in the
redirect (an id, validated against the list on display, never trusted).

## Deviations / notes
- The page renders in the personal-space shell (Account active), as for users.
- Dialog-only focus/Tab browser test now exercises the Retire dialog.
