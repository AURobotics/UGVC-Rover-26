//
// Created by motawe on 5/18/26.
//

#ifndef UGVC_ROVER_26_PWM_EXPANDER_H
#define UGVC_ROVER_26_PWM_EXPANDER_H

#include "stm32f4xx_hal.h"

enum class PWM_channel : uint8_t {
    ch_0 = 0
    , ch_1 = 1
    , ch_2 = 2
    , ch_3 = 3
    , ch_4 = 4
    , ch_5 = 5
    , ch_6 = 6
    , ch_7 = 7
    , ch_8 = 8
    , ch_9 = 9
    , ch_10 = 10
    , ch_11 = 11
    , ch_12 = 12
    , ch_13 = 13
    , ch_14 = 14
    , ch_15 = 15
};

class PWM_expander {
    public:
        I2C_HandleTypeDef* _hi2c;
        uint8_t _address;
        uint8_t reg_buffer[64] = {0};


        PWM_expander(I2C_HandleTypeDef* hi2c, uint8_t address);
        PWM_expander(const PWM_expander&) = delete;
        void set_channel(PWM_channel ch, uint16_t value);
        HAL_StatusTypeDef write();
        void set_frequency();
        void enable_output();
        void disable_output();
};

#endif //UGVC_ROVER_26_PWM_EXPANDER_H