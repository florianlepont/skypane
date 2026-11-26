/*
 * SkyPane companion service — copy-button.js.
 *
 * Click handler on every [data-copy-value] button, copying its value
 * to the clipboard (Clipboard API, with a document.execCommand("copy")
 * fallback). No build step, ES5-safe subset. Inert on a page with no
 * [data-copy-value] element. Served by companion/app.py's
 * COPY_BUTTON_SCRIPT_ROUTE. No HTML-writing sink: only textContent and
 * attribute reads, since the values here are already server-escaped
 * data-copy-value attributes. The on-success feedback text is read
 * from each button's own server-rendered, translated data-copied-text
 * attribute.
 */
(function () {
  "use strict";

  var buttons = document.querySelectorAll("[data-copy-value]");
  if (buttons.length === 0) {
    return;
  }

  // Fallback for a caller whose markup does not yet carry
  // data-copied-text; copiedText() reads the real, translated value
  // off each button first.
  var FALLBACK_FEEDBACK_TEXT = "Copied";
  // The visible-confirmation window for the on-button feedback swap.
  var FEEDBACK_RESET_MS = 1500;
  var COPIED_CLASS = "copy-btn--copied";
  var CHECK_CLASS = "copy-btn__check";
  var SVG_NS = "http://www.w3.org/2000/svg";

  // The ink check that springs in beside the copied word (the stylesheet
  // animates it, and not at all under reduced motion). Built with DOM
  // methods only and hidden from assistive technology: the live region
  // announces the word.
  function buildCheck() {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", CHECK_CLASS);
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", "M3 8.5l3.2 3.2L13 4.8");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-linecap", "round");
    svg.appendChild(path);
    return svg;
  }

  function removeCheck(button) {
    var check = button.querySelector("." + CHECK_CLASS);
    if (check) {
      button.removeChild(check);
    }
  }

  function copiedText(button) {
    return button.getAttribute("data-copied-text") || FALLBACK_FEEDBACK_TEXT;
  }

  // The element the fallback textarea joins: the open dialog around the
  // button when there is one (the rest of the page is inert while a modal
  // dialog is open and a textarea there cannot be selected), else the body.
  function hostFor(button) {
    var node = button;
    while (node && node.nodeType === 1) {
      if (node.nodeName.toLowerCase() === "dialog") {
        return node;
      }
      node = node.parentNode;
    }
    return document.body;
  }

  function fallbackCopy(value, button) {
    var host = hostFor(button);
    var textarea = document.createElement("textarea");
    // Off-screen, not display:none — some browsers refuse to select()
    // an element with no rendered box.
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    textarea.style.left = "-9999px";
    textarea.value = value;
    host.appendChild(textarea);
    try {
      textarea.select();
      // Propagate the real result, so handleClick() below never shows
      // success feedback for a copy that silently failed.
      return document.execCommand("copy");
    } finally {
      host.removeChild(textarea);
    }
  }

  function _toggleCopiedClass(button, isActive) {
    // Defensive classList fallback, matching battery-trend.js's own
    // _toggleActive() pattern.
    if (button.classList) {
      if (isActive) {
        button.classList.add(COPIED_CLASS);
      } else {
        button.classList.remove(COPIED_CLASS);
      }
      return;
    }
    var current = " " + (button.getAttribute("class") || "") + " ";
    var has = current.indexOf(" " + COPIED_CLASS + " ") !== -1;
    if (isActive && !has) {
      button.setAttribute("class", (current + COPIED_CLASS).replace(/^\s+|\s+$/g, ""));
    } else if (!isActive && has) {
      button.setAttribute("class", current.split(" " + COPIED_CLASS + " ").join(" ")
        .replace(/^\s+|\s+$/g, ""));
    }
  }

  function showFeedback(button) {
    var feedbackEl = button.nextElementSibling;
    if (!feedbackEl || !feedbackEl.hasAttribute("data-copy-feedback")) {
      return;
    }
    var feedbackText = copiedText(button);
    feedbackEl.textContent = feedbackText;

    // Swaps a visible success label in beside the icon. The button's
    // own visible content is an SVG icon, so writing textContent onto
    // the button itself would destroy it; this writes only into the
    // leaf .copy-btn__label span rendered alongside it.
    //
    // A double-click mid-animation must not overwrite the remembered
    // original label a second time: data-copy-pending guards that, so
    // only the first swap in a run records the label to restore, and
    // one shared setTimeout clears the label, feedback span and class
    // together.
    var labelEl = button.querySelector(".copy-btn__label");
    if (!labelEl || button.getAttribute("data-copy-pending") === "1") {
      window.setTimeout(function () {
        feedbackEl.textContent = "";
      }, FEEDBACK_RESET_MS);
      return;
    }

    button.setAttribute("data-copy-pending", "1");
    var originalLabel = labelEl.textContent;
    labelEl.textContent = feedbackText;
    button.insertBefore(buildCheck(), labelEl);
    _toggleCopiedClass(button, true);
    window.setTimeout(function () {
      feedbackEl.textContent = "";
      labelEl.textContent = originalLabel;
      removeCheck(button);
      _toggleCopiedClass(button, false);
      button.removeAttribute("data-copy-pending");
    }, FEEDBACK_RESET_MS);
  }

  function handleClick(button) {
    var value = button.getAttribute("data-copy-value") || "";
    if (window.navigator && window.navigator.clipboard
        && window.navigator.clipboard.writeText) {
      window.navigator.clipboard.writeText(value).then(
        function () {
          showFeedback(button);
        },
        function () {
          // Only report success when fallbackCopy() actually succeeded;
          // a failed copy must never show a false success indication.
          if (fallbackCopy(value, button)) {
            showFeedback(button);
          }
        }
      );
      return;
    }
    if (fallbackCopy(value, button)) {
      showFeedback(button);
    }
  }

  for (var i = 0; i < buttons.length; i++) {
    (function (button) {
      button.addEventListener("click", function () {
        handleClick(button);
      });
    })(buttons[i]);
  }

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
