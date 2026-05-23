
#ifndef INC_MESSAGES_H_
#define INC_MESSAGES_H_
#include <stdint.h>
#include <stdbool.h>

typedef enum
{
    // Upstream Messages
    MSG_IMU_DATA = 0X02,
    MSG_ENCODER_DATA = 0X03,
    MSG_GPS_DATA = 0X04,
    MSG_STATUS_DATA = 0X05,
    
    // Downstream Messages
    MSG_WHEEL_VELOCITY = 0X10,
    MSG_LASER_STATUS = 0X11,
    MSG_SERVO_ANGLES = 0X12,
    MSG_OPERATION_MODE = 0X13,
} MessageType;



//up stream--------------------------------------------------

typedef struct
{
    float imu_data[9];
} IMUData;

typedef struct
{
    float encoder_speeds[4];
} EncoderData;

typedef struct
{
    float longitude;
    float latitude;
    float position_covariance[9];
} GPSData;


typedef struct
{
    float bat_voltage_1;
    float bat_voltage_2_4;
    float motors_current;
    float servo_1_pose;
    float servo_2_pose;
    uint8_t status_flags; // LED(bit 0) | Laser(bit 1) | Emergency(bit 2) | IMU_Cal(bits 3-7)  
} StatusData;


// down stream--------------------------------------------------

typedef struct
{
    float wheel_velocity[4]; // [left, right]
} WheelVelocityData;

// Laser Status (boolean)
typedef struct
{
    bool laser_status; // 0 = off, 1 = on
} LaserStatusData;

// Servo Angles (servo_1, servo_2)
typedef struct
{
    float servo_angles[2]; // [servo_1, servo_2]
} ServoAnglesData;

// Operation Mode (0 = manual, 1 = autonomous)
typedef struct
{
    bool operation_mode; // 0 = manual, 1 = autonomous
} OperationModeData;


// ==================== GENERAL MESSAGE STRUCTURE WITH UNION ====================

typedef struct
{
    MessageType type;
    uint8_t size;
    union
    {
        // Upstream

        IMUData imu_data;
        EncoderData encoder_data;
        GPSData gps_data;
        StatusData status_data;
       

        // Downstream
        WheelVelocityData wheel_velocity;
        LaserStatusData laser_status;
        ServoAnglesData servo_angles;
        OperationModeData operation_mode;
        
    } value;
} Message;

#endif /* INC_MESSAGES_H_ */