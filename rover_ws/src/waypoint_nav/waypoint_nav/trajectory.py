#!/usr/bin/env python3

import math
import os
import numpy as np
import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path, Odometry
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA
from builtin_interfaces.msg import Duration, Time
from ament_index_python.packages import get_package_share_directory

EARTH_RADIUS_M = 6_371_000.0

def gps_to_xy(lat, lon, origin_lat, origin_lon):
    x = math.radians(lon - origin_lon) * math.cos(math.radians(origin_lat)) * EARTH_RADIUS_M
    y = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return np.array([x, y])
    

class BezierCurve:
    def __init__(self, control_scale=0.3, min_control_dist=0.2, points_per_meter=5): #####
        self.control_scale    = control_scale
        self.min_control_dist = min_control_dist
        self.points_per_meter = points_per_meter

    def generate(self, P0, theta0, P3, theta3) -> np.ndarray:
        """
        Generates a parametric Cubic Bezier Curve between two points (P0 and P3) 
        given their respective boundary heading constraints (theta0 and theta3).
        """
        P0 = np.array(P0, dtype=float)
        P3 = np.array(P3, dtype=float)
        path_length  = np.linalg.norm(P3 - P0)
        control_dist = max(self.min_control_dist, self.control_scale * path_length)

        P1 = P0 + control_dist * np.array([math.cos(theta0), math.sin(theta0)])
        P2 = P3 - control_dist * np.array([math.cos(theta3), math.sin(theta3)])

        num_points = max(10, int(self.points_per_meter * path_length))
        t = np.linspace(0, 1, num_points).reshape(-1, 1)

        trajectory = ((1 - t)**3        * P0 +
                      3*(1 - t)**2 * t   * P1 +
                      3*(1 - t)   * t**2 * P2 +
                      t**3               * P3)
        return trajectory

    def heading_between2p(self, A, B) -> float:
        return math.atan2(B[1] - A[1], B[0] - A[0])

    def build_full_path(self, xy_waypoints: list) -> np.ndarray:
        pts = [np.array(p, dtype=float) for p in xy_waypoints]
        n   = len(pts)
        if n < 2:
            raise ValueError("Need at least 2 waypoints")
     #compute tangent 
        headings = []
        for i in range(n):
            if i == 0:
                h = self.heading_between2p(pts[0], pts[1])
            elif i == n - 1:
                h = self.heading_between2p(pts[-2], pts[-1])
            else:
                h_in  = self.heading_between2p(pts[i-1], pts[i])
                h_out = self.heading_between2p(pts[i],   pts[i+1])
                h = math.atan2(math.sin(h_in) + math.sin(h_out), math.cos(h_in) + math.cos(h_out))
            headings.append(h)
        #generate curve
        segments = []
        for i in range(n - 1):
            seg = self.generate(P0=pts[i], theta0=headings[i], P3=pts[i + 1], theta3=headings[i + 1])
            if i < n - 2:
                seg = seg[:-1]
            segments.append(seg)
        return np.vstack(segments)


class TrajectoryNode(Node):
    def __init__(self):
        super().__init__("trajectory_node")

        self.declare_parameter("waypoints_file",     "config/waypoints.yaml")
        self.declare_parameter("control_scale",      0.3)
        self.declare_parameter("min_control_dist",   0.2)
        self.declare_parameter("points_per_meter",   15)
        self.declare_parameter("republish_rate_sec", 2.0)

        self.wf              = self.get_parameter("waypoints_file").value  
        control_scale        = self.get_parameter("control_scale").value
        min_control_dist     = self.get_parameter("min_control_dist").value
        points_per_meter     = self.get_parameter("points_per_meter").value
        republish_rate       = self.get_parameter("republish_rate_sec").value

        self.generator = BezierCurve(
            control_scale    = control_scale,
            min_control_dist = min_control_dist,
            points_per_meter = int(points_per_meter),
        )

        self.robot_pose      = None
        self.path_array      = None
        self.final_waypoints = []
        self.final_labels    = []
        self.is_path_built   = False   

        latch_qos = QoSProfile(
            depth       = 1,
            durability  = DurabilityPolicy.TRANSIENT_LOCAL,
            reliability = ReliabilityPolicy.RELIABLE,
        )

        self.path_pub    = self.create_publisher(Path,        "/controller/path",      latch_qos)
        self.markers_pub = self.create_publisher(MarkerArray, "/controller/waypoints", latch_qos)

        self.create_subscription(Odometry, "/odom", self._odom_callback, qos_profile_sensor_data)
        self.republish_timer = self.create_timer(republish_rate, self._publish_all)
        self.get_logger().info("TrajectoryNode Initialized. Waiting for /odom...")

    def _odom_callback(self, msg: Odometry):
        if self.is_path_built:
            return

        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        self.robot_pose = np.array([x, y])
        
        self.get_logger().info(f" Odom received! Robot at: ({x:.2f}, {y:.2f}). Building path...")
      
        try:
            yaml_wps, yaml_labels = self._load_waypoints_relative_to_robot(self.wf, x, y)
            self.final_waypoints = [self.robot_pose] + yaml_wps
            self.final_labels = ["Start (Robot)"] + yaml_labels

            self.path_array = self.generator.build_full_path(self.final_waypoints)
            self.is_path_built = True  
            self.get_logger().info(f"Full path successfully built with {len(self.path_array)} points!")
            self._publish_all()
        except Exception as e:
            self.get_logger().error(f" Failed to build path: {str(e)}")
        
    def _load_waypoints_relative_to_robot(self, yaml_path: str, robot_x: float, robot_y: float):
        if not os.path.isabs(yaml_path):
            try:
                pkg_dir = get_package_share_directory('waypoint_nav')
                yaml_path = os.path.join(pkg_dir, 'config', 'waypoints.yaml')
            except Exception:
                yaml_path = os.path.join(os.path.dirname(__file__), "..", yaml_path)

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        raw = data.get("waypoints", [])
        if not raw:
            raise ValueError("No waypoints found in YAML file")

        origin_gps = raw[0]
        xy_list = []
        labels  = []
        
        for i, wp in enumerate(raw[1:], start=1):
            xy_rel = gps_to_xy(
                wp["latitude"], wp["longitude"],
                origin_gps["latitude"], origin_gps["longitude"]
            )
            xy_world = np.array([robot_x + xy_rel[0], robot_y + xy_rel[1]])
            xy_list.append(xy_world)
            labels.append(wp.get("label", f"wp{i}"))

        return xy_list, labels

    def _publish_all(self):
        if self.path_array is None:
            return
        zero_stamp = Time(sec=0, nanosec=0)
        self._publish_path(zero_stamp)
        self._publish_waypoint_markers(zero_stamp)

    def _publish_path(self, stamp):
        msg = Path()
        msg.header.frame_id = "odom"
        msg.header.stamp    = stamp

        for (x, y) in self.path_array:
            ps = PoseStamped()
            ps.header             = msg.header
            ps.pose.position.x    = float(x)
            ps.pose.position.y    = float(y)
            ps.pose.position.z    = 0.0
            ps.pose.orientation.w = 1.0
            msg.poses.append(ps)
        self.path_pub.publish(msg)

    def _publish_waypoint_markers(self, stamp):
        arr = MarkerArray()
        for i, (xy, label) in enumerate(zip(self.final_waypoints, self.final_labels)):
            sphere                    = Marker()
            sphere.header.frame_id    = "odom"
            sphere.header.stamp       = stamp
            sphere.ns                 = "waypoints"
            sphere.id                 = i * 2
            sphere.type               = Marker.SPHERE
            sphere.action             = Marker.ADD
            sphere.pose.position.x    = float(xy[0])
            sphere.pose.position.y    = float(xy[1])
            sphere.pose.position.z    = 0.0
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.3
            
            if i == 0:
                sphere.color          = ColorRGBA(r=0.0, g=0.5, b=1.0, a=0.9)
            else:
                sphere.color          = ColorRGBA(r=0.0, g=1.0, b=0.0, a=0.9)
                
            sphere.lifetime           = Duration(sec=0)
            arr.markers.append(sphere)

            text                    = Marker()
            text.header             = sphere.header
            text.ns                 = "waypoint_labels"
            text.id                 = i * 2 + 1
            text.type               = Marker.TEXT_VIEW_FACING
            text.action             = Marker.ADD
            text.pose.position.x    = float(xy[0])
            text.pose.position.y    = float(xy[1])
            text.pose.position.z    = 0.5
            text.pose.orientation.w = 1.0
            text.scale.z            = 0.3
            text.color              = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
            text.text               = label
            text.lifetime           = Duration(sec=0)
            arr.markers.append(text)
        self.markers_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()