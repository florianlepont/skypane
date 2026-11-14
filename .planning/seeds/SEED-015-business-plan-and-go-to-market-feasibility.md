---
id: SEED-015
status: dormant
planted: 2026-11-14
planted_during: "v1.2, owner's roadmap discussion (repository visibility, licensing and data sources questions of 2026-11-13)"
trigger_when: "Future milestone, no version number yet — the owner plans a business plan and a technical feasibility study for a market launch after v1.4; surface it when the owner decides to prepare a go-to-market study, or earlier if a licensing or data-source decision cannot wait."
target_milestone: future
scope: large
---

# SEED-015: Business plan and technical feasibility of a market launch

## Why This Matters

The owner intends to use SkyPane professionally in the end. Several things found
in the repository during the discussion of 2026-11-13 show that this is not only
a matter of building more features: some of them could block a launch if they
are not looked at early. The deliverables of this milestone are documents and
decisions (a business plan, a technical feasibility study and a go or no-go),
not code.

## When to Surface

**Trigger:** after v1.3 (photo mode) and v1.4 (enclosure), or sooner if one of
the "decide early" items below needs an answer before then.

## Scope Estimate

**Large, and mostly research and decisions.** Starting list, to be checked with
the right experts, not taken as legal or regulatory advice:

**Decide early (they can block or reshape the plan)**
- **Flight data licences.** The sources used today are for personal,
  non-commercial use (adsb.fi), may require an API key in future (adsb.lol), or
  require a commercial licence for any revenue use (airplanes.live); adsbdb
  forbids copying its route data into another database. See `COMPLIANCE.md`. A
  commercial source, and its price per frame, has to be found and costed.
- **Licence of the code.** The repository is under AGPL-3.0 with a commercial
  licence on offer. The firmware and `stub-server/byos_server.py` are
  Apache-2.0 (derived from FlightPortrait, YODE PTE LTD) and cannot be
  relicensed; the aircraft illustrations are AI-generated and not under AGPL; a
  large share of the code was written with an AI assistant, and the copyright
  status of such content is uncertain in several countries. A lawyer in
  intellectual property should look at this before any commercial step.
- **Repository visibility and tooling.** On the free GitHub plan, a private
  repository loses the approval step before a production deploy and has a
  monthly limit of CI minutes (GitHub documentation, checked 2026-11-13). Where
  the commercial work lives, and on what hosting and plan, has to be decided.

**Technical feasibility**
- **Bill of materials and cost at volume:** panel price at scale, a bare ESP32
  module and a custom board instead of the development board, the enclosure
  (SEED-014), the battery, the packaging.
- **Regulation for an object sold in Europe with a radio and a battery:** CE
  marking for radio equipment, rules for lithium batteries, electronic waste and
  hazardous-substances rules, product safety, packaging.
- **Production and logistics:** supply and lead times of the panels, assembly,
  provisioning each frame (flash and enrolment), warranty and returns.
- **Service side:** capacity of the server for many frames, the cost of
  authentication at scale, backup and support, and what is promised to a
  customer if a data source stops.
- **Privacy:** accounts and, with photo mode (SEED-013), customers' photos: the
  rule that the administrator never sees them, retention, deletion, the
  European data protection rules.

**Business plan**
- Target customers and use cases (aviation enthusiasts, people living near an
  airport, gift market, photo frame users), pricing and subscription model,
  channels, competitors (including FlightPortrait, the upstream of the
  firmware: its positioning and its trademark), margins, a financing need and a
  go or no-go with the conditions.

## Breadcrumbs

- `COMPLIANCE.md` (terms of every data source)
- `README.md` (licence section and commercial licence offer), `LICENSE`, `NOTICE`
- `firmware/VENDOR.md`, `firmware/LICENSE`, `firmware/NOTICE` (Apache-2.0 upstream)
- `hardware/BOM.md`, `hardware/SECOND-HARDWARE.md`, `hardware/BATTERY-MODEL.md`
- `.planning/seeds/SEED-013-photo-display-mode.md`, `SEED-014-enclosure-for-the-back-of-the-frame.md`
- `.planning/notes/photo-mode-concept.md` (privacy and collection licence decisions)

## Notes

Treat every legal and regulatory point above as a question for a professional,
not as a conclusion. The numbers (plans, limits) come from public pages checked
on the dates given and must be rechecked at the time of the study.
