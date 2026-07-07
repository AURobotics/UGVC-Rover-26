import rclpy
from rclpy.node import Node
from rover_interfaces.msg import WheelVel
from nav_msgs.msg import Odometry
from tf_transformations import quaternion_from_euler
from geometry_msgs.msg import Point, Quaternion, Vector3
from math import cos, sin

class OdomNode(Node):

    def __init__(self):
        super().__init__('odom_node')
        #parameters
        self.declare_parameter('wheel_base', 0.0) #added 0.0 as default just to make the ros2 warning shutup
        self.declare_parameter('wheel_radius', 0.0)
        self.declare_parameter('position_covariance', [0.0] * 36)
        self.declare_parameter('twist_covariance', [0.0] * 36)

        self.wheel_base = self.get_parameter('wheel_base').get_parameter_value().double_value
        self.wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value

        #topics
        self.publisher_ = self.create_publisher(Odometry, '/odometry/unfiltered', 10)
        self.subscription = self.create_subscription(
            WheelVel,
            '/wheel_vel',
            self.listener_callback,
            10)
        
        #variables
        self.angle = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.curr_stamp = -1
        self.prev_stamp = -1
    def listener_callback(self, msg:WheelVel):
        self.curr_stamp = msg.header.stamp.sec + (msg.header.stamp.nanosec * 1e-9)
        
        if(self.prev_stamp is None): #if this is the first message the node receives, initialize the prev stamp parameter and wait for next message
            self.prev_stamp = self.curr_stamp
            self.get_logger().info('wheel base: "%f"' % float(self.wheel_base))
            self.get_logger().info('wheel radius: "%f"' % float(self.wheel_radius))
            return
        
        odom_matrix = self.forward_kinematics(msg.front_left, msg.front_right, msg.back_left, msg.back_right)
        self.prev_stamp = self.curr_stamp
        self.publish(odom_matrix)
        

    def publish(self, odom_matrix):
        msg = Odometry()
        pos_co = self.get_parameter('position_covariance').get_parameter_value().double_array_value
        twist_co = self.get_parameter('twist_covariance').get_parameter_value().double_array_value


        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "odom"
        msg.child_frame_id = "base_link"

        x,y,z = odom_matrix[0]
        msg.pose.pose.position = Point(x=x, y=y, z=z)
        q = quaternion_from_euler(*odom_matrix[1])
        msg.pose.pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        msg.pose.covariance = pos_co

        x,y,z = odom_matrix[2]
        msg.twist.twist.linear = Vector3(x=x, y=y, z=z)
        x,y,z = odom_matrix[3]
        msg.twist.twist.angular = Vector3(x=x, y=y, z=z)
        msg.twist.covariance = twist_co

        
        self.publisher_.publish(msg)
        #self.get_logger().info('Publishing: "%s"' % msg.data)

    def forward_kinematics(self, fl_vel, fr_vel, bl_vel, br_vel):

        v_left = (fl_vel + bl_vel) / 2
        v_right = (fr_vel + br_vel) / 2
        linear_velocity = ((v_left + v_right) / 2) * self.wheel_radius #average of velocity values of wheels multiplied by wheel radius so that it becomes linear velocity
        angular_velocity = (v_right - v_left) * self.wheel_radius / self.wheel_base
        elapsed_time = self.curr_stamp - self.prev_stamp
        self.angle += angular_velocity * elapsed_time
        x_dot = linear_velocity * cos(self.angle)
        y_dot = linear_velocity * sin(self.angle)
        z_dot = 0.0
        #no z_dot
        self.x += x_dot * elapsed_time
        self.y += y_dot * elapsed_time
        #no z
        return [[self.x, self.y, self.z], [0.0, 0.0, self.angle], [x_dot, y_dot, z_dot], [0.0, 0.0, angular_velocity]] 



def main(args=None):
    rclpy.init(args=args)

    odom_node_obj = OdomNode()

    rclpy.spin(odom_node_obj)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    odom_node_obj.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

