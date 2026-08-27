---
phase: quick-260827-kih
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/plane/enrich.py
  - server/plane/illustrations.py
  - server/plane/render.py
  - server/test_enrich.py
  - server/test_illustrations.py
  - server/test_render.py
  - server/fixtures/README.md
  - server/fixtures/adsbdb_hit_AIA6412.json
  - server/assets/icons/VENDOR.md
  - server/assets/icons/illustrations/HANDOFF.md
  - server/assets/icons/illustrations/VENDOR.md
  - server/assets/icons/illustrations/ccm-airlines.png -> air-corsica.png
  - server/assets/icons/illustrations/ccm-airlines-atr72.png -> air-corsica-atr72.png
  - server/assets/icons/illustrations/europe-airpost.png -> asl-airlines-france.png
  - server/assets/icons/illustrations/corsairfly.png -> corsair.png
autonomous: true
requirements: [PLANE-01, PLANE-02]
user_setup: []

must_haves:
  truths:
    - "A real Air Corsica / ASL Airlines France / Corsair flight displays the carrier's real current name on the panel and reaches that carrier's own illustration, whether the name came from a fresh adsbdb hit, a cached adsbdb hit, or the callsign-prefix-only fallback — all three paths produce the same string."
    - "A real Amelia flight (callsign prefix AIA) displays 'Amelia', not the defunct Estonian carrier 'Avies' that adsbdb actually returns for that prefix."
    - "An airline_name that happens to equal a corrected-away string but arrives under a different callsign prefix is left untouched — the correction is keyed on (prefix, exact string), never a blind global string replace."
    - "An already-deployed server/state/poll_state.json holding pre-correction cached names starts rendering the corrected names on the very next poll, with no cache migration, purge, or version bump."
    - "The four renamed illustration files keep their git history and their existing VENDOR.md sha256 digests — the rename changed the path, not the bytes."
    - "A future reader can tell from enrich.py, illustrations.py, HANDOFF.md and VENDOR.md alone which prior decision was superseded, by whom, and why — and that TUIfly Belgium's and KM Malta's own entries were deliberately left alone."
  artifacts:
    - server/plane/enrich.py  # _AIRLINE_NAME_CORRECTIONS + correct_airline_name() + apply_airline_name_correction(), single seam in lookup_route(); AIA row; three corrected prefix values
    - server/plane/illustrations.py  # three renamed targets, two new Amelia targets, rewritten naming-rule docstring section
    - server/fixtures/adsbdb_hit_AIA6412.json  # the recorded adsbdb response that attributes AIA to the wrong carrier
    - server/test_enrich.py  # EXPECTED_CHECK_COUNT 27 -> 35
    - server/test_illustrations.py  # EXPECTED_CHECK_COUNT 44 -> 46
    - server/test_render.py  # EXPECTED_CHECK_COUNT 41 -> 42
    - server/assets/icons/illustrations/HANDOFF.md  # 38-file plan, rewritten Naming rules, Amelia coverage, renumbered prompts
    - server/assets/icons/illustrations/VENDOR.md  # four renamed digest rows (digests carried over), dated 260827-kih subsection
  key_links:
    - "lookup_route() -> apply_airline_name_correction() — the ONE line every adsbdb-sourced route leaves through, fresh or cached; correction on read, never on write, so the persisted cache stays a faithful record of what adsbdb returned"
    - "_AIRLINE_NAME_CORRECTIONS[(prefix, stale)] == _ICAO_AIRLINE_PREFIXES[prefix] — the machine-checked invariant that proves the adsbdb path and the prefix-only fallback path agree on the same string"
    - "enrich._ICAO_AIRLINE_PREFIXES values -> illustrations.target_airline_names() (existing check 24 drift guard) — renaming a target without mirroring the prefix table fails the suite"
    - "illustrations._LIVE_RESOLVED_AIRLINES -> required_filenames() — this list is a FILENAME source, so its CCM entry must carry the corrected name or --validate demands a file that no longer exists"
    - "illustrations._ILLUSTRATION_TARGETS -> target_filenames() -> HANDOFF.md prompt ordering (HANDOFF's own stated invariant: prompt sections are printed in --targets order)"
    - "scripts/check-attribution.sh greps every on-disk asset basename against every VENDOR.md — a git mv with no VENDOR.md row rename fails the gate in the same commit"
---

<objective>
Introduce a **single, prefix-scoped, adsbdb-resolved-name correction seam** in
`server/plane/enrich.py`, and use it to make four carriers display their real
current names everywhere — on the panel caption *and* as the illustration
selection key — regardless of which of the three enrichment paths produced the
name.

Purpose: today the panel can show a real airline under a stale or outright wrong
name. `adsbdb`'s crowdsourced database still resolves `FPO` to "Europe Airpost"
(ASL Airlines France rebranded in 2015), `CRL` to "Corsairfly" (Corsair reverted
~2012), `CCM` to "CCM Airlines" (Air Corsica rebranded in 2013) — and, worse,
resolves `AIA` to **"Avies"**, a *different, defunct Estonian airline* that
happened to hold the same ICAO code before ceasing operations in 2016. A real
Amelia flight over runway 3 would today be captioned with another company's
name. That is not a stale-but-same-carrier label; it is an actively wrong claim.

Output: one correction table + one correction function applied at one seam;
four vendored illustration files renamed with `git mv`; Amelia added as a new
target airline (primary + Embraer secondary, artwork outstanding); the hand-off
and provenance docs rewritten around the new rule; and eleven new automated
checks including the three regression cases that keep the mechanism honest.

**No PNG artwork is produced by this plan.** Amelia's two files are named,
specified, and reported as outstanding for a later external generation batch
(D-09, unchanged) — the same incremental-delivery pattern quick task
`260827-jz6` used for KM Malta Airlines and TUIfly Belgium.

## Decisions this plan implements

| ID | Decision |
|---|---|
| **QT-kih-D-01** | All corrections live in **one** table, `_AIRLINE_NAME_CORRECTIONS`, keyed on the **pair** `(ICAO callsign prefix, exact airline_name string adsbdb returned)`, applied by **one** function at **one** seam inside `lookup_route()`. Not three or four ad-hoc special cases scattered through the module, and not a global string replace: the correction is conditioned on *which prefix produced the hit*, so a hypothetical unrelated carrier legitimately named by a corrected-away string, arriving under a different prefix, is never rewritten. |
| **QT-kih-D-02** | The persistent cache stores **adsbdb's raw payload**; the correction is applied **on read**, never on write. Two consequences, both deliberate: the already-deployed `server/state/poll_state.json` starts producing corrected names on the next poll with zero migration or cache purge, and the cache remains a faithful record of what the upstream API actually said. This mirrors the existing precedent that prefix resolution "is recomputed from the static table on every call" rather than cached. |
| **QT-kih-D-03** | The prefix-only fallback table `_ICAO_AIRLINE_PREFIXES` carries the **corrected** names by construction (its values are the illustration selection keys, enforced by the existing check-24 drift guard). Rather than pointlessly re-running a no-op correction over a table that already holds corrected values, a **machine-checked invariant** asserts that for every correction row, `_ICAO_AIRLINE_PREFIXES[prefix]` equals the corrected value — and that the corrected value is a member of `illustrations.target_airline_names()`. That invariant is what proves all three paths agree; adding a correction row without mirroring the prefix table fails the suite. |
| **QT-kih-D-04** | The four vendored files are renamed with `git mv` (history preserved). Their `VENDOR.md` sha256 digests and pixel dimensions are **carried over verbatim, not recomputed** — the bytes are unchanged, only the path moved. Task 3's gate re-derives the digests with `shasum -a 256` and cross-checks them against the carried-over rows, so a rename that silently altered bytes fails. |
| **QT-kih-D-05** | Amelia is filed as **"Amelia"** — the current short name on the official Paris Aéroport airline list — not "Amelia International". Primary (unsuffixed) file `amelia.png` shows an **Airbus A320** (A320-family; A319 shares the file per HANDOFF's suffix rule). Secondary `amelia-embraer.png` shows an **Embraer E145**, chosen over the E190 because the E145 is the type on Amelia's real Orly-relevant Pau service (recorded in Phase 3.1's own fleet research); the E190 shares the file per the same family rule. Livery detail (white fuselage, blue tail, lowercase wordmark) is **moderate confidence** and is flagged as such in the hand-off prompt for the developer's own judgement at generation time. |
| **QT-kih-D-06** | This **supersedes**, for `FPO`/`CRL`/`CCM` only, the Phase 3.1 P-01/D-04 naming rule, `03.1-LIVE-RESOLUTION.md`'s Step B/C naming verdicts, and quick task `260827-hyy`'s D-01 ("copy the resolved column verbatim, never retype from a brand name"). Those decisions were correct given the machinery that existed then — there *was* no correction seam, so mirroring adsbdb's string was the only way to keep selection working. This plan builds the seam that removes that constraint. The supersession is recorded in prose in `enrich.py`, `illustrations.py`, `HANDOFF.md` and `VENDOR.md`; it is never silently overwritten. |
| **QT-kih-D-07** | **KM Malta Airlines (`KMM`, QT-jz6-D-01) and TUIfly Belgium (`JAF`, QT-jz6-D-02) are out of scope and must not be changed.** TUIfly Belgium is the same failure mode as the three carriers this plan fixes and the new seam could trivially cover it — the developer explicitly chose not to, this session. HANDOFF.md must say that plainly so a future reader does not "complete the job" by adding a `JAF` row. |
| **QT-kih-D-08** | `render.py`'s P-01 `_AIRLINE_DISPLAY_ALIASES` entry is **retained unchanged** as a defensive no-op — the string it keys on can no longer reach it through the corrected seam, but a hand-built route dict still resolves correctly. Only its explanatory comment is updated to record the supersession. No rendering logic, no table value, and no existing check is altered. |
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

@server/plane/enrich.py
@server/plane/illustrations.py
@server/test_enrich.py
@server/test_illustrations.py
@server/fixtures/README.md
@server/assets/icons/illustrations/HANDOFF.md
@server/assets/icons/illustrations/VENDOR.md
</context>

<interface_context>

## Existing shapes this plan builds on (do not re-derive them)

**`enrich.lookup_route(callsign, cache, transport=None, timeout=...)`** returns a
route dict with exactly five keys — `airline_name`, `origin_iata`, `origin_city`,
`destination_iata`, `destination_city` — or `None`. It has two success paths that
must both be corrected: the cache-hit branch (`_route_from_entry(entry)`) and the
fresh-fetch branch (`_parse_route(body)`). `_parse_route()` does **not** receive
the callsign, so the correction cannot live inside it.

**`enrich.normalise_callsign(raw)`** upper-cases and strips; returns `None` for
non-strings. **`enrich._AIRLINE_PREFIX_SHAPE_RE`** (`^[A-Z]{3}[A-Z0-9]+$`) is the
shape gate `airline_from_callsign()` applies before any prefix lookup — reuse it,
do not write a second one.

**`illustrations.target_airline_names()`** de-duplicates the first element of every
`_ILLUSTRATION_TARGETS` triple. **`illustrations._LIVE_RESOLVED_AIRLINES`** is
consumed by `required_filenames()` to build the immovable on-disk baseline — it is
a *filename source*, not just a historical record.

**`illustrations._validate_directory()`** fails on any `.png` in the directory that
is not in `target_filenames()`, so a rename must land in the same commit as its
target-table entry.

**Harness convention** (all three test files): a `check(name, fn)` closure where
`fn` returns `(ok, reason)`; a module-level `EXPECTED_CHECK_COUNT` that the run
asserts against the number of checks actually registered. Adding a check without
bumping the constant fails the harness.

</interface_context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build the prefix-scoped correction seam and land Amelia through it</name>
  <files>server/plane/enrich.py, server/plane/illustrations.py, server/fixtures/adsbdb_hit_AIA6412.json, server/fixtures/README.md, server/test_enrich.py, server/test_illustrations.py</files>
  <behavior>
    - `correct_airline_name("AIA6412", "Avies")` returns `"Amelia"`.
    - `correct_airline_name("ZZZ1234", "Avies")` returns `"Avies"` unchanged — a
      different prefix carrying the same string is never rewritten.
    - `resolve_route()` against a stubbed 200 body that attributes AIA6412 to the
      wrong carrier yields a route whose `airline_name` is `"Amelia"`, source
      `"fresh_hit"`; a second call with the same cache yields `"Amelia"` again with
      source `"cache_hit"`, and the cache entry itself still holds the raw upstream
      string — proving the correction is applied on read, not on write.
    - `airline_from_callsign("AIA6412")` returns `"Amelia"` with zero network call.
    - For every `(prefix, stale) -> corrected` row, `_ICAO_AIRLINE_PREFIXES[prefix]`
      equals `corrected`, and `corrected` is a member of
      `illustrations.target_airline_names()`.
    - Both new functions never raise for `None`, an int, an empty string, a bare
      3-letter callsign, a path-separator payload, a non-dict route, or a route whose
      `.get` raises — and never return a value derived from their arguments other
      than the unchanged `airline_name` they were handed.
    - `target_filenames()` contains `amelia.png` and `amelia-embraer.png` and totals
      38 entries; `outstanding_filenames()` reports 5 files.
  </behavior>
  <action>
Record the AIA evidence first. Run `curl -s https://api.adsbdb.com/v0/callsign/AIA6412` and capture the response verbatim into `server/fixtures/adsbdb_hit_AIA6412.json`, following the wrapper convention `adsbdb_miss_EJU84YF.json` already uses (a top-level object carrying `http_status` alongside `body`) so the harness can replay both. Add a `## adsbdb_hit_AIA6412.json` section to `server/fixtures/README.md` in that file's existing house style: source URL, retrieval date, and an explicit real-vs-synthetic marking of every field. Two branches, both acceptable, neither may be skipped: if the live response still attributes the AIA prefix to the defunct Estonian carrier, mark every field real and say so; if the live response has since changed (different carrier, or a miss), record what actually came back verbatim, then additionally hand-build the minimal replay body the harness needs, mark it **synthetic** in `README.md` exactly as that file requires for invented fixtures, and note the divergence prominently in the SUMMARY — do not quietly present a hand-built body as a captured one.

In `enrich.py`, move `_AIRLINE_PREFIX_SHAPE_RE` and its explanatory comment up to sit beside `_CALLSIGN_SAFE_RE` among the module-level constants (a pure move — same pattern, same comment, no behaviour change), so the correction seam can be defined before its call site without a forward reference. Then, immediately above `lookup_route()`, add the correction seam as one clearly-marked block: a module-level dict `_AIRLINE_NAME_CORRECTIONS` mapping a two-tuple of `(three-letter ICAO prefix, the exact airline_name string the upstream API returns)` to the corrected current name, seeded with the single AIA row this task lands; a public `correct_airline_name(callsign, airline_name)` returning the mapped value or its `airline_name` argument unchanged; and a public `apply_airline_name_correction(callsign, route)` returning `route` unchanged when nothing changes, otherwise a shallow copy with the corrected `airline_name`. `correct_airline_name()` must gate the callsign through `normalise_callsign()` and `_AIRLINE_PREFIX_SHAPE_RE` before deriving any prefix, and must return non-string / falsy `airline_name` arguments untouched — so, exactly like `airline_from_callsign()`, the only strings it can ever produce are fixed table values or the argument it was given, and a hostile callsign can never reach `illustrations.py`'s path construction through this new seam.

Restructure `lookup_route()` so both success paths converge on a single `return apply_airline_name_correction(normalised, route)` at the end of the function: the cache-hit branch assigns `route = _route_from_entry(entry)` instead of returning, the fresh-fetch branch assigns `route = _parse_route(body)` and still writes the **uncorrected** payload to the cache before falling through. Every early `return None` (bad callsign, non-2xx, transport exception, unparseable body, cached miss) stays exactly as it is. Write a docstring/comment block on the seam stating: this is the one line every adsbdb-sourced route leaves through, fresh or cached (QT-kih-D-01); the cache deliberately holds the raw upstream payload so a server whose `poll_state.json` predates this change is corrected on read with no migration (QT-kih-D-02); and the prefix-only fallback path needs no call here because its table already holds corrected values, an agreement asserted by the invariant check in `test_enrich.py` rather than assumed (QT-kih-D-03).

Add the `AIA` row to `_ICAO_AIRLINE_PREFIXES` with a live-evidence comment in the same style as the existing `KMM`/`JAF` rows: the ICAO prefix is real and independently corroborated (Flightradar24 live-tracked flight 8R6412 as `8R/AIA`, plus Airhex, Wikipedia, ERAA and IATA), the upstream API *does* return a populated result for it, and that result names a different, defunct Estonian carrier that ceased operations in 2016 and whose ICAO code was never retired upstream. State plainly that this is a worse failure mode than either previously-handled one — not a stale label for the same real airline, and not a miss, but an actively wrong carrier attribution — which is why the correction is prefix-scoped and auditable rather than a string swap.

In `illustrations.py`, add two `_ILLUSTRATION_TARGETS` entries in a new dated `260827-kih` block placed immediately after the `260827-jz6` block and before the secondary-variant block: the unsuffixed primary, and — appended at the end of the existing secondary-variant group so target ordering stays stable — the `embraer` secondary. Both notes must carry the live evidence and the correction-row cross-reference. Update the two `_TYPE_SHAPE_BUCKETS` comments that currently list this carrier as excluded-pending-re-verification (the A320-family comment gains it, the Embraer comment's parenthetical exclusion is replaced by the secondary-variant cross-reference). Extend the module docstring's closing paragraph to record that this carrier is now reachable precisely because `enrich.correct_airline_name()` exists, and that the prior exclusion rationale — an untrustworthy candidate ICAO code — was retired by this session's live verification of the real one.

In `test_enrich.py`, add checks 28 through 33 exactly as enumerated in the behavior block above, in that order, following the file's existing numbered-comment + `check(name, fn)` convention, and bump `EXPECTED_CHECK_COUNT` to 33. Check 30 must assert on the cache dict directly (the stored entry still carries the upstream string) as well as on the returned route, and must count transport invocations to prove the second call was served from cache. Check 32 is the cross-table invariant and must iterate `_AIRLINE_NAME_CORRECTIONS` rather than restating its contents. In `test_illustrations.py`, add check 45 asserting both new filenames are in `target_filenames()`, both are still absent from disk, and `len(target_filenames())` is 38; bump `EXPECTED_CHECK_COUNT` to 45.

Note for the executor: this task deliberately leaves `HANDOFF.md`'s prompt numbering out of step with `--targets` — Task 3 closes that. Do not assert the HANDOFF/targets diff gate here.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_enrich.py 2>&1 | tail -3 | grep -q "enrich: 33/33 checks pass"</automated>
    <automated>server/.venv/bin/python3 server/test_illustrations.py 2>&1 | tail -3 | grep -q "illustrations: 45/45 checks pass"</automated>
    <automated>server/.venv/bin/python3 server/plane/illustrations.py --validate >/dev/null && server/.venv/bin/python3 server/plane/illustrations.py --outstanding | wc -l | tr -d ' ' | grep -qx 5</automated>
    <automated>server/.venv/bin/python3 -m ruff check . && python3 -c "import json,sys; json.load(open('server/fixtures/adsbdb_hit_AIA6412.json'))"</automated>
    <automated>scripts/run-all-tests.sh</automated>
  </verify>
  <done>`correct_airline_name()` and `apply_airline_name_correction()` exist as one documented block with one call site in `lookup_route()`; the AIA correction row, the AIA prefix row and both new illustration targets are live; the recorded fixture and its provenance entry are committed; `test_enrich.py` is 33/33 and `test_illustrations.py` 45/45; the full 9-harness suite, ruff and `--validate` are green with exactly 5 outstanding target files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Apply the seam to the three stale-brand carriers and rename their four vendored files</name>
  <files>server/plane/enrich.py, server/plane/illustrations.py, server/plane/render.py, server/test_enrich.py, server/test_illustrations.py, server/test_render.py, server/assets/icons/VENDOR.md, server/assets/icons/illustrations/VENDOR.md, server/assets/icons/illustrations/*.png (four git mv renames)</files>
  <behavior>
    - `correct_airline_name()` maps each of the three `(prefix, upstream string)` pairs
      to its real current name: the FPO pair to `"ASL Airlines France"`, the CRL pair to
      `"Corsair"`, the CCM pair to `"Air Corsica"`.
    - `resolve_route()` against a stubbed 200 body carrying each upstream string under
      its own prefix returns the corrected name; the same body served under an
      unrelated prefix returns the upstream string untouched.
    - `illustrations.select_illustration()` on a corrected CCM route plus type `A320`
      resolves to the renamed primary file, and plus type `AT72` to the renamed
      secondary — proving the correction lands *before* illustration selection.
    - `render._flight_line2_text()` on a corrected route renders the current brand name
      in the caption, and `render.display_airline_name()` is a no-op on that already-
      corrected string.
    - `target_airline_names()` contains the three current names and none of the three
      upstream strings they replace.
    - The four renamed files exist on disk under their new names; the four superseded
      filenames do not exist; `--validate` reports no unexpected file.
  </behavior>
  <action>
Add the three remaining rows to `_AIRLINE_NAME_CORRECTIONS`, each with a one-line evidence comment naming the real-world rebrand and its year, and set the three corresponding `_ICAO_AIRLINE_PREFIXES` values to the same corrected names — both edits in the same commit, because the existing check-24 drift guard and this plan's new check-32 invariant each fail the moment the two tables disagree. Rewrite the block comment above `_ICAO_AIRLINE_PREFIXES` that currently instructs the reader to copy the upstream column verbatim and never retype a brand name: it must now state that the rule held while no correction seam existed, name the three decisions it superseded (Phase 3.1 P-01/D-04, `03.1-LIVE-RESOLUTION.md`'s Step B/C naming verdicts, and quick task `260827-hyy`'s D-01), point at `_AIRLINE_NAME_CORRECTIONS` as the mechanism that replaced it, and state explicitly that `JAF` was deliberately left out of the correction table this session at the developer's direction (QT-kih-D-07) so nobody adds it as tidy-up.

In `illustrations.py`: update the three `_ILLUSTRATION_TARGETS` primary entries and the one secondary-variant entry to the corrected names, rewriting each note string to cite the correction row instead of the old stale-brand rationale. Update the `_LIVE_RESOLVED_AIRLINES` entry for the CCM callsign to the corrected name with an inline comment explaining why this list, unlike the docstring's historical live-resolution table, must carry post-correction names — it is consumed by `required_filenames()` to build the on-disk baseline, so a stale value there would demand a file that no longer exists. Leave the docstring's historical live-resolution table itself untouched: it records what the upstream API returned on a given date and remains true. Replace the docstring section that currently asserts filenames mirror the data source rather than the current brand with the new rule — filenames mirror the carrier's real current name, and where the upstream API disagrees, `enrich.correct_airline_name()` reconciles it before selection — including the supersession record, and including the explicit carve-out that TUIfly Belgium's and KM Malta's entries are unchanged and out of scope. Update the three `_TYPE_SHAPE_BUCKETS` family comments that name these carriers by their superseded strings. Update the `normalise_airline_key()` docstring's worked example to use a corrected name and its slug.

Rename the four files with `git mv` so history is preserved — the CCM primary and its ATR72 secondary, the FPO primary, and the CRL primary — to the slugs `normalise_airline_key()` derives from the corrected names. Do not open, re-encode, or otherwise touch the image bytes.

In the same commit, rename the four corresponding filename cells in `server/assets/icons/illustrations/VENDOR.md`'s per-file digest tables and update their "Airline served" cells to the current name with the superseded upstream string kept in parentheses, carrying the existing sha256 and dimension values across verbatim (QT-kih-D-04 — the bytes did not change). Rename the one filename mention in `server/assets/icons/VENDOR.md`'s summary list the same way. This must land here, not in Task 3, because `scripts/check-attribution.sh` greps every on-disk asset basename against every `VENDOR.md` and would otherwise fail on this commit.

In `render.py`, change only the comment above `_AIRLINE_DISPLAY_ALIASES`: record that `enrich.correct_airline_name()` now corrects this carrier upstream, so the entry is retained as a defensive no-op for hand-built route dicts rather than as the live presentation path, and cite QT-kih-D-08. Do not alter the dict, the function, or any rendering logic.

In `test_enrich.py` add checks 34 and 35 per the behavior block (34: the three pairs through `correct_airline_name()`; 35: end-to-end through `resolve_route()` for all three upstream strings, the negative unrelated-prefix case, and the two `select_illustration()` assertions), and bump `EXPECTED_CHECK_COUNT` to 35. In `test_illustrations.py`: rewrite the existing check 43 in place so it asserts the three current names are present in `target_airline_names()` and the three upstream strings they replace are absent — the same drift-guard shape, inverted — and rename its check label to match; update the `normalise_airline_key` slug check to the corrected name; update the P-04 primary/secondary pair list to the renamed filenames; and add check 46 asserting the four new filenames exist on disk and the four superseded ones do not. Bump `EXPECTED_CHECK_COUNT` to 46. In `test_render.py` add check 42 per the behavior block and bump `EXPECTED_CHECK_COUNT` to 42; leave the existing P-01 alias check untouched.

Note for the executor: stage everything before running the rename gate, and expect the HANDOFF/targets diff to still be out of step until Task 3.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_enrich.py 2>&1 | tail -3 | grep -q "enrich: 35/35 checks pass"</automated>
    <automated>server/.venv/bin/python3 server/test_illustrations.py 2>&1 | tail -3 | grep -q "illustrations: 46/46 checks pass"</automated>
    <automated>server/.venv/bin/python3 server/test_render.py 2>&1 | tail -3 | grep -q "render: 42/42 checks pass"</automated>
    <automated>test -f server/assets/icons/illustrations/air-corsica.png && test -f server/assets/icons/illustrations/air-corsica-atr72.png && test -f server/assets/icons/illustrations/asl-airlines-france.png && test -f server/assets/icons/illustrations/corsair.png</automated>
    <automated>test ! -e server/assets/icons/illustrations/ccm-airlines.png && test ! -e server/assets/icons/illustrations/ccm-airlines-atr72.png && test ! -e server/assets/icons/illustrations/europe-airpost.png && test ! -e server/assets/icons/illustrations/corsairfly.png</automated>
    <automated>git add -A && test "$(git diff --cached --name-status -M --diff-filter=R -- server/assets/icons/illustrations | wc -l | tr -d ' ')" = "4"</automated>
    <automated>server/.venv/bin/python3 server/plane/illustrations.py --validate >/dev/null && scripts/check-attribution.sh >/dev/null && server/.venv/bin/python3 -m ruff check .</automated>
    <automated>scripts/run-all-tests.sh</automated>
  </verify>
  <done>All four correction rows are live and mirrored in the prefix table; the four illustration files are renamed as staged renames with history preserved and their VENDOR.md rows carry the original digests; `render.py` carries a comment-only supersession note with its alias table and every existing check intact; `test_enrich.py` 35/35, `test_illustrations.py` 46/46, `test_render.py` 42/42; the full suite, ruff, `--validate` and `check-attribution.sh` are all green.</done>
</task>

<task type="auto">
  <name>Task 3: Rewrite the hand-off spec and the provenance record around the new naming rule</name>
  <files>server/assets/icons/illustrations/HANDOFF.md, server/assets/icons/illustrations/VENDOR.md</files>
  <action>
Rewrite `HANDOFF.md` so it describes the current, post-correction world. Take `server/.venv/bin/python3 server/plane/illustrations.py --targets` as the authority for every list and every ordering in this file — never hand-order anything.

Header and counts: the plan is now 38 files, up from 36; say which quick task moved it and why. Required-files lists: 25 airline primaries (the three renamed slugs in place, plus the new primary inserted in `--targets` order after the two `260827-jz6` entries), 5 secondary variants (the renamed ATR72 slug, plus the new Embraer secondary appended at the end of that group), and the unchanged 8 neutral/fallback entries. Strip the trailing "see Naming rules, do NOT rename" annotations from the three renamed entries and replace them with a pointer to the correction mechanism.

Naming rules: this section inverts. The rule is now that a filename is derived, through `normalise_airline_key()`, from the carrier's **real current name**, and that where the upstream API disagrees — because its crowdsourced database carries a pre-rebrand name, or because it attributes an ICAO code to a different, defunct carrier that once held it — `enrich.correct_airline_name()` reconciles the two before either the selection key or the caption is computed. Record the supersession explicitly: which decisions were superseded (Phase 3.1 P-01/D-04, `03.1-LIVE-RESOLUTION.md`'s Step B and Step C naming verdicts, quick task `260827-hyy`'s D-01), by which decision (QT-kih-D-06), on what date, and why they were right at the time — the seam that makes the current rule safe did not exist then. Keep the old rule's warning about what happens to selection when a filename and a selection key drift apart: that hazard is real and unchanged; what changed is that the mechanism now keeps them from drifting.

The subsection currently framed as "the one approved override" is no longer one of one. Rewrite its framing — not its substance — so TUIfly Belgium's decision (QT-jz6-D-02) is recorded intact, and add an explicit note that TUIfly Belgium is the same failure mode the new mechanism now fixes for three other carriers, that adding a `JAF` correction row was considered and deliberately excluded this session by the developer (QT-kih-D-07), and that a future reader must not add one as tidy-up. Leave KM Malta Airlines' entry and rationale untouched.

Coverage caveat: replace the exclusion entry for this task's newly added carrier with its current status — a live-verified real ICAO prefix, an upstream API that returns a populated result under a different defunct carrier's name, and a correction row that fixes it — and record that the prior exclusion rested on two candidate codes that turned out to belong to other airlines, both now retired by the real code. Leave La Compagnie's exclusion exactly as it stands.

Prompts: rename the three renamed sections' headings and filenames, insert two new sections in `--targets` order, and renumber every section below the insertion points. The resulting order is: the new primary becomes section 25; the four existing secondary variants shift to 26 through 29 (with the renamed ATR72 slug at 26); the new Embraer secondary becomes 30; the seven neutral shapes become 31 through 37; the universal fallback becomes 38. Write the two new prompts in the file's exact house style — side-profile editorial illustration, nose pointing left, transparent PNG with a real alpha channel, no ground/sky/shadow, flat vintage-poster styling — naming an Airbus A320 for the primary and an Embraer E145 for the secondary, and stating in plain words inside each prompt block's surrounding prose that the livery description (white fuselage, blue tail, lowercase wordmark) is **moderate confidence** and should be checked against a real photo before generating, per this project's established practice for unverified livery detail. Do not regenerate or restyle any other prompt.

Then rewrite `server/assets/icons/illustrations/VENDOR.md`'s narrative sections (its four renamed digest rows already landed in Task 2 — do not touch the digests again). Add a dated `### Quick task 260827-kih (2026-08-27)` subsection recording: the four `git mv` renames with old and new names side by side and the explicit statement that digests were carried over rather than recomputed because the bytes are unchanged; the correction mechanism and where it lives; the live-curl evidence for the AIA prefix and the wrong-carrier attribution it returns; the two new outstanding targets with aircraft type and livery (flagged moderate confidence); and the count movements — targets 36 to 38, outstanding 3 to 5. Update the existing coverage sections that state the older totals so no stale count survives. Update the `_unresolved/` table row for the previously-excluded carrier: the carrier itself is now a real target, but that file remains a non-selectable holding-directory artifact because its filename does not match either derived slug and its depicted aircraft type was never recorded or eye-verified as a selection target — state that the developer may promote it by `git mv` at generation time *after* confirming its type and nose orientation, or regenerate. Do not rename or move that file in this task.
  </action>
  <verify>
    <automated>T=$(mktemp); H=$(mktemp); server/.venv/bin/python3 server/plane/illustrations.py --targets > "$T"; grep -oE '^### [0-9]+\. `[^`]+`' server/assets/icons/illustrations/HANDOFF.md | sed -E 's/^### [0-9]+\. `([^`]+)`$/\1/' > "$H"; diff "$T" "$H"; rc=$?; rm -f "$T" "$H"; exit $rc</automated>
    <automated>for f in air-corsica.png air-corsica-atr72.png asl-airlines-france.png corsair.png; do d=$(shasum -a 256 "server/assets/icons/illustrations/$f" | cut -d' ' -f1); grep -qF "$d" server/assets/icons/illustrations/VENDOR.md || { echo "DIGEST-MISMATCH $f"; exit 1; }; grep -qF "$f" server/assets/icons/illustrations/VENDOR.md || { echo "ROW-MISSING $f"; exit 1; }; done</automated>
    <automated>test "$(server/.venv/bin/python3 server/plane/illustrations.py --targets | wc -l | tr -d ' ')" = "38" && test "$(server/.venv/bin/python3 server/plane/illustrations.py --outstanding | wc -l | tr -d ' ')" = "5"</automated>
    <automated>scripts/check-attribution.sh >/dev/null && server/.venv/bin/python3 server/plane/illustrations.py --validate >/dev/null</automated>
  </verify>
  <done>`HANDOFF.md`'s prompt-section headings match `--targets` line for line at 38 entries; the Naming rules section states the inverted rule plus a named supersession record and the explicit `JAF` carve-out; both new prompts exist with a moderate-confidence livery flag; `VENDOR.md` carries a dated `260827-kih` subsection, no stale target/outstanding counts, and an updated `_unresolved/` disposition; the carried-over digests still match the renamed files on disk.</done>
</task>

<task type="auto">
  <name>Task 4: Full-gate verification and developer hand-off report</name>
  <files>(no source edits — verification only)</files>
  <action>
Run every project gate in order and record the real output in the SUMMARY, never a claimed result: the canonical 9-harness runner, the linter across the repo, the attribution checker, and the illustration validator in both `--validate` and `--outstanding` modes.

Prove the renames preserved history now that they are committed: for each of the four new paths, run `git log --follow --oneline` and confirm the log reaches back past this session's commit into the file's original life under its previous name.

Prove the mechanism end to end against the real code, not just the harnesses, in a throwaway in-memory cache with no network call and nothing written to `server/state/poll_state.json`: for each of the four corrections, resolve a stubbed hit through `resolve_route()` and print the resulting `airline_name`, the file `select_illustration()` picks for it, and the caption `render._flight_line2_text()` produces. Then do the same for a route carrying a corrected-away string under an unrelated prefix and confirm it comes back untouched. Record the actual printed values in the SUMMARY.

Prove QT-kih-D-02 concretely: seed a cache dict by hand with an entry in the pre-correction shape (found, carrying the upstream string), resolve it, and show the corrected name comes out of the cached path with the stored entry itself still holding the upstream string. This is the check that a deployed server needs no cache migration.

Write the SUMMARY's developer hand-off section in the shape quick task `260827-jz6` established: state plainly that no PNG artwork was generated, faked, or placed; name the two files still needed with their aircraft type and livery description, marking the livery detail as moderate confidence for the developer's own judgement; point at the two new `HANDOFF.md` prompt sections by number; give the three post-generation commands in order; and restate the full current outstanding list of 5 files by name so the earlier batch's remaining item is not forgotten. Mention the `_unresolved/` holding-directory file as an option the developer may inspect and promote rather than regenerate, with the type/orientation confirmation that would require.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh && server/.venv/bin/python3 -m ruff check . && scripts/check-attribution.sh >/dev/null</automated>
    <automated>for f in air-corsica.png air-corsica-atr72.png asl-airlines-france.png corsair.png; do test "$(git log --follow --oneline -- "server/assets/icons/illustrations/$f" | wc -l | tr -d ' ')" -ge 2 || { echo "NO-HISTORY $f"; exit 1; }; done</automated>
    <automated>server/.venv/bin/python3 server/plane/illustrations.py --validate >/dev/null && test "$(server/.venv/bin/python3 server/plane/illustrations.py --outstanding | wc -l | tr -d ' ')" = "5"</automated>
    <automated>T=$(mktemp); H=$(mktemp); server/.venv/bin/python3 server/plane/illustrations.py --targets > "$T"; grep -oE '^### [0-9]+\. `[^`]+`' server/assets/icons/illustrations/HANDOFF.md | sed -E 's/^### [0-9]+\. `([^`]+)`$/\1/' > "$H"; diff "$T" "$H"; rc=$?; rm -f "$T" "$H"; exit $rc</automated>
  </verify>
  <done>All four gates green with recorded output; `git log --follow` proves history survived all four renames; the four corrections and the negative unrelated-prefix case are demonstrated live against `resolve_route()` + `select_illustration()` + `_flight_line2_text()` with the actual values recorded; the pre-correction-cache replay is demonstrated; the SUMMARY carries a complete 5-file hand-off report.</done>
</task>

</tasks>
<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| aggregator -> `enrich.correct_airline_name()` | The callsign is untrusted aggregator-supplied input; it is the key half of the correction lookup. |
| adsbdb -> `enrich.correct_airline_name()` | The `airline_name` string is untrusted third-party API output; it is the value half of the correction lookup. |
| corrected `airline_name` -> `illustrations.illustration_path_for_key()` | The corrected name becomes a filesystem path component through `normalise_airline_key()`. |
| repo -> vendored asset files | Four asset files change path; `scripts/check-attribution.sh` and `VENDOR.md` digests are the integrity record. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-kih-01 | Tampering | `correct_airline_name()` / `apply_airline_name_correction()` | medium | mitigate | Gate the callsign through `normalise_callsign()` + the existing `_AIRLINE_PREFIX_SHAPE_RE` before deriving any prefix, and return only a fixed table value or the caller's own `airline_name` argument — never a value derived from the callsign. Same property `airline_from_callsign()` already holds, so no attacker-controlled substring reaches `illustrations.py`'s path construction through the new seam. Proven by check 33's hostile-input battery. |
| T-kih-02 | Spoofing | adsbdb-supplied `airline_name` | medium | mitigate | Corrections are keyed on the `(prefix, exact string)` pair, never on the string alone (QT-kih-D-01). A hostile or coincidental `airline_name` arriving under a different prefix is returned untouched — proven by check 29 and by check 35's negative unrelated-prefix case. This is the difference between a principled correction and a blind global replace. |
| T-kih-03 | Tampering | the four renamed vendored PNGs | low | mitigate | `VENDOR.md` digests are carried over rather than recomputed, then Task 3's gate re-derives each file's `shasum -a 256` and requires it to appear in `VENDOR.md` — a rename that silently altered bytes fails the gate instead of quietly re-blessing new content. |
| T-kih-04 | Information disclosure | `server/fixtures/adsbdb_hit_AIA6412.json` | low | mitigate | The fixture records a public, unauthenticated third-party API response for a public flight number; it carries no credential, key, or host secret. Provenance is recorded in `server/fixtures/README.md` with an explicit real-vs-synthetic marking per that file's existing rule. |
| T-kih-05 | Denial of service | correction applied on every cache read | low | accept | A single tuple-keyed dict lookup with no I/O, recomputed per call — the same cost class as the existing per-call prefix lookup, on a poll cycle that already makes network calls. Accepted rather than cached, because caching it would reintroduce exactly the stale-value problem QT-kih-D-02 removes. |
| T-kih-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package-manager install task exists in this plan — no dependency is added, removed, or version-changed, and the existing pinned `server/requirements.txt` / `requirements-dev.txt` are untouched. The Package Legitimacy Gate does not apply. |
</threat_model>

<verification>
## Overall phase checks

1. `scripts/run-all-tests.sh` exits 0 — all 9 harnesses plus the coverage floor.
2. `server/.venv/bin/python3 -m ruff check .` exits 0.
3. `scripts/check-attribution.sh` exits 0 — every on-disk asset basename, including the four renamed ones, is named in a `VENDOR.md`.
4. `server/plane/illustrations.py --validate` exits 0 with no unexpected-file report; `--targets` lists 38 files and `--outstanding` lists exactly 5.
5. `HANDOFF.md`'s prompt-section headings diff clean against `--targets` output, line for line.
6. `git log --follow` reaches past this session for all four renamed asset paths.
7. Check counts: `test_enrich.py` 35/35, `test_illustrations.py` 46/46, `test_render.py` 42/42.

## The five required regression cases (constraint-mandated)

| # | Case | Where it lives |
|---|------|----------------|
| a | Live-hit-shaped stubs prove the three upstream stale strings are corrected before reaching illustration selection *and* caption text | `test_enrich.py` check 35 (selection) + `test_render.py` check 42 (caption) |
| b | An AIA-prefixed callsign whose upstream result names the defunct carrier is corrected | `test_enrich.py` checks 28 and 30 |
| c | The same corrected-away string arriving under a **different** prefix is NOT corrected — the override is genuinely prefix-scoped | `test_enrich.py` check 29 + check 35's negative case |
| d | The existing drift guard (prefix-table values are a subset of illustration target names) still holds after the renames | `test_enrich.py` check 24, unchanged, plus new check 32's stronger cross-table invariant |
| e | The renamed files still pass `check-attribution.sh` via updated `VENDOR.md` entries | Task 2 and Task 4 verify gates |
</verification>

<success_criteria>
- One correction table and one correction function in `enrich.py`, with exactly one call site, covering the fresh-hit, cached-hit and prefix-only paths — not scattered special cases.
- All four carriers resolve to their real current name identically through every path; the machine-checked invariant makes that agreement a test failure if it ever breaks.
- A corrected-away string under an unrelated prefix is provably left alone.
- Four illustration files renamed with `git mv`, history intact, digests carried over and re-verified.
- Amelia added as a primary + Embraer secondary target, both reported outstanding; no artwork fabricated.
- The superseded Phase 3.1 / `260827-hyy` naming decisions are cited by name in `enrich.py`, `illustrations.py`, `HANDOFF.md` and `VENDOR.md` — superseded on the record, never silently overwritten.
- KM Malta Airlines and TUIfly Belgium entries unchanged, with the `JAF` carve-out documented so a future reader does not undo it.
- `detect.py`, `poll_loop.py`, and `render.py`'s rendering logic untouched (`render.py` receives a comment-only edit).
- Full suite, ruff, and `check-attribution.sh` green at every task commit.
</success_criteria>

<output>
Create `.planning/quick/260827-kih-introduce-an-adsbdb-resolved-name-correc/260827-kih-SUMMARY.md` when done.
</output>