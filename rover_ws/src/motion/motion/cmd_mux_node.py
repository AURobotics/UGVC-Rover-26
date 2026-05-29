#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import String
from ugvc_msgs.msg import Speed
from sensor_msgs.msg import Joy


# Mission State Mapping
STATE_MAP = {
    'IDLE': None,
    'LANE': '/cmd_vel/lane_pid',
    'WP': '/cmd_vel/waypoint',
    'SEARCH': '/cmd_vel/pothole',
    'DONE': None,
    'MANUAL': None,
}

class CmdMuxNode(Node):

    def __init__(self):
        super().__init__('cmd_mux_node')

        # Parameters
        self.declare_parameter('wheel_radius', 0.10)       # meters
        self.declare_parameter('wheelbase', 0.50)          # meters
        self.declare_parameter('max_wheel_speed', 10.0)    # rad/s
        self.declare_parameter('publish_rate', 50.0)       # Hz
        self.declare_parameter('joy_linear_axis',  1)     # axes index
        self.declare_parameter('joy_angular_axis', 0)     # axes index
        self.declare_parameter('joy_max_linear',   1.0)   # m/s
        self.declare_parameter('joy_max_angular',  2.0)   # rad/s
        self.declare_parameter('joy_deadzone',     0.1)   # 0.0 – 1.0

        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.wheelbase = self.get_parameter('wheelbase').value
        self.max_wheel_speed = self.get_parameter('max_wheel_speed').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.joy_linear_axis = self.get_parameter('joy_linear_axis').value
        self.joy_angular_axis = self.get_parameter('joy_angular_axis').value
        self.joy_max_linear = self.get_parameter('joy_max_linear').value
        self.joy_max_angular = self.get_parameter('joy_max_angular').value
        self.joy_deadzone = self.get_parameter('joy_deadzone').value

        # Internal Variables
        self.state = 'IDLE'

        self.latest_cmds = {
            '/cmd_vel/waypoint': None,
            '/cmd_vel/lane_pid': None,
            '/cmd_vel/pothole':  None,
        }
 
        self.joy_msg = None

        # Publisher
        self.speed_pub = self.create_publisher(Speed,'/cmd_speed',10)

        # Subscribers
        self.create_subscription(Twist,'/cmd_vel/waypoint', self.waypoint_callback, 10)
        self.create_subscription(Twist,'/cmd_vel/lane_pid', self.lane_pid_callback, 10)
        self.create_subscription(Twist,'/cmd_vel/pothole', self.pothole_callback, 10)
        self.create_subscription(Joy,'/joy', self.joy_callback, 10)

        self.create_subscription(String,'/mission/active_state',self.state_callback,10)

        # Main Timer
        self.create_timer(1.0 / self.publish_rate,self.publish_speed)

        self.get_logger().info('Cmd Mux Node Started')

    # Twist Callback
    def waypoint_callback(self, msg: Twist):
        self.latest_cmds['/cmd_vel/waypoint'] = msg
 
    def lane_pid_callback(self, msg: Twist):
        self.latest_cmds['/cmd_vel/lane_pid'] = msg
 
    def pothole_callback(self, msg: Twist):
        self.latest_cmds['/cmd_vel/pothole'] = msg
 
    def joy_callback(self, msg: Joy):
        self.joy_msg = msg

    # Mission State Callback
    def state_callback(self, msg: String):
        new_state = msg.data.strip()
 
        if new_state not in STATE_MAP:
            self.get_logger().warn(f'Unknown state: {new_state}')
            return
 
        if new_state != self.state:
            self.get_logger().info(f'State changed: {self.state} → {new_state}')
 
        self.state = new_state

    def get_active_command(self):
 
        # MANUAL: compute v/ω from joystick axes
        if self.state == 'MANUAL':
            if self.joy_msg is None:
                self.get_logger().warn(
                    'MANUAL state but no joy message received, outputting zero.',
                    throttle_duration_sec=1.0
                )
                return 0.0, 0.0
 
            linear_val  = self.joy_msg.axes[self.joy_linear_axis]
            angular_val = self.joy_msg.axes[self.joy_angular_axis]
 
            # Apply deadzone
            if abs(linear_val)  < self.joy_deadzone:
                linear_val  = 0.0
            if abs(angular_val) < self.joy_deadzone:
                angular_val = 0.0
 
            v = linear_val  * self.joy_max_linear
            w = angular_val * self.joy_max_angular
            return v, w
 
        elif self.state == 'LANE' :
            cmd = self.latest_cmds.get('/cmd_vel/lane_pid')
            if cmd is None:
                self.get_logger().warn(
                    'LANE state but no lane_pid command received, outputting zero.',
                    throttle_duration_sec=1.0
                )
                return 0.0, 0.0
            return cmd.linear.x, cmd.angular.z
    
        elif self.state == 'WP':
            cmd = self.latest_cmds.get('/cmd_vel/waypoint')
            if cmd is None:
                self.get_logger().warn(
                    'WP state but no waypoint command received, outputting zero.',
                    throttle_duration_sec=1.0
                )
                return 0.0, 0.0
            return cmd.linear.x, cmd.angular.z

        elif self.state == 'SEARCH':
            cmd = self.latest_cmds.get('/cmd_vel/pothole')
            if cmd is None:
                self.get_logger().warn(
                    'SEARCH state but no pothole command received, outputting zero.',
                    throttle_duration_sec=1.0
                )
                return 0.0, 0.0
            return cmd.linear.x, cmd.angular.z

        else:
        # IDLE / DONE / no message yet → zero
            return 0.0, 0.0

    # Kinematics
    def compute_wheel_speeds(self, v, w):
        half_L = self.wheelbase / 2.0
 
        v_left  = (v - w * half_L) / self.wheel_radius
        v_right = (v + w * half_L) / self.wheel_radius
 
        v_left  = max(-self.max_wheel_speed, min(self.max_wheel_speed, v_left))
        v_right = max(-self.max_wheel_speed, min(self.max_wheel_speed, v_right))
 
        return v_left, v_right

    # Publish Loop
    def publish_speed(self):
        v, w = self.get_active_command()
        v_left, v_right = self.compute_wheel_speeds(v, w)
 
        speed_msg = Speed()
        speed_msg.left  = float(v_left)   
        speed_msg.right = float(v_right)
        self.speed_pub.publish(speed_msg)
 
        self.get_logger().info(
            f'[{self.state}] v={v:.2f} w={w:.2f} → '
            f'vL={v_left:.2f} vR={v_right:.2f} rad/s',
        )
        

    # Safe Shutdown
    def stop_robot(self):
        stop_msg = Speed()
        stop_msg.left = 0.0
        stop_msg.right = 0.0
        self.speed_pub.publish(stop_msg)
        self.get_logger().info('Robot stopped safely')

def main(args=None):
    rclpy.init(args=args)
    node = CmdMuxNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        node.get_logger().info('Keyboard Interrupt')

    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
