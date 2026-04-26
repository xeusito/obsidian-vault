---
status: todo
priority: medium
startDate: 2026-04-24
dueDate: 2026-08-31
tags: [project, raspberry-pi, home-assistant, bring, openfoodfacts, barcode]
---

# Grocery List Automation

A kitchen-counter scan-and-done station that adds items to the Bring! shopping list in under 3 seconds, with zero typing for known products. A Raspberry Pi with a barcode scanner looks the product up in OpenFoodFacts and pushes it to Bring! via the existing Home Assistant integration. LED + LCD + speaker give instant feedback.

## Subpages
- [[Hardware]] — components, wiring, mounting
- [[Software]] — daemon, HA integration, OpenFoodFacts, web app

## Background (from original idea)

### Why
The shopping list is never up-to-date because it requires typing items into a phone or the kitchen tablet. Reducing that friction is the whole point — a comprehensive shopping list when it's time to shop or order groceries online.

### Constraints
OpenFoodFacts has over 3 million entries, but coverage varies by language and region — not every scanned product will be present. The system must degrade gracefully for unknowns (queue + manual resolution) and eventually support adding missing products, including from photos.

### Languages
German, Spanish, English — DE / ES / EN fallback when reading product names.

## Status

| Item                                   | State       |
| -------------------------------------- | ----------- |
| Plan drafted                           | ✅ done     |
| Project folder scaffolded              | ✅ done     |
| Pi 3 dedicated to project              | ✅ confirmed |
| Honeywell USB-A scanner                | ✅ on hand  |
| Govee RGB strip (to cut)               | ✅ on hand  |
| LCD module ordered                     | ⬜ pending  |
| Speaker amp (PAM8302 or similar)       | ⬜ pending  |
| HA long-lived access token             | ⬜ pending  |
| Daemon MVP (Phase 1)                   | ⬜ pending  |
| Systemd auto-start                     | ⬜ pending  |
| Phase 2 web app + HA dashboard embed   | ⬜ pending  |
| Phase 3 local LLM (Proxmox capacity)   | ⬜ pending  |
| Phase 4 pre-printed barcodes / camera  | ⬜ pending  |

## Next Steps
- [ ] Order LCD (SSD1306 OLED preferred) and speaker amp (PAM8302)
- [ ] Flash fresh Raspberry Pi OS on the Pi 3, bring it onto the network
- [ ] Create HA long-lived access token, store in `.env`
- [ ] Cut Govee strip to 2–3 LEDs, prototype MOSFET driver on a breadboard
- [ ] Write Phase 1 daemon: evdev scanner read → OpenFoodFacts lookup → HA `todo.add_item` → feedback
- [ ] Create `grocery-scanner.service` systemd unit
- [ ] End-to-end verification (see plan file)

## Key Decisions
- **Sync via HA Bring! integration, not unofficial Bring! API** — integration is already loaded (`todo.shopping`). One `todo.add_item` service call, no reverse-engineered endpoints to babysit.
- **Phase 1 is the MVP** — barcode → OpenFoodFacts → Bring!. No AI, no voice, no NFC. Ship that first; everything else is polish.
- **LED + LCD + speaker together, not one vs. the other** — LED for glance-distance status, LCD for text (product name / error), speaker for hands-busy audio confirmation.
- **Pre-printed barcodes before NFC** — a printed barcode sheet for bulk/unlabelled items reuses the existing scanner; NFC reader is deferred until this isn't sufficient.
- **Code lives in the vault during MVP, migrates to Home Automation repo later** — keeps planning + code + notes in one place while iterating; Home Automation repo gets the polished artefact.
- **Local LLM deferred to Phase 3** — Proxmox capacity audit required; may need new hardware. Not on the critical path.

## Plan File
Full plan: `~/.claude/plans/read-the-grocery-list-automation-md-file-snappy-hoare.md`
