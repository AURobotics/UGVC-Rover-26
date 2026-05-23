/*
 * stm32_bridge.cpp — STM32Bridge implementation
 *
 * ... (existing comments, CRC8_TABLE unchanged) ...
 */

#include "stm32_bridge.hpp"
#include "usbd_cdc_if.h"
#include <string.h>

/* ── Global instance ─────────────────────────────────────────────────── */
STM32Bridge g_bridge;

/* ── CRC8 table and crc8() unchanged ─────────────────────────────────── */
static const uint8_t CRC8_TABLE[256] = {
    // ... (existing table) ...
};

extern "C" uint8_t crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0x00;
    while (len--)
        crc = CRC8_TABLE[crc ^ *data++];
    return crc;
}

/* ══════════════════════════════════════════════════════════════════════
 * Constructor — initialise all members, including ack_received
 * ══════════════════════════════════════════════════════════════════════ */
STM32Bridge::STM32Bridge()
    : head(0),
      tail(0),
      current_state(STATE_SYNC),
      active_msg_id(0),
      active_msg_len(0),
      payload_index(0),
      last_heartbeat_tick(0),
      estop_active(false),
      debug_mode(false),
      ack_received(false) // <-- ADDED
{
    memset(rx_buffer, 0, sizeof(rx_buffer));
    memset(payload_buffer, 0, sizeof(payload_buffer));
}

/* ══════════════════════════════════════════════════════════════════════
 * Init — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::Init()
{
    last_heartbeat_tick = HAL_GetTick();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);
}

/* ══════════════════════════════════════════════════════════════════════
 * PushBytesFromISR — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::PushBytesFromISR(const uint8_t *buf, uint32_t len)
{
    for (uint32_t i = 0; i < len; i++)
    {
        uint16_t next_head = (uint16_t)((head + 1u) % BUFFER_SIZE);
        if (next_head != tail)
        {
            rx_buffer[head] = buf[i];
            head = next_head;
        }
    }
}

/* ══════════════════════════════════════════════════════════════════════
 * read_message — only change: add case MSG_ACK in dispatch
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::read_message()
{
    while (tail != head)
    {
        uint8_t byte = rx_buffer[tail];
        tail = (uint16_t)((tail + 1u) % BUFFER_SIZE);

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
            if (byte > MAX_PAYLOAD_SIZE)
            {
                current_state = STATE_SYNC;
            }
            else if (byte == 0)
            {
                active_msg_len = 0;
                payload_index = 0;
                current_state = STATE_CRC;
            }
            else
            {
                active_msg_len = byte;
                payload_index = 0;
                current_state = STATE_PAYLOAD;
            }
            break;

        case STATE_PAYLOAD:
            payload_buffer[payload_index++] = byte;
            if (payload_index >= active_msg_len)
                current_state = STATE_CRC;
            break;

        case STATE_CRC:
        {
            uint8_t check_buf[MAX_PAYLOAD_SIZE + 2];
            check_buf[0] = active_msg_id;
            check_buf[1] = active_msg_len;
            if (active_msg_len > 0)
                memcpy(&check_buf[2], payload_buffer, active_msg_len);

            if (crc8(check_buf, (uint8_t)(active_msg_len + 2u)) == byte)
            {
                switch (active_msg_id)
                {
                case MSG_HEARTBEAT:
                    last_heartbeat_tick = HAL_GetTick();
                    if (estop_active)
                        ClearEStop();
                    break;

                case MSG_CMD_VEL:
                {
                    CmdVelPayload *cmd = (CmdVelPayload *)payload_buffer;
                    (void)cmd;
                    /* TODO: apply wheel velocities */
                    break;
                }

                case MSG_SERVO:
                {
                    ServoPayload *srv = (ServoPayload *)payload_buffer;
                    (void)srv;
                    /* TODO: set servos */
                    break;
                }

                case MSG_LASER:
                {
                    LaserPayload *lz = (LaserPayload *)payload_buffer;
                    (void)lz;
                    /* TODO: set laser */
                    break;
                }

                case MSG_MODE:
                {
                    ModePayload *md = (ModePayload *)payload_buffer;
                    (void)md;
                    /* TODO: change operation mode */
                    break;
                }

                case MSG_READY:
                    SendPacket(MSG_ACK, NULL, 0);
                    break;

                /* ── NEW: MSG_ACK handler ────────────────────────── */
                case MSG_ACK:
                    ack_received = true;
                    break;

                default:
                    break;
                }
            }
            current_state = STATE_SYNC;
            break;
        }
        }
    }
}

/* ══════════════════════════════════════════════════════════════════════
 * CheckWatchdog — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::CheckWatchdog()
{
    if (estop_active)
        return;
    uint32_t age = HAL_GetTick() - last_heartbeat_tick;
    if (age > TIMEOUT_MS)
        ExecuteSafeStop();
}

/* ══════════════════════════════════════════════════════════════════════
 * ExecuteSafeStop — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ExecuteSafeStop()
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_RESET);
    estop_active = true;
}

/* ══════════════════════════════════════════════════════════════════════
 * ClearEStop — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ClearEStop()
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);
    estop_active = false;
    last_heartbeat_tick = HAL_GetTick();
}

/* ══════════════════════════════════════════════════════════════════════
 * SendPacket — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::SendPacket(uint8_t msg_type, const void *payload, uint8_t length)
{
    if (debug_mode)
        return;

    uint8_t tx_frame[MAX_PAYLOAD_SIZE + 4];
    uint8_t frame_len = build_frame(tx_frame, msg_type, payload, length);

    if (CDC_Transmit_FS(tx_frame, frame_len) == USBD_OK)
        return;

    HAL_Delay(1);
    CDC_Transmit_FS(tx_frame, frame_len);
}

/* ══════════════════════════════════════════════════════════════════════
 * ToggleDebugMode — unchanged
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ToggleDebugMode(bool enable)
{
    debug_mode = enable;
}

/* ══════════════════════════════════════════════════════════════════════
 * C‑linkage functions — Bridge_Update() modified with handshake
 * ══════════════════════════════════════════════════════════════════════ */
extern "C"
{
    void STM32Bridge_PushBytes(const uint8_t *buf, uint32_t len)
    {
        g_bridge.PushBytesFromISR(buf, len);
    }

    void Bridge_Init(void)
    {
        g_bridge.Init();
    }

    void Bridge_Update(void)
    {
        g_bridge.read_message();
        g_bridge.CheckWatchdog();

        static uint32_t last_50hz = 0;
        static uint32_t last_10hz = 0;
        uint32_t now = HAL_GetTick();

        /* ── 50 Hz: IMU + Encoders with READY/ACK handshake ────────── */
        if (now - last_50hz >= 20u)
        {
            last_50hz = now;

            if (!g_bridge.HasAck())
            {
                // No ACK yet — send READY and wait until next tick
                g_bridge.SendPacket(MSG_READY, NULL, 0);
            }
            else
            {
                // ACK received — send the data burst
                g_bridge.ResetAck(); // reset for next burst

                IMUPayload imu;
                memset(&imu, 0, sizeof(imu));
                /* TODO: populate imu fields */
                g_bridge.SendPacket(MSG_IMU, &imu, (uint8_t)sizeof(imu));

                EncodersPayload enc;
                memset(&enc, 0, sizeof(enc));
                /* TODO: populate enc fields */
                g_bridge.SendPacket(MSG_ENCODERS, &enc, (uint8_t)sizeof(enc));
            }
        }

        /* ── 10 Hz: GPS + Status ──────────────────────────────────── */
        if (now - last_10hz >= 100u)
        {
            last_10hz = now;

            GPSPayload gps;
            memset(&gps, 0, sizeof(gps));
            g_bridge.SendPacket(MSG_GPS, &gps, (uint8_t)sizeof(gps));

            StatusPayload status;
            memset(&status, 0, sizeof(status));
            status.emergency_active = g_bridge.IsEStopActive() ? 1u : 0u;
            g_bridge.SendPacket(MSG_STATUS, &status, (uint8_t)sizeof(status));
        }
    }

    int _write(int file, char *ptr, int len)
    {
        (void)file;
        if (g_bridge.IsDebugMode())
            CDC_Transmit_FS((uint8_t *)ptr, (uint16_t)len);
        return len;
    }
}