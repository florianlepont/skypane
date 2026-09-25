#!/usr/bin/env python3
"""Per-airline aircraft illustration selection.

Selection keys off `route["airline_name"]`. Coverage combines `adsbdb`'s
route lookup with `enrich.airline_from_callsign()`'s ICAO-prefix
fallback, so a rotating-callsign carrier reaches its own illustration
even when adsbdb has nothing. No network call of its own; the
illustration set is a hand-curated, static mapping.

Filenames are derived from each carrier's real current name via
`normalise_airline_key()`. Where `adsbdb` still resolves a stale or
wrong name, `enrich.py`'s `correct_airline_name()` reconciles it before
selection - without that seam, a filename and a selection key could
drift apart with no error, log line, or failing test.

`_TYPE_SHAPE_BUCKETS` classifies ICAO type designators into art-sizing
shape buckets (`classify_aircraft_type()`); a missing designator degrades
to `None`, treated as "no shape" by `select_illustration()`.

CLI: `--validate` checks every required illustration file;
`--required`/`--targets`/`--outstanding` list the corresponding filename
sets; `--strict-targets` (with `--validate`) also fails on any
outstanding target.
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

# The whole set's single documented orientation convention - there is no
# per-file metadata and no way to detect this in code; it is enforced by
# the HANDOFF.md spec plus human verification. render.py never mirrors
# these files - every illustration renders nose-left always, in both
# departing and arriving states, so this is the panel's one and only
# orientation, not a "source" convention a mirror step flips per state.
ILLUSTRATION_SOURCE_NOSE = "left"

# Downscale headroom against the 900px SILHOUETTE_TARGET_W width cap.
ILLUSTRATION_MIN_WIDTH = 1200

# An explicit decompression-bomb ceiling, well below Pillow's own default
# warning threshold, checked from the PNG header before any pixel data is
# decoded.
ILLUSTRATION_MAX_PIXELS = 40_000_000

# Live-resolved (callsign, airline_name) pairs requested for art, each
# confirmed against a real adsbdb lookup.
_LIVE_RESOLVED_AIRLINES = [
    ("AFR56XX", "Air France"),
    ("IBE05EM", "Iberia Airlines"),
    ("TAP440", "TAP Portugal"),
    ("DAH1008", "Air Algerie"),
    # This list is a FILENAME source consumed by required_filenames() to
    # build the on-disk baseline, so it must always carry the carrier's
    # real current name - a stale "CCM Airlines" value here would demand
    # a ccm-airlines.png file that no longer exists after the rename to
    # Air Corsica.
    ("CCM21AW", "Air Corsica"),
    ("VLG6PD", "Vueling Airlines"),
    ("TVF16VB", "Transavia France"),
]

# Volotea's adsbdb resolution is confirmed but not requested for art -
# recorded for coverage-status purposes only. Not consumed by
# required_filenames().
_COVERAGE_CHECK_CALLSIGN = "VOE8KA"
_COVERAGE_CHECK_AIRLINE_NAME = "Volotea"

# The full illustration target set: `(resolved_airline_name,
# shape_slug_or_None, note)`. `resolved_airline_name` is always the
# carrier's real current name (see module docstring's correction-seam
# note). `shape` is `None` for the primary file, else a SHAPE_SLUGS
# member for a secondary mixed-fleet variant. `note` carries the verdict
# token (evidence strength) HANDOFF.md is generated from.
#
# easyJet is included on its UK-AOC `EZY` prefix; the Austrian-AOC `EJU`
# prefix (easyJet Europe) remains a confirmed non-resolving carrier.
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
    # --- Additional target airlines ---
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
    # --- Amelia, reachable now that enrich.correct_airline_name() exists ---
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
    # Wizz Air Malta is deliberately absent: it reuses the vendored
    # "Wizz Air" key (see enrich._ICAO_AIRLINE_PREFIXES' WMT row).
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
    # --- Secondary-variant files for mixed-fleet airlines ---
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
    # --- [DEVELOPER-OBSERVED] rows (defined in HANDOFF.md): direct
    # observation, no adsbdb transcript - weaker evidence than [VERIFIED-*]. ---
    (
        "La Compagnie",
        None,
        "QT-v9c-D-02: supersedes Phase 3.1's [UNRESOLVED] verdict "
        "(03.1-LIVE-RESOLUTION.md Step C, and its 'Consequences for the "
        "target set' exclusion), which parked this carrier because its "
        "Wikipedia-confirmed ICAO code (DJT) resolves in adsbdb to a "
        "different, unrelated US operator ('Denver Jet'), and no real "
        "La Compagnie callsign had ever been caught to learn what a "
        "genuine flight returns. The developer observed a real "
        "DJT-prefixed La Compagnie flight at Orly on 2026-09-21 - that is "
        "the blocker the old verdict named, and it is now cleared. "
        "Primary airframe: Airbus A321neo LR (registration F-HNCO in the "
        "delivered art), La Compagnie's real current single-type "
        "all-business-class fleet - corrects this note's own earlier "
        "draft, which assumed the carrier's former Boeing 757 / a "
        "guessed A350 before the actual delivered file was inspected. "
        "[DEVELOPER-OBSERVED]",
    ),
    (
        "Qatar Amiri Flight",
        None,
        "Qatar's state/VIP operator (ICAO QAF). Primary airframe: Airbus "
        "A320, depicted in Qatar Airways' commercial 'QATAR' livery - the "
        "delivered art carries no distinct VIP paint scheme and no "
        "visible registration, so it is not confirmed to depict the "
        "developer's observed tail A7-MBK specifically, only the QAF "
        "operator identity. [DEVELOPER-OBSERVED]",
    ),
    (
        "South Korea Government",
        None,
        "The ROKAF-operated Republic of Korea presidential fleet (ICAO "
        "KAF). Observed as callsign KAF001, a Boeing 747-8i, tail 22-001. "
        "No 747 shape bucket exists in _TYPE_SHAPE_BUCKETS, so this "
        "carrier is reachable only through Tier 2 (the airline's own "
        "primary file), never through an exact airline+shape Tier 1 "
        "match - there is no generic-747 fallback either. "
        "[DEVELOPER-OBSERVED]",
    ),
    (
        "Royal Jordanian",
        None,
        "Jordan's flag carrier (ICAO RJA), an ordinary scheduled "
        "commercial carrier - see enrich.py's RJA/SVA header comment for "
        "why this row, unlike the state/charter operators around it, may "
        "see a live adsbdb hit under a different string. Primary "
        "airframe: Boeing 787-8 Dreamliner (registration JY-BAA in the "
        "delivered art), Royal Jordanian's widebody flagship type. "
        "[DEVELOPER-OBSERVED]",
    ),
    (
        "French Air Force",
        None,
        "QT-v9c-D-04: filed under the broader 'French Air Force' name "
        "rather than 'COTAM' (Commandement du Transport Aerien "
        "Militaire), the operator's real name - see enrich.py's CTM row "
        "for why the term stays greppable there. The delivered file was "
        "named french-air-force-a330.png (COTAM's A330 MRTT Phenix, "
        "vendored here under the unsuffixed primary name "
        "french-air-force.png rather than as an a330-suffixed "
        "secondary): companion/pages/airlines_page.py builds every "
        "gallery card's <img src> from the primary key alone, "
        "unconditionally, and companion/test_status_pages.py asserts "
        "every rendered card src is a target_filenames() member - a "
        "shape-only 'French Air Force' target would render a 404 image "
        "in the companion and fail that harness. Installed as the "
        "primary, Tier 2 (D-06, brand identity wins over exact type "
        "precision) returns this identical file for a real COTAM A330 "
        "that Tier 1 would have returned, and additionally covers "
        "COTAM's other types instead of dropping them to the generic "
        "silhouette. See VENDOR.md for the delivered-filename record. "
        "[DEVELOPER-OBSERVED]",
    ),
    (
        "Saudi Royal Aviation",
        None,
        "Saudi Arabia's state/royal VIP operator (ICAO SRA). Primary "
        "airframe: Boeing 777-300ER, in the green/white 'KINGDOM OF "
        "SAUDI ARABIA' state livery (registration HZ-HM5 in the "
        "delivered art). No B777 shape bucket exists in "
        "_TYPE_SHAPE_BUCKETS (only the 737/A330/A350/etc. families do), "
        "so this carrier is reachable only through Tier 2 (the airline's "
        "own primary file). [DEVELOPER-OBSERVED]",
    ),
    (
        "Saudia",
        None,
        "Saudi Arabia's flag carrier (ICAO SVA), an ordinary scheduled "
        "commercial carrier - see enrich.py's RJA/SVA header comment for "
        "why this row, unlike the state/charter operators around it, may "
        "see a live adsbdb hit under a different string (its former "
        "legal name, say). This is the carrier's current real name; the "
        "former name 'Saudi Arabian Airlines' is a searchable alias, not "
        "a value ever stored in any table. Primary airframe: Boeing "
        "777-300ER. [DEVELOPER-OBSERVED]",
    ),
    (
        "Gendarmerie Nationale",
        None,
        "QT-v9c-D-05: initially scoped out as 'not a real airline', "
        "reversed by the developer on 2026-09-21. This is the aviation "
        "branch of the French national gendarmerie (ICAO FGN), a state "
        "law-enforcement operator, not a commercial airline - recorded "
        "here so that fact stays visible in-tree. Primary airframe: "
        "Eurocopter/Airbus EC145 helicopter (labelled 'EC145 AIRBUS' in "
        "the delivered art), rendered as a rotorcraft side profile - no "
        "rotorcraft shape bucket exists in _TYPE_SHAPE_BUCKETS, so this "
        "operator is reachable only through Tier 2. [DEVELOPER-OBSERVED]",
    ),
    (
        "Iraqi Government",
        None,
        "QT-v9c-D-05: initially scoped out as 'not a real airline', "
        "reversed by the developer on 2026-09-21. This is the Iraqi "
        "Prime Minister's Office aircraft (ICAO IPF), observed tail "
        "YI-ASF (matching the registration visible in the delivered "
        "art), a state operator, not a commercial airline - recorded "
        "here so that fact stays visible in-tree. Primary airframe: "
        "Boeing 737 in 'REPUBLIC OF IRAQ' government livery - the "
        "delivered art does not depict a distinct VIP/BBJ cabin "
        "configuration, so it is described here as a 737, not "
        "overclaimed as a Boeing Business Jet. [DEVELOPER-OBSERVED]",
    ),
]

# A key must reduce to this shape after normalise_airline_key() - defensive
# boundary check independent of normalise_airline_key()'s own guarantee
# that a hostile/malformed airline_name must never escape the asset
# directory via path construction.
_UNSAFE_KEY_RE = re.compile(r"[\\/]|\.\.")

# The seven base aircraft shapes classify_aircraft_type() classifies into.
# Order is iteration-stable (target_filenames() relies on it) but not a
# priority ranking. Shared contract with the filename convention
# (illustrations/{shape}.png) and render.py's caption labels.
SHAPE_SLUGS = (
    "a320",
    "b737",
    "atr72",
    "beechcraft1900d",
    "embraer",
    "a330",
    "a350",
)

# ICAO type designator (uppercase) -> one of SHAPE_SLUGS. Hand-curated,
# verified out of band, never a live lookup. A missing designator
# degrades to None (treated as "no shape"), never raises.
_TYPE_SHAPE_BUCKETS = {
    # A320 family: Air France, Vueling, Iberia, TAP, Transavia, easyJet,
    # Wizz Air, Volotea, ITA Airways, Tunisair, Pegasus, La Compagnie
    # [excluded from the target set pending re-verification]; KM Malta
    # Airlines (A320neo primary); Amelia (A320 primary).
    "A318": "a320", "A319": "a320", "A320": "a320", "A321": "a320",
    "A20N": "a320", "A21N": "a320",  # A320neo / A321neo
    # B737 family: Transavia, Air Europa, Air Algerie, Royal Air Maroc;
    # TUIfly Belgium (737 MAX 8 primary); ASL Airlines France (adsbdb
    # resolves the pre-2015-rebrand name "Europe Airpost", corrected on
    # read, see enrich.py); KlasJet (737-800 primary, lower-confidence
    # entry - see enrich.py's KLJ row).
    "B731": "b737", "B732": "b737", "B733": "b737", "B734": "b737",
    "B735": "b737", "B736": "b737", "B737": "b737", "B738": "b737",
    "B739": "b737", "B37M": "b737", "B38M": "b737", "B39M": "b737",
    "B3XM": "b737",  # MAX 7/8/9/10
    # ATR72: Air Corsica, Chalair Aviation (Air Corsica's key was renamed
    # from the adsbdb-resolved "CCM Airlines" to its real current name,
    # see enrich.py); Air France Hop ATR72 secondary (see the
    # "Air France Hop"/"atr72" row in _ILLUSTRATION_TARGETS) - ATR42
    # designators map here too since there is no separate ATR42 shape.
    "AT43": "atr72", "AT44": "atr72", "AT45": "atr72", "AT46": "atr72",
    "AT72": "atr72", "AT73": "atr72", "AT75": "atr72", "AT76": "atr72",
    # Beechcraft 1900D: Twin Jet.
    "BE9L": "beechcraft1900d",
    # Embraer E-Jet family: LOT Polish Airlines, Royal Air Maroc
    # minority; Amelia's E145 secondary variant (see the
    # "Amelia"/"embraer" row in _ILLUSTRATION_TARGETS); Air France Hop
    # primary, E170/E175/E190, the numerically dominant regional type
    # since HOP!'s fold-in (see the "Air France Hop" primary entry).
    "E135": "embraer", "E145": "embraer", "E170": "embraer",
    "E75L": "embraer", "E75S": "embraer", "E190": "embraer",
    "E195": "embraer", "E290": "embraer", "E295": "embraer",
    # A330 family: Air Caraibes minority; Corsair (adsbdb's CRL airline
    # endpoint resolves the prior-brand name "Corsairfly", corrected on
    # read, see enrich.py).
    "A332": "a330", "A333": "a330", "A339": "a330",
    # A350 family: Air Caraibes majority, French Bee.
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
    """One of SHAPE_SLUGS for a known ICAO type designator, else `None`.
    Never raises. Always one of the seven hardcoded slugs or `None`,
    never a value derived from the argument, so a hostile designator can
    never reach a filesystem path.
    """
    if not isinstance(icao_type, str) or not icao_type:
        return None
    return _TYPE_SHAPE_BUCKETS.get(icao_type.strip().upper())


def illustration_path_for_key(key):
    """Join `ILLUSTRATION_DIR` and `key + ".png"`. `None` if `key` is
    falsy or contains a path separator or parent-directory segment - this
    is the boundary itself, not reliant on callers already sanitising `key`.
    """
    if not key or _UNSAFE_KEY_RE.search(key):
        return None
    return os.path.join(ILLUSTRATION_DIR, key + ".png")


def generic_fallback_path():
    return os.path.join(ILLUSTRATION_DIR, GENERIC_FALLBACK_FILENAME)


# --- Override resolution -------------------------------------------------
# An uploaded replacement must survive a redeploy, so it cannot live
# inside git-tracked ILLUSTRATION_DIR (`deploy/deploy.sh` rsyncs `server/`
# with `--delete`, excluding only `state`). An override instead lives at
# `{state_dir}/illustration_overrides/{key}.png`.
ILLUSTRATION_OVERRIDE_DIRNAME = "illustration_overrides"

# Process-scoped default; `None` means no override location configured.
_override_state_dir = None


def set_override_state_dir(state_dir):
    """Set the process-wide default state dir the resolver functions
    below fall back to when called without an explicit `state_dir=`.

    Exists because `select_illustration()` is called from deep inside
    `render._build_active_canvas()`, which carries no filesystem-location
    awareness. The explicit `state_dir=` parameter every resolver accepts
    stays the primary, directly testable contract - this setter only
    exists for callers, like the render call chain, that have no way to pass one
    directly. Passing `None` restores the vendored-only behaviour.
    """
    global _override_state_dir
    _override_state_dir = state_dir


def override_dir_for_state_dir(state_dir=None):
    """`{state_dir or process default}/ILLUSTRATION_OVERRIDE_DIRNAME`, or
    `None` when neither is set. Never creates the directory.
    """
    effective = state_dir if state_dir is not None else _override_state_dir
    if not effective:
        return None
    return os.path.join(effective, ILLUSTRATION_OVERRIDE_DIRNAME)


def override_path_for_key(key, state_dir=None):
    """Join the override dir and `key + ".png"`. `None` for a falsy or
    unsafe key (`_UNSAFE_KEY_RE`), or no effective override dir - this is
    the boundary itself, not reliant on caller validation.
    """
    if not key or _UNSAFE_KEY_RE.search(key):
        return None
    override_dir = override_dir_for_state_dir(state_dir)
    if not override_dir:
        return None
    return os.path.join(override_dir, key + ".png")


def resolved_illustration_path(key, state_dir=None):
    """The single seam every tier of `select_illustration()` goes through:
    return the override path for `key` when it exists as a real file, else
    the vendored `illustration_path_for_key(key)` path when THAT exists as
    a real file, else `None`. Never raises.
    """
    override_path = override_path_for_key(key, state_dir)
    if override_path is not None and os.path.isfile(override_path):
        return override_path
    vendored_path = illustration_path_for_key(key)
    if vendored_path is not None and os.path.isfile(vendored_path):
        return vendored_path
    return None


def select_illustration(route, aircraft_type=None, state_dir=None):
    """Illustration path for `route`/`aircraft_type`, resolved through
    four fallback tiers, or `None` if not even the generic fallback
    exists. Never raises.

    Tier 1: `{airline}-{shape}.png` - exact airline+type match.
    Tier 2: `{airline}.png` - airline's own illustration (brand identity
        wins over exact type precision).
    Tier 3: `generic-{shape}.png` - neutral, correct-shape illustration
        for an unrecognised airline.
    Tier 4: `generic-fallback.png` - universal fallback.

    `state_dir`: each tier consults `{state_dir}/illustration_overrides/
    {key}.png` first, vendored file second, via
    `resolved_illustration_path()`. Tier precedence is unaffected - an
    override only replaces its own tier's source.
    """
    try:
        airline_name = route.get("airline_name") if isinstance(route, dict) else None
    except Exception:
        airline_name = None

    airline_key = normalise_airline_key(airline_name)
    shape_key = classify_aircraft_type(aircraft_type)

    # Tier 1: exact airline + shape match.
    if airline_key and shape_key:
        exact = resolved_illustration_path("%s-%s" % (airline_key, shape_key), state_dir)
        if exact is not None:
            return exact

    # Tier 2: known airline, no exact-shape file - brand wins over
    # type precision; still show that airline's own default illustration.
    if airline_key:
        primary = resolved_illustration_path(airline_key, state_dir)
        if primary is not None:
            return primary

    # Tier 3: unrecognized airline, but a recognized+covered shape - show
    # the neutral correct-shape illustration instead of jumping straight
    # to the single universal generic.
    if shape_key:
        neutral = resolved_illustration_path("generic-%s" % shape_key, state_dir)
        if neutral is not None:
            return neutral

    # Tier 4: universal fallback. Key derived from GENERIC_FALLBACK_FILENAME
    # rather than a second hardcoded literal.
    fallback_key = GENERIC_FALLBACK_FILENAME
    if fallback_key.endswith(".png"):
        fallback_key = fallback_key[: -len(".png")]
    fallback = resolved_illustration_path(fallback_key, state_dir)
    if fallback is not None:
        return fallback
    return None


def validate_illustration_file(path):
    """Return a list of human-readable problems with the illustration file
    at `path`, empty when the file is acceptable. Reads `.size`/`.format`
    from the PNG header before calling anything that decodes pixel data,
    so an oversized/decompression-bomb file is rejected without ever being
    fully decoded. Never raises - any Pillow exception is turned into a
    problem string.
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
    """Distinct `resolved_airline_name` values of `_ILLUSTRATION_TARGETS`,
    order-preserving and de-duplicated. `enrich.py`'s ICAO-prefix table is
    checked against this output, so a drift fails the suite instead of
    silently orphaning a callsign-prefix resolution.
    """
    names = []
    for airline_name, _shape, _note in _ILLUSTRATION_TARGETS:
        if airline_name not in names:
            names.append(airline_name)
    return names


def target_filenames():
    """The full illustration hand-off plan: one filename per
    `_ILLUSTRATION_TARGETS` entry, then one `generic-{shape}.png` per
    `SHAPE_SLUGS`, then the universal fallback. Order-preserving and
    de-duplicated. Contrast `required_filenames()` ("must exist right
    now").
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


def target_variants_by_airline():
    """One `(airline_name, [shape, ...])` pair per distinct airline in
    `_ILLUSTRATION_TARGETS`, first-appearance order. A primary-only
    airline maps to an empty list, never `[None]`.

    Shape strings are free-text filename suffixes (e.g. `"a350-1000"`), a
    different domain from `SHAPE_SLUGS`' ICAO-type classification - never
    validate a variant against `SHAPE_SLUGS`.
    """
    order = []
    shapes_by_name = {}
    for airline_name, shape, _note in _ILLUSTRATION_TARGETS:
        if airline_name not in shapes_by_name:
            order.append(airline_name)
            shapes_by_name[airline_name] = []
        if shape is not None:
            shapes_by_name[airline_name].append(shape)
    return [(name, shapes_by_name[name]) for name in order]


def required_filenames():
    """The immovable baseline (`_LIVE_RESOLVED_AIRLINES` filenames plus
    the generic fallback) unioned with every `target_filenames()` entry
    already on disk. Means "must exist and validate right now" - a newly
    delivered file is enforced the moment it lands; contrast
    `target_filenames()`'s "full plan".
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
    disk, in target order - the machine-reportable remainder of the
    illustration hand-off.
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
