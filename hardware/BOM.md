# Ink Frame — Phase 1 Bill of Materials

This BOM covers only what Phase 1 needs on the bench: no enclosure, no solar, no RTL-SDR.

## Required Now

| Item | SKU / Model | Vendor | URL | Unit price (excl. VAT) | Qty | Subtotal |
|---|---|---|---|---|---|---|
| XIAO ePaper DIY Kit EE02 — **bundle** (driver board + panel, both ordered together) | Bundle SKU `E26010501` (board `E-6639`, panel `E-6569`) | Seeed Studio (official, EU store) | https://www.seeedstudio.com/XIAO-ePaper-DIY-Kit-EE02-for-13-3-Spectratm-6-E-Ink.html | €142.98 (board €12.99 + panel €129.99, EUR store, price-lookup date 2026-08-04) | 1 | €142.98 |
| — alternative pricing reference (USD store, same page, same date) | same | same | same | $163.90 (board $14.90 + panel $149.00) | — | for cross-check only |
| LiPo battery pack, 3.7V, JST-PH 2.0mm 2-pin, protected | "Batterie 3000mAh Li-Po" | Kubii (French EU distributor) | https://www.kubii.com/fr/alimentations-protections/4913-batterie-3000mah-li-po-3272496324541.html | €7.13 HT (€8.55 TTC incl. 20% French VAT), looked up 2026-08-04 | 1 | €7.13 (excl. VAT) |
| USB-C data cable (USB 3, carries data — not power-only) | "Cable USB 3 Type-C vers USB-A" | Kubii (French EU distributor) | https://www.kubii.com/fr/hub-cables-adaptateurs/4093-cable-usb-3-type-c-vers-usb-a-3272496315709.html | €5.79 HT (€6.95 TTC incl. 20% French VAT), looked up 2026-08-04 | 1 | €5.79 (excl. VAT) |

**Which path is being ordered:** the EE02 **bundle** (board + panel bought together as one bundle SKU on the same product page), not the two sub-items bought separately — there is no separate/cheaper path on Seeed's site; the "bundle" *is* the sum of the two selectable components (board `E-6639` @ €12.99 + panel `E-6569` @ €129.99), confirmed directly in the page's bundle pricing config at execution time. D-05 locks this exact kit; no substitution.

**Live-lookup notes (2026-08-04, direct fetch of the Seeed product page, not recalled from CLAUDE.md):**
- CLAUDE.md's indicative USD figures ($14.90 board / $149 panel / $163.90 total) are confirmed still current as of this lookup — no drift found.
- **Stock/lead-time flag:** at lookup time the driver board shows 82 units in the China warehouse (in stock now). The 13.3" panel shows **0 units in stock** in the China, US, and Germany warehouses, with an incoming batch of 287 units arriving 2026-08-10 and a further 50 arriving 2026-09-01. This means the panel side of the order is expected to ship on backorder against that incoming batch — directly relevant to RESEARCH.md's Assumption A4 (lead time reported anywhere from 5–10 business days to 4–6 weeks). **Confirm the live ship date at checkout in Task 2** — do not assume same-day dispatch.

## Battery Connector Verification

**(a) Connector pitch on the XIAO ESP32-S3 Plus / EE02 driver board:** 2-pin **JST 2.0mm** connector.
Source: Seeed's own EE02 getting-started wiki — "JST Connector: 2 pins JST 2.0mm connector to connect battery." — https://wiki.seeedstudio.com/getting_started_with_ee02/ (fetched 2026-08-04)

**(b) Pin order / polarity on the board's connector:** the **negative** terminal is the pin closest to the USB-C port; the **positive** terminal is the pin farthest from the USB-C port.
Source: Seeed's XIAO ESP32-S3 series getting-started wiki, "Battery Usage" section (covers XIAO ESP32-S3 / Sense / **Plus** together) — "When soldering the battery, please be careful to distinguish between the positive and negative terminals. The negative terminal of the power supply should be the side closest to the USB port, and the positive terminal of the power supply is the side away from the USB port." — https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/ (fetched 2026-08-04)

**(c) Polarity of the pack being ordered:** the Kubii "Batterie 3000mAh Li-Po" listing explicitly states its connector is **JST-PH 2.0mm, 2-pin, female**, with the standard **red wire = positive / black wire = negative** convention.
Source: https://www.kubii.com/fr/alimentations-protections/4913-batterie-3000mah-li-po-3272496324541.html (fetched 2026-08-04)

**Pitch match confirmed:** board = JST 2.0mm, pack = JST-PH 2.0mm — same 2.0mm pitch family, not a mismatched "1.25mm vs 2.0mm both sold as JST" trap. (For contrast: gotronic.fr's LiPo battery range, checked during this same lookup, uses **JST-SYP 2.54mm** — a different, incompatible pitch — and was rejected for that reason. This is exactly the kind of mismatch this section exists to catch.)

**A reversed-polarity pack destroys the board on first connection and is not recoverable.** The board's own polarity (negative-near-USB) and the pack's own polarity (red=+/black=-) are stated by two independent, official sources above, but the *physical* JST housing orientation still needs a visual check against the board's silkscreen at unboxing time before the first connection — red-wire-to-positive-pad is the pack manufacturer's convention, not a guarantee it's keyed identically to Seeed's housing. **If there is any doubt at unboxing, verify polarity with a multimeter before connecting the pack for the first time**, per this plan's own fallback instruction.

## Budget Ceiling Check

PROJECT.md's constraint: **Hardware ≤ €300 total (display + compute)**. Per this plan's instructions, the battery pack and USB-C cable — while technically accessories, not "display + compute" — are counted **inside** the €300 ceiling below, to keep the number conservative.

| Line | Amount |
|---|---|
| EE02 kit (board + panel), excl. VAT | €142.98 |
| Battery pack, excl. VAT | €7.13 |
| USB-C cable, excl. VAT | €5.79 |
| **Subtotal, excl. VAT** | **€155.90** |
| Estimated EU VAT (France, 20%) — applied to the Seeed kit subtotal only; Kubii's battery and cable prices above are already VAT-inclusive (TTC) per the French storefront, so VAT is not added a second time on those two lines | €142.98 × 20% = €28.60 |
| Battery + cable, incl. VAT (as listed, TTC) | €8.55 + €6.95 = €15.50 |
| Estimated shipping and customs — Seeed kit (economy/DHL from HK/China warehouse, small parcel, ~1kg) | €15.00 (estimate — confirm live figure at checkout in Task 2) |
| Estimated shipping — Kubii (French domestic small-parcel) | €5.00 (estimate — confirm live figure at checkout in Task 2) |
| **Total** | **€142.98 + €28.60 + €15.50 + €15.00 + €5.00 = €207.08** |
| **Headroom vs EUR 300 ceiling** | **€300.00 − €207.08 = €92.92 headroom (positive — within budget)** |

The total clears the €300 display+compute ceiling with meaningful headroom (~€93), even counting the battery and cable inside the ceiling and using a conservative (excl.-VAT-then-add-20%) treatment of the Seeed kit price. Shipping/customs figures are estimates pending the live checkout total in Task 2 — if the actual checkout total differs materially from this estimate, note it in the `## Unblock Date` section of Task 2 rather than silently revising this table.

## Separate Budget Line — Conditional, Not Ordered Now (D-04)

Per D-02, this hardware is ordered **only if** plan 01-04's aggregator-API validation comes back insufficient for near-ground reception at runway 3. Per D-04, its cost is tracked on this separate line and **does not count against the €300 display+compute ceiling** above. **Nothing in this section is being purchased during this plan.**

| Item | Indicative price | Notes |
|---|---|---|
| RTL-SDR Blog V4 dongle | ~€35 | Indicative only — not looked up live this plan, per RESEARCH.md's own framing of this hardware as conditional/deferred. Confirm live price if/when D-02's fallback is actually triggered. |
| 1090 MHz ADS-B antenna | ~€20 | Indicative only, same caveat. |
| Raspberry Pi (if a permanent local receiver is later wanted, beyond just proving reception) | ~€70 | Only needed if the fallback becomes a permanent pipeline (readsb/dump1090 forwarding to the VPS), not for the initial reception test. |
| microSD card (for the Pi, if used) | ~€10 | Same conditional scope as the Pi line. |
| **Indicative subtotal (dongle + antenna only, reception test)** | **~€55** | This is the minimum spend if D-02's fallback triggers but a permanent receiver is not yet warranted. |
| **Indicative subtotal (full permanent pipeline)** | **~€135** | Matches RESEARCH.md's Assumptions Log A3 range (~€75-100) in order of magnitude; the higher figure here includes the Pi, which A3's estimate also implicitly assumes. |

## Deliberately Not In Phase 1

- **Enclosure** — no confirmed public EE02 enclosure design exists yet (per RESEARCH.md); the panel sits bare on the bench for Phase 1 validation.
- **Solar** — out of scope for v1 per PROJECT.md's constraints.
- **Wall power** — battery-only by constraint; wall power is never used, even on the bench, once battery testing starts.
- **USB inline power meter** — rejected by D-07 in favor of the simpler time-to-depletion measurement method (no extra hardware/technical setup required).
- **reTerminal E1004** (all-in-one alternative, $279.90 / ~€258 per CLAUDE.md) — considered and rejected under D-05; listed here only as the priced-but-rejected comparison point, not as something to order.

## Order Tracking

| Item | Vendor | Order number | Ordered on | Estimated delivery | Arrived on |
|---|---|---|---|---|---|
| XIAO ePaper DIY Kit EE02 (board + panel bundle) | Seeed Studio | <seeed-order-ref> | 2026-08-05 | 2026-08-14 to 2026-08-26 (window, see note below) | PENDING |
| LiPo battery pack (Kubii "Batterie 3000mAh Li-Po") | Kubii | <kubii-order-ref> | 2026-08-05 | 2026-08-08 | PENDING |
| USB-C data cable (Kubii "Cable USB 3 Type-C vers USB-A") | Kubii | <kubii-order-ref> (same order as the battery pack — see note below) | 2026-08-05 | 2026-08-08 | PENDING |

**Notes:**
- The Kubii order (<kubii-order-ref>) covers **both** the battery pack and the USB-C cable in a single checkout — total <order-payment-details-redacted>. The two rows above share the same order number and date because they are one order, not two.
- The Seeed order's checkout-stated shipping method was "Direct Group Shipping — Duty Included — (7-15 working days), Shipping From China Warehouse." Converting that working-day range from the 2026-08-05 order date gives an estimated calendar delivery window of **2026-08-14 to 2026-08-26** (recorded as a range, since the vendor quoted working days rather than a fixed date). The BOM's own live-lookup note above flagged the panel as 0-in-stock at lookup time with an incoming restock batch expected 2026-08-10 — this working-day estimate may already price in that restock, but that is not independently confirmed, so treat 2026-08-26 as the conservative end of the window for planning purposes.

Task 2 has filled in this table now that the orders are placed.

## Unblock Date

**Unblock date: 2026-08-26** — the later of the two estimated delivery dates (the EE02 kit's 2026-08-14 to 2026-08-26 window; the Kubii battery + cable order's 2026-08-08 is earlier and not the constraint). Physical hardware in hand is not guaranteed before the end of that window, so 2026-08-26 is the conservative planning date.

**Plans gated by this date:**
- **01-06** (first light / hardware bring-up) — needs the physical EE02 board and panel to flash firmware and drive the display; cannot start before the kit arrives.
- **01-07** (backoff validation on real hardware) — needs the physical device running to validate the wake/poll/backoff loop against a live battery and network conditions; cannot start before both the kit and the battery pack arrive.

**Correction to the plan's original assumption:** the plan text for this task named 01-05, 01-06, and 01-07 as the three hardware-gated plans. That is no longer accurate for 01-05 — plan 01-05 (device firmware: wake loop, log line contract, vendored network stack, EE02 board profile) has already been completed and committed (see `.planning/phases/01-foundation-hardware-bring-up-ads-b-validation/01-05-SUMMARY.md`). 01-05 only required a containerized ESP-IDF build (`espressif/idf:v5.3.1`) and host-side tests — it never depended on physical hardware arriving, so it is not gated by this Unblock Date. Only 01-06 and 01-07 remain blocked on physical hardware.

If the actual Seeed checkout total or shipping estimate differs materially from what `## Budget Ceiling Check` assumed, that would be noted here — no material difference was reported by the developer for this order.
