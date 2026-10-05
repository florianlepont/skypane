---
quick_id: 261005-upr
type: quick
autonomous: true
branch: claude/update-rows
---

# 261005-upr: Update page, direction B ("compact list")

## Objective

Ship the owner-approved redesign of the companion "Mise à jour" page. Sketches and analysis live
outside the repo (scratchpad `sketches-update/`). Owner decisions: direction B; one
call-to-action card on top; a "Versions" card of one-line rows, each a native `<details>`; the full
history (no cut-off); relative dates on every line with the absolute date kept in `title` and inside
the opened row; release notes cleaned at the source; an older release is worded "Revenir à
fw-vX.Y.Z"; no "last contact" line; the accent primary button only for installing a newer release.

## Tasks

1. `server/firmware_registry.update_view()` gains a per-release `direction` ("newer"/"older"/None)
   against the running version; the page words an older install as a rollback from it.
2. `companion/pages/update_page.py`: one call-to-action card (up to date / update available /
   scheduled / installing / failed, plus "on the frame" footer) and one list of `<details>` rows;
   Install forms, the confirmation gate and every guard unchanged. Old cards + table markup removed.
3. `companion/ui_time.py`: `relative_time_html(with_title=)` and `absolute_time_html()` (a plain,
   non-ticking `<time>`).
4. `companion/static/style.css`: `.update-cta*`, `.update-row*`, `.update-actions`; old firmware
   table / notes rules removed; no new token, colour, size or accent consumer.
5. French strings in `companion/i18n_fr/update.py`; "Versions" joins the cognate list.
6. Release notes cleaned at the source: pure `clean_note()`/`clean_notes()` in
   `scripts/fw_release_manifest.py` (strip `type(scope):` and `Phase NN:` prefixes and `(#123)`,
   drop empty/merge/housekeeping subjects, sentence case, dedupe). Notes are display text only:
   the signed image, its sha256 and the manifest identity fields are untouched.
7. Tests: rewrite `companion/test_update_page.py` and `companion/test_browser_update.py` against the
   served HTML and a browser; cleaning unit tests in `deploy/tests/test_release_manifest.py`.
8. Regenerate the render baseline; verify only the Update page entries changed.
