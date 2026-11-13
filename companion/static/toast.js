/*
 * SkyPane companion service — toast.js.
 *
 * Enhances the server-rendered toasts (companion/ui_components.py's
 * toast_html()). Everything here is optional: with scripts blocked a
 * flash toast stays in flow and its dismiss link reloads the page
 * without the flash.
 *
 * - Dismiss: the toast's own dismiss control (a link or a button)
 *   removes it in place; Escape does the same while focus is inside it.
 * - Auto-hide: only a toast the server marked data-toast-autohide
 *   (success, info and pending; pending carries the value "long" for the
 *   longer dwell). Warning and error toasts are never marked, so they
 *   stay until dismissed. The timer pauses while the
 *   pointer is over the toast, while focus is inside it and while the
 *   document is hidden, and resumes with the time that was left.
 * - Swipe: a floating toast (the flash and live regions) follows a sideways
 *   drag and is dismissed by one past 80px or a quick flick; a shorter drag
 *   springs back. The auto-hide timer and its hairline pause while the
 *   pointer is down. Its own dismiss control and action keep working.
 * - Never moves focus to a toast; announcement is the server-rendered
 *   role="status"/role="alert" alone. Focus only moves (to <main>) when
 *   it was inside a toast that is being removed, so it is never lost.
 *
 * No build step, ES5-safe subset. Served by companion/app.py's
 * TOAST_SCRIPT_ROUTE. No HTML-writing sink.
 */
(function () {
  "use strict";

  // Must equal companion/ui_components.py's TOAST_ATTR,
  // TOAST_AUTOHIDE_ATTR and TOAST_DISMISS_ATTR.
  var TOAST_ATTR = "data-toast";
  var AUTOHIDE_ATTR = "data-toast-autohide";
  var DISMISS_ATTR = "data-toast-dismiss";
  // Set once the timer runs, so the hairline only shows (and only starts
  // its CSS animation) when a hide is really scheduled.
  var ARMED_ATTR = "data-toast-armed";
  var PAUSED_CLASS = "is-paused";
  // The attribute value that selects the long dwell.
  var LONG_VALUE = "long";
  // The stylesheet's own dwell tokens, so the hairline and the timer
  // share one number.
  var DWELL_PROPERTY = "--motion-toast-dwell";
  var DWELL_LONG_PROPERTY = "--motion-toast-dwell-long";
  // Fallbacks only, for a stylesheet that failed to load.
  var FALLBACK_DWELL_MS = 6000;
  var FALLBACK_DWELL_LONG_MS = 12000;
  var MAIN_ID = "main-content";

  function closestToast(node) {
    while (node && node.getAttribute) {
      if (node.hasAttribute(TOAST_ATTR)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  function dwellMs(toast) {
    var isLong = toast.getAttribute(AUTOHIDE_ATTR) === LONG_VALUE;
    var property = isLong ? DWELL_LONG_PROPERTY : DWELL_PROPERTY;
    var raw = "";
    if (window.getComputedStyle) {
      raw = window.getComputedStyle(document.documentElement)
        .getPropertyValue(property);
    }
    var match = /^\s*(\d+(?:\.\d+)?)(ms|s)\s*$/.exec(raw || "");
    if (!match) {
      return isLong ? FALLBACK_DWELL_LONG_MS : FALLBACK_DWELL_MS;
    }
    var value = parseFloat(match[1]);
    return match[2] === "s" ? value * 1000 : value;
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) {
      return;
    }
    if (toast._skypaneTimer) {
      toast._skypaneTimer.stop();
    }
    var hadFocus = toast.contains(document.activeElement);
    toast.parentNode.removeChild(toast);
    if (hadFocus) {
      var main = document.getElementById(MAIN_ID);
      if (main && main.focus) {
        main.focus();
      }
    }
  }

  // One pausable countdown per auto-hiding toast. The reasons map holds every
  // active pause cause; the countdown runs only while it is empty.
  function Timer(toast, totalMs) {
    this.toast = toast;
    this.remaining = totalMs;
    this.handle = null;
    this.startedAt = 0;
    this.reasons = {};
  }

  Timer.prototype.paused = function () {
    for (var key in this.reasons) {
      if (this.reasons.hasOwnProperty(key) && this.reasons[key]) {
        return true;
      }
    }
    return false;
  };

  Timer.prototype.run = function () {
    var self = this;
    if (this.handle !== null || this.paused()) {
      return;
    }
    this.toast.classList.remove(PAUSED_CLASS);
    this.startedAt = new Date().getTime();
    this.handle = window.setTimeout(function () {
      self.handle = null;
      removeToast(self.toast);
    }, Math.max(this.remaining, 0));
  };

  Timer.prototype.hold = function () {
    if (this.handle !== null) {
      window.clearTimeout(this.handle);
      this.handle = null;
      this.remaining -= new Date().getTime() - this.startedAt;
    }
    this.toast.classList.add(PAUSED_CLASS);
  };

  Timer.prototype.set = function (reason, active) {
    this.reasons[reason] = active;
    if (this.paused()) {
      this.hold();
    } else {
      this.run();
    }
  };

  Timer.prototype.stop = function () {
    if (this.handle !== null) {
      window.clearTimeout(this.handle);
      this.handle = null;
    }
  };

  var timers = [];

  function armAutohide(toast) {
    var timer = new Timer(toast, dwellMs(toast));
    toast._skypaneTimer = timer;
    timers.push(timer);
    toast.setAttribute(ARMED_ATTR, "");
    timer.reasons.hidden = document.hidden === true;
    toast.addEventListener("mouseenter", function () {
      timer.set("hover", true);
    });
    toast.addEventListener("mouseleave", function () {
      timer.set("hover", false);
    });
    toast.addEventListener("focusin", function () {
      timer.set("focus", true);
    });
    toast.addEventListener("focusout", function (evt) {
      if (!evt.relatedTarget || !toast.contains(evt.relatedTarget)) {
        timer.set("focus", false);
      }
    });
    if (timer.paused()) {
      timer.hold();
    } else {
      timer.run();
    }
  }

  document.addEventListener("visibilitychange", function () {
    for (var i = 0; i < timers.length; i++) {
      if (timers[i].toast.parentNode) {
        timers[i].set("hidden", document.hidden === true);
      }
    }
  });

  // Delegated, so a toast cloned in later (quick-switch.js's failure
  // toast) is dismissable too.
  document.addEventListener("click", function (evt) {
    var node = evt.target;
    while (node && node.getAttribute && !node.hasAttribute(DISMISS_ATTR)) {
      node = node.parentNode;
    }
    if (!node || !node.getAttribute) {
      return;
    }
    var toast = closestToast(node);
    if (!toast) {
      return;
    }
    evt.preventDefault();
    removeToast(toast);
  });

  document.addEventListener("keydown", function (evt) {
    if (evt.key !== "Escape" && evt.key !== "Esc") {
      return;
    }
    var toast = closestToast(document.activeElement);
    if (toast) {
      removeToast(toast);
    }
  });

  // ---- Swipe to dismiss (floating toasts only).
  var FLOATING_SELECTOR = ".toast-region--flash, .toast-region--live";
  var SWIPE_DISTANCE = 80;
  var SWIPE_VELOCITY = 0.6;
  var SWIPE_FALLBACK_MS = 500;
  var CONTROL_SELECTOR = "a, button, input, select, textarea, summary";
  var swipe = null;

  function inFloatingRegion(toast) {
    var el = toast.parentNode;
    while (el && el.classList) {
      if (el.matches(FLOATING_SELECTOR)) {
        return true;
      }
      el = el.parentNode;
    }
    return false;
  }

  function onControl(node, toast) {
    while (node && node !== toast && node.nodeType === 1) {
      if (node.matches(CONTROL_SELECTOR)) {
        return true;
      }
      node = node.parentNode;
    }
    return false;
  }

  function reduced() {
    return !!window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function setSwipeState(toast, name) {
    toast.classList.remove("is-swiping", "is-returning", "is-leaving");
    if (name) {
      toast.classList.add(name);
    }
  }

  function clearSwipe(toast) {
    setSwipeState(toast, "");
    toast.style.transform = "";
    toast.style.opacity = "";
  }

  // Runs done when the toast's transform transition ends, or after a
  // fallback delay; at once under reduced motion.
  function afterTransition(toast, done) {
    if (reduced()) {
      done();
      return;
    }
    var finished = false;
    function finish() {
      if (finished) {
        return;
      }
      finished = true;
      toast.removeEventListener("transitionend", onEnd);
      done();
    }
    function onEnd(evt) {
      if (evt.target === toast && evt.propertyName === "transform") {
        finish();
      }
    }
    toast.addEventListener("transitionend", onEnd);
    window.setTimeout(finish, SWIPE_FALLBACK_MS);
  }

  function setSwipePause(toast, active) {
    if (toast._skypaneTimer) {
      toast._skypaneTimer.set("swipe", active);
    } else if (active) {
      toast.classList.add(PAUSED_CLASS);
    } else {
      toast.classList.remove(PAUSED_CLASS);
    }
  }

  document.addEventListener("pointerdown", function (evt) {
    if (swipe || evt.button > 0 || evt.isPrimary === false) {
      return;
    }
    var toast = closestToast(evt.target);
    if (!toast || !inFloatingRegion(toast) || onControl(evt.target, toast)) {
      return;
    }
    swipe = {
      toast: toast, id: evt.pointerId, startX: evt.clientX, lastX: evt.clientX,
      lastT: evt.timeStamp, velocity: 0, offset: 0
    };
    setSwipeState(toast, "is-swiping");
    // The entrance animation would override the dragged transform.
    toast.style.animation = "none";
    setSwipePause(toast, true);
    try {
      toast.setPointerCapture(evt.pointerId);
    } catch (err) {
      // A pointer that cannot be captured still drives the drag through the
      // events that reach the document.
    }
  });

  document.addEventListener("pointermove", function (evt) {
    if (!swipe || evt.pointerId !== swipe.id) {
      return;
    }
    swipe.offset = evt.clientX - swipe.startX;
    var dt = evt.timeStamp - swipe.lastT;
    if (dt > 0) {
      swipe.velocity = (evt.clientX - swipe.lastX) / dt;
    }
    swipe.lastX = evt.clientX;
    swipe.lastT = evt.timeStamp;
    var fade = Math.max(0.3, 1 - Math.abs(swipe.offset) / 300);
    swipe.toast.style.transform = "translateX(" + Math.round(swipe.offset) + "px)";
    swipe.toast.style.opacity = String(fade);
  });

  function leave(toast, direction) {
    setSwipeState(toast, "is-leaving");
    var width = Math.max(window.innerWidth || 0, toast.offsetWidth);
    toast.style.transform = "translateX(" + direction * width + "px)";
    toast.style.opacity = "0";
    afterTransition(toast, function () {
      removeToast(toast);
    });
  }

  function comeBack(toast) {
    setSwipeState(toast, "is-returning");
    toast.style.transform = "translateX(0px)";
    toast.style.opacity = "1";
    afterTransition(toast, function () {
      if (toast.classList.contains("is-returning")) {
        clearSwipe(toast);
      }
    });
  }

  function endSwipe(evt, cancelled) {
    if (!swipe || evt.pointerId !== swipe.id) {
      return;
    }
    var toast = swipe.toast;
    var offset = swipe.offset;
    var flick = Math.abs(offset) > 0 && swipe.velocity * offset > 0 &&
      Math.abs(swipe.velocity) > SWIPE_VELOCITY;
    swipe = null;
    if (!toast.parentNode) {
      return;
    }
    if (!cancelled && (Math.abs(offset) > SWIPE_DISTANCE || flick)) {
      leave(toast, offset < 0 ? -1 : 1);
    } else {
      setSwipePause(toast, false);
      comeBack(toast);
    }
  }

  document.addEventListener("pointerup", function (evt) {
    endSwipe(evt, false);
  });
  document.addEventListener("pointercancel", function (evt) {
    endSwipe(evt, true);
  });

  var toasts = document.querySelectorAll("[" + AUTOHIDE_ATTR + "]");
  for (var i = 0; i < toasts.length; i++) {
    armAutohide(toasts[i]);
  }

  // quick-switch.js shows a confirmation toast after the page has loaded.
  window.skypaneToasts = { arm: armAutohide };

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
