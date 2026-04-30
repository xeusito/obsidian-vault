# Changelog

All notable changes to the Grocery List Automation project. Versions follow [Semantic Versioning](https://semver.org/) — major.minor for user-visible feature sets; bugfixes between releases roll into the next minor.

Tagged in git as `grocery-list-automation-v<version>` on the [obsidian-vault](https://github.com/xeusito/obsidian-vault) repo.

---

## [1.1] — 2026-04-30

Quality-of-life pass driven entirely by real-life kitchen use.

### Added
- **Shopping-list view on device** — tap idle → menu → *Shopping List*. Paginated 5 items per page with a red ✕ per row to delete (calls HA `todo.remove_item`). Prev / Back / Next footer.
- **Duplicate-add detection** — every `add_to_bring` (barcode-scanned and AI-identified) first calls `todo.get_items` and compares the trimmed name case-insensitively. Existing entries trigger a yellow *Already in shopping list* screen instead of a second copy. Network failures still fall through to the add — better risk a duplicate than block while HA blips.
- **Manual entry on the touchscreen** — `+` in the list-view header opens a full virtual QWERTY keyboard with three layers (letters / numbers / accents). Sticky-one-shot Shift. ⌫ backspace.
- **Recents + autocomplete** — last 8 unique manually-added items appear as one-tap chips. As you type, the chip row swaps to up to 3 prefix-matches.
- **Optional description field** — `+ desc` toggle reveals a second input row. Empty descriptions are dropped from the HA payload. Recents that carry a description auto-expand the row when their chip is tapped, so what's about to submit is always visible.
- **Manual-add history file** — `data/manual_items.jsonl` (one append-only JSON line per add). De-duplicated by name (latest description wins) when read.
- **Kiosk-style return-to-idle** — 90 s of inactivity on `list_view`, `manual_input`, `menu`, or `webui_hint` resets state and returns to the calm "Ready — scan a product" screen. Active sessions still get the full 30 s blank-timer first, so reading a list isn't punished.

### Changed
- **List-view header `+` button** — trimmed from "+ Add" text to a single `+` glyph (56 px) so it stops crowding the title.
- **Keyboard backspace label** — `⌫` icon instead of the "Bksp" text.
- **`add_to_bring()` return value** — was `bool`, now `"added" | "duplicate" | "error"` so callers can route to the new `already_in_list` screen.
- **Scanner gating** — `handle_barcode` is now also a no-op while on `already_in_list`; prevents double-firing on rapid re-scans.

### Fixed
- (No bugfixes — v1.0 was tagged stable; this is purely additive.)

---

## [1.0] — 2026-04-30

Initial production release. Kitchen-counter scan-and-done station fully assembled, mounted, and integrated with Bring! via Home Assistant.

### Added — Phase 1 (Scanner daemon)
- Honeywell 7580 USB barcode scanner in HID-keyboard mode, configured for Switzerland keyboard layout via the vendor quick-start barcodes.
- `scanner.py` Python daemon: reads barcodes via `evdev` (exclusive grab), looks them up in OpenFoodFacts v2 with `de → es → en → wider fallback` for product names, posts to HA `todo.add_item` on `todo.shopping`.
- Pygame-driven full-screen UI on the BTT TFT50 v2.1 (800×480 DSI touchscreen): green/yellow/red colour-coded scan feedback.
- LXDE autostart (with `while true; sleep 5; done` crash-recovery loop) — chosen over a systemd user service because LXDE doesn't trigger `graphical-session.target` on Pi OS.

### Added — Phase 2 (Web UI)
- Flask app on port 5000 (LAN-only) with two views:
  - `/unknown` — queue of barcodes the scanner couldn't resolve; resolve adds to Bring! and saves the barcode→name mapping to `custom_barcodes.json`.
  - `/custom` — full CRUD editor for the custom-barcode map (used for pre-printed barcodes on bulk/unlabelled items).
- Inline edit support on the custom-barcode editor.
- HA dashboard button card linking to the web UI in a new tab (HTTP iframes blocked by HTTPS HA).

### Added — Phase 3 (Vision + UX polish)
- Pi camera module wired to CSI; `vision.py` shared module with `rpicam-jpeg` capture, Gemini 2.5 Flash AI identification, and OpenFoodFacts contribution upload.
- Touchscreen identification flow: front photo → optional back photo → Gemini → accept/retry. Multi-photo support in a single API call. Robust JSON parsing with 4-step fallback (direct → strip fences → regex extract → fix unquoted JS-style keys).
- OpenFoodFacts contribution: products identified by Gemini are posted back to OFF (data + front photo). Skipped silently if `OFF_USER`/`OFF_PASSWORD` are absent.
- On-screen menu (Restart / Close) reachable by tapping the idle screen, plus a desktop icon on `~/Desktop` to relaunch after Close.
- Display auto-blank after 30 s of inactivity (`vcgencmd display_power 0`); wakes on touch (consumes the tap) or barcode scan (processes normally).
- **CPU thermal monitoring**:
  - `tempmon.py` reads `/sys/class/thermal/thermal_zone0/temp` every 30 s via a systemd timer, posts to `input_number.grocery_scanner_pi`, auto-shuts-down at ≥ 80 °C.
  - HA single automation with three triggers (`warning > 70 °C for 1 min`, `critical > 80 °C`, `mobile_app_notification_action`) dispatched by `trigger.id`. Warning fires a notification with a *Shutdown Pi* action button on the OnePlus.
  - `webapp.py:/shutdown` route (HA-token auth) so HA can remotely halt the Pi.
  - sudoers entry letting `pi` run `/sbin/shutdown` without a password.

### Added — Phase 4 (Inputs)
- Pre-printed barcodes for unlabelled items (coffee jar, flour tin) — managed via the `/custom` web UI.

### Added — Phase 5 (Enclosure & mounting)
- Custom 3D-printed enclosure (Bambu Studio `.3mf` + 4 STLs: body, vented rear panel, SKADIS connector plate, SKADIS pegs).
- Camera positioned for ~45° downward shots of products held below the screen.
- Mounted on the IKEA SKADIS pegboard in the kitchen.

### Decisions captured at v1.0
- Sync via HA `todo.shopping` entity (Bring! integration already loaded; one `todo.add_item` call per scan).
- Display-only feedback — buzzer and RGB LED strip both dropped; the BTT TFT50 colour flash is more informative and visible from across the kitchen.
- Static IP `192.168.0.162` over mDNS (`.local` was unreliable on this network).
- Custom barcode map as a learning layer — resolved unknowns are remembered and skip the OFF lookup on re-scan.
- Gemini 2.5 Flash (Google AI Studio) over local/featherless LLM — featherless Basic plan has no vision models in the free tier; Proxmox/Ollama dropped.
- Identification flow on touchscreen, not web UI — full multi-photo capture → Gemini → accept/retry runs in pygame; web UI is for manual editing only.
- Two-threshold thermal protection — 70 °C warning + button, 80 °C self-shutdown.
- Re-use HA long-lived token for `/shutdown` auth — one credential to rotate, not two.
- Code lives in the vault — daemon, docs, enclosure, photos all under `Projects/✅ Grocery List Automation/`.
