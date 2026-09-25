# Phase 42: Remote firmware update over the air (OTA) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-25
**Phase:** 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
**Areas discussed:** Trigger, Authenticity, When to apply, Release pipeline
**Language:** the session ran in French; options are translated here.

---

## Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Companion button | Release is available; the operator clicks Install | ✓ |
| Automatic on deploy | Every deployed release goes to the frame at its next wake | |
| Automatic + pause switch | Automatic by default, with a pause toggle | |

**Where firmware management lives.** The first question offered a set of Health-page contents. The developer answered with a question instead: "why the Health tab? why not an Update tab under Advanced?" The follow-up question offered three places:

| Option | Description | Selected |
|--------|-------------|----------|
| New "Update" tab in Advanced | Third Advanced entry; 7 entries in the mobile tab bar | ✓ |
| Section in Device | A "Firmware" card on the Device page | |
| Section in Health | Next to battery and last check-in | |

**Page contents (multi-select):** running version ✓, update state ✓, rollback warning ✓, version history ✓.

| Question | Options | Choice |
|----------|---------|--------|
| Cancel before next wake? | Yes, Cancel button / No | Yes, Cancel button |
| Voluntary downgrade? | Any published version / Latest only | Any published version |
| Push notification? | Success and failure / Failure only / None | Success and failure |
| Release notes? | Version+date+commits / Version+date / Hand-written | Version+date+commits |
| Confirm before install? | Confirmation dialog / No, Cancel is enough (recommended) | Confirmation dialog |

## Authenticity

| Question | Options | Choice |
|----------|---------|--------|
| Protection level | Signed images, no eFuse / HTTPS + SHA-256 only | Signed images |
| Signing key location | GitHub Actions secret / Offline on the Mac / N/A | GitHub Actions secret |
| Key backup | Encrypted offline copy / No copy | Encrypted offline copy |
| Version floor | Software floor, server and device / Anything allowed | Software floor |

## When to apply

| Question | Options | Choice |
|----------|---------|--------|
| Battery threshold | Outside battery-low (3500/3600 mV) / Higher, e.g. 50 % / Outside critical only | Outside battery-low |
| Quiet hours / display off | Wait for the end (recommended) / Display-off OK, quiet hours no / Next wake regardless | Next wake regardless |
| Screen during update | Nothing changes (recommended) / "Updating…" screen | "Updating…" screen |
| That screen at night / display off | No, hold screen stays (recommended) / Yes, always | Yes, always |
| Attempts before failure | 3 / 1 / Unlimited | 3 |

**Notes:** the developer overrode the recommendation three times in this area. Each time they chose visibility, and an update that is not held back by quiet hours or display off, over saving energy.

## Release pipeline

| Question | Options | Choice |
|----------|---------|--------|
| What creates a release | Git tag / Every merge touching firmware/ / Manual workflow | Git tag |
| Transport to the VPS | Existing deploy job into the state dir / Upload from companion | Existing deploy job |
| Retention | All / Last 10 | All |
| Let's Encrypt chain guard | CI check / Capability only | CI check |

## Claude's Discretion

- Offer wire format.
- How OTA progress and outcome are reported, and where they are stored.
- Firmware URL layout.
- When the download runs within a wake, and how the wake deadline is extended.
- Whether the "Updating…" screen is drawn on the device or served as an image.
- Where the release registry lives.

## Deferred Ideas

- Per-device targeting and a multi-frame UI.
- An automatic rollout mode.
- A separate CA-bundle update channel.
