//
// Created by motawe on 5/18/26.
//

#include "Encoder.h"

Encoder::Encoder(TIM_HandleTypeDef *htim, float radius): _htim(htim), _radius(radius){
    HAL_TIM_Encoder_Start(htim, TIM_CHANNEL_ALL);
}

long Encoder::get_ticks(){
    return __HAL_TIM_GET_COUNTER(_htim);
}

int16_t Encoder::get_velocity() {
    long current_ticks = get_ticks();
    long now = HAL_GetTick();

    int16_t delta_ticks = (int16_t)(current_ticks - last_ticks_read);
    float dt = (now - last_read_time) / 1000.0f;

    last_ticks_read = current_ticks;
    last_read_time = now;

    if (dt <= 0.0f) return (int16_t)_filtered_velocity;

    float distance = (delta_ticks / 600.0f) * (_radius * 2.0f * PI);
    float raw_velocity = distance / dt;

    _filtered_velocity = _alpha * raw_velocity + (1.0f - _alpha) * _filtered_velocity;

    return (int16_t)_filtered_velocity;
}
    /*long current_ticks = get_ticks();
    long now = HAL_GetTick();

    float delta = ((current_ticks - last_ticks_read)/600.0f) * (_radius * 2.0f * PI);
    float dt = (now - last_read_time) / 1000.0f;

    last_ticks_read = current_ticks;
    last_read_time = now;


    return (int16_t)(delta/dt);
}

void Encoder::reset(){
    __HAL_TIM_SET_COUNTER(_htim, 0);
}
*/
