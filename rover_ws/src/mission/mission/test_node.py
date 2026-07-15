import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from nav_msgs.msg import Odometry
from std_msgs.msg import UInt8
from std_srvs.srv import SetBool
from rover_interfaces.action import GenerateBezierPath # type: ignore

class TestNode(Node):
    def __init__(self):
        super().__init__('test_node')
        
        # Internal State tracking
        self.current_mission_state = 0  # 0: MANUAL, 1: AUTO_LANES, 2: AUTO_WAYPOINTS, 3: AUTO_WAYPOINT2
        self.timer_counter = 0

        # 1. Subscriptions & Publishers
        self.state_sub = self.create_subscription(UInt8, '/mission/active_state', self.state_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom/global', 10)
        
        # 2. Service Servers & Action Servers (Mocking External Subsystems)
        self.face_rec_server = self.create_service(SetBool, '/face_recognition/start', self.face_rec_callback)
        
        # Adding the missing Bezier Path Action Server to prevent MissionNode from hanging
        self._action_server = ActionServer(
            self,
            GenerateBezierPath,
            'generate_bezier_path',
            execute_callback=self.bezier_action_execute_callback,
            goal_callback=self.bezier_action_goal_callback,
            cancel_callback=self.bezier_action_cancel_callback
        )
        
        # 3. Service Clients
        self.toggle_client = self.create_client(SetBool, '/manual_toggle')
        
        # 4. Simulation Control Loop (Faster 5Hz loop for more responsive state switching)
        self.timer = self.create_timer(0.2, self.test_sequence_loop)
        
        self.get_logger().info("====================================================")
        self.get_logger().info("Upgraded Mission Test Node Started.")
        self.get_logger().info("====================================================")

    def state_callback(self, msg: UInt8):
        states = {0: "MANUAL", 1: "AUTO_LANES", 2: "AUTO_WAYPOINTS", 3: "AUTO_WAYPOINT2"}
        self.current_mission_state = msg.data
        state_name = states.get(int(msg.data), f"UNKNOWN ({msg.data})")
        self.get_logger().info(f"[MONITOR] Mission Node State -> {state_name}", throttle_duration_sec=2.0)

    def face_rec_callback(self, request, response):
        self.get_logger().info(f"[MOCK FACE REC] Received service call! Request data: {request.data}")
        response.success = True
        response.message = f"Mock Face Rec toggled to {request.data}"
        return response

    # --- Mock Action Server Callbacks ---
    def bezier_action_goal_callback(self, goal_request):
        self.get_logger().info("[MOCK BEZIER SERVER] Goal received! Accepting tracking request.")
        return GoalResponse.ACCEPT

    def bezier_action_cancel_callback(self, goal_handle):
        self.get_logger().info("[MOCK BEZIER SERVER] Cancel received!")
        return CancelResponse.ACCEPT

    def bezier_action_execute_callback(self, goal_handle):
        self.get_logger().info("[MOCK BEZIER SERVER] Executing path tracking simulation...")
        feedback_msg = GenerateBezierPath.Feedback()
        feedback_msg.status = "Mocking progress..."
        goal_handle.publish_feedback(feedback_msg)
        
        goal_handle.succeed()
        result = GenerateBezierPath.Result()
        result.success = True
        result.message = "Mock path followed successfully."
        return result

    # --- Core Test Orchestration Loop ---
    def test_sequence_loop(self):
        self.timer_counter += 1

        # Phase 0: Trigger transition from MANUAL to AUTO_LANES
        if self.current_mission_state == 0:  # State.MANUAL
            if self.timer_counter >= 15:  # Wait ~3 seconds
                if self.toggle_client.service_is_ready():
                    self.get_logger().info("[TEST SEQUENCE] Requesting switch to Autonomous mode...")
                    req = SetBool.Request()
                    req.data = False  # Triggers AUTO_LANES transition in mission_node
                    self.toggle_client.call_async(req)
                    self.timer_counter = 0
                else:
                    self.get_logger().warn("Waiting for '/manual_toggle' service...")

        # Phase 1: In AUTO_LANES -> Feed Odom data to satisfy Waypoint 1 (Default: 100.0, 100.0)
        elif self.current_mission_state == 1:  # State.AUTO_LANES
            # publish going to waypoint 1
            self.publish_mock_odom(10, 10)
            self.publish_mock_odom(50, 50)
            self.publish_mock_odom(90, 90) 
            
            # Within 1.25m threshold of (100.0, 100.0)
            self.publish_mock_odom(99.2, 99.2)

        # Phase 2: In AUTO_WAYPOINTS -> Feed Odom data to satisfy Waypoint 2 (Default: 200.0, 200.0)
        elif self.current_mission_state == 2:  # State.AUTO_WAYPOINTS
            # Within 1.25m threshold of (200.0, 200.0)
            self.publish_mock_odom(200.1, 200.1)

        # Phase 3: In AUTO_WAYPOINT2 -> Node is waiting on Face Recognition
        elif self.current_mission_state == 3:  # State.AUTO_WAYPOINT2
            self.get_logger().info("[TEST SEQUENCE] Mission in Face Rec mode. Waiting out timeout or feedback...", throttle_duration_sec=5.0)
            # Maintain position around Waypoint 2 during face recognition routine
            self.publish_mock_odom(300.0, 300.0)

    def publish_mock_odom(self, x: float, y: float):
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        self.odom_pub.publish(msg)
        self.get_logger().info(f"[MOCK ODOM] Transmitting position: x={x}, y={y}", throttle_duration_sec=4.0)

def main(args=None):
    rclpy.init(args=args)
    node = TestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()