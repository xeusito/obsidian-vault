#include "render.h"
#include "pins.h"

// LCD pins (override here if pins.h doesn't already define them)
#ifndef PIN_TFT_MOSI
#define PIN_TFT_MOSI 6
#define PIN_TFT_SCLK 7
#define PIN_TFT_CS   14
#define PIN_TFT_DC   15
#define PIN_TFT_RST  21
#define PIN_TFT_BL   22
#endif

// Bus + display + offscreen canvas (heap-allocated so we control timing).
static Arduino_DataBus* s_bus    = nullptr;
static Arduino_GFX*     s_panel  = nullptr;   // physical ST7789 LCD
static Arduino_Canvas*  s_canvas = nullptr;   // offscreen 16-bit framebuffer
static Arduino_GFX*     s_gfx    = nullptr;   // -> canvas if allocated, else panel

// Palette (RGB565) — punchy, high-contrast
static constexpr uint16_t COL_SKY      = 0x6EBF;  // light cornflower blue
static constexpr uint16_t COL_SKY_TOP  = 0x4D9F;  // deeper blue band
static constexpr uint16_t COL_GROUND   = 0xEDC8;  // sandy tan
static constexpr uint16_t COL_GROUND_2 = 0x9B25;  // dark sand (pebble line)
static constexpr uint16_t COL_PLAYER   = 0x0000;  // black silhouette
static constexpr uint16_t COL_PLAYER_HL= 0x4A49;  // dark grey edge
static constexpr uint16_t COL_CACTUS   = 0x0584;  // bright green
static constexpr uint16_t COL_CACTUS_HL= 0x07E8;  // brighter green edge
static constexpr uint16_t COL_TEXT     = 0x2124;
static constexpr uint16_t COL_TEXT_DIM = 0x6B6D;
static constexpr uint16_t COL_CLOUD    = 0xFFFF;
static constexpr uint16_t COL_RED      = 0xF800;

bool renderInit() {
  // ESP32 SPI driver (works on C6)
  s_bus = new Arduino_ESP32SPI(PIN_TFT_DC, PIN_TFT_CS,
                               PIN_TFT_SCLK, PIN_TFT_MOSI, GFX_NOT_DEFINED);

  // ST7789 1.47" 172x320 IPS — typical Waveshare-style offsets (col=34).
  // Native portrait 172x320; we rotate to landscape (rotation = 1 → 320x172).
  s_panel = new Arduino_ST7789(s_bus, PIN_TFT_RST,
                               1 /*rotation: landscape*/,
                               true /*IPS*/,
                               172, 320,
                               34, 0, 34, 0);

  if (!s_panel->begin()) return false;

  // Backlight on
  pinMode(PIN_TFT_BL, OUTPUT);
  digitalWrite(PIN_TFT_BL, HIGH);

  s_panel->fillScreen(COL_SKY);

  // Offscreen canvas for double-buffered drawing.
  s_canvas = new Arduino_Canvas(SCREEN_W, SCREEN_H, s_panel);
  if (s_canvas->begin()) {
    s_gfx = s_canvas;
    s_canvas->fillScreen(COL_SKY);
  } else {
    // Fallback: draw straight to the panel (will flicker, but works).
    delete s_canvas;
    s_canvas = nullptr;
    s_gfx = s_panel;
  }
  return true;
}

static inline void flushCanvas() {
  if (s_canvas) s_canvas->flush();
}

// Right-aligned text helper (Adafruit_GFX-style: cursor + print).
static void drawTextRight(const char* s, int rightX, int y,
                          uint16_t fg, uint16_t bg, uint8_t size = 1) {
  int16_t bx, by; uint16_t bw, bh;
  s_gfx->setTextSize(size);
  s_gfx->getTextBounds(s, 0, 0, &bx, &by, &bw, &bh);
  s_gfx->setTextColor(fg, bg);
  s_gfx->setCursor(rightX - bw, y);
  s_gfx->print(s);
}

static void drawTextCenter(const char* s, int cx, int y,
                           uint16_t fg, uint16_t bg, uint8_t size = 1) {
  int16_t bx, by; uint16_t bw, bh;
  s_gfx->setTextSize(size);
  s_gfx->getTextBounds(s, 0, 0, &bx, &by, &bw, &bh);
  s_gfx->setTextColor(fg, bg);
  s_gfx->setCursor(cx - bw / 2, y);
  s_gfx->print(s);
}

static void drawSkyAndClouds(uint32_t worldX) {
  s_gfx->fillRect(0, 0,  SCREEN_W, 40,            COL_SKY_TOP);
  s_gfx->fillRect(0, 40, SCREEN_W, GROUND_Y - 40, COL_SKY);

  int cx = ((int)(worldX / 4)) % 240;
  for (int i = 0; i < 3; ++i) {
    int x = (i * 110 - cx + 320) % 320 - 30;
    int y = 18 + ((i * 13) % 14);
    s_gfx->fillCircle(x,    y,    7, COL_CLOUD);
    s_gfx->fillCircle(x+10, y+2,  9, COL_CLOUD);
    s_gfx->fillCircle(x+22, y,    6, COL_CLOUD);
  }
}

static void drawGround(uint32_t worldX) {
  s_gfx->fillRect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, COL_GROUND);
  s_gfx->drawFastHLine(0, GROUND_Y, SCREEN_W, COL_GROUND_2);
  int gx = ((int)worldX) % 32;
  for (int x = -gx; x < SCREEN_W; x += 32) {
    s_gfx->drawPixel(x + 6,  GROUND_Y + 6,  COL_GROUND_2);
    s_gfx->drawPixel(x + 14, GROUND_Y + 14, COL_GROUND_2);
    s_gfx->drawPixel(x + 22, GROUND_Y + 4,  COL_GROUND_2);
  }
}

static void drawPlayer(const GameState& g) {
  int px = PLAYER_X;
  int py = (int)g.playerY;
  s_gfx->fillRect(px, py, PLAYER_W, PLAYER_H, COL_PLAYER);
  s_gfx->fillRect(px + PLAYER_W - 5, py + 3, 2, 2, 0xFFFF);
  s_gfx->drawFastVLine(px + 1, py + 1, PLAYER_H - 2, COL_PLAYER_HL);
}

static void drawCactus(const Obstacle& o) {
  int x = (int)o.x;
  int y = GROUND_Y - o.h;
  s_gfx->fillRect(x, y, o.w, o.h, COL_CACTUS);
  s_gfx->drawFastVLine(x, y, o.h, COL_CACTUS_HL);
  if (o.type == ObstacleType::CactusWide) {
    s_gfx->fillRect(x + o.w + 2, y + 4, 4, o.h - 4, COL_CACTUS);
  }
}

static void drawHUD(const GameState& g) {
  char buf[32];
  snprintf(buf, sizeof(buf), "%05lu", (unsigned long)g.score);
  drawTextRight(buf, SCREEN_W - 6, 6, COL_TEXT, COL_SKY_TOP, 2);

  snprintf(buf, sizeof(buf), "HI %05lu", (unsigned long)g.bestScore);
  drawTextRight(buf, SCREEN_W - 90, 8, COL_TEXT_DIM, COL_SKY_TOP, 1);
}

void renderFrame(const GameState& g, uint32_t /*frameCount*/) {
  drawSkyAndClouds((uint32_t)g.worldX);
  drawGround((uint32_t)g.worldX);
  for (uint8_t i = 0; i < g.obsCount; ++i) drawCactus(g.obs[i]);
  drawPlayer(g);
  drawHUD(g);
  flushCanvas();
}

void renderTitle(uint32_t bestScore, uint32_t frameCount) {
  s_gfx->fillScreen(COL_SKY);
  drawTextCenter("RUNNER", SCREEN_W / 2, 40, COL_TEXT, COL_SKY, 4);
  if ((frameCount / 20) & 1) {
    drawTextCenter("press BOOT to start", SCREEN_W / 2, 95, COL_TEXT_DIM, COL_SKY, 1);
  }
  if (bestScore > 0) {
    char buf[32];
    snprintf(buf, sizeof(buf), "best  %05lu", (unsigned long)bestScore);
    drawTextCenter(buf, SCREEN_W / 2, 125, COL_TEXT, COL_SKY, 1);
  }
  flushCanvas();
}

void renderGameOver(const GameState& g, uint32_t frameCount) {
  // Re-draw frozen game frame, then overlay.
  drawSkyAndClouds((uint32_t)g.worldX);
  drawGround((uint32_t)g.worldX);
  for (uint8_t i = 0; i < g.obsCount; ++i) drawCactus(g.obs[i]);
  drawPlayer(g);
  drawHUD(g);

  int boxW = 220, boxH = 88;
  int bx = (SCREEN_W - boxW) / 2;
  int by = (SCREEN_H - boxH) / 2 - 6;
  s_gfx->fillRoundRect(bx, by, boxW, boxH, 6, COL_SKY_TOP);
  s_gfx->drawRoundRect(bx, by, boxW, boxH, 6, COL_TEXT);

  drawTextCenter("GAME OVER", SCREEN_W / 2, by + 10, COL_TEXT, COL_SKY_TOP, 3);
  char buf[40];
  snprintf(buf, sizeof(buf), "score  %05lu", (unsigned long)g.score);
  drawTextCenter(buf, SCREEN_W / 2, by + 42, COL_TEXT, COL_SKY_TOP, 1);
  snprintf(buf, sizeof(buf), "best   %05lu", (unsigned long)g.bestScore);
  drawTextCenter(buf, SCREEN_W / 2, by + 56, COL_TEXT, COL_SKY_TOP, 1);
  if (g.newBest) {
    drawTextCenter("NEW BEST!", SCREEN_W / 2, by + 72, COL_RED, COL_SKY_TOP, 1);
  } else if ((frameCount / 20) & 1) {
    drawTextCenter("press BOOT to retry", SCREEN_W / 2, by + 72, COL_TEXT_DIM, COL_SKY_TOP, 1);
  }

  flushCanvas();
}
