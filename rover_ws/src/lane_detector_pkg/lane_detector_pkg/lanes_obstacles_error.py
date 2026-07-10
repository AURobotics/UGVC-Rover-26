import cv2
import rclpy
from rclpy.node import Node
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, Bool
from std_srvs.srv import SetBool
import os
import sys
import numpy as np
from ultralytics import YOLO
from ament_index_python.packages import get_package_share_directory
from lane_detector_pkg.lane_classic import RoadFeatureDetector
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy


Camera_topic = "camera/image/raw"  # SUBSCRIBE
Lane_error_topic = "lane/error"  # PUBLISHER
obstacle_error_topic = "obstacle/error"  # PUBLISHER
obstacle_detected_topic = "obstacle/detected"  # PUBLISHER
circle_error_topic = "circle/error"  # PUBLISHER
circle_detected_topic = "circle/detected"  # PUBLISHER
total_error_topic = "total/error"  # PUBLISHER
start_service_topic = "/obstacle_detector/start"  # SERVICE

ROI_HEIGHT = 0.7 # fraction of image to evalute lane/circle/obstacle errors

class ObstacleDetector(Node):

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
            [793.79768697, 0, 290.78702859],
            [0, 813.96117996, 241.57106901],
            [0, 0, 1]
        ], dtype=np.float64)

        self.dist_coeffs = np.array([-4.97661814e-01, 8.05356640e+00, 9.44660547e-03, -2.64434172e-02, -4.33974203e+01], dtype=np.float64)

        self.camera_height = 1.2
        self.pitch_deg = -30
        self.yaw_deg = 0
        self.roll_deg = 0
        self.lane_detector = None  # RoadFeatureDetector, created on first frame

        #smothing state
        self.prev_left_x = None
        self.prev_right_x = None
        self.prev_lane_error = 0.0
        self.prev_circle_error = 0.0

        # YOLO obstacle model
        package_share_dir = get_package_share_directory('lane_detector_pkg')
        model_path_obstacle = os.path.join(package_share_dir, 'models', 'ModelForObstecale.pt')
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
        #if not self.is_running:
         #   return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed To Convert Image as {e}')
            return

        if frame is None or frame.size == 0:
            self.get_logger().warn('Received empty frame, skipping.')
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

        frame_width = frame.shape[1]
        #----------- YOLO Model ---------------#
        results = self.model_obstacle(frame,conf = 0.3)[0]
        
        # ---------- lane offset (current frame only, no memory) ----------
        edges, white_mask = self.lane_detector.detect_edges(frame)
        x_left_px, x_right_px, look_ahead_y = self.get_lane_data(frame, edges)

        # missing left  -> left edge of frame (x = 0)
        # missing right -> right edge of frame (x = frame_width)
        # missing both  -> both frame edges (full frame width treated as the lane)
        if x_left_px is None:
            x_left_px = 0.0
        if x_right_px is None:
            x_right_px = float(frame_width)

        X_frame_center, _ = self.lane_detector.bev.pixel_to_ground(frame_width / 2.0, look_ahead_y)
        X_left, _ = self.lane_detector.bev.pixel_to_ground(x_left_px, look_ahead_y)
        X_right, _ = self.lane_detector.bev.pixel_to_ground(x_right_px, look_ahead_y)
        
        obstacle_error = self.detect_obstacles(
            results,
            frame,
            x_left_px,
            x_right_px,
            look_ahead_y
        )

        lane_center_m = (X_left + X_right) / 2.0
        lane_error = lane_center_m - X_frame_center

        self.publish_float(self.lane_error_publisher, lane_error)

        # ---------- circle (hole) offset — reuses the SAME lane edges as ----------
        # ---------- lane_error / obstacle_error, computed once above     ----------
        circles = self.lane_detector.detect_circles(frame, white_mask)
        circle_error, frame = self.lane_detector.offsetx_circle(
            frame, circles, x_left_px, x_right_px, look_ahead_y
        )
        self.publish_bool(self.circle_detected_publisher, len(circles) > 0)
        self.publish_float(self.circle_error_publisher, circle_error)

        total_error = self.compute_navigation_error(frame,results, circles, x_left_px, x_right_px, look_ahead_y)

        self.publish_float(self.total_error_publisher, total_error)

    # ------------------------------------------------------------------
    # LANE HELPER (thin wrapper around RoadFeatureDetector)
    # ------------------------------------------------------------------
    def get_lane_data(self, frame, edges):
        lines = self.lane_detector.detect_lines(edges)
        left_fit, right_fit = self.lane_detector._fit_left_right_lanes(lines)
        look_ahead_y = int(frame.shape[0] * ROI_HEIGHT)

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
    def detect_obstacles(self,results,frame, x_left, x_right, y_eval):
        #try:
        #    results_obstacles = self.model_obstacle(frame, conf=0.3)[0]
        #except Exception as e:
        #    self.get_logger().error(f'YOLO obstacle inference failed: {e}')
        #    self.publish_bool(self.obstacle_detected_publisher, False)
        #    self.publish_float(self.obstacle_error_publisher, 0.0)
        #    return 0.0

        obstacles = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0])
            bottom_x = (x1 + x2) // 2
            obstacles.append({"x1": x1, "x2": x2, "y2": y2, "bottom_x": bottom_x, "conf": confidence})

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

    def compute_navigation_error(self,frame,results,circles,x_left_px,x_right_px,y_eval):

        occupied = []

        # =====================================================
        # YOLO obstacles
        # =====================================================

        lane_obstacles = []

        for box in results.boxes:

            x1, y1, x2, y2 = map(int,box.xyxy[0])

            bottom_x = (x1 + x2) // 2

            if x_left_px <= bottom_x <= x_right_px:

                lane_obstacles.append((x1, x2, y2))

        self.publish_bool(self.obstacle_detected_publisher,len(lane_obstacles) > 0)

        # =====================================================
        # Convert obstacles to occupied intervals
        # =====================================================

        for x1, x2, y2 in lane_obstacles:

            X1, _ = self.lane_detector.bev.pixel_to_ground(x1,y2)

            X2, _ = self.lane_detector.bev.pixel_to_ground(x2,y2)

            occupied.append({"start": min(X1, X2),"end": max(X1, X2)})

        # =====================================================
        # Convert circles to occupied intervals
        # =====================================================

        lane_circles = []

        for cx, cy, r in circles:

            if x_left_px <= cx <= x_right_px:

                lane_circles.append((cx, cy, r))

                X1, _ = self.lane_detector.bev.pixel_to_ground(cx - r,cy)

                X2, _ = self.lane_detector.bev.pixel_to_ground(cx + r,cy)

                occupied.append({"start": min(X1, X2),"end": max(X1, X2)})

        self.publish_bool(self.circle_detected_publisher,len(lane_circles) > 0)

        # =====================================================
        # lane boundaries
        # =====================================================

        X_left, _ = self.lane_detector.bev.pixel_to_ground(x_left_px,y_eval)

        X_right, _ = self.lane_detector.bev.pixel_to_ground(x_right_px,y_eval)

        X_center, _ = self.lane_detector.bev.pixel_to_ground(frame.shape[1] / 2,y_eval)

        # =====================================================
        # Nothing detected
        # =====================================================

        if not occupied:

            lane_center = (X_left + X_right) / 2.0

            return lane_center - X_center

        # =====================================================
        # Merge intervals
        # =====================================================

        occupied.sort(key=lambda x: x["start"])

        merged = []

        for obj in occupied:

            if not merged:

                merged.append(obj)

            elif obj["start"] <= merged[-1]["end"]:

                merged[-1]["end"] = max(merged[-1]["end"],obj["end"])

            else:
                merged.append(obj)

        # =====================================================
        # Compute gaps
        # =====================================================

        gaps = []

        gaps.append({"start": X_left,"end": merged[0]["start"]})

        for i in range(len(merged)-1):

            gaps.append({

                "start":
                    merged[i]["end"],

                "end":
                    merged[i+1]["start"]
            })

        gaps.append({
            "start": merged[-1]["end"],
            "end": X_right
        })

        gaps = [
            g for g in gaps
            if g["end"] > g["start"]
        ]

        if not gaps:

            return 0.0

        # =====================================================
        # Biggest gap
        # =====================================================

        best_gap = max(
            gaps,
            key=lambda g:
                g["end"] - g["start"]
        )

        target_center = (best_gap["start"] + best_gap["end"]) / 2.0

        total_error = (target_center - X_center)

        return total_error

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