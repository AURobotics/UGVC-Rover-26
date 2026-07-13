#!/usr/bin/env python3
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class ObstacleAvoidance(Node):
    def __init__(self):
        super().__init__('obstacle_node')

        self.declare_parameter('safe_distance', 0.6)      # meters, start slowing/steering
        self.declare_parameter('stop_distance', 0.4)       # meters, hard stop distance
        self.declare_parameter('cruise_speed', 0.2)         # m/s forward speed when clear
        self.declare_parameter('turn_speed', 0.6)           # rad/s when avoiding
        self.declare_parameter('front_angle_deg', 60.0)     # total width of "front" cone
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        self.safe_distance = self.get_parameter('safe_distance').value
        self.stop_distance = self.get_parameter('stop_distance').value
        self.cruise_speed = self.get_parameter('cruise_speed').value
        self.turn_speed = self.get_parameter('turn_speed').value
        self.front_angle = math.radians(self.get_parameter('front_angle_deg').value)

        scan_topic = self.get_parameter('scan_topic').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value

        self.sub = self.create_subscription(
            LaserScan, scan_topic, self.scan_callback, qos_profile_sensor_data
        )
        self.pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        self.get_logger().info(
            f'Obstacle avoidance node started. Listening on "{scan_topic}", '
            f'publishing to "{cmd_vel_topic}".'
        )

    def scan_callback(self, msg: LaserScan):
        ranges = msg.ranges
        n = len(ranges)
        if n == 0:
            return

        angle_min = msg.angle_min
        angle_increment = msg.angle_increment

        def clean(r):
            # Filter out inf/nan/out-of-range readings.
            if r is None or math.isnan(r) or math.isinf(r):
                return float('inf')
            if r < msg.range_min or r > msg.range_max:
                return float('inf')
            return r

        # Index helper: convert an angle (radians, 0 = straight ahead) to array index.
        def angle_to_index(angle):
            idx = int(round((angle - angle_min) / angle_increment))
            return max(0, min(n - 1, idx))

        half_front = self.front_angle / 2.0

        front_start = angle_to_index(-half_front)
        front_end = angle_to_index(half_front)
        left_start = angle_to_index(half_front)
        left_end = angle_to_index(math.pi / 2.0)
        right_start = angle_to_index(-math.pi / 2.0)
        right_end = angle_to_index(-half_front)

        def min_in_range(a, b):
            if a > b:
                a, b = b, a
            segment = [clean(r) for r in ranges[a:b + 1]]
            return min(segment) if segment else float('inf')

        front_min = min_in_range(front_start, front_end)
        left_min = min_in_range(left_start, left_end)
        right_min = min_in_range(right_start, right_end)

        twist = Twist()

        if front_min < self.stop_distance:
            # Obstacle very close: stop forward motion, turn in place
            # toward the more open side.
            twist.linear.x = 0.0
            twist.angular.z = self.turn_speed if left_min > right_min else -self.turn_speed

        elif front_min < self.safe_distance:
            # Obstacle ahead but not critical: slow down and curve
            # away from it toward the more open side.
            # Scale speed down as the obstacle gets closer.
            fraction = (front_min - self.stop_distance) / (self.safe_distance - self.stop_distance)
            fraction = max(0.0, min(1.0, fraction))
            twist.linear.x = self.cruise_speed * fraction
            twist.angular.z = self.turn_speed if left_min > right_min else -self.turn_speed

        else:
            # Path clear: go straight.
            twist.linear.x = self.cruise_speed
            twist.angular.z = 0.0
        self.get_logger().info(f'front_min={front_min:.2f}, left_min={left_min:.2f}, right_min={right_min:.2f}, '
                               f'twist.linear.x={twist.linear.x:.2f}, twist.angular.z={twist.angular.z:.2f}')

        self.pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoidance()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the rover on shutdown.
        stop = Twist()
        node.pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()