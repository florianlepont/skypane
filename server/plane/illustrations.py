#!/usr/bin/env python3
"""Per-airline aircraft illustration selection (D-06, D-08, D-09, D-19,
PLANE-01/PLANE-02).

Selection keys off `route["airline_name"]`, which `enrich.lookup_route()`
already returns - no new enrichment call (D-06). Coverage is transitively
limited by that lookup's real-world hit rate: `adsbdb` resolved only 52.6%
of this airport's traffic in Phase 2's live test
(`server/plane/enrich.py`'s module docstring). `EJU` (easyJet Europe) and
`KMM` (KM Malta Airlines) are confirmed misses and will ALWAYS render the
generic fallback no matter what art exists for them; `TVF` (Transavia
France, the numerically dominant prefix in raw traffic) resolves only 2 of
20 and therefore still often falls to the fallback.

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


def select_illustration(route):
    """Return the illustration path for `route` (a route dict, or `None`),
    or `None` if not even the generic fallback file exists. Never raises
    for any input, including a non-dict `route` or a non-string
    `airline_name`.
    """
    try:
        airline_name = route.get("airline_name") if isinstance(route, dict) else None
    except Exception:
        airline_name = None

    key = normalise_airline_key(airline_name)
    if key is not None:
        path = illustration_path_for_key(key)
        if path is not None and os.path.isfile(path):
            return path

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


def required_filenames():
    """Return the ordered list of filenames the hand-off must deliver: one
    per live-resolved covered airline (see the module docstring's table),
    plus the generic fallback. Single source of truth for HANDOFF.md,
    Task 2's validation, and this module's own --validate.
    """
    names = []
    for _callsign, airline_name in _LIVE_RESOLVED_AIRLINES:
        key = normalise_airline_key(airline_name)
        if key:
            names.append(key + ".png")
    names.append(GENERIC_FALLBACK_FILENAME)
    return names


def _validate_directory():
    """Validate every required file plus flag any unexpected .png in
    ILLUSTRATION_DIR. Returns True if everything passes.
    """
    required = required_filenames()
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
        required_set = set(required)
        for entry in sorted(os.listdir(ILLUSTRATION_DIR)):
            if entry.endswith(".png") and entry not in required_set:
                ok = False
                print("FAIL unexpected file not in the required set: %s" % entry)
    else:
        ok = False
        print("FAIL illustration directory does not exist: %s" % ILLUSTRATION_DIR)

    return ok


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate", action="store_true", help="Validate every required file in the illustration directory; exit non-zero on any problem."
    )
    parser.add_argument("--required", action="store_true", help="Print required_filenames(), one per line.")
    args = parser.parse_args(argv)

    if args.required:
        for name in required_filenames():
            print(name)
        return 0

    if args.validate:
        ok = _validate_directory()
        return 0 if ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
