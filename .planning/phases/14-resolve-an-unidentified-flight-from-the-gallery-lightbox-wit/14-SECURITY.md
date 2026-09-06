---
phase: 14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit
audited: 2026-09-06
asvs_level: 1
block_on: high
threats_total: 29
threats_closed: 29
threats_open: 0
threats_open_nonblocking: 0
unregistered_flags: 6
status: secured
verification_method: >
  Source-level grep plus empirical execution against the real render path
  (rendered HTML scanned for duplicate ids, hostile-input escaping, filter-group
  collisions, injection bounds, and registry read counts under an instrumented
  loader), and all three companion harnesses run at HEAD.
harnesses_at_head:
  - "companion/test_view_pages.py: 63/63 pass"
  - "companion/test_status_pages.py: 163/163 pass"
  - "companion/test_companion_app.py: 159/159 pass"
---

# Phase 14: Security Audit

**Phase:** 14 — Resolve an unidentified flight from the gallery lightbox, with coverage gaps as empty cards
**ASVS Level:** 1 (mitigation present in the cited file)
**Block threshold:** `high` — only `high` and `critical` open threats count toward `threats_open`
**Result:** SECURED. 29/29 threats closed, 0 open. Six unregistered flags recorded below (all closed in code; recorded because the plan-time register did not anticipate them).

Implementation files were not modified by this audit. The only file written is this one.

---

## 1. Threat register verification

### 1.1 Plan-time register (24 entries, 8 plans)

| ID | Category | Severity | Disposition | Status | Evidence |
|----|----------|----------|-------------|--------|----------|
| T-14-01 | Tampering (stored XSS) | high | mitigate | **CLOSED** | `airlines_page.py:1247-1472` — `_resolve_context_html()` escapes prefix/count/callsign once each and interpolates `layout.concise_timestamp_html()`'s already-safe markup verbatim (documented exception); `_resolve_name_form_html():1394` escapes `prefix_value` once; `_known_airlines_datalist_html():1318` escapes each option value once; `_resolve_upload_form_html()`/`_manual_delete_form_html()` receive an `action` already escaped at construction (`_manual_delete_action():1610` `escape_html(prefix)`, and `_resolve_section_html():1583` `escape_html(key)`) and correctly do **not** re-escape. Empirically confirmed: a full render with hostile prefixes/callsigns/timestamps and an operator name containing `&`/`<`/`>`/`"` produced zero raw markup and zero attribute break-outs. |
| T-14-07 | Tampering | low | mitigate | **CLOSED** | `test_status_pages.py:404-441` — `_seed_manual_resolutions()` seeds only via `manual_resolutions.add_entry()` and raises `AssertionError` naming prefix + code on any non-`ADD_OK` return. The negative gate holds: `grep -c 'json.dump' companion/test_status_pages.py` = 0. End-to-end check at `:7198-7238` exercises it against the real loader (green). |
| T-14-08 | Repudiation | low | accept | **CLOSED — accepted risk logged** (§3.1) | `test_status_pages.py:286` `EXPECTED_CHECK_COUNT = 163`, `:7825` `return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1`; `test_view_pages.py:75` = 63, `:2599` same gate. Both suites currently pass at exactly the stated counts, so a mis-stated comment fails loudly, never silently. |
| T-14-09 | Tampering (DOM integrity) | high | mitigate | **CLOSED** | Verified empirically, not by inspection. Rendered `/airlines` with `?resolve=` set (dialog **and** no-JS fallback simultaneously present) across all four branches — Step A, Step B, already-resolved/superseded, and no-resolve. Duplicate ids: **none** in any branch. Every `<label for>` and every `list=` resolves to exactly one id in every branch. `id_suffix` mechanism confirmed in source for all three id-bearing shared functions: `_resolve_name_form_html():1370` (`MANUAL_NAME_INPUT_ID + id_suffix` in both `id` and `for`, threaded into `list=`), `_known_airlines_datalist_html():1321` (`MANUAL_DATALIST_ID + id_suffix`), `_resolve_upload_form_html():1429` (`MANUAL_UPLOAD_INPUT_ID + id_suffix`). **`_manual_delete_form_html()`'s no-`id_suffix` claim independently confirmed true in current source** (`:1468-1473`): its returned markup names only a `class`, an `action`, a `<p>` and a `<button>` — no `id`, no `label for`, no `<datalist>`. `_resolve_context_html()` does `del id_suffix` and emits `<dl>/<dt>/<dd>` with classes only. `_lightbox_replace_form_html()`'s `REPLACE_INPUT_ID` is reachable from exactly one call site (`_lightbox_html():1119`, once per page). |
| T-14-10 | Elevation of Privilege | medium | mitigate | **CLOSED** | The route's own authorization is unchanged and unwidened. `app.py:1767-1774` — `MANUAL_DELETE_ROUTE_PREFIX` appears in `do_POST` **only** (grep: single dispatch site); a GET to that path falls through to 404. `require_session()` runs *before* the prefix slice and before `_handle_manual_resolution_delete()`. `GET /airlines` (the trigger surface) is gated at `app.py:1592-1594`. `auth.py:138` still emits `HttpOnly; Secure; SameSite=Strict`, and `companion/auth.py` is **not in this phase's diffstat** — untouched. `git diff f12ab47..HEAD -- companion/app.py` shows the delete dispatch was not modified at all. Pinned live by `test_companion_app.py:3632-3679` (unauthenticated POST → 303 to `/login`, and `manual_resolutions.json` provably not written). |
| T-14-11 | Information Disclosure | low | accept | **CLOSED — accepted risk logged** (§3.2) | Both names render only behind the session gate, escaped once each — confirmed in the rendered note attribute with a hostile operator name (`&amp;`/`&lt;Co&gt;`). |
| T-14-12 | Tampering (client-side injection) | medium | mitigate | **CLOSED** | `list-filter.js:110-116` — `input.value = setBtn.getAttribute("data-filter-set") \|\| ""`, a property assignment. Downstream consumer is `applyFilter()`'s `text.indexOf(query)` substring test only. Grep for `innerHTML\|outerHTML\|insertAdjacentHTML\|document.write\|eval(\|new Function` across `list-filter.js`: **zero matches**. The attribute is emitted with the fixed literal `"manual"` (`airlines_page.py:1678`). |
| T-14-13 | DoS (self-inflicted) | low | mitigate | **CLOSED** | `list-filter.js:44` — one `querySelectorAll("[data-filter-set]")` at init, one listener per match (`:108-117`). Grep for `setTimeout\|setInterval\|fetch(\|XMLHttpRequest`: **zero matches**. Card set is bounded by `GAP_BLOCK_CAP = 12` plus the curated list. |
| T-14-14 | Information Disclosure | low | accept | **CLOSED — accepted risk logged** (§3.3) | Independently verified: the phase's added CSS contains **no** `content:`, `url()`, `attr()`, or new custom property. Pinned by the exhaustive selector-inventory check (`test_status_pages.py:7502`, green). |
| T-14-15 | Tampering (visual signalling) | low | mitigate | **CLOSED** | `_gap_card_html():1013-1015` — `<span class="airline-card__placeholder" aria-hidden="true"></span>` sits beside a real visible `<p class="airline-card__name mono">{callsign}</p>`, and the card carries `aria-label="Resolve prefix %s — example callsign %s"`. `style.css:3720-3727` uses a dashed border + canvas fill as reinforcement, no accent token. The announced text, not the colour/shape, carries the meaning. |
| T-14-16 | Tampering (stored XSS) | high | mitigate | **CLOSED** | `_gap_card_html():974-1029` — `escaped_prefix`/`escaped_callsign` computed once and reused across `href`, `data-view-panel-caption`, `-scope`, `-resolve-prefix`, `aria-label` and the visible `<p>`; `first_seen`/`last_seen`/`count` escaped at their own interpolation; `filter_text` escaped once. Empirically confirmed with a hostile `example_callsign`, hostile `first_seen`/`last_seen`, **and a hostile registry key used as the prefix** — output clean. |
| T-14-17 | Tampering (filter collision) | medium | mitigate | **CLOSED** | Verified empirically against a render carrying 12 gap cards **and** 28 curated/injected cards simultaneously. Raw group values: `gap0..gap11` vs `0..27`, raw-value overlap = `set()`. After `list-filter.js:79`'s own `"g" + group` keying: **zero** duplicate keys. |
| T-14-18 | Information Disclosure | low | accept | **CLOSED — accepted risk logged** (§3.4) | Same values `_resolve_context_html()` already renders to the same session; the whole page is behind `require_session()`. |
| T-14-19 | DoS (self-inflicted) | high | mitigate | **CLOSED** | `panel-lookup.js:157-161` — the imageless branch is `image.removeAttribute("src"); image.removeAttribute("alt")`. Grep for `\.src *= *""` / `\.src *= *''` across the file: **zero matches**; the only `image.src` write (`:153`) is inside `if (src)`. Pinned green by two `test_view_pages.py` checks (no-empty-src assertion, and "`removeAttribute("src")` is nested inside a conditional branch, never at module scope"). |
| T-14-20 | Tampering (client-side re-validation) | medium | mitigate | **CLOSED** | `panel-lookup.js:346-357` — no validation logic; the determination is entirely "does a matching `data-view-panel-resolve-prefix` element exist in the already-server-rendered DOM". `if (autoTrigger) { openFromTrigger(autoTrigger); }` has no `else` — a non-match is a silent no-op with no error surfaced. Server-side counterpart confirmed empirically: `?resolve=` values `x"],img,["y`, `<script>alert(1)</script>`, `not-a-prefix`, `../../etc/passwd`, `ZZZZZZZZZZ` each render the stale sentence, **no** form, and **never** echo the raw value. |
| T-14-21 | Tampering (raw-markup injection) | high | mitigate | **CLOSED** | Every write in `openFromTrigger()` is `textContent`, `.hidden`, `.value` or `setAttribute` (`:150-269`). Grep for `innerHTML\|outerHTML\|insertAdjacentHTML\|document.write\|eval(\|new Function` across `panel-lookup.js`: **zero matches**. |
| T-14-22 | Tampering | low | mitigate | **CLOSED** | `app.py:1421-1436` (diff verified) — the narrowed branch selects only between `FLASH_KEY_MANUAL_NAME_UNUSABLE` and `FLASH_KEY_MANUAL_NAME_EMPTY`, two fixed server-authored constants. `raw_name` is read only for `.strip()` truthiness and never reaches the response body or the redirect `Location`. The diff touches nothing else in `_handle_manual_resolve_post()` — `unresolved_row_for_prefix()` still runs first, unchanged. |
| T-14-23 | Repudiation | low | accept | **CLOSED — accepted risk logged** (§3.5) | The new message (`app.py:265-266`) states a requirement in user terms and never echoes the rejected value. |
| T-14-24 | Tampering (stored XSS) | high | mitigate | **CLOSED** | `_airline_card_html():578-800` — every one of the widened block's fifteen `data-view-panel-*` values is either a server constant, an already-escaped-at-construction URL (deliberately not re-escaped, documented), or `escape_html()`'d once (`heading_value:678`, `upload_action_value:679`, `resolve_prefix_value:674`, `first_seen/last_seen/count:711-714`, `aria-label:761`, `filter_text:783`, the name `<p>`, and each chip). `MANUAL_SUPERSEDED_NOTE_TEMPLATE`'s four slots at `:699-703` are `escape_html(prefix)`, `escaped_built_in_name`, `escape_html(operator_name)`, `escaped_built_in_name`. Empirically confirmed on a real superseded card with an operator name of `Zephyr & <Co>` → `Zephyr &amp; &lt;Co&gt;`. **Cross-plan check: all three stored-XSS threats (T-14-01/16/24) verified in the FINAL merged file, not per-diff — no later plan dropped an earlier plan's escaping.** |
| T-14-25 | Elevation of Privilege | medium | mitigate | **CLOSED** | Same evidence as T-14-10. The trigger surface widened (`_airline_card_html():747-753` now emits `<a href="/airlines?resolve={prefix}">` for every prefixed card); the route's gate, method restriction and CSRF posture are byte-identical and unmodified by this phase. |
| T-14-26 | Tampering (duplicate state) | low | mitigate | **CLOSED** | `render():1796-1804` — `injected_names` set plus the `airline_name not in curated_names` test bounds injection to one card per distinct name. Verified empirically: two prefixes (`XQZ`, `XQY`) resolving to the identical name produce exactly **one** card; a manual entry naming an already-curated airline (`Air France`) produces **zero** extra cards. The accepted "first-prefix-wins" limitation was independently confirmed non-lossy: `?resolve=XQZ` still renders a real delete form with `action="/airlines/manual-resolutions/XQZ/delete"`. |
| T-14-27 | Repudiation | low | accept | **CLOSED — accepted risk logged** (§3.6) | Removal proof re-derived at runtime: `_manual_resolutions_section_html`, `_manual_resolution_row_html`, `_manual_resolution_card_html`, `MANUAL_SECTION_HEADING`, `MANUAL_RESOLUTION_STATUS_SUPERSEDED_CLASS` all `hasattr(...) == False`. `_manual_resolution_rows()` — the function whose correctness matters — is present and green (`test_status_pages.py:7234`). |
| T-14-28 | Repudiation | medium | mitigate | **CLOSED** | `14-08-SUMMARY.md:50-124` — every coverage row D1..D10 carries an explicit typed outcome: eight `status: pass` with concrete evidence refs (network request-id log, `getComputedStyle`, `document.activeElement`, `curl` with a session cookie only), and two `human_judgment: true` rows with written `rationale` rather than a silent skip. Both human-judgment items were subsequently confirmed live by the developer (`14-VERIFICATION.md` frontmatter, `developer_confirmed: 2026-09-06`). |
| T-14-SC | Tampering (supply chain) | medium (plan 01) / n/a (plans 02-07) | mitigate (01) / accept (02-07) | **CLOSED — accepted risk logged** (§3.7) | **Independently confirmed accurate.** `git diff --stat f12ab47..HEAD` for `*requirements*.txt`, `*requirements*.in`, `package.json`, `package-lock.json`, `pyproject.toml`, `Pipfile*`, `poetry.lock`, `yarn.lock`, `*.toml`: **empty**. No tracked path matching `venv\|node_modules\|site-packages`. The network-free route was the one taken: `server/.venv` is a symlink to the main checkout's venv, and the only `.gitignore` change is the root-anchored `/server/.venv` pattern that covers it. Zero packages installed in this phase. |

### 1.2 Post-plan code-review findings (5 entries)

Each was re-derived independently from current source and, where possible, exercised. The `14-REVIEW.md` `resolved` label was **not** taken as evidence.

| ID | Category | Severity | Disposition | Status | Independent evidence |
|----|----------|----------|-------------|--------|----------------------|
| CR-01 | Tampering (UI integrity, spoofing-adjacent) | critical | mitigate | **CLOSED** | `style.css:4354` — `.lightbox__image:not([hidden])` carries the `display: block`. The review's own conditional caveat was checked and is **not** needed: `.lightbox--wide .lightbox__image` (`:4438`) declares `width`/`max-width`/`max-height`/margins and **no** `display`, so it cannot re-defeat the UA `[hidden]` rule. Swept the full set of elements `panel-lookup.js` sets `.hidden` on, not just the one named: `.lightbox__replace`/`.lightbox__resolve-name`/`.lightbox__delete` (`:4497-4499`) and `.lightbox__replace-zone`/`.resolve-upload-zone` (`:4536-4537`) are scoped; `.resolve-context` (`:2646`, `resolveContext.hidden = !count`) declares **margin only, no `display`**, so the UA rule applies unimpeded. No unscoped sibling remains. |
| WR-01 | Tampering (CSS selector injection) | **medium** (see note) | mitigate | **CLOSED** | `panel-lookup.js:350-351` — `document.querySelector('[data-view-panel-resolve-prefix="' + CSS.escape(resolveValue) + '"]')`. This is the file's **only** dynamically-constructed selector (all other 20 `querySelector` calls use string literals — verified by grep), so the fix covers every entry point, not just the one the review named. The surrounding `try/catch` still fails closed (`autoTrigger = null`) if `CSS` were ever unavailable. |
| WR-02 | Tampering (TOCTOU race) | medium | mitigate | **CLOSED on its named vector — invariant overclaimed, see §4.1** | `_gap_rows_for_grid(state_dir, manual_registry=None)` (`:837, :915-918`) and `render():1745-1749` — the registry is resolved once and threaded into both `_manual_resolution_rows()` and `_gap_rows_for_grid()`, so the two sets that produced the "prefix visible in neither block" failure are guaranteed to observe one snapshot. That specific divergence is genuinely closed. |
| WR-03 | DoS (unhandled crash) | medium | mitigate | **CLOSED** | `_gap_card_html():972-973` — `if not isinstance(example_callsign, str): example_callsign = str(example_callsign)` executes before `.lower()`. Exercised: a `poll_state.json` holding `example_callsign` as a dict and as an int, with `first_seen` as an int/`None` and `last_seen` as a list/`True`, renders without raising and with clean escaped output. `prefix.lower()` needs no guard — it is a `json.load()` object key, always `str`. The review's out-of-scope claim for `health_page.unresolved_rows()` was checked and holds: no `.lower()`-shaped call on that field there. |
| WR-04 | Tampering (state consistency) | low | mitigate | **CLOSED** | `render():1794-1795` — `if not superseded and not manual_resolutions.illustration_key_for_name(airline_name): continue`. The review also asked for the same check inside `_gap_rows_for_grid()`'s exclusion condition; that was deliberately **not** done, and the load-bearing justification was verified rather than accepted: `server/plane/manual_resolutions.py:277-279` — `load_manual_resolutions()` drops any entry whose `illustration_key_for_name(...)` is `None`, on **every** load, so an unkeyable entry can never reach either function through the codebase's one real loader. `server/` is untouched by this phase, so that behaviour is pre-existing and stable. The `render()` guard is genuine defence-in-depth, correctly characterised. |

> **Note on WR-01's severity.** `14-REVIEW.md` classified it as a "warning"/"defect" without a severity rating and asked this audit to assign one. Assessed **medium**, not high: exploitation requires luring an already-authenticated single operator to a crafted link on their own session-gated page; the payload reaches only `document.querySelector()`, never a markup sink; `openFromTrigger()` on a wrongly-matched element reads absent attributes that all fall back to `""` via the `attr || ""` idiom; the auto-open path performs no network request and mutates no state; and `SameSite=Strict` is intact. Worst realistic case is an unwanted, mostly-blank modal — UI confusion, not disclosure or write. It is closed either way, so this rating does not affect `threats_open`.

---

## 2. Severity-filtered gate

`block_on: high` ⇒ only `high` and `critical` **open** threats count.

- Open threats at severity ≥ high: **0**
- Open threats below threshold: **0**
- No threat in the register lacks a parseable severity, so the fail-closed rule was not invoked.

**`threats_open` = 0. This phase is not blocked from shipping by the threat register.**

---

## 3. Accepted risks log

Entries required for every `accept` disposition.

### 3.1 T-14-08 — `EXPECTED_CHECK_COUNT` arithmetic (Repudiation, low)
A hand-maintained running comment could misstate how many checks a harness contains. **Accepted** because the count is not merely commentary: both harnesses hard-gate on `total == EXPECTED_CHECK_COUNT` and exit non-zero otherwise, so a wrong value produces a loud failure, never a silently-shrunk suite. Verified at HEAD: 163/163 and 63/63 against the stated constants.

### 3.2 T-14-11 — superseded note names both airline names (Information Disclosure, low)
`MANUAL_SUPERSEDED_NOTE_TEMPLATE` renders the operator's own stored name beside the built-in one. **Accepted:** this is a single-operator site; both strings are already visible to the same session elsewhere on the same page, so the note adds explanation, not disclosure. The whole surface is behind `require_session()`. Escaped once at each of the four interpolation points (verified with hostile input).

### 3.3 T-14-14 — `style.css` is global (Information Disclosure, low)
Any rule added here is served to every page. **Accepted:** independently verified that the phase's added CSS declares no `content:`, no `url()`, no `attr()`, and no new custom property — it receives no state and therefore can leak none. The rule set is pinned to UI-SPEC's exhaustive inventory by a green harness check.

### 3.4 T-14-18 — raw sighting values in `data-view-panel-*` attributes (Information Disclosure, low)
`first_seen`/`last_seen`/`count` are copied verbatim (unformatted) into trigger attributes rather than through `layout.concise_timestamp_html()`. **Accepted:** identical values, differently formatted, are already shown by `_resolve_context_html()` and Health's registry table to the same session-gated operator. Escaped once at interpolation like every other value.

### 3.5 T-14-23 — more specific rejection reason (Repudiation, low)
`FLASH_KEY_MANUAL_NAME_UNUSABLE` tells the operator *why* a typed name was rejected. **Accepted:** the message is a fixed server-authored constant that states a requirement in user terms and never echoes the rejected value back; it discloses nothing `add_entry()`'s unchanged validation had not already computed.

### 3.6 T-14-27 — removal of six rendering functions and eight constants (Repudiation, low)
Deleting code loses its history in the working tree. **Accepted:** `_manual_resolution_rows()`, the one function whose correctness matters, is untouched and covered; only retired *rendering* functions and their bespoke copy were removed, and their absence is proven at runtime by an exhaustive `hasattr` scan (re-derived independently for this audit).

### 3.7 T-14-SC — package installs (Tampering, medium in plan 01 / n/a in plans 02-07)
Plan 01 disposed this `mitigate` (prefer the network-free symlink; if `pip` runs at all, only the two already-pinned in-repo requirements files); plans 02-07 disposed it `accept` as not applicable. **Both hold, and the stronger claim was verified:** the phase installed nothing. No dependency-manifest file of any shape changed between `f12ab47` and HEAD, no vendored dependency path is tracked, and `server/.venv` is a symlink to the main checkout's existing venv — the network-free route. No `[ASSUMED]`/`[SUS]` package exists, so no legitimacy checkpoint applies.

---

## 4. Warnings — unregistered flags

None of the eight SUMMARY files contains a `## Threat Flags` section (`grep -l "Threat Flags" *.md` → no match). The executor therefore surfaced no new attack surface during implementation, and the following were found only afterwards. All six are **closed in code**; they are recorded here because the plan-time register did not anticipate them, which is a real adequacy gap in the phase's threat modelling.

### 4.1 WR-02's shipped invariant is narrower than the one claimed — `unregistered_flag`
The WR-02 fix's docstring (`airlines_page.py:892-909`), the commit message `ad186c7`, and `14-VERIFICATION.md` Truth #6 all assert that `render()` reads `manual_resolutions.json` **once**. Instrumenting the loader shows that is not what shipped:

- `GET /airlines` with one superseded card → **2** reads: `page_context()` (`app.py:911`) + `_airline_card_html()` (`airlines_page.py:698`, once **per superseded card**).
- `GET /airlines?resolve={prefix}` → **3** reads: the two above plus `_resolve_section_html()` (`airlines_page.py:1546`).

The *named* failure mode (a prefix rendered in neither the gap block nor the grid) is genuinely closed, because the gap-exclusion set and the injection set now share one dict by construction. The residual divergences are benign — a concurrent delete between reads 1 and 3 makes the superseded note fall back to the card's display name via the existing `or airline_name`; between reads 1 and 2 it makes the no-JS fallback section disagree with the grid for one render, self-correcting on reload. **Not a blocker** (WR-02 is medium, below the `high` threshold, and closed on its named vector), but the documented invariant should be corrected to match the code, or `_airline_card_html()`/`_resolve_section_html()` should take the threaded registry the way `_gap_rows_for_grid()` now does.

### 4.2 CR-01 was a genuinely new threat, not a registered one — `unregistered_flag`
The register has no threat for "author-origin CSS `display` beats the UA stylesheet's `[hidden] { display: none }`". Plan 14-05 introduced the `.hidden`-toggling mechanism that depends on this, and registered T-14-19 (empty-`src` network call) and T-14-21 (markup sinks) for that same code — neither covers the cascade. Plan 14-08 registered only T-14-28. The class was first found on-glass (commit `73b2fd4`, four sibling selectors), then CR-01 caught the fifth. **The original register had a real gap here**, and it is the most consequential of the six: the sibling instance caused a gap-mode dialog to display the replace form, the delete form and the resolve-name form *simultaneously*, which is spoofing-adjacent — an operator could submit against a control the mode was supposed to have hidden.

### 4.3 WR-01 was a genuinely new threat, not a registered one — `unregistered_flag`
Plan 14-05's trust-boundary table explicitly names the `location.search → querySelector` boundary and then reasons only about markup ("never written into markup, never used to construct a URL"). T-14-20 covers the same component but declares a *semantic* property (no client-side re-validation), not a syntactic one. **Selector injection was not a category anyone modelled** — the register treated "not a markup sink" as equivalent to "safe sink".

### 4.4 WR-02 was a genuinely new threat, not a registered one — `unregistered_flag`
No plan in this phase modelled concurrency at all, despite `companion/app.py` being a `ThreadingHTTPServer` with no lock around `manual_resolutions.json`. TOCTOU on shared mutable state is absent from all eight threat models.

### 4.5 WR-03 was a genuinely new threat, not a registered one — `unregistered_flag`
T-14-16 covers `_gap_card_html()`'s interpolation points for *escaping* only. No threat covered type-safety or an unhandled crash on the same untrusted JSON values, even though the module's own established posture treats a hand-edited state file as an anticipated threat elsewhere.

### 4.6 WR-04 is adjacent to a registered threat, but a different property — informational
T-14-26 (low, `mitigate`) covers the same function and the same loop, but declares "at most one injected card per distinct name, never a curated name" — not key-validity. Closest to a register hit of the five, yet still a distinct property. Its fix is correct and its non-extension into `_gap_rows_for_grid()` is properly justified (§1.2).

**Adequacy verdict:** four of the five post-plan findings (CR-01, WR-01, WR-02, WR-03) were threat classes **absent** from the plan-time register, not instances of registered threats that slipped. The register was thorough on the categories it chose — stored XSS, DOM-id integrity, route authorization, supply chain — and blind to three others that the phase's own new mechanisms introduced: **CSS-cascade-defeats-`[hidden]`, selector injection, and cross-thread state races**. Future phases touching JS-driven visibility toggling, dynamic selectors, or shared JSON state should carry threats for these explicitly.

---

## 5. Files audited

- `companion/pages/airlines_page.py`
- `companion/pages/health_page.py` (unchanged this phase — confirmed against the diffstat)
- `companion/app.py`
- `companion/auth.py` (unchanged this phase — confirmed absent from the diffstat)
- `companion/static/panel-lookup.js`
- `companion/static/list-filter.js`
- `companion/static/style.css`
- `companion/test_status_pages.py`, `companion/test_view_pages.py`, `companion/test_companion_app.py`
- `server/plane/manual_resolutions.py` (read-only, to verify WR-04's load-bearing claim; `server/` untouched by this phase)
- `.gitignore`

_Audited: 2026-09-06 — gsd-security-auditor, ASVS L1, `block_on: high`_
