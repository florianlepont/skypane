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
 * this file ever makes are one <img>'s "src" property (always assigned
 * from a server-rendered data-preview-src attribute, never a string
 * this file builds itself) and a class-list toggle on the four usage
 * panels — no markup-writing DOM sink of any kind is used anywhere in
 * this file.
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

  function showUsage(usage) {
    var i;
    for (i = 0; i < panels.length; i++) {
      var target = panels[i].getAttribute("data-usage-panel-target");
      var collapsedClass = "frame-colours__usage-panel--collapsed";
      var isCollapsed = panels[i].className.indexOf(collapsedClass) !== -1;
      if (target === usage) {
        if (isCollapsed) {
          panels[i].className = panels[i].className.replace(
            new RegExp("\\s*" + collapsedClass), "");
        }
      } else if (!isCollapsed) {
        panels[i].className += " " + collapsedClass;
      }
    }
    var src = effectiveSrcForUsage(usage);
    if (src) {
      preview.src = src;
    }
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
    if (src) {
      preview.src = src;
    }
  });

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
