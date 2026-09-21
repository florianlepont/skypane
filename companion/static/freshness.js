/*
 * SkyPane companion service — freshness.js.
 *
 * This is the project's own no-build-step/no-bundler/no-framework/
 * no-dependency JavaScript idiom (nav-dropdown.js, battery-trend.js,
 * list-filter.js before it) — must stay written to an ES5-safe subset
 * (no let/const/arrow functions/template literals/backticks) so no
 * transpiler is ever needed to ship it. It is served by
 * companion/app.py's FRESHNESS_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route.
 *
 * --- 260902-chc: the D-12 reversal -----------------------------------
 *
 * SUPERSEDED — D-12 (06.6.3-CONTEXT.md) gave Health "an explicit
 * Refresh action plus a stale-view warning ... no automatic background
 * polling", reasoning that this "avoids new steady-state request volume
 * and keeps authoritative health severity server-computed only". This
 * file's own prior header went further than D-12 itself, restating the
 * no-polling half as a standing constraint addressed to future editors
 * ("this file must never poll ... at most one deferred setTimeout").
 * Nothing in any harness ever enforced that rule — a source read of
 * companion/test_status_pages.py, test_companion_app.py and
 * test_config_page.py found the sibling ES5/forbidden-sink guards
 * scoped to nav-dropdown.js and panel-lookup.js by name, with this file
 * appearing only as a served static route — so prose was the only
 * enforcement, which is exactly why this reversal has to be legible
 * here, in prose, rather than assumed obvious. After living with the
 * manual-refresh pattern in real use, the developer chose the opposite
 * for Health specifically: accepting the request-volume trade for a
 * genuinely live monitoring page.
 *
 * What was NOT reversed: D-12's severity claim stands, and is
 * strengthened, not weakened. The mechanism below regenerates the whole
 * page server-side on every cycle, so no health verdict is ever
 * recomputed client-side — this file still computes no health state of
 * any kind, exactly as before. The scope stands too: Health alone. The
 * gate that makes that structural, not just a promise, is the pill
 * attribute this file requires before doing anything (see the early
 * return below) — lose the attribute and Health silently stops
 * refreshing; loosen the guard and every page starts.
 *
 * --- SUPERSEDED (19-09-PLAN.md, D-02/A-20): the mechanism decision,
 * --- reversed a second time ------------------------------------------
 *
 * 260902-chc weighed two mechanisms and chose (a) — a
 * Page-Visibility-gated whole-page reload (the window-level navigation
 * method, invoked with no arguments) — over (b), a network-fetch-
 * based soft refresh that patches content in place, for four named
 * reasons. Living with mechanism (a) in real use surfaced its own real
 * cost (A-20): it destroys keyboard focus and silently closes every
 * open disclosure on EVERY cycle, with no opt-out, and the freshness
 * line beside it read "(0s ago)", which was structurally always zero
 * (see companion/pages/health_page.py's own FRESHNESS_PREFIX_TEXT
 * comment). This rewrite reverses that choice — mechanism (b),
 * implemented below — and answers each of the four reasons mechanism
 * (a) was chosen for, in order, rather than pretending they were never
 * real:
 *   1. The nav-dot-outside-render()'s-own-output problem stands, and is
 *      solved directly rather than avoided: the whole nav link
 *      (the anchor whose href is "/health", in BOTH nav renderings) is
 *      one of this file's own SWAP targets, taken verbatim from the fetched
 *      document — never recomputed client-side.
 *      health_page.REFRESH_SWAP_SELECTORS is the single, pinned,
 *      greppable agreement between the two files' target lists (a dot-
 *      only selector would have nothing to replace on the far more
 *      common transition where severity newly clears — see that
 *      tuple's own comment for why the WHOLE link is the target).
 *   2. battery-trend.js's/list-filter.js's own no-re-init-hook contract
 *      also stands, and is accepted as a real constraint rather than
 *      argued away: the sparkline <svg>, every .sparkline-hit, the
 *      registry card and the filter bar are deliberately EXCLUDED from
 *      the swap target list — pinned absent from this file's own
 *      source by name (companion/test_status_pages.py's excluded-
 *      selectors check). The battery readout's two text spans are
 *      updated via textContent on the EXISTING nodes only, and only
 *      when no .sparkline-hit--active point exists, so a hovered
 *      reading is never stomped.
 *   3. The "needs an HTML-writing DOM sink and a network-call sink"
 *      objection is answered by construction, not overridden:
 *      DOMParser.parseFromString() plus document.importNode()/
 *      parentNode.replaceChild() are the load-bearing choice here — none
 *      of them is an HTML-writing DOM sink, so the standing markup-
 *      writing-sink ban (the same one nav-dropdown.js/panel-lookup.js
 *      carry) stays absolute in this file too. companion/
 *      test_companion_app.py's own named guard
 *      for this file states, in its body, that fetch( is a single,
 *      deliberate, reviewed exception to the sibling scripts' ban list
 *      — never a silent exemption, and never a second exception without
 *      a new decision.
 *   4. The line-count objection is accepted outright: this file is
 *      meaningfully larger than the reload-based version it replaces.
 *      That cost was weighed against A-20's real, reported harm, and
 *      lost.
 *
 * The accepted cost this rewrite adds on top of reason 2 above, stated
 * rather than glossed: the sparkline and the registry only ever update
 * on a real navigation — a deliberate trade, not an oversight, and not
 * new (260902-chc's own text already named the identical trade for the
 * mechanism it chose not to build).
 *
 * --- SUPERSEDED (21-02-PLAN.md, D-18): the Pause/Resume control removed --
 *
 * 19-09-PLAN.md added a visible Pause/Resume button and a boolean state
 * flag that independently gated every tick alongside the tab-visibility
 * gate below. D-18 deletes that control outright, with no replacement:
 * the loop below is now unconditional whenever the tab is visible — the
 * ONLY gate left is the pre-existing tab-visibility mechanism
 * (intervalHandle/startLoop()/stopLoop()/the visibilitychange listener),
 * which this plan leaves untouched.
 *
 * --- T13 (22-15-PLAN.md Task 2): three defects, one loop -------------
 *
 * 22-AUDIT.md found three faults in the mechanism above, all read from
 * this file's own source:
 *
 *   1. ANY non-OK response, and any network error, called stopLoop().
 *      The loop then never ran again for the life of the page, and the
 *      only visible sign was a pill that stopped appearing. A page
 *      showing ten-minute-old data looked exactly like a page showing
 *      fresh data. The fix is an exponential retry ladder — the normal
 *      cadence, doubling to a ten-minute ceiling — with a visible,
 *      NEUTRAL badge saying which state the loop is in. Neutral, not a
 *      warning: a browser that lost its connection is not a device
 *      fault (22-UI-SPEC.md §5 contract 9).
 *   2. No in-flight guard. A slow response plus a visibilitychange
 *      catch-up could put two fetches in the air, and the LAST to
 *      resolve won the swap — so a stale response could overwrite a
 *      fresher one.
 *   3. Whole-region swaps. Every cycle destroyed and rebuilt all five
 *      swap targets whether or not their content had changed, taking
 *      any focus inside them with it. Swaps are now targeted: an
 *      unchanged region, and a region containing the focused element,
 *      are both left alone.
 *
 * stopLoop() SURVIVES and is still called twice, and both calls are
 * deliberate teardowns of a background tab — never a failure path. The
 * retry ladder deliberately does NOT stop the interval; it stands the
 * interval's own tick down while a retry is pending instead, so there
 * is no state in which a recovered page is left with no schedule.
 *
 * --- The corrected page list -------------------------------------------
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * [data-loaded-at] element at all — the guard below is load-bearing,
 * not defensive noise, matching the project's established convention.
 * Health is the only page today: Preview was retired in Phase 06.6.4.1,
 * its content merged into History; the old "/config" settings path
 * 404s by design (D-26), while "/preview" itself redirects to
 * "/history" rather than 404ing (D-22) — history_page.py's own comment
 * records that Preview's page-level freshness apparatus (its Refresh
 * link and paired stale banner) was deliberately not ported when its
 * content moved.
 */
(function () {
  "use strict";

  // In the developer's own stated 30-60 second band. Justified against
  // two real numbers already in this codebase: server/poll_loop.py's
  // POLL_INTERVAL_S is a fixed 30 seconds, so a cadence at or below that
  // can be guaranteed-redundant against the pipeline's own writes; and
  // companion/pages/health_page.py's STALE_PIPELINE_WARN_S is 180
  // seconds, so this cadence notices a newly-warn pipeline well inside a
  // quarter of the threshold that defines it. The resulting steady-state
  // cost, spelled out rather than left for a reader to compute: at most
  // one authenticated page render per interval per open, visible Health
  // tab, and exactly zero from a backgrounded or closed one — the
  // number D-12 was written to protect (21-02-PLAN.md, D-18: the
  // interval is now the only gate — there is no user-facing pause).
  var AUTO_REFRESH_INTERVAL_MS = 45000;

  // --- T13 (22-AUDIT.md, 22-UI-SPEC.md §2 and §5 contract 9,
  // --- 22-15-PLAN.md Task 2): the loop no longer stops dead ----------
  //
  // The defect: ANY non-OK response, and any network-level failure,
  // called stopLoop() and hid the pill. The page then sat frozen and
  // silent for the rest of its life, showing data from the moment it
  // loaded with nothing to say it had stopped listening. The commonest
  // trigger is the most ordinary one there is: a laptop lid closed on a
  // cafe network, or a session that expired (which redirect: "manual"
  // below correctly turns into a non-OK response).
  //
  // The retry schedule starts AT the normal cadence rather than below
  // it, and doubles to a stated ceiling. That is deliberate and is the
  // mitigation for T-22-56: a failing server sees a strictly
  // DECREASING request rate from this page, never a higher one, so the
  // repair cannot itself become a load problem. 45s, 90s, 3m, 6m, then
  // 10m for as long as the failure lasts.
  var RETRY_BASE_MS = AUTO_REFRESH_INTERVAL_MS;
  var RETRY_CEILING_MS = 600000;

  // The visible state's copy. These are English FALLBACKS only: the
  // real, translated strings are server-rendered onto <body> by
  // companion/layout.py (page_shell) and read below, the same
  // attribute-with-fallback idiom dirty-state.js and poll-cooldown.js
  // already use. companion/test_i18n.py's Check 6 scans exactly this
  // shape and requires a French catalogue entry for each.
  //
  // The state is NEUTRAL and is never a warning. A browser that lost
  // its connection is not a device fault, and painting it as one is the
  // same class of error as the nightly false alarm this phase removed
  // from the frame strip. It uses .dot--off, the app's own "a neutral,
  // everyday state, never a problem" dot.
  var PAUSED_TEXT = "Paused";
  var RECONNECTING_TEXT = "Reconnecting…";

  // --- 23-05-PLAN.md Task 2 (D22's remainder, D14/CFG-34) -----------
  //
  // The dot beside the freshness line breathes while this loop is live
  // and stops the instant it is not. companion/pages/health_page.py
  // renders it, static and neutral; this file adds and removes ONE
  // class, companion/static/style.css does the rest, and under a
  // reduced-motion preference the stylesheet's global override zeroes
  // it for free.
  //
  // It is .dot--off, the app's own "a neutral, everyday state, never a
  // problem" dot, and it stays that colour in every state. A paused or
  // reconnecting loop is a browser that stopped listening, not a device
  // fault, which is the same argument 22-15 made when it shipped the
  // Paused/Reconnecting badge neutral rather than orange.
  // Built from the attribute name rather than written out as one
  // selector literal, so the name has exactly one site here — and so
  // companion/test_i18n.py's Check 6, which scans every upper-case
  // string constant in this directory and demands a French catalogue
  // entry for it, sees an attribute name (which its own allowlist
  // excludes) rather than a bracketed selector (which its allowlist is
  // documented to exclude but, as written, does not).
  var LIVE_DOT_ATTR = "data-refresh-live-dot";
  var LIVE_DOT_SELECTOR = "[" + LIVE_DOT_ATTR + "]";
  var BREATHING_CLASS = "is-breathing";

  // --- 23-06-PLAN.md Task 1 (D1/CFG-35) ------------------------------
  //
  // The attribute companion/layout.py's page_shell() renders on <body>
  // to say which page this is, and therefore which swap-region list
  // applies. See SWAP_SELECTORS_BY_PAGE below.
  var PAGE_ATTR = "data-refresh-page";

  // The marker a region carries while it holds an optimistic control
  // whose server confirmation has not arrived (layout.py's own
  // REFRESH_PENDING_ATTR). swapNodes() leaves such a region alone
  // entirely — see its own comment for what goes wrong without it.
  // Plan 23-07 is what sets the attribute; this file only reads it.
  var PENDING_ATTR = "data-pending";
  var PENDING_SELECTOR = "[" + PENDING_ATTR + "]";

  // 23-06-PLAN.md Task 2 (D1/CFG-35): the picture that fades when a NEW
  // render arrives. The class is companion/static/style.css's; the
  // image class is companion/pages/home_page.py's own, duplicated here
  // rather than imported for the reason every literal in this file is.
  var FADE_IMAGE_CLASS = "preview-frame__image";
  var FADE_IMAGE_SELECTOR = "." + FADE_IMAGE_CLASS;
  var FADE_CLASS = "is-fading-in";

  // 23-08-PLAN.md Task 1 (D7/CFG-37): the new-row highlight's two
  // literals, both companion/layout.py's
  // (REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS) and both pinned equal to
  // it by companion/test_status_pages.py.
  //
  // The attribute carries a stable identity for the EVENT a row
  // describes, never the row's position — that distinction is the whole
  // mechanism and layout.py's own comment holds the argument for it.
  var ROW_ID_ATTR = "data-flight-id";
  var ROW_ID_SELECTOR = "[" + ROW_ID_ATTR + "]";
  var NEW_ROW_CLASS = "is-new-row";

  // The event this file dispatches on document after a successful swap.
  // The two Flights scripts listen for it; nothing else does, and
  // nothing has to.
  //
  // WHY THIS EXISTS AT ALL, stated once here. Every exclusion in the
  // registry above is the same sentence: a script captured some DOM at
  // load, and there is no re-init hook, so the region it captured can
  // never be swapped. That reasoning is sound and stays — but it is an
  // argument for a hook, not against one, and Flights is the page where
  // the alternative ran out: its list IS the thing that must be
  // replaced, and both list-filter.js and flight-rows.js hold state
  // about the rows in it. So the loop now SAYS when it has swapped, and
  // a script that cares re-derives whatever it owns. It is announced,
  // not commanded: this file knows nothing about what any listener does.
  var SWAPPED_EVENT = "skypane-regions-swapped";

  // Every selector literal above is built from an attribute or class
  // NAME held in its own constant rather than written out whole, which
  // is 23-05's recorded convention for this directory: companion/
  // test_i18n.py's Check 6 scans upper-case string constants here and
  // demands a French catalogue entry for anything it cannot recognise
  // as an identifier — and a bracketed selector is not one of the
  // shapes its allowlist recognises. Giving the name its own constant
  // is independently better anyway: the name then has exactly one site.

  var loadedAtEl = document.querySelector("[data-loaded-at]");
  if (!loadedAtEl) {
    return;
  }

  var raw = loadedAtEl.getAttribute("data-loaded-at");
  if (!raw) {
    return;
  }

  // This file has no access to companion/layout.py's parse_iso() — it
  // must do its own defensive parse-or-noop rather than assuming the
  // attribute is always well-formed.
  var initialParsed = new Date(raw);
  if (isNaN(initialParsed.getTime())) {
    return;
  }
  // Reassigned after every successful swap (see updateLoadedAt() below)
  // — never re-read from loadedAtEl itself, since that element sits
  // inside .page-header__freshness, one of this file's own swap
  // targets, and is a stale/detached node the moment a swap replaces
  // it.
  var loadedAtMs = initialParsed.getTime();

  // Interaction check: true when the user is mid-interaction with
  // something a swap would disrupt. Its failure mode is silence —
  // nothing errors when it stops matching, the page simply starts
  // swapping content out from under a user mid-interaction, and only
  // companion/test_status_pages.py's cross-file DOM-contract check
  // would notice.
  //
  // 19-09-PLAN.md (D-02): the original open-disclosure clause — "any
  // open disclosure anywhere on the page" — is DELETED here on purpose.
  // That clause existed to protect a disclosure from being slammed shut
  // by a whole-page reload; a targeted swap never touches any
  // disclosure element at all (registry/readings disclosures are
  // excluded from the swap target list, see health_page.
  // REFRESH_SWAP_SELECTORS' own comment), so an open disclosure now
  // survives a swap unconditionally, with no guard needed to protect
  // it. D-02's own text names this removal directly: "an open <details>
  // no longer silently suspends the polling".
  function userIsInteracting() {
    // The active element is a form field, a disclosure summary, or a
    // battery-chart hit target — covering a half-typed registry filter
    // query, keyboard disclosure use, and arrow-key traversal of the
    // chart. Read the active element's class through getAttribute(),
    // never the property form: an SVG element's className property is
    // an SVGAnimatedString, not a plain string — the same class of
    // reason companion/static/battery-trend.js's own comment gives for
    // preferring getAttribute() over dataset on SVG elements.
    var active = document.activeElement;
    if (!active) {
      return false;
    }
    var tag = active.tagName ? active.tagName.toUpperCase() : "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "SUMMARY") {
      return true;
    }
    var activeClass = active.getAttribute ? active.getAttribute("class") : null;
    if (activeClass && (" " + activeClass + " ").indexOf(" sparkline-hit ") !== -1) {
      return true;
    }
    return false;
  }

  // 23-06-PLAN.md Task 1 (D1/CFG-35): the third skip, and the only one
  // that stands the WHOLE cycle down rather than one region. A settings
  // page whose form is mid-edit should not be fetching and diffing
  // itself at all: the fetched document describes the SAVED state, so
  // every region it would swap in is a statement about a page the user
  // has already moved on from, and the strip sitting above that form is
  // one of those regions. Standing down is also strictly fewer requests,
  // which is the direction T-23-20 requires.
  //
  // 27-04-PLAN.md (deviation, in-scope per Rule 2 — CFG-63 retired the
  // save bar this gate used to read): SUPERSEDES the account above. The
  // save bar and its own two-marker proof-of-life (B1's lesson,
  // 22-01-PLAN.md Task 3) are both gone — dirty-state.js is now the
  // settings form's auto-save driver, and it exposes the identical
  // question through window.SkyPaneDirtyState.hasUncommittedEdits(),
  // the same small-namespace-object idiom theme-preview.js's own window.
  // SkyPaneLivePreview already established for exactly this kind of
  // cross-script query with no shared module to import. The proof-of-
  // life concern does not reappear in a different shape here: a page
  // whose dirty-state.js never ran (or ran and found no settings form)
  // simply never defines window.SkyPaneDirtyState at all, which this
  // guard reads as "no unsaved edits" — the same honest degrade the bar
  // era's own comment already argued for, and a user actively typing
  // into a field is covered by userIsInteracting() above regardless.
  //
  // Looked up fresh on every call, never cached — the same reason
  // revealPill() below gives.
  function unsavedEdits() {
    return !!(window.SkyPaneDirtyState && window.SkyPaneDirtyState.hasUncommittedEdits());
  }

  // 19-09-PLAN.md (D-02): looked up fresh on every call, never cached
  // in a module-level variable. The pill lives inside
  // .page-header__freshness, one of this file's own swap targets — a
  // cached reference would go stale (detached from the document) the
  // moment the very first successful swap replaces that wrapper, and
  // every reveal/hide after that would silently do nothing.
  function revealPill() {
    // T13 (22-15-PLAN.md Task 2): suppressed while a state badge is
    // showing. A retry attempt is still a request in flight, but
    // swapping "Reconnecting…" for "Updating…" on every attempt and
    // back again would flicker between two claims about the same
    // situation, and the honest one while a connection is failing is
    // the one that says so.
    if (currentState !== null) {
      return;
    }
    var pill = document.querySelector("[data-refresh-pill]");
    if (pill) {
      pill.hidden = false;
    }
  }

  function hidePill() {
    var pill = document.querySelector("[data-refresh-pill]");
    if (pill) {
      pill.hidden = true;
    }
  }

  // T13's visible state. Null while the loop is healthy; "reconnecting"
  // while a retry is pending; "paused" while the loop is deliberately
  // idle, which after 21-02-PLAN.md's D-18 means exactly one thing —
  // the tab is hidden, the only gate this loop has left.
  var currentState = null;

  // Looked up fresh on every call and REBUILT if missing, for the same
  // reason revealPill() above refuses to cache: this pill is a child of
  // .page-header__freshness, one of this file's own swap targets, so a
  // successful refresh can legitimately replace the element out from
  // under a cached reference. Rebuilding is cheap and is the only
  // mechanism that survives a swap.
  //
  // Built with createElement/appendChild/textContent only. The standing
  // HTML-writing-sink ban this file carries is absolute, and a pill
  // whose text comes from a server-rendered attribute is exactly the
  // sort of thing that invites a markup-writing shortcut; there is
  // none, and the guard in companion/test_companion_app.py would fail
  // if there were.
  //
  // It renders in flow, inside the freshness line, rather than taking
  // .page-header .refresh-pill's absolute top-right slot: that slot is
  // already occupied by the "Updating…" pill, and two pills stacked on
  // the same coordinates is not a state a user can read. It is
  // .banner__pill, this file's label-voice badge primitive, per
  // 22-UI-SPEC.md's own T13 row.
  function stateBadge() {
    var existing = document.querySelector("[data-refresh-state-pill]");
    if (existing) {
      return existing;
    }
    var anchor = document.querySelector("[data-refresh-pill]");
    if (!anchor || !anchor.parentNode) {
      return null;
    }
    var badge = document.createElement("span");
    badge.className = "banner__pill";
    badge.setAttribute("data-refresh-state-pill", "");
    badge.hidden = true;
    var dot = document.createElement("span");
    dot.className = "dot dot--off";
    badge.appendChild(dot);
    var label = document.createElement("span");
    label.setAttribute("data-refresh-state-text", "");
    badge.appendChild(label);
    anchor.parentNode.insertBefore(badge, anchor.nextSibling);
    return badge;
  }

  // The translated string, server-rendered onto <body> by
  // companion/layout.py's page_shell(). The English constants above are
  // the no-attribute fallback and nothing else.
  function stateText(state) {
    var attr = state === "paused"
      ? "data-refresh-paused-text" : "data-refresh-reconnecting-text";
    var fallback = state === "paused" ? PAUSED_TEXT : RECONNECTING_TEXT;
    var host = document.body;
    var value = host ? host.getAttribute(attr) : null;
    return value || fallback;
  }

  function setState(state) {
    currentState = state;
    // Exactly one pill is ever visible. The "Updating…" pill means a
    // request is in flight and succeeding; this badge means it is not.
    hidePill();
    var badge = stateBadge();
    if (!badge) {
      return;
    }
    var label = badge.querySelector("[data-refresh-state-text]");
    if (label) {
      label.textContent = stateText(state);
    }
    badge.hidden = false;
    syncLiveDot();
  }

  function clearState() {
    currentState = null;
    var badge = document.querySelector("[data-refresh-state-pill]");
    if (badge) {
      badge.hidden = true;
    }
    syncLiveDot();
  }

  // 23-05-PLAN.md Task 2: DERIVED from this loop's own two state
  // variables, never tracked separately. There is no second state
  // machine here and there must not be one — two sources for one claim
  // is this codebase's most repeated defect, and a dot that breathes
  // while the page is not actually listening is exactly the lie D22
  // exists to remove (T-23-15).
  //
  // Live means both halves at once: an interval exists AND no state
  // badge is showing. A paused tab has no interval; a reconnecting
  // page has one but is failing, and its ladder — not the interval —
  // owns the schedule.
  //
  // Looked up fresh on every call and never cached, for the same reason
  // revealPill() above refuses to cache: this dot is a child of
  // .page-header__freshness, one of this file's own swap targets, so a
  // successful refresh legitimately replaces it. succeed() below calls
  // clearState() immediately after every swap, which is what re-applies
  // the class to the newly-rendered dot.
  function syncLiveDot() {
    var dot = document.querySelector(LIVE_DOT_SELECTOR);
    if (!dot || !dot.classList) {
      return;
    }
    if (intervalHandle !== null && currentState === null) {
      dot.classList.add(BREATHING_CLASS);
      return;
    }
    dot.classList.remove(BREATHING_CLASS);
  }

  // 19-09-PLAN.md (D-02): the single, greppable swap-target list. Must
  // stay in agreement, selector for selector, with the Python registry
  // — companion/test_status_pages.py's own cross-file check pins the
  // two equal. Comma-grouped selectors (one entry, several
  // comma-separated clauses) are valid querySelectorAll() input and
  // count as one entry each, matching the Python tuple's own shape.
  //
  // 23-06-PLAN.md Task 1 (D1/CFG-35): one list became a REGISTRY. D1
  // puts this loop on Home and on the Display scope as well as Health,
  // and the honest way to serve three pages from one loop is for the
  // page to declare its own regions rather than for this file to grow a
  // branch per page. The keys are companion/layout.py's nav_slug()
  // values, and the check above pins the two key sets EQUAL in both
  // directions: a key here that the Python does not have is a list
  // nothing renders, and a key there that this file lacks is a page
  // that silently never refreshes.
  //
  // Each page's own list is documented where it is defined
  // (companion/layout.py's REFRESH_SWAP_SELECTORS_BY_PAGE), including
  // what each page deliberately EXCLUDES and why — that reasoning has
  // one home and this is not it.
  var SWAP_SELECTORS_BY_PAGE = {
    "home": [
      ".page-header__freshness",
      ".frame-strip",
      ".home-status-grid",
      "figure.preview-frame",
      'section[aria-labelledby="home-flights"]'
    ],
    "display": [
      ".page-header__freshness",
      ".frame-strip"
    ],
    "health": [
      ".dashboard-grid",
      "div.banner--anomaly, div.banner--warn",
      "section.banner",
      ".page-header__freshness",
      'a[href="/health"]'
    ],
    "flights": [
      ".page-header__freshness",
      "ul.history-cards",
      ".data-table-wrap",
      "[data-filter-count]",
      ".flights-more"
    ]
  };

  // The page key, server-rendered on <body> by page_shell(). <body> and
  // not an element inside the page, for the reason the two copy
  // attributes beside it give: several regions below ARE swap targets,
  // and an attribute there would be replaced out from under this file
  // on the first successful refresh.
  //
  // hasOwnProperty and not a bare lookup: this key arrives as markup,
  // and "constructor" or "toString" would otherwise resolve to an
  // inherited Object property — a function, not a list — which is a
  // strange crash rather than the no-op that is correct here.
  //
  // The SECOND guard on this file, and both are load-bearing: the
  // [data-loaded-at] one above is what keeps every page with no
  // freshness marker free, and this one is what keeps a page that has
  // one but declares no regions from swapping things nobody listed.
  var pageKey = document.body ? document.body.getAttribute(PAGE_ATTR) : null;
  if (!pageKey
      || !Object.prototype.hasOwnProperty.call(SWAP_SELECTORS_BY_PAGE, pageKey)) {
    return;
  }
  var SWAP_SELECTORS = SWAP_SELECTORS_BY_PAGE[pageKey];

  // 19-09-PLAN.md (D-02): for each swap selector, look up matching
  // nodes in both the live document and the freshly-fetched one, and
  // replace each live node at a given index with document.importNode()
  // of its fetched counterpart at the same index — using replaceChild(),
  // not the newer replaceWith(), for ES5-era reach. An index present on
  // only one side (a banner that just appeared, or just cleared) is
  // never touched: the newly-appearing/disappearing region simply waits
  // for the next real navigation, exactly the same accepted cost this
  // file's own header already names for the sparkline/registry.
  //
  // T13 (22-15-PLAN.md Task 2): the swap is now TARGETED. Two skips,
  // each of which leaves the live node exactly where it is:
  //
  //   1. The region did not change. isEqualNode() compares node type,
  //      name, attributes and children recursively, across documents,
  //      with no HTML string anywhere — which is why it, and not a
  //      serialized-markup comparison, is the mechanism here: the
  //      serializing properties are on this file's standing ban list,
  //      and for good reason. On a
  //      healthy Health page most cycles change one region out of five;
  //      replacing the other four destroyed and rebuilt their whole
  //      subtrees for no reason, taking any focus, selection or
  //      :active state inside them with it.
  //   2. The user's focus is inside the region. userIsInteracting()
  //      above already skips the whole tick for a focused field,
  //      summary or chart point, but it cannot see focus on an ordinary
  //      link or button inside a swap target — and a refresh that
  //      silently moves keyboard focus to the top of the document while
  //      someone is tabbing through a card is the same A-20 harm the
  //      whole-page reload was retired for, just smaller.
  //   3. The region holds an UNCONFIRMED OPTIMISTIC CONTROL
  //      (23-06-PLAN.md Task 1, T-23-21). D1 and D2 meet here: a switch
  //      flipped a moment ago has already painted its new state, and
  //      the server answer confirming it has not arrived yet — so the
  //      document this loop just fetched still describes the OLD state,
  //      honestly and uselessly. Swapping it in makes the control
  //      visibly bounce back under the user's finger and then forward
  //      again a second later, which reads as the page overruling them.
  //      The rule is per REGION and not per tick on purpose: one
  //      unconfirmed control must not stand down the refresh of
  //      everything else on the page. The accepted cost, stated: a
  //      control whose confirmation never arrives holds its own region
  //      stale until it clears or the user navigates — which is the
  //      correct trade, because the region is showing what the user
  //      asked for and the alternative is showing them the opposite.
  //      This file only READS the marker; plan 23-07 is what sets it.
  function swapNodes(fromDoc) {
    var active = document.activeElement;
    for (var s = 0; s < SWAP_SELECTORS.length; s++) {
      var existingNodes = document.querySelectorAll(SWAP_SELECTORS[s]);
      var fetchedNodes = fromDoc.querySelectorAll(SWAP_SELECTORS[s]);
      var count = Math.min(existingNodes.length, fetchedNodes.length);
      for (var i = 0; i < count; i++) {
        var existing = existingNodes[i];
        if (existing.isEqualNode && existing.isEqualNode(fetchedNodes[i])) {
          continue;
        }
        if (active && existing.contains && existing.contains(active)) {
          continue;
        }
        // Asked of the region itself AND of its subtree: a control
        // that IS the region and a control inside a card mean the same
        // thing here.
        if ((existing.hasAttribute && existing.hasAttribute(PENDING_ATTR))
            || (existing.querySelector && existing.querySelector(PENDING_SELECTOR))) {
          continue;
        }
        var replacement = document.importNode(fetchedNodes[i], true);
        markPictureFade(existing, replacement);
        existing.parentNode.replaceChild(replacement, existing);
      }
    }
  }

  // 23-06-PLAN.md Task 2 (D1/CFG-35): the frame picture fades in when a
  // NEW render arrives, and does NOT animate when the same picture is
  // swapped back in.
  //
  // The condition is the whole point. The picture's region is replaced
  // on most cycles for reasons that have nothing to do with the picture
  // — its caption carries a timestamp, so the fetched figure differs
  // from the live one whenever the clock has moved. A fade fired on
  // every swap would flash the page every 45 seconds to say nothing,
  // which is worse than no fade: it teaches the user that the movement
  // means nothing, and then a real new render means nothing either.
  //
  // The src attribute is the honest signal and needs no marker
  // invented for it: the gallery names every render after its own
  // instant, so a new render IS a new src. Read through
  // getAttribute() rather than the .src property on purpose — the
  // property resolves to an absolute URL
  // against each document's own base, and these two nodes come from two
  // different documents, so the property form can report a difference
  // where the markup has none.
  //
  // The class goes on the node that is about to be inserted, before it
  // is inserted, so the animation starts with the element's first
  // frame. Nothing removes it afterwards and nothing needs to: the
  // animation runs once, the element's own opacity is 1 before and
  // after, and the next swap replaces the node entirely.
  function markPictureFade(existing, replacement) {
    var fetchedImage = replacement.querySelector
      ? replacement.querySelector(FADE_IMAGE_SELECTOR) : null;
    if (!fetchedImage || !fetchedImage.classList) {
      return;
    }
    var liveImage = existing.querySelector
      ? existing.querySelector(FADE_IMAGE_SELECTOR) : null;
    if (liveImage
        && liveImage.getAttribute("src") === fetchedImage.getAttribute("src")) {
      return;
    }
    fetchedImage.classList.add(FADE_CLASS);
  }

  // 23-08-PLAN.md Task 1 (D7/CFG-37): the new-row highlight — a diff
  // over server-rendered row identity, applied after a swap and to
  // nothing else.
  //
  // WHAT WOULD BE WRONG, since that is what the shape here is chosen
  // against. Highlighting every row after a swap says "everything is
  // new" every forty-five seconds, which is the same as saying nothing.
  // Highlighting on first paint says the whole list just arrived, which
  // is false — it was already there when the reader opened the page.
  // Both failures are one missing thing: a set of identities known
  // BEFORE. So the set is populated from the page AS FIRST RENDERED,
  // below, and never starts empty.
  //
  // hasOwnProperty and not a bare lookup, for the reason the page-key
  // guard above gives: these identities arrive as markup, and
  // "constructor" or "toString" would otherwise resolve to an inherited
  // Object property and read as already-known.
  //
  // The class is added and never removed, and nothing needs to remove
  // it: the node it lands on was itself just inserted by the swap, so
  // its animation starts with the element's first frame and runs once;
  // the element's own background is its normal one before and after;
  // and the next swap replaces the node entirely. A removal path would
  // only be a way to re-trigger the same arrival twice.
  function collectRowIds() {
    var seen = {};
    var nodes = document.querySelectorAll(ROW_ID_SELECTOR);
    for (var i = 0; i < nodes.length; i++) {
      var value = nodes[i].getAttribute(ROW_ID_ATTR);
      if (value) {
        seen[value] = true;
      }
    }
    return seen;
  }

  function markNewRows() {
    var nodes = document.querySelectorAll(ROW_ID_SELECTOR);
    var next = {};
    for (var i = 0; i < nodes.length; i++) {
      var node = nodes[i];
      var value = node.getAttribute(ROW_ID_ATTR);
      if (!value) {
        continue;
      }
      if (!Object.prototype.hasOwnProperty.call(knownRowIds, value)
          && node.classList) {
        node.classList.add(NEW_ROW_CLASS);
      }
      next[value] = true;
    }
    knownRowIds = next;
  }

  // The page as first rendered. Every row visible on load is, by
  // definition, not news.
  var knownRowIds = collectRowIds();

  // 23-08-PLAN.md Task 1: the loop says it swapped; it does not say what
  // anyone should do about it. Dispatched on document so a listener
  // needs no reference to any element this file touches, and built the
  // ES3-era way (createEvent/initEvent) rather than with the Event
  // constructor, for the same reach reason this file uses replaceChild
  // over replaceWith.
  //
  // Fired once per successful swap, after every region is in place and
  // after the diff above, so a listener always sees the finished
  // document. Never fired for a cycle that fetched and swapped nothing
  // — there would be nothing to re-derive.
  function announceSwap() {
    if (!document.createEvent) {
      return;
    }
    var evt = document.createEvent("Event");
    evt.initEvent(SWAPPED_EVENT, false, false);
    document.dispatchEvent(evt);
  }

  // 19-09-PLAN.md (D-02): battery-trend.js's own two readout spans are
  // written through textContent on the EXISTING nodes, never replaced —
  // contract 2 in this file's own SUPERSEDED section above. Skipped
  // entirely while a chart point is actively revealed
  // (.sparkline-hit--active), so a hovered/focused reading is never
  // stomped by a background refresh.
  function swapBatteryReadout(fromDoc) {
    if (document.querySelector(".sparkline-hit--active")) {
      return;
    }
    var value = document.querySelector(".battery-readout__value");
    var detail = document.querySelector(".battery-readout__detail");
    var fetchedValue = fromDoc.querySelector(".battery-readout__value");
    var fetchedDetail = fromDoc.querySelector(".battery-readout__detail");
    if (value && fetchedValue) {
      value.textContent = fetchedValue.textContent;
    }
    if (detail && fetchedDetail) {
      detail.textContent = fetchedDetail.textContent;
      var title = fetchedDetail.getAttribute("title");
      if (title !== null) {
        detail.setAttribute("title", title);
      }
    }
  }

  // 19-09-PLAN.md (D-02): the freshness wrapper (one of SWAP_SELECTORS'
  // own entries) carries the live data-loaded-at marker, so reading it
  // straight off the just-fetched document is the honest "when was this
  // content actually generated" value — never Date.now(), which would
  // only say "when did this browser finish parsing", a different and
  // less useful instant.
  function updateLoadedAt(fromDoc) {
    var fetchedMarker = fromDoc.querySelector("[data-loaded-at]");
    var rawValue = fetchedMarker ? fetchedMarker.getAttribute("data-loaded-at") : null;
    var nextParsed = rawValue ? new Date(rawValue) : null;
    loadedAtMs = (nextParsed && !isNaN(nextParsed.getTime()))
      ? nextParsed.getTime() : Date.now();
  }

  // 21-02-PLAN.md (D-18): the Pause/Resume button that used to live
  // inside .page-header__freshness — one of SWAP_SELECTORS' own entries
  // — is deleted outright, with no replacement. applySwap() below no
  // longer needs to re-wire anything after a swap replaces that
  // wrapper.
  function applySwap(fromDoc) {
    swapNodes(fromDoc);
    swapBatteryReadout(fromDoc);
    updateLoadedAt(fromDoc);
    // AFTER the regions are in place, never before: a diff taken
    // against the document that is about to be thrown away would
    // compare the old page with itself.
    markNewRows();
    announceSwap();
  }

  // T13 (22-15-PLAN.md Task 2): the in-flight guard. Without it a
  // request slower than the interval, or a visibilitychange catch-up
  // landing on top of a running tick, could put two fetches in the air
  // at once — and whichever resolved LAST would win the swap, so a
  // stale response could overwrite a fresher one. Set before the fetch
  // and cleared in both terminal branches, never only the happy one.
  var inFlight = false;

  function doRefresh() {
    if (inFlight) {
      return;
    }
    inFlight = true;
    revealPill();
    // 19-09-PLAN.md (D-02/T-19-33): window.location.href — the same-
    // document URL — and NEVER a URL read out of the DOM. This is a
    // security property, not a style preference: the fetch target must
    // never be readable from, or influenced by, injected markup. No
    // URL-taking navigation form (an assignment to the page's own
    // location, or a call to assign/replace/open) appears anywhere in
    // this file, preserving the exact property the retired reload-only
    // file's own comment protected.
    //
    // redirect: "manual" (T-19-34): fetch()'s default behaviour silently
    // FOLLOWS a same-origin redirect and reports the FINAL response's
    // status — so a session that expired between page loads would make
    // this fetch transparently land on the login page and report status
    // 200, which is indistinguishable from a genuine Health refresh
    // without this option. With redirect: "manual", a redirect response
    // (the 303 an expired session produces) instead resolves to an
    // opaque response whose ok is false — caught by the same "non-OK
    // status" branch below, with no separate code path needed.
    fetch(window.location.href, {
      credentials: "same-origin",
      redirect: "manual",
      headers: {"X-Requested-With": "freshness"}
    }).then(function (response) {
      if (!response.ok) {
        // A non-OK status (including the opaque redirect above) means
        // do NOT swap anything and do NOT navigate — leave the stale
        // page visible. A redirect must never be mistaken for fresh
        // data, and a partial swap is worse than none.
        //
        // T13 (22-15-PLAN.md Task 2): what this branch must NOT do any
        // more is stop. It schedules the next attempt at a growing
        // delay and says so, in the pill.
        failAndRetry();
        return null;
      }
      return response.text();
    }).then(function (text) {
      if (text === null || typeof text === "undefined") {
        return;
      }
      // The load-bearing choice: DOMParser.parseFromString() is NOT an
      // HTML-writing sink on the LIVE document — it builds an inert,
      // detached document with no script execution and no external
      // resource loading — so the standing markup-writing-sink ban
      // stays absolute for this file too, and this rewrite introduces
      // no markup-writing surface on the page the user is actually
      // looking at.
      var fetchedDoc = new DOMParser().parseFromString(text, "text/html");
      applySwap(fetchedDoc);
      inFlight = false;
      hidePill();
      // T13: the first success resets the backoff to zero and clears
      // the state badge, so a page that recovers stops saying it has
      // not, and the next real failure starts its own ladder from the
      // bottom rather than inheriting the last one's ceiling.
      succeed();
    }).catch(function () {
      // A network-level failure (offline, DNS, aborted) gets the exact
      // same treatment as a non-OK status, for the same reason: no
      // partial swap and no guess. Since T13 that treatment is a
      // backed-off retry with a visible neutral state, not a silent
      // stop.
      failAndRetry();
    });
  }

  // Single interval handle, one null-ish sentinel. Starting is a no-op
  // when a handle already exists — what stops repeated visibility
  // toggles from stacking two or three intervals onto one page, which
  // would show up as multiple refreshes per cycle rather than as an
  // error.
  var intervalHandle = null;

  // T13 (22-15-PLAN.md Task 2): the retry ladder's own state. A pending
  // retry is a one-shot timer, deliberately NOT a second interval —
  // each failure schedules exactly one next attempt, so the ladder can
  // never fan out.
  var retryHandle = null;
  var retryDelayMs = 0;

  function cancelRetry() {
    if (retryHandle !== null) {
      window.clearTimeout(retryHandle);
      retryHandle = null;
    }
  }

  function failAndRetry() {
    inFlight = false;
    retryDelayMs = retryDelayMs === 0
      ? RETRY_BASE_MS
      : Math.min(retryDelayMs * 2, RETRY_CEILING_MS);
    setState("reconnecting");
    cancelRetry();
    // While a retry is pending the ladder OWNS the schedule and tick()
    // below stands down, so the two can never both fire. That is what
    // makes the backoff a real reduction in request rate rather than an
    // extra request laid on top of the normal cadence. The interval
    // itself is deliberately left running as a plain heartbeat: it
    // needs no teardown and no restart, and there is therefore no state
    // in which a recovered page is left with no schedule at all — which
    // is precisely the failure T13 exists to remove.
    retryHandle = window.setTimeout(function () {
      retryHandle = null;
      if (document.hidden) {
        // A tab that went away mid-ladder is not a failing server. The
        // visibilitychange listener below re-arms everything on return;
        // do not keep a background tab retrying.
        setState("paused");
        return;
      }
      doRefresh();
    }, retryDelayMs);
  }

  function succeed() {
    retryDelayMs = 0;
    cancelRetry();
    clearState();
  }

  function tick() {
    // Belt and braces: the visibility listener below already stops this
    // interval on hide, but an interval that somehow survives must not
    // fire in a background tab.
    if (document.hidden) {
      stopLoop();
      return;
    }
    if (retryHandle !== null) {
      // A retry is already scheduled; the ladder owns the cadence until
      // it succeeds. Leave the interval running — it is the heartbeat
      // that takes over the moment the ladder clears.
      return;
    }
    if (userIsInteracting()) {
      // Leave the interval running — the next tick tries again.
      return;
    }
    if (unsavedEdits()) {
      // Leave the interval running — the next tick tries again, and the
      // one after the user saves succeeds.
      return;
    }
    doRefresh();
  }

  function startLoop() {
    if (intervalHandle !== null) {
      return;
    }
    intervalHandle = window.setInterval(tick, AUTO_REFRESH_INTERVAL_MS);
    syncLiveDot();
  }

  function stopLoop() {
    if (intervalHandle === null) {
      return;
    }
    window.clearInterval(intervalHandle);
    intervalHandle = null;
    syncLiveDot();
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      // Deliberate idling, and the only kind this loop has left after
      // 21-02-PLAN.md's D-18 retired the user-facing Pause control. The
      // retry ladder stands down with the interval: a hidden tab must
      // cost the server nothing at all, which was already this file's
      // contract and stays so.
      stopLoop();
      cancelRetry();
      setState("paused");
      return;
    }
    // Back in view: drop the paused badge, re-arm the interval, and let
    // the catch-up below decide whether to fetch immediately. A ladder
    // that was mid-retry when the tab went away restarts from the
    // normal cadence rather than from wherever it had climbed to.
    clearState();
    retryDelayMs = 0;
    startLoop();
    // Catch-up on return: a tab returning after a long hidden stretch
    // would otherwise sit showing minutes-old data for a full interval
    // — precisely the failure the retired stale-view banner was
    // invented to report, and it would be perverse to remove the
    // banner and then reproduce its own trigger condition.
    var elapsed = Date.now() - loadedAtMs;
    if (elapsed > AUTO_REFRESH_INTERVAL_MS && !userIsInteracting() && !unsavedEdits()) {
      doRefresh();
    }
  });

  // A page that loads in a background tab starts stopped (tab
  // visibility only — 21-02-PLAN.md, D-18: there is no separate
  // user-facing pause state any more).
  if (!document.hidden) {
    startLoop();
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
