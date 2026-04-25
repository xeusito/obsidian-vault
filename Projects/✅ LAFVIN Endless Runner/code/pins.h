#pragma once
// All GPIO assignments for LAFVIN ESP32-C6-LCD-1.47.
// VERIFY against the LAFVIN component-list / schematic before flashing.

// LCD pins are also defined in User_Setups/Setup_LAFVIN.h for TFT_eSPI.
// Keep the two in sync if you change them.

#define PIN_BOOT_BUTTON   9    // active-low, has internal pull-up
#define PIN_RGB_LED       8    // WS2812 single addressable

// microSD (SPI). Shares MOSI/SCLK with the LCD on most C6-LCD-1.47 boards.
#define PIN_SD_CS         4
#define PIN_SD_MOSI       6
#define PIN_SD_MISO       5
#define PIN_SD_SCLK       7
