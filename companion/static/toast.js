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

  var toasts = document.querySelectorAll("[" + AUTOHIDE_ATTR + "]");
  for (var i = 0; i < toasts.length; i++) {
    armAutohide(toasts[i]);
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
