# Software

## Stack
- ESPHome 2026.4.1 — built-in `ld2450` component
- Home Assistant — native API integration
- HLKRadarTool (Android) — zone configuration over Bluetooth

## ESPHome Config

```yaml
esphome:
  name: hallway-presence
  friendly_name: Hallway Presence

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:

api:
  encryption:
    key: "<stored in secrets>"

ota:
  - platform: esphome
    password: "<stored in secrets>"

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Hallway Fallback Hotspot"
    password: "<fallback>"

captive_portal:

uart:
  id: ld2450_uart
  tx_pin: GPIO17
  rx_pin: GPIO16
  baud_rate: 256000
  parity: NONE
  stop_bits: 1

ld2450:
  uart_id: ld2450_uart
  id: ld2450_radar

binary_sensor:
  - platform: ld2450
    ld2450_id: ld2450_radar
    has_target:
      name: Presence
    has_moving_target:
      name: Moving
    has_still_target:
      name: Still

sensor:
  - platform: ld2450
    ld2450_id: ld2450_radar
    target_1:
      x: { name: T1 X }
      y: { name: T1 Y }
      speed: { name: T1 Speed }
      resolution: { name: T1 Resolution }
```

## Zone Configuration
Zones defined via HLKRadarTool over Bluetooth. 2 zones configured to cover the hallway, excluding adjacent doorways. Zones are stored in LD2450 flash and survive ESP32 reboots and OTA updates. ESPHome does not push zone coordinates, so the app-defined zones remain authoritative.

## Lessons Learned
- **CP2102 driver required on Windows** — ESPHome reports "UNKNOWN device" if the Silicon Labs CP210x driver isn't installed. Install it first; no manual bootloader mode needed.
- **`throttle` removed** in ESPHome 2026.x — the `ld2450` component no longer accepts `throttle`; use per-sensor filters instead.
- **`distance_resolution` renamed to `resolution`** in the target sensor block.
- **Avoid trial firmware** on the LD2450 — trial builds (e.g. `2.14.25112412`) expire and lock the app behind an authorization code gate with no public .bin available.
- **HLKRadarTool baud rate** — leave at 256000 to match ESPHome. Changing it in the app breaks communication.

## Reference Links
- [ESPHome LD2450 component](https://esphome.io/components/sensor/ld2450/)
- [LD2450 Serial Protocol PDF](https://make.net.za/wp-content/datasheets/HLK%20LD2450%20Serial%20Communication%20Protocol%20v1.03.pdf)
- [Hi-Link Download Center](https://hlktech.net/index.php?id=download-center)
- [TillFleisch ESPHome-HLK-LD2450 (alternative with convex polygon zones)](https://github.com/TillFleisch/ESPHome-HLK-LD2450)
