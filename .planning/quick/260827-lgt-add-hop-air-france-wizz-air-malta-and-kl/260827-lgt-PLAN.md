---
phase: quick-260827-lgt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/plane/enrich.py
  - server/plane/illustrations.py
  - server/test_enrich.py
  - server/test_illustrations.py
  - server/assets/icons/illustrations/HANDOFF.md
  - server/assets/icons/illustrations/VENDOR.md
autonomous: true
requirements: [PLANE-01, PLANE-02]
user_setup: []

must_haves:
  truths:
    - "A real HOP! Air France flight over runway 3 (callsign prefix HOP) resolves the airline name 'Air France Hop' through BOTH the adsbdb-hit path and the prefix-only fallback path, producing the identical selection key either way — with no correction-seam row, because adsbdb's own answer is already correct and current."
    - "A real Wizz Air Malta flight (callsign prefix WMT) resolves the airline name 'Wizz Air' and reaches the ALREADY-VENDORED wizz-air.png with zero new artwork — the same brand-consolidation pattern the shipped EJU -> easyJet row already uses."
    - "A KlasJet flight (callsign prefix KLJ) resolves the airline name 'KlasJet', and every document and code comment that names it states plainly that this prefix was never live-confirmed and that the carrier's ACMI/wet-lease model may mean a KLJ-prefixed callsign is rarely or never observed at Orly."
    - "Three new files appear in the machine-reported hand-off plan (illustrations.py --targets) as outstanding targets; the outstanding total goes 5 -> 8 and the target total 38 -> 41."
    - "Adding three not-yet-delivered targets leaves the full 9-harness suite, ruff, check-attribution.sh, and illustrations.py --validate green — nothing enforces a file that does not exist on disk yet."
    - "A future reader can tell from HANDOFF.md alone (a) why Wizz Air Malta gets no file of its own, (b) why HOP! Air France needs no correction-seam row when Amelia did, and (c) that KlasJet's evidence is materially weaker than every other row's."
  artifacts:
    - server/plane/enrich.py  # three new _ICAO_AIRLINE_PREFIXES rows (HOP/WMT/KLJ) with evidence comments; NO _AIRLINE_NAME_CORRECTIONS change
    - server/plane/illustrations.py  # two new _ILLUSTRATION_TARGETS primaries + one new secondary variant
    - server/test_enrich.py  # four new checks, EXPECTED_CHECK_COUNT 35 -> 39
    - server/test_illustrations.py  # one new drift guard + check 45's total 38 -> 41, EXPECTED_CHECK_COUNT 46 -> 47
    - server/assets/icons/illustrations/HANDOFF.md  # required-files counts, three coverage-caveat bullets, three new prompts, full renumber to 41
    - server/assets/icons/illustrations/VENDOR.md  # new dated subsection, outstanding record 5 -> 8, Wizz Air Malta reuse recorded as a non-outstanding item
  key_links:
    - "enrich._ICAO_AIRLINE_PREFIXES values -> illustrations.target_airline_names() (existing check 24 drift guard: a prefix value with no illustration target fails the suite — this is exactly what makes WMT -> 'Wizz Air' legal with zero new target, and HOP/KLJ illegal without one)"
    - "illustrations._ILLUSTRATION_TARGETS -> target_filenames() -> outstanding_filenames() -> HANDOFF.md prompt ordering (HANDOFF's own stated invariant: prompts are printed in --targets order)"
    - "normalise_airline_key('Air France Hop') -> 'air-france-hop' and normalise_airline_key('KlasJet') -> 'klasjet' — filenames are derived, never hand-typed"
    - "select_illustration() key matching is EXACT, never prefix-based: 'Air France Hop' and 'Air France' are two independent keys reaching two independent files"
    - "scripts/check-attribution.sh walks files on disk only — a filename named in VENDOR.md with no file behind it is not a gap"
---

<objective>
Add three new target carriers to the established D-09 hand-off machinery —
**HOP! Air France** (ICAO `HOP`), **Wizz Air Malta** (ICAO `WMT`), and
**KlasJet** (ICAO `KLJ`) — across the illustration target table, the
callsign-prefix airline resolution table, the hand-off spec, the provenance
record, and regression coverage.

Purpose: all three appear in this session's cross-check against the official
Paris Aéroport Orly airline list, and since quick task `260827-hyy` the panel no
longer needs an adsbdb hit to identify an airline —
`enrich.airline_from_callsign()` resolves the carrier straight from the ICAO
callsign prefix. This is the fourth application of a now well-established
repeatable pattern (`260827-hyy` built the seam, `260827-jz6` and `260827-kih`
each extended it); it deliberately reinvents nothing.

Output: **three** new outstanding illustration targets (`air-france-hop.png`,
`air-france-hop-atr72.png`, `klasjet.png`), **three** new prefix-table rows, and
**zero** new artwork for Wizz Air Malta — which reuses the already-vendored
`wizz-air.png`. Updated hand-off + provenance docs and five new automated
checks. **No PNG artwork is produced by this plan** — the three files are named,
specified, and reported as outstanding so the developer can generate them
externally afterward (D-09, unchanged).

## Decisions this plan implements

| ID | Decision |
|---|---|
| **QT-lgt-D-01** | **Wizz Air Malta maps to the EXISTING `"Wizz Air"` selection key — no new illustration target, no new PNG, no new filename.** `WMT` is a genuinely separate legal entity and AOC (Malta), and it gets its own prefix-table row, but its aircraft are brand-standard Wizz Air: A320/A321neo airframes in the same dark-purple/magenta livery, visually indistinguishable at this project's illustration fidelity (a flat side-profile plate — no registration text, no national flag decal that would read at this scale). This is **exactly** the shipped `EJU` -> `"easyJet"` precedent: two ICAO prefixes, one brand, one vendored asset. `wizz-air.png` already exists on disk, so this row costs nothing and closes immediately. **This call is made here, now, deliberately — it is not an open question for the executor.** Accepted consequence: a Wizz Air Malta flight's caption reads `Wizz Air`, not `Wizz Air Malta`, identical in kind to `EJU` rendering `easyJet`. |
| **QT-lgt-D-02** | **Wizz Air UK (`WUK`, IATA W9) is explicitly OUT OF SCOPE and must not be added**, as tidy-up or otherwise. It was not researched this session and no decision exists for it. A future reader adding it "for symmetry" would be inventing an unverified prefix row. |
| **QT-lgt-D-03** | HOP! Air France is filed as **`"Air France Hop"`** — the exact string adsbdb live-resolved. This is a **new evidence class for this project**: the first carrier added where adsbdb's own answer is already *correct and current*, not stale (`FPO`/`CRL`/`CCM`), not a wrong carrier (`AIA`), not absent (`KMM`), and not deliberately overridden (`JAF`). Because the resolved string and the prefix-table value are the same string, the adsbdb-hit path and the prefix-only fallback path produce an **identical** selection key by construction, and **no `_AIRLINE_NAME_CORRECTIONS` row is needed or permitted**. Live-verified 2026-08-27: `curl https://api.adsbdb.com/v0/callsign/HOP4001` returns a real route (Nantes–Lyon) with `airline_name` `"Air France Hop"`. |
| **QT-lgt-D-04** | HOP! Air France gets its **own** art, distinct from `air-france.png`, and needs a **primary + secondary** pair. `select_illustration()` matches keys exactly — `"Air France Hop"` and `"Air France"` are two independent keys, never a prefix match — and the existing `air-france.png` is a mainline A320, which looks nothing like the regional fleet. **Primary = Embraer (`air-france-hop.png`); secondary = ATR72 (`air-france-hop-atr72.png`).** Reasoning, in the same style as the Air Corsica/Transavia P-04 splits already in the table: since the 2019–2021 fold-in of HOP! into Air France's regional operation, the Embraer E-Jet fleet (E170/E175/E190) is the structurally permanent and numerically dominant type while the ATR turboprops have been progressively withdrawn, and the E-Jet is the type on the Orly-relevant regional trunk routes. **Confidence: MEDIUM** — this is a judgment call on relative fleet size, not a live-verified count. It must be flagged as such in HANDOFF.md, together with the note that reversing it is a one-token change (move the `"atr72"` slug onto the primary row and give the secondary `"embraer"`), and that the D-06 Tier-2 safety net means a HOP ATR flight still gets HOP-branded art either way. |
| **QT-lgt-D-05** | KlasJet is filed as **`"KlasJet"`** (the carrier's real camel-case trading style, consistent with QT-kih-D-06's real-current-name rule). `normalise_airline_key()` slugs `"KlasJet"` and `"Klasjet"` identically to `klasjet`, so the **filename is unaffected by the casing choice** — the only consumer of the exact casing is the rendered caption string. Single primary file, **Boeing 737-800** (`b737` bucket via `B738`). |
| **QT-lgt-D-06** | **KlasJet's entry carries a materially lower confidence than every other row in either table, and every place that names it must say so.** The `KLJ` prefix is corroborated by lookup sources but was **NOT live-confirmed**: approximately 25 adsbdb queries across plausible flight-number ranges all returned `"unknown callsign"` — zero live confirmation, which is *weaker* evidence than `KMM`'s confirmed-negative (a specific curl of a specific real callsign). KlasJet is a Lithuanian ACMI/wet-lease and VIP charter operator, and wet-lease flights typically broadcast the **contracting** airline's callsign rather than the operator's own, so a real `KLJ`-prefixed callsign may rarely or never appear in this project's live detections at Orly. **The developer explicitly chose to include it anyway, with this uncertainty in hand.** It must not be presented with the same confidence as the other two. |
| **QT-lgt-D-07** | **No `_AIRLINE_NAME_CORRECTIONS` row is added for any of the three prefixes.** HOP needs none (adsbdb is already correct — QT-lgt-D-03). KLJ needs none (nothing resolves at all). WMT needs none: if adsbdb resolves a `WMT` callsign to some string other than `"Wizz Air"`, that is **not a misattribution** — it is a correct-but-more-specific answer, the same accepted-divergence class as `JAF`/TUIfly Belgium (QT-jz6-D-02), and is documented as an accepted consequence, not corrected. Task 1 asserts the absence of all three rows as a machine-checked guard so a future reader cannot silently "complete the job". |
| **QT-lgt-D-08** | KlasJet's illustrated airframe (737-800) is the most plausible **scheduled-passenger-shaped** choice among its fleet (737-300/500/800 plus Boeing Business Jets). A BBJ/VIP-configured aircraft would not visually match a standard 737-800 plate. This is **surfaced as an open question for the developer at generation time** in the HANDOFF prompt, not resolved unilaterally here. |
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

@server/plane/enrich.py
@server/plane/illustrations.py
@server/test_enrich.py
@server/test_illustrations.py
@server/assets/icons/illustrations/HANDOFF.md
@server/assets/icons/illustrations/VENDOR.md
</context>

<interface_context>
Verified against the live tree immediately before planning — treat these as
facts, do not re-derive or re-litigate them:

- **Current totals: 38 targets, 5 outstanding.** `--outstanding` prints, in
  target order: `km-malta-airlines.png`, `tuifly-belgium.png`, `amelia.png`,
  `royal-air-maroc-embraer.png`, `amelia-embraer.png`.
- `wizz-air.png` **already exists on disk** and is already a delivered,
  digest-recorded target. QT-lgt-D-01 therefore adds **zero** work to the
  artwork backlog.
- `illustrations._ILLUSTRATION_TARGETS` is a list of
  `(resolved_airline_name, shape_slug_or_None, note)` tuples. Current layout:
  **25 primary entries** (`shape=None`), then a trailing
  `# --- P-04 secondary-variant files for mixed-fleet airlines ---` block of
  **5 entries**. `target_filenames()` walks it in list order, then appends one
  `generic-{shape}.png` per `SHAPE_SLUGS` (7), then `generic-fallback.png`.
- `target_airline_names()` de-duplicates by name, so the two `"Air France Hop"`
  rows (primary + secondary) contribute **one** name. Adding `WMT` -> `"Wizz Air"`
  contributes **no** new name, because `"Wizz Air"` is already a target name.
- `required_filenames()` = the pre-3.1 baseline ∪ *only those* `target_filenames()`
  entries already on disk. **Adding a target for a file that does not exist
  cannot fail `--validate` or the suite.** `_validate_directory()` only prints
  `OUTSTANDING <name>` lines and a count (`strict_targets` is False by default).
- `_validate_directory()` also fails on any `.png` on disk that is *not* in
  `target_filenames()`. Adding targets can only ever relax that check.
- `select_illustration()` key matching is **exact**: `normalise_airline_key()`
  produces a whole slug and `illustration_path_for_key()` joins it directly.
  There is no prefix/substring matching anywhere, so `"Air France Hop"` can
  never collide with or shadow `"Air France"`.
- `enrich._ICAO_AIRLINE_PREFIXES` currently holds **26 rows**. Evidence comments
  come in three one-line forms (`# callsign XXXNNNN`, `# airline endpoint XXX`,
  `# cited callsign XXXNNN`) plus a multi-line block-comment form used by `EJU`,
  `KMM`, `JAF` and `AIA` — **the block form is the precedent to follow for all
  three new rows**, since each needs real explanation, not a one-line citation.
- `_AIRLINE_PREFIX_SHAPE_RE` is `^[A-Z]{3}[A-Z0-9]+$`. `HOP`, `WMT` and `KLJ`
  are all admissible keys with no regex change. A **bare** three-letter string
  with no flight-number suffix deliberately does not resolve — test callsigns
  must carry a suffix.
- `test_enrich.py` check **24** asserts
  `set(_ICAO_AIRLINE_PREFIXES.values()) ⊆ set(illustrations.target_airline_names())`.
  This is what makes `WMT` -> `"Wizz Air"` legal with no new target, and makes
  the `HOP`/`KLJ` rows load-bearing on their illustration targets. **Land
  `enrich.py` and `illustrations.py` in the same commit.**
- `test_enrich.py` check **32** asserts, for every `_AIRLINE_NAME_CORRECTIONS`
  row, that `_ICAO_AIRLINE_PREFIXES[prefix]` equals the corrected value. This
  plan adds no corrections row, so that invariant is untouched.
- There is **no** assertion anywhere on the row count of
  `_ICAO_AIRLINE_PREFIXES` — verified by grep. Adding rows needs no counter bump.
- Both harnesses gate on a module-level `EXPECTED_CHECK_COUNT`
  (`test_enrich.py` = **35**, `test_illustrations.py` = **46**) and fail if the
  actual count differs.
- `test_illustrations.py` check **45** hardcodes `if len(targets) != 38`. This
  **will** fail on any target addition and must be updated in the same commit —
  it is the one pre-existing check this plan is required to edit rather than
  merely extend.
- `scripts/check-attribution.sh` enumerates **files found on disk** under
  `server/assets/` and requires each to be named in some `VENDOR.md`. It never
  performs the reverse check — naming a not-yet-delivered filename in
  `VENDOR.md` is safe and is exactly the discipline HANDOFF.md prescribes.
- HANDOFF.md's prompt sections are `### N. \`filename.png\` (optional note)`,
  currently numbered **1–38**, and the file explicitly claims "Prompts below are
  grouped in the same order `--targets` prints them." **This invariant currently
  holds** — verified by diffing the extracted heading filenames against
  `--targets` output before planning. Task 2 must keep it holding.
- `_TYPE_SHAPE_BUCKETS` already maps every designator these three carriers need:
  `E170`/`E190`/`E175` (`E75L`/`E75S`) -> `embraer`; `AT42` family
  (`AT43`/`AT45`/`AT46`) and `AT72` family -> `atr72`; `B738` -> `b737`;
  `A20N`/`A21N`/`A320`/`A321` -> `a320`. **No table value changes** — comment
  extensions only.
- `render._TYPE_DISPLAY_LABELS` already labels every one of those designators
  (verified: `E170`, `E190`, `AT43`–`AT46`, `AT72`–`AT76`, `B738`). **No change
  to `render.py` is needed or permitted.**
- Test runner: `scripts/run-all-tests.sh` (9 harnesses under coverage,
  `fail_under=75`). Lint is separate: `server/.venv/bin/ruff check .`.
- No change to `render.py`, `poll_loop.py`, or `detect.py` is needed or
  permitted.
</interface_context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wire all three carriers into the illustration target table and the ICAO-prefix airline table, with regression coverage</name>
  <files>server/plane/illustrations.py, server/plane/enrich.py, server/test_illustrations.py, server/test_enrich.py</files>
  <behavior>
    - `illustrations.target_airline_names()` contains `"Air France Hop"` and `"KlasJet"`.
    - `illustrations.target_airline_names()` still contains `"Air France"` and `"Wizz Air"`, as two names distinct from the above — asserted as Python value membership, never as a text search over any source file.
    - `illustrations.target_airline_names()` does **not** contain a separate Wizz Air Malta entry, and `target_filenames()` contains no Malta-specific Wizz filename — the QT-lgt-D-01 reuse guard, asserted as Python value membership.
    - `illustrations.target_filenames()` contains `"air-france-hop.png"`, `"air-france-hop-atr72.png"` and `"klasjet.png"`, and its length is **41**.
    - `illustrations.outstanding_filenames()` has length **8**; all three new filenames are members and none of them exists on disk.
    - `enrich.airline_from_callsign("HOP4001")` returns `"Air France Hop"`.
    - `enrich.airline_from_callsign("WMT1234")` returns `"Wizz Air"` (prefix-only lookup, so any shape-valid `WMT` suffix behaves identically).
    - `enrich.airline_from_callsign("KLJ123")` returns `"KlasJet"`.
    - No `_AIRLINE_NAME_CORRECTIONS` key exists whose prefix element is `HOP`, `WMT` or `KLJ` (QT-lgt-D-07 guard).
    - The pre-existing drift guard (test_enrich check 24) still passes: every prefix-table value is a `target_airline_names()` member.
    - The pre-existing shape guard (test_enrich check 25) still passes: all three new keys are exactly 3 uppercase A–Z characters.
    - The pre-existing cross-table invariant (test_enrich check 32) still passes, untouched.
  </behavior>
  <action>
Land all four files in **one commit** — test_enrich check 24 makes the `enrich.py` and `illustrations.py` halves mutually load-bearing, and test_illustrations check 45's hardcoded total makes the harness edit load-bearing on the target edit. Splitting would leave a red intermediate state.

**1. `server/plane/illustrations.py` — three new `_ILLUSTRATION_TARGETS` entries.**

Two primaries go at the **end of the primary block**, immediately after the
`"Amelia"` primary entry and **before** the
`# --- P-04 secondary-variant files for mixed-fleet airlines ---` comment.
Introduce them under a new section comment naming this quick task
(`260827-lgt`) and the date, matching the existing
`# --- Quick task 260827-jz6 (2026-08-27): two new target airlines ---` style.
Use the multi-line tuple form the long-note entries use.

- `("Air France Hop", None, <note>)` — primary, Embraer (QT-lgt-D-04). The note
  must state: that this is the **first** target added where adsbdb's own
  resolution is already correct and current, not stale, not a wrong carrier and
  not absent; the exact live evidence (2026-08-27, `curl` against
  `https://api.adsbdb.com/v0/callsign/HOP4001`, returning a real route
  Nantes–Lyon with `airline_name` `"Air France Hop"`); that the adsbdb-hit path
  and the prefix-only fallback path therefore produce an identical selection key
  by construction and **no correction-seam row exists or is needed**
  (QT-lgt-D-03/D-07); that the ADS-B callsign string really is `HOP`+number even
  though the spoken ATC radio callsign is "Airfrans" — radio phraseology is
  irrelevant to this project, which matches on the ADS-B callsign field; that
  this key is deliberately **distinct** from `"Air France"` and reaches its own
  file, because `select_illustration()` matches keys exactly and the mainline
  A320 art does not represent the regional fleet; and that the livery is the
  post-2019 Air France mainline white/blue scheme with small `HOP` titling, not
  the pre-2019 standalone brightly-coloured HOP! livery. Carry a
  `[VERIFIED-CALLSIGN]` verdict token — the existing token for this evidence
  class, since the callsign genuinely resolved.
- `("KlasJet", None, <note>)` — primary, Boeing 737-800 (QT-lgt-D-05). The note
  must record QT-lgt-D-06 in full and prominently: the `KLJ` prefix is
  corroborated by lookup sources but was **never live-confirmed** — roughly 25
  adsbdb probes across plausible flight-number ranges all returned
  `"unknown callsign"`, i.e. zero live confirmation, which is *weaker* evidence
  than `KMM`'s confirmed-negative (a specific real callsign, curled, that
  definitively missed); that KlasJet is a Lithuanian ACMI/wet-lease and VIP
  charter operator whose wet-lease flights typically broadcast the
  **contracting** airline's callsign rather than its own, so a real
  `KLJ`-prefixed callsign may rarely or never be observed at Orly; and that the
  developer chose to include it anyway with that uncertainty in hand. Carry a
  new, deliberately distinct verdict token — use `[UNCONFIRMED-PREFIX]` — chosen
  precisely because none of the four existing tokens
  (`[VERIFIED-CALLSIGN]`, `[VERIFIED-AIRLINE-ENDPOINT-ONLY]`,
  `[VERIFIED-CALLSIGN-MISS]`, `[VERIFIED-CALLSIGN-STALE-NAME-OVERRIDDEN]`, and
  `[CITED: ...]`) honestly describes "corroborated by reference sources, never
  observed live". Do **not** reuse `[VERIFIED-CALLSIGN-MISS]`, which means
  something stronger and different.

One secondary goes at the **end of the secondary block**, after the
`("Amelia", "embraer", ...)` entry:

- `("Air France Hop", "atr72", <note>)` — the P-04 mixed-fleet secondary. The
  note must state that the ATR42/ATR72 turboprop fleet is the minority type
  alongside the Embraer primary, cross-reference the primary entry's evidence
  rather than repeating it, and record QT-lgt-D-04's **MEDIUM** confidence on
  the primary/secondary split explicitly — including that reversing it is a
  one-token change (swap which row carries the shape slug) and that D-06's
  Tier 2 means a HOP ATR flight still reaches HOP-branded art either way.

Also extend the module docstring with a short closing paragraph for
`260827-lgt`, recording (a) the new "adsbdb already correct" evidence class HOP
introduces and why it needs no correction-seam row, and (b) that Wizz Air Malta
was **deliberately not** given a target of its own, pointing at the `EJU` /
`easyjet.png` precedent. Do not rewrite existing docstring sections — append.

Cosmetic, one line each, no table values change: extend the airline lists in the
`_TYPE_SHAPE_BUCKETS` `# Embraer E-Jet family (...)`, `# ATR72 (...)` and
`# B737 family (...)` comments to mention Air France Hop (twice) and KlasJet.

**2. `server/plane/enrich.py` — three new `_ICAO_AIRLINE_PREFIXES` rows.**

Append all three after the existing final `"AIA": "Amelia",` row, under a new
block comment naming this quick task and the date, each row preceded by its own
block comment in the same shape as the existing `EJU`/`KMM`/`JAF`/`AIA` entries.

- `"HOP": "Air France Hop"` — comment cites the exact command run
  (`curl https://api.adsbdb.com/v0/callsign/HOP4001`, 2026-08-27) and its exact
  outcome (a real resolved route, Nantes–Lyon, `airline_name`
  `"Air France Hop"`). It must state clearly that this is the **first** row in
  this table whose value agrees with adsbdb's live answer *because adsbdb is
  already right*, not because it was corrected and not because adsbdb is silent
  — and that this is precisely why **no `_AIRLINE_NAME_CORRECTIONS` row exists
  for `HOP`, and none should be added** (QT-lgt-D-07). Note that the ADS-B
  callsign field really is `HOP`+number regardless of the "Airfrans" radio
  callsign.
- `"WMT": "Wizz Air"` — comment records QT-lgt-D-01 in full: Wizz Air Malta is a
  separate legal entity and AOC from `WZZ` (main Wizz Air, IATA W6, already in
  this table), holding IATA `W4` since its 2022 reassignment to the Malta AOC;
  it is mapped to the parent brand's name **deliberately**, because the fleet
  (A320/A321neo) and livery are brand-standard and this project vendors exactly
  one asset per brand — the identical rationale as the `EJU` row above, which
  the comment should name explicitly as the precedent. Record the accepted
  consequence: the caption renders `Wizz Air`, not `Wizz Air Malta`. Also record
  QT-lgt-D-02: **Wizz Air UK (`WUK`) is out of scope and must not be added as
  tidy-up** — it was never researched and no decision exists for it. Note that
  the Paris Aéroport list's `Wizz Air Hungary Ltd / W4` labelling is very likely
  an airport-side error, since `W4` belongs to the Malta AOC today.
- `"KLJ": "KlasJet"` — comment records QT-lgt-D-06 in full and **must not
  present this row with the confidence the rows above it carry**. State: the
  prefix is corroborated by lookup sources but was **never live-confirmed**;
  approximately 25 adsbdb queries across plausible flight-number ranges all
  returned `"unknown callsign"`; this is materially weaker than `KMM`'s
  confirmed-negative; KlasJet is a Lithuanian ACMI/wet-lease and VIP charter
  operator and wet-lease flights typically broadcast the contracting airline's
  callsign, so a real `KLJ`-prefixed callsign may rarely or never appear at
  Orly; and the developer chose to include it anyway. Add an explicit remediation
  pointer: if a real `KLJ` callsign is ever observed and resolves to a different
  carrier, this row is the first thing to re-verify.

All three rows are pure static-table data. **Do not touch**
`_AIRLINE_NAME_CORRECTIONS`, `correct_airline_name()`,
`apply_airline_name_correction()`, `airline_from_callsign()`,
`_AIRLINE_PREFIX_SHAPE_RE`, `airline_only_route()`, `lookup_route()` or
`resolve_route()`.

**3. `server/test_enrich.py` — four new checks.**

Add checks **36–39** at the end of the check list, immediately before the
`total = len(results)` block, following the file's exact
`def _name(): ... return True, ""` + `check("<description>", _name)` convention
with a numbered lead comment each.

- **36:** `airline_from_callsign("HOP4001") == "Air France Hop"`. Lead comment
  notes this is the real callsign curled this session and that adsbdb resolves
  the same string, so both paths agree.
- **37:** `airline_from_callsign(<a WMT callsign>) == "Wizz Air"`. Before writing
  it, run one `curl` against `https://api.adsbdb.com/v0/callsign/` for a `WMT`
  callsign to obtain a **real** one that resolves, and use that exact callsign in
  both this check and the `enrich.py` evidence comment, recording what adsbdb
  actually returned. If no `WMT` callsign can be confirmed live in this session,
  fall back to the shape-valid synthetic `WMT1234` and say **explicitly** in the
  lead comment that it is synthetic and why — do not imply a live confirmation
  that did not happen. Either way the lead comment records QT-lgt-D-01: the
  expected value is the parent brand name, deliberately.
- **38:** `airline_from_callsign("KLJ123") == "KlasJet"`. The lead comment must
  state plainly that `KLJ123` is a **synthetic, shape-valid** callsign, that no
  real `KLJ` callsign could be confirmed live (QT-lgt-D-06), and that this check
  therefore proves only that the table row is wired correctly — not that the
  prefix assignment itself is correct.
- **39:** QT-lgt-D-07 guard. Assert that no key of
  `enrich._AIRLINE_NAME_CORRECTIONS` has `HOP`, `WMT` or `KLJ` as its prefix
  element (the keys are `(prefix, airline_name)` tuples). Written as Python
  value inspection over the imported table, **not** as a text search over any
  source file. Lead comment states this is the guard that keeps a future reader
  from "completing the job" by adding correction rows none of these three needs.

Bump `EXPECTED_CHECK_COUNT` from 35 to **39**.

**4. `server/test_illustrations.py` — one edit and one new check.**

- **Edit check 45** (`_amelia_targets_present_and_total_is_38`): change its
  hardcoded expected total from 38 to **41**, and update both its failure
  message and its `check(...)` description text so they name 41. Rename the inner
  function accordingly. Its Amelia assertions stay exactly as they are.
- **Add check 47** immediately after check 46, mirroring check 44's structure.
  It must assert, against `ill.target_airline_names()`, that `"Air France Hop"`
  and `"KlasJet"` are present, and that `"Air France"` and `"Wizz Air"` are
  *also* still present as distinct names (the exact-match guard for
  QT-lgt-D-04's separate-key claim). It must assert, against
  `ill.target_filenames()`, that `air-france-hop.png`,
  `air-france-hop-atr72.png` and `klasjet.png` are all present and that none of
  them exists on disk yet. And it must assert the **QT-lgt-D-01 reuse guard**:
  no member of `target_airline_names()` is a Malta-specific Wizz variant, and no
  member of `target_filenames()` is a Malta-specific Wizz filename — implement
  this by checking that no name in either list, other than the exact `"Wizz Air"`
  entry and `wizz-air.png`, starts with the Wizz brand token, so a future
  accidental `wizz-air-malta.png` target fails this check. All assertions are
  Python value membership over the imported module's return values, never a text
  search over a source file.

Bump `EXPECTED_CHECK_COUNT` from 46 to **47**.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_enrich.py &amp;&amp; server/.venv/bin/python3 server/test_illustrations.py &amp;&amp; test "$(server/.venv/bin/python3 server/plane/illustrations.py --targets | wc -l | tr -d ' ')" = "41" &amp;&amp; test "$(server/.venv/bin/python3 server/plane/illustrations.py --targets | grep -cE '^(air-france-hop|air-france-hop-atr72|klasjet)\.png$')" = "3" &amp;&amp; test "$(server/.venv/bin/python3 server/plane/illustrations.py --outstanding | wc -l | tr -d ' ')" = "8" &amp;&amp; server/.venv/bin/python3 -c "import sys; sys.path.insert(0,'.'); from server.plane.enrich import airline_from_callsign as a, _AIRLINE_NAME_CORRECTIONS as C; from server.plane.illustrations import target_airline_names as t, target_filenames as f; assert a('HOP4001')=='Air France Hop', a('HOP4001'); assert a('WMT1234')=='Wizz Air', a('WMT1234'); assert a('KLJ123')=='KlasJet', a('KLJ123'); assert not [k for k in C if k[0] in ('HOP','WMT','KLJ')], 'unexpected correction row'; n=t(); assert 'Air France Hop' in n and 'KlasJet' in n and 'Air France' in n and 'Wizz Air' in n, n; assert [x for x in n if x.lower().startswith('wizz')]==['Wizz Air'], n; assert [x for x in f() if x.startswith('wizz')]==['wizz-air.png'], f(); print('lgt-tables-OK')" &amp;&amp; server/.venv/bin/ruff check .</automated>
  </verify>
  <done>
`test_enrich.py` reports 39/39 and `test_illustrations.py` reports 47/47.
`--targets` prints 41 filenames including all three new ones; `--outstanding`
prints exactly 8. `airline_from_callsign()` returns the three expected names.
No correction row exists for `HOP`/`WMT`/`KLJ`. `"Wizz Air"` is the sole Wizz
target name and `wizz-air.png` the sole Wizz target filename. `ruff check .` is
clean. All four files are in one commit.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend the D-09 hand-off spec and the provenance record to cover the three new targets and the one deliberate reuse</name>
  <files>server/assets/icons/illustrations/HANDOFF.md, server/assets/icons/illustrations/VENDOR.md</files>
  <action>
Both documents currently assert totals Task 1 just made false. Every edit below
is either a correction of a now-stale count or an addition at the same detail
level as the surrounding entries — do not restructure either file, and do not
touch the Phase 3/3.1, `260827-jz6` or `260827-kih` historical records except
where a count is explicitly superseded.

**A. `HANDOFF.md` — required-files list.**

- Header paragraph: append a sentence recording that quick task `260827-lgt`
  (2026-08-27) added two further carriers with art plus one that reuses existing
  art, taking the plan from 38 to 41 files. Leave the earlier history sentences
  intact — this file is cumulative.
- `## Required files (38 total, 8 already vendored)` -> `41 total, 8 already vendored`.
- `**Airline primary files (25)**` -> `(27)`, and append two lines to that
  fenced block in the same aligned style: `air-france-hop.png` (pointer:
  `see Coverage caveat — Embraer primary, MEDIUM confidence on the split`) and
  `klasjet.png` (pointer: `see Coverage caveat — lower-confidence entry`).
  Neither carries an asterisk; both are new.
- `**Airline secondary-variant files (5)**` -> `(6)`, and append
  `air-france-hop-atr72.png` with a one-line description matching the style of
  the existing rows (Air France Hop's minority ATR turboprop, alongside the
  Embraer primary).
- Leave the neutral-fallback count (8) untouched.
- **Do not add any Wizz Air Malta line to any of these three blocks** — it is
  deliberately not a file (QT-lgt-D-01), and adding one would contradict Task 1's
  check 47.

**B. `HANDOFF.md` — Coverage caveat section.** Add three new bullets, in the
same voice and detail level as the existing `EJU` / KM Malta / TUIfly Belgium /
Amelia bullets:

- **Air France Hop (`HOP`) is a new target (`air-france-hop.png` primary +
  `air-france-hop-atr72.png` secondary).** State that this is the **first**
  carrier this project has added where adsbdb's own resolution is already
  correct and current — cite the live evidence (2026-08-27,
  `curl https://api.adsbdb.com/v0/callsign/HOP4001`, real route Nantes–Lyon,
  `airline_name` `"Air France Hop"`) — and that it consequently needs **no**
  correction-seam row, unlike Amelia and unlike the three renamed carriers. Say
  explicitly why it does not share `air-france.png`: `select_illustration()`
  matches keys exactly, so `"Air France Hop"` and `"Air France"` are two
  independent keys, and the mainline A320 plate does not represent the regional
  fleet. State the livery target: post-2019 Air France mainline white/blue with
  small `HOP` titling — **not** the pre-2019 standalone brightly-coloured HOP!
  scheme. Then flag QT-lgt-D-04's split honestly: Embraer primary / ATR72
  secondary is a **MEDIUM-confidence** judgment on relative fleet size, not a
  live-verified count; reversing it is a one-token change in
  `_ILLUSTRATION_TARGETS`; and either way D-06's Tier 2 means a HOP flight of the
  non-primary type still gets HOP-branded art.
- **Wizz Air Malta (`WMT`) shares `wizz-air.png` with `WZZ` — no separate file is
  requested.** Place this bullet adjacent to the existing `EJU`/`EZY` bullet and
  name that bullet as the precedent it follows. Record: `WMT` is a genuinely
  separate legal entity and AOC (Malta), holding IATA `W4` since its 2022
  reassignment; its fleet (A320/A321neo) and livery are brand-standard Wizz Air,
  visually indistinguishable at this project's flat side-profile fidelity; so it
  gets its own prefix-table row and **zero** new artwork. Record the accepted
  consequence: the caption renders `Wizz Air`, not `Wizz Air Malta` — the same
  accepted consequence `EJU` already carries. Record QT-lgt-D-02 explicitly:
  **Wizz Air UK (`WUK`) is out of scope, was never researched, and must not be
  added as tidy-up.** Note in passing that the Paris Aéroport list's
  `Wizz Air Hungary Ltd / W4` labelling is very likely an airport-side error.
- **KlasJet (`KLJ`) is a new target (`klasjet.png`) carrying materially lower
  confidence than every other entry in this document.** This bullet must not
  read like the others. State: the prefix is corroborated by lookup sources but
  was **never live-confirmed** — roughly 25 adsbdb queries across plausible
  flight-number ranges all returned `"unknown callsign"`, which is *weaker*
  evidence than KM Malta's confirmed-negative, not equivalent to it; KlasJet is a
  Lithuanian ACMI/wet-lease and VIP charter operator, and wet-lease flights
  typically broadcast the **contracting** airline's callsign rather than the
  operator's own, so a real `KLJ`-prefixed callsign may rarely or never actually
  appear in this project's detections at Orly; and the developer chose to include
  it anyway with that uncertainty in hand. Add the remediation pointer: re-verify
  this row first if a `KLJ` flight is ever observed with a surprising caption.

**C. `HANDOFF.md` — three new prompt sections, and a full renumber.** The file
states prompts appear in `--targets` order. Task 1 placed the two primaries at
the end of the primary block and the secondary at the end of the secondary
block, so the resulting order is: new **#26** `air-france-hop.png` and **#27**
`klasjet.png` inserted after the current #25 (`amelia.png`); the current #26–#30
secondaries shift to **#28–#32**; new **#33** `air-france-hop-atr72.png`
inserted after them; and the current #31–#38 generics shift to **#34–#41**.
Insert, then renumber every affected heading. Write all three prompts at the
same level of detail as the surrounding ones, reusing the file's fixed closing
boilerplate verbatim (nose pointing LEFT / transparent background with real
alpha / no ground, sky or shadow / clean flat illustration style, crisp hard
edges, vintage aviation poster plate):

- `air-france-hop.png` — an **Embraer E190** in the post-2019 Air France
  regional livery: white fuselage, Air France dark-blue tail, red/white/blue
  accents, small `HOP` titling. The heading must state that this is the
  post-2019 Air France mainline scheme with HOP titling, explicitly **not** the
  pre-2019 standalone brightly-coloured HOP! livery, so the generator does not
  produce the retired brand's art. Add a short note that this file is
  deliberately distinct from `air-france.png` (which is the mainline A320) and
  must show the regional jet.
- `klasjet.png` — a **Boeing 737-800** in KlasJet livery: white fuselage with an
  abstract light-blue/yellow tail design. Include **two** explicit notes, in the
  same style as the existing `amelia.png` LIVERY CONFIDENCE NOTE: (1) the livery
  description is **lower confidence** than this project's other entries — check
  it against a real photo before generating; and (2) **an open question for the
  developer to resolve at generation time** (QT-lgt-D-08): KlasJet's fleet mixes
  737-300/500/800 with Boeing Business Jets, and a BBJ/VIP-configured airframe
  would not visually match a standard 737-800 plate — the 737-800 was chosen as
  the most plausible scheduled-passenger-shaped option, but the developer should
  make the final call. Do not resolve this question in the document.
- `air-france-hop-atr72.png` — an **ATR 72-600** in the same Air France regional
  livery, matching `air-france-hop.png`'s colours on the turboprop airframe
  instead of the regional jet, in the same "matching {primary}'s ..." phrasing
  the other secondary prompts already use.

**D. `VENDOR.md` — coverage records.**

- Add a new `### Quick task 260827-lgt (2026-08-27) — two new targets with art,
  one carrier deliberately sharing existing art` subsection after the
  `260827-kih` subsection. It records: target count **38 -> 41**; outstanding
  count **5 -> 8**; the full current 8-file outstanding list by name; a
  per-file table for the three new targets (filename / airline / aircraft type /
  livery, with the confidence qualifier stated inline for `klasjet.png` and for
  the HOP primary/secondary split); the live-curl evidence for `HOP` and for
  whichever `WMT` callsign Task 1 actually confirmed (or an explicit statement
  that none was confirmed this session, if that is what happened); and the
  QT-lgt-D-06 record for `KLJ` — never live-confirmed, ~25 probes all missing,
  ACMI/wet-lease caveat, included by explicit developer choice.
- In that same subsection, record **Wizz Air Malta as a non-outstanding item**:
  a new `WMT` prefix-table row that maps to the existing `"Wizz Air"` target and
  reuses the already-vendored, already-digest-recorded `wizz-air.png`, adding
  **zero** files to the backlog (QT-lgt-D-01), plus the QT-lgt-D-02 out-of-scope
  note for `WUK`. Make it unambiguous that this is a deliberate reuse, not an
  omission.
- Update the `## Coverage note` section's Wizz Air / easyJet material (if it
  states a per-brand asset count or enumerates which prefixes share an asset) so
  it does not contradict the new `WMT` row. Make the minimum edit that removes
  the contradiction; do not rewrite the section.
- Update the `260827-kih` subsection's "outstanding count 3 -> 5" line only to
  the extent of appending a forward pointer to the new subsection for the
  current project-wide total of 8, exactly as `260827-jz6`'s subsection already
  points forward to `260827-kih`. Keep each subsection accurate to its own
  scope — do not retroactively rewrite historical counts.
- **Do not add sha256 or dimension rows for any of the three new files** —
  none exists. `wizz-air.png`'s existing digest row is already correct and must
  not be touched.
- Do not touch `server/assets/icons/VENDOR.md` (the parent), which records only
  the Phase 3 baseline eight.
  </action>
  <verify>
    <automated>diff &lt;(grep -oE '^### [0-9]+\. `[^`]+`' server/assets/icons/illustrations/HANDOFF.md | sed -E 's/.*`([^`]+)`.*/\1/') &lt;(server/.venv/bin/python3 server/plane/illustrations.py --targets) &amp;&amp; test "$(grep -oE '^### [0-9]+\.' server/assets/icons/illustrations/HANDOFF.md | grep -oE '[0-9]+' | tr '\n' ' ')" = "$(seq 1 41 | tr '\n' ' ')" &amp;&amp; for f in air-france-hop.png air-france-hop-atr72.png klasjet.png; do grep -qF "$f" server/assets/icons/illustrations/HANDOFF.md || { echo "HANDOFF missing $f"; exit 1; }; grep -qF "$f" server/assets/icons/illustrations/VENDOR.md || { echo "VENDOR missing $f"; exit 1; }; done &amp;&amp; grep -qF '41 total' server/assets/icons/illustrations/HANDOFF.md &amp;&amp; for d in HANDOFF VENDOR; do grep -qiE 'wizz air malta|WMT' "server/assets/icons/illustrations/$d.md" || { echo "$d missing the WMT reuse record"; exit 1; }; grep -qiE 'klasjet' "server/assets/icons/illustrations/$d.md" || { echo "$d missing KlasJet"; exit 1; }; done &amp;&amp; scripts/check-attribution.sh &amp;&amp; server/.venv/bin/python3 server/plane/illustrations.py --validate &amp;&amp; echo DOCS-OK</automated>
  </verify>
  <done>
HANDOFF.md's 41 prompt headings are numbered 1–41 with no gaps and their
filenames match `--targets` output line-for-line. All three new filenames appear
in HANDOFF.md and VENDOR.md; both documents record the Wizz Air Malta reuse and
KlasJet by name. The required-files header reads 41 total.
`check-attribution.sh` passes (it walks disk files only, so the three
named-but-undelivered PNGs are correctly not a gap) and `--validate` exits 0
while reporting 8 outstanding targets.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full-gate verification and developer hand-off report</name>
  <files>(no source edits — verification and reporting only)</files>
  <action>
Run the project's three canonical gates end to end and confirm nothing
regressed: `scripts/run-all-tests.sh` (all 9 harnesses under coverage,
`fail_under=75`), `server/.venv/bin/ruff check .`, and
`scripts/check-attribution.sh`. Confirm the enrich harness reports 39/39 and the
illustrations harness 47/47 **in the aggregate run output**, not just in
isolation — the aggregate run is what CI executes.

If coverage drops below the 75 floor, do **not** lower the floor. Three static
table rows, three target entries and five checks should not move coverage
measurably; a real drop means something else changed and must be investigated
before commit.

Then produce the hand-off report in the SUMMARY, since the artwork is the
developer's next real-world action and this environment cannot produce it:

- the exact **three** filenames to generate, with their target directory
  (`server/assets/icons/illustrations/`);
- the aircraft type and livery for each, with the confidence qualifiers stated,
  not smoothed over: the HOP primary/secondary split is MEDIUM confidence
  (QT-lgt-D-04), and `klasjet.png`'s livery description plus its 737-800-vs-BBJ
  airframe question are both open for the developer's judgment (QT-lgt-D-06,
  QT-lgt-D-08);
- an explicit statement that **Wizz Air Malta needs no artwork** — it reuses the
  already-vendored `wizz-air.png` (QT-lgt-D-01) — so the developer does not go
  looking for a fourth file;
- the copy-pasteable commands the developer runs after dropping files in:
  `--outstanding`, then `--validate`, then `--outstanding` again, then the
  by-eye nose-left and type-matches-filename confirmation, exactly as
  HANDOFF.md's "After generating the files" section prescribes;
- a reminder that the outstanding list is now **8** files, not 3, since
  `royal-air-maroc-embraer.png` (Phase 3.1), `km-malta-airlines.png` /
  `tuifly-belgium.png` (`260827-jz6`) and `amelia.png` / `amelia-embraer.png`
  (`260827-kih`) were all already outstanding before this task.

Record in the SUMMARY that no PNG artwork was generated, faked, or placed by
this task, and that `render.py`, `poll_loop.py` and `detect.py` were
deliberately untouched.

**Surface, do not silently fix:** if anything discovered while running these
gates contradicts this plan's research — in particular if a live `WMT` or `KLJ`
lookup turns out to be an adsbdb *misattribution* (a populated result naming a
different carrier, the Amelia/Avies failure mode) rather than the accepted
divergence or plain miss this plan assumes — record it in the SUMMARY as a
**finding** with the evidence. Do **not** add an `_AIRLINE_NAME_CORRECTIONS` row
beyond what QT-lgt-D-07 specifies; that is a separate decision for the developer.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh &amp;&amp; server/.venv/bin/ruff check . &amp;&amp; scripts/check-attribution.sh &amp;&amp; test "$(server/.venv/bin/python3 server/plane/illustrations.py --outstanding | LC_ALL=C sort | tr '\n' ' ')" = "air-france-hop-atr72.png air-france-hop.png amelia-embraer.png amelia.png klasjet.png km-malta-airlines.png royal-air-maroc-embraer.png tuifly-belgium.png "</automated>
  </verify>
  <done>
All 9 harnesses pass in the aggregate run with `enrich: 39/39` and
`illustrations: 47/47` visible in its output; coverage is at or above 75.
`ruff check .` and `scripts/check-attribution.sh` both pass. `--outstanding`
lists exactly the eight expected filenames. The SUMMARY carries the developer
hand-off report, the explicit "Wizz Air Malta needs no artwork" note, the
confidence qualifiers, and an explicit statement that no artwork was produced.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| aggregator → `detect.py` → `enrich.airline_from_callsign()` | An attacker-influenced or malformed ADS-B `flight`/callsign string crosses into the static prefix-table lookup. |
| resolved `airline_name` → `illustrations.normalise_airline_key()` → filesystem path | An airline-name string reaches path construction under `ILLUSTRATION_DIR`. |
| rendered panel → the developer's own eyes | The panel asserts a real-world carrier identity for a real, physical aircraft overhead. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-lgt-01 | Tampering | `illustrations.illustration_path_for_key()` fed the two new `_ILLUSTRATION_TARGETS` airline names | low | mitigate | Both new names are plain ASCII and slug to `air-france-hop` / `klasjet`. No new code path is introduced — the existing `_UNSAFE_KEY_RE` boundary in `illustration_path_for_key()` and `test_illustrations.py`'s pre-existing `^[a-z0-9-]+\.png$` assertion over the whole of `target_filenames()` both cover the three new entries automatically. Task 1's verify runs that harness. |
| T-lgt-02 | Spoofing | `enrich.airline_from_callsign()` — hostile callsign reaching the three new prefix rows | low | mitigate | No change to the lookup function, its `_AIRLINE_PREFIX_SHAPE_RE` gate, or `normalise_callsign()`. The function still can only ever return a fixed table value or `None`, never anything derived from its argument (T-hyy-01, preserved). `test_enrich.py` check 25 (unchanged) asserts all three new keys are exactly 3 uppercase A–Z characters. |
| T-lgt-03 | Spoofing | **`KLJ` prefix assignment is unverified** — if the prefix is actually held by a different carrier, a real flight would be captioned `KlasJet` and shown KlasJet art (an Amelia/Avies-class wrong-carrier attribution, but with this project as the source of the error rather than adsbdb) | medium | mitigate | Genuinely bounded rather than eliminated. Bounded because no `KLJ`-prefixed callsign has ever been observed in this project's traffic (~25 adsbdb probes all missed), so the row is very unlikely to fire at all. Mitigation is **documentary and deliberate**: QT-lgt-D-06's uncertainty is recorded in `enrich.py`, `illustrations.py`, `HANDOFF.md` and `VENDOR.md`, each carrying an explicit re-verify-this-row-first remediation pointer, and `illustrations.py` gives it a distinct `[UNCONFIRMED-PREFIX]` verdict token so it can never be mistaken for a live-verified row. A future wrong caption is therefore immediately traceable to this known-weak entry instead of presenting as a fresh mystery. |
| T-lgt-04 | Repudiation | Brand consolidation on the panel — a real **Wizz Air Malta** aircraft captioned `Wizz Air` | low | **accept** | Explicit developer-scoped decision (QT-lgt-D-01), made with the tradeoff stated, and identical in kind to the already-shipped and already-accepted `EJU` → `easyJet` consolidation. This is never a wrong-carrier claim: the brand is correct, the livery shown is genuinely the aircraft's own, and only the legal-entity granularity is dropped. Recorded in `enrich.py`, `HANDOFF.md` and `VENDOR.md` so it cannot be mistaken for a defect, and guarded by Task 1's check 47 so it cannot be silently "corrected" into a spurious Malta-specific target. |
| T-lgt-05 | Spoofing | A generated PNG misrepresenting a carrier — the retired pre-2019 standalone HOP! livery landing under `air-france-hop.png`, or a BBJ/VIP airframe under `klasjet.png` | medium | mitigate | Task 2's prompt sections name the current livery explicitly and name the superseded HOP! scheme as the thing **not** to produce; `klasjet.png`'s prompt carries both a lower-confidence livery note and the explicit 737-800-vs-BBJ open question (QT-lgt-D-08) rather than an unearned assertion. HANDOFF.md's existing "After generating the files" step 4 already requires the developer to confirm type-matches-filename by eye before the file is recorded in `VENDOR.md`. |
| T-lgt-06 | Tampering | A future reader adding an `_AIRLINE_NAME_CORRECTIONS` row for `HOP`/`WMT`/`KLJ` as tidy-up, silently changing selection behaviour for a carrier that needs no correction | low | mitigate | Task 1's check 39 asserts the absence of all three rows as a machine-checked guard, and check 32's pre-existing cross-table invariant would fail loudly if such a row disagreed with the prefix table. QT-lgt-D-07's rationale is recorded in `enrich.py` beside each row. |
| T-lgt-SC | Tampering | npm/pip/cargo installs | n/a | **accept** | No package-manager install is in scope — no dependency is added, removed, or upgraded. `server/requirements.txt` and `server/requirements-dev.txt` are not touched, so the Package Legitimacy Gate does not apply and no blocking human checkpoint is required. |
</threat_model>

<verification>
1. `server/.venv/bin/python3 server/test_enrich.py` → `enrich: 39/39 checks pass`.
2. `server/.venv/bin/python3 server/test_illustrations.py` → `illustrations: 47/47 checks pass`.
3. `scripts/run-all-tests.sh` → all 9 harnesses pass, coverage ≥ 75.
4. `server/.venv/bin/ruff check .` → clean.
5. `scripts/check-attribution.sh` → PASS (unchanged asset-file count; the three
   named-but-undelivered PNGs are correctly not counted, because the script
   walks disk files only).
6. `server/plane/illustrations.py --validate` → exits 0, reports
   `8 outstanding target file(s)`.
7. `server/plane/illustrations.py --targets | wc -l` → 41.
8. HANDOFF.md prompt headings 1–41, in `--targets` order (diff-verified).
9. `airline_from_callsign()` returns `Air France Hop` / `Wizz Air` / `KlasJet`
   for `HOP` / `WMT` / `KLJ` callsigns, with zero network call.
10. `_AIRLINE_NAME_CORRECTIONS` has no row for any of the three prefixes.
11. `"Wizz Air"` is the only Wizz name in `target_airline_names()` and
    `wizz-air.png` the only Wizz filename in `target_filenames()` — the
    QT-lgt-D-01 reuse holds and no Malta-specific target crept in.
</verification>

<success_criteria>
- Three new prefix rows (`HOP`, `WMT`, `KLJ`) resolve their intended airline
  names with zero network call, each carrying an evidence comment honest about
  its own confidence level.
- Three new outstanding illustration targets exist (`air-france-hop.png`,
  `air-france-hop-atr72.png`, `klasjet.png`); the target total is 41 and the
  outstanding total is 8.
- Wizz Air Malta reaches the already-vendored `wizz-air.png` with **zero** new
  artwork, and both documents state that this is deliberate.
- KlasJet's lower confidence and ACMI/wet-lease caveat are stated in `enrich.py`,
  `illustrations.py`, `HANDOFF.md` and `VENDOR.md` — a future reader cannot
  mistake it for a live-verified entry.
- No `_AIRLINE_NAME_CORRECTIONS` row was added, and a check now guards that.
- `render.py`, `poll_loop.py` and `detect.py` are untouched; so are KM Malta
  Airlines, TUIfly Belgium, Amelia, Air Corsica, ASL Airlines France and Corsair.
- Full 9-harness suite, `ruff check .`, `scripts/check-attribution.sh` and
  `illustrations.py --validate` all green.
- No PNG artwork was generated, faked, or placed.
</success_criteria>

<output>
Create `.planning/quick/260827-lgt-add-hop-air-france-wizz-air-malta-and-kl/260827-lgt-SUMMARY.md` when done
</output>
