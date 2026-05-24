#include "servo.h"

Servo::Servo(PWM_expander &servo0, PWM_channel channel) : servo0(servo0), channel(channel)
{
        char msg[128];
        sprintf(msg, "initialized servo on channel %d\r\n", channel);
        CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
    
}

HAL_StatusTypeDef Servo::setAngle(float angle)
{
    // clamp if angle is out of range
    if (angle < 0)
        angle = 0.0f;
    else if (angle > 180)
        angle = 180.0f;

    float pulse_width = pulse_range[0] + angle * (pulse_range[1] - pulse_range[0]) / 180.0f; // mapping from angle to pulse_width
    uint16_t count = (pulse_width * 4096.0f) / period_us;                                    // Convert pulse_width to count (0-4095)

    // char msg[128];
    // sprintf(msg, "in setAngle() --> pulse_width: %.2f, period_us: %.2f, count: %hu , angle: %.2f\r\n", pulse_width, period_us, count, angle);
    // CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
    // HAL_Delay(1);
    
    servo0.set_channel(channel, count);
    HAL_Delay(1);
    current_angle = angle;
    HAL_StatusTypeDef status = servo0.write();

    // sprintf(msg, ".write() status: %d\r\n", status);
    // CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
    return status;
}

float Servo::getAngle()
{
    return current_angle;
}