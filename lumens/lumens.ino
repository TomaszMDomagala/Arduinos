#include <Wire.h>
#include "mbedtls/md.h"

#include <BH1750.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

BH1750 lightMeter;
Adafruit_BME280 bme;

void setup(){
  Serial.begin(9600);

  Wire.begin();
  bool status_bh = lightMeter.begin();
  if (!status_bh) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
  }

  bool status_bme = bme.begin(0x76);  
  if (!status_bme) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
  }
}

void loop() {
  
  hashdata();

  Serial.println();
  printValues();
  delay(1000);
}

void printValues() {
  Serial.print("Light: ");
  Serial.print(lightMeter.readLightLevel());
  Serial.println(" lx");
  
  Serial.print("Temperature = ");
  Serial.print(bme.readTemperature());
  Serial.println(" *C");
  
  Serial.print("Pressure = ");
  Serial.print(bme.readPressure() / 100.0F);
  Serial.println(" hPa");
  
  Serial.print("Humidity = ");
  Serial.print(bme.readHumidity());
  Serial.println(" %");
  
  Serial.println();
}

void hashdata() {

  char *key = "secretKeys";
  char *payload = "Tomako";
  byte hmacResult[32];
 
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
 
  const size_t payloadLength = strlen(payload);
  const size_t keyLength = strlen(key);            
 
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char *) key, keyLength);
  mbedtls_md_hmac_update(&ctx, (const unsigned char *) payload, payloadLength);
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);
 
  Serial.print("Hash: ");
 
  for(int i= 0; i< sizeof(hmacResult); i++){
      char str[3];
 
      sprintf(str, "%02x", (int)hmacResult[i]);
      Serial.print(str);
  }
}
