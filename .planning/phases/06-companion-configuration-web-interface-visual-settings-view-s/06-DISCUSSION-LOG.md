# Phase 6: Companion Configuration Web Interface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-27
**Phase:** 06-companion-configuration-web-interface-visual-settings-view-s
**Areas discussed:** Authentification / accès, Architecture serveur / hébergement, Délai d'application des réglages, CFG-02 sans deuxième vue, Périmètre exact de CFG-01, Contenu de CFG-03 (statut santé), Contenu de CFG-04 (monitoring compagnies), Ton visuel de la page, Scope widening (autres fonctionnalités), CFG-12 (sélection de piste, raised mid-discussion)

---

## Authentification / accès

| Option | Description | Selected |
|--------|-------------|----------|
| Mot de passe partagé | Secret unique, cookie de session, stocké comme le bearer token device | ✓ |
| Restriction par IP (réseau maison) | Plus sûr mais bloque l'accès hors domicile | (initially chosen, then reconsidered) |
| Rien (URL obscure uniquement) | Simple mais risqué | |

**User's choice:** Mot de passe partagé — first picked IP restriction, then explicitly changed their mind ("je change d'avis, je préfère gérer la connexion autrement") after considering dynamic home-IP practicality.

**Follow-up:** Password protects the entire site uniformly (not just write actions) — user chose simplicity over splitting read/write access.

**Notes:** Session mechanism (cookie duration, rate limiting) left to Claude's Discretion.

---

## Architecture serveur / hébergement

| Option | Description | Selected |
|--------|-------------|----------|
| Nouveau service séparé | Own port/systemd unit, never modifies vendored byos_server.py | ✓ |
| Intégré à poll_loop.py | Mixes ADS-B detection and web serving in one process | |

**User's choice:** Nouveau service séparé. User asked "c'est quoi le moins cher" — clarified both options cost the same (already-paid OVH VPS with spare capacity, ~4.35€/mo). User also corrected the record: hosting is OVH, not Hetzner as the stack doc recommends.

**Follow-up — Caddy routing:**

| Option | Description | Selected |
|--------|-------------|----------|
| Chemin sur le même nom d'hôte | e.g. `/config/*` on the existing hostname | |
| Sous-domaine séparé | e.g. `config-<ip>.nip.io` | ✓ |

**Notes:** User asked "c'est quoi nip.io" and "niveau prix c'est quoi le mieux" — both free regardless of choice; explained nip.io's mechanism before the user picked subdomain. This question also needed 3 retries due to the AskUserQuestion widget being dismissed twice — resolved once the user clarified they actually wanted the *earlier* hosting question ("Comment l'interface web doit-elle être hébergée") re-asked, not this one.

---

## Délai d'application des réglages

| Option | Description | Selected |
|--------|-------------|----------|
| Au prochain poll planifié | Preserves poll-only, no-inbound-push security model (MSG-01) | ✓ |
| Réveil anticipé possible | Would require a new wake mechanism, not budgeted | |

**User's choice:** Au prochain poll planifié.

**Follow-up:** Yes, an explicit confirmation message should tell the user the change applies on the frame's next wake.

---

## CFG-02 sans deuxième vue

| Option | Description | Selected |
|--------|-------------|----------|
| Retirer CFG-02 de cette phase | No control to build for switching to nothing | ✓ |
| Contrôle à option unique dès maintenant | Build a disabled single-option selector now | |

**User's choice:** Retirer CFG-02 — moved back to v2 Requirements' "View Switching" section.

---

## Périmètre exact de CFG-01

**Notes:** First question wrongly assumed the panel design was "already precisely calibrated on real glass." User corrected this ("Tu te trompes? Le réglage n'a pas encore été calibré") — Phase 7 (on-glass verification) hasn't run yet; `03-CONTEXT.md`'s D-21 colors were only confirmed via screen preview.

| Option | Description | Selected |
|--------|-------------|----------|
| CFG-01 sans les couleurs pour l'instant | Ship config UI without color setting now | |
| Profiter de Phase 7 pour tester plusieurs teintes | Validate 2-3 hue variants during the real on-glass session, CFG-01 offers a real choice | ✓ |

**Follow-up — which colors:**

| Option | Description | Selected |
|--------|-------------|----------|
| Les couleurs de fond DEPARTING/ARRIVING | Reopens D-21's locked Blue/Green | ✓ |
| Autre chose | User-specified alternative | |

**Notes:** This reopens Phase 7's D-21 and widens that phase's success criterion 7 — applied live to ROADMAP.md's Phase 7 section during this session.

---

## Contenu de CFG-03 (statut santé)

| Option | Description | Selected |
|--------|-------------|----------|
| État actuel simple | Just current snapshot | |
| Historique/tendance | Trend over time, useful for spotting battery decline | ✓ |

**Follow-up — retention:** User's first answer ("m") was unclear and clarified as a typo/incomplete input. User then asked "tu crois que ça peut devenir lourd?" — clarified the storage cost is negligible (~1-2MB/year worst case). User then chose to keep everything indefinitely, showing recent weeks by default.

**Follow-up — anomaly highlighting:** Yes, visual emphasis on stale polls / abnormal battery drops (recommended option chosen).

**Follow-up — ADS-B corroboration status:** Yes, include the existing `corroborated` signal from the runway3-false-positive fix (recommended option chosen, zero new computation).

---

## Contenu de CFG-04 (monitoring compagnies)

| Option | Description | Selected |
|--------|-------------|----------|
| Affichage lecture seule | Just display the existing unresolved_prefixes registry | ✓ |
| Actions intégrées | Mark-resolved etc. | |

**User's choice:** Affichage lecture seule.

---

## Ton visuel de la page

| Option | Description | Selected |
|--------|-------------|----------|
| Outil utilitaire simple | Functional, no elaborate design investment | ✓ |
| Même soin visuel que le cadre | Match the frame's carefully-tuned aesthetic | |

**Follow-ups:** Mobile-responsive (basic) — yes. UI language — English (consistent with codebase, despite this discussion being in French). Page identity — simple "SkyPane" title, no logo.

**Notes:** One AskUserQuestion in this area was dismissed once; the user asked to continue rather than move on, and further questions were asked normally afterward.

---

## Scope widening — "autres fonctionnalités à imaginer"

User explicitly asked to brainstorm beyond the fixed CFG-01..05 scope, twice. First round of suggestions (flight history log, manual poll trigger, resolution stats, dark/light theme) were all selected by the user for inclusion — added as CFG-06 through CFG-09. A second round (render preview, simulate-a-flight, render gallery) saw two of three selected (render preview, render gallery — CFG-10/CFG-11); "simulate a flight/state" was not selected and stays deferred.

**Follow-up (CFG-07 cooldown):** Yes, short cooldown after use, to avoid hammering the free ADS-B APIs (recommended option chosen).

**Follow-up (navigation):** Given the resulting breadth, the interface is multiple pages/tabs, not one long page (recommended option chosen).

---

## CFG-12 — runway selection (raised mid-conversation, after the rest of this document was already drafted)

User: "Peut-être qu'on pourrait aussi laisser la possibilité de changer de piste ?" — sent mid-turn while CONTEXT.md was already being written.

| Option | Description | Selected |
|--------|-------------|----------|
| Idée différée | Capture as a seed for a future dedicated phase — this touches detection logic, not just display | |
| L'ajouter à cette phase quand même | Include now as CFG-12, knowing it touches `server/plane/detect.py` too | ✓ |

**Follow-up — which runways:**

| Option | Description | Selected |
|--------|-------------|----------|
| Les 3 pistes d'Orly | Runway 3 + 06/24 + 02/20, geometry for the latter two already exists (exclusion-only) | ✓ |
| Seulement la piste 3 pour l'instant | Mechanism ready, other runways' geometry not yet wired for tracking | |

**Follow-up — timing/exclusivity:** Confirmed both — applies on next scheduled poll (same as other settings), and one runway tracked at a time (recommended option chosen).

---

## Claude's Discretion

- Web framework choice (stdlib vs. Flask/FastAPI) for the new service
- Session/cookie mechanism for the password gate
- New persistence format for poll/battery history and flight log (file-based vs. other)
- Exact page/tab grouping and per-page layout
- Exact metrics/visualization for CFG-08's resolution statistics
- Whether CFG-01's theme picker ships now against a placeholder or waits for Phase 7

## Deferred Ideas

- Simulate a flight/state for preview (callsign/state override) — proposed alongside CFG-10/CFG-11, not selected
- Webhook/notification integration — not proposed to the user, would contradict CFG-03's established "no phone dependency" rationale
