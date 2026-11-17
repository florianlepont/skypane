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
  // Set on a switch whose change also alters other regions of the page (the
  // Home headline and next-update line): once the server confirms, one
  // freshness.js refresh cycle repaints them in place. Must equal
  // freshness.js's REQUEST_EVENT name below.
  var REFRESH_ATTR = "data-quick-refresh";
  var REFRESH_REQUEST_EVENT = "skypane-refresh-request";
  var ACTION_ON_ATTR = "data-quick-action-on";
  var ACTION_OFF_ATTR = "data-quick-action-off";
  var STATE_ON_ATTR = "data-quick-state-on";
  var STATE_OFF_ATTR = "data-quick-state-off";
  // Must equal companion/ui_base.py's QUICK_TOAST_ATTR and
  // QUICK_TOAST_TEMPLATE_ATTR.
  var TOAST_ATTR = "data-quick-toast";
  var TEMPLATE_ATTR = "data-quick-toast-template";

  // The value companion/app.py's _wants_no_content() tests the
  // X-Requested-With header against to pick a 204 over its 303. A
  // browser form post sends nothing of the sort, keeping the
  // scripts-blocked path unchanged.
  var FETCH_HEADER_VALUE = "quick-switch";
  // Set by the server on the 200 that answers a switch with its confirmation toast.
  var RESULT_HEADER = "X-Quick-Switch-Result";

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
    // A switch whose two states post to two routes (the Users Active
    // switch) names both in server-rendered attributes: the form always
    // posts the action that leaves the state now displayed.
    var nextAction = form.getAttribute(on ? ACTION_ON_ATTR : ACTION_OFF_ATTR);
    if (nextAction) {
      form.setAttribute("action", nextAction);
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
    // Home's rows carry their state in a modifier of their own.
    if (region.classList && region.classList.contains("home-switch")) {
      region.classList.remove(on ? "home-switch--off" : "home-switch--on");
      region.classList.add(on ? "home-switch--on" : "home-switch--off");
    }
  }

  // Clones the server-rendered, translated error toast into the live
  // region, which announces it. An error never hides on its own; its
  // dismiss button is handled by toast.js. One region, one toast: a
  // second failure replaces the first rather than stacking under it.
  function announceFailure() {
    var region = document.querySelector("[" + TOAST_ATTR + "]");
    var template = document.querySelector("[" + TEMPLATE_ATTR + "]");
    if (!region || !template || !template.content) {
      return;
    }
    while (region.firstChild) {
      region.removeChild(region.firstChild);
    }
    region.appendChild(template.content.cloneNode(true));
  }

  function confirmed(region) {
    region.removeAttribute(PENDING_ATTR);
    announceMutation();
    requestRefresh(region);
  }

  // Shows the server-rendered confirmation toast in the live region, parsed
  // as a document (never written as markup into the page) and armed for its
  // auto-hide like the toasts the page arrived with.
  function announceConfirmation(markup) {
    var region = document.querySelector("[" + TOAST_ATTR + "]");
    var toast = new DOMParser().parseFromString(markup, "text/html").querySelector(".toast");
    if (!region || !toast) {
      return;
    }
    while (region.firstChild) {
      region.removeChild(region.firstChild);
    }
    var shown = document.importNode(toast, true);
    region.appendChild(shown);
    if (window.skypaneToasts && shown.hasAttribute("data-toast-autohide")) {
      window.skypaneToasts.arm(shown);
    }
  }

  // Asks freshness.js for one refresh now. A page without that loop simply
  // leaves the dependent regions as they were until its next navigation.
  function requestRefresh(region) {
    if (!region.hasAttribute(REFRESH_ATTR) || !document.createEvent) {
      return;
    }
    var evt = document.createEvent("Event");
    evt.initEvent(REFRESH_REQUEST_EVENT, false, false);
    document.dispatchEvent(evt);
  }

  // Tells prefetch.js the user changed something, so pages it warmed before
  // the change are not served after it.
  function announceMutation() {
    if (!document.createEvent) {
      return;
    }
    var evt = document.createEvent("Event");
    evt.initEvent("skypane-mutated", false, false);
    document.dispatchEvent(evt);
  }

  function rollBack(control, region, form, wasOn, response) {
    applyState(control, region, form, wasOn);
    region.removeAttribute(PENDING_ATTR);
    // A refusal because the session ended gets the session guard's own
    // toast and redirect instead of the generic failure.
    if (response && window.skypaneSession) {
      window.skypaneSession.report(response).then(function (ended) {
        if (!ended) {
          announceFailure();
        }
      });
      return;
    }
    announceFailure();
  }

  // A press on any switch: the ring plays once and, where the browser has a
  // vibration motor, a 10 ms tick. Both are skipped under reduced motion.
  function tick(control) {
    if (window.matchMedia
        && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    control.classList.remove("switch--tick");
    void control.offsetWidth;
    control.classList.add("switch--tick");
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
  }

  document.addEventListener("click", function (evt) {
    var node = evt.target;
    while (node && node !== document) {
      if (node.classList && node.classList.contains("switch")
          && node.getAttribute("role") === "switch") {
        if (!ancestorWith(node, PENDING_ATTR)) {
          tick(node);
        }
        return;
      }
      node = node.parentNode;
    }
  });

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
    var csrf = fieldValue(form, "csrf_token");
    var action = form.action;
    applyState(control, region, form, nextOn);
    region.setAttribute(PENDING_ATTR, "");
    // Security: the form's own server-rendered action, never a URL
    // assembled here. credentials: "same-origin" carries the session
    // cookie, whose SameSite=Strict is this app's only CSRF control.
    // redirect: "manual" makes an expired-session 303 resolve to an
    // opaque response (status 0, treated as failure below) instead of
    // fetch silently following it to the login page and reporting 200.
    window.fetch(action, {
      method: "POST",
      credentials: "same-origin",
      redirect: "manual",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": FETCH_HEADER_VALUE
      },
      body: "state=" + encodeURIComponent(nextOn ? "on" : "off")
          + "&return_to=" + encodeURIComponent(returnTo)
          + (csrf ? "&csrf_token=" + encodeURIComponent(csrf) : "")
    }).then(function (response) {
      // 204, or the 200 that carries the confirmation toast, and nothing
      // else confirms; every other status (including the opaque redirect
      // above) rolls back.
      if (response.status === 204) {
        confirmed(region);
        return;
      }
      if (response.status === 200 && response.headers.get(RESULT_HEADER) === "toast") {
        response.text().then(function (markup) {
          confirmed(region);
          announceConfirmation(markup);
        });
        return;
      }
      rollBack(control, region, form, wasOn, response);
    })["catch"](function () {
      // A network-level failure gets the same treatment as a non-OK
      // status. Bracket form because catch is a reserved word in ES3.
      rollBack(control, region, form, wasOn);
    });
  }, true);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
