#!/usr/bin/env python3
"""
pointcloud_logger_node.py
--------------------------
ROS2 node that subscribes to the PointCloud2 topic published by
road_detector.py and writes every received cloud to a human-readable
text file so you can verify the data is correct.

Usage
-----
    python3 pointcloud_logger_node.py --ros-args \
        -p pointcloud_topic:=/road_detector/pointcloud \
        -p output_file:=/tmp/pointcloud_log.txt \
        -p max_points_to_log:=50 \
        -p log_every_n:=1

Parameters
----------
pointcloud_topic   (str)  - Topic to subscribe to.
                             Default: /road_detector/pointcloud
output_file        (str)  - Path of the output text file.
                             Default: /tmp/pointcloud_log.txt
max_points_to_log  (int)  - Max XYZ points written per message (0 = all).
                             Default: 50
log_every_n        (int)  - Log every Nth message (1 = every message).
                             Default: 1
flush_every_n      (int)  - Flush the file every Nth logged message.
                             Default: 5
"""

import sys
import os
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)

from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2 as pc2


class PointCloudLoggerNode(Node):
    """Subscribes to PointCloud2 and logs every cloud to a text file."""

    def __init__(self):
        super().__init__("pointcloud_logger")

        # ── Declare parameters ────────────────────────────────────────────────
        self.declare_parameter("pointcloud_topic", "/road_detector/pointcloud")
        self.declare_parameter("output_file", "/tmp/pointcloud_log.txt")
        self.declare_parameter("max_points_to_log", 50)
        self.declare_parameter("log_every_n", 1)
        self.declare_parameter("flush_every_n", 5)

        # ── Load parameters ───────────────────────────────────────────────────
        self.topic = self.get_parameter("pointcloud_topic").value
        self.output_file = self.get_parameter("output_file").value
        self.max_points = self.get_parameter("max_points_to_log").value
        self.log_every_n = self.get_parameter("log_every_n").value
        self.flush_every_n = self.get_parameter("flush_every_n").value

        # ── Open output file ──────────────────────────────────────────────────
        output_dir = os.path.dirname(self.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        try:
            self.log_file = open(self.output_file, "w", encoding="utf-8")
        except OSError as e:
            self.get_logger().fatal(f"Cannot open output file '{self.output_file}': {e}")
            raise

        self._write_header()

        # ── Counters ──────────────────────────────────────────────────────────
        self.msg_count = 0       # total messages received
        self.logged_count = 0    # messages actually written

        # ── Subscriber ───────────────────────────────────────────────────────
        # road_detector publishes with RELIABLE QoS; match it here
        reliable_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub = self.create_subscription(
            PointCloud2,
            self.topic,
            self._cloud_callback,
            reliable_qos,
        )

        self.get_logger().info(
            f"PointCloudLoggerNode ready.\n"
            f"  Subscribing to : {self.topic}\n"
            f"  Output file    : {self.output_file}\n"
            f"  Max pts/msg    : {'all' if self.max_points == 0 else self.max_points}\n"
            f"  Log every Nth  : {self.log_every_n}"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _write_header(self):
        self.log_file.write(
            "=" * 70 + "\n"
            "PointCloud2 Log — road_detector output verification\n"
            "=" * 70 + "\n"
            "Columns: X (m)  Y (m)  Z (m)\n"
            "Format : one point per line, clouds separated by a blank line\n"
            "=" * 70 + "\n\n"
        )

    def _cloud_callback(self, msg: PointCloud2):
        self.msg_count += 1

        # Throttle logging
        if self.msg_count % self.log_every_n != 0:
            return

        self.logged_count += 1

        # ── Extract fields ────────────────────────────────────────────────────
        fields = [f.name for f in msg.fields]
        stamp = msg.header.stamp
        timestamp_sec = stamp.sec + stamp.nanosec * 1e-9

        # Read XYZ points
        try:
            # read_points returns a generator of named tuples / dicts
            points = list(
                pc2.read_points(msg, field_names=("x", "y", "z"), skip_nans=True)
            )
        except Exception as e:
            self.get_logger().error(f"Failed to read point cloud: {e}")
            return

        total_pts = len(points)
        pts_to_log = points if self.max_points == 0 else points[: self.max_points]

        # ── Write to file ─────────────────────────────────────────────────────
        self.log_file.write(
            f"--- Message #{self.logged_count} (received #{self.msg_count}) ---\n"
            f"  Timestamp  : {timestamp_sec:.6f} s\n"
            f"  Frame ID   : {msg.header.frame_id}\n"
            f"  Fields     : {fields}\n"
            f"  Total pts  : {total_pts}\n"
            f"  Logged pts : {len(pts_to_log)}"
            + (" (truncated)" if len(pts_to_log) < total_pts else "")
            + "\n"
            f"  Width x Height: {msg.width} x {msg.height}\n"
            f"  Is dense   : {msg.is_dense}\n"
            f"  Point step : {msg.point_step} bytes\n"
        )

        # Write point data
        if total_pts == 0:
            self.log_file.write("  (empty cloud)\n")
        else:
            self.log_file.write("  Points (X, Y, Z):\n")
            for i, pt in enumerate(pts_to_log):
                # pt is a named tuple — access by index or name
                x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
                self.log_file.write(f"    [{i:>5}]  {x:>10.4f}  {y:>10.4f}  {z:>10.4f}\n")

            # Quick per-cloud statistics
            import numpy as np
            arr = [(float(p[0]), float(p[1]), float(p[2])) for p in points]
            import numpy as np
            arr_np = np.array(arr, dtype=float)
            self.log_file.write(
                f"\n  Statistics (all {total_pts} pts):\n"
                f"    X  min={arr_np[:,0].min():.4f}  max={arr_np[:,0].max():.4f}"
                f"  mean={arr_np[:,0].mean():.4f}\n"
                f"    Y  min={arr_np[:,1].min():.4f}  max={arr_np[:,1].max():.4f}"
                f"  mean={arr_np[:,1].mean():.4f}\n"
                f"    Z  min={arr_np[:,2].min():.4f}  max={arr_np[:,2].max():.4f}"
                f"  mean={arr_np[:,2].mean():.4f}\n"
            )

        self.log_file.write("\n")

        # Periodic flush so data is visible even if node is still running
        if self.logged_count % self.flush_every_n == 0:
            self.log_file.flush()

        # Console summary
        self.get_logger().info(
            f"[msg {self.logged_count}] Logged cloud: "
            f"{total_pts} pts | stamp={timestamp_sec:.3f}s | "
            f"frame='{msg.header.frame_id}'"
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def destroy_node(self):
        if not self.log_file.closed:
            self.log_file.write(
                "\n" + "=" * 70 + "\n"
                f"Session ended.  Total received: {self.msg_count}  "
                f"Total logged: {self.logged_count}\n"
                + "=" * 70 + "\n"
            )
            self.log_file.flush()
            self.log_file.close()
            self.get_logger().info(
                f"Log file closed.  "
                f"Received {self.msg_count} msgs, logged {self.logged_count}."
            )
        super().destroy_node()


# ── Entry point ────────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)

    try:
        node = PointCloudLoggerNode()
    except (RuntimeError, OSError) as e:
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
