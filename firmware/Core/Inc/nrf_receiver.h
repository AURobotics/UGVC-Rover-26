//
// Created by Dania on 5/21/2026.
//

#ifndef NRF_RECEIVER_H
#define NRF_RECEIVER_H

#include "main.h"
#include "Motor.h"

// wireless data structure mapped to the over-the-air payload
struct __attribute__((packed)) RadioPacket {
    int8_t left_wheel_vel;   // -100 to +100 percentage throttle from Arduino remote
    int8_t right_wheel_vel;  // -100 to +100 percentage throttle from Arduino remote
    uint8_t estop_pressed;   // 1 if active emergency mushroom compression, 0 if nominal
};

extern uint8_t remote_link_active;
extern RadioPacket rxData;

void NRF24_Init_Receiver(void);
void NRF24_PrintRegisters();
uint8_t Handle_Manual_Remote_Input(Motor* fl_motor, Motor* bl_motor, Motor* fr_motor, Motor* br_motor);
void nrf_test();
uint8_t NRF_ReadStatus(void);

#endif // NRF_RECEIVER_H