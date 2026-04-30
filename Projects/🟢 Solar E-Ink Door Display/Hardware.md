---
tags: [hardware, bom, wiring]
---
# Hardware

[[index|← Project Overview]]

## Display
- **Waveshare 7.5" e-ink** — 800×480, black/white
- Flat, low power, readable in all lighting
- Avoid 3-colour (red/black/white) — slow refresh; use LED for colour alerts instead

## Power System

**Battery:** Li-Po pouch cell — 3.7V, 2000mAh (~7.4Wh) with protection board
- Model: 505060 rechargeable lithium polymer (from Temu)
- Protection circuit included; charges to 4.2V (compatible with DFR0559 CN3791)
- At ~1–2mA average draw (ESP32 deep sleep + occasional refresh) → lasts ~3–5 days without sun

**Solar panel:** Reolink 12W 5V (user-owned)

### Power Chain

| Stage | Component | Notes |
|---|---|---|
| Solar input regulation | DFRobot DFR0559 (CN3791 MPPT) | 5V solar input → Li-Po, MPPT tracking, up to 2A charge |
| Battery → 3.3V | Built into DFR0559 | Stable 3.3V regulated output |
| 5V rail | DFR0559 5V output | For WS2812B LED only |
| Battery monitoring | MAX17048 (I2C) | Reports SoC to ESP32 → visible in HA |

## Microcontroller
- **ESP32 dev board** — generic Temu board, CP2102 USB-to-UART, dual-core LX6 240MHz
- Deep sleep ~10µA
- Wake on timer every 15–30 min → fetch data → refresh display → sleep
- 20+ usable GPIOs — plenty for all peripherals + 4 buttons
- XIAO ESP32C6 (owned) reserved as candidate for final compact build

## Alert LED
- **WS2812B** addressable RGB LED (single or 3-LED mini strip)
- Red / Yellow / Green via single GPIO
- Powered from 5V rail
- 470Ω series resistor on data line, 100nF decoupling cap on VCC

---

## Wiring

### Pin Assignments (ESP32 — VSPI + hardware I2C)

| GPIO | Function | Connected To |
|---|---|---|
| GPIO21 | I2C SDA | MAX17048 SDA |
| GPIO22 | I2C SCL | MAX17048 SCL |
| GPIO23 | SPI MOSI (VSPI) | e-ink MOSI |
| GPIO19 | SPI MISO (VSPI) | e-ink MISO (optional) |
| GPIO18 | SPI CLK (VSPI) | e-ink CLK |
| GPIO5  | SPI CS (VSPI) | e-ink CS |
| GPIO17 | DC | e-ink DC |
| GPIO16 | RST | e-ink RST |
| GPIO4  | BUSY | e-ink BUSY |
| GPIO25 | WS2812B DATA | LED DIN |
| GPIO14 | CHRG (optional) | DFR0559 charging status |
| 3V3 | Power | DFR0559 3V3 out, e-ink VCC, MAX17048 VCC |
| GND | Ground | All components |

### Button GPIOs

| Button | GPIO | Function |
|---|---|---|
| B1 | GPIO32 | Cycle display page / next screen |
| B2 | GPIO33 | Dismiss / acknowledge alert |
| B3 | GPIO26 | Force display refresh |
| B4 | GPIO27 | Spare / user-defined from HA |

- Internal pull-up enabled on each button GPIO
- ~10 GPIOs still free after all allocations

### Wiring Notes
- 470Ω series resistor on WS2812B data line
- 100nF decoupling cap across WS2812B VCC/GND, close to LED
- MISO optional (e-ink is write-only) but include for driver compatibility
- Battery connects via DFR0559 KF396 screw terminal (no JST needed on battery side)
- GPIO14 CHRG: goes LOW when DFR0559 is actively charging — wire to optional status pin

---

## Bill of Materials

| Component                                       | Approx. Cost | Notes |
| ----------------------------------------------- | ------------ | --- |
| Waveshare 7.5" e-ink + driver hat               | CHF 67.90    | Bastelgarage SKU 420486 |
| ESP32 dev board (generic, CP2102)               | —            | ✅ owned — used for prototype |
| Seeed Studio XIAO ESP32C6                       | €4.89        | ✅ owned — reserved for final build |
| DFRobot Solar Power Manager DFR0559             | CHF 13.90    | Bastelgarage |
| Li-Po pouch cell 3.7V 2000mAh (505060)          | ~CHF 8–10    | Temu |
| MAX17048 fuel gauge breakout                    | ~CHF 4–5     | AliExpress |
| WS2812B mini LED                                | —            | ✅ owned |
| 4× tactile buttons                              | ~CHF 1–2     | AliExpress |
| JST-PH 2.0 connector + pigtail                  | ~CHF 1–2     | LCSC |
| 470Ω resistors (2x)                             | ~CHF 0.50    | LCSC |
| 100nF ceramic caps (2x)                         | ~CHF 0.50    | LCSC |
| Breadboard / perfboard / wire / misc            | ~CHF 5–8     | LCSC or owned |
| **Total**                                       | **~CHF 100–110** | — |

*ESP32 dev board already owned — deduct ~8 CHF if using it*

---

## Ordering Checklist

Legend: ✅ owned · 🟡 ordered · ⬜ still needed

| Component                           | Status     | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ----------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| ESP32 dev board (generic, CP2102)   | ✅ owned    | Prototype board — Temu generic dual-core                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Seeed Studio XIAO ESP32C6           | ✅ owned    | Kiwi SS-113991254 — reserved for final compact build                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Reolink 12W 5V solar panel          | ✅ owned    |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Waveshare 7.5" e-ink + driver hat   | ✅ owned    | Delivered                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| DFRobot DFR0559 solar power manager | ✅ owned    | Delivered                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Li-Po pouch cell 3.7V 2000mAh       | 🟡 ordered | [Temu 505060](https://www.temu.com/goods.html?_bg_fs=1&goods_id=601100416357332&from_share=1&refer_share_id=ac7cac5c-b46b-490c-b285-3e96bc55&refer_share_channel=whatsapp_chat&_oak_page_source=417&_oak_region=192&refer_share_suin=RSSBDHSS5SR5Z64L2BQGA3TNRERECVRW6O4RQWQTW2ULN66EVPR3M7YXQTDKZYNLBZXMRCC2TY&share_img=https%3A%2F%2Fimg-eu.kwcdn.com%2Fgoods-detail-img%2F35b7c2%2FyeUWmfsNGd%2F1c6ebb058e0e4662a6bac71d2da08b2e.png&share_ui_type=1&_oaksn_=CKI%2FqmYUzTy7hJMwe8d8LkEU9c50jgAn9Ts00YRjrK4%3D) |
| MAX17048 fuel gauge breakout        | ✅ owned    | Adafruit ADA-5580 — Kiwi Electronics €5.69                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| WS2812B mini LED                    | ✅ owned    | —                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 4× tactile buttons                  | ✅ owned    | 6mm Pushbutton 20-pack — Kiwi KW-1557 €1.99                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| JST-PH 2.0 connector + pigtail      | ✅ owned    | 2× 10cm pigtail — Kiwi KW-1560 €1.58                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 470Ω resistors (2x, 0603/THT)       | ✅ owned    | LCSC ~CHF 0.50                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 100nF ceramic caps (2x, X7R)        | ✅ owned    | From capacitor kit                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Breadboard / perfboard / wire       | ✅ owned    | LCSC or scrap ~CHF 5–8                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| M3 heat-set inserts                 | ✅ owned    | For enclosure wall mount                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
|                                     |            |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
