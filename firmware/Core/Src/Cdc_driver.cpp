#include "Cdc_driver.h"
#include "usbd_cdc_if.h"

Cdc_driver* g_cdc_driver = nullptr;
extern "C" void on_cdc_isr(uint8_t* buf, uint32_t len) {
    if (g_cdc_driver != nullptr)
        g_cdc_driver->on_data_receive(buf, len);
}

void Cdc_driver::setup() {
    if (g_cdc_driver == nullptr)
        g_cdc_driver = this;
}

bool Cdc_driver::available() {
    // if both are equal (0,0) -> empty buffer
    return m_read_index != m_write_index;
}

bool Cdc_driver::parse(uint8_t* buf, uint32_t len, Generic_msg& out) {
    if (len < 2 || buf[0] != 0xFF)
        return false;

    auto type = static_cast<Message_Type>(buf[1]);
    last_received_msg_type = type;

    switch (type) {

    case MSG_IMU:
        if (len < sizeof(IMUPayload) + 2) // +2 accounts for length byte and CRC missing from struct layout
            return false;
        // Reconstruct the internal payload directly by bypassing the wire-length byte
        out.data.imu_msg = *reinterpret_cast<const IMUPayload*>(buf);
        // Correct internal fields shifting over wire's length byte if parsing from raw wire buffer
        out.type = MSG_IMU;
        out.size = sizeof(IMUPayload);
        break;

    case MSG_GPS:
        out.data.gps_msg = *reinterpret_cast<const GPSPayload*>(buf);
        out.type = MSG_GPS;
        out.size = sizeof(GPSPayload);
        break;

    case MSG_ENCODERS:
        out.data.encoders_msg = *reinterpret_cast<const EncodersPayload*>(buf);
        out.type = MSG_ENCODERS;
        out.size = sizeof(EncodersPayload);
        break;

    case MSG_STATUS:
        out.data.status_msg = *reinterpret_cast<const StatusPayload*>(buf);
        out.type = MSG_STATUS;
        out.size = sizeof(StatusPayload);
        break;

    case MSG_CMD_VEL:
        out.data.cmd_vel_msg = *reinterpret_cast<const CmdVelPayload*>(buf);
        out.type = MSG_CMD_VEL;
        out.size = sizeof(CmdVelPayload);
        break;

    case MSG_SERVO:
        out.data.servo_msg = *reinterpret_cast<const ServoPayload*>(buf);
        out.type = MSG_SERVO;
        out.size = sizeof(ServoPayload);
        break;

    case MSG_LASER:
        out.data.laser_msg = *reinterpret_cast<const LaserPayload*>(buf);
        out.type = MSG_LASER;
        out.size = sizeof(LaserPayload);
        break;

    case MSG_MODE:
        out.data.mode_msg = *reinterpret_cast<const ModePayload*>(buf);
        out.type = MSG_MODE;
        out.size = sizeof(ModePayload);
        break;

    default:
        return false;
    }

    return true;
}

void Cdc_driver::on_data_receive(uint8_t* buf, uint32_t len) {
    // writes in the next slot and advances the write index
    RawData& slot = m_slots[m_write_index];
    memcpy(slot.data, buf, len);
    slot.len = len;
    m_write_index = (m_write_index + 1) % BUFFER_SIZE;
}

Message_Type Cdc_driver::read_msg(Generic_msg& msg) {
    RawData& slot = m_slots[m_read_index];
    parse(slot.data, slot.len, msg);
    m_read_index = (m_read_index + 1) % BUFFER_SIZE;
    last_received_time = HAL_GetTick();
    return msg.type;
}

