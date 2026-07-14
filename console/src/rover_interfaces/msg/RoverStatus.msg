std_msgs/Header header

# Power
float32 battery_voltage_1
float32 battery_voltage_2

# Motor currents (A)
float32 motor_current_fl
float32 motor_current_fr
float32 motor_current_bl
float32 motor_current_br

# Servo positions (degrees)
float32 servo_1_angle
float32 servo_2_angle

# Digital outputs
bool laser_enabled
bool led_enabled
bool emergency_stop

# IMU calibration status
uint8[4] imu_calibration