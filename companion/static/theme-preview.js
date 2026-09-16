/*
 * SkyPane companion service — theme-preview.js.
 *
 * D-08/D-12/R-11 (21-CONTEXT.md, 21-UI-SPEC.md §D): rewritten for the
 * Frame colours card — a genuine rewrite of this file's own selector/
 * event-delegation strategy (21-RESEARCH.md Area B.5/Pitfall 3), not a
 * patch, since a page-wide single-grid lookup silently binds to only
 * the FIRST of the card's several chip grids the moment more than one
 * exists on the page. Every lookup below is scoped to the one
 * .frame-colours card container instead. Like
 * nav-dropdown.js/battery-trend.js/dirty-state.js/flight-rows.js before
 * it, this file has no build step, no bundler, no framework and no
 * dependency of any kind, and must stay written to an ES5-safe subset
 * (var-only declarations, no arrow functions, no template-literal
 * syntax) so no transpiler is ever needed to ship it. It is served by
 * companion/app.py's THEME_PREVIEW_SCRIPT_ROUTE, mirroring the existing
 * /static/style.css route — the route, the script-src pair and the
 * <script> tag are all unchanged by this rewrite; only this file's own
 * body changes.
 *
 * Standing constraints, not just a description of this version: this
 * file must never introduce a network call, a timer, or any persistent
 * state, and must never use any HTML-writing DOM sink at all, matching
 * the CSP's own "no inline script, no on* attribute" rule (D-32) with
 * this file's own "no markup-building sink" rule. The only DOM writes
 * this file ever makes are one <img>'s "src" (always assigned from a
 * server-rendered data-preview-src attribute, never a string this file
 * builds itself) and a class-list toggle on the four usage panels and
 * on that same <img> — no markup-writing DOM sink of any kind is used
 * anywhere in this file.
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
 * .frame-colours card at all — today only Display does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention (nav-dropdown.js/battery-trend.js's own early
 * returns).
 *
 * No-JS floor (D-08, locked): companion/pages/config_page.py's own
 * panel builder NEVER emits a hidden attribute — all four
 * data-usage-panel-target panels render visible, each wrapped in its
 * own fieldset/legend, so a script-free page shows four clearly
 * labelled stacked sections and every control still submits its real
 * value. This file is the ONLY thing that ever collapses three of the
 * four — on load, it adds frame-colours__usage-panel--collapsed to
 * every panel except the one matching the checked colour_usage radio
 * (departures, by default),
 * the same per-script class-at-load pattern flight-rows.js already
 * uses for its own detail rows. A browser with JavaScript disabled (or
 * this specific script blocked by a stricter CSP directive) simply
 * never runs this file at all, and every panel stays visible and
 * saveable exactly as D-08 requires.
 *
 * 22-01-PLAN.md Task 2 (D-01/T8): exposes window.SkyPaneLivePreview, a
 * single small namespace object carrying one function, refresh() —
 * this file's own first and only global. companion/static/dirty-state.js
 * calls it after its Cancel handler's form.reset(), which restores every
 * form=-attached theme radio's checked property natively but fires no
 * change event, so this file's own delegated listener (below) never
 * hears about the reverted selection on its own. refresh() re-derives
 * the checked usage from the live DOM and re-applies its preview src -
 * the identical work the "Collapse at load" call below already does,
 * just callable again on demand.
 *
 * 28-05-PLAN.md Task 1 (CFG-75): the "only DOM writes this file ever
 * makes" sentence above was re-checked against this plan's own addition
 * (the per-strip scroll-preview tracker, near the bottom of this file)
 * and CONFIRMED STILL TRUE — the new code calls applyPreviewSrc(), the
 * SAME sink, and touches no other DOM write of any kind. It never sets a
 * radio's checked property and never dispatches a change event, so a
 * scroll only ever PREVIEWS a theme, never SELECTS one.
 */
(function () {
  "use strict";

  var card = document.querySelector(".frame-colours");
  if (!card) {
    return;
  }
  var preview = card.querySelector(".theme-live-preview__image");
  var usageRadios = card.querySelectorAll('input[name="colour_usage"]');
  var panels = card.querySelectorAll("[data-usage-panel-target]");
  if (!preview || !usageRadios.length || !panels.length) {
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

  function panelForUsage(usage) {
    var i;
    for (i = 0; i < panels.length; i++) {
      if (panels[i].getAttribute("data-usage-panel-target") === usage) {
        return panels[i];
      }
    }
    return null;
  }

  function departuresPanel() {
    return panelForUsage("departures");
  }

  // The currently-effective live-preview source for one usage panel:
  // the first checked radio inside it that is actually a theme chip
  // (carries data-preview-src) — never the first checked radio overall,
  // since the rules panel's own "Match by" segmented control and the
  // Frame colours card's own value input are checked radios too, with
  // no preview of their own.
  function checkedChipSrc(panel) {
    if (!panel) {
      return null;
    }
    var checked = panel.querySelectorAll('input[type="radio"]:checked');
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

  // Arrivals'/calendar's own leading "Same as departures" chip carries
  // no data-preview-src of its own (D-09: no fabricated theme-coloured
  // preview for "no override") — the effective preview for that usage
  // is then the departures grid's own currently-checked theme (D-12).
  function effectiveSrcForUsage(usage) {
    var panel = panelForUsage(usage);
    var src = checkedChipSrc(panel);
    if (src) {
      return src;
    }
    return checkedChipSrc(departuresPanel());
  }

  // 28-05-PLAN.md Task 1 (CFG-75): hoisted out of showUsage() so the new
  // per-strip scroll-preview tracker below can ask the SAME question
  // ("is this strip's own usage panel currently collapsed?") off the
  // ONE literal, rather than a second copy that could drift from this
  // one.
  var COLLAPSED_PANEL_CLASS = "frame-colours__usage-panel--collapsed";

  function showUsage(usage) {
    var i;
    for (i = 0; i < panels.length; i++) {
      var target = panels[i].getAttribute("data-usage-panel-target");
      var isCollapsed = panels[i].className.indexOf(COLLAPSED_PANEL_CLASS) !== -1;
      if (target === usage) {
        if (isCollapsed) {
          panels[i].className = panels[i].className.replace(
            new RegExp("\\s*" + COLLAPSED_PANEL_CLASS), "");
        }
      } else if (!isCollapsed) {
        panels[i].className += " " + COLLAPSED_PANEL_CLASS;
      }
    }
    applyPreviewSrc(effectiveSrcForUsage(usage));
  }

  function checkedUsage() {
    var i;
    for (i = 0; i < usageRadios.length; i++) {
      if (usageRadios[i].checked) {
        return usageRadios[i].value;
      }
    }
    return null;
  }

  // 22-01-PLAN.md Task 2 (D-01/T8): re-derives the checked usage and
  // re-applies its preview src from the CURRENT DOM state - the one
  // entry point dirty-state.js's Cancel handler calls after
  // form.reset(), since reset() restores every radio's checked property
  // natively but fires no change event, so this file would otherwise
  // never hear that the departures/arrivals/calendar selection just
  // reverted. Exposed as the file's own one new global, a small
  // namespace object rather than a bare function, matching this
  // codebase's "no stray globals" discipline while still giving another
  // script a named, stable entry point to call.
  function refreshFromCurrentState() {
    var usage = checkedUsage();
    if (usage) {
      showUsage(usage);
    }
  }
  window.SkyPaneLivePreview = { refresh: refreshFromCurrentState };

  // Collapse at load — the ONLY place this file ever hides a panel; see
  // the file header's own no-JS floor paragraph.
  var initialUsage = checkedUsage();
  if (initialUsage) {
    showUsage(initialUsage);
  }

  // One delegated listener on the card container, never one per radio
  // or per chip (a single usage panel can carry a full THEME_IDS-sized
  // grid) — matching this file's own pre-existing event-delegation
  // idiom, now scoped to the card rather than to a single global grid.
  card.addEventListener("change", function (evt) {
    var input = evt.target;
    if (!input || input.type !== "radio") {
      return;
    }
    if (input.name === "colour_usage") {
      showUsage(input.value);
      return;
    }
    // config_page._theme_chip_grid_html() wraps each real theme chip's
    // radio directly in its own <label class="theme-chip ...">, which
    // is where the server renders data-preview-src — the input's own
    // parentNode is that label in this exact markup shape. A checked
    // radio whose parentNode carries no "theme-chip" class at all (the
    // rules panel's own "Match by" segmented control, whose radio and
    // label are SIBLINGS, not parent/child) is never treated as a chip
    // click here.
    var chip = input.parentNode;
    if (!chip || !chip.getAttribute) {
      return;
    }
    var isThemeChip = chip.className && chip.className.indexOf("theme-chip") !== -1;
    var src = chip.getAttribute("data-preview-src");
    if (!src && isThemeChip) {
      src = checkedChipSrc(departuresPanel());
    }
    applyPreviewSrc(src);
  });

  // --- 25-06-PLAN.md Task 3 (CFG-50): D5's two carousel pagers ------
  //
  // WHY THIS FILE GREW INSTEAD OF A NEW ONE APPEARING. Phase 25's
  // budget is ONE new static script and 25-01 spent it on
  // value-controls.js; the deferred-script pin in
  // companion/test_companion_app.py is fifteen and this plan does not
  // move it. Beyond the budget, this is the right file on the merits:
  // the carousel IS the theme radio group, and this file is already
  // the one thing on the page that listens to that radio group. A
  // second file would have meant two scripts bound to one control.
  //
  // THE PAGERS ARE THE ONLY PART OF THE CAROUSEL THAT NEEDS A SCRIPT,
  // which is why they are the only part inside 25-01's .js gate. (No
  // backtick appears in this comment, or anywhere else in this file:
  // companion/test_companion_app.py bans the character outright as the
  // template-literal guard, and it does not except comments.)
  // Everything else — the strip scrolling, the eighteen radios
  // selecting, the arrow keys moving through them, the disclosure
  // opening, the whole thing saving — is native and works with this
  // file blocked.
  //
  // NO KEY LISTENER OF ANY KIND IS REGISTERED HERE, and that is
  // load-bearing rather than an omission: a pager that captured
  // ArrowLeft/ArrowRight would take those keys away from the native
  // radiogroup, and native arrow-key selection is exactly what the
  // scripts-blocked path depends on. Clicks only.
  //
  // The strip is resolved through the button's OWN aria-controls, not
  // through a class or a second data attribute, so the accessibility
  // contract and this script's contract are ONE contract: an
  // aria-controls pointing at nothing breaks the pager too, rather
  // than leaving a button that works while announcing a lie.
  var PAGER_ATTR = "data-theme-pager";

  function pagerStep(strip) {
    var chip = strip.querySelector(".theme-chip");
    var gap;
    if (!chip) {
      return strip.clientWidth;
    }
    gap = parseFloat(getComputedStyle(strip).columnGap);
    if (isNaN(gap)) {
      gap = 0;
    }
    return chip.getBoundingClientRect().width + gap;
  }

  // scrollLeft, not scrollBy({behavior: "smooth"}): an instant scroll
  // has no duration for the reduced-motion override to have an opinion
  // about, and the strip's own CSS scroll-snap settles the landing
  // position either way. This file names no duration anywhere and adds
  // none here.
  function onPagerClick(evt) {
    var button = evt.currentTarget;
    var strip = document.getElementById(button.getAttribute("aria-controls"));
    if (!strip) {
      return;
    }
    if (button.getAttribute(PAGER_ATTR) === "prev") {
      strip.scrollLeft -= pagerStep(strip);
    } else {
      strip.scrollLeft += pagerStep(strip);
    }
  }

  var pagers = card.querySelectorAll("[" + PAGER_ATTR + "]");
  var pagerIndex;
  for (pagerIndex = 0; pagerIndex < pagers.length; pagerIndex++) {
    pagers[pagerIndex].addEventListener("click", onPagerClick);
  }

  // --- 28-05-PLAN.md Task 1 (CFG-75): preview follows scroll ----------
  //
  // PREVIEW IS NOT SELECTION. Forbidden in every function below:
  // input.checked = true, dispatchEvent(new Event("change")), .click(),
  // form.requestSubmit(), writing any form value of any kind, and
  // writing the preview element's own image source through any path
  // other than applyPreviewSrc() — no direct assignment to that
  // property and no direct setAttribute call naming it. This code path
  // calls applyPreviewSrc() — the SAME sink onPagerClick's own sibling,
  // the delegated "change" listener above, already writes through —
  // and nothing else. A reload with nothing clicked must still show
  // the SAVED theme, never whatever chip a visitor last scrolled past.
  //
  // ONE TRACKER PER STRIP, built in a loop, exactly like the pagers
  // above are wired one per button rather than one shared listener for
  // all three carousels — 27-07-PLAN.md's strip_id-per-instance
  // discipline exists precisely to stop one carousel's state leaking
  // into a sibling's, and a single shared observer keyed by one strip
  // would be that exact regression.
  //
  // "CENTERED" IS A TOTAL FUNCTION OF LAYOUT, NOT A THRESHOLD TO TUNE:
  // the chip whose own getBoundingClientRect() centre X is nearest the
  // strip's own centre X, recomputed fresh on every settle. There is no
  // ambiguity when two chips are equally visible and nothing here
  // guesses at an IntersectionObserver ratio.
  function nearestCenteredChip(strip) {
    var chips = strip.querySelectorAll(".theme-chip");
    var stripRect = strip.getBoundingClientRect();
    var stripCenterX = stripRect.left + stripRect.width / 2;
    var closest = null;
    var closestDistance = Infinity;
    var i, chip, rect, chipCenterX, distance;
    for (i = 0; i < chips.length; i++) {
      chip = chips[i];
      rect = chip.getBoundingClientRect();
      chipCenterX = rect.left + rect.width / 2;
      distance = Math.abs(chipCenterX - stripCenterX);
      if (distance < closestDistance) {
        closestDistance = distance;
        closest = chip;
      }
    }
    return closest;
  }

  // Reuses the SAME panels NodeList and the SAME COLLAPSED_PANEL_CLASS
  // showUsage() already maintains — never a second, independently
  // invented visibility signal. A strip inside a collapsed usage panel
  // (i.e. not the one currently on screen) must never fight the strip
  // the visitor is actually scrolling.
  function stripPanelIsCollapsed(strip) {
    var i;
    for (i = 0; i < panels.length; i++) {
      if (panels[i].contains && panels[i].contains(strip)) {
        return panels[i].className.indexOf(COLLAPSED_PANEL_CLASS) !== -1;
      }
    }
    return false;
  }

  // One of these per strip, closing over its own lastScrollLeft so no
  // two strips ever share a byte of state.
  function makeScrollPreviewTracker(strip) {
    var lastScrollLeft = strip.scrollLeft;

    function settle() {
      // Skip a strip that is not currently displayed — reuse the same
      // signal showUsage() sets, never invent a second one.
      if (stripPanelIsCollapsed(strip)) {
        return;
      }
      // Skip when the scroll position has not actually moved, so a
      // layout reflow (a window resize, a sibling image finishing its
      // load) can never silently overwrite a preview a click just set.
      if (strip.scrollLeft === lastScrollLeft) {
        return;
      }
      lastScrollLeft = strip.scrollLeft;
      var chip = nearestCenteredChip(strip);
      if (!chip) {
        return;
      }
      // The ONLY write in this whole code path. No checked property, no
      // change event, no form value — see the forbidden-operations
      // comment above this section.
      applyPreviewSrc(chip.getAttribute("data-preview-src"));
    }

    // The plain "scroll" event covers BOTH a finger dragging the strip
    // and a programmatic scrollLeft/scrollTo() assignment (exactly how
    // onPagerClick already moves the strip, and how a check drives it)
    // — every browser fires it for both.
    strip.addEventListener("scroll", settle);

    // IntersectionObserver is the CHEAP TRIGGER where available (it
    // avoids a full settle() computation on every scroll frame), guarded
    // so a browser without it simply falls back to the scroll listener
    // above rather than throwing — a scripts-poor browser losing this
    // preview nicety is acceptable, a thrown error that kills the rest
    // of this file's behaviour is not. Its own threshold is never the
    // definition of "centered" — settle() always recomputes that fresh
    // via nearestCenteredChip(), so the observer only decides WHEN to
    // look, never WHICH chip is picked.
    if (window.IntersectionObserver) {
      var observer = new IntersectionObserver(
        function () {
          settle();
        },
        { root: strip, threshold: [0, 0.25, 0.5, 0.75, 1] });
      var obsChips = strip.querySelectorAll(".theme-chip");
      var obsIndex;
      for (obsIndex = 0; obsIndex < obsChips.length; obsIndex++) {
        observer.observe(obsChips[obsIndex]);
      }
    }
  }

  // Found the same way the pagers are found above — a loop over the
  // card's own strips, never three hardcoded ids. .theme-chip-grid
  // --strip is the modifier _theme_carousel_html()'s three call sites
  // already apply (companion/pages/config_page.py), and each strip
  // already carries its own strip_id as its element id — an addressable
  // per-instance hook that already exists, so no new attribute is
  // needed in config_page.py for this.
  var STRIP_SELECTOR = ".theme-chip-grid--strip";
  var strips = card.querySelectorAll(STRIP_SELECTOR);
  var stripIndex;
  for (stripIndex = 0; stripIndex < strips.length; stripIndex++) {
    makeScrollPreviewTracker(strips[stripIndex]);
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
