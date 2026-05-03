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

## ESPHome Config

> [!tip] Full working YAML (copy-paste ready)
> [[Files/door-display.yaml|→ door-display.yaml]] — current Phase 2 + Phase 3a config in one file.
> Plain path: `Projects/🟢 Solar E-Ink Door Display/Files/door-display.yaml`
> Update this file when changing the firmware so the canonical version always matches what's flashed.

### Phase 1 — Display smoke test (current)

Minimal config: display only. No deep sleep, no MAX17048, no LED, no buttons.
Goal: confirm e-ink refreshes and shows "Hello from ESPHome".

```yaml
esphome:
  name: door-display
  friendly_name: Door Display

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:

api:
  encryption:
    key: !secret api_encryption_key

ota:
  - platform: esphome
    password: !secret ota_password

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Door Display Fallback"
    password: !secret ap_password

captive_portal:

spi:
  clk_pin: GPIO18
  mosi_pin: GPIO23
  miso_pin: GPIO19

font:
  - file: "gfonts://Roboto"
    id: font_label
    size: 32

display:
  - platform: waveshare_epaper
    cs_pin: GPIO15
    dc_pin: GPIO17
    reset_pin: GPIO16
    busy_pin: GPIO4
    model: 7.50inv2
    rotation: 0°
    update_interval: 60s
    lambda: |-
      it.fill(COLOR_OFF);
      it.print(10, 10, id(font_label), "Hello from ESPHome");
```

**secrets.yaml** entries needed (in ESPHome `config/` folder):
```yaml
wifi_ssid: "YourSSID"
wifi_password: "YourPassword"
ap_password: "fallback123"
api_encryption_key: "<copy from working test-delete config>"
ota_password: "<copy from working test-delete config>"
```

### Phase 2 — Full display layout (current)

HA entities created: `input_text.door_display_event_1/2/3`, `input_text.door_display_alert`,
`sensor.door_display_weather`, `sensor.door_display_waste_next`.
Automation `automation.door_display_refresh_calendar_events` refreshes event slots every 15 min.

```yaml
esphome:
  name: door-display
  friendly_name: Door Display

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:

api:
  encryption:
    key: "laHKYmI3o0VLGx5NNsTtbtgzb0Z7NpdtKVtZIyXENmw="

ota:
  - platform: esphome
    password: !secret ota_password

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Door Display Fallback"
    password: !secret ap_password

captive_portal:

time:
  - platform: sntp
    id: ha_time
    timezone: "Europe/Zurich"

spi:
  clk_pin: GPIO18
  mosi_pin: GPIO23
  miso_pin: GPIO19

text_sensor:
  - platform: homeassistant
    id: ev1
    entity_id: input_text.door_display_event_1
    internal: true
  - platform: homeassistant
    id: ev2
    entity_id: input_text.door_display_event_2
    internal: true
  - platform: homeassistant
    id: ev3
    entity_id: input_text.door_display_event_3
    internal: true
  - platform: homeassistant
    id: waste_next
    entity_id: sensor.door_display_waste_next
    internal: true
  - platform: homeassistant
    id: weather_summary
    entity_id: sensor.door_display_weather
    internal: true
  - platform: homeassistant
    id: alert_text
    entity_id: input_text.door_display_alert
    internal: true

font:
  - file:
      type: gfonts
      family: Roboto
      weight: 700
    id: font_date
    size: 36
    glyphsets:
      - GF_Latin_Kernel       # PT/ES extended Latin: ã ñ ç é etc.
  - file:
      type: gfonts
      family: Roboto
      weight: 700
    id: font_body
    size: 22
    glyphsets:
      - GF_Latin_Kernel
  - file:
      type: gfonts
      family: Roboto
      weight: 700
    id: font_small
    size: 16
    glyphsets:
      - GF_Latin_Kernel
  - file:
      type: gfonts
      family: Noto Sans Symbols 2
    id: font_icon
    size: 22
    glyphs: ["⚠"]

display:
  - platform: waveshare_epaper
    cs_pin: GPIO15
    dc_pin: GPIO17
    reset_pin: GPIO16
    busy_pin: GPIO4
    model: 7.50inv2
    rotation: 0°
    update_interval: 60s
    lambda: |-
      it.fill(COLOR_OFF);

      // ── Header ────────────────────────────────────────────────
      auto now = id(ha_time).now();
      if (now.is_valid()) {
        it.strftime(10, 10, id(font_date), "%A, %d %B %Y", now);
      }
      it.print(650, 16, id(font_small), "Bat: --%");
      it.line(0, 65, 800, 65);

      // ── Upcoming events (left column) ─────────────────────────
      it.print(10, 74, id(font_small), "UPCOMING");
      it.print(10, 100, id(font_body), id(ev1).state.c_str());
      it.print(10, 132, id(font_body), id(ev2).state.c_str());
      it.print(10, 164, id(font_body), id(ev3).state.c_str());

      // ── Vertical divider ──────────────────────────────────────
      it.line(400, 65, 400, 415);

      // ── Weather (right top) ───────────────────────────────────
      it.print(412, 74, id(font_small), "WEATHER");
      it.print(412, 100, id(font_body), id(weather_summary).state.c_str());

      // ── Trash (right bottom) ──────────────────────────────────
      it.line(400, 210, 800, 210);
      it.print(412, 220, id(font_small), "TRASH");
      auto waste = id(waste_next).state;
      size_t sep = waste.find('|');
      std::string wl1 = (sep != std::string::npos) ? waste.substr(0, sep) : waste;
      std::string wl2 = (sep != std::string::npos) ? waste.substr(sep + 1) : "";
      it.print(412, 246, id(font_body), wl1.c_str());
      if (!wl2.empty()) {
        it.print(412, 278, id(font_body), wl2.c_str());
      }

      // ── Alert footer ──────────────────────────────────────────
      it.line(0, 415, 800, 415);
      auto alert = id(alert_text).state;
      if (alert.length() > 0 && alert != "unknown") {
        it.print(10, 435, id(font_icon), "⚠");
        it.printf(40, 435, id(font_body), " %s", alert.c_str());
      } else {
        it.print(10, 435, id(font_body), "No alerts");
      }
```

### Phase 3a — MAX17048 fuel gauge (current step)

Add the I²C bus and MAX17048 sensor. Two HA entities appear automatically:
`sensor.door_display_battery_voltage`, `sensor.door_display_battery_level`.

```yaml
# Add at top level, alongside spi: / display: / etc.
i2c:
  sda: GPIO21
  scl: GPIO22
  scan: true        # logs all detected I²C addresses on boot — useful for debugging

sensor:
  - platform: max17043      # NOTE: ESPHome only ships max17043 — works with MAX17048
    battery_voltage:        # too (same I²C addr 0x36, same VCELL/SOC registers).
      name: "Door Display Battery Voltage"
      id: bat_voltage
    battery_level:
      name: "Door Display Battery Level"
      id: bat_level
    update_interval: 60s
```

> [!note] Why `max17043` and not `max17048`?
> ESPHome doesn't ship a dedicated MAX17048 driver. The chips share the same
> I²C address (0x36) and the VCELL + SOC register layout, so the `max17043`
> driver reads voltage and battery % correctly from a MAX17048. You miss the
> MAX17048-only registers (rate-of-charge, time-to-empty) but those aren't
> exposed in ESPHome anyway.

Then in the display lambda, replace the placeholder line:

```cpp
// OLD:
it.print(650, 16, id(font_small), "Bat: --%");

// NEW:
if (id(bat_level).has_state()) {
  it.printf(650, 16, id(font_small), "Bat: %.0f%% (%.2fV)",
            id(bat_level).state, id(bat_voltage).state);
} else {
  it.print(650, 16, id(font_small), "Bat: --%");
}
```

**Boot-time check:** with `scan: true`, the logs should show `Found i2c device at address 0x36` (MAX17048's fixed address). If it's missing, the chip isn't seeing battery voltage on its CELL pin — re-check the JST connection.

### Phase 3b — To add after MAX17048 confirmed
- Deep sleep (`deep_sleep:` block, 15 min interval)
- WS2812B alert LED (`light: platform: neopixelbus`, GPIO25)
- Physical buttons (GPIO32/33/26/27)

## Next Steps
- [x] Confirm board model → `esp32dev`
- [x] Confirm GPIO assignments
- [x] Flash Phase 1 config → display confirmed working
- [x] HA helpers + template sensors + calendar refresh automation
- [x] Trash reminder automation updated with display alert (in Spanish)
- [x] Garbage collection calendar events added to `calendar.garbage_collection_2`
- [x] Flash Phase 2 config → confirmed working (font readability tuned: Bold 36/22/16px)
- [x] Wire MAX17048 (in-line between battery and DFR0559)
- [ ] Add MAX17048 to ESPHome YAML (Phase 3a)
- [ ] Add deep sleep (Phase 3b)
- [ ] Add buttons + LED (Phase 3b)
- [ ] Tune sleep interval based on real battery drain
