/*
 * SkyPane companion service — airline-suggest.js.
 *
 * An unidentified prefix of the airline editor whose name is still being
 * looked up carries data-suggest-prefix on its <tbody>. This script asks the
 * server for them one at a time (the page marks at most three) and swaps in
 * the row the server returns, which holds either the proposed name with its
 * check or the plain "Name it" row. It stops at the first busy or failed
 * answer and then removes the pending marks of the rows it did not ask, so
 * nothing keeps saying it is looking. It holds no visible text: the server
 * renders every word. Without a script the page shows cached suggestions and
 * "Name it". ES5-safe subset.
 */
(function () {
  "use strict";

  var PREFIX_ATTR = "data-suggest-prefix";
  var MAX_PER_LOAD = 3;
  var STOP_STATES = { busy: true, failed: true, off: true, stale: true };

  function csrfOf(group) {
    var field = group.querySelector('input[name="csrf_token"]');
    return field ? field.value : "";
  }

  function body(group) {
    var parts = {
      prefix: group.getAttribute(PREFIX_ATTR),
      index: group.getAttribute("data-suggest-index"),
      csrf_token: csrfOf(group)
    };
    var pairs = [];
    for (var key in parts) {
      if (Object.prototype.hasOwnProperty.call(parts, key)) {
        pairs.push(encodeURIComponent(key) + "=" + encodeURIComponent(parts[key] || ""));
      }
    }
    return pairs.join("&");
  }

  function swap(group, html) {
    var template = document.createElement("template");
    template.innerHTML = html;
    var fresh = template.content.firstElementChild;
    if (fresh && group.parentNode) {
      group.parentNode.replaceChild(fresh, group);
    }
  }

  // Drop the "looking" tag of a row that will not be asked after all.
  function settle(group) {
    group.removeAttribute(PREFIX_ATTR);
    var tag = group.querySelector(".airlines-tag--pending");
    if (tag && tag.parentNode) {
      var top = tag.parentNode;
      top.removeChild(tag);
      if (top.parentNode && !top.firstChild) {
        top.parentNode.removeChild(top);
      }
    }
  }

  function settleAll(groups, from) {
    for (var i = from; i < groups.length; i++) {
      settle(groups[i]);
    }
  }

  function ask(groups, position) {
    if (position >= groups.length) {
      return;
    }
    var group = groups[position];
    var url = group.getAttribute("data-suggest-url");
    if (position >= MAX_PER_LOAD || !url || !window.fetch) {
      settleAll(groups, position);
      return;
    }
    window.fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body(group)
    }).then(function (response) {
      return response.ok ? response.json() : null;
    }).then(function (answer) {
      if (!answer || typeof answer.html !== "string") {
        settleAll(groups, position);
        return;
      }
      if (answer.html) {
        swap(group, answer.html);
      } else {
        settle(group);
      }
      if (STOP_STATES[answer.state] === true) {
        settleAll(groups, position + 1);
        return;
      }
      ask(groups, position + 1);
    }, function () {
      settleAll(groups, position);
    });
  }

  function start() {
    var found = document.querySelectorAll("tbody[" + PREFIX_ATTR + "]");
    var groups = [];
    for (var i = 0; i < found.length; i++) {
      groups.push(found[i]);
    }
    if (groups.length) {
      ask(groups, 0);
    }
  }

  // Nothing is asked while the tab is in the background.
  function whenVisible() {
    if (document.hidden) {
      document.addEventListener("visibilitychange", function once() {
        if (!document.hidden) {
          document.removeEventListener("visibilitychange", once);
          start();
        }
      });
      return;
    }
    start();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", whenVisible);
  } else {
    whenVisible();
  }
}());
