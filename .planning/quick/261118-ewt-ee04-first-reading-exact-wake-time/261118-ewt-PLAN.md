---
quick_id: 261118-ewt
date: 2026-11-18
description: "Phase 64 criterion 7: exact wake time of the first EE04 battery reading"
---

# Quick 261118-ewt: exact wake time of the first EE04 battery reading

Documents only. No firmware, server, test or workflow file, no Phase 47/47.1 file.

1. `hardware/SECOND-HARDWARE-MEASUREMENTS.md`: row 6 and the 2026-11-18 notes drop the
   "minute not noted" caveat and record the wake time from the frame's battery-history
   export (read-only). Row 6 stays `provisional, first reading, 1 of 3 levels`.
2. `hardware/SECOND-HARDWARE-BATTERY.md` and `64-VERIFICATION.md` (criterion 7): the dated
   sentence gets the exact time. Criterion 7 stays OPEN.
3. Run `python3 scripts/check_comment_history.py check`.
