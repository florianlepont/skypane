# -*- coding: utf-8 -*-
"""French strings for the frame-state held headline and the two delay
sentences companion/frame_state.py owns outright (the due headline, the
late headline and the unknown-delay sentence are keyed in sibling
modules — home.py and display.py respectively — since those wordings
are shared with a page-level consumer).

Every entry is migrated onto a stable message id: the source-side
Message is declared where the English constant already lives
(companion/frame_state.py, companion/ui_base.py), never here — this
module only carries each id's French translation.

Copy follows sentence case, the typographic apostrophe (U+2019, never
a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The middle dot ("·") in the held headline is a visual
separator, not one of those four characters, so it takes no leading
non-breaking space.
"""

MESSAGES = {
    "frame_state.next_wake_around_quiet_hours": "Prochain réveil vers %s · heures calmes",
    "frame_state.applies_at_the_next_wake_around": "S’applique au prochain réveil, vers %s.",
    "frame_state.applies_when_quiet_hours_end_around": "S’applique à la fin des heures calmes, vers %s.",
}
