#pragma once
#include <sys/types.h>
#include "message.h"
#include "usbd_cdc_if.h"

#ifdef __cplusplus
extern "C" {
#endif
void on_cdc_isr(uint8_t* buf, uint32_t len);
#ifdef __cplusplus
}
#endif

#ifdef __cplusplus
typedef struct {
    Message_Type type;
    uint16_t size;
    union {
        Ready_msg ready_msg;
        IMUPayload imu_msg;
        GPSPayload gps_msg;
        EncodersPayload encoders_msg;
        StatusPayload status_msg;

        // Downstream Messages
        CmdVelPayload cmd_vel_msg;
        ServoPayload servo_msg;
        LaserPayload laser_msg;
        ModePayload mode_msg;
        HeartbeatPayload heartbeat_msg;
    } data;

} Generic_msg;

typedef struct {
    uint8_t data[sizeof(Generic_msg)];
    uint32_t len;
} RawData;

class Cdc_driver {
    static constexpr uint8_t BUFFER_SIZE = 2;

    uint32_t m_timeout_ms{};
    bool data_received = false;
    uint8_t m_rx_buffer[256]{};
    uint16_t rx_len{};
    RawData m_slots[BUFFER_SIZE]{}; // actual address that messages are written to and read from
    volatile uint8_t m_write_index{0};
    volatile uint8_t m_read_index{0};

public:
    explicit constexpr Cdc_driver(uint32_t m_timeout) : m_timeout_ms(m_timeout) {}
    void setup();
    bool available();

    template <typename T>
    bool write_msg(T& msg) {
        return CDC_Transmit_FS(reinterpret_cast<uint8_t*>(&msg), sizeof(msg));
    }

    Message_Type read_msg(Generic_msg& msg);
    void on_data_receive(uint8_t* buf, uint32_t len);
    bool parse(uint8_t* buf, uint32_t len, Generic_msg& out);


    Message_Type last_received_msg_type{};
    uint32_t last_received_time{};
};

#endif
