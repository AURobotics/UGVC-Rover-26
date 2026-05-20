#include "servo.h"

Servo::Servo(PCA9685& pca, uint8_t channel) : pca(pca), channel(channel) {
    setAngle(0);
}

void Servo::setAngle(float angle) {
    //clamp if angle is out of range
    if(angle < 0) angle = 0.0f;
    else if (angle > 180) angle = 180.0f;

    float pulse_width = pulse_range[0] + angle * (pulse_range[1] - pulse_range[0]) / 180.0f; // mapping from angle to pulse_width
    uint16_t count = (pulse_width / pulse_range[1] * 4096.0f); // Convert pulse_width to count (0-4095)

    pca.setChannel(channel, 0, count);  // Motawe3's function
    current_angle = angle;
}

float Servo::getAngle() {
    return current_angle;
}