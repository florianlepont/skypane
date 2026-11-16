---
quick_id: 261116-avp
description: Simplify the Reassign modal
---

# Quick 261116-avp: Simplify the Reassign modal

Task 1 (test first): browser test at 390x844, EN and FR: the Reassign sheet has the
owner select, a Reassign button and a Cancel button; no hardware/id text; Cancel
closes without changing the owner; Reassign still reassigns. Update the string
assertion in test_console_fleet_page.py.

Task 2: Reassign dialog only: drop the subtitle, dismiss label becomes Cancel/Annuler
rendered as a secondary button (opt-in `secondary_dismiss` on `ui_modal.dialog_html`),
shorter helper sentence. Retire and re-activate sheets share `_frame_dialog` and stay unchanged.

Task 3: full suites, linters, render baseline, screenshots, SUMMARY.
