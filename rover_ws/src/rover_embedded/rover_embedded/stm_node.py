#!/usr/bin/env python3

import struct
import time

import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, Float32MultiArray
from sensor_msgs.msg import Imu, NavSatFix, NavSatStatus
from geometry_msgs.msg import Twist
from rover_interfaces.msg import WheelVel,RoverStatus,Speed

from .stm32 import STM32
from .stm_msgs import PacketType, PAYLOAD_FMT

START_BYTE    = 0xAA
SYNC_BYTE = 0XFF # ready
WHEEL_BASE    = 0.30
PORT          = '/dev/ttyUSB0'

class STM32Node(Node):

    def __init__(self):
        super().__init__('stm32_node')

        self.stm = STM32(baudrate=115200)
        self.stm.connect(port=PORT)
        time.sleep(1)

        if not self.stm.connected:
            self.get_logger().error('STM32 not found')
            raise RuntimeError('STM32 not found')

        self.get_logger().info(f'Connected to STM32 on {self.stm.port}')

        # Publishers
        self.pub_imu       = self.create_publisher(Imu,               '/imu/data',      10)
        self.pub_gps       = self.create_publisher(NavSatFix,         '/gps/fix',       10)
        self.pub_status    = self.create_publisher(RoverStatus,         '/stm32/status',  10)
        self.pub_antenna   = self.create_publisher(NavSatFix,         '/stm32/antenna', 10)
        self.pub_wheel_vel = self.create_publisher(WheelVel,          '/wheel_vel',     10)

        # Subscribers
        self.create_subscription(Twist,             '/cmd_vel',           self._cb_cmd_vel, 10)
        self.create_subscription(Bool,              '/stm32/cmd_laser',   self._cb_laser,   10)
        self.create_subscription(Float32MultiArray, '/stm32/cmd_servo',   self._cb_servo,   10)
        self.create_subscription(Bool,              '/stm32/cmd_mode',    self._cb_mode,    10)
        self.create_subscription(Float32MultiArray, '/stm32/cmd_antenna', self._cb_antenna, 10)

        self.create_timer(0.01, self.poll_serial)  # 100 Hz
    def poll_serial(self):
        if not self.stm.connected:
            return

        while self.stm.incoming:
            byte = self.stm._serial.read(1)
            if not byte or byte[0] != START_BYTE:
                continue

            header = self.stm._serial.read(2)
            if not header or len(header) < 2:
                return

            msg_type, size = struct.unpack('<BB', header)

            payload = self.stm._serial.read(size)
            if not payload or len(payload) < size:
                return

            self.handle_msg(msg_type, payload)

    def handle_msg(self, msg_type: int, payload: bytes):
        try:
            if msg_type == PacketType.IMU:
                self.handle_imu(payload)
            elif msg_type == PacketType.GPS:
                self.handle_gps(payload)
            elif msg_type == PacketType.ENCODERS:
                self.handle_encoders(payload)
            elif msg_type == PacketType.STATUS:
                self.handle_status(payload)
            elif msg_type == PacketType.ANTENNA:
                self.handle_antenna(payload)
            else:
                self.get_logger().warn(f'Unknown message type: {msg_type}')
        except Exception as e:
            self.get_logger().error(f'Failed to handle msg type {msg_type}: {e}')

    def handle_imu(self, payload: bytes):
        q1, q2, q3, q4, alpha, beta, psi, xd, yd, zd = struct.unpack(
            PAYLOAD_FMT[PacketType.IMU], payload)

        msg = Imu()
        msg.header.stamp              = self.get_clock().now().to_msg()
        msg.header.frame_id           = 'imu_link'
        msg.orientation.x             = float(q1)
        msg.orientation.y             = float(q2)
        msg.orientation.z             = float(q3)
        msg.orientation.w             = float(q4)
        msg.angular_velocity.x        = float(alpha)
        msg.angular_velocity.y        = float(beta)
        msg.angular_velocity.z        = float(psi)
        msg.linear_acceleration.x     = float(xd)
        msg.linear_acceleration.y     = float(yd)
        msg.linear_acceleration.z     = float(zd)
        self.pub_imu.publish(msg)

    def handle_gps(self, payload: bytes):
        vals = struct.unpack(PAYLOAD_FMT[PacketType.GPS], payload)

        msg = NavSatFix()
        msg.header.stamp             = self.get_clock().now().to_msg()
        # msg.header.frame_id          = 'gps_link'
        msg.status.status            = NavSatStatus.STATUS_FIX
        msg.status.service           = NavSatStatus.SERVICE_GPS
        msg.longitude                = float(vals[0])
        msg.latitude                 = float(vals[1])
        msg.altitude                 = 0.0
        msg.position_covariance      = [float(v) for v in vals[2:]]
        msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_KNOWN
        self.pub_gps.publish(msg)

    def handle_status(self, payload: bytes):
        vals = struct.unpack('<2f 4f 2f B 4B', payload)

        msg = RoverStatus()
        msg.header.stamp        = self.get_clock().now().to_msg()
        msg.header.frame_id     = 'base_link'
        msg.battery_voltage_1   = vals[0]
        msg.battery_voltage_2   = vals[1]
        msg.motor_current_fl    = vals[2]
        msg.motor_current_fr    = vals[3]
        msg.motor_current_bl    = vals[4]
        msg.motor_current_br    = vals[5]
        msg.servo_1_angle       = vals[6]
        msg.servo_2_angle       = vals[7]
        combined_byte =vals[8]
        msg.laser_enabled = bool(combined_byte & 0x01)
        msg.led_enabled = bool(combined_byte & 0x02)
        msg.emergency_stop = bool(combined_byte & 0x03)
        msg.laser_enabled       = vals[8]
        msg.led_enabled         = vals[9]
        msg.emergency_stop      = vals[10]
        msg.imu_calibration     = list(vals[9:13])

        self.pub_status.publish(msg)

    def handle_encoders(self, payload: bytes):
        fl, bl, fr, br = struct.unpack(PAYLOAD_FMT[PacketType.ENCODERS], payload)

        msg = WheelVel()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.front_left      = float(fl)
        msg.front_right     = float(fr)
        msg.back_left       = float(bl)
        msg.back_right      = float(br)
        self.pub_wheel_vel.publish(msg)

    def handle_antenna(self, payload: bytes):
        vals = struct.unpack(PAYLOAD_FMT[PacketType.ANTENNA], payload)
        msg = NavSatFix()
        msg.header.stamp    = self.get_clock().now().to_msg()
        # msg.header.frame_id = 'antenna_link'
        msg.longitude = float(vals[0])
        msg.latitude  = float(vals[1])
        self.pub_antenna.publish(msg)


    def _send(self, pkt_type: PacketType, payload: bytes):
        packet = bytes([START_BYTE]) + struct.pack('<BB', pkt_type.value, len(payload)) + payload
        self.stm.send(packet)

    def _cb_cmd_vel(self, msg: Speed):
        v_left=msg.left
        v_right=msg.right

        payload = struct.pack('<2f',
           v_left,v_right
        )
        self._send(PacketType.CMD_VEL, payload)

    def _cb_laser(self, msg: Bool):
        self._send(PacketType.LASER, struct.pack('<?', msg.data))

    def _cb_servo(self, msg: Float32MultiArray):
        if len(msg.data) != 2:
            self.get_logger().warn('servo needs [servo1, servo2]')
            return
        self._send(PacketType.SERVO, struct.pack('<2f', *msg.data))

    def _cb_mode(self, msg: Bool):
        self._send(PacketType.MODE, struct.pack('<?', msg.data))

    def _cb_antenna(self, msg: Float32MultiArray):
        if len(msg.data) != 1:
            self.get_logger().warn('antenna_angle needs [angle]')
            return
        self._send(PacketType.MODE, struct.pack('<f', msg.data[0]))


    def destroy_node(self):
        self.stm.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = STM32Node()
        rclpy.spin(node)
    except RuntimeError as e:
        print(f'[stm32_node] Failed to start: {e}')
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()