//
// Created by motawe on 5/18/26.
//

#include "Encoder.h"

Encoder::Encoder(TIM_HandleTypeDef *htim, float radius, bool inverted): _htim(htim), _radius(radius), _inverted(inverted) {}

void Encoder::begin() {
    HAL_TIM_Encoder_Start(_htim, TIM_CHANNEL_ALL);
}

long Encoder::get_ticks(){
    return __HAL_TIM_GET_COUNTER(_htim);
}

float Encoder::get_raw_velocity() {
    long current_ticks = get_ticks();
    long now = HAL_GetTick();

    float dt_seconds = (now - last_read_time) / 1000.0f;

    if (dt_seconds <= 0.0001f) return last_velocity;

    int16_t delta_ticks = (int16_t)(current_ticks - last_ticks_read);

    // Save states for the next cycle
    last_ticks_read = current_ticks;
    last_read_time = now;

    float raw_vel = (((float)delta_ticks / 600.0f) * (2 * PI * _radius)/100.0f) /(dt_seconds);

    if (_inverted)
        return -(raw_vel);
    else
        return raw_vel;

}

float Encoder::get_velocity(float raw_sensor_vel) {
    float y_curr = (SENS_FILT_B0 * raw_sensor_vel) + (SENS_FILT_B1 * sens_u1) +
            (SENS_FILT_B2 * sens_u2) - (SENS_FILT_A1 * sens_y1)- (SENS_FILT_A2 * sens_y2); // Shift registers MUST happen oldest first!
    sens_u2 = sens_u1;
    sens_u1 = raw_sensor_vel;
    sens_y2 = sens_y1;
    sens_y1 = y_curr;
    last_velocity = y_curr;
    return y_curr;
}