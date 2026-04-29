---
pm-project: true
id: "368ebf0315314be6"
title: "Grocery List Automation"
description: "Raspberry Pi barcode scanner station — scan product → OpenFoodFacts → Bring! via HA. LED + LCD + audio feedback."
color: "#8a94a0"
icon: "🟡"
taskIds: ["c552bb335eb84d08", "8200efd47448498a", "341571e82f184914", "102ded91151646b8", "840e6682d6bb4df3", "e0242bbe0de8489f"]
customFields: []
teamMembers: []
savedViews: []
createdAt: "2026-04-26T10:00:00.000Z"
updatedAt: "2026-04-26T17:52:17.173Z"
---

# 🟡 Grocery List Automation

Raspberry Pi barcode scanner station — scan product → OpenFoodFacts → Bring! via HA. LED + LCD + audio feedback.

## Tasks
- [ ] [[order-lcd-module-(ssd1306-oled)-and-spea-c552bb33|Order LCD module (SSD1306 OLED) and speaker amp (PAM8302)]]
- [ ] [[flash-raspberry-pi-os-and-bring-onto-net-8200efd4|Flash Raspberry Pi OS and bring onto network]]
- [ ] [[create-ha-long-lived-access-token-and-st-341571e8|Create HA long-lived access token and store in .env]]
- [ ] [[write-phase-1-daemon-(evdev-scanner-→-op-102ded91|Write Phase 1 daemon (evdev scanner → OpenFoodFacts → HA todo.add_item → feedback)]]
- [ ] [[create-grocery-scanner.service-systemd-u-840e6682|Create grocery-scanner.service systemd unit and end-to-end test]]
- [ ] [[phase-2-—-web-app-+-ha-dashboard-embed-e0242bbe|Phase 2 — web app + HA dashboard embed]]
