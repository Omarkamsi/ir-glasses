/*
 * IR Counter-Surveillance Glasses — Firmware Skeleton
 * Target: ESP32-C3 (Arduino core), e.g. ESP32-C3 SuperMini
 *
 * Drives an IR-LED array through a logic-level N-MOSFET using hardware PWM (LEDC).
 * A push button cycles through pulsing modes. Optional battery-voltage monitor over serial.
 *
 * Modes:
 *   0 OFF
 *   1 STEADY      high duty, continuous-style IR wash
 *   2 PULSE_LOW   ~120 Hz, low duty  -> rolling-shutter banding
 *   3 PULSE_HIGH  ~480 Hz, low duty  -> max overdrive bursts
 *
 * --- ESP32 Arduino core version note ---
 *   This file uses the channel-based LEDC API from core 2.0.x:
 *       ledcSetup(channel, freq, resBits) / ledcAttachPin(pin, channel) / ledcWrite(channel, duty)
 *   On core 3.0.x the API changed to pin-based:
 *       ledcAttach(pin, freq, resBits) / ledcWrite(pin, duty) / ledcChangeFrequency(pin, freq, resBits)
 *   If you're on 3.x, swap the three LEDC calls accordingly (see comments below).
 *
 * SAFETY: keep duty cycles low for "overdrive". Verify LED current with a multimeter and
 * confirm the LEDs/MOSFET do not overheat. Aim LEDs outward, away from eyes.
 */

#include <Arduino.h>

// ---------------- Pin map (adjust to your wiring) ----------------
const int MOSFET_PIN = 4;   // PWM output -> MOSFET gate
const int BUTTON_PIN = 9;   // mode button to GND (internal pull-up)
const int STATUS_LED = 8;   // onboard LED on many C3 boards (active LOW)
const int VBAT_PIN   = 3;   // ADC pin for optional battery divider

// ---------------- PWM config ----------------
const int PWM_CHANNEL  = 0;
const int PWM_RES_BITS = 10;                 // 10-bit resolution -> duty 0..1023
const int PWM_MAX      = (1 << PWM_RES_BITS) - 1;

// ---------------- Mode table ----------------
struct Mode { const char* name; int freqHz; int dutyPct; };
Mode modes[] = {
  {"OFF",        1,   0 },
  {"STEADY",     200, 70},
  {"PULSE_LOW",  120, 15},
  {"PULSE_HIGH", 480, 15},
};
const int NUM_MODES = sizeof(modes) / sizeof(modes[0]);
int currentMode = 0;

// ---------------- Button debounce ----------------
int lastBtn = HIGH;
unsigned long lastBtnMs = 0;
const unsigned long DEBOUNCE_MS = 40;

void applyMode(int m) {
  // core 2.x:
  ledcChangeFrequency(PWM_CHANNEL, modes[m].freqHz, PWM_RES_BITS);
  int duty = (int)((long)modes[m].dutyPct * PWM_MAX / 100);
  ledcWrite(PWM_CHANNEL, duty);
  // core 3.x equivalent:
  //   ledcChangeFrequency(MOSFET_PIN, modes[m].freqHz, PWM_RES_BITS);
  //   ledcWrite(MOSFET_PIN, duty);

  // status LED: on (active-low) when emitting, off when OFF mode
  digitalWrite(STATUS_LED, (m == 0) ? HIGH : LOW);

  Serial.printf("Mode %d: %-10s  freq=%4d Hz  duty=%2d%%\n",
                m, modes[m].name, modes[m].freqHz, modes[m].dutyPct);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED, OUTPUT);

  // core 2.x LEDC setup:
  ledcSetup(PWM_CHANNEL, modes[0].freqHz, PWM_RES_BITS);
  ledcAttachPin(MOSFET_PIN, PWM_CHANNEL);
  // core 3.x equivalent:
  //   ledcAttach(MOSFET_PIN, modes[0].freqHz, PWM_RES_BITS);

  applyMode(currentMode);
  Serial.println("IR glasses ready. Press button to cycle modes.");
}

void loop() {
  // ---- button: cycle modes on press ----
  int btn = digitalRead(BUTTON_PIN);
  if (btn != lastBtn && (millis() - lastBtnMs) > DEBOUNCE_MS) {
    lastBtnMs = millis();
    if (btn == LOW) {                                  // pressed (active low)
      currentMode = (currentMode + 1) % NUM_MODES;
      applyMode(currentMode);
    }
    lastBtn = btn;
  }

  // ---- optional battery monitor every 5 s ----
  static unsigned long lastBat = 0;
  if (millis() - lastBat > 5000) {
    lastBat = millis();
    int raw = analogRead(VBAT_PIN);
    // With a 2x divider (100k/100k): Vbat = (raw/4095)*3.3*2
    float vbat = (raw / 4095.0f) * 3.3f * 2.0f;
    Serial.printf("VBAT ~ %.2f V\n", vbat);
  }
}
