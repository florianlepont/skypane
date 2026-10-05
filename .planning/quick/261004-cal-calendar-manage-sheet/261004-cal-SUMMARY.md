# 261004-cal Summary

The calendar connection on Display is now one status row and a "Manage" sheet (owner-approved
direction C).

## Design as built

- Row (inside Special looks, under the calendar look): provider tile, provider name derived from the
  feed host ("iCloud", "Google Calendar", "Outlook", else the host), a status pill (words plus a dot),
  a one-line detail naming the 48 h window, and one button: "Gérer", or a primary "Connecter" while
  nothing is connected. The row meta no longer says "Connecté".
- Sheet: one `<dialog id="calendar-sheet">`. Masked host and "Lien privé, jamais réaffiché", the
  paste field (write-only, never a `value`), Replace/Connect with a "Vérification…" pending label,
  inline errors, and a quiet red Disconnect with an in-sheet confirmation that says what happens to
  the flights. No native `confirm()`; no reveal or copy of the link.
- No script: Manage is a link to `/display?calendar=manage#calendar-sheet`; the same dialog markup
  renders open in the page. The server confirmation page for Disconnect is unchanged.
  `companion/static/calendar-sheet.js` promotes the open dialog to a modal, writes the pending
  label, runs the confirmation, drops the reopen parameters from the address, and focuses the field
  only after a refused replace.

## Server

- `calendar_rules.connect_calendar_url()`: fetch and parse first; only on success store the link
  (which erases the old registry) and write the new flights. A refused or unreachable link changes
  nothing. `_handle_calendar_connect_post` now calls it (no `_POLL_LOCK`: the candidate fetch touches
  no state, and the existing superseded-fetch guard covers a poll in flight).
- Refusal redirects to `/display?flash=…&calendar=manage&calendar_error=invalid|unreachable#calendar-sheet`.
  New flash `calendar_connect_failed` ("nothing was changed"); the old "Saved, but couldn't sync"
  copy no longer applies to this route. Deferred flash now only means "saved, first registry write
  failed, the next poll reads it".
- Stale threshold: `CALENDAR_STALE_AFTER_S` = 4 x the 30 min fetch interval = 2 h (a blip or two
  is absorbed by the 48 h window; four misses mean the feed or poll stopped).

## States (all derived from persisted fields, no new storage)

none, waiting, connected N, zero flights (warning pill "À vérifier"), stale (warning), last read
failed (error), unparseable timestamp (neutral dot, no detail), ignored (group-readable secret).
"Failed" = last attempt newer than the last success by more than 60 s (success stamps second
precision). Server changes were needed only for fetch-first and the stale constant.

## Decisions not taken (reported, not built)

- Events-read count for zero flights: `parse_ics_events()` returns flight entries only; not exposed.
- Refused/revoked vs unreachable: `fetch_ics()` returns `None` for every failure, no status exposed.
  One error ("Ce lien ne répond pas").
- Copy uses vouvoiement ("vérifiez") to match the app, not the owner's "vérifie".
- The one line "Colore seulement un vol déjà à l’écran ; ne suit ni n’annonce rien…" is kept in the
  connect (not-connected) sheet only; the "Comment ça marche" disclosure is gone.
- The masked host shows in the sheet, not on the page row (the row shows the provider name).

## Tests

New: `companion/test_calendar_sheet.py` (states EN/FR, threshold boundary, structure, no-script
address, refusal, no full URL, fetch-first, failed replace leaves old link and flights, disconnect),
`companion/test_browser_calendar_sheet.py` (390/1280, EN/FR, light/dark, focus, round trips,
pending label, in-sheet confirmation, scripts blocked), server unit tests for
`connect_calendar_url`. Retired/rewritten: the "How it works"/Replace-disclosure/old status tests in
`test_config_page_04.py`, three in `_03`/`_05`. Script pin 16 -> 17, render baseline regenerated
(Display x12 and the disconnect confirmation page, the new script tag plus the new markup).
Pending label is observed at the submit event: Playwright cannot evaluate in a frame whose POST
response is pending.
