---
status: hardware installed, streaming to HA
started: 2026-04-22
tags: [project, hardware, esp32, home-assistant, esphome, mmwave]
---

# Presence Detection in the Hallway

Detect presence in the hallway and switch either the ceiling (bright) light during the day or a soft glow light at night. Hands-free lighting that adapts to time-of-day — no blind-you-at-3am full brightness.

## Subpages
- [[Hardware]] — components, wiring, wiring diagram
- [[Software]] — ESPHome config, zone setup, lessons learned

## Resources
- [[Resources/HLK-LD2450-Instruction-Manual.pdf|HLK-LD2450 Instruction Manual]]

## Status

| Item                        | State        |
| --------------------------- | ------------ |
| Hardware wired              | ✅ done      |
| ESPHome flashed             | ✅ done      |
| Connected to Home Assistant | ✅ done      |
| Zones configured            | ✅ done      |
| HA automation built         | ⬜ pending   |
| Physical mount / enclosure  | ⬜ pending   |

## Next Steps
- [ ] Build HA automation: presence + sun below horizon → soft glow; else → ceiling light. Add 2 min timeout-off helper.
- [ ] Tune zones if false triggers occur from adjacent rooms.
- [ ] Design and print enclosure for the ESP32 + LD2450 combo.

## Key Decisions
- **Wired (USB-C), not battery** — LD2450 draws ~80mA continuously with no sleep/wake pin; battery life would be ~30h on a 3000mAh cell.
- **Zones via HLKRadarTool app (Bluetooth)** — zones are stored in LD2450 flash, not ESPHome YAML, so they survive OTA updates.
- **UART2 (GPIO16/17)** — leaves UART0 free for USB flashing and logging.
