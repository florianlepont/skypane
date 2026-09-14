/*
 * SkyPane companion service — quick-switch.js.
 *
 * D2 (22-AUDIT.md's dynamism half, 23-07-PLAN.md Task 1/2, CFG-36).
 *
 * Three settings in this app apply instantly rather than through the
 * save bar: the frame's Screen, its Quiet hours, and the Diagnostic LED.
 * Each one ships as a real <form> posting to its own /quick/* route.
 * This file upgrades those forms: the switch flips under the finger,
 * the request goes out over fetch, and the visible state is reconciled
 * with the server afterwards — rolled back and announced if the server
 * did not agree.
 *
 * --- IT IS AN ENHANCEMENT, AND THE FLOOR IS STRUCTURAL ---------------
 *
 * This file creates no control. Every switch it touches is a <form>
 * that already works: companion/layout.py's quick_switch_html() renders
 * the form, the two hidden fields (the state to switch to, and the
 * page to return to) and the button, and companion/app.py's own
 * _handle_quick_toggle() validates
 * and saves. Delete this file and every switch still posts, still
 * saves, and still lands back on its own page with the server's flash.
 *
 * role="switch" and aria-checked are rendered by the SERVER from the
 * saved value, so the accessible state is correct with scripts blocked
 * too. The role is not a promise this file keeps; it is a description of
 * what the button does either way.
 *
 * --- HOW THE TWO EXISTING SUBMIT LISTENERS WERE CHECKED --------------
 *
 * Read before writing, the way submit-guard.js's own header does it,
 * because an intercepted submit changes the premise both of them reason
 * from. This file listens in the CAPTURE phase on document and calls
 * stopPropagation() on the one submit it takes over, so neither of the
 * two runs for it at all. That is deliberate for each:
 *
 *   1. dirty-state.js has a delegated document-level submit listener
 *      that sets its private suppressGuard flag for any form carrying
 *      data-quick-switch, so the leave-page dialog does not fire for a
 *      navigation the app itself is performing. There is now no
 *      navigation: the submission is cancelled. Allowing that listener
 *      to run would disarm the unsaved-edits guard for the rest of the
 *      page's life — and on the Display page the settings form sits
 *      directly under these very switches. dirty-state.js re-arms on the
 *      next real edit (its updateBar() clears the flag whenever the form
 *      is dirty again), but a form that was ALREADY dirty when the
 *      switch was pressed emits no further change event, and the guard
 *      would stay down with nothing to re-arm it. Skipping the listener
 *      is what keeps that case correct, and this file's own harness
 *      check drives exactly it.
 *   2. submit-guard.js disables the submitting control from a
 *      zero-delay timer. It already returns early when the submission
 *      was cancelled (it re-reads defaultPrevented inside that timer),
 *      so it would be a no-op here anyway — but a switch must stay
 *      pressable the moment its own request settles, and a permanently
 *      disabled switch is worse than a double request. The in-flight
 *      guard below is this file's own, and it clears in both terminal
 *      branches rather than on a navigation that never happens.
 *   3. poll-cooldown.js owns one button on one page and never sees a
 *      [data-quick-switch] form.
 *
 * --- THE RACE THIS FILE IS ONE HALF OF ------------------------------
 *
 * companion/static/freshness.js refreshes Home and Display every 45s by
 * swapping regions of the document. A swap landing between the
 * optimistic flip and the server's answer would repaint the switch with
 * the server's OLDER state, and it would bounce back under the user's
 * finger. Plan 23-06 shipped the other half of the fix: a region
 * carrying, or containing, the PENDING_ATTR below is skipped by that
 * swap entirely. Setting that attribute for the life of the request,
 * and clearing it in BOTH terminal branches, is this file's whole share
 * of the contract — nothing else about the refresh loop is this file's
 * business.
 *
 * --- NO USER-FACING COPY LIVES HERE ---------------------------------
 *
 * The two state wordings are both server-rendered and translated, with
 * exactly one of them hidden; flipping the switch swaps which. The one
 * failure sentence is read off <body>, where companion/layout.py's
 * page_shell() renders it translated. The English constant below is the
 * no-attribute fallback and nothing else. A switch therefore cannot
 * drop a French reader back into English the moment it is pressed.
 *
 * Like every other script here it has no build step, no bundler, no
 * framework and no dependency of any kind, and must stay written to an
 * ES5-safe subset (no arrow functions, no block-scoped declarations, no
 * template literals) so no transpiler is ever needed to ship it. It is
 * served by companion/app.py's QUICK_SWITCH_SCRIPT_ROUTE and registered
 * once on the authenticated shell by companion/layout.py's page_shell().
 *
 * Standing constraint this file must never violate: no HTML-writing
 * sink of any kind, and no dynamic evaluation. It writes attributes,
 * one class pair and one textContent, and nothing else. It also takes
 * no navigation: there is no assignment to the document's own URL
 * anywhere in this file, and the only URL it ever fetches is the form's
 * own server-rendered action.
 */
(function () {
  "use strict";

  // The handshake attribute companion/layout.py's quick_switch_html()
  // renders on every switch form. Semantic, never a presentation class —
  // 22-05-PLAN.md Task 3 put it there for dirty-state.js and it is the
  // stable hook for this file too.
  var FORM_ATTR = "data-quick-switch";
  // The switch button itself. Needed separately from the form because
  // the Diagnostic LED's button is attached ACROSS the DOM through a
  // form= attribute (its card is rendered inside the settings form, and
  // a <form> can never nest inside another <form>), so the button is not
  // a descendant of the form it submits.
  var CONTROL_ATTR = "data-quick-control";
  // The cell or card holding one switch: the element whose repaint would
  // undo an optimistic flip, and therefore the element the marker below
  // goes on.
  var REGION_ATTR = "data-quick-region";
  // The region held still while the request is in flight. Must equal
  // companion/layout.py's REFRESH_PENDING_ATTR and the constant of the
  // same name in companion/static/freshness.js; a harness pins all three
  // equal, because a rename on one side alone is a skip that silently
  // never fires.
  var PENDING_ATTR = "data-pending";
  var STATE_ON_ATTR = "data-quick-state-on";
  var STATE_OFF_ATTR = "data-quick-state-off";
  var TOAST_ATTR = "data-quick-toast";
  var FAILED_TEXT_ATTR = "data-quick-failed-text";

  // The value companion/app.py's _wants_no_content() tests the
  // X-Requested-With request header against, by exact equality, to pick
  // a 204 over its 303. A browser form post sends nothing of the sort,
  // which is what keeps the scripts-blocked path byte-identical to the
  // one that shipped.
  var FETCH_HEADER_VALUE = "quick-switch";

  // The one user-facing sentence, and only as a fallback for a page
  // whose <body> carries no translated copy (a bare render in a test).
  // It is the app's own existing generic quick-action failure flash,
  // reused verbatim rather than reworded: no status code, no URL, no
  // server internal, in either language.
  var FAILED_TEXT = "Couldn't change that — please try again.";

  // How long the toast stays. Long enough to read a short sentence twice
  // at an unhurried pace, short enough that it is gone before the next
  // thing the user does. It is a transient announcement, not a banner:
  // the state it reports on is already visible in the switch itself,
  // which has rolled back to the truth by the time this appears.
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
  // the direct answer where the browser provides it; the fallback walks
  // form.elements, which INCLUDES controls attached from outside the
  // form through a form= attribute — the cross-DOM idiom the LED switch
  // uses, so a query over the form's descendants alone would miss it.
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
  // boolean. The flip and the rollback are therefore the SAME operation
  // with a different argument, which is the property that makes a
  // rollback impossible to get half right.
  function applyState(control, region, form, on) {
    control.setAttribute("aria-checked", on ? "true" : "false");
    // The form must always post the OPPOSITE of what is now displayed,
    // or the next press re-asserts the state the switch is already in —
    // including a press made with scripts blocked after this one.
    var stateField = form.elements ? form.elements.state : null;
    if (stateField) {
      // "on"/"off" are the two values companion/app.py validates the
      // state field against, written here rather than held in a named
      // constant: a bare lowercase word in a named JS constant is what
      // this project's own translation scanner reads as untranslated
      // user-facing copy, and these are wire values, not copy.
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
    // The control-state left edge, where the region has one. Asked of
    // the region rather than assumed, because the Frame strip's cells
    // carry it and the Device page's LED card does not.
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
    // textContent, never any markup-writing sink: the string is copy the
    // server translated, and it is written as text.
    toast.textContent = copy || FAILED_TEXT;
    toast.className = "quick-toast is-visible";
    // One region, one timer: a second failure REPLACES the first rather
    // than stacking a second box under it. Clearing the old handle first
    // is what stops an earlier dismissal from cutting a later message
    // short.
    if (toastTimer !== null) {
      window.clearTimeout(toastTimer);
    }
    toastTimer = window.setTimeout(function () {
      toast.className = "quick-toast";
      // Emptied as well as hidden, so the live region does not re-announce
      // a stale sentence if anything else mutates it later.
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
    // No fetch, no interception. The form submits natively and the
    // server's own 303 lands exactly as it does with scripts blocked —
    // which is the correct degrade, not a fallback worth writing.
    if (!window.fetch) {
      return;
    }
    var region = ancestorWith(control, REGION_ATTR);
    if (!region) {
      return;
    }
    evt.preventDefault();
    // See this file's header: the two other document-level submit
    // listeners must not run for a submission that is not happening.
    evt.stopPropagation();
    // The in-flight guard, and the same attribute freshness.js reads.
    // A second press while the first is unanswered is ignored rather
    // than queued: the server is the authority on the result and two
    // requests racing to it would make the final state a coin toss.
    if (region.hasAttribute(PENDING_ATTR)) {
      return;
    }
    var wasOn = control.getAttribute("aria-checked") === "true";
    var nextOn = !wasOn;
    var returnTo = fieldValue(form, "return_to");
    applyState(control, region, form, nextOn);
    region.setAttribute(PENDING_ATTR, "");
    // The form's OWN server-rendered action, never a URL assembled here
    // and never one read from anywhere else in the document: the target
    // of a state-changing POST must be the element's own contract.
    // credentials: "same-origin" carries the session cookie, whose
    // SameSite=Strict is this app's only CSRF control — there is no
    // token anywhere, so every state change stays a same-origin POST.
    // redirect: "manual" makes the 303 a session that expired between
    // page load and press would produce resolve to an opaque response
    // whose status is 0, which the check below treats as the failure it
    // is; without it, fetch would follow that redirect to the login page
    // and report 200.
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
      // 204 and nothing else confirms. A 2xx that is not the negotiated
      // no-content answer, a 4xx/5xx, and the opaque redirect above all
      // fall to the same rollback, because none of them is the server
      // saying it saved.
      if (response.status === 204) {
        region.removeAttribute(PENDING_ATTR);
        return;
      }
      rollBack(control, region, form, wasOn);
    })["catch"](function () {
      // The network branch: offline, DNS, aborted. Identical treatment
      // to a non-OK status, for the identical reason — the server never
      // said it saved, so the switch must not claim it did.
      //
      // Written in bracket form because catch is a reserved word in
      // ES3, and a .then() with no catch at all is 23-RESEARCH.md's
      // Pitfall 5 by shape: the optimistic switch that lies.
      rollBack(control, region, form, wasOn);
    });
  }, true);

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add one
  // later. The listener is on document, which exists regardless, and a
  // page with no switch on it is covered by that listener never matching
  // — the same no-op-via-guard convention every sibling script here
  // follows.
})();
