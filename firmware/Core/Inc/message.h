#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>

#define PROTOCOL_SYNC_BYTE 0xFF
#define MAX_PAYLOAD_SIZE 64

enum MessageType : uint8_t
{
    MSG_IMU = 0x01,
    MSG_GPS = 0x02,
    MSG_ENCODERS = 0x03,
    MSG_CMD_VEL = 0x04
};

struct __attribute__((packed)) IMUPayload
{
    float linear_accel[3];   // 12 Bytes (X, Y, Z)
    float angular_vel[3];    // 12 Bytes (X, Y, Z)
    float magnetic_field[3]; // 12 Bytes (X, Y, Z)
    float temperature;       // 4 Bytes | Total = 40 Bytes
};

struct __attribute__((packed)) GPSPayload
{
    float latitude;  // 4 Bytes
    float longitude; // 4 Bytes
    float altitude;  // 4 Bytes | Total = 12 Bytes
};

struct __attribute__((packed)) EncodersPayload
{
    float left_speed;    // 4 Bytes
    float right_speed;   // 4 Bytes
    int32_t left_ticks;  // 4 Bytes
    int32_t right_ticks; // 4 Bytes | Total = 16 Bytes
};

struct __attribute__((packed)) CmdVelPayload
{
    float linear_x;  // 4 Bytes
    float angular_z; // 4 Bytes | Total = 8 Bytes
};

struct __attribute__((packed)) MessageFrame
{
    uint8_t sync_byte;
    uint8_t msg_type;
    uint8_t length;
    uint8_t payload[MAX_PAYLOAD_SIZE];
    uint8_t crc8;
};

#endif // MESSAGES_H