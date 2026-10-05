---
quick_id: 261004-cal
type: quick
autonomous: true
branch: claude/calendar-sheet
---

# 261004-cal: Calendar connection becomes one status row and a Manage sheet

## Objective

Owner-approved direction C for the calendar connection (Display, "Allures spéciales"): the page
keeps one compact status row and one button; every control (the masked host, paste/replace,
disconnect with an in-sheet confirmation) lives in a "Manage" dialog, mirroring the airline sheet
(`?calendar=manage#calendar-sheet` no-script variant, flash plus reopen on refusal).

## Tasks

1. Server: replace is fetch-first. `calendar_rules.connect_calendar_url()` reads and parses the
   pasted link before anything is stored; a refused or unreachable link leaves the working link
   and its flights untouched and reopens the sheet with an inline error.
2. Status states derived from persisted fields: not connected, waiting, connected N, zero flights
   (warning), stale (last success older than four fetch intervals), last read failed, ignored
   (group-readable secret). The pill carries the verdict in words; no green dot beside a
   failing or stale verdict. The Calendar row meta no longer repeats "Connected".
3. Markup/CSS/JS: status row, one `<dialog>`, `calendar-sheet.js` (modal open, pending label,
   in-sheet disconnect confirmation). The full URL never reaches the browser; no reveal/copy.
4. EN + FR strings in `companion/i18n_fr/calendar_group.py`; copy-lock tests refreshed deliberately.
5. Tests: served-HTML/route tests per state, fetch-first/failed replace/disconnect, browser tests
   (390/1280, EN/FR, light/dark, round trips, focus, no-script), render baseline regenerated.
