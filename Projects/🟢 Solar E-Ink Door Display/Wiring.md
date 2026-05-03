---
tags: [wiring, hardware, soldering]
---

# Wiring Diagram

[[index|← Project Overview]]

> [!tip] Interactive diagram
> [Open wiring diagram in browser](Files/door-display-wiring.html) — colour-coded SVG, full component view (dark theme).
> [Open A4 print version](Files/door-display-wiring-print.html) — light theme, scaled to A4 landscape · `Ctrl+P` to print.

---

## Pin Assignments (ESP32)

| GPIO | Signal | Connected To | Wire Colour |
|---|---|---|---|
| GPIO18 | SPI CLK | E-ink CLK | Yellow |
| GPIO23 | SPI MOSI | E-ink MOSI | Yellow |
| GPIO19 | SPI MISO | E-ink MISO | Yellow |
| GPIO15 | SPI CS | E-ink CS | Yellow |
| GPIO17 | DC | E-ink DC | Blue |
| GPIO16 | RST | E-ink RST | Blue |
| GPIO4 | BUSY | E-ink BUSY | Blue |
| GPIO21 | I2C SDA | MAX17048 SDA | Green |
| GPIO22 | I2C SCL | MAX17048 SCL | Green |
| MAX17048 JST PH | — | Battery JST pigtail (in) | Red/Black |
| MAX17048 BAT+ pin | DFR0559 BAT+ KF396 | Charger feed (out) | Red |
| MAX17048 BAT– pin | DFR0559 BAT– KF396 | Charger feed (out) | Black |
| GPIO25 | LED data | 470Ω → WS2812B DIN | Purple |
| GPIO32 | Button B1 | B1 → GND | Purple |
| GPIO33 | Button B2 | B2 → GND | Purple |
| GPIO26 | Button B3 | B3 → GND | Purple |
| GPIO27 | Button B4 | B4 → GND | Purple |
| GPIO14 | CHRG (opt) | DFR0559 CHRG pin | — |
| 3V3 | Power in | DFR0559 3V3 out | Red |
| GND | Ground | Common ground rail | Black |

---

## Power Chain

> [!warning] DFR0559 has no 3.3V output
> The DFR0559 only provides a **5V rail**. Connect it to ESP32 **VIN** (not 3V3).
> The ESP32's onboard AMS1117-3.3 LDO then generates 3.3V via the **3V3 pin**.

```
Solar Panel (5V)
  └─→ DFR0559 IN+ / IN–
        ├─→ DFR0559 BAT+ / BAT–  ──→  MAX17048 BAT+ / BAT– (header pins)
        │                                  │
        │                                  └─→ MAX17048 JST PH socket ──→ Battery JST pigtail
        │                                       (chip powered by battery; sees true Vbat in-line)
        ├─→ 5V out ──→ ESP32 VIN     (feeds onboard LDO)
        │              └─→ ESP32 3V3 pin ──→ E-ink VCC
        │                                    MAX17048 VCC (I2C logic level only)
        └─→ 5V out ──→ WS2812B VCC   (direct 5V)
```

> [!important] MAX17048 sits IN-LINE between battery and DFR0559
> The battery does **not** connect directly to the DFR0559. Instead:
> 1. Battery JST pigtail plugs into the **MAX17048 JST PH socket**
> 2. Two short wires from the **MAX17048 BAT+ / BAT– header pins** screw into the **DFR0559 KF396 BAT+ / BAT– terminals**
>
> All three points (battery JST, MAX17048 BAT pin, DFR0559 BAT terminal) are the **same electrical node** — current flows through the MAX17048's BAT pin in both directions (charging from DFR0559 → battery, discharging from battery → load via DFR0559's 5V boost).
>
> The 3V3 pin on the MAX17048 breakout only supplies the **I2C logic level**. If no battery is plugged into the JST socket, the chip will not respond to I2C scans regardless of 3V3.

---

## Passives

| Component | Value | Location |
|---|---|---|
| Series resistor | 470Ω | GPIO25 → WS2812B DIN inline |
| Decoupling cap | 100nF | WS2812B VCC to GND, as close to LED as possible |

---

## Buttons

All buttons: one leg to GPIO pin, other leg to GND. Pull-up enabled in ESPHome (`internal: true`).

| Button | GPIO | Function |
|---|---|---|
| B1 | GPIO32 | Cycle display page |
| B2 | GPIO33 | Dismiss / acknowledge alert |
| B3 | GPIO26 | Force display refresh |
| B4 | GPIO27 | Spare / HA-defined |

---

## Notes

- **MISO** is optional — e-ink display is write-only, but include for driver compatibility
- **SPI wires** should be kept short (< 15 cm) to avoid signal integrity issues
- **GPIO15** is a strapping pin — ESPHome will warn about it, safe to ignore for CS use
- **DFR0559 CHRG** goes LOW when actively charging — useful for a charging indicator if needed
- **MAX17048 JST PH** — plug battery JST pigtail directly into MAX17048 breakout BAT+/BAT– port; the chip monitors battery voltage and reports SoC over I2C
