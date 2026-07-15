//
// Created by motawe on 5/18/26.
//

#include "PWM_expander.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

PWM_expander::PWM_expander(I2C_HandleTypeDef *hi2c, uint8_t address) : _hi2c(hi2c), _address(address)
{

    /*
        8ayart kol HAL_I2C_Mem_Write_DMA --> HAL_I2C_Mem_Write
        3ashan write dma kan somehow blocking w it returns HAL_BUSY
        w keda keda el functions deeh get called once fa mesh hayeb2a blocking AWY ya3ny
        bas keda el moshkela ba2a fy write() 3ashan this one gets called kol showaya bas idk eh el moshkela
        aslan we didnt enable dma for i2c so maybe thas why its returning HAL_BUSY
    */
}

void PWM_expander::setup(uint8_t prescaler){
   set_frequency(prescaler);
    uint8_t mode[2] = {0x20, 0x04};
    HAL_I2C_Mem_Write(_hi2c, _address, 0x00, I2C_MEMADD_SIZE_8BIT, mode, 2, 100);
    HAL_Delay(1);
  char buf[64];
    int len = snprintf(buf, sizeof(buf), "done setup...\r\n");
    CDC_Transmit_FS( (uint8_t*)buf, len);
}

void PWM_expander::set_channel(uint8_t ch, uint16_t value)
{
    // char msg[128];
    // sprintf(msg, "in set_channel() --> setting channel %d to %hu\r\n", ch, value);
    // CDC_Transmit_FS((uint8_t *)msg, strlen(msg));
    // HAL_Delay(1);
    uint8_t reg_data[2] = {((value) & 0xFF), ((value) >> 8)};

    switch (ch)
    {
    case 0:
        reg_buffer[0] = 0;
        reg_buffer[1] = 0;
        reg_buffer[2] = reg_data[0];
        reg_buffer[3] = reg_data[1];
        break;

    case 1:
        reg_buffer[4] = 0;
        reg_buffer[5] = 0;
        reg_buffer[6] = reg_data[0];
        reg_buffer[7] = reg_data[1];
        break;

    case 2:
        reg_buffer[8] = 0;
        reg_buffer[9] = 0;
        reg_buffer[10] = reg_data[0];
        reg_buffer[11] = reg_data[1];
        break;

    case 3:
        reg_buffer[12] = 0;
        reg_buffer[13] = 0;
        reg_buffer[14] = reg_data[0];
        reg_buffer[15] = reg_data[1];
        break;

    case 4:
        reg_buffer[16] = 0;
        reg_buffer[17] = 0;
        reg_buffer[18] = reg_data[0];
        reg_buffer[19] = reg_data[1];
        break;

    case 5:
        reg_buffer[20] = 0;
        reg_buffer[21] = 0;
        reg_buffer[22] = reg_data[0];
        reg_buffer[23] = reg_data[1];
        break;

    case 6:
        reg_buffer[24] = 0;
        reg_buffer[25] = 0;
        reg_buffer[26] = reg_data[0];
        reg_buffer[27] = reg_data[1];
        break;

    case 7:
        reg_buffer[28] = 0;
        reg_buffer[29] = 0;
        reg_buffer[30] = reg_data[0];
        reg_buffer[31] = reg_data[1];
        break;

    case 8:
        reg_buffer[32] = 0;
        reg_buffer[33] = 0;
        reg_buffer[34] = reg_data[0];
        reg_buffer[35] = reg_data[1];
        break;

    case 9:
        reg_buffer[36] = 0;
        reg_buffer[37] = 0;
        reg_buffer[38] = reg_data[0];
        reg_buffer[39] = reg_data[1];
        break;

    case 10:
        reg_buffer[40] = 0;
        reg_buffer[41] = 0;
        reg_buffer[42] = reg_data[0];
        reg_buffer[43] = reg_data[1];
        break;

    case 11:
        reg_buffer[44] = 0;
        reg_buffer[45] = 0;
        reg_buffer[46] = reg_data[0];
        reg_buffer[47] = reg_data[1];
        break;

    case 12:
        reg_buffer[48] = 0;
        reg_buffer[49] = 0;
        reg_buffer[50] = reg_data[0];
        reg_buffer[51] = reg_data[1];
        break;

    case 13:
        reg_buffer[52] = 0;
        reg_buffer[53] = 0;
        reg_buffer[54] = reg_data[0];
        reg_buffer[55] = reg_data[1];
        break;

    case 14:
        reg_buffer[56] = 0;
        reg_buffer[57] = 0;
        reg_buffer[58] = reg_data[0];
        reg_buffer[59] = reg_data[1];
        break;

    case 15:
        reg_buffer[60] = 0;
        reg_buffer[61] = 0;
        reg_buffer[62] = reg_data[0];
        reg_buffer[63] = reg_data[1];
        break;
    default:
        break;
    }
}

HAL_StatusTypeDef PWM_expander::write()
{
    HAL_StatusTypeDef status = HAL_I2C_Mem_Write(_hi2c, _address, 0x06, I2C_MEMADD_SIZE_8BIT, reg_buffer, 64,100);

    return status;
}

void PWM_expander::set_frequency(uint8_t prescaler)
{
    uint8_t mode = 0x10;
    HAL_StatusTypeDef status = HAL_I2C_Mem_Write(_hi2c, _address, 0x00, I2C_MEMADD_SIZE_8BIT, &mode, 1, 100);

    status = HAL_I2C_Mem_Write(_hi2c, _address, 0xFE, I2C_MEMADD_SIZE_8BIT, &prescaler, 1, 100);

    uint8_t wake = 0x00;
    HAL_I2C_Mem_Write(_hi2c, _address, 0x00, I2C_MEMADD_SIZE_8BIT, &wake, 1, 100);
    HAL_Delay(1);
}

void PWM_expander::enable_output(){
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);
}

void PWM_expander::disable_output(){
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_RESET);
}
