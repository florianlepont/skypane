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

/*
 * Page restore (same file, separate scope).
 *
 * An authenticated page is served `private, no-cache` (not `no-store`) so the
 * browser may keep it in the back/forward cache. A page restored from there
 * runs no request of its own, so it could show private content after the
 * session ended (signed out here or in another tab, or another account
 * signed in). On every restore (pageshow with persisted set) this script:
 *   1. hides the whole document at once, so no private content is painted;
 *   2. asks the server whether this page's session is still the live one: a
 *      POST to /session/check carrying the page's own anti-forgery token
 *      (derived from the session, so another session or account fails it);
 *   3. reveals the page on a 204, and on anything else (a refusal, a
 *      redirect to sign-in, a network error, no answer in time) sends the
 *      browser to /login?next=<this page>&expired=1.
 * It also leaves a marker cookie: the server only serves the cacheable
 * header to a browser that has run this script, so a browser without
 * scripts, which could not run the check, keeps `no-store`. The only URL it
 * builds is the same-origin sign-in route with the current path. ES5-safe
 * subset.
 */
(function () {
  "use strict";

  var CHECK_ROUTE = "/session/check";
  var LOGIN_ROUTE = "/login";
  var TOKEN_SELECTOR = "input[name=\"csrf_token\"]";
  var CAPABLE_COOKIE = "sp_restore";
  var CAPABLE_MAX_AGE_S = 31536000;
  // The page stays hidden while the check runs; past this it gives up and
  // signs in again rather than leaving a blank page.
  var CHECK_TIMEOUT_MS = 8000;

  function markCapable() {
    try {
      document.cookie = CAPABLE_COOKIE + "=1; Path=/; Max-Age=" +
        CAPABLE_MAX_AGE_S + "; SameSite=Lax";
    } catch (e) {
      // Cookies blocked: the page then stays `no-store`.
    }
  }

  function hide() {
    document.documentElement.style.visibility = "hidden";
  }

  function reveal() {
    document.documentElement.style.removeProperty("visibility");
  }

  function signInAgain() {
    var path = window.location.pathname + window.location.search;
    var safe = path.charAt(0) === "/" && path.charAt(1) !== "/" &&
      path.indexOf("\\") === -1;
    window.location.replace(
      LOGIN_ROUTE + "?" + (safe ? "next=" + encodeURIComponent(path) + "&" : "") +
      "expired=1");
  }

  function pageToken() {
    var field = document.querySelector(TOKEN_SELECTOR);
    return field ? field.value : "";
  }

  function verify() {
    var token = pageToken();
    if (!token || !window.fetch) {
      signInAgain();
      return;
    }
    var settled = false;
    var controller = window.AbortController ? new window.AbortController() : null;
    var timer = window.setTimeout(function () {
      if (controller) {
        controller.abort();
      }
      if (!settled) {
        settled = true;
        signInAgain();
      }
    }, CHECK_TIMEOUT_MS);
    window.fetch(CHECK_ROUTE, {
      method: "POST",
      credentials: "same-origin",
      redirect: "manual",
      cache: "no-store",
      signal: controller ? controller.signal : undefined,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "page-restore"
      },
      body: "csrf_token=" + encodeURIComponent(token)
    }).then(function (response) {
      window.clearTimeout(timer);
      if (settled) {
        return;
      }
      settled = true;
      if (response.status === 204) {
        reveal();
      } else {
        signInAgain();
      }
    })["catch"](function () {
      window.clearTimeout(timer);
      if (!settled) {
        settled = true;
        signInAgain();
      }
    });
  }

  markCapable();
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) {
      return;
    }
    hide();
    verify();
  });
})();
