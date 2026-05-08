#include <Wire.h>
#include <Adafruit_ADS1X15.h>

Adafruit_ADS1115 ads;

// --- Konfigurasi ---
#define BAUDRATE 9600
#define ADS_GAIN GAIN_TWO   // ±2.048 V
float lsb;                 // Volt per bit

void setup() {
  Serial.begin(BAUDRATE);

  if (!ads.begin()) {
    while (1); // kalau ADS tidak ketemu, berhenti
  }

  ads.setGain(ADS_GAIN);

  // Hitung LSB sesuai PGA
  float vfsr;
  switch (ADS_GAIN) {
    case GAIN_TWOTHIRDS: vfsr = 6.144; break;
    case GAIN_ONE:       vfsr = 4.096; break;
    case GAIN_TWO:       vfsr = 2.048; break;
    case GAIN_FOUR:      vfsr = 1.024; break;
    case GAIN_EIGHT:     vfsr = 0.512; break;
    case GAIN_SIXTEEN:   vfsr = 0.256; break;
    default:             vfsr = 2.048; break;
  }

  lsb = vfsr / 32768.0; // ADS1115 single-ended = 15 bit
}

void loop() {
  int16_t raw = ads.readADC_SingleEnded(0); // A0 ke GND
  float voltage = raw * lsb;

  Serial.println(voltage, 8);
  delay(1000);
}
