/*
 * SkyPane companion service — value-controls.js.
 *
 * Drives continuous-value controls (a dial or slider steering a native
 * form input the server already renders): clamps a number into a
 * stated range/step, writes it into the named input, wakes the save
 * bar, paints the handle. Inert until a page carries a
 * [data-value-control] wrapper; no build step, ES5-safe subset. Served
 * by companion/app.py's VALUE_CONTROLS_SCRIPT_ROUTE.
 */
(function () {
  "use strict";

  // Registration seam: every attribute below is also defined on the
  // Python side (companion/layout.py's VALUE_CONTROL_* constants).
  // Nothing outside a [data-value-control] wrapper is ever touched.
  var WRAPPER_ATTR = "data-value-control";
  // Name of the native input this control writes into (server-rendered
  // with its own min/max).
  var FIELD_ATTR = "data-value-field";
  // id of the <form> the field belongs to, since settings groups attach
  // across the DOM via a form= attribute rather than nesting; falls
  // back to the nearest ancestor <form>.
  var FORM_ATTR = "data-value-form";
  var MIN_ATTR = "data-value-min";
  var MAX_ATTR = "data-value-max";
  var STEP_ATTR = "data-value-step";
  // The grabbable element, and the element the pointer position is
  // measured against.
  var HANDLE_ATTR = "data-value-handle";
  var TRACK_ATTR = "data-value-track";
  // "angular" for a dial, anything else for a left-to-right track.
  var GEOMETRY_ATTR = "data-value-geometry";
  // Server-rendered, already-translated aria-valuetext template; the
  // token below is replaced with the number. No template, no
  // aria-valuetext.
  var TEXT_ATTR = "data-value-text";
  // "#" rather than "{}", since companion/test_i18n.py scans every
  // French render for a stray "%s"/"%d"/"{}" as a mistyped catalogue key.
  var TEXT_TOKEN = "#";
  // Codec between the number this file steers and the text a native
  // <input type="time"> holds (which stores "HH:MM" and discards
  // anything else). Without this, an arrow press would empty the field
  // the form posts.
  var FORMAT_ATTR = "data-value-format";
  // A native control inside the wrapper mirroring the field's value and
  // posting nothing (no name attribute). Repainted from the field on
  // every paint; a wrapper with a mirror takes no gestures from this
  // file at all, since a native range already has its own keyboard
  // model and drag handling — the job here is to sync, not steer.
  var INPUT_ATTR = "data-value-input";
  // An element whose text is a sentence about the value, found by field
  // name rather than containment (a readout must render correctly with
  // scripts blocked, so it lives outside the gated wrapper). The
  // sentence is a server-rendered, translated template with TEXT_TOKEN
  // standing in for the number.
  var READOUT_ATTR = "data-value-readout";
  var READOUT_TEXT_ATTR = "data-value-readout-text";
  var READOUT_SCALE_ATTR = "data-value-readout-scale";
  var READOUT_BASE_ATTR = "data-value-readout-base";
  // Readout-scoped clock-format signal, mirroring FORMAT_ATTR (a
  // readout is found by field name, not wrapper containment, so it
  // cannot see the wrapper's own FORMAT_ATTR).
  var READOUT_FORMAT_ATTR = "data-value-readout-format";
  var MINUTES_PER_HOUR = 60;
  var HOURS_PER_DAY = 24;
  var MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY;
  var SECONDS_PER_MINUTE = 60;
  var CLOCK_RE = /^(\d{1,2}):(\d{2})$/;

  // companion/layout.py's DURATION_ATTRS, in the same s/m/h/d order as
  // DURATION_BOUNDARY_SECONDS below; companion/test_companion_app.py
  // pins these four present in this file's source.
  var DURATION_ATTRS = [
    "data-duration-s",
    "data-duration-m",
    "data-duration-h",
    "data-duration-d",
  ];
  // layout._age_bucket()'s own three boundaries, in seconds.
  var DURATION_BOUNDARY_SECONDS = [60, 3600, 86400];

  // The painted position, as a 0..1 fraction, handed to the stylesheet
  // as a custom property so all geometry stays in CSS.
  var FRACTION_PROPERTY = "--value-fraction";

  // Pair seam: an arc/caption that is a function of both ends of a
  // window. PAIR_ATTR marks the shared ancestor two wrappers publish
  // onto; its value is the name of the derived sweep property written
  // there once both members have published. PAIR_PROPERTY_ATTR, on a
  // wrapper, names which ancestor property is that wrapper's own
  // fraction. A wrapper with neither attribute is untouched by any of
  // this.
  var PAIR_ATTR = "data-value-pair";
  var PAIR_PROPERTY_ATTR = "data-value-pair-property";

  // How many steps PageUp/PageDown move — the native <input
  // type="range"> convention.
  var PAGE_STEPS = 10;

  // Marks a plain <span> (companion/pages/config_page.py's
  // _normalised_time_html()) shown only to correct a browser whose
  // native <input type="time"> does not render 24-hour time.
  var NORMALISED_TIME_ATTR = "data-normalised-time";

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
  // this file does nothing at all, since an invented range would write
  // a value the server's own re-check would then reject.
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

  // Rounds to the nearest step measured from the minimum, then clamps
  // into the inclusive range, so a maximum off a step boundary is still
  // exactly reachable. A non-numeric or null input returns the minimum
  // rather than NaN.
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

  // Zero-padded "HH:MM" formatting, extracted so a readout wanting the
  // identical text has one place to call rather than a second copy of
  // the arithmetic. Both halves are zero-padded, since "7:0" is not a
  // value a native time input accepts.
  function minutesToClock(value) {
    var whole = Math.max(0, Math.round(value));
    var hours = Math.floor(whole / MINUTES_PER_HOUR) % HOURS_PER_DAY;
    var minutes = whole % MINUTES_PER_HOUR;
    return (hours < 10 ? "0" : "") + hours + ":" + (minutes < 10 ? "0" : "") + minutes;
  }

  // This file's number as the field's TEXT.
  function numberToField(wrapper, value) {
    if (!isClockFormat(wrapper)) {
      return String(value);
    }
    return minutesToClock(value);
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
  // browser has it and through the legacy path otherwise; both branches
  // must name the same event, or a file whose branches disagree wakes
  // the save bar on one browser and loses the edit on another.
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

  // The mirror this wrapper declares, or null. Queried every time for
  // the same reason fieldFor() is: a cache would be state this file is
  // forbidden to hold.
  function mirrorFor(wrapper) {
    return wrapper.querySelector("[" + INPUT_ATTR + "]");
  }

  // The only place in this file that assigns to a .value; both callers
  // go through it: the write into the native input the form posts
  // (steer, below) and the write into the mirror that posts nothing
  // (paint, below). Returns whether anything actually changed,
  // which is what keeps a write during a drag from fighting the thumb
  // the visitor is holding, and what keeps steer() from dispatching a
  // notification for a value that did not move.
  function writeValue(el, text) {
    if (!el || el.value === text) {
      return false;
    }
    el.value = text;
    return true;
  }

  // A readout's own quantity: the value divided by the scale its markup
  // declares, rounded up, since every consumer of this seam states a
  // bound ("at most 2 min" is true of a 90-second cadence). No scale,
  // no division.
  function readoutQuantity(readout, value) {
    var scale = numberOrNull(readout.getAttribute(READOUT_SCALE_ATTR));
    if (scale === null || scale <= 0) {
      return value;
    }
    return Math.ceil(value / scale);
  }

  // Does this readout declare itself clock-formatted — read from
  // READOUT_FORMAT_ATTR, never the wrapper's own FORMAT_ATTR, since a
  // readout is found by field name rather than wrapper containment.
  function isReadoutClockFormat(readout) {
    return readout.getAttribute(READOUT_FORMAT_ATTR) === "clock";
  }

  // pairAncestor's PAIR_PROPERTY_ATTR children are the two paired
  // wrappers, in document order (start before end), read via
  // currentValue() rather than the painted fraction. The wrap,
  // (end - start + MINUTES_PER_DAY) % MINUTES_PER_DAY, measures forward
  // through midnight (23:00 to 07:00 is 480 minutes, never negative)
  // and a start-equals-end window measures 0, not a full day. Returns
  // null when either end has no usable bounds/value.
  function pairedDurationMinutes(pairAncestor) {
    var members = pairAncestor.querySelectorAll("[" + PAIR_PROPERTY_ATTR + "]");
    if (members.length < 2) {
      return null;
    }
    var startBounds = boundsFor(members[0]);
    var endBounds = boundsFor(members[1]);
    if (!startBounds || !endBounds) {
      return null;
    }
    var start = currentValue(members[0], startBounds);
    var end = currentValue(members[1], endBounds);
    return (end - start + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  }

  // wrapper is whichever paired wrapper is currently painting, used to
  // find the shared pair ancestor: the readout element is a sibling of
  // the pair-ancestor div, never a descendant, so the lookup must start
  // from the wrapper. Selects the bucket with _age_bucket()'s own
  // boundaries and walks DURATION_ATTRS in the same order to read the
  // matching server-rendered wording; writes "" when unresolvable.
  function paintDurationReadout(wrapper, readout) {
    var pairAncestor = ancestorWith(wrapper, PAIR_ATTR);
    var minutes = pairAncestor ? pairedDurationMinutes(pairAncestor) : null;
    if (minutes === null) {
      readout.textContent = "";
      return;
    }
    var seconds = Math.max(0, Math.round(minutes * SECONDS_PER_MINUTE));
    var quantity, attrIndex;
    if (seconds < DURATION_BOUNDARY_SECONDS[0]) {
      quantity = seconds;
      attrIndex = 0;
    } else if (seconds < DURATION_BOUNDARY_SECONDS[1]) {
      quantity = Math.floor(seconds / DURATION_BOUNDARY_SECONDS[0]);
      attrIndex = 1;
    } else if (seconds < DURATION_BOUNDARY_SECONDS[2]) {
      quantity = Math.floor(seconds / DURATION_BOUNDARY_SECONDS[1]);
      attrIndex = 2;
    } else {
      quantity = Math.floor(seconds / DURATION_BOUNDARY_SECONDS[2]);
      attrIndex = 3;
    }
    var template = readout.getAttribute(DURATION_ATTRS[attrIndex]);
    if (!template) {
      readout.textContent = "";
      return;
    }
    readout.textContent = template.split(TEXT_TOKEN).join(String(quantity));
  }

  // Every readout for this wrapper's field, rewritten from its own
  // server-rendered template. A readout whose value equals its declared
  // base says nothing, since a sentence comparing a value with itself
  // would be noise. A readout with no READOUT_TEXT_ATTR falls back to
  // the duration path (DURATION_ATTRS) rather than being skipped.
  function paintReadouts(wrapper, value) {
    var name = wrapper.getAttribute(FIELD_ATTR);
    if (!name) {
      return;
    }
    var readouts = document.querySelectorAll(
      "[" + READOUT_ATTR + "=\"" + name + "\"]");
    for (var i = 0; i < readouts.length; i++) {
      var readout = readouts[i];
      var template = readout.getAttribute(READOUT_TEXT_ATTR);
      if (template === null) {
        paintDurationReadout(wrapper, readout);
        continue;
      }
      var base = numberOrNull(readout.getAttribute(READOUT_BASE_ATTR));
      if (base !== null && base === value) {
        readout.textContent = "";
        continue;
      }
      var quantity = isReadoutClockFormat(readout)
        ? minutesToClock(value)
        : String(readoutQuantity(readout, value));
      readout.textContent = template.split(TEXT_TOKEN).join(quantity);
    }
  }

  // The sweep, derived on the ancestor once both members of the pair
  // have published there.
  //
  // Read back off the ancestor's own style, never a cached number.
  // Members are found in document order (the server always emits the
  // start handle before the end handle). The +1 handles the wrap:
  // 23:00 -> 07:00 is start 0.9583, end 0.2917, so a plain subtraction
  // gives -0.6667, while (end - start + 1) % 1 correctly reads 0.3333.
  // Does nothing until both members have a readable number.
  function paintSweep(ancestor) {
    var sweepProperty = ancestor.getAttribute(PAIR_ATTR);
    if (!sweepProperty || !ancestor.style || !ancestor.style.setProperty) {
      return;
    }
    var members = ancestor.querySelectorAll("[" + PAIR_PROPERTY_ATTR + "]");
    if (members.length < 2) {
      return;
    }
    var startProperty = members[0].getAttribute(PAIR_PROPERTY_ATTR);
    var endProperty = members[1].getAttribute(PAIR_PROPERTY_ATTR);
    var start = numberOrNull(ancestor.style.getPropertyValue(startProperty));
    var end = numberOrNull(ancestor.style.getPropertyValue(endProperty));
    if (start === null || end === null) {
      return;
    }
    ancestor.style.setProperty(sweepProperty, String((end - start + 1) % 1));
  }

  function paint(wrapper, bounds, value) {
    // The announcing element is the one a visitor lands on: an explicit
    // handle first, then the native mirror, and the wrapper only when
    // neither exists — a wrapper holding aria-value* while something
    // inside it takes focus would announce a value that never changes.
    var announce = wrapper.querySelector("[" + HANDLE_ATTR + "]")
        || mirrorFor(wrapper) || wrapper;
    announce.setAttribute("aria-valuenow", String(value));
    var text = wrapper.getAttribute(TEXT_ATTR);
    if (text) {
      announce.setAttribute(
        "aria-valuetext", text.split(TEXT_TOKEN).join(numberToField(wrapper, value)));
    }
    // The mirror follows the field, never the other way round: written
    // here from the value just read back off the field, so typing into
    // the native input moves the slider for free.
    writeValue(mirrorFor(wrapper), numberToField(wrapper, value));
    paintReadouts(wrapper, value);
    if (wrapper.style && wrapper.style.setProperty) {
      var span = bounds.max - bounds.min;
      var fraction = (value - bounds.min) / span;
      wrapper.style.setProperty(FRACTION_PROPERTY, String(fraction));
      // Additive over the fraction write above; a wrapper with no pair
      // property is untouched. This is a separate fraction from
      // FRACTION_PROPERTY: that one divides by (max - min), reaching
      // max at a full turn, but for a wrapping/angular pair that would
      // be off by 1/(max - min) of a turn. Dividing by (max - min) + 1
      // instead treats bounds as an inclusive integer range, where the
      // value one step past max is min again — the correct wrap point
      // for a value a sweep is derived from.
      var pairProperty = wrapper.getAttribute(PAIR_PROPERTY_ATTR);
      if (pairProperty) {
        var pairAncestor = ancestorWith(wrapper, PAIR_ATTR);
        if (pairAncestor && pairAncestor.style && pairAncestor.style.setProperty) {
          var pairFraction = (value - bounds.min) / (span + 1);
          pairAncestor.style.setProperty(pairProperty, String(pairFraction));
          paintSweep(pairAncestor);
        }
      }
    }
  }

  // Entry point: clamp, round, write into the native input, wake the
  // save bar, paint. Returns the value actually written, or null when
  // this wrapper has no usable bounds or no field.
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
    if (writeValue(field, numberToField(wrapper, value))) {
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

  // Which wrapper, if any, this event belongs to. The guard clause
  // every listener below returns from on a page with no continuous-
  // value control, before reading or writing anything in the DOM.
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

  // A wrapper with a mirror is not steered from here: its native input
  // already implements this model, and a handler that both prevented
  // the default and stepped the value would move the control twice.
  function steeredHere(wrapper) {
    return wrapper && !mirrorFor(wrapper);
  }

  document.addEventListener("keydown", function (evt) {
    var wrapper = wrapperFor(evt.target);
    if (!steeredHere(wrapper)) {
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
  // track) begins a drag; setPointerCapture keeps subsequent moves
  // coming even when the pointer leaves the element.
  //
  // Security: a synthetic PointerEvent carries clientX/clientY of 0,0,
  // so steering from one would yank a real setting to whatever the
  // corner of the screen happens to be, from any script on the page.
  // Compared against false rather than negated, since a browser that
  // does not implement isTrusted leaves it undefined, and the negated
  // form would refuse every real drag rather than every fake one.
  function untrusted(evt) {
    return evt.isTrusted === false;
  }

  document.addEventListener("pointerdown", function (evt) {
    if (untrusted(evt)) {
      return;
    }
    var wrapper = wrapperFor(evt.target);
    // Load-bearing here: preventDefault() below cancels a native
    // range's own thumb drag, so without this the slider would be
    // immovable by pointer.
    if (!steeredHere(wrapper)) {
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
    if (!evt.buttons || untrusted(evt)) {
      return;
    }
    var wrapper = wrapperFor(evt.target);
    if (!steeredHere(wrapper)) {
      return;
    }
    evt.preventDefault();
    steerFromPointer(wrapper, evt.clientX, evt.clientY);
  });

  // Repaints from the native input for a write this file did not cause:
  // a visitor typing into the field, browser autofill, or (the live
  // case) dirty-state.js's quiet-hours preset buttons, which assign to
  // .value from script and fire no event at all. Reacting to the click
  // that triggers a preset is ordering-safe, since the preset's own
  // handler is bound to the button and has already run by the time the
  // click reaches document. Idempotent: the change event this file
  // sends after its own write finds the value already correct.
  function repaintAll() {
    var wrappers = document.querySelectorAll("[" + WRAPPER_ATTR + "]");
    for (var i = 0; i < wrappers.length; i++) {
      var bounds = boundsFor(wrappers[i]);
      if (bounds) {
        paint(wrappers[i], bounds, currentValue(wrappers[i], bounds));
      }
    }
  }

  // The sync: a repaint writes the mirror from the field; this writes
  // the field from the mirror, which is what a drag on a native range
  // has to do to reach the form. Goes through the same steer() as
  // every other path, so a dragged value clamps like a typed one.
  function onValueEvent(evt) {
    var target = evt.target;
    if (target && target.hasAttribute && target.hasAttribute(INPUT_ATTR)) {
      var wrapper = wrapperFor(target);
      if (wrapper) {
        // steer() paints, so returning here keeps the visitor's own
        // in-flight drag from being written back over mid-gesture.
        steer(wrapper, target.value);
        return;
      }
    }
    repaintAll();
  }

  document.addEventListener("change", onValueEvent);
  document.addEventListener("input", onValueEvent);
  document.addEventListener("click", repaintAll);

  // No DOMContentLoaded wrapper, and no load-time pass over the
  // document: the <script> tag carries defer, and every control's
  // initial position is already rendered by the server from the saved
  // value, so this file mutates nothing until a user touches a control.
  //
  // The one exception below writes no control state; it makes a
  // one-time environment check — does this browser's resolved hour
  // cycle unambiguously use 24-hour time — and only then hides the
  // normalised-time twins that exist to correct a browser whose native
  // <input type="time"> does not. Conservative by construction: since
  // Intl.DateTimeFormat's resolved hour12 measures the browser's
  // locale preference, not what this specific input will paint, every
  // uncertain case (no Intl, no resolvedOptions, anything but the
  // literal boolean false) leaves every twin exactly as visible as the
  // server rendered it.
  function hideNormalisedTimeTwinsIfUnambiguously24Hour() {
    try {
      if (!window.Intl || !window.Intl.DateTimeFormat) {
        return;
      }
      var formatter = new Intl.DateTimeFormat(undefined, { hour: "numeric" });
      if (!formatter.resolvedOptions) {
        return;
      }
      var resolved = formatter.resolvedOptions();
      if (resolved && resolved.hour12 === false) {
        var twins = document.querySelectorAll("[" + NORMALISED_TIME_ATTR + "]");
        for (var i = 0; i < twins.length; i++) {
          twins[i].hidden = true;
        }
      }
    } catch (err) {
      // A throw here must never break the rest of this file's own
      // initialisation (the listeners registered above) — this pass
      // makes a best-effort environment check, and its own failure is
      // itself an uncertain case, which this file's own rule already
      // says means: leave every twin visible.
    }
  }
  hideNormalisedTimeTwinsIfUnambiguously24Hour();

  // Exposes repaintAll() as a callable entry point: dirty-state.js's
  // Cancel handler calls it after a native reset event has restored
  // every field's value, since repaintAll() reads each wrapper's live
  // field value at call time. A small namespace object, matching
  // theme-preview.js's window.SkyPaneLivePreview and dirty-state.js's
  // window.SkyPaneDirtyState.
  window.SkyPaneValueControls = { repaintAll: repaintAll };
})();
