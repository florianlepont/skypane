/*
 * SkyPane companion service — panel-lookup.js.
 *
 * Opens a shared lightbox showing the rendered panel image nearest a
 * History row's timestamp, or an Airlines gallery picture, when a
 * "View panel" trigger is clicked. No build step, ES5-safe subset.
 * Inert on a page with no #panel-lookup-dialog. Served by
 * companion/app.py's PANEL_LOOKUP_SCRIPT_ROUTE. Never a network call,
 * a timer, or persistent state, and never a raw-markup DOM sink: all
 * writes go through textContent/src/alt/setAttribute.
 */
(function () {
  "use strict";

  // Drag-and-drop over the two upload forms, and the framing preview
  // beside them. Lives here rather than in a new file because it
  // rewires forms this file already owns. Sits above the dialog guard
  // below because the drop affordance is revealed by nav-dropdown.js's
  // .js gate independently of the dialog, so an early return here would
  // leave a visible, inert drop target on a page with no dialog.
  //
  // A drop builds a DataTransfer, adds the dropped File to it, and
  // assigns it to the form's own <input type="file">; from there the
  // bytes travel the identical multipart POST path a picked file
  // travels, with the same server-side size cap and crop. This file
  // never reads or posts the bytes itself, and contains no canvas code:
  // companion/illustration_normalize.py's own docstring forbids a
  // second, browser-side implementation of the crop measurement it
  // owns, since the server can neither check it nor trust the machine
  // it ran on.
  var uploadDropZones = document.querySelectorAll("[data-upload-drop]");

  function uploadZoneInput(zone) {
    // getElementById of a SERVER-RENDERED id, never an ancestor walk:
    // this file is written to an ES5-safe subset with no
    // Element.closest(), and an exact lookup beats a guess.
    var inputId = zone.getAttribute("data-upload-drop-input") || "";
    return inputId ? document.getElementById(inputId) : null;
  }

  function setUploadMessage(zone, text) {
    var target = zone.querySelector(".upload-drop__message");
    if (target) {
      // textContent only; the text itself is server-rendered onto the
      // zone already translated, so this file writes no copy of its own.
      target.textContent = text;
    }
  }

  function clearUploadPreview(zone) {
    var image = zone.querySelector(".upload-drop__image");
    if (image) {
      image.hidden = true;
      // Dropping the src drops the data URL with it. An <img> left
      // holding one keeps the whole decoded file alive for as long as
      // the document does, which is the same leak an unrevoked object
      // URL would have been.
      image.removeAttribute("src");
    }
  }

  function clearAllUploadPreviews() {
    for (var i = 0; i < uploadDropZones.length; i += 1) {
      clearUploadPreview(uploadDropZones[i]);
      setUploadMessage(uploadDropZones[i], "");
    }
  }

  // The one validator: both the drop and pick paths call this and
  // nothing else, so they cannot disagree about what is acceptable.
  //
  // Security: this is a courtesy, not the control. The size cap, PNG
  // header parsing and filename discarding all happen server-side in
  // companion/app.py and companion/illustration_normalize.py, unchanged
  // by this file; this function only saves a round trip. It refuses
  // only what it positively knows is wrong — a browser reporting no
  // type at all hands the decision to the server, the real gate.
  function uploadRefusal(zone, files) {
    if (!files || files.length === 0) {
      // Zero files is a drag of something that is not a file at all —
      // a link, a selection, a browser tab.
      return zone.getAttribute("data-upload-drop-type-error") || "";
    }
    if (files.length !== 1) {
      return zone.getAttribute("data-upload-drop-multiple-error") || "";
    }
    var file = files[0];
    if (file.type && file.type !== "image/png") {
      return zone.getAttribute("data-upload-drop-type-error") || "";
    }
    var maxBytes = parseInt(zone.getAttribute("data-upload-drop-max-bytes") || "", 10);
    if (maxBytes > 0 && file.size > maxBytes) {
      return zone.getAttribute("data-upload-drop-size-error") || "";
    }
    return "";
  }

  // The preview is a plain <img> the stylesheet frames; nothing here
  // resizes, crops or re-encodes. FileReader rather than an object URL,
  // since this app's CSP is img-src 'self' data: and Chromium refuses a
  // blob: image under it — widening the CSP for a thumbnail is the
  // wrong trade on the one control that accepts outside bytes. There is
  // therefore no object URL to revoke; the src is dropped instead.
  function showUploadPreview(zone, file) {
    var image = zone.querySelector(".upload-drop__image");
    if (!image || !file) {
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      image.src = reader.result;
      image.hidden = false;
    };
    reader.onerror = function () {
      clearUploadPreview(zone);
    };
    reader.readAsDataURL(file);
  }

  // THE DROP PATH. The refusal happens BEFORE anything is assigned:
  // this function is the only place in this file that ever writes an
  // input's files, and it has already returned by then.
  function applyDroppedFiles(zone, files) {
    var input = uploadZoneInput(zone);
    if (!input) {
      return;
    }
    var refusal = uploadRefusal(zone, files);
    if (refusal) {
      setUploadMessage(zone, refusal);
      clearUploadPreview(zone);
      return;
    }
    try {
      var transfer = new DataTransfer();
      transfer.items.add(files[0]);
      input.files = transfer.files;
    } catch (err) {
      // A browser without a constructible DataTransfer degrades to no
      // drop handling at all rather than to a JavaScript error — the
      // file picker underneath is untouched and still works. The same
      // fail-silently posture as this file's showModal() feature gate.
      return;
    }
    setUploadMessage(zone, "");
    showUploadPreview(zone, files[0]);
  }

  // THE PICKER PATH. It runs the SAME validator and says the same
  // thing, so the two paths agree about what is acceptable — but it
  // deliberately never touches input.files.
  //
  // That asymmetry is principled, not an oversight. A drop is this
  // script's own act, so declining to perform it is the script doing
  // nothing. A pick is the visitor's act through the browser's own
  // control, and silently discarding their choice would be this script
  // undoing a person's input to spare them a server error it is not
  // entitled to predict. In both cases the bytes that reach the server
  // reach it through the identical form, and the server decides.
  function reviewChosenFile(zone) {
    var input = uploadZoneInput(zone);
    if (!input) {
      return;
    }
    var files = input.files;
    if (!files || files.length === 0) {
      setUploadMessage(zone, "");
      clearUploadPreview(zone);
      return;
    }
    var refusal = uploadRefusal(zone, files);
    setUploadMessage(zone, refusal);
    if (refusal) {
      clearUploadPreview(zone);
      return;
    }
    showUploadPreview(zone, files[0]);
  }

  function wireUploadDropZone(zone) {
    var input = uploadZoneInput(zone);
    if (!input) {
      return;
    }

    // Assigning to a .value (or to .files) from script fires NO event,
    // so the picker's own preview has to be driven by the browser's
    // "change" — the event a real pick actually emits.
    input.addEventListener("change", function () {
      reviewChosenFile(zone);
    });

    zone.addEventListener("dragover", function (evt) {
      // preventDefault on dragover is what makes this element a drop
      // target at all; without it the browser navigates to the file.
      evt.preventDefault();
      zone.setAttribute("data-upload-drop-active", "");
    });
    zone.addEventListener("dragleave", function () {
      zone.removeAttribute("data-upload-drop-active");
    });
    zone.addEventListener("drop", function (evt) {
      evt.preventDefault();
      zone.removeAttribute("data-upload-drop-active");
      // 25-01's value-controls.js refuses an untrusted event for its
      // own control and this one has the same exposure: a script
      // running in this document can dispatch a drop carrying a
      // DataTransfer it built itself. Refusing it keeps the only way
      // into this handler the gesture a person performed.
      if (!evt.isTrusted) {
        return;
      }
      applyDroppedFiles(zone, evt.dataTransfer ? evt.dataTransfer.files : null);
    });
  }

  for (var zoneIndex = 0; zoneIndex < uploadDropZones.length; zoneIndex += 1) {
    wireUploadDropZone(uploadDropZones[zoneIndex]);
  }

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

  // Everything below is looked up optionally, outside the mandatory
  // image/caption/note guard above, and guarded independently at its
  // own point of use: History's dialog renders none of these
  // Airlines-only resolve/replace/delete elements. resolveSubmit's
  // visibility is mirrored from resolveNameForm's own hidden state
  // below, never a second copy of the mode test.
  var replaceForm = dialog.querySelector(".lightbox__replace");
  var resolveNameForm = dialog.querySelector(".lightbox__resolve-name");
  var resolveUploadZone = dialog.querySelector(".resolve-upload-zone");
  var deleteForm = dialog.querySelector(".lightbox__delete");
  var resolveScope = dialog.querySelector(".lightbox__resolve-scope");
  var resolveSubmit = dialog.querySelector(".lightbox__actions [type=\"submit\"]");
  var heading = dialog.querySelector(".lightbox__heading");
  var manualNote = dialog.querySelector(".lightbox__manual-note");
  var resolveContext = dialog.querySelector(".resolve-context");
  var resolvePrefixInput = resolveNameForm
    ? resolveNameForm.querySelector('input[name="prefix"]')
    : null;
  var contextPrefix = dialog.querySelector(".resolve-context__prefix");
  var contextFirstSeen = dialog.querySelector(".resolve-context__first-seen");
  var contextLastSeen = dialog.querySelector(".resolve-context__last-seen");
  var contextCount = dialog.querySelector(".resolve-context__count");
  var contextCallsign = dialog.querySelector(".resolve-context__callsign");

  // ES5-safe manual ancestor walk (no Element.closest) for the nearest
  // ancestor of target (inclusive) carrying data-view-panel-src.
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

  // Every read/write to populate and open the dialog lives here once —
  // the single place both the click listener and the load-time
  // auto-open below call. Never duplicate this logic at a second site.
  function openFromTrigger(trigger) {
    var src = trigger.getAttribute("data-view-panel-src") || "";
    var captionText = trigger.getAttribute("data-view-panel-caption") || "";
    // A gap card carries no image at all. Setting src to an empty
    // string must be avoided: browsers resolve an empty src against
    // the current document URL and issue a spurious GET, so
    // removeAttribute is used instead.
    if (src) {
      image.hidden = false;
      image.src = src;
      // The caption text also becomes the image's alt text, so the
      // modal is never an unlabelled image.
      image.alt = captionText;
    } else {
      image.hidden = true;
      image.removeAttribute("src");
      image.removeAttribute("alt");
    }
    caption.textContent = captionText;

    // Every one of these is written unconditionally on every open,
    // never gated on the attribute's own presence: the dialog's DOM is
    // reused across clicks, and skipping a write would leak the
    // previous click's content onto an unrelated card.
    var headingText = trigger.getAttribute("data-view-panel-heading") || "";
    if (heading) {
      heading.textContent = headingText;
    }

    var mode = trigger.getAttribute("data-view-panel-mode") || "";
    // Governed by mode alone, independent of manual below. Every hidden
    // assignment here runs before showModal() further down, since its
    // one-time autofocus placement is synchronous and only ever sees
    // the dialog's final, already-toggled subtree.
    if (resolveNameForm) {
      resolveNameForm.hidden = (mode !== "gap");
      // Mirrored, never re-derived: the lifted Save button is visible
      // exactly when the form it submits is.
      if (resolveSubmit) {
        resolveSubmit.hidden = resolveNameForm.hidden;
      }
    }
    if (resolveUploadZone) {
      resolveUploadZone.hidden = (mode !== "needs-artwork");
    }
    if (replaceForm) {
      replaceForm.hidden = (mode !== "art");
    }

    var manual = trigger.getAttribute("data-view-panel-manual") || "";
    // Orthogonal to mode — governs only the delete form and the
    // manual-note text, never folded into the mode branch above.
    if (deleteForm) {
      deleteForm.hidden = (manual === "");
    }
    var manualNoteText = trigger.getAttribute("data-view-panel-manual-note") || "";
    if (manualNote) {
      manualNote.textContent = manualNoteText;
    }

    var scopeText = trigger.getAttribute("data-view-panel-scope") || "";
    if (resolveScope) {
      resolveScope.textContent = scopeText;
    }

    var resolvePrefix = trigger.getAttribute("data-view-panel-resolve-prefix") || "";
    var firstSeen = trigger.getAttribute("data-view-panel-first-seen") || "";
    var lastSeen = trigger.getAttribute("data-view-panel-last-seen") || "";
    var count = trigger.getAttribute("data-view-panel-count") || "";
    if (resolveContext) {
      resolveContext.hidden = !count;
    }
    if (resolvePrefixInput) {
      resolvePrefixInput.value = resolvePrefix;
    }
    if (contextPrefix) {
      contextPrefix.textContent = resolvePrefix;
    }
    if (contextFirstSeen) {
      contextFirstSeen.textContent = firstSeen;
    }
    if (contextLastSeen) {
      contextLastSeen.textContent = lastSeen;
    }
    if (contextCount) {
      contextCount.textContent = count;
    }
    if (contextCallsign) {
      // Gated on the same count that gates resolveContext.hidden, so
      // the field and its container can never disagree. In art mode
      // captionText is the illustration's caption, not a callsign, so
      // it is only written in the resolve modes where it genuinely is
      // the example callsign.
      contextCallsign.textContent = count ? captionText : "";
    }

    // setAttribute rather than the form.action property, which resolves
    // to an absolute URL and is shadowable by a same-named form control.
    if (replaceForm) {
      var replaceAction = trigger.getAttribute("data-view-panel-replace-action") || "";
      replaceForm.setAttribute("action", replaceAction);
    }
    if (resolveUploadZone) {
      var uploadAction = trigger.getAttribute("data-view-panel-upload-action") || "";
      var uploadForm = resolveUploadZone.querySelector("form");
      if (uploadForm) {
        uploadForm.setAttribute("action", uploadAction);
      }
    }
    if (deleteForm) {
      var deleteAction = trigger.getAttribute("data-view-panel-delete-action") || "";
      deleteForm.setAttribute("action", deleteAction);
    }

    dialog.showModal();
  }

  document.addEventListener("click", function (evt) {
    var trigger = findTriggerAncestor(evt.target);
    if (!trigger) {
      return;
    }
    // A gap/manual/needs-artwork trigger is a real
    // <a href="/airlines?resolve={prefix}">, not a <button>, so this
    // navigation must never happen once JS is running the show.
    evt.preventDefault();
    openFromTrigger(trigger);
  });

  var closeButton = dialog.querySelector("[data-view-panel-close]");
  if (closeButton) {
    closeButton.addEventListener("click", function () {
      dialog.close();
    });
  }

  // A click on the backdrop closes the dialog. A click inside it lands
  // on a descendant, never on the <dialog> element itself, so
  // evt.target === dialog means the backdrop was clicked.
  dialog.addEventListener("click", function (evt) {
    if (evt.target === dialog) {
      dialog.close();
    }
  });

  // The one upload-drop hook that needs the dialog: a closed dialog
  // still holding a preview is a decoded copy of the visitor's file
  // kept alive, and the next trigger click could open a different
  // airline over it.
  dialog.addEventListener("close", clearAllUploadPreviews);

  // No Escape handler and no focus-management code is added here: the
  // native <dialog> element already provides Escape-to-close, a
  // backdrop, and focus-trap semantics for free.

  // ES5-safe extraction of a single query-string key's decoded value,
  // or "" when absent.
  function resolveParamFromSearch(search) {
    var query = search.charAt(0) === "?" ? search.slice(1) : search;
    var pairs = query ? query.split("&") : [];
    for (var i = 0; i < pairs.length; i += 1) {
      var pair = pairs[i].split("=");
      if (pair[0] === "resolve") {
        try {
          return decodeURIComponent(pair[1] || "");
        } catch (err) {
          return "";
        }
      }
    }
    return "";
  }

  // Reads location.search once; if a "resolve" value is present and a
  // matching trigger already exists in the rendered DOM, runs the same
  // population-and-open logic a click would run. Never re-validates
  // the prefix; a non-matching value is silently ignored.
  //
  // Security: resolveValue comes straight from the URL's query string,
  // fully user-controlled. CSS.escape() prevents it from breaking out
  // of the attribute-selector string and matching an unintended
  // element; the try/catch degrades to autoTrigger = null if
  // CSS.escape is ever unavailable.
  var resolveValue = resolveParamFromSearch(location.search);
  if (resolveValue) {
    var autoTrigger = null;
    try {
      autoTrigger = document.querySelector(
        '[data-view-panel-resolve-prefix="' + CSS.escape(resolveValue) + '"]');
    } catch (err) {
      autoTrigger = null;
    }
    if (autoTrigger) {
      openFromTrigger(autoTrigger);
      // The same resolve section also renders in-page as the no-JS
      // fallback; once the dialog copy is open, hide the duplicate.
      var fallback = document.querySelector("[data-resolve-fallback]");
      if (fallback) {
        fallback.hidden = true;
      }
    }
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
