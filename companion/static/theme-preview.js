/*
 * SkyPane companion service — theme-preview.js.
 *
 * The Display page's look picker. Every look on the page (Departures,
 * Arrivals, Calendar flights, and a new special look) is a group of
 * native radios carrying real theme ids, inside a [data-look-target]
 * element; that table works with no script at all. This file adds:
 *
 * - live pictures: each target's [data-look-image] follows its checked
 *   radio, built from the server-rendered data-preview-src-template;
 * - the look sheet: clicking a picture or its "Change" control opens one
 *   shared dialog with three choices (colour, background, diagonal
 *   stripe). The server's data-look-model says which combinations are
 *   real themes and why the others are not; this file never decides
 *   that itself. A choice checks the matching theme radio and fires a
 *   change event, so dirty-state.js sees it like a click;
 * - the special look form page: the same three choices in the page and
 *   recent-key suggestions.
 *
 * No build step, ES5-safe subset. Never a network call, a timer, or an
 * HTML-writing DOM sink: writes are an <img> src/alt (from server
 * attributes), textContent, SVG fill attributes, classes, the hidden flag,
 * checked/disabled, and moving the sheet element.
 *
 * Exposes window.SkyPaneLivePreview.refresh(): dirty-state.js's Cancel
 * handler calls it after form.reset(), which restores every radio
 * natively but fires no change event.
 */
(function () {
  "use strict";

  // --- The section navigation -------------------------------------------
  // A thumb behind the current link. Each view is its own page, so the
  // thumb starts under the link of the page that was left (kept in
  // sessionStorage) and slides to the current one, unless the visitor
  // prefers reduced motion.
  var nav = document.querySelector("[data-pers-nav]");
  var NAV_KEY = "skypane-pers-nav";
  if (nav) {
    var thumb = nav.querySelector("[data-pers-thumb]");
    var navLinks = nav.querySelectorAll("[data-pers-view]");
    var currentLink = nav.querySelector("[aria-current]");
    var cl;
    var fromLink = null;
    var previous = null;
    try {
      previous = window.sessionStorage.getItem(NAV_KEY);
    } catch (err) {
      previous = null;
    }
    for (cl = 0; cl < navLinks.length; cl++) {
      if (navLinks[cl].getAttribute("data-pers-view") === previous) {
        fromLink = navLinks[cl];
      }
    }
    var placeThumb = function (link) {
      // The pill sits 3px inside its segment, like the label's own box.
      thumb.style.width = (link.offsetWidth - 6) + "px";
      thumb.style.transform = "translateX(" + (link.offsetLeft + 3) + "px)";
    };
    if (thumb && currentLink) {
      nav.className += " is-enhanced";
      var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      placeThumb(fromLink && !calm ? fromLink : currentLink);
      if (fromLink && fromLink !== currentLink && !calm) {
        // Read the layout so the start position is painted first.
        thumb.getBoundingClientRect();
        thumb.className += " is-sliding";
        placeThumb(currentLink);
      }
      try {
        window.sessionStorage.setItem(NAV_KEY, currentLink.getAttribute("data-pers-view"));
      } catch (err) {
        // The slide start is only a nicety.
      }
    }
  }

  var sheet = document.querySelector("[data-look-sheet]");
  if (!sheet) {
    return;
  }
  var model;
  try {
    model = JSON.parse(sheet.getAttribute("data-look-model"));
  } catch (err) {
    return;
  }
  var scrim = document.querySelector("[data-look-scrim]");
  // The Look page's picker sits in the page: no dialog, no focus trap.
  var inline = sheet.hasAttribute("data-look-inline");
  var targets = document.querySelectorAll("[data-look-target]");
  var THEME_TOKEN = "__THEME__";
  var SENTENCE_TOKEN = "__LOOK__";
  // Matches style.css's phone breakpoint, where the sheet is a bottom sheet.
  var PHONE_QUERY = "(max-width: 699.98px)";

  function addClass(el, name) {
    if ((" " + el.className + " ").indexOf(" " + name + " ") === -1) {
      el.className = (el.className ? el.className + " " : "") + name;
    }
  }

  function removeClass(el, name) {
    el.className = (" " + el.className + " ").replace(" " + name + " ", " ")
      .replace(/^\s+|\s+$/g, "");
  }

  function ancestorWith(node, attr, stop) {
    while (node && node !== stop && node.getAttribute) {
      if (node.hasAttribute(attr)) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  function targetFor(usage) {
    var i;
    for (i = 0; i < targets.length; i++) {
      if (targets[i].getAttribute("data-look-usage") === usage) {
        return targets[i];
      }
    }
    return null;
  }

  function fieldRadios(target) {
    var field = target.getAttribute("data-look-field");
    var all = target.querySelectorAll('input[type="radio"]');
    var out = [];
    var i;
    for (i = 0; i < all.length; i++) {
      if (all[i].name === field) {
        out.push(all[i]);
      }
    }
    return out;
  }

  function checkedValue(target) {
    var radios = fieldRadios(target);
    var i;
    for (i = 0; i < radios.length; i++) {
      if (radios[i].checked) {
        return radios[i].value;
      }
    }
    return null;
  }

  // The theme a target's picture shows: its own checked theme, or the
  // look it follows ("same as departures") when its value is empty.
  function effectiveTheme(target) {
    var value = checkedValue(target);
    if (value && model.axes[value]) {
      return value;
    }
    var follows = target.getAttribute("data-look-follows");
    var other = follows ? targetFor(follows) : null;
    if (other) {
      return effectiveTheme(other);
    }
    // A page without a departures look carries the saved one.
    var carried = target.getAttribute("data-look-follows-theme");
    return carried && model.axes[carried] ? carried : null;
  }

  function renderTarget(target) {
    var theme = effectiveTheme(target);
    if (!theme) {
      return;
    }
    var value = checkedValue(target);
    var sentence = (value === "" && target.getAttribute("data-look-same-label"))
      || model.sentences[theme];
    var src = target.getAttribute("data-preview-src-template").split(THEME_TOKEN).join(theme);
    var images = target.querySelectorAll("[data-look-image]");
    var i;
    for (i = 0; i < images.length; i++) {
      if (images[i].getAttribute("src") !== src) {
        images[i].setAttribute("src", src);
      }
      var altTemplate = images[i].getAttribute("data-look-alt-template");
      if (altTemplate) {
        images[i].setAttribute("alt", altTemplate.split(SENTENCE_TOKEN).join(sentence));
      }
    }
    var sentences = target.querySelectorAll("[data-look-sentence]");
    for (i = 0; i < sentences.length; i++) {
      sentences[i].textContent = sentence;
    }
  }

  function renderAll() {
    var i;
    for (i = 0; i < targets.length; i++) {
      renderTarget(targets[i]);
    }
  }

  function fireChange(input) {
    var evt = document.createEvent("HTMLEvents");
    evt.initEvent("change", true, false);
    input.dispatchEvent(evt);
  }

  // Checks the target's radio for value and announces it the way a
  // click would, so the save bar and every picture follow.
  function setValue(target, value) {
    var radios = fieldRadios(target);
    var i;
    for (i = 0; i < radios.length; i++) {
      if (radios[i].value === value && !radios[i].checked) {
        radios[i].checked = true;
        fireChange(radios[i]);
        return;
      }
    }
    renderAll();
  }

  function cellKey(colour, background, stripe) {
    return colour + "|" + background + "|" + stripe;
  }

  // One set of the three choices, bound to whichever target getTarget()
  // returns. A choice with no theme is disabled, greyed and explained, never
  // removed: the stripe row is always there, and the colour row greys out
  // while the look is plain white paper (a colour changes nothing there).
  function bindAxes(container, getTarget) {
    var state = { colour: "black", background: "paper", stripe: "none" };
    var why = container.querySelector("[data-look-why]");
    var colourName = container.querySelector("[data-look-colour-name]");
    var colourWhy = container.querySelector("[data-look-colour-why]");

    function radios(axis) {
      return container.querySelectorAll('input[data-look-axis="' + axis + '"]');
    }

    function paintAxis(axis) {
      var list = radios(axis);
      var i;
      for (i = 0; i < list.length; i++) {
        list[i].checked = list[i].value === state[axis];
      }
    }

    function paintStripes() {
      var list = radios("stripe");
      var reasons = [];
      var i;
      for (i = 0; i < list.length; i++) {
        var key = cellKey(state.colour, state.background, list[i].value);
        var missing = !model.cells[key];
        list[i].disabled = missing;
        if (missing) {
          addClass(list[i].parentNode, "is-disabled");
          var reason = model.reasons[key];
          if (reason && reasons.indexOf(reason) === -1) {
            reasons.push(reason);
          }
        } else {
          removeClass(list[i].parentNode, "is-disabled");
        }
      }
      why.textContent = reasons.join(" ");
    }

    function paintColours() {
      var list = radios("colour");
      var plain = state.background === "paper" && state.stripe === "none";
      var i;
      for (i = 0; i < list.length; i++) {
        list[i].disabled = plain;
        if (plain) {
          addClass(list[i].parentNode, "is-disabled");
        } else {
          removeClass(list[i].parentNode, "is-disabled");
        }
      }
      colourWhy.textContent = plain ? model.colourReason : "";
    }

    function paintIcons() {
      var icons = container.querySelectorAll("[data-look-bg-icon]");
      var i;
      for (i = 0; i < icons.length; i++) {
        var kind = icons[i].getAttribute("data-look-bg-icon");
        icons[i].setAttribute("fill", kind === "paper" ? model.paper : model.colours[state.colour]);
        icons[i].setAttribute("fill-opacity", kind === "soft" ? model.softOpacity : "1");
      }
    }

    function paint() {
      paintAxis("colour");
      paintAxis("background");
      paintAxis("stripe");
      paintStripes();
      paintColours();
      paintIcons();
      var plain = state.background === "paper" && state.stripe === "none";
      colourName.textContent = plain ? "" : model.colourNames[state.colour];
    }

    function load(theme) {
      var axes = model.axes[theme];
      if (!axes) {
        return;
      }
      if (axes[0]) {
        state.colour = axes[0];
      }
      state.background = axes[1];
      state.stripe = axes[2];
      paint();
    }

    container.addEventListener("change", function (evt) {
      var input = evt.target;
      var axis = input && input.getAttribute ? input.getAttribute("data-look-axis") : null;
      if (!axis) {
        return;
      }
      state[axis] = input.value;
      if (!model.cells[cellKey(state.colour, state.background, state.stripe)]) {
        state.stripe = "none";
      }
      paint();
      var target = getTarget();
      if (target) {
        setValue(target, model.cells[cellKey(state.colour, state.background, state.stripe)]);
      }
    });

    return { load: load };
  }

  function focusables(root) {
    var all = root.querySelectorAll("button, input, summary, [href]");
    var out = [];
    var i;
    for (i = 0; i < all.length; i++) {
      if (!all[i].disabled && all[i].getClientRects().length) {
        out.push(all[i]);
      }
    }
    return out;
  }

  // Tab and Shift+Tab wrap inside an open dialog.
  function trapTab(evt, root) {
    if (evt.key !== "Tab") {
      return;
    }
    var list = focusables(root);
    if (!list.length) {
      return;
    }
    var first = list[0];
    var last = list[list.length - 1];
    if (evt.shiftKey && document.activeElement === first) {
      evt.preventDefault();
      last.focus();
    } else if (!evt.shiftKey && document.activeElement === last) {
      evt.preventDefault();
      first.focus();
    }
  }

  // --- The look sheet ---------------------------------------------------

  var current = null;
  var opener = null;
  var initialValue = null;
  var sheetTitle = sheet.querySelector("[data-look-sheet-title]");
  var sameRow = sheet.querySelector("[data-look-same-row]");
  var same = sheet.querySelector("[data-look-same]");
  var sameNote = sheet.querySelector("[data-look-same-note]");
  var sheetAxesBox = sheet.querySelector("[data-look-axes]");
  var sheetAxes = bindAxes(sheetAxesBox, function () { return current; });

  function setAxesDisabled(disabled) {
    var sets = sheetAxesBox.querySelectorAll("fieldset");
    var i;
    for (i = 0; i < sets.length; i++) {
      sets[i].disabled = disabled;
    }
  }

  function syncSheet() {
    if (!current) {
      return;
    }
    var follows = current.getAttribute("data-look-follows");
    if (inline) {
      sameRow.hidden = !follows;
    }
    var following = !!follows && checkedValue(current) === "";
    same.setAttribute("aria-checked", following ? "true" : "false");
    setAxesDisabled(following);
    // Following departures there is nothing to choose: the controls are hidden, not dimmed.
    sheetAxesBox.hidden = following;
    sameNote.hidden = !following;
    sheetAxes.load(effectiveTheme(current));
  }

  function closeSheet(restoreFocus) {
    if (!current || inline) {
      return;
    }
    sheet.hidden = true;
    scrim.hidden = true;
    removeClass(current, "is-editing");
    var from = opener;
    current = null;
    opener = null;
    if (restoreFocus && from) {
      from.focus();
    }
  }

  function openSheet(target, from) {
    closeSheet(false);
    current = target;
    opener = from;
    initialValue = checkedValue(target);
    sheetTitle.textContent = target.getAttribute("data-look-title");
    sameRow.hidden = !target.getAttribute("data-look-follows");
    var anchor = target.hasAttribute("data-look-anchor")
      ? target : target.querySelector("[data-look-anchor]");
    anchor.appendChild(sheet);
    sheet.className = "look-sheet look-sheet--" + target.getAttribute("data-look-usage");
    addClass(target, "is-editing");
    syncSheet();
    sheet.hidden = false;
    scrim.hidden = false;
    // On a phone the sheet covers the lower half of the screen: bring the
    // picture it changes to the top, so every choice is seen to land.
    if (window.matchMedia && window.matchMedia(PHONE_QUERY).matches) {
      var picture = target.querySelector("[data-look-image]");
      if (picture && picture.scrollIntoView) {
        picture.scrollIntoView({ block: "start" });
      }
    }
    var start = sheet.querySelector('input[data-look-axis="colour"]:checked:not(:disabled)')
      || sheet.querySelector("[data-look-close]");
    start.focus({ preventScroll: true });
    // Beside the page a popover can open below the fold: bring it into view.
    if (!(window.matchMedia && window.matchMedia(PHONE_QUERY).matches) && sheet.scrollIntoView) {
      sheet.scrollIntoView({ block: "nearest" });
    }
  }

  function sameIsOn() {
    return same.getAttribute("aria-checked") === "true";
  }

  same.addEventListener("click", function () {
    if (!current) {
      return;
    }
    if (!sameIsOn()) {
      setValue(current, "");
    } else {
      setValue(current, effectiveTheme(current));
    }
    syncSheet();
  });

  // The dialog's own footer. The inline picker has none: the page's save bar
  // saves, and its Cancel restores every look to the saved value.
  var resetButton = sheet.querySelector("[data-look-reset]");
  if (resetButton) {
    resetButton.addEventListener("click", function () {
      if (current && initialValue !== null) {
        setValue(current, initialValue);
        syncSheet();
      }
    });
  }
  var doneButton = sheet.querySelector("[data-look-done]");
  if (doneButton) {
    doneButton.addEventListener("click", function () {
      closeSheet(true);
    });
  }
  sheet.querySelector("[data-look-close]").addEventListener("click", function () {
    closeSheet(true);
  });
  sheet.addEventListener("keydown", function (evt) {
    if (inline) {
      return;
    }
    if (evt.key === "Escape") {
      evt.preventDefault();
      closeSheet(true);
      return;
    }
    trapTab(evt, sheet);
  });

  // A picture's overlay button and its "Change" summary both open the
  // sheet; preventing the summary's default keeps its table closed.
  document.addEventListener("click", function (evt) {
    var trigger = ancestorWith(evt.target, "data-look-open", null);
    if (!trigger || inline) {
      return;
    }
    var target = ancestorWith(trigger, "data-look-target", null);
    if (!target) {
      return;
    }
    evt.preventDefault();
    openSheet(target, trigger);
  });

  // --- The special look form page -----------------------------------------

  var addForm = document.querySelector("[data-special-form]");

  function showSuggestions() {
    var box = addForm.querySelector("[data-rule-suggestions]");
    if (!box) {
      return;
    }
    var kind = addForm.querySelector('input[name="rule_kind"]:checked');
    var groups = box.querySelectorAll(".rule-suggestions__group");
    var any = false;
    var i;
    for (i = 0; i < groups.length; i++) {
      groups[i].hidden = !kind || groups[i].getAttribute("data-kind") !== kind.value;
      any = any || !groups[i].hidden;
    }
    box.hidden = !any;
  }

  if (addForm) {
    var axesHost = addForm.querySelector("[data-look-axes-host]");
    var tableHost = addForm.querySelector("[data-look-table-host]");
    var addAxes = bindAxes(axesHost.querySelector("[data-look-axes]"), function () { return addForm; });
    axesHost.hidden = false;
    tableHost.hidden = true;
    addAxes.load(effectiveTheme(addForm));
    showSuggestions();

    addForm.addEventListener("change", function (evt) {
      if (evt.target && evt.target.name === "rule_kind") {
        // A key typed for one kind is not valid for another: start again.
        var key = addForm.querySelector('input[name="rule_key"]');
        key.value = "";
        key.setCustomValidity("");
        key.removeAttribute("aria-invalid");
        showSuggestions();
      }
    });
    addForm.addEventListener("click", function (evt) {
      var chip = ancestorWith(evt.target, "data-value", addForm);
      if (!chip) {
        return;
      }
      var key = addForm.querySelector('input[name="rule_key"]');
      key.value = chip.getAttribute("data-value");
      key.focus();
    });
  }

  // --- Shared wiring ------------------------------------------------------

  scrim.addEventListener("click", function () {
    closeSheet(true);
  });

  // Focus that leaves an open dialog (a click elsewhere, an assistive
  // technology jump) is brought back into it.
  document.addEventListener("focusin", function (evt) {
    if (current && !inline && !sheet.contains(evt.target)) {
      var list = focusables(sheet);
      if (list.length) {
        list[0].focus();
      }
    }
  });

  document.addEventListener("change", function (evt) {
    var input = evt.target;
    if (input && input.type === "radio" && ancestorWith(input, "data-look-target", null)) {
      renderAll();
      if (current && current.contains(input)) {
        syncSheet();
      }
    }
  });

  var openers = document.querySelectorAll("button[data-look-open]");
  var o;
  for (o = 0; !inline && o < openers.length; o++) {
    openers[o].hidden = false;
  }

  // --- The look views: the one picture of the type the address names ---

  var panels = document.querySelectorAll("[data-look-panel]");

  function showUsage(usage) {
    var i;
    for (i = 0; i < panels.length; i++) {
      panels[i].hidden = panels[i].getAttribute("data-look-panel") !== usage;
    }
    current = targetFor(usage);
    syncSheet();
  }

  if (inline) {
    var lookView = document.querySelector("[data-look-initial]");
    showUsage(lookView ? lookView.getAttribute("data-look-initial") : "departures");
  }

  window.SkyPaneLivePreview = {
    refresh: function () {
      renderAll();
      syncSheet();
      if (addForm) {
        addAxes.load(effectiveTheme(addForm));
      }
    }
  };

  renderAll();
})();
