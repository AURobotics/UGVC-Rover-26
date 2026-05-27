#ifndef adc_utils_h
#define adc_utils_h 

#include <stdint.h>

float raw_adc_to_voltage(uint32_t adc_value);
float raw_adc_to_current(uint32_t adc_value);

#endif /* adc_utils_h */