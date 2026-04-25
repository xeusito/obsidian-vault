# Software

## Toolchain
- **Arduino IDE 2.x**
- **esp32 by Espressif Systems** ≥ 3.0.0 (3.3.8 used) — required for ESP32-C6 support
- Board: **ESP32C6 Dev Module**, USB CDC On Boot: **Enabled**, Flash Size: **4MB**
- Boards-manager URL: `https://espressif.github.io/arduino-esp32/package_esp32_index.json`

## Libraries
| Library | Author | Why |
|---|---|---|
| **GFX Library for Arduino** (`Arduino_GFX`) | moononournation | LCD driver — the only mainstream GFX lib that compiles cleanly for ESP32-C6 |
| **Adafruit NeoPixel** | Adafruit | WS2812 |
| `SD` | bundled with esp32 core | high-score file |
| `Preferences` | bundled | NVS fallback when no SD card |

> ⚠️ **Do not use TFT_eSPI** on ESP32-C6 — version 2.5.43 hardcodes the original-ESP32 SoC (VSPI registers, raw `GPIO.out_w1tc` writes). Compile fails with hundreds of errors.

## Architecture

```
runner_c6.ino       boot, input debounce, frame loop, FPS log
├── pins.h          GPIO constants (single source of truth)
├── game.{h,cpp}    physics, AABB collision, obstacle spawning, score
├── render.{h,cpp}  Arduino_ST7789 + Arduino_Canvas, sprite-style draws
├── led.{h,cpp}     WS2812 state machine (idle/jump/death/rainbow)
└── sd_score.{h,cpp} SD → /runner.txt, NVS fallback
```

Frame loop is fixed-`dt` style with a 50 ms cap so a stutter can't teleport the player into a cactus.

## Display init (the part that took the longest)

```cpp
s_bus   = new Arduino_ESP32SPI(DC=15, CS=14, SCK=7, MOSI=6, GFX_NOT_DEFINED);
s_panel = new Arduino_ST7789(s_bus, RST=21, /*rotation*/1, /*IPS*/true,
                             172, 320, /*col_off1*/34, 0, /*col_off2*/34, 0);
s_canvas = new Arduino_Canvas(SCREEN_W=320, SCREEN_H=172, s_panel);
```

Rotation = 1 → landscape 320×172. The `34, 0, 34, 0` offsets are mandatory for this 1.47" panel — without them you get a blank screen or pixels offset off the visible area.

## Tuning knobs (in `game.h`)
| Constant | Value | What it does |
|---|---|---|
| `GRAVITY` | 1400 | px/s² down |
| `JUMP_VY` | -520 | initial jump velocity |
| `JUMP_CUT_VY` | -180 | clamp Vy on early-release for variable jump |
| `SPEED_START` | 90 | px/s initial scroll |
| `SPEED_MAX` | 240 | px/s cap |
| `SPEED_RAMP` | 4 | px/s² acceleration |

## Input
BOOT (GPIO9) read with `INPUT_PULLUP`, debounced 15 ms in software. Edge detection in `readButton()` returns `pressed` / `released` flags so jump-cut works.

## RGB LED state machine
- **Idle / running**: dim cyan breathing
- **Jump pressed**: blue flash, 200 ms
- **Hit obstacle**: red fade, 1200 ms
- **New high score (game-over screen)**: rainbow, 3000 ms

Driven from the main loop via `ledOnEvent(justJumped, justDied, newBest)` plus a per-frame `ledTick()`.

## Persistence
`sdInit()` tries the SD card first. On success, high score reads/writes go to `/runner.txt` as plain ASCII. If the card is missing or fails, the code falls back transparently to NVS via `Preferences` (namespace `runner`, key `best`). The user never sees the difference.
