/*
 * SkyPane companion service — dirty-state.js.
 *
 * Watches Config's form for unsaved edits and shows a save/cancel bar
 * while any field differs from its value at page load. No build step;
 * ES5-safe subset. Inert on a page with no form[data-dirty-form]
 * (today only Config has one). Served by companion/app.py's
 * DIRTY_STATE_SCRIPT_ROUTE. Never a network call or a timer, except
 * one zero-delay deferred callback inside the form's own reset-event
 * handler (see the Cancel handler below), needed because the reset
 * event fires before the browser restores the form's fields.
 */
(function () {
  "use strict";

  // Rendered by the server on a bar that only shows once something changed:
  // while it is there the stylesheet keeps the bar out of the first paint.
  // Must equal companion/ui_save_bar.py's WAIT_ATTR.
  var WAIT_ATTR = "data-dirty-wait";

  var form = document.querySelector("form[data-dirty-form]");

  var bar = document.querySelector("[data-dirty-bar]");
  var countEl = document.querySelector("[data-dirty-count]");
  var cancelBtn = document.querySelector("[data-dirty-cancel]");

  // Quiet hours presets: fills the two time inputs and the enable
  // checkbox client-side, then marks the form dirty via notifyDirty().
  // Placed before the bar guard below so presets keep working even on
  // a page whose save bar failed to initialise. A preset inside its own
  // form (the Quiet hours dialog on Home) fills that form's fields; this
  // part also runs on a page that has no dirty-tracked form.
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
      var target = button.form || form;
      if (!target) {
        return;
      }
      var start = button.getAttribute("data-preset-start");
      var end = button.getAttribute("data-preset-end");
      var enabledAttr = button.getAttribute("data-preset-enabled");
      if (start !== null && target.elements["quiet_hours_start"]) {
        target.elements["quiet_hours_start"].value = start;
      }
      if (end !== null && target.elements["quiet_hours_end"]) {
        target.elements["quiet_hours_end"].value = end;
      }
      // A window preset turns quiet hours on (picking Night after Always
      // active must not save "off"); Always active turns them off.
      if (enabledAttr !== null && target.elements["quiet_hours_enabled"]) {
        target.elements["quiet_hours_enabled"].checked = enabledAttr !== "0";
      } else if (start !== null && target.elements["quiet_hours_enabled"]) {
        target.elements["quiet_hours_enabled"].checked = true;
      }
      syncPresetCards(target);
      notifyDirty();
    });
  }

  // The Quiet hours dialog's preset cards carry their selection in
  // aria-pressed: a window card is selected when quiet hours are on with
  // exactly its hours, "Always active" when they are off. Re-evaluated
  // after a card tap and whenever a field of the form changes.
  // A 12-hour browser's time field is read in 24-hour form by the twin the
  // server draws over it; the twin follows the field's value.
  function syncTimeTwin(field) {
    var twin = field && field.parentNode &&
      field.parentNode.querySelector("[data-normalised-time]");
    if (twin && field.value && twin.textContent !== field.value) {
      twin.textContent = field.value;
    }
  }

  function syncPresetCards(target) {
    var cards = target.querySelectorAll("[data-quiet-card]");
    var enabledField = target.elements["quiet_hours_enabled"];
    var startField = target.elements["quiet_hours_start"];
    var endField = target.elements["quiet_hours_end"];
    var i;
    var card;
    var on;
    var pressed;
    syncTimeTwin(startField);
    syncTimeTwin(endField);
    if (!cards.length || !enabledField || !startField || !endField) {
      return;
    }
    on = enabledField.checked;
    for (i = 0; i < cards.length; i++) {
      card = cards[i];
      if (card.getAttribute("data-preset-enabled") !== null) {
        pressed = !on;
      } else {
        pressed = on &&
          startField.value === card.getAttribute("data-preset-start") &&
          endField.value === card.getAttribute("data-preset-end");
      }
      card.setAttribute("aria-pressed", pressed ? "true" : "false");
    }
  }

  (function () {
    var cards = document.querySelectorAll("[data-quiet-card]");
    var i;
    var cardForm;
    var handler;
    for (i = 0; i < cards.length; i++) {
      cardForm = cards[i].form;
      if (cardForm && !cardForm.hasAttribute("data-quiet-synced")) {
        cardForm.setAttribute("data-quiet-synced", "");
        handler = (function (f) {
          return function () { syncPresetCards(f); };
        })(cardForm);
        cardForm.addEventListener("input", handler);
        cardForm.addEventListener("change", handler);
      }
    }
  })();

  // Reuses updateBar()/countDifferences() rather than dispatching a
  // synthetic change event. Only calls updateBar() once the bar is
  // confirmed present, so a missing bar degrades to "fields still fill
  // in, no dirty count shown" rather than throwing.
  function notifyDirty() {
    if (form && bar && countEl) {
      updateBar();
    }
  }

  // A form page (New special look, Calendar connect, the calendar look) shows
  // its Cancel and Save bar as a fixture and has no dirty bar of its own.
  // Leaving it with values that differ from the ones it loaded with still asks
  // first, keyed on the form the bar's Save button submits; a submit disarms it.
  function guardFormPage() {
    var save = document.querySelector(".dirty-bar[data-dirty-page] .dirty-bar__save[form]") ||
      document.querySelector(".dirty-bar:not([data-dirty-bar]) .dirty-bar__save[form]");
    var pageForm = save ? document.getElementById(save.getAttribute("form")) : null;
    if (!pageForm || pageForm.hasAttribute("data-dirty-form")) {
      return;
    }

    function values() {
      var out = {};
      var els = pageForm.elements;
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

    // Taken once the page has finished loading: the scripts that enhance the
    // form (the look picker swapping its controls in) have settled by then, so
    // only a visitor's own edit differs from it.
    var snapshot = null;
    var leaving = false;

    function takeSnapshot() {
      snapshot = values();
    }

    if (document.readyState === "complete") {
      takeSnapshot();
    } else {
      window.addEventListener("load", takeSnapshot);
    }

    function changed() {
      if (snapshot === null) {
        return false;
      }
      var current = values();
      var name;
      for (name in current) {
        if (Object.prototype.hasOwnProperty.call(current, name) && current[name] !== snapshot[name]) {
          return true;
        }
      }
      for (name in snapshot) {
        if (Object.prototype.hasOwnProperty.call(snapshot, name) && !(name in current)) {
          return true;
        }
      }
      return false;
    }

    // A form page's bar is in the page for a visitor without script; with
    // script it appears once a field differs from the value the page loaded
    // with, and goes again when the edit is undone. A page redrawn with a
    // refused value keeps it from the start.
    var pageBar = document.querySelector(".dirty-bar[data-dirty-page]");
    var reveals = !!pageBar && !pageBar.hasAttribute("data-dirty-keep");
    if (reveals) {
      pageBar.hidden = true;
    }

    function syncPageBar() {
      if (reveals && snapshot !== null) {
        pageBar.hidden = !changed();
      }
    }
    pageForm.addEventListener("input", syncPageBar);
    pageForm.addEventListener("change", syncPageBar);

    pageForm.addEventListener("submit", function () {
      leaving = true;
    });

    window.addEventListener("pageshow", function (evt) {
      if (evt.persisted) {
        leaving = false;
      }
    });

    window.addEventListener("beforeunload", function (evt) {
      if (!leaving && changed()) {
        evt.preventDefault();
        evt.returnValue = "";
      }
    });
  }
  guardFormPage();

  // From here the hidden attribute alone decides whether a bar shows: the
  // server's mark is taken off, so the stylesheet's before-first-paint rule
  // lets go. A bar nothing above took over shows as the server rendered it.
  function release() {
    var bars = document.querySelectorAll(".dirty-bar[" + WAIT_ATTR + "]");
    for (var i = 0; i < bars.length; i++) {
      bars[i].removeAttribute(WAIT_ATTR);
    }
  }

  if (!form || !bar || !countEl) {
    release();
    return;
  }

  // The bar is server-rendered visible (the no-JS floor, since there is
  // no separate fallback Save button); hiding it here, before any
  // listener attaches, hands control to the enhanced experience. A bar
  // carrying data-dirty-carried stays visible: the server rendered it
  // for unsaved values that arrived through the URL.
  var carriedCancelHref = bar.getAttribute("data-dirty-carried");
  var carried = carriedCancelHref !== null;
  bar.hidden = !carried;
  release();

  // Words read once off the bar element, server-rendered and translated;
  // each fallback literal is used only when its attribute is absent, so the
  // bar can never render empty or untranslated. The several-areas message
  // is this lead-in followed by the list of areas.
  var dirtySeveral = bar.getAttribute("data-dirty-several") || "Unsaved changes:";
  var dirtySavingText = bar.getAttribute("data-dirty-saving") || "Saving…";
  var dirtyInitialText = bar.getAttribute("data-dirty-initial-text") || "Unsaved changes";

  // No liveness-marker class is written onto <html>: style.css's
  // clearance rule uses :has(.dirty-bar) instead, which needs no
  // script-written marker and works with scripts blocked too.

  // Snapshot every named field's value at load time. form.elements is a
  // live HTMLFormControlsCollection — re-scanned on every change/input
  // event below rather than cached as a static list, so a field added or
  // removed from the form later (not expected today, but cheap to get
  // right) is still handled correctly.
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
  if (carried) {
    // The stored setting is unknown here, so a carried page is dirty
    // from the start: the mode never equals this marker.
    snapshot["mode"] = "\u0000carried";
  }

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

  // freshness.js's only external consumer, wired to countDifferences().
  window.SkyPaneDirtyState = {
    hasUncommittedEdits: function () {
      return countDifferences() > 0;
    }
  };

  // Returns an array of dirty section labels, in document order, one
  // entry per [data-dirty-section] wrapper whose scoped fields differ
  // from the load-time snapshot. The wrapper lookup queries document,
  // not form: on the Display scope, a [data-dirty-section] group
  // renders as a sibling of the physical form rather than a
  // descendant, and form.querySelectorAll() only searches descendants.
  function dirtySectionLabels() {
    var current = snapshotValues();
    var wrappers = document.querySelectorAll("[data-dirty-section]");
    var labels = [];
    var i, j;
    for (i = 0; i < wrappers.length; i++) {
      var wrapper = wrappers[i];
      var dirty = false;
      var els = form.elements;
      for (j = 0; j < els.length; j++) {
        var el = els[j];
        if (!el.name || !wrapper.contains(el)) {
          continue;
        }
        if (current[el.name] !== snapshot[el.name]) {
          dirty = true;
          break;
        }
      }
      // Several wrappers may share one label (a section split across the
      // page): it is named once.
      if (dirty && labels.indexOf(wrapper.getAttribute("data-dirty-section")) < 0) {
        labels.push(wrapper.getAttribute("data-dirty-section"));
      }
    }
    return labels;
  }

  // The stylesheet's existing changed-value animation class; the bar's
  // entrance is a different motion with its own block.
  var COUNT_CHANGED_CLASS = "is-fading-in";

  // The count's one write site. The bar is role="status", so every
  // write is a potential announcement; updateBar() runs on every change
  // and input event, and most produce the same sentence again, so
  // nothing happens unless the text genuinely differs (a screen reader
  // should not read the same number twice). Text is written before the
  // class, so the displayed value is real at the animation's first
  // frame. The class is removed, its layout read (forcing the removal
  // to take effect), then re-added — reading a layout property, not a
  // timer, is what makes the restart work.
  function setCountText(text) {
    if (countEl.textContent === text) {
      return;
    }
    countEl.textContent = text;
    if (countEl.classList) {
      countEl.classList.remove(COUNT_CHANGED_CLASS);
      void countEl.offsetWidth;
      countEl.classList.add(COUNT_CHANGED_CLASS);
    }
  }

  function updateBar() {
    var count = countDifferences();
    // T1: re-arm the leave-guard the moment a real edit exists again —
    // Cancel (below) is the only place that ever sets suppressGuard to
    // true, and it must not stay true for the rest of the page's life.
    if (count > 0) {
      suppressGuard = false;
    }
    if (count <= 0) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    // One message for every page, naming the areas only
    // when several of them changed.
    // A phone's one-line message is too narrow for the list: the short
    // message stands alone there.
    var labels = dirtySectionLabels();
    var narrow = window.matchMedia && window.matchMedia("(max-width: 959.98px)").matches;
    if (labels.length < 2 || narrow) {
      setCountText(dirtyInitialText);
      return;
    }
    setCountText(dirtySeveral + " " + labels.join(", "));
  }

  var suppressGuard = false;

  // Document-level delegation, filtered to this form's own associated
  // elements via the native .form property, which is authoritative for
  // both real descendants and any form=-attached field living
  // elsewhere in the DOM.
  document.addEventListener("change", function (e) {
    if (e.target && e.target.form === form) {
      updateBar();
    }
  });
  document.addEventListener("input", function (e) {
    if (e.target && e.target.form === form) {
      updateBar();
    }
  });

  // Warns before a real navigation discards unsaved edits, keyed on the
  // same countDifferences() predicate the bar uses. Both
  // preventDefault() and setting returnValue are needed for
  // cross-browser coverage; the browser supplies its own confirmation
  // copy, so never set a custom message.
  window.addEventListener("beforeunload", function (evt) {
    if (suppressGuard) {
      return;
    }
    if (countDifferences() > 0) {
      evt.preventDefault();
      evt.returnValue = "";
    }
  });

  // Clears the guard on the one legitimate submit path. The bar's Save
  // button renders outside this form and submits it natively via its
  // form="settings-form" attribute, so this single listener covers it.
  form.addEventListener("submit", function (evt) {
    suppressGuard = true;
    relabelSubmitter(evt);
  });

  // Relabels the in-flight Save button. Safe to run inline (unlike
  // submit-guard.js, which defers to a zero-delay timer): a submit
  // button's name/value pair is only contributed to the form data set
  // by the submitter when it has a name, and the bar's Save button
  // carries none, so relabelling its text content here displaces
  // nothing. An <input type="submit"> is excluded by the <button>
  // check, since its label is its value and relabelling one would
  // change what is posted. Ordering against submit-guard.js is
  // guaranteed by event propagation: this listener is on the form and
  // runs before submit-guard.js's document-level, timer-deferred one.
  // A submission with no evt.submitter simply gets no relabel.

  // The one control this file has relabelled, so a back/forward-cache
  // restore (which leaves the DOM exactly as left, including a stale
  // in-flight label) can put it back.
  var relabelled = null;

  function relabelSubmitter(evt) {
    var control = evt.submitter;
    if (!control || !control.tagName || control.tagName.toUpperCase() !== "BUTTON") {
      return;
    }
    if (control.getAttribute("name")) {
      return;
    }
    relabelled = { el: control, text: control.textContent };
    control.textContent = dirtySavingText;
  }

  window.addEventListener("pageshow", function (evt) {
    if (!evt.persisted || !relabelled) {
      return;
    }
    relabelled.el.textContent = relabelled.text;
    relabelled = null;
  });

  // A Frame strip switch is its own, separate <form>, so the settings
  // form's own submit listener above never fires for it. Without this,
  // activating a strip switch while the settings form has unsaved edits
  // would raise the leave-page dialog for a change the strip is itself
  // about to apply. Delegated at document level and keyed on a
  // handshake attribute, never a presentation class.
  document.addEventListener("submit", function (e) {
    if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-quick-switch")) {
      suppressGuard = true;
    }
  });

  // Cancel is a native <button type="reset">, so this file never calls
  // the form's own reset() itself — only listens for the reset event
  // and layers enhancements on top. Spec fact: the reset event always
  // fires before the browser restores the form's fields (restoring is
  // the event's default action), so anything synchronous in this
  // handler reads stale, pre-reset values. The native reset() also
  // fires no change/input events, so nothing downstream repaints on
  // its own — hence both repaints below run from a zero-delay deferred
  // callback, the first point at which restored values are readable.
  // Never call preventDefault() here: cancelling the reset's default
  // action would turn Cancel into a silent no-op with scripts on.
  // A click on the reset button also bubbles to value-controls.js's own
  // click-delegated repaint before the reset itself runs, so Cancel
  // harmlessly repaints the quiet-hours dial twice: once too early,
  // once correctly from this deferred tick.
  if (cancelBtn) {
    form.addEventListener("reset", function () {
      bar.hidden = true;
      suppressGuard = true;
      window.setTimeout(function () {
        if (window.SkyPaneLivePreview && window.SkyPaneLivePreview.refresh) {
          window.SkyPaneLivePreview.refresh();
        }
        if (window.SkyPaneValueControls && window.SkyPaneValueControls.repaintAll) {
          window.SkyPaneValueControls.repaintAll();
        }
      }, 0);
    });
  }

  // Page-local navigation (data-detection-nav): the page's own GET
  // navigations carry the live mode, radius and location through the
  // URL, so the leave-guard must not fire for them and a typed value
  // survives the round trip. A restore from the back/forward cache
  // re-arms the guard.
  var NAV_FIELDS = ["mode", "radius_km", "location_id"];

  function liveNavValues() {
    var out = {};
    for (var i = 0; i < NAV_FIELDS.length; i++) {
      var control = form.elements[NAV_FIELDS[i]];
      out[NAV_FIELDS[i]] = control && typeof control.value === "string" ? control.value : "";
    }
    return out;
  }

  function withNavQuery(href, values) {
    var hash = "";
    var at = href.indexOf("#");
    if (at >= 0) {
      hash = href.slice(at);
      href = href.slice(0, at);
    }
    var q = href.indexOf("?");
    var base = q >= 0 ? href.slice(0, q) : href;
    var kept = [];
    if (q >= 0) {
      var parts = href.slice(q + 1).split("&");
      for (var i = 0; i < parts.length; i++) {
        if (parts[i] && NAV_FIELDS.indexOf(parts[i].split("=")[0]) < 0) {
          kept.push(parts[i]);
        }
      }
    }
    for (var j = 0; j < NAV_FIELDS.length; j++) {
      var value = values[NAV_FIELDS[j]];
      if (value) {
        kept.push(NAV_FIELDS[j] + "=" + encodeURIComponent(value));
      }
    }
    return base + (kept.length ? "?" + kept.join("&") : "") + hash;
  }

  document.addEventListener("submit", function (e) {
    var navForm = e.target;
    if (!navForm || !navForm.hasAttribute || !navForm.hasAttribute("data-detection-nav")) {
      return;
    }
    var values = liveNavValues();
    for (var i = 0; i < NAV_FIELDS.length; i++) {
      var name = NAV_FIELDS[i];
      var hidden = navForm.elements[name];
      if (!hidden && values[name]) {
        hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = name;
        navForm.appendChild(hidden);
      }
      if (hidden) {
        hidden.value = values[name];
      }
    }
    suppressGuard = true;
  });

  document.addEventListener("click", function (e) {
    if (e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) {
      return;
    }
    var link = e.target;
    while (link && !(link.hasAttribute && link.hasAttribute("data-detection-nav") &&
        link.getAttribute("href") !== null)) {
      link = link.parentNode;
    }
    if (!link) {
      return;
    }
    link.setAttribute("href", withNavQuery(link.getAttribute("href"), liveNavValues()));
    suppressGuard = true;
  });

  window.addEventListener("pageshow", function (evt) {
    if (evt.persisted) {
      suppressGuard = false;
    }
  });

  // A bar rendered for values carried in the URL counts as one unsaved
  // change and keeps the guard armed; its Cancel returns to the stored
  // setting at the URL the server named, since a native reset would only
  // restore the carried defaults.
  if (carried) {
    updateBar();
    if (cancelBtn && carriedCancelHref) {
      cancelBtn.addEventListener("click", function (evt) {
        evt.preventDefault();
        suppressGuard = true;
        window.location.href = carriedCancelHref;
      });
    }
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
