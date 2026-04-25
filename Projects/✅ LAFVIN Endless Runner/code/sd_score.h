#pragma once
#include <Arduino.h>

bool     sdInit();              // returns true if SD mounted
uint32_t sdReadHighScore();     // 0 if file missing or SD unavailable
void     sdWriteHighScore(uint32_t score);
