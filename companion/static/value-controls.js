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
 *      to a .value in it — writeValue(), the single write helper — and
 *      every read of the control's current state is a read of the
 *      native input the form posts. There is no parallel state anywhere
 *      here: no map keyed by element, no cached number, nothing to fall
 *      out of step.
 *
 *      25-05 gave that helper a SECOND call site and it is worth being
 *      precise about why it is not a second source of truth. A wrapper
 *      may declare a MIRROR — another native control holding the same
 *      value and posting nothing at all (a range input with no name).
 *      The mirror is written only inside paint(), from the value just
 *      read back off the field, so it is strictly downstream: the field
 *      is what the form posts, what this file reads, and what the
 *      server rendered. The mirror can no more disagree with it than a
 *      painted handle position can.
 *   2. This file never renders an affordance. An affordance that cannot
 *      work without script lives inside companion/static/style.css's
 *      .js-gated wrapper, which HIDES by default and reveals under
 *      .js — so with scripts blocked the handle is not merely
 *      invisible, it is out of the layout and out of the tab order.
 *   3. This file writes no copy. aria-valuetext is filled from a
 *      SERVER-RENDERED, already-translated template on the wrapper; if
 *      no template is there, no aria-valuetext is written at all and
 *      the numeric aria-valuenow stands alone. The same rule governs
 *      25-05's READOUTS — the sentences beside a control that restate
 *      what its value MEANS: the wording is a translated template the
 *      server put in an attribute, and this file substitutes one number
 *      into it and writes nothing else. A French reader can therefore
 *      never be dropped into English by touching a control.
 *
 *      THE HONESTY COROLLARY, because this is the one place it could be
 *      quietly lost. 25-05's battery gauge prints an absolute
 *      "days left" figure only when the device's OWN observed history
 *      supports one, and that sentence is rendered by the server,
 *      OUTSIDE every readout, and never touched here. What a readout
 *      holds is a statement about the two CADENCES, which is arithmetic
 *      on the value itself. If the server declined to state a figure,
 *      nothing in this file can invent one — not by policy, but because
 *      no template here contains one.
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
 * any kind. It writes attributes, one custom property, one input value
 * through one helper, and the text of readouts whose wording the server
 * wrote — and nothing else.
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
  // THE MIRROR — 25-05-PLAN.md Task 2 (CFG-49/CFG-52), and the third
  // and last way this file's consumers differ from one another.
  //
  // A NATIVE control inside the wrapper holding the same value as the
  // field and posting NOTHING (25-05's <input type="range"> carries no
  // "name" attribute, so it cannot submit and can never become a second
  // source of truth). It is not a second value: it is repainted FROM
  // the field on every paint, and the field is the only thing read back.
  //
  // A WRAPPER WITH A MIRROR TAKES NO GESTURES FROM THIS FILE AT ALL.
  // The three listeners at the bottom stand aside for it, and that is
  // load-bearing rather than tidy: preventDefault() on a pointerdown
  // over a native range CANCELS the browser's own thumb drag, and a
  // keydown that both prevents the default and steps the value moves
  // the control twice per arrow press. A native range already has this
  // file's exact keyboard model, its own aria-valuenow and its own
  // touch handling; the job here is to SYNC, never to steer.
  var INPUT_ATTR = "data-value-input";
  // THE READOUTS — an element whose whole text is a sentence ABOUT the
  // value. Found by the FIELD's name rather than by containment,
  // because a readout is deliberately NOT inside the wrapper: the
  // wrapper is gated (it cannot work without script) and the readouts
  // are not (they have to be correct with scripts blocked).
  //
  // The sentence is a SERVER-RENDERED, already-translated template with
  // TEXT_TOKEN standing in for the number, exactly like the
  // aria-valuetext template above and for the identical reason: this
  // file writes no copy. It substitutes one number and nothing else.
  //
  // AND IT CAN NEVER BECOME BRAVER THAN THE SERVER WAS. This is the one
  // place the honesty rule of 25-05's battery gauge could be quietly
  // lost, so it is stated here: the sentence that carries an absolute
  // battery figure is rendered by the SERVER, outside every readout,
  // and is never touched by this file. What a readout holds is only
  // ever a statement about the two CADENCES — arithmetic on the value
  // itself. If the server declined to print a days figure (because this
  // device's observed history does not support one), nothing here can
  // invent it, because nothing here has a template containing one.
  var READOUT_ATTR = "data-value-readout";
  var READOUT_TEXT_ATTR = "data-value-readout-text";
  var READOUT_SCALE_ATTR = "data-value-readout-scale";
  var READOUT_BASE_ATTR = "data-value-readout-base";
  var MINUTES_PER_HOUR = 60;
  var HOURS_PER_DAY = 24;
  var CLOCK_RE = /^(\d{1,2}):(\d{2})$/;

  // The painted position, as a 0..1 fraction, handed to the stylesheet
  // as a custom property so every bit of geometry stays in the CSS.
  var FRACTION_PROPERTY = "--value-fraction";

  // THE PAIR SEAM — 27-02-PLAN.md Task 1 (CFG-62). Every wrapper above
  // models ONE value; an arc and a caption sentence are functions of
  // BOTH ends of a window, and until this seam existed there was no
  // element in this file's model for a pair to live on at all — two
  // handles could each be independently correct while nothing was a
  // function of the two of them together, which is exactly how a
  // correct pair of fields shipped a lying arc.
  //
  // PAIR_ATTR marks the shared ancestor two wrappers publish onto. Its
  // OWN VALUE is the name of the DERIVED SWEEP property this file
  // writes there once both members have published — not a fixed
  // constant, because the sweep's name is a server decision like every
  // other property name this file only ever reads, never invents.
  //
  // PAIR_PROPERTY_ATTR, on a wrapper, names which of the ancestor's
  // properties is THAT wrapper's own fraction. A wrapper carrying
  // neither attribute is untouched by any of this — the pair seam is
  // strictly additive over the fraction write above.
  var PAIR_ATTR = "data-value-pair";
  var PAIR_PROPERTY_ATTR = "data-value-pair-property";

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
  // The mirror this wrapper declares, or null. Queried every time for
  // the same reason fieldFor() is: a cache would be state this file is
  // forbidden to hold.
  function mirrorFor(wrapper) {
    return wrapper.querySelector("[" + INPUT_ATTR + "]");
  }

  // THE ONLY PLACE IN THIS FILE THAT ASSIGNS TO A .value, and both of
  // its callers go through it: the write into the native input the form
  // posts (steer, below) and the write into the mirror that posts
  // nothing (paint, below). Returns whether anything actually changed,
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
  // declares, ROUNDED UP, because every consumer of this seam states a
  // BOUND ("at most 2 min" is true of a 90-second cadence and "at most
  // 1 min" is false). No scale, no division.
  function readoutQuantity(readout, value) {
    var scale = numberOrNull(readout.getAttribute(READOUT_SCALE_ATTR));
    if (scale === null || scale <= 0) {
      return value;
    }
    return Math.ceil(value / scale);
  }

  // Every readout for this wrapper's field, rewritten from its own
  // server-rendered template. A readout whose value equals its declared
  // base says NOTHING — that is the state every page load renders, and
  // a sentence comparing a value with itself would be noise.
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
        continue;
      }
      var base = numberOrNull(readout.getAttribute(READOUT_BASE_ATTR));
      if (base !== null && base === value) {
        readout.textContent = "";
        continue;
      }
      readout.textContent = template.split(TEXT_TOKEN).join(
        String(readoutQuantity(readout, value)));
    }
  }

  // THE SWEEP, DERIVED ON THE ANCESTOR ONCE BOTH MEMBERS OF THE PAIR
  // HAVE PUBLISHED THERE — 27-02-PLAN.md Task 1 (CFG-62).
  //
  // Read back off the ANCESTOR'S OWN STYLE, never a cached number: the
  // same "never a cached number" rule every other read in this file
  // follows, and the reason there is still no parallel state after this
  // seam exists. Members are found in DOCUMENT ORDER, which is
  // publication order — quiet_dial_handles_html()'s own comment states
  // the server always emits the start handle before the end handle, so
  // the first wrapper this ancestor contains carrying
  // PAIR_PROPERTY_ATTR is always the start of the pair and the second
  // is always the end.
  //
  // THE +1 IS THE WRAP, AND IT IS THE WHOLE REASON THIS IS NOT A PLAIN
  // SUBTRACTION. 23:00 -> 07:00 is start 0.9583, end 0.2917: end - start
  // is -0.6667, which is not a sweep at all, and (end - start + 1) % 1
  // reads it correctly as 0.3333 — the eight hours forward through
  // midnight this control has always drawn.
  //
  // Silently does nothing until both members have a readable number on
  // the ancestor (an unset custom property reads back as "", and
  // numberOrNull("") is null) — there is no invented sweep for half a
  // pair, matching this file's total-by-construction discipline
  // elsewhere.
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
    // THE ANNOUNCING ELEMENT IS THE ONE A VISITOR LANDS ON: an explicit
    // handle first, then the native mirror (which IS the focusable
    // control when there is one), and the wrapper only when there is
    // neither. A wrapper holding aria-value* while something inside it
    // takes the focus announces a value that never changes.
    var announce = wrapper.querySelector("[" + HANDLE_ATTR + "]")
        || mirrorFor(wrapper) || wrapper;
    announce.setAttribute("aria-valuenow", String(value));
    var text = wrapper.getAttribute(TEXT_ATTR);
    if (text) {
      announce.setAttribute(
        "aria-valuetext", text.split(TEXT_TOKEN).join(numberToField(wrapper, value)));
    }
    // THE MIRROR FOLLOWS THE FIELD, NEVER THE OTHER WAY ROUND. It is
    // written here, in the paint, from the value just read back off the
    // field — so typing into the native input moves the slider for
    // free, and the slider can never hold a value the field does not.
    writeValue(mirrorFor(wrapper), numberToField(wrapper, value));
    paintReadouts(wrapper, value);
    if (wrapper.style && wrapper.style.setProperty) {
      var span = bounds.max - bounds.min;
      var fraction = (value - bounds.min) / span;
      wrapper.style.setProperty(FRACTION_PROPERTY, String(fraction));
      // THE PAIR SEAM'S OWN WRITE. Additive over the fraction write
      // above: a wrapper that declares no pair property is untouched
      // from here on, and behaves exactly as it did before this task.
      //
      // A SEPARATE FRACTION, NOT THE ONE JUST WRITTEN ABOVE — found by
      // Task 4's own agreement check, which decodes the arc back to an
      // exact minute and caught this disagreeing by one. FRACTION_PROPERTY
      // above is deliberately (value - min) / (max - min), matching
      // quiet_dial_handle_fraction()'s own documented choice to make the
      // control's MAXIMUM reachable at a full visual turn. For a
      // wrapping/angular pair that fraction is off by exactly
      // 1 / (max - min) of a turn — under a quarter of a degree, which is
      // invisible on a painted handle and exactly enough to round a
      // decoded minute to its neighbour (1380/1439 of a turn decodes to
      // minute 1381, not 1380). The pair fraction instead divides by
      // (max - min) + 1: bounds are an INCLUSIVE range of integers, so the
      // value one step past max is min again, and that wrap point — not
      // max itself — is what one full turn must mean for a value a sweep
      // gets derived from. This is exactly QUIET_WINDOW_MINUTES_PER_DAY
      // (1440) for the quiet-hours dial, reached with no knowledge of
      // that constant at all.
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

  // A WRAPPER WITH A MIRROR IS NOT STEERED FROM HERE. Its native input
  // already implements exactly this model, and a handler that both
  // prevented the default AND stepped the value would move the control
  // twice on every arrow press. The mirror's own change/input event
  // reaches the sync path below instead.
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
  // track) begins a drag; setPointerCapture keeps the subsequent moves
  // coming even when the pointer leaves the element, which is what
  // makes a drag that overshoots the end behave like a native one.
  // A SYNTHETIC POINTER EVENT IS NOT A GESTURE, AND THIS GUARD IS NOT
  // TEST SCAFFOLDING. An el.dispatchEvent(new PointerEvent("pointerdown"))
  // carries clientX/clientY of 0,0 — the top-left corner of the viewport
  // — so steering from one yanks a real, saved setting to whatever angle
  // the corner of the screen happens to be at, from any script on the
  // page. Measured on this tree: companion/test_browser_ux.py's pointer
  // recorder proves itself alive by dispatching exactly that event, and
  // it moved the quiet window by half an hour while doing it.
  //
  // Compared against false rather than negated, deliberately: a browser
  // that does not implement the property leaves it undefined, and the
  // negated form would then refuse every real drag rather than every
  // fake one.
  function untrusted(evt) {
    return evt.isTrusted === false;
  }

  document.addEventListener("pointerdown", function (evt) {
    if (untrusted(evt)) {
      return;
    }
    var wrapper = wrapperFor(evt.target);
    // The mirror guard again, and here it is the load-bearing one:
    // preventDefault() below cancels a native range's own thumb drag
    // outright, so without this the slider would be immovable by
    // pointer while every string comparison in every harness stayed
    // green.
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

  // THE ONE THING THIS FILE LISTENS FOR THAT IT DID NOT CAUSE, and it
  // is what makes "this control holds no value" true rather than merely
  // claimed.
  //
  // The painted position is read off the native input. So when SOMETHING
  // ELSE writes into that input, the handle has to follow, or it shows a
  // value that is no longer there while the field beside it shows the
  // real one. Three writers exist today and none of them is this file:
  // a visitor typing into the field, a browser autofill, and — the live
  // case — companion/static/dirty-state.js's quiet-hours preset buttons.
  //
  // THE PRESET IS WHY THE CLICK LISTENER IS HERE AND NOT ONLY THE OTHER
  // TWO. Assigning to .value from script fires NO event of any kind, so
  // a preset that fills both time inputs is completely silent; measured
  // on this tree, clicking "Work day" moved both inputs and left both
  // handles exactly where they were. Reacting to the click instead is
  // ordering-safe by the DOM's own event model rather than by luck: the
  // preset's handler is bound to the BUTTON, so it has already run by
  // the time the click reaches document. And it is generic — this file
  // learns nothing about presets, only that a click is a moment after
  // which an input it paints from may hold something new.
  //
  // IT REPAINTS AND NEVER WRITES. The change event this file sends after
  // its own write reaches here, finds the value already correct, and
  // stops. There is no loop to guard against because there is no second
  // write — and re-reading a value this file does not own is idempotent
  // by construction.
  //
  // Delegated at document level, and on a page with no continuous-value
  // control (which is most of them) it costs one selector query that
  // matches nothing.
  function repaintAll() {
    var wrappers = document.querySelectorAll("[" + WRAPPER_ATTR + "]");
    for (var i = 0; i < wrappers.length; i++) {
      var bounds = boundsFor(wrappers[i]);
      if (bounds) {
        paint(wrappers[i], bounds, currentValue(wrappers[i], bounds));
      }
    }
  }

  // THE SYNC, AND IT IS THE ONE DIRECTION THE REPAINT ABOVE CANNOT DO.
  // A repaint writes the mirror FROM the field; this writes the field
  // from the mirror, which is what a drag on a native range has to do
  // to reach the form at all. It is the same steer() every other path
  // goes through — one clamp, one write, one notification, one paint —
  // so a value dragged past the end is clamped exactly as a typed one
  // is, and the save bar wakes the same way.
  function onValueEvent(evt) {
    var target = evt.target;
    if (target && target.hasAttribute && target.hasAttribute(INPUT_ATTR)) {
      var wrapper = wrapperFor(target);
      if (wrapper) {
        // steer() paints, so there is nothing left for the repaint to
        // do — and returning here is what keeps the visitor's own
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
  // document either. The <script> tag companion/layout.py's
  // page_shell() emits carries defer, so this file only runs after
  // parsing; and the INITIAL position of every control is rendered by
  // the server, from the saved value, so there is nothing to
  // initialise. That is not an omission — it is what makes the
  // scripts-blocked rendering correct rather than merely present, and
  // it is why this file mutates absolutely nothing until a user
  // touches a control that exists.
})();
