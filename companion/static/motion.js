/*
 * SkyPane companion service — motion.js.
 *
 * Shell script present on every authenticated page. Two small enhancements,
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
 * Every motion is skipped under prefers-reduced-motion. No build step,
 * ES5-safe subset. Served by companion/app.py's MOTION_SCRIPT_ROUTE. Never a
 * network call or persistent state; the only timer is the zero-delay one that
 * notices a cancelled tab click.
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
      for (var r = 0; r < records.length; r++) {
        pictureLoading(records[r].target);
      }
    });
    for (var w = 0; w < swapped.length; w++) {
      watcher.observe(swapped[w], {attributes: true, attributeFilter: ["src"]});
    }
  }
})();
