#pragma once
#include <cstdint>
#include "PWM_expander.h"

class Servo {
public:
    Servo(PWM_expander& pca, PWM_channel channel);
    void setAngle(float angle);
    float getAngle();
private:
    PWM_expander& pca;
    const PWM_channel   channel;
    float current_angle = 0.0f;
    static constexpr float period_us = 20000.0f; // 20ms period
    static constexpr float pulse_range[2] = {1000.0f, 2000.0f}; // in microseconds NEED TO CHECK THESE ACCORDING TO OUR SERVO not sure which model yet
};