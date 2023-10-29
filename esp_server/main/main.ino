#include <Wire.h>
#include <BH1750.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <string.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

struct UNITS {
  float temperature;
  float pressure;
  float humidity;
  float light;
};

struct WIFISettings
{
    char* ssid;
    char* password;
    char* ip;
    uint ServerPort;
} wifiSettings = {"UPC3739675", "Zz3dvtzkhxw7", "192.168.0.205", 8080};

struct Settings
{
    int timeBetweenRequests;
    int dataNeeded;
};

// TCP server https://techtutorialsx.com/2017/11/13/esp32-arduino-setting-a-socket-server/
WiFiServer Server(wifiSettings.ServerPort);
Adafruit_BME280 bme;
BH1750 light;

void setup()
{
    Serial.begin(115200);

    if (!bme.begin(0x76)) {
        Serial.println("Could not find a valid BME280 sensor, check wiring!");
        while (true);
    }

    if (!light.begin()) {
        Serial.println("Could not find a valid BH1750 sensor, check wiring!");
        while (true);
    }

    WiFi.begin(wifiSettings.ssid, wifiSettings.password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to " + WiFi.localIP());
    Server.begin();
    Serial.println("TCP Server started");
}

void loop()
{
    String data;
//    if (Client.connected())
//    {
//        data = Client.read();
//        Client.println("Recieved data: " + data);
//        Client.println("Data recieved successfully");
//    }
//    else
//    {
//       Client = Server.available();
//    }

    UNITS unit;
    Settings sets;
    sets = processJSONData(sets, data);
    unit = getSensorData(unit);
}

UNITS getSensorData(UNITS& unit)
{
    unit.temperature = bme.readTemperature();
    unit.humidity = bme.readHumidity();
    unit.pressure = bme.readPressure() / 100.0F;
    unit.light = light.readLightLevel();
    return unit;
}

Settings processJSONData(Settings& sets, String& jsonData)
{
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, jsonData);
    if (error)
    {
        Serial.println("JSON parsing failed!");
        return sets;
    }
    sets.timeBetweenRequests = doc["timeBetweenRequests"];
    sets.dataNeeded = doc["dataNeeded"];
    return sets;
}
