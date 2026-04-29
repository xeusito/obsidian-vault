---
status: active
priority: medium
startDate: 2026-04-24
tags: [project, raspberry-pi, home-assistant, bring, openfoodfacts, barcode]
---

# Grocery List Automation

A kitchen-counter scan-and-done station that adds items to the Bring! shopping list in under 3 seconds, with zero typing for known products. A Raspberry Pi 4 with a Honeywell barcode scanner looks the product up in OpenFoodFacts and pushes it to Bring! via the existing Home Assistant integration. The BTT TFT50 v2.1 touchscreen gives colour-coded feedback on every scan.

## Subpages
- [[Hardware]] — components, wiring, network, mounting
- [[Software]] — daemon, web app, HA integration, autostart

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
| Phase 4 — Pre-printed barcodes                | ⬜ planned   |
| Phase 5 — 3D-printed case (screen + Pi)       | ⬜ planned   |
| Phase 5 — Camera case (print or source)       | ⬜ planned   |
| Phase 5 — Print case(s)                       | ⬜ planned   |
| Phase 5 — Mount project in kitchen            | ⬜ planned   |

## Next Steps
- [ ] Generate pre-printed barcode sheet for bulk/unlabelled items (coffee, flour, etc.)
- [ ] Design or find a 3D-printable enclosure for the touchscreen + Pi
- [ ] Design or find a case for the Pi camera module
- [ ] Print the case(s) and mount everything in the kitchen

## Key Decisions
- **Sync via HA `todo.shopping` entity** — Bring! integration already loaded in HA. One `todo.add_item` call, brand + quantity in the `description` field (maps to Bring!'s "Quantity, description…" field in the Android app).
- **Display only — no LED or buzzer in MVP** — BTT TFT50 fullscreen colour flash handles all feedback. Buzzer deferred (wrong cable type); LED strip deferred.
- **LXDE autostart over systemd user service** — `graphical-session.target` not triggered by LXDE on Pi OS; autostart fires reliably after X11 is ready.
- **Static IP (192.168.0.162) over mDNS** — `.local` hostname unreliable on this network.
- **HA button card over iframe** — HA runs on HTTPS; browsers block HTTP iframes (mixed content). Button card opens the web UI in a new tab.
- **Custom barcode map as learning layer** — resolving an unknown via the web UI automatically saves the barcode→name mapping; re-scanning that product works immediately without hitting OpenFoodFacts.
- **Gemini 2.5 Flash (AI Studio) over local/featherless LLM** — featherless.ai Basic plan has no vision models within the free tier limit; Proxmox/Ollama dropped. Google AI Studio key used; `google-genai` SDK (not the deprecated `google-generativeai`).
- **Identification flow on touchscreen, not web UI** — the full multi-photo capture → Gemini → accept/retry flow runs in the pygame state machine. The web UI is for manual editing only.
- **OpenFoodFacts contribution optional** — product data and front photo are uploaded back to OFF after AI identification. Silently skipped if `OFF_USER`/`OFF_PASSWORD` are absent in `.env`.
- **Code lives in the vault** — development and documentation kept together in the Obsidian vault; daemon code under `daemon/`.
