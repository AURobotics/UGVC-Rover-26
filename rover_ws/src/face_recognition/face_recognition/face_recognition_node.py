#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

from .cv_code.face_recognition import FaceRecognition


class FaceRecognitionNode(Node):

    def __init__(self):
        super().__init__('face_recognition')
        self.bridge = CvBridge()
        self.face_recognition = FaceRecognition()
        cv2.startWindowThread()

        self.sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        result = self.face_recognition.recognize_frame(frame)
        cv2.imshow("Face Recognition", result)
        if cv2.waitKey(1) == 27:  # 27 is ESC
            cv2.destroyAllWindows()
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()