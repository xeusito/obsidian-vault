
## Components (on hand)
- **Raspberry Pi 4** — dedicated to this project. Runs the scanner daemon + Phase 2 web app. More RAM than Pi 3, same GPIO layout.
- **Honeywell USB-A barcode scanner** — HID-mode (emulates keyboard + Enter). Plugs directly into a Pi USB port, no drivers.
- **BigTreeTech TFT50 v2.1** — 5" touch display (800×480). Connects via ribbon cable to the Pi DSI port, works out of the box. Replaces the SSD1306 OLED — much more real estate, touch input opens up richer interactions (confirm/reject scans, browse unknown queue on-device, host Phase 2 web UI locally). No need to order a separate OLED.
- **Govee 4-pin RGB LED strip** — on hold. Visual feedback handled entirely by the TFT50 (full-screen colour flash + message). May revisit for distance-visible status in a later phase.
- **Passive buzzer module (3-pin PCB: S / VCC / -)** — acoustic feedback. S → GPIO (PWM), middle pin → 3.3V, `-` → GND. Driven directly, no amp needed.

## Components (to order)
- **(Later) Raspberry Pi camera module v2 or v3** — Phase 4 vision input.

> Nothing to order for the MVP. All hardware is on hand.

## Wiring (planned — finalise during Phase 1)

### Display (BTT TFT50 v2.1)
Connects via DSI ribbon cable to the Pi's CSI/DSI connector. Powers up and works without additional configuration. No I²C/SPI wiring needed.

### Passive buzzer module
| Pi pin        | Buzzer pin |
|---------------|------------|
| GPIO18 (PWM0) | S (signal) |
| 3.3V          | VCC (mid)  |
| GND           | − (GND)    |

### Scanner
USB-A port directly. Read via `evdev` from `/dev/input/event*` (device path pinned by udev rule using scanner's VID:PID).

## Mounting
TBD — goal is the kitchen counter near where groceries are unpacked. Needs:
- Clear line of sight for the scanner.
- LCD visible from standing position.
- Speaker not muffled.
- Mains power within reach.

## Network
Static IP: **192.168.0.162/24** — Gateway: 192.168.0.1, DNS: 192.168.0.1. Set via `nmtui` on the `netplan-wlan0-MoreVilla` Wi-Fi connection.

## Power
Pi 4 + scanner + display fit comfortably within a 3A USB-C supply.

## Open questions
- Govee strip input voltage (5V or 12V)? Affects PSU choice.
- Scanner trigger style (auto-sense on presentation, or trigger-button)? Changes physical mounting.
- Final speaker placement — inside an enclosure resonates well but can muffle; a small opening or mesh grille helps.
