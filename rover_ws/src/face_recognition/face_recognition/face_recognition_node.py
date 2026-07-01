#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge
from std_srvs.srv import SetBool
import sys

from .cv_code.face_recognition_cv import FaceRecognition

CAMERA_TOPIC = '/camera/image_raw'
FACE_RECOGNITION_START_SERVICE = '/face_recognition/start'
FACE_RECOGNITION_OFFSET_TOPIC = '/face_recognition/offset'
FACE_RECOGNITION_RESULT_IMAGE_TOPIC = '/face_recognition/result_image'

class FaceRecognitionNode(Node):    

    def __init__(self):
        super().__init__('face_recognition_node')
        self.bridge = CvBridge()
        self.face_recognition = FaceRecognition()
        self.is_running = False

        # Publishers
        self.offset_pub = self.create_publisher(Point, FACE_RECOGNITION_OFFSET_TOPIC, 10)
        self.result_pub = self.create_publisher(Image, FACE_RECOGNITION_RESULT_IMAGE_TOPIC, 10)

        # Service
        self.control_srv = self.create_service(
            SetBool,
            FACE_RECOGNITION_START_SERVICE,
            self.control_callback
        )

        # Subscriber
        self.sub = self.create_subscription(
            Image,
            CAMERA_TOPIC,
            self.image_callback,
            10
        )

        print("[FACE_RECOGNITION_NODE] Node started — call " + FACE_RECOGNITION_START_SERVICE + " to start", flush=True, file=sys.stdout)

    def control_callback(self, request, response):
        self.is_running = request.data
        state = "started" if self.is_running else "stopped"
        response.success = True
        response.message = f"Face recognition {state}"
        print(f"[FACE_RECOGNITION_NODE] {response.message}", flush=True, file=sys.stdout)
        return response

    def offset_publish(self, offset_x, offset_y):
        offset_msg = Point()
        offset_msg.x = float(offset_x)
        offset_msg.y = float(offset_y)
        offset_msg.z = 0.0
        self.offset_pub.publish(offset_msg)
        print(f"[FACE_RECOGNITION_NODE] Published offset: ({int(offset_x)}, {int(offset_y)})", flush=True, file=sys.stdout)

    def image_callback(self, msg):
        if not self.is_running:
            return

        print("[FACE_RECOGNITION_NODE] image_callback triggered", flush=True, file=sys.stdout)
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        result, is_faces, is_detected, offset_x, offset_y = self.face_recognition.recognize_frame(frame)

        # Publish result image
        result_msg = self.bridge.cv2_to_imgmsg(result, 'bgr8')
        result_msg.header.stamp = self.get_clock().now().to_msg()
        result_msg.header.frame_id = 'camera_frame'
        self.result_pub.publish(result_msg)

        # Publish offset_x and offset_y in a single Point message
        if is_faces is False:
            offset_x, offset_y = 0, 100
            self.offset_publish(offset_x, offset_y)

        elif is_detected is False:
            offset_x, offset_y = 100, 0
            self.offset_publish(offset_x, offset_y)    

        elif offset_x is not None and offset_y is not None:
            self.offset_publish(offset_x, offset_y)
        else:
            print("[FACE_RECOGNITION_NODE] offset is None, not publishing", flush=True, file=sys.stdout)

        print(f"[FACE_RECOGNITION_NODE] is_faces: {is_faces} | is_detected: {is_detected} | offset: ({offset_x}, {offset_y})", flush=True, file=sys.stdout)


def main(args=None):
    rclpy.init(args=args)
    node = FaceRecognitionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()