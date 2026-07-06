#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped
from std_srvs.srv import SetBool

import time
from enum import Enum

class MissionState(Enum):
    INIT = 0
    PHASE1_LANE_TO_WP1 = 1
    PHASE2_NAV_TO_WP2 = 2
    PHASE2_TIMED_TASK = 3
    PHASE3_NAV_TO_WP3 = 4
    COMPLETED = 5

class RoverMissionExecutive(Node):
    def __init__(self):
        super().__init__('rover_mission_executive')
        
        # Use a ReentrantCallbackGroup so Nav2 actions and service calls 
        # can execute simultaneously without blocking each other
        self.cb_group = ReentrantCallbackGroup()
        
        # Initialize Nav2 Simple Commander
        self.navigator = BasicNavigator()
        
        # Service Client to toggle your lane detection node
        self.lane_toggle_client = self.create_client(
            SetBool, 
            '/lane_detector/toggle_walls', 
            callback_group=self.cb_group
        )
        
        # Define Mission State
        self.state = MissionState.INIT
        
        # Define Waypoints (x, y, theta_z, w)
        self.wp1 = self.generate_pose(1.5, 2.0, 0.0, 1.0)
        self.wp2 = self.generate_pose(5.0, -1.0, 0.707, 0.707)
        self.wp3 = self.generate_pose(10.0, 4.0, 0.0, 1.0)
        
        # Wait for dependencies to be ready
        self.wait_for_system()
        
        # Kickoff the mission loop using a one-shot timer to keep the constructor non-blocking
        self.create_timer(0.5, self.mission_loop, callback_group=self.cb_group)

    def generate_pose(self, x, y, qz, qw):
        """Helper to build a PoseStamped message."""
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def wait_for_system(self):
        """Blocks until Nav2 lifecycle and vital services are active."""
        self.get_logger().info("Waiting for Lane Toggle service...")
        while not self.lane_toggle_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().info("Service not available, waiting...")
            
        self.get_logger().info("Waiting for Nav2 lifecycle to be active...")
        self.navigator.waitUntilNav2Active()
        self.get_logger().info("System is completely ready!")

    def set_lane_walls(self, enable: bool):
        """Synchronously updates the state of the lane virtual obstacles."""
        req = SetBool.Request()
        req.data = enable
        self.get_logger().info(f"Sending request: set_lane_walls = {enable}")
        
        # call_async mixed with an executor loop handles thread safety elegantly
        future = self.lane_toggle_client.call_async(req)
        while not future.done():
            time.sleep(0.1)
        
        res = future.result()
        if res and res.success:
            self.get_logger().info(f"Successfully toggled lane walls: {res.message}")
        else:
            self.get_logger().error("Failed to toggle lane walls.")

    def mission_loop(self):
        """State Machine managing the transitions between coordinates and modalities."""
        
        # Phase 1: Enable lane walls and travel to WP1
        if self.state == MissionState.INIT:
            self.set_lane_walls(True)
            self.get_logger().info("Navigating to Waypoint 1 (Lane Mode active)...")
            self.navigator.goToPose(self.wp1)
            self.state = MissionState.PHASE1_LANE_TO_WP1

        elif self.state == MissionState.PHASE1_LANE_TO_WP1:
            if self.navigator.isTaskComplete():
                if self.navigator.getResult() == TaskResult.SUCCEEDED:
                    self.get_logger().info("Arrived at Waypoint 1 successfully.")
                    
                    # Disable lane walls before traveling to WP2
                    self.set_lane_walls(False)
                    self.get_logger().info("Clearing virtual costmap lanes for open transit...")
                    time.sleep(1.5)  # Buffer time for costmap decay/clearing layer
                    
                    self.navigator.goToPose(self.wp2)
                    self.state = MissionState.PHASE2_NAV_TO_WP2
                else:
                    self.get_logger().error("Failed to reach Waypoint 1. Aborting.")
                    self.state = MissionState.COMPLETED

        # Phase 2: Open area navigation to WP2
        elif self.state == MissionState.PHASE2_NAV_TO_WP2:
            if self.navigator.isTaskComplete():
                if self.navigator.getResult() == TaskResult.SUCCEEDED:
                    self.get_logger().info("Arrived at Waypoint 2. Commencing timed task loop.")
                    self.task_start_time = time.time()
                    self.state = MissionState.PHASE2_TIMED_TASK
                else:
                    self.get_logger().error("Failed to reach Waypoint 2. Aborting.")
                    self.state = MissionState.COMPLETED

        # Phase 2: Execute Task with a hard-capped 45s timer
        elif self.state == MissionState.PHASE2_TIMED_TASK:
            elapsed_time = time.time() - self.task_start_time
            
            # --- Insert your task triggers/checks here ---
            # Ex: trigger an internal service or flag to start drilling/sampling
            
            if elapsed_time >= 45.0:
                self.get_logger().warn(f"Task timed out at {elapsed_time:.1f}s limit. Exiting task.")
                # Send Nav goal to Waypoint 3
                self.navigator.goToPose(self.wp3)
                self.state = MissionState.PHASE3_NAV_TO_WP3
            else:
                self.get_logger().info(f"Task performing... Elapsed: {elapsed_time:.1f}s", throttle_duration_sec=5.0)

        # Phase 3: Travel to WP3, then bring lanes back online
        elif self.state == MissionState.PHASE3_NAV_TO_WP3:
            if self.navigator.isTaskComplete():
                if self.navigator.getResult() == TaskResult.SUCCEEDED:
                    self.get_logger().info("Arrived at Waypoint 3. Re-enabling lane walls.")
                    self.set_lane_walls(True)
                    
                    # Add your closing strategy logic or next coordinate goals here!
                    self.state = MissionState.COMPLETED
                else:
                    self.get_logger().error("Failed to reach Waypoint 3. Aborting.")
                    self.state = MissionState.COMPLETED

        elif self.state == MissionState.COMPLETED:
            self.get_logger().info("Mission routine ended completely. Shutting down Executive Node.")
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    node = RoverMissionExecutive()
    
    # We use a MultiThreadedExecutor so the ReentrantCallbackGroup 
    # can spawn threads for calls while managing the state machine loop
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()