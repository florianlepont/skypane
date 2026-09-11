/*
 * SkyPane companion service — dirty-state.js.
 *
 * D-03 (06.6.3-CONTEXT.md): watches Config's form for unsaved edits and
 * shows a save/cancel bar while any field differs from the value it had
 * on page load. Like nav-dropdown.js/battery-trend.js before it, this
 * file has no build step, no bundler, no framework and no dependency of
 * any kind, and must stay written to an ES5-safe subset (no let/const/
 * arrow functions/template literals/backticks) so no transpiler is ever
 * needed to ship it. It is served by companion/app.py's
 * DIRTY_STATE_SCRIPT_ROUTE, mirroring the existing /static/style.css
 * route.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state — it only reads/writes form values, attributes, and text
 * content already present in the DOM.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * form[data-dirty-form] at all — today only Config does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns).
 *
 * 06.6.4.1 (D-03/D-04): the bar's copy now names which settings group(s)
 * changed, using the group labels Settings' own page module assigns via
 * data-dirty-section, instead of a raw field-diff count — see
 * dirtySectionLabels() and updateBar() below.
 *
 * SUPERSEDED by 19-10-PLAN.md (D-09/A-27): this paragraph used to say
 * hiding the form's always-rendered bottom Save Settings button was NOT
 * this file's job, because that was instead a .js-gated CSS rule
 * (.js [data-static-save-fallback] { display: none; }) driven by the
 * .js class nav-dropdown.js sets unconditionally on <html>. That was the
 * defect: .js says nothing about whether THIS file ever reached its own
 * initialisation — any hiccup in dirty-state.js (a thrown exception, a
 * markup change that broke a querySelector) still left .js set, so the
 * fallback button hid anyway while the replacement bar never appeared,
 * leaving no way to save settings at all. The new contract: this file
 * adds a marker class to <html>, defined below right after the guard
 * that proves the bar actually exists, and
 * companion/static/style.css's fallback-hide rule is retargeted to key
 * on that marker instead of on .js, so the fallback now hides if and
 * only if a working replacement is actually present.
 *
 * 19-10-PLAN.md (D-10/A-28): a beforeunload listener now warns before a
 * real navigation (Add rule, Delete, Trigger poll, or simply closing the
 * tab) discards unsaved settings edits. It uses one predicate,
 * countDifferences() below - the same one the bar itself uses, reused
 * rather than reimplemented - and is cleared by exactly two legitimate
 * exits: a real form submit, and the Cancel button.
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
  if (!bar || !countEl) {
    return;
  }

  // D-09/A-27: the bar is now proven present — set the marker
  // style.css's fallback-hide rule keys on. Mirrors nav-dropdown.js's
  // own unconditional document.documentElement.className += " js"
  // (its very first statement) rather than classList, matching this
  // codebase's existing convention for writing a class onto <html>.
  document.documentElement.className += " dirty-ready";

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

  // Returns an array of dirty section labels, in document order (making
  // the bar's copy deterministic and independent of which field the user
  // touched first) — one entry per [data-dirty-section] wrapper whose
  // scoped fields differ from the load-time snapshot. Section labels are
  // never hardcoded here: at least one settings group can render zero
  // form controls at all (whenever its registry has exactly one member,
  // there's nothing left to pick), so a hardcoded label list would name
  // a section that structurally cannot change. Re-runs the same
  // per-field comparison countDifferences() performs, scoped to only
  // the fields each wrapper contains().
  function dirtySectionLabels() {
    var current = snapshotValues();
    var wrappers = form.querySelectorAll("[data-dirty-section]");
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

  function updateBar() {
    var count = countDifferences();
    if (count <= 0) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    var labels = dirtySectionLabels();
    if (labels.length === 0) {
      // Never-silent fallback: a differing field sits outside every
      // section wrapper. Falls back to the raw-count copy this file
      // shipped before D-03's section-naming so the bar can never go
      // silent while unsaved edits exist.
      countEl.textContent = count === 1
        ? "1 unsaved change"
        : count + " unsaved changes";
      return;
    }
    if (labels.length === 1) {
      countEl.textContent = labels[0] + " changed";
      return;
    }
    if (labels.length === 2) {
      countEl.textContent = labels[0] + " and " + labels[1] + " changed";
      return;
    }
    // Three or more: every label but the last joined with ", ", the
    // last one prefixed with ", and " — UI-SPEC §5.1's table.
    var head = labels.slice(0, labels.length - 1).join(", ");
    countEl.textContent = head + ", and " + labels[labels.length - 1] + " changed";
  }

  var suppressGuard = false;

  form.addEventListener("change", updateBar);
  form.addEventListener("input", updateBar);

  // D-10/A-28: warn before a real navigation discards unsaved edits.
  // Keyed on countDifferences() - the exact same predicate the bar
  // itself uses, reused rather than reimplemented, so the two can never
  // disagree about whether the form is actually dirty. Both
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

  // Clears the guard on the one legitimate submit path. The bar's own
  // Save button renders OUTSIDE this form and submits it natively via
  // its form="{SETTINGS_FORM_ID}" attribute (see config_page.py's
  // dirty_bar_html, quick task 260901-re6) - so this single submit
  // listener covers BOTH the in-form bottom Save button and the bar's
  // out-of-form Save button. Do not add a second click handler on the
  // bar's Save button for this; there is nothing to hook, it is a plain
  // native submit.
  form.addEventListener("submit", function () {
    suppressGuard = true;
  });

  if (cancelBtn) {
    cancelBtn.addEventListener("click", function () {
      form.reset();
      bar.hidden = true;
      // form.reset() above already restores the load-time snapshot
      // values, so countDifferences() would already report 0 - this is
      // belt-and-braces against a browser whose reset() timing races
      // the unload event, not the primary mechanism.
      suppressGuard = true;
    });
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
