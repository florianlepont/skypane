"""Capture every companion page across language, theme and width.

Starts the seeded companion server the browser tests use
(test-support/companion_app_server.py with provisioned_fleet), signs in
through the test-support session helper (a local session row, never a real
credential), and visits each page in en/fr x light/dark x 360/1280 wide.

Browser driver: Python Playwright when it is importable, otherwise the
Node Playwright CLI package with the system Chrome (nothing is installed).
When neither can launch a browser every cell is written as "CI needed".

Output (JSON matrix and PNG screenshots) goes to --out, never to the repo.
Usage: python3 -I capture_pages.py --out DIR [--repo ROOT] [--only NAME,...]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

LANGS = ("en", "fr")
THEMES = ("light", "dark")
WIDTHS = {"360": (360, 800), "1280": (1280, 900)}
SHOT_CELLS = {("360", "light", "en"), ("360", "dark", "fr")}
NODE_PATH = "/opt/node22/lib/node_modules"
CHROME_CANDIDATES = ("/usr/bin/google-chrome", "/usr/bin/chromium")

# name -> (server, role, path template, group). Placeholders: {live}, {a1},
# {retired}, {pending} are frame ids of the seeded fleet.
PAGES = [
    ("home", "user", "/devices/{a1}/", "personal"),
    ("flights", "user", "/devices/{a1}/flights", "personal"),
    ("airlines-user", "user", "/devices/{a1}/airlines", "personal"),
    ("airlines-admin", "admin", "/devices/{live}/airlines", "personal"),
    ("style-departures", "user", "/devices/{a1}/display", "personal"),
    ("style-arrivals", "user", "/devices/{a1}/display/arrivals", "personal"),
    ("style-special-looks", "user", "/devices/{a1}/display/special-looks", "personal"),
    ("style-calendar", "user", "/devices/{a1}/display/calendar", "personal"),
    ("location", "user", "/devices/{a1}/detection", "personal"),
    ("account-user", "user", "/account", "personal"),
    ("account-admin", "admin", "/account", "personal"),
    ("credits", "user", "/credits", "personal"),
    ("signin", None, "/login", "personal"),
    ("not-found", "user", "/no-such-page", "personal"),
    ("fleet-list", "admin", "/fleet", "console"),
    ("fleet-frame", "admin", "/fleet?frame={live}", "console"),
    ("fleet-battery", "admin", "/fleet?frame={live}&view=battery", "console"),
    ("fleet-versions", "admin", "/fleet?frame={live}&view=versions", "console"),
    ("fleet-retired", "admin", "/fleet?frame={retired}", "console"),
    ("fleet-pending", "admin", "/fleet?frame={pending}", "console"),
    ("fleet-system", "admin", "/fleet?view=system", "console"),
    ("users", "admin", "/users", "console"),
    ("editor", "admin", "/airlines/manage", "console"),
    ("audit", "admin", "/audit", "console"),
    ("components", "admin", "/components", "console"),
]

# Page-side measurement, run by the driver in every cell.
MEASURE_JS = r"""
() => {
  const vis = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'
      && !el.closest('[hidden], dialog:not([open])') && s.opacity !== '0'
      && r.right > 0 && r.bottom > 0 && r.left < innerWidth + 1
      && !(el.closest('details:not([open])') && el.closest('details:not([open])') !== el
           && !(el.parentElement === el.closest('details:not([open])') && el.tagName === 'SUMMARY')
           && el.tagName !== 'SUMMARY')
      && !el.closest('.visually-hidden, .sr-only'); };
  const name = (el) => (el.getAttribute('aria-label') || '').trim()
    || ((el.getAttribute('aria-labelledby') || '').split(' ').map((i) => { const t = document.getElementById(i);
         return t ? t.textContent.trim() : ''; }).join(' ').trim())
    || (el.textContent || '').trim() || (el.getAttribute('title') || '').trim()
    || ((el.querySelector('img[alt]') || {}).alt || '').trim();
  const label = (el) => (name(el) || el.className || el.tagName).toString().slice(0, 40);
  const sel = 'a[href], button, summary, select, input:not([type=hidden]), [role=button], [role=tab], [role=switch]';
  const small = [], unnamed = [];
  document.querySelectorAll(sel).forEach((el) => {
    if (!vis(el)) return;
    let box = el.getBoundingClientRect();
    if (el.matches('input[type=radio], input[type=checkbox]')) {
      const l = el.labels && el.labels[0]; if (l && vis(l)) box = l.getBoundingClientRect();
      else if (el.closest('label')) box = el.closest('label').getBoundingClientRect();
    }
    if (el.tagName === 'A' && getComputedStyle(el).display === 'inline'
        && el.closest('p, li, .note, .caption, small, span, div') && (el.textContent || '').trim().length > 0
        && el.parentElement && /\S/.test(el.parentElement.childNodes[0] ? el.parentElement.textContent.replace(el.textContent, '') : '')) {
      return; }
    if (box.width < 43.5 || box.height < 43.5) {
      small.push({el: label(el), w: Math.round(box.width), h: Math.round(box.height), tag: el.tagName.toLowerCase()}); }
    if (!name(el) && !el.matches('input[type=radio], input[type=checkbox]')) unnamed.push(label(el));
    else if (!name(el) && !(el.labels && el.labels.length) && !el.closest('label')) unnamed.push(label(el));
  });
  const clipped = [];
  document.querySelectorAll('body *').forEach((el) => {
    if (!vis(el) || !(el.textContent || '').trim()) return;
    const s = getComputedStyle(el);
    if (['auto', 'scroll'].includes(s.overflowX)) return;
    if ((s.overflowX === 'hidden' || s.overflowX === 'clip' || s.textOverflow === 'ellipsis')
        && el.clientWidth > 4 && el.scrollWidth > el.clientWidth + 1) {
      clipped.push({el: label(el), sw: el.scrollWidth, cw: el.clientWidth, ellipsis: s.textOverflow === 'ellipsis'}); }
  });
  const props = {}; const names = new Set();
  try { for (const sh of document.styleSheets) { let rules; try { rules = sh.cssRules; } catch (e) { continue; }
    for (const r of rules) { if (r.style) for (const p of r.style) if (p.startsWith('--color-')) names.add(p); } } } catch (e) {}
  const cs = getComputedStyle(document.body);
  names.forEach((p) => { props[p] = cs.getPropertyValue(p).trim(); });
  const tabbar = document.querySelector('.tab-bar'); const side = document.querySelector('.sidebar-nav, .sidebar');
  const shown = (el) => !!el && vis(el);
  const labels = (root) => root ? Array.from(root.querySelectorAll('a, summary')).filter(vis)
    .map((a) => (a.getAttribute('aria-label') || a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)) : [];
  const texts = new Set();
  document.querySelectorAll('body *').forEach((el) => {
    if (!vis(el) || el.closest('.visually-hidden, script, style')) return;
    if (el.children.length === 0) { const t = (el.textContent || '').trim(); if (t.length > 2 && t.length < 90) texts.add(t); } });
  return {
    title: document.title, lang: document.documentElement.lang, theme: document.documentElement.dataset.uiTheme || null,
    h1: Array.from(document.querySelectorAll('h1')).filter(vis).map((h) => h.textContent.trim()),
    hscroll: document.documentElement.scrollWidth > innerWidth, scrollW: document.documentElement.scrollWidth, innerW: innerWidth,
    small, unnamed, clipped, colours: props,
    nav: {tabbar: shown(tabbar), sidebar: shown(side), tabLabels: shown(tabbar) ? labels(tabbar) : [], sideLabels: shown(side) ? labels(side) : []},
    splash: !!document.querySelector('[class*=splash]'),
    texts: Array.from(texts),
  };
}
"""


# Opens every <dialog> in turn with showModal() and measures it on its own.
DIALOGS_JS = r"""
async () => {
  const out = [];
  const list = Array.from(document.querySelectorAll('dialog'));
  for (const d of list) {
    const rec = {id: d.id || null, heading: ((d.querySelector('h1, h2, h3') || {}).textContent || '').trim().slice(0, 60)};
    try {
      if (!d.open) d.showModal();
      await new Promise((r) => setTimeout(r, 350));
      const r = d.getBoundingClientRect();
      rec.box = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
      rec.fitsViewport = r.left >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1;
      rec.innerScroll = d.scrollHeight > d.clientHeight + 1;
      const bg = getComputedStyle(d).backgroundColor; rec.background = bg;
      rec.small = []; rec.clipped = [];
      d.querySelectorAll('a[href], button, select, input:not([type=hidden]), summary').forEach((el) => {
        const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
        if (b.width === 0 || b.height === 0 || s.visibility === 'hidden') return;
        let box = b; if (el.matches('input[type=radio], input[type=checkbox]') && el.labels && el.labels[0]) box = el.labels[0].getBoundingClientRect();
        if (box.width < 43.5 || box.height < 43.5) rec.small.push([((el.getAttribute('aria-label') || el.textContent || el.className) + '').trim().slice(0, 30), Math.round(box.width), Math.round(box.height)]);
      });
      d.querySelectorAll('*').forEach((el) => { const s = getComputedStyle(el);
        if (el.clientWidth > 4 && (s.overflowX === 'hidden' || s.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1 && (el.textContent || '').trim())
          rec.clipped.push([(el.textContent || '').trim().slice(0, 30), el.scrollWidth, el.clientWidth]); });
      d.close();
    } catch (e) { rec.error = String(e).slice(0, 120); }
    out.push(rec);
  }
  return out;
}
"""

NODE_DRIVER = r"""
const {chromium} = require('playwright');
const fs = require('fs');
const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const MEASURE = eval('(' + cfg.measure + ')');
const DIALOGS = eval('(' + cfg.dialogs + ')');
(async () => {
  const browser = await chromium.launch({executablePath: cfg.chrome, args: ['--no-sandbox']});
  const out = [];
  for (const job of cfg.jobs) {
    for (const lang of cfg.langs) for (const theme of cfg.themes) for (const w of Object.keys(cfg.widths)) {
      const [vw, vh] = cfg.widths[w];
      const cell = {page: job.name, lang, theme, width: w, status: null};
      const ctx = await browser.newContext({viewport: {width: vw, height: vh}, reducedMotion: 'reduce'});
      try {
        const cookies = [
          {name: 'sp_ui_lang', value: lang, url: job.base},
          {name: 'sp_ui_theme', value: theme, url: job.base}];
        if (job.cookie) { const [n, v] = job.cookie.split('='); cookies.push({name: n, value: v, url: job.base, httpOnly: true}); }
        await ctx.addCookies(cookies);
        const page = await ctx.newPage();
        const resp = await page.goto(job.base + job.path, {waitUntil: 'load', timeout: 20000});
        cell.status = resp ? resp.status() : null; cell.finalUrl = page.url().replace(job.base, '');
        cell.splashAtLoad = await page.evaluate(() => !!document.querySelector('[class*=splash]'));
        const t0 = Date.now();
        await page.waitForFunction(() => { const e = document.querySelector('[class*=splash]');
          return !e || getComputedStyle(e).display === 'none' || getComputedStyle(e).visibility === 'hidden'
            || e.getBoundingClientRect().height === 0 || document.documentElement.classList.contains('splash-done'); },
          null, {timeout: 6000}).catch(() => { cell.splashStuck = true; });
        cell.splashMs = Date.now() - t0;
        await page.waitForTimeout(800);
        Object.assign(cell, await page.evaluate(MEASURE));
        cell.dialogs = await page.evaluate(DIALOGS);
        const key = [w, theme, lang].join('/');
        if (cfg.shots.includes(key)) {
          const f = job.name + '__' + w + '-' + theme + '-' + lang + '.png';
          await page.screenshot({path: cfg.outdir + '/' + f, fullPage: true}); cell.shot = f; }
      } catch (e) { cell.error = String(e).slice(0, 300); }
      await ctx.close(); out.push(cell);
    }
  }
  await browser.close();
  fs.writeFileSync(cfg.outdir + '/' + cfg.result, JSON.stringify(out, null, 1));
})();
"""


def find_chrome():
    for path in CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return shutil.which("google-chrome") or shutil.which("chromium")


def seed_server(repo, live_owner, workdir):
    """Start one seeded server from `repo` and return (server, ids, helpers)."""
    support = os.path.join(repo, "test-support")
    for entry in (support, repo):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    import companion_app_server  # noqa: PLC0415
    import provisioned_fleet  # noqa: PLC0415
    state_dir = os.path.join(workdir, "state-" + live_owner)
    ids = provisioned_fleet.provision_fleet(state_dir, live_owner=live_owner)
    server = companion_app_server.AppServer(state_dir)
    server.start()
    return server, ids, companion_app_server


def build_jobs(only, servers):
    jobs = []
    for name, role, path, group in PAGES:
        if only and name not in only:
            continue
        server, ids, helper = servers["a" if role == "user" else "admin"]
        frame_ids = {
            "live": ids.live, "a1": ids.a1, "retired": ids.retired,
            "pending": ids.pending}
        cookie = None
        if role == "user":
            cookie = helper.session_cookie_for_state_dir(
                server.state_dir, email="user-a@example.test", role="user")
        elif role == "admin":
            cookie = helper.session_cookie_for_state_dir(server.state_dir)
        jobs.append({
            "name": name, "group": group, "role": role, "base": server.base_url(),
            "path": path.format(**frame_ids), "cookie": cookie})
    return jobs


def run_driver(jobs, outdir, result_name, chrome):
    cfg = {
        "jobs": jobs, "langs": LANGS, "themes": THEMES, "widths": WIDTHS,
        "shots": ["/".join((w, t, lang)) for (w, t, lang) in SHOT_CELLS],
        "outdir": outdir, "result": result_name, "chrome": chrome, "measure": MEASURE_JS, "dialogs": DIALOGS_JS}
    cfg["shots"] = ["%s/%s/%s" % cell for cell in SHOT_CELLS]
    cfg_path = os.path.join(outdir, "driver-config-" + result_name)
    driver_path = os.path.join(outdir, "driver.js")
    with open(cfg_path, "w") as fh:
        json.dump(cfg, fh)
    with open(driver_path, "w") as fh:
        fh.write(NODE_DRIVER)
    env = dict(os.environ, NODE_PATH=NODE_PATH)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(key, None)
    env["NO_PROXY"] = "127.0.0.1"
    proc = subprocess.run(
        ["node", driver_path, cfg_path], env=env, capture_output=True, text=True, timeout=1500)
    return proc


def ci_needed_matrix(jobs, reason):
    return [
        {"page": j["name"], "lang": lang, "theme": theme, "width": width, "status": "CI needed",
         "reason": reason}
        for j in jobs for lang in LANGS for theme in THEMES for width in WIDTHS]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="scratch directory for JSON and PNG output")
    parser.add_argument("--repo", default=os.getcwd(), help="repository root to serve")
    parser.add_argument("--only", default="", help="comma-separated page names")
    parser.add_argument("--result", default="matrix.json", help="result file name inside --out")
    args = parser.parse_args()
    only = {n for n in args.only.split(",") if n}
    os.makedirs(args.out, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="capture-state-", dir=args.out)
    servers = {}
    try:
        for key, owner in (("a", "a"), ("admin", "admin")):
            servers[key] = seed_server(os.path.abspath(args.repo), owner, workdir)
        jobs = build_jobs(only, servers)
        chrome = find_chrome()
        if chrome is None:
            matrix = ci_needed_matrix(jobs, "no browser available locally")
            with open(os.path.join(args.out, args.result), "w") as fh:
                json.dump(matrix, fh, indent=1)
            print("no browser: every cell marked CI needed")
            return 0
        proc = run_driver(jobs, args.out, args.result, chrome)
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr[-2000:])
            matrix = ci_needed_matrix(jobs, "browser driver failed: " + proc.stderr[-200:])
            with open(os.path.join(args.out, args.result), "w") as fh:
                json.dump(matrix, fh, indent=1)
        return proc.returncode
    finally:
        for server, _ids, _helper in servers.values():
            server.stop()


if __name__ == "__main__":
    sys.exit(main())
