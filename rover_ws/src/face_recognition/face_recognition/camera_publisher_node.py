#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Int32
from cv_bridge import CvBridge
import cv2
import sys


class CameraPublisher(Node):

    def __init__(self):
        super().__init__('camera_publisher')
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open camera")
            raise RuntimeError("Camera not available")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Publish camera frames
        self.timer = self.create_timer(1/30, self.timer_callback)

        # Subscribe to face recognition outputs
        self.result_sub = self.create_subscription(
            Image,
            '/face_recognition/result_image',
            self.result_callback,
            10
        )
        self.is_faces_sub = self.create_subscription(
            Bool,
            '/face_recognition/is_faces',
            self.is_faces_callback,
            10
        )
        self.is_detected_sub = self.create_subscription(
            Bool,
            '/face_recognition/is_detected',
            self.is_detected_callback,
            10
        )
        self.offset_sub = self.create_subscription(
            Int32,
            '/face_recognition/offset',
            self.offset_callback,
            10
        )

        self.latest_result = None
        self.display_timer = self.create_timer(1/30, self.display_callback)

        self.get_logger().info("Camera publisher started")
        print("[CAMERA_PUBLISHER] Node initialized successfully", flush=True, file=sys.stdout)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Failed to read frame")
            return

        msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'
        self.pub.publish(msg)

    def result_callback(self, msg):
        self.latest_result = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def is_faces_callback(self, msg):
        print(f"[CAMERA_PUBLISHER] is_faces: {msg.data}", flush=True, file=sys.stdout)

    def is_detected_callback(self, msg):
        print(f"[CAMERA_PUBLISHER] is_detected: {msg.data}", flush=True, file=sys.stdout)

    def offset_callback(self, msg):
        print(f"[CAMERA_PUBLISHER] offset: {msg.data}", flush=True, file=sys.stdout)

    def display_callback(self):
        if self.latest_result is None:
            return
        cv2.imshow("Face Recognition Result", self.latest_result)
        if cv2.waitKey(1) == 27:  # ESC to quit
            cv2.destroyAllWindows()
            rclpy.shutdown()

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()