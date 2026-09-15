/*
 * SkyPane companion service — dirty-state.js.
 *
 * 27-04-PLAN.md (D-04..D-10, CFG-63): the developer's own words, reviewing
 * the deployed app — "je veux aucun bouton ça sert à rien. Si tu veux une
 * confirmation visuelle, un 'sauvegarde…' et 'sauvegardé' suffit." This
 * file WAS the dirty save bar: it watched Config's form for unsaved edits
 * and showed a save/cancel bar with a running count of changed sections.
 * It is now the settings form's auto-save driver instead — the bar, its
 * count, its Save/Cancel buttons and the copy that named which sections
 * changed are all deleted. What replaces them is the model
 * companion/static/quick-switch.js already shipped for the three
 * role="switch" controls on this same page: optimistic apply (already
 * true here — a text field already shows what the user typed, with no
 * script's help) -> POST by fetch -> 204 and nothing else confirms ->
 * anything else rolls back the save (never the field's own text — see
 * "WHY A REJECTED VALUE IS NOT REVERTED" below) and raises the SAME
 * generic toast quick-switch.js already owns. There is no second save
 * model on this page; this file adopts the one that already existed.
 *
 * NO NEW SCRIPT, NO NEW ROUTE. This file already owned the delegated
 * change/input listeners on the settings form and the region that
 * announced save state (the bar's own [data-dirty-count]) — both are
 * reused rather than re-derived. It still has no build step, no bundler,
 * no framework and no dependency of any kind, and stays written to an
 * ES5-safe subset (no let/const/arrow functions/template literals/
 * backticks) so no transpiler is ever needed to ship it. It is served by
 * companion/app.py's DIRTY_STATE_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * form[data-dirty-form] at all — today only Config does — so the guard
 * below is load-bearing, not defensive noise.
 *
 * --- THE TRIGGER IS change, NOT input (D-04, PROVISIONAL) -------------
 *
 * A keystroke is not a decision; a commit is. change fires on blur for
 * text/number/url fields and immediately for radios, checkboxes, selects
 * and time inputs — exactly "the user has decided". This removes any
 * need for a debounce timer and any question of saving a half-typed URL,
 * and it is what makes the leave-guard below (still armed, D-10) and this
 * driver agree on exactly one definition of "uncommitted".
 *
 * PROVISIONAL, named here so a later plan can revisit it on developer
 * report: the visible cost is that a user who types into the calendar
 * URL field and closes the tab without blurring has not saved — the
 * leave-guard is what protects exactly that case today. The fallback,
 * if this is ever found surprising, is input plus a debounce: a timer,
 * a second tuning constant and a save per keystroke burst, deliberately
 * not chosen here.
 *
 * --- WHY A REJECTED VALUE IS NOT REVERTED ------------------------------
 *
 * The three switches roll a REJECTED FLIP back to what it was — there is
 * nothing else a switch could sensibly show. A text field is different:
 * this app already ships a deliberate design (wake_interval_group()'s own
 * D-07 behaviour) where a rejected submission is echoed BACK into the
 * field with scripts blocked, so the person can see and fix what they
 * typed rather than have it silently vanish. Auto-save keeps that
 * promise: on any non-204 the field keeps the user's own text, the save
 * is not claimed (the status region never says the saved word), and the
 * generic toast fires. Per-field error copy is NOT delivered to this
 * path — companion/app.py's own docstring names why (rendering it would
 * mean parsing returned HTML into the page, an HTML-writing sink this
 * codebase forbids everywhere) and names the alternative for a later
 * phase (a JSON error map on the rejection branch) as explicitly out of
 * this one's scope.
 *
 * --- THE LEAVE-GUARD STAYS (D-10) --------------------------------------
 *
 * The developer's own binding answer, 2026-09-15: with change-triggered
 * saves, an edit that has never fired change — a calendar URL pasted and
 * the tab closed without leaving the field — is exactly the case a
 * leave-guard exists for. It is unchanged in mechanism from before this
 * plan: still keyed on countDifferences() below, still a plain leave
 * listener with no custom message (every modern browser supplies its
 * own). What changed is WHEN the snapshot this predicate compares
 * against advances: every successful beginSave() call
 * advances it BEFORE the fetch resolves (the same instant the status
 * region starts saying the in-flight word), so the guard disarms the
 * moment a save is under way and re-arms itself, via the identical
 * revert, if that save turns out to have failed (see beginSave() below).
 * "Annuler" is retired alongside the bar (D-10's other half) — it only
 * ever meant something against a pending, uncommitted edit the Save
 * button hadn't sent yet, and there is no longer such a state to cancel.
 *
 * --- WHAT THIS FILE DOES NOT TOUCH --------------------------------------
 *
 * companion/static/submit-guard.js (the double-submit guard for every
 * form on the site) and companion/static/confirm-submit.js (the
 * destructive-action confirm, today the calendar disconnect) are NOT
 * leave-guards and are NOT touched here — D-10 asks specifically that the
 * two halves it separates (the beforeunload leave-guard and the
 * "Annuler" cancel handler) both live and are both retired inside THIS
 * file alone, and they did.
 */
(function () {
  "use strict";

  var form = document.querySelector("form[data-dirty-form]");
  if (!form) {
    return;
  }

  // D-14/S-04: Quiet hours presets. Fills the two time inputs and the
  // enable checkbox client-side, then commits the same way any other
  // field's own change event would — a preset press is as much a
  // decision as a manual edit is. Placed here, BEFORE the [data-save-
  // status] guard immediately below, so the presets keep working even on
  // a page whose status region failed to render — matching this file's
  // own top guard's reasoning. This script is served to every page on
  // the site; most pages render no [data-quiet-preset] buttons at all,
  // so the early return inside the nested function below is load-
  // bearing, matching this file's own top guard.
  (function () {
    var buttons = document.querySelectorAll("[data-quiet-preset]");
    if (!buttons.length) {
      return;
    }
    var i;
    for (i = 0; i < buttons.length; i++) {
      attachPresetClickHandler(buttons[i]);
    }
  })();

  function attachPresetClickHandler(button) {
    button.addEventListener("click", function () {
      var start = button.getAttribute("data-preset-start");
      var end = button.getAttribute("data-preset-end");
      var enabledAttr = button.getAttribute("data-preset-enabled");
      if (start !== null && form.elements["quiet_hours_start"]) {
        form.elements["quiet_hours_start"].value = start;
      }
      if (end !== null && form.elements["quiet_hours_end"]) {
        form.elements["quiet_hours_end"].value = end;
      }
      if (enabledAttr !== null && form.elements["quiet_hours_enabled"]) {
        form.elements["quiet_hours_enabled"].checked = enabledAttr !== "0";
      }
      beginSave();
    });
  }

  // 27-04-PLAN.md Task 3 (CFG-63): the one status region that replaces
  // the retired bar — companion/pages/config_page.py's own
  // _save_status_region_html(), rendered unconditionally alongside
  // data-dirty-form on every scope. A page carrying the form but no
  // region (a markup regression, never expected today) simply gets no
  // visible save feedback — the fetch/save machinery below still runs
  // regardless, matching notifyDirty()'s own pre-27-04 degrade shape
  // ("the fields still fill in, there is just no [feedback] to show").
  var statusRegion = document.querySelector("[data-save-status]");

  // D-06's data-*-attribute-with-an-English-fallback idiom, read once —
  // see companion/pages/config_page.py's own SAVE_STATUS_SAVING_TEXT/
  // SAVE_STATUS_SAVED_TEXT comment for why the fallback literals below
  // are this file's documented degrade and must match those constants
  // byte for byte.
  var savingText = (statusRegion && statusRegion.getAttribute("data-save-status-saving"))
    || "Saving…";
  var savedText = (statusRegion && statusRegion.getAttribute("data-save-status-saved"))
    || "Saved";

  // --- The failure toast, reused rather than reinvented (D-08) ---------
  //
  // Byte-for-byte the same ELEMENT and the same COPY ATTRIBUTE
  // companion/static/quick-switch.js's own announceFailure() reads —
  // never a second toast element, never a second copy attribute. The
  // show/dismiss MECHANISM (the timer, the visible class) is duplicated
  // rather than shared, the same "no import across static/*.js files"
  // convention layout.REFRESH_PENDING_ATTR's own three-file duplication
  // already established for this codebase — there is no build step to
  // share a module through. Each script owns writing to the shared
  // element for the length of ITS OWN transient message; two scripts
  // racing to report a failure inside the same six-second window is an
  // accepted, low-probability edge shared by every multi-script toast
  // owner already on this page (three quick-switch forms plus this one).
  var TOAST_ATTR = "data-quick-toast";
  var FAILED_TEXT_ATTR = "data-quick-failed-text";
  var FAILED_TEXT = "Couldn't change that — please try again.";
  var TOAST_DISMISS_MS = 6000;
  var toastTimer = null;

  function announceFailure() {
    var toast = document.querySelector("[" + TOAST_ATTR + "]");
    if (!toast) {
      return;
    }
    var copy = document.body ? document.body.getAttribute(FAILED_TEXT_ATTR) : null;
    toast.textContent = copy || FAILED_TEXT;
    toast.className = "quick-toast is-visible";
    if (toastTimer !== null) {
      window.clearTimeout(toastTimer);
    }
    toastTimer = window.setTimeout(function () {
      toast.className = "quick-toast";
      toast.textContent = "";
      toastTimer = null;
    }, TOAST_DISMISS_MS);
  }

  // Snapshot every named field's value at load time — unchanged in shape
  // from this file's pre-27-04 own snapshotValues()/countDifferences(),
  // which the leave-guard below still depends on byte for byte. form.
  // elements is a live HTMLFormControlsCollection, re-scanned on every
  // call rather than cached, so a field added or removed later is still
  // handled correctly — including every settings group living OUTSIDE
  // this physical <form> via a form= attribute (several cross-submit
  // this way; see this file's own git history for the B1 defect that
  // made the listener attachment point below document-level rather than
  // form-level for exactly this reason).
  var snapshot = {};

  function snapshotValues() {
    var out = {};
    var els = form.elements;
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (!el.name) {
        continue;
      }
      if (el.type === "checkbox" || el.type === "radio") {
        if (el.checked) {
          out[el.name] = el.value;
        }
      } else {
        out[el.name] = el.value;
      }
    }
    return out;
  }

  snapshot = snapshotValues();

  function countDifferences() {
    var current = snapshotValues();
    var count = 0;
    var name;
    for (name in current) {
      if (Object.prototype.hasOwnProperty.call(current, name)) {
        if (current[name] !== snapshot[name]) {
          count++;
        }
      }
    }
    for (name in snapshot) {
      if (Object.prototype.hasOwnProperty.call(snapshot, name)) {
        if (!(name in current) && snapshot[name] !== undefined) {
          count++;
        }
      }
    }
    return count;
  }

  // 27-04-PLAN.md (deviation, in-scope per Rule 2): companion/static/
  // freshness.js's own tick() used to stand its whole refresh cycle down
  // while the retired bar reported unsaved edits (23-06-PLAN.md Task 1,
  // D1/CFG-35) — gated on the bar's OWN liveness marker AND its own
  // current visibility, B1's lesson that presence is not proof of life.
  // That bar and its own liveness marker class are both gone; a
  // periodic swap landing mid-edit on an uncommitted field is exactly
  // the same hazard this plan's own leave-guard exists for, so the
  // predicate freshness.js reads is exposed here instead — the same
  // small-namespace-object idiom theme-preview.js's own window.
  // SkyPaneLivePreview already established, and this file's own ONE new
  // global. No liveness marker is needed on this side of the seam any
  // more: the function itself is the proof of life, in the one place
  // that can genuinely fail to exist (a page freshness.js runs on but
  // this form is not present) — see this file's own top guard, which is
  // exactly why the object below is defined inside it rather than
  // unconditionally.
  window.SkyPaneDirtyState = {
    hasUncommittedEdits: function () {
      return countDifferences() > 0;
    }
  };

  // D-32's own established idiom (23-09-PLAN.md Task 1's changed-value
  // animation, list-filter.js's and freshness.js's own reuse of it): the
  // stylesheet's EXISTING transform/opacity fade, never a fourth
  // @keyframes block for this plan's own text. Nothing happens unless
  // the sentence genuinely differs, matching this file's pre-27-04
  // setCountText() reasoning against re-announcing identical text to a
  // live region.
  var STATUS_CHANGED_CLASS = "is-fading-in";

  function setStatusText(text) {
    if (!statusRegion) {
      return;
    }
    if (statusRegion.textContent === text) {
      return;
    }
    statusRegion.textContent = text;
    if (statusRegion.classList) {
      statusRegion.classList.remove(STATUS_CHANGED_CLASS);
      void statusRegion.offsetWidth;
      statusRegion.classList.add(STATUS_CHANGED_CLASS);
    }
  }

  // Posts every named field the form currently holds, urlencoded exactly
  // like a native submission of this same <form> would — CFG-36's own
  // hazard (an absent field silently resolving to "leave unchanged" on
  // ONE handler, "clear it" on another) is why this always serializes
  // EVERY field rather than only the one that changed. Excludes any
  // control with no name — the always-rendered fallback Save button
  // (STATIC_SAVE_FALLBACK_ATTR) is exactly that shape and contributes no
  // entry to a native submission either, so this matches native
  // behaviour rather than special-casing it.
  function serializeForm() {
    var els = form.elements;
    var parts = [];
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (!el.name || el.disabled) {
        continue;
      }
      if (el.type === "checkbox" || el.type === "radio") {
        if (!el.checked) {
          continue;
        }
      }
      parts.push(encodeURIComponent(el.name) + "=" + encodeURIComponent(el.value));
    }
    return parts.join("&");
  }

  // --- The save itself, one in flight at a time (T-27-04-C/D) -----------
  //
  // saving is true for the life of one fetch; pendingSave records
  // that a LATER commit arrived while it was in flight. Two booleans and
  // no timer: N rapid commits produce at most one request in flight plus
  // one coalesced follow-up, never N, and the follow-up always
  // serializes the form's CURRENT state at the moment it actually fires
  // — never a captured older body — so an older response can never win
  // over a newer one.
  var saving = false;
  var pendingSave = false;
  var previousSnapshot = null;

  function settleSave() {
    saving = false;
    if (pendingSave) {
      pendingSave = false;
      beginSave();
    }
  }

  function beginSave() {
    if (saving) {
      pendingSave = true;
      return;
    }
    if (countDifferences() === 0) {
      // Nothing left to save — can happen when a coalesced follow-up
      // runs after the field that triggered it was edited back to its
      // last-saved value before the first request even settled.
      return;
    }
    // No fetch, no attempt. A browser this old still has the always-
    // rendered fallback Save button available — .js hides it as a plain
    // script-presence decision (27-03-PLAN.md/CFG-64), which is the
    // deliberate floor this plan builds on rather than reopens; a
    // JS-running, fetch-less browser is the same accepted, out-of-scope
    // gap companion/static/quick-switch.js already ships for its own
    // three switches.
    if (!window.fetch) {
      return;
    }
    saving = true;
    previousSnapshot = snapshot;
    // Optimistic commit — the SAME instant the status region starts
    // saying the in-flight word, and the reason the leave-guard below
    // disarms immediately on change rather than waiting on the
    // network: this is the "apply" half of "optimistic apply -> POST ->
    // 204 confirms -> anything else rolls back", identical in shape to
    // quick-switch.js's own applyState() call before its own fetch.
    snapshot = snapshotValues();
    setStatusText(savingText);
    var body = serializeForm();
    window.fetch(form.action, {
      method: "POST",
      credentials: "same-origin",
      redirect: "manual",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "quick-switch"
      },
      body: body
    }).then(function (response) {
      if (response.status === 204) {
        setStatusText(savedText);
      } else {
        // A validation rejection (200, the user's submission re-rendered
        // with field-level errors, never read here — see this file's
        // own header for why), any 4xx/5xx, or an opaque redirect (a
        // session that expired between page load and this save) — none
        // of them is the server saying it saved. Revert the optimistic
        // snapshot so the leave-guard re-arms for exactly the value that
        // did not land, clear the region so it never claims saved over a
        // failure (the same lie the stale arc this phase exists to fix
        // would be, in a sentence instead), and raise the one toast.
        snapshot = previousSnapshot;
        setStatusText("");
        announceFailure();
      }
      settleSave();
    })["catch"](function () {
      // The network branch: offline, DNS, aborted. Identical treatment
      // to a non-OK status, for the identical reason — the server never
      // said it saved. Written in bracket form because catch is a
      // reserved word in ES3, matching quick-switch.js's own comment.
      snapshot = previousSnapshot;
      setStatusText("");
      announceFailure();
      settleSave();
    });
  }

  // B1/D-01's own lesson, carried forward rather than re-learned: the
  // listeners below are delegated at the DOCUMENT level, filtered to
  // e.target.form === form, because a <form> element never receives a
  // change event from a control that is merely form=-associated with it
  // while living elsewhere in the DOM. Only change drives a save (see
  // this file's own header); input is deliberately NOT listened for
  // any more — there is no bar left for it to update, and a save-on-
  // input would be exactly the keystroke-is-a-decision mistake this
  // plan's own D-04 PROVISIONAL note argues against.
  document.addEventListener("change", function (e) {
    if (e.target && e.target.form === form) {
      beginSave();
    }
  });

  // 22-05-PLAN.md Task 3 (D-04): a Frame strip switch is its own,
  // separate <form> (action="/quick/display" or "/quick/quiet-hours",
  // companion/layout.py's frame_strip_html()) — a browser too old to run
  // quick-switch.js's own fetch path lets that form submit natively,
  // which is a real navigation the leave-guard below would otherwise warn
  // against for a change the strip is itself about to apply. The
  // settings form's own save no longer causes any such navigation (it is
  // a fetch, never a real submit), so this is the ONE remaining reason
  // this file still needs a suppress flag at all — kept narrowly scoped
  // to that one case rather than generalised.
  var suppressGuard = false;
  document.addEventListener("submit", function (e) {
    if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-quick-switch")) {
      suppressGuard = true;
    }
  });

  // D-10 (unchanged mechanism, re-armed by the exact same predicate the
  // save above reverts on failure): warns before a real navigation
  // discards an edit that has never fired change at all. Both
  // evt.preventDefault() and setting evt.returnValue are needed for
  // cross-browser coverage; the browser supplies its own confirmation
  // copy in every modern browser, so never try to set a custom message.
  window.addEventListener("beforeunload", function (evt) {
    if (suppressGuard) {
      return;
    }
    if (countDifferences() > 0) {
      evt.preventDefault();
      evt.returnValue = "";
    }
  });

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
