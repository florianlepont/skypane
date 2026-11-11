/* Shared helpers for the v1.3 photo sketches (007-009): URL params, the
   EN/FR dictionary, the sketch chrome (variant tabs, language, theme,
   per-sketch state controls), the mock navigation and procedural SVG
   scenes. Throwaway sketch code, plain JS, no dependencies. */
(function () {
  const q = new URLSearchParams(location.search);
  const SK = window.SK = {
    lang: (q.get('lang') || 'en').toLowerCase().startsWith('fr') ? 'fr' : 'en',
    theme: q.get('theme') === 'dark' ? 'dark' : 'light',
    chrome: q.get('chrome') !== '0',
    variant: (q.get('v') || 'a').toLowerCase(),
    q, state: {}, dict: {}, renderFn: null,
  };
  const NB = ' ';

  /* ---------- i18n: SK.add({ key: ['English', 'Français'] }) ---------- */
  SK.add = function (map) { Object.assign(SK.dict, map); };
  SK.t = function (key, vars) {
    const e = SK.dict[key];
    let s = e ? e[SK.lang === 'fr' ? 1 : 0] : '[' + key + ']';
    if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
    if (SK.lang === 'fr') s = s.replace(/ ([:;!?»])/g, NB + '$1').replace(/« /g, '«' + NB);
    return s;
  };
  SK.num = function (n, digits) {
    return new Intl.NumberFormat(SK.lang === 'fr' ? 'fr-FR' : 'en-GB',
      { minimumFractionDigits: digits || 0, maximumFractionDigits: digits || 0 }).format(n);
  };
  SK.pct = function (v) { return Math.round(v * 100) + (SK.lang === 'fr' ? NB + '%' : '%'); };
  SK.esc = function (s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); };
  SK.applyStatic = function () {
    document.documentElement.lang = SK.lang;
    document.querySelectorAll('[data-i]').forEach(n => { n.textContent = SK.t(n.dataset.i); });
    document.querySelectorAll('[data-i-html]').forEach(n => { n.innerHTML = SK.t(n.dataset.iHtml); });
    ['aria-label', 'title', 'placeholder'].forEach(a => {
      document.querySelectorAll('[data-i-' + a + ']').forEach(n => n.setAttribute(a, SK.t(n.getAttribute('data-i-' + a))));
    });
  };

  /* ---------- icons ---------- */
  const P = {
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    flights: '<path d="M10.5 13.5L3 11l1-2 8 1 5-5a2 2 0 013 3l-5 5 1 8-2 1-2.5-7.5z"/>',
    photos: '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="M4 18l5-5 4 4 3-3 4 4"/>',
    style: '<circle cx="12" cy="12" r="9"/><circle cx="8.5" cy="10" r="1.2"/><circle cx="12" cy="7.5" r="1.2"/><circle cx="15.5" cy="10" r="1.2"/>',
    location: '<path d="M12 21s7-6.2 7-11.5A7 7 0 005 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    device: '<rect x="6" y="3" width="12" height="18" rx="2"/><path d="M9 17h6"/>',
    health: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    upload: '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"/>',
    trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    about: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="7.8" r=".6"/>',
    alert: '<path d="M12 7v6"/><circle cx="12" cy="17" r=".6"/>',
    info: '<path d="M12 11v6"/><circle cx="12" cy="7.5" r=".6"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r=".8"/><circle cx="4.5" cy="12" r=".8"/><circle cx="4.5" cy="18" r=".8"/>',
    crop: '<path d="M6 2v14a2 2 0 002 2h14"/><path d="M2 6h14a2 2 0 012 2v14"/>',
    up: '<path d="M12 19V6M6 11l6-6 6 6"/>', down: '<path d="M12 5v13M6 13l6 6 6-6"/>',
    left: '<path d="M19 12H6M11 6l-6 6 6 6"/>', right: '<path d="M5 12h13M13 6l6 6-6 6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', reset: '<path d="M4 12a8 8 0 112.5 5.8"/><path d="M4 18v-6h6"/>',
    shuffle: '<path d="M4 7h4l8 10h4M4 17h4l2.5-3M14 9l2-2h4"/><path d="M18 5l2 2-2 2M18 15l2 2-2 2"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  };
  SK.icon = function (name, size) {
    const s = size ? ' style="width:' + size + 'px;height:' + size + 'px"' : '';
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"' + s + '>' + (P[name] || '') + '</svg>';
  };

  /* ---------- mock navigation ---------- */
  SK.add({
    'nav.home': ['Home', 'Accueil'], 'nav.flights': ['Flights', 'Vols'], 'nav.photos': ['Photos', 'Photos'],
    'nav.style': ['Style', 'Style'], 'nav.location': ['Location', 'Lieu'], 'nav.device': ['Device', 'Appareil'],
    'nav.health': ['Health', 'État'], 'nav.more': ['More', 'Plus'],
    'nav.frame': ['Salon frame', 'Cadre du salon'],
    'nav.tabs_label': ['Main navigation', 'Navigation principale'],
  });
  const NAV = [['home', 'home'], ['flights', 'flights'], ['photos', 'photos'], ['style', 'style'], ['location', 'location'], ['device', 'device'], ['health', 'health']];
  const TABS = ['home', 'flights', 'photos', 'device', 'more'];
  SK.mountNav = function (active) {
    const side = document.getElementById('sidebar');
    if (side) side.innerHTML = '<div class="site-title"><span class="logo"></span>SkyPane</div>' +
      '<nav aria-label="' + SK.esc(SK.t('nav.tabs_label')) + '">' +
      NAV.map(([k, ic]) => '<a class="sidebar-link" href="#" onclick="return false" ' + (k === active ? 'aria-current="page"' : '') + '>' + SK.icon(ic) + '<span>' + SK.esc(SK.t('nav.' + k)) + '</span></a>').join('') + '</nav>' +
      '<div class="sidebar-foot">' + SK.esc(SK.t('nav.frame')) + '</div>';
    const mh = document.getElementById('mheader');
    if (mh) mh.innerHTML = '<div class="site-title"><span class="logo"></span>SkyPane</div><span class="small muted">' + SK.esc(SK.t('nav.frame')) + '</span>';
    const tb = document.getElementById('tabbar');
    if (tb) tb.innerHTML = TABS.map(k => '<a href="#" onclick="return false" ' + (k === active ? 'aria-current="page"' : '') + '><span class="pill">' + SK.icon(k === 'more' ? 'more' : k) + '<span class="lbl">' + SK.esc(SK.t('nav.' + k)) + '</span></span></a>').join('');
    if (tb) tb.setAttribute('aria-label', SK.t('nav.tabs_label'));
  };

  /* ---------- sketch chrome ---------- */
  SK.setLang = function (l) { SK.lang = l; refreshChrome(); SK.rerender(); };
  SK.setTheme = function (t) { SK.theme = t; document.documentElement.setAttribute('data-theme', t); refreshChrome(); };
  SK.setVariant = function (v) {
    SK.variant = v;
    document.querySelectorAll('.variant').forEach(n => { n.hidden = n.id !== 'variant-' + v; });
    refreshChrome(); SK.rerender();
  };
  SK.setState = function (k, v) { SK.state[k] = v; refreshChrome(); SK.rerender(); };
  SK.rerender = function () {
    SK.applyStatic();
    if (SK.mountActive) SK.mountNav(SK.mountActive);
    if (SK.renderFn) SK.renderFn();
  };
  let cfg = null;
  function refreshChrome() {
    const bar = document.getElementById('sk-bar');
    if (!bar || !cfg) return;
    bar.querySelectorAll('[data-sk]').forEach(b => {
      const [kind, val, key] = b.dataset.sk.split('|');
      let on = false;
      if (kind === 'v') on = SK.variant === val;
      if (kind === 'lang') on = SK.lang === val;
      if (kind === 'theme') on = SK.theme === val;
      if (kind === 's') on = String(SK.state[key]) === val;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }
  SK.initChrome = function (c) {
    cfg = c;
    document.documentElement.setAttribute('data-theme', SK.theme);
    document.body.classList.add(SK.chrome ? 'chrome' : 'nochrome');
    (c.states || []).forEach(s => { SK.state[s.key] = q.get(s.key) != null ? q.get(s.key) : s.def; });
    if (SK.chrome) {
      const bar = document.createElement('div'); bar.id = 'sk-bar'; bar.className = 'sk-bar';
      let h = '<b>' + SK.esc(c.title) + '</b><span class="sk-group" role="group" aria-label="Variant">' +
        c.variants.map(([id, label]) => '<button data-sk="v|' + id + '">' + SK.esc(label) + '</button>').join('') + '</span>';
      (c.states || []).forEach(s => {
        h += '<span class="sk-sep">|</span><span>' + SK.esc(s.label) + '</span><span class="sk-group">' +
          s.options.map(([v, l]) => '<button data-sk="s|' + v + '|' + s.key + '">' + SK.esc(l) + '</button>').join('') + '</span>';
      });
      h += '<span class="sk-group" style="margin-left:auto"><button data-sk="lang|en">EN</button><button data-sk="lang|fr">FR</button></span>' +
        '<span class="sk-group"><button data-sk="theme|light">Light</button><button data-sk="theme|dark">Dark</button></span>';
      bar.innerHTML = h; document.body.prepend(bar);
      bar.addEventListener('click', e => {
        const b = e.target.closest('[data-sk]'); if (!b) return;
        const [kind, val, key] = b.dataset.sk.split('|');
        if (kind === 'v') SK.setVariant(val);
        if (kind === 'lang') SK.setLang(val);
        if (kind === 'theme') SK.setTheme(val);
        if (kind === 's') SK.setState(key, val);
      });
      const fit = () => { document.body.style.paddingTop = bar.offsetHeight + 'px'; document.documentElement.style.setProperty('--sk-h', bar.offsetHeight + 'px'); };
      fit(); addEventListener('resize', fit); setTimeout(fit, 50);
    }
    SK.setVariant(c.variants.some(v => v[0] === SK.variant) ? SK.variant : c.variants[0][0]);
  };

  /* ---------- transient toast (success) ---------- */
  SK.flash = function (tone, titleKey, detailKey, vars) {
    let reg = document.querySelector('.toast-region');
    if (!reg) { reg = document.createElement('div'); reg.className = 'toast-region'; reg.setAttribute('role', 'status'); document.body.appendChild(reg); }
    const n = document.createElement('div'); n.className = 'toast toast--' + tone;
    n.innerHTML = '<span class="toast__icon">' + SK.icon('check') + '</span><span class="toast__text"><span class="toast__title">' + SK.esc(SK.t(titleKey, vars)) + '</span>' +
      (detailKey ? '<span class="toast__detail">' + SK.esc(SK.t(detailKey, vars)) + '</span>' : '') + '</span>';
    reg.appendChild(n); setTimeout(() => n.remove(), 4500);
  };

  /* ---------- procedural scenes (SVG, 300x200, no external images) ---------- */
  const poly = (pts, f, extra) => '<polygon points="' + pts + '" fill="' + f + '"' + (extra || '') + '/>';
  const rect = (x, y, w, h, f) => '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="' + f + '"/>';
  const circ = (x, y, r, f, extra) => '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + f + '"' + (extra || '') + '/>';
  let gid = 0;
  const grad = (stops, vertical) => {
    const id = 'g' + (++gid);
    return ['<linearGradient id="' + id + '" x1="0" y1="0" x2="' + (vertical === false ? 1 : 0) + '" y2="' + (vertical === false ? 0 : 1) + '">' +
      stops.map(s => '<stop offset="' + s[0] + '" stop-color="' + s[1] + '"/>').join('') + '</linearGradient>', 'url(#' + id + ')'];
  };
  function pine(x, y, s, f) {
    return poly((x) + ',' + (y - 38 * s) + ' ' + (x - 9 * s) + ',' + (y - 16 * s) + ' ' + (x - 5 * s) + ',' + (y - 16 * s) + ' ' + (x - 13 * s) + ',' + (y + 2 * s) + ' ' + (x + 13 * s) + ',' + (y + 2 * s) + ' ' + (x + 5 * s) + ',' + (y - 16 * s) + ' ' + (x + 9 * s) + ',' + (y - 16 * s), f) + rect(x - 1.5 * s, y + 2 * s, 3 * s, 8 * s, '#3b2a1e');
  }
  const SCENES = [
    /* 0: lake at sunrise. Detail is spread across the width so a crop visibly changes. */
    function () {
      const [d1, sky] = grad([[0, '#1f3f7a'], [0.55, '#e8a14a'], [1, '#f7d98a']]);
      const [d2, lake] = grad([[0, '#e3a44f'], [1, '#2a4d86']]);
      return d1 + d2 +
        rect(0, 0, 300, 110, sky) + circ(228, 112, 26, '#fff3c4') + circ(228, 112, 36, '#fff3c4', ' opacity=".28"') +
        poly('0,110 40,60 62,78 96,38 140,92 175,70 215,104 262,80 300,104 300,112 0,112', '#2b3f66') +
        poly('96,38 86,52 96,48 104,54', '#f4f6fb') +
        poly('0,112 70,92 140,106 210,96 300,110 300,114 0,114', '#1d2d49') +
        rect(0, 112, 300, 88, lake) +
        '<g opacity=".75">' + rect(206, 118, 44, 3, '#fff0b8') + rect(212, 126, 32, 3, '#fff0b8') + rect(216, 134, 22, 3, '#fff0b8') + rect(220, 143, 14, 3, '#fff0b8') + '</g>' +
        poly('118,148 150,148 144,156 124,156', '#b0281f') + rect(133, 118, 2, 30, '#222') + poly('135,120 135,146 158,146', '#fbfbf6') + poly('133,126 133,146 118,146', '#f0e050') +
        rect(0, 168, 300, 32, '#22351f') + pine(30, 176, 1.6, '#1a3a24') + pine(58, 184, 1.1, '#24472c') + pine(272, 182, 1.3, '#1a3a24') +
        '<path d="M70 40q6-7 12 0M84 32q5-6 10 0M190 30q5-6 10 0" stroke="#1d2d49" stroke-width="1.6" fill="none"/>';
    },
    /* 1: alpine dusk */
    function () {
      const [d, sky] = grad([[0, '#40306b'], [0.6, '#d9728a'], [1, '#f6c27a']]);
      return d + rect(0, 0, 300, 200, sky) + circ(70, 60, 14, '#fdf1d0') +
        poly('0,150 60,70 100,120 150,40 210,130 250,90 300,140 300,200 0,200', '#4b4a7a') + poly('150,40 132,76 150,66 166,80', '#fbfbff') +
        poly('0,170 90,130 170,160 260,125 300,150 300,200 0,200', '#2c2a4d') + rect(0, 180, 300, 20, '#1b1a33');
    },
    /* 2: sea and lighthouse */
    function () {
      const [d, sky] = grad([[0, '#6fb2e6'], [1, '#dff0fb']]);
      return d + rect(0, 0, 300, 200, sky) + rect(0, 120, 300, 80, '#2d6aa3') +
        '<g fill="#fff" opacity=".8"><ellipse cx="60" cy="40" rx="30" ry="9"/><ellipse cx="86" cy="34" rx="22" ry="8"/><ellipse cx="220" cy="56" rx="34" ry="9"/></g>' +
        poly('0,150 60,134 110,150 200,140 300,152 300,200 0,200', '#4d86bd') +
        poly('196,150 204,70 220,70 228,150', '#f4f4f0') + rect(203, 90, 18, 10, '#b0281f') + rect(203, 116, 18, 10, '#b0281f') + rect(201, 60, 22, 10, '#333') + poly('199,60 212,46 225,60', '#b0281f') +
        poly('160,160 300,150 300,200 140,200', '#6b6f73');
    },
    /* 3: forest path */
    function () {
      const [d, sky] = grad([[0, '#bfe3c2'], [1, '#f3f0c4']]);
      let t = '';
      [20, 62, 104, 178, 224, 270].forEach((x, i) => { t += pine(x, 150 + (i % 2) * 8, 2 + (i % 3) * .3, i % 2 ? '#1f4a2c' : '#2e6a3c'); });
      return d + rect(0, 0, 300, 200, sky) + rect(0, 150, 300, 50, '#3c6a38') + t + poly('120,200 135,150 165,150 200,200', '#c9ae7e');
    },
    /* 4: poppy field */
    function () {
      let dots = ''; for (let i = 0; i < 46; i++) dots += circ((i * 53) % 300, 128 + ((i * 29) % 70), 2.4 + (i % 3) * .5, i % 4 ? '#d63a2a' : '#f0e050');
      return rect(0, 0, 300, 200, '#7ec0ee') + '<g fill="#fff" opacity=".9"><ellipse cx="80" cy="36" rx="34" ry="10"/><ellipse cx="190" cy="52" rx="40" ry="11"/></g>' +
        poly('0,120 80,100 170,116 260,98 300,110 300,200 0,200', '#5a9a46') + rect(0, 140, 300, 60, '#4d8a3c') + dots;
    },
    /* 5: city skyline at dusk */
    function () {
      const [d, sky] = grad([[0, '#1d2a55'], [1, '#f0a26a']]);
      let b = ''; [[10, 90, 30], [44, 60, 26], [74, 100, 34], [112, 70, 24], [140, 112, 36], [180, 84, 28], [212, 54, 30], [246, 96, 40]].forEach(([x, y, w]) => { b += rect(x, 200 - y - 20, w, y + 20, '#14182e'); for (let i = 0; i < 5; i++) b += rect(x + 5 + (i % 2) * 11, 200 - y - 10 + i * 12, 4, 5, '#f7d98a'); });
      return d + rect(0, 0, 300, 200, sky) + circ(220, 100, 18, '#ffe9b0') + b;
    },
    /* 6: desert dunes */
    function () {
      const [d, sky] = grad([[0, '#f4c48a'], [1, '#fce6c4']]);
      return d + rect(0, 0, 300, 200, sky) + circ(70, 50, 16, '#fff6dc') + poly('0,130 90,100 170,140 250,110 300,130 300,200 0,200', '#d9894a') + poly('0,170 100,140 200,176 300,150 300,200 0,200', '#b8662f');
    },
    /* 7: autumn trees */
    function () {
      let t = ''; [[50, 150, 26, '#d86a1f'], [110, 160, 22, '#e8b22b'], [200, 148, 30, '#b0281f'], [260, 162, 22, '#d86a1f']].forEach(([x, y, r, f]) => { t += rect(x - 3, y, 6, 36, '#4a3322') + circ(x, y - 4, r, f); });
      return rect(0, 0, 300, 200, '#cfe3ee') + rect(0, 170, 300, 30, '#8a6b3a') + t;
    },
  ];
  SK.scene = function (kind, opts) {
    const o = opts || {};
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" ' +
      (o.size ? 'width="' + o.size[0] + '" height="' + o.size[1] + '" ' : '') +
      'preserveAspectRatio="' + (o.par || 'xMidYMid slice') + '" role="img" aria-label="' + SK.esc(o.label || '') + '">' + SCENES[kind % SCENES.length]() + '</svg>';
  };
})();
