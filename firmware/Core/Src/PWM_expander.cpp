//
// Created by motawe on 5/18/26.
//

#include "PWM_expander.h"


PWM_expander::PWM_expander(I2C_HandleTypeDef* hi2c, uint8_t address): _hi2c(hi2c), _address(address){
    set_frequency();
    uint8_t mode[2] = {0x20, 0x04};
    HAL_I2C_Mem_Write_DMA(_hi2c, _address, 0x00,I2C_MEMADD_SIZE_8BIT, mode, 2);
}

void PWM_expander::set_channel(PWM_channel ch, int value){
    uint8_t reg_data[2] = {((value) & 0xFF), ((value) >> 8)};

    switch (ch){
        case PWM_channel::ch_0:
            reg_buffer[0] = reg_data[0];
            reg_buffer[1] = reg_data[1];
            break;

        case PWM_channel::ch_1:
            reg_buffer[4] = reg_data[0];
            reg_buffer[5] = reg_data[1];
            break;

        case PWM_channel::ch_2:
            reg_buffer[8] = reg_data[0];
            reg_buffer[9] = reg_data[1];
            break;

        case PWM_channel::ch_3:
            reg_buffer[12] = reg_data[0];
            reg_buffer[13] = reg_data[1];
            break;

        case PWM_channel::ch_4:
            reg_buffer[16] = reg_data[0];
            reg_buffer[17] = reg_data[1];
            break;

        case PWM_channel::ch_5:
            reg_buffer[20] = reg_data[0];
            reg_buffer[21] = reg_data[1];
            break;

        case PWM_channel::ch_6:
            reg_buffer[24] = reg_data[0];
            reg_buffer[25] = reg_data[1];
            break;

        case PWM_channel::ch_7:
            reg_buffer[28] = reg_data[0];
            reg_buffer[29] = reg_data[1];
            break;

        case PWM_channel::ch_8:
            reg_buffer[32] = reg_data[0];
            reg_buffer[33] = reg_data[1];
            break;

        case PWM_channel::ch_9:
            reg_buffer[36] = reg_data[0];
            reg_buffer[37] = reg_data[1];
            break;

        case PWM_channel::ch_10:
            reg_buffer[40] = reg_data[0];
            reg_buffer[41] = reg_data[1];
            break;

        case PWM_channel::ch_11:
            reg_buffer[44] = reg_data[0];
            reg_buffer[45] = reg_data[1];
            break;

        case PWM_channel::ch_12:
            reg_buffer[48] = reg_data[0];
            reg_buffer[49] = reg_data[1];
            break;

        case PWM_channel::ch_13:
            reg_buffer[52] = reg_data[0];
            reg_buffer[53] = reg_data[1];
            break;

        case PWM_channel::ch_14:
            reg_buffer[56] = reg_data[0];
            reg_buffer[57] = reg_data[1];
            break;

        case PWM_channel::ch_15:
            reg_buffer[60] = reg_data[0];
            reg_buffer[61] = reg_data[1];
            break;
        default:
            break;
    }
}

void PWM_expander::write(){
        HAL_I2C_Mem_Write_DMA(_hi2c, _address, 0x06, I2C_MEMADD_SIZE_8BIT, reg_buffer, 30);
}

int PWM_expander::set_frequency(){
    uint8_t mode = 0x30;
    HAL_I2C_Mem_Write_DMA(_hi2c, _address, 0x00,I2C_MEMADD_SIZE_8BIT, &mode, 1);

    uint8_t prescale = 0x03;
    HAL_I2C_Mem_Write_DMA(_hi2c, _address, 0xFE,I2C_MEMADD_SIZE_8BIT, &prescale, 1);
}
/*
void PWM_expander::enable_output(){
    HAL_GPIO_WritePin(OE_GPIO_Port, OE_Pin, GPIO_PIN_RESET);
}

void PWM_expander::disable_output(){
    HAL_GPIO_WritePin(OE_GPIO_Port, OE_Pin, GPIO_PIN_SET);
}
*/