# -*- coding: utf-8 -*-
"""companion/i18n_fr/frame_state.py — French strings for the three
frame-state headlines and the three delay sentences (D-03/D-04,
22-02-PLAN.md Task 2).

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string `companion/frame_state.py` defines as a module constant
(`HEADLINE_DUE`/`HEADLINE_HELD`/`HEADLINE_LATE`/`DELAY_DUE`/
`DELAY_HELD`/`DELAY_UNKNOWN`), including the "%s" placeholder,
unchanged — companion.i18n.t() looks these up by that exact string.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The middle dot ("·") in the held headline is not
punctuation requiring a leading non-breaking space under that rule —
it is a visual separator, not one of ":" ";" "?" "!", matching how the
English source treats it.

Three of the six English source strings are DELIBERATELY ABSENT here,
each a documented, load-bearing omission rather than an oversight —
the package's own auto-merge `_build_catalog()` raises `ValueError` on
a duplicate key across sibling modules, and all three already have a
live entry elsewhere today, each predating this module:

  - `"Next update ≈ %s"` — already keyed in `companion/i18n_fr/home.py`
    to the IDENTICAL value this module would otherwise add
    ("Prochaine mise à jour ≈ %s"). No behaviour changes by omitting
    it; `companion.i18n.t()` resolves it from `home.py`'s entry either
    way, since the merged CATALOG is one flat dict keyed by the
    English string regardless of which sibling module supplied it.
  - `"Expected since %s"` — already keyed in `home.py` to "Attendue
    depuis %s" (feminine agreement, from that call site's own
    grammatical context). 22-UI-SPEC.md's Copywriting Contract
    specifies "Attendu depuis %s" (no agreement) for THIS module's
    own held/late-headline context — a real, currently-UNRESOLVED
    text discrepancy between the two call sites sharing one English
    key, left for the plan that actually deletes `home.py`'s
    NEXT_UPDATE_TEMPLATE/EXPECTED_SINCE_TEMPLATE consumer (22-04/
    22-05, per this phase's own "delete them there, in the same
    commit as their French entries" instruction) to reconcile,
    because THIS plan (22-02) wires no consumer to this new module
    yet and therefore cannot make either value live incorrectly.
  - `"Applies the next time the frame wakes up."` — already keyed in
    `companion/i18n_fr/display.py` to "S’applique la prochaine fois
    que le cadre se réveille." (the retired `QUICK_ACTION_APPLIES_
    SENTENCE`'s own French value). 22-UI-SPEC.md's Copywriting
    Contract specifies "S’applique au prochain réveil du cadre."
    instead — the same unresolved-until-retirement situation as
    above.

22-02-SUMMARY.md records both discrepancies explicitly; they are a
known, tracked gap, not a silent omission — see that file for the full
reasoning and the specific downstream plan expected to close it.
"""

CATALOG = {
    # --- The one genuinely new headline (22-UI-SPEC.md §3.3's
    #     condition table) — "Next update ≈ %s" and "Expected since %s"
    #     are deliberately NOT redefined here; see the module docstring
    #     above for why.
    "Next wake around %s · quiet hours": "Prochain réveil vers %s · heures calmes",

    # --- The two genuinely new delay-sentence branches (D-04) —
    #     "Applies the next time the frame wakes up." is deliberately
    #     NOT redefined here; see the module docstring above for why.
    "Applies at the next wake, around %s.": "S’applique au prochain réveil, vers %s.",
    "Applies when quiet hours end, around %s.": "S’applique à la fin des heures calmes, vers %s.",
}
