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
France, the numerically dominant prefix in raw traffic) resolved only 2 of
20 and usually falls to the fallback too.

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
| VOE8KA    | "Volotea"                            | no - recorded for status only |

All seven calls returned a full route (no misses among this set). VOE8KA
(Volotea) was queried per 03-RESEARCH.md's instruction to resolve its
previously-`[ASSUMED]`-unconfirmed status, not to request art for it - the
plan explicitly scopes the hand-off to the six confirmed-hit carriers above
plus the one generic fallback (03-UI-SPEC.md's "Illustration Asset
Contract" table, 7 files total). Volotea's now-confirmed hit is recorded
here for completeness only; `required_filenames()` deliberately excludes
it. `EJU`/`KMM` are not re-queried here - `server/plane/enrich.py`'s module
docstring and 02-RESEARCH.md already document them as confirmed misses.

Filenames are derived from these exact live-resolved strings via
`normalise_airline_key()`, never hand-typed - see `required_filenames()`.
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
# checkpoint), mirroring render.SILHOUETTE_SOURCE_NOSE.
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
