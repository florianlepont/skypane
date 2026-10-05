---
quick_id: 261006-alr
status: complete
---

# 261006-alr summary

- The Airlines page is one list of fixed-height rows (76px at every width, one column, two from
  960px): small picture, name (at most two lines, full name in `title`), every aircraft type as one
  uppercase line (all of them up to three, else the first two and `+N`), chevron. The whole row
  opens the sheet. Status chips ("Illustration remplacée", "Nom intégré utilisé…", "Renommée",
  "Résolue à la main", "Pas encore d'illustration") are gone from rows; a missing picture shows as a
  dashed frame. The state stays reachable in the sheet only where the owner can act on it: the
  reset for a renamed airline, one sentence plus the delete form for a hand-typed name the built-in
  list overrides, the add-artwork step for an airline without a picture.
- Aircraft labels: `illustrations.PRIMARY_AIRCRAFT_LABELS` / `VARIANT_AIRCRAFT_LABELS` /
  `aircraft_label()`, transcribed from `VENDOR.md`. Primary labels: Air France A320, Iberia A320,
  TAP A321, Air Algerie B737, Air Corsica A320 (+ ATR72), Vueling A320, Transavia France B737 (+ A320),
  easyJet A320, Wizz Air A321, Volotea A320, ITA A321, Air Europa B737, Royal Air Maroc B737 (+ E190),
  LOT E195, Air Caraïbes A350-900 (+ A330, A350-1000, ATR72), French Bee A350-900, ASL B737, Tunisair A320,
  Pegasus A321, Chalair ATR72, Twin Jet B1900D, Corsair A330, KM Malta A320, TUIfly Belgium B737,
  Amelia A320 (+ E145), Air France Hop E190 (+ ATR72), KlasJet B737, La Compagnie A321, Qatar Amiri
  Flight A320, South Korea Government B747, Royal Jordanian B787, French Air Force A330, Saudi Royal
  Aviation B777, Saudia B777, Gendarmerie Nationale EC145, Iraqi Government B737. An owner-named
  airline (one picture, used for every aircraft) reads "Tous types" / "All types".
- Dead A350-1000 slide: fixed, not dropped. `select_illustration()` tried only
  `air-caraibes-a350`, which does not exist, because A35K and A359 both bucket to `a350`. A small
  designator-to-variant table (`_TYPE_VARIANT_SLUGS`, A35K -> `a350-1000`) is tried before the
  shape bucket, so an A350-1000 flight now gets `air-caraibes-a350-1000.png`; an A359 keeps the
  primary and an airline without a sub-type file keeps its primary. Air Caraïbes' primary is labelled
  A350-900 so it differs from the A350-1000 tab.
- Transavia "A320 twice": not reproducible from the repo (distinct files). The row and the sheet tab
  now say B737 for the primary and A320 for the second picture, so an owner upload over the primary
  (or two look-alike pictures) becomes visible. A unit test pins that no airline's primary label
  repeats a secondary's.
- Sheet: one title (the airline name) with the prefixes as quiet chips beside it, no "Modifier" line,
  no caption repeating the name; the picture; a type switcher (one 44px tab per type, a plain label
  for one type; real `?sheet=<type>` links without script); the replace zone (per selected type,
  the previously chosen file is cleared on a switch); the name field with "Enregistrer le nom"
  (rename, refusals and no-autofocus unchanged); the reset only for a renamed airline; Close. The
  "Affiché sur tous les vols…" sentence and the separate prefixes block are removed; no replacement
  explanation is kept (an owner-named airline has no name form to explain, and its delete form
  already states its outcome). The no-script in-page sheet has the same head and picture, with the
  name form before the upload zone so the jump to it keeps Save in view.
- Shared machinery: the dialog, `data-view-panel-*` vocabulary (a sixth sheet attribute carries the
  row's types, with the shown one marked) and the Health resolve dialog keep working; Health's
  baseline entries changed only through the shared dialog markup and that new empty attribute on its
  triggers. `airline-types.js` is no longer wired to any markup; it is left loaded (removing it
  touches every page's script list and the whole baseline).
- Verification: `./scripts/run-all-tests.sh` 4105 passed, 8 skipped (root/openssl skips); ruff,
  mypy, function-size and comment-history clean. Browser tests: 76px equal rows at 360/390/700/1024/1280
  (two-line names measured), no overflow, 44px targets, search by name/type/prefix, FR/EN, both themes,
  scripts blocked. Screenshots (FR) in the session scratchpad `shots-airlines-list/`.
