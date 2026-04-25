#include "game.h"

static void spawnObstacle(GameState& g) {
  if (g.obsCount >= GameState::MAX_OBS) return;
  ObstacleType t;
  uint8_t w, h;
  uint8_t r = random(100);
  if (r < 55)      { t = ObstacleType::CactusShort; w = 8;  h = 14; }
  else if (r < 85) { t = ObstacleType::CactusTall;  w = 8;  h = 22; }
  else             { t = ObstacleType::CactusWide;  w = 16; h = 14; }
  g.obs[g.obsCount++] = Obstacle{ (float)SCREEN_W + 4, t, w, h };
}

static bool aabb(int ax, int ay, int aw, int ah,
                 int bx, int by, int bw, int bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

void gameReset(GameState& g, uint32_t best) {
  g.phase = Phase::Playing;
  g.playerY = GROUND_Y - PLAYER_H;
  g.playerVY = 0.0f;
  g.onGround = true;
  g.jumpHeld = false;
  g.speed = SPEED_START;
  g.worldX = 0.0f;
  g.spawnCooldown = 1.0f;
  g.obsCount = 0;
  g.score = 0;
  g.bestScore = best;
  g.newBest = false;
  g.justJumped = false;
  g.justDied = false;
}

void gameStep(GameState& g, float dt,
              bool buttonDown, bool buttonPressedEdge, bool buttonReleasedEdge) {
  g.justJumped = false;
  g.justDied = false;

  if (g.phase != Phase::Playing) return;

  // Input → jump
  if (buttonPressedEdge && g.onGround) {
    g.playerVY = JUMP_VY;
    g.onGround = false;
    g.jumpHeld = true;
    g.justJumped = true;
  }
  if (buttonReleasedEdge && g.jumpHeld) {
    g.jumpHeld = false;
    if (g.playerVY < JUMP_CUT_VY) g.playerVY = JUMP_CUT_VY;  // variable jump
  }

  // Physics
  g.playerVY += GRAVITY * dt;
  g.playerY  += g.playerVY * dt;
  if (g.playerY >= GROUND_Y - PLAYER_H) {
    g.playerY = GROUND_Y - PLAYER_H;
    g.playerVY = 0.0f;
    g.onGround = true;
    g.jumpHeld = false;
  }

  // Speed ramp
  g.speed += SPEED_RAMP * dt;
  if (g.speed > SPEED_MAX) g.speed = SPEED_MAX;

  // Scroll & score (1 point per 10 px)
  float dx = g.speed * dt;
  g.worldX += dx;
  g.score = (uint32_t)(g.worldX / 10.0f);

  // Move obstacles
  uint8_t w = 0;
  for (uint8_t i = 0; i < g.obsCount; ++i) {
    g.obs[i].x -= dx;
    if (g.obs[i].x + g.obs[i].w > 0) g.obs[w++] = g.obs[i];
  }
  g.obsCount = w;

  // Spawn
  g.spawnCooldown -= dt;
  if (g.spawnCooldown <= 0.0f && g.obsCount < GameState::MAX_OBS) {
    spawnObstacle(g);
    // Min gap shrinks as speed grows. seconds = gapPx / speed.
    float gapPx = (float)random(80, 160) - (g.speed - SPEED_START) * 0.25f;
    if (gapPx < 60.0f) gapPx = 60.0f;
    g.spawnCooldown = gapPx / g.speed;
  }

  // Collision (2 px forgiveness)
  int px = PLAYER_X + 2;
  int py = (int)g.playerY + 2;
  int pw = PLAYER_W - 4;
  int ph = PLAYER_H - 4;
  for (uint8_t i = 0; i < g.obsCount; ++i) {
    int ox = (int)g.obs[i].x;
    int oh = g.obs[i].h;
    int oy = GROUND_Y - oh;
    int ow = g.obs[i].w;
    if (aabb(px, py, pw, ph, ox + 1, oy + 1, ow - 2, oh - 2)) {
      g.phase = Phase::GameOver;
      g.justDied = true;
      if (g.score > g.bestScore) {
        g.bestScore = g.score;
        g.newBest = true;
      }
      return;
    }
  }
}
