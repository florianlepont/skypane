---
quick_id: 261121-ssf
date: 2026-11-21
description: "Fix the stale per-type release status paragraph in firmware/SIGNING.md"
---

# Quick 261121-ssf: fix the stale signing status paragraph

Documents only. No firmware, server, test or workflow file, no Phase 47/47.1 file.

1. `firmware/SIGNING.md` ("Per-type releases"): replace the "first typed release not yet
   published / workflow does not build the second board / never run on a panel" status
   with a dated factual status, checked against `.github/workflows/firmware-release.yml`
   and the Phase 64 records.
2. Scan the rest of `SIGNING.md` for other statements made false by the same facts.
3. `64-VERIFICATION.md` open point 10: mark the SIGNING.md item fixed (2026-11-21).
4. Run `python3 scripts/check_comment_history.py check`.
