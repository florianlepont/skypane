# Open Research Questions

Questions surfaced during exploration that need deeper investigation before they can inform a plan. Append-only; move an entry to a note or seed once answered.

---

## Can the user's Freebox (Delta/Pop) run `readsb`/`dump1090-fa` directly?

**Raised:** 2026-08-27, during the local-RTL-SDR-backup explore session (see `.planning/seeds/local-rtl-sdr-adsb-backup.md`).

**Why it matters:** If local RTL-SDR reception is ever pursued as a backup ADS-B source, the decoder needs an always-on host near Orly. The user already owns a Freebox and a Raspberry Pi, and would prefer to avoid dedicating either if there's a lower-friction option. Freebox Delta/Pop devices are known to support running apps/VMs via Freebox OS on at least some models/firmware versions, which could mean the Freebox itself (already always-on as the home router) could host the ADS-B decoder with an attached RTL-SDR USB dongle — avoiding a separate Raspberry Pi entirely.

**Not yet verified:**
- Whether the user's specific Freebox model/firmware actually supports installing arbitrary Docker containers or VMs (vs. only Free's own curated app store).
- Whether USB passthrough to an attached RTL-SDR dongle is possible from within that environment.
- Whether `readsb`/`dump1090-fa` (or a compatible ARM/x86 build matching the Freebox's CPU architecture) can actually be installed and run there.
- Performance/thermal headroom on a device that's also doing router/NAS duty.

**How to resolve:** Check Free's official Freebox OS documentation for the user's exact model, and/or community forums (e.g. Freebox-focused tech forums) for existing reports of running dump1090/readsb on a Freebox.
