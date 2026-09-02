/*
 * SkyPane companion service — panel-lookup.js.
 *
 * D-20 (06.6.4.1-CONTEXT.md, UI-SPEC §8.3): opens a shared lightbox
 * showing the rendered panel image nearest a History row's timestamp,
 * when the row's "View panel near this time" trigger button is clicked.
 * Like nav-dropdown.js/dirty-state.js before it, this file has no build
 * step, no bundler, no framework and no dependency of any kind, and must
 * stay written to an ES5-safe subset (no let/const/arrow functions/
 * template literals/backticks) so no transpiler is ever needed to ship
 * it. It is served by companion/app.py's PANEL_LOOKUP_SCRIPT_ROUTE,
 * mirroring the existing /static/style.css route.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state — it only reads attributes off already-rendered DOM elements and
 * writes them into the dialog's image src/alt and caption textContent.
 * This file writes to element content only via textContent/src/alt —
 * never via a raw-markup DOM sink of any kind: the note text is
 * server-rendered by companion/pages/history_page.py and never written
 * here.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Since quick task 260902-tli,
 * both History and the Airlines gallery carry a #panel-lookup-dialog
 * element (Airlines' own click-to-enlarge lightbox reuses this exact
 * mechanism rather than inventing a second one), so the guard below is
 * what lets this one cached script serve every page that does or does
 * not render the dialog, matching the project's established convention
 * (nav-dropdown.js/dirty-state.js's own early returns).
 *
 * Standing constraint added by 260902-tli: this script must never
 * decide, from the viewport's dimensions or from the device's reported
 * orientation, whether to open the dialog — that gate belongs entirely
 * in the stylesheet, on the trigger's own rule, never here. The harness
 * pins this by grepping this file's whole source for the two browser
 * APIs such a decision would require.
 */
(function () {
  "use strict";

  var dialog = document.getElementById("panel-lookup-dialog");
  if (!dialog) {
    return;
  }

  // A browser with no native <dialog>/showModal() support degrades to no
  // lightbox at all, rather than to a JavaScript error — the underlying
  // History page (the trigger buttons, the table rows) stays fully
  // usable either way.
  if (typeof dialog.showModal !== "function") {
    return;
  }

  var image = dialog.querySelector(".lightbox__image");
  var caption = dialog.querySelector(".lightbox__caption");
  var note = dialog.querySelector(".lightbox__note");
  if (!image || !caption || !note) {
    return;
  }

  // ES5-safe manual ancestor walk (no Element.closest, matching this
  // codebase's transpiler-free constraint) — finds the nearest ancestor
  // of "target" (inclusive) carrying the data-view-panel-src attribute,
  // or null if none exists within the document.
  function findTriggerAncestor(target) {
    var node = target;
    while (node && node.nodeType === 1) {
      if (node.hasAttribute && node.hasAttribute("data-view-panel-src")) {
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }

  document.addEventListener("click", function (evt) {
    var trigger = findTriggerAncestor(evt.target);
    if (!trigger) {
      return;
    }
    var src = trigger.getAttribute("data-view-panel-src") || "";
    var captionText = trigger.getAttribute("data-view-panel-caption") || "";
    image.src = src;
    // The caption text also becomes the image's alt text, so the modal
    // is never an unlabelled image.
    image.alt = captionText;
    caption.textContent = captionText;
    dialog.showModal();
  });

  var closeButton = dialog.querySelector("[data-view-panel-close]");
  if (closeButton) {
    closeButton.addEventListener("click", function () {
      dialog.close();
    });
  }

  // No Escape handler and no focus-management code is added here on
  // purpose: the native <dialog> element already provides Escape-to-
  // close, a backdrop, and focus-trap semantics for free — exactly why
  // UI-SPEC §8.3 chose <dialog> over a hand-rolled overlay <div>. Do not
  // add a redundant handler later.

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
