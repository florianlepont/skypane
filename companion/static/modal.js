/*
 * SkyPane companion service — modal.js.
 *
 * Upgrades the shared dialog.modal component (companion/ui_modal.py) and
 * closes the open row menus and frame switchers. No build step, ES5-safe
 * subset. Served by companion/app.py's MODAL_SCRIPT_ROUTE. No network call,
 * no timer, no HTML-writing sink: only attribute and class changes, focus
 * and the native dialog methods.
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

  // Where focus goes when a dialog closes: the link that opened it, its
  // row menu's button when the menu has closed, else the page heading
  // (after a reload there is no opener).
  function returnFocus() {
    var target = opener;
    opener = null;
    if (target && document.body.contains(target)) {
      var menu = closestTag(target, "details");
      if (menu && !menu.open) {
        target = menu.querySelector("summary") || target;
      }
      target.focus();
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

  function onClosed(evt) {
    var dialog = evt.target;
    dialog.classList.remove("is-modal");
    clearHash();
    returnFocus();
  }

  function openModal(dialog) {
    if (dialog.hasAttribute("open")) {
      dialog.close();
    }
    dialog.classList.add("is-modal");
    dialog.removeEventListener("close", onClosed);
    dialog.addEventListener("close", onClosed);
    dialog.showModal();
  }

  function shutDetails(except) {
    var open = document.querySelectorAll(
      "details.row-menu[open], details.frame-switcher[open]");
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
    var menu = closestTag(link, "details");
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
    var open = document.querySelectorAll(
      "details.row-menu[open], details.frame-switcher[open]");
    if (open.length === 0) {
      return;
    }
    var summary = open[0].querySelector("summary");
    shutDetails(null);
    if (summary) {
      summary.focus();
    }
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

  upgradeOnLoad();
})();
