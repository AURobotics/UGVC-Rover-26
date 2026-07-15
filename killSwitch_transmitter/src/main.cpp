#include <Arduino.h>
#include <SPI.h>
#include <RF24.h>

#define JOYSTICK_X_PIN  A0
#define JOYSTICK_Y_PIN  A1
#define ESTOP_BUTTON_PIN 2

#define NRF_CE_PIN       9
#define NRF_CSN_PIN     10

RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);
const byte address[6] = "00001";

// ROBOT PHYSICAL REVISION DATA
// L is the track width of the rover. Adjust this to match your physical chassis!
const float ROVER_L = 0.65;

// New Structure: Sending direct left and right targets instead of raw X/Y
struct DataPacket {
    int8_t left_wheel_vel;   // Ranges from -100 (Full Reverse) to +100 (Full Forward)
    int8_t right_wheel_vel;  // Ranges from -100 (Full Reverse) to +100 (Full Forward)
    uint8_t estop_pressed;
};

DataPacket txData;
unsigned long lastTransmissionTime = 0;
const unsigned long heartbeatInterval = 30;

void setup() {
    Serial.begin(115200);

    // pinMode(JOYSTICK_X_PIN, INPUT);
    // pinMode(JOYSTICK_Y_PIN, INPUT);
    pinMode(ESTOP_BUTTON_PIN, INPUT_PULLUP);

    if (!radio.begin()) {
        Serial.println(F("CRITICAL ERROR: NRF24L01 Unresponsive!"));
        while (1);
    }

    radio.openWritingPipe(address);
    radio.setPALevel(RF24_PA_MAX);
    radio.setDataRate(RF24_1MBPS);
    radio.setAutoAck(false);
    radio.stopListening();

    txData.estop_pressed = 0;
}

void loop() {
    unsigned long currentTime = millis();

    if (currentTime - lastTransmissionTime >= heartbeatInterval) {
        lastTransmissionTime = currentTime;

        // Step 1: Read raw values and map to a signed velocity scale (-100 to +100)
        // int rawX = analogRead(JOYSTICK_X_PIN);
        // int rawY = analogRead(JOYSTICK_Y_PIN);

        // Linear velocity (v): negative is backward, positive is forward
        // float v = map(rawY, 0, 1023, -100, 100);
        // // Angular velocity (w): negative is left turn, positive is right turn
        // float w = map(rawX, 0, 1023, -100, 100);
        //
        // // Step 2: Apply Transmitter Deadzone Filter
        // // Forcing small resting values to absolute zero so the rover doesn't creep
        // if (abs(v) < 5) v = 0;
        // if (abs(w) < 5) w = 0;
        //
        // // Step 3: Run Kinematics Equations (Differential Drive)
        // float target_left  = v - ((w * ROVER_L) / 2.0);
        // float target_right = v + ((w * ROVER_L) / 2.0);
        //
        // // Step 4: Constrain values to guarantee they fit within our signed 8-bit limits (-100 to 100)
        // txData.left_wheel_vel  = (int8_t)constrain(target_left, -100, 100);
        // txData.right_wheel_vel = (int8_t)constrain(target_right, -100, 100);

        // Step 5: Capture E-Stop status
        if (digitalRead(ESTOP_BUTTON_PIN) == HIGH) {
            txData.estop_pressed = 1;
        } else {
            txData.estop_pressed = 0;
        }

        // Step 6: Broadcast ready-to-use velocities to the STM32
        radio.write(&txData, sizeof(DataPacket));

        // Diagnostic Output
        //Serial.print(F("Left Wheel Target: ")); Serial.print(txData.left_wheel_vel);
        //Serial.print(F(" | Right Wheel Target: ")); Serial.println(txData.right_wheel_vel);
    }
}