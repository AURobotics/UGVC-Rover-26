//
// Created by motawe on 5/18/26.
//

#ifndef UGVC_ROVER_26_ENCODER_H
#define UGVC_ROVER_26_ENCODER_H
#define PI 3.14159265359

#include "stm32f4xx_hal.h"


class Encoder {

    TIM_HandleTypeDef *_htim;
    float _radius;

    public:
    Encoder(TIM_HandleTypeDef *htim, float radius);
    long get_ticks();
    int16_t get_velocity();
    void reset();

    private:
    long last_ticks_read;
    long last_read_time;
    float _filtered_velocity = 0;
    float _alpha = 0.2;
};


#endif //UGVC_ROVER_26_ENCODER_H