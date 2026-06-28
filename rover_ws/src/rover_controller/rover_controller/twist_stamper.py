import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped

class TwistStamper(Node):
    def __init__(self):
        super().__init__('twist_stamper')
        self.sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.callback,
            10)
        self.pub = self.create_publisher(
            TwistStamped,
            '/cmd_vel_stamped',
            10)

    def callback(self, msg):
        stamped = TwistStamped()
        stamped.header.stamp = self.get_clock().now().to_msg()
        stamped.header.frame_id = 'base_link'
        stamped.twist = msg
        self.pub.publish(stamped)

def main():
    rclpy.init()
    node = TwistStamper()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()