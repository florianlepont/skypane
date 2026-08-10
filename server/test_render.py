#!/usr/bin/env python3
"""Contract harness for server/plane/render.py's state colour field and
label (PLANE-01/PLANE-02 visual contract, 02-UI-SPEC.md Revision 2).

Stdlib-only, plus the module under test (server.plane.render,
server.panel_format) - render.py transitively imports Pillow, so this
harness must be run under server/.venv's interpreter, not the bare system
python3. Exits 0 only when every check below passes; any failure (or
exception - none is ever swallowed into a pass) exits 1.

This harness asserts on the rendered canvas and packed bytes only - never
on a screenshot. "Dominant nibble" means the most common nibble by count,
which is unambiguous for a full-bleed field.

Usage:
    server/.venv/bin/python3 server/test_render.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 15

IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN = 0, 1, 2, 3, 4, 5
NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
LEGAL_NIBBLES = {NIBBLE_BLACK, NIBBLE_WHITE, NIBBLE_YELLOW, NIBBLE_RED, NIBBLE_BLUE, NIBBLE_GREEN}

TEST_FLIGHT = {"hex": "3985a7", "callsign": "AF1380"}


def nibble_counts(buf):
    counts = {}
    for b in buf:
        for nibble in ((b >> 4) & 0xF, b & 0xF):
            counts[nibble] = counts.get(nibble, 0) + 1
    return counts


def dominant_nibble(buf):
    counts = nibble_counts(buf)
    return max(counts, key=counts.get)


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.plane.render as render
        import server.panel_format as panel_format
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before this
        # slice's render.py state-colour/label work exists. It must fail -
        # Task 3 turns it green.
        print("FAIL import server.plane.render / server.panel_format - %r" % (exc,))
        print("render: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    ctx = {}

    # 1-2. Both active states pack to exactly 960000 bytes with only legal nibble codes.
    def _departing_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "departing")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "departing render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "departing render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["departing_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'departing') packs to exactly 960000 bytes with only legal nibbles", _departing_packs_correctly)

    def _arriving_packs_correctly():
        buf = render.render_panel(TEST_FLIGHT, "arriving")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "arriving render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        bad = set(nibble_counts(buf)) - LEGAL_NIBBLES
        if bad:
            return False, "arriving render contains illegal nibble codes: %r" % (sorted(bad),)
        ctx["arriving_bytes"] = buf
        return True, ""
    check("render_panel(flight, 'arriving') packs to exactly 960000 bytes with only legal nibbles", _arriving_packs_correctly)

    # 3-4. Dominant nibble per state.
    def _departing_dominant_is_blue():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_BLUE:
            return False, "departing render's dominant nibble is 0x%x, expected 0x5 (Blue)" % dom
        return True, ""
    check("departing render's dominant nibble is 0x5 (Blue)", _departing_dominant_is_blue)

    def _arriving_dominant_is_green():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        dom = dominant_nibble(buf)
        if dom != NIBBLE_GREEN:
            return False, "arriving render's dominant nibble is 0x%x, expected 0x6 (Green)" % dom
        return True, ""
    check("arriving render's dominant nibble is 0x6 (Green)", _arriving_dominant_is_green)

    # 5-6. Black drops out of the active states (UI-SPEC Revision 2).
    def _departing_has_no_black():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        if NIBBLE_BLACK in nibble_counts(buf):
            return False, "departing render contains a Black (0x0) nibble - UI-SPEC's 'Black drops out of the active states' violated"
        return True, ""
    check("departing render contains no Black (0x0) nibble", _departing_has_no_black)

    def _arriving_has_no_black():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        if NIBBLE_BLACK in nibble_counts(buf):
            return False, "arriving render contains a Black (0x0) nibble - UI-SPEC's 'Black drops out of the active states' violated"
        return True, ""
    check("arriving render contains no Black (0x0) nibble", _arriving_has_no_black)

    # 7-8. Foreground content exists (at least one White nibble).
    def _departing_has_white():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        if NIBBLE_WHITE not in nibble_counts(buf):
            return False, "departing render contains no White (0x1) nibble - no foreground content drawn"
        return True, ""
    check("departing render contains at least one White (0x1) nibble (foreground content)", _departing_has_white)

    def _arriving_has_white():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        if NIBBLE_WHITE not in nibble_counts(buf):
            return False, "arriving render contains no White (0x1) nibble - no foreground content drawn"
        return True, ""
    check("arriving render contains at least one White (0x1) nibble (foreground content)", _arriving_has_white)

    # 9. Empty state is unchanged: White-dominant, at least one Black pixel.
    def _empty_state_white_dominant_with_black():
        buf = render.render_panel(None, "empty")
        if len(buf) != panel_format.IMAGE_BYTES:
            return False, "empty render is %d bytes, expected %d" % (len(buf), panel_format.IMAGE_BYTES)
        counts = nibble_counts(buf)
        dom = max(counts, key=counts.get)
        if dom != NIBBLE_WHITE:
            return False, "empty render's dominant nibble is 0x%x, expected 0x1 (White)" % dom
        if NIBBLE_BLACK not in counts:
            return False, "empty render contains no Black (0x0) nibble - expected Black text"
        return True, ""
    check("empty-state render is White-dominant and contains at least one Black nibble", _empty_state_white_dominant_with_black)

    # 10-11. Yellow/Red are reserved for later phases - never used this phase.
    def _departing_has_no_yellow_or_red():
        buf = ctx.get("departing_bytes")
        if buf is None:
            return False, "no departing bytes captured from a previous check"
        counts = nibble_counts(buf)
        bad = {NIBBLE_YELLOW, NIBBLE_RED} & set(counts)
        if bad:
            return False, "departing render contains reserved nibble(s): %r" % (sorted(bad),)
        return True, ""
    check("departing render contains no Yellow (0x2) or Red (0x3) nibble (cross-phase reservation)", _departing_has_no_yellow_or_red)

    def _arriving_has_no_yellow_or_red():
        buf = ctx.get("arriving_bytes")
        if buf is None:
            return False, "no arriving bytes captured from a previous check"
        counts = nibble_counts(buf)
        bad = {NIBBLE_YELLOW, NIBBLE_RED} & set(counts)
        if bad:
            return False, "arriving render contains reserved nibble(s): %r" % (sorted(bad),)
        return True, ""
    check("arriving render contains no Yellow (0x2) or Red (0x3) nibble (cross-phase reservation)", _arriving_has_no_yellow_or_red)

    # 12-13. Pre-pack canvas anti-aliasing guard: exactly two palette
    #        indices, per 02-RESEARCH.md's own verified Image.getcolors()
    #        method.
    def _departing_canvas_has_two_indices():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "departing")
        colors = canvas.getcolors()
        if colors is None or len(colors) != 2:
            return False, "departing canvas has %r distinct palette indices, expected exactly 2" % (
                None if colors is None else len(colors),
            )
        return True, ""
    check("departing pre-pack canvas contains exactly two distinct palette indices (no anti-aliasing)", _departing_canvas_has_two_indices)

    def _arriving_canvas_has_two_indices():
        if not hasattr(render, "build_canvas"):
            return False, "server.plane.render has no build_canvas() - test cannot reach a pre-pack canvas without it"
        canvas = render.build_canvas(TEST_FLIGHT, "arriving")
        colors = canvas.getcolors()
        if colors is None or len(colors) != 2:
            return False, "arriving canvas has %r distinct palette indices, expected exactly 2" % (
                None if colors is None else len(colors),
            )
        return True, ""
    check("arriving pre-pack canvas contains exactly two distinct palette indices (no anti-aliasing)", _arriving_canvas_has_two_indices)

    # 14. Determinism: rendering the same flight twice is byte-identical.
    def _rendering_is_deterministic():
        first = render.render_panel(TEST_FLIGHT, "departing")
        second = render.render_panel(TEST_FLIGHT, "departing")
        if first != second:
            return False, "rendering the same flight twice produced different bytes - render_panel is not deterministic"
        return True, ""
    check("rendering the same flight twice produces byte-identical output (determinism)", _rendering_is_deterministic)

    # 15. State actually changes the output.
    def _departing_and_arriving_differ():
        departing = ctx.get("departing_bytes")
        arriving = ctx.get("arriving_bytes")
        if departing is None or arriving is None:
            return False, "missing captured bytes from a previous check"
        if departing == arriving:
            return False, "departing and arriving renders of the same flight are byte-identical - state does not change output"
        return True, ""
    check("departing and arriving renders of the same flight differ in bytes (state changes output)", _departing_and_arriving_differ)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("render: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
