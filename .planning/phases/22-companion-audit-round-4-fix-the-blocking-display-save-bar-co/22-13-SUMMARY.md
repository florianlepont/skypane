---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 13
subsystem: ui
tags: [login, pre-auth, field-error, aria-invalid, copy-btn, show-password, lockout, countdown, login-shell, i18n-fr, playwright, contrast]

requires:
  - phase: 22-08
    provides: "the translated login <title> in login_shell(), and the widened test_i18n.py scanner (app.py + attribute literals + JS fallbacks) every new string here had to satisfy"
  - phase: 22-12
    provides: "CFG-29 complete — the standard this plan's four new strings had to be shipped against"
provides:
  - "X3: the login card's field and primary stacked, both filling the content column, both 44px, one shared radius, one --space-md apart — measured at 390px and 1280px by a real layout engine"
  - "X3: the login error under the field in .field-error text-label (that class's SECOND consumer), with aria-invalid/aria-describedby present only when an error is rendered"
  - "X3: an error-coloured field border, gated through WCAG_AA_UI_COMPONENT in both themes against both adjacent colours before shipping"
  - "X3: a show-password toggle reusing .copy-btn verbatim, server-rendered hidden and revealed by script — never a dead control"
  - "X3: a live lockout countdown seeded from the server's own seconds_remaining(), re-enabling both controls at zero with no reload"
  - "companion/layout.py's LOGIN_CARD_SCRIPT_SRC and the ONE deferred script tag login_shell() now emits — it emitted zero before this plan"
  - "companion/static/login-card.js, the twelfth static script and the first this app loads pre-auth"
  - "companion/test_browser_ux.py's first pre-auth coverage: geometry at two widths, a scripts-blocked pass, and a clock-driven countdown"
affects: [22-14, 22-15, 22-16]

tech-stack:
  added: []
  patterns:
    - "A component whose base rule sets `display` always needs its own higher-specificity `[hidden]` selector, or the server-rendered hidden attribute is silently defeated by the author stylesheet"
    - "A per-second update to a role=alert element sets aria-live=off explicitly: the role stays in the accessibility tree, the announcement storm does not"
    - "Playwright's clock API drives a real countdown to zero instead of a harness sleeping through the server's own window"
    - "A live-countdown template is built by substituting into the ALREADY TRANSLATED sentence, and the substitution token is an uppercase code so the i18n scanner excludes it without an exception list"

key-files:
  created:
    - companion/static/login-card.js
  modified:
    - companion/app.py
    - companion/layout.py
    - companion/static/style.css
    - companion/i18n_fr/common.py
    - companion/test_companion_app.py
    - companion/test_contrast_check.py
    - companion/test_browser_ux.py

key-decisions:
  - "The error border SHIPPED: measured 5.16/6.29 light and 5.93/6.53 dark against the two colours adjacent to it, all past WCAG_AA_UI_COMPONENT (3.0). The precedent that would have dropped it was not needed and the threshold was not touched"
  - "aria-invalid is emitted on the wrong-password branch only, not on the lockout branch — during a lockout the typed value is not what is wrong. aria-describedby is emitted on both, because the message describes the field either way"
  - "The toggle's glyph is a text character, not an SVG: login_shell() emits no ICON_DEFS_HTML sprite and emitting one would be a third edit to that function, which the plan forbids. .copy-btn's geometry is still reused verbatim"
  - "The field's toggle gutter is var(--space-xl) (32px), not 22-UI-SPEC.md §3.2's suggested 40px, because §1 of the same document forbids a new off-scale literal and 32px clears the toggle's real 30px reach"
  - "The countdown's substitution token is POLL_COOLDOWN_TEMPLATE_TOKEN's own literal '__N__', which the i18n scanner excludes as an uppercase code — a braced lowercase placeholder failed Check 1 and would have needed an exception list entry"
  - "The brand mark the audit suggested was deliberately NOT added, per 22-UI-SPEC.md §3.2, and the decline is pinned by a check"

patterns-established:
  - "The no-JS floor for a script-gated control is asserted by a real scripts-blocked browser pass, not by reading the markup — that pass is what caught .copy-btn's display beating the UA [hidden] rule"
  - "A test file's own new prose is checked against the plan's grep-shaped acceptance criteria before the criteria are run, because a comment can trip them exactly as code can"

requirements-completed: []

duration: 95min
completed: 2026-09-13
---

# Phase 22 Plan 13: The login card (X3) Summary

**The app's only pre-auth surface stopped being the one page with no stylesheet rule for its own controls: the field and the primary now read as one object at every width, a wrong password is announced instead of merely appearing, you can check what you typed, and a lockout ends by itself.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3 of 3
- **Files created:** 1; **modified:** 7
- **Harness deltas:** companion-app 261 → 269, contrast-check 41 → 43, browser-ux 14 → 17; i18n/status-pages/config-page/view-pages all unchanged in count

## Accomplishments

### Task 1 — geometry and a real, announced error state (`875de52`)

- `.login-form__input` and `.login-card button[type="submit"]` are the app's first rules for these two controls. Both take the full content column, both are 44px tall, both sit at `--radius-control`, separated by one `--space-md`.
- The message moved out of a bare `<p class="text-body">` at the top of the card and into the form, directly under the field, in the existing `.field-error text-label` treatment — that class's second consumer, and its `margin-top` exists for exactly this placement.
- `aria-describedby` is emitted only when a message is rendered; `aria-invalid="true"` only on the wrong-password branch. The negative value is never emitted anywhere.
- `role="alert"` is kept on both branches (existing, correct behaviour).

### Task 2 — the show-password toggle (`31c6e2a`)

- `login_shell()` emitted **zero** script tags. It now emits exactly one deferred tag, sourced from a new `LOGIN_CARD_SCRIPT_SRC` constant beside its eleven siblings, following their duplicated-not-imported convention; the docstring sentence claiming otherwise is corrected in the same edit. **Those are the only two changes this plan made to `companion/layout.py`.**
- `companion/static/login-card.js` is the twelfth static script and the first one this app loads pre-auth: an ES5-safe IIFE, no build step, no vendored library, no inline script, no nonce, **no CSP change** (`grep -c 'unsafe-inline\|nonce-' companion/app.py` is 3 before and after).
- The toggle server-renders with the `hidden` attribute on every branch and the script is the only thing that removes it. The field's padding modifier is appended by the same script, so a scripts-blocked page shows no toggle and reserves no gutter for one.
- `.copy-btn` is reused verbatim — the 22×22 box, the transparent no-border fill, the `::before { inset: -11px }` 44×44 hit area, the 14px glyph box. The new rule adds position and nothing else; there is no second icon-button size in the file.

### Task 3 — the live lockout countdown (`7e3df30`)

- Both controls are natively `disabled` during a lockout, in the existing `button:disabled` treatment. No new disabled styling.
- The countdown is seeded from `LoginThrottle.seconds_remaining()`'s own figure, serialised with `json.dumps()` and carried on the form as `data-lockout-seconds` — the same server-computes / data-attribute / script-reads mechanism `poll-cooldown.js` established, reused rather than re-derived.
- It ticks and, at zero, re-enables both controls with no reload, clears the message and drops the `aria-describedby` that pointed at it.
- **No authentication logic was added.** `auth.py`'s `LoginThrottle` is re-consulted on every POST before the submitted password is even looked at, so re-enabling the form by hand gains nothing (T-22-46). `grep -r "LOGIN_FAILURE_LIMIT" companion/static/ | wc -l` is `0`.

## Measurements

### The error border's contrast gate (Task 1)

`--color-status-error` against the two colours physically adjacent to the field's border, in both themes:

| Theme | vs the field fill (`--color-secondary`) | vs the card surface (`--color-dominant`) |
|---|---|---|
| light (`#BE123C`) | 5.16 (`#EEE8DE`) | 6.29 (`#FFFFFF`) |
| dark (`#FB7185`) | 5.93 (`#1C222D`) | 6.53 (`#151922`) |

All four clear `WCAG_AA_UI_COMPONENT` (3.0), so **the border ships**. The 20-UI-SPEC precedent that would have dropped it was not needed, and the threshold was not touched. Colour is not alone either way: the message under the field names the problem and the next action.

### Geometry, measured by a real layout engine (Task 3)

| Viewport | Field | Primary | Gap | Radius |
|---|---|---|---|---|
| 390px | 278 × 44 | 278 × 44 | 16px | shared |
| 1280px | 296 × 44 | 296 × 44 | 16px | shared |

Against the audit's own measurements — desktop `225×44` r8 beside `68×30` r6 sitting 7px lower; phone 225 of 278px with the button glued at 0px — every figure in the target row is met.

### Touch-target register

`.login-card button[type="submit"]` joins the **kept / met-directly** category at 44px, not the traded-away list, with the three justifications the rule's own comment records: it *restores* the WCAG 2.5.5 floor rather than trading it; matching the field's height and radius satisfies C4's composition rule for a pair that reads as one object; and this is the app's only pre-auth surface, with no density argument to trade against — the same reasoning quick task 260902-qkm used for `.mobile-nav__link`. **22-16 owns recording this in `references/control-density.md`**, along with `.field-error`'s second consumer in `references/settings-page-patterns.md`.

### The declined brand mark

X3's fix column suggested "small brand mark". **It was not added**, per 22-UI-SPEC.md §3.2. The card already renders `<h1 class="page-title">SkyPane</h1>`, which *is* the brand mark in the correct role, and this app's rule that headings carry no glyphs was set deliberately (quick task 260902-j8w removed the app's one heading glyph at the developer's explicit instruction). The decline is pinned by a check that asserts the bare `<h1>` and the absence of any `<svg>` or sprite on the page, so a future plan cannot add one silently.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — Bug] `.copy-btn`'s `display: inline-flex` defeated the server-rendered `hidden` attribute**

- **Found during:** Task 3, by the new scripts-blocked browser pass
- **Issue:** the toggle carries `.copy-btn`, whose `display: inline-flex` is an author-stylesheet declaration and therefore beats the user-agent `[hidden] { display: none }` regardless of source order. With scripts blocked the page rendered a visible show-password button that did nothing — precisely the defect the control was built to avoid, and precisely what D-09's no-JS floor forbids.
- **Fix:** `.login-reveal[hidden] { display: none; }`, the same higher-specificity `[hidden]` selector `.dirty-bar[hidden]` and `.refresh-pill[hidden]` already carry for the same collision class.
- **Files modified:** `companion/static/style.css`
- **Commit:** `7e3df30`
- **Note:** no string-comparison harness could have seen this. It is the clearest argument this phase has produced for D-02's browser harness.

### Acceptance criteria that did not evaluate as predicted

Both were tripped by **this plan's own new prose**, not by shipped behaviour. In each case the prose was reworded; no criterion was edited and no check was weakened.

**1. Task 1 — `grep -c 'aria-invalid="false"' companion/app.py` returned `1`, not `0`.** The single occurrence was in the new `_login_body()` docstring, describing the attribute the function refuses to emit. The docstring now describes it without writing the literal, and says why. The real guard is unaffected: the harness check asserts the literal is absent from the *rendered* output. `grep -c` now returns `0`. This is the same class of self-inflicted trip that caught 22-09 and 22-11 with a backtick in their own new JS comments — worth naming again.

**2. Task 2 — `grep -c "LOGIN_CARD_SCRIPT_SRC" companion/layout.py` returned `3`, not `2`.** The third occurrence was in the corrected `login_shell()` docstring. The docstring now names the constant by description rather than by token, and carries a parenthetical saying why. `grep -c` now returns `2` — the definition and its one use.

Every other criterion in all three tasks evaluated exactly as stated.

### Scoping calls, each recorded rather than taken silently

**1. The plan's `must_haves` asserted "the app has none today" for a `.login-card` stylesheet rule. That is not accurate, and neither is the derived acceptance criterion.** `.login-shell` and `.login-card` rules have existed since 06.6.2-07 (`style.css:4880-4908`), so `grep -c "login-card" companion/static/style.css` was already non-zero (9) *before* this plan and cannot discriminate. What genuinely did not exist — and what the audit actually wrote, `.login-form` — is any rule for the two **controls inside** the card. The check added here pins the three rules that genuinely are new (`.login-form__input`, its `[aria-invalid]` border, and `.login-card button[type="submit"]`) rather than relying on the non-discriminating grep. **22-16 may want to correct the plan-frontmatter claim if it re-reads it.**

**2. `json.dumps()` vs "the poll-cooldown idiom".** The plan's `key_links` requires both, and they are not the same thing: `config_page.poll_trigger_section()` serialises its own seed with `escape_html(str(cooldown_remaining))`, not `json.dumps`. 22-UI-SPEC.md §3.2 names `json.dumps()` explicitly, so that is what shipped (`import json` added to `app.py` for this one use, documented at the import). The *mechanism* — server computes, data-attribute carries, script reads, never a client derivation — is poll-cooldown's, reused verbatim.

**3. The contrast pairs live in `test_contrast_check.py`, not in `contrast_check.py`.** `STATUS_WARN_ON_CARD_PAIRS`'s precedent promotes a pair into the module itself, but `companion/contrast_check.py` is outside this plan's `files_modified`, and that precedent exists for a pair whose measured verdict is *asymmetric across themes* and therefore load-bearing on the shipped CSS. This pair passes in both themes, so nothing in `style.css` is conditional on the numbers.

**4. A pre-existing check was strengthened in place, not duplicated.** `_eleven_deferred_scripts_before_closing_body` keeps its count of eleven and now also asserts `login-card.js` is *absent* from an authenticated page. That is strictly narrower than before and is the "the authenticated page's script count is unchanged" half of Task 2's own acceptance, pinned by the machine that already owns the count. The check count did not change for it.

**5. Task 1's `i18n_fr/common.py` edit did not happen in Task 1.** Task 1 introduced no new user-facing string — `LOGIN_LOCKOUT_TEXT` only moved to a module constant, keeping its existing catalogue key byte for byte. The two new strings (`Show password` / `Hide password`) shipped with their French entries in Task 2's own commit, as required.

**6. Task 3's lockout check extended Task 1's rather than adding a fourth.** Both need an isolated `Harness()` — locking the process-global throttle cannot be undone over HTTP, so the shared harness cannot be used — and spawning a second subprocess to assert two more attributes on the same render would be pure cost. `companion-app` therefore stays at 269 through Task 3.

### No exception was added anywhere

No exception list, allowlist or skip was added to any harness. One near-miss is worth recording: `LOGIN_LOCKOUT_TEMPLATE_TOKEN` was first written as a braced lowercase placeholder, which `test_i18n.py`'s Check 1 correctly flagged as an untranslated module constant. Rather than adding it to an exception list, the value was changed to `config_page.POLL_COOLDOWN_TEMPLATE_TOKEN`'s own `"__N__"`, which the scanner excludes as an uppercase code — which is, on inspection, exactly why that constant has that shape.

## Verification

| Harness | Before | After | Result |
|---|---|---|---|
| `companion/test_companion_app.py` | 261 | 269 | 267/269 — the two documented WR-11 root-sandbox FAILs, by name, unchanged |
| `companion/test_contrast_check.py` | 41 | 43 | 43/43 |
| `companion/test_browser_ux.py` | 14 | 17 | 17/17 |
| `companion/test_i18n.py` | 24 | 24 | 24/24 |
| `companion/test_status_pages.py` | 258 | 258 | 257/258 — the documented `anomaly_active()` root-sandbox FAIL |
| `server/test_manual_resolutions.py` | 23 | 23 | 21/23 — the two documented WR-11 root-sandbox FAILs |

Every `EXPECTED_CHECK_COUNT` was re-derived by **running** the harness and reading its printed total, never by arithmetic; each is appended as a new last assignment citing this plan.

`scripts/run-all-tests.sh`: **no new failure.** The five failing checks are exactly the documented sandbox baseline — 4 × WR-11 read-only plus 1 × `anomaly_active()`, all of which pass in CI because this container runs as root and uid 0 cannot trip a read-only-directory case. Per-harness counts match the baseline: `manual_resolutions` 21/23, `status-pages` 257/258, `companion-app` 267/269 (was 259/261; +8 checks, same 2 failures). Coverage **93%**, well above the 83 floor.

`ruff check .` clean.

## Notes for later plans

- **22-14** — CFG-30 is not ticked. X3 is complete; **B3, B10 and B13 remain** and are 22-14's. The traceability row was updated, the checkbox was not.
- **22-15** — `companion/static/style.css` is handed over clean. This plan's rules are confined to one contiguous block after `.login-card:focus-within` (the `.login-form*` / `.login-reveal*` selectors) plus nothing else; no rule outside that block was touched, tidied or reordered. **T6 ("selection shifts layout by 2px") was not touched and is yours** — it did not surface on this surface at all, since neither login control carries a selected state.
- **22-16** — three things:
  1. **Two `references/control-density.md` rows and one `references/settings-page-patterns.md` row are now owed**, both named in 22-UI-SPEC.md §4's X3 rows: `.login-card button[type="submit"]` joining the touch-target register's **kept** category with its three-point justification, and `.field-error` gaining its **second consumer** with the placement rule stated. C4's composition rule itself is also yours; the login card's field + Sign in is its worked example and now exists in code.
  2. The pattern in Deviation 1 above — *a component whose base rule sets `display` needs its own `[hidden]` selector* — now has **three** consumers in `style.css` (`.dirty-bar`, `.refresh-pill`, `.login-reveal`). If the skill records that collision anywhere, the count is three.
  3. **CFG-28 was not touched and not re-ticked.** Health's page-header clock `title` is still yours.
- **Not re-verified here:** the `<human-check>` in this plan's own `<verification>` block (sign in with a wrong password; block scripts and confirm no dead toggle) is folded into 22-16's closing sweep, as the plan specifies. Both halves are however now covered by machine checks — the error render by `test_companion_app.py` and the scripts-blocked pass by `test_browser_ux.py`.

## Self-Check: PASSED
