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
 * Standing constraint: this file must never introduce a network call or
 * any persistent state, and never a timer EXCEPT the one described
 * below — it only reads/writes form values, attributes, and text
 * content already present in the DOM. THE ONE NAMED EXCEPTION: a single
 * zero-delay deferred callback (window's own next-tick primitive,
 * called with a literal 0 delay) inside the form's own reset-event
 * handler (see "THE CANCEL ENHANCEMENT" below), which exists solely
 * because the reset event fires BEFORE the browser restores the
 * form's fields — it is a reset-event side-effect flush, never a poll,
 * never a debounce, never a retry. This file's own pre-27-04 shape
 * permitted exactly one such deferred callback too, then scoped to the
 * toast's own dismissal (deleted with the auto-save interlude below) —
 * "exactly one, narrowly scoped" is this file's own existing
 * convention, not a new liberty.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * form[data-dirty-form] at all — today only Config does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns).
 *
 * --- THE 27-04 AUTO-SAVE INTERLUDE, AND WHY THIS FILE IS NOT THAT
 *     VERSION ANY MORE ------------------------------------------------
 *
 * 27-04-PLAN.md (D-04..D-10, CFG-63) rewrote this file entirely: the bar,
 * its Save/Cancel buttons, its section-naming copy and the leave-guard's
 * disarm-on-commit semantics were all deleted, replaced by a network-
 * request-driven auto-save off the settings form's own change events,
 * reusing quick-switch.js's own optimistic-apply/POST/204/toast-on-
 * failure model. That mechanism WORKED — real Safari Network tab
 * evidence later showed the request landing 204, every field present,
 * the value genuinely persisted after reload (ROADMAP.md's Phase 28
 * addendum has the full account). The developer rejected the auto-save
 * MODEL anyway, having been asked directly and having confirmed twice:
 * they want the bar back, with real Enregistrer/Annuler buttons over a
 * genuine native form POST. 28-08-PLAN.md (CFG-77/CFG-78), 2026-09-16,
 * is that restoration. This file is once again the bar's driver — the
 * paragraphs below document its ORIGINAL, pre-27-04 mechanism as
 * restored, not the network-request-era shape that sat here for one
 * phase in between. Every artifact of that era — the save-initiation/
 * settle/form-serialization helper functions, the saving/pendingSave/
 * previousSnapshot state, the status region and its two words, this
 * file's own copy of the failure-announcement function and the toast
 * constants, and the file's only outbound network call — is deleted
 * outright. This file's ONLY external consumer,
 * window.SkyPaneDirtyState.hasUncommittedEdits() (freshness.js:385),
 * SURVIVES — its own reasoning ("presence is not proof of life") is
 * still correct even though the auto-save that motivated building it
 * that way is gone; it is wired to the restored
 * countDifferences() below, unchanged in shape.
 *
 * --- FIVE DEPARTURES FROM THIS FILE'S OWN PRE-27-04 SHAPE (all
 *     28-08-PLAN.md Task 3, CFG-77/CFG-78) ------------------------------
 *
 * 1. VISIBILITY POLARITY INVERTS. The pre-27-04 bar relied on being
 *    server-rendered hidden (companion/pages/config_page.py). It is
 *    not any more — there is no second, separate fallback Save button
 *    for a no-JS visitor to fall back to any more, so the bar's own
 *    server-rendered visible state IS the no-JS floor now. This file
 *    sets bar.hidden = true explicitly at init, immediately after the
 *    if (!bar || !countEl) return; guard below proves the bar exists
 *    and before any edit can possibly have happened — that single line
 *    is the whole inversion, in code.
 * 2. THE COUNT SPAN STARTS EMPTY, carrying no server-rendered seed
 *    (config_page.py no longer writes DIRTY_BAR_INITIAL_TEXT into
 *    [data-dirty-count] — see that constant's own comment for why a
 *    seeded claim would now be a permanent, role="status"-announced
 *    lie to every scripts-blocked visitor). This file is the span's
 *    ONLY writer, and it writes only inside updateBar(), only once
 *    countDifferences() > 0.
 * 3. NO MARKER CLASS is written onto <html> any more — neither of this
 *    file's own two former liveness-marker classes (the shorter one
 *    proving the script ran, the longer one proving the bar had
 *    actually shown real content at least once). Both existed for
 *    exactly one consumer: style.css's own content-clearance rules,
 *    scoped to the shorter marker so only a page that had proven its
 *    bar live reserved space for it. That premise cannot survive point
 *    1 above:
 *    a scripts-blocked visitor needs the clearance too, and no script
 *    ever runs for them to write the marker. style.css's own restored
 *    clearance (28-08-PLAN.md Task 2) uses :has(.dirty-bar) instead —
 *    true the instant the bar exists in the DOM, no script needed to
 *    prove anything live first — so this file writes NEITHER marker,
 *    and correctly so; do not reintroduce either one by copying an
 *    older commit wholesale.
 * 4. CANCEL IS AN ENHANCEMENT OVER A NATIVE RESET, never a click
 *    handler that performs the reset itself. See "THE CANCEL
 *    ENHANCEMENT" below, at this file's own Cancel wiring, for the full
 *    account — it is the least obvious piece of this restoration and it
 *    gets its own section rather than a paragraph here.
 * 5. THE SEVENTH WORD. DIRTY_BAR_INITIAL_TEXT (config_page.py) is read
 *    here the same getAttribute()-with-a-documented-fallback way the
 *    six connector words are, for parity and because a documented
 *    fallback literal is this file's own established idiom for every
 *    translated word a server-rendered attribute carries — but unlike
 *    the six, no branch of updateBar() below currently spends it (none
 *    of the four copy branches ever say the plain initial-state
 *    sentence). It is read, and its own fallback-literal check passes,
 *    precisely because
 *    reading it costs nothing and keeps the seven-word set uniform;
 *    said here explicitly so a future reader does not go looking for a
 *    dead branch that was silently trimmed.
 *
 * --- WHAT SURVIVES BELOW, RESTORED FROM THIS FILE'S OWN HISTORY -------
 *
 * 06.6.4.1 (D-03/D-04): the bar's copy names which settings group(s)
 * changed, using the group labels Settings' own page module assigns via
 * data-dirty-section, instead of a raw field-diff count — see
 * dirtySectionLabels() and updateBar() below.
 *
 * 19-10-PLAN.md (D-10/A-28): a beforeunload listener warns before a real
 * navigation (Add rule, Delete, Trigger poll, or simply closing the tab)
 * discards unsaved settings edits. It uses one predicate,
 * countDifferences() below — the same one the bar itself uses, reused
 * rather than reimplemented — and is cleared by exactly two legitimate
 * exits: a real form submit, and Cancel.
 *
 * 19-10-PLAN.md (D-14/S-04): three Quiet hours preset buttons
 * (config_page.py's quiet_hours_group()) are also handled here, reading
 * their data-preset-start/data-preset-end/data-preset-enabled
 * attributes and writing into the same form's time inputs and enable
 * checkbox, then reusing notifyDirty()/updateBar() to mark the form
 * dirty — never a synthetic change event.
 *
 * 22-01-PLAN.md Task 2 (D-01/B1, T1, T8): several settings groups (see
 * config_page.py's own DIRTY_SECTION_ATTR wrappers) live OUTSIDE the
 * physical <form id="settings-form">, cross-submitting only via a form=
 * attribute on each control. The change/input listeners below are
 * delegated at the document level, filtered to e.target.form === form —
 * a <form> element never receives a change/input event from a control
 * that is merely form=-associated with it while living elsewhere in the
 * DOM. form.elements was ALREADY correct here (the WHATWG spec builds
 * it from both descendants and any form=-matching element anywhere in
 * the document) — snapshotValues(), countDifferences() and
 * dirtySectionLabels() need no change for this at all.
 *
 * 22-01-PLAN.md Task 3 (D-01/B1): dirtySectionLabels()'s own wrapper
 * lookup queries document, never form — on the Display scope every
 * [data-dirty-section] group renders as a SIBLING of the physical form,
 * exactly like the fields inside them, and form.querySelectorAll()
 * only ever searches descendants.
 *
 * T1: updateBar() resets suppressGuard to false at its own top whenever
 * a real edit exists (countDifferences() > 0), re-arming the leave-guard
 * the moment the next edit is detected after a Cancel — a Cancel must
 * not disarm the guard for the rest of the page's life.
 *
 * D-06 (20-11-PLAN.md Task 3): six of the bar's own connector words are
 * read once from the dirty-bar element itself via data-* attributes,
 * server-rendered and translated by config_page.py's render() (the
 * seventh, DIRTY_BAR_INITIAL_TEXT, is departure 5 above). Each var
 * declaration below documents its own hardcoded fallback literal, used
 * only when the corresponding attribute is missing, so the bar can
 * never render empty or untranslated; the pluralisation LOGIC itself
 * (which branch runs) stays in this file — only the words move.
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

  // D-14/S-04: Quiet hours presets. Fills the two time inputs and the
  // enable checkbox client-side, then marks the form dirty through
  // notifyDirty() below. Placed here, BEFORE the [data-dirty-bar]/
  // [data-dirty-count] guard immediately below, so the presets keep
  // working even on a page whose save bar failed to initialise — that
  // is the whole point of D-09. This script is served to every page on
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
      notifyDirty();
    });
  }

  // Reuses updateBar()/countDifferences() below rather than dispatching
  // a synthetic change event — constructing one in an ES5-safe way is
  // awkward and unnecessary when the handler that needs to react lives
  // in this very same file. Only calls updateBar() once the bar itself
  // is confirmed present, so a missing bar degrades to "the fields
  // still fill in, there is just no dirty count to show" rather than
  // throwing.
  function notifyDirty() {
    if (bar && countEl) {
      updateBar();
    }
  }

  if (!bar || !countEl) {
    return;
  }

  // DEPARTURE 1 (see this file's own header): the no-JS-floor polarity
  // inversion, in one line. The bar is no longer server-rendered
  // hidden — there is no second, separate fallback Save button any
  // more, so the bar's own visible server-rendered state IS the no-JS
  // floor. Once script has proven itself live (this line has run), the
  // enhanced experience takes over: the bar hides until there is
  // something real to report. Set BEFORE any word is read below and
  // before any listener is attached, so no edit can race this line.
  bar.hidden = true;

  // D-06 (20-11-PLAN.md Task 3): read once, off the dirty-bar element
  // itself, now that it is proven present — see this file's own header
  // comment for what each attribute means. Each fallback literal below
  // is this file's own pre-27-04 English wording, restored verbatim,
  // used only when the corresponding attribute is absent.
  var dirtyChangedSuffix = bar.getAttribute("data-dirty-changed-suffix") || " changed";
  var dirtyAnd = bar.getAttribute("data-dirty-and") || " and ";
  var dirtyListAnd = bar.getAttribute("data-dirty-list-and") || ", and ";
  var dirtyUnsavedSingular = bar.getAttribute("data-dirty-unsaved-singular") || "1 unsaved change";
  var dirtyUnsavedPlural = bar.getAttribute("data-dirty-unsaved-plural") || " unsaved changes";
  // 23-09-PLAN.md Task 2 (D3/CFG-32): the sixth word, same idiom, same
  // reason — see this file's own header and config_page.py's own
  // DIRTY_SAVING_TEXT comment. The fallback literal is byte-identical
  // to the server constant; a check fails if the two ever drift.
  var dirtySavingText = bar.getAttribute("data-dirty-saving") || "Saving…";
  // DEPARTURE 5 (see this file's own header): the seventh word, read
  // for parity with the six above — no branch below currently spends
  // it (none of updateBar()'s four copy branches ever say the plain
  // initial-state sentence); kept explicit, and its own fallback-
  // literal check passes on this line alone, rather than silently
  // dropping the read and letting a future reader wonder where the
  // seventh word went.
  var dirtyInitialText = bar.getAttribute("data-dirty-initial-text") || "Unsaved changes";

  // DEPARTURE 3 (see this file's own header): NEITHER of this file's own
  // two former liveness-marker classes is written onto <html> here.
  // Both existed for exactly one consumer — style.css's own content-
  // clearance rules, scoped to the shorter marker — and that consumer
  // is gone: 28-08-PLAN.md Task 2's restored clearance uses
  // :has(.dirty-bar) instead, which needs no script-written marker and
  // (unlike a marker class) works correctly with scripts blocked. Do
  // not reintroduce either marker by copying an older commit's shape
  // wholesale.

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

  // freshness.js:385 is this file's only external consumer — "presence
  // is not proof of life" (27-04's own reasoning for building it this
  // way) is still correct even though the auto-save that motivated it
  // is gone. Wired to the restored countDifferences() below, unchanged
  // in shape from its 27-04 form.
  window.SkyPaneDirtyState = {
    hasUncommittedEdits: function () {
      return countDifferences() > 0;
    }
  };

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
  //
  // 22-01-PLAN.md Task 3 (D-01/B1): the wrapper lookup below queries
  // document, not form. On the Display scope every [data-dirty-section]
  // group renders as a SIBLING of the physical form, exactly like the
  // fields inside them — form.querySelectorAll() only ever searches
  // descendants, so it would find zero wrappers there and the bar would
  // silently fall back to its raw-count copy on every Display save,
  // never naming a section. Wrapper membership is still resolved the
  // identical way afterwards (wrapper.contains(el) against
  // form.elements) — only the wrapper QUERY's scope matters here, for
  // the same reason the listener attachment point below is
  // document-level too.
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

  // 23-09-PLAN.md Task 1 (D3/CFG-32): the stylesheet's EXISTING
  // changed-value animation, not a fourth keyframes block. Its own rule
  // comment says it names the motion rather than the component so the
  // next thing that changes under the reader spends it, and 23-08's own
  // notes hand it to this plan by name. The bar's ENTRANCE is a
  // different motion and has its own block; this is only the count.
  var COUNT_CHANGED_CLASS = "is-fading-in";

  // The count's ONE write site (there were four, one per branch of
  // updateBar() below), and the whole reason it is one.
  //
  // The bar is role="status" and this element is its content, so every
  // write to it is a potential announcement. updateBar() runs on every
  // change AND every input event — which is every keystroke in the
  // wake-interval and quiet-hours fields — and most of those produce the
  // same sentence again. Re-writing identical text into a live region is
  // how a screen reader ends up reading the same number twice, and
  // animating it would be motion carrying no information, which is the
  // one thing a motion budget exists to stop. So: nothing happens at all
  // unless the sentence genuinely differs.
  //
  // The TEXT is written first and the CLASS second. What animates is the
  // element's presentation; the number itself is never tweened, so the
  // displayed value is the real one at every instant including the
  // animation's first frame. An animation that had to rewrite the text
  // mid-transition would be the wrong animation, not a reason to accept
  // a partial announcement.
  //
  // Removed, reflowed, re-added: a class that is already present runs
  // nothing on the next change, because the browser coalesces a remove
  // and an add in the same frame into no change at all. Reading a layout
  // property in between is what forces the removal to take effect first
  // — and it is a READ, not a timer: this file's own header makes "never
  // a timer" a standing constraint (with the one named exception), and a
  // live check enforces it.
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
      // section wrapper. Falls back to the raw-count copy this file
      // shipped before D-03's section-naming so the bar can never go
      // silent while unsaved edits exist.
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

  // B1/D-01 (22-01-PLAN.md Task 2): document-level delegation, filtered
  // to this form's own associated elements via the native .form
  // property (authoritative for both real descendants and any
  // form=-attached field living elsewhere in the DOM) — see this
  // file's own header comment for the full defect history. A change/
  // input anywhere else on the page (a different form, or a page with
  // no dirty form at all) resolves e.target.form !== form and is a
  // no-op.
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

  // D-10/A-28: warn before a real navigation discards unsaved edits.
  // Keyed on countDifferences() — the exact same predicate the bar
  // itself uses, reused rather than reimplemented, so the two can never
  // disagree about whether the form is actually dirty. Both
  // evt.preventDefault() and setting evt.returnValue are needed for
  // cross-browser coverage; the browser supplies its own confirmation
  // copy in every modern browser, so never try to set a custom message.
  // This preventDefault() is correct and load-bearing — it cancels a
  // NAVIGATION, never the unrelated reset event the Cancel
  // enhancement below listens for (see that handler's own comment for
  // why THAT event must never be cancelled).
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
  // its form="settings-form" attribute (config_page.py's render(), the
  // relocated STATIC_SAVE_FALLBACK_ATTR button) — so this single submit
  // listener covers the bar's own Save button. Do not add a second click
  // handler on it for this; there is nothing to hook, it is a plain
  // native submit.
  form.addEventListener("submit", function (evt) {
    suppressGuard = true;
    relabelSubmitter(evt);
  });

  // 23-09-PLAN.md Task 2 (D3/CFG-32): the in-flight label. T14
  // (22-15-PLAN.md Task 3) left this to D3 explicitly; submit-guard.js
  // deliberately changes no label at all, and still does not.
  //
  // --- WHY THIS MAY RUN INLINE, WHICH IS THE WHOLE QUESTION ----------
  //
  // submit-guard.js's own header is the model for this register, and it
  // asks one question of anything that touches a submitting control: a
  // submit button's own name/value pair is contributed to the form data
  // set by the SUBMITTER, and that set is built AFTER the submit event's
  // listeners return. That is why THAT file switches the control off
  // from a zero-delay timer rather than inline — inline, it would drop
  // the field that says what the user asked for.
  //
  // The answer for this control is a property of the control, not of the
  // timing. The bar's own Save is a <button type="submit"> carrying NO
  // name attribute (config_page.py's render(), the bar's markup), and a
  // submitter with no name contributes NO entry to the form data set at
  // all — so there is nothing a label could displace, whenever this
  // runs. The clause below re-checks that on the live control rather
  // than trusting it: if a later plan ever gives the Save button a name,
  // the relabel stands down on its own instead of quietly rewriting a
  // payload.
  //
  // The <button> clause is the sharper half of the same argument. An
  // <input type="submit"> has no text content: its LABEL IS ITS VALUE,
  // so relabelling one genuinely does change what is posted. That
  // element is excluded by shape, not by a comment.
  //
  // --- ORDER AGAINST submit-guard.js, WHICH IS FIXED, NOT LUCKY ------
  //
  // This listener is registered on the FORM; submit-guard.js's is on
  // document. A submit event dispatched at the form bubbles to the
  // form's own listeners before it reaches document, so this one runs
  // first, synchronously, every time. submit-guard.js then only SCHEDULES
  // its own write, from a zero-delay timer, which cannot run until the
  // whole dispatch has finished. So the sequence is relabel, then the
  // shared guard, and it is guaranteed by event propagation plus a
  // queued task rather than by either file knowing about the other.
  //
  // Neither file cancels anything, and neither writes the other's
  // property: this one writes text content and never the property that
  // makes a control unusable, and submit-guard.js writes that property
  // and never text.
  //
  // evt.submitter absent (an older browser, or a submission with no
  // submitter at all) simply means no relabel. That degrades to exactly
  // what this control did before this plan, which is the right degrade
  // for a label: guessing at the submitter would risk relabelling a
  // control whose name/value IS the request.

  // The one control this file has relabelled, so a back/forward-cache
  // restore can put it back. A page restored from bfcache comes back
  // with the DOM exactly as it was left — including a Save button still
  // reading the in-flight word for a request that finished, or never
  // finished, a navigation ago. submit-guard.js restores the controls it
  // wrote on the same event and for the same reason; this is that
  // pattern applied to the property this file writes, and only to a
  // control this file wrote it on.
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

  // 22-05-PLAN.md Task 3 (D-04): a Frame strip switch is its own,
  // separate <form> (action="/quick/display" or "/quick/quiet-hours",
  // companion/layout.py's frame_strip_html()) — submitting it navigates
  // away exactly like the settings form's own Save does, but the
  // settings form's own submit listener above never fires for it (it is
  // a different <form> element entirely). Without this, activating a
  // strip switch while the settings form has unsaved edits raises the
  // same leave-page dialog Save itself is exempt from, for a change the
  // strip is itself about to apply. Delegated at the document level (the
  // switch could be either of two forms, never exactly this file's own
  // form variable) and keyed below on the submitting form's own pinned
  // handshake attribute (22-04-PLAN.md Task 1's own named deliverable on
  // both strip switch forms) — never a presentation class, which a later
  // CSS change could rename with no semantic meaning behind it. Every
  // OTHER form's submit (a page with no strip at all, or a deliberately
  // crafted third-party form) still leaves suppressGuard untouched here,
  // so the leave-guard still arms for it exactly as before.
  document.addEventListener("submit", function (e) {
    if (e.target && e.target.hasAttribute && e.target.hasAttribute("data-quick-switch")) {
      suppressGuard = true;
    }
  });

  // --- THE CANCEL ENHANCEMENT (DEPARTURE 4) ------------------------------
  //
  // config_page.py's render() now ships Cancel as a NATIVE
  // <button type="reset" form="settings-form" data-dirty-cancel> — not
  // 6dea46a's own <button type="button">, because with the bar visible
  // by default now (DEPARTURE 1), a type="button" Cancel would be a
  // fully visible, fully inert control for every scripts-blocked
  // visitor. The native reset already restores every field, with or
  // without script. THIS FILE MUST NOT CALL THE FORM'S OWN NATIVE
  // reset() METHOD ITSELF — doing so would replace a working native
  // behaviour with a scripted one and re-create exactly the no-JS hole
  // DEPARTURE 1 exists to keep shut.
  //
  // So: listen for the form's own reset EVENT (fired on the form when
  // the native reset runs — more robust than a click handler on the
  // button, and it also catches a programmatic reset), and layer only
  // the enhancements a native reset cannot do on top of it.
  //
  // THE ORDERING FACT, AND IT IS A SPECIFICATION FACT RATHER THAN AN
  // ENGINE QUIRK. The reset event ALWAYS fires BEFORE the browser
  // restores the form's fields, in every engine. It is not a
  // notification that the reset has happened; it is the *cancelable
  // trigger* for the reset, and restoring the fields is that event's
  // DEFAULT ACTION, performed only if no handler calls
  // preventDefault(). Everything done SYNCHRONOUSLY inside this handler
  // therefore reads the STALE, PRE-RESET field values. A synchronous
  // window.SkyPaneLivePreview.refresh() here would re-apply the theme
  // the user just asked to discard — the exact defect Cancel exists to
  // prevent.
  //
  // The form's own native reset() also fires NO change/input events on
  // the fields it restores — that is spec behaviour, not a quirk — so nothing
  // downstream of those events repaints on its own. That is precisely
  // why BOTH repaints below have to be called explicitly, and why the
  // theme preview and the quiet-hours dial would otherwise keep showing
  // the discarded values forever.
  //
  // So: two state-only side effects run SYNCHRONOUSLY (they depend on no
  // field value), and both repaints are scheduled for the NEXT tick, from
  // a single zero-delay deferred callback below — the standard idiom for
  // "run this after the browser has finished the default action of the
  // event currently being dispatched". The restore happens synchronously
  // the instant
  // this handler returns, so the deferred callback is the first point at
  // which fully restored values are readable. This is NOT a poll, NOT a
  // debounce, NOT an animation timer and NOT a retry — it is a
  // reset-event side-effect flush, and it is the ONE timer this file's
  // own header names as a permitted exception.
  //
  // NEVER call preventDefault() on the reset event in this handler,
  // and never write evt.returnValue here. The field restore IS that
  // event's default action: cancelling it would turn Annuler into a
  // silent no-op for every visitor running JS, while continuing to work
  // perfectly with scripts blocked — the worst possible failure shape,
  // because the no-JS floor would mask it entirely. (This file's OTHER
  // preventDefault() — the beforeunload leave-guard above — cancels an
  // unrelated NAVIGATION event and is correct and load-bearing; the ban
  // here is scoped to this handler's own body, not to the file.)
  //
  // A repaint listener for the quiet-hours dial's OWN document-level
  // click delegate (companion/static/value-controls.js's own
  // document.addEventListener("click", repaintAll)) does NOT make this
  // deferred call redundant: a click on a <button type="reset">
  // dispatches and bubbles to COMPLETION before the button's own default
  // action — the reset — runs, so that listener fires while the fields
  // still hold the EDITED values and repaints the dial straight back to
  // the value the user just discarded. This is a fact about event
  // dispatch order, not an empirical question — see value-controls.js's
  // own newly-exposed entry point below, called from AFTER the restore,
  // which lands last and therefore wins. The harmless consequence is
  // that a Cancel repaints the dial twice: once wrongly, from the
  // bubbling click, then once correctly, from this deferred tick.
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
