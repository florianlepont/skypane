# Phase 11: Web-configurable wake interval - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-04
**Phase:** 11-web-configurable-wake-interval
**Areas discussed:** Delivery mechanism, Validation bounds, Base-value layering with Phase 10, Field naming and UI presentation, Apply-timing convention

> **This was a fully autonomous `--auto` pass (mode: yolo).** No AskUserQuestion
> calls were made — every "Selected" below is Claude's own recommended-default
> choice, not a developer confirmation. Flag this log for a developer read
> before treating Phase 11 as truly locked, especially D-02 (the min/max
> bounds), which was not discussed live and is explicitly noted as such in
> CONTEXT.md.

---

## Delivery mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Poll-response delivery | Server returns the current wake interval in the `/display` response's `sleep_s`; device honors it as its next sleep duration; no service restart | ✓ |
| Service restart | Config write triggers a server-side restart of `skypane-byos.service` with the new `--sleep` value | |

**Selected (auto):** Poll-response delivery (recommended option — SEED-002's own explicitly stated preference).
**Notes:** Matches CFG-01/CFG-12's existing live-config-read pattern; avoids service-restart plumbing entirely; needs no new protocol field since `sleep_s` already exists in the response.

---

## Validation bounds

| Option | Description | Selected |
|--------|-------------|----------|
| min 10s / max 3600s (1h) | Floor well above any risk of hammering ADS-B aggregators; cap staleness at one hour worst case | ✓ |
| Other bounds | Not explored — no alternative pair was generated for comparison | |

**Selected (auto):** min 10s, max 3600s.
**Notes:** **Not discussed live with the developer.** Flagged explicitly in CONTEXT.md for confirmation — the developer may want a tighter max given the device's whole purpose is near-real-time departure info.

---

## Base-value layering with Phase 10 (quiet hours)

| Option | Description | Selected |
|--------|-------------|----------|
| New config field becomes the base value | `--sleep` CLI arg becomes only the bootstrap/fallback default when `device_config.json` doesn't have the field yet | ✓ |
| Independent layering | Some other mechanism keeps the CLI arg authoritative and layers the web-configured value differently | |

**Selected (auto):** New config field becomes the base value (recommended option).
**Notes:** Matches every other `device_config.py` field's own "degrade to documented default when absent" contract. Preserves Phase 10's `quiet_hours_sleep_s(base_sleep_s, ...)` call shape unchanged — only what gets passed as `base_sleep_s` changes.

---

## Field naming and UI presentation

| Option | Description | Selected |
|--------|-------------|----------|
| `wake_interval_s`, plain numeric input | SEED-002's own suggested field name; first plain `<input type="number">` anywhere in the companion app | ✓ |
| Alternative naming/UI shape | Not explored | |

**Selected (auto):** `wake_interval_s`, numeric input labeled "Wake interval (seconds)".
**Notes:** This is a genuinely new UI pattern (first numeric input in the app) — flagged in CONTEXT.md for a real-preview check before treating the visual design as final, same discipline Phase 10 used for its own first `type="time"` input.

---

## Apply-timing convention

| Option | Description | Selected |
|--------|-------------|----------|
| Same "applies on next scheduled poll" convention | Matches every other Settings field (`06-CONTEXT.md` D-06/D-07) | ✓ |
| A faster-apply mechanism | Some new mechanism to apply the change sooner than the next poll | |

**Selected (auto):** Same existing convention, no new mechanism.
**Notes:** The device already re-reads `sleep_s` fresh on every poll — no new latency-reduction mechanism needed or requested.

---

## Claude's Discretion

- Exact validation error copy for an out-of-bounds/non-numeric submitted value.
- Exact companion-page form layout/spacing for the new field.
- Whether the field pre-fills with the current effective interval (assumed yes).
- Exact wording of the trade-off caption text under the field.

## Deferred Ideas

- A per-time-of-day variable wake interval (faster daytime, slower overnight) — out of scope; Phase 10's quiet-hours window already covers the "pause entirely overnight" case.
