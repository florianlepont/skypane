"""File-length and function-length guards for the companion app's
production code.

The measurement itself lives in `test-support/companion_structure.py`
(stdlib `ast`) — this module only imports its already-computed results,
never `ast`/`inspect`/`tokenize`/`linecache` itself (companion/test_suite_guards.py
rule G2) and never reads a source file as text (rule G3).

Both ceilings below (`FILE_LINE_LIMIT`, `FUNCTION_LINE_LIMIT`) are already
exceeded by pre-existing production code, measured at this plan's base
commit. Rather than fail the suite outright, every offender that exists
today is named in an explicit allowlist (`TRACKED_FILE_EXCEPTIONS`,
`PENDING_OVERSIZED_FILES`, `PENDING_LONG_FUNCTIONS`); the guard's real job
is catching a NEW offender, not the four files and twelve functions this
phase itself exists to shrink. `PENDING_OVERSIZED_FILES` and
`PENDING_LONG_FUNCTIONS` are expected to shrink as later plans in this
phase land, and this phase's closing plan is expected to empty both.

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

# Production .py files over FILE_LINE_LIMIT today, expected to shrink to
# nothing as this phase's later plans split them.
PENDING_OVERSIZED_FILES = {
    "companion/app.py",
    "companion/layout.py",
    "companion/pages/config_page.py",
    "companion/pages/health_page.py",
}

# Qualified function names over FUNCTION_LINE_LIMIT today, expected to
# shrink to nothing as this phase's later plans split them.
PENDING_LONG_FUNCTIONS = {
    "companion/ui_components.py::frame_strip_html",
    "companion/layout.py::page_shell",
    "companion/pages/airlines_page.py::_airline_card_html",
    "companion/pages/config_page.py::_aspect_card_html",
    "companion/pages/config_page.py::_calendar_connection_html",
    "companion/pages/config_page.py::handle_post",
    "companion/pages/config_page.py::notifications_group",
    "companion/pages/config_page.py::render",
    "companion/pages/health_page.py::battery_sparkline_svg",
    "companion/pages/history_page.py::_history_cards_html",
}


def test_no_companion_file_exceeds_the_line_ceiling():
    offenders = companion_structure.oversized_files(limit=FILE_LINE_LIMIT)
    allowed = set(TRACKED_FILE_EXCEPTIONS) | PENDING_OVERSIZED_FILES
    counts = companion_structure.file_line_counts()
    unexpected = [path for path in offenders if path not in allowed]
    assert unexpected == [], (
        "new file(s) over the %d-line ceiling, not in TRACKED_FILE_EXCEPTIONS or "
        "PENDING_OVERSIZED_FILES: %s" % (
            FILE_LINE_LIMIT,
            ", ".join("%s (%d lines)" % (path, counts[path]) for path in unexpected),
        )
    )


def test_no_production_function_exceeds_the_code_line_ceiling():
    offenders = companion_structure.long_functions(limit=FUNCTION_LINE_LIMIT)
    counts = companion_structure.function_code_lines()
    unexpected = [key for key in offenders if key not in PENDING_LONG_FUNCTIONS]
    assert unexpected == [], (
        "new function(s) over the %d-code-line ceiling, not in PENDING_LONG_FUNCTIONS: %s" % (
            FUNCTION_LINE_LIMIT,
            ", ".join("%s (%d lines)" % (key, counts[key]) for key in unexpected),
        )
    )


def test_tracked_exception_reasons_are_non_empty():
    for path, reason in TRACKED_FILE_EXCEPTIONS.items():
        assert isinstance(reason, str) and reason.strip(), (
            "TRACKED_FILE_EXCEPTIONS[%r] must carry a non-empty reason" % (path,)
        )
