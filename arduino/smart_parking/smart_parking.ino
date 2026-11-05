// ==========================================================
//  SMART PARKING - 2 live slots, streams status over USB
//  Output line (every ~0.3 s):  S1=1,S2=0,D1=7,D2=999
//    S1/S2 = slot full (1) or empty (0)
//    D1/D2 = measured distance in cm (999 = no echo / nothing in range)
// ==========================================================

// LED pins
const int slot1Green = 4;
const int slot1Red   = 5;
const int slot2Green = 6;
const int slot2Red   = 7;
const int entryGreen = 8;
const int entryRed   = 9;

// Ultrasonic sensor pins
const int trigPin1 = 10;
const int echoPin1 = 11;
const int trigPin2 = 12;
const int echoPin2 = 13;

// Detection settings (hysteresis stops flickering near the threshold)
const int FULL_BELOW_CM  = 50;   // closer than this  -> slot becomes FULL
const int EMPTY_ABOVE_CM = 55;   // farther than this -> slot becomes EMPTY
const int NO_ECHO        = 999;

bool slot1Full = false;
bool slot2Full = false;

void setup() {
  Serial.begin(9600);

  pinMode(slot1Green, OUTPUT);
  pinMode(slot1Red,   OUTPUT);
  pinMode(slot2Green, OUTPUT);
  pinMode(slot2Red,   OUTPUT);
  pinMode(entryGreen, OUTPUT);
  pinMode(entryRed,   OUTPUT);

  pinMode(trigPin1, OUTPUT);
  pinMode(echoPin1, INPUT);
  pinMode(trigPin2, OUTPUT);
  pinMode(echoPin2, INPUT);

  Serial.println("BOOT");
}

// One ultrasonic reading in cm. Times out after 30 ms instead of 1 s.
int readOnce(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, 30000UL);
  if (duration == 0) return NO_ECHO;
  return (int)(duration * 0.0343 / 2);
}

// Median of 3 readings - throws away a single bad reading.
int readMedian(int trigPin, int echoPin) {
  int a = readOnce(trigPin, echoPin); delay(10);
  int b = readOnce(trigPin, echoPin); delay(10);
  int c = readOnce(trigPin, echoPin);
  int t;
  if (a > b) { t = a; a = b; b = t; }
  if (b > c) { t = b; b = c; c = t; }
  if (a > b) { t = a; a = b; b = t; }
  return b;
}

bool updateSlot(bool isFull, int d) {
  if (!isFull && d > 0 && d < FULL_BELOW_CM) return true;
  if (isFull && d > EMPTY_ABOVE_CM)          return false;
  return isFull;
}

void setPair(int greenPin, int redPin, bool full) {
  digitalWrite(greenPin, full ? LOW : HIGH);
  digitalWrite(redPin,   full ? HIGH : LOW);
}

void loop() {
  int d1 = readMedian(trigPin1, echoPin1);
  delay(40);                                   // let sensor 1's echo die out (avoids crosstalk)
  int d2 = readMedian(trigPin2, echoPin2);

  slot1Full = updateSlot(slot1Full, d1);
  slot2Full = updateSlot(slot2Full, d2);

  setPair(slot1Green, slot1Red, slot1Full);
  setPair(slot2Green, slot2Red, slot2Full);
  setPair(entryGreen, entryRed, slot1Full && slot2Full);   // red entry light = lot full

  // Machine-readable line for the laptop server
  Serial.print("S1=");  Serial.print(slot1Full ? 1 : 0);
  Serial.print(",S2="); Serial.print(slot2Full ? 1 : 0);
  Serial.print(",D1="); Serial.print(d1);
  Serial.print(",D2="); Serial.println(d2);

  delay(100);
}
