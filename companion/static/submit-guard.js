/*
 * SkyPane companion service — submit-guard.js.
 *
 * Disables the submitting control after any form submit, one delegated
 * document-level listener guarding every form, so a slow response
 * cannot be doubled by a second click. No build step, ES5-safe subset.
 * Served by companion/app.py's SUBMIT_GUARD_SCRIPT_ROUTE. An
 * enhancement, never a boundary: with scripts blocked every form
 * submits exactly as today. Disabled only, never a label change (that
 * is dirty-state.js's job); the disable is deferred to a zero-delay
 * timer, since a submit button's name/value is read by the submitter
 * before the event's listeners return, and disabling inline would drop
 * it from the request on companion/layout.py's segmented pickers.
 */
(function () {
  "use strict";

  // poll-cooldown.js's own handshake attribute. A control carrying it
  // manages its own disabled state, including re-enabling itself, and
  // this file must not touch it.
  var COOLDOWN_OWNED_ATTR = "data-submit-pending";

  // Every control this file has disabled, so a bfcache restore can put
  // exactly those back and nothing else.
  var disabledControls = [];

  function isSubmitControl(el) {
    if (!el || !el.tagName) {
      return false;
    }
    var tag = el.tagName.toUpperCase();
    if (tag === "BUTTON") {
      // A <button> with no type attribute defaults to type="submit".
      var type = el.getAttribute("type");
      return type === null || type.toLowerCase() === "submit";
    }
    if (tag === "INPUT") {
      return (el.type || "").toLowerCase() === "submit";
    }
    return false;
  }

  // The control that actually submitted. SubmitEvent.submitter is the
  // direct answer where provided; the fallback walks form.elements,
  // which includes form=-attached controls a descendants-only query
  // would miss.
  function submitterFor(evt, form) {
    if (evt.submitter && isSubmitControl(evt.submitter)) {
      return evt.submitter;
    }
    var elements = form.elements;
    if (!elements) {
      return null;
    }
    for (var i = 0; i < elements.length; i++) {
      if (isSubmitControl(elements[i]) && !elements[i].disabled) {
        return elements[i];
      }
    }
    return null;
  }

  document.addEventListener("submit", function (evt) {
    var form = evt.target;
    if (!form || !form.elements) {
      return;
    }
    var control = submitterFor(evt, form);
    if (!control || control.disabled) {
      return;
    }
    if (control.hasAttribute && control.hasAttribute(COOLDOWN_OWNED_ATTR)) {
      return;
    }
    window.setTimeout(function () {
      // Another listener may have cancelled the submission (the
      // leave-page dialog is one way); a form going nowhere keeps a
      // usable button.
      if (evt.defaultPrevented) {
        return;
      }
      control.disabled = true;
      disabledControls.push(control);
    }, 0);
  });

  // A page restored from bfcache comes back with any control this file
  // disabled still disabled. Only controls this file itself disabled
  // are restored, so a button the server or poll-cooldown.js
  // deliberately disabled stays that way.
  window.addEventListener("pageshow", function (evt) {
    if (!evt.persisted) {
      return;
    }
    for (var i = 0; i < disabledControls.length; i++) {
      disabledControls[i].disabled = false;
    }
    disabledControls = [];
  });

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
