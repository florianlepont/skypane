# -*- coding: utf-8 -*-
"""companion/i18n_fr/airlines.py — French strings for the Airlines page
(companion/pages/airlines_page.py, D-05), 20-10-PLAN.md.

One sibling module of the companion/i18n_fr package (see that
package's __init__.py for the auto-merge/duplicate-key contract this
module participates in). Every key here is the exact English source
string a call site in companion/pages/airlines_page.py passes to
companion.i18n.t() — including any "%s"/"%d" placeholder, unchanged.

Deliberately absent (reused from a sibling module rather than
redefined — the auto-merge package raises ValueError on a duplicate
key across sibling modules, see companion/i18n_fr/__init__.py):
- "Airlines" — companion/i18n_fr/nav.py already owns that exact key
  (the nav label, "Compagnies").
- "%s illustration" — companion/i18n_fr/home.py already owns that
  exact key (the recent-flights thumbnail's own alt-text template,
  byte-identical text, "Illustration %s").
- "Delete" — companion/i18n_fr/display.py already owns that exact key
  (the flight-colour-rules delete button, "Supprimer").
- "Prefix" / "First seen" / "Last seen" / "Example callsign" —
  companion/i18n_fr/health.py already owns these exact keys (the
  unresolved-prefix registry table's own column labels).
- "%d of %d shown" / "Clear" — companion/i18n_fr/health.py already
  owns these exact keys (its own filter-bar copy).

Task 1 (20-10-PLAN.md) adds only the "Change pictures"/"Done" toggle's
three strings, pulled forward into this plan's first commit so it is
independently buildable and its own French-render check passes at
that commit (the same precedent 20-01-SUMMARY.md/20-06-SUMMARY.md
document for their own Task 2/3 splits). Task 2 extends this same file
with the rest of the page's sweep.

Copy follows D-09 (20-CONTEXT.md): sentence case, the typographic
apostrophe (U+2019, never a straight quote), and a non-breaking space
(U+00A0) before ":" ";" "?" "!".
"""

CATALOG = {
    # --- The "Change pictures"/"Done" toggle (D-36, 20-10-PLAN.md Task 1) --
    "Change pictures": "Modifier les images",
    "Done": "Terminé",
    "Replace an airline’s picture or add one for an airline that has "
    "none.": "Remplacez l’image d’une compagnie, ou ajoutez-en une pour "
    "une compagnie qui n’en a pas encore.",
}
