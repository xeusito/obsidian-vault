
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
Mounted on the kitchen IKEA SKADIS pegboard — see [[Files/Mounting/Wall_mount.jpg|wall mount photo]] and [[Files/Mounting/scanner_placement.jpg|scanner placement photo]]. The Pi 4 + TFT50 + camera live inside a 3D-printed enclosure (see `Files/Enclosure/`) that clips onto SKADIS via the printed pegs and connector plate. The Honeywell scanner sits in its stand within easy reach of where groceries are unpacked.

The enclosure design is by **Ioannis Giannakas** — *Raspberry Pi 3B with BTT TFT50 screen enclosure (KL-style)*, [printables.com/model/810131](https://www.printables.com/model/810131-raspberry-pi-3b-with-btt-tft50-screen-enclosure-kl). Originally for the Pi 3B; fits the Pi 4 unchanged.

## Network
Static IP: **192.168.0.162/24** — Gateway: 192.168.0.1, DNS: 192.168.0.1. Set via `nmtui` on the `MoreVilla` Wi-Fi connection.

NetworkManager (Bookworm-and-later default — `wpa_supplicant.conf` no longer used). Edit the connection via `nmcli`, not text files.

### Wi-Fi reliability tuning
The Pi sits on the kitchen pegboard, far from the router. 5 GHz signal there is borderline (-72 to -75 dBm with `Tx excessive retries:20`), so the connection is locked to 2.4 GHz where attenuation is much lower. Combined with disabling Wi-Fi power save (which used to drop long-lived TCP connections to HA every few minutes), the link is now stable.

```bash
# Lock connection to 2.4 GHz only (router broadcasts MoreVilla on both bands;
# this prevents the Pi from drifting back to weaker 5 GHz):
sudo nmcli connection modify MoreVilla 802-11-wireless.band bg

# Clear any pinned BSSID so the profile is free to associate with whichever
# 2.4 GHz AP under the same SSID has the strongest signal:
sudo nmcli connection modify MoreVilla 802-11-wireless.bssid ""

# Disable Wi-Fi power management (0=default, 1=ignore, 2=disable, 3=enable):
sudo nmcli connection modify MoreVilla 802-11-wireless.powersave 2

# Auto-reconnect with infinite retries (default is 4 attempts then gives up):
sudo nmcli connection modify MoreVilla connection.autoconnect yes
sudo nmcli connection modify MoreVilla connection.autoconnect-priority 100
sudo nmcli connection modify MoreVilla connection.autoconnect-retries 0

# Apply changes:
sudo systemctl restart NetworkManager
```

Verify:
```bash
iwconfig wlan0 | grep -E 'Frequency|Signal'    # expect Frequency:2.4xx GHz
nmcli -g connection.autoconnect connection show MoreVilla    # yes
nmcli connection show MoreVilla | grep -i 'band\|powersave\|autoconnect'
```

> **Gotcha:** `sudo nmcli connection modify MoreVilla 802-11-wireless.band bg` on its own can leave a stale BSSID pinned to the previous 5 GHz AP MAC (`48:A9:8A:C1:93:90`), making the saved profile fail to find a match — appears as "asks for password again" in the Wi-Fi UI. Always clear `bssid ""` alongside band changes.

> **If the router only broadcast `MoreVilla` on 5 GHz** (it doesn't, but for diagnosis): the band lock would have no AP to match. Confirm with `nmcli -f SSID,FREQ device wifi list | grep -i more`.

Signal strength is monitored continuously via the Netdata `wifi_signal_low` alert — see Software.md → Monitoring.

## Power
Pi 4 + scanner + display fit comfortably within a 3A USB-C supply.
