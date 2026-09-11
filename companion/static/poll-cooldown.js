/*
 * SkyPane companion service — poll-cooldown.js.
 *
 * D-18 (19-04-PLAN.md, A-35): externalizes the two inline <script>
 * elements companion/pages/config_page.py's poll_trigger_section() used
 * to emit — the D-01 live cooldown countdown and the UXA-15 disable-on-
 * submit affordance — so companion/app.py's Content-Security-Policy can
 * set script-src 'self' with no 'unsafe-inline' and no nonce. Like
 * copy-button.js/dirty-state.js before it, this file has no build step,
 * no bundler, no framework and no dependency of any kind, and must stay
 * written to an ES5-safe subset (no let/const/arrow functions/template
 * literals/backticks) so no transpiler is ever needed to ship it. It is
 * served by companion/app.py's POLL_COOLDOWN_SCRIPT_ROUTE, mirroring the
 * existing /static/style.css route.
 *
 * Standing constraint this file must never violate: no HTML-writing
 * sink of any kind anywhere in this file — only textContent and
 * attribute reads/removals. Every value this file touches is a data-*
 * attribute companion/pages/config_page.py's poll_trigger_section()
 * already ran through escape_html() at render time.
 *
 * This script is served to every page on the site (a single cached
 * static asset, not re-emitted per page). Most pages carry no
 * #poll-trigger-btn at all — today only Settings does — so the guard
 * below is load-bearing, not defensive noise, matching the project's
 * established convention.
 */
(function () {
  "use strict";

  var btn = document.getElementById("poll-trigger-btn");
  if (!btn) {
    return;
  }

  // D-01: the live countdown. Present only on poll_trigger_section()'s
  // disabled branch, via the button's own data-cooldown attribute — a
  // server-computed, history_db-persisted remaining-seconds figure,
  // never re-derived client-side from a duration constant.
  //
  // parseInt()+isNaN(), not truthy: must agree with poll_trigger_
  // section()'s own "greater than zero" branch test, or a
  // negative/non-numeric value could take the disabled branch (natively
  // disabling the button)
  // while this script inertly no-ops, leaving no way to re-enable it
  // client-side.
  var rawRemaining = btn.getAttribute("data-cooldown");
  var remaining = parseInt(rawRemaining, 10);
  if (rawRemaining !== null && !isNaN(remaining) && remaining > 0) {
    var textId = btn.getAttribute("data-cooldown-text-id");
    var text = textId ? document.getElementById(textId) : null;
    var template = btn.getAttribute("data-cooldown-template");
    var token = btn.getAttribute("data-cooldown-token");
    if (text && template && token) {
      var timer = setInterval(function () {
        remaining -= 1;
        if (remaining <= 0) {
          clearInterval(timer);
          btn.removeAttribute("disabled");
          text.textContent = "";
          return;
        }
        text.textContent = template.replace(token, String(remaining));
      }, 1000);
    }
  }

  // UXA-15: the disable-on-submit affordance. Present only on poll_
  // trigger_section()'s enabled (zero-cooldown) branch, via the
  // button's own data-submit-pending attribute. Cosmetic only, never a
  // trust boundary — companion/app.py's _POLL_LOCK is the actual
  // correctness boundary, independent of this affordance.
  var pendingText = btn.getAttribute("data-submit-pending");
  if (pendingText) {
    var form = btn.form;
    if (form) {
      form.addEventListener("submit", function () {
        btn.disabled = true;
        btn.textContent = pendingText;
      });
    }
  }

  // No DOMContentLoaded wrapper is needed: the <script> tag
  // companion/layout.py's page_shell() emits carries the defer
  // attribute, so this file only ever runs after parsing. Do not add
  // one later.
})();
