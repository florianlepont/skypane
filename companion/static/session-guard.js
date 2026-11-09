/*
 * SkyPane companion service — session-guard.js.
 *
 * A request the page makes on its own (a quick switch, a list view, the
 * freshness tick) can be refused because the session ended: a 401, or a
 * redirect to the sign-in page that fetch() reports as an opaque response.
 * Each such script hands the failed response to window.skypaneSession.report();
 * a 403 or an opaque redirect is confirmed against the sign-in page itself
 * (it only answers 200 to a visitor who is signed out), so a refusal for any
 * other reason keeps its own handling. When the session really ended the
 * guard shows the server-rendered, translated "session expired" toast and
 * sends the browser to /login?next=<this page>&expired=1, which the server validates
 * again against its own list of destinations. No HTML-writing sink; the only
 * URL it builds is the same-origin sign-in route with the current path.
 * ES5-safe subset.
 */
(function () {
  "use strict";

  var LOGIN_ROUTE = "/login";
  var TOAST_ATTR = "data-quick-toast";
  var TEMPLATE_ATTR = "data-session-expired-template";
  // Long enough to read the toast, short enough not to feel stuck.
  var REDIRECT_DELAY_MS = 1800;
  var started = false;

  // The current page as a same-origin path with its query, or "" when the
  // address is anything else (the server would refuse it anyway).
  function currentTarget() {
    var path = window.location.pathname + window.location.search;
    if (path.charAt(0) !== "/" || path.charAt(1) === "/"
        || path.indexOf("\\") !== -1) {
      return "";
    }
    return path;
  }

  function showToast() {
    var region = document.querySelector("[" + TOAST_ATTR + "]");
    var template = document.querySelector("[" + TEMPLATE_ATTR + "]");
    if (!region || !template || !template.content) {
      return;
    }
    while (region.firstChild) {
      region.removeChild(region.firstChild);
    }
    region.appendChild(template.content.cloneNode(true));
  }

  function goToSignIn() {
    var target = currentTarget();
    window.location.assign(
      LOGIN_ROUTE + "?" + (target ? "next=" + encodeURIComponent(target) + "&" : "") +
      "expired=1");
  }

  // Tells the visitor once, then sends them to sign in. Idempotent.
  function expire() {
    if (started) {
      return;
    }
    started = true;
    showToast();
    window.setTimeout(goToSignIn, REDIRECT_DELAY_MS);
  }

  // Resolves true when the sign-in page answers 200 (signed out) and false
  // when it redirects (still signed in) or cannot be reached.
  function signedOut() {
    if (!window.fetch) {
      return Promise.resolve(false);
    }
    return window.fetch(LOGIN_ROUTE, {
      credentials: "same-origin",
      redirect: "manual",
      headers: { "X-Requested-With": "session-guard" }
    }).then(function (response) {
      return response.type !== "opaqueredirect" && response.status === 200;
    })["catch"](function () {
      return false;
    });
  }

  // Resolves true when `response` shows the session ended (and the expiry
  // flow has started), false when it is some other failure.
  function report(response) {
    if (started) {
      return Promise.resolve(true);
    }
    var status = response ? response.status : 0;
    var type = response ? response.type : "";
    if (status === 401) {
      expire();
      return Promise.resolve(true);
    }
    if (status !== 403 && type !== "opaqueredirect" && status !== 0) {
      return Promise.resolve(false);
    }
    return signedOut().then(function (gone) {
      if (gone) {
        expire();
      }
      return gone;
    });
  }

  window.skypaneSession = {
    report: report,
    expire: expire,
    ending: function () { return started; }
  };
})();
