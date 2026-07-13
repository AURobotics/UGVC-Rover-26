import rclpy
from rclpy.node import Node
from rover_interfaces.msg import WheelVel
from sensor_msgs.msg import JointState
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry

class navsat_sim_node(Node):

    def __init__(self):
        super().__init__('encoder_sim_node')

        #topics
        self.publisher_ = self.create_publisher(Odometry, '/odometry/gps/sim', 10)
        self.subscription = self.create_subscription(
            Odometry,
            '/odometry/gps',
            self.listener_callback,
            10)
        self.current_msg = None
    
    def listener_callback(self, msg:Odometry):
        msg.pose.covariance = [
            0.5, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.5, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.5, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,

        ]
        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)

    navsat_sim_node_obj = navsat_sim_node()

    rclpy.spin(navsat_sim_node_obj)

    navsat_sim_node_obj.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

