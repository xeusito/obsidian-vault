# runner_c6

One-button endless runner for the **LAFVIN ESP32-C6-LCD-1.47** kit. Press the
on-board BOOT button to jump, dodge cacti, beat your best score. Uses the
1.47" 172×320 ST7789 LCD (landscape), the WS2812 RGB LED for feedback, and
the microSD slot (with NVS fallback) for the high score.

## Files

| File | Purpose |
|---|---|
| `runner_c6.ino` | Main sketch — boot, input, frame loop, FPS log |
| `pins.h` | All GPIO assignments (single source of truth) |
| `game.h/.cpp` | Physics, obstacle spawning, collision |
| `render.h/.cpp` | Sprite-based renderer with parallax + HUD |
| `led.h/.cpp` | RGB-LED state machine (idle / jump / death / rainbow) |
| `sd_score.h/.cpp` | Persist high score to SD; falls back to NVS |
| `User_Setups/Setup_LAFVIN.h` | TFT_eSPI configuration for this board |

## One-time setup

1. **Arduino IDE 2.x** + Espressif board package:
   - File → Preferences → Additional Boards URL:
     `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   - Tools → Board → Boards Manager → install **esp32 by Espressif Systems**
     (≥ 3.0.0 — required for ESP32-C6).
2. Libraries (Tools → Manage Libraries):
   - **TFT_eSPI** by Bodmer
   - **Adafruit NeoPixel**
3. **Configure TFT_eSPI for this board** (this is the trickiest step):
   - Find your TFT_eSPI library folder. On Windows it's usually
     `Documents\Arduino\libraries\TFT_eSPI\`.
   - Copy `User_Setups/Setup_LAFVIN.h` from this project into
     `TFT_eSPI/User_Setups/`.
   - Open `TFT_eSPI/User_Setup_Select.h` and:
     - Comment out the currently active `#include` line.
     - Add: `#include <User_Setups/Setup_LAFVIN.h>`.
4. Board settings:
   - Tools → Board → ESP32 Arduino → **ESP32C6 Dev Module**
   - Tools → USB CDC On Boot → **Enabled**
   - Tools → Flash Size → **4MB**

## ⚠️ Verify pinout before flashing

Pin assignments in `pins.h` and `Setup_LAFVIN.h` are based on the Waveshare
ESP32-C6-LCD-1.47 reference design that LAFVIN almost certainly clones.
**Confirm them against the LAFVIN schematic / component-list** before the
first flash. If anything is wrong, pixels won't appear or the LED will be
silent — but nothing should be damaged.

| Peripheral | GPIO |
|---|---|
| LCD MOSI / SCLK / CS / DC / RST / BL | 6 / 7 / 14 / 15 / 21 / 22 |
| BOOT button (active low) | 9 |
| WS2812 RGB LED | 8 |
| microSD CS / MOSI / MISO / SCLK | 4 / 6 / 5 / 7 |

## First-flash troubleshooting

- **Blank screen**: wrong driver or rotation. Try uncommenting
  `TFT_OFFSET_X 34` in `Setup_LAFVIN.h`. If the colors are inverted,
  toggle `TFT_RGB_ORDER` between `TFT_RGB` and `TFT_BGR`.
- **`sprite alloc failed`**: the 110 KB framebuffer didn't fit. The
  renderer auto-falls back to half-height strips; if it still fails,
  reduce other allocations or lower `setColorDepth(8)` in `render.cpp`.
- **No SD detected**: the sketch falls back to NVS automatically — gameplay
  is unaffected, only the score-file location changes. Format the card as
  FAT32 if you want SD persistence.
- **Game too hard / too easy**: tune `JUMP_VY`, `GRAVITY`, `SPEED_*` in
  `game.h`.

## Controls

- **BOOT button**: short press to jump, hold for higher jump (variable
  jump-cut on early release). Same button starts the run from the title
  screen and restarts after Game Over.

## Verification checklist (mirrors the plan)

- [ ] Compiles cleanly with no warnings.
- [ ] Boot serial shows `free heap`, `SD: mounted/absent`, and loaded high score.
- [ ] Title screen appears in landscape with blinking "press BOOT" prompt.
- [ ] Press BOOT → run starts, player jumps, world scrolls, score climbs.
- [ ] Frame rate ≥ 30 (printed once per second to Serial).
- [ ] Speed visibly ramps up over ~60 s of play.
- [ ] Crashing into a cactus → red LED fade + Game Over overlay.
- [ ] Beat the high score → rainbow LED + "NEW BEST" + score persists across power-cycle.
- [ ] 5-min soak: free-heap value stays steady.
