#include "sd_score.h"
#include <SPI.h>
#include <SD.h>
#include <Preferences.h>
#include "pins.h"

static const char* SCORE_PATH = "/runner.txt";
static bool s_sdReady = false;
static Preferences s_prefs;       // NVS fallback if SD is absent

bool sdInit() {
  // The SD card shares MOSI/SCLK with the LCD. Begin a second SPIClass on
  // the same pins is fine — the SD library will toggle CS appropriately.
  SPI.begin(PIN_SD_SCLK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  s_sdReady = SD.begin(PIN_SD_CS, SPI, 20000000);
  if (!s_sdReady) {
    // Fall back to NVS so the high score still persists.
    s_prefs.begin("runner", false);
  }
  return s_sdReady;
}

uint32_t sdReadHighScore() {
  if (s_sdReady) {
    File f = SD.open(SCORE_PATH, FILE_READ);
    if (!f) return 0;
    String s = f.readStringUntil('\n');
    f.close();
    return (uint32_t) s.toInt();
  }
  return s_prefs.getUInt("best", 0);
}

void sdWriteHighScore(uint32_t score) {
  if (s_sdReady) {
    File f = SD.open(SCORE_PATH, FILE_WRITE);
    if (!f) return;
    f.println(score);
    f.close();
  } else {
    s_prefs.putUInt("best", score);
  }
}
