# Phase 2: Plane View — End-to-End Slice - Pattern Map

**Mapped:** 2026-08-08
**Files analyzed:** 13 (new) + 2 (modified)
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `server/plane/detect.py` | service | request-response (polling) | `adsb-test/query_aggregator.py` | exact (direct adaptation, same geofence/provider logic) |
| `server/plane/runway_config.py` | utility (transform) | transform | `adsb-test/query_aggregator.py` (`filter_in_geofence`'s defensive-typing style) | role-match |
| `server/plane/enrich.py` | service | request-response + cache | `adsb-test/query_aggregator.py` (`query_provider`/error-handling shape) | role-match |
| `server/plane/render.py` | utility (transform) | transform (raster render) | `stub-server/make_test_panel.py` | exact (same byte-packing contract, same module) |
| `server/poll_loop.py` | controller (scheduled entrypoint) | batch / event-driven | `adsb-test/sample_window.py` (orchestration script calling `query_aggregator.py` on a loop — not read in full but same shape per RESEARCH.md structure) + `stub-server/byos_server.py` (`save_state` atomic-write pattern) | role-match |
| `server/test_plane_detection.py` | test | — | `stub-server/test_poll_cycle.py` | exact (project's stdlib-only harness convention) |
| `server/test_runway_config.py` | test | — | `stub-server/test_poll_cycle.py` | exact |
| `server/test_enrich.py` | test | — | `stub-server/test_poll_cycle.py` | exact |
| `server/test_render.py` | test | — | `stub-server/test_poll_cycle.py` | exact |
| `server/assets/icons/VENDOR.md` | config (provenance doc) | — | `stub-server/VENDOR.md` | exact |
| `server/assets/fonts/VENDOR.md` | config (provenance doc) | — | `stub-server/VENDOR.md` | exact |
| `server/requirements.txt` | config | — | none exists yet — no analog | n/a |
| Caddy config / systemd unit files (VPS provisioning) | config | — | none exists yet — no analog | n/a |
| `stub-server/byos_server.py` (modified: `https://` scheme fix) | controller | request-response | itself (in-place edit, one-line deviation) | exact |
| `stub-server/VENDOR.md` (modified: log the scheme-fix deviation) | config (provenance doc) | — | itself (in-place edit, following its own "Local modifications" convention) | exact |

## Pattern Assignments

### `server/plane/detect.py` (service, request-response/polling)

**Analog:** `adsb-test/query_aggregator.py` (read in full — 220 lines, stdlib `urllib.request`)

**Imports pattern** (lines 19-25):
```python
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
```
Phase 2's `detect.py` should switch `urllib.request` → `requests` per RESEARCH.md's Standard Stack decision (the real server, unlike the Phase 1 spike script, adopts `requests` for timeout/retry ergonomics) — this is a deliberate, documented deviation from the analog, not a straight copy.

**User-Agent / identification pattern** (lines 27-33):
```python
USER_AGENT = (
    "ink-frame-adsb-validation/0.1 "
    "(hobby project, Phase 1 ADS-B-viability spike; "
    "see adsb-test/README.md for what this traffic is)"
)
```
Copy this identification discipline verbatim (update project-phase wording) — both aggregators are unauthenticated public APIs and this project already established the convention of self-identifying via `User-Agent`.

**Provider table + rate-limit constant pattern** (lines 39-52):
```python
PROVIDERS = {
    "adsbfi": {
        "url_template": "https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}",
        "aircraft_key": "aircraft",
    },
    "airplaneslive": {
        "url_template": "https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}",
        "aircraft_key": "ac",
    },
}
MIN_SECONDS_BETWEEN_CALLS = 1.1
```
Copy directly — both aggregators' endpoint shapes and the 1 req/s rate-limit discipline are already validated live in Phase 1 (RESULTS.md).

**Core geofence-filter pattern with defensive typing** (lines 79-116, `filter_in_geofence`):
```python
def filter_in_geofence(aircraft, geofence):
    bbox = geofence["bbox"]
    ceiling_ft = geofence["alt_ceiling_ft"]
    matched = []
    for ac in aircraft:
        lat = ac.get("lat")
        lon = ac.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue  # no position report this update - can't geofence it
        if not (bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lon_min"] <= lon <= bbox["lon_max"]):
            continue
        alt_baro = ac.get("alt_baro")
        on_ground = isinstance(alt_baro, str)
        if on_ground:
            below_ceiling = True
        elif isinstance(alt_baro, (int, float)):
            below_ceiling = alt_baro <= ceiling_ft
        else:
            below_ceiling = False  # unknown/missing altitude - don't claim it's below ceiling
        tagged = dict(ac)
        tagged["in_bbox"] = True
        tagged["on_ground"] = on_ground
        tagged["below_ceiling"] = below_ceiling
        matched.append(tagged)
    return matched
```
This is the direct starting point for `detect.py`'s geofence filter — copy the "skip/don't-claim rather than raise on malformed field" discipline exactly (this is also the ASVS V5 input-validation pattern RESEARCH.md calls for). Extend with the multi-aircraft selection rule (RESEARCH.md Open Question 1) as an additional filtering/sorting step after `filter_in_geofence`.

**Error-isolation pattern (one provider down ≠ abort)** (lines 139-153):
```python
for i, name in enumerate(providers):
    if i > 0:
        time.sleep(MIN_SECONDS_BETWEEN_CALLS)
    try:
        aircraft = query_provider(name, center["lat"], center["lon"], radius_nm, timeout)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        results[name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
        continue
```
Copy this per-provider isolation pattern into `detect.py`; with `requests` the equivalent except clause is `(requests.RequestException, ValueError)`.

**Geofence config file:** `adsb-test/runway3.json` — reuse as-is (already sourced/validated in Phase 1, per CONTEXT.md's Reusable Assets).

---

### `server/plane/runway_config.py` (utility, transform)

**Analog:** same file, same defensive-typing convention as above (no dedicated inference module exists yet in the codebase — this is genuinely new logic per D-03).

**Pattern to copy:** the "skip/hold-last-state rather than guess" discipline demonstrated in `filter_in_geofence`'s altitude-typing branch, applied to RESEARCH.md's Pitfall 3 deadband:
```python
# Pattern derived from RESEARCH.md Pitfall 3 / Common Pitfalls, using the
# same "explicit isinstance + graceful fallback" style as query_aggregator.py
CLIMB_THRESHOLD_FPM = 200
DESCEND_THRESHOLD_FPM = -200

def infer_runway_config(vertical_rate, last_confirmed_state):
    if not isinstance(vertical_rate, (int, float)):
        return last_confirmed_state  # unknown reading - don't flip state
    if vertical_rate >= CLIMB_THRESHOLD_FPM:
        return "departing"
    if vertical_rate <= DESCEND_THRESHOLD_FPM:
        return "arriving"
    return last_confirmed_state  # inside the deadband - hold last state
```

---

### `server/plane/enrich.py` (service, request-response + in-process cache)

**Analog:** `adsb-test/query_aggregator.py`'s `query_provider` (lines 62-76) for the HTTP-call shape; no existing cache pattern in the codebase (new logic).

**Core request pattern to adapt** (mirrors lines 62-76, but targets a single endpoint with `requests` instead of `urllib`):
```python
# Analog: query_aggregator.py's query_provider() — same "raise on failure,
# let caller catch per-call" contract, same explicit timeout requirement.
import requests

ADSBDB_URL = "https://api.adsbdb.com/v0/callsign/{callsign}"

def lookup_route(callsign, timeout=10.0):
    resp = requests.get(ADSBDB_URL.format(callsign=callsign),
                         headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if resp.status_code == 404:
        return None  # "Route unavailable" fallback per UI-SPEC
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", {}).get("flightroute")
```
**Cache-first pattern (new, per RESEARCH.md Architecture Patterns / Anti-Patterns):** keyed by callsign, in-process dict, never re-queried once cached (avoid the "re-query every poll" anti-pattern explicitly called out in RESEARCH.md).

**Error handling:** follow the same "malformed/missing → treat as enrichment miss, never crash the render loop" discipline as `filter_in_geofence`'s typing checks (ASVS V5/V7 — see Security Domain in RESEARCH.md).

---

### `server/plane/render.py` (utility, transform/raster render)

**Analog:** `stub-server/make_test_panel.py` (read in full — 121 lines)

**Constants/header pattern** (lines 37-42):
```python
WIDTH = 1200
HEIGHT = 1600
ROW_BYTES = WIDTH // 2  # 600
IMAGE_BYTES = ROW_BYTES * HEIGHT  # 960000

BLACK, WHITE, YELLOW, RED, BLUE, GREEN = 0x0, 0x1, 0x2, 0x3, 0x5, 0x6
```
Copy these constants verbatim — this is the exact protocol contract `render.py`'s final packing step must produce.

**Deterministic-output discipline** (docstring, lines 26-27): "The same pattern always produces identical bytes... this generator has no randomness." Apply the same discipline to `render.py`'s fixture-driven tests (RESEARCH.md's `test_render.py` plan uses recorded fixtures, not live network/random data, for exactly this reason).

**Byte-packing pattern (final step of the pipeline)** — combine with RESEARCH.md's own verified Pattern 3 (`pack_panel`, already fully specified in 02-RESEARCH.md's Architecture Patterns section) — do not re-derive; copy that function directly as `render.py`'s last step, reusing `make_test_panel.py`'s `WIDTH`/`HEIGHT`/`ROW_BYTES`/`IMAGE_BYTES` constants and nibble-code assignments so the two files share one source of truth for the format (consider importing the constants from `make_test_panel.py` rather than duplicating them, or extracting them to a shared `server/panel_format.py` if that avoids a `stub-server` → `server` import direction that feels backwards — planner's discretion).

**Rendering approach itself:** new code, no direct analog for Pillow "P"-mode drawing exists in the codebase yet — use RESEARCH.md's own verified Pattern 1 (indexed-canvas direct-index drawing) and Pattern 2 (resize-then-threshold mask compositing) as the primary source; both are already-executed, pixel-verified code in 02-RESEARCH.md's Architecture Patterns section, more authoritative than any codebase analog for this specific new capability.

**CLI/argparse structure to mirror** (lines 101-121, `main()`):
```python
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pattern", choices=sorted(PATTERNS), default="palette")
    ap.add_argument("--out", required=True, help="output path for the generated .bin")
    args = ap.parse_args()
    data = PATTERNS[args.pattern]()
    if len(data) != IMAGE_BYTES:
        sys.exit("internal error: generated %d bytes, expected %d" % (len(data), IMAGE_BYTES))
    with open(args.out, "wb") as fh:
        fh.write(data)
    digest = hashlib.sha256(data).hexdigest()
    print("wrote %s (%d bytes, pattern=%s)" % (args.out, len(data), args.pattern))
    print("sha256 %s" % digest)
```
If `render.py` also needs a standalone CLI entrypoint (e.g. for manual QA against a fixture), mirror this structure: validate byte-length before writing, print the digest.

---

### `server/poll_loop.py` (controller, scheduled entrypoint / batch)

**Analog (orchestration structure):** no single file in the codebase already loops detect→enrich→render, but two analogs jointly cover this:
1. `stub-server/byos_server.py`'s `save_state`/`load_state` atomic-write pattern (lines 42-58):
```python
def state_path(state_dir):
    return os.path.join(state_dir, "byos_state.json")

def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))
```
Copy this exact tmp-write-then-`os.replace()` atomic-swap pattern for `poll_loop.py`'s `panel.bin` write (RESEARCH.md's Security Domain V12 explicitly calls for reusing this pattern) — never write the served file in place.

2. `adsb-test/query_aggregator.py`'s `run()` (lines 139-174) for the "call each stage, catch and isolate failures, keep going" orchestration shape — same principle applies across detect → runway_config → enrich → render stages: a failure in enrichment (RESEARCH.md's "Route unavailable" fallback) must not abort the render, and a failure in the whole poll cycle must not crash the process (RESEARCH.md's Known Threat Patterns: "previous file keeps being served").

**Scheduling:** systemd timer (not in-process loop) per RESEARCH.md's Don't Hand-Roll table — `poll_loop.py` is a oneshot script invoked by a systemd `.timer`/`.service` unit pair, no `while True: sleep()` daemon loop, no APScheduler.

---

### `server/test_*.py` (test files)

**Analog:** `stub-server/test_poll_cycle.py` (read lines 1-80 of 20,606 bytes — stdlib-only harness convention)

**Structure to copy** (docstring + module-level constants, lines 1-39):
```python
#!/usr/bin/env python3
"""<One-line purpose>.

Stdlib-only (...). <what it does>. Exits 0 only when every check below
passes; any failure (or exception - none is ever swallowed into a pass)
exits 1.

Usage:
    python3 server/test_<module>.py
"""
import ...

HERE = os.path.dirname(os.path.abspath(__file__))
...
```

**Assertion-helper pattern** (lines 42-80, `verify_panel_bytes`/`validate_display_response`):
```python
def verify_panel_bytes(buf, expected_hash):
    if len(buf) != IMAGE_BYTES:
        return False
    if expected_hash is None:
        return False
    expected_hex = expected_hash.split(":", 1)[-1] if ":" in expected_hash else expected_hash
    return hashlib.sha256(buf).hexdigest() == expected_hex
```
Each `server/test_*.py` should follow this shape: small pure-function `validate_*`/`verify_*` helpers returning booleans, aggregated by a `main()` that counts checks and exits 1 on any failure (project convention — no pytest, no test framework dependency, per RESEARCH.md's Validation Architecture / Test Framework table, which explicitly cites this file as the established convention).

**Fixture-driven, not live-network testing:** `test_runway_config.py`, `test_enrich.py`, `test_render.py` should use recorded fixtures (from `adsb-test/samples/*.jsonl` and captured adsbdb responses, per RESEARCH.md's Code Examples) rather than live calls — this mirrors `make_test_panel.py`'s "deterministic, no randomness" philosophy applied to test inputs.

---

### `server/assets/{icons,fonts}/VENDOR.md` (config, provenance doc)

**Analog:** `stub-server/VENDOR.md` (read in full — 79 lines)

**Structure to copy** (the whole file's shape, e.g. lines 1-14, 16-46):
```markdown
# <dir> — Vendor Provenance

## `<filename>`

- **Upstream repository/source:** <URL>
- **Pinned commit / retrieval date:** <hash or date>
- **Upstream path:** <path, if applicable>
- **Licence:** <license>. <attribution details if required>

### Local modifications

<numbered list of exactly what changed, or "None — copied byte-for-byte.">
```
Apply this exact structure for:
- `server/assets/icons/VENDOR.md` — document the freesvg.org/OpenClipart SVG ID 178507 source, CC0 license, retrieval date, and the vendoring + pre-rasterization step (per UI-SPEC's Design System section and RESEARCH.md's Don't Hand-Roll table).
- `server/assets/fonts/VENDOR.md` — document Inter (SIL OFL 1.1), Regular 400 + Bold 700, source URL, retrieval date.

---

### `stub-server/byos_server.py` (modified — `https://` scheme fix)

**Exact edit location** (lines 141-142, current code):
```python
return self.send_json(200, {
    "image_url": "http://%s/img/%s.bin" % (host, digest),
```
Per RESEARCH.md's Common Pitfall 2 (binding), change to:
```python
return self.send_json(200, {
    "image_url": "https://%s/img/%s.bin" % (host, digest),
```
This is a one-line, deliberate deviation — record it in `stub-server/VENDOR.md`'s "Local modifications" list (item 2, following the existing numbered-list convention shown in that file's `--state-dir` entry, lines 22-37) rather than leaving it undocumented.

---

## Shared Patterns

### Defensive input validation (never raise on malformed external-API data)
**Source:** `adsb-test/query_aggregator.py`, `filter_in_geofence` (lines 94-116) and `run` (lines 139-153)
**Apply to:** `detect.py`, `enrich.py`, `runway_config.py` — every module parsing adsb.fi/airplanes.live/adsbdb.com responses. Explicit `isinstance()` checks before use; default to "skip/don't claim" rather than raising; catch network/JSON errors per-call and isolate failures so one provider/lookup being down never aborts the whole poll cycle.

### Atomic file writes for served state
**Source:** `stub-server/byos_server.py`, `save_state()` (lines 54-58)
**Apply to:** `poll_loop.py`'s `panel.bin` write — write to a `.tmp` path, then `os.replace()`. Never write the served file path directly (RESEARCH.md's V12 File & Resource Handling requirement).

### Vendoring provenance discipline
**Source:** `stub-server/VENDOR.md` (whole file)
**Apply to:** `server/assets/icons/VENDOR.md`, `server/assets/fonts/VENDOR.md`, and the `stub-server/VENDOR.md` update itself for the scheme-fix deviation — every non-original asset or file gets a provenance entry: upstream source, license, retrieval date/pinned commit, and an explicit "Local modifications" list (even if "none").

### stdlib-only, no-pytest test harness convention
**Source:** `stub-server/test_poll_cycle.py` (whole file structure)
**Apply to:** all four new `server/test_*.py` files — docstring stating stdlib-only deps and the "exits 0 only if every check passes, no exception ever swallowed" contract; small boolean-returning `validate_*` helper functions; a `main()` that runs checks and reports pass/fail counts.

### Explicit self-identification on outbound HTTP calls
**Source:** `adsb-test/query_aggregator.py`, `USER_AGENT` constant (lines 27-33)
**Apply to:** `detect.py` (adsb.fi/airplanes.live calls) and `enrich.py` (adsbdb.com calls) — both are free, unauthenticated public APIs; identify this project's traffic honestly, updating the version/phase wording.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `server/requirements.txt` | config | — | No `requirements.txt` exists anywhere in the repo yet (RESEARCH.md confirms this explicitly: "none exists yet — needed before any of the above can run"). Use RESEARCH.md's Standard Stack section directly: `Pillow==12.3.0`, `requests==2.34.2`. |
| Systemd timer/service unit files, Caddy config, Hetzner provisioning scripts | config (infra) | — | No infra-as-code exists yet in this repo (Phase 1 was firmware + a local Python spike only). Use RESEARCH.md's Architecture Patterns diagram and Code Examples (Caddy nip.io snippet) as the primary source instead of a codebase analog. |
| Pillow "P"-mode direct-index drawing + resize/threshold masking (the render technique itself, as opposed to the packing step) | — | transform | No existing codebase file does any Pillow rendering. RESEARCH.md's own Pattern 1/Pattern 2 (Architecture Patterns section) are pixel-verified, executable-tested code from this session's research — treat those as the primary and sufficient source for this specific new capability. |

## Metadata

**Analog search scope:** `stub-server/`, `adsb-test/`, `firmware/main/` (for the `INK_API_BASE` integration point only — no firmware code changes this phase)
**Files scanned:** `stub-server/byos_server.py` (194 lines, full read), `stub-server/make_test_panel.py` (121 lines, full read), `stub-server/test_poll_cycle.py` (lines 1-80 of 20,606 bytes, targeted), `stub-server/VENDOR.md` (79 lines, full read), `adsb-test/query_aggregator.py` (220 lines, full read), `firmware/main/api_client.c`/`secrets.h` (grepped for `INK_API_BASE`)
**Pattern extraction date:** 2026-08-08
