
#ifndef INC_CDC_DRIVER_H_
#define INC_CDC_DRIVER_H_

#ifdef __cplusplus
#include "stm32f4xx_hal.h"
#include "messages.h"
#include <stdbool.h>
#else
#include <stdint.h> 
#endif

/* --- C-Compatible Section (Visible to both) --- */
#ifdef __cplusplus
extern "C"
{
#endif

    // This is the ONLY thing the C file is allowed to see
    void CDC_Rx_Callback(uint8_t *buf, uint32_t len);

#ifdef __cplusplus
}
#endif

/* --- C++ Only Section (Hidden from C) --- */
#ifdef __cplusplus

class CdcDriver
{
private:
    uint32_t m_timeout_ms;
    static constexpr uint8_t START_BYTE = 0XFF;

    uint8_t m_rx_buffer[256];
    uint16_t rx_len;
    volatile bool data_received;

public:
    CdcDriver(uint32_t timeout_ms = 1000);
    void init();
    bool sendMessage(const Message *msg);
    bool receiveMessage(Message *msg);
    bool available() const;
    void onDataReceived(uint8_t *buf, uint32_t len); // callback from usb when data arrives
    void print(const char *format, ...);
};
#endif /* __cplusplus */
#endif /* INC_CDC_DRIVER_H_ */