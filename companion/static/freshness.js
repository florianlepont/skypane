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
  // stay in agreement, selector for selector, with health_page.
  // REFRESH_SWAP_SELECTORS — companion/test_status_pages.py's own
  // cross-file check pins the two lists equal. Comma-grouped selectors
  // (one array entry, several comma-separated clauses) are valid
  // querySelectorAll() input and count as one entry each, matching the
  // Python tuple's own shape.
  var SWAP_SELECTORS = [
    ".dashboard-grid",
    "div.banner--anomaly, div.banner--warn",
    "section.banner",
    ".page-header__freshness",
    'a[href="/health"]'
  ];

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
        var replacement = document.importNode(fetchedNodes[i], true);
        existing.parentNode.replaceChild(replacement, existing);
      }
    }
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
    if (elapsed > AUTO_REFRESH_INTERVAL_MS && !userIsInteracting()) {
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
