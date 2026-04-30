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
| Screen             | Description                                           |
|--------------------|-------------------------------------------------------|
| `idle`             | Dark — "Ready — scan a product". Tap → menu.          |
| `lookup`           | Dark — "Looking up…" while OpenFoodFacts query runs   |
| `known_ok`         | Green — product name + brand/qty. Auto-idle after 3s  |
| `known_err`        | Yellow — name + "not added". Auto-idle after 3s       |
| `already_in_list`  | Yellow — "Already in shopping list" + name. Auto-idle after 3s |
| `unknown_screen`   | Red — "Unknown product". Tap anywhere → `choice`      |
| `choice`           | Auto (camera) / Use web UI buttons                    |
| `front_prompt`     | "Place front toward camera" + Take photo button       |
| `back_prompt`      | "Add back photo?" — Take back / Identify now          |
| `processing`       | "Taking photo… / Identifying…" — no buttons           |
| `result_screen`    | AI result: name, brand, qty, confidence + Accept / Try again / Web UI |
| `confirmed`        | Green — "Added to Bring!". Auto-idle after 2s         |
| `webui_hint`       | Shows IP address + "Back to main menu" button         |
| `menu`             | Shopping List / Restart / Close / Cancel buttons      |
| `list_loading`     | Dark — "Loading list…" or "Removing…" — no buttons    |
| `list_view`        | Dark — paginated Bring! items (4 per page; name + description with dynamic font sizing), ✕ per row, **+** in top-right opens `manual_input`, Prev/Back/Next footer |
| `manual_input`     | Dark — header with × close + name field + optional description field + chip row (recents *or* autocomplete) + 3-layer virtual keyboard |

### Scanner gating
`handle_barcode()` is a no-op unless `screen` is `idle`, `known_ok`, `known_err`, `already_in_list`, or `menu`. This prevents the barcode scanner from interrupting the touchscreen identification flow, the shopping-list browse view, or the on-device manual entry keyboard.

### Manual entry on the touchscreen (`manual_input`)
Tapping the **+** button in the top-right of the shopping-list view opens an on-device entry screen with a virtual QWERTY keyboard. Most items typed manually are repeats (milk, bread…) so the screen has three layers of effort:

1. **Recents row** — when the name field is empty, the chip row shows the last 8 unique names from `data/manual_items.jsonl` (most-recent first). One tap fills the name (and description, if the recent entry had one) → tap **Add** to submit.
2. **Autocomplete** — once you start typing, the same chip row swaps to up to 3 prefix-matches from history. `to` → `tomatoes`, `toilet paper`, …
3. **Full keyboard** — fallback for genuinely new items.

Keyboard layout is built every render by `_build_keyboard(layer, shift)` and has three layers, toggled by the `123` / `äöü` / `abc` keys on the bottom row:

| Layer     | Row 1                       | Row 2                    | Row 3 (between Shift & ⌫) |
|-----------|-----------------------------|--------------------------|----------------------------|
| `letters` | q w e r t y u i o p         | a s d f g h j k l        | z x c v b n m              |
| `numbers` | 1 2 3 4 5 6 7 8 9 0         | - / : ; ( ) € & @        | ' , . ? ! - "              |
| `accents` | ä ö ü ß á é í ó ú ñ         | Ä Ö Ü À É Í Ó Ú Ñ        | ç ¿ ¡ - ' , .              |

Bottom row is fixed across layers: layer-1 toggle, layer-2 toggle, space, **Add**. **Shift** is sticky-one-shot — pressing it uppercases the next single alpha keypress, then auto-clears.

#### Description field
Tapping `+ desc` in the input area expands a second input row below the name. Field focus follows taps; `active_field` (`name` | `desc`) governs which field receives keystrokes. Empty descriptions are dropped from the HA payload entirely. Recents that carry a non-empty description auto-expand the desc row when their chip is tapped, so what's about to be submitted is always visible.

#### Submit & dup-check
**Add** runs `_do_manual_add(name, desc)` in a daemon thread:
1. Strip; skip if name is empty.
2. Fetch the current Bring! list via `todo.get_items?return_response`. Case-insensitive equality on `summary` → if present, show `already_in_list` (yellow, 2 s), then return to a freshly-fetched list view.
3. Otherwise `POST todo.add_item` with `{entity_id, item: name, description?: desc}`. On success, append `{name, desc, ts}` to `manual_items.jsonl`, flash `confirmed` for 1.5 s, return to a refreshed list view.
4. On HA error, drop back to `manual_input` with the user's typed text intact so they can retry.

Dup matching ignores description — only the name is compared.

#### Long-press to delete a suggestion
Long-pressing any chip (≥ 0.5 s, threshold `LONG_PRESS_S`) toggles **delete mode**. Each chip then renders a red **×** badge in its top-right corner. Tapping a × deletes every entry matching that name (case-insensitive) from `manual_items.jsonl` and refreshes the recents/autocomplete; the screen stays in delete mode so you can prune several in a row. Any other tap (chip body — also fills the field, keyboard key, input field focus, +desc toggle, header close) exits delete mode.

Long-press detection is implemented at the main-loop level: `MOUSEBUTTONDOWN` records a timestamp; `MOUSEBUTTONUP` computes `duration` and passes it to `handle_touch(pos, duration)`. All non-chip screens ignore the `duration` argument so behaviour elsewhere is unchanged.

#### Recents data file (`data/manual_items.jsonl`)
Append-only log; one JSON line per successful manual add:
```
{"name": "Bananas",   "desc": "",       "ts": "2026-04-30T14:22:11.302Z"}
{"name": "Deodorant", "desc": "Nelson", "ts": "2026-04-30T18:10:08.117Z"}
```
`_load_manual_history()` reads this file in reverse (most-recent first), dedupes by lower-case name (latest entry's `desc` wins), and returns up to 8 dicts. `_suggest(prefix, history)` is a case-insensitive prefix-match returning the top 3.

### Shopping list rendering
The list view shows up to **4 rows per page** (78 px tall), each rendering both the item name (bold) and — if present — its description below in a smaller non-bold light-grey font. Names walk down 32 → 28 → 24 → 20 px and descriptions 22 → 20 → 18 → 16 px via `_fit_font(text, max_w, sizes, bold)` — the largest size that fits the available width is picked; if none fit, the smallest is used and the text is truncated with "…". Single-line items (no description) are vertically centred in their row. Fonts are cached by `(size, bold)` in `_font_cache` so repeated re-renders are cheap.

Both barcode-scanned items (where the description carries `brand • quantity` from OpenFoodFacts) and manually-added items with a description are rendered the same way.

### Inactivity → return-to-idle
The display backlight already cuts at 30 s of inactivity (`BLANK_TIMEOUT`, via `vcgencmd display_power 0`). On top of that, after `IDLE_RETURN_TIMEOUT = 90 s` of inactivity, the daemon resets transient screens (`list_view`, `manual_input`, `menu`, `webui_hint`) back to `idle` and clears their state (typed text, current page, etc.). This follows the kiosk/POS convention rather than the phone "wake to last screen" pattern — see the *Key Decisions* in `index.md`.

The check sits in the main loop next to the blank-screen check; it's self-limiting because once the screen flips to `idle` the condition no longer matches `IDLE_RETURN_FROM`. Mid-flow screens (Gemini photo capture, scan-result) are deliberately excluded — bouncing out mid-photo would be jarring.

### Duplicate-add detection
`add_to_bring()` returns one of `"added"`, `"duplicate"`, or `"error"`. Before any `todo.add_item` call, the daemon fetches the active Bring! list via `todo.get_items?return_response` and case-insensitively compares the trimmed product name against each `summary`. If it already exists the scanner shows `already_in_list` (yellow, 3 s) instead of adding a second copy. If the list fetch fails the add proceeds anyway — better to risk a duplicate than block the user when HA is momentarily unreachable.

The Gemini-identification flow (`_do_confirm`) treats a duplicate as a successful identification: the barcode → name mapping is still saved to `custom_barcodes.json` and the photo is still uploaded to OpenFoodFacts, so future re-scans of the same barcode hit the duplicate path instantly without a Gemini call.

### Shopping list view
Tap the screen → menu → **Shopping List**. The daemon calls `todo.get_items` and renders a paginated list (5 items per page) of active Bring! entries. Each row has a red **X** button that calls `todo.remove_item` (by `uid`, falling back to `summary`) and refreshes the list in place. Footer: Prev / Back / Next. Useful for both checking before scanning ("is milk already on the list?") and undoing accidental scans without reaching for a phone.

### Barcode resolution order
1. Check `custom_barcodes.json` — if found, dup-check then add to Bring! (no OFF lookup).
2. Query OpenFoodFacts v2: `GET https://world.openfoodfacts.org/api/v2/product/{barcode}.json`
3. On hit: extract name (DE → ES → EN → `product_name` → any `product_name_*` field → brand fallback), dup-check, then add to Bring! with brand + quantity as description.
4. On miss: append `{barcode, timestamp}` to `unknown.jsonl`, show `unknown_screen`.

### HA integration
Three `todo` services on `todo.shopping` (friendly name "Bring!", config entry `01JB51G7N4TRZ6CX5J1QMXT2Z9`), all authenticated with the long-lived token from `.env`:

```http
POST {HA_URL}/api/services/todo/add_item
{ "entity_id": "todo.shopping", "item": "<product name>",
  "description": "<brand> • <quantity>" }

POST {HA_URL}/api/services/todo/get_items?return_response
{ "entity_id": "todo.shopping" }
# → { "service_response": { "todo.shopping": { "items": [
#       {"uid": "...", "summary": "Milk", "status": "needs_action"}, …
#     ] } } }

POST {HA_URL}/api/services/todo/remove_item
{ "entity_id": "todo.shopping", "item": "<uid or summary>" }
```

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

Flask app on port 5000, LAN-only. Two views + a control endpoint:

1. **`/unknown`** — lists unresolved entries from `unknown.jsonl`. Type a name and hit "Add to Bring!" → calls HA, removes from queue, saves to `custom_barcodes.json`. "Dismiss" removes without adding. AI identification is done from the touchscreen, not here.
2. **`/custom`** — full CRUD editor for `custom_barcodes.json`. Add, **Edit** (inline name change), and Delete. Used for pre-printed barcodes on bulk/unlabelled items (coffee jar, flour tin, etc.).
3. **`POST /shutdown`** — invoked by the HA `rest_command.shutdown_grocery_scanner_pi` when the user taps the *Shutdown Pi* button on the thermal-warning push notification. Requires `Authorization: Bearer <HA_TOKEN>`; runs `sudo shutdown -h now` and returns 202.

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
- **Mode:** USB PC Keyboard, Switzerland keyboard layout — programmed by scanning barcodes from the [[Files/Scanner/sps-ppr-7580-qs.pdf|Honeywell 7580 quick-start guide]]:
  1. USB PC Keyboard (p.7)
  2. Program Keyboard Country (p.8)
  3. 6 — Switzerland (p.13)
  4. Save (p.8)
- **Device path:** `/dev/input/by-id/usb-Honeywell_Imaging___Mobility_7580_18362B50A8-event-kbd`
- **evdev grab:** daemon exclusively grabs the device so keystrokes don't leak to the desktop.

---

## Thermal monitoring (`tempmon.py` + systemd timer)

The Pi sits directly behind the BTT TFT50 inside the SKADIS-mounted enclosure with no aluminium passive case, only stick-on heatsinks. The thermal monitor gives visibility plus a hard safety cut-off.

### `tempmon.py`
Reads `/sys/class/thermal/thermal_zone0/temp` (millidegrees → °C, one decimal), POSTs to HA's REST API to update `input_number.grocery_scanner_pi`, and runs `sudo /sbin/shutdown -h now` if temp ≥ 80 °C. One-shot script, fired by a systemd timer; no long-running daemon.

```python
POST {HA_URL}/api/services/input_number/set_value
Authorization: Bearer {HA_TOKEN}
{ "entity_id": "input_number.grocery_scanner_pi", "value": <float> }
```

### systemd units (`/etc/systemd/system/`)
- `grocery-tempmon.service` — `Type=oneshot`, runs the script as `pi`.
- `grocery-tempmon.timer` — `OnBootSec=30s`, `OnUnitActiveSec=30s` → fires every 30 s.

30 s sampling means HA's `numeric_state ... for: 00:01:00` debounce requires at least 2 consecutive high samples before notifying — single-sample CPU-burst spikes are filtered out.

### sudoers (`/etc/sudoers.d/grocery-scanner-shutdown`)
```
pi ALL=(ALL) NOPASSWD: /sbin/shutdown
```
Lets `tempmon.py` and the webapp's `/shutdown` route halt the Pi without a password.

### HA side
- Helper: `input_number.grocery_scanner_pi` (0–100, °C, mode `box`).
- `rest_command.shutdown_grocery_scanner_pi` → `POST http://192.168.0.162:5000/shutdown` with the long-lived token (stored in `secrets.yaml`).
- Automation **Grocery Scanner Pi — thermal alerts** (`automation.grocery_scanner_pi_thermal_alerts`) — single automation, three triggers dispatched by `trigger.id`:
  - `warning` — `> 70 °C for 1 min` → notification (`notify.mobile_app_oneplus`) with a *Shutdown Pi* action button (`action: SHUTDOWN_GROCERY_PI`).
  - `critical` — `> 80 °C` → informational notification (Pi is already shutting itself down).
  - `shutdown_action` — `mobile_app_notification_action` event → fires `rest_command.shutdown_grocery_scanner_pi` and confirms.
- All three notifications share `tag: grocery_pi_thermal` so a follow-up replaces the previous one on the OnePlus.

```yaml
# secrets.yaml  (NOTE the literal "Bearer " prefix — required by webapp.py)
grocery_scanner_pi_token: "Bearer eyJhbGciOi…<long-lived token>…"

# configuration.yaml
rest_command:
  shutdown_grocery_scanner_pi:
    url: "http://192.168.0.162:5000/shutdown"
    method: POST
    headers:
      Authorization: !secret grocery_scanner_pi_token
```

> **Gotcha:** the Pi's `/shutdown` route does an exact-string compare (`auth == "Bearer <HA_TOKEN>"`). YAML can't concatenate `"Bearer "` with `!secret` inline, so the secret value itself must include the prefix. After editing `secrets.yaml`, reload via **Dev Tools → YAML → "REST commands"** (the big "Quick Reload" button does **not** include rest_commands).

---

## Phase 4 — Additional inputs
1. **Pre-printed barcodes** — Code-128 label sheet for bulk/unlabelled items (coffee jar, flour tin, etc.). Entries managed via the `/custom` web UI; resolved on first scan and stored in `custom_barcodes.json` so the scanner recognises them instantly.
2. **NFC reader** (PN532) — never installed; pre-printed barcodes covered all the unlabelled items in practice.

---

## Reference Links
- [OpenFoodFacts API v2 docs](https://openfoodfacts.github.io/openfoodfacts-server/api/)
- [HA `todo` domain services](https://www.home-assistant.io/integrations/todo/)
- [HA Bring! integration](https://www.home-assistant.io/integrations/bring/)
- [python-evdev](https://python-evdev.readthedocs.io/)
- [[Files/Scanner/sps-ppr-7580-qs.pdf|Honeywell 7580 Quick Start Guide]] — local PDF (vendor manual; configuration barcodes for keyboard mode + country layout)
