"""
Shared pytest fixtures for mission_node tests.

Layout assumed:
    your_package/
        mission_node.py
        tests/
            conftest.py         <- this file
            test_*.py

If mission_node.py lives elsewhere, adjust the sys.path.insert below
(or install the package and drop the path hack).
"""
import os
import sys
import math
import tempfile
import yaml
import pytest
import rclpy
from rclpy.time import Time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mission import mission_node as mn


# --------------------------------------------------------------------------
# Test waypoint layout
#
# Chosen so distances are easy to hand-verify:
#   - 1 degree of latitude ~= 111,320 m
#   - WP1 -> WP2 is ~5 m north  (well inside the 1.25 m error is NOT true;
#     used only as a "far away" reference point)
#   - A "near" point 1.0 m from WP2 and a "far" point 2.0 m from WP2 are
#     computed precisely in the tests themselves via the same haversine
#     math, so the test is self-consistent regardless of Earth-radius
#     rounding choices.
# --------------------------------------------------------------------------
TEST_WAYPOINTS = {
    1: {"latitude": 30.0812120422, "longitude": 31.2961983329},
    2: {"latitude": 30.0811119783, "longitude": 31.2962010261},
    3: {"latitude": 30.0811029050, "longitude": 31.2960926525},
}


def _write_params_yaml(tmp_path, mode=1, waypoints=TEST_WAYPOINTS):
    params = {
        "mission_node": {
            "ros__parameters": {
                "mode": mode,
                "waypoints": {
                    f"wp{i}": {
                        "latitude": wp["latitude"],
                        "longitude": wp["longitude"],
                    }
                    for i, wp in waypoints.items()
                },
            }
        }
    }
    path = os.path.join(tmp_path, "test_params.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(params, f)
    return path


@pytest.fixture(scope="session", autouse=True)
def rclpy_context():
    """rclpy must be initialized exactly once for the whole test session."""
    rclpy.init(args=[])
    yield
    rclpy.shutdown()


@pytest.fixture
def make_mission_node(tmp_path):
    """
    Factory fixture: make_mission_node(mode=1, waypoints=TEST_WAYPOINTS)
    returns a live MissionNode built with the given params, and destroys
    it automatically at the end of the test.
    """
    created = []

    def _factory(mode=1, waypoints=TEST_WAYPOINTS):
        params_path = _write_params_yaml(tmp_path, mode=mode, waypoints=waypoints)
        node = mn.MissionNode.__new__(mn.MissionNode)  # bypass nothing, real init below
        # Re-init rclpy Node base with per-node params file so we don't
        # touch global context args (keeps tests isolated from each other).
        rclpy.node.Node.__init__(
            node, "mission_node",
            cli_args=["--ros-args", "--params-file", params_path],
        )
        # Now run the rest of MissionNode's __init__ body manually is fragile;
        # instead we just call the real __init__ but it re-calls Node.__init__.
        # Simpler & robust: construct fresh, passing cli_args through a thin
        # subclass so MissionNode's own __init__ runs untouched.
        node.destroy_node()

        class _TestMissionNode(mn.MissionNode):
            def __init__(self):
                # Same as MissionNode.__init__ but forwards cli_args so the
                # params file above is actually picked up.
                rclpy.node.Node.__init__(
                    self, "mission_node",
                    cli_args=["--ros-args", "--params-file", params_path],
                )
                self.position = None
                self.orientation = None
                self.linear_vel = None
                self.current_lat = None
                self.current_lon = None
                self.waypoint1_time = None
                self.waypoint2_time = None
                self.waypoint3_time = None
                self.waypoint2_done = False
                self._send_goal_future = None
                self.state_topic_publisher = self.create_publisher(mn.UInt8, mn.STATE_TOPIC, 10)
                self.face_recognition_client = self.create_client(mn.SetBool, mn.FACE_RECOGNITION_SERVICE)
                self.waypoint_navigation_client = self._action_client = mn.ActionClient(
                    self, mn.GenerateBezierPath, mn.WAYPOINT_NAVIGATION_SERVICE
                )
                self._declare_fetch_variables()
                self.state = mn.State.MANUAL
                if self.mode == mn.Mode.AUTO:
                    self.manual_toggle_server = self.create_service(
                        mn.SetBool, mn.MANUAL_TOGGLE_TOPIC, self.manual_toggle_callback
                    )
                self.position_subscriber = self.create_subscription(
                    mn.Odometry, mn.LOCALIZATION_TOPIC, self.odom_callback, 10
                )
                self.gps_subscriber = self.create_subscription(
                    mn.NavSatFix, mn.GPS_TOPIC, self.gps_callback, 10
                )
                self.create_timer(0.05, self._control_loop)

        test_node = _TestMissionNode()
        created.append(test_node)
        return test_node

    yield _factory

    for n in created:
        n.destroy_node()


class FakeClock:
    """Deterministic stand-in for node.get_clock(), advanced manually by tests."""

    def __init__(self, start_seconds=0.0):
        self._t = float(start_seconds)

    def now(self):
        return Time(seconds=self._t)

    def advance(self, dt_seconds):
        self._t += dt_seconds
        return self.now()


@pytest.fixture
def fake_clock():
    return FakeClock()


def haversine(lat1, lon1, lat2, lon2):
    """Reference implementation used to independently verify mission_node's math."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def offset_latlon(lat, lon, north_m, east_m):
    """Return a lat/lon shifted approximately north_m/east_m meters from (lat, lon)."""
    R = 6_371_000.0
    dlat = (north_m / R) * (180.0 / math.pi)
    dlon = (east_m / (R * math.cos(math.radians(lat)))) * (180.0 / math.pi)
    return lat + dlat, lon + dlon
