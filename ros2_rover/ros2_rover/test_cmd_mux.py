#!/usr/bin/env python3
"""
Simple cmd_mux_node - No external dependencies
Just copy and run this file
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_msgs.msg import Float64MultiArray

class SimpleCmdMux(Node):
    def __init__(self):
        super().__init__('cmd_mux_node')
        
        # Parameters
        self.wheel_radius = 0.10
        self.wheelbase = 0.50
        self.max_speed = 10.0
        
        # State
        self.state = 'IDLE'
        self.latest_cmd = None
        
        # Publisher
        self.pub = self.create_publisher(Float64MultiArray, '/cmd_speed', 10)
        
        # Subscribers
        self.create_subscription(Twist, '/cmd_vel/lane_pid', self.lane_callback, 10)
        self.create_subscription(Twist, '/cmd_vel/waypoint', self.wp_callback, 10)
        self.create_subscription(Twist, '/cmd_vel/teleop', self.teleop_callback, 10)
        self.create_subscription(String, '/mission/active_state', self.state_callback, 10)
        
        # Timer (50Hz)
        self.create_timer(0.02, self.publish_loop)
        
        self.get_logger().info('Simple Cmd Mux Node Started')
        self.get_logger().info(f'Parameters: r={self.wheel_radius}, L={self.wheelbase}')
    
    def lane_callback(self, msg):
        if self.state == 'LANE':
            self.latest_cmd = msg
            self.get_logger().debug(f'LANE cmd: v={msg.linear.x}, w={msg.angular.z}')
    
    def wp_callback(self, msg):
        if self.state == 'WP':
            self.latest_cmd = msg
            self.get_logger().debug(f'WP cmd: v={msg.linear.x}, w={msg.angular.z}')
    
    def teleop_callback(self, msg):
        # Teleop always overrides!
        self.latest_cmd = msg
        self.get_logger().debug(f'TELEOP cmd: v={msg.linear.x}, w={msg.angular.z}')
    
    def state_callback(self, msg):
        old_state = self.state
        self.state = msg.data
        self.get_logger().info(f'State: {old_state} -> {self.state}')
        
        # Clear command when entering IDLE
        if self.state == 'IDLE':
            self.latest_cmd = None
    
    def publish_loop(self):
        v = 0.0
        w = 0.0
        
        # Use latest command if available
        if self.latest_cmd is not None:
            v = self.latest_cmd.linear.x
            w = self.latest_cmd.angular.z
        
        # Kinematics
        v_left = (v - w * self.wheelbase / 2.0) / self.wheel_radius
        v_right = (v + w * self.wheelbase / 2.0) / self.wheel_radius
        
        # Clamp
        v_left = max(-self.max_speed, min(self.max_speed, v_left))
        v_right = max(-self.max_speed, min(self.max_speed, v_right))
        
        # Publish
        msg = Float64MultiArray()
        msg.data = [v_left, v_right]
        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = SimpleCmdMux()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
