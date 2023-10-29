#include <Stepper.h>
#include "CRSFforArduino.h"

const int stepsPerRevolution = 200;

Stepper myStepper(stepsPerRevolution, 8, 9, 10, 11);
int stepCount = 0;

void setup() {
  Serial.begin(9600);

}

void loop() {
  int sensorReading = analogRead(A0);
  Serial.println(sensorReading);
  int motorSpeed = map(sensorReading, 0, 1023, 0, 100);
  if (motorSpeed > 0) {
    myStepper.setSpeed(motorSpeed);
    myStepper.step(stepsPerRevolution / 100);  
  }
}
