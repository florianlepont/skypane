/*
 * SkyPane companion service — theme-preview.js.
 *
 * 30-04-PLAN.md Task 3 (CFG-85): re-scoped from the retired "Frame
 * colours" card (.frame-colours, a colour_usage radiogroup driving
 * JS-toggled usage-panel visibility, plus a scroll-snap carousel with
 * two gated pagers) to the "Aspect" card (.aspect-card, a native
 * details name="aspect-rows" grouped accordion). The accordion
 * needs ZERO script for open/close — a grouped details set is
 * mutually exclusive in the browser by construction — so every
 * carousel/colour_usage-driven function this file used to carry
 * (panel visibility, pagers, scroll-position tracking) is retired
 * outright, not ported forward. What survives is the one thing this
 * file has always actually been for: keeping the live preview <img>
 * in sync with whichever theme chip is checked.
 *
 * D-08/D-12/R-11 (21-CONTEXT.md, 21-UI-SPEC.md §D) originally rewrote
 * this file's own selector/event-delegation strategy so a page-wide
 * single-grid lookup could never silently bind to only the FIRST of
 * several chip grids on the page — every lookup below stays scoped to
 * the one .aspect-card container. Like nav-dropdown.js/
 * battery-trend.js/dirty-state.js/flight-rows.js before it, this file
 * has no build step, no bundler, no framework and no dependency of any
 * kind, and must stay written to an ES5-safe subset (var-only
 * declarations, no arrow functions, no template-literal syntax) so no
 * transpiler is ever needed to ship it. It is served by
 * companion/app.py's THEME_PREVIEW_SCRIPT_ROUTE, mirroring the
 * existing /static/style.css route — the route, the script-src pair
 * and the <script> tag are all unchanged by this rewrite; only this
 * file's own body changes.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state, and must never use any HTML-writing DOM sink at all, matching
 * the CSP's own "no inline script, no on* attribute" rule (D-32) with
 * this file's own "no markup-building sink" rule. The only DOM write
 * this file ever makes is one <img>'s "src" (always assigned from a
 * server-rendered data-preview-src attribute, never a string this file
 * builds itself) and a class-list toggle on that same <img> for the
 * crossfade — no markup-writing DOM sink of any kind is used anywhere
 * in this file.
 *
 * 23-10-PLAN.md Task 2 (D3/CFG-32) changed that src write from
 * the .src PROPERTY to setAttribute("src", …) — the same sink, the same
 * server-rendered value, and the change is load-bearing rather than
 * stylistic: the crossfade below has to compare what is on screen
 * against what was last requested, and reading .src back gives the
 * resolved ABSOLUTE url while every value this file has to compare it
 * with (the server-rendered attribute, and the chips' own
 * data-preview-src) is relative. Comparing those two forms never
 * matches, and a comparison that never matches would fade on every
 * event including the ones that change nothing.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * .aspect-card at all — today only Display does — so the guard below
 * is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns). THIS IS THE MOST DANGEROUS LINE IN THE FILE: the whole IIFE
 * is gated behind it, and getting it wrong makes the entire script a
 * silent no-op on every page — no error, no console warning, no
 * failing check unless one specifically probes the live preview's
 * dynamic behaviour (30-RESEARCH.md Pitfall 5).
 *
 * No-JS floor (CFG-85, locked — STRONGER than the retired card's own
 * claim, not merely re-stated): row visibility is native <details>
 * state this file NEVER WRITES, at any point, for any reason. The
 * retired card's own no-JS floor used to read "the server never emits
 * a hidden attribute on a usage panel" — that claim no longer applies
 * because there is no usage panel any more, and the replacement claim
 * is stronger: a closed row's own radios stay in the DOM and DO
 * participate in form submission, and <summary> is natively
 * activatable by pointer and keyboard with scripts blocked, so a
 * visitor can open any row themselves with zero help from this file. A
 * browser with JavaScript disabled (or this specific script blocked by
 * a stricter CSP directive) simply never runs this file at all, and
 * the accordion, every palette radio and every row all keep working
 * exactly as CFG-85 requires.
 *
 * 22-01-PLAN.md Task 2 (D-01/T8): exposes window.SkyPaneLivePreview, a
 * single small namespace object carrying one function, refresh() —
 * this file's own first and only global. companion/static/dirty-state.js
 * calls it after its Cancel handler's form.reset(), which restores every
 * form=-attached theme radio's checked property natively but fires no
 * change event, so this file's own delegated listener (below) never
 * hears about the reverted selection on its own. refresh() re-derives
 * the open row's own checked chip and re-applies its preview src.
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

  // 23-10-PLAN.md Task 2 (D3/CFG-32): the crossfade.
  //
  // Every preview swap in this file now goes through applyPreviewSrc()
  // instead of assigning preview.src directly, so the fade and the swap
  // can never get out of step: the image fades out, the src is replaced
  // while it is invisible, and it fades back in once the new frame has
  // actually arrived. pendingSrc is the ONE piece of state this adds,
  // and it is the answer to the only way a crossfade goes wrong — a
  // second click landing mid-fade and the preview settling on the theme
  // whose load happened to finish last. Every handler below compares
  // against pendingSrc, so the settled frame is always the most recently
  // requested one.
  //
  // NO TIMER, and that is this file's own standing rule rather than a
  // preference: a timed crossfade guesses when the fade ended and when
  // the image arrived, and is wrong on both counts on a slow connection.
  // transitionend is when the fade-out is genuinely over and the
  // image's own load/error is when the new frame genuinely is (or will
  // never be) there. companion/test_companion_app.py bans every
  // timer primitive in this file outright, by name.
  //
  // The class is declared in companion/static/style.css, which also owns
  // the duration; this file names neither a duration nor an easing.
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
      // Already showing it (the load-time call, and any re-selection of
      // the theme already on screen) - nothing to cross-fade to, and
      // fading out and back in for no change would be motion with no
      // information in it.
      endFade();
      return;
    }
    startFade();
    // THE ONE STALL THIS MACHINE CAN HAVE, CLOSED HERE. Everything
    // below waits on the fade-out's own transitionend, and a
    // transitionend only arrives if a transition actually RAN. There are
    // two ordinary ways it does not:
    //
    //   1. The image is already invisible - a previous swap faded it out
    //      and is still waiting on its load. Adding the class again
    //      changes nothing, so nothing transitions.
    //   2. The class was removed and re-added without the browser
    //      running a style recalculation in between (an image load event
    //      and a click landing inside the same frame will do it). The
    //      computed opacity never left 0, so again nothing transitions.
    //
    // In both cases there is no fade-out left to wait for, so the swap
    // happens now instead of never. This was a REAL flake, not a
    // hypothetical: the Cancel-restore check in
    // companion/test_browser_ux.py failed once with the preview stuck on
    // the discarded theme, then passed on a rerun with no code change.
    if (parseFloat(getComputedStyle(preview).opacity) === 0) {
      swapIfNeeded();
    }
  }

  // The fade-out has finished: the image is invisible, so this is the
  // moment to replace it. If there is nothing left to swap to (the user
  // came back to the frame already showing), fade straight back in.
  preview.addEventListener("transitionend", function (evt) {
    if (evt.propertyName !== "opacity" || !isFading()) {
      return;
    }
    if (!swapIfNeeded()) {
      endFade();
    }
  });

  // The new frame has arrived. If a newer one was requested while this
  // one was loading, go straight on to it rather than fading in a frame
  // that is already stale.
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

  // 30-04-PLAN.md Task 3 (CFG-85): re-keyed from "a usage panel" to
  // "any element" — this function already took its container as an
  // argument and walked input[type="radio"]:checked looking for a
  // parentNode carrying data-preview-src, which the accordion rebuild
  // does not change. The currently-effective live-preview source for
  // one scope: the first checked radio inside it that is actually a
  // theme/palette chip (carries data-preview-src) — never the first
  // checked radio overall, since the rules row's own "Match by"
  // segmented control and the Aspect card's own value input are
  // checked radios too, with no preview of their own.
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

  // The departures row, by its own locked data-usage value — never a
  // strip id or a panel-target attribute, both retired with the
  // carousel/usage-panel markup. Arrivals'/calendar's own leading "Same
  // as departures" option carries no data-preview-src of its own (D-09:
  // no fabricated theme-coloured preview for "no override"), so this is
  // also the fallback source whenever a scope's own checked chip has
  // none.
  function departuresRow() {
    return card.querySelector('details.usage-row[data-usage="departures"]');
  }

  // 30-04-PLAN.md Task 3 (CFG-85): the card's own currently-open row.
  // <details name="aspect-rows"> is a native, browser-enforced
  // mutually-exclusive group, so at most one row is ever open — but a
  // visitor can legitimately close the one open row, leaving NONE open
  // for a moment, and a null read here must not throw. Falls back to
  // the departures row in that case, matching the server's own default
  // (row 1 ships open).
  function openRow() {
    return card.querySelector("details.usage-row[open]") || departuresRow();
  }

  // 22-01-PLAN.md Task 2 (D-01/T8): re-derives the open row's own
  // checked chip and re-applies its preview src from the CURRENT DOM
  // state - the one entry point dirty-state.js's Cancel handler calls
  // after form.reset(), since reset() restores every radio's checked
  // property natively but fires no change event, so this file would
  // otherwise never hear that a selection just reverted. Exposed as the
  // file's own one new global, a small namespace object rather than a
  // bare function, matching this codebase's "no stray globals"
  // discipline while still giving another script a named, stable entry
  // point to call.
  function refreshFromCurrentState() {
    applyPreviewSrc(checkedChipSrc(openRow()) || checkedChipSrc(departuresRow()));
  }
  window.SkyPaneLivePreview = { refresh: refreshFromCurrentState };

  // Settle the preview on the saved theme at first paint — the direct
  // replacement for the retired "collapse three of four panels at
  // load" call. There is nothing to collapse any more (the accordion is
  // native, closed-by-default state, never a class this file adds), but
  // the preview still needs to agree with whichever row/chip the server
  // rendered as checked.
  refreshFromCurrentState();

  // One delegated listener on the card container, never one per radio
  // or per chip (a single row can carry a full THEME_IDS-sized palette)
  // — matching this file's own pre-existing event-delegation idiom, now
  // scoped to the card rather than to a single global grid.
  //
  // 30-04-PLAN.md Task 3 (CFG-85): widened to recognise palette-chip
  // IN ADDITION TO theme-chip — palette-chip is the new control
  // (departures/arrivals/calendar rows), and theme-chip still exists
  // on this page inside the rule-add form's own compact grid, whose
  // radios already moved the preview today. Preserving that
  // deliberately: this plan changes the Aspect tile's structure and
  // must not silently change an unrelated behaviour as a side effect.
  card.addEventListener("change", function (evt) {
    var input = evt.target;
    if (!input || input.type !== "radio") {
      return;
    }
    // config_page._palette_chip_html()/_theme_chip_grid_html() both wrap
    // each real chip's radio directly in its own <label class=
    // "palette-chip ..."> / <label class="theme-chip ...">, which is
    // where the server renders data-preview-src — the input's own
    // parentNode is that label in both markup shapes. A checked radio
    // whose parentNode carries neither class at all (the rules row's
    // own "Match by" segmented control, whose radio and label are
    // SIBLINGS, not parent/child) is never treated as a chip click here.
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
      // The empty-data-preview-src fallback: the leading "Same as
      // departures" option carries none, and its effective preview is
      // the departures row's own checked chip.
      src = checkedChipSrc(departuresRow());
    }
    applyPreviewSrc(src);
  });

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
