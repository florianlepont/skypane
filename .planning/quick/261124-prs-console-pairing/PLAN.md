# Quick 261124-prs: Console "Add a frame" uses /pair-frame

Owner decision (2026-11-24): an administrator gets an Owner selector on the
user pairing page; the server validates it.

1. Fleet "Add a frame" button, the frame menu row and a pending frame's
   "Pair frame" button link to /pair-frame; GET /fleet?pair=1 redirects there.
2. /pair-frame shows an Owner select (all enabled users, administrator first
   and selected) to an administrator only.
3. user_pairing.handle_post reads the owner only for an administrator; it must
   be an existing active user, else a 400 field error (as the old route did).
   Throttles, CSRF, code cookie and PRG are unchanged; the refused redirect
   carries the owner id so the choice survives.
4. Remove the Fleet dialog, POST /fleet/pair and the dialog-only strings.
5. Update tests, route matrix and render baseline.
