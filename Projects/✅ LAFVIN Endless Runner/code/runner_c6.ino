// One-button endless runner for LAFVIN ESP32-C6-LCD-1.47.
//
// IMPORTANT setup before flashing:
//  1. Install esp32 by Espressif Systems (>= 3.0.0) via Boards Manager.
//  2. Install libraries via Library Manager:
//       - GFX Library for Arduino  (by moononournation, "Arduino_GFX")
//       - Adafruit NeoPixel
//  3. Board: "ESP32C6 Dev Module", USB CDC On Boot: Enabled, Flash 4MB.
//
// VERIFY pin assignments in pins.h against the LAFVIN schematic before
// the first flash.

#include "pins.h"
#include "game.h"
#include "render.h"
#include "led.h"
#include "sd_score.h"

static GameState game;
static uint32_t  s_frame = 0;
static uint32_t  s_lastMicros = 0;
static uint32_t  s_lastFpsLog = 0;
static uint32_t  s_frames = 0;

// Button: active-low on GPIO9 with internal pull-up.
static bool s_btnPrev = false;
static bool s_btnRaw  = false;
static uint32_t s_btnChangedMs = 0;
static constexpr uint32_t BTN_DEBOUNCE_MS = 15;

static void readButton(bool& down, bool& pressedEdge, bool& releasedEdge) {
  bool raw = (digitalRead(PIN_BOOT_BUTTON) == LOW);
  uint32_t now = millis();
  if (raw != s_btnRaw) { s_btnRaw = raw; s_btnChangedMs = now; }
  bool stable = s_btnPrev;
  if (now - s_btnChangedMs >= BTN_DEBOUNCE_MS) stable = s_btnRaw;

  pressedEdge  = (!s_btnPrev && stable);
  releasedEdge = ( s_btnPrev && !stable);
  down = stable;
  s_btnPrev = stable;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("=== runner_c6 boot ===");

  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);

  ledInit();

  if (!renderInit()) {
    Serial.println("ERROR: renderInit failed");
    while (true) delay(1000);
  }
  Serial.printf("free heap after canvas: %u\n", (unsigned)ESP.getFreeHeap());

  bool sd = sdInit();
  Serial.printf("SD: %s\n", sd ? "mounted" : "absent (using NVS fallback)");

  uint32_t best = sdReadHighScore();
  Serial.printf("high score loaded: %lu\n", (unsigned long)best);

  randomSeed(esp_random());

  game.phase = Phase::Title;
  game.bestScore = best;

  s_lastMicros = micros();
}

void loop() {
  uint32_t nowUs = micros();
  float dt = (nowUs - s_lastMicros) / 1e6f;
  if (dt > 0.05f) dt = 0.05f;
  s_lastMicros = nowUs;

  bool down, pressed, released;
  readButton(down, pressed, released);

  switch (game.phase) {
    case Phase::Title:
      renderTitle(game.bestScore, s_frame);
      if (pressed) gameReset(game, game.bestScore);
      break;

    case Phase::Playing:
      gameStep(game, dt, down, pressed, released);
      ledOnEvent(game.justJumped, game.justDied, game.newBest);
      renderFrame(game, s_frame);
      if (game.phase == Phase::GameOver && game.newBest) {
        sdWriteHighScore(game.bestScore);
      }
      break;

    case Phase::GameOver:
      renderGameOver(game, s_frame);
      if (pressed) gameReset(game, game.bestScore);
      break;
  }

  ledTick(game.phase == Phase::Playing, millis());

  s_frames++;
  uint32_t nowMs = millis();
  if (nowMs - s_lastFpsLog >= 1000) {
    Serial.printf("fps=%lu free=%u score=%lu speed=%.1f\n",
                  (unsigned long)s_frames, (unsigned)ESP.getFreeHeap(),
                  (unsigned long)game.score, game.speed);
    s_frames = 0;
    s_lastFpsLog = nowMs;
  }
  s_frame++;
}
