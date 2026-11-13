/*
 * SkyPane companion service — motion.js.
 *
 * Shell script present on every authenticated page. Small enhancements,
 * both optional: without this file every page looks and works the same, only
 * without the motion.
 *
 * - The tab bar's sliding pill. The server renders the active tab with its
 *   own pill; here one slider element is moved (a whole-pixel transform only)
 *   under the active tab, and under the tab being pressed a moment before the
 *   real navigation replaces the page. The bar's class tab-bar--slider hands
 *   the active background over to the slider, and only once the slider has a
 *   real box.
 * - Picture placeholders. While a picture is still loading its container
 *   carries .is-loading (a sweeping band, see style.css); when the picture
 *   lands the container is released and the picture fades in from a blur once.
 *   A picture already in the browser's cache is left alone.
 *
 * - Live Home: the countdown rolls on each tick, numbers count up once, a
 *   flight row the refresh brings in slides to the top (FLIP).
 * - Pull to refresh on a phone's Flights list.

 * - Airline card unlock: a card the server marks as newly seen plays a 3D
 *   flip, a glint and a few sparks once per airline and per user. "Played" is
 *   a list in localStorage keyed by the user's scope; storage that cannot be
 *   used means no animation at all (never a replay on every load). Without
 *   this script, or under reduced motion, the card is simply shown as it ends.
 *
 * Every motion is skipped under prefers-reduced-motion. No build step,
 * ES5-safe subset. Served by companion/app.py's MOTION_SCRIPT_ROUTE. Never a
 * network call or persistent state; its timers are the zero-delay one that
 * notices a cancelled tab click and the pull-to-refresh give-up timeout.
 */
(function () {
  "use strict";

  var reducedQuery = window.matchMedia
    ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  function reducedMotion() {
    return !!(reducedQuery && reducedQuery.matches);
  }

  var ACTIVE = ".tab-bar__link--active";

  function initTabSlider(bar) {
    var slider = document.createElement("span");
    slider.className = "tab-bar__slider";
    slider.setAttribute("aria-hidden", "true");
    bar.insertBefore(slider, bar.firstChild);

    // The pill spans its link's whole width and only has a vertical margin, so
    // the slider's box is derived from the link (which never animates) rather
    // than from the pill (whose own entrance briefly scales it).
    function place(link, animate) {
      var pill = link && link.querySelector(".tab-bar__pill");
      var box = link && link.getBoundingClientRect();
      if (!pill || box.width === 0) {
        bar.classList.remove("tab-bar--slider");
        return;
      }
      var style = window.getComputedStyle(pill);
      var top = parseFloat(style.marginTop) || 0;
      var bottom = parseFloat(style.marginBottom) || 0;
      var barBox = bar.getBoundingClientRect();
      var x = Math.round(box.left - barBox.left - bar.clientLeft);
      var y = Math.round(box.top + top - barBox.top - bar.clientTop);
      var glide = animate && !reducedMotion();
      slider.classList.toggle("tab-bar__slider--glide", glide);
      slider.style.width = Math.round(box.width) + "px";
      slider.style.height = Math.round(box.height - top - bottom) + "px";
      slider.style.transform = "translate(" + x + "px, " + y + "px)";
      if (glide) {
        slider.classList.remove("tab-bar__slider--stretch");
        void slider.offsetWidth;
        slider.classList.add("tab-bar__slider--stretch");
      }
      bar.classList.add("tab-bar--slider");
    }

    function setActive(link) {
      var cells = bar.querySelectorAll(".tab-bar__link");
      for (var i = 0; i < cells.length; i++) {
        cells[i].classList.toggle("tab-bar__link--active", cells[i] === link);
      }
    }

    function settle() {
      place(bar.querySelector(ACTIVE), false);
    }

    settle();
    window.addEventListener("resize", settle);
    window.addEventListener("load", settle);
    window.addEventListener("pageshow", settle);
    // The cells may still change size after the first paint (fonts, icons, a
    // late stylesheet); the slider follows whatever the active cell ends up as.
    if (window.ResizeObserver) {
      var sizes = new ResizeObserver(settle);
      var cells = bar.querySelectorAll(".tab-bar__link");
      for (var c = 0; c < cells.length; c++) {
        sizes.observe(cells[c]);
      }
    }
    slider.addEventListener("animationend", function () {
      slider.classList.remove("tab-bar__slider--stretch");
    });

    bar.addEventListener("click", function (evt) {
      var link = evt.target;
      while (link && link !== bar && !(link.tagName === "A"
          && link.classList.contains("tab-bar__link"))) {
        link = link.parentNode;
      }
      if (!link || link === bar || link.classList.contains("tab-bar__link--active")
          || evt.button !== 0 || evt.metaKey || evt.ctrlKey || evt.shiftKey || evt.altKey
          || link.hasAttribute("target")) {
        return;
      }
      var from = bar.querySelector(ACTIVE);
      setActive(link);
      place(link, true);
      // Another handler may still cancel the navigation (an unsaved-changes
      // guard): then the pill returns to the tab the page really is on.
      window.setTimeout(function () {
        if (evt.defaultPrevented) {
          setActive(from);
          place(from, true);
        }
      }, 0);
    });
  }

  // --- Tab strips -----------------------------------------------------------
  // Any segmented strip marked data-tabs (the Style and Fleet section links,
  // the Flights, Airlines and Audit filter chips) gets one thumb behind its
  // segments that slides under the current one. A strip whose segments are
  // links is a page change: the thumb is under the current segment from the
  // start and never slides after the page opened (the page change itself
  // carries the selection across, see the stylesheet's skypane-strip). A
  // strip of radios moves on change. A strip may name the
  // content its segments switch (data-tabs-content, a selector) and the
  // content replays the shared entrance, or only a fade with
  // data-tabs-replay="fade". The thumb moves by transform and width alone and
  // the replay is opacity and translate, so neither lays anything out again.
  var STRIP_ITEMS = "A, LABEL, BUTTON";

  function replay(target, fadeOnly) {
    if (!target || reducedMotion()) {
      return;
    }
    // Cancel whatever the element already played (a finished entrance, or one
    // an earlier replay left behind) so the new one starts from its first frame.
    target.classList.remove("reveal-replay", "reveal-replay--fade");
    target.style.animationName = "none";
    void target.offsetWidth;
    target.style.animationName = "";
    target.classList.add("reveal-replay");
    if (fadeOnly) {
      target.classList.add("reveal-replay--fade");
    }
    if (!target.hasAttribute("data-replay-bound")) {
      target.setAttribute("data-replay-bound", "");
      target.addEventListener("animationend", function (evt) {
        if (evt.target === target && evt.animationName === "skypane-reveal-fade") {
          // A replay that ends while the page opening is still marked would
          // hand the element back to the opening's rule and its rise would
          // start again under content that is already in place.
          var main = document.querySelector("main[data-page-open]");
          if (main && main.contains(target)) {
            main.removeAttribute("data-page-open");
          }
          target.classList.remove("reveal-replay", "reveal-replay--fade");
        }
      });
    }
  }

  // A row or card the list just appended enters like the first screenful did;
  // the caller marks only the first few.
  function appended(el) {
    // The phone cards and the desktop table are both updated; the one the
    // breakpoint hides has no box and would never end the animation.
    if (!el || reducedMotion() || !el.getClientRects().length) {
      return;
    }
    el.classList.add("reveal-appended");
    el.addEventListener("animationend", function done(evt) {
      if (evt.target === el && evt.animationName === "skypane-reveal-fade") {
        el.classList.remove("reveal-appended");
        el.removeEventListener("animationend", done);
      }
    });
  }
  window.SkyPaneMotion = { replay: replay, appended: appended };

  function stripItems(strip) {
    var items = [];
    for (var i = 0; i < strip.children.length; i++) {
      if (STRIP_ITEMS.indexOf(strip.children[i].tagName) !== -1) {
        items.push(strip.children[i]);
      }
    }
    return items;
  }

  function stripCurrent(items) {
    for (var i = 0; i < items.length; i++) {
      var el = items[i];
      if (el.hasAttribute("aria-current") || el.getAttribute("aria-pressed") === "true"
          || el.querySelector("input:checked")) {
        return i;
      }
    }
    return -1;
  }

  // `carried` is the geometry the thumb of the strip this one replaces had (an
  // in-place swap renders the strip again): the new thumb starts there and
  // slides to the current segment.
  function initTabStrip(strip, carried) {
    if (strip.hasAttribute("data-tabs-ready")) {
      return;
    }
    strip.setAttribute("data-tabs-ready", "");
    var items = stripItems(strip);
    var wantsThumb = strip.getAttribute("data-tabs-thumb") !== "none";
    var thumb = null;
    if (wantsThumb && items.length) {
      thumb = document.createElement("span");
      thumb.className = "tabs-thumb";
      thumb.setAttribute("data-tabs-thumb", "");
      thumb.setAttribute("aria-hidden", "true");
      var lead = strip.firstElementChild;
      strip.insertBefore(thumb, lead && lead.tagName === "LEGEND" ? lead.nextSibling : lead);
    }

    function face(item) {
      return item.querySelector(".filter-chip__box") || item.querySelector("span") || item;
    }

    // False while the strip has no box (a strip a breakpoint hides).
    function place(index) {
      var box = face(items[index]).getBoundingClientRect();
      if (!box.width) {
        strip.classList.remove("is-enhanced");
        return false;
      }
      var host = strip.getBoundingClientRect();
      // Both edges are rounded, not the left edge and the width, so the first
      // and last choices keep the same inset from the track whatever the
      // fractional layout.
      var left = Math.round(box.left - host.left - strip.clientLeft);
      var right = Math.round(box.right - host.left - strip.clientLeft);
      var top = Math.round(box.top - host.top - strip.clientTop);
      var bottom = Math.round(box.bottom - host.top - strip.clientTop);
      thumb.style.width = (right - left) + "px";
      thumb.style.height = (bottom - top) + "px";
      thumb.style.transform = "translate(" + left + "px, " + top + "px)";
      strip.classList.add("is-enhanced");
      return true;
    }

    var index = stripCurrent(items);
    if (thumb && index !== -1) {
      if (carried && !reducedMotion()) {
        thumb.style.width = carried.width;
        thumb.style.height = carried.height;
        thumb.style.transform = carried.transform;
        strip.classList.add("is-enhanced");
        thumb.getBoundingClientRect();
        thumb.classList.add("is-sliding");
        place(index);
      } else {
        place(index);
      }
      // Re-place the thumb only when the strip's own geometry changed (fonts,
      // a resize): the observers also report their first measurement, which
      // must not cut a slide short.
      var geometry = function () {
        var sizes = [strip.offsetWidth];
        for (var g = 0; g < items.length; g++) {
          sizes.push(items[g].offsetWidth, items[g].offsetLeft);
        }
        return sizes.join(",");
      };
      var placed = geometry();
      var settleStrip = function () {
        var now = stripCurrent(items);
        var seen = geometry();
        if (now !== -1 && seen !== placed) {
          placed = seen;
          thumb.classList.remove("is-sliding");
          place(now);
        }
      };
      window.addEventListener("resize", settleStrip);
      window.addEventListener("load", settleStrip);
      if (window.ResizeObserver) {
        var watcher = new ResizeObserver(settleStrip);
        watcher.observe(strip);
        for (var w = 0; w < items.length; w++) {
          watcher.observe(items[w]);
        }
      }
    }

    strip.addEventListener("change", function () {
      var now = stripCurrent(items);
      if (thumb && now !== -1) {
        if (!reducedMotion()) {
          thumb.classList.add("is-sliding");
        }
        place(now);
      }
      var selector = strip.getAttribute("data-tabs-content");
      if (selector) {
        replay(document.querySelector(selector),
          strip.getAttribute("data-tabs-replay") === "fade");
      }
    });
  }

  function enhanceTabs(root, carried) {
    var found = root.querySelectorAll ? root.querySelectorAll("[data-tabs]") : [];
    for (var t = 0; t < found.length; t++) {
      initTabStrip(found[t], carried ? carried[found[t].getAttribute("data-tabs")] : null);
    }
  }

  // Where each strip's thumb is now, by strip name.
  function tabsState(root) {
    var state = {};
    var found = root.querySelectorAll("[data-tabs]");
    for (var t = 0; t < found.length; t++) {
      var thumb = found[t].querySelector("[data-tabs-thumb]");
      if (thumb && thumb.style.transform) {
        state[found[t].getAttribute("data-tabs")] = {
          width: thumb.style.width, height: thumb.style.height,
          transform: thumb.style.transform
        };
      }
    }
    return state;
  }

  window.SkyPaneMotion.enhanceTabs = enhanceTabs;
  window.SkyPaneMotion.tabsState = tabsState;
  enhanceTabs(document, null);

  var PICTURES = "img.preview-frame__image, img.look-frame__image, img.history-card__thumb-image";
  // Small pictures that fade in when they arrive but never shimmer their
  // container (a card, a row or a list of fifty).
  var QUIET_PICTURES = "img.collection-card__image, img.airlines-thumb__image, " +
    "img.special-row__image, img.layout-card__thumb, img.look-pick__preview";

  function pictureLoading(img) {
    if (img.parentNode) {
      img.parentNode.classList.add("is-loading");
    }
    img.classList.remove("is-revealed");
  }

  function pictureLoaded(img, ok) {
    if (img.parentNode) {
      img.parentNode.classList.remove("is-loading");
    }
    if (ok && !reducedMotion()) {
      revealQueue.push(img);
      if (!revealFrame) {
        revealFrame = window.requestAnimationFrame(flushReveals);
      }
    }
  }

  // Pictures that loaded in the same frame fade in together. A picture
  // that still carries the class from an earlier reveal restarts its
  // animation; the one forced reflow covers all of them.
  var revealQueue = [];
  var revealFrame = 0;
  function flushReveals() {
    var batch = revealQueue;
    var restart = false;
    revealQueue = [];
    revealFrame = 0;
    for (var i = 0; i < batch.length; i++) {
      if (batch[i].classList.contains("is-revealed")) {
        batch[i].classList.remove("is-revealed");
        restart = true;
      }
    }
    if (restart) {
      void document.documentElement.offsetWidth;
    }
    for (var j = 0; j < batch.length; j++) {
      batch[j].classList.add("is-revealed");
    }
  }

  function bindPicture(img, quiet) {
    img.addEventListener("load", function () {
      pictureLoaded(img, true);
    });
    img.addEventListener("error", function () {
      pictureLoaded(img, false);
    });
    img.addEventListener("animationend", function () {
      img.classList.remove("is-revealed");
    });
    if (!img.complete && !quiet) {
      pictureLoading(img);
    }
  }

  var bar = document.querySelector(".tab-bar");
  if (bar) {
    initTabSlider(bar);
  }

  var pictures = document.querySelectorAll(PICTURES);
  for (var p = 0; p < pictures.length; p++) {
    bindPicture(pictures[p], false);
  }
  var quietPictures = document.querySelectorAll(QUIET_PICTURES);
  for (var q = 0; q < quietPictures.length; q++) {
    bindPicture(quietPictures[q], true);
  }

  // The Style preview swaps one picture's src as the choice changes.
  if (window.MutationObserver) {
    var swapped = document.querySelectorAll("[data-look-image]");
    var watcher = new MutationObserver(function (records) {
      if (countingUp > 0) {
        return;
      }
      for (var r = 0; r < records.length; r++) {
        pictureLoading(records[r].target);
      }
    });
    for (var w = 0; w < swapped.length; w++) {
      watcher.observe(swapped[w], {attributes: true, attributeFilter: ["src"]});
    }
  }

  // ---- Live Home and pull to refresh -------------------------------------

  var pageKey = document.body ? document.body.getAttribute("data-refresh-page") : null;

  // A motion length or easing from the stylesheet's own tokens; the second
  // argument is only the answer when the stylesheet did not load.
  function token(name, fallback) {
    var value = window.getComputedStyle(document.documentElement)
      .getPropertyValue(name);
    return value && value.replace(/^\s+|\s+$/g, "") || fallback;
  }

  function millis(name, fallback) {
    var value = token(name, "");
    var number = parseFloat(value);
    if (isNaN(number)) {
      return fallback;
    }
    return /ms$/.test(value) ? number : number * 1000;
  }

  function play(el, frames, options) {
    if (reducedMotion() || !el.animate) {
      return null;
    }
    return el.animate(frames, options);
  }

  // The "Next update in ..." countdown is rewritten by relative-time.js. In
  // its last minute the text changes every second and stays plain text: a
  // roll a second is a nudge nobody can pause. A coarser change (one minute
  // less) gets one short roll. A rewrite that leaves the text as it was, the
  // count-up below and the text a refresh brings with a new hero roll
  // nothing. The watcher follows the hero across the refresh that replaces it.
  function initCountdownTick() {
    if (!window.MutationObserver) {
      return;
    }
    var duration = millis("--motion-fast", 180);
    var ease = token("--ease-out", "ease-out");
    var host = null;
    var shown = null;

    function lastMinute(el) {
      var at = new Date(el.getAttribute("datetime") || "").getTime();
      return isNaN(at) || Math.abs(at - new Date().getTime()) < 60000;
    }

    var watcher = new MutationObserver(function () {
      var el = host && host.querySelector("[data-relative-countdown]");
      if (!el) {
        return;
      }
      var text = el.textContent;
      var changed = shown !== null && text !== shown;
      shown = text;
      if (changed && !countingUp && !lastMinute(el)) {
        play(el, [{opacity: 0.4, transform: "translateY(3px)"},
                  {opacity: 1, transform: "none"}],
             {duration: duration, easing: ease});
      }
    });

    function watch() {
      var next = document.querySelector(".home-state");
      if (next === host) {
        return;
      }
      watcher.disconnect();
      host = next;
      if (host) {
        var el = host.querySelector("[data-relative-countdown]");
        shown = el ? el.textContent : null;
        watcher.observe(host, {childList: true, characterData: true, subtree: true});
      }
    }
    watch();
    document.addEventListener("skypane-regions-swapped", watch);
  }

  // Numbers on Home count up once, on first render: the leading figure of
  // the next-update countdown and the battery reading. The last frame writes
  // the server's own text back. The count starts at the smallest number of
  // the same digit count so the line does not change width.
  var countingUp = 0;

  function initCountUp() {
    if (reducedMotion() || !window.requestAnimationFrame) {
      return;
    }
    var els = document.querySelectorAll(
      ".home-battery__value, .home-state__next [data-relative-countdown]");
    var duration = millis("--motion-count", 600);
    Array.prototype.forEach.call(els, function (el) {
      var node = el.firstChild;
      var parts = node && node.nodeType === 3 ? /^(\D*?)(\d+)(\D[\s\S]*|)$/.exec(node.nodeValue) : null;
      if (!parts) {
        return;
      }
      var text = node.nodeValue;
      var lead = parts[1];
      var rest = parts[3];
      var target = parseInt(parts[2], 10);
      var from = parts[2].length > 1 ? Math.pow(10, parts[2].length - 1) : 0;
      if (target <= from) {
        return;
      }
      var begin = null;
      countingUp += 1;
      node.nodeValue = lead + from + rest;
      function step(now) {
        if (begin === null) {
          begin = now;
        }
        var t = Math.min(1, (now - begin) / duration);
        if (t >= 1 || !node.parentNode) {
          node.nodeValue = text;
          countingUp -= 1;
          return;
        }
        node.nodeValue = lead + (from + Math.round((target - from) * (1 - Math.pow(1 - t, 3)))) + rest;
        window.requestAnimationFrame(step);
      }
      window.requestAnimationFrame(step);
    });
  }

  // A new flight row brought in by the freshness swap slides in at the top
  // while the rows below glide down from where they were (FLIP, whole
  // pixels, transform and opacity only).
  var HOME_ROWS = 'section[aria-labelledby="home-flights"] li.row';

  function rowKey(li) {
    var name = li.querySelector(".mono");
    var detail = li.querySelector(".row__detail");
    return (name ? name.textContent : "") + "|" + (detail ? detail.textContent : "");
  }

  function readRows() {
    var rows = {};
    var nodes = document.querySelectorAll(HOME_ROWS);
    for (var i = 0; i < nodes.length; i++) {
      rows[rowKey(nodes[i])] = Math.round(nodes[i].getBoundingClientRect().top);
    }
    return rows;
  }

  function initRowSlide() {
    var before = null;
    document.addEventListener("skypane-regions-swapping", function () {
      before = readRows();
    });
    document.addEventListener("skypane-regions-swapped", function () {
      var was = before;
      before = null;
      if (!was) {
        return;
      }
      var duration = millis("--motion-enter", 400);
      var ease = token("--ease-out", "ease-out");
      var nodes = document.querySelectorAll(HOME_ROWS);
      for (var i = 0; i < nodes.length; i++) {
        var key = rowKey(nodes[i]);
        if (!Object.prototype.hasOwnProperty.call(was, key)) {
          play(nodes[i], [{opacity: 0, transform: "translateY(-14px)"},
                          {opacity: 1, transform: "none"}],
               {duration: duration, easing: ease});
          continue;
        }
        var shift = was[key] - Math.round(nodes[i].getBoundingClientRect().top);
        if (shift !== 0) {
          play(nodes[i], [{transform: "translateY(" + shift + "px)"},
                          {transform: "none"}],
               {duration: duration, easing: ease});
        }
      }
    });
  }

  if (pageKey === "home") {
    initCountdownTick();
    initCountUp();
    initRowSlide();
  }

  // Pull to refresh on a phone's Flights list. A downward drag that starts
  // with the page at the top moves the list with the finger; past the
  // threshold the release asks freshness.js for a refresh (a reload when
  // the page has no refresh loop), then the list comes back with a short
  // staggered entrance.
  var PULL_THRESHOLD = 56;
  var PULL_MAX = 90;
  // The spinner turns for as long as the give-up timeout below (6 s at 700 ms a turn).
  var SPIN_TURNS = 9;
  var PULL_START = 8;

  function initPullToRefresh() {
    var phone = window.matchMedia("(max-width: 699.98px)");
    // The list is a swap target: looked up fresh, never held.
    function getList() {
      return document.querySelector(".history-cards");
    }
    if (!getList()) {
      return;
    }
    var hint = document.body.getAttribute("data-pull-text") || "Pull to refresh";
    var release = document.body.getAttribute("data-pull-release-text")
      || "Release to refresh";
    var indicator = document.createElement("div");
    indicator.className = "pull-indicator";
    indicator.setAttribute("aria-hidden", "true");
    var icon = document.querySelector("[data-refresh-pill] svg");
    var glyph = icon ? icon.cloneNode(true) : null;
    if (glyph) {
      glyph.setAttribute("class", "icon pull-indicator__icon");
      indicator.appendChild(glyph);
    }
    var label = document.createElement("span");
    label.className = "pull-indicator__label";
    indicator.appendChild(label);
    document.body.appendChild(indicator);

    var startY = null;
    var startX = 0;
    var pull = 0;
    var pulling = false;
    var busy = false;
    var spin = null;

    function pillText() {
      var pill = document.querySelector("[data-refresh-pill]");
      var text = pill ? pill.textContent.replace(/^\s+|\s+$/g, "") : "";
      return text || "Updating…";
    }

    function paint(offset) {
      var list = getList();
      offset = Math.round(offset);
      var moving = !reducedMotion();
      if (list) {
        list.style.transform = moving && offset ? "translateY(" + offset + "px)" : "";
      }
      indicator.style.setProperty("--pull-offset", offset + "px");
      indicator.style.opacity = String(Math.min(1, offset / 36));
      if (glyph && !spin && moving) {
        glyph.style.transform = "rotate(" + (offset >= PULL_THRESHOLD ? 180
          : Math.round(Math.min(180, offset * 3.2))) + "deg)";
      }
      var text = offset >= PULL_THRESHOLD ? release : hint;
      if (!busy && label.textContent !== text) {
        label.textContent = text;
      }
    }

    // pointermove can fire faster than frames: the latest offset is painted
    // once per frame, and a release paints from the same state.
    var frame = 0;
    function schedulePaint() {
      if (!frame) {
        frame = window.requestAnimationFrame(function () {
          frame = 0;
          paint(pull);
        });
      }
    }
    function cancelPaint() {
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
    }

    function settle() {
      var list = getList();
      if (list) {
        list.classList.add("is-pull-settling");
      }
      indicator.classList.add("is-pull-settling");
      paint(0);
      indicator.style.opacity = "0";
      document.body.classList.remove("is-pulling");
    }

    document.addEventListener("transitionend", function (evt) {
      if (evt.target.classList && evt.target.classList.contains("is-pull-settling")) {
        evt.target.classList.remove("is-pull-settling");
      }
    });

    function entrance() {
      var cards = document.querySelectorAll("li.history-card");
      var stagger = millis("--motion-stagger", 60);
      var duration = millis("--motion-enter", 400);
      var ease = token("--ease-out", "ease-out");
      for (var i = 0; i < cards.length && i < 8; i++) {
        play(cards[i], [{opacity: 0, transform: "translateY(10px)"},
                        {opacity: 1, transform: "none"}],
             {duration: duration, delay: i * stagger, easing: ease, fill: "backwards"});
      }
    }

    function finish() {
      document.removeEventListener("skypane-refresh-done", finish);
      window.clearTimeout(giveUp);
      if (spin) {
        spin.cancel();
        spin = null;
      }
      if (glyph) {
        glyph.style.transform = "";
      }
      busy = false;
      settle();
      entrance();
    }

    var giveUp = 0;

    function trigger() {
      busy = true;
      label.textContent = pillText();
      if (glyph) {
        glyph.style.transform = "";
        spin = play(glyph, [{transform: "rotate(0deg)"}, {transform: "rotate(360deg)"}],
                    {duration: 700, iterations: SPIN_TURNS});
      }
      paint(PULL_THRESHOLD);
      document.addEventListener("skypane-refresh-done", finish);
      giveUp = window.setTimeout(finish, 6000);
      var evt = document.createEvent("Event");
      evt.initEvent("skypane-refresh-request", false, false);
      document.dispatchEvent(evt);
      if (!evt.handled) {
        window.location.reload();
      }
    }

    function blocked(target) {
      if (busy || window.scrollY > 1 || !phone.matches
          || document.querySelector("dialog[open]")) {
        return true;
      }
      for (var el = target; el && el !== document.body; el = el.parentNode) {
        if (el.nodeType !== 1) {
          continue;
        }
        var tag = el.tagName;
        if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA"
            || el.isContentEditable) {
          return true;
        }
        if (el.scrollWidth > el.clientWidth + 1) {
          var overflow = window.getComputedStyle(el).overflowX;
          if (overflow === "auto" || overflow === "scroll") {
            return true;
          }
        }
      }
      return false;
    }

    document.addEventListener("pointerdown", function (evt) {
      if (!evt.isPrimary || (evt.pointerType === "mouse" && evt.button !== 0)
          || blocked(evt.target)) {
        return;
      }
      startY = evt.clientY;
      startX = evt.clientX;
      pull = 0;
      pulling = false;
    });

    document.addEventListener("pointermove", function (evt) {
      if (startY === null || !evt.isPrimary) {
        return;
      }
      var dy = evt.clientY - startY;
      var dx = evt.clientX - startX;
      if (!pulling) {
        if (dy < -PULL_START || Math.abs(dx) > PULL_START && Math.abs(dx) > dy) {
          startY = null;
          return;
        }
        if (dy < PULL_START) {
          return;
        }
        if (window.scrollY > 1) {
          startY = null;
          return;
        }
        pulling = true;
        var list = getList();
        if (!list) {
          startY = null;
          return;
        }
        indicator.style.setProperty(
          "--pull-top", Math.round(list.getBoundingClientRect().top) + "px");
        list.classList.remove("is-pull-settling");
        indicator.classList.remove("is-pull-settling");
        document.body.classList.add("is-pulling");
      }
      pull = Math.max(0, Math.min(dy * 0.5, PULL_MAX));
      schedulePaint();
      if (evt.cancelable) {
        evt.preventDefault();
      }
    });

    function end() {
      if (startY === null) {
        return;
      }
      var wasPulling = pulling;
      var reached = pull >= PULL_THRESHOLD;
      cancelPaint();
      startY = null;
      pulling = false;
      pull = 0;
      if (!wasPulling) {
        return;
      }
      if (reached) {
        trigger();
      } else {
        settle();
      }
    }

    document.addEventListener("pointerup", end);
    document.addEventListener("pointercancel", end);

    // Lets a touch drag reach the page only while it starts at the top: the
    // browser keeps every other vertical pan for scrolling.
    function mark() {
      var list = getList();
      if (list) {
        list.classList.toggle("is-pullable", window.scrollY <= 1);
      }
    }
    window.addEventListener("scroll", mark, {passive: true});
    document.addEventListener("skypane-regions-swapped", mark);
    mark();
  }

  if (pageKey === "flights") {
    initPullToRefresh();
  }
  // ---- Airline card unlock -------------------------------------------------
  var SPARKS = [[-100, -60], [100, -70], [-120, 20], [120, 30], [0, -95], [-55, 85], [65, 90], [30, -80]];

  function unlockStore(scope) {
    var key = "skypane.unlocked." + scope;
    try {
      var raw = window.localStorage.getItem(key);
      var list = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(list)) {
        list = [];
      }
      return {
        has: function (slug) { return list.indexOf(slug) !== -1; },
        add: function (slug) {
          if (list.indexOf(slug) === -1) {
            list.push(slug);
            window.localStorage.setItem(key, JSON.stringify(list));
          }
        }
      };
    } catch (err) {
      return null;
    }
  }

  function playUnlock(item) {
    var card = item.querySelector("a.collection-card");
    if (!card || !card.animate) {
      return;
    }
    var glint = document.createElement("span");
    glint.className = "unlock-glint";
    glint.setAttribute("aria-hidden", "true");
    var sweep = document.createElement("i");
    sweep.className = "unlock-glint__sweep";
    glint.appendChild(sweep);
    card.appendChild(glint);
    var glintMs = millis("--motion-reveal", 900);
    var ease = token("--ease-out", "ease-out");
    card.animate(
      [{transform: "rotateY(90deg)"}, {transform: "rotateY(0deg)"}],
      {duration: millis("--motion-unlock", 560),
       easing: token("--motion-spring", "cubic-bezier(0.34, 1.56, 0.64, 1)")});
    sweep.animate(
      [{transform: "translateX(-120%)"}, {transform: "translateX(120%)"}],
      {duration: glintMs, delay: 300, easing: ease, fill: "both"}
    ).finished.then(function () {
      glint.remove();
    }, function () {
      glint.remove();
    });
    SPARKS.forEach(function (to, index) {
      var spark = document.createElement("i");
      spark.className = "unlock-spark";
      spark.setAttribute("aria-hidden", "true");
      item.appendChild(spark);
      spark.animate(
        [{opacity: 1, transform: "translate(0, 0) scale(1)"},
         {opacity: 0, transform: "translate(" + to[0] + "px, " + to[1] + "px) scale(0.3)"}],
        {duration: glintMs, delay: 300 + index * 25, easing: ease, fill: "both"}
      ).finished.then(function () {
        spark.remove();
      }, function () {
        spark.remove();
      });
    });
  }

  function initCardUnlock() {
    var grid = document.querySelector(".collection-grid[data-unlock-scope]");
    if (!grid) {
      return;
    }
    var store = unlockStore(grid.getAttribute("data-unlock-scope"));
    var items = grid.querySelectorAll(".collection-item[data-unlock]");
    if (!store) {
      return;
    }
    function settle(item) {
      var slug = item.getAttribute("data-unlock");
      try {
        store.add(slug);
      } catch (err) {
        return;
      }
      if (!reducedMotion()) {
        playUnlock(item);
      }
    }
    for (var i = 0; i < items.length; i += 1) {
      (function (item) {
        if (store.has(item.getAttribute("data-unlock"))) {
          return;
        }
        if (!window.IntersectionObserver) {
          settle(item);
          return;
        }
        // The flip plays when the card is actually on screen.
        var watcher = new IntersectionObserver(function (entries) {
          if (entries[0].isIntersecting) {
            watcher.disconnect();
            settle(item);
          }
        }, {threshold: 0.6});
        watcher.observe(item);
      })(items[i]);
    }
  }

  initCardUnlock();

  // ---- The page opening plays once --------------------------------------------
  // The stylesheet stages the opening under main[data-page-open]. When the
  // last of its animations has ended the mark is dropped, so content a
  // refresh, a filter or a switch puts in later arrives without replaying it.
  // The animations fill backwards only: dropping the rule changes no pixel.
  function initPageOpen() {
    var main = document.querySelector("main[data-page-open]");
    if (!main || !main.getAnimations) {
      return;
    }
    function opening() {
      var running = main.getAnimations({ subtree: true });
      for (var i = 0; i < running.length; i++) {
        var name = running[i].animationName || "";
        if (name.indexOf("skypane-reveal") === 0 && running[i].playState !== "finished") {
          return true;
        }
      }
      return false;
    }
    // A page that keeps its header back while it boots (the map) has not
    // opened yet: the opening plays when the header gets its box.
    function shown() {
      var header = main.querySelector(".page-header");
      return !header || header.getClientRects().length > 0;
    }
    function check() {
      if (!main.hasAttribute("data-page-open") || !shown() || opening()) {
        return;
      }
      main.removeAttribute("data-page-open");
      main.removeEventListener("animationend", check);
      main.removeEventListener("animationcancel", check);
      window.removeEventListener("load", check);
    }
    main.addEventListener("animationend", check);
    main.addEventListener("animationcancel", check);
    window.addEventListener("load", check);
    if (document.readyState === "complete") {
      check();
    }
  }

  initPageOpen();

  // ---- Ambient rest ----------------------------------------------------------
  // Home's slow ambient loops (the status dot, the glow and glint on the
  // picture) keep the compositor drawing every frame. They run for a minute
  // after the page is shown or touched, then `data-ambient="rest"` on <html>
  // switches them off in the stylesheet; any touch, key press or return to the
  // tab starts them again for another minute.
  var AMBIENT_MS = 60000;
  var ambientTimer = 0;

  function ambientRest() {
    document.documentElement.setAttribute("data-ambient", "rest");
  }

  function ambientWake() {
    document.documentElement.removeAttribute("data-ambient");
    window.clearTimeout(ambientTimer);
    ambientTimer = window.setTimeout(ambientRest, AMBIENT_MS);
  }

  if (document.querySelector(".home-state__dot--pulse, .hero__picture")) {
    ["pointerdown", "keydown"].forEach(function (name) {
      document.addEventListener(name, ambientWake, {passive: true});
    });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") {
        ambientWake();
      } else {
        ambientRest();
      }
    });
    ambientWake();
  }
})();
