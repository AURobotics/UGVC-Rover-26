#ifndef STM32_BRIDGE_HPP
#define STM32_BRIDGE_HPP

#include "main.h"
#include "messages.h"

#include <stdint.h>
class STM32Bridge
{
private:
    static const uint16_t BUFFER_SIZE = 512;

    uint8_t rx_buffer[BUFFER_SIZE];
    volatile uint16_t head;
    volatile uint16_t tail;

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

    uint32_t last_heartbeat_tick;
    const uint32_t TIMEOUT_MS = 500;
    bool debug_mode;

public:
    STM32Bridge();
    void Init();

    void PushByteFromISR(uint8_t byte);
    void read_message();
    void CheckWatchdog();
    void SendReadyHandshake();

    void SendPacket(MessageType msg_type, const void *payload, uint8_t length);
    void ToggleDebugMode(bool enable);
    bool IsDebugMode() const { return debug_mode; }
    void ExecuteSafeStop();
};

extern STM32Bridge g_bridge;

#ifdef __cplusplus
extern "C" {
#endif

void Bridge_Init(void);
void Bridge_Update(void);
void STM32Bridge_PushByte(uint8_t byte);

#ifdef __cplusplus
}
#endif //__cplusplus
#endif// STM32_BRIDGE_HPP