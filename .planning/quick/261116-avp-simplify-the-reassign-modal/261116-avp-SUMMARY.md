# Quick 261116-avp: Simplify the Reassign modal - Summary

The Reassign bottom sheet now shows only the title, a one-line helper ("Nothing is erased." / "Rien n'est effacé."), the New owner select, the Reassign button and a secondary Cancel / Annuler button. The hardware-type/id line is gone.

## Changes
- `companion/pages/fleet_page.py`: Reassign dialog drops the subtitle (`with_hardware=False`), dismiss label is `Cancel`, shortened live-frame sentence.
- `companion/ui_modal.py`: `dialog_html(secondary_dismiss=True)` renders the dismiss link as a secondary button (opt-in; default unchanged).
- `companion/static/style-admin.css`: `a.modal__dismiss--button` shares the access-sheet secondary button rule.
- `companion/i18n_fr/admin_fleet.py`: `admin_fleet.keep_owner` replaced by `admin_fleet.cancel` ("Annuler"); helper sentence shortened.
- Tests: new 390x844 EN/FR browser test (select, Reassign, Cancel, no hardware/id text, Cancel leaves owner unchanged); existing Reassign-through-sheet test still covers reassigning; string assertions updated.
- `companion/testdata/render_baseline.json`: stylesheet hash only (verified).

## Other confirm sheets
Retire and Re-activate share `_frame_dialog` / `ui_modal.dialog_html` with Reassign but were left unchanged (still hardware subtitle and "Keep frame" / "Keep retired" text links). Only Reassign opts in.

## Verification
Full suite 15793 passed, 8 skipped (one assertion on the old sentence fixed afterwards and re-run); ruff, mypy, function-size, comment-history clean.

## Deviations
None.
