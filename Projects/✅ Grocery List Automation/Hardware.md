
## Components
- **Raspberry Pi 4** — dedicated to this project. Runs the scanner daemon + web app. Stick-on heatsinks on CPU/RAM/USB controller (passive aluminium case dropped to fit the enclosure).
- **Honeywell 7580 USB barcode scanner** — HID-mode (emulates keyboard + Enter). Plugs directly into a Pi USB port, no drivers. Configured for Switzerland keyboard layout via the quick-start barcodes.
- **BigTreeTech TFT50 v2.1** — 5" touch display (800×480). Connects via ribbon cable to the Pi DSI port, works out of the box. Replaced the originally planned SSD1306 OLED — much more real estate, touch input opens up richer interactions (confirm/reject scans, browse unknown queue on-device).
- **Raspberry Pi camera module** — wired to the Pi CSI port; used by `vision.py` for Gemini AI product identification when the barcode isn't in OpenFoodFacts.

## Wiring

### Display (BTT TFT50 v2.1)
DSI ribbon cable to the Pi's DSI connector. Powers up and works without additional configuration. No I²C/SPI wiring needed.

### Camera
CSI ribbon cable to the Pi's camera connector. Captured via `rpicam-jpeg`.

### Scanner
USB-A port directly. Read via `evdev` from `/dev/input/by-id/usb-Honeywell_Imaging___Mobility_7580_18362B50A8-event-kbd` (path pinned by-id, exclusively grabbed by the daemon).

## Mounting
Mounted on the kitchen IKEA SKADIS pegboard — see [[Files/Mounting/Wall_mount.jpg|wall mount photo]] and [[Files/Mounting/scanner_placement.jpg|scanner placement photo]]. The Pi 4 + TFT50 + camera live inside a custom 3D-printed enclosure (see `Files/Enclosure/`) that clips onto SKADIS via the printed pegs and connector plate. The Honeywell scanner sits in its stand within easy reach of where groceries are unpacked.

## Network
Static IP: **192.168.0.162/24** — Gateway: 192.168.0.1, DNS: 192.168.0.1. Set via `nmtui` on the `netplan-wlan0-MoreVilla` Wi-Fi connection.

## Power
Pi 4 + scanner + display fit comfortably within a 3A USB-C supply.
