# Software

## Stack
- **Python 3.13** — scanner daemon (`scanner.py`) + shared vision module (`vision.py`) + web app (`webapp.py`).
- **evdev** — reads barcode keystrokes from the Honeywell 7580 as an input event device (`/dev/input/by-id/...`).
- **requests** — OpenFoodFacts v2 API + Home Assistant REST calls + OpenFoodFacts write API.
- **pygame 2.6.1** (SDL 2.32.4, X11 backend) — fullscreen touchscreen UI on the BTT TFT50 v2.1. State-machine driven; all rendering on the main thread.
- **google-genai** — Google Gemini 2.5 Flash vision API for AI product identification.
- **python-dotenv** — loads `.env` config at startup.
- **Flask** — lightweight web app for manual barcode resolution and custom-barcode editor (port 5000).
- **LXDE autostart** — starts both processes after the desktop session is ready. `while true` shell loop gives automatic restart on crash.

> systemd user service was attempted but `graphical-session.target` is not triggered by LXDE on Pi OS. LXDE autostart is more reliable for X11 apps.

## File layout (`/home/pi/grocery-scanner/`)
```
scanner.py              — barcode scanner daemon + touchscreen UI state machine
vision.py               — camera capture, Gemini AI identification, OpenFoodFacts upload
webapp.py               — Flask web UI (manual resolution + custom barcode editor)
.env                    — config (HA URL, token, device path, Gemini key, etc.)
data/
  unknown.jsonl         — unknown barcodes queue (append-only log)
  custom_barcodes.json  — barcode → name map (hand-curated + auto-saved on resolution)
templates/
  base.html
  unknown.html
  custom.html
~/Desktop/
  Start Scanner.desktop — desktop icon to restart the scanner daemon
```

Autostart entries:
```
~/.config/autostart/grocery-scanner.desktop
~/.config/autostart/grocery-webapp.desktop
```

## Daemon architecture (`scanner.py`)

State machine running on the pygame main thread. Touch events (`MOUSEBUTTONDOWN`) drive transitions between screens. All blocking calls (camera, Gemini, HA, OFF) run in daemon threads and signal the main thread to re-render via `threading.Event`.

```
┌─────────────────────────────────────────────────────────────┐
│                   grocery-scanner daemon                     │
├─────────────────────────────────────────────────────────────┤
│  evdev scanner loop  →  handle_barcode()  (daemon thread)   │
│                               │                             │
│          ┌────────────────────┴──────────────────┐          │
│          ▼                                       ▼          │
│   known product                          unknown product    │
│   add_to_bring() → green/yellow          log_unknown()      │
│   sleep 3s → idle                        screen="unknown"   │
│                                               │  tap         │
│                                          choice screen       │
│                                         Auto │  Web UI       │
│                                              ▼               │
│                               front_prompt → take photo      │
│                               back_prompt  → take back?      │
│                               processing   → Gemini          │
│                               result_screen → accept         │
│                               confirmed    → idle            │
└─────────────────────────────────────────────────────────────┘
```

### Screen states
| Screen           | Description                                           |
|------------------|-------------------------------------------------------|
| `idle`           | Dark — "Ready — scan a product". Tap → menu.          |
| `lookup`         | Dark — "Looking up…" while OpenFoodFacts query runs   |
| `known_ok`       | Green — product name + brand/qty. Auto-idle after 3s  |
| `known_err`      | Yellow — name + "not added". Auto-idle after 3s       |
| `unknown_screen` | Red — "Unknown product". Tap anywhere → `choice`      |
| `choice`         | Auto (camera) / Use web UI buttons                    |
| `front_prompt`   | "Place front toward camera" + Take photo button       |
| `back_prompt`    | "Add back photo?" — Take back / Identify now          |
| `processing`     | "Taking photo… / Identifying…" — no buttons           |
| `result_screen`  | AI result: name, brand, qty, confidence + Accept / Try again / Web UI |
| `confirmed`      | Green — "Added to Bring!". Auto-idle after 2s         |
| `webui_hint`     | Shows IP address + "Back to main menu" button         |
| `menu`           | Restart / Close / Cancel buttons                      |

### Scanner gating
`handle_barcode()` is a no-op unless `screen` is `idle`, `known_ok`, or `known_err`. This prevents the barcode scanner from interrupting the touchscreen identification flow.

### Barcode resolution order
1. Check `custom_barcodes.json` — if found, add to Bring! immediately (no network lookup).
2. Query OpenFoodFacts v2: `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json`
3. On hit: extract name (DE → ES → EN → `product_name` → any `product_name_*` field → brand fallback), add to Bring! with brand + quantity as description.
4. On miss: append `{barcode, timestamp}` to `unknown.jsonl`, show `unknown_screen`.

### HA integration
```
POST {HA_URL}/api/services/todo/add_item
Authorization: Bearer {LONG_LIVED_TOKEN}
Content-Type: application/json

{
  "entity_id": "todo.shopping",
  "item": "<product name>",
  "description": "<brand> • <quantity>"
}
```
Entity: `todo.shopping` (friendly name "Bring!", config entry `01JB51G7N4TRZ6CX5J1QMXT2Z9`).

### Config (`.env`)
```
HA_URL=http://homeassistant.local:8123
HA_TOKEN=<long-lived access token>
HA_TODO_ENTITY=todo.shopping
SCANNER_DEVICE=/dev/input/by-id/usb-Honeywell_Imaging___Mobility_7580_18362B50A8-event-kbd
LANG_PRIORITY=de,es,en
DATA_DIR=/home/pi/grocery-scanner/data

# Phase 3 — AI vision
GEMINI_API_KEY=<Google AI Studio API key>

# Phase 3 — OpenFoodFacts contribution (optional)
OFF_USER=<OpenFoodFacts username>
OFF_PASSWORD=<OpenFoodFacts password>
```

### Autostart entries
```ini
# ~/.config/autostart/grocery-scanner.desktop
[Desktop Entry]
Type=Application
Name=Grocery Scanner
Exec=bash -c 'while true; do python3 /home/pi/grocery-scanner/scanner.py; sleep 5; done'
X-GNOME-Autostart-enabled=true

# ~/.config/autostart/grocery-webapp.desktop
[Desktop Entry]
Type=Application
Name=Grocery Scanner Web App
Exec=bash -c 'sleep 10; while true; do python3 /home/pi/grocery-scanner/webapp.py; sleep 5; done'
X-GNOME-Autostart-enabled=true
```

### Desktop icon
`~/Desktop/Start Scanner.desktop` — kills any running scanner instance and starts a fresh one. Used after closing the scanner via the on-screen menu.

---

## Vision module (`vision.py`) — Phase 3

Shared module imported by `scanner.py`. Isolates all AI and camera logic.

### `capture_photo(path)`
Runs `rpicam-jpeg --nopreview -t 2000 --width 1280 --height 960 -o {path}`. Returns `(ok, error_string)`.

### `identify_with_gemini(paths)`
Accepts a list of 1–2 image paths (front + optional back). Sends all photos in one API call to **Gemini 2.5 Flash** with a structured JSON prompt. Returns `(result_dict, error_string)`.

Result dict: `{name, brand, quantity, confidence}`.

JSON parsing is robust: direct parse → strip markdown fences → regex extract → fix unquoted keys.

### `upload_to_openfoodfacts(barcode, name, brand, quantity, front_path)`
Contributes the identified product back to the OpenFoodFacts database. Requires `OFF_USER` and `OFF_PASSWORD` in `.env`. Silently skipped if credentials are absent. Photo upload is non-fatal — product data is submitted even if the image upload fails.

Endpoints used:
- `POST https://world.openfoodfacts.org/cgi/product_jqm2.pl` — product data
- `POST https://world.openfoodfacts.org/cgi/product_image_upload.pl` — front photo

---

## Web app (`webapp.py`) — Phase 2

Flask app on port 5000, LAN-only. Two views:

1. **`/unknown`** — lists unresolved entries from `unknown.jsonl`. Type a name and hit "Add to Bring!" → calls HA, removes from queue, saves to `custom_barcodes.json`. "Dismiss" removes without adding. AI identification is done from the touchscreen, not here.
2. **`/custom`** — full CRUD editor for `custom_barcodes.json`. Add, **Edit** (inline name change), and Delete. Used for pre-printed barcodes on bulk/unlabelled items (coffee jar, flour tin, etc.).

### HA dashboard integration
HA runs on HTTPS; browsers block HTTP iframes (mixed content). Solution: button card that opens the web UI in a new tab.

```yaml
type: button
name: Open Web UI
icon: mdi:barcode-scan
tap_action:
  action: url
  url_path: http://192.168.0.162:5000
```

---

## Scanner setup notes
- **Mode:** USB PC Keyboard, Switzerland keyboard layout — programmed by scanning barcodes from the Honeywell 7580 quick-start guide (`sps-ppr-7580-qs.pdf`):
  1. USB PC Keyboard (p.7)
  2. Program Keyboard Country (p.8)
  3. 6 — Switzerland (p.13)
  4. Save (p.8)
- **Device path:** `/dev/input/by-id/usb-Honeywell_Imaging___Mobility_7580_18362B50A8-event-kbd`
- **evdev grab:** daemon exclusively grabs the device so keystrokes don't leak to the desktop.

---

## Phase 4 — Additional inputs (planned)
1. **Pre-printed barcodes** — generate Code-128 label sheet for bulk/unlabelled items. Entries managed via the `/custom` web UI. Zero new hardware.
2. **NFC reader** (PN532) — deferred; only if pre-printed barcodes prove insufficient.

---

## Reference Links
- [OpenFoodFacts API v2 docs](https://openfoodfacts.github.io/openfoodfacts-server/api/)
- [HA `todo` domain services](https://www.home-assistant.io/integrations/todo/)
- [HA Bring! integration](https://www.home-assistant.io/integrations/bring/)
- [python-evdev](https://python-evdev.readthedocs.io/)
- [Honeywell 7580 Quick Start Guide](sps-ppr-7580-qs.pdf)
