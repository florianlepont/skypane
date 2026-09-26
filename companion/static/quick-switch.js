/*
 * SkyPane companion service — quick-switch.js.
 *
 * Three settings apply instantly rather than through the save bar: the
 * frame's Screen, its Quiet hours, and the Diagnostic LED. Each ships
 * as a real <form> posting to its own /quick/* route; this file
 * upgrades those forms so the switch flips under the finger over
 * fetch, then reconciles with the server, rolling back and announcing
 * a toast if it disagreed. Every switch still posts and saves with
 * scripts blocked. No build step, ES5-safe subset. Served by
 * companion/app.py's QUICK_SWITCH_SCRIPT_ROUTE. No HTML-writing sink;
 * the only URL it ever fetches is the form's own server-rendered
 * action.
 */
(function () {
  "use strict";

  // The handshake attribute companion/layout.py's quick_switch_html()
  // renders on every switch form.
  var FORM_ATTR = "data-quick-switch";
  // The switch button. Needed separately from the form because the
  // Diagnostic LED's button attaches across the DOM through a form=
  // attribute, so it is not a descendant of the form it submits.
  var CONTROL_ATTR = "data-quick-control";
  // The cell or card holding one switch, where the pending marker goes.
  var REGION_ATTR = "data-quick-region";
  // Held while the request is in flight. Must equal
  // companion/layout.py's REFRESH_PENDING_ATTR and the same-named
  // constant in freshness.js, so a swap never repaints a pending switch.
  var PENDING_ATTR = "data-pending";
  var STATE_ON_ATTR = "data-quick-state-on";
  var STATE_OFF_ATTR = "data-quick-state-off";
  var TOAST_ATTR = "data-quick-toast";
  var FAILED_TEXT_ATTR = "data-quick-failed-text";

  // The value companion/app.py's _wants_no_content() tests the
  // X-Requested-With header against to pick a 204 over its 303. A
  // browser form post sends nothing of the sort, keeping the
  // scripts-blocked path unchanged.
  var FETCH_HEADER_VALUE = "quick-switch";

  // Fallback only, for a page whose <body> carries no translated copy.
  var FAILED_TEXT = "Couldn't change that — please try again.";

  // How long the toast stays: long enough to read twice, short enough
  // to be gone before the next action. A transient announcement, not a
  // banner — the switch itself has already rolled back to the truth.
  var TOAST_DISMISS_MS = 6000;

  var toastTimer = null;

  function ancestorWith(el, attr) {
    var node = el;
    while (node && node.getAttribute) {
      if (node.hasAttribute(attr)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  // The switch button that submitted this form. SubmitEvent.submitter is
  // the direct answer where provided; the fallback walks form.elements,
  // which includes form=-attached controls a descendants-only query
  // would miss.
  function controlFor(evt, form) {
    if (evt.submitter && evt.submitter.hasAttribute
        && evt.submitter.hasAttribute(CONTROL_ATTR)) {
      return evt.submitter;
    }
    var elements = form.elements;
    if (!elements) {
      return null;
    }
    for (var i = 0; i < elements.length; i++) {
      if (elements[i].hasAttribute && elements[i].hasAttribute(CONTROL_ATTR)) {
        return elements[i];
      }
    }
    return null;
  }

  function fieldValue(form, name) {
    var field = form.elements ? form.elements[name] : null;
    return field && typeof field.value === "string" ? field.value : "";
  }

  // The whole visible state of one switch, written from a single
  // boolean, so the flip and the rollback are the same operation with a
  // different argument.
  function applyState(control, region, form, on) {
    control.setAttribute("aria-checked", on ? "true" : "false");
    // The form must always post the opposite of what is now displayed,
    // or the next press (including one made with scripts blocked)
    // re-asserts the state the switch is already in.
    var stateField = form.elements ? form.elements.state : null;
    if (stateField) {
      stateField.value = on ? "off" : "on";
    }
    var onText = region.querySelector("[" + STATE_ON_ATTR + "]");
    var offText = region.querySelector("[" + STATE_OFF_ATTR + "]");
    if (onText) {
      onText.hidden = !on;
    }
    if (offText) {
      offText.hidden = on;
    }
    // Asked of the region rather than assumed: the Frame strip's cells
    // carry this class and the Device page's LED card does not.
    if (region.classList && region.classList.contains("quick-action")) {
      region.classList.remove(on ? "quick-action--off" : "quick-action--on");
      region.classList.add(on ? "quick-action--on" : "quick-action--off");
    }
  }

  function announceFailure() {
    var toast = document.querySelector("[" + TOAST_ATTR + "]");
    if (!toast) {
      return;
    }
    var copy = document.body ? document.body.getAttribute(FAILED_TEXT_ATTR) : null;
    toast.textContent = copy || FAILED_TEXT;
    toast.className = "quick-toast is-visible";
    // One region, one timer: a second failure replaces the first rather
    // than stacking a second box under it.
    if (toastTimer !== null) {
      window.clearTimeout(toastTimer);
    }
    toastTimer = window.setTimeout(function () {
      toast.className = "quick-toast";
      // Emptied as well as hidden, so a later mutation does not
      // re-announce a stale sentence.
      toast.textContent = "";
      toastTimer = null;
    }, TOAST_DISMISS_MS);
  }

  function rollBack(control, region, form, wasOn) {
    applyState(control, region, form, wasOn);
    region.removeAttribute(PENDING_ATTR);
    announceFailure();
  }

  document.addEventListener("submit", function (evt) {
    var form = evt.target;
    if (!form || !form.hasAttribute || !form.hasAttribute(FORM_ATTR)) {
      return;
    }
    var control = controlFor(evt, form);
    if (!control) {
      return;
    }
    // No fetch, no interception: the form submits natively and the
    // server's own 303 lands exactly as it does with scripts blocked.
    if (!window.fetch) {
      return;
    }
    var region = ancestorWith(control, REGION_ATTR);
    if (!region) {
      return;
    }
    evt.preventDefault();
    // Listening in the capture phase and stopping propagation here
    // keeps dirty-state.js's and submit-guard.js's own document-level
    // submit listeners from running for a submission that never
    // happens — otherwise dirty-state.js would disarm the unsaved-edits
    // guard for the rest of the page's life.
    evt.stopPropagation();
    // In-flight guard, the same attribute freshness.js reads. A second
    // press while the first is unanswered is ignored rather than
    // queued, since the server is the sole authority on the result.
    if (region.hasAttribute(PENDING_ATTR)) {
      return;
    }
    var wasOn = control.getAttribute("aria-checked") === "true";
    var nextOn = !wasOn;
    var returnTo = fieldValue(form, "return_to");
    applyState(control, region, form, nextOn);
    region.setAttribute(PENDING_ATTR, "");
    // Security: the form's own server-rendered action, never a URL
    // assembled here. credentials: "same-origin" carries the session
    // cookie, whose SameSite=Strict is this app's only CSRF control.
    // redirect: "manual" makes an expired-session 303 resolve to an
    // opaque response (status 0, treated as failure below) instead of
    // fetch silently following it to the login page and reporting 200.
    window.fetch(form.action, {
      method: "POST",
      credentials: "same-origin",
      redirect: "manual",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": FETCH_HEADER_VALUE
      },
      body: "state=" + encodeURIComponent(nextOn ? "on" : "off")
          + "&return_to=" + encodeURIComponent(returnTo)
    }).then(function (response) {
      // 204 and nothing else confirms; every other status (including
      // the opaque redirect above) rolls back.
      if (response.status === 204) {
        region.removeAttribute(PENDING_ATTR);
        return;
      }
      rollBack(control, region, form, wasOn);
    })["catch"](function () {
      // A network-level failure gets the same treatment as a non-OK
      // status. Bracket form because catch is a reserved word in ES3.
      rollBack(control, region, form, wasOn);
    });
  }, true);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
