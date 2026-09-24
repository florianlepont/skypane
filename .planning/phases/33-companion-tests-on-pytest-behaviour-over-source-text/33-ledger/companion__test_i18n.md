# Ledger: companion/test_i18n.py

Baseline: `companion__test_i18n.txt`, 24 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | t_lang('Home', 'fr') == 'Accueil' | ported | companion/test_i18n.py::test_t_lang_fr_translates_a_known_key |
| 2 | t_lang('Home', 'en') == 'Home' | ported | companion/test_i18n.py::test_t_lang_en_returns_the_english_source |
| 3 | t_lang() degrades a missing key to the English source unchanged | ported | companion/test_i18n.py::test_t_lang_degrades_a_missing_key_to_the_english_source_unchanged |
| 4 | t() follows prefs.set_request_prefs(lang='fr') and back | ported | companion/test_i18n.py::test_t_follows_set_request_prefs_and_back |
| 5 | prefs.set_request_prefs(lang='de') resolves to 'en' | ported | companion/test_i18n.py::test_prefs_unknown_lang_degrades_to_en |
| 6 | i18n_fr.CATALOG contains every key defined in common.py | ported | companion/test_i18n.py::test_catalog_contains_every_key_defined_in_common |
| 7 | i18n_fr.CATALOG contains every key defined in nav.py | ported | companion/test_i18n.py::test_catalog_contains_every_key_defined_in_nav |
| 8 | every CATALOG value is a str and differs from its English key | ported | companion/test_i18n.py::test_every_catalog_value_is_str_and_differs_from_its_english_key |
| 9 | companion/i18n.py and companion/prefs.py import neither companion.pages nor server | ported | companion/test_i18n.py::test_i18n_and_prefs_import_neither_pages_nor_server |
| 10 | D-08 Check 1: every scanned page-module string is a companion.i18n_fr.CATALOG key (ast-based, source-only scan) | deleted | S: asserted source text (an ast-based scan of the D-05 page-module set for i18n.t()-call/dict/constant string literals lacking a French catalogue entry); no behaviour a rendered page or an imported object can prove the same way — covered instead by the catalogue's own key-set/placeholder/non-empty self-consistency checks (test_every_catalog_value_is_non_empty, test_catalog_placeholders_match_between_key_and_value, test_t_lang_round_trips_every_catalog_key) and the real French page renders below, which are the direct behavioural proof of translation coverage |
| 11 | D-08 Check 2: every companion.i18n_fr.CATALOG key is produced by the D-05 module scan, server/notify.py's own bodies, or a documented exception | deleted | S: asserted source text (the inverse ast-based scan, proving no CATALOG key is orphaned relative to the same page-module scan); no behaviour test can observe "this string is never read from source" without reading source — covered by the same catalogue self-consistency checks and real French page renders as row 10 |
| 12 | D-08 Check 3: Home renders in French (GET /, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Home] |
| 13 | D-08 Check 3: Display renders in French (GET /display, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Display] |
| 14 | D-08 Check 3: Device renders in French (GET /device, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Device] |
| 15 | D-08 Check 3: Flights renders in French (GET /flights, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Flights] |
| 16 | D-08 Check 3: Airlines renders in French (GET /airlines, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Airlines] |
| 17 | D-08 Check 3: Health renders in French (GET /health, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Health] |
| 18 | D-08 Check 3: the login page renders in French | ported | companion/test_i18n.py::test_login_page_renders_in_french |
| 19 | D-08 Check 3: the 404 page renders in French | ported | companion/test_i18n.py::test_404_page_renders_in_french |
| 20 | D-08 Check 3: the calendar-disconnect confirmation page renders in French | ported | companion/test_i18n.py::test_calendar_disconnect_confirm_page_renders_in_french |
| 21 | D-08 Check 4 (D-09): every CATALOG value uses the typographic apostrophe, never a straight quote | ported | companion/test_i18n.py::test_every_catalog_value_uses_the_typographic_apostrophe |
| 22 | D-08 Check 4 (D-09): every CATALOG value uses U+00A0 (not a plain space) before ':'/';'/'?'/'!' | ported | companion/test_i18n.py::test_every_catalog_value_uses_nbsp_before_punctuation |
| 23 | D-08 Check 5: every literal title=/alt=/aria-label=/placeholder= attribute value scanned from the D-05 module set is a companion.i18n_fr.CATALOG key (ast-based, source-only scan; a dynamically-filled attribute is proven by Check 1's own i18n.t() call-argument tracing instead) | deleted | S: asserted source text (an ast-based scan of the D-05 module set's own string constants for a literal title=/alt=/aria-label=/placeholder= attribute value); same reasoning as rows 10/11 — covered by the real French page renders below, which parse (via a real HTTP response) the actual rendered attribute values a browser would see |
| 24 | D-08 Check 6: every genuine English fallback literal scanned from companion/static/*.js (var ALL_CAPS = "..."; ... \|\| "...") is a companion.i18n_fr.CATALOG key (regex-based, boundary stated in this file's own header comment and above _scan_all_js_files_for_fallback_literals()) | deleted | S: asserted source text (a regex scan of companion/static/*.js for a hard-coded English fallback literal); no behaviour surface exists without reading JS source text as a string — covered by the catalogue's own self-consistency checks and the real French page renders, which are the only way this project proves what a JS-rendered fallback actually displays |

### Part 01 (plan 33-04)

- Rubric codes: 5× B (t_lang/t/prefs round-trip and fallback, direct calls into `companion.i18n`/
  `companion.prefs`), 3× B (catalogue completeness/value-shape checks against the imported
  `i18n_fr.CATALOG`/sibling-module `CATALOG` dicts), 1× S (the import-boundary check — rewritten
  from a line-by-line source grep of `i18n.py`/`prefs.py` into a fresh-interpreter subprocess
  proving `companion.pages`/`server` never enter `sys.modules`), 9× B (the real French page/login/
  404/calendar-disconnect-confirm renders, now over `companion_app_server.InProcessAppServer` +
  `http_request`/`login` instead of `companion.test_companion_app._InProcessHarness`), 2× B (the
  two D-09 typographic checks, already over the imported `CATALOG` dict, no source-text read),
  4× S (the ast/regex completeness, dead-translation, attribute-literal and JS-fallback scans —
  deleted; each read a production `.py`/`.js` file as source text with no way to observe the same
  property behaviourally).
- 4 deleted (rows 10, 11, 23, 24), all reason S. 20 ported. 0 pending.
- 3 new tests beyond the 24-row baseline (not tracked as ledger rows — new coverage, not a
  1:1 port): `test_every_catalog_value_is_non_empty`, `test_catalog_placeholders_match_between_key_and_value`,
  `test_t_lang_round_trips_every_catalog_key` — together they are what replaces the deleted
  ast-based completeness/dead-translation scans' catalogue-shape guarantee.
- New module: `companion/test_i18n.py` (rewritten in place). No longer imports
  `companion.test_companion_app` — its render checks use a module-scoped
  `companion_app_server.InProcessAppServer` fixture built locally in this file.
