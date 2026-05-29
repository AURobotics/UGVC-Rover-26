#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float32


class CameraServoNode(Node):
    def __init__(self):
        super().__init__('camera_servo_node')

        # Parameters
        self.declare_parameter('axis_x', 2)        # Horizontal control axis
        self.declare_parameter('axis_y', 3)        # Vertical control axis
        self.declare_parameter('deadzone', 0.1)
        self.declare_parameter('speed_x', 90.0)    # degrees per second
        self.declare_parameter('speed_y', 45.0)    # degrees per second
        self.declare_parameter('publish_rate', 50.0)

        self.axis_x = self.get_parameter('axis_x').value
        self.axis_y = self.get_parameter('axis_y').value
        self.deadzone = self.get_parameter('deadzone').value
        self.speed_x = self.get_parameter('speed_x').value
        self.speed_y = self.get_parameter('speed_y').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # Current positions
        self.pos_x = 0.0
        self.pos_y = 0.0

        # Publishers
        self.pub_x = self.create_publisher(Float32, '/camera/x', 10)
        self.pub_y = self.create_publisher(Float32, '/camera/y', 10)

        # Subscriber
        self.create_subscription(Joy, '/joy', self.joy_callback, 10)

        # Timer
        self.create_timer(1.0 / self.publish_rate, self.publish)

        self.get_logger().info(f'Camera Servo Node Started at {self.publish_rate}Hz')

    def joy_callback(self, msg: Joy):
        # Apply deadzone
        input_x = msg.axes[self.axis_x] if abs(msg.axes[self.axis_x]) > self.deadzone else 0.0
        input_y = msg.axes[self.axis_y] if abs(msg.axes[self.axis_y]) > self.deadzone else 0.0

        # Integrate with delta time
        dt = 1.0 / self.publish_rate
        self.pos_x += input_x * self.speed_x * dt
        self.pos_y += input_y * self.speed_y * dt

        # Clamp to limits
        self.pos_x = max(-90.0, min(90.0, self.pos_x))
        self.pos_y = max(-45.0, min(45.0, self.pos_y))

    def publish(self):
        self.pub_x.publish(Float32(data=self.pos_x))
        self.pub_y.publish(Float32(data=self.pos_y))

        self.get_logger().info(
            f'Camera: X={self.pos_x:.1f}°, Y={self.pos_y:.1f}°',
            throttle_duration_sec=1.0
        )

    def stop_servos(self):
        self.pub_x.publish(Float32(data=0.0))
        self.pub_y.publish(Float32(data=0.0))
        self.get_logger().info('Camera servos centered')


def main(args=None):
    rclpy.init(args=args)
    node = CameraServoNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_servos()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()