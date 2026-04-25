#pragma once
#include <Arduino.h>

void ledInit();
void ledOnEvent(bool justJumped, bool justDied, bool newBest);
void ledTick(bool playing, uint32_t nowMs);   // call every frame
