/*
 * messages.h — Protocol contract between STM32 firmware and ROS node
 *
 * RULES FOR THIS FILE:
 *   - Pure C syntax only (no C++ classes, no references, no nullptr)
 *   - Safe to include from both .c and .cpp files
 *   - Do NOT include crc8.hpp here — it is C++ only
 *   - Do NOT include usbd_cdc_if.h here
 *
 * WIRE FORMAT (every message, upstream and downstream):
 *   [0xFF][MSG_TYPE 1B][LEN 1B][PAYLOAD 0-64B][CRC8 1B]
 *   CRC8 covers: MSG_TYPE + LEN + PAYLOAD (NOT the sync byte)
 *
 * ENDIANNESS:
 *   STM32F401 (ARM Cortex-M4) = little-endian
 *   Python struct.pack must use '<' prefix:
 *     struct.pack('<2f', left, right)  for CmdVelPayload
 *     struct.pack('<10f', ...)         for IMUPayload
 *
 * __attribute__((packed)):
 *   Prevents GCC padding between struct members.
 *   Without it: uint8_t + float = 8 bytes (3 hidden padding bytes).
 *   With it:    uint8_t + float = 5 bytes (what you actually want).
 *
 * SHARED WITH ROS:
 *   stm_msgs.py on the ROS side must define identical numeric
 *   values for every MessageType entry. Do not change values here
 *   without updating stm_msgs.py at the same time.
 */

#ifndef MESSAGES_H
#define MESSAGES_H

#include <stdint.h>
#include <string.h>   /* memcpy — used in build_frame */

/* ── Protocol constants ──────────────────────────────────────────────── */
#define PROTOCOL_SYNC_BYTE   0xFF
#define MAX_PAYLOAD_SIZE     64

/* ── Message type IDs ────────────────────────────────────────────────── */
/*
 * Using #define instead of enum so this file stays valid C89/C90.
 * In .cpp files you can cast to uint8_t freely.
 *
 * Upstream   = STM32 → ROS
 * Downstream = ROS   → STM32
 */

/* Upstream */
#define MSG_IMU        0x01   /* 50 Hz  — quaternion + euler + accel        */
#define MSG_GPS        0x02   /* 10 Hz  — lat + lon + alt + covariance      */
#define MSG_ENCODERS   0x03   /* 50 Hz  — 4-wheel velocities m/s            */
#define MSG_STATUS     0x04   /* 10 Hz  — battery + current + servo + flags */
#define MSG_READY      0x05   /* flow control handshake — zero payload       */
#define MSG_ANTENNA    0x06   /* as needed — base station GPS position       */

/* Downstream */
#define MSG_CMD_VEL    0x10   /* pre-converted wheel velocities m/s         */
#define MSG_SERVO      0x11   /* servo1 + servo2 target angles (degrees)    */
#define MSG_LASER      0x12   /* laser on/off                                */
#define MSG_MODE       0x13   /* 0=manual  1=autonomous                      */
#define MSG_HEARTBEAT  0x14   /* 1 Hz watchdog feed                          */

/* Bidirectional */
#define MSG_ACK        0xA0   /* acknowledge READY or control message        */

/* ══════════════════════════════════════════════════════════════════════
 * UPSTREAM PAYLOAD STRUCTS  (STM32 → ROS)
 * ══════════════════════════════════════════════════════════════════════ */

/*
 * IMUPayload — 40 bytes
 * Source:    BNO055 fused output via I2C1
 * Rate:      50 Hz
 * ROS topic: /imu/data  (sensor_msgs/Imu)
 *
 * Send fused quaternion — NOT raw magnetometer.
 * BNO055 computes orientation internally.
 * Python unpack: struct.unpack('<10f', payload)
 */
struct __attribute__((packed)) IMUPayload {
    float q1, q2, q3, q4;           /* quaternion w,x,y,z   — 16 bytes */
    float roll, pitch, yaw;          /* euler angles radians  — 12 bytes */
    float accel_x, accel_y, accel_z; /* linear accel m/s²    — 12 bytes */
    /* total = 40 bytes */
};

/*
 * GPSPayload — 16 bytes
 * Source:    NEO-M8N via USART2 + DMA, NMEA parsing
 * Rate:      10 Hz
 * ROS topic: /gps/fix  (sensor_msgs/NavSatFix)
 *
 * Python unpack: struct.unpack('<4f', payload)
 */
struct __attribute__((packed)) GPSPayload {
    float latitude;            /* degrees  — 4 bytes */
    float longitude;           /* degrees  — 4 bytes */
    float altitude;            /* metres   — 4 bytes */
    float position_covariance; /* m²       — 4 bytes */
    /* total = 16 bytes */
};

/*
 * EncodersPayload — 16 bytes
 * Source:    Hardware timer CNT registers (TIM1/3/4/5 in encoder mode)
 * Rate:      50 Hz
 * ROS topic: /odom  (nav_msgs/Odometry) — computed in stm_node.py
 *
 * WHY 4 WHEELS:
 *   Rover is 4WD with independent encoders per wheel.
 *   Differential drive kinematics run on the ROS side.
 *   STM32 sends raw per-wheel velocities only.
 *
 * Python unpack: struct.unpack('<4f', payload)
 */
struct __attribute__((packed)) EncodersPayload {
    float front_left;  /* m/s — 4 bytes */
    float back_left;   /* m/s — 4 bytes */
    float front_right; /* m/s — 4 bytes */
    float back_right;  /* m/s — 4 bytes */
    /* total = 16 bytes */
};

/*
 * StatusPayload — 39 bytes
 * Source:    ADC DMA (ACS712 current + voltage dividers) + servo feedback
 * Rate:      10 Hz
 * ROS topic: /rover/status  (ugvc_msgs/RoverStatus)
 *
 * imu_cal[4]: BNO055 calibration (0=uncal, 3=fully cal)
 *   [0]=system  [1]=gyro  [2]=accel  [3]=mag
 *
 * Python unpack:
 *   floats = struct.unpack('<9f', payload[:36])
 *   flags  = struct.unpack('<3B', payload[36:39])
 *   (imu_cal packed separately as 4 bytes after flags in extended version)
 */
struct __attribute__((packed)) StatusPayload {
    float bat_voltage_1;     /* volts         — 4 bytes */
    float bat_voltage_2;     /* volts         — 4 bytes */
    float motor_current[4];  /* amps FL BL FR BR — 16 bytes */
    float servo1_angle;      /* degrees       — 4 bytes */
    float servo2_angle;      /* degrees       — 4 bytes */
    uint8_t led_state;       /* 0=off 1=on    — 1 byte  */
    uint8_t laser_state;     /* 0=off 1=on    — 1 byte  */
    uint8_t emergency_active;/* 0=ok 1=estop  — 1 byte  */
    uint8_t imu_cal[4];      /* BNO055 cal    — 4 bytes */
    /* total = 39 bytes */
};

/*
 * AntennaPayload — 8 bytes
 * Source:    Base station GPS forwarded via NRF
 * Rate:      As needed
 * ROS topic: /antenna/position
 *
 * Python unpack: struct.unpack('<2f', payload)
 */
struct __attribute__((packed)) AntennaPayload {
    float longitude; /* degrees — 4 bytes */
    float latitude;  /* degrees — 4 bytes */
    /* total = 8 bytes */
};

/* ══════════════════════════════════════════════════════════════════════
 * DOWNSTREAM PAYLOAD STRUCTS  (ROS → STM32)
 * ══════════════════════════════════════════════════════════════════════ */

/*
 * CmdVelPayload — 8 bytes
 * Source:    stm_node.py converts geometry_msgs/Twist (linear_x, angular_z)
 *            to per-wheel velocities using wheelbase, then sends this.
 *
 * WHY NOT linear_x + angular_z:
 *   STM32 PID runs on wheel velocity setpoints directly.
 *   Differential drive kinematics belong in ROS, not firmware.
 *
 * Python pack: struct.pack('<2f', left_wheel_vel, right_wheel_vel)
 */
struct __attribute__((packed)) CmdVelPayload {
    float left_wheel_vel;  /* m/s — 4 bytes */
    float right_wheel_vel; /* m/s — 4 bytes */
    /* total = 8 bytes */
};

/*
 * ServoPayload — 8 bytes
 * Python pack: struct.pack('<2f', angle1, angle2)
 */
struct __attribute__((packed)) ServoPayload {
    float servo1_angle; /* degrees — 4 bytes */
    float servo2_angle; /* degrees — 4 bytes */
    /* total = 8 bytes */
};

/*
 * LaserPayload — 1 byte
 * Python pack: struct.pack('<B', 1)  or  struct.pack('<B', 0)
 */
struct __attribute__((packed)) LaserPayload {
    uint8_t status; /* 0=off 1=on — 1 byte */
};

/*
 * ModePayload — 1 byte
 * Python pack: struct.pack('<B', 0)  manual
 *              struct.pack('<B', 1)  autonomous
 */
struct __attribute__((packed)) ModePayload {
    uint8_t mode; /* 0=manual 1=autonomous — 1 byte */
};

/*
 * HeartbeatPayload — 1 byte
 * Sent by stm_node.py every 50 timer ticks (= 1 Hz at 50 Hz loop).
 * STM32 watchdog resets its timer ONLY on receipt of this message.
 * sequence increments each send — gaps detect missed beats.
 *
 * Python pack: struct.pack('<B', seq)
 */
struct __attribute__((packed)) HeartbeatPayload {
    uint8_t sequence; /* wraps 0-255 — 1 byte */
};

/* ══════════════════════════════════════════════════════════════════════
 * FRAME BUILDER
 * ══════════════════════════════════════════════════════════════════════ */

/*
 * crc8 — declared here, defined in stm32_bridge.cpp
 * Dallas/Maxim polynomial 0x31.
 * Covers: msg_type + length + payload bytes (NOT sync byte).
 */
#ifdef __cplusplus
extern "C" {
#endif
uint8_t crc8(const uint8_t* data, uint8_t len);
#ifdef __cplusplus
}
#endif

/*
 * build_frame — serialise any payload struct into a wire-ready buffer
 *
 * WHY NOT a fixed MessageFrame struct:
 *   A struct with payload[64] always sends 68 bytes regardless of
 *   actual payload size. build_frame() writes only what is needed:
 *   3 header bytes + payload_len + 1 CRC byte.
 *
 * PARAMETERS:
 *   out_buf     — caller buffer, must be >= 4 + payload_len bytes
 *   msg_type    — one of the MSG_* defines above
 *   payload     — pointer to packed payload struct, or NULL for 0-byte msgs
 *   payload_len — sizeof(your_struct), or 0 for MSG_READY / MSG_ACK
 *
 * RETURNS:
 *   Total bytes written to out_buf. Pass this to CDC_Transmit_FS.
 *
 * EXAMPLE:
 *   uint8_t frame[4 + sizeof(CmdVelPayload)];
 *   CmdVelPayload cmd = { 1.0f, -1.0f };
 *   uint8_t len = build_frame(frame, MSG_CMD_VEL, &cmd, sizeof(cmd));
 */
static inline uint8_t build_frame(uint8_t*    out_buf,
                                   uint8_t     msg_type,
                                   const void* payload,
                                   uint8_t     payload_len)
{
    out_buf[0] = PROTOCOL_SYNC_BYTE;
    out_buf[1] = msg_type;
    out_buf[2] = payload_len;

    if (payload != 0 && payload_len > 0)
        memcpy(&out_buf[3], payload, payload_len);

    out_buf[3 + payload_len] = crc8(&out_buf[1], (uint8_t)(2u + payload_len));

    return (uint8_t)(4u + payload_len);
}

#endif /* MESSAGES_H */
