#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <RF24.h>
#define I2C_SLAVE_ADDRESS 0x08

// Nano > NRF24L01 Connections
#define NRF_CE_PIN   9
#define NRF_CSN_PIN 10

RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);

// CRITICAL: Address must match the transmitter's "00001" string exactly
const byte address[6] = "00001";

// CRITICAL: Struct must perfectly mirror the transmitter's layout and data types
struct DataPacket {
    int8_t left_wheel_vel;
    int8_t right_wheel_vel;
    uint8_t estop_pressed;
};

DataPacket rxData;

void requestEvent() {
    // Send the 3 bytes of the struct directly over I2C
    Wire.write((uint8_t*)&rxData, sizeof(DataPacket));
}

void setup() {
    Serial.begin(115200);
    Wire.begin(I2C_SLAVE_ADDRESS);
    Wire.onRequest(requestEvent);
    // digitalWrite(SDA, LOW);
    // digitalWrite(SCL, LOW);
    delay(1000);
    Serial.println(F("\n--- Nano > NRF24L01 Target Receiver ---"));

    if (!radio.begin()) {
        Serial.println(F("CRITICAL ERROR: NRF24L01 Unresponsive!"));
        while (1); // Halt if hardware connection is bad
    } else {
        Serial.println(F("NRF24L01 Hardware Detected Successfully."));
    }

    // CRITICAL: Mirror all radio configurations from transmitter
    radio.setAutoAck(false);           // Must match transmitter's false setting
    radio.setDataRate(RF24_1MBPS);     // Must match transmitter
    radio.setPALevel(RF24_PA_MAX);

    radio.openReadingPipe(1, address); // Open the identical pipe address
    radio.startListening();            // Set module as receiver

    Serial.println(F("Listening for incoming packets..."));
}

void loop() {
    // Check if a packet has arrived over the air
    if (radio.available()) {

        // Read only the exact size of our 3-byte struct
        radio.read(&rxData, sizeof(DataPacket));

        // Print the received values
        Serial.print(F("Received -> L: "));
        Serial.print(rxData.left_wheel_vel);
        Serial.print(F(" | R: "));
        Serial.print(rxData.right_wheel_vel);
        Serial.print(F(" | E-Stop: "));
        Serial.println(rxData.estop_pressed);

    }
}