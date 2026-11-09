/*
 * SkyPane companion service — list-filter.js.
 *
 * One generic client-side filter, reused by Flights, Airlines and
 * Health's unresolved-prefix list. No
 * build step, ES5-safe subset. Inert on a page with no
 * [data-filter-input], except that a [data-autosubmit] control still
 * submits its form on change (the Users page's role select). Served by
 * companion/app.py's LIST_FILTER_SCRIPT_ROUTE. No network call, timer, or persistent
 * state: only DOM attributes/text. The count text uses the
 * [data-filter-count] element's own server-rendered, translated
 * template. Flights joined freshness.js's refresh loop, so the count
 * element is looked up fresh each run rather than cached, and the
 * filter re-applies after every swap since the server renders the list
 * unfiltered.
 */
(function () {
  "use strict";

  // A control marked [data-autosubmit] sends its form as soon as it
  // changes (the collection's sort and show chips, the Users role select); without a script the
  // form's own button does the same.
  // Heard on the document, so a control a script adds later (the airline
  // editor opens its aircraft-type rows on demand) submits too.
  function submitOwnForm(event) {
    var target = event.target;
    if (target && target.hasAttribute && target.hasAttribute("data-autosubmit")
        && target.form) {
      target.form.submit();
    }
  }
  document.addEventListener("change", submitOwnForm);

  var input = document.querySelector("[data-filter-input]");
  if (!input) {
    return;
  }

  // Deliberately not captured here, unlike its siblings below — the
  // count is the one element that must be looked up fresh (see header).
  var COUNT_ATTR = "data-filter-count";
  var COUNT_SELECTOR = "[" + COUNT_ATTR + "]";

  // The stylesheet's existing changed-value animation class. Applied to
  // the element, never to its number: text is written before the
  // class, so the displayed value is correct at the animation's first
  // frame.
  var COUNT_CHANGED_CLASS = "is-fading-in";
  // freshness.js's post-swap announcement. Listened for, never
  // dispatched from here.
  var SWAPPED_EVENT = "skypane-regions-swapped";
  var emptyEl = document.querySelector("[data-filter-empty]");
  var clearButtons = document.querySelectorAll("[data-filter-clear]");
  // Optional segmented chips: radios whose value is a row's
  // data-filter-kind ("" is every row). Absent on a plain search bar.
  var chipInputs = document.querySelectorAll("[data-filter-chip]");
  var CHIP_COUNT_SELECTOR = "[data-filter-chip-count]";
  var ZERO_CLASS = "is-zero";
  // Set on the bar while the search holds text, so the collapsed search
  // stays open without a :has() selector.
  var ACTIVE_ATTR = "data-filter-active";
  var bar = input.closest ? input.closest(".filter-bar") : null;

  function selectedKind() {
    for (var k = 0; k < chipInputs.length; k++) {
      if (chipInputs[k].checked) {
        return chipInputs[k].value;
      }
    }
    return "";
  }

  // Distinct-group tally for one chip: rows matching the query and the
  // chip's kind, each logical flight counted once.
  function tallyChip(rows, query, kind) {
    var seen = {};
    var n = 0;
    for (var r = 0; r < rows.length; r++) {
      var rowKind = rows[r].getAttribute("data-filter-kind") || "";
      var text = rows[r].getAttribute("data-filter-text") || "";
      if (kind !== "" && rowKind !== kind) {
        continue;
      }
      if (query !== "" && text.indexOf(query) === -1) {
        continue;
      }
      var rg = rows[r].getAttribute("data-filter-group");
      var key = "g" + (rg === null ? "i" + r : rg);
      if (!seen[key]) {
        seen[key] = true;
        n++;
      }
    }
    return n;
  }

  // A day header with no visible row under it would read as an empty
  // section: hide it until a row of its day shows again. Walks the
  // siblings up to the next header; a Flights detail row (no
  // data-filter-text) between rows is skipped.
  function syncDayHeaders() {
    var heads = document.querySelectorAll("[data-filter-day]");
    for (var h = 0; h < heads.length; h++) {
      var sib = heads[h].nextElementSibling;
      var any = false;
      while (sib && !sib.hasAttribute("data-filter-day")) {
        if (sib.hasAttribute("data-filter-text") && !sib.hidden) {
          any = true;
          break;
        }
        sib = sib.nextElementSibling;
      }
      heads[h].hidden = !any;
    }
    // A phone day is one group: hidden while none of its rows shows.
    var days = document.querySelectorAll("[data-filter-day-group]");
    for (var d = 0; d < days.length; d++) {
      days[d].hidden = !days[d].querySelector("[data-filter-text]:not([hidden])");
    }
  }

  function paintChips(rows, query) {
    for (var c = 0; c < chipInputs.length; c++) {
      var chip = chipInputs[c];
      var label = chip.closest ? chip.closest("label") : chip.parentNode;
      var countEl = label ? label.querySelector(CHIP_COUNT_SELECTOR) : null;
      var n = tallyChip(rows, query, chip.value);
      if (countEl) {
        countEl.textContent = String(n);
      }
      if (label && label.classList) {
        if (n === 0) {
          label.classList.add(ZERO_CLASS);
        } else {
          label.classList.remove(ZERO_CLASS);
        }
      }
    }
  }

  function applyFilter() {
    // Query fresh on every input event: the desktop <tr> and mobile
    // <li> for the same row both exist simultaneously (CSS toggles
    // which is visible), so a NodeList cached at load would miss
    // whichever the current breakpoint is not rendering.
    var rows = document.querySelectorAll("[data-filter-text]");
    var query = input.value.toLowerCase();
    var kind = selectedKind();
    var rowKind;
    var total = rows.length;
    var i;
    var row;
    var text;
    var rawGroup;
    var group;
    var matched;
    var detail;
    // Every row also carries data-filter-group: History emits a <tr>
    // and a <li> per logical flight sharing one group value. Counting
    // distinct groups, not raw elements, keeps "X of Y shown" accurate
    // instead of double-counting the paired representations.
    var totalGroups = {};
    var visibleGroups = {};
    var totalCount = 0;
    var visibleCount = 0;
    for (i = 0; i < total; i++) {
      row = rows[i];
      text = row.getAttribute("data-filter-text") || "";
      rawGroup = row.getAttribute("data-filter-group");
      group = "g" + (rawGroup === null ? "i" + i : rawGroup);
      rowKind = row.getAttribute("data-filter-kind") || "";
      matched = (query === "" || text.indexOf(query) !== -1)
        && (kind === "" || rowKind === kind);
      row.hidden = !matched;
      // A Flights summary row's sibling .flight-detail-row is a
      // separate element sharing the same group value via
      // id="flight-detail-{group}", looked up by id rather than DOM
      // adjacency; a page with none (Airlines, the mobile <li>) is
      // unaffected by the guard below.
      if (rawGroup !== null) {
        detail = document.getElementById("flight-detail-" + rawGroup);
        if (detail) {
          detail.hidden = !matched;
        }
      }
      if (!totalGroups[group]) {
        totalGroups[group] = true;
        totalCount++;
      }
      if (matched && !visibleGroups[group]) {
        visibleGroups[group] = true;
        visibleCount++;
      }
    }
    var countEl = document.querySelector(COUNT_SELECTOR);
    if (countEl) {
      var countTemplate = countEl.getAttribute("data-filter-count-template")
        || "# of # shown";
      var countText = countTemplate
        .replace("#", String(visibleCount))
        .replace("#", String(totalCount));
      // Only on a real change: this runs on every keystroke and every
      // swap, and animating an unchanged sentence would be motion with
      // no information.
      if (countEl.textContent !== countText) {
        countEl.textContent = countText;
        if (countEl.classList) {
          // Removed, reflowed, re-added: reading a layout property in
          // between forces the removal to take effect before the
          // re-add, which a bare remove+add would otherwise coalesce.
          countEl.classList.remove(COUNT_CHANGED_CLASS);
          void countEl.offsetWidth;
          countEl.classList.add(COUNT_CHANGED_CLASS);
        }
      }
    }
    if (chipInputs.length) {
      paintChips(rows, query);
    }
    syncDayHeaders();
    if (bar) {
      if (query !== "") {
        bar.setAttribute(ACTIVE_ATTR, "");
      } else {
        bar.removeAttribute(ACTIVE_ATTR);
      }
    }
    if (emptyEl) {
      emptyEl.hidden = !((query !== "" || kind !== "") && visibleCount === 0);
    }
  }

  input.addEventListener("input", applyFilter);

  for (var ci = 0; ci < chipInputs.length; ci++) {
    chipInputs[ci].addEventListener("change", applyFilter);
  }

  // querySelectorAll: the inline clear and the empty state's own Clear
  // button are both [data-filter-clear]. The inline one clears the
  // search text; the empty state's (also [data-filter-clear-all]) resets
  // the chips to "All" too, since a chip can be what emptied the list.
  function resetAllChips() {
    for (var rc = 0; rc < chipInputs.length; rc++) {
      chipInputs[rc].checked = (chipInputs[rc].value === "");
    }
  }
  for (var bi = 0; bi < clearButtons.length; bi++) {
    (function (clearBtn) {
      clearBtn.addEventListener("click", function () {
        input.value = "";
        var clearAll = clearBtn.hasAttribute("data-filter-clear-all");
        if (clearAll) {
          resetAllChips();
        }
        applyFilter();
        // Keep the keyboard out of the way after the empty state's reset.
        if (!clearAll) {
          input.focus();
        }
      });
    })(clearButtons[bi]);
  }

  // Re-apply the filter after the refresh loop has swapped the list in.
  document.addEventListener(SWAPPED_EVENT, applyFilter);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();

/*
 * The Flights page's server-driven list. The search, the direction chips and
 * the sort are one GET form the server answers over the whole history; this
 * block only sends that form without leaving the page and swaps the answer in,
 * and appends the next flights for Load more without a reload, so the scroll
 * position, the focus and the typed text survive. Every control also works
 * without it (a form submit, a plain Load more link).
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-flights-form]");
  if (!form || !window.fetch || !window.DOMParser || !history.replaceState) {
    return;
  }

  var VIEW = "[data-flights-view]";
  var ID_ATTR = "data-flight-id";
  var DEFAULT_SORT = "newest";
  var SEARCH_DELAY_MS = 250;
  var CARD_ANCHOR = "flights-new-card";
  var TABLE_ANCHOR = "flights-new";
  var input = form.querySelector("[data-flights-search]");
  var latest = 0;
  var timer = null;
  var busy = false;

  function encode(value) {
    return encodeURIComponent(value);
  }

  // The address for the form's current controls; defaults are left out, as
  // the server leaves them out of its own links.
  function currentUrl() {
    var parts = [];
    var fields = form.elements;
    for (var i = 0; i < fields.length; i++) {
      var field = fields[i];
      if (!field.name || field.type === "submit" || field.type === "button") {
        continue;
      }
      if (field.type === "radio" && !field.checked) {
        continue;
      }
      var value = field.name === "q" ? field.value.replace(/^\s+|\s+$/g, "") : field.value;
      if (value === "" || (field.name === "sort" && value === DEFAULT_SORT)) {
        continue;
      }
      parts.push(encode(field.name) + "=" + encode(value));
    }
    var action = form.getAttribute("action");
    return action + (parts.length ? "?" + parts.join("&") : "");
  }

  function fetchView(url) {
    return fetch(url, { credentials: "same-origin" }).then(function (response) {
      if (response.redirected && window.skypaneSession
          && /\/login$/.test(new URL(response.url).pathname)) {
        window.skypaneSession.expire();
      }
      if (!response.ok || response.redirected) {
        throw new Error("flights");
      }
      return response.text();
    }).then(function (text) {
      var doc = new DOMParser().parseFromString(text, "text/html");
      if (!doc.querySelector(VIEW)) {
        throw new Error("flights");
      }
      return doc;
    });
  }

  // A failed or redirected request (an expired session) falls back to the
  // plain navigation the same address would have done.
  function giveUp(url) {
    if (window.skypaneSession && window.skypaneSession.ending()) {
      return;
    }
    window.location.assign(url);
  }

  function syncActive() {
    if (input && input.value !== "") {
      form.setAttribute("data-filter-active", "");
    } else {
      form.removeAttribute("data-filter-active");
    }
  }

  // The page's list is a run of sibling elements, each marked [data-flights-view]
  // (the controls, the empty card or the lists, the Load more block). A swap puts the
  // fetched run where the live one is. The entrance animation the stylesheet gives a
  // card is finished at once: only the first arrival of a page is staged.
  function swapView(doc) {
    var live = document.querySelectorAll(VIEW);
    var fresh = doc.querySelectorAll(VIEW);
    var active = document.activeElement;
    var key = active && active.getAttribute ? active.getAttribute("data-flights-key") : null;
    var parent = live[0].parentNode;
    var added = [];
    var i;
    for (i = 0; i < fresh.length; i++) {
      var node = document.importNode(fresh[i], true);
      parent.insertBefore(node, live[0]);
      added.push(node);
    }
    for (i = 0; i < live.length; i++) {
      parent.removeChild(live[i]);
    }
    for (i = 0; i < added.length; i++) {
      settle(added[i]);
    }
    if (key) {
      var again = document.querySelector('[data-flights-key="' + key + '"]');
      if (again) {
        again.focus();
      }
    }
  }

  function settle(node) {
    if (!node.getAnimations) {
      return;
    }
    var running = node.getAnimations({ subtree: true });
    for (var i = 0; i < running.length; i++) {
      running[i].finish();
    }
  }

  // What the page shows, as an address: a Back or Forward to another one
  // shows that state again by reloading it.
  var shown = window.location.pathname + window.location.search;

  // `commit` is a search the visitor settled (Enter, a chip, the sort, Clear):
  // it gets a history entry of its own so Back returns to the state before it.
  // Live typing only replaces the current entry.
  function refresh(commit) {
    window.clearTimeout(timer);
    var url = currentUrl();
    var mine = ++latest;
    fetchView(url).then(function (doc) {
      if (mine !== latest) {
        return;
      }
      swapView(doc);
      if (commit === true && url !== shown) {
        history.pushState(null, "", url);
      } else {
        history.replaceState(null, "", url);
      }
      shown = url;
    }, function () {
      if (mine === latest) {
        giveUp(url);
      }
    });
  }

  function idMap(root) {
    var map = {};
    var rows = root.querySelectorAll("[" + ID_ATTR + "]");
    for (var i = 0; i < rows.length; i++) {
      map[rows[i].getAttribute(ID_ATTR)] = rows[i];
    }
    return map;
  }

  // Appends the phone cards the fetched list holds beyond the live ones: a
  // fetched day group that already exists takes its new rows, any other is
  // added whole. Returns the first appended card.
  function appendCards(live, fetched) {
    var liveCards = live.querySelector(".history-cards");
    var newCards = fetched.querySelector(".history-cards");
    if (!liveCards || !newCards) {
      return null;
    }
    var present = idMap(liveCards);
    var first = null;
    var groups = newCards.children;
    for (var g = 0; g < groups.length; g++) {
      var rows = groups[g].querySelectorAll("[" + ID_ATTR + "]");
      var fresh = [];
      var host = null;
      for (var r = 0; r < rows.length; r++) {
        var known = present[rows[r].getAttribute(ID_ATTR)];
        if (known) {
          host = known.parentNode;
        } else {
          fresh.push(rows[r]);
        }
      }
      if (!fresh.length) {
        continue;
      }
      var added = [];
      if (host) {
        for (var f = 0; f < fresh.length; f++) {
          var card = document.importNode(fresh[f], true);
          host.appendChild(card);
          added.push(card);
        }
      } else {
        var section = document.importNode(groups[g], true);
        liveCards.appendChild(section);
        settle(section);
        added = section.querySelectorAll("[" + ID_ATTR + "]");
      }
      first = first || added[0];
    }
    return first;
  }

  // The same for the desktop table: rows in order, a day separator only when
  // a new row follows it. Returns the first appended row.
  function appendRows(live, fetched) {
    var liveBody = live.querySelector(".data-table-wrap tbody");
    var newBody = fetched.querySelector(".data-table-wrap tbody");
    if (!liveBody || !newBody) {
      return null;
    }
    var present = idMap(liveBody);
    var first = null;
    var day = null;
    var rows = newBody.children;
    for (var i = 0; i < rows.length; i++) {
      var id = rows[i].getAttribute(ID_ATTR);
      if (id === null) {
        day = rows[i];
      } else if (present[id]) {
        day = null;
      } else {
        if (day) {
          liveBody.appendChild(document.importNode(day, true));
          day = null;
        }
        var row = document.importNode(rows[i], true);
        liveBody.appendChild(row);
        first = first || row;
      }
    }
    return first;
  }

  function clearAnchors(live) {
    var old = live.querySelectorAll("#" + CARD_ANCHOR + ", #" + TABLE_ANCHOR);
    for (var i = 0; i < old.length; i++) {
      old[i].removeAttribute("id");
    }
  }

  function visible(el) {
    return !!(el && el.getClientRects().length);
  }

  function updateMore(live, fetched, hadFocus, firstNew) {
    var liveMore = live.querySelector("[data-history-more]");
    var newMore = fetched.querySelector("[data-history-more]");
    if (!liveMore) {
      return;
    }
    if (!newMore) {
      liveMore.parentNode.removeChild(liveMore);
      if (hadFocus && firstNew) {
        firstNew.setAttribute("tabindex", "-1");
        firstNew.focus({ preventScroll: true });
      }
      return;
    }
    var count = liveMore.querySelector(".history-more__count");
    var newCount = newMore.querySelector(".history-more__count");
    if (count && newCount) {
      count.textContent = newCount.textContent;
    }
    var links = liveMore.querySelectorAll("[data-flights-more]");
    var newLinks = newMore.querySelectorAll("[data-flights-more]");
    for (var i = 0; i < links.length && i < newLinks.length; i++) {
      links[i].setAttribute("href", newLinks[i].getAttribute("href"));
    }
  }

  function loadMore(link) {
    if (busy) {
      return;
    }
    var href = link.getAttribute("href");
    var url = href.split("#")[0];
    busy = true;
    link.setAttribute("aria-busy", "true");
    fetchView(url).then(function (doc) {
      var live = document;
      var fetched = doc;
      var hadFocus = live.querySelector("[data-history-more]").contains(document.activeElement);
      clearAnchors(live);
      var card = appendCards(live, fetched);
      var row = appendRows(live, fetched);
      if (card) {
        card.id = CARD_ANCHOR;
      }
      if (row) {
        row.id = TABLE_ANCHOR;
      }
      updateMore(live, fetched, hadFocus, visible(row) ? row : card);
      history.replaceState(null, "", url);
      shown = url;
      busy = false;
    }, function () {
      busy = false;
      giveUp(href);
    });
  }

  function clearSearch(link) {
    var inView = !!(link.closest && link.closest(VIEW));
    if (input) {
      input.value = "";
    }
    if (inView) {
      var chips = document.querySelectorAll('input[name="kind"][form="' + form.id + '"]');
      for (var i = 0; i < chips.length; i++) {
        chips[i].checked = chips[i].value === "";
      }
    }
    syncActive();
    refresh(true);
    if (!inView && input) {
      input.focus();
    }
  }

  if (input) {
    input.addEventListener("input", function () {
      syncActive();
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { refresh(false); }, SEARCH_DELAY_MS);
    });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    refresh(true);
  });

  document.addEventListener("change", function (event) {
    var target = event.target;
    if (target && target.hasAttribute && target.hasAttribute("data-flights-auto")) {
      refresh(true);
    }
  });

  window.addEventListener("popstate", function () {
    if (window.location.pathname + window.location.search !== shown) {
      window.location.reload();
    }
  });

  document.addEventListener("click", function (event) {
    var target = event.target && event.target.closest ? event.target : null;
    var link = target ? target.closest("a[data-flights-more], a[data-flights-clear]") : null;
    if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey) {
      return;
    }
    event.preventDefault();
    if (link.hasAttribute("data-flights-more")) {
      loadMore(link);
    } else {
      clearSearch(link);
    }
  });
})();
