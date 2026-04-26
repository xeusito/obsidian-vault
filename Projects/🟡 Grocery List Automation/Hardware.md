
## Components (on hand)
- **Raspberry Pi 3** — dedicated to this project. Runs the scanner daemon + Phase 2 web app.
- **Honeywell USB-A barcode scanner** — HID-mode (emulates keyboard + Enter). Plugs directly into a Pi USB port, no drivers.
- **Govee 4-pin RGB LED strip** — to be cut to 2–3 LEDs for status feedback. Common-anode, driven via GPIO + MOSFETs.
- **Old TV 2-wire speaker** — acoustic feedback. Needs a small audio amp between Pi GPIO and the speaker.

## Components (to order)
- **SSD1306 OLED 128×64 (I²C)** — for text feedback (resolved product name, unknown/error messages). ~€5.
- **PAM8302 mono amp module** — drives the speaker from a Pi PWM pin. ~€3.
- **3× logic-level N-channel MOSFETs** (e.g., 2N7000 or AO3400) — one per RGB channel for the LED strip.
- **Resistors** — gate pull-downs (10kΩ) + current limiting as needed.
- **Breadboard + jumper wires** — prototyping.
- **(Later) Raspberry Pi camera module v2 or v3** — Phase 4 vision input.

## Wiring (planned — finalise during Phase 1)

### LED strip (RGB via MOSFETs)
| Pi GPIO | MOSFET gate | Channel |
|---------|-------------|---------|
| GPIO17  | Q1          | Red     |
| GPIO27  | Q2          | Green   |
| GPIO22  | Q3          | Blue    |

Strip common (12V or 5V depending on Govee model — **verify before wiring**) to external supply; drains to MOSFETs; sources tied to GND.

### LCD (I²C)
| Pi pin   | OLED pin |
|----------|----------|
| 3.3V     | VCC      |
| GND      | GND      |
| GPIO2 (SDA) | SDA   |
| GPIO3 (SCL) | SCL   |

### Speaker + amp
| Pi pin          | PAM8302 pin |
|-----------------|-------------|
| GPIO18 (PWM0)   | IN+         |
| GND             | IN− / GND   |
| 5V              | VCC         |

Speaker on PAM8302 output terminals.

### Scanner
USB-A port directly. Read via `evdev` from `/dev/input/event*` (device path pinned by udev rule using scanner's VID:PID).

## Mounting
TBD — goal is the kitchen counter near where groceries are unpacked. Needs:
- Clear line of sight for the scanner.
- LCD visible from standing position.
- Speaker not muffled.
- Mains power within reach.

## Power
Pi 3 + scanner + LCD + amp + 2–3 LEDs fit comfortably within a 2.5A USB-C supply. LED strip power depends on the Govee model's voltage — if it's 12V the strip needs its own small supply; if 5V it can share the Pi's rail with a beefier PSU.

## Open questions
- Govee strip input voltage (5V or 12V)? Affects PSU choice.
- Scanner trigger style (auto-sense on presentation, or trigger-button)? Changes physical mounting.
- Final speaker placement — inside an enclosure resonates well but can muffle; a small opening or mesh grille helps.
