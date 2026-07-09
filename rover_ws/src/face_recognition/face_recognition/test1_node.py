#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge
from std_srvs.srv import SetBool
import cv2
import sys


class CameraPublisher(Node):

    def __init__(self):
        super().__init__('camera_publisher')
        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[CAMERA_PUBLISHER] Failed to open camera", flush=True, file=sys.stdout)
            raise RuntimeError("Camera not available")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Publish camera frames
        self.timer = self.create_timer(1/30, self.timer_callback)

        # Service client
        self.control_client = self.create_client(SetBool, '/face_recognition/start')

        # Subscribers
        self.result_sub = self.create_subscription(
            Image,
            '/face_recognition/result_image',
            self.result_callback,
            10
        )

        self.offset_sub = self.create_subscription(
            Point,
            '/face_recognition/offset',
            self.offset_callback,
            10
        )

        self.latest_result = None
        self.latest_frame = None
        self.is_running = False
        self.display_timer = self.create_timer(1/30, self.display_callback)

        print("[CAMERA_PUBLISHER] Node initialized — press S to start, X to stop, ESC to quit", flush=True, file=sys.stdout)

    def call_control_service(self, state: bool):
        if not self.control_client.service_is_ready():
            print("[CAMERA_PUBLISHER] Face recognition service not available", flush=True, file=sys.stdout)
            return
        request = SetBool.Request()
        request.data = state
        self.is_running = state
        if not state:
            self.latest_result = None
        future = self.control_client.call_async(request)
        future.add_done_callback(self.control_response_callback)

    def control_response_callback(self, future):
        try:
            response = future.result()
            print(f"[CAMERA_PUBLISHER] Service response: {response.message}", flush=True, file=sys.stdout)
        except Exception as e:
            print(f"[CAMERA_PUBLISHER] Service call failed: {e}", flush=True, file=sys.stdout)

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            print("[CAMERA_PUBLISHER] Failed to read frame", flush=True, file=sys.stdout)
            return

        self.latest_frame = frame

        msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'
        self.pub.publish(msg)

    def result_callback(self, msg):
        if not self.is_running:
            return
        self.latest_result = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def offset_callback(self, msg):
        print(f"[CAMERA_PUBLISHER] offset_x: {msg.x:.2f}% | offset_y: {msg.y:.2f}%", flush=True, file=sys.stdout)

    def display_callback(self):
        if self.latest_frame is None:
            return

        display = self.latest_result if self.latest_result is not None else self.latest_frame
        cv2.imshow("Face Recognition", display)

        key = cv2.waitKey(1)
        if key == ord('s'):
            print("[CAMERA_PUBLISHER] Starting face recognition...", flush=True, file=sys.stdout)
            self.call_control_service(True)
        elif key == ord('x'):
            print("[CAMERA_PUBLISHER] Stopping face recognition...", flush=True, file=sys.stdout)
            self.call_control_service(False)
            self.latest_result = None
        elif key == 27:
            print("[CAMERA_PUBLISHER] ESC pressed, shutting down...", flush=True, file=sys.stdout)
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