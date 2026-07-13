#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Vector3
import math
import numpy as np
from tf_transformations import euler_from_quaternion

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


    def imu_callback(self, msg):
        """Callback function for IMU messages"""
        # Extract quaternion
        qx = msg.orientation.x
        qy = msg.orientation.y
        qz = msg.orientation.z
        qw = msg.orientation.w
        
        # Convert to Euler angles
        # roll, pitch, yaw = self.quaternion_to_euler(qx, qy, qz, qw)
        angles = euler_from_quaternion([qx, qy, qz, qw])
        roll, pitch, yaw = angles[0], angles[1], angles[2]
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