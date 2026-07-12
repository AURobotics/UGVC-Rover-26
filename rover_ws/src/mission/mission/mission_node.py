import sys
import math
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from enum import Enum
from nav_msgs.msg import Odometry, Path
from std_srvs.srv import SetBool
from rclpy.action.client import ActionClient
from geometry_msgs.msg import PoseStamped
from rover_interfaces.action import GenerateBezierPath #type: ignore
from std_msgs.msg import UInt8
from sensor_msgs.msg import NavSatFix

WAYPOINT_ERROR = 1.25 # 1.5 allowed error in meters for reaching a waypoint (1.25 for safety)
WAYPOINT_TIMEOUT = 60 # 60 seconds allowed to reach a waypoint before timing out and returning to manual control
WAYPOINT2_TIMEOUT = 44 # 45 seconds allowed for face recognition to complete before timing out and returning to waypoint navigation

EARTH_RADIUS_M = 6_371_000.0

# Topics
LOCALIZATION_TOPIC = '/odom/global'
GPS_TOPIC = '/gps/fix'                       # raw lat/lon fix, used for waypoint distance + as path origin
FACE_RECOGNITION_SERVICE = '/face_recognition/start'
WAYPOINT_NAVIGATION_SERVICE = 'generate_bezier_path'
MANUAL_TOGGLE_TOPIC = '/manual_toggle'
STATE_TOPIC = '/mission/active_state'

class State(Enum):
    MANUAL = 0 # Manual control mode
    AUTO_LANES = 1 # Autonomous lane following mode
    AUTO_WAYPOINTS = 2 # Autonomous waypoint navigation mode
    AUTO_WAYPOINT2 = 3 # Face recognition mode

class Mode(Enum):
    MANUAL = 0
    AUTO = 1

class MissionNode(Node):
    def __init__(self):
        super().__init__("mission_node")

        # 1. Initialize all tracking variables to prevent AttributeError race conditions
        self.position = None
        self.orientation = None
        self.linear_vel = None

        self.current_lat = None
        self.current_lon = None

        self.waypoint1_time = None
        self.waypoint2_time = None
        self.waypoint3_time = None

        self.waypoint2_done = False # waypoint2 completion flag
        self._send_goal_future = None  # must exist before cancel_waypoint_navigation can be called

        self.state_topic_publisher = self.create_publisher(UInt8, STATE_TOPIC, 10)

        # Instantiate clients in constructor
        self.face_recognition_client = self.create_client(SetBool, FACE_RECOGNITION_SERVICE)

        self.waypoint_navigation_client = self._action_client = ActionClient(self,
                                                                GenerateBezierPath,
                                                                WAYPOINT_NAVIGATION_SERVICE
                                                                )

        self._declare_fetch_variables()

        self.state = State.MANUAL # Initial state is manual control for all modes

        if self.mode == Mode.AUTO:
            self.manual_toggle_server = self.create_service(
                SetBool,
                MANUAL_TOGGLE_TOPIC,
                self.manual_toggle_callback
            ) # Service is only used in auto to switch to and from manual

        self.position_subscriber = self.create_subscription(
            Odometry,
            LOCALIZATION_TOPIC,
            self.odom_callback,
            10
        )

        # Raw GPS fix: needed both to test "am I at the waypoint?" and to build the
        # 2-point (current -> target) GPS path the Bezier action server requires.
        self.gps_subscriber = self.create_subscription(
            NavSatFix,
            GPS_TOPIC,
            self.gps_callback,
            10
        )

        self.create_timer(0.05, self._control_loop)

    def _control_loop(self):
        if self.state == State.MANUAL:
            self.state_topic_publisher.publish(UInt8(data=State.MANUAL.value))

        elif self.state == State.AUTO_LANES:
            if self.is_at_waypoint(1):
                self.state = State.AUTO_WAYPOINTS
                self.waypoint1_time = self.get_clock().now()
                self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINTS.value))
                self.navigate_to_waypoint(2)
                return

            self.state_topic_publisher.publish(UInt8(data=State.AUTO_LANES.value))

        elif self.state == State.AUTO_WAYPOINTS:
            is_timed_out1 = False
            # Only relevant while we're still trying to reach waypoint 2 -- once waypoint2_done
            # is True this must stop being evaluated, otherwise it fires on every tick forever
            # (waypoint1_time is old by the time we're heading to waypoint 3) and blocks the
            # is_at_waypoint(3) check below from ever being reached.
            if self.waypoint1_time is not None and not self.waypoint2_done:
                is_timed_out1 = (self.get_clock().now() - self.waypoint1_time) >= Duration(seconds=WAYPOINT_TIMEOUT)

            is_timed_out3 = False
            if self.waypoint3_time is not None:
                is_timed_out3 = (self.get_clock().now() - self.waypoint3_time) >= Duration(seconds=WAYPOINT_TIMEOUT * 2) # double timeout for waypoint 3 since it is the last waypoint and we want to give it more time to reach

            if self.is_at_waypoint(2) and not self.waypoint2_done:
                self.state = State.AUTO_WAYPOINT2
                self.waypoint2_time = self.get_clock().now()
                self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINT2.value))
                self.start_waypoint2()
                return
            elif is_timed_out1:
                self.get_logger().error("Timeout reached at waypoint 2. Skipping to waypoint 3.")
                self.waypoint2_done = True   # skip face recognition, we never reached waypoint 2
                self.waypoint1_time = None   # stop re-triggering this branch
                self.waypoint3_time = self.get_clock().now()
                self.cancel_waypoint_navigation(lambda f: self.navigate_to_waypoint(3))
            elif self.is_at_waypoint(3) or is_timed_out3:
                self.state = State.AUTO_LANES
                if is_timed_out3:
                    self.get_logger().error("Timeout reached at waypoint 3. Returning to lane following.")

            self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINTS.value))

        elif self.state == State.AUTO_WAYPOINT2:
            is_timed_out2 = False
            if self.waypoint2_time is not None:
                is_timed_out2 = (self.get_clock().now() - self.waypoint2_time) >= Duration(seconds=WAYPOINT2_TIMEOUT)

            done = False # placeholder for future feedback as mentioned in TODO below
            if is_timed_out2 or done:
                self.call_face_recognition_service(False, "Stopping face recognition after 45 seconds")
                self.waypoint2_done = True
                self.state = State.AUTO_WAYPOINTS
                self.waypoint3_time = self.get_clock().now()
                self.navigate_to_waypoint(3)
                return
            #TODO
            # or if WAYPOINT2 is completed: (node for servo movement to center the face isn't written yet)
            # I will wait to take feedback from this node since it is the one that will be firing the laser
            # or the node that fires the laser

            self.state_topic_publisher.publish(UInt8(data=State.AUTO_WAYPOINT2.value))

# ===== helper functions ================================================================================

    def _declare_fetch_variables(self):
        self.declare_parameter('mode', 0)  # 0: manual, 1: auto
        mode_value = self.get_parameter('mode').get_parameter_value().integer_value

        # in case of manual mode, State = MANUAL and no switching
        if mode_value not in [0, 1]:
            self.get_logger().error("Invalid mode parameter. Must be 0 (manual) or 1 (auto).")
            sys.exit(1)
        elif mode_value == 0:
            self.mode = Mode.MANUAL
            return # if manual mode, no need to declare other variables
        self.mode = Mode.AUTO

        # waypoint coordinates (only used in auto mode)
        self.waypoints = {}

        # Loop over 1, 2, 3 to match the exact names in your YAML file (wp1, wp2, wp3)
        for wp in range(1, 4):
            # 1. Properly declare the flattened parameters based on YAML keys (waypoints.1.latitude, etc.)
            self.declare_parameter(f'waypoints.wp{wp}.latitude', 0.0)
            self.declare_parameter(f'waypoints.wp{wp}.longitude', 0.0)

            # 2. Shift the dictionary storage index back by 1 (e.g., waypoint 1 stores at index 0)
            storage_index = wp - 1

            self.waypoints[storage_index] = {
                'latitude': self.get_parameter(f'waypoints.wp{wp}.latitude').value,
                'longitude': self.get_parameter(f'waypoints.wp{wp}.longitude').value
            }

    def odom_callback(self, msg: Odometry):
        self.position = msg.pose.pose.position
        self.orientation = msg.pose.pose.orientation
        self.linear_vel = msg.twist.twist.linear

    def gps_callback(self, msg: NavSatFix):
        self.current_lat = msg.latitude
        self.current_lon = msg.longitude

    # @staticmethod
    # def _haversine_distance(lat1, lon1, lat2, lon2):
    #     """Great-circle distance in meters between two lat/lon points."""
    #     phi1, phi2 = math.radians(lat1), math.radians(lat2)
    #     dphi = math.radians(lat2 - lat1)
    #     dlambda = math.radians(lon2 - lon1)
    #     a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    #     return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))

    # def is_at_waypoint(self, waypoint_number):
    #     """True if the robot's current GPS fix is within WAYPOINT_ERROR meters of the
    #     given waypoint (1-indexed, matching self.waypoints keys 0..2)."""
    #     if self.current_lat is None or self.current_lon is None:
    #         return False

    #     target = self.waypoints[waypoint_number - 1]
    #     dist = self._haversine_distance(
    #         self.current_lat, self.current_lon,
    #         target['latitude'], target['longitude']
    #     )
    #     return dist <= WAYPOINT_ERROR

    def gps_to_xy(self, lat, lon, origin_lat, origin_lon):
        """
            Convert GPS coordinates to local Cartesian coordinates (x, y) in meters.
            x is the Easting (longitude), y is the Northing (latitude).
        """
        phi1, phi2 = math.radians(origin_lat), math.radians(lat)
        dphi = math.radians(lat - origin_lat)
        dlambda = math.radians(lon - origin_lon)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2 * math.asin(math.sqrt(a))
        distance = EARTH_RADIUS_M * c

        # Calculate bearing from origin to target
        y = math.sin(dlambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
        bearing = math.atan2(y, x)

        # Convert polar coordinates (distance, bearing) to Cartesian (x, y)
        x_local = distance * math.cos(bearing)
        y_local = distance * math.sin(bearing)

        return x_local, y_local
    
    def is_at_waypoint(self, waypoint_number):
        """True if the robot's current GPS fix is within WAYPOINT_ERROR meters of the
        given waypoint (1-indexed, matching self.waypoints keys 0..2)."""
        if self.current_lat is None or self.current_lon is None:
            return False

        target = self.waypoints[waypoint_number - 1]
        x_local, y_local = self.gps_to_xy(
            START_LAT, START_LON,
            target['latitude'], target['longitude']
        )
        distance = ((x_local-)**2 + (y_local-)**2)**0.5  # Calculate Euclidean distance in local frame
        return distance <= WAYPOINT_ERROR

    #waypoint navigation
    def navigate_to_waypoint(self, waypoint_number):
        if self.current_lat is None or self.current_lon is None:
            self.get_logger().error("No GPS fix yet -- cannot start waypoint navigation.")
            return

        gps_path_msg = Path()
        gps_path_msg.header.frame_id = "wgs84"
        gps_path_msg.header.stamp = self.get_clock().now().to_msg()

        # The Bezier server needs >= 2 points: the current position (used as the local-frame
        # origin) and the target waypoint. Sending only the target gets the goal REJECTED.
        start_pose = PoseStamped()
        start_pose.pose.position.x = float(self.current_lat)
        start_pose.pose.position.y = float(self.current_lon)
        start_pose.pose.position.z = 0.0
        gps_path_msg.poses.append(start_pose)

        target_pose = PoseStamped()
        target_pose.pose.position.x = float(self.waypoints[waypoint_number - 1]['latitude'])
        target_pose.pose.position.y = float(self.waypoints[waypoint_number - 1]['longitude'])
        target_pose.pose.position.z = 0.0
        gps_path_msg.poses.append(target_pose)

        goal_msg = GenerateBezierPath.Goal()
        goal_msg.raw_gps_path = gps_path_msg

        self.get_logger().info("Waiting for Path Action ")
        self._action_client.wait_for_server()

        self.get_logger().info("Sending GPS Waypoint to Server...")
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self._waypoint_navigation_feedback_callback
        )
        self._send_goal_future.add_done_callback(self._waypoint_navigation_goal_response_callback)

    def _waypoint_navigation_goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal REJECTED by server.")
            return

        self.get_logger().info("Goal ACCEPTED by server, waiting for result...")
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self._waypoint_navigation_result_callback)

    def _waypoint_navigation_feedback_callback(self, feedback_msg):
        status = feedback_msg.feedback.status
        self.get_logger().info(f"[Feedback State]: {status}")

    def _waypoint_navigation_result_callback(self, future):
        result = future.result().result
        if result.success:
            self.get_logger().info(f"[Success]: {result.message}")
            self.get_logger().info(
                f"Total dense points built and published: {result.total_generated_points}"
            )

            if result.leg_start_indices:
                self.get_logger().info(
                    f"Leg start indices: {list(result.leg_start_indices)}"
                )
                self.get_logger().info(
                    f"Leg point counts:  {list(result.leg_point_counts)}"
                )
        else:
            self.get_logger().error(f"[Failed]: {result.message}")

    def cancel_waypoint_navigation(self, callback=None):
        if self._send_goal_future is None or not self._send_goal_future.done():
            self.get_logger().info("No active goal to cancel.")
            return

        goal_handle = self._send_goal_future.result()
        if goal_handle.accepted:
            cancel_future = goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(callback if callback is not None else (lambda f: None))
        else:
            self.get_logger().info("No active goal to cancel.")

    # WAYPOINT 2: Face recognition Functions
    def start_waypoint2(self):
        self.call_face_recognition_service(True, "Starting face recognition for waypoint 2")

    def call_face_recognition_service(self, state: bool, reason: str = ""):
        if not self.face_recognition_client.service_is_ready():
            self.get_logger().error("[SESSION] Face recognition service not available")
            return

        request = SetBool.Request()
        request.data = state
        future = self.face_recognition_client.call_async(request)
        future.add_done_callback(
            lambda f: self.face_recognition_client_callback(f, reason)
        )

    def face_recognition_client_callback(self, future, reason: str):
        try:
            response = future.result()
            tag = f" ({reason})" if reason else ""
            self.get_logger().info(f"Service response{tag}: {response.message}")
        except Exception as e:
            self.get_logger().error(f"Service call failed: {e}")

    def manual_toggle_callback(self, request, response):
        if request.data:
            self.state = State.MANUAL
            response.success = True
            response.message = "Switched to manual control"
            self.get_logger().info("Switched to manual control")
        else:
            if self.state == State.MANUAL:
                self.state = State.AUTO_LANES
                response.success = True
                response.message = "Switched to autonomous lane following"
                self.get_logger().info("Switched to autonomous lane following")
            else:
                response.success = False
                response.message = "Already in autonomous mode"
                self.get_logger().info("Already in autonomous mode")
        return response

def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()