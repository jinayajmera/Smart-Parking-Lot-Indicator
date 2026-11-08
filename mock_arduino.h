// Minimal stand-in for the Arduino core so the REAL sketch can be compiled and
// tested on a PC. The sketch itself is included unchanged by test_firmware.cpp.
#pragma once
#include <string>
#include <vector>
#include <map>
#include <cstdio>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1

static std::map<int,int> g_pin;                 // last value written to each pin
static std::vector<unsigned long> g_echo;       // scripted pulseIn() results
static size_t g_echo_i = 0;
static std::string g_serial;                    // everything the sketch printed
static unsigned long g_delay_ms = 0;            // total delay() time requested

inline void pinMode(int, int) {}
inline void digitalWrite(int p, int v) { g_pin[p] = v; }
inline void delay(unsigned long ms) { g_delay_ms += ms; }
inline void delayMicroseconds(unsigned int) {}
inline unsigned long pulseIn(int, int, unsigned long) {
  return g_echo_i < g_echo.size() ? g_echo[g_echo_i++] : 0;
}

struct SerialMock {
  void begin(long) {}
  void print(const char* s) { g_serial += s; }
  void print(int v) { g_serial += std::to_string(v); }
  void println(const char* s) { g_serial += s; g_serial += "\n"; }
  void println(int v) { g_serial += std::to_string(v); g_serial += "\n"; }
};
static SerialMock Serial;
