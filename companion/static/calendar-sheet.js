/*
 * SkyPane companion service — calendar-sheet.js.
 *
 * Upgrades the Display page's calendar "Manage" sheet. No build step,
 * ES5-safe subset. Inert on a page with no [data-calendar-sheet]
 * dialog. Served by companion/app.py's CALENDAR_SHEET_SCRIPT_ROUTE. No
 * network call, no timer, no HTML-writing sink: only attribute reads,
 * hidden/textContent writes and the native dialog methods.
 *
 * The sheet is one server-rendered <dialog>. Scripts blocked, it renders
 * open in the page at ?calendar=manage#calendar-sheet and every control in
 * it is a plain link or form. This file only adds: opening as a modal
 * from the page's Manage button, a "Checking…" label while the connect
 * form's POST runs (the server fetches the link before saving it), and
 * the in-sheet disconnect confirmation. Security: the confirmation is a
 * misclick guard only; the disconnect route independently requires its
 * own exact confirm value and a session, so this file only ever sets the
 * form's confirm field after a click on the confirm button.
 */
(function () {
  "use strict";

  var dialog = document.querySelector("[data-calendar-sheet]");
  if (!dialog || typeof dialog.showModal !== "function") {
    return;
  }

  var openers = document.querySelectorAll("[data-calendar-open]");
  var closers = dialog.querySelectorAll("[data-calendar-close]");
  var urlInput = dialog.querySelector('input[name="calendar_url"]');
  var connectForm = dialog.querySelector("[data-calendar-connect]");
  var disconnectForm = dialog.querySelector("[data-calendar-disconnect]");
  var confirmPanel = dialog.querySelector("[data-calendar-confirm]");
  var confirmYes = dialog.querySelector("[data-calendar-confirm-yes]");
  var confirmCancel = dialog.querySelector("[data-calendar-confirm-cancel]");
  var disconnectButton = disconnectForm
    ? disconnectForm.querySelector('button[type="submit"]') : null;

  // Back to the sheet's resting state: the confirmation closed and the
  // Disconnect action shown again.
  function resetConfirm() {
    if (confirmPanel) {
      confirmPanel.hidden = true;
    }
    if (disconnectForm) {
      disconnectForm.hidden = false;
    }
  }

  // The query parameters that only exist to reopen the sheet after a
  // redirect, dropped so a reload does not reopen it.
  function cleanAddress() {
    if (!window.history || typeof window.history.replaceState !== "function") {
      return;
    }
    var parts = window.location.search.replace(/^\?/, "").split("&");
    var keep = [];
    for (var i = 0; i < parts.length; i += 1) {
      var name = parts[i].split("=")[0];
      if (parts[i] !== "" && name !== "calendar" && name !== "calendar_error") {
        keep.push(parts[i]);
      }
    }
    window.history.replaceState(
      null, "", window.location.pathname + (keep.length ? "?" + keep.join("&") : ""));
  }

  // A scripts-blocked page already shows the sheet open in the page
  // (non-modal); closing and re-opening it promotes it to a modal.
  function openModal() {
    if (dialog.hasAttribute("open")) {
      dialog.close();
    }
    resetConfirm();
    dialog.showModal();
  }

  for (var i = 0; i < openers.length; i += 1) {
    openers[i].addEventListener("click", function (evt) {
      evt.preventDefault();
      openModal();
    });
  }

  for (var c = 0; c < closers.length; c += 1) {
    closers[c].addEventListener("click", function (evt) {
      evt.preventDefault();
      dialog.close();
    });
  }

  dialog.addEventListener("close", resetConfirm);

  // The pending state. The server reads the link before saving it, which
  // can take up to ten seconds; the sheet stays open and says so. The
  // label is rendered by the server (already translated) on the button.
  if (connectForm) {
    connectForm.addEventListener("submit", function () {
      var button = connectForm.querySelector('button[type="submit"]');
      var label = button ? button.getAttribute("data-pending-label") : null;
      if (button && label) {
        button.textContent = label;
      }
      connectForm.setAttribute("aria-busy", "true");
    });
  }

  if (disconnectForm && confirmPanel && confirmYes && confirmCancel) {
    disconnectForm.addEventListener("submit", function (evt) {
      var field = disconnectForm.querySelector("[data-confirm-field]");
      if (field && field.value !== "") {
        return;
      }
      evt.preventDefault();
      disconnectForm.hidden = true;
      confirmPanel.hidden = false;
      // The safe choice takes focus, so a stray Enter cannot confirm.
      confirmCancel.focus();
    });
    confirmYes.addEventListener("click", function () {
      var field = disconnectForm.querySelector("[data-confirm-field]");
      var value = disconnectForm.getAttribute("data-confirm-value");
      if (field && value !== null) {
        field.value = value;
      }
      disconnectForm.submit();
    });
    confirmCancel.addEventListener("click", function () {
      resetConfirm();
      if (disconnectButton) {
        disconnectButton.focus();
      }
    });
  }

  // Reopened by the server after a refused link or at the no-script
  // address. Focus lands on the field only after a refusal, where the
  // next thing to do is paste again; a plain open leaves it on the
  // dialog's first control.
  if (dialog.hasAttribute("open")) {
    var refused = dialog.hasAttribute("data-calendar-error");
    openModal();
    cleanAddress();
    if (refused && urlInput) {
      urlInput.focus();
    }
  }
})();
