"""
Tests for navigate_to_waypoint(): the code that builds the raw_gps_path goal
sent to the Bezier action server.

Covers:
  - refuses to send a goal when there's no GPS fix yet (would otherwise crash
    or silently generate a garbage 0,0 origin)
  - sends exactly 2 poses (current position, target waypoint) -- the action
    server's goal_callback rejects anything with < 2 poses
  - pose[0] is the robot's CURRENT position, pose[1] is the TARGET waypoint
    (order matters: pose[0] becomes the local-frame origin server-side)
  - lat/lon values land in .position.x/.position.y respectively, matching
    what trajectory.py's gps_to_xy() expects
  - wait_for_server() / send_goal_async() are actually invoked
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mission import mission_node as mn
from conftest import TEST_WAYPOINTS

def test_navigate_to_waypoint_noop_without_gps_fix(make_mission_node):
    node = make_mission_node()
    node._action_client.wait_for_server = MagicMock()
    node._action_client.send_goal_async = MagicMock()

    assert node.current_lat is None and node.current_lon is None
    node.navigate_to_waypoint(2)

    node._action_client.wait_for_server.assert_not_called()
    node._action_client.send_goal_async.assert_not_called()
    assert node._send_goal_future is None


def test_navigate_to_waypoint_sends_two_point_path(make_mission_node):
    node = make_mission_node()
    node.current_lat, node.current_lon = 30.0800000000, 31.2960000000

    node._action_client.wait_for_server = MagicMock()
    fake_future = MagicMock()
    node._action_client.send_goal_async = MagicMock(return_value=fake_future)

    node.navigate_to_waypoint(2)

    node._action_client.wait_for_server.assert_called_once()
    node._action_client.send_goal_async.assert_called_once()

    goal_msg = node._action_client.send_goal_async.call_args[0][0]
    poses = goal_msg.raw_gps_path.poses
    assert len(poses) == 2, "action server rejects goals with < 2 poses"

    start, target = poses[0], poses[1]
    assert start.pose.position.x == 30.0800000000
    assert start.pose.position.y == 31.2960000000

    wp2 = TEST_WAYPOINTS[2]
    assert target.pose.position.x == wp2["latitude"]
    assert target.pose.position.y == wp2["longitude"]

    assert goal_msg.raw_gps_path.header.frame_id == "wgs84"

    # feedback callback wired, and future stored + a done callback attached
    kwargs = node._action_client.send_goal_async.call_args[1]
    assert kwargs["feedback_callback"] == node._waypoint_navigation_feedback_callback
    assert node._send_goal_future is fake_future
    fake_future.add_done_callback.assert_called_once_with(
        node._waypoint_navigation_goal_response_callback
    )


def test_navigate_to_waypoint_uses_correct_target_for_each_waypoint(make_mission_node):
    node = make_mission_node()
    node.current_lat, node.current_lon = 30.0800000000, 31.2960000000
    node._action_client.wait_for_server = MagicMock()

    for wp_num in (1, 2, 3):
        node._action_client.send_goal_async = MagicMock(return_value=MagicMock())
        node.navigate_to_waypoint(wp_num)
        goal_msg = node._action_client.send_goal_async.call_args[0][0]
        target = goal_msg.raw_gps_path.poses[1]
        expected = TEST_WAYPOINTS[wp_num]
        assert target.pose.position.x == expected["latitude"]
        assert target.pose.position.y == expected["longitude"]
