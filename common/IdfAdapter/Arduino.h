// Arduino.h, Version: 1.01
#pragma once
// Narrow IDF adapter for the unchanged shared rescue sources; no Arduino SDK.
#include <cstdint>
#include <string>
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
using String = std::string;
#define F(Text) Text
constexpr int LOW = 0;
constexpr int HIGH = 1;
constexpr int INPUT_PULLUP = 2;
constexpr int OUTPUT = 3;
inline void delay(unsigned long Milliseconds)
 {
  const TickType_t Ticks = pdMS_TO_TICKS(Milliseconds);
  vTaskDelay(Milliseconds && !Ticks ? 1 : Ticks);
 }
inline void pinMode(int Pin, int Mode)
 {
  gpio_config_t Config = {};
  Config.pin_bit_mask = 1ULL << Pin;
  Config.mode = Mode == OUTPUT ? GPIO_MODE_OUTPUT : GPIO_MODE_INPUT;
  Config.pull_up_en = Mode == INPUT_PULLUP ? GPIO_PULLUP_ENABLE : GPIO_PULLUP_DISABLE;
  ESP_ERROR_CHECK(gpio_config(&Config));
 }
inline void digitalWrite(int Pin, int Level) { ESP_ERROR_CHECK(gpio_set_level((gpio_num_t)Pin, Level)); }
