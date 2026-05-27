#pragma once
#include <cstdint>
#include "PWM_expander.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

class Servo {
public:
    Servo(PWM_expander& servo0, PWM_channel channel);
    HAL_StatusTypeDef setAngle(float angle);
    float getAngle();
private:
    PWM_expander& servo0;
    const PWM_channel   channel;
    float current_angle = 0.0f;
    static constexpr float period_us = 20000.0f; // 20ms period
    static constexpr float pulse_range[2] = {500.0f, 2500.0f}; // in microseconds NEED TO CHECK THESE ACCORDING TO OUR SERVO not sure which model yet
};