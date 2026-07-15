"""
Tests for _declare_fetch_variables() (mode/waypoint parameter parsing) and
manual_toggle_callback() (the /manual_toggle service).

Covers:
  - mode=1 (auto): waypoints parsed correctly, manual_toggle service created
  - mode=0 (manual): no waypoints declared, manual_toggle service NOT created
  - invalid mode value exits the process (sys.exit)
  - manual_toggle: True while in any state -> MANUAL, success
  - manual_toggle: False while MANUAL -> AUTO_LANES, success
  - manual_toggle: False while already AUTO_* -> failure, state unchanged
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mission import mission_node as mn

def test_auto_mode_parses_waypoints_and_creates_toggle_service(make_mission_node):
    node = make_mission_node(mode=1)
    assert node.mode == mn.Mode.AUTO
    assert len(node.waypoints) == 3
    assert hasattr(node, "manual_toggle_server")


def test_manual_mode_skips_waypoints_and_toggle_service(make_mission_node):
    node = make_mission_node(mode=0)
    assert node.mode == mn.Mode.MANUAL
    assert not hasattr(node, "waypoints")
    assert not hasattr(node, "manual_toggle_server")


def test_invalid_mode_exits(make_mission_node):
    with pytest.raises(SystemExit):
        make_mission_node(mode=7)


def test_manual_toggle_to_manual_always_succeeds(make_mission_node):
    node = make_mission_node(mode=1)
    node.state = mn.State.AUTO_LANES

    request = mn.SetBool.Request()
    request.data = True
    response = node.manual_toggle_callback(request, mn.SetBool.Response())

    assert node.state == mn.State.MANUAL
    assert response.success is True


def test_manual_toggle_to_auto_from_manual_succeeds(make_mission_node):
    node = make_mission_node(mode=1)
    node.state = mn.State.MANUAL

    request = mn.SetBool.Request()
    request.data = False
    response = node.manual_toggle_callback(request, mn.SetBool.Response())

    assert node.state == mn.State.AUTO_LANES
    assert response.success is True


def test_manual_toggle_to_auto_when_already_auto_fails(make_mission_node):
    node = make_mission_node(mode=1)
    node.state = mn.State.AUTO_WAYPOINTS

    request = mn.SetBool.Request()
    request.data = False
    response = node.manual_toggle_callback(request, mn.SetBool.Response())

    assert node.state == mn.State.AUTO_WAYPOINTS, "state must not change on failed toggle"
    assert response.success is False
