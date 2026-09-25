/*
 * SkyPane companion service — freshness.js.
 *
 * Written to an ES5-safe subset (no let/const/arrow functions/template
 * literals) so it ships with no build step. Served by
 * companion/app.py's FRESHNESS_SCRIPT_ROUTE to every page; it exits
 * early unless the page has a [data-loaded-at] element and a
 * recognised data-refresh-page value on <body>, so a page missing
 * either simply renders server-side with no auto-refresh.
 */
(function () {
  "use strict";

  // 45s: below server/poll_loop.py's 30s POLL_INTERVAL_S would be
  // guaranteed-redundant; well inside a quarter of health_page.py's
  // 180s STALE_PIPELINE_WARN_S so a newly-warn pipeline is caught fast.
  var AUTO_REFRESH_INTERVAL_MS = 45000;

  // Retry ladder for a non-OK response or network failure: starts at
  // the normal cadence and doubles to a ten-minute ceiling, so a
  // failing server sees a strictly decreasing request rate, never a
  // higher one.
  var RETRY_BASE_MS = AUTO_REFRESH_INTERVAL_MS;
  var RETRY_CEILING_MS = 600000;

  // English fallbacks; companion/layout.py's page_shell() renders the
  // translated strings onto <body> and stateText() below reads them.
  // Neutral state, never a warning: a browser that lost its connection
  // is not a device fault.
  var PAUSED_TEXT = "Paused";
  var RECONNECTING_TEXT = "Reconnecting…";

  // The dot beside the freshness line breathes while the loop is live;
  // companion/static/style.css owns the animation and zeroes it under
  // a reduced-motion preference.
  var LIVE_DOT_ATTR = "data-refresh-live-dot";
  var LIVE_DOT_SELECTOR = "[" + LIVE_DOT_ATTR + "]";
  var BREATHING_CLASS = "is-breathing";

  // Which page this is, server-rendered on <body> by
  // companion/layout.py's page_shell(). See SWAP_SELECTORS_BY_PAGE.
  var PAGE_ATTR = "data-refresh-page";

  // Marks a region holding an optimistic control whose server
  // confirmation has not arrived yet (layout.py's REFRESH_PENDING_ATTR);
  // swapNodes() leaves such a region alone entirely.
  var PENDING_ATTR = "data-pending";
  var PENDING_SELECTOR = "[" + PENDING_ATTR + "]";

  // The frame picture's fade-in class and the image class it targets,
  // both companion/pages/home_page.py's own.
  var FADE_IMAGE_CLASS = "preview-frame__image";
  var FADE_IMAGE_SELECTOR = "." + FADE_IMAGE_CLASS;
  var FADE_CLASS = "is-fading-in";

  // New-row highlight attribute/class, both companion/layout.py's
  // (REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS). The attribute carries
  // a stable identity for the event a row describes, not its position.
  var ROW_ID_ATTR = "data-flight-id";
  var ROW_ID_SELECTOR = "[" + ROW_ID_ATTR + "]";
  var NEW_ROW_CLASS = "is-new-row";

  // Dispatched on document after a successful swap so a listener needs
  // no reference to any element this file touches; list-filter.js and
  // flight-rows.js re-derive their own row state from it.
  var SWAPPED_EVENT = "skypane-regions-swapped";

  var loadedAtEl = document.querySelector("[data-loaded-at]");
  if (!loadedAtEl) {
    return;
  }

  var raw = loadedAtEl.getAttribute("data-loaded-at");
  if (!raw) {
    return;
  }

  // Defensive parse-or-noop: this file has no access to
  // companion/layout.py's parse_iso() and cannot assume the attribute
  // is well-formed.
  var initialParsed = new Date(raw);
  if (isNaN(initialParsed.getTime())) {
    return;
  }
  // Reassigned after every successful swap (see updateLoadedAt()); never
  // re-read from loadedAtEl, which is inside a swap target and goes
  // stale the moment a swap replaces it.
  var loadedAtMs = initialParsed.getTime();

  // True when the user is mid-interaction with something a swap would
  // disrupt: a form field, a disclosure summary, or a battery-chart hit
  // target. An open <details> is not checked here — a targeted swap
  // never touches a disclosure element, so it survives unconditionally.
  function userIsInteracting() {
    // Read the active element's class through getAttribute(), not the
    // property: an SVG element's className is an SVGAnimatedString, not
    // a plain string (see battery-trend.js's own comment).
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

  // Stands the whole cycle down when the settings form is mid-edit, so
  // the fetched document (the saved state) is never swapped in over
  // unsaved changes. dirty-state.js is the settings form's auto-save
  // driver and exposes this through window.SkyPaneDirtyState — a page
  // whose dirty-state.js never ran simply has no unsaved edits.
  //
  // Looked up fresh on every call, never cached — the same reason
  // revealPill() below gives.
  function unsavedEdits() {
    return !!(window.SkyPaneDirtyState && window.SkyPaneDirtyState.hasUncommittedEdits());
  }

  // Looked up fresh, never cached in a module-level variable: the pill
  // lives inside a swap target and a cached reference would go stale
  // the moment the first successful swap replaces that wrapper.
  function revealPill() {
    // Suppressed while a state badge is showing, so "Reconnecting…"
    // and "Updating…" never flicker against each other for the same
    // in-flight request.
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

  // Null while the loop is healthy; "reconnecting" while a retry is
  // pending; "paused" while the tab is hidden, the only gate this loop
  // has left.
  var currentState = null;

  // Looked up fresh and rebuilt if missing: this pill is a child of a
  // swap target, so a successful refresh can replace it out from under
  // a cached reference. Built with createElement/appendChild/textContent
  // only, never an HTML-writing sink.
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

  // Derived from the loop's own two state variables, never tracked
  // separately: live means an interval exists AND no state badge is
  // showing. Looked up fresh and never cached, since this dot is a
  // child of a swap target and a successful refresh replaces it.
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

  // Swap-target registry, one list per page (companion/layout.py's
  // nav_slug() values). Must stay in agreement, selector for selector,
  // with companion/layout.py's REFRESH_SWAP_SELECTORS_BY_PAGE, which
  // also documents what each page deliberately excludes and why.
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

  // The page key, server-rendered on <body> by page_shell() (not an
  // inner element, since several regions below are swap targets).
  // hasOwnProperty and not a bare lookup, since the key arrives as
  // markup and "constructor"/"toString" would otherwise resolve to an
  // inherited Object property instead of the correct no-op.
  var pageKey = document.body ? document.body.getAttribute(PAGE_ATTR) : null;
  if (!pageKey
      || !Object.prototype.hasOwnProperty.call(SWAP_SELECTORS_BY_PAGE, pageKey)) {
    return;
  }
  var SWAP_SELECTORS = SWAP_SELECTORS_BY_PAGE[pageKey];

  // For each swap selector, replaces each live node at a given index
  // with document.importNode() of its fetched counterpart at the same
  // index, via replaceChild() for ES5-era reach. An index present on
  // only one side is left untouched until the next real navigation.
  // A node is skipped, and left exactly as it is, when: its isEqualNode()
  // match says the region is unchanged; the user's focus is inside it;
  // or it (or a descendant) carries PENDING_ATTR, meaning an optimistic
  // control's server confirmation has not arrived yet and swapping
  // would visibly bounce it back under the user's hand. This file only
  // reads that marker.
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
        // Checked on the region itself and on its subtree.
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

  // Fades the frame picture in only when its src actually changed,
  // since the caption's timestamp alone would make every cycle look
  // different. Read through getAttribute(), not .src, because that
  // property resolves to an absolute URL against each document's own
  // base and the two nodes come from different documents. The class is
  // added before insertion and never removed; the next swap replaces
  // the node entirely.
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

  // New-row highlight: a diff over server-rendered row identity
  // (ROW_ID_ATTR), applied after a swap. The known-identity set is
  // seeded from the page as first rendered (below), never empty, so a
  // row already on the page at load is never marked new. hasOwnProperty
  // and not a bare lookup, since these identities arrive as markup.
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

  // Fired once per successful swap, after every region and the row-id
  // diff are in place, so a listener always sees the finished document.
  // Built the ES3-era way (createEvent/initEvent) for the same reach
  // reason this file uses replaceChild over replaceWith.
  function announceSwap() {
    if (!document.createEvent) {
      return;
    }
    var evt = document.createEvent("Event");
    evt.initEvent(SWAPPED_EVENT, false, false);
    document.dispatchEvent(evt);
  }

  // battery-trend.js's two readout spans are updated via textContent on
  // the existing nodes, never replaced, and skipped entirely while a
  // chart point is actively revealed, so a hovered reading is never
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

  // The freshness wrapper carries the live data-loaded-at marker;
  // reading it off the just-fetched document (never Date.now()) is when
  // the content was actually generated, not when this browser parsed it.
  function updateLoadedAt(fromDoc) {
    var fetchedMarker = fromDoc.querySelector("[data-loaded-at]");
    var rawValue = fetchedMarker ? fetchedMarker.getAttribute("data-loaded-at") : null;
    var nextParsed = rawValue ? new Date(rawValue) : null;
    loadedAtMs = (nextParsed && !isNaN(nextParsed.getTime()))
      ? nextParsed.getTime() : Date.now();
  }

  function applySwap(fromDoc) {
    swapNodes(fromDoc);
    swapBatteryReadout(fromDoc);
    updateLoadedAt(fromDoc);
    // After the regions are in place, never before: a diff taken
    // against the document about to be thrown away would compare the
    // old page with itself.
    markNewRows();
    announceSwap();
  }

  // In-flight guard: without it, a slow response plus a visibilitychange
  // catch-up could put two fetches in the air, and whichever resolved
  // last would win the swap, overwriting a fresher response with a
  // stale one. Set before the fetch and cleared in both terminal
  // branches.
  var inFlight = false;

  function doRefresh() {
    if (inFlight) {
      return;
    }
    inFlight = true;
    revealPill();
    // Security: window.location.href, the same-document URL, and never
    // a URL read out of the DOM — the fetch target must never be
    // readable from, or influenced by, injected markup.
    //
    // redirect: "manual" — fetch()'s default silently follows a
    // same-origin redirect and reports the final response's status, so
    // an expired session would otherwise land on the login page and
    // report 200. With "manual" a redirect resolves to an opaque
    // response whose ok is false, caught by the non-OK branch below.
    fetch(window.location.href, {
      credentials: "same-origin",
      redirect: "manual",
      headers: {"X-Requested-With": "freshness"}
    }).then(function (response) {
      if (!response.ok) {
        // Non-OK (including the opaque redirect above): do not swap or
        // navigate, leave the stale page visible, and schedule a retry.
        failAndRetry();
        return null;
      }
      return response.text();
    }).then(function (text) {
      if (text === null || typeof text === "undefined") {
        return;
      }
      // DOMParser.parseFromString() builds an inert, detached document
      // with no script execution and no external resource loading, so
      // it is not an HTML-writing sink on the live document.
      var fetchedDoc = new DOMParser().parseFromString(text, "text/html");
      applySwap(fetchedDoc);
      inFlight = false;
      hidePill();
      succeed();
    }).catch(function () {
      // A network-level failure gets the same treatment as a non-OK
      // status: no partial swap, no guess, a backed-off retry.
      failAndRetry();
    });
  }

  // Single interval handle. Starting is a no-op when a handle already
  // exists, so repeated visibility toggles never stack two intervals.
  var intervalHandle = null;

  // The retry ladder's state. A pending retry is a one-shot timer, not
  // a second interval, so each failure schedules exactly one attempt.
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
    // While a retry is pending the ladder owns the schedule and tick()
    // stands down, so the two never both fire. The interval itself is
    // left running as a heartbeat, so a recovered page is never left
    // with no schedule.
    retryHandle = window.setTimeout(function () {
      retryHandle = null;
      if (document.hidden) {
        // A tab that went away mid-ladder is not a failing server; the
        // visibilitychange listener re-arms everything on return.
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
    // Belt and braces: an interval that somehow survives a hide must
    // not fire in a background tab.
    if (document.hidden) {
      stopLoop();
      return;
    }
    if (retryHandle !== null) {
      // A retry is already scheduled; the ladder owns the cadence.
      return;
    }
    if (userIsInteracting()) {
      return;
    }
    if (unsavedEdits()) {
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
      // A hidden tab must cost the server nothing: the retry ladder
      // stands down with the interval.
      stopLoop();
      cancelRetry();
      setState("paused");
      return;
    }
    // Back in view: drop the paused badge and re-arm from the normal
    // cadence, not from wherever a mid-retry ladder had climbed to.
    clearState();
    retryDelayMs = 0;
    startLoop();
    // Catch-up on return, so a tab back after a long hidden stretch
    // does not sit showing minutes-old data for a full interval.
    var elapsed = Date.now() - loadedAtMs;
    if (elapsed > AUTO_REFRESH_INTERVAL_MS && !userIsInteracting() && !unsavedEdits()) {
      doRefresh();
    }
  });

  // A page that loads in a background tab starts stopped.
  if (!document.hidden) {
    startLoop();
  }

  // No DOMContentLoaded wrapper needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing.
})();
