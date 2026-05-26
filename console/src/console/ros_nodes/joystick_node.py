#! /usr/bin/env python3
import rclpy
from rclpy.node import Node

class JoystickNode(Node):
    def __init__(self):
        super().__init__("joystick_node")
        self.get_logger().info("Joystick node started ")
        ...