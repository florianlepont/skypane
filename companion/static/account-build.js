/*
 * SkyPane companion service — account-build.js.
 *
 * Copies the build line of the Account page ([data-build-copy]) to the
 * clipboard (Clipboard API, with a document.execCommand("copy") fallback) and
 * swaps the hint line for the translated "copied" word for a moment. Inert on
 * a page with no such button. No HTML-writing sink: only textContent and
 * attribute reads. ES5-safe subset.
 */
(function () {
  "use strict";

  var button = document.querySelector("[data-build-copy]");
  if (!button) {
    return;
  }
  var RESET_MS = 1500;

  function fallbackCopy(value) {
    var textarea = document.createElement("textarea");
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    textarea.value = value;
    document.body.appendChild(textarea);
    try {
      textarea.select();
      return document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }
  }

  function showCopied() {
    var hint = button.querySelector("[data-build-hint]");
    var status = button.parentNode.querySelector("[data-build-status]");
    var copied = button.getAttribute("data-copied-text") || "Copied";
    if (!hint || button.getAttribute("data-copy-pending") === "1") {
      return;
    }
    button.setAttribute("data-copy-pending", "1");
    var original = hint.textContent;
    hint.textContent = copied;
    if (status) {
      status.textContent = copied;
    }
    window.setTimeout(function () {
      hint.textContent = original;
      if (status) {
        status.textContent = "";
      }
      button.removeAttribute("data-copy-pending");
    }, RESET_MS);
  }

  button.addEventListener("click", function () {
    var value = button.getAttribute("data-build-copy") || "";
    var clipboard = window.navigator && window.navigator.clipboard;
    if (clipboard && clipboard.writeText) {
      clipboard.writeText(value).then(showCopied, function () {
        if (fallbackCopy(value)) {
          showCopied();
        }
      });
    } else if (fallbackCopy(value)) {
      showCopied();
    }
  });
})();
