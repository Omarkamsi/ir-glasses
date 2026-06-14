/*
 * IR Counter-Surveillance Glasses — Firmware
 * Target: ESP32-C3 (Arduino core), e.g. ESP32-C3 SuperMini
 *
 * Drives an IR-LED array through a logic-level N-MOSFET using hardware PWM (LEDC).
 * A push button cycles preset pulsing modes, and a line-based SERIAL COMMAND INTERFACE
 * lets a host PC set a numeric intensity / frequency for controlled data capture — so the
 * captured frames map directly onto the evaluation pipeline's intensity axis
 * (software/experiment.py --real-dir). An optional battery monitor warns and protects the
 * LiPo at low voltage.
 *
 * Preset modes (button cycles):
 *   0 OFF
 *   1 STEADY      ~200 Hz, high duty  -> continuous-style IR wash
 *   2 PULSE_LOW   ~120 Hz, low duty   -> rolling-shutter banding
 *   3 PULSE_HIGH  ~480 Hz, low duty   -> max overdrive bursts
 *
 * Serial commands (115200 baud, newline-terminated):
 *   I<0-100>   set EXPERIMENT intensity = PWM duty %, at the experiment frequency.
 *              Maps to the capture folders: I0->0.0  I30->0.3  I60->0.6  I100->1.0
 *   F<hz>      set the experiment pulse frequency (Hz); ~120 Hz gives rolling-shutter bands
 *   M<0-3>     select a preset mode (leaves experiment mode)
 *   S          print status (mode, intensity, freq, battery)
 *   H          help
 *
 * --- ESP32 Arduino core compatibility ---
 *   This file compiles on BOTH core 2.x (channel-based LEDC) and core 3.x (pin-based LEDC)
 *   via the LEDC_* macros below — no manual edits needed.
 *
 * SAFETY: keep duty cycles modest for "overdrive". Verify LED current with a multimeter and
 * confirm the LEDs/MOSFET do not overheat. Aim LEDs outward, away from eyes. See
 * docs/IR_Glasses_Build_Guide.md §7 and hardware/safety_iec62471.py.
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

// ---------------- Battery monitor ----------------
const float VBAT_DIVIDER = 2.0f;             // 100k/100k divider -> x2
const float VBAT_LOW     = 3.30f;            // warn + fast-blink below this (1S LiPo)
const float VBAT_CRIT    = 3.00f;            // force OFF below this to protect the cell

// ---------------- LEDC compatibility (core 2.x and 3.x) ----------------
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  #define LEDC_SETUP(pin, ch, freq, res)  ledcAttach((pin), (freq), (res))
  #define LEDC_WRITE(pin, ch, duty)       ledcWrite((pin), (duty))
  #define LEDC_FREQ(pin, ch, freq, res)   ledcChangeFrequency((pin), (freq), (res))
#else
  #define LEDC_SETUP(pin, ch, freq, res)  do { ledcSetup((ch), (freq), (res)); \
                                               ledcAttachPin((pin), (ch)); } while (0)
  #define LEDC_WRITE(pin, ch, duty)       ledcWrite((ch), (duty))
  #define LEDC_FREQ(pin, ch, freq, res)   ledcChangeFrequency((ch), (freq), (res))
#endif

// ---------------- Mode table ----------------
struct Mode { const char* name; int freqHz; int dutyPct; };
Mode modes[] = {
  {"OFF",        1,   0 },
  {"STEADY",     200, 70},
  {"PULSE_LOW",  120, 15},
  {"PULSE_HIGH", 480, 15},
};
const int NUM_MODES = sizeof(modes) / sizeof(modes[0]);

// ---------------- Runtime state ----------------
int  currentMode    = 0;
int  curFreq        = 1;       // currently applied PWM frequency (Hz)
int  curDutyPct     = 0;       // currently applied duty (%)
int  expFreq        = 120;     // experiment pulse frequency (rolling-shutter banding)
bool experimentMode = false;   // true once an I/F command is issued
bool batteryCutoff  = false;   // latched when VBAT < VBAT_CRIT

// ---------------- Button debounce ----------------
int lastBtn = HIGH;
unsigned long lastBtnMs = 0;
const unsigned long DEBOUNCE_MS = 40;

// ---------------- Core PWM apply ----------------
void applyPwm(int freqHz, int dutyPct) {
  freqHz  = constrain(freqHz, 1, 20000);
  dutyPct = constrain(dutyPct, 0, 100);
  LEDC_FREQ(MOSFET_PIN, PWM_CHANNEL, freqHz, PWM_RES_BITS);
  int duty = (int)((long)dutyPct * PWM_MAX / 100);
  LEDC_WRITE(MOSFET_PIN, PWM_CHANNEL, duty);
  curFreq = freqHz;
  curDutyPct = dutyPct;
  digitalWrite(STATUS_LED, (dutyPct > 0) ? LOW : HIGH);  // active-low: on while emitting
}

void applyMode(int m) {
  experimentMode = false;
  currentMode = m;
  applyPwm(modes[m].freqHz, modes[m].dutyPct);
  Serial.printf("Mode %d: %-10s  freq=%4d Hz  duty=%2d%%\n",
                m, modes[m].name, modes[m].freqHz, modes[m].dutyPct);
}

float readVbat() {
  int raw = analogRead(VBAT_PIN);
  return (raw / 4095.0f) * 3.3f * VBAT_DIVIDER;
}

void printStatus() {
  const char* label = experimentMode ? "EXPERIMENT" : modes[currentMode].name;
  Serial.printf("STATUS  mode=%s  intensity=%d%%  freq=%d Hz  vbat=%.2f V%s\n",
                label, curDutyPct, curFreq, readVbat(),
                batteryCutoff ? "  [BATT CUTOFF]" : "");
}

void printHelp() {
  Serial.println(F("Commands: I<0-100> intensity%  F<hz> freq  M<0-3> preset  S status  H help"));
  Serial.println(F("Capture mapping: I0->0.0  I30->0.3  I60->0.6  I100->1.0"));
}

void processCmd(String s) {
  s.trim();
  if (s.length() == 0) return;
  char cmd = toupper(s[0]);
  long val = s.substring(1).toInt();
  if (batteryCutoff && (cmd == 'I' || cmd == 'F' || cmd == 'M')) {
    Serial.println(F("refused: battery cutoff active (recharge the cell)"));
    return;
  }
  switch (cmd) {
    case 'I':
      experimentMode = true;
      applyPwm(expFreq, (int)val);
      Serial.printf("intensity=%d%%  (freq=%d Hz)\n", curDutyPct, curFreq);
      break;
    case 'F':
      expFreq = constrain((int)val, 1, 20000);
      if (experimentMode) applyPwm(expFreq, curDutyPct);
      Serial.printf("experiment freq=%d Hz\n", expFreq);
      break;
    case 'M':
      if (val >= 0 && val < NUM_MODES) applyMode((int)val);
      else Serial.println(F("? mode out of range (0-3)"));
      break;
    case 'S': printStatus(); break;
    case 'H': printHelp(); break;
    default:  Serial.println(F("? unknown command; send H for help"));
  }
}

void handleSerial() {
  static String buf;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (buf.length()) { processCmd(buf); buf = ""; }
    } else if (buf.length() < 32) {
      buf += c;
    }
  }
}

void handleButton() {
  int btn = digitalRead(BUTTON_PIN);
  if (btn != lastBtn && (millis() - lastBtnMs) > DEBOUNCE_MS) {
    lastBtnMs = millis();
    if (btn == LOW && !batteryCutoff) {                // pressed (active low)
      currentMode = (currentMode + 1) % NUM_MODES;
      applyMode(currentMode);
    }
    lastBtn = btn;
  }
}

void handleBattery() {
  static unsigned long lastBat = 0;
  if (millis() - lastBat < 5000) return;
  lastBat = millis();
  float v = readVbat();
  if (v < VBAT_CRIT) {
    if (!batteryCutoff) {
      batteryCutoff = true;
      applyPwm(1, 0);                                  // force LEDs OFF to protect the cell
      Serial.printf("CRITICAL: VBAT %.2f V < %.2f V — LEDs forced OFF\n", v, VBAT_CRIT);
    }
  } else if (v < VBAT_LOW) {
    Serial.printf("WARNING: VBAT low %.2f V\n", v);
    for (int i = 0; i < 4; i++) {                      // fast-blink the status LED
      digitalWrite(STATUS_LED, HIGH); delay(60);
      digitalWrite(STATUS_LED, LOW);  delay(60);
    }
    digitalWrite(STATUS_LED, (curDutyPct > 0) ? LOW : HIGH);
  } else {
    Serial.printf("VBAT ~ %.2f V\n", v);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED, OUTPUT);

  LEDC_SETUP(MOSFET_PIN, PWM_CHANNEL, modes[0].freqHz, PWM_RES_BITS);
  applyMode(currentMode);

  Serial.println(F("IR glasses ready. Button cycles modes; send H for serial commands."));
}

void loop() {
  handleSerial();
  handleButton();
  handleBattery();
}
