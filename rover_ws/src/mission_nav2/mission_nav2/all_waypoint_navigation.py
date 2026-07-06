#!/usr/bin/env python3
"""
lane_mode_manager.py

Drives the 3-waypoint mission described:
  start --(lanes on)--> WP1 --(lanes off)--> WP2 --[task, <=45s]--> WP3 --(lanes on)--> continue

It does this by:
  1. Sending NavigateToPose goals one at a time (simpler to reason about than
     FollowWaypoints when you need to inject a timed task between two of them).
  2. Disabling the costmap "lane_layer" right after WP1 is reached, and
     re-enabling it right after WP3 is reached, via each costmap node's
     parameter service.
  3. Running your task callback at WP2 with a hard 45s timeout.

Replace `run_task_at_wp2()` with your actual task logic (call a service,
publish a command, wait for a "task done" topic, etc). It already returns
early if the task finishes before the timeout.

This is a reference skeleton -- adapt topic/action names, frame, and the
waypoint coordinates to your setup.
"""

import time
from dataclasses import dataclass

import rclpy
from rclpy.action.client import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import Parameter as ParameterMsg
from rcl_interfaces.srv import SetParameters
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose

#TODO: use cancel_all_goals method as needed
#TODO: add manual
#TODO: organize code

@dataclass
class Waypoint:
    x: float
    y: float
    yaw: float = 0.0


# ---- SET YOUR ACTUAL COORDINATES HERE (in the map frame) ------------------
WP1 = Waypoint(x=5.0, y=0.0)     # lanes end here
WP2 = Waypoint(x=8.0, y=2.0)     # task location
WP3 = Waypoint(x=11.0, y=0.0)    # lanes resume here
TASK_TIMEOUT_S = 45.0
# -----------------------------------------------------------------------


def make_pose(wp: Waypoint, frame_id: str = "map") -> PoseStamped:
    from tf_transformations import quaternion_from_euler  # or write your own yaw->quat
    ps = PoseStamped()
    ps.header.frame_id = frame_id
    q = quaternion_from_euler(0, 0, wp.yaw)
    ps.pose.position.x = wp.x
    ps.pose.position.y = wp.y
    ps.pose.orientation.x = q[0]
    ps.pose.orientation.y = q[1]
    ps.pose.orientation.z = q[2]
    ps.pose.orientation.w = q[3]
    return ps


class LaneModeManager(Node):

    def __init__(self):
        super().__init__("lane_mode_manager")
        self._nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._local_param_client = self.create_client(
            SetParameters, "/local_costmap/local_costmap/set_parameters")
        self._global_param_client = self.create_client(
            SetParameters, "/global_costmap/global_costmap/set_parameters")

    # -- costmap lane layer toggle -------------------------------------
    def set_lane_layer_enabled(self, enabled: bool):
        self.get_logger().info(f"Setting lane_layer.enabled = {enabled}")
        for client, name in (
            (self._local_param_client, "local_costmap"),
            (self._global_param_client, "global_costmap"),
        ):
            if not client.wait_for_service(timeout_sec=5.0):
                self.get_logger().error(f"{name} set_parameters service unavailable")
                continue
            req = SetParameters.Request()
            p = ParameterMsg()
            p.name = "lane_layer.enabled"
            p.value.type = Parameter.Type.BOOL.value
            p.value.bool_value = enabled
            req.parameters = [p]
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

    # -- navigation -------------------------------------------------------
    def navigate_to(self, wp: Waypoint) -> bool:
        self._nav_client.wait_for_server()
        goal = NavigateToPose.Goal()
        goal.pose = make_pose(wp)
        self.get_logger().info(f"Navigating to ({wp.x}, {wp.y})")

        send_future = self._nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected")
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        status = result_future.result().status
        return status == GoalStatus.STATUS_SUCCEEDED
    
    #TODO: implement a cancel_all_goals method that cancels all active Nav2 goals
    def cancel_all_goals(self):
        """Cancels all active Nav2 goals."""
        self.get_logger().info("Cancelling all active navigation goals...")
        pass

    # -- task at WP2 --------------------------------------------------------
    def run_task_at_wp2(self) -> None:
        self.get_logger().info(f"Running task at WP2, timeout={TASK_TIMEOUT_S}s")
        start = time.time()
        task_done = False

        # TODO: replace this loop with your real task trigger + completion check.
        # e.g. call a service to start the task, then poll a "task_complete" topic.
        while (time.time() - start) < TASK_TIMEOUT_S and not task_done:
            task_done = self._poll_task_completion()
            time.sleep(0.5)

        elapsed = time.time() - start
        self.get_logger().info(f"Task phase ended after {elapsed:.1f}s (done={task_done})")

    def _poll_task_completion(self) -> bool:
        # Placeholder: wire this up to whatever signals your task is finished.
        return False

    # -- full mission ------------------------------------------------------
    def run_mission(self):
        # Phase A: start -> WP1, lanes ON (already enabled by default in params)
        self.set_lane_layer_enabled(True)
        if not self.navigate_to(WP1):
            self.get_logger().error("Failed to reach WP1, aborting mission")
            return

        # Phase B: WP1 -> WP2, lanes OFF (free navigation)
        self.set_lane_layer_enabled(False)
        if not self.navigate_to(WP2):
            self.get_logger().error("Failed to reach WP2, aborting mission")
            return

        # Task at WP2, capped at 45s
        self.run_task_at_wp2()

        # Phase C: WP2 -> WP3, still lanes OFF
        if not self.navigate_to(WP3):
            self.get_logger().error("Failed to reach WP3, aborting mission")
            return

        # Phase D: past WP3, lanes ON again
        self.set_lane_layer_enabled(True)
        if not self.navigate_to(WP1):
            self.get_logger().error("Failed to reach WP1, aborting mission")
            return
        
        self.get_logger().info("Mission complete: lane-following resumed")


def main():
    rclpy.init()
    node = LaneModeManager()
    try:
        node.run_mission()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
