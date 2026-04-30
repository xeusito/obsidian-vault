---
status: in-progress
priority: medium
startDate: 2026-04-21
dueDate: 2026-07-15
tags: [project, hardware, esp32, home-assistant, esphome]
---

# Solar-Powered E-Ink Door Display

A solar-powered e-ink information display mounted behind the front door. Shows calendar events, trash pickup schedules, and alert messages. Controlled by an ESP32, powered by a solar panel + LiFePO4 battery, integrated with Home Assistant via ESPHome.

## Subpages
- [[Hardware]] — power system, display, wiring, BOM
- [[Software]] — ESPHome YAML, Home Assistant integration
- [[Enclosure]] — 3D design, dimensions, layout

## Status

| Item                   | State     |
| ---------------------- | --------- |
| ESP32 board confirmed  | ✅ Seeed XIAO ESP32C6 — received |
| Parts ordered          | ✅ complete — battery still in transit |
| ESPHome config started | ⬜ pending |
| Prototype wired        | ⬜ pending |
| Enclosure designed     | ⬜ pending |
| Final assembly         | ⬜ pending |

## Next Steps
- [ ] Confirm exact ESP32 board model (C3 vs S3) and available GPIOs
- [ ] Order DFR0559, MAX17048, Waveshare 7.5" e-ink, LiFePO4 cell
- [ ] Assign button GPIOs based on confirmed pinout
- [ ] Start ESPHome YAML configuration
- [ ] Design 3D enclosure (FreeCAD / Fusion 360 / OpenSCAD)
- [ ] Wire prototype on breadboard
- [ ] Flash ESPHome and test HA integration
- [ ] Print enclosure and final assembly
- [ ] Add a task to suggest umbrella of the weather seems to be bad for the day

## Key Decisions
- **No touch display** — LCD touch draws 200–500mA, kills solar viability; e-ink + physical buttons chosen
- **Use owned ESP32 dev board** — C3 or S3, sufficient GPIOs, no extra purchase needed
- **No red/black/white e-ink** — slow refresh; use WS2812B LED for colour alerts instead
- **LiFePO4 chemistry** — safer than Li-ion, tolerates partial charge, better cold performance
