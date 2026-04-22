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

**Battery:** LiFePO4 pouch cell — 3.2V, 6Ah (~19Wh)
- Safer than Li-ion, tolerates partial charge, 2000–3000 cycle lifespan, better cold performance
- At ~1–2mA average draw (ESP32 deep sleep + occasional refresh) → lasts weeks without sun

**Solar panel:** Reolink 12W 5V (user-owned)

### Power Chain

| Stage | Component | Notes |
|---|---|---|
| Solar input regulation | DFRobot DFR0559 (CN3791 MPPT) | 5V solar input → LiFePO4, MPPT tracking, up to 2A charge |
| Battery → 3.3V | Built into DFR0559 | Stable 3.3V regulated output |
| 5V rail | DFR0559 5V output | For WS2812B LED only |
| Battery monitoring | MAX17048 (I2C) | Reports SoC to ESP32 → visible in HA |

## Microcontroller
- **ESP32-S3 Mini** (or owned ESP32-C3/S3 dev board)
- Deep sleep ~10–20µA
- Wake on timer every 15–30 min → fetch data → refresh display → sleep

## Alert LED
- **WS2812B** addressable RGB LED (single or 3-LED mini strip)
- Red / Yellow / Green via single GPIO
- Powered from 5V rail
- 470Ω series resistor on data line, 100nF decoupling cap on VCC

---

## Wiring

### Pin Assignments (ESP32-S3)

| GPIO | Function | Connected To |
|---|---|---|
| GPIO8 | I2C SDA | MAX17048 SDA |
| GPIO9 | I2C SCL | MAX17048 SCL |
| GPIO18 | SPI MOSI | e-ink MOSI |
| GPIO19 | SPI MISO | e-ink MISO (optional) |
| GPIO20 | SPI CLK | e-ink CLK |
| GPIO21 | SPI CS | e-ink CS |
| GPIO22 | DC | e-ink DC |
| GPIO23 | RST | e-ink RST |
| GPIO24 | BUSY | e-ink BUSY |
| GPIO5 | WS2812B DATA | LED DIN |
| 3V3 | Power | DFR0559 3V3 out, e-ink VCC, MAX17048 VCC |
| GND | Ground | All components |

### Button GPIOs (4 buttons — TBD after board confirmed)

| Button | GPIO | Suggested Function |
|---|---|---|
| B1 | TBD | Cycle display page / next screen |
| B2 | TBD | Dismiss / acknowledge alert |
| B3 | TBD | Force display refresh |
| B4 | TBD | Spare / user-defined from HA |

- Internal pull-up enabled on each button GPIO
- 10–15 free GPIOs remain after SPI + I2C + LED allocations

### Wiring Notes
- 470Ω series resistor on WS2812B data line
- 100nF decoupling cap across WS2812B VCC/GND, close to LED
- MISO optional (e-ink is write-only) but recommended for driver compatibility
- JST-PH 2.0 connector for battery (swappable)

---

## Bill of Materials

| Component | Approx. Cost |
|---|---|
| Waveshare 7.5" e-ink + driver hat | ~35 CHF |
| ESP32-S3 Mini (or use owned dev board) | ~8 CHF |
| DFRobot Solar Power Manager DFR0559 | ~12 CHF |
| LiFePO4 pouch cell 3.2V 6Ah | ~15 CHF |
| MAX17048 fuel gauge breakout | ~5 CHF |
| WS2812B mini LED | ~2 CHF |
| 4× tactile buttons | ~2 CHF |
| Misc (connectors, PCB, wiring, resistors, caps) | ~10 CHF |
| **Total** | **~89 CHF** |

*ESP32 dev board already owned — deduct ~8 CHF if using it*

---

## Ordering Checklist

Legend: ✅ owned · 🟡 ordered · ⬜ still needed

| Component                           | Status         | Notes                        |
| ----------------------------------- | -------------- | ---------------------------- |
| ESP32 dev board (C3 or S3)          | ✅ owned        | Confirm exact model + pinout |
| Reolink 12W 5V solar panel          | ✅ owned        |                              |
| Waveshare 7.5" e-ink + driver hat   | ⬜ still needed |                              |
| DFRobot DFR0559 solar power manager | ⬜ still needed |                              |
| LiFePO4 pouch cell 3.2V 6Ah         | 🟡 ordered     |                              |
| MAX17048 fuel gauge breakout        | ⬜ still needed |                              |
| WS2812B mini LED                    | ⬜ still needed |                              |
| 4× tactile buttons                  | ⬜ still needed |                              |
| JST-PH 2.0 connector (battery)      | ⬜ still needed |                              |
| 470Ω resistors                      | ⬜ still needed | For WS2812B data line        |
| 100nF ceramic caps                  | ⬜ still needed | WS2812B decoupling           |
| M3 heat-set inserts                 | ✅ owned        | For enclosure wall mount     |
| Misc wire / PCB / connectors        | ⬜ still needed |                              |
|                                     |                |                              |
