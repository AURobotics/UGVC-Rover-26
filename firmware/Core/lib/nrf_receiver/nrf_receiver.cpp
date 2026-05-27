//
// Created by Dania on 5/21/2026.
//

#include "nrf_receiver.h"

// Reference the SPI handle
extern SPI_HandleTypeDef hspi2;

RadioPacket rxData;
uint8_t remote_link_active = 0;

// for exp smoother output
static float left_smoothed = 0.0f;
static float right_smoothed = 0.0f;

// Ramping tuning factor. Lower values = smoother software cushions to protect gears
static const float ALPHA = 0.12f;
static uint32_t last_packet_received_tick = 0;


// Drop CSN Pin PA15 to Low (0V) to alert the NRF chip that an SPI command is arriving
static void NRF_Select(void) {
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_RESET);
}

// Drive CSN Pin PA15 High (3.3V) to release the NRF chip back to standby monitoring
static void NRF_Unselect(void) {
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_SET);
}

// Pulse the CE Pin PB12 to switch the NRF antenna circuitry between active scanning and standby
static void NRF_CE_Control(uint8_t state) {
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

// Low-level SPI transactional cycle handler. Shifts 1 byte out, clocks 1 byte back in
static uint8_t SPI2_WriteRead(uint8_t data) {
    uint8_t result = 0;
    HAL_SPI_TransmitReceive(&hspi2, &data, &result, 1, HAL_MAX_DELAY);
    return result;
}


void NRF24_Init_Receiver(void) {
    NRF_CE_Control(0); // De-energize antenna to modify structural registers safely
    NRF_Unselect();

    //  Write to CONFIG Register (0x00) with value 0x0F
    // Powers up the NRF chip, enables internal 2-byte CRC mathematical validation, and forces RX mode
    NRF_Select();
    SPI2_WriteRead(0x20 + 0x00);
    SPI2_WriteRead(0x0F);
    NRF_Unselect();

    //  Write to EN_AA Register (0x01) with value 0x00
    // Shuts off automatic over-the-air handshakes to prevent hardware retry lock-ups(mmkn neb2a nsha8lo lw e7tagna)
    NRF_Select();
    SPI2_WriteRead(0x20 + 0x01);
    SPI2_WriteRead(0x00);
    NRF_Unselect();

    //  Write to Payload Width Register (0x11) for Data Pipe 0 with value 3
    // Configures the internal buffer to expect precisely a 3-byte layout (Left, Right, E-stop)
    NRF_Select();
    SPI2_WriteRead(0x20 + 0x11);
    SPI2_WriteRead(3);
    NRF_Unselect();

    //  Write to Address Register (0x0A) and feed the unique key channel code "00001"
    // Tunes the module so it screens out surrounding 2.4 GHz signal pollution
    uint8_t rx_address[5] = {'0', '0', '0', '0', '1'};
    NRF_Select();
    SPI2_WriteRead(0x20 + 0x0A);
    for(int i = 0; i < 5; i++) {
        SPI2_WriteRead(rx_address[i]);
    }
    NRF_Unselect();

    NRF_CE_Control(1); // Energize internal RF layout to start scanning airwaves
}

uint8_t Handle_Manual_Remote_Input(Motor* fl_motor, Motor* bl_motor, Motor* fr_motor, Motor* br_motor) {
    uint8_t status = 0;

    // Query the radio's central Status Register (0x07)
    NRF_Select();
    status = SPI2_WriteRead(0x07);
    NRF_Unselect();

    // Check Bit 6 (RX_DR Data Ready Flag). It flips to 1 when a packet matches our address
    if (status & (1 << 6)) {
        NRF_Select();
        SPI2_WriteRead(0x61); // Fire the "Read RX Payload" hardware instruction command

        // Use a pointer to sweep the incoming bytes directly into our data structure fields
        uint8_t* ptr = (uint8_t*)&rxData;
        for (uint8_t i = 0; i < 3; i++) {
            ptr[i] = SPI2_WriteRead(0xFF); // Drive the hardware SPI clocks using dummy bits
        }
        NRF_Unselect();

        // Write a 1 back to Bit 6 in the Status register to clear the flag for subsequent packets
        NRF_Select();
        SPI2_WriteRead(0x20 + 0x07);
        SPI2_WriteRead(1 << 6);
        NRF_Unselect();

        // Capture a millisecond timestamp of this transaction to pass to the watchdog logic
        last_packet_received_tick = HAL_GetTick();
        remote_link_active = 1;
    }

    //  Watchdog Connection Validation
    // If more than 500ms passes without a fresh packet, assume signal occlusion or battery death
    if (HAL_GetTick() - last_packet_received_tick > 500) {
        remote_link_active = 0;
    }

    //  FAILSAFE LAYER 1 — Active Mushroom Emergency Switch Compression
    // If the remote is alive and the button is smashed, trip safety line PB2 and halt all wheels immediately
    if (remote_link_active && rxData.estop_pressed == 1) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_RESET); // Drive safety NAND logic low
        if (fl_motor) fl_motor->stop();
        if (bl_motor) bl_motor->stop();
        if (fr_motor) fr_motor->stop();
        if (br_motor) br_motor->stop();
        left_smoothed = 0.0f;
        right_smoothed = 0.0f;
        return remote_link_active; // Fixed: Now returns the connection state correctly
    }

    // Check PA10 for joystick to drive the rover
    // (1) means the human operator demands direct physical drive line priority
    if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_10) == GPIO_PIN_SET) {

        // Energize the safety override channel HIGH to authorize motor actuation
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);

        if (remote_link_active) {
            // Convert input scale (-100 to +100) straight to 12-bit expander bounds (-4096 to +4096)
            float target_left  = (rxData.left_wheel_vel  / 100.0f) * 4096.0f;
            float target_right = (rxData.right_wheel_vel / 100.0f) * 4096.0f;

            // Apply Exponential Smoother
            left_smoothed  = (ALPHA * target_left)  + ((1.0f - ALPHA) * left_smoothed);
            right_smoothed = (ALPHA * target_right) + ((1.0f - ALPHA) * right_smoothed);

            // Smoothed velocities into left-side motor pairs
            if (fl_motor) fl_motor->move((int16_t)left_smoothed);
            if (bl_motor) bl_motor->move((int16_t)left_smoothed);

            // Smoothed velocities into right-side motor pairs
            if (fr_motor) fr_motor->move((int16_t)right_smoothed);
            if (br_motor) br_motor->move((int16_t)right_smoothed);
        }
    }

    // Fixed Gold-Standard Return Pattern: Whichever path executed above,
    // we safely exit here and pass the connection flag back to main.cpp!
    return remote_link_active;
}