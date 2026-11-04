# companion/static/vendor/leaflet - Vendor Provenance

## `leaflet.js` / `leaflet.css` / `LICENSE`

- **Upstream:** Leaflet 1.9.4, https://leafletjs.com, https://github.com/Leaflet/Leaflet
- **Source:** the npm tarball `https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz`,
  downloaded with curl on 2026-11-03 and extracted in an empty scratch
  directory. No package manager was run; the repository has no `package.json`,
  lockfile or `node_modules`.
- **Upstream paths:** `package/dist/leaflet.js`, `package/dist/leaflet.css`,
  `package/LICENSE`
- **Licence:** BSD-2-Clause, Copyright (c) 2010-2023 Vladimir Agafonkin and
  (c) 2010-2011 CloudMade. The licence text travels with the code as `LICENSE`.
- **Local modifications:** none; the three files are byte-for-byte copies.

| File | Bytes | SHA-256 |
|------|-------|---------|
| `leaflet.js` | 147552 | `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a` |
| `leaflet.css` | 14806 | `a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6` |
| `LICENSE` | 1395 | `53e8dc25862014e4324741ca18fbe3611e11d42ef69f59f86ea8c5389647d4cb` |

## Scan result (2026-11-03)

`leaflet.js` contains none of `eval(`, `new Function`, `XMLHttpRequest`,
`fetch(`, `navigator.sendBeacon`, `process.env`, `document.write`. The only
URLs in it are the SVG XML namespace and the documentation link
`https://leafletjs.com` in the header comment; it imports nothing remote.
`companion/test_vendored_leaflet.py` repeats the scan and the hash check on the
served bytes.

## Why 1.9.4

It is the latest stable release; Leaflet 2.0 is still a pre-release.

## Images are not vendored

`leaflet.css` refers to `images/*.png` (layers control, default marker). The
location page uses no layers control and no PNG marker, so the images are
neither vendored nor served.

## Upgrade note

Download the new tarball from the npm registry into an empty directory, copy
the three files unmodified, record the new sizes and SHA-256 values here and in
`companion/test_vendored_leaflet.py`, re-run the scan, and re-run the companion
tests. Check the Content-Security-Policy of the location page still needs
nothing beyond the two named hosts.
