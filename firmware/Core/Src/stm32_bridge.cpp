/*
 * stm32_bridge.cpp — STM32Bridge implementation
 *
 * FIXES APPLIED vs previous versions:
 *   1. tail is NOT volatile (only head is — ISR writes head, main writes tail)
 *   2. TIMEOUT_MS is static constexpr (compile-time, zero RAM cost)
 *   3. Watchdog fed ONLY on MSG_HEARTBEAT, not on any valid frame
 *   4. ExecuteSafeStop() actually drives PB2 LOW (was empty before)
 *   5. PushBytesFromISR() takes buffer + length (one call instead of loop)
 *   6. SendReadyHandshake() removed — READY sent before each TX burst instead
 *   7. usbd_cdc_if.h included here, NOT in the header
 *   8. CRC8 uses lookup table (faster than bit-by-bit on STM32)
 */

#include "stm32_bridge.hpp"

/*
 * usbd_cdc_if.h gives us CDC_Transmit_FS().
 * Included here (in the .cpp) NOT in the .hpp, so only this translation
 * unit pays the cost of pulling in the full USB stack headers.
 */
#include "usbd_cdc_if.h"

#include <string.h> /* memcpy */

/* ── Global instance ─────────────────────────────────────────────────── */
/*
 * One global bridge object. extern'd in stm32_bridge.hpp.
 * Constructed before main() by the C++ runtime startup code.
 * usbd_cdc_if.c accesses it via the C-linkage STM32Bridge_PushBytes().
 */
STM32Bridge g_bridge;

/* ══════════════════════════════════════════════════════════════════════
 * CRC8 — Dallas/Maxim polynomial 0x31 (reflected as 0x8C)
 *
 * Uses a 256-entry lookup table: one table lookup per byte instead of
 * 8 bit-level iterations. At 84 MHz the table fits in L1 cache.
 *
 * VERIFICATION: crc8("123456789", 9) must return 0xA1
 * Run this assert in your Phase 2 test before integrating anything else.
 *
 * Declared extern "C" in messages.h so C files can call it.
 * ══════════════════════════════════════════════════════════════════════ */
static const uint8_t CRC8_TABLE[256] = {
    0x00, 0x5E, 0xBC, 0xE2, 0x61, 0x3F, 0xDD, 0x83,
    0xC2, 0x9C, 0x7E, 0x20, 0xA3, 0xFD, 0x1F, 0x41,
    0x9D, 0xC3, 0x21, 0x7F, 0xFC, 0xA2, 0x40, 0x1E,
    0x5F, 0x01, 0xE3, 0xBD, 0x3E, 0x60, 0x82, 0xDC,
    0x23, 0x7D, 0x9F, 0xC1, 0x42, 0x1C, 0xFE, 0xA0,
    0xE1, 0xBF, 0x5D, 0x03, 0x80, 0xDE, 0x3C, 0x62,
    0xBE, 0xE0, 0x02, 0x5C, 0xDF, 0x81, 0x63, 0x3D,
    0x7C, 0x22, 0xC0, 0x9E, 0x1D, 0x43, 0xA1, 0xFF,
    0x46, 0x18, 0xFA, 0xA4, 0x27, 0x79, 0x9B, 0xC5,
    0x84, 0xDA, 0x38, 0x66, 0xE5, 0xBB, 0x59, 0x07,
    0xDB, 0x85, 0x67, 0x39, 0xBA, 0xE4, 0x06, 0x58,
    0x19, 0x47, 0xA5, 0xFB, 0x78, 0x26, 0xC4, 0x9A,
    0x65, 0x3B, 0xD9, 0x87, 0x04, 0x5A, 0xB8, 0xE6,
    0xA7, 0xF9, 0x1B, 0x45, 0xC6, 0x98, 0x7A, 0x24,
    0xF8, 0xA6, 0x44, 0x1A, 0x99, 0xC7, 0x25, 0x7B,
    0x3A, 0x64, 0x86, 0xD8, 0x5B, 0x05, 0xE7, 0xB9,
    0x8C, 0xD2, 0x30, 0x6E, 0xED, 0xB3, 0x51, 0x0F,
    0x4E, 0x10, 0xF2, 0xAC, 0x2F, 0x71, 0x93, 0xCD,
    0x11, 0x4F, 0xAD, 0xF3, 0x70, 0x2E, 0xCC, 0x92,
    0xD3, 0x8D, 0x6F, 0x31, 0xB2, 0xEC, 0x0E, 0x50,
    0xAF, 0xF1, 0x13, 0x4D, 0xCE, 0x90, 0x72, 0x2C,
    0x6D, 0x33, 0xD1, 0x8F, 0x0C, 0x52, 0xB0, 0xEE,
    0x32, 0x6C, 0x8E, 0xD0, 0x53, 0x0D, 0xEF, 0xB1,
    0xF0, 0xAE, 0x4C, 0x12, 0x91, 0xCF, 0x2D, 0x73,
    0xCA, 0x94, 0x76, 0x28, 0xAB, 0xF5, 0x17, 0x49,
    0x08, 0x56, 0xB4, 0xEA, 0x69, 0x37, 0xD5, 0x8B,
    0x57, 0x09, 0xEB, 0xB5, 0x36, 0x68, 0x8A, 0xD4,
    0x95, 0xCB, 0x29, 0x77, 0xF4, 0xAA, 0x48, 0x16,
    0xE9, 0xB7, 0x55, 0x0B, 0x88, 0xD6, 0x34, 0x6A,
    0x2B, 0x75, 0x97, 0xC9, 0x4A, 0x14, 0xF6, 0xA8,
    0x74, 0x2A, 0xC8, 0x96, 0x15, 0x4B, 0xA9, 0xF7,
    0xB6, 0xE8, 0x0A, 0x54, 0xD7, 0x89, 0x6B, 0x35};

extern "C" uint8_t crc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0x00;
    while (len--)
        crc = CRC8_TABLE[crc ^ *data++];
    return crc;
}

/* ══════════════════════════════════════════════════════════════════════
 * Constructor
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
      debug_mode(false)
{
    memset(rx_buffer, 0, sizeof(rx_buffer));
    memset(payload_buffer, 0, sizeof(payload_buffer));
}

/* ══════════════════════════════════════════════════════════════════════
 * Init — call once after MX_USB_DEVICE_Init()
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::Init()
{
    /*
     * Seed the watchdog with current tick so the first 500ms
     * grace period starts from boot, not from epoch 0.
     */
    last_heartbeat_tick = HAL_GetTick();

    /*
     * PB2 HIGH = NAND input 1 HIGH = OE pin follows button only.
     * Motors are ARMED at boot. Watchdog will disarm them if ROS
     * does not send a heartbeat within TIMEOUT_MS.
     */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET);
}

/* ══════════════════════════════════════════════════════════════════════
 * PushBytesFromISR — USB RX interrupt hook
 *
 * CALLED FROM: CDC_Receive_FS in usbd_cdc_if.c (interrupt context)
 *
 * RULES — never violate these:
 *   1. Copy bytes into ring buffer and update head. Nothing else.
 *   2. No parsing, no function calls, no HAL calls, no logging.
 *   3. head is volatile so the compiler never caches it in a register.
 *   4. If buffer is full, byte is silently dropped. The CRC check in
 *      read_message() will catch the resulting corrupt frame.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::PushBytesFromISR(const uint8_t *buf, uint32_t len)
{
    for (uint32_t i = 0; i < len; i++)
    {
        uint16_t next_head = (uint16_t)((head + 1u) % BUFFER_SIZE);
        if (next_head != tail) /* drop byte if buffer full */
        {
            rx_buffer[head] = buf[i];
            head = next_head;
        }
    }
}

/* ══════════════════════════════════════════════════════════════════════
 * read_message — state machine parser
 *
 * CALLED FROM: Bridge_Update() in main loop (never from ISR)
 *
 * Processes bytes from the ring buffer one at a time.
 * Advances through 5 states per frame. Persists state between calls
 * so USB transfers that split a frame across multiple chunks are
 * handled transparently.
 *
 * The inner switch (dispatch) runs ONLY after CRC passes.
 * MSG_HEARTBEAT is the ONLY place that feeds the watchdog.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::read_message()
{
    while (tail != head)
    {
        uint8_t byte = rx_buffer[tail];
        tail = (uint16_t)((tail + 1u) % BUFFER_SIZE);

        switch (current_state)
        {
        /* ── STATE 1: Wait for sync byte ─────────────────────────────
         * Discard every byte that is not 0xFF.
         * This is how the parser recovers from misalignment or noise.
         * The moment 0xFF arrives we know: next byte is MSG_TYPE.
         * ─────────────────────────────────────────────────────────── */
        case STATE_SYNC:
            if (byte == PROTOCOL_SYNC_BYTE)
                current_state = STATE_ID;
            /* else: silently discard, keep scanning */
            break;

        /* ── STATE 2: Read message type ──────────────────────────────
         * Store the type byte. Do NOT act on it yet — no CRC yet.
         * e.g. 0x10 = MSG_CMD_VEL, 0x14 = MSG_HEARTBEAT
         * ─────────────────────────────────────────────────────────── */
        case STATE_ID:
            active_msg_id = byte;
            current_state = STATE_LEN;
            break;

        /* ── STATE 3: Read payload length ────────────────────────────
         * Three outcomes:
         *   > MAX_PAYLOAD_SIZE → impossible, misaligned → resync
         *   == 0              → zero-payload msg (READY/ACK) → skip to CRC
         *   valid length      → collect that many bytes in STATE_PAYLOAD
         * ─────────────────────────────────────────────────────────── */
        case STATE_LEN:
            if (byte > MAX_PAYLOAD_SIZE)
            {
                current_state = STATE_SYNC; /* invalid → resync */
            }
            else if (byte == 0)
            {
                active_msg_len = 0;
                payload_index = 0;
                current_state = STATE_CRC; /* no payload → go to CRC */
            }
            else
            {
                active_msg_len = byte;
                payload_index = 0;
                current_state = STATE_PAYLOAD;
            }
            break;

        /* ── STATE 4: Collect payload bytes ──────────────────────────
         * Store bytes into payload_buffer one at a time.
         * payload_index persists between calls — safe if USB splits
         * the payload across multiple transfers.
         * When all bytes collected → move to STATE_CRC.
         * ─────────────────────────────────────────────────────────── */
        case STATE_PAYLOAD:
            payload_buffer[payload_index++] = byte;
            if (payload_index >= active_msg_len)
                current_state = STATE_CRC;
            break;

        /* ── STATE 5: CRC check and dispatch ─────────────────────────
         * Build check buffer [type, len, payload...].
         * Compute CRC8 and compare with received byte.
         *
         * MATCH   → dispatch inner switch, apply command / feed watchdog
         * MISMATCH → frame discarded silently, reset to STATE_SYNC
         *
         * ALWAYS reset to STATE_SYNC after this state.
         * ─────────────────────────────────────────────────────────── */
        case STATE_CRC:
        {
            uint8_t check_buf[MAX_PAYLOAD_SIZE + 2];
            check_buf[0] = active_msg_id;
            check_buf[1] = active_msg_len;
            if (active_msg_len > 0)
                memcpy(&check_buf[2], payload_buffer, active_msg_len);

            if (crc8(check_buf, (uint8_t)(active_msg_len + 2u)) == byte)
            {
                /* ── CRC PASSED ── dispatch on message type ────────── */
                switch (active_msg_id)
                {
                /* ── MSG_HEARTBEAT ────────────────────────────────────
                 * Feed the watchdog HERE AND ONLY HERE.
                 * If ROS stops sending heartbeats (crash, disconnect),
                 * last_heartbeat_tick stops updating and CheckWatchdog()
                 * fires ExecuteSafeStop() after TIMEOUT_MS.
                 * ─────────────────────────────────────────────────── */
                case MSG_HEARTBEAT:
                {
                    last_heartbeat_tick = HAL_GetTick();
                    if (estop_active)
                        ClearEStop(); /* re-arm motors after reconnect */
                    break;
                }

                /* ── MSG_CMD_VEL ───────────────────────────────────────
                 * Wheel velocity setpoints from ROS nav stack.
                 * Cast payload_buffer directly — safe because the struct
                 * is __attribute__((packed)) and buffer is uint8_t aligned.
                 * ─────────────────────────────────────────────────── */
                case MSG_CMD_VEL:
                {
                    CmdVelPayload *cmd = (CmdVelPayload *)payload_buffer;
                    (void)cmd;
                    /* TODO: motor_left.set_setpoint(cmd->left_wheel_vel);  */
                    /* TODO: motor_right.set_setpoint(cmd->right_wheel_vel);*/
                    break;
                }

                /* ── MSG_SERVO ─────────────────────────────────────── */
                case MSG_SERVO:
                {
                    ServoPayload *srv = (ServoPayload *)payload_buffer;
                    (void)srv;
                    /* TODO: servo1.write(srv->servo1_angle); */
                    /* TODO: servo2.write(srv->servo2_angle); */
                    break;
                }

                /* ── MSG_LASER ─────────────────────────────────────── */
                case MSG_LASER:
                {
                    LaserPayload *lz = (LaserPayload *)payload_buffer;
                    (void)lz;
                    /* TODO: HAL_GPIO_WritePin(LASER_PORT, LASER_PIN,
                     *           lz->status ? GPIO_PIN_SET : GPIO_PIN_RESET); */
                    break;
                }

                /* ── MSG_MODE ──────────────────────────────────────── */
                case MSG_MODE:
                {
                    ModePayload *md = (ModePayload *)payload_buffer;
                    (void)md;
                    /* TODO: operation_mode = md->mode; */
                    /* 0 = manual (LED solid ON), 1 = autonomous (LED blink) */
                    break;
                }

                /* ── MSG_READY ─────────────────────────────────────────
                 * ROS is signalling it is ready to receive data.
                 * Respond with ACK immediately (zero-payload frame).
                 * ─────────────────────────────────────────────────── */
                case MSG_READY:
                    SendPacket(MSG_ACK, NULL, 0);
                    break;

                default:
                    /* Unknown type — ignore, parser continues */
                    break;
                }
                /* ── end dispatch ───────────────────────────────────── */
            }
            /* CRC mismatch → frame silently discarded */

            /* Always reset — this frame is done either way */
            current_state = STATE_SYNC;
            break;
        }

        } /* end switch(current_state) */
    } /* end while(tail != head) */
}

/* ══════════════════════════════════════════════════════════════════════
 * CheckWatchdog — call every main loop iteration
 *
 * Compares HAL_GetTick() against last_heartbeat_tick.
 * Unsigned subtraction is safe even when GetTick() wraps (~49 days).
 * If age > TIMEOUT_MS and e-stop is not already active → trigger.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::CheckWatchdog()
{
    if (estop_active)
        return; /* already triggered — nothing new to do */

    uint32_t age = HAL_GetTick() - last_heartbeat_tick;
    if (age > TIMEOUT_MS)
        ExecuteSafeStop();
}

/* ══════════════════════════════════════════════════════════════════════
 * ExecuteSafeStop — hardware e-stop
 *
 * PB2 LOW → NAND gate: NAND(LOW, x) = HIGH
 *         → PCA9685 OE pin HIGH (active-low) → all PWM outputs disabled
 *         → Motor drivers receive no PWM → all motors coast to stop
 *
 * This is a GPIO write — it happens in microseconds regardless of
 * I2C bus state or any other software. Pure hardware kill.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ExecuteSafeStop()
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_RESET); /* PB2 LOW */
    estop_active = true;
}

/* ══════════════════════════════════════════════════════════════════════
 * ClearEStop — re-arm motors after reconnect
 *
 * Called from the MSG_HEARTBEAT handler when a fresh heartbeat arrives
 * after an e-stop. PB2 HIGH re-enables PCA9685 OE.
 * Reseeds the watchdog timer immediately.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ClearEStop()
{
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_2, GPIO_PIN_SET); /* PB2 HIGH */
    estop_active = false;
    last_heartbeat_tick = HAL_GetTick(); /* restart grace period */
}

/* ══════════════════════════════════════════════════════════════════════
 * SendPacket — build frame and transmit via USB CDC
 *
 * If debug_mode is active, transmission is blocked — printf is using
 * the USB line and binary frames would corrupt the output.
 *
 * CDC_Transmit_FS returns USBD_BUSY if the previous DMA transfer is
 * still running. We retry once with a 1ms delay. If still busy, the
 * frame is dropped. The non-blocking timer design in Bridge_Update()
 * means the next tick will re-attempt transmission.
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::SendPacket(uint8_t msg_type, const void *payload, uint8_t length)
{
    if (debug_mode)
        return;

    uint8_t tx_frame[MAX_PAYLOAD_SIZE + 4];
    uint8_t frame_len = build_frame(tx_frame, msg_type, payload, length);

    /* Attempt 1 */
    if (CDC_Transmit_FS(tx_frame, frame_len) == USBD_OK)
        return;

    /* Attempt 2 — wait 1ms and retry once */
    HAL_Delay(1);
    CDC_Transmit_FS(tx_frame, frame_len);
    /* If still busy: frame dropped. Next scheduled TX will re-send. */
}

/* ══════════════════════════════════════════════════════════════════════
 * ToggleDebugMode
 * ══════════════════════════════════════════════════════════════════════ */
void STM32Bridge::ToggleDebugMode(bool enable)
{
    debug_mode = enable;
}

/* ══════════════════════════════════════════════════════════════════════
 * C-linkage functions — callable from main.c and usbd_cdc_if.c
 * ══════════════════════════════════════════════════════════════════════ */
extern "C"
{
    /*
     * STM32Bridge_PushBytes — called from CDC_Receive_FS in usbd_cdc_if.c
     * This is the C name for PushBytesFromISR().
     * Declared extern in usbd_cdc_if.c:
     *   extern void STM32Bridge_PushBytes(const uint8_t* buf, uint32_t len);
     */
    void STM32Bridge_PushBytes(const uint8_t *buf, uint32_t len)
    {
        g_bridge.PushBytesFromISR(buf, len);
    }

    /*
     * Bridge_Init — called from main.c USER CODE BEGIN 2
     * Seeds watchdog, arms motors (PB2 HIGH).
     */
    void Bridge_Init(void)
    {
        g_bridge.Init();
    }

    /*
     * Bridge_Update — called from main.c while(1) USER CODE BEGIN 3
     *
     * Order matters:
     *   1. read_message()  — parse any pending bytes first
     *   2. CheckWatchdog() — check AFTER parsing so a heartbeat in
     *                        this same tick can prevent a false e-stop
     *   3. Timed TX        — send upstream data at correct rates
     */
    void Bridge_Update(void)
    {
        g_bridge.read_message();
        g_bridge.CheckWatchdog();

        static uint32_t last_50hz = 0;
        static uint32_t last_10hz = 0;
        uint32_t now = HAL_GetTick();

        /* ── 50 Hz: IMU + Encoders ──────────────────────────────── */
        if (now - last_50hz >= 20u)
        {
            last_50hz = now;

            /* Send READY before the burst — ROS will ACK */
            g_bridge.SendPacket(MSG_READY, NULL, 0);

            IMUPayload imu;
            memset(&imu, 0, sizeof(imu));
            /* TODO: populate imu fields from BNO055 driver */
            g_bridge.SendPacket(MSG_IMU, &imu, (uint8_t)sizeof(imu));

            EncodersPayload enc;
            memset(&enc, 0, sizeof(enc));
            /* TODO: populate enc fields from timer CNT registers */
            g_bridge.SendPacket(MSG_ENCODERS, &enc, (uint8_t)sizeof(enc));
        }

        /* ── 10 Hz: GPS + Status ────────────────────────────────── */
        if (now - last_10hz >= 100u)
        {
            last_10hz = now;

            GPSPayload gps;
            memset(&gps, 0, sizeof(gps));
            /* TODO: populate gps fields from NMEA parser */
            g_bridge.SendPacket(MSG_GPS, &gps, (uint8_t)sizeof(gps));

            StatusPayload status;
            memset(&status, 0, sizeof(status));
            /* TODO: populate status from ADC DMA buffers */
            status.emergency_active = g_bridge.IsEStopActive() ? 1u : 0u;
            g_bridge.SendPacket(MSG_STATUS, &status, (uint8_t)sizeof(status));
        }
    }

    /*
     * _write — printf redirect to USB CDC
     *
     * Overrides the weak _write() in CubeMX-generated syscalls.c.
     * When debug_mode is true, printf output goes to USB CDC.
     * When debug_mode is false (ROS mode), output is silently dropped.
     *
     * HOW TO USE:
     *   g_bridge.ToggleDebugMode(true);
     *   printf("IMU q1=%.3f\r\n", imu.q1);   // appears in serial monitor
     *
     * WARNING: never enable debug_mode while ROS is connected.
     * Binary frames and printf strings share the same USB pipe.
     */
    int _write(int file, char *ptr, int len)
    {
        (void)file;
        if (g_bridge.IsDebugMode())
            CDC_Transmit_FS((uint8_t *)ptr, (uint16_t)len);
        return len;
    }

} /* end extern "C" */
