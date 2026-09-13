---
phase: 26
slug: companion-dynamism-iv-app-the-finishes
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-13
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | This project's own hand-rolled harnesses — a module per surface, each a list of named checks with an `EXPECTED_CHECK_COUNT` pin. No pytest, no unittest. A check is a function returning `(bool, message)` registered with a human-readable NAME; **the name is the identity, never the index**. |
| **Config file** | none — `scripts/run_all_tests.py` holds the harness list, concurrency and per-harness timeout; `scripts/run-all-tests.sh` owns the stable `PYTHON` contract |
| **Quick run command** | `PY=/home/user/skypane/server/.venv/bin/python; [ -x "$PY" ] \|\| PY=$(command -v python3); "$PY" companion/<the harness this task touches>.py` |
| **Full suite command** | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |
| **Estimated runtime** | single harness: seconds. Full suite: minutes — the browser harness is the only long pole. |

**Baseline (verify by NAME, never by failing-file count):** exactly **5** failing
checks in this sandbox — 4 × WR-11 (read-only filesystem) and 1 ×
`anomaly_active()`. A plan reporting a different count must name which check moved
and why. `EXPECTED_CHECK_COUNT` is re-derived by **running** the harness and
appended as a NEW last assignment citing the plan and task — never by arithmetic.

**The instrument that matters most in this phase:** `companion/test_browser_ux.py`.
This phase's central claim — *a palette and a keystroke are script-only, and that
is acceptable only because everything they reach is reachable without them* — is a
claim about a browser with scripts blocked. A `SKIP` from that harness means the
claim was never checked, so **a SKIP is a failed phase gate, not a caveat.**

---

## Sampling Rate

- **After every task commit:** the touched harness, plus `ruff check .`
- **After every plan (all tasks):** `companion/test_companion_app.py`,
  `companion/test_status_pages.py`, `companion/test_i18n.py` — the three any
  companion change can move — plus `companion/test_view_pages.py` for any plan
  touching a page module
- **After every wave:** full suite
- **Before `/gsd:verify-work`:** full suite green against the 5-check baseline, and
  the browser harness NOT skipping
- **Max feedback latency:** single harness < 60 s; the browser harness is sampled
  per plan, not per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | CFG-53 | T-26-01-B | every palette destination comes from the ONE nav iteration; no second list | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-01-02 | 01 | 1 | CFG-53 | T-26-01-A | a new static route behaving exactly as the sixteen existing ones; no session data in the asset | unit | `… companion/test_companion_app.py && … companion/test_i18n.py` | ✅ | ⬜ pending |
| 26-01-03 | 01 | 1 | CFG-53 | T-26-01-C | a script-only affordance cannot render without script (gate asserted in BOTH directions) | unit (stylesheet scan) | `… companion/test_status_pages.py` | ✅ | ⬜ pending |
| 26-02-01 | 02 | 1 | CFG-61 | — | focus restoration is observed, not assumed | browser (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-02-02 | 02 | 1 | CFG-61 | — | an announcement is read as text, so a repeated one is detectable | browser (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-02-03 | 02 | 1 | CFG-61 | T-26-02-A | the unauthenticated-route set is enumerable, so a new public route is detectable | browser + unit (helper) | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-03-01 | 03 | 2 | CFG-54 | T-26-03-A | results written via textContent only — never a raw-markup sink | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-03-02 | 03 | 2 | CFG-54 | T-26-03-B | focus trapped and restored by the platform; Escape works in three states; no repeated announcement | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-03-03 | 03 | 2 | CFG-54 | — | fits 360 px in both themes; entrance reuses the existing `@starting-style` | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-04-01 | 04 | 3 | CFG-55 | T-26-04-B | a shortcut never fires while the user is typing; the chord is bounded | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-04-02 | 04 | 3 | CFG-55, CFG-53 | T-26-04-A | **every** palette destination is reachable with scripts blocked | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-04-03 | 04 | 3 | CFG-55 | — | no shortcut is the only path to anything; no state change from a keystroke | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-05-01 | 05 | 3 | CFG-56 | T-26-05-A | the configured password is never rendered, nor any prefix of it; comparison is constant-time | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-05-02 | 05 | 3 | CFG-56 | — | the checklist is ABSENT from the response body when complete, not hidden | unit | `… companion/test_view_pages.py` | ✅ | ⬜ pending |
| 26-05-03 | 05 | 3 | CFG-56 | — | the checklist renders and its next actions navigate with scripts blocked; no client storage | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-06-01 | 06 | 4 | CFG-57 | — | the two new parameters' falsy default is BYTE-IDENTICAL for all six existing callers | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-06-02 | 06 | 4 | CFG-57 | T-26-06-A | illustrations carry no colour literal and every emitted class resolves | unit | `… companion/test_status_pages.py` | ✅ | ⬜ pending |
| 26-06-03 | 06 | 4 | CFG-57 | — | the illustration is visible in BOTH themes and carries its own size | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-07-01 | 07 | 5 | CFG-57 | T-26-07-A | every next-action link is a real destination, escaped | unit | `… companion/test_view_pages.py` | ✅ | ⬜ pending |
| 26-07-02 | 07 | 5 | CFG-57 | — | Health's two tiles keep the compact variant; no `.widget-verdict` appears | unit | `… companion/test_status_pages.py` | ✅ | ⬜ pending |
| 26-07-03 | 07 | 5 | CFG-57 | — | every adopted empty state renders with scripts blocked at 360 px | browser | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-08-01 | 08 | 6 | CFG-58 | T-26-08-B | the download resolves through the caller's OWN session; no route loses its gate | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-08-02 | 08 | 6 | CFG-58 | T-26-08-C | `panel-lookup.js` still makes no network call, starts no timer, holds no state | unit (source scan) | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-08-03 | 08 | 6 | CFG-58 | T-26-08-A | the set of routes reachable WITHOUT a session is unchanged by this phase | browser + unit | `… companion/test_browser_ux.py` | ✅ | ⬜ pending |
| 26-09-01 | 09 | 7 | CFG-59 | T-26-09-A | the theme-color value comes from the resolved theme's own token, escaped | unit | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-09-02 | 09 | 7 | CFG-60 | T-26-09-B | compression is scoped to public static types; no HTML response is compressed | unit (file assertion) | `… companion/test_companion_app.py` | ✅ | ⬜ pending |
| 26-09-03 | 09 | 7 | CFG-53…61 | — | baseline by NAME; no SKIP; every requirement's clauses accounted for | full suite + browser | `bash scripts/run-all-tests.sh && … companion/test_browser_ux.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Sampling adequacy — the Nyquist question

### The one that decides the phase

**Checking one palette destination is sampling below the rate at which a broken
destination can be introduced.** The failure mode is a *single* hand-added command
pointing somewhere no link goes — so the sweep must be **per destination, every
run**, not a spot check. This is the phase's defining sampling decision and 26-02
exists to make it cheap enough to always do.

### Axes every new surface must be asserted across

| Axis | Values that must appear |
|---|---|
| Scripts | on **and** blocked (`_no_js_page()`, `test_browser_ux.py:930`, `:1377`, `:1584`) |
| Input modality | pointer **and** keyboard-only; plus **typing into a field** while a shortcut key is pressed |
| Theme | light **and** dark (24-02's switch — the harness had never measured dark mode before it) |
| Viewport | 360 px (contract floor) and 1280 px; 320 px kept where it already passes |
| Language | English and French — French strings are longer and have overflowed before |

### Per-surface states a happy-path check would miss

| Surface | States that must be sampled |
|---|---|
| Palette | empty query; a query matching nothing; a query matching everything; Escape from the input, from a focused result, and with an empty query; opened by trigger, by `⌘K`, and by `/`; re-opened after a close (focus must go back to the trigger, not to `<body>`) |
| Shortcuts | `g` pressed **inside** the Airlines filter box, inside the palette's own input, and inside a `<textarea>`; `g` alone with the chord window expired; `g` followed by an unbound letter; a modifier held |
| First run | each of the three signals false alone (3 states), all three false, **and all three true** — the all-true case is the one that proves disappearance and the one a happy-path check omits |
| Empty states | each of the six existing call sites unchanged; the compact variant inside a Health tile; an empty state whose next action points at a page the user is already on |
| Share | `navigator.canShare` absent (the harness's real state — assert the control is ABSENT and the download anchor PRESENT); the lightbox on History and on Airlines; the Home hero picture with no picture yet |

### The defect most likely to ship silently

**An empty state that renders correctly in light mode and invisibly in dark.**
24-01 states the rule in as many words — *a drawing correct only in light mode is
a defect, not a polish item* — and an SVG line illustration on an off-white ground
is exactly the shape that gets drawn with a stroke that vanishes on a dark one.
Every illustration is measured in both themes, in a real browser, at 360 px.

### The claim no instrument in this repository can settle

`navigator.share` is **undefined** in the harness Chromium (verified, 23-RESEARCH.md)
and desktop Firefox has no support. The share sheet itself is **manual, on a real
phone**. It is pinned here by its *absence* instead — a named check that the
control does not render when the capability is missing, which is the branch a wrong
implementation actually gets wrong.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements, with cross-phase
dependencies that must be present before the waves that need them:

- [x] `companion/test_browser_ux.py` `_no_js_page()` — **already exists** (23-02)
- [x] The `.js` gate — **already shipped**: `nav-dropdown.js:31` sets it
      unconditionally and `style.css:1078` consumes it. This phase depends on the
      shipped mechanism, **not** on Phase 25's restatement
- [x] Native `<dialog>` + `showModal()` and its `@starting-style` entrance —
      already shipped (`panel-lookup.js:280`, `style.css:6220-6299`)
- [ ] `companion/draw.py` — **owned by 24-01**. 26-06 requires it and carries an
      **executable precondition** that fails loudly if absent. It must NOT fork a
      second drawing path (Open decision 4)
- [ ] `companion/test_browser_ux.py` theme switch — **owned by 24-02**. 26-06 and
      26-03 call it. If it has not landed, those plans STOP rather than building a
      second theme mechanism
- [ ] The deferred-script pin at its post-Phase-25 value — 26-01 re-derives it by
      **running**, never by assuming 15
- [ ] No framework install needed. Playwright is already pinned in
      `server/requirements-dev.txt` and never reaches the VPS

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The native share sheet | CFG-58 | `navigator.share` does not exist in the harness browser and Firefox desktop has no support — there is no machine path to it in this repository at all | On a real phone, open the picture, tap Share, send it to a messaging app, and confirm the received image is the panel |
| Whether the palette is worth its keystroke | CFG-54, CFG-55 | Reach is not usefulness. The harness proves every destination resolves; only the developer can say whether `⌘K` beats the tab bar for them | Use the app for a session with the palette present; decide whether the trigger stays in the header, becomes keyboard-only, or the feature is dropped |
| The guided first run, actually first-run | CFG-56 | The harness can force each signal; it cannot reproduce the experience of a genuinely new install | On a clean state directory with no check-in and no gallery, walk the checklist to completion and confirm it disappears without a reload trick |
| Whether the manifest half is really not wanted | CFG-59 | A recommendation, not a measurement (26-RESEARCH.md §5) | Read the five grounds and accept or reverse |
| gzip actually reaching the wire | CFG-60 | The harness launches `companion/app.py` directly and never runs Caddy | On the VPS: `curl -H 'Accept-Encoding: gzip' -sI https://<config-host>/static/style.css` shows `content-encoding: gzip`, and the same request for `/` does **not** |
| The phase judged together, real device | CFG-53…61 | 06.6.1-06's precedent: a real-device session found two confirmed CSS defects no harness had caught | A real phone at 360 px and a desktop, both themes, both languages |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a named cross-phase dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0's cross-phase dependencies confirmed present before the waves needing them
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s per harness
- [ ] The browser harness does not SKIP at the phase gate
- [ ] The destination sweep runs **per destination**, not as a spot check
- [ ] The unauthenticated-route set is asserted unchanged
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
