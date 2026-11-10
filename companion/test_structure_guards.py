"""File-length and function-length guards for the companion app's
production code.

The measurement itself lives in `test-support/companion_structure.py`
(stdlib `ast`) — this module only imports its already-computed results,
never `ast`/`inspect`/`tokenize`/`linecache` itself (companion/test_suite_guards.py
rule G2) and never reads a source file as text (rule G3).

Both ceilings below (`FILE_LINE_LIMIT`, `FUNCTION_LINE_LIMIT`) are now
held with no allowlist standing in for work still owed: this phase's
earlier plans shrank every oversized production file and split every
overlong function, and this phase's own closing plan retired the two
mid-phase allowances a still-in-progress snapshot once needed. The one
file still over `FILE_LINE_LIMIT` is named, permanently, in
`TRACKED_FILE_EXCEPTIONS` with a one-line reason; any other file or
function crossing a ceiling from here on is a real, new offender this
guard is meant to catch.

Companion test modules (`companion/test_*.py`) are outside the ceiling
entirely: the audit findings this guard enforces scope to production
code only, and test modules are already split by concern under this
project's own established test-migration conventions — a second,
unrelated size discipline for test files does not belong in this guard.
"""

import companion_structure

# Measured at this plan's base commit via companion_structure.oversized_files()
# / long_functions() with the ceilings below. If a later run of the helper
# disagrees with this file, trust the helper — it is the source of truth —
# and update these sets, not the ceiling.
FILE_LINE_LIMIT = 1500
FUNCTION_LINE_LIMIT = 80

# Files that are expected to stay over the ceiling permanently, with a
# named reason each (never an empty string — test 3 below enforces it).
TRACKED_FILE_EXCEPTIONS = {
    "companion/static/style.css": (
        "one served stylesheet; splitting it adds a <link> to every page's "
        "<head> and a request per page, a rendered-output change this "
        "phase forbids"
    ),
}


def test_no_companion_file_exceeds_the_line_ceiling():
    offenders = companion_structure.oversized_files(limit=FILE_LINE_LIMIT)
    counts = companion_structure.file_line_counts()
    unexpected = [path for path in offenders if path not in TRACKED_FILE_EXCEPTIONS]
    assert unexpected == [], (
        "new file(s) over the %d-line ceiling, not in TRACKED_FILE_EXCEPTIONS: %s" % (
            FILE_LINE_LIMIT,
            ", ".join("%s (%d lines)" % (path, counts[path]) for path in unexpected),
        )
    )


def test_no_production_function_exceeds_the_code_line_ceiling():
    offenders = companion_structure.long_functions(limit=FUNCTION_LINE_LIMIT)
    counts = companion_structure.function_code_lines()
    assert offenders == [], (
        "function(s) over the %d-code-line ceiling, with no pending allowlist left to "
        "excuse them: %s" % (
            FUNCTION_LINE_LIMIT,
            ", ".join("%s (%d lines)" % (key, counts[key]) for key in offenders),
        )
    )


def test_tracked_exception_reasons_are_non_empty():
    for path, reason in TRACKED_FILE_EXCEPTIONS.items():
        assert isinstance(reason, str) and reason.strip(), (
            "TRACKED_FILE_EXCEPTIONS[%r] must carry a non-empty reason" % (path,)
        )
