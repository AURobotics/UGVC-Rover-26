#!/usr/bin/env python3
"""
test_cmd_mux.py - Simple test node for cmd_mux_node
Publishes test commands to verify functionality
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import time

class TestCmdMux(Node):
    def __init__(self):
        super().__init__('test_cmd_mux')
        
        # Publishers
        self.twist_pub = self.create_publisher(Twist, '/cmd_vel/lane_pid', 10)
        self.state_pub = self.create_publisher(String, '/mission/active_state', 10)
        
        self.get_logger().info('Test Node Started')
        
        # Run tests after 1 second
        self.timer = self.create_timer(1.0, self.run_tests)
        
    def publish_twist(self, v, w):
        """Publish a Twist message"""
        msg = Twist()
        msg.linear.x = v
        msg.angular.z = w
        self.twist_pub.publish(msg)
        self.get_logger().info(f'Published: v={v}, w={w}')
    
    def publish_state(self, state):
        """Publish mission state"""
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)
        self.get_logger().info(f'State: {state}')
    
    def run_tests(self):
        self.get_logger().info('=' * 50)
        self.get_logger().info('Starting Tests...')
        self.get_logger().info('=' * 50)
        
        # Test 1: LANE state with linear motion
        self.get_logger().info('\n--- Test 1: LANE + Linear Motion ---')
        self.publish_state('LANE')
        time.sleep(0.5)
        self.publish_twist(0.5, 0.0)
        time.sleep(2)
        
        # Test 2: LANE state with rotation
        self.get_logger().info('\n--- Test 2: LANE + Rotation ---')
        self.publish_twist(0.0, 1.0)
        time.sleep(2)
        
        # Test 3: LANE state with combined motion
        self.get_logger().info('\n--- Test 3: LANE + Combined Motion ---')
        self.publish_twist(0.5, 0.5)
        time.sleep(2)
        
        # Test 4: Switch to WP state
        self.get_logger().info('\n--- Test 4: WP State ---')
        self.publish_state('WP')
        time.sleep(0.5)
        self.publish_twist(0.3, 0.0)
        time.sleep(2)
        
        # Test 5: IDLE state (should output zero)
        self.get_logger().info('\n--- Test 5: IDLE State (Zero Output) ---')
        self.publish_state('IDLE')
        time.sleep(0.5)
        self.publish_twist(0.5, 0.0)
        time.sleep(2)
        
        # Test 6: Back to LANE
        self.get_logger().info('\n--- Test 6: Back to LANE ---')
        self.publish_state('LANE')
        time.sleep(0.5)
        self.publish_twist(0.5, 0.0)
        time.sleep(2)
        
        self.get_logger().info('\n' + '=' * 50)
        self.get_logger().info('Tests Complete!')
        self.get_logger().info('=' * 50)
        
        # Shutdown after tests
        self.destroy_timer(self.timer)
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = TestCmdMux()
    rclpy.spin(node)

if __name__ == '__main__':
    main()