import rclpy
from rclpy.node import Node
from rover_interfaces.msg import WheelVel
from sensor_msgs.msg import JointState
from sensor_msgs.msg import Imu

class encoder_sim_node(Node):

    def __init__(self):
        super().__init__('encoder_sim_node')

        #topics
        self.publisher_ = self.create_publisher(WheelVel, '/wheel_vel', 10)
        self.timer = self.create_timer(0.02, self.timer_callback)
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        self.current_msg = None
    def timer_callback(self):
        if(self.current_msg != None):
            self.current_msg.header.stamp = self.get_clock().now().to_msg()
            self.publish(self.current_msg)
    def listener_callback(self, msg:JointState):
        self.current_msg = msg
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

