//
// nrf_receiver.cpp — STM32F401 bare-metal nRF24L01+ receiver
// CSN = PB1   CE = PB12   SPI2 (SCK=PB13, MISO=PB14, MOSI=PB15)
//

#include "nrf_receiver.h"
#include "Motor.h"
#include "usbd_cdc_if.h"
#include <cstdio>
#include <cstring>

extern SPI_HandleTypeDef hspi2;

RadioPacket rxData;
uint8_t remote_link_active = 0;

static float left_smoothed  = 0.0f;
static float right_smoothed = 0.0f;
static const float ALPHA = 0.12f;
static uint32_t last_packet_received_tick = 0;

/* ==========================================================================
   GPIO helpers
   CSN = PB1  (set HIGH = deselect, LOW = select)
   CE  = PB12 (HIGH = RX active, LOW = standby)
   ========================================================================== */
static void CSN_high(void)   { HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1,  GPIO_PIN_SET); }
static void CSN_LOW(void) { HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1,  GPIO_PIN_RESET);   }
static void NRF_CE_High(void)  { HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);   }
static void NRF_CE_Low(void)   { HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_RESET); }

/* ==========================================================================
   Core SPI primitives
   ========================================================================== */

// Send one byte, return one byte — the status register
static uint8_t SPI_Transfer(uint8_t data) {
    uint8_t rx = 0;
    HAL_SPI_TransmitReceive(&hspi2, &data, &rx, 1, HAL_MAX_DELAY);
    return rx;
}

// Write a single-byte register
static void NRF_WriteReg(uint8_t reg, uint8_t value) {
    CSN_LOW();
    SPI_Transfer(0x20 | reg);   // W_REGISTER command
    SPI_Transfer(value);
    CSN_high();
}

// Read a single-byte register
static uint8_t NRF_ReadReg(uint8_t reg) {
    CSN_LOW();
    SPI_Transfer(reg);                  // send register address (READ, bit7=0)
    uint8_t val = SPI_Transfer(0xFF);   // clock out the value
    CSN_high();
    return val;
}

// Read the STATUS register — returned on MISO while sending any command
 uint8_t NRF_ReadStatus(void) {
    CSN_LOW();
    uint8_t status = SPI_Transfer(0xFF);  // NOP command returns STATUS
    CSN_high();
    return status;
}

// Write a 5-byte address register
static void NRF_WriteAddr(uint8_t reg, const uint8_t* addr) {
    CSN_LOW();
    SPI_Transfer(0x20 | reg);
    for (int i = 0; i < 5; i++) SPI_Transfer(addr[i]);
    CSN_high();
}

/* ==========================================================================
   INIT
   ========================================================================== */
void NRF24_Init_Receiver(void) {
    // Safe idle state before touching registers
    NRF_CE_Low();
    CSN_high();
    HAL_Delay(100);

    // Extra CSN pulses to reset nRF SPI state machine
    for (int i = 0; i < 8; i++) {
        CSN_LOW();
        HAL_Delay(1);
        CSN_high();
        HAL_Delay(1);
    }
    HAL_Delay(10);

    // Force power down first, then back up — hard reset state
    NRF_WriteReg(0x00, 0x00);  // PWR_UP=0
    HAL_Delay(50);
    NRF_WriteReg(0x00, 0x0F);  // PWR_UP=1, PRIM_RX=1, EN_CRC=1, CRCO=1
    HAL_Delay(50);

    // EN_AA: disable auto-ack on all pipes
    NRF_WriteReg(0x01, 0x00);

    uint8_t config  = NRF_ReadReg(0x00);
    uint8_t en_aa   = NRF_ReadReg(0x01);
    char buf[64];
    sprintf(buf, "CONFIG=0x%02X EN_AA=0x%02X\r\n", config, en_aa);
    CDC_Transmit_FS((uint8_t*)buf, strlen(buf));
    HAL_Delay(2000);

    // EN_RXADDR: enable pipe 0 only
    NRF_WriteReg(0x02, 0x01);

    // SETUP_AW: 5-byte address width
    NRF_WriteReg(0x03, 0x03);

    // SETUP_RETR: no retransmit
    NRF_WriteReg(0x04, 0x00);

    // RF_CH: channel 76
    NRF_WriteReg(0x05,0x4C);

    // RF_SETUP: 1Mbps, 0dBm & LNA gain→ 0x07
    NRF_WriteReg(0x06, 0x07);

    // RX_PW_P0: 3-byte fixed payload
    NRF_WriteReg(0x11, 0x03);

    // RX_ADDR_P0: must match TX_ADDR on the ESP32
    // ESP32 printDetails shows TX_ADDR = 0x3130303030
    // That is bytes: 0x31='1', 0x30='0', 0x30='0', 0x30='0', 0x30='0'
    // nRF24 stores/sends addresses LSByte first, so wire order = '0','0','0','0','1'
    // We write in the same order we want them stored: index 0 = first byte out
uint8_t rx_addr[5] = {0xE1, 0xF0, 0xF0, 0xE8, 0xE8};
    NRF_WriteAddr(0x0A, rx_addr);

    // Clear all interrupt flags
    NRF_WriteReg(0x07, 0x70);

    // Flush both FIFOs
    CSN_LOW(); SPI_Transfer(0xE2); CSN_high();  // 0xE2--> FLUSH_RX
    CSN_LOW(); SPI_Transfer(0xE1); CSN_high();  // 0xE1--> FLUSH_TX

    // CE HIGH → start listening
    NRF_CE_High();
    HAL_Delay(1);
    // CSN_LOW(); SPI_Transfer(0xE2); CSN_high();  // FLUSH_RX
    // NRF_WriteReg(0x07, 0x70);
    // HAL_Delay(5);
    // Read back actual register state
    uint8_t en_rx = NRF_ReadReg(0x02);
     config = NRF_ReadReg(0x00);
     buf[64];
    sprintf(buf, "CONFIG=0x%02X EN_RXADDR=0x%02X\r\n", config, en_rx);
    CDC_Transmit_FS((uint8_t*)buf, strlen(buf));
}

/* ==========================================================================
   REGISTER DUMP — call once after init to verify config
   ========================================================================== */
void NRF24_PrintRegisters(void) {
    const uint8_t regs[]  = {0x00, 0x01, 0x02, 0x03, 0x05, 0x06, 0x07, 0x11};
    const char*   names[] = {"CONFIG","EN_AA","EN_RX","SETUP_AW",
                              "RF_CH","RF_SETUP","STATUS","RX_PW_P0"};
    char buf[64];

    CDC_Transmit_FS((uint8_t*)"--- NRF24 Registers ---\r\n", 25);
    HAL_Delay(10);

    for (int i = 0; i < 8; i++) {
        uint8_t val = NRF_ReadReg(regs[i]);
        sprintf(buf, "%-12s (0x%02X): 0x%02X\r\n", names[i], regs[i], val);
        CDC_Transmit_FS((uint8_t*)buf, strlen(buf));
        HAL_Delay(15);
    }

    // Read back 5-byte RX address pipe 0
    CSN_LOW();
    SPI_Transfer(0x0A);   // READ RX_ADDR_P0
    uint8_t addr[5];
    for (int i = 0; i < 5; i++) addr[i] = SPI_Transfer(0xFF);
    CSN_high();

    sprintf(buf, "RX_ADDR_P0:  %c%c%c%c%c  (hex: %02X %02X %02X %02X %02X)\r\n",
            addr[0], addr[1], addr[2], addr[3], addr[4],
            addr[0], addr[1], addr[2], addr[3], addr[4]);
    CDC_Transmit_FS((uint8_t*)buf, strlen(buf));
    HAL_Delay(15);
    CDC_Transmit_FS((uint8_t*)"--- End ---\r\n", 13);
    HAL_Delay(10);
}

/* ==========================================================================
   RECEIVE HANDLER — call in main loop
   ========================================================================== */
uint8_t Handle_Manual_Remote_Input(Motor* fl_motor, Motor* bl_motor,
                                    Motor* fr_motor, Motor* br_motor) {
    // Read STATUS using NOP — this is the CORRECT way
    // NRF_ReadReg reads reg address then a dummy byte — byte[1] is register value
    // But STATUS comes back on byte[0] (during command phase), so use NRF_ReadStatus()
    // CSN_LOW(); SPI_Transfer(0xE1); CSN_high();
    uint8_t status = NRF_ReadStatus();
    uint8_t rx_pipe = (status >> 1) & 0x07;

    if (status & (1 << 6) ) {   // RX_DR bit — data ready
        // Read 3-byte payload
        uint8_t payload[3] = {0, 0, 0};
        CSN_LOW();
        SPI_Transfer(0x61);             // R_RX_PAYLOAD command
        payload[0] = SPI_Transfer(0xFF);
        payload[1] = SPI_Transfer(0xFF);
        payload[2] = SPI_Transfer(0xFF);
        CSN_high();

        NRF_WriteReg(0x07, 0x70);  // clear RX_DR + TX_DS + MAX_RT

        rxData.left_wheel_vel  = (int8_t)payload[0];
        rxData.right_wheel_vel = (int8_t)payload[1];
        rxData.estop_pressed   =         payload[2];

        last_packet_received_tick = HAL_GetTick();
        remote_link_active = 1;
    }

    // Watchdog: 500ms without packet = link lost
    if (HAL_GetTick() - last_packet_received_tick > 1500) {
        remote_link_active = 0;
    }

    // E-stop failsafe
    if (remote_link_active && rxData.estop_pressed == 1) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_RESET);
        if (fl_motor) fl_motor->stop();
        if (bl_motor) bl_motor->stop();
        if (fr_motor) fr_motor->stop();
        if (br_motor) br_motor->stop();
        left_smoothed  = 0.0f;
        right_smoothed = 0.0f;
        return remote_link_active;
    }

    // Manual drive
    if (HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_10) == GPIO_PIN_SET) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);
        if (remote_link_active) {
            float target_left  = (rxData.left_wheel_vel  / 100.0f) * 4096.0f;
            float target_right = (rxData.right_wheel_vel / 100.0f) * 4096.0f;
            left_smoothed  = ALPHA * target_left  + (1.0f - ALPHA) * left_smoothed;
            right_smoothed = ALPHA * target_right + (1.0f - ALPHA) * right_smoothed;
            if (fl_motor) fl_motor->move((int16_t)left_smoothed);
            if (bl_motor) bl_motor->move((int16_t)left_smoothed);
            if (fr_motor) fr_motor->move((int16_t)right_smoothed);
            if (br_motor) br_motor->move((int16_t)right_smoothed);
        }
    }

    // At the top of the function, add:
    static uint32_t last_print_tick = 0;

    // Replace the entire if/else debug block at the bottom with:
    if (HAL_GetTick() - last_print_tick > 1000) {   // print at most once per second
        last_print_tick = HAL_GetTick();
        char msg[80];
        sprintf(msg, "STATUS=0x%02X link=%d left=%d right=%d estop=%u\r\n",
                status, remote_link_active,
                rxData.left_wheel_vel, rxData.right_wheel_vel, rxData.estop_pressed);
        CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
    }

    return remote_link_active;
}