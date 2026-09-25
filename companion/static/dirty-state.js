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

  var form = document.querySelector("form[data-dirty-form]");
  if (!form) {
    return;
  }

  var bar = document.querySelector("[data-dirty-bar]");
  var countEl = document.querySelector("[data-dirty-count]");
  var cancelBtn = document.querySelector("[data-dirty-cancel]");

  // Quiet hours presets: fills the two time inputs and the enable
  // checkbox client-side, then marks the form dirty via notifyDirty().
  // Placed before the bar guard below so presets keep working even on
  // a page whose save bar failed to initialise.
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
      notifyDirty();
    });
  }

  // Reuses updateBar()/countDifferences() rather than dispatching a
  // synthetic change event. Only calls updateBar() once the bar is
  // confirmed present, so a missing bar degrades to "fields still fill
  // in, no dirty count shown" rather than throwing.
  function notifyDirty() {
    if (bar && countEl) {
      updateBar();
    }
  }

  if (!bar || !countEl) {
    return;
  }

  // The bar is server-rendered visible (the no-JS floor, since there is
  // no separate fallback Save button); hiding it here, before any
  // listener attaches, hands control to the enhanced experience.
  bar.hidden = true;

  // Connector words read once off the dirty-bar element, server-
  // rendered and translated; each fallback literal is used only when
  // its attribute is absent, so the bar can never render empty or
  // untranslated.
  var dirtyChangedSuffix = bar.getAttribute("data-dirty-changed-suffix") || " changed";
  var dirtyAnd = bar.getAttribute("data-dirty-and") || " and ";
  var dirtyListAnd = bar.getAttribute("data-dirty-list-and") || ", and ";
  var dirtyUnsavedSingular = bar.getAttribute("data-dirty-unsaved-singular") || "1 unsaved change";
  var dirtyUnsavedPlural = bar.getAttribute("data-dirty-unsaved-plural") || " unsaved changes";
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
      if (dirty) {
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
    var labels = dirtySectionLabels();
    if (labels.length === 0) {
      // Never-silent fallback: a differing field sits outside every
      // section wrapper, so the bar falls back to a raw-count copy
      // rather than going silent while unsaved edits exist.
      setCountText(count === 1
        ? dirtyUnsavedSingular
        : count + dirtyUnsavedPlural);
      return;
    }
    if (labels.length === 1) {
      setCountText(labels[0] + dirtyChangedSuffix);
      return;
    }
    if (labels.length === 2) {
      setCountText(labels[0] + dirtyAnd + labels[1] + dirtyChangedSuffix);
      return;
    }
    // Three or more: every label but the last joined with ", " (a
    // punctuation mark, not a translatable word — French list-commas
    // read identically), the last one prefixed with the final joiner —
    // UI-SPEC §5.1's table.
    var head = labels.slice(0, labels.length - 1).join(", ");
    setCountText(head + dirtyListAnd + labels[labels.length - 1] + dirtyChangedSuffix);
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

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
