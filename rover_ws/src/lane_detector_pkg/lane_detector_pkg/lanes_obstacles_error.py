import cv2
import rclpy 
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Float32,Bool
from std_srvs.srv import SetBool
import os 
import sys
import numpy as np
from ultralytics import YOLO 
from ament_index_python.packages import get_package_share_directory
from lane_detector_pkg.lane_classic import RoadFeatureDetector
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy


Camera_topic = "camera/image/raw" #SUBSCRIBE
Lane_error_topic = "lane/error" #PUBLISHER
obstacle_error_topic = "obstacle/error" #PUBLISHER
obstacle_detected_topic = "obstacle/detected" #PUBLISHER
circle_error_topic = "circle/error" #PUBLISHER
circle_detected_topic = "circle/detected" #PUBLISHER
total_error_topic = "total/error" #PUBLISHER
start_service_topic = "/obstacle_detector/start" #SERVICE


class ObstacleDetector(Node):
    """
    ROS2-only responsibilities live here: subscriptions, publishers, the
    start/stop service, and the camera callback that wires them together.
    All computer-vision / geometry logic (edge detection, Hough lines,
    Hough circles, homography, offsets in meters) lives in
    RoadFeatureDetector (road_features_detector.py / lane_classic.py) and
    is only *called* from this file.
    """

    def __init__(self):
        super().__init__('obstacle_detector')

        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.bridge = CvBridge()
        self.is_running = False

        # camera / homography calibration
        self.K = np.array([
            [1000, 0, 960],
            [0, 1000, 540],
            [0, 0, 1]
        ], dtype=np.float64)
        self.camera_height = 1.2
        self.pitch_deg = -30
        self.yaw_deg = 0
        self.roll_deg = 0
        self.lane_detector = None  # RoadFeatureDetector, created on first frame

        # smoothing state
        self.prev_left_x = None
        self.prev_right_x = None
        self.prev_lane_error = 0.0
        self.prev_circle_error = 0.0

        # YOLO obstacle model
        package_share_dir = get_package_share_directory('lane_detector_pkg')
        model_path_obstacle = os.path.join(package_share_dir, 'models', 'ModelForObstacle.pt')
        self.model_obstacle = YOLO(model_path_obstacle)

        # subscriber
        self.camera_subscriber = self.create_subscription(
            Image,
            Camera_topic,
            self.camera_callback,
            qos_profile
        )

        # publishers
        self.lane_error_publisher = self.create_publisher(Float32, Lane_error_topic, qos_profile)
        self.obstacle_error_publisher = self.create_publisher(Float32, obstacle_error_topic, qos_profile)
        self.obstacle_detected_publisher = self.create_publisher(Bool, obstacle_detected_topic, qos_profile)
        self.circle_error_publisher = self.create_publisher(Float32, circle_error_topic, qos_profile)
        self.circle_detected_publisher = self.create_publisher(Bool, circle_detected_topic, qos_profile)
        self.total_error_publisher = self.create_publisher(Float32, total_error_topic, qos_profile)

        # start/stop service
        self.control_srv = self.create_service(
            SetBool,
            start_service_topic,
            self.control_callback
        )

        print("[OBSTACLE_DETECTOR] Node started — call /obstacle_detector/start to start", flush=True, file=sys.stdout)

    # ------------------------------------------------------------------
    # SERVICE
    # ------------------------------------------------------------------
    def control_callback(self, request, response):
        self.is_running = request.data
        state = "started" if self.is_running else "stopped"
        response.success = True
        response.message = f"Obstacle detector {state}"
        print(f"[OBSTACLE_DETECTOR] {response.message}", flush=True, file=sys.stdout)
        return response

    # ------------------------------------------------------------------
    # MAIN CAMERA CALLBACK — orchestrates lane + circle + obstacle
    # ------------------------------------------------------------------
    def camera_callback(self, msg):
        if not self.is_running:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed To Convert Image as {e}')
            return

        if self.lane_detector is None:
            height, width = frame.shape[:2]
            self.lane_detector = RoadFeatureDetector(
                K=self.K,
                camera_height=self.camera_height,
                pitch_deg=self.pitch_deg,
                yaw_deg=self.yaw_deg,
                roll_deg=self.roll_deg,
                image_size=(width, height)
            )

        # ---------- lane offset (meters, relative to frame center) ----------
        x_left_px, x_right_px, look_ahead_y = self.get_lane_data(frame)

        if x_left_px is not None:
            self.prev_left_x = x_left_px
        else:
            x_left_px = self.prev_left_x

        if x_right_px is not None:
            self.prev_right_x = x_right_px
        else:
            x_right_px = self.prev_right_x

        X_frame_center, _ = self.lane_detector.bev.pixel_to_ground(frame.shape[1] / 2.0, look_ahead_y)

        if x_left_px is not None and x_right_px is not None:
            X_left, _ = self.lane_detector.bev.pixel_to_ground(x_left_px, look_ahead_y)
            X_right, _ = self.lane_detector.bev.pixel_to_ground(x_right_px, look_ahead_y)
            lane_center_m = (X_left + X_right) / 2.0
            lane_error = lane_center_m - X_frame_center
            self.prev_lane_error = lane_error
        else:
            lane_error = self.prev_lane_error

        self.publish_float(self.lane_error_publisher, lane_error)

        # ---------- circle (hole) offset — delegated to RoadFeatureDetector ----------
        circle_error, frame = self.lane_detector.offsetx_circle(frame)
        self.prev_circle_error = circle_error

        edges, white_mask = self.lane_detector.detect_edges(frame)
        circles = self.lane_detector.detect_circles(frame, white_mask)
        self.publish_bool(self.circle_detected_publisher, len(circles) > 0)
        self.publish_float(self.circle_error_publisher, circle_error)

        # ---------- obstacle offset (YOLO-based) ----------
        obstacle_error = self.detect_obstacles(frame, x_left_px, x_right_px, look_ahead_y)

        # ---------- combined total ----------
        total_error = lane_error + circle_error + obstacle_error
        self.publish_float(self.total_error_publisher, total_error)

    # ------------------------------------------------------------------
    # LANE HELPER (thin wrapper around RoadFeatureDetector)
    # ------------------------------------------------------------------
    def get_lane_data(self, frame):
        edges, _ = self.lane_detector.detect_edges(frame)
        lines = self.lane_detector.detect_lines(edges)
        left_fit, right_fit = self.lane_detector._fit_left_right_lanes(lines)
        look_ahead_y = int(frame.shape[0] * 0.7)

        x_left = None
        x_right = None
        if left_fit is not None:
            m_left, b_left = left_fit
            x_left = m_left * look_ahead_y + b_left
        if right_fit is not None:
            m_right, b_right = right_fit
            x_right = m_right * look_ahead_y + b_right

        return x_left, x_right, look_ahead_y

    # ------------------------------------------------------------------
    # OBSTACLE HELPER (YOLO detection + gap math, uses RoadFeatureDetector.bev)
    # ------------------------------------------------------------------
    def detect_obstacles(self, frame, x_left, x_right, y_eval):
        results_obstacles = self.model_obstacle(frame, conf=0.3)[0]
        obstacles = []

        for box in results_obstacles.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            if confidence < 0.3:
                continue
            bottom_x = (x1 + x2) // 2
            obstacles.append({"x1": x1, "x2": x2, "y2": y2, "bottom_x": bottom_x, "conf": confidence})

        if x_left is None or x_right is None:
            self.publish_bool(self.obstacle_detected_publisher, False)
            self.publish_float(self.obstacle_error_publisher, 0.0)
            return 0.0

        X_left, _ = self.lane_detector.bev.pixel_to_ground(x_left, y_eval)
        X_right, _ = self.lane_detector.bev.pixel_to_ground(x_right, y_eval)
        X_frame_center, _ = self.lane_detector.bev.pixel_to_ground(frame.shape[1] / 2.0, y_eval)

        lane_obstacles = [o for o in obstacles if x_left <= o["bottom_x"] <= x_right]
        lane_obstacles.sort(key=lambda o: o["x1"])

        self.publish_bool(self.obstacle_detected_publisher, len(lane_obstacles) > 0)

        if not lane_obstacles:
            self.publish_float(self.obstacle_error_publisher, 0.0)
            return 0.0

        ground_edges = []
        for o in lane_obstacles:
            Xg1, _ = self.lane_detector.bev.pixel_to_ground(o["x1"], o["y2"])
            Xg2, _ = self.lane_detector.bev.pixel_to_ground(o["x2"], o["y2"])
            ground_edges.append({"start": min(Xg1, Xg2), "end": max(Xg1, Xg2)})

        gaps = [{"start": X_left, "end": ground_edges[0]["start"]}]
        for i in range(len(ground_edges) - 1):
            gaps.append({"start": ground_edges[i]["end"], "end": ground_edges[i + 1]["start"]})
        gaps.append({"start": ground_edges[-1]["end"], "end": X_right})

        for gap in gaps:
            gap["width"] = gap["end"] - gap["start"]

        best_gap = max(gaps, key=lambda g: g["width"])
        target_center = (best_gap["start"] + best_gap["end"]) / 2.0
        obstacle_error = target_center - X_frame_center

        self.publish_float(self.obstacle_error_publisher, obstacle_error)
        return obstacle_error

    # ------------------------------------------------------------------
    # SMALL PUBLISH HELPERS
    # ------------------------------------------------------------------
    def publish_float(self, publisher, value):
        msg = Float32()
        msg.data = float(value)
        publisher.publish(msg)

    def publish_bool(self, publisher, value):
        msg = Bool()
        msg.data = bool(value)
        publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()