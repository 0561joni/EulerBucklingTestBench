#include <CheapStepper.h>
#include <HX711_ADC.h>
#include <EEPROM.h>

#define MAX_FORCE 2000
#define MOTOR_SPEED 6 //must be between 6 and 22
#define LEAD 8
#define DEVICENAME "EulerBucklingTestBench"
#define PROTOCOL_VERSION 1

HX711_ADC LoadCell(2, 3);
CheapStepper stepper (8, 9, 10, 11);
const int calVal_eepromAdress = 0;
long t;
int globalSteps = 0;
int rot = 0;
int lastSteps = 0;
bool motorStart = false;
bool motorDir = true;

void lcSetup() {
  Serial.println("Starting up loadcell...");
  LoadCell.begin();
  float calibrationValue; // calibration value (see example file "Calibration.ino")
  EEPROM.get(calVal_eepromAdress, calibrationValue); // uncomment this if you want to fetch the calibration value from eeprom
  long stabilizingtime = 2000; // preciscion right after power-up can be improved by adding a few seconds of stabilizing time
  LoadCell.start(stabilizingtime, true);
  if (LoadCell.getTareTimeoutFlag()) {
    Serial.println("Timeout, check MCU>HX711 wiring and pin designations");
    while (1);
  }
  else {
    LoadCell.setCalFactor(calibrationValue); // set calibration value (float)
    Serial.println("ready");
  }
}

void readCell() {
  bool newDataReady = false;
  // check for new data/start next conversion:
  if (LoadCell.update()) newDataReady = true;
  // get smoothed value from the dataset:
  if (newDataReady) {
    float i = LoadCell.getData();
    int steps = stepper.getStep();
    if (motorDir && steps < lastSteps) {
      rot += 1;
    }
    else if (!motorDir && steps > lastSteps) {
      rot -= 1;
    }
    lastSteps = steps;
    globalSteps = rot * 4096 + steps;
    if (motorStart) {
      Serial.print("steps:");
      Serial.print(globalSteps);
      Serial.print(" dist:");
      Serial.print(LEAD * (rot + (float)steps / 4096));
      Serial.print(" load:");
      Serial.println(i);
      if (i > MAX_FORCE) {
        Serial.println("stopped because of overload");
        motorStart = false;
      }
    }
    newDataReady = 0;
    t = millis();

  }
}

void readSerial() {
  // receive command from serial terminal, send 'tare' to initiate tare operation:
  static String buf = "";
  if (Serial.available() > 0) {
    char c = Serial.read();
    buf += c;
    if (c == '\n') {
      buf.remove(buf.length() - 1);
      if (buf == "tare") LoadCell.tareNoDelay();
      else if (buf == "go") {
        motorStart = true;
      }
      else if (buf == "stop") {
        motorStart = false;
        stepper.off();
      }
      else if (buf == "switchDir" && motorStart == false) {
        motorDir = !motorDir;
      }
      else if (buf == "reverse") {
        stepper.move(!motorDir,globalSteps);
        motorStart = false;
        globalSteps = 0;
        lastSteps = 0;
        rot = 0; 
        stepper.off();
      }
      buf = "";
    }
  }

  // check if last tare operation is complete:
  if (LoadCell.getTareStatus() == true) {
    Serial.println("Tare complete");
  }
}

void setup() {
  Serial.begin(115200); delay(10);
  Serial.println(DEVICENAME);
  Serial.print("protocol version: ");
  Serial.println(PROTOCOL_VERSION);
  lcSetup();
  stepper.setRpm(MOTOR_SPEED);

}

void loop() {
  readCell();
  readSerial();
  if (motorStart) {
    stepper.move(motorDir, 1);
  }
}
