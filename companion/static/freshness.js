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
  function swapNodes(fromDoc) {
    for (var s = 0; s < SWAP_SELECTORS.length; s++) {
      var existingNodes = document.querySelectorAll(SWAP_SELECTORS[s]);
      var fetchedNodes = fromDoc.querySelectorAll(SWAP_SELECTORS[s]);
      var count = Math.min(existingNodes.length, fetchedNodes.length);
      for (var i = 0; i < count; i++) {
        var existing = existingNodes[i];
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

  function doRefresh() {
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
        // do NOT swap anything and do NOT navigate — hide the pill,
        // stop the loop, and leave the stale page visible. Silent
        // failure is better than a partial swap, and a redirect must
        // never be mistaken for fresh data.
        hidePill();
        stopLoop();
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
      hidePill();
    }).catch(function () {
      // A network-level failure (offline, DNS, aborted) gets the exact
      // same treatment as a non-OK status, for the same reason: no
      // partial swap, no guess, just a visibly stale page and a stopped
      // loop.
      hidePill();
      stopLoop();
    });
  }

  // Single interval handle, one null-ish sentinel. Starting is a no-op
  // when a handle already exists — what stops repeated visibility
  // toggles from stacking two or three intervals onto one page, which
  // would show up as multiple refreshes per cycle rather than as an
  // error.
  var intervalHandle = null;

  function tick() {
    // Belt and braces: the visibility listener below already stops this
    // interval on hide, but an interval that somehow survives must not
    // fire in a background tab.
    if (document.hidden) {
      stopLoop();
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
  }

  function stopLoop() {
    if (intervalHandle === null) {
      return;
    }
    window.clearInterval(intervalHandle);
    intervalHandle = null;
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      stopLoop();
      return;
    }
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
