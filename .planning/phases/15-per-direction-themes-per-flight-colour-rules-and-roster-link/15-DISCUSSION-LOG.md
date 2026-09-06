# Phase 15: Per-direction themes, per-flight colour rules and roster-linked highlighting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 15-per-direction-themes-per-flight-colour-rules-and-roster-link
**Areas discussed:** Découpage de la phase, Thème par direction, Règles par vol, Volet roster K Stewart
**Participants:** developer + Claude (Fable 5.1); questions and options were presented in French, the developer's working language, and selected all four proposed areas.

---

## Pre-discussion findings

Carried in from the promotion entry (`.planning/ROADMAP.md` §Phase 15), established by reading the code before the discussion and presented as "not re-asked":

1. Every one of the 18 registered themes already has `departing_index == arriving_index` (Phase 8 D-02 plus the retirement of "Sky" in 08-06), so the seed's "reconcile the existing pair mechanism" question has no object — sub-idea 1 reduces to a second theme selection.
2. A rule that resolves to a theme id reuses every on-glass-verified pairing; a rule carrying a raw colour would not.
3. The displayed flight carries the ICAO24 `hex` but not the registration.

---

## Découpage de la phase

| Option | Description | Selected |
|--------|-------------|----------|
| Socle + volets 1 et 2, roster différé (Recommended) | Phase 15 delivers the seam, per-direction themes and per-flight rules; the roster half stays in SEED-003 until export format and consent are known; a roster match will write into the same rule store | ✓ |
| Une seule phase, les trois volets | Planned in waves; the roster half cannot be planned until K Stewart answers, so the phase risks not closing | |
| Trois phases, une par volet | Cleanest bookkeeping, but sub-ideas 1 and 2 share the seam and Settings work too closely | |

**User's choice:** Socle + volets 1 et 2, roster différé.

| Option | Description | Selected |
|--------|-------------|----------|
| Rien d'anticipé (Recommended) | Rules purely manual; the record's shape documented as extensible, no reserved field | ✓ |
| Réserver un champ « origine » | Every rule carries an origin ("manual") now so "roster" can be added without a file migration | |
| Vous décidez | Claude's discretion at plan time | |

**User's choice:** Rien d'anticipé.

| Option | Description | Selected |
|--------|-------------|----------|
| Capturer l'intention maintenant (Recommended) | A few questions on the roster half, recorded as notes for the future phase, not as Phase 15 decisions | ✓ |
| Ne pas en parler aujourd'hui | Area dropped; the seed keeps its open questions as they are | |

**User's choice:** Capturer l'intention maintenant.
**Notes:** "Zone suivante" chosen at the area check — no further questions on the split (the fate of the SEED-003 file and the phase's closing gate were offered and left to Claude).

---

## Thème par direction

| Option | Description | Selected |
|--------|-------------|----------|
| Un thème + surcharge arrivées (Recommended) | `theme` stays the frame's theme; an optional arrivals theme, unset = same; existing `device_config.json` stays valid | ✓ |
| Deux champs pleins départs / arrivées | `theme_departing` + `theme_arriving`, both mandatory; key migration; decide which dresses the empty state and previews | |
| Vous décidez | Claude's discretion | |

**User's choice:** Un thème + surcharge arrivées.

| Option | Description | Selected |
|--------|-------------|----------|
| Case à cocher qui révèle une 2e grille (Recommended) | Theme group unchanged; a checkbox below it reveals an identical second chip grid; unchecked = override cleared; grid always in the HTML (no-JS) | ✓ |
| Deux grilles toujours visibles | Departures / Arrivals grids, the second with a "Same as departures" chip; 36 preview chips | |
| Sélecteur de direction au-dessus d'une grille | Segmented Departures / Arrivals control switching what one grid edits | |
| Vous décidez | Claude's discretion with sketch-findings-skypane as density reference | |

**User's choice:** Case à cocher qui révèle une 2e grille.
**Notes:** "Zone suivante" at the area check (what Health/History show when the override is active, and per-direction chip previews, were offered and left to Claude).

---

## Règles par vol

| Option | Description | Selected |
|--------|-------------|----------|
| Un thème du registre (Recommended) | The rule names one of the 18 themes; reuses every on-glass pairing; no new render code; existing previews reusable | ✓ |
| Une couleur brute du panneau | A palette index per rule; untested background/ink combinations; on-glass verification per rule | |
| Vous décidez | Claude's discretion | |

**User's choice:** Un thème du registre.

| Option (multi-select) | Description | Selected |
|--------|-------------|----------|
| Callsign exact | Normalised ADS-B callsign via `enrich.normalise_callsign()` | ✓ |
| Hex ICAO24 | The airframe's ICAO24 address, already carried by the detection — the seed's "tail number" in its available form | ✓ |
| Préfixe de callsign | The 3-letter ICAO carrier prefix | ✓ |
| Immatriculation (F-HBNA) | The aggregators' `r` field, absent from the selection dict today | |

**User's choice:** Callsign exact + Hex ICAO24 + Préfixe de callsign.

| Option | Description | Selected |
|--------|-------------|----------|
| Settings, sous le groupe Thème (Recommended) | Beside what rules override; add form + list with delete on the Phase 13 model; immediate actions outside the main form and its dirty bar | ✓ |
| Airlines, à côté des résolutions manuelles | One page for runtime lists, far from the theme a rule names | |
| Une nouvelle page « Rules » | A fifth tab; reopens the four-tab navigation | |
| Vous décidez | Claude's discretion | |

**User's choice:** Settings, sous le groupe Thème.

| Option | Description | Selected |
|--------|-------------|----------|
| La plus spécifique : callsign > hex > préfixe (Recommended) | Fixed order by key kind, narrow to broad; one rule per key, adding an existing key replaces it | ✓ |
| L'appareil d'abord : hex > callsign > préfixe | The airframe beats the flight number | |
| L'ordre de la liste | First matching rule in the list wins; needs a reorder control with no precedent | |
| Vous décidez | Claude's discretion | |

**User's choice:** La plus spécifique : callsign > hex > préfixe.

| Option | Description | Selected |
|--------|-------------|----------|
| Liste déroulante native (Recommended) | A `<select>` of the 18 labels; swatch + label in each rules-list row | ✓ |
| Une troisième grille de puces avec aperçu | Same control as the main theme, on a very long page | |
| Vous décidez | Claude's discretion | |

**User's choice:** Liste déroulante native.
**Notes:** "Zone suivante" at the area check (a rules cap, a History trace when a rule fired, and the previous-flight card's behaviour were offered and left to Claude / not requested).

---

## Volet roster K Stewart (intent for the deferred phase — not Phase 15 decisions)

| Option | Description | Selected |
|--------|-------------|----------|
| URL iCal d'abonnement au roster (Recommended) | The crew app's subscription URL, re-read periodically; depends on the real event format | ✓ |
| Saisie manuelle des vols de la semaine | No secret, no parser, no fetch — but a weekly chore and no longer automatic | |
| Import d'un fichier exporté | An `.ics` uploaded from Settings per roster publication, via the Phase 13 upload path | |
| À voir avec K Stewart | No preference today | |

**User's choice:** URL iCal d'abonnement au roster.

| Option | Description | Selected |
|--------|-------------|----------|
| Un thème dédié seulement (Recommended) | The match behaves as an automatic rule imposing a chosen theme; nothing new on the glass | ✓ |
| Thème + un marqueur nommé | A small mention on the panel; new render element to verify on glass; a first name on a wall | |
| Vous décidez | Decide in the future phase | |

**User's choice:** Un thème dédié seulement.

| Option | Description | Selected |
|--------|-------------|----------|
| Numéro de vol + jour (Recommended) | `callsign_iata` (after enrichment) equals a roster duty's number dated the same day | ✓ |
| Numéro de vol seul | Any detection of that number, any day | |
| Vous décidez | Decide in the future phase | |

**User's choice:** Numéro de vol + jour.

| Option | Description | Selected |
|--------|-------------|----------|
| Variable d'environnement, comme le mot de passe (Recommended) | In `skypane.env`, entered once over SSH, never in `state_dir` or the UI; Settings shows configured / not configured | ✓ |
| Champ dans Settings, stocké à part | Pasteable from the web into a dedicated file — the project's first runtime-written secret | |
| Vous décidez | Decide in the future phase | |

**User's choice:** Variable d'environnement, comme le mot de passe.

---

## Closing check

"Prêt pour le CONTEXT" chosen over "Plus de questions sur le roster" and "Explorer d'autres zones grises" (offered: Health/History showing when a rule or the override played, the rules cap, hold-screen behaviour).

## Claude's Discretion

- Field/file names, the rules cap, hex normalisation details, the resolver's module placement.
- All copy (checkbox, rules form, empty state, flash messages).
- Whether the log line / `run_once()` result report the effective theme; whether History/Health surface a fired rule (no requirement).
- Reusing the per-theme preview cache for the second grid.
- Test strategy.
- Bookkeeping: SEED-003's file gets a dated "partially promoted" addendum (the `260902-ipj` convention for a seed whose halves diverge) rather than a status change.

## Deferred Ideas

- The roster half of SEED-003 (source, rendering, match key, secret, prerequisites) — see CONTEXT.md `<deferred>`.
- Registration (tail number) as a rule key.
- A visible trace on History/Health that a rule or the arrivals override fired.
