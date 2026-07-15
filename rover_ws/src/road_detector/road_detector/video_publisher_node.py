#!/usr/bin/env python3
"""
video_publisher_node.py
------------------------
ROS2 node that reads a video file and publishes each frame as a
sensor_msgs/Image on /camera/image_raw — the exact topic that
road_detector.py subscribes to by default.

Usage
-----
Run directly (after sourcing your ROS2 workspace):

    python3 video_publisher_node.py --ros-args \
        -p video_path:=/abs/path/to/video.mp4 \
        -p publish_rate:=30.0 \
        -p loop:=true \
        -p frame_id:=camera

Parameters
----------
video_path        (str)   - Absolute path to the video file.  REQUIRED.
publish_rate      (float) - Publish frequency in Hz.  Default: 30.0
loop              (bool)  - Loop the video when it ends.  Default: False
image_topic       (str)   - Topic to publish on.  Default: /camera/image_raw
frame_id          (str)   - frame_id in the image header.  Default: camera
start_frame       (int)   - Frame index to start from.  Default: 0
"""

import sys
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)

from sensor_msgs.msg import Image
from std_msgs.msg import Header

import cv2
from cv_bridge import CvBridge


class VideoPublisherNode(Node):
    """Publishes video frames as ROS2 Image messages."""

    def __init__(self):
        super().__init__("video_publisher")

        # ── Declare parameters ────────────────────────────────────────────────
        self.declare_parameter("video_path", "")
        self.declare_parameter("publish_rate", 30.0)
        self.declare_parameter("loop", False)
        self.declare_parameter("image_topic", "/camera/image_raw")
        self.declare_parameter("frame_id", "camera")
        self.declare_parameter("start_frame", 0)

        # ── Load parameters ───────────────────────────────────────────────────
        self.video_path = self.get_parameter("video_path").value
        self.publish_rate = self.get_parameter("publish_rate").value
        self.loop = self.get_parameter("loop").value
        self.image_topic = self.get_parameter("image_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        self.start_frame = self.get_parameter("start_frame").value

        # ── Validate ──────────────────────────────────────────────────────────
        if not self.video_path:
            self.get_logger().fatal(
                "Parameter 'video_path' is empty.  "
                "Pass it with: --ros-args -p video_path:=/path/to/video.mp4"
            )
            raise RuntimeError("video_path parameter is required")

        # ── Open video ────────────────────────────────────────────────────────
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            self.get_logger().fatal(f"Cannot open video file: {self.video_path}")
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        # Seek to start frame if requested
        if self.start_frame > 0:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        native_fps = self.cap.get(cv2.CAP_PROP_FPS)
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.get_logger().info(
            f"Opened: {self.video_path}\n"
            f"  Resolution : {width}x{height}\n"
            f"  Native FPS : {native_fps:.2f}\n"
            f"  Total frames: {total_frames}\n"
            f"  Publish rate: {self.publish_rate} Hz\n"
            f"  Loop        : {self.loop}\n"
            f"  Topic       : {self.image_topic}"
        )

        # ── cv_bridge ─────────────────────────────────────────────────────────
        self.bridge = CvBridge()

        # ── Publisher ─────────────────────────────────────────────────────────
        # Use BEST_EFFORT + VOLATILE to match road_detector's subscriber QoS
        image_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.publisher = self.create_publisher(Image, self.image_topic, image_qos)

        # ── Timer ─────────────────────────────────────────────────────────────
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self._timer_callback)

        self.frame_index = self.start_frame
        self.get_logger().info("VideoPublisherNode ready — starting to stream.")

    # ── Timer callback ────────────────────────────────────────────────────────
    def _timer_callback(self):
        ret, frame = self.cap.read()

        if not ret:
            if self.loop:
                self.get_logger().info("End of video — looping back to start.")
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.frame_index = 0
                ret, frame = self.cap.read()
                if not ret:
                    self.get_logger().error("Failed to read frame after loop reset.")
                    return
            else:
                self.get_logger().info("End of video — shutting down publisher.")
                self.timer.cancel()
                self.cap.release()
                rclpy.shutdown()
                return

        # Build ROS Image message
        try:
            img_msg: Image = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"cv_bridge conversion error: {e}")
            return

        img_msg.header = Header()
        img_msg.header.stamp = self.get_clock().now().to_msg()
        img_msg.header.frame_id = self.frame_id

        self.publisher.publish(img_msg)
        self.frame_index += 1

        if self.frame_index % 100 == 0:
            self.get_logger().info(f"Published frame {self.frame_index}")

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


# ── Entry point ────────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)

    try:
        node = VideoPublisherNode()
    except RuntimeError as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrupted by user.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
