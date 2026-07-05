#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu

def main():
    rclpy.init()
    node = Node("imu_republisher")

    imu_pub = node.create_publisher(Imu, "imu/ekf", 10)

    def imu_callback(imu):
        imu.header.frame_id = "base_footprint_ekf"
        imu_pub.publish(imu)

    node.create_subscription(Imu, "/imu", imu_callback, 10)

    # ROS-aware delay — uses a wall timer instead of blocking sleep
    node.get_clock().sleep_for(rclpy.duration.Duration(seconds=1))

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()