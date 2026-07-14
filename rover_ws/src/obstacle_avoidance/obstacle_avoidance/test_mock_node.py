#!/usr/bin/env python3
"""
print_front_ranges.py

Minimal debug node: subscribes to /scan and prints only the ranges
in the front cone (default +/- 30 degrees around straight ahead).
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class PrintFrontRanges(Node):
    def __init__(self):
        super().__init__('test_mock_node')

        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('front_angle_deg', 60.0)  # total width of front cone

        scan_topic = self.get_parameter('scan_topic').value
        self.front_angle = math.radians(self.get_parameter('front_angle_deg').value)

        self.sub = self.create_subscription(
            LaserScan, scan_topic, self.scan_callback, qos_profile_sensor_data
        )

        self.get_logger().info(f'Printing front ranges from "{scan_topic}"...')

    def scan_callback(self, msg: LaserScan):
        n = len(msg.ranges)
        if n == 0:
            self.get_logger().warn('Received empty scan.')
            return

        angle_min = msg.angle_min
        angle_increment = msg.angle_increment
        half_front = self.front_angle / 2.0

        def angle_to_index(angle):
            idx = int(round((angle - angle_min) / angle_increment))
            return max(0, min(n - 1, idx))

        start = angle_to_index(half_front + 180)
        end = angle_to_index(-math.pi / 2.0)
        if start > end:
            start, end = end, start

        front_ranges = msg.ranges[start:end + 1]

        # Print rounded values, on one line, easy to eyeball.
        rounded = [round(r, 2) if not math.isnan(r) and not math.isinf(r) else None
                   for r in front_ranges]
        print(f'Front ranges ({len(rounded)} pts): {rounded}')


def main(args=None):
    rclpy.init(args=args)
    node = PrintFrontRanges()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()