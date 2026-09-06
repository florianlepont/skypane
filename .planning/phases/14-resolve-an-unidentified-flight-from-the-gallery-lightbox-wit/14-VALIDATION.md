---
phase: 14
slug: resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-06
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `14-RESEARCH.md` § Validation Architecture, with one correction applied
> (see "Which harness owns what" below).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Custom stdlib-only `check()`/`main()` harness per file — not pytest/unittest. Every file defines `EXPECTED_CHECK_COUNT` and exits non-zero when the actual pass count does not match exactly. |
| **Config file** | none — `scripts/run-all-tests.sh` is the single source of truth for the harness list (17 files since Phase 13) |
| **Quick run command** | `server/.venv/bin/python3 companion/test_status_pages.py` (or `companion/test_view_pages.py`) |
| **Full suite command** | `scripts/run-all-tests.sh` |
| **Estimated runtime** | ~60 seconds full suite |

### Which harness owns what — correction to RESEARCH.md

RESEARCH.md names `companion/test_view_pages.py` as *the* target harness. Verified against the
source, the ownership is actually split, and a plan that targets the wrong one will add checks
where the fixtures do not exist:

| Harness | Checks today | Owns |
|---|---|---|
| `companion/test_status_pages.py` | **149** | The Airlines page's rendered content — 153 `airlines_page` references. This is where Phase 13 added all its page checks (136 → 149). **Gap cards, chips, the summary line, the overflow line, ordering and caps go here.** |
| `companion/test_view_pages.py` | **54** | The shared lightbox/dialog contract — 66 `lightbox`/`panel-lookup` references, and the home of `_lightbox_dom_contract_three_file_guard()` (line 1712), which pins DOM tokens across page, script and stylesheet. **New `data-view-panel-*` attributes and `lightbox__*` classes go here.** |

Both counts must move in the same task that adds their checks.

---

## Sampling Rate

- **After every task commit:** the harness owning the file just touched, per the table above
- **After every plan wave:** `scripts/run-all-tests.sh`
- **Before `/gsd-verify-work`:** full suite green — **and** the manual browser pass below completed
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

This phase has no REQUIREMENTS.md ID (unmapped presentation follow-up, Phase 10-13 precedent). The map is keyed to `14-CONTEXT.md`'s locked decisions. Task IDs fill in once PLAN.md files exist.

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | Cross-file contract | Every new `data-view-panel-*` attribute and `lightbox__*` class appears in the rendered page, in `panel-lookup.js`'s source, and in `style.css` — mirroring the existing three-file guard | source + render assertion | `companion/test_view_pages.py` | ✅ (guard exists at :1712, extend it) | ⬜ pending |
| TBD | TBD | 1 | D-01 / D-02 | A gap card renders the example callsign as its label, emits **no `<img>`**, and its trigger is a real `<a href="/airlines?resolve=…">` — not a `<button>` | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | D-05 / D-06 | The gap block sits at the head, sorted count-descending, with the ≥3 threshold and ≤12 cap both applied — seeded from a `poll_state.json` fixture | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | D-07 | The overflow line renders the exact hidden count and the Health link **only** when the cap actually bites | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 1 | `data-filter-group` | Gap cards carry their own group namespace and never collide with the gallery's `enumerate()` sequence — RESEARCH.md's silent-collision finding | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-08 / D-10 | Chips render "resolved by hand" / "superseded" from `_manual_resolution_rows()`'s existing booleans — **consumed, never re-derived** | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-11 | The summary line's counts match the registry, and each card's `data-filter-text` carries its chip label | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | D-12 | Phase 13's `_resolve_section_html()` still renders for `?resolve=` — the no-JS fallback is intact, and its form comes from the **same rendering function** the dialog uses | render assertion | `companion/test_status_pages.py` | ✅ | ⬜ pending |
| TBD | TBD | 2 | No-network invariant | `panel-lookup.js`'s source contains no `image.src = ""` assignment path — RESEARCH.md's spurious-request finding | source assertion | `companion/test_view_pages.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Extend `_lightbox_dom_contract_three_file_guard()` (`companion/test_view_pages.py:1712`) to cover every new dialog attribute and class this phase introduces — RESEARCH.md's Open Question 3, answered: **yes, they need the same guard**, because this phase adds the first attributes that mean different things to different card types.
- [ ] Seeded `poll_state.json` fixtures for the threshold/cap/ordering cases (D-05/D-06/D-07). Phase 13's `test_status_pages.py` already seeds `unresolved_prefixes` via `poll_loop.save_poll_state()` — reuse that helper, do not invent a second one.
- [ ] No framework install needed.

---

## Manual-Only Verifications

**This section is unusually large, and that is the honest shape of this phase.** Almost everything that makes it worth doing lives in the browser. Phase 13 hit this wall with one row (its `<datalist>`, gap G-02, still open); this phase inherits it across most of its surface.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The dialog opens from a gap card with **no image** and no spurious network request | D-02 | Requires a JS engine executing against a live DOM, plus the network panel to confirm no request fires | Open Airlines with a seeded gap, click an empty card, confirm the dialog opens with no image area and the network tab shows no extra request |
| The right form shows for the right card type | D-03 | `hidden` toggling happens at runtime | Click an art card (replace form), then a gap card (resolve form); confirm each shows only its own |
| Delete works from inside the dialog | D-09 | Runtime form wiring | Open a manual entry's card, delete from the dialog, confirm the entry goes and the override image stays |
| `?resolve=` opens the dialog on page load | D-13 | Load-time `showModal()` | Click Resolve on Health; confirm the dialog is open on arrival |
| After naming, the dialog reopens on the upload step by itself | D-14 | Redirect + load-time open | Name an airline with no artwork; confirm the dialog reopens on Step B |
| Focus lands sensibly when the dialog opens | D-02/D-03 | Native `<dialog>` autofocus, and RESEARCH.md's finding that `hidden` must be toggled **before** `showModal()` | Open both card types with the keyboard; confirm focus is not lost and Escape still closes |
| The summary line actually re-filters the grid | D-11 | Needs `list-filter.js`'s new programmatic hook to run | Click the summary line; confirm the grid filters to manual entries |
| The no-JS fallback still resolves | D-12 | Requires disabling JS | With JS disabled, follow Health's Resolve link and complete a resolution through the page section |
| **Phase 13's G-02**, inherited | — | Browser-owned `<datalist>` behaviour, never yet verified | Confirm suggestions drop down while typing, dismiss, and do not obstruct the form on a narrow viewport |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] **The manual browser pass above is complete** — not optional for this phase
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
