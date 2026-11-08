/*
 * SkyPane companion service - place-card.js.
 *
 * The small page furniture around the map on the Location and detection page:
 * the credits popover and the details card's heading. Loaded after
 * place-map.js on that one page only, and inert unless the map started (the
 * page element carries `map-ready`), so a page without the map keeps its plain
 * form. No build step, ES5-safe subset.
 */
(function () {
  "use strict";

  if (!document.getElementById("place-map") ||
      (" " + document.documentElement.className + " ").indexOf(" map-ready ") < 0) {
    return;
  }

  var infoButton = document.getElementById("place-info");
  var creditsEl = document.getElementById("place-credits");

  function setCreditsOpen(open) {
    creditsEl.hidden = !open;
    infoButton.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function wireCredits() {
    if (!infoButton || !creditsEl) {
      return;
    }
    infoButton.addEventListener("click", function () {
      setCreditsOpen(creditsEl.hidden);
    });
    document.addEventListener("click", function (event) {
      if (!creditsEl.hidden && !event.target.closest(".place-info")) {
        setCreditsOpen(false);
      }
    }, true);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !creditsEl.hidden) {
        setCreditsOpen(false);
        infoButton.focus();
      }
    });
  }

  wireCredits();

  // The radius field and its slider: a value past the limits is pulled back
  // to the nearest limit once the field is left, and the slider speaks the
  // value in kilometres.
  function wireRadius() {
    var field = document.getElementById("place-radius");
    var range = document.getElementById("place-radius-range");
    if (!field) {
      return;
    }
    function speak() {
      if (range && field.value !== "") {
        range.setAttribute("aria-valuetext", field.value + " km");
      }
    }
    field.addEventListener("input", speak);
    if (range) {
      range.addEventListener("input", speak);
    }
    field.addEventListener("change", function () {
      var km = parseFloat(field.value);
      var min = parseFloat(field.getAttribute("min"));
      var max = parseFloat(field.getAttribute("max"));
      if (isNaN(km) || isNaN(min) || isNaN(max)) {
        return;
      }
      var clamped = Math.round(Math.min(max, Math.max(min, km)));
      if (String(clamped) !== field.value) {
        field.value = String(clamped);
        field.dispatchEvent(new Event("input", { bubbles: true }));
      }
      speak();
    });
    speak();
  }

  wireRadius();

  var detailsSummary = document.querySelector("#details > summary");
  if (detailsSummary) {
    // With the map the details are a card shown by the #details link: its
    // title is a heading, not a toggle.
    detailsSummary.addEventListener("click", function (event) {
      event.preventDefault();
    });
  }
}());
