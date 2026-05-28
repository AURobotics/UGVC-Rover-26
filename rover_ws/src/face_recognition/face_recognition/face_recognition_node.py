#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Int32
from cv_bridge import CvBridge
import sys

from .cv_code.face_recognition import FaceRecognition


class FaceRecognitionNode(Node):    

    def __init__(self):
        super().__init__('face_recognition_node')
        self.bridge = CvBridge()
        self.face_recognition = FaceRecognition()

        # Publishers
        self.is_faces_pub = self.create_publisher(Bool, '/face_recognition/is_faces', 10)
        self.is_detected_pub = self.create_publisher(Bool, '/face_recognition/is_detected', 10)
        self.offset_pub = self.create_publisher(Int32, '/face_recognition/offset', 10)
        self.result_pub = self.create_publisher(Image, '/face_recognition/result_image', 10)

        # Subscriber
        self.sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        self.get_logger().info("Face recognition node started")

    def image_callback(self, msg):
        self.get_logger().info('image_callback triggered')
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        result, is_faces, is_detected, offset = self.face_recognition.recognize_frame(frame)
        # Publish result image
        result_msg = self.bridge.cv2_to_imgmsg(result, 'bgr8')
        result_msg.header.stamp = self.get_clock().now().to_msg()
        result_msg.header.frame_id = 'camera_frame'
        self.result_pub.publish(result_msg)
        # Publish outputs
        self.is_faces_pub.publish(Bool(data=bool(is_faces)))
        self.is_detected_pub.publish(Bool(data=bool(is_detected)))
        if offset is not None:
            self.offset_pub.publish(Int32(data=int(offset)))
            print(f"[FACE_RECOGNITION_NODE] Published offset (int): {int(offset)}", flush=True, file=sys.stdout)
        else:
            print("[FACE_RECOGNITION_NODE] Offset is None, not publishing", flush=True, file=sys.stdout)
        # Log
        self.get_logger().info(
            f'is_faces: {is_faces} | is_detected: {is_detected} | offset: {offset}'
        )

def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()