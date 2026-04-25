#include "led.h"
#include <Adafruit_NeoPixel.h>
#include "pins.h"

static Adafruit_NeoPixel s_pixel(1, PIN_RGB_LED, NEO_GRB + NEO_KHZ800);

enum class Mode : uint8_t { Idle, JumpFlash, Death, Rainbow };
static Mode     s_mode    = Mode::Idle;
static uint32_t s_modeStart = 0;

void ledInit() {
  s_pixel.begin();
  s_pixel.setBrightness(40);
  s_pixel.clear();
  s_pixel.show();
}

void ledOnEvent(bool justJumped, bool justDied, bool newBest) {
  if (justDied) {
    s_mode = newBest ? Mode::Rainbow : Mode::Death;
    s_modeStart = millis();
  } else if (justJumped) {
    s_mode = Mode::JumpFlash;
    s_modeStart = millis();
  }
}

static uint32_t wheel(uint8_t pos) {
  pos = 255 - pos;
  if (pos < 85)  return s_pixel.Color(255 - pos * 3, 0, pos * 3);
  if (pos < 170) { pos -= 85; return s_pixel.Color(0, pos * 3, 255 - pos * 3); }
  pos -= 170;    return s_pixel.Color(pos * 3, 255 - pos * 3, 0);
}

void ledTick(bool playing, uint32_t nowMs) {
  uint32_t e = nowMs - s_modeStart;
  uint32_t c = 0;

  switch (s_mode) {
    case Mode::JumpFlash: {
      if (e > 200) { s_mode = Mode::Idle; }
      else { uint8_t v = 255 - (uint8_t)(e * 255 / 200); c = s_pixel.Color(0, 0, v); }
    } break;
    case Mode::Death: {
      if (e > 1200) { s_mode = Mode::Idle; }
      else { uint8_t v = 255 - (uint8_t)(e * 255 / 1200); c = s_pixel.Color(v, 0, 0); }
    } break;
    case Mode::Rainbow: {
      if (e > 3000) { s_mode = Mode::Idle; }
      else { c = wheel((uint8_t)((e / 8) & 0xFF)); }
    } break;
    case Mode::Idle:
    default: {
      if (playing) {
        // Dim cyan breathing
        float ph = (nowMs % 2000) / 2000.0f;
        uint8_t v = (uint8_t)(20 + 40 * (0.5f + 0.5f * sinf(ph * 2 * PI)));
        c = s_pixel.Color(0, v, v);
      } else {
        c = s_pixel.Color(8, 8, 16);
      }
    } break;
  }

  s_pixel.setPixelColor(0, c);
  s_pixel.show();
}
