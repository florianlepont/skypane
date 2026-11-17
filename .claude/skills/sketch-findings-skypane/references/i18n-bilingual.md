# Bilingual UI (English / French)

- Every user-facing string literal is an `i18n.msg("<id>", "<English>")` `Message`; `i18n.t()` and
  `t_lang()` accept only `Message` objects. French lives in `companion/i18n_fr/` (26 modules, one
  per area, `MESSAGES = {id: text}`); the English is declared next to the code that uses it. A string
  with a number uses `%d`/`%s`; the JS-side templates use `#` instead (the i18n test scans French
  renders for a stray `%s`/`%d`/`{}`).
- French copy: sentence case, typographic apostrophe (U+2019), a no-break space (U+00A0) before
  `:` `;` `?` `!`. "FR"/"EN" are identifiers, not translated.
- Page names: see `navigation.md`. Concept words: frame / cadre, look / allure, airline /
  compagnie. Tab bar French labels are short (Vols, Lieu, Plus, Équipe, Éditeur, Journal).
- Language is a cookie-backed preference (Account page and the More panel's Settings group);
  it never changes the route.
- Layout must hold French: longer words wrap or ellipsise, never clip a control; check at 360px.
- Tests: `companion/test_i18n.py` (every id has a French string, no stray placeholders),
  `companion/test_browser_french_fit.py`, the Components browser test (EN and FR).
- Dead id: `nav.frame_tools` (declared in `ui_base.py`, translated, unused).
