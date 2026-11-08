// Host-side tests for arduino/smart_parking/smart_parking.ino.
// The sketch is #included unchanged, so these tests run the real firmware logic.
#include "mock_arduino.h"
#include "../../arduino/smart_parking/smart_parking.ino"

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { std::printf("FAIL: %s\n", msg); failures++; } } while (0)

static void script(std::vector<unsigned long> v) { g_echo = v; g_echo_i = 0; }

int main() {
  // readOnce: echo time -> centimetres (truncated), 0 -> NO_ECHO
  script({1750});  CHECK(readOnce(trigPin1, echoPin1) == 30, "1750 us should read 30 cm");
  script({2915});  CHECK(readOnce(trigPin1, echoPin1) == 49, "2915 us truncates to 49 cm");
  script({0});     CHECK(readOnce(trigPin1, echoPin1) == NO_ECHO, "no echo should read 999");

  // readMedian: one bad reading in three is thrown away
  script({1750, 20000, 1750}); CHECK(readMedian(trigPin1, echoPin1) == 30, "median should ignore a spike");
  script({0, 1750, 1750});     CHECK(readMedian(trigPin1, echoPin1) == 30, "median should ignore one missed echo");
  script({0, 0, 1750});        CHECK(readMedian(trigPin1, echoPin1) == NO_ECHO, "two misses of three give no echo");

  // updateSlot: hysteresis between 50 and 55 cm
  CHECK(updateSlot(false, 49) == true,   "empty -> full below 50");
  CHECK(updateSlot(false, 50) == false,  "empty stays empty at 50");
  CHECK(updateSlot(false, NO_ECHO) == false, "empty stays empty with no echo");
  CHECK(updateSlot(true, 55) == true,    "full stays full at 55");
  CHECK(updateSlot(true, 53) == true,    "full stays full inside the band");
  CHECK(updateSlot(true, 56) == false,   "full -> empty above 55");
  CHECK(updateSlot(true, NO_ECHO) == false, "full -> empty when nothing is in range");
  CHECK(updateSlot(false, 0) == false,   "a zero reading is ignored");

  // setPair: green on when empty, red on when full
  setPair(slot1Green, slot1Red, false); CHECK(g_pin[slot1Green] == HIGH && g_pin[slot1Red] == LOW, "empty = green");
  setPair(slot1Green, slot1Red, true);  CHECK(g_pin[slot1Green] == LOW && g_pin[slot1Red] == HIGH, "full = red");

  // loop(): sensor 1 sees a car at 30 cm, sensor 2 sees 120 cm (empty)
  slot1Full = slot2Full = false; g_serial.clear();
  script({1750,1750,1750, 7000,7000,7000});
  loop();
  CHECK(g_serial == "S1=1,S2=0,D1=30,D2=120\n", ("serial line was: " + g_serial).c_str());
  CHECK(g_pin[slot1Red] == HIGH && g_pin[slot2Green] == HIGH, "slot LEDs follow the state");
  CHECK(g_pin[entryGreen] == HIGH && g_pin[entryRed] == LOW, "entry stays green while one slot is free");

  // both slots full -> entry turns red
  g_serial.clear();
  script({1750,1750,1750, 1750,1750,1750});
  loop();
  CHECK(g_pin[entryRed] == HIGH && g_pin[entryGreen] == LOW, "entry red when both slots are full");

  if (failures == 0) std::printf("firmware: all checks passed\n");
  return failures ? 1 : 0;
}
