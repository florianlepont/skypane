/*
 * SkyPane companion service -- update-question.js.
 *
 * Asks the Install and Roll back question in the shared modal dialog (a card
 * on a wide screen, a bottom sheet on a phone) for any form that carries the
 * question as data-question-title, -body, -go and -cancel. Accepting posts the
 * form with confirm=yes; Cancel closes the dialog and sends nothing. No build
 * step, ES5-safe subset. Every text goes in through textContent: no
 * HTML-writing sink.
 *
 * Security: the dialog is a convenience, never a boundary. Without script (or
 * with this file blocked) the form posts without a confirm field and the
 * server answers with its own confirmation page; the server requires the exact
 * confirm=yes and the session and CSRF field either way.
 */
(function () {
  "use strict";

  var forms = document.querySelectorAll("form[data-question-title]");
  var i;

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  function buildDialog(form) {
    var dialog = element("dialog", "modal question-dialog");
    var head = element("header", "modal__head");
    var heading = element("div");
    var title = element("h2", "modal__title text-heading",
      form.getAttribute("data-question-title"));
    var body = element("div", "modal__body");
    var actions = element("div", "modal__actions");
    var go = element("button", "btn btn--primary", form.getAttribute("data-question-go"));
    var cancel = element("button", "btn btn--secondary",
      form.getAttribute("data-question-cancel"));
    title.id = "question-dialog-title";
    dialog.setAttribute("aria-labelledby", title.id);
    go.type = "button";
    cancel.type = "button";
    cancel.setAttribute("autofocus", "");
    heading.appendChild(title);
    head.appendChild(heading);
    body.appendChild(element("p", "text-body", form.getAttribute("data-question-body")));
    actions.appendChild(cancel);
    actions.appendChild(go);
    dialog.appendChild(head);
    dialog.appendChild(body);
    dialog.appendChild(actions);
    cancel.addEventListener("click", function () {
      dialog.close();
    });
    go.addEventListener("click", function () {
      var field = document.createElement("input");
      field.type = "hidden";
      field.name = "confirm";
      field.value = "yes";
      form.appendChild(field);
      form.submit();
    });
    dialog.addEventListener("close", function () {
      document.body.removeChild(dialog);
    });
    return dialog;
  }

  function attach(form) {
    form.addEventListener("submit", function (evt) {
      var dialog;
      if (!window.SkyPaneModal) {
        return;
      }
      dialog = buildDialog(form);
      document.body.appendChild(dialog);
      if (window.SkyPaneModal.open(dialog, document.activeElement)) {
        evt.preventDefault();
        return;
      }
      document.body.removeChild(dialog);
    });
  }

  for (i = 0; i < forms.length; i++) {
    attach(forms[i]);
  }
})();
