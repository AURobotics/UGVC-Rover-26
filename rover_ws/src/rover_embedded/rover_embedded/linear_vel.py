#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
# from rover_interfaces.msg import Speed

# WHEEL_BASE = 0.74  # meters


class Linear_Vel(Node):
    def __init__(self):
        super().__init__('linear_vel')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        # self.create_subscription(Twist, '/cmd_vel', self._cb, 10)
        # self.get_logger().info(
        #     f'twist_to_speed ready  (wheelbase={self.wheel_base} m)'
        # )
        self.create_timer(0.1, self.publish_linear_velocity)

    # def _cb(self, msg: Twist):
    #     half_base = self.wheel_base / 2.0
    #     v_left  = msg.linear.x - msg.angular.z * half_base
    #     v_right = msg.linear.x + msg.angular.z * half_base

    #     out = Speed()
    #     out.left  = float(v_left)
    #     out.right = float(v_right)
    #     self.pub.publish(out)

    def publish_linear_velocity(self):
        msg = Twist()
        msg.linear.x = 0.55  # Set the desired linear velocity (m/s)
        msg.angular.z = 0.0  # Set the desired angular velocity (rad/s)
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = Linear_Vel()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()