#pragma once
// #include "servo.h"
#include <cstdint>

class Servo {
public:
    Servo(PCA9685& pca, uint8_t channel);
    float setAngle(float angle);
    float getAngle();
private:
    PCA9685& pca;// esmo pwm_expander check pwm_expander.cpp in roder to use the functions in it
    uint8_t channel;
    float current_angle;
    const float pulse_range[2] = {1000, 2000}; // in microseconds NEED TO CHECK THESE ACCORDING TO OUR SERVO not sure which model yet
};