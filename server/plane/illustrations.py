#!/usr/bin/env python3
"""Per-airline aircraft illustration selection (D-06, D-08, D-09, D-19,
PLANE-01/PLANE-02).

Selection keys off `route["airline_name"]`, which `enrich.lookup_route()`
already returns - no new enrichment call (D-06). Coverage was originally
transitively limited by that lookup's real-world hit rate: `adsbdb`
resolved only 52.6% of this airport's traffic in Phase 2's live test
(`server/plane/enrich.py`'s module docstring). **Since quick task
260827-hyy, a confirmed adsbdb route miss no longer implies a lost airline
identity** - `enrich.airline_from_callsign()` resolves the airline directly
from the callsign's ICAO prefix as an independent fallback source, so `EJU`
(easyJet Europe) and every other rotating-callsign prefix in
`enrich._ICAO_AIRLINE_PREFIXES` reach their own illustration via this
module's normal Tier 1/2 selection even when adsbdb has nothing. The
historical hit-rate measurements above (52.6% overall, `TVF` at 2 of 20)
remain true and are preserved as-is - they describe adsbdb's own coverage,
not the panel's final airline-identification rate, which this second
source now improves.

This module makes no network call of its own - the live lookups below were
performed once, out of band, during this plan's Task 1 execution, purely to
turn the exact required illustration filenames into resolved fact instead
of a guess (03-RESEARCH.md Assumption A3 flagged that only "Transavia
France" had ever been confirmed live; the rest were inferred from carrier
names).

## Live-resolved airline names (2026-08-26, `enrich.lookup_route()` against
## `api.adsbdb.com`, throwaway in-memory cache - nothing written to
## `server/state/poll_state.json`)

| Callsign  | Resolved `airline_name` (verbatim) | Requested for art? |
|-----------|-------------------------------------|---------------------|
| AFR56XX   | "Air France"                        | yes |
| IBE05EM   | "Iberia Airlines"                   | yes |
| TAP440    | "TAP Portugal"                      | yes |
| DAH1008   | "Air Algerie"                       | yes |
| CCM21AW   | "CCM Airlines"                      | yes |
| VLG6PD    | "Vueling Airlines"                  | yes |
| TVF16VB   | "Transavia France"                  | yes — user-requested extension |
| VOE8KA    | "Volotea"                            | no - recorded for status only |

All seven original calls returned a full route (no misses among this set). VOE8KA
(Volotea) was queried per 03-RESEARCH.md's instruction to resolve its
previously-`[ASSUMED]`-unconfirmed status, not to request art for it - the
originally scoped the hand-off to the six confirmed-hit carriers plus the
generic fallback. On 2026-08-26, a user-requested extension added Transavia
France despite its sparse resolution coverage. Volotea's now-confirmed hit is
recorded here for completeness only; `required_filenames()` deliberately
excludes it. `EJU`/`KMM` are not re-queried here - `server/plane/enrich.py`'s
module docstring and 02-RESEARCH.md already document them as confirmed misses.

Filenames are derived from these exact live-resolved strings via
`normalise_airline_key()`, never hand-typed - see `required_filenames()`.

## `_TYPE_SHAPE_BUCKETS` (Phase 3.1, `classify_aircraft_type()`)

`_TYPE_SHAPE_BUCKETS` follows the same discipline as `_LIVE_RESOLVED_AIRLINES`
above: it is a hand-curated, static table, verified out of band (against
`03.1-CONTEXT.md`'s D-03 user-verified fleet table and a live-observed
sample of real ICAO type designators), hardcoded rather than fetched at
runtime. A designator missing from the table is not an error - it degrades
`classify_aircraft_type()` to `None`, which `select_illustration()` treats
as "no shape" and falls through to the next fallback tier.

## Filenames mirror the carrier's real current name (superseded rule, 260827-kih)

**SUPERSEDED (quick task 260827-kih, 2026-08-27, QT-kih-D-06):** every
illustration filename is now derived from the carrier's **real current
name**, run through `normalise_airline_key()` - and where `adsbdb`'s
crowdsourced database disagrees (because it still resolves a pre-rebrand
legal/trading name, or because it attributes an ICAO prefix to a
*different*, defunct carrier that once held it), `enrich.py`'s
`correct_airline_name()` / `apply_airline_name_correction()` reconcile the
two before either the selection key or the caption text is computed. This
is the opposite direction from the rule that governed this file through
Phase 3.1 and quick task `260827-hyy`.

**The rule this supersedes, for the record:** every filename used to be
derived from the literal `airline_name` string adsbdb's API actually
resolved - never from the current public brand name, and never
hand-typed - because no correction mechanism existed and mirroring adsbdb
verbatim was the only way to keep `select_illustration()`'s lookup working.
That was correct given the machinery available then: Phase 3.1
(`03.1-LIVE-RESOLUTION.md`'s Step B/C naming verdicts, P-01/D-04) and
quick task `260827-hyy`'s D-01 all rested on it. The **hazard the old rule
warned about is unchanged and still real** - a filename and a selection key
that drift apart silently lose selection, with no error anywhere, no log
line, no failing test. What changed is that `enrich.correct_airline_name()`
is now the mechanism that keeps them from drifting, not manual filename
discipline alone.

**Three files were renamed accordingly (`git mv`, history preserved,
QT-kih-D-04):**

- `ccm-airlines.png` -> `air-corsica.png` - adsbdb's callsign `CCM21AW`
  still resolves the pre-2013-rebrand string `"CCM Airlines"`.
- `europe-airpost.png` -> `asl-airlines-france.png` - adsbdb's callsigns
  `FPO701`/`FPO458` still resolve the pre-2015-rebrand string
  `"Europe Airpost"`.
- `corsairfly.png` -> `corsair.png` - adsbdb's `CRL` airline endpoint still
  resolves the prior-brand string `"Corsairfly"`.

Each rename's corresponding `enrich._AIRLINE_NAME_CORRECTIONS` row and
`enrich._ICAO_AIRLINE_PREFIXES` value are what make the renamed file
reachable again through every path (fresh adsbdb hit, cached adsbdb hit,
and the prefix-only fallback) - see that module for the full live evidence
behind each correction.

**TUIfly Belgium (`tuifly-belgium.png`, `JAF`) and KM Malta Airlines
(`km-malta-airlines.png`, `KMM`) are deliberately UNCHANGED and out of
scope for this correction (QT-kih-D-07).** TUIfly Belgium is the exact same
failure mode this seam now fixes for the three carriers above - a real
`JAF` callsign resolves live in adsbdb to the pre-2016 legacy brand
`"Jetairfly"` (QT-jz6-D-02) - and the new seam could trivially cover it
too. The developer considered this and explicitly chose NOT to add a
`JAF` correction row this session. **A future reader must not "complete
the job" by adding one as tidy-up.** KM Malta Airlines is unaffected for a
different reason - adsbdb has no record of that carrier under any callsign
at all (a confirmed permanent miss, QT-jz6-D-01), so there is no stale
string for a correction to reconcile.

Quick task `260827-kih` also adds Amelia (`AIA`) as a new target -
precisely because `enrich.correct_airline_name()` now exists: adsbdb's
`AIA` callsign resolves live to `"Avies"`, a *different, defunct* Estonian
carrier that happened to hold the same ICAO code (not a stale label for
the same real airline - an outright wrong carrier attribution, worse than
the three rename cases above). Amelia was excluded from the target set
through Phase 3.1 (`03.1-LIVE-RESOLUTION.md` marked it `[UNRESOLVED]`
because neither candidate ICAO code it tried could be trusted); that
exclusion rationale is retired by this session's live verification of the
real prefix. See `enrich._AIRLINE_NAME_CORRECTIONS` for the full live
evidence and `_ILLUSTRATION_TARGETS`' own Amelia entry.

## Quick task `260827-lgt` (2026-08-27): HOP! Air France, Wizz Air Malta, KlasJet

Three more carriers cross-checked against the official Paris Aéroport Orly
airline list. HOP! Air France (`"Air France Hop"`, primary Embraer +
secondary ATR72) introduces a new evidence class for this project: the
first target where `adsbdb`'s own resolution is already correct and
current, not stale, not wrong, and not absent - so it needs **no**
`enrich._AIRLINE_NAME_CORRECTIONS` row, the first new carrier added since
the correction seam existed that genuinely doesn't need one. KlasJet
(`"KlasJet"`, primary B737-800) carries materially lower confidence than
every other row in this table - its `KLJ` prefix was never live-confirmed,
only corroborated by reference sources - and is flagged as such everywhere
it appears. **Wizz Air Malta is deliberately absent from this table
entirely**: it maps to the existing `"Wizz Air"` selection key rather than
getting a target of its own, the same brand-consolidation precedent the
shipped `EJU` -> `"easyJet"` row already establishes - see
`enrich._ICAO_AIRLINE_PREFIXES`'s `WMT` row for the full rationale.
"""
import os
import re
import sys
import unicodedata

from PIL import Image

# Allow both `import server.plane.illustrations` (package import) and direct
# script execution, matching enrich.py/render.py's sys.path bootstrap.
_HERE = os.path.dirname(os.path.abspath(__file__))  # server/plane
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# --- Constants ---------------------------------------------------------------

ILLUSTRATION_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons", "illustrations")
)

GENERIC_FALLBACK_FILENAME = "generic-fallback.png"

# The whole set's single documented orientation convention (Pitfall 4 -
# there is no per-file metadata and no way to detect this in code; it is
# enforced by the HANDOFF.md spec plus human verification at the Task 2
# checkpoint). D-24 (03-CONTEXT.md): render.py never mirrors these files -
# every illustration renders nose-left always, in both departing and
# arriving states, so this is now the panel's one and only orientation,
# not a "source" convention a mirror step flips per state.
ILLUSTRATION_SOURCE_NOSE = "left"

# Downscale headroom against the 900px SILHOUETTE_TARGET_W width cap.
ILLUSTRATION_MIN_WIDTH = 1200

# T-03-03-01: an explicit decompression-bomb ceiling, well below Pillow's
# own default warning threshold, checked from the PNG header before any
# pixel data is decoded.
ILLUSTRATION_MAX_PIXELS = 40_000_000

# Live-resolved (callsign, airline_name) pairs requested for art - see the
# module docstring's table above for the full lookup record, including the
# one entry (Volotea) deliberately excluded from this list.
_LIVE_RESOLVED_AIRLINES = [
    ("AFR56XX", "Air France"),
    ("IBE05EM", "Iberia Airlines"),
    ("TAP440", "TAP Portugal"),
    ("DAH1008", "Air Algerie"),
    # Corrected to "Air Corsica" (260827-kih, QT-kih-D-06). Unlike the
    # module docstring's historical live-resolution table just above
    # (which records what adsbdb actually returned on 2026-08-26 and stays
    # unchanged), this list is a FILENAME source consumed by
    # required_filenames() to build the on-disk baseline - a stale
    # "CCM Airlines" value here would demand a ccm-airlines.png file that
    # no longer exists after this session's git mv rename.
    ("CCM21AW", "Air Corsica"),
    ("VLG6PD", "Vueling Airlines"),
    ("TVF16VB", "Transavia France"),
]

# Recorded per the module docstring's table - queried for status only, not
# requested for art. Not consumed by required_filenames().
_COVERAGE_CHECK_CALLSIGN = "VOE8KA"
_COVERAGE_CHECK_AIRLINE_NAME = "Volotea"

# The full D-03 target set (03.1-LIVE-RESOLUTION.md's "Consequences for the
# target set" section is the authority for this table's contents). Each
# entry is `(resolved_airline_name, shape_slug_or_None, note)`:
#   - `resolved_airline_name` is a live-verified carrier name, never a
#     guess - as of 260827-kih, the carrier's real current name for every
#     entry (see the module docstring's "Filenames mirror the carrier's
#     real current name" section for the Air Corsica/ASL Airlines France/
#     Corsair renames and why TUIfly Belgium is deliberately excepted).
#   - `shape` is `None` for the primary (unsuffixed) file - the numerically
#     dominant type per P-04 - or a SHAPE_SLUGS member for a secondary
#     mixed-fleet variant.
#   - `note` carries the D-reference / verdict token so HANDOFF.md (plan
#     03.1-05) can be generated from this table rather than hand-written.
#
# easyJet is included on the strength of its UK-AOC `EZY` prefix, which
# resolves live as `"easyJet"` - the Austrian-AOC `EJU` prefix (easyJet
# Europe) remains a confirmed non-resolving carrier for which no file is
# requested, unchanged from Phase 3 (P-03).
#
# La Compagnie remains deliberately absent: 03.1-LIVE-RESOLUTION.md marks
# it `[UNRESOLVED]`.  The additional airline assets below are explicit
# product coverage requested on 2026-08-27; the table is also the canonical
# filename registry, even where adsbdb still needs a future resolution-key
# audit before the art can be selected from live traffic.
_ILLUSTRATION_TARGETS = [
    # --- Baseline: already-confirmed resolutions, primary files ---
    ("Air France", None, "D-03 baseline; [VERIFIED-CALLSIGN]"),
    ("Iberia Airlines", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("TAP Portugal", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Air Algerie", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    (
        "Air Corsica",
        None,
        "D-03/D-04 baseline, A320 primary (P-04); adsbdb's own callsign "
        "CCM21AW still resolves the pre-2013-rebrand string 'CCM Airlines' "
        "- corrected on read via enrich.correct_airline_name() (260827-kih, "
        "QT-kih-D-06); [VERIFIED-CALLSIGN]",
    ),
    ("Vueling Airlines", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Transavia France", None, "D-03/D-05 baseline, B737 primary (P-04, pre-transition majority); [VERIFIED-CALLSIGN]"),
    ("easyJet", None, "D-03 baseline, UK-AOC EZY prefix only (P-03); [VERIFIED-CALLSIGN]"),
    ("Wizz Air", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    ("Volotea", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    ("ITA Airways", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    ("Air Europa", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    ("Royal Air Maroc", None, "D-03 baseline, B737 primary (P-04); [CITED: 03.1-RESEARCH.md]"),
    ("LOT Polish Airlines", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    ("Air Caraïbes", None, "D-03 baseline, A350 primary (P-04); [CITED: 03.1-RESEARCH.md]"),
    ("French Bee", None, "D-03 baseline; [CITED: 03.1-RESEARCH.md]"),
    # --- Step-C airlines newly live-resolved this phase ---
    (
        "ASL Airlines France",
        None,
        "adsbdb's own callsigns FPO701/FPO458 still resolve the "
        "pre-2015-rebrand string 'Europe Airpost' - corrected on read via "
        "enrich.correct_airline_name() (260827-kih, QT-kih-D-06); "
        "[VERIFIED-CALLSIGN]",
    ),
    ("Tunisair", None, "[VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Pegasus Airlines", None, "[VERIFIED-CALLSIGN]"),
    ("Chalair Aviation", None, "[VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Twin Jet", None, "[VERIFIED-CALLSIGN]"),
    (
        "Corsair",
        None,
        "adsbdb's own CRL airline endpoint still resolves the prior-brand "
        "string 'Corsairfly' - corrected on read via "
        "enrich.correct_airline_name() (260827-kih, QT-kih-D-06); "
        "[VERIFIED-AIRLINE-ENDPOINT-ONLY]",
    ),
    # --- Quick task 260827-jz6 (2026-08-27): two new target airlines ---
    (
        "KM Malta Airlines",
        None,
        "Confirmed permanent adsbdb miss - live-verified 2026-08-27: "
        "`curl https://api.adsbdb.com/v0/callsign/KMM466` returns "
        "'unknown callsign'. adsbdb was never updated for the 2023 Air "
        "Malta -> KM Malta Airlines rebrand, so this airline is reachable "
        "only via enrich.airline_from_callsign()'s ICAO-prefix path (quick "
        "task 260827-hyy), never via an adsbdb hit. The real current brand "
        "name is correct here precisely because no adsbdb string exists to "
        "mirror (QT-jz6-D-01) - same class as the existing EJU exception "
        "above. [VERIFIED-CALLSIGN-MISS]",
    ),
    (
        "TUIfly Belgium",
        None,
        "Deliberate, developer-chosen EXCEPTION: unlike Air Corsica/ASL "
        "Airlines France/Corsair above, this carrier's stale-brand-name "
        "mismatch is NOT corrected by enrich.correct_airline_name() - the "
        "developer considered and declined to add a JAF correction row "
        "this session (260827-kih, QT-kih-D-07). adsbdb DOES resolve a "
        "real JAF callsign - live-verified 2026-08-27: "
        "`curl https://api.adsbdb.com/v0/callsign/"
        "JAF7521` returns 'Jetairfly', the pre-2016 legacy brand. The "
        "accepted consequence: an adsbdb hit renders 'Jetairfly' and falls "
        "through to a lower illustration tier, while the airline-only "
        "fallback renders 'TUIfly Belgium' and reaches tuifly-belgium.png. "
        "See HANDOFF.md's Naming rules section for the full record. "
        "[VERIFIED-CALLSIGN-STALE-NAME-OVERRIDDEN]",
    ),
    # --- Quick task 260827-kih (2026-08-27): Amelia, reachable now that
    # enrich.correct_airline_name() exists ---
    (
        "Amelia",
        None,
        "Live-verified 2026-08-27: `curl https://api.adsbdb.com/v0/callsign/"
        "AIA6412` returns a populated result attributing the AIA prefix to "
        "'Avies', a different, defunct Estonian carrier (ceased operations "
        "2016) that happened to hold the same ICAO code - not merely a "
        "stale label for the same real airline, an actively wrong carrier "
        "attribution. The ICAO prefix AIA/Amelia itself is independently "
        "corroborated (Flightradar24 live-tracked flight 8R6412 as "
        "callsign 8R/AIA, plus Airhex, Wikipedia, ERAA and IATA). Reachable "
        "precisely because enrich.correct_airline_name() now reconciles "
        "the adsbdb-hit path with the corrected name before selection; the "
        "prior exclusion rationale (an untrustworthy candidate ICAO code, "
        "03.1-LIVE-RESOLUTION.md) is retired by this session's live "
        "verification of the real one. Primary file, Airbus A320 "
        "(A320-family; A319 shares the file per the suffix rule). "
        "[VERIFIED-CALLSIGN]",
    ),
    # --- Quick task 260827-lgt (2026-08-27): three new target carriers,
    # cross-checked against the official Paris Aéroport Orly airline list.
    # HOP! Air France and KlasJet are new primaries below; Wizz Air Malta
    # is deliberately NOT a new target here - see enrich._ICAO_AIRLINE_
    # PREFIXES' WMT row and this module's docstring for why (QT-lgt-D-01):
    # it reuses the already-vendored "Wizz Air" key, exactly the shipped
    # EJU -> easyJet brand-consolidation precedent, so it costs zero new
    # artwork and needs no entry in this table at all. ---
    (
        "Air France Hop",
        None,
        "New target (QT-lgt-D-03/D-04). This is the FIRST carrier this "
        "project has added where adsbdb's own resolution is already "
        "correct and current - not stale (unlike FPO/CRL/CCM), not a "
        "wrong carrier (unlike AIA), and not absent (unlike KMM). "
        "Live-verified 2026-08-27: `curl https://api.adsbdb.com/v0/"
        "callsign/HOP4001` returns a real route (Nantes-Lyon) with "
        "airline_name 'Air France Hop'. Because the resolved string and "
        "this table's prefix-table value are the same string, the "
        "adsbdb-hit path and the prefix-only fallback path produce an "
        "identical selection key by construction, and NO "
        "enrich._AIRLINE_NAME_CORRECTIONS row exists or is needed "
        "(QT-lgt-D-07) - a future reader must not add one as tidy-up. "
        "The real ADS-B callsign field genuinely is HOP+number even "
        "though the spoken ATC radio callsign is 'Airfrans' - radio "
        "phraseology is irrelevant here, this project matches on the "
        "ADS-B callsign field, never the radio callsign. This key is "
        "deliberately DISTINCT from 'Air France' and reaches its own "
        "file: select_illustration() matches keys exactly, never by "
        "prefix, and the mainline air-france.png (an A320) does not "
        "represent the regional fleet. Livery target: the post-2019 Air "
        "France mainline white/blue scheme with small HOP titling - NOT "
        "the pre-2019 standalone brightly-coloured HOP! livery. Primary "
        "airframe: Embraer E-Jet (E170/E175/E190), the structurally "
        "permanent and numerically dominant regional type since the "
        "2019-2021 fold-in of HOP! into Air France's regional operation "
        "(P-04 mixed-fleet split, MEDIUM confidence on relative fleet "
        "size - see the secondary entry below and HANDOFF.md's coverage "
        "caveat). [VERIFIED-CALLSIGN]",
    ),
    (
        "KlasJet",
        None,
        "New target (QT-lgt-D-05/D-06). Filed under the carrier's real "
        "camel-case trading style 'KlasJet' - normalise_airline_key() "
        "slugs 'KlasJet' and 'Klasjet' identically to 'klasjet', so this "
        "casing choice affects only the rendered caption, never the "
        "filename. CARRIES MATERIALLY LOWER CONFIDENCE THAN EVERY OTHER "
        "ROW IN THIS TABLE - do not read this entry with the same "
        "confidence as the rows around it. The KLJ prefix is corroborated "
        "by lookup sources but was NEVER LIVE-CONFIRMED: approximately 25 "
        "adsbdb probes across plausible flight-number ranges all returned "
        "'unknown callsign' - zero live confirmation, which is WEAKER "
        "evidence than KMM's confirmed-negative above (a specific curl of "
        "a specific real callsign that definitively missed). KlasJet is a "
        "Lithuanian ACMI/wet-lease and VIP charter operator, and wet-lease "
        "flights typically broadcast the CONTRACTING airline's callsign "
        "rather than the operator's own, so a real KLJ-prefixed callsign "
        "may rarely or never appear in this project's detections at "
        "Orly. The developer chose to include it anyway, with this "
        "uncertainty in hand. Remediation pointer: if a real KLJ callsign "
        "is ever observed and resolves to a different carrier, this row "
        "is the first thing to re-verify. Primary airframe: Boeing "
        "737-800 - the most plausible scheduled-passenger-shaped choice "
        "among KlasJet's fleet (737-300/500/800 plus Boeing Business "
        "Jets); which exact airframe is right remains an open question "
        "for the developer at generation time (QT-lgt-D-08), not resolved "
        "here. [UNCONFIRMED-PREFIX]",
    ),
    # --- P-04 secondary-variant files for mixed-fleet airlines ---
    (
        "Air Corsica",
        "atr72",
        "D-03/D-04 mixed-fleet secondary (P-04); renamed from the "
        "adsbdb-resolved 'CCM Airlines' key (260827-kih, QT-kih-D-06)",
    ),
    ("Transavia France", "a320", "D-05 fleet-transition secondary (P-04)"),
    ("Royal Air Maroc", "embraer", "D-03 mixed-fleet secondary (P-04)"),
    ("Air Caraïbes", "a330", "D-03 mixed-fleet secondary (P-04)"),
    (
        "Amelia",
        "embraer",
        "Quick task 260827-kih secondary variant - Embraer E145 (E190 "
        "shares the file per the suffix rule), chosen over the E190 "
        "because the E145 is the type on Amelia's real Orly-relevant Pau "
        "service (recorded in Phase 3.1's own fleet research, "
        "03.1-CONTEXT.md D-03). Cross-references the same AIA correction "
        "row as the primary entry above.",
    ),
    (
        "Air France Hop",
        "atr72",
        "Quick task 260827-lgt P-04 mixed-fleet secondary. The ATR42/ATR72 "
        "turboprop fleet is the minority type alongside the Embraer "
        "primary above - see that entry for the full evidence, not "
        "repeated here. QT-lgt-D-04's primary/secondary split (Embraer "
        "primary, ATR72 secondary) is a MEDIUM-confidence judgment on "
        "relative fleet size, not a live-verified count; reversing it is "
        "a one-token change (move the 'atr72' shape slug onto the "
        "'Air France Hop' primary row and give this row 'embraer' "
        "instead), and D-06's Tier 2 fallback means a HOP flight of the "
        "non-primary type still gets HOP-branded art either way.",
    ),
    (
        "Air Caraïbes",
        "a350-1000",
        "Long-haul secondary variant added during a parallel 2026-08-27 "
        "livery-audit session (independent of 260827-jz6/kih/lgt) - real "
        "vendored artwork delivered directly to main "
        "(air-caraibes-a350-1000.png), merged in here rather than "
        "duplicated.",
    ),
    (
        "Air Caraïbes",
        "atr72",
        "Regional secondary variant added during the same parallel "
        "2026-08-27 livery-audit session - real vendored artwork "
        "delivered directly to main (air-caraibes-atr72.png), merged in "
        "here rather than duplicated.",
    ),
]

# A key must reduce to this shape after normalise_airline_key() - defensive
# boundary check independent of normalise_airline_key()'s own guarantee
# (T-03-03-03: a hostile/malformed airline_name must never escape the
# asset directory via path construction).
_UNSAFE_KEY_RE = re.compile(r"[\\/]|\.\.")

# The seven D-03 base aircraft shapes classify_aircraft_type() classifies
# real ICAO type designators into. Order is iteration-stable (target_
# filenames()'s generic-{shape}.png block uses this exact order) but is not
# a priority ranking. Character-for-character contract shared with the
# filename convention (illustrations/{shape}.png) and with render.py's
# caption labels (03.1-04) - these seven strings must match everywhere.
SHAPE_SLUGS = (
    "a320",
    "b737",
    "atr72",
    "beechcraft1900d",
    "embraer",
    "a330",
    "a350",
)

# ICAO type designator (uppercase) -> one of SHAPE_SLUGS. Hand-curated from
# 03.1-CONTEXT.md's D-03 user-verified fleet table and 03.1-RESEARCH.md's
# Code-Level Finding #4 (ICAO Doc 8643 designators; the two designators
# actually observed live this phase, A320 and B738, are confirmed, the
# rest are a first draft from training knowledge per Assumption A1) -
# same discipline as _LIVE_RESOLVED_AIRLINES below: verified out of band,
# hardcoded, documented, never a live lookup. A designator missing from
# this table degrades classify_aircraft_type() to None, which
# select_illustration() treats as "no shape" and falls through to the
# next fallback tier - a wrong or missing entry degrades safely, it never
# raises and never fails closed into an error.
_TYPE_SHAPE_BUCKETS = {
    # A320 family (D-03: Air France, Vueling, Iberia, TAP, Transavia,
    # easyJet, Wizz Air, Volotea, ITA Airways, Tunisair, Pegasus, La
    # Compagnie [excluded from the target set pending re-verification];
    # 260827-jz6: KM Malta Airlines, A320neo primary; 260827-kih: Amelia,
    # A320 primary)
    "A318": "a320", "A319": "a320", "A320": "a320", "A321": "a320",
    "A20N": "a320", "A21N": "a320",  # A320neo / A321neo
    # B737 family (D-03: Transavia, Air Europa, Air Algerie, Royal Air
    # Maroc; 260827-jz6: TUIfly Belgium, 737 MAX 8 primary; 260827-kih:
    # ASL Airlines France - adsbdb resolves the pre-2015-rebrand name
    # "Europe Airpost", corrected on read, see enrich.py; 260827-lgt:
    # KlasJet 737-800 primary, MEDIUM-lower-confidence entry - see
    # enrich.py's KLJ row)
    "B731": "b737", "B732": "b737", "B733": "b737", "B734": "b737",
    "B735": "b737", "B736": "b737", "B737": "b737", "B738": "b737",
    "B739": "b737", "B37M": "b737", "B38M": "b737", "B39M": "b737",
    "B3XM": "b737",  # MAX 7/8/9/10
    # ATR72 (D-03: Air Corsica, Chalair Aviation - 260827-kih renamed the
    # adsbdb-resolved "CCM Airlines" key to Air Corsica's real current
    # name, see enrich.py; 260827-lgt: Air France Hop ATR72 secondary,
    # MEDIUM-confidence P-04 split, see the "Air France Hop"/"atr72" row
    # in _ILLUSTRATION_TARGETS) - per P-06, ATR42 designators map here too
    # since D-03's table has no separate ATR42 shape.
    "AT43": "atr72", "AT44": "atr72", "AT45": "atr72", "AT46": "atr72",
    "AT72": "atr72", "AT73": "atr72", "AT75": "atr72", "AT76": "atr72",
    # Beechcraft 1900D (D-03: Twin Jet)
    "BE9L": "beechcraft1900d",
    # Embraer E-Jet family (D-03: LOT Polish Airlines, Royal Air Maroc
    # minority; 260827-kih: Amelia's E145 secondary variant - see the
    # "Amelia"/"embraer" row in _ILLUSTRATION_TARGETS; 260827-lgt: Air
    # France Hop primary, E170/E175/E190, the numerically dominant
    # regional type since HOP!'s fold-in - MEDIUM-confidence P-04 split,
    # see the "Air France Hop" primary entry)
    "E135": "embraer", "E145": "embraer", "E170": "embraer",
    "E75L": "embraer", "E75S": "embraer", "E190": "embraer",
    "E195": "embraer", "E290": "embraer", "E295": "embraer",
    # A330 family (D-03: Air Caraibes minority; 260827-kih: Corsair -
    # adsbdb's CRL airline endpoint resolves the prior-brand name
    # "Corsairfly", corrected on read, see enrich.py)
    "A332": "a330", "A333": "a330", "A339": "a330",
    # A350 family (D-03: Air Caraibes majority, French Bee)
    "A359": "a350", "A35K": "a350",
}


def normalise_airline_key(airline_name):
    """Return a deterministic, filesystem-safe slug for `airline_name`, or
    `None` for anything falsy or non-string - mirrors enrich.py's
    `normalise_callsign()` never-raises discipline. Pure, no I/O.

    `normalise_airline_key("Air Algérie")` -> `"air-algerie"`
    `normalise_airline_key("Air Corsica")` -> `"air-corsica"`
    `normalise_airline_key("")`, `(None)`, `(42)` -> `None`
    """
    if not isinstance(airline_name, str) or not airline_name:
        return None
    ascii_name = unicodedata.normalize("NFKD", airline_name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or None


def classify_aircraft_type(icao_type):
    """Return one of SHAPE_SLUGS for a known ICAO type designator, or
    `None` for anything falsy, non-string, or unrecognized - mirrors
    normalise_airline_key()'s never-raises discipline exactly. Pure, no
    I/O.

    `classify_aircraft_type("A20N")` -> `"a320"`
    `classify_aircraft_type(" b38m ")` -> `"b737"`
    `classify_aircraft_type("ZZZZ")`, `(None)`, `("")`, `(42)` -> `None`

    This is a lookup against a fixed static table (_TYPE_SHAPE_BUCKETS)
    whose values are all members of SHAPE_SLUGS - it never returns any
    value derived from its argument. That is what makes a hostile
    designator (e.g. containing a path separator or a parent-directory
    sequence) unable to reach a filesystem path: the only strings this
    function can ever produce are the seven hardcoded slugs, or None
    (T-03.1-03-01).
    """
    if not isinstance(icao_type, str) or not icao_type:
        return None
    return _TYPE_SHAPE_BUCKETS.get(icao_type.strip().upper())


def illustration_path_for_key(key):
    """Join `ILLUSTRATION_DIR` and `key + ".png"`. Returns `None` if `key`
    is falsy or contains a path separator or a parent-directory segment -
    this is the boundary itself and must not rely on `normalise_airline_key`
    already having made that impossible (T-03-03-03).
    """
    if not key or _UNSAFE_KEY_RE.search(key):
        return None
    return os.path.join(ILLUSTRATION_DIR, key + ".png")


def generic_fallback_path():
    return os.path.join(ILLUSTRATION_DIR, GENERIC_FALLBACK_FILENAME)


def select_illustration(route, aircraft_type=None):
    """Return the illustration path for `route` (a route dict, or `None`)
    and `aircraft_type` (a raw ICAO type designator string, or `None`),
    resolved through four fallback tiers, or `None` if not even the
    generic fallback file exists. Never raises for any input, including a
    non-dict `route`, a route whose `.get` raises, a non-string
    `airline_name`, and a hostile `aircraft_type`.

    Omitting `aircraft_type` reproduces this function's pre-03.1 behaviour
    exactly: Tier 1 and Tier 3 both short-circuit on a `None` shape key,
    so the call falls straight through to the historical Tier 2 -> Tier 4
    path every existing caller and test already relies on.

    Tier 1: `{airline}-{shape}.png` - an exact airline+type match.
    Tier 2 (D-06): `{airline}.png` - the airline's own illustration when
        no exact-shape file exists. Brand identity wins over exact type
        precision here - a real flight is still instantly recognisable as
        "that airline", which matters more on a glanceable frame than
        showing the technically-correct silhouette.
    Tier 3 (D-07): `generic-{shape}.png` - a neutral, correct-shape
        illustration for an airline this module doesn't recognise, rather
        than the single undifferentiated universal fallback.
    Tier 4 (D-08): `generic-fallback.png` - the existing universal
        fallback, unchanged from Phase 3, used when neither the airline
        nor the shape resolves to anything on disk.
    """
    try:
        airline_name = route.get("airline_name") if isinstance(route, dict) else None
    except Exception:
        airline_name = None

    airline_key = normalise_airline_key(airline_name)
    shape_key = classify_aircraft_type(aircraft_type)

    # Tier 1: exact airline + shape match.
    if airline_key and shape_key:
        exact = illustration_path_for_key("%s-%s" % (airline_key, shape_key))
        if exact is not None and os.path.isfile(exact):
            return exact

    # Tier 2 (D-06): known airline, no exact-shape file - brand wins over
    # type precision; still show that airline's own default illustration.
    if airline_key:
        primary = illustration_path_for_key(airline_key)
        if primary is not None and os.path.isfile(primary):
            return primary

    # Tier 3 (D-07): unrecognized airline, but a recognized+covered shape
    # - show the neutral correct-shape illustration instead of jumping
    # straight to the single universal generic.
    if shape_key:
        neutral = illustration_path_for_key("generic-%s" % shape_key)
        if neutral is not None and os.path.isfile(neutral):
            return neutral

    # Tier 4 (D-08): neither airline nor shape resolves to anything on
    # disk - the existing single universal fallback, unchanged.
    fallback = generic_fallback_path()
    if os.path.isfile(fallback):
        return fallback
    return None


def validate_illustration_file(path):
    """Return a list of human-readable problems with the illustration file
    at `path`, empty when the file is acceptable. Reads `.size`/`.format`
    from the PNG header before calling anything that decodes pixel data,
    so an oversized/decompression-bomb file is rejected without ever being
    fully decoded (T-03-03-01). Never raises - any Pillow exception is
    turned into a problem string.
    """
    problems = []
    if not os.path.isfile(path):
        return ["file does not exist: %s" % path]

    try:
        with Image.open(path) as img:
            fmt = img.format
            width, height = img.size

            if fmt != "PNG":
                problems.append("not a PNG file (detected format=%r)" % (fmt,))

            pixel_count = width * height
            if pixel_count > ILLUSTRATION_MAX_PIXELS:
                problems.append(
                    "pixel count %d (%dx%d) exceeds the %d-pixel cap" % (pixel_count, width, height, ILLUSTRATION_MAX_PIXELS)
                )
                # Do not decode any further - the whole point of checking
                # the header first is to never call load()/convert() on a
                # file this large.
                return problems

            if width < ILLUSTRATION_MIN_WIDTH:
                problems.append("width %dpx is below the %dpx minimum" % (width, ILLUSTRATION_MIN_WIDTH))

            if width <= height:
                problems.append("image is not landscape (width=%d, height=%d)" % (width, height))

            mode = img.mode
            has_alpha = mode in ("RGBA", "LA") or "transparency" in img.info
            if not has_alpha:
                problems.append("no alpha channel present (mode=%r, no transparency info)" % (mode,))
            else:
                rgba = img.convert("RGBA")
                alpha_min, alpha_max = rgba.getchannel("A").getextrema()
                if alpha_min == 255:
                    problems.append("alpha channel is fully opaque everywhere - transparency requirement not met")
    except Exception as exc:  # never propagate a Pillow decode error
        problems.append("failed to open/parse image: %r" % (exc,))

    return problems


def target_airline_names():
    """Return the distinct `resolved_airline_name` values of
    `_ILLUSTRATION_TARGETS`, order-preserving and de-duplicated.

    This is the drift guard quick task 260827-hyy's design decision D-07
    requires: `enrich.py`'s static ICAO-prefix-to-airline-name table is
    checked against this function's output, so renaming or dropping an
    illustration target without mirroring the change in the prefix table
    fails the suite instead of silently producing a callsign-prefix
    resolution that can never reach any art. Derived from
    `_ILLUSTRATION_TARGETS` directly - never a second hardcoded list.
    """
    names = []
    for airline_name, _shape, _note in _ILLUSTRATION_TARGETS:
        if airline_name not in names:
            names.append(airline_name)
    return names


def target_filenames():
    """Return the full D-03 plan: one filename per `_ILLUSTRATION_TARGETS`
    entry - derived through `normalise_airline_key()`, never hand-typed -
    then one `generic-{shape}.png` per `SHAPE_SLUGS` entry (in `SHAPE_SLUGS`
    order), then the universal fallback. Order-preserving and de-duplicated.
    Skips (does not crash on) any airline whose slug comes back `None`.

    This is "the full plan" (P-05) - what should eventually exist once
    plan 03.1-05's hand-off is complete. See `required_filenames()` for
    "what must exist and validate right now".
    """
    names = []
    for airline_name, shape, _note in _ILLUSTRATION_TARGETS:
        key = normalise_airline_key(airline_name)
        if not key:
            continue
        filename = ("%s-%s.png" % (key, shape)) if shape else ("%s.png" % key)
        if filename not in names:
            names.append(filename)
    for shape in SHAPE_SLUGS:
        filename = "generic-%s.png" % shape
        if filename not in names:
            names.append(filename)
    if GENERIC_FALLBACK_FILENAME not in names:
        names.append(GENERIC_FALLBACK_FILENAME)
    return names


def required_filenames():
    """Return the immovable baseline - the pre-03.1 set (one filename per
    live-resolved covered airline in `_LIVE_RESOLVED_AIRLINES`, plus the
    generic fallback) - unioned with every `target_filenames()` entry that
    already exists on disk, de-duplicated and order-preserving.

    P-05: this function means "must exist and validate right now" -
    a newly delivered file becomes enforced automatically the moment it
    lands on disk, and deleting an already-vendored file still fails this
    contract. `target_filenames()` means "the full plan". The split exists
    so this harness and CI stay green while plan 03.1-05's illustration
    hand-off proceeds, without any target ever being silently dropped.
    """
    names = []
    for _callsign, airline_name in _LIVE_RESOLVED_AIRLINES:
        key = normalise_airline_key(airline_name)
        if key:
            names.append(key + ".png")
    if GENERIC_FALLBACK_FILENAME not in names:
        names.append(GENERIC_FALLBACK_FILENAME)
    for name in target_filenames():
        if name not in names and os.path.isfile(os.path.join(ILLUSTRATION_DIR, name)):
            names.append(name)
    return names


def outstanding_filenames():
    """Return `target_filenames()` minus the files already present on
    disk, in target order - the machine-reportable remainder of plan
    03.1-05's hand-off (T-03.1-03-04).
    """
    return [name for name in target_filenames() if not os.path.isfile(os.path.join(ILLUSTRATION_DIR, name))]


def _validate_directory(strict_targets=False):
    """Validate every required file plus flag any unexpected .png in
    ILLUSTRATION_DIR - checked against the full `target_filenames()` set,
    so a delivered-but-not-yet-baseline file is never reported as
    unexpected. Prints one informational line per outstanding target and a
    final count. Returns True if everything passes; when `strict_targets`
    is True, a non-empty outstanding list also fails the run.
    """
    required = required_filenames()
    targets = set(target_filenames())
    ok = True

    for name in required:
        path = os.path.join(ILLUSTRATION_DIR, name)
        problems = validate_illustration_file(path)
        if problems:
            ok = False
            print("FAIL %s" % name)
            for problem in problems:
                print("  - %s" % problem)
        else:
            print("PASS %s" % name)

    if os.path.isdir(ILLUSTRATION_DIR):
        for entry in sorted(os.listdir(ILLUSTRATION_DIR)):
            if entry.endswith(".png") and entry not in targets:
                ok = False
                print("FAIL unexpected file not in the target set: %s" % entry)
    else:
        ok = False
        print("FAIL illustration directory does not exist: %s" % ILLUSTRATION_DIR)

    outstanding = outstanding_filenames()
    for name in outstanding:
        print("OUTSTANDING %s" % name)
    print("%d outstanding target file(s)" % len(outstanding))
    if strict_targets and outstanding:
        ok = False

    return ok


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate", action="store_true", help="Validate every required file in the illustration directory; exit non-zero on any problem."
    )
    parser.add_argument(
        "--required", action="store_true", help="Print required_filenames() (must exist and validate now), one per line."
    )
    parser.add_argument("--targets", action="store_true", help="Print target_filenames() (the full D-03 hand-off plan), one per line.")
    parser.add_argument(
        "--outstanding", action="store_true", help="Print outstanding_filenames() (target files not yet on disk), one per line."
    )
    parser.add_argument(
        "--strict-targets",
        action="store_true",
        help="With --validate, also fail (non-zero exit) if any target file is outstanding.",
    )
    args = parser.parse_args(argv)

    if args.required:
        for name in required_filenames():
            print(name)
        return 0

    if args.targets:
        for name in target_filenames():
            print(name)
        return 0

    if args.outstanding:
        for name in outstanding_filenames():
            print(name)
        return 0

    if args.validate:
        ok = _validate_directory(strict_targets=args.strict_targets)
        return 0 if ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
