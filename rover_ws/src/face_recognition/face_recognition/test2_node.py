#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point
from cv_bridge import CvBridge
from std_srvs.srv import SetBool
import cv2
import sys
import time


OFFSET_THRESHOLD = 20.0   # % — treat as "centered" when both axes are within this range
SESSION_DURATION = 45.0  # seconds


class FaceTrackingSession(Node):

    def __init__(self):
        super().__init__('face_tracking_session')
        self.bridge = CvBridge()

        self.latest_frame = None
        self.latest_result = None
        self.is_running = False
        self.session_start_time = None
        self.offset_x = None
        self.offset_y = None

        # ── Camera subscriber ──────────────────────────────────────────────
        self.camera_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.camera_callback,
            10
        )

        # ── Face recognition result subscriber ────────────────────────────
        self.result_sub = self.create_subscription(
            Image,
            '/face_recognition/result_image',
            self.result_callback,
            10
        )

        # ── Offset subscriber ─────────────────────────────────────────────
        self.offset_sub = self.create_subscription(
            Point,
            '/face_recognition/offset',
            self.offset_callback,
            10
        )

        # ── Face recognition service client ───────────────────────────────
        self.control_client = self.create_client(SetBool, '/face_recognition/start')

        # ── Display + session-check timer (30 Hz) ─────────────────────────
        self.display_timer = self.create_timer(1 / 30, self.display_callback)

        print("[SESSION] Node ready — press S to start a 45-second session, ESC to quit", flush=True, file=sys.stdout)

    # ── Service helpers ────────────────────────────────────────────────────

    def call_control_service(self, state: bool, reason: str = ""):
        if not self.control_client.service_is_ready():
            print("[SESSION] Face recognition service not available", flush=True, file=sys.stdout)
            return

        request = SetBool.Request()
        request.data = state
        future = self.control_client.call_async(request)
        future.add_done_callback(
            lambda f: self._control_response_callback(f, reason)
        )

    def _control_response_callback(self, future, reason: str):
        try:
            response = future.result()
            tag = f" ({reason})" if reason else ""
            print(f"[SESSION] Service response{tag}: {response.message}", flush=True, file=sys.stdout)
        except Exception as e:
            print(f"[SESSION] Service call failed: {e}", flush=True, file=sys.stdout)

    def start_session(self):
        self.is_running = True
        self.session_start_time = time.time()
        self.offset_x = None
        self.offset_y = None
        self.latest_result = None
        self.call_control_service(True, "session started")
        print(f"[SESSION] Started — {SESSION_DURATION:.0f}s countdown begins now", flush=True, file=sys.stdout)

    def stop_session(self, reason: str):
        if not self.is_running:
            return
        self.is_running = False
        self.session_start_time = None
        self.latest_result = None
        self.call_control_service(False, reason)
        print(f"[SESSION] Stopped — reason: {reason}", flush=True, file=sys.stdout)

    # ── Subscriber callbacks ───────────────────────────────────────────────

    def camera_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def result_callback(self, msg):
        if not self.is_running:
            return
        self.latest_result = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def offset_callback(self, msg):
        if not self.is_running:
            return

        self.offset_x = msg.x
        self.offset_y = msg.y

        print(
            f"[SESSION] offset_x: {msg.x:.2f}% | offset_y: {msg.y:.2f}%",
            flush=True, file=sys.stdout
        )

        # Stop if face is centered within threshold on both axes
        if abs(self.offset_x) <= OFFSET_THRESHOLD and abs(self.offset_y) <= OFFSET_THRESHOLD:
            print("[SESSION] Face centered — stopping session", flush=True, file=sys.stdout)
            self.stop_session("face centered (offset ≈ 0)")

    # ── Main loop (display + countdown check) ─────────────────────────────

    def display_callback(self):
        # ── Check 45-second timeout ───────────────────────────────────────
        if self.is_running and self.session_start_time is not None:
            elapsed = time.time() - self.session_start_time
            remaining = SESSION_DURATION - elapsed

            if remaining <= 0:
                self.stop_session("45-second timer expired")
            else:
                # Overlay countdown on display frame
                self._draw_countdown(remaining)

        # ── Display ───────────────────────────────────────────────────────
        if self.latest_frame is None:
            return

        display = self.latest_result if self.latest_result is not None else self.latest_frame
        cv2.imshow("Face Tracking Session", display)

        key = cv2.waitKey(1)
        if key == ord('s') and not self.is_running:
            self.start_session()
        elif key == 27:  # ESC
            print("[SESSION] ESC pressed — shutting down", flush=True, file=sys.stdout)
            self.stop_session("user quit")
            cv2.destroyAllWindows()
            rclpy.shutdown()

    def _draw_countdown(self, remaining: float):
        """Overlay a countdown timer on the result/raw frame in place."""
        target = self.latest_result if self.latest_result is not None else self.latest_frame
        if target is None:
            return

        label = f"Time: {remaining:.1f}s"
        color = (0, 255, 0) if remaining > 10 else (0, 0, 255)  # red when < 10s

        cv2.putText(
            target,
            label,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2
        )

    # ── Cleanup ───────────────────────────────────────────────────────────

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = FaceTrackingSession()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()