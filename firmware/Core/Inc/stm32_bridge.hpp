/*
 * stm32_bridge.hpp — STM32Bridge class declaration
 *
 * ... (existing comments) ...
 */

#ifndef STM32_BRIDGE_HPP
#define STM32_BRIDGE_HPP

#include "main.h"
#include "messages.h"
#include <stdint.h>

class STM32Bridge
{
public:
    STM32Bridge();

    void Init();
    void PushBytesFromISR(const uint8_t *buf, uint32_t len);
    void read_message();
    void CheckWatchdog();
    void SendPacket(uint8_t msg_type, const void *payload, uint8_t length);
    void ExecuteSafeStop();
    void ClearEStop();
    void ToggleDebugMode(bool enable);
    bool IsDebugMode() const { return debug_mode; }
    bool IsEStopActive() const { return estop_active; }

    // Handshake helpers (added)
    bool HasAck() const { return ack_received; }
    void ResetAck() { ack_received = false; }

private:
    static const uint16_t BUFFER_SIZE = 512;
    uint8_t rx_buffer[BUFFER_SIZE];
    volatile uint16_t head;
    uint16_t tail;

    enum ParseState
    {
        STATE_SYNC,
        STATE_ID,
        STATE_LEN,
        STATE_PAYLOAD,
        STATE_CRC
    };
    ParseState current_state;
    uint8_t active_msg_id;
    uint8_t active_msg_len;
    uint8_t payload_buffer[MAX_PAYLOAD_SIZE];
    uint8_t payload_index;

    static constexpr uint32_t TIMEOUT_MS = 500;
    uint32_t last_heartbeat_tick;
    bool estop_active;
    bool debug_mode;

    /* NEW: handshake flag for per‑burst ACK */
    bool ack_received;
};

extern STM32Bridge g_bridge;

#ifdef __cplusplus
extern "C"
{
#endif

    void Bridge_Init(void);
    void Bridge_Update(void);
    void STM32Bridge_PushBytes(const uint8_t *buf, uint32_t len);

#ifdef __cplusplus
}
#endif

#endif /* STM32_BRIDGE_HPP */