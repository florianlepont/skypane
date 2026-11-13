/*
 * SkyPane companion service — modal.js.
 *
 * Upgrades the shared dialog.modal component (companion/ui_modal.py) and
 * closes the open row menus and the frame popover. No build step, ES5-safe
 * subset. Served by companion/app.py's MODAL_SCRIPT_ROUTE. No network call,
 * no HTML-writing sink: attribute and class changes, focus, the native
 * dialog methods and, for the phone's drag-to-close, the dialog's own
 * transform set through the CSSOM (never a style attribute in the markup)
 * with one short fallback timer.
 *
 * Scripts blocked, a dialog still works: a [data-modal-open] link is a hash
 * link to it, the stylesheet shows the targeted (or server-rendered open)
 * dialog as an in-page card, and its close and dismiss links are plain
 * links to the host page. This file only adds the modal presentation, focus
 * return, Esc and backdrop dismissal.
 */
(function () {
  "use strict";

  var opener = null;
  // The opener's hash target, kept so the link can be found again when a
  // background refresh replaced the opener while the dialog was open.
  var openerHref = "";
  // The open menus Escape and an outside tap close: row menus and the frame
  // button's popover, and the phone More sheet.
  var MENU_SELECTOR =
    "details.row-menu[open], details.frame-menu[open], details.tab-bar__more[open]";
  var HOLD_SELECTOR = "input:not([type=hidden]), select, textarea";

  function closestTag(node, tag) {
    var el = node;
    while (el && el.nodeType === 1) {
      if (el.nodeName.toLowerCase() === tag) {
        return el;
      }
      el = el.parentNode;
    }
    return null;
  }

  // The menu a link sits in: its closest <details>.
  function closestMenu(node) {
    return closestTag(node, "details");
  }

  function hasAttr(node, name) {
    return node && node.nodeType === 1 && node.hasAttribute(name);
  }

  function closestWithAttr(node, name) {
    var el = node;
    while (el && el.nodeType === 1) {
      if (el.hasAttribute(name)) {
        return el;
      }
      el = el.parentNode;
    }
    return null;
  }

  function isModalDialog(el) {
    return !!el && el.nodeName.toLowerCase() === "dialog" &&
      el.classList.contains("modal") && typeof el.showModal === "function";
  }

  // The address without the fragment that targeted the dialog, so a
  // reload does not reopen it.
  function clearHash() {
    if (window.location.hash &&
        window.history && typeof window.history.replaceState === "function") {
      window.history.replaceState(
        null, "", window.location.pathname + window.location.search);
    }
  }

  // The last input kind, so focus handed back after a dialog closes shows
  // the focus ring only for keyboard users.
  var lastInputWasKeyboard = false;
  document.addEventListener("keydown", function () {
    lastInputWasKeyboard = true;
  }, true);
  document.addEventListener("pointerdown", function () {
    lastInputWasKeyboard = false;
  }, true);

  // Where focus goes when a dialog closes: the link that opened it, its
  // row menu's button when the menu has closed, else the page heading
  // (after a reload there is no opener) unless the dialog names a control.
  function returnFocus(dialog) {
    var target = opener;
    var href = openerHref;
    opener = null;
    openerHref = "";
    if (target && !document.body.contains(target) && href) {
      target = document.querySelector('a[data-modal-open][href="' + href + '"]');
    }
    if (!target && dialog) {
      // A dialog the address opened names the control it came from.
      var named = dialog.getAttribute("data-modal-return-focus");
      target = named ? document.getElementById(named) : null;
    }
    if (target && document.body.contains(target)) {
      var menu = closestMenu(target);
      if (menu && !menu.open) {
        target = menu.querySelector("summary") || target;
      }
      // A dialog closed by pointer or touch hands focus back without the
      // keyboard ring; one closed from the keyboard keeps it.
      target.focus(lastInputWasKeyboard ? undefined : {focusVisible: false});
      return;
    }
    var heading = document.querySelector("#main-content h1");
    if (heading) {
      if (!heading.hasAttribute("tabindex")) {
        heading.setAttribute("tabindex", "-1");
      }
      heading.focus();
    }
  }

  // A dialog closed without saving shows the saved values when it opens
  // again, not what was typed before. The forms are reset to their
  // server-rendered values and told so with a change event, for the parts of
  // the page that mirror a field (the quiet-hours preset cards).
  function resetForms(dialog) {
    var forms = dialog.querySelectorAll("form");
    for (var i = 0; i < forms.length; i++) {
      forms[i].reset();
      if (document.createEvent) {
        var evt = document.createEvent("Event");
        evt.initEvent("change", true, false);
        forms[i].dispatchEvent(evt);
      }
    }
  }

  function onClosed(evt) {
    var dialog = evt.target;
    // The close that openModal() issues on an already-open dialog reports
    // asynchronously, after the dialog has been shown again as a modal.
    if (dialog.hasAttribute("data-reopening")) {
      dialog.removeAttribute("data-reopening");
      return;
    }
    dialog.classList.remove("is-modal");
    resetSheet(dialog);
    resetForms(dialog);
    clearHash();
    forgetQuestion(dialog);
    returnFocus(dialog);
  }

  // A dialog the address itself opened (one pending confirmation) names the
  // address that no longer asks: a reload after closing does not ask again.
  function forgetQuestion(dialog) {
    var back = dialog.getAttribute("data-modal-return");
    if (back && back.charAt(0) === "/" && back.charAt(1) !== "/" && history.replaceState) {
      history.replaceState(null, "", back);
    }
  }

  function openModal(dialog) {
    if (dialog.hasAttribute("open")) {
      dialog.setAttribute("data-reopening", "");
      dialog.close();
    }
    dialog.classList.add("is-modal");
    ensureGrabber(dialog);
    dialog.removeEventListener("close", onClosed);
    dialog.addEventListener("close", onClosed);
    dialog.showModal();
    focusTitleIfAsked(dialog);
  }

  // For a script that opens a dialog itself (no opener link): `returnTo` is
  // the control that takes the focus back when the dialog closes.
  window.SkyPaneModal = {
    open: function (dialog, returnTo) {
      if (!isModalDialog(dialog)) {
        return false;
      }
      opener = returnTo || null;
      openerHref = "";
      openModal(dialog);
      return true;
    }
  };

  // A dialog marked data-focus-title opens on its heading, so no field
  // raises the keyboard or a native picker unasked.
  function focusTitleIfAsked(dialog) {
    if (!dialog.hasAttribute("data-focus-title")) {
      return;
    }
    var title = dialog.querySelector(".modal__title");
    if (title) {
      title.focus();
    }
  }

  function shutDetails(except) {
    var open = document.querySelectorAll(MENU_SELECTOR);
    for (var i = 0; i < open.length; i += 1) {
      if (open[i] !== except) {
        open[i].removeAttribute("open");
      }
    }
  }

  function onOpenerClick(evt, link) {
    var href = link.getAttribute("href") || "";
    if (href.charAt(0) !== "#" || href.length < 2) {
      return;
    }
    var dialog = document.getElementById(href.slice(1));
    if (!isModalDialog(dialog)) {
      return;
    }
    evt.preventDefault();
    opener = link;
    openerHref = link.getAttribute("href") || "";
    var menu = closestMenu(link);
    if (menu) {
      menu.removeAttribute("open");
    }
    openModal(dialog);
  }

  function onCloserClick(evt, link) {
    var dialog = closestTag(link, "dialog");
    if (!dialog || !dialog.classList.contains("is-modal")) {
      return;
    }
    evt.preventDefault();
    dialog.close();
  }

  // A click on the backdrop lands on the dialog element itself, outside
  // its box. A dialog holding fields ignores it so typed text is not lost.
  function onBackdropClick(evt) {
    var dialog = evt.target;
    if (!isModalDialog(dialog) || !dialog.classList.contains("is-modal")) {
      return;
    }
    if (dialog.querySelector(HOLD_SELECTOR)) {
      return;
    }
    var box = dialog.getBoundingClientRect();
    var inside = evt.clientX >= box.left && evt.clientX <= box.right &&
      evt.clientY >= box.top && evt.clientY <= box.bottom;
    if (!inside) {
      dialog.close();
    }
  }

  document.addEventListener("click", function (evt) {
    var target = evt.target;
    var link = closestWithAttr(target, "data-modal-open");
    if (link) {
      onOpenerClick(evt, link);
      return;
    }
    link = closestWithAttr(target, "data-modal-close");
    if (link) {
      onCloserClick(evt, link);
      return;
    }
    onBackdropClick(evt);
    // Outside tap closes the menus and switchers that are not under it.
    shutDetails(closestTag(target, "details"));
  });

  document.addEventListener("keydown", function (evt) {
    if (evt.key !== "Escape" && evt.key !== "Esc") {
      return;
    }
    var open = document.querySelectorAll(MENU_SELECTOR);
    if (open.length === 0) {
      return;
    }
    var summary = open[0].querySelector("summary");
    shutDetails(null);
    if (summary) {
      summary.focus();
    }
  });

  var FOCUSABLE = 'a[href], button, input, select, textarea, summary, ' +
    '[tabindex]';

  // The modal dialog that is open now, if any.
  function openModalDialog() {
    var all = document.querySelectorAll("dialog[open]");
    for (var i = all.length - 1; i >= 0; i -= 1) {
      var matches = all[i].matches || all[i].msMatchesSelector;
      try {
        if (matches.call(all[i], ":modal")) {
          return all[i];
        }
      } catch (err) {
        if (all[i].classList.contains("is-modal")) {
          return all[i];
        }
      }
    }
    return null;
  }

  // The controls a Tab can reach inside `root`, in document order.
  function tabStops(root) {
    var found = root.querySelectorAll(FOCUSABLE);
    var stops = [];
    for (var i = 0; i < found.length; i += 1) {
      var el = found[i];
      if (el.disabled || el.getAttribute("tabindex") === "-1" ||
          (el.type === "hidden") || el.getClientRects().length === 0) {
        continue;
      }
      if (window.getComputedStyle(el).visibility === "hidden") {
        continue;
      }
      stops.push(el);
    }
    return stops;
  }

  // Tab and Shift+Tab loop inside the open dialog (or the open More sheet):
  // they never reach the page behind it nor the browser's own chrome.
  document.addEventListener("keydown", function (evt) {
    if (evt.key !== "Tab" || evt.altKey || evt.ctrlKey || evt.metaKey) {
      return;
    }
    // The phone More sheet traps the focus too: its panel and its cell are the
    // only stops while it is open, so Tab never lands on the dimmed page.
    var dialog = openModalDialog() || document.querySelector("details.tab-bar__more[open]");
    if (!dialog) {
      return;
    }
    var stops = tabStops(dialog);
    if (stops.length === 0) {
      evt.preventDefault();
      return;
    }
    var first = stops[0];
    var last = stops[stops.length - 1];
    var active = document.activeElement;
    if (!dialog.contains(active) || active === dialog) {
      evt.preventDefault();
      (evt.shiftKey ? last : first).focus();
    } else if (evt.shiftKey && (active === first || (stops.indexOf(active) === -1 &&
        (active.compareDocumentPosition(first) & 4)))) {
      evt.preventDefault();
      last.focus();
    } else if (!evt.shiftKey && (active === last || (stops.indexOf(active) === -1 &&
        (active.compareDocumentPosition(last) & 2)))) {
      evt.preventDefault();
      first.focus();
    }
  });

  // The frame button is a <summary>: keep aria-expanded in step with the
  // popover (the attribute is absent without script, where the disclosure
  // state is still exposed natively).
  function syncExpanded(menu) {
    var summary = menu.querySelector("summary");
    if (summary) {
      summary.setAttribute("aria-expanded", menu.open ? "true" : "false");
    }
  }

  var frameMenus = document.querySelectorAll("details.frame-menu");
  for (var m = 0; m < frameMenus.length; m += 1) {
    syncExpanded(frameMenus[m]);
    frameMenus[m].addEventListener("toggle", function (evt) {
      syncExpanded(evt.target);
    });
  }

  // ---- Phone bottom sheets: drag the grabber or the heading down to close.
  var PHONE_QUERY = window.matchMedia ? window.matchMedia("(max-width: 699.98px)") : null;
  var REDUCED_QUERY = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var GRAB_TEXT_ATTR = "data-sheet-grab-text";
  // A drag past this many pixels, or a faster flick, closes the sheet.
  var CLOSE_DISTANCE = 90;
  var CLOSE_VELOCITY = 0.5;
  // Upward drags barely move the sheet.
  var RUBBER_BAND = 6;
  var SETTLE_FALLBACK_MS = 600;
  var NO_DRAG = "a, button, input, select, textarea, summary, label";
  var drag = null;

  function phoneSheet() {
    return !!PHONE_QUERY && PHONE_QUERY.matches;
  }

  function reducedMotion() {
    return !!REDUCED_QUERY && REDUCED_QUERY.matches;
  }

  // The grabber's hit area; the pill itself is drawn by the stylesheet. Only
  // shown on a phone.
  function ensureGrabber(dialog) {
    if (dialog.querySelector("[data-modal-grabber]")) {
      return;
    }
    var grabber = document.createElement("div");
    grabber.className = "modal__grabber";
    grabber.setAttribute("data-modal-grabber", "");
    grabber.setAttribute("role", "img");
    var text = document.body.getAttribute(GRAB_TEXT_ATTR);
    if (text) {
      grabber.setAttribute("aria-label", text);
    }
    dialog.insertBefore(grabber, dialog.firstChild);
  }

  function resetSheet(dialog) {
    if (drag && drag.dialog === dialog) {
      drag = null;
    }
    if (dialog.getAttribute("data-sheet-state") === null && !dialog.style.transform) {
      return;
    }
    dialog.removeAttribute("data-sheet-state");
    dialog.style.transform = "";
  }

  // The heading strip and the grabber start a drag; controls and the body do
  // not, so scrolling and tapping inside the sheet are untouched.
  function dragStart(node, dialog) {
    if (closestWithAttr(node, "data-modal-grabber")) {
      return true;
    }
    var el = node;
    while (el && el !== dialog && el.nodeType === 1) {
      if (el.matches && el.matches(NO_DRAG)) {
        return false;
      }
      if (el.classList.contains("modal__head")) {
        return true;
      }
      el = el.parentNode;
    }
    return false;
  }

  function sheetDialog(node) {
    var dialog = closestTag(node, "dialog");
    if (!isModalDialog(dialog) || !dialog.classList.contains("is-modal") ||
        !dialog.open || dialog.getAttribute("data-sheet-state") === "closing") {
      return null;
    }
    return dialog;
  }

  document.addEventListener("pointerdown", function (evt) {
    if (!phoneSheet() || drag || evt.button > 0 || evt.isPrimary === false) {
      return;
    }
    var dialog = sheetDialog(evt.target);
    if (!dialog || !dragStart(evt.target, dialog)) {
      return;
    }
    drag = {
      dialog: dialog, id: evt.pointerId, startY: evt.clientY, lastY: evt.clientY,
      lastT: evt.timeStamp, velocity: 0, offset: 0
    };
    dialog.setAttribute("data-sheet-state", "dragging");
    try {
      dialog.setPointerCapture(evt.pointerId);
    } catch (err) {
      // A synthetic or already-ended pointer cannot be captured; the drag
      // still follows the events that reach the document.
    }
  });

  document.addEventListener("pointermove", function (evt) {
    if (!drag || evt.pointerId !== drag.id) {
      return;
    }
    var moved = evt.clientY - drag.startY;
    drag.offset = moved > 0 ? moved : moved / RUBBER_BAND;
    var dt = evt.timeStamp - drag.lastT;
    if (dt > 0) {
      drag.velocity = (evt.clientY - drag.lastY) / dt;
    }
    drag.lastY = evt.clientY;
    drag.lastT = evt.timeStamp;
    drag.dialog.style.transform = "translateY(" + Math.round(drag.offset) + "px)";
  });

  // Runs done once the sheet's transform transition ends (or, with no
  // transition to wait for, at once).
  function afterSettle(dialog, done) {
    if (reducedMotion()) {
      done();
      return;
    }
    var finished = false;
    function finish() {
      if (finished) {
        return;
      }
      finished = true;
      dialog.removeEventListener("transitionend", onEnd);
      done();
    }
    function onEnd(evt) {
      if (evt.target === dialog && evt.propertyName === "transform") {
        finish();
      }
    }
    dialog.addEventListener("transitionend", onEnd);
    window.setTimeout(finish, SETTLE_FALLBACK_MS);
  }

  // Closing goes through the dialog's own close(): the same close event,
  // focus return and hash clean-up as the Close link.
  function closeSheet(dialog) {
    dialog.setAttribute("data-sheet-state", "closing");
    dialog.style.transform = "translateY(" + Math.ceil(dialog.getBoundingClientRect().height) + "px)";
    afterSettle(dialog, function () {
      if (dialog.open) {
        dialog.close();
      }
      resetSheet(dialog);
    });
  }

  function springBack(dialog) {
    dialog.setAttribute("data-sheet-state", "springing");
    dialog.style.transform = "translateY(0px)";
    afterSettle(dialog, function () {
      if (dialog.getAttribute("data-sheet-state") === "springing") {
        resetSheet(dialog);
      }
    });
  }

  function endDrag(evt, cancelled) {
    if (!drag || evt.pointerId !== drag.id) {
      return;
    }
    var dialog = drag.dialog;
    var far = drag.offset > CLOSE_DISTANCE;
    var fast = drag.offset > 0 && drag.velocity > CLOSE_VELOCITY;
    drag = null;
    if (!cancelled && (far || fast)) {
      closeSheet(dialog);
    } else {
      springBack(dialog);
    }
  }

  document.addEventListener("pointerup", function (evt) {
    endDrag(evt, false);
  });
  document.addEventListener("pointercancel", function (evt) {
    endDrag(evt, true);
  });

  // A server-rendered open dialog (a refused submission) or a hash that
  // targets a dialog becomes a modal as soon as the page loads.
  function upgradeOnLoad() {
    var rendered = document.querySelectorAll("dialog.modal[open]");
    var upgraded = false;
    for (var i = 0; i < rendered.length; i += 1) {
      if (isModalDialog(rendered[i]) && !rendered[i].classList.contains("is-modal")) {
        openModal(rendered[i]);
        upgraded = true;
      }
    }
    if (upgraded || !window.location.hash || window.location.hash.length < 2) {
      return;
    }
    var targeted = document.getElementById(window.location.hash.slice(1));
    if (isModalDialog(targeted) && !hasAttr(targeted, "open")) {
      openModal(targeted);
    }
  }

  // The phone More sheet dims the page with a fixed scrim. The browser's
  // status-bar tint is sampled from the page's theme-color, not from that
  // scrim, so while the sheet is open the tint becomes the page ground under
  // the same dim and is put back when the sheet closes.
  var tintSaved = null;
  var SCRIM_SHARE = 0.55;

  function rgbOf(value) {
    var m = /rgba?\(([^)]+)\)/.exec(value || "");
    if (!m) {
      return null;
    }
    var parts = m[1].split(/[ ,\/]+/);
    return [parseFloat(parts[0]), parseFloat(parts[1]), parseFloat(parts[2])];
  }

  function dimmedGround() {
    var ground = rgbOf(window.getComputedStyle(document.documentElement).backgroundColor);
    var ink = rgbOf(window.getComputedStyle(document.body).color);
    if (!ground || !ink) {
      return "";
    }
    var out = "#";
    for (var i = 0; i < 3; i += 1) {
      var channel = Math.round(ground[i] * (1 - SCRIM_SHARE) + ink[i] * SCRIM_SHARE);
      out += ("0" + Math.max(0, Math.min(255, channel)).toString(16)).slice(-2);
    }
    return out;
  }

  function syncStatusTint(open) {
    var metas = document.querySelectorAll('meta[name="theme-color"]');
    if (open && !tintSaved) {
      var dim = dimmedGround();
      if (!dim) {
        return;
      }
      tintSaved = [];
      for (var i = 0; i < metas.length; i += 1) {
        tintSaved.push([metas[i], metas[i].getAttribute("content")]);
        metas[i].setAttribute("content", dim);
      }
    } else if (!open && tintSaved) {
      for (var j = 0; j < tintSaved.length; j += 1) {
        tintSaved[j][0].setAttribute("content", tintSaved[j][1]);
      }
      tintSaved = null;
    }
  }

  // A toggle event does not bubble, so it is caught on the way down.
  document.addEventListener("toggle", function (evt) {
    var el = evt.target;
    if (el && el.classList && el.classList.contains("tab-bar__more")) {
      syncStatusTint(el.open);
      // Closing hides the control that held the focus: it goes back to the
      // More cell instead of the top of the page.
      var held = document.activeElement;
      if (!el.open && (held === document.body || el.contains(held))) {
        el.querySelector("summary").focus();
      }
    }
  }, true);

  upgradeOnLoad();
})();
