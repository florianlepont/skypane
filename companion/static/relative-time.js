/*
 * SkyPane companion service — relative-time.js.
 *
 * D14 (22-AUDIT.md's dynamism half, 23-05-PLAN.md Task 1, CFG-34).
 *
 * Plan 23-03 gave this app its first <time> elements. Their text is
 * correct at render time and frozen for the rest of the page's life: a
 * page that says "3m ago" goes on saying "3m ago" an hour after anybody
 * stopped looking at it. This file is the one thing that makes them
 * move. It rewrites the text of every [data-relative] element once a
 * second, from that element's own datetime attribute, and it does
 * nothing whatsoever in a background tab.
 *
 * Like every other script here it has no build step, no bundler, no
 * framework and no dependency of any kind, and must stay written to an
 * ES5-safe subset (no arrow functions, no block-scoped declarations, no
 * String interpolation syntax) so no transpiler is ever needed to ship
 * it. It is served by companion/app.py's RELATIVE_TIME_SCRIPT_ROUTE,
 * mirroring the existing /static/style.css route, and registered once
 * on the authenticated shell by companion/layout.py's page_shell() —
 * the thirteenth deferred script on that shell, and the fourteenth
 * static script route in the app.
 *
 * --- One registration, every page ------------------------------------
 *
 * Served everywhere and inert where there is nothing to do, which is
 * this shell's own convention rather than a habit copied without
 * thought: the guard clause below returns before anything is
 * registered on a page carrying no [data-relative] element at all, and
 * the elements it does find are produced by ONE shared builder
 * (layout.relative_time_html(), reached by most callers through
 * layout.concise_timestamp_html()), so a per-page include would have to
 * enumerate a set that no page module actually controls.
 *
 * --- It is an enhancement, never a boundary --------------------------
 *
 * With scripts blocked every one of these elements renders exactly what
 * it renders today: layout.relative_time_html() writes the age into the
 * element server-side, in the reader's own language, and THAT output is
 * the no-JS floor rather than an enhancement over one. This file adds
 * movement to a value that is already there and already correct. There
 * is no control here, nothing to click, and nothing that could render
 * and then do nothing — the failure mode Phase 22's audit found in the
 * save bar is structurally unavailable to a file whose only write is
 * textContent on an element the server already filled in.
 *
 * --- This file computes NO state -------------------------------------
 *
 * companion/static/freshness.js states the rule for the whole app and
 * this file inherits it unchanged: a script here formats, it never
 * judges. What follows measures the distance between an instant and
 * now and picks a wording for it. It does not decide that anything is
 * due, missed, at fault or in need of attention, and it must never
 * acquire a verdict vocabulary — those words belong to frame_state and
 * stay server-rendered. The one state-ish thing here, an expired
 * countdown, is deliberately given the app's NEUTRAL breathing
 * treatment and never a status colour: a wake that has not happened yet
 * is an ordinary condition, and painting it as a fault is the same
 * class of error Phase 22 removed from the frame strip.
 *
 * --- A second implementation of one arithmetic, and why --------------
 *
 * companion/layout.py's _age_bucket() owns the s/m/h/d ladder. It has
 * three boundaries and they are written down there, once. The array
 * below is a SECOND implementation of that same arithmetic, and it is
 * deliberate: ticking a counter in the browser is the only way to make
 * a counter tick, and a round trip to the server every second for a
 * string the browser could compute is not a trade anybody would take.
 *
 * Python remains the definition site. This file mirrors it and must
 * never lead it. A cross-file check in companion/test_companion_app.py
 * reads _age_bucket()'s own source, reads the array below, and fails if
 * the two disagree — so the mirror cannot drift without a named
 * failure. That check is the mitigation for 23-RESEARCH.md's Pitfall 4
 * ("re-deriving arithmetic that has one definition site"), and it
 * exists rather than being promised.
 *
 * The WORDING is not mirrored at all. Every visible word is server
 * rendered onto <body> by companion/layout.py in the reader's own
 * language and read back here through getAttribute(); the constants
 * below are English no-attribute fallbacks and nothing else, the same
 * idiom dirty-state.js, poll-cooldown.js and freshness.js already use,
 * and companion/test_i18n.py's Check 6 requires a French catalogue
 * entry for each one. There is not one word of French in this file and
 * there must never be.
 *
 * --- Why the quantity mark is "#" and not the usual %s ---------------
 *
 * These wordings reach the browser as attribute values on a rendered
 * page, and companion/test_i18n.py's Check 3 scans every French render
 * for a stray "%s"/"%d"/"{}" — the actual failure mode of a mistyped
 * catalogue key. That check is right, and a wording carrying "%s" into
 * the markup would trip it on every page in the app. "#" is the
 * quantity's place in a wording, it is not a Python format artefact,
 * and it cannot be confused for one.
 *
 * --- A hidden tab costs nothing --------------------------------------
 *
 * The interval is stopped on visibilitychange and restarted on return,
 * which is freshness.js's own policy and is adopted here for the same
 * reason and in the same shape. A once-a-second timer on every
 * authenticated page is the one real cost this file carries, and a
 * background tab must not pay it. On return the elements are repainted
 * IMMEDIATELY, before the interval is re-armed: a tab that comes back
 * showing a stale age is exactly the defect this file exists to
 * remove, just one tick further on.
 */
(function () {
  "use strict";

  // Once a second. This is a counter of seconds; anything slower and
  // the seconds bucket visibly skips numbers.
  var TICK_MS = 1000;

  // The hook layout.relative_time_html() renders. Built from the
  // attribute name rather than written out as one selector literal so
  // the name has exactly one site here — and so
  // companion/test_i18n.py's Check 6, which scans every upper-case
  // string constant in this directory and demands a French catalogue
  // entry for it, sees an attribute name (which its own
  // allowlist excludes) rather than a bracketed selector (which its
  // allowlist is documented to exclude but, as written, does not).
  var RELATIVE_ATTR = "data-relative";
  var HOOK_SELECTOR = "[" + RELATIVE_ATTR + "]";

  // Marks an element the server rendered as a COUNTDOWN (see
  // layout.relative_time_html()'s own countdown keyword). Such an
  // element keeps counting down towards its instant and, once that
  // instant passes, reads the waiting wording below instead of turning
  // itself into an age — because a countdown that has run out is still
  // a countdown, and an age would silently change what the element is
  // about. An element without this marker is an age, in both
  // directions, exactly as the server rendered it.
  var COUNTDOWN_ATTR = "data-relative-countdown";

  // companion/static/style.css's one animation consumer. It spends the
  // stylesheet's single opacity cycle at the slow duration token and
  // adds nothing else — no colour, no size, no status treatment. Under
  // a reduced-motion preference the stylesheet's own global override
  // zeroes it for free; there is no per-rule block and there must not
  // be one.
  var BREATHING_CLASS = "is-breathing";

  // --- The ladder, mirrored from companion/layout.py's _age_bucket().
  // Three boundaries, in the same order, with the same meanings:
  // under the first is the seconds bucket, then minutes, then hours,
  // and everything above the third is days. Each of these three
  // numbers appears exactly ONCE in this file, and the cross-file
  // check named in the header compares all three against the Python.
  var BUCKET_BOUNDARIES = [60, 3600, 86400];

  // The <body> attributes companion/layout.py renders the wordings
  // onto, one per bucket per direction, in BUCKET order. They live on
  // <body> and not on the element for the reason
  // layout.REFRESH_PAUSED_ATTR's own comment gives: several of these
  // elements sit inside freshness.js's swap targets, and an attribute
  // there would be replaced out from under this file on every
  // successful refresh. <body> is never swapped.
  var PAST_ATTRS = [
    "data-relative-past-s",
    "data-relative-past-m",
    "data-relative-past-h",
    "data-relative-past-d"
  ];
  var FUTURE_ATTRS = [
    "data-relative-future-s",
    "data-relative-future-m",
    "data-relative-future-h",
    "data-relative-future-d"
  ];
  var WAITING_ATTR = "data-relative-waiting";

  // English no-attribute fallbacks. The real wording is whatever the
  // server put in the attribute above; these exist for the case where
  // a page was served by an older build that does not carry them, and
  // for nothing else. companion/test_i18n.py's Check 6 scans exactly
  // this shape and requires a French catalogue entry for every one.
  //
  // "#" is where the quantity goes. A wording with no "#" in it takes
  // no quantity at all — which is how a language that collapses a
  // whole bucket into one phrase (French does this under a minute, in
  // both directions) is carried as DATA rather than as a branch in
  // this file. There is no language logic here, only substitution.
  var PAST_SECONDS_TEXT = "#s ago";
  var PAST_MINUTES_TEXT = "#m ago";
  var PAST_HOURS_TEXT = "#h ago";
  var PAST_DAYS_TEXT = "#d ago";
  var FUTURE_SECONDS_TEXT = "in #s";
  var FUTURE_MINUTES_TEXT = "in #m";
  var FUTURE_HOURS_TEXT = "in #h";
  var FUTURE_DAYS_TEXT = "in #d";
  var WAITING_TEXT = "waiting…";

  var QUANTITY_MARK = "#";

  var PAST_FALLBACKS = [
    PAST_SECONDS_TEXT, PAST_MINUTES_TEXT, PAST_HOURS_TEXT, PAST_DAYS_TEXT
  ];
  var FUTURE_FALLBACKS = [
    FUTURE_SECONDS_TEXT, FUTURE_MINUTES_TEXT, FUTURE_HOURS_TEXT, FUTURE_DAYS_TEXT
  ];

  // The guard clause every one of this file's twelve siblings carries:
  // a page with nothing to tick registers no listener and no timer at
  // all. Queried once here and NEVER cached beyond this test — see
  // repaintAll() below for why the live lookup has to be per tick.
  if (!document.querySelector(HOOK_SELECTOR)) {
    return;
  }

  // The server's own wording for the named attribute, or the English
  // fallback when it is absent. Read from <body> on every call rather
  // than cached: the cost is a single getAttribute and the benefit is
  // that a language switch mid-session can never leave this file
  // holding the previous language's words.
  function wording(attr, fallback) {
    var host = document.body;
    var value = host ? host.getAttribute(attr) : null;
    return value || fallback;
  }

  // Which bucket a whole number of seconds falls in: 0 seconds,
  // 1 minutes, 2 hours, 3 days. The mirror of _age_bucket()'s three
  // comparisons, in order, reading the boundaries and nothing else.
  function bucketIndex(seconds) {
    var i;
    for (i = 0; i < BUCKET_BOUNDARIES.length; i += 1) {
      if (seconds < BUCKET_BOUNDARIES[i]) {
        return i;
      }
    }
    return BUCKET_BOUNDARIES.length;
  }

  // The quantity that bucket shows. The seconds bucket shows the count
  // itself; every other bucket divides by the boundary BELOW it and
  // rounds down, which is what _age_bucket()'s own floor division
  // does.
  function bucketQuantity(seconds, index) {
    if (index === 0) {
      return seconds;
    }
    return Math.floor(seconds / BUCKET_BOUNDARIES[index - 1]);
  }

  function fill(shape, quantity) {
    if (shape.indexOf(QUANTITY_MARK) === -1) {
      return shape;
    }
    return shape.replace(QUANTITY_MARK, String(quantity));
  }

  function distanceText(seconds, ahead) {
    var index = bucketIndex(seconds);
    var attrs = ahead ? FUTURE_ATTRS : PAST_ATTRS;
    var fallbacks = ahead ? FUTURE_FALLBACKS : PAST_FALLBACKS;
    return fill(wording(attrs[index], fallbacks[index]),
                bucketQuantity(seconds, index));
  }

  function breathe(el, on) {
    if (!el.classList) {
      return;
    }
    if (on) {
      el.classList.add(BREATHING_CLASS);
      return;
    }
    el.classList.remove(BREATHING_CLASS);
  }

  // One element, one repaint. textContent is the only write in this
  // file: it is the only one the standing sink ban permits, and it is
  // also the only one needed — there is no markup in any of these
  // wordings and there must never be.
  //
  // A datetime that is absent or unparseable leaves the element exactly
  // as the server rendered it. That is the same parse-or-noop
  // discipline freshness.js applies to its own data-loaded-at, and it
  // is the right one: the server-rendered text is already correct, so
  // doing nothing is strictly better than guessing.
  function repaint(el, nowMs) {
    var raw = el.getAttribute("datetime");
    if (!raw) {
      return;
    }
    var targetMs = new Date(raw).getTime();
    if (isNaN(targetMs)) {
      return;
    }
    var deltaMs = targetMs - nowMs;
    var counting = el.hasAttribute(COUNTDOWN_ATTR);
    var text;
    if (counting && deltaMs <= 0) {
      text = wording(WAITING_ATTR, WAITING_TEXT);
    } else if (deltaMs > 0) {
      text = distanceText(Math.floor(deltaMs / 1000), true);
    } else {
      text = distanceText(Math.floor(-deltaMs / 1000), false);
    }
    if (counting) {
      breathe(el, deltaMs <= 0);
    }
    if (el.textContent !== text) {
      el.textContent = text;
    }
  }

  // Looked up fresh on every pass, never cached in a module-level
  // variable, for the reason freshness.js's revealPill() gives about
  // its own pill: several of these elements live inside that file's
  // swap targets, so a cached NodeList goes stale (detached from the
  // document) the moment a successful refresh replaces the region
  // holding them, and every repaint after that would silently do
  // nothing at all.
  function repaintAll() {
    var nodes = document.querySelectorAll(HOOK_SELECTOR);
    var nowMs = Date.now();
    var i;
    for (i = 0; i < nodes.length; i += 1) {
      repaint(nodes[i], nowMs);
    }
  }

  // Single interval handle, one null sentinel, a no-op start when a
  // handle already exists — freshness.js's own double-start guard,
  // which is what stops repeated visibility toggles stacking two or
  // three intervals onto one page.
  var intervalHandle = null;

  function startTicking() {
    if (intervalHandle !== null) {
      return;
    }
    intervalHandle = window.setInterval(tick, TICK_MS);
  }

  function stopTicking() {
    if (intervalHandle === null) {
      return;
    }
    window.clearInterval(intervalHandle);
    intervalHandle = null;
  }

  function tick() {
    // Belt and braces, exactly as freshness.js does it: the listener
    // below already stops the interval on hide, but an interval that
    // somehow survives must not do work in a background tab.
    if (document.hidden) {
      stopTicking();
      return;
    }
    repaintAll();
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      stopTicking();
      return;
    }
    // Repaint FIRST, then re-arm. A tab returning after a long hidden
    // stretch would otherwise sit showing an age from before it went
    // away for a whole further tick.
    repaintAll();
    startTicking();
  });

  // A page that loads in a background tab starts stopped and costs
  // nothing until it is looked at.
  if (!document.hidden) {
    startTicking();
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one.
})();
