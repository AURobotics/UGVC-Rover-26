#!/usr/bin/env python3
"""
test_joy_simulator.py - Simulates joystick input for testing MANUAL mode
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String
import time

class JoySimulator(Node):
    def __init__(self):
        super().__init__('joy_simulator')
        
        # Publisher
        self.joy_pub = self.create_publisher(Joy, '/joy', 10)
        
        # State publisher
        self.state_pub = self.create_publisher(String, '/mission/active_state', 10)
        
        self.get_logger().info('Joy Simulator Started')
        
        # Run simulation after 1 second
        self.timer = self.create_timer(1.0, self.run_simulation)
    
    def publish_joy(self, linear, angular):
        """Publish joystick command"""
        msg = Joy()
        msg.axes = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        msg.axes[1] = linear   # Left stick up/down (axis 1)
        msg.axes[0] = angular  # Left stick left/right (axis 0)
        self.joy_pub.publish(msg)
        self.get_logger().info(f'Joy: linear={linear:.2f}, angular={angular:.2f}')
    
    def publish_state(self, state):
        """Publish mission state"""
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)
        self.get_logger().info(f'State: {state}')
    
    def run_simulation(self):
        self.get_logger().info('=' * 50)
        self.get_logger().info('Starting MANUAL Mode Test...')
        self.get_logger().info('=' * 50)
        
        # Set to MANUAL state
        self.get_logger().info('\n--- Setting to MANUAL mode ---')
        self.publish_state('MANUAL')
        time.sleep(1)
        
        # Test forward
        self.get_logger().info('\n--- Forward ---')
        self.publish_joy(0.5, 0.0)
        time.sleep(2)
        
        # Test reverse
        self.get_logger().info('\n--- Reverse ---')
        self.publish_joy(-0.5, 0.0)
        time.sleep(2)
        
        # Test turn left
        self.get_logger().info('\n--- Turn Left ---')
        self.publish_joy(0.0, -0.8)
        time.sleep(2)
        
        # Test turn right
        self.get_logger().info('\n--- Turn Right ---')
        self.publish_joy(0.0, 0.8)
        time.sleep(2)
        
        # Test diagonal
        self.get_logger().info('\n--- Forward + Right Turn ---')
        self.publish_joy(0.5, 0.5)
        time.sleep(2)
        
        # Stop
        self.get_logger().info('\n--- Stop ---')
        self.publish_joy(0.0, 0.0)
        time.sleep(1)
        
        self.get_logger().info('\n' + '=' * 50)
        self.get_logger().info('Simulation Complete!')
        self.get_logger().info('=' * 50)
        
        # Shutdown
        self.destroy_timer(self.timer)
        rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = JoySimulator()
    rclpy.spin(node)

if __name__ == '__main__':
    main()