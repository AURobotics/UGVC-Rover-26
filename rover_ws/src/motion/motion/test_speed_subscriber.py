#!/usr/bin/env python3
"""
test_speed_subscriber.py - Simple node to monitor /cmd_speed output
Displays left and right wheel speeds
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class SpeedSubscriber(Node):
    def __init__(self):
        super().__init__('speed_subscriber')
        
        # Subscribe to /cmd_speed
        self.subscription = self.create_subscription(
            Float64MultiArray,
            '/cmd_speed',
            self.speed_callback,
            10
        )
        
        self.get_logger().info('Speed Subscriber Started - Waiting for /cmd_speed messages...')
        self.get_logger().info('Press Ctrl+C to stop\n')
        
        self.counter = 0
    
    def speed_callback(self, msg):
        self.counter += 1
        self.get_logger().info(
            f'[{self.counter}] Left: {msg.data[0]:6.2f} rad/s | Right: {msg.data[1]:6.2f} rad/s'
        )

def main(args=None):
    rclpy.init(args=args)
    node = SpeedSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('\nShutting down...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()