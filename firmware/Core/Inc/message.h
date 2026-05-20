#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>

// ── Protocol constants ─────────────────────────────────────────────────
#define PROTOCOL_SYNC_BYTE 0xFF
#define MAX_PAYLOAD_SIZE 64

// ── Message type enum ──────────────────────────────────────────────────
// Upstream  = STM32 → ROS
// Downstream = ROS → STM32
enum MessageType : uint8_t
{
    // Upstream
    MSG_IMU = 0x01,      // 50 Hz  — quaternion + euler + accel
    MSG_GPS = 0x02,      // 10 Hz  — lat + lon + altitude
    MSG_ENCODERS = 0x03, // 50 Hz  — 4-wheel speeds
    MSG_STATUS = 0x04,   // 10 Hz  — battery + current + servo + flags
    MSG_READY = 0x05,    // flow control — no payload
    //MSG_ANTENNA = 0x06,  // as needed — station position

    // Downstream
    MSG_CMD_VEL = 0x10,   // wheel velocities (already converted by ROS)
    MSG_SERVO = 0x11,     // servo1 + servo2 angles
    MSG_LASER = 0x12,     // on/off
    MSG_MODE = 0x13,      // 0=manual 1=autonomous
   // MSG_HEARTBEAT = 0x14, // 1 Hz — watchdog feed

    // Bidirectional
    MSG_ACK = 0xA0, // acknowledge READY or other control msgs
};

// ── Upstream payload structs ───────────────────────────────────────────

struct __attribute__((packed)) IMUPayload
{
    // Fused orientation from BNO055 (NOT raw magnetometer)
    float q1, q2, q3, q4;            // quaternion — 16 bytes
    float alpha, beta, Psi;          // euler angles (rad) — 12 bytes
    float accel_x, accel_y, accel_z; // linear accel m/s² — 12 bytes
    // Total = 40 bytes
};

struct __attribute__((packed)) GPSPayload
{
    float latitude;            // degrees
    float longitude;           // degrees
    float position_covariance; // m² — required by ROS NavSatFix
    // Total = 16 bytes
};

struct __attribute__((packed)) EncodersPayload
{
    // Four wheels — matches rover geometry: FL BL FR BR
    float front_left;  // m/s
    float back_left;   // m/s
    float front_right; // m/s
    float back_right;  // m/s
    // Total = 16 bytes
    // Note: odometry computation happens in stm_node.py, not here
};

struct __attribute__((packed)) StatusPayload
{
    float bat_voltage_1;      // volts
    float bat_voltage_2;      // volts
    float motor_current[4];   // amps: FL BL FR BR
    float servo1_angle;       // degrees
    float servo2_angle;       // degrees
    uint8_t led_state;        // 0=off 1=on
    uint8_t laser_state;      // 0=off 1=on
    uint8_t emergency_active; // 0=normal 1=estop triggered
    uint8_t imu_cal[4];       // BNO055 calibration: sys gyro accel mag (0-3)
    // Total = 44 bytes  ← fits within MAX_PAYLOAD_SIZE=64
};

/*struct __attribute__((packed)) AntennaPayload
{
    float longitude; // station GPS longitude
    float latitude;  // station GPS latitude
    // Total = 8 bytes
};*/

// ── Downstream payload structs ─────────────────────────────────────────

struct __attribute__((packed)) CmdVelPayload
{
    // Pre-converted by ROS node from cmd_vel Twist
    // STM32 receives wheel speeds directly — no kinematics needed here
    float left_wheel_vel;  // m/s
    float right_wheel_vel; // m/s
    // Total = 8 bytes
};

struct __attribute__((packed)) ServoPayload
{
    float servo1_angle; // degrees
    float servo2_angle; // degrees
    // Total = 8 bytes
};

struct __attribute__((packed)) LaserPayload
{
    uint8_t status; // 0=off 1=on
    // Total = 1 byte
};

struct __attribute__((packed)) ModePayload
{
    uint8_t mode; // 0=manual 1=autonomous
    // Total = 1 byte
};

struct __attribute__((packed)) HeartbeatPayload
{
    uint8_t sequence; // increments each send — detect missed beats
    // Total = 1 byte
};

// ── CRC8 (Dallas/Maxim, polynomial 0x31) ──────────────────────────────
// Covers bytes: msg_type + length + payload
// Declared here — implemented in crc8.cpp
uint8_t crc8(const uint8_t *data, uint8_t len);

// ── Frame builder helper ───────────────────────────────────────────────
// Do NOT use a fixed-size MessageFrame struct on the wire.
// Call this to build a frame into a caller-supplied buffer.
// Returns total frame length (3 + payload_len + 1).
inline uint8_t build_frame(uint8_t *out_buf,
                           MessageType msg_type,
                           const void *payload,
                           uint8_t payload_len)
{
    out_buf[0] = PROTOCOL_SYNC_BYTE;
    out_buf[1] = static_cast<uint8_t>(msg_type);
    out_buf[2] = payload_len;
    if (payload && payload_len > 0)
        __builtin_memcpy(&out_buf[3], payload, payload_len);
    out_buf[3 + payload_len] = crc8(&out_buf[1], 2 + payload_len);
    return 4 + payload_len;
}

#endif // MESSAGES_H