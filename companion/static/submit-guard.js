/*
 * SkyPane companion service — submit-guard.js.
 *
 * T14 (22-AUDIT.md, 22-UI-SPEC.md §2's T14 row, 22-15-PLAN.md Task 3).
 *
 * The audit found exactly one double-submission guard in the whole app:
 * poll-cooldown.js's, on the poll button alone. Save, the Frame strip's
 * quick switches, the rules add/delete forms, the language and theme
 * switches and Disconnect all accepted a second POST from a second
 * click, and a slow response is the normal condition in which a user
 * clicks twice. This file is that guard, once, for every form — one
 * delegated listener rather than a handler per page.
 *
 * Like every other script here it has no build step, no bundler, no
 * framework and no dependency of any kind, and must stay written to an
 * ES5-safe subset (no let/const/arrow functions/template literals) so no
 * transpiler is ever needed to ship it. It is served by companion/
 * app.py's SUBMIT_GUARD_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route, and registered once on the authenticated
 * shell by companion/layout.py's page_shell().
 *
 * --- It is an enhancement, never a boundary ---------------------------
 *
 * With scripts blocked every form submits exactly as it does today. The
 * server's own handlers stay authoritative: this file makes a second
 * click harder, it does not make a second POST safe. Anything that
 * genuinely must not run twice belongs in a server-side lock, which is
 * what companion/app.py's own _POLL_LOCK already is for the one
 * operation that needs it.
 *
 * --- Disabled only. The label does NOT change ------------------------
 *
 * No progress word, in either language, and no spinner. A button that
 * changes what it says while a request is in flight is D3, Phase 23,
 * and this file must not pre-empt it. The appearance is the EXISTING
 * button:disabled treatment in companion/static/style.css (opacity
 * 0.5, not-allowed cursor), already defined and already correctly
 * ordered after button:active. No new disabled styling anywhere.
 *
 * --- Why the disable is DEFERRED, which is the whole subtlety --------
 *
 * The submit control is disabled from a zero-delay timer, not inline in
 * the listener. This is not defensive padding; it is required for
 * correctness. A submit button's own name/value pair is contributed to
 * the form data set by the SUBMITTER, and a disabled control is skipped
 * when that set is constructed — which happens after the submit event's
 * listeners return. Disable the button inline and the payload can lose
 * the very field that says what the user asked for.
 *
 * That is not hypothetical here. companion/layout.py's theme picker and
 * language picker are segmented controls built from
 * <button type="submit" name="ui_theme" value="..."> and
 * <button type="submit" name="ui_lang" value="..."> — the button's
 * name/value IS the whole request. An inline disable would have made
 * every theme and language switch a no-op. By the time a zero-delay
 * timer runs, the submission has already been initiated and the entry
 * list already built.
 *
 * --- How the three existing submit handlers were checked -------------
 *
 * Read before writing, as 22-15-PLAN.md Task 3 requires, and each is
 * unaffected for a stated reason rather than by assumption:
 *
 *   1. dirty-state.js has TWO submit listeners — one on the settings
 *      form, one delegated at document level for [data-quick-switch].
 *      Both do exactly one thing: set suppressGuard = true so the
 *      leave-page dialog does not fire for a navigation the app itself
 *      is performing. Neither reads, writes or cancels anything this
 *      file touches, and neither calls preventDefault(). They run to
 *      completion before this file's timer fires, so ordering between
 *      them is not merely safe, it is fixed.
 *   2. The Frame strip's quick switches are ordinary forms that navigate
 *      (companion/layout.py's frame_strip_html()). Disabling their
 *      button after the navigation has started changes nothing about
 *      the navigation; the page is replaced either way.
 *   3. poll-cooldown.js owns the poll button and ALREADY disables it on
 *      submit, plus runs a server-seeded countdown that re-enables it.
 *      This file therefore skips it outright rather than double-
 *      disabling it or, worse, re-enabling something that script
 *      deliberately left disabled. It is identified by its own
 *      data-submit-pending attribute — a semantic handshake that script
 *      already relies on, never a presentation class a CSS change could
 *      rename out from under this one.
 *
 * Standing constraint this file must never violate: no HTML-writing
 * sink of any kind, and no dynamic evaluation — the same ban list its
 * sibling scripts carry, enforced for this file by name in
 * companion/test_companion_app.py. It creates no markup at all: it
 * writes exactly one property, disabled, on exactly one element per
 * submit, and nothing else.
 *
 * This script is served to every authenticated page (a single cached
 * static asset, not re-emitted per page). A page with no form at all is
 * covered by the listener never firing, which is the project's
 * established no-op-via-guard convention.
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
  // direct answer where the browser provides it; the fallback walks the
  // form's own elements collection, which includes controls attached
  // from OUTSIDE the form through the form= attribute — the cross-DOM
  // idiom the save bar and the Notifications test button both use, so a
  // narrower query over the form's descendants would miss them.
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
      // Another listener may have cancelled the submission after this
      // one ran — the leave-page dialog is one real way that happens.
      // A form that is not going anywhere must keep a usable button.
      if (evt.defaultPrevented) {
        return;
      }
      control.disabled = true;
      disabledControls.push(control);
    }, 0);
  });

  // A page restored from the back/forward cache comes back with the DOM
  // exactly as it was left — including any control this file disabled on
  // the way out. Without this, navigating back after a save would land
  // on a form whose only button is dead, with nothing to explain it.
  // Only controls this file disabled are restored, so a button the
  // server or poll-cooldown.js deliberately disabled stays that way.
  window.addEventListener("pageshow", function (evt) {
    if (!evt.persisted) {
      return;
    }
    for (var i = 0; i < disabledControls.length; i++) {
      disabledControls[i].disabled = false;
    }
    disabledControls = [];
  });

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later. The listener is on document, which exists regardless.
})();
