/*
 * SkyPane companion service — value-controls.js.
 *
 * CFG-46 (25-01-PLAN.md Task 1). Phase 25's ONE new static script, and
 * the only one it is allowed. Its subject is a control that steers a
 * CONTINUOUS VALUE: a handle you drag or arrow, over a track or around
 * a dial, whose whole job is to put a number into a native form input
 * the server already renders and the form already posts.
 *
 * Two consumers are coming — 25-04's 24 h quiet-hours dial and 25-05's
 * wake-interval slider — and they are ONE behaviour, not two: clamp a
 * number into a stated range and step, write it into a named input,
 * wake the save bar. Two scripts would have been two copies of one
 * clamp/round/keyboard model, drifting the first time either was
 * touched. They differ here only in the attributes their markup
 * carries.
 *
 * --- THIS FILE CREATES NO CONTROL, AND TODAY IT HAS NO SUBJECT -------
 *
 * There is no markup anywhere in this app carrying the wrapper
 * attribute below. That is deliberate and it is the state every script
 * here is in on fifteen of its sixteen pages: served everywhere,
 * inert until its subject appears, no-op via its own guard. What this
 * file gives 25-04 and 25-05 is the plumbing, so each of them adds
 * markup and a check rather than a script, a route, a shell
 * registration and a pin move.
 *
 * --- THE FLOOR IS STRUCTURAL, AND IT IS NOT NEGOTIABLE --------------
 *
 * D-09 (22-CONTEXT.md:133-135) is a locked decision. Every value this
 * file can change is held by a native <input> the SERVER renders on
 * every render, with its own min/max/step and its own form association.
 * Delete this file and every one of those inputs still renders, still
 * validates, still posts and still saves. Specifically:
 *
 *   1. This file never holds a value. There is exactly one assignment
 *      to a .value in it (the write into the native input), and every
 *      read of the control's current state is a read of that same
 *      input. There is no parallel state anywhere here — no map keyed
 *      by element, no cached number, nothing to fall out of step.
 *   2. This file never renders an affordance. An affordance that cannot
 *      work without script lives inside companion/static/style.css's
 *      .js-gated wrapper, which HIDES by default and reveals under
 *      .js — so with scripts blocked the handle is not merely
 *      invisible, it is out of the layout and out of the tab order.
 *   3. This file writes no copy. aria-valuetext is filled from a
 *      SERVER-RENDERED, already-translated template on the wrapper; if
 *      no template is there, no aria-valuetext is written at all and
 *      the numeric aria-valuenow stands alone. A French reader can
 *      therefore never be dropped into English by touching a handle.
 *
 * --- HOW THE SAVE BAR IS WOKEN, AND WHY IT IS THIS WAY --------------
 *
 * A control that changes a value without waking the save bar is a
 * control that silently loses the user's edit, so this is the part of
 * this file with the most care spent on it.
 *
 * companion/static/dirty-state.js's own quiet-hours preset handler
 * reaches its bar by calling a PRIVATE notifyDirty(), which is a
 * closure inside that file's IIFE and is unreachable from here. The
 * question this plan had to answer was therefore: move the control
 * into dirty-state.js, or notify across the file boundary?
 *
 * ANSWER: notify across the boundary, because a public surface for
 * exactly this already exists and is already load-bearing.
 * dirty-state.js registers DELEGATED document-level change and
 * input listeners, filtered to e.target.form === form — that
 * delegation is 22-01's own fix for the B1 defect, and it is what makes
 * every form=-attached settings field (which is what all of them are)
 * reach the bar at all. A bubbling change dispatched on the input
 * this file wrote is therefore indistinguishable, to dirty-state.js,
 * from a user typing in that input — which is precisely the semantics
 * wanted. dirty-state.js needs no change of any kind, and its private
 * preset path keeps working exactly as it does today.
 *
 * The alternative — moving a dial and a slider into dirty-state.js —
 * would have put two page-specific controls inside the file that owns
 * the app's unsaved-edits guard, which is the last file in this tree
 * that should grow a feature.
 *
 * A harness pins both ends of this: the event name constructed in BOTH
 * branches below, and dirty-state.js's listener for it, together with
 * that listener's e.target.form filter.
 *
 * --- CONSTRAINTS THIS FILE MUST KEEP -------------------------------
 *
 * No build step, no bundler, no framework, no dependency, and an
 * ES5-safe subset throughout (no arrow functions, no block-scoped
 * declarations, no template literals) so no transpiler is ever needed.
 * Unlike three of its siblings it claims NO reviewed exception: no
 * network call, no timer, no navigation, and no HTML-writing sink of
 * any kind. It writes attributes, one custom property and one input
 * value, and nothing else.
 *
 * It is served by companion/app.py's VALUE_CONTROLS_SCRIPT_ROUTE and
 * registered once on the authenticated shell by companion/layout.py's
 * page_shell(), because its two consumers already live on two
 * different settings pages and the set is expected to grow.
 */
(function () {
  "use strict";

  // The registration seam. Every one of these is defined on the Python
  // side too (companion/layout.py's VALUE_CONTROL_* constants) and a
  // harness asserts the served body names them, so a rename on either
  // side alone fails rather than producing a control that renders and
  // steers nothing.
  //
  // The wrapper. Carries the whole contract; nothing outside a wrapper
  // is ever touched by this file.
  var WRAPPER_ATTR = "data-value-control";
  // The name of the native input this control writes into. The input
  // itself is server-rendered, unconditionally, with its own min/max.
  var FIELD_ATTR = "data-value-field";
  // The id of the <form> that input belongs to. Needed because this
  // app's settings groups deliberately attach ACROSS the DOM via a
  // form= attribute (a <form> can never nest inside another <form>), so
  // walking up from the wrapper would miss the field. Absent, the
  // nearest ancestor <form> is used instead.
  var FORM_ATTR = "data-value-form";
  var MIN_ATTR = "data-value-min";
  var MAX_ATTR = "data-value-max";
  var STEP_ATTR = "data-value-step";
  // The grabbable element, and the element whose box (or circle) the
  // pointer position is measured against.
  var HANDLE_ATTR = "data-value-handle";
  var TRACK_ATTR = "data-value-track";
  // "angular" for a dial, anything else (including absent) for a
  // left-to-right track. Compared inline rather than held in a named
  // ALL_CAPS constant, for the reason quick-switch.js's own state
  // values document: a bare lowercase word in a named JS constant is
  // what this project's translation scanner reads as untranslated
  // user-facing copy, and this is a geometry mode, not copy.
  var GEOMETRY_ATTR = "data-value-geometry";
  // The SERVER-RENDERED, already-translated aria-valuetext template.
  // The token below is replaced with the number. No template, no
  // aria-valuetext — never an English sentence invented here.
  var TEXT_ATTR = "data-value-text";
  // "#" and not "{}": these templates reach the browser as attribute
  // values on a rendered page, and companion/test_i18n.py scans every
  // French render for a stray "%s"/"%d"/"{}" — the real failure mode
  // of a mistyped catalogue key. Corrected in place by 25-04 when the
  // first consumer of this seam tripped that check. companion/
  // layout.py's RELATIVE_QUANTITY_MARK already records the reasoning.
  var TEXT_TOKEN = "#";
  // The CODEC between the NUMBER this file steers and the TEXT the
  // native input holds — 25-04-PLAN.md Task 3 (CFG-48), and the second
  // of exactly two places this file's consumers differ (the first is
  // GEOMETRY_ATTR above).
  //
  // WHY IT HAD TO EXIST. 25-04's dial steers the two native
  // <input type="time"> fields the quiet-hours form already posts, and
  // a time input holds "HH:MM" and silently DISCARDS anything else.
  // Writing a minute count straight into one would empty the field the
  // form posts, on the first arrow press, with no error anywhere — the
  // "changes a value and loses the edit" failure this file's own header
  // spends its longest paragraph on. The alternative (a hidden numeric
  // input beside the visible time input) was refused by 25-04's plan
  // outright: the time inputs stay visible AND stay what the form
  // posts, because typing 23:00 beats dragging to it and they are the
  // only controls on that card a visitor can type into at all.
  //
  // Compared inline against a bare lowercase word rather than held in a
  // named ALL_CAPS constant, for the reason GEOMETRY_ATTR's own comment
  // records: a bare lowercase word in a named JS constant is what this
  // project's translation scanner reads as untranslated user-facing
  // copy, and a value FORMAT is not copy.
  var FORMAT_ATTR = "data-value-format";
  var MINUTES_PER_HOUR = 60;
  var HOURS_PER_DAY = 24;
  var CLOCK_RE = /^(\d{1,2}):(\d{2})$/;

  // The painted position, as a 0..1 fraction, handed to the stylesheet
  // as a custom property so every bit of geometry stays in the CSS.
  var FRACTION_PROPERTY = "--value-fraction";

  // How many steps PageUp/PageDown move. Ten is the native <input
  // type="range"> convention and needs no attribute.
  var PAGE_STEPS = 10;

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

  function ancestorForm(el) {
    var node = el;
    while (node) {
      if (node.tagName && node.tagName.toLowerCase() === "form") {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  // The native input this wrapper steers, or null. Asked of the DOM
  // every time rather than cached: a cache would be the parallel state
  // this file is forbidden to hold, and freshness.js can swap whole
  // regions of the document out from under it.
  function fieldFor(wrapper) {
    var name = wrapper.getAttribute(FIELD_ATTR);
    if (!name) {
      return null;
    }
    var formId = wrapper.getAttribute(FORM_ATTR);
    var form = formId ? document.getElementById(formId) : ancestorForm(wrapper);
    if (!form || !form.elements) {
      return null;
    }
    var field = form.elements[name];
    // A radio group resolves to a collection rather than an element.
    // This file steers a single continuous value, so anything without
    // its own .value is not its subject.
    if (!field || typeof field.value !== "string") {
      return null;
    }
    return field;
  }

  // A finite number from raw, or null. parseFloat is deliberately
  // guarded by isFinite: parseFloat("") is NaN, parseFloat(null) is
  // NaN, and NaN silently poisons every clamp it reaches.
  function numberOrNull(raw) {
    var value = parseFloat(raw);
    if (typeof value !== "number" || !isFinite(value)) {
      return null;
    }
    return value;
  }

  // The bounds this wrapper declares. Missing or unusable bounds mean
  // this file does nothing at all — it does NOT invent a range, because
  // an invented range would write a value the server's own re-check
  // would then reject.
  function boundsFor(wrapper) {
    var min = numberOrNull(wrapper.getAttribute(MIN_ATTR));
    var max = numberOrNull(wrapper.getAttribute(MAX_ATTR));
    var step = numberOrNull(wrapper.getAttribute(STEP_ATTR));
    if (min === null || max === null || max <= min) {
      return null;
    }
    if (step === null || step <= 0) {
      step = 1;
    }
    return { min: min, max: max, step: step };
  }

  // THE CLAMP. Round to the nearest step measured FROM the minimum,
  // then clamp into the inclusive range — in that order, so a maximum
  // that does not sit on a step boundary is still exactly reachable
  // rather than rounded away. Total by construction: a non-numeric or
  // null input returns the minimum rather than NaN, and a value beyond
  // either end returns that end exactly.
  function clampToStep(raw, bounds) {
    var value = numberOrNull(raw);
    if (value === null) {
      return bounds.min;
    }
    var stepped = bounds.min + Math.round((value - bounds.min) / bounds.step) * bounds.step;
    // Rounding in floating point can leave a long tail (0.1 + 0.2).
    // Six decimal places is far finer than any control here needs and
    // removes the tail without changing any value a step can produce.
    stepped = Math.round(stepped * 1000000) / 1000000;
    return Math.max(bounds.min, Math.min(bounds.max, stepped));
  }

  function isClockFormat(wrapper) {
    return wrapper.getAttribute(FORMAT_ATTR) === "clock";
  }

  // The field's TEXT as this file's number, or null. Total by
  // construction and deliberately stricter than the shape alone:
  // "99:99" matches the pattern and is minute 5,999 of a 1,440-minute
  // day, which would send the geometry off the dial.
  function fieldToNumber(wrapper, raw) {
    if (!isClockFormat(wrapper)) {
      return numberOrNull(raw);
    }
    var parts = CLOCK_RE.exec(String(raw));
    if (!parts) {
      return null;
    }
    var hours = numberOrNull(parts[1]);
    var minutes = numberOrNull(parts[2]);
    if (hours === null || minutes === null
        || hours > HOURS_PER_DAY - 1 || minutes > MINUTES_PER_HOUR - 1) {
      return null;
    }
    return hours * MINUTES_PER_HOUR + minutes;
  }

  // This file's number as the field's TEXT. Zero-padded both halves,
  // because "7:0" is not a value a native time input accepts and a
  // rejected write is an emptied field.
  function numberToField(wrapper, value) {
    if (!isClockFormat(wrapper)) {
      return String(value);
    }
    var whole = Math.max(0, Math.round(value));
    var hours = Math.floor(whole / MINUTES_PER_HOUR) % HOURS_PER_DAY;
    var minutes = whole % MINUTES_PER_HOUR;
    return (hours < 10 ? "0" : "") + hours + ":" + (minutes < 10 ? "0" : "") + minutes;
  }

  // The control's CURRENT value: read back off the native input, never
  // from anything this file remembers. A field holding something
  // unusable falls back to the minimum, which is a defined answer
  // rather than a NaN travelling into the geometry.
  function currentValue(wrapper, bounds) {
    var field = fieldFor(wrapper);
    var value = field ? fieldToNumber(wrapper, field.value) : null;
    if (value === null) {
      return bounds.min;
    }
    return Math.max(bounds.min, Math.min(bounds.max, value));
  }

  // The bubbling notification dirty-state.js's delegated document-level
  // listener is waiting for. Constructed the modern way where the
  // browser has it and through the legacy path otherwise; BOTH branches
  // name the same event, and a harness asserts they do, because a file
  // whose two branches disagree wakes the save bar on one browser and
  // loses the edit on another.
  function notify(field) {
    var evt = null;
    if (typeof window.Event === "function") {
      evt = new window.Event("change", { bubbles: true, cancelable: false });
    } else if (document.createEvent) {
      evt = document.createEvent("HTMLEvents");
      evt.initEvent("change", true, false);
    }
    if (evt) {
      field.dispatchEvent(evt);
    }
  }

  // The announced state. aria-valuenow is the number and needs no
  // translation; aria-valuetext is written ONLY when the server put a
  // translated template on the wrapper.
  //
  // THE ANNOUNCED ELEMENT IS THE FOCUSABLE HANDLE when the wrapper has
  // one, and the wrapper itself otherwise. role="slider" and its
  // aria-value* belong on the element a keyboard visitor actually lands
  // on: a wrapper holding them while a <button> inside it takes the
  // focus announces a value that never changes, which is worse than
  // announcing none — a screen reader would read the saved time on
  // every step of a drag that had already moved somewhere else.
  //
  // aria-valuetext carries the value in the FIELD's own notation
  // (25-04's dial announces "23:00", not "one thousand three hundred
  // and eighty", which is the whole reason aria-valuetext exists),
  // through the same codec the field write below goes through — one
  // conversion, so the announcement and the stored value cannot
  // disagree.
  function paint(wrapper, bounds, value) {
    var announce = wrapper.querySelector("[" + HANDLE_ATTR + "]") || wrapper;
    announce.setAttribute("aria-valuenow", String(value));
    var text = wrapper.getAttribute(TEXT_ATTR);
    if (text) {
      announce.setAttribute(
        "aria-valuetext", text.split(TEXT_TOKEN).join(numberToField(wrapper, value)));
    }
    if (wrapper.style && wrapper.style.setProperty) {
      var span = bounds.max - bounds.min;
      wrapper.style.setProperty(
        FRACTION_PROPERTY, String((value - bounds.min) / span));
    }
  }

  // THE ENTRY POINT. Clamp, round, write into the native input, wake
  // the save bar, paint. Returns the value actually written, or null
  // when this wrapper has no usable bounds or no field — so a caller
  // can never mistake "refused" for "wrote the minimum".
  function steer(wrapper, raw) {
    var bounds = boundsFor(wrapper);
    if (!bounds) {
      return null;
    }
    var field = fieldFor(wrapper);
    if (!field) {
      return null;
    }
    var value = clampToStep(raw, bounds);
    var next = numberToField(wrapper, value);
    if (field.value !== next) {
      field.value = next;
      notify(field);
    }
    paint(wrapper, bounds, value);
    return value;
  }

  // Pointer geometry, and the only place the dial and the track differ.
  // Returns a 0..1 fraction along the track, or null when the element's
  // box has no extent at all (a display:none ancestor, which is exactly
  // what the .js gate produces with scripts blocked — and a division
  // by zero would be the NaN this file refuses to write).
  function fractionFromPointer(wrapper, track, clientX, clientY) {
    var rect = track.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    if (wrapper.getAttribute(GEOMETRY_ATTR) === "angular") {
      var cx = rect.left + rect.width / 2;
      var cy = rect.top + rect.height / 2;
      var dx = clientX - cx;
      var dy = clientY - cy;
      if (dx === 0 && dy === 0) {
        return null;
      }
      // Clockwise from twelve o'clock, normalised into [0, 1).
      var angle = Math.atan2(dx, -dy) / (Math.PI * 2);
      if (angle < 0) {
        angle += 1;
      }
      return angle;
    }
    return (clientX - rect.left) / rect.width;
  }

  function steerFromPointer(wrapper, clientX, clientY) {
    var track = wrapper.querySelector("[" + TRACK_ATTR + "]");
    if (!track) {
      return;
    }
    var bounds = boundsFor(wrapper);
    if (!bounds) {
      return;
    }
    var fraction = fractionFromPointer(wrapper, track, clientX, clientY);
    if (fraction === null) {
      return;
    }
    fraction = Math.max(0, Math.min(1, fraction));
    steer(wrapper, bounds.min + fraction * (bounds.max - bounds.min));
  }

  // Which wrapper, if any, this event belongs to. THE GUARD CLAUSE:
  // every listener below returns from here on every page that carries
  // no continuous-value control, before reading or writing a single
  // thing in the DOM. That is every page in this app today.
  function wrapperFor(target) {
    if (!target || !target.getAttribute) {
      return null;
    }
    return ancestorWith(target, WRAPPER_ATTR);
  }

  // The keyboard model, and it is the native <input type="range"> one
  // rather than a new invention: arrows move one step in each
  // direction, PageUp/PageDown move ten, Home and End go to the ends.
  // Up and Right both increase, matching the native control in both
  // orientations. Returns null for every other key, so nothing else a
  // keyboard user presses is swallowed.
  function keyedValue(key, value, bounds) {
    if (key === "ArrowRight" || key === "ArrowUp") {
      return value + bounds.step;
    }
    if (key === "ArrowLeft" || key === "ArrowDown") {
      return value - bounds.step;
    }
    if (key === "PageUp") {
      return value + bounds.step * PAGE_STEPS;
    }
    if (key === "PageDown") {
      return value - bounds.step * PAGE_STEPS;
    }
    if (key === "Home") {
      return bounds.min;
    }
    if (key === "End") {
      return bounds.max;
    }
    return null;
  }

  document.addEventListener("keydown", function (evt) {
    var wrapper = wrapperFor(evt.target);
    if (!wrapper) {
      return;
    }
    var bounds = boundsFor(wrapper);
    if (!bounds) {
      return;
    }
    var next = keyedValue(evt.key, currentValue(wrapper, bounds), bounds);
    if (next === null) {
      return;
    }
    // Only for the keys actually handled: arrows and Page keys scroll
    // the page otherwise, and swallowing Tab or Enter would trap a
    // keyboard user inside a control.
    evt.preventDefault();
    steer(wrapper, next);
  });

  // Pointer steering. pointerdown on the handle (or anywhere on the
  // track) begins a drag; setPointerCapture keeps the subsequent moves
  // coming even when the pointer leaves the element, which is what
  // makes a drag that overshoots the end behave like a native one.
  document.addEventListener("pointerdown", function (evt) {
    var wrapper = wrapperFor(evt.target);
    if (!wrapper) {
      return;
    }
    var handle = ancestorWith(evt.target, HANDLE_ATTR)
        || wrapper.querySelector("[" + HANDLE_ATTR + "]");
    // A drag is a pointer gesture, not a text selection or a scroll.
    evt.preventDefault();
    if (handle && handle.setPointerCapture && evt.pointerId !== undefined) {
      try {
        handle.setPointerCapture(evt.pointerId);
      } catch (err) {
        // A pointer that has already been released cannot be captured.
        // Steering still works from the move events; nothing here needs
        // the capture to have succeeded.
      }
    }
    if (handle && handle.focus) {
      handle.focus();
    }
    steerFromPointer(wrapper, evt.clientX, evt.clientY);
  });

  document.addEventListener("pointermove", function (evt) {
    // evt.buttons is 0 for a hover, so a pointer merely passing over a
    // control never moves it.
    if (!evt.buttons) {
      return;
    }
    var wrapper = wrapperFor(evt.target);
    if (!wrapper) {
      return;
    }
    evt.preventDefault();
    steerFromPointer(wrapper, evt.clientX, evt.clientY);
  });

  // No DOMContentLoaded wrapper, and no load-time pass over the
  // document either. The <script> tag companion/layout.py's
  // page_shell() emits carries defer, so this file only runs after
  // parsing; and the INITIAL position of every control is rendered by
  // the server, from the saved value, so there is nothing to
  // initialise. That is not an omission — it is what makes the
  // scripts-blocked rendering correct rather than merely present, and
  // it is why this file mutates absolutely nothing until a user
  // touches a control that exists.
})();
