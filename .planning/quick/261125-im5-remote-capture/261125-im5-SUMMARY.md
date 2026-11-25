---
type: quick
id: 261125-im5
status: complete
---

# Quick 261125-im5: Read-only remote mode for capture_pages.py

Added `--remote URL` (https only, site root) and `--cookie-file PATH` to
`capture_pages.py`, plus owner instructions in `CAPTURE-REMOTE.md` (same 68.1
phase folder).

## Behaviour
- Cookie file must be mode 600 (group/world readable is refused); accepts bare token or `sp_session=<token>`.
- Frame ids discovered by GET of `/fleet` and `/` (urllib, 15 s timeout, redirects not followed so the cookie cannot leave the origin); unresolved placeholders produce "skipped: no frame id" cells and a `meta` record in the JSON.
- Cookie reaches the Node driver via the `SP_CAPTURE_COOKIE` environment variable, not the driver config file; output text and JSON are scrubbed of the value; error messages carry only the exception type.
- Browser requests: the driver aborts any non-GET request; dialogs are only opened with showModal(), no clicks. The sign-in page is visited without the cookie.
- Local mode unchanged.

## Tested
- `--help` lists both flags; py_compile and `scripts/check_comment_history.py check` pass.
- Mode 644 cookie file refused; http URL refused; https://127.0.0.1:1 with dummy cookie fails with "ConnectionRefusedError" only; dummy token not found in any output.
- Local `--only signin` still produces matrix.json and screenshots (8 cells, status 200).
- Link parsing and placeholder mapping/skip logic checked with a synthetic snippet.

## Not tested
- The remote browser path end to end (no credentials, real site off limits): env cookie injection, non-GET route abort, and the real /fleet markup for retired/pending detection (best-effort text match on "retired"/"pending"/"en attente").
