"""
Tests for MissionNode._control_loop() -- the FSM driving lane-following ->
waypoint navigation -> face recognition -> waypoint navigation -> lanes.

is_at_waypoint(), navigate_to_waypoint(), call_face_recognition_service(),
and cancel_waypoint_navigation() are unit-tested elsewhere, so here they're
mocked/stubbed to isolate pure state-transition logic and keep tests fast
and deterministic (no real GPS math, no real action/service traffic).

Covers:
  - AUTO_LANES -> AUTO_WAYPOINTS when waypoint 1 is reached
  - AUTO_WAYPOINTS -> AUTO_WAYPOINT2 when waypoint 2 is reached (and not already done)
  - AUTO_WAYPOINTS: does NOT re-enter AUTO_WAYPOINT2 once waypoint2_done is True
  - AUTO_WAYPOINT2 -> AUTO_WAYPOINTS after WAYPOINT2_TIMEOUT elapses (heading to wp3)
  - AUTO_WAYPOINTS -> AUTO_LANES when waypoint 3 is reached
  - AUTO_WAYPOINTS -> AUTO_LANES when waypoint 3 times out (double timeout)
  - wp1 timeout (never reaching waypoint 2) skips straight to waypoint 3
  - REGRESSION: once that wp1-timeout skip has fired once, it must not keep
    re-firing every tick afterward (this was the original bug: it would
    spam cancel/resend forever and block is_at_waypoint(3) from ever being
    checked)
  - MANUAL state just republishes MANUAL and does nothing else
  - cancel_waypoint_navigation(): no future yet, future not done yet,
    future done but goal rejected, future done and goal accepted
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mission import mission_node as mn

def _stub_out_side_effects(node):
    """Replace anything that would touch the network/action servers."""
    node.navigate_to_waypoint = MagicMock()
    node.call_face_recognition_service = MagicMock()
    node.cancel_waypoint_navigation = MagicMock()
    node.state_topic_publisher.publish = MagicMock()


def test_manual_state_does_nothing_but_publish(make_mission_node):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.state = mn.State.MANUAL

    node._control_loop()

    node.state_topic_publisher.publish.assert_called_once()
    assert node.state == mn.State.MANUAL
    node.navigate_to_waypoint.assert_not_called()


def test_auto_lanes_transitions_to_auto_waypoints_at_waypoint1(make_mission_node):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.state = mn.State.AUTO_LANES
    node.is_at_waypoint = MagicMock(side_effect=lambda n: n == 1)

    node._control_loop()

    assert node.state == mn.State.AUTO_WAYPOINTS
    assert node.waypoint1_time is not None
    node.navigate_to_waypoint.assert_called_once_with(2)


def test_auto_lanes_stays_put_when_not_at_waypoint1(make_mission_node):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.state = mn.State.AUTO_LANES
    node.is_at_waypoint = MagicMock(return_value=False)

    node._control_loop()

    assert node.state == mn.State.AUTO_LANES
    node.navigate_to_waypoint.assert_not_called()


# def test_auto_waypoints_transitions_to_waypoint2_stage(make_mission_node, fake_clock):
#     node = make_mission_node()
#     _stub_out_side_effects(node)
#     node.get_clock = MagicMock(return_value=fake_clock)
#     node.state = mn.State.AUTO_WAYPOINTS
#     node.waypoint1_time = fake_clock.now()
#     node.is_at_waypoint = MagicMock(side_effect=lambda n: n == 2)

#     node._control_loop()

#     assert node.state == mn.State.AUTO_WAYPOINT2
#     assert node.waypoint2_time is not None
#     node.call_face_recognition_service.assert_called_once_with(True, "Starting face recognition for waypoint 2")


def test_auto_waypoints_does_not_reenter_waypoint2_once_done(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINTS
    node.waypoint1_time = fake_clock.now()
    node.waypoint2_done = True
    # robot happens to still be geometrically at waypoint 2's coordinates
    node.is_at_waypoint = MagicMock(side_effect=lambda n: n == 2)

    node._control_loop()

    assert node.state == mn.State.AUTO_WAYPOINTS
    node.call_face_recognition_service.assert_not_called()


def test_waypoint2_stage_times_out_and_moves_to_waypoint3(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINT2
    node.waypoint2_time = fake_clock.now()

    fake_clock.advance(mn.WAYPOINT2_TIMEOUT + 1)
    node._control_loop()

    assert node.waypoint2_done is True
    assert node.state == mn.State.AUTO_WAYPOINTS
    assert node.waypoint3_time is not None
    node.call_face_recognition_service.assert_called_once_with(False, "Stopping face recognition after 45 seconds")
    node.navigate_to_waypoint.assert_called_once_with(3)


def test_waypoint2_stage_does_not_time_out_early(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINT2
    node.waypoint2_time = fake_clock.now()

    fake_clock.advance(mn.WAYPOINT2_TIMEOUT - 5)
    node._control_loop()

    assert node.state == mn.State.AUTO_WAYPOINT2
    node.navigate_to_waypoint.assert_not_called()


def test_auto_waypoints_reaches_waypoint3_and_returns_to_lanes(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINTS
    node.waypoint2_done = True
    node.waypoint1_time = None
    node.waypoint3_time = fake_clock.now()
    node.is_at_waypoint = MagicMock(side_effect=lambda n: n == 3)

    node._control_loop()

    assert node.state == mn.State.AUTO_LANES


def test_auto_waypoints_waypoint3_double_timeout_returns_to_lanes(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINTS
    node.waypoint2_done = True
    node.waypoint1_time = None
    node.waypoint3_time = fake_clock.now()
    node.is_at_waypoint = MagicMock(return_value=False)

    fake_clock.advance((mn.WAYPOINT_TIMEOUT * 2) + 1)
    node._control_loop()

    assert node.state == mn.State.AUTO_LANES


def test_waypoint1_timeout_skips_to_waypoint3(make_mission_node, fake_clock):
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINTS
    node.waypoint1_time = fake_clock.now()
    node.is_at_waypoint = MagicMock(return_value=False)  # never reaches wp2

    fake_clock.advance(mn.WAYPOINT_TIMEOUT + 1)
    node._control_loop()

    assert node.waypoint2_done is True, "must skip face recognition since wp2 was never reached"
    assert node.waypoint1_time is None, "must clear so this branch can't refire"
    assert node.waypoint3_time is not None
    node.cancel_waypoint_navigation.assert_called_once()
    # state stays AUTO_WAYPOINTS -- it's now racing toward waypoint 3
    assert node.state == mn.State.AUTO_WAYPOINTS


def test_waypoint1_timeout_does_not_refire_on_next_tick(make_mission_node, fake_clock):
    """
    Regression test for the original bug: after the wp1-timeout skip fires
    once, waypoint1_time is cleared, so subsequent ticks must NOT keep
    calling cancel_waypoint_navigation/navigate_to_waypoint(3) again --
    and must be able to reach the normal is_at_waypoint(3) check.
    """
    node = make_mission_node()
    _stub_out_side_effects(node)
    node.get_clock = MagicMock(return_value=fake_clock)
    node.state = mn.State.AUTO_WAYPOINTS
    node.waypoint1_time = fake_clock.now()
    node.is_at_waypoint = MagicMock(return_value=False)

    fake_clock.advance(mn.WAYPOINT_TIMEOUT + 1)
    node._control_loop()  # first tick: fires the skip-to-3 branch
    node.cancel_waypoint_navigation.reset_mock()

    # lots more (simulated) time passes while en route to waypoint 3 --
    # this used to keep re-triggering the wp1-timeout branch forever
    fake_clock.advance(500)
    node.is_at_waypoint = MagicMock(side_effect=lambda n: n == 3)  # now arrives at wp3
    node._control_loop()

    node.cancel_waypoint_navigation.assert_not_called()
    assert node.state == mn.State.AUTO_LANES


def test_cancel_waypoint_navigation_no_future_yet(make_mission_node):
    node = make_mission_node()
    assert node._send_goal_future is None
    node.cancel_waypoint_navigation()  # must not raise


def test_cancel_waypoint_navigation_future_not_done(make_mission_node):
    node = make_mission_node()
    future = MagicMock()
    future.done.return_value = False
    node._send_goal_future = future

    node.cancel_waypoint_navigation()  # must not call future.result()

    future.result.assert_not_called()


def test_cancel_waypoint_navigation_goal_rejected(make_mission_node):
    node = make_mission_node()
    future = MagicMock()
    future.done.return_value = True
    goal_handle = MagicMock()
    goal_handle.accepted = False
    future.result.return_value = goal_handle
    node._send_goal_future = future

    node.cancel_waypoint_navigation()

    goal_handle.cancel_goal_async.assert_not_called()


def test_cancel_waypoint_navigation_goal_accepted_wires_callback(make_mission_node):
    node = make_mission_node()
    future = MagicMock()
    future.done.return_value = True
    goal_handle = MagicMock()
    goal_handle.accepted = True
    cancel_future = MagicMock()
    goal_handle.cancel_goal_async.return_value = cancel_future
    future.result.return_value = goal_handle
    node._send_goal_future = future

    my_callback = MagicMock()
    node.cancel_waypoint_navigation(my_callback)

    goal_handle.cancel_goal_async.assert_called_once()
    cancel_future.add_done_callback.assert_called_once_with(my_callback)
