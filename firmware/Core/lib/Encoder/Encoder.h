//
// Created by motawe on 5/18/26.
//

#ifndef UGVC_ROVER_26_ENCODER_H
#define UGVC_ROVER_26_ENCODER_H
#define PI 3.14159265359
#define REF_FILT_B0 (0.047657f)
#define REF_FILT_B1 (0.047657f)
#define REF_FILT_A1 (-0.904687f)
#define SENS_FILT_B0 (0.030947f)
#define SENS_FILT_B1 (0.061894f)
#define SENS_FILT_B2 (0.030947f)
#define SENS_FILT_A1 (-1.444455f)
#define SENS_FILT_A2 (0.568244f)

#include "stm32f4xx_hal.h"


class Encoder {

    TIM_HandleTypeDef *_htim;
    float _radius;
    bool _inverted;

    public:
    Encoder(TIM_HandleTypeDef *htim, float radius, bool inverted = false);
    void begin();
    long get_ticks();
    float get_raw_velocity();
    float get_velocity(float raw_velocity);
    void reset();
    float last_velocity;

    private:
    long last_ticks_read;
    long last_read_time;
    float _filtered_velocity = 0;
	float sens_u1 = 0.0f, sens_u2 = 0.0f;
	float sens_y1 = 0.0f, sens_y2 = 0.0f;
    float _alpha = 0.2;
};


#endif //UGVC_ROVER_26_ENCODER_H