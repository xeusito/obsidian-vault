# Stack
- **Python 3.11+** — scanner daemon + Phase 2 web app.
- **evdev** — read barcode keystrokes from the scanner as an input device.
- **requests / httpx** — OpenFoodFacts + Home Assistant REST calls.
- **gpiozero + RPi.GPIO / lgpio** — LED PWM + speaker tone generation.
- **luma.oled** — SSD1306 OLED driver.
- **Flask or FastAPI** (Phase 2) — local web app for unknown-barcode resolution + custom-barcode editor.
- **systemd** — daemon process management, auto-start on boot.

## Daemon architecture (Phase 1)

```
┌────────────────────────────────────────────────────────────────┐
│                     grocery-scanner daemon                      │
├────────────────────────────────────────────────────────────────┤
│  Scanner reader   →   Barcode dispatcher   →   Feedback bus    │
│  (evdev loop)          │                        ├─ LED         │
│                        ├─ Custom map lookup     ├─ LCD         │
│                        ├─ OpenFoodFacts API     └─ Speaker     │
│                        └─ HA todo.add_item                      │
│                                  ↓                              │
│                         unknown.jsonl (queue)                   │
└────────────────────────────────────────────────────────────────┘
```

### Barcode resolution order
1. Check local `custom_barcodes.json` (Phase 4 pre-printed codes, bulk items). If hit → use mapped name directly.
2. Query OpenFoodFacts v2: `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json`.
3. On hit, pick the product name using the fallback chain below.
4. On miss, append `{barcode, timestamp}` to `unknown.jsonl`, flash red LED, play unknown tone.

### Language fallback (name picker)
Priority: **DE → ES → EN → generic**.
- `product_name_de` → `product_name_es` → `product_name_en` → `product_name` → `generic_name_de` → ... → brand + quantity as a last-resort composite.

### HA integration
Call the existing Bring! integration's todo entity via the standard todo service:

```
POST {HA_URL}/api/services/todo/add_item
Authorization: Bearer {LONG_LIVED_TOKEN}
Content-Type: application/json

{"entity_id": "todo.shopping", "item": "<resolved product name>"}
```

Entity confirmed: `todo.shopping` (friendly name "Bring!", config entry `01JB51G7N4TRZ6CX5J1QMXT2Z9`).

### Feedback states
| Outcome             | LED       | LCD line                        | Speaker                  |
|---------------------|-----------|---------------------------------|--------------------------|
| Added to Bring!     | Green     | `+ <product name>`              | Single high beep         |
| Unknown barcode     | Red       | `? <barcode>`                   | Two descending low beeps |
| Network / HA error  | Amber     | `! <short error>`               | Descending buzz          |
| Idle                | Off / dim | (last message or blank)         | —                        |

### Config (`.env`)
```
HA_URL=http://homeassistant.local:8123
HA_TOKEN=<long-lived access token>
HA_TODO_ENTITY=todo.shopping
SCANNER_DEVICE=/dev/input/by-id/usb-Honeywell-....-event-kbd
OFF_USER_AGENT=grocery-scanner/0.1 (nelsonmoreira@gmail.com)
LANG_PRIORITY=de,es,en
DATA_DIR=/var/lib/grocery-scanner
```

### systemd unit (sketch)

```ini
[Unit]
Description=Grocery scanner daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/grocery-scanner
EnvironmentFile=/opt/grocery-scanner/.env
ExecStart=/opt/grocery-scanner/.venv/bin/python -m grocery_scanner
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Phase 2 — web app + HA dashboard

Two views served from the Pi on the LAN:

1. **Unknown barcodes queue** — list `unknown.jsonl` entries; form per row to name the item; on submit: add to Bring!, mark entry resolved, optionally push to OpenFoodFacts.
2. **Custom barcodes editor** — CRUD for `custom_barcodes.json` (pre-printed codes → item names for bulk / unlabelled items).

### HA dashboard embedding options
- **`panel_iframe`** (sidebar): simplest — adds a top-level sidebar link opening the web app full-frame.
- **Lovelace `iframe` card** or HACS `webpage` card: embed inline inside an existing dashboard view.

Required on the web app:
- Allow framing from the HA origin (`Content-Security-Policy: frame-ancestors <HA_URL>`; do NOT set `X-Frame-Options: DENY`).
- Rely on HA's auth at the network edge — restrict web app to LAN only; no separate login.

## Phase 3 — Local LLM (deferred)
- Audit Proxmox capacity first. Candidates: Ollama in an LXC, exposed over LAN.
- Small vision-capable model for identifying products from a Pi camera photo when the barcode lookup misses or the product has no barcode.

## Phase 4 — Additional inputs
1. **Pre-printed barcodes** — generate a sheet of Code-128 labels tied to `custom_barcodes.json` entries. Stick on coffee jars, flour tins, produce containers. Zero new hardware.
2. **Camera + vision LLM** — Pi camera v2/v3 → still capture → LLM name extraction → button-press or second-scan confirmation.
3. **NFC reader** (PN532) — deferred; only if pre-printed barcodes prove insufficient.
4. **Voice command** — lowest priority; via existing HA assistant.

## OpenFoodFacts etiquette
- Set a distinctive User-Agent (see `.env` above) — OFF asks for this so they can contact operators of buggy clients.
- Cache lookups locally (`sqlite` or a JSON file) to avoid re-hitting the API for repeat scans.
- Respect rate limits — for our volume (tens of scans/day) this is never a concern, but cache anyway.

## Reference Links
- [OpenFoodFacts API v2 docs](https://openfoodfacts.github.io/openfoodfacts-server/api/)
- [HA `todo` domain services](https://www.home-assistant.io/integrations/todo/)
- [HA Bring! integration](https://www.home-assistant.io/integrations/bring/)
- [luma.oled docs](https://luma-oled.readthedocs.io/)
- [python-evdev](https://python-evdev.readthedocs.io/)
