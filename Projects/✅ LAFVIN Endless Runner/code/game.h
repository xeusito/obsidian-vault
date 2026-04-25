#pragma once
#include <Arduino.h>

// Screen layout (landscape)
static constexpr int SCREEN_W = 320;
static constexpr int SCREEN_H = 172;
static constexpr int GROUND_Y = 140;     // top of ground line
static constexpr int PLAYER_X = 40;
static constexpr int PLAYER_W = 14;
static constexpr int PLAYER_H = 18;

enum class ObstacleType : uint8_t {
  CactusShort,
  CactusTall,
  CactusWide,
};

struct Obstacle {
  float x;
  ObstacleType type;
  uint8_t w, h;
};

enum class Phase : uint8_t {
  Title,
  Playing,
  GameOver,
};

struct GameState {
  Phase phase = Phase::Title;

  // Player
  float playerY = GROUND_Y - PLAYER_H;
  float playerVY = 0.0f;
  bool  onGround = true;
  bool  jumpHeld = false;

  // World
  float speed = 90.0f;          // px/sec, ramps up
  float worldX = 0.0f;          // total scrolled distance
  float spawnCooldown = 0.0f;   // seconds until next obstacle spawn

  static constexpr int MAX_OBS = 6;
  Obstacle obs[MAX_OBS];
  uint8_t  obsCount = 0;

  // Score
  uint32_t score = 0;
  uint32_t bestScore = 0;
  bool     newBest = false;

  // Edge-triggered events for the LED / renderer
  bool justJumped = false;
  bool justDied   = false;
};

// Tunables
static constexpr float GRAVITY      = 1400.0f;  // px/s^2
static constexpr float JUMP_VY      = -520.0f;  // initial jump impulse
static constexpr float JUMP_CUT_VY  = -180.0f;  // velocity clamp on early release
static constexpr float SPEED_START  = 90.0f;
static constexpr float SPEED_MAX    = 240.0f;
static constexpr float SPEED_RAMP   = 4.0f;     // px/s added per second of play

void gameReset(GameState& g, uint32_t best);
void gameStep(GameState& g, float dt, bool buttonDown, bool buttonPressedEdge, bool buttonReleasedEdge);
