---
status: in-progress
priority: high
startDate: 2026-04-22
dueDate: 2026-05-17
tags: [project, hardware, esp32, home-assistant, esphome, mmwave]
---

# Presence Detection in the Hallway

Detect presence in the hallway and switch either the ceiling (bright) light during the day or a soft glow light at night. Hands-free lighting that adapts to time-of-day — no blind-you-at-3am full brightness.

## Subpages
- [[Projects/🟢 Presence Detection in the Hallway/Hardware]] — components, wiring, wiring diagram
- [[Projects/🟢 Presence Detection in the Hallway/Software]] — ESPHome config, zone setup, lessons learned

## Resources
- [[Resources/HLK-LD2450-Instruction-Manual.pdf|HLK-LD2450 Instruction Manual]]

## Status

| Item                          | State        |
| ----------------------------- | ------------ |
| Hardware wired                | ✅ done      |
| ESPHome flashed               | ✅ done      |
| Connected to Home Assistant   | ✅ done      |
| Zones configured              | ✅ done      |
| Physical mount                | ⬜ pending   |
| Zones recalibrated after mount| ⬜ pending   |
| Pi + dashboard reinstated     | ⬜ pending   |
| HA automation built           | ⬜ pending   |
| HDMI CEC display control      | ⬜ pending   |

## Next Steps
- [ ] Mount ESP32 + LD2450 on end wall (opposite front door), ~1.5m high, powered from monitor USB port
- [ ] Redo zones in HLKRadarTool after mounting — Y axis now runs the hallway length toward the front door
- [ ] Reinstall Raspberry Pi + 27" touch display on end wall for HA dashboard
- [ ] Install `cec-utils` on Pi, expose CEC commands to HA → wake/standby display based on `has_target`
- [ ] Build HA automation: presence → ceiling light (day) / soft glow (night). Add 2 min timeout-off helper.

## Key Decisions
- **Wired (USB-C), not battery** — LD2450 draws ~80mA continuously with no sleep/wake pin; battery life would be ~30h on a 3000mAh cell.
- **Powered from monitor USB port** — 27" display has always-on USB downstream ports; powers ESP32 + LD2450 (~200mA) without any extra wiring.
- **End wall mount, not ceiling** — LD2450 on the wall opposite the front door, pointing down the hallway length. Better field of view along the full hallway axis.
- **HDMI CEC for display power** — Pi sends CEC standby/wake commands based on LD2450 presence, preserving power when hallway is empty.
- **Zones via HLKRadarTool app (Bluetooth)** — zones are stored in LD2450 flash, not ESPHome YAML, so they survive OTA updates.
- **UART2 (GPIO16/17)** — leaves UART0 free for USB flashing and logging.
