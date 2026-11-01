# Second hardware: costed shortlist (7.3" Spectra 6, 800x480)

Fetched on **2026-11-01**. Every fact below comes from a product page opened on
that date (plain HTTP GET, page HTML and the data embedded in it) and is
quoted as shown. **No purchase, order, cart or payment was made**; no login
was used. Shop pages were fetched through a proxy whose exit country is not
France: Seeed and Waveshare were switched to their EUR display with a GET
(`?___store=eu`, `/directory/currency/switch/currency/EUR/...`); that sets a
display cookie only.

Target (owner): complete device (panel + board, plus battery and cable,
delivered to France, TTC) at most **100 EUR TTC**. Context only: the current
EE02 kit is about 143 EUR HT and the project ceiling is 300 EUR
(`hardware/BOM.md`, read only).

## Method and its main caveat

- VAT: neither Seeed nor Waveshare state on the product page whether the
  displayed EUR price includes VAT. `BOM.md` treated the Seeed EU price as ex-VAT
  and added 20 % French VAT; the same method is applied here to Seeed and
  Waveshare (**assumption, UNCONFIRMED on the pages**). Kubii (French shop)
  prices are TTC as listed. If the Seeed/Waveshare prices were already TTC, every
  total below drops by the 20 % VAT line (shown separately in the arithmetic).
- Delivery cost to France is computed only at checkout on all four shops, so it
  is **UNCONFIRMED** everywhere. Totals are therefore "at least" figures
  (delivery excluded). A second column adds the delivery *assumption* from
  `BOM.md` (15 EUR Seeed/Waveshare-class parcel, 5 EUR Kubii; those were
  estimates there too, not page facts). Ranking uses the "at least" figure.
- Ranking is cheapest landed cost first. Port ease, battery and enclosure are
  report columns and never reorder the table.

## Summary table (ranked, cheapest landed cost first)

| Rank | Candidate | Landed cost TTC, at least (delivery excluded) | With delivery assumption | Gap to 100 EUR (at least / assumed) | Controller | Ships to France | Battery included | Enclosure | Driver status | Unconfirmed items |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Seeed XIAO ePaper DIY Kit EE04 (board + 7.3" panel) | **78.73** | 98.73 | under (21.27 left / 1.27 left) | not named on page | unconfirmed for France (page: "ships to most countries", Germany warehouse stocks the panel) | no (JST 2.0 mm connector, switch, charger on board) | no | not stated on page | delivery, VAT, battery stock, panel controller |
| 2 | Waveshare ESP32-S3-PhotoPainter (with battery) | **90.48** | 105.48 | under (9.52 left) / **EXCEEDS by 5.48** | not named on page | page says worldwide, FR listed for e-packet | yes (3.7 V 1500 mAh, MX1.25) | wood photo frame | not stated on page | delivery, VAT, customs fees, controller |
| 3 | Waveshare 7.3" e-Paper (E) raw panel + Waveshare e-Paper ESP32 Driver Board | **at least 96.27** | at least 116.27 | under (3.73 left) / **EXCEEDS by 16.27** | not named | worldwide | no | no | bare panel: driver to write; board/panel pin match unconfirmed | charger on driver board, 7.3" compatibility, delivery |
| 4 | Waveshare 7.3" e-Paper HAT (E) (panel + Pi driver HAT) | **at least 101.67** (no MCU priced) | at least 121.67 | **EXCEEDS by at least 1.67** | not named | worldwide | no | no | HAT targets Raspberry Pi/Jetson/Arduino/STM32 | MCU board, delivery |
| 5 | Seeed reTerminal E1002 | **106.14** (cable not priced) | 121.14 | **EXCEEDS by 6.14** | ESP32-S3 (page) | unconfirmed for France (China warehouse only, 15 in stock) | yes (built-in 2000 mAh) | yes (176x120x53 mm with stand) | page lists ESP-IDF, Arduino | delivery, VAT, cable |
| unranked | Good Display GDEP073E01 bare panel | panel price UNCONFIRMED; extras alone at least 27.28 | n/a | cannot be computed | not read | UNCONFIRMED | no | no | bare panel: driver to write | panel price, MOQ, connector, controller, reseller |

Ranking note: the Good Display row has no confirmed panel price, so it is not
ranked (see its section). The VAT assumption applies to all rows alike, so it
does not change the order.

### Arithmetic (re-add each total)

All Seeed and Waveshare prices are the EUR prices displayed on 2026-11-01.

1. EE04: board 9.82 + 7.3" panel 42.87 = 52.69 HT; VAT 20 % = 10.54;
   52.69 + 10.54 = 63.23 TTC. Battery (Kubii 3000 mAh, see below) 8.55 TTC.
   USB-C cable (Kubii) 6.95 TTC. 63.23 + 8.55 + 6.95 = **78.73**. Assumed delivery
   15 + 5 = 20, giving 98.73.
2. PhotoPainter with battery: 75.40 HT; VAT 15.08; 75.40 + 15.08 = **90.48** TTC.
   The USB-A to USB-C cable (about 1 m) is in the package contents, so no cable line.
   Assumed delivery 15 gives 105.48. (Variant without battery: 74.50 HT, 89.40 TTC; it
   needs a battery with an MX1.25 2-pin plug, not priced.)
3. Waveshare raw (E) panel 53.85 + ESP32 Driver Board 13.46 = 67.31 HT;
   VAT 13.46; 67.31 + 13.46 = 80.77 TTC. Battery 8.55 + cable 6.95 = 15.50.
   80.77 + 15.50 = **96.27**. Assumed delivery 15 + 5 gives 116.27. The Kubii battery
   has a JST-PH 2.0 plug and the page does not say the driver board takes it
   (UNCONFIRMED).
4. HAT (E) with driver HAT: 71.81 HT; VAT 14.36; 86.17 TTC. Battery 8.55 + cable 6.95
   = 15.50. 86.17 + 15.50 = **101.67**, with no ESP32 board priced yet, so the real total is higher.
5. E1002: 88.45 HT; VAT 17.69; 88.45 + 17.69 = **106.14** TTC. Assumed delivery 15
   gives 121.14.
6. Good Display: extras only. EE04 board 9.82 HT x 1.2 = 11.78 TTC; battery 8.55; cable
   6.95; 11.78 + 8.55 + 6.95 = **27.28**, plus the panel, plus delivery.

Comparison, context only: the cheapest candidate (EE04, 63.23 TTC for board and
panel, 78.73 with battery and cable) against the EE02 kit at 142.98 HT (171.58
TTC by the same method): about 108 EUR TTC less for board and panel (171.58 - 63.23 = 108.35). All candidates sit far
below the 300 EUR project ceiling.

## 1. Seeed XIAO ePaper DIY Kit EE04 (bundle: board + 7.3" Spectra 6)

- URL: https://www.seeedstudio.com/XIAO-ePaper-EE04-DIY-Bundle-Kit.html (SKU E25102101), fetched 2026-11-01.
  Wiki name: EE04 (page title "XIAO ePaper Board(ESP32-S3) EE04 DIY Display Bundle Kit").
- Panel option on the page: "7.3" spectra 6 E-Ink / ePaper Display with 800x480 Pixels, SPI interface, Support XIAO/Arduino" (SKU 100064541). Confirms 800x480 Spectra 6.
- Board: "XIAO ePaper Display Board(ESP32-S3) - EE04" (SKU 100075670), "Powered by XIAO ESP32-S3 Plus ... supports both 24-pin and 50-pin ePaper displays ... JST 2.0 mm battery connector with power switch, built-in charging IC ... one reset and three user buttons". Which pin count the 7.3" panel uses: not stated (UNCONFIRMED).
- Included items: board + chosen panel. No battery, no cable, no enclosure listed.
- Price, EUR store: board 9.82, panel 42.87 (list prices shown struck: 8.99 / 40.99). USD store, same page: board 10.99, panel 47.99 (USD 58.98 total). Bundle page total is shown only after JS selection; the sum is mine.
- TVA: the page does not say whether the price includes VAT (UNCONFIRMED). Page text: "the shipping fee includes the 3 EUR EU import duty for orders under $150" and "Under DAP terms, buyers cover customs duties, taxes, and import fees; ... DAP shipments with TAXES over $100 require payment within 5 days at customs clearance".
- Stock (EUR store): board China warehouse 62, US 0, Germany 0; panel China warehouse 33, Germany warehouse 39, US 0.
- Delivery to France: cost and estimate UNCONFIRMED (computed at checkout; the page's delivery-date field is filled by script and was empty). Page says "ships to most countries" / "ships to European Union only" for some warehouses. History only (own order of 2026-08-05 in `BOM.md`, not today): "Direct Group Shipping, Duty Included, 7-15 working days, from China warehouse".
- Extras to reach a complete device: battery (3.7 V LiPo, JST 2.0 mm) and USB-C cable; see "Battery and cable sources".
- Vendor driver/library: page names none for the panel. Seeed wiki links on the EE02 page (not opened for this table): `epaper_ee04`, `EE04_with_esphome_advanced`, `EE04_with_hmi` (plan 58-02 reads these).

## 2. Waveshare ESP32-S3-PhotoPainter 7.3" E6

- URL: https://www.waveshare.com/esp32-s3-photopainter.htm (SKU 32408 with battery, 32753 without), fetched 2026-11-01.
- Panel: 7.3" E6 full colour, 800 x 480 (title). Board: ESP32-S3-WROOM-1-N16R8 (16 MB flash, 8 MB PSRAM), RTC PCF85063, SHTC3, TF slot, audio codec, battery management (page).
- Included: card reader, screen film, USB-A to USB-C cable about 1 m, 8 ohm 2 W speaker, hook hanger, opening tool, 16 GB TF card; "3.7V 1500mA Lithium battery" is the page's "optional" item (selector "3.7V Lithium battery: Included / Not included"). Solid wood frame with stand/hook. Battery header is MX1.25 2-pin.
- Price, EUR display: with battery 75.40, without battery 74.50 (the 0.90 difference is odd for a 1500 mAh pack; page shows no separate battery price). Structured data on the page labels 83.99 / 82.99 as EUR; those are the USD amounts (USD display: 83.99 / 82.99). **Mismatch on the page: the structured-data currency label is wrong; the displayed EUR price is used.**
- TVA: not stated on the product page. Waveshare shipping page: "all additional local taxes, duties, GST, tariffs and fees should be customers' responsibilities". Import VAT and any courier fee are therefore extra and not quantified (UNCONFIRMED).
- Stock: structured data says InStock for all variants; no quantity shown (UNCONFIRMED beyond that).
- Delivery: cost computed at checkout (UNCONFIRMED). Waveshare shipping page: DHL "usually takes about 3-8 working days; Better for Europe", FedEx 4-8, UPS 3-7, E-packet "7-15 working days or more ... available for USA, CA, AU, FR, UK, and RU only"; orders are shipped "within 3 business days" after payment. FR is therefore named for E-packet; cost not shown.
- Vendor driver: page says "Open source code", wiki at www.waveshare.com/wiki/ESP32-S3-PhotoPainter (not opened here). Controller: not named. ESP-IDF: not stated on the product page.

## 3. Waveshare 7.3inch e-Paper HAT (E) / raw (E)

- URL: https://www.waveshare.com/7.3inch-e-paper-hat-e.htm (SKU 27875 with HAT, 27863 raw), fetched 2026-11-01.
- Panel: 7.3", 800 x 480, E6 full colour, SPI, 2 grey levels (page). Two variants: "7.3inch e-Paper (E) raw display, without driver board" and "7.3inch e-Paper HAT (E) with e-Paper Driver HAT".
- Included in the raw variant: "7.3inch e-Paper (E) x1" only. Included in the HAT variant: panel, "e-Paper Driver HAT + Adapter board + FFC cable x1", PH2.0 8-pin cable, Raspberry Pi screws.
- Price, EUR display: raw 53.85, with HAT 71.81 (USD display 59.99 / 79.99). Same structured-data currency-label mismatch as above (USD amounts labelled EUR).
- The HAT is a Raspberry Pi 40-pin / SPI board; it contains no ESP32. A standalone device needs an MCU board, not priced for the HAT variant.
- Raw panel route priced here: Waveshare "Universal e-Paper Driver Board with ESP32 onboard", https://www.waveshare.com/e-paper-esp32-driver-board.htm (SKU 15823), fetched 2026-11-01: 13.46 EUR displayed (structured data 14.99), package "e-Paper ESP32 Driver Board, e-Paper Adapter, 24PIN FFC". The page does not mention 7.3" (E) compatibility, a battery connector or a charger (UNCONFIRMED).
- TVA, delivery, stock, shipping times: as for the PhotoPainter (same shop; structured data InStock for both variants).
- Vendor driver: "examples for Raspberry Pi/Jetson Nano/RDK X3/Arduino/STM32" (page); controller not named; ESP-IDF not stated.

## 4. Seeed reTerminal E1002

- URL: https://www.seeedstudio.com/reTerminal-E1002-p-6533.html, fetched 2026-11-01.
- Page: "7.3 inch open-source full color ePaper display", E Ink Spectra 6, 800x480, ESP32-S3, "built-in 2000mAh battery ... up to 3 months ... (6-hour refresh interval)", USB-C 5V/1A, enclosure 176 x 120 x 53 mm with stand. Page names "Home Assistant, TRMNL, Arduino and ESP-IDF" as supported development paths (vendor statement; not verified against any code here).
- Price, EUR store: 88.45 (structured data, schema.org InStock). USD store: 99.00.
- Stock: China warehouse only, 15 units in stock; further inbound batches are listed with dates from 2026-11-03.
- TVA, delivery to France: UNCONFIRMED, as for Seeed above. Cable: not listed as included (UNCONFIRMED); not priced.
- Controller: not named.

## 5. Good Display GDEP073E01 (bare panel)

- Listing page read: https://www.e-paper-display.com/products_list/pmcId=33.html (fetched 2026-11-01): "E Ink displays 7.3-inch color ePaper module 800x480 GDEP073E01(E6)" and "7.3-inch color E Ink Specta 6 ePaper module 800x480 GDEP073E01", linking to https://www.good-display.com/product/533.html.
- **The product page could not be read**: a plain GET of good-display.com/product/533.html returned HTTP 404 and the site root also returned 404 (one earlier attempt was reset). No workaround was attempted. Reseller pages (buydisplay.com, digikey.fr, mouser.fr) returned a bot challenge and were not read.
- Therefore UNCONFIRMED: price HT/TTC, MOQ or sample rules, who sells it in or to France, FPC connector type and pitch, controller named in the datasheet, supply voltage, stock, delivery.
- It is the same 7.3" 800x480 Spectra 6 size as the Seeed and Waveshare panels; whether those panels are this part is not stated on any page read.

### Bare panel extras (priced from pages actually read)

| Line | Source | Price shown | TTC (method above) |
|---|---|---|---|
| Driver board with ESP32-S3 and LiPo charging, EE04 board (24/50-pin FPC) | Seeed EE04 page | 9.82 HT | 11.78 |
| Alternative: Waveshare e-Paper ESP32 Driver Board (charging not stated) | Waveshare driver board page | 13.46 HT | 16.15 |
| Battery 3.7 V 3000 mAh JST-PH 2.0 (page shows add-to-cart disabled, "Rupture de stock") | Kubii | 8.55 TTC | 8.55 |
| USB-C cable (Kubii, 118 in stock) | Kubii | 6.95 TTC | 6.95 |
| Delivery of each part | all shops | UNCONFIRMED | n/a |
| Panel GDEP073E01 | Good Display | UNCONFIRMED | n/a |
| Enclosure | none | not priced | n/a |

Extras with the cheaper EE04 board: 11.78 + 8.55 + 6.95 = **27.28 TTC**, before the panel and delivery.

Driver-writing risk, in plain terms: a bare panel has no vendor ESP-IDF driver
on any page read. The controller is not named on the Seeed, Waveshare or
Good Display listing pages read, so it is unknown until the datasheet or vendor
demo code is read. Init and refresh sequences would come only from vendor
Arduino or C sources and have to be ported to ESP-IDF 5.3.1 behind the
`fp_panel_draw` / `epd_init` / `epd_blit` / `epd_sleep` seam. That port plus
wiring, with no enclosure, has to fit the one-day, no-hardware spike. If the
controller is unknown or no init sequence is found, the candidate fails the
spike. Note that the EE04 and PhotoPainter/E1002 candidates are not "bare":
the vendors supply the panel on a matching board and demo code.

Further candidates: no further 7.3" Spectra 6 800x480 candidate was opened and
recorded to this standard (the Seeed EE04 page also sells 4.26", 5.83" and 7.5"
mono and smaller panels, which are not 7.3" colour). No further candidates found.

## Battery and cable sources (all candidates needing them)

- Battery, Kubii "Batterie 3000mAh Li-Po": https://www.kubii.com/fr/alimentations-protections/4913-batterie-3000mah-li-po-3272496324541.html, fetched 2026-11-01. Price 8.55 TTC (matches `BOM.md`, 8.55 TTC). **Stock: the add-to-cart button is disabled and reads "Rupture de stock"** (the microdata still says InStock). `BOM.md` recorded 7.13 HT, so this is a change since 2026-08-04. A replacement battery is UNCONFIRMED (a Kubii search for LiPo battery showed only this one).
- Cable, Kubii "Cable USB 3 Type-C vers USB-A": https://www.kubii.com/fr/hub-cables-adaptateurs/4093-cable-usb-3-type-c-vers-usb-a-3272496315709.html, fetched 2026-11-01. 6.95 TTC, "En stock 118". The owner already received one with the EE02 order (`BOM.md`); counted anyway per the target definition.
- Kubii delivery: "Livraison offerte a partir de 75 EUR en France"; below that the cost is shown only at checkout (UNCONFIRMED).
- Connector warning: Kubii pack is JST-PH 2.0 (fits EE04); the PhotoPainter uses MX1.25 2-pin, so its own pack is the one to use.

## Spike candidates

For plan 58-02, cheapest landed cost first, at most five, purchasable for France
as far as the pages show:

1. Seeed XIAO ePaper EE04 (board + 7.3" panel)
2. Waveshare ESP32-S3-PhotoPainter 7.3"
3. Waveshare 7.3" e-Paper (E) raw panel / HAT (E) (one panel and driver source covers both variants and the ESP32 driver board route)
4. Seeed reTerminal E1002 (exceeds 100 EUR TTC; kept so the owner sees the whole field)
5. Good Display GDEP073E01 (purchasability for France UNCONFIRMED; kept because the spike only reads sources and compiles, it does not buy)

## What could not be confirmed

- VAT treatment of every displayed Seeed and Waveshare price (ex-VAT assumed, as in `BOM.md`).
- Delivery cost and estimate to France on Seeed, Waveshare, Kubii (checkout only); import VAT/customs handling fees on Waveshare.
- Whether Seeed ships each item to France (no address was entered); only warehouse labels and generic "ships to" text were seen.
- Stock quantity on Waveshare (structured data only says InStock).
- Panel controller on every Seeed and Waveshare page (not named); ESP-IDF support is stated only for the E1002 (vendor wording), not for the others.
- EE04 FPC pin count for the 7.3" panel (24 or 50 pin).
- Waveshare ESP32 driver board: 7.3" (E) compatibility, charger and battery connector.
- PhotoPainter: price of the optional battery (the selector delta is 0.90 EUR) and ESP-IDF status.
- Replacement for the out-of-stock Kubii battery.
- E1002: cable included or not; delivery.
- Good Display GDEP073E01: price, MOQ, sellers in France, connector, controller, voltage (page 404 for a plain GET; resellers behind bot challenges).
- Owner's earlier web research was not available in this run, so no claim-by-claim comparison was possible; mismatches found against records are the Kubii battery stock (`BOM.md` implied buyable) and the Waveshare structured-data currency label.

No purchase, order, cart or payment was made.
