import rclpy
from rclpy.node import Node
from ugvc_msgs.msg import WheelVel
from sensor_msgs.msg import JointState
from sensor_msgs.msg import Imu

class encoder_sim_node(Node):

    def __init__(self):
        super().__init__('encoder_sim_node')

        #topics
        self.publisher_ = self.create_publisher(WheelVel, '/wheel_vel', 10)
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        
    def listener_callback(self, msg:JointState):
        self.publish(msg)
    def publish(self, input:JointState):
        msg = WheelVel()
        msg.header.frame_id = 'base_link'
        msg.header.stamp = self.get_clock().now().to_msg()
        lft_wheel_idx = input.name.index('wheel_left_joint')
        rt_wheel_idx = input.name.index('wheel_right_joint')
        msg.front_left = msg.back_left = input.velocity[lft_wheel_idx]
        msg.front_right = msg.back_right = input.velocity[rt_wheel_idx]
        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    encoder_sim_node_obj = encoder_sim_node()

    rclpy.spin(encoder_sim_node_obj)

    encoder_sim_node_obj.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

