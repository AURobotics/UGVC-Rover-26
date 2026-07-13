#!/usr/bin/env python3
# controller node for sending GPS waypoints to the Bezier path server
import os
import yaml
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from ament_index_python.packages import get_package_share_directory
from rover_interfaces.action import GenerateBezierPath


class BezierPathClient(Node):
    def __init__(self):
        super().__init__("bezier_path_client")
        self.declare_parameter("waypoints_file", "config/waypoints.yaml")
        self.yaml_file_param = self.get_parameter("waypoints_file").value

        self._action_client = ActionClient(
            self,
            GenerateBezierPath,
            "generate_bezier_path"
        )

        self.get_logger().info("Action Client intialized")
        self.send_waypoints_goal()

    def _resolve_yaml_path(self):
        yaml_path = self.yaml_file_param
        if os.path.isabs(yaml_path):
            return yaml_path
        try:
            pkg_dir = get_package_share_directory('waypoint_nav')
            return os.path.join(pkg_dir, 'config', 'waypoints.yaml')
        except Exception:
            return os.path.join(os.path.dirname(__file__), "..", yaml_path)

    def send_waypoints_goal(self):
        yaml_path = self._resolve_yaml_path()

        if not os.path.exists(yaml_path):
            self.get_logger().error(f"YAML file not found at: {yaml_path}")
            return

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        raw_wps = data.get("waypoints", [])
        if not raw_wps:
            self.get_logger().error("No waypoints found ")
            return

        self.get_logger().info(f"Loaded {len(raw_wps)} GPS waypoints from YAML.")

        gps_path_msg = Path()
        gps_path_msg.header.frame_id = "wgs84"
        gps_path_msg.header.stamp = self.get_clock().now().to_msg()

        for wp in raw_wps:
            ps = PoseStamped()
            ps.pose.position.x = float(wp["latitude"])
            ps.pose.position.y = float(wp["longitude"])
            ps.pose.position.z = 0.0
            gps_path_msg.poses.append(ps)

        goal_msg = GenerateBezierPath.Goal()
        goal_msg.raw_gps_path = gps_path_msg

        self.get_logger().info("Waiting for Path Action ")
        self._action_client.wait_for_server()

        self.get_logger().info("Sending GPS Waypoints to Server...")
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._feedback_callback
        )
        self._send_goal_future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal REJECTED by server.")
            rclpy.shutdown()
            return

        self.get_logger().info("Goal ACCEPTED by server, waiting for result...")
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self._get_result_callback)

    def _feedback_callback(self, feedback_msg):
        status = feedback_msg.feedback.status
        self.get_logger().info(f"[Feedback State]: {status}")

    def _get_result_callback(self, future):
        result = future.result().result
        if result.success:
            self.get_logger().info(f"[Success]: {result.message}")
            self.get_logger().info(
                f"Total dense points built and published: {result.total_generated_points}"
            )
    
            if result.leg_start_indices:
                self.get_logger().info(
                    f"Leg start indices: {list(result.leg_start_indices)}"
                )
                self.get_logger().info(
                    f"Leg point counts:  {list(result.leg_point_counts)}"
                )
        else:
            self.get_logger().error(f"[Failed]: {result.message}")

        self.get_logger().info("Shutting down Client Node.")
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = BezierPathClient()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()