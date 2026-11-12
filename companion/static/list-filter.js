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
  // The Airlines collection's form is answered in place by the block at the end
  // of this file when the browser can do that; only then is it not submitted.
  var inPlace = !!(window.fetch && window.DOMParser && history.replaceState);
  function submitOwnForm(event) {
    var target = event.target;
    if (target && target.hasAttribute && target.hasAttribute("data-autosubmit")
        && target.form) {
      if (inPlace && target.form.hasAttribute("data-collection-form")) {
        return;
      }
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
  // Optional segmented chips: radios whose value is a row's
  // data-filter-kind ("" is every row). Absent on a plain search bar.
  var chipInputs = document.querySelectorAll("[data-filter-chip]");
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
    syncDayHeaders();
    if (bar) {
      if (query !== "") {
        bar.setAttribute(ACTIVE_ATTR, "");
      } else {
        bar.removeAttribute(ACTIVE_ATTR);
      }
    }
    // Looked up fresh: an in-place swap of the list renders the card again.
    var emptyEl = document.querySelector("[data-filter-empty]");
    if (emptyEl) {
      emptyEl.hidden = !((query !== "" || kind !== "") && visibleCount === 0);
    }
  }

  input.addEventListener("input", applyFilter);

  for (var ci = 0; ci < chipInputs.length; ci++) {
    chipInputs[ci].addEventListener("change", applyFilter);
  }

  // The inline clear and the empty state's own Clear
  // button are both [data-filter-clear]. The inline one clears the
  // search text; the empty state's (also [data-filter-clear-all]) resets
  // the chips to "All" too, since a chip can be what emptied the list.
  function resetAllChips() {
    for (var rc = 0; rc < chipInputs.length; rc++) {
      chipInputs[rc].checked = (chipInputs[rc].value === "");
    }
  }
  // Heard on the document so a Clear button the list swap renders again works too.
  document.addEventListener("click", function (event) {
    var node = event.target;
    var clearBtn = node && node.closest ? node.closest("[data-filter-clear]") : null;
    if (!clearBtn) {
      return;
    }
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

  // Re-apply the filter after the refresh loop has swapped the list in.
  document.addEventListener(SWAPPED_EVENT, applyFilter);

  // No DOMContentLoaded wrapper needed: the <script> tag carries defer,
  // so this file only ever runs after parsing.
})();

/*
 * What the two server-answered lists below do when a request gets no answer
 * (no connection): the page is kept, an error toast says the list could not
 * be updated, and the chips and the sort go back to what the list shows.
 */
(function () {
  "use strict";

  // Must equal companion/ui_base.py's QUICK_TOAST_ATTR and
  // companion/ui_filter.py's LIST_OFFLINE_TEMPLATE_ATTR.
  var REGION_ATTR = "data-quick-toast";
  var OFFLINE_TEMPLATE_ATTR = "data-list-offline-template";
  // Marks the notice in the region, so only this notice is taken back.
  var OFFLINE_MARK_ATTR = "data-list-offline";

  function announce() {
    var region = document.querySelector("[" + REGION_ATTR + "]");
    var template = document.querySelector("[" + OFFLINE_TEMPLATE_ATTR + "]");
    if (!region || !template || !template.content) {
      return;
    }
    while (region.firstChild) {
      region.removeChild(region.firstChild);
    }
    region.appendChild(template.content.cloneNode(true));
    if (region.firstElementChild) {
      region.firstElementChild.setAttribute(OFFLINE_MARK_ATTR, "");
    }
  }

  // An answer arrived again: the notice has nothing left to say.
  function clear() {
    var region = document.querySelector("[" + REGION_ATTR + "]");
    var shownNotice = region && region.querySelector("[" + OFFLINE_MARK_ATTR + "]");
    if (shownNotice) {
      region.removeChild(shownNotice);
    }
  }

  // The radios of `form` are checked again as the address `shown` names
  // them (`defaults` gives the value of a name the address leaves out). The
  // typed text stays: it is what the visitor will send again.
  function restore(form, shown, defaults) {
    var query = new URLSearchParams(shown.split("?")[1] || "");
    var fields = form.elements;
    for (var i = 0; i < fields.length; i++) {
      var field = fields[i];
      if (field.type === "radio" && field.name) {
        var wanted = query.has(field.name) ? query.get(field.name) : (defaults[field.name] || "");
        field.checked = field.value === wanted;
      }
    }
    var menus = form.querySelectorAll("details[open]");
    for (var m = 0; m < menus.length; m++) {
      menus[m].removeAttribute("open");
    }
  }

  window.skypaneListOffline = {
    REASON: {}, announce: announce, clear: clear, restore: restore
  };
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
  var OFFLINE = window.skypaneListOffline.REASON;
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

  // The server answers `?part=` with the list alone: PART_LIST is every
  // element a filter replaces, PART_NEW the flights of the last Load more
  // step. Must equal PART_PARAM, PART_LIST and PART_NEW in
  // companion/pages/history_page.py. The address shown never carries it.
  var PART_PARAM = "part";
  var PART_LIST = "list";
  var PART_NEW = "new";

  function fetchView(url, part) {
    var asked = url + (url.indexOf("?") === -1 ? "?" : "&") + PART_PARAM + "=" + part;
    return fetch(asked, { credentials: "same-origin" }).then(function (response) {
      if (response.redirected && window.skypaneSession
          && /\/login$/.test(new URL(response.url).pathname)) {
        window.skypaneSession.expire();
      }
      if (!response.ok || response.redirected) {
        throw new Error("flights");
      }
      return response.text();
    }, function () {
      // The request got no answer at all: there is no connection.
      throw OFFLINE;
    }).then(function (text) {
      var doc = new DOMParser().parseFromString(text, "text/html");
      if (!doc.querySelector(VIEW)) {
        throw new Error("flights");
      }
      return doc;
    });
  }

  // A refused or redirected request (an expired session) falls back to the
  // plain navigation the same address would have done. Without a connection
  // that navigation would replace the list with the browser's error page:
  // the page stays, says so, and its controls show what the list holds.
  function giveUp(url, reason) {
    if (window.skypaneSession && window.skypaneSession.ending()) {
      return;
    }
    if (reason === OFFLINE) {
      window.skypaneListOffline.announce();
      window.skypaneListOffline.restore(form, shown, { sort: DEFAULT_SORT });
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
    var motion = window.SkyPaneMotion;
    var thumbs = motion ? motion.tabsState(document) : null;
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
      if (motion) {
        // The chips are rendered again: their thumb carries on from where the
        // old one was. The swapped list fades in again (opacity only); the
        // one the breakpoint hides has no box and is left alone.
        motion.enhanceTabs(added[i], thumbs);
        if (visible(added[i]) && added[i].matches(".history-cards, .data-table-wrap")) {
          motion.replay(added[i], true);
        }
      }
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

  // What the current history entry holds: "base" the entry the page opened
  // on, "draft" an entry the live typing is rewriting, "committed" an entry a
  // settled search owns. Live typing never overwrites a committed entry, so
  // Back returns to the search that was settled before it.
  var entryState = "base";

  // `commit` is a search the visitor settled (Enter, a chip, the sort, Clear):
  // a changed address gets a history entry of its own so Back returns to the
  // state before it, and Enter on text already typed live settles the entry
  // typing wrote. Live typing rewrites the current entry, or starts a new one
  // right after a settled search.
  function record(url, commit) {
    if (commit === true) {
      if (url !== shown) {
        history.pushState(null, "", url);
      } else {
        history.replaceState(null, "", url);
      }
      entryState = "committed";
    } else {
      if (entryState === "committed") {
        history.pushState(null, "", url);
      } else {
        history.replaceState(null, "", url);
      }
      entryState = "draft";
    }
    shown = url;
  }

  function refresh(commit) {
    window.clearTimeout(timer);
    var url = currentUrl();
    var mine = ++latest;
    fetchView(url, PART_LIST).then(function (doc) {
      if (mine !== latest) {
        return;
      }
      window.skypaneListOffline.clear();
      swapView(doc);
      record(url, commit);
    }, function (reason) {
      if (mine === latest) {
        giveUp(url, reason);
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

  // Only the first few items a "Load more" adds take the entrance; the rest
  // of a long batch just appears.
  var ENTER_APPENDED_MAX = 3;
  function enterAppended(el, position) {
    if (position < ENTER_APPENDED_MAX && window.SkyPaneMotion) {
      window.SkyPaneMotion.appended(el);
    }
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
          enterAppended(card, f);
        }
      } else {
        var section = document.importNode(groups[g], true);
        liveCards.appendChild(section);
        settle(section);
        enterAppended(section, 0);
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
    var entered = 0;
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
        enterAppended(row, entered);
        entered++;
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
    fetchView(url, PART_NEW).then(function (doc) {
      var live = document;
      var fetched = doc;
      var hadFocus = live.querySelector("[data-history-more]").contains(document.activeElement);
      window.skypaneListOffline.clear();
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
    }, function (reason) {
      busy = false;
      link.removeAttribute("aria-busy");
      giveUp(href, reason);
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

/*
 * The Airlines collection's show chips and sort menu. The server answers the
 * form (the list is built from the whole history); this block only fetches that
 * answer and puts the list in the place of the live one, so the page is not
 * reloaded, its opening is not played again and the scroll position stays.
 * Without it the controls submit the form as a plain GET.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-collection-form]");
  if (!form || !window.fetch || !window.DOMParser || !history.replaceState) {
    return;
  }

  var VIEW = ".collection-grid, .collection-sheet, [data-filter-empty], [data-collection-empty]";
  var DEFAULTS = { show: "all", sort: "most" };
  var SORT_NAME = "sort";
  var OFFLINE = window.skypaneListOffline.REASON;
  var latest = 0;
  var shown = window.location.pathname + window.location.search;

  function currentUrl() {
    var parts = [];
    var fields = form.elements;
    for (var i = 0; i < fields.length; i++) {
      var field = fields[i];
      if (!field.name || field.type === "submit" || field.type === "button"
          || (field.type === "radio" && !field.checked)) {
        continue;
      }
      var value = field.name === "q" ? field.value.replace(/^\s+|\s+$/g, "") : field.value;
      if (value === "" || DEFAULTS[field.name] === value) {
        continue;
      }
      parts.push(encodeURIComponent(field.name) + "=" + encodeURIComponent(value));
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
        throw new Error("collection");
      }
      return response.text();
    }, function () {
      throw OFFLINE;
    }).then(function (text) {
      var doc = new DOMParser().parseFromString(text, "text/html");
      if (!doc.querySelector("[data-collection-form]")) {
        throw new Error("collection");
      }
      return doc;
    });
  }

  // The menu button names the current order; the fetched page has the new name.
  function syncSortName(doc) {
    var live = form.querySelector(".collection-sort__toggle");
    var fresh = doc.querySelector(".collection-sort__toggle");
    if (live && fresh) {
      live.setAttribute("aria-label", fresh.getAttribute("aria-label"));
      live.setAttribute("title", fresh.getAttribute("title"));
    }
    var menu = form.querySelector(".collection-sort");
    if (menu) {
      menu.removeAttribute("open");
    }
  }

  // The entrance the stylesheet gives the list on a page's first arrival is
  // finished at once: a tab change is not a new page.
  function settle(node) {
    if (!node.getAnimations) {
      return;
    }
    var running = node.getAnimations({ subtree: true });
    for (var i = 0; i < running.length; i++) {
      running[i].finish();
    }
  }

  function swapView(doc) {
    var live = document.querySelectorAll(VIEW);
    var fresh = doc.querySelectorAll(VIEW);
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
    syncSortName(doc);
    document.dispatchEvent(new CustomEvent("skypane-regions-swapped"));
  }

  function refresh() {
    var url = currentUrl();
    var mine = ++latest;
    fetchView(url).then(function (doc) {
      if (mine !== latest) {
        return;
      }
      window.skypaneListOffline.clear();
      swapView(doc);
      history.pushState(null, "", url);
      shown = url;
    }, function (reason) {
      if (mine !== latest || (window.skypaneSession && window.skypaneSession.ending())) {
        return;
      }
      if (reason === OFFLINE) {
        window.skypaneListOffline.announce();
        window.skypaneListOffline.restore(form, shown, DEFAULTS);
        return;
      }
      window.location.assign(url);
    });
  }

  // Each card carries its place in every order (one number per sort value,
  // in the menu's order): the sort moves the cards the page already holds.
  // Must equal RANK_ATTR in companion/pages/airline_collection_page.py.
  var RANK_ATTR = "data-sort-rank";

  function rankOf(item, column) {
    var places = (item.getAttribute(RANK_ATTR) || "").split(" ");
    return column < places.length && places[column] !== "" ? Number(places[column]) : NaN;
  }

  // Puts the cards in the order of `radio`'s value without a request. False
  // when the page cannot (no grid, or a card without its places): the server
  // is asked instead.
  function sortInPlace(radio) {
    var grid = document.querySelector(".collection-grid");
    var radios = form.querySelectorAll('input[type="radio"][name="' + radio.name + '"]');
    var column = Array.prototype.indexOf.call(radios, radio);
    if (!grid || column < 0) {
      return false;
    }
    var items = Array.prototype.slice.call(grid.children);
    for (var i = 0; i < items.length; i++) {
      if (isNaN(rankOf(items[i], column))) {
        return false;
      }
    }
    items.sort(function (a, b) { return rankOf(a, column) - rankOf(b, column); });
    for (var k = 0; k < items.length; k++) {
      grid.appendChild(items[k]);
    }
    nameSort(radio);
    var url = currentUrl();
    history.pushState(null, "", url);
    shown = url;
    return true;
  }

  // The menu button names the order chosen: "<menu label>: <option>".
  function nameSort(radio) {
    var menu = form.querySelector(".collection-sort");
    var toggle = form.querySelector(".collection-sort__toggle");
    var panel = form.querySelector(".collection-sort__panel");
    var option = radio.parentNode.querySelector(".collection-sort__row > span");
    if (toggle && panel && option) {
      var name = panel.getAttribute("aria-label") + ": " + option.textContent;
      toggle.setAttribute("aria-label", name);
      toggle.setAttribute("title", name);
    }
    if (menu) {
      menu.removeAttribute("open");
    }
  }

  document.addEventListener("change", function (event) {
    var target = event.target;
    if (target && target.form === form && target.hasAttribute("data-autosubmit")) {
      if (target.name === SORT_NAME && sortInPlace(target)) {
        latest++;
        return;
      }
      refresh();
    }
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    refresh();
  });

  window.addEventListener("popstate", function () {
    if (window.location.pathname + window.location.search !== shown) {
      window.location.reload();
    }
  });
})();
