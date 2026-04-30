---
tags: [software, esphome, home-assistant]
---

# Software

[[Projects/🟡 Solar E-Ink Door Display/index|← Project Overview]]

## Stack
- **Firmware:** ESPHome
- **Integration:** Native Home Assistant (no MQTT needed)
- **Deep sleep:** Wake on timer, supported natively in ESPHome

## Behaviour Loop

```
Wake (timer, every 15–30 min)
  → Connect to Wi-Fi
  → Fetch data from HA (calendar, trash schedule, alert text)
  → Render layout on e-ink display
  → Check battery SoC via MAX17048
  → Push battery level to HA
  → Enter deep sleep
```

Button wakes also trigger a render + HA sync before sleeping again.

## Home Assistant Data Sources

| Sensor / Entity | Purpose |
|---|---|
| Calendar entity | Upcoming events shown on display |
| Template sensor — trash schedule | Next trash/recycling pickup day |
| Template sensor — alert text | Custom alert message (colour-coded via LED) |
| MAX17048 SoC | Battery % visible in HA dashboard |

## ESPHome Config (skeleton — to be built)

```yaml
esphome:
  name: door-display
  platform: ESP32
  board: esp32-s3-devkitc-1  # update to actual board

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

deep_sleep:
  run_duration: 30s
  sleep_duration: 15min

i2c:
  sda: GPIO8
  scl: GPIO9

spi:
  mosi_pin: GPIO18
  clk_pin: GPIO20

sensor:
  - platform: max17048
    battery_voltage:
      name: "Door Display Battery Voltage"
    battery_level:
      name: "Door Display Battery Level"

light:
  - platform: neopixelbus
    type: GRB
    variant: WS2812X
    pin: GPIO5
    num_leds: 1
    name: "Alert LED"

# e-ink display config — add waveshare 7.5" component
# button GPIO config — add after board pinout confirmed
```

## Next Steps
- [ ] Confirm board model → update `board:` field
- [ ] Assign button GPIOs → add `binary_sensor` entries
- [ ] Add Waveshare 7.5" display component and layout rendering
- [ ] Define HA template sensors for calendar + trash + alert
- [ ] Test deep sleep wake cycle end-to-end
- [ ] Tune wake interval based on real battery drain measurements
