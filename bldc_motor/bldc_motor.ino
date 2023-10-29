#include <Servo.h>

int defPin = 9;
int CH1 = 3;
int CH2 = 5;
int CH3 = 6;
int CH4 = 9;
int CH5 = 10;


Servo ESC;
int potValue;

int readChannel(int channelInput, int minLimit, int maxLimit, int defaultValue) {
  int ch = pulseIn(channelInput, HIGH, 30000);
  if (ch < 100) return defaultValue;
  return map(ch, 1000, 2000, minLimit, maxLimit);  
}

bool readSwitch(byte channelInput, bool defaultValue) {
  int intDefaultValue = (defaultValue)? 100: 0;
  int ch = readChannel(channelInput, 0, 100, intDefaultValue);
  return (ch > 50);  
}

void setup() {
  Serial.begin(115200);
  ESC.attach(defPin, 1000, 2000);
  pinMode(CH1, INPUT);
  pinMode(CH2, INPUT);
  pinMode(CH3, INPUT);
  pinMode(CH4, INPUT);
  pinMode(CH5, INPUT); 
}

int ch1Value, ch2Value, ch3Value, ch4Value;
bool ch5Value;

void loop() {
  h1Value = readChannel(CH1, -100, 100, 0);
  ch2Value = readChannel(CH2, -100, 100, 0);
  ch3Value = readChannel(CH3, -100, 100, -100);
  ch4Value = readChannel(CH4, -100, 100, 0);
  ch5Value = readSwitch(CH5, false);
  
  Serial.print("Ch1: ");
  Serial.print(ch1Value);
  Serial.print(" Ch2: ");
  Serial.print(ch2Value);
  Serial.print(" Ch3: ");
  Serial.print(ch3Value);
  Serial.print(" Ch4: ");
  Serial.print(ch4Value);
  Serial.print(" Ch5: ");
  Serial.println(ch5Value);
  delay(500);
  
  potValue = analogRead(A0);
  potValue = map(potValue, 0, 1023, 0, 180);
  ESC.write(potValue);  
}
