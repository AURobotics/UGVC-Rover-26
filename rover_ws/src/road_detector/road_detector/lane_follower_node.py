#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import PointCloud2
import sensor_msgs_py.point_cloud2 as pc2
import numpy as np

class LaneFollowerNode(Node):
    def __init__(self):
        super().__init__('lane_follower_node')
        
        # --- Declare All Parameters (Small Robot Defaults) ---
        self.declare_parameter('lane_topic', '/road_detector/lanes')
        self.declare_parameter('potholes_topic', '/road_detector/potholes')
        self.declare_parameter('obstacles_topic', '/rplidar/obstacles')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        
        self.declare_parameter('min_look_ahead', 0.15)
        self.declare_parameter('max_look_ahead', 4.0)
        
        self.declare_parameter('target_linear_velocity', 0.15)
        self.declare_parameter('kp_steering', 1.0)
        
        self.declare_parameter('wall_hug_distance', 0.75)
        self.declare_parameter('single_wall_speed_multiplier', 0.85)

        # --- Fetch Topic Names ---
        lane_topic = self.get_parameter('lane_topic').value
        potholes_topic = self.get_parameter('potholes_topic').value
        obstacles_topic = self.get_parameter('obstacles_topic').value
        vel_topic = self.get_parameter('cmd_vel_topic').value
        
        # --- Subscribers & Publishers ---
        self.cloud_sub = self.create_subscription(
            PointCloud2,
            lane_topic, 
            self.cloud_callback,
            10
        )
        
        self.lost_frames_count = 0
        self.max_coast_frames = 10  # Coast for 10 frames before giving up (adjust based on your camera FPS)
        
        self.cmd_vel_pub = self.create_publisher(Twist, vel_topic, 10)
        
        self.get_logger().info(f"Lane Follower Node initialized for Small Robot.")
        self.get_logger().info(f"Listening to: {lane_topic} | Publishing to: {vel_topic}")

    def cloud_callback(self, msg):
        # Fetch current dynamic tuning parameters
        min_x = self.get_parameter('min_look_ahead').value
        max_x = self.get_parameter('max_look_ahead').value
        kp = self.get_parameter('kp_steering').value
        linear_vel = self.get_parameter('target_linear_velocity').value
        wall_hug = self.get_parameter('wall_hug_distance').value
        speed_mult = self.get_parameter('single_wall_speed_multiplier').value

        left_y_coords = []
        right_y_coords = []

        # Parse PointCloud2
        for p in pc2.read_points(msg, field_names=("x", "y"), skip_nans=True):
            x, y = p[0], p[1]
            if min_x <= x <= max_x:
                if y > 0.0:
                    left_y_coords.append(y)
                else:
                    right_y_coords.append(y)

        twist_msg = Twist()

       # --- STATE MACHINE ---
        
        # If we see ANY walls, reset the lost frame counter
        if len(left_y_coords) > 0 or len(right_y_coords) > 0:
            self.lost_frames_count = 0  
            
            # CASE 1: Normal Driving (Both walls visible)
            if len(left_y_coords) > 0 and len(right_y_coords) > 0:
                avg_left_y = np.mean(left_y_coords)
                avg_right_y = np.mean(right_y_coords)
                
                target_center_y = (avg_left_y + avg_right_y) / 2.0
                error_y = float(target_center_y - 0.0)
                
                twist_msg.linear.x = float(linear_vel)
                twist_msg.angular.z = float(kp * error_y)
                
            # CASE 2: Track Widens/Narrows (Only Left Wall Visible)
            elif len(left_y_coords) > 0:
                error_y = float(np.mean(left_y_coords) - wall_hug)
                twist_msg.linear.x = float(linear_vel * speed_mult)
                twist_msg.angular.z = float(kp * error_y)
                
            # CASE 3: Track Widens/Narrows (Only Right Wall Visible)
            elif len(right_y_coords) > 0:
                error_y = float(np.mean(right_y_coords) + wall_hug)
                twist_msg.linear.x = float(linear_vel * speed_mult)
                twist_msg.angular.z = float(kp * error_y)

        # CASE 4: No points detected
        else:
            self.lost_frames_count += 1
            
            if self.lost_frames_count < self.max_coast_frames:
                # 4a. Coasting State: Move forward slowly, zero steering
                twist_msg.linear.x = float(linear_vel * 0.5)
                twist_msg.angular.z = 0.0
                self.get_logger().warn(f"Lost lane! Coasting forward... ({self.lost_frames_count}/{self.max_coast_frames})", throttle_duration_sec=0.5)
            else:
                # 4b. Recovery State: Coasting failed. Spin in place to find the road!
                twist_msg.linear.x = 0.0
                twist_msg.angular.z = 0.4  # Adjust this speed so it spins slowly enough for the camera to catch the lines
                self.get_logger().error("Track lost completely! Spinning to search...", throttle_duration_sec=1.0)

        # Publish the safe native-float Twist message
        self.cmd_vel_pub.publish(twist_msg)

def main(args=None):
    rclpy.init(args=args)
    node = LaneFollowerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        emergency_stop = Twist()
        node.cmd_vel_pub.publish(emergency_stop)
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()