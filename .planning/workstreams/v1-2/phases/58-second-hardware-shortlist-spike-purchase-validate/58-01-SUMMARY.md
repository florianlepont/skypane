---
phase: 58-second-hardware-shortlist-spike-purchase-validate
plan: 01
subsystem: hardware
tags: [second-hardware, shortlist, e-ink, spectra-6, costing]
requires: []
provides:
  - hardware/SECOND-HARDWARE.md costed, dated, sourced shortlist (HW2-01 first half)
affects: [58-02 spike]
key-files:
  created: [hardware/SECOND-HARDWARE.md]
  modified: []
key-decisions:
  - "VAT method mirrors BOM.md (Seeed/Waveshare prices treated as ex-VAT, +20%); unconfirmed on the pages"
  - "Ranking on the at-least landed cost (delivery excluded, delivery is checkout-only everywhere)"
requirements-completed: [HW2-01]
duration: ~1h
completed: 2026-11-01
---

# Phase 58 Plan 01: Second-hardware costed shortlist Summary

Ranked shortlist of five 7.3" Spectra 6 (800x480) candidates built from product pages opened on 2026-11-01; Seeed EE04 is cheapest at 78.73 EUR TTC (delivery excluded), the only one that can reach the 100 EUR TTC target.

## Result (landed cost TTC, delivery excluded, VAT +20% assumed)

1. Seeed EE04 (board 9.82 + panel 42.87 HT) plus battery and cable: 78.73 (98.73 with BOM's delivery estimates)
2. Waveshare ESP32-S3-PhotoPainter with battery, 75.40 HT: 90.48 (105.48 with estimate, exceeds)
3. Waveshare raw (E) panel 53.85 + ESP32 driver board 13.46, plus battery and cable: at least 96.27
4. Waveshare HAT (E) 71.81 HT, no MCU priced: at least 101.67, exceeds
5. Seeed reTerminal E1002, 88.45 HT: 106.14, exceeds
- Good Display GDEP073E01: unranked, panel price unconfirmed; extras alone 27.28.

## Deviations from Plan

**1. [Rule 3 - Blocking] WebFetch unavailable in this session.** Pages were read with plain GET requests (curl through the agent proxy) and the data embedded in the page HTML (bundle price/stock JSON, structured data). GET only, no cart, login or order call. A browser-user-agent retry on good-display.com was refused by the permission system and not pursued.

## Findings against earlier assumptions

- Kubii 3000 mAh battery (BOM.md pick) now shows "Rupture de stock".
- Waveshare structured data labels USD amounts as EUR.

## Unconfirmed (details in the file)

Delivery cost and time to France on all shops, VAT treatment of displayed prices, controller on all pages, Good Display page (404) and reseller pages (bot challenges), EE04 FPC pin count for 7.3", Waveshare driver board charger/compatibility, PhotoPainter battery price, replacement battery.

## Verification

Plan verify commands pass; only `hardware/SECOND-HARDWARE.md` is new; `stub-server/test_phase47_freeze.py` 21 passed. Nothing purchased, ordered, carted or paid.
