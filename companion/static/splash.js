/* The opening splash, "Cadre": a blank frame outline draws itself, the
 * e-paper refresh runs inside it (one inversion, four colour sweeps, a scan
 * line that uncovers the logo from its ghost), the real preload progress
 * thickens the outline, and at 100% the page opens from the frame's
 * rectangle. It runs only when splash-boot.js has put `splash-on` on <html>
 * (once per browser session, not without scripts).
 *
 * Preloaded for real, each group reporting its own events: the fonts, the
 * stylesheets, the page's scripts (the motion assets, seen through resource
 * timing) and the key images. Hard cap: the whole splash, opening included,
 * never lasts longer than CAP_MS. Reduced motion: the logo and the progress
 * are static, then the page is revealed at once.
 *
 * Photosensitivity: the sequence below is the whole list of moving parts;
 * exactly one of them is a luminance flash (the inversion, a soft 340 ms
 * fade), and the sweeps are narrow soft bands, so the splash never exceeds
 * one flash per second (the limit is three). Every dynamic value goes
 * through attributes, classes and the Web Animations API: no inline style.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var overlay = document.querySelector("[data-splash]");
  if (!root.classList.contains("splash-on")) {
    return;
  }
  if (!overlay) {
    root.classList.remove("splash-on");
    return;
  }

  var CAP_MS = 3000;
  // The preload counts as done at this moment whatever the network says, so
  // the scan, the opening and the finish still fit under the cap.
  var FORCE_DONE_MS = 1900;

  var SEQUENCE = [
    { name: "outline", kind: "draw", at: 0, duration: 460 },
    { name: "inversion", kind: "flash", at: 420, duration: 340 },
    { name: "sweep-1", kind: "sweep", at: 740, duration: 520 },
    { name: "sweep-2", kind: "sweep", at: 810, duration: 520 },
    { name: "sweep-3", kind: "sweep", at: 880, duration: 520 },
    { name: "sweep-4", kind: "sweep", at: 950, duration: 520 },
    { name: "scan", kind: "scan", at: 950, duration: 320 },
    { name: "open", kind: "open", at: 1370, duration: 520 }
  ];
  SEQUENCE.forEach(Object.freeze);
  Object.freeze(SEQUENCE);

  var api = {
    sequence: SEQUENCE,
    capMs: CAP_MS,
    flashLog: [],
    state: "playing"
  };
  window.skypaneSplash = api;

  function pick(selector) {
    return overlay.querySelector(selector);
  }

  var frame = pick(".splash__frame");
  var ink = pick(".splash__ink");
  var bands = overlay.querySelectorAll(".splash__band");
  var sharp = pick(".splash__logo--sharp");
  var scan = pick(".splash__scan");
  var track = pick(".splash__track");
  var bar = pick(".splash__bar");
  var caption = pick(".splash__caption");
  var label = pick(".splash__label");
  var percentEl = pick(".splash__percent");

  var reducedQuery = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  var staticMode = !!(reducedQuery && reducedQuery.matches) || typeof overlay.animate !== "function";
  var anims = [];
  var inerted = [];
  var finished = false;
  var startedAt = window.performance.now();

  function animate(el, keyframes, options) {
    var animation = el.animate(keyframes, options);
    anims.push(animation);
    return animation;
  }

  // ---- The page below stays inert while the splash shows ------------------

  function pageElements() {
    var found = [];
    for (var node = document.body.firstElementChild; node; node = node.nextElementSibling) {
      var tag = node.tagName.toLowerCase();
      if (node === overlay || tag === "script" || tag === "template" || tag === "svg") {
        continue;
      }
      found.push(node);
    }
    return found;
  }

  // The label is a live status only while the splash runs, so a hidden
  // overlay never answers a page-wide status query.
  if (label) {
    label.setAttribute("role", "status");
  }

  var pageNodes = pageElements();
  pageNodes.forEach(function (node) {
    if (!node.hasAttribute("inert")) {
      node.setAttribute("inert", "");
      inerted.push(node);
    }
  });

  // ---- Real preload progress ----------------------------------------------

  var GROUP_WEIGHTS = { fonts: 0.1, styles: 0.2, scripts: 0.3, images: 0.4 };
  var groups = { fonts: 0, styles: 0, scripts: 0, images: 0 };

  function fontsGroup() {
    if (!document.fonts || !document.fonts.ready) {
      groups.fonts = 1;
      return;
    }
    if (document.fonts.status === "loaded") {
      groups.fonts = 1;
    }
    document.fonts.ready.then(function () {
      groups.fonts = 1;
    }, function () {
      groups.fonts = 1;
    });
  }

  function stylesGroup() {
    var links = document.querySelectorAll('link[rel="stylesheet"]');
    var done = 0;
    if (!links.length) {
      groups.styles = 1;
      return;
    }
    function settle() {
      done += 1;
      groups.styles = done / links.length;
    }
    for (var i = 0; i < links.length; i += 1) {
      if (links[i].sheet) {
        settle();
      } else {
        links[i].addEventListener("load", settle);
        links[i].addEventListener("error", settle);
      }
    }
  }

  var scriptUrls = [];

  function scriptsGroup() {
    var tags = document.querySelectorAll("script[src]");
    for (var i = 0; i < tags.length; i += 1) {
      if (tags[i].src.indexOf("/static/splash") === -1) {
        scriptUrls.push(tags[i].src);
      }
    }
    if (!scriptUrls.length) {
      groups.scripts = 1;
    }
  }

  function pollScripts() {
    if (groups.scripts >= 1 || !window.performance.getEntriesByName) {
      return;
    }
    var done = 0;
    for (var i = 0; i < scriptUrls.length; i += 1) {
      var entries = window.performance.getEntriesByName(scriptUrls[i], "resource");
      if (entries.length && entries[0].responseEnd > 0) {
        done += 1;
      }
    }
    groups.scripts = done / scriptUrls.length;
  }

  function imagesGroup() {
    var all = document.querySelectorAll("img");
    var wanted = [];
    for (var i = 0; i < all.length; i += 1) {
      var box = all[i].getBoundingClientRect();
      var inView = box.top < window.innerHeight && box.bottom > 0;
      if (all[i].getAttribute("src") && !all[i].complete && (inView || all[i].loading !== "lazy")) {
        wanted.push(all[i]);
      }
    }
    var done = 0;
    if (!wanted.length) {
      groups.images = 1;
      return;
    }
    function settle() {
      done += 1;
      groups.images = done / wanted.length;
    }
    wanted.forEach(function (img) {
      img.addEventListener("load", settle);
      img.addEventListener("error", settle);
    });
  }

  fontsGroup();
  stylesGroup();
  scriptsGroup();
  imagesGroup();
  // The window's own load event means everything above has arrived.
  window.addEventListener("load", function () {
    groups.fonts = groups.styles = groups.scripts = groups.images = 1;
  });

  function target() {
    var sum = 0;
    var all = true;
    for (var name in GROUP_WEIGHTS) {
      if (GROUP_WEIGHTS.hasOwnProperty(name)) {
        sum += GROUP_WEIGHTS[name] * Math.min(1, groups[name]);
        all = all && groups[name] >= 1;
      }
    }
    return all ? 1 : sum;
  }

  // ---- The progress bar: attributes only ------------------------------------

  var shown = 0;
  var lastPercent = -1;
  var percentSuffix = (document.documentElement.lang || "").indexOf("fr") === 0 ? " %" : "%";

  function drawProgress() {
    var percent = Math.round(shown * 100);
    bar.setAttribute("stroke-dashoffset", (100 * (1 - shown)).toFixed(2));
    if (percent !== lastPercent) {
      lastPercent = percent;
      percentEl.textContent = percent + percentSuffix;
      // The spoken status changes once, at the end.
      if (percent === 100 && label) {
        label.textContent = overlay.getAttribute("data-splash-ready") || label.textContent;
      }
    }
  }

  // ---- The sequence -----------------------------------------------------------

  function startOutline() {
    if (staticMode) {
      return;
    }
    animate(track, [{ strokeDashoffset: 100 }, { strokeDashoffset: 0 }], {
      duration: SEQUENCE[0].duration, easing: "cubic-bezier(0.4, 0, 0.2, 1)", fill: "forwards"
    });
  }

  function startInversion() {
    api.flashLog.push(Math.round(window.performance.now() - startedAt));
    animate(ink, [
      { opacity: 0 },
      { opacity: 1, offset: 0.42 },
      { opacity: 1, offset: 0.58 },
      { opacity: 0 }
    ], { duration: SEQUENCE[1].duration, easing: "ease-in-out" });
  }

  function startSweeps() {
    for (var i = 0; i < bands.length; i += 1) {
      animate(bands[i], [
        { transform: "translateX(-120%)", opacity: 0 },
        { opacity: 0.72, offset: 0.2 },
        { opacity: 0.72, offset: 0.8 },
        { transform: "translateX(420%)", opacity: 0 }
      ], { duration: SEQUENCE[2].duration, delay: i * 70, easing: "cubic-bezier(0.45, 0, 0.2, 1)" });
    }
  }

  // The scan line crosses the panel top to bottom; the sharp logo is
  // uncovered exactly while the line passes over it.
  function startScan() {
    var height = frame.getBoundingClientRect().height;
    var logoHeight = sharp.getBoundingClientRect().height;
    var from = Math.max(0, (height - logoHeight) / 2 / height);
    var to = Math.min(1, (height + logoHeight) / 2 / height);
    var duration = SEQUENCE[6].duration;
    animate(sharp, [
      { clipPath: "inset(0 0 100% 0)", offset: 0 },
      { clipPath: "inset(0 0 100% 0)", offset: from },
      { clipPath: "inset(0 0 0% 0)", offset: to },
      { clipPath: "inset(0 0 0% 0)", offset: 1 }
    ], { duration: duration, easing: "linear", fill: "forwards" });
    animate(scan, [
      { opacity: 1, transform: "translateY(0)" },
      { opacity: 1, transform: "translateY(" + height + "px)", offset: 0.92 },
      { opacity: 0, transform: "translateY(" + height + "px)" }
    ], { duration: duration, easing: "linear" });
  }

  // The page opens from the frame's own rectangle, each of its top-level
  // pieces clipped to the part of that rectangle it covers.
  function startOpening() {
    var f = frame.getBoundingClientRect();
    overlay.classList.add("splash--opening");
    var duration = SEQUENCE[7].duration;
    pageNodes.forEach(function (node) {
      var r = node.getBoundingClientRect();
      var from = "inset(" + (f.top - r.top) + "px " + (r.right - f.right) + "px " +
        (r.bottom - f.bottom) + "px " + (f.left - r.left) + "px round 18px)";
      animate(node, [{ clipPath: from }, { clipPath: "inset(0px 0px 0px 0px round 0px)" }], {
        duration: duration, easing: "cubic-bezier(0.65, 0, 0.2, 1)", fill: "forwards"
      });
    });
    animate(frame, [{ opacity: 1 }, { opacity: 0 }], {
      duration: 260, easing: "ease-in", fill: "forwards"
    });
    animate(caption, [{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: "forwards" });
  }

  function finish() {
    if (finished) {
      return;
    }
    finished = true;
    anims.forEach(function (animation) {
      try {
        animation.cancel();
      } catch (ignored) {
        // An animation that already ended has nothing to cancel.
      }
    });
    inerted.forEach(function (node) {
      node.removeAttribute("inert");
    });
    if (label) {
      label.removeAttribute("role");
    }
    overlay.classList.remove("splash--opening");
    root.classList.remove("splash-on");
    api.state = "done";
    api.finishedAt = Math.round(window.performance.now() - startedAt);
  }

  var phase = 0;
  var phaseAt = 0;
  var last = window.performance.now();

  function tick(now) {
    if (finished) {
      return;
    }
    var elapsed = now - startedAt;
    // The first frame can be stamped before the clock read at script start:
    // a step back in time counts as no time, and the share stays in [0, 1].
    var dt = Math.max(0, Math.min(0.05, (now - last) / 1000));
    last = now;
    pollScripts();
    var goal = elapsed >= FORCE_DONE_MS ? 1 : target();
    shown += (goal - shown) * (1 - Math.exp(-dt * (staticMode ? 60 : 8)));
    shown = Math.max(0, Math.min(1, shown));
    if (goal >= 1 && (shown > 0.996 || elapsed >= FORCE_DONE_MS)) {
      shown = 1;
    }
    drawProgress();
    if (elapsed >= CAP_MS) {
      finish();
      return;
    }
    if (staticMode) {
      if (phase === 0 && shown >= 1) {
        phase = 1;
        phaseAt = elapsed + 160;
      } else if (phase === 1 && elapsed >= phaseAt) {
        finish();
        return;
      }
    } else if (phase === 0 && elapsed >= SEQUENCE[1].at) {
      startInversion();
      phase = 1;
      phaseAt = elapsed + 320;
    } else if (phase === 1 && elapsed >= phaseAt) {
      startSweeps();
      phase = 2;
    } else if (phase === 2 && elapsed >= SEQUENCE[6].at && shown >= 0.5) {
      startScan();
      phase = 3;
      phaseAt = elapsed + SEQUENCE[6].duration;
    } else if (phase === 3 && elapsed >= phaseAt && shown >= 1) {
      phase = 4;
      phaseAt = elapsed + 100;
    } else if (phase === 4 && elapsed >= phaseAt) {
      startOpening();
      phase = 5;
      phaseAt = elapsed + SEQUENCE[7].duration + 20;
    } else if (phase === 5 && elapsed >= phaseAt) {
      finish();
      return;
    }
    window.requestAnimationFrame(tick);
  }

  if (staticMode) {
    overlay.classList.add("splash--static");
    track.setAttribute("stroke-dashoffset", "0");
    api.state = "static";
  } else {
    startOutline();
  }
  drawProgress();
  // Whatever happens in the frame loop, the cap ends the splash.
  window.setTimeout(finish, CAP_MS);
  window.requestAnimationFrame(tick);
}());
