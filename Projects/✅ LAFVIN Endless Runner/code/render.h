#pragma once
#include <Arduino_GFX_Library.h>
#include "game.h"

bool renderInit();
void renderFrame(const GameState& g, uint32_t frameCount);
void renderTitle(uint32_t bestScore, uint32_t frameCount);
void renderGameOver(const GameState& g, uint32_t frameCount);
