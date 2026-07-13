"""
Tests for MissionNode._haversine_distance() and MissionNode.is_at_waypoint().

Covers:
  - distance-to-self is zero
  - distance is symmetric
  - matches an independently-computed reference haversine value
  - is_at_waypoint True strictly inside WAYPOINT_ERROR
  - is_at_waypoint True exactly ON the WAYPOINT_ERROR boundary (<=)
  - is_at_waypoint False just outside the boundary
  - is_at_waypoint False when no GPS fix has arrived yet
  - correct waypoint indexing (wp1/wp2/wp3 -> dict index 0/1/2)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mission import mission_node as mn
from conftest import TEST_WAYPOINTS, haversine, offset_latlon

def test_distance_to_self_is_zero(make_mission_node):
    node = make_mission_node()
    lat, lon = TEST_WAYPOINTS[1]["latitude"], TEST_WAYPOINTS[1]["longitude"]
    assert node._haversine_distance(lat, lon, lat, lon) == 0.0


def test_distance_is_symmetric(make_mission_node):
    node = make_mission_node()
    a = TEST_WAYPOINTS[1]
    b = TEST_WAYPOINTS[2]
    d1 = node._haversine_distance(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    d2 = node._haversine_distance(b["latitude"], b["longitude"], a["latitude"], a["longitude"])
    assert d1 == pytest.approx(d2, abs=1e-9)


def test_distance_matches_reference_formula(make_mission_node):
    node = make_mission_node()
    a = TEST_WAYPOINTS[1]
    b = TEST_WAYPOINTS[3]
    got = node._haversine_distance(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    expected = haversine(a["latitude"], a["longitude"], b["latitude"], b["longitude"])
    assert got == pytest.approx(expected, rel=1e-9)


def test_is_at_waypoint_true_when_close(make_mission_node):
    node = make_mission_node()
    wp2 = TEST_WAYPOINTS[2]
    # 0.5 m from waypoint 2, well inside the 1.25 m error radius
    lat, lon = offset_latlon(wp2["latitude"], wp2["longitude"], north_m=0.5, east_m=0.0)
    node.current_lat, node.current_lon = lat, lon
    assert node.is_at_waypoint(2) is True


def test_is_at_waypoint_true_on_boundary(make_mission_node):
    node = make_mission_node()
    wp2 = TEST_WAYPOINTS[2]
    lat, lon = offset_latlon(wp2["latitude"], wp2["longitude"], north_m=mn.WAYPOINT_ERROR, east_m=0.0)
    node.current_lat, node.current_lon = lat, lon
    dist = node._haversine_distance(lat, lon, wp2["latitude"], wp2["longitude"])
    # boundary point should measure very close to WAYPOINT_ERROR (small numerical drift
    # from the flat-earth offset approximation is expected and fine)
    assert dist == pytest.approx(mn.WAYPOINT_ERROR, abs=0.01)
    assert node.is_at_waypoint(2) is True


def test_is_at_waypoint_false_just_outside(make_mission_node):
    node = make_mission_node()
    wp2 = TEST_WAYPOINTS[2]
    lat, lon = offset_latlon(wp2["latitude"], wp2["longitude"], north_m=mn.WAYPOINT_ERROR + 0.5, east_m=0.0)
    node.current_lat, node.current_lon = lat, lon
    assert node.is_at_waypoint(2) is False


def test_is_at_waypoint_false_far_away(make_mission_node):
    node = make_mission_node()
    wp1 = TEST_WAYPOINTS[1]
    lat, lon = offset_latlon(wp1["latitude"], wp1["longitude"], north_m=500.0, east_m=200.0)
    node.current_lat, node.current_lon = lat, lon
    assert node.is_at_waypoint(1) is False


def test_is_at_waypoint_false_without_gps_fix(make_mission_node):
    node = make_mission_node()
    assert node.current_lat is None and node.current_lon is None
    assert node.is_at_waypoint(1) is False
    assert node.is_at_waypoint(2) is False
    assert node.is_at_waypoint(3) is False


def test_waypoint_indexing_matches_yaml_order(make_mission_node):
    node = make_mission_node()
    for wp_num in (1, 2, 3):
        stored = node.waypoints[wp_num - 1]
        expected = TEST_WAYPOINTS[wp_num]
        assert stored["latitude"] == pytest.approx(expected["latitude"])
        assert stored["longitude"] == pytest.approx(expected["longitude"])

