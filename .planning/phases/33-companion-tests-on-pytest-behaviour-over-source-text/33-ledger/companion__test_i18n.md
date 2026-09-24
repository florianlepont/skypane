# Ledger: companion/test_i18n.py

Baseline: `companion__test_i18n.txt`, 24 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | t_lang('Home', 'fr') == 'Accueil' | pending | |
| 2 | t_lang('Home', 'en') == 'Home' | pending | |
| 3 | t_lang() degrades a missing key to the English source unchanged | pending | |
| 4 | t() follows prefs.set_request_prefs(lang='fr') and back | pending | |
| 5 | prefs.set_request_prefs(lang='de') resolves to 'en' | pending | |
| 6 | i18n_fr.CATALOG contains every key defined in common.py | pending | |
| 7 | i18n_fr.CATALOG contains every key defined in nav.py | pending | |
| 8 | every CATALOG value is a str and differs from its English key | pending | |
| 9 | companion/i18n.py and companion/prefs.py import neither companion.pages nor server | pending | |
| 10 | D-08 Check 1: every scanned page-module string is a companion.i18n_fr.CATALOG key (ast-based, source-only scan) | pending | |
| 11 | D-08 Check 2: every companion.i18n_fr.CATALOG key is produced by the D-05 module scan, server/notify.py's own bodies, or a documented exception | pending | |
| 12 | D-08 Check 3: Home renders in French (GET /, lang=fr) | pending | |
| 13 | D-08 Check 3: Display renders in French (GET /display, lang=fr) | pending | |
| 14 | D-08 Check 3: Device renders in French (GET /device, lang=fr) | pending | |
| 15 | D-08 Check 3: Flights renders in French (GET /flights, lang=fr) | pending | |
| 16 | D-08 Check 3: Airlines renders in French (GET /airlines, lang=fr) | pending | |
| 17 | D-08 Check 3: Health renders in French (GET /health, lang=fr) | pending | |
| 18 | D-08 Check 3: the login page renders in French | pending | |
| 19 | D-08 Check 3: the 404 page renders in French | pending | |
| 20 | D-08 Check 3: the calendar-disconnect confirmation page renders in French | pending | |
| 21 | D-08 Check 4 (D-09): every CATALOG value uses the typographic apostrophe, never a straight quote | pending | |
| 22 | D-08 Check 4 (D-09): every CATALOG value uses U+00A0 (not a plain space) before ':'/';'/'?'/'!' | pending | |
| 23 | D-08 Check 5: every literal title=/alt=/aria-label=/placeholder= attribute value scanned from the D-05 module set is a companion.i18n_fr.CATALOG key (ast-based, source-only scan; a dynamically-filled attribute is proven by Check 1's own i18n.t() call-argument tracing instead) | pending | |
| 24 | D-08 Check 6: every genuine English fallback literal scanned from companion/static/*.js (var ALL_CAPS = "..."; ... \|\| "...") is a companion.i18n_fr.CATALOG key (regex-based, boundary stated in this file's own header comment and above _scan_all_js_files_for_fallback_literals()) | pending | |

