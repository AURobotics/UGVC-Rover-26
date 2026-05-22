#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy
)

from geometry_msgs.msg import Twist
from std_msgs.msg import String
from ugvc_msgs.msg import Speed

# QoS Profiles
BEST_EFFORT = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1
)

RELIABLE = QoSProfile(
    reliability=QoSReliabilityPolicy.RELIABLE,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1
)

# Mission State Mapping
STATE_MAP = {
    'IDLE': None,
    'LANE': '/cmd_vel/lane_pid',
    'WP': '/cmd_vel/waypoint',
    'SEARCH': '/cmd_vel/pothole',
    'DONE': None,
    'MANUAL': '/cmd_vel/teleop',
}

class CmdMuxNode(Node):

    def __init__(self):
        super().__init__('cmd_mux_node')

        # Parameters
        self.declare_parameter('wheel_radius', 0.10)       # meters
        self.declare_parameter('wheelbase', 0.50)          # meters
        self.declare_parameter('max_wheel_speed', 10.0)    # rad/s
        self.declare_parameter('publish_rate', 50.0)       # Hz
        self.declare_parameter('cmd_timeout', 0.5)         # seconds

        self.wheel_radius = float(
            self.get_parameter('wheel_radius').value
        )

        self.wheelbase = float(
            self.get_parameter('wheelbase').value
        )

        self.max_wheel_speed = float(
            self.get_parameter('max_wheel_speed').value
        )

        self.publish_rate = float(
            self.get_parameter('publish_rate').value
        )

        self.cmd_timeout = float(
            self.get_parameter('cmd_timeout').value
        )

        # Internal Variables
        self.state = 'IDLE'

        self.latest_cmds = {
            topic: None
            for topic in STATE_MAP.values()
            if topic is not None
        }

        self.latest_times = {
            topic: None
            for topic in STATE_MAP.values()
            if topic is not None
        }

        self.tick_counter = 0
        self._timeout_warned = False

        # Publisher
        self.speed_pub = self.create_publisher(
            Speed,
            '/cmd_speed',
            RELIABLE
        )

        # Subscribers
        for topic in self.latest_cmds.keys():

            self.create_subscription(
                Twist,
                topic,
                self.create_twist_callback(topic),
                BEST_EFFORT
            )

        self.create_subscription(
            String,
            '/mission/active_state',
            self.state_callback,
            RELIABLE
        )

        # Main Timer
        self.create_timer(
            1.0 / self.publish_rate,
            self.publish_speed
        )

        self.get_logger().info('Cmd Mux Node Started with Teleop Override')

    # Twist Callback
    def create_twist_callback(self, topic):

        def callback(msg):

            self.latest_cmds[topic] = msg

            self.latest_times[topic] = (
                self.get_clock().now()
            )

        return callback

    # Mission State Callback
    def state_callback(self, msg):

        new_state = msg.data.strip()

        if new_state not in STATE_MAP:
            self.get_logger().warn(
                f'Unknown mission state: {new_state}'
            )
            return

        if new_state != self.state:
            self.get_logger().info(
                f'State changed: {self.state} -> {new_state}'
            )

        self.state = new_state

    # Check Command Timeout
    def is_cmd_valid(self, topic):

        if self.latest_cmds[topic] is None:
            return False

        if self.latest_times[topic] is None:
            return False

        now = self.get_clock().now()

        age = (
            now - self.latest_times[topic]
        ).nanoseconds / 1e9

        return age <= self.cmd_timeout

    # Clamp Function
    def clamp(self, value):
        return max(
            -self.max_wheel_speed,
            min(self.max_wheel_speed, value)
        )

    # Publish Loop
    def publish_speed(self):
        # Safe default
        linear_v = 0.0
        angular_w = 0.0
        source = 'ZERO'

        # TELEOP OVERRIDE (Highest Priority)
        teleop_topic = '/cmd_vel/teleop'
        
        if self.is_cmd_valid(teleop_topic):
            # Teleop overrides EVERYTHING
            teleop_msg = self.latest_cmds[teleop_topic]
            linear_v = float(teleop_msg.linear.x)
            angular_w = float(teleop_msg.angular.z)
            source = 'TELEOP_OVERRIDE'
            
        else:
            # Normal State-Based Selection
            active_topic = STATE_MAP.get(self.state)

            if active_topic is not None:
                if self.is_cmd_valid(active_topic):
                    cmd_msg = self.latest_cmds[active_topic]
                    linear_v = float(cmd_msg.linear.x)
                    angular_w = float(cmd_msg.angular.z)
                    source = active_topic
                    
                else:
                    # Timeout warning (once per timeout event)
                    if not self._timeout_warned:
                        self.get_logger().warn(
                            f'Command timeout on {active_topic}, '
                            f'no valid command for {self.cmd_timeout}s'
                        )
                        self._timeout_warned = True
            else:
                # IDLE or DONE state
                source = self.state

        # Reset timeout warning flag if we got a valid command
        if source !='ZERO':
            self._timeout_warned = False

        # Differential Drive Kinematics
        v_left = (
            linear_v -
            (angular_w * self.wheelbase / 2.0)
        ) / self.wheel_radius

        v_right = (
            linear_v +
            (angular_w * self.wheelbase / 2.0)
        ) / self.wheel_radius

        # Clamp wheel speeds
        v_left = self.clamp(v_left)
        v_right = self.clamp(v_right)

        # Publish Output
        speed_msg = Speed()
        speed_msg.vL = float(v_left)
        speed_msg.vR = float(v_right)
        self.speed_pub.publish(speed_msg)

        # Debug Logging
        self.tick_counter += 1
        if self.tick_counter >= int(self.publish_rate):
            self.tick_counter = 0
            self.get_logger().info(
                f'[{self.state}] src={source} | '
                f'vL={v_left:.2f} rad/s | '
                f'vR={v_right:.2f} rad/s'
            )

    # Safe Shutdown
    def stop_robot(self):
        stop_msg = Speed()
        stop_msg.vL = 0.0
        stop_msg.vR = 0.0
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
