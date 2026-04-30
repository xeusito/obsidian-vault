---
status: completed
version: "1.1.1"
priority: medium
startDate: 2026-04-24
completedDate: 2026-04-30
tags: [project, raspberry-pi, home-assistant, bring, openfoodfacts, barcode]
---
# Grocery List Automation — v1.1.1 ✅

A kitchen-counter scan-and-done station that adds items to the Bring! shopping list in under 3 seconds, with zero typing for known products. A Raspberry Pi 4 with a Honeywell barcode scanner looks the product up in OpenFoodFacts and pushes it to Bring! via the existing Home Assistant integration. Unknown items can be identified on-device via the Pi camera + Gemini 2.5 Flash AI vision. The BTT TFT50 v2.1 touchscreen gives colour-coded feedback on every scan. Mounted on an IKEA SKADIS pegboard inside a custom 3D-printed enclosure.

## Subpages
- [[Hardware]] — components, wiring, network, mounting
- [[Software]] — daemon, web app, HA integration, autostart, thermal monitoring
- [[CHANGELOG]] — release notes (v1.0, v1.1, …)

## Files
- **3D-printable enclosure** — `Files/Enclosure/` · designed by **Ioannis Giannakas** ([Printables: Raspberry Pi 3B with BTT TFT50 screen enclosure (KL-style)](https://www.printables.com/model/810131-raspberry-pi-3b-with-btt-tft50-screen-enclosure-kl)). Original is for the Pi 3B; fits the Pi 4 with no modification.
  - [[Files/Enclosure/Grocery Scanner enclosure.3mf|Grocery Scanner enclosure.3mf]] — Bambu Studio project (slicer-ready)
  - [[Files/Enclosure/Body.stl|Body.stl]] — main shell housing the BTT TFT50 + Pi 4
  - [[Files/Enclosure/Rear panel.stl|Rear panel.stl]] — back cover with vents
  - [[Files/Enclosure/connectors-plate.stl|connectors-plate.stl]] — IKEA SKADIS mounting plate
  - [[Files/Enclosure/connectors-pegs.stl|connectors-pegs.stl]] — SKADIS pegs that clip the plate to the pegboard
- **Mounting photos** — `Files/Mounting/`
  - ![[Files/Mounting/Wall_mount.jpg]]
  - ![[Files/Mounting/scanner_placement.jpg]]
- **Scanner reference** — `Files/Scanner/`
  - [[Files/Scanner/sps-ppr-7580-qs.pdf|Honeywell 7580 Quick Start Guide]] — vendor PDF; contains the configuration barcodes used to set USB-PC-Keyboard mode and Switzerland keyboard layout

## Background

### Why
The shopping list is never up-to-date because adding items requires typing into a phone or the kitchen tablet. Reducing that friction is the whole point — a comprehensive list ready when it's time to shop or order groceries online.

### Constraints
OpenFoodFacts has over 3 million entries but coverage varies by language and region. The system degrades gracefully for unknowns — queued in a local log, resolved via the web UI, and saved to the custom barcode map so future scans work automatically.

### Languages
German, Spanish, English — DE → ES → EN fallback when reading product names from OpenFoodFacts.

## Status

| Item                                          | State        |
| --------------------------------------------- | ------------ |
| Plan drafted                                  | ✅ done      |
| Project folder scaffolded                     | ✅ done      |
| Pi 4 dedicated + on static IP                 | ✅ done      |
| Honeywell USB-A scanner (kbd mode)            | ✅ done      |
| BTT TFT50 v2.1 display (DSI)                 | ✅ done      |
| HA long-lived access token                    | ✅ done      |
| Phase 1 — scanner daemon                      | ✅ done      |
| Phase 1 — LXDE autostart + reboot            | ✅ done      |
| Phase 2 — unknown barcode web UI              | ✅ done      |
| Phase 2 — custom barcode editor (+ inline edit) | ✅ done   |
| Phase 2 — HA dashboard button                 | ✅ done      |
| Phase 3 — Pi camera input                     | ✅ done      |
| Phase 3 — AI vision (Gemini 2.5 Flash)        | ✅ done      |
| Phase 3 — Touchscreen identification flow     | ✅ done      |
| Phase 3 — OpenFoodFacts contribution upload   | ✅ done      |
| Phase 3 — On-screen menu (Restart / Close)    | ✅ done      |
| Phase 3 — Desktop icon to restart scanner     | ✅ done      |
| Phase 3 — Screen auto-blank after 30 s idle   | ✅ done      |
| Phase 3 — CPU temp monitor + HA alerts        | ✅ done      |
| Phase 4 — Pre-printed barcodes                | ✅ done      |
| Phase 5 — 3D-printed case (screen + Pi)       | ✅ done      |
| Phase 5 — Camera case (print or source)       | ✅ done      |
| Phase 5 — Print case(s)                       | ✅ done      |
| Phase 5 — Mount project in kitchen            | ✅ done      |
| v1.1 — Shopping list view + delete on device  | ✅ done      |
| v1.1 — Duplicate-add detection                | ✅ done      |
| v1.1 — Manual entry on touchscreen (keyboard, recents, autocomplete, optional desc) | ✅ done |
| v1.1 — Inactivity → return to idle (90 s)     | ✅ done      |
| v1.1.1 — Long-press to delete suggestions     | ✅ done      |
| v1.1.1 — Description on shopping-list rows + dynamic font sizing | ✅ done |

## Next Steps
_None — project shipped at v1.0 on 2026-04-30._

## Credentials
- SSH user `pi` password for `192.168.0.162` is stored in **Bitwarden**.

## Key Decisions
- **Sync via HA `todo.shopping` entity** — Bring! integration already loaded in HA. One `todo.add_item` call, brand + quantity in the `description` field (maps to Bring!'s "Quantity, description…" field in the Android app).
- **Display-only feedback** — BTT TFT50 full-screen colour flash + status text handles every scan outcome. The originally planned buzzer and RGB LED strip were dropped — the display alone is more informative and visible from across the kitchen.
- **LXDE autostart over systemd user service** — `graphical-session.target` not triggered by LXDE on Pi OS; autostart fires reliably after X11 is ready.
- **Static IP (192.168.0.162) over mDNS** — `.local` hostname unreliable on this network.
- **HA button card over iframe** — HA runs on HTTPS; browsers block HTTP iframes (mixed content). Button card opens the web UI in a new tab.
- **Custom barcode map as learning layer** — resolving an unknown via the web UI automatically saves the barcode→name mapping; re-scanning that product works immediately without hitting OpenFoodFacts.
- **Gemini 2.5 Flash (AI Studio) over local/featherless LLM** — featherless.ai Basic plan has no vision models within the free tier limit; Proxmox/Ollama dropped. Google AI Studio key used; `google-genai` SDK (not the deprecated `google-generativeai`).
- **Identification flow on touchscreen, not web UI** — the full multi-photo capture → Gemini → accept/retry flow runs in the pygame state machine. The web UI is for manual editing only.
- **OpenFoodFacts contribution optional** — product data and front photo are uploaded back to OFF after AI identification. Silently skipped if `OFF_USER`/`OFF_PASSWORD` are absent in `.env`.
- **Two-threshold thermal protection** — warning at 70 °C (notification + "Shutdown Pi" button) lets me decide; critical at 80 °C triggers the Pi's own `sudo shutdown` without needing HA round-trip. 30 s sample cadence + `for: 1 min` debounce filters out short Gemini-burst spikes.
- **Re-use HA long-lived token for `/shutdown` auth** — instead of a separate shared secret, the Pi's webapp authenticates the HA `rest_command` against the same long-lived token already in `.env`. One credential to rotate.
- **Recents + autocomplete > full keyboard alone** — manual entry is dominated by repeats (milk, bread, eggs). The chip row covers 1-tap re-adds and 2-tap autocomplete; the QWERTY keyboard is the fallback for genuinely new items. Storage is a single append-only `manual_items.jsonl`.
- **Kiosk-pattern return-to-idle, not phone-pattern resume** — after 90 s of inactivity on transient screens (`list_view`, `manual_input`, `menu`, `webui_hint`) the device resets to `idle`. POS/kiosk convention beats phone "wake to last screen" here because the device is shared (anyone in the kitchen) and the calm idle state gives clearer "ready to scan" feedback than a stale list view. The blank timer (30 s) still kicks in first, so active users reading a list aren't punished — only walked-away sessions reset.
- **Code lives in the vault** — development and documentation kept together in the Obsidian vault; daemon code under `daemon/`.
