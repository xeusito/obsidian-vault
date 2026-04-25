# Hardware

## Board
**LAFVIN ESP32-C6-LCD-1.47** — clone of the Waveshare ESP32-C6-LCD-1.47 reference design.

- ESP32-C6 (RISC-V, 160 MHz), 4 MB flash, 512 KB SRAM
- Wi-Fi 6 (2.4 GHz), BLE 5, Thread/Matter, Zigbee
- 1.47" ST7789 IPS LCD, 172×320, SPI
- 1× WS2812 addressable RGB LED
- BOOT button (active-low) + reset button
- microSD slot (SPI)

Wi-Fi is left **off** in this project to maximize free SRAM for the framebuffer.

## Pinout (verified working)

| Peripheral          | Signal | GPIO |
| ------------------- | ------ | ---- |
| LCD                 | MOSI   | 6    |
|                     | SCLK   | 7    |
|                     | CS     | 14   |
|                     | DC     | 15   |
|                     | RST    | 21   |
|                     | BL     | 22   |
| BOOT button         | —      | 9    |
| WS2812 RGB LED      | DIN    | 8    |
| microSD             | CS     | 4    |
|                     | MOSI   | 6    |
|                     | MISO   | 5    |
|                     | SCLK   | 7    |

LCD and SD share the SPI bus (MOSI=6, SCLK=7) — separate CS lines keep them isolated.

## Power
USB-C from the dev board. Backlight is hard-on via `digitalWrite(PIN_TFT_BL, HIGH)` — no PWM dimming.

## Measured behavior
- Frame rate: **30 fps stable** (printed once/sec to Serial)
- Free heap after canvas alloc: **~316 KB**, stays flat over 5+ min — no leak
- Boot to title screen: ~1.2 s
