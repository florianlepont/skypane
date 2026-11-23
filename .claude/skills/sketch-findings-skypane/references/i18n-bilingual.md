# Bilingual UI (English / French)

- Every user-facing string literal is an `i18n.msg("<id>", "<English>")` `Message`; `i18n.t()` and
  `t_lang()` accept only `Message` objects. French lives in `companion/i18n_fr/` (about 25 modules, one
  per area, `MESSAGES = {id: text}`); the English is declared next to the code that uses it. A string
  with a number uses `%d`/`%s`; the JS-side templates use `#` instead (the i18n test scans French
  renders for a stray `%s`/`%d`/`{}`).
- French copy: sentence case, typographic apostrophe (U+2019), a no-break space (U+00A0) before
  `:` `;` `?` `!`. "FR"/"EN" are identifiers, not translated.
- Page names: see `navigation.md`; one name per page, the same on the tab, the sidebar and the
  title (Flights / Vols, Location / Lieu, Airlines / Compagnies, My frames / Mes cadres, System /
  Système). Concept words: frame / cadre, look / allure, airline / compagnie. The French word
  "Airlines" never appears in a French value (a catalogue test refuses it). Console bar labels stay
  short (Équipe, Éditeur).
- Words the latest pages fixed: a retired frame's header reads "Retired · Belonged to <address>" /
  "Retiré · Appartenait à <address>"; the foreign-frame marker "You are viewing <address>'s frame" /
  "Vous consultez le cadre de <address>" with "Back to Fleet" / "Retour à la flotte"; the leave
  dialog "Leave without saving?" / "Quitter sans enregistrer ?"; the editor's "Known by name only"
  / "Connues par leur nom seulement" and "Name it" / "Rename" / "Reset to the original name"; Fleet
  groups "Live / Waiting to be paired / Retired" / "En service / En attente d’appairage / Retirés".
- Language is a cookie-backed preference (Account page and the More panel's Settings group);
  it never changes the route.
- Layout must hold French: longer words wrap or ellipsise, never clip a control; check at 360px.
- Tests: `companion/test_i18n.py` (every id has a French string, no stray placeholders),
  `companion/test_browser_french_fit.py`, the Components browser test (EN and FR).
- Dead id: `nav.frame_tools` (declared in `ui_base.py`, translated, unused).
