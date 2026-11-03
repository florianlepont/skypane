/*
 * SkyPane companion service — nav-dropdown.js.
 *
 * Drives the mobile nav toggle/panel (open, close, Escape-to-close,
 * reduced-motion). No build step, ES5-safe subset. Served by
 * companion/app.py's NAV_SCRIPT_ROUTE. Never a network call, a timer,
 * or persistent state; reads and writes attributes and class names
 * only, never element content or markup.
 */
(function () {
  "use strict";

  // Runs unconditionally, even with no dropdown on the page, since
  // style.css's .js-scoped rules must never be left unresolved.
  document.documentElement.className += " js";

  var toggle = document.getElementById("site-nav-toggle");
  var panel = document.getElementById("mobile-nav");
  if (!toggle || !panel) {
    return;
  }

  // Mirrors companion/layout.py's MOBILE_NAV_OPEN_CLASS literal.
  var OPEN_CLASS = "mobile-nav--open";

  var reduceMotion = false;
  if (window.matchMedia) {
    reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // The one property the collapse animates, mirroring the transition
  // shorthand on style.css's own .js-scoped .mobile-nav clipping rule.
  var COLLAPSE_PROPERTY = "max-height";

  // Whether a collapse will really fire transitionend (it will not
  // under reduced motion, or when max-height did not actually change).
  // Answered by reading the computed style synchronously, since this
  // file introduces no timer.
  function collapseWillTransition() {
    if (!window.getComputedStyle) {
      return false;
    }
    var style = window.getComputedStyle(panel);
    var properties = String(style.transitionProperty || "").split(",");
    var durations = String(style.transitionDuration || "").split(",");
    var i;
    var name;
    for (i = 0; i < properties.length; i++) {
      name = properties[i].replace(/^\s+|\s+$/g, "");
      if (name !== COLLAPSE_PROPERTY && name !== "all") {
        continue;
      }
      // The duration list is shorter than the property list when one
      // duration covers several properties; CSS repeats it, so index
      // modulo its length is the real pairing.
      if (parseFloat(durations[i % durations.length]) > 0) {
        return true;
      }
    }
    return false;
  }

  // Filters on its own target and property, so a colour transition on
  // any descendant link cannot bubble a transitionend here and hide an
  // open panel. A named function, not a once-only closure, so a
  // repeated registration is idempotent.
  function onCollapsed(evt) {
    if (evt.target !== panel || evt.propertyName !== COLLAPSE_PROPERTY) {
      return;
    }
    panel.removeEventListener("transitionend", onCollapsed);
    // Re-read the single source of truth: a close-then-reopen inside
    // the transition window must not be undone by this callback.
    if (!isOpen()) {
      panel.hidden = true;
    }
  }

  // Explicit initial closed state, matching the server-rendered
  // aria-expanded="false" baseline, so the panel is not left in the
  // accessibility tree and tab order until the first toggle.
  panel.hidden = true;

  function isOpen() {
    // aria-expanded is deliberately the single source of truth; the CSS
    // open-state class is derived from it, never the other way round,
    // so the visual and announced states cannot diverge.
    return toggle.getAttribute("aria-expanded") === "true";
  }

  function setOpen(next) {
    toggle.setAttribute("aria-expanded", next ? "true" : "false");
    // classList is safe here (an HTMLElement), unlike battery-trend.js's
    // SVGElement, whose className is an SVGAnimatedString.
    if (next) {
      // A hidden element has no box to transition from, so hidden must
      // be cleared before the open class is added.
      panel.hidden = false;
      if (reduceMotion) {
        panel.classList.add(OPEN_CLASS);
      } else {
        window.requestAnimationFrame(function () {
          // Re-check isOpen(): a fast open-then-close, both synchronous
          // before this frame runs, would otherwise allow this stale
          // callback to re-open a panel already told to close.
          if (isOpen()) {
            panel.classList.add(OPEN_CLASS);
          }
        });
      }
    } else {
      panel.classList.remove(OPEN_CLASS);
      if (reduceMotion || !collapseWillTransition()) {
        // No animation to cut short, so hidden is set synchronously
        // rather than waiting for an event that will never arrive.
        panel.hidden = true;
      } else {
        // Apply hidden only after the collapse completes, since a
        // hidden element renders nothing mid-transition.
        panel.addEventListener("transitionend", onCollapsed);
      }
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(!isOpen());
  });

  // Scoped to only act while open, and only for Escape, so an
  // unconditional handler never swallows Escape from a future dialog.
  document.addEventListener("keydown", function (evt) {
    if (!isOpen()) {
      return;
    }
    if (evt.key === "Escape") {
      setOpen(false);
      toggle.focus();
    }
  });

  // No touchstart/touchend listeners: a tap synthesises a click in
  // every mobile browser this project targets, and duplicate handlers
  // risk double-firing.

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
