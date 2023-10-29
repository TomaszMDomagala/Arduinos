#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <string.h>


unsigned int screen_width = 128;
unsigned int screen_height = 32;

Adafruit_SSD1306 display(screen_width, screen_height, &Wire, -1);
Adafruit_BME280 bme;
BH1750 light;

void setup() {

  Serial.begin(9600);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    while (true);
  }

  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    while (true);
  }

  light.begin();

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);

  delay(2000);

}

void loop() {

  Serial.print("Temperature = ");
  Serial.print(bme.readTemperature());
  Serial.println("*C");

  Serial.print("Pressure = ");
  Serial.print(bme.readPressure() / 100.0F);
  Serial.println(" hPa");

  Serial.print("Humidity = ");
  Serial.print(bme.readHumidity());
  Serial.println("%");

  Serial.print("Light = ");
  Serial.print(light.readLightLevel());
  Serial.println(" lux");

  Serial.println();

  display.clearDisplay();
  display.setCursor(0, 10);
  // Display static text
  display.println("Hello, world!");
  display.display(); 

}
