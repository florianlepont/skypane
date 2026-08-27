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

## Filenames mirror the data source, never the current public brand name

Every illustration filename (primary or secondary-variant) is derived from
the literal `airline_name` string `adsbdb`'s API actually resolves - never
from the airline's current public brand name, and never hand-typed. This
matters because `adsbdb`'s crowdsourced database sometimes still resolves
an airline's pre-rebrand legal/trading name years after a real rebrand:
`ccm-airlines.png` stays named for "CCM Airlines" even though the real
airline rebranded to Air Corsica in 2013, and Phase 3.1's own live
resolution (`03.1-LIVE-RESOLUTION.md`) found two more cases of exactly this
pattern - ASL Airlines France resolves as `"Europe Airpost"` (its
pre-2016-rebrand name) and Corsair International resolves as
`"Corsairfly"` (a genuine prior brand name) - so both are filed under
those older names, not D-03's current-brand labels. Renaming a file to
match the "correct" current brand would silently make every real flight of
that carrier fall through to a lower fallback tier, with no error anywhere
- see `03.1-LIVE-RESOLUTION.md`'s recorded live-callsign evidence for each.
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
    ("CCM21AW", "CCM Airlines"),
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
#   - `resolved_airline_name` is a live-verified adsbdb-resolved
#     airline_name string, never a guess and never the airline's current
#     public brand name where the two differ (see the module docstring's
#     "Filenames mirror the data source" section for Europe Airpost/
#     Corsairfly).
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
# Amelia International and La Compagnie are deliberately absent -
# 03.1-LIVE-RESOLUTION.md marks both `[UNRESOLVED]` (no adsbdb code could
# be trusted this session for either). Add them here with zero other code
# change once a real callsign confirms their resolved name.
_ILLUSTRATION_TARGETS = [
    # --- Baseline: already-confirmed resolutions, primary files ---
    ("Air France", None, "D-03 baseline; [VERIFIED-CALLSIGN]"),
    ("Iberia Airlines", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("TAP Portugal", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Air Algerie", None, "D-03 baseline; [VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("CCM Airlines", None, "D-03/D-04 baseline, A320 primary (P-04); [VERIFIED-CALLSIGN]"),
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
        "Europe Airpost",
        None,
        "D-03 lists this airline as 'ASL Airlines France' - adsbdb resolves the pre-2016-rebrand name; [VERIFIED-CALLSIGN]",
    ),
    ("Tunisair", None, "[VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Pegasus Airlines", None, "[VERIFIED-CALLSIGN]"),
    ("Chalair Aviation", None, "[VERIFIED-AIRLINE-ENDPOINT-ONLY]"),
    ("Twin Jet", None, "[VERIFIED-CALLSIGN]"),
    (
        "Corsairfly",
        None,
        "D-03 lists this airline as 'Corsair International' - adsbdb resolves a genuine prior brand name; [VERIFIED-AIRLINE-ENDPOINT-ONLY]",
    ),
    # --- P-04 secondary-variant files for mixed-fleet airlines ---
    ("CCM Airlines", "atr72", "D-03/D-04 mixed-fleet secondary (P-04)"),
    ("Transavia France", "a320", "D-05 fleet-transition secondary (P-04)"),
    ("Royal Air Maroc", "embraer", "D-03 mixed-fleet secondary (P-04)"),
    ("Air Caraïbes", "a330", "D-03 mixed-fleet secondary (P-04)"),
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
    # Compagnie [excluded from the target set pending re-verification])
    "A318": "a320", "A319": "a320", "A320": "a320", "A321": "a320",
    "A20N": "a320", "A21N": "a320",  # A320neo / A321neo
    # B737 family (D-03: Transavia, Air Europa, Air Algerie, Europe
    # Airpost/ASL Airlines France, Royal Air Maroc)
    "B731": "b737", "B732": "b737", "B733": "b737", "B734": "b737",
    "B735": "b737", "B736": "b737", "B737": "b737", "B738": "b737",
    "B739": "b737", "B37M": "b737", "B38M": "b737", "B39M": "b737",
    "B3XM": "b737",  # MAX 7/8/9/10
    # ATR72 (D-03: CCM Airlines/Air Corsica, Chalair Aviation) - per P-06,
    # ATR42 designators map here too since D-03's table has no separate
    # ATR42 shape.
    "AT43": "atr72", "AT44": "atr72", "AT45": "atr72", "AT46": "atr72",
    "AT72": "atr72", "AT73": "atr72", "AT75": "atr72", "AT76": "atr72",
    # Beechcraft 1900D (D-03: Twin Jet)
    "BE9L": "beechcraft1900d",
    # Embraer E-Jet family (D-03: LOT Polish Airlines, Amelia International
    # [excluded from the target set pending re-verification], Royal Air
    # Maroc minority)
    "E135": "embraer", "E145": "embraer", "E170": "embraer",
    "E75L": "embraer", "E75S": "embraer", "E190": "embraer",
    "E195": "embraer", "E290": "embraer", "E295": "embraer",
    # A330 family (D-03: Air Caraibes minority, Corsairfly)
    "A332": "a330", "A333": "a330", "A339": "a330",
    # A350 family (D-03: Air Caraibes majority, French Bee)
    "A359": "a350", "A35K": "a350",
}


def normalise_airline_key(airline_name):
    """Return a deterministic, filesystem-safe slug for `airline_name`, or
    `None` for anything falsy or non-string - mirrors enrich.py's
    `normalise_callsign()` never-raises discipline. Pure, no I/O.

    `normalise_airline_key("Air Algérie")` -> `"air-algerie"`
    `normalise_airline_key("CCM Airlines")` -> `"ccm-airlines"`
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
