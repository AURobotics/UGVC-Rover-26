#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3
import math
import numpy as np

class QuaternionToEuler(Node):
    def __init__(self):
        super().__init__('quaternion_to_euler')
        
        # Subscribe to IMU topic
        self.subscription = self.create_subscription(
            Imu,
            '/imu/data',  # Change this to your IMU topic
            self.imu_callback,
            10
        )
        
        # Publisher for Euler angles
        self.euler_publisher = self.create_publisher(
            Vector3,
            '/imu/euler',  # Topic for Euler angles
            10
        )
        
        # Timer for printing (optional - print every 1 second)
        self.print_timer = self.create_timer(0.1, self.print_euler_angles)
        
        # Store latest Euler angles
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.new_data_received = False
        
        self.get_logger().info('Quaternion to Euler converter node started')
        self.get_logger().info('Subscribing to: /imu/data')
        self.get_logger().info('Publishing to: /imu/euler')

    def quaternion_to_euler(self, x, y, z, w):
        """
        Convert quaternion to Euler angles (roll, pitch, yaw)
        Returns angles in radians
        """
        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2.0 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # Use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return roll, pitch, yaw

    def imu_callback(self, msg):
        """Callback function for IMU messages"""
        # Extract quaternion
        qx = msg.orientation.x
        qy = msg.orientation.y
        qz = msg.orientation.z
        qw = msg.orientation.w
        
        # Convert to Euler angles
        roll, pitch, yaw = self.quaternion_to_euler(qx, qy, qz, qw)
        
        # Convert to degrees
        roll_deg = math.degrees(roll)
        pitch_deg = math.degrees(pitch)
        yaw_deg = math.degrees(yaw)
        
        # Store latest values
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.new_data_received = True
        
        # Publish Euler angles as Vector3
        euler_msg = Vector3()
        euler_msg.x = roll
        euler_msg.y = pitch
        euler_msg.z = yaw
        self.euler_publisher.publish(euler_msg)
        
        # Optional: Print immediately (comment out if you prefer timer-based printing)
        # self.get_logger().info(
        #     f'Roll: {roll_deg:.2f}°, Pitch: {pitch_deg:.2f}°, Yaw: {yaw_deg:.2f}°'
        # )

    def print_euler_angles(self):
        """Print Euler angles at regular intervals"""
        if self.new_data_received:
            roll_deg = math.degrees(self.roll)
            pitch_deg = math.degrees(self.pitch)
            yaw_deg = math.degrees(self.yaw)
            
            self.get_logger().info('=' * 50)
            self.get_logger().info('EULER ANGLES:')
            self.get_logger().info(f'  Roll (X):  {roll_deg:8.2f}°  |  {self.roll:8.4f} rad')
            self.get_logger().info(f'  Pitch (Y): {pitch_deg:8.2f}°  |  {self.pitch:8.4f} rad')
            self.get_logger().info(f'  Yaw (Z):   {yaw_deg:8.2f}°  |  {self.yaw:8.4f} rad')
            self.get_logger().info('=' * 50)

def main(args=None):
    rclpy.init(args=args)
    node = QuaternionToEuler()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()