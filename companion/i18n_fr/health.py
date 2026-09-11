# -*- coding: utf-8 -*-
"""companion/i18n_fr/health.py — French strings for companion/layout.py's
language-aware date helpers (D-07) and for the Health page
(companion/pages/health_page.py, D-05), 20-03-PLAN.md.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/layout.py or companion/pages/
health_page.py passes to companion.i18n.t()/t_lang() — including any
"%d"/"%s" placeholder, unchanged.

Copy follows D-09: sentence case, the typographic apostrophe (U+2019,
never a straight quote), and a non-breaking space (U+00A0) before
":" ";" "?" "!". The relative-age connector and quantity strings below
additionally carry a real U+00A0 between a number and its unit
(D-07's own example: "il y a 1 j").
"""

CATALOG = {
    # --- companion/layout.py's relative_age_text()/local_clock_text()
    #     (D-07) — the copy lives here rather than as a layout.py
    #     literal so it stays with the rest of the French catalogue. --
    "just now": "à l’instant",
    "%s ago": "il y a %s",
}
