#include "stm32_bridge.hpp"
#include "usbd_cdc_if.h"
#include <string.h>
#include <stdio.h>

STM32Bridge g_bridge;

// ── CRC8 Implementation ───────────────────────────────────────────────
uint8_t crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++)
    {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++)
        {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x31;
            else
                crc <<= 1;
        }
    }
    return crc;
}

// ── Constructor & Init ────────────────────────────────────────────────
STM32Bridge::STM32Bridge() : head(0), tail(0), current_state(STATE_SYNC),
                             active_msg_id(0), active_msg_len(0), payload_index(0),
                             last_heartbeat_tick(0), debug_mode(false) {}

void STM32Bridge::Init()
{
    last_heartbeat_tick = HAL_GetTick();
}

// ── ISR-Safe Ring Buffer Push ─────────────────────────────────────────
void STM32Bridge::PushByteFromISR(uint8_t byte)
{
    uint16_t next_head = (head + 1) % BUFFER_SIZE;
    if (next_head != tail) // drop byte if buffer full
    {
        rx_buffer[head] = byte;
        head = next_head;
    }
}

// ── State Machine Parser ──────────────────────────────────────────────
void STM32Bridge::read_message()
{
    while (tail != head)
    {
        uint8_t byte = rx_buffer[tail];
        tail = (tail + 1) % BUFFER_SIZE;

        switch (current_state)
        {
        case STATE_SYNC:
            if (byte == PROTOCOL_SYNC_BYTE)
                current_state = STATE_ID;
            break;

        case STATE_ID:
            active_msg_id = byte;
            current_state = STATE_LEN;
            break;

        case STATE_LEN:
            active_msg_len = byte;
            payload_index = 0;
            if (active_msg_len <= MAX_PAYLOAD_SIZE)
                current_state = STATE_PAYLOAD;
            else
                current_state = STATE_SYNC; // invalid length → reset
            break;

        case STATE_PAYLOAD:
            if (active_msg_len == 0)
            {
                current_state = STATE_CRC;
            }
            else
            {
                payload_buffer[payload_index++] = byte;
                if (payload_index >= active_msg_len)
                    current_state = STATE_CRC;
            }
            break;

        case STATE_CRC:
        {
            uint8_t check_buf[MAX_PAYLOAD_SIZE + 2];
            check_buf[0] = active_msg_id;
            check_buf[1] = active_msg_len;
            if (active_msg_len > 0)
                memcpy(&check_buf[2], payload_buffer, active_msg_len);

            if (crc8(check_buf, active_msg_len + 2) == byte)
            {
                last_heartbeat_tick = HAL_GetTick();

                switch (active_msg_id)
                {
                case MSG_CMD_VEL:
                {
                    CmdVelPayload *cmd = (CmdVelPayload *)payload_buffer;
                    // Apply cmd->left_wheel_vel and cmd->right_wheel_vel
                    break;
                }
                case MSG_SERVO:
                {
                    ServoPayload *srv = (ServoPayload *)payload_buffer;
                    // Apply srv->servo1_angle and srv->servo2_angle
                    break;
                }
                }
            }
            current_state = STATE_SYNC;
            break;
        }
        }
    }
}

// ── Transmit ──────────────────────────────────────────────────────────
void STM32Bridge::SendPacket(MessageType msg_type, const void *payload, uint8_t length)
{
    if (debug_mode)
        return;
    uint8_t tx_frame[MAX_PAYLOAD_SIZE + 4];
    uint8_t frame_len = build_frame(tx_frame, msg_type, payload, length);
    CDC_Transmit_FS(tx_frame, frame_len);
}

void STM32Bridge::SendReadyHandshake()
{
    uint16_t used = (head >= tail) ? (head - tail) : (BUFFER_SIZE - tail + head);
    uint16_t free_space = BUFFER_SIZE - used - 1;

    if (free_space > 150)
        SendPacket(MSG_READY, nullptr, 0);
}

// ── Watchdog ──────────────────────────────────────────────────────────
void STM32Bridge::CheckWatchdog()
{
    if (HAL_GetTick() - last_heartbeat_tick > TIMEOUT_MS)
        ExecuteSafeStop();
}

void STM32Bridge::ExecuteSafeStop()
{
    // Zero out PWM signals to motors immediately
}

// ── Debug ─────────────────────────────────────────────────────────────
void STM32Bridge::ToggleDebugMode(bool enable)
{
    debug_mode = enable;
}

// ── C-Linkage Hooks (single definition each) ──────────────────────────
extern "C"
{
    void STM32Bridge_PushByte(uint8_t byte)
    {
        g_bridge.PushByteFromISR(byte);
    }

    void Bridge_Init(void)
    {
        g_bridge.Init();
    }

    void Bridge_Update(void)
    {
        g_bridge.read_message();
        g_bridge.CheckWatchdog();
        g_bridge.SendReadyHandshake();

        static uint32_t last_time_50hz = 0;
        static uint32_t last_time_10hz = 0;
        uint32_t current_tick = HAL_GetTick();

        // 50 Hz → IMU + Encoders
        if (current_tick - last_time_50hz >= 20)
        {
            last_time_50hz = current_tick;

            IMUPayload imu_data = {0};
            g_bridge.SendPacket(MSG_IMU, &imu_data, sizeof(IMUPayload));

            EncodersPayload enc_data = {0};
            g_bridge.SendPacket(MSG_ENCODERS, &enc_data, sizeof(EncodersPayload));
        }

        // 10 Hz → GPS + Status
        if (current_tick - last_time_10hz >= 100)
        {
            last_time_10hz = current_tick;

            GPSPayload gps_data = {0};
            g_bridge.SendPacket(MSG_GPS, &gps_data, sizeof(GPSPayload));

            StatusPayload status_data = {0};
            status_data.bat_voltage_1 = 12.0f;
            g_bridge.SendPacket(MSG_STATUS, &status_data, sizeof(StatusPayload));
        }
    }

    // printf() redirect → USB CDC when debug mode is active
    int _write(int file, char *ptr, int len)
    {
        if (g_bridge.IsDebugMode())
            CDC_Transmit_FS((uint8_t *)ptr, len);
        return len;
    }
}