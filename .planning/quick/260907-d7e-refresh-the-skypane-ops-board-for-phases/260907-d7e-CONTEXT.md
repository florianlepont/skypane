# Quick Task 260907-d7e: Refresh the SkyPane ops board for Phases 14 and 15 - Context

**Gathered:** 2026-09-07
**Status:** Ready for planning

<domain>
## Task Boundary

Bring `.planning/notes/skypane-ops-board.html` (a single self-contained HTML page in French,
published as a Claude artifact) up to date with `origin/main` @ `d46e22a` (2026-09-06/07). Two
phases merged since the board's last refresh (`e63fff7`): **Phase 14** (gallery lightbox resolve,
PR #55) and **Phase 15** (per-direction themes / colour rules, PR #54, promoted from SEED-003).

The board's current base state already carries ONE small, buggy patch from Phase 15's own commit
(`d46e22a`) that added a Roadmap row **tagged `P14` but containing Phase 15's content** — there is
no row for the real Phase 14 at all. This must be fixed, not layered on top of.

The "Avertissements de revue" section does **not** exist on this base (a prior local build of it
was never pushed and was discarded when this branch was reset to `origin/main`). Build it fresh,
covering Phases 3 through 15 in one pass — do not assume any prior partial version exists in the
file.

All facts below were verified by the orchestrator directly against the code on `origin/main` @
`d46e22a` on 2026-09-07 — reading each REVIEW.md/SECURITY.md finding and grepping/reading the
current source to confirm it. Do NOT re-verify, do NOT re-derive, do NOT second-guess a status.
Transcribe.

</domain>

<decisions>
## Implementation Decisions

### Ground-truth counts (recompute nothing — these are final)
- **28 phase directories** exist under `.planning/phases/` (`git ls-tree --name-only` confirms):
  15 integer-numbered main phases (1–15) + 13 decimal-numbered inserted phases (3.1, 6.1, 6.2, 6.3,
  6.4, 6.5, 6.6, 6.6.1, 6.6.2, 6.6.3, 6.6.4, 6.6.4.1, 6.6.4.1.1).
- **27 of 28 complete.** Only Phase 5 (DEVICE-05, the multi-day battery discharge run) is open.
  Phases 14 and 15 are BOTH fully complete and verified — Phase 14: 13/13 must-haves, both
  human-verification items developer-confirmed, zero open gaps (`14-VERIFICATION.md`). Phase 15:
  27/27 must-haves, UAT `status: complete` (`15-UAT.md`), security sign-off 15/15 threats closed
  (`15-SECURITY.md`) — its `15-VERIFICATION.md` frontmatter says `status: passed`; an inner
  paragraph of that same file is a stale leftover claiming `human_needed` from before `15-UAT.md`/
  `15-SECURITY.md` existed — trust the frontmatter and `STATE.md`'s own summary
  ("Phases 14 and 15 both COMPLETE"), not that inner paragraph.
- **ROADMAP.md's own head-list checkbox section is known-incomplete** (only lists phases up to
  6.6.1, skips 6.6.2 through 6.6.4.1.1 entirely) — this is a pre-existing drift, not something to
  fix; the board has always sourced its phase list from `.planning/phases/` directories instead,
  continue that practice.
- **Seeds: 3 pure-dormant, 2 partially-fulfilled, 5 fully realized, out of 10 files.** SEED-003 is
  now the second partial (alongside `on-device-fault-icon.md`) — Phase 15 shipped 2 of its 3
  sub-ideas (per-direction theme, per-flight colour rules); the third (roster-linked highlighting)
  was deliberately deferred and stays recorded in `SEED-003-*.md`, whose own frontmatter still says
  `status: dormant` (not yet updated to `partially-fulfilled` — a real drift, footnote it in the
  seed card's trigger text but do not edit the seed file itself, out of scope). Pure-dormant now:
  presence-adaptive poll cadence, local RTL-SDR backup, AeroDataBox rotating-callsign fallback.
- **Quick tasks: 54** (unchanged — Phases 14/15 were full GSD phases, not quick tasks).
- **Debug: 0 open, 4 resolved** (unchanged).
- **Backlog v2: 9 requirements, unchanged** — REQUIREMENTS.md was not touched by Phases 14/15.

### Review/security warnings: 21 open, 33 verified closed (out of a universe of 56 raw findings)
Breakdown of the 21 open, by group (this is also the board's group structure — six groups, in
this order):
1. **Phase 13 — revue de code (9)** — unchanged from the board's last published version: WR-01,
   03, 05, 07, 08, 09, 10, 12, 13. Re-verified against current code on 2026-09-07, all still stand
   exactly as previously described (Phase 14/15 touched `airlines_page.py`/`app.py` heavily but did
   not fix any of these nine).
2. **Phase 13 — audit sécurité (2)** — UF-01, UF-03 (unchanged). **T-13-18 is REMOVED from this
   group — it is now CLOSED**, not open: Phase 14 deliberately added client-side JavaScript to the
   Airlines page (`panel-lookup.js`, `list-filter.js`) with its own dedicated threat coverage
   (T-14-09 DOM integrity, T-14-20 client-side re-validation), and `companion/test_status_pages.py`
   now contains a real `<script` count assertion (`rendered.count("<script") != 1` at two call
   sites) — the exact regression guard T-13-18 said was missing now exists, just enforcing "one
   script" instead of "zero", because the design legitimately changed. Do not list T-13-18 as open.
3. **Phase 14 — audit sécurité (1)** — new group. One item: `14-SECURITY.md` §4.1 ("WR-02's shipped
   invariant is narrower than the one claimed"). Phase 14's code review itself (5 findings: 1
   critical CR-01 + 4 warnings WR-01..04) is FULLY resolved and independently re-verified in code —
   zero open items from `14-REVIEW.md`. `14-SECURITY.md`'s six numbered sub-findings (§4.1–§4.6)
   are five closed (§4.2–§4.6, each describing a threat class that WAS mitigated) plus this one
   open item.
4. **Phase 15 — revue de code (1)** — new group. `15-REVIEW.md`'s WR-01 (rule-delete race, spurious
   failure message). WR-02 (no write lock on `save_device_config()`) is NOT a separate row here —
   it is the *same defect* as the pre-existing "Revues antérieures" item `6.2 · WR-01`, re-found
   independently by Phase 15's reviewer. Fold it into that older row (update its description only,
   per the exact text below) rather than creating a duplicate.
5. **Phase 15 — audit sécurité (1)** — new group. `15-SECURITY.md`'s Unregistered Flag `UF-15-02`
   (`rule_rows()`/theme-swatch rendering are not self-gating). `UF-15-01` is NOT a separate row —
   it is the same `save_device_config()` lock gap as `6.2 · WR-01`/`15 · WR-02`, already folded into
   that one row; do not triple-count it.
6. **Revues antérieures (7)** — unchanged set of tags (3·WR-01, 3·WR-02, 6.2·WR-01, 6.2·WR-02,
   10·WR-02, 11·WR-01, 11·WR-02), all re-verified still open on 2026-09-07. Only `6.2 · WR-01`'s
   **description** changes (to note the Phase 15 rediscovery) — its tag, pill and title stay as
   they were.

Total row count on the page: 9 + 2 + 1 + 1 + 1 + 7 = **21**.
Pill-class split within the 21: 5 `warn`, 12 `neutral`, 4 `accent` (verify by counting the table
below — do not recompute independently).

Closed-count accounting for the note-box (state as ranges, not a list — matches the board's
standing rule of never enumerating fixed items):
- Ten older reviews (Phases 3, 6.2, 6.3, 6.4, 6.6, 6.6.2, 6.6.4, 8, 10, 11): 25 total, 18 closed.
- Phase 13 review: 13 total, 4 closed (WR-02, 04, 06, 11 — unchanged from last publish).
- Phase 13 security: 3 total, now **1** closed (T-13-18, newly closed as above), 2 open.
- Phase 14 review: 5 total, **5** closed (all of them — CR-01, WR-01..04).
- Phase 14 security: 6 sub-findings, **5** closed (§4.2–§4.6), 1 open (§4.1).
- Phase 15 review: 2 total, both open (WR-01 shown standalone; WR-02 folded into `6.2·WR-01`).
- Phase 15 security: 2 unregistered flags, 1 folded (`UF-15-01` into `6.2·WR-01`), 1 open
  (`UF-15-02`).
Sum of closed: 18+4+1+5+5 = **33**. Sum of open (distinct rows): 9+2+1+1+1+7 = **21**.

### Stat strip (5 tiles, unchanged column count from the board's last publish)
1. `27/28` · **Phases terminées** · `15 principales + 13 insérées · toutes sur main`
2. `1` · **Chantier ouvert** · `DEVICE-05 — run batterie multi-jours, parqué volontairement`
   (unchanged)
3. `0` · **Bugs ouverts** · `4 sessions debug résolues et archivées` (unchanged)
4. `3` · **Seeds dormantes** · `sur 10 · 5 réalisées, 2 partielles · + 9 items backlog v2`
   (was 4/5 réalisées/1 partielle — now 3 pure-dormant + SEED-003 joins the partial bucket)
5. `21` · **Avertissements ouverts** · `17 de revue de code, 4 d'audit sécurité · 33 autres vérifiés
   clos`

### Roadmap section — exact replacement text

**Section head:** `<span class="count">26 phases · 2026-08-26 → 2026-09-06</span>` →
`<span class="count">28 phases · 2026-08-26 → 2026-09-06</span>`

**board-intro:** `Treize phases principales, treize insérées en cours de route. Tout est terminé et
sur <code>main</code>, sauf un point volontairement gardé pour la fin.` → `Quinze phases
principales, treize insérées en cours de route. Tout est terminé et sur <code>main</code>, sauf un
point volontairement gardé pour la fin.`

**Replace the entire existing `P14` row** (the one titled "Thèmes par direction, règles par vol,
vols de K Stewart", currently tagged `P14` with pill `accent`/"Cadrée") **with these two rows, in
this order** — a corrected `P14` row for the real Phase 14, then a `P15` row carrying (and
updating) that same content to reflect it now being fully shipped:

Row 1 (new, real Phase 14):
- tag: `P14`
- title: `Résoudre un vol non identifié depuis la lightbox de la galerie`
- row-desc: `Le flux de résolution de la Phase 13 replié dans le motif d'interaction que la galerie
  Airlines utilise déjà : un vol non couvert devient une carte vide dans la grille, cliquer dessus
  ouvre le même <code>&lt;dialog&gt;</code> que toute autre carte, et le tableau de gestion autonome
  est absorbé dans les cartes plutôt que supprimé. Remontée par le développeur en voyant la vraie
  page de la Phase 13 (la section ne s'intégrait pas à son propre entourage) — aucun changement
  côté serveur.`
- row-note: `Revue de code : 5 constats (1 bloquant, 4 avertissements), tous corrigés avant merge —
  0 restant. Un signalement de l'audit sécurité reste ouvert (voir « Avertissements de revue »).`
- accent row-desc: `Non issue d'une seed — remontée directement par le développeur · PR #55, 8/8
  plans, 13/13 preuves vérifiées.`
- pill: `good` / `Terminé`
- date: `6 sept.`

Row 2 (replaces the old mislabeled row, now correctly tagged P15 and updated to "shipped"):
- tag: `P15`
- title: `Thèmes par direction, règles par vol, vols de K Stewart` (unchanged)
- row-desc: `Un thème dédié aux arrivées, activable/désactivable ; une règle par vol (callsign, hex
  ICAO24 ou préfixe compagnie) qui impose un thème du registre ; un point de résolution unique en
  amont du choix de thème dans <code>run_once()</code>. Le volet surlignage automatique des vols de
  K Stewart (lu depuis son roster) a été différé — deux inconnues externes (format d'export,
  consentement) que seul le développeur peut lever.`
- row-note: `5/5 plans, 27/27 preuves vérifiées, UAT complet, audit sécurité 15/15 menaces closes.`
- accent row-desc: `Promue depuis SEED-003 (partiellement — le volet roster reste dans la seed) ·
  cadrée et livrée le 6 sept.`
- pill: `good` / `Terminé`
- date: `6 sept.`

**SEUL POINT OUVERT callout** — replace the sentence about Phase 15 being "en cadrage":
old: `La Phase 15 (promue depuis SEED-003 le 6 sept., en cadrage) est ouverte mais indépendante de
lui — elle ne touche ni le firmware ni la batterie.`
new: `Les Phases 14 et 15, ajoutées après le dernier calage de ce tableau, sont désormais toutes
deux terminées et indépendantes de lui — ni l'une ni l'autre ne touche le firmware ou la batterie.`
(Keep the rest of the callout's sentences before and after this one exactly as they are.)

### Seeds section — exact replacement text

**board-intro:** `Idées mises de côté avec une condition de réveil explicite. Cinq ont été promues
en phases en six jours (10, 11, 12, 13, 14) — les quatre premières livrées, la 14 en cadrage — c'est
le mécanisme qui fonctionne.` → `Idées mises de côté avec une condition de réveil explicite. Cinq
ont été promues en phases en six jours (10, 11, 12, 13, 15), toutes livrées — c'est le mécanisme qui
fonctionne.`
(Note the seed-promotion count references phases 10/11/12/13/15 — NOT 14, since Phase 14 was
developer-raised, not seed-promoted.)

**SEED-003 card** — keep the card's title, pill (`Promue en partie · Phase 15` — already correct)
and body paragraph unchanged. Replace only the `seed-trigger` paragraph:
old: `<p class="seed-trigger"><b>Promue le 6 sept.</b> ; le cadrage a gardé les volets 1 et 2 dans la
Phase 15 et <b>différé le volet roster</b>, qui reste ici avec l'intention du développeur consignée
dans <code>15-CONTEXT.md</code> (URL iCal, thème dédié seulement, numéro de vol + jour, secret en
variable d'environnement). Il reste conditionné au format d'export du roster et au consentement
explicite de K Stewart — deux réponses que seule cette personne peut donner.</p>`
new: `<p class="seed-trigger"><b>Promue et livrée le 6 sept.</b> (Phase 15, 5/5 plans) ; l'exécution
a gardé les volets 1 et 2 et <b>différé le volet roster</b>, qui reste ici avec l'intention du
développeur consignée dans <code>15-CONTEXT.md</code> (URL iCal, thème dédié seulement, numéro de
vol + jour, secret en variable d'environnement). Il reste conditionné au format d'export du roster
et au consentement explicite de K Stewart — deux réponses que seule cette personne peut donner. Le
fichier de la seed lui-même dit encore <code>dormant</code>, pas <code>partially-fulfilled</code> —
décalage documentaire mineur, non corrigé ici.</p>`

No other seed cards change.

### Backlog v2 section
No changes — REQUIREMENTS.md untouched by Phases 14/15.

### Bugs section
No changes.

### Header comment, masthead, footer

**Header comment `Dernière génération` line** — replace:
old: `Dernière génération : 2026-09-06, passe de clôture, main @ f12ab47
  (Phases 12 et 13 mergées : #49/#50 et #51).`
new: `Dernière génération : 2026-09-07, Phases 14 et 15 intégrées, main @ d46e22a
  (Phase 14 : PR #55 ; Phase 15 : PR #54, promue depuis SEED-003).`

**Header comment SOURCES list** — append two entries after the existing `.planning/debug/` entry
(ending `resolved/ serait un bug ouvert`) and before the `⚠ VÉRIFIER` paragraph:
```
    .planning/phases/*/*-REVIEW.md
                                — section "## Warnings" de chaque revue de code ;
                                ⚠ jamais mise à jour après correction : vérifier
                                chaque WR-xx contre le code (les fix commits sont
                                sur la branche de phase, "fix(NN): WR-xx …")
    .planning/phases/*/*-SECURITY.md
                                — sections "Open Warnings"/"Unregistered Flags"
                                (Phases 13, 14, 15 en ont ; les autres phases
                                antérieures à l'intégration de /gsd-secure-phase
                                n'en ont pas)
```

**masthead-sub** — replace:
old: `Roadmap, backlog v2, seeds et bugs — consolidé depuis <code>.planning/</code> sur
<code>main</code> — passe de clôture du 6 septembre.`
new: `Roadmap, backlog v2, seeds, bugs et avertissements de revue — consolidé depuis
<code>.planning/</code> sur <code>main</code> @ <code>d46e22a</code>, 7 septembre.`

**footer first span** — append ` · <code>phases/*-REVIEW.md</code> · <code>phases/*-SECURITY.md</code>`
right after `54 quick tasks` and before the closing `</span>` (generalize the previous single-phase
`13-SECURITY.md` reference to the wildcard form, since three phases now carry a SECURITY.md).

### CSS and new-section structure (place the section between Bugs and `<footer>`)
Same conventions established for this board's row/pill/group markup:
- `.warn-row{ display:grid; grid-template-columns:96px 1fr auto; gap:12px; align-items:baseline;
  padding:9px 4px; border-bottom:1px solid var(--line-soft); font-size:0.85rem; }` +
  `.warn-row:last-child{ border-bottom:none; }`
- `.warn-tag{ font-family:'IBM Plex Mono', ui-monospace, monospace; font-size:0.75rem;
  font-weight:600; color:var(--ink-faint); white-space:nowrap; }`
- `.warn-name{ font-weight:600; }` — the row description reuses the existing `.bug-desc` class,
  nested inside `.warn-name` (same nesting the Bugs section already uses for `.bug-name`/`.bug-desc`).
- 680px media query: add `.stat:last-child{ grid-column:span 2; }` and
  `.warn-row{ grid-template-columns:1fr; }` alongside the existing responsive rules.
- `.stats` grid-template-columns → `repeat(5,1fr)`.
- Section skeleton: `<section class="board">` with `board-head` (`<h2>Avertissements de revue</h2>`
  + count span `.planning/phases/*/*-REVIEW.md · *-SECURITY.md · 21 ouverts`), a `board-intro`
  paragraph, six `<p class="backlog-group-name">` group headers each followed by its `.warn-row`
  entries, then a closing `<p class="note-box">`.

**board-intro for the new section:** `Points laissés ouverts par les revues de code de phase et par
les audits sécurité des Phases 13, 14 et 15, vérifiés un par un contre le code de <code>main</code>
le 7 septembre. Rien ici ne bloque la roadmap : ce sont des candidats de durcissement, gardés
visibles pour ne pas se perdre.`

**Closing note-box** (counts only, per the board's standing rule of never listing fixed items):
`<strong>Clos, vérifié dans le code :</strong> 18 des 25 avertissements des dix revues antérieures à
la Phase 13, et 4 des 13 de la Phase 13 elle-même (WR-02, 04, 06, 11, corrigés sur la branche de
phase avant merge). Les Phases 14 et 15 ont ajouté deux nouveaux audits sécurité, chacun trouvant et
refermant ses propres constats en cours de route : la revue de code de la Phase 14 est intégralement
close (5/5, dont le bloquant CR-01), et 5 des 6 signalements de son audit sécurité aussi — seul le
14&nbsp;·&nbsp;SEC-4.1 reste ouvert. Le 13&nbsp;·&nbsp;T-13-18 (absence d'un test « zéro script ») est
également clos : la Phase 14 a ajouté du JavaScript à la page Airlines avec sa propre modélisation de
menaces, et un test compte désormais les balises <code>&lt;script&gt;</code>. Le 10&nbsp;·&nbsp;WR-01
(icône batterie figée pendant les heures calmes) n'est toujours pas compté ouvert : la Phase 12
(D-07) a tranché que rien ne se repeint pendant un état de maintien, batterie comprise. Les fichiers
<code>REVIEW.md</code>/<code>SECURITY.md</code> ne sont jamais mis à jour après correction — c'est le
code qui fait foi, et il faut le relire à chaque rafraîchissement.`

### The 21 rows — exact French copy, in group order

**Group 1 — `<p class="backlog-group-name">Phase 13 — revue de code (9)</p>`**
(These 9 rows are UNCHANGED verbatim from the board's last published build. Recreate them exactly:)

1. tag `13 · WR-01` · pill `neutral` `Contrat` · title: `<code>manual_resolutions.py</code> — « never
   raises » faux pour <code>state_dir=None</code>` · desc: `Trois fonctions du registre promettent
   de ne jamais lever mais lèvent <code>TypeError</code> pour <code>state_dir=None</code> ; deux
   appelants contournent avec un <code>if state_dir:</code>, trois autres s'y fient sans garde.
   Latent : la prod passe toujours une chaîne.`
2. tag `13 · WR-03` · pill `warn` `Données` · title: `<code>manual_resolutions.py</code> — une
   entrée rejetée est effacée à l'écriture suivante` · desc: `Toute entrée rejetée au chargement, ou
   au-delà du plafond de 200, disparaît définitivement dès que l'opérateur ajoute ou supprime quoi
   que ce soit. Corrigé a minima : la perte est journalisée, pas évitée.`
3. tag `13 · WR-05` · pill `neutral` `Cosmétique` · title: `<code>_PREFIX_RE</code> /
   <code>_SAFE_KEY_RE</code> — <code>$</code> accepte un saut de ligne final` · desc: `Le
   <code>$</code> Python matche aussi avant un <code>\n</code> terminal. Aucun contournement
   possible (strip et normalisation en amont, la regex exposée a été supprimée par le fix WR-04) :
   dérive de contrat seulement, <code>\Z</code> suffirait.`
4. tag `13 · WR-07` · pill `neutral` `Mise en page` · title: `<code>.resolve-upload-zone</code> ne
   reproduit pas le DOM de la lightbox` · desc: `Le commentaire CSS promet le même traitement que
   <code>.lightbox__replace-zone</code>, mais le champ fichier et le bouton sont enfouis dans un
   <code>&lt;form&gt;</code> : ils perdent l'empilement en colonne et l'espacement.`
5. tag `13 · WR-08` · pill `neutral` `Message` · title: `<code>ADD_REJECTED_PREFIX</code> affiche «
   Enter an airline name »` · desc: `Un rejet de forme du préfixe (champ caché, jamais saisi)
   renvoie un message faux et inactionnable. Branche inatteignable aujourd'hui — c'est précisément
   ce qui cache l'erreur si elle le devient.`
6. tag `13 · WR-09` · pill `neutral` `Code mort` · title:
   `<code>_manual_resolution_rows(state_dir, registry)</code> ne lit jamais <code>state_dir</code>` ·
   desc: `Paramètre accepté, transmis, jamais utilisé — sa fonction sœur
   <code>unresolved_row_for_prefix()</code> s'en sert, ce qui invite à croire que celle-ci lit aussi
   l'état.`
7. tag `13 · WR-10` · pill `warn` `Concurrence` · title: `<code>companion/app.py</code> — deux
   uploads simultanés partagent le fichier temporaire` · desc: `Les temporaires sont nommés par clé
   et pid, sans identité de thread : sous <code>ThreadingHTTPServer</code>, deux uploads d'une même
   clé entremêlent leurs octets et l'un des deux échoue à tort. L'audit sécurité (UF-02) y ajoute une
   fenêtre TOCTOU entre validation et décodage. Antérieur (260902-v26), mais D-09 a élargi l'espace
   de clés.`
8. tag `13 · WR-12` · pill `neutral` `Message` · title: `Étape B — « Illustration replaced » pour un
   tout premier upload` · desc: `Le formulaire d'upload de l'étape B réutilise le flash de
   remplacement alors qu'il n'y avait rien à remplacer ; la phase a créé un flash dédié pour l'étape
   A et pas pour celle-ci.`
9. tag `13 · WR-13` · pill `neutral` `Contrat` · title:
   `<code>static_airline_name_for_prefix()</code> — « ASCII » n'est pas ce que le code impose` ·
   desc: `<code>str.isalpha()</code> accepte « ÀÉÎ » ; le lookup échoue donc c'est correct par
   accident, mais cette fonction est l'oracle de supersession de D-06 et son contrat écrit est ce
   que le prochain appelant croira.`

**Group 2 — `<p class="backlog-group-name">Phase 13 — audit sécurité (2)</p>`**

10. tag `13 · UF-01` · pill `accent` `Audit sécu` · title: `<code>illustration_normalize.py</code> —
    cache LRU illimité, clé sur <code>mtime</code>` · desc: `Chaque ré-upload d'une même clé crée
    une entrée permanente dans un serveur qui tourne longtemps ; le commentaire « 43 fichiers
    vendored » est périmé depuis que D-09 a ajouté jusqu'à 200 clés opérateur. Croissance mémoire
    lente, opérateur authentifié seulement.`
11. tag `13 · UF-03` · pill `accent` `Audit sécu` · title: `Une entrée malformée du registre → une
    ligne de log par rendu` · desc: `Le fix WR-03 journalise le nombre d'entrées qui seront perdues,
    mais <code>load_manual_resolutions()</code> tourne désormais deux à trois fois par page
    authentifiée (voir 14 · SEC-4.1 ci-dessous) : la ligne revient d'autant plus souvent au lieu
    d'une fois. Volume de log seulement.`

**Group 3 — `<p class="backlog-group-name">Phase 14 — audit sécurité (1)</p>`**

12. tag `14 · SEC-4.1` · pill `neutral` `Contrat` · title: `Le fix WR-02 lit le registre 2 à 3 fois,
    pas « une seule fois » comme documenté` · desc: `Le docstring du fix, le message du commit et
    <code>14-VERIFICATION.md</code> affirment tous que <code>render()</code> lit
    <code>manual_resolutions.json</code> une seule fois ; en instrumentant le chargeur, une page
    Airlines avec une carte supersédée en fait 2 lectures, et avec <code>?resolve=</code> en fait 3.
    La faille nommée par WR-02 (un préfixe absent des deux ensembles) reste bien close ; c'est
    l'invariant écrit qui est faux.`

**Group 4 — `<p class="backlog-group-name">Phase 15 — revue de code (1)</p>`**

13. tag `15 · WR-01` · pill `neutral` `Message` · title: `Suppression d'une règle — un « échec »
    signalé alors qu'elle a bien disparu` · desc: `<code>_handle_rule_delete()</code> vérifie
    l'existence de la règle hors verrou, puis appelle <code>delete_rule()</code> qui revérifie sous
    verrou : une suppression concurrente entre les deux fait croire à un échec côté opérateur alors
    que la règle est bien partie. La suppression elle-même reste sûre — seul le message ment.`

**Group 5 — `<p class="backlog-group-name">Phase 15 — audit sécurité (1)</p>`**

14. tag `15 · UF-15-02` · pill `neutral` `Dépendance` · title: `<code>rule_rows()</code> et le rendu
    de la pastille de thème ne se protègent pas eux-mêmes` · desc: `Les deux ne sont sûrs aujourd'hui
    que parce que leur unique appelant leur passe déjà un registre filtré par
    <code>load_colour_rules()</code> ; un futur appelant direct casserait cette hypothèse en
    silence.`

**Group 6 — `<p class="backlog-group-name">Revues antérieures (7)</p>`**

15. tag `3 · WR-01` · pill `neutral` `Contrat` · title: `<code>render.py</code> —
    <code>previous_state</code> jamais validé` · desc: `<code>draw_previous_text_block()</code>
    transmet l'état tel quel : toute valeur inconnue rend « from » en silence au lieu d'échouer.
    Seuls des appelants directs peuvent le déclencher.`
16. tag `3 · WR-02` · pill `neutral` `Garde-fou` · title: `<code>_assert_legal_palette()</code> ne
    voit rien au-delà de 256 couleurs` · desc: `<code>Image.getcolors()</code> renvoie
    <code>None</code> passé 256 couleurs, traité comme « zéro couleur » : les deux assertions
    passent à vide dans le cas exact qu'elles doivent attraper.`
17. tag `6.2 · WR-01` · pill `warn` `Concurrence` · title: `<code>save_device_config()</code> —
    lecture-fusion-écriture sans verrou` · desc: `Deux enregistrements rapprochés (Settings et LED,
    ou une double soumission) sous <code>ThreadingHTTPServer</code> peuvent s'écraser : le dernier
    écrit gagne. Re-signalé indépendamment par la revue de la Phase 15 (15 · WR-02, même fichier,
    même défaut) — cette phase a correctement verrouillé son propre registre
    <code>colour_rules.json</code> mais a laissé <code>device_config.json</code> tel quel.`
    **(This description text changes from the last publish — the rest of the row is unchanged.)**
18. tag `6.2 · WR-02` · pill `warn` `Diagnostic` · title: `Poll manuel — l'échec est avalé sans une
    ligne de log` · desc: `Le handler <code>/poll-now</code> attrape <code>Exception</code> et
    redirige, sans rien écrire, alors que le message affiché demande de « check the companion
    service logs ». Il n'y a rien à y lire.`
19. tag `10 · WR-02` · pill `warn` `UX` · title: `Heures calmes — une fenêtre début = fin
    s'enregistre et ne s'active jamais` · desc: `Une largeur nulle est un « jamais actif » voulu
    côté serveur, mais Settings l'enregistre avec le « saved » habituel : case cochée, horaires
    enregistrés, fonction morte, aucun retour.`
20. tag `11 · WR-01` · pill `neutral` `Dérive` · title: `<code>WAKE_INTERVAL_MIN_S</code>/<code>MAX_S</code>
    dupliqués sans garde anti-dérive` · desc: `<code>stub-server/byos_server.py</code> redéfinit les
    bornes (frontière vendor, pas d'import), mais contrairement à
    <code>seconds_until_quiet_hours_end()</code> et <code>_HHMM_RE</code>, rien ne vérifie qu'elles
    restent égales.`
21. tag `11 · WR-02` · pill `neutral` `Contrat` · title: `Intervalle de réveil — seul
    <code>ValueError</code> est attrapé` · desc: `La conversion <code>int()</code> ignore
    <code>TypeError</code>. Inatteignable via HTTP (toujours une chaîne), seulement par des
    appelants directs du handler.`

**Pill totals to cross-check (must match exactly):** walking the 21 numbered rows above and tallying
the pill class stated on each: `neutral` on rows 1, 3, 4, 5, 6, 8, 9, 12, 13, 14, 15, 16, 20, 21
(14 rows); `warn` on rows 2, 7, 17, 18, 19 (5 rows); `accent` on rows 10, 11 (2 rows).
**14 + 5 + 2 = 21.** This is the authoritative split — build the section to match it, and have the
verify step count pills within the new section and assert exactly 14/5/2.

</decisions>

<specifics>
## Verification method (for the record, not to be repeated)

Every item above was checked by the orchestrator directly against files on `origin/main` @
`d46e22a` on 2026-09-07: `grep`/`sed` reads of the current source (`server/plane/manual_resolutions.py`,
`server/plane/render.py`, `server/plane/enrich.py`, `server/device_config.py`, `server/plane/colour_rules.py`,
`companion/app.py`, `companion/pages/airlines_page.py`, `companion/pages/config_page.py`,
`companion/static/style.css`, `stub-server/byos_server.py`, `stub-server/test_poll_cycle.py`,
`companion/test_status_pages.py`) cross-referenced against every phase's `*-REVIEW.md`,
`*-SECURITY.md` and `*-VERIFICATION.md`. Diff-stats between phase boundaries (`f12ab47..5082629` for
Phase 14, `5082629..d46e22a` for Phase 15) confirmed exactly which files each phase touched, which is
how the "still open, unaffected by 14/15" calls for the nine Phase-13 review items and the
older-review items were made.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/notes/skypane-ops-board.html` — the page itself, currently at the `d46e22a` base state
  (no Avertissements section, P14 row mislabeled).
- `.planning/phases/14-resolve-an-unidentified-flight-from-the-gallery-lightbox-wit/` — `14-REVIEW.md`,
  `14-SECURITY.md`, `14-VERIFICATION.md`.
- `.planning/phases/15-per-direction-themes-per-flight-colour-rules-and-roster-link/` — `15-REVIEW.md`,
  `15-SECURITY.md`, `15-VERIFICATION.md`, `15-UAT.md`.
- `.planning/phases/13-add-an-illustration-for-an-unidentified-flight-from-the-comp/13-REVIEW.md`,
  `13-SECURITY.md` — source of the 9+2 Phase-13 rows (re-verified unaffected).
- The seven older reviews (Phases 3, 6.2, 6.3, 6.4, 6.6, 6.6.2, 6.6.4, 8, 10, 11) — source of the
  "Revues antérieures" group (re-verified unaffected, except `6.2·WR-01`'s description text).
- `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/seeds/*.md` — ground truth for phase/seed
  counts.
- Memory rule for this board (user feedback): status dashboards show open backlog only, never a list
  of resolved items — counts of closed items are fine.

</canonical_refs>
