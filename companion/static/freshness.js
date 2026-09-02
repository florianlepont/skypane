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
 * --- The mechanism decision, with the losing option's real advantages
 * --- named ------------------------------------------------------------
 *
 * Two mechanisms were weighed against this codebase. Mechanism (b), a
 * network-fetch-based soft refresh that patches content in place,
 * genuinely wins on two things, and they are real: it can show a pill for the
 * actual duration of the fetch, and it preserves scroll, disclosure and
 * focus state by construction. It loses on four things this specific
 * codebase makes decisive, which is why mechanism (a) — a
 * Page-Visibility-gated location.reload(), implemented below — was
 * chosen instead:
 *   1. companion/pages/health_page.py's health_severity() docstring
 *      claims it is "structurally impossible for the nav dot and the
 *      banner to disagree" — but the nav dot is emitted outside
 *      render()'s own output, by companion/layout.py's page_shell(),
 *      so any in-page patch would leave a stale nav dot beside a
 *      freshly-patched banner. Only a whole-page regeneration keeps
 *      the two in step.
 *   2. companion/static/battery-trend.js and companion/static/
 *      list-filter.js each capture their DOM once inside an IIFE, with
 *      no re-init hook and no MutationObserver — replacing either
 *      region under a patch would leave a permanently dead chart (no
 *      hover, no tap, no arrow keys) or a permanently dead filter (and
 *      would additionally discard the user's in-progress filter
 *      query), a silent regression worse than a stale view.
 *   3. A patch needs an HTML-writing DOM sink and a network-call sink —
 *      the whole markup-writing/document-mutation/network-request
 *      family this repo's own forbidden-sink guards already ban
 *      (test_config_page.py's _FORBIDDEN_SCRIPT_SINKS, and the
 *      nav-dropdown.js/panel-lookup.js guards in
 *      test_companion_app.py) — mechanism (b) means writing a
 *      repo-first exception to a discipline that is currently absolute.
 *      (Deliberately not spelling those sink names here: this file's
 *      own harness check bans them from appearing anywhere in this
 *      file, comments included, so naming them would trip the very
 *      check that explains why they are absent.)
 *   4. Mechanism (b) is roughly 100 lines of new machinery, against
 *      roughly 40 for (a), in a codebase whose every other script is
 *      DOM-toggling only, never fetch-based.
 *
 * --- The accepted costs of (a), named rather than glossed ------------
 *
 * Open disclosures do not survive a reload, and keyboard focus is
 * destroyed by one — both mitigated by the interaction-skip guard
 * below, which suppresses a tick entirely rather than trying to restore
 * state afterwards. Browsers restore scroll position on a reload
 * through session-history scroll restoration, unlike a fresh
 * navigation — recorded here as the expectation a live-browser pass
 * must confirm per browser, not asserted as an established fact. And
 * the one cost nothing here mitigates: a reload that fires while a
 * screen-reader user is reading, with focus on the document body,
 * returns their virtual cursor to the top of the document — the
 * interaction-skip guard below cannot detect that state. The lever if
 * this bites is AUTO_REFRESH_INTERVAL_MS below, not an announcement,
 * and a live screen-reader pass is named in this task's SUMMARY.
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
  // tab, and exactly zero from a backgrounded or closed one — the number
  // D-12 was written to protect.
  var AUTO_REFRESH_INTERVAL_MS = 45000;

  // Small and load-bearing, not cosmetic: revealing the pill and calling
  // reload() synchronously can begin navigation before the reveal is
  // ever painted, so without this deferral the pill may never appear at
  // all. What this delivers is honest about its own limits: a
  // pre-navigation indicator, not a fetch-duration indicator — the old
  // document stays painted for the length of the request, so on a fast
  // local response the pill's total visible time is short. The
  // dwell-time version (a pill visible for the actual duration of a
  // fetch) is mechanism (b), not this file.
  var PILL_REVEAL_DELAY_MS = 80;

  var loadedAtEl = document.querySelector("[data-loaded-at]");
  var pill = document.querySelector("[data-refresh-pill]");
  if (!loadedAtEl || !pill) {
    return;
  }

  var raw = loadedAtEl.getAttribute("data-loaded-at");
  if (!raw) {
    return;
  }

  // This file has no access to companion/layout.py's parse_iso() — it
  // must do its own defensive parse-or-noop rather than assuming the
  // attribute is always well-formed.
  var parsed = new Date(raw);
  if (isNaN(parsed.getTime())) {
    return;
  }
  var loadedAtMs = parsed.getTime();

  // Interaction check: true when the user is mid-interaction with
  // something a reload would destroy. Its failure mode is silence —
  // nothing errors when it stops matching, the page simply starts
  // reloading out from under a user mid-interaction, and only
  // companion/test_status_pages.py's cross-file DOM-contract check
  // would notice.
  function userIsInteracting() {
    // First: any open disclosure anywhere on the page. A reader with
    // the readings history or Corroboration's "More details" open is
    // reading, and a reload would slam it shut.
    if (document.querySelector("details[open]")) {
      return true;
    }
    // Second: the active element is a form field, a disclosure summary,
    // or a battery-chart hit target — covering a half-typed registry
    // filter query, keyboard disclosure use, and arrow-key traversal of
    // the chart. Read the active element's class through
    // getAttribute("class"), never the property form: an SVG element's
    // className property is an SVGAnimatedString, not a plain string —
    // the same class of reason companion/static/battery-trend.js's own
    // comment gives for preferring getAttribute() over dataset on SVG
    // elements.
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

  function revealPill() {
    pill.hidden = false;
  }

  function doRefresh() {
    revealPill();
    window.setTimeout(function () {
      // The no-argument form only. This is a security property, not a
      // style preference: the navigation target must never be readable
      // from the DOM, so no URL-taking navigation form appears anywhere
      // in this file.
      window.location.reload();
    }, PILL_REVEAL_DELAY_MS);
  }

  // Single interval handle, one null-ish sentinel. Starting is a no-op
  // when a handle already exists — what stops repeated visibility
  // toggles from stacking two or three intervals onto one page, which
  // would show up as multiple reloads per cycle rather than as an
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

  // A page that loads in a background tab starts fully paused.
  if (!document.hidden) {
    startLoop();
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
