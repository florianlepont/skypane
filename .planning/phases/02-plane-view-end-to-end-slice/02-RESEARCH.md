# Phase 2: Plane View — End-to-End Slice - Research

**Researched:** 2026-08-08
**Domain:** ADS-B-driven data pipeline + Pillow raster rendering + always-on VPS hosting, wired into an already-working device/protocol layer
**Confidence:** HIGH (enrichment API and render pipeline were verified with live calls and executable experiments against this project's own real data, not just documentation reading)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (superseded framing):** Phase 1's plan 01-04 resolved "local ADS-B vs. aggregator API" with a validated result: **aggregator-sufficient**. Both adsb.fi and airplanes.live cleared coverage comfortably (38/37 distinct aircraft ≤3000ft, 2/2 on-ground detections) over ~92 real minutes at the runway-3 geofence; only update-cadence missed a pre-committed threshold, judged immaterial given the device's multi-minute refresh cycle. **No RTL-SDR hardware, no local receiver.** `.planning/PROJECT.md`/`.planning/ROADMAP.md` still contain stale "local ADS-B receiver" wording — known doc-drift, not a live decision. Treat D-01 as authoritative regardless of what those files say until Phase 1 close corrects them.
- **D-02 (flight enrichment):** Raw ADS-B gives position/altitude/speed/callsign only — no airline name or destination/origin. Add a supplementary free lookup keyed by callsign/hex to resolve airline name + route. Must evaluate concrete free options and confirm one actually returns route data for real Orly callsigns (Phase 1's `adsb-test/samples/*.jsonl`) before locking a provider. **Specific API choice left to research** — resolved below.
- **D-03 (runway configuration detection):** Departure vs. arrival inferred directly from ADS-B track data already collected — climbing altitude + track heading away from the runway = departure; descending altitude + track heading toward the runway = arrival. No external NOTAM/config feed. Uses fields already captured by `adsb-test/query_aggregator.py`: `altitude`, `on_ground`, `vertical_rate`. **Exact climbing/descending and toward/away thresholds left to planner, informed by real sample data** — resolved below.
- **D-04 (between-flights display state):** When no aircraft is in the runway-3 geofence, keep showing the last detected flight — no "waiting" state, no artificial expiry. Consistent with the locked no-freshness-indicator decision. Persists until the next detection, however long that takes.
- **Visual rendering/layout:** Explicitly deferred to `02-UI-SPEC.md` (already produced, Revision 2, pending checker sign-off) — this research treats the UI-SPEC as a locked design contract to implement, not a design question to re-open.

### Claude's Discretion

- Exact enrichment API/provider selection (per D-02) — resolved below: **adsbdb.com** (`api.adsbdb.com`).
- Specific thresholds for "climbing/descending" and "toward/away" in runway-configuration inference (D-03) — resolved below using Phase 1's real sample data.
- Real VPS provisioning specifics (OS image, deployment method, secrets management, TLS) — resolved below: Hetzner CX22, Ubuntu 24.04 LTS, systemd services/timers, Caddy for automatic TLS.

### Deferred Ideas (OUT OF SCOPE)

- Updating `.planning/PROJECT.md`/`REQUIREMENTS.md`/`ROADMAP.md` wording to reflect the aggregator-sufficient decision — tracked since Phase 1's 01-04 plan, pending at Phase 1 close. Not this phase's job; downstream agents treat D-01 above as authoritative regardless.
- Visual rendering/layout of the plane view — belongs to `02-UI-SPEC.md`, already produced.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLANE-01 | User can see flight number, airline, and destination for the next plane departing Orly runway 3 | adsbdb.com callsign lookup verified live against 38 real Orly callsigns (20/38 = 52.6% hit rate); D-03 climb-threshold values derived from real sample vertical-rate data; Pillow render pipeline verified to produce hard-edged output per UI-SPEC |
| PLANE-02 | User can see flight number, airline, and origin for the next plane landing on runway 3 (arrival configuration) | Same enrichment API (symmetric origin/destination fields in one response); D-03 descent-threshold values empirically derived from real sample data (all 20 tracked hexes in Phase 1's sample were arrivals, giving strong descent-side coverage but zero climb-side real data — flagged as an Open Question below) |
| PLANE-03 | Plane view updates one flight at a time, as real aircraft use runway 3, detected via the aggregator API (D-01 supersedes the stale "local ADS-B receiver" wording) | Reuse `adsb-test/query_aggregator.py` geofence/query pattern; scheduled polling architecture (systemd timer) documented below; multi-aircraft-in-geofence selection logic flagged as an Open Question |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

These directives from `.claude/CLAUDE.md` constrain this phase's implementation and were treated as locked, not re-litigated:

- **Server language/runtime:** Python 3.12, "boring, reliable" library choices preferred (e.g. `requests` over anything fancier).
- **Rendering:** Pillow (PIL) for panel image generation; `Image.quantize(..., dither=Image.FLOYDSTEINBERG)` is explicitly reserved for future photographic content only — this phase's UI-SPEC mandates `dither=Image.NONE`/no anti-aliasing for all flat shapes and glyphs.
- **Scheduling:** "APScheduler **or plain cron**" — both are sanctioned; this research recommends systemd timers (the modern Ubuntu-native equivalent of cron) over pulling in APScheduler, see Architecture Patterns below.
- **Hosting:** Hetzner CX22 (~€4.35/mo), always-on — explicitly NOT a scale-to-zero tier, matching "device should always find a reachable server."
- **Vendoring discipline:** Phase 1 vendored/trimmed rather than reimplemented wherever a working reference existed (flightportrait's server/firmware code); same approach applies to extending `byos_server.py` in this phase — extend, don't rewrite the protocol layer.
- **Secrets discipline:** Config/state kept out of git (`secrets.h` pattern in firmware, gitignored sample data); same discipline expected for VPS secrets/API keys (env file, not committed).
- **No custom crypto/provisioning reinvention:** Not directly applicable this phase (BLE provisioning is Phase 4+ scope; Phase 1 hardcoded `secrets.h` credentials instead), but the same philosophy applies to TLS — use Caddy's built-in Let's Encrypt automation rather than hand-rolling certificate management.
- **What NOT to use (from CLAUDE.md):** OpenSky Network or a local SDR as the flight-data source (superseded by D-01's validated aggregator-sufficient result — this project uses adsb.fi/airplanes.live, not OpenSky); a scale-to-zero hosting tier; Arduino framework for shipped firmware (not touched this phase).

## Summary

Phase 2's real engineering surface is almost entirely server-side. The device firmware built in Phase 1 already speaks the full protocol against a configurable `INK_API_BASE`; the only firmware-adjacent change is pointing that macro at the real VPS's `https://` base (a config change, not a code change — already anticipated in `firmware/main/api_client.c`'s comments). The work is: (1) a plane-detection module that reuses `adsb-test/query_aggregator.py`'s geofence-query pattern on a schedule, (2) a flight-enrichment client against **adsbdb.com**, verified live against real Orly-area callsigns, (3) runway-configuration inference with concrete numeric thresholds derived from Phase 1's real sample data, (4) a Pillow render pipeline that draws directly onto an indexed "P"-mode image (verified experimentally to produce zero anti-aliasing artifacts, satisfying UI-SPEC's hard-edge rendering rule for free), (5) a minimal, deliberately non-rewriting extension of `stub-server/byos_server.py`, and (6) Hetzner CX22 provisioning with Caddy-automated TLS.

The single most consequential finding is the enrichment API's real-world coverage: querying `api.adsbdb.com/v0/callsign/{callsign}` against all 38 distinct real callsigns from Phase 1's sample data returned a full route (airline + origin + destination) for only **20 of 38 (52.6%)** — meaning the UI-SPEC's "Route unavailable" fallback state is not a rare edge case, it is an expected, roughly-coin-flip outcome for this specific traffic mix (mostly Transavia France low-cost-carrier callsigns with per-tail suffixes that aren't in adsbdb's crowdsourced route database). The render pipeline finding is the second most consequential: drawing text and shapes directly onto a Pillow `"P"`-mode (indexed-palette) image with `fill=<exact palette index>` produces **zero intermediate colors** — confirmed by direct pixel-count inspection — which fully satisfies the UI-SPEC's anti-aliasing-disabled rendering rule without needing any supersample-then-threshold workaround, provided any pre-rasterized asset (the vendored aircraft silhouette) is hard-thresholded back to a binary mask after any resize.

**Primary recommendation:** Extend `byos_server.py` minimally (fix its hardcoded `http://` `image_url` scheme — a real bug once Caddy TLS is in front of it), add a separate systemd-timer-driven Python script that polls the aggregator → detects the runway-3 aircraft → enriches via adsbdb.com (in-process cache keyed by callsign, not re-queried every poll) → renders directly onto a `"P"`-mode Pillow canvas → atomically swaps the served image file. No new web framework, no APScheduler, no database — just `Pillow` and `requests` as new dependencies, deployed on Hetzner CX22 (Ubuntu 24.04 LTS) behind Caddy for automatic HTTPS.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ADS-B aggregator polling (geofenced query) | API/Backend | — | Scheduled server-side job; reuses `adsb-test/query_aggregator.py` pattern directly, no device involvement |
| Runway-configuration inference (D-03) | API/Backend | — | Pure business logic over already-fetched track data; belongs with the detection module, not the device (device has no ADS-B awareness at all) |
| Flight enrichment (airline/route lookup) | API/Backend | — | Outbound call to a third-party API; must never happen on the device (battery/radio-time budget, per DEVICE-05/03) |
| Panel image rendering (Pillow) | API/Backend | — | Server pre-renders on its own schedule so the device's short poll window is always answered from a warm, already-rendered file (per CLAUDE.md's APScheduler/cron rationale) |
| Device poll protocol (setup/display/log endpoints) | API/Backend | Embedded/Device Client | Server: `byos_server.py` (already vendored, minimally extended). Device: firmware's `api_client.c` (already built in Phase 1, config-only change this phase) |
| Last-detected-flight cache (D-04) | API/Backend (in-process) | — | No database needed — the UI-SPEC's own Empty-state copy ("no aircraft detected yet **since server start**") means an in-memory cache that resets on restart is spec-correct, not a shortcut |
| TLS termination | API/Backend (infra) | — | Caddy reverse-proxying to `byos_server.py`'s plain-HTTP loopback listener; satisfies DEVICE-03's "polls over HTTPS" without touching the vendored protocol code |
| Deep-sleep wake/poll cycle, display blit | Embedded/Device Client | — | Entirely Phase 1 firmware, unchanged this phase except `INK_API_BASE` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.3.0 (verified current on PyPI 2026-08-08; local dev env has 11.3.0, both share the same `Image`/`ImageDraw`/`ImageFont`/palette APIs used here) [VERIFIED: PyPI registry] | Panel raster rendering — indexed-palette drawing, TTF text, mask-based compositing | Confirmed experimentally in this session: drawing directly onto a `"P"`-mode image with integer palette-index fills produces zero anti-aliasing artifacts — the exact behavior UI-SPEC's "disable anti-aliasing" rule requires, with no extra library needed |
| requests | 2.34.2 (verified current on PyPI 2026-08-08) [VERIFIED: PyPI registry] | HTTP client for aggregator (adsb.fi/airplanes.live) and enrichment (adsbdb.com) calls | Already CLAUDE.md's stated choice ("standard, boring, reliable"); Phase 1's `query_aggregator.py` used stdlib `urllib` instead specifically to avoid a pip install for a throwaway spike script — Phase 2 is the real server, so `requests`' timeout/retry/session ergonomics are worth the one dependency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none — see "Don't Hand-Roll" below for why FastAPI/APScheduler/python-dotenv/cairosvg are deliberately excluded) | — | — | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| systemd timer + plain script for the poll→render loop | FastAPI + APScheduler (CLAUDE.md's documented pairing) | FastAPI/APScheduler is the more "webapp-shaped" choice and would unify the HTTP+scheduling code into one process; systemd timer keeps the already-tested `byos_server.py` contract completely untouched (lower regression risk against `test_poll_cycle.py`'s 15/15 assertions) and needs zero new pip dependencies. Use FastAPI+APScheduler instead if a later phase (RER view, Phase 3) needs a second concurrent scheduled job and unifying them in one process becomes worth the complexity |
| adsbdb.com as sole enrichment provider | hexdb.io as a secondary fallback | Live-tested: hexdb.io recovered 2 of 4 sampled adsbdb misses (EJU84YF, KMM466) but missed the same 2 Transavia France (TVF) callsigns adsbdb missed — coverage is complementary, not a strict superset. Deferred for MVP: UI-SPEC's fallback contract already treats "no route" as a clean degrade-to-"Route unavailable" state, so a second lookup adds latency/complexity for a coverage gain that doesn't change user-visible behavior in the failure case (both TVF misses persist either way) |
| Pre-rasterized silhouette PNG (vendor-time conversion) | cairosvg / resvg-py at runtime | No SVG parsing library needed as a runtime dependency for a single static, never-changing vendored asset — rasterize once when vendoring the SVG (any tool: `rsvg-convert`, Inkscape, even a browser "save as PNG"), commit the resulting PNG alpha mask, and the server only ever does Pillow resize+threshold+paste at render time |
| Caddy for TLS | nginx + certbot | Caddy's automatic-HTTPS-by-default (single-line config, Let's Encrypt HTTP-01, auto-renewal) fits a single-service hobby VPS better than nginx+certbot's more manual cert lifecycle; nginx+certbot is the better choice only if the VPS later hosts multiple services needing fine-grained proxy config |

**Installation:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install "Pillow==12.3.0" "requests==2.34.2"
```

**Version verification:** Confirmed directly against the PyPI JSON API this session:
```bash
curl -s https://pypi.org/pypi/Pillow/json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['version'])"
# → 12.3.0 (uploaded 2026-07-01)
curl -s https://pypi.org/pypi/requests/json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['version'])"
# → 2.34.2 (uploaded 2026-05-14)
```
Note: CLAUDE.md's original stack table cites "Pillow 11.x" — this is now one major version behind the verified current release (12.3.0). The `Image`/`ImageDraw`/`ImageFont`/palette APIs this phase uses are long-stable across that boundary; no known breaking change affects this phase's usage. Recommend pinning to the verified-current 12.3.0 rather than the stale 11.x figure, and re-verifying at execution time since this is a fast-moving figure (see Metadata's "Valid until").

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|-------------|
| Pillow | PyPI | Long-established (python-pillow/Pillow, PIL's direct successor) | Not resolvable via this session's tooling (`weeklyDownloads: null`) | github.com/python-pillow/Pillow | [SUS] (reason: `unknown-downloads`) | **Approved** — tool artifact, not a genuine risk signal. `unknown-downloads` reflects a data-availability gap in the legitimacy-check tool, not evidence of low adoption; Pillow is the de facto standard Python imaging library, already explicitly recommended in this project's own CLAUDE.md, with a long-standing official GitHub org repo |
| requests | PyPI | Long-established (psf/requests, official Python Software Foundation-adjacent project) | Not resolvable (`weeklyDownloads: null`) | github.com/psf/requests | [SUS] (reason: `unknown-downloads`) | **Approved** — same tool artifact as above; `requests` is explicitly named "standard, boring, reliable" in this project's own CLAUDE.md |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** Pillow, requests — both dispositioned "Approved" above; the `unknown-downloads` signal is a limitation of the legitimacy-check tool's data source for PyPI (it could not resolve a download-count metric for either package in this session), not a finding about the packages themselves. Cross-checked independently via each package's official PyPI project page and GitHub organization (`python-pillow`, `psf`) — both long-standing, canonical projects, and both are already named directly in this project's own `.claude/CLAUDE.md` stack recommendations, which predates this research session. **No `checkpoint:human-verify` gate is warranted for these two specific packages** given this cross-check; the planner may install them directly. Any *additional* Python package introduced during planning/execution beyond these two must go through the same check before being added to `requirements.txt`.

**Not applicable to this audit:** Caddy (installed via the official Debian/Ubuntu apt repository or static Go binary — not a language package manager install; the npm registry has an unrelated, irrelevant low-download package also named `caddy` that must NOT be installed via `npm install caddy` under any circumstance — that is a different, unrelated project).

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────── Hetzner CX22 VPS (Ubuntu 24.04 LTS) ───────────────────────────────┐
│                                                                                                       │
│  systemd timer (every 30-60s)                                                                        │
│        │                                                                                             │
│        ▼                                                                                             │
│  ┌─────────────────────┐     ┌────────────────────┐     ┌─────────────────────┐                     │
│  │ 1. Poll aggregator   │────▶│ 2. Filter geofence  │────▶│ 3. Pick ONE aircraft │                    │
│  │ adsb.fi /            │     │ (runway3.json bbox, │     │ (see Open Questions  │                    │
│  │ airplanes.live       │     │  alt ≤3000ft)       │     │  for multi-hit rule) │                    │
│  └─────────────────────┘     └────────────────────┘     └──────────┬──────────┘                     │
│                                                                       │                                │
│                                                                       ▼                                │
│                                              ┌──────────────────────────────────────┐                 │
│                                              │ 4. Infer runway config (D-03)         │                 │
│                                              │ vertical_rate ≥ +200 ft/min → depart   │                 │
│                                              │ vertical_rate ≤ -200 ft/min → arrive   │                 │
│                                              │ else: hold last confirmed state        │                 │
│                                              └──────────────────┬───────────────────┘                 │
│                                                                   │                                     │
│                                                                   ▼                                     │
│                                  ┌────────────────────────────────────────────────┐                   │
│                                  │ 5. Enrich (cache-first, keyed by callsign)      │                   │
│                                  │    cache hit? → skip network call               │                   │
│                                  │    cache miss? → GET api.adsbdb.com/v0/callsign │                   │
│                                  │    404/error? → "Route unavailable" fallback     │                   │
│                                  └──────────────────────┬───────────────────────────┘                 │
│                                                             │                                            │
│                                                             ▼                                            │
│                                  ┌────────────────────────────────────────────────┐                   │
│                                  │ 6. Render (Pillow, "P"-mode canvas, exact       │                   │
│                                  │    palette indices — see Code Examples)         │                   │
│                                  │    → pack to 960,000-byte Spectra 6 .bin        │                   │
│                                  └──────────────────────┬───────────────────────────┘                 │
│                                                             │                                            │
│                                                             ▼ atomic os.replace()                        │
│                                                    panel.bin (served file)                               │
│                                                             │                                            │
│                                                             ▼                                            │
│  ┌──────────────┐  HTTPS  ┌───────────────────┐  loopback HTTP  ┌──────────────────────┐               │
│  │ Device (poll │────────▶│ Caddy (:443, auto │────────────────▶│ byos_server.py       │               │
│  │ every N min, │         │ Let's Encrypt TLS) │                │ (:8642, 127.0.0.1)   │               │
│  │ deep sleep   │◀────────│                    │◀────────────────│ setup/display/log/img│               │
│  │ between)     │  image  └───────────────────┘  panel.bin bytes └──────────────────────┘               │
│  └──────────────┘                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
server/
├── plane/
│   ├── detect.py          # geofence query against adsb.fi/airplanes.live (adapts adsb-test/query_aggregator.py)
│   ├── runway_config.py   # D-03 inference: vertical_rate + track heading → departure/arrival
│   ├── enrich.py          # adsbdb.com client, in-process cache keyed by callsign
│   └── render.py          # Pillow "P"-mode render pipeline → 960,000-byte .bin
├── poll_loop.py           # the systemd-timer entrypoint: detect → infer → enrich → render → atomic swap
├── assets/
│   ├── icons/
│   │   ├── aircraft-silhouette.svg   # vendored source (provenance only)
│   │   ├── aircraft-silhouette.png   # pre-rasterized alpha mask (used at render time)
│   │   └── VENDOR.md
│   └── fonts/
│       ├── Inter-Regular.ttf
│       ├── Inter-Bold.ttf
│       └── VENDOR.md
├── state/
│   └── panel.bin           # the currently-served image, atomically replaced each cycle
├── test_plane_detection.py # stdlib harness, follows stub-server/test_poll_cycle.py convention
├── test_runway_config.py
├── test_enrich.py
├── test_render.py
└── requirements.txt
```
(`stub-server/byos_server.py`, `.../make_test_panel.py`, `.../VENDOR.md` stay in place and are extended in-place, per the "extend, don't rewrite" instruction — not moved into `server/`.)

### Pattern 1: Draw directly on an indexed "P"-mode canvas — never compose in RGB then quantize
**What:** Create the panel canvas as `Image.new("P", (1200, 1600), color=<bg_index>)`, call `putpalette()` once with the exact 6 legal colors at fixed indices, then draw all shapes/text with `fill=<int index>` — never build the frame in RGB and call `quantize()` at the end.
**When to use:** Every render this phase. This is the single technique that satisfies UI-SPEC's "disable anti-aliasing... threshold edges to the two flat legal colors" rule for text and solid shapes, with no extra code.
**Example:**
```python
# Verified this session: ImageDraw.text() on a "P"-mode image with an
# integer fill produces EXACTLY 2 unique palette indices in the output
# (background + foreground) — zero intermediate/gray pixels, confirmed
# via Image.getcolors() on the rendered result.
from PIL import Image, ImageDraw, ImageFont

# nibble codes per PROTOCOL.md §1 / make_test_panel.py:
# 0x0 black, 0x1 white, 0x2 yellow, 0x3 red, 0x5 blue, 0x6 green
# Pillow palette indices must be contiguous from 0, so index 4 is
# assigned to blue (nibble 0x5) — remap at pack time (see Pattern 3).
PALETTE_RGB = [
    0, 0, 0,        # index 0 -> nibble 0x0 black
    255, 255, 255,  # index 1 -> nibble 0x1 white
    255, 255, 0,    # index 2 -> nibble 0x2 yellow
    255, 0, 0,      # index 3 -> nibble 0x3 red
    0, 0, 255,      # index 4 -> nibble 0x5 blue (index/nibble differ!)
    0, 255, 0,      # index 5 -> nibble 0x6 green (index/nibble differ!)
]
INDEX_TO_NIBBLE = {0: 0x0, 1: 0x1, 2: 0x2, 3: 0x3, 4: 0x5, 5: 0x6}

BLUE_IDX, WHITE_IDX = 4, 1
canvas = Image.new("P", (1200, 1600), color=BLUE_IDX)
canvas.putpalette(PALETTE_RGB + [0, 0, 0] * (256 - 6))
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("server/assets/fonts/Inter-Bold.ttf", 88)
draw.text((150, 900), "AF56XX", fill=WHITE_IDX, font=font)
```

### Pattern 2: Pre-rasterize the vendored silhouette once, threshold after every resize
**What:** The SVG silhouette is rasterized to a PNG alpha mask exactly once at vendor time (external tool, not a runtime dependency). At render time, `Image.resize()` reintroduces gray edge pixels (confirmed: 159 distinct gray levels after a `LANCZOS` resize of a simple test shape in this session) — these must be hard-thresholded back to a strict binary mask with `.point()` before `paste()`, or the paste will alpha-blend gray edges into unintended intermediate colors.
**When to use:** Any time the pre-rasterized silhouette mask is resized to fit the UI-SPEC's ~900px-wide / mirrored-by-state target box.
**Example:**
```python
# Verified this session: without the .point() threshold step, a resized
# mask carries ~150+ distinct gray levels and alpha-blends into the
# canvas; with it, the final canvas contains exactly 2 palette indices.
mask = Image.open("server/assets/icons/aircraft-silhouette.png").convert("L")
mask = mask.resize(target_size, Image.LANCZOS)          # reintroduces AA gray
mask = mask.point(lambda p: 255 if p > 127 else 0)       # hard threshold back to binary
if departing:
    mask = mask.transpose(Image.FLIP_LEFT_RIGHT)          # nose-right per UI-SPEC
fill = Image.new("P", canvas.size, color=WHITE_IDX)
fill.putpalette(PALETTE_RGB + [0, 0, 0] * (256 - 6))
canvas.paste(fill, (x, y), mask=mask)
```

### Pattern 3: Pack the "P"-mode canvas to the exact 960,000-byte protocol format
**What:** `stub-server/make_test_panel.py` already defines the exact byte layout this phase's renderer must produce: 1600 rows × 600 bytes, 2 px/byte, left pixel in the high nibble, only the six legal nibble codes. The render pipeline's last step converts the Pillow "P"-mode canvas's index buffer into this format using `INDEX_TO_NIBBLE` (Pattern 1) — this is inherently custom code (no library does Spectra-6 nibble packing), but it is a small, already-fully-specified transform, not a design decision.
**When to use:** Once, as the final step of `server/plane/render.py`.
**Example:**
```python
def pack_panel(canvas):  # canvas: "P"-mode, 1200x1600
    px = list(canvas.getdata())
    out = bytearray(600 * 1600)
    for row in range(1600):
        base = row * 1200
        obase = row * 600
        for col in range(0, 1200, 2):
            left = INDEX_TO_NIBBLE[px[base + col]]
            right = INDEX_TO_NIBBLE[px[base + col + 1]]
            out[obase + col // 2] = (left << 4) | right
    assert len(out) == 960000
    return bytes(out)
```
(Optimize with `numpy` only if profiling shows this loop is too slow for the render cadence — at a 30-60s cadence this is very unlikely to matter; do not add `numpy` as a dependency pre-emptively.)

### Anti-Patterns to Avoid
- **Composing the frame in RGB and calling `Image.quantize(dither=Image.NONE)` at the end:** works in principle but is strictly harder to get right than drawing directly in "P" mode with exact indices (Pattern 1) — quantize's nearest-color mapping for arbitrary RGB values you compute yourself is an extra place to introduce an off-palette color by mistake. Draw directly with indices instead.
- **Re-querying the enrichment API on every poll cycle for an already-cached callsign:** wastes calls against an undocumented rate limit and adds latency to every render cycle for no benefit (D-04 already establishes that the displayed flight doesn't change until a genuinely new aircraft is detected).
- **Hardcoding the `image_url` scheme in `byos_server.py`'s `/device/v1/display` response:** the vendored file currently does `"http://%s/img/%s.bin" % (host, digest)` unconditionally (line 141-142) — this must become `https://` once Caddy is in front, or the device is silently told to download the 960KB panel over plaintext HTTP even after polling the metadata endpoint over TLS. See Common Pitfalls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Flight route/airline-name lookup | A custom scraper or static ICAO-airline-code table + a second manually-maintained route database | `api.adsbdb.com/v0/callsign/{callsign}` — one call returns airline name, IATA/ICAO flight number, and origin+destination (with clean municipality names) together | Live-verified this session against 38 real Orly callsigns; open-source (mrjackwills/adsbdb), free, no API key, CORS-enabled, actively maintained |
| TLS certificate issuance/renewal | Hand-rolled certbot cron job, manual cert renewal, self-signed certs | Caddy's built-in automatic HTTPS (Let's Encrypt HTTP-01, auto-renewal) | Zero-config for a single-domain single-service VPS; matches this project's stated aversion to hand-rolling security-adjacent infrastructure (CLAUDE.md's BLE-provisioning rationale applies by the same logic) |
| SVG-to-raster conversion at runtime | `cairosvg`/`resvg-py` as a server dependency | Pre-rasterize once at vendor time, commit the PNG mask | The silhouette is a single static asset that never changes at runtime — a runtime SVG-parsing dependency buys nothing here and adds install-time complexity (cairosvg needs system `libcairo`) |
| Scheduling the poll→render loop | A hand-rolled `while True: sleep()` daemon process, or pulling in APScheduler for a single job | A systemd timer unit calling a oneshot script | systemd timers already provide restart-on-failure, logging via journald, and a standard admin interface (`systemctl status`) for free on the target Ubuntu VPS — no extra process supervision code needed |
| Env var loading for secrets (API keys, bearer setup secret) | `python-dotenv` | systemd's native `EnvironmentFile=` directive in the unit file | One less pip dependency; systemd already reads a `KEY=VALUE` file directly into the service's environment, and this project's own convention (secrets.h pattern) already favors keeping secrets in a plain, gitignored file read by the runtime rather than a library-mediated mechanism |

**Key insight:** Every "don't hand-roll" item above is really the same principle applied twice — this phase needs exactly two new pip dependencies (Pillow, requests) because systemd (already present on the target OS) and Caddy (a single static binary) absorb what would otherwise become FastAPI+APScheduler+python-dotenv+cairosvg. Fewer runtime dependencies means less to secure, less to keep updated, and a smaller diff against the already-tested `byos_server.py` contract.

## Common Pitfalls

### Pitfall 1: Enrichment lookup misses are the common case, not the exception
**What goes wrong:** Building/testing the enrichment client against only 2-3 hand-picked callsigns (e.g. the AF1380-style examples in the UI-SPEC's copy) gives a false impression that the "Route unavailable" fallback is rare.
**Why it happens:** adsbdb's route database is crowdsourced and has much better coverage for legacy/full-service carriers (Air France, Iberia, TAP, Air Algérie, CCM Airlines, Vueling all hit 100% in this session's test) than for low-cost carriers using per-tail rotating callsigns (Transavia France/`TVF` hit only 2 of 20 in this session's live test).
**How to avoid:** Design and test the render pipeline's fallback path from day one, not as an afterthought — write `server/test_enrich.py` against real recorded misses (the `TVF*` callsigns from `adsb-test/samples/`) alongside real hits, not just hits.
**Warning signs:** A demo/manual QA session that only ever shows Air France or Iberia flights and never exercises the "Route unavailable" caption.

### Pitfall 2: `byos_server.py`'s hardcoded `http://` image URL breaks HTTPS-over-Caddy
**What goes wrong:** The vendored `Handler.do_GET`'s `/device/v1/display` branch builds `"http://%s/img/%s.bin" % (host, digest)` unconditionally (verified by direct read of `stub-server/byos_server.py` lines 140-142). Once Caddy terminates TLS in front of this process, the device will still receive an `http://` image URL and — because firmware's `url_valid()` in `api_client.c` accepts either scheme — will silently download the 960KB panel image over plaintext HTTP even though the metadata request itself went over HTTPS.
**Why it happens:** The reference implementation was written for the "frame allows plain http for hand-set targets" local-stub case (documented in the file's own docstring) and was never updated for a real TLS-fronted deployment.
**How to avoid:** When extending `byos_server.py` for Phase 2, change the hardcoded scheme to `https://` (safe because production always sits behind Caddy) rather than leaving it as a copy-paste holdover. This is a one-line, deliberate, documented deviation from the vendored file — record it in `stub-server/VENDOR.md`'s "Local modifications" list per that file's own re-pinning discipline.
**Warning signs:** Packet capture or Caddy access logs showing a device fetching `/img/*.bin` on port 80 instead of 443 in production.

### Pitfall 3: Single-sample vertical-rate noise near touchdown can flip the departure/arrival inference
**What goes wrong:** Real sample data shows `vertical_rate` values of `+48 ft/min` appearing repeatedly on aircraft that are unambiguously landing (descending from 425ft to on-ground over the next few samples) — a flare/rounding artifact right before touchdown. A naive `vertical_rate > 0 → departure` check would misclassify this moment as a departure signal.
**Why it happens:** ADS-B's Mode-S vertical-rate field is quantized in 64 ft/min steps and genuinely goes near-zero during the flare just before touchdown; a raw sign check on a single sample is not robust to this.
**How to avoid:** Use a deadband, not a zero-crossing: classify `vertical_rate ≥ +200 ft/min` as a climbing signal and `≤ -200 ft/min` as a descending signal (both comfortably above the observed `+48 ft/min` noise floor and above 3× the 64 ft/min quantization step); values between -200 and +200 should not flip the currently-held D-03 state — hold the last confirmed configuration rather than re-inferring from a single ambiguous sample.
**Warning signs:** The display flipping between DEPARTING/ARRIVING captions mid-approach for a single aircraft that is only ever landing.

### Pitfall 4: Multiple aircraft in the geofence simultaneously — no disambiguation rule exists yet
**What goes wrong:** `runway3.json`'s bbox (sized to cover the full ~3320m runway plus approach/rollout margin) can and does contain more than one aircraft at once in real traffic (confirmed in Phase 1's samples — e.g. two separate hex tracks with overlapping timestamp windows). D-03/D-04 describe how to classify and persist *a* flight, but not which one to pick when several are simultaneously in-bbox.
**Why it happens:** The geofence is deliberately generous (to catch full approach/rollout) and Orly's runway-3 corridor sees genuinely overlapping traffic during busy periods.
**How to avoid:** See Open Questions — this needs an explicit selection rule (e.g., lowest altitude / most likely to be "the" runway-3 event right now) before planning task breakdown; flagging here rather than silently picking an implicit default.
**Warning signs:** The displayed flight number appearing to "jump" erratically between two genuinely different simultaneous aircraft on a busy poll cycle.

### Pitfall 5: The runway-3 geofence is not perfectly exclusive of the nearby 06/24 runway
**What goes wrong:** `adsb-test/runway3.json`'s own sourcing note states the bbox "is not perfectly exclusive of the nearby, non-parallel 06/24 runway, whose western end sits close to runway 3's western threshold" — an aircraft using a different runway could occasionally register as an in-bbox detection.
**Why it happens:** Geofence was computed from runway-3's own threshold coordinates with margin, not hand-tuned against the full airport layout.
**How to avoid:** Carried forward as a known limitation from Phase 1, not a new Phase 2 finding — no new mitigation is in scope this phase (RTL-SDR-precision geofencing was explicitly rejected by D-01), but the render pipeline's real-world QA pass should watch for occasional wrong-runway flights appearing in the plane view.
**Warning signs:** A displayed flight whose enriched destination/origin makes no sense for runway-3 traffic patterns (e.g., a very short-haul regional hop using a runway typically reserved for different traffic).

## Code Examples

Verified patterns from this session's direct testing (not third-party docs — see each Pattern above in Architecture Patterns for the full runnable code):

- **Indexed-canvas text rendering with zero AA artifacts** — Pattern 1 above; verified via `Image.getcolors()` on the rendered output showing exactly 2 unique indices.
- **Resize-then-threshold mask compositing** — Pattern 2 above; verified via distinct-gray-level counts before (159) and after (2) the threshold step.
- **Live enrichment API response shape** (`api.adsbdb.com/v0/callsign/TVF16VB`, captured this session):
```json
{"response":{"flightroute":{
  "callsign":"TVF16VB","callsign_icao":"TVF16VB","callsign_iata":"TO16VB",
  "airline":{"name":"Transavia France","icao":"TVF","iata":"TO","country":"France","country_iso":"FR","callsign":"FRENCH SUN"},
  "origin":{"country_iso_name":"FR","country_name":"France","elevation":291,"iata_code":"ORY","icao_code":"LFPO","latitude":48.7233333,"longitude":2.3794444,"municipality":"Paris","name":"Paris-Orly Airport"},
  "destination":{"country_iso_name":"ES","country_name":"Spain","elevation":27,"iata_code":"PMI","icao_code":"LEPA","latitude":39.551701,"longitude":2.73881,"municipality":"Palma De Mallorca","name":"Palma de Mallorca Airport"}
}}}
```
Use `destination.municipality` (e.g. `"Palma De Mallorca"`) for the UI-SPEC's sentence-case route-line city name — note the API returns title case, not exactly sentence case; a small `.title()`-aware or manual capitalization normalization step may be needed depending on exact UI-SPEC conformance requirements for mixed-case municipality names (e.g. "De" vs "de").
- **404 shape for a genuinely unknown callsign** (captured this session): `{"response":"unknown callsign"}` with HTTP 404 — trivial to detect and route to the "Route unavailable" fallback.
- **Caddy minimal config for automatic HTTPS without owning a domain** (nip.io-style, no DNS setup required — verified via web search this session, standard documented Caddy/nip.io pattern):
```
203-0-113-10.nip.io {
    reverse_proxy 127.0.0.1:8642
}
```
(Replace with the VPS's real IP address in dash form; nip.io resolves that hostname to the embedded IP automatically, satisfying Let's Encrypt's HTTP-01 challenge with zero DNS configuration — a real owned domain is not required for this MVP phase, though one may be added later without changing this pattern.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| certbot + nginx manual cert renewal cron jobs | Caddy's built-in automatic HTTPS | Caddy has defaulted to this since v2 (2020) | Simpler, fewer moving parts for a single-service VPS; still valid/current as of this session's verification |
| Composing RGB then quantizing to a palette | Drawing directly on a Pillow `"P"`-mode image with explicit palette indices | Not a recent Pillow change — this is a long-standing Pillow capability that is simply underused in most e-ink rendering tutorials, which default to the RGB+quantize workflow because it's the first thing most Pillow docs demonstrate | For a fixed, small, hard-saturated palette like Spectra 6, the direct-index approach is strictly more predictable and was verified this session to eliminate AA-dithering risk entirely |

**Deprecated/outdated:** None directly relevant — no library or API used this phase has a documented deprecation affecting this project's usage.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | Ubuntu 24.04 LTS is the right image choice over the newer Ubuntu 26.04 (also confirmed available on Hetzner Cloud per this session's web search) | Standard Stack / VPS provisioning | Low — both are viable; 24.04 was chosen for maturity/boring-and-reliable fit with project philosophy, not because 26.04 is unavailable or broken. If 26.04's package versions (Python, systemd) turn out materially better for this stack, switching is a fresh-VM decision with no migration cost since nothing is deployed yet |
| A2 | `api.adsbdb.com` has no hard rate limit that this project's expected call volume (roughly one enrichment call per newly-detected flight, cached thereafter — likely tens to low hundreds per day) would hit | Standard Stack / Don't Hand-Roll | Low-Medium — undocumented in adsbdb's own README per this session's fetch; if a limit exists and is hit, the fallback path ("Route unavailable") already handles the failure gracefully per UI-SPEC, so user-visible impact is bounded, but it would degrade PLANE-01/02 more often than the 52.6%-coverage baseline suggests |
| A3 | The `TVF*` (Transavia France) low route-lookup coverage observed in this session (2/20 hits) reflects a general adsbdb data-completeness gap for this carrier's callsign pattern, not a transient outage during testing | Common Pitfalls / Summary | Medium — if this was a temporary adsbdb data gap rather than a structural one, the real-world "Route unavailable" frequency could be lower than 47% once deployed; either way the fallback path must be built and tested, so this doesn't change the required engineering work, only the expected frequency users will see it |
| A4 | The `TVF` route-lookup misses correlate with per-tail/random callsign suffixes rather than any lookup-key formatting issue in this project's own query (e.g. trailing whitespace, case sensitivity) | Common Pitfalls | Low — the *same* 404 response shape (`"unknown callsign"`) was returned for both a clearly-malformed test input and the real misses, and adjacent TVF callsigns with different suffixes had genuinely mixed hit/miss results in this session's test (not a uniform 100% miss for the whole prefix), which is consistent with genuine per-flight data gaps rather than a systematic query bug — but this project's actual production query code should still be tested against these exact recorded miss cases to rule out a self-inflicted formatting bug |

**If this table is empty:** N/A — see entries above; all four are LOW-to-MEDIUM risk and none blocks planning.

## Open Questions

1. **Which single aircraft to display when multiple are in the runway-3 geofence simultaneously?**
   - What we know: The geofence bbox is intentionally generous (covers full approach/rollout for both runway ends) and Phase 1's real sample data shows overlapping-timestamp detections of different hexes are a real occurrence, not a hypothetical.
   - What's unclear: D-03/D-04 specify how to classify and persist *a* flight's state, but not a selection rule among simultaneous candidates.
   - Recommendation: The planner should pick an explicit, simple rule for the MVP — e.g., "lowest current altitude" (closest to being the immediate departure/arrival event) or "most recently transitioned on/off ground" — and document it as a locked decision in the plan rather than leaving it implicit in code.

2. **Are the D-03 climb-side (departure) thresholds validated against any real departure data?**
   - What we know: This session's real-sample-data analysis of every multi-observation hex in Phase 1's ~92-minute window shows **100% of tracked aircraft were descending arrivals** — runway 3 was apparently in arrival configuration for the entire sampled window. The recommended `≥ +200 ft/min` departure threshold (Common Pitfall 3) is derived by symmetry with the well-evidenced descent threshold, not from any observed real climbing aircraft.
   - What's unclear: Whether real runway-3 departures produce vertical-rate/track-heading signals that actually clear this threshold cleanly, or whether departure profiles look meaningfully different (e.g., faster initial climb rate, different track-heading noise characteristics right after rotation).
   - Recommendation: Treat the departure-side threshold as provisional pending real-world QA once an actual runway-3 departure is observed on live hardware/staging; do not treat it as equally well-validated as the arrival-side threshold in verification planning.

3. **Does the UI-SPEC's "airline line falls back to 'Route unavailable'" wording mean the route line (TO/FROM + city) also blanks out, or only the airline-name line?**
   - What we know: Layout & Composition lists the route line (item 7) and airline line (item 9) as two visually distinct lines; the Copywriting Contract's fallback row title says "Airline line falls back to..." but its body text says "only the airline/route line degrades" (ambiguous plural).
   - What's unclear: Whether a route-lookup 404 should render as one combined fallback replacing both lines, or leave the route line blank/omitted while only the airline line shows "Route unavailable."
   - Recommendation: This is a UI-SPEC ambiguity, not a research gap — flag for the planner to resolve with a one-line clarification (either re-reading UI-SPEC literally as "the whole airline-line role is replaced" and treating the route line as simply omitted in that state, or looping back to `/gsd-ui-phase` for a one-line fix) before task breakdown, since it affects exactly which Pillow draw calls execute in the fallback branch.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Python 3 (local dev) | Writing/testing server code locally before deploy | ✓ | 3.9.6 (macOS system Python) | Target production is 3.12 (Ubuntu 24.04 default) — recommend installing a local 3.12 via `pyenv`/`brew install python@3.12` for parity before relying on any 3.10+-only syntax; nothing in this phase's planned code needs 3.10+ features, so 3.9 is sufficient for local iteration if parity isn't set up |
| git | Vendoring assets, committing server code | ✓ | 2.50.1 | — |
| Docker | Not required this phase (native systemd deployment recommended over containerizing) | ✓ (available, running) | — | N/A — deliberately not used for the server this phase, unlike Phase 1's containerized firmware build |
| ssh / scp / rsync | Deploying code to the Hetzner VPS | ✓ | OpenSSH 10.2p1 | — |
| Caddy | TLS termination on the VPS | ✗ (not installed locally — correct, it belongs on the VPS, not the dev machine) | — | Install via the official Caddy apt repository on the Ubuntu VPS at provisioning time; not needed locally |
| Hetzner Cloud account/API token | VPS provisioning | Unconfirmed — not verifiable from this repository/session | — | Must be provisioned as part of this phase's execution (D-09/CONTEXT.md explicitly defers real VPS provisioning to this phase) |
| `api.adsbdb.com` reachability | Flight enrichment | ✓ — confirmed reachable and responsive this session via direct HTTPS calls from this network | — | If unreachable from the deployed VPS specifically (different network path), the "Route unavailable" fallback already covers total enrichment outage gracefully per D-04/UI-SPEC |

**Missing dependencies with no fallback:** none — the one required-but-unconfirmed item (Hetzner account/API token) is expected to be provisioned as part of this phase's own execution, not a pre-existing gap.

**Missing dependencies with fallback:** Caddy (install at VPS provisioning time, not needed locally); local Python version parity (3.9 dev vs 3.12 target — low risk, no 3.10+ syntax needed).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | stdlib-only harness scripts (project convention — no pytest; see `stub-server/test_poll_cycle.py`, which asserts protocol behavior directly via `assert` statements and a `main()`/exit-code pattern, no test framework dependency) |
| Config file | none — each `test_*.py` is directly executable |
| Quick run command | `python3 server/test_<module>.py` (per-module, seconds) |
| Full suite command | `for f in server/test_*.py stub-server/test_poll_cycle.py; do python3 "$f" || exit 1; done` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| PLANE-01 | Departing flight (climbing, enrichment hit) renders flight number/airline/destination correctly | unit (pure function, fixture-driven — recorded real ADS-B record + recorded real adsbdb response, no live network call) | `python3 server/test_render.py` | ❌ Wave 0 |
| PLANE-01 | Enrichment miss on a departing flight renders the "Route unavailable" fallback per the resolved Open Question 3 | unit | `python3 server/test_render.py` | ❌ Wave 0 |
| PLANE-02 | Arriving flight (descending, enrichment hit) renders flight number/airline/origin correctly, silhouette mirrored nose-left | unit | `python3 server/test_render.py` | ❌ Wave 0 |
| PLANE-02 | D-03 threshold correctly classifies the real recorded arrival sequences from `adsb-test/samples/` (all 20 real tracked hexes) | unit, fixture-driven against real captured data | `python3 server/test_runway_config.py` | ❌ Wave 0 |
| PLANE-03 | Detection module correctly filters a multi-aircraft geofence snapshot and applies the (planner-resolved) selection rule from Open Question 1 | unit | `python3 server/test_plane_detection.py` | ❌ Wave 0 |
| PLANE-03 | Full pipeline end-to-end: extended `byos_server.py` serves a freshly rendered, correctly-sized (960,000-byte), correctly-hashed image over the real protocol contract | integration/smoke, extends the existing harness pattern | `python3 stub-server/test_poll_cycle.py` (extended) | ✅ exists (extend, don't replace) |
| All three | `image_url` in the `/device/v1/display` response uses `https://` in the Caddy-fronted deployment (Common Pitfall 2 regression guard) | integration/smoke, requires either a config flag or a Caddy-fronted staging instance | manual-only for local dev (no TLS locally); automated once deployed via a smoke curl against the real HTTPS endpoint | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant single `test_*.py` for the module just touched.
- **Per wave merge:** full suite (`server/test_*.py` + `stub-server/test_poll_cycle.py`).
- **Phase gate:** full suite green, plus a real end-to-end check against the deployed Hetzner VPS (real device poll or a curl-simulated poll over the real HTTPS endpoint) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `server/test_plane_detection.py` — covers PLANE-03 (geofence filtering + selection rule)
- [ ] `server/test_runway_config.py` — covers PLANE-01/PLANE-02 (D-03 thresholds against real recorded data)
- [ ] `server/test_enrich.py` — covers the enrichment cache/fallback logic (recorded fixtures for both hits and the real recorded `TVF*` misses)
- [ ] `server/test_render.py` — covers PLANE-01/PLANE-02 (render output correctness, both success and fallback paths)
- [ ] Extend `stub-server/test_poll_cycle.py` (or add a sibling) to assert the `https://` scheme fix from Common Pitfall 2
- [ ] `requirements.txt` — none exists yet; needed before any of the above can run (`Pillow==12.3.0`, `requests==2.34.2`)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|--------------------|
| V2 Authentication | yes | Already implemented in vendored `byos_server.py`: bearer-token issuance on `/device/v1/setup`, checked on `/device/v1/display` and `/device/v1/log`. No change needed this phase beyond keeping the setup secret out of git (already the established pattern) |
| V3 Session Management | partial | The issued bearer token is long-lived (no expiry logic in the vendored reference) — this matches flightportrait's own reference design and is not a regression introduced this phase; not re-scoped here |
| V4 Access Control | yes | Endpoint-level bearer check already present and unmodified; no new endpoints introduced this phase |
| V5 Input Validation | yes | New code this phase (aggregator response parsing, adsbdb response parsing) must validate types before use — follow `query_aggregator.py`'s existing pattern of explicit `isinstance()` checks and defaulting to "skip/don't claim" rather than raising on malformed/missing fields from either external API |
| V6 Cryptography | yes (delegated) | TLS is Caddy's responsibility (Let's Encrypt-issued certs, automatic renewal) — never hand-roll certificate handling in the Python server itself |
| V7 Error Handling & Logging | yes | `byos_server.py`'s existing `log_telemetry()` already avoids logging secrets (bearer tokens are never printed); new code (enrichment/render pipeline logs) must maintain this — never log the full bearer token or the BYOS setup secret to stdout/journald |
| V9 Communication Security | yes (new this phase) | DEVICE-03 requires HTTPS; Phase 1's stub deliberately allowed plain HTTP for a LAN-only dev target. This phase must close that gap: Caddy terminates TLS, and Common Pitfall 2's fix ensures the served `image_url` doesn't silently downgrade to `http://` |
| V12 File & Resource Handling | yes | The rendered `panel.bin` must be written atomically (`os.replace()`, same tmp+rename pattern already used by `byos_server.py`'s own `save_state()`) so the HTTP server never serves a partially-written file mid-render; the served image path is a fixed server-side constant, never derived from any request input |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Enrichment/aggregator API returning malformed, oversized, or unexpectedly-shaped JSON | Tampering / Denial of Service | Explicit type checks before use (V5 above), a `timeout=` on every `requests` call, and treating any parse failure as an enrichment/detection miss (falls back gracefully per D-04/UI-SPEC) rather than crashing the render loop |
| Third-party API outage (adsb.fi, airplanes.live, or adsbdb.com all down simultaneously) | Denial of Service (external) | The systemd timer's poll cycle simply fails to update `panel.bin` that cycle and the previous file keeps being served — no crash-loop risk since the render loop and the HTTP server are decoupled processes (Architecture Patterns) |
| `image_url` scheme downgrade (Common Pitfall 2) | Information Disclosure (device telemetry headers sent in the clear on the plaintext image fetch) | Fix the hardcoded scheme as documented in Common Pitfalls / V9 above |
| Secrets (Hetzner API token, adsbdb usage if ever keyed, BYOS setup secret) committed to git | Information Disclosure | Same discipline as `firmware/main/secrets.h`: a gitignored env file on the VPS, loaded via systemd's `EnvironmentFile=`, never committed; verify with `git status --porcelain` before any commit touching deployment config, matching Phase 1's own acceptance-criteria pattern |

## Sources

### Primary (HIGH confidence — direct tool verification this session)
- `api.adsbdb.com/v0/callsign/{callsign}` — live HTTPS queries against all 38 distinct real callsigns from `adsb-test/samples/*.jsonl` (20 hits, 18 misses; response shapes captured directly)
- `hexdb.io/api/v1/route/icao/{callsign}` and `hexdb.io/api/v1/airport/icao/{icao}` — live HTTPS queries confirming complementary-but-not-superset coverage vs. adsbdb.com
- Local Pillow 11.3.0 experiments (this session): `"P"`-mode text rendering (zero AA artifacts, confirmed via `Image.getcolors()`), mask resize+threshold+paste pipeline (159 gray levels → 2 after threshold)
- PyPI JSON API (`pypi.org/pypi/{package}/json`) for Pillow, fastapi, uvicorn, requests, apscheduler, python-dotenv, cairosvg, gunicorn, pydantic — current versions and publish dates
- Direct `grep`/`Read` of this repository's own files: `adsb-test/query_aggregator.py`, `adsb-test/RESULTS.md`, `adsb-test/runway3.json`, `adsb-test/samples/*.jsonl` (real vertical-rate/altitude sequences), `stub-server/byos_server.py`, `stub-server/VENDOR.md`, `stub-server/make_test_panel.py`, `firmware/main/api_client.c` (confirming both `http://`/`https://` are accepted by firmware and locating the exact `INK_API_BASE` integration point)

### Secondary (MEDIUM confidence)
- GitHub `mrjackwills/adsbdb` README (fetched this session) — API endpoint documentation, self-hosting option, data-attribution terms
- Web search: Hetzner Cloud Ubuntu image availability (24.04 LTS confirmed current/default, 26.04 also available)
- Web search: Caddy automatic HTTPS + nip.io HTTP-01 challenge pattern for TLS without owning a domain

### Tertiary (LOW confidence)
- `hexdb.io`'s informally-stated "1000 requests / 5 minutes" rate limit (sourced from a community forum post found via web search, not an official docs page) — not depended on for this phase's primary-provider recommendation (adsbdb.com), only mentioned as a deferred-alternative's characteristic

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified directly against PyPI's JSON API this session; package legitimacy cross-checked and dispositioned despite tool-reported SUS artifacts
- Enrichment API coverage: HIGH — measured directly against real production traffic data (38/38 real callsigns tested live), not estimated or assumed
- Render pipeline (indexed-canvas approach): HIGH — verified via executable experiments in this session with inspectable pixel-level output, not just documentation reading
- Runway-configuration thresholds (D-03): MEDIUM — descent-side thresholds are well-evidenced by real data; climb-side (departure) thresholds are derived by symmetry, not independently observed (see Open Question 2)
- VPS provisioning specifics: MEDIUM — Caddy/systemd/Ubuntu-24.04 recommendations are standard, current, and cross-checked via web search, but not executed end-to-end against a real Hetzner instance in this research session
- Pitfalls: HIGH — all five pitfalls are either directly observed in this session's own tool calls (enrichment misses, gray-level counts, the hardcoded `http://` bug found by reading the actual vendored file) or directly inherited from Phase 1's own documented findings (the 06/24 geofence overlap)

**Research date:** 2026-08-08
**Valid until:** 2026-09-07 (30 days) for the VPS/Caddy/Pillow-version guidance; the enrichment API coverage measurement (52.6%) should be treated as a point-in-time snapshot of adsbdb's crowdsourced database and may drift — if Phase 2 execution happens more than a few weeks after this research, consider re-running the same live-callsign-coverage check against a fresh sample before finalizing the fallback-frequency expectations in QA planning.
