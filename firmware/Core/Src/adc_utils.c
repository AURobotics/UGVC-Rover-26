#include "adc_utils.h"

float raw_adc_to_current(uint32_t adc_value) {
    int R1 = 2000, R2 = 2200; // voltage divider resistors NEED TO CHANGE THESE VALUES ONCE WE HAVE THE ACTUAL RESISTORS
    
    // voltage on the pin after voltage divider
    float stm32_voltage = (adc_value / 4095.0f) * 3.3f;

    // actual voltage coming out of the sensor before voltage divider
    //float sensor_voltage = stm32_voltage * (R1+R2) / R2;

    // convert to current (0A = 2.5V, sensitivity = 185mV/A)
    float current = (stm32_voltage - 2.39f) / 0.185f;

    return current; 
}

float raw_adc_to_voltage(uint32_t adc_value) {
    float stm32_voltage = (adc_value / 4095.0f) * 3.3f * 1000;      
    // float battery_voltage = stm32_voltage * ((R1 + R2) / R2); //TODO: Define R1 and R2 in voltage divider
    return stm32_voltage; // return battery_voltage once voltage divider is set up
}
