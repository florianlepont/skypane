# Quick Task 260902-req: Fix inconsistent aircraft centering across ~46 airline illustration PNGs - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning

<domain>
## Task Boundary

Fix inconsistent aircraft centering/cropping across the ~46 airline illustration PNGs (`server/assets/icons/illustrations/`), confirmed via real pixel bbox measurement (e.g. `air-france.png` margins L/T/R/B = 0/14/8/0 near edge-to-edge, vs `lot-polish-airlines.png` = 17/62/14/66, vs `air-caraibes.png` = 0/43/29/18 asymmetric). The developer confirmed the problem is visible on **both** screens: the physical e-ink panel AND the companion web Airlines gallery (`companion/pages/airlines_page.py`).

</domain>

<decisions>
## Implementation Decisions

### The panel side already has a fix in code — this is NOT a build-from-scratch task there
A debug session (`illustration-crop-text-margin`, resolved 2026-08-28, two passes — see `.planning/debug/knowledge-base.md` and `.planning/STATE.md` line 127) already diagnosed and fixed this exact symptom for `server/plane/render.py`'s panel compositor. `draw_illustration()` now returns an `IllustrationPlacement(rect, content)` — `.content` is the tight bbox of pixels actually painted (alpha hard-thresholded at `ILLUSTRATION_ALPHA_THRESHOLD=127` via `_threshold_alpha()`/`_opaque_bbox()`, deliberately excluding each PNG's soft drop-shadow band). `_left_for_centered_content()`, `_top_for_centered_content()`, `_left_for_right_aligned_content()` all anchor to `.content`, not the naive image rectangle. This code is present on the current branch right now (confirmed by direct read).

**The catch, recorded in that session's own notes: "Neither fix has been confirmed on real Spectra 6 glass yet."** The developer is reporting the problem live today, 5 days later. The planner/executor must determine: (a) whether this fix has actually been deployed to the production VPS (`deploy/deploy.sh` — deployment is a manual, explicit action, NOT automatic on merge; do not assume merged-to-main means live-on-device), and (b) if deployed, whether it's genuinely still broken (a real bug in the fix, needing fresh debugging — treat as a new investigation, this exact bug class already has a documented root-cause pattern to check first per the knowledge-base entry) versus just never having been visually confirmed until now.

**Deploying to the production VPS is a real, hard-to-reverse, shared-infrastructure action.** Per this session's own standing rules, do not run `deploy.sh` or any production deploy/restart step unilaterally — if the investigation concludes the fix needs deploying (or redeploying after a further fix), surface that to the developer and let them run it, or get their explicit go-ahead first. SSH `sudo systemctl` access to this VPS is also known to be blocked for this session even after chat confirmation (ask the developer to run it themselves).

### The web gallery side needs a genuinely new fix
`companion/pages/airlines_page.py`'s card grid renders plain `<img src="/illustration/{name}.png">` tags — no server-side Pillow processing, no centering logic at all. This needs the same underlying technique the panel side already validated (alpha-threshold + opaque bbox), applied to however the web gallery displays these images consistently. The exact mechanism (compute the bbox once per file and expose it as a CSS `object-position`/inline style per card; crop-and-serve a normalized version via a dedicated route; or something else) is Claude's discretion — but should reuse/share logic with `render.py`'s already-proven `_threshold_alpha()`/`_opaque_bbox()` rather than reinventing bbox detection from scratch, since that logic is already tested and correct against these exact files.

### Claude's Discretion
- Exact mechanism for the web gallery fix (object-position vs pre-cropped serve vs other) — pick whatever is simplest and most consistent with this codebase's existing patterns (e.g. companion pages already import from `server.*` in several places — check precedent before deciding whether `airlines_page.py` should import directly from `server.plane.render` or a shared helper module).
- Whether this fits as a single quick-task plan (1-3 tasks) or needs to split into two (panel-side investigation/deploy-verification is a different kind of work — debug/verify — than the web-gallery build). If it doesn't fit cleanly, say so rather than forcing an oversized single plan.
- Whether/how to cache computed bboxes for the web gallery (46 files, presumably computed once and cached rather than per-request, but this is not performance-critical the way the panel's per-poll render is).

</decisions>

<specifics>
## Specific Ideas

None beyond what's captured above — the panel-side fix's own approach (opaque-pixel bbox via a fixed alpha threshold, deliberately excluding the soft drop-shadow band every vendored file carries) is the validated reference implementation; the web-gallery fix should follow the same principle for consistency, not invent a different one.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/debug/knowledge-base.md` — `illustration-crop-text-margin` entry (root cause, fix shape, files changed, transferable lesson)
- `.planning/STATE.md` line 127 — session record noting the fix was never confirmed on real glass, and that it also required a second `_DEFAULT_CONFIG_DIGEST` re-pin (relevant precedent: this class of fix changes `panel.bin`'s rendered pixel output, so any further panel-side change here will likely need the same re-pin treatment, following the established "only re-pin from a real CI run" discipline)
- `.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md` line 65 — the corrected design-constant record from that same debug session
- `server/plane/render.py` — `IllustrationPlacement`, `_opaque_bbox()`, `_threshold_alpha()`, `ILLUSTRATION_ALPHA_THRESHOLD`, `_left_for_centered_content()`, `_top_for_centered_content()`, `_left_for_right_aligned_content()`, `draw_illustration()` — read these in full before planning, they are the reference implementation to reuse/share, not reinvent
- `deploy/README.md`, `deploy/deploy.sh` — how production deployment actually works (manual rsync + service restart, not automatic)

</canonical_refs>
