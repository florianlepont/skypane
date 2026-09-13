/*
 * SkyPane companion service — nav-dropdown.js.
 *
 * This is the project's second JavaScript file, and — as of this phase
 * (06.6.1) — the last one. Like companion/static/battery-trend.js before
 * it, it has no build step, no bundler, no framework and no dependency of
 * any kind. It is served by companion/app.py's NAV_SCRIPT_ROUTE,
 * mirroring the existing /static/style.css and /static/battery-trend.js
 * routes, and must stay written to an ES5-safe subset (no let/const/arrow
 * functions/template literals) so no transpiler is ever needed to ship
 * it.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state.
 *
 * This file reads and writes attributes and class names only — it never
 * touches element content and never writes markup of any kind. Because no
 * HTML-producing DOM sink exists here, no escaping function is needed,
 * for the same reason battery-trend.js's own header states.
 */
(function () {
  "use strict";

  // Progressive-enhancement marker (UXA-02/UXA-12's joint fix). This must
  // run unconditionally, before any dropdown-specific lookup below and
  // even on a page whose header has no dropdown at all — style.css's
  // .js .mobile-nav clipping rule (and any other .js-scoped rule a
  // future page adds) must never be left permanently un-resolved just
  // because this particular page has no toggle/panel pair to find.
  document.documentElement.className += " js";

  // This script is served to every page on the site (a single cached
  // static asset, not re-emitted per page). This early return is
  // load-bearing, not defensive noise, matching battery-trend.js's own
  // documented reasoning: the login/404/preview-error page_shell() calls
  // render no dropdown at all (no request ctx to draw one from), so this
  // file must do nothing on a page whose header has not rendered one.
  var toggle = document.getElementById("site-nav-toggle");
  var panel = document.getElementById("mobile-nav");
  if (!toggle || !panel) {
    return;
  }

  // Mirrors companion/layout.py's MOBILE_NAV_OPEN_CLASS literal — the
  // three-file DOM contract guard (06.6.1-05 Task 3) reads this file from
  // disk and asserts that constant's value appears here.
  var OPEN_CLASS = "mobile-nav--open";

  var reduceMotion = false;
  if (window.matchMedia) {
    reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // The one property the collapse actually animates, and the one this
  // file's transitionend handler below is allowed to act on. Mirrors
  // the transition shorthand on companion/static/style.css's own
  // .js-scoped .mobile-nav clipping rule.
  var COLLAPSE_PROPERTY = "max-height";

  // T5 (22-14-PLAN.md Task 2), half one of two. Whether a collapse will
  // really produce a transitionend event at all.
  //
  // The close path below used to register a once-only transitionend
  // listener unconditionally and rely on it to re-apply the hidden
  // property. When no transition runs — the stylesheet's own
  // prefers-reduced-motion override, a UA or extension that disables
  // transitions, a panel whose computed max-height did not actually
  // change — that event never fires and the panel stays in the
  // accessibility tree and the tab order with aria-expanded="false",
  // which is precisely the divergence aria-expanded-as-single-source-of-
  // truth exists to prevent.
  //
  // Answered by READING the computed style rather than by starting a
  // fallback timer: this file's header states, as a standing constraint
  // and not merely a description, that it introduces no timer. A
  // computed-style read is synchronous and exact.
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
      // The duration list is shorter than the property list when the
      // author wrote one duration for several properties; CSS repeats
      // it, so index modulo its length is the real pairing. A missing
      // entry parses to NaN, and NaN is not greater than zero, so no
      // default string is needed (and none is written here: a bare
      // string default would read to companion/test_i18n.py's JS
      // fallback-literal scanner as an untranslated user-facing word).
      if (parseFloat(durations[i % durations.length]) > 0) {
        return true;
      }
    }
    return false;
  }

  // T5, half two of two: the listener filters on its OWN target and on
  // the property it cares about. Without both filters, a transition on
  // any descendant — every .mobile-nav__link and every .theme-option in
  // the footer declares one on background-color/border-color/color —
  // bubbles a transitionend to this element and sets panel.hidden while
  // aria-expanded is still "true", hiding an open panel.
  //
  // Registered as a NAMED function rather than a fresh once-only
  // closure: the once option would be spent by the first event that the
  // filter rejects, and a named reference makes addEventListener's own
  // duplicate-registration rule (same type, same listener, same
  // capture) idempotent, so a double close cannot stack listeners.
  function onCollapsed(evt) {
    if (evt.target !== panel || evt.propertyName !== COLLAPSE_PROPERTY) {
      return;
    }
    panel.removeEventListener("transitionend", onCollapsed);
    // Re-read the single source of truth: a close-then-reopen inside the
    // transition window must not be undone by this callback, the same
    // stale-callback guard the open path's requestAnimationFrame
    // callback already applies (WR-01).
    if (!isOpen()) {
      panel.hidden = true;
    }
  }

  // Explicit initial closed state, matching the server-rendered
  // aria-expanded="false" baseline. Without this, the panel would be
  // visually clipped by the new .js .mobile-nav CSS rule but still
  // present in the accessibility tree/tab order until the user's first
  // toggle — reopening exactly the bug this task closes.
  panel.hidden = true;

  function isOpen() {
    // aria-expanded is deliberately the single source of truth for the
    // open state — the CSS open-state class below is derived from it,
    // never the other way round. That is what makes it structurally
    // impossible for the visual state and the announced state to
    // diverge, which is the specific failure this pattern exists to
    // prevent.
    return toggle.getAttribute("aria-expanded") === "true";
  }

  function setOpen(next) {
    toggle.setAttribute("aria-expanded", next ? "true" : "false");
    // battery-trend.js avoided classList because it operated on an
    // SVGElement, where className is an SVGAnimatedString rather than a
    // plain string. This file operates on an HTMLElement, where classList
    // is universally available and unambiguous — a deliberate, reasoned
    // difference from the sibling file, not an inconsistency.
    //
    // hidden and the CSS open-state class both derive from this single
    // function, never set independently elsewhere in this file — that is
    // what keeps the two findings this task closes (UXA-02's tab-order/
    // accessibility-tree removal and UXA-12's no-JS floor) from silently
    // re-diverging.
    if (next) {
      // A hidden element has no box to transition from, so hidden must
      // be cleared before the open class is added.
      panel.hidden = false;
      if (reduceMotion) {
        panel.classList.add(OPEN_CLASS);
      } else {
        window.requestAnimationFrame(function () {
          // Re-check isOpen() before applying the class: a fast
          // setOpen(true) followed by setOpen(false) (both synchronous,
          // before this frame runs) would otherwise allow this stale
          // callback to re-open a panel that has already been told to
          // close, so aria-expanded="false" and the rendered panel
          // state would visibly disagree (WR-01).
          if (isOpen()) {
            panel.classList.add(OPEN_CLASS);
          }
        });
      }
    } else {
      panel.classList.remove(OPEN_CLASS);
      if (reduceMotion || !collapseWillTransition()) {
        // T5: the no-transition path sets hidden SYNCHRONOUSLY. There
        // is no animation to cut short, and waiting for an event that
        // will never arrive is what left hidden and aria-expanded
        // contradicting each other.
        panel.hidden = true;
      } else {
        // Apply hidden only after the collapse transition completes —
        // a hidden element renders nothing at all mid-transition, which
        // would otherwise cut the close animation off instantly.
        panel.addEventListener("transitionend", onCollapsed);
      }
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(!isOpen());
  });

  // Scoped to only act while the dropdown is open, and only for the
  // Escape key: an unconditional global handler would swallow Escape from
  // any future dialog on the page. Returning focus to the toggle is what
  // stops a keyboard user being stranded inside a panel that just
  // collapsed.
  document.addEventListener("keydown", function (evt) {
    if (!isOpen()) {
      return;
    }
    if (evt.key === "Escape") {
      setOpen(false);
      toggle.focus();
    }
  });

  // No touchstart/touchend listeners are registered here: a tap
  // synthesises a click in every mobile browser this project targets, and
  // duplicate handlers risk double-firing — battery-trend.js already
  // documents this exact reasoning; cited here rather than re-derived.

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer attribute,
  // so this file only ever runs after parsing. Do not add one later.
})();
