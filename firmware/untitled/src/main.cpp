#include <Arduino.h>
// #include <SPI.h>
// #include <RF24.h>
void setup() {
// write your initialization code here
    Serial.begin(115200);
    pinMode(PB_0, OUTPUT);
}

void loop() {
// write your code here
    digitalWrite(PB_0, LOW);
    delay(500);
    digitalWrite(PB_0, HIGH);
}





// void nrf_test() {
//     CSN_high();
//     uint8_t status = SPI_Transfer(0xFF);  // NOP
//     CSN_LOW();
//
//     // Step 2: Only proceed if RX_DR is set
//     if (status & (1 << 6)) {
//
//         // Step 3: Read payload
//         uint8_t payload[3] = {0,0,0};
//         CSN_high();
//         SPI_Transfer(0x61);              // R_RX_PAYLOAD
//         payload[0] = SPI_Transfer(0xFF);
//         payload[1] = SPI_Transfer(0xFF);
//         payload[2] = SPI_Transfer(0xFF);
//         CSN_LOW();
//
//         // Step 4: Clear RX_DR AFTER reading
//         NRF_WriteReg(0x07, 0x40);
//
//         // Step 5: Check FIFO_STATUS — if more packets, flush them
//         // to avoid reading stale data
//         CSN_high();
//         SPI_Transfer(0x17);              // read FIFO_STATUS
//         uint8_t fifo = SPI_Transfer(0xFF);
//         CSN_LOW();
//
//         if (!(fifo & 0x01)) {
//             // More data in FIFO — flush it to avoid stale reads
//             CSN_high();
//             SPI_Transfer(0xE2);          // FLUSH_RX
//             CSN_LOW();
//         }
//
//         int8_t left  = (int8_t)payload[0];
//         int8_t right = (int8_t)payload[1];
//         uint8_t estop = payload[2];
//
//         // In nrf_test(), after parsing:
//         if (left < -100 || left > 100 || right < -100 || right > 100) return; // discard
//
//         char msg[64];
//         sprintf(msg, "left=%d right=%d estop=%u\r\n",left,right,estop);
//         CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
//     }
//
//     HAL_Delay(5);
// }

// void nrf_test() {
//     // Step 1: Read STATUS using a clean NOP transaction
//     uint8_t status = NRF_ReadStatus();
//
//     // Step 2: Only proceed if Data Ready (RX_DR) flag is high
//     if (status & (1 << 6)) {
//
//         // Step 3: Read exactly 3 bytes from the RX payload buffer
//         uint8_t payload[3] = {0, 0, 0};
//         CSN_high();
//         SPI_Transfer(0x61); // R_RX_PAYLOAD command
//         payload[0] = SPI_Transfer(0xFF);
//         payload[1] = SPI_Transfer(0xFF);
//         payload[2] = SPI_Transfer(0xFF);
//         CSN_LOW();
//
//         // Step 4: Clear the RX_DR flag by writing 1 to bit 6 of STATUS register
//         NRF_WriteReg(0x07, 0x40);
//
//         // Parse signed integers explicitly
//         int8_t left   = (int8_t)payload[0];
//         int8_t right  = (int8_t)payload[1];
//         uint8_t estop = payload[2];
//
//         // Sanity filter checking bounds matching your application rules
//         // if (left >= -100 && left <= 100 && right >= -100 && right <= 100) {
//             char msg[64];
//             sprintf(msg, "left=%d right=%d estop=%u\r\n", left, right, estop);
//             CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
//         }
//
//         // Step 5: Read FIFO_STATUS safely using the R_REGISTER mask (0x00)
//         uint8_t fifo_status = NRF_ReadReg(0x17);
//
//         // Check if RX_EMPTY bit (bit 0) is still 0 (meaning more packets are waiting)
//         if (!(fifo_status & 0x01)) {
//             // Flush remaining packets only if the queue is backed up with old frames
//             CSN_high();
//             SPI_Transfer(0xE2); // FLUSH_RX
//             CSN_LOW();
//         }
//
//     HAL_Delay(5);
// }

// void nrf_test() {
//     // ---- SPI PERIPHERAL FAILSAFE RESCUE ----
//     // If HAL SPI gets locked up by an Overrun (OVR) flag from noise,
//     // this clears the error and restores operation immediately.
//     if (__HAL_SPI_GET_FLAG(&hspi2, SPI_FLAG_OVR) != RESET) {
//         __HAL_SPI_CLEAR_OVRFLAG(&hspi2);
//
//         // Force fully resetting and re-initializing the SPI peripheral hardware state
//         HAL_SPI_DeInit(&hspi2);
//         HAL_SPI_Init(&hspi2);
//
//         // Toggle CSN to clear the radio's state machine
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//         HAL_Delay(1);
//         return;
//     }
//
//     // 1. Read the STATUS register directly using a standard NOP
//     HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);
//     uint8_t dummy = 0xFF;
//     uint8_t status = 0;
//     HAL_StatusTypeDef spi_result = HAL_SPI_TransmitReceive(&hspi2, &dummy, &status, 1, 10);
//     HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//
//     // If the SPI bus failed to respond, exit early to avoid blocking
//     if (spi_result != HAL_OK) {
//         return;
//     }
//
//     // 2. Check if the RX Data Ready (RX_DR) flag is active (Bit 6)
//     if (status & (1 << 6)) {
//         uint8_t payload[3] = {0, 0, 0};
//
//         // 3. Read the 3-byte payload cleanly
//         CSN_high();
//         SPI_Transfer(0x61); // R_RX_PAYLOAD command
//         payload[0] = SPI_Transfer(0xFF);
//         payload[1] = SPI_Transfer(0xFF);
//         payload[2] = SPI_Transfer(0xFF);
//         CSN_LOW();
//
//         // 4. Forcefully clear the RX_DR interrupt flag in the STATUS register.
//         // We write 0x40 to bit 6 of register 0x07.
//         CSN_high();
//         SPI_Transfer(0x20 | 0x07); // W_REGISTER command to STATUS register
//         SPI_Transfer(0x40);        // Write 1 to bit 6 to clear it
//         CSN_LOW();
//
//         // 5. Read FIFO_STATUS (Register 0x17) to make sure nothing is backed up
//         CSN_high();
//         SPI_Transfer(0x17); // Read FIFO_STATUS register address
//         uint8_t fifo_status = SPI_Transfer(0xFF);
//         CSN_LOW();
//
//         // If the RX FIFO is full (Bit 1) or completely jammed, flush it to prevent freezing
//         if (fifo_status & (1 << 1)) {
//             CSN_high();
//             SPI_Transfer(0xE2); // FLUSH_RX command
//             CSN_LOW();
//         }
//
//         // 6. Map raw unsigned bytes explicitly into signed 8-bit integers
//         int8_t left   = (int8_t)payload[0];
//         int8_t right  = (int8_t)payload[1];
//         uint8_t estop = payload[2];
//
//         // Filter out obvious out-of-sync frames
//         if (left >= -100 && left <= 100 && right >= -100 && right <= 100) {
//             char msg[64];
//             sprintf(msg, "SUCCESS -> left=%d right=%d estop=%u\r\n", left, right, estop);
//             CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
//         } else {
//             // Unaligned packet caught! Flush to recover alignment immediately
//             char err_msg[64];
//             sprintf(err_msg, "CORRUPT FRAME: [%d, %d, %u] -> Recovering...\r\n", left, right, estop);
//             CDC_Transmit_FS((uint8_t*)err_msg, strlen(err_msg));
//
//             CSN_high();
//             SPI_Transfer(0xE2); // FLUSH_RX
//             CSN_LOW();
//         }
//     }
//
//     HAL_Delay(5);
// }

// void nrf_test() {
//     // ---- SPI PERIPHERAL FAILSAFE RESCUE ----
//     if (__HAL_SPI_GET_FLAG(&hspi2, SPI_FLAG_OVR) != RESET) {
//         __HAL_SPI_CLEAR_OVRFLAG(&hspi2);
//         HAL_SPI_DeInit(&hspi2);
//         HAL_SPI_Init(&hspi2);
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//         HAL_Delay(1);
//         return;
//     }
//
//     // 1. Read the STATUS register cleanly via NOP
//     HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);
//     uint8_t dummy = 0xFF;
//     uint8_t status = 0;
//     HAL_StatusTypeDef spi_result = HAL_SPI_TransmitReceive(&hspi2, &dummy, &status, 1, 10);
//     HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//
//     if (spi_result != HAL_OK) {
//         return;
//     }
//
//     // 2. Process only if the RX Data Ready (RX_DR) flag is asserted (Bit 6)
//     if (status & (1 << 6)) {
//         // We use a 4-byte unified buffer to transmit the command and clock out data in ONE single burst
//         uint8_t spi_tx[4] = {0x61, 0xFF, 0xFF, 0xFF}; // 0x61 = R_RX_PAYLOAD
//         uint8_t spi_rx[4] = {0, 0, 0, 0};
//
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);
//         HAL_StatusTypeDef rx_status = HAL_SPI_TransmitReceive(&hspi2, spi_tx, spi_rx, 4, 10);
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//
//         // Clear the RX_DR interrupt flag immediately using an isolated transaction
//         uint8_t write_reg_cmd[2] = {(uint8_t)(0x20 | 0x07), 0x40}; // W_REGISTER to STATUS, clear bit 6
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);
//         HAL_SPI_Transmit(&hspi2, write_reg_cmd, 2, 10);
//         HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//
//         if (rx_status != HAL_OK) return;
//
//         // Note: spi_rx[0] received data while we sent the 0x61 command byte (it contains old STATUS).
//         // The actual payload bytes are shifted into indices 1, 2, and 3.
//         int8_t left   = (int8_t)spi_rx[1];
//         int8_t right  = (int8_t)spi_rx[2];
//         uint8_t estop = spi_rx[3];
//
//         // 3. Filter and process the real over-the-air payload parameters
//         // Target expected: left = 75, right = -40, estop = 0
//         if (left == 75 && right == -40) {
//             char msg[64];
//             sprintf(msg, "SUCCESS -> left=%d right=%d estop=%u\r\n", left, right, estop);
//             CDC_Transmit_FS((uint8_t*)msg, strlen(msg));
//         } else {
//             // If the values are drifting or zero, print the raw shift indices to observe them
//             char err_msg[80];
//             sprintf(err_msg, "UNALIGNED DATA SHIFTED: [%d, %d, %u] -> Flushing FIFO...\r\n", left, right, estop);
//             CDC_Transmit_FS((uint8_t*)err_msg, strlen(err_msg));
//
//             // Clean up the FIFO explicitly so the next packet realigns to index 1
//             uint8_t flush_cmd = 0xE2; // FLUSH_RX
//             HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET);
//             HAL_SPI_Transmit(&hspi2, &flush_cmd, 1, 10);
//             HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET);
//         }
//     }
//
//     HAL_Delay(1);
// }