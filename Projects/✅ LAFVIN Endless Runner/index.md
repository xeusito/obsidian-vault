---
status: done
priority: low
startDate: 2026-04-25
dueDate: 2026-04-25
tags: [project, hardware, esp32-c6, arduino, game, lafvin]
---

# LAFVIN Endless Runner

One-button Chrome-dino-style endless runner for the **LAFVIN ESP32-C6-LCD-1.47** kit. Press BOOT to jump, dodge cacti, beat the high score. First project on the new board — exercises the LCD, RGB LED, microSD, and BOOT button all at once.

## Subpages
- [[Projects/✅ LAFVIN Endless Runner/Hardware]] — board, pinout, peripherals used
- [[Projects/✅ LAFVIN Endless Runner/Software]] — architecture, libraries, tuning knobs

## Source
- [[code/runner_c6.ino|runner_c6.ino]] — main sketch
- [[code/game.h|game.h]] / [[code/game.cpp|game.cpp]] — physics, collision, spawning
- [[code/render.h|render.h]] / [[code/render.cpp|render.cpp]] — Arduino_GFX renderer
- [[code/led.h|led.h]] / [[code/led.cpp|led.cpp]] — WS2812 state machine
- [[code/sd_score.h|sd_score.h]] / [[code/sd_score.cpp|sd_score.cpp]] — high-score persistence
- [[code/pins.h|pins.h]] — GPIO map
- [[code/README.md|README.md]] — setup steps

## Status

| Item                          | State        |
| ----------------------------- | ------------ |
| Compiles cleanly              | ✅ done      |
| LCD renders in landscape      | ✅ done      |
| Player jumps + collides       | ✅ done      |
| Speed ramp                    | ✅ done      |
| RGB LED feedback              | ✅ done      |
| Score persists across reboot  | ✅ done      |
| 30 fps stable, no heap leak   | ✅ done      |

## Key Decisions
- **Arduino_GFX over TFT_eSPI** — TFT_eSPI 2.5.43 is hardcoded for the original ESP32 SoC (VSPI, GPIO.out_w1tc int assignment) and won't compile for ESP32-C6. Arduino_GFX (`moononournation`) supports the C6 cleanly via `Arduino_ESP32SPI`.
- **`Arduino_Canvas` for double buffering** — 320×172×2 ≈ 110 KB framebuffer fits comfortably in the C6's 512 KB SRAM with Wi-Fi off; eliminates flicker, makes scrolling trivial.
- **ST7789 column offset = 34** — the 1.47" 172×320 panel has the typical Waveshare-style 34-pixel column offset; without it the image is shifted off-screen.
- **One-button variable jump** — short press = small hop (jump-cut on early release), hold = full arc. Keeps the design genuinely one-input while giving the player some skill expression.
- **SD with NVS fallback** — high score writes to `/runner.txt` if a card is mounted; otherwise falls back to NVS via `Preferences`. Player never loses their score because the card is missing.

## Lessons learned
- ESP32-C6 is new enough that "popular" Arduino libraries aren't all ported yet. Always check the library's `library.properties` `architectures=` field before fighting compile errors.
- Default RGB565 palette numbers off the internet are usually too dark on this IPS panel — start brighter than you think.
- `randomSeed(esp_random())` in `setup()` is the right way to seed on ESP32; `analogRead` of a floating pin is the AVR habit and doesn't apply here.
