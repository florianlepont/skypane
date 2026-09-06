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
 * writes them into the dialog's image src/alt, caption textContent, and
 * (quick task 260903-btu) the replace form's action attribute. This
 * file writes to element content only via textContent/src/alt/an
 * attribute value — never via a raw-markup DOM sink of any kind: the
 * note text is server-rendered by companion/pages/history_page.py and
 * never written here.
 *
 * Quick task 260903-btu: the replace-form lookup below is deliberately
 * optional and deliberately placed after the mandatory three-element
 * guard, never inside its condition. History's own dialog legitimately
 * renders no such form, and folding this lookup into that guard's
 * condition would make the whole script a no-op on History — killing
 * History's lightbox entirely. This file still makes no network call,
 * starts no timer, and holds no persistent state.
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

  // Quick task 260903-btu: optional, looked up once like the three
  // above, but excluded from their guard on purpose — History's page
  // never renders this form, and that is a legitimate, expected state,
  // not a missing-element error.
  var replaceForm = dialog.querySelector(".lightbox__replace");

  // Phase 14 (14-05-PLAN.md Task 1, D-03/D-09): three more optional
  // dialog forms, looked up the exact same way replaceForm already is
  // — outside the mandatory image/caption/note guard above, each
  // guarded independently at its own point of use below. History's
  // page never renders any of these three either.
  var resolveNameForm = dialog.querySelector(".lightbox__resolve-name");
  var resolveUploadZone = dialog.querySelector(".resolve-upload-zone");
  var deleteForm = dialog.querySelector(".lightbox__delete");

  // Phase 14 (14-06-PLAN.md external gap-closure, 2026-09-06): the
  // element 14-UI-SPEC.md's Copy Deck names as data-view-panel-scope's
  // destination — companion/pages/airlines_page.py's
  // _resolve_name_form_html() now emits it (empty, server-side) inside
  // the same form as resolveNameForm above, so this lookup is optional
  // in the identical style as everything else in this block.
  var resolveScope = dialog.querySelector(".lightbox__resolve-scope");

  // These three are unconditionally present in the dialog's static
  // markup after 14-02 (companion/pages/airlines_page.py's
  // _lightbox_html() always emits them) — still looked up in this same
  // optional style for consistency with the file's own idiom, and so a
  // future History-only reader of this file is not misled into
  // thinking they are guaranteed.
  var heading = dialog.querySelector(".lightbox__heading");
  var manualNote = dialog.querySelector(".lightbox__manual-note");
  var resolveContext = dialog.querySelector(".resolve-context");

  // 14-UI-SPEC.md's Component Inventory names these two as this
  // script's own JS hooks: the resolve-name form's hidden prefix field
  // ("JS fills the hidden prefix input's .value at click time") and the
  // resolve-context block's five per-field classes ("each <dd>
  // additionally carries one of five new classes ... so the dialog's
  // copy has stable JS hooks (plan 14-05)"). Looked up the same
  // optional way as everything above — null on History and on any
  // trigger shape that never carries a resolve prefix.
  var resolvePrefixInput = resolveNameForm
    ? resolveNameForm.querySelector('input[name="prefix"]')
    : null;
  var contextPrefix = dialog.querySelector(".resolve-context__prefix");
  var contextFirstSeen = dialog.querySelector(".resolve-context__first-seen");
  var contextLastSeen = dialog.querySelector(".resolve-context__last-seen");
  var contextCount = dialog.querySelector(".resolve-context__count");
  var contextCallsign = dialog.querySelector(".resolve-context__callsign");

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

  // Phase 14 (14-05-PLAN.md Task 2, RESEARCH.md Pitfall 2, mandatory
  // factoring): every read/write the click handler used to perform
  // inline, from the image branch through showModal(), now lives here
  // once — the single place both the click listener and the load-time
  // auto-open below populate the dialog and open it. Never duplicate
  // any of this logic at a second call site.
  function openFromTrigger(trigger) {
    var src = trigger.getAttribute("data-view-panel-src") || "";
    var captionText = trigger.getAttribute("data-view-panel-caption") || "";
    // D-02/RESEARCH.md Pitfall 1: a gap card carries no image at all.
    // Setting the image element's src to an empty string is the one
    // assignment this file must never make again — Safari/Chrome/IE all
    // resolve an empty src against the current document URL and issue a
    // spurious GET, exactly the kind of network call this script's own
    // header comment forbids. removeAttribute (never an empty-string
    // src) is what avoids it.
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

    // 14-UI-SPEC.md's Interaction Contract "Correctness rule": every
    // one of these is read and (where a dialog element exists to
    // receive it) written on every single open, unconditionally, using
    // the existing attr || "" idiom — never gated behind a condition on
    // the attribute's own presence. The dialog's DOM is reused across
    // clicks; skipping a write when an attribute is absent would leak
    // the previous click's content onto an unrelated card.
    var headingText = trigger.getAttribute("data-view-panel-heading") || "";
    if (heading) {
      heading.textContent = headingText;
    }

    var mode = trigger.getAttribute("data-view-panel-mode") || "";
    // Visibility toggle table (14-UI-SPEC.md): governed by mode alone,
    // independent of manual below. Every hidden assignment below runs
    // before this function's own dialog.showModal() call, further
    // down — RESEARCH.md Pitfall 3's whole point: showModal()'s
    // one-time autofocus placement is synchronous and only ever sees
    // the dialog's final, already-toggled subtree.
    if (resolveNameForm) {
      resolveNameForm.hidden = (mode !== "gap");
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

    // Phase 14 (14-06-PLAN.md external gap-closure, 2026-09-06): the
    // element 14-UI-SPEC.md's Copy Deck names as this value's
    // destination now exists (airlines_page._resolve_name_form_html()),
    // so the read that used to be discarded is written here — the one
    // more assignment line 14-05-SUMMARY.md's own "Known Limitations"
    // section predicted would be all a future plan needed.
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
      contextCallsign.textContent = captionText;
    }

    // Quick task 260903-btu: when a replace form is present (Airlines
    // only), point it at this trigger's own upload target. setAttribute
    // is used rather than the form.action property: that property
    // resolves to an absolute URL rather than the literal it was given,
    // and is shadowable by a same-named form control — setAttribute
    // writes the literal attribute and sidesteps both.
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
    // Phase 14 (D-12): a gap/manual/needs-artwork trigger is a real
    // <a href="/airlines?resolve={prefix}">, not a <button> — this
    // navigation must never happen once JS is running the show. A
    // plain <button> trigger's click has no default navigation to
    // prevent, so this is a no-op for every existing art-card trigger.
    evt.preventDefault();
    openFromTrigger(trigger);
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

  // ES5-safe (no browser query-string-parsing API, matching this file's
  // own hand-rolled style) extraction of a single query-string key's
  // decoded value, or "" when absent — "search" is passed in rather
  // than read here, so location.search itself is referenced exactly
  // once, at the one call site below.
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

  // Phase 14 (14-05-PLAN.md Task 2, D-13/D-14, RESEARCH.md Pitfall 2):
  // the first non-click entry point into this script since it shipped.
  // Placed after the click listener above is already wired, so a
  // malformed value here can never prevent every other click on the
  // page from working. Reads location.search once; if a "resolve"
  // value is present and a matching trigger already exists in the
  // rendered DOM, runs the identical population-and-open logic a click
  // would run. Never re-validates the prefix itself (RESEARCH.md
  // Pattern 3) — a non-matching value, or one that is not even a
  // syntactically valid attribute-selector value, is silently ignored:
  // no error, no dialog. The page's own server-rendered fallback
  // section already tells the honest story for a stale or
  // already-fully-resolved prefix.
  //
  // Code review fix (2026-09-06, WR-01): resolveValue comes straight
  // from the URL's query string — fully attacker/user-controlled — and
  // was previously concatenated into the attribute-selector string
  // with only a literal double-quote character as a delimiter. A value
  // containing that same character could break out of the string
  // context (e.g. close the attribute selector early and append an
  // unrelated one), matching an unintended element and opening the
  // dialog on its data instead of failing closed. CSS.escape() is the
  // standard fix for exactly
  // this — escaping a string for safe use inside a CSS selector — and
  // is available in every browser this file already assumes, since
  // dialog.showModal()'s own feature-detection gate at the top of this
  // file already requires a browser new enough to have it. Left
  // uncalled behind a feature check on purpose: the existing try/catch
  // below already degrades to autoTrigger = null if CSS.escape were
  // ever unavailable, matching this block's own established
  // fail-silently posture.
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
    }
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
