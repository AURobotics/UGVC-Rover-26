import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import String


class JoystickControls(Node):

    def __init__(self):
        super().__init__('joystick_controls')

        self.enabled = True

        self.fwd = 0.0
        self.steer = 0.0
        self.laser_x = 0.0
        self.laser_y = 0.0

        self.publisher = self.create_publisher(String,'cmd_vel',10)

        self.joy_subscriber = self.create_subscription(Joy,'joy',self.joy_callback,10)

        self.timer = self.create_timer(0.1,self.publish_cmd_vel)

    def joy_callback(self, msg):
        """
        axes[0] -> left analog (left/right)
        axes[1] -> left analog (up/down)
        axes[2] -> laser (left/right)
        axes[3] -> laser (up/down)
        """

        if len(msg.axes) >= 4:
            self.steer = float(msg.axes[0])
            self.fwd = float(msg.axes[1])
            self.laser_x = float(msg.axes[2])
            self.laser_y = float(msg.axes[3])

    def publish_cmd_vel(self):

        if not self.enabled:
            return

        data = {
            "fwd": self.fwd,
            "steer": self.steer,
            "laser_x": self.laser_x,
            "laser_y": self.laser_y
        }
        msg = String()
        msg.data = json.dumps(data)
        
        self.publisher.publish(msg)