/*
 * SkyPane companion service — relative-time.js.
 *
 * Rewrites the text of every [data-relative] element once a second,
 * from its own datetime attribute, so a rendered "3m ago" keeps
 * counting instead of freezing at render time. Does nothing in a
 * background tab. No build step, ES5-safe subset. Inert on a page
 * with no [data-relative] element. Served by companion/app.py's
 * RELATIVE_TIME_SCRIPT_ROUTE. This file formats, it never judges: it
 * has no verdict vocabulary, and the only write is textContent on an
 * element companion/layout.py's relative_time_html() already filled
 * in, so the no-JS floor is that same server-rendered text.
 *
 * The s/m/h/d bucket boundaries mirror companion/layout.py's
 * _age_bucket(); a cross-file check in companion/test_companion_app.py
 * fails if the two disagree. The wording itself is never mirrored:
 * every visible word is server-rendered onto <body>, already localised,
 * and read back through getAttribute(); the constants below are
 * English no-attribute fallbacks only. "#" marks the quantity's
 * place, not the usual "%s"/"{}", since companion/test_i18n.py's
 * Check 3 scans every French render for a stray format artefact.
 */
(function () {
  "use strict";

  // Once a second. This is a counter of seconds; anything slower and
  // the seconds bucket visibly skips numbers.
  var TICK_MS = 1000;

  // The hook layout.relative_time_html() renders.
  var RELATIVE_ATTR = "data-relative";
  var HOOK_SELECTOR = "[" + RELATIVE_ATTR + "]";

  // Marks an element the server rendered as a countdown. Such an
  // element keeps counting down towards its instant and, once it
  // passes, reads the waiting wording below instead of turning itself
  // into an age. An element without this marker is an age, in both
  // directions, exactly as the server rendered it.
  var COUNTDOWN_ATTR = "data-relative-countdown";

  // companion/static/style.css's one animation consumer; a
  // reduced-motion preference zeroes it via the stylesheet's own
  // global override.
  var BREATHING_CLASS = "is-breathing";

  // The ladder, mirrored from companion/layout.py's _age_bucket():
  // under the first boundary is the seconds bucket, then minutes, then
  // hours, and everything above the third is days.
  var BUCKET_BOUNDARIES = [60, 3600, 86400];

  // The <body> attributes companion/layout.py renders the wordings
  // onto, one per bucket per direction, in bucket order. They live on
  // <body> rather than the element since several of these elements sit
  // inside freshness.js's swap targets, and <body> is never swapped.
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

  // English no-attribute fallbacks, used only when a page was served
  // by an older build that does not carry the real, server-rendered
  // wording. A wording with no "#" in it takes no quantity at all,
  // which is how a language that collapses a whole bucket into one
  // phrase is carried as data rather than a branch in this file.
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

  // A page with nothing to tick registers no listener and no timer at
  // all. Queried once here and never cached beyond this test — see
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

  // One element, one repaint; textContent is the only write. A
  // datetime that is absent or unparseable leaves the element exactly
  // as the server rendered it, the same parse-or-noop discipline
  // freshness.js applies to its own data-loaded-at.
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

  // Looked up fresh on every pass, never cached: several of these
  // elements live inside freshness.js's swap targets, so a cached
  // NodeList would go stale the moment a refresh replaces the region.
  function repaintAll() {
    var nodes = document.querySelectorAll(HOOK_SELECTOR);
    var nowMs = Date.now();
    var i;
    for (i = 0; i < nodes.length; i += 1) {
      repaint(nodes[i], nowMs);
    }
  }

  // Single interval handle; a no-op start when one already exists
  // stops repeated visibility toggles stacking two intervals.
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
    // Belt and braces: an interval that somehow survives a hide must
    // not do work in a background tab.
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

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
