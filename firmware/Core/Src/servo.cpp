#include "servo.h"

Servo::Servo(PWM_expander& pca, PWM_channel channel) : pca(pca), channel(channel) {
    setAngle(0);
}

void Servo::setAngle(float angle) {
    //clamp if angle is out of range
    if(angle < 0) angle = 0.0f;
    else if (angle > 180) angle = 180.0f;

    float pulse_width = pulse_range[0] + angle * (pulse_range[1] - pulse_range[0]) / 180.0f; // mapping from angle to pulse_width
    uint16_t count = (pulse_width / period_us * 4096.0f); // Convert pulse_width to count (0-4095)

    pca.set_channel(channel, count); 
    pca.write();
    current_angle = angle;
}

float Servo::getAngle() {
    return current_angle;
}