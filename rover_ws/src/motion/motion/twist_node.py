#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from rover_interfaces.msg import Speed

WHEEL_BASE = 0.74  # meters


class TwistToSpeed(Node):
    def __init__(self):
        super().__init__('twist_to_speed')
        self.declare_parameter('wheelbase', WHEEL_BASE)
        self.wheel_base = self.get_parameter('wheelbase').value
        self.pub = self.create_publisher(Speed, '/cmd_speed', 10)
        self.create_subscription(Twist, '/cmd_vel', self._cb, 10)
        self.get_logger().info(
            f'twist_to_speed ready  (wheelbase={self.wheel_base} m)'
        )

    def _cb(self, msg: Twist):
        half_base = self.wheel_base / 2.0
        v_left  = msg.linear.x - msg.angular.z * half_base
        v_right = msg.linear.x + msg.angular.z * half_base

        out = Speed()
        out.left  = float(v_left)
        out.right = float(v_right)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = TwistToSpeed()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()