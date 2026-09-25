# -*- coding: utf-8 -*-
"""French strings for the three frame-state headlines and the three
delay sentences. Every key is the exact English source string
`companion/frame_state.py` defines as a module constant, including the
"%s" placeholder.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The middle dot ("·") in the held headline is a visual
separator, not one of those four characters, so it takes no leading
non-breaking space.

"Next update ≈ %s", "Expected since %s" and "Applies the next time the
frame wakes up." are deliberately absent, already keyed in sibling
modules — the auto-merge package raises ValueError on a duplicate key.
"Expected since %s" and the "applies" sentence carry a known, tracked
wording mismatch against this module's own copy: their sibling entries
use a different grammatical agreement than this context calls for,
left for the plan that retires their other consumer to reconcile.
"""

CATALOG = {
    "Next wake around %s · quiet hours": "Prochain réveil vers %s · heures calmes",
    "Applies at the next wake, around %s.": "S’applique au prochain réveil, vers %s.",
    "Applies when quiet hours end, around %s.": "S’applique à la fin des heures calmes, vers %s.",
}
