# Phase 58: supplier contact tracking

Owner-reported contacts. Nothing here is a quote or an order; no purchase has been made.
Last updated 2026-11-02.

## Scope

Two panel formats are in scope (decision D-10 in `58-CONTEXT.md`): the 13.3" (current EE02 frame,
1200x1600) and a new 7.3" (800x480). One message asked each supplier for both references.

## Contacts

| Supplier | Contacted | Asked for | Status | Reply |
|---|---|---|---|---|
| OKRA Technologies (Shanghai) | 2026-11-02 (owner-reported; the supplier name is assumed from the datasheet page the owner shared) | 7.3" OK-EL073TF1 and the OK-DEV01C ESP32-S3 board; 13.3" if offered | replied with datasheets (7.3" tentative v0.1, 13.3" EL133UF3 v1.0), no price; owner replied; not pursued since 2026-11-07 | datasheets only |
| Seekink | 2026-11-02 (owner-reported) | 7.3" and 13.3" Spectra 6 modules, demo kits | not pursued since 2026-11-07 | none |

## What each reply must answer

1. Unit price for 1, 5, 20 and 50 pieces, delivered to France, with EU VAT and import duty treatment.
2. Minimum order quantity, lead time, payment and shipping options.
3. Datasheet, controller IC name, interface and connector, initialization sequence, waveform data,
   and ESP-IDF sample code with its licence (13.3": confirm the two-controller layout).
4. Typical and standby power, full refresh time at 25 C and 0 C, minimum refresh interval
   (feeds the battery model of the new type).
5. Proof of genuine E Ink film with batch/date code, warranty, dead-on-arrival terms.
6. Price and datasheet of an ESP32-S3 driver or development board, and 3.7 V LiPo support.

## Reference prices observed (not quotes)

7.3" Spectra 6, 800x480. Currency as displayed, no delivery, VAT not uniform.
Seeed and Waveshare figures date from 2026-11-01; the others from 2026-11-02.

| Source | Price | Note |
|---|---|---|
| Seeed EE04 kit (board 9.82 + panel 42.87) | 52.69 EUR excl. VAT | board is an ESP32-S3 Plus; VAT and delivery unconfirmed |
| Good Display, panel only | 39.51 USD (list 52.67) | owner screenshot, time-limited sale |
| Good Display, panel with ESP32 kit | 51.13 USD (list 68.17) + 23.22 USD shipping | owner screenshot; board name not legible, possibly not an ESP32-S3 |
| AliExpress, module EL073TF1 | 44.13 USD (list 66.92) | seller not checked |
| AliExpress, GDEP073E01 | 52.80 USD (list 61.40) | seller not checked |
| Waveshare raw panel | 53.85 EUR excl. VAT | |
| E Ink shop | 149 USD | business shop |
| OKRA OK-EL073TF1 | not stated | datasheet only: 17 s full refresh, 0-50 C, controller not named |

Order-of-magnitude totals: Seeed kit about 67.7 EUR excl. VAT with the 15 EUR delivery estimate of
`hardware/BOM.md`; Good Display kit about 74.4 USD with its stated shipping, before VAT and duties.

## Decisions still open

- Purchase of a 7.3" evaluation unit: agreed by the owner on 2026-11-07 (one Seeed EE04 bundle kit, owner orders). Ordered by the owner on 2026-11-07 (owner-reported: "j'ai commandé le kit"). Price paid, delivery estimate and order reference not yet given.
- Gallery 3 and Kaleido 3: dropped for this phase by the owner on 2026-11-02 (decision D-11).

## Order notes for the Seeed evaluation unit (not an order)

- Seeed's own pages blocked automated reads on 2026-11-07, so price and stock must be read on the page at checkout.
- A European reseller, OpenELAB (Munich), listed on 2026-11-07: bundle 67.15 EUR (pre-order, dispatch estimated 10 to 20 days),
  board alone 11.50 EUR and panel alone 55.49 EUR (shown in stock). Bundle contents per that reseller: EE04 board, 2.4 GHz FPC antenna, 7.3" panel.
- Not in the bundle: battery, USB-C cable, enclosure. Check whether the antenna and the 24/50-pin jumper cap are supplied.
  The 50-pin side must be selected for the 7.3" panel; a wrong jumper position can damage the screen (Seeed wiki).
- Battery: a 3.7 V LiPo with a JST 2.0 mm plug. Check the polarity with a multimeter before the first connection (`hardware/BOM.md`).
- Record the price actually paid and the delivery date in `hardware/SECOND-HARDWARE-VALIDATION.md` when part 2 starts.
