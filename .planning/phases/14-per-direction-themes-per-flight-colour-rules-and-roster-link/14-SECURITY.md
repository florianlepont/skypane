---
phase: 14
slug: per-direction-themes-per-flight-colour-rules-and-roster-link
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
register_authored_at_plan_time: true
created: 2026-09-06
---

# Phase 14 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register consolidated from the `<threat_model>` blocks of `14-01-PLAN.md` through
`14-05-PLAN.md` (15 distinct threat IDs, several appearing in more than one plan).
Every row below was verified against the shipped code at HEAD, not against plan or
summary prose. Where a plan named a specific test as the proof, that test was located
and executed.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| authenticated operator → `POST /settings/rules/add` → `colour_rules.add_rule()` | Free-typed rule key + submitted kind + submitted theme id become durable state consulted on every poll cycle | Untrusted strings (callsign / ICAO24 hex / 3-letter prefix), theme id |
| request URL path segments → `POST /settings/rules/{kind}/{value}/delete` | Two request-controlled path segments identify a stored registry entry | Untrusted strings used as registry keys |
| `rule=` query parameter → rendered flash message | An operator-supplied value is echoed back into an authenticated HTML page | Untrusted string into HTML |
| authenticated operator → `POST /settings` → `save_device_config(theme_arriving=…)` | A submitted theme id becomes durable config read on every arrival render | Theme id (closed set) |
| hand-edited / corrupted `colour_rules.json` / `device_config.json` → loaders | Both files are operator-inspectable in `state_dir` and hold no secret | Arbitrary JSON |
| `state_dir` JSON → `run_once()` → `render.build_canvas(theme_id=…)` | Durable state decides what the physical panel renders | Resolved theme id |
| two concurrent `ThreadingHTTPServer` request threads → one JSON file | Add and delete are both immediate POST routes | Whole-file read-modify-write |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-14-01 | Tampering | rule-key allowlist (write + read + delete route) | high | mitigate | Three compiled positive-allowlist regexes (`server/plane/colour_rules.py:79,85,87`) reached through the single `normalise_rule_value()` entry point (`:176-192`); applied before persisting (`:318-320`), re-applied on every read (`:256-259`), and applied to both delete-route path segments before any registry lookup (`companion/app.py:1647-1652`, 404 on failure) and before the `rule=` echo is re-derived (`app.py:1612-1618`) | closed |
| T-14-02 | Tampering / Repudiation | registry write path + mid-cycle mutation | medium | mitigate | Module-level `_WRITE_LOCK` (`colour_rules.py:114`) wraps the **entire** load-check-mutate-write sequence in both mutators (`:326-355`, `:376-398`), not just the final `os.replace()`; temp filename embeds `os.getpid()` + `threading.get_ident()` (`:341`, `:384`). Registry loaded exactly once per poll cycle by the priming call (`server/poll_loop.py:749`) | closed |
| T-14-03 | Tampering (of displayed information) | resolver placement in `run_once()` | high | mitigate | Resolver invoked at exactly the two flight-displaying call sites, immediately before each `build_canvas()` (`poll_loop.py:1152`, `:1237`); never hoisted — `effective_theme_id` is a default assignment at `:773` with an explicit comment forbidding resolution there. Verified counts hold exactly: `theme_id=theme_id` == 4, `theme_id=effective_theme_id` == 2 | closed |
| T-14-04 | Denial of Service | registry growth | medium | mitigate | `COLOUR_RULE_MAX_ENTRIES = 200` (`colour_rules.py:58`); hard reject on a new key at the cap, replace explicitly exempt (`:328-331`); bounded read stops accumulating at the cap (`:253-255`); route surfaces it as the registry-full flash (`app.py:1621-1622`) | closed |
| T-14-05 | Tampering | theme-id membership, three gates | high | mitigate | `normalise_rule_theme_id()` (`colour_rules.py:195-204`) applied before persisting (`:322`), on every read (`:263`), and the resolver re-checks membership on **every** return path before handing a value back (`:498`, `:503`, `:507`, falling back to `DEFAULT_THEME_ID` at `:509`). 14-03's `transfer` of this row to 14-01 is honoured: no second gate exists at the `build_canvas()` call sites, and none is needed | closed |
| T-14-06 | Tampering | `theme_arriving` write validation | high | mitigate | Two independent lines, both present: `config_page.handle_post()` membership test against `device_config.THEME_IDS` before the value leaves the HTTP layer (`companion/pages/config_page.py:1546-1550` → `FLASH_SAVE_FAILED`, nothing written), and `save_device_config()`'s own `ValueError` before the file is touched (`server/device_config.py:663-664`) | closed |
| T-14-07 | Denial of Service | corrupt-file never-raises contract | low | mitigate | `load_colour_rules()` catches `OSError`/`ValueError` and coerces a non-dict top level (`colour_rules.py:232-238`), guards every per-entry shape (`:260-270`); `resolve_effective_theme_id()` tolerates a non-dict cache, `None`/non-dict flight, and a `theme`-less `device_cfg` (`:480-509`); `load_device_config()` keeps the same contract with `theme_arriving` joining the normalise-on-read discipline (`device_config.py:589-606`) | closed |
| T-14-08 | Tampering | `theme_arriving` read validation | medium | mitigate | `normalise_theme_arriving()` degrades a non-member to `None` — never to `DEFAULT_THEME_ID` (`device_config.py:456-476`), wired into the read path at `:598`. Independent of the write-path gate (defence in depth behind T-14-06) | closed |
| T-14-09 | Tampering | `None`-versus-sentinel write distinction | medium | mitigate | `CLEAR_THEME_ARRIVING` is a distinct module-level `object()` (`device_config.py:111`) compared **by identity** (`:694`); `None` keeps its single meaning "carry forward" (`:699`). The HTTP layer passes the sentinel, never `None`, on the clear path (`config_page.py:1565`) | closed |
| T-14-10 | Tampering (of displayed information) | divergence between the two flight branches | high | mitigate | Both branches call the identical pure function with identically-shaped inputs from the same `current_flight` dict (`poll_loop.py:1152` vs `:1237`); `resolve_effective_theme_id()` holds no cycle-local mutable state | closed |
| T-14-11 | Tampering | `theme_arriving_enabled` checkbox branch | medium | mitigate | Explicit three-way branch: absent → clear, exact `ARRIVING_CHECKBOX_VALUE` → on, anything else → reject the whole submission (`config_page.py:1564-1569`), matching the three pre-existing checkboxes | closed |
| T-14-12 | Denial of Service (of function) | the CSS-only arrivals reveal | low | accept | Acceptance rationale re-verified in shipped code — see Accepted Risks Log ACC-14-01 | closed (accepted) |
| T-14-13 | Cross-site request forgery | the two new state-changing POST routes | medium | transfer | Transfer target verified to actually cover both new routes — see Transfer Verification below | closed |
| T-14-14 | Information disclosure / injection | `rule=` echoed into a flash message | medium | mitigate | Validate-then-display in `_resolve_flash_text()` (`companion/app.py:460-464`): the value is re-normalised through `normalise_rule_callsign()` (charset `[A-Z0-9]{2,8}`, a strict superset of the hex and prefix charsets) and falls back to the generic added copy on failure; `escape_html()` in `layout.flash_banner()` (`companion/layout.py:1044`) is the second line | closed |
| T-14-SC | Tampering (package installs) | package installs | n/a | accept | Acceptance rationale re-verified against the diff — see Accepted Risks Log ACC-14-02 | closed (accepted) |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party / existing control)*

**No open threats at any severity. `threats_open: 0` is a genuine zero, not a below-threshold filter artifact.**

---

## Transfer Verification (T-14-13)

`transfer` was not taken on trust. The declared transfer target — the site-wide session
gate plus the session cookie's `SameSite=Strict` flag — was verified to cover both new
routes specifically:

1. **Gate placement.** `do_POST()` calls `require_session()` *before* dispatching either
   new route and before any registry read or write: `companion/app.py:1967-1970`
   (`RULES_ADD_ROUTE`) and `:1977-1986` (`RULES_DELETE_ROUTE_PREFIX/SUFFIX`, whose 404
   for a non-two-segment middle also sits behind the gate).
2. **The cookie is the only auth carrier.** `_is_authenticated()` (`app.py:789-791`)
   reads the session cookie and nothing else — no header, query token, or basic-auth
   fallback exists that would bypass the SameSite protection.
3. **The flag is actually set.** `auth.session_set_cookie_header()`
   (`companion/auth.py:128-140`) emits
   `sp_session=…; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=43200` — confirmed
   by executing the function, not by reading the string literal.
4. **Behavioural proof executed.** `companion/test_companion_app.py:4045-4089` drives
   unauthenticated POSTs at both new routes and asserts a 303 to `/login` **and** that
   no `colour_rules.json` is written. Ran green (companion-app: 165/165).

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| ACC-14-01 | T-14-12 | **CSS-only arrivals reveal degrades, never breaks.** Re-verified in shipped code: both theme grids are rendered unconditionally server-side (`companion/pages/config_page.py:476-511`, second grid at `:481-483`), and `companion/static/style.css:2126-2133` only ever *hides* the second grid inside an `@supports selector(:has(*))` block. A browser without `:has()` skips the block entirely and shows both grids — denser, still selectable, still correctly submitted with scripting fully disabled. No new JavaScript file was added by this phase (`companion/static/` gained none), so form correctness gained no script dependency. Rationale holds. | gsd-security-auditor (plan-time disposition, 14-04) | 2026-09-06 |
| ACC-14-02 | T-14-SC | **Zero package installs.** Re-verified against the phase diff (`c99fd3a..HEAD`): no `server/requirements*.txt`, `package*.json`, lockfile, or `pyproject.toml` appears in the changed-file set. The one new module, `server/plane/colour_rules.py`, imports `json`, `os`, `re`, `threading`, `datetime` and `server.device_config` only. No component library, CSS framework, client script, or build step was added. The supply-chain gate is genuinely not applicable. | gsd-security-auditor (plan-time disposition, all five plans) | 2026-09-06 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Flags (WARNING — new surface with no threat mapping)

None of the five SUMMARY.md files carries a `## Threat Flags` section, so no
executor-declared flags exist to reconcile. The following surfaced during verification
and are recorded here rather than silently dropped. Neither is a blocker: both are
below the `high` block threshold and neither invalidates a declared mitigation.

| Flag | Surface | Severity | Assessment |
|------|---------|----------|------------|
| UF-14-01 | `save_device_config()`'s unguarded read-modify-write (`server/device_config.py:687-725`) now carries this phase's new `theme_arriving` field | medium | **Same threat class as T-14-02 (lost update), applied to a store no T-14-02 register row names.** T-14-02's declared mitigation site is `colour_rules.py`'s mutators (14-01) and the per-cycle priming call (14-03); `device_config.json`'s save path is outside every plan's stated scope. The gap is pre-existing (the file had no lock before Phase 14 either — confirmed independently by 14-REVIEW.md WR-02), so this phase widened an existing unguarded surface by one field rather than creating one. Two concurrent `POST /settings` requests can lose an update; no validation is bypassed and no crafted value can be persisted. Already filed as WR-02 follow-up work. |
| UF-14-02 | `colour_rules.rule_rows()` (`colour_rules.py:401-424`) and `_rule_theme_swatch_html()` (`companion/pages/config_page.py:1130-1140`) are not themselves allowlist gates | low | `rule_rows()` re-checks only `isinstance(str)`, and the swatch helper does an unguarded `device_config.THEMES[theme_id]` lookup. Both are safe **today** solely because their only production caller feeds them a registry that already passed `load_colour_rules()`'s membership gate (`companion/app.py:996` → `config_page.py:1258-1262`). Verified: a hand-edited file with an unregistered `theme_id` is dropped on read before it can reach the swatch, so no `KeyError`/500 path exists. Noted as a single-gate dependency a future caller could break, not as an open threat — T-14-05's declared read-side gate is present and is what protects it. |

---

## Residual Notes on Closed Threats

- **T-14-02 / WR-01.** `_handle_rule_delete()` (`companion/app.py:1654-1661`) computes
  `existed` from an *unlocked* `load_colour_rules()` before calling the locked
  `delete_rule()`. This was weighed rather than accepted at face value: the mutation
  itself is fully serialised inside `_WRITE_LOCK`, so a concurrent double-delete cannot
  lose an update, corrupt the file, or leave a stray temp file — the only consequence is
  a spurious "delete failed" flash for an entry that is in fact gone. That is a
  *reporting* inaccuracy at the HTTP tier, not the lost-update tampering T-14-02
  declares and mitigates, and 14-05 explicitly dispositioned the HTTP tier as
  `transfer`-to-14-01 rather than adding a second locking layer. **T-14-02 stays CLOSED**;
  the flash-accuracy race is tracked as WR-01 follow-up work.
- **T-14-06.** A non-string, unhashable `theme_arriving` (e.g. a list) reaching
  `save_device_config()` directly would raise `TypeError` from the `in THEMES` test
  rather than the documented `ValueError`. The all-or-nothing contract still holds
  (nothing is written, the file is untouched) and the HTTP layer can never produce that
  shape, since form values are always strings. Identical to the pre-existing `theme`
  check's shape — not a Phase 14 regression.

---

## Verification Method

ASVS L1 (grep-depth: mitigation present in the cited file). Depth applied per threat was
in practice higher than L1 for the four `high`-severity rows and for both non-`mitigate`
dispositions, because grep alone could not have distinguished a present-but-misplaced
control:

- **Executed proofs, not just located them.** `server/test_colour_rules.py` (27/27),
  `companion/test_config_page.py` (109/109) and `companion/test_companion_app.py`
  (165/165) were run at HEAD; every named proof check passed, including the
  20-thread concurrent-writer check (T-14-02), the hostile-input write+read sweep
  (T-14-01), the tampered-cache check (T-14-05), the byte-identical-file rejection
  checks (T-14-06), the crafted-checkbox rejection (T-14-11) and the
  unauthenticated-POST-writes-nothing check (T-14-13).
- **Behavioural spot checks against the live modules** (read-only, via
  `server/.venv/bin/python3`): `_resolve_flash_text()` was driven with nine hostile
  `rule=` payloads (`<script>alert(1)</script>`, `"><img src=x onerror=…>`,
  `../../etc/passwd`, `AFR'--`, over-long, empty, `None`) — every one degraded to the
  generic added copy, only `AFR1234`/`afr1234` reached interpolation (T-14-14);
  `resolve_effective_theme_id()` with a tampered cache entry carrying
  `theme_id="../../etc/passwd"` returned the base theme, not the crafted id (T-14-05);
  the session cookie header was emitted and inspected rather than read from source
  (T-14-13).
- **Call-site counts re-derived from the shipped file**, not from the summary's claim:
  `grep -c "theme_id=theme_id" server/poll_loop.py` == 4 and
  `grep -c "theme_id=effective_theme_id" server/poll_loop.py` == 2 (T-14-03).
- **Both non-`mitigate` dispositions were re-derived from code**, per the audit brief:
  the transfer target was traced end-to-end (see Transfer Verification) and both
  acceptance rationales were re-checked against the shipped diff (see Accepted Risks).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-06 | 15 | 15 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (ACC-14-01, ACC-14-02)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-06
