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

  var ACTIVE = ".tab-bar__link--active:not(.tab-bar__link--switch)";

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
      var cells = bar.querySelectorAll(".tab-bar__link:not(.tab-bar__link--switch)");
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
      if (!link || link === bar || link.classList.contains("tab-bar__link--switch")
          || link.classList.contains("tab-bar__link--active")
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

  var PICTURES = "img.preview-frame__image, img.look-frame__image, img.history-card__thumb-image";

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
      void img.offsetWidth;
      img.classList.add("is-revealed");
    }
  }

  function bindPicture(img) {
    img.addEventListener("load", function () {
      pictureLoaded(img, true);
    });
    img.addEventListener("error", function () {
      pictureLoaded(img, false);
    });
    img.addEventListener("animationend", function () {
      img.classList.remove("is-revealed");
    });
    if (!img.complete) {
      pictureLoading(img);
    }
  }

  var bar = document.querySelector(".tab-bar");
  if (bar) {
    initTabSlider(bar);
  }

  var pictures = document.querySelectorAll(PICTURES);
  for (var p = 0; p < pictures.length; p++) {
    bindPicture(pictures[p]);
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

  // The "Next update in ..." countdown is rewritten once a second by
  // relative-time.js; each change gets a short roll so the tick is seen.
  function initCountdownTick() {
    var host = document.querySelector(".home-state");
    if (!host || !window.MutationObserver) {
      return;
    }
    var duration = millis("--motion-fast", 180);
    var ease = token("--ease-out", "ease-out");
    var watcher = new MutationObserver(function (records) {
      for (var r = 0; r < records.length; r++) {
        var target = records[r].target;
        var el = target.nodeType === 1 ? target : target.parentNode;
        while (el && !(el.hasAttribute && el.hasAttribute("data-relative-countdown"))) {
          el = el.parentNode;
        }
        if (el) {
          play(el, [{opacity: 0.4, transform: "translateY(3px)"},
                    {opacity: 1, transform: "none"}],
               {duration: duration, easing: ease});
        }
      }
    });
    watcher.observe(host, {childList: true, characterData: true, subtree: true});
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
      if (!busy) {
        label.textContent = offset >= PULL_THRESHOLD ? release : hint;
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
                    {duration: 700, iterations: Infinity});
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
      paint(pull);
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
})();
