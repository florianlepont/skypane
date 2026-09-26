/*
 * SkyPane companion service — theme-preview.js.
 *
 * Keeps the Aspect card's live preview <img> in sync with whichever
 * theme/palette chip is checked (or hovered/focused). The accordion
 * itself needs no script: a native <details name="aspect-rows">
 * group is mutually exclusive in the browser by construction. No
 * build step, ES5-safe subset. Inert on a page with no .aspect-card
 * (today only Display). Served by companion/app.py's
 * THEME_PREVIEW_SCRIPT_ROUTE. Never a network call, a timer, or an
 * HTML-writing DOM sink: the only writes are one <img>'s src
 * (always from a server-rendered data-preview-src attribute) and a
 * class-list toggle for the crossfade.
 *
 * No-JS floor: row visibility is native <details> state this file
 * never writes. A closed row's radios stay in the DOM and participate
 * in form submission, and <summary> is natively activatable with
 * scripts blocked, so every row keeps working with this script absent.
 *
 * Exposes window.SkyPaneLivePreview.refresh(): dirty-state.js's Cancel
 * handler calls it after form.reset(), which restores every radio's
 * checked property natively but fires no change event, so this file's
 * own delegated listener never hears about the reverted selection.
 */
(function () {
  "use strict";

  var card = document.querySelector(".aspect-card");
  if (!card) {
    return;
  }
  var preview = card.querySelector(".theme-live-preview__image");
  if (!preview) {
    return;
  }

  // Every swap goes through applyPreviewSrc(): fade out, replace src
  // while invisible, fade back in. pendingSrc is compared by every
  // handler, so a click mid-fade settles on the most recently requested
  // theme. No timer: transitionend and the image's load/error are the
  // real signals. Class and duration are declared in style.css.
  var FADE_CLASS = "theme-live-preview__image--swapping";
  var pendingSrc = preview.getAttribute("src");

  function isFading() {
    return preview.className.indexOf(FADE_CLASS) !== -1;
  }

  function startFade() {
    if (!isFading()) {
      preview.className += " " + FADE_CLASS;
    }
  }

  function endFade() {
    if (isFading()) {
      preview.className = preview.className.replace(
        new RegExp("\\s*" + FADE_CLASS), "");
    }
  }

  // Swap only while invisible, and only ever to the latest request.
  function swapIfNeeded() {
    if (pendingSrc && preview.getAttribute("src") !== pendingSrc) {
      preview.setAttribute("src", pendingSrc);
      return true;
    }
    return false;
  }

  function applyPreviewSrc(src) {
    if (!src) {
      return;
    }
    pendingSrc = src;
    if (preview.getAttribute("src") === src) {
      // Already showing it: nothing to cross-fade to.
      endFade();
      return;
    }
    startFade();
    // Everything below waits on the fade-out's own transitionend, which
    // only arrives if a transition actually ran. It does not when the
    // image is already invisible (a previous swap is still fading, or
    // the class was removed and re-added with no style recalculation in
    // between), so if opacity is already 0 the swap happens now instead
    // of waiting forever.
    if (parseFloat(getComputedStyle(preview).opacity) === 0) {
      swapIfNeeded();
    }
  }

  // Fade-out finished; if nothing is left to swap to, fade back in.
  preview.addEventListener("transitionend", function (evt) {
    if (evt.propertyName !== "opacity" || !isFading()) {
      return;
    }
    if (!swapIfNeeded()) {
      endFade();
    }
  });

  // New frame arrived; if a newer one was requested meanwhile, go
  // straight on to it rather than fading in a stale frame.
  function onSettled() {
    if (preview.getAttribute("src") === pendingSrc) {
      endFade();
    } else {
      swapIfNeeded();
    }
  }
  preview.addEventListener("load", onSettled);
  // A preview that fails to load must not leave the element stranded at
  // opacity 0 - an invisible preview is worse than a stale one.
  preview.addEventListener("error", onSettled);

  // The currently-effective live-preview source for one scope: the
  // first checked radio inside it that is actually a theme/palette chip
  // (carries data-preview-src) — never the first checked radio overall,
  // since other checked radios in the card (the rules row's "Match by"
  // control, the value input) carry no preview of their own.
  function checkedChipSrc(scope) {
    if (!scope) {
      return null;
    }
    var checked = scope.querySelectorAll('input[type="radio"]:checked');
    var i;
    for (i = 0; i < checked.length; i++) {
      var chip = checked[i].parentNode;
      if (chip && chip.getAttribute) {
        var src = chip.getAttribute("data-preview-src");
        if (src) {
          return src;
        }
      }
    }
    return null;
  }

  // The departures row, by its own locked data-usage value. Arrivals'/
  // calendar's own leading "Same as departures" option carries no
  // data-preview-src, so this is also the fallback source whenever a
  // scope's own checked chip has none.
  function departuresRow() {
    return card.querySelector('details.usage-row[data-usage="departures"]');
  }

  // The card's currently-open row. A visitor can legitimately close the
  // one open row, leaving none open, so this falls back to departures
  // (the server's own default).
  function openRow() {
    return card.querySelector("details.usage-row[open]") || departuresRow();
  }

  // Re-derives the open row's own checked chip and re-applies its
  // preview src from the current DOM state — the entry point
  // dirty-state.js's Cancel handler calls after form.reset(), since
  // reset() restores every radio's checked property natively but fires
  // no change event.
  function refreshFromCurrentState() {
    applyPreviewSrc(checkedChipSrc(openRow()) || checkedChipSrc(departuresRow()));
  }
  window.SkyPaneLivePreview = { refresh: refreshFromCurrentState };

  // Settle the preview on the saved theme at first paint, so it agrees
  // with whichever row/chip the server rendered as checked.
  refreshFromCurrentState();

  // One delegated listener on the card container, never one per radio
  // or per chip, since a single row can carry a full palette of chips.
  card.addEventListener("change", function (evt) {
    var input = evt.target;
    if (!input || input.type !== "radio") {
      return;
    }
    // The server wraps each real chip's radio directly in its own
    // label, where data-preview-src is rendered — the input's own
    // parentNode is that label. A checked radio whose parentNode
    // carries neither chip class (the "Match by" segmented control,
    // whose radio and label are siblings, not parent/child) is never
    // treated as a chip click here.
    var chip = input.parentNode;
    if (!chip || !chip.getAttribute) {
      return;
    }
    var className = chip.className || "";
    var isChip = (
      className.indexOf("theme-chip") !== -1
      || className.indexOf("palette-chip") !== -1);
    var src = chip.getAttribute("data-preview-src");
    if (!src && isChip) {
      // "Same as departures" carries no src of its own.
      src = checkedChipSrc(departuresRow());
    }
    applyPreviewSrc(src);
  });

  // Hover/focus preview, delegated on the card. mouseover/mouseout, not
  // mouseenter/mouseleave, since the latter do not bubble and a
  // delegated listener could never see them. Walks up from the event
  // target to the card; a walk that finds no data-preview-src means
  // "not a chip", not an error.
  function resolveChipPreviewSrc(node) {
    while (node && node !== card) {
      if (node.getAttribute) {
        var src = node.getAttribute("data-preview-src");
        if (src) {
          return src;
        }
      }
      node = node.parentNode;
    }
    return null;
  }

  // Resolving to no chip is a no-op: hovering the summary chevron or
  // empty grid padding must not disturb the preview.
  function previewHoveredOrFocusedChip(evt) {
    var src = resolveChipPreviewSrc(evt.target);
    if (src) {
      applyPreviewSrc(src);
    }
  }

  // Reverts to the open row's own checked chip, computed fresh on every
  // revert since the checked selection changes under this script's
  // feet. Only reverts when evt.relatedTarget resolves to no chip of
  // its own, so hovering from one chip straight to a sibling previews
  // the sibling without flashing back to the checked selection first.
  function revertUnlessMovingToAnotherChip(evt) {
    if (!resolveChipPreviewSrc(evt.target)) {
      return;
    }
    if (resolveChipPreviewSrc(evt.relatedTarget)) {
      return;
    }
    applyPreviewSrc(checkedChipSrc(openRow()) || checkedChipSrc(departuresRow()));
  }

  card.addEventListener("mouseover", previewHoveredOrFocusedChip);
  card.addEventListener("focusin", previewHoveredOrFocusedChip);
  card.addEventListener("mouseout", revertUnlessMovingToAnotherChip);
  card.addEventListener("focusout", revertUnlessMovingToAnotherChip);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();
