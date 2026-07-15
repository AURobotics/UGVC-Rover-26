#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header
import sensor_msgs_py.point_cloud2 as pc2
import numpy as np

class MockLanePublisher(Node):
    def __init__(self):
        super().__init__('mock_lane_publisher')
        self.pub = self.create_publisher(PointCloud2, '/lane_pointcloud', 10)
        self.timer = self.create_timer(0.1, self.publish_fake_lanes)
        self.offset = 0.0  # Change this to simulate drifting left or right

    def publish_fake_lanes(self):
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = 'base_footprint'

        points = []
        # Create a corridor 1 to 2 meters ahead
        for x in np.arange(1.0, 2.1, 0.1):
            # Left wall is at Y = 0.5 + offset
            points.append([x, 0.5 + self.offset, 0.0])
            # Right wall is at Y = -0.5 + offset
            points.append([x, -0.5 + self.offset, 0.0])

        cloud = pc2.create_cloud_xyz32(header, points)
        self.pub.publish(cloud)

def main():
    rclpy.init()
    node = MockLanePublisher()
    
    # Test 1: Dead center (offset = 0.0) -> Steering should be 0.0
    # Test 2: Drift left (offset = -0.2) -> Steering should be negative (steer right)
    node.offset = -0.2 
    
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()